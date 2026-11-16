"""Household wealth index for census microdata, shared by the census scripts.

The index follows the standard asset-index method (Filmer and Pritchett 2001;
Rutstein and Johnson 2004 for the DHS wealth index; Lovaton Davila et al. 2022
for IPUMS-International census samples): the first principal component of
household-level indicator variables, one for each asset owned and one for each
category of a categorical housing variable (toilet type). Variables are
standardized, so the principal components are those of the household-weighted
correlation matrix, and the score is oriented to rise with the number of assets
owned. Wealth groups are formed from the score's distribution over the
household population (all persons), as for the DHS wealth quintiles.

IPUMS-I codes, checked against the codebooks of every extract:
ELECTRIC and CELL 1 = yes; PHONE, COMPUTER, REFRIG, RADIO and INTERNET 2 = yes;
WASHER 2 = yes, 3-4 = yes by machine type; TV 20-43 = yes (21-43 give the number
or type of sets); BATH 2-4 = has a bathing facility; AUTOS 1-6 = number of cars,
7 = has a car, number unspecified, 8 = unknown, 9 = NIU; TOILET 10 = none,
11 = no flush toilet, 20 = toilet of unspecified type, 21 = flush, 22 = latrine,
23 = other non-flush, 99 = unknown. Unknown and NIU answers count as "not owned".
"""

import numpy as np
import pandas as pd

YES = {"ELECTRIC": [1], "PHONE": [2], "CELL": [1], "INTERNET": [2],
       "COMPUTER": [2], "WASHER": [2, 3, 4], "REFRIG": [2], "TV": list(range(20, 44)),
       "RADIO": [2], "BATH": [2, 3, 4], "AUTOS": [1, 2, 3, 4, 5, 6, 7]}
TOILET = {10: "toilet_none", 11: "toilet_no_flush", 20: "toilet_unspecified",
          21: "toilet_flush", 22: "toilet_latrine", 23: "toilet_other"}
QUANTILES = (0.2, 0.4, 0.6, 0.8)


def in_universe(per):
    """Persons in households that answered the asset module (NIU is 0, AUTOS 9)."""
    obs = pd.Series(False, index=per.index)
    for c in [c for c in YES if c != "AUTOS" and c in per.columns] + (
            ["TOILET"] if "TOILET" in per.columns else []):
        obs |= per[c].fillna(0) > 0
    if "AUTOS" in per.columns:
        obs |= per["AUTOS"].fillna(9) != 9
    return obs


def indicators(hh):
    """Household-level 0/1 indicators: one per asset, one per toilet category."""
    X = pd.DataFrame(index=hh.index)
    for c, yes in YES.items():
        if c in hh.columns:
            X[c.lower()] = hh[c].isin(yes).astype(float)
    if "TOILET" in hh.columns:
        for code, name in TOILET.items():
            X[name] = (hh["TOILET"] == code).astype(float)
    return X


def pca_score(X, w):
    """First principal component of the weighted correlation matrix.

    Returns the household scores, the loadings (eigenvector, oriented so the
    score rises with assets owned) and the share of variance explained.
    Indicators with no variation in the sample are dropped.
    """
    w = np.asarray(w, dtype=float)
    w = w / w.sum()
    mean = (X.values * w[:, None]).sum(axis=0)
    sd = np.sqrt(((X.values - mean) ** 2 * w[:, None]).sum(axis=0))
    keep = sd > 1e-9
    Z = (X.values[:, keep] - mean[keep]) / sd[keep]
    C = (Z * w[:, None]).T @ Z
    vals, vecs = np.linalg.eigh(C)
    v = vecs[:, -1]
    score = Z @ v
    owned = X[[c for c in X.columns if not c.startswith("toilet_")]].sum(axis=1).values
    if np.corrcoef(score, owned)[0, 1] < 0:
        v, score = -v, -score
    loadings = pd.Series(v, index=X.columns[keep])
    return score, loadings, float(vals[-1] / vals.sum())


def household_index(per):
    """PCA wealth score for each household in the asset universe.

    `per` is the person-level extract (numeric asset columns, SERIAL, HHWT).
    Returns (households with a `score` column, loadings, variance share).
    """
    hh = per.drop_duplicates("SERIAL").copy()
    X = indicators(hh)
    score, loadings, share = pca_score(X, hh["HHWT"])
    hh["score"] = score
    return hh[["SERIAL", "score"]], loadings, share


MIN_GROUP_SHARE = 0.10  # half a quintile; smaller groups are merged into a neighbour


