"""
register_site.py — SecuriSphere Browser Monitor: Site Registration

Provides a Flask Blueprint that exposes POST /api/register-site. Websites
that want to embed the ShopSphere browser agent must first register here
to obtain a deterministic ``site_id`` (first 8 chars of sha256(url+name)).

This module is imported by ``browser_monitor.py`` and its ``bp`` is
registered onto the main Flask app. It also exposes ``init_db()`` which
creates the ``registered_sites`` table idempotently on startup.
"""

import os
import re
import hashlib
import logging

import psycopg2
from flask import Blueprint, request, jsonify

logger = logging.getLogger("BrowserMonitor.register_site")

bp = Blueprint("register_site", __name__)

# ── config ─────────────────────────────────────────────────────────────────

POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "database")
POSTGRES_PORT     = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_USER     = os.getenv("POSTGRES_USER", "securisphere")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "securisphere")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "securisphere")

AGENT_URL = os.getenv("BROWSER_AGENT_URL", "/static/agent.js")

URL_RE   = re.compile(r"^https?://[^\s/$.?#][^\s]*$", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE TABLE IF NOT EXISTS registered_sites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    email       TEXT NOT NULL,
    site_id     TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_registered_sites_site_id ON registered_sites(site_id);
"""


def _conn():
    """Open a fresh psycopg2 connection to the SecuriSphere PostgreSQL DB."""
    return psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
        dbname=POSTGRES_DB,
    )


def init_db() -> None:
    """Create the registered_sites table (idempotent). Safe to call on
    every monitor startup — uses CREATE ... IF NOT EXISTS."""
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(SCHEMA_SQL)
        conn.commit()
    logger.info("registered_sites schema ready")


def _compute_site_id(url: str, name: str) -> str:
    """Deterministic site identifier: first 8 hex chars of sha256(url+name)."""
    return hashlib.sha256(f"{url}{name}".encode("utf-8")).hexdigest()[:8]


def _snippet(site_id: str) -> str:
    """Return a ready-to-paste <script> snippet that wires up the browser
    agent for a registered site."""
    return (
        f'<script>window.__SECURISPHERE_SITE_ID__ = "{site_id}";</script>'
        f'<script src="{AGENT_URL}" async></script>'
    )


@bp.route("/api/register-site", methods=["POST", "OPTIONS"])
def register_site():
    """Register a new monitored site and return an embeddable snippet.

    Request body (JSON):
        name  (str)  — at least 3 characters
        url   (str)  — must match ``^https?://...``
        email (str)  — simple ``x@y.z`` regex check

    Response (JSON):
        { site_id, name, url, snippet }
    """
    if request.method == "OPTIONS":
        return ("", 204)

    data = request.get_json(silent=True) or {}
    name  = (data.get("name")  or "").strip()
    url   = (data.get("url")   or "").strip()
    email = (data.get("email") or "").strip()

    if len(name) < 3:
        return jsonify({"error": "name must be at least 3 characters"}), 400
    if not URL_RE.match(url):
        return jsonify({"error": "invalid url"}), 400
    if not EMAIL_RE.match(email):
        return jsonify({"error": "invalid email"}), 400

    site_id = _compute_site_id(url, name)

    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO registered_sites (name, url, email, site_id)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (site_id) DO UPDATE
                  SET name  = EXCLUDED.name,
                      email = EXCLUDED.email
                RETURNING site_id
                """,
                (name, url, email, site_id),
            )
            site_id = cur.fetchone()[0]
            conn.commit()
    except Exception as e:
        logger.error(f"registration db error: {e}")
        return jsonify({"error": f"database error: {e}"}), 500

    return jsonify({
        "site_id": site_id,
        "name":    name,
        "url":     url,
        "snippet": _snippet(site_id),
    })
