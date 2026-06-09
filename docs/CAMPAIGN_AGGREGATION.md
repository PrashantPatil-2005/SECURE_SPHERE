# Campaign Aggregation

## create_or_update_campaign()

Public API in `backend/engine/correlation/campaign_aggregator.py`.

```python
def create_or_update_campaign(incident) -> Tuple[Campaign, str]:
    """
    Returns (campaign, change_kind).
    change_kind ∈ {"created", "escalated", "extended", "duplicate"}
    """
```

Legacy alias: `ingest()` → `create_or_update_campaign()`.

## Actor identity priority

1. `service:{source_service_name}` — external attacker hitting known ingress
2. `workload:{workload_id}` — intra-mesh lateral movement
3. `ip:{source_ip}` — fallback
4. `user:{target_username}` — credential attacks

## Merge algorithm

```
actor = resolve_actor_id(incident)
campaign = load_active(actor) or create_new(actor)

if incident_id in campaign.incident_ids:
    return (campaign, "duplicate")

campaign.incident_ids.append(incident_id)
campaign.service_path = dedupe_concat(campaign.service_path, incident.service_path)
campaign.kill_chain_steps = merge_steps(campaign.steps, incident.steps)
campaign.mitre_techniques = union(campaign.mitre, incident.mitre)
campaign.severity = max_severity(campaign, incident)
campaign.max_confidence = max(campaign.max_confidence, incident.confidence)

if severity_increased: change_kind = "escalated"
elif new_stage: change_kind = "extended"
else: change_kind = "extended"

persist(campaign)
return (campaign, change_kind)
```

## Lifecycle

- **Open:** first incident from actor
- **Extended:** new incident, same severity band
- **Escalated:** severity rose or new kill-chain stage
- **Closed:** `CAMPAIGN_IDLE_TIMEOUT` (default 1800s) without new incidents

## Alert gate

Alerts dispatch only when `max_confidence >= CAMPAIGN_ALERT_THRESHOLD` (default 0.75).
