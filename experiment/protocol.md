# MTTD Experiment Protocol

## Objective
Measure Mean Time To Detect (MTTD) reduction when using SecuriSphere correlation engine vs. raw logs alone.

Target: ≥70% MTTD reduction with dashboard.

---

## Definitions

### "Full Kill Chain Identified"
Operator declares kill chain complete when:
1. **Raw logs condition:** All 4 stages manually identified in raw log output (stage names visible)
2. **Dashboard condition:** All expected incidents appear in SecuriSphere Dashboard UI with correlations visible

Expected incidents per scenario:
- **Scenario A:** brute_force_attempt, credential_compromise, data_exfiltration_risk
- **Scenario B:** sql_injection_attempt, privilege_escalation, lateral_movement
- **Scenario C:** lateral_movement_attempt (x3), privilege_escalation, data_access_anomaly

### Timer Start/Stop
- **START:** Scenario execution begins (first HTTP request sent by attacker)
- **STOP:** Operator visually confirms all expected incidents present in output/dashboard
- **MTTD = (STOP - START) in seconds**

---

## Trial Structure

### Condition A: Raw Logs Only
- Run scenario with `make attack-{a|b|c}` (no dashboard open)
- Watch console output for stage completion messages
- Timer: start at first log line, stop when all stages logged
- Record: MTTD in seconds

### Condition B: With SecuriSphere Dashboard
- Launch SecuriSphere dashboard on separate monitor/window
- Run scenario with `make attack-{a|b|c}`
- Watch dashboard for incident cards to appear + correlate
- Timer: start at first log, stop when all incidents visible + correlated
- Record: MTTD in seconds

### Per-Scenario Trials
- **3 trials per scenario per condition = 18 total runs**
- Scenario sequence: A → B → C (repeat 3×)
- Between trials: `make reset-state` (clear detection state)
- Cool-down: 30 seconds between trial runs

---

## Success Criteria

### Individual Trial
- ✅ All expected incidents detected/visible
- ✅ MTTD recorded in seconds
- ⚠️ Partial detection (some incidents missed) = trial fails, re-run

### Overall Results
- ✅ 18/18 trials successful
- ✅ Average MTTD(Dashboard) / Average MTTD(Raw) ≤ 0.3 (70% reduction)

---

## Data Collection Template

```
Scenario: A | Condition: Raw Logs | Trial 1
Start time: [HH:MM:SS]
End time: [HH:MM:SS]
MTTD: [seconds]
Incidents detected: brute_force_attempt, credential_compromise, data_exfiltration_risk ✓
Notes: [any observations]
```

---

## Metrics Calculated

1. **MTTD per condition:** avg(all trials for that condition)
2. **Reduction %:** (1 - avg(Dashboard) / avg(Raw)) × 100%
3. **Variability:** stddev(MTTD) per condition (lower = more consistent)

---

## Notes

- Ensure correlation engine is warmed up before trial 1 (run a dummy attack)
- Do NOT open dashboard during Condition A trials
- Operator must be consistent in "kill chain complete" judgment across trials
- If system behaves anomalously (timeouts, crashes), discard trial and re-run
