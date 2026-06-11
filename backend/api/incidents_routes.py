"""
SecuriSphere — Incident routes
==============================
Incident listing/detail plus triage-status read/write. Status writes are
Redis-backed, mirrored to the Postgres kill_chains table, broadcast over
Socket.IO, and recorded in the audit log. Token-protected.
"""

import os
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from auth import token_required
import services
from services import get_incidents
from extensions import socketio

try:
    from audit import log_audit
except Exception:  # audit module optional in some envs
    def log_audit(*_a, **_kw):
        return None

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("incidents_routes", __name__)

VALID_INCIDENT_STATUSES = (
    'open', 'active',
    'acknowledged', 'investigating',
    'resolved',
    'escalated', 'suppressed',
)


def _read_incident_status_redis(incident_id):
    """Return (status, note, updated_at) from Redis hash, or (None, None, None)."""
    if not services.redis_available or not incident_id:
        return None, None, None
    try:
        raw = services.redis_client.hgetall(f"incident_status:{incident_id}")
        if not raw:
            return None, None, None
        return raw.get('status'), raw.get('note'), raw.get('updated_at')
    except Exception:
        return None, None, None


def _write_incident_status_redis(incident_id, status, note):
    updated_at = datetime.utcnow().isoformat()
    if services.redis_available:
        try:
            services.redis_client.hset(
                f"incident_status:{incident_id}",
                mapping={
                    "status": status,
                    "note": note or "",
                    "updated_at": updated_at,
                },
            )
        except Exception as exc:
            logger.warning("redis status write failed: %s", exc)
    return updated_at


@bp.route('/api/incidents')
@token_required
def list_incidents():
    limit = min(int(request.args.get('limit', 20)), 100)
    incidents = get_incidents(limit)

    # Batch read statuses from PostgreSQL kill_chains (legacy source of truth)
    pg_status_map, pg_note_map = {}, {}
    try:
        import psycopg2
        import psycopg2.extras
        incident_ids = [i.get('incident_id') for i in incidents if i.get('incident_id')]
        if incident_ids:
            conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT incident_id, status, analyst_note FROM kill_chains "
                    "WHERE incident_id = ANY(%s)",
                    (incident_ids,),
                )
                for row in cur.fetchall():
                    key = str(row['incident_id'])
                    pg_status_map[key] = row['status']
                    pg_note_map[key] = row.get('analyst_note')
            conn.close()
    except Exception:
        pass

    # Merge in Redis override (PATCH writes to Redis hash incident_status:{id})
    for inc in incidents:
        iid = inc.get('incident_id')
        redis_status, redis_note, _ = _read_incident_status_redis(iid)
        inc['status'] = redis_status or pg_status_map.get(iid) or 'active'
        inc['analyst_note'] = redis_note or pg_note_map.get(iid) or inc.get('analyst_note')
        # Severity must never be null on the wire — kill chain incidents
        # are floored at 'high' end-to-end. Treat nested {level: ...} dicts
        # too, since some upstream emitters use that shape.
        sev = inc.get('severity')
        if isinstance(sev, dict):
            sev = sev.get('level')
        inc['severity'] = (str(sev).lower() if sev else 'high')
        # target_username is explicitly null (not missing) for non-auth
        # incidents so the frontend can render conditional chips reliably.
        inc['target_username'] = inc.get('target_username') or None

    return jsonify({
        "status": "success",
        "data": {
            "incidents": incidents,
            "count": len(incidents),
            "total_available": services.redis_client.llen("incidents") if services.redis_available else 0
        }
    })


@bp.route('/api/incidents/<incident_id>')
@token_required
def get_incident(incident_id):
    incidents = get_incidents(100)
    for i in incidents:
        if i.get('incident_id') == incident_id:
            sev = i.get('severity')
            if isinstance(sev, dict):
                sev = sev.get('level')
            i['severity'] = (str(sev).lower() if sev else 'high')
            i['target_username'] = i.get('target_username') or None
            return jsonify({"status": "success", "data": {"incident": i}})
    return jsonify({"status": "error", "message": "Incident not found"}), 404


@bp.route('/api/incidents/<incident_id>/status', methods=['PATCH'])
@token_required
def update_incident_status(incident_id):
    """Update the triage status of an incident (Redis-backed, mirrored to Postgres)."""
    try:
        data = request.get_json() or {}
        status = data.get('status')
        note = data.get('note', '') or ''

        if status not in VALID_INCIDENT_STATUSES:
            return jsonify({"status": "error", "message": "Invalid status value"}), 400

        # Primary store: Redis hash (per spec)
        updated_at = _write_incident_status_redis(incident_id, status, note)

        # Mirror to Postgres kill_chains for legacy readers
        try:
            import psycopg2
            conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "database"),
                port=int(os.getenv("POSTGRES_PORT", 5432)),
                dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
                user=os.getenv("POSTGRES_USER", "securisphere_user"),
                password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE kill_chains SET status = %s, analyst_note = %s WHERE incident_id = %s",
                        (status, note, incident_id),
                    )
                    if status == 'suppressed':
                        cur.execute("SELECT source_ip FROM kill_chains WHERE incident_id = %s", (incident_id,))
                        row = cur.fetchone()
                        if row and row[0] and services.redis_available:
                            services.redis_client.setex(f"suppressed:{row[0]}", 1800, "1")
            conn.close()
        except Exception as exc:
            logger.warning("postgres status mirror failed: %s", exc)

        socketio.emit('incident_status_change', {
            "type": "incident_status_change",
            "incident_id": incident_id,
            "status": status,
            "note": note,
            "updated_at": updated_at,
        })

        # Audit: incident triage action by user. Map status → action so the
        # log surfaces "incident.acknowledged" / "incident.resolved" etc.
        actor_user = getattr(request, "current_user", {}) or {}
        log_audit(
            action=f"incident.{status}",
            actor=actor_user.get("username") or "unknown",
            actor_type="user",
            target_type="incident",
            target_id=str(incident_id),
            detail={"status": status, "note": note},
            severity=("warning" if status in ("escalated", "suppressed") else "info"),
            source_ip=request.remote_addr,
        )

        return jsonify({
            "status": "success",
            "incident_id": incident_id,
            "updated_at": updated_at,
            "data": {"incident_id": incident_id, "status": status, "updated_at": updated_at},
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@bp.route('/api/incidents/<incident_id>/status', methods=['GET'])
@token_required
def get_incident_status(incident_id):
    """Return the current status for an incident (Redis hash, fallback open)."""
    status, note, updated_at = _read_incident_status_redis(incident_id)
    return jsonify({
        "incident_id": incident_id,
        "status": status or "open",
        "note": note or "",
        "updated_at": updated_at or "",
    })
