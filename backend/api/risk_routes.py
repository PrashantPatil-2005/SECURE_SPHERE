"""
SecuriSphere — Risk-score routes
================================
Entity risk scores (service/IP) and per-account risk summaries. Token-protected.
"""

import os
import logging

from flask import Blueprint, jsonify

from auth import token_required
import services
from services import get_risk_scores, get_incidents, _looks_like_ip

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("risk_routes", __name__)


@bp.route('/api/risk-scores')
@token_required
def list_risk_scores():
    risks = get_risk_scores()

    # Normalise each entry so callers can rely on `entity` / `entity_type`
    # regardless of whether the key is a service name or a fallback IP.
    normalised = {}
    for key, r in risks.items():
        entity_type = r.get('entity_type') or ('service' if not _looks_like_ip(key) else 'ip')
        normalised[key] = {
            **r,
            "entity":      r.get('entity') or key,
            "entity_type": entity_type,
            "source_ip":   r.get('source_ip') or (key if entity_type == 'ip' else None),
        }

    summary = {
        "total_entities":   len(normalised),
        "service_count":    sum(1 for v in normalised.values() if v["entity_type"] == "service"),
        "ip_count":         sum(1 for v in normalised.values() if v["entity_type"] == "ip"),
        "critical_count":   0,
        "threatening_count":0,
        "suspicious_count": 0,
        "normal_count":     0,
    }

    for r in normalised.values():
        score = r.get('current_score', 0)
        if score >= 90: summary["critical_count"] += 1
        elif score >= 70: summary["threatening_count"] += 1
        elif score >= 30: summary["suspicious_count"] += 1
        else: summary["normal_count"] += 1

    return jsonify({
        "status": "success",
        "data": {
            "risk_scores": normalised,
            "summary": summary
        }
    })


@bp.route('/api/risk-scores/<ip>')
@token_required
def get_ip_risk(ip):
    risks = get_risk_scores()
    if ip in risks:
        return jsonify({"status": "success", "data": risks[ip]})
    return jsonify({"status": "error", "message": "Risk score not found"}), 404


# ============================================================
# ACCOUNT RISK  (/api/v2/risk/accounts)
# ============================================================
#
# Per-user risk summary built from correlated_incidents grouped by
# target_username. Returns up to 100 accounts ordered by recent activity.
# Severity is the worst label seen across each account's incidents.

_SEV_RANK = {"info": 0, "low": 0, "medium": 1, "high": 2, "critical": 3}


def _worst_severity(values):
    best = None
    best_rank = -1
    for v in values:
        r = _SEV_RANK.get(str(v or "").lower(), 0)
        if r > best_rank:
            best, best_rank = v, r
    return best or "high"


@bp.route('/api/v2/risk/accounts')
@token_required
def risk_accounts_v2():
    """Group incidents by target_username and return per-user risk summaries."""
    rows = []
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
                """
                SELECT
                    target_username AS username,
                    COUNT(*)        AS incident_count,
                    MAX(created_at) AS last_seen,
                    ARRAY_AGG(severity) AS severities
                  FROM correlated_incidents
                 WHERE target_username IS NOT NULL AND target_username <> ''
                 GROUP BY target_username
                 ORDER BY last_seen DESC NULLS LAST
                 LIMIT 100
                """
            )
            for r in cur.fetchall():
                ts = r.get("last_seen")
                rows.append({
                    "username":         r["username"],
                    "incident_count":   int(r.get("incident_count") or 0),
                    "highest_severity": _worst_severity(r.get("severities") or []),
                    "last_seen":        ts.isoformat() if hasattr(ts, "isoformat") else ts,
                })
        conn.close()
    except Exception as exc:
        # Fall back to the in-memory Redis incident list so the panel still
        # shows something on a fresh stack with no PG persistence yet.
        logger.debug("account risk PG path failed, using Redis fallback: %s", exc)
        agg = {}
        for inc in get_incidents(200):
            u = inc.get("target_username")
            if not u:
                continue
            entry = agg.setdefault(u, {"incident_count": 0, "severities": [], "last_seen": None})
            entry["incident_count"] += 1
            entry["severities"].append(inc.get("severity"))
            ts = inc.get("timestamp") or inc.get("created_at")
            if ts and (entry["last_seen"] is None or ts > entry["last_seen"]):
                entry["last_seen"] = ts
        for u, e in agg.items():
            rows.append({
                "username":         u,
                "incident_count":   e["incident_count"],
                "highest_severity": _worst_severity(e["severities"]),
                "last_seen":        e["last_seen"],
            })
        rows.sort(key=lambda r: r.get("last_seen") or "", reverse=True)

    return jsonify({"status": "success", "data": rows})
