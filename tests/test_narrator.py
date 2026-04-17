"""
test_narrator.py — Unit tests for engine/narration/narrator.py

These tests exercise the prompt builder and the client-init fallback paths
without making any real network calls to the Hugging Face API.
"""

import os
import sys

import pytest

# Make the engine/ directory importable so `narration.narrator` resolves the
# same way the correlation engine imports it at runtime.
ENGINE_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "backend", "engine")
)
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)

from narration import narrator  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_narrator_state(monkeypatch):
    """Reset the module-level client cache before each test."""
    monkeypatch.setattr(narrator, "_client", None, raising=False)
    monkeypatch.setattr(narrator, "_CLIENT_INIT_FAILED", False, raising=False)
    yield


def test_build_prompt_full_incident():
    incident = {
        "incident_id": "abc-123",
        "incident_type": "recon_to_exploitation",
        "severity": "critical",
        "source_ip": "10.0.0.5",
        "mttd_seconds": 12.34,
        "service_path": ["api-server", "auth-service"],
        "mitre_techniques": ["T1046", "T1190"],
        "kill_chain_steps": [
            {
                "service_name": "api-server",
                "event_type": "port_scan",
                "timestamp": "2026-04-12T10:00:00",
                "mitre": "T1046",
            },
            {
                "service_name": "auth-service",
                "event_type": "brute_force",
                "timestamp": "2026-04-12T10:01:00",
                "mitre": "T1110",
            },
        ],
    }

    prompt = narrator._build_prompt(incident)

    assert "abc-123" in prompt
    assert "recon_to_exploitation" in prompt
    assert "critical" in prompt
    assert "10.0.0.5" in prompt
    assert "api-server -> auth-service" in prompt
    assert "T1046" in prompt and "T1190" in prompt
    assert "port_scan" in prompt
    assert "brute_force" in prompt
    assert "12.34s" in prompt


def test_build_prompt_minimal_incident():
    """Should not crash when most fields are missing."""
    prompt = narrator._build_prompt({})

    assert "unknown" in prompt
    assert "Kill chain steps:" in prompt
    assert "(no detailed steps recorded)" in prompt


def test_build_prompt_empty_steps_uses_correlated_events():
    """If kill_chain_steps is empty, fall back to correlated_events."""
    incident = {
        "incident_id": "xyz-999",
        "kill_chain_steps": [],
        "correlated_events": [
            {
                "source_layer": "network",
                "event_type": "port_scan",
                "timestamp": "2026-04-12T09:00:00",
                "mitre_technique": "T1046",
            },
        ],
    }

    prompt = narrator._build_prompt(incident)

    assert "port_scan" in prompt
    assert "network" in prompt
    assert "T1046" in prompt


def test_get_client_no_api_key(monkeypatch):
    """Missing HF_API_TOKEN should disable narration gracefully."""
    monkeypatch.delenv("HF_API_TOKEN", raising=False)

    client = narrator._get_client()

    assert client is None
    assert narrator._CLIENT_INIT_FAILED is True

    # Subsequent calls should keep returning None without retrying.
    assert narrator._get_client() is None


def test_get_client_stub_key_disabled(monkeypatch):
    """The default `.env` stub should also be treated as disabled."""
    monkeypatch.setenv("HF_API_TOKEN", "your_key_here")

    assert narrator._get_client() is None
    assert narrator._CLIENT_INIT_FAILED is True


def test_hf_model_constant():
    assert narrator.HF_MODEL == "mistralai/Mistral-7B-Instruct-v0.3"


def test_generate_narrative_returns_none_without_client(monkeypatch):
    """generate_narrative must never raise when the client is unavailable."""
    monkeypatch.delenv("HF_API_TOKEN", raising=False)

    result = narrator.generate_narrative({"incident_id": "foo"})

    assert result is None
