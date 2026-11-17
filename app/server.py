import json
import mimetypes
import os
import traceback
from urllib.parse import parse_qs, urlparse

from app.auth import (
    authenticate,
    create_staff,
    create_session,
    destroy_session,
    ensure_admin,
    ensure_driver,
    get_session,
    pop_flash,
    register_customer,
    rotate_session,
    set_flash,
    user_by_id,
)
from app.cart import remove_item, set_promo, update_quantity
from app.db import ROOT, init_db
from app.pages import (
    account,
    admin_avis,
    admin_cuisine,
    admin_home,
    admin_login,
    admin_order,
    admin_orders,
    admin_delivery,
    admin_drivers,
    admin_hours,
    admin_notifications,
    admin_products,
    admin_promotions,
    admin_settings,
    admin_slots,
    cart,
    checkout,
    confirmation,
    handle_add,
    handle_order_post,
    home,
    menu,
    product,
)
from app.seed import seed
from app.admin_store import (
    add_distance_band,
    add_promo,
    add_slot,
    add_zone,
    confirm_zone_fee,
    save_geo_key,
    save_stripe_keys,
    save_hours,
    save_product,
    set_band_active,
    set_delivery_mode,
    set_payment,
    set_slot_active,
    set_zone_active,
)
from app.orders import mark_collected, set_status


class Response:
    def __init__(self, status=200, body="", headers=None, content_type="text/html; charset=utf-8"):
        self.status = status
        self.body = body if isinstance(body, bytes) else body.encode("utf-8")
        self.headers = list(headers or [])
        self.content_type = content_type


class Ctx:
    def __init__(self, conn, session, user, flash):
        self.conn = conn
        self.session = session
        self.user = user
        self.flash = flash


def _cors_origins():
    raw = os.environ.get(
        "ALLOKO_CORS_ORIGINS",
        "https://affouchatasylla.github.io,https://affouchataSylla.github.io,https://allokodrone.vercel.app,http://127.0.0.1:8080,http://localhost:8080,http://127.0.0.1:5173,http://localhost:5173",
    )
    return {item.strip().rstrip("/") for item in raw.split(",") if item.strip()}


def _cookie(sid, clear=False, cross_site=False):
    if cross_site:
        if clear:
            return "sid=; HttpOnly; Secure; SameSite=None; Path=/; Max-Age=0"
        return f"sid={sid}; HttpOnly; Secure; SameSite=None; Path=/; Max-Age=1209600"
    if clear:
        return "sid=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0"
    return f"sid={sid}; HttpOnly; SameSite=Lax; Path=/; Max-Age=1209600"


def _form(body, query, content_type):
    data = {key: values[-1] for key, values in query.items()}
    if body and "application/json" not in content_type:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        for key, values in parsed.items():
            data[key] = values[-1]
    return data


def _payload(body, content_type):
    if "application/json" not in content_type:
        return None, False
    try:
        data = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return None, True
    if not isinstance(data, dict):
        return None, True
    return data, False


def _asset(path):
    if not path.startswith("/assets/"):
        return None
    name = path[len("/assets/") :]
    if not name or "/" in name or "\\" in name or ".." in name:
        return None
    target = (ROOT / "web" / "dist" / "assets" / name).resolve()
    root = (ROOT / "web" / "dist" / "assets").resolve()
    if target.parent != root or not target.is_file():
        return None
    mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if target.suffix == ".js":
        mime = "text/javascript; charset=utf-8"
    elif target.suffix == ".css":
        mime = "text/css; charset=utf-8"
    return Response(200, target.read_bytes(), content_type=mime, headers=[("Cache-Control", "public, max-age=31536000, immutable")])


def _spa(path):
    if path.startswith("/admin") or path.startswith("/api") or path.startswith("/assets"):
        return None
    if path.startswith(("/css/", "/js/", "/images/", "/videos/", "/fonts/")) or path == "/menu.pdf":
        return None
    index = ROOT / "web" / "dist" / "index.html"
    if not index.is_file():
        return None
    return Response(200, index.read_bytes(), content_type="text/html; charset=utf-8", headers=[("Cache-Control", "no-cache")])


