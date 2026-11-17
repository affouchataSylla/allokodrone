"""Vercel serverless entry — proxie /api et /admin vers le serveur Python."""

from __future__ import annotations

import os
import sys
from http.server import BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.server import handle_http, prepare  # noqa: E402


def _db_path() -> str | None:
    from app.db import uses_remote_db

    if uses_remote_db():
        return None
    if os.environ.get("VERCEL"):
        # Sans Turso : SQLite /tmp est éphémère et non partagé entre instances.
        return "/tmp/allokodrone.db"
    return os.environ.get("ALLOKO_DB", str(ROOT / "data" / "allokodrone.db"))


def _target_from_request(raw_path: str) -> str:
    parsed = urlparse(raw_path)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)
    orig = None
    rest: list[tuple[str, str]] = []
    for key, value in pairs:
        if key == "__p" and orig is None:
            orig = value
        else:
            rest.append((key, value))
    if not orig:
        return raw_path
    query = urlencode(rest)
    return f"{orig}?{query}" if query else orig


class handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self._serve("GET")

    def do_POST(self):  # noqa: N802
        self._serve("POST")

    def do_OPTIONS(self):  # noqa: N802
        self._serve("OPTIONS")

    def do_PATCH(self):  # noqa: N802
        self._serve("PATCH")

    def do_DELETE(self):  # noqa: N802
        self._serve("DELETE")

    def _serve(self, method: str) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else b""
        target = _target_from_request(self.path)
        headers = {key.lower(): value for key, value in self.headers.items()}
        conn = prepare(_db_path())
        try:
            response = handle_http(conn, method, target, headers, body)
        finally:
            conn.close()

        self.send_response(response.status)
        self.send_header("Content-Type", response.content_type)
        self.send_header("X-Content-Type-Options", "nosniff")
        for key, value in response.headers:
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(response.body)))
        self.end_headers()
        self.wfile.write(response.body)

    def log_message(self, format, *args):  # noqa: A003
        return
