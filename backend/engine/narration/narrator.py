"""
narrator.py — SecuriSphere AI Kill Chain Narration

Uses the Hugging Face Inference API (free tier) via the official
``huggingface_hub`` library to turn a reconstructed kill chain incident
into a short, human-readable attack narrative.

This module is optional: if HF_API_TOKEN is not set, or the API call
fails, generate_narrative() returns None and the rest of the pipeline
continues unaffected.

Token setup
-----------
1. Go to https://huggingface.co/settings/tokens
2. Create a **fine-grained** token
3. Enable the **"Make calls to Inference Providers"** permission
4. Set HF_API_TOKEN in your .env file

Default model: ``mistralai/Mistral-7B-Instruct-v0.3``
Override via ``HF_MODEL`` env var.
"""

import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger("Narrator")

HF_MODEL = os.getenv("HF_MODEL", "Qwen/Qwen2.5-72B-Instruct")
HF_TIMEOUT = int(os.getenv("HF_TIMEOUT", "60"))

_client = None
_CLIENT_INIT_FAILED = False


def _get_client():
    """Lazy-initialize the HF InferenceClient. Returns None if unavailable."""
    global _client, _CLIENT_INIT_FAILED

    if _client is not None:
        return _client
    if _CLIENT_INIT_FAILED:
        return None

    token = os.getenv("HF_API_TOKEN", "").strip()
    if not token or token == "your_key_here":
        logger.info("HF_API_TOKEN not set — AI narration disabled")
        _CLIENT_INIT_FAILED = True
        return None

    try:
        from huggingface_hub import InferenceClient
        _client = InferenceClient(token=token, timeout=HF_TIMEOUT)
        logger.info("Hugging Face InferenceClient initialized (model=%s)", HF_MODEL)
        return _client
    except ImportError:
        logger.warning("huggingface_hub package not installed — AI narration disabled")
        _CLIENT_INIT_FAILED = True
        return None
    except Exception as exc:
        logger.warning("Failed to initialize HF client: %s", exc)
        _CLIENT_INIT_FAILED = True
        return None


def _build_prompt(incident: Dict[str, Any]) -> str:
    from ai.prompts import KILL_CHAIN_NARRATIVE_PROMPT
    import json
    
    incident_id = incident.get("incident_id", "unknown")
    incident_type = incident.get("incident_type", "unknown")
    severity = incident.get("severity", "unknown")
    source_ip = incident.get("source_ip", "unknown")
    mttd = incident.get("mttd_seconds")
    service_path = incident.get("service_path") or []
    mitre = incident.get("mitre_techniques") or []

    steps: List[Dict[str, Any]] = incident.get("kill_chain_steps") or []
    if not steps:
        raw = incident.get("correlated_events") or []
        steps = [e for e in raw if isinstance(e, dict)]

    step_lines = []
    for i, step in enumerate(steps[:12], start=1):
        svc = step.get("service_name") or step.get("source_layer") or "unknown"
        etype = step.get("event_type", "unknown")
        ts = step.get("timestamp", "")
        tech = step.get("mitre") or step.get("mitre_technique") or ""
        line = f"  {i}. [{ts}] {svc} — {etype}"
        if tech:
            line += f" ({tech})"
        step_lines.append(line)
    steps_block = "\n".join(step_lines) if step_lines else "  (no detailed steps recorded)"

    mttd_str = f"{mttd:.2f}s" if isinstance(mttd, (int, float)) else "unknown"
    path_str = " -> ".join(service_path) if service_path else "unknown"
    mitre_str = ", ".join(mitre) if mitre else "none recorded"

    context = (
        f"Incident ID : {incident_id}\n"
        f"Type        : {incident_type}\n"
        f"Severity    : {severity}\n"
        f"Source IP   : {source_ip}\n"
        f"MTTD        : {mttd_str}\n"
        f"Service path: {path_str}\n"
        f"MITRE       : {mitre_str}\n"
        f"Kill chain steps:\n{steps_block}\n"
    )
    
    return KILL_CHAIN_NARRATIVE_PROMPT.format(context=context)


def generate_narrative(incident: Dict[str, Any]) -> Optional[str]:
    """
    Generate a structured JSON attack narrative for an incident using Hugging Face.
    Returns the JSON narrative string, or None if generation is unavailable/failed.
    Never raises.
    """
    client = _get_client()
    if client is None:
        return None

    try:
        import json
        prompt = _build_prompt(incident)
        
        # We append a trailing `{` if response_format="json_object" isn't strictly enforced by HF API for this model
        # The Qwen model typically supports json output if instructed well.
        
        response = client.chat_completion(
            model=HF_MODEL,
            messages=[
                {"role": "user", "content": prompt},
            ],
            max_tokens=800,
            temperature=0.2,
        )
        narrative = (response.choices[0].message.content or "").strip()
        
        # Strip potential markdown formatting if the LLM leaked it
        if narrative.startswith("```json"):
            narrative = narrative[7:]
        if narrative.startswith("```"):
            narrative = narrative[3:]
        if narrative.endswith("```"):
            narrative = narrative[:-3]
        narrative = narrative.strip()
        
        if not narrative:
            logger.warning("HuggingFace returned empty narrative for %s",
                           incident.get("incident_id"))
            return None
            
        # Verify it parses as JSON
        json.loads(narrative)
            
        logger.info("Structured JSON narrative generated for %s (%d chars)",
                     incident.get("incident_id"), len(narrative))
        return narrative
    except Exception as exc:
        logger.warning("Narrative generation failed for %s: %s",
                       incident.get("incident_id"), exc)
        return None

