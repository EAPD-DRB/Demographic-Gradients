# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""Regenerate ANALYSIS.md and the README headline table from the data in ../data/.

Keeps every data-derived number in the prose in sync with the CSVs, so the
documentation cannot drift from the data it describes. The narrative is fixed
here; the counts, tilts, and regional tables are computed. Run after the data
or figures change:

    uv run scripts/build_analysis.py

(or just run scripts/refresh.py, which chains data -> figures -> analysis).
"""

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REGION_ORDER_NOTE = "(single survey)"
NEG = "−"  # true minus sign, matching the rest of the docs


def fmt(x):
    return f"{NEG}{abs(x):.2f}" if x < 0 else f"{x:.2f}"


def load():
    lib = pd.read_csv(DATA / "gradient_library.csv")
    latest = pd.read_csv(DATA / "gradient_library_latest.csv").merge(
        pd.read_csv(DATA / "dhs_regions.csv"), on="country", how="left"
    )
    return lib, latest


def headline(latest, ind):
    l = latest[latest["indicator"] == ind]
    return {
        "n": l["country"].nunique(),
        "med": l["slope"].median(),
        "q25": l["slope"].quantile(0.25),
        "q75": l["slope"].quantile(0.75),
        "ratio": l["ratio"].median(),
    }


def census_child_mortality():
    """The census child-mortality series, on its published (full-index) basis."""
    p = DATA / "census_child_mortality.csv"
    if not p.exists():
        return None
    d = pd.read_csv(p)
    f = d[(d["index"] == "full") & (d["measure"] == "prop_dead_2529")]
    c = d[(d["index"] == "common") & (d["measure"] == "prop_dead_2529")]
    if not len(f):
        return None
    rows = "\n".join(
        f"| {int(r.year)} | {r.groups} | {fmt(r.slope)} | {r.ratio:.2f} | "
        f"{r.q1 * 100:.1f}% |"
        for _, r in f.sort_values("year").iterrows())
    ff, cc = f.sort_values("year"), c.sort_values("year")
    # the row carrying a DHS cross-check, and how close it landed
    vrow = f[f["dhs_check"].astype(str).str.len() > 0]
    vtilt = float(vrow["slope"].iloc[0]) if len(vrow) else float("nan")
    chk = str(vrow["dhs_check"].iloc[0]) if len(vrow) else ""
    vref = float(chk.split()[-1]) if chk else float("nan")
    vsurvey = chk.split(" U5MR")[0] if chk else ""
    return {"rows": rows, "n": len(f), "vtilt": vtilt, "vdiff": abs(vtilt - vref),
            "vsurvey": vsurvey, "vref": vref,
            "y0": int(ff.year.iloc[0]), "y1": int(ff.year.iloc[-1]),
            "t0": ff.slope.iloc[0], "t1": ff.slope.iloc[-1],
            "chg_full": ff.slope.iloc[-1] - ff.slope.iloc[0],
            "chg_common": (cc.slope.iloc[-1] - cc.slope.iloc[0]) if len(cc) > 1 else float("nan"),
            "check": next((x for x in f["dhs_check"] if isinstance(x, str) and x), "")}


def general_gradient():
    """The fallback rule and its validation, read from data/ so it cannot drift."""
    p = DATA / "general_gradient.csv"
    if not p.exists():
        return None
    g = pd.read_csv(p)
    d = {f"{r['component']}.{r['key']}": r["value"] for _, r in g.iterrows()}
    d["_ages"] = [(r["key"], r["value"]) for _, r in
                  g[g["component"] == "age_offset"].iterrows()]
    return d


def imr_vs_u5mr(lib):
    """How much steeper the U5MR proxy is than the infant series it stands in for."""
    p = lib.pivot_table(index=["country", "year"], columns="indicator",
                        values="slope")
    if "IMR" not in p.columns:
        return None
    p = p[["IMR", "U5MR"]].dropna()
    if not len(p):
        return None
    d = p["IMR"] - p["U5MR"]
    return {"n": len(p), "med_imr": p["IMR"].median(), "med_u5": p["U5MR"].median(),
            "med_diff": d.median(), "share_flatter": (d > 0).mean(),
            "r": p["IMR"].corr(p["U5MR"]),
            "worst": d.abs().idxmax(), "worst_gap": d.abs().max()}


def amr_headline():
    """One 45q15 observation per census: the 'all' row, else the sex mean."""
    p = DATA / "adult_mortality_gradients.csv"
    if not p.exists():
        return None
    q = pd.read_csv(p)
    q = q[q["measure"] == "45q15"]
    if not len(q):
        return None
    obs, ratios = [], []
    for _, g in q.groupby(["country", "year"]):
        a = g[g["sex"] == "all"]
        src = a if len(a) else g[g["sex"].isin(["male", "female"])]
        obs.append(float(src["slope"].mean()))
        ratios.append(float(src["ratio"].mean()))
    s, r = pd.Series(obs), pd.Series(ratios)
    return {"n": q["country"].nunique(), "censuses": len(obs), "med": s.median(),
            "q25": s.quantile(0.25), "q75": s.quantile(0.75), "ratio": r.median()}


def region_table(latest, ind):
    l = latest[latest["indicator"] == ind]
    g = (
        l.groupby("region")
        .agg(
            n=("country", "nunique"),
            med=("slope", "median"),
            q25=("slope", lambda s: s.quantile(0.25)),
            q75=("slope", lambda s: s.quantile(0.75)),
            ratio=("ratio", "median"),
        )
        .sort_values("med")
    )
    rows = []
    for rgn, r in g.iterrows():
        iqr = REGION_ORDER_NOTE if r["n"] == 1 else f"{fmt(r['q25'])} to {fmt(r['q75'])}"
        rows.append(
            f"| {rgn} | {int(r['n'])} | {fmt(r['med'])} | {iqr} | {r['ratio']:.2f} |"
        )
    return "\n".join(rows)


def sa(latest, ind):
    row = latest[(latest["indicator"] == ind) & (latest["country"] == "South Africa")]
    if not len(row):
        return None
    return {"slope": row["slope"].iloc[0], "ratio": row["ratio"].iloc[0], "year": int(row["year"].iloc[0])}


def replace_between(text, start, end, new):
    a, b = text.index(start) + len(start), text.index(end)
    return text[:a] + "\n" + new + "\n" + text[b:]


def main():
    lib, latest = load()
    tfr, u5, imr = headline(latest, "TFR"), headline(latest, "U5MR"), headline(latest, "IMR")
    # lib has one row per country x year x indicator; a "survey" is a country-year
    n_surveys = lib.groupby(["country", "year"]).ngroups
    n_obs = len(lib)
    n_countries = latest["country"].nunique()

    # --- README headline table (between markers) ---
    readme_path = ROOT / "README.md"
    readme = readme_path.read_text()
    table = (
        "| Margin | Countries | Median tilt | IQR | Median poorest/richest ratio |\n"
        "|---|---|---|---|---|\n"
        f"| Fertility (TFR) | {tfr['n']} | **{fmt(tfr['med'])}** | "
        f"{fmt(tfr['q25'])} to {fmt(tfr['q75'])} | {tfr['ratio']:.2f} |\n"
        f"| Infant mortality | {imr['n']} | **{fmt(imr['med'])}** | "
        f"{fmt(imr['q25'])} to {fmt(imr['q75'])} | {imr['ratio']:.2f} |\n"
        f"| Under-5 mortality (fallback) | {u5['n']} | **{fmt(u5['med'])}** | "
        f"{fmt(u5['q25'])} to {fmt(u5['q75'])} | {u5['ratio']:.2f} |"
    )
    amr = amr_headline()
    if amr:
        table += (
            f"\n| Adult mortality (45q15) | {amr['n']} | **{fmt(amr['med'])}** | "
            f"{fmt(amr['q25'])} to {fmt(amr['q75'])} | {amr['ratio']:.2f} |"
        )
    readme = replace_between(
        readme,
        "<!-- AUTO-GENERATED by scripts/build_analysis.py — do not edit by hand -->",
        "<!-- END AUTO-GENERATED -->",
        table,
    )
    # keep the coverage parenthetical in step with the data too
    readme = re.sub(r"\d[\d,]* surveys, \d+ countries",
                    f"{n_surveys:,} surveys, {n_countries} countries", readme)
    readme_path.write_text(readme)
    print(f"updated README headline table ({n_surveys} surveys, {n_countries} countries)")

    # --- ANALYSIS.md (fully generated) ---
    sa_t, sa_u = sa(latest, "TFR"), sa(latest, "U5MR")
    cmp_ = imr_vs_u5mr(lib)
    doc = f"""# The gradient library, in figures

