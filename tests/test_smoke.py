"""
Smoke test — SecuriSphere end-to-end pipeline.

Requires the full stack to be running (make start).
Run with: pytest tests/test_smoke.py -v -s

Skips automatically if Redis is not reachable on localhost:6379.
"""

import json
import time
import pytest
from datetime import datetime, timezone

# Optional imports — skip test if not available
try:
    import redis as redis_lib
    import requests
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False


REDIS_HOST = "localhost"
REDIS_PORT = 6379
BACKEND_URL = "http://localhost:8000"
SECURITY_EVENTS_CHANNEL = "security_events"   # matches correlation_engine.py pubsub.subscribe()
WAIT_SECONDS = 12  # time to allow correlation engine to process the event


def redis_is_reachable():
    try:
        r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT, socket_connect_timeout=2)
        r.ping()
        return True
    except Exception:
        return False


def backend_is_reachable():
    try:
        resp = requests.get(f"{BACKEND_URL}/api/metrics", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


@pytest.mark.skipif(not DEPS_AVAILABLE, reason="redis or requests not installed")
def test_full_pipeline_smoke():
    """
    Inject one synthetic brute_force event into Redis.
    Wait 12 seconds for the correlation engine to process it.
    Assert that at least one incident exists in the backend.
    """
    if not redis_is_reachable():
        pytest.skip("Redis not reachable on localhost:6379 — is the stack running?")

    if not backend_is_reachable():
        pytest.skip("Backend not reachable on localhost:8000 — is the stack running?")

    r = redis_lib.Redis(host=REDIS_HOST, port=REDIS_PORT)

    # Build synthetic event — matches the schema correlation_engine.py expects
    synthetic_event = {
        "event_type": "brute_force",
        "source_layer": "auth",
        "severity": "high",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_entity": {
            "ip": "10.99.0.1",
            "service_name": "auth-service"
        },
        "target_entity": {
            "ip": "10.99.0.2",
            "service_name": "api-gateway"
        },
        "details": {
            "failed_attempts": 12,
            "note": "smoke-test-synthetic-event"
        }
    }

    # Record how many incidents exist BEFORE injection
    before_resp = requests.get(f"{BACKEND_URL}/api/incidents", timeout=5)
    assert before_resp.status_code == 200, f"Backend /api/incidents returned {before_resp.status_code}"
    before_data = before_resp.json()
    # Handle both response shapes: {data: {incidents: []}} or {data: []}
    before_incidents = (
        before_data.get("data", {}).get("incidents", [])
        if isinstance(before_data.get("data"), dict)
        else before_data.get("data", [])
    )
    incident_count_before = len(before_incidents)

    # Publish synthetic event
    payload = json.dumps(synthetic_event)
    r.publish(SECURITY_EVENTS_CHANNEL, payload)

    # Wait for correlation engine to process
    print(f"\nEvent published. Waiting {WAIT_SECONDS}s for correlation engine...")
    time.sleep(WAIT_SECONDS)

    # Check backend for new incidents
    after_resp = requests.get(f"{BACKEND_URL}/api/incidents", timeout=5)
    assert after_resp.status_code == 200, f"Backend /api/incidents returned {after_resp.status_code} after event injection"
    after_data = after_resp.json()
    after_incidents = (
        after_data.get("data", {}).get("incidents", [])
        if isinstance(after_data.get("data"), dict)
        else after_data.get("data", [])
    )
    incident_count_after = len(after_incidents)

    print(f"Incidents before: {incident_count_before} | Incidents after: {incident_count_after}")

    assert incident_count_after > 0, (
        "No incidents found after injecting synthetic brute_force event. "
        "Check that the correlation engine is running and subscribed to the security_events channel."
    )
