import json
import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from app.api import dispatch_api
from app.db import init_db
from app.pages import admin_promo_codes, admin_promotions
from app.promo_popups import (
    get_active_promotion,
    get_promotion,
    duplicate_promotion,
    record_event,
    save_promotion,
    seed_demo_promotion,
    seed_premium_promotion,
    store_image,
)
from app.seed import seed


class PromotionPopupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = init_db(os.path.join(self.tmp.name, "promotions.db"))
        seed(self.conn)

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def payload(self, *, title="Test menu", pages=None, priority=0, end=None):
        now = datetime.now().replace(microsecond=0)
        return {
            "titre": title,
            "prix": "9.90",
            "ancien_prix": "14.90",
            "badge_texte": "OFFRE DE LANCEMENT",
            "description": "Un menu à prix spécial.",
            "image_url": "",
            "cta_texte": "COMMANDER MAINTENANT",
            "cta_lien": "/carte",
            "mention_legale": "",
            "date_debut": (now - timedelta(minutes=5)).isoformat(timespec="minutes"),
            "date_fin": (end or now + timedelta(days=1)).isoformat(timespec="minutes"),
            "actif": True,
            "priorite": priority,
            "pages_cibles": pages or ["accueil"],
            "frequence": "session",
            "delai_affichage": 4,
            "intention_de_sortie": False,
            "couleur_fond": "#F6EBD9",
            "couleur_accent": "#FF6A13",
        }

    def test_seed_demo_is_present_but_not_automatically_published(self):
        seed_demo_promotion(self.conn)
        promo = self.conn.execute(
            "SELECT titre, prix, ancien_prix, image_url, delai_affichage, couleur_fond, theme, actif FROM promotions WHERE titre = ?",
            ("Tous nos plats",),
        ).fetchone()
        self.assertEqual(promo["prix"], 9.9)
        self.assertEqual(promo["ancien_prix"], 14.9)
        self.assertEqual(promo["image_url"], "/images/bowl.jpg")
        self.assertEqual(promo["delai_affichage"], 6)
        self.assertEqual(promo["couleur_fond"], "#F6EBD9")
        self.assertEqual(promo["theme"], "beige")
        self.assertEqual(promo["actif"], 0)

    def test_seed_can_publish_the_demo_promotion(self):
        path = os.path.join(self.tmp.name, "published.db")
        conn = init_db(path)
        try:
            seed(conn, publish_demo=True)
            promo = conn.execute(
                "SELECT actif FROM promotions WHERE titre = ?",
                ("Tous nos plats",),
            ).fetchone()
            self.assertEqual(promo["actif"], 1)
        finally:
            conn.close()

    def test_premium_demo_is_distinct_and_disabled_by_default(self):
        seed_premium_promotion(self.conn)
        promo = self.conn.execute(
            """
            SELECT titre, prix, ancien_prix, badge_texte, image_url, theme,
                   couleur_fond, couleur_accent, actif, delai_affichage
            FROM promotions WHERE theme = 'premium'
            """
        ).fetchone()
        self.assertEqual(promo["titre"], "Menu Afro-Food")
        self.assertEqual(promo["prix"], 9.9)
        self.assertEqual(promo["ancien_prix"], 14.9)
        self.assertEqual(promo["badge_texte"], "OFFRE DE LANCEMENT – 2 SEMAINES")
        self.assertEqual(promo["image_url"], "/images/bowl.jpg")
        self.assertEqual(promo["couleur_fond"], "#1E0F08")
        self.assertEqual(promo["couleur_accent"], "#FF6A13")
        self.assertEqual(promo["actif"], 0)
        self.assertEqual(promo["delai_affichage"], 6)

    def test_theme_is_persisted_exposed_and_duplicated(self):
        data = self.payload(title="Offre sombre")
        data.update(theme="premium", couleur_fond="#1E0F08")
        promo, error = save_promotion(self.conn, data)
        self.assertIsNone(error)
        self.assertEqual(promo["theme"], "premium")

        self.conn.execute("UPDATE promotions SET actif = 1 WHERE id = ?", (promo["id"],))
        self.assertEqual(get_active_promotion(self.conn, "accueil")["theme"], "premium")

        duplicate = duplicate_promotion(self.conn, promo["id"])
        self.assertEqual(duplicate["theme"], "premium")

    def test_unmodified_demo_uses_bowl_photo_and_short_cta(self):
        promo = self.conn.execute(
            "SELECT id FROM promotions WHERE titre = ?",
            ("Tous nos plats",),
        ).fetchone()
        self.conn.execute(
            "UPDATE promotions SET image_url = ?, cta_texte = ? WHERE id = ?",
            ("/images/burger-hero.jpg", "Découvrir la carte", promo["id"]),
        )

        seed_demo_promotion(self.conn)

        updated = self.conn.execute(
            "SELECT image_url, cta_texte FROM promotions WHERE id = ?",
            (promo["id"],),
        ).fetchone()
        self.assertEqual(updated["image_url"], "/images/bowl.jpg")
        self.assertEqual(updated["cta_texte"], "COMMANDER MAINTENANT")

    def test_adding_demo_promotion_keeps_existing_offer(self):
        promo = self.conn.execute(
            "SELECT id FROM promotions WHERE titre = ?",
            ("Tous nos plats",),
        ).fetchone()
        self.conn.execute(
            """
            UPDATE promotions
            SET titre = 'Offre de lancement', badge_texte = 'OFFRE DE LANCEMENT – 2 SEMAINES',
                description = 'Menu de lancement à prix spécial, à emporter ou en livraison.',
                image_url = '/images/bowl.jpg', cta_texte = 'COMMANDER MAINTENANT',
                delai_affichage = 4, couleur_fond = '#1E0F08'
            WHERE id = ?
            """,
            (promo["id"],),
        )

        seed_demo_promotion(self.conn)

        existing = self.conn.execute(
            "SELECT titre, image_url, delai_affichage, couleur_fond, actif FROM promotions WHERE id = ?",
            (promo["id"],),
        ).fetchone()
        self.assertEqual(existing["titre"], "Offre de lancement")
        self.assertEqual(existing["image_url"], "/images/bowl.jpg")
        self.assertEqual(existing["delai_affichage"], 4)
        self.assertEqual(existing["couleur_fond"], "#1E0F08")

        added = self.conn.execute(
            "SELECT id, image_url, delai_affichage, actif FROM promotions WHERE titre = ?",
            ("Tous nos plats",),
        ).fetchone()
        self.assertNotEqual(added["id"], promo["id"])
        self.assertEqual(added["image_url"], "/images/bowl.jpg")
        self.assertEqual(added["delai_affichage"], 6)
        self.assertEqual(added["actif"], 0)

        seed_demo_promotion(self.conn)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM promotions WHERE titre = ?",
            ("Tous nos plats",),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_new_promotions_default_to_six_second_delay(self):
        data = self.payload()
        data.pop("delai_affichage")
        data.pop("cta_texte")
        promo, error = save_promotion(self.conn, data)
        self.assertIsNone(error)
        self.assertEqual(promo["delai_affichage"], 6)
        self.assertEqual(promo["cta_texte"], "COMMANDER MAINTENANT")

    def test_active_promotion_obeys_page_target_and_priority(self):
        menu, error = save_promotion(self.conn, self.payload(pages=["menu"], priority=1))
        self.assertIsNone(error)
        all_pages, error = save_promotion(
            self.conn,
            self.payload(title="Toutes pages", pages=["toutes"], priority=5),
        )
        self.assertIsNone(error)
        self.assertEqual(get_active_promotion(self.conn, "menu")["id"], all_pages["id"])
        self.assertEqual(get_active_promotion(self.conn, "accueil")["id"], all_pages["id"])

        self.conn.execute("UPDATE promotions SET actif = 0 WHERE id = ?", (all_pages["id"],))
        self.assertEqual(get_active_promotion(self.conn, "menu")["id"], menu["id"])
        self.assertIsNone(get_active_promotion(self.conn, "accueil"))

    def test_end_minute_remains_active_until_its_last_second(self):
        end = datetime.now().replace(second=0, microsecond=0) + timedelta(minutes=2)
        promo, error = save_promotion(self.conn, self.payload(end=end))
        self.assertIsNone(error)
        with patch("app.promo_popups._now", return_value=end + timedelta(seconds=30)):
            self.assertEqual(get_active_promotion(self.conn, "accueil")["id"], promo["id"])

    def test_event_statistics_are_deduplicated_per_session_and_day(self):
        promo, error = save_promotion(self.conn, self.payload())
        self.assertIsNone(error)
        self.assertTrue(record_event(self.conn, promo["id"], "session-a", "impression"))
        self.assertFalse(record_event(self.conn, promo["id"], "session-a", "impression"))
        self.assertEqual(get_promotion(self.conn, promo["id"])["impressions"], 1)

    def test_custom_colors_must_keep_accessible_contrast(self):
        data = self.payload()
        data["couleur_fond"] = "#1E0F08"
        promo, error = save_promotion(self.conn, data)
        self.assertIsNone(promo)
        self.assertIn("contraste", error)

    def test_premium_theme_defaults_to_its_dark_background(self):
        data = self.payload()
        data.pop("couleur_fond")
        data.update(theme="premium")
        promo, error = save_promotion(self.conn, data)
        self.assertIsNone(error)
        self.assertEqual(promo["couleur_fond"], "#1E0F08")

    def test_upload_accepts_supported_image_signatures_and_rejects_oversize(self):
        image, error = store_image(self.conn, b"\xff\xd8\xffdata", "image/jpeg")
        self.assertIsNone(error)
        self.assertEqual(image["format"], "jpeg")

        image, error = store_image(self.conn, b"x" * (2 * 1024 * 1024 + 1), "image/jpeg")
        self.assertIsNone(image)
        self.assertIn("2 Mo", error)

    def test_admin_api_rejects_unauthenticated_and_driver_accounts(self):
        for user in (None, {"role": "driver"}):
            response = dispatch_api(
                SimpleNamespace(conn=self.conn, user=user, session={"id": "test-session"}),
                "GET",
                "/api/admin/promotions",
                {},
                {},
            )
            self.assertEqual(response.status, 403)

    def test_admin_api_saves_a_premium_promotion(self):
        context = SimpleNamespace(
            conn=self.conn,
            session={"id": "admin-session"},
            user={"id": 1, "role": "admin"},
        )
        data = self.payload(title="Offre Premium")
        data.update(theme="premium", couleur_fond="#1E0F08")

        response = dispatch_api(context, "POST", "/api/admin/promotions", {}, data)

        self.assertEqual(response.status, 201)
        saved = json.loads(response.body)["promotion"]
        self.assertEqual(saved["theme"], "premium")
        self.assertEqual(saved["couleur_fond"], "#1E0F08")

    def test_promotions_page_uses_the_existing_admin_navigation(self):
        context = SimpleNamespace(
            conn=self.conn,
            session={"id": "admin-session", "csrf": "test-csrf"},
            user={"id": 1, "role": "admin"},
            flash="",
            path="/admin/promotions",
        )
        response = admin_promotions(context)
        self.assertIn('id="root"', response)
        self.assertIn('aria-label="Administration"', response)
        self.assertIn("Tableau de bord", response)
        self.assertIn('href="/admin/codes-promo" aria-current="page"', response)
        self.assertLess(response.index("/assets/"), response.index("/css/app.css"))

        codes_page = admin_promo_codes(context)
        self.assertIn('aria-label="Gestion des promotions"', codes_page)
        self.assertIn('href="/admin/promotions">Pop-ups promotionnels', codes_page)


