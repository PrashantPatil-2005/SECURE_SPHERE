"""
common.py — Shared helpers for attacker scenarios.

Provides:
- Endpoint resolution (env-var overridable, sensible localhost defaults)
- Timestamped colored logging
- HTTP helper with optional X-Forwarded-For spoofing
- Speed multiplier map + CLI speed argument helper
- Detection verification against /api/incidents
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable

import requests

try:
    from colorama import Fore, Style, init as _colorama_init
    _colorama_init(autoreset=True)
except Exception:  # colorama optional
    class _Dummy:
        def __getattr__(self, _): return ""
    Fore = _Dummy(); Style = _Dummy()


# ── Endpoint resolution ─────────────────────────────────────────────────────

API_URL     = os.getenv("SECURISPHERE_API_URL",     "http://localhost:5000")
AUTH_URL    = os.getenv("SECURISPHERE_AUTH_URL",    "http://localhost:5001")
BACKEND_URL = os.getenv("SECURISPHERE_BACKEND_URL", "http://localhost:8000")
WEBAPP_URL  = os.getenv("SECURISPHERE_WEBAPP_URL",  "http://localhost:8080")


# ── Speed ───────────────────────────────────────────────────────────────────

SPEED_MAP = {
    "fast":   0.2,
    "normal": 1.0,
    "demo":   2.5,
    "slow":   4.0,
}


def add_speed_arg(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--speed",
        choices=list(SPEED_MAP.keys()),
        default="normal",
        help="Pacing multiplier for inter-request delays.",
    )
    parser.add_argument(
        "--noise",
        action="store_true",
        help="Run traffic-generator in the background for realistic noise.",
    )


# ── Logging ─────────────────────────────────────────────────────────────────

def log(tag: str, msg: str, color: str = "") -> None:
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{ts}] [{tag}] {msg}{Style.RESET_ALL}")


# ── HTTP helpers ────────────────────────────────────────────────────────────

def req(
    method: str,
    url: str,
    *,
    spoofed_ip: str | None = None,
    timeout: float = 3.0,
    **kwargs,
) -> requests.Response | None:
    headers = kwargs.pop("headers", {}) or {}
    if spoofed_ip:
        headers["X-Forwarded-For"] = spoofed_ip
        headers["X-Real-IP"]       = spoofed_ip
    try:
        return requests.request(method, url, headers=headers, timeout=timeout, **kwargs)
    except Exception:
        return None


def reset_state() -> None:
    """Best-effort reset of backend event log + auth state + engine cooldowns."""
    ENGINE_URL  = os.getenv("SECURISPHERE_ENGINE_URL",  "http://localhost:5070")
    AUTHMON_URL = os.getenv("SECURISPHERE_AUTHMON_URL", "http://localhost:5060")
    for url, method in (
        (f"{BACKEND_URL}/api/events/clear",  "POST"),
        (f"{AUTH_URL}/auth/reset-all",        "POST"),
        (f"{ENGINE_URL}/engine/reset",        "POST"),   # clears 5-min per-IP cooldown
        (f"{AUTHMON_URL}/monitor/reset",      "POST"),   # flush ip_failures + cooldowns
    ):
        try:
            requests.request(method, url, timeout=3)
        except Exception:
            pass


# ── Detection verification ──────────────────────────────────────────────────

@dataclass
class DetectionResult:
    scenario: str
    start_time: str
    end_time: str = ""
    stages: list = field(default_factory=list)
    detections: list = field(default_factory=list)
    expected: list = field(default_factory=list)

    def matched_expected(self) -> list[str]:
        types = {d.get("type") for d in self.detections}
        return [e for e in self.expected if e in types]

    def summary(self) -> dict:
        return {
            "scenario":        self.scenario,
            "start_time":      self.start_time,
            "end_time":        self.end_time,
            "stages":          self.stages,
            "detections":      self.detections,
            "expected":        self.expected,
            "matched":         self.matched_expected(),
            "match_ratio":     (
                len(self.matched_expected()) / len(self.expected)
                if self.expected else 1.0
            ),
        }


def verify_detections(
    result: DetectionResult,
    relevant_types: Iterable[str],
    wait_seconds: float = 6.0,
    tag: str = "Verify",
) -> DetectionResult:
    time.sleep(wait_seconds)
    relevant_types = list(relevant_types)
    result.expected = relevant_types

    try:
        resp = requests.get(f"{BACKEND_URL}/api/incidents", timeout=5)
        payload = resp.json().get("data", {})
        incidents = payload.get("incidents") if isinstance(payload, dict) else payload
        if not isinstance(incidents, list):
            incidents = []
    except Exception as exc:
        log(tag, f"Fetch error: {exc}", Fore.RED)
        return result

    matched = [i for i in incidents if i.get("incident_type") in relevant_types]
    result.detections = [
        {
            "type":     i.get("incident_type"),
            "severity": i.get("severity"),
            "title":    i.get("title"),
            "mitre":    i.get("mitre_techniques", []),
        }
        for i in matched
    ]

    log(tag, f"{len(matched)}/{len(relevant_types)} expected incident types present", Fore.MAGENTA)
    for inc in matched:
        log(tag, f"  [{inc.get('severity', '?').upper()}] {inc.get('title', '?')}", Fore.MAGENTA)
    return result
