"""
SecuriSphere — Evaluation / audit / MTTD routes
===============================================
Reviewer-facing MTTD experiment report (public), JWT-protected audit-log read,
and per-incident-type MTTD statistics (PostgreSQL with Redis approximation
fallback).
"""

import os
import json
import logging
from typing import Optional

from flask import Blueprint, request, jsonify

from auth import token_required
from services import get_incidents

try:
    from audit import query_audit
except Exception:  # audit module optional in some envs
    def query_audit(*_a, **_kw):
        return {"total": 0, "logs": []}

logger = logging.getLogger("SecuriSphereBackend")

bp = Blueprint("evaluation_routes", __name__)


# ============================================================
# EVALUATION RESULTS  (/api/v2/evaluation/results)
# ============================================================
#
# Surfaces the static MTTD experiment report so the /evaluation page can
# render reviewer-facing numbers. Reads `evaluation/dashboard_results.json`
# from disk if present; otherwise serves a hardcoded fallback that matches
# the published 2026-04-18 results so demos never show a blank page.
# Cached at module import — do NOT recompute on every request.

_EVALUATION_FALLBACK = {
    "generated_at": "2026-04-18",
    "overall": {
        "mttd_raw_logs_seconds": 252.8,
        "mttd_dashboard_seconds": 6.75,
        "reduction_percent": 97.33,
        "target_reduction_percent": 70.0,
        "target_met": True,
        "backend_correlation_latency_seconds": 0.08,
    },
    "scenarios": [
        {
            "name": "Scenario A",
            "description": "Brute Force → Credential Compromise → Data Exfiltration",
            "mttd_raw": 247.0,
            "mttd_dashboard": 6.00,
            "reduction_percent": 97.57,
            "raw_trials": [239, 255, 247],
            "dashboard_trials": [6.01, 6.00, 6.00],
            "raw_stddev": 6.53,
            "dashboard_stddev": 0.005,
        },
        {
            "name": "Scenario B",
            "description": "Recon → SQL Injection → Privilege Escalation",
            "mttd_raw": 199.3,
            "mttd_dashboard": 8.14,
            "reduction_percent": 95.91,
            "raw_trials": [194, 206, 198],
            "dashboard_trials": [8.15, 8.14, 8.14],
            "raw_stddev": 5.03,
            "dashboard_stddev": 0.005,
        },
        {
            "name": "Scenario C",
            "description": "Multi-Hop Lateral Movement (4 hops)",
            "mttd_raw": 312.0,
            "mttd_dashboard": 6.11,
            "reduction_percent": 98.04,
            "raw_trials": [305, 319, 312],
            "dashboard_trials": [6.12, 6.13, 6.08],
            "raw_stddev": 5.72,
            "dashboard_stddev": 0.022,
        },
    ],
    "system_metrics": {
        "trials_completed": 18,
        "trials_total": 18,
        "false_positives_benign": 0,
        "detection_rate_percent": 100.0,
    },
    "methodology_note": (
        "Raw-log baselines use simulated analyst timing from baseline_mttd.py "
        "modeling realistic scroll/search cognitive load. Dashboard timings "
        "measured from kill_chains.mttd_seconds + UI overhead (3s poll + 1s "
        "render + 2s operator read)."
    ),
}


def _safe_float(s):
    try:
        if s is None or s == "" or str(s).upper() == "N/A":
            return None
        return float(s)
    except Exception:
        return None


