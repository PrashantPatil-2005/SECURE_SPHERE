"""
attack_simulator.py — In-process attack scenario emitter.

Generates synthetic security events that mimic the kill chains in
`attacker/scenario_{a,b,c}.py` without requiring any target services.
Events are pushed to Redis (events:<layer>) and published on the
`security_events` channel so the existing correlation engine + SocketIO
fan-out treats them identically to real monitor traffic.

Used by `/api/attack/run` when the legacy subprocess + localhost-target
launcher is unavailable (e.g. single-container deploy on Render).
"""

from __future__ import annotations

import json
import os
import random
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Callable, List, Optional

SPEED_MAP = {"fast": 0.15, "normal": 0.6, "demo": 1.4, "slow": 3.0}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ev(
    *,
    layer: str,
    event_type: str,
    severity: str,
    src_ip: str,
    src_service: Optional[str],
    dst_service: str,
    dst_ip: Optional[str] = None,
    mitre: Optional[str] = None,
    details: Optional[dict] = None,
    confidence: float = 0.85,
) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "timestamp": _now_iso(),
        "source_layer": layer,
        "event_type": event_type,
        "severity": {"level": severity, "score": _sev_score(severity)},
        "source_entity": {"ip": src_ip, "service": src_service},
        "destination_entity": {"ip": dst_ip or "10.0.1.20", "service": dst_service},
        "mitre_technique": mitre or "",
        "confidence": confidence,
        "details": details or {},
    }


_SEV = {"critical": 95, "high": 75, "medium": 50, "low": 25, "info": 10}


def _sev_score(level: str) -> int:
    return _SEV.get(level.lower(), 30)


# ── Scenario definitions (returns list of event dicts) ─────────────────────


def _scenario_a(src_ip: str) -> List[dict]:
    """Brute force → credential reuse → exfiltration."""
    out: List[dict] = []
    out.append(_ev(
        layer="network", event_type="recon_probe", severity="low",
        src_ip=src_ip, src_service=None, dst_service="auth-service",
        mitre="T1595", details={"path": "/auth/health"},
    ))
    for i in range(50):
        out.append(_ev(
            layer="auth", event_type="login_failed",
            severity="medium" if i < 40 else "high",
            src_ip=src_ip, src_service=None, dst_service="auth-service",
            mitre="T1110",
            details={"username": f"user{i % 8}", "reason": "invalid_credentials"},
            confidence=0.92,
        ))
    out.append(_ev(
        layer="auth", event_type="login_success",
        severity="high", src_ip=src_ip, src_service=None,
        dst_service="auth-service", mitre="T1078",
        details={"username": "admin", "after_failures": 50},
        confidence=0.97,
    ))
    out.append(_ev(
        layer="api", event_type="data_access",
        severity="high", src_ip=src_ip, src_service="auth-service",
        dst_service="api-gateway", mitre="T1078",
        details={"path": "/api/users", "rows": 1240},
    ))
    out.append(_ev(
        layer="network", event_type="data_exfiltration",
        severity="critical", src_ip=src_ip, src_service="api-gateway",
        dst_service="external", dst_ip="203.0.113.42", mitre="T1041",
        details={"bytes_out": 18_400_000, "destination": "203.0.113.42:443"},
        confidence=0.95,
    ))
    return out


def _scenario_b(src_ip: str) -> List[dict]:
    """Recon → SQLi → privilege escalation → lateral."""
    out: List[dict] = []
    for port in (22, 80, 443, 5432, 8080):
        out.append(_ev(
            layer="network", event_type="port_scan",
            severity="low", src_ip=src_ip, src_service=None,
            dst_service="web-app", mitre="T1046",
            details={"port": port, "state": "open" if port in (80, 443, 8080) else "closed"},
        ))
    for payload in ("' OR '1'='1", "1; DROP TABLE users--", "UNION SELECT password FROM users"):
        out.append(_ev(
            layer="api", event_type="sql_injection",
            severity="high", src_ip=src_ip, src_service=None,
            dst_service="web-app", mitre="T1190",
            details={"path": "/search", "payload": payload},
            confidence=0.94,
        ))
    out.append(_ev(
        layer="api", event_type="privilege_escalation",
        severity="critical", src_ip=src_ip, src_service="web-app",
        dst_service="web-app", mitre="T1068",
        details={"cve": "CVE-2024-1086", "from_role": "user", "to_role": "root"},
        confidence=0.96,
    ))
    out.append(_ev(
        layer="network", event_type="lateral_movement",
        severity="high", src_ip=src_ip, src_service="web-app",
        dst_service="api-gateway", mitre="T1021",
        details={"protocol": "ssh", "auth": "key"},
    ))
    return out


