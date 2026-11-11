# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib", "adjustText"]
# ///
"""Regenerate the library's figures from the CSVs in ../data/.

    uv run scripts/make_figures.py

Conventions follow statistical publications (DHS further analyses, World Bank
indicator notes): a descriptive title naming the indicator, population and
survey; a Note line explaining what is drawn; a Source line. The title
describes; the finding belongs in the text. Comparisons between wealth groups
use the low/high ratio (lowest-quintile rate over highest-quintile rate, as
published); charts of the library's own estimates plot the wealth gradient
itself (slope of the log rate on wealth rank; 0 = no difference).
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from adjustText import adjust_text  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
INK, MUTED, GRID, SURF, HI = "#1a1a19", "#6b6b68", "#e8e8e6", "#fcfcfb", "#2a78d6"
CONTEXT = "#9c9b97"  # gray for the marks that are context
QUINTILES = ["Lowest", "Second", "Middle", "Fourth", "Highest"]
RANK = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
RATIO_TICKS = [0.3, 0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 10]
DHS = "Source: DHS Program indicator API; author's calculations."
CENSUS = ("Source: IPUMS International and IBGE census microdata; World Bank GNI per "
          "capita; author's calculations.")

plt.style.use(Path(__file__).with_name("figures.mplstyle"))


def num(x, fmt=".2f"):
    """A number with a true minus sign."""
    return format(x, fmt).replace("-", "−")


def frame(fig, title, note, source, top=0.88, bottom=0.2):
    """Descriptive title above; Note and Source lines below."""
    fig.text(0.01, 0.985, title, fontsize=12.5, fontweight="bold", va="top")
    fig.text(0.01, 0.01, f"Note: {note}\n{source}", fontsize=8.5, color=MUTED, va="bottom",
             linespacing=1.4)
    fig.subplots_adjust(top=top, bottom=bottom, left=0.08, right=0.98)


def grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def ratio_axis(ax, axis="y", lo=0.6, hi=6):
    """Log-scaled low/high ratio axis with plain tick labels and a line at 1."""
    (ax.set_yscale if axis == "y" else ax.set_xscale)("log")
    (ax.set_ylim if axis == "y" else ax.set_xlim)(lo, hi)
    a = ax.yaxis if axis == "y" else ax.xaxis
    ticks = [t for t in RATIO_TICKS if lo <= t <= hi]
    a.set_major_locator(FixedLocator(ticks))
    a.set_minor_locator(NullLocator())
    a.set_ticklabels([f"{t:g}" for t in ticks])
    (ax.axhline if axis == "y" else ax.axvline)(1, color=INK, lw=1, alpha=0.55, zorder=1)


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)


def what_is_a_gradient(latest, country="Philippines"):
    """One country's quintile values, the fitted line, and the two summary measures."""
    r = latest[(latest["indicator"] == "TFR") & (latest["country"] == country)].iloc[0]
    q = np.array([r[f"q{i}"] for i in range(1, 6)])
    b, a = np.polyfit(RANK, np.log(q), 1)
    fig, ax = plt.subplots(figsize=(10, 5.2))
    grid(ax)
    ax.bar(RANK, q, width=0.05, color=HI, zorder=2)
    for x, v in zip(RANK, q):
        ax.annotate(f"{v:g}", (x, v), xytext=(0, 5), textcoords="offset points",
                    ha="center", fontsize=10, zorder=5,
                    bbox=dict(boxstyle="square,pad=0.15", fc=SURF, ec="none"))
    xs = np.linspace(0, 1, 100)
    ax.plot(xs, np.exp(a + b * xs), color=INK, lw=1.8, zorder=3)
    ax.annotate("fitted line: ln(TFR) on wealth rank", (0.62, np.exp(a + b * 0.62)),
                xytext=(0.6, q.max() * 0.98), fontsize=9.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.text(1.03, q.max() * 0.72,
            f"Wealth gradient: {num(b)}\n(slope of the fitted line\non a log scale)\n\n"
            f"Low/high ratio: {q[0]:g} / {q[4]:g} = {q[0] / q[4]:.1f}\n"
            "(lowest over highest\nquintile)",
            fontsize=10, va="top", linespacing=1.45)
    ax.set_xticks(RANK, QUINTILES)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, q.max() * 1.18)
    ax.set_ylabel("births per woman")
    ax.set_xlabel("household wealth quintile")
    frame(fig, f"Total fertility rate by household wealth quintile, {country}, "
          f"DHS {int(r['year'])}",
          "Bars are the published quintile rates. Each quintile is placed at the midpoint "
          "of its wealth rank (0.1, 0.3, ..., 0.9); the\ngradient is the slope of the "
          "fitted line on a log scale. A negative gradient means the rate falls as "
          "wealth rises.", DHS, top=0.9, bottom=0.22)
    fig.subplots_adjust(right=0.76)
    save(fig, "what_is_a_gradient.png")


