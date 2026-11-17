"""Smoke test production AlloKodrone."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
import http.cookiejar

BASE = "https://allokodrone.vercel.app"
jar = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, bool(ok), detail))
    print(("OK   " if ok else "FAIL "), name, detail)


def call(method: str, path: str, body=None, headers=None):
    hdrs = {"Accept": "application/json", "User-Agent": "AllocodroneSiteTest/1.0"}
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE + path, data=data, headers=hdrs, method=method)
    try:
        with opener.open(req, timeout=45) as res:
            raw = res.read()
            ctype = res.headers.get("Content-Type", "")
            payload = json.loads(raw.decode("utf-8")) if "json" in ctype else raw[:300]
            return res.status, payload
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            payload = raw[:300].decode("utf-8", "replace")
        return exc.code, payload


def page(path: str):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "AllocodroneSiteTest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            html = res.read(1200).decode("utf-8", "replace")
            return res.status, html
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(300).decode("utf-8", "replace")
    except Exception as exc:
        return 0, str(exc)


def asset(path: str):
    req = urllib.request.Request(BASE + path, headers={"User-Agent": "AllocodroneSiteTest/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.status, res.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception as exc:
        return 0, str(exc)


for path in ["/", "/carte", "/panier", "/commander", "/contact", "/avis", "/concept"]:
    status, html = page(path)
    ok = status == 200 and ("id=\"root\"" in html or "ALLOKODRONE" in html.upper() or "<!DOCTYPE" in html.upper())
    check(f"page {path}", ok, f"status={status}")

status, session = call("GET", "/api/session")
csrf = session.get("csrf") if isinstance(session, dict) else ""
slots = session.get("slots") if isinstance(session, dict) else []
check(
    "GET /api/session",
    status == 200 and bool(csrf) and isinstance(slots, list) and len(slots) > 0,
    f"status={status} slots={len(slots) if isinstance(slots, list) else 0} csrf={bool(csrf)}",
)

status, home = call("GET", "/api/accueil")
featured = home.get("featured") if isinstance(home, dict) else []
categories = home.get("categories") if isinstance(home, dict) else []
check(
    "GET /api/accueil",
    status == 200 and bool(featured) and bool(categories),
    f"status={status} featured={len(featured or [])} cats={len(categories or [])}",
)

status, carte = call("GET", "/api/carte")
check("GET /api/carte", status == 200, f"status={status} keys={list(carte)[:10] if isinstance(carte, dict) else carte}")

product = (featured or [{}])[0]
pid = product.get("id")
slug = product.get("slug")
check("produit signature", bool(pid), f"id={pid} slug={slug}")

if slug:
    status, product_page = call("GET", f"/api/produit/{slug}")
    check(f"GET /api/produit/{slug}", status == 200, f"status={status} keys={list(product_page)[:8] if isinstance(product_page, dict) else product_page}")

status, panier = call("GET", "/api/panier")
check("GET /api/panier", status == 200, f"status={status} body={str(panier)[:160]}")

# refresh csrf after session/cart calls
status, session = call("GET", "/api/session")
csrf = session.get("csrf") if isinstance(session, dict) else csrf

add_bodies = [
    {"produit": pid, "quantite": 1, "choix": [], "notes": ""},
    {"productId": pid, "quantity": 1, "choiceIds": []},
]
added = None
add_status = 0
for body in add_bodies:
    add_status, added = call("POST", "/api/panier/ajouter", body, headers={"X-CSRF": csrf})
    if add_status == 400:
        status, session = call("GET", "/api/session")
        csrf = session.get("csrf") if isinstance(session, dict) else csrf
        add_status, added = call("POST", "/api/panier/ajouter", body, headers={"X-CSRF": csrf})
    if add_status < 400:
        break
check("POST /api/panier/ajouter", add_status < 400, f"status={add_status} body={str(added)[:200]}")

status, panier = call("GET", "/api/panier")
lines = []
if isinstance(panier, dict):
    lines = panier.get("lines") or panier.get("items") or panier.get("cart", {}).get("lines") or []
check("panier non vide", status == 200 and len(lines) > 0, f"status={status} lines={len(lines)} body={str(panier)[:180]}")

status, checkout = call("GET", "/api/commander")
check(
    "GET /api/commander",
    status == 200 and isinstance(checkout, dict),
    f"status={status} keys={list(checkout)[:12] if isinstance(checkout, dict) else checkout}",
)

slot_id = ""
if isinstance(checkout, dict) and checkout.get("slots"):
    slot_id = str(checkout["slots"][0]["id"])
elif slots:
    slot_id = str(slots[0]["id"])

methods = []
if isinstance(checkout, dict):
    methods = checkout.get("paymentMethods") or checkout.get("methods") or checkout.get("payments") or []
method = "pay_on_delivery"
for item in methods:
    code = item.get("code") if isinstance(item, dict) else item
    if code and code != "stripe":
        method = code
        break
if methods and method == "pay_on_delivery":
    first = methods[0]
    method = first.get("code") if isinstance(first, dict) else first

order_body = {
    "idempotencyKey": "site-smoke-order-1",
    "nom": "Test Site",
    "email": "test@example.com",
    "telephone": "0612345678",
    "mode": "pickup",
    "slotId": slot_id,
    "paiement": method,
    "conditions": True,
}
status, order = call("POST", "/api/commander", order_body, headers={"X-CSRF": csrf})
if status == 400:
    status, session = call("GET", "/api/session")
    csrf = session.get("csrf") if isinstance(session, dict) else csrf
    status, order = call("POST", "/api/commander", order_body, headers={"X-CSRF": csrf})
ok_order = status == 200 and isinstance(order, dict) and (order.get("ok") or order.get("ref"))
check("POST /api/commander", ok_order or (status == 422 and isinstance(order, dict)), f"status={status} body={str(order)[:240]}")

ref = order.get("ref") if isinstance(order, dict) else None
if ref:
    status, conf = call("GET", f"/api/commande/{ref}")
    check(f"GET /api/commande/{ref}", status == 200, f"status={status} body={str(conf)[:180]}")

status, html = page("/admin")
check("GET /admin", status == 200 and ("connexion" in html.lower() or "admin" in html.lower() or "mot de passe" in html.lower() or "email" in html.lower()), f"status={status}")

for path in ["/images/burger.jpg", "/images/alloko.jpg", "/videos/signature.mp4"]:
    st, ctype = asset(path)
    check(f"asset {path}", st == 200, f"status={st} type={ctype}")

status, pay = call(
    "POST",
    "/api/paiement/verifier",
    {"ref": "AK-DEADBEEF", "sessionId": "cs_test_x"},
    headers={"X-CSRF": csrf},
)
check("POST /api/paiement/verifier unknown", status in (400, 404, 422), f"status={status} body={str(pay)[:160]}")

print("\n=== SUMMARY ===")
fails = [item for item in results if not item[1]]
print(f"passed={len(results) - len(fails)} failed={len(fails)} total={len(results)}")
for name, _ok, detail in fails:
    print("FAIL:", name, "|", detail)
