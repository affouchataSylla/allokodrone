import html

BTN = "inline-flex min-h-11 items-center justify-center rounded-xl bg-terracotta px-4 text-sm font-medium text-cream hover:bg-terracotta-deep disabled:cursor-not-allowed disabled:opacity-40"
BTN_GHOST = "inline-flex min-h-11 items-center justify-center rounded-xl border border-line bg-transparent px-4 text-sm font-medium text-ink hover:border-ink"
BTN_TEXT = "inline-flex min-h-11 items-center text-sm font-medium text-terracotta-deep underline decoration-line underline-offset-4 hover:decoration-terracotta"
EYEBROW = "text-xs font-medium uppercase tracking-[0.16em] text-terracotta"
PANEL = "rounded-2xl border border-line bg-cream"
PANEL_PAD = "rounded-2xl border border-line bg-cream p-5"
H1 = "font-display text-4xl leading-[0.95] text-ink sm:text-5xl"
H2 = "mt-2 font-display text-3xl leading-none text-ink"
LEAD = "mt-4 max-w-xl text-base leading-relaxed text-ink-soft"
MUTED = "text-sm leading-relaxed text-ink-soft"
FIELD = "mt-4 flex flex-col gap-1.5 text-sm text-ink"
INPUT = "w-full rounded-xl border border-line bg-cream px-3 py-2.5 text-base text-ink outline-none focus:border-ink"
CHOICE = "flex min-h-11 items-center gap-3 rounded-xl border border-line bg-cream px-3 py-2 text-sm has-checked:border-ink has-checked:bg-paper-2"
CHECK = "mt-3 flex min-h-11 items-start gap-3 text-sm leading-snug text-ink"
CHIP = "inline-flex min-h-11 shrink-0 items-center rounded-full border border-line px-3 text-sm text-ink"
CHIP_ON = "inline-flex min-h-11 shrink-0 items-center rounded-full border border-ink bg-cream px-3 text-sm text-ink"
NOTICE = "mb-5 border-l-2 border-saffron bg-paper-2 px-4 py-3 text-sm leading-relaxed"
NOTICE_WARN = "mb-5 border-l-2 border-terracotta-deep bg-paper-2 px-4 py-3 text-sm leading-relaxed"
PRICE = "shrink-0 font-medium tabular-nums text-ink"
PRICE_MISSING = "shrink-0 text-sm text-terracotta-deep"


def esc(value):
    return html.escape("" if value is None else str(value), quote=True)


def password_field(name="password", *, label="Mot de passe", required=True, autocomplete="current-password", placeholder="", value="", extra=""):
    req = " required" if required else ""
    ph = f' placeholder="{esc(placeholder)}"' if placeholder else ""
    val = f' value="{esc(value)}"' if value else ""
    extras = f" {extra}" if extra else ""
    return f"""
      <label class="{FIELD}"><span>{esc(label)}</span>
        <span class="relative block">
          <input class="{INPUT} pr-12" name="{esc(name)}" type="password"{req} autocomplete="{esc(autocomplete)}"{ph}{val}{extras}>
          <button class="absolute inset-y-0 right-0 inline-flex w-11 items-center justify-center text-ink-soft hover:text-ink" type="button" data-password-toggle aria-label="Afficher le mot de passe" aria-pressed="false">
            <svg class="h-5 w-5" data-eye="show" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>
            <svg class="hidden h-5 w-5" data-eye="hide" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3l18 18"/><path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/><path d="M9.9 5.1A10.4 10.4 0 0 1 12 5c6.5 0 10 7 10 7a17.5 17.5 0 0 1-4.2 4.8"/><path d="M6.1 6.1C4 7.8 2.5 10 2 12s3.5 7 10 7a10.8 10.8 0 0 0 4.2-.8"/></svg>
          </button>
        </span>
      </label>
    """


