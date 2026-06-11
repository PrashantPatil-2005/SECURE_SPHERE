"""Read-only PostgreSQL helpers for experiment metric extraction."""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any

import psycopg2
import psycopg2.extras


def _dsn() -> str | None:
    """Build a connection string from env vars."""
    url = os.getenv("DATABASE_URL")
    if url:
        return url
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "securisphere_db")
    user = os.getenv("POSTGRES_USER", "securisphere_user")
    password = os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024")
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"


def _connect():
    """Open a PostgreSQL connection."""
    dsn = _dsn()
    if dsn and dsn.startswith("postgresql://"):
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def _parse_steps(raw: Any) -> list[dict]:
    """Normalize kill-chain steps from JSONB."""
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if isinstance(raw, list):
        return [s for s in raw if isinstance(s, dict)]
    return []


def fetch_kill_chains_since(
    since: datetime,
    *,
    scenario_label: str | None = None,
) -> list[dict[str, Any]]:
    """Return kill-chain rows created at or after *since*.

    Args:
        since: Lower bound on ``detected_at`` (naive or aware).
        scenario_label: Optional filter on ``scenario_label`` column.

    Returns:
        List of dicts with incident_id, steps, mttd_seconds, service_path, etc.
    """
    query = """
        SELECT incident_id, incident_type, steps, service_path,
               mttd_seconds, first_event_at, detected_at, severity,
               correlation_key, source_service_name, scenario_label
        FROM kill_chains
        WHERE detected_at >= %s
    """
    params: list[Any] = [since]
    if scenario_label:
        query += " AND scenario_label = %s"
        params.append(scenario_label)
    query += " ORDER BY detected_at ASC"

    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(query, params)
            rows = [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()

    for row in rows:
        row["kill_chain_steps"] = _parse_steps(row.pop("steps", None))
    return rows


def fetch_latest_kill_chain(
    *,
    incident_id: str | None = None,
) -> dict[str, Any] | None:
    """Fetch the most recent kill chain, optionally by incident_id.

    Args:
        incident_id: If set, return that specific chain.

    Returns:
        Kill-chain dict or None.
    """
    conn = _connect()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if incident_id:
                cur.execute(
                    """
                    SELECT incident_id, incident_type, steps, service_path,
                           mttd_seconds, first_event_at, detected_at
                    FROM kill_chains WHERE incident_id = %s LIMIT 1
                    """,
                    (incident_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT incident_id, incident_type, steps, service_path,
                           mttd_seconds, first_event_at, detected_at
                    FROM kill_chains
                    ORDER BY detected_at DESC LIMIT 1
                    """
                )
            row = cur.fetchone()
    finally:
        conn.close()

    if not row:
        return None
    out = dict(row)
    out["kill_chain_steps"] = _parse_steps(out.pop("steps", None))
    return out


def merge_kill_chain_steps(chains: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Union steps from multiple kill chains (chronological, deduped by event_id).

    Args:
        chains: Rows from :func:`fetch_kill_chains_since`.

    Returns:
        Combined step list sorted by timestamp.
    """
    seen_ids: set[str] = set()
    merged: list[dict[str, Any]] = []
    for chain in chains:
        for step in chain.get("kill_chain_steps") or []:
            eid = step.get("event_id")
            if eid and eid in seen_ids:
                continue
            if eid:
                seen_ids.add(eid)
            merged.append(step)

    def _sort_key(s: dict) -> str:
        return str(s.get("timestamp") or "")

    merged.sort(key=_sort_key)
    return merged
