# SecuriSphere Demo Checklist

End-to-end verification for fresh Docker environment. Run this before every presentation / recording / stakeholder demo.

---

## 0. Prerequisites

- [ ] Docker Desktop running
- [ ] `docker --version` ≥ 20.10
- [ ] `docker compose version` ≥ 2.0
- [ ] Ports free: 3000, 5090, 8000, 8080, 6379 (check `netstat -ano | findstr LISTENING`)
- [ ] Repo on `main` branch, clean working tree (`git status`)

---

## 1. Clean Slate (Fresh Docker Environment)

```bash
# Stop & remove all containers + volumes + orphans
docker compose down -v --remove-orphans

# Purge dangling images (optional but recommended)
docker image prune -f

# Verify zero SecuriSphere containers
docker ps -a | grep securi || echo "clean ✓"

# Verify zero persistent volumes
docker volume ls | grep securi || echo "no volumes ✓"
```

- [ ] No leftover containers
- [ ] No leftover volumes
- [ ] No leftover networks

---

## 2. One-Command Boot

```bash
make demo-full
```

Expected timeline:
- [ ] `docker compose up -d` completes without errors
- [ ] Health probes pass within 90s (backend, frontend, redis, auth, api, attacker)
- [ ] Browser opens to `http://localhost:3000`
- [ ] Attack scenario auto-runs after health check

---

## 3. Service Health Verification

```bash
# Backend API
curl -sf http://localhost:8000/api/system/status | python -m json.tool

# Browser-monitor
curl -sf http://localhost:5090/api/health || echo "check browser-monitor"

# ShopSphere target app
curl -sf http://localhost:8080/ | head -5

# Redis
docker compose exec redis redis-cli ping
```

- [ ] All services return 200
- [ ] Redis responds PONG
- [ ] No restart loops: `docker compose ps` shows all `Up` (no `Restarting`)

---

## 4. Register Demo Site

```bash
make register-demo-site
```

- [ ] Returns JSON with `site_id` and `api_key`
- [ ] No `registration failed` message
- [ ] Site appears in browser-monitor DB

---

## 5. Dashboard Smoke Test

Open `http://localhost:3000` in Chrome/Edge.

- [ ] Login succeeds (default creds: `admin/admin`)
- [ ] Dashboard loads without console errors (F12 → Console)
- [ ] KPI cards render with non-zero values
- [ ] Incident list populates as attacks run
- [ ] Topology graph renders
- [ ] MITRE panel shows techniques
- [ ] Mode switcher works (Triage / Grid / Story)

---

## 6. Demo Banner

Trigger an attack:

```bash
make attack-a
```

- [ ] Amber banner appears at top of dashboard within 3s
- [ ] Banner text reads: "Scenario A — Brute Force → Credential Compromise → Data Exfiltration"
- [ ] "ATTACK IN PROGRESS" pill visible
- [ ] Pulsing dot animation visible
- [ ] Banner disappears when scenario ends

Repeat for:
- [ ] `make attack-b` — shows "Scenario B" banner
- [ ] `make attack-c` — shows "Scenario C" banner

---

## 7. Kill Chain Detection

After each attack:

```bash
curl -s http://localhost:8000/api/incidents | python -m json.tool | grep -E "incident_type|severity"
```

- [ ] **Scenario A:** `brute_force_attempt`, `credential_compromise`, `data_exfiltration_risk` present
- [ ] **Scenario B:** `sql_injection_attempt`, `privilege_escalation`, `lateral_movement` present
- [ ] **Scenario C:** `lateral_movement_attempt` (×3), `privilege_escalation`, `data_access_anomaly` present

---

## 8. MTTD & Metrics

```bash
make evaluate-full
```

- [ ] Runs without Python traceback
- [ ] Generates `mttd_results.csv`
- [ ] Generates Markdown MTTD table
- [ ] MTTD reduction ≥70% (target)

---

## 9. Browser UX

- [ ] No 4xx/5xx requests in Network tab
- [ ] No console errors/warnings
- [ ] WebSocket live feed updating
- [ ] Animations smooth (60fps)
- [ ] Responsive on laptop (1440×900) and desktop (1920×1080)

---

## 10. Cleanup

```bash
docker compose down -v
```

- [ ] Clean shutdown, no hanging processes
- [ ] Volumes removed
- [ ] Ports released

---

## Pass Criteria

- ✅ All items above checked
- ✅ No manual intervention required at any step
- ✅ `make demo-full` is truly one-command
- ✅ Banner correctly identifies active scenario
- ✅ Clean slate → full demo in <3 minutes

## Known Edge Cases

| Symptom | Cause | Fix |
|---------|-------|-----|
| Banner never appears | Redis `demo:active` key not set | Check `backend/api/app.py:906` — ensure attacker publishes before starting |
| Health probe timeout | Slow first pull | Pre-pull images: `docker compose pull` |
| Port conflict | Other app on 3000/8000 | Stop conflict or change ports in `docker-compose.yml` |
| Empty incident list | Attacker not reaching services | Check `docker compose logs attack-simulator` |
| Dashboard blank | API unreachable from frontend | Verify `VITE_API_URL` env matches backend URL |

---

## Sign-off

- **Tester:** ________________
- **Date:** ________________
- **Result:** [ ] PASS  [ ] FAIL
- **Commit:** ________________
