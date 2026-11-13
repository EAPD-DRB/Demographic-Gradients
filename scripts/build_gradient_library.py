# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""Rebuild the demographic gradient library from DHS and MICS surveys.

Pulls total fertility (FE_FRTR_W_TFR), infant mortality (CM_ECMR_C_IMR) and
under-5 mortality (CM_ECMR_C_U5M) by wealth quintile for every DHS survey,
computes one comparable gradient per survey (the OLS slope of ln(rate) on
wealth-rank percentile midpoints), and writes the four library CSVs in ../data/.

Also pulls age-specific fertility (FE_FRTR_W_A15 ... A45) by wealth quintile
and writes the fertility age offsets: how much steeper or flatter the gradient is
at each age than the TFR gradient, pooled across countries. The differential is
concentrated in the timing of births, so a single TFR gradient at every age
misses it. Over consecutive surveys a country's own age pattern predicts the next
survey about as well as the pooled offsets overall (better below 30, worse from
35; backtest written to fertility_age_offsets.csv); the pooled offsets are
published because they cover every country and age, and the per-survey age
gradients are supporting data.

IMR is what OG-Core's `infmort_gradient` represents. U5MR is published for
comparison: its gradient is steeper in most surveys that report both, because
it includes deaths at ages 1-4, where infectious causes weigh more. Every
survey in the library that reports U5MR by quintile also reports IMR.

MICS surveys (UNICEF) are added from the pinned copy of the World Bank's
compilation written by fetch_mics.py. Every survey of either kind goes into
gradient_library.csv, with a `source` column (DHS or MICS); the latest file
takes each country's most recent survey of either kind, the DHS survey where
both are from the same year. MICS infant and under-five mortality are used
only where UNICEF (or, where UNICEF has no record, the survey report) records
the rates as direct estimates from a full birth history, the basis of the DHS
rates; mics_surveys.csv records the classification of every survey and what
is used from it. Values were checked against the MICS reports: see the MICS
checks below. Surveys from
countries classified as high income in the survey year are outside the
library's scope. The fertility age offsets use DHS surveys only: the MICS compilation
has no age-specific rates by quintile.

