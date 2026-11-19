import json
import re

from app.admin_store import (
    add_promo,
    add_slot,
    add_zone,
    save_hours,
    save_product,
    set_payment,
    settings_view,
)
from app.auth import authenticate, register_customer, set_idempotency_key
from app.cart import add_item, cart_count, remove_item, set_promo, update_quantity
from app.catalog import categories, featured_products, groups_for_product, list_products, product_by_slug
from app.db import ROOT
from app.money import format_eur
from app.orders import (
    KITCHEN_STATUSES,
    STATUS_LABELS,
    active_payment_methods,
    active_points,
    active_zones,
    cart_totals,
    dashboard_stats,
    open_slots,
    order_for_session,
    orders_for_user,
    place_order,
    orders_sheet,
    payment_summary,
    place_label,
    set_status,
    when_label,
)
from app.schedule import hours_label, load_json_setting
from app.ui import (
    BTN,
    BTN_GHOST,
    BTN_TEXT,
    CHECK,
    CHIP,
    CHIP_ON,
    CHOICE,
    EYEBROW,
    FIELD,
    H1,
    H2,
    INPUT,
    LEAD,
    MUTED,
    NOTICE,
    PANEL,
    PANEL_PAD,
    PRICE,
    PRICE_MISSING,
    errors_block,
    esc,
    hidden,
    login_page,
    page,
    password_field,
    price_label,
)


def _signature_media(product):
    image = f"/images/{product['image']}" if product["image"] else ""
    video = ""
    for ext in ("mp4", "webm"):
        if (ROOT / "videos" / f"{product['slug']}.{ext}").is_file():
            video = f"/videos/{product['slug']}.{ext}"
            break
    frame = "aspect-[4/5] w-full object-cover"
    if video:
        poster = f' poster="{esc(image)}"' if image else ""
        return (
            f'<video class="{frame}" src="{esc(video)}"{poster} '
            f'autoplay muted loop playsinline></video>'
        )
    if image:
        return f'<img class="{frame}" src="{esc(image)}" alt="{esc(product["name"])}">'
    return f'<div class="{frame} bg-ink"></div>'


def home(ctx):
    features = []
    for product in featured_products(ctx.conn):
        features.append(
            f"""
            <a class="group flex h-full flex-col rounded-2xl border border-cream/15 bg-night-2 p-3" href="/produit/{esc(product['slug'])}">
              <div class="overflow-hidden rounded-xl bg-ink">{_signature_media(product)}</div>
              <p class="mt-4 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.16em] text-terracotta"><span class="h-1.5 w-1.5 shrink-0 bg-terracotta" aria-hidden="true"></span>{esc(product["category_name"])}</p>
              <h3 class="mt-2 font-display text-lg uppercase leading-tight tracking-wide text-cream group-hover:text-terracotta">{esc(product["name"])}</h3>
              <p class="mt-2 text-sm leading-relaxed text-cream/70">{esc(product["description"])}</p>
            </a>
            """
        )
    cats = "".join(
        f'<li><a class="{CHIP}" href="/carte?categorie={esc(cat["slug"])}">{esc(cat["name"])}</a></li>'
        for cat in categories(ctx.conn)
    )
    hours = load_json_setting(ctx.conn, "hours", {"mon_sat": ["11:30", "22:30"], "sun": ["17:00", "22:30"]})
    body = f"""
      <section class="relative left-1/2 -mt-8 w-screen -translate-x-1/2 overflow-hidden bg-night sm:-mt-12">
        <video class="aspect-[4/5] w-full object-cover sm:aspect-video lg:aspect-[2.2/1]" src="/videos/hero.mp4" poster="/images/bowl.jpg" autoplay muted loop playsinline></video>
        <div class="absolute inset-0 bg-gradient-to-r from-night/80 via-night/35 to-transparent"></div>
        <div class="absolute inset-0 flex items-end px-4 pb-8 sm:items-center">
          <div class="mx-auto w-full max-w-6xl">
            <p class="{EYEBROW}">Afro street food · Noisy-le-Sec</p>
            <h1 class="mt-3 max-w-xl font-display text-4xl leading-[0.95] text-cream sm:text-5xl">L'Afrique servie à grande vitesse</h1>
            <p class="mt-4 max-w-md text-base leading-relaxed text-cream/80">Burgers yassa, bowls à composer, wings et alloko. Choisissez, personnalisez, puis commandez en retrait ou en livraison.</p>
            <div class="mt-6 flex flex-wrap gap-3">
              <a class="{BTN}" href="/carte">Voir la carte</a>
              <a class="inline-flex min-h-11 items-center justify-center rounded-xl border border-cream/40 px-4 text-sm font-medium text-cream hover:border-cream" href="/panier">Voir le panier</a>
            </div>
          </div>
        </div>
      </section>
      <ul class="mt-8 flex gap-2 overflow-x-auto pb-1" aria-label="Catégories">{cats}</ul>
      <section id="signatures" class="relative left-1/2 mt-16 w-screen -translate-x-1/2 bg-night px-4 py-14 text-cream sm:py-16">
        <div class="mx-auto max-w-6xl">
          <div class="grid items-end gap-6 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,0.7fr)]">
            <div>
              <p class="text-xs font-medium uppercase tracking-[0.18em] text-terracotta">Notre signature</p>
              <h2 class="mt-3 font-display text-4xl leading-[0.92] text-cream sm:text-5xl lg:text-6xl">Des recettes qui font <span class="text-terracotta">voyager</span></h2>
            </div>
            <p class="max-w-xs text-sm leading-relaxed text-cream/75 lg:justify-self-end lg:pb-1">Nos incontournables préparés maison, chaque jour, avec des ingrédients de qualité.</p>
          </div>
          <div class="mt-10 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4 lg:gap-5">{''.join(features)}</div>
        </div>
      </section>
      <section class="mt-14 grid gap-6 rounded-2xl border border-line bg-cream p-6 sm:p-8 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p class="{EYEBROW}">Offre annoncée</p>
          <h2 class="mt-2 font-display text-3xl text-ink">Boisson offerte en Click &amp; Collect</h2>
          <p class="mt-3 text-sm leading-relaxed text-ink-soft">Offre publiée par le restaurant. Elle n'est pas déduite automatiquement : aucune boisson ni aucun montant n'est précisé dans les données actuelles.</p>
        </div>
        <p class="text-sm leading-relaxed text-ink-soft lg:self-end">{esc(hours_label(hours))}</p>
      </section>
      <section class="mt-14 grid gap-8 lg:grid-cols-2" id="restaurant">
        <img class="aspect-[6/5] w-full rounded-2xl object-cover object-top" src="/images/storefront.jpg" alt="Devanture ALLOKODRONE, 24 rue Emmanuel Arago à Noisy-le-Sec">
        <div>
          <p class="{EYEBROW}">Nous trouver</p>
          <h2 class="{H2}">Au comptoir</h2>
          <p class="{LEAD}">24 rue Emmanuel Arago, 93130 Noisy-le-Sec.</p>
          <p class="mt-4 {MUTED}">{esc(hours_label(hours))}</p>
          <blockquote class="mt-8 border-l-2 border-saffron pl-4">
            <p class="font-display text-2xl leading-snug">« Une vraie découverte ! Les saveurs sont au rendez-vous, le pulled beef yassa est incroyable et l'accueil est top. »</p>
            <footer class="mt-3 {MUTED}">Sarah — Noisy-le-Sec · Google</footer>
          </blockquote>
          <a class="mt-6 {BTN_GHOST}" href="https://www.google.com/maps/dir/?api=1&amp;destination=24+rue+Emmanuel+Arago+93130+Noisy-le-Sec">Itinéraire</a>
        </div>
      </section>
    """
    return _html(ctx, "Commander", body)


def menu(ctx, query):
    slug = (query.get("categorie") or [""])[0]
    text = (query.get("q") or [""])[0]
    cats = categories(ctx.conn)
    chips = [
        f'<a class="{CHIP if slug else CHIP_ON}" href="/carte"{" aria-current=\"page\"" if not slug else ""}>Tout</a>'
    ]
    for cat in cats:
        current = cat["slug"] == slug
        chips.append(
            f'<a class="{CHIP_ON if current else CHIP}" href="/carte?categorie={esc(cat["slug"])}"{" aria-current=\"page\"" if current else ""}>{esc(cat["name"])}</a>'
        )
    products = list_products(ctx.conn, slug or None, text or None)
    groups = []
    current = None
    bucket = []
    for product in products:
        if product["category_name"] != current:
            if bucket:
                groups.append((current, bucket))
            current = product["category_name"]
            bucket = []
        bucket.append(product)
    if bucket:
        groups.append((current, bucket))
    blocks = []
    if not groups:
        blocks.append(f'<p class="mt-8 {MUTED}">Aucun produit ne correspond à cette recherche.</p>')
    for name, items in groups:
        rows = []
        for product in items:
            state = "Disponible" if product["available"] else "Indisponible"
            if not product["orderable"]:
                state = "Composition à valider"
            price_class = PRICE if product["price_confirmed"] else PRICE_MISSING
            rows.append(
                f"""
                <article class="border-b border-line py-4 last:border-b-0">
                  <div class="flex items-baseline justify-between gap-4">
                    <h3 class="font-display text-2xl leading-tight"><a class="hover:text-terracotta-deep" href="/produit/{esc(product['slug'])}">{esc(product['name'])}</a></h3>
                    <span class="{price_class}">{esc(price_label(product))}</span>
                  </div>
                  <p class="mt-1 {MUTED}">{esc(product['description'])}</p>
                  <p class="mt-2 text-xs uppercase tracking-[0.12em] text-ink-soft">{esc(state)}</p>
                </article>
                """
            )
        blocks.append(f'<section class="mt-8 {PANEL} px-5"><h2 class="border-b border-line py-4 font-display text-3xl text-ink">{esc(name)}</h2><div>{"".join(rows)}</div></section>')
    body = f"""
      <p class="{EYEBROW}">La carte</p>
      <h1 class="mt-3 {H1}">Commander</h1>
      <form class="mt-6 flex gap-2" method="get" action="/carte" role="search">
        <input class="{INPUT}" type="search" name="q" value="{esc(text)}" placeholder="Rechercher un plat" aria-label="Rechercher un plat">
        {f'<input type="hidden" name="categorie" value="{esc(slug)}">' if slug else ''}
        <button class="{BTN_GHOST} shrink-0" type="submit">Chercher</button>
      </form>
      <div class="mt-4 flex gap-2 overflow-x-auto pb-1" aria-label="Catégories">{''.join(chips)}</div>
      {''.join(blocks)}
      <p class="mt-8 {MUTED}">Les prix non publiés sur la carte d'origine restent marqués « prix à valider ». Le restaurant les confirme dans l'administration avant qu'une commande soit possible. Allergènes non communiqués.</p>
    """
    return _html(ctx, "La carte", body)


