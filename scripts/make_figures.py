# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "matplotlib", "adjustText"]
# ///
"""Regenerate the library's figures from the CSVs in ../data/.

    uv run scripts/make_figures.py

One message per figure, readable without the text around it (AGENTS.md,
figure standard): a short title stating the finding, one subtitle line naming
the measure and data, short axis labels, a one-line source. The gap between
wealth groups is shown as poorest / richest: the published low/high ratio, or
exp(-0.8 x gradient), the ratio between the poorest and richest fifth read from
the fitted line (quintile midpoints 0.1 and 0.9). Log scale, 1x marked.
Blue = the library's estimates, orange = another source, grey = context.
"""

import textwrap
from pathlib import Path

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from adjustText import adjust_text  # noqa: E402
from matplotlib.ticker import FixedLocator, NullLocator  # noqa: E402
from matplotlib.transforms import Bbox  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA, FIG = ROOT / "data", ROOT / "figures"
INK, MUTED, GRID, SURF = "#1a1a19", "#6b6b68", "#e8e8e6", "#fcfcfb"
BLUE, ORANGE, CONTEXT = "#2a78d6", "#c2611b", "#9c9b97"
RANK = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
FIFTHS = ["Poorest", "2nd", "3rd", "4th", "Richest"]
GAP = "Poorest fifth ÷ richest fifth"
SURVEYS = "DHS Program indicator API; MICS as compiled by the World Bank; Demographic-Gradients."
CENSUS = ("Census microdata (IPUMS International, IBGE, DANE); India NFHS; Bangladesh BMMS; "
          "World Bank GDP per capita (PPP); Demographic-Gradients.")

plt.style.use(Path(__file__).with_name("figures.mplstyle"))


def ratio(slope):
    """Poorest-fifth rate / richest-fifth rate on the fitted line."""
    return np.exp(-0.8 * np.asarray(slope, float))


def ratio_axis(ax, axis, ticks, lo, hi):
    """Log-scaled ratio axis labelled 0.5x, 1x, 2x ..., with a line at 1x."""
    a = ax.xaxis if axis == "x" else ax.yaxis
    (ax.set_xscale if axis == "x" else ax.set_yscale)("log")
    (ax.set_xlim if axis == "x" else ax.set_ylim)(lo, hi)
    a.set_major_locator(FixedLocator([t for t in ticks if lo <= t <= hi]))
    a.set_minor_locator(NullLocator())
    a.set_ticklabels([f"{t:g}×" for t in ticks if lo <= t <= hi])
    (ax.axvline if axis == "x" else ax.axhline)(1, color=INK, lw=1, alpha=0.5, zorder=1)


def grid(ax, axis="y"):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name, title, subtitle, source, note=None):
    """Title and subtitle above the drawn plot, source (and note) below, then save."""
    fig.canvas.draw()
    bb = Bbox.union([a.get_tightbbox(fig.canvas.get_renderer()) for a in fig.axes])
    W, H, dpi = fig.get_figwidth(), fig.get_figheight(), fig.dpi
    x0, top, bot = bb.x0 / (W * dpi), bb.y1 / (H * dpi), bb.y0 / (H * dpi)
    chars = int(max(bb.width / dpi, 7) * 72 / (9 * 0.52))
    sub = textwrap.fill(subtitle, chars)
    fig.text(x0, top + 0.14 / H, sub, fontsize=10.5, color=MUTED, va="bottom", linespacing=1.3)
    fig.text(x0, top + (0.24 + (sub.count("\n") + 1) * 10.5 * 1.3 / 72) / H, title,
             fontsize=14, fontweight="bold", color=INK, va="bottom")
    parts = (["Note: " + note] if note else []) + ["Source: " + source]
    foot = "\n".join(textwrap.fill(p, int(chars * 1.15)) for p in parts)
    fig.text(x0, bot - 0.1 / H, foot.replace("$", r"\$"),  # a literal $, not mathtext
             fontsize=8.5, color=MUTED, va="top", linespacing=1.4)
    fig.savefig(FIG / name, bbox_inches="tight", pad_inches=0.2)
    plt.close(fig)


