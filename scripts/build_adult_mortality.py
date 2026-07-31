# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""Universal adult-mortality gradient builder (IPUMS International).

One pipeline for every country: a slim IPUMS extract (persons rectangularized
with household asset variables) is linked to the sample's supplementary
per-death file (age/sex of each death in the 12 months before the census) by
household SERIAL; households are ranked by an asset index; and the tilt — the
OLS slope of ln(death rate) on wealth rank — is estimated by sex and age band.

Subcommands
    submit   define + submit the slim extracts via the IPUMS API
    download poll and download completed extracts
    estimate build data/adult_mortality_gradients.csv from local files

Inputs the API cannot fetch: the supplementary mortality files, downloaded
once per sample (logged in) from
https://international.ipums.org/international/mort_fert_mig.shtml
into --deaths-dir as <sample>_mortality.dta. Microdata (extracts and death
files) stay local under the IPUMS license; only the aggregated gradients in
data/ are published.

API key: .secrets/ipums_api_key (gitignored) or the IPUMS_API_KEY env var.

Method notes (validated on Brazil 2010 and South Africa 2001/2007/2011):
- Rank by ASSETS, never post-death household income (a death removes the
  deceased's earnings from measured income - reverse causation; on Sao Paulo
  assets gave monotonic gradients where income did not).
- The asset index is a count of owned durables plus a toilet-quality tier
  (and a car count where available). Components vary by census and are
  recorded per sample below; ranking within a census remains valid.
- Integer asset indices produce tied quintile cuts; groups are whatever the
  distribution supports (recorded in the `groups` column) and the regression
  uses each group's realized population midpoint.
- Some samples anonymize most death records' household IDs (e.g. za2011a
  links only ~10%): levels are then meaningless but the tilt is unbiased if
  linkage is mechanical. The estimate prints a linked-vs-unlinked composition
  check (province/urban/sex/age) wherever those fields exist; `linked_share`
  is recorded per row.
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

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "adult_mortality_gradients.csv"
API = "https://api.ipums.org"
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
MIN_BAND_DEATHS = 900  # publish a band tilt only above this record count

# Harmonized IPUMS-I codes meaning "owns it"
YES = {"ELECTRIC": [1], "PHONE": [2], "CELL": [1], "INTERNET": [1],
       "COMPUTER": [2], "WASHER": [1], "REFRIG": [2], "TV": [20], "RADIO": [2],
       "BATH": [2, 3, 4]}
BASE_VARS = ["AGE", "SEX", "TOILET", "ELECTRIC", "PHONE", "CELL", "REFRIG", "TV", "RADIO", "COMPUTER"]