def _static(path):
    if path.startswith("/uploads/reviews/"):
        from app.reviews import upload_file

        target = upload_file(path)
        if not target:
            return None
        mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        return Response(200, target.read_bytes(), content_type=mime, headers=[("Cache-Control", "public, max-age=86400")])
    relative = path.lstrip("/")
    kind = ""
    if relative == "menu.pdf":
        target = ROOT / "menu.pdf"
    else:
        parts = relative.split("/")
        if len(parts) != 2 or parts[0] not in {"css", "js", "images", "videos", "fonts"}:
            return None
        if ".." in parts[1] or "/" in parts[1] or "\\" in parts[1]:
            return None
        kind = parts[0]
        target = (ROOT / parts[0] / parts[1]).resolve()
        if ROOT.resolve() not in target.parents:
            return None
    if not target.is_file():
        return None
    mime = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if target.suffix.lower() == ".woff2":
        mime = "font/woff2"
    elif target.suffix.lower() == ".woff":
        mime = "font/woff"
    elif target.suffix.lower() == ".ttf":
        mime = "font/ttf"
    elif target.suffix.lower() == ".otf":
        mime = "font/otf"
    headers = [("Cache-Control", "public, max-age=31536000, immutable")] if kind == "fonts" else None
    return Response(200, target.read_bytes(), content_type=mime, headers=headers)


def _cross_site(headers):
    origin = (headers or {}).get("origin", "").strip().rstrip("/")
    return bool(origin) and origin in _cors_origins()


def _apply_cors(response, headers):
    origin = (headers or {}).get("origin", "").strip().rstrip("/")
    if origin and origin in _cors_origins():
        response.headers.append(("Access-Control-Allow-Origin", origin))
        response.headers.append(("Access-Control-Allow-Credentials", "true"))
        response.headers.append(("Access-Control-Allow-Headers", "Content-Type, X-CSRF, Accept"))
        response.headers.append(("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS"))
        response.headers.append(("Vary", "Origin"))
    return response


def handle_http(conn, method, target, headers, body):
    parsed = urlparse(target)
    path = parsed.path
    query = parse_qs(parsed.query)
    cross_site = _cross_site(headers)
    if method == "OPTIONS":
        return _apply_cors(Response(204, b""), headers)
    if method == "POST" and path == "/api/stripe/webhook":
        from app.stripe_pay import handle_webhook

        status, data = handle_webhook(conn, body or b"", headers.get("stripe-signature", ""))
        return Response(status, json.dumps(data, ensure_ascii=False), content_type="application/json; charset=utf-8")
    if method == "POST" and path == "/api/uber/webhook":
        from app.uber_direct import handle_webhook as uber_webhook

        signature = headers.get("x-uber-signature") or headers.get("x-postmates-signature") or ""
        status, data = uber_webhook(conn, body or b"", signature)
        return Response(status, json.dumps(data, ensure_ascii=False), content_type="application/json; charset=utf-8")
    if method == "GET":
        static = _static(path) or _asset(path)
        if static:
            return static
    content_type = headers.get("content-type", "")
    payload, bad_json = _payload(body, content_type)
    if bad_json:
        return Response(400, json.dumps({"error": "JSON invalide."}), content_type="application/json; charset=utf-8")
    form = _form(body, query if method == "POST" else {}, content_type)
    cookie = _cookie_value(headers.get("cookie", ""), "sid")
    session = get_session(conn, cookie)
    new_sid = None
    if not session and not path.startswith(("/css", "/images", "/js", "/assets", "/videos")):
        new_sid = create_session(conn)
        session = get_session(conn, new_sid)
    if method in {"POST", "PATCH", "DELETE"}:
        token = form.get("csrf") or headers.get("x-csrf") or (payload or {}).get("csrf")
        if not session or token != session["csrf"]:
            if path.startswith("/api/"):
                return Response(400, json.dumps({"error": "Requete refusee."}), content_type="application/json; charset=utf-8")
            return Response(400, "Requete refusee.")
    user = user_by_id(conn, session["user_id"]) if session else None
    flash = pop_flash(conn, session["id"]) if session else ""
    ctx = Ctx(conn, session, user, flash)
    ctx.path = path
    from app.stripe_pay import public_base

    ctx.public_base = public_base(headers)
    try:
        response = dispatch(ctx, method, path, query, form, payload)
    except Exception:
        traceback.print_exc()
        if path.startswith("/api/"):
            response = Response(500, json.dumps({"error": "Une erreur interne est survenue."}), content_type="application/json; charset=utf-8")
        else:
            response = Response(500, "Une erreur interne est survenue.")
    if new_sid and not any(header[0].lower() == "set-cookie" for header in response.headers):
        response.headers.append(("Set-Cookie", _cookie(new_sid, cross_site=cross_site)))
    # Re-tag cookies issued by redirects for cross-site GitHub Pages → API
    if cross_site:
        patched = []
        for key, value in response.headers:
            if key.lower() == "set-cookie" and "SameSite=None" not in value:
                if "Max-Age=0" in value or value.startswith("sid=;"):
                    patched.append((key, _cookie("", clear=True, cross_site=True)))
                elif value.startswith("sid="):
                    sid = value.split(";", 1)[0].split("=", 1)[1]
                    patched.append((key, _cookie(sid, cross_site=True)))
                else:
                    patched.append((key, value))
            else:
                patched.append((key, value))
        response.headers = patched
    return _apply_cors(response, headers)