def _icon(name):
    paths = {
        "board": '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
        "orders": '<path d="M6 6h12M6 12h12M6 18h8"/><path d="M4 4h16v16H4z"/>',
        "reviews": '<path d="M12 3l2.2 4.5 5 .7-3.6 3.5.9 5.1L12 14.8 7.5 16.8l.9-5.1L4.8 8.2l5-.7L12 3z"/>',
        "kitchen": '<path d="M8 4v6a4 4 0 0 0 8 0V4"/><path d="M12 14v6M8 20h8"/>',
        "products": '<path d="M4 8l8-4 8 4-8 4-8-4z"/><path d="M4 12l8 4 8-4"/><path d="M4 16l8 4 8-4"/>',
        "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6 17 7M7 17l-1.4 1.4"/>',
        "delivery": '<path d="M3 7h11v8H3z"/><path d="M14 10h4l3 3v2h-7z"/><circle cx="7" cy="17" r="1.5"/><circle cx="17" cy="17" r="1.5"/>',
        "hours": '<circle cx="12" cy="12" r="8"/><path d="M12 8v5l3 2"/>',
        "slots": '<rect x="4" y="5" width="16" height="15" rx="1"/><path d="M8 3v4M16 3v4M4 10h16"/>',
        "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 19a2 2 0 0 0 4 0"/>',
        "promo": '<path d="M4 12V5h7l9 9-7 7z"/><circle cx="8.5" cy="8.5" r="1"/>',
        "shop": '<path d="M4 10 12 4l8 6"/><path d="M6 10v8h12v-8"/><path d="M10 18v-5h4v5"/>',
        "logout": '<path d="M9 7V5H4v14h5v-2"/><path d="M10 12h9"/><path d="M16 9l3 3-3 3"/>',
    }
    return (
        '<svg class="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
        f'{paths[name]}</svg>'
    )


def _admin_nav_items(role):
    if role == "driver":
        return [("/admin/livreurs", "Mes courses", "delivery", False)]
    return [
        ("/admin", "Tableau de bord", "board", True),
        ("/admin/commandes", "Commandes", "orders", False),
        ("/admin/avis", "Avis", "reviews", False),
        ("/admin/cuisine", "Cuisine", "kitchen", False),
        ("/admin/livreurs", "Livreurs", "delivery", False),
        ("/admin/produits", "Produits", "products", False),
        ("/admin/livraison", "Livraison", "delivery", False),
        ("/admin/horaires", "Horaires", "hours", False),
        ("/admin/creneaux", "Créneaux", "slots", False),
        ("/admin/notifications", "Notifications", "bell", False),
        ("/admin/codes-promo", "Codes promo", "promo", False),
        ("/admin/reglages", "Réglages", "settings", False),
    ]


def _admin_document(title, body, flash, current, csrf, notify_n=0, role="admin", extra_head=""):
    items = _admin_nav_items(role)
    home = "/admin/livreurs" if role == "driver" else "/admin"
    section = "Livraison" if role == "driver" else "Service"
    nav_label = "Espace livreur" if role == "driver" else "Administration"
    links = []
    for href, name, icon, exact in items:
        active = current == href if exact else current == href or current.startswith(href + "/")
        if href == "/admin/codes-promo" and current == "/admin/promotions":
            active = True
        state = "bg-paper-2 font-medium text-ink" if active else "text-ink-soft hover:bg-paper hover:text-ink"
        current_attr = ' aria-current="page"' if active else ""
        badge = ""
        label = esc(name)
        labelled = ""
        if role == "admin" and href == "/admin/notifications" and notify_n:
            word = "non lue" if notify_n == 1 else "non lues"
            label = esc(f"{name}, {notify_n} {word}")
            labelled = f' aria-label="{label}"'
            badge = (
                f'<span class="ml-auto inline-flex h-6 min-w-6 items-center justify-center rounded-full '
                f'bg-terracotta px-1.5 text-xs font-medium text-cream" aria-hidden="true">{notify_n}</span>'
            )
        links.append(
            f'<li><a class="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm {state}" href="{href}"{current_attr}{labelled}>{_icon(icon)}<span class="min-w-0 flex-1">{esc(name)}</span>{badge}</a></li>'
        )
    shop_link = ""
    if role == "admin":
        shop_link = (
            f'<a class="flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm text-ink-soft hover:bg-paper hover:text-ink" '
            f'href="/">{_icon("shop")}<span>Voir la boutique</span></a>'
        )
    flash_html = f'<p class="{NOTICE}" role="status">{esc(flash)}</p>' if flash else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — ALLOKODRONE</title>
  <meta name="theme-color" content="#f5dfbc">
  <link rel="icon" href="/images/logo-dark.png" type="image/png">
  <link rel="stylesheet" href="/css/fonts.css">
  {extra_head}
  <link rel="stylesheet" href="/css/app.css">
