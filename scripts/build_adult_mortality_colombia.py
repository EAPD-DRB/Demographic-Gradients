# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "numpy"]
# ///
"""Colombia 2018: adult mortality by household wealth, from DANE's census
microdata (Censo Nacional de Población y Vivienda 2018, full count).

The census asked each household for its members who died in 2017, with sex,
age at death and whether a death certificate was issued (FALLECIDOS file).
Colombia 2018 is not in IPUMS International, so the estimate is built from
DANE's own files.

Input: the 33 department archives from DANE's microdata catalogue
(https://microdatos.dane.gov.co/index.php/catalog/643/get-microdata; about
2.5 GB, free of charge, each download behind a reCAPTCHA, so they are fetched
by hand), saved unopened in --zipdir. The CSV files inside are extracted to
--workdir on the first run. DANE's terms permit use with citation and forbid
redistribution of the microdata; only estimates are committed.

    uv run scripts/build_adult_mortality_colombia.py [--zipdir DIR] [--workdir DIR]

Method, as for the IPUMS censuses (asset_index.py):
- Universe: households in occupied private dwellings (V_CON_OCUP = 1). Persons
  in collective quarters (LEA) have no household record and are excluded.
- Wealth index: first principal component of household indicators for
  electricity (VA_EE), internet (VF_INTERNET) and each toilet category
  (V_TIPO_SERSA 1-6), the census's only items comparable to the durable goods
  and toilet type used elsewhere. Housing materials and services are not used
  (ruled 2026-11-13); the script prints, for comparison only, the gradient on
  an index that adds them.
- Wealth groups at the quintiles of the household population, with groups under
  10% merged; gradient by least squares weighted by group population share.
- Death rates: deaths in 2017 divided by the census population of the same
  sex, age band and wealth group (P_EDADR five-year groups); 45q15 from the
  15-29, 30-44 and 45-59 bands, published only from at least 900 death records.
  It is a full count: every household and death has weight 1.
Checks printed: linkage of death records to households; death records against
the deaths each household reports (HA_NRO_FALL), by wealth group; unknown age
and sex, and death-certificate status, by wealth group.
"""

import argparse
import glob
import io
import os
import sys
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import asset_index as ai  # noqa: E402

DEPTS = ["05", "08", "11", "13", "15", "17", "18", "19", "20", "23", "25", "27", "41",
         "44", "47", "50", "52", "54", "63", "66", "68", "70", "73", "76", "81", "85",
         "86", "88", "91", "94", "95", "97", "99"]
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
# P_EDADR codes: 4 = 15-19 ... 15 = 70-74
PBAND = {4: 0, 5: 0, 6: 0, 7: 1, 8: 1, 9: 1, 10: 2, 11: 2, 12: 2, 13: 3, 14: 3, 15: 3}
MIN_BAND_DEATHS = 900
TOILET = range(1, 7)  # 1 sewer, 2 septic tank, 3 unconnected, 4 latrine, 5 discharge to water, 6 none
# housing items for the comparison index only (not published)
EXTRA_CAT = {"V_MAT_PARED": range(1, 10), "V_MAT_PISO": range(1, 7),
             "H_AGUA_COCIN": range(1, 13), "H_DONDE_PREPALIM": range(1, 7), "crowd": range(4)}
EXTRA_YES = ["VB_ACU", "VC_ALC", "VD_GAS", "VE_RECBAS"]
K = ["COD_ENCUESTAS", "U_VIVIENDA"]
HK = K + ["H_NROHOG"]
OUT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data",
                   "adult_mortality_gradients.csv")
COLUMNS = ["indicator", "country", "year", "sex", "measure", "age_lo", "age_hi", "slope", "se", "ratio",
           "q1", "q2", "q3", "q4", "q5", "share1", "share2", "share3", "share4", "share5", "n_deaths", "ranking", "source", "groups", "linked_share"]
SRC = ("DANE, Censo Nacional de Población y Vivienda 2018, microdata "
       "(household deaths in 2017)")


