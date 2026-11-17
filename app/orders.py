import json
import secrets
from datetime import datetime, timedelta, timezone

from app.auth import iso, utc_now
from app.cart import cart_lines, clear_cart
from app.pricing import apply_promo
from app.schedule import (
    DEFAULT_HOURS,
    PARIS,
    hours_label,
    is_open,
    load_json_setting,
    minutes,
    now_paris,
    slot_inside_hours,
)

STATUS_LABELS = {
    "received": "Reçue",
    "accepted": "Acceptée",
    "preparing": "En préparation",
    "ready": "Prête",
    "out_for_delivery": "En livraison",
    "completed": "Terminée",
    "cancelled": "Annulée",
    "paid": "Paiement confirmé",
    "payment_retry": "Nouvelle tentative",
    "refunded": "Remboursement confirmé",
    "driver_accepted": "Prise en charge livreur",
}

KITCHEN_STATUSES = (
    "received",
    "accepted",
    "preparing",
    "ready",
    "out_for_delivery",
    "completed",
    "cancelled",
)

ACTIVE_STATUSES = (
    "received",
    "accepted",
    "preparing",
    "ready",
    "out_for_delivery",
    "completed",
)

OPEN_STATUSES = (
    "received",
    "accepted",
    "preparing",
    "ready",
    "out_for_delivery",
)

METHOD_LABELS = {
    "pay_at_pickup": "Au retrait",
    "pay_on_delivery": "À la livraison",
    "stripe": "Paiement en ligne",
}

PAY_LABELS = {
    "paid": "Encaissé",
    "pending": "En attente",
    "failed": "Refusé",
    "cancelled": "Annulé",
    "unpaid": "Non encaissé",
    "refunded": "Remboursé",
}

COUNTER_METHODS = ("pay_at_pickup", "pay_on_delivery")


def active_payment_methods(conn):
    return conn.execute(
        "SELECT * FROM payment_methods WHERE active = 1 ORDER BY id"
    ).fetchall()


def active_zones(conn):
    return conn.execute(
        """
        SELECT * FROM delivery_zones
        WHERE active = 1 AND fee_confirmed = 1 AND fee_cents IS NOT NULL
        ORDER BY name
        """
    ).fetchall()


def active_points(conn):
    return conn.execute(
        "SELECT * FROM pickup_points WHERE active = 1 ORDER BY id"
    ).fetchall()


def open_slots(conn, clock=None):
    moment = now_paris(clock)
    today = moment.date().isoformat()
    current = f"{moment.hour:02d}:{moment.minute:02d}"
    rows = conn.execute(
        """
        SELECT * FROM pickup_slots
        WHERE active = 1 AND (slot_date > ? OR (slot_date = ? AND start_time > ?))
        ORDER BY slot_date, start_time
        """,
        (today, today, current),
    ).fetchall()
    available = []
    for row in rows:
        used = conn.execute(
            """
            SELECT COUNT(*) AS n FROM orders
            WHERE slot_id = ? AND status != 'cancelled'
            """,
            (row["id"],),
        ).fetchone()["n"]
        if used < row["capacity"]:
            available.append(row)
    return available


DEFAULT_SLOT_CAPACITY = 4