def the_gap(latest):
    """Every country's latest estimate: poorest / richest for four rates."""
    ages = pd.read_csv(DATA / "fertility_age_tilts.csv")
    teen = ages[ages["age_lo"] == 15].sort_values(["country", "year", "survey"])
    teen = teen.groupby("country").tail(1)
    teen = teen[(teen[["q1", "q5"]] > 0).all(axis=1)]
    amr = pd.read_csv(DATA / "adult_mortality_gradients.csv")
    a45 = amr[(amr["measure"] == "45q15") & (amr["sex"] == "all")].sort_values("year")
    a45 = a45.groupby("country").tail(1)
    rows = [("Births", latest.loc[latest["indicator"] == "TFR", "ratio"].values),
            ("Teen births", (teen["q1"] / teen["q5"]).values),
            ("Infant deaths", latest.loc[latest["indicator"] == "IMR", "ratio"].values),
            ("Adult deaths", a45["ratio"].values)]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    grid(ax, "x")
    rng = np.random.default_rng(3)
    for k, (lab, v) in enumerate(rows):
        ax.scatter(v, k + rng.uniform(-0.17, 0.17, len(v)), s=18, color=BLUE, alpha=0.55,
                   lw=0, zorder=3)
        med = np.median(v)
        ax.plot([med, med], [k - 0.3, k + 0.3], color=INK, lw=2.2, zorder=4)
        ax.text(med, k - 0.34, f"{med:.1f}×", ha="center", va="bottom", fontsize=10,
                fontweight="bold")
        ax.text(1.01, k, f"{len(v)} countries", transform=ax.get_yaxis_transform(),
                va="center", fontsize=9, color=MUTED)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=11)
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(rows) - 0.5, -0.8)
    ratio_axis(ax, "x", [0.5, 1, 2, 3, 5], 0.45, 7)
    ax.set_xlabel(GAP + " (log scale)")
    save(fig, "the_gap.png",
         "Poorer households have more births and more deaths",
         "Rate in the poorest fifth of households ÷ richest fifth. One dot per country, latest "
         "survey or census; bar = median.",
         "DHS; MICS; census and survey household-death records; Demographic-Gradients.")


def what_is_a_gradient(latest, country="Philippines"):
    """One country's five quintile rates, the fitted line and the ratio read from it."""
    r = latest[(latest["indicator"] == "TFR") & (latest["country"] == country)].iloc[0]
    q = np.array([r[f"q{i}"] for i in range(1, 6)])
    b, a = np.polyfit(RANK, np.log(q), 1)
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.bar(RANK, q, width=0.12, color=BLUE, zorder=2)
    for x, v in zip(RANK, q):
        ax.text(x, 0.1, f"{v:g}", ha="center", va="bottom", fontsize=12, color=SURF,
                fontweight="bold", zorder=3)
    xs = np.linspace(0, 1, 100)
    ax.plot(xs, np.exp(a + b * xs), color=INK, lw=2.2, zorder=3)
    ax.set_xticks(RANK, FIFTHS)
    ax.set_xlim(0, 1)
    ax.set_yticks([])
    ax.spines["left"].set_visible(False)
    ax.set_ylim(0, q.max() * 1.15)
    ax.set_xlabel("Household wealth fifth")
    ax.text(1.04, 0.62, f"{ratio(b):.1f}×", transform=ax.transAxes, fontsize=34,
            fontweight="bold", color=BLUE, va="center")
    ax.text(1.04, 0.42, f"poorest ÷ richest,\nread from the line\n(gradient {b:.2f})".replace(
        "-", "−"), transform=ax.transAxes, fontsize=10.5, va="center", linespacing=1.4)
    save(fig, "what_is_a_gradient.png",
         "A wealth gradient summarises the five wealth groups in one number",
         f"Births per woman by household wealth fifth (bars) and the fitted line, {country}, "
         f"{r['source']} {int(r['year'])}.",
         "DHS Program indicator API; Demographic-Gradients.")