def extract(zipdir, workdir):
    os.makedirs(workdir, exist_ok=True)
    for d in DEPTS:
        if os.path.exists(os.path.join(workdir, f"CNPV2018_5PER_A2_{d}.CSV")):
            continue
        z = glob.glob(os.path.join(zipdir, f"{d}_*.zip"))
        if not z:
            raise SystemExit(f"department {d}: no archive in {zipdir}; nothing written")
        with zipfile.ZipFile(z[0]) as outer:
            name = [n for n in outer.namelist() if n.endswith("_CSV.zip")][0]
            with zipfile.ZipFile(io.BytesIO(outer.read(name))) as inner:
                for info in inner.infolist():
                    base = os.path.basename(info.filename)
                    if "MGN" in base or not base.upper().endswith(".CSV"):
                        continue
                    with inner.open(info) as src, open(os.path.join(workdir, base), "wb") as dst:
                        while chunk := src.read(1 << 20):
                            dst.write(chunk)
        print(f"extracted department {d}", flush=True)


def department(workdir, d):
    """Households of one department, collapsed to patterns of the index items."""
    f = lambda kind: os.path.join(workdir, f"CNPV2018_{kind}_A2_{d}.CSV")  # noqa: E731
    v = pd.read_csv(f("1VIV"), usecols=K + ["V_CON_OCUP", "VA_EE", "VF_INTERNET", "V_TIPO_SERSA",
                                            "V_MAT_PARED", "V_MAT_PISO"] + EXTRA_YES)
    v = v[v["V_CON_OCUP"] == 1].drop(columns="V_CON_OCUP")
    h = pd.read_csv(f("2HOG"), usecols=HK + ["H_NRO_DORMIT", "H_DONDE_PREPALIM", "H_AGUA_COCIN",
                                            "HA_NRO_FALL"]).merge(v, on=K)
    p = pd.read_csv(f("5PER"), usecols=K + ["P_NROHOG", "P_SEXO", "P_EDADR"]).rename(
        columns={"P_NROHOG": "H_NROHOG"})
    p = p.dropna(subset=["H_NROHOG"])  # persons in collective quarters
    h = h.merge(p.groupby(HK).size().rename("npers").reset_index(), on=HK, how="left")
    p["b"] = p["P_EDADR"].map(PBAND)
    pc = p.dropna(subset=["b"]).groupby(HK + ["P_SEXO", "b"]).size().unstack(["P_SEXO", "b"], fill_value=0)
    pc.columns = [f"p_{int(s)}_{int(b)}" for s, b in pc.columns]
    m = pd.read_csv(f("3FALL")).rename(columns={"F_NROHOG": "H_NROHOG"})
    n_deaths = len(m)
    m = m.merge(h[HK], on=HK)
    age = m["FA3_EDAD_FALL"].where(m["FA3_EDAD_FALL"] < 999)  # 999 = unknown
    m["b"] = np.select([age.between(a0, a1) for a0, a1 in BANDS], range(len(BANDS)), -1)
    m.loc[age.isna(), "b"] = -2
    m["s"] = m["FA2_SEXO_FALL"].where(m["FA2_SEXO_FALL"].isin([1, 2]), 9)
    dc = m.groupby(HK + ["s", "b"]).size().unstack(["s", "b"], fill_value=0)
    dc.columns = [f"d_{int(s)}_{int(b)}" for s, b in dc.columns]
    cert = m.groupby(HK + ["FA4_CERT_DEFUN"]).size().unstack(fill_value=0)
    cert.columns = [f"cert_{int(c)}" for c in cert.columns]
    h = (h.merge(pc, left_on=HK, right_index=True, how="left")
          .merge(dc, left_on=HK, right_index=True, how="left")
          .merge(cert, left_on=HK, right_index=True, how="left"))
    rooms = h["H_NRO_DORMIT"].where(h["H_NRO_DORMIT"] < 99)
    h["crowd"] = pd.cut(h["npers"] / rooms, [0, 1, 2, 3, np.inf], labels=False)
    h["hh"] = 1
    cats = ["VA_EE", "VF_INTERNET", "V_TIPO_SERSA"] + list(EXTRA_CAT) + EXTRA_YES
    num = [c for c in h.columns if c.startswith(("p_", "d_", "cert_"))] + ["npers", "HA_NRO_FALL", "hh"]
    h[num] = h[num].fillna(0)
    g = h.groupby([h[c].fillna(-1).astype(int) for c in cats])[num].sum().reset_index()
    return g, n_deaths, len(m)


