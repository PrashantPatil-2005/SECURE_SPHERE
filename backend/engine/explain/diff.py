"""Structural diff between two kill chains.

Useful for two workflows:
  1. Regression testing: did today's rule change alter how this incident
     reconstructs vs the recorded baseline?
  2. Analyst pattern matching: "is this incident the same shape as the
     one we saw last week?" — diff stage sequence + service path + MITRE
     set, return a similarity score.
"""

from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Dict, List


def _stages(chain: Dict[str, Any]) -> List[str]:
    out = []
    for s in chain.get("kill_chain_steps") or []:
        if isinstance(s, dict) and s.get("stage"):
            out.append(str(s["stage"]).lower())
    return out


def _services(chain: Dict[str, Any]) -> List[str]:
    return list(chain.get("service_path") or [])


def _techniques(chain: Dict[str, Any]) -> List[str]:
    return list(chain.get("mitre_techniques") or [])


def _seq_similarity(a: List[str], b: List[str]) -> float:
    if not a and not b:
        return 1.0
    return SequenceMatcher(a=a, b=b).ratio()


def _set_jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(1, len(sa | sb))


def diff_chains(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    l_stages, r_stages = _stages(left), _stages(right)
    l_svc, r_svc = _services(left), _services(right)
    l_tech, r_tech = _techniques(left), _techniques(right)

    stage_sim = _seq_similarity(l_stages, r_stages)
    service_sim = _seq_similarity(l_svc, r_svc)
    technique_sim = _set_jaccard(l_tech, r_tech)
    overall = 0.45 * stage_sim + 0.35 * service_sim + 0.20 * technique_sim

    return {
        "similarity": {
            "overall":            round(overall, 4),
            "stage_sequence":     round(stage_sim, 4),
            "service_path":       round(service_sim, 4),
            "mitre_jaccard":      round(technique_sim, 4),
        },
        "stages": {
            "left":      l_stages,
            "right":     r_stages,
            "added":     [s for s in r_stages if s not in l_stages],
            "removed":   [s for s in l_stages if s not in r_stages],
        },
        "services": {
            "left":      l_svc,
            "right":     r_svc,
            "added":     [s for s in r_svc if s not in l_svc],
            "removed":   [s for s in l_svc if s not in r_svc],
        },
        "techniques": {
            "shared":  sorted(set(l_tech) & set(r_tech)),
            "left_only": sorted(set(l_tech) - set(r_tech)),
            "right_only": sorted(set(r_tech) - set(l_tech)),
        },
    }
