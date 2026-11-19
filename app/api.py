import json
import urllib.parse

from app.auth import authenticate, destroy_session, register_customer, rotate_session, set_idempotency_key
from app.cart import add_item, cart_count, remove_item, set_promo, update_quantity
from app.catalog import featured_products, groups_for_product, list_products, product_by_slug
from app.delivery import customer_delivery_open
from app.money import format_eur
from app.orders import (
    STATUS_LABELS,
    active_points,
    active_zones,
    cart_totals,
    open_slots,
    order_for_session,
    orders_for_user,
    orders_for_viewer,
    place_order,
)
from app.stripe_pay import (
    _request,
    begin_checkout,
    cancel_payment,
    checkout_methods,
    ensure_order_from_checkout,
    limited,
    payment_view,
    retry_payment,
    stripe_configured,
    verify_return,
)
from app.schedule import hours_label, load_json_setting
from app.db import ROOT
from app import reviews as review_store
from app.ui import price_label


MAPS = "https://www.google.com/maps/dir/?api=1&destination=24+rue+Emmanuel+Arago+93130+Noisy-le-Sec"
INSTAGRAM = "https://www.instagram.com/alloko_drone/"
REVIEW = {
    "quote": "Une vraie découverte ! Les saveurs sont au rendez-vous, le pulled beef yassa est incroyable et l'accueil est top.",
    "author": "Sarah",
    "place": "Noisy-le-Sec",
    "source": "Google",
    "reviews": [
        {
            "quote": "Une vraie découverte ! Les saveurs sont au rendez-vous, le pulled beef yassa est incroyable et l'accueil est top.",
            "author": "Sarah",
        },
        {
            "quote": "Impecable",
            "author": "Ibrahim",
        },
    ],
}


def json_response(data, status=200, headers=None):
    from app.server import Response

    body = json.dumps(data, ensure_ascii=False)
    return Response(status, body, headers=headers, content_type="application/json; charset=utf-8")


