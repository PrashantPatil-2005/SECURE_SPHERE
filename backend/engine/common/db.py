"""Shared PostgreSQL connection helper.

Replaces the duplicated nested-ternary `_get_conn` blocks scattered through
correlation_engine, reconstructor, topology_collector, and the backend API.

Why centralize: each previous copy had the bug
  ``psycopg2.connect(URL) if URL else psycopg2.connect(URL) if URL else psycopg2.connect(host=...)``
which evaluates correctly only by accident. One canonical helper avoids drift.
"""

import os
import logging
from contextlib import contextmanager

logger = logging.getLogger("securisphere.db")


def _connect():
    """Open a PostgreSQL connection. DATABASE_URL takes precedence; otherwise
    falls back to POSTGRES_HOST/PORT/DB/USER/PASSWORD. Lazily imports
    psycopg2 so modules can import this helper even when the driver is
    not installed (tests, CLI tools)."""
    import psycopg2
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def get_conn():
    """Return a raw psycopg2 connection (caller is responsible for close)."""
    return _connect()


@contextmanager
def conn_ctx():
    """Context-manager variant: auto-commits on success, rolls back on error,
    closes either way. Prefer this over raw get_conn for new code."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        try:
            conn.close()
        except Exception:
            pass
