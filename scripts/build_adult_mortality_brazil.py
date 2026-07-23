# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "xlrd", "numpy"]
# ///
"""Brazil 2010: adult mortality gradient by household asset rank, from the
open IBGE census sample microdata (household deaths module).

Fully replicable, no registration: downloads all 27 federative units from
IBGE's public FTP (~1.5 GB), links each recorded death (age/sex, deaths in
the 12 months before the census) to its household's asset index, and writes
age-band- and sex-specific gradients to data/adult_mortality_gradients.csv.

    uv run scripts/build_adult_mortality_brazil.py [--workdir DIR]

Takes ~30-60 minutes (download + two estimation passes). Method notes:
- Ranking is a household ASSET index (bathrooms capped at 4, plus ten
  durable-goods indicators), not measured income: a death mechanically
  removes the deceased's earnings from post-death household income
  (reverse causation), while assets are shock-stable. In validation on
  Sao Paulo, assets produced clean monotonic gradients where income did not.
- Quintile cuts land inside ties of the integer asset index, so groups are
  not exactly 20%; the tilt regression uses each group's realized
  population midpoint.
- Census death reporting is incomplete (~90% against vital statistics);
  under-reporting that is uniform across wealth cancels out of the tilt.
"""

import argparse
import glob
import io
import os
import urllib.request
import zipfile

import numpy as np
import pandas as pd

FTP = "https://ftp.ibge.gov.br/Censos/Censo_Demografico_2010/Resultados_Gerais_da_Amostra/Microdados"
UFS = ["AC","AL","AM","AP","BA","CE","DF","ES","GO","MA","MG","MS","MT","PA","PB",
       "PE","PI","PR","RJ","RN","RO","RR","RS","SC","SE","SP1","SP2_RM","TO"]
ASSETS = ["V0205","V0213","V0214","V0215","V0216","V0217","V0218","V0219","V0220","V0221","V0222"]
BANDS = [(15, 29), (30, 44), (45, 59), (60, 74)]
OUT = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "data",
                   "adult_mortality_gradients.csv")


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
    for _, r in raw.iloc[hdr_row + 1 :].iterrows():
        var, ini, fim = r[0], r[hdr_col], r[hdr_col + 1]
        if isinstance(var, str) and var.startswith(("V", "M")) and pd.notna(ini):
            d[var.strip()] = (int(ini) - 1, int(fim))
    return d


def read_fwf(path, lay, cols):
    return pd.read_fwf(path, colspecs=[lay[c] for c in cols], names=cols, dtype=str)


def state_dirs(workdir):
    return sorted({os.path.dirname(f) for f in
                   glob.glob(os.path.join(workdir, "*", "Amostra_Mortalidade_*.txt"))})