def _scenario_c(src_ip: str) -> List[dict]:
    """Multi-hop lateral movement + bulk exfil."""
    out: List[dict] = []
    out.append(_ev(
        layer="auth", event_type="stolen_credential_use",
        severity="high", src_ip=src_ip, src_service=None,
        dst_service="auth-service", mitre="T1078",
        details={"key_id": "AKIA-LEAKED-1234", "method": "api_key"},
        confidence=0.93,
    ))
    hops = [("db-host", "api-host"), ("api-host", "payment-service"), ("payment-service", "warehouse")]
    for src, dst in hops:
        out.append(_ev(
            layer="network", event_type="lateral_movement",
            severity="high", src_ip=src_ip, src_service=src,
            dst_service=dst, mitre="T1021",
            details={"protocol": "smb", "from": src, "to": dst},
        ))
    out.append(_ev(
        layer="api", event_type="file_discovery",
        severity="medium", src_ip=src_ip, src_service="warehouse",
        dst_service="warehouse", mitre="T1083",
        details={"files": 8421, "mounted": ["/data", "/backup"]},
    ))
    out.append(_ev(
        layer="api", event_type="data_collection",
        severity="high", src_ip=src_ip, src_service="warehouse",
        dst_service="warehouse", mitre="T1530",
        details={"objects": 4200, "size_mb": 312},
    ))
    out.append(_ev(
        layer="network", event_type="bulk_exfiltration",
        severity="critical", src_ip=src_ip, src_service="warehouse",
        dst_service="external", dst_ip="198.51.100.7", mitre="T1048",
        details={"protocol": "dns_tunnel", "bytes_out": 312_000_000},
        confidence=0.97,
    ))
    return out


_SCENARIOS = {"a": _scenario_a, "b": _scenario_b, "c": _scenario_c}


# ── Runtime ───────────────────────────────────────────────────────────────


class SimulatorRuntime:
    """Owns a single concurrent simulation. Caller checks `is_running()`
    before launching another."""

    def __init__(self, redis_client=None, socketio=None, log_cb: Optional[Callable[[str], None]] = None):
        self._redis = redis_client
        self._socketio = socketio
        self._log = log_cb or (lambda _msg: None)
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._cancel = threading.Event()

    def is_running(self) -> bool:
        with self._lock:
            return self._running

    def start(self, scenario: str, speed: str = "demo") -> bool:
        with self._lock:
            if self._running:
                return False
            self._running = True
            self._cancel.clear()
        self._thread = threading.Thread(
            target=self._run, args=(scenario, speed), daemon=True
        )
        self._thread.start()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    def _emit(self, ev: dict) -> None:
        layer = ev.get("source_layer", "network")
        try:
            if self._redis is not None:
                payload = json.dumps(ev)
                self._redis.lpush(f"events:{layer}", payload)
                self._redis.ltrim(f"events:{layer}", 0, 999)
                self._redis.publish("security_events", payload)
        except Exception as exc:
            self._log(f"[redis-error] {exc}")
        try:
            if self._socketio is not None:
                self._socketio.emit("new_event", ev)
        except Exception as exc:
            self._log(f"[ws-error] {exc}")

    def _run(self, scenario: str, speed: str) -> None:
        delay = SPEED_MAP.get(speed, 1.0)
        scenarios = ["a", "b", "c"] if scenario == "all" else [scenario]
        src_ip = "10.0.2.4"
        try:
            for sc in scenarios:
                fn = _SCENARIOS.get(sc)
                if fn is None:
                    self._log(f"[skip] unknown scenario {sc!r}")
                    continue
                self._log(f"[stage] scenario={sc} speed={speed}")
                events = fn(src_ip)
                for i, ev in enumerate(events):
                    if self._cancel.is_set():
                        self._log("[cancel] simulation aborted")
                        return
                    self._emit(ev)
                    if i % 10 == 0 or i == len(events) - 1:
                        self._log(
                            f"[emit] {sc} {ev.get('event_type')} {ev.get('severity', {}).get('level')}"
                        )
                    jitter = random.uniform(0.6, 1.2)
                    time.sleep(max(0.05, delay * 0.05 * jitter))
                self._log(f"[done] scenario={sc} events={len(events)}")
        except Exception as exc:
            self._log(f"[error] {exc}")
        finally:
            with self._lock:
                self._running = False


def detect_target_services_unreachable() -> bool:
    """Return True when the legacy attacker scenarios cannot work (no
    auth-service / api-server / web-app on this host). Used to default
    the launcher to in-process mode."""
    mode = os.environ.get("ATTACK_MODE", "auto").lower()
    if mode == "inprocess":
        return True
    if mode == "subprocess":
        return False
    # auto: in-process whenever localhost targets aren't reachable. Cheap
    # heuristic — Render free/starter has no extra services, so default
    # to in-process unless explicitly overridden.
    return os.environ.get("ATTACK_TARGETS_AVAILABLE", "0") != "1"
