# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas"]
# ///
"""Rebuild the demographic gradient library from the DHS Program public API.

Pulls total fertility (FE_FRTR_W_TFR) and under-5 mortality (CM_ECMR_C_U5M)
by wealth quintile for every DHS survey, computes one comparable tilt per
survey (the OLS slope of ln(rate) on wealth-rank percentile midpoints), and
writes the four CSVs in ../data/.

The API is free and public (https://api.dhsprogram.com) — no key, no
registration. Run:

    uv run scripts/build_gradient_library.py
"""

import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
API = "https://api.dhsprogram.com/rest/dhs"
INDICATORS = {"FE_FRTR_W_TFR": "TFR", "CM_ECMR_C_U5M": "U5MR"}
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


def main():
    DATA_DIR.mkdir(exist_ok=True)

    # 1. Raw quintile-level observations
    rows = []
    for ind_id, name in INDICATORS.items():
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

    # 3. One tilt per survey: slope of ln(rate) on percentile midpoint.
    #    On this scale a slope of -0.79 means the poorest decile's rate is
    #    about exp(0.79 * 0.8) ~ 1.9x the richest decile's.
    df = raw[raw["quintile"].isin(QUINTILE_MIDPOINTS)].copy()
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
            f"{ind}: {len(l)} countries | median tilt {l['slope'].median():.3f} "
            f"IQR [{l['slope'].quantile(0.25):.3f}, {l['slope'].quantile(0.75):.3f}] "
            f"| median poorest/richest ratio {l['ratio'].median():.2f}"
        )
    print(f"surveys with complete quintets: {len(lib)}")


if __name__ == "__main__":
    main()
