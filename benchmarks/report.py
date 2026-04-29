"""Aggregate benchmark JSON reports into the paper's results table.

Reads every ``benchmarks/results/*.json``, groups by scenario, picks the
most-recent run per scenario, and prints a Markdown table that drops
straight into ``paper/sections/06_results.md``. Numbers are honest —
empty cells stay empty, no interpolation, no "expected" values.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from collections import defaultdict
from typing import Any, Dict, List


def _load_all(results_dir: str) -> List[Dict[str, Any]]:
    out = []
    for path in glob.glob(os.path.join(results_dir, "*.json")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                out.append(json.load(f))
        except Exception:
            continue
    return out


def _latest_per_scenario(reports: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by: Dict[str, Dict[str, Any]] = {}
    for r in reports:
        name = r.get("scenario") or "?"
        if name not in by or r.get("started_at", "") > by[name].get("started_at", ""):
            by[name] = r
    return by


def render_markdown(table: Dict[str, Dict[str, Any]]) -> str:
    lines = [
        "| Scenario | MTTD (s) | Chain completeness | Incidents | Confidence (mean) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for name in sorted(table):
        r = table[name]
        m = r.get("metrics", {})
        confs = [
            i.get("confidence") for i in (r.get("incidents") or [])
            if isinstance(i.get("confidence"), (int, float))
        ]
        mean_conf = round(sum(confs) / len(confs), 3) if confs else "—"
        lines.append(
            f"| `{name}` | "
            f"{m.get('mttd_first_incident', '—')} | "
            f"{m.get('chain_completeness', '—')} | "
            f"{m.get('incidents_emitted', '—')} | "
            f"{mean_conf} |"
        )
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", default=os.path.join(os.path.dirname(__file__), "results"))
    args = ap.parse_args()

    reports = _load_all(args.results)
    if not reports:
        print("No reports found. Run `python -m benchmarks.run --all` first.")
        return
    table = _latest_per_scenario(reports)
    print(render_markdown(table))


if __name__ == "__main__":
    main()
