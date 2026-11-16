# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "xlrd", "numpy"]
# ///
"""Brazil 2010: adult mortality by household wealth, from IBGE's census sample
microdata (household deaths module).

The IPUMS mortality supplement for this census is incomplete in a way that
varies with wealth (see br2010a in build_adult_mortality.py), so Brazil is
built from IBGE's own open files instead: all 27 federative units from IBGE's
public FTP (about 1.5 GB compressed, 11 GB extracted), no registration.

    uv run scripts/build_adult_mortality_brazil.py [--workdir DIR]

Method, as for the IPUMS censuses (asset_index.py):
- Wealth index: first principal component of household indicators for ten
  durable goods (IBGE V0213-V0222, code 1 = yes, verified against IBGE's
  variable description) and the number of exclusive bathrooms (V0205, as
  categories 0, 1, 2, 3, 4+). Households outside the asset module (improvised
  and collective dwellings, blank V0213) are excluded.
- Wealth groups at the quintiles of the household population, with groups under
  10% merged; gradient by least squares weighted by group population share.
- Death rates: weighted deaths in the 12 months before the census divided by
  the weighted population of the same age, sex and wealth group; 45q15 from the
  15-29, 30-44 and 45-59 bands. Bands and 45q15 are published only from at
  least 900 death records.
The PCA is computed from household asset patterns aggregated over all states,
which gives the same result as household-level data with far less memory.
"""

import argparse
import glob
import io
import os
import sys
import urllib.request
import zipfile

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import asset_index as ai  # noqa: E402

FTP = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Resultados_Gerais_da_Amostra/Microdados"
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB",
       "PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP1","SP2_RM","TO"]
DURABLES = {"V0213": "radio", "V0214": "tv", "V0215": "washer", "V0216": "refrig",
            "V0217": "cell", "V0218": "phone", "V0219": "computer", "V0220": "internet",
            "V0221": "motorcycle", "V0222": "car"}
BATHS = ["bath_0", "bath_1", "bath_2", "bath_3", "bath_4plus"]
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
SEXES = {"1": "male", "2": "female"}
MIN_BAND_DEATHS = 900
OUT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data",
                   "adult_mortality_gradients.csv")
# column order of the published file, as in build_adult_mortality.py
COLUMNS = ["indicator", "country", "year", "sex", "measure", "age_lo", "age_hi", "slope", "se", "ratio",
           "q1", "q2", "q3", "q4", "q5", "n_deaths", "ranking", "source", "groups", "linked_share"]
SRC = "IBGE Census 2010 sample microdata, household deaths module"


def fetch(workdir):
    os.makedirs(workdir, exist_ok=True)
    for name in ["Documentacao"] + UFS:
        marker = os.path.join(workdir, f".{name}.done")
        if os.path.exists(marker):
            continue
        print(f"downloading {name}.zip ...")
        with urllib.request.urlopen(f"{FTP}/{name}.zip", timeout=900) as r:
            buf = io.BytesIO(r.read())
        with zipfile.ZipFile(buf) as f:
            for info in f.infolist():
                if info.is_dir():
                    continue
                # zip names decode as cp437; strip to ASCII for the filesystem
                out = (info.filename.encode("cp437").decode("latin-1")
                       .encode("ascii", "ignore").decode().replace(" ", "_"))
                path = os.path.join(workdir, out)
                os.makedirs(os.path.dirname(path) or workdir, exist_ok=True)
                with f.open(info) as src, open(path, "wb") as dst:
                    while chunk := src.read(1 << 20):
                        dst.write(chunk)
        open(marker, "w").close()


def layout(workdir, sheet):
    xls = glob.glob(os.path.join(workdir, "Documenta*", "Layout", "Layout_microdados_Amostra.xls"))[0]
    raw = pd.read_excel(xls, sheet_name=sheet, header=None)
    hdr_row = hdr_col = None
    for i in range(min(6, len(raw))):
        for j, v in enumerate(raw.iloc[i]):
            if isinstance(v, str) and "INICIAL" in v.upper():
                hdr_row, hdr_col = i, j
    d = {}
    for _, r in raw.iloc[hdr_row + 1:].iterrows():
        var, ini, fim = r[0], r[hdr_col], r[hdr_col + 1]
        if isinstance(var, str) and var.startswith(("V", "M")) and pd.notna(ini):
            d[var.strip()] = (int(ini) - 1, int(fim))
    return d


def read_fwf(path, lay, cols):
    return pd.read_fwf(path, colspecs=[lay[c] for c in cols], names=cols, dtype=str)


def state_dirs(workdir):
    return sorted({os.path.dirname(f) for f in
                   glob.glob(os.path.join(workdir, "*", "Amostra_Mortalidade_*.txt"))})


