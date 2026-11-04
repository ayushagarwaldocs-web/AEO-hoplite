"""Shared matplotlib style for the repo's figures (light, print-friendly).

Colors follow a validated categorical order (adjacent pairs pass CVD and
normal-vision separation; the first three slots pass all pairs). Light slots
sit below 3:1 contrast on the surface, so charts carry direct value labels and
every figure has a CSV table next to it.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch, Rectangle  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6", "#e34948"]
SEQ_BLUE = ["#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7", "#3987e5",
            "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b"]
DIVERGING_MID = "#f0efec"


def apply() -> None:
    plt.rcParams.update({
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
        "font.family": "sans-serif", "font.sans-serif": ["Helvetica Neue", "Helvetica", "Arial", "DejaVu Sans"],
        "font.size": 9, "axes.titlesize": 10, "axes.titleweight": "semibold", "axes.titlecolor": INK,
        "axes.labelcolor": INK2, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
        "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": False, "grid.color": GRID, "grid.linewidth": 0.8, "grid.linestyle": "-",
        "legend.frameon": False, "legend.fontsize": 8, "text.color": INK,
        "lines.linewidth": 2, "lines.solid_capstyle": "round",
    })


def save(fig, stem: str | Path) -> None:
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".png"), dpi=220, bbox_inches="tight")
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    plt.close(fig)


def _px_per_unit(ax) -> tuple[float, float]:
    ax.figure.canvas.draw()
    bbox = ax.get_window_extent()
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    return bbox.width / abs(x1 - x0), bbox.height / abs(y1 - y0)


def hbar(ax, y: float, start: float, length: float, color: str, max_px: float = 18,
         band: float = 0.62, round_end: bool = True, radius_px: float = 4) -> None:
    """A horizontal bar with a rounded data-end and a square baseline end.

    Set the axes limits before calling: rounding is computed in screen pixels.
    """
    if length <= 0:
        return
    px_x, px_y = _px_per_unit(ax)
    height = min(band, max_px / px_y)
    if not round_end:
        ax.add_patch(Rectangle((start, y - height / 2), length, height, facecolor=color, edgecolor="none"))
        return
    r = min(radius_px / px_x, length / 2)
    ax.add_patch(FancyBboxPatch((start, y - height / 2), length, height,
                                boxstyle=f"round,pad=0,rounding_size={r}",
                                mutation_aspect=px_x / px_y, facecolor=color, edgecolor="none"))
    ax.add_patch(Rectangle((start, y - height / 2), min(r * 1.05, length), height,
                           facecolor=color, edgecolor="none"))