def household_assets(st, DL):
    dom = read_fwf(glob.glob(os.path.join(st, "Amostra_Domicilios_*.txt"))[0], DL, ["V0300"] + ASSETS)
    dom["assets"] = (dom[ASSETS[1:]] == "1").sum(axis=1) + pd.to_numeric(
        dom["V0205"], errors="coerce").fillna(0).clip(0, 4)
    return dom[["V0300", "assets"]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workdir", default=os.path.expanduser("~/.cache/br2010-census"))
    args = ap.parse_args()
    fetch(args.workdir)

    DL, PL, ML = (layout(args.workdir, s) for s in ["DOMI", "PESS", "MORT"])
    states = state_dirs(args.workdir)
    print(f"{len(states)} state file sets")

    # pass 1: pooled adult asset distribution -> national cuts and midpoints
    asset_w = {}
    for st in states:
        dom = household_assets(st, DL)
        per = read_fwf(glob.glob(os.path.join(st, "Amostra_Pessoas_*.txt"))[0], PL,
                       ["V0300", "V0010", "V6036"])
        per["w"] = per["V0010"].astype(float)
        per["age"] = pd.to_numeric(per["V6036"], errors="coerce")
        per = per[per["age"].between(BANDS[0][0], BANDS[-1][1])].merge(dom, on="V0300", how="left")
        for a, w in per.groupby("assets")["w"].sum().items():
            asset_w[a] = asset_w.get(a, 0.0) + w
    dist = pd.Series(asset_w).sort_index()
    cum = dist.cumsum() / dist.sum()
    cuts = [dist.index[np.searchsorted(cum.values, q)] for q in [0.2, 0.4, 0.6, 0.8]]
    qof = lambda v: np.searchsorted(cuts, v, side="right")
    gshare = np.zeros(5)
    for a, w in dist.items():
        gshare[qof(a)] += w
    gshare /= gshare.sum()
    mids = np.cumsum(gshare) - 0.5 * gshare

    # pass 2: deaths and exposure by sex x band x quintile
    expo = np.zeros((2, len(BANDS), 5))
    dths = np.zeros((2, len(BANDS), 5))
    nrec = np.zeros((2, len(BANDS), 5))
    for st in states:
        dom = household_assets(st, DL)
        per = read_fwf(glob.glob(os.path.join(st, "Amostra_Pessoas_*.txt"))[0], PL,
                       ["V0300", "V0010", "V6036", "V0601"])
        per["w"] = per["V0010"].astype(float)
        per["age"] = pd.to_numeric(per["V6036"], errors="coerce")
        per = per.merge(dom, on="V0300", how="left").dropna(subset=["assets"])
        per["q"] = per["assets"].apply(qof)
        mor = read_fwf(glob.glob(os.path.join(st, "Amostra_Mortalidade_*.txt"))[0], ML,
                       ["V0300", "V0010", "V0704", "V7051"])
        mor["w"] = mor["V0010"].astype(float)
        mor["age_d"] = pd.to_numeric(mor["V7051"], errors="coerce")
        mor = mor.merge(dom, on="V0300", how="left").dropna(subset=["assets"])
        mor["q"] = mor["assets"].apply(qof)
        for si, sex in enumerate(["1", "2"]):
            for bi, (a0, a1) in enumerate(BANDS):
                p = per[(per["V0601"] == sex) & per["age"].between(a0, a1)]
                m = mor[(mor["V0704"] == sex) & mor["age_d"].between(a0, a1)]
                expo[si, bi] += p.groupby("q")["w"].sum().reindex(range(5), fill_value=0).values
                dths[si, bi] += m.groupby("q")["w"].sum().reindex(range(5), fill_value=0).values
                nrec[si, bi] += m.groupby("q")["V0300"].count().reindex(range(5), fill_value=0).values
        print(f"  {os.path.basename(st)} done")

    rates = dths / expo
    rows = []
    SRC = "IBGE Census 2010 sample microdata, household deaths module"
    for si, sex in [(0, "male"), (1, "female")]:
        for bi, (a0, a1) in enumerate(BANDS):
            r = rates[si, bi]
            rows.append(dict(indicator="AMR", country="Brazil", year=2010, sex=sex,
                measure="mx", age_lo=a0, age_hi=a1,
                slope=round(np.polyfit(mids, np.log(r), 1)[0], 4),
                ratio=round(r[0] / r[4], 3),
                **{f"q{i+1}": round(1000 * r[i], 3) for i in range(5)},
                n_deaths=int(nrec[si, bi].sum()), ranking="asset_index", source=SRC))
        q45 = 1 - np.prod((1 - rates[si, :3]) ** 15, axis=0)
        rows.append(dict(indicator="AMR", country="Brazil", year=2010, sex=sex,
            measure="45q15", age_lo=15, age_hi=59,
            slope=round(np.polyfit(mids, np.log(q45), 1)[0], 4),
            ratio=round(q45[0] / q45[4], 3),
            **{f"q{i+1}": round(1000 * q45[i], 1) for i in range(5)},
            n_deaths=int(nrec[si, :3].sum()), ranking="asset_index", source=SRC))
    pd.DataFrame(rows).to_csv(OUT, index=False)
    print("wrote", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
