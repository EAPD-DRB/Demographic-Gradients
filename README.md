# Demographic-Gradients

A borrowable library of **demographic wealth gradients** for the OG-Core country
model family (OG-USA, OG-ZAF, OG-PHL, OG-IDN, OG-ETH, OG-BRA, ...). It measures how
fertility and under-5 mortality tilt across the household wealth distribution —
identically, in 601 DHS surveys across 78 countries — so that a country calibration
can set OG-Core's income-group demographic gradients (`fert_gradient`,
`mort_gradient`, ogcore >= 0.18.0) from its own survey, or borrow a defensible
range when it has no data of its own.

This repo plays the same role for demographic *differentials* that
[EAPD-DRB/Population-Data](https://github.com/EAPD-DRB/Population-Data) plays for
population *levels*: a stable mirror the country repos can reference by raw URL.

**Visual report:** [interactive version](https://claude.ai/code/artifact/28e22a84-7bdf-408f-8770-139b178c8e49)
(hosted; requires access) or open [`gradient_library.html`](gradient_library.html)
from this repo in any browser — both show all four figures with the numbers below.

## The headline numbers (latest survey per country)

| Margin | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Fertility (TFR) | 77 | **−0.79** | −0.97 to −0.53 | 1.90 |
| Under-5 mortality | 78 | **−0.82** | −1.16 to −0.54 | 1.96 |

The **tilt** is the OLS slope of ln(rate) on wealth-rank percentile midpoints
(quintiles at the 10th...90th percentile) — the same log-scale OG-Core's
income-group demographics consume. A tilt of −0.79 means the poorest decile's rate
is about e^(0.79×0.8) ≈ 1.9× the richest decile's. Negative = poor higher.

Two structural findings from the library:

1. **The gradients are near-universal**: essentially every country's fertility and
   child-mortality rates decline with wealth rank.
2. **They are stable**: the pooled median tilt is flat across 35 years of surveys
   (1990–2024). A borrowed gradient is not a decaying quantity.

## How a country repo uses this

1. **Own data first.** If the country has a DHS with wealth-quintile tables (78
   do), read its own tilt from `data/gradient_library_latest.csv`.
2. **No own data.** Borrow the regional median as the central value and use the
   regional IQR as the sensitivity band (see `figures/fig3_slopes_by_region.png`
   and the regional table in the notebook page). Both beat the current default of
   assuming no gradient at all — which the library shows is wrong essentially
   everywhere.
3. **Mapping to OG-Core.** OG-Core (>= 0.18.0) applies gradients at each
   lifetime-income group's percentile midpoint and preserves the UN aggregate
   rates automatically. The quintile-based tilt here is measured on household
   asset rank — the standard LMIC proxy for economic rank; note the assumption
   (asset rank ≈ lifetime-income rank) in your calibration docs, and note that no
   quintile design resolves a top-1% group.

## Contents

```
data/
  dhs_gradients_raw.csv         quintile-level observations (indicator, country,
                                survey year, quintile, value)
  gradient_library.csv          one tilt per survey (601 rows): slope, poorest/
                                richest ratio, and the five quintile values
  gradient_library_latest.csv   most recent survey per country (the library view)
  dhs_regions.csv               DHS Program country -> region map
figures/
  fig1_tfr_gradients.png        every country's fertility gradient, individually
  fig2_u5mr_gradients.png       every country's under-5 mortality gradient
  fig3_slopes_by_region.png     the distribution of tilts, grouped by region
  fig4_slopes_over_time.png     tilt stability across 35 years of surveys
scripts/
  build_gradient_library.py     rebuilds data/ from the DHS API (uv run, no setup)
  make_figures.py               rebuilds figures/ from data/ (uv run, no setup)
ADULT_MORTALITY.md              the separate evidence base for ADULT mortality
                                gradients (not measurable by DHS-type surveys)
gradient_library.html           self-contained visual report (open in a browser)
```

## Reproducibility

Everything is rebuilt from public, registration-free sources with two commands:

```
uv run scripts/build_gradient_library.py
uv run scripts/make_figures.py
```

Data source: the [DHS Program indicator API](https://api.dhsprogram.com)
(indicators `FE_FRTR_W_TFR`, `CM_ECMR_C_U5M`, characteristic "Wealth quintile").
Wealth quintiles are the DHS household asset index. Surveys with incomplete
quintets are dropped, never imputed. Data vintage of the committed CSVs:
API pull of 23 July 2026.

When citing, credit the DHS Program as the data source alongside this repo.

## Scope and honest limits

- **Adult mortality is not in this library and cannot be**: surveys don't observe
  the dead, and sibling-history methods carry no wealth information. The evidence
  base for adult-mortality gradients is panel and registry studies, collected in
  [ADULT_MORTALITY.md](ADULT_MORTALITY.md).
- Quintiles are household-based cross-sections, not lifetime individual rank.
- U5MR quintile cells are noisy in low-mortality countries.
- Immigration by income: no usable source exists, anywhere, as of July 2026.
