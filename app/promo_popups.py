import json
import re
import uuid
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlsplit


MAX_IMAGE_BYTES = 2 * 1024 * 1024
FREQUENCIES = {"session", "day", "visit"}
TARGET_PAGES = {"accueil", "menu", "toutes"}
PROMOTION_THEMES = {"beige", "premium"}
COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
IMAGE_PATH_PATTERN = re.compile(r"^/api/promotions/images/([a-f0-9]{32})$")


def _now():
    return datetime.now().replace(microsecond=0)


def _timestamp(value=None):
    return (value or _now()).isoformat(timespec="seconds")


def _contrast_ratio(first, second):
    def luminance(color):
        channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
        linear = [
            channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
            for channel in channels
        ]
        return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]

    light, dark = sorted((luminance(first), luminance(second)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


def _datetime(value, *, end=False):
    text = str(value or "").strip()
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if "T" not in text and end:
        parsed = parsed.replace(hour=23, minute=59, second=59)
    elif end and parsed.second == 0:
        parsed = parsed.replace(second=59)
    return parsed.replace(tzinfo=None, microsecond=0)


def _status(promo, now=None):
    if not promo["actif"]:
        return "inactive"
    now = now or _now()
    start = _datetime(promo["date_debut"])
    end = _datetime(promo["date_fin"], end=True)
    if not start or not end:
        return "inactive"
    if now < start:
        return "scheduled"
    if now > end:
        return "expired"
    return "active"


def _pages(value):
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            value = [item.strip() for item in value.split(",") if item.strip()]
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if item in TARGET_PAGES and item not in result:
            result.append(item)
    return ["toutes"] if "toutes" in result else result


def _decimal(value, label, optional=False):
    text = str(value or "").strip().replace(",", ".")
    if optional and not text:
        return None, None
    try:
        number = Decimal(text)
    except (InvalidOperation, ValueError):
        return None, f"{label} invalide."
    if not number.is_finite() or number <= 0 or number > Decimal("9999.99"):
        return None, f"{label} invalide."
    return number.quantize(Decimal("0.01")), None


def _url(value, *, allow_empty=False):
    text = str(value or "").strip()
    if allow_empty and not text:
        return text, None
    if not text or len(text) > 2048 or any(ord(char) < 32 for char in text):
        return None, "Adresse invalide."
    if text.startswith("/") and not text.startswith("//") and "\\" not in text:
        return text, None
    parsed = urlsplit(text)
    if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
        return None, "Utilisez une adresse locale ou une URL HTTPS."
    return text, None


def _normalise(payload):
    title = str(payload.get("titre") or "").strip()
    if not title or len(title) > 120:
        return None, "Le titre est obligatoire (120 caractères maximum)."

    price, error = _decimal(payload.get("prix"), "Le prix")
    if error:
        return None, error
    old_price, error = _decimal(payload.get("ancien_prix"), "L'ancien prix", optional=True)
    if error:
        return None, error
    if old_price is not None and old_price <= price:
        return None, "L'ancien prix doit être supérieur au prix promotionnel."

    start = _datetime(payload.get("date_debut"))
    end = _datetime(payload.get("date_fin"), end=True)
    if not start or not end or end <= start:
        return None, "Les dates de début et de fin sont invalides."

    pages = _pages(payload.get("pages_cibles"))
    if not pages:
        return None, "Choisissez au moins une page cible."
    frequency = str(payload.get("frequence") or "session")
    if frequency not in FREQUENCIES:
        return None, "Fréquence invalide."

    try:
        priority = int(payload.get("priorite") or 0)
        delay = int(payload.get("delai_affichage", 6))
    except (TypeError, ValueError):
        return None, "Priorité ou délai invalide."
    if not -10000 <= priority <= 10000 or not 0 <= delay <= 120:
        return None, "Priorité ou délai hors limites."

    badge = str(payload.get("badge_texte") or "").strip()
    description = str(payload.get("description") or "").strip()
    legal = str(payload.get("mention_legale") or "").strip()
    if len(badge) > 80 or len(description) > 280 or len(legal) > 500:
        return None, "Un texte dépasse la longueur autorisée."

    image_url, error = _url(payload.get("image_url"), allow_empty=True)
    if error:
        return None, "Adresse d'image invalide."
    cta_text = str(payload.get("cta_texte") or "COMMANDER MAINTENANT").strip()
    if not cta_text or len(cta_text) > 60:
        return None, "Le texte du bouton est obligatoire (60 caractères maximum)."
    cta_link, error = _url(payload.get("cta_lien") or "/carte")
    if error:
        return None, "Lien du bouton invalide."

    theme = str(payload.get("theme") or "beige").strip()
    if theme not in PROMOTION_THEMES:
        return None, "Design de promotion invalide."
    default_background = "#1E0F08" if theme == "premium" else "#F6EBD9"
    background = str(payload.get("couleur_fond") or default_background).strip()
    accent = str(payload.get("couleur_accent") or "#FF6A13").strip()
    if not COLOR_PATTERN.fullmatch(background) or not COLOR_PATTERN.fullmatch(accent):
        return None, "Les couleurs doivent être au format hexadécimal #RRGGBB."
    if theme == "premium":
        accessible = (
            _contrast_ratio("#F6EBD9", background) >= 4.5
            and _contrast_ratio("#E8D7BC", background) >= 4.5
            and _contrast_ratio("#1E0F08", accent) >= 4.5
            and _contrast_ratio(accent, background) >= 4.5
        )
    else:
        accessible = (
            _contrast_ratio("#1E0F08", background) >= 4.5
            and _contrast_ratio("#1E0F08", accent) >= 4.5
        )
    if not accessible:
        return None, "Les couleurs choisies ne respectent pas le contraste d’accessibilité requis."

    return {
        "titre": title,
        "prix": str(price),
        "ancien_prix": str(old_price) if old_price is not None else None,
        "badge_texte": badge,
        "afficher_pastille_reduction": int(bool(payload.get("afficher_pastille_reduction", True))),
        "description": description,
        "image_url": image_url,
        "cta_texte": cta_text,
        "cta_lien": cta_link,
        "mention_legale": legal,
        "date_debut": start.isoformat(timespec="minutes"),
        "date_fin": end.isoformat(timespec="minutes"),
        "actif": int(bool(payload.get("actif", False))),
        "priorite": priority,
        "pages_cibles": json.dumps(pages, ensure_ascii=False),
        "frequence": frequency,
        "delai_affichage": delay,
        "intention_de_sortie": int(bool(payload.get("intention_de_sortie", False))),
        "couleur_fond": background.upper(),
        "couleur_accent": accent.upper(),
        "theme": theme,
    }, None


def _stats(conn, promo_id):
    row = conn.execute(
        "SELECT impressions, clicks, closes FROM promotion_popup_stats WHERE promo_id = ?",
        (promo_id,),
    ).fetchone()
    if not row:
        return {"impressions": 0, "clicks": 0, "closes": 0, "click_rate": 0}
    impressions = int(row["impressions"])
    clicks = int(row["clicks"])
    return {
        "impressions": impressions,
        "clicks": clicks,
        "closes": int(row["closes"]),
        "click_rate": round(clicks * 100 / impressions, 1) if impressions else 0,
    }


def _as_dict(conn, row, *, include_stats=False):
    promo = dict(row)
    promo["pages_cibles"] = _pages(promo["pages_cibles"])
    promo["actif"] = bool(promo["actif"])
    promo["afficher_pastille_reduction"] = bool(promo["afficher_pastille_reduction"])
    promo["intention_de_sortie"] = bool(promo["intention_de_sortie"])
    promo["statut"] = _status(row)
    if include_stats:
        promo.update(_stats(conn, promo["id"]))
    return promo


def list_promotions(conn):
    rows = conn.execute("SELECT * FROM promotions ORDER BY priorite DESC, id DESC").fetchall()
    return [_as_dict(conn, row, include_stats=True) for row in rows]


def get_promotion(conn, promo_id):
    row = conn.execute("SELECT * FROM promotions WHERE id = ?", (promo_id,)).fetchone()
    return _as_dict(conn, row, include_stats=True) if row else None


def get_active_promotion(conn, page):
    now = _now().isoformat(timespec="minutes")
    rows = conn.execute(
        """
        SELECT * FROM promotions
        WHERE actif = 1 AND date_debut <= ? AND date_fin >= ?
        ORDER BY priorite DESC, id DESC
        """,
        (now, now),
    ).fetchall()
    for row in rows:
        targets = _pages(row["pages_cibles"])
        if "toutes" in targets or page in targets:
            promo = _as_dict(conn, row)
            return {
                key: promo[key]
                for key in (
                    "id",
                    "titre",
                    "prix",
                    "ancien_prix",
                    "badge_texte",
                    "afficher_pastille_reduction",
                    "description",
                    "image_url",
                    "cta_texte",
                    "cta_lien",
                    "mention_legale",
                    "date_fin",
                    "frequence",
                    "delai_affichage",
                    "intention_de_sortie",
                    "couleur_fond",
                    "couleur_accent",
                    "theme",
                    "updated_at",
                )
            }
    return None


def save_promotion(conn, payload, promo_id=None):
    if not isinstance(payload, dict):
        return None, "Données invalides."
    values, error = _normalise(payload)
    if error:
        return None, error
    now = _timestamp()
    if promo_id is None:
        columns = ", ".join(values)
        placeholders = ", ".join("?" for _ in values)
        cursor = conn.execute(
            f"INSERT INTO promotions ({columns}, created_at, updated_at) VALUES ({placeholders}, ?, ?)",
            (*values.values(), now, now),
        )
        promo_id = cursor.lastrowid
    else:
        exists = conn.execute("SELECT id FROM promotions WHERE id = ?", (promo_id,)).fetchone()
        if not exists:
            return None, "Promotion introuvable."
        updates = ", ".join(f"{key} = ?" for key in values)
        conn.execute(
            f"UPDATE promotions SET {updates}, updated_at = ? WHERE id = ?",
            (*values.values(), now, promo_id),
        )
    conn.execute(
        "INSERT OR IGNORE INTO promotion_popup_stats (promo_id) VALUES (?)",
        (promo_id,),
    )
    return get_promotion(conn, promo_id), None


def toggle_promotion(conn, promo_id, active):
    cursor = conn.execute(
        "UPDATE promotions SET actif = ?, updated_at = ? WHERE id = ?",
        (int(bool(active)), _timestamp(), promo_id),
    )
    return get_promotion(conn, promo_id) if cursor.rowcount else None


def duplicate_promotion(conn, promo_id):
    row = conn.execute("SELECT * FROM promotions WHERE id = ?", (promo_id,)).fetchone()
    if not row:
        return None
    now = _timestamp()
    columns = (
        "titre", "prix", "ancien_prix", "badge_texte", "afficher_pastille_reduction",
        "description", "image_url", "cta_texte", "cta_lien", "mention_legale",
        "date_debut", "date_fin", "priorite", "pages_cibles", "frequence",
        "delai_affichage", "intention_de_sortie", "couleur_fond", "couleur_accent",
        "theme",
    )
    values = [row[key] for key in columns]
    values[0] = f"{row['titre']} (copie)"[:120]
    cursor = conn.execute(
        f"INSERT INTO promotions ({', '.join(columns)}, actif, created_at, updated_at) "
        f"VALUES ({', '.join('?' for _ in columns)}, 0, ?, ?)",
        (*values, now, now),
    )
    new_id = cursor.lastrowid
    conn.execute("INSERT INTO promotion_popup_stats (promo_id) VALUES (?)", (new_id,))
    return get_promotion(conn, new_id)


def _stored_image_id(url):
    match = IMAGE_PATH_PATTERN.fullmatch(str(url or ""))
    return match.group(1) if match else None


def delete_promotion(conn, promo_id):
    row = conn.execute("SELECT image_url FROM promotions WHERE id = ?", (promo_id,)).fetchone()
    if not row:
        return False
    conn.execute("DELETE FROM promotions WHERE id = ?", (promo_id,))
    image_id = _stored_image_id(row["image_url"])
    if image_id:
        used = conn.execute(
            "SELECT 1 FROM promotions WHERE image_url = ? LIMIT 1",
            (row["image_url"],),
        ).fetchone()
        if not used:
            conn.execute("DELETE FROM promotion_popup_images WHERE id = ?", (image_id,))
    return True


def store_image(conn, data, mime_type):
    if not isinstance(data, bytes) or not data or len(data) > MAX_IMAGE_BYTES:
        return None, "L'image doit faire 2 Mo maximum."
    if mime_type == "image/jpeg" and data.startswith(b"\xff\xd8\xff"):
        extension = "jpeg"
    elif mime_type == "image/webp" and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        extension = "webp"
    else:
        return None, "Format non pris en charge. Utilisez une image WebP ou JPEG."
    image_id = uuid.uuid4().hex
    conn.execute(
        "INSERT INTO promotion_popup_images (id, mime_type, data, created_at) VALUES (?, ?, ?, ?)",
        (image_id, mime_type, data, _timestamp()),
    )
    return {"url": f"/api/promotions/images/{image_id}", "format": extension, "size": len(data)}, None


def image_by_id(conn, image_id):
    if not re.fullmatch(r"[a-f0-9]{32}", str(image_id or "")):
        return None
    return conn.execute(
        "SELECT mime_type, data FROM promotion_popup_images WHERE id = ?",
        (image_id,),
    ).fetchone()


def record_event(conn, promo_id, session_id, event):
    if event not in {"impression", "click", "close"} or not session_id:
        return False
    cursor = conn.execute(
        "INSERT OR IGNORE INTO promotion_popup_events (promo_id, session_id, event, event_day) "
        "SELECT id, ?, ?, ? FROM promotions WHERE id = ?",
        (str(session_id), event, _now().date().isoformat(), promo_id),
    )
    if cursor.rowcount:
        column = {"impression": "impressions", "click": "clicks", "close": "closes"}[event]
        conn.execute(
            f"INSERT INTO promotion_popup_stats (promo_id, {column}) VALUES (?, 1) "
            f"ON CONFLICT(promo_id) DO UPDATE SET {column} = {column} + 1",
            (promo_id,),
        )
    return bool(cursor.rowcount)


def seed_demo_promotion(conn, *, active=False):
    exists = conn.execute(
        "SELECT id, image_url, cta_texte, couleur_fond FROM promotions WHERE titre = ? LIMIT 1",
        ("Tous nos plats",),
    ).fetchone()
    if exists:
        if (
            exists["image_url"] == "/images/burger-hero.jpg"
            and exists["cta_texte"] == "Découvrir la carte"
            and exists["couleur_fond"] == "#F6EBD9"
        ):
            conn.execute(
                "UPDATE promotions SET image_url = ?, cta_texte = ?, updated_at = ? WHERE id = ?",
                ("/images/bowl.jpg", "COMMANDER MAINTENANT", _timestamp(), exists["id"]),
            )
        return
    start = _now() - timedelta(minutes=1)
    end = start + timedelta(days=14)
    now = _timestamp()
    cursor = conn.execute(
        """
        INSERT INTO promotions (
          titre, prix, ancien_prix, badge_texte, afficher_pastille_reduction,
          description, image_url, cta_texte, cta_lien, mention_legale,
          date_debut, date_fin, actif, priorite, pages_cibles, frequence,
          delai_affichage, intention_de_sortie, couleur_fond, couleur_accent,
          created_at, updated_at
        ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 'session', 6, 0, '#F6EBD9', '#FF6A13', ?, ?)
        """,
        (
            "Tous nos plats",
            "9.90",
            "14.90",
            "OFFRE DE LANCEMENT",
            "Profite de nos prix de lancement et découvre nos spécialités afro street food.",
            "/images/bowl.jpg",
            "COMMANDER MAINTENANT",
            "/carte",
            "",
            start.isoformat(timespec="minutes"),
            end.isoformat(timespec="minutes"),
            int(bool(active)),
            json.dumps(["accueil", "menu"], ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.execute(
        "INSERT INTO promotion_popup_stats (promo_id) VALUES (?)",
        (cursor.lastrowid,),
    )


def seed_premium_promotion(conn):
    exists = conn.execute(
        "SELECT id FROM promotions WHERE theme = 'premium' OR titre = ? LIMIT 1",
        ("Menu Afro-Food",),
    ).fetchone()
    if exists:
        return
    start = _now() - timedelta(minutes=1)
    end = start + timedelta(days=14)
    now = _timestamp()
    cursor = conn.execute(
        """
        INSERT INTO promotions (
          titre, prix, ancien_prix, badge_texte, afficher_pastille_reduction,
          description, image_url, cta_texte, cta_lien, mention_legale,
          date_debut, date_fin, actif, priorite, pages_cibles, frequence,
          delai_affichage, intention_de_sortie, couleur_fond, couleur_accent,
          theme, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?, 'session', 6, 0,
          '#1E0F08', '#FF6A13', 'premium', ?, ?)
        """,
        (
            "Menu Afro-Food",
            "9.90",
            "14.90",
            "OFFRE DE LANCEMENT – 2 SEMAINES",
            "Profitez de notre menu afro-food à prix spécial, à emporter ou en livraison.",
            "/images/bowl.jpg",
            "COMMANDER MAINTENANT",
            "/carte",
            "",
            start.isoformat(timespec="minutes"),
            end.isoformat(timespec="minutes"),
            json.dumps(["accueil", "menu"], ensure_ascii=False),
            now,
            now,
        ),
    )
    conn.execute(
        "INSERT INTO promotion_popup_stats (promo_id) VALUES (?)",
        (cursor.lastrowid,),
    )
