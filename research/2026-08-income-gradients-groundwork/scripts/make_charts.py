"""
Income-differentiated mortality & fertility by age — data views for OG-Core
calibration countries (ETH, IDN, PHL, ZAF).

All numbers transcribed from primary sources (cited per dict).
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.normpath(os.path.join(HERE, "..", "figures"))
os.makedirs(OUT, exist_ok=True)

# Consistent country styling
C = {"Ethiopia": "#d62728", "Indonesia": "#2ca02c",
     "Philippines": "#1f77b4", "South Africa": "#ff7f0e"}
AGE_GROUPS = ["15-19", "20-24", "25-29", "30-34", "35-39", "40-44", "45-49"]
QUINT = ["Lowest", "Second", "Middle", "Fourth", "Highest"]

# ---- FERTILITY DATA ----------------------------------------------------------
# National ASFR (births per 1,000 women), DHS Table 5.1
ASFR_NAT = {
    "Ethiopia":    [80, 200, 214, 190, 138, 69, 22],   # EDHS 2016 FR328
    "Indonesia":   [36, 111, 138, 113, 63, 20, 4],     # IDHS 2017 FR342
    "Philippines": [25, 84, 105, 95, 58, 21, 2],       # NDHS 2022 FR381
    "South Africa":[71, 133, 139, 98, 62, 23, 2],      # SADHS 2016 FR337
}
# TFR by wealth quintile, DHS Table 5.2
TFR_Q = {
    "Ethiopia":    [6.4, 5.6, 4.9, 4.3, 2.6],
    "Indonesia":   [2.9, 2.6, 2.3, 2.3, 2.1],
    "Philippines": [3.1, 2.2, 2.0, 1.5, 1.4],
    "South Africa":[3.1, 2.9, 2.7, 2.3, 2.1],
}
# Teenage childbearing (% 15-19 who have begun childbearing) by wealth quintile,
# DHS Table 5.11/5.12  -- the AGE-TILT signal
TEEN_Q = {
    "Ethiopia":    [24.0, 17.3, 14.9, 8.1, 5.8],
    "Indonesia":   [12.5, 9.9, 6.8, 5.5, 1.5],
    "Philippines": [10.1, 5.4, 7.0, 2.7, 1.8],
    "South Africa":[20.0, 21.7, 18.3, 9.4, 6.5],
}
# South Africa ASFR (per 1,000) by population group, Stats SA Census 2011
# Report 03-01-63 Table 15 -- the only real full age x SES fertility matrix
SA_ASFR_GRP = {
    "Black African": [76, 128, 125, 106, 81, 42, 6],
    "Coloured":      [71, 137, 125, 94, 61, 24, 3],
    "Indian/Asian":  [20, 74, 117, 100, 47, 11, 2],
    "White":         [14, 57, 108, 106, 45, 10, 1],
}

# ---- MORTALITY DATA ----------------------------------------------------------
# Under-5 mortality (deaths per 1,000 live births) by wealth quintile, DHS API
U5MR_Q = {
    "Ethiopia":    [77, 73, 72, 62, 46],   # EDHS 2019
    "Indonesia":   [52, 33, 29, 31, 24],   # IDHS 2017
    "Philippines": [35, 23, 25, 13, 8],    # NDHS 2022
    "South Africa":[67, 52, 51, 34, 41],   # SADHS 2016 (noisy)
}
# Agincourt (rural South Africa) Relative Index of Inequality in mortality by
# age band & period (Kabudula 2017, Lancet GH, Table 3) -- LMIC age-shape
AGINCOURT_PERIODS = ["2001-03", "2004-07", "2008-10", "2011-13"]
AGINCOURT_RII = {
    "Children <5": [2.06, 1.37, 1.62, 2.38],
    "Women 15+":   [1.81, 1.55, 1.39, 1.29],
    "Men 15+":     [1.54, 1.33, 1.43, 1.38],
}
# Ethiopia life expectancy at birth by wealth quintile (Mekonnen 2013, modeled)
ETH_E0_Q = [53.4, 56.2, 60.6, 59.9, 62.5]

# =============================================================================
# FIGURE A -- FERTILITY
# =============================================================================
figA, ax = plt.subplots(2, 2, figsize=(13.5, 9.5))
figA.suptitle("Fertility by age and by income — OG-Core calibration countries",
              fontsize=15, fontweight="bold")

# (a) national ASFR schedules
for c, v in ASFR_NAT.items():
    ax[0, 0].plot(AGE_GROUPS, v, marker="o", color=C[c], label=c, lw=2)
ax[0, 0].set_title("(a) National age-specific fertility rate\n(the schedule each j-group must average back to)")
ax[0, 0].set_ylabel("births per 1,000 women")
ax[0, 0].legend(fontsize=8)
ax[0, 0].grid(alpha=0.3)

# (b) TFR by wealth quintile
x = np.arange(5)
for c, v in TFR_Q.items():
    ax[0, 1].plot(x, v, marker="s", color=C[c], label=c, lw=2)
ax[0, 1].set_title("(b) Total fertility rate by wealth quintile\n(the 'quantum' gradient)")
ax[0, 1].set_ylabel("TFR (children/woman)")
ax[0, 1].set_xticks(x); ax[0, 1].set_xticklabels(QUINT, fontsize=8)
ax[0, 1].legend(fontsize=8); ax[0, 1].grid(alpha=0.3)

# (c) teen childbearing by wealth quintile -- the age tilt
for c, v in TEEN_Q.items():
    ax[1, 0].plot(x, v, marker="^", color=C[c], label=c, lw=2)
ax[1, 0].set_title("(c) Teen childbearing (% of 15-19 begun) by wealth quintile\n"
                   "the AGE-TILT: poor childbear young (Indonesia flat TFR, 8x teen gap)")
ax[1, 0].set_ylabel("% of women 15-19 who have begun childbearing")
ax[1, 0].set_xticks(x); ax[1, 0].set_xticklabels(QUINT, fontsize=8)
ax[1, 0].legend(fontsize=8); ax[1, 0].grid(alpha=0.3)

# (d) South Africa ASFR by population group (real age x SES matrix)
grp_col = {"Black African": "#8c564b", "Coloured": "#e377c2",
           "Indian/Asian": "#7f7f7f", "White": "#17becf"}
for g, v in SA_ASFR_GRP.items():
    ax[1, 1].plot(AGE_GROUPS, v, marker="o", color=grp_col[g], label=g, lw=2)
ax[1, 1].set_title("(d) South Africa ASFR by group (Census 2011)\n"
                   "real age x SES matrix: curve shifts RIGHT as SES rises")
ax[1, 1].set_ylabel("births per 1,000 women")
ax[1, 1].legend(fontsize=8); ax[1, 1].grid(alpha=0.3)

figA.text(0.5, 0.005,
          "Sources: DHS final reports (EDHS 2016, IDHS 2017, NDHS 2022, SADHS 2016) Tables 5.1/5.2/5.11; "
          "Stats SA Census 2011 Fertility Report 03-01-63 Table 15.",
          ha="center", fontsize=7.5, style="italic")
figA.tight_layout(rect=[0, 0.02, 1, 0.96])
figA.savefig(f"{OUT}/fertility_overview.png", dpi=115)

# =============================================================================
# FIGURE B -- MORTALITY
# =============================================================================
figB, bx = plt.subplots(1, 3, figsize=(16, 5.2))
figB.suptitle("Mortality by age and by income — and why the LMIC age-shape differs",
              fontsize=15, fontweight="bold")

# (a) under-5 mortality by wealth quintile
for c, v in U5MR_Q.items():
    bx[0].plot(x, v, marker="o", color=C[c], label=c, lw=2)
bx[0].set_title("(a) Under-5 mortality by wealth quintile\n"
                "child gradient is steep & directly observed (DHS)")
bx[0].set_ylabel("under-5 deaths per 1,000 live births")
bx[0].set_xticks(x); bx[0].set_xticklabels(QUINT, fontsize=8)
bx[0].legend(fontsize=8); bx[0].grid(alpha=0.3)

# (b) Agincourt RII by age band -- the double-peak evidence
xp = np.arange(len(AGINCOURT_PERIODS))
band_col = {"Children <5": "#d62728", "Women 15+": "#9467bd", "Men 15+": "#1f77b4"}
for b, v in AGINCOURT_RII.items():
    bx[1].plot(xp, v, marker="D", color=band_col[b], label=b, lw=2)
bx[1].axhline(1.0, color="k", lw=0.8, ls="--", alpha=0.6)
bx[1].set_title("(b) South Africa: relative inequality in mortality by age\n"
                "CHILD gradient > adult gradient (Agincourt RII)")
bx[1].set_ylabel("Relative Index of Inequality (poorest:richest)")
bx[1].set_xticks(xp); bx[1].set_xticklabels(AGINCOURT_PERIODS, fontsize=8)
bx[1].legend(fontsize=8); bx[1].grid(alpha=0.3)

# (c) Ethiopia life expectancy by wealth quintile
bars = bx[2].bar(x, ETH_E0_Q, color=plt.cm.YlOrRd(np.linspace(0.3, 0.85, 5)))
bx[2].set_title("(c) Ethiopia life expectancy at birth by wealth quintile\n"
                "9-yr gap (Mekonnen 2013; adult portion modeled)")
bx[2].set_ylabel("life expectancy at birth (years)")
bx[2].set_xticks(x); bx[2].set_xticklabels(QUINT, fontsize=8)
bx[2].set_ylim(45, 65); bx[2].grid(alpha=0.3, axis="y")
for b, val in zip(bars, ETH_E0_Q):
    bx[2].text(b.get_x() + b.get_width()/2, val + 0.2, f"{val}", ha="center", fontsize=8)

figB.text(0.5, 0.005,
          "Sources: DHS API child mortality by wealth quintile; Kabudula et al. 2017 Lancet GH "
          "(Agincourt RII, PMC5559644); Mekonnen et al. 2013 Int J Equity Health (PMC3716728). "
          "Contrast: Nordic gradient is a single mid-life hump; LMIC is double-peaked (child + young-adult HIV/TB).",
          ha="center", fontsize=7.5, style="italic")
figB.tight_layout(rect=[0, 0.03, 1, 0.94])
figB.savefig(f"{OUT}/mortality_overview.png", dpi=115)

print("wrote:", sorted(os.listdir(OUT)))