def wealth_groups(score, weight):
    """Wealth groups at the population quintiles of the score.

    Cut points are placed at the score values closest to the 20th, 40th, 60th
    and 80th percentiles of the person-weighted distribution. A household whose
    score equals a cut belongs to the group above it. Coinciding cuts are
    dropped, and so is a cut at the minimum score, which would leave the lowest
    group empty; a cut at the maximum is kept, since it separates the
    households with the highest score into a group of their own (ruled
    2026-11-13; dropping it had merged a real top group in Colombia 2018 and
    Malawi 1998). Where many households
    share a score, a group can still be very small; any group holding less than
    MIN_GROUP_SHARE of the population is merged into its smaller neighbour,
    repeatedly, so every group is large enough to give a stable rate.

    Returns the cuts, a function assigning groups, each group's realized rank
    midpoint, and each group's population share.
    """
    d = pd.DataFrame({"s": np.asarray(score, dtype=float),
                      "w": np.asarray(weight, dtype=float)}).sort_values("s")
    cum = d["w"].cumsum() / d["w"].sum()
    cuts = sorted({float(d["s"].iloc[int((cum - q).abs().values.argmin())]) for q in QUANTILES})
    cuts = [c for c in cuts if c > d["s"].min()]

    def shares(cuts):
        g = np.searchsorted(cuts, d["s"].values, side="right")
        sh = pd.Series(d["w"].values).groupby(g).sum().reindex(range(len(cuts) + 1),
                                                                   fill_value=0).values
        return sh / sh.sum()

    sh = shares(cuts)
    while len(cuts) and sh.min() < MIN_GROUP_SHARE:
        i = int(sh.argmin())
        if i == 0:
            cuts.pop(0)
        elif i == len(sh) - 1:
            cuts.pop()
        else:  # merge with the smaller neighbour
            cuts.pop(i - 1 if sh[i - 1] <= sh[i + 1] else i)
        sh = shares(cuts)

    def group(s):
        return np.searchsorted(cuts, np.asarray(s, dtype=float), side="right")

    return cuts, group, np.cumsum(sh) - 0.5 * sh, sh


def gradient(mids, rates, shares):
    """Wealth gradient: slope of ln(rate) on rank midpoint, weighted by group share.

    Weighted least squares with the groups' population shares as weights; for
    equal-sized groups this is ordinary least squares.
    """
    return float(np.polyfit(np.asarray(mids), np.log(np.asarray(rates, dtype=float)), 1,
                            w=np.sqrt(np.asarray(shares, dtype=float)))[0])


def q45_gradient(mids, q45, shares):
    """Wealth gradient of adult mortality (ages 15-59) on the death-rate scale.

    45q15 is a probability and approaches 1 where adult mortality is high, so
    ln(45q15) moves less than the death rates behind it: with rates twice as
    high in the poorest group, 45q15 may differ by much less than a factor of
    two. The gradient is therefore fitted to the cumulative death rate over the
    age range, -ln(1 - 45q15) (the sum of the age-specific rates times 15 years
    each), which is proportional to the death rates. This is the scale on which
    OG-Core applies a mortality gradient (annual death rates), and a uniform
    under-recording of deaths leaves it unchanged. Ruled 2026-11-16; 45q15
    itself is still what the q1..q5 columns report.
    """
    return gradient(mids, -np.log1p(-np.asarray(q45, dtype=float)), shares)


def gradient_se(mids, shares, band_rates, band_counts):
    """Standard error of a census gradient, treating death counts as Poisson.

    band_rates and band_counts are the death rates and the unweighted numbers
    of death records by wealth group: one band (shape G) for an age-band
    gradient, or the three bands 15-29, 30-44, 45-59 (shape 3 x G) for the
    45q15 gradient. A rate m from n records has relative variance 1/n. For
    45q15 the variance of the cumulative rate H = -15 sum ln(1 - m) follows by
    the delta method. The gradient is a weighted least-squares slope, a linear
    combination sum c_g y_g of the log values, so its variance is
    sum c_g^2 var(y_g). The figure measures the sampling variability of the
    deaths only: it leaves out clustering of deaths within households and
    every non-sampling error (the wealth index, under-recording), which are
    usually larger.
    """
    x, w = np.asarray(mids, dtype=float), np.asarray(shares, dtype=float)
    w = w / w.sum()
    xb = (w * x).sum()
    c = w * (x - xb) / (w * (x - xb) ** 2).sum()
    m, n = np.atleast_2d(np.asarray(band_rates, float)), np.atleast_2d(np.asarray(band_counts, float))
    if m.shape[0] == 1:
        var_y = 1.0 / n[0]
    else:
        H = -15 * np.log1p(-m).sum(axis=0)
        var_H = ((15 * m / (1 - m)) ** 2 / n).sum(axis=0)
        var_y = var_H / H ** 2
    return float(np.sqrt((c ** 2 * var_y).sum()))
