import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def remote_database_url():
    return (
        os.environ.get("TURSO_DATABASE_URL")
        or os.environ.get("LIBSQL_URL")
        or ""
    ).strip()


def remote_auth_token():
    return (
        os.environ.get("TURSO_AUTH_TOKEN")
        or os.environ.get("LIBSQL_AUTH_TOKEN")
        or ""
    ).strip()


def uses_remote_db():
    return bool(remote_database_url())

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY,
  email TEXT NOT NULL UNIQUE COLLATE NOCASE,
  password_hash TEXT NOT NULL,
  name TEXT NOT NULL,
  phone TEXT,
  role TEXT NOT NULL CHECK(role IN ('customer', 'admin', 'driver')),
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  user_id INTEGER REFERENCES users(id),
  csrf TEXT NOT NULL,
  flash TEXT,
  idempotency_key TEXT,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY,
  category_id INTEGER NOT NULL REFERENCES categories(id),
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  description TEXT NOT NULL,
  image TEXT,
  price_cents INTEGER,
  price_confirmed INTEGER NOT NULL DEFAULT 0,
  available INTEGER NOT NULL DEFAULT 1,
  orderable INTEGER NOT NULL DEFAULT 1,
  block_reason TEXT,
  service_window TEXT,
  featured INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS option_groups (
  id INTEGER PRIMARY KEY,
  product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  required INTEGER NOT NULL DEFAULT 1,
  min_select INTEGER NOT NULL DEFAULT 1,
  max_select INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS option_choices (
  id INTEGER PRIMARY KEY,
  group_id INTEGER NOT NULL REFERENCES option_groups(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  price_delta_cents INTEGER,
  price_delta_confirmed INTEGER NOT NULL DEFAULT 0,
  available INTEGER NOT NULL DEFAULT 1,
  sort_order INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS carts (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
  promo_code TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS cart_items (
  id INTEGER PRIMARY KEY,
  cart_id INTEGER NOT NULL REFERENCES carts(id) ON DELETE CASCADE,
  product_id INTEGER NOT NULL REFERENCES products(id),
  quantity INTEGER NOT NULL CHECK(quantity > 0 AND quantity <= 20),
  notes TEXT NOT NULL DEFAULT '',
  line_key TEXT NOT NULL,
  UNIQUE(cart_id, line_key)
);

CREATE TABLE IF NOT EXISTS cart_item_choices (
  item_id INTEGER NOT NULL REFERENCES cart_items(id) ON DELETE CASCADE,
  choice_id INTEGER NOT NULL REFERENCES option_choices(id),
  PRIMARY KEY(item_id, choice_id)
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pickup_points (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  address TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS delivery_zones (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  fee_cents INTEGER,
  fee_confirmed INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 0,
  notice TEXT
);

CREATE TABLE IF NOT EXISTS pickup_slots (
  id INTEGER PRIMARY KEY,
  slot_date TEXT NOT NULL,
  start_time TEXT NOT NULL,
  end_time TEXT NOT NULL,
  capacity INTEGER NOT NULL CHECK(capacity > 0),
  active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS payment_methods (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE,
  label TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS promotions (
  id INTEGER PRIMARY KEY,
  code TEXT NOT NULL UNIQUE COLLATE NOCASE,
  label TEXT NOT NULL,
  kind TEXT NOT NULL CHECK(kind IN ('amount', 'percent')),
  amount_cents INTEGER,
  percent INTEGER,
  active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY,
  public_ref TEXT NOT NULL UNIQUE,
  user_id INTEGER REFERENCES users(id),
  session_id TEXT,
  status TEXT NOT NULL,
  mode TEXT NOT NULL,
  customer_name TEXT NOT NULL,
  email TEXT NOT NULL,
  phone TEXT NOT NULL,
  address_json TEXT,
  pickup_point_id INTEGER REFERENCES pickup_points(id),
  slot_id INTEGER REFERENCES pickup_slots(id),
  zone_id INTEGER REFERENCES delivery_zones(id),
  payment_method TEXT NOT NULL,
  payment_status TEXT NOT NULL DEFAULT 'unpaid',
  subtotal_cents INTEGER NOT NULL,
  delivery_fee_cents INTEGER NOT NULL,
  discount_cents INTEGER NOT NULL,
  total_cents INTEGER NOT NULL,
  promo_code TEXT,
  idempotency_key TEXT NOT NULL UNIQUE,
  snapshot_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  stripe_session_id TEXT,
  stripe_payment_intent TEXT
);

CREATE TABLE IF NOT EXISTS stripe_events (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_events (
  id INTEGER PRIMARY KEY,
  order_id INTEGER NOT NULL REFERENCES orders(id),
  status TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_slot ON orders(slot_id);

CREATE TABLE IF NOT EXISTS kitchen_lines (
  order_id INTEGER NOT NULL REFERENCES orders(id),
  line_index INTEGER NOT NULL,
  done INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (order_id, line_index)
);

CREATE TABLE IF NOT EXISTS distance_bands (
  id INTEGER PRIMARY KEY,
  max_meters INTEGER NOT NULL,
  fee_cents INTEGER,
  fee_confirmed INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS guest_reviews (
  id INTEGER PRIMARY KEY,
  session_id TEXT,
  author TEXT NOT NULL,
  stars INTEGER NOT NULL,
  body TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
  id INTEGER PRIMARY KEY,
  order_id INTEGER REFERENCES orders(id),
  event TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL,
  detail TEXT,
  created_at TEXT NOT NULL,
  seen INTEGER NOT NULL DEFAULT 0
);
"""


def connect(path=None):
    url = remote_database_url()
    if url:
        import turso_serverless

        conn = turso_serverless.connect(
            url,
            auth_token=remote_auth_token() or None,
            isolation_level=None,
        )
        conn.row_factory = turso_serverless.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass
        return conn

    db_path = path or str(ROOT / "data" / "allokodrone.db")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _ensure_driver_role(conn):
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'").fetchone()
    if not sql or not sql[0] or "'driver'" in sql[0]:
        return
    conn.executescript(
        """
        PRAGMA foreign_keys = OFF;
        BEGIN;
        CREATE TABLE users_new (
          id INTEGER PRIMARY KEY,
          email TEXT NOT NULL UNIQUE COLLATE NOCASE,
          password_hash TEXT NOT NULL,
          name TEXT NOT NULL,
          phone TEXT,
          role TEXT NOT NULL CHECK(role IN ('customer', 'admin', 'driver')),
          created_at TEXT NOT NULL
        );
        INSERT INTO users_new (id, email, password_hash, name, phone, role, created_at)
        SELECT id, email, password_hash, name, phone, role, created_at FROM users;
        DROP TABLE users;
        ALTER TABLE users_new RENAME TO users;
        COMMIT;
        PRAGMA foreign_keys = ON;
        """
    )


def init_db(path=None):
    conn = connect(path)
    conn.executescript(SCHEMA)
    _ensure_driver_role(conn)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if "stripe_session_id" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN stripe_session_id TEXT")
    if "stripe_payment_intent" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN stripe_payment_intent TEXT")
    for name, kind in (
        ("distance_meters", "INTEGER"),
        ("uber_delivery_id", "TEXT"),
        ("uber_status", "TEXT"),
        ("uber_tracking_url", "TEXT"),
        ("driver_name", "TEXT"),
        ("driver_phone", "TEXT"),
        ("driver_accepted_at", "TEXT"),
    ):
        if name not in columns:
            conn.execute(f"ALTER TABLE orders ADD COLUMN {name} {kind}")
    note_columns = {row[1] for row in conn.execute("PRAGMA table_info(notifications)")}
    if "seen" not in note_columns:
        conn.execute("ALTER TABLE notifications ADD COLUMN seen INTEGER NOT NULL DEFAULT 0")
    columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)")}
    if "kitchen_issue" not in columns:
        conn.execute("ALTER TABLE orders ADD COLUMN kitchen_issue TEXT")
    from app.reviews import ensure_review_tables

    ensure_review_tables(conn)
    return conn
