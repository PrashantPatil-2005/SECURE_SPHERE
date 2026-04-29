"""Counterfactual explainer + kill-chain diff for SOC analysts."""
from .counterfactual import explain_chain
from .diff import diff_chains

__all__ = ["explain_chain", "diff_chains"]
