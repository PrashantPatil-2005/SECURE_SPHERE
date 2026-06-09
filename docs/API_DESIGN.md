# API Design

## Service map

| Service | Port | Framework | Role |
|---------|------|-----------|------|
| backend | 8000 | Flask | Auth, Socket.IO, legacy proxy |
| bff | 8001 | FastAPI | Incidents, campaigns, search, MITRE |
| ingestion | 5010 | FastAPI | Event ingest → Redis Streams |
| topology-collector | 5080 | FastAPI | Graph discovery |
| correlation-engine | 5070 | Flask | Health/stats only |

## Auth
All protected routes: `Authorization: Bearer <JWT>` (HS256, `JWT_SECRET`).

## FastAPI BFF (`/api/*` proxied from Flask)

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/incidents | List incidents |
| GET | /api/incidents/{id} | Incident detail + kill chain |
| GET | /api/campaigns | List campaigns |
| GET | /api/campaigns/{id} | Campaign detail |
| GET | /api/search/events | Elasticsearch query |
| GET | /api/mitre-mapping | Technique heatmap |
| GET | /api/evaluation/results | Benchmark summary |

## Ingestion (`:5010`)

| Method | Path | Description |
|--------|------|-------------|
| POST | /ingest/events | Batch normalized events |
| POST | /ingest/syslog | Syslog line parser |
| POST | /ingest/docker-events | Docker event stream |
| GET | /health | Health check |

## WebSocket (Flask-SocketIO on :8000)

| Event | Payload |
|-------|---------|
| new_incident | Incident object |
| campaign_escalated | Campaign + change_kind |
| risk_update | Per-service risk |
| topology_update | Graph diff |

## Topology (`:5080`)

| Method | Path | Description |
|--------|------|-------------|
| GET | /topology/graph | Full graph |
| GET | /topology/service/{name} | Service metadata |
| POST | /topology/edge | Record observed edge |
