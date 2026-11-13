# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""Universal adult-mortality gradient builder (IPUMS International).

One pipeline for every country: a slim IPUMS extract (persons rectangularized
with household asset variables) is linked to the sample's supplementary
per-death file (age/sex of each death in the 12 months before the census) by
household SERIAL; households are ranked by an asset index; and the wealth
gradient — the slope of ln(death rate) on wealth rank — is estimated by sex
and age band. Brazil 2010 is built separately from IBGE's own microdata by
build_adult_mortality_brazil.py (the IPUMS supplement for it fails the
completeness check below).

Subcommands
    submit   define + submit the slim extracts via the IPUMS API
    download poll and download completed extracts
    estimate build data/adult_mortality_gradients.csv from local files
             (keeps the IBGE Brazil rows already in the file)

Inputs the API cannot fetch: the supplementary mortality files, downloaded
once per sample (logged in) from
https://international.ipums.org/international/mort_fert_mig.shtml
into --deaths-dir as <sample>_mortality.dta. Microdata (extracts and death
files) stay local under the IPUMS license; only the aggregated gradients in
data/ are published.

API key: .secrets/ipums_api_key (gitignored) or the IPUMS_API_KEY env var.

Method notes:
- Rank by ASSETS, never post-death household income (a death removes the
  deceased's earnings from measured income - reverse causation; on Sao Paulo
  assets gave monotonic gradients where income did not).
- The asset index is the first principal component of household asset and
  toilet-type indicators (asset_index.py). Components vary by census and are
  recorded per sample below; ranking within a census remains valid.
- Wealth groups are cut at the population quintiles of the index; groups under
  10% are merged, and a census with fewer than MIN_GROUPS groups is not
  published (recorded in the `groups` column). The gradient is fitted on each
  group's realized population midpoint, weighted by its population share.
- Completeness check, printed for every sample with MORTNUM: weighted death
  records against the deaths households report, by wealth group. It must be
  flat; samples where it is not are set publish=False with the evidence.
- 45q15 and each age band are published only from MIN_BAND_DEATHS records.
- Some samples anonymize most death records' household IDs (za2011a links
  about 9%): `linked_share` is recorded per row. A linked-vs-unlinked
  composition comparison was made by hand for za2011a; this script does not
  run it.
- Deaths are weighted by the supplementary file's own weight where provided
  (za2011a: wtmort), else by the linked household's HHWT.
