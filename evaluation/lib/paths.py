"""Project-root path helpers for experiment scripts."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the SecuriSphere repository root (parent of ``evaluation/``)."""
    return Path(__file__).resolve().parents[2]


def results_dir() -> Path:
    """Default directory for experiment JSON/CSV artifacts."""
    d = project_root() / "evaluation" / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d


def benchmarks_results_dir() -> Path:
    """Throughput benchmark CSV output directory."""
    d = project_root() / "benchmarks" / "results"
    d.mkdir(parents=True, exist_ok=True)
    return d
