"""
traffic_generator.py — Realistic background-noise generator.

Produces benign and low-level suspicious HTTP traffic against the SecuriSphere
targets so attack-scenario detections must rise above a noisy baseline.

Use as a standalone script:
    python -m attacker.traffic_generator --duration 60
Or as a context-manager from a scenario:
    with traffic_generator.background(rate=3):
        run_scenario()
"""

from __future__ import annotations

import argparse
import random
import threading
import time
from contextlib import contextmanager

from attacker.common import API_URL, AUTH_URL, Fore, log, req

# Benign browsing endpoints (the normal user journey)
BENIGN_ENDPOINTS = [
    "/api/health",
    "/api/products",
    "/api/products/search?q=laptop",
    "/api/products/search?q=phone",
    "/api/products/search?q=shoes",
    "/api/products/1",
    "/api/products/42",
]

# Low-level suspicious but non-incident-triggering activity
LOW_NOISE = [
    "/api/products/search?q=test%20test",
    "/api/products/search?q=abc123",
    "/api/files?name=readme.txt",
]

# Benign logins — valid credentials only (must match auth-service seed data
# in backend/targets/auth-service/app.py). Repeated failures from a single
# source would eventually trip the auth-monitor brute-force rule (5 failures
# in 120 s), contaminating benign-baseline runs with false positives.
BENIGN_LOGINS = [
    ("john",  "password123"),
    ("jane",  "jane2024"),
    ("bob",   "bobsecure"),
    ("alice", "alice789"),
]


def _one_cycle() -> None:
    # 80% benign browsing, 17% low-noise GETs, 3% valid logins.
    # Auth share kept below the brute-force threshold budget even across
    # long sessions so the benign baseline produces 0 incidents.
    r = random.random()
    if r < 0.8:
        ep = random.choice(BENIGN_ENDPOINTS)
        req("GET", f"{API_URL}{ep}", timeout=2)
    elif r < 0.97:
        ep = random.choice(LOW_NOISE)
        req("GET", f"{API_URL}{ep}", timeout=2)
    else:
        username, password = random.choice(BENIGN_LOGINS)
        req(
            "POST",
            f"{AUTH_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=2,
        )


def run(duration: float = 60.0, rate: float = 2.0, verbose: bool = False) -> int:
    """Run noise for *duration* seconds at *rate* requests/sec.

    Returns number of requests issued.
    """
    end = time.time() + duration
    sent = 0
    interval = 1.0 / max(rate, 0.1)
    while time.time() < end:
        _one_cycle()
        sent += 1
        if verbose and sent % 10 == 0:
            log("Noise", f"{sent} requests dispatched", Fore.BLUE)
        # Jitter so requests are not perfectly periodic
        time.sleep(interval * random.uniform(0.6, 1.4))
    if verbose:
        log("Noise", f"done — {sent} requests in {duration:.0f}s", Fore.BLUE)
    return sent


@contextmanager
def background(rate: float = 2.0, verbose: bool = False):
    """Context manager: run noise continuously in a daemon thread until exit."""
    stop = threading.Event()

    def _loop():
        interval = 1.0 / max(rate, 0.1)
        while not stop.is_set():
            _one_cycle()
            stop.wait(interval * random.uniform(0.6, 1.4))

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    if verbose:
        log("Noise", f"background generator started ({rate} rps)", Fore.BLUE)
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=2)
        if verbose:
            log("Noise", "background generator stopped", Fore.BLUE)


def main() -> None:
    parser = argparse.ArgumentParser(description="SecuriSphere traffic noise generator")
    parser.add_argument("--duration", type=float, default=60.0, help="Seconds to run")
    parser.add_argument("--rate",     type=float, default=2.0,  help="Requests per second")
    parser.add_argument("--quiet",    action="store_true")
    args = parser.parse_args()
    run(duration=args.duration, rate=args.rate, verbose=not args.quiet)


if __name__ == "__main__":
    main()