def by_region(latest):
    """Poorest / richest by region, latest survey per country."""
    tfr = latest[latest["indicator"] == "TFR"]
    regions = tfr.groupby("region")["ratio"].median().sort_values().index.tolist()
    short = {"North Africa/West Asia/Europe": "N. Africa, W. Asia & Europe"}
    rng = np.random.default_rng(7)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.8), sharey=True)
    top = {}
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"], ["Births", "Infant deaths"]):
        l = latest[latest["indicator"] == ind]
        top[ind] = l.groupby("region")["ratio"].median().idxmax()
        for yi, rgn in enumerate(regions):
            sub = l[l["region"] == rgn]
            if not len(sub):
                continue
            ax.scatter(sub["ratio"], yi + rng.uniform(-0.17, 0.17, len(sub)), s=18,
                       color=BLUE, alpha=0.55, lw=0, zorder=2)
            med = sub["ratio"].median()
            ax.plot([med, med], [yi - 0.3, yi + 0.3], color=INK, lw=2.2, zorder=3)
            ax.text(1.01, yi, f"{len(sub)}", transform=ax.get_yaxis_transform(), va="center",
                    fontsize=8.5, color=MUTED)
        grid(ax, "x")
        ratio_axis(ax, "x", [0.5, 1, 2, 3, 5], 0.45, 6)
        ax.set_title(ttl, fontsize=11.5, fontweight="bold", loc="left")
        ax.set_xlabel(GAP)
    axes[0].set_yticks(range(len(regions)), [short.get(r, r) for r in regions])
    axes[0].tick_params(axis="y", length=0)
    fig.subplots_adjust(wspace=0.18)
    save(fig, "by_region.png",
         f"The gap is widest in {short.get(top['TFR'], top['TFR'])} for births and in "
         f"{short.get(top['IMR'], top['IMR'])} for infant deaths",
         "Rate in the poorest fifth ÷ richest fifth. One dot per country, latest survey; bar = "
         "regional median; numbers = countries.", SURVEYS)


def over_time(lib):
    """Every survey since 1990 by fieldwork year, with a running median."""
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4), sharey=True)
    for ax, ind, ttl in zip(axes, ["TFR", "IMR"], ["Births", "Infant deaths"]):
        l = lib[lib["indicator"] == ind]
        grid(ax)
        ax.scatter(l["year"], l["ratio"], s=12, color=CONTEXT, alpha=0.45, lw=0)
        yrs = sorted(l["year"].unique())
        roll = [l[(l["year"] >= y - 4) & (l["year"] <= y + 4)]["ratio"].median() for y in yrs]
        ax.plot(yrs, roll, color=BLUE, lw=2.5, zorder=3)
        ratio_axis(ax, "y", [0.5, 1, 2, 3, 5], 0.4, 8)
        ax.set_title(ttl, fontsize=11.5, fontweight="bold", loc="left")
        ax.set_xlabel("Survey year")
    axes[0].set_ylabel(GAP)
    fig.subplots_adjust(wspace=0.08)
    save(fig, "over_time.png",
         "The gap in births and infant deaths has changed little since 1990",
         f"Rate in the poorest fifth ÷ richest fifth. Dots: {len(lib[lib['indicator'] == 'TFR'])} "
         f"and {len(lib[lib['indicator'] == 'IMR'])} DHS and MICS surveys, "
         f"{int(lib['year'].min())}–{int(lib['year'].max())}; line: median over nine years.",
         SURVEYS)


