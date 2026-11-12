# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy", "scipy"]
# ///
"""The general adult-mortality gradient: a fallback any country can use.

A country model should use its own measured tilt when it has one. Most do not.
This builds the fallback and, more importantly, shows how well it would have
served the countries that DO have a measured tilt - so a user can see what
accuracy they are accepting.

Three candidate rules are compared by leave-one-country-out prediction error:
each census is predicted from a rule estimated without any census of the same
country, which matches the use case of a country with no estimate of its own.
All rules are scored on the same censuses (those with a GNI figure); the region
rule falls back to the pooled median where a region has no other census.

    constant   one number for everyone (the pooled median)
    income     tilt ~ a + b * ln(GNI per capita)
    region     the median tilt of the country's region

The level comes from the winning rule; the by-age shape is pooled separately,
because ogcore's `mort_gradient` accepts a tilt per age band.

    uv run scripts/build_general_gradient.py

Writes data/general_gradient.csv (the rule, with its standard errors and what
is needed for a prediction interval) and data/general_gradient_points.csv (each
census behind it: GNI, measured tilt, leave-one-out prediction).

GNI per capita (World Bank, Atlas method, current US$) is read from
data/gni_census_years.csv, so the fit does not change when the World Bank
revises its historical series. A census missing from that file is fetched from
the World Bank API (free, no key) and appended with the retrieval date;
`--refresh-gni` re-downloads every value.

Inference is classical OLS: standard errors from the residual standard error
with n - 2 degrees of freedom, 95% intervals from Student's t. The interval
for a country without its own estimate is the prediction interval

    pred +/- t * s * sqrt(1 + 1/n + (ln GNI - mean_ln_gni)^2 / sxx_ln_gni)

whose terms are all written to the output.
"""

import argparse
import datetime
import json
import time
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "adult_mortality_gradients.csv"
OUT = ROOT / "data" / "general_gradient.csv"
POINTS = ROOT / "data" / "general_gradient_points.csv"
GNI = ROOT / "data" / "gni_census_years.csv"
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
    """The World Bank value, or None only when the API has no value for it.

    Any other failure (network, an error message in place of data) is retried
    and then raised, so a transient outage cannot silently drop a census.
    """
    url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/{indicator}"
           f"?date={year}&format=json")
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                body = json.load(r)
            if len(body) > 1 and body[1] is None:
                return None                      # valid reply, no data
            return body[1][0]["value"]
        except Exception as e:
            err = e
            time.sleep(4 * (attempt + 1))
    raise RuntimeError(f"World Bank API failed for {iso3} {year}: {err}")


def census_gni(need, refresh=False):
    """GNI per capita for each census, from the pinned file; fetch what is missing.

    A value the World Bank does not have (South Sudan before 2011) is stored
    as blank, so it is not requested again.
    """
    have = (pd.read_csv(GNI) if GNI.exists() and not refresh else
            pd.DataFrame(columns=["country", "iso3", "year", "gni", "retrieved"]))
    known = set(zip(have["country"], have["year"]))
    today = datetime.date.today().isoformat()
    new = [dict(country=c, iso3=ISO3[c], year=int(y), gni=wb(ISO3[c], int(y)), retrieved=today)
           for c, y in need.itertuples(index=False) if (c, y) not in known]
    if new:
        have = pd.concat([have, pd.DataFrame(new)], ignore_index=True)
        have = have.sort_values(["country", "year"])
        have.to_csv(GNI, index=False)
        print(f"fetched GNI for {len(new)} census(es) from the World Bank API; wrote {GNI}")
    return have[["country", "year", "gni"]].astype({"year": int, "gni": float})


def observations(refresh=False):
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
    d = d.merge(census_gni(d[["country", "year"]], refresh), on=["country", "year"], how="left")
    for r in d[d["gni"].isna()].itertuples():
        print(f"no World Bank GNI for {r.country} {r.year}: excluded from the fit")
    d["lg"] = np.log(d["gni"])
    return d