def dispatch(ctx, method, path, query, form, payload=None):
    from app.api import dispatch_api

    api_response = dispatch_api(ctx, method, path, query, payload)
    if api_response:
        return api_response
    if method == "GET":
        document = _spa(path)
        if document:
            return document
    if path == "/" and method == "GET":
        return html(home(ctx))
    if path == "/carte" and method == "GET":
        return html(menu(ctx, query))
    if path.startswith("/produit/") and method == "GET":
        rendered = product(ctx, path.split("/")[2])
        if not rendered:
            return Response(404, "Produit introuvable.")
        return html(rendered)
    if path == "/panier" and method == "GET":
        return html(cart(ctx))
    if path == "/panier/ajouter" and method == "POST":
        slug, errors = handle_add(ctx, form)
        if errors:
            set_flash(ctx.conn, ctx.session["id"], " ".join(errors))
            return redirect(f"/produit/{slug}" if slug else "/carte")
        set_flash(ctx.conn, ctx.session["id"], "Ajoute au panier.")
        return redirect("/panier")
    if path == "/panier/modifier" and method == "POST":
        try:
            error = update_quantity(ctx.conn, ctx.session["id"], int(form.get("article") or 0), int(form.get("quantite") or 0))
        except ValueError:
            error = "Quantite invalide."
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect("/panier")
    if path == "/panier/supprimer" and method == "POST":
        try:
            remove_item(ctx.conn, ctx.session["id"], int(form.get("article") or 0))
        except ValueError:
            pass
        return redirect("/panier")
    if path == "/panier/code" and method == "POST":
        set_promo(ctx.conn, ctx.session["id"], form.get("code") or "")
        return redirect("/panier")
    if path == "/commander" and method == "GET":
        return html(checkout(ctx))
    if path == "/commander" and method == "POST":
        order, errors = handle_order_post(ctx, form)
        if errors:
            set_flash(ctx.conn, ctx.session["id"], " ".join(errors))
            return redirect("/commander")
        if order["payment_method"] == "stripe":
            from app.stripe_pay import begin_checkout

            url, error = begin_checkout(ctx.conn, order, ctx.public_base)
            if error or not url or not url.startswith("https://checkout.stripe.com/"):
                set_flash(ctx.conn, ctx.session["id"], error or "Stripe n'a pas ouvert de page de paiement.")
                return redirect(f"/commande/{order['public_ref']}")
            return redirect(url)
        return redirect(f"/commande/{order['public_ref']}")
    if path.startswith("/commande/") and method == "GET":
        rendered = confirmation(ctx, path.split("/")[2])
        if not rendered:
            return Response(404, "Commande introuvable.")
        return html(rendered)
    if path == "/compte" and method == "GET":
        return html(account(ctx))
    if path == "/compte/inscription" and method == "POST":
        user_id, error = register_customer(
            ctx.conn, form.get("email"), form.get("password"), form.get("nom"), form.get("telephone")
        )
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
            return redirect("/compte")
        sid = rotate_session(ctx.conn, ctx.session["id"], user_id)
        return redirect("/compte", sid)
    if path == "/compte/connexion" and method == "POST":
        user = authenticate(ctx.conn, form.get("email"), form.get("password"))
        if not user or user["role"] != "customer":
            set_flash(ctx.conn, ctx.session["id"], "Identifiants refuses.")
            return redirect("/compte")
        sid = rotate_session(ctx.conn, ctx.session["id"], user["id"])
        return redirect("/compte", sid)
    if path == "/compte/deconnexion" and method == "POST":
        destroy_session(ctx.conn, ctx.session["id"])
        return redirect("/", clear_cookie=True)
    if path == "/admin/connexion" and method == "GET":
        return html(admin_login(ctx))
    if path == "/admin/connexion" and method == "POST":
        user = authenticate(ctx.conn, form.get("email"), form.get("password"))
        if not user or user["role"] not in ("admin", "driver"):
            set_flash(ctx.conn, ctx.session["id"], "Identifiants refuses.")
            return redirect("/admin/connexion")
        sid = rotate_session(ctx.conn, ctx.session["id"], user["id"])
        if user["role"] == "driver":
            return redirect("/admin/livreurs", sid)
        return redirect("/admin", sid)
    if path.startswith("/admin"):
        if not ctx.user:
            return redirect("/admin/connexion")
        role = ctx.user["role"]
        if role == "driver":
            allowed = (
                path == "/admin/livreurs"
                or path.startswith("/admin/livreurs/")
                or path == "/admin/deconnexion"
            )
            if path in ("/admin", "/admin/"):
                return redirect("/admin/livreurs")
            if not allowed:
                set_flash(ctx.conn, ctx.session["id"], "Accès réservé aux administrateurs.")
                return redirect("/admin/livreurs")
        elif role != "admin":
            return Response(403, "Acces refuse.")
    if path == "/admin" and method == "GET":
        return html(admin_home(ctx))
    if path == "/admin/cuisine" and method == "GET":
        return html(admin_cuisine(ctx, query))
    if path == "/admin/cuisine/fragment" and method == "GET":
        from app.kitchen import render_fragment

        return Response(200, render_fragment(ctx, query), headers=[("Cache-Control", "no-store")])
    if path == "/admin/cuisine/delais" and method == "POST":
        from app.kitchen import kitchen_return, save_thresholds

        error = save_thresholds(ctx.conn, form.get("attention"), form.get("urgent"))
        set_flash(ctx.conn, ctx.session["id"], error or "Délais enregistrés.")
        return redirect(kitchen_return(form))
    if path == "/admin/cuisine/ligne" and method == "POST":
        from app.kitchen import kitchen_return, mark_line

        try:
            index = int(form.get("index") or -1)
            order_id = int(form.get("commande") or 0)
        except ValueError:
            index, order_id = -1, 0
        error = mark_line(ctx.conn, order_id, index, form.get("fait") == "1")
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(kitchen_return(form))
    if path == "/admin/cuisine/prete" and method == "POST":
        from app.kitchen import kitchen_return, mark_ready

        try:
            order_id = int(form.get("commande") or 0)
        except ValueError:
            order_id = 0
        error = mark_ready(ctx.conn, order_id, form.get("confirmer"))
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(kitchen_return(form))
    if path == "/admin/cuisine/probleme" and method == "POST":
        from app.kitchen import kitchen_return, save_issue

        try:
            order_id = int(form.get("commande") or 0)
        except ValueError:
            order_id = 0
        error = save_issue(ctx.conn, order_id, form.get("probleme"))
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(kitchen_return(form))
    if path == "/admin/deconnexion" and method == "POST":
        destroy_session(ctx.conn, ctx.session["id"])
        return redirect("/", clear_cookie=True)
    if path == "/admin/produits" and method == "GET":
        return html(admin_products(ctx))
    if path.startswith("/admin/produits/") and method == "POST":
        error = save_product(ctx.conn, int(path.split("/")[3]), form)
        set_flash(ctx.conn, ctx.session["id"], error or "Produit enregistre.")
        return redirect("/admin/produits")
    if path == "/admin/avis" and method == "GET":
        return html(admin_avis(ctx, query))
    if path.startswith("/admin/avis/") and method == "POST" and path.endswith("/masquer"):
        from app.reviews import hide_review

        review_id = int(path.split("/")[3])
        errors = hide_review(ctx.conn, review_id, ctx.user["id"], form.get("motif") or "")
        set_flash(ctx.conn, ctx.session["id"], errors[0] if errors else "Avis masqué.")
        return redirect("/admin/avis")
    if path.startswith("/admin/avis/") and method == "POST" and path.endswith("/publier"):
        from app.reviews import publish_review

        review_id = int(path.split("/")[3])
        errors = publish_review(ctx.conn, review_id)
        set_flash(ctx.conn, ctx.session["id"], errors[0] if errors else "Avis republé.")
        return redirect("/admin/avis?statut=hidden")
    if path.startswith("/admin/avis/") and method == "POST" and path.endswith("/repondre"):
        from app.reviews import reply_review

        review_id = int(path.split("/")[3])
        errors = reply_review(ctx.conn, review_id, ctx.user["id"], form.get("reponse") or "")
        set_flash(ctx.conn, ctx.session["id"], errors[0] if errors else "Réponse publiée.")
        return redirect("/admin/avis")
    if path.startswith("/admin/avis/") and method == "POST" and path.endswith("/supprimer"):
        from app.reviews import delete_review

        review_id = int(path.split("/")[3])
        errors = delete_review(ctx.conn, review_id, ctx.session["id"], ctx.user["id"], admin=True)
        set_flash(ctx.conn, ctx.session["id"], errors[0] if errors else "Avis supprimé.")
        return redirect("/admin/avis")
    if path == "/admin/commandes" and method == "GET":
        return html(admin_orders(ctx, query))
    if path.startswith("/admin/commandes/") and method == "GET":
        rendered = admin_order(ctx, int(path.split("/")[3]))
        if not rendered:
            return Response(404, "Commande introuvable.")
        return html(rendered)
    if path.startswith("/admin/commandes/") and method == "POST" and path.endswith("/statut"):
        from app.kitchen import kitchen_return, needs_confirmation

        order_id = path.split("/")[3]
        if needs_confirmation(form):
            set_flash(ctx.conn, ctx.session["id"], "Confirmez cette action.")
            if form.get("retour") == "service":
                return redirect(kitchen_return(form))
            return redirect(f"/admin/commandes/{order_id}")
        error = set_status(ctx.conn, int(order_id), form.get("statut"))
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        if form.get("retour") == "service":
            return redirect(kitchen_return(form))
        return redirect(f"/admin/commandes/{order_id}")
    if path.startswith("/admin/commandes/") and method == "POST" and path.endswith("/encaisser"):
        order_id = path.split("/")[3]
        error = mark_collected(ctx.conn, int(order_id))
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(f"/admin/commandes/{order_id}")
    if path.startswith("/admin/commandes/") and method == "POST" and path.endswith("/rembourser"):
        from app.stripe_pay import refund_order

        order_id = int(path.split("/")[3])
        order = ctx.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        error = "Commande introuvable." if not order else refund_order(ctx.conn, order)
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(f"/admin/commandes/{order_id}")
    if path.startswith("/admin/commandes/") and method == "POST" and path.endswith("/uber"):
        from app.uber_direct import dispatch_order

        order_id = int(path.split("/")[3])
        order = ctx.conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
        error = "Commande introuvable." if not order else dispatch_order(ctx.conn, order)
        if error:
            set_flash(ctx.conn, ctx.session["id"], error)
        return redirect(f"/admin/commandes/{order_id}")
    if path == "/admin/livraison" and method == "GET":
        return html(admin_delivery(ctx))
    if path == "/admin/livreurs" and method == "GET":
        return html(admin_drivers(ctx))
    if path.startswith("/admin/livreurs/") and method == "POST" and path.endswith("/accepter"):
        from app.drivers import accept_order

        order_id = int(path.split("/")[3])
        error = accept_order(ctx.conn, order_id, form.get("livreur"), form.get("telephone"))
        set_flash(ctx.conn, ctx.session["id"], error or "Course acceptée. Bonne livraison.")
        return redirect("/admin/livreurs")
    if path.startswith("/admin/livreurs/") and method == "POST" and path.endswith("/livree"):
        from app.drivers import complete_order

        order_id = int(path.split("/")[3])
        error = complete_order(ctx.conn, order_id)
        set_flash(ctx.conn, ctx.session["id"], error or "Livraison marquée comme terminée.")
        return redirect("/admin/livreurs")
    if path.startswith("/admin/livreurs/") and method == "POST" and path.endswith("/relacher"):
        from app.drivers import release_order

        order_id = int(path.split("/")[3])
        error = release_order(ctx.conn, order_id)
        set_flash(ctx.conn, ctx.session["id"], error or "Course remise en attente.")
        return redirect("/admin/livreurs")
    if path == "/admin/horaires" and method == "GET":
        return html(admin_hours(ctx))
    if path == "/admin/creneaux" and method == "GET":
        return html(admin_slots(ctx, query))
    if path == "/admin/notifications" and method == "GET":
        return html(admin_notifications(ctx))
    if path == "/admin/promotions" and method == "GET":
        return html(admin_promotions(ctx))
    if path == "/admin/reglages" and method == "GET":
        return html(admin_settings(ctx))
    if path == "/admin/equipe" and method == "POST":
        _, error = create_staff(
            ctx.conn,
            form.get("email"),
            form.get("password"),
            form.get("nom"),
            form.get("telephone"),
            form.get("role"),
        )
        role = (form.get("role") or "").strip().lower()
        ok = "Administrateur ajouté." if role == "admin" else "Livreur ajouté à l'équipe."
        set_flash(ctx.conn, ctx.session["id"], error or ok)
        return redirect("/admin/reglages")
    if path == "/admin/horaires" and method == "POST":
        error = save_hours(ctx.conn, form)
        set_flash(ctx.conn, ctx.session["id"], error or "Horaires enregistrés.")
        return redirect("/admin/horaires")
    if path.startswith("/admin/zones/") and method == "POST":
        zone_id = int(path.split("/")[3])
        if form.get("action") == "confirmer":
            error = confirm_zone_fee(ctx.conn, zone_id)
            note = "Frais validés. La zone reste fermée tant que vous ne l'ouvrez pas."
        else:
            error = set_zone_active(ctx.conn, zone_id, form.get("active") == "1")
            note = "Zone mise à jour."
        set_flash(ctx.conn, ctx.session["id"], error or note)
        return redirect("/admin/livraison")
    if path == "/admin/zones" and method == "POST":
        error = add_zone(ctx.conn, form)
        set_flash(ctx.conn, ctx.session["id"], error or "Zone enregistrée.")
        return redirect("/admin/livraison")
    if path.startswith("/admin/creneaux/") and method == "POST":
        error = set_slot_active(ctx.conn, int(path.split("/")[3]), form.get("active") == "1")
        set_flash(ctx.conn, ctx.session["id"], error or "Créneau mis à jour.")
        return redirect(_creneaux_redirect(form))
    if path == "/admin/creneaux" and method == "POST":
        error = add_slot(ctx.conn, form)
        set_flash(ctx.conn, ctx.session["id"], error or "Créneau enregistré.")
        return redirect(_creneaux_redirect(form))
    if path == "/admin/paiements" and method == "POST":
        set_payment(ctx.conn, "pay_at_pickup", False)
        set_payment(ctx.conn, "pay_on_delivery", form.get("pay_on_delivery") == "1")
        set_flash(ctx.conn, ctx.session["id"], "Règlements enregistrés.")
        return redirect("/admin/reglages")
    if path == "/admin/stripe" and method == "POST":
        error = save_stripe_keys(ctx.conn, form)
        if form.get("retirer") == "1":
            note = "Clé Stripe retirée. Le paiement en ligne est débranché."
        else:
            note = "Paiement Stripe branché et vérifié."
        set_flash(ctx.conn, ctx.session["id"], error or note)
        return redirect("/admin/reglages")
    if path == "/admin/livraison-mode" and method == "POST":
        error = set_delivery_mode(ctx.conn, form)
        set_flash(ctx.conn, ctx.session["id"], error or "Mode de livraison enregistré.")
        return redirect("/admin/livraison")
    if path == "/admin/livraison-essai" and method == "POST":
        from app.delivery import fee_for_km
        from app.money import format_eur

        fee, error = fee_for_km(ctx.conn, form.get("km"))
        if error:
            note = error
        else:
            shown = (form.get("km") or "").strip().replace(".", ",")
            note = f"Pour {shown} km, la livraison coûte {format_eur(fee)}."
        set_flash(ctx.conn, ctx.session["id"], note)
        return redirect("/admin/livraison")
    if path == "/admin/livraison-cle" and method == "POST":
        error = save_geo_key(ctx.conn, form)
        if form.get("retirer") == "1":
            note = "Clé retirée. Le calcul du trajet est débranché."
        else:
            note = "Le calcul du trajet est branché."
        set_flash(ctx.conn, ctx.session["id"], error or note)
        return redirect("/admin/livraison")
    if path.startswith("/admin/distances/") and method == "POST":
        opening = form.get("active") == "1"
        error = set_band_active(ctx.conn, int(path.split("/")[3]), opening)
        note = "Palier ouvert." if opening else "Palier fermé."
        set_flash(ctx.conn, ctx.session["id"], error or note)
        return redirect("/admin/livraison")
    if path == "/admin/distances" and method == "POST":
        error = add_distance_band(ctx.conn, form)
        set_flash(ctx.conn, ctx.session["id"], error or "Palier enregistré.")
        return redirect("/admin/livraison")
    if path == "/admin/promotions" and method == "POST":
        try:
            error = add_promo(ctx.conn, form)
        except Exception:
            error = "Ce code existe deja."
        set_flash(ctx.conn, ctx.session["id"], error or "Promotion enregistrée.")
        return redirect("/admin/promotions")
    return Response(404, "Page introuvable.")


