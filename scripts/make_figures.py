# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib"]
# ///
"""Regenerate the library's figures from the CSVs in ../data/.

    uv run scripts/make_figures.py

Every figure follows one standard, so a reader with no context can follow it:
a title that states the finding, a subtitle that says what is plotted, plain
axis labels, one accent colour for the series the story is about and gray for
context, and a source line. Where a gradient is shown as a number it is the
poorest-to-richest ratio (the fitted rate of the poorest fifth over the
richest fifth, exp(-0.8 x tilt)), on a log scale, because a ratio needs no explanation and a
tilt does.
"""

from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
INK, MUTED, GRID, SURF, HI = "#1a1a19", "#6b6b68", "#e8e8e6", "#fcfcfb", "#2a78d6"
CONTEXT = "#9c9b97"  # gray for the lines and dots that are context, not the story
QUINTILES = ["Poorest\nfifth", "Second", "Middle", "Fourth", "Richest\nfifth"]
RANK = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
RATIO_TICKS = [0.5, 0.75, 1, 1.5, 2, 3, 4, 6, 8]
DHS = "Source: DHS Program API, wealth-quintile breakdowns; latest survey per country."

plt.rcParams.update({
    "font.size": 10.5, "text.color": INK, "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
    "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
    "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.titlesize": 11, "axes.titlelocation": "left", "axes.titlepad": 8,
    "lines.solid_capstyle": "round", "lines.solid_joinstyle": "round",
})


def num(x, fmt=".2f"):
    """A number with a true minus sign."""
    return format(x, fmt).replace("-", "−")


def ratio(tilt):
    """The poorest-to-richest ratio implied by a tilt: fitted poorest fifth over richest fifth.

    The fifths' midpoints sit at ranks 0.1 and 0.9, 0.8 apart, so the ratio is exp(-0.8 x tilt).
    """
    return np.exp(-0.8 * np.asarray(tilt, dtype=float))


def frame(fig, title, subtitle, source, top=0.77):
    """Title (the finding), subtitle (what is plotted) and source line."""
    fig.text(0.01, 0.985, title, fontsize=14, fontweight="bold", va="top")
    fig.text(0.01, 0.925, subtitle, fontsize=10, color=MUTED, va="top", linespacing=1.35)
    fig.text(0.01, 0.01, source, fontsize=8, color=MUTED, va="bottom")
    fig.subplots_adjust(top=top, bottom=0.17, left=0.08, right=0.98)


def grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def ratio_axis(ax, axis="y", lo=0.6, hi=6):
    """Log-scaled poorest-to-richest ratio axis, plain tick labels, a no-difference line at 1."""
    (ax.set_yscale if axis == "y" else ax.set_xscale)("log")
    (ax.set_ylim if axis == "y" else ax.set_xlim)(lo, hi)
    a = ax.yaxis if axis == "y" else ax.xaxis
    ticks = [t for t in RATIO_TICKS if lo <= t <= hi]
    a.set_major_locator(FixedLocator(ticks))
    a.set_minor_locator(NullLocator())
    a.set_ticklabels([f"{t:g}" for t in ticks])
    (ax.axhline if axis == "y" else ax.axvline)(1, color=INK, lw=1, alpha=0.55, zorder=1)


def save(fig, name):
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)


