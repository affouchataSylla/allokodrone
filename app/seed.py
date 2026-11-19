import json

from app.schedule import DEFAULT_HOURS, DEFAULT_MIDI

# Tarifs publies sur la carte menu ALLOKO DRONE (nov. 2026).
# Riz blanc inclus dans le bowl ; riz Jollof +1 euro.
# Salade Berbéré absente de cette carte : reste sans prix.

BOWL_PROTEINS = [
    ("Poulet effiloché", 0, 1),
    ("Spice Wings x3", 0, 1),
    ("Veggie", 0, 1),
    ("Bœuf effiloché", 0, 1),
]

BOWL_SAUCES = [
    ("Mafé (à l'arachide)", 0, 1),
    ("Yassa", 0, 1),
    ("NANJI", 0, 1),
]

BOWL_SIDES = [
    ("Suya Fries", 0, 1),
    ("Alloko", 0, 1),
    ("Accras", 0, 1),
    ("Rougail tomates", 0, 1),
]


PUBLISHED_COPY = {
    "pby": "Bœuf effiloché épices Cajun, sauce Yassa, roquette, Allokos, double cheddar, moutarde douce.",
    "suya-mama": "Galette végétale aux épices Kankan, mayo épicée, sauce arachide, chou rouge, cheddar, roquette.",
    "pcy": "Poulet effiloché épices Cajun, sauce Yassa, roquette, Allokos, double cheddar, moutarde douce.",
    "bowl": "Créez votre bowl : choisissez votre base, votre viande, votre sauce et votre accompagnement. Riz blanc ou riz Jollof (+1 €).",
    "accras": "Beignets fait maison au poisson.",
    "spice-wings": "Ailes de poulet aux épices maison.",
    "alloko": "Banane plantain frite.",
    "suya-fries": "Frites maison aux épices Suya.",
    "rougail": "Salade de tomates, coriandre, oignon et gingembre.",
    "og-mafe": "Plat à base de sauce mafé, accompagné d'une base au choix, d'une viande au choix et d'alloko.",
    "og-yassa": "Plat à base de sauce yassa, accompagné d'une base au choix, d'une viande au choix et d'alloko.",
    "nanji-combo": "Bowl à base de riz Jollof, de sauce nanji, d'une viande au choix, d'alloko et de rougail tomates.",
    "dekiri": "Le premier Dégué saveur Thiakry.",
}

PUBLISHED_PRICES = {
    "pby": ("DKR Beef — Pulled Beef Yassa", 1390),
    "suya-mama": ("Kankan Burger (Veggie)", 1290),
    "pcy": ("DKR Chicken — Pulled Chicken Yassa", 1190),
    "bowl": ("Bowl à composer", 1390),
    "accras": ("Accras", 650),
    "spice-wings": ("Spice Wings", 650),
    "alloko": ("Alloko", 490),
    "suya-fries": ("Suya Fries", 490),
    "rougail": ("Rougail tomates", 450),
    "og-mafe": ("BKO Mafé", 1290),
    "og-yassa": ("DKR Yassa", 1290),
    "nanji-combo": ("Lagos Bowl", 1150),
    "gingembre": ("Gingembre", 450),
    "bissap": ("Bissap", 450),
    "mango-colada": ("Mango Colada", 450),
    "vimto": ("Vimto", 290),
    "vitamalt": ("Vitamalt", 290),
    "eau": ("Eau", 250),
    "san-pellegrino": ("San Pellegrino", 250),
    "jus": ("Jus", 250),
    "coca": ("Coca", 250),
    "dekiri": ("Dekiri", 450),
    "banana-bread": ("Banana bread", 290),
    "yam-cake": ("Yam Cake", 290),
    "choco-manioc": ("Choco-Manioc", 290),
    "midi-bowl": ("Bowl au choix + boisson", 1490),
    "midi-etudiant": ("Combo étudiant + boisson", 990),
    "midi-wings": ("Menu Spice Wings Combo", 1350),
}