def dispatch_api(ctx, method, path, query, payload):
    if not path.startswith("/api/"):
        return None
    payload = payload or {}
    if path == "/api/promotions/active" and method == "GET":
        from app.promo_popups import get_active_promotion

        page = (query.get("page") or [""])[0]
        return json_response({"promotion": get_active_promotion(ctx.conn, page)})
    if path.startswith("/api/promotions/images/") and method == "GET":
        from app.promo_popups import image_by_id
        from app.server import Response

        image_id = path.rsplit("/", 1)[-1]
        image = image_by_id(ctx.conn, image_id)
        if not image:
            return Response(404, "Image introuvable.")
        return Response(
            200,
            image["data"],
            headers=[("Cache-Control", "public, max-age=86400")],
            content_type=image["mime_type"],
        )
    if path == "/api/promotions/event" and method == "POST":
        from app.promo_popups import record_event

        try:
            promo_id = int(payload.get("id") or 0)
        except (TypeError, ValueError):
            return json_response({"error": "Promotion invalide."}, 400)
        if not record_event(ctx.conn, promo_id, ctx.session["id"] if ctx.session else "", payload.get("event")):
            return json_response({"ok": True})
        return json_response({"ok": True})
    if path.startswith("/api/admin/promotions"):
        from app.promo_popups import (
            delete_promotion,
            duplicate_promotion,
            list_promotions,
            save_promotion,
            store_image,
            toggle_promotion,
        )

        if not ctx.user or ctx.user["role"] != "admin":
            return json_response({"error": "Accès réservé aux administrateurs."}, 403)
        if path == "/api/admin/promotions" and method == "GET":
            return json_response({"promotions": list_promotions(ctx.conn)})
        if path == "/api/admin/promotions" and method == "POST":
            promo, error = save_promotion(ctx.conn, payload)
            if error:
                return json_response({"error": error}, 400)
            return json_response({"promotion": promo}, 201)
        if path == "/api/admin/promotions/upload" and method == "POST":
            upload = payload.get("_upload") or {}
            if payload.get("_upload_error"):
                return json_response({"error": payload["_upload_error"]}, 400)
            image, error = store_image(ctx.conn, upload.get("data"), upload.get("mime_type"))
            if error:
                return json_response({"error": error}, 400)
            return json_response(image, 201)
        parts = path.split("/")
        if len(parts) == 5 and parts[4].isdigit():
            promo_id = int(parts[4])
            if method == "POST" and len(parts) == 5:
                promo, error = save_promotion(ctx.conn, payload, promo_id)
                if error:
                    return json_response({"error": error}, 404 if error == "Promotion introuvable." else 400)
                return json_response({"promotion": promo})
        if len(parts) == 6 and parts[4].isdigit():
            promo_id = int(parts[4])
            action = parts[5]
            if method == "POST" and action == "toggle":
                promo = toggle_promotion(ctx.conn, promo_id, payload.get("actif"))
                return json_response({"promotion": promo}, 200 if promo else 404)
            if method == "POST" and action == "duplicate":
                promo = duplicate_promotion(ctx.conn, promo_id)
                return json_response({"promotion": promo}, 201 if promo else 404)
            if method == "POST" and action == "delete":
                return json_response({"ok": delete_promotion(ctx.conn, promo_id)}, 200)
    if path == "/api/session" and method == "GET":
        return json_response(_session(ctx))
    if path == "/api/avis" and method == "GET":
        return json_response(_reviews(ctx, query))
    if path == "/api/avis" and method == "POST":
        return _post_review(ctx, payload)
    if path == "/api/avis/eligibilite" and method == "GET":
        return json_response(_review_eligibility(ctx, query))
    if path.startswith("/api/avis/") and method == "PATCH":
        review_id = _review_id(path)
        if review_id is None:
            return json_response({"error": "Introuvable."}, 404)
        return _patch_review(ctx, review_id, payload)
    if path.startswith("/api/avis/") and method == "DELETE":
        review_id = _review_id(path)
        if review_id is None:
            return json_response({"error": "Introuvable."}, 404)
        return _delete_review(ctx, review_id)
    if path.startswith("/api/avis/") and path.endswith("/utile") and method == "POST":
        review_id = _review_id(path, suffix="utile")
        if review_id is None:
            return json_response({"error": "Introuvable."}, 404)
        return _useful_review(ctx, review_id)
    if path.startswith("/api/avis/") and path.endswith("/signaler") and method == "POST":
        review_id = _review_id(path, suffix="signaler")
        if review_id is None:
            return json_response({"error": "Introuvable."}, 404)
        return _report_review(ctx, review_id, payload)
    if path == "/api/accueil" and method == "GET":
        return json_response(_home(ctx))
    if path == "/api/catalogue" and method == "GET":
        return json_response(_catalog(ctx, query))
    if path.startswith("/api/produit/") and method == "GET":
        slug = path.split("/")[3] if len(path.split("/")) > 3 else ""
        data = _product(ctx, slug)
        if not data:
            return json_response({"error": "Produit introuvable."}, 404)
        return json_response(data)
    if path == "/api/panier" and method == "GET":
        return json_response(_cart(ctx))
    if path == "/api/panier/ajouter" and method == "POST":
        return _add(ctx, payload)
    if path == "/api/panier/modifier" and method == "POST":
        return _update(ctx, payload)
    if path == "/api/panier/supprimer" and method == "POST":
        return _remove(ctx, payload)
    if path == "/api/panier/code" and method == "POST":
        set_promo(ctx.conn, ctx.session["id"], payload.get("code") or "")
        data = _cart(ctx)
        data["ok"] = True
        return json_response(data)
    if path == "/api/commander" and method == "GET":
        return json_response(_checkout(ctx))
    if path == "/api/livraison/estimer" and method == "POST":
        return _estimate(ctx, payload)
    if path == "/api/livraison/localisation" and method == "POST":
        return _locate(ctx, payload)
    if path == "/api/commander" and method == "POST":
        return _order(ctx, payload)
    if path == "/api/paiement/verifier" and method == "POST":
        return _verify_payment(ctx, payload)
    if path == "/api/paiement/annuler" and method == "POST":
        return _cancel_payment(ctx, payload)
    if path == "/api/paiement/reessayer" and method == "POST":
        return _retry_payment(ctx, payload)
    if path.startswith("/api/commande/") and path.endswith("/pdf") and method == "GET":
        parts = path.split("/")
        ref = parts[3] if len(parts) == 5 else ""
        return _order_pdf(ctx, ref)
    if path.startswith("/api/commande/") and method == "GET":
        ref = path.split("/")[3] if len(path.split("/")) > 3 else ""
        data = _confirmation(ctx, ref)
        if not data:
            return json_response({"error": "Commande introuvable."}, 404)
        return json_response(data)
    if path == "/api/compte" and method == "GET":
        return json_response(_account(ctx))
    if path == "/api/compte/connexion" and method == "POST":
        return _login(ctx, payload)
    if path == "/api/compte/inscription" and method == "POST":
        return _register(ctx, payload)
    if path == "/api/compte/deconnexion" and method == "POST":
        destroy_session(ctx.conn, ctx.session["id"])
        return json_response({"ok": True}, headers=[("Set-Cookie", "sid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0")])
    return json_response({"error": "Introuvable."}, 404)


