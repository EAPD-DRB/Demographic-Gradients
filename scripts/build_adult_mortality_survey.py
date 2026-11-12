# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy", "pyreadstat"]
# ///
"""Adult-mortality gradients from DHS household-reported deaths.

A few DHS-type surveys ask the household respondent about every usual member
who died during a recent period, with sex, age at death and date of death:
the same design as the census household-deaths module, collected in a survey.
This script estimates the wealth gradient from those records, in the units of
build_adult_mortality.py, and adds the rows to
data/adult_mortality_gradients.csv. It is unrelated to sibling survival
histories (build_adult_mortality_dhs.py), which were rejected.

Method
- Deaths: records whose date of death falls in the WINDOW_MONTHS months before
  the month of interview (months 0..WINDOW_MONTHS-1 back, the interview month
  included). Records without a usable date or age are excluded; their share is
  printed by wealth quintile.
- Exposure: the weighted de jure household population (hv102 == 1) by age, sex
  and wealth quintile, multiplied by WINDOW_MONTHS / 12 to give person-years;
  the census estimates use the population at the census the same way.
- Wealth: the DHS wealth-index quintile (hv270, or the separate wealth-index
  file for surveys that predate it). Quintiles are of the de jure household
  population, so each group is at its midpoint 0.1 ... 0.9 with equal weights
  and the fit is ordinary least squares.
- Weights: hv005 / 1e6.
- Band rates, 45q15 and the publication minimum (MIN_BAND_DEATHS records) are
  as in build_adult_mortality.py.

Checks printed for every survey (none is a published quantity):
- recorded deaths against the household's reported number of deaths, by
  quintile (records cut off by the questionnaire's slots would show here);
- recall: adult deaths 12-23 months back over deaths 0-11 months back, by
  quintile, relative to the mean; wealth-skewed forgetting shows as a trend;
- unknown date and unknown age shares by quintile;
- age heaping (share of adult ages at death ending in 0 or 5) by quintile, and
  the 45q15 gradient with persons and deaths at exactly 15, 30, 45 and 60 split
  half and half across the band boundary;
- the national 45q15 by sex, to compare with UN / World Bank estimates;
- a cluster bootstrap standard error of the 45q15 gradient (PSUs resampled
  within strata).

Microdata: the household recode (HR) .DTA of each survey, downloaded once
(logged in) from https://dhsprogram.com into --dhs-dir, where it is found by
file name anywhere below. Microdata stay local under the DHS terms of use;
only the aggregated gradients in data/ are published.

    uv run scripts/build_adult_mortality_survey.py --dhs-dir ~/Projects/data/dhs
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyreadstat

import asset_index as ai

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "adult_mortality_gradients.csv"
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
MIN_BAND_DEATHS = 900  # as in build_adult_mortality.py
WINDOW_MONTHS = 24  # ruled 2026-11-12: two years before interview; recall falls off beyond
MID = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
SHARES = np.full(5, 0.2)
ROSTER_MAX = 99  # roster slots probed: hv102_01 ... (only those present are read)
BOOT_REPS, BOOT_SEED = 200, 1
# column order of the published file, as in build_adult_mortality.py
COLUMNS = ["indicator", "country", "year", "sex", "measure", "age_lo", "age_hi", "slope", "ratio",
           "q1", "q2", "q3", "q4", "q5", "n_deaths", "ranking", "source", "groups", "linked_share"]
SRC_PREFIX = "The DHS Program"

# Per-survey layout of the household-deaths module; `{i}` is the death slot.
# Age at death is either a unit and a number (age_unit, age_num) or one code
# whose hundreds digit is the unit (age_code; Pakistan: 1xx days, 2xx months,
# 3xx years). age_units maps a unit code to its divisor to years; any other
# unit, or a value in age_unknown, is unknown. Year of death is stored with
# year_offset added (two-digit years in NFHS-1). Where visitors' deaths are
# also recorded, `resident` selects usual members, matching the de jure
# denominator. `wealth` is the quintile column, or the separate wealth-index
# file (matched on household id) for surveys that predate hv270. `reported`
# is the household's own count of the deaths recorded (usual members).
AGE_UNITS = {1: 365, 2: 12, 3: 1}
IIPS = "International Institute for Population Sciences (IIPS), Mumbai"
SURVEYS = {
    "IAHR23": dict(
        country="India", year=1993, survey="NFHS-1 1992-93", org=IIPS, file="IAHR23FL.DTA",
        # deaths in the two years before interview, residents and visitors
        reported="sh059", slots=10, resident="sh064_{i:02d}",
        sex="sh065_{i:02d}", age_unit="sh066u_{i:02d}", age_num="sh066n_{i:02d}",
        month="sh067m_{i:02d}", year_d="sh067y_{i:02d}", year_offset=1900,
        age_unknown=[98], year_unknown=[98, 99],
        wealth=dict(file="IAWI22FL.DTA", id="whhid", q="wlthind5"),
        # Not published: the age-at-death number (sh066n) is blank for every
        # record in the released recode - DHS's own frequency file lists all
        # 885,620 occurrences as not applicable - so no death has an age.
        publish=False,
    ),
    "IAHR42": dict(
        country="India", year=1999, survey="NFHS-2 1998-99", org=IIPS, file="IAHR42FL.DTA",
        # deaths of usual members since January 1996
        reported="sh52", slots=4,
        sex="sh54_{i}", age_unit="sh55u_{i}", age_num="sh55n_{i}",
        month="sh56m_{i}", year_d="sh56y_{i}",
        age_unknown=[98], year_unknown=[9998],
        wealth=dict(file="IAWI41FL.DTA", id="whhid", q="wlthind5"),
    ),
    "IAHR74": dict(
        country="India", year=2015, survey="NFHS-4 2015-16", org=IIPS, file="IAHR74FL.DTA",
        # "any usual member died since January 2011" by its label; the
        # recorded dates begin in 2012 (20 of 74,945 records in 2011).
        reported="sh71", slots=5,
        sex="sh73_{i}", age_unit="sh74u_{i}", age_num="sh74n_{i}",
        month="sh75m_{i}", year_d="sh75y_{i}",
        age_unknown=[98], year_unknown=[9998], wealth="hv270",
    ),
    "IAHR7E": dict(
        country="India", year=2020, survey="NFHS-5 2019-21", org=IIPS, file="IAHR7EFL.DTA",
        # fieldwork June 2019 - April 2021, paused March-November 2020; the
        # 24-month window of later interviews covers the first COVID-19 wave
        reported="sh88", slots=5,
        sex="sh90_{i}", age_unit="sh92u_{i}", age_num="sh92n_{i}",
        month="sh93m_{i}", year_d="sh93y_{i}",
        age_unknown=[98], year_unknown=[9998], wealth="hv270",
        censor_cmc=(2020 - 1900) * 12 + 3,
    ),
    "PKHR53": dict(
        country="Pakistan", year=2006, survey="DHS 2006-07",
        org="National Institute of Population Studies (NIPS), Islamabad", file="PKHR53FL.DTA",
        # deaths since January 2003, residents and visitors
        reported="shdeaths", slots=6, resident="sh31a_{i}",
        sex="sh31_{i}", age_code="sh33_{i}", month="sh32m_{i}", year_d="sh32y_{i}",
        age_unknown=[998], year_unknown=[9998], wealth="hv270",
        # Not published: deaths were recorded in all 95,441 households, but
        # assets (and hv270) only in the 13,844 given the full DHS
        # questionnaire; those hold 848 deaths at 15-59 in the window, under
        # MIN_BAND_DEATHS, and 698 of them are women's (maternal-mortality
        # focus), so the records are not a sample of all adult deaths.
        publish=False,
    ),
}
FIELDS = ("sex", "age_unit", "age_num", "age_code", "month", "year_d", "resident")


def find(dhs_dir, name):
    hits = sorted(Path(dhs_dir).expanduser().rglob(name))
    return hits[0] if hits else None


def load(cfg, path, dhs_dir):
    _, meta = pyreadstat.read_dta(str(path), metadataonly=True)
    have = set(meta.column_names)
    wq = cfg["wealth"] if isinstance(cfg["wealth"], str) else None
    cols = ["hhid", "hv005", "hv008", "hv021", "hv022", cfg["reported"]] + ([wq] if wq else [])
    for s in range(1, ROSTER_MAX + 1):
        for v in ("hv102", "hv104", "hv105"):
            if f"{v}_{s:02d}" in have:
                cols.append(f"{v}_{s:02d}")
    for i in range(1, cfg["slots"] + 1):
        cols += [cfg[k].format(i=i) for k in FIELDS if k in cfg]
    missing = [c for c in cols if c not in have]
    assert not missing, f"{path.name}: missing {missing}"
    h, _ = pyreadstat.read_dta(str(path), usecols=cols, apply_value_formats=False)
    # some older recodes (NFHS-1) store numeric codes in object columns
    h = pd.concat([h[["hhid"]], h[cols[1:]].apply(pd.to_numeric, errors="coerce")], axis=1)
    if wq:
        h["q"] = h[wq]
    else:
        w = cfg["wealth"]
        wp = find(dhs_dir, w["file"])
        assert wp, f"{w['file']} not found under {dhs_dir}"
        wi, _ = pyreadstat.read_dta(str(wp), usecols=[w["id"], w["q"]], apply_value_formats=False)
        wi = wi.assign(hhid=wi[w["id"]].str.strip()).set_index("hhid")[w["q"]]
        h["q"] = h["hhid"].str.strip().map(wi)
        print(f"  wealth quintile from {w['file']}: {h['q'].notna().mean():.1%} of households matched")
    h = h[h["q"].between(1, 5)].copy()
    h["q"] = h["q"].astype(int)
    h["w"] = h["hv005"] / 1e6
    h["hh"] = np.arange(len(h))
    return h


def persons(h):
    """De jure household members, one row each, with the household's weight and quintile."""
    out = []
    for s in range(1, ROSTER_MAX + 1):
        c = f"hv102_{s:02d}"
        if c not in h.columns:
            continue
        p = h[["hh", "hv021", "hv022", "hv008", "w", "q", c, f"hv104_{s:02d}", f"hv105_{s:02d}"]]
        p.columns = ["hh", "psu", "strat", "cmc_int", "w", "q", "res", "sex", "age"]
        out.append(p[(p["res"] == 1) & (p["age"] < 95)])  # top and don't-know codes start at 95-98
    return pd.concat(out, ignore_index=True)


