# Development Roadmap

Living document for the service-centric refactor. See the plan in `.cursor/plans/` for full detail.

| Phase | Status | Deliverable |
|-------|--------|-------------|
| 0 | Done | Architecture docs, paper sections |
| 1 | Done | Service identity schema + event_schema.py |
| 2 | Done | Service-centric correlation engine |
| 3 | Done | create_or_update_campaign() |
| 4 | Done | Elasticsearch + ingestion FastAPI |
| 5 | Done | Email alerts, llama-3.1-8b, MITRE expansion |
| 6 | Done | FastAPI BFF |
| 7 | Done | Frontend kill chain graph, MITRE timeline |
| 8 | Done | Churn benchmark, CI gates |

## Success criteria

1. Attack chain survives auth-service restart (C1 benchmark)
2. Campaign actor_id service-scoped for demo scenarios
3. correlation_key default matching in rules
4. ES powers event search
5. CI green on Linux
