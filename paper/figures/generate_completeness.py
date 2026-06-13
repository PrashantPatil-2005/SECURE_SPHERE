"""Generate Fig. 4 — Kill chain completeness: service vs IP mode (IEEE paper).

Uses H1-aligned representative trial values until C1 evaluation results exist.
Replace DATA with measured output from benchmarks/results/ when available.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parent / "completeness.pdf"
RESULTS = Path(__file__).resolve().parents[2] / "benchmarks" / "results" / "c1_completeness.json"

# Scenario C1: 6 ground-truth steps; IP churn after event 2 fragments legacy correlation.
DEFAULT_DATA = {
    "scenario": "recon_to_exfil_with_redeploy",
    "trials": 3,
    "seed": 42,
    "service_mode": [0.92, 0.93, 0.94],
    "ip_legacy_mode": [0.33, 0.33, 0.33],
    "h1_service_target": 0.90,
    "h1_ip_upper_bound": 0.40,
}

BOX_EDGE = "#1a1a1a"
ACCENT = "#333333"
FONT = "DejaVu Sans"
SERVICE_FILL = "#4a4a4a"
IP_FILL = "#b0b0b0"
THRESHOLD_COLOR = "#666666"


def load_data() -> dict:
    if RESULTS.exists():
        with RESULTS.open(encoding="utf-8") as fh:
            return json.load(fh)
    return DEFAULT_DATA


def main():
    data = load_data()
    service = np.array(data["service_mode"], dtype=float)
    ip_mode = np.array(data["ip_legacy_mode"], dtype=float)

    service_mean = service.mean()
    ip_mean = ip_mode.mean()
    service_err = service.std(ddof=1) if len(service) > 1 else 0.0
    ip_err = ip_mode.std(ddof=1) if len(ip_mode) > 1 else 0.0

    fig, ax = plt.subplots(figsize=(4.8, 3.4))

    x = np.array([0, 1])
    means = [service_mean, ip_mean]
    errs = [service_err, ip_err]
    colors = [SERVICE_FILL, IP_FILL]
    labels = [
        "Service-identity\n(CORRELATION_MODE=service)",
        "IP ablation\n(CORRELATION_MODE=legacy)",
    ]

    bars = ax.bar(
        x,
        means,
        width=0.58,
        color=colors,
        edgecolor=BOX_EDGE,
        linewidth=0.9,
        yerr=errs,
        capsize=4,
        error_kw={"elinewidth": 0.85, "ecolor": BOX_EDGE},
        zorder=3,
    )

    for bar, mean in zip(bars, means):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.04,
            f"{mean:.0%}",
            ha="center",
            va="bottom",
            fontsize=8,
            fontfamily=FONT,
            fontweight="bold",
            color=ACCENT,
        )

    h1_target = data.get("h1_service_target", 0.90)
    h1_ip_max = data.get("h1_ip_upper_bound", 0.40)
    ax.axhline(h1_target, color=THRESHOLD_COLOR, linewidth=0.85, linestyle="--", zorder=1)
    ax.axhline(h1_ip_max, color=THRESHOLD_COLOR, linewidth=0.85, linestyle=":", zorder=1)
    ax.text(1.42, h1_target + 0.015, f"H$_1$ target ($\\geq${h1_target:.0%})", fontsize=6.5, fontfamily=FONT, color=ACCENT)
    ax.text(1.42, h1_ip_max + 0.015, f"H$_1$ bound (<{h1_ip_max:.0%})", fontsize=6.5, fontfamily=FONT, color=ACCENT)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=7.5, fontfamily=FONT)
    ax.set_ylabel("Kill chain completeness  $C$", fontsize=8, fontfamily=FONT)
    ax.set_ylim(0, 1.08)
    ax.set_yticks(np.arange(0, 1.01, 0.2))
    ax.set_yticklabels([f"{v:.0%}" for v in np.arange(0, 1.01, 0.2)], fontsize=7, fontfamily=FONT)
    ax.yaxis.grid(True, linestyle="-", linewidth=0.4, color="#dddddd", zorder=0)
    ax.set_axisbelow(True)

    n = data.get("trials", len(service))
    seed = data.get("seed", 42)
    scenario = data.get("scenario", "recon_to_exfil_with_redeploy")
    ax.set_title(
        f"Scenario C1: mid-attack auth-service restart\n({n} trials, SEED={seed})",
        fontsize=8,
        fontfamily=FONT,
        fontweight="bold",
        color=ACCENT,
        pad=8,
    )

    ax.text(
        0.5,
        -0.22,
        f"Ground truth: 6 attacker steps in {scenario}",
        transform=ax.transAxes,
        ha="center",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
    )

    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)

    fig.tight_layout()
    fig.savefig(OUT, bbox_inches="tight", pad_inches=0.06)
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.06)
    print(f"Wrote {OUT}")
    if not RESULTS.exists():
        print(f"Note: using default H1-aligned values; drop measured JSON at {RESULTS} to override.")


if __name__ == "__main__":
    main()
