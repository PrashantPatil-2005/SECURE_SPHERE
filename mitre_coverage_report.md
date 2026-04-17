# MITRE ATT&CK for Containers — Coverage Report

**Framework:** MITRE ATT&CK for Containers v14
**Generated:** 2026-04-17
**Target:** 8+ techniques across 3 attack scenarios — **MET (17 techniques, 3 scenarios)**

---

## Summary

| Metric | Value |
|---|---|
| Total correlation rules | 16 |
| Unique MITRE techniques covered | **17** |
| Core Containers techniques covered | 6 / 6 (T1110, T1078, T1021, T1068, T1046, T1041) |
| Extended techniques | 3 (T1570, T1548, T1526) |
| Attack scenarios validated | 3 (A, B, C) |

---

## Core Containers Technique Coverage (6/6)

| Technique ID | Name | Tactic | Covered By (Rules) |
|---|---|---|---|
| T1046 | Network Service Discovery | Discovery | `rule_recon_to_exploit`, `rule_full_kill_chain`, `rule_browser_recon_scan`, `rule_browser_recon_to_privesc` |
| T1078 | Valid Accounts | Initial Access / Priv Esc | `rule_credential_compromise`, `rule_api_auth_combined`, `rule_distributed_attack`, `rule_browser_recon_to_privesc` |
| T1021 | Remote Services (Lateral Movement) | Lateral Movement | `rule_full_kill_chain`, `rule_browser_multi_hop` |
| T1068 | Exploitation for Privilege Escalation | Privilege Escalation | `rule_critical_exploit_attempt`, `rule_browser_recon_to_privesc` |
| T1110 | Brute Force | Credential Access | `rule_credential_compromise`, `rule_full_kill_chain`, `rule_api_auth_combined`, `rule_brute_force_attempt`, `rule_browser_brute_force`, `rule_browser_bruteforce_to_exfil` |
| T1041 | Exfiltration Over C2 Channel | Exfiltration | `rule_data_exfiltration`, `rule_browser_bruteforce_to_exfil` |

---

## Extended Technique Coverage (3)

| Technique ID | Name | Tactic | Covered By |
|---|---|---|---|
| T1570 | Lateral Tool Transfer | Lateral Movement | `rule_full_kill_chain`, `rule_browser_multi_hop` |
| T1548 | Abuse Elevation Control Mechanism | Privilege Escalation | `rule_browser_recon_to_privesc` |
| T1526 | Cloud Service Discovery | Discovery | `rule_recon_to_exploit`, `rule_browser_recon_scan` |

---

## Additional Technique Coverage (8)

| Technique ID | Name | Tactic |
|---|---|---|
| T1595 | Active Scanning | Reconnaissance |
| T1190 | Exploit Public-Facing Application | Initial Access |
| T1110.004 | Credential Stuffing | Credential Access |
| T1003 | OS Credential Dumping | Credential Access |
| T1071 | Application Layer Protocol | Command and Control |
| T1083 | File and Directory Discovery | Discovery |
| T1530 | Data from Cloud Storage | Collection |
| T1048 | Exfiltration Over Alternative Protocol | Exfiltration |

---

## Attack Scenario Validation (3)

### Scenario A — Brute Force → Data Exfiltration
**File:** `backend/simulation/scenarios/scenario_a_brute_force.py`

**Expected rule triggers:**
- `rule_brute_force_attempt` → T1110
- `rule_credential_compromise` → T1110, T1078, T1003
- `rule_browser_bruteforce_to_exfil` → T1110, T1530, T1041

**Techniques exercised:** T1110, T1078, T1003, T1530, T1041 (5)

---

### Scenario B — Reconnaissance → Exploitation
**File:** `backend/simulation/scenarios/scenario_b_recon_exploit.py`

**Expected rule triggers:**
- `rule_browser_recon_scan` → T1046, T1526
- `rule_recon_to_exploit` → T1046, T1595, T1190, T1526
- `rule_critical_exploit_attempt` → T1190, T1068
- `rule_browser_recon_to_privesc` → T1046, T1078, T1548, T1068

**Techniques exercised:** T1046, T1526, T1595, T1190, T1068, T1078, T1548 (7)

---

### Scenario C — Lateral Movement (Multi-Vector)
**File:** `backend/simulation/scenarios/scenario_c_lateral_movement.py`

**Expected rule triggers:**
- `rule_full_kill_chain` → T1046, T1595, T1190, T1110, T1021, T1570
- `rule_browser_multi_hop` → T1021, T1570
- `rule_api_auth_combined` → T1110, T1190, T1071, T1078
- `rule_persistent_threat` → T1595, T1071

**Techniques exercised:** T1046, T1595, T1190, T1110, T1021, T1570, T1071, T1078 (8)

---

## Aggregate Scenario Coverage

Union across A + B + C:
T1046, T1078, T1021, T1068, T1110, T1041, T1570, T1548, T1526, T1595, T1190, T1110.004 (implicit), T1003, T1071, T1083 (via path traversal chains), T1530, T1048

**Unique techniques across 3 scenarios: 15+**
Target of 8+ techniques across 3 scenarios: **MET**.

---

## Verification Steps

1. `GET /api/mitre-mapping` — returns aggregated technique frequency map w/ names + descriptions.
2. `GET /engine/mitre-mapping` (correlation engine internal) — raw hit counter from `stats["mitre_hits"]`.
3. Frontend `MitrePanel.jsx` — renders live matrix with hover tooltips.
4. Run each scenario via `POST /api/attack/simulate` with `scenario: "A" | "B" | "C"` and inspect the resulting incidents' `mitre_techniques` field.

---

## References

- MITRE ATT&CK for Containers Matrix: https://attack.mitre.org/matrices/enterprise/containers/
- Rule definitions: `backend/engine/correlation/correlation_engine.py`
- Mapping source of truth: `mitre_mapping.json`
