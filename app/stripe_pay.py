"""Paiement Stripe Checkout. Les cartes ne transitent jamais par ce serveur."""

import base64
import hashlib
import hmac
import json
import os
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

from app.orders import STATUS_LABELS, order_events
from app.schedule import load_json_setting

API = "https://api.stripe.com/v1"
MIN_CENTS = 50
CURRENCY = "eur"
_BLOB_CHUNK = 450
_hits = {}
_ready = {"fingerprint": "", "ok": None, "error": "", "at": 0.0}


def _integrity_error():
    try:
        import turso_serverless

        return (sqlite3.IntegrityError, turso_serverless.IntegrityError)
    except Exception:
        return (sqlite3.IntegrityError,)


def _order_snapshot(order):
    keys = (
        "public_ref",
        "user_id",
        "session_id",
        "status",
        "mode",
        "customer_name",
        "email",
        "phone",
        "address_json",
        "pickup_point_id",
        "slot_id",
        "zone_id",
        "payment_method",
        "payment_status",
        "subtotal_cents",
        "delivery_fee_cents",
        "discount_cents",
        "total_cents",
        "promo_code",
        "idempotency_key",
        "snapshot_json",
        "created_at",
        "distance_meters",
    )
    available = set(order.keys()) if hasattr(order, "keys") else set(order)
    return {key: order[key] for key in keys if key in available}


def _pack_order_blob(order):
    raw = json.dumps(_order_snapshot(order), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    token = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")
    chunks = [token[i : i + _BLOB_CHUNK] for i in range(0, len(token), _BLOB_CHUNK)]
    if not chunks or len(chunks) > 40:
        return []
    fields = [("metadata[obn]", str(len(chunks)))]
    for index, chunk in enumerate(chunks):
        fields.append((f"metadata[ob{index}]", chunk))
    return fields


def _unpack_order_blob(metadata):
    if not isinstance(metadata, dict):
        return None
    try:
        count = int(metadata.get("obn") or "0")
    except (TypeError, ValueError):
        return None
    if count < 1 or count > 40:
        return None
    parts = []
    for index in range(count):
        piece = metadata.get(f"ob{index}")
        if not isinstance(piece, str) or not piece:
            return None
        parts.append(piece)
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode("".join(parts).encode("ascii")))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, zlib.error, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("public_ref"), str):
        return None
    return data


