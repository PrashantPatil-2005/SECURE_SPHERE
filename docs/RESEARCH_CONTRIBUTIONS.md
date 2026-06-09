# Research Contributions

1. **Service-identity correlation under container churn** — Events correlated by Compose/K8s service name survive container restarts and IP reassignment.

2. **Topology-aware lateral movement detection** — Correlation rules consult live service graph and observed edges to detect impossible or suspicious paths.

3. **Campaign-level alert reduction** — `create_or_update_campaign()` collapses N rule fires into one evolving analyst record with Discord PATCH semantics.

4. **Churn-resilient kill-chain reconstruction** — `service_path` and graph JSONB persist stable traversal independent of `workload_id` changes.

## Evaluation

- C1: `recon_to_exfil_with_redeploy.yaml` — restart auth-service mid-attack
- MTTD: `mttd_seconds` on kill_chains table
- Chain completeness: fraction of attacker steps in `kill_chain_steps`

See `experiment/protocol.md` and `paper/sections/05_evaluation.md`.