def product(ctx, slug, errors=None):
    item = product_by_slug(ctx.conn, slug)
    if not item:
        return None
    groups = groups_for_product(ctx.conn, item["id"])
    fields = []
    for group, choices in groups:
        options = []
        for choice in choices:
            if choice["price_delta_confirmed"] and choice["price_delta_cents"] is not None:
                extra = format_eur(choice["price_delta_cents"])
                if choice["price_delta_cents"] == 0:
                    extra = "inclus"
                else:
                    extra = "+" + extra
            else:
                extra = "supplément à valider"
            disabled = "" if choice["available"] else " disabled"
            options.append(
                f"""
                <label class="{CHOICE}">
                  <input type="radio" name="groupe-{group['id']}" value="{choice['id']}" required
                    data-delta="{choice['price_delta_cents'] or 0}"
                    data-delta-confirmed="{1 if choice['price_delta_confirmed'] else 0}"{disabled}>
                  <span>{esc(choice['name'])} <span class="text-ink-soft">— {esc(extra)}</span></span>
                </label>
                """
            )
        fields.append(
            f'<fieldset class="mt-5 space-y-2 rounded-2xl border border-line p-4"><legend class="px-1 font-display text-xl">{esc(group["name"])}{" *" if group["required"] else ""}</legend>{"".join(options)}</fieldset>'
        )
    notes = ""
    if load_json_setting(ctx.conn, "allow_notes", 0):
        notes = f'<label class="{FIELD}"><span>Instructions</span><textarea class="{INPUT}" name="notes" maxlength="280"></textarea></label>'
    image = (
        f'<img class="aspect-square w-full rounded-2xl object-cover" src="/images/{esc(item["image"])}" alt="{esc(item["name"])}">'
        if item["image"]
        else f'<p class="{NOTICE}">Photo non fournie pour ce produit.</p>'
    )
    blocked = []
    if not item["available"]:
        blocked.append("Ce produit est indisponible.")
    if not item["orderable"]:
        blocked.append(item["block_reason"] or "Composition à valider par le restaurant.")
    price_ready = bool(item["price_confirmed"]) and item["price_cents"] is not None
    if item["available"] and item["orderable"]:
        price_note = ""
        if not price_ready:
            price_note = f'<p class="mt-3 {MUTED}">Le restaurant confirme ce prix avant de pouvoir le commander.</p>'
        action = f"""
            <label class="{FIELD}"><span>Quantité</span><input class="{INPUT} max-w-28" name="quantite" type="number" min="1" max="20" value="1" required></label>
            {notes}
            <div class="mt-6"><button class="{BTN}" type="submit">Ajouter au panier</button></div>
            {price_note}
        """
    else:
        action = ""
    price_class = PRICE if price_ready else PRICE_MISSING
    body = f"""
      <a class="mb-6 inline-flex h-11 w-11 items-center justify-center rounded-xl border border-line text-xl text-ink hover:border-ink" href="/carte?categorie={esc(item['category_slug'])}" aria-label="Retour">←</a>
      <article class="grid gap-8 lg:grid-cols-2 lg:items-start">
        {image}
        <div>
          <p class="{EYEBROW}">{esc(item['category_name'])}</p>
          <h1 class="mt-3 {H1}">{esc(item['name'])}</h1>
          <p class="{LEAD}">{esc(item['description'])}</p>
          {errors_block(errors)}
          {errors_block(blocked)}
          <form class="mt-6" method="post" action="/panier/ajouter" data-once data-product-form
            data-base-cents="{item['price_cents'] if item['price_cents'] is not None else ''}"
            data-base-confirmed="{1 if price_ready else 0}">
            {hidden('csrf', ctx.session['csrf'])}
            {hidden('produit', item['id'])}
            <p class="font-display text-3xl {price_class}" data-live-price>{esc(price_label(item))}</p>
            {''.join(fields)}
            {action}
          </form>
        </div>
      </article>
    """
    return _html(ctx, item["name"], body)


def cart(ctx, errors=None):
    totals = cart_totals(ctx.conn, ctx.session["id"])
    rows = []
    for item, quote in totals["lines"]:
        name = quote.product["name"] if quote.product else "Produit retiré"
        issue = errors_block(quote.issues)
        line = format_eur(quote.line_cents) if quote.line_cents is not None and not quote.issues else "Prix à valider"
        rows.append(
            f"""
            <article class="border-b border-line py-5 last:border-b-0">
              <div class="flex items-baseline justify-between gap-4">
                <h3 class="font-display text-2xl">{esc(name)}</h3>
                <span class="{PRICE}">{esc(line)}</span>
              </div>
              <p class="mt-1 {MUTED}">{esc(quote.summary)}</p>
              {f'<p class="mt-1 {MUTED}">{esc(quote.notes)}</p>' if quote.notes else ''}
              {issue}
              <form class="mt-3 flex flex-wrap items-end gap-3" method="post" action="/panier/modifier">
                {hidden('csrf', ctx.session['csrf'])}
                {hidden('article', item['id'])}
                <label class="text-sm">Quantité <input class="{INPUT} mt-1 w-24" name="quantite" type="number" min="1" max="20" value="{item['quantity']}"></label>
                <button class="{BTN_GHOST}" type="submit">Mettre à jour</button>
              </form>
              <form class="mt-2" method="post" action="/panier/supprimer">
                {hidden('csrf', ctx.session['csrf'])}
                {hidden('article', item['id'])}
                <button class="{BTN_TEXT}" type="submit">Retirer</button>
              </form>
            </article>
            """
        )
    summary = ""
    if totals["priced"]:
        summary = f"""
          <div class="mt-6 divide-y divide-line border-y border-line">
            <div class="flex justify-between py-2 text-sm"><span>Sous-total</span><span>{esc(format_eur(totals['subtotal']))}</span></div>
            <div class="flex justify-between py-2 text-sm"><span>Réduction</span><span>{esc(format_eur(totals['discount']))}</span></div>
            <div class="flex justify-between py-3 font-medium"><span>Avant livraison</span><span>{esc(format_eur(totals['subtotal'] - totals['discount']))}</span></div>
          </div>
          <p class="mt-3 {MUTED}">Les frais de livraison sont ajoutés au moment du choix du mode, uniquement si une zone est configurée.</p>
        """
    elif totals["lines"]:
        summary = f'<p class="mt-6 {PRICE_MISSING}">Total indisponible : des prix ou des options restent à valider.</p>'
    code = totals["cart"]["promo_code"] if totals["cart"] and totals["cart"]["promo_code"] else ""
    body = f"""
      <p class="{EYEBROW}">Panier</p>
      <h1 class="mt-3 {H1}">Votre commande</h1>
      {errors_block(errors)}
      {errors_block([totals['promo_error']] if totals['promo_error'] else [])}
      <div class="mt-6 {PANEL} px-5">{''.join(rows) if rows else f'<p class="py-5 {MUTED}">Votre panier est vide.</p>'}</div>
      {summary}
      <form class="mt-6 flex flex-wrap items-end gap-3" method="post" action="/panier/code">
        {hidden('csrf', ctx.session['csrf'])}
        <label class="min-w-0 flex-1 text-sm">Code promotionnel <input class="{INPUT} mt-1" name="code" value="{esc(code)}" autocomplete="off"></label>
        <button class="{BTN_GHOST}" type="submit">Appliquer</button>
      </form>
      <div class="mt-6"><a class="{BTN}" href="/commander">Continuer</a></div>
    """
    return _html(ctx, "Panier", body)


