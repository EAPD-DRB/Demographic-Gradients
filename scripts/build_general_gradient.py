# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""The general adult-mortality gradient: a fallback any country can use.

A country model should use its own measured tilt when it has one. Most do not.
This builds the fallback and, more importantly, shows how well it would have
served the countries that DO have a measured tilt - so a user can see what
accuracy they are accepting.

Three candidate rules compete, judged by leave-one-out error. Leave-one-out is
the honest test: a country using the fallback is by definition not in the fit,
so each country is predicted from a rule fitted without it.

    constant   one number for everyone (the pooled median)
    income     tilt ~ a + b * ln(GNI per capita)
    region     the median tilt of the country's region

The level comes from the winning rule; the by-age shape is pooled separately,
because ogcore's `mort_gradient` accepts a tilt per age band.

    uv run scripts/build_general_gradient.py

Writes data/general_gradient.csv. GNI per capita comes from the World Bank API
(free, no key), matched to each census year.
"""

import argparse
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "adult_mortality_gradients.csv"
OUT = ROOT / "data" / "general_gradient.csv"
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]

# World Bank ISO3 per country in the adult-mortality file
ISO3 = {"South Africa": "ZAF", "Ethiopia": "ETH", "Brazil": "BRA", "Zambia": "ZMB",
        "Malawi": "MWI", "Mozambique": "MOZ", "Uganda": "UGA", "Rwanda": "RWA",
        "Senegal": "SEN", "Sierra Leone": "SLE", "Lesotho": "LSO", "Benin": "BEN",
        "Sudan": "SDN", "South Sudan": "SSD", "Burkina Faso": "BFA",
        "Cote d'Ivoire": "CIV", "Mali": "MLI"}
# UN/World Bank regional grouping, for the region rule
REGION = {"South Africa": "Southern Africa", "Lesotho": "Southern Africa",
          "Zambia": "Eastern Africa", "Malawi": "Eastern Africa",
          "Mozambique": "Eastern Africa", "Uganda": "Eastern Africa",
          "Rwanda": "Eastern Africa", "Ethiopia": "Eastern Africa",
          "Sudan": "Northern Africa", "South Sudan": "Eastern Africa",
          "Senegal": "Western Africa", "Sierra Leone": "Western Africa",
          "Benin": "Western Africa", "Burkina Faso": "Western Africa",
          "Cote d'Ivoire": "Western Africa", "Mali": "Western Africa",
          "Brazil": "Latin America"}


def wb(iso3, year, indicator="NY.GNP.PCAP.CD"):
    url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}"
           f"?date={year}&format=json")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return json.load(r)[1][0]["value"]
        except (IndexError, KeyError, TypeError):
            return None
        except Exception:
            time.sleep(4 * (attempt + 1))
    return None


def observations():
    """One tilt per census: the 45q15 'all' row, else the mean of the sexes."""
    a = pd.read_csv(SRC)
    q = a[a["measure"] == "45q15"]
    rows = []
    for (c, y), g in q.groupby(["country", "year"]):
        both = g[g["sex"] == "all"]
        src = both if len(both) else g[g["sex"].isin(["male", "female"])]
        rows.append(dict(country=c, year=int(y), tilt=float(src["slope"].mean()),
                         n_deaths=int(src["n_deaths"].max()),
                         region=REGION.get(c, "unknown")))
    d = pd.DataFrame(rows)
    d["gni"] = [wb(ISO3[c], y) for c, y in zip(d["country"], d["year"])]
    d["lg"] = np.log(d["gni"])
    return d


def loo_errors(d):
    """Leave-one-out prediction error for each candidate rule."""
    out = []
    for i in d.index:
        tr, te = d.drop(index=i), d.loc[i]
        pred = {"constant": tr["tilt"].median()}
        fit = tr.dropna(subset=["lg", "tilt"])
        b, a_ = np.polyfit(fit["lg"], fit["tilt"], 1)
        pred["income"] = (a_ + b * te["lg"]) if np.isfinite(te["lg"]) else np.nan
        same = tr[tr["region"] == te["region"]]
        pred["region"] = same["tilt"].median() if len(same) else tr["tilt"].median()
        out.append(dict(country=te["country"], year=te["year"], actual=te["tilt"],
                        **{f"pred_{k}": v for k, v in pred.items()}))
    e = pd.DataFrame(out)
    for k in ("constant", "income", "region"):
        e[f"err_{k}"] = e[f"pred_{k}"] - e["actual"]
    return e


def age_shape(src=SRC):
    """Pooled offset of each age band's tilt from the 15-59 summary tilt."""
    a = pd.read_csv(src)
    mx = a[(a["measure"] == "mx") & (a["sex"] == "all")]
    q = a[(a["measure"] == "45q15") & (a["sex"] == "all")].set_index(["country", "year"])["slope"]
    rows = []
    for (c, y), g in mx.groupby(["country", "year"]):
        if (c, y) not in q.index:
            continue
        base = q.loc[(c, y)]
        for _, r in g.iterrows():
            rows.append(dict(band=f"{int(r.age_lo)}-{int(r.age_hi)}",
                             offset=float(r["slope"]) - float(base)))
    o = pd.DataFrame(rows)
    return o.groupby("band")["offset"].agg(["median", "count"])


