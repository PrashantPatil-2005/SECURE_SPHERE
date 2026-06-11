"""Reset SecuriSphere state between experiment trials (idempotent)."""

from __future__ import annotations

import argparse
import os
import time

import requests

BACKEND_URL = os.getenv("SECURISPHERE_BACKEND_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))
ENGINE_URL = os.getenv("SECURISPHERE_ENGINE_URL", os.getenv("ENGINE_URL", "http://localhost:5070"))
AUTH_URL = os.getenv("SECURISPHERE_AUTH_URL", os.getenv("AUTH_URL", "http://localhost:5001"))
AUTHMON_URL = os.getenv("SECURISPHERE_AUTHMON_URL", "http://localhost:5060")


def reset_state(*, cooldown_sec: float = 3.0) -> None:
    """Clear events, incidents, engine buffers, and auth tracker.

    Args:
        cooldown_sec: Pause after reset before the next trial starts.
    """
    endpoints = (
        (f"{BACKEND_URL}/api/events/clear", "POST"),
        (f"{AUTH_URL}/auth/reset-all", "POST"),
        (f"{ENGINE_URL}/engine/reset", "POST"),
        (f"{AUTHMON_URL}/monitor/reset", "POST"),
    )
    for url, method in endpoints:
        try:
            requests.request(method, url, timeout=5)
        except requests.RequestException:
            pass
    try:
        requests.post(f"{ENGINE_URL}/engine/clear-buffer", timeout=2)
    except requests.RequestException:
        pass
    if cooldown_sec > 0:
        time.sleep(cooldown_sec)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for ``make reset-state``."""
    parser = argparse.ArgumentParser(
        description="Reset SecuriSphere experiment state (Postgres incidents, Redis, engine buffers).",
    )
    parser.add_argument("--seed", type=int, default=42, help="Recorded in logs only (reproducibility).")
    parser.add_argument("--cooldown", type=float, default=3.0, help="Seconds to wait after reset.")
    args = parser.parse_args(argv)
    reset_state(cooldown_sec=args.cooldown)
    print(f"State reset complete (seed={args.seed}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