def checkout(ctx, errors=None):
    totals = cart_totals(ctx.conn, ctx.session["id"])
    if not totals["lines"]:
        return cart(ctx, ["Votre panier est vide."])
    key = ctx.session["idempotency_key"]
    used = False
    if key:
        used = ctx.conn.execute(
            "SELECT 1 FROM orders WHERE idempotency_key = ?",
            (key,),
        ).fetchone()
    if not key or used:
        key = set_idempotency_key(ctx.conn, ctx.session["id"])
    zones = active_zones(ctx.conn)
    slots = open_slots(ctx.conn)
    points = active_points(ctx.conn)
    methods = active_payment_methods(ctx.conn)
    terms = load_json_setting(ctx.conn, "terms_text", "")
    zone_fields = "".join(
        f'<label class="{CHOICE}"><input type="radio" name="zone_id" value="{zone["id"]}"> <span>{esc(zone["name"])} — {esc(format_eur(zone["fee_cents"]))}</span></label>'
        for zone in zones
    ) or f'<p class="{PRICE_MISSING}">Aucune zone de livraison n\'est configurée. La livraison ne peut pas être validée.</p>'
    slot_fields = "".join(
        f'<label class="{CHOICE}"><input type="radio" name="slot_id" value="{slot["id"]}"> <span>{esc(slot["slot_date"])} · {esc(slot["start_time"])}–{esc(slot["end_time"])}</span></label>'
        for slot in slots
    ) or f'<p class="{PRICE_MISSING}">Aucun créneau de retrait n\'est ouvert.</p>'
    if len(points) > 1:
        point_fields = "".join(
            f'<label class="{CHOICE}"><input type="radio" name="point_id" value="{point["id"]}"> <span>{esc(point["name"])} — {esc(point["address"])}</span></label>'
            for point in points
        )
    elif points:
        point_fields = f'<p class="mt-3 text-sm">{esc(points[0]["name"])}<br>{esc(points[0]["address"])}</p>'
    else:
        point_fields = f'<p class="{PRICE_MISSING}">Aucun point de retrait n\'est actif.</p>'
    pay_fields = "".join(
        f'<label class="{CHOICE}"><input type="radio" name="paiement" value="{esc(method["code"])}" required> <span>{esc(method["label"])}</span></label>'
        for method in methods
    ) or f'<p class="{PRICE_MISSING}">Aucun moyen de règlement n\'est activé. Le paiement carte n\'est pas branché et aucun règlement sur place n\'est autorisé pour le moment.</p>'
    if isinstance(terms, str) and terms.strip():
        terms_field = f'<label class="{CHECK}"><input type="checkbox" name="conditions" value="1"> <span>{esc(terms)}</span></label>'
    else:
        terms_field = f'<p class="mt-4 {MUTED}">Les conditions générales de vente ne sont pas encore publiées. Aucune case fictive n\'est demandée.</p>'
    user = ctx.user
    body = f"""
      <p class="{EYEBROW}">Commande</p>
      <h1 class="mt-3 {H1}">Retrait ou livraison</h1>
      {errors_block(errors)}
      <form class="mt-6" method="post" action="/commander" data-once>
        {hidden('csrf', ctx.session['csrf'])}
        {hidden('idempotency_key', key)}
        <div class="grid gap-4 lg:grid-cols-2">
          <section class="{PANEL_PAD}">
            <h2 class="font-display text-2xl">Click &amp; Collect</h2>
            <label class="mt-4 {CHOICE}"><input type="radio" name="mode" value="pickup" required> <span>Je retire au restaurant</span></label>
            {point_fields}
            <fieldset class="mt-4 space-y-2"><legend class="font-display text-xl">Créneau</legend>{slot_fields}</fieldset>
          </section>
          <section class="rounded-2xl bg-night p-5 text-cream">
            <h2 class="font-display text-2xl">Livraison</h2>
            <label class="mt-4 flex min-h-11 items-center gap-3 rounded-xl border border-cream/30 px-3 py-2 text-sm has-checked:border-saffron"><input type="radio" name="mode" value="delivery"> <span>Je me fais livrer</span></label>
            <fieldset class="mt-4 space-y-2"><legend class="font-display text-xl">Zone</legend>{zone_fields}</fieldset>
            <p class="mt-3 text-sm text-cream/75">L'adresse n'est pas vérifiée automatiquement. Seules les zones enregistrées par le restaurant sont proposées.</p>
            <label class="mt-4 flex flex-col gap-1.5 text-sm"><span>Rue</span><input class="rounded-xl border border-cream/30 bg-transparent px-3 py-2.5 text-cream outline-none focus:border-saffron" name="rue" autocomplete="street-address"></label>
            <label class="mt-4 flex flex-col gap-1.5 text-sm"><span>Code postal</span><input class="rounded-xl border border-cream/30 bg-transparent px-3 py-2.5 text-cream outline-none focus:border-saffron" name="code_postal" autocomplete="postal-code"></label>
            <label class="mt-4 flex flex-col gap-1.5 text-sm"><span>Ville</span><input class="rounded-xl border border-cream/30 bg-transparent px-3 py-2.5 text-cream outline-none focus:border-saffron" name="ville" autocomplete="address-level2"></label>
          </section>
        </div>
        <label class="{FIELD}"><span>Nom</span><input class="{INPUT}" name="nom" required value="{esc(user['name'] if user else '')}"></label>
        <label class="{FIELD}"><span>E-mail</span><input class="{INPUT}" name="email" type="email" required value="{esc(user['email'] if user else '')}"></label>
        <label class="{FIELD}"><span>Téléphone</span><input class="{INPUT}" name="telephone" required value="{esc(user['phone'] if user and user['phone'] else '')}"></label>
        <fieldset class="mt-6 space-y-2"><legend class="font-display text-xl">Règlement</legend>{pay_fields}</fieldset>
        {terms_field}
        <p class="mt-5 {NOTICE}">Aucun paiement n'est encaissé en ligne. Une commande n'est enregistrée que si les prix, le mode et le règlement ont été validés côté serveur. Le statut de paiement reste « non encaissé ».</p>
        <button class="{BTN}" type="submit">Valider la commande</button>
      </form>
    """
    return _html(ctx, "Valider", body)


def _payment_notice(order):
    status = order["payment_status"]
    if status == "paid" and order["payment_method"] == "stripe":
        return "Paiement encaissé. Stripe a confirmé le montant de cette commande."
    if status == "paid":
        return "Paiement enregistré au restaurant. Aucun encaissement en ligne n'a été utilisé."
    if status == "pending":
        return "Paiement en attente. L'arrivée sur une page ne confirme pas l'encaissement."
    if status == "failed":
        return "Paiement refusé. La commande n'est pas encaissée."
    if status == "cancelled":
        return "Paiement annulé. La commande n'est pas encaissée."
    return "Paiement non encaissé. Aucun prestataire de paiement n'a confirmé d'encaissement."


def confirmation(ctx, public_ref):
    order = order_for_session(ctx.conn, public_ref, ctx.session["id"], ctx.user["id"] if ctx.user else None)
    if not order:
        return None
    lines = json.loads(order["snapshot_json"])
    rows = "".join(
        f'<li class="border-b border-line py-3"><strong>{esc(line["name"])}</strong> × {line["quantity"]} — {esc(format_eur(line["line_cents"]))}<br><span class="{MUTED}">{esc(line["options"])}</span></li>'
        for line in lines
    )
    body = f"""
      <p class="{EYEBROW}">Confirmation</p>
      <h1 class="mt-3 {H1}">Commande {esc(order['public_ref'])}</h1>
      <p class="mt-4">Statut : <strong>{esc(STATUS_LABELS.get(order['status'], order['status']))}</strong></p>
      <p class="mt-4 {NOTICE}">{esc(_payment_notice(order))}</p>
      <p class="{MUTED}">Aucun e-mail n'est envoyé : aucun service d'e-mail n'est configuré.</p>
      <ul class="mt-6">{rows}</ul>
      <div class="mt-6 divide-y divide-line border-y border-line">
        <div class="flex justify-between py-2 text-sm"><span>Sous-total</span><span>{esc(format_eur(order['subtotal_cents']))}</span></div>
        <div class="flex justify-between py-2 text-sm"><span>Livraison</span><span>{esc(format_eur(order['delivery_fee_cents']))}</span></div>
        <div class="flex justify-between py-2 text-sm"><span>Réduction</span><span>{esc(format_eur(order['discount_cents']))}</span></div>
        <div class="flex justify-between py-3 font-medium"><span>Total</span><span>{esc(format_eur(order['total_cents']))}</span></div>
      </div>
      <p class="mt-8"><a class="{BTN}" href="/carte">Commander autre chose</a></p>
    """
    return _html(ctx, order["public_ref"], body)


def account(ctx, errors=None, mode="login"):
    if ctx.user and ctx.user["role"] == "customer":
        rows = []
        for order in orders_for_user(ctx.conn, ctx.user["id"]):
            rows.append(
                f'<li class="border-b border-line py-3"><a class="font-medium hover:text-terracotta-deep" href="/commande/{esc(order["public_ref"])}">{esc(order["public_ref"])}</a> — {esc(STATUS_LABELS.get(order["status"], order["status"]))} — {esc(format_eur(order["total_cents"]))}</li>'
            )
        body = f"""
          <h1 class="{H1}">Bonjour {esc(ctx.user['name'])}</h1>
          <h2 class="mt-8 {H2}">Commandes</h2>
          <ul class="mt-4">{''.join(rows) if rows else f'<li class="{MUTED}">Aucune commande liée à ce compte.</li>'}</ul>
          <form class="mt-6" method="post" action="/compte/deconnexion">{hidden('csrf', ctx.session['csrf'])}<button class="{BTN_GHOST}" type="submit">Se déconnecter</button></form>
        """
        return _html(ctx, "Compte", body)
    if ctx.user and ctx.user["role"] == "admin":
        body = f'<p>Vous êtes connecté à l\'administration.</p><p class="mt-4"><a class="{BTN}" href="/admin">Ouvrir l\'administration</a></p>'
        return _html(ctx, "Compte", body)
    if ctx.user and ctx.user["role"] == "driver":
        body = f'<p>Vous êtes connecté en tant que livreur.</p><p class="mt-4"><a class="{BTN}" href="/admin/livreurs">Ouvrir mes courses</a></p>'
        return _html(ctx, "Compte", body)
    body = f"""
      <div class="grid gap-10 lg:grid-cols-2">
        <section>
          <h1 class="{H1}">Connexion</h1>
          {errors_block(errors if mode == 'login' else None)}
          <form class="mt-4" method="post" action="/compte/connexion">
            {hidden('csrf', ctx.session['csrf'])}
            <label class="{FIELD}"><span>E-mail</span><input class="{INPUT}" name="email" type="email" required></label>
            {password_field("password", label="Mot de passe", autocomplete="current-password")}
            <button class="mt-5 {BTN}" type="submit">Se connecter</button>
          </form>
        </section>
        <section>
          <h2 class="{H2}">Créer un compte</h2>
          <p class="mt-3 {MUTED}">La commande invité reste possible sans compte.</p>
          {errors_block(errors if mode == 'register' else None)}
          <form method="post" action="/compte/inscription">
            {hidden('csrf', ctx.session['csrf'])}
            <label class="{FIELD}"><span>Nom</span><input class="{INPUT}" name="nom" required></label>
            <label class="{FIELD}"><span>E-mail</span><input class="{INPUT}" name="email" type="email" required></label>
            <label class="{FIELD}"><span>Téléphone</span><input class="{INPUT}" name="telephone"></label>
            {password_field("password", label="Mot de passe", required=True, autocomplete="new-password", extra='minlength="10"')}
            <button class="mt-5 {BTN_GHOST}" type="submit">Créer le compte</button>
          </form>
        </section>
      </div>
    """
    return _html(ctx, "Compte", body)


def _stat(label, value):
    return f"""
      <article class="{PANEL_PAD}">
        <p class="text-xs uppercase tracking-[0.14em] text-ink-soft">{esc(label)}</p>
        <p class="mt-2 font-display text-4xl leading-none">{esc(value)}</p>
      </article>
    """


