import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

PBKDF2_ROUNDS = 200_000


def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ROUNDS)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password, stored):
    try:
        salt_hex, digest_hex = stored.split(":", 1)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            PBKDF2_ROUNDS,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def utc_now():
    return datetime.now(timezone.utc)


def iso(moment):
    return moment.replace(microsecond=0).isoformat()


def create_session(conn, user_id=None):
    sid = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    now = utc_now()
    conn.execute(
        """
        INSERT INTO sessions (id, user_id, csrf, created_at, expires_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sid, user_id, csrf, iso(now), iso(now + timedelta(days=14))),
    )
    return sid


def get_session(conn, sid):
    if not sid:
        return None
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row:
        return None
    if row["expires_at"] < iso(utc_now()):
        conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))
        return None
    return row


def destroy_session(conn, sid):
    if sid:
        conn.execute("DELETE FROM sessions WHERE id = ?", (sid,))


def rotate_session(conn, old_sid, user_id):
    new_sid = create_session(conn, user_id)
    if old_sid:
        conn.execute(
            "UPDATE carts SET session_id = ? WHERE session_id = ?",
            (new_sid, old_sid),
        )
        conn.execute("DELETE FROM sessions WHERE id = ?", (old_sid,))
    return new_sid


def user_by_id(conn, user_id):
    if not user_id:
        return None
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


_admin_synced = set()


def ensure_admin(conn, email, password):
    if not email or not password:
        return None
    email = email.strip().lower()
    if len(password) < 10:
        raise ValueError("Le mot de passe administrateur doit contenir au moins 10 caracteres.")
    existing = conn.execute(
        "SELECT id, password_hash FROM users WHERE email = ? AND role = 'admin'",
        (email,),
    ).fetchone()
    if existing:
        # Aligne le hash sur les variables d'environnement (Vercel / prod)
        # une seule fois par process pour éviter le coût PBKDF2 à chaque requête.
        marker = f"{email}:{existing['id']}"
        if marker not in _admin_synced:
            if not verify_password(password, existing["password_hash"]):
                conn.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (hash_password(password), existing["id"]),
                )
            _admin_synced.add(marker)
        return existing["id"]
    now = iso(utc_now())
    cur = conn.execute(
        """
        INSERT INTO users (email, password_hash, name, phone, role, created_at)
        VALUES (?, ?, ?, ?, 'admin', ?)
        """,
        (email, hash_password(password), "Administration", "", now),
    )
    _admin_synced.add(f"{email}:{cur.lastrowid}")
    return cur.lastrowid


def create_staff(conn, email, password, name, phone="", role="driver"):
    email = (email or "").strip().lower()
    name = " ".join(str(name or "").split())[:80]
    phone = " ".join(str(phone or "").split())[:40]
    role = (role or "").strip().lower()
    if role not in ("admin", "driver"):
        return None, "Choisissez un rôle valide."
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 120:
        return None, "Adresse e-mail invalide."
    if len(password or "") < 10:
        return None, "Le mot de passe doit contenir au moins 10 caracteres."
    if len(name) < 2:
        return None, "Indiquez le nom."
    if phone and not _phone_ok(phone):
        return None, "Numero de telephone invalide."
    try:
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, phone, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (email, hash_password(password), name, phone, role, iso(utc_now())),
        )
    except Exception:
        return None, "Un compte existe deja avec cette adresse."
    return cur.lastrowid, None


def create_driver(conn, email, password, name, phone=""):
    return create_staff(conn, email, password, name, phone, role="driver")


def ensure_driver(conn, email, password, name="Livreur"):
    if not email or not password:
        return None
    existing = conn.execute(
        "SELECT id FROM users WHERE email = ? AND role = 'driver'",
        (email.strip().lower(),),
    ).fetchone()
    if existing:
        return existing["id"]
    user_id, error = create_driver(conn, email, password, name)
    if error:
        raise ValueError(error)
    return user_id


def register_customer(conn, email, password, name, phone):
    email = (email or "").strip().lower()
    name = (name or "").strip()
    phone = (phone or "").strip()
    if "@" not in email or "." not in email.split("@")[-1] or len(email) > 120:
        return None, "Adresse e-mail invalide."
    if len(password or "") < 10:
        return None, "Le mot de passe doit contenir au moins 10 caracteres."
    if len(name) < 2 or len(name) > 80:
        return None, "Indiquez votre nom."
    if phone and not _phone_ok(phone):
        return None, "Numero de telephone invalide."
    try:
        cur = conn.execute(
            """
            INSERT INTO users (email, password_hash, name, phone, role, created_at)
            VALUES (?, ?, ?, ?, 'customer', ?)
            """,
            (email, hash_password(password), name, phone, iso(utc_now())),
        )
    except Exception:
        return None, "Un compte existe deja avec cette adresse."
    return cur.lastrowid, None


def authenticate(conn, email, password):
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        ((email or "").strip().lower(),),
    ).fetchone()
    if not row or not verify_password(password or "", row["password_hash"]):
        return None
    return row


def _phone_ok(phone):
    digits = [char for char in phone if char.isdigit()]
    allowed = set("0123456789 +().-")
    return 8 <= len(digits) <= 15 and all(char in allowed for char in phone)


def set_flash(conn, sid, message):
    conn.execute("UPDATE sessions SET flash = ? WHERE id = ?", (message, sid))


def pop_flash(conn, sid):
    row = conn.execute("SELECT flash FROM sessions WHERE id = ?", (sid,)).fetchone()
    if not row or not row["flash"]:
        return ""
    conn.execute("UPDATE sessions SET flash = NULL WHERE id = ?", (sid,))
    return row["flash"]


def set_idempotency_key(conn, sid):
    key = secrets.token_urlsafe(18)
    conn.execute("UPDATE sessions SET idempotency_key = ? WHERE id = ?", (key, sid))
    return key
