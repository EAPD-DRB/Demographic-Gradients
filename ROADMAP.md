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
- [x] **A2. Age-specific fertility tilts.** Both repos pass one TFR tilt, but the
  gradient is U-shaped by age. *Done 2026-11-05:* DHS age-specific rates by
  wealth quintile (`FE_FRTR_W_A15`…`A45`) now pulled by
  `build_gradient_library.py`. 5 × Σ ASFR reproduces DHS's TFR per quintile
  within rounding. *Ruling:* publish pooled **age offsets** to add to the TFR
  tilt (`fertility_age_offsets.csv`), not per-country age tilts — a country's
  own age shape predicts its next survey no better (backtest in the same
  file). Docs: `docs/methods/fertility-by-age.md` (generated, with fig6),
  ANALYSIS.md, country pages, AGENTS.md, README, skill.
- [R] **A3. Child mortality at ages 1–4.** Both repos use the under-5 tilt there,
  which includes infant deaths. DHS publishes 4q1 by wealth (`CM_ECMR_C_CMR`).
  *Validated 2026-11-11:* (1 − IMR)(1 − CMR) reproduces DHS's U5MR in all
  1,461 quintile cells within 1.4 per 1,000 (rounding). 291 surveys,
  78 countries; 14 unfittable (a quintile with no child deaths). The ages 1–4
  gradient is much steeper than under-5: median tilt −1.36 vs −0.82 (poorest-to-richest
  ratio 3.0 vs 1.9); steeper in 79% of countries. Unlike fertility
  by age, a country's own value is signal: predicting the next survey's
  ages 1–4 tilt, own previous value MAE 0.43, U5MR + pooled offset 0.43,
  plain U5MR (status quo) 0.61; test-retest r 0.70 (U5MR 0.75).
  *Ruling needed:* publish the ages 1–4 tilt per country as indicator `CMR`
  in the library files (fallback where unfittable: U5MR tilt + pooled offset).

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

## E. Documentation for readers with no context

- [x] **E1. Front door, figures, glossary (2026-11-11).** README cut to a short
  front door with a generated coverage table; seven figures rebuilt to one
  standard (finding as title, poorest-to-richest ratio, one accent), including
  two new ones: what a gradient is, and adult mortality against income;
  `docs/glossary.md`, `docs/data-files.md`, `docs/sources.md`; ANALYSIS.md
  rewritten as seven findings; a page for every country (80) opening with
  "What to use in OG-Core".

## Downstream — not this repo, tracked so they are not lost

- OG-PHL: gradient work sits on `calib/multi-industry-remittances`, never pushed.
- OG-ZAF: passes no gradients, despite the library's best-measured country.
- OG-IDN, OG-BRA: no gradients.
- OG-ETH, OG-PHL: still pass plain `tilt / 100` and one TFR tilt at every
  age; switch to the A1 conversion and the A2 age offsets, then align with
  the C1 recipe once written.
- Rwanda: the 2025 DHS appeared in the API (pull of 2026-11-05) and replaced
  the 2019/2023 rows; its quintile cells are noisy (IMR Q4 > Q1).
