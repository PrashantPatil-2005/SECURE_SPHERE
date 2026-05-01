"""
audit.py — System-wide append-only audit log.

Records every security-significant action across SecuriSphere:
  • automated:  engine fired a rule, kill chain created
  • user:       login, logout, incident triage, settings change
  • system:     bootstrap, schema migrations

The helper is intentionally synchronous (no queue) and silent-fail —
a logging error must never crash the engine or break a user request.
The audit_log table is created by scripts/init_db.sql or
scripts/migrations/001_audit_log.sql; this module also runs an
idempotent CREATE on first call to support fresh databases.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Optional

import psycopg2
from psycopg2.extras import Json, RealDictCursor

logger = logging.getLogger("SecuriSphere.audit")

VALID_ACTOR_TYPES = ("system", "user", "engine")
VALID_SEVERITIES  = ("info", "warning", "critical")

_schema_ready = False
_schema_lock  = threading.Lock()


def _get_conn():
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def _ensure_schema() -> None:
    """Create the audit_log table if missing. Runs once per process."""
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if _schema_ready:
            return
        try:
            conn = _get_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS audit_log (
                            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            timestamp   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                            actor       VARCHAR(120) NOT NULL,
                            actor_type  VARCHAR(20)  NOT NULL,
                            action      VARCHAR(80)  NOT NULL,
                            target_type VARCHAR(40),
                            target_id   VARCHAR(120),
                            detail      JSONB        NOT NULL DEFAULT '{}'::jsonb,
                            severity    VARCHAR(20)  NOT NULL DEFAULT 'info',
                            source_ip   VARCHAR(45)
                        )
                    """)
                    cur.execute("CREATE INDEX IF NOT EXISTS audit_log_timestamp_idx ON audit_log(timestamp DESC)")
                    cur.execute("CREATE INDEX IF NOT EXISTS audit_log_action_idx    ON audit_log(action)")
                    cur.execute("CREATE INDEX IF NOT EXISTS audit_log_actor_idx     ON audit_log(actor)")
                    cur.execute("CREATE INDEX IF NOT EXISTS audit_log_severity_idx  ON audit_log(severity)")
            conn.close()
            _schema_ready = True
        except Exception as exc:
            logger.warning("audit_log schema ensure failed: %s", exc)


def log_audit(
    action: str,
    actor: str = "system",
    actor_type: str = "system",
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    detail: Optional[dict] = None,
    severity: str = "info",
    source_ip: Optional[str] = None,
) -> None:
    """Insert an audit log entry. Silent-fail by contract."""
    if not action:
        return
    if actor_type not in VALID_ACTOR_TYPES:
        actor_type = "system"
    if severity not in VALID_SEVERITIES:
        severity = "info"

    _ensure_schema()
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_log
                        (actor, actor_type, action, target_type, target_id,
                         detail, severity, source_ip)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(actor)[:120],
                        actor_type,
                        str(action)[:80],
                        (str(target_type)[:40] if target_type else None),
                        (str(target_id)[:120] if target_id else None),
                        Json(detail or {}),
                        severity,
                        source_ip,
                    ),
                )
        conn.close()
    except Exception as exc:
        logger.debug("audit log write skipped (%s): %s", action, exc)


def query_audit(
    actor: Optional[str] = None,
    action_prefix: Optional[str] = None,
    severity: Optional[str] = None,
    start: Optional[str] = None,   # ISO datetime
    end: Optional[str] = None,     # ISO datetime
    limit: int = 100,
) -> dict:
    """Return a {total, logs} dict for the audit-logs API endpoint.
    Raises on DB failure — the route handler decides how to respond."""
    limit = max(1, min(int(limit or 100), 500))
    where: list = []
    params: list = []
    if actor:
        where.append("actor = %s")
        params.append(actor)
    if action_prefix:
        where.append("action LIKE %s")
        params.append(action_prefix.rstrip("%") + "%")
    if severity:
        where.append("severity = %s")
        params.append(severity)
    if start:
        where.append("timestamp >= %s")
        params.append(start)
    if end:
        where.append("timestamp <= %s")
        params.append(end)
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    _ensure_schema()
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(f"SELECT COUNT(*) AS n FROM audit_log {where_sql}", tuple(params))
            total = int(cur.fetchone()["n"])
            cur.execute(
                f"SELECT id, timestamp, actor, actor_type, action, target_type, "
                f"target_id, detail, severity, source_ip "
                f"FROM audit_log {where_sql} ORDER BY timestamp DESC LIMIT %s",
                tuple(params) + (limit,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    logs = []
    for r in rows:
        ts = r.get("timestamp")
        logs.append({
            "id":          str(r.get("id")),
            "timestamp":   ts.isoformat() if hasattr(ts, "isoformat") else ts,
            "actor":       r.get("actor"),
            "actor_type":  r.get("actor_type"),
            "action":      r.get("action"),
            "target_type": r.get("target_type"),
            "target_id":   r.get("target_id"),
            "detail":      r.get("detail") or {},
            "severity":    r.get("severity"),
            "source_ip":   r.get("source_ip"),
        })
    return {"total": total, "logs": logs}