def by_wealth(latest):
    """Every country's latest survey: fertility and infant mortality by quintile."""
    panels = [("TFR", "Total fertility rate (births per woman)"),
              ("IMR", "Infant mortality rate (deaths per 1,000 live births)")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5))
    for ax, (ind, ttl) in zip(axes, panels):
        l = latest[latest["indicator"] == ind]
        Q = l[[f"q{i}" for i in range(1, 6)]].values
        grid(ax)
        for row in Q:
            ax.plot(RANK, row, color=CONTEXT, alpha=0.35, lw=1)
        med = np.median(Q, axis=0)
        ax.plot(RANK, med, color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
        ax.annotate(f"median,\n{len(l)} countries", (RANK[-1], med[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9)
        ax.set_xticks(RANK, QUINTILES)
        ax.set_xlim(0.05, 1.12)
        ax.set_ylim(0, None)
        ax.set_xlabel("household wealth quintile")
        ax.set_title(ttl)
    frame(fig, "Total fertility rate and infant mortality rate by household wealth quintile, "
          "latest DHS survey",
          "Grey lines are individual countries (latest survey with a complete quintile "
          "breakdown); the blue line is the median across countries.", DHS)
    save(fig, "by_wealth.png")


def by_region(latest):
    """Low/high ratios by region."""
    tfr = latest[latest["indicator"] == "TFR"]
    regions = tfr.groupby("region")["ratio"].median().sort_values().index.tolist()
    rng = np.random.default_rng(7)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5), sharey=True)
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"],
                            ["Total fertility rate", "Infant mortality rate"]):
        l = latest[latest["indicator"] == ind]
        for yi, rgn in enumerate(regions):
            sub = l[l["region"] == rgn]
            if not len(sub):
                continue
            ax.axhline(yi, color=GRID, lw=0.8, zorder=0)
            q25, q50, q75 = sub["ratio"].quantile([0.25, 0.5, 0.75])
            ax.plot([q25, q75], [yi, yi], color=HI, lw=6, alpha=0.25, zorder=1)
            ax.scatter(sub["ratio"], yi + rng.uniform(-0.17, 0.17, len(sub)), s=22,
                       color=CONTEXT, alpha=0.7, edgecolors="none", zorder=2)
            ax.plot([q50], [yi], marker="|", ms=18, mew=2.5, color=HI, zorder=3)
            ax.text(1.01, yi, f"n={len(sub)}", transform=ax.get_yaxis_transform(),
                    va="center", fontsize=8.5, color=MUTED)
        ratio_axis(ax, "x", 0.5, 8)
        ax.set_title(ttl)
        ax.set_xlabel("low/high ratio (log scale)")
    short = {"North Africa/West Asia/Europe": "N. Africa, W. Asia & Europe"}
    axes[0].set_yticks(range(len(regions)), [short.get(r, r) for r in regions])
    axes[0].tick_params(axis="y", length=0)
    frame(fig, "Low/high ratio of the total fertility rate and the infant mortality rate, "
          "by DHS region",
          "Low/high ratio = rate in the lowest wealth quintile divided by the rate in the "
          "highest. Dots are countries (latest survey); the tick is\nthe regional median "
          "and the band the interquartile range; n = number of countries. Regions follow "
          "the DHS Program's classification.", DHS)
    fig.subplots_adjust(left=0.235, right=0.95, wspace=0.14)
    save(fig, "by_region.png")


