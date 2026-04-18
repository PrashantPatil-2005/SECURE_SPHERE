"""
run_attack_trials.py - Phase 16 reproducibility trial runner.

Drives SecuriSphere attack scenarios three times each (or the benign
baseline), captures per-trial incident deltas + MTTD from the backend
``/api/kill-chains`` endpoint, and writes a structured report to
``evaluation/trial_report.json``.

Exit code is non-zero when an attack scenario produces zero new incidents
(silent failure) or when the benign scenario produces >0 incidents (false
positive), so the script is CI-safe.

Usage:
    python scripts/run_attack_trials.py --scenario a
    python scripts/run_attack_trials.py --scenario all
    python scripts/run_attack_trials.py --scenario benign --runs 3

Environment variables:
    SECURISPHERE_BACKEND_URL   default: http://localhost:8000
    SECURISPHERE_ENGINE_URL    default: http://localhost:5070
    SECURISPHERE_AUTH_URL      default: http://localhost:5001
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

BACKEND_URL = os.getenv("SECURISPHERE_BACKEND_URL", "http://localhost:8000")
ENGINE_URL  = os.getenv("SECURISPHERE_ENGINE_URL",  "http://localhost:5070")
AUTH_URL    = os.getenv("SECURISPHERE_AUTH_URL",    "http://localhost:5001")
AUTHMON_URL = os.getenv("SECURISPHERE_AUTHMON_URL", "http://localhost:5060")
API_URL     = os.getenv("SECURISPHERE_API_URL",     "http://localhost:5000")
SCENARIOS   = ("a", "b", "c", "benign")

# Module-invocation per scenario. Fast speed cuts wall-clock ~5× without
# changing detection semantics (inter-stage sleeps shrink, requests identical).
COMMANDS: dict[str, list[str]] = {
    "a":      [sys.executable, "-m", "attacker.scenario_a", "--speed", "fast"],
    "b":      [sys.executable, "-m", "attacker.scenario_b", "--speed", "fast"],
    "c":      [sys.executable, "-m", "attacker.scenario_c", "--speed", "fast"],
    # Benign: simple health + public product checks (no auth, no injection)
    "benign": [
        sys.executable, "-c",
        "import requests, time, os; api=os.getenv('SECURISPHERE_API_URL','http://localhost:5000'); "
        "[requests.get(f'{api}/api/health', timeout=3) or time.sleep(0.5) for _ in range(5)]; "
        "[requests.get(f'{api}/api/products/search', params={'q': t}, timeout=3) or time.sleep(0.8) "
        " for t in ['laptop','phone','tablet','keyboard']]; "
        "requests.get(f'{api}/api/products', timeout=3)",
    ],
}

GRACE_SECONDS = 25           # correlation-engine flush + kill-chain persist
RESET_COOLDOWN_SECONDS = 3   # brief pause after reset before next trial
POLL_INTERVAL = 3            # re-check kill-chains every N seconds during grace


def _reset_backend_state() -> None:
    """Clear events, auth tracker, engine cooldown so each trial is isolated."""
    for url, method in (
        (f"{BACKEND_URL}/api/events/clear",  "POST"),
        (f"{AUTH_URL}/auth/reset-all",        "POST"),
        (f"{ENGINE_URL}/engine/reset",        "POST"),   # clears 5-min per-IP cooldown
        (f"{AUTHMON_URL}/monitor/reset",      "POST"),   # flush ip_failures + alert cooldowns
    ):
        try:
            requests.request(method, url, timeout=3)
        except requests.RequestException:
            pass


def _fetch_kill_chains(limit: int = 50) -> list[dict[str, Any]]:
    try:
        r = requests.get(f"{BACKEND_URL}/api/kill-chains?limit={limit}", timeout=5)
        data = r.json().get("data") or {}
        chains = data.get("kill_chains") or []
        return chains if isinstance(chains, list) else []
    except Exception:
        return []


def _ids(chains: list[dict[str, Any]]) -> set[str]:
    return {c.get("incident_id") for c in chains if c.get("incident_id")}


def _run_one_trial(scenario: str, trial_idx: int) -> dict[str, Any]:
    cmd = COMMANDS[scenario]
    before = _fetch_kill_chains()
    before_ids = _ids(before)
    t0 = time.time()
    started = datetime.now(timezone.utc).isoformat()

    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
            env=env, encoding="utf-8", errors="replace",
        )
        exit_code = proc.returncode
        stderr_tail = (proc.stderr or "").strip().splitlines()[-5:]
    except subprocess.TimeoutExpired:
        exit_code = -1
        stderr_tail = ["TimeoutExpired after 300s"]

    scenario_secs = round(time.time() - t0, 2)

    # Poll until new chains appear or overall grace window elapses. Keeps
    # wall-clock short on fast-responding stacks while still waiting long
    # enough for the kill-chain reconstructor on the slow path.
    after: list[dict[str, Any]] = []
    new_ids: set[str] = set()
    deadline = time.time() + GRACE_SECONDS
    while True:
        after = _fetch_kill_chains()
        after_ids = _ids(after)
        new_ids = after_ids - before_ids
        # Benign scenario: keep polling the full window so we never miss
        # a late-arriving false positive.
        if new_ids and scenario != "benign":
            break
        if time.time() >= deadline:
            break
        time.sleep(POLL_INTERVAL)

    new_chains = [c for c in after if c.get("incident_id") in new_ids]

    mttds = [
        float(c.get("mttd_seconds"))
        for c in new_chains
        if c.get("mttd_seconds") is not None
    ]
    mttd_avg = round(statistics.fmean(mttds), 3) if mttds else None

    severities = sorted({c.get("severity") for c in new_chains if c.get("severity")})
    techniques = sorted({
        t for c in new_chains for t in (c.get("mitre_techniques") or [])
    })
    service_path_max = max(
        (len(c.get("service_path") or []) for c in new_chains),
        default=0,
    )

    return {
        "trial":              trial_idx,
        "scenario":           scenario,
        "started_at":         started,
        "scenario_seconds":   scenario_secs,
        "exit_code":          exit_code,
        "new_incidents":      len(new_ids),
        "incident_ids":       sorted(new_ids),
        "mttd_seconds_avg":   mttd_avg,
        "mttd_seconds_all":   mttds,
        "severities":         severities,
        "mitre_techniques":   techniques,
        "max_service_path":   service_path_max,
        "stderr_tail":        stderr_tail,
    }


def _verdict(scenario: str, trials: list[dict[str, Any]]) -> dict[str, Any]:
    """Each scenario has its own pass criteria."""
    total_new = sum(t["new_incidents"] for t in trials)
    runs = len(trials)
    if scenario == "benign":
        ok = total_new == 0
        reason = (
            "benign scenario produced 0 incidents across all runs"
            if ok
            else f"benign scenario produced {total_new} incident(s) - false positive"
        )
    else:
        min_per_run = min(t["new_incidents"] for t in trials)
        mttds = [t["mttd_seconds_avg"] for t in trials if t["mttd_seconds_avg"] is not None]
        ok = min_per_run >= 1 and len(mttds) == runs
        reason = (
            f"every trial produced >=1 incident and measurable MTTD (avg "
            f"{round(statistics.fmean(mttds), 3)}s across {runs} runs)"
            if ok
            else f"min-per-trial={min_per_run}, runs-with-MTTD={len(mttds)}/{runs}"
        )
    return {"pass": ok, "reason": reason, "total_new_incidents": total_new}


def _print_table(scenario: str, trials: list[dict[str, Any]]) -> None:
    print(f"\n=== Scenario {scenario.upper()} - {len(trials)} trial(s) ===")
    print(f"{'#':>2}  {'new_inc':>7}  {'mttd(s)':>8}  {'elapsed':>7}  {'exit':>4}  mitre")
    for t in trials:
        mttd = "-" if t["mttd_seconds_avg"] is None else f"{t['mttd_seconds_avg']:.2f}"
        mitre = ",".join(t["mitre_techniques"]) or "-"
        print(
            f"{t['trial']:>2}  "
            f"{t['new_incidents']:>7}  "
            f"{mttd:>8}  "
            f"{t['scenario_seconds']:>7}  "
            f"{t['exit_code']:>4}  "
            f"{mitre}"
        )


def run_scenario(scenario: str, runs: int) -> dict[str, Any]:
    trials: list[dict[str, Any]] = []
    for i in range(1, runs + 1):
        _reset_backend_state()
        time.sleep(RESET_COOLDOWN_SECONDS)
        trials.append(_run_one_trial(scenario, i))
    _print_table(scenario, trials)
    verdict = _verdict(scenario, trials)
    print(f"    -> {'PASS' if verdict['pass'] else 'FAIL'}: {verdict['reason']}")
    return {"scenario": scenario, "runs": runs, "trials": trials, "verdict": verdict}


def main() -> int:
    parser = argparse.ArgumentParser(description="SecuriSphere attack reproducibility trials")
    parser.add_argument("--scenario", choices=list(SCENARIOS) + ["all"], default="all")
    parser.add_argument("--runs", type=int, default=3, help="Trials per scenario (default 3)")
    parser.add_argument("--report", default="evaluation/trial_report.json")
    args = parser.parse_args()

    targets = SCENARIOS[:3] if args.scenario == "all" else (args.scenario,)
    results: list[dict[str, Any]] = []
    for sc in targets:
        results.append(run_scenario(sc, args.runs))

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "backend_url":  BACKEND_URL,
        "runs_per_scenario": args.runs,
        "scenarios":    results,
        "overall_pass": all(r["verdict"]["pass"] for r in results),
    }
    out = Path(args.report)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out}")
    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