def admin_home(ctx):
    stats = dashboard_stats(ctx.conn)
    figures = "".join(
        (
            _stat("Commandes du jour", stats["today"]),
            _stat("En cours", stats["open"]),
            _stat("Encaissé", format_eur(stats["collected_cents"])),
            _stat("À encaisser", format_eur(stats["due_cents"])),
            _stat("Retraits", stats["pickup"]),
            _stat("Livraisons", stats["delivery"]),
            _stat("Terminées", stats["counts"]["completed"]),
            _stat("Annulées", stats["counts"]["cancelled"]),
        )
    )
    kitchen = "".join(
        f'<li class="flex justify-between border-b border-line py-2"><span>{esc(STATUS_LABELS[key])}</span><span>{stats["counts"][key]}</span></li>'
        for key in KITCHEN_STATUSES
        if key not in {"completed", "cancelled"}
    )
    ready = "".join(
        (
            _stat("Plats vendables", stats["sellable"]),
            _stat("Prix à valider", stats["missing_prices"]),
            _stat("Zones actives", stats["zones"]),
            _stat("Créneaux du jour", stats["slots_today"]),
            _stat("Créneaux à venir", stats["slots"]),
            _stat("Règlements hors ligne", stats["payments"]),
        )
    )
    body = f"""
      <p class="{EYEBROW}">Administration</p>
      <h1 class="mt-3 {H1}">Tableau de bord</h1>
      <p class="mt-3 {MUTED}">Journée du {esc(stats['day'])}. Les montants viennent des commandes enregistrées.</p>
      <div class="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">{figures}</div>
      <div class="mt-8 grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <section>
          <h2 class="font-display text-3xl">Cuisine</h2>
          <ul class="mt-4 text-sm">{kitchen}</ul>
        </section>
        <section>
          <h2 class="font-display text-3xl">Prêt à vendre</h2>
          <div class="mt-4 grid gap-3 sm:grid-cols-2">{ready}</div>
        </section>
      </div>
      <p class="mt-8"><a class="{BTN}" href="/admin/cuisine">Ouvrir la cuisine</a></p>
    """
    return _html(ctx, "Tableau de bord", body, admin=True)


def admin_avis(ctx, query=None):
    from app.reviews import admin_list, admin_stats

    query = query or {}
    status = (query.get("statut") or ["published"])[0]
    if status not in {"published", "hidden", "pending"}:
        status = "published"
    note_raw = (query.get("note") or [""])[0]
    try:
        note = int(note_raw) if note_raw else None
    except ValueError:
        note = None
    search = (query.get("q") or [""])[0]
    stats = admin_stats(ctx.conn)
    rows = admin_list(ctx.conn, status=status, note=note, q=search)
    histogram = "".join(
        f'<li class="flex justify-between border-b border-line py-2 text-sm"><span>{item["stars"]} ★</span><span>{item["count"]}</span></li>'
        for item in stats["histogram"]
    )
    trend = "".join(
        f'<li class="flex justify-between border-b border-line py-2 text-sm"><span>{esc(item["day"])}</span><span>{item["count"]} · {esc(item["average"] if item["average"] is not None else "—")}</span></li>'
        for item in stats["trend"][-7:]
    )
    cards = []
    for row in rows:
        stars = "★" * int(row["stars"]) + "☆" * (5 - int(row["stars"]))
        verified = (
            '<span class="ml-2 rounded-full border border-line px-2 py-0.5 text-[0.65rem] uppercase tracking-[0.12em]">Achat vérifié</span>'
            if row["verified"]
            else ""
        )
        order_ref = esc(row["public_ref"]) if row["public_ref"] else "—"
        reply = (
            f'<p class="mt-3 border-l-2 border-saffron pl-3 text-sm text-ink-soft"><strong>Réponse</strong> — {esc(row["reply_body"])}</p>'
            if row["reply_body"]
            else ""
        )
        hide_note = (
            f'<p class="mt-2 text-xs text-terracotta-deep">Masqué : {esc(row["hidden_reason"])}</p>'
            if row["status"] == "hidden" and row["hidden_reason"]
            else ""
        )
        if row["status"] == "published":
            moderate = f"""
              <form class="mt-3 flex flex-wrap items-end gap-2" method="post" action="/admin/avis/{row['id']}/masquer">
                {hidden('csrf', ctx.session['csrf'])}
                <label class="text-sm grow"><span class="mb-1 block">Motif de masquage</span>
                  <input class="{INPUT}" name="motif" required maxlength="240">
                </label>
                <button class="{BTN_GHOST}" type="submit">Masquer</button>
              </form>
            """
        else:
            moderate = f"""
              <form class="mt-3" method="post" action="/admin/avis/{row['id']}/publier">
                {hidden('csrf', ctx.session['csrf'])}
                <button class="{BTN_GHOST}" type="submit">Republier</button>
              </form>
            """
        cards.append(
            f"""
            <article class="border border-line bg-cream p-5">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p class="font-medium">{esc(row['author'])}{verified}</p>
                  <p class="mt-1 text-sm text-terracotta" aria-label="{row['stars']} sur 5">{stars}</p>
                </div>
                <p class="text-xs text-ink-soft">{esc(row['created_at'][:10])} · {order_ref}</p>
              </div>
              <p class="mt-4 text-sm leading-relaxed">{esc(row['body'])}</p>
              {reply}
              {hide_note}
              <p class="mt-3 text-xs text-ink-soft">Utile : {row['useful_count'] or 0}</p>
              <form class="mt-4" method="post" action="/admin/avis/{row['id']}/repondre">
                {hidden('csrf', ctx.session['csrf'])}
                <label class="{FIELD}"><span>Réponse officielle</span>
                  <textarea class="{INPUT} min-h-20" name="reponse" maxlength="800" required>{esc(row['reply_body'] or '')}</textarea>
                </label>
                <button class="mt-3 {BTN}" type="submit">Enregistrer la réponse</button>
              </form>
              {moderate}
              <form class="mt-2" method="post" action="/admin/avis/{row['id']}/supprimer" onsubmit="return confirm('Supprimer définitivement cet avis ?');">
                {hidden('csrf', ctx.session['csrf'])}
                <button class="{BTN_TEXT}" type="submit">Supprimer</button>
              </form>
            </article>
            """
        )
    note_options = "".join(
        f'<option value="{n}"{" selected" if note == n else ""}>{n} ★</option>'
        for n in range(5, 0, -1)
    )
    status_options = "".join(
        f'<option value="{key}"{" selected" if key == status else ""}>{esc(label)}</option>'
        for key, label in (("published", "Publiés"), ("hidden", "Masqués"), ("pending", "En attente"))
    )
    avg = stats["average"]
    avg_label = str(avg).replace(".", ",") if avg is not None else "—"
    body = f"""
      <p class="{EYEBROW}">Réputation</p>
      <h1 class="mt-3 {H1}">Avis clients</h1>
      <p class="mt-3 {MUTED}">Note moyenne {esc(avg_label)} · {stats['count']} publiés · {stats['verified']} vérifiés · {stats['hidden']} masqués · {stats['reports']} signalements</p>
      <div class="mt-6 grid gap-6 lg:grid-cols-2">
        <section class="{PANEL_PAD}">
          <h2 class="font-display text-2xl">Répartition</h2>
          <ul class="mt-3">{histogram or '<li class="text-sm text-ink-soft">Aucun avis.</li>'}</ul>
        </section>
        <section class="{PANEL_PAD}">
          <h2 class="font-display text-2xl">Évolution (14 jours)</h2>
          <ul class="mt-3">{trend or '<li class="text-sm text-ink-soft">Pas encore de tendance.</li>'}</ul>
        </section>
      </div>
      <form class="mt-8 flex flex-wrap items-end gap-3" method="get" action="/admin/avis">
        <label class="text-sm"><span class="mb-1 block">Statut</span>
          <select class="{INPUT}" name="statut">{status_options}</select>
        </label>
        <label class="text-sm"><span class="mb-1 block">Note</span>
          <select class="{INPUT}" name="note"><option value="">Toutes</option>{note_options}</select>
        </label>
        <label class="text-sm grow"><span class="mb-1 block">Recherche</span>
          <input class="{INPUT}" name="q" value="{esc(search)}" placeholder="Auteur, texte…">
        </label>
        <button class="{BTN}" type="submit">Filtrer</button>
      </form>
      <div class="mt-6 grid gap-4">{''.join(cards) if cards else '<p class="text-sm text-ink-soft">Aucun avis pour ces filtres.</p>'}</div>
    """
    return _html(ctx, "Avis", body, admin=True)


def admin_cuisine(ctx, query=None):
    from app.kitchen import render_kitchen

    return _html(ctx, "Cuisine", render_kitchen(ctx, query or {}), admin=True)


def admin_login(ctx, errors=None):
    admins = ctx.conn.execute("SELECT COUNT(*) AS n FROM users WHERE role = 'admin'").fetchone()["n"]
    note = ""
    if not admins:
        note = f'<p class="{NOTICE}">Aucun administrateur n\'est configuré. Définissez ALLOKO_ADMIN_EMAIL et ALLOKO_ADMIN_PASSWORD avant de lancer le serveur.</p>'
    body = f"""
      <a class="inline-block" href="/"><img class="h-14 w-auto" src="/images/logo-dark.png" width="532" height="299" alt="ALLOKODRONE"></a>
      <h1 class="mt-8 {H1}">Connexion service</h1>
      <p class="mt-3 {MUTED}">Administrateur : tableau de bord complet. Livreur : suivi des courses uniquement.</p>
      <div class="mt-6">
        {note}
        {errors_block(errors)}
        <form method="post" action="/admin/connexion">
          {hidden('csrf', ctx.session['csrf'])}
          <label class="{FIELD}"><span>E-mail</span><input class="{INPUT}" name="email" type="email" required></label>
          {password_field("password", label="Mot de passe", autocomplete="current-password")}
          <button class="mt-5 {BTN}" type="submit">Entrer</button>
        </form>
      </div>
    """
    return login_page("Connexion service", body, flash=ctx.flash)


def _tick(name, on, label):
    checked = " checked" if on else ""
    return (
        f'<label class="flex min-h-11 items-start gap-3 text-sm leading-snug text-ink">'
        f'<input type="checkbox" name="{esc(name)}" value="1"{checked}><span>{label}</span></label>'
    )


def _product_photo(product):
    if not product["image"]:
        return (
            '<div class="flex aspect-square w-full items-center justify-center rounded-2xl border border-dashed '
            'border-line bg-paper-2 px-4 text-center text-sm text-ink-soft">Sans photo</div>'
        )
    crop = " object-[center_22%]" if product["slug"] == "bowl" else ""
    return (
        f'<img class="aspect-square w-full rounded-2xl object-cover{crop}" '
        f'src="/images/{esc(product["image"])}" alt="">'
    )


