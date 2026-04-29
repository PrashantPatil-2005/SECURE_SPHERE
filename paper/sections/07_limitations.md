# Limitations

The honest section. What this paper deliberately does **not** claim.

1. **TGNN results are absent.** The architecture and training script ship
   under `backend/engine/predictor/tgnn.py`. We did not have enough
   labelled chains to train it usefully, so the reported "next-step
   prediction" numbers are from the Markov heuristic baseline. The TGNN
   row in every results table reads `N/T` — *not trained*.

2. **Single-tenant lab.** Every experiment runs in our 13-container
   Compose deployment. We do not test on Kubernetes, multi-host, or
   cloud-managed clusters. The service-identity claim is unaffected
   (service names are still the only churn-resistant identifier) but the
   topology drift detector's calibration would shift on a real cluster.

3. **Attack scenarios are simulator-driven.** Real attacker traffic is
   different — slower, noisier, less correlated. The baseline FPR we
   report is a lower bound on what production telemetry would produce.

4. **Behavioural fingerprint uses a 60-second window.** Slow attacks
   (low-and-slow data exfiltration over hours) will not produce a strong
   anomaly signal. The window choice is a deliberate trade-off for
   demo-lab realism, not an optimal choice.

5. **Bayesian priors are uncalibrated outside the lab.** The default
   prior table in `confidence/bayesian.py` was tuned by inspection. An
   operator deploying this needs to refit priors on their own labelled
   chains via `/engine/confidence/refit` (TODO).
