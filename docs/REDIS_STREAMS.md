# Redis Streams Architecture

## Streams

| Stream | Producer | Consumer |
|--------|----------|----------|
| `securisphere:events` | Monitors, ingestion | Correlation engine, search indexer |
| `securisphere:incidents` | Correlation engine | Audit, replay |
| `securisphere:replay:{id}` | Replay recorder | Dashboard replay |
| `securisphere:drift` | Topology collector | Correlation engine |

## Consumer groups

```
XGROUP CREATE securisphere:events correlation-workers $ MKSTREAM
```

Workers: `correlation-workers-{shard}` where `shard = hash(source_service_name) % CORRELATION_WORKERS`.

## EVENT_BUS_MODE

| Mode | Description |
|------|-------------|
| streams | Primary (default in compose) |
| pubsub | Legacy only |
| dual | Bridge pub/sub → stream during migration |

## Pub/sub channels (legacy)

- `security_events` — monitor publish
- `correlated_incidents` — engine output
- `topology_updates` — graph diffs
