"""
SecuriSphere — Metrics / dashboard / system-status routes
=========================================================
Dashboard summary KPIs, raw metrics, timeline buckets, service health, and
demo-scenario status. Token-protected.
"""

import os
from collections import defaultdict
from datetime import datetime, timedelta

import requests
from flask import Blueprint, request, jsonify

from auth import token_required
import services
from services import (
    calculate_metrics,
    get_latest_summary,
    get_incidents,
    get_risk_scores,
    get_all_events,
    get_events_from_redis,
)

bp = Blueprint("metrics_routes", __name__)


@bp.route('/api/dashboard/summary')
@token_required
def dashboard_summary():
    metrics = calculate_metrics()
    return jsonify({
        "status": "success",
        "data": {
            "summary": get_latest_summary(),
            "metrics": {
                "raw_events": metrics["raw_events"],
                "correlated_incidents": metrics["correlated_incidents"],
                "alert_reduction_percentage": metrics["alert_reduction_percentage"],
                "active_threats": metrics["active_risk_entities"],
                "critical_events": metrics["events_by_severity"]["critical"]
            },
            "recent_incidents": get_incidents(5),
            "risk_scores": get_risk_scores(),
            "events_by_layer": metrics["raw_events"], # simplified
            "timestamp": datetime.utcnow().isoformat()
        }
    })


@bp.route('/api/metrics')
@token_required
def system_metrics():
    return jsonify({
        "status": "success",
        "data": calculate_metrics()
    })


@bp.route('/api/metrics/timeline')
@token_required
def metrics_timeline():
    # Mocking timeline for now as we don't have time-series DB
    # In real impl, we would bucket recent events
    minutes = int(request.args.get('minutes', 30))
    events = get_all_events(500) # Get recent

    timeline = defaultdict(lambda: {"timestamp": "", "network": 0, "api": 0, "auth": 0, "total": 0})
    now = datetime.utcnow()

    # Init buckets
    for i in range(minutes):
        t = (now - timedelta(minutes=i)).strftime("%Y-%m-%dT%H:%M:00Z")
        timeline[t]["timestamp"] = t

    for e in events:
        ts_str = e.get('timestamp')
        if ts_str:
            try:
                # Truncate to minute
                ts = datetime.fromisoformat(ts_str.replace('Z', ''))
                key = ts.strftime("%Y-%m-%dT%H:%M:00Z")
                if key in timeline:
                    layer = e.get('source_layer', 'other')
                    timeline[key][layer] += 1
                    timeline[key]['total'] += 1
            except:
                pass

    return jsonify({
        "status": "success",
        "data": {
            "timeline": sorted([v for v in timeline.values()], key=lambda x: x['timestamp']),
            "time_range": {"minutes": minutes}
        }
    })


@bp.route('/api/system/status')
@token_required
def system_status():
    status = {
        "redis": {"connected": services.redis_available},
        "monitors": {},
        "correlation_engine": {"active": False, "incidents": 0},
        "total_events": 0,
        "uptime_seconds": (datetime.utcnow() - services.SERVER_START_TIME).seconds
    }

    if services.redis_available:
        status["redis"]["ping"] = "PONG"

        # Per-monitor liveness: count + latest-event freshness (<=120s => active)
        monitors = ["network", "api", "auth", "browser"]
        now_ts = datetime.utcnow()
        for m in monitors:
            last_list = get_events_from_redis(f"events:{m}", 0, 1) or []
            last = last_list[0] if last_list else {}
            last_ts_raw = last.get('timestamp') if isinstance(last, dict) else None
            fresh = False
            if last_ts_raw:
                try:
                    s = str(last_ts_raw)
                    dt = datetime.fromisoformat(s.replace('Z', '+00:00')) if ('Z' in s or '+' in s[10:]) else datetime.fromisoformat(s)
                    age = (now_ts - dt.replace(tzinfo=None)).total_seconds()
                    fresh = age <= 120
                except Exception:
                    fresh = False
            count = services.redis_client.llen(f"events:{m}")
            status["monitors"][m] = {
                "active": bool(fresh or count > 0),
                "last_event": last_ts_raw,
                "event_count": count,
            }
            status["total_events"] += count

        status["correlation_engine"]["incidents"] = services.redis_client.llen("incidents")

    # Ping correlation engine /health (container DNS name)
    try:
        engine_url = os.getenv("SECURISPHERE_ENGINE_URL", "http://correlation-engine:5070")
        r = requests.get(f"{engine_url}/engine/health", timeout=1.5)
        if r.ok:
            body = r.json() if r.headers.get('content-type', '').startswith('application/json') else {}
            status["correlation_engine"]["active"] = True
            status["correlation_engine"]["uptime"] = body.get("uptime") or body.get("uptime_seconds")
        else:
            status["correlation_engine"]["active"] = False
            status["correlation_engine"]["error"] = f"HTTP {r.status_code}"
    except Exception as e:
        status["correlation_engine"]["active"] = False
        status["correlation_engine"]["error"] = str(e)[:120]

    return jsonify({"status": "success", "data": status})


@bp.route('/api/demo-status')
@token_required
def demo_status():
    """Return whether a demo scenario is currently running."""
    try:
        active_val = services.redis_client.get('demo:active') if services.redis_available else None
        scenario_val = services.redis_client.get('demo:scenario') if services.redis_available else None
        return jsonify({"status": "success", "data": {
            "active": active_val is not None,
            "scenario": scenario_val if isinstance(scenario_val, str) else (scenario_val.decode() if scenario_val else None)
        }})
    except Exception as e:
        return jsonify({"status": "success", "data": {"active": False, "scenario": None}})
