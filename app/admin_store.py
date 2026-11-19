import json

from app.money import parse_euros
from app.schedule import DEFAULT_HOURS, DEFAULT_MIDI, load_json_setting, slot_inside_hours


def save_product(conn, product_id, form):
    product = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not product:
        return "Produit introuvable."
    try:
        cents = parse_euros(form.get("prix"))
    except ValueError:
        return "Prix invalide."
    confirmed = 1 if form.get("prix_confirme") == "1" and cents is not None else 0
    available = 1 if form.get("disponible") == "1" else 0
    orderable = 1 if form.get("commandable") == "1" else 0
    featured = 1 if form.get("signature") == "1" else 0
    reason = (form.get("blocage") or "").strip() or None
    conn.execute(
        """
        UPDATE products
        SET price_cents = ?, price_confirmed = ?, available = ?, orderable = ?,
            block_reason = ?, featured = ?
        WHERE id = ?
        """,
        (cents, confirmed, available, orderable, reason, featured, product_id),
    )
    for key, value in form.items():
        if not key.startswith("choix-"):
            continue
        choice_id = int(key.split("-", 1)[1])
        try:
            delta = parse_euros(value)
        except ValueError:
            return "Supplement invalide."
        delta_ok = 1 if form.get(f"choix_ok-{choice_id}") == "1" and delta is not None else 0
        choice_on = 1 if form.get(f"choix_dispo-{choice_id}") == "1" else 0
        owned = conn.execute(
            """
            SELECT ch.id FROM option_choices ch
            JOIN option_groups g ON g.id = ch.group_id
            WHERE ch.id = ? AND g.product_id = ?
            """,
            (choice_id, product_id),
        ).fetchone()
        if not owned:
            return "Option invalide."
        conn.execute(
            """
            UPDATE option_choices
            SET price_delta_cents = ?, price_delta_confirmed = ?, available = ?
            WHERE id = ?
            """,
            (delta, delta_ok, choice_on, choice_id),
        )
    return None


def save_hours(conn, form):
    hours = {
        "mon_sat": [form.get("semaine_debut") or "11:30", form.get("semaine_fin") or "22:30"],
        "sun": [form.get("dimanche_debut") or "17:00", form.get("dimanche_fin") or "22:30"],
    }
    midi = {
        "start": form.get("midi_debut") or "12:00",
        "end": form.get("midi_fin") or "15:00",
        "sunday": form.get("midi_dimanche") == "1",
    }
    for window in (hours["mon_sat"], hours["sun"], [midi["start"], midi["end"]]):
        if not _hhmm(window[0]) or not _hhmm(window[1]) or window[1] <= window[0]:
            return "Horaires invalides."
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('hours', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(hours),),
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('midi', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(midi),),
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('allow_notes', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        ("1" if form.get("notes") == "1" else "0",),
    )
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('terms_text', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps((form.get("conditions") or "").strip()),),
    )
    return None


def add_zone(conn, form):
    name = (form.get("nom") or "").strip()
    if len(name) < 2:
        return "Nom de zone trop court."
    try:
        fee = parse_euros(form.get("frais"))
    except ValueError:
        return "Frais invalides."
    confirmed = 1 if form.get("frais_ok") == "1" and fee is not None else 0
    active = 1 if form.get("active") == "1" and confirmed else 0
    conn.execute(
        """
        INSERT INTO delivery_zones (name, fee_cents, fee_confirmed, active, notice)
        VALUES (?, ?, ?, ?, ?)
        """,
        (name, fee, confirmed, active, (form.get("notice") or "").strip() or None),
    )
    return None


def set_delivery_mode(conn, form):
    mode = form.get("mode")
    if mode not in {"zones", "distance"}:
        return "Mode de livraison inconnu."
    conn.execute(
        "INSERT INTO settings (key, value) VALUES ('delivery_mode', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (json.dumps(mode),),
    )
    return None