def _plain(value, limit):
    if not isinstance(value, str):
        return ""
    return " ".join(value.replace("\x00", " ").split())[:limit]


def _query_one(query, key):
    values = query.get(key) if query else None
    if not values:
        return None
    return values[0]


def _review_id(path, suffix=None):
    parts = path.strip("/").split("/")
    if len(parts) < 3 or parts[0] != "api" or parts[1] != "avis":
        return None
    if suffix and (len(parts) != 4 or parts[3] != suffix):
        return None
    if not suffix and len(parts) != 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def _reviews(ctx, query=None):
    note_raw = _query_one(query, "note")
    try:
        note = int(note_raw) if note_raw not in (None, "") else None
    except ValueError:
        note = None
    sort = _query_one(query, "tri") or "date"
    try:
        page = int(_query_one(query, "page") or 1)
    except ValueError:
        page = 1
    data = review_store.board(
        ctx.conn,
        note=note,
        sort=sort,
        page=page,
        session_id=ctx.session["id"],
        user_id=ctx.user["id"] if ctx.user else None,
    )
    data["google"] = REVIEW
    return data


def _post_review(ctx, payload):
    item, errors = review_store.create_from_order(
        ctx.conn,
        payload,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
    )
    if errors:
        status = 429 if any("Trop" in error for error in errors) else 422
        return json_response({"ok": False, "errors": errors}, status)
    data = _reviews(ctx, {})
    data["ok"] = True
    data["review"] = item
    return json_response(data)


def _patch_review(ctx, review_id, payload):
    item, errors = review_store.update_review(
        ctx.conn,
        review_id,
        payload,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
    )
    if errors:
        return json_response({"ok": False, "errors": errors}, 422)
    return json_response({"ok": True, "review": item})


def _delete_review(ctx, review_id):
    errors = review_store.delete_review(
        ctx.conn,
        review_id,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
    )
    if errors:
        return json_response({"ok": False, "errors": errors}, 422)
    return json_response({"ok": True})


def _useful_review(ctx, review_id):
    data, error = review_store.mark_useful(ctx.conn, review_id, ctx.session["id"])
    if error:
        return json_response({"ok": False, "errors": [error]}, 404)
    data["ok"] = True
    return json_response(data)


def _report_review(ctx, review_id, payload):
    errors = review_store.report_review(
        ctx.conn,
        review_id,
        ctx.session["id"],
        payload.get("motif") or payload.get("reason") or "",
    )
    if errors:
        status = 429 if any("Trop" in error for error in errors) else 422
        return json_response({"ok": False, "errors": errors}, status)
    return json_response({"ok": True})


def _review_eligibility(ctx, query):
    ref = _query_one(query, "ref") or ""
    order, error = review_store.reviewable_order(
        ctx.conn,
        ref,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
    )
    if error:
        return {"canReview": False, "reason": error, "orderRef": ref or None}
    return {
        "canReview": True,
        "orderRef": order["public_ref"],
        "customerName": order["customer_name"],
        "mode": order["mode"],
    }


def _session(ctx):
    user = _public_user(ctx.user)
    return {
        "csrf": ctx.session["csrf"],
        "user": user,
        "cartCount": cart_count(ctx.conn, ctx.session["id"]),
        "latestOrderRef": _latest_order_ref(ctx),
        "restaurant": _restaurant(ctx),
        "slots": _slot_rows(ctx),
        "points": _point_rows(ctx),
    }


def _latest_order_ref(ctx):
    rows = orders_for_viewer(ctx.conn, ctx.session["id"], ctx.user["id"] if ctx.user else None, limit=1)
    if not rows:
        return None
    return rows[0]["public_ref"]


def _public_user(user):
    if not user:
        return None
    return {
        "name": user["name"],
        "email": user["email"],
        "phone": user["phone"] or "",
        "role": user["role"],
    }


