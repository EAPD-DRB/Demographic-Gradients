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

- [ ] **A1. Log-odds vs log-rate.** ogcore reads a slope as log-odds; the library
  publishes a log-rate tilt. Negligible for mortality; about 10% at peak
  fertility ages under ogcore's births-per-person scaling (rates / 2000).
  *Validate:* feed both slopes through ogcore's own mean-preserving logit and
  check which reproduces the measured quintile ratios. *Decide:* publish a
  log-odds column (in ogcore's scaling) or convert in the helper (C1).
  Settle this first — it fixes the units of A2, A3 and C1.
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

- [R] **C1. Consumer output.** OG-ETH and OG-PHL each wrote ~100 lines of glue
  and made different choices. Ship one: per-country single-age gradients in
  ogcore units (fertility by age, infant, ages 1–4, adult by age) as CSV, plus
  a small dependency-free reference function for the time path (B2).
  *Ruling needed:* whether the library ships Python code at all (it has been
  data plus build scripts so far).
  *Validate:* reproduce OG-ETH's and OG-PHL's current arrays exactly from the
  new output where the rules agree, and run `get_pop_objs` end to end to
  confirm the UN aggregates are preserved.
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
- After C1 ships, OG-ETH and OG-PHL can replace their glue with it.
