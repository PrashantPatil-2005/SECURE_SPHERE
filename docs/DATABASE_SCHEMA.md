# Database Schema

Canonical DDL: `scripts/init_db.sql` + `scripts/migrations/*.sql`.

## Core tables

### security_events
Raw normalized events from monitors and ingestion.

| Column | Type | Notes |
|--------|------|-------|
| event_id | UUID | Unique |
| source_service_name | VARCHAR(100) | Stable Compose/K8s service name |
| destination_service_name | VARCHAR(100) | Target service |
| workload_id | VARCHAR(64) | Container/task ID (churn-prone) |
| correlation_key | VARCHAR(200) | Stable correlation identity |
| source_ip | VARCHAR(45) | Fallback only |

### correlated_incidents
Engine-emitted incidents.

| Column | Type | Notes |
|--------|------|-------|
| incident_id | UUID | |
| source_service_name | VARCHAR(100) | |
| destination_service_name | VARCHAR(100) | |
| service_path | TEXT[] | Ordered traversal |
| correlation_key | VARCHAR(200) | |

### risk_scores
Per-entity threat state (service-first).

| Column | Type | Notes |
|--------|------|-------|
| entity_type | VARCHAR(20) | `service`, `ip`, `workload` |
| entity_key | VARCHAR(200) | Primary key for scoring |
| entity_ip | VARCHAR(45) | Nullable legacy |

### campaigns
Campaign aggregation (migration 004 + 005).

| Column | Type | Notes |
|--------|------|-------|
| actor_id | VARCHAR(100) | `service:api-server`, `ip:1.2.3.4`, etc. |
| actor_type | VARCHAR(20) | `service`, `ip`, `user`, `workload` |
| source_service_name | VARCHAR(100) | |
| service_path | TEXT[] | Union across incidents |
| kill_chain_steps | JSONB | Deduped steps |

### kill_chains
Reconstructed attack paths (migration 006 adds `graph` JSONB).

| Column | Type | Notes |
|--------|------|-------|
| service_path | TEXT[] | Linear path |
| graph | JSONB | `{nodes:[], edges:[]}` for D3 |
| mttd_seconds | FLOAT | detected_at − first_event_at |

### topology_snapshots
Historical topology graphs from collector.

## Migrations

| File | Purpose |
|------|---------|
| 001_audit_log.sql | Audit trail |
| 002_severity_default.sql | NOT NULL severity |
| 003_target_username.sql | Credential attacks |
| 004_campaigns.sql | Campaign table |
| 005_service_identity.sql | Service-centric columns |
| 006_kill_chain_graph.sql | Graph JSONB on kill_chains |
