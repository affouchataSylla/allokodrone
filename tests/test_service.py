import os
import tempfile
import unittest
from datetime import datetime

from app.auth import create_session
from app.cart import add_item
from app.catalog import product_by_slug
from app.db import init_db
from app.orders import dashboard_stats, mark_collected, orders_sheet, place_order, set_status, slot_board
from app.schedule import PARIS
from app.seed import seed

TUESDAY_NOON = datetime(2026, 10, 20, 12, 30, tzinfo=PARIS)


class ServiceBoardTests(unittest.TestCase):
    def setUp(self):
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
            "INSERT INTO payment_methods (code, label, active) VALUES ('pay_on_delivery', 'A la livraison', 1)"
        )
        self.conn.execute(
            "INSERT INTO delivery_zones (name, fee_cents, fee_confirmed, active) VALUES ('NOISY', 0, 1, 1)"
        )
        self.zone = self.conn.execute("SELECT id FROM delivery_zones").fetchone()["id"]
        self.conn.execute(
            "UPDATE products SET price_cents = 450, price_confirmed = 1 WHERE slug = 'alloko'"
        )

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def order(self, method="pay_on_delivery"):
        product = product_by_slug(self.conn, "alloko")
        add_item(self.conn, self.sid, product["id"], [], 1)
        pickup = method == "stripe"
        order, errors = place_order(
            self.conn,
            self.sid,
            None,
            {
                "idempotency_key": "service-" + method,
                "nom": "Awa Diallo",
                "email": "awa@example.com",
                "telephone": "0612345678",
                "mode": "pickup" if pickup else "delivery",
                "slot_id": str(self.slot),
                "zone_id": str(self.zone),
                "rue": "10 rue des Lilas",
                "code_postal": "93130",
                "ville": "Noisy-le-Sec",
                "paiement": method,
            },
            clock=TUESDAY_NOON,
        )
        self.assertEqual(errors, [])
        return order

    def test_open_board_lists_the_order_until_it_is_finished(self):
        order = self.order()
        refs = [row["public_ref"] for row in orders_sheet(self.conn, only_open=True)]
        self.assertEqual(refs, [order["public_ref"]])
        self.assertIsNone(set_status(self.conn, order["id"], "preparing"))
        self.assertIsNone(set_status(self.conn, order["id"], "completed"))
        self.assertEqual(list(orders_sheet(self.conn, only_open=True)), [])

    def test_kitchen_status_rejects_a_payment_label(self):
        order = self.order()
        self.assertEqual(set_status(self.conn, order["id"], "paid"), "Statut inconnu.")
        row = self.conn.execute("SELECT status, payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["status"], "received")
        self.assertEqual(row["payment_status"], "unpaid")

    def test_counter_collection_is_recorded_without_a_provider(self):
        order = self.order()
        self.assertIsNone(mark_collected(self.conn, order["id"]))
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "paid")
        self.assertIsNone(mark_collected(self.conn, order["id"]))
        count = self.conn.execute(
            "SELECT COUNT(*) AS n FROM order_events WHERE order_id = ? AND status = 'paid'",
            (order["id"],),
        ).fetchone()["n"]
        self.assertEqual(count, 1)

    def test_online_payment_cannot_be_marked_collected_here(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fixture_not_a_real_key"
        try:
            order = self.order(method="stripe")
        finally:
            os.environ.pop("STRIPE_SECRET_KEY", None)
        error = mark_collected(self.conn, order["id"])
        self.assertIn("Stripe", error)
        row = self.conn.execute("SELECT payment_status FROM orders WHERE id = ?", (order["id"],)).fetchone()
        self.assertEqual(row["payment_status"], "pending")

    def test_dashboard_counts_real_orders_only(self):
        order = self.order()
        self.conn.execute(
            "UPDATE orders SET created_at = ? WHERE id = ?",
            ("2026-10-20T10:00:00+00:00", order["id"]),
        )
        stats = dashboard_stats(self.conn, clock=TUESDAY_NOON)
        self.assertEqual(stats["day"], "2026-10-20")
        self.assertEqual(stats["today"], 1)
        self.assertEqual(stats["open"], 1)
        self.assertEqual(stats["pickup"], 0)
        self.assertEqual(stats["delivery"], 1)
        self.assertEqual(stats["due_cents"], 450)
        self.assertEqual(stats["collected_cents"], 0)
        self.assertEqual(stats["slots_today"], 1)
        self.assertIsNone(mark_collected(self.conn, order["id"]))
        paid = dashboard_stats(self.conn, clock=TUESDAY_NOON)
        self.assertEqual(paid["collected_cents"], 450)
        self.assertEqual(paid["due_cents"], 0)
        self.assertIsNone(set_status(self.conn, order["id"], "cancelled"))
        gone = dashboard_stats(self.conn, clock=TUESDAY_NOON)
        self.assertEqual(gone["collected_cents"], 0)
        self.assertEqual(gone["due_cents"], 0)
        self.assertEqual(gone["counts"]["cancelled"], 1)
        self.assertEqual(gone["open"], 0)

    def test_slot_board_counts_only_active_bookings(self):
        os.environ["STRIPE_SECRET_KEY"] = "sk_test_fixture_not_a_real_key"
        try:
            order = self.order(method="stripe")
        finally:
            os.environ.pop("STRIPE_SECRET_KEY", None)
        board = slot_board(self.conn, "2026-10-20")
        self.assertEqual(len(board), 1)
        self.assertEqual(board[0]["used"], 1)
        self.assertEqual(board[0]["remaining"], 3)
        self.assertEqual(board[0]["orders"][0]["public_ref"], order["public_ref"])
        self.assertIsNone(set_status(self.conn, order["id"], "cancelled"))
        after = slot_board(self.conn, "2026-10-20")
        self.assertEqual(after[0]["used"], 0)
        self.assertEqual(after[0]["remaining"], 4)

    def test_empty_database_gets_default_capacity_slots(self):
        from app.orders import ensure_upcoming_slots, open_slots

        empty = init_db(os.path.join(self.tmp.name, "empty.db"))
        seed(empty)
        created = ensure_upcoming_slots(empty, days=1, clock=TUESDAY_NOON)
        self.assertGreater(created, 0)
        self.assertGreater(len(open_slots(empty, clock=TUESDAY_NOON)), 0)
        capacity = empty.execute("SELECT MIN(capacity) AS capacity FROM pickup_slots").fetchone()["capacity"]
        self.assertEqual(capacity, 4)
        empty.close()

    def test_missing_days_are_opened_from_published_hours(self):
        from app.orders import ensure_upcoming_slots

        created = ensure_upcoming_slots(self.conn, days=2, clock=TUESDAY_NOON)
        self.assertEqual(created, 22)
        same_day = self.conn.execute(
            "SELECT COUNT(*) AS n FROM pickup_slots WHERE slot_date = '2026-10-20'"
        ).fetchone()["n"]
        next_day = self.conn.execute(
            """
            SELECT COUNT(*) AS n, MIN(capacity) AS capacity, MIN(start_time) AS start_time
            FROM pickup_slots WHERE slot_date = '2026-10-21'
            """
        ).fetchone()
        self.assertEqual(same_day, 1)
        self.assertEqual(next_day["n"], 22)
        self.assertEqual(next_day["capacity"], 4)
        self.assertEqual(next_day["start_time"], "11:30")
        self.assertEqual(ensure_upcoming_slots(self.conn, days=2, clock=TUESDAY_NOON), 0)
