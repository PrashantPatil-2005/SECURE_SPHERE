"""Generate Fig. 3 — SICA detection and correlation pipeline (IEEE paper)."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Polygon

OUT = Path(__file__).resolve().parent / "sica_pipeline.pdf"

BOX_FILL = "#f5f5f5"
BOX_EDGE = "#1a1a1a"
ACCENT = "#333333"
ARROW = "#222222"
HIGHLIGHT = "#ececec"
ACCEPT_FILL = "#e0e0e0"
REJECT_FILL = "#f0f0f0"
LAYER_EDGE = "#cccccc"
FONT = "DejaVu Sans"
MONO = "DejaVu Sans Mono"

CX = 5.0
BW = 5.8
BX = CX - BW / 2


def box(ax, x, y, w, h, text, fontsize=7, bold=False, fill=BOX_FILL, mono=False):
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
    family = MONO if mono else FONT
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        fontfamily=family,
        fontweight=weight,
        zorder=4,
        linespacing=1.12,
    )
    return patch


def diamond(ax, cx, cy, w, h, text, fontsize=6.5):
    pts = [(cx, cy + h / 2), (cx + w / 2, cy), (cx, cy - h / 2), (cx - w / 2, cy)]
    patch = Polygon(pts, closed=True, facecolor=HIGHLIGHT, edgecolor=BOX_EDGE, linewidth=0.9, zorder=3)
    ax.add_patch(patch)
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fontsize, fontfamily=FONT, zorder=4, linespacing=1.05)
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


def label(ax, x, y, text, fontsize=6, ha="left", mono=False):
    ax.text(x, y, text, ha=ha, va="center", fontsize=fontsize, fontfamily=MONO if mono else FONT, color=ACCENT, zorder=5)


def stage_band(ax, y, h, title):
    band = FancyBboxPatch(
        (0.35, y),
        9.3,
        h,
        boxstyle="square,pad=0",
        linewidth=0.55,
        edgecolor=LAYER_EDGE,
        facecolor="#fafafa",
        zorder=0,
    )
    ax.add_patch(band)
    ax.text(0.08, y + h / 2, title, ha="center", va="center", fontsize=6.5, fontfamily=FONT, fontweight="bold", rotation=90, color=ACCENT, zorder=1)


def main():
    fig, ax = plt.subplots(figsize=(7.2, 7.4))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8.6)
    ax.axis("off")

    # --- A ---
    stage_band(ax, 7.45, 0.76, "A\nIngest")
    box(ax, BX, 7.5, BW, 0.56, "Normalized event  $e \\in \\Sigma$\n$(t, s_{src}, s_{dst}, \\tau, \\lambda, \\ldots)$", fontsize=7, bold=True)
    label(ax, 8.65, 7.76, "input alphabet", mono=True)
    arrow(ax, CX, 7.5, CX, 7.36)

    # --- B ---
    stage_band(ax, 6.18, 1.1, "B\nKey")
    box(ax, BX, 6.26, BW, 0.44, "$\\kappa(e)$ correlation key resolution  (Eq.~2)", fontsize=7, bold=True)
    tiers = [
        ("1", "svc:$s_{src}\\!\\rightarrow\\!s_{dst}$"),
        ("2", "svc:$s_{src}$"),
        ("3", "wl:$w$"),
        ("4", "ip:$\\alpha_{src}$"),
    ]
    tw, gap = 1.25, 0.1
    for i, (rank, txt) in enumerate(tiers):
        box(ax, BX + 0.1 + i * (tw + gap), 6.26 - 0.54, tw, 0.36, f"{rank}. {txt}", fontsize=6.1, fill=HIGHLIGHT)
    label(ax, 8.65, 6.4, "churn-stable\n(cases 1–2)")
    arrow(ax, CX, 5.72, CX, 5.58)

    # --- C ---
    stage_band(ax, 4.96, 0.54, "C\nBuffer")
    box(ax, BX, 5.04, BW, 0.48, "Partitioned buffer  $B_k(t)$  per key $k$\nprune stale events ($\\delta$=900s)  ·  append $e$  (Eq.~3)", fontsize=6.7, bold=True)
    arrow(ax, CX, 5.04, CX, 4.9)

    # --- D ---
    stage_band(ax, 3.52, 1.3, "D\nDetect")
    box(
        ax,
        BX,
        3.6,
        BW,
        0.72,
        "Rule set $R$:  evaluate $P_r(e, B_k, G)$  for each $r \\in R$\nlateral-movement  ·  impossible-path  ·  YAML predicates\nquery topology $G$ for reachability / TTL$_{edge}$",
        fontsize=6.6,
        bold=True,
    )

    diamond(ax, CX, 3.18, 1.28, 0.48, "$P{=}$TRUE?")
    arrow(ax, CX, 3.6, CX, 3.42)
    label(ax, 6.82, 3.18, "no", mono=True, ha="right")
    box(ax, 7.65, 2.96, 1.2, 0.36, "skip rule", fontsize=6.3, fill=REJECT_FILL)
    arrow(ax, 6.65, 3.18, 7.65, 3.14, style="-|>")
    arrow(ax, CX, 2.94, CX, 2.8)

    # --- E ---
    stage_band(ax, 2.08, 0.64, "E\nScore")
    box(ax, BX, 2.16, BW, 0.4, "Bayesian posterior  $\\phi(e,B) \\propto P(\\mathrm{attack})\\prod P(f|\\mathrm{attack})$  (Eq.~5)", fontsize=6.7, bold=True)

    diamond(ax, CX, 1.76, 1.12, 0.42, "$\\phi \\geq \\theta$?")
    arrow(ax, CX, 2.16, CX, 1.98)
    label(ax, 6.78, 1.76, "no", mono=True, ha="right")
    box(ax, 7.65, 1.6, 1.2, 0.3, "suppress alert", fontsize=6.2, fill=REJECT_FILL)
    arrow(ax, 6.58, 1.76, 7.65, 1.76, style="-|>")
    label(ax, CX + 0.1, 1.9, "yes", mono=True)
    arrow(ax, CX, 1.55, CX, 1.52, style="-|>")

    # --- F: acceptance ---
    stage_band(ax, 1.02, 0.5, "F\nSICA")
    ax.text(5.0, 1.44, "$\\mathrm{SICA}=(Q,\\Sigma,\\delta,q_0,F,\\Gamma)$  (Eq.~1)", ha="center", fontsize=7, fontfamily=FONT, fontweight="bold", color=ACCENT, zorder=2)

    box(ax, BX, 1.08, 2.4, 0.44, "Emit incident $\\sigma$\nCampaignAggregator.merge()", fontsize=6.4, bold=True)
    box(ax, BX + 2.6, 1.08, 3.05, 0.44, "SICA transition  $\\delta(q,\\sigma_{in})\\rightarrow q'$\nvalidate ATT\\&CK phase order", fontsize=6.4, bold=True, fill=HIGHLIGHT)
    box(ax, BX + 5.8, 1.08, BW - 5.8, 0.44, "Accept $K$ iff $q_f \\in F$\npersist $G_{kc}$ · MTTD", fontsize=6.4, bold=True, fill=ACCEPT_FILL)
    arrow(ax, 2.4, 1.3, 4.0, 1.3, style="-|>")
    arrow(ax, 6.05, 1.3, 7.25, 1.3, style="-|>")

    # --- Automaton strip (bottom) ---
    band = FancyBboxPatch(
        (0.35, 0.04),
        9.3,
        0.76,
        boxstyle="square,pad=0",
        linewidth=0.55,
        edgecolor=LAYER_EDGE,
        facecolor="#f7f7f7",
        zorder=0,
    )
    ax.add_patch(band)
    ax.text(0.55, 0.41, "Attack-phase $Q$:", ha="left", fontsize=6.3, fontfamily=FONT, fontweight="bold", color=ACCENT, zorder=2)

    states = [
        ("$q_0$", "start"),
        ("Init.\nAccess", "T1190"),
        ("Execution", "T1078"),
        ("Lat.\nMove", "T1021"),
        ("Collection", "T1005"),
        ("Exfiltration\n$F$", "T1041"),
    ]
    sw, sg = 1.05, 0.14
    sx, sy, sh = 1.55, 0.18, 0.5

    for i, (name, mitre) in enumerate(states):
        fill = ACCEPT_FILL if "$F$" in name else BOX_FILL
        bold = i == 0 or "$F$" in name
        box(ax, sx + i * (sw + sg), sy, sw, sh, name, fontsize=6.0, bold=bold, fill=fill)
        label(ax, sx + i * (sw + sg) + sw / 2, sy - 0.1, f"$\\Gamma$:{mitre}", ha="center", fontsize=5.6, mono=True)
        if i < len(states) - 1:
            arrow(ax, sx + i * (sw + sg) + sw, sy + sh / 2, sx + (i + 1) * (sw + sg), sy + sh / 2, style="-|>")

    label(ax, 8.55, 0.41, "invalid $\\delta$ → reject", ha="left", fontsize=6)
    arrow(ax, 5.25, 1.08, 5.25, 0.72, style="-|>")

    fig.savefig(OUT, bbox_inches="tight", pad_inches=0.06)
    fig.savefig(OUT.with_suffix(".png"), dpi=300, bbox_inches="tight", pad_inches=0.06)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