</head>
<body class="bg-paper font-sans text-ink antialiased">
  <a class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-cream focus:px-3 focus:py-2" href="#contenu">Aller au contenu</a>
  <header class="site-header sticky top-0 z-40 flex h-14 items-center justify-between border-b border-line bg-cream px-4 md:hidden">
    <a href="{home}"><img class="h-8 w-auto" src="/images/logo-dark.png" width="532" height="299" alt="ALLOKODRONE"></a>
    <button class="nav-toggle inline-flex h-11 w-11 items-center justify-center" type="button" aria-expanded="false" aria-controls="site-nav">
      <span class="flex w-4 flex-col gap-1.5" aria-hidden="true"><span class="block h-px bg-ink"></span><span class="block h-px bg-ink"></span><span class="block h-px bg-ink"></span></span>
      <span class="sr-only">Ouvrir le menu</span>
    </button>
  </header>
  <div class="md:grid md:grid-cols-[16rem_1fr]">
    <nav id="site-nav" class="fixed inset-y-0 left-0 z-40 hidden w-64 max-w-full flex-col overflow-x-hidden border-r border-line bg-cream px-4 py-6 md:sticky md:top-0 md:flex md:h-screen" aria-label="{nav_label}">
      <a class="hidden max-w-full shrink-0 px-2 md:block" href="{home}"><img class="h-10 w-auto max-w-full" src="/images/logo-dark.png" width="532" height="299" alt="ALLOKODRONE"></a>
      <p class="mt-8 shrink-0 px-3 text-xs font-medium uppercase tracking-[0.16em] text-ink-soft">{section}</p>
      <ul class="mt-3 min-h-0 flex-1 space-y-1 overflow-y-auto">{''.join(links)}</ul>
      <div class="mt-3 shrink-0 pb-1">
        <div class="mx-3 border-t border-line"></div>
        <div class="mt-3 space-y-1">
          {shop_link}
          <form method="post" action="/admin/deconnexion">{hidden('csrf', csrf)}<button class="flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-left text-sm text-ink-soft hover:bg-paper hover:text-ink" type="submit">{_icon("logout")}<span>Se déconnecter</span></button></form>
        </div>
      </div>
    </nav>
    <main id="contenu">
      <div class="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        {flash_html}
        {body}
      </div>
    </main>
  </div>
  <script src="/js/main.js"></script>
</body>
</html>"""


def _site_footer():
    return """
  <footer class="bg-night text-cream">
    <div class="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:grid-cols-2 lg:grid-cols-4">
      <div>
        <a href="/"><img class="h-14 w-auto" src="/images/logo-light.png" width="532" height="299" alt="ALLOKODRONE"></a>
        <p class="mt-4 text-sm text-cream/80">L'Afrique servie à grande vitesse.</p>
      </div>
      <div>
        <h2 class="font-display text-xl">Commander</h2>
        <ul class="mt-3 space-y-2 text-sm">
          <li><a class="hover:text-saffron" href="/carte">La carte</a></li>
          <li><a class="hover:text-saffron" href="/panier">Panier</a></li>
          <li><a class="hover:text-saffron" href="/compte">Compte</a></li>
        </ul>
      </div>
      <div>
        <h2 class="font-display text-xl">Restaurant</h2>
        <p class="mt-3 text-sm leading-relaxed text-cream/80">24 rue Emmanuel Arago<br>93130 Noisy-le-Sec</p>
        <p class="mt-3 text-sm text-cream/80">Lun – sam · 11h30 – 22h30<br>Dimanche · 17h – 22h30</p>
        <p class="mt-3 text-sm"><a class="hover:text-saffron" href="https://www.google.com/maps/dir/?api=1&amp;destination=24+rue+Emmanuel+Arago+93130+Noisy-le-Sec" target="_blank" rel="noopener noreferrer">Itinéraire</a></p>
      </div>
      <div>
        <h2 class="font-display text-xl">Réseaux</h2>
        <ul class="mt-3 space-y-2 text-sm">
          <li><a class="hover:text-saffron" href="https://www.instagram.com/alloko_drone/" target="_blank" rel="noopener noreferrer">Instagram</a></li>
        </ul>
      </div>
    </div>
    <div class="border-t border-cream/15">
      <div class="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-4 text-xs text-cream/70 sm:flex-row sm:justify-between">
        <p>© 2026 ALLOKODRONE. Tous droits réservés.</p>
        <p>Aucun paiement en ligne n'est encaissé par ce site.</p>
      </div>
    </div>
  </footer>"""


def login_page(title, body, flash=""):
    flash_html = f'<p class="{NOTICE}" role="status">{esc(flash)}</p>' if flash else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — ALLOKODRONE</title>
  <meta name="theme-color" content="#f5dfbc">
  <link rel="icon" href="/images/logo-dark.png" type="image/png">
  <link rel="stylesheet" href="/css/fonts.css">
  <link rel="stylesheet" href="/css/app.css">
</head>
<body class="flex min-h-screen flex-col bg-paper font-sans text-ink antialiased">
  <main id="contenu" class="flex flex-1 items-center">
    <div class="mx-auto w-full max-w-md px-4 py-12">
      {flash_html}
      {body}
    </div>
  </main>
  {_site_footer()}
  <script src="/js/main.js"></script>
</body>
</html>"""


