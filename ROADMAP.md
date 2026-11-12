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
  reverse); OG-PHL applies the general-gradient offsets (then +0.13, +0.40;
  +0.13, +0.49 since G1), which
  AGENTS.md calls the least trustworthy numbers here. One documented rule.
  *Validate:* show the effect of each choice on survival from 20 to 65 and on
  life expectancy at 65 by group, so the ruling is made on consequences.
- [R] **B2. Updating a stale measurement.** OG-ETH's method: measured tilt plus
  the income rule's change since the census year, then along the model's
  growth path, capped at $10,000 GNI. OG-PHL uses the rule's level directly.
  *Validate:* backtest on the library's within-country pairs — Malawi
  1998 → 2008, South Africa 2001 → 2007 (2011 withdrawn in G1) — predicting the later tilt
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
  IFLS life tables by consumption quartile (Sudharsanan 2019). Cambodia 2008
  passes every check but is held (ruling 2026-11-11): 1,250 adult death
  records, no band reaches 900, 45q15 gradient −0.73; revisit with a second
  Asian source (Benin 2013, published, is comparably thin: 1,555 records,
  35% coverage, so the hold rests on the Asian question, not the checks).
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

## F. Questions raised by the documentation review (2026-11-11)

- [R] **F1. GNI price basis.** The general gradient is fitted on GNI in current
  dollars of the census years (1998–2013) and applied to recent current-dollar
  GNI. Price change since then makes predicted gradients about 0.1–0.15 steeper
  (close to one residual SD). Option: deflate GNI to a common year before
  fitting and applying. Disclosed in the docs meanwhile.
- [R] **F2. Brazil `infmort_gradient`.** The country page uses the 2010 census
  child-mortality gradient (−0.96 on the PCA index), an under-five-type measure that probably
  overstates the infant gradient; the alternative is the 1996 DHS infant
  gradient (−1.37). Both are now shown on the page.
- [x] **F3. 45q15 publication threshold.** Ruled 2026-11-11: 45q15 needs 900
  death records at 15–59, as the bands do. Cambodia 2008 is now
  `publish=False` (held).
- [x] **F4. Completeness check in code.** `estimate` now prints the MORTNUM
  comparison by wealth group for every sample (2026-11-11); it rejected
  South Africa 2011 and Mozambique 2007 on the PCA index and shows South
  Africa 2007 passing. The linkage composition comparison stays manual; it
  only concerned South Africa 2011, now unpublished.
- [ ] **F5. Senegal 2002 death counts.** `n_deaths` repeats exactly (1,086 for
  15–29 and 30–44; 1,311 for 60–74 and male 45q15), and still does on the PCA
  index. Check against the microdata.
- [x] **F6. Uncertainty of the income rule (2026-11-12).** Standard OLS
  inference: residual standard error with n − 2 df (0.177, was 0.170 with
  n − 1), coefficient SEs and 95% CIs, and the 95% prediction interval
  (~±0.4) published with every value read off the rule; the figure shows the
  confidence and prediction bands. Clustered-by-country SE (0.046) and one
  census per country (slope −0.296) as sensitivity checks.
- [x] **F7. GNI download (2026-11-12).** A transient World Bank API failure
  silently dropped Sierra Leone from a re-run (the old code turned any
  non-data reply into "no value"). Now: retries, then a hard error; and GNI is
  pinned in `data/gni_census_years.csv` with retrieval dates, because WDI
  revises historical values. `--refresh-gni` re-downloads deliberately.

## G. Wealth index (2026-11-11)

- [x] **G1. Census asset index: principal components.** Coding errors found in
  the additive score (INTERNET and WASHER scored backwards, TV codes 21-43
  ignored, latrine scored as flush). Replaced, on Marcelo's ruling, by the
  standard first-principal-component index (Filmer and Pritchett 2001; DHS;
  Lovaton Davila et al. 2022), groups cut on the household population.
  Shared module `scripts/asset_index.py`. Done 2026-11-11 with the rulings:
  groups under 10% merged, gradient weighted by group share, at least three
  groups (Rwanda 2002 withheld), 45q15 needs 900 records; South Africa 2011
  and Mozambique 2007 withheld on the completeness check; Malawi 1998
  published with a caveat; Brazil rebuilt from IBGE with
  `build_adult_mortality_brazil.py` (restored). Result: 15 censuses in 13
  countries; general gradient 1.639 − 0.302 ln(GNI), LOO MAE 0.175.
- [ ] **G2. Compare with Marcelo's improved wealth index** (code change to the
  PCA calculation; materials in `~/Downloads/Inequality`, incl. Wittenberg and
  Leibbrandt 2015) once the PCA rebuild is complete; decide which to use.

## H. New data sources (opened 2026-11-12)

Found by a source review on 2026-11-12. Worked one at a time; each is
validated before anything is published. Cambodia 2008 (D1) stays held until
these are done, since they may change the picture for Asia.

- [x] **H1. DHS access (2026-11-12).** The "OG Model calibrations" project
  (approved 2026-07-30) covers 87 countries, India, Pakistan, Philippines,
  Indonesia, Bangladesh, Vietnam and Cambodia included; nothing to request.
  Microdata come only through the logged-in site (the DHS API serves
  indicators, not microdata); files are kept in `~/Projects/data/dhs/`,
  never in the repo. A label scan of 42 household recodes (Asian surveys
  since 1997 plus every survey tagged for causes of death or verbal autopsy)
  found household-reported deaths of all ages with sex, age and date in
  **India NFHS-1 1992–93** (deaths in the last two years), **NFHS-2 1998–99**
  (since January 1996), **NFHS-4** (since January 2011), **NFHS-5**, and
  **Pakistan 2006–07** (since January 2003). NFHS-1 and NFHS-2 need DHS's
  separate wealth-index files (IAWI22, IAWI41, downloaded). Not found in:
  Philippines 2003–2022, Indonesia 2007–2017, Bangladesh, Nepal, Cambodia
  2000–2021, Myanmar, Timor-Leste, Vietnam 2002, Pakistan 2012/2017,
  Afghanistan, Maldives, Honduras, Haiti, Bolivia 1994 (death counts or
  accident and child modules only). Africa not yet scanned.
