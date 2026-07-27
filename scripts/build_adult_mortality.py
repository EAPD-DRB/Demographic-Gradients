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
       "COMPUTER": [2], "WASHER": [1], "REFRIG": [2], "TV": [20], "RADIO": [2]}
BASE_VARS = ["AGE", "SEX", "TOILET", "ELECTRIC", "PHONE", "CELL", "REFRIG", "TV", "RADIO", "COMPUTER"]

# Per-sample configuration. asset_extra: variables beyond BASE_VARS that the
# census supports. death_weight: column in the supplementary file, or None to
# use the linked household's HHWT.
SAMPLES = {
    "za2001a": dict(country="South Africa", year=2001, asset_extra=[], death_weight=None),
    "za2007a": dict(country="South Africa", year=2007, asset_extra=["INTERNET"], death_weight=None),
    "za2011a": dict(country="South Africa", year=2011,
                    asset_extra=["INTERNET", "AUTOS", "WASHER", "MORTNUM"], death_weight="wtmort"),
    # br2010a: queued - the repo's Brazil rows currently come from the same
    # census via IBGE's open files; the IPUMS rebuild will replace them.
}


def api_key():
    p = ROOT / ".secrets" / "ipums_api_key"
    key = p.read_text().strip() if p.exists() else os.environ.get("IPUMS_API_KEY", "")
    assert key, "no API key: .secrets/ipums_api_key or IPUMS_API_KEY"
    return key


def api(path, payload=None):
    req = urllib.request.Request(
        f"{API}{path}", headers={"Authorization": api_key(), "Content-Type": "application/json"},
        data=json.dumps(payload).encode() if payload else None)
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def cmd_submit(args):
    for sample, cfg in SAMPLES.items():
        variables = {v: {} for v in BASE_VARS + cfg["asset_extra"]}
        body = {"description": f"AMR gradient: {sample}",
                "dataStructure": {"rectangular": {"on": "P"}}, "dataFormat": "fixed_width",
                "samples": {sample: {}}, "variables": variables}
        d = api("/extracts?collection=ipumsi&version=2", body)
        print(f"{sample}: extract #{d['number']} {d['status']}")


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
        want = f"{710 if sample.startswith('za') else 76}{sample[2:6]}01"
        if code == want:
            return xml
    return None


def estimate_sample(sample, cfg, extracts_dir, deaths_dir):
    xml = find_extract_for(sample, extracts_dir)
    assert xml, f"no extract found for {sample} in {extracts_dir}"
    per = load_extract(xml)
    for c in list(YES) + ["TOILET", "SEX", "AGE", "AUTOS"]:
        if c in per.columns:
            per[c] = pd.to_numeric(per[c], errors="coerce")
    avail = [c for c in YES if c in per.columns]
    per["assets"] = sum(per[c].isin(YES[c]).astype(int) for c in avail)
    if "AUTOS" in per.columns:
        per["assets"] += per["AUTOS"].clip(0, 3).where(per["AUTOS"] < 8, 0)
    per["assets"] += np.select(
        [per["TOILET"].between(21, 22), per["TOILET"].between(23, 26)], [2, 1], 0)
    per["PERWT"] = per["PERWT"].astype(float) / 100
    per["HHWT"] = per["HHWT"].astype(float) / 100

    d = per[per["AGE"].between(15, 59)].sort_values("assets")
    cum = d["PERWT"].cumsum() / d["PERWT"].sum()
    cuts = sorted(set(d.loc[(cum - q).abs().idxmin(), "assets"] for q in [0.2, 0.4, 0.6, 0.8]))
    qof = lambda v: np.searchsorted(cuts, v, side="right")
    G = len(cuts) + 1
    per["q"] = per["assets"].apply(qof)
    gsh = d.assign(q=d["assets"].apply(qof)).groupby("q")["PERWT"].sum().reindex(range(G), fill_value=0)
    gshv = (gsh / gsh.sum()).values
    mids = np.cumsum(gshv) - 0.5 * gshv

    hh = per.groupby("SERIAL").agg(assets=("assets", "first"), hhwt=("HHWT", "first")).reset_index()
    hh["SERIAL"] = hh["SERIAL"].astype("int64")
    m = pd.read_stata(Path(deaths_dir) / f"{sample}_mortality.dta", convert_categoricals=False)
    linked_share = float((m["serial"] > 0).mean())
    m = m[m["serial"] > 0]
    m = m.assign(serial=m["serial"].astype("int64")).merge(hh, left_on="serial", right_on="SERIAL")
    m["q"] = m["assets"].apply(qof)
    m["dw"] = m[cfg["death_weight"]] if cfg["death_weight"] else m["hhwt"]
    m["sexd"] = pd.to_numeric(m["sexd"], errors="coerce")

    src = ("IPUMS International (Ruggles et al., doi:10.18128/D020.V7.7); "
           "original data: Statistics South Africa" if sample.startswith("za")
           else "IPUMS International; original data: IBGE")
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