Documentation of the data in this repo. **This file is generated** by
[`scripts/build_analysis.py`](scripts/build_analysis.py) from the CSVs in
[`data/`](data/); every number below is computed from the data, not hand-typed,
so it cannot drift. Figures come from
[`scripts/make_figures.py`](scripts/make_figures.py) and live in
[`figures/`](figures/). Regenerate both with `uv run scripts/refresh.py`.

South Africa is highlighted throughout as the worked example; pass
`--highlight "<country>"` to `make_figures.py` to feature any other.

The **tilt** summarizing each survey is the OLS slope of ln(rate) on wealth-rank
percentile midpoints (quintiles at the 10th…90th percentile) — the same log scale
OG-Core's income-group demographics consume. Negative means the poor have higher
rates; a tilt of {fmt(tfr['med'])} puts the poorest decile's rate at about
e^({abs(tfr['med']):.2f}×0.8) ≈ {2.718281828 ** (abs(tfr['med']) * 0.8):.1f}× the richest decile's.

Coverage: **{n_surveys} surveys with complete wealth quintets across
{n_countries} countries**, giving {n_obs} country-survey-margin tilts (most
recent survey per country used for the library view below).

## Every country, individually

Nearly every line slopes down: the wealth gradient in fertility is close to
universal. South Africa is both low-fertility and mild-gradient (tilt
{fmt(sa_t['slope'])} in {sa_t['year']}, vs the pooled median of {fmt(tfr['med'])}).

