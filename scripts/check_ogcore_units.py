# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy", "scipy"]
# ///
"""How should a library tilt be passed to OG-Core?

The library publishes a log-rate tilt: the OLS slope of ln(rate) on wealth
rank 0-1. OG-Core (>= 0.18) reads a gradient as a log-odds slope per centered
percentile point and turns it into income-group rates with a mean-preserving
logistic (`_mean_preserving_logit_rates`). Dividing by 100 converts rank to
percentile points. Whether a further log-odds conversion is needed depends on
the rate level OG-Core applies the slope to, so this check runs every measured
quintile set through OG-Core's own functions, at OG-Core's own scaling:

    infant mortality   probability of dying per birth   (IMR / 1000)
    under five         annual hazard  -ln(1 - U5MR/1000) / 5
    ages 1-4           annual hazard  -ln(1 - CMR/1000) / 4
    fertility by age   births per person per year       (ASFR / 2000, as
                       OG-Core's get_fert does)

and compares three slopes:

    tilt / 100                     what calibrations passed before this check
    tilt / (100 * (1 - p))         first-order log-odds conversion, p = the
                                   mean rate at OG-Core's scaling
    OG-Core's optimum              the slope that best reproduces the measured
                                   quintiles through OG-Core's own function

The "units effect" is the change in the poorest/richest ratio OG-Core produces
from tilt/100 against the converted slope (same tilt, conversion only). The
"residual" is the converted slope against OG-Core's optimum; it centres on zero
and its tails are noisy quintile sets, not a units problem.

OG-Core's two functions are read from the pinned public release below, so the
check reproduces without a local OG-Core install.

    uv run scripts/check_ogcore_units.py

Writes data/ogcore_units_check.csv; build_analysis.py renders it into
docs/methods/ogcore-units.md. Age-specific fertility is fetched from the DHS
API until the library publishes it itself (ROADMAP A2).
"""

import json
import re
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import optimize as opt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "ogcore_units_check.csv"
OGCORE_TAG = "v0.24.1"
OGCORE_SRC = (f"https://raw.githubusercontent.com/PSLmodels/OG-Core/{OGCORE_TAG}"
              "/ogcore/demographics.py")
API = "https://api.dhsprogram.com/rest/dhs/data"
ORDER = ["Lowest", "Second", "Middle", "Fourth", "Highest"]
RANK = np.array([0.1, 0.3, 0.5, 0.7, 0.9])      # library convention
PCT = (RANK - 0.5) * 100                          # OG-Core's centered midpoints
W = np.full(5, 0.2)
ASFR_AGES = ["15", "20", "25", "30", "35", "40", "45"]


def ogcore_functions():
    """OG-Core's _logistic and _mean_preserving_logit_rates, verbatim."""
    with urllib.request.urlopen(OGCORE_SRC, timeout=120) as r:
        code = r.read().decode()
    ns = {"np": np, "opt": opt}
    for fn in ("_logistic", "_mean_preserving_logit_rates"):
        m = re.search(rf"^def {fn}\(.*?(?=^def )", code, re.S | re.M)
        if m is None:
            raise RuntimeError(f"{fn} not found in OG-Core {OGCORE_TAG}")
        exec(m.group(0), ns)
    return ns["_mean_preserving_logit_rates"]


def dhs_pages(indicator):
    page = 1
    while True:
        url = f"{API}?indicatorIds={indicator}&breakdown=all&f=json&perpage=5000&page={page}"
        req = urllib.request.Request(url, headers={"User-Agent": "Demographic-Gradients"})
        with urllib.request.urlopen(req, timeout=240) as r:
            d = json.load(r)
        yield from d["Data"]
        if page >= d["TotalPages"]:
            return
        page += 1


def quintile_sets():
    """(label, rates at OG-Core's scaling) for every complete quintile set."""
    raw = pd.read_csv(ROOT / "data" / "dhs_gradients_raw.csv")
    raw = raw[raw["quintile"].isin(ORDER)]
    for (ind, _c, _y), g in raw.groupby(["indicator", "country", "year"]):
        v = g.set_index("quintile").reindex(ORDER)["value"].astype(float).values
        if np.isnan(v).any() or (v <= 0).any():
            continue
        if ind == "IMR":
            yield "Infant mortality", v / 1000
        elif ind == "U5MR":
            yield "Under-five mortality", -np.log(1 - v / 1000) / 5
        elif ind == "CMR":
            yield "Child mortality, ages 1-4", -np.log(1 - v / 1000) / 4
    for age in ASFR_AGES:
        recs = pd.DataFrame([r for r in dhs_pages(f"FE_FRTR_W_A{age}")
                             if r["CharacteristicCategory"] == "Wealth quintile"])
        for (_c, _y), g in recs.groupby(["CountryName", "SurveyYear"]):
            v = g.set_index("CharacteristicLabel").reindex(ORDER)["Value"].astype(float).values
            if np.isnan(v).any() or (v <= 0).any():
                continue
            yield f"Fertility, ages {age}-{int(age) + 4}", v / 2000


def main():
    mplr = ogcore_functions()

    def ratio(rates, slope):
        r = mplr(np.array([rates.mean()]), np.array([slope]), W.reshape(1, 5), PCT)[0]
        return r[0] / r[-1]

    rows = []
    for label, rates in quintile_sets():
        tilt = np.polyfit(RANK, np.log(rates), 1)[0]
        p = rates.mean()
        s_plain, s_conv = tilt / 100, tilt / (100 * (1 - p))
        loss = lambda s: np.sum((np.log(mplr(np.array([p]), np.array([s]),
                                             W.reshape(1, 5), PCT)[0]) - np.log(rates)) ** 2)
        s_opt = opt.minimize_scalar(loss, bounds=(-0.2, 0.2), method="bounded").x
        r_plain, r_conv, r_opt = ratio(rates, s_plain), ratio(rates, s_conv), ratio(rates, s_opt)
        rows.append(dict(margin=label, rate=p,
                         units=100 * (r_plain / r_conv - 1),
                         residual=100 * (r_conv / r_opt - 1)))
    t = pd.DataFrame(rows)
    order = (["Infant mortality", "Child mortality, ages 1-4", "Under-five mortality"]
             + [f"Fertility, ages {a}-{int(a) + 4}" for a in ASFR_AGES])
    out = (t.groupby("margin")
           .agg(quintile_sets=("rate", "size"),
                median_rate=("rate", "median"),
                max_rate=("rate", "max"),
                units_effect_median_pct=("units", "median"),
                units_effect_p10_pct=("units", lambda x: x.quantile(0.10)),
                units_effect_worst_pct=("units", "min"),
                residual_after_conversion_median_pct=("residual", "median"))
           .reindex(order).reset_index())
    out["ogcore_version"] = OGCORE_TAG
    out.round(4).to_csv(OUT, index=False)
    print(out.round(2).to_string(index=False))
    print(f"\nwrote {OUT} ({len(t)} quintile sets)")


if __name__ == "__main__":
    main()