def _choice_row(choice):
    delta = "" if choice["price_delta_cents"] is None else f"{choice['price_delta_cents'] / 100:.2f}"
    return f"""
      <li class="grid gap-3 rounded-xl border border-line bg-paper p-3 sm:grid-cols-[minmax(0,1fr)_9rem] sm:items-end">
        <div class="min-w-0">
          <p class="text-sm font-medium">{esc(choice["name"])}</p>
          <div class="mt-1 grid sm:grid-cols-2">
            {_tick(f"choix_ok-{choice['id']}", choice["price_delta_confirmed"], "Supplément validé")}
            {_tick(f"choix_dispo-{choice['id']}", choice["available"], "Option disponible")}
          </div>
        </div>
        <label class="flex flex-col gap-1.5 text-sm text-ink">
          <span>Supplément €</span>
          <input class="{INPUT}" name="choix-{choice['id']}" inputmode="decimal" value="{esc(delta)}">
        </label>
      </li>
    """


def admin_products(ctx, message=""):
    sections = []
    category = None
    cards = []
    for product in list_products(ctx.conn):
        if product["category_name"] != category:
            if cards:
                sections.append((category, cards))
            category = product["category_name"]
            cards = []
        groups = []
        for group, options in groups_for_product(ctx.conn, product["id"]):
            rows = "".join(_choice_row(choice) for choice in options)
            groups.append(
                f"""
                <section class="mt-6 border-t border-line pt-5">
                  <h3 class="font-display text-xl">{esc(group["name"])}</h3>
                  <ul class="mt-3 grid gap-3">{rows}</ul>
                </section>
                """
            )
        price = "" if product["price_cents"] is None else f"{product['price_cents'] / 100:.2f}"
        description = (
            f'<p class="mt-3 max-w-2xl {MUTED}">{esc(product["description"])}</p>'
            if product["description"]
            else ""
        )
        cards.append(
            f"""
            <form class="mt-4 {PANEL_PAD}" method="post" action="/admin/produits/{product['id']}">
              {hidden('csrf', ctx.session['csrf'])}
              <div class="grid items-start gap-5 lg:grid-cols-[14rem_minmax(0,1fr)]">
                <div class="mx-auto w-full max-w-56 lg:mx-0 lg:max-w-none">{_product_photo(product)}</div>
                <div class="min-w-0">
                  <h2 class="font-display text-3xl leading-none">{esc(product['name'])}</h2>
                  {description}
                  <label class="mt-5 flex max-w-xs flex-col gap-1.5 text-sm text-ink">
                    <span>Prix de vente en euros</span>
                    <input class="{INPUT}" name="prix" inputmode="decimal" value="{esc(price)}">
                  </label>
                  <div class="mt-3">
                    {_tick("prix_confirme", product["price_confirmed"], "Prix validé, le produit peut être vendu à ce montant")}
                  </div>
                  <div class="grid sm:grid-cols-3">
                    {_tick("disponible", product["available"], "Disponible")}
                    {_tick("commandable", product["orderable"], "Commandable")}
                    {_tick("signature", product["featured"], "Mis en avant")}
                  </div>
                  <label class="{FIELD}"><span>Raison de blocage</span><input class="{INPUT}" name="blocage" value="{esc(product['block_reason'] or '')}"></label>
                </div>
              </div>
              {''.join(groups)}
              <button class="mt-5 {BTN}" type="submit">Enregistrer</button>
            </form>
            """
        )
    if cards:
        sections.append((category, cards))
    listed = "".join(
        f'<section class="mt-10"><h2 class="font-display text-3xl">{esc(name)}</h2>{"".join(forms)}</section>'
        for name, forms in sections
    )
    body = f"""
      <p class="{EYEBROW}">Carte</p>
      <h1 class="mt-3 {H1}">Produits</h1>
      {f'<p class="mt-4 {NOTICE}" role="status">{esc(message)}</p>' if message else ''}
      {listed}
    """
    return _html(ctx, "Produits", body, admin=True)


def admin_orders(ctx, query=None):
    query = query or {}
    status = (query.get("statut") or [""])[0]
    day = (query.get("date") or [""])[0]
    if status not in KITCHEN_STATUSES:
        status = ""
    if not _date_ok(day):
        day = ""
    rows = []
    for order in orders_sheet(ctx.conn, status=status or None, day=day or None):
        rows.append(
            f"""
            <tr class="border-b border-line">
              <td class="py-3 pr-3"><a class="font-medium hover:text-terracotta-deep" href="/admin/commandes/{order['id']}">{esc(order['public_ref'])}</a></td>
              <td class="py-3 pr-3">{esc(order['customer_name'])}<br><span class="text-ink-soft">{esc(order['phone'])}</span></td>
              <td class="py-3 pr-3">{esc(when_label(order))}</td>
              <td class="py-3 pr-3">{esc(STATUS_LABELS.get(order['status'], order['status']))}</td>
              <td class="py-3">{esc(format_eur(order['total_cents']))}<br><span class="text-ink-soft">{esc(payment_summary(order))}</span></td>
            </tr>
            """
        )
    status_options = "".join(
        f'<option value="{key}"{" selected" if key == status else ""}>{esc(label)}</option>'
        for key, label in STATUS_LABELS.items()
        if key in KITCHEN_STATUSES
    )
    body = f"""
      <h1 class="{H1}">Commandes</h1>
      <form class="mt-6 flex flex-wrap items-end gap-3" method="get" action="/admin/commandes">
        <label class="text-sm"><span class="mb-1 block">Statut</span>
          <select class="{INPUT}" name="statut"><option value="">Tous</option>{status_options}</select>
        </label>
        <label class="text-sm"><span class="mb-1 block">Jour</span>
          <input class="{INPUT}" type="date" name="date" value="{esc(day)}">
        </label>
        <button class="{BTN}" type="submit">Filtrer</button>
      </form>
      <div class="mt-6 overflow-x-auto">
        <table class="w-full min-w-[40rem] text-left text-sm">
          <thead class="border-b border-ink text-xs uppercase tracking-[0.12em]">
            <tr><th class="py-2 pr-3">Numéro</th><th class="py-2 pr-3">Client</th><th class="py-2 pr-3">Mode</th><th class="py-2 pr-3">Statut</th><th class="py-2">Total</th></tr>
          </thead>
          <tbody>{''.join(rows) if rows else '<tr><td class="py-4" colspan="5">Aucune commande.</td></tr>'}</tbody>
        </table>
      </div>
    """
    return _html(ctx, "Commandes", body, admin=True)


def admin_order(ctx, order_id, error=""):
    order = next((row for row in orders_sheet(ctx.conn) if row["id"] == order_id), None)
    if not order:
        return None
    lines = json.loads(order["snapshot_json"])
    detail = "".join(
        f'<li class="border-b border-line py-2 text-sm">{esc(line["quantity"])} × {esc(line["name"])} — {esc(line["options"])} — {esc(format_eur(line["line_cents"]))}</li>'
        for line in lines
    )
    options = "".join(
        f'<option value="{key}"{" selected" if key == order["status"] else ""}>{esc(label)}</option>'
        for key, label in ((key, STATUS_LABELS[key]) for key in KITCHEN_STATUSES)
    )
    collect = ""
    if order["payment_method"] in {"pay_at_pickup", "pay_on_delivery"} and order["payment_status"] != "paid":
        collect = f"""
          <form class="mt-4" method="post" action="/admin/commandes/{order['id']}/encaisser">
            {hidden('csrf', ctx.session['csrf'])}
            <button class="{BTN_GHOST}" type="submit">Enregistrer l'encaissement au restaurant</button>
          </form>
        """
    body = f"""
      <h1 class="{H1}">{esc(order['public_ref'])}</h1>
      <div class="mt-4">{errors_block([error] if error else [])}</div>
      <p class="text-sm leading-relaxed">{esc(order['customer_name'])}<br>{esc(order['email'])}<br>{esc(order['phone'])}</p>
      <p class="mt-3 text-sm">{esc(when_label(order))}<br>{esc(place_label(order))}</p>
      <ul class="mt-4">{detail}</ul>
      <p class="mt-4 text-sm">Paiement : {esc(payment_summary(order))}</p>
      <form class="mt-4 max-w-md" method="post" action="/admin/commandes/{order['id']}/statut">
        {hidden('csrf', ctx.session['csrf'])}
        <label class="{FIELD}"><span>Statut en cuisine</span><select class="{INPUT}" name="statut">{options}</select></label>
        <button class="mt-4 {BTN}" type="submit">Enregistrer le statut</button>
      </form>
      {collect}
      {_order_actions(ctx, order)}
    """
    return _html(ctx, order["public_ref"], body, admin=True)


def _order_actions(ctx, order):
    blocks = []
    if order["payment_method"] == "stripe" and order["payment_status"] == "paid" and (order["stripe_payment_intent"] or "").startswith("pi_"):
        blocks.append(
            f"""
            <form class="mt-4" method="post" action="/admin/commandes/{order['id']}/rembourser">
              {hidden('csrf', ctx.session['csrf'])}
              <button class="{BTN_GHOST}" type="submit">Rembourser via Stripe</button>
            </form>
            """
        )
    if order["mode"] == "delivery" and order["status"] not in {"cancelled", "completed"}:
        from app.uber_direct import configured

        if configured() and not order["uber_delivery_id"]:
            blocks.append(
                f"""
                <form class="mt-4" method="post" action="/admin/commandes/{order['id']}/uber">
                  {hidden('csrf', ctx.session['csrf'])}
                  <button class="{BTN_GHOST}" type="submit">Demander un livreur Uber Direct</button>
                </form>
                """
            )
        elif order["uber_delivery_id"]:
            blocks.append(
                f'<p class="mt-4 text-sm">Uber Direct : {esc(order["uber_status"] or "demandé")} {esc(order["uber_tracking_url"] or "")}</p>'
            )
        else:
            blocks.append(
                '<p class="mt-4 text-sm text-ink-soft">Uber Direct n\'est pas configuré. '
                'Utilisez <a class="underline" href="/admin/livreurs">Livreurs</a> pour les courses du restaurant.</p>'
            )
        driver_name = order["driver_name"] if "driver_name" in order.keys() else None
        if driver_name:
            driver_phone = order["driver_phone"] if "driver_phone" in order.keys() else ""
            phone_bit = f" · {esc(driver_phone)}" if driver_phone else ""
            blocks.append(
                f'<p class="mt-2 text-sm">Livreur restaurant : {esc(driver_name)}{phone_bit}'
                f' — <a class="underline" href="/admin/livreurs">Voir le suivi</a></p>'
            )
    return "".join(blocks)