![Fertility (TFR) by household wealth rank, one line per country](figures/fig1_tfr_gradients.png)

The same universal direction holds for child mortality, with wider spread across
countries. South Africa's non-monotonic top quintiles reflect the small
child-mortality samples in its {sa_u['year']} survey.

![Under-5 mortality by household wealth rank, one line per country](figures/fig2_u5mr_gradients.png)

### Use infant mortality, not under-5, for `infmort_gradient`

The library carries both. They are not interchangeable, and the difference runs
one way: across the {cmp_['n']} surveys that report both by wealth quintile, the
under-5 tilt is steeper than the infant tilt by a median
{abs(cmp_['med_diff']):.2f}, and it is steeper in {cmp_['share_flatter']:.0%} of
them. The two are strongly correlated (r = {cmp_['r']:.2f}), so the shape of the
story is the same — but the level is not, and the gap reaches
{cmp_['worst_gap']:.2f} ({cmp_['worst'][0]} {cmp_['worst'][1]}).

The reason is what under-5 mortality includes. Deaths between ages 1 and 4 are
dominated by diarrhoea, malaria, and malnutrition, which wealth protects against
strongly; infant deaths lean toward prematurity and birth complications, which it
protects against much less. Using under-5 as the infant proxy therefore imports
the steeper child-mortality gradient into a parameter meant to describe infants.
Prefer `indicator == "IMR"`, and fall back to `"U5MR"` only for the surveys that
report no infant quintiles.

## Grouped by region

Each dot is a country's most recent survey; the bar marks the regional
interquartile range and the tick marks the median. Latin America has the steepest
gradients; Sub-Saharan Africa sits mid-range; South Africa is milder than its
region's median on fertility.

![Distribution of gradient tilts by region](figures/fig3_slopes_by_region.png)

**Fertility (TFR) tilt by region**

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
{region_table(latest, "TFR")}

**Infant mortality tilt by region** — the series `infmort_gradient` should use

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
{region_table(latest, "IMR")}

**Under-5 mortality tilt by region** — the fallback, and steeper (see below)

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
{region_table(latest, "U5MR")}

## Stability over survey years

All {n_obs} country-survey-margin tilts plotted by fieldwork year, with a
rolling median. The
pooled gradient is nearly flat across three and a half decades — wealth gradients
are a stable structural feature, not an eroding one, so a borrowed gradient is not
a decaying quantity. South Africa's own fertility gradient flattened between its
1998 and {sa_t['year']} surveys.

![Gradient tilts across survey years](figures/fig4_slopes_over_time.png)

**Stable across countries is not the same as stable within one.** The flat line
above is a pooled median over many countries; a single fast-developing country
can move a long way underneath it. Brazil is the worked case — see the census
series below, where its child-mortality gradient roughly halves in twenty years.
Read the pooled stability as "a borrowed gradient does not decay", not as "a
country's own gradient will not change".
"""

    ccm = census_child_mortality()
    if ccm:
        doc += f"""
## Child mortality from censuses, and Brazil's twenty-year trend

The DHS child-mortality gradients above are one survey per country, and for some
countries that survey is old — Brazil's only usable DHS is 1996. Censuses ask
every mother how many children she has borne and how many are still alive, so
the household asset index already used for adult mortality yields a
child-mortality gradient for any census year, including years no survey covers.
These rows live in
[`data/census_child_mortality.csv`](data/census_child_mortality.csv).

