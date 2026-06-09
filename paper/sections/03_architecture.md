# III. System Architecture

SecuriSphere is a Docker-first, topology-aware kill-chain reconstruction platform for containerized microservice environments. Unlike traditional SIEM systems that correlate events by IP address, SecuriSphere maintains attack continuity using stable **Docker service identities** that persist across container restarts, IP changes, and scale events.

## A. High-Level Design

The system comprises five layers: (1) event ingestion from monitors and custom agents, (2) topology discovery via Docker SDK polling, (3) service-centric correlation and kill-chain reconstruction, (4) campaign aggregation for alert reduction, and (5) a React analyst dashboard with real-time WebSocket updates.

Events flow through Redis Streams (`securisphere:events`) to a correlation engine that partitions a 15-minute sliding window by `correlation_key`—a stable identifier derived from `source_service_name` and `destination_service_name` before falling back to IP. Incidents are merged into campaigns via `create_or_update_campaign()`, which emits at most one Discord notification per attacker pattern.

PostgreSQL stores metadata (incidents, kill chains, campaigns, topology snapshots). Elasticsearch indexes raw events for full-text search. A phased FastAPI extraction provides ingestion (`:5010`) and read APIs (`:8001`) while the Flask gateway retains authentication and Socket.IO.

## B. Service Identity Model

Each normalized event carries:

- `source_service_name` — Compose label `com.docker.compose.service`
- `destination_service_name` — target microservice
- `workload_id` — ephemeral container ID (churn-prone)
- `correlation_key` — `svc:auth-service→api-server` or `ip:10.0.1.5`

Correlation rules match on `correlation_key` by default (`CORRELATION_MODE=service`), ensuring that an attacker's reconnaissance against `auth-service` before and after a container restart links to the same incident chain.

## C. Topology Graph

The topology collector (FastAPI, port 5080) polls Docker every 10 seconds, building a directed graph of services and observed communication edges. Drift events (image replacement, unexpected containers) publish as security events mapped to MITRE T1525. The correlation engine queries `/topology/service/{name}` for enrichment and uses graph reachability for lateral-movement rules.

## D. Deployment

The reference testbed is a 16-service Docker Compose stack: 3 target microservices, 5 monitors, Redis, PostgreSQL, correlation engine, topology collector, WAF proxy, Flask API, React dashboard, and optional Elasticsearch under the `search` profile.