def _date_ok(value):
    parts = (value or "").split("-")
    return len(parts) == 3 and all(part.isdigit() for part in parts) and len(parts[0]) == 4


def admin_delivery(ctx, message=""):
    from app.delivery import customer_delivery_open, delivery_mode, geo_configured

    mode = delivery_mode(ctx.conn)
    zones = ctx.conn.execute("SELECT * FROM delivery_zones ORDER BY name, id").fetchall()
    bands = ctx.conn.execute("SELECT * FROM distance_bands ORDER BY max_meters, id").fetchall()
    open_now = customer_delivery_open(ctx.conn)
    if open_now and mode == "zones":
        status = "Livraison ouverte. Le client choisit une zone active."
    elif open_now:
        status = "Livraison ouverte. Les frais suivent le palier de distance validé."
    elif mode == "distance" and not geo_configured(ctx.conn):
        status = "Le calcul du trajet attend la clé OpenRouteService."
    elif mode == "distance":
        status = "Livraison fermée. Ajoutez au moins un palier, validez ses frais, puis activez-le."
    else:
        status = "Livraison fermée. Ajoutez au moins une zone, validez ses frais, puis activez-la."
    zone_rows = []
    for zone in zones:
        fee = format_eur(zone["fee_cents"]) if zone["fee_cents"] is not None else None
        if fee is None:
            detail = "Aucun montant enregistré."
            action = ""
        elif not zone["fee_confirmed"]:
            detail = f"{fee} enregistrés. Validez ce montant avant de pouvoir ouvrir la zone."
            action = f"""
              <form method="post" action="/admin/zones/{zone["id"]}">
                {hidden("csrf", ctx.session["csrf"])}
                {hidden("action", "confirmer")}
                <button class="{BTN}" type="submit">Valider {esc(fee)}</button>
              </form>
            """
        elif zone["active"]:
            detail = f"{fee} validés. Le client peut choisir cette zone."
            action = f"""
              <form method="post" action="/admin/zones/{zone["id"]}">
                {hidden("csrf", ctx.session["csrf"])}
                {hidden("active", "0")}
                <button class="{BTN_GHOST}" type="submit">Fermer</button>
              </form>
            """
        else:
            detail = f"{fee} validés. La zone est fermée : le client ne la voit pas."
            action = f"""
              <form method="post" action="/admin/zones/{zone["id"]}">
                {hidden("csrf", ctx.session["csrf"])}
                {hidden("active", "1")}
                <button class="{BTN}" type="submit">Ouvrir</button>
              </form>
            """
        zone_rows.append(
            f'''<li class="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3 text-sm">
              <span class="min-w-0"><span class="font-medium">{esc(zone["name"])}</span><span class="mt-1 block text-ink-soft">{esc(detail)}</span></span>
              {action}
            </li>'''
        )
    band_rows = []
    for band in bands:
        fee = format_eur(band["fee_cents"]) if band["fee_cents"] is not None else "frais non validés"
        state = "ouvert" if band["active"] else "fermé"
        band_rows.append(
            f'''<li class="flex flex-wrap items-center justify-between gap-3 border-b border-line py-3 text-sm">
              <span>Jusqu'à {band["max_meters"] / 1000:g} km — {esc(fee)} — {state}</span>
              <form method="post" action="/admin/distances/{band["id"]}">
                {hidden("csrf", ctx.session["csrf"])}
                {hidden("active", "0" if band["active"] else "1")}
                <button class="{BTN_GHOST}" type="submit">{"Fermer" if band["active"] else "Ouvrir"}</button>
              </form>
            </li>'''
        )
    if mode == "zones":
        editor = f"""
          <section class="mt-8 max-w-xl {PANEL_PAD}">
            <h2 class="font-display text-2xl">Zones</h2>
            <p class="mt-2 {MUTED}">Une zone est un nom et un prix fixe. Au moment de commander, le client choisit ce nom, et ce prix s'ajoute à la commande. L'adresse ne calcule pas le montant.</p>
            <p class="mt-2 {MUTED}">Deux gestes, dans l'ordre : validez le montant, puis ouvrez la zone. Tant qu'elle est fermée, le client ne la voit pas.</p>
            <ul class="mt-4">{''.join(zone_rows) or '<li class="text-sm text-ink-soft">Aucune zone.</li>'}</ul>
            <form method="post" action="/admin/zones">
              {hidden('csrf', ctx.session['csrf'])}
              <label class="{FIELD}"><span>Nom de la zone</span><input class="{INPUT}" name="nom" required></label>
              <label class="{FIELD}"><span>Frais en euros</span><input class="{INPUT}" name="frais" inputmode="decimal" required></label>
              <label class="{CHECK}"><input type="checkbox" name="frais_ok" value="1"> <span>Je confirme que ce montant est le tarif du restaurant</span></label>
              <label class="{CHECK}"><input type="checkbox" name="active" value="1"> <span>Ouvrir cette zone aux clients dès maintenant</span></label>
              <button class="mt-4 {BTN}" type="submit">Ajouter la zone</button>
            </form>
          </section>
        """
    else:
        map_note = ""
        if geo_configured(ctx.conn):
            map_note = f"""
            <p class="mt-3 {MUTED}">Le calcul du trajet est branché. La distance part du restaurant.</p>
            <form class="mt-3" method="post" action="/admin/livraison-cle">
              {hidden('csrf', ctx.session['csrf'])}
              {hidden('retirer', '1')}
              <button class="{BTN_GHOST}" type="submit">Retirer la clé</button>
            </form>
            """
        else:
            map_note = f"""
            <form class="mt-4" method="post" action="/admin/livraison-cle">
              {hidden('csrf', ctx.session['csrf'])}
              {password_field("cle", label="Clé OpenRouteService", required=True, autocomplete="off", extra='spellcheck="false"')}
              <button class="mt-4 {BTN}" type="submit">Brancher le calcul</button>
            </form>
            """
        editor = f"""
          <section class="mt-8 max-w-xl {PANEL_PAD}">
            <h2 class="font-display text-2xl">Paliers</h2>
            <p class="mt-2 {MUTED}">Le prix ne se tape pas à la commande. Indiquez une distance : le palier ouvert qui la couvre donne le montant. Jusqu'au palier, le prix est le même pour chaque kilomètre compris dedans.</p>
            {map_note}
            <form class="mt-4" method="post" action="/admin/livraison-essai">
              {hidden('csrf', ctx.session['csrf'])}
              <label class="{FIELD} mt-0"><span>Distance en kilomètres</span>
                <input class="{INPUT}" name="km" inputmode="decimal" required>
              </label>
              <button class="mt-4 {BTN}" type="submit">Calculer le prix</button>
            </form>
            <ul class="mt-4">{''.join(band_rows) or '<li class="text-sm text-ink-soft">Aucun palier.</li>'}</ul>
            <form method="post" action="/admin/distances">
              {hidden('csrf', ctx.session['csrf'])}
              <label class="{FIELD}"><span>Jusqu'à, en kilomètres</span><input class="{INPUT}" name="km" inputmode="decimal" required></label>
              <label class="{FIELD}"><span>Frais en euros</span><input class="{INPUT}" name="frais" inputmode="decimal" required></label>
              <label class="{CHECK}"><input type="checkbox" name="frais_ok" value="1"> <span>Je confirme que ce montant est le tarif du restaurant</span></label>
              <label class="{CHECK}"><input type="checkbox" name="active" value="1"> <span>Ouvrir ce palier aux clients dès maintenant</span></label>
              <button class="mt-4 {BTN}" type="submit">Ajouter le palier</button>
            </form>
          </section>
        """
    kept = len(bands) if mode == "zones" else len(zones)
    kept_label = (
        f"{kept} palier{'s' if kept != 1 else ''} de distance conservé{'s' if kept != 1 else ''}, non proposé{'s' if kept != 1 else ''} au client."
        if mode == "zones"
        else f"{kept} zone{'s' if kept != 1 else ''} conservée{'s' if kept != 1 else ''}, non proposée{'s' if kept != 1 else ''} au client."
    )
    zones_checked = "checked" if mode != "distance" else ""
    distance_checked = "checked" if mode == "distance" else ""
    body = f"""
      <h1 class="{H1}">Livraison</h1>
      <p class="mt-4 {NOTICE}" role="status">{esc(status)}</p>
      {f'<p class="mt-4 {NOTICE}">{esc(message)}</p>' if message else ''}
      <form class="mt-6 max-w-xl {PANEL_PAD}" method="post" action="/admin/livraison-mode">
        {hidden('csrf', ctx.session['csrf'])}
        <h2 class="font-display text-2xl">Mode</h2>
        <p class="mt-2 {MUTED}">Un seul mode est proposé au client. L'autre reste enregistré, mais il n'est pas utilisé.</p>
        <label class="{CHOICE} mt-4"><input type="radio" name="mode" value="zones" {zones_checked}> <span>Tarif par zone — le client choisit la zone et ses frais</span></label>
        <label class="{CHOICE} mt-3"><input type="radio" name="mode" value="distance" {distance_checked}> <span>Tarif selon la distance — le serveur calcule le trajet, puis le palier</span></label>
        <button class="mt-4 {BTN}" type="submit">Enregistrer le mode</button>
      </form>
      {editor}
      <p class="mt-6 max-w-xl {MUTED}">{kept_label}</p>
    """
    return _html(ctx, "Livraison", body, admin=True)


