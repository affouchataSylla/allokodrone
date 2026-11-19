import hashlib
import hmac
import json
import os
import time
import unittest
import urllib.request
from datetime import datetime
from urllib.parse import parse_qs

from app.auth import create_session
from app.cart import add_item
from app.catalog import product_by_slug
from app.db import init_db
from app.orders import place_order
from app.schedule import PARIS
from app.seed import seed
from app.server import handle_http
from app.stripe_pay import (
    begin_checkout,
    cancel_payment,
    ensure_order_from_checkout,
    handle_webhook,
    public_base,
    verify_return,
)
import app.stripe_pay as stripe_pay

TUESDAY_NOON = datetime(2026, 10, 20, 12, 30, tzinfo=PARIS)
SECRET = "whsec_test_fixture_only"
KEY = "sk_test_fixture_not_a_real_key"


class Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeStripe:
    def __init__(self):
        self.sessions = {}
        self.creates = 0
        self.last_fields = {}

    def __call__(self, request, timeout=20):
        del timeout
        path = request.full_url.split("stripe.com/v1", 1)[-1]
        if request.get_method() == "GET" and path.rstrip("/").endswith("/account"):
            return Response({"id": "acct_test", "object": "account", "charges_enabled": True})
        if request.get_method() == "POST":
            fields = {key: values[-1] for key, values in parse_qs(request.data.decode("utf-8")).items()}
            self.last_fields = fields
            idem = request.get_header("Idempotency-key")
            existing = next((item for item in self.sessions.values() if item["idempotency"] == idem), None)
            if existing:
                return Response(existing)
            self.creates += 1
            session_id = f"cs_test_{self.creates}"
            metadata = {
                key[len("metadata[") : -1]: value
                for key, value in fields.items()
                if key.startswith("metadata[") and key.endswith("]")
            }
            session = {
                "id": session_id,
                "url": f"https://checkout.stripe.com/c/pay/{session_id}",
                "status": "open",
                "payment_status": "unpaid",
                "amount_total": int(fields["line_items[0][price_data][unit_amount]"]),
                "currency": fields["line_items[0][price_data][currency]"],
                "metadata": metadata,
                "client_reference_id": fields["client_reference_id"],
                "payment_intent": f"pi_test_{self.creates}",
                "idempotency": idem,
            }
            self.sessions[session_id] = session
            return Response(session)
        session_id = request.full_url.rsplit("/", 1)[-1]
        return Response(self.sessions[session_id])


def sign(payload, secret=SECRET):
    stamp = int(time.time())
    digest = hmac.new(secret.encode("utf-8"), f"{stamp}.".encode("utf-8") + payload, hashlib.sha256).hexdigest()
    return f"t={stamp},v1={digest}"


class StripeTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.tmp = tempfile.TemporaryDirectory()
        self.conn = init_db(os.path.join(self.tmp.name, "shop.db"))
        seed(self.conn)
        self.sid = create_session(self.conn)
        self.conn.execute(
            """
            INSERT INTO pickup_slots (slot_date, start_time, end_time, capacity, active)
            VALUES ('2026-10-20', '19:00', '19:15', 4, 1)
            """
        )
        self.slot = self.conn.execute("SELECT id FROM pickup_slots").fetchone()["id"]
        self.conn.execute(
            "UPDATE products SET price_cents = 450, price_confirmed = 1 WHERE slug = 'alloko'"
        )
        os.environ["STRIPE_SECRET_KEY"] = KEY
        os.environ["STRIPE_WEBHOOK_SECRET"] = SECRET
        stripe_pay._hits.clear()
        stripe_pay.invalidate_stripe_cache()
        self.fake = FakeStripe()
        self.original = urllib.request.urlopen
        urllib.request.urlopen = self.fake

    def tearDown(self):
        urllib.request.urlopen = self.original
        os.environ.pop("STRIPE_SECRET_KEY", None)
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        self.conn.close()
        self.tmp.cleanup()

    def form(self, key="pay-1", **extra):
        payload = {
            "idempotency_key": key,
            "nom": "Awa Diallo",
            "email": "awa@example.com",
            "telephone": "0612345678",
            "mode": "pickup",
            "slot_id": str(self.slot),
            "paiement": "stripe",
        }
        payload.update(extra)
        return payload

    def order(self, key="pay-1", **extra):
        product = product_by_slug(self.conn, "alloko")
        add_item(self.conn, self.sid, product["id"], [], 2)
        order, errors = place_order(self.conn, self.sid, None, self.form(key, **extra), clock=TUESDAY_NOON)
        self.assertEqual(errors, [])
        return order

    def test_local_payment_return_ignores_a_configured_github_pages_url(self):
        previous = os.environ.get("ALLOKO_PUBLIC_URL")
        try:
            os.environ["ALLOKO_PUBLIC_URL"] = "https://affouchatasylla.github.io/allokodrone"
            self.assertEqual(
                public_base({"host": "127.0.0.1:8080"}),
                "http://127.0.0.1:8080",
            )
            self.assertEqual(
                public_base({"host": "localhost:8080"}),
                "http://localhost:8080",
            )
            order = self.order("local-return")
            _url, error = begin_checkout(
                self.conn,
                order,
                public_base({"host": "127.0.0.1:8080"}),
            )
            self.assertIsNone(error)
            self.assertTrue(
                self.fake.last_fields["success_url"].startswith(
                    "http://127.0.0.1:8080/paiement/succes?ref="
                )
            )
            self.assertTrue(
                self.fake.last_fields["cancel_url"].startswith(
                    "http://127.0.0.1:8080/paiement/echec?ref="
                )
            )
        finally:
            if previous is None:
                os.environ.pop("ALLOKO_PUBLIC_URL", None)
            else:
                os.environ["ALLOKO_PUBLIC_URL"] = previous

    def event(self, order, kind, **fields):
        data = {
            "id": order["stripe_session_id"],
            "amount_total": order["total_cents"],
            "currency": "eur",
            "payment_status": "paid",
            "status": "complete",
            "metadata": {"order_ref": order["public_ref"]},
            "client_reference_id": order["public_ref"],
        }
        data.update(fields)
        payload = json.dumps({"id": fields.get("event_id", "evt_test_1"), "type": kind, "data": {"object": data}}).encode("utf-8")
        return payload

    def test_success_is_pending_until_stripe_confirms_amount(self):
        order = self.order()
        url, error = begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        self.assertIsNone(error)
        self.assertTrue(url.startswith("https://checkout.stripe.com/"))
        self.assertEqual(self.fake.last_fields.get("locale"), "fr")
        self.assertNotIn("payment_method_types[0]", self.fake.last_fields)
        stored = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(stored["payment_status"], "pending")
        session = self.fake.sessions[stored["stripe_session_id"]]
        session["payment_status"] = "paid"
        state, error = verify_return(self.conn, stored, stored["stripe_session_id"])
        self.assertEqual((state, error), ("paid", None))
        paid = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(paid["payment_status"], "paid")

    def test_refused_payment_stays_unpaid(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        payload = self.event(order, "checkout.session.async_payment_failed", event_id="evt_fail", payment_status="unpaid")
        status, body = handle_webhook(self.conn, payload, sign(payload))
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        row = self.conn.execute("SELECT payment_status, status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "failed")
        self.assertNotEqual(row["payment_status"], "paid")

    def test_customer_cancel_does_not_mark_paid(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertIsNone(cancel_payment(self.conn, order))
        row = self.conn.execute("SELECT payment_status, status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "cancelled")
        self.assertEqual(row["status"], "cancelled")

    def test_invalid_webhook_is_rejected(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        payload = self.event(order, "checkout.session.completed", event_id="evt_bad")
        status, _body = handle_webhook(self.conn, payload, "t=1,v1=deadbeef")
        self.assertEqual(status, 400)
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "pending")
        self.assertIsNone(self.conn.execute("SELECT 1 FROM stripe_events WHERE id = 'evt_bad'").fetchone())

    def test_wrong_amount_is_not_accepted(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.fake.sessions[order["stripe_session_id"]]["amount_total"] = 1
        self.fake.sessions[order["stripe_session_id"]]["payment_status"] = "paid"
        state, error = verify_return(self.conn, order, order["stripe_session_id"])
        self.assertIsNone(state)
        self.assertIn("montant", error)
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertNotEqual(row["payment_status"], "paid")
        payload = self.event(order, "checkout.session.completed", event_id="evt_amount", amount_total=1)
        status, body = handle_webhook(self.conn, payload, sign(payload))
        self.assertEqual(status, 200)
        self.assertEqual(body.get("reason"), "amount")
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertNotEqual(row["payment_status"], "paid")

    def test_duplicate_webhook_confirms_once(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        payload = self.event(order, "checkout.session.completed", event_id="evt_once")
        first, _body = handle_webhook(self.conn, payload, sign(payload))
        second, body = handle_webhook(self.conn, payload, sign(payload))
        self.assertEqual(first, 200)
        self.assertEqual(second, 200)
        self.assertTrue(body["duplicate"])
        count = self.conn.execute(
            "SELECT COUNT(*) AS n FROM order_events WHERE order_id = ? AND status = 'paid'",
            (order["id"],),
        ).fetchone()["n"]
        self.assertEqual(count, 1)

    def test_double_click_creates_one_checkout(self):
        order = self.order()
        first, error = begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        second, error_again = begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        self.assertIsNone(error)
        self.assertIsNone(error_again)
        self.assertEqual(first, second)
        self.assertEqual(self.fake.creates, 1)
        again, errors = place_order(self.conn, self.sid, None, self.form(), clock=TUESDAY_NOON)
        self.assertEqual(errors, [])
        self.assertEqual(again["id"], order["id"])
        self.assertEqual(self.conn.execute("SELECT COUNT(*) AS n FROM orders").fetchone()["n"], 1)

    def test_abandoned_checkout_cancels_the_order(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        payload = self.event(order, "checkout.session.expired", event_id="evt_expired", payment_status="unpaid", status="expired")
        status, _body = handle_webhook(self.conn, payload, sign(payload))
        self.assertEqual(status, 200)
        row = self.conn.execute("SELECT status, payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["status"], "cancelled")
        self.assertEqual(row["payment_status"], "cancelled")

    def test_client_price_is_ignored(self):
        order = self.order(total_cents="1", montant="1")
        self.assertEqual(order["total_cents"], 900)
        _url, error = begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        self.assertIsNone(error)
        session = next(iter(self.fake.sessions.values()))
        self.assertEqual(session["amount_total"], 900)

    def test_webhook_route_skips_csrf(self):
        order = self.order()
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        payload = self.event(order, "checkout.session.completed", event_id="evt_http")
        response = handle_http(
            self.conn,
            "POST",
            "/api/stripe/webhook",
            {"stripe-signature": sign(payload), "content-type": "application/json"},
            payload,
        )
        self.assertEqual(response.status, 200)
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "paid")

    def test_checkout_metadata_restores_missing_order(self):
        order = self.order(key="pay-recover")
        begin_checkout(self.conn, order, "http://127.0.0.1:8080")
        order = self.conn.execute("SELECT * FROM orders WHERE id = ?", (order["id"],)).fetchone()
        checkout = self.fake.sessions[order["stripe_session_id"]]
        self.assertIn("obn", checkout["metadata"])
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute("DELETE FROM order_events WHERE order_id = ?", (order["id"],))
        self.conn.execute("DELETE FROM notifications WHERE order_id = ?", (order["id"],))
        self.conn.execute("DELETE FROM orders WHERE id = ?", (order["id"],))
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.assertIsNone(self.conn.execute("SELECT 1 FROM orders WHERE public_ref = ?", (order["public_ref"],)).fetchone())
        restored = ensure_order_from_checkout(self.conn, checkout, claim_session_id="sid-new")
        self.assertIsNotNone(restored)
        self.assertEqual(restored["public_ref"], order["public_ref"])
        self.assertEqual(restored["total_cents"], order["total_cents"])
        self.assertEqual(restored["session_id"], "sid-new")
        checkout["payment_status"] = "paid"
        checkout["status"] = "complete"
        payload = self.event(
            restored,
            "checkout.session.completed",
            event_id="evt_recover",
            metadata=checkout["metadata"],
        )
        self.conn.execute("PRAGMA foreign_keys = OFF")
        self.conn.execute("DELETE FROM order_events")
        self.conn.execute("DELETE FROM notifications")
        self.conn.execute("DELETE FROM orders")
        self.conn.execute("PRAGMA foreign_keys = ON")
        status, body = handle_webhook(self.conn, payload, sign(payload))
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        paid = self.conn.execute(
            "SELECT payment_status, total_cents FROM orders WHERE public_ref = ?",
            (order["public_ref"],),
        ).fetchone()
        self.assertEqual(paid["payment_status"], "paid")
        self.assertEqual(paid["total_cents"], order["total_cents"])
