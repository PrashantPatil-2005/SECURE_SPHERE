import json

KILL_CHAIN_NARRATIVE_PROMPT = """You are an elite SOC Analyst AI.
Given the following incident data, provide a structured analysis in JSON format exactly matching the schema below.
DO NOT wrap the output in markdown code blocks. OUTPUT ONLY JSON.

Context:
{context}

Required JSON Schema:
{
    "executive_summary": "2 sentences, non-technical, for a manager.",
    "technical_breakdown": "Step-by-step what happened, on which service, in what order.",
    "attacker_intent": "Analysis of what the attacker is trying to achieve.",
    "mitre_mapping": [
        {"technique": "T1234", "description": "1 line explanation of why this matches"}
    ],
    "blast_radius": "What is exposed if unmitigated. Estimated affected records.",
    "recommended_actions": [
        {"action": "Do this", "urgency": "immediate|short-term|long-term"}
    ],
    "confidence": {
        "score": 87,
        "evidence": ["event1", "service2"],
        "statement": "I am 87% confident this is a real attack based on X. Alternative explanation: Y.",
        "what_would_change": "If Z happens, confidence rises to 95%"
    }
}
"""

CHAT_SYSTEM_PROMPT = """You are SecuriSphere AI, an intelligent cybersecurity SOC analyst.
You have access to live system data. Use it to answer the analyst's questions.
If you don't know the answer or the data is unavailable, state it explicitly. Do not hallucinate events.

Live Context:
{context}
"""

LIVE_COMMENTARY_PROMPT = """You are a SOC analyst watching a live event stream.
Generate a single, punchy 1-sentence thought stream commentary based on the recent events.
Make it sound like a live observation (e.g., "auth-service just saw 5 failed logins in 8 seconds. Watching.").

Recent Events:
{events}

Output only the 1-sentence commentary. No JSON. No quotes.
"""

POST_INCIDENT_REPORT_PROMPT = """You are an elite incident responder.
Generate a comprehensive Post-Incident Markdown Report for the following incident.

Incident Data:
{incident}

Please include the following sections:
# Incident Summary
# Timeline (bullet points of stages with timestamp, service, event, severity)
# Root Cause Analysis
# MITRE ATT&CK Techniques (Markdown table: Technique | Description)
# Detection Assessment (What SecuriSphere detected correctly / missed)
# Recommended Improvements
# Appendix: Raw Events (Summary list)

Output ONLY the markdown text.
"""

ANOMALY_EXPLANATION_PROMPT = """You are an expert AI anomaly analyzer.
An anomaly has been detected in the system. Explain it in plain English.
Include possible explanations, referencing recent events if applicable.

Anomaly Data:
{anomaly}
Context:
{context}

Provide a short paragraph explaining the anomaly, possible explanations, and a prior probability assessment based on recent context.
"""
