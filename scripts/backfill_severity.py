"""
backfill_severity.py — One-shot backfill of severity on incident tables.

Walks `correlated_incidents` and `kill_chains` for rows with a NULL or
empty severity and recomputes the label using the canonical resolver.

Usage:
    DATABASE_URL=postgres://… python scripts/backfill_severity.py
or:
    make backfill-severity

The script is idempotent: re-running it only touches rows that still
need a label.
"""
from __future__ import annotations

import os
import sys
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "engine"))

from severity import resolve_incident_severity  # noqa: E402

import psycopg2  # noqa: E402
from psycopg2.extras import RealDictCursor  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("backfill_severity")


def get_conn():
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def _step_count(row: dict) -> int:
    """Best-effort step count from JSONB columns we know about."""
    steps = row.get("steps")
    if isinstance(steps, list):
        return len(steps)
    events = row.get("correlated_event_ids")
    if isinstance(events, list):
        return len(events)
    return 0


def backfill_correlated_incidents(conn) -> int:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT incident_id, risk_score_at_time, mitre_techniques, correlated_event_ids "
            "FROM correlated_incidents WHERE severity IS NULL OR severity = ''"
        )
        rows = cur.fetchall()

    updated = 0
    with conn.cursor() as cur:
        for r in rows:
            sev = resolve_incident_severity(
                risk_score=r.get("risk_score_at_time") or 0,
                step_count=_step_count(r),
                technique_ids=r.get("mitre_techniques") or [],
            )
            cur.execute(
                "UPDATE correlated_incidents SET severity = %s WHERE incident_id = %s",
                (sev, r["incident_id"]),
            )
            updated += 1
    return updated


def backfill_kill_chains(conn) -> int:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT incident_id, steps, mitre_techniques "
            "FROM kill_chains WHERE severity IS NULL OR severity = ''"
        )
        rows = cur.fetchall()

    updated = 0
    with conn.cursor() as cur:
        for r in rows:
            steps = _step_count(r)
            sev = resolve_incident_severity(
                # No risk score on kill_chains directly — fall back to
                # step-count heuristic (>=2 → high) handled by the resolver.
                risk_score=0,
                step_count=steps,
                technique_ids=r.get("mitre_techniques") or [],
            )
            cur.execute(
                "UPDATE kill_chains SET severity = %s WHERE incident_id = %s",
                (sev, r["incident_id"]),
            )
            updated += 1
    return updated


def main() -> int:
    try:
        conn = get_conn()
    except Exception as exc:
        logger.error("Failed to connect to PostgreSQL: %s", exc)
        return 1

    try:
        with conn:
            ci = backfill_correlated_incidents(conn)
            kc = backfill_kill_chains(conn)
        logger.info("Backfill complete — correlated_incidents=%d kill_chains=%d", ci, kc)
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
