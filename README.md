# 🛡️ SecuriSphere

> The first open-source system that detects east-west lateral movement
> between named microservices and reconstructs the full attack kill chain
> on a live service dependency graph — in real time.


---

## Table of Contents
- [The Problem](#the-problem)
- [What Makes SecuriSphere Different](#what-makes-securisphere-different)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Attack Scenarios & MTTD Results](#attack-scenarios--mttd-results)
- [MITRE ATT&CK for Containers Coverage](#mitre-attck-for-containers-coverage)
- [Features](#features)
- [ShopSphere — Live Demo Web App](#-shopsphere--live-demo-web-app)
- [Browser Monitoring Layer (Phase 1–3)](#browser-monitoring-layer-phase-13)
- [Correlation Rules](#correlation-rules)
- [Risk Scoring](#risk-scoring)
- [Running Attacks](#running-attacks)
- [Step-by-Step Attack Guide](ATTACK_GUIDE.md)
- [Evaluation](#evaluation)
- [Dashboard](#dashboard)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## The Problem

Legacy SIEM tools (Splunk, Wazuh, Elastic) correlate security events by
IP address. In Docker environments, container IPs change on every restart,
redeploy, or scaling event. This makes them structurally blind to
east-west lateral movement in microservice architectures.

| What happened | What legacy SIEM sees |
|---|---|
| Attacker brute-forces `auth-service`, pivots to `api-gateway`, exfiltrates data from `payment-service` | Three unrelated events on three unrelated IPs that rotated between the restarts |
| Kill chain spans 4 services over 90 seconds | Four disconnected alerts across four different `src_ip` values |
| Same compromised account used from 3 different container IPs | Three separate "failed login" events, none correlated |

**The gap in one sentence:** No existing open-source tool can detect
lateral movement between named microservices in a containerised environment.

---

## What Makes SecuriSphere Different

| Capability | SecuriSphere | Falco | Wazuh | Elastic SIEM | Cilium |
|---|:---:|:---:|:---:|:---:|:---:|
| Service-name-aware correlation (not IP-based) | ✅ | ❌ | ❌ | ❌ | ⚠️ |
| Multi-layer (network + API + auth) in one engine | ✅ | ❌ | ⚠️ | ⚠️ | ❌ |
| Kill-chain reconstruction across services | ✅ | ❌ | ❌ | ❌ | ❌ |
| Live service dependency graph | ✅ | ❌ | ❌ | ❌ | ✅ |
| MTTD measured end-to-end in the framework | ✅ | ❌ | ❌ | ❌ | ❌ |
| MITRE ATT&CK for Containers mapping | ✅ | ⚠️ | ⚠️ | ⚠️ | ❌ |
| One-command demo with live attack simulator | ✅ | ❌ | ❌ | ❌ | ❌ |
| Open-source, self-hosted, Docker-first | ✅ | ✅ | ✅ | ⚠️ | ✅ |

---

## Quick Start

```bash
git clone https://github.com/yourusername/securisphere.git
cd securisphere

# First time setup
make setup

# Start the full stack (13 always-on services + attack-simulator profile = 14 total)
make start

# Verify every service is healthy before attacking
make health-full

# Register the demo site so browser-agent events will be accepted
make register-demo-site

# Run the live demo (opens dashboard, runs attack automatically)
make demo-full
```

> **First time here?** Read [ATTACK_GUIDE.md](ATTACK_GUIDE.md) — it walks through
> every command, every expected output, and every dashboard URL with zero
> prior-knowledge assumptions.

Access points:
- Security Dashboard: http://localhost:3000
- ShopSphere Target App: http://localhost:8080
- Backend API + Docs: http://localhost:8000/api/metrics
- Browser Monitor (Phase 1–3): http://localhost:5090/health

### Prerequisites
- Docker Desktop (v20.10+) / Docker Compose (v2.0+)
- 4 GB+ RAM available
- Ports 3000, 5000–5001, 5050–5070, 5080, **5090**, 5432, 6379, 8000, 8080 available

## Deploy on Render

This repo now includes a Render Blueprint file: `render.yaml`.

It provisions:
- `securisphere-backend` (Python web service)
- `securisphere-dashboard` (static frontend)
- `securisphere-redis` (managed Redis)
- `securisphere-db` (managed PostgreSQL)

Deploy steps:

1. Push this repo to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select your repository and deploy using `render.yaml`.
4. After deploy, open:
   - Dashboard: Render URL for `securisphere-dashboard`
   - API health: `<backend-url>/api/health`

Notes:
- Backend now reads Render's `PORT` automatically.
- `VITE_API_URL` is wired to the backend service URL in `render.yaml`.
- This cloud setup is a simplified deployment for dashboard/API use, not the full local 13+ container attack lab.

---

## Architecture

```mermaid
graph TD
    User((User/Attacker)) --> WebApp["ShopSphere Web App :8080"]
    
    subgraph "Target Environment"
        WebApp --> API[API Server :5000]
        WebApp --> Auth[Auth Service :5001]
        DB[(Postgres :5432)]
    end
    
    subgraph "Monitoring Layer"
        NetMon[Network Monitor]
        APIMon[API Monitor :5050]
        AuthMon[Auth Monitor :5060]
        BrowserMon[Browser Monitor :5090]
    end

    WebApp -. serves agent.js .-> Browser[(Browser / agent.js)]
    Browser -->|POST /api/ingest| BrowserMon
    
    subgraph "Processing Layer"
        Redis[(Redis Event Bus :6379)]
        Engine[Correlation Engine :5070]
    end
    
    subgraph "Presentation Layer"
        Backend[Backend API :8000]
        Dash[React Dashboard :3000]
    end
    
    API --> NetMon
    API --> APIMon
    Auth --> AuthMon
    
    NetMon --> Redis
    APIMon --> Redis
    AuthMon --> Redis
    BrowserMon --> Redis
    
    Redis --> Engine
    Engine --> Redis
    Redis --> Backend
    Backend --> Dash
```

### Data Flow
1. **Attack Occurs**: Malicious traffic hits the Target services.
2. **Detection**: Monitors capture logs/traffic, apply immediate detection rules (e.g., regex for SQLi), and publish normalized events to Redis.
3. **Correlation**: The Engine consumes events, updates risk scores, and checks for multi-event patterns (Rules).
4. **Response**: If a rule triggers, an Incident is created and published.
5. **Visualization**: The Backend pushes updates via WebSocket to the Dashboard for real-time alerts.

### System Components

| Service | Port | Description |
|---------|------|-------------|
| **securisphere-webapp** | 8080 | ShopSphere Victim E-commerce (Nginx) |
| **securisphere-dashboard** | 3000 | Security Dashboard UI (React + Tailwind) |
| **securisphere-api** | 5000 | Vulnerable Target API (Flask) |
| **securisphere-auth** | 5001 | Target Auth Service (Flask) |
| **securisphere-apimon** | 5050 | Detects SQLi, XSS, Path Traversal |
| **securisphere-authmon** | 5060 | Detects Brute Force, Cred Stuffing |
| **securisphere-browsermon** | 5090 | Browser-layer agent ingest + site registration (Phase 1–3) |
| **securisphere-correlator** | 5070 | Core Logic: Rules + Risk Scoring |
| **securisphere-topology** | 5080 | Live service dependency graph |
| **securisphere-backend** | 8000 | Aggregates data for Dashboard |
| **securisphere-redis** | 6379 | Event Bus & State Store |
| **securisphere-db** | 5432 | User & Product Database |

---

## Attack Scenarios & MTTD Results

SecuriSphere is validated against three formally-named attack scenarios.
Run `make evaluate-full` to generate real MTTD measurements.

| Scenario | Description | Entry Point | Target |
|---|---|---|---|
| Scenario A | Brute Force → Credential Compromise → Exfiltration | auth-service | payment-service |
| Scenario B | Reconnaissance → SQL Injection → Privilege Escalation | frontend | payment-service |
| Scenario C | Multi-Hop Lateral Movement (4 hops) | auth-service | payment-service |

**MTTD Comparison** (detailed results in `experiment/` directory):

| Scenario | MTTD — Raw Logs | MTTD — SecuriSphere | Reduction |
|---|---|---|---|
| Scenario A | — | — | — |
| Scenario B | — | — | — |
| Scenario C | — | — | — |

### Running MTTD Trials

1. **Review protocol:** `cat experiment/protocol.md`
2. **Run controlled trials:**
   - Condition A (raw logs): `make attack-a`, `make attack-b`, `make attack-c` (3× each, no dashboard)
   - Condition B (dashboard): Open SecuriSphere, run same attacks
3. **Record results** in `experiment/raw_log_trials.md` and `experiment/securisphere_trials.md`
4. **Generate metrics:** `make evaluate-full` (auto-generates from system logs)
5. **See final report:** `cat experiment/results.md`

Target reduction: **≥70% MTTD improvement with SecuriSphere dashboard**

---

## MITRE ATT&CK for Containers Coverage

| Technique ID | Name | Detected At | Rule |
|---|---|---|---|
| T1110 | Brute Force | auth-service | Repeated failed logins within window |
| T1078 | Valid Account Compromise | auth-service | Successful login after brute force |
| T1021 | Lateral Movement via Service API | api-gateway | Unusual inter-service request pattern |
| T1068 | Privilege Escalation | payment-service | Elevated permission request from non-admin |
| T1046 | Internal Reconnaissance | multiple | Service discovery request pattern |
| T1041 | Data Exfiltration | payment-service | Anomalous outbound data volume |
| T1595 | Active Scanning | frontend | Port/endpoint scanning detected |
| T1190 | Exploit Public-Facing Application | api-gateway | SQL injection / path traversal |
| T1003 | Credential Dumping | auth-service | Unusual auth database query |
| T1071 | Application Layer Protocol abuse | api-gateway | Unusual protocol usage |
| T1083 | File and Directory Discovery | api-gateway | Path traversal attempts |
| T1530 | Data from Cloud Storage | payment-service | Mass data read from storage |

---

## Features

- **Real-time Multi-Layer Monitoring**: Simultaneous visibility into Network traffic, API requests, and Authentication events.
- **Unified Event Schema**: All events are normalized to a standard JSON format inspired by OCSF.
- **Advanced Correlation Engine**: 9 built-in rules detect complex kill chains, not just isolated alerts.
- **Dynamic Risk Scoring**: Entity-based risk scoring with cross-layer bonuses and time-based decay.
- **Automated Attack Simulator**: On-demand generation of named attack scenarios (including Stealth and Full Kill Chain).
- **Interactive Dashboard**: React-based UI with live event feeds, risk heatmaps, topology graph, and incident metrics.
- **ShopSphere Victim Web App**: A realistic e-commerce frontend for live SQL Injection and Brute Force demonstrations.
- **Quantitative Evaluation**: Built-in framework to measure Detection Rate, False Positive Rate, and MTTD.
- **Docker-First Design**: Entire stack deploys with a single command.

---

## 🛒 ShopSphere — Live Demo Web App

ShopSphere is a purpose-built "victim" e-commerce website that serves as the attack surface during live security demonstrations. It runs on **port 8080** and proxies requests to the backend API and Auth services through Nginx.

### Demo Flow

1. **Open ShopSphere**: Navigate to [http://localhost:8080](http://localhost:8080) — products load from the API server.
2. **SQL Injection Demo**: In the search bar, type `' OR '1'='1` and press Search. The query is forwarded to the vulnerable API, and the Security Dashboard ([http://localhost:3000](http://localhost:3000)) detects it in real-time.
3. **Brute Force Demo**: Click **Login** (or go to [http://localhost:8080/login.html](http://localhost:8080/login.html)). Enter username `admin` and try passwords like `pass1`, `pass2`, `pass3`, etc. The Dashboard detects the repeated failed login attempts.

### Architecture

```
Browser ──► :8080 (Nginx)
               ├── /           → Static HTML (index.html, login.html)
               ├── /api/*      → Reverse Proxy → api-server:5000
               └── /auth/*     → Reverse Proxy → auth-service:5001
```

### Files

| File | Purpose |
|------|--------|
| `targets/web-app/Dockerfile` | Nginx Alpine container for static serving + reverse proxy |
| `targets/web-app/nginx.conf` | Server block with proxy rules for `/api/` and `/auth/` |
| `targets/web-app/html/index.html` | E-commerce homepage with product grid and search bar |
| `targets/web-app/html/login.html` | Login page with brute force attempt counter and shake animation |
| `targets/web-app/html/static/agent.js` | **Browser-side telemetry agent (Phase 1)** — fetch/XHR/form/DOM hooks, regex SQLi/traversal/XSS detection, 2 s batched POST to browser-monitor |

---

## Browser Monitoring Layer (Phase 1–3)

SecuriSphere's fourth monitor layer captures attacks that never reach the server: payloads typed into the page, XHR requests issued from a hijacked browser tab, DOM injections from a stored XSS, and form submissions to login pages. The pipeline is:

```
ShopSphere page (browser)
    │  agent.js (fetch/XHR/form/DOM hooks; regex SQLi/traversal/XSS)
    │     │  batches every 2 s
    ▼     ▼
browser-monitor :5090  (Flask, CORS-enabled)
    │  validates schema, looks up site_id in registered_sites,
    │  enriches → publishes to security_events Redis channel
    ▼
correlation-engine :5070
    │  16 rules total — 7 of them are browser-layer-only
    ▼
backend :8000  →  dashboard :3000
```

### Register a site before ingesting events

The browser-monitor will reject events from any unknown `site_id`. Register the demo site once after `make start`:

```bash
make register-demo-site
# → returns { site_id, name, url, snippet }
```

The returned `snippet` is a `<script>` tag that you can paste into any HTML page you want to instrument:

```html
<script>window.__SECURISPHERE_SITE_ID__ = "abc12345";</script>
<script src="/static/agent.js" async></script>
```

### Files

| File | Purpose |
|---|---|
| `backend/targets/web-app/html/static/agent.js` | Browser-side collector (no dependencies, ~200 LOC, never crashes the host page) |
| `backend/monitors/browser/browser_monitor.py` | Flask :5090 — validates batches, looks up `site_id`, publishes to `security_events` |
| `backend/monitors/browser/register_site.py` | Flask Blueprint — `POST /api/register-site`, deterministic `site_id = sha256(url+name)[:8]` |
| `backend/monitors/browser/Dockerfile` | Container build (Python 3.10-slim, healthcheck on `/health`) |
| `scripts/init_db.sql` (excerpt) | `registered_sites` table + `pgcrypto` extension |

### Verifying the pipeline end-to-end

```bash
# 1. Service is up
curl -sf http://localhost:5090/health

# 2. Site is registered (returns site_id)
make register-demo-site

# 3. Send a synthetic SQLi event (replace SITE_ID with the value from step 2)
curl -X POST http://localhost:5090/api/ingest \
     -H "Content-Type: application/json" \
     -d '{"events":[{
           "event_type": "fetch_request",
           "source_layer": "browser-agent",
           "site_id": "SITE_ID",
           "target_entity": "/products",
           "target_url": "/products?id=1%27%20OR%20%271%27=%271",
           "severity": "HIGH",
           "correlation_tags": ["sql-injection"]
         }]}'
# → expect: { "published": 1, "skipped": 0 }

# 4. Confirm the correlation engine raised an incident
curl -s "http://localhost:8000/api/incidents?limit=5" | python -m json.tool
# → look for incident_type: "browser_sql_injection_attempt"
```

See [ATTACK_GUIDE.md](ATTACK_GUIDE.md) for the no-assumptions, copy-paste-friendly walkthrough of every attack scenario including the browser-layer ones.

---

## Correlation Rules

The engine currently implements **16 heuristic rules** (9 baseline + 7 browser-layer, added in Phase 2). All 16 run on every incoming event; browser-layer rules are early-guarded on `source_layer == 'browser-agent'` so they never fire on network/api/auth events and vice versa.

### Baseline rules (Phase 0 — network + API + auth layers)

1. **Reconnaissance followed by Exploitation**: Port scan (Network) followed by SQLi/XSS (API).
2. **Credential Compromise**: Brute force attempts followed by a successful login.
3. **Full Kill Chain**: Detects activity across all 3 layers (Net → Auth → API) targeting the same asset.
4. **Automated Attack Tooling**: High-frequency API errors combined with Auth failures.
5. **Distributed Credential Attack**: Multiple source IPs targeting the same user account.
6. **Data Exfiltration**: Successful exploit followed by accessing sensitive endpoints/bulk export.
7. **Persistent Threat / Stealth**:
   - *Standard*: High event volume (>10) in short window.
   - *Stealth Mode*: Detects isolated Critical events (e.g., single SQLi) that attempt to evade frequency filters.
8. **Service-Aware Lateral Movement**: Unusual inter-service requests along the topology graph.
9. **Privilege Escalation Chain**: Low-privileged account accessing high-privilege endpoints after a detected compromise.

### Browser-layer rules (Phase 2 — consume events from `agent.js` via browser-monitor)

Keyed by `site_id` (not by IP, since client IPs can NAT):

10. **Browser SQL Injection Attempt** — fires on any browser event tagged `sql-injection`/`sqli` → CRITICAL, MITRE T1190.
11. **Browser Path Traversal Attempt** — `../` / `%2e%2e` in `target_url` or `path-traversal` tag → HIGH, T1083.
12. **Browser Brute Force** — ≥5 `auth_failure` events from the same `site_id` in 60 s → HIGH, T1110.
13. **Browser Reconnaissance Scan** — ≥10 distinct `target_entity` values probed in 30 s → MEDIUM, T1046.
14. **Kill Chain A — BruteForce → Data Access** — Rule 12 fires, then a `data_access` event from the same `site_id` within 5 min → CRITICAL, stages `[initial_access, exfiltration]`.
15. **Kill Chain B — Recon → Privilege Escalation** — Rule 13 fires, then a `privilege_change` within 3 min → HIGH, stages `[reconnaissance, privilege_escalation]`.
16. **Kill Chain C — Multi-Hop Lateral Movement** — ≥3 distinct `target_entity` values hit in sequence within 2 min (deliberately noisy on high-traffic sites; tune `_browser_window` or cooldown if it raises FPs).

---

## Risk Scoring

Risk is tracked per Source Entity (IP Address).

- **Base Scores**:
  - Low Severity Event: +10
  - Medium Severity Event: +25
  - High Severity Event: +50
  - Critical Severity Event: +100

- **Multipliers**:
  - **Cross-Layer Bonus**: Events detected on multiple layers trigger a 1.5× multiplier.

- **Decay**:
  - Scores decay by 5 points every minute to allow "cooling off" of benign anomalies.

- **Thresholds**:
  - **Normal**: 0 – 30
  - **Suspicious**: 31 – 70
  - **Threatening**: 71 – 150
  - **Critical**: > 150 (Triggers immediate blocking recommendation)

---

## Running Attacks

> **For a step-by-step, no-assumptions walkthrough — including how to verify
> each detection on the dashboard — see [ATTACK_GUIDE.md](ATTACK_GUIDE.md).**

Quick reference:

```bash
make attack-killchain   # Full kill chain (legacy single-scenario)
make attack-fast        # All scenarios at maximum speed (for CI)
make attack-demo        # Full kill chain at demo speed (for presentations)
make attack-slow        # All scenarios slowly (for walkthrough)
```

Named scenarios (A / B / C) — used for evaluation and the research paper:

```bash
make attack-a           # Scenario A: Brute Force → Credential Compromise → Exfiltration
make attack-b           # Scenario B: Recon → SQL Injection → Privilege Escalation
make attack-c           # Scenario C: Multi-Hop Lateral Movement
make attack-abc         # All three in sequence
```

Browser-layer manual attacks (Phase 1–3):

```bash
# After `make start` and `make register-demo-site`, open ShopSphere and:
#   1. Type ' OR '1'='1 in the search bar  → triggers browser_sql_injection_attempt
#   2. Type ../../../etc/passwd in the URL → triggers browser_path_traversal_attempt
#   3. Submit /login.html with bad creds 5+ times in 60 s → triggers browser_brute_force
```

---

## Evaluation

```bash
make evaluate-full      # Run named scenarios + generate MTTD table
make mttd-markdown      # Export MTTD results as Markdown for paper
make mttd-report        # Export MTTD results as CSV
```

**Metrics collected:**
- **Detection Rate (DR)**: % of attack stages correctly identified
- **False Positive Rate (FPR)**: % of benign actions incorrectly flagged
- **Mean Time to Detect (MTTD)**: seconds from first attack event to kill chain alert
- **Alert Reduction Ratio**: raw events processed vs correlated incidents raised

---

## Dashboard

The React Dashboard provides:
- **Live Event Feed**: Real-time stream of raw security events.
- **Incident Timeline**: Correlated alerts with drill-down details and kill-chain reconstruction.
- **Risk Heatmap**: Visual representation of active threats by IP.
- **Topology Graph**: Live service dependency graph with attack replay.
- **System Health**: Status of all containers and Redis connectivity.
- **Stats Overview**: Total events, active incidents, and reduction metrics.

---

## API Reference

Key backend endpoints (served on `http://localhost:8000`):

| Endpoint | Description |
|---|---|
| `GET /api/health` | Liveness probe |
| `GET /api/metrics` | Aggregate raw-event and incident counts |
| `GET /api/events?limit=N` | Recent normalized events |
| `GET /api/incidents?limit=N` | Correlated incidents |
| `GET /api/risk-scores` | Current per-IP risk scores |
| `GET /api/kill-chains?limit=N&site_id=X` | **List** recent kill chains (Phase 3) |
| `GET /api/kill-chains/<id>` | Kill-chain reconstruction for a specific incident |
| `GET /api/mttd/report` | MTTD time-series report (for evaluation) |
| `GET /api/mitre-mapping` | MITRE ATT&CK technique frequency |
| `GET /api/demo-status` | Whether a demo is currently running (drives DemoBanner) |
| `GET /api/system/status` | Health of each SecuriSphere container |

**Topology Collector** — `http://localhost:5080`

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness probe |
| `GET /topology/services` | Flat list of running services |
| `GET /topology/graph` | Full node+edge graph (D3-ready) |
| `GET /topology/history?limit=N` | **Recent topology snapshots** from PostgreSQL (Phase 3) |
| `GET /topology/service/{name}` | Single-service lookup |
| `POST /topology/edge` | Register a runtime-observed edge |

**Browser Monitor** — `http://localhost:5090` (Phase 1–3)

| Endpoint | Description |
|---|---|
| `GET /health` | Liveness probe |
| `POST /api/register-site` | Register a site; returns `site_id` + embed snippet |
| `POST /api/ingest` | Accept a batch of browser events from `agent.js` |

---

## Configuration

Environment variables in `.env` control system behavior:

- `REDIS_HOST`, `REDIS_PORT`: Redis connection details.
- `POSTGRES_USER`, `POSTGRES_PASSWORD`: Database credentials.
- `CORRELATION_WINDOW`, `RISK_DECAY_RATE`, `RISK_DECAY_INTERVAL`: Correlation engine tuning.
- `GROQ_API_KEY`: Optional — enables AI-generated incident narration.
- `LOG_LEVEL`: Logging verbosity (INFO/DEBUG).
- `SPEED`: Default attack-simulator speed (`fast` / `normal` / `demo` / `slow`).

---

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions to common problems like:
- Redis connection failures
- Docker volume permission issues
- Port conflicts
- WebSocket disconnection

Quick checks:
```bash
make health-full        # Verify all services are responding
make logs               # Stream logs from all containers
make ps                 # List running container status
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on code style, testing, and pull requests.

---

## License

MIT License. See [LICENSE](LICENSE) file for details.
