"""
attacker — Scripted, repeatable attack scenarios for SecuriSphere.

Exposes three named kill chains plus a traffic-generator that produces
realistic background noise so detections must be made against a noisy
baseline rather than a synthetic quiet environment.

Entry points
------------
  python -m attacker.scenario_a      # 4-stage brute force → exfiltration
  python -m attacker.scenario_b      # 3-stage recon → SQLi → priv esc
  python -m attacker.scenario_c      # multi-hop lateral movement, 4 services

Environment
-----------
Endpoints default to localhost but respect these env vars:
  SECURISPHERE_API_URL      (default http://localhost:5000)
  SECURISPHERE_AUTH_URL     (default http://localhost:5001)
  SECURISPHERE_BACKEND_URL  (default http://localhost:8000)
  SECURISPHERE_WEBAPP_URL   (default http://localhost:8080)
"""

__all__ = ["scenario_a", "scenario_b", "scenario_c", "traffic_generator", "common"]
