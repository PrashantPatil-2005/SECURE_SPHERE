"""
scenario_a_brute_force.py — SecuriSphere Attack Scenario A

Scenario A: Brute Force → Credential Compromise → Data Exfiltration

Attack narrative
----------------
1. Attacker discovers the auth endpoint and runs a dictionary attack against
   the ``admin`` account.
2. After multiple failures trigger an account lockout the attacker resets and
   tries a known-bad credential list.
3. Upon success the compromised session is used to hit two sensitive exfil
   endpoints, completing the kill chain:
       auth-service → auth-service → api-server

Expected detections
-------------------
- brute_force (auth-monitor)
- credential_compromise (correlation-engine)
- data_exfiltration_risk (correlation-engine)

MITRE ATT&CK mapping
---------------------
  T1110   Brute Force
  T1078   Valid Accounts (post-compromise)
  T1530   Data from Cloud Storage Object (exfil via admin endpoint)
"""

import time
import requests
from datetime import datetime
from colorama import Fore, Style

# ─────────────────────────────────────────────────────────────────────────────

AUTH_URL    = "http://auth-service:5001"
API_URL     = "http://api-server:5000"
BACKEND_URL = "http://backend:8000"

DELAY = 0.4   # seconds between individual requests

# ─────────────────────────────────────────────────────────────────────────────


def log(msg: str, color=Fore.WHITE) -> None:
    print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] [Scenario-A] {msg}{Style.RESET_ALL}")


def reset_auth() -> None:
    """Reset all auth accounts so the attack can start from a clean state."""
    try:
        requests.post(f"{AUTH_URL}/auth/reset-all", timeout=5)
        log("Auth accounts reset", Fore.GREEN)
    except Exception as exc:
        log(f"Reset failed: {exc}", Fore.RED)


def run(delay_multiplier: float = 1.0) -> dict:
    """
    Execute Scenario A and return a result dict with detection summary.

    Parameters
    ----------
    delay_multiplier:
        1.0 = normal speed; 3.0 = demo/slow mode; 0.3 = fast mode.
    """
    d = DELAY * delay_multiplier
    results: dict = {
        "scenario":  "A — Brute Force → Credential Compromise → Data Exfiltration",
        "start_time": datetime.now().isoformat(),
        "stages":    [],
        "detections": [],
    }

    print(Fore.CYAN + "╔══════════════════════════════════════════════════╗")
    print(Fore.CYAN + "║  Scenario A: Brute Force → Exfiltration          ║")
    print(Fore.CYAN + "╚══════════════════════════════════════════════════╝" + Style.RESET_ALL)

    reset_auth()
    time.sleep(2)

    # ── Stage 1: Dictionary brute force ────────────────────────────────────
    log("Stage 1 — Dictionary Brute Force against 'admin'", Fore.YELLOW)
    passwords = ["123456", "password", "admin", "welcome", "letmein",
                 "qwerty", "abc123", "monkey", "1234567", "dragon"]
    success_pass = None

    for pwd in passwords:
        try:
            r = requests.post(
                f"{AUTH_URL}/auth/login",
                json={"username": "admin", "password": pwd},
                timeout=3,
            )
            data = r.json()
            if data.get("status") == "success":
                log(f"  ✅ admin:{pwd} — LOGIN SUCCESS", Fore.RED)
                success_pass = pwd
                break
            else:
                locked = "locked" in r.text.lower()
                log(f"  ❌ admin:{pwd} — {'LOCKED' if locked else 'failed'}", Fore.YELLOW)
                if locked:
                    # Reset and continue to trigger more brute-force events
                    requests.post(f"{AUTH_URL}/auth/reset/admin", timeout=3)
        except Exception as exc:
            log(f"  Error: {exc}", Fore.RED)
        time.sleep(d)

    results["stages"].append({
        "name":    "brute_force",
        "success": success_pass is not None,
        "detail":  f"Tried {len(passwords)} passwords; success={'yes' if success_pass else 'no'}",
    })

    # ── Stage 2: Credential stuffing (different usernames) ─────────────────
    log("Stage 2 — Credential Stuffing from known breach database", Fore.YELLOW)
    stuffing_pairs = [
        ("alice",    "alice123"),
        ("bob",      "bobpass"),
        ("charlie",  "charlie!"),
        ("diana",    "diana2024"),
        ("eve",      "eve@home"),
        ("john",     "password123"),  # valid credential in auth-service seed
    ]
    stuffing_success = False
    for username, password in stuffing_pairs:
        try:
            r = requests.post(
                f"{AUTH_URL}/auth/login",
                json={"username": username, "password": password},
                timeout=3,
            )
            status = r.json().get("status", "?")
            log(f"  {username}:{password} → {status}", Fore.YELLOW if status != "success" else Fore.RED)
            if status == "success":
                stuffing_success = True
        except Exception:
            pass
        time.sleep(d)

    results["stages"].append({
        "name":    "credential_stuffing",
        "success": stuffing_success,
        "detail":  f"Tried {len(stuffing_pairs)} credential pairs",
    })

    # ── Stage 3: Wait so correlation window accumulates events ─────────────
    log("Stage 3 — Waiting for correlation engine…", Fore.CYAN)
    time.sleep(max(3.0, d * 4))

    # ── Stage 4: Data exfiltration via sensitive endpoints ─────────────────
    log("Stage 4 — Accessing sensitive data endpoints (exfiltration)", Fore.RED)
    exfil_endpoints = [
        "/api/admin/config",
        "/api/admin/users/export",
    ]
    for ep in exfil_endpoints:
        try:
            requests.get(f"{API_URL}{ep}", timeout=3)
            log(f"  Fetched {ep}", Fore.RED)
        except Exception as exc:
            log(f"  Error hitting {ep}: {exc}", Fore.YELLOW)
        time.sleep(d)

    results["stages"].append({
        "name":    "data_exfiltration",
        "success": True,
        "detail":  f"Hit {len(exfil_endpoints)} sensitive endpoints",
    })

    # ── Verification ───────────────────────────────────────────────────────
    time.sleep(5)
    try:
        resp = requests.get(f"{BACKEND_URL}/api/incidents", timeout=5)
        incidents = resp.json().get("data", {}).get("incidents", [])
        relevant  = [
            i for i in incidents
            if i.get("incident_type") in (
                "brute_force_attempt", "credential_compromise", "data_exfiltration_risk",
                "automated_attack_tool", "full_kill_chain",
            )
        ]
        results["detections"] = [
            {"type": i["incident_type"], "severity": i["severity"]}
            for i in relevant
        ]
        log(f"Verification: {len(relevant)} relevant incidents detected", Fore.MAGENTA)
        for inc in relevant:
            log(f"  [{inc['severity'].upper()}] {inc['title']}", Fore.MAGENTA)
    except Exception as exc:
        log(f"Verification error: {exc}", Fore.RED)

    results["end_time"] = datetime.now().isoformat()
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scenario A: Brute Force → Exfiltration")
    parser.add_argument("--speed", choices=["fast", "normal", "demo"], default="normal")
    args = parser.parse_args()
    speed_map = {"fast": 0.3, "normal": 1.0, "demo": 3.0}
    run(delay_multiplier=speed_map[args.speed])