def add_distance_band(conn, form):
    raw = (form.get("km") or "").strip().replace(",", ".")
    try:
        km = float(raw)
        fee = parse_euros(form.get("frais"))
    except ValueError:
        return "Barème invalide."
    if km <= 0 or km > 100 or fee is None:
        return "Barème invalide."
    meters = int(round(km * 1000))
    wants_open = form.get("active") == "1"
    confirmed = 1 if form.get("frais_ok") == "1" or wants_open else 0
    active = 1 if wants_open else 0
    conn.execute(
        """
        INSERT INTO distance_bands (max_meters, fee_cents, fee_confirmed, active)
        VALUES (?, ?, ?, ?)
        """,
        (meters, fee, confirmed, active),
    )
    return None


def confirm_zone_fee(conn, zone_id):
    zone = conn.execute("SELECT * FROM delivery_zones WHERE id = ?", (zone_id,)).fetchone()
    if not zone:
        return "Zone introuvable."
    if zone["fee_cents"] is None:
        return "Indiquez d'abord les frais."
    conn.execute("UPDATE delivery_zones SET fee_confirmed = 1 WHERE id = ?", (zone_id,))
    return None


def set_zone_active(conn, zone_id, active):
    zone = conn.execute("SELECT * FROM delivery_zones WHERE id = ?", (zone_id,)).fetchone()
    if not zone:
        return "Zone introuvable."
    if active and (not zone["fee_confirmed"] or zone["fee_cents"] is None):
        return "Les frais doivent être validés avant d'ouvrir la zone."
    conn.execute("UPDATE delivery_zones SET active = ? WHERE id = ?", (1 if active else 0, zone_id))
    return None


def set_band_active(conn, band_id, active):
    band = conn.execute("SELECT * FROM distance_bands WHERE id = ?", (band_id,)).fetchone()
    if not band:
        return "Palier introuvable."
    if active and band["fee_cents"] is None:
        return "Indiquez d'abord les frais."
    if active:
        conn.execute(
            "UPDATE distance_bands SET fee_confirmed = 1, active = 1 WHERE id = ?",
            (band_id,),
        )
        return None
    conn.execute("UPDATE distance_bands SET active = 0 WHERE id = ?", (band_id,))
    return None


def save_geo_key(conn, form):
    if form.get("retirer") == "1":
        conn.execute("DELETE FROM settings WHERE key = 'geo_api_key'")
        return None
    key = (form.get("cle") or "").strip()
    if len(key) < 20 or any(char.isspace() for char in key):
        return "Collez la clé OpenRouteService, sans espace."
    from app import delivery

    error = delivery.probe_key(key)
    if error:
        return error
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('geo_api_key', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (json.dumps(key),),
    )
    return None


def _write_env_value(key, value):
    from pathlib import Path

    from app.db import ROOT

    path = ROOT / ".env"
    lines = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    written = False
    next_lines = []
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            next_lines.append(line)
            continue
        name = stripped.split("=", 1)[0].strip()
        if name == key:
            next_lines.append(f"{key}={value}")
            written = True
        else:
            next_lines.append(line)
    if not written:
        if next_lines and next_lines[-1].strip():
            next_lines.append("")
        next_lines.append(f"{key}={value}")
    path.write_text("\n".join(next_lines) + "\n", encoding="utf-8")


