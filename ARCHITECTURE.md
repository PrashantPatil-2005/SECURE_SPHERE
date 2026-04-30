# SecuriSphere — System Architecture

End-to-end design reference for the SecuriSphere multi-layer cyber-monitoring platform. Covers methodology, runtime topology, data flow, detection logic, storage, real-time pipeline, and the engineering principles behind the codebase.

For frontend visual rules see `frontend/DESIGN_SYSTEM.md`. For repo-wide AI-assistant rules see `CLAUDE.md`. This file is the **system-level companion** — *what runs where, what calls what, and why*.

---

## 1. What SecuriSphere is

SecuriSphere is a **multi-layer security monitoring + correlation platform** wrapped in a real-time SOC dashboard. It ingests telemetry from four observation layers (network, API, auth, browser), normalises events into a uniform schema, runs a correlation engine that fires both heuristic Python rules and YAML-defined rules, scores risk per host/service with time decay, reconstructs kill chains, maps activity to MITRE ATT&CK techniques, and surfaces everything live to analysts via Socket.IO.

It is built as a **containerised microservice mesh** (Docker Compose) where each layer is independently runnable. Redis is the event bus + hot store; PostgreSQL is the system of record for incidents and kill chains. The backend Flask API at `:8000` is the only public surface; the dashboard at `:3000` (or nginx in prod) consumes it.

---

