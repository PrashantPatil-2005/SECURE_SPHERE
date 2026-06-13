"""Generate Fig. 2 — SecuriSphere end-to-end event processing workflow (IEEE paper)."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "workflow.pdf"

BOX_FILL = "#f5f5f5"
BOX_EDGE = "#1a1a1a"
ACCENT = "#333333"
ARROW = "#222222"
STEP_FILL = "#e8e8e8"
LAYER_EDGE = "#cccccc"
FONT = "DejaVu Sans"


def box(ax, x, y, w, h, text, fontsize=7, bold=False, fill=BOX_FILL):
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
        linespacing=1.2,
    )
    return patch


def arrow(ax, x1, y1, x2, y2, style="-|>", rad=0.0):
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


def step_badge(ax, x, y, n):
    circle = plt.Circle((x, y), 0.14, facecolor=STEP_FILL, edgecolor=BOX_EDGE, linewidth=0.8, zorder=6)
    ax.add_patch(circle)
    ax.text(
        x,
        y,
        str(n),
        ha="center",
        va="center",
        fontsize=7,
        fontfamily=FONT,
        fontweight="bold",
        zorder=7,
    )


def main():
    fig, ax = plt.subplots(figsize=(7.5, 2.9))
    ax.set_xlim(0, 10.4)
    ax.set_ylim(0, 3.2)
    ax.axis("off")

    y_main = 1.55
    h = 0.72
    gap = 0.14

    # Step 1 — Attacker action
    x = 0.12
    w = 1.0
    step_badge(ax, x + 0.12, y_main + h + 0.22, 1)
    box(ax, x, y_main, w, h, "Attacker\naction", fontsize=7, bold=True)
    box(ax, x, y_main - 0.82, w, 0.55, "Target service\n(api-server)", fontsize=6.5)
    arrow(ax, x + w / 2, y_main, x + w / 2, y_main - 0.27, style="-|>")
    ax.text(x + w / 2, y_main - 0.95, "telemetry", ha="center", fontsize=6, fontfamily="DejaVu Sans Mono", color=ACCENT)

    # Step 2 — Monitor normalize
    x2 = x + w + gap
    w2 = 1.15
    step_badge(ax, x2 + 0.12, y_main + h + 0.22, 2)
    box(ax, x2, y_main, w2, h, "Monitor\nnormalize", fontsize=7, bold=True)
    box(ax, x2, y_main - 0.82, w2, 0.55, "svc names\n$\\kappa(e)$", fontsize=6.5)

    arrow(ax, x + w, y_main + h / 2, x2, y_main + h / 2, style="-|>")

    # Step 3 — Redis Streams
    x3 = x2 + w2 + gap
    w3 = 1.28
    step_badge(ax, x3 + 0.12, y_main + h + 0.22, 3)
    box(ax, x3, y_main, w3, h, "Redis Streams\nsecurisphere:events", fontsize=6.8, bold=True, fill="#ececec")

    arrow(ax, x2 + w2, y_main + h / 2, x3, y_main + h / 2, style="-|>")

    # Step 4 — Correlation engine
    x4 = x3 + w3 + gap
    w4 = 1.48
    step_badge(ax, x4 + 0.12, y_main + h + 0.22, 4)
    box(ax, x4, y_main, w4, h, "Correlation Engine\nprune $B_{\\kappa(e)}$", fontsize=7, bold=True)
    box(ax, x4 + 0.02, y_main - 0.82, w4 - 0.04, 0.55, "rules on $(e,B,G)$", fontsize=6.5)

    arrow(ax, x3 + w3, y_main + h / 2, x4, y_main + h / 2, style="-|>")

    # Topology side input
    box(ax, x4 + 0.2, 2.55, 1.1, 0.42, "Topology $G$", fontsize=6.5)
    arrow(ax, x4 + 0.75, 2.55, x4 + 0.75, y_main + h, style="-|>")

    # Step 5 — Incident + campaign
    x5 = x4 + w4 + gap
    w5 = 1.28
    step_badge(ax, x5 + 0.12, y_main + h + 0.22, 5)
    box(ax, x5, y_main, w5, h, "Incident +\ncampaign", fontsize=7, bold=True)
    box(ax, x5, y_main - 0.82, w5, 0.55, "conf. $\\geq\\theta$\n(MTTD)", fontsize=6.5)

    arrow(ax, x4 + w4, y_main + h / 2, x5, y_main + h / 2, style="-|>")

    # Step 6 — Persist kill chain
    x6 = x5 + w5 + gap
    w6 = 1.15
    step_badge(ax, x6 + 0.12, y_main + h + 0.22, 6)
    box(ax, x6, y_main, w6, h, "PostgreSQL\nkill chain", fontsize=7, bold=True)
    box(ax, x6, y_main - 0.82, w6, 0.55, "service_path\ngraph JSON", fontsize=6.5)

    arrow(ax, x5 + w5, y_main + h / 2, x6, y_main + h / 2, style="-|>")

    # Step 7 — Analyst dashboard
    x7 = x6 + w6 + gap
    w7 = 1.18
    step_badge(ax, x7 + 0.12, y_main + h + 0.22, 7)
    box(ax, x7, y_main, w7, h, "Analyst\ndashboard", fontsize=7, bold=True)
    box(ax, x7, y_main - 0.82, w7, 0.55, "D3 path\nSocket.IO", fontsize=6.5)

    arrow(ax, x6 + w6, y_main + h / 2, x7, y_main + h / 2, style="-|>")

    # API read path from persistence to UI
    arrow(ax, x6 + w6 / 2, y_main, x7 + w7 / 2, y_main - 0.27, style="-|>", rad=-0.22)

    # Swimlane labels
    ax.text(
        0.02,
        2.95,
        "Attack surface",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
        fontweight="bold",
    )
    ax.text(
        3.1,
        2.95,
        "Ingestion & bus",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
        fontweight="bold",
    )
    ax.text(
        5.5,
        2.95,
        "Detection",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
        fontweight="bold",
    )
    ax.text(
        8.0,
        2.95,
        "Response",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
        fontweight="bold",
    )

    # Bottom timeline bar
    bar = FancyBboxPatch(
        (0.12, 0.12),
        10.1,
        0.22,
        boxstyle="square,pad=0",
        linewidth=0.5,
        edgecolor=LAYER_EDGE,
        facecolor="#fafafa",
        zorder=0,
    )
    ax.add_patch(bar)
    ax.text(
        4.9,
        0.23,
        "End-to-end path: attacker action $\\rightarrow$ normalized event $\\rightarrow$ correlated incident $\\rightarrow$ analyst visualization",
        ha="center",
        va="center",
        fontsize=6.5,
        fontfamily=FONT,
        color=ACCENT,
        zorder=1,
    )

    fig.savefig(OUT, bbox_inches="tight", pad_inches=0.05)
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.05)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
