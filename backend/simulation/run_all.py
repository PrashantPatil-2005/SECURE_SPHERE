"""
run_all.py — SecuriSphere Attack Orchestrator

Runs all three named attack scenarios (A, B, C) in sequence with a
configurable inter-scenario pause.  After each scenario it polls the
backend for newly created incidents and prints a summary table.

Usage
-----
  python run_all.py                # normal speed, all scenarios
  python run_all.py --scenario a   # only scenario A
  python run_all.py --speed demo   # slow mode for live demonstrations
  python run_all.py --delay 30     # 30-second pause between scenarios
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import requests
from colorama import Fore, Style, init

init(autoreset=True)

try:
    from scenarios.scenario_a_brute_force    import run as run_a
    from scenarios.scenario_b_recon_exploit  import run as run_b
    from scenarios.scenario_c_lateral_movement import run as run_c
except ImportError:
    # Allow running from repo root via docker exec
    sys.path.insert(0, "/app")
    from scenarios.scenario_a_brute_force    import run as run_a
    from scenarios.scenario_b_recon_exploit  import run as run_b
    from scenarios.scenario_c_lateral_movement import run as run_c

BACKEND_URL = "http://backend:8000"

# Execution-speed multiplier: higher value = longer inter-action delays.
# fast   → near-instant (CI / quick tests)
# normal → standard pacing (evaluation default)
# demo   → slightly slowed for live audience
# slow   → clearly visible for classroom walkthroughs
SPEED_MAP = {
    "fast":   0.05,
    "normal": 1.0,
    "demo":   1.5,
    "slow":   3.0,
}

# ─────────────────────────────────────────────────────────────────────────────


def _log(msg: str, color=Fore.WHITE) -> None:
    print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] [Orchestrator] {msg}{Style.RESET_ALL}")


def _print_summary(results: list) -> None:
    """Print a tabular summary of all scenario results."""
    print(f"\n{Fore.CYAN}{'═' * 70}")
    print(f"  SecuriSphere Attack Simulation — Results Summary")
    print(f"{'═' * 70}{Style.RESET_ALL}")
    header = f"{'Scenario':<45} {'Stages OK':<10} {'Detections':<12}"
    print(Fore.WHITE + header)
    print("-" * 70)
    for r in results:
        ok      = sum(1 for s in r.get("stages", []) if s.get("success"))
        total   = len(r.get("stages", []))
        detects = len(r.get("detections", []))
        name    = r.get("scenario", "?")[:44]
        color   = Fore.GREEN if detects > 0 else Fore.YELLOW
        print(f"{color}{name:<45} {ok}/{total:<9} {detects:<12}{Style.RESET_ALL}")

    # Pull overall backend metrics
    try:
        m = requests.get(f"{BACKEND_URL}/api/metrics", timeout=5).json().get("data", {})
        print(f"\n{Fore.CYAN}  Backend Metrics After Simulation:")
        print(f"    Raw Events   : {m.get('raw_events', {}).get('total', '?')}")
        print(f"    Incidents    : {m.get('correlated_incidents', '?')}")
        print(f"    Alert Reduction: {m.get('alert_reduction_percentage', '?')}%")

        # MTTD report
        mttd_resp = requests.get(f"{BACKEND_URL}/api/mttd/report", timeout=5)
        if mttd_resp.status_code == 200:
            mttd_data = mttd_resp.json().get("data", [])
            if mttd_data:
                print(f"\n  MTTD by Incident Type:")
                for row in mttd_data[:10]:
                    avg = row.get("avg_mttd_seconds")
                    avg_str = f"{avg:.2f}s" if avg is not None else "N/A"
                    print(f"    {row.get('incident_type', '?'):<40} avg: {avg_str}")
    except Exception as exc:
        print(f"{Fore.RED}  Metrics fetch error: {exc}{Style.RESET_ALL}")

    print(f"\n{Fore.CYAN}{'═' * 70}{Style.RESET_ALL}")


def main() -> None:
    parser = argparse.ArgumentParser(description="SecuriSphere Attack Orchestrator")
    parser.add_argument(
        "--scenario", "-s",
        choices=["a", "b", "c", "all"],
        default="all",
        help="Which scenario to run (default: all)",
    )
    parser.add_argument(
        "--speed",
        choices=["fast", "normal", "demo", "slow"],
        default=None,
        help="Execution speed: fast=0.05x, normal=1.0x, demo=1.5x, slow=3.0x delay",
    )
    parser.add_argument(
        "--delay", "-d",
        type=int,
        default=10,
        help="Seconds to pause between scenarios (default: 10)",
    )
    parser.add_argument(
        "--no-clear",
        action="store_true",
        help="Do not clear events between scenarios",
    )
    args = parser.parse_args()

    # CLI flag takes precedence; SPEED env var is the fallback; normal is the floor.
    speed_name = args.speed or os.getenv("SPEED", "normal")
    if speed_name not in SPEED_MAP:
        _log(f"Unknown speed '{speed_name}', falling back to 'normal'", Fore.YELLOW)
        speed_name = "normal"
    speed = SPEED_MAP[speed_name]

    _log(f"Orchestrator starting — speed={speed_name} ({speed}x), inter-scenario delay={args.delay}s")

    # Wait for services to be ready
    _log("Waiting for backend to be reachable…")
    for attempt in range(30):
        try:
            requests.get(f"{BACKEND_URL}/api/health", timeout=2)
            _log("Backend is ready", Fore.GREEN)
            break
        except Exception:
            time.sleep(2)
    else:
        _log("Backend not reachable after 60s — proceeding anyway", Fore.YELLOW)

    all_results = []

    scenario_map = {
        "a": ("Scenario A: Brute Force → Credential Compromise → Exfiltration", run_a),
        "b": ("Scenario B: Recon → SQL Injection → Privilege Escalation",       run_b),
        "c": ("Scenario C: Multi-Hop Lateral Movement",                          run_c),
    }

    to_run = list(scenario_map.keys()) if args.scenario == "all" else [args.scenario]

    for i, key in enumerate(to_run):
        label, fn = scenario_map[key]
        _log(f"Starting {label}", Fore.CYAN)

        if not args.no_clear:
            try:
                requests.post(f"{BACKEND_URL}/api/events/clear", timeout=3)
                _log("Events cleared", Fore.GREEN)
            except Exception:
                pass
            # Reset engine cooldowns so each scenario gets a fresh detection window
            engine_url = os.getenv("ENGINE_URL", "http://correlation-engine:5070")
            try:
                r = requests.post(f"{engine_url}/engine/reset", timeout=5)
                d = r.json()
                _log(
                    f"Engine reset — {d.get('cleared_cooldowns', '?')} cooldowns, "
                    f"{d.get('cleared_events', '?')} buffered events cleared",
                    Fore.GREEN,
                )
            except Exception as exc:
                _log(f"Engine reset failed (non-fatal): {exc}", Fore.YELLOW)

        try:
            result = fn(delay_multiplier=speed)
            all_results.append(result)
        except Exception as exc:
            _log(f"Scenario {key.upper()} error: {exc}", Fore.RED)
            all_results.append({"scenario": label, "stages": [], "detections": []})

        if i < len(to_run) - 1:
            _log(f"Pausing {args.delay}s before next scenario…", Fore.YELLOW)
            time.sleep(args.delay)

    _print_summary(all_results)

    # Persist results to a JSON file for CI/reporting
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"/app/results/simulation_{ts}.json"
    try:
        os.makedirs("/app/results", exist_ok=True)
        with open(out_file, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        _log(f"Results saved to {out_file}", Fore.GREEN)
    except Exception as exc:
        _log(f"Could not save results: {exc}", Fore.YELLOW)


if __name__ == "__main__":
    main()
