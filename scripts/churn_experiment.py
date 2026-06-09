#!/usr/bin/env python3
"""Measure kill-chain completeness with service-centric correlation under churn."""

from __future__ import annotations

import argparse
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "backend", "engine"))

from shared.event_schema import normalize_event, filter_buffer_by_actor  # noqa: E402


def simulate_chain(events: list, mode: str = "service") -> list:
    """Return unique service_path steps correlated under *mode*."""
    path = []
    for i, ev in enumerate(events):
        ev = normalize_event(ev)
        prior = filter_buffer_by_actor(events[:i], ev, mode=mode)
        svc = ev.get("destination_service_name") or ev.get("source_service_name")
        if svc and (not path or path[-1] != svc):
            path.append(svc)
        if prior:
            for p in prior:
                ps = p.get("destination_service_name")
                if ps and ps not in path:
                    path.append(ps)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="benchmarks/scenarios/recon_to_exfil_with_redeploy.yaml")
    parser.add_argument("--min-completeness", type=float, default=0.9)
    args = parser.parse_args()

    try:
        import yaml
    except ImportError:
        print("pyyaml required: pip install pyyaml")
        return 1

    path = os.path.join(ROOT, args.scenario)
    with open(path, encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    events = spec.get("events", [])
    expected = len(spec.get("expected_chain", []))
    service_path = simulate_chain(events, mode="service")
    legacy_path = simulate_chain(events, mode="legacy")
    completeness = len(service_path) / max(expected, 1)

    report = {
        "scenario": spec.get("name"),
        "service_path": service_path,
        "legacy_path": legacy_path,
        "completeness": round(completeness, 3),
        "pass": completeness >= args.min_completeness,
    }
    print(json.dumps(report, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
