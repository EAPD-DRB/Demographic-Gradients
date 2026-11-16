# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy", "scipy"]
# ///
"""The general adult-mortality gradient: a fallback any country can use.

A country model should use its own measured tilt when it has one. Most do not.
The observations are every 45q15 estimate in adult_mortality_gradients.csv:
censuses, and DHS surveys with a household-deaths module (India; ruled
2026-11-12 that survey rows enter the rule on the same footing).
This builds the fallback and, more importantly, shows how well it would have
served the countries that DO have a measured tilt - so a user can see what
accuracy they are accepting.

Three candidate rules are compared by leave-one-country-out prediction error:
each observation is predicted from a rule estimated without any observation of
the same country, which matches the use case of a country with no estimate of
its own. All rules are scored on the same observations (those with an income
figure); the region rule falls back to the pooled median where a region has no
other country.

    constant   one number for everyone (the pooled median)
    income     tilt ~ a + b * ln(GDP per capita, PPP)
    region     the median tilt of the country's region

The level comes from the winning rule; the by-age shape is pooled separately,
because ogcore's `mort_gradient` accepts a tilt per age band.

    uv run scripts/build_general_gradient.py

Writes data/general_gradient.csv (the rule, with its standard errors and what
is needed for a prediction interval) and data/general_gradient_points.csv (each
census or survey behind it: income, measured tilt, leave-one-out prediction).

Income is GDP per capita at purchasing-power parity in constant 2021
international dollars (World Bank NY.GDP.PCAP.PP.KD; ruled 2026-11-13), the
standard measure for comparing living standards across countries and years:
it removes both price change over time and differences in price levels
between countries. A user applies the rule to the same series for any year,
with no conversion. GNI per capita (Atlas method, current US$), the measure
used before, is kept beside it for reference. Both are read from
data/income_census_years.csv, so the fit does not change when the World Bank
revises its series (PPP values are revised with each new ICP benchmark); a
year missing from that file is fetched from the World Bank API (free, no key)
and appended with the retrieval date; `--refresh-income` re-downloads every
value.

Inference is classical OLS: standard errors from the residual standard error
with n - 2 degrees of freedom, 95% intervals from Student's t. The interval
for a country without its own estimate is the prediction interval

    pred +/- t * s * sqrt(1 + 1/n + (ln income - mean_ln_income)^2 / sxx_ln_income)

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
INCOME = ROOT / "data" / "income_census_years.csv"
LATEST_INCOME = ROOT / "data" / "income_latest.csv"
LIBRARY = ROOT / "data" / "gradient_library_latest.csv"
MICS_RAW = ROOT / "data" / "mics_quintiles_raw.csv"
MICS_NAMES = {"Congo, Rep.": "Congo", "Gambia, The": "Gambia"}  # as in build_gradient_library.py
PPP = "NY.GDP.PCAP.PP.KD"   # GDP per capita, PPP, constant 2021 international $
ATLAS = "NY.GNP.PCAP.CD"    # GNI per capita, Atlas method, current US$ (reference)
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]

# World Bank ISO3 per country in the adult-mortality file
ISO3 = {"South Africa": "ZAF", "Ethiopia": "ETH", "Brazil": "BRA", "Zambia": "ZMB",
        "Malawi": "MWI", "Mozambique": "MOZ", "Uganda": "UGA", "Rwanda": "RWA",
        "Senegal": "SEN", "Sierra Leone": "SLE", "Lesotho": "LSO", "Benin": "BEN",
        "Sudan": "SDN", "South Sudan": "SSD", "Burkina Faso": "BFA",
        "Cote d'Ivoire": "CIV", "Mali": "MLI", "India": "IND", "Colombia": "COL",
        "Bangladesh": "BGD", "Cambodia": "KHM"}
# UN/World Bank regional grouping, for the region rule
REGION = {"South Africa": "Southern Africa", "Lesotho": "Southern Africa",
          "Zambia": "Eastern Africa", "Malawi": "Eastern Africa",
          "Mozambique": "Eastern Africa", "Uganda": "Eastern Africa",
          "Rwanda": "Eastern Africa", "Ethiopia": "Eastern Africa",
          "Sudan": "Northern Africa", "South Sudan": "Eastern Africa",
          "Senegal": "Western Africa", "Sierra Leone": "Western Africa",
          "Benin": "Western Africa", "Burkina Faso": "Western Africa",
          "Cote d'Ivoire": "Western Africa", "Mali": "Western Africa",
          "Brazil": "Latin America", "Colombia": "Latin America", "India": "South Asia",
          "Bangladesh": "South Asia", "Cambodia": "South-eastern Asia"}


def wb(iso3, year, indicator="NY.GNP.PCAP.CD"):
    """The World Bank value, or None only when the API has no value for it.

    Any other failure (network, an error message in place of data) is retried
    and then raised, so a transient outage cannot silently drop an observation.
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