## 2. High-level topology

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                         OBSERVATION  PLANE                                    │
│                                                                               │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐    │
│  │ network-     │   │ api-monitor  │   │ auth-monitor │   │ browser-     │    │
│  │ monitor      │   │ (HTTP /      │   │ (login /     │   │ monitor      │    │
│  │ (scapy:eth0) │   │ payload      │   │ token /      │   │ (telemetry / │    │
│  │  port-scan,  │   │ inspection)  │   │ MFA / brute) │   │ JS-RUM,      │    │
│  │  syn flood,  │   │              │   │              │   │ XSS/SQLi/    │    │
│  │  DNS tunnel) │   │              │   │              │   │ traversal)   │    │
│  └──────┬───────┘   └──────┬───────┘   └──────┬───────┘   └──────┬───────┘    │
│         │                  │                  │                  │             │
│         └──────────────────┴───────┬──────────┴──────────────────┘             │
│                                    │                                           │
│                          publishes normalised events                           │
│                                    ▼                                           │
│                  ┌─────────────────────────────────┐                           │
│                  │  Redis  (pub/sub + Streams)     │                           │
│                  │  channel:    security_events    │                           │
│                  │  stream:     events:stream      │                           │
│                  │  lists:      events:network /api/auth │                     │
│                  │  lists:      incidents          │                           │
│                  │  hashes:     risk_scores_current│                           │
│                  └────────────────┬────────────────┘                           │
└─────────────────────────────────────┼─────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         DETECTION  PLANE                                      │
│                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────┐   │
│  │ correlation-engine (:5070)                                             │   │
│  │   1. enrich_event   → topology lookup (cached 30 s)                    │   │
│  │   2. threat-intel   → IP feed match                                    │   │
│  │   3. behaviour      → fingerprinter (anomaly events recurse)           │   │
│  │   4. rolling buffer (CORRELATION_WINDOW = 900 s, deque)                │   │
│  │   5. risk score     → per-IP / per-service, time-decayed               │   │
│  │   6. heuristic rules (12 Python + N YAML)                              │   │
│  │   7. kill-chain reconstructor (service_path, MTTD, steps)              │   │
│  │   8. confidence (Bayesian) + counterfactual explainer                  │   │
│  │   9. predictor (next-step heuristic, MITRE-aware)                      │   │
│  │  10. publish incident → Redis list + pub/sub + Postgres                │   │
│  │  11. AI narrator (HuggingFace) — fire-and-forget commentary            │   │
│  │  12. replay recorder (writes incident frames for /replay)              │   │
│  └────────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                         PRESENTATION  PLANE                                   │
│                                                                               │
│   ┌──────────────────────────────────┐    ┌──────────────────────────────┐    │
│   │  backend Flask API (:8000)       │    │  topology-collector (:5080)  │    │
│   │  /api/events  /api/incidents     │◄───│  Docker socket → service map │    │
│   │  /api/risk-scores /api/topology  │    │  pushes graph to backend     │    │
│   │  /api/kill-chains  /api/mitre-…  │    └──────────────────────────────┘    │
│   │  /api/auth/* (JWT)               │                                        │
│   │  /api/engine/* (proxy → :5070)   │                                        │
│   │  Socket.IO (realtime fan-out)    │                                        │
│   └──────────────────┬───────────────┘                                        │
│                      │                                                        │
│                      ▼                                                        │
│             ┌────────────────┐                                                │
│             │  React/Vite UI │  (login → dashboard, events, incidents,       │
│             │  (:3000 / nginx│   topology, risk, MITRE, replay, system)      │
│             │  dist)         │                                                │
│             └────────────────┘                                                │
└───────────────────────────────────────────────────────────────────────────────┘
                                      ▲
                                      │ alerts (REST + Socket.IO)
┌───────────────────────────────────────────────────────────────────────────────┐
│                         CONTROL  /  RED-TEAM  PLANE                           │
│                                                                               │
│  ┌──────────────────┐  ┌──────────────────┐   ┌──────────────────────────┐    │
│  │ attack-simulator │  │ waf-proxy (:8088)│   │ targets (api-server :5000│    │
│  │ (scenarios)      │  │ + proxy-monitor  │   │  auth-service :5001,     │    │
│  │ — recon, brute,  │  │ — opt-in WAF     │   │  web-app :8080)          │    │
│  │ exfil, multi-hop │  │  upstream         │   │                          │    │
│  └──────────────────┘  └──────────────────┘   └──────────────────────────┘    │
└───────────────────────────────────────────────────────────────────────────────┘
```

Every box is a Docker service in `docker-compose.yml`. Network = `securisphere-network` (172.18.0.0/16).

---

## 3. Service inventory

| Service | Port | Role |
|---|---|---|
| `redis` | 6379 (internal) | Event bus (pub/sub + Streams), hot lists, risk hash, rate-limit storage |
| `database` (postgres) | 5432 (internal) | Persistent store: users, incidents, kill_chains, audit |
| `api-server` | 5000 | Mock target — protected API surface |
| `auth-service` | 5001 | Mock target — login/token issuer |
| `web-app` | 8080 | Mock target — vulnerable webapp for browser-layer demos |
| `network-monitor` | — | scapy sniffer in `network_mode: service:api-server`, NET_RAW |
| `api-monitor` | 5050 | Inspects target API traffic, emits API events |
| `auth-monitor` | 5060 | Watches auth-service logs/events |
| `browser-monitor` | 5090 | Browser RUM agent endpoint |
| `proxy-monitor` | — | Mirrors WAF activity into Redis |
| `topology-collector` | 5080 | Reads Docker socket, builds live service graph |
| `correlation-engine` | 5070 | Detection brain (see §5) |
| `backend` (Flask API) | 8000 | Public REST + Socket.IO; only externally addressable backend |
| `dashboard` (Vite/Nginx) | 3000 | React SPA |
| `waf-proxy` | 8088 / 8443 | Optional WAF in front of `web-app` |
| `attack-simulator` | — | Profile-gated red-team scenarios |

Outside Compose: `attacker/`, `cli/`, `evaluation/`, `experiment/`, `paper/`, `benchmarks/` are research/dev artefacts, not runtime.

---

## 4. Data model

### 4.1 Normalised event schema

Every monitor emits the same envelope onto Redis (`security_events` channel + `events:stream` Redis Stream):

```json
{
  "event_id": "uuid",
  "timestamp": "2026-04-30T10:15:32.812Z",
  "source_layer": "network|api|auth|browser|behavior-fingerprint",
  "source_service_name": "api-server",
  "source_entity":  { "ip": "10.0.0.42", "user": "alice", "asn": 64500 },
  "event_type":     "port_scan|brute_force|sqli|xss|exfil|...",
  "severity":       "low|medium|high|critical",
  "details":        { "ports": [22,80,443], "method": "GET", "path": "/admin" },
  "topology_info":  { /* added by enrich_event */ },
  "enrichment_source": "live|cached|none",
  "threat_intel_match": false
}
```

### 4.2 Incident schema (engine output)

```json
{
  "incident_id":   "uuid",
  "incident_type": "recon_to_exploit|credential_compromise|full_kill_chain|...",
  "severity":      "critical|high|medium|low",
  "service_path":  ["browser","auth-service","api-server"],
  "first_event_at":"...",  "detected_at":"...",  "mttd_seconds": 14.2,
  "kill_chain_steps": [ { "tactic": "Initial Access", "technique": "T1190", ... } ],
  "mitre_techniques": ["T1110","T1071","T1530"],
  "confidence":    { "prior": 0.6, "likelihood": 0.84, "posterior": 0.91 },
  "explanation":   { "counterfactuals": [...], "diff": [...] },
  "narrative":     "AI-generated prose (optional, async)",
  "events":        [/* events that fired the rule */]
}
```

### 4.3 Storage layout

**Redis (hot path, capped):**
- `events:network`, `events:api`, `events:auth`, `events:browser` — capped lists per layer (LPUSH + LTRIM).
- `incidents` — capped list of recent incidents (LPUSH).
- `risk_scores_current` — hash, key=`service|ip`, value=JSON `{ score, level, last_event, history[] }`.
- `mitre_mapping_current` — technique frequency snapshot.
- channel `security_events` — pub/sub fan-out.
- stream `events:stream` — durable replay (Redis Streams, Phase 13).

**PostgreSQL (cold path, source of truth):**
- `users` — username, email, password_hash, role, failed_attempts, locked_until, last_login_at.
- `incidents` — full incident row, indexed by `incident_id`, `severity`, `detected_at`.
- `kill_chains` — reconstructor output: steps, service_path, MTTD, narrative.
- (init script: `scripts/init_db.sql`).

---

## 5. Detection methodology

### 5.1 The pipeline (per event)

`backend/engine/correlation/correlation_engine.py:process_event`

```
event ──▶ enrich_event (topology cache, 30 s TTL)
      ──▶ threat-intel lookup (bumps low/medium → high on hit)
      ──▶ behaviour fingerprinter (emits anomaly events into stream)
      ──▶ buffer.append + prune (CORRELATION_WINDOW = 900 s)
      ──▶ update_risk_score (per service|ip, decayed)
      ──▶ for rule in self.rules: rule(event, buffer)  ← 12 Python rules
      ──▶ yaml_rules.evaluate(event, buffer)            ← N declarative rules
      ──▶ on hit: publish_incident
            ├─ kill_chain.reconstruct → service_path, MTTD, steps
            ├─ confidence.score_chain (Bayesian)
            ├─ explain.counterfactual + diff
            ├─ Redis LPUSH incidents + PUBLISH
            ├─ Postgres INSERT incidents/kill_chains
            ├─ replay.recorder.write
            ├─ Discord webhook (rate-limited 60 s/type, 3 retries)
            └─ AI narrator (poll, 8 s timeout, async best-effort)
