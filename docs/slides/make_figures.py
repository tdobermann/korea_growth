"""Figures for docs/slides/matsuyama_in_space.tex.

Solves the history-calibrated baseline (scripts/korea_baseline.CURRENT) and plots the
1965-85 paths against the targets in scripts/data_targets.py.

Run from the repository root:
    python docs/slides/make_figures.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for path in (ROOT, ROOT / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from scripts.calibrate_history import history_moments, solve_history  # noqa: E402
from scripts.data_targets import CALIBRATION_KEYS, TARGETS  # noqa: E402
from scripts.korea_baseline import CURRENT, YEARS  # noqa: E402

# Metropolis-friendly palette
INK = "#23373B"
ACCENT = "#EB811B"
GREEN = "#14B03D"

PANELS = [
    ("ag_employment_share", "Agriculture, employment share"),
    ("mnf_va_share", "Manufacturing, value-added share"),
    ("urban_pop_share", "Urban population share"),
    ("exports_gdp", "Exports / GDP"),
    ("real_gdp_pc_index", "Real GDP per capita (1965 = 1)"),
    ("traditional_rice_share", "Traditional share of rice output (no data)"),
]


def main() -> None:
    _, inputs, path = solve_history(CURRENT)
    m = history_moments(inputs, path)

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK, "axes.labelcolor": INK,
                         "xtick.color": INK, "ytick.color": INK, "axes.titlecolor": INK})
    fig, axes = plt.subplots(2, 3, figsize=(9.6, 4.9))
    for ax, (key, title) in zip(axes.flat, PANELS):
        ax.plot(YEARS, m[key], "-o", color=INK, ms=3.5, lw=1.6, label="model, emp. share")
        data_key = "real_gdp_pc_ratio" if key == "real_gdp_pc_index" else key
        for tg in TARGETS:
            if tg.key != data_key:
                continue
            targeted = (tg.key, tg.year) in CALIBRATION_KEYS or (tg.key, tg.year) == ("urban_pop_share", 1965)
            ax.plot(tg.year, tg.value, "s" if targeted else "D", ms=7,
                    mfc=ACCENT if targeted else "white", mec=ACCENT, mew=1.6, zorder=5)
        if key == "ag_employment_share":
            # untargeted value-added share, to show the missing productivity gap
            ax.plot(YEARS, m["ag_va_share"], "--", color=GREEN, lw=1.3, label="model, VA share")
            for tg in TARGETS:
                if tg.key == "ag_va_share":
                    ax.plot(tg.year, tg.value, "D", ms=6, mfc="white", mec=GREEN, mew=1.6, zorder=5)
            ax.legend(frameon=False, fontsize=7, loc="upper right")
        ax.set_title(title, fontsize=9.5)
        ax.set_xticks([1965, 1970, 1975, 1980, 1985])
        ax.grid(alpha=0.25)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    handles = [
        plt.Line2D([], [], color=INK, marker="o", ms=3.5, label="model (baseline)"),
        plt.Line2D([], [], ls="", marker="s", ms=7, mfc=ACCENT, mec=ACCENT, label="data, targeted"),
        plt.Line2D([], [], ls="", marker="D", ms=7, mfc="white", mec=ACCENT, mew=1.6, label="data, untargeted"),
    ]
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False, fontsize=8.5)
    fig.tight_layout(rect=(0, 0.06, 1, 1))
    out = HERE / "fig_history_fit.pdf"
    fig.savefig(out)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