def deaths(h, cfg):
    """One row per death record of a usual member, with age in years and months before interview."""
    out = []
    for i in range(1, cfg["slots"] + 1):
        k = {key: cfg[key].format(i=i) for key in FIELDS if key in cfg}
        d = h[["hh", "hv021", "hv022", "w", "q", "hv008"] + list(k.values())].copy()
        d.columns = ["hh", "psu", "strat", "w", "q", "cmc_int"] + list(k)
        out.append(d[d[["sex", "month", "year_d"]].notna().any(axis=1)])
    d = pd.concat(out, ignore_index=True)
    if "resident" in d:
        print(f"  visitors' deaths excluded: {int((d['resident'] != 1).sum())} records")
        d = d[d["resident"] == 1]
    if "age_code" in d:
        unknown = d["age_code"].isin(cfg["age_unknown"])
        unit, num = d["age_code"] // 100, d["age_code"] % 100
    else:
        unknown = d["age_num"].isin(cfg["age_unknown"])
        unit, num = d["age_unit"], d["age_num"]
    div = unit.map(AGE_UNITS)
    d["age"] = np.where(unknown | div.isna(), np.nan, num / div)
    dy = d["year_d"] + cfg.get("year_offset", 0)
    ok = d["month"].between(1, 12) & ~d["year_d"].isin(cfg["year_unknown"]) & d["year_d"].notna()
    d["mago"] = np.where(ok, d["cmc_int"] - ((dy - 1900) * 12 + d["month"]), np.nan)
    return d.reset_index(drop=True)


