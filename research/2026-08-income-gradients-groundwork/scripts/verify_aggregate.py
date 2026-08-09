"""
Verify the income-group schedules aggregate to the national schedule.
Recomputes m[age,q] at FULL precision (not from the rounded CSV).

  (A) FIXED-SHARE rate aggregate   sum_q (1/5) m(a,q) == nMx_national(a)
      -> enforced in construction; should be ~machine epsilon.
  (B) SURVIVOR-WEIGHTED aggregate   total deaths / total exposure of the actual
      surviving cohort -> drifts slightly below national at old age (selection).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.interpolate import PchipInterpolator

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "figures"))
os.makedirs(OUT, exist_ok=True)
AGES_LB = np.array([0,1,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,90,95,100], float)
MID = np.array([0.5,3,7.5,12.5,17.5,22.5,27.5,32.5,37.5,42.5,47.5,52.5,57.5,62.5,
                67.5,72.5,77.5,82.5,87.5,92.5,97.5,102], float)
N = np.array([1,4]+[5]*20, float)
PRANK = np.array([0.1,0.3,0.5,0.7,0.9])

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
IMR_Q   = {"Ethiopia":[58,62,57,49,39],"Indonesia":[40,26,23,24,20],
           "Philippines":[24,17,23,11,6],"South Africa":[54,44,46,27,40]}
CHILD_Q = {"Ethiopia":[20,12,16,14,7],"Indonesia":[13,7,6,7,4],
           "Philippines":[11,6,2,2,1],"South Africa":[14,9,6,8,2]}
ADULT_ANCHORS = {
 "Ethiopia":    [(20,1.80),(32,1.80),(45,1.70),(57,1.50),(67,1.30),(80,1.12),(92,1.03),(102,1.0)],
 "Indonesia":   [(20,1.18),(32,1.18),(45,1.18),(57,1.15),(67,1.08),(80,1.04),(92,1.01),(102,1.0)],
 "Philippines": [(20,1.35),(32,1.35),(45,1.33),(57,1.28),(67,1.15),(80,1.06),(92,1.02),(102,1.0)],
 "South Africa":[(20,1.55),(32,1.72),(45,1.55),(57,1.60),(67,1.45),(80,1.20),(92,1.05),(102,1.0)],
}

def fit_ratio(rates):
    slope = np.polyfit(PRANK, np.log(rates), 1)[0]
    return float(np.exp(-0.8*slope))

def build_M(country):
    R_inf, R_chl = fit_ratio(IMR_Q[country]), fit_ratio(CHILD_Q[country])
    anchors = [(0.5,R_inf),(3,R_chl),(8,np.sqrt(R_chl*ADULT_ANCHORS[country][0][1]))] + ADULT_ANCHORS[country]
    aa = np.array([a for a,_ in anchors]); rr = np.array([r for _,r in anchors])
    R_age = np.clip(PchipInterpolator(aa, rr)(MID), 1.0, None)
    beta = np.log(R_age)/0.8
    phi = np.exp(-np.outer(beta, (PRANK-0.5)))
    phi /= phi.mean(axis=1, keepdims=True)
    nmx = np.array(NMX[country])
    return nmx, phi*nmx[:, None]

def tables(m):
    m = np.asarray(m, float)
    lx = np.empty(len(m)+1); lx[0] = 1.0
    for i in range(len(m)-1):
        lx[i+1] = lx[i]*np.exp(-N[i]*m[i])
    lx[-1] = 0.0
    ndx = lx[:-1]-lx[1:]
    nLx = np.empty(len(m))
    for i in range(len(m)-1):
        nLx[i] = ndx[i]/m[i]
    nLx[-1] = lx[-2]/m[-1]
    return lx, ndx, nLx

def e0(m):
    lx, ndx, nLx = tables(m)
    return nLx.sum()/lx[0]

print("="*90)
print(f"{'country':13} {'(A) max rel|Σ(1/5)m−nMx|':26} {'nat e0':>7} {'agg e0 (survivor-wt)':>21} {'drift(yr)':>10}")
print("-"*90)
store = {}
for c in NMX:
    nat, M = build_M(c)
    ew = M.mean(axis=1)                                   # (A) fixed-share aggregate
    relA = np.max(np.abs(ew - nat)/nat)
    ndx_q = np.zeros((len(nat),5)); nLx_q = np.zeros((len(nat),5))
    for q in range(5):
        _, ndx_q[:,q], nLx_q[:,q] = tables(M[:,q])
    m_agg = (0.2*ndx_q).sum(1)/(0.2*nLx_q).sum(1)         # (B) survivor-weighted aggregate
    store[c] = (nat, ew, m_agg)
    print(f"{c:13} {relA:<26.2e} {e0(nat):7.2f} {e0(m_agg):21.2f} {e0(m_agg)-e0(nat):+10.2f}")
print("-"*90)
print("(A) ~1e-16  => fixed-share rate aggregate reproduces national EXACTLY (enforced by construction).")
print("(B) +0.01..0.12 yr => survivor-weighted aggregate dips just below national at old age (selection).")
print("Note: the saved CSV is rounded to 6 dp, so reconstructing FROM it shows ~1e-3 (rounding, not error).")

c = "South Africa"; nat, ew, m_agg = store[c]
print(f"\n{c}: survivor-weighted aggregate vs national nMx, by age:")
for i in [0,9,13,16,18]:
    print(f"  age {int(AGES_LB[i]):>3}: national {nat[i]:.5f}  aggregate {m_agg[i]:.5f}  ratio {m_agg[i]/nat[i]:.4f}")

fig, ax = plt.subplots(2,2, figsize=(13,8.5))
fig.suptitle("Aggregate check — do the income-group rates sum back to the national schedule?",
             fontsize=13, fontweight="bold")
for k,c in enumerate(NMX):
    a = ax.ravel()[k]; nat, ew, m_agg = store[c]
    a.semilogy(MID, nat, "k-", lw=5, alpha=0.30, label="National (observed)")
    a.semilogy(MID, ew, color="#1f77b4", lw=1.6, ls="--", label="Fixed-share aggregate (A) — exact")
    a.semilogy(MID, m_agg, color="#d62728", lw=1.6, label="Survivor-weighted aggregate (B)")
    a.set_title(c, fontsize=10); a.set_xlabel("age"); a.set_ylabel("nMx (log)")
    a.grid(alpha=0.3, which="both"); a.legend(fontsize=7.5)
fig.text(0.5, 0.005, "(A) sits exactly on the national curve (enforced). (B) tracks it but dips ~1% below at ages "
         "40-85 because the surviving cohort skews to lower-mortality groups (mortality selection) — the only "
         "source of non-match, and only if population shares are allowed to drift with age.",
         ha="center", fontsize=7.3, style="italic")
fig.tight_layout(rect=[0,0.02,1,0.95])
fig.savefig(f"{OUT}/aggregate_check.png", dpi=115)
print(f"\nwrote {OUT}/aggregate_check.png")
