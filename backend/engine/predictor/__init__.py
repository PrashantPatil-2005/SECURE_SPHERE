"""Kill-chain next-step predictor (Phase 13 — research scaffold).

Two implementations:
  - ``HeuristicPredictor``: Markov transition matrix over past kill-chain
    stages, runs on every install, no ML deps.
  - ``TGNNPredictor``: Temporal Graph Neural Network. Architecture is
    defined; training script provided; weights are NOT shipped — see
    ``predictor/tgnn.py`` for the honest disclaimer.
"""
from .heuristic import HeuristicPredictor

__all__ = ["HeuristicPredictor"]
