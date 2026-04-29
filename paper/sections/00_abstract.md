# Abstract (draft)

Container orchestration breaks IP-based event correlation: a pod restart
re-IPs every workload, severing cross-event linkage in tools that key
their state on `source_ip`. We present **SecuriSphere**, a kill-chain
reconstruction system that correlates security events on the *service
name* — the only identifier that survives container churn — and
augments rule-based detection with a per-service behavioural fingerprint
and a topology-drift detector that flags silent supply-chain rewrite.

We evaluate three claims: (C1) MTTD stability under forced redeploy
mid-attack, (C2) coherent kill-chain reconstruction across browser- and
network-layer telemetry sharing a service identity, and (C3) the
neighbour-fingerprint signal as a real-time proxy for supply-chain
compromise. Results are reported against IP-correlation baselines drawn
from Falco, Wazuh, and a stock Elastic SIEM ruleset.

> Numbers will appear here once `/benchmarks/run.py` is run end-to-end on
> the reference lab. The paper does not ship with placeholder numbers.