def _creneaux_redirect(form):
    day = (form.get("jour") or form.get("date") or "").strip()
    parts = day.split("-")
    if len(parts) == 3 and all(part.isdigit() for part in parts) and len(parts[0]) == 4:
        return f"/admin/creneaux?jour={day}"
    return "/admin/creneaux"


def html(text):
    return Response(200, text)


def redirect(location, sid=None, clear_cookie=False):
    headers = [("Location", location)]
    if clear_cookie:
        headers.append(("Set-Cookie", _cookie("", clear=True)))
    elif sid:
        headers.append(("Set-Cookie", _cookie(sid)))
    return Response(303, "", headers=headers)


def _cookie_value(header, name):
    for part in header.split(";"):
        piece = part.strip()
        if piece.startswith(name + "="):
            return piece.split("=", 1)[1]
    return ""


def prepare(path=None):
    conn = init_db(path)
    seed(conn)
    from app.orders import ensure_upcoming_slots

    ensure_upcoming_slots(conn)
    try:
        ensure_admin(conn, os.environ.get("ALLOKO_ADMIN_EMAIL"), os.environ.get("ALLOKO_ADMIN_PASSWORD"))
        ensure_driver(
            conn,
            os.environ.get("ALLOKO_DRIVER_EMAIL"),
            os.environ.get("ALLOKO_DRIVER_PASSWORD"),
            os.environ.get("ALLOKO_DRIVER_NAME") or "Livreur",
        )
    except ValueError as exc:
        print(exc)
    return conn


