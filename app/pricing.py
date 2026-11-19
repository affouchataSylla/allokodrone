from app.catalog import choice_by_id, groups_for_product, product_by_id
from app.schedule import is_midi, load_json_setting, now_paris


class LineQuote:
    def __init__(self, product, quantity, choice_rows, notes, unit_cents, issues, summary):
        self.product = product
        self.quantity = quantity
        self.choice_rows = choice_rows
        self.notes = notes
        self.unit_cents = unit_cents
        self.issues = issues
        self.summary = summary

    @property
    def ok(self):
        return self.unit_cents is not None and not self.issues

    @property
    def line_cents(self):
        if self.unit_cents is None:
            return None
        return self.unit_cents * self.quantity


def quote_product(conn, product_id, choice_ids, quantity, notes="", clock=None):
    product = product_by_id(conn, product_id)
    issues = []
    if not product:
        return LineQuote(None, quantity, [], "", None, ["Produit introuvable."], "")
    quantity = int(quantity or 0)
    if quantity < 1 or quantity > 20:
        issues.append("La quantite doit etre comprise entre 1 et 20.")
    if not product["available"]:
        issues.append(f"{product['name']} est indisponible.")
    if not product["orderable"]:
        reason = product["block_reason"] or "Ce produit n'est pas encore commandable."
        issues.append(reason)
    moment = now_paris(clock)
    if product["service_window"] == "midi":
        midi = load_json_setting(conn, "midi", {"start": "12:00", "end": "15:00", "sunday": False})
        if not is_midi(moment, midi):
            issues.append("Les menus midi sont servis de 12h a 15h, hors dimanche, selon les horaires publies.")
    if not product["price_confirmed"] or product["price_cents"] is None:
        issues.append(f"Le prix de {product['name']} n'est pas encore valide par le restaurant.")

    groups = groups_for_product(conn, product["id"])
    selected = []
    seen_groups = {}
    for choice_id in choice_ids:
        choice = choice_by_id(conn, int(choice_id))
        if not choice or choice["product_id"] != product["id"]:
            issues.append("Une option ne correspond pas a ce produit.")
            continue
        if not choice["available"]:
            issues.append(f"L'option {choice['name']} n'est plus disponible.")
        seen_groups.setdefault(choice["group_id"], []).append(choice)
        selected.append(choice)

    for group, _choices in groups:
        chosen = seen_groups.get(group["id"], [])
        if len(chosen) < group["min_select"]:
            issues.append(f"Choix obligatoire : {group['name']}.")
        if len(chosen) > group["max_select"]:
            issues.append(f"Trop de choix pour {group['name']}.")

    delta = 0
    deltas_ok = True
    for choice in selected:
        if not choice["price_delta_confirmed"] or choice["price_delta_cents"] is None:
            deltas_ok = False
            issues.append(
                f"Le supplement de l'option {choice['name']} n'est pas encore valide par le restaurant."
            )
        else:
            delta += choice["price_delta_cents"]

    allow_notes = load_json_setting(conn, "allow_notes", 0)
    clean_notes = ""
    if allow_notes and notes:
        clean_notes = " ".join(str(notes).split())[:280]

    summary = " · ".join(choice["group_name"] + " : " + choice["name"] for choice in selected)
    price_ready = (
        product["price_confirmed"]
        and product["price_cents"] is not None
        and deltas_ok
        and not any(issue.startswith("Le prix") or issue.startswith("Le supplement") for issue in issues)
    )
    unit = product["price_cents"] + delta if price_ready else None
    return LineQuote(product, quantity, selected, clean_notes, unit, issues, summary)


def apply_promo(conn, code, subtotal):
    if not code:
        return 0, None, None
    row = conn.execute(
        "SELECT * FROM promo_codes WHERE code = ? AND active = 1",
        (code.strip(),),
    ).fetchone()
    if not row:
        return 0, None, "Ce code n'est pas reconnu."
    if row["kind"] == "percent":
        percent = int(row["percent"] or 0)
        if percent < 0 or percent > 100:
            return 0, None, "Cette promotion est mal configuree."
        discount = subtotal * percent // 100
    else:
        if row["amount_cents"] is None:
            return 0, None, "Cette promotion est mal configuree."
        discount = min(subtotal, int(row["amount_cents"]))
    return discount, row["code"], None