def admin_hours(ctx, message=""):
    data = settings_view(ctx.conn)
    hours = data["hours"]
    midi = data["midi"]
    body = f"""
      <h1 class="{H1}">Horaires</h1>
      {f'<p class="mt-4 {NOTICE}">{esc(message)}</p>' if message else ''}
      <form class="mt-8 max-w-xl {PANEL_PAD}" method="post" action="/admin/horaires">
        {hidden('csrf', ctx.session['csrf'])}
        <h2 class="font-display text-2xl">Horaires publiés</h2>
        <label class="{FIELD}"><span>Semaine, ouverture</span><input class="{INPUT}" name="semaine_debut" value="{esc(hours['mon_sat'][0])}"></label>
        <label class="{FIELD}"><span>Semaine, fermeture</span><input class="{INPUT}" name="semaine_fin" value="{esc(hours['mon_sat'][1])}"></label>
        <label class="{FIELD}"><span>Dimanche, ouverture</span><input class="{INPUT}" name="dimanche_debut" value="{esc(hours['sun'][0])}"></label>
        <label class="{FIELD}"><span>Dimanche, fermeture</span><input class="{INPUT}" name="dimanche_fin" value="{esc(hours['sun'][1])}"></label>
        <label class="{FIELD}"><span>Midi, début</span><input class="{INPUT}" name="midi_debut" value="{esc(midi['start'])}"></label>
        <label class="{FIELD}"><span>Midi, fin</span><input class="{INPUT}" name="midi_fin" value="{esc(midi['end'])}"></label>
        <label class="{CHECK}"><input type="checkbox" name="midi_dimanche" value="1" {'checked' if midi.get('sunday') else ''}> <span>Menus midi aussi le dimanche</span></label>
        <label class="{CHECK}"><input type="checkbox" name="notes" value="1" {'checked' if data['allow_notes'] else ''}> <span>Autoriser une instruction par article</span></label>
        <label class="{FIELD}"><span>Conditions à accepter</span><textarea class="{INPUT}" name="conditions">{esc(data['terms'] if isinstance(data['terms'], str) else '')}</textarea></label>
        <button class="mt-5 {BTN}" type="submit">Enregistrer</button>
      </form>
    """
    return _html(ctx, "Horaires", body, admin=True)


def admin_slots(ctx, query=None):
    from datetime import date

    from app.schedule import now_paris

    weekdays = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    months = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    )
    today = now_paris().date().isoformat()
    slots = ctx.conn.execute(
        "SELECT * FROM pickup_slots WHERE slot_date >= ? ORDER BY slot_date, start_time",
        (today,),
    ).fetchall()
    by_day = {}
    for slot in slots:
        by_day.setdefault(slot["slot_date"], []).append(slot)
    days = list(by_day)
    requested = ((query or {}).get("jour") or [""])[0]
    selected = requested if requested in by_day else (days[0] if days else "")
    day_links = []
    for day in days:
        current = date.fromisoformat(day)
        label = f"{weekdays[current.weekday()][:3]} {current.day}"
        kind = CHIP_ON if day == selected else CHIP
        current_attr = ' aria-current="page"' if day == selected else ""
        day_links.append(f'<a class="{kind}" href="/admin/creneaux?jour={esc(day)}"{current_attr}>{esc(label)}</a>')
    board = '<p class="mt-6 text-sm text-ink-soft">Aucun créneau à venir.</p>'
    if selected:
        rows = by_day[selected]
        current = date.fromisoformat(selected)
        closed = sum(1 for slot in rows if not slot["active"])
        opened = len(rows) - closed
        opened_word = "ouvert" if opened == 1 else "ouverts"
        closed_word = "fermé" if closed == 1 else "fermés"
        capacities = {slot["capacity"] for slot in rows}
        places = f"{next(iter(capacities))} places" if len(capacities) == 1 else "capacités différentes"
        chips = []
        for slot in rows:
            action = "Réactiver" if not slot["active"] else "Désactiver"
            tone = "border-line bg-paper-2 text-ink-soft" if not slot["active"] else "border-line bg-cream text-ink hover:border-ink"
            chips.append(
                f'''<form method="post" action="/admin/creneaux/{slot["id"]}">
                  {hidden("csrf", ctx.session["csrf"])}
                  {hidden("active", "0" if slot["active"] else "1")}
                  {hidden("jour", selected)}
                  <button class="inline-flex min-h-11 min-w-16 items-center justify-center rounded-xl border px-3 text-sm {tone}" type="submit" aria-label="{esc(action)} le créneau de {esc(slot["start_time"])} à {esc(slot["end_time"])}">{esc(slot["start_time"][:5])}</button>
                </form>'''
            )
        board = f"""
          <section class="mt-4 {PANEL_PAD}">
            <h2 class="font-display text-3xl">{esc(weekdays[current.weekday()])} {current.day} {esc(months[current.month - 1])}</h2>
            <p class="mt-2 {MUTED}">{opened} {opened_word} · {closed} {closed_word} · {esc(places)}. Un horaire fermé est grisé.</p>
            <div class="mt-4 flex flex-wrap gap-2">{''.join(chips)}</div>
          </section>
        """
    body = f"""
      <p class="{EYEBROW}">Service</p>
      <h1 class="mt-3 {H1}">Créneaux</h1>
      <p class="mt-4 max-w-xl {MUTED}">Un jour à la fois. Les jours vides s'ouvrent seuls sur 14 jours, dans les horaires publiés.</p>
      <nav class="mt-6 flex gap-2 overflow-x-auto pb-1" aria-label="Jours">{''.join(day_links)}</nav>
      {board}
      <form class="mt-8 max-w-xl {PANEL_PAD}" method="post" action="/admin/creneaux">
        {hidden('csrf', ctx.session['csrf'])}
        {hidden('jour', selected)}
        <h2 class="font-display text-2xl">Ajouter</h2>
        <label class="{FIELD}"><span>Date</span><input class="{INPUT}" name="date" type="date" value="{esc(selected)}" required></label>
        <label class="{FIELD}"><span>Début</span><input class="{INPUT}" name="debut" type="time" required></label>
        <label class="{FIELD}"><span>Fin</span><input class="{INPUT}" name="fin" type="time" required></label>
        <label class="{FIELD}"><span>Capacité</span><input class="{INPUT}" name="capacite" type="number" min="1" value="10" required></label>
        <button class="mt-4 {BTN}" type="submit">Ajouter le créneau</button>
      </form>
    """
    return _html(ctx, "Créneaux", body, admin=True)


def admin_notifications(ctx, message=""):
    body = f"""
      <p class="{EYEBROW}">Service</p>
      <h1 class="mt-3 {H1}">Notifications</h1>
      <p class="mt-4 max-w-xl {MUTED}">Les étapes de chaque commande sont notées ici. Le client n'est prévenu que si un envoi est branché.</p>
      {f'<p class="mt-4 {NOTICE}" role="status">{esc(message)}</p>' if message else ''}
      {_notification_board(ctx)}
    """
    return _html(ctx, "Notifications", body, admin=True)


def admin_promo_codes(ctx, message=""):
    promos = ctx.conn.execute("SELECT * FROM promo_codes ORDER BY id").fetchall()
    promo_rows = "".join(
        f'<li class="border-b border-line py-2 text-sm">{esc(promo["code"])} — {esc(promo["label"])}</li>'
        for promo in promos
    )
    body = f"""
      <h1 class="{H1}">Codes promo</h1>
      <nav class="mt-5 flex flex-wrap gap-2 border-b border-line pb-3" aria-label="Gestion des promotions">
        <a class="inline-flex min-h-11 items-center rounded-xl bg-paper-2 px-4 text-sm font-medium text-ink" href="/admin/codes-promo" aria-current="page">Codes promo</a>
        <a class="inline-flex min-h-11 items-center rounded-xl px-4 text-sm text-ink-soft hover:bg-paper-2 hover:text-ink" href="/admin/promotions">Pop-ups promotionnels</a>
      </nav>
      {f'<p class="mt-4 {NOTICE}">{esc(message)}</p>' if message else ''}
      <ul class="mt-6 max-w-xl">{promo_rows or '<li class="text-sm text-ink-soft">Aucune promotion.</li>'}</ul>
      <form class="mt-8 max-w-xl {PANEL_PAD}" method="post" action="/admin/codes-promo">
        {hidden('csrf', ctx.session['csrf'])}
        <label class="{FIELD}"><span>Code</span><input class="{INPUT}" name="code" required></label>
        <label class="{FIELD}"><span>Libellé</span><input class="{INPUT}" name="libelle" required></label>
        <label class="{FIELD}"><span>Type</span><select class="{INPUT}" name="type"><option value="amount">Montant en euros</option><option value="percent">Pourcentage</option></select></label>
        <label class="{FIELD}"><span>Valeur</span><input class="{INPUT}" name="valeur" required></label>
        <button class="mt-4 {BTN}" type="submit">Ajouter</button>
      </form>
    """
    return _html(ctx, "Promotions", body, admin=True)


def admin_promotions(ctx):
    build_index = ROOT / "web" / "dist" / "index.html"
    content = build_index.read_text(encoding="utf-8")
    script = re.search(r'<script[^>]+src="(/assets/[^"]+\.js)"', content)
    stylesheet = re.search(r'<link[^>]+href="(/assets/[^"]+\.css)"', content)
    if not script or not stylesheet:
        raise RuntimeError("Assets de l’interface des promotions introuvables.")
    body = f'<div id="root"></div><script type="module" crossorigin src="{esc(script.group(1))}"></script>'
    head = f'<link rel="stylesheet" crossorigin href="{esc(stylesheet.group(1))}">'
    return _html(ctx, "Pop-ups promotionnels", body, admin=True, extra_head=head)


def admin_drivers(ctx, message=""):
    from app.drivers import render_board

    return _html(ctx, "Livreurs", render_board(ctx, message), admin=True)