def main():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    db_path = os.environ.get("ALLOKO_DB", str(ROOT / "data" / "allokodrone.db"))
    # Render/Railway exposent PORT ; ALLOKO_PORT reste pour le local
    port = int(os.environ.get("PORT") or os.environ.get("ALLOKO_PORT", "8080"))

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self._serve("GET")

        def do_POST(self):
            self._serve("POST")

        def do_OPTIONS(self):
            self._serve("OPTIONS")

        def _serve(self, method):
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            conn = prepare(db_path)
            try:
                response = handle_http(conn, method, self.path, {k.lower(): v for k, v in self.headers.items()}, body)
            finally:
                conn.close()
            self.send_response(response.status)
            self.send_header("Content-Type", response.content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "same-origin")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; "
                "img-src 'self' data: https:; "
                "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
                "font-src 'self' https://fonts.gstatic.com; "
                "script-src 'self'; "
                "frame-src 'self' https://www.openstreetmap.org; "
                "connect-src 'self'; "
                "base-uri 'self'; "
                "form-action 'self'",
            )
            for key, value in response.headers:
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(response.body)))
            self.end_headers()
            self.wfile.write(response.body)

        def log_message(self, fmt, *args):
            print("%s - %s" % (self.address_string(), fmt % args))

    host = os.environ.get("ALLOKO_HOST", "0.0.0.0")
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ALLOKODRONE ecoute sur http://{host}:{port}")
    print(f"En local : http://127.0.0.1:{port}")
    server.serve_forever()