- [x] **H2. India NFHS-1, -2, -4, -5 and Pakistan 2006–07: adult mortality
  from household-reported deaths.** Household files list deaths of usual members
  with sex, age and date, ranked by the DHS wealth index — the census design,
  not sibling histories. Published benchmark: Dhakad & Saikia, *Demographic
  Research* 55(16), 2026. Method ruled 2026-11-12: deaths in the 24 months
  before interview over 2 × the de jure population; DHS wealth quintiles,
  OLS; same 900-record minimum; rows go into `adult_mortality_gradients.csv`
  with a DHS `source` (`scripts/build_adult_mortality_survey.py`); survey
  rows enter the income rule on the same footing as censuses (ruled
  2026-11-12). Done 2026-11-12:
  - [x] NFHS-2 1998–99 (labelled 1999): 45q15 −0.733 (SE 0.055), 2,422 records;
    men −0.72, women −0.76 (benchmark −0.71/−0.68); national 45q15 243/197
    against WDI 250/192. Only the 45–59 and 60–74 bands reach 900 records.
  - [x] NFHS-4 2015–16 (2015): −0.742 (SE 0.050), 11,330 records; men −0.65,
    women −0.94 (benchmark −0.61/−0.88); window 12/24/36 months
    −0.72/−0.74/−0.72; heaping falls with wealth but boundary split gives
    −0.762; national 194/117 against WDI 205/141.
  - [x] NFHS-5 2019–21 (2020): −0.725 (SE 0.042), 11,994 records; men −0.73,
    women −0.74 (benchmark −0.69/−0.68). Before March 2020 only −0.763
    (86% of exposure); from March 2020 −0.564. Full window kept.
  - [x] NFHS-1 1992–93: not published — age at death blank for every record
    in the released recode (DHS .FRQ confirms).
  - [x] Pakistan 2006–07: not published — assets only in the 13.8k long-form
    households, 848 adult deaths in the window (698 women).
  - Rule now 1.481 − 0.286 ln(GNI), n = 17, r −0.84, residual SE 0.208, LOO
    MAE 0.176. India's gradient is flat over 1999–2020 while GNI quadrupled;
    long-run guidance changed from "should steepen" to a fixed/rule range.
- [ ] **H3. World Bank "HNP Statistics by Wealth Quintile"** (API source 39):
  TFR, IMR and U5MR by quintile from DHS and MICS. Count the countries it adds
  beyond the DHS API, and check its values against ours where both exist.
- [ ] **H4. Constant-price GNI** (WDI constant 2015 US$ or constant PPP) for
  the income rule — resolves F1's price-basis problem.
- [ ] **H5. IPUMS mortality supplements not yet tried:** Mali 1987 and 1998,
  Malawi 1987, Benin 1992 and 2002, El Salvador 1992, Indonesia 1976, Guinea
  1983, Lesotho 1996. Same pipeline and gates; adds points to the income rule.
- [ ] **H6. Colombia 2018 census** (DANE, free download): deaths in 2017 by
  age and sex, with death-certificate flag. Housing and services only (no
  durable goods), so the index is coarse.
- [ ] **H7. Bangladesh BMMS 2016** (all household deaths in three years,
  ~298,000 households; UNC Dataverse). Access terms and wealth index
  unverified.
- [ ] **H8. Indonesia IFLS** (RAND, free with registration): cross-check only;
  published wealth-quartile life expectancy in Sudharsanan (2019).
- [ ] **H9. MORTNUM-only IPUMS samples** (Vietnam 1989/1999, Indonesia 2010,
  Cambodia 2004/2013/2019, Bolivia, Colombia 2005 and others): no age at
  death, so would need a new all-ages method. Not before H2–H6.

## Downstream — not this repo, tracked so they are not lost

- OG-PHL: gradient work sits on `calib/multi-industry-remittances`, never pushed.
- OG-ZAF: passes no gradients, despite the library's best-measured country.
- OG-IDN, OG-BRA: no gradients.
- After G1 the published values moved: general-gradient slope −0.244 →
  −0.302 (OG-ETH hard-codes −0.2443 for its income path); Philippines
  −0.76 → −0.90 (OG-PHL); Indonesia −0.79 → −0.93; Ethiopia's own 45q15
  +0.09 → +0.01; South Africa's latest becomes 2007, −1.23 (was 2011, −0.80);
  age offsets 15–29 −0.41 → −0.44, 30–44 −0.20 → −0.27, 60–74 +0.40 → +0.49.
  Update once pushed.
- After H2 (India surveys in the rule) they moved again: slope −0.302 →
  −0.286, intercept 1.639 → 1.481; Philippines −0.90 → −0.92 (PI −1.41 to
  −0.44); Indonesia −0.93 → −0.95; age offsets 15–29 −0.47, 30–44 −0.27,
  45–59 +0.13, 60–74 +0.43. India gets its own estimate (NFHS-5, −0.72).
- OG-ETH, OG-PHL: still pass plain `tilt / 100` and one TFR tilt at every
  age; switch to the A1 conversion and the A2 age offsets, then align with
  the C1 recipe once written.
- Rwanda: the 2025 DHS appeared in the API (pull of 2026-11-05) and replaced
  the 2019/2023 rows; its quintile cells are noisy (IMR Q4 > Q1).