def admin_settings(ctx, message=""):
    from app.stripe_pay import resolve_secret_key, stripe_ready

    methods = ctx.conn.execute("SELECT * FROM payment_methods ORDER BY id").fetchall()
    method_rows = "".join(
        f'<li class="border-b border-line py-2 text-sm">{esc(method["label"])} — {"actif" if method["active"] else "inactif"}</li>'
        for method in methods
    )
    ready, ready_error = stripe_ready(ctx.conn)
    key = resolve_secret_key(ctx.conn)
    key_hint = f"{key[:12]}…{key[-4:]}" if len(key) > 20 else (key or "aucune")
    stripe_status = (
        f'<p class="mt-3 text-sm text-ink">Clé active : {esc(key_hint)}. Stripe répond correctement.</p>'
        if ready
        else f'<p class="mt-3 text-sm text-terracotta-deep">{esc(ready_error or "Paiement en ligne indisponible.")}</p>'
    )
    body = f"""
      <h1 class="{H1}">Réglages</h1>
      {f'<p class="mt-4 {NOTICE}">{esc(message)}</p>' if message else ''}
      <section class="mt-8 max-w-xl {PANEL_PAD}">
        <h2 class="font-display text-2xl">Paiement Stripe</h2>
        <p class="mt-3 text-sm text-ink-soft">Le Click &amp; Collect se règle par carte sur Stripe. Collez une clé secrète valide depuis le Dashboard Stripe (Developers → API keys).</p>
        {stripe_status}
        <form class="mt-4" method="post" action="/admin/stripe">
          {hidden('csrf', ctx.session['csrf'])}
          {password_field("cle", label="Clé secrète", required=False, autocomplete="off", placeholder="sk_test_… ou rkcs_…")}
          {password_field("webhook", label="Secret webhook (facultatif)", required=False, autocomplete="off", placeholder="whsec_…")}
          <div class="mt-4 flex flex-wrap gap-3">
            <button class="{BTN}" type="submit">Enregistrer Stripe</button>
            <button class="{BTN_GHOST}" type="submit" name="retirer" value="1" formnovalidate>Retirer la clé</button>
          </div>
        </form>
      </section>
      <section class="mt-8 max-w-xl">
        <h2 class="font-display text-2xl">Règlement hors ligne</h2>
        <ul class="mt-3">{method_rows or '<li class="text-sm text-ink-soft">Aucun moyen activé.</li>'}</ul>
        <form method="post" action="/admin/paiements">
          {hidden('csrf', ctx.session['csrf'])}
          <p class="mt-3 text-sm">Le Click &amp; Collect se règle par carte, avant le retrait.</p>
          <label class="{CHECK}"><input type="checkbox" name="pay_on_delivery" value="1" {'checked' if any(method['code'] == 'pay_on_delivery' and method['active'] for method in methods) else ''}> <span>À régler à la livraison</span></label>
          <button class="mt-4 {BTN_GHOST}" type="submit">Enregistrer</button>
        </form>
      </section>
      <section class="mt-10 max-w-xl {PANEL_PAD}">
        <h2 class="font-display text-2xl">Équipe</h2>
        <p class="mt-3 text-sm text-ink-soft">Ajoutez des administrateurs ou des livreurs. Ils se connectent sur la même page service.</p>
        <ul class="mt-4">{_team_rows(ctx)}</ul>
        <form class="mt-6 space-y-1" method="post" action="/admin/equipe">
          {hidden('csrf', ctx.session['csrf'])}
          <label class="{FIELD}"><span>Nom</span><input class="{INPUT}" name="nom" required maxlength="80" autocomplete="name"></label>
          <label class="{FIELD}"><span>E-mail</span><input class="{INPUT}" name="email" type="email" required autocomplete="username"></label>
          <label class="{FIELD}"><span>Téléphone (facultatif)</span><input class="{INPUT}" name="telephone" maxlength="40" autocomplete="tel"></label>
          <label class="{FIELD}"><span>Rôle</span>
            <select class="{INPUT}" name="role" required>
              <option value="driver">Livreur — courses uniquement</option>
              <option value="admin">Administrateur — tableau de bord complet</option>
            </select>
          </label>
          {password_field("password", label="Mot de passe", required=True, autocomplete="new-password", extra='minlength="10"')}
          <button class="mt-4 {BTN}" type="submit">Ajouter à l'équipe</button>
        </form>
      </section>
      <section class="mt-10 max-w-xl">
        <h2 class="font-display text-2xl">Clients</h2>
        <ul class="mt-3">{_customer_rows(ctx)}</ul>
      </section>
    """
    return _html(ctx, "Réglages", body, admin=True)


def _notification_board(ctx):
    from datetime import datetime, timedelta, timezone

    from app.schedule import PARIS, now_paris

    rows = ctx.conn.execute(
        """
        SELECT n.order_id, n.event, n.status, n.detail, n.created_at, o.public_ref
        FROM notifications n
        LEFT JOIN orders o ON o.id = n.order_id
        ORDER BY n.id DESC
        LIMIT 40
        """
    ).fetchall()
    if not rows:
        return f'<p class="mt-6 max-w-xl {MUTED}">Aucune notification pour le moment.</p>'
    results = {
        "skipped": "Non envoyée",
        "sent": "Envoyée",
        "failed": "Échec",
    }
    weekdays = ("lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche")
    months = (
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    )
    today = now_paris().date()
    groups = []
    for row in rows:
        moment = _notification_moment(row["created_at"], datetime, timezone, PARIS)
        key = moment.date().isoformat() if moment else ""
        if not groups or groups[-1]["key"] != key:
            groups.append({"key": key, "moment": moment, "rows": []})
        groups[-1]["rows"].append((row, moment))
    parts = []
    unsent = sum(1 for row in rows if row["status"] != "sent")
    if unsent == len(rows):
        parts.append(
            f'<p class="mt-6 max-w-xl {NOTICE}">Aucun e-mail ni SMS n\'est parti. Aucun fournisseur n\'est branché.</p>'
        )
    cards = []
    for group in groups:
        moment = group["moment"]
        if moment and moment.date() == today:
            title = "Aujourd'hui"
        elif moment and moment.date() == today - timedelta(days=1):
            title = "Hier"
        elif moment:
            title = f"{weekdays[moment.weekday()]} {moment.day} {months[moment.month - 1]}"
        else:
            title = "Sans date"
        lines = []
        for row, when in group["rows"]:
            label = STATUS_LABELS.get(row["event"]) or ("Commande passée" if row["event"] == "order.placed" else "Mise à jour")
            result = results.get(row["status"], "Non envoyée")
            tone = "text-terracotta-deep" if row["status"] == "failed" else "text-ink-soft"
            clock = when.strftime("%H:%M") if when else ""
            if row["public_ref"] and row["order_id"]:
                order = (
                    f'<a class="text-ink-soft underline decoration-line underline-offset-4 hover:text-terracotta-deep" '
                    f'href="/admin/commandes/{int(row["order_id"])}">{esc(row["public_ref"])}</a>'
                )
            else:
                order = ""
            detail = (row["detail"] or "").strip()
            extra = ""
            if detail and "n'est configuré" not in detail and "Aucun fournisseur" not in detail:
                extra = f'<p class="mt-1 text-sm text-ink-soft">{esc(detail)}</p>'
            lines.append(
                f'''<li class="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 px-5 py-4">
                  <div class="min-w-0"><p class="text-sm"><span class="font-medium">{esc(label)}</span>{f" · {order}" if order else ""}</p>{extra}</div>
                  <p class="flex items-baseline gap-4 text-sm"><span class="{tone}">{esc(result)}</span><time class="tabular-nums text-ink-soft">{esc(clock)}</time></p>
                </li>'''
            )
        cards.append(
            f'''<section>
              <h2 class="bg-paper-2 px-5 py-3 text-xs font-medium uppercase tracking-[0.16em] text-ink-soft">{esc(title)}</h2>
              <ul class="divide-y divide-line">{''.join(lines)}</ul>
            </section>'''
        )
    parts.append(f'<div class="mt-6 max-w-3xl overflow-hidden rounded-2xl border border-line bg-cream">{''.join(cards)}</div>')
    return "".join(parts)


def _notification_moment(value, datetime, timezone, paris):
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(paris)


def _team_rows(ctx):
    labels = {"admin": "Administrateur", "driver": "Livreur"}
    rows = ctx.conn.execute(
        "SELECT email, name, phone, role FROM users WHERE role IN ('admin', 'driver') ORDER BY role, name, id"
    ).fetchall()
    return "".join(
        f'<li class="border-b border-line py-3 text-sm">'
        f'<span class="font-medium">{esc(row["name"] or row["email"])}</span>'
        f'<span class="text-ink-soft"> — {esc(labels.get(row["role"], row["role"]))}</span>'
        f'<br><span class="text-ink-soft">{esc(row["email"])}'
        f'{(" · " + esc(row["phone"])) if row["phone"] else ""}</span></li>'
        for row in rows
    ) or '<li class="text-sm text-ink-soft">Aucun membre d\'équipe pour le moment.</li>'


def _customer_rows(ctx):
    rows = ctx.conn.execute(
        "SELECT email, name FROM users WHERE role = 'customer' ORDER BY id DESC LIMIT 40"
    ).fetchall()
    return "".join(
        f'<li class="border-b border-line py-2 text-sm">{esc(row["email"])}'
        f'{(" · " + esc(row["name"])) if row["name"] else ""}</li>'
        for row in rows
    ) or '<li class="text-sm text-ink-soft">Aucun client inscrit.</li>'


def handle_add(ctx, form):
    try:
        choice_ids = []
        for key, value in form.items():
            if key.startswith("groupe-") and value:
                choice_ids.append(int(value))
        quote = add_item(
            ctx.conn,
            ctx.session["id"],
            int(form.get("produit") or 0),
            choice_ids,
            int(form.get("quantite") or 1),
            form.get("notes") or "",
        )
    except (TypeError, ValueError):
        return None, ["Données de personnalisation invalides."]
    if quote.issues:
        return quote.product["slug"] if quote.product else None, quote.issues
    return None, []


def handle_order_post(ctx, form):
    order, errors = place_order(
        ctx.conn,
        ctx.session["id"],
        ctx.user["id"] if ctx.user else None,
        form,
    )
    return order, errors


def _html(ctx, title, body, admin=False, extra_head=""):
    from app.notify import mark_seen, unseen_count
    from app.ui import page as render

    count = cart_count(ctx.conn, ctx.session["id"]) if ctx.session else 0
    notify_n = 0
    if admin and ctx.user and ctx.user["role"] == "admin":
        if getattr(ctx, "path", "") == "/admin/notifications":
            mark_seen(ctx.conn)
        notify_n = unseen_count(ctx.conn)
    return render(
        title,
        body,
        cart_n=count,
        flash=ctx.flash,
        user=ctx.user,
        admin=admin,
        current=getattr(ctx, "path", ""),
        csrf=ctx.session["csrf"] if ctx.session else "",
        notify_n=notify_n,
        extra_head=extra_head,
    )
