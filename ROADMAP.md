# Roadmap: lessons from the country repos (opened 2026-11-05)

A review of how the OG country repos consume this library (OG-ETH in production,
OG-PHL on an unpushed branch, OG-ZAF plumbing only) exposed the items below.
Each is validated before anything is published, and worked in order: earlier
items fix the units and rules that later ones build on.

**None of this needs a change to OG-Core.** Checked against ogcore 0.24.1
(`ogcore/demographics.py`): `fert_gradient` and `mort_gradient` accept a
scalar, a per-age vector (length S or E+S), or a period-by-age array, and are
applied per period and per age with the UN rate preserved
(`_mean_preserving_logit_rates`); `infmort_gradient` is a scalar per period.
Everything can be built here for calibrations to ingest.

Status: `[ ]` open · `[~]` in progress · `[x]` done · `[R]` needs Marcelo's ruling

## A. Units and inputs (data the library publishes)

- [x] **A1. Log-odds vs log-rate.** ogcore reads a slope as log-odds; the library
  publishes a log-rate tilt. *Done:* every measured quintile set run through
  ogcore 0.24.1's own functions (`scripts/check_ogcore_units.py`,
  `data/ogcore_units_check.csv`). Plain `tilt / 100` leaves gradients too flat
  — about 1% for mortality from age 1, 2.6% for infant, 3–7% for fertility.
  *Ruling:* adapt to ogcore as it is; calibrations pass
  `tilt / (100 × (1 − p))` with p = ogcore's own rate array, which gives the
  by-age and by-year conversion in one line and lands within 1% of exact
  almost everywhere. The library keeps publishing the log-rate tilt.
  Documented in `docs/methods/ogcore-units.md`, AGENTS.md, README and the
  og-country-calibration skill.
- [ ] **A2. Age-specific fertility tilts.** Both repos pass one TFR tilt, but the
  gradient is U-shaped by age (median −1.51 at 15–19, −0.40 at 30–34;
  Indonesia +0.05 at 25–29). DHS publishes ASFR by wealth quintile
  (`FE_FRTR_W_A15`…`A45`; 313 surveys, 77 countries).
  *Validate:* 5 × Σ ASFR per quintile must reproduce DHS's published TFR per
  quintile; and through ogcore, the age-level UN rates stay fixed while the
  TFR gradient comes out right.
- [ ] **A3. Child mortality at ages 1–4.** Both repos use the under-5 tilt there,
  which includes infant deaths. DHS publishes 4q1 by wealth (`CM_ECMR_C_CMR`).
  *Validate:* per quintile, (1 − IMR)(1 − CMR) must reproduce 1 − U5MR.

## B. Rules a calibration needs (method documentation)

- [R] **B1. Adult tilt at ages 45+.** OG-ETH applies none (the measured bands
  reverse); OG-PHL applies the general-gradient offsets (+0.13, +0.40), which
  AGENTS.md calls the least trustworthy numbers here. One documented rule.
  *Validate:* show the effect of each choice on survival from 20 to 65 and on
  life expectancy at 65 by group, so the ruling is made on consequences.
- [R] **B2. Updating a stale measurement.** OG-ETH's method: measured tilt plus
  the income rule's change since the census year, then along the model's
  growth path, capped at $10,000 GNI. OG-PHL uses the rule's level directly.
  *Validate:* backtest on the library's within-country pairs — Malawi
  1998 → 2008, South Africa 2001 → 2007 → 2011 — predicting the later tilt
  from the earlier one plus the rule's change.

## C. Something calibrations can ingest

- [ ] **C1. A written recipe, no code.** OG-ETH and OG-PHL each wrote ~100
  lines of glue and made different choices. *Ruling:* the library stays data
  plus build scripts — no package for consumers (an exact-solver package was
  built and dropped: it beat the one-line conversion by under 1%). The fix is
  one recipe in AGENTS.md: which rows to pick, the A1 conversion, and the B1
  and B2 rules. Write it once B1 and B2 are ruled.
- [ ] **C2. Provenance pages and AGENTS.md** updated to the new inputs and rules
  (generated pages via `build_analysis.py`).

## D. Coverage gaps (separate tracks)

- [ ] **D1. An Asian adult-mortality observation.** None exists, so the
  Philippines and Indonesia rest on the income rule. Routes: Vietnam 1999
  census (mortality as household-record variables, untried), or published
  IFLS life tables by consumption quartile (Sudharsanan 2019).
- [ ] **D2. `imm_pctiles`** — the lifetime-income distribution of new
  immigrants. Not covered. Scope before building.

## Downstream — not this repo, tracked so they are not lost

- OG-PHL: gradient work sits on `calib/multi-industry-remittances`, never pushed.
- OG-ZAF: passes no gradients, despite the library's best-measured country.
- OG-IDN, OG-BRA: no gradients.
- OG-ETH, OG-PHL: still pass plain `tilt / 100`; switch to the A1 conversion,
  then align with the C1 recipe once written.
