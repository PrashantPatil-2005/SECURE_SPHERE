"""Rule DSL — load YAML rules, evaluate them against the rolling buffer.

Schema (minimal but real)
-------------------------

```yaml
name: recon_to_exploit_yaml
incident_type: recon_to_exploit          # used for cooldown + Discord routing
severity: high
description: Reconnaissance followed by an exploitation attempt
mitre_techniques: [T1046, T1190]
window_seconds: 600                       # how far back to search
sequence:                                 # ordered list of stages
  - id: recon
    match:
      any:
        - event_type: port_scan
        - event_type: service_enumeration
        - event_type: directory_enumeration
  - id: exploit
    same:                                 # same-source/service constraint
      key: source_service_name            # default = source_service_name
    within_seconds: 300                   # gap from previous stage
    match:
      any:
        - event_type: sql_injection_attempt
        - event_type: command_injection
        - event_type: path_traversal_attempt
explanation: "Service {source} performed recon then attempted exploitation"
```

Evaluator is intentionally simple: it walks the buffer once per rule and
checks for an ordered match using the ``same`` key as the join key. Not as
expressive as Sigma — but it covers every kill-chain rule the engine
already had, and the YAML round-trips cleanly to the dashboard's rule
editor.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("RuleDSL")

try:
    import yaml  # type: ignore
    _YAML = True
except Exception:
    _YAML = False


def _evt_ts(event: Dict[str, Any]) -> Optional[datetime]:
    raw = event.get("timestamp")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", ""))
    except Exception:
        return None


def _matches_clause(event: Dict[str, Any], clause: Dict[str, Any]) -> bool:
    """One leaf clause = a dict of equality constraints. ``any`` and ``all``
    are handled by the caller."""
    for key, expected in clause.items():
        if key in ("any", "all"):
            continue
        actual = event.get(key)
        if isinstance(expected, list):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True


def _matches(event: Dict[str, Any], spec: Any) -> bool:
    if isinstance(spec, dict):
        if "any" in spec:
            return any(_matches(event, c) for c in spec["any"])
        if "all" in spec:
            return all(_matches(event, c) for c in spec["all"])
        return _matches_clause(event, spec)
    return False


@dataclass
class Stage:
    id: str
    match: Dict[str, Any]
    same_key: str = "source_service_name"
    within_seconds: Optional[int] = None


@dataclass
class Rule:
    name: str
    incident_type: str
    severity: str
    description: str
    mitre_techniques: List[str]
    sequence: List[Stage]
    window_seconds: int = 900
    explanation: str = ""

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Rule":
        seq_raw = d.get("sequence") or []
        stages: List[Stage] = []
        for s in seq_raw:
            stages.append(Stage(
                id=str(s.get("id") or s.get("name") or f"stage{len(stages)}"),
                match=s.get("match") or {},
                same_key=(s.get("same") or {}).get("key", "source_service_name"),
                within_seconds=s.get("within_seconds"),
            ))
        return cls(
            name=str(d["name"]),
            incident_type=str(d.get("incident_type") or d["name"]),
            severity=str(d.get("severity", "medium")),
            description=str(d.get("description", "")),
            mitre_techniques=list(d.get("mitre_techniques") or []),
            sequence=stages,
            window_seconds=int(d.get("window_seconds", 900)),
            explanation=str(d.get("explanation", "")),
        )

    # ------------------------------------------------------------------
    def evaluate(
        self, latest_event: Dict[str, Any], buffer: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Return an incident dict if the latest event completes the
        sequence. The latest event must match the *last* stage; earlier
        stages are searched backwards in the buffer."""
        if not self.sequence:
            return None
        last_stage = self.sequence[-1]
        if not _matches(latest_event, last_stage.match):
            return None

        join_key = latest_event.get(last_stage.same_key)
        if not join_key:
            return None

        last_ts = _evt_ts(latest_event) or datetime.now()
        cutoff = last_ts - timedelta(seconds=self.window_seconds)

        # Walk earlier stages oldest→newest, anchoring after each match.
        anchor_ts: Optional[datetime] = None
        matched_events: List[Dict[str, Any]] = []
        for stage in self.sequence[:-1]:
            found: Optional[Dict[str, Any]] = None
            for ev in buffer:
                if ev is latest_event:
                    continue
                if ev.get(stage.same_key) != join_key:
                    continue
                ts = _evt_ts(ev)
                if not ts or ts < cutoff or ts > last_ts:
                    continue
                if anchor_ts and ts < anchor_ts:
                    continue
                if not _matches(ev, stage.match):
                    continue
                if stage.within_seconds and anchor_ts:
                    if (ts - anchor_ts).total_seconds() > stage.within_seconds:
                        continue
                found = ev
                anchor_ts = ts
                break
            if not found:
                return None
            matched_events.append(found)

        # Last stage's within_seconds is from the previous anchor.
        if last_stage.within_seconds and anchor_ts:
            if (last_ts - anchor_ts).total_seconds() > last_stage.within_seconds:
                return None

        matched_events.append(latest_event)
        return self._build_incident(join_key, matched_events)

    def _build_incident(
        self, join_key: str, matched: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        first = matched[0]
        last = matched[-1]
        first_ts = _evt_ts(first) or datetime.now()
        last_ts = _evt_ts(last) or datetime.now()
        services = []
        for ev in matched:
            svc = ev.get("source_service_name")
            if svc and svc not in services:
                services.append(svc)
        explanation = self.explanation.format(source=join_key) if self.explanation else self.description
        return {
            "incident_type": self.incident_type,
            "severity": self.severity,
            "description": self.description,
            "explanation": explanation,
            "rule_name": self.name,
            "rule_source": "yaml",
            "mitre_techniques": list(self.mitre_techniques),
            "first_event_at": first_ts.isoformat(),
            "detected_at": last_ts.isoformat(),
            "mttd_seconds": max(0.0, (last_ts - first_ts).total_seconds()),
            "service_path": services,
            "kill_chain_steps": [
                {
                    "stage": s.id,
                    "service": ev.get("source_service_name"),
                    "event_type": ev.get("event_type"),
                    "timestamp": ev.get("timestamp"),
                }
                for s, ev in zip(self.sequence, matched)
            ],
            "join_key": join_key,
        }


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

def load_rules(directories: List[str]) -> List[Rule]:
    """Load every ``*.yaml`` rule from each directory. Skips silently if
    PyYAML isn't installed (engine still works with hardcoded rules)."""
    if not _YAML:
        logger.info("PyYAML not installed; YAML rules disabled")
        return []
    rules: List[Rule] = []
    for d in directories:
        if not d or not os.path.isdir(d):
            continue
        for fname in sorted(os.listdir(d)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(d, fname)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not isinstance(data, dict) or "name" not in data:
                    logger.warning("Skipping malformed rule: %s", path)
                    continue
                rules.append(Rule.from_dict(data))
            except Exception as exc:
                logger.warning("Failed to load rule %s: %s", path, exc)
    logger.info("Loaded %d YAML rule(s)", len(rules))
    return rules


class RuleEngine:
    """Thin runner — held by CorrelationEngine, evaluated per event."""
    def __init__(self, rules: List[Rule]) -> None:
        self.rules = rules
        self.hits: Dict[str, int] = {r.name: 0 for r in rules}

    def evaluate(
        self, event: Dict[str, Any], buffer: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        incidents: List[Dict[str, Any]] = []
        for rule in self.rules:
            try:
                inc = rule.evaluate(event, buffer)
                if inc:
                    self.hits[rule.name] = self.hits.get(rule.name, 0) + 1
                    incidents.append(inc)
            except Exception as exc:
                logger.debug("YAML rule %s error: %s", rule.name, exc)
        return incidents

    def stats(self) -> Dict[str, Any]:
        return {
            "rule_count": len(self.rules),
            "hits": dict(self.hits),
            "rules": [{"name": r.name, "incident_type": r.incident_type, "severity": r.severity} for r in self.rules],
        }
