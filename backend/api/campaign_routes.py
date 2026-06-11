"""
SecuriSphere — Campaign aggregation routes
==========================================
Campaigns group multiple correlated incidents from one attacker into a single
analyst-facing record. See backend/engine/correlation/campaign_aggregator.py
for the aggregation logic. Token-protected.
"""

import os
import logging

from flask import Blueprint, request, jsonify

from auth import token_required, role_required  # noqa: F401 (role_required kept for parity)

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("campaign_routes", __name__)


def _campaigns_pg_conn():
    import psycopg2
    if os.getenv("DATABASE_URL"):
        return psycopg2.connect(os.getenv("DATABASE_URL"))
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "database"),
        port=int(os.getenv("POSTGRES_PORT", 5432)),
        dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
        user=os.getenv("POSTGRES_USER", "securisphere_user"),
        password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
    )


def _serialize_campaign(row):
    """Convert a RealDictCursor row into the JSON shape the dashboard expects."""
    out = dict(row)
    for k in ("first_event_at", "last_event_at", "created_at",
              "updated_at", "closed_at"):
        v = out.get(k)
        if v is not None and hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    out["campaign_id"] = str(out.get("campaign_id"))
    out["incident_ids"] = [str(x) for x in (out.get("incident_ids") or [])]
    return out


@bp.route('/api/campaigns', methods=['GET'])
@token_required
def list_campaigns():
    """List campaigns, newest activity first.

    Query params:
        status   active|closed|all   (default: all)
        severity critical|high|medium|low (optional filter)
        limit    int (default 50, max 200)
    """
    import psycopg2.extras
    status   = (request.args.get('status') or 'all').lower()
    severity = (request.args.get('severity') or '').lower()
    limit    = min(int(request.args.get('limit', 50)), 200)

    where = []
    params = []
    if status in ('active', 'closed'):
        where.append("status = %s")
        params.append(status)
    if severity in ('critical', 'high', 'medium', 'low'):
        where.append("severity = %s")
        params.append(severity)
    sql = "SELECT * FROM campaigns"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY last_event_at DESC LIMIT %s"
    params.append(limit)

    try:
        conn = _campaigns_pg_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        conn.close()
        campaigns = [_serialize_campaign(r) for r in rows]
        return jsonify({
            "status": "success",
            "data": {
                "campaigns": campaigns,
                "count": len(campaigns),
            },
        })
    except Exception as exc:
        logger.warning("list_campaigns failed: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@bp.route('/api/campaigns/stats', methods=['GET'])
@token_required
def campaigns_stats():
    """Aggregate counts for the dashboard KPI strip."""
    try:
        conn = _campaigns_pg_conn()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) FILTER (WHERE status = 'active')                     AS active,
                    COUNT(*) FILTER (WHERE status = 'closed')                     AS closed,
                    COUNT(*) FILTER (WHERE status = 'active' AND severity='critical') AS critical_active,
                    COUNT(*) FILTER (WHERE status = 'active' AND severity='high')     AS high_active,
                    COALESCE(AVG(incident_count) FILTER (WHERE status='active'), 0)   AS avg_incidents_per_active,
                    COALESCE(MAX(incident_count), 0)                              AS max_incidents
                FROM campaigns
            """)
            row = cur.fetchone()
        conn.close()
        return jsonify({
            "status": "success",
            "data": {
                "active":                   int(row[0] or 0),
                "closed":                   int(row[1] or 0),
                "critical_active":          int(row[2] or 0),
                "high_active":              int(row[3] or 0),
                "avg_incidents_per_active": float(row[4] or 0),
                "max_incidents":            int(row[5] or 0),
            },
        })
    except Exception as exc:
        logger.warning("campaigns_stats failed: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500


@bp.route('/api/campaigns/<campaign_id>', methods=['GET'])
@token_required
def get_campaign(campaign_id):
    """Drill-down: campaign + its incidents + merged kill chain."""
    import psycopg2.extras
    try:
        conn = _campaigns_pg_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM campaigns WHERE campaign_id = %s",
                        (campaign_id,))
            campaign = cur.fetchone()
            if not campaign:
                conn.close()
                return jsonify({"status": "error",
                                "message": "Campaign not found"}), 404

            cur.execute("""
                SELECT incident_id, incident_type, severity, title, description,
                       source_ip, target_username, mitre_techniques,
                       technique_id, technique_name, tactic,
                       time_span_seconds, risk_score_at_time, confidence
                  FROM correlated_incidents
                 WHERE campaign_id = %s
                 ORDER BY incident_id
            """, (campaign_id,))
            incidents = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT incident_id, service_path, steps, mitre_techniques,
                       first_event_at, detected_at, mttd_seconds, severity
                  FROM kill_chains
                 WHERE campaign_id = %s
                 ORDER BY first_event_at
            """, (campaign_id,))
            kill_chains = []
            for r in cur.fetchall():
                row = dict(r)
                for k in ("first_event_at", "detected_at"):
                    v = row.get(k)
                    if v is not None and hasattr(v, "isoformat"):
                        row[k] = v.isoformat()
                row["incident_id"] = str(row["incident_id"])
                kill_chains.append(row)
        conn.close()

        for inc in incidents:
            inc["incident_id"] = str(inc.get("incident_id"))

        return jsonify({
            "status": "success",
            "data": {
                "campaign":    _serialize_campaign(campaign),
                "incidents":   incidents,
                "kill_chains": kill_chains,
            },
        })
    except Exception as exc:
        logger.warning("get_campaign failed: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500
