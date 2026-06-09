# Correlation Engine Design

## Core principle

Correlate by **stable service identity**, not transient IP addresses.

## correlation_key resolution

Priority (implemented in `backend/engine/shared/event_schema.py`):

1. `svc:{source_service_name}→{destination_service_name}` when both present
2. `svc:{source_service_name}` when source service known
3. `wl:{workload_id}` when workload ID present
4. `ip:{source_ip}` fallback only

## Partitioned event buffers

```python
event_buffers: Dict[str, List[Event]]  # keyed by correlation_key
CORRELATION_WINDOW = 900  # 15 minutes
```

Each new event appends to its partition; stale entries pruned per partition.

## Rule matching pseudocode

```
function process_event(event):
    key = resolve_correlation_key(event)
    buffer = event_buffers[key]
    prune(buffer, window=15m)
    for rule in rules:
        if rule.matches(event, buffer, key):
            incident = rule.emit(event, buffer)
            publish_incident(incident)
```

## Topology-aware lateral movement

```
function rule_service_lateral_movement(event, buffer, key):
    prior = find(buffer, dest=event.destination_service_name)
    if not prior: return
    src = prior.source_service_name
    dst = event.destination_service_name
    if graph_reachable(topology, src, dst) or observed_edge(src, dst):
        return incident(type="lateral_movement", service_path=[src, dst])
```

## CORRELATION_MODE flag

| Value | Behavior |
|-------|----------|
| service | Match on correlation_key only |
| legacy | Match on source_ip only |
| dual | Match if correlation_key OR ip agrees (migration) |

## YAML DSL rules

Rules in `backend/engine/rules/builtin/*.yaml` use `same.key: source_service_name` by default.