def census_income(need, refresh=False):
    """Income for each census or survey year, from the pinned file; fetch what is missing.

    Columns gdp_ppp (the rule's measure) and gni_atlas (reference), each with
    its retrieval date. A value the World Bank does not have (South Sudan
    2008) is stored as blank, so it is not requested again.
    """
    cols = ["country", "iso3", "year", "gdp_ppp", "gdp_ppp_retrieved", "gni_atlas",
            "gni_atlas_retrieved"]
    have = (pd.read_csv(INCOME, dtype={"gdp_ppp_retrieved": object, "gni_atlas_retrieved": object})
            if INCOME.exists() and not refresh else pd.DataFrame(columns=cols))
    today = datetime.date.today().isoformat()
    have = have.merge(need.assign(iso3=need["country"].map(ISO3)), on=["country", "year", "iso3"],
                      how="outer").reindex(columns=cols)
    fetched = 0
    for col, ind in (("gdp_ppp", PPP), ("gni_atlas", ATLAS)):
        for i in have.index[have[f"{col}_retrieved"].isna()]:
            have.loc[i, col] = wb(have.loc[i, "iso3"], int(have.loc[i, "year"]), ind)
            have.loc[i, f"{col}_retrieved"] = today
            fetched += 1
    if fetched or not INCOME.exists():
        have = have.sort_values(["country", "year"])
        have.to_csv(INCOME, index=False)
        print(f"fetched {fetched} income value(s) from the World Bank API; wrote {INCOME}")
    return have[["country", "year", "gdp_ppp", "gni_atlas"]].astype(
        {"year": int, "gdp_ppp": float, "gni_atlas": float})


def observations(refresh=False):
    """One tilt per census or survey: the 45q15 'all' row, else the mean of the sexes."""
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
    d = d.merge(census_income(d[["country", "year"]], refresh), on=["country", "year"], how="left")
    for r in d[d["gdp_ppp"].isna()].itertuples():
        print(f"no World Bank GDP per capita (PPP) for {r.country} {r.year}: excluded from the fit")
    d["lg"] = np.log(d["gdp_ppp"])
    return d


