# Evaluation Methodology

## Test bed

The 13-container Docker Compose lab in the repository root is the
reference deployment. Every experiment runs against it, on the same
machine, with the same seed for the attack simulator. The lab exposes:

- 6 mock target microservices (api-server, auth-service, ...)
- 5 monitor containers (api/auth/network/proxy/browser)
- Postgres + Redis + topology-collector + correlation-engine

## Scenarios

Each scenario is a YAML file under `/benchmarks/scenarios/`. A scenario
defines: (a) the sequence of attacker actions (b) any mid-attack churn
events (forced redeploy, scale-down, scale-up) (c) the expected kill chain
that should be reconstructed.

| Scenario | C-claim | Description |
|---|---|---|
| `recon_to_exfil_stable.yaml`         | baseline | No churn; full kill chain |
| `recon_to_exfil_with_redeploy.yaml`  | C1       | Same chain; restart auth-service mid-attack |
| `multi_layer_browser_to_db.yaml`     | C2       | Browser-layer SQLi + network-layer DB exfil |
| `silent_replace_payment.yaml`        | C3       | Replace `payment-service` image with same name |

## Metrics

- **MTTD (mean-time-to-detect):** seconds between the first attacker
  action and the engine emitting the corresponding incident.
- **Chain completeness:** fraction of attacker steps that appear in the
  reconstructed `kill_chain_steps`.
- **False-positive rate:** incidents emitted during a 10-min benign
  workload (browser monitor + topology drift on a stable lab).
- **Posterior calibration:** Brier score of the Bayesian confidence
  posterior against the ground-truth attack/benign label.

## Baselines

- **IP-correlation (in-tree):** the same engine run with
  `service-correlation` disabled.
- **Falco** with default container ruleset.
- **Elastic SIEM** with the public ATT&CK detection rules.

> Falco / Elastic numbers will be reported only on the configurations
> we can reproducibly stand up; otherwise we mark the cell N/R
> ("not reproduced") instead of fabricating a value.