def band_rates(p, d, years):
    """Death rate by age band (rows) and wealth quintile (columns)."""
    R, N = np.zeros((len(BANDS), 5)), np.zeros(len(BANDS), dtype=int)
    py = p["w"] * years  # person-years; years is a scalar or a per-person Series
    for b, (a0, a1) in enumerate(BANDS):
        inb = p["age"].between(a0, a1)
        e = py[inb].groupby(p.loc[inb, "q"]).sum().reindex(range(1, 6), fill_value=0).values
        x = d[(d["age"] >= a0) & (d["age"] < a1 + 1)]
        R[b] = x.groupby("q")["w"].sum().reindex(range(1, 6), fill_value=0).values / e
        N[b] = len(x)
    return R, N


def q45(R):
    return 1 - np.prod((1 - R[:3]) ** 15, axis=0)


def checks(h, p, d, cfg, win):
    rep = pd.to_numeric(h[cfg["reported"]], errors="coerce").astype(float)
    rep = (rep.where(rep.between(0, 50), 0) * h["w"]).groupby(h["q"]).sum()
    rec = d.groupby("q")["w"].sum()
    print(f"  death records / reported deaths by quintile: {np.round((rec / rep).values.astype(float), 3)}")
    a = d[(d["age"] >= 15) & (d["age"] < 60)]
    r = a[a["mago"].between(12, 23)].groupby("q")["w"].sum() / a[a["mago"].between(0, 11)].groupby("q")["w"].sum()
    print(f"  recall, adult deaths 12-23 / 0-11 months back, relative to mean: {np.round((r / r.mean()).values, 3)}")
    print(f"  unknown date share by quintile: {np.round(d.groupby('q')['mago'].apply(lambda s: s.isna().mean()).values, 4)}")
    print(f"  unknown age share by quintile:  {np.round(d.groupby('q')['age'].apply(lambda s: s.isna().mean()).values, 4)}")
    ya = win[(win["age"] >= 15) & (win["age"] < 75) & (win["age"] % 1 == 0)]
    print(f"  age heaping (adult ages at death ending 0/5) by quintile: "
          f"{np.round(ya.groupby('q')['age'].apply(lambda s: (s % 5 == 0).mean()).values, 3)}")
    # heaping sensitivity: exact ages 15, 30, 45, 60 split half and half across the boundary
    years = WINDOW_MONTHS / 12

    def soft(df, a0, a1):
        x = df[(df["age"] > a0) & (df["age"] < a1 + 1)].groupby("q")["w"].sum()
        x = x.add(df[df["age"] == a0].groupby("q")["w"].sum() * 0.5, fill_value=0)
        x = x.add(df[df["age"] == a1 + 1].groupby("q")["w"].sum() * 0.5, fill_value=0)
        return x.reindex(range(1, 6), fill_value=0).values
    R = np.array([soft(win, a0, a1) / (soft(p, a0, a1) * years) for a0, a1 in BANDS[:3]])
    print(f"  45q15 gradient with boundary ages split: {ai.gradient(MID, q45(R), SHARES):+.3f}")
    for sx, lab in [(1, "male"), (2, "female")]:
        with np.errstate(invalid="ignore", divide="ignore"):  # quintiles 2-5 empty here
            Rn, _ = band_rates(p[p["sex"] == sx].assign(q=1), win[win["sex"] == sx].assign(q=1), years)
        print(f"  national 45q15, {lab}: {1000 * q45(Rn)[0]:.0f} per 1,000")
    if cfg.get("censor_cmc"):
        # deaths and exposure before a date only (NFHS-5: COVID-19 from March 2020)
        c = cfg["censor_cmc"]
        yrs = np.clip(c - (p["cmc_int"] - (WINDOW_MONTHS - 1)), 0, WINDOW_MONTHS) / 12
        pre = win[(win["cmc_int"] - win["mago"]) < c]
        R, N = band_rates(p, pre, yrs)
        print(f"  45q15 gradient from deaths and exposure before CMC {c} only: "
              f"{ai.gradient(MID, q45(R), SHARES):+.3f} ({N[:3].sum()} records; "
              f"{(yrs * p['w']).sum() / (p['w'].sum() * WINDOW_MONTHS / 12):.0%} of exposure)")
        R, N = band_rates(p, win[(win["cmc_int"] - win["mago"]) >= c], WINDOW_MONTHS / 12 - yrs)
        print(f"  45q15 gradient from deaths and exposure from CMC {c} on: "
              f"{ai.gradient(MID, q45(R), SHARES):+.3f} ({N[:3].sum()} records)")
    # cluster bootstrap of the all-sex 45q15 gradient
    bands = [14.5, 29.5, 44.5, 59.5]
    pe = p.assign(b=pd.cut(p["age"], bands, labels=False)).dropna(subset=["b"])
    de = win[(win["age"] >= 15) & (win["age"] < 60)].assign(b=lambda x: np.floor((x["age"] - 15) / 15))
    E = pe.groupby(["psu", "q", "b"])["w"].sum().unstack(["q", "b"], fill_value=0).sort_index(axis=1)
    D = (de.groupby(["psu", "q", "b"])["w"].sum().unstack(["q", "b"], fill_value=0)
         .reindex(index=E.index, columns=E.columns, fill_value=0))
    strat = h.groupby("hv021")["hv022"].first().reindex(E.index).values
    Ev, Dv = E.values, D.values

    def g(ix):
        R = (Dv[ix].sum(0) / (Ev[ix].sum(0) * years)).reshape(5, 3).T
        return ai.gradient(MID, q45(R), SHARES)
    rng = np.random.default_rng(BOOT_SEED)
    groups = [np.flatnonzero(strat == s) for s in np.unique(strat)]
    bs = [g(np.concatenate([gr[rng.integers(0, len(gr), len(gr))] for gr in groups]))
          for _ in range(BOOT_REPS)]
    print(f"  45q15 gradient {g(np.arange(len(E))):+.3f}, cluster bootstrap SE {np.std(bs):.3f} "
          f"({BOOT_REPS} replicates, PSUs resampled within strata)")