class PromoCodeMigrationTests(unittest.TestCase):
    def test_existing_popup_promotions_receive_beige_theme(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy-popup.db")
            conn = sqlite3.connect(path)
            conn.execute(
                """
                CREATE TABLE promotions (
                  id INTEGER PRIMARY KEY, titre TEXT NOT NULL, actif INTEGER,
                  priorite INTEGER, date_debut TEXT, date_fin TEXT
                )
                """
            )
            conn.execute(
                "INSERT INTO promotions (titre, actif, priorite, date_debut, date_fin) "
                "VALUES ('Ancienne offre', 0, 0, '', '')"
            )
            conn.commit()
            conn.close()

            migrated = init_db(path)
            theme = migrated.execute(
                "SELECT theme FROM promotions WHERE titre = 'Ancienne offre'"
            ).fetchone()["theme"]
            migrated.close()

            self.assertEqual(theme, "beige")

    def test_legacy_promo_codes_are_preserved_while_popup_table_is_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "legacy.db")
            conn = sqlite3.connect(path)
            conn.executescript(
                """
                CREATE TABLE promotions (
                  id INTEGER PRIMARY KEY,
                  code TEXT NOT NULL UNIQUE COLLATE NOCASE,
                  label TEXT NOT NULL,
                  kind TEXT NOT NULL CHECK(kind IN ('amount', 'percent')),
                  amount_cents INTEGER,
                  percent INTEGER,
                  active INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO promotions (code, label, kind, amount_cents, percent, active)
                VALUES ('WELCOME', 'Welcome', 'percent', NULL, 10, 1);
                """
            )
            conn.close()

            migrated = init_db(path)
            code = migrated.execute(
                "SELECT code, percent, active FROM promo_codes WHERE code = 'WELCOME'"
            ).fetchone()
            popup_columns = {
                row["name"] for row in migrated.execute("PRAGMA table_info(promotions)")
            }
            migrated.close()

            self.assertEqual(code["percent"], 10)
            self.assertEqual(code["active"], 1)
            self.assertIn("titre", popup_columns)


if __name__ == "__main__":
    unittest.main()
