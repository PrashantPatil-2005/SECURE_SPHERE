#!/usr/bin/env python3
"""Throughput / latency benchmark (E3) — Figure 8 data.

Injects synthetic events at configurable rates, measures P50/P95/P99
detection latency, and finds the saturation point.

Usage:
    python benchmarks/load_test.py --seed 42
    python benchmarks/load_test.py --rates 100,500,1000 --events-per-rate 200
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from benchmarks.lib.event_generator import generate_event
from benchmarks.lib.latency_probe import publish_event, wait_for_incident
from evaluation.lib.metadata import build_result_envelope, get_git_commit_hash
from evaluation.lib.paths import benchmarks_results_dir
from evaluation.metrics.latency import percentile_ms

DEFAULT_RATES = [100, 500, 1000, 2000, 3000, 5000]
SEED = 42


def _connect_redis():
    import redis

    return redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )


def run_rate_trial(
    eps: int,
    *,
    n_events: int = 1000,
    seed: int = 42,
    timeout_per_event: float = 10.0,
) -> dict:
    """Run one throughput rate trial.

    Args:
        eps: Target events per second (injection rate).
        n_events: Number of events to inject.
        seed: RNG seed for reproducibility.
        timeout_per_event: Max seconds to wait per event for detection.

    Returns:
        Dict with eps, p50_ms, p95_ms, p99_ms, n_ok, n_timeout.
    """
    rng = random.Random(seed + eps)
    r = _connect_redis()
    interval = 1.0 / max(eps, 1)
    latencies: list[float] = []
    n_timeout = 0

    for _ in range(n_events):
        ev = generate_event(rng)
        d = ev.to_dict()
        pub_ts = time.time()
        d["client_publish_ts"] = pub_ts
        publish_event(r, d)
        lat = wait_for_incident(
            r,
            since_ts=pub_ts,
            timeout_sec=timeout_per_event,
            event_id=d["event_id"],
        )
        if lat is None:
            n_timeout += 1
        else:
            latencies.append(lat)
        elapsed = time.time() - pub_ts
        sleep_for = interval - elapsed
        if sleep_for > 0:
            time.sleep(sleep_for)

    return {
        "eps": eps,
        "p50_ms": percentile_ms(latencies, 50),
        "p95_ms": percentile_ms(latencies, 95),
        "p99_ms": percentile_ms(latencies, 99),
        "n_ok": len(latencies),
        "n_timeout": n_timeout,
        "n_events": n_events,
    }


def find_saturation_point(
    results: list[dict],
    *,
    multiplier: float = 2.0,
) -> int | None:
    """First rate where P99 exceeds multiplier × baseline P99.

    Args:
        results: Ordered list of per-rate trial dicts.
        multiplier: Saturation threshold factor.

    Returns:
        eps value at saturation, or None.
    """
    if not results:
        return None
    baseline = results[0].get("p99_ms") or 1.0
    threshold = baseline * multiplier
    for row in results[1:]:
        p99 = row.get("p99_ms") or 0.0
        if p99 > threshold:
            return int(row["eps"])
    return None


def write_csv(results: list[dict], out_path: Path) -> Path:
    """Write throughput results CSV.

    Args:
        results: Per-rate metrics.
        out_path: Destination path.

    Returns:
        Written path.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["eps", "p50_ms", "p95_ms", "p99_ms", "n_ok", "n_timeout", "n_events"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k) for k in fields})
    return out_path


def plot_latency_curve(results: list[dict], out_path: Path) -> Path | None:
    """Render latency-vs-throughput PNG at 300 DPI (Figure 8).

    Args:
        results: Per-rate metrics.
        out_path: PNG output path.

    Returns:
        Path if matplotlib available, else None.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    eps = [r["eps"] for r in results]
    p50 = [r["p50_ms"] for r in results]
    p95 = [r["p95_ms"] for r in results]
    p99 = [r["p99_ms"] for r in results]

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(eps, p50, marker="o", label="P50")
    ax.plot(eps, p95, marker="s", label="P95")
    ax.plot(eps, p99, marker="^", label="P99")
    ax.set_xlabel("Events per second")
    ax.set_ylabel("Detection latency (ms)")
    ax.set_title("SecuriSphere Throughput Benchmark (E3)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return out_path


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="E3 throughput / latency benchmark.")
    parser.add_argument("--seed", type=int, default=SEED, help="RNG seed (default: 42)")
    parser.add_argument(
        "--rates",
        type=str,
        default=",".join(str(x) for x in DEFAULT_RATES),
        help="Comma-separated events/sec rates",
    )
    parser.add_argument(
        "--events-per-rate",
        type=int,
        default=1000,
        help="Events injected per rate (default: 1000)",
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Smoke mode: 50 events per rate, rates 100,500,1000 only",
    )
    args = parser.parse_args(argv)

    if args.quick:
        rates = [100, 500, 1000]
        n_events = 50
    else:
        rates = [int(x.strip()) for x in args.rates.split(",") if x.strip()]
        n_events = args.events_per_rate

    print(f"Throughput benchmark seed={args.seed} rates={rates}")
    results: list[dict] = []
    for eps in rates:
        print(f"  Running {eps} eps × {n_events} events…", flush=True)
        row = run_rate_trial(eps, n_events=n_events, seed=args.seed)
        results.append(row)
        print(f"    P50={row['p50_ms']}ms P99={row['p99_ms']}ms timeouts={row['n_timeout']}")

    saturation = find_saturation_point(results)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = benchmarks_results_dir()
    csv_path = write_csv(results, out_dir / f"throughput_{ts}.csv")
    png_path = plot_latency_curve(results, out_dir / f"throughput_{ts}.png")

    summary = build_result_envelope(
        seed=args.seed,
        experiment="E3_throughput",
        extra={
            "rates": results,
            "saturation_eps": saturation,
            "git_commit_hash": get_git_commit_hash(),
            "csv_path": str(csv_path),
            "png_path": str(png_path) if png_path else None,
        },
    )
    json_path = out_dir / f"throughput_{ts}.json"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\nWrote {csv_path}")
    if png_path:
        print(f"Wrote {png_path}")
    print(f"Saturation point (P99 > 2× baseline): {saturation} eps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