def _restaurant(ctx):
    hours = load_json_setting(ctx.conn, "hours", {"mon_sat": ["11:30", "22:30"], "sun": ["17:00", "22:30"]})
    points = active_points(ctx.conn)
    address = points[0]["address"] if points else "24 rue Emmanuel Arago, 93130 Noisy-le-Sec"
    def clock(value):
        return str(value).replace(":", "h")

    week = hours.get("mon_sat") or ["11:30", "22:30"]
    sunday = hours.get("sun") or ["17:00", "22:30"]
    return {
        "name": points[0]["name"] if points else "ALLOKODRONE",
        "address": address,
        "hoursLabel": hours_label(hours),
        "hoursLines": [
            f"Lundi – samedi · {clock(week[0])} – {clock(week[1])}",
            f"Dimanche · {clock(sunday[0])} – {clock(sunday[1])}",
        ],
        "deliveryOpen": customer_delivery_open(ctx.conn),
        "instagram": INSTAGRAM,
        "maps": MAPS,
        "review": REVIEW,
        "offer": "Boisson offerte en Click & Collect",
    }


def _home(ctx):
    counts = _category_rows(ctx.conn)
    board = review_store.board(
        ctx.conn,
        sort="pertinence",
        page=1,
        session_id=ctx.session["id"],
        user_id=ctx.user["id"] if ctx.user else None,
    )
    return {
        "featured": [_summary(ctx.conn, row) for row in featured_products(ctx.conn)],
        "categories": counts,
        "restaurant": _restaurant(ctx),
        "signatureVideo": _signature_video(),
        "avis": {
            "average": board["average"],
            "count": board["count"],
            "histogram": board["histogram"],
            "reviews": board["reviews"][:3],
        },
    }


def _signature_video():
    for ext in ("mp4", "webm"):
        if (ROOT / "videos" / f"signature.{ext}").is_file():
            return f"/videos/signature.{ext}"
    return None


def _catalog(ctx, query):
    slug = (query.get("categorie") or [""])[0]
    text = (query.get("q") or [""])[0]
    products = list_products(ctx.conn, slug or None, text or None)
    return {
        "categories": _category_rows(ctx.conn),
        "category": slug,
        "query": text,
        "products": [_summary(ctx.conn, row) for row in products],
    }


CATEGORY_COPY = {
    "burgers": "DKR Beef, Kankan Burger et DKR Chicken, sauces yassa et arachide.",
    "bowls": "Base, viande, sauce et side au choix. Riz blanc inclus, riz Jollof +1 €.",
    "sides": "Accras, Spice Wings, Alloko, Suya Fries et rougail tomates.",
    "plats": "BKO Mafé, DKR Yassa et Lagos Bowl, à composer selon vos envies.",
    "boissons": "Cocktails & specials, OG Classics, cannettes et eaux.",
    "desserts": "Dekiri et cakes maison : banana bread, yam cake, choco-manioc.",
    "midi": "Bowl + boisson, combo étudiant + boisson, et Spice Wings Combo.",
}

CATEGORY_FALLBACK_IMAGE = {
    "burgers": "burger.jpg",
    "bowls": "bowl.jpg",
    "sides": "wings.jpg",
    "plats": "bowl.jpg",
    "boissons": "alloko.jpg",
    "desserts": "alloko.jpg",
    "midi": "bowl.jpg",
}


def _category_rows(conn):
    rows = conn.execute(
        """
        SELECT c.slug, c.name, COUNT(p.id) AS n,
          (
            SELECT p2.image FROM products p2
            WHERE p2.category_id = c.id
              AND p2.image IS NOT NULL
              AND TRIM(p2.image) != ''
            ORDER BY p2.featured DESC, p2.sort_order, p2.id
            LIMIT 1
          ) AS image
        FROM categories c
        LEFT JOIN products p ON p.category_id = c.id
        GROUP BY c.id
        ORDER BY c.sort_order, c.id
        """
    ).fetchall()
    items = []
    for row in rows:
        image = row["image"] or CATEGORY_FALLBACK_IMAGE.get(row["slug"])
        if image and not (ROOT / "images" / image).is_file():
            image = None
        items.append(
            {
                "slug": row["slug"],
                "name": row["name"],
                "count": row["n"],
                "description": CATEGORY_COPY.get(row["slug"], ""),
                "image": f"/images/{image}" if image else None,
            }
        )
    return items


def _product_image(row):
    image = row["image"] if row["image"] and str(row["image"]).strip() else None
    if not image:
        image = CATEGORY_FALLBACK_IMAGE.get(row["category_slug"])
    if image and not (ROOT / "images" / image).is_file():
        return None
    return f"/images/{image}" if image else None