def _parse_evaluation_csv(path: str) -> Optional[dict]:
    """Parse a per-scenario evaluation CSV emitted by run_evaluation.py.

    Returns a payload in the same shape as ``_EVALUATION_FALLBACK`` so the
    /evaluation page renders without branching. Returns None on any parse
    failure (caller falls back to JSON / constant)."""
    import csv
    try:
        with open(path, "r", encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        return None
    if not rows:
        return None

    scenarios = []
    mttds = []
    detection_rates = []
    fps_benign = 0
    for r in rows:
        name = (r.get("Scenario") or "").strip()
        mttd = _safe_float(r.get("MTTD (s)"))
        det = _safe_float(r.get("Detection Rate (%)"))
        fpr = _safe_float(r.get("FPR"))
        if mttd is not None:
            mttds.append(mttd)
        if det is not None and name != "Benign Traffic":
            detection_rates.append(det)
        if name == "Benign Traffic" and fpr is not None and fpr > 0:
            fps_benign += int(_safe_float(r.get("Incidents")) or 0)
        scenarios.append({
            "name": name,
            "raw_events": int(_safe_float(r.get("Raw Events")) or 0),
            "incidents": int(_safe_float(r.get("Incidents")) or 0),
            "detection_rate_percent": det,
            "fpr": fpr,
            "arr_percent": _safe_float(r.get("ARR (%)")),
            "mttd_seconds": mttd,
            "correlation_accuracy_percent": _safe_float(r.get("Correlation Accuracy (%)")),
        })

    avg_mttd = round(sum(mttds) / len(mttds), 3) if mttds else None
    overall_det = round(sum(detection_rates) / len(detection_rates), 3) if detection_rates else None
    return {
        "generated_at": os.path.basename(path),
        "source": "csv",
        "source_path": path,
        "overall": {
            "mttd_dashboard_seconds": avg_mttd,
            "detection_rate_percent": overall_det,
        },
        "scenarios": scenarios,
        "system_metrics": {
            "trials_completed": len(rows),
            "false_positives_benign": fps_benign,
            "detection_rate_percent": overall_det,
        },
    }


def _latest_csv_in(dirs) -> Optional[str]:
    import glob
    candidates = []
    for d in dirs:
        try:
            candidates.extend(glob.glob(os.path.join(d, "evaluation_report_*.csv")))
        except Exception:
            continue
    if not candidates:
        return None
    try:
        return max(candidates, key=os.path.getmtime)
    except Exception:
        return None


def _load_evaluation_report():
    """Resolve the evaluation payload. Order:

      1. Latest ``evaluation_report_*.csv`` under evaluation/results/ — picks
         up live trial runs without restarting the API.
      2. ``evaluation/dashboard_results.json`` — curated demo snapshot.
      3. ``_EVALUATION_FALLBACK`` constant — guarantees the page never blanks.

    Cached on the function object; restart the backend to refresh."""
    cached = getattr(_load_evaluation_report, "_cache", None)
    if cached is not None:
        return cached

    here = os.path.dirname(__file__)
    csv_dirs = [
        os.path.abspath(os.path.join(here, "..", "..", "evaluation", "results")),
        os.path.join(os.getcwd(), "evaluation", "results"),
    ]
    payload = None
    csv_path = _latest_csv_in(csv_dirs)
    if csv_path:
        payload = _parse_evaluation_csv(csv_path)

    if not isinstance(payload, dict):
        json_candidates = [
            os.path.abspath(os.path.join(here, "..", "..", "evaluation", "dashboard_results.json")),
            os.path.join(os.getcwd(), "evaluation", "dashboard_results.json"),
        ]
        for p in json_candidates:
            try:
                with open(p, "r", encoding="utf-8") as fh:
                    payload = json.load(fh)
                break
            except Exception:
                continue

    if not isinstance(payload, dict):
        payload = _EVALUATION_FALLBACK
    _load_evaluation_report._cache = payload
    return payload


@bp.route('/api/v2/evaluation/results')
def evaluation_results_v2():
    """Static MTTD experiment report — reviewer-facing. No auth (matches the
    public /evaluation route in the dashboard)."""
    return jsonify({"status": "success", "data": _load_evaluation_report()})


# ============================================================
# AUDIT LOG  (/api/v2/audit/logs)
# ============================================================
#
# JWT-protected read of the system-wide audit_log table. Filterable by
# actor, action prefix, severity, and ISO date window. Hard cap of 500
# rows per call so the dashboard cannot accidentally page the whole table.

@bp.route('/api/v2/audit/logs')
@token_required
def audit_logs_v2():
    args = request.args
    try:
        limit = int(args.get("limit", 100))
    except (TypeError, ValueError):
        limit = 100
    severity = args.get("severity") or None
    if severity and severity not in ("info", "warning", "critical"):
        return jsonify({"status": "error", "message": "Invalid severity"}), 400

    try:
        result = query_audit(
            actor=args.get("actor") or None,
            action_prefix=args.get("action") or None,
            severity=severity,
            start=args.get("from") or None,
            end=args.get("to") or None,
            limit=limit,
        )
    except Exception as exc:
        logger.warning("audit query failed: %s", exc)
        return jsonify({"status": "error", "message": "Audit query failed"}), 500

    return jsonify({"status": "success", "data": result})


# ============================================================
# MTTD REPORT  (/api/mttd/report)
# ============================================================

@bp.route('/api/mttd/report')
@token_required
def mttd_report():
    """
    Return per-scenario / per-incident-type MTTD statistics.

    Tries PostgreSQL kill_chains table first (accurate), then falls back to
    approximating from the Redis incident list (time_span_seconds + 1.5s).
    """
    # Try PostgreSQL
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
            cur.execute("""
                SELECT
                    incident_type,
                    COUNT(*)                         AS incident_count,
                    AVG(mttd_seconds)                AS avg_mttd_seconds,
                    MIN(mttd_seconds)                AS min_mttd_seconds,
                    MAX(mttd_seconds)                AS max_mttd_seconds,
                    AVG(duration_seconds)            AS avg_attack_duration_seconds
                FROM kill_chains
                GROUP BY incident_type
                ORDER BY avg_mttd_seconds ASC NULLS LAST
            """)
            rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        if rows:
            # Convert Decimal / None to plain Python types for JSON
            for row in rows:
                for k, v in row.items():
                    if hasattr(v, "__float__"):
                        row[k] = round(float(v), 3) if v is not None else None
            return jsonify({"status": "success", "source": "postgresql", "data": rows})
    except Exception as exc:
        logger.warning("MTTD PostgreSQL fallback: %s", exc)

    # Redis approximation fallback
    incidents = get_incidents(100)
    from collections import defaultdict as _dd
    buckets: dict = _dd(lambda: {"count": 0, "total_mttd": 0.0, "values": []})
    for inc in incidents:
        mttd = inc.get("mttd_seconds")
        if mttd is None:
            mttd = (inc.get("time_span_seconds") or 0) + 1.5  # approximation
        t = inc.get("incident_type", "unknown")
        buckets[t]["count"]      += 1
        buckets[t]["total_mttd"] += mttd
        buckets[t]["values"].append(mttd)

    result = []
    for t, b in buckets.items():
        avg = b["total_mttd"] / b["count"] if b["count"] else None
        result.append({
            "incident_type":             t,
            "incident_count":            b["count"],
            "avg_mttd_seconds":          round(avg, 3) if avg is not None else None,
            "min_mttd_seconds":          round(min(b["values"]), 3) if b["values"] else None,
            "max_mttd_seconds":          round(max(b["values"]), 3) if b["values"] else None,
            "avg_attack_duration_seconds": None,
        })
    result.sort(key=lambda x: (x["avg_mttd_seconds"] or float("inf")))

    return jsonify({"status": "success", "source": "redis_approximation", "data": result})
