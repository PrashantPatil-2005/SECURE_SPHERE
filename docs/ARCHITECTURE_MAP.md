# SecuriSphere — Architecture Map (Dimension 1)

> Status snapshot generated during the 360° transformation pass.
> Captures every service, data flow, and gap between **claimed** and **actual** behaviour.

---

## 1. Compose Surface (14 services, 1 attack profile)

| Service | Tech | Port | Role |
|---|---|---|---|
| redis | redis:7.2-alpine | 6379 (expose) | Event bus + risk-score cache + Streams (new) |
| database | postgres:15-alpine | 5432 (expose) | Persistent store: kill_chains, correlated_incidents, topology_snapshots, registered_sites, users |
| api-server | Flask | 5000 | Vulnerable target API |
| auth-service | Flask | 5001 | Vulnerable auth endpoint |
| network-monitor | scapy + tshark sidecar | shares api-server netns | L3/L4 capture |
| api-monitor | Flask | 5050 | SQLi/XSS/path-traversal/rate-abuse detection |
| auth-monitor | Flask | 5060 | Brute force, stuffing, suspicious login |
| browser-monitor | Flask | 5090 | Browser-agent ingest + site registration (Phase 1–3) |
| backend | Flask + flask-socketio (gevent) | 8000 | Public REST + WebSocket aggregator |
| dashboard | React 18 + Vite + Tailwind + d3 + framer-motion | 3000 | SOC UI |
| correlation-engine | Flask + Redis pub/sub | 5070 | Rule engine + risk scoring + kill chain |
| topology-collector | **FastAPI** + docker SDK | 5080 | Live service graph |
| web-app | nginx | 8080 | ShopSphere demo target |
| waf-proxy | OpenResty + Lua | 8088 / 8443 | Optional WAF in front of web-app |
| proxy-monitor | Python | — | Tail WAF logs |
| attack-simulator | Python | — | Kill-chain scenarios A/B/C (profile only) |

> Backend is **Flask**, not FastAPI as the prompt claimed. Only `topology-collector` is FastAPI.

## 2. Data Flow (current)

```
target services → monitors (regex/heuristic) → redis PUBLISH security_events
                                              ↓
                                   correlation-engine pubsub.listen()
                                              ↓
                                   in-memory event_buffer (15 min)
                                              ↓
                                   9 + 7 rules (single-thread)
                                              ↓
                                   create_incident → reconstruct kill chain
                                              ↓
                  redis lpush incidents / ws_push_queue       postgres kill_chains
                                              ↓                          ↓
                              backend Flask /api/*       backend → react dashboard
```

### Channels / Keys
- `security_events` (pub/sub) — every monitor publishes here
- `auth_events`, `api_logs` — raw logs to specific monitors
- `correlated_incidents`, `risk_scores`, `correlation_summary` — engine outputs
- `topology_updates` — snapshot diffs from collector
- Redis lists: `events:network`, `events:api`, `events:auth`, `incidents`, `ws_push_queue`
- Redis hashes: `risk_scores_current`, `incident_status:{id}`
- Redis kv: `latest_summary`, `topology:latest`, `config:discord_webhook`

## 3. Gap Analysis: Claimed vs. Actual

### Claimed in prompt — Actual reality

| Prompt claim | Reality | Action |
|---|---|---|
| "Polling every 5s" | Engine is pub/sub; no polling. Single-threaded though — bottleneck under load. | Migrate to Redis Streams + consumer groups for replay/parallelism. |
| "Topology collector incomplete (Phase 12)" | Mostly complete: docker.from_env, snapshot persist, REST graph/services/service/{name}/history, Redis publish. **Bugs:** duplicated nested-ternary in `_pg_conn` (also in reconstructor), no traffic-observed edge inference loop, no graph-embedding drift signal. | Fix bugs, add observed-edge inference + topology drift detector. |
| "FastAPI backend" | Backend is Flask; only topology-collector is FastAPI. | Document; keep Flask (consumed by tests + frontend). |
| "MTTD experiment data incomplete" | `evaluation/results/` has 9 trials from 2026-02-15. No automated baseline-vs-securisphere bench. | Add `/benchmarks` with reproducible MTTD diff. |
| "No ML/AI layer" | True. Only HF narrator (post-hoc text). | Add Isolation Forest behavioural fingerprint + TGNN scaffold + Bayesian confidence. |
| "No predictive lateral movement" | True. | Scaffold TGNN next-pivot predictor. |
| "UI functional but not wow" | 30+ React components, framer-motion, d3 force-graph. Lacks 3D, no replay scrubber, no MITRE heatmap live, no cinema mode. | Add r3f 3D graph, cinema mode, replay scrubber, live MITRE heatmap. |

### Concrete bugs & TODOs found