def what_is_a_gradient(latest, country="Philippines"):
    """The concept: five wealth groups, one fitted curve, one number."""
    r = latest[(latest["indicator"] == "TFR") & (latest["country"] == country)].iloc[0]
    q = np.array([r[f"q{i}"] for i in range(1, 6)])
    b, a = np.polyfit(RANK, np.log(q), 1)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    grid(ax)
    ax.bar(RANK, q, width=0.05, color=HI, zorder=2)
    for x, v in zip(RANK, q):
        ax.annotate(f"{v:g}", (x, v), xytext=(0, 5), textcoords="offset points",
                    ha="center", fontsize=10, zorder=5,
                    bbox=dict(boxstyle="square,pad=0.15", fc=SURF, ec="none"))
    xs = np.linspace(0, 1, 100)
    ax.plot(xs, np.exp(a + b * xs), color=INK, lw=2, zorder=3)
    fit = np.exp(a + b * RANK)
    step = 100 * (1 - np.exp(b * 0.2))           # the curve's fall per fifth
    drops = 100 * (1 - q[1:] / q[:-1])           # the bars' actual falls
    # the two curve values the ratio is read from, drawn so the reader can check it
    # poorest: above-right of the point, clear of the falling curve; richest: left, between bars
    for i, text, off, ha, va in ((0, f"{fit[0]:.1f} on the curve", (18, 4), "left", "bottom"),
                                 (4, f"{fit[4]:.1f} on\nthe curve", (-18, -4), "right", "top")):
        ax.plot(RANK[i], fit[i], "o", ms=8, color=INK, mec=SURF, mew=2, zorder=4)
        ax.annotate(text, (RANK[i], fit[i]), xytext=off, textcoords="offset points", ha=ha,
                    va=va, fontsize=9, color=INK, zorder=5)
    ax.annotate(f"fitted curve: falls {step:.0f}% at every step up a fifth.\n"
                "The bars fall unevenly ("
                + ", ".join(f"{d:.0f}%" for d in drops)
                + ");\nthe curve is the steady fall that fits them best.",
                (0.62, np.exp(a + b * 0.62)), xytext=(0.5, q.max() * 1.02),
                fontsize=9.5, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.text(1.02, q.max() * 0.78,
            f"The tilt is the slope of this\ncurve on a log scale: {num(b)}\n\n"
            f"Poorest-to-richest ratio,\nread off the curve:\n"
            f"{fit[0]:.1f} ÷ {fit[4]:.1f} = {fit[0] / fit[4]:.1f}\n"
            f"(the bars give {q[0]:g} ÷ {q[4]:g} = {q[0] / q[4]:.1f})\n\n"
            "A negative tilt means the\npoor have the higher rate.",
            fontsize=10, va="top", linespacing=1.4)
    ax.set_xticks(RANK, QUINTILES)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, q.max() * 1.18)
    ax.set_ylabel("births per woman")
    ax.set_xlabel("households ranked by wealth (assets), split into fifths")
    frame(fig, "A wealth gradient: how a rate changes from poor to rich households",
          f"Births per woman by household wealth, {country} (DHS {int(r['year'])}). The "
          "library summarizes each such pattern\nwith one number, the tilt, so it can "
          "be compared across countries and passed to OG-Core.",
          "Source: DHS Program API. Tilt = slope of ln(rate) on wealth rank 0–1, "
          "fitted on the five group midpoints.", top=0.8)
    fig.subplots_adjust(right=0.75)
    save(fig, "what_is_a_gradient.png")