def _summary(conn, row):
    image = _product_image(row)
    video = None
    for ext in ("mp4", "webm"):
        if (ROOT / "videos" / f"{row['slug']}.{ext}").is_file():
            video = f"/videos/{row['slug']}.{ext}"
            break
    confirmed = bool(row["price_confirmed"]) and row["price_cents"] is not None
    if not row["available"]:
        availability = "Indisponible"
    elif not row["orderable"]:
        availability = row["block_reason"] or "Composition à valider par le restaurant."
    else:
        availability = ""
    return {
        "id": row["id"],
        "slug": row["slug"],
        "name": row["name"],
        "description": row["description"],
        "image": image,
        "video": video,
        "categorySlug": row["category_slug"],
        "categoryName": row["category_name"],
        "priceLabel": price_label(row),
        "priceCents": row["price_cents"] if confirmed else None,
        "priceConfirmed": confirmed,
        "available": bool(row["available"]),
        "orderable": bool(row["orderable"]),
        "availability": availability,
        "featured": bool(row["featured"]),
        "hasOptions": conn.execute(
            "SELECT 1 FROM option_groups WHERE product_id = ? LIMIT 1",
            (row["id"],),
        ).fetchone()
        is not None,
    }


def _product(ctx, slug):
    item = product_by_slug(ctx.conn, slug)
    if not item:
        return None
    groups = []
    for group, choices in groups_for_product(ctx.conn, item["id"]):
        options = []
        for choice in choices:
            confirmed = bool(choice["price_delta_confirmed"]) and choice["price_delta_cents"] is not None
            if not confirmed:
                extra = "supplément à valider"
            elif choice["price_delta_cents"] == 0:
                extra = "inclus"
            else:
                extra = "+" + format_eur(choice["price_delta_cents"])
            options.append(
                {
                    "id": choice["id"],
                    "name": choice["name"],
                    "extra": extra,
                    "deltaCents": choice["price_delta_cents"] if confirmed else None,
                    "deltaConfirmed": confirmed,
                    "available": bool(choice["available"]),
                }
            )
        groups.append(
            {
                "id": group["id"],
                "name": group["name"],
                "required": bool(group["required"]),
                "choices": options,
            }
        )
    return {
        "product": _summary(ctx.conn, item),
        "groups": groups,
        "allowNotes": bool(load_json_setting(ctx.conn, "allow_notes", 0)),
    }


def _money(cents):
    if cents is None:
        return "Prix à valider"
    return format_eur(cents)


def _cart(ctx):
    totals = cart_totals(ctx.conn, ctx.session["id"])
    lines = []
    for item, quote in totals["lines"]:
        name = quote.product["name"] if quote.product else "Produit retiré"
        image = None
        slug = ""
        if quote.product and quote.product["image"]:
            image = f"/images/{quote.product['image']}"
        if quote.product:
            slug = quote.product["slug"]
        lines.append(
            {
                "id": item["id"],
                "slug": slug,
                "name": name,
                "summary": quote.summary,
                "notes": quote.notes,
                "quantity": item["quantity"],
                "lineLabel": _money(quote.line_cents) if not quote.issues else "Prix à valider",
                "issues": quote.issues,
                "image": image,
            }
        )
    priced = bool(totals["priced"])
    subtotal = totals["subtotal"] if priced else None
    discount = totals["discount"] if priced else 0
    before = None if subtotal is None else subtotal - discount
    code = ""
    if totals["cart"] and totals["cart"]["promo_code"]:
        code = totals["cart"]["promo_code"]
    return {
        "lines": lines,
        "priced": priced,
        "subtotalLabel": _money(subtotal) if lines else "",
        "discountLabel": format_eur(discount) if priced else "",
        "beforeDeliveryLabel": _money(before) if priced else "",
        "promo": code,
        "promoError": totals["promo_error"] or "",
        "issues": list(dict.fromkeys(totals["issues"])),
        "cartCount": cart_count(ctx.conn, ctx.session["id"]),
        "suivi": [
            _order_suivi(ctx, order)
            for order in orders_for_viewer(ctx.conn, ctx.session["id"], ctx.user["id"] if ctx.user else None)
        ],
    }


def _add(ctx, payload):
    try:
        choices = [int(item) for item in (payload.get("choix") or [])]
        quote = add_item(
            ctx.conn,
            ctx.session["id"],
            int(payload.get("produit") or 0),
            choices,
            int(payload.get("quantite") or 1),
            payload.get("notes") or "",
        )
    except (TypeError, ValueError):
        return json_response({"ok": False, "errors": ["Données de personnalisation invalides."]}, 400)
    if quote.issues:
        return json_response(
            {"ok": False, "errors": quote.issues, "cartCount": cart_count(ctx.conn, ctx.session["id"])},
            422,
        )
    return json_response({"ok": True, "cartCount": cart_count(ctx.conn, ctx.session["id"])})


