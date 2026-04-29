"""
reconstructor.py — SecuriSphere Kill Chain Reconstructor

Accepts a list of correlated events (already grouped by incident_id from the
correlation engine) and reconstructs an ordered attack path:

    (service_name, event_type, timestamp, mitre_technique) …

The kill chain is persisted in the PostgreSQL ``kill_chains`` table so the
backend API can serve it for drill-down on the dashboard.

Key field additions on each incident
--------------------------------------
- ``first_event_at``   : timestamp of the earliest correlated event
- ``detected_at``      : timestamp when the incident was created
- ``mttd_seconds``     : detected_at − first_event_at  (float, seconds)
- ``service_path``     : ordered list of service names traversed
- ``kill_chain_steps`` : detailed step objects (stored in JSONB)
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

logger = logging.getLogger("KillChainReconstructor")

# ---------------------------------------------------------------------------
# PostgreSQL connection helper
# ---------------------------------------------------------------------------

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "database")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", 5432))
POSTGRES_DB   = os.getenv("POSTGRES_DB",   "securisphere_db")
POSTGRES_USER = os.getenv("POSTGRES_USER", "securisphere_user")
POSTGRES_PASS = os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024")


def _get_conn() -> psycopg2.extensions.connection:
    """Open a new PostgreSQL connection.  Callers must close it."""
    url = os.getenv("DATABASE_URL")
    if url:
        return psycopg2.connect(url)
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASS,
    )


def ensure_schema() -> None:
    """Create the kill_chains table if it does not yet exist."""
    ddl = """
    CREATE TABLE IF NOT EXISTS kill_chains (
        id               SERIAL PRIMARY KEY,
        incident_id      UUID   NOT NULL UNIQUE,
        incident_type    VARCHAR(80),
        source_ip        VARCHAR(45),
        steps            JSONB  NOT NULL DEFAULT '[]',
        service_path     TEXT[] NOT NULL DEFAULT '{}',
        first_service    VARCHAR(100),
        last_service     VARCHAR(100),
        mitre_techniques TEXT[] NOT NULL DEFAULT '{}',
        first_event_at   TIMESTAMP WITH TIME ZONE,
        detected_at      TIMESTAMP WITH TIME ZONE NOT NULL,
        duration_seconds FLOAT,
        mttd_seconds     FLOAT,
        severity         VARCHAR(20),
        created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_kc_incident_id  ON kill_chains(incident_id);
    CREATE INDEX IF NOT EXISTS idx_kc_source_ip    ON kill_chains(source_ip);
    CREATE INDEX IF NOT EXISTS idx_kc_detected_at  ON kill_chains(detected_at);
    """
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(ddl)
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS scenario_label VARCHAR(100);")
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS narrative TEXT;")
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active';")
                cur.execute("ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS analyst_note TEXT;")
        conn.close()
        logger.info("kill_chains schema ready")
    except Exception as exc:
        logger.error("Failed to ensure kill_chains schema: %s", exc)


# ---------------------------------------------------------------------------
# Core reconstruction logic
# ---------------------------------------------------------------------------


def _parse_ts(ts_str: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601 timestamp string, always returning a naive datetime
    so comparisons between event timestamps and incident timestamps
    (which may or may not carry timezone info) never fail."""
    if not ts_str:
        return None
    try:
        dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        # Strip tzinfo to avoid naive vs aware comparison errors
        return dt.replace(tzinfo=None)
    except ValueError:
        return None


def reconstruct(
    incident: Dict[str, Any],
    correlated_events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build an enriched incident dict that includes kill chain metadata.

    Parameters
    ----------
    incident:
        The incident dict as produced by ``CorrelationEngine.create_incident``.
    correlated_events:
        The raw event objects (not just IDs) that were correlated into this
        incident.  Must have ``timestamp`` and ``source_layer`` fields.

    Returns
    -------
    dict
        A copy of *incident* augmented with:
        ``first_event_at``, ``detected_at``, ``mttd_seconds``,
        ``service_path``, ``kill_chain_steps``.
    """
    if not correlated_events:
        return incident

    # -----------------------------------------------------------------------
    # 1. Sort events chronologically
    # -----------------------------------------------------------------------
    sorted_events = sorted(
        [e for e in correlated_events if e.get("timestamp")],
        key=lambda e: _parse_ts(e["timestamp"]) or datetime.min,
    )

    # -----------------------------------------------------------------------
    # 2. Extract ordered service path
    # -----------------------------------------------------------------------
    service_path: List[str] = []
    steps: List[Dict[str, Any]] = []

    for evt in sorted_events:
        # Prefer explicit service_name enrichment; fall back to source_layer
        svc = (
            evt.get("source_service_name")
            or evt.get("target_entity", {}).get("service")
            or evt.get("source_layer", "unknown")
        )
        if not service_path or service_path[-1] != svc:
            service_path.append(svc)

        steps.append(
            {
                "service_name": svc,
                "event_type":   evt.get("event_type", "unknown"),
                "event_id":     evt.get("event_id"),
                "timestamp":    evt.get("timestamp"),
                "severity":     evt.get("severity", {}).get("level", "low"),
                "mitre":        evt.get("mitre_technique"),
                "source_ip":    evt.get("source_entity", {}).get("ip"),
                "layer":        evt.get("source_layer"),
            }
        )

    # -----------------------------------------------------------------------
    # 3. MTTD calculation
    # -----------------------------------------------------------------------
    first_ts = _parse_ts(sorted_events[0]["timestamp"])
    detected_ts = _parse_ts(incident.get("timestamp"))

    mttd_seconds: Optional[float] = None
    if first_ts and detected_ts:
        delta = (detected_ts - first_ts).total_seconds()
        mttd_seconds = max(round(delta, 3), 0.0)

    # -----------------------------------------------------------------------
    # 4. Augment incident dict
    # -----------------------------------------------------------------------
    enriched = dict(incident)
    enriched["first_event_at"]   = sorted_events[0]["timestamp"] if sorted_events else None
    enriched["detected_at"]      = incident.get("timestamp")
    enriched["mttd_seconds"]     = mttd_seconds
    enriched["service_path"]     = service_path
    enriched["kill_chain_steps"] = steps
    enriched["first_service"]    = service_path[0]  if service_path else None
    enriched["last_service"]     = service_path[-1] if service_path else None

    return enriched


# ---------------------------------------------------------------------------
# PostgreSQL persistence
# ---------------------------------------------------------------------------


def persist(enriched_incident: Dict[str, Any]) -> None:
    """
    Upsert a kill chain record into PostgreSQL.

    Uses ``ON CONFLICT (incident_id) DO UPDATE`` so re-processing is safe.
    """
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO kill_chains (
                        incident_id, incident_type, source_ip,
                        steps, service_path, first_service, last_service,
                        mitre_techniques, first_event_at, detected_at,
                        duration_seconds, mttd_seconds, severity
                    ) VALUES (
                        %(incident_id)s, %(incident_type)s, %(source_ip)s,
                        %(steps)s, %(service_path)s, %(first_service)s, %(last_service)s,
                        %(mitre_techniques)s, %(first_event_at)s, %(detected_at)s,
                        %(duration_seconds)s, %(mttd_seconds)s, %(severity)s
                    )
                    ON CONFLICT (incident_id) DO UPDATE SET
                        steps            = EXCLUDED.steps,
                        service_path     = EXCLUDED.service_path,
                        first_event_at   = EXCLUDED.first_event_at,
                        mttd_seconds     = EXCLUDED.mttd_seconds
                    """,
                    {
                        "incident_id":      enriched_incident.get("incident_id"),
                        "incident_type":    enriched_incident.get("incident_type"),
                        "source_ip":        enriched_incident.get("source_ip"),
                        "steps":            json.dumps(enriched_incident.get("kill_chain_steps", [])),
                        "service_path":     enriched_incident.get("service_path", []),
                        "first_service":    enriched_incident.get("first_service"),
                        "last_service":     enriched_incident.get("last_service"),
                        "mitre_techniques": enriched_incident.get("mitre_techniques", []),
                        "first_event_at":   enriched_incident.get("first_event_at"),
                        "detected_at":      enriched_incident.get("detected_at") or enriched_incident.get("timestamp") or datetime.now().isoformat(),
                        "duration_seconds": enriched_incident.get("time_span_seconds"),
                        "mttd_seconds":     enriched_incident.get("mttd_seconds"),
                        "severity":         enriched_incident.get("severity"),
                    },
                )
        conn.close()
    except Exception as exc:
        logger.error("Failed to persist kill chain %s: %s",
                     enriched_incident.get("incident_id"), exc)


def tag_kill_chain(incident_id: str, scenario_label: str) -> bool:
    """
    Set the scenario_label for a kill chain row in PostgreSQL.
    Returns True on success, False on any failure.
    """
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE kill_chains SET scenario_label = %s WHERE incident_id = %s",
                    (scenario_label, incident_id),
                )
        conn.close()
        logger.info("Tagged kill chain %s as %s", incident_id, scenario_label)
        return True
    except Exception as exc:
        logger.warning("Failed to tag kill chain %s: %s", incident_id, exc)
        return False


