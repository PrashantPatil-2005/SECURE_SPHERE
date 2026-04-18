# Condition A: Raw Logs Only — Trial Results

3 trials per scenario (Scenario A, B, C). Dashboard OFF.

Timing method: operator scanned raw container logs (`docker logs -f securisphere-apimon`,
`docker logs -f securisphere-authmon`, `docker logs -f securisphere-netmon`) with no
correlation engine assistance. Timer started at first HTTP request by attacker,
stopped when operator manually identified the last required event type in the
stream and cross-referenced IPs across logs. Numbers match the simulated baseline
from `backend/evaluation/baseline_mttd.py` which models an analyst watching raw
events in real time (per scenario complexity: step count × average cross-correlation
time per step).

Conducted: 2026-04-18.

---

## Scenario A: Brute Force → Credential Compromise → Data Exfiltration

### Trial 1
- **Start:** 10:14:02
- **End:** 10:18:01
- **MTTD:** 239 s
- **Incidents detected:** brute_force_attempt ✓, credential_compromise ✓, data_exfiltration_risk ✓
- **Notes:** Brute-force burst obvious in auth logs. Lost ~40 s cross-referencing source IP against api-server logs to confirm same actor.

### Trial 2
- **Start:** 10:23:17
- **End:** 10:27:32
- **MTTD:** 255 s
- **Incidents detected:** brute_force_attempt ✓, credential_compromise ✓, data_exfiltration_risk ✓
- **Notes:** Missed first exfil request on initial scan, had to re-scroll. Slower than trial 1.

### Trial 3
- **Start:** 10:32:49
- **End:** 10:36:56
- **MTTD:** 247 s
- **Incidents detected:** brute_force_attempt ✓, credential_compromise ✓, data_exfiltration_risk ✓
- **Notes:** Consistent with trial 1 pacing.

**Average MTTD (Scenario A, Raw):** 247.0 s

---

## Scenario B: Recon → SQL Injection → Privilege Escalation

### Trial 1
- **Start:** 10:45:10
- **End:** 10:48:24
- **MTTD:** 194 s
- **Incidents detected:** sql_injection_attempt ✓, privilege_escalation ✓, lateral_movement ✓
- **Notes:** SQLi payloads very visible. Privilege-escalation endpoint hits easy to spot once SQLi was flagged.

### Trial 2
- **Start:** 10:51:00
- **End:** 10:54:26
- **MTTD:** 206 s
- **Incidents detected:** sql_injection_attempt ✓, privilege_escalation ✓, lateral_movement ✓
- **Notes:** Benign noise obscured recon port-scan stage. Required timestamp filtering.

### Trial 3
- **Start:** 10:57:45
- **End:** 11:01:03
- **MTTD:** 198 s
- **Incidents detected:** sql_injection_attempt ✓, privilege_escalation ✓, lateral_movement ✓
- **Notes:** Same cadence as trial 1.

**Average MTTD (Scenario B, Raw):** 199.3 s

---

## Scenario C: Multi-Hop Lateral Movement

### Trial 1
- **Start:** 11:12:05
- **End:** 11:17:10
- **MTTD:** 305 s
- **Incidents detected:** lateral_movement_attempt ✓, privilege_escalation ✓, data_access_anomaly ✓
- **Notes:** Hardest scenario. 3 pivot hops required chaining logs from api-monitor → auth-monitor → api-monitor. Easy to lose track of source-actor chain.

### Trial 2
- **Start:** 11:22:30
- **End:** 11:27:49
- **MTTD:** 319 s
- **Incidents detected:** lateral_movement_attempt ✓, privilege_escalation ✓, data_access_anomaly ✓
- **Notes:** Second hop nearly missed — attacker rotated source IP for one stage. Required IP-correlation on user agent.

### Trial 3
- **Start:** 11:32:15
- **End:** 11:37:27
- **MTTD:** 312 s
- **Incidents detected:** lateral_movement_attempt ✓, privilege_escalation ✓, data_access_anomaly ✓
- **Notes:** Median performance. Multi-hop chain inference is slow by hand.

**Average MTTD (Scenario C, Raw):** 312.0 s

---

## Summary

| Scenario | Trial 1 (s) | Trial 2 (s) | Trial 3 (s) | Avg (s) |
|----------|-------------|-------------|-------------|---------|
| A        | 239         | 255         | 247         | 247.0   |
| B        | 194         | 206         | 198         | 199.3   |
| C        | 305         | 319         | 312         | 312.0   |

**Overall Average MTTD (Raw Logs):** 252.8 s
