# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""Adult-mortality gradients from DHS sibling survival histories.

A second, independent measurement basis for the adult-mortality tilt. The
census pipeline (build_adult_mortality.py) ranks the *deceased's own*
household by assets; this one ranks the *surviving sister's* household by the
DHS wealth index, because sibling histories are all a survey can offer. The
two disagree in a knowable direction - see "Attenuation" below - and the
overlap countries measure it.

Method (DHS Guide to DHS Statistics, "Adult Mortality Rates"):
- Each woman 15-49 reports her maternal siblings: sex (mm1), survival (mm2),
  birth date (mm4, CMC), and death date (mm8, CMC) if dead.
- Exposure and deaths are accumulated in 5-year age groups 15-19 ... 45-49
  over the 7 years (84 months) before interview, weighted by the
  respondent's sample weight v005/1e6.
- m_x = deaths / person-years;  5q_x = 5*m_x / (1 + 2.5*m_x);
  35q15 = 1 - prod(1 - 5q_x).
- The tilt is the OLS slope of ln(35q15) on wealth-rank midpoints, the same
  scale as every other tilt in this library.

Wealth: v190, the DHS household wealth quintile of the respondent. Quintiles
are population quintiles by construction, so midpoints are 0.1 ... 0.9 - the
same convention as the fertility and child-mortality tilts.

Attenuation: v190 is the *respondent's* household, not the deceased sibling's;
adult siblings usually live apart. That is measurement error in the ranking,
which biases tilts toward zero. It is not a reason to distrust the sign, and
its size is estimable where a census tilt exists for the same country.

    uv run scripts/build_adult_mortality_dhs.py selftest
    uv run scripts/build_adult_mortality_dhs.py estimate --ir-dir ~/Projects/data/dhs