def fertility_by_age():
    """Poorest / richest of each age-specific fertility rate, median across countries."""
    p = DATA / "fertility_age_tilts.csv"
    if not p.exists():
        return
    t = pd.read_csv(p).sort_values(["country", "year", "survey", "age_lo"])
    t = t[t["survey"].isin(t.groupby("country")["survey"].last())].copy()
    t["r"] = (t["q1"] / t["q5"]).where(t["slope"].notna())
    by = t.groupby("age_lo")["r"]
    med, q25, q75, n = by.median(), by.quantile(0.25), by.quantile(0.75), by.count()
    x = np.arange(len(med))
    labels = [f"{a}–{a + 4}" for a in med.index]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    grid(ax)
    ax.fill_between(x, q25.values, q75.values, color=BLUE, alpha=0.12, lw=0)
    ax.plot(x, med.values, color=BLUE, lw=2.5, marker="o", ms=7, mec=SURF, mew=2, zorder=3)
    for i, v in enumerate(med.values):
        ax.text(i, v * 1.07, f"{v:.1f}×", ha="center", va="bottom", fontsize=10)
    ax.set_xticks(x, labels)
    ax.set_xlabel("Age of mother")
    ratio_axis(ax, "y", [1, 1.5, 2, 3, 5, 8], 0.9, 9)
    ax.set_ylabel(GAP)
    save(fig, "fertility_by_age.png",
         "The gap in births is largest for the youngest and the oldest mothers",
         "Births by age of mother, poorest fifth ÷ richest fifth. Median across countries (band: "
         f"middle half), latest DHS survey; {int(n.iloc[0])} countries, {int(n.iloc[-1])} at 45–49.",
         "DHS Program indicator API, age-specific fertility rates by wealth quintile; "
         "Demographic-Gradients.",
         note="At 45–49 many surveys record no births in a wealth fifth and are left out.")


def adult_mortality_vs_income():
    """Adult-mortality gap against income per capita, drawn only over the data's range."""
    pts_p, rule_p = DATA / "general_gradient_points.csv", DATA / "general_gradient.csv"
    if not (pts_p.exists() and rule_p.exists()):
        return
    pts = pd.read_csv(pts_p).dropna(subset=["gdp_ppp"])
    rule = pd.read_csv(rule_p).set_index(["component", "key"])["value"]
    a, b = rule[("income_rule", "intercept")], rule[("income_rule", "slope_ln_income")]
    s, n, t95 = (rule[("income_rule", k)] for k in ("residual_sd", "n_observations", "t_95"))
    xbar, sxx = rule[("income_rule", "mean_ln_income")], rule[("income_rule", "sxx_ln_income")]
    lo, hi = pts["gdp_ppp"].min(), pts["gdp_ppp"].max()
    g = np.geomspace(lo, hi, 100)
    pred = a + b * np.log(g)
    pi = t95 * s * np.sqrt(1 + 1 / n + (np.log(g) - xbar) ** 2 / sxx)
    fig, ax = plt.subplots(figsize=(10, 5.4))
    grid(ax)
    ax.fill_between(g, ratio(pred + pi), ratio(pred - pi), color=BLUE, alpha=0.12, lw=0)
    ax.plot(g, ratio(pred), color=BLUE, lw=2.5, zorder=2)
    y = ratio(pts["tilt_45q15"])
    ax.scatter(pts["gdp_ppp"], y, s=40, color=INK, edgecolors=SURF, linewidths=1.5, zorder=3)
    texts = [ax.text(x, v, f"{c} {int(yr)}", fontsize=8.5) for x, v, c, yr in
             zip(pts["gdp_ppp"], y, pts["country"], pts["year"])]
    ax.set_xscale("log")
    ax.set_xlim(lo / 1.15, hi * 1.15)
    ax.xaxis.set_major_locator(FixedLocator([1000, 2000, 5000, 10000, 20000]))
    ax.xaxis.set_minor_locator(NullLocator())
    ax.xaxis.set_ticklabels(["$1,000", "$2,000", "$5,000", "$10,000", "$20,000"])
    ratio_axis(ax, "y", [0.75, 1, 1.5, 2, 3, 4], 0.7, 5)
    ax.set_xlabel("GDP per capita, PPP (log scale)")
    ax.set_ylabel(GAP)
    adjust_text(texts, x=pts["gdp_ppp"].values, y=y, ax=ax, expand=(1.3, 1.8),
                # a fixed iteration count, not a time limit, so the layout reproduces
                iter_lim=2000, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.6))
    save(fig, "adult_mortality_vs_income.png",
         "In richer countries the gap in adult deaths is larger",
         "Deaths between ages 15 and 60, poorest fifth ÷ richest fifth, by census or survey, "
         "against income per capita. Line: fitted; band: 95% range for one country.",
         CENSUS,
         note=f"Drawn only over the incomes observed (${lo:,.0f} to ${hi:,.0f}); the library gives "
              "no value outside them. South Sudan 2008 has no income estimate.")


