# SecuriSphere — Attack & Simulation Guide

> **Audience:** Anyone — even someone who has never opened this repo before.
> **Promise:** Every command is copy-paste ready. Every expected output is
> shown. No prior knowledge of Docker, Flask, Redis, or SecuriSphere internals
> is assumed. If you have never run this project before, start at Section 0
> and do not skip steps.

---

## Table of Contents

- [0. Before you start (prerequisites)](#0-before-you-start-prerequisites)
- [1. Bring up the stack](#1-bring-up-the-stack)
- [2. Verify every service is healthy](#2-verify-every-service-is-healthy)
- [3. Register the demo site (one-time, required for browser attacks)](#3-register-the-demo-site-one-time-required-for-browser-attacks)
- [4. Open the dashboard](#4-open-the-dashboard)
- [5. Automated attack scenarios](#5-automated-attack-scenarios)
  - [5.1 Scenario A — Brute Force → Credential Compromise → Exfiltration](#51-scenario-a--brute-force--credential-compromise--exfiltration)
  - [5.2 Scenario B — Recon → SQL Injection → Privilege Escalation](#52-scenario-b--recon--sql-injection--privilege-escalation)
  - [5.3 Scenario C — Multi-Hop Lateral Movement](#53-scenario-c--multi-hop-lateral-movement)
  - [5.4 All three in sequence](#54-all-three-in-sequence)
  - [5.5 Speed presets — when to use which](#55-speed-presets--when-to-use-which)
- [6. Manual attacks via ShopSphere (live demo)](#6-manual-attacks-via-shopsphere-live-demo)
  - [6.1 SQL injection in the search bar](#61-sql-injection-in-the-search-bar)
  - [6.2 Brute force on the login page](#62-brute-force-on-the-login-page)
  - [6.3 Path traversal in a URL](#63-path-traversal-in-a-url)
- [7. Browser-layer attacks (Phase 1–3)](#7-browser-layer-attacks-phase-13)
  - [7.1 Synthetic SQL injection event](#71-synthetic-sql-injection-event)
  - [7.2 Synthetic brute-force burst](#72-synthetic-brute-force-burst)
  - [7.3 Reconnaissance scan](#73-reconnaissance-scan)
- [8. How to confirm an attack was detected](#8-how-to-confirm-an-attack-was-detected)
- [9. One-command full demo](#9-one-command-full-demo)
- [10. Reset between runs](#10-reset-between-runs)
- [11. Troubleshooting (every common failure)](#11-troubleshooting-every-common-failure)
- [12. Cheat sheet — every command in this guide](#12-cheat-sheet--every-command-in-this-guide)

---

## 0. Before you start (prerequisites)

You need **four things** installed and one repo cloned. **Do not skip the verification commands** — they take 30 seconds and prevent 90 % of failures.

### 0.1 What to install

| Tool | Minimum version | Why |
|---|---|---|
| **Docker Desktop** | 20.10+ | Runs the 14-container stack |
| **Docker Compose** | 2.0+ (bundled with Desktop) | Orchestrates multi-container start/stop |
| **Bash shell** | any | All commands here use Unix syntax. On Windows use **Git Bash** (comes with Git for Windows) — do **not** use cmd.exe or PowerShell |
| **curl** | any | All health-checks and ingest tests use curl. Pre-installed on macOS/Linux; Git Bash on Windows includes it |
| **Python 3** | 3.8+ | Only needed if you want to pretty-print JSON output (`python -m json.tool`). Optional. |

### 0.2 What to verify (run these now)

```bash
docker --version
# Expected: Docker version 24.x.x or newer

docker compose version
# Expected: Docker Compose version v2.x.x

bash --version
# Expected: GNU bash, version 4.x or 5.x

curl --version
# Expected: curl 7.x or 8.x

docker info | grep -i "server version"
# Expected: a line — if you see "Cannot connect to the Docker daemon",
#           open Docker Desktop and wait for the whale icon to stop animating
```

If **any** of these fail, fix it before continuing. Do not proceed.

### 0.3 Free disk + memory

- **Disk:** ~3 GB free for Docker images
- **RAM:** 4 GB free for the running stack (8 GB total system RAM minimum)
- **Ports the stack will bind on `localhost`:** `3000, 5000, 5001, 5050, 5060, 5070, 5080, 5090, 5432, 6379, 8000, 8080`

Check no one else is using those ports:

```bash
# macOS / Linux
for p in 3000 5000 5001 5050 5060 5070 5080 5090 5432 6379 8000 8080; do
  lsof -i :$p >/dev/null 2>&1 && echo "PORT $p IN USE" || echo "port $p free"
done

# Windows Git Bash
for p in 3000 5000 5001 5050 5060 5070 5080 5090 5432 6379 8000 8080; do
  netstat -ano | grep -q ":$p " && echo "PORT $p IN USE" || echo "port $p free"
done
```

If any port is in use, either stop the process holding it or change the port mapping in `docker-compose.yml` (the `ports:` section of the relevant service).

### 0.4 Get the repo

```bash
# If you don't already have it
git clone https://github.com/yourusername/securisphere.git
cd securisphere

# If you already have it, just cd into it
cd /path/to/securisphere
pwd
# Expected: an absolute path ending in /securisphere
```

**Every command in this guide assumes you are in the repo root.** If you `cd` away, come back before the next command.

---

## 1. Bring up the stack

### 1.1 First-time setup (run once, ever)

```bash
make setup
```

**What this does:** copies `.env.example` to `.env` and seeds the database schema (`scripts/init_db.sql`). Idempotent — safe to re-run.

**Expected output (last line):**
```
[setup] SecuriSphere setup complete. Run 'make start' next.
```

### 1.2 Start the containers

```bash
make start
```

**What this does:** runs `docker compose up --build -d`. The `-d` means "detached" — containers start in the background. The first run takes **3–5 minutes** because Docker has to build 11 images. Subsequent runs take 15–30 seconds.

**Expected output (last few lines):**
```
✔ Container securisphere-redis           Started
✔ Container securisphere-db              Started
✔ Container securisphere-api             Started
✔ Container securisphere-auth            Started
✔ Container securisphere-netmon          Started
✔ Container securisphere-apimon          Started
✔ Container securisphere-authmon         Started
✔ Container securisphere-browsermon      Started
✔ Container securisphere-correlator      Started
✔ Container securisphere-topology        Started
✔ Container securisphere-backend         Started
✔ Container securisphere-dashboard       Started
✔ Container securisphere-webapp          Started
```

13 always-on containers should be `Started`. The 14th, `securisphere-attacker`, only starts on demand via the `attack-*` targets.

**If you see "Started" but the service crashes 5 seconds later**, that's normal for the first 30 s while it waits for Redis/Postgres. Wait, then move to Section 2.

### 1.3 Confirm containers are actually running

```bash
make ps
# (alias for: docker compose ps)
```

**Expected:** every row shows `running` or `healthy` in the STATUS column. **If any row shows `restarting`, `exited`, or `unhealthy`**, jump to [Section 11.2](#112-a-container-is-restarting-or-unhealthy) before continuing.

---

## 2. Verify every service is healthy

**Do not skip this section.** A flaky stack will silently swallow attack events and you will think the rules are broken when really the engine never came up.

### 2.1 One-command health check

```bash
make health-full
```

**Expected output:** every line ends with `OK` or `200`. If any line shows `FAIL` or a non-200 HTTP code, **wait 15 seconds and re-run** — some services take a moment to settle. If it still fails, jump to [Section 11](#11-troubleshooting-every-common-failure).

### 2.2 Per-service manual checks (use if `health-full` is missing or fails)

```bash
# Redis (event bus)
docker exec securisphere-redis redis-cli ping
# Expected: PONG

# PostgreSQL (persistence)
docker exec securisphere-db pg_isready -U securisphere_user
# Expected: /var/run/postgresql:5432 - accepting connections

# API server (target)
curl -sf http://localhost:5000/api/health && echo " — api-server OK"

# Auth service (target)
curl -sf http://localhost:5001/auth/health && echo " — auth-service OK"

# API monitor
curl -sf http://localhost:5050/monitor/health && echo " — api-monitor OK"

# Auth monitor
curl -sf http://localhost:5060/monitor/health && echo " — auth-monitor OK"

# Browser monitor (Phase 1–3)
curl -sf http://localhost:5090/health && echo " — browser-monitor OK"

# Correlation engine
curl -sf http://localhost:5070/engine/health && echo " — correlation-engine OK"

# Topology collector
curl -sf http://localhost:5080/health && echo " — topology-collector OK"

# Backend aggregation API
curl -sf http://localhost:8000/api/health && echo " — backend OK"

# Dashboard (returns HTML, just check it's reachable)
curl -sf -o /dev/null http://localhost:3000 && echo " — dashboard OK"

# ShopSphere web-app
curl -sf -o /dev/null http://localhost:8080 && echo " — web-app OK"
```

You should see **11 OK lines**. If even one is missing, fix it before attacking. An attack against an unhealthy stack tells you nothing.

---

## 3. Register the demo site (one-time, required for browser attacks)

The browser-monitor (Phase 1) **rejects events from unknown `site_id` values**. You must register the ShopSphere site once per database lifetime.

```bash
make register-demo-site
```

**Expected output (a JSON blob like this):**
```json
{
    "site_id": "abc12345",
    "name": "ShopSphere",
    "url": "http://localhost:8080",
    "snippet": "<script>window.__SECURISPHERE_SITE_ID__ = \"abc12345\";</script><script src=\"/static/agent.js\" async></script>"
}
```

**Save the `site_id` value** — Section 7 needs it. The `site_id` is deterministic (`first 8 chars of sha256(url+name)`), so re-running the command returns the same value; it is safe to run it again any time.

If you skip this step, all browser-layer ingest attempts will return `{"published": 0, "skipped": N}` and **no browser-layer rule will fire** — by design.

---

## 4. Open the dashboard

```
http://localhost:3000
```

**You should see:** the SecuriSphere dashboard with a top navbar, a tab strip (`Dashboard`, `Events`, `Incidents`, `Risk`, `System`, `Topology`), and a live event counter that ticks up every few seconds.

**Tabs you will use during attacks:**
- **Events** — raw events flowing through Redis (one row per detected hit)
- **Incidents** — correlated kill chains (one row per rule firing)
- **Risk** — per-source risk scores with threat-level color
- **Topology** — D3 force-directed service graph; lights up red during an attack

**Keep this tab open** in your browser while running attacks. Every detection is visible within ~2 seconds of the attack happening.

---

## 5. Automated attack scenarios

These run inside the `attack-simulator` container (compose profile `attack`). They do not require any manual interaction — just one command per scenario.

### 5.1 Scenario A — Brute Force → Credential Compromise → Exfiltration

**What it simulates:** an attacker hammers `auth-service` with a credential list, eventually finds a working password, then uses the session to pull sensitive data from the API.

**Targets:** `auth-service` → `api-server`

**Expected duration:** ~30 s (normal speed)

**Run it:**
```bash
make attack-a
```

**What you should see in the simulator log (last lines):**
```
[Scenario A] Brute force phase complete: 5 successful logins discovered
[Scenario A] Credential compromise phase complete
[Scenario A] Exfiltration phase complete
[Scenario A] === DONE — 1 incident expected ===
```

**What you should see on the dashboard:**
- **Events tab** — bursts of `brute_force`, `credential_stuffing`, `sensitive_access` events
- **Incidents tab** — at least one incident of type `credential_compromise` or `data_exfiltration_risk`
- **Risk tab** — the attacker IP climbing into `threatening` (orange) or `critical` (purple)

**Confirm via API:**
```bash
curl -s "http://localhost:8000/api/incidents?limit=5" | python -m json.tool
```
→ at least one incident in the JSON. If the array is empty, see [Section 11.4](#114-attack-ran-but-no-incidents-appeared).

### 5.2 Scenario B — Recon → SQL Injection → Privilege Escalation

**What it simulates:** attacker probes the API surface, finds an injectable parameter, escalates to admin.

**Targets:** `api-server`

**Expected duration:** ~25 s (normal speed)

**Run it:**
```bash
make attack-b
```

**What you should see on the dashboard:**
- **Events tab** — `port_scan`, `endpoint_enumeration`, `sql_injection`, `privilege_escalation` events
- **Incidents tab** — `recon_to_exploitation` and likely `critical_exploit_attempt`

### 5.3 Scenario C — Multi-Hop Lateral Movement

**What it simulates:** attacker compromises one service and pivots through 4 services in sequence — the killer feature SecuriSphere exists to detect.

**Targets:** `auth-service` → `api-server` → multiple endpoints

**Expected duration:** ~40 s (normal speed)

**Run it:**
```bash
make attack-c
```

**What you should see on the dashboard:**
- **Topology tab** — services light up RED in sequence as the attack hops
- **Incidents tab** — `full_kill_chain` incident with `service_path` containing 3+ services

### 5.4 All three in sequence

```bash
make attack-abc
```

Runs A → wait 30 s → B → wait 30 s → C. Total ~3 minutes. Use this when recording a demo.

### 5.5 Speed presets — when to use which

| Preset | Multiplier | When to use |
|---|---|---|
| `make attack-fast` | 0.05× (≈20× faster) | CI runs, smoke tests, "did anything break" |
| (default in `attack-a/b/c`) | 1.0× | Normal evaluation, MTTD measurement |
| `make attack-demo` | 1.5× | Live audience — slow enough to narrate, fast enough to keep attention |
| `make attack-slow` | 3× | Classroom walkthroughs, debugging a specific rule |

To override speed for a single scenario:
```bash
docker compose run --rm attack-simulator python run_all.py --scenario a --speed slow
```

---

## 6. Manual attacks via ShopSphere (live demo)

These are the attacks you run **with your own hands** in a browser to demonstrate detection live to an audience. They use the ShopSphere "victim" e-commerce site at `http://localhost:8080`.

### 6.1 SQL injection in the search bar

1. Open `http://localhost:8080` in a browser
2. In the search bar, type **exactly** this:
   ```
   ' OR '1'='1
   ```
3. Press Enter or click the Search button

**What happens:**
- The page submits to `/api/products?search=...`
- `api-monitor` regex-matches the SQLi pattern, publishes a `sql_injection` event
- The correlation engine fires `critical_exploit_attempt` after the second hit (cooldown protects against single-event noise — submit it twice if needed)
- **Dashboard → Incidents tab** shows the new incident within ~2 s

**Reset:** clear the search bar, refresh.

### 6.2 Brute force on the login page

1. Open `http://localhost:8080/login.html`
2. Username: `admin`
3. Try these passwords in order, hitting Login between each:
   ```
   pass1
   pass2
   pass3
   pass4
   pass5
   pass6
   ```
4. Total time: under 60 seconds

**What happens:**
- Each failed attempt publishes a `brute_force` event from `auth-monitor`
- After **5 failures within 60 s**, the engine fires `brute_force_attempt` (high severity) and bumps the source IP into `threatening` risk
- **Dashboard → Risk tab** shows the IP climbing in real time

### 6.3 Path traversal in a URL

1. In the browser address bar:
   ```
   http://localhost:8080/api/files?path=../../../etc/passwd
   ```
2. Press Enter

**What happens:**
- `api-monitor` matches the `../` pattern, publishes a `path_traversal` event
- The engine fires `critical_exploit_attempt` after the second attempt
- **Dashboard → Incidents tab** shows it

---

## 7. Browser-layer attacks (Phase 1–3)

These exercise the **fourth monitor layer** — `browser-monitor` on port 5090. Unlike the manual ShopSphere attacks above, these go directly to the browser-monitor's `/api/ingest` endpoint, simulating what `agent.js` would send.

> **Required:** complete [Section 3](#3-register-the-demo-site-one-time-required-for-browser-attacks) first and have the `site_id` value handy. The examples below use `abc12345` as a placeholder — **replace it with your actual site_id**.

### 7.1 Synthetic SQL injection event

```bash
SITE_ID="abc12345"   # ← replace with your real site_id from step 3

curl -X POST http://localhost:5090/api/ingest \
  -H "Content-Type: application/json" \
  -d "{
    \"events\": [{
      \"event_type\": \"fetch_request\",
      \"source_layer\": \"browser-agent\",
      \"site_id\": \"$SITE_ID\",
      \"target_entity\": \"/products\",
      \"target_url\": \"/products?id=1%27%20OR%20%271%27=%271\",
      \"severity\": \"HIGH\",
      \"correlation_tags\": [\"sql-injection\"]
    }]
  }"
```

**Expected response:**
```json
{"published": 1, "skipped": 0}
```

**Confirm detection:**
```bash
curl -s "http://localhost:8000/api/incidents?limit=5" | python -m json.tool | grep incident_type
```
→ look for `"incident_type": "browser_sql_injection_attempt"`. If you see `"skipped": 1`, your `site_id` is wrong — re-run [Section 3](#3-register-the-demo-site-one-time-required-for-browser-attacks).

### 7.2 Synthetic brute-force burst

Sends 6 `auth_failure` events from the same site_id within a few seconds, which is enough to trip Rule 12 (`browser_brute_force` — needs ≥5 in 60 s).

```bash
SITE_ID="abc12345"   # ← replace

for i in 1 2 3 4 5 6; do
  curl -s -X POST http://localhost:5090/api/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"events\": [{
        \"event_type\": \"auth_failure\",
        \"source_layer\": \"browser-agent\",
        \"site_id\": \"$SITE_ID\",
        \"target_entity\": \"/login\",
        \"target_url\": \"http://localhost:8080/login.html\",
        \"severity\": \"MEDIUM\",
        \"correlation_tags\": [\"failed-login\"]
      }]
    }" > /dev/null
  echo "sent failure $i"
done

# Wait 2 s for the engine to consume them
sleep 2

curl -s "http://localhost:8000/api/incidents?limit=5" | python -m json.tool | grep -A 2 browser_brute_force
```

**Expected:** an incident with `"incident_type": "browser_brute_force"` and the matching site_id in `extra`.

### 7.3 Reconnaissance scan

Sends 12 events to 12 different `target_entity` values within a few seconds, tripping Rule 13 (`browser_recon_scan` — ≥10 distinct targets in 30 s).

```bash
SITE_ID="abc12345"   # ← replace

for path in /admin /backup /config /db /debug /env /git /hidden /internal /private /staging /test; do
  curl -s -X POST http://localhost:5090/api/ingest \
    -H "Content-Type: application/json" \
    -d "{
      \"events\": [{
        \"event_type\": \"fetch_request\",
        \"source_layer\": \"browser-agent\",
        \"site_id\": \"$SITE_ID\",
        \"target_entity\": \"$path\",
        \"target_url\": \"http://localhost:8080$path\",
        \"severity\": \"INFO\",
        \"correlation_tags\": []
      }]
    }" > /dev/null
done

sleep 2
curl -s "http://localhost:8000/api/incidents?limit=5" | python -m json.tool | grep browser_recon_scan
```

**Expected:** `"incident_type": "browser_recon_scan"` in the output.

---

## 8. How to confirm an attack was detected

After **any** attack, run these in order. They go from "raw" to "correlated".

### 8.1 Are events flowing on the Redis bus?

```bash
docker exec securisphere-redis redis-cli SUBSCRIBE security_events
# (run an attack in another terminal — you should see JSON events stream by)
# Press Ctrl-C to exit when you've seen them
```

If **nothing** streams, the monitors are not publishing. Check `make logs-apimon`, `make logs-authmon`, `make logs-browser`.

### 8.2 Are events being persisted?

```bash
curl -s "http://localhost:8000/api/events?limit=10" | python -m json.tool
```

→ should show 10 most recent events with timestamps. If empty, the backend cannot reach Postgres or Redis — see [Section 11.5](#115-events-tab-is-empty).

### 8.3 Are incidents being created?

```bash
curl -s "http://localhost:8000/api/incidents?limit=10" | python -m json.tool
```

→ each item has `incident_id`, `incident_type`, `severity`, `correlated_event_count`, `mitre_techniques`. If this returns an empty list after a successful attack, jump to [Section 11.4](#114-attack-ran-but-no-incidents-appeared).

### 8.4 Are kill chains being persisted?

```bash
curl -s "http://localhost:8000/api/kill-chains?limit=10" | python -m json.tool
```

→ Phase 3's list endpoint. Each kill chain has `incident_id`, `service_path`, `mitre_techniques`, `mttd_seconds`.

### 8.5 What's the per-IP risk score?

```bash
curl -s "http://localhost:8000/api/risk-scores" | python -m json.tool
```

→ shows current scores. After a successful attack scenario, the attacker IP should be in `threatening` (71–150) or `critical` (>150).

### 8.6 What MITRE techniques have fired?

```bash
curl -s "http://localhost:8000/api/mitre-mapping" | python -m json.tool
```

→ frequency map of every MITRE technique that has ever triggered. After scenarios A+B+C you should see `T1110`, `T1190`, `T1078`, `T1530`, `T1046`, `T1083`, `T1021` populated.

---

## 9. One-command full demo

For live audiences, this is the single command that does everything end-to-end:

```bash
make demo-full
```

**What this does** (from `scripts/run_demo.sh`):
1. Starts the stack if not running
2. Polls 4 health endpoints for up to 90 s
3. Opens `http://localhost:3000` in your default browser
4. Sets `demo:active` in Redis (the dashboard's `DemoBanner` lights up amber)
5. Runs Scenario A at `demo` speed
6. Clears the demo flag

**Total time:** ~2 minutes. Watch the dashboard during the run — every detection is visible live.

---

## 10. Reset between runs

After multiple attack runs, the dashboard fills up with stale data. Pick the right reset for your situation:

### 10.1 Soft reset — clear events + risk scores, keep containers running

```bash
curl -X POST http://localhost:8000/api/events/clear
docker exec securisphere-redis redis-cli FLUSHDB
```

Fast (~1 s). Use between scenario runs in the same demo.

### 10.2 Hard reset — restart all containers (keeps DB data)

```bash
make restart
```

~30 s. Use if a single service is acting weird.

### 10.3 Nuclear reset — DESTROYS all data, rebuilds from scratch

```bash
make reset
```

⚠️ **This is destructive.** It runs `docker compose down -v` (which deletes the Postgres + Redis volumes), then re-runs `make setup`. You will lose every event, incident, kill chain, registered site, and risk score. Use only when you want a pristine state — e.g. before recording the final research-paper evaluation.

After `make reset`, you must re-do [Section 1.2](#12-start-the-containers) (`make start`) and [Section 3](#3-register-the-demo-site-one-time-required-for-browser-attacks) (`make register-demo-site`).

---

## 11. Troubleshooting (every common failure)

### 11.1 `make start` fails with "port already in use"

Another process is holding one of the ports SecuriSphere needs. Find it:

```bash
# macOS / Linux
lsof -i :8080
# Windows Git Bash
netstat -ano | grep ":8080 "
```

Either kill the process or change the host port mapping in `docker-compose.yml` (e.g. `"8081:80"` instead of `"8080:80"`).

### 11.2 A container is restarting or unhealthy

```bash
make ps
# Find the bad service, e.g. securisphere-correlator

make logs-engine     # or logs-api, logs-auth, logs-netmon, logs-apimon,
                     #     logs-authmon, logs-browser, logs-backend,
                     #     logs-frontend, logs-topology
```

Read the last 30 lines. Common causes:
- **"Connection refused" on Redis/Postgres** → the dependency hasn't passed its healthcheck yet. Wait 30 s and re-check.
- **"OperationalError: FATAL: database does not exist"** → run `make reset` (destructive) or manually run `scripts/init_db.sql`.
- **"OSError: [Errno 98] Address already in use"** → another container is binding the same internal port. `make stop && make start`.

### 11.3 `make register-demo-site` returns `database error`

The browser-monitor cannot reach Postgres or the `registered_sites` table doesn't exist:

```bash
make logs-browser
# Look for: "init_db failed" or "psycopg2.OperationalError"

# Verify the table exists
docker exec securisphere-db psql -U securisphere_user -d securisphere_db \
  -c "\d registered_sites"
```

If the table is missing, the init script didn't run. Run `make reset` (destructive) or manually:

```bash
docker exec -i securisphere-db psql -U securisphere_user -d securisphere_db < scripts/init_db.sql
```

### 11.4 Attack ran but no incidents appeared

Three things to check, in this exact order:

1. **Is the correlation engine subscribed to Redis?**
   ```bash
   make logs-engine | grep -i "Connected to Redis"
   # Expected: "Connected to Redis at redis:6379"
   ```
2. **Are events reaching the bus?**
   ```bash
   docker exec securisphere-redis redis-cli SUBSCRIBE security_events
   # In another terminal: re-run the attack. If nothing streams, the monitor is broken.
   ```
3. **Did rules trigger but get rate-limited?** Check the engine log:
   ```bash
   make logs-engine | tail -100 | grep -i "rule\|incident\|cooldown"
   ```
   Many rules have a 5-minute cooldown per source IP. If you ran the same scenario twice in a row, the second run may be silenced. Wait 5 min or `make restart`.

### 11.5 Events tab is empty

```bash
# Backend can't reach Postgres
make logs-backend | grep -i "postgres\|database"

# Or the dashboard is hitting wrong URL
# Open browser DevTools → Network tab → look for failed XHRs to localhost:8000
```

If the backend logs show `connection refused`, the database container isn't ready yet. Wait 30 s, then refresh the dashboard.

### 11.6 Browser ingest returns `{"published": 0, "skipped": 1}`

The `site_id` you sent is **not registered**. Either:
- You forgot to run `make register-demo-site`, or
- You used the wrong `site_id` value in the curl payload, or
- You ran `make reset` since registration (which wipes `registered_sites`)

Re-run [Section 3](#3-register-the-demo-site-one-time-required-for-browser-attacks).

### 11.7 Dashboard at `localhost:3000` is blank or "cannot connect"

```bash
make logs-frontend
```

If you see `Compiled successfully` but the page is blank, hard-refresh the browser (`Ctrl-Shift-R` / `Cmd-Shift-R`). If you see build errors, the React build is broken — `make build-frontend && make restart`.

### 11.8 "Cannot connect to the Docker daemon"

Docker Desktop is not running. Open it, wait for the whale icon to stop animating, then re-run your command.

### 11.9 Everything is broken and I want to start over

```bash
make reset      # destructive — wipes all data
make start
make health-full
make register-demo-site
```

If even `make reset` fails, the absolute last resort:

```bash
docker compose down -v --remove-orphans
docker system prune -af --volumes   # ⚠️ removes ALL Docker data on your machine
make setup
make start
```

---

## 12. Cheat sheet — every command in this guide

```bash
# Setup (once ever)
make setup
make start
make health-full
make register-demo-site

# Open these in a browser
http://localhost:3000        # SecuriSphere dashboard
http://localhost:8080        # ShopSphere target site

# Automated attacks
make attack-a                # Brute force → credential compromise → exfil
make attack-b                # Recon → SQL injection → privesc
make attack-c                # Multi-hop lateral movement
make attack-abc              # All three in sequence
make attack-fast             # All scenarios at max speed (CI)
make attack-demo             # Demo speed for live audience
make attack-slow             # Walkthrough speed for classroom
make demo-full               # One-command full demo

# Browser-layer manual attacks (set SITE_ID first — see Section 7)
SITE_ID="abc12345"           # from `make register-demo-site`
# ...then the curl examples in Section 7

# Verify detection
curl -s http://localhost:8000/api/events?limit=10        | python -m json.tool
curl -s http://localhost:8000/api/incidents?limit=10     | python -m json.tool
curl -s http://localhost:8000/api/kill-chains?limit=10   | python -m json.tool
curl -s http://localhost:8000/api/risk-scores            | python -m json.tool
curl -s http://localhost:8000/api/mitre-mapping          | python -m json.tool

# Logs (one per service)
make logs                    # all services
make logs-engine             # correlation engine
make logs-browser            # browser monitor (Phase 1–3)
make logs-apimon             # api monitor
make logs-authmon            # auth monitor
make logs-backend            # aggregation API
make logs-frontend           # dashboard

# Reset
make restart                 # restart containers, keep data
make reset                   # ⚠️ destructive — wipe DB and Redis

# Stop
make stop
```

---

**Last updated:** Phase 3 (browser monitor wired into compose, kill-chains list endpoint, topology history persistence). If anything in this guide does not match what you see, file an issue or ping the maintainer — the guide is the contract.
