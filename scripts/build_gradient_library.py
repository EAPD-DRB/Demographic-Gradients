# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""Rebuild the demographic gradient library from the DHS Program public API.

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

The API is free and public (https://api.dhsprogram.com) — no key, no
registration. Run:

    uv run scripts/build_gradient_library.py
"""

import datetime
import json
import re
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


def main():
    DATA_DIR.mkdir(exist_ok=True)

    # 1. Raw quintile-level observations
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

    # 2. Country -> DHS region map
    regions = pd.DataFrame(
        [
            {"country": c["CountryName"], "region": c["RegionName"]}
            for c in api_pages(f"{API}/countries?f=json")
        ]
    )
    regions.to_csv(DATA_DIR / "dhs_regions.csv", index=False)

    # 3. One wealth gradient per survey: slope of ln(rate) on rank midpoint.
    #    On this scale a slope of -0.79 means the poorest decile's rate is
    #    about exp(0.79 * 0.8) ~ 1.9x the richest decile's.
    df = raw[raw["quintile"].isin(QUINTILE_MIDPOINTS)
             & raw["indicator"].isin(INDICATORS.values())].copy()
    df["pct"] = df["quintile"].map(QUINTILE_MIDPOINTS)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna(subset=["value"])
    df = df[df["value"] > 0]

    out = []
    for (ind, ctry, yr), g in df.groupby(["indicator", "country", "year"]):
        if g["pct"].nunique() != 5:
            continue  # incomplete quintets are dropped, not imputed
        slope = np.polyfit(g["pct"].values, np.log(g["value"].values), 1)[0]
        q = {
            f"q{i + 1}": g.loc[g["pct"] == p, "value"].iloc[0]
            for i, p in enumerate([0.10, 0.30, 0.50, 0.70, 0.90])
        }
        out.append(
            {
                "indicator": ind,
                "country": ctry,
                "year": yr,
                "slope": slope,
                "ratio": q["q1"] / q["q5"],
                **q,
            }
        )
    lib = pd.DataFrame(out).sort_values(["indicator", "country", "year"])
    lib.to_csv(DATA_DIR / "gradient_library.csv", index=False)

    latest = lib.groupby(["indicator", "country"]).tail(1)
    latest.to_csv(DATA_DIR / "gradient_library_latest.csv", index=False)

    for ind in INDICATORS.values():
        l = latest[latest["indicator"] == ind]
        print(
            f"{ind}: {len(l)} countries | median gradient {l['slope'].median():.3f} "
            f"IQR [{l['slope'].quantile(0.25):.3f}, {l['slope'].quantile(0.75):.3f}] "
            f"| median low/high ratio {l['ratio'].median():.2f}"
        )
    print(f"surveys with complete quintets: {lib.groupby(['country', 'year']).ngroups} "
          f"({len(lib)} country-survey-indicator gradients)")

    # 4. Fertility by age: per-survey age gradients and the pooled offsets
    ages = fertility_age_tilts(raw)
    ages.to_csv(DATA_DIR / "fertility_age_tilts.csv", index=False)
    offsets = fertility_age_offsets(ages)
    offsets.to_csv(DATA_DIR / "fertility_age_offsets.csv", index=False)
    print(f"fertility by age: {ages['survey'].nunique()} surveys, "
          f"{ages['country'].nunique()} countries | offsets "
          + " ".join(f"{r.age_lo}-{r.age_hi} {r.offset:+.2f}" for r in offsets.itertuples()))

    # Stamp the data vintage where the README states it: the script that pulls
    # owns the stamp, so it cannot drift when this runs outside refresh.py.
    readme = DATA_DIR.parent / "README.md"
    today = datetime.date.today().strftime("%-d %B %Y")
    readme.write_text(re.sub(r"API pull of \d{1,2} \w+ \d{4}",
                             f"API pull of {today}", readme.read_text()))
    print(f"stamped data vintage: {today}")


if __name__ == "__main__":
    main()
