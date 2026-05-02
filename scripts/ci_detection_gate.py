"""CI gate: detection-rate + MTTD assertion for SecuriSphere.

Spawns scenario A against the running stack, waits for incidents to land,
then asserts:

  * at least ``MIN_INCIDENTS`` kill chains were created
  * average MTTD (kill_chains.mttd_seconds) < ``MAX_MTTD_SECONDS``
  * /api/metrics ``detection_rate`` >= ``MIN_DETECTION_RATE`` percent

Exit codes
----------
  0 — all gates passed
  1 — at least one gate failed
  2 — backend never reachable (infrastructure problem, not a regression)

Designed for the GitHub Actions ``docker-smoke`` job — assumes the full
docker-compose stack is already up on localhost (backend :8000,
correlation engine :5070, attacker container reachable via subprocess).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

BACKEND_URL          = os.getenv("CI_GATE_BACKEND_URL", "http://localhost:8000")
SCENARIO             = os.getenv("CI_GATE_SCENARIO", "a")
WAIT_SECONDS         = int(os.getenv("CI_GATE_WAIT_SECONDS", "180"))
POLL_INTERVAL        = int(os.getenv("CI_GATE_POLL_SECONDS", "5"))
MIN_INCIDENTS        = int(os.getenv("CI_GATE_MIN_INCIDENTS", "1"))
MAX_MTTD_SECONDS     = float(os.getenv("CI_GATE_MAX_MTTD_SECONDS", "30"))
MIN_DETECTION_RATE   = float(os.getenv("CI_GATE_MIN_DETECTION_RATE", "90"))


def _http_get_json(path: str, timeout: float = 5.0):
    url = f"{BACKEND_URL}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _wait_for_backend() -> bool:
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            _http_get_json("/api/health", timeout=2.0)
            return True
        except Exception:
            time.sleep(2)
    return False


def _run_scenario(scenario: str) -> int:
    """Spawn the scenario module via subprocess. Returns the exit code."""
    cmd = [
        sys.executable, "-u", "-m", f"attacker.scenario_{scenario}",
        "--speed", "fast",
    ]
    env = os.environ.copy()
    proc = subprocess.run(
        cmd, env=env, capture_output=True, text=True, timeout=180,
    )
    if proc.returncode != 0:
        print(f"[gate] scenario {scenario} exited {proc.returncode}")
        print(proc.stdout[-2000:])
        print(proc.stderr[-2000:])
    return proc.returncode


def _poll_incidents() -> dict:
    deadline = time.time() + WAIT_SECONDS
    last = {"incidents": [], "metrics": {}}
    while time.time() < deadline:
        try:
            inc = _http_get_json("/api/incidents")
            metrics = _http_get_json("/api/metrics")
        except Exception as exc:
            print(f"[gate] poll failed: {exc}")
            time.sleep(POLL_INTERVAL)
            continue

        incidents = inc.get("data") or inc.get("incidents") or inc or []
        if isinstance(incidents, dict):
            incidents = incidents.get("data") or incidents.get("incidents") or []
        last = {"incidents": incidents, "metrics": metrics}

        if len(incidents) >= MIN_INCIDENTS:
            return last
        time.sleep(POLL_INTERVAL)
    return last


def main() -> int:
    print(f"[gate] backend={BACKEND_URL} scenario={SCENARIO} "
          f"min_incidents={MIN_INCIDENTS} max_mttd={MAX_MTTD_SECONDS}s "
          f"min_detection_rate={MIN_DETECTION_RATE}%")

    if not _wait_for_backend():
        print("[gate] backend never became reachable")
        return 2

    rc = _run_scenario(SCENARIO)
    if rc != 0:
        print("[gate] scenario subprocess failed; continuing — engine may still "
              "have detected partial chain")

    snapshot = _poll_incidents()
    incidents = snapshot["incidents"]
    metrics   = snapshot["metrics"] or {}

    failures = []

    incident_count = len(incidents) if isinstance(incidents, list) else 0
    if incident_count < MIN_INCIDENTS:
        failures.append(
            f"incident count {incident_count} < required {MIN_INCIDENTS}"
        )

    mttds = []
    for inc in (incidents if isinstance(incidents, list) else []):
        if not isinstance(inc, dict):
            continue
        m = inc.get("mttd_seconds")
        if isinstance(m, (int, float)):
            mttds.append(float(m))
    avg_mttd = sum(mttds) / len(mttds) if mttds else None
    if avg_mttd is not None and avg_mttd > MAX_MTTD_SECONDS:
        failures.append(
            f"avg MTTD {avg_mttd:.2f}s > max {MAX_MTTD_SECONDS}s"
        )

    detection_rate = metrics.get("detection_rate")
    if isinstance(detection_rate, (int, float)) and detection_rate < MIN_DETECTION_RATE:
        failures.append(
            f"detection_rate {detection_rate}% < min {MIN_DETECTION_RATE}%"
        )

    print(f"[gate] incidents={incident_count} "
          f"avg_mttd={avg_mttd if avg_mttd is not None else 'n/a'}s "
          f"detection_rate={detection_rate if detection_rate is not None else 'n/a'}%")

    if failures:
        print("[gate] FAILED:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("[gate] OK — all detection-rate gates passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