def save_stripe_keys(conn, form):
    import os

    from app.stripe_pay import (
        _looks_like_key,
        _request,
        invalidate_stripe_cache,
    )

    if form.get("retirer") == "1":
        conn.execute("DELETE FROM settings WHERE key IN ('stripe_secret_key', 'stripe_webhook_secret')")
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        _write_env_value("STRIPE_SECRET_KEY", "")
        _write_env_value("STRIPE_WEBHOOK_SECRET", "")
        invalidate_stripe_cache()
        return None
    key = (form.get("cle") or "").strip()
    webhook = (form.get("webhook") or "").strip()
    if not _looks_like_key(key):
        return "Collez une clé secrète Stripe (sk_test_…, sk_live_… ou rkcs_…)."
    if any(char.isspace() for char in key):
        return "La clé Stripe ne doit pas contenir d'espace."
    data, error = _request("GET", "/account", secret_key=key)
    if error or not data:
        return error or "Stripe a refusé cette clé."
    conn.execute(
        """
        INSERT INTO settings (key, value) VALUES ('stripe_secret_key', ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (json.dumps(key),),
    )
    os.environ["STRIPE_SECRET_KEY"] = key
    _write_env_value("STRIPE_SECRET_KEY", key)
    if webhook:
        if not webhook.startswith("whsec_") or len(webhook) < 20:
            return "Le secret webhook doit commencer par whsec_."
        conn.execute(
            """
            INSERT INTO settings (key, value) VALUES ('stripe_webhook_secret', ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (json.dumps(webhook),),
        )
        os.environ["STRIPE_WEBHOOK_SECRET"] = webhook
        _write_env_value("STRIPE_WEBHOOK_SECRET", webhook)
    invalidate_stripe_cache()
    return None


def set_slot_active(conn, slot_id, active):
    slot = conn.execute("SELECT id FROM pickup_slots WHERE id = ?", (slot_id,)).fetchone()
    if not slot:
        return "Créneau introuvable."
    conn.execute("UPDATE pickup_slots SET active = ? WHERE id = ?", (1 if active else 0, slot_id))
    return None


def add_slot(conn, form):
    date = (form.get("date") or "").strip()
    start = (form.get("debut") or "").strip()
    end = (form.get("fin") or "").strip()
    try:
        capacity = int(form.get("capacite") or 0)
    except ValueError:
        return "Capacite invalide."
    if not _date(date) or not _hhmm(start) or not _hhmm(end) or capacity < 1:
        return "Creneau invalide."
    hours = load_json_setting(conn, "hours", DEFAULT_HOURS)
    if not slot_inside_hours(date, start, end, hours):
        return "Le creneau doit etre compris dans les horaires d'ouverture enregistres."
    conn.execute(
        """
        INSERT INTO pickup_slots (slot_date, start_time, end_time, capacity, active)
        VALUES (?, ?, ?, ?, 1)
        """,
        (date, start, end, capacity),
    )
    return None


def set_payment(conn, code, active):
    row = conn.execute("SELECT id FROM payment_methods WHERE code = ?", (code,)).fetchone()
    if not row:
        labels = {
            "pay_at_pickup": "A regler au retrait",
            "pay_on_delivery": "A regler a la livraison",
        }
        if code not in labels:
            return "Moyen de reglement inconnu."
        conn.execute(
            "INSERT INTO payment_methods (code, label, active) VALUES (?, ?, ?)",
            (code, labels[code], 1 if active else 0),
        )
        return None
    conn.execute(
        "UPDATE payment_methods SET active = ? WHERE code = ?",
        (1 if active else 0, code),
    )
    return None


def add_promo(conn, form):
    code = (form.get("code") or "").strip()
    label = (form.get("libelle") or "").strip()
    kind = form.get("type")
    if len(code) < 2 or len(label) < 2 or kind not in {"amount", "percent"}:
        return "Promotion incomplete."
    amount = None
    percent = None
    try:
        if kind == "amount":
            amount = parse_euros(form.get("valeur"))
            if amount is None:
                return "Montant manquant."
        else:
            percent = int(form.get("valeur") or 0)
            if percent < 1 or percent > 100:
                return "Pourcentage invalide."
    except ValueError:
        return "Valeur de promotion invalide."
    conn.execute(
        """
        INSERT INTO promo_codes (code, label, kind, amount_cents, percent, active)
        VALUES (?, ?, ?, ?, ?, 1)
        """,
        (code, label, kind, amount, percent),
    )
    return None


def _hhmm(value):
    parts = (value or "").split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        return False
    hour, minute = int(parts[0]), int(parts[1])
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _date(value):
    parts = (value or "").split("-")
    return len(parts) == 3 and all(part.isdigit() for part in parts) and len(parts[0]) == 4


def settings_view(conn):
    return {
        "hours": load_json_setting(conn, "hours", DEFAULT_HOURS),
        "midi": load_json_setting(conn, "midi", DEFAULT_MIDI),
        "allow_notes": load_json_setting(conn, "allow_notes", 0),
        "terms": load_json_setting(conn, "terms_text", ""),
    }
