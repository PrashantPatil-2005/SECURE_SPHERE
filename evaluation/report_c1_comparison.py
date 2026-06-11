"""Render C1 churn comparison table for paper Table 5."""

from __future__ import annotations

import argparse
import json
from glob import glob
from pathlib import Path

from evaluation.lib.paths import project_root, results_dir


def _latest_c1_result(search_dir: Path) -> dict | None:
    """Load the most recent c1_churn_*.json file."""
    paths = sorted(glob(str(search_dir / "c1_churn_*.json")))
    if not paths:
        return None
    with open(paths[-1], encoding="utf-8") as f:
        return json.load(f)


def render_table_5(result: dict) -> str:
    """Generate LaTeX tabular for Table 5.

    Args:
        result: C1 experiment JSON envelope.

    Returns:
        LaTeX table body string.
    """
    modes = result.get("modes", {})
    svc = modes.get("service", {})
    leg = modes.get("legacy", {})
    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{C1 Churn Resilience: Kill Chain Completeness Under Mid-Attack Container Restart}",
        r"\label{tab:c1-churn}",
        r"\begin{tabular}{lccc}",
        r"\toprule",
        r"Mode & Completeness & MTTD (s) & Incidents \\",
        r"\midrule",
        f"Service-identity & {svc.get('completeness', '—')} & "
        f"{svc.get('mttd_seconds', '—')} & {svc.get('incident_count', '—')} \\\\",
        f"IP (legacy) & {leg.get('completeness', '—')} & "
        f"{leg.get('mttd_seconds', '—')} & {leg.get('incident_count', '—')} \\\\",
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI: print Table 5 LaTeX from latest C1 result."""
    parser = argparse.ArgumentParser(description="Render C1 comparison as LaTeX Table 5.")
    parser.add_argument("--input", type=Path, help="Specific c1_churn JSON file")
    parser.add_argument("--out", type=Path, help="Write .tex file (default: stdout only)")
    args = parser.parse_args(argv)

    if args.input:
        with args.input.open(encoding="utf-8") as f:
            result = json.load(f)
    else:
        result = _latest_c1_result(results_dir())
        if not result:
            print("No c1_churn_*.json found. Run: make run-c1")
            return 1

    tex = render_table_5(result)
    print(tex)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(tex, encoding="utf-8")
        print(f"\nWrote {args.out}")
    else:
        default = project_root() / "paper" / "tables" / "table_5.tex"
        default.parent.mkdir(parents=True, exist_ok=True)
        default.write_text(tex, encoding="utf-8")
        print(f"\nWrote {default}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