def _update(ctx, payload):
    try:
        error = update_quantity(
            ctx.conn,
            ctx.session["id"],
            int(payload.get("article") or 0),
            int(payload.get("quantite") or 0),
        )
    except (TypeError, ValueError):
        error = "Quantite invalide."
    data = _cart(ctx)
    data["ok"] = not error
    data["errors"] = [error] if error else []
    return json_response(data, 200 if not error else 422)


def _remove(ctx, payload):
    try:
        remove_item(ctx.conn, ctx.session["id"], int(payload.get("article") or 0))
    except (TypeError, ValueError):
        return json_response({"ok": False, "errors": ["Article invalide."]}, 400)
    data = _cart(ctx)
    data["ok"] = True
    return json_response(data)


def _checkout(ctx):
    from app.stripe_pay import stripe_ready

    cart = _cart(ctx)
    key = ctx.session["idempotency_key"]
    used = False
    if key:
        used = ctx.conn.execute("SELECT 1 FROM orders WHERE idempotency_key = ?", (key,)).fetchone()
    if not key or used:
        key = set_idempotency_key(ctx.conn, ctx.session["id"])
    terms = load_json_setting(ctx.conn, "terms_text", "")
    if not isinstance(terms, str):
        terms = ""
    user = ctx.user
    ready, ready_error = stripe_ready(ctx.conn)
    return {
        "cart": cart,
        "idempotencyKey": key,
        "zones": [
            {"id": zone["id"], "name": zone["name"], "feeLabel": format_eur(zone["fee_cents"])}
            for zone in active_zones(ctx.conn)
        ],
        "slots": _slot_rows(ctx),
        "points": _point_rows(ctx),
        "payments": checkout_methods(ctx.conn),
        "stripeReady": ready,
        "stripeMessage": "" if ready else (ready_error or "Le paiement en ligne n'est pas disponible."),
        "deliveryMode": _delivery_mode(ctx),
        "terms": terms.strip(),
        "customer": {
            "nom": user["name"] if user else "",
            "email": user["email"] if user else "",
            "telephone": user["phone"] if user and user["phone"] else "",
        },
    }


def _slot_rows(ctx):
    return [
        {
            "id": slot["id"],
            "date": slot["slot_date"],
            "start": slot["start_time"],
            "end": slot["end_time"],
            "label": f"{slot['slot_date']} · {slot['start_time']}–{slot['end_time']}",
        }
        for slot in open_slots(ctx.conn)
    ]


def _point_rows(ctx):
    return [
        {"id": point["id"], "name": point["name"], "address": point["address"]}
        for point in active_points(ctx.conn)
    ]


def _delivery_mode(ctx):
    from app.delivery import delivery_mode

    return delivery_mode(ctx.conn)


def _estimate(ctx, payload):
    from app.delivery import quote_delivery

    if limited(f"estimate:{ctx.session['id']}", max_hits=20):
        return json_response({"ok": False, "errors": ["Trop de tentatives. Réessayez dans une minute."]}, 429)
    quote, error = quote_delivery(
        ctx.conn,
        {
            "rue": (payload.get("rue") or "").strip(),
            "code_postal": (payload.get("codePostal") or "").strip(),
            "ville": (payload.get("ville") or "").strip(),
        },
    )
    if error:
        return json_response({"ok": False, "errors": [error]}, 422)
    return json_response({
        "ok": True,
        "feeLabel": format_eur(quote["fee_cents"]),
        "feeCents": quote["fee_cents"],
        "meters": quote["meters"],
    })


def _locate(ctx, payload):
    from app.delivery import quote_from_coords, reverse_address

    if limited(f"locate:{ctx.session['id']}", max_hits=20):
        return json_response({"ok": False, "errors": ["Trop de tentatives. Réessayez dans une minute."]}, 429)
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    address, error = reverse_address(ctx.conn, latitude, longitude, require_complete=False)
    if error:
        return json_response({"ok": False, "errors": [error]}, 422)
    body = {"ok": True, **address}
    quote, quote_error = quote_from_coords(ctx.conn, latitude, longitude)
    if quote:
        body["feeLabel"] = format_eur(quote["fee_cents"])
        body["feeCents"] = quote["fee_cents"]
        body["meters"] = quote["meters"]
    elif quote_error:
        body["feeError"] = quote_error
    if not address.get("rue") or not address.get("codePostal") or not address.get("ville"):
        body["incomplete"] = True
        if not quote:
            return json_response(
                {"ok": False, "errors": ["Cette position ne donne pas une adresse complète."], **body},
                422,
            )
    return json_response(body)