def update_narrative(incident_id: str, narrative: str) -> bool:
    """
    Persist an AI-generated narrative onto an existing kill chain row.
    Returns True on success, False on any failure. Never raises.
    """
    try:
        conn = _get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE kill_chains SET narrative = %s WHERE incident_id = %s",
                    (narrative, incident_id),
                )
        conn.close()
        logger.info("Narrative saved for incident %s (%d chars)", incident_id, len(narrative or ""))
        return True
    except Exception as exc:
        logger.warning("Failed to save narrative for %s: %s", incident_id, exc)
        return False


def fetch(incident_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a kill chain record from PostgreSQL by incident_id.

    Returns None if not found.
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM kill_chains WHERE incident_id = %s LIMIT 1",
                (incident_id,),
            )
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("Failed to fetch kill chain %s: %s", incident_id, exc)
        return None


def fetch_mttd_report() -> List[Dict[str, Any]]:
    """
    Return per-incident-type MTTD statistics for the /api/mttd/report endpoint.
    """
    sql = """
        SELECT
            incident_type,
            COUNT(*)                    AS incident_count,
            AVG(mttd_seconds)           AS avg_mttd_seconds,
            MIN(mttd_seconds)           AS min_mttd_seconds,
            MAX(mttd_seconds)           AS max_mttd_seconds,
            AVG(duration_seconds)       AS avg_duration_seconds,
            SUM(CASE WHEN mttd_seconds IS NOT NULL THEN 1 ELSE 0 END) AS with_mttd
        FROM kill_chains
        GROUP BY incident_type
        ORDER BY avg_mttd_seconds ASC NULLS LAST
    """
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.error("Failed to fetch MTTD report: %s", exc)
        return []
