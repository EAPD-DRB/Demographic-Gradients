# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""Child mortality by wealth from census microdata (IPUMS International).

Why this exists: the DHS child-mortality gradients in `gradient_library.csv`
are one survey per country, and for some countries that survey is decades old.
Brazil's only usable DHS is 1996. Censuses ask every mother how many children
she has borne (CHBORN) and how many are still alive (CHSURV), so the same
household asset index used for adult mortality yields a child-mortality
gradient for any census year - including years no survey covers.

Measure: the proportion of children ever born who have died, the classic Brass
indirect indicator. It is *cumulative*, not a period rate, so it is sensitive
to the mother's age - older mothers' children have been exposed longer. Three
variants are published per census:

    prop_dead_2529    women aged 25-29 only, the standard Brass age group
    prop_dead_agestd  computed within 5-year maternal age groups (20-39) and
                      averaged with equal weights, so wealth groups are
                      compared at the same age structure
    prop_dead_all     all mothers 15-49, no age control (most affected by
                      composition; published for transparency, not for use)

Validated against DHS: Brazil's 2000 census, four years after its 1996 DHS,
gives a `prop_dead_2529` tilt of -1.449 where the DHS U5MR tilt is -1.463 - a
difference of 0.014, from two independent sources with different measures and
different wealth rankings. That agreement is why these rows are publishable.

What the tilt is NOT: a period U5MR gradient. Levels are not comparable to
DHS U5MR levels and are not published as such; only the tilt is comparable,
and only approximately. Do not pool these rows with the DHS rows.

Ranking follows the repo's census conventions: an asset index, the observed
asset universe only, weighted quantile cuts with edge cuts dropped, and each
group's realized population midpoint in the regression.

    uv run scripts/build_census_child_mortality.py

