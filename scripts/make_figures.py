# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib"]
# ///
"""Regenerate the library's four figures from the CSVs in ../data/.

    uv run scripts/make_figures.py [--highlight "South Africa"]
"""

import argparse
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
INK, MUTED, GRID, SURF, HI = "#1a1a19", "#6b6b68", "#e8e8e6", "#fcfcfb", "#2a78d6"
PCTS = [10, 30, 50, 70, 90]

plt.rcParams.update(
    {
        "font.size": 11,
        "text.color": INK,
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": SURF,
        "axes.facecolor": SURF,
    }
)


def spaghetti(latest, ind, unit, fname, highlight):
    l = latest[latest["indicator"] == ind]
    fig, ax = plt.subplots(figsize=(7.6, 5.2), dpi=150)
    ax.grid(True, color=GRID, linewidth=0.6)
    for _, r in l.iterrows():
        ax.plot(PCTS, [r[f"q{i}"] for i in range(1, 6)], color=MUTED, alpha=0.25, lw=1)
    med = [l[f"q{i}"].median() for i in range(1, 6)]
    ax.plot(PCTS, med, color=INK, lw=2.5)
    ax.annotate(
        f"median of {len(l)} countries",
        (PCTS[-1], med[-1]),
        xytext=(6, 0),
        textcoords="offset points",
        fontsize=10,
        va="center",
    )
    hl = l[l["country"] == highlight]
    if len(hl):
        vals = [hl[f"q{i}"].iloc[0] for i in range(1, 6)]
        ax.plot(PCTS, vals, color=HI, lw=2.5, marker="o", ms=5, mec=SURF, mew=1)
        ax.annotate(
            f"{highlight} {int(hl['year'].iloc[0])}",
            (PCTS[-1], vals[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            color=HI,
            fontsize=10,
            va="center",
            fontweight="bold",
        )
    ax.set_xticks(PCTS)
    ax.set_xticklabels(
        ["Poorest\n(10th pct)", "Second\n(30th)", "Middle\n(50th)", "Fourth\n(70th)", "Richest\n(90th)"],
        fontsize=9,
    )
    ax.set_ylabel(unit)
    ax.set_title(
        f"{ind} by household wealth rank — every country's most recent DHS survey",
        fontsize=12,
        loc="left",
        pad=12,
    )
    ax.margins(x=0.14)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / fname)
    plt.close(fig)


def strip_by_region(latest, fname, highlight):
    rng = np.random.default_rng(7)
    tfr = latest[latest["indicator"] == "TFR"]
    regions = tfr.groupby("region")["slope"].median().sort_values().index.tolist()
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), dpi=150, sharey=True)
    for ax, ind, ttl in zip(axes, ["TFR", "U5MR"], ["Fertility (TFR)", "Under-5 mortality"]):
        l = latest[latest["indicator"] == ind]
        for yi, rgn in enumerate(regions):
            sub = l[l["region"] == rgn]
            if not len(sub):
                continue
            ax.axhline(yi, color=GRID, lw=0.6, zorder=0)
            q25, q50, q75 = sub["slope"].quantile([0.25, 0.5, 0.75])
            ax.plot([q25, q75], [yi, yi], color=INK, lw=3, alpha=0.22, zorder=1, solid_capstyle="round")
            ax.plot([q50], [yi], marker="|", ms=15, color=INK, mew=2.2, zorder=3)
            ax.scatter(
                sub["slope"],
                yi + rng.uniform(-0.16, 0.16, len(sub)),
                s=22,
                color=MUTED,
                alpha=0.55,
                zorder=2,
                edgecolors="none",
            )
            hl = sub[sub["country"] == highlight]
            if len(hl):
                ax.scatter(hl["slope"], [yi], s=75, color=HI, zorder=4, edgecolors=SURF, linewidths=1.2)
                ax.annotate(
                    highlight,
                    (hl["slope"].iloc[0], yi),
                    xytext=(0, 11),
                    textcoords="offset points",
                    color=HI,
                    fontsize=9.5,
                    fontweight="bold",
                    ha="center",
                )
        ax.axvline(0, color=GRID, lw=1)
        ax.set_title(ttl, fontsize=12, loc="left", pad=10)
    counts = tfr.groupby("region")["country"].nunique()
    axes[0].set_yticks(range(len(regions)))
    axes[0].set_yticklabels([f"{r}  (n={counts.get(r, 0)})" for r in regions], fontsize=9)
    fig.supxlabel(
        "log-rate slope across wealth rank  (more negative = steeper gradient, poor higher)",
        fontsize=10,
        color=MUTED,
    )
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / fname)
    plt.close(fig)


def slopes_over_time(lib, fname, highlight):
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2), dpi=150, sharey=True)
    for ax, ind, ttl in zip(
        axes,
        ["TFR", "U5MR"],
        ["Fertility gradient over survey years", "Under-5 mortality gradient over survey years"],
    ):
        l = lib[lib["indicator"] == ind]
        ax.scatter(l["year"], l["slope"], s=14, color=MUTED, alpha=0.4, edgecolors="none")
        yrs = sorted(l["year"].unique())
        roll = [l[(l["year"] >= y - 4) & (l["year"] <= y + 4)]["slope"].median() for y in yrs]
        ax.plot(yrs, roll, color=INK, lw=2.2)
        hl = l[l["country"] == highlight]
        ax.scatter(hl["year"], hl["slope"], s=60, color=HI, zorder=4, edgecolors=SURF, linewidths=1.2)
        for _, r in hl.iterrows():
            ax.annotate(
                int(r["year"]),
                (r["year"], r["slope"]),
                xytext=(0, 9),
                textcoords="offset points",
                color=HI,
                fontsize=9,
                ha="center",
                fontweight="bold",
            )
        ax.axhline(0, color=GRID, lw=1)
        ax.set_xlabel("survey year")
        ax.set_title(ttl, fontsize=12, loc="left", pad=10)
    axes[0].set_ylabel("log-rate slope across wealth rank")
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / fname)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--highlight", default="South Africa")
    args = ap.parse_args()

    lib = pd.read_csv(ROOT / "data" / "gradient_library.csv")
    latest = pd.read_csv(ROOT / "data" / "gradient_library_latest.csv").merge(
        pd.read_csv(ROOT / "data" / "dhs_regions.csv"), on="country", how="left"
    )
    (ROOT / "figures").mkdir(exist_ok=True)
    spaghetti(latest, "TFR", "births per woman", "fig1_tfr_gradients.png", args.highlight)
    spaghetti(latest, "U5MR", "deaths per 1,000 live births", "fig2_u5mr_gradients.png", args.highlight)
    strip_by_region(latest, "fig3_slopes_by_region.png", args.highlight)
    slopes_over_time(lib, "fig4_slopes_over_time.png", args.highlight)
    print("wrote 4 figures to figures/")


if __name__ == "__main__":
    main()