def ensure_order_from_checkout(conn, checkout, claim_session_id=None):
    """Recrée une commande absente à partir des métadonnées Stripe (Vercel multi-instance)."""
    metadata = checkout.get("metadata") or {}
    reference = metadata.get("order_ref") or checkout.get("client_reference_id") or ""
    if not reference:
        return None
    existing = conn.execute("SELECT * FROM orders WHERE public_ref = ?", (reference,)).fetchone()
    if existing:
        if claim_session_id and existing["session_id"] != claim_session_id:
            conn.execute(
                "UPDATE orders SET session_id = ? WHERE id = ? AND payment_status != 'paid'",
                (claim_session_id, existing["id"]),
            )
            existing = conn.execute("SELECT * FROM orders WHERE id = ?", (existing["id"],)).fetchone()
        return existing
    data = _unpack_order_blob(metadata)
    if not data or data.get("public_ref") != reference:
        return None
    if data.get("payment_method") != "stripe":
        return None
    session_id = claim_session_id or data.get("session_id")
    try:
        cur = conn.execute(
            """
            INSERT INTO orders (
              public_ref, user_id, session_id, status, mode, customer_name, email, phone,
              address_json, pickup_point_id, slot_id, zone_id, payment_method, payment_status,
              subtotal_cents, delivery_fee_cents, discount_cents, total_cents, promo_code,
              idempotency_key, snapshot_json, created_at, stripe_session_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'stripe', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                reference,
                data.get("user_id"),
                session_id,
                data.get("status") or "received",
                data.get("mode") or "delivery",
                data.get("customer_name") or "",
                data.get("email") or "",
                data.get("phone") or "",
                data.get("address_json"),
                data.get("pickup_point_id"),
                data.get("slot_id"),
                data.get("zone_id"),
                data.get("payment_status") or "pending",
                int(data.get("subtotal_cents") or 0),
                int(data.get("delivery_fee_cents") or 0),
                int(data.get("discount_cents") or 0),
                int(data.get("total_cents") or 0),
                data.get("promo_code"),
                data.get("idempotency_key") or f"stripe-recover-{reference}",
                data.get("snapshot_json") or "[]",
                data.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                checkout.get("id"),
            ),
        )
        order_id = cur.lastrowid
        if data.get("distance_meters") is not None:
            conn.execute(
                "UPDATE orders SET distance_meters = ? WHERE id = ?",
                (data.get("distance_meters"), order_id),
            )
        conn.execute(
            "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'received', ?)",
            (order_id, data.get("created_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
    except _integrity_error():
        return conn.execute("SELECT * FROM orders WHERE public_ref = ?", (reference,)).fetchone()
    return conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()


def _looks_like_key(key):
    return isinstance(key, str) and key.startswith(
        ("sk_test_", "sk_live_", "rk_test_", "rk_live_", "rkcs_test_", "rkcs_live_")
    )


def resolve_secret_key(conn=None):
    if conn is not None:
        stored = load_json_setting(conn, "stripe_secret_key", "")
        if isinstance(stored, str) and _looks_like_key(stored.strip()):
            return stored.strip()
    return os.environ.get("STRIPE_SECRET_KEY", "").strip()


def resolve_webhook_secret(conn=None):
    if conn is not None:
        stored = load_json_setting(conn, "stripe_webhook_secret", "")
        if isinstance(stored, str) and stored.strip():
            return stored.strip()
    return os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()


def stripe_configured(conn=None):
    return _looks_like_key(resolve_secret_key(conn))


def _key(conn=None):
    return resolve_secret_key(conn)


def _webhook_secret(conn=None):
    return resolve_webhook_secret(conn)


def _auth_error(message):
    text = (message or "").lower()
    return "api key" in text or "invalid api" in text or ("expired" in text and "key" in text)


def invalidate_stripe_cache():
    _ready.update(fingerprint="", ok=None, error="", at=0.0)


def stripe_ready(conn=None):
    key = resolve_secret_key(conn)
    if not _looks_like_key(key):
        return False, "Le paiement en ligne n'est pas configuré."
    # Clé réservée aux tests unitaires : jamais une vraie clé Stripe.
    if key == "sk_test_fixture_not_a_real_key":
        return True, ""
    fingerprint = key[-12:]
    now = time.monotonic()
    if _ready["fingerprint"] == fingerprint and _ready["ok"] is not None and now - _ready["at"] < 180:
        return bool(_ready["ok"]), _ready["error"]
    data, error = _request("GET", "/account", secret_key=key, conn=conn)
    if data:
        _ready.update(fingerprint=fingerprint, ok=True, error="", at=now)
        return True, ""
    message = (
        "La clé Stripe est invalide ou expirée. Mettez-la à jour dans Réglages admin."
        if _auth_error(error)
        else (error or "Le service de paiement est injoignable.")
    )
    _ready.update(fingerprint=fingerprint, ok=False, error=message, at=now)
    return False, message


def public_base(headers):
    configured = os.environ.get("ALLOKO_PUBLIC_URL", "").strip().rstrip("/")
    if configured.startswith("https://") or configured.startswith("http://"):
        return configured
    host = (headers or {}).get("host") or "127.0.0.1:8080"
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-:")
    if not host or ".." in host or len(host) > 200 or any(char not in allowed for char in host):
        host = "127.0.0.1:8080"
    proto = "https" if (headers or {}).get("x-forwarded-proto") == "https" else "http"
    return f"{proto}://{host}"


def limited(bucket, max_hits=8, window=60):
    now = time.monotonic()
    recent = [stamp for stamp in _hits.get(bucket, []) if now - stamp < window]
    if len(recent) >= max_hits:
        _hits[bucket] = recent
        return True
    recent.append(now)
    _hits[bucket] = recent
    return False


def checkout_methods(conn):
    from app.orders import active_payment_methods

    ready, _error = stripe_ready(conn)
    rows = []
    for method in active_payment_methods(conn):
        if method["code"] == "stripe" and not ready:
            continue
        rows.append({"code": method["code"], "label": method["label"]})
    if ready and not any(row["code"] == "stripe" for row in rows):
        rows.append({"code": "stripe", "label": "Paiement en ligne"})
    return rows


def _request(method, path, fields=None, idempotency_key=None, secret_key=None, conn=None):
    key = (secret_key or resolve_secret_key(conn) or "").strip()
    if not key:
        return None, "Le paiement en ligne n'est pas configuré."
    data = urllib.parse.urlencode(fields or {}, doseq=True).encode("utf-8")
    request = urllib.request.Request(API + path, data=data if method == "POST" else None, method=method)
    request.add_header("Authorization", "Bearer " + key)
    if method == "POST":
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        if idempotency_key:
            request.add_header("Idempotency-Key", idempotency_key)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8")), None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
            message = payload.get("error", {}).get("message") or "Stripe a refusé la requête."
        except json.JSONDecodeError:
            message = "Stripe a refusé la requête."
        if _auth_error(message):
            invalidate_stripe_cache()
            message = "La clé Stripe est invalide ou expirée. Mettez-la à jour dans Réglages admin."
        return None, message
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None, "Le service de paiement est injoignable."


def _session_paid(session, order):
    amount = session.get("amount_total")
    currency = (session.get("currency") or "").lower()
    metadata = session.get("metadata") or {}
    reference = metadata.get("order_ref") or session.get("client_reference_id") or ""
    return (
        session.get("payment_status") == "paid"
        and amount == order["total_cents"]
        and currency == CURRENCY
        and reference == order["public_ref"]
    )


def _intent_id(session):
    intent = session.get("payment_intent") or ""
    if isinstance(intent, dict):
        return intent.get("id") or ""
    return intent


def _apply_session(conn, order, session, force=None):
    if order["payment_status"] == "paid":
        return "paid"
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    intent = _intent_id(session)
    session_id = session.get("id") or order["stripe_session_id"] or ""
    if force != "failed" and _session_paid(session, order):
        conn.execute(
            """UPDATE orders SET payment_status = 'paid',
               status = CASE WHEN status = 'cancelled' THEN 'received' ELSE status END,
               stripe_session_id = ?, stripe_payment_intent = ?
               WHERE id = ? AND payment_status != 'paid'""",
            (session_id, intent, order["id"]),
        )
        conn.execute(
            "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'paid', ?)",
            (order["id"], now),
        )
        return "paid"
    if force == "expired" or session.get("status") == "expired":
        if order["status"] != "cancelled" or order["payment_status"] != "cancelled":
            conn.execute(
                "UPDATE orders SET status = 'cancelled', payment_status = 'cancelled', stripe_session_id = ? WHERE id = ? AND payment_status != 'paid'",
                (session_id, order["id"]),
            )
            conn.execute(
                "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'cancelled', ?)",
                (order["id"], now),
            )
        return "cancelled"
    if force == "failed" or (session.get("status") == "complete" and session.get("payment_status") != "paid"):
        conn.execute(
            "UPDATE orders SET payment_status = 'failed', stripe_session_id = ? WHERE id = ? AND payment_status != 'paid'",
            (session_id, order["id"]),
        )
        return "failed"
    conn.execute(
        "UPDATE orders SET payment_status = 'pending', stripe_session_id = ?, stripe_payment_intent = ? WHERE id = ? AND payment_status != 'paid'",
        (session_id, intent, order["id"]),
    )
    return "pending"


def begin_checkout(conn, order, base):
    if order["payment_method"] != "stripe":
        return None, None
    ready, ready_error = stripe_ready(conn)
    if not ready:
        return None, ready_error or "Le paiement en ligne n'est pas configuré."
    if order["payment_status"] == "paid":
        return None, "Cette commande est déjà payée."
    if order["total_cents"] < MIN_CENTS:
        return None, "Le montant est inférieur au minimum accepté pour un paiement en ligne."
    if order["status"] == "cancelled":
        return None, "Cette commande est annulée. Relancez le paiement depuis le récapitulatif."
    stored = order["stripe_session_id"]
    if stored:
        session, error = _request("GET", "/checkout/sessions/" + urllib.parse.quote(stored), conn=conn)
        if session and session.get("status") == "open" and session.get("url"):
            return session["url"], None
        if session and _session_paid(session, order):
            _apply_session(conn, order, session)
            return None, "Cette commande est déjà payée."
    reference = order["public_ref"]
    fields = [
        ("mode", "payment"),
        ("locale", "fr"),
        ("success_url", f"{base}/paiement/succes?ref={urllib.parse.quote(reference)}&session_id={{CHECKOUT_SESSION_ID}}"),
        ("cancel_url", f"{base}/paiement/echec?ref={urllib.parse.quote(reference)}"),
        ("client_reference_id", reference),
        ("metadata[order_ref]", reference),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", CURRENCY),
        ("line_items[0][price_data][unit_amount]", str(order["total_cents"])),
        ("line_items[0][price_data][product_data][name]", f"Commande {reference}"),
    ]
    fields.extend(_pack_order_blob(order))
    suffix = stored or "new"
    session, error = _request(
        "POST",
        "/checkout/sessions",
        fields,
        idempotency_key=f"checkout-{reference}-{suffix}",
        conn=conn,
    )
    if error or not session or not session.get("url") or not session.get("id"):
        return None, error or "Stripe n'a pas ouvert de page de paiement."
    conn.execute(
        "UPDATE orders SET stripe_session_id = ?, payment_status = 'pending' WHERE id = ? AND payment_status != 'paid'",
        (session["id"], order["id"]),
    )
    return session["url"], None


def verify_return(conn, order, session_id):
    if not stripe_configured(conn):
        return None, "Le paiement en ligne n'est pas configuré."
    if not session_id or len(session_id) > 120 or not session_id.startswith("cs_"):
        return None, "Identifiant de paiement invalide."
    session, error = _request("GET", "/checkout/sessions/" + urllib.parse.quote(session_id), conn=conn)
    if error or not session:
        return None, error or "Stripe n'a pas confirmé cette session."
    reference = (session.get("metadata") or {}).get("order_ref") or session.get("client_reference_id") or ""
    if reference != order["public_ref"]:
        return None, "Cette session ne correspond pas à la commande."
    if session.get("amount_total") != order["total_cents"] or (session.get("currency") or "").lower() != CURRENCY:
        conn.execute(
            "UPDATE orders SET payment_status = 'failed' WHERE id = ? AND payment_status != 'paid'",
            (order["id"],),
        )
        return None, "Le montant confirmé ne correspond pas à la commande."
    state = _apply_session(conn, order, session)
    return state, None


def cancel_payment(conn, order):
    if order["payment_status"] == "paid":
        return "Une commande déjà payée ne peut pas être annulée ici."
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    conn.execute(
        "UPDATE orders SET status = 'cancelled', payment_status = 'cancelled' WHERE id = ? AND payment_status != 'paid'",
        (order["id"],),
    )
    conn.execute(
        "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'cancelled', ?)",
        (order["id"], now),
    )
    return None


def retry_payment(conn, order, base):
    if order["payment_status"] == "paid":
        return None, "Cette commande est déjà payée."
    if order["payment_method"] != "stripe":
        return None, "Cette commande n'a pas de paiement en ligne à relancer."
    if order["status"] == "cancelled":
        if order["slot_id"]:
            from app.orders import slot_remaining

            _slot, remaining = slot_remaining(conn, order["slot_id"])
            if remaining < 1:
                return None, "Le créneau n'est plus disponible."
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        conn.execute(
            "UPDATE orders SET status = 'received', payment_status = 'pending' WHERE id = ? AND payment_status != 'paid'",
            (order["id"],),
        )
        conn.execute(
            "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'payment_retry', ?)",
            (order["id"], now),
        )
        order = conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
    return begin_checkout(conn, order, base)


def verify_signature(payload, header, secret):
    if not header or not secret:
        return False
    parts = {}
    for piece in header.split(","):
        if "=" not in piece:
            continue
        key, value = piece.split("=", 1)
        parts.setdefault(key.strip(), []).append(value.strip())
    timestamps = parts.get("t") or []
    signatures = parts.get("v1") or []
    if not timestamps or not signatures:
        return False
    try:
        stamp = int(timestamps[0])
    except ValueError:
        return False
    if abs(int(time.time()) - stamp) > 300:
        return False
    signed = f"{stamp}.".encode("utf-8") + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, candidate) for candidate in signatures)


def handle_webhook(conn, payload, signature):
    secret = resolve_webhook_secret(conn)
    if not secret or not stripe_configured(conn):
        return 503, {"ok": False, "error": "Paiement non configuré."}
    if not verify_signature(payload, signature, secret):
        return 400, {"ok": False, "error": "Signature invalide."}
    try:
        event = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return 400, {"ok": False, "error": "Notification illisible."}
    event_id = event.get("id") or ""
    if not event_id.startswith("evt_") or len(event_id) > 120:
        return 400, {"ok": False, "error": "Notification invalide."}
    if conn.execute("SELECT 1 FROM stripe_events WHERE id = ?", (event_id,)).fetchone():
        return 200, {"ok": True, "duplicate": True}
    kind = event.get("type") or ""
    data = (event.get("data") or {}).get("object") or {}
    if kind not in {
        "checkout.session.completed",
        "checkout.session.async_payment_succeeded",
        "checkout.session.async_payment_failed",
        "checkout.session.expired",
    }:
        _remember(conn, event_id)
        return 200, {"ok": True, "ignored": True}
    order = ensure_order_from_checkout(conn, data)
    if not order or order["payment_method"] != "stripe":
        _remember(conn, event_id)
        return 200, {"ok": True, "ignored": True}
    if data.get("amount_total") not in (None, order["total_cents"]) or (
        data.get("currency") and data.get("currency").lower() != CURRENCY
    ):
        _remember(conn, event_id)
        return 200, {"ok": True, "ignored": True, "reason": "amount"}
    force = None
    if kind == "checkout.session.expired":
        force = "expired"
    elif kind == "checkout.session.async_payment_failed":
        force = "failed"
    _apply_session(conn, order, data, force=force)
    _remember(conn, event_id)
    return 200, {"ok": True}


def refund_order(conn, order):
    if order["payment_method"] != "stripe" or order["payment_status"] != "paid":
        return "Seule une commande encaissée en ligne peut être remboursée ici."
    intent = order["stripe_payment_intent"] or ""
    if not intent.startswith("pi_"):
        return "Aucun paiement Stripe n'est associé à cette commande."
    if not stripe_configured(conn):
        return "Le paiement en ligne n'est pas configuré."
    payload, error = _request(
        "POST",
        "/refunds",
        [("payment_intent", intent)],
        idempotency_key=f"refund-{order['public_ref']}",
        conn=conn,
    )
    if error or not payload:
        return error or "Stripe n'a pas confirmé le remboursement."
    if payload.get("status") != "succeeded":
        return "Stripe n'a pas encore confirmé le remboursement."
    conn.execute(
        "UPDATE orders SET payment_status = 'refunded' WHERE id = ? AND payment_status = 'paid'",
        (order["id"],),
    )
    conn.execute(
        "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'refunded', ?)",
        (order["id"], time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    )
    return None


def _remember(conn, event_id):
    try:
        conn.execute(
            "INSERT INTO stripe_events (id, created_at) VALUES (?, ?)",
            (event_id, time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        )
    except _integrity_error():
        pass


def payment_view(conn, order):
    status = order["payment_status"]
    labels = {
        "paid": "Paiement encaissé",
        "pending": "Paiement en attente de confirmation",
        "failed": "Paiement refusé",
        "cancelled": "Paiement annulé",
        "unpaid": "Paiement non encaissé",
        "refunded": "Paiement remboursé",
    }
    method = "Paiement en ligne" if order["payment_method"] == "stripe" else order["payment_method"]
    return {
        "paymentStatus": status,
        "paymentLabel": labels.get(status, status),
        "paymentMethod": order["payment_method"],
        "paymentMethodLabel": method,
        "confirmedByProvider": status == "paid" and order["payment_method"] == "stripe",
        "canRetry": order["payment_method"] == "stripe" and status != "paid",
        "status": order["status"],
        "statusLabel": STATUS_LABELS.get(order["status"], order["status"]),
        "events": [
            {"status": event["status"], "label": STATUS_LABELS.get(event["status"], event["status"]), "at": event["created_at"]}
            for event in order_events(conn, order["id"])
        ],
    }