```

### 5.2 Heuristic rules (Python)

Located at `backend/engine/correlation/correlation_engine.py:rule_*`.

| Rule | What triggers it |
|---|---|
| `recon_to_exploit` | port-scan event followed by exploit attempt from same IP within window |
| `credential_compromise` | brute-force success → privileged endpoint access |
| `full_kill_chain` | ≥3 distinct tactics observed across the kill chain |
| `api_auth_combined` | auth-layer brute + api-layer probe correlated |
| `distributed_attack` | many source IPs hitting the same target inside window |
| `data_exfiltration` | high-volume outbound + DNS tunnel pattern |
| `persistent_threat` | repeated low-and-slow activity across decay cycles |
| `brute_force_attempt` | login failures > threshold from one IP |
| `critical_exploit_attempt` | known-bad payload signature |
| `browser_sqli` / `browser_path_traversal` / `browser_brute_force` / `browser_recon_scan` | browser-layer detections |
| `browser_bruteforce_to_exfil` / `browser_recon_to_privesc` / `browser_multi_hop` | composite browser kill chains |

Cooldown gates each rule per key (`_check_cooldown` / `_set_cooldown`) so duplicates don't spam the dashboard.

### 5.3 YAML rule DSL

`backend/engine/rules/dsl.py` (loader) lets ops add detections without editing Python. Same incident shape, same `publish_incident` path. Fields supported include `match`, `threat_intel_match`, `count_within`, `service_path`, `mitre_techniques`. Rules hot-reload on engine boot.

### 5.4 Risk scoring

`update_risk_score` keyed by service name (preferred) or source IP. Adds rule-defined points; `decay_risk_scores_loop` shaves `RISK_DECAY_RATE` (default 5) every `RISK_DECAY_INTERVAL` (60 s). Threat level is derived from score:

```
score < 25  → normal
score < 50  → suspicious
score < 75  → threatening
score ≥ 75  → critical
```

Stored under `risk_scores_current` Redis hash; pushed live via Socket.IO so the dashboard threat ring updates without polling.

### 5.5 Kill-chain reconstruction

`backend/engine/kill_chain/reconstructor.py` walks the buffer for events that share the incident's source/service, orders them by timestamp, and emits a list of MITRE-tagged steps. Computes `mttd_seconds = detected_at − first_event_at`. Persisted to Postgres for the `/replay` view.

### 5.6 Bayesian confidence + counterfactuals

`backend/engine/confidence/bayesian.py` — `score_chain()` returns prior/likelihood/posterior given step composition + historical base rate. `backend/engine/explain/counterfactual.py` produces "if step X had not occurred, would this still classify as the same incident?" deltas. Both ride along in the incident payload — the dashboard incident detail panel renders them.

### 5.7 Behaviour fingerprinter

`backend/engine/anomaly/fingerprinter.py:BehaviorTracker` runs *before* rules and re-emits anomaly events back through the same pipeline tagged `source_layer="behavior-fingerprint"`. The skip in `process_event` prevents feedback loops. Lets the system treat "unusual behaviour" as just another event type for rule consumption.

### 5.8 MITRE ATT&CK mapping

Static map at `backend/engine/mitre/mitre_map.py`. Every rule + YAML rule attaches `mitre_techniques`. The engine maintains a frequency map (`mitre_mapping_current`) exposed by the backend `/api/mitre-mapping`. Frontend `pages/Mitre.jsx` renders the heatmap.

### 5.9 Predictor

`backend/engine/predictor/heuristic.py:HeuristicPredictor` looks at the current kill chain prefix and suggests the next likely tactic/technique. Surfaced via `/api/engine/predict-next`.

### 5.10 Replay

`backend/engine/replay/recorder.py` writes per-incident frame files; `replay/player.py` streams them back. Powers `/api/engine/replays/*` and the UI Replay page (frame-by-frame attack walkthrough).

---

## 6. Real-time pipeline

### 6.1 Backend ↔ Redis ↔ Engine

The backend Flask app (`backend/api/app.py`) doesn't run rules itself — it **subscribes** to Redis and forwards everything to Socket.IO clients.

- Events: read via `LRANGE events:<layer>` for HTTP fetch; pushed live via Socket.IO when the engine PUBLISHes on `security_events`.
- Incidents: same pattern, PUBLISH'd when `correlation-engine.publish_incident` fires.
- Risk scores: `_publish_risk` → Socket.IO room.
- Topology: pulled from `topology-collector:5080` via `enrich_event` and `/api/topology`.

### 6.2 Frontend realtime hook

`frontend/src/hooks/use-realtime.js` opens a Socket.IO client on first render of `<AuthenticatedApp>`, subscribes to `event`, `incident`, `risk_update`, `topology_update`, and merges into local state. HTTP polling acts as a fallback when socket transport fails — `lib/api.js` retries on `fetch` errors and `lib/mock-data.js` provides demo data when the backend is offline.

### 6.3 Backpressure + caps

- Redis lists are capped via `LTRIM` on write so dashboards never flood.
- Socket.IO emits are coalesced — `publish_summary_loop` runs once per few seconds with rolling aggregate counts.
- Discord alerts use a 60 s/incident-type rate limit + 3-retry backoff.
- AI narrator is fire-and-forget; the incident is published before the LLM call returns, narrative is patched in async.

---

## 7. Auth + RBAC

**File: `backend/api/auth.py`** — Flask blueprint mounted at `/api/auth`.

- `POST /login` → JWT (HS256, env `JWT_SECRET`, ≥16 chars in prod). Lockout after 5 failed attempts (15 min). Constant-time-ish dummy hash check on missing user to prevent enumeration.
- `POST /register` → username/email/password (3-32 chars / valid email / 8+ chars w/ letter & digit). Default role `user`. Gated by `ALLOW_PUBLIC_REGISTRATION`.
- `POST /logout` → adds bearer token to in-memory blocklist (10 k cap).
- `POST /forgot` → no-op stub returning generic 200 (no enumeration).
- `GET /me`, `POST /verify` → token introspection.
- Decorators `@token_required`, `@role_required(*roles)` gate every other backend route that mutates state.
- Passwords hashed with Werkzeug pbkdf2/scrypt. Plaintext is **never** seeded; `ALLOW_PLAINTEXT_LOGIN` exists only as a dev-only legacy migration path and is rejected in prod.
- Bootstrap admin from `ADMIN_BOOTSTRAP_USER` / `ADMIN_BOOTSTRAP_PASSWORD` env vars at table creation.

JWT lifecycle:

```
Login  → backend issues token  → frontend stores in localStorage (remember) or sessionStorage
Every API call → authFetch injects Authorization: Bearer <token>
Logout → backend blocklists token, frontend clears storage, redirects /login
Expiry → 401, frontend redirects /login
```

---

## 8. Frontend architecture

```
frontend/src/
├── main.jsx                ReactDOM root → <App/>
├── App.jsx                 BrowserRouter
│                            ├─ /attacker → standalone red-team view
│                            └─ * → <Shell/>
│                                   ├─ unauth + /signup → <Signup/>
│                                   ├─ unauth + /login  → <Login/>
│                                   └─ authed → <AuthenticatedApp/>
├── pages/                  Login, Signup, Intro, Dashboard, Events, Incidents,
│                           Topology, RiskScores, Mitre, Replay, System, Attacker
├── components/
│   ├── ui/                 Button, Card, Badge, Input, StatCard, Spinner    (primitives)
│   ├── layout/             DashboardLayout, Header, StatusBar               (chrome)
│   ├── nav/                navConfig, SidebarNav, TopNav, AppNavTabs, CommandPalette
│   ├── shell/              AuthenticatedApp, TweaksPanel
│   ├── notifications/      IncidentToaster                                  (toasts)
│   ├── charts/             Recharts wrappers (EventsAreaChart, ThreatDonutChart, …)
│   ├── dashboard/          KPI cards, mode switcher, TriageDashboard, GridDashboard, StoryDashboard
│   ├── events/ incidents/  feature blocks per page
│   ├── topology/ topology3d/ replay/ intro/ design/ cinema/ ai/
│   └── KillChainTimeline.jsx, TopologyGraph.jsx, ...
├── contexts/CommandPaletteBridge.jsx   wires ⌘K palette to router
├── stores/useAppStore.js    zustand persisted: theme, density, ann, kc, nav, tweaksOpen
├── hooks/                   use-realtime, use-theme, useCommandPalette, useLocalStorage
└── lib/                     api.js, websocket.js, mock-data.js, themeDom.js, utils.js
```

### 8.1 State separation

- **UI prefs** (theme, density, nav shell, kill-chain view) → `useAppStore` (zustand + persist, key `securisphere-app-store`).
- **Live data** (events, incidents, metrics, timeline, topology) → `useRealtime()`. Pages receive props from `<AuthenticatedApp>`. Pages never call `api.*` directly (Login/Signup/Attacker exempt).
- **Routing-aware actions** (open palette, jump to incident, run scenario) → `CommandPaletteBridge` over `NAV_ITEMS`.

### 8.2 Nav shells

Three interchangeable chromes: `sidebar` (default), `top`, `minimal` — selected via `useAppStore().nav`. Picked at runtime in `AuthenticatedApp`. New chrome layouts plug in here, not into individual pages.

### 8.3 Authoritative nav config

`components/nav/navConfig.js` defines `NAV_ITEMS` (`id`, `label`, `path`, `section`, `icon`). Adding a route = one entry here + one `<Route>` in `AuthenticatedApp`. Helpers `pathForTab(id)` / `tabIdFromPath(pathname)` keep label/path lookup centralised.

---

## 9. Configuration surface

### 9.1 Backend env vars (boot-time validated)

| Var | Default | Note |
|---|---|---|
| `FLASK_ENV` | `production` | Strict prod checks at boot |
| `JWT_SECRET` | — | Required ≥16 chars in prod |
| `JWT_EXPIRATION_HOURS` | `1` | |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` or `DATABASE_URL` | — | DB connection |
| `REDIS_HOST/PORT` | `redis:6379` | Bus + cache |
| `CORS_ORIGINS` | `*` (dev only) | `*` forbidden in prod |
| `RATE_LIMIT_DEFAULT` | `200/minute` | Moving-window via flask-limiter |
| `RATE_LIMIT_LOGIN` | `10/minute` | Login-specific |
| `ALLOW_LOCALHOST_UPSTREAM` | `0` | SSRF guard; demo-only |
| `ALLOW_PUBLIC_REGISTRATION` | `1` | |
| `ALLOW_PLAINTEXT_LOGIN` | `0` | Legacy migration only |
| `ADMIN_BOOTSTRAP_USER/PASSWORD/EMAIL` | — | Seed first admin |
| `CORRELATION_WINDOW` | `900` | Buffer window seconds |
| `RISK_DECAY_RATE/INTERVAL` | `5/60` | Decay tuning |
| `EVENT_BUS_MODE` | `dual` | `pubsub` / `streams` / `dual` |
| `HF_API_TOKEN` / `HF_MODEL` | — / `Qwen/Qwen2.5-72B-Instruct` | AI narrator |
| `DISCORD_WEBHOOK_URL` | — | Alert sink |

### 9.2 Frontend env vars

- `VITE_API_URL` — base URL for backend (proxy-relative when empty).
- Token storage keys: `securisphere_token` (local OR session storage based on "remember me").

---

## 10. Engineering principles / methodology

### 10.1 Microservice-per-concern, single bus

Every observation layer is its own container with its own dependencies. They share **one** integration contract: the normalised event envelope on Redis. New layers plug in by writing to the same channel — no engine changes needed for ingestion.

### 10.2 Detection as data

Heuristic rules are first-class Python — the YAML DSL is the second-class equivalent for ops. Both produce the same `Incident` shape, both flow through `publish_incident`. Adding a detection never requires touching downstream consumers.

### 10.3 Hot store + cold store split

Redis holds **what's happening now** (capped lists, decayed scores, current MITRE map). Postgres holds **what happened** (incidents, kill chains, users). The dashboard reads hot for live views and cold for forensics. Caps prevent memory blow-up; LRU policy is set on Redis at startup.

### 10.4 Enrichment is best-effort

Topology, threat-intel, and AI narration enrich the event but never block it. Live → cached → none degradation. Caches have a TTL after which the engine logs and proceeds without enrichment. The system stays detecting even when ancillaries fail.

### 10.5 Defence in depth at the API edge

Backend boot fails closed on missing prod env. CORS is allowlisted. Rate limits are enforced per-route. Login lockout protects credential endpoints. SSRF guard is on by default for upstream calls. JWT secrets are validated for length. Plaintext login is opt-in and prod-banned.

### 10.6 Realtime first, polling as fallback

UI starts on Socket.IO. If transport fails it falls back to HTTP polling. If backend is down it falls back to `lib/mock-data.js` so the UI is always demoable. No spinner-of-doom states.

### 10.7 Time correctness

Backend currently emits naive ISO timestamps via `datetime.utcnow().isoformat()`. Frontend `parseServerTime()` in `lib/utils.js` compensates by appending `Z`. New endpoints should emit timezone-aware ISO. **Never** call `new Date(iso)` directly in the frontend — always use the `formatTimestamp` / `relativeTime` helpers.

### 10.8 Composition over inheritance

Frontend has no class components and no HOCs. Composition is via hooks (`useRealtime`, `useAppStore`) and primitives (`Card`, `Badge`, `Button` with `cva` variants). New behaviour adds a hook or extends a `cva` variant — never wraps.

### 10.9 No premature optimisation, no premature genericisation

The codebase prefers concrete duplication over speculative abstractions. Three similar rule functions are fine; a generic rule registry is not introduced until five exist. Same in the frontend — `Triage/Grid/Story` dashboards are three siblings, not an over-engineered driver.

### 10.10 Demoability is a feature

The project ships an `attack-simulator` profile, mock targets (`api-server`, `auth-service`, `web-app`), an `Attacker.jsx` standalone red-team view, and a `Replay` engine. Anyone with Docker can fire `docker compose --profile attack up` and watch a kill chain assemble live. The architecture explicitly supports being its own demo.

---

## 11. Request lifecycles (worked examples)

### 11.1 A port scan from outside the cluster

```
attacker  ──TCP SYN→  api-server (host port 5000)
network-monitor (sniffing eth0 inside api-server's net ns)
   detects 12 ports / 5 s from one IP
   ──XADD events:stream {layer:network, type:port_scan, severity:high}
correlation-engine (consumer)
   enrich_event → topology says "api-server is a public-facing service"
   buffer.append; update_risk_score("api-server", +20)
   rule_recon_to_exploit fires?  Not yet (no follow-up). Cooldown set.
backend Flask
   PUBLISH security_events forwarded → Socket.IO clients
dashboard
   Header bell badge +1; Events page row flashes;
   Topology graph node "api-server" turns suspicious.
```

### 11.2 A correlated kill chain

```
event 1: brute_force on auth-service        +30 to 10.0.0.42
event 2: token reuse on api-server          +25
event 3: data exfiltration to external IP   +20
correlation-engine
   rule_full_kill_chain matches (≥3 distinct tactics, single source IP)
   reconstructor.reconstruct → service_path = [auth-service, api-server, external]
                              MTTD = 28 s
                              steps = [Initial Access T1110, Credential Access T1078, Exfiltration T1048]
   confidence.score_chain → posterior 0.91
   explain.counterfactual → "removing brute_force drops posterior to 0.43"
   publish_incident
      LPUSH incidents
      INSERT incidents, kill_chains in Postgres
      replay.recorder.write
      Discord alert
      AI narrator (async)
backend
   Socket.IO emit incident
dashboard
   IncidentToaster pops ("CRITICAL · full_kill_chain — auth-service → api-server → ext")
   Incidents page prepends row
   Replay page now offers this incident_id for frame replay
```

### 11.3 A user logging in

```
browser → POST /api/auth/login {username,password}
backend.auth.login
   _ensure_auth_schema (idempotent)
   _fetch_user_by_username
   lockout check (locked_until?)
   check_password_hash
   _record_login_success → updates last_login_at, resets failed_attempts
   _generate_token (JWT HS256, exp = now + JWT_EXPIRATION_HOURS)
   200 { token, user }
frontend Login.jsx
   stores token in localStorage (remember) or sessionStorage
   onLogin(data) → Shell.setAuthed(true) → mounts AuthenticatedApp
useRealtime
   opens Socket.IO with Authorization header
   primes events/incidents/risk via REST
```

---

## 12. Where to extend

| Want to… | Touch this |
|---|---|
| Add a new detection layer (e.g. mobile telemetry) | `backend/monitors/<new>/` — emit normalised events to `security_events` |
| Add a Python rule | `correlation_engine.py:rule_*` + register in `self.rules` |
| Add a YAML rule | `backend/engine/rules/yaml/*.yaml` (loaded at engine boot) |
| Add a backend route | Flask blueprint under `backend/api/` + register in `app.py` |
| Add a top-level UI page | `frontend/src/pages/<Page>.jsx` + entry in `nav/navConfig.js` + `<Route>` in `AuthenticatedApp` |
| Add a UI primitive | `frontend/src/components/ui/` — extend `cva` variants, don't fork |
| Add a chart | `frontend/src/components/charts/` — copy the Recharts tooltip pattern |
| Add a MITRE technique mapping | `backend/engine/mitre/mitre_map.py` |
| Add a notification channel | After `publish_incident`, mirror the Discord pattern (rate-limited + retried) |
| Add an attack scenario | `backend/simulation/scenarios/` + register in `attack_orchestrator.py` |

---

## 13. Operational notes

- `docker compose up -d` brings the whole mesh up (minus `attack-simulator` which is profile-gated).
- `docker compose --profile attack up attack-simulator` fires the red-team scenarios.
- Dev: `docker-compose.dev.yml` exposes debug ports + Vite HMR. Prod: `docker-compose.prod.yml` runs nginx in front of the dashboard build.
- `Makefile` wraps the common flows. `run.bat` is the Windows convenience entry point.
- Postgres init runs `scripts/init_db.sql` at first boot.
- All services emit JSON logs (Docker `json-file` driver, 10 MB × 3 rotation).
- Health checks gate `depends_on` ordering so the backend doesn't boot before its dependencies.

---

## 14. Glossary

- **MTTD** — Mean Time To Detect: `detected_at − first_event_at` per kill chain.
- **Kill chain** — ordered sequence of tactics/techniques observed from a single attacker.
- **Event** — atomic observation from a monitor.
- **Incident** — correlated set of events that triggered a rule.
- **Risk score** — decayed numeric pressure attached to an entity (service or IP).
- **Threat level** — categorical projection of a risk score.
- **Topology enrichment** — augmenting an event with the live service graph.
- **Confidence posterior** — Bayesian-scored credibility of an incident classification.
- **Replay** — frame-by-frame attack reconstruction available for any incident with a kill chain.
