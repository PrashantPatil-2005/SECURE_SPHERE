# SecuriSphere — Research Paper Scaffold

This directory hosts the in-progress paper that accompanies the
SecuriSphere project. It is **scaffolding** — sections are stubbed with the
intended argument and the experiments that would back it. We do not ship
fabricated numbers; results sections are empty until the corresponding
benchmark in `/benchmarks` produces them.

## Working title

> **Service-Identity Correlation Survives Container Churn:
> A Kill-Chain Reconstruction System for Microservice Telemetry**

## Why this paper exists (the gap)

SIEMs and runtime-security tools (Falco, Wazuh, Cilium-Tetragon, Elastic
SIEM) correlate by IP, hostname, or PID. In a containerised microservice
environment IPs change on every redeploy, so cross-event correlation
breaks the moment a container restarts. SecuriSphere correlates on
**service name** — the only identifier that survives churn — and
reconstructs full kill chains across that identifier.

Three claims we want to support empirically:

1. **C1 — Correctness under churn:** detection MTTD remains stable when
   containers are forcibly redeployed mid-attack. IP-correlation baselines
   degrade.
2. **C2 — Cross-layer reconstruction:** browser-layer and network-layer
   events that share a service name produce a single coherent chain.
3. **C3 — Topology-drift catches supply-chain compromise:** the
   neighbour-fingerprint signal flags silently-replaced services that
   pure runtime detectors miss.

## Structure

| File | Section |
| --- | --- |
| `sections/00_abstract.md`     | Abstract |
| `sections/01_introduction.md` | Introduction + problem statement |
| `sections/02_related.md`      | Related work (Falco, Wazuh, Cilium, Elastic SIEM, MITRE Engenuity) |
| `sections/03_threat_model.md` | Threat model + assumptions |
| `sections/04_design.md`       | Architecture + service-identity correlation |
| `sections/05_evaluation.md`   | Methodology + the three claims |
| `sections/06_results.md`      | (empty until `/benchmarks` produces numbers) |
| `sections/07_limitations.md`  | What we cannot claim |
| `sections/08_future.md`       | TGNN, eBPF integration, federated detection |

## How figures get built

Figures are generated from `/benchmarks/results/*.json` — never hand-drawn.
A figure that doesn't have a regenerator script in this repo doesn't
appear in the paper. That keeps the paper honest about what is measured.