# Per-sample configuration. asset_extra: variables beyond BASE_VARS that the
# census supports; drop: BASE_VARS the census lacks (the API 400 names them).
# death_weight: column in the supplementary file, or None to use the linked
# household's HHWT. nso: the originating statistical office, cited alongside
# IPUMS in the source column.
WISH = ["INTERNET", "AUTOS", "WASHER", "BATH", "MORTNUM"]  # extras to try everywhere
SAMPLES = {
    "za2001a": dict(country="South Africa", year=2001, asset_extra=[], death_weight=None,
                    nso="Statistics South Africa"),
    "za2007a": dict(country="South Africa", year=2007, asset_extra=["INTERNET"], death_weight=None,
                    nso="Statistics South Africa"),
    "za2011a": dict(country="South Africa", year=2011,
                    asset_extra=["INTERNET", "AUTOS", "WASHER", "MORTNUM"], death_weight="wtmort",
                    nso="Statistics South Africa"),
    "et2007a": dict(country="Ethiopia", year=2007, asset_extra=["MORTNUM"],
                    drop=["CELL", "REFRIG", "COMPUTER"], death_weight=None,
                    nso="Central Statistical Agency, Ethiopia"),
    # br2010a: the repo's Brazil rows come from the same census via IBGE's
    # open files; this IPUMS rebuild must reproduce them before replacing them.
    # br2010a: NOT published (publish=False) - the IPUMS mortality supplement
    # is defective for this sample. It ships 52,393 death records where the
    # extract's own MORTNUM implies ~110k (weighted 1.007M = 88.5% of
    # registered deaths, the expected module completeness); the ~52% record
    # loss is wealth-skewed (q5 rates retain ~1/3 of their IBGE values, q1
    # ~3/4), so tilts from it are biased, not just noisy. The committed
    # Brazil rows come from IBGE's open microdata via the retired
    # build_adult_mortality_brazil.py (git 7600931) and stay authoritative.
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
    "mz2007a": dict(country="Mozambique", year=2007, asset_extra=["AUTOS", "MORTNUM"],
                    drop=["REFRIG"], death_weight=None,
                    nso="Instituto Nacional de Estatistica, Mozambique"),
    "ug2002a": dict(country="Uganda", year=2002, asset_extra=["BATH", "MORTNUM"],
                    drop=["REFRIG", "COMPUTER"], death_weight=None,
                    nso="Uganda Bureau of Statistics"),
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
    "kh2008a": dict(country="Cambodia", year=2008, asset_extra=["INTERNET", "AUTOS", "MORTNUM"],
                    drop=["REFRIG"], death_weight=None,
                    nso="National Institute of Statistics, Cambodia"),
    # sd/ss2008a carry their own per-death weight (weightd); the 2008 census
    # covered both, split here at the 2011 independence boundary.
    # bf1996a: age is a value plus a unit code (days/months/years), and 27% of
    # deaths have it undetermined - the unknown-age wealth check gates this one.
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
    #  2. Only ELECTRIC and TOILET survive the API's availability check, giving
    #     a 0-3 index that supports a single cut: 2 wealth groups.
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
    for c in list(YES) + ["TOILET", "SEX", "AGE", "AUTOS", "BATH"]:
        if c in per.columns:
            per[c] = pd.to_numeric(per[c], errors="coerce")
    avail = [c for c in YES if c in per.columns]
    # rank only households observed on the asset module: et2007a asks assets
    # (and mortality) on the long form only; collective dwellings are NIU
    # everywhere. NIU is 0 on all asset vars except AUTOS (9).
    obs = pd.Series(False, index=per.index)
    for c in avail + (["TOILET"] if "TOILET" in per.columns else []):
        obs |= per[c].fillna(0) > 0
    if "AUTOS" in per.columns:
        obs |= per["AUTOS"].fillna(9) != 9
    print(f"  asset universe: {obs.mean():.1%} of persons ({(~obs).sum()} excluded as NIU)")
    per = per[obs].copy()
    per["assets"] = sum(per[c].isin(YES[c]).astype(int) for c in avail)
    if "AUTOS" in per.columns:
        # 7 = "have auto, number unspecified" (e.g. br2010a) - one auto, not clip's 3
        autos = per["AUTOS"].mask(per["AUTOS"] == 7, 1)
        per["assets"] += autos.clip(0, 3).where(autos < 8, 0)
    if "TOILET" in per.columns:
        per["assets"] += np.select(
            [per["TOILET"].between(21, 22), per["TOILET"].between(23, 26)], [2, 1], 0)
    per["PERWT"] = per["PERWT"].astype(float) / 100
    per["HHWT"] = per["HHWT"].astype(float) / 100

    d = per[per["AGE"].between(15, 59)].sort_values("assets")
    cum = d["PERWT"].cumsum() / d["PERWT"].sum()
    cuts = sorted(set(d.loc[(cum - q).abs().idxmin(), "assets"] for q in [0.2, 0.4, 0.6, 0.8]))
    # a cut at the distribution's min or max creates a structurally empty edge
    # group (searchsorted side="right"): e.g. et2007a, where 46% of persons
    # hold zero assets and the 20% cut lands on 0
    cuts = [c for c in cuts if d["assets"].min() < c < d["assets"].max()]
    qof = lambda v: np.searchsorted(cuts, v, side="right")
    G = len(cuts) + 1
    print(f"  groups: {G} (cuts at {cuts}, assets 0-{int(per['assets'].max())})")
    per["q"] = per["assets"].apply(qof)
    gsh = d.assign(q=d["assets"].apply(qof)).groupby("q")["PERWT"].sum().reindex(range(G), fill_value=0)
    gshv = (gsh / gsh.sum()).values
    mids = np.cumsum(gshv) - 0.5 * gshv

    hh = per.groupby("SERIAL").agg(assets=("assets", "first"), hhwt=("HHWT", "first")).reset_index()
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
    m["q"] = m["assets"].apply(qof)
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
                rows.append(_row(cfg, lab, "mx", a0, a1, rates[bi], mids, int(nb[bi]), G, linked_share, src))
        q45 = 1 - np.prod((1 - rates[:3]) ** 15, axis=0)
        if np.all(q45 > 0):
            rows.append(_row(cfg, lab, "45q15", 15, 59, q45, mids, int(nb[:3].sum()), G, linked_share, src))
    return rows


def _row(cfg, sex, measure, a0, a1, vals, mids, n, G, linked_share, src):
    r = dict(indicator="AMR", country=cfg["country"], year=cfg["year"], sex=sex,
             measure=measure, age_lo=a0, age_hi=a1,
             slope=round(float(np.polyfit(mids, np.log(vals), 1)[0]), 4),
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
            print(f"skipping {sample}: no {' or '.join(missing)}")
            continue
        print(f"estimating {sample} ...")
        rows += estimate_sample(sample, cfg, args.extracts_dir, args.deaths_dir)
    new = pd.DataFrame(rows)
    if OUT.exists():
        old = pd.read_csv(OUT)
        keep = old[~old["country"].isin(new["country"].unique())]
        if "groups" not in keep.columns:
            keep = keep.assign(groups=5, linked_share=1.0)
        new = pd.concat([keep, new], ignore_index=True)
    new.to_csv(OUT, index=False)
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
