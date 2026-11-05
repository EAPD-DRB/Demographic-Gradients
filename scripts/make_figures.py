# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib"]
# ///
"""Regenerate the library's figures from the CSVs in ../data/.

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
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"], ["Fertility (TFR)", "Infant mortality"]):
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
        ["TFR", "IMR"],
        ["Fertility gradient over survey years", "Infant mortality gradient over survey years"],
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


def amr_age_profile(fname):
    """Adult-mortality tilt by age band: the age-fade, across countries."""
    path = ROOT / "data" / "adult_mortality_gradients.csv"
    if not path.exists():
        return False
    amr = pd.read_csv(path)
    mx = amr[amr["measure"] == "mx"].copy()
    if not len(mx):
        return False
    mx["agemid"] = (mx["age_lo"] + mx["age_hi"]) / 2
    mx["series"] = mx["country"] + " " + mx["year"].astype(str)
    colors = {"Brazil 2010": "#6b6b68", "South Africa 2001": "#7fb0e8", "South Africa 2007": "#2a78d6"}
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4), dpi=150, sharey=True)
    for ax, sex, ttl in zip(axes, ["male", "female"], ["Men", "Women"]):
        sub = mx[mx["sex"] == sex]
        ends = []
        for series, g in sub.groupby("series"):
            g = g.sort_values("agemid")
            c = colors.get(series, "#1a1a19")
            ax.plot(g["agemid"], g["slope"], color=c, lw=2.2, marker="o", ms=5, mec=SURF, mew=1)
            ends.append([series, c, g["agemid"].iloc[-1], g["slope"].iloc[-1]])
        # dodge end labels that would collide
        ends.sort(key=lambda e: e[3])
        for i in range(1, len(ends)):
            if ends[i][3] - ends[i - 1][3] < 0.09:
                ends[i][3] = ends[i - 1][3] + 0.09
        for series, c, x, y in ends:
            ax.annotate(series, (x, y), xytext=(6, 0), textcoords="offset points",
                        color=c, fontsize=8.5, va="center")
        ax.grid(True, color=GRID, linewidth=0.6)
        # zero is the substantive line: above it the gradient has reversed
        ax.axhline(0, color="#1a1a19", lw=1, alpha=0.55)
        ax.set_xlabel("age band midpoint")
        ax.set_title(ttl, fontsize=12, loc="left", pad=10)
        ax.margins(x=0.22)
    axes[0].set_ylabel("mortality tilt across wealth rank")
    fig.suptitle("The adult-mortality gradient fades with age in every census — "
                 "and in the poorest countries it reverses",
                 fontsize=12, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(ROOT / "figures" / fname)
    plt.close(fig)
    return True


def fertility_age_offsets(latest, fname):
    """The fertility age offsets, and what they mean for a median country."""
    tilts, offs = ROOT / "data" / "fertility_age_tilts.csv", ROOT / "data" / "fertility_age_offsets.csv"
    if not (tilts.exists() and offs.exists()):
        return False
    t = pd.read_csv(tilts).sort_values(["country", "year", "survey", "age_lo"])
    o = pd.read_csv(offs).sort_values("age_lo")
    last = t.groupby("country")["survey"].last()
    t = t[t["survey"].isin(last)]
    x = np.arange(len(o))
    labels = [f"{a}–{b}" for a, b in zip(o["age_lo"], o["age_hi"])]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6), dpi=150, gridspec_kw={"wspace": 0.28})
    for ax in (a1, a2):
        ax.grid(True, axis="y", color=GRID, linewidth=0.6)
        ax.set_xticks(x, labels)
        ax.set_xlabel("mother's age")
    for _, g in t.groupby("survey"):
        a1.plot(x, g["offset"].values, color=MUTED, alpha=0.13, lw=1)
    a1.fill_between(x, o["iqr_lo"], o["iqr_hi"], color=HI, alpha=0.15, lw=0)
    a1.axhline(0, color=INK, lw=1, ls=(0, (4, 3)))
    a1.text(x[-1] + 0.45, 0.06, "single TFR tilt\nat every age", ha="right", va="bottom",
            color=MUTED, fontsize=8.5)
    a1.plot(x, o["offset"], color=HI, lw=2, marker="o", ms=7, mec=SURF, mew=1.5, zorder=3)
    for i, v in enumerate(o["offset"]):
        a1.annotate(f"{v:+.2f}".replace("-", "−"), (i, v), textcoords="offset points",
                    xytext=(0, 10 if v >= 0 else -16), ha="center", fontsize=9)
    a1.set_ylim(-2.6, 1.6)
    a1.set_ylabel("offset added to the country's TFR tilt")
    a1.set_title(f"Age offsets: median of {o['countries'].max()} countries, IQR band,\n"
                 "gray = each country's latest survey", loc="left", fontsize=11)
    n_last = int(o["countries"].iloc[-1])
    a1.text(x[-1], -2.5, f"{labels[-1]}: {n_last} countries (elsewhere a quintile has no births)",
            ha="right", fontsize=8, color=MUTED)
    tfr = latest.loc[latest["indicator"] == "TFR", "slope"].median()
    ref = np.exp(-tfr * 0.8)
    ratio = np.exp(-(tfr + o["offset"].values) * 0.8)
    a2.axhline(ref, color=INK, lw=1, ls=(0, (4, 3)))
    a2.text(x[-1] + 0.45, ref - 0.06, f"single TFR tilt:\n{ref:.1f}× at every age", ha="right",
            va="top", color=MUTED, fontsize=8.5)
    a2.plot(x, ratio, color=HI, lw=2, marker="o", ms=7, mec=SURF, mew=1.5, zorder=3)
    for i, v in enumerate(ratio):
        below = v < ref and ref - v < 0.3  # keep the label off the reference line
        a2.annotate(f"{v:.1f}×", (i, v), textcoords="offset points",
                    xytext=(0, -16 if below else 10), ha="center", fontsize=9)
    a2.set_ylim(1, max(4.6, ratio.max() + 0.5))
    a2.set_ylabel("poorest-decile ÷ richest-decile birth rate")
    a2.set_title(f"What it means for the median country (TFR tilt {tfr:.2f})".replace("-", "−"),
                 loc="left", fontsize=11)
    fig.text(0.01, -0.02, "Source: DHS Program API, age-specific fertility by wealth quintile; "
             "latest survey per country. Offset = age tilt − TFR tilt.", fontsize=8, color=MUTED)
    fig.savefig(ROOT / "figures" / fname, bbox_inches="tight")
    plt.close(fig)
    return True


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
    n = 4 + int(amr_age_profile("fig5_amr_age_profile.png"))
    n += int(fertility_age_offsets(latest, "fig6_fertility_age_offsets.png"))
    print(f"wrote {n} figures to figures/")


if __name__ == "__main__":
    main()