def _owned(ctx, ref):
    if not isinstance(ref, str) or not ref.startswith("AK-") or len(ref) > 20:
        return None
    return order_for_session(ctx.conn, ref, ctx.session["id"], ctx.user["id"] if ctx.user else None)


def _order(ctx, payload):
    if limited(f"order:{ctx.session['id']}"):
        return json_response({"ok": False, "errors": ["Trop de tentatives. Réessayez dans une minute."]}, 429)
    form = {
        "idempotency_key": payload.get("idempotencyKey") or payload.get("idempotency_key") or "",
        "nom": payload.get("nom") or "",
        "email": payload.get("email") or "",
        "telephone": payload.get("telephone") or "",
        "mode": payload.get("mode") or "",
        "zone_id": str(payload.get("zoneId") or ""),
        "slot_id": str(payload.get("slotId") or ""),
        "point_id": str(payload.get("pointId") or ""),
        "rue": payload.get("rue") or "",
        "code_postal": payload.get("codePostal") or "",
        "ville": payload.get("ville") or "",
        "paiement": payload.get("paiement") or "",
        "conditions": "1" if payload.get("conditions") else "",
    }
    order, errors = place_order(
        ctx.conn,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
        form,
    )
    if errors:
        return json_response({"ok": False, "errors": errors}, 422)
    if order["payment_method"] == "stripe":
        url, error = begin_checkout(ctx.conn, order, getattr(ctx, "public_base", "http://127.0.0.1:8080"))
        if error:
            return json_response(
                {"ok": False, "errors": [f"{error} Commande {order['public_ref']}."], "ref": order["public_ref"]},
                422,
            )
        if not url or not url.startswith("https://checkout.stripe.com/"):
            return json_response(
                {"ok": False, "errors": ["Stripe n'a pas ouvert de page de paiement."], "ref": order["public_ref"]},
                422,
            )
        return json_response(
            {"ok": True, "ref": order["public_ref"], "paymentStatus": "pending", "checkoutUrl": url}
        )
    return json_response(
        {
            "ok": True,
            "ref": order["public_ref"],
            "paymentStatus": order["payment_status"],
        }
    )


def _verify_payment(ctx, payload):
    if limited(f"verify:{ctx.session['id']}"):
        return json_response({"ok": False, "errors": ["Trop de tentatives. Réessayez dans une minute."]}, 429)
    ref = payload.get("ref") or ""
    session_id = (payload.get("sessionId") or "").strip()
    order = _owned(ctx, ref)
    if not order and session_id.startswith("cs_") and stripe_configured(ctx.conn):
        checkout, _error = _request(
            "GET",
            "/checkout/sessions/" + urllib.parse.quote(session_id),
            conn=ctx.conn,
        )
        if checkout:
            order = ensure_order_from_checkout(ctx.conn, checkout, claim_session_id=ctx.session["id"])
            if order and order["public_ref"] != ref:
                order = None
    if not order:
        return json_response({"ok": False, "errors": ["Commande introuvable."]}, 404)
    state, error = verify_return(ctx.conn, order, session_id)
    fresh = order_for_session(ctx.conn, order["public_ref"], ctx.session["id"], ctx.user["id"] if ctx.user else None) or order
    body = {"ok": state == "paid", "ref": order["public_ref"], **payment_view(ctx.conn, fresh)}
    if error:
        body["errors"] = [error]
        return json_response(body, 422)
    return json_response(body)


def _cancel_payment(ctx, payload):
    order = _owned(ctx, payload.get("ref") or "")
    if not order:
        return json_response({"ok": False, "errors": ["Commande introuvable."]}, 404)
    error = cancel_payment(ctx.conn, order)
    if error:
        return json_response({"ok": False, "errors": [error]}, 422)
    return json_response({"ok": True, "ref": order["public_ref"]})


def _retry_payment(ctx, payload):
    if limited(f"retry:{ctx.session['id']}"):
        return json_response({"ok": False, "errors": ["Trop de tentatives. Réessayez dans une minute."]}, 429)
    order = _owned(ctx, payload.get("ref") or "")
    if not order:
        return json_response({"ok": False, "errors": ["Commande introuvable."]}, 404)
    url, error = retry_payment(ctx.conn, order, getattr(ctx, "public_base", "http://127.0.0.1:8080"))
    if error:
        return json_response({"ok": False, "errors": [error]}, 422)
    if not url or not url.startswith("https://checkout.stripe.com/"):
        return json_response({"ok": False, "errors": ["Stripe n'a pas ouvert de page de paiement."]}, 422)
    return json_response({"ok": True, "ref": order["public_ref"], "checkoutUrl": url})