def loo_errors(d):
    """Leave-one-country-out prediction error for each candidate rule.

    A country's observations are all left out together (South Africa and
    Malawi have two censuses, India three surveys), matching the use case of a
    country with no estimate of its own. Observations without an income figure are
    dropped first, so every rule is scored on the same observations.
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


def latest_income(refresh=False):
    """Each country's most recent GDP per capita (PPP), pinned in data/income_latest.csv.

    For every country with a page (any survey gradient or adult-mortality
    estimate), the World Bank's latest non-empty value of NY.GDP.PCAP.PP.KD
    and its year, so country pages can show the general gradient's value and
    prediction interval for countries without their own estimate. Countries
    already pinned are not fetched again; --refresh-income re-fetches all.
    ISO3 codes come from the pinned file, the census list (ISO3), the MICS
    file, and otherwise the DHS API's country list.
    """
    countries = sorted(set(pd.read_csv(LIBRARY)["country"]) | set(pd.read_csv(SRC)["country"]))
    cols = ["country", "iso3", "year", "gdp_ppp", "retrieved"]
    have = (pd.read_csv(LATEST_INCOME, dtype={"retrieved": object})
            if LATEST_INCOME.exists() and not refresh else pd.DataFrame(columns=cols))
    todo = [c for c in countries if c not in set(have["country"])]
    if todo:
        iso = dict(zip(have["country"], have["iso3"]))
        iso.update(ISO3)
        m = pd.read_csv(MICS_RAW)
        iso.update(dict(zip(m["wb_country"].replace(MICS_NAMES), m["iso3"])))
        if any(c not in iso for c in todo):
            with urllib.request.urlopen("https://api.dhsprogram.com/rest/dhs/countries?f=json"
                                        "&returnFields=CountryName,ISO3_CountryCode", timeout=120) as r:
                iso.update({x["CountryName"]: x["ISO3_CountryCode"] for x in json.load(r)["Data"]})
        today = datetime.date.today().isoformat()
        # one request for every country's latest non-empty value
        url = (f"https://api.worldbank.org/v2/country/all/indicator/{PPP}"
               "?mrnev=1&format=json&per_page=500")
        for attempt in range(5):
            try:
                with urllib.request.urlopen(url, timeout=120) as r:
                    body = json.load(r)
                break
            except Exception as err:
                last = err
                time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"World Bank API failed: {last}")
        wb = {x["countryiso3code"]: (int(x["date"]), x["value"]) for x in body[1]
              if x.get("countryiso3code") and x.get("value") is not None}
        rows = []
        for c in todo:
            code = iso.get(c)
            year, value = wb.get(code, (None, None))
            rows.append(dict(country=c, iso3=code, year=year, gdp_ppp=value, retrieved=today))
            print(f"  latest income {c} ({code}): {value} ({year})")
        have = pd.concat([have, pd.DataFrame(rows)], ignore_index=True).sort_values("country")
        have.to_csv(LATEST_INCOME, index=False)
        print(f"fetched latest income for {len(todo)} countries; wrote {LATEST_INCOME}")
    return have


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--refresh-income", action="store_true",
                    help="re-download every income figure instead of using the pinned files")
    refresh = ap.parse_args().refresh_income
    latest_income(refresh)
    d = observations(refresh)
    print(f"{len(d)} observations ({d['country'].nunique()} countries)\n")
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
    print(f"{'country':<15}{'year':>6}{'GDP PPP':>8}{'measured':>10}{'general':>9}{'error':>8}")
    m = e.merge(d[["country", "year", "gdp_ppp", "gni_atlas"]], on=["country", "year"])
    for _, r in m.sort_values("gdp_ppp").iterrows():
        g = f"{r['gdp_ppp']:,.0f}" if pd.notna(r["gdp_ppp"]) else "n/a"
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
    # sensitivity: standard error of the slope clustered by country (two
    # observations of the same country are not independent), with the small-sample correction
    X = np.column_stack([np.ones(n), fit["lg"]])
    bread = np.linalg.inv(X.T @ X)
    G = fit["country"].nunique()
    meat = sum(np.outer(X[idx].T @ resid.values[idx], X[idx].T @ resid.values[idx])
               for idx in fit.groupby("country").indices.values())
    se_b_cl = float(np.sqrt((bread @ meat @ bread)[1, 1] * G / (G - 1) * (n - 1) / (n - 2)))
    print(f"\nfull-sample income rule: tilt = {a_:+.4f} {b:+.4f} * ln(GDP pc PPP)   (n = {n})")
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
    # leave one country out: each band tilt is predicted from its own 45q15 tilt
    # plus offsets estimated from the other countries only
    mx = mx[[(c, y) in q.index for c, y in zip(mx["country"], mx["year"])]].copy()
    mx["band"] = [f"{int(lo)}-{int(hi)}" for lo, hi in zip(mx["age_lo"], mx["age_hi"])]
    mx["diff"] = mx["slope"].values - q.loc[list(zip(mx["country"], mx["year"]))].values
    errs = []
    for row in mx.itertuples():
        others = mx[(mx["country"] != row.country) & (mx["band"] == row.band)]["diff"]
        if len(others):
            errs.append(abs(row.diff - others.median()))
    age_mae = float(np.median(errs))
    print(f"   adding an offset to the 45q15 tilt reproduces a measured band tilt to "
          f"+/-{age_mae:.3f} (median abs error, leaving each country out, n={len(errs)})")

    # --- write the rule out
    recs = [dict(component="income_rule", key="intercept", value=round(float(a_), 4),
                 note="tilt_45q15 = intercept + slope_ln_income * ln(GDP per capita, PPP, "
                      "constant 2021 international $; World Bank NY.GDP.PCAP.PP.KD)"),
            dict(component="income_rule", key="slope_ln_income", value=round(float(b), 4), note=""),
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
            dict(component="income_rule", key="mean_ln_income", value=round(xbar, 4),
                 note="for the prediction interval (see the script docstring)"),
            dict(component="income_rule", key="sxx_ln_income", value=round(sxx, 4),
                 note="sum of squared deviations of ln income"),
            dict(component="income_rule", key="t_95", value=round(t95, 4),
                 note="Student's t, 0.975 quantile, n - 2 df"),
            dict(component="income_rule", key="r", value=round(float(r), 3), note=""),
            dict(component="income_rule", key="n_observations", value=int(len(fit)),
                 note="censuses and surveys in the fit"),
            dict(component="validation", key=f"loo_mae_{best}", value=round(float(best_mae), 4),
                 note="leave-one-out mean absolute error of the chosen rule"),
            dict(component="fallback", key="pooled_median_tilt",
                 value=round(float(d["tilt"].median()), 4),
                 note="use when income is unavailable")]
    for band, row in shape.iterrows():
        recs.append(dict(component="age_offset", key=band, value=round(float(row["median"]), 4),
                         note="add to the 45q15 tilt to get this band's tilt"))
    recs.append(dict(component="validation", key="age_offset_mae", value=round(age_mae, 4),
                     note="median abs error of (45q15 tilt + offset) vs a measured band tilt, "
                          "offsets estimated leaving the country out"))
    for k in ("constant", "income", "region"):
        s = e[f"err_{k}"].dropna()
        recs.append(dict(component="validation", key=f"loo_mae_rule_{k}",
                         value=round(float(s.abs().mean()), 4), note=""))
    pd.DataFrame(recs).to_csv(OUT, index=False)
    print(f"\nwrote {OUT}")
    pts = m.assign(region=m["country"].map(REGION).fillna("unknown"))[
        ["country", "year", "region", "gdp_ppp", "gni_atlas", "actual", f"pred_{best}"]].rename(
        columns={"actual": "tilt_45q15", f"pred_{best}": "loo_prediction"})
    pts["gdp_ppp"] = pts["gdp_ppp"].round(0)
    pts.sort_values("gdp_ppp").to_csv(POINTS, index=False)
    print(f"wrote {POINTS}")


if __name__ == "__main__":
    main()