def seed(conn, *, publish_demo=False):
    from app.promo_popups import seed_demo_promotion, seed_premium_promotion

    seed_demo_promotion(conn, active=publish_demo)
    seed_premium_promotion(conn)
    existing = conn.execute("SELECT COUNT(*) AS n FROM categories").fetchone()["n"]
    if existing:
        _refresh_published_copy(conn)
        return
    conn.execute("BEGIN")
    try:
        categories = [
            ("burgers", "Afro Burgers", 1),
            ("bowls", "Bowls à composer", 2),
            ("sides", "Starters & Sides", 3),
            ("plats", "Plats signature", 4),
            ("boissons", "Drinks", 5),
            ("desserts", "Desserts", 6),
            ("midi", "Menus midi", 7),
        ]
        category_ids = {}
        for slug, name, order in categories:
            cur = conn.execute(
                "INSERT INTO categories (slug, name, sort_order) VALUES (?, ?, ?)",
                (slug, name, order),
            )
            category_ids[slug] = cur.lastrowid

        def add_product(category, slug, name, description, **extra):
            fields = {
                "image": None,
                "price_cents": None,
                "price_confirmed": 0,
                "available": 1,
                "orderable": 1,
                "block_reason": None,
                "service_window": None,
                "featured": 0,
                "sort_order": 1,
            }
            fields.update(extra)
            cur = conn.execute(
                """
                INSERT INTO products (
                  category_id, slug, name, description, image, price_cents, price_confirmed,
                  available, orderable, block_reason, service_window, featured, sort_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    category_ids[category],
                    slug,
                    name,
                    description,
                    fields["image"],
                    fields["price_cents"],
                    fields["price_confirmed"],
                    fields["available"],
                    fields["orderable"],
                    fields["block_reason"],
                    fields["service_window"],
                    fields["featured"],
                    fields["sort_order"],
                ),
            )
            return cur.lastrowid

        def add_group(product_id, name, choices, sort_order, required=1):
            cur = conn.execute(
                """
                INSERT INTO option_groups (product_id, name, required, min_select, max_select, sort_order)
                VALUES (?, ?, ?, 1, 1, ?)
                """,
                (product_id, name, required, sort_order),
            )
            group_id = cur.lastrowid
            for index, (label, delta, confirmed) in enumerate(choices, start=1):
                conn.execute(
                    """
                    INSERT INTO option_choices (
                      group_id, name, price_delta_cents, price_delta_confirmed, available, sort_order
                    ) VALUES (?, ?, ?, ?, 1, ?)
                    """,
                    (group_id, label, delta, confirmed, index),
                )

        add_product(
            "burgers",
            "pby",
            PUBLISHED_PRICES["pby"][0],
            PUBLISHED_COPY["pby"],
            image="burger.jpg",
            price_cents=PUBLISHED_PRICES["pby"][1],
            price_confirmed=1,
            featured=1,
            sort_order=1,
        )
        add_product(
            "burgers",
            "suya-mama",
            PUBLISHED_PRICES["suya-mama"][0],
            PUBLISHED_COPY["suya-mama"],
            price_cents=PUBLISHED_PRICES["suya-mama"][1],
            price_confirmed=1,
            sort_order=2,
        )
        add_product(
            "burgers",
            "pcy",
            PUBLISHED_PRICES["pcy"][0],
            PUBLISHED_COPY["pcy"],
            price_cents=PUBLISHED_PRICES["pcy"][1],
            price_confirmed=1,
            sort_order=3,
        )

        bowl_id = add_product(
            "bowls",
            "bowl",
            PUBLISHED_PRICES["bowl"][0],
            PUBLISHED_COPY["bowl"],
            image="bowl.jpg",
            price_cents=PUBLISHED_PRICES["bowl"][1],
            price_confirmed=1,
            featured=1,
            sort_order=1,
        )
        add_group(
            bowl_id,
            "Base",
            [("Riz blanc", 0, 1), ("Riz Jollof", 100, 1)],
            1,
        )
        add_group(bowl_id, "Viande", BOWL_PROTEINS, 2)
        add_group(bowl_id, "Sauce", BOWL_SAUCES, 3)
        add_group(bowl_id, "Side", BOWL_SIDES, 4)

        sides = [
            ("accras", None),
            ("spice-wings", "wings.jpg"),
            ("alloko", "alloko.jpg"),
            ("suya-fries", None),
            ("salade-berbere", None),
            ("rougail", None),
        ]
        for index, (slug, image) in enumerate(sides, start=1):
            priced = PUBLISHED_PRICES.get(slug)
            add_product(
                "sides",
                slug,
                priced[0] if priced else ("Salade Berbéré (Veggie)" if slug == "salade-berbere" else slug),
                PUBLISHED_COPY.get(slug) or ("Crudités, sauce maison aux épices berbéré." if slug == "salade-berbere" else ""),
                image=image,
                price_cents=priced[1] if priced else None,
                price_confirmed=1 if priced else 0,
                featured=1 if slug in {"spice-wings", "alloko"} else 0,
                sort_order=index,
            )

        mafe = add_product(
            "plats",
            "og-mafe",
            PUBLISHED_PRICES["og-mafe"][0],
            PUBLISHED_COPY["og-mafe"],
            price_cents=PUBLISHED_PRICES["og-mafe"][1],
            price_confirmed=1,
            sort_order=1,
        )
        add_group(mafe, "Base", [("Riz blanc", 0, 1), ("Riz Jollof", 0, 1)], 1)
        add_group(mafe, "Viande", BOWL_PROTEINS, 2)
        yassa = add_product(
            "plats",
            "og-yassa",
            PUBLISHED_PRICES["og-yassa"][0],
            PUBLISHED_COPY["og-yassa"],
            price_cents=PUBLISHED_PRICES["og-yassa"][1],
            price_confirmed=1,
            sort_order=2,
        )
        add_group(yassa, "Base", [("Riz blanc", 0, 1), ("Riz Jollof", 0, 1)], 1)
        add_group(yassa, "Viande", BOWL_PROTEINS, 2)
        nanji = add_product(
            "plats",
            "nanji-combo",
            PUBLISHED_PRICES["nanji-combo"][0],
            PUBLISHED_COPY["nanji-combo"],
            price_cents=PUBLISHED_PRICES["nanji-combo"][1],
            price_confirmed=1,
            sort_order=3,
        )
        add_group(nanji, "Viande", BOWL_PROTEINS, 1)

        drinks = [
            ("gingembre", "Cocktail & special."),
            ("bissap", "Cocktail & special."),
            ("mango-colada", "Cocktail & special."),
            ("vimto", "OG Classic."),
            ("vitamalt", "OG Classic."),
            ("eau", "Cannette & eau."),
            ("san-pellegrino", "Cannette & eau."),
            ("jus", "Cannette & eau."),
            ("coca", "Cannette & eau."),
        ]
        for index, (slug, description) in enumerate(drinks, start=1):
            add_product(
                "boissons",
                slug,
                PUBLISHED_PRICES[slug][0],
                description,
                price_cents=PUBLISHED_PRICES[slug][1],
                price_confirmed=1,
                sort_order=index,
            )

        desserts = [
            ("dekiri", PUBLISHED_COPY["dekiri"]),
            ("banana-bread", "Cake maison."),
            ("yam-cake", "Cake maison."),
            ("choco-manioc", "Cake maison."),
        ]
        for index, (slug, description) in enumerate(desserts, start=1):
            add_product(
                "desserts",
                slug,
                PUBLISHED_PRICES[slug][0],
                description,
                price_cents=PUBLISHED_PRICES[slug][1],
                price_confirmed=1,
                sort_order=index,
            )

        midi_reason = (
            "Formule publiee avec son prix. Le detail exact des boissons ou sides inclus "
            "reste a valider par le restaurant avant toute commande."
        )
        add_product(
            "midi",
            "midi-bowl",
            PUBLISHED_PRICES["midi-bowl"][0],
            "Formule midi : bowl au choix + boisson.",
            service_window="midi",
            price_cents=PUBLISHED_PRICES["midi-bowl"][1],
            price_confirmed=1,
            orderable=0,
            block_reason=midi_reason,
            sort_order=1,
        )
        add_product(
            "midi",
            "midi-etudiant",
            PUBLISHED_PRICES["midi-etudiant"][0],
            "Formule midi : combo étudiant + boisson.",
            service_window="midi",
            price_cents=PUBLISHED_PRICES["midi-etudiant"][1],
            price_confirmed=1,
            orderable=0,
            block_reason=midi_reason,
            sort_order=2,
        )
        add_product(
            "midi",
            "midi-wings",
            PUBLISHED_PRICES["midi-wings"][0],
            "Wings + Side + Boisson.",
            service_window="midi",
            price_cents=PUBLISHED_PRICES["midi-wings"][1],
            price_confirmed=1,
            orderable=0,
            block_reason=midi_reason,
            sort_order=3,
        )

        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("hours", json.dumps(DEFAULT_HOURS)),
        )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("midi", json.dumps(DEFAULT_MIDI)),
        )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("allow_notes", "0"),
        )
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("terms_text", ""),
        )
        conn.execute(
            """
            INSERT INTO pickup_points (name, address, active)
            VALUES (?, ?, 1)
            """,
            (
                "ALLOKODRONE",
                "24 rue Emmanuel Arago, 93130 Noisy-le-Sec",
            ),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    _refresh_published_copy(conn)


def _refresh_published_copy(conn):
    for slug, description in PUBLISHED_COPY.items():
        conn.execute(
            "UPDATE products SET description = ? WHERE slug = ?",
            (description, slug),
        )
    for slug, (name, cents) in PUBLISHED_PRICES.items():
        conn.execute(
            """
            UPDATE products
            SET name = ?, price_cents = ?, price_confirmed = 1
            WHERE slug = ?
            """,
            (name, cents, slug),
        )
    midi_reason = (
        "Formule publiee avec son prix. Le detail exact des boissons ou sides inclus "
        "reste a valider par le restaurant avant toute commande."
    )
    conn.execute(
        """
        UPDATE products
        SET orderable = 0, block_reason = ?
        WHERE slug IN ('midi-bowl', 'midi-etudiant', 'midi-wings')
        """,
        (midi_reason,),
    )
    conn.execute(
        """
        UPDATE option_choices
        SET price_delta_cents = 0, price_delta_confirmed = 1
        WHERE group_id IN (
          SELECT og.id FROM option_groups og
          JOIN products p ON p.id = og.product_id
          WHERE p.slug IN ('og-mafe', 'og-yassa', 'nanji-combo')
        )
        """
    )
    conn.execute(
        """
        UPDATE option_choices
        SET price_delta_cents = 0, price_delta_confirmed = 1
        WHERE name != 'Riz Jollof'
          AND group_id IN (
            SELECT og.id FROM option_groups og
            JOIN products p ON p.id = og.product_id
            WHERE p.slug = 'bowl'
          )
        """
    )
    conn.execute(
        """
        UPDATE option_choices
        SET price_delta_cents = 100, price_delta_confirmed = 1
        WHERE name = 'Riz Jollof'
          AND group_id IN (
            SELECT og.id FROM option_groups og
            JOIN products p ON p.id = og.product_id
            WHERE p.slug = 'bowl'
          )
        """
    )