def loo_errors(d):
    """Leave-one-country-out prediction error for each candidate rule.

    A country's censuses are all left out together (South Africa and Malawi
    have two each), matching the use case of a country with no estimate of its
    own. Censuses without a GNI figure are dropped first, so every rule is
    scored on the same observations.
    """
    d = d.dropna(subset=["lg", "tilt"])
    out = []
    for i in d.index:
        te = d.loc[i]
        tr = d[d["country"] != te["country"]]
        pred = {"constant": tr["tilt"].median()}
        b, a_ = np.polyfit(tr["lg"], tr["tilt"], 1)
        pred["income"] = a_ + b * te["lg"]
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
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh-gni", action="store_true",
                    help="re-download every census's GNI instead of using the pinned file")
    d = observations(ap.parse_args().refresh_gni)
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
    n = len(fit)
    b, a_ = np.polyfit(fit["lg"], fit["tilt"], 1)
    r = np.corrcoef(fit["lg"], fit["tilt"])[0, 1]
    resid = fit["tilt"] - (a_ + b * fit["lg"])
    s_e = float(np.sqrt((resid ** 2).sum() / (n - 2)))     # residual standard error
    xbar = float(fit["lg"].mean())
    sxx = float(((fit["lg"] - xbar) ** 2).sum())
    se_b = s_e / np.sqrt(sxx)
    se_a = s_e * np.sqrt(1 / n + xbar ** 2 / sxx)
    t95 = float(stats.t.ppf(0.975, n - 2))
    # sensitivity: standard error of the slope clustered by country (two censuses
    # of the same country are not independent), with the small-sample correction
    X = np.column_stack([np.ones(n), fit["lg"]])
    bread = np.linalg.inv(X.T @ X)
    G = fit["country"].nunique()
    meat = sum(np.outer(X[idx].T @ resid.values[idx], X[idx].T @ resid.values[idx])
               for idx in fit.groupby("country").indices.values())
    se_b_cl = float(np.sqrt((bread @ meat @ bread)[1, 1] * G / (G - 1) * (n - 1) / (n - 2)))
    print(f"\nfull-sample income rule: tilt = {a_:+.4f} {b:+.4f} * ln(GNI)   (n = {n})")
    print(f"   intercept SE {se_a:.4f}; slope SE {se_b:.4f}, 95% CI {b - t95 * se_b:+.3f} "
          f"to {b + t95 * se_b:+.3f}; slope SE clustered by country {se_b_cl:.4f}")
    print(f"   r = {r:+.3f}   R2 = {r**2:.2f}   residual standard error = {s_e:.3f}")

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
            dict(component="income_rule", key="se_intercept", value=round(float(se_a), 4),
                 note="standard error, OLS"),
            dict(component="income_rule", key="se_slope", value=round(float(se_b), 4),
                 note="standard error, OLS"),
            dict(component="income_rule", key="slope_ci95_lo", value=round(float(b - t95 * se_b), 4),
                 note="95% confidence interval, Student's t with n - 2 df"),
            dict(component="income_rule", key="slope_ci95_hi", value=round(float(b + t95 * se_b), 4),
                 note=""),
            dict(component="income_rule", key="se_slope_cluster", value=round(se_b_cl, 4),
                 note="sensitivity: slope standard error clustered by country"),
            dict(component="income_rule", key="residual_sd", value=round(s_e, 4),
                 note="residual standard error, n - 2 df"),
            dict(component="income_rule", key="mean_ln_gni", value=round(xbar, 4),
                 note="for the prediction interval (see the script docstring)"),
            dict(component="income_rule", key="sxx_ln_gni", value=round(sxx, 4),
                 note="sum of squared deviations of ln GNI"),
            dict(component="income_rule", key="t_95", value=round(t95, 4),
                 note="Student's t, 0.975 quantile, n - 2 df"),
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
    pts = m[["country", "year", "gni", "actual", f"pred_{best}"]].rename(
        columns={"actual": "tilt_45q15", f"pred_{best}": "loo_prediction"})
    pts.sort_values("gni").to_csv(POINTS, index=False)
    print(f"wrote {POINTS}")


if __name__ == "__main__":
    main()