def _order_suivi(ctx, order):
    try:
        lines = json.loads(order["snapshot_json"])
    except (TypeError, json.JSONDecodeError):
        lines = []
    view = payment_view(ctx.conn, order)
    return {
        "ref": order["public_ref"],
        "statusLabel": view["statusLabel"],
        "lines": [
            {
                "name": line["name"],
                "quantity": line["quantity"],
                "lineLabel": format_eur(line["line_cents"]),
            }
            for line in lines
        ],
        "subtotalLabel": format_eur(order["subtotal_cents"]),
        "deliveryLabel": format_eur(order["delivery_fee_cents"]),
        "discountLabel": format_eur(order["discount_cents"]),
        "totalLabel": format_eur(order["total_cents"]),
        "events": [{"status": event["label"], "at": event["at"]} for event in view["events"]],
    }


def _order_pdf(ctx, public_ref):
    from app.server import Response
    from app.receipt import render_order_pdf

    order = order_for_session(ctx.conn, public_ref, ctx.session["id"], ctx.user["id"] if ctx.user else None)
    if not order:
        return json_response({"error": "Commande introuvable."}, 404)
    safe = "".join(char for char in order["public_ref"] if char.isalnum() or char == "-") or "commande"
    return Response(
        200,
        render_order_pdf(ctx.conn, order),
        headers=[
            ("Content-Disposition", f'attachment; filename="commande-{safe}.pdf"'),
            ("Cache-Control", "no-store"),
        ],
        content_type="application/pdf",
    )


def _confirmation(ctx, public_ref):
    order = order_for_session(ctx.conn, public_ref, ctx.session["id"], ctx.user["id"] if ctx.user else None)
    if not order:
        return None
    lines = json.loads(order["snapshot_json"])
    view = payment_view(ctx.conn, order)
    review = review_store.order_review_state(
        ctx.conn,
        order,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
    )
    return {
        "ref": order["public_ref"],
        "status": view["status"],
        "statusLabel": view["statusLabel"],
        "paymentStatus": view["paymentStatus"],
        "paymentLabel": view["paymentLabel"],
        "paymentMethod": view["paymentMethod"],
        "paymentMethodLabel": view["paymentMethodLabel"],
        "confirmedByProvider": view["confirmedByProvider"],
        "canRetry": view["canRetry"],
        "canReview": review["canReview"],
        "reviewId": review["reviewId"],
        "lines": [
            {
                "name": line["name"],
                "quantity": line["quantity"],
                "options": line["options"],
                "lineLabel": format_eur(line["line_cents"]),
            }
            for line in lines
        ],
        "subtotalLabel": format_eur(order["subtotal_cents"]),
        "deliveryLabel": format_eur(order["delivery_fee_cents"]),
        "discountLabel": format_eur(order["discount_cents"]),
        "totalLabel": format_eur(order["total_cents"]),
        "events": [{"status": event["label"], "at": event["at"]} for event in view["events"]],
    }


def _account(ctx):
    user = _public_user(ctx.user)
    orders = []
    if user and user["role"] == "customer":
        for order in orders_for_user(ctx.conn, ctx.user["id"]):
            orders.append(
                {
                    "ref": order["public_ref"],
                    "statusLabel": STATUS_LABELS.get(order["status"], order["status"]),
                    "totalLabel": format_eur(order["total_cents"]),
                }
            )
    return {"user": user, "orders": orders}


def _login(ctx, payload):
    user = authenticate(ctx.conn, payload.get("email"), payload.get("password"))
    if not user or user["role"] != "customer":
        return json_response({"ok": False, "errors": ["Identifiants refusés."]}, 401)
    sid = rotate_session(ctx.conn, ctx.session["id"], user["id"])
    return json_response(
        {"ok": True, "user": _public_user(user)},
        headers=[("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=1209600")],
    )


def _register(ctx, payload):
    user_id, error = register_customer(
        ctx.conn,
        payload.get("email"),
        payload.get("password"),
        payload.get("nom"),
        payload.get("telephone"),
    )
    if error:
        return json_response({"ok": False, "errors": [error]}, 422)
    sid = rotate_session(ctx.conn, ctx.session["id"], user_id)
    user = ctx.conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return json_response(
        {"ok": True, "user": _public_user(user)},
        headers=[("Set-Cookie", f"sid={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=1209600")],
    )