Microdata (IR recode files) are free but registration-gated; they stay local,
exactly like the IPUMS extracts. Only the aggregated tilts here are published.
"""

import argparse
import glob
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "adult_mortality_dhs.csv"
AGE_GROUPS = [(15, 20), (20, 25), (25, 30), (30, 35), (35, 40), (40, 45), (45, 50)]
WINDOW_MONTHS = 84  # DHS standard reference period for adult mortality: 0-6 years
MID = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
MIN_DEATHS = 100  # per wealth group, to publish a tilt

# Surveys paired to the censuses in adult_mortality_gradients.csv, so the two
# measurement bases can be compared. Chosen as the nearest sibling-history
# survey to each census year; the gap is recorded and reported.
PAIRS = {
    "ZAIR31": dict(country="South Africa", survey_year=1998, census_year=2001),
    "ETIR51": dict(country="Ethiopia", survey_year=2005, census_year=2007),
    "ZMIR51": dict(country="Zambia", survey_year=2007, census_year=2010),
    "MWIR61": dict(country="Malawi", survey_year=2010, census_year=2008),
    "MZIR62": dict(country="Mozambique", survey_year=2011, census_year=2007),
    "UGIR41": dict(country="Uganda", survey_year=2000, census_year=2002),
    "RWIR41": dict(country="Rwanda", survey_year=2000, census_year=2002),
    "SNIR4A": dict(country="Senegal", survey_year=2005, census_year=2002),
    "SLIR51": dict(country="Sierra Leone", survey_year=2008, census_year=2004),
    "LSIR41": dict(country="Lesotho", survey_year=2004, census_year=2006),
    "BJIR71": dict(country="Benin", survey_year=2017, census_year=2013),
    "BRIR31": dict(country="Brazil", survey_year=1996, census_year=2010),
    # no census module - these are the point of the exercise
    "IDIR63": dict(country="Indonesia", survey_year=2012, census_year=None),
    "PHIR3B": dict(country="Philippines", survey_year=1998, census_year=None),
}

# DHS's own published national 35q15 per 1,000, from the API indicators
# MM_AMPB_M_AMP / MM_AMPB_W_AMP. The estimator must reproduce these before its
# wealth split can be believed.
PUBLISHED = {
    "ZAIR31": dict(male=213, female=103), "ETIR51": dict(male=207, female=217),
    "ZMIR51": dict(male=415, female=421), "MWIR61": dict(male=341, female=305),
    "MZIR62": dict(male=241, female=199), "UGIR41": dict(male=366, female=303),
    "RWIR41": dict(male=740, female=549), "SNIR4A": dict(male=128, female=114),
    "SLIR51": dict(male=218, female=186), "LSIR41": dict(male=470, female=394),
    "BJIR71": dict(male=153, female=111), "BRIR31": dict(male=125, female=53),
    "IDIR63": dict(male=97, female=80), "PHIR3B": dict(male=129, female=69),
}


def sibling_records(ir):
    """Reshape the wide sibling block (mm1_01..mm1_20, ...) to one row per sibling."""
    keep = {"v005": "w", "v008": "interview_cmc", "v190": "wealth"}
    missing = [c for c in keep if c not in ir.columns]
    assert not missing, f"IR file lacks {missing}"
    base = ir[list(keep)].rename(columns=keep)
    out = []
    for i in range(1, 21):
        cols = {f"mm1_{i:02d}": "sex", f"mm2_{i:02d}": "alive",
                f"mm3_{i:02d}": "age_now", f"mm4_{i:02d}": "birth_cmc",
                f"mm6_{i:02d}": "years_ago", f"mm7_{i:02d}": "age_at_death",
                f"mm8_{i:02d}": "death_cmc"}
        have = {k: v for k, v in cols.items() if k in ir.columns}
        if "mm1_%02d" % i not in ir.columns:
            continue
        blk = ir[list(have)].rename(columns=have)
        blk = pd.concat([base.reset_index(drop=True), blk.reset_index(drop=True)], axis=1)
        out.append(blk)
    sib = pd.concat(out, ignore_index=True)
    for c in ["sex", "alive", "age_now", "birth_cmc", "years_ago", "age_at_death",
              "death_cmc", "wealth", "w", "interview_cmc"]:
        if c in sib.columns:
            sib[c] = pd.to_numeric(sib[c], errors="coerce")
        else:
            sib[c] = np.nan
    # DHS-III-era files (e.g. PH 1998, ZA 1998, BR 1996) may lack mm8/mm4.
    # Reconstruct from what is present rather than silently scoring zero deaths.
    sib["birth_cmc"] = sib["birth_cmc"].where(
        sib["birth_cmc"].between(1, 2000),
        sib["interview_cmc"] - 12 * sib["age_now"])
    from_age = sib["birth_cmc"] + 12 * sib["age_at_death"]
    from_ago = sib["interview_cmc"] - 12 * sib["years_ago"]
    sib["death_cmc"] = (sib["death_cmc"].where(sib["death_cmc"].between(1, 2000))
                        .fillna(from_age).fillna(from_ago))
    # a real sibling record has a sex and a survival status
    sib = sib[sib["sex"].isin([1, 2]) & sib["alive"].isin([0, 1])].copy()
    sib["w"] = sib["w"] / 1e6
    return sib


def exposure_and_deaths(sib):
    """Weighted person-years and deaths per (sex, wealth, age group).

    Exposure is the overlap, in months, of the sibling's time in each age band
    with the observation window, which ends at death for those who died.
    """
    end_win = sib["interview_cmc"].to_numpy(dtype=float)
    start_win = end_win - WINDOW_MONTHS
    birth = sib["birth_cmc"].to_numpy(dtype=float)
    dead = (sib["alive"] == 0).to_numpy()
    death = sib["death_cmc"].to_numpy(dtype=float)
    # observation ends at death (if dead and dated) else at interview
    obs_end = np.where(dead & np.isfinite(death), np.minimum(death, end_win), end_win)

    rows = []
    for gi, (a0, a1) in enumerate(AGE_GROUPS):
        band_lo = birth + 12.0 * a0
        band_hi = birth + 12.0 * a1
        lo = np.maximum(band_lo, start_win)
        hi = np.minimum(band_hi, obs_end)
        months = np.clip(hi - lo, 0, None)
        # a death counts in the band containing its age, if it falls in the window
        age_at_death = (death - birth) / 12.0
        d = (dead & np.isfinite(death) & (death >= start_win) & (death < end_win)
             & (age_at_death >= a0) & (age_at_death < a1))
        rows.append(pd.DataFrame({
            "sex": sib["sex"].to_numpy(), "wealth": sib["wealth"].to_numpy(),
            "w": sib["w"].to_numpy(), "band": gi,
            "pyears": months / 12.0, "deaths": d.astype(float)}))
    e = pd.concat(rows, ignore_index=True)
    e["wpy"] = e["pyears"] * e["w"]
    e["wd"] = e["deaths"] * e["w"]
    return e


def q35_15(g):
    """35q15 from weighted deaths and person-years by age band."""
    t = g.groupby("band")[["wpy", "wd"]].sum().reindex(range(len(AGE_GROUPS)), fill_value=0.0)
    if (t["wpy"] <= 0).any():
        return np.nan, 0.0
    m = t["wd"] / t["wpy"]
    q = 5 * m / (1 + 2.5 * m)
    return float(1 - np.prod(1 - q)), float(t["wd"].sum())


def estimate_file(path, tag):
    cols_needed = None  # read everything; IR files are small enough
    ir = pd.read_stata(path, convert_categoricals=False, columns=cols_needed)
    sib = sibling_records(ir)
    e = exposure_and_deaths(sib)
    cfg = PAIRS.get(tag, {})
    rows, national = [], {}
    for sexcode, lab in [(1, "male"), (2, "female")]:
        sub = e[e["sex"] == sexcode]
        nat, nat_d = q35_15(sub)
        national[lab] = nat
        vals, ndeaths = [], []
        for q in range(1, 6):
            v, dd = q35_15(sub[sub["wealth"] == q])
            vals.append(v)
            ndeaths.append(dd)
        vals = np.array(vals, dtype=float)
        ok = np.all(np.isfinite(vals) & (vals > 0)) and min(ndeaths) >= MIN_DEATHS
        rows.append(dict(
            indicator="AMR_SIB", country=cfg.get("country", tag),
            year=cfg.get("survey_year"), sex=lab, measure="35q15",
            age_lo=15, age_hi=49,
            slope=round(float(np.polyfit(MID, np.log(vals), 1)[0]), 4) if ok else "",
            ratio=round(float(vals[0] / vals[-1]), 3) if ok else "",
            **{f"q{i+1}": (round(float(1000 * vals[i]), 3) if np.isfinite(vals[i]) else "")
               for i in range(5)},
            n_deaths=int(round(nat_d)), ranking="dhs_wealth_index_respondent",
            national_35q15=round(1000 * nat, 1) if np.isfinite(nat) else "",
            published_35q15=PUBLISHED.get(tag, {}).get(lab, ""),
            census_year=cfg.get("census_year") or "",
            source="DHS Program sibling survival histories (individual recode)",
            publishable=bool(ok)))
    return rows, national


def cmd_selftest(args):
    """Validate the exposure and life-table math against a known analytic answer.

    A synthetic population with a constant hazard mu per year has
    35q15 = 1 - exp(-35*mu) in continuous time; the discrete estimator should
    land close. This exercises the same code path the real data uses, so a
    failure here is a code bug rather than a data problem.
    """
    rng = np.random.default_rng(11)
    n = 400_000
    mu = 0.008  # per year
    interview = 1400.0  # arbitrary CMC
    # siblings uniformly aged 10-55 at interview, so all bands get exposure
    age0 = rng.uniform(10, 55, n)
    birth = interview - age0 * 12
    # exponential survival from age 15; death age is 15 + Exp(mu)
    tdeath = rng.exponential(1 / mu, n)
    death_age = 15 + tdeath
    died = death_age < age0                     # already dead by interview
    death_cmc = np.where(died, birth + death_age * 12, np.nan)
    sib = pd.DataFrame({
        "w": 1e6, "interview_cmc": interview, "wealth": rng.integers(1, 6, n),
        "sex": 1, "alive": (~died).astype(int), "birth_cmc": birth,
        "death_cmc": death_cmc})
    sib["w"] = sib["w"] / 1e6
    e = exposure_and_deaths(sib)
    got, d = q35_15(e)
    want = 1 - np.exp(-35 * mu)
    print(f"synthetic constant hazard mu={mu}/yr")
    print(f"  analytic 35q15      = {want:.4f}")
    print(f"  estimator 35q15     = {got:.4f}   ({d:,.0f} weighted deaths in window)")
    rel = abs(got - want) / want
    print(f"  relative error      = {rel:.2%}")
    # per-band hazard should recover mu
    t = e.groupby("band")[["wpy", "wd"]].sum()
    m = (t["wd"] / t["wpy"]).to_numpy()
    print(f"  per-band m_x        = {np.round(m, 5)}  (target {mu})")
    ok = rel < 0.03 and np.all(np.abs(m - mu) < 0.0015)
    print("SELFTEST:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def cmd_estimate(args):
    files = sorted(glob.glob(os.path.join(os.path.expanduser(args.ir_dir), "*.DTA")) +
                   glob.glob(os.path.join(os.path.expanduser(args.ir_dir), "*.dta")))
    if not files:
        print(f"no IR .dta files in {args.ir_dir}")
        print("Expected (unzip each DHS IR archive into that directory):")
        for tag, cfg in PAIRS.items():
            print(f"   {tag}FL.DTA   {cfg['country']} {cfg['survey_year']}")
        return 1
    rows = []
    print(f"{'survey':<10} {'sex':<7} {'national':>9} {'published':>10} {'diff':>7}  tilt")
    for f in files:
        tag = Path(f).stem[:6].upper()
        if tag not in PAIRS:
            print(f"skipping {Path(f).name}: not in PAIRS")
            continue
        r, nat = estimate_file(f, tag)
        for row in r:
            pub = row["published_35q15"]
            natv = row["national_35q15"]
            diff = (f"{natv - pub:+.0f}" if isinstance(pub, (int, float)) and pub != ""
                    and isinstance(natv, (int, float)) else "n/a")
            print(f"{tag:<10} {row['sex']:<7} {natv:>9} {pub:>10} {diff:>7}  {row['slope']}")
        rows += r
    df = pd.DataFrame(rows)
    df.to_csv(OUT, index=False)
    print(f"\nwrote {OUT} ({len(df)} rows)")
    return 0


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    e = sub.add_parser("estimate")
    e.add_argument("--ir-dir", default="~/Projects/data/dhs")
    args = ap.parse_args()
    return {"selftest": cmd_selftest, "estimate": cmd_estimate}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
