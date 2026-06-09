# SecuriSphere Architecture

## High-level ASCII diagram

```
                    ┌─────────────────────────────────────────────────────────┐
                    │                    Internet / Attacker                   │
                    └────────────────────────────┬────────────────────────────┘
                                                 │
         ┌───────────────────────────────────────┼───────────────────────────────────────┐
         │                                       ▼                                       │
         │  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐        │
         │  │ api-server  │   │auth-service │   │   web-app   │   │  waf-proxy  │        │
         │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘        │
         │         │                 │                 │                 │                │
         │  ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐        │
         │  │ api-monitor │   │auth-monitor │   │browser-mon. │   │proxy-monitor│        │
         │  │network-mon. │   │             │   │             │   │             │        │
         │  └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘        │
         │         │                 │                 │                 │                │
         │         └─────────────────┴────────┬────────┴─────────────────┘                │
         │                                      ▼                                          │
         │                         ┌────────────────────────┐                              │
         │                         │  Ingestion (FastAPI)   │                              │
         │                         │  POST /ingest/events   │                              │
         │                         └───────────┬────────────┘                              │
         │                                     │ XADD                                      │
         │                         ┌───────────▼────────────┐                              │
         │                         │   Redis Streams        │                              │
         │                         │ securisphere:events    │                              │
         │                         └───────────┬────────────┘                              │
         │              ┌──────────────────────┼──────────────────────┐                   │
         │              ▼                      ▼                      ▼                   │
         │   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐          │
         │   │ Correlation      │   │ Search Indexer   │   │ Topology         │          │
         │   │ Engine           │◄──│ (ES bulk)        │   │ Collector        │          │
         │   │ (service-key)    │   └────────┬─────────┘   │ (FastAPI :5080)  │          │
         │   └────────┬─────────┘            │             └────────┬─────────┘          │
         │            │                        ▼                      │                   │
         │            │              ┌──────────────────┐             │                   │
         │            ├─────────────►│ Elasticsearch    │             │                   │
         │            │              └──────────────────┘             │                   │
         │            ▼                                                 │                   │
         │   ┌──────────────────┐   ┌──────────────────┐             │                   │
         │   │ Campaign Layer   │──►│ Alert Dispatcher │             │                   │
         │   │ create_or_update │   │ Discord/Email/WS │             │                   │
         │   └────────┬─────────┘   └──────────────────┘             │                   │
         │            ▼                                                 │                   │
         │   ┌──────────────────┐                                      │                   │
         │   │ PostgreSQL       │◄─────────────────────────────────────┘                   │
         │   │ incidents, KC,   │                                                          │
         │   │ campaigns, topo  │                                                          │
         │   └────────┬─────────┘                                                          │
         │            ▼                                                                      │
         │   ┌──────────────────┐   ┌──────────────────┐                                    │
         │   │ Flask Gateway    │   │ FastAPI BFF      │                                    │
         │   │ auth + Socket.IO │◄──│ read APIs        │                                    │
         │   └────────┬─────────┘   └──────────────────┘                                    │
         │            ▼                                                                      │
         │   ┌──────────────────┐                                                           │
         │   │ React Dashboard  │                                                           │
         │   └──────────────────┘                                                           │
         │                         Docker Compose Lab                                       │
         └───────────────────────────────────────────────────────────────────────────────────┘
```

## Event flow

1. Monitors or ingestion service normalize raw logs into canonical events.
2. Events carry `source_service_name`, `destination_service_name`, `workload_id`, `correlation_key`.
3. Events land on Redis Stream `securisphere:events`.
4. Correlation engine consumes by consumer group, partitions buffers by `correlation_key`.
5. Rules fire incidents; kill-chain reconstructor builds `service_path` + graph.
6. `create_or_update_campaign()` merges incidents; alerts dispatch on confidence threshold.
7. Metadata persists to PostgreSQL; raw events indexed in Elasticsearch.
8. Flask WebSocket + FastAPI BFF serve the React dashboard.

## Sequence: ingest → correlate → campaign → alert

```
Monitor/Ingest → XADD stream → CorrelationEngine.process_event
  → enrich_event(topology) → resolve_correlation_key
  → partition buffer → rules → create_incident
  → reconstruct kill chain → create_or_update_campaign
  → NotificationDispatcher (Discord PATCH / Email / WS)
  → Dashboard receives campaign_escalated
```

See also: [CORRELATION_ENGINE.md](CORRELATION_ENGINE.md), [CAMPAIGN_AGGREGATION.md](CAMPAIGN_AGGREGATION.md), [REDIS_STREAMS.md](REDIS_STREAMS.md).