Writes data/census_child_mortality.csv. Microdata stays local under the IPUMS
license; only these aggregates are published.
"""

import argparse
import gzip
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "census_child_mortality.csv"

# Harmonized IPUMS-I codes meaning "owns it" - same convention as
# build_adult_mortality.py, kept in step deliberately.
YES = {"ELECTRIC": [1], "PHONE": [2], "CELL": [1], "INTERNET": [1],
       "COMPUTER": [2], "WASHER": [1], "REFRIG": [2], "TV": [20], "RADIO": [2],
       "BATH": [2, 3, 4]}
AGE_BANDS = [(20, 24), (25, 29), (30, 34), (35, 39)]

CCODE = {"br": "076"}
SAMPLES = {
    "br1991a": dict(country="Brazil", year=1991,
                    nso="Instituto Brasileiro de Geografia e Estatistica (IBGE)"),
    "br2000a": dict(country="Brazil", year=2000,
                    nso="Instituto Brasileiro de Geografia e Estatistica (IBGE)"),
    "br2010a": dict(country="Brazil", year=2010,
                    nso="Instituto Brasileiro de Geografia e Estatistica (IBGE)"),
}
# The DHS survey each census is checked against, where one exists nearby.
DHS_CHECK = {"br2000a": dict(survey="Brazil 1996 DHS", u5mr_tilt=-1.4634)}


def _cols(xml):
    ns = "{ddi:codebook:2_5}"
    out = {}
    for v in ET.parse(xml).getroot().iter(f"{ns}var"):
        loc = v.find(f"{ns}location")
        out[v.get("ID")] = (int(loc.get("StartPos")) - 1, int(loc.get("EndPos")))
    return out


def find_extract_for(sample, extracts_dir):
    """Best extract for a sample: has CHBORN/CHSURV, and the most asset variables.

    More than one extract can match a sample; a thin one produces a coarse
    asset index and too few wealth groups, so richness is the tie-breaker.
    """
    want = f"{CCODE[sample[:2]]}{sample[2:6]}01"
    best, best_n = None, -1
    for xml in sorted(Path(extracts_dir).glob("*.xml")):
        cols = _cols(xml)
        if not {"CHBORN", "CHSURV", "SAMPLE"} <= set(cols):
            continue
        with gzip.open(str(xml).replace(".xml", ".dat.gz"), "rt") as f:
            line = f.readline()
        s0, s1 = cols["SAMPLE"]
        if line[s0:s1] != want:
            continue
        n = sum(1 for c in list(YES) + ["AUTOS"] if c in cols)
        if n > best_n:
            best, best_n = xml, n
    return best


def load_extract(xml):
    """Read only the columns the estimate uses - the fixed-width parse dominates."""
    cols = _cols(xml)
    need = [c for c in (["PERWT", "SEX", "AGE", "CHBORN", "CHSURV", "AUTOS"]
                        + list(YES)) if c in cols]
    df = pd.read_fwf(str(xml).replace(".xml", ".dat.gz"),
                     colspecs=[cols[c] for c in need], names=need,
                     compression="gzip", dtype=str)
    for c in need:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["PERWT"] = df["PERWT"] / 100
    return df


def assets_available(xml):
    """Which asset variables an extract carries, from the DDI alone (cheap)."""
    cols = _cols(xml)
    return [c for c in list(YES) + ["AUTOS"] if c in cols]


def wealth_groups(per, yesmap=None):
    """Asset index -> groups, on the repo's census conventions."""
    yesmap = yesmap or YES
    avail = [c for c in yesmap if c in per.columns]
    obs = pd.Series(False, index=per.index)
    for c in avail:
        obs |= per[c].fillna(0) > 0
    if "AUTOS" in per.columns:
        obs |= per["AUTOS"].fillna(9) != 9
    per = per[obs].copy()
    per["assets"] = sum(per[c].isin(yesmap[c]).astype(int) for c in avail)
    if "AUTOS" in per.columns:  # code 7 = "has a car, count unspecified"
        a = per["AUTOS"].mask(per["AUTOS"] == 7, 1)
        per["assets"] += a.clip(0, 3).where(a < 8, 0)
    base = per.sort_values("assets")
    cum = base["PERWT"].cumsum() / base["PERWT"].sum()
    cuts = sorted({base.loc[(cum - q).abs().idxmin(), "assets"] for q in (.2, .4, .6, .8)})
    cuts = [c for c in cuts if base["assets"].min() < c < base["assets"].max()]
    G = len(cuts) + 1
    per["q"] = np.searchsorted(cuts, per["assets"], side="right")
    sh = per.groupby("q")["PERWT"].sum().reindex(range(G), fill_value=0)
    shv = (sh / sh.sum()).values
    return per, G, np.cumsum(shv) - 0.5 * shv, avail


