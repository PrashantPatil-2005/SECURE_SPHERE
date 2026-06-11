#!/usr/bin/env python3
"""C1 churn resilience experiment (H1) — service vs legacy correlation.

Runs ``benchmarks/scenarios/recon_to_exfil_with_redeploy.yaml``, restarts
``auth-service`` mid-attack, and measures kill chain completeness + MTTD
from PostgreSQL ``kill_chains``.

Usage:
    python scripts/churn_experiment.py --mode both --seed 42
    python scripts/churn_experiment.py --mode service --seed 42
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Literal

# Ensure repo root is on sys.path when invoked as a script
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from evaluation.lib.docker_ctl import restart_service, set_correlation_mode
from evaluation.lib.metadata import build_result_envelope
from evaluation.lib.paths import project_root, results_dir
from evaluation.lib.postgres import (
    fetch_kill_chains_since,
    merge_kill_chain_steps,
)
from evaluation.lib.reset_state import reset_state
from evaluation.metrics.completeness import evaluate_completeness, reconstruct_chain_log
from evaluation.metrics.mttd import mean_mttd_seconds

logger = logging.getLogger("churn_experiment")

DEFAULT_SCENARIO = project_root() / "benchmarks" / "scenarios" / "recon_to_exfil_with_redeploy.yaml"


def load_scenario(path: Path) -> dict[str, Any]:
    """Load a YAML benchmark scenario.

    Args:
        path: Path to scenario file.

    Returns:
        Parsed scenario dict.
    """
    try:
        import yaml
    except ImportError as exc:
        raise SystemExit("PyYAML required: pip install pyyaml") from exc
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid scenario format: {path}")
    return data


def _connect_redis():
    """Return a Redis client from environment defaults."""
    try:
        import redis
    except ImportError as exc:
        raise SystemExit("redis package required") from exc
    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD") or None,
        decode_responses=True,
    )


def _send_event(redis_client, event: dict[str, Any]) -> None:
    """Publish one security event on the legacy pub/sub ingress path."""
    redis_client.publish("security_events", json.dumps(event))


def inject_events_with_churn(
    scenario: dict[str, Any],
    *,
    redis_client,
    on_churn: Callable[[dict[str, Any]], None] | None = None,
) -> float:
    """Inject scenario events, executing churn actions between steps.

    Args:
        scenario: Loaded scenario YAML dict.
        redis_client: Connected Redis client.
        on_churn: Optional callback invoked for each churn spec dict.

    Returns:
        Unix epoch timestamp when injection started.
    """
    events: list[dict[str, Any]] = list(scenario.get("events") or [])
    churn_specs: list[dict[str, Any]] = list(scenario.get("churn") or [])
    churn_by_after = {
        int(c.get("after_event", 0)): c
        for c in churn_specs
        if c.get("after_event") is not None
    }

    started = time.time()
    for idx, raw in enumerate(events, start=1):
        ev = dict(raw)
        ev.setdefault("timestamp", datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"))
        ev.setdefault("event_id", str(uuid.uuid4()))
        delay = float(ev.pop("delay_after", 0.0))
        _send_event(redis_client, ev)
        if idx in churn_by_after:
            spec = churn_by_after[idx]
            action = spec.get("action")
            if action == "restart_service":
                service = spec.get("service", "auth-service")
                logger.info("Churn: restarting %s after event %d", service, idx)
                restart_service(str(service))
            if on_churn:
                on_churn(spec)
        if delay > 0:
            time.sleep(delay)
    return started


def capture_kill_chain_from_postgres(
    since: datetime,
    *,
    dsn: str | None = None,
) -> dict[str, Any]:
    """Fetch and merge kill chains written since experiment start.

    Args:
        since: Lower bound on ``detected_at``.
        dsn: Unused; reserved for future DSN override.

    Returns:
        Dict with steps, mttd_seconds, chains, incident_ids.
    """
    del dsn
    chains = fetch_kill_chains_since(since)
    steps = merge_kill_chain_steps(chains)
    return {
        "kill_chain_steps": steps,
        "mttd_seconds": mean_mttd_seconds(chains),
        "chains": chains,
        "incident_count": len(chains),
        "incident_ids": [c.get("incident_id") for c in chains],
    }


def _wait_for_kill_chains(
    since: datetime,
    *,
    timeout_sec: float,
    poll_sec: float = 1.0,
) -> dict[str, Any]:
    """Poll Postgres until kill chains appear or timeout."""
    deadline = time.time() + timeout_sec
    last: dict[str, Any] = {
        "kill_chain_steps": [],
        "mttd_seconds": None,
        "chains": [],
        "incident_count": 0,
        "incident_ids": [],
    }
    while time.time() < deadline:
        last = capture_kill_chain_from_postgres(since)
        if last["kill_chain_steps"] or last["incident_count"] > 0:
            break
        time.sleep(poll_sec)
    return last


def run_single_mode(
    mode: Literal["service", "legacy"],
    scenario_path: Path,
    *,
    seed: int,
    reset: bool = True,
) -> dict[str, Any]:
    """Execute C1 for one correlation mode.

    Args:
        mode: ``service`` or ``legacy``.
        scenario_path: Path to scenario YAML.
        seed: Reproducibility seed (logged in output).
        reset: Clear system state before the run.

    Returns:
        Per-mode result dict with completeness, mttd, chain log.
    """
    del seed  # reserved for future deterministic event IDs
    scenario = load_scenario(scenario_path)
    if reset:
        reset_state(cooldown_sec=5.0)

    set_correlation_mode(mode, recreate_engine=True, warmup_sec=12.0)

    # Warm-up event (Section 25.2 — not counted in metrics)
    r = _connect_redis()
    _send_event(r, {
        "event_id": str(uuid.uuid4()),
        "event_type": "health_check",
        "severity": "low",
        "source_layer": "network",
        "source_service_name": "warmup",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    time.sleep(2.0)
    if reset:
        reset_state(cooldown_sec=3.0)

    since_dt = datetime.now(timezone.utc).replace(tzinfo=None)
    inject_events_with_churn(scenario, redis_client=r)

    settle = float(scenario.get("settle_timeout", 15.0))
    captured = _wait_for_kill_chains(since_dt, timeout_sec=settle + 30.0)

    expected = list(scenario.get("expected_kill_chain_steps") or [])
    actual_steps = captured["kill_chain_steps"]
    completeness = evaluate_completeness(actual_steps, expected)
    chain_log = reconstruct_chain_log(actual_steps, expected)

    return {
        "correlation_mode": mode,
        "completeness": completeness,
        "mttd_seconds": captured["mttd_seconds"],
        "incident_count": captured["incident_count"],
        "incident_ids": captured["incident_ids"],
        "chain_reconstruction_log": chain_log,
        "actual_step_count": len(actual_steps),
        "expected_step_count": len(expected),
    }


def _paired_ttest(a: list[float], b: list[float]) -> dict[str, float | None]:
    """Two-sample t-test p-value; returns empty if scipy unavailable."""
    if len(a) < 2 or len(b) < 2:
        return {"p_value": None, "t_statistic": None}
    try:
        from scipy import stats

        res = stats.ttest_ind(a, b, equal_var=False)
        return {
            "p_value": round(float(res.pvalue), 6),
            "t_statistic": round(float(res.statistic), 4),
        }
    except ImportError:
        return {"p_value": None, "t_statistic": None}


def run_comparison(
    scenario_path: Path,
    *,
    seed: int,
) -> dict[str, Any]:
    """Run service and legacy modes and compute comparison statistics.

    Args:
        scenario_path: Scenario YAML path.
        seed: Reproducibility seed.

    Returns:
        Full experiment result envelope.
    """
    service = run_single_mode("service", scenario_path, seed=seed, reset=True)
    legacy = run_single_mode("legacy", scenario_path, seed=seed, reset=True)

    comparison = {
        "delta_completeness": round(
            service["completeness"] - legacy["completeness"], 4
        ),
        "service_meets_target": service["completeness"] >= 0.90,
        "legacy_meets_target": legacy["completeness"] <= 0.40,
    }
    comparison.update(
        _paired_ttest(
            [service["completeness"]],
            [legacy["completeness"]],
        )
    )

    scenario = load_scenario(scenario_path)
    envelope = build_result_envelope(
        seed=seed,
        experiment="C1_churn_resilience",
        extra={
            "scenario": scenario.get("name", scenario_path.stem),
            "claim": scenario.get("claim", "C1"),
            "hypothesis": "H1",
            "modes": {
                "service": service,
                "legacy": legacy,
            },
            "comparison": comparison,
        },
    )
    return envelope


def write_result(result: dict[str, Any], out_dir: Path | None = None) -> Path:
    """Write JSON result artifact with ISO timestamp in filename.

    Args:
        result: Full result dict.
        out_dir: Output directory (default: evaluation/results).

    Returns:
        Path to written file.
    """
    out = out_dir or results_dir()
    out.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = out / f"c1_churn_{ts}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)
    return path


def print_comparison_table(result: dict[str, Any]) -> None:
    """Print side-by-side completeness + MTTD table (Table 5 preview)."""
    try:
        from tabulate import tabulate
    except ImportError:
        modes = result.get("modes", {})
        for name, data in modes.items():
            print(f"{name}: completeness={data.get('completeness')} mttd={data.get('mttd_seconds')}")
        return

    rows = []
    modes = result.get("modes", {})
    for label in ("service", "legacy"):
        m = modes.get(label, {})
        rows.append([
            label,
            m.get("completeness", "—"),
            m.get("mttd_seconds", "—"),
            m.get("incident_count", "—"),
            m.get("actual_step_count", "—"),
        ])
    print(tabulate(
        rows,
        headers=["Mode", "Completeness", "MTTD (s)", "Incidents", "Steps captured"],
        tablefmt="github",
    ))
    comp = result.get("comparison", {})
    print(
        f"\nΔ completeness: {comp.get('delta_completeness')}  "
        f"service ≥0.90: {comp.get('service_meets_target')}  "
        f"legacy ≤0.40: {comp.get('legacy_meets_target')}"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(
        description="C1 churn resilience experiment (H1): service vs legacy correlation.",
    )
    parser.add_argument(
        "--mode",
        choices=("service", "legacy", "both"),
        default="both",
        help="Correlation mode to run (default: both)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Reproducibility seed")
    parser.add_argument(
        "--scenario",
        type=Path,
        default=DEFAULT_SCENARIO,
        help="Path to scenario YAML",
    )
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Skip state reset before each mode run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output directory (default: evaluation/results)",
    )
    args = parser.parse_args(argv)

    if not args.scenario.is_file():
        print(f"Scenario not found: {args.scenario}", file=sys.stderr)
        return 1

    if args.mode == "both":
        result = run_comparison(args.scenario, seed=args.seed)
    else:
        mode_result = run_single_mode(
            args.mode,
            args.scenario,
            seed=args.seed,
            reset=not args.no_reset,
        )
        scenario = load_scenario(args.scenario)
        result = build_result_envelope(
            seed=args.seed,
            experiment="C1_churn_resilience",
            extra={
                "scenario": scenario.get("name"),
                "modes": {args.mode: mode_result},
            },
        )

    out_path = write_result(result, args.output)
    print_comparison_table(result)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
