"""Provenance metadata attached to every experiment output JSON."""

from __future__ import annotations

import os
import platform
import subprocess
from datetime import datetime, timezone
from typing import Any


def get_git_commit_hash() -> str:
    """Return the current HEAD commit hash, or ``unknown`` if git is unavailable."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return out.strip()
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return "unknown"


def get_machine_spec() -> dict[str, str | int | float]:
    """Capture host metadata for reproducibility manifests."""
    spec: dict[str, str | int | float] = {
        "os": platform.platform(),
        "python": platform.python_version(),
        "cpu_cores": 0,
        "ram_gb": 0.0,
        "hostname": platform.node(),
    }
    try:
        spec["cpu_cores"] = len(os.sched_getaffinity(0))  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        spec["cpu_cores"] = os.cpu_count() or 0

    try:
        import psutil  # type: ignore

        spec["ram_gb"] = round(psutil.virtual_memory().total / (1024**3), 2)
    except ImportError:
        pass

    return spec


def build_result_envelope(
    *,
    seed: int,
    experiment: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Standard header fields required on every experiment JSON artifact.

    Args:
        seed: Random seed used for the trial.
        experiment: Short experiment identifier (e.g. ``C1_churn_resilience``).
        extra: Optional additional top-level keys merged into the envelope.

    Returns:
        Dict with timestamp, git_commit_hash, seed, machine_spec, experiment.
    """
    envelope: dict[str, Any] = {
        "experiment": experiment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit_hash": get_git_commit_hash(),
        "seed": seed,
        "machine_spec": get_machine_spec(),
    }
    if extra:
        envelope.update(extra)
    return envelope