def estimate_sample(sample, cfg, extracts_dir, common=None):
    """Rows for one census, on the full index and (if given) a common-core index.

    `common` is the set of asset variables shared by every census of this
    country. Estimating on it as well is the robustness check for a trend: if a
    change over time only appears on the full index, it may be an artefact of
    the index getting richer rather than of real convergence.
    """
    xml = find_extract_for(sample, extracts_dir)
    if xml is None:
        print(f"skipping {sample}: no extract with CHBORN/CHSURV")
        return []
    per = load_extract(xml)  # loaded once; both index variants reuse it
    src = ("IPUMS International (Ruggles et al., doi:10.18128/D020.V7.7); "
           f"original data: {cfg['nso']}")
    rows = []
    variants = [("full", YES)]
    if common:
        variants.append(("common", {k: v for k, v in YES.items() if k in common}))
    for index_label, yesmap in variants:
        d, G, mids, avail = wealth_groups(per, yesmap)
        print(f"  [{index_label}] {len(avail)} asset vars -> {G} groups, "
              f"midpoints {np.round(mids, 3)}")
        w = d[(d["SEX"] == 2) & d["AGE"].between(15, 49)
              & d["CHBORN"].between(0, 30) & d["CHSURV"].between(0, 30)].copy()
        w["born"] = w["CHBORN"] * w["PERWT"]
        w["surv"] = w["CHSURV"] * w["PERWT"]

        def pd_(x):
            b = x["born"].sum()
            return (b - x["surv"].sum()) / b if b > 0 else np.nan

        measures = {
            "prop_dead_2529": [pd_(w[(w["q"] == q) & w["AGE"].between(25, 29)])
                               for q in range(G)],
            "prop_dead_agestd": [np.nanmean([pd_(w[(w["q"] == q) & w["AGE"].between(a, b)])
                                             for a, b in AGE_BANDS]) for q in range(G)],
            "prop_dead_all": [pd_(w[w["q"] == q]) for q in range(G)],
        }
        for measure, vals in measures.items():
            v = np.asarray(vals, float)
            if not np.all(np.isfinite(v) & (v > 0)):
                print(f"      {measure}: incomplete, skipped")
                continue
            n_moth = int(len(w[w["AGE"].between(25, 29)])
                         if measure == "prop_dead_2529" else len(w))
            r = dict(indicator="CHMORT_CENSUS", country=cfg["country"],
                     year=cfg["year"], measure=measure, index=index_label,
                     slope=round(float(np.polyfit(mids, np.log(v), 1)[0]), 4),
                     ratio=round(float(v[0] / v[-1]), 3))
            for i in range(5):
                r[f"q{i + 1}"] = round(float(v[i]), 5) if i < G else ""
            r.update(n_mothers=n_moth, ranking="asset_index", groups=G,
                     asset_vars=" ".join(avail), source=src)
            chk = DHS_CHECK.get(sample)
            r["dhs_check"] = (f"{chk['survey']} U5MR tilt {chk['u5mr_tilt']:+.4f}"
                              if chk and measure == "prop_dead_2529"
                              and index_label == "full" else "")
            rows.append(r)
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--extracts-dir", default=os.path.expanduser("~/ipums-extracts"))
    args = ap.parse_args()
    # the common core per country: assets present in every census of it
    core = {}
    for s, cfg in SAMPLES.items():
        xml = find_extract_for(s, args.extracts_dir)
        if xml is None:
            continue
        a = set(assets_available(xml))
        core[cfg["country"]] = a if cfg["country"] not in core else core[cfg["country"]] & a
    for c, a in core.items():
        print(f"common asset core for {c}: {sorted(a)}")

    rows = []
    for sample, cfg in SAMPLES.items():
        print(f"estimating {sample} ...")
        rows += estimate_sample(sample, cfg, args.extracts_dir,
                                common=core.get(cfg["country"]))
    if not rows:
        print("no rows produced")
        return 1
    df = pd.DataFrame(rows).sort_values(["country", "year", "index", "measure"])
    df.to_csv(OUT, index=False)
    print(f"\nwrote {OUT} ({len(df)} rows)")
    print("\ntilt by census, index and measure:")
    p = df.pivot_table(index=["country", "year", "index"], columns="measure", values="slope")
    print(p.to_string())
    # trend robustness: does a change over time survive the common index?
    for c in df["country"].unique():
        s = df[(df.country == c) & (df.measure == "prop_dead_2529")]
        for lab in ("full", "common"):
            t = s[s["index"] == lab].sort_values("year")
            if len(t) > 1:
                print(f"   {c} {lab:<7} {int(t.year.iloc[0])} {t.slope.iloc[0]:+.3f}"
                      f" -> {int(t.year.iloc[-1])} {t.slope.iloc[-1]:+.3f}"
                      f"   change {t.slope.iloc[-1] - t.slope.iloc[0]:+.3f}")
    for s, chk in DHS_CHECK.items():
        c, y = SAMPLES[s]["country"], SAMPLES[s]["year"]
        got = df[(df.country == c) & (df.year == y) & (df["index"] == "full") &
                 (df.measure == "prop_dead_2529")]["slope"]
        if len(got):
            print(f"\nvalidation: {c} {y} census gives {got.iloc[0]:+.4f}; "
                  f"{chk['survey']} gives {chk['u5mr_tilt']:+.4f} "
                  f"(difference {abs(got.iloc[0] - chk['u5mr_tilt']):.4f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
