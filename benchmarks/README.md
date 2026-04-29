# SecuriSphere Benchmarks

Reproducible scenarios that produce the numbers in `/paper/sections/06_results.md`.

## Quick run

```bash
# Engine + lab must be up first
docker compose up -d
python -m benchmarks.run --scenario recon_to_exfil_stable
python -m benchmarks.run --all   # every scenario, results → benchmarks/results/
```

Each scenario writes a JSON report:

```
benchmarks/results/<scenario>_<utc-timestamp>.json
```

with this shape:

```json
{
  "scenario": "recon_to_exfil_stable",
  "started_at": "2025-...",
  "duration_seconds": 42.0,
  "events_sent": 28,
  "incidents": [
    { "incident_id": "...", "incident_type": "...", "mttd_seconds": 3.7 }
  ],
  "expected_chain": ["recon", "exploit", "lateral", "exfil"],
  "observed_chain": ["recon", "exploit", "lateral", "exfil"],
  "metrics": {
    "mttd_first_incident": 3.7,
    "chain_completeness":  1.0,
    "false_positives":     0
  }
}
```

## Files

- `run.py`            — runner CLI (loads scenario YAML, drives the engine)
- `scenarios/*.yaml`  — declarative attack scripts
- `report.py`         — aggregates results JSON into the paper's tables
- `results/`          — output directory (gitignored except for `.gitkeep`)

## What this is NOT

- It is not a load test. We do not measure throughput here; that lives
  in `/backend/evaluation/baseline_mttd.py`.
- It does not run baselines (Falco, Elastic) — those need an external
  fixture container we have not yet stood up. Adding them is tracked
  in the paper limitations section.
