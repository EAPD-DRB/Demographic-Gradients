"""
Build approximate income-group mortality-rate schedules  m[age, j]  for
ETH, IDN, PHL, ZAF.

Design
------
* LEVEL: national abridged nMx (UN WPP 2024, both sexes, 2020-2025) -- the
  schedule OG-Core itself uses.
* GRADIENT: a multiplicative factor phi(age, q) = m_q / m_national, modelled
  as log-linear in income rank with a poorest:richest ratio R(age).
    - child ratios are FITTED to the observed DHS rates-by-wealth-quintile
    - adult ratios are anchored to observed studies (Agincourt 45q15, Butajira
      rate-ratios, IFLS e30, INDEPTH); 5-15 interpolated; old age tapered to 1
    - DHS gives the SHAPE of the child gradient; WPP gives the LEVEL.
* CONSTRAINT: phi normalised so the equal-weighted (0.2) quintile mean = 1 at
  every age -> the population aggregate reproduces the national schedule.
Output: rate schedules, adjustment-factor curves, and life-expectancy
validation vs observed gaps.  Quintiles (5 groups); remaps to OG-Core J later.
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(BASE, "figures")
os.makedirs(OUT, exist_ok=True)
AGES_LB = np.array([0,1,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100], float)
MID = np.array([0.5,3,7.5,12.5,17.5,22.5,27.5,32.5,37.5,42.5,47.5,52.5,57.5,62.5,
                67.5,72.5,77.5,82.5,87.5,92.5,97.5,102], float)
N = np.array([1,4]+[5]*20, float)
PRANK = np.array([0.1,0.3,0.5,0.7,0.9])          # quintile income-rank midpoints
QLAB = ["Q1 poorest","Q2","Q3","Q4","Q5 richest"]
qcol = plt.cm.viridis(np.linspace(0.12,0.85,5))

# ---- national nMx (UN WPP 2024, both sexes, 2020-2025) -----------------------
NMX = {
 "Ethiopia":   [0.0345118,0.0031896,0.0019703,0.0012813,0.0019596,0.0027819,0.0029860,
   0.0032554,0.0037182,0.0048070,0.0060273,0.0087286,0.0116724,0.0180447,0.0285365,
   0.0459360,0.0742117,0.1208886,0.1936767,0.2991081,0.4412753,0.5954177],
 "Indonesia":  [0.0177336,0.0008974,0.0004752,0.0004462,0.0010138,0.0013560,0.0014690,
   0.0017740,0.0024285,0.0035614,0.0055414,0.0085973,0.0133348,0.0207812,0.0326248,
   0.0516288,0.0817009,0.1282289,0.2004120,0.3017754,0.4383419,0.6020581],
 "Philippines":[0.0209177,0.0017716,0.0004616,0.0004539,0.0008024,0.0011965,0.0015924,
   0.0020861,0.0029046,0.0041786,0.0062861,0.0094633,0.0138618,0.0209094,0.0322968,
   0.0522682,0.0854199,0.1381262,0.2180092,0.3246086,0.4782133,0.6646832],
 "South Africa":[0.0267234,0.0023179,0.0005305,0.0006008,0.0014350,0.0026157,0.0038856,
   0.0050812,0.0062665,0.0079164,0.0104399,0.0139108,0.0194774,0.0268102,0.0376194,
   0.0514789,0.0710152,0.0965295,0.1329268,0.1834618,0.2503425,0.3399502],
}
# ---- DHS child mortality by wealth quintile (per 1,000), Q1..Q5 --------------
IMR_Q   = {"Ethiopia":[58,62,57,49,39],"Indonesia":[40,26,23,24,20],
           "Philippines":[24,17,23,11,6],"South Africa":[54,44,46,27,40]}
CHILD_Q = {"Ethiopia":[20,12,16,14,7],"Indonesia":[13,7,6,7,4],
           "Philippines":[11,6,2,2,1],"South Africa":[14,9,6,8,2]}
# ---- adult poorest:richest ratio anchors (age_mid -> R), per country ---------
# child anchors (0.5, 3) are filled from the fitted DHS gradient at runtime
ADULT_ANCHORS = {  # (age, R)
 "Ethiopia":    [(20,1.80),(32,1.80),(45,1.70),(57,1.50),(67,1.30),(80,1.12),(92,1.03),(102,1.0)],
 "Indonesia":   [(20,1.18),(32,1.18),(45,1.18),(57,1.15),(67,1.08),(80,1.04),(92,1.01),(102,1.0)],
 "Philippines": [(20,1.35),(32,1.35),(45,1.33),(57,1.28),(67,1.15),(80,1.06),(92,1.02),(102,1.0)],
 "South Africa":[(20,1.55),(32,1.72),(45,1.55),(57,1.60),(67,1.45),(80,1.20),(92,1.05),(102,1.0)],
}
OBS_GAP = {  # observed life-expectancy / e30 gap anchors for validation
 "Ethiopia":   ("e0 gap Q1-Q5 (Mekonnen 2013, modeled)", 9.0),
 "Indonesia":  ("e30 gap, men (IFLS/Sudharsanan)", 3.6),
 "South Africa":("LE gap, Agincourt HDSS (rural, high-HIV)", 12.0),
 "Philippines":("no direct estimate (borrowed gradient)", None),
}

def fit_ratio(rates):
    """poorest:richest ratio from a log-linear fit of rate on income rank."""
    slope = np.polyfit(PRANK, np.log(rates), 1)[0]
    return float(np.exp(-0.8*slope))

def phi_matrix(country):
    """phi[age_group, quintile]: log-linear gradient, mean-1 normalised per age."""
    R_inf, R_chl = fit_ratio(IMR_Q[country]), fit_ratio(CHILD_Q[country])
    anchors = [(0.5,R_inf),(3,R_chl),(8,np.sqrt(R_chl*ADULT_ANCHORS[country][0][1]))] \
              + ADULT_ANCHORS[country]
    aa = np.array([a for a,_ in anchors]); rr = np.array([r for _,r in anchors])
    R_age = np.clip(PchipInterpolator(aa, rr)(MID), 1.0, None)        # R at each group
    beta = np.log(R_age)/0.8
    phi = np.exp(-np.outer(beta, (PRANK-0.5)))                        # [age, q]
    phi /= phi.mean(axis=1, keepdims=True)                            # aggregate => national
    return phi, R_age, (R_inf, R_chl)

def lifetable(m):
    m = np.asarray(m, float)
    lx = np.empty(len(m)+1); lx[0] = 1.0
    for i in range(len(m)-1):
        lx[i+1] = lx[i]*np.exp(-N[i]*m[i])
    lx[-1] = 0.0
    nLx = np.empty(len(m))
    for i in range(len(m)-1):
        nLx[i] = (lx[i]-lx[i+1])/m[i]
    nLx[-1] = lx[-2]/m[-1]
    Tx = np.cumsum(nLx[::-1])[::-1]
    ex = Tx/lx[:-1]
    return ex, lx

idx = {a: i for i, a in enumerate(AGES_LB)}
def e0(m):  return lifetable(m)[0][0]
def e30(m): return lifetable(m)[0][idx[30]]
def u5mr(m):
    lx = lifetable(m)[1]
    return (1 - lx[idx[5]]/lx[0])*1000

# =============================================================================
# BUILD + VALIDATE
# =============================================================================
print("="*78)
schedules = {}
for c in NMX:
    nmx = np.array(NMX[c]); phi, R_age, (R_inf, R_chl) = phi_matrix(c)
    M = phi * nmx[:, None]                       # m[age, quintile]
    schedules[c] = (nmx, phi, M, R_age)
    e0q  = [e0(M[:, q]) for q in range(5)]
    u5q  = [u5mr(M[:, q]) for q in range(5)]
    lab, gap = OBS_GAP[c]
    print(f"\n{c}:  national e0 = {e0(nmx):.1f} yr   (child gradient fitted: "
          f"infant {R_inf:.2f}x, child1-4 {R_chl:.2f}x)")
    print(f"  implied e0 by quintile:  " + "  ".join(f"{v:.1f}" for v in e0q) +
          f"   -> Q5-Q1 gap {e0q[4]-e0q[0]:.1f} yr")
    print(f"  implied U5MR by quintile (WPP level, DHS shape): " +
          "  ".join(f"{v:.0f}" for v in u5q))
    print(f"  validation target: {lab} = {gap if gap is not None else 'n/a'}")

# ---- CSV: rate schedules -----------------------------------------------------
import csv
csv_path = os.path.join(BASE, "mortality_rate_schedules.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["country","age_group_lb","national_nMx"]+QLAB)
    for c in NMX:
        nmx, phi, M, _ = schedules[c]
        for i, a in enumerate(AGES_LB):
            w.writerow([c, int(a), f"{nmx[i]:.6f}"]+[f"{M[i,q]:.6f}" for q in range(5)])
print(f"\nwrote {csv_path}")

# =============================================================================
# CHARTS  -- per country: rate fan (log) + adjustment factor
# =============================================================================
for c in NMX:
    nmx, phi, M, R_age = schedules[c]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.3))
    borrow = "  [adult gradient BORROWED]" if c == "Philippines" else ""
    fig.suptitle(f"{c} — approximate mortality rate schedule by income group{borrow}",
                 fontsize=13, fontweight="bold")
    for q in range(5):
        ax[0].semilogy(MID, M[:, q], color=qcol[q], lw=1.8, marker="o", ms=3, label=QLAB[q])
    ax[0].semilogy(MID, nmx, "k--", lw=2.2, label="National (aggregate)")
    ax[0].set_title("(a) central death rate  nMx  by quintile")
    ax[0].set_xlabel("age"); ax[0].set_ylabel("nMx (log scale, deaths / person-yr)")
    ax[0].legend(fontsize=7.5); ax[0].grid(alpha=0.3, which="both")
    for q in range(5):
        ax[1].plot(MID, phi[:, q], color=qcol[q], lw=1.8, marker="o", ms=3)
    ax[1].axhline(1, color="k", lw=0.8, ls="--")
    ax[1].axvspan(0, 5, color="#cfe8cf", alpha=0.4); ax[1].axvspan(5, 15, color="#ffe9b3", alpha=0.5)
    ax[1].text(2.5, ax[1].get_ylim()[1]*0.97, "child:\nDHS-fitted", fontsize=7, ha="center", va="top", color="#2a6")
    ax[1].text(10, ax[1].get_ylim()[1]*0.97, "5-15\nhole", fontsize=7, ha="center", va="top", color="#b8860b")
    ax[1].set_title("(b) adjustment factor  phi = m_q / m_national")
    ax[1].set_xlabel("age"); ax[1].set_ylabel("× national rate")
    ax[1].grid(alpha=0.3)
    fig.text(0.5, 0.005, "National nMx: UN WPP 2024 (both sexes, 2020-25). Child gradient fitted to DHS "
             "wealth-quintile rates; adult anchors: ZAF Agincourt 45q15 + 50+ HR, IDN IFLS e30, ETH Butajira "
             "rate-ratios, INDEPTH. phi normalised so the equal-weighted quintile mean = national at every age.",
             ha="center", fontsize=7, style="italic")
    fig.tight_layout(rect=[0, 0.03, 1, 0.94])
    fname = f"{OUT}/schedule_{c.split()[0].lower()}.png"
    fig.savefig(fname, dpi=115); plt.close(fig)

# ---- validation figure: implied e0 by quintile + observed gap ----------------
figV, vx = plt.subplots(1, 4, figsize=(16, 4.4), sharey=False)
figV.suptitle("Validation — implied life expectancy by income quintile (from the constructed schedules)",
              fontsize=13, fontweight="bold")
for k, c in enumerate(NMX):
    nmx, phi, M, _ = schedules[c]
    e0q = [e0(M[:, q]) for q in range(5)]
    vx[k].bar(range(5), e0q, color=qcol)
    lab, gap = OBS_GAP[c]
    vx[k].set_title(f"{c}\nimplied Q5-Q1 gap = {e0q[4]-e0q[0]:.1f} yr", fontsize=9.5)
    vx[k].set_xticks(range(5)); vx[k].set_xticklabels(["Q1","Q2","Q3","Q4","Q5"], fontsize=8)
    vx[k].set_ylim(min(e0q)-3, max(e0q)+2); vx[k].grid(alpha=0.3, axis="y")
    note = f"obs: {gap} yr" if gap is not None else "obs: none (borrowed)"
    vx[k].text(0.5, 0.02, note, transform=vx[k].transAxes, ha="center", fontsize=8,
               style="italic", color="0.3")
    if k == 0: vx[k].set_ylabel("life expectancy at birth (yr)")
figV.text(0.5, 0.005, "Implied gaps come from anchor RRs, not calibrated to the LE targets; ETH/ZAF observed gaps are "
          "from higher-mortality modeled/HDSS populations so levels differ — shown for shape comparison. "
          "betas are tunable to hit any target gap exactly.", ha="center", fontsize=7, style="italic")
figV.tight_layout(rect=[0, 0.04, 1, 0.93])
figV.savefig(f"{OUT}/schedule_validation.png", dpi=115); plt.close(figV)

print("wrote:", sorted(f for f in os.listdir(OUT) if f.startswith("schedule")))
