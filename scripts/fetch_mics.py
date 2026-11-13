# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "openpyxl"]
# ///
"""Download the MICS wealth-quintile rates and pin them in data/.

UNICEF's Multiple Indicator Cluster Surveys (MICS) publish total fertility,
infant mortality and under-five mortality by wealth quintile in their survey
reports, but no public API serves them. The World Bank's Health Nutrition and
Population Statistics by Wealth Quintile database (source 39) compiles them
together with the DHS values, and its footnotes name the survey behind each
value. This script keeps the values whose footnote names a MICS survey; DHS
values come from the DHS Program's own API (build_gradient_library.py).

UNICEF's child-mortality database (CME, under-five mortality by wealth
quintile) records for each MICS survey whether the rates are direct estimates
from a full birth history or indirect estimates from a summary birth history.
That classification is pinned beside the rates; build_gradient_library.py
accepts MICS infant and under-five mortality only from direct estimates, the
basis of the DHS rates. The World Bank income group of each country in the
survey year (historical classification, OGHIST) and, for fertility, the
national TFR in the survey year (World Development Indicators) are recorded
with the rates.

The World Bank database was last updated in December 2022 and its API is slow
and intermittently unavailable, so the downloads are pinned and the library is
built from the pinned copies. Run this script only to refresh them,
deliberately, and review the diff:

    uv run scripts/fetch_mics.py

Writes data/mics_quintiles_raw.csv and data/mics_methods_unicef.csv.
"""

import io
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
WB = "https://api.worldbank.org/v2"
WB_SERIES = {"SP.DYN.TFRT": "TFR", "SP.DYN.IMRT": "IMR", "SH.DYN.MORT": "U5MR"}
UNICEF = ("https://sdmx.data.unicef.org/ws/public/sdmxapi/rest/data/"
          "UNICEF,CME_DF_2021_WQ,1.0/.MRY0T4..Q1+Q2+Q3+Q4+Q5..?format=csv")
# World Bank historical income classifications (OGHIST), by calendar year of GNI data
OGHIST = ("https://datacatalogfiles.worldbank.org/ddh-published/0037712/DR0090754/"
          "OGHIST.xlsx")
INCOME = {"L": "Low income", "LM": "Lower middle income", "UM": "Upper middle income",
          "H": "High income"}
MICS = re.compile(r"mics|multiple indicator", re.I)


def get(url, timeout=180, tries=6):
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # the World Bank API returns 502s and timeouts
            print(f"  retry {a + 1}/{tries}: {e}", flush=True)
            time.sleep(10 * (a + 1))
    sys.exit(f"download failed: {url}")


def world_bank():
    rows = []
    for code, ind in WB_SERIES.items():
        for q in range(1, 6):
            url = (f"{WB}/country/all/indicator/{code}.Q{q}"
                   "?source=39&format=json&per_page=20000&footnote=y")
            recs = json.loads(get(url))[1] or []
            n = 0
            for r in recs:
                note = (r.get("footnote") or "").strip()
                if r["value"] is None or not MICS.search(note):
                    continue
                rows.append({"indicator": ind, "iso3": r["countryiso3code"],
                             "wb_country": r["country"]["value"], "year": int(r["date"]),
                             "quintile": q, "value": float(r["value"]), "footnote": note})
                n += 1
            print(f"{code}.Q{q}: {n} MICS values", flush=True)
    d = pd.DataFrame(rows)
    # Income group in the survey year (the World Bank's classification changes:
    # Guyana is high income now, lower middle income at its 2014 survey).
    h = pd.read_excel(io.BytesIO(get(OGHIST)), "Country Analytical History", header=None)
    years = [int(y) if str(y).isdigit() else None for y in h.iloc[5, 2:]]
    hist = h.iloc[11:, 2:].set_axis(years, axis=1).set_axis(h.iloc[11:, 0], axis=0)
    last = max(y for y in years if y)
    d["income_level"] = [INCOME.get(str(hist.at[i, min(y, last)]).strip(), "")
                         if i in hist.index else "" for i, y in zip(d["iso3"], d["year"])]
    # National TFR in the survey year (World Development Indicators), for the
    # consistency check in build_gradient_library.py
    tfr = json.loads(get(f"{WB}/country/all/indicator/SP.DYN.TFRT.IN"
                         "?format=json&per_page=20000&date=1990:2025"))[1]
    nat = {(r["countryiso3code"], int(r["date"])): r["value"] for r in tfr if r["value"]}
    d["national_tfr"] = [nat.get((i, y)) if ind == "TFR" else None
                         for ind, i, y in zip(d["indicator"], d["iso3"], d["year"])]
    return d.sort_values(["indicator", "iso3", "year", "quintile"])


def unicef_methods():
    u = pd.read_csv(io.BytesIO(get(UNICEF)), dtype=str)
    u = u[u["SERIES_CATEGORY"].fillna("").str.contains("MICS")]
    m = (u[["REF_AREA", "SERIES_YEAR", "SERIES_METHOD"]].drop_duplicates()
         .rename(columns={"REF_AREA": "iso3", "SERIES_YEAR": "series_year",
                          "SERIES_METHOD": "method"}))
    return m.sort_values(["iso3", "series_year", "method"])


def main():
    wb = world_bank()
    wb.to_csv(DATA_DIR / "mics_quintiles_raw.csv", index=False)
    print(f"mics_quintiles_raw.csv: {len(wb)} values, "
          f"{wb.groupby(['iso3', 'year']).ngroups} surveys, {wb['iso3'].nunique()} countries")
    um = unicef_methods()
    um.to_csv(DATA_DIR / "mics_methods_unicef.csv", index=False)
    print(f"mics_methods_unicef.csv: {len(um)} MICS surveys "
          f"({um['method'].value_counts().to_dict()})")


if __name__ == "__main__":
    main()