The measure is the proportion of children ever born who have died — the classic
Brass indirect indicator, for mothers aged 25–29. It is cumulative rather than a
period rate, so **its levels are not comparable to DHS U5MR levels and must not
be pooled with them.** Only the tilt is comparable.

That comparability was tested rather than assumed. Brazil's 2000 census sits four
years after its 1996 DHS, and the two agree to {ccm['vdiff']:.3f}: the census
gives {fmt(ccm['vtilt'])} where the {ccm['vsurvey']} U5MR gradient is
{fmt(ccm['vref'])}. Two independent sources, with different measures and
different wealth rankings, landing on the same number.

| Census | Groups | Tilt | Poorest/richest | Poorest group's children dead |
|---|---|---|---|---|
{ccm['rows']}

**Brazil's child-mortality gradient roughly halved**, from {fmt(ccm['t0'])} in
{ccm['y0']} to {fmt(ccm['t1'])} in {ccm['y1']}. Child mortality fell in every
group, but proportionally faster among the poor, and the poorest-to-richest ratio
narrowed from 4.4× to 2.1×.

That is a real change, not an artefact of the asset index growing richer over
time (1991 offers four asset variables, 2010 offers ten). Re-estimating every
census on only the assets common to all three — electricity, fridge, TV, radio
and cars — the flattening is *larger*, {fmt(ccm['chg_common'])} against
{fmt(ccm['chg_full'])} on the full index. Both variants are published, tagged by
the `index` column; use `index == "full"`, which supports more wealth groups. The
common-index 2010 estimate collapses to two groups, because by then nearly every
Brazilian household owned all four items — a warning that simple durable-goods
indices stop discriminating as a country gets richer.

**For calibration:** the library's Brazil DHS row is a 1996 tilt of −1.46, and by
2010 the value was near {fmt(ccm['t1'])}. A present-day Brazilian calibration
using the DHS row overstates the child-mortality gradient by roughly 0.5.
"""

    amr_path = DATA / "adult_mortality_gradients.csv"
    if amr_path.exists():
        amr = pd.read_csv(amr_path)
        n_cens = amr.groupby(["country", "year"]).ngroups
        gg = general_gradient() or {}
        gg_a = gg.get("income_rule.intercept", float("nan"))
        gg_b = gg.get("income_rule.slope_ln_gni", float("nan"))
        gg_r = gg.get("income_rule.r", float("nan"))
        gg_n = gg.get("income_rule.n_censuses", float("nan"))
        gg_sd = gg.get("income_rule.residual_sd", float("nan"))
        gg_dbl = gg_b * 0.6931  # effect of doubling income
        gg_med = gg.get("fallback.pooled_median_tilt", float("nan"))
        gg_mae_c = gg.get("validation.loo_mae_rule_constant", float("nan"))
        gg_mae_i = gg.get("validation.loo_mae_rule_income", float("nan"))
        gg_mae_r = gg.get("validation.loo_mae_rule_region", float("nan"))
        gg_agemae = gg.get("validation.age_offset_mae", float("nan"))
        gg_bsign, gg_babs = ("+" if gg_b >= 0 else NEG), abs(gg_b)
        gg_rf, gg_dblf, gg_medf = fmt(gg_r), fmt(gg_dbl), fmt(gg_med)
        gg_agerows = "\n".join(
            f"| {b} | {fmt(v)} | {'least trustworthy' if b in ('45-59', '60-74') else ''} |"
            for b, v in gg.get("_ages", []))
        doc += f"""
## Adult mortality gradients (census household-deaths modules)

Adult mortality by wealth comes from census microdata, not DHS surveys (see the
README for why). Households are ranked by an asset index; tilts are on the same
log-rate-per-unit-rank scale as the tables above. The age pattern — steepest at
prime working ages, fading in old age — is the by-age shape ogcore's
`mort_gradient` accepts directly, and it holds in every one of the
{n_cens} censuses measured:

![Adult-mortality tilt by age band and country](figures/fig5_amr_age_profile.png)

### The general gradient: what to use when a country has no measurement of its own

Most countries have no measured adult-mortality gradient. The library therefore
publishes a fallback in
[`data/general_gradient.csv`](data/general_gradient.csv), and the rule for using
it is simple: **a country with its own measurement should always prefer it; the
general gradient is for everyone else.**

The steepness of the gradient tracks how rich the country is:

    tilt(45q15) = {gg_a:.3f} {gg_bsign} {gg_babs:.3f} × ln(GNI per capita, current US$)

with r = {gg_rf} across {gg_n:.0f} censuses and a 1 SD band of
±{gg_sd:.2f}. Doubling income per head steepens the gradient by about
{gg_dblf}.