The DHS API is free and public (https://api.dhsprogram.com) — no key, no
registration. Run:

    uv run scripts/build_gradient_library.py            # re-pull the DHS API
    uv run scripts/build_gradient_library.py --no-pull  # rebuild from data/
"""

import argparse
import datetime
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
API = "https://api.dhsprogram.com/rest/dhs"
INDICATORS = {"FE_FRTR_W_TFR": "TFR", "CM_ECMR_C_IMR": "IMR", "CM_ECMR_C_U5M": "U5MR"}
ASFR_AGES = [15, 20, 25, 30, 35, 40, 45]
ASFR = {f"FE_FRTR_W_A{a}": f"ASFR{a}" for a in ASFR_AGES}
# The backtest leaves out 45-49: a quintile with no births makes it unfittable
# in about half the surveys.
BACKTEST_AGES = ASFR_AGES[:-1]
# Wealth-rank percentile midpoint represented by each quintile
QUINTILE_MIDPOINTS = {
    "Lowest": 0.10,
    "Second": 0.30,
    "Middle": 0.50,
    "Fourth": 0.70,
    "Highest": 0.90,
}
MID = list(QUINTILE_MIDPOINTS.values())
# MICS checks, verified against the MICS survey reports (2026-11-13).
# - The World Bank compilation files the adolescent birth rate column of MICS6
#   table TM.2.1 under TFR for seven surveys. Their TFR by quintile is taken
#   from the reports (mics_tfr_from_reports.csv; a row with blank values is a
#   known mislabel whose report has not been read, and is excluded).
# - Guard: any other MICS TFR set whose quintile mean is more than 1.4 times
#   from the national TFR (WDI; the widest DHS discrepancy is 1.35) stops the
#   build, unless verified against its report below. Survey and WDI TFRs can
#   differ legitimately, so the guard flags, it does not exclude.
# - Mortality is published mostly in whole numbers; a quintile rate of 3 or
#   less per 1,000 (none in the DHS sets, whose minimum is 5) leaves the
#   gradient to rounding and to a handful of deaths. Correct but too imprecise.
TFR_GUARD = 1.4
MAX_IMPRECISE_RATE = 3
MICS_TFR_VERIFIED = {
    ("MKD", 2019): "report table TM.2.1 gives the same values; the survey's national TFR "
                   "is 1.9 against 1.34 in WDI",
}
SOURCE_ORDER = {"MICS": 0, "DHS": 1}  # on a same-year tie the DHS survey is latest
# World Bank country names that differ from the DHS Program's
WB_NAMES = {"Congo, Rep.": "Congo", "Gambia, The": "Gambia"}
# Countries with a MICS survey but no DHS survey are not in the DHS Program's
# region list; each is placed in the DHS region it would belong to. The DHS
# scheme has no East Asia region; Mongolia is placed with Central Asia.
MICS_REGIONS = {
    "Algeria": "North Africa/West Asia/Europe",
    "Argentina": "Latin America & Caribbean",
    "Belize": "Latin America & Caribbean",
    "Bhutan": "South & Southeast Asia",
    "Guinea-Bissau": "Sub-Saharan Africa",
    "Iraq": "North Africa/West Asia/Europe",
    "Jamaica": "Latin America & Caribbean",
    "Kiribati": "Oceania",
    "Lao PDR": "South & Southeast Asia",
    "Mongolia": "Central Asia",
    "North Macedonia": "North Africa/West Asia/Europe",
    "Serbia": "North Africa/West Asia/Europe",
    "Suriname": "Latin America & Caribbean",
    "Tonga": "Oceania",
}


def api_pages(url):
    page = 1
    while True:
        with urllib.request.urlopen(f"{url}&perpage=1000&page={page}", timeout=60) as r:
            d = json.load(r)
        yield from d.get("Data", [])
        if page >= d.get("TotalPages", 1):
            return
        page += 1
        time.sleep(0.3)


def tilt(values):
    """OLS slope of ln(rate) on the quintile midpoints; NaN if any rate is 0."""
    v = np.asarray(values, dtype=float)
    if len(v) != 5 or np.isnan(v).any() or (v <= 0).any():
        return np.nan
    return np.polyfit(list(QUINTILE_MIDPOINTS.values()), np.log(v), 1)[0]


def fertility_age_tilts(raw):
    """Each survey's fertility gradient at each age, beside its TFR gradient.

    Keyed by survey, and kept only where every quintile reports the TFR and
    all seven age rates; an age with a zero-birth quintile gets a NaN gradient.
    """
    q = raw[raw["quintile"].isin(QUINTILE_MIDPOINTS)].copy()
    q["value"] = pd.to_numeric(q["value"], errors="coerce")
    wide = q.pivot_table(index=["country", "year", "survey", "quintile"],
                         columns="indicator", values="value", aggfunc="first")
    need = ["TFR"] + list(ASFR.values())
    wide = wide.reindex(columns=need).dropna().reset_index()
    out = []
    for (ctry, yr, sid), g in wide.groupby(["country", "year", "survey"]):
        if len(g) != 5:
            continue
        g = g.set_index("quintile").reindex(list(QUINTILE_MIDPOINTS))
        tfr = tilt(g["TFR"])
        for a in ASFR_AGES:
            v = g[f"ASFR{a}"].values
            s = tilt(v)
            out.append({"country": ctry, "year": yr, "survey": sid,
                        "age_lo": a, "age_hi": a + 4, "slope": s,
                        "tfr_slope": tfr, "offset": s - tfr,
                        **{f"q{i + 1}": x for i, x in enumerate(v)}})
    return pd.DataFrame(out).sort_values(["country", "year", "survey", "age_lo"])


def fertility_age_offsets(ages):
    """Pooled offsets (latest survey per country) and the backtest behind them."""
    off = ages.pivot_table(index=["country", "year", "survey"], columns="age_lo",
                           values="offset").reset_index()
    off = off.sort_values(["country", "year", "survey"])
    latest = off.groupby("country").tail(1)
    # Backtest: predict each survey's age shape from (a) a single TFR gradient at
    # every age, (b) the offsets pooled over the other countries' surveys, or
    # (c) the same country's previous survey.
    full = off.dropna(subset=BACKTEST_AGES)
    err = {k: {a: [] for a in BACKTEST_AGES} for k in ("flat", "pooled", "own")}
    pairs = 0
    for ctry, g in full.groupby("country"):
        pool = full.loc[full["country"] != ctry, BACKTEST_AGES].median()
        for i in range(1, len(g)):
            prev, cur = g.iloc[i - 1], g.iloc[i]
            pairs += 1
            for a in BACKTEST_AGES:
                err["flat"][a].append(abs(cur[a]))
                err["pooled"][a].append(abs(cur[a] - pool[a]))
                err["own"][a].append(abs(cur[a] - prev[a]))
    rows = []
    for a in ASFR_AGES:
        x = latest[a].dropna()
        rows.append({
            "age_lo": a, "age_hi": a + 4, "offset": x.median(),
            "iqr_lo": x.quantile(0.25), "iqr_hi": x.quantile(0.75),
            "countries": len(x),
            **{f"backtest_err_{k}": (np.mean(err[k][a]) if a in BACKTEST_AGES else np.nan)
               for k in ("flat", "pooled", "own")},
            "backtest_pairs": pairs if a in BACKTEST_AGES else 0,
        })
    return pd.DataFrame(rows)


def gradient_rows(df, source):
    """One wealth gradient per indicator and survey from long quintile data.

    df has indicator, country, year, pct (quintile midpoint) and value.
    Incomplete quintets and zero rates are dropped, not imputed.
    """
    df = df.dropna(subset=["value"])
    df = df[df["value"] > 0]
    out = []
    for (ind, ctry, yr), g in df.groupby(["indicator", "country", "year"]):
        if g["pct"].nunique() != 5:
            continue
        slope = np.polyfit(g["pct"].values, np.log(g["value"].values), 1)[0]
        q = {f"q{i + 1}": g.loc[g["pct"] == p, "value"].iloc[0] for i, p in enumerate(MID)}
        out.append({"indicator": ind, "country": ctry, "year": yr, "source": source,
                    "slope": slope, "ratio": q["q1"] / q["q5"], **q})
    return pd.DataFrame(out)


def mics_surveys():
    """The pinned MICS values, each survey classified for use.

    Returns the quintile values (with the DHS country name) and one row per
    survey recording its label, mortality method and what is used from it.
    """
    raw = pd.read_csv(DATA_DIR / "mics_quintiles_raw.csv")
    meth = pd.read_csv(DATA_DIR / "mics_methods_unicef.csv", dtype=str)
    raw["country"] = raw["wb_country"].replace(WB_NAMES)
    # Survey label from the footnote ("Source: MICS6, 2018-19" -> "MICS6, 2018-19");
    # UNICEF identifies a survey by its first fieldwork year ("2018_2019"), the
    # World Bank by its last (2019).
    raw["label"] = (raw["footnote"].str.extract(r"(MICS.*)$", flags=re.I)[0]
                    .str.replace(r"\.\s.*$", "", regex=True).str.strip()
                    .fillna(raw["footnote"]))
    yrs = raw["label"].str.extract(r"((?:19|20)\d{2})(?:\s*-\s*(\d{2,4}))?")
    raw["y0"] = yrs[0].fillna(raw["year"].astype(str)).astype(int)
    end = yrs[1].fillna("").map(lambda e: (2000 + int(e) if len(e) == 2 else int(e)) if e else 0)
    raw["y1"] = np.maximum(raw["y0"], np.maximum(end, raw["year"]))
    meth["y0"] = meth["series_year"].str[:4].astype(int)
    meth["y1"] = meth["series_year"].str[-4:].astype(int)
    reports = pd.read_csv(DATA_DIR / "mics_methods_reports.csv").set_index(["iso3", "year"])
    tfr_rep = pd.read_csv(DATA_DIR / "mics_tfr_from_reports.csv").set_index(["iso3", "year"])
    rows = []
    for (iso, ctry, yr), g in raw.groupby(["iso3", "country", "year"]):
        # UNICEF's record for the same survey: fieldwork years overlap. The two
        # sources label some surveys differently (Congo: World Bank 2015-16,
        # UNICEF and the report 2014-15).
        a, b = int(g["y0"].min()), int(g["y1"].max())
        u = meth[(meth["iso3"] == iso) & (meth["y0"] <= b) & (meth["y1"] >= a)]
        m = "/".join(sorted(set(u["method"])))
        src = "UNICEF"
        if not m and (iso, yr) in reports.index:
            m, src = reports.loc[(iso, yr), "method"], "report"
        method = {"FBH": "direct", "SBH": "indirect", "": "not recorded"}.get(m, f"mixed ({m})")
        if m in ("FBH", "SBH"):
            method += f" ({src})"
        inds = set(g["indicator"])
        mort = inds & {"IMR", "U5MR"}
        use, excl, tfr_note = [], [], ""
        if (g["income_level"] == "High income").any():
            excl.append("high-income country")
        else:
            t = g[g["indicator"] == "TFR"]
            if len(t) and (iso, yr) in tfr_rep.index:
                fix = tfr_rep.loc[(iso, yr)]
                if fix[["q1", "q2", "q3", "q4", "q5"]].notna().all():
                    use.append("TFR")
                    tfr_note = f"TFR from the report (table {fix['table']}, p. {int(fix['page'])})"
                else:
                    excl.append("TFR: World Bank value is the adolescent birth rate; "
                                "report not yet read")
            elif len(t):
                r = t["value"].mean() / t["national_tfr"].iloc[0]
                if not (1 / TFR_GUARD <= r <= TFR_GUARD) and (iso, yr) not in MICS_TFR_VERIFIED:
                    sys.exit(f"MICS TFR check: {ctry} {yr} quintile mean is {r:.2f} times the "
                             "national TFR. Read the survey report: add the true values to "
                             "mics_tfr_from_reports.csv, or MICS_TFR_VERIFIED if correct.")
                use.append("TFR")
            if mort:
                mv = g[g["indicator"].isin(mort)]["value"]
                if not method.startswith("direct"):
                    excl.append("mortality: " + ("method not recorded" if method == "not recorded"
                                                 else f"{method} estimate"))
                elif (mv <= MAX_IMPRECISE_RATE).any():
                    excl.append(f"mortality: a quintile rate of {MAX_IMPRECISE_RATE} or less per "
                                "1,000 (correct as published, too imprecise for a gradient)")
                else:
                    use.append(", ".join(sorted(mort, key=["IMR", "U5MR"].index)))
        rows.append({"country": ctry, "iso3": iso, "year": yr,
                     "survey": g["label"].iloc[0],
                     "indicators": ", ".join(sorted(set(g["indicator"]),
                                                    key=["TFR", "IMR", "U5MR"].index)),
                     "mortality_method": method if mort else "",
                     "income_level": g["income_level"].iloc[0],
                     "used": ", ".join(use), "excluded": "; ".join(excl), "note": tfr_note})
    sv = pd.DataFrame(rows).sort_values(["country", "year"])
    return raw, sv


def mics_library(raw, sv):
    keep = set()
    for r in sv.itertuples():
        for ind in ("TFR", "IMR", "U5MR"):
            if ind in r.used.split(", "):
                keep.add((ind, r.country, r.year))
    d = raw[[k in keep for k in zip(raw["indicator"], raw["country"], raw["year"])]].copy()
    # TFR sets the World Bank mislabels: values from the survey reports
    fix = pd.read_csv(DATA_DIR / "mics_tfr_from_reports.csv").dropna(subset=["q1"])
    for f in fix.itertuples():
        m = (d["indicator"] == "TFR") & (d["iso3"] == f.iso3) & (d["year"] == f.year)
        d.loc[m, "value"] = d.loc[m, "quintile"].map(
            {i: getattr(f, f"q{i}") for i in range(1, 6)})
    d["pct"] = d["quintile"].map(dict(enumerate(MID, start=1)))
    return gradient_rows(d, "MICS")


def regions_table(dhs_regions, countries):
    """DHS regions, plus the MICS-only countries placed in them."""
    known = set(dhs_regions["country"])
    missing = sorted(set(countries) - known - set(MICS_REGIONS))
    if missing:
        sys.exit(f"no region for {missing}: add them to MICS_REGIONS")
    extra = pd.DataFrame([{"country": c, "region": MICS_REGIONS[c]}
                          for c in sorted(set(countries) - known)])
    out = pd.concat([dhs_regions.assign(classification="DHS Program"),
                     extra.assign(classification="assigned")], ignore_index=True)
    return out.sort_values("country")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-pull", action="store_true",
                    help="rebuild from data/dhs_gradients_raw.csv instead of the DHS API")
    args = ap.parse_args()
    DATA_DIR.mkdir(exist_ok=True)

    if args.no_pull:
        raw = pd.read_csv(DATA_DIR / "dhs_gradients_raw.csv")
        regions = pd.read_csv(DATA_DIR / "dhs_regions.csv")
        if "classification" in regions:
            regions = regions[regions["classification"] == "DHS Program"]
        regions = regions[["country", "region"]]
    else:
        raw, regions = pull()

    # 3. One wealth gradient per survey: slope of ln(rate) on rank midpoint.
    #    On this scale a slope of -0.79 means the poorest decile's rate is
    #    about exp(0.79 * 0.8) ~ 1.9x the richest decile's.
    df = raw[raw["quintile"].isin(QUINTILE_MIDPOINTS)
             & raw["indicator"].isin(INDICATORS.values())].copy()
    df["pct"] = df["quintile"].map(QUINTILE_MIDPOINTS)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    dhs = gradient_rows(df, "DHS")

    mraw, sv = mics_surveys()
    sv.to_csv(DATA_DIR / "mics_surveys.csv", index=False)
    mics = mics_library(mraw, sv)
    print(f"MICS: {len(sv)} surveys, {sv['country'].nunique()} countries; use: "
          + "; ".join(f"{k or 'nothing'} {v}" for k, v in sv["used"].value_counts().items()))
    for r in sv[sv["excluded"] != ""].itertuples():
        print(f"  excluded: {r.country} {r.year} ({r.survey}): {r.excluded}")
    print("MICS mortality method: " + "; ".join(
        f"{k} {v}" for k, v in sv.loc[sv["mortality_method"] != "", "mortality_method"]
        .value_counts().items()))

    lib = pd.concat([dhs, mics], ignore_index=True)
    lib["_o"] = lib["source"].map(SOURCE_ORDER)
    lib = lib.sort_values(["indicator", "country", "year", "_o"]).drop(columns="_o")
    lib.to_csv(DATA_DIR / "gradient_library.csv", index=False)
    regions_table(regions, lib["country"]).to_csv(DATA_DIR / "dhs_regions.csv", index=False)

    latest = lib.groupby(["indicator", "country"]).tail(1)
    latest.to_csv(DATA_DIR / "gradient_library_latest.csv", index=False)

    for ind in INDICATORS.values():
        l = latest[latest["indicator"] == ind]
        print(
            f"{ind}: {len(l)} countries ({(l['source'] == 'MICS').sum()} from MICS) | "
            f"median gradient {l['slope'].median():.3f} "
            f"IQR [{l['slope'].quantile(0.25):.3f}, {l['slope'].quantile(0.75):.3f}] "
            f"| median low/high ratio {l['ratio'].median():.2f}"
        )
    print(f"surveys with complete quintets: {lib.groupby(['country', 'year', 'source']).ngroups} "
          f"({len(lib)} country-survey-indicator gradients)")

    # 4. Fertility by age: per-survey age gradients and the pooled offsets (DHS)
    ages = fertility_age_tilts(raw)
    ages.to_csv(DATA_DIR / "fertility_age_tilts.csv", index=False)
    offsets = fertility_age_offsets(ages)
    offsets.to_csv(DATA_DIR / "fertility_age_offsets.csv", index=False)
    print(f"fertility by age: {ages['survey'].nunique()} surveys, "
          f"{ages['country'].nunique()} countries | offsets "
          + " ".join(f"{r.age_lo}-{r.age_hi} {r.offset:+.2f}" for r in offsets.itertuples()))

    if args.no_pull:
        return
    # Stamp the data vintage where the README states it: the script that pulls
    # owns the stamp, so it cannot drift when this runs outside refresh.py.
    readme = DATA_DIR.parent / "README.md"
    today = datetime.date.today().strftime("%-d %B %Y")
    readme.write_text(re.sub(r"API pull of \d{1,2} \w+ \d{4}",
                             f"API pull of {today}", readme.read_text()))
    print(f"stamped data vintage: {today}")


def pull():
    """Raw quintile-level observations and the region list from the DHS API."""
    rows = []
    for ind_id, name in {**INDICATORS, **ASFR}.items():
        n = 0
        for r in api_pages(f"{API}/data?indicatorIds={ind_id}&breakdown=all&f=json"):
            if r.get("CharacteristicCategory") == "Wealth quintile":
                rows.append(
                    {
                        "indicator": name,
                        "country": r["CountryName"],
                        "year": r["SurveyYear"],
                        "survey": r.get("SurveyId", ""),
                        "quintile": r["CharacteristicLabel"],
                        "value": r["Value"],
                    }
                )
                n += 1
        print(f"{name}: {n} wealth-quintile observations")
    raw = pd.DataFrame(rows)
    raw.to_csv(DATA_DIR / "dhs_gradients_raw.csv", index=False)
    regions = pd.DataFrame(
        [
            {"country": c["CountryName"], "region": c["RegionName"]}
            for c in api_pages(f"{API}/countries?f=json")
        ]
    )
    return raw, regions


if __name__ == "__main__":
    main()
