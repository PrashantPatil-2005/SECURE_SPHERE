"""Benchmark runner for SecuriSphere.

Drives a YAML scenario against the running engine, listens for the
resulting incidents on the correlated_incidents pub/sub channel, and
writes a JSON report under ``benchmarks/results/``.

Designed so that:
  - The runner has no engine-internal imports — talks to it over Redis +
    HTTP only, like a real client. So the report numbers reflect the
    end-to-end system, not a model unit-tested in isolation.
  - Scenarios are declarative. Adding a new scenario is one YAML file.
  - The output is machine-readable so ``benchmarks/report.py`` can build
    the paper's tables without re-running anything.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
import time
import uuid
from typing import Any, Dict, List, Optional


def _load_scenario(path: str) -> Dict[str, Any]:
    try:
        import yaml  # type: ignore
    except Exception:
        print("error: PyYAML required for scenarios. pip install pyyaml", file=sys.stderr)
        sys.exit(1)
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _connect_redis():
    try:
        import redis  # type: ignore
    except Exception:
        print("error: 'redis' python client not installed", file=sys.stderr)
        sys.exit(1)
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


def _send_event(r, event: Dict[str, Any]) -> None:
    """Publish to legacy pub/sub channel — bridge mirrors into the stream
    so we exercise the real production ingress path."""
    r.publish("security_events", json.dumps(event))


def _drain_incidents(r, since_ts: float, timeout: float) -> List[Dict[str, Any]]:
    """Pull incidents from the recent-incidents Redis list. We don't use
    pub/sub because we want at-least-once read after the run completes."""
    deadline = time.time() + timeout
    seen = set()
    out: List[Dict[str, Any]] = []
    while time.time() < deadline:
        raw_list = r.lrange("incidents", 0, 49) or []
        for raw in raw_list:
            try:
                inc = json.loads(raw)
            except Exception:
                continue
            iid = inc.get("incident_id")
            if not iid or iid in seen:
                continue
            try:
                detected = time.mktime(time.strptime(
                    inc.get("detected_at", "")[:19], "%Y-%m-%dT%H:%M:%S"
                ))
            except Exception:
                detected = 0.0
            if detected >= since_ts - 1:
                seen.add(iid)
                out.append(inc)
        time.sleep(0.5)
    return out


def _run_one(scenario: Dict[str, Any]) -> Dict[str, Any]:
    name = scenario["name"]
    events: List[Dict[str, Any]] = scenario.get("events") or []
    expected_chain: List[str] = scenario.get("expected_chain") or []
    settle_timeout = float(scenario.get("settle_timeout", 10.0))

    r = _connect_redis()
    started = time.time()

    for ev in events:
        ev = dict(ev)
        ev.setdefault("timestamp", time.strftime("%Y-%m-%dT%H:%M:%S"))
        ev.setdefault("event_id", str(uuid.uuid4()))
        delay = float(ev.pop("delay_after", 0.0))
        _send_event(r, ev)
        if delay > 0:
            time.sleep(delay)

    incidents = _drain_incidents(r, since_ts=started, timeout=settle_timeout)

    first_mttd = None
    if incidents:
        first_mttd = min(
            float(i.get("mttd_seconds") or 0.0) for i in incidents
        )

    observed_chain: List[str] = []
    for inc in incidents:
        for step in inc.get("kill_chain_steps") or []:
            stage = step.get("stage") if isinstance(step, dict) else None
            if stage and stage not in observed_chain:
                observed_chain.append(stage)

    completeness = 0.0
    if expected_chain:
        hit = len(set(expected_chain) & set(observed_chain))
        completeness = hit / len(expected_chain)

    return {
        "scenario":         name,
        "started_at":       time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(started)),
        "duration_seconds": time.time() - started,
        "events_sent":      len(events),
        "incidents":        [
            {
                "incident_id":   i.get("incident_id"),
                "incident_type": i.get("incident_type"),
                "mttd_seconds":  i.get("mttd_seconds"),
                "service_path":  i.get("service_path"),
                "confidence":    (i.get("confidence") or {}).get("posterior"),
            }
            for i in incidents
        ],
        "expected_chain":   expected_chain,
        "observed_chain":   observed_chain,
        "metrics": {
            "mttd_first_incident": first_mttd,
            "chain_completeness":  round(completeness, 3),
            "incidents_emitted":   len(incidents),
        },
    }


def _write_report(report: Dict[str, Any], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    fname = f"{report['scenario']}_{int(time.time())}.json"
    path = os.path.join(out_dir, fname)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, default=str)
    return path


def main() -> None:
    ap = argparse.ArgumentParser(prog="benchmarks.run")
    ap.add_argument("--scenario", help="Single scenario name (filename without .yaml)")
    ap.add_argument("--all", action="store_true", help="Run every scenario")
    ap.add_argument("--scenarios-dir", default=os.path.join(os.path.dirname(__file__), "scenarios"))
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "results"))
    args = ap.parse_args()

    if not args.scenario and not args.all:
        ap.error("specify --scenario NAME or --all")

    if args.all:
        paths = sorted(glob.glob(os.path.join(args.scenarios_dir, "*.yaml")))
    else:
        paths = [os.path.join(args.scenarios_dir, args.scenario + ".yaml")]

    for path in paths:
        if not os.path.exists(path):
            print(f"missing scenario: {path}", file=sys.stderr)
            continue
        scenario = _load_scenario(path)
        print(f"running: {scenario.get('name')} ({path})")
        report = _run_one(scenario)
        out_path = _write_report(report, args.out)
        print(f"  → {out_path}")
        print(f"  mttd={report['metrics']['mttd_first_incident']}  "
              f"completeness={report['metrics']['chain_completeness']}  "
              f"incidents={report['metrics']['incidents_emitted']}")


if __name__ == "__main__":
    main()