def estimate(code, cfg, dhs_dir):
    if not cfg.get("publish", True):
        print(f"skipping {code} ({cfg['country']} {cfg['survey']}): publish=False (see config note)")
        return []
    path = find(dhs_dir, cfg["file"])
    if path is None:
        print(f"skipping {code}: {cfg['file']} not found under {dhs_dir}")
        return []
    print(f"estimating {code} ({cfg['country']} {cfg['survey']}) from {path}")
    h = load(cfg, path, dhs_dir)
    p, d = persons(h), deaths(h, cfg)
    win = d[d["mago"].between(0, WINDOW_MONTHS - 1)]
    print(f"  {len(h):,} households, {len(p):,} de jure persons; {len(d):,} death records, "
          f"{len(win):,} in the {WINDOW_MONTHS} months before interview")
    print(f"  person share by quintile: {np.round(p.groupby('q')['w'].sum().values / p['w'].sum(), 3)}")
    checks(h, p, d, cfg, win)
    src = (f"{SRC_PREFIX}, {cfg['country']} {cfg['survey']}, household deaths module; "
           f"original data: {cfg['org']}")
    rows = []
    for sx, lab in [(None, "all"), (1, "male"), (2, "female")]:
        pp = p if sx is None else p[p["sex"] == sx]
        dd = win if sx is None else win[win["sex"] == sx]
        R, N = band_rates(pp, dd, WINDOW_MONTHS / 12)
        for b, (a0, a1) in enumerate(BANDS):
            if N[b] >= MIN_BAND_DEATHS and np.all(R[b] > 0):
                rows.append(row(cfg, lab, "mx", a0, a1, R[b], N[b], src))
        if N[:3].sum() >= MIN_BAND_DEATHS and np.all(q45(R) > 0):
            rows.append(row(cfg, lab, "45q15", 15, 59, q45(R), N[:3].sum(), src))
    return rows


def row(cfg, sex, measure, a0, a1, vals, n, src):
    r = dict(indicator="AMR", country=cfg["country"], year=cfg["year"], sex=sex,
             measure=measure, age_lo=a0, age_hi=a1,
             slope=round(ai.gradient(MID, vals, SHARES), 4),
             ratio=round(float(vals[0] / vals[-1]), 3))
    for i in range(5):
        r[f"q{i+1}"] = round(float(1000 * vals[i]), 3)
    r.update(n_deaths=int(n), ranking="dhs_wealth_index", source=src, groups=5, linked_share=1.0)
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dhs-dir", default="~/Projects/data/dhs")
    args = ap.parse_args()
    rows = []
    for code, cfg in SURVEYS.items():
        rows += estimate(code, cfg, args.dhs_dir)
    new = pd.DataFrame(rows, columns=COLUMNS)
    old = pd.read_csv(OUT)
    keep = old[~old["source"].astype(str).str.startswith(SRC_PREFIX)]
    # survey rows last, after the census rows, as the census scripts preserve them
    pd.concat([keep, new], ignore_index=True)[COLUMNS].to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(new)} survey rows)")


if __name__ == "__main__":
    main()