def by_wealth(latest):
    """Every country's latest survey: fertility and infant mortality by wealth fifth."""
    panels = [("TFR", "Births per woman"), ("IMR", "Infant deaths per 1,000 live births")]
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2))
    counts = []
    for ax, (ind, ttl) in zip(axes, panels):
        l = latest[latest["indicator"] == ind]
        Q = l[[f"q{i}" for i in range(1, 6)]].values
        grid(ax)
        for row in Q:
            ax.plot(RANK, row, color=CONTEXT, alpha=0.35, lw=1)
        med = np.median(Q, axis=0)
        ax.plot(RANK, med, color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
        ax.annotate(f"median of\n{len(l)} countries", (RANK[-1], med[-1]), xytext=(8, 0),
                    textcoords="offset points", va="center", fontsize=9.5)
        ax.set_xticks(RANK, QUINTILES)
        ax.set_xlim(0.05, 1.08)
        ax.set_ylim(0, None)
        ax.set_title(ttl)
        counts.append(((Q[:, 0] > Q[:, 4]).sum(), len(l)))
    frame(fig, "Poorer households have more births and more infant deaths, almost everywhere",
          "Each gray line is one country's latest DHS survey; blue is the median across "
          f"countries. The poorest fifth is higher than\nthe richest in {counts[0][0]} of "
          f"{counts[0][1]} countries for births and {counts[1][0]} of {counts[1][1]} for "
          "infant deaths.", DHS)
    save(fig, "by_wealth.png")


def by_region(latest):
    """How steep the gradient is, region by region."""
    tfr = latest[latest["indicator"] == "TFR"]
    regions = tfr.groupby("region")["slope"].median().sort_values(ascending=False).index.tolist()
    rng = np.random.default_rng(7)
    fig, axes = plt.subplots(1, 2, figsize=(11, 5.2), sharey=True)
    steepest = {}
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"], ["Births", "Infant deaths"]):
        l = latest[latest["indicator"] == ind].copy()
        l["r"] = ratio(l["slope"])
        steepest[ind] = l.groupby("region")["r"].median().idxmax()
        for yi, rgn in enumerate(regions):
            sub = l[l["region"] == rgn]
            if not len(sub):
                continue
            ax.axhline(yi, color=GRID, lw=0.8, zorder=0)
            q25, q50, q75 = sub["r"].quantile([0.25, 0.5, 0.75])
            ax.plot([q25, q75], [yi, yi], color=HI, lw=6, alpha=0.25, zorder=1)
            ax.scatter(sub["r"], yi + rng.uniform(-0.17, 0.17, len(sub)), s=22, color=CONTEXT,
                       alpha=0.7, edgecolors="none", zorder=2)
            ax.plot([q50], [yi], marker="|", ms=18, mew=2.5, color=HI, zorder=3)
            ax.text(1.01, yi, str(len(sub)), transform=ax.get_yaxis_transform(), va="center",
                    fontsize=9, color=MUTED)
        ratio_axis(ax, "x", 0.5, 8)
        ax.set_title(ttl)
        ax.set_xlabel("poorest-to-richest ratio (log scale)")
    short = {"North Africa/West Asia/Europe": "N. Africa, W. Asia & Europe"}
    axes[0].set_yticks(range(len(regions)), [short.get(r, r) for r in regions])
    axes[0].tick_params(axis="y", length=0)
    same = steepest["TFR"] == steepest["IMR"]
    title = (f"Gradients are steepest in {steepest['TFR']}" if same else
             f"Birth gradients are steepest in {steepest['TFR']}, infant-death gradients "
             f"in {steepest['IMR']}")
    frame(fig, title,
          "Each dot is one country's latest survey; the number at the right of each row counts "
          "them. The blue tick is the region's\nmedian and the band its middle half. Above 1 "
          "the poor have the higher rate.", DHS)
    fig.subplots_adjust(left=0.235, right=0.96, wspace=0.12)
    save(fig, "by_region.png")


def over_time(lib):
    """Every survey since 1990, by fieldwork year."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.9), sharey=True)
    notes = []
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"], ["Births", "Infant deaths"]):
        l = lib[lib["indicator"] == ind]
        grid(ax)
        ax.scatter(l["year"], ratio(l["slope"]), s=14, color=CONTEXT, alpha=0.5,
                   edgecolors="none")
        yrs = sorted(l["year"].unique())
        roll = [ratio(l[(l["year"] >= y - 4) & (l["year"] <= y + 4)]["slope"].median())
                for y in yrs]
        ax.plot(yrs, roll, color=HI, lw=2.5, zorder=3)
        ratio_axis(ax, "y", 0.5, 8)
        ax.set_title(ttl)
        ax.set_xlabel("survey year")
        early = ratio(l[l["year"] < 2000]["slope"].median())
        late = ratio(l[l["year"] >= 2015]["slope"].median())
        notes.append(f"{ttl.lower()} {early:.1f} in the 1990s and {late:.1f} since 2015")
    axes[0].set_ylabel("poorest-to-richest ratio (log scale)")
    frame(fig, "The typical gradient has changed little since 1990",
          "Each dot is one survey; the line is the median over a nine-year window. Median "
          f"poorest-to-richest ratio: {notes[0]};\n{notes[1]}. A single country can still change a lot "
          "(Brazil's child-mortality gradient halved 1991–2010).",
          "Source: DHS Program API, every survey with a complete wealth-quintile breakdown.")
    save(fig, "over_time.png")


def fertility_by_age(latest):
    """The fertility gradient by mother's age, and the offsets the library publishes."""
    tilts, offs = DATA / "fertility_age_tilts.csv", DATA / "fertility_age_offsets.csv"
    if not (tilts.exists() and offs.exists()):
        return
    t = pd.read_csv(tilts).sort_values(["country", "year", "survey", "age_lo"])
    o = pd.read_csv(offs).sort_values("age_lo")
    t = t[t["survey"].isin(t.groupby("country")["survey"].last())]
    x = np.arange(len(o))
    labels = [f"{a}–{b}" for a, b in zip(o["age_lo"], o["age_hi"])]
    tfr = latest.loc[latest["indicator"] == "TFR", "slope"].median()
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 5.2), gridspec_kw={"wspace": 0.25})
    for ax in (a1, a2):
        grid(ax)
        ax.set_xticks(x, labels)
        ax.set_xlabel("mother's age")
    # left: what it means
    rr = ratio(tfr + o["offset"].values)
    ratio_axis(a1, "y", 0.8, 6)
    a1.axhline(ratio(tfr), color=CONTEXT, lw=1.5, zorder=1)
    a1.text(x[-1] + 0.3, ratio(tfr) * 0.97, f"one tilt for all ages: {ratio(tfr):.1f}",
            ha="right", va="top", color=MUTED, fontsize=8.5)
    a1.plot(x, rr, color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
    for i, v in enumerate(rr):
        a1.annotate(f"{v:.1f}", (i, v), xytext=(0, 9), textcoords="offset points",
                    ha="center", fontsize=9)
    a1.set_ylabel("poorest-to-richest ratio, birth rate (log scale)")
    a1.set_title("The gap by age, for a typical country")
    # right: what the file holds
    for _, g in t.groupby("survey"):
        a2.plot(x, g["offset"].values, color=CONTEXT, alpha=0.3, lw=1)
    a2.fill_between(x, o["iqr_lo"], o["iqr_hi"], color=HI, alpha=0.12, lw=0)
    a2.axhline(0, color=INK, lw=1, alpha=0.55)
    a2.plot(x, o["offset"], color=HI, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
    for i, v in enumerate(o["offset"]):
        a2.annotate(f"{v:+.2f}".replace("-", "−"), (i, v), xytext=(0, 9 if v >= 0 else -16),
                    textcoords="offset points", ha="center", fontsize=9)
    a2.set_ylim(min(-2.6, t["offset"].min() - 0.2), max(1.6, t["offset"].max() + 0.2))
    a2.set_ylabel("offset added to the country's fertility tilt")
    a2.set_title("The age offsets the library publishes")
    frame(fig, "Poorer women start having children earlier and continue later: the gap "
          "is widest at both ends",
          f"Left: a typical country (the median fertility tilt, {tfr:.2f}, plus the median "
          "offsets). Right: each gray line is one country's\nlatest survey with fertility by "
          "age; blue is the median across countries (the published offset), the band its "
          "middle half. "
          f"Ages 45–49 rest on {int(o['countries'].iloc[-1])} countries.".replace("-0", "−0"),
          "Source: DHS Program API, age-specific fertility by wealth quintile. "
          "Offset = tilt at that age − the survey's fertility tilt.")
    save(fig, "fertility_by_age.png")


def adult_mortality_vs_income():
    """The general gradient: adult-mortality tilt against national income."""
    pts_p, rule_p = DATA / "general_gradient_points.csv", DATA / "general_gradient.csv"
    if not (pts_p.exists() and rule_p.exists()):
        return
    pts = pd.read_csv(pts_p).dropna(subset=["gni"])
    rule = pd.read_csv(rule_p).set_index(["component", "key"])["value"]
    a, b = rule[("income_rule", "intercept")], rule[("income_rule", "slope_ln_gni")]
    sd, r = rule[("income_rule", "residual_sd")], rule[("income_rule", "r")]
    fig, ax = plt.subplots(figsize=(10, 5.6))
    grid(ax, "both")
    g = np.geomspace(120, 11000, 100)
    ax.fill_between(g, ratio(a + b * np.log(g) + sd), ratio(a + b * np.log(g) - sd),
                    color=HI, alpha=0.12, lw=0)
    ax.plot(g, ratio(a + b * np.log(g)), color=HI, lw=2.5, zorder=2)
    ax.scatter(pts["gni"], ratio(pts["tilt_45q15"]), s=55, color=INK, edgecolors=SURF,
               linewidths=2, zorder=3)
    show = {"Ethiopia 2007": (-9, -2), "Uganda 2002": (8, -3), "Malawi 1998": (6, 4),
            "Malawi 2008": (6, -12), "Zambia 2010": (6, -4), "Benin 2013": (-8, 6),
            "South Africa 2001": (-8, 8),
            "Brazil 2010": (-8, 8)}
    for _, p in pts.iterrows():
        key = f"{p['country']} {int(p['year'])}"
        if key in show:
            dx, dy = show[key]
            ax.annotate(key, (p["gni"], ratio(p["tilt_45q15"])), xytext=(dx, dy),
                        textcoords="offset points", fontsize=9, color=INK, va="center",
                        ha="left" if dx > 0 else "right")
    za = pts[(pts["country"] == "South Africa") & (pts["year"] > 2001)]
    if len(za):  # two censuses side by side: one label under both
        ax.annotate("South Africa " + " and ".join(str(int(y)) for y in za["year"]),
                    (np.exp(np.log(za["gni"]).mean()), ratio(za["tilt_45q15"]).min()),
                    xytext=(-30, -16), textcoords="offset points", fontsize=9, ha="center")
    ax.set_xscale("log")
    ax.set_xlim(120, 11000)
    ax.xaxis.set_major_locator(FixedLocator([200, 500, 1000, 2000, 5000, 10000]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_ticklabels(["$200", "$500", "$1,000", "$2,000", "$5,000", "$10,000"])
    ratio_axis(ax, "y", 0.8, 2.6)
    ax.set_xlabel("national income per person in the census year (GNI, current US$, log scale)")
    ax.set_ylabel("poorest-to-richest ratio, adult death risk (log scale)")
    ax.text(2200, ratio(a + b * np.log(2200)) * 0.95, "general gradient\n(fallback rule)",
            color=INK, fontsize=9.5, ha="center", va="top")
    frame(fig, "Adult deaths are more concentrated among the poor in richer countries",
          "Each dot is one census (risk of dying between 15 and 60). The blue line is the rule "
          "the library uses for countries with no\nmeasurement, fitted to these dots "
          f"(r = {num(r)}); the band is ±1 standard deviation of the dots around it.\n"
          "Below 1 the richer households report more deaths.",
          "Source: IPUMS International and IBGE census microdata (household deaths "
          "modules); World Bank GNI per capita.")
    save(fig, "adult_mortality_vs_income.png")


def adult_mortality_by_age():
    """Youngest against oldest measured age band, census by census."""
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
    for i, r in d.iterrows():
        ax.annotate("", (ratio(r["old"]), i), (ratio(r["young"]), i),
                    arrowprops=dict(arrowstyle="->", color=CONTEXT, lw=1.5,
                                    shrinkA=6, shrinkB=6))
        if r["band"] != "60–74":
            ax.text(ratio(r["old"]) / 1.04, i, r["band"], fontsize=8.5, color=MUTED,
                    ha="right", va="center")
    ax.scatter(ratio(d["young"]), d.index, s=70, color=HI, edgecolors=SURF, linewidths=2,
               zorder=3, label="ages 15–29")
    ax.scatter(ratio(d["old"]), d.index, s=70, color=INK, edgecolors=SURF, linewidths=2,
               zorder=3, label="ages 60–74 (or oldest measured)")
    ax.set_yticks(d.index, [f"{r.label}  (${r.gni:,.0f})" for r in d.itertuples()])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(d) - 0.4, -0.7)
    ratio_axis(ax, "x", 0.5, 4)
    ax.set_xlabel("poorest-to-richest ratio, death rate (log scale)")
    ax.legend(loc="lower right", bbox_to_anchor=(1, 1.0), ncol=2, frameon=False, fontsize=9.5)
    weaker, reversed_ = (d["old"] > d["young"]).sum(), (d["old"] > 0).sum()
    frame(fig, f"Adult-mortality gradients weaken with age in {weaker} of {len(d)} "
          f"censuses, and reverse in {reversed_}",
          "Each row is one census, men and women together (Brazil, published only by sex: "
          "the average of the two). Richest country at the top,\nGNI per person in "
          "brackets. The arrow runs from ages 15–29 to ages 60–74 (45–59 where marked: "
          "too few deaths above 60).\nBelow 1 the richer households report more deaths. "
          "That may be real or an effect of how deaths of elderly relatives get reported;\n"
          "no check separates the two.",
          "Source: IPUMS International and IBGE census microdata (household deaths "
          "modules); World Bank GNI per capita.", top=0.71)
    fig.subplots_adjust(left=0.27)
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