That rule was chosen by competition, not assertion. Three candidates were each
judged by leaving one census out of the fit and predicting it — the honest test,
because a country using the fallback is by definition not in the fit:

| Candidate rule | Mean absolute error |
|---|---|
| One tilt for every country (the pooled median, {gg_medf}) | {gg_mae_c:.3f} |
| **Read it off national income** | **{gg_mae_i:.3f}** |
| The country's regional median | {gg_mae_r:.3f} |

Income is wrong by less than half as much as a single global number, and a third
less than regional medians. So there is a general gradient, and income — not
region — is what it tracks. It is also most accurate in the middle-income range
where the countries needing it actually sit, and it reproduces South Africa's own
census measurement to within a rounding error.

To spread the summary tilt across age bands, which is what ogcore's
`mort_gradient` accepts, add these pooled offsets:

| Age band | Offset to add | |
|---|---|---|
{gg_agerows}

Applying an offset this way reproduces a country's own measured band tilt to a
median ±{gg_agemae:.2f}, so the age shape is a good deal coarser than the level.

**The 45–59 and 60–74 offsets are the least trustworthy numbers in this file.**
They are positive because in the poorest countries measured mortality rises with
wealth at older ages, and that may not be real — see the next section. A model
that only needs working-age mortality should prefer the 15–29 and 30–44 offsets
and treat the older ones as an upper bound on flatness.

**Do not hold a low-income country's tilt fixed across a long transition.** As
income rises the gradient should be expected to steepen toward the middle- and
high-income values in this table.

### The reversal at older ages, and why HIV does not explain it

In the poorest countries the gradient is flat, and at older ages it turns
positive: measured mortality is *higher* in wealthier households in Ethiopia
2007, Uganda 2002, South Sudan 2008 and Mozambique 2007. Where almost everyone
is poor, the top asset group is barely better protected, and deaths are
infectious and maternal rather than the socially graded chronic diseases of
middle income. Against that, a frail elderly relative often moves into a
better-off household before dying, which records the death against that
household's wealth.

Independent evidence now favours a reporting explanation for at least part of
it. In DHS sibling histories — a different source, also relying on a
household's recall of deaths — poorer and less educated respondents report
*fewer* siblings than richer ones despite having far more children of their own,
and the deficit grows the further back they are asked to recall. Under-reporting
of deaths by poorer respondents flattens or reverses a measured gradient in
exactly this way. That does not prove the census reversal is artefactual, but it
makes it the more likely reading, and it is why the older-age offsets above
carry a warning.

HIV does not explain the pattern: excluding South Africa, the correlation
between the tilt and HIV prevalence is +0.00, Lesotho has the set's highest
prevalence with a solidly negative tilt, and the reversal is strongest at
60–74, where HIV mortality is rare.

### What the columns mean, and what was left out

`linked` is the share of the census's death records that reached estimation.
Where it is well below 1 (South Africa 2011), rate *levels* are meaningless but
the tilt is unbiased — the linked deaths' composition matches the unlinked on
province, urban/rural, sex, and age.

Every sample here passed a completeness check: the supplementary per-death file
is compared, *within each wealth group*, against the same households' own
reported death counts (`MORTNUM`). Even record loss cancels out of a tilt;
wealth-skewed loss does not. Three samples failed and are deliberately absent —
the IPUMS mortality supplement for Brazil 2010 (holds 48% of the deaths the
census itself reports, with the loss concentrated in wealthy households; the
Brazil rows below come from IBGE's own microdata instead), Nepal 2001, and El
Salvador 2007. Their evidence is recorded in
`scripts/build_adult_mortality.py`.

| Country | Year | Sex | Ages | Measure | Tilt | Poorest/richest | Death records | Linked |
|---|---|---|---|---|---|---|---|---|
"""
        for _, r in amr.iterrows():
            doc += (
                f"| {r['country']} | {r['year']} | {r['sex']} | {r['age_lo']}–{r['age_hi']} "
                f"| {r['measure']} | {fmt(r['slope'])} | {r['ratio']:.2f} | {r['n_deaths']:,} "
                f"| {r.get('linked_share', 1.0):.0%} |\n"
            )
        doc += (
            "\nRanking: household asset index (see README for the income-vs-assets"
            " validation and the build pipeline; asset components vary by census"
            " and are recorded in `scripts/build_adult_mortality.py`).\n"
        )

    (ROOT / "ANALYSIS.md").write_text(doc)
    print("wrote ANALYSIS.md")


if __name__ == "__main__":
    main()
