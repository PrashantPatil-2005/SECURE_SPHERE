"""
SecuriSphere — Event routes
===========================
Security-event listing, lookup, latest-per-layer, and admin clear. Token-protected.
"""

import os
import logging
from datetime import datetime

from flask import Blueprint, request, jsonify

from auth import token_required, role_required
import services
from services import get_all_events, get_events_from_redis, calculate_event_stats

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("events_routes", __name__)


@bp.route('/api/events')
@token_required
def get_events():
    layer = request.args.get('layer', 'all')
    limit = min(int(request.args.get('limit', 50)), 500)
    severity = request.args.get('severity', 'all')
    ev_type = request.args.get('event_type')

    if layer == 'all':
        events = get_all_events(limit) # This limits first, then filters. Might need optimization for deep filtering
        # Optimize: get more then filter? For now, fetch limit*2 to allow some filtering space
        if severity != 'all' or ev_type:
            events = get_all_events(limit * 5)
    else:
        events = get_events_from_redis(f"events:{layer}", 0, limit * 5)

    # Filtering
    filtered = []
    for e in events:
        if severity != 'all' and e.get('severity', {}).get('level') != severity:
            continue
        if ev_type and e.get('event_type') != ev_type:
            continue
        filtered.append(e)

    # Apply limit after filtering
    final_events = filtered[:limit]

    return jsonify({
        "status": "success",
        "data": {
            "events": final_events,
            "count": len(final_events),
            "total_available": {
                "network": services.redis_client.llen("events:network") if services.redis_available else 0,
                "api": services.redis_client.llen("events:api") if services.redis_available else 0,
                "auth": services.redis_client.llen("events:auth") if services.redis_available else 0
            },
            "filters_applied": {
                "layer": layer,
                "severity": severity,
                "event_type": ev_type,
                "limit": limit
            },
            "stats": calculate_event_stats(final_events)
        }
    })


@bp.route('/api/events/<event_id>')
@token_required
def get_single_event(event_id):
    # Search in all lists (expensive but necessary without index)
    # Optimization: Search recent 1000 first
    all_ev = get_all_events(1000)
    for e in all_ev:
        if e.get('event_id') == event_id:
            return jsonify({"status": "success", "data": {"event": e}})
    return jsonify({"status": "error", "message": "Event not found"}), 404


@bp.route('/api/events/latest')
@token_required
def latest_events():
    return jsonify({
        "status": "success",
        "data": {
            "latest": {
                "network": (get_events_from_redis("events:network", 0, 1) or [None])[0],
                "api": (get_events_from_redis("events:api", 0, 1) or [None])[0],
                "auth": (get_events_from_redis("events:auth", 0, 1) or [None])[0]
            }
        }
    })


@bp.route('/api/events/clear', methods=['POST'])
@token_required
@role_required('admin')
def clear_events():
    if services.redis_available:
        services.redis_client.delete("events:network", "events:api", "events:auth", "incidents", "risk_scores_current", "latest_summary")

    # Also clear PostgreSQL incidents (kill_chains)
    try:
        import psycopg2
        conn = psycopg2.connect(os.getenv("DATABASE_URL")) if os.getenv("DATABASE_URL") else psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "database"),
            port=int(os.getenv("POSTGRES_PORT", 5432)),
            dbname=os.getenv("POSTGRES_DB", "securisphere_db"),
            user=os.getenv("POSTGRES_USER", "securisphere_user"),
            password=os.getenv("POSTGRES_PASSWORD", "securisphere_pass_2024"),
        )
        with conn.cursor() as cur:
            cur.execute("TRUNCATE TABLE kill_chains RESTART IDENTITY")
            conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error clearing PostgreSQL kill_chains: {e}")

    return jsonify({
        "status": "success",
        "message": "All events and incidents cleared (Redis + Postgres)",
        "timestamp": datetime.utcnow().isoformat()
    })
