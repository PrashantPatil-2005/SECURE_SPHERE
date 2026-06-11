"""
SecuriSphere — Kill-chain routes
================================
List and drill-down of correlated kill chains from PostgreSQL, with a Redis
incident-store fallback for detail. Token-protected.
"""

import os
import json
import logging

from flask import Blueprint, request, jsonify

from auth import token_required
from services import get_incidents

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("killchain_routes", __name__)


def _fetch_kill_chain_from_pg(incident_id: str):
    """Attempt to read kill chain detail from PostgreSQL."""
    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM kill_chains WHERE incident_id = %s LIMIT 1",
                (incident_id,),
            )
            row = cur.fetchone()
        conn.close()
        return dict(row) if row else None
    except Exception as exc:
        logger.error("PostgreSQL kill chain lookup error: %s", exc)
        return None


@bp.route('/api/kill-chains')
@token_required
def list_kill_chains():
    """
    List recent kill chains from PostgreSQL.

    Query params:
        limit   (int, default 20, max 200) — max rows to return
        site_id (str, optional)            — filter to chains whose JSONB
                                              ``steps`` reference this site_id
                                              (browser-layer incidents)

    Returns: {"status": "success", "data": {"kill_chains": [...], "count": N}}
    """
    try:
        limit = min(max(int(request.args.get('limit', 20)), 1), 200)
    except (TypeError, ValueError):
        limit = 20
    site_id = request.args.get('site_id')

    try:
        import psycopg2
        import psycopg2.extras
        conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            base = (
                "SELECT incident_id, incident_type, source_ip, service_path, "
                "first_service, last_service, mitre_techniques, "
                "first_event_at, detected_at, duration_seconds, mttd_seconds, "
                "severity, steps, created_at, "
                "scenario_label, narrative, status, analyst_note "
                "FROM kill_chains"
            )
            if site_id:
                cur.execute(
                    base + " WHERE steps::text ILIKE %s "
                           "ORDER BY created_at DESC LIMIT %s",
                    (f'%"site_id": "{site_id}"%', limit),
                )
            else:
                cur.execute(base + " ORDER BY created_at DESC LIMIT %s", (limit,))
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()

        for kc in rows:
            for field in ("first_event_at", "detected_at", "created_at"):
                if hasattr(kc.get(field), "isoformat"):
                    kc[field] = kc[field].isoformat()
            if isinstance(kc.get("steps"), str):
                try:
                    kc["steps"] = json.loads(kc["steps"])
                except Exception:
                    pass

        return jsonify({
            "status": "success",
            "data": {"kill_chains": rows, "count": len(rows)},
        })
    except Exception as exc:
        logger.error("Kill chain list error: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@bp.route('/api/kill-chains/<incident_id>')
@token_required
def get_kill_chain(incident_id):
    """
    Drill-down into a specific kill chain.
    First tries PostgreSQL (full steps/path); falls back to Redis incident store.
    """
    # Try PostgreSQL first for full kill-chain detail
    kc = _fetch_kill_chain_from_pg(incident_id)
    if kc:
        # Deserialise JSONB steps field if needed
        if isinstance(kc.get("steps"), str):
            try:
                kc["steps"] = json.loads(kc["steps"])
            except Exception:
                pass
        # Convert datetime objects to ISO strings for JSON serialisation
        for field in ("first_event_at", "detected_at", "created_at"):
            if hasattr(kc.get(field), "isoformat"):
                kc[field] = kc[field].isoformat()
        kc["source"] = "postgres"
        return jsonify({"status": "success", "data": {"kill_chain": kc}})

    # Fall back to Redis incident list
    incidents = get_incidents(100)
    for inc in incidents:
        if inc.get("incident_id") == incident_id:
            inc["source"] = "redis_fallback"
            return jsonify({"status": "success", "data": {"kill_chain": inc}})

    return jsonify({"status": "error", "message": "Kill chain not found", "source": "none"}), 404
