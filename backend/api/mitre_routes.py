"""
SecuriSphere — MITRE ATT&CK routes
==================================
Merges the static MITRE_MAP (everything SecuriSphere can detect) with live hit
counts from Redis incidents + the correlation engine, producing the coverage
breakdown and the tactic-bucketed heatmap matrix. Token-protected.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import requests
from flask import Blueprint, jsonify

from auth import token_required
import services
from services import get_incidents

# Resolve the static MITRE technique catalogue (shared with the engine).
_here = Path(__file__).resolve()
for _cand in (_here.parent, _here.parent.parent / "engine"):
    if (_cand / "mitre" / "mitre_map.py").exists():
        sys.path.insert(0, str(_cand))
        break
try:
    from mitre.mitre_map import MITRE_MAP, TACTIC_ORDER
except ImportError:
    MITRE_MAP, TACTIC_ORDER = {}, []

bp = Blueprint("mitre_routes", __name__)


@bp.route('/api/mitre-mapping')
@token_required
def mitre_mapping():
    """
    Merge the static MITRE_MAP (every technique SecuriSphere can detect)
    with live hit counts derived from Redis incidents and the correlation
    engine stats. Returns a full coverage breakdown suitable for the
    MITRE page.
    """
    # ---- 1. Aggregate live hit counts -----------------------------------
    hit_counts: dict = defaultdict(int)
    incident_ids: dict = defaultdict(list)

    incidents = get_incidents(100)
    for inc in incidents:
        for technique in (inc.get("mitre_techniques") or []):
            if technique:
                hit_counts[technique] += 1
                incident_ids[technique].append(inc.get("incident_id"))

    # Engine stats (in-memory mitre_hits counter) — merges even if the
    # Redis incident list has been trimmed.
    try:
        eng_resp = requests.get(
            "http://correlation-engine:5070/engine/mitre-mapping", timeout=2,
        )
        if eng_resp.status_code == 200:
            eng_hits = (eng_resp.json().get("data") or {}).get("technique_hits") or {}
            for tech, hits in eng_hits.items():
                # Prefer the larger of the two counters
                hit_counts[tech] = max(hit_counts[tech], int(hits or 0))
    except Exception:
        pass

    # Optional Redis hash `mitre_hits` — reserved for future direct writes
    if services.redis_available:
        try:
            redis_hits = services.redis_client.hgetall("mitre_hits") or {}
            for tech, hits in redis_hits.items():
                try:
                    hit_counts[tech] = max(hit_counts[tech], int(hits))
                except (TypeError, ValueError):
                    pass
        except Exception:
            pass

    # ---- 2. Compose technique rows from MITRE_MAP -----------------------
    techniques = []
    coverage_tally = {"full": 0, "partial": 0, "theoretical": 0}
    tactics_summary: dict = defaultdict(int)

    for tid, entry in MITRE_MAP.items():
        row = {
            "technique_id":      entry["technique_id"],
            "technique_name":    entry["technique_name"],
            "tactic":            entry["tactic"],
            "tactic_id":         entry["tactic_id"],
            "hit_count":         int(hit_counts.get(tid, 0)),
            "coverage":          entry["coverage"],
            "scenarios":         list(entry.get("scenarios", [])),
            "detected_by":       list(entry.get("detected_by", [])),
            "correlation_rules": list(entry.get("correlation_rules", [])),
            "container_context": entry.get("container_context", ""),
            "description":       entry.get("description", ""),
            "incident_ids":      incident_ids.get(tid, [])[:10],
        }
        techniques.append(row)
        coverage_tally[entry["coverage"]] = coverage_tally.get(entry["coverage"], 0) + 1
        tactics_summary[entry["tactic"]] += 1

    # Sort by hit_count desc, then by technique_id for stable ordering
    techniques.sort(key=lambda r: (-r["hit_count"], r["technique_id"]))

    return jsonify({
        "status": "success",
        "data": {
            "techniques":            techniques,
            "tactics_summary":       dict(tactics_summary),
            "total_techniques":      len(techniques),
            "full_coverage":         coverage_tally.get("full", 0),
            "partial_coverage":      coverage_tally.get("partial", 0),
            "theoretical_coverage":  coverage_tally.get("theoretical", 0),
            "total_incidents":       len(incidents),
            "tactic_order":          TACTIC_ORDER,
        }
    })


# ============================================================
# MITRE COVERAGE v2  (/api/v2/mitre/coverage)
# ============================================================
#
# Tactic-bucketed coverage matrix optimised for the heatmap UI: every
# technique SecuriSphere knows about appears as a cell with
# {hit_count, last_seen, status, rules, incident_ids}. Status is
# "covered" when hit_count > 0, else falls back to MITRE_MAP.coverage.

@bp.route('/api/v2/mitre/coverage')
@token_required
def mitre_coverage_v2():
    # ---- 1. Aggregate hits + last_seen from recent incidents -----------
    hit_counts: dict = defaultdict(int)
    last_seen: dict  = {}
    incident_ids: dict = defaultdict(list)
    incidents = get_incidents(200)
    for inc in incidents:
        ts = inc.get("timestamp") or inc.get("created_at")
        for technique in (inc.get("mitre_techniques") or []):
            if not technique:
                continue
            hit_counts[technique] += 1
            incident_ids[technique].append(inc.get("incident_id"))
            if ts and (technique not in last_seen or ts > last_seen[technique]):
                last_seen[technique] = ts

    # Merge engine in-memory counter (covers trimmed Redis lists).
    try:
        eng_resp = requests.get(
            "http://correlation-engine:5070/engine/mitre-mapping", timeout=2,
        )
        if eng_resp.status_code == 200:
            for tech, hits in ((eng_resp.json().get("data") or {}).get("technique_hits") or {}).items():
                hit_counts[tech] = max(hit_counts[tech], int(hits or 0))
    except Exception:
        pass

    # ---- 2. Bucket every known technique by tactic ---------------------
    buckets: dict = defaultdict(list)
    coverage_summary = {"covered": 0, "uncovered": 0, "partial": 0, "theoretical": 0}
    techniques_total = 0

    for tid, entry in MITRE_MAP.items():
        techniques_total += 1
        hits = int(hit_counts.get(tid, 0))
        if hits > 0:
            status = "covered"
            coverage_summary["covered"] += 1
        elif entry.get("coverage") == "full":
            status = "uncovered"
            coverage_summary["uncovered"] += 1
        elif entry.get("coverage") == "partial":
            status = "partial"
            coverage_summary["partial"] += 1
        else:
            status = "theoretical"
            coverage_summary["theoretical"] += 1

        buckets[entry["tactic"]].append({
            "technique_id":      entry["technique_id"],
            "technique_name":    entry["technique_name"],
            "tactic":            entry["tactic"],
            "tactic_id":         entry["tactic_id"],
            "hit_count":         hits,
            "last_seen":         last_seen.get(tid),
            "status":            status,                # covered | partial | uncovered | theoretical
            "coverage":          entry.get("coverage"), # static label from MITRE_MAP
            "rules":             list(entry.get("correlation_rules") or []),
            "detected_by":       list(entry.get("detected_by") or []),
            "scenarios":         list(entry.get("scenarios") or []),
            "description":       entry.get("description", ""),
            "incident_ids":      incident_ids.get(tid, [])[:10],
        })

    # ---- 3. Order buckets by canonical kill-chain tactic order ---------
    rows = []
    seen_tactics = set()
    for tactic in TACTIC_ORDER:
        cells = buckets.get(tactic) or []
        if not cells:
            continue
        cells.sort(key=lambda c: c["technique_id"])
        rows.append({
            "tactic":     tactic,
            "tactic_id":  cells[0]["tactic_id"],
            "covered":    sum(1 for c in cells if c["status"] == "covered"),
            "total":      len(cells),
            "techniques": cells,
        })
        seen_tactics.add(tactic)
    # Append any tactics outside TACTIC_ORDER (defensive).
    for tactic, cells in buckets.items():
        if tactic in seen_tactics:
            continue
        cells.sort(key=lambda c: c["technique_id"])
        rows.append({
            "tactic":     tactic,
            "tactic_id":  cells[0]["tactic_id"],
            "covered":    sum(1 for c in cells if c["status"] == "covered"),
            "total":      len(cells),
            "techniques": cells,
        })

    return jsonify({
        "status": "success",
        "data": {
            "rows":             rows,
            "tactic_order":     TACTIC_ORDER,
            "summary":          coverage_summary,
            "techniques_total": techniques_total,
            "incidents_total":  len(incidents),
            "generated_at":     datetime.utcnow().isoformat() + "Z",
        }
    })