def ensure_upcoming_slots(conn, days=14, clock=None):
    """Ouvre les créneaux manquants sur les horaires publiés. La capacité reprend le dernier créneau enregistré."""
    sample = conn.execute("SELECT capacity FROM pickup_slots ORDER BY id DESC LIMIT 1").fetchone()
    capacity = int(sample["capacity"]) if sample and int(sample["capacity"]) > 0 else DEFAULT_SLOT_CAPACITY
    hours = load_json_setting(conn, "hours", DEFAULT_HOURS)
    moment = now_paris(clock)
    created = 0
    for offset in range(days):
        day = moment.date() + timedelta(days=offset)
        key = day.isoformat()
        if conn.execute("SELECT 1 FROM pickup_slots WHERE slot_date = ?", (key,)).fetchone():
            continue
        window = hours["sun"] if day.weekday() == 6 else hours["mon_sat"]
        minute = minutes(window[0])
        end = minutes(window[1])
        while minute + 30 <= end:
            start = f"{minute // 60:02d}:{minute % 60:02d}"
            finish_m = minute + 30
            finish = f"{finish_m // 60:02d}:{finish_m % 60:02d}"
            if slot_inside_hours(key, start, finish, hours):
                conn.execute(
                    """
                    INSERT INTO pickup_slots (slot_date, start_time, end_time, capacity, active)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (key, start, finish, capacity),
                )
                created += 1
            minute += 30
    return created


def slot_board(conn, day):
    slots = conn.execute(
        """
        SELECT * FROM pickup_slots
        WHERE slot_date >= ?
        ORDER BY slot_date, start_time, id
        """,
        (day,),
    ).fetchall()
    board = []
    for slot in slots:
        booked = conn.execute(
            """
            SELECT public_ref, customer_name, status
            FROM orders
            WHERE slot_id = ? AND status != 'cancelled'
            ORDER BY id
            """,
            (slot["id"],),
        ).fetchall()
        board.append(
            {
                "slot": slot,
                "used": len(booked),
                "remaining": max(int(slot["capacity"]) - len(booked), 0),
                "orders": booked,
            }
        )
    return board


def slot_remaining(conn, slot_id):
    slot = conn.execute("SELECT * FROM pickup_slots WHERE id = ?", (slot_id,)).fetchone()
    if not slot or not slot["active"]:
        return None, 0
    used = conn.execute(
        "SELECT COUNT(*) AS n FROM orders WHERE slot_id = ? AND status != 'cancelled'",
        (slot_id,),
    ).fetchone()["n"]
    return slot, slot["capacity"] - used


def cart_totals(conn, session_id, clock=None):
    cart, lines = cart_lines(conn, session_id, clock=clock)
    issues = []
    subtotal = 0
    priced = True
    for _item, quote in lines:
        if quote.issues or quote.line_cents is None:
            priced = False
            issues.extend(quote.issues)
        else:
            subtotal += quote.line_cents
    discount = 0
    promo_error = None
    code = cart["promo_code"] if cart else None
    if priced and lines and code:
        discount, _applied, promo_error = apply_promo(conn, code, subtotal)
        if promo_error:
            discount = 0
    return {
        "cart": cart,
        "lines": lines,
        "subtotal": subtotal if priced and lines else None,
        "discount": discount if priced and lines else 0,
        "issues": issues,
        "promo_error": promo_error,
        "priced": priced and bool(lines),
    }


def _customer_errors(name, email, phone):
    errors = []
    name = (name or "").strip()
    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    if len(name) < 2 or len(name) > 80:
        errors.append("Indiquez votre nom.")
    if "@" not in email or "." not in email.split("@")[-1]:
        errors.append("Indiquez une adresse e-mail valide.")
    digits = [char for char in phone if char.isdigit()]
    if not (8 <= len(digits) <= 15):
        errors.append("Indiquez un numero de telephone.")
    return errors, name, email, phone


def place_order(conn, session_id, user_id, form, clock=None):
    key = (form.get("idempotency_key") or "").strip()
    if not key:
        return None, ["La commande n'a pas pu etre securisee. Rechargez la page."]
    existing = conn.execute(
        "SELECT * FROM orders WHERE idempotency_key = ?",
        (key,),
    ).fetchone()
    if existing:
        if existing["session_id"] == session_id or (user_id and existing["user_id"] == user_id):
            return existing, []
        return None, ["Cette confirmation ne correspond pas a votre session."]

    totals = cart_totals(conn, session_id, clock=clock)
    errors = []
    if not totals["lines"]:
        errors.append("Votre panier est vide.")
    if totals["issues"]:
        errors.extend(dict.fromkeys(totals["issues"]))
    if not totals["priced"]:
        errors.append("Le total ne peut pas etre calcule tant que des prix restent a valider.")

    customer_errors, name, email, phone = _customer_errors(
        form.get("nom"), form.get("email"), form.get("telephone")
    )
    errors.extend(customer_errors)

    mode = form.get("mode")
    if mode not in {"pickup", "delivery"}:
        errors.append("Choisissez le retrait ou la livraison.")

    moment = now_paris(clock)
    hours = load_json_setting(conn, "hours", {"mon_sat": ["11:30", "22:30"], "sun": ["17:00", "22:30"]})
    point_id = None
    slot_id = None
    zone_id = None
    address = None
    fee = 0

    distance_meters = None
    if mode == "delivery":
        if not is_open(moment, hours):
            errors.append(f"La livraison n'est pas prise en ce moment. {hours_label(hours)}.")
        from app.delivery import delivery_mode, quote_delivery

        street = (form.get("rue") or "").strip()
        postcode = (form.get("code_postal") or "").strip()
        city = (form.get("ville") or "").strip()
        address_ok = True
        if len(street) < 4:
            errors.append("Indiquez la rue." if not street else "La rue est trop courte.")
            address_ok = False
        if len(postcode) < 4:
            errors.append("Indiquez le code postal." if not postcode else "Le code postal est incomplet.")
            address_ok = False
        if len(city) < 2:
            errors.append("Indiquez la ville.")
            address_ok = False
        if delivery_mode(conn) == "distance":
            if address_ok:
                quote, quote_error = quote_delivery(
                    conn,
                    {"rue": street, "code_postal": postcode, "ville": city},
                )
                if quote_error:
                    errors.append(quote_error)
                else:
                    fee = int(quote["fee_cents"])
                    distance_meters = int(quote["meters"])
        else:
            zones = active_zones(conn)
            if not zones:
                errors.append("Aucune zone de livraison n'est configuree par le restaurant.")
            else:
                try:
                    zone_id = int(form.get("zone_id") or 0)
                except ValueError:
                    zone_id = 0
                zone = next((item for item in zones if item["id"] == zone_id), None)
                if not zone:
                    errors.append("Choisissez une zone de livraison proposee par le restaurant.")
                    zone_id = None
                else:
                    fee = int(zone["fee_cents"])
        address = {"rue": street, "code_postal": postcode, "ville": city}
        raw_slot = str(form.get("slot_id") or "").strip()
        if raw_slot:
            slots = open_slots(conn, clock=clock)
            try:
                chosen = int(raw_slot)
            except ValueError:
                chosen = 0
            slot = next((item for item in slots if item["id"] == chosen), None)
            if not slot:
                errors.append("Choisissez un creneau encore disponible.")
            elif not slot_inside_hours(slot["slot_date"], slot["start_time"], slot["end_time"], hours):
                errors.append("Ce creneau est en dehors des horaires du restaurant.")
            else:
                slot_id = slot["id"]

    if mode == "pickup":
        points = active_points(conn)
        if len(points) == 1:
            point_id = points[0]["id"]
        else:
            try:
                point_id = int(form.get("point_id") or 0)
            except ValueError:
                point_id = 0
            if not any(point["id"] == point_id for point in points):
                errors.append("Choisissez un point de retrait.")
                point_id = None
        slots = open_slots(conn, clock=clock)
        if not slots:
            errors.append("Aucun creneau de retrait n'est ouvert. Le restaurant doit les configurer.")
        else:
            try:
                slot_id = int(form.get("slot_id") or 0)
            except ValueError:
                slot_id = 0
            slot = next((item for item in slots if item["id"] == slot_id), None)
            if not slot:
                errors.append("Choisissez un creneau encore disponible.")
                slot_id = None
            elif not slot_inside_hours(slot["slot_date"], slot["start_time"], slot["end_time"], hours):
                errors.append("Ce creneau est en dehors des horaires du restaurant.")
                slot_id = None

    from app.stripe_pay import stripe_ready

    methods = active_payment_methods(conn)
    method_code = (form.get("paiement") or "").strip()
    method = next((item for item in methods if item["code"] == method_code), None)
    ready, ready_error = stripe_ready(conn)
    if mode == "pickup":
        if method_code != "stripe":
            errors.append("Le Click & Collect se règle par carte.")
        elif not ready:
            errors.append(ready_error or "Le paiement en ligne n'est pas configuré.")
        else:
            method = {"code": "stripe"}
    elif method_code == "stripe" and ready:
        method = {"code": "stripe"}
    elif method_code == "stripe":
        errors.append(ready_error or "Le paiement en ligne n'est pas configuré.")
    elif not methods:
        errors.append("Aucun moyen de reglement n'est active. Le paiement en ligne n'est pas branche.")
    elif not method:
        errors.append("Choisissez un moyen de reglement propose par le restaurant.")

    terms = load_json_setting(conn, "terms_text", "")
    if isinstance(terms, str) and terms.strip() and form.get("conditions") != "1":
        errors.append("Acceptez les conditions publiees par le restaurant.")

    if errors:
        return None, list(dict.fromkeys(errors))

    subtotal = totals["subtotal"]
    discount = totals["discount"]
    total = subtotal - discount + fee
    if method and method["code"] == "stripe" and total < 50:
        return None, ["Le montant est inférieur au minimum accepté pour un paiement en ligne."]
    snapshot = []
    for item, quote in totals["lines"]:
        snapshot.append(
            {
                "product_id": quote.product["id"],
                "name": quote.product["name"],
                "quantity": quote.quantity,
                "unit_cents": quote.unit_cents,
                "line_cents": quote.line_cents,
                "options": quote.summary,
                "notes": quote.notes,
            }
        )

    conn.execute("BEGIN IMMEDIATE")
    try:
        if mode == "delivery" and delivery_mode(conn) == "distance":
            quote, quote_error = quote_delivery(
                conn,
                {"rue": address["rue"], "code_postal": address["code_postal"], "ville": address["ville"]},
            )
            if quote_error:
                conn.execute("ROLLBACK")
                return None, [quote_error]
            fee = int(quote["fee_cents"])
            distance_meters = int(quote["meters"])
            zone_id = None
            total = subtotal - discount + fee
        elif mode == "delivery":
            zone = conn.execute(
                """
                SELECT * FROM delivery_zones
                WHERE id = ? AND active = 1 AND fee_confirmed = 1 AND fee_cents IS NOT NULL
                """,
                (zone_id,),
            ).fetchone()
            if not zone:
                conn.execute("ROLLBACK")
                return None, ["La zone de livraison n'est plus disponible."]
            fee = int(zone["fee_cents"])
            total = subtotal - discount + fee
        if method["code"] == "stripe":
            still_ready, still_error = stripe_ready(conn)
            if not still_ready:
                conn.execute("ROLLBACK")
                return None, [still_error or "Le paiement en ligne n'est pas configuré."]
        else:
            method_row = conn.execute(
                "SELECT * FROM payment_methods WHERE code = ? AND active = 1",
                (method["code"],),
            ).fetchone()
            if not method_row:
                conn.execute("ROLLBACK")
                return None, ["Ce moyen de reglement n'est plus disponible."]
        if slot_id:
            _slot, remaining = slot_remaining(conn, slot_id)
            if remaining < 1:
                conn.execute("ROLLBACK")
                return None, ["Ce creneau vient d'etre complet."]
        public_ref = _new_ref(conn)
        cur = conn.execute(
            """
            INSERT INTO orders (
              public_ref, user_id, session_id, status, mode, customer_name, email, phone,
              address_json, pickup_point_id, slot_id, zone_id, payment_method, payment_status,
              subtotal_cents, delivery_fee_cents, discount_cents, total_cents, promo_code,
              idempotency_key, snapshot_json, created_at
            ) VALUES (?, ?, ?, 'received', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                public_ref,
                user_id,
                session_id,
                mode,
                name,
                email,
                phone,
                json.dumps(address, ensure_ascii=False) if address else None,
                point_id,
                slot_id,
                zone_id,
                method["code"],
                "pending" if method["code"] == "stripe" else "unpaid",
                subtotal,
                fee,
                discount,
                total,
                totals["cart"]["promo_code"] if discount else None,
                key,
                json.dumps(snapshot, ensure_ascii=False),
                iso(utc_now()),
            ),
        )
        order_id = cur.lastrowid
        conn.execute(
            "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'received', ?)",
            (order_id, iso(utc_now())),
        )
        if distance_meters is not None:
            conn.execute("UPDATE orders SET distance_meters = ? WHERE id = ?", (distance_meters, order_id))
        clear_cart(conn, totals["cart"]["id"])
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        again = conn.execute(
            "SELECT * FROM orders WHERE idempotency_key = ?",
            (key,),
        ).fetchone()
        if again:
            return again, []
        raise
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    from app.notify import record

    record(conn, order["id"], "received")
    return order, []


