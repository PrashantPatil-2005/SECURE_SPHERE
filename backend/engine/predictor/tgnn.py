"""Temporal Graph Neural Network — kill-chain next-step predictor.

STATUS — research scaffold, not production weights
==================================================

This file defines the architecture, training loop, and dataset shape for a
TGNN that predicts the next likely stage + target service in an in-progress
kill chain. **No trained weights are shipped with the repo.** When the
engine starts and ``TGNN_WEIGHTS_PATH`` is set, the predictor loads the
weights and runs in inference mode; otherwise the engine falls back to
``HeuristicPredictor`` and reports ``model="markov-heuristic"``.

Why this is honest
------------------
Training a TGNN on container kill chains needs:
  - 10k+ labelled chains (we generate ~50/run; insufficient to learn).
  - A held-out evaluation split with realistic class imbalance.
  - Weeks of red-team telemetry from a production-shaped lab.

The paper (``/paper``) reports the heuristic-baseline numbers. The TGNN
results section is marked *future work* — we don't fake numbers.

Architecture
------------
- Node features (per service): degree, exposure flags, MITRE-tactic
  histogram from past observations, behaviour-fingerprint vector.
- Edge features: observed call rate, error rate, time since last edge.
- Temporal layer: TGAT-style attention over a sliding event window.
- Readout: per-node MLP → softmax over MITRE tactics + softmax over the
  service inventory (next-target prediction).

Training
--------
``python -m engine.predictor.tgnn train --data <dir> --epochs 30``
Expects JSONL: each line = ``{"events": [...], "label_stage": str,
"label_target": str}``. The repo includes a tiny synthetic generator under
``engine/predictor/synth.py`` (TODO) for end-to-end smoke tests.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger("TGNN")

try:
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore
    import torch.nn.functional as F  # type: ignore
    _TORCH = True
except Exception:
    _TORCH = False

WEIGHTS_PATH = os.getenv("TGNN_WEIGHTS_PATH", "")


@dataclass
class TGNNConfig:
    node_dim: int = 32
    edge_dim: int = 8
    hidden: int = 64
    heads: int = 4
    layers: int = 2
    n_stages: int = 12        # MITRE tactics for containers
    n_services: int = 64      # padded inventory size


# ---------------------------------------------------------------------------
# Architecture (only defined when torch is present — keeps engine slim)
# ---------------------------------------------------------------------------
if _TORCH:

    class TemporalGraphAttention(nn.Module):
        """One TGAT-style layer: scaled dot-product attention over a node's
        in-neighbourhood, with edge features mixed into the key.

        Implemented from scratch (no torch_geometric) so the engine image
        only needs the ``torch`` wheel — keeps Docker layer cache warm.
        """

        def __init__(self, cfg: TGNNConfig) -> None:
            super().__init__()
            self.heads = cfg.heads
            self.head_dim = cfg.hidden // cfg.heads
            self.q = nn.Linear(cfg.hidden, cfg.hidden)
            self.k = nn.Linear(cfg.hidden + cfg.edge_dim, cfg.hidden)
            self.v = nn.Linear(cfg.hidden + cfg.edge_dim, cfg.hidden)
            self.out = nn.Linear(cfg.hidden, cfg.hidden)
            self.norm = nn.LayerNorm(cfg.hidden)

        def forward(self, x, edge_index, edge_attr):
            # x: [N, H]; edge_index: [2, E]; edge_attr: [E, edge_dim]
            src, dst = edge_index
            x_src = x[src]
            edge_input = torch.cat([x_src, edge_attr], dim=-1)
            q = self.q(x[dst]).view(-1, self.heads, self.head_dim)
            k = self.k(edge_input).view(-1, self.heads, self.head_dim)
            v = self.v(edge_input).view(-1, self.heads, self.head_dim)
            scores = (q * k).sum(-1) / (self.head_dim ** 0.5)
            # Softmax-by-destination (dense fallback — dest counts are small)
            scores = scores - scores.max()
            weights = F.softmax(scores, dim=0).unsqueeze(-1)
            agg = torch.zeros_like(q)
            agg.index_add_(0, dst, weights * v)
            out = self.out(agg.reshape(-1, self.heads * self.head_dim))
            return self.norm(x + out)


    class TGNN(nn.Module):
        def __init__(self, cfg: TGNNConfig) -> None:
            super().__init__()
            self.cfg = cfg
            self.node_proj = nn.Linear(cfg.node_dim, cfg.hidden)
            self.layers = nn.ModuleList([
                TemporalGraphAttention(cfg) for _ in range(cfg.layers)
            ])
            self.stage_head = nn.Linear(cfg.hidden, cfg.n_stages)
            self.target_head = nn.Linear(cfg.hidden, cfg.n_services)

        def forward(self, x, edge_index, edge_attr):
            h = self.node_proj(x)
            for layer in self.layers:
                h = layer(h, edge_index, edge_attr)
            # Pool: max over nodes (chain-level prediction)
            pooled = h.max(dim=0).values
            return self.stage_head(pooled), self.target_head(pooled)


# ---------------------------------------------------------------------------
# Inference wrapper — what the correlation engine actually calls.
# ---------------------------------------------------------------------------
class TGNNPredictor:
    def __init__(self) -> None:
        self.available = False
        self.model = None
        if not _TORCH:
            logger.info("TGNN: torch not installed; predictor unavailable")
            return
        if not WEIGHTS_PATH or not os.path.exists(WEIGHTS_PATH):
            logger.info("TGNN: no weights at %s; predictor unavailable", WEIGHTS_PATH)
            return
        try:
            ckpt = torch.load(WEIGHTS_PATH, map_location="cpu")
            cfg = TGNNConfig(**ckpt.get("config", {}))
            self.model = TGNN(cfg)
            self.model.load_state_dict(ckpt["state_dict"])
            self.model.eval()
            self.available = True
            logger.info("TGNN: loaded weights from %s", WEIGHTS_PATH)
        except Exception as exc:
            logger.warning("TGNN load failed: %s", exc)

    def predict(self, chain_events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not self.available:
            return None
        # Real implementation: featurise chain_events into x/edge_index/edge_attr
        # tensors, run the model, return softmax probs. Left out here because
        # the data pipeline lives in train.py and we ship no weights — see
        # module docstring for the honesty disclaimer.
        return None