def indicators(t, extended=False):
    X = pd.DataFrame({"electric": (t["VA_EE"] == 1), "internet": (t["VF_INTERNET"] == 1)})
    for k in TOILET:
        X[f"toilet_{k}"] = t["V_TIPO_SERSA"] == k
    if extended:
        for c, ks in EXTRA_CAT.items():
            for k in ks:
                X[f"{c}_{k}"] = t[c] == k
        for c in EXTRA_YES:
            X[c] = t[c] == 1
    return X.astype(float)


def groups_of(t, extended):
    """Wealth group of each row of the pattern table, with midpoints and shares."""
    X = indicators(t, extended)
    key = X.astype(int).astype(str).agg("".join, axis=1)
    g = t.assign(key=key).groupby("key")
    hw, pw = g["hh"].sum(), g["npers"].sum()
    Xp = X.groupby(key).first().loc[hw.index]
    score, loadings, pc1 = ai.pca_score(Xp, hw.values)
    cuts, group, mids, shares = ai.wealth_groups(score, pw.values)
    q = pd.Series(group(pd.Series(score, index=hw.index).loc[key].values), index=t.index)
    return q, mids, shares, loadings, pc1


def rates(T, sexes, G):
    """Band rates, record totals and record counts by wealth group."""
    R, N, C = np.zeros((len(BANDS), G)), np.zeros(len(BANDS)), np.zeros((len(BANDS), G))
    for b in range(len(BANDS)):
        e = sum(T.get(f"p_{s}_{b}", 0) for s in sexes)
        d = sum(T.get(f"d_{s}_{b}", 0) for s in sexes)
        if len(sexes) == 2:  # deaths of unrecorded sex count in the both-sexes rates
            d = d + T.get(f"d_9_{b}", 0)
        R[b], N[b] = np.asarray(d / e, dtype=float), float(np.sum(d))
        C[b] = np.asarray(d, dtype=float)  # full count: every record has weight 1
    return R, N, C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zipdir", default=os.path.expanduser("~/Projects/data/co2018"))
    ap.add_argument("--workdir", default=os.path.expanduser("~/.cache/co2018-census"))
    args = ap.parse_args()
    extract(args.zipdir, args.workdir)
    parts, n_all, n_linked = [], 0, 0
    for d in DEPTS:
        g, n, k = department(args.workdir, d)
        parts.append(g)
        n_all, n_linked = n_all + n, n_linked + k
    num = [c for c in pd.concat(parts).columns if c.startswith(("p_", "d_", "cert_"))] + [
        "npers", "HA_NRO_FALL", "hh"]
    cats = [c for c in parts[0].columns if c not in num]
    t = pd.concat(parts).fillna(0).groupby(cats)[num].sum().reset_index()
    linked_share = n_linked / n_all
    print(f"{int(t['hh'].sum())} households, {int(t['npers'].sum())} persons; "
          f"{n_all} death records, {n_linked} linked to a household ({linked_share:.1%})")

    q, mids, shares, loadings, pc1 = groups_of(t, extended=False)
    G = len(mids)
    print(f"wealth index: {len(loadings)} indicators, PC1 explains {pc1:.0%}; "
          f"{G} groups, shares {np.round(shares, 3)}")
    print("loadings:", loadings.round(2).to_dict())
    if G < 3:
        raise SystemExit(f"{G} wealth groups, fewer than 3; nothing written")
    T = t.groupby(q).sum(numeric_only=True)
    dcols = [c for c in T.columns if c.startswith("d_")]
    tot = T[dcols].sum(axis=1)
    print("death records / deaths reported by the household, by wealth group:",
          np.round((tot / T["HA_NRO_FALL"]).values, 4))
    print("unknown age share by wealth group:",
          np.round((T[[c for c in dcols if c.endswith("_-2")]].sum(axis=1) / tot).values, 4))
    print("unknown sex share by wealth group:",
          np.round((T[[c for c in dcols if c.startswith("d_9_")]].sum(axis=1) / tot).values, 4))
    cert = T[[c for c in T.columns if c.startswith("cert_")]].div(tot, axis=0)
    print("death certificate (cert_1 yes, 2 no, 3 not known, 9 not stated), share by wealth group:")
    print(cert.round(3).to_string())

    rows = []
    for lab, sexes in [("all", [1, 2]), ("male", [1]), ("female", [2])]:
        R, N, C = rates(T, sexes, G)
        for b, (a0, a1) in enumerate(BANDS):
            if N[b] >= MIN_BAND_DEATHS and np.all(R[b] > 0):
                rows.append(row(lab, "mx", a0, a1, R[b], mids, shares, N[b], G, linked_share,
                                ai.gradient_se(mids, shares, R[b], C[b])))
        q45 = 1 - np.prod((1 - R[:3]) ** 15, axis=0)
        if N[:3].sum() >= MIN_BAND_DEATHS and np.all(q45 > 0):
            rows.append(row(lab, "45q15", 15, 59, q45, mids, shares, N[:3].sum(), G, linked_share,
                            ai.gradient_se(mids, shares, R[:3], C[:3])))
            print(f"45q15 {lab}: gradient {rows[-1]['slope']:+.3f}, per 1000 {np.round(1000 * q45, 1)}")

    # comparison only: an index adding housing materials and services
    qx, mx_, shx, lx, pcx = groups_of(t, extended=True)
    Tx = t.groupby(qx).sum(numeric_only=True)
    Rx, _, _ = rates(Tx, [1, 2], len(mx_))
    q45x = 1 - np.prod((1 - Rx[:3]) ** 15, axis=0)
    print(f"comparison (not published): index with housing items, {len(lx)} indicators, "
          f"{len(mx_)} groups; 45q15 gradient {ai.q45_gradient(mx_, q45x, shx):+.3f}, "
          f"per 1000 {np.round(1000 * q45x, 1)}")

    new = pd.DataFrame(rows)
    old = pd.read_csv(OUT)
    old = old[old["source"] != SRC]
    src = old["source"].astype(str)
    # census rows (IPUMS, then Brazil), then Colombia, then the survey rows, so
    # the file is identical whichever script ran last
    first = src.str.startswith("IPUMS") | src.str.startswith("IBGE")
    out = pd.concat([old[first], new, old[~first]], ignore_index=True)
    out[COLUMNS].to_csv(OUT, index=False)
    print(f"wrote {os.path.normpath(OUT)} ({len(new)} Colombia rows)")


def row(sex, measure, a0, a1, vals, mids, shares, n, G, linked_share, se):
    r = dict(indicator="AMR", country="Colombia", year=2018, sex=sex, measure=measure,
             age_lo=a0, age_hi=a1,
             slope=round((ai.q45_gradient if measure == "45q15" else ai.gradient)(mids, vals, shares), 4),
             se=round(se, 4),
             ratio=round(float(vals[0] / vals[-1]), 3))
    for i in range(5):
        r[f"q{i + 1}"] = round(float(1000 * vals[i]), 3) if i < G else ""
    for i in range(5):
        r[f"share{i + 1}"] = round(float(shares[i]), 4) if i < G else ""
    r.update(n_deaths=int(n), ranking="asset_index", source=SRC, groups=G,
             linked_share=round(linked_share, 3))
    return r


if __name__ == "__main__":
    main()
