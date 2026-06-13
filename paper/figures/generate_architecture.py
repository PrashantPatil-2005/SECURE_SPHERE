"""Generate Fig. 1 — SecuriSphere overall system architecture (IEEE paper)."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "architecture.pdf"

# IEEE-friendly monochrome palette
BOX_FILL = "#f5f5f5"
BOX_EDGE = "#1a1a1a"
ACCENT = "#333333"
ARROW = "#222222"
LAYER_BG = "#fafafa"
LAYER_EDGE = "#cccccc"
FONT = "DejaVu Sans"


def box(ax, x, y, w, h, text, fontsize=7.5, bold=False, fill=BOX_FILL):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.04",
        linewidth=0.9,
        edgecolor=BOX_EDGE,
        facecolor=fill,
        transform=ax.transData,
        zorder=3,
    )
    ax.add_patch(patch)
    weight = "bold" if bold else "normal"
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontfamily=FONT,
        fontweight=weight,
        zorder=4,
        linespacing=1.25,
    )
    return patch


def arrow(ax, x1, y1, x2, y2, label=None, style="-|>", rad=0.0, fontsize=6.5):
    arr = FancyArrowPatch(
        (x1, y1),
        (x2, y2),
        arrowstyle=style,
        mutation_scale=9,
        linewidth=0.85,
        color=ARROW,
        connectionstyle=f"arc3,rad={rad}",
        zorder=2,
    )
    ax.add_patch(arr)
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mx,
            my + 0.08,
            label,
            ha="center",
            va="bottom",
            fontsize=fontsize,
            fontfamily="DejaVu Sans Mono",
            color=ACCENT,
            zorder=5,
        )


def layer_band(ax, y, h, label):
    band = FancyBboxPatch(
        (0.35, y),
        10.5,
        h,
        boxstyle="square,pad=0",
        linewidth=0.6,
        edgecolor=LAYER_EDGE,
        facecolor=LAYER_BG,
        zorder=0,
    )
    ax.add_patch(band)
    ax.text(
        0.08,
        y + h / 2,
        label,
        ha="center",
        va="center",
        fontsize=7,
        fontfamily=FONT,
        fontweight="bold",
        rotation=90,
        color=ACCENT,
        zorder=1,
    )


def main():
    fig, ax = plt.subplots(figsize=(9.0, 7.0))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 9)
    ax.axis("off")

    # --- Layer 1: Event ingestion ---
    layer_band(ax, 6.8, 1.8, "L1\nIngestion")
    box(ax, 0.5, 7.8, 1.4, 0.6, "api-server", fontsize=7)
    box(ax, 2.1, 7.8, 1.4, 0.6, "auth-service", fontsize=7)
    box(ax, 3.7, 7.8, 1.2, 0.6, "web-app", fontsize=7)
    box(ax, 5.1, 7.8, 1.2, 0.6, "WAF\nproxy", fontsize=7)
    box(ax, 6.5, 7.8, 1.3, 0.6, "Canary\nHoneypot", fontsize=7, bold=True)

    box(ax, 0.5, 7.0, 1.4, 0.5, "API Monitor", fontsize=7)
    box(ax, 2.1, 7.0, 1.4, 0.5, "Auth Monitor", fontsize=7)
    box(ax, 3.7, 7.0, 1.2, 0.5, "Net Monitor", fontsize=7)
    box(ax, 5.1, 7.0, 1.2, 0.5, "Browser\nMonitor", fontsize=7)
    box(ax, 6.5, 7.0, 1.3, 0.5, "Proxy\nMonitor", fontsize=7)

    for x in (1.2, 2.8, 4.3, 5.7, 7.15):
        arrow(ax, x, 7.8, x, 7.5, style="-")

    # --- Layer 2: Topology ---
    layer_band(ax, 5.3, 1.2, "L2\nTopology")
    box(ax, 0.5, 5.6, 1.6, 0.6, "Docker\nDaemon API", fontsize=7)
    box(ax, 2.5, 5.6, 2.0, 0.6, "Topology Collector\n(FastAPI :5080)", fontsize=7, bold=True)
    box(ax, 4.9, 5.6, 2.4, 0.6, "Service Graph $G=(V,E)$\n+ drift detection", fontsize=7)

    arrow(ax, 2.1, 5.9, 2.5, 5.9, style="-|>")
    arrow(ax, 4.5, 5.9, 4.9, 5.9, style="-|>")

    # --- Event bus (Redis Streams) ---
    box(ax, 8.1, 6.4, 2.6, 0.8, "Redis Streams\nsecurisphere:events", fontsize=7.5, bold=True, fill="#ececec")

    for x in (1.2, 2.8, 4.3, 5.7, 7.15):
        arrow(ax, x, 7.0, 8.1, 6.8, style="-|>", rad=0.08)

    # --- Layer 3: Correlation ---
    layer_band(ax, 3.2, 1.8, "L3\nCorrelate")
    box(ax, 0.5, 3.6, 1.8, 0.8, "Adaptive\nSteganography", fontsize=7, bold=True)
    box(ax, 2.6, 3.6, 1.8, 0.8, "Steganalysis\nModule", fontsize=7, bold=True)
    box(ax, 7.5, 4.1, 3.0, 0.8, "Correlation Engine (SICA)\n$\\kappa(e)$ buffers · YAML rules\nlateral-movement · kill chains", fontsize=7.2, bold=True)
    box(ax, 7.5, 3.3, 3.0, 0.6, "Campaign Aggregator\ncreate_or_update_campaign()", fontsize=7)

    arrow(ax, 9.4, 6.4, 9.0, 4.9, style="-|>")
    arrow(ax, 7.3, 5.9, 7.5, 4.5, style="-|>", label="query $G$", rad=-0.15)
    arrow(ax, 9.0, 4.1, 9.0, 3.9, style="-|>")

    # --- Layer 4: Persistence ---
    layer_band(ax, 1.6, 1.3, "L4\nStore")
    box(ax, 0.5, 1.9, 1.8, 0.7, "PostgreSQL\nincidents · chains", fontsize=7, bold=True)
    box(ax, 2.6, 1.9, 1.8, 0.7, "Redis\ncache · pub/sub", fontsize=7)
    box(ax, 4.7, 1.9, 2.2, 0.7, "Elasticsearch\n(raw events, opt.)", fontsize=7)

    arrow(ax, 1.4, 3.6, 1.4, 2.6, style="-|>")
    arrow(ax, 3.5, 3.6, 3.5, 2.6, style="-|>")
    arrow(ax, 7.5, 3.6, 2.3, 2.6, style="-|>", rad=0.1)
    arrow(ax, 8.2, 3.3, 4.0, 2.6, style="-|>", rad=0.05)
    arrow(ax, 9.0, 3.3, 5.8, 2.6, style="-|>", rad=-0.08)

    # --- Layer 5: Presentation ---
    layer_band(ax, 0.1, 1.3, "L5\nUI")
    box(ax, 7.4, 0.2, 1.4, 0.5, "Flask API\n:8000", fontsize=7, bold=True)
    box(ax, 9.1, 0.2, 1.4, 0.5, "Socket.IO\nreal-time push", fontsize=7)
    box(ax, 7.4, 0.85, 3.1, 0.45, "React Analyst Dashboard\nD3 attack path · MITRE heatmap", fontsize=7.5, bold=True)

    arrow(ax, 1.4, 1.9, 7.4, 0.45, style="-|>", rad=-0.15)
    arrow(ax, 3.5, 1.9, 7.4, 1.07, style="-|>", rad=-0.1)
    arrow(ax, 8.1, 0.7, 8.1, 0.85, style="-|>")
    arrow(ax, 9.8, 0.7, 9.8, 0.85, style="-|>")

    # Attacker annotation
    ax.annotate(
        "Attacker",
        xy=(0.5, 8.1),
        xytext=(0.1, 8.6),
        fontsize=7.5,
        fontfamily=FONT,
        arrowprops=dict(arrowstyle="-|>", lw=0.8, color=ARROW),
    )

    fig.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.05)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()