def page(title, body, *, cart_n=0, flash="", user=None, admin=False, current="", csrf="", notify_n=0, extra_head=""):
    if admin and user and user["role"] in ("admin", "driver"):
        return _admin_document(
            title, body, flash, current, csrf, notify_n, role=user["role"], extra_head=extra_head
        )
    account = "Compte"
    if user and user["role"] == "admin":
        account = "Admin"
    link = "block py-2 text-sm tracking-wide text-ink hover:text-terracotta-deep md:py-0"
    if admin:
        items = [
            ("/admin", "Tableau"),
            ("/admin/produits", "Produits"),
            ("/admin/commandes", "Commandes"),
            ("/admin/reglages", "Réglages"),
            ("/", "Boutique"),
        ]
        label = "Administration"
    else:
        items = [
            ("/carte", "La carte"),
            ("/compte", account),
            ("/#restaurant", "Nous trouver"),
        ]
        label = "Navigation principale"
    links = "".join(f'<li><a class="{link}" href="{href}">{esc(name)}</a></li>' for href, name in items)
    flash_html = f'<p class="{NOTICE}" role="status">{esc(flash)}</p>' if flash else ""
    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)} — ALLOKODRONE</title>
  <meta name="description" content="Commandez chez ALLOKODRONE, afro street food à Noisy-le-Sec. Retrait et livraison.">
  <meta name="theme-color" content="#f5dfbc">
  <link rel="icon" href="/images/logo-dark.png" type="image/png">
  <link rel="stylesheet" href="/css/fonts.css">
  {extra_head}
  <link rel="stylesheet" href="/css/app.css">
</head>
<body class="bg-paper font-sans text-ink antialiased">
  <a class="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-cream focus:px-3 focus:py-2" href="#contenu">Aller au contenu</a>
  <header class="site-header sticky top-0 z-40 border-b border-line bg-paper">
    <div class="relative mx-auto grid h-16 max-w-6xl grid-cols-[1fr_auto] items-center gap-4 px-4 md:h-20 md:grid-cols-[auto_1fr_auto]">
      <a class="shrink-0 justify-self-start" href="/"><img class="h-10 w-auto md:h-12" src="/images/logo-dark.png" width="532" height="299" alt="ALLOKODRONE"></a>
      <nav id="site-nav" class="absolute left-0 right-0 top-full z-40 hidden flex-col border-b border-line bg-paper px-4 py-2 md:static md:flex md:items-center md:justify-center md:border-0 md:bg-transparent md:p-0" aria-label="{label}">
        <ul class="flex flex-col md:flex-row md:items-center md:gap-8">{links}</ul>
      </nav>
      <div class="flex items-center gap-1 justify-self-end">
        <a class="inline-flex h-11 items-center gap-2.5 px-2 text-sm tracking-wide text-ink hover:text-terracotta-deep" href="/panier">
          <span class="hidden sm:inline">Panier</span>
          <span class="inline-flex h-7 min-w-7 items-center justify-center bg-terracotta px-1.5 text-xs font-medium text-cream">{int(cart_n)}</span>
        </a>
        <button class="nav-toggle inline-flex h-11 w-11 shrink-0 items-center justify-center md:hidden" type="button" aria-expanded="false" aria-controls="site-nav">
          <span class="flex w-4 flex-col gap-1.5" aria-hidden="true"><span class="block h-px bg-ink"></span><span class="block h-px bg-ink"></span><span class="block h-px bg-ink"></span></span>
          <span class="sr-only">Ouvrir le menu</span>
        </button>
      </div>
    </div>
  </header>
  <main id="contenu">
    <div class="mx-auto max-w-6xl px-4 py-8 sm:py-12">
      {flash_html}
      {body}
    </div>
  </main>
  {_site_footer()}
  <script src="/js/main.js"></script>
  <script src="/js/shop.js"></script>
</body>
</html>"""


def errors_block(errors):
    if not errors:
        return ""
    items = "".join(f"<li>{esc(item)}</li>" for item in errors)
    return f'<div class="{NOTICE_WARN}" role="alert"><ul class="list-disc space-y-1 pl-4">{items}</ul></div>'


def price_label(product):
    from app.money import format_eur

    if product["price_confirmed"] and product["price_cents"] is not None:
        return format_eur(product["price_cents"])
    return "Prix à valider"


def hidden(name, value):
    return f'<input type="hidden" name="{esc(name)}" value="{esc(value)}">'