"""

import argparse
import glob
import gzip
import json
import os
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

import asset_index as ai

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "adult_mortality_gradients.csv"
API = "https://api.ipums.org"
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
MIN_BAND_DEATHS = 900  # publish a band or 45q15 gradient only from at least this many records
# column order of the published file, shared with build_adult_mortality_brazil.py
COLUMNS = ["indicator", "country", "year", "sex", "measure", "age_lo", "age_hi", "slope", "ratio",
           "q1", "q2", "q3", "q4", "q5", "n_deaths", "ranking", "source", "groups", "linked_share"]
MIN_GROUPS = 3  # a gradient needs at least three wealth groups (ruled 2026-11-11)

# Harmonized IPUMS-I codes meaning "owns it"
YES = ai.YES  # asset codes and the wealth index live in asset_index.py
BASE_VARS = ["AGE", "SEX", "TOILET", "ELECTRIC", "PHONE", "CELL", "REFRIG", "TV", "RADIO", "COMPUTER"]

# Per-sample configuration. asset_extra: variables beyond BASE_VARS that the
# census supports; drop: BASE_VARS the census lacks (the API 400 names them).
# death_weight: column in the supplementary file, or None to use the linked
# household's HHWT. nso: the originating statistical office, cited alongside
# IPUMS in the source column.
# extras to try for a new sample: start its asset_extra from this list and let
# submit's 400 retries name what the census lacks
WISH = ["INTERNET", "AUTOS", "WASHER", "BATH", "MORTNUM"]
SAMPLES = {
    "za2001a": dict(country="South Africa", year=2001, asset_extra=[], death_weight=None,
                    nso="Statistics South Africa"),
    "za2007a": dict(country="South Africa", year=2007, asset_extra=["INTERNET", "MORTNUM"], death_weight=None,
                    nso="Statistics South Africa"),
    # za2011a: NOT published (publish=False; ruled 2026-11-11). Only 9.4% of
    # death records link to a household, and the linkage varies with wealth:
    # linked / household-reported (MORTNUM) deaths by wealth group, PCA index,
    # 0.066 0.073 0.064 0.059 0.055 - deaths in the richest households are
    # under-captured by 15-20%, biasing the 45q15 gradient steep by about 0.30
    # (-1.63 uncorrected, about -1.33 corrected). Linked and unlinked deaths
    # match on population group, province, residence, sex, age and cause.
    "za2011a": dict(country="South Africa", year=2011, publish=False,
                    asset_extra=["INTERNET", "AUTOS", "WASHER", "MORTNUM"], death_weight="wtmort",
                    nso="Statistics South Africa"),
    "et2007a": dict(country="Ethiopia", year=2007, asset_extra=["MORTNUM"],
                    drop=["CELL", "REFRIG", "COMPUTER"], death_weight=None,
                    nso="Central Statistical Agency, Ethiopia"),
    # br2010a: NOT published (publish=False) - the IPUMS mortality supplement
    # is defective for this sample. It ships 52,393 death records where the
    # extract's own MORTNUM implies ~110k (weighted 1.007M = 88.5% of
    # registered deaths, the expected module completeness); the ~52% record
    # loss is wealth-skewed (q5 rates retain ~1/3 of their IBGE values, q1
    # ~3/4), so tilts from it are biased, not just noisy. The committed
    # Brazil rows come from IBGE's open microdata via
    # build_adult_mortality_brazil.py.
    "br2010a": dict(country="Brazil", year=2010, publish=False,
                    asset_extra=["INTERNET", "AUTOS", "WASHER", "BATH"],
                    drop=["TOILET"], death_weight=None,
                    nso="Instituto Brasileiro de Geografia e Estatistica (IBGE)"),
    # Comparator set for the borrowing tables. Submitted with the full wish
    # list; the API's 400s named each census's gaps (recorded below as
    # asset_extra/drop, from extracts #6-#17, 2026-07-28).
    "zm2010a": dict(country="Zambia", year=2010, asset_extra=["INTERNET", "AUTOS", "MORTNUM"],
                    death_weight=None, nso="Central Statistical Office, Zambia"),
    "mw2008a": dict(country="Malawi", year=2008, asset_extra=["AUTOS", "MORTNUM"],
                    drop=["CELL", "COMPUTER"], death_weight=None,
                    nso="National Statistical Office, Malawi"),
    # mz2007a: NOT published (publish=False; ruled 2026-11-11). Death records
    # against household-reported deaths (MORTNUM) by wealth group, PCA index,
    # relative to the mean: 0.89 1.09 0.97 1.05 - deaths in the poorest group
    # are under-recorded by about 11%, biasing the 45q15 gradient flat by about
    # 0.15 (+0.08 uncorrected, about -0.07 corrected).
    "mz2007a": dict(country="Mozambique", year=2007, publish=False,
                    asset_extra=["AUTOS", "MORTNUM"],
                    drop=["REFRIG"], death_weight=None,
                    nso="Instituto Nacional de Estatistica, Mozambique"),
    "ug2002a": dict(country="Uganda", year=2002, asset_extra=["BATH", "MORTNUM"],
                    drop=["REFRIG", "COMPUTER"], death_weight=None,
                    nso="Uganda Bureau of Statistics"),
    # rw2002a: not published under MIN_GROUPS - its asset distribution gives
    # two wealth groups once a group holding 0.1% of the population is merged.
    "rw2002a": dict(country="Rwanda", year=2002, asset_extra=["INTERNET", "AUTOS", "MORTNUM"],
                    drop=["REFRIG"], death_weight=None,
                    nso="National Institute of Statistics of Rwanda"),
    "sn2002a": dict(country="Senegal", year=2002, asset_extra=["AUTOS", "MORTNUM"],
                    drop=["CELL"], death_weight=None,
                    nso="Agence Nationale de la Statistique et de la Demographie, Senegal"),
    "sl2004a": dict(country="Sierra Leone", year=2004, asset_extra=["AUTOS", "BATH", "MORTNUM"],
                    death_weight=None, nso="Statistics Sierra Leone"),
    "ls2006a": dict(country="Lesotho", year=2006, asset_extra=["AUTOS", "MORTNUM"],
                    drop=["COMPUTER"], death_weight=None,
                    nso="Bureau of Statistics, Lesotho"),
    # bj2013a: age arrives as agedyr; the window is deaths since 1 Jan 2012
    # (~16 months to the May census) - fine for tilts, not for levels.
    "bj2013a": dict(country="Benin", year=2013, asset_extra=["INTERNET", "AUTOS", "MORTNUM"],
                    drop=["CELL"], death_weight=None, age_col="agedyr",
                    nso="Institut National de la Statistique et de l'Analyse Economique, Benin"),
    # sv2007a: NOT published. The supplement's serials carry a within-dwelling
    # suffix the extract lacks (flooring links 82.9%), and the unlinked
    # deaths are wealth-skewed - supplement/MORTNUM capture by wealth group
    # runs 0.96, 0.76, 0.75, 0.58, 0.69 (rich households' deaths missing),
    # which would bias the tilt steep. Kept for reference; do not publish.
    "sv2007a": dict(country="El Salvador", year=2007, publish=False,
                    asset_extra=["INTERNET", "AUTOS", "WASHER", "MORTNUM"],
                    drop=["RADIO"], death_weight=None, serial_floor=1000,
                    nso="Direccion General de Estadistica y Censos, El Salvador"),
    # np2001a: NOT published - 24% of supplement deaths carry serials that
    # match no extract household, and the loss is wealth-skewed
    # (supplement/MORTNUM capture by wealth group: 0.77, 0.79, 0.90, 1.13),
    # so the tilt is biased flat, not just noisy.
    "np2001a": dict(country="Nepal", year=2001, publish=False, asset_extra=["MORTNUM"],
                    drop=["PHONE", "CELL", "REFRIG", "COMPUTER"], death_weight=None,
                    nso="Central Bureau of Statistics, Nepal"),
    # kh2008a: HELD (publish=False; ruled 2026-11-11, renewed 2026-11-12)
    # until the new-source review (ROADMAP H) is finished. Passes population (13.40m) and linkage (99.8%); death coverage
    # 48% of the expected national total; the MORTNUM check passes (the death
    # file reproduces MORTNUM exactly, ratio 1.00 in every group);
    # 1,250 death records at 15-59, none of the age bands reaches 900. The
    # 45q15 gradient is -0.73 (PCA index).
    "kh2008a": dict(country="Cambodia", year=2008, publish=False,
                    asset_extra=["INTERNET", "AUTOS", "MORTNUM"],
                    drop=["REFRIG"], death_weight=None,
                    nso="National Institute of Statistics, Cambodia"),
    # sd/ss2008a carry their own per-death weight (weightd); the 2008 census
    # covered both, split here at the 2011 independence boundary.
    # bf1996a: age is a value plus a unit code (days/months/years).
    # bf1996a: NOT published (publish=False), rejected on three compounding
    # grounds, any one of which might be tolerable alone.
    #  1. The death file's serial is the DWELLING (dwelling x 1000), while the
    #     extract's SERIAL is dwelling x 1000 + a household-within-dwelling
    #     suffix (1001, 1002, 2001, ...). `serial + 1` links 100% of records,
    #     but only by assigning every death to household #1 of its dwelling -
    #     and 34.8% of dwellings hold more than one household, covering 62.2%
    #     of all households. Most deaths would be charged to a household whose
    #     assets may not be theirs, which is precisely the mis-attribution a
    #     wealth gradient cannot survive.
    #  2. Only ELECTRIC and TOILET survive the API's availability check; on the
    #     earlier additive index this supported a single cut: 2 wealth groups.
    #  3. 29.1% of death records have an undetermined age (agedcode 9/10).
    "bf1996a": dict(country="Burkina Faso", year=1996, publish=False,
                    asset_extra=["MORTNUM"],
                    drop=["PHONE", "CELL", "REFRIG", "TV", "RADIO", "COMPUTER"],
                    death_weight=None, age_col="agedx", age_unit_col="agedcode",
                    nso="Institut National de la Statistique et de la Demographie, Burkina Faso"),
    # ci1998a: death file columns arrive uppercase; agedyr codes 99 = unknown
    # (2,209 records against 7-141 at each of ages 88-98 - a 20x spike).
    # ci1998a has NO MORTNUM, so the completeness check that gates publication
    # cannot be run for it. Six asset variables survive, the best of these three.
    "ci1998a": dict(country="Cote d'Ivoire", year=1998, asset_extra=[],
                    drop=["CELL", "COMPUTER"],
                    death_weight=None, age_col="agedyr", age_unknown=[99],
                    nso="Institut National de la Statistique, Cote d'Ivoire"),
    # mw1998a: a second Malawi census, giving a within-country trend against 2008.
    # Published with a caveat (ruled 2026-11-11): only radio, electricity and
    # toilet type are recorded, and the first principal component ranks
    # flush-toilet and electrified households below latrine households, so the
    # wealth ranking rests on very little information.
    "mw1998a": dict(country="Malawi", year=1998, asset_extra=["MORTNUM"],
                    drop=["PHONE", "CELL", "REFRIG", "TV", "COMPUTER"],
                    death_weight=None,
                    nso="National Statistical Office, Malawi"),
    "sd2008a": dict(country="Sudan", year=2008, asset_extra=["AUTOS", "MORTNUM"],
                    death_weight="weightd", nso="Central Bureau of Statistics, Sudan"),
    "ss2008a": dict(country="South Sudan", year=2008, asset_extra=["AUTOS", "MORTNUM"],
                    death_weight="weightd",
                    nso="Southern Sudan Centre for Census, Statistics and Evaluation"),
}

# SAMPLE-code country prefixes (ISO numeric, zero-padded to 3 digits) used by
# find_extract_for(); extend when adding countries.
CCODE = {"za": "710", "br": "076", "et": "231", "zm": "894", "mw": "454",
         "mz": "508", "ug": "800", "rw": "646", "sn": "686", "sl": "694",
         "ls": "426", "bj": "204", "sv": "222", "np": "524", "kh": "116",
         "sd": "729", "ss": "728", "bf": "854", "ci": "384"}


def api_key():
    p = ROOT / ".secrets" / "ipums_api_key"
    key = p.read_text().strip() if p.exists() else os.environ.get("IPUMS_API_KEY", "")
    assert key, "no API key: .secrets/ipums_api_key or IPUMS_API_KEY"
    return key


def api(path, payload=None):
    req = urllib.request.Request(
        f"{API}{path}", headers={"Authorization": api_key(), "Content-Type": "application/json"},
        data=json.dumps(payload).encode() if payload else None)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        # 400 bodies name the unavailable variables - the per-sample tuning loop
        body = e.read().decode()
        sys.stderr.write(body + "\n")
        try:
            e.detail = json.loads(body).get("detail", [])
        except json.JSONDecodeError:
            e.detail = []
        raise


def cmd_submit(args):
    for sample in (args.samples or SAMPLES):
        cfg = SAMPLES[sample]
        want = [v for v in BASE_VARS if v not in cfg.get("drop", [])] + cfg["asset_extra"]
        dropped = []
        while True:
            body = {"description": f"AMR gradient: {sample}",
                    "dataStructure": {"rectangular": {"on": "P"}}, "dataFormat": "fixed_width",
                    "samples": {sample: {}}, "variables": {v: {} for v in want}}
            try:
                d = api("/extracts?collection=ipumsi&version=2", body)
                note = f" (dropped: {', '.join(dropped)} - record in SAMPLES)" if dropped else ""
                print(f"{sample}: extract #{d['number']} {d['status']}{note}")
                break
            except urllib.error.HTTPError as e:
                # drop the variables the 400 names and retry
                bad = [v for v in want if any(d.startswith(f"{v}:") or d.endswith(f" {v}")
                                              for d in getattr(e, "detail", []))]
                if e.code != 400 or not bad:
                    raise
                want = [v for v in want if v not in bad]
                dropped += bad


def cmd_download(args):
    os.makedirs(args.extracts_dir, exist_ok=True)
    todo = dict((n, None) for n in args.numbers)
    while todo:
        for n in list(todo):
            d = api(f"/extracts/{n}?collection=ipumsi&version=2")
            print(f"extract {n}: {d['status']}")
            if d["status"] == "completed":
                for k, v in d["downloadLinks"].items():
                    url = v.get("url")
                    if url:
                        req = urllib.request.Request(url, headers={"Authorization": api_key()})
                        out = Path(args.extracts_dir) / url.split("/")[-1]
                        with urllib.request.urlopen(req, timeout=900) as r, open(out, "wb") as f:
                            f.write(r.read())
                del todo[n]
        if todo:
            time.sleep(60)


def load_extract(xml_path):
    ns = "{ddi:codebook:2_5}"
    cols = {}
    for v in ET.parse(xml_path).getroot().iter(f"{ns}var"):
        loc = v.find(f"{ns}location")
        cols[v.get("ID")] = (int(loc.get("StartPos")) - 1, int(loc.get("EndPos")))
    dat = str(xml_path).replace(".xml", ".dat.gz")
    df = pd.read_fwf(dat, colspecs=list(cols.values()), names=list(cols.keys()),
                     compression="gzip", dtype=str)
    return df


def find_extract_for(sample, extracts_dir):
    """Match an extract to its sample via the SAMPLE column of the first row."""
    for xml in sorted(glob.glob(str(Path(extracts_dir) / "*.xml"))):
        # cheap probe: read first data line and check the sample id digits
        ns = "{ddi:codebook:2_5}"
        cols = {}
        for v in ET.parse(xml).getroot().iter(f"{ns}var"):
            loc = v.find(f"{ns}location")
            cols[v.get("ID")] = (int(loc.get("StartPos")) - 1, int(loc.get("EndPos")))
        with gzip.open(xml.replace(".xml", ".dat.gz"), "rt") as f:
            line = f.readline()
        s0, s1 = cols["SAMPLE"]
        code = line[s0:s1]
        want = f"{CCODE[sample[:2]]}{sample[2:6]}01"
        if code == want:
            return xml
    return None


def estimate_sample(sample, cfg, extracts_dir, deaths_dir):
    xml = find_extract_for(sample, extracts_dir)
    assert xml, f"no extract found for {sample} in {extracts_dir}"
    per = load_extract(xml)
    for c in list(ai.YES) + ["TOILET", "SEX", "AGE"]:
        if c in per.columns:
            per[c] = pd.to_numeric(per[c], errors="coerce")
    # rank only households observed on the asset module: et2007a asks assets
    # (and mortality) on the long form only; collective dwellings are NIU
    # everywhere.
    obs = ai.in_universe(per)
    print(f"  asset universe: {obs.mean():.1%} of persons ({(~obs).sum()} excluded as NIU)")
    per = per[obs].copy()
    per["PERWT"] = per["PERWT"].astype(float) / 100
    per["HHWT"] = per["HHWT"].astype(float) / 100
    # wealth index: first principal component of household asset indicators;
    # groups at the quintiles of the household population (asset_index.py)
    hidx, loadings, pc1 = ai.household_index(per)
    per = per.merge(hidx, on="SERIAL")
    cuts, group, mids, gshare = ai.wealth_groups(per["score"], per["PERWT"])
    G = len(mids)
    print(f"  wealth index: {len(loadings)} indicators, PC1 explains {pc1:.0%}; "
          f"{G} groups, shares {np.round(gshare, 3)}")
    per["q"] = group(per["score"])
    if G < MIN_GROUPS:
        print(f"  not published: {G} wealth groups, fewer than MIN_GROUPS ({MIN_GROUPS})")
        return []

    hh = per.groupby("SERIAL").agg(score=("score", "first"), hhwt=("HHWT", "first")).reset_index()
    hh["SERIAL"] = hh["SERIAL"].astype("int64")
    m = pd.read_stata(Path(deaths_dir) / f"{sample}_mortality.dta", convert_categoricals=False)
    m.columns = [c.lower() for c in m.columns]  # ci1998a ships them uppercase
    n_all = len(m)
    # Age arrives in three shapes across samples: a plain year column; a year
    # column with an unknown code (ci1998a: 99); or a value plus a unit code
    # (bf1996a: agedcode 1=days 2=months 3=years, 9/10 unknown). Decode to
    # years here so the estimator only ever sees `aged`.
    if cfg.get("age_unit_col"):
        u = pd.to_numeric(m[cfg["age_unit_col"]], errors="coerce")
        v = pd.to_numeric(m[cfg["age_col"]], errors="coerce")
        m["aged"] = np.select([u == 3, u == 2, u == 1], [v, v / 12, v / 365], np.nan)
    elif cfg.get("age_col"):
        m["aged"] = pd.to_numeric(m[cfg["age_col"]], errors="coerce")
    if cfg.get("age_unknown"):
        m.loc[m["aged"].isin(cfg["age_unknown"]), "aged"] = np.nan
    if "aged" in m.columns:
        unk = float(m["aged"].isna().mean())
        if unk > 0.02:
            print(f"  age undetermined for {unk:.1%} of death records "
                  f"- checked for wealth-uniformity below")
    m = m[m["serial"] > 0]
    n_pre = len(m)
    m = m.assign(serial=m["serial"].astype("int64"))
    if cfg.get("serial_floor"):
        m["serial"] = m["serial"] // cfg["serial_floor"] * cfg["serial_floor"]
    m = m.merge(hh, left_on="serial", right_on="SERIAL")
    # share of ALL supplement records that reached estimation (anonymized
    # serials, unmatched households and NIU exclusions all count against it)
    linked_share = len(m) / max(n_all, 1)
    print(f"  deaths: {n_all} records, {n_pre} with serial, {len(m)} matched to an "
          f"asset-universe household (linked_share {linked_share:.1%})")
    m["q"] = group(m["score"])
    if "MORTNUM" in per.columns:
        # completeness check: weighted death records against the deaths each
        # household reports (MORTNUM), by wealth group; it should be flat
        h = per.drop_duplicates("SERIAL")
        mn = pd.to_numeric(h["MORTNUM"], errors="coerce")
        rep = (mn.where(mn.between(0, 30), 0) * h["HHWT"]).groupby(h["q"]).sum()
        dw = m[cfg["death_weight"]] if cfg["death_weight"] else m["hhwt"]
        cap = (dw.groupby(m["q"]).sum() / rep).reindex(range(G))
        print(f"  completeness (death records / MORTNUM deaths) by wealth group: "
              f"{np.round(cap.values / np.nanmean(cap.values), 2)} (relative to mean)")
    else:
        print("  completeness: no MORTNUM in this census; check not possible")
    m["dw"] = m[cfg["death_weight"]] if cfg["death_weight"] else m["hhwt"]
    m["sexd"] = pd.to_numeric(m["sexd"], errors="coerce")
    m["aged"] = pd.to_numeric(m["aged"], errors="coerce")
    # Missing age is only harmless if it is wealth-uniform: a wealth-skewed
    # gap would bias the age-band tilts even when the MORTNUM check passes.
    if m["aged"].isna().any():
        share = m.groupby("q")["aged"].apply(lambda s: float(s.isna().mean()))
        print(f"  unknown-age share by wealth group: "
              f"{[round(share.get(i, 0.0), 3) for i in range(G)]}")

    src = ("IPUMS International (Ruggles et al., doi:10.18128/D020.V7.7); "
           f"original data: {cfg['nso']}")
    rows = []
    for sex, lab in [(None, "all"), (1, "male"), (2, "female")]:
        pp = per if sex is None else per[per["SEX"] == sex]
        mm = m if sex is None else m[m["sexd"] == sex]
        rates = np.full((len(BANDS), G), np.nan)
        nb = np.zeros(len(BANDS))
        for bi, (a0, a1) in enumerate(BANDS):
            e = pp[pp["AGE"].between(a0, a1)].groupby("q")["PERWT"].sum().reindex(range(G), fill_value=0).values
            dd = mm[mm["aged"].between(a0, a1)].groupby("q")["dw"].sum().reindex(range(G), fill_value=0).values
            rates[bi] = np.where(e > 0, dd / np.maximum(e, 1e-12), np.nan)
            nb[bi] = int(len(mm[mm["aged"].between(a0, a1)]))
            if nb[bi] >= MIN_BAND_DEATHS and np.all(rates[bi] > 0):
                rows.append(_row(cfg, lab, "mx", a0, a1, rates[bi], mids, gshare, int(nb[bi]), G, linked_share, src))
        q45 = 1 - np.prod((1 - rates[:3]) ** 15, axis=0)
        if nb[:3].sum() >= MIN_BAND_DEATHS and np.all(q45 > 0):
            rows.append(_row(cfg, lab, "45q15", 15, 59, q45, mids, gshare, int(nb[:3].sum()), G, linked_share, src))
    return rows


def _row(cfg, sex, measure, a0, a1, vals, mids, shares, n, G, linked_share, src):
    r = dict(indicator="AMR", country=cfg["country"], year=cfg["year"], sex=sex,
             measure=measure, age_lo=a0, age_hi=a1,
             slope=round(ai.gradient(mids, vals, shares), 4),
             ratio=round(float(vals[0] / vals[-1]), 3))
    scale = 1000
    for i in range(5):
        r[f"q{i+1}"] = round(float(scale * vals[i]), 3) if i < G else ""
    r.update(n_deaths=n, ranking="asset_index", groups=G,
             linked_share=round(linked_share, 3), source=src)
    return r


def cmd_estimate(args):
    rows = []
    for sample, cfg in SAMPLES.items():
        if not cfg.get("publish", True):
            print(f"skipping {sample}: publish=False (see config note)")
            continue
        missing = [w for w, ok in [("extract", find_extract_for(sample, args.extracts_dir)),
                                   ("death file", (Path(args.deaths_dir) / f"{sample}_mortality.dta").exists())]
                   if not ok]
        if missing:
            # fail rather than skip: every IPUMS row is rebuilt below, so a
            # missing input would silently delete that sample's published rows
            raise SystemExit(f"{sample}: no {' or '.join(missing)}; nothing written "
                             "(the published rows are unchanged)")
        print(f"estimating {sample} ...")
        rows += estimate_sample(sample, cfg, args.extracts_dir, args.deaths_dir)
    new = pd.DataFrame(rows)
    if OUT.exists():
        # keep only rows this pipeline does not produce (Brazil, from IBGE via
        # build_adult_mortality_brazil.py); every IPUMS row is rebuilt here, so
        # a sample that no longer publishes drops out of the file
        old = pd.read_csv(OUT)
        keep = old[~old["source"].astype(str).str.startswith("IPUMS")]
        if "groups" not in keep.columns:
            keep = keep.assign(groups=5, linked_share=1.0)
        # IPUMS rows first, then the rest, as build_adult_mortality_brazil.py
        # writes them, so the file is identical whichever script ran last
        new = pd.concat([new, keep], ignore_index=True)
    new[COLUMNS].to_csv(OUT, index=False)
    print(f"wrote {OUT} ({len(new)} rows)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("submit")
    s.add_argument("samples", nargs="*", help="subset of SAMPLES to submit (default: all)")
    d = sub.add_parser("download")
    d.add_argument("numbers", nargs="+", type=int)
    e = sub.add_parser("estimate")
    for p in (d, e):
        p.add_argument("--extracts-dir", default=os.path.expanduser("~/ipums-extracts"))
    e.add_argument("--deaths-dir", default=os.path.expanduser("~/Projects/data"))
    args = ap.parse_args()
    {"submit": cmd_submit, "download": cmd_download, "estimate": cmd_estimate}[args.cmd](args)


if __name__ == "__main__":
    main()
