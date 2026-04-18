# MTTD Experiment Setup

Controlled trials measuring Mean Time To Detect (MTTD) improvement with SecuriSphere dashboard vs. raw logs.

---

## Files

- **protocol.md** — Experiment protocol: definitions, timer points, trial structure, success criteria
- **raw_log_trials.md** — Results from Condition A (raw logs only, no dashboard)
- **securisphere_trials.md** — Results from Condition B (with SecuriSphere dashboard)
- **results.md** — Final analysis, comparison, reduction % calculation

---

## Quick Start

### 1. Understand Protocol
```bash
cat protocol.md
```

Key definitions:
- **Timer START:** First HTTP request from attacker
- **Timer STOP:** Operator visually confirms all expected incidents in output/dashboard
- **Success:** All expected incidents detected in both conditions

### 2. Prepare System
```bash
# Start backend services
docker-compose up -d

# Open SecuriSphere dashboard in browser
# http://localhost:3000

# In another terminal, enable log monitoring
tail -f logs/correlation_engine.log
```

### 3. Run Trials (Condition A: Raw Logs)
No dashboard visible. Watch console output for kill chain completion.

```bash
make reset-state
sleep 2
time make attack-a  # Record MTTD in raw_log_trials.md
sleep 30

make reset-state
sleep 2
time make attack-b
sleep 30

make reset-state
sleep 2
time make attack-c
sleep 30

# Repeat 3× total per scenario (9 trials)
```

### 4. Run Trials (Condition B: Dashboard)
Dashboard ON. Watch UI for incident cards + correlations.

```bash
# SecuriSphere dashboard must be open in browser
# http://localhost:3000/incidents

make reset-state
sleep 2
time make attack-a  # Record MTTD in securisphere_trials.md
sleep 30

make reset-state
sleep 2
time make attack-b
sleep 30

make reset-state
sleep 2
time make attack-c
sleep 30

# Repeat 3× total per scenario (9 trials)
```

### 5. Calculate Results
```bash
# Fill in raw_log_trials.md and securisphere_trials.md with measurements
# Then run:

make evaluate-full
```

This auto-generates MTTD metrics from system logs and updates results.md.

### 6. Check Results
```bash
cat results.md

# Success criteria:
# ✅ 18/18 trials completed
# ✅ MTTD reduction ≥70% (target)
```

---

## Timing Tips

- Use `time` command to capture wall-clock duration
- Start timer when first attack log appears
- Stop timer when you visually confirm all expected incidents:
  - **Raw logs:** Stage names visible in console output
  - **Dashboard:** Incident cards appear in UI + correlated in timeline
- Difference = MTTD for that trial

---

## Expected Incidents

**Scenario A (Brute Force):**
- brute_force_attempt
- credential_compromise
- data_exfiltration_risk

**Scenario B (SQL Injection):**
- sql_injection_attempt
- privilege_escalation
- lateral_movement

**Scenario C (Lateral Movement):**
- lateral_movement_attempt (×3)
- privilege_escalation
- data_access_anomaly

---

## Troubleshooting

**Scenario doesn't run?**
- Check `make attack-a` etc. have correct Docker service names
- Verify backend services are running: `docker-compose ps`

**Incidents not appearing?**
- Correlation engine may need warmup (run dummy attack first)
- Check correlation engine logs: `tail -f logs/correlation_engine.log`
- Dashboard UI needs refresh (Ctrl+R)

**Timer not accurate?**
- Close other apps to reduce noise
- System load affects timing; use averages
- Mark anomalies in trial notes and exclude if severe

---

## Success Checklist

- [ ] 3 trials × 3 scenarios × 2 conditions = 18 trials total
- [ ] All trials successful (all expected incidents detected)
- [ ] MTTD measurements recorded in raw_log_trials.md
- [ ] MTTD measurements recorded in securisphere_trials.md
- [ ] `make evaluate-full` runs without errors
- [ ] results.md populated with statistics
- [ ] MTTD reduction ≥70% achieved