def household_patterns(st, DL):
    """Asset indicators for each household in the asset module, and its weight."""
    dom = read_fwf(glob.glob(os.path.join(st, "Amostra_Domicilios_*.txt"))[0], DL,
                   ["V0300", "V0010", "V0205"] + list(DURABLES))
    dom = dom[dom["V0213"].notna()].copy()       # private permanent dwellings only
    X = pd.DataFrame({name: (dom[v] == "1").astype(np.int8) for v, name in DURABLES.items()})
    nb = pd.to_numeric(dom["V0205"], errors="coerce").fillna(0).clip(0, 4).astype(int)
    for k, name in enumerate(BATHS):
        X[name] = (nb == k).astype(np.int8)
    X["pattern"] = X.astype(str).agg("".join, axis=1)
    return pd.DataFrame({"V0300": dom["V0300"].values, "hw": dom["V0010"].astype(float).values,
                         "pattern": X["pattern"].values})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser("~/.cache/br2010-census/micro"))
    args = ap.parse_args()
    fetch(args.workdir)
    DL, PL, ML = (layout(args.workdir, s) for s in ["DOMI", "PESS", "MORT"])
    states = state_dirs(args.workdir)
    print(f"{len(states)} state file sets")

    # one pass: household weights by asset pattern; person weights by pattern
    # (all ages, for the wealth groups) and by pattern x sex x band (exposure);
    # weighted deaths and death records by pattern x sex x band
    hw, pw, expo, dths, nrec = {}, {}, {}, {}, {}

    def add(d, key, val):
        d[key] = d.get(key, 0.0) + val

    for st in states:
        hh = household_patterns(st, DL)
        for p, w in hh.groupby("pattern")["hw"].sum().items():
            add(hw, p, w)
        per = read_fwf(glob.glob(os.path.join(st, "Amostra_Pessoas_*.txt"))[0], PL,
                       ["V0300", "V0010", "V6036", "V0601"]).merge(hh[["V0300", "pattern"]], on="V0300")
        per["w"] = per["V0010"].astype(float)
        per["age"] = pd.to_numeric(per["V6036"], errors="coerce")
        for p, w in per.groupby("pattern")["w"].sum().items():
            add(pw, p, w)
        mor = read_fwf(glob.glob(os.path.join(st, "Amostra_Mortalidade_*.txt"))[0], ML,
                       ["V0300", "V0010", "V0704", "V7051"]).merge(hh[["V0300", "pattern"]], on="V0300")
        mor["w"] = mor["V0010"].astype(float)
        mor["age"] = pd.to_numeric(mor["V7051"], errors="coerce")
        for bi, (a0, a1) in enumerate(BANDS):
            p_b = per[per["age"].between(a0, a1)]
            m_b = mor[mor["age"].between(a0, a1)]
            for (p, s), w in p_b.groupby(["pattern", "V0601"])["w"].sum().items():
                add(expo, (p, s, bi), w)
            for (p, s), g in m_b.groupby(["pattern", "V0704"]):
                add(dths, (p, s, bi), g["w"].sum())
                add(nrec, (p, s, bi), len(g))
        print(f"  {os.path.basename(st)} done", flush=True)

    # wealth index from the household-weighted asset patterns
    pats = sorted(hw)
    X = pd.DataFrame([[int(c) for c in p] for p in pats],
                     columns=list(DURABLES.values()) + BATHS, index=pats)
    score, loadings, pc1 = ai.pca_score(X, [hw[p] for p in pats])
    sc = dict(zip(pats, score))
    print(f"wealth index: {len(loadings)} indicators, PC1 explains {pc1:.0%}")
    print("loadings:", loadings.round(2).to_dict())
    ppats = [p for p in pats if p in pw]
    cuts, group, mids, shares = ai.wealth_groups([sc[p] for p in ppats], [pw[p] for p in ppats])
    G = len(mids)
    gof = {p: int(group([sc[p]])[0]) for p in pats}
    print(f"{G} wealth groups, shares {np.round(shares, 3)}")

    def table(d, sexes):
        t = np.zeros((len(BANDS), G))
        for (p, s, bi), v in d.items():
            if s in sexes and p in gof:
                t[bi, gof[p]] += v
        return t

    rows = []
    for lab, sexes in [("all", {"1", "2"}), ("male", {"1"}), ("female", {"2"})]:
        e, dd, n = table(expo, sexes), table(dths, sexes), table(nrec, sexes)
        rates = dd / e
        for bi, (a0, a1) in enumerate(BANDS):
            if n[bi].sum() >= MIN_BAND_DEATHS and np.all(rates[bi] > 0):
                rows.append(row(lab, "mx", a0, a1, rates[bi], mids, shares, n[bi].sum(), G,
                                ai.gradient_se(mids, shares, rates[bi], n[bi])))
        q45 = 1 - np.prod((1 - rates[:3]) ** 15, axis=0)
        if n[:3].sum() >= MIN_BAND_DEATHS and np.all(q45 > 0):
            rows.append(row(lab, "45q15", 15, 59, q45, mids, shares, n[:3].sum(), G,
                            ai.gradient_se(mids, shares, rates[:3], n[:3])))

    new = pd.DataFrame(rows)
    old = pd.read_csv(OUT) if os.path.exists(OUT) else pd.DataFrame()
    keep = old[old["source"] != SRC] if len(old) else old
    # IPUMS rows, then Brazil, then the rest (Colombia, from
    # build_adult_mortality_colombia.py, then the survey rows of
    # build_adult_mortality_survey.py), so the file is identical whichever
    # script ran last
    ipums = keep["source"].astype(str).str.startswith("IPUMS") if len(keep) else []
    out = pd.concat([keep[ipums], new, keep[~ipums]] if len(keep) else [new], ignore_index=True)
    out[COLUMNS].to_csv(OUT, index=False)
    print(f"wrote {os.path.normpath(OUT)} ({len(new)} Brazil rows)")


def row(sex, measure, a0, a1, vals, mids, shares, n, G, se):
    r = dict(indicator="AMR", country="Brazil", year=2010, sex=sex, measure=measure,
             age_lo=a0, age_hi=a1,
             slope=round((ai.q45_gradient if measure == "45q15" else ai.gradient)(mids, vals, shares), 4),
             se=round(se, 4),
             ratio=round(float(vals[0] / vals[-1]), 3))
    for i in range(5):
        r[f"q{i + 1}"] = round(float(1000 * vals[i]), 3) if i < G else ""
    r.update(n_deaths=int(n), ranking="asset_index", source=SRC, groups=G, linked_share=1.0)
    return r


if __name__ == "__main__":
    main()