def main():
    # no options; argparse is here so `--help` behaves like the sibling scripts
    # rather than silently running a full fit (which calls the World Bank API)
    argparse.ArgumentParser(description=__doc__.splitlines()[0]).parse_args()
    d = observations()
    print(f"{len(d)} census observations, {d['country'].nunique()} countries\n")
    e = loo_errors(d)

    print("Leave-one-out accuracy of each candidate general rule:")
    print(f"{'rule':<12}{'MAE':>8}{'RMSE':>8}{'max |err|':>11}{'sign correct':>14}")
    best, best_mae = None, 9e9
    for k in ("constant", "income", "region"):
        s = e[f"err_{k}"].dropna()
        mae, rmse = s.abs().mean(), np.sqrt((s ** 2).mean())
        sign = (np.sign(e[f"pred_{k}"]) == np.sign(e["actual"])).mean()
        print(f"{k:<12}{mae:>8.3f}{rmse:>8.3f}{s.abs().max():>11.3f}{sign:>13.0%}")
        if mae < best_mae:
            best, best_mae = k, mae
    print(f"\nbest rule: {best}\n")

    print("Per-country: what the general rule would have predicted vs the measured tilt")
    print(f"{'country':<15}{'year':>6}{'GNI':>8}{'measured':>10}{'general':>9}{'error':>8}")
    m = e.merge(d[["country", "year", "gni"]], on=["country", "year"])
    for _, r in m.sort_values("gni").iterrows():
        g = f"{r['gni']:,.0f}" if pd.notna(r["gni"]) else "n/a"
        p, err = r[f"pred_{best}"], r[f"err_{best}"]
        print(f"{r['country']:<15}{int(r['year']):>6}{g:>8}{r['actual']:>10.3f}"
              f"{p:>9.3f}{err:>8.3f}" if pd.notna(p) else
              f"{r['country']:<15}{int(r['year']):>6}{g:>8}{r['actual']:>10.3f}"
              f"{'n/a':>9}{'n/a':>8}")

    fit = d.dropna(subset=["lg", "tilt"])
    b, a_ = np.polyfit(fit["lg"], fit["tilt"], 1)
    r = np.corrcoef(fit["lg"], fit["tilt"])[0, 1]
    resid = fit["tilt"] - (a_ + b * fit["lg"])
    print(f"\nfull-sample income rule: tilt = {a_:+.4f} {b:+.4f} * ln(GNI)")
    print(f"   r = {r:+.3f}   R2 = {r**2:.2f}   residual SD = {resid.std():.3f}")

    shape = age_shape()
    print("\nBy-age shape (offset from the 15-59 tilt, pooled median):")
    for band, row in shape.iterrows():
        print(f"   {band:<8}{row['median']:+.3f}   (n={int(row['count'])})")

    # how well does 45q15 + offset reproduce a measured band tilt?
    a = pd.read_csv(SRC)
    q = a[(a["measure"] == "45q15") & (a["sex"] == "all")].set_index(["country", "year"])["slope"]
    mx = a[(a["measure"] == "mx") & (a["sex"] == "all")]
    offs = shape["median"].to_dict()
    errs = [abs((q.loc[(r.country, r.year)] + offs[f"{int(r.age_lo)}-{int(r.age_hi)}"]) - r.slope)
            for r in mx.itertuples()
            if (r.country, r.year) in q.index and f"{int(r.age_lo)}-{int(r.age_hi)}" in offs]
    age_mae = float(np.median(errs))
    print(f"   applying an offset reproduces a measured band tilt to "
          f"+/-{age_mae:.3f} (median abs error, n={len(errs)})")

    # --- write the rule out
    recs = [dict(component="income_rule", key="intercept", value=round(float(a_), 4),
                 note="tilt_45q15 = intercept + slope_ln_gni * ln(GNI per capita, current US$)"),
            dict(component="income_rule", key="slope_ln_gni", value=round(float(b), 4), note=""),
            dict(component="income_rule", key="residual_sd", value=round(float(resid.std()), 4),
                 note="1 SD uncertainty band on a predicted tilt"),
            dict(component="income_rule", key="r", value=round(float(r), 3), note=""),
            dict(component="income_rule", key="n_censuses", value=int(len(fit)), note=""),
            dict(component="validation", key=f"loo_mae_{best}", value=round(float(best_mae), 4),
                 note="leave-one-out mean absolute error of the chosen rule"),
            dict(component="fallback", key="pooled_median_tilt",
                 value=round(float(d["tilt"].median()), 4),
                 note="use when GNI is unavailable")]
    for band, row in shape.iterrows():
        recs.append(dict(component="age_offset", key=band, value=round(float(row["median"]), 4),
                         note="add to the 45q15 tilt to get this band's tilt"))
    recs.append(dict(component="validation", key="age_offset_mae", value=round(age_mae, 4),
                     note="median abs error of (45q15 tilt + offset) vs a measured band tilt"))
    for k in ("constant", "income", "region"):
        s = e[f"err_{k}"].dropna()
        recs.append(dict(component="validation", key=f"loo_mae_rule_{k}",
                         value=round(float(s.abs().mean()), 4), note=""))
    pd.DataFrame(recs).to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
