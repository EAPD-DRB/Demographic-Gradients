"""
Additional views:
  1. Illustrative fertility[age, j]   (national ASFR + age-tilt, aggregate-consistent)
  2. Per-country mortality stitch      (poorest:richest R[age], observed anchors + holes)
  3. Adult gradient, all 4             (top-vs-bottom life-expectancy gap)
  4. LMIC vs Nordic shape schematic    (double-peak vs single-hump)
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
QUINT = ["Lowest", "Second", "Middle", "Fourth", "Highest"]
qcol = plt.cm.viridis(np.linspace(0.1, 0.85, 5))

# =============================================================================
# 1. ILLUSTRATIVE fertility[age, j]  (Ethiopia: quantum+tempo ; Indonesia: tempo only)
# =============================================================================
xp = [12, 17, 22, 27, 32, 37, 42, 47, 52]
NAT = {"Ethiopia":  [0, 80, 200, 214, 190, 138, 69, 22, 0],
       "Indonesia": [0, 36, 111, 138, 113, 63, 20, 4, 0]}
TFR_Q = {"Ethiopia":  [6.4, 5.6, 4.9, 4.3, 2.6],
         "Indonesia": [2.9, 2.6, 2.3, 2.3, 2.1]}
DELTA = [-2.5, -1.25, 0.0, 1.25, 2.5]     # tempo shift (yrs): poor younger, rich later
lam = 0.2                                  # equal illustrative group shares
ages = np.arange(15, 50)

fig1, ax1 = plt.subplots(1, 2, figsize=(14, 5.4))
fig1.suptitle("(1) Illustrative  fertility[age, income group]  — national ASFR + age-tilt,\n"
              "constrained so the equal-weighted group average reproduces the national schedule",
              fontsize=13, fontweight="bold")
for k, country in enumerate(["Ethiopia", "Indonesia"]):
    nat = np.interp(ages, xp, NAT[country])
    raw = []
    for j in range(5):
        shifted = np.interp(ages - DELTA[j], xp, NAT[country])
        shifted = np.clip(shifted, 0, None)
        scale = TFR_Q[country][j] * 1000.0 / shifted.sum()
        raw.append(shifted * scale)
    raw = np.array(raw)
    agg = lam * raw.sum(axis=0)
    fert = raw * (nat / np.where(agg == 0, 1, agg))      # aggregate-consistency
    for j in range(5):
        ax1[k].plot(ages, fert[j], color=qcol[j], lw=2,
                    label=f"{QUINT[j]} (TFR≈{fert[j].sum()/1000:.1f})")
    ax1[k].plot(ages, nat, "k--", lw=2.2, label="National (aggregate)")
    note = "big quantum + tempo gap" if country == "Ethiopia" else "near-flat TFR — tilt ONLY"
    ax1[k].set_title(f"{country}  ({note})")
    ax1[k].set_xlabel("age"); ax1[k].set_ylabel("births per 1,000 women")
    ax1[k].legend(fontsize=7.5); ax1[k].grid(alpha=0.3)
fig1.text(0.5, 0.005, "Illustrative construction: national ASFR (DHS Table 5.1) shifted by a tempo offset and "
          "scaled to observed TFR-by-quintile (Table 5.2). Indonesia shows why scaling alone fails: same heights, "
          "different age-shape.", ha="center", fontsize=7.5, style="italic")
fig1.tight_layout(rect=[0, 0.02, 1, 0.92])
fig1.savefig(f"{OUT}/fertility_age_j_illustrative.png", dpi=115)

# =============================================================================
# 2. PER-COUNTRY MORTALITY STITCH  (poorest:richest mortality ratio across age)
#    anchors: filled=observed band, holes 5-15 & old-age taper shown dashed
# =============================================================================
STITCH = {
 "Ethiopia":    [(0.5,1.45,1),(3,2.9,1),(10,1.6,0),(35,2.0,1),(50,2.0,1),(70,1.3,0),(85,1.05,0)],
 "Indonesia":   [(0.5,2.0,1),(3,3.3,1),(10,1.6,0),(35,1.3,1),(50,1.3,1),(70,1.1,0),(85,1.0,0)],
 "Philippines": [(0.5,4.0,1),(3,4.4,1),(10,2.0,0),(35,1.7,0),(50,1.7,0),(70,1.2,0),(85,1.0,0)],
 "South Africa":[(0.5,1.4,1),(3,4.0,1),(10,2.0,0),(25,2.3,1),(40,2.1,1),(55,1.5,1),(70,1.2,0),(85,1.0,0)],
}
src_note = {"Ethiopia":"child: DHS · adult 15-64: Butajira HDSS",
            "Indonesia":"child: DHS · adult 30-60: IFLS (men)",
            "Philippines":"child: DHS · adult: NO direct (area-SES/borrowed)",
            "South Africa":"child: DHS · adult: Agincourt + HIV/TB young-adult hump"}
fig2, ax2 = plt.subplots(2, 2, figsize=(13.5, 9))
fig2.suptitle("(2) Per-country mortality stitch:  poorest : richest mortality ratio across age\n"
              "filled = observed band   ·  open/dashed = interpolated hole (5–15 everywhere; old-age taper)",
              fontsize=13, fontweight="bold")
for ax, (country, pts) in zip(ax2.ravel(), STITCH.items()):
    a = np.array([p[0] for p in pts]); r = np.array([p[1] for p in pts]); ob = np.array([p[2] for p in pts])
    g = np.linspace(a.min(), a.max(), 200)
    ax.plot(g, PchipInterpolator(a, r)(g), color="0.6", lw=1.5, ls="--", zorder=1)
    ax.scatter(a[ob == 1], r[ob == 1], color="#d62728", s=55, zorder=3, label="observed")
    ax.scatter(a[ob == 0], r[ob == 0], facecolors="none", edgecolors="0.5", s=55, zorder=3, label="interpolated")
    ax.axhspan(0.95, 1.0, color="0.9"); ax.axhline(1, color="k", lw=0.7)
    ax.axvspan(5, 15, color="#ffe9b3", alpha=0.5, zorder=0)   # the 5-15 hole
    ax.text(10, 0.5 + ax.get_ylim()[1]*0.0, "5–15\nhole", ha="center", va="bottom", fontsize=7, color="#b8860b")
    ax.set_title(f"{country}\n{src_note[country]}", fontsize=9.5)
    ax.set_xlabel("age"); ax.set_ylabel("poorest : richest mortality ratio")
    ax.set_ylim(0.9, 4.7); ax.grid(alpha=0.3); ax.legend(fontsize=7, loc="upper right")
fig2.text(0.5, 0.005, "Illustrative: ratios at observed anchors from cited sources (child cells noisy in PHL/ZAF — small "
          "denominators); 5–15 and old-age tapers interpolated. The gradient is age-VARYING: steep at 1–5, second "
          "(HIV/TB) hump in young adults for ZAF, compressing toward 1 at old age.", ha="center", fontsize=7.3, style="italic")
fig2.tight_layout(rect=[0, 0.02, 1, 0.93])
fig2.savefig(f"{OUT}/mortality_stitch.png", dpi=115)

# =============================================================================
# 3. ADULT GRADIENT, ALL 4  (top-vs-bottom life-expectancy gap, metric labeled)
# =============================================================================
countries = ["Ethiopia", "Indonesia", "South Africa", "Philippines"]
gap = [9.1, 3.6, 12.0, 0.0]
metric = ["e0 by wealth quintile\n(Mekonnen 2013, modeled)",
          "e30 by wealth quartile,\nmen (IFLS/Sudharsanan)",
          "LE by wealth quintile\n(Agincourt HDSS)",
          "NO direct estimate\n(area-SES only)"]
ccol = ["#d62728", "#2ca02c", "#ff7f0e", "#1f77b4"]
fig3, ax3 = plt.subplots(figsize=(9.5, 5.6))
fig3.suptitle("(3) Adult mortality gradient, all four — top-vs-bottom life-expectancy gap",
              fontsize=13, fontweight="bold")
bars = ax3.bar(countries, gap, color=ccol, alpha=0.85)
bars[3].set_hatch("//"); bars[3].set_alpha(0.35)
for b, g_, m in zip(bars, gap, metric):
    if g_ > 0:
        ax3.text(b.get_x()+b.get_width()/2, g_+0.2, f"{g_:.1f} yr", ha="center", fontweight="bold")
    ax3.text(b.get_x()+b.get_width()/2, 0.4, m, ha="center", va="bottom", fontsize=7.5, color="white" if g_ > 2 else "0.3")
ax3.set_ylabel("life-expectancy gap, richest − poorest SES group (years)")
ax3.set_ylim(0, 13.5); ax3.grid(alpha=0.3, axis="y")
fig3.text(0.5, 0.005, "Caveat: metrics differ — ETH e0 (includes child mortality) vs IDN e30 (adult-only) vs ZAF HDSS LE. "
          "Magnitudes are not strictly comparable; PHL has no domestic adult-by-income estimate.",
          ha="center", fontsize=7.5, style="italic")
fig3.tight_layout(rect=[0, 0.03, 1, 0.94])
fig3.savefig(f"{OUT}/adult_gradient_all4.png", dpi=115)

# =============================================================================
# 4. LMIC vs NORDIC SHAPE SCHEMATIC
# =============================================================================
ag = np.linspace(0, 90, 300)
nordic_a = [0, 10, 30, 45, 58, 72, 90]; nordic_r = [1.15, 1.10, 1.25, 1.55, 1.72, 1.45, 1.18]
lmic_a   = [0, 2, 8, 15, 25, 35, 45, 55, 70, 85]; lmic_r = [1.7, 2.6, 1.7, 1.4, 1.9, 2.1, 1.85, 1.6, 1.25, 1.05]
fig4, ax4 = plt.subplots(figsize=(10.5, 5.8))
fig4.suptitle("(4) Why not borrow the Nordic shape: where the SES–mortality gradient lives across age",
              fontsize=13, fontweight="bold")
ax4.plot(ag, PchipInterpolator(nordic_a, nordic_r)(ag), color="#1f77b4", lw=2.6, label="Nordic / high-income (single mid-life hump)")
ax4.plot(ag, PchipInterpolator(lmic_a, lmic_r)(ag), color="#d62728", lw=2.6, label="Developing (double-peak)")
ax4.axhline(1, color="k", lw=0.7)
ax4.annotate("childhood spike\n(infectious / nutrition)", (3, 2.6), (12, 2.9), fontsize=8,
             color="#d62728", arrowprops=dict(arrowstyle="->", color="#d62728"))
ax4.annotate("young-adult hump\n(HIV/TB, injury, maternal)", (35, 2.1), (40, 2.55), fontsize=8,
             color="#d62728", arrowprops=dict(arrowstyle="->", color="#d62728"))
ax4.annotate("NCD / 'deaths of despair'\n(peak of HIC gradient)", (58, 1.72), (30, 1.0), fontsize=8,
             color="#1f77b4", arrowprops=dict(arrowstyle="->", color="#1f77b4"))
ax4.annotate("old-age compression\n(both)", (82, 1.12), (66, 0.78), fontsize=8, color="0.3",
             arrowprops=dict(arrowstyle="->", color="0.4"))
ax4.set_xlabel("age"); ax4.set_ylabel("poorest : richest mortality ratio (schematic)")
ax4.set_ylim(0.7, 3.1); ax4.legend(fontsize=9, loc="upper right"); ax4.grid(alpha=0.3)
fig4.text(0.5, 0.005, "Schematic, grounded in: Agincourt RII child>adult; SA male modal age-at-death 40–44 at AIDS peak; "
          "INDEPTH age-stratified RRs; comparative finding that relative gradients are steeper in high- than middle-income.",
          ha="center", fontsize=7.4, style="italic")
fig4.tight_layout(rect=[0, 0.03, 1, 0.94])
fig4.savefig(f"{OUT}/shape_schematic.png", dpi=115)

print("wrote:", sorted(f for f in os.listdir(OUT) if f.endswith(".png")))
