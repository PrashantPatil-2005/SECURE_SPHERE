"""
Shared PostgreSQL helpers used across the SecuriSphere backend.

Centralises connection bootstrap + a handful of read-only aggregation
queries that were previously duplicated between `backend/api/app.py`,
`backend/engine/kill_chain/reconstructor.py`, and other call sites.

All callers must `conn.close()` themselves when using `pg_connect()`.
The higher-level helpers (`avg_mttd_seconds`) handle their own lifecycle.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger("SecuriSphere.PgHelpers")


def pg_connect():
    """
    Open a new PostgreSQL connection using DATABASE_URL or the discrete
    POSTGRES_* env vars. Caller is responsible for closing the connection.
    """
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


def avg_mttd_seconds() -> Optional[float]:
    """
    Pull AVG(mttd_seconds) from the kill_chains table, rounded to 3 dp.
    Returns None if the table is empty, the connection fails, or the
    aggregation produces NULL.
    """
    try:
        conn = pg_connect()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT AVG(mttd_seconds) FROM kill_chains "
                "WHERE mttd_seconds IS NOT NULL"
            )
            row = cur.fetchone()
        conn.close()
        if row and row[0] is not None:
            return round(float(row[0]), 3)
    except Exception as exc:
        logger.debug("avg_mttd_seconds postgres lookup failed: %s", exc)
    return None