def adult_mortality_by_age():
    """The gap at ages 15-29 against the oldest age band measured, by census or survey."""
    p, pts_p = DATA / "adult_mortality_gradients.csv", DATA / "general_gradient_points.csv"
    if not (p.exists() and pts_p.exists()):
        return
    amr = pd.read_csv(p)
    mx = amr[amr["measure"] == "mx"]
    gdp = pd.read_csv(pts_p).set_index(["country", "year"])["gdp_ppp"]
    rows = []
    for (c, yr), g in mx.groupby(["country", "year"]):
        # both sexes where published, else the mean of men and women in each band
        g = (g[g["sex"] == "all"] if (g["sex"] == "all").any() else
             g[g["sex"].isin(["male", "female"])]).groupby(["age_lo", "age_hi"], as_index=False)[
            "slope"].mean().sort_values("age_lo")
        if len(g) < 2 or g["age_lo"].iloc[0] != 15:  # needs 15-29 and an older band
            continue
        band = f"{int(g['age_lo'].iloc[-1])}–{int(g['age_hi'].iloc[-1])}"
        rows.append(dict(label=f"{c} {yr}" + ("*" if band != "60–74" else ""), gdp=gdp.get((c, yr), np.nan),
                         young=ratio(g["slope"].iloc[0]), old=ratio(g["slope"].iloc[-1]),
                         band=f"{int(g['age_lo'].iloc[-1])}–{int(g['age_hi'].iloc[-1])}"))
    d = pd.DataFrame(rows).sort_values("gdp", ascending=False).reset_index(drop=True)
    fig, ax = plt.subplots(figsize=(9.5, 5.8))
    grid(ax, "x")
    for i, r in d.iterrows():
        ax.annotate("", (r["old"], i), (r["young"], i),
                    arrowprops=dict(arrowstyle="-|>", color=CONTEXT, lw=1.2, shrinkA=5,
                                    shrinkB=4, mutation_scale=9))
    ax.scatter(d["young"], d.index, s=55, color=BLUE, edgecolors=SURF, linewidths=1.5,
               zorder=3, label="Ages 15–29")
    ax.scatter(d["old"], d.index, s=55, color=INK, edgecolors=SURF, linewidths=1.5, zorder=3,
               label="Ages 60–74")
    ax.set_yticks(d.index, [f"{r.label} (${r.gdp:,.0f})" for r in d.itertuples()])
    ax.tick_params(axis="y", length=0)
    ax.set_ylim(len(d) - 0.4, -0.7)
    ratio_axis(ax, "x", [0.5, 0.75, 1, 1.5, 2, 3, 4], 0.45, 5)
    ax.set_xlabel(GAP + " (log scale)")
    ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, fontsize=9.5,
              borderaxespad=0.2)
    save(fig, "adult_mortality_by_age.png",
         "The gap in adult deaths narrows with age, and reverses in some poorer countries",
         "Death rate, poorest fifth ÷ richest fifth, at ages 15–29 and 60–74, by census or survey, "
         "ordered by GDP per capita (PPP).",
         CENSUS.replace("Bangladesh BMMS; ", ""),
         note="Left of 1×: higher death rates in richer households. *Too few deaths above 60: "
              "ages 45–59 shown.")


def main():
    lib = pd.read_csv(DATA / "gradient_library.csv")
    latest = pd.read_csv(DATA / "gradient_library_latest.csv").merge(
        pd.read_csv(DATA / "dhs_regions.csv"), on="country", how="left")
    FIG.mkdir(exist_ok=True)
    the_gap(latest)
    what_is_a_gradient(latest)
    by_region(latest)
    over_time(lib)
    fertility_by_age()
    adult_mortality_vs_income()
    adult_mortality_by_age()
    print(f"wrote {len(list(FIG.glob('*.png')))} figures to figures/")


if __name__ == "__main__":
    main()