def _new_ref(conn):
    for _ in range(5):
        ref = "AK-" + secrets.token_hex(4).upper()
        if not conn.execute("SELECT 1 FROM orders WHERE public_ref = ?", (ref,)).fetchone():
            return ref
    raise RuntimeError("reference")


def order_for_session(conn, public_ref, session_id, user_id):
    row = conn.execute("SELECT * FROM orders WHERE public_ref = ?", (public_ref,)).fetchone()
    if not row:
        return None
    if row["session_id"] == session_id or (user_id and row["user_id"] == user_id):
        return row
    return None


def orders_for_user(conn, user_id):
    return conn.execute(
        "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()


def orders_for_viewer(conn, session_id, user_id, limit=5):
    if user_id:
        return conn.execute(
            """SELECT * FROM orders
               WHERE session_id = ? OR user_id = ?
               ORDER BY id DESC LIMIT ?""",
            (session_id, user_id, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM orders WHERE session_id = ? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    ).fetchall()


def order_events(conn, order_id):
    return conn.execute(
        "SELECT * FROM order_events WHERE order_id = ? ORDER BY id",
        (order_id,),
    ).fetchall()


def set_status(conn, order_id, status):
    if status not in KITCHEN_STATUSES:
        return "Statut inconnu."
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        return "Commande introuvable."
    if status == "out_for_delivery" and order["mode"] != "delivery":
        return "Ce statut concerne uniquement la livraison."
    if status == order["status"]:
        return None
    conn.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.execute(
        "INSERT INTO order_events (order_id, status, created_at) VALUES (?, ?, ?)",
        (order_id, status, iso(utc_now())),
    )
    from app.notify import record

    record(conn, order_id, status)
    return None


def slot_takes_capacity(status):
    return status in ACTIVE_STATUSES or status != "cancelled"


def payment_summary(order):
    method = METHOD_LABELS.get(order["payment_method"], order["payment_method"])
    state = PAY_LABELS.get(order["payment_status"], order["payment_status"])
    return f"{state} · {method}"


def orders_sheet(conn, only_open=False, status=None, day=None):
    where = ""
    if only_open:
        marks = ",".join("?" for _ in OPEN_STATUSES)
        where = f"WHERE o.status IN ({marks})"
    rows = conn.execute(
        f"""
        SELECT o.*, s.slot_date, s.start_time, s.end_time, z.name AS zone_name, p.name AS point_name
        FROM orders o
        LEFT JOIN pickup_slots s ON s.id = o.slot_id
        LEFT JOIN delivery_zones z ON z.id = o.zone_id
        LEFT JOIN pickup_points p ON p.id = o.pickup_point_id
        {where}
        ORDER BY {('o.created_at, o.id' if only_open else 'o.id DESC')}
        """,
        OPEN_STATUSES if only_open else (),
    ).fetchall()
    if status:
        rows = [row for row in rows if row["status"] == status]
    if day:
        rows = [row for row in rows if _order_day(row["created_at"]) == day]
    return rows


def when_label(order):
    if order["mode"] == "pickup" and order["slot_date"]:
        return f"Retrait · {order['slot_date']} {order['start_time']}–{order['end_time']}"
    if order["mode"] == "delivery" and order["slot_date"]:
        return f"Livraison · {order['slot_date']} {order['start_time']}–{order['end_time']}"
    if order["mode"] == "delivery":
        zone = order["zone_name"] or "Adresse"
        return f"Livraison · {zone}"
    return "Retrait"


def place_label(order):
    if order["mode"] == "pickup":
        return order["point_name"] or "Au restaurant"
    if not order["address_json"]:
        return ""
    try:
        data = json.loads(order["address_json"])
    except json.JSONDecodeError:
        return ""
    return ", ".join(
        part for part in (data.get("rue"), f"{data.get('code_postal', '')} {data.get('ville', '')}".strip()) if part
    )


def _order_day(created_at):
    try:
        moment = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return ""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(PARIS).date().isoformat()


def dashboard_stats(conn, clock=None):
    day = now_paris(clock).date().isoformat()
    counts = {key: 0 for key in KITCHEN_STATUSES}
    today = open_count = pickup = delivery = 0
    collected = due = 0
    for order in conn.execute("SELECT status, mode, payment_status, total_cents, created_at FROM orders"):
        status = order["status"]
        if status in counts:
            counts[status] += 1
        kept = status != "cancelled"
        if _order_day(order["created_at"]) == day:
            today += 1
        if status in OPEN_STATUSES:
            open_count += 1
        if kept and order["mode"] == "pickup":
            pickup += 1
        if kept and order["mode"] == "delivery":
            delivery += 1
        if kept and order["payment_status"] == "paid":
            collected += int(order["total_cents"])
        elif kept and order["payment_status"] in {"unpaid", "pending"}:
            due += int(order["total_cents"])
    return {
        "day": day,
        "today": today,
        "open": open_count,
        "pickup": pickup,
        "delivery": delivery,
        "collected_cents": collected,
        "due_cents": due,
        "counts": counts,
        "missing_prices": conn.execute(
            "SELECT COUNT(*) AS n FROM products WHERE price_confirmed = 0 OR price_cents IS NULL"
        ).fetchone()["n"],
        "sellable": conn.execute(
            """
            SELECT COUNT(*) AS n FROM products
            WHERE price_confirmed = 1 AND price_cents IS NOT NULL AND available = 1 AND orderable = 1
            """
        ).fetchone()["n"],
        "zones": conn.execute("SELECT COUNT(*) AS n FROM delivery_zones WHERE active = 1").fetchone()["n"],
        "slots": conn.execute("SELECT COUNT(*) AS n FROM pickup_slots WHERE active = 1").fetchone()["n"],
        "slots_today": conn.execute(
            "SELECT COUNT(*) AS n FROM pickup_slots WHERE active = 1 AND slot_date = ?",
            (day,),
        ).fetchone()["n"],
        "payments": conn.execute("SELECT COUNT(*) AS n FROM payment_methods WHERE active = 1").fetchone()["n"],
    }


def mark_collected(conn, order_id):
    order = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
    if not order:
        return "Commande introuvable."
    if order["payment_method"] not in COUNTER_METHODS:
        return "Le paiement en ligne se confirme auprès de Stripe, pas depuis ce bouton."
    if order["payment_status"] == "paid":
        return None
    conn.execute("UPDATE orders SET payment_status = 'paid' WHERE id = ?", (order_id,))
    conn.execute(
        "INSERT INTO order_events (order_id, status, created_at) VALUES (?, 'paid', ?)",
        (order_id, iso(utc_now())),
    )
    return None
