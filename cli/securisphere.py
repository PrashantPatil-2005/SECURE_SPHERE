#!/usr/bin/env python3
"""SecuriSphere CLI — analyst tool for the running engine.

Usage:
  securisphere status
  securisphere incidents [--limit N] [--min-confidence 0.7]
  securisphere replay <incident_id>
  securisphere explain <incident_id>
  securisphere diff <incident_id_a> <incident_id_b>
  securisphere predict
  securisphere drift
  securisphere mitre
  securisphere yaml-rules
  securisphere threat-intel [--refresh]
  securisphere stream-events [--follow]

Environment:
  SECURISPHERE_ENGINE_URL  default http://localhost:5070
  SECURISPHERE_API_URL     default http://localhost:5050
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, Optional

try:
    import requests
except Exception:
    print("error: 'requests' not installed. pip install requests", file=sys.stderr)
    sys.exit(1)

ENGINE_URL = os.getenv("SECURISPHERE_ENGINE_URL", "http://localhost:5070")
API_URL = os.getenv("SECURISPHERE_API_URL", "http://localhost:5050")


def _get(url: str, **kwargs) -> Dict[str, Any]:
    r = requests.get(url, timeout=10, **kwargs)
    r.raise_for_status()
    return r.json()


def _post(url: str, **kwargs) -> Dict[str, Any]:
    r = requests.post(url, timeout=10, **kwargs)
    r.raise_for_status()
    return r.json()


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, indent=2, default=str))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_status(_args) -> None:
    try:
        health = _get(f"{ENGINE_URL}/engine/health")
    except Exception as exc:
        print(f"engine unreachable: {exc}", file=sys.stderr)
        sys.exit(2)
    rules = _get(f"{ENGINE_URL}/engine/yaml-rules").get("data", {})
    ti = _get(f"{ENGINE_URL}/engine/threat-intel").get("data", {})
    print(f"engine:        {health.get('status')}  uptime={int(health.get('uptime', 0))}s")
    print(f"events:        {health.get('events_processed')}")
    print(f"incidents:     {health.get('incidents_created')}")
    print(f"py rules:      {health.get('active_rules')}")
    print(f"yaml rules:    {rules.get('rule_count', 0)} (enabled={rules.get('enabled', False)})")
    print(f"threat intel:  {ti.get('indicator_count', 0)} indicators (enabled={ti.get('enabled', False)})")


def cmd_incidents(args) -> None:
    data = _get(f"{API_URL}/api/incidents")
    incidents = data.get("data", []) if isinstance(data, dict) else data
    if args.min_confidence:
        incidents = [
            i for i in incidents
            if (i.get("confidence", {}) or {}).get("posterior", 0) >= args.min_confidence
        ]
    incidents = incidents[: args.limit]
    for i in incidents:
        conf = (i.get("confidence", {}) or {}).get("posterior", 0)
        print(f"{i.get('incident_id', '?'):<40}  {i.get('incident_type', '?'):<28}  "
              f"sev={i.get('severity', '?'):<8}  conf={conf:.2f}  "
              f"path={'->'.join(i.get('service_path') or [])}")


def cmd_replay(args) -> None:
    frames = _get(f"{ENGINE_URL}/engine/replay/{args.incident_id}").get("data", [])
    for f in frames:
        ev = f.get("event", {})
        delta = f.get("delta", {})
        print(f"[{f.get('ts', 0):.0f}] rule={f.get('rule')} "
              f"event={ev.get('event_type')}@{ev.get('source_service_name')} "
              f"+services={delta.get('new_services')} +techs={delta.get('new_techniques')}")


def cmd_explain(args) -> None:
    data = _get(f"{ENGINE_URL}/engine/incident/{args.incident_id}/explain").get("data", {})
    base = data.get("baseline", {})
    print(f"baseline posterior: {base.get('posterior')}")
    print(f"explanation:        {base.get('explanation')}")
    print(f"pivotal step idxs:  {data.get('pivotal_steps')}")
    print()
    print("counterfactuals:")
    for r in data.get("removed", []):
        flag = " *" if r.get("crossed_threshold") else "  "
        print(f"{flag} remove[{r['removed_index']}] {r.get('removed_stage')}@{r.get('removed_service')}: "
              f"posterior={r['posterior_without']:.3f} (Δ={r['delta']:+.3f})")


def cmd_diff(args) -> None:
    data = _get(f"{ENGINE_URL}/engine/incident/{args.left}/diff/{args.right}").get("data", {})
    _print_json(data)


def cmd_predict(_args) -> None:
    data = _get(f"{ENGINE_URL}/engine/predict-next").get("data", {})
    _print_json(data)


def cmd_drift(_args) -> None:
    try:
        data = _get("http://localhost:5080/topology/drift")
    except Exception:
        # may be remote
        data = {"error": "topology-collector unreachable"}
    _print_json(data)


def cmd_mitre(_args) -> None:
    data = _get(f"{ENGINE_URL}/engine/mitre-mapping").get("data", {})
    hits = data.get("technique_hits", {})
    rows = sorted(hits.items(), key=lambda kv: -kv[1])
    print(f"techniques observed: {data.get('total_techniques', 0)}")
    for tech, count in rows:
        print(f"  {tech:<10}  {count}")


def cmd_yaml_rules(_args) -> None:
    data = _get(f"{ENGINE_URL}/engine/yaml-rules").get("data", {})
    _print_json(data)


def cmd_threat_intel(args) -> None:
    if args.refresh:
        data = _post(f"{ENGINE_URL}/engine/threat-intel/refresh").get("data", {})
        print(f"refreshed: loaded {data.get('loaded', 0)} indicators")
        return
    data = _get(f"{ENGINE_URL}/engine/threat-intel").get("data", {})
    _print_json(data)


def cmd_stream_events(args) -> None:
    last_id = "$" if args.follow else "0"
    try:
        import redis  # type: ignore
    except Exception:
        print("error: 'redis' python client not installed", file=sys.stderr)
        sys.exit(1)
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = redis.Redis(host=host, port=port, decode_responses=True)
    while True:
        resp = r.xread({"securisphere:events": last_id}, block=2000, count=20)
        if not resp:
            if not args.follow:
                return
            continue
        for _stream, msgs in resp:
            for stream_id, fields in msgs:
                last_id = stream_id
                payload = fields.get("payload", "{}")
                try:
                    e = json.loads(payload)
                except Exception:
                    e = {"raw": payload}
                print(f"{stream_id}  {e.get('event_type')}  svc={e.get('source_service_name')}  sev={e.get('severity')}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(prog="securisphere")
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("status").set_defaults(func=cmd_status)

    sp = sub.add_parser("incidents")
    sp.add_argument("--limit", type=int, default=20)
    sp.add_argument("--min-confidence", type=float, default=0.0)
    sp.set_defaults(func=cmd_incidents)

    sp = sub.add_parser("replay")
    sp.add_argument("incident_id")
    sp.set_defaults(func=cmd_replay)

    sp = sub.add_parser("explain")
    sp.add_argument("incident_id")
    sp.set_defaults(func=cmd_explain)

    sp = sub.add_parser("diff")
    sp.add_argument("left")
    sp.add_argument("right")
    sp.set_defaults(func=cmd_diff)

    sub.add_parser("predict").set_defaults(func=cmd_predict)
    sub.add_parser("drift").set_defaults(func=cmd_drift)
    sub.add_parser("mitre").set_defaults(func=cmd_mitre)
    sub.add_parser("yaml-rules").set_defaults(func=cmd_yaml_rules)

    sp = sub.add_parser("threat-intel")
    sp.add_argument("--refresh", action="store_true")
    sp.set_defaults(func=cmd_threat_intel)

    sp = sub.add_parser("stream-events")
    sp.add_argument("--follow", action="store_true")
    sp.set_defaults(func=cmd_stream_events)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
