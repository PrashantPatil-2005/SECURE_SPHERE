"""
mitre_map.py — Static MITRE ATT&CK for Containers mapping.

Describes every technique SecuriSphere detects (or correlates) along with
the tactic it belongs to, the monitor/rule that surfaces it, the attack
scenario(s) it participates in, and a coverage classification:

    full        — directly detected by a monitor on raw telemetry
    partial     — inferred / labelled through correlation of lower-signal events
    theoretical — recognised label only; no dedicated detector yet

Imported by the correlation engine and the ``/api/mitre-mapping`` endpoint
to merge static metadata with live Redis/engine hit counts.
"""

TACTIC_ORDER = [
    "Reconnaissance",
    "Initial Access",
    "Credential Access",
    "Discovery",
    "Lateral Movement",
    "Privilege Escalation",
    "Collection",
    "Command and Control",
    "Exfiltration",
]


MITRE_MAP = {
    "T1046": {
        "technique_id": "T1046",
        "technique_name": "Network Service Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
        "description": (
            "Adversaries enumerate reachable services on hosts or container "
            "networks to identify exploitable targets before attacking."
        ),
        "detected_by": ["network-monitor"],
        "correlation_rules": [
            "recon_to_exploitation",
            "full_kill_chain",
            "browser_recon_scan",
            "browser_recon_to_privilege_escalation",
        ],
        "scenarios": ["B", "C"],
        "container_context": (
            "Surfaced as port_scan events from the network-monitor sidecar "
            "observing sweeps across the container network (>=20 unique "
            "destination ports in 60s)."
        ),
        "coverage": "full",
    },
    "T1595": {
        "technique_id": "T1595",
        "technique_name": "Active Scanning",
        "tactic": "Reconnaissance",
        "tactic_id": "TA0043",
        "description": (
            "Active reconnaissance of the target network, probing for "
            "running services, versions, and exposed endpoints."
        ),
        "detected_by": ["network-monitor"],
        "correlation_rules": [
            "recon_to_exploitation",
            "full_kill_chain",
            "persistent_threat",
        ],
        "scenarios": ["B"],
        "container_context": (
            "Detected via high-rate SYN / connection probes captured by "
            "network-monitor before any layer-7 activity from the same IP."
        ),
        "coverage": "full",
    },
    "T1190": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
        "description": (
            "Adversaries weaponise a vulnerability in an Internet-facing "
            "service (SQLi, XSS, RCE, path traversal) to gain execution."
        ),
        "detected_by": ["api-monitor", "browser-agent"],
        "correlation_rules": [
            "recon_to_exploitation",
            "full_kill_chain",
            "automated_attack_tool",
            "data_exfiltration_risk",
            "critical_exploit_attempt",
            "browser_sql_injection_attempt",
        ],
        "scenarios": ["A", "B", "C"],
        "container_context": (
            "api-monitor parses requests to api-server / web-app for "
            "SQLi/XSS/path-traversal signatures; browser-agent flags "
            "in-DOM payloads tagged sql-injection / path-traversal."
        ),
        "coverage": "full",
    },
    "T1110": {
        "technique_id": "T1110",
        "technique_name": "Brute Force",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": (
            "Adversary attempts to gain access by systematically guessing "
            "credentials against an authentication endpoint."
        ),
        "detected_by": ["auth-monitor", "browser-agent"],
        "correlation_rules": [
            "credential_compromise",
            "automated_attack_tool",
            "brute_force_attempt",
            "browser_brute_force",
            "browser_bruteforce_to_exfiltration",
        ],
        "scenarios": ["A"],
        "container_context": (
            "Targets auth-service login endpoint. Fires when "
            ">=5 failed logins from one source IP (or site_id for the "
            "browser layer) hit within a 60-second window."
        ),
        "coverage": "full",
    },
    "T1110.004": {
        "technique_id": "T1110.004",
        "technique_name": "Credential Stuffing",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": (
            "Using username/password pairs leaked in prior breaches to "
            "spray against authentication endpoints."
        ),
        "detected_by": ["auth-monitor"],
        "correlation_rules": [
            "distributed_credential_attack",
            "automated_attack_tool",
            "brute_force_attempt",
        ],
        "scenarios": ["A"],
        "container_context": (
            "Observed when the same username is hit from >=3 distinct "
            "source IPs within the correlation window — a classic "
            "stuffing pattern against auth-service."
        ),
        "coverage": "full",
    },
    "T1078": {
        "technique_id": "T1078",
        "technique_name": "Valid Accounts",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
        "description": (
            "Use of legitimate credentials (stolen or compromised) to "
            "access systems, bypassing normal auth scrutiny."
        ),
        "detected_by": ["auth-monitor"],
        "correlation_rules": [
            "credential_compromise",
            "automated_attack_tool",
            "distributed_credential_attack",
            "browser_recon_to_privilege_escalation",
        ],
        "scenarios": ["A", "B"],
        "container_context": (
            "Flagged when a successful login immediately follows a "
            "brute-force or stuffing burst from the same IP — the compromise "
            "is taken to be a valid-account use-after-brute-force."
        ),
        "coverage": "full",
    },
    "T1003": {
        "technique_id": "T1003",
        "technique_name": "OS Credential Dumping",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
        "description": (
            "Dumping credential material (hashes, tokens, secrets) from "
            "OS memory, config files, or secret stores for lateral reuse."
        ),
        "detected_by": [],
        "correlation_rules": ["credential_compromise"],
        "scenarios": [],
        "container_context": (
            "No dedicated detector yet — tagged theoretically on "
            "credential_compromise incidents to flag that post-exploit "
            "credential theft is plausible. Reserved for a future "
            "container-runtime monitor (eBPF / Falco)."
        ),
        "coverage": "theoretical",
    },
    "T1021": {
        "technique_id": "T1021",
        "technique_name": "Remote Services",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
        "description": (
            "Using valid accounts and network-reachable services (SSH, "
            "RDP, internal APIs) to move laterally between hosts."
        ),
        "detected_by": ["network-monitor", "browser-agent"],
        "correlation_rules": [
            "full_kill_chain",
            "browser_multi_hop_lateral_movement",
        ],
        "scenarios": ["C"],
        "container_context": (
            "Inferred from multi-hop traversal across >=3 distinct target "
            "entities / service aliases within 2 minutes from the same "
            "origin — matches inter-service lateral movement in the "
            "container mesh."
        ),
        "coverage": "full",
    },
    "T1071": {
        "technique_id": "T1071",
        "technique_name": "Application Layer Protocol",
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
        "description": (
            "Blending C2 traffic with normal application protocols "
            "(HTTP/HTTPS, DNS) to evade simple network filters."
        ),
        "detected_by": ["api-monitor"],
        "correlation_rules": [
            "automated_attack_tool",
            "persistent_threat",
        ],
        "scenarios": ["C"],
        "container_context": (
            "Partial: persistent long-tail HTTP traffic from the same "
            "source IP over >=5 minutes with >=3 event types is labelled "
            "T1071, but no protocol-anomaly detector is wired in yet."
        ),
        "coverage": "partial",
    },
    "T1083": {
        "technique_id": "T1083",
        "technique_name": "File and Directory Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
        "description": (
            "Enumerating files and directories — often via path traversal "
            "or directory listing — to locate secrets or config material."
        ),
        "detected_by": ["api-monitor", "browser-agent"],
        "correlation_rules": [
            "browser_path_traversal_attempt",
        ],
        "scenarios": ["B"],
        "container_context": (
            "Path-traversal payloads (../, %2e%2e) in HTTP requests "
            "against web-app / api-server are matched by api-monitor "
            "and the browser-agent's DOM inspector."
        ),
        "coverage": "full",
    },
    "T1530": {
        "technique_id": "T1530",
        "technique_name": "Data from Cloud Storage Object",
        "tactic": "Collection",
        "tactic_id": "TA0009",
        "description": (
            "Access to improperly secured objects in cloud object stores "
            "or internal data stores exposed by the application tier."
        ),
        "detected_by": ["api-monitor", "browser-agent"],
        "correlation_rules": [
            "data_exfiltration_risk",
            "browser_bruteforce_to_exfiltration",
        ],
        "scenarios": ["A"],
        "container_context": (
            "api-monitor flags sensitive_access events (requests to "
            "/api/admin/, /api/secrets, /export) and the browser-agent "
            "emits data_access on bulk table reads."
        ),
        "coverage": "full",
    },
    "T1041": {
        "technique_id": "T1041",
        "technique_name": "Exfiltration Over C2 Channel",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
        "description": (
            "Stolen data is exfiltrated back over the same application "
            "channel the attacker is already using for command and control."
        ),
        "detected_by": ["browser-agent"],
        "correlation_rules": [
            "browser_bruteforce_to_exfiltration",
        ],
        "scenarios": ["A"],
        "container_context": (
            "Fires when a data_access event follows a successful "
            "credential compromise on the same site_id — the attacker "
            "is pulling data over the active session."
        ),
        "coverage": "full",
    },
    "T1048": {
        "technique_id": "T1048",
        "technique_name": "Exfiltration Over Alternative Protocol",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
        "description": (
            "Data is moved off the network over a protocol distinct from "
            "the attacker's C2 channel (DNS, FTP, cloud upload API)."
        ),
        "detected_by": ["api-monitor"],
        "correlation_rules": [
            "data_exfiltration_risk",
        ],
        "scenarios": ["A", "C"],
        "container_context": (
            "Partial: labelled on data_exfiltration_risk incidents where "
            "sensitive_access follows an exploit on the same IP. No "
            "protocol-level egress inspector yet."
        ),
        "coverage": "partial",
    },
    "T1068": {
        "technique_id": "T1068",
        "technique_name": "Exploitation for Privilege Escalation",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
        "description": (
            "Abusing a software flaw or misconfiguration to gain higher "
            "privileges than the attacker's current account allows."
        ),
        "detected_by": ["api-monitor", "browser-agent"],
        "correlation_rules": [
            "critical_exploit_attempt",
            "browser_recon_to_privilege_escalation",
        ],
        "scenarios": ["B"],
        "container_context": (
            "Partial: inferred when a privilege_change browser event or "
            "a repeated critical exploit follows recon. True kernel/"
            "container-break-out detection is out of scope."
        ),
        "coverage": "partial",
    },
}


def get_technique(technique_id: str) -> dict:
    """Return the entry for *technique_id*, or a minimal fallback dict."""
    entry = MITRE_MAP.get(technique_id)
    if entry:
        return entry
    return {
        "technique_id": technique_id,
        "technique_name": "Unknown Technique",
        "tactic": "Unknown",
        "tactic_id": "",
        "description": "",
        "detected_by": [],
        "correlation_rules": [],
        "scenarios": [],
        "container_context": "",
        "coverage": "theoretical",
    }