1. **`backend/engine/kill_chain/reconstructor.py:45-51`** — `_get_conn` has nested-ternary noise: `psycopg2.connect(os.getenv("DATABASE_URL")) if ... else psycopg2.connect(...) if ... else psycopg2.connect(...)`. Same pattern repeats in `topology_collector._pg_conn` and `app._avg_mttd_from_postgres`. Refactor to a shared helper.
2. **Engine pub/sub loses messages** if subscriber drops. No consumer-group durability, no replay, no fan-out.
3. **No structured event correlation IDs** spanning monitor → engine → incident — only `event_id` (uuid4) per event; can't trace one request through.
4. **Topology static edges are hardcoded** in collector — no observed edges from real traffic. The `/topology/edge` POST exists but nothing calls it.
5. **No OpenTelemetry** — only print/log statements.
6. **No tests for kill-chain detection time** — `tests/test_phase*.py` exists but nothing asserts MTTD < N.
7. **MITRE coverage is static dict** — there is no live "what % of MITRE for Containers do we cover today" page.
8. **Browser rules duplicate keys with global `site_id`** but `site_id` enrichment and per-site cooldown collide if attacker spoofs.
9. **Discord narrative poll blocks 8s** — moved to thread already (good), but the polling pattern wastes a DB connection per second.

### What's actually solid (do not break)

- `engine/correlation/correlation_engine.py` rule pattern — keep API.
- `engine/kill_chain/reconstructor.py` reconstruction algorithm.
- `engine/mitre/mitre_map.py` static taxonomy.
- monitor → redis publish contract (event schema in `init_db.sql:3-27`).
- Frontend Zustand store + use-realtime hook.
- React Router + AuthenticatedApp shell.

## 4. Module Inventory

```
backend/
├── api/                    Flask backend public API (1806 LOC monolith)
├── engine/
│   ├── correlation/        Rule engine (1432 LOC, single file)
│   ├── kill_chain/         Postgres-backed reconstructor
│   ├── mitre/              Static MITRE for Containers map
│   ├── narration/          HF Inference (optional)
│   ├── anomaly/            **NEW** Isolation Forest fingerprinting
│   ├── predictor/          **NEW** TGNN next-pivot scaffold
│   ├── replay/             **NEW** Attack replay frame recorder
│   ├── bayesian/           **NEW** Bayesian kill-chain confidence
│   ├── embedding/          **NEW** Node2Vec topology drift detector
│   ├── counterfactual/     **NEW** Evasion-distance explainer
│   ├── adversarial/        **NEW** Slow-and-low + impersonation sim
│   ├── threat_intel/       **NEW** OTX/MISP IOC enrichment
│   └── dsl/                **NEW** YAML kill-chain rule loader (kcrl)
├── monitors/               api/auth/network/browser/proxy
├── targets/                api-server, auth-service, web-app
├── topology/               FastAPI graph collector
├── simulation/             Attack scenarios A/B/C
└── evaluation/             MTTD baseline runner
cli/                        **NEW** securisphere CLI (zero-config Compose scan)
paper/                      **NEW** IEEE paper scaffold
benchmarks/                 **NEW** Reproducible MTTD vs Elasticsearch
frontend/src/
├── components/
│   ├── topology3d/         **NEW** react-three-fiber 3D graph
│   ├── cinema/             **NEW** Threat Cinema replay
│   ├── replay/             **NEW** Kill-chain scrubber
│   └── ...                 (existing 30+ components — preserved)
└── ...
```

## 5. Backward-Compatibility Contract

Everything new is **additive**:
- New Redis Stream `securisphere:events` runs **alongside** existing `security_events` pub/sub. Engine subscribes to both for one release.
- New rule DSL files in `backend/engine/dsl/rules/*.yaml` are loaded into the same `self.rules` list — Python rules keep working.
- New tables: `kill_chain_replays`, `service_baselines`, `service_embeddings`, `bayesian_states`, `mitre_coverage_runtime`. Existing tables untouched.
- New API endpoints under `/api/v2/*` (predictions, replay, bayesian, counterfactual, embedding, mitre/heatmap). v1 untouched.
- New 3D dashboard route `/topology3d` and `/cinema` added to AuthenticatedApp router. Existing routes preserved.

## 6. Performance Targets

| Metric | Current | Target | Mechanism |
|---|---|---|---|
| Event → incident latency | ~5s (single-thread + buffer prune cost) | < 1s | Redis Streams + consumer groups (parallel rules) |
| Detection rate (3 scenarios) | claimed in trials, not gated | > 90% (CI gate) | GitHub Actions runs simulation, parses kill chain count |
| MTTD vs raw Elastic | hand-measured | reproducible benchmarks/run.sh | Auto report JSON |
| UI first-paint | ~1s (Vite dev) | < 600ms (prod) | Already achievable; verify in build |

---

This map is the blueprint. Subsequent phases reference these line numbers and module paths.