def over_time(lib):
    """Every survey since 1990, by fieldwork year."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9), sharey=True)
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"],
                            ["Total fertility rate", "Infant mortality rate"]):
        l = lib[lib["indicator"] == ind]
        grid(ax)
        ax.scatter(l["year"], l["ratio"], s=14, color=CONTEXT, alpha=0.5, edgecolors="none")
        yrs = sorted(l["year"].unique())
        roll = [l[(l["year"] >= y - 4) & (l["year"] <= y + 4)]["ratio"].median() for y in yrs]
        ax.plot(yrs, roll, color=HI, lw=2.5, zorder=3)
        ratio_axis(ax, "y", 0.3, 10)
        ax.set_title(ttl)
        ax.set_xlabel("survey year")
    axes[0].set_ylabel("low/high ratio (log scale)")
    frame(fig, "Low/high ratio of the total fertility rate and the infant mortality rate, "
          f"by survey year, {int(lib['year'].min())}–{int(lib['year'].max())}",
          "Dots are surveys with a complete wealth-quintile breakdown. The line is the "
          "median over a nine-year centered window.", DHS)
    save(fig, "over_time.png")


def fertility_by_age(latest):
    """Low/high ratio by mother's age, and the age offsets the library publishes."""
    tilts, offs = DATA / "fertility_age_tilts.csv", DATA / "fertility_age_offsets.csv"
    if not (tilts.exists() and offs.exists()):
        return
    t = pd.read_csv(tilts).sort_values(["country", "year", "survey", "age_lo"])
    o = pd.read_csv(offs).sort_values("age_lo")
    t = t[t["survey"].isin(t.groupby("country")["survey"].last())].copy()
    # ratios on the surveys behind the offsets: every quintile positive at that age
    t["ratio"] = (t["q1"] / t["q5"]).where(t["slope"].notna())
    x = np.arange(len(o))
    labels = [f"{a}–{b}" for a, b in zip(o["age_lo"], o["age_hi"])]
    by_age = t.groupby("age_lo")["ratio"]
    med, q25, q75 = by_age.median(), by_age.quantile(0.25), by_age.quantile(0.75)
    tfr_ratio = latest.loc[latest["indicator"] == "TFR", "ratio"].median()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5), gridspec_kw={"wspace": 0.25})
    for ax in (a1, a2):
        grid(ax)
        ax.set_xticks(x, labels)
        ax.set_xlabel("age of mother")
    ratio_axis(a1, "y", 0.8, 8)
    a1.fill_between(x, q25.values, q75.values, color=HI, alpha=0.12, lw=0)
    a1.axhline(tfr_ratio, color=CONTEXT, lw=1.5, zorder=1)
    a1.text(x[-1] + 0.3, tfr_ratio * 0.96, f"TFR: {tfr_ratio:.1f}", ha="right", va="top",
            color=MUTED, fontsize=8.5)
    a1.plot(x, med.values, color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
    for i, v in enumerate(med.values):
        a1.annotate(f"{v:.1f}", (i, v), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=9)
    a1.set_ylabel("low/high ratio (log scale)")
    a1.set_title("Low/high ratio of age-specific fertility rates")
    for _, g in t.groupby("survey"):
        a2.plot(x, g["offset"].values, color=CONTEXT, alpha=0.3, lw=1)
    a2.fill_between(x, o["iqr_lo"], o["iqr_hi"], color=HI, alpha=0.12, lw=0)
    a2.axhline(0, color=INK, lw=1, alpha=0.55)
    a2.plot(x, o["offset"], color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
    for i, v in enumerate(o["offset"]):
        a2.annotate(num(v, "+.2f"), (i, v), xytext=(0, 9 if v >= 0 else -16),
                    textcoords="offset points", ha="center", fontsize=9)
    a2.set_ylim(min(-2.6, t["offset"].min() - 0.2), max(1.6, t["offset"].max() + 0.2))
    a2.set_ylabel("age gradient minus TFR gradient")
    a2.set_title("Age offsets (median across countries)")
    frame(fig, "Wealth differentials in fertility by age of mother, latest DHS survey",
          "Left: median across countries of the low/high ratio of each age-specific "
          "fertility rate (band: interquartile range); grey line: median low/high ratio of "
          "the TFR.\nRight: grey lines are countries; blue is the median offset (band: "
          f"interquartile range). Both panels: ages 45–49 rest on {int(o['countries'].iloc[-1])} "
          "countries; in the others a quintile reports no births.",
          "Source: DHS Program indicator API, age-specific fertility rates by wealth "
          "quintile; author's calculations.")
    save(fig, "fertility_by_age.png")


def adult_mortality_vs_income():
    """Adult-mortality gradient against GNI per capita, with the fitted rule."""
    pts_p, rule_p = DATA / "general_gradient_points.csv", DATA / "general_gradient.csv"
    if not (pts_p.exists() and rule_p.exists()):
        return
    pts = pd.read_csv(pts_p).dropna(subset=["gni"])
    rule = pd.read_csv(rule_p).set_index(["component", "key"])["value"]
    a, b = rule[("income_rule", "intercept")], rule[("income_rule", "slope_ln_gni")]
    sd, r = rule[("income_rule", "residual_sd")], rule[("income_rule", "r")]
    fig, ax = plt.subplots(figsize=(10, 5.4))
    grid(ax, "both")
    g = np.geomspace(120, 11000, 100)
    ax.fill_between(g, a + b * np.log(g) - sd, a + b * np.log(g) + sd, color=HI, alpha=0.12,
                    lw=0)
    ax.plot(g, a + b * np.log(g), color=HI, lw=2.5, zorder=2)
    ax.axhline(0, color=INK, lw=1, alpha=0.55, zorder=1)
    ax.scatter(pts["gni"], pts["tilt_45q15"], s=55, color=INK, edgecolors=SURF, linewidths=2,
               zorder=3)
    # every census labelled; adjustText places the labels clear of points and each other
    za = pts[(pts["country"] == "South Africa") & (pts["year"] > 2001)]
    rest = pts.drop(za.index)
    texts = [ax.text(p["gni"], p["tilt_45q15"], f"{p['country']} {int(p['year'])}", fontsize=8.5)
             for _, p in rest.iterrows()]
    if len(za):  # two adjacent censuses share one label, placed between them
        texts.append(ax.text(np.exp(np.log(za["gni"]).mean()), za["tilt_45q15"].mean() + 0.05,
                             "South Africa " + " and ".join(str(int(y)) for y in za["year"]),
                             fontsize=8.5, ha="center"))
    ax.set_xscale("log")
    ax.set_xlim(120, 11000)
    ax.xaxis.set_major_locator(FixedLocator([200, 500, 1000, 2000, 5000, 10000]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_ticklabels(["200", "500", "1,000", "2,000", "5,000", "10,000"])
    ax.set_xlabel("GNI per capita in the census year (current US$, log scale)")
    ax.set_ylabel("wealth gradient in 45q15")
    texts.append(ax.text(2600, a + b * np.log(2600) + 0.08,
                         f"fitted: {num(a, '.3f')} − {abs(b):.3f} × ln(GNI)", fontsize=9.5))
    adjust_text(texts, x=pts["gni"].values, y=pts["tilt_45q15"].values, ax=ax,
                expand=(1.3, 1.6), force_text=(0.4, 0.6), force_static=(0.6, 0.8),
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    frame(fig, "Wealth gradient in adult mortality (45q15) and GNI per capita, by census",
          "Each dot is one census (South Sudan 2008 is omitted: no GNI estimate). 45q15 is "
          "the probability of dying between ages 15 and 60. "
          f"Line: least-squares\nfit (r = {num(r)}); band: ±1 residual standard deviation. "
          "A negative gradient means mortality falls as household wealth rises; zero means "
          "no difference.", CENSUS)
    save(fig, "adult_mortality_vs_income.png")


def adult_mortality_by_age():
    """Gradient at ages 15-29 against the oldest age band measured, by census."""
    p, pts_p = DATA / "adult_mortality_gradients.csv", DATA / "general_gradient_points.csv"
    if not (p.exists() and pts_p.exists()):
        return
    amr = pd.read_csv(p)
    mx = amr[amr["measure"] == "mx"]
    gni = pd.read_csv(pts_p).set_index(["country", "year"])["gni"]
    rows = []
    for (c, y), g in mx.groupby(["country", "year"]):
        # both sexes where published, else the mean of men and women in each band
        g = (g[g["sex"] == "all"] if (g["sex"] == "all").any() else
             g[g["sex"].isin(["male", "female"])]).groupby(["age_lo", "age_hi"], as_index=False)[
            "slope"].mean().sort_values("age_lo")
        if len(g) < 2:
            continue
        rows.append(dict(label=f"{c} {y}", gni=gni.get((c, y), np.nan),
                         young=g["slope"].iloc[0], old=g["slope"].iloc[-1],
                         band=f"{int(g['age_lo'].iloc[-1])}–{int(g['age_hi'].iloc[-1])}"))
    d = pd.DataFrame(rows).sort_values("gni", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(10, 6))
    grid(ax, "x")
    ax.axvline(0, color=INK, lw=1, alpha=0.55, zorder=1)
    for i, r in d.iterrows():
        ax.annotate("", (r["old"], i), (r["young"], i),
                    arrowprops=dict(arrowstyle="->", color=CONTEXT, lw=1.5,
                                    shrinkA=6, shrinkB=6))
        if r["band"] != "60–74":
            ax.text(r["old"] + 0.07, i, r["band"], fontsize=8.5, color=MUTED, ha="left",
                    va="center")
    ax.scatter(d["young"], d.index, s=70, color=HI, edgecolors=SURF, linewidths=2,
               zorder=3, label="ages 15–29")
    ax.scatter(d["old"], d.index, s=70, color=INK, edgecolors=SURF, linewidths=2,
               zorder=3, label="ages 60–74 (or oldest band measured)")
    ax.set_yticks(d.index, [f"{r.label} (GNI {r.gni:,.0f})" for r in d.itertuples()])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(d) - 0.4, -0.7)
    ax.set_xlabel("wealth gradient in the age-specific death rate")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, frameon=False, fontsize=9.5)
    frame(fig, "Wealth gradient in adult mortality at ages 15–29 and at older ages, by census",
          "Censuses with estimates for at least two age bands; both sexes (Brazil, published "
          "by sex only: mean of men and women); ordered by GNI per capita\n(current US$). "
          "The oldest band is 60–74 except where "
          "marked (too few deaths above 60). Positive values: death rates rise with "
          "household wealth.", CENSUS, top=0.85)
    fig.subplots_adjust(left=0.29)
    save(fig, "adult_mortality_by_age.png")


def main():
    lib = pd.read_csv(DATA / "gradient_library.csv")
    latest = pd.read_csv(DATA / "gradient_library_latest.csv").merge(
        pd.read_csv(DATA / "dhs_regions.csv"), on="country", how="left")
    FIG.mkdir(exist_ok=True)
    what_is_a_gradient(latest)
    by_wealth(latest)
    by_region(latest)
    over_time(lib)
    fertility_by_age(latest)
    adult_mortality_vs_income()
    adult_mortality_by_age()
    print(f"wrote {len(list(FIG.glob('*.png')))} figures to figures/")


if __name__ == "__main__":
    main()
