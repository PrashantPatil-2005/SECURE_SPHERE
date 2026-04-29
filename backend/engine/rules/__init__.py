"""YAML-based correlation rule DSL.

Each rule is a single YAML file under ``rules/builtin/`` (built-in) or a
mounted directory (operator-supplied). The engine loads them at startup and
evaluates them alongside the hardcoded Python rules until those are fully
migrated. New rules are added without touching engine code, which is the
whole point of the DSL.
"""
from .dsl import Rule, RuleEngine, load_rules

__all__ = ["Rule", "RuleEngine", "load_rules"]
