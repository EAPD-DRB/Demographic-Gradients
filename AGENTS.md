# Demographic-Gradients: guidance for agents

## Answering calibration questions

Use [`docs/calibration-guide.md`](docs/calibration-guide.md) and the country's
page in [`docs/countries/`](docs/countries/README.md). Both are generated from
the data, so their values are current; do not quote values from memory or from
older notes. Terms are in [`docs/glossary.md`](docs/glossary.md).

The rules, in brief (the guide gives the values and the reasons):

- Use the country's own estimate where there is one. Otherwise use the general
  gradient for adult mortality (with its 95% prediction interval, and only
  within the income range it is estimated on), or the regional median for
  fertility and infant mortality, reported as borrowed. Never substitute
  another country's value without saying so.
- Convert every gradient to OG-Core's units: divide by 100 × (1 − p), with p
  OG-Core's own rate at that age and period.
- Pass fertility and mortality as vectors by age, following the guide's
  tables.
- Use IMR, not U5MR, for `infmort_gradient`, and CMR at ages 1–4 of
  `mort_gradient`.
- `imm_pctiles` is not provided; say so.
- State the source and year of every value, and what is borrowed.
- High-income countries are outside the library's scope. DHS sibling
  histories were tested for adult mortality and rejected; do not propose
  them.

# Working on this repo

Demographic-Gradients hosts wealth gradients in demographic rates for OG-Core
country calibrations. Data lives in `data/`, everything is regenerable by
scripts, and the documentation is generated — respect that architecture.

## Non-negotiables

- **Never hand-edit the generated docs** — `ANALYSIS.md`,
  `docs/calibration-guide.md`, the README's marked coverage table, the marked line-fit table in `docs/methods/survey-gradients.md`, `docs/methods/general-gradient.md`,
  `docs/methods/ogcore-units.md`, `docs/methods/fertility-by-age.md`,
  `docs/tables/adult_mortality.md`, and
  everything under `docs/countries/`
  are written by `scripts/build_analysis.py` from the CSVs (each carries a
  GENERATED banner). Change the generator or the data, then regenerate
  (`uv run scripts/build_analysis.py`, or `uv run scripts/refresh.py` for the
  full DHS refresh). The rest of `README.md`, `docs/methodology.md`, `docs/glossary.md`,
  `docs/files.md`, `docs/sources.md`, `docs/methods/adult-mortality.md`
  and `docs/methods/survey-gradients.md` are hand-written — edit those directly,
  but keep any numbers in them qualitative so they cannot drift.
- **Writing standard: statistical-publication style.** Documentation follows
  the conventions of DHS reports and World Bank indicator notes: neutral,
  declarative prose; results stated with their numbers and comparison group;
  no persuasive or rhetorical phrasing; hedged only as far as the evidence
  requires ("consistent with", "may reflect"). Use the standard terms: *wealth
  gradient* (slope of the log rate on wealth rank; the `slope` column), *low/high
  ratio* (lowest-quintile rate over highest-quintile rate; the `ratio` column),
  *wealth quintile* (lowest … highest). The README stays a short entry point;
  detail belongs on the method pages; new terms go in `docs/glossary.md`.
  Hand-written pages keep counts qualitative so they cannot drift.
- **Figure standard** (`scripts/make_figures.py`, styling in
  `scripts/figures.mplstyle`): standard matplotlib; a descriptive title naming
  the indicator, population and survey; a *Note:* line explaining what is drawn
  and a *Source:* line; plain axis labels with units; low/high ratios on a log
  scale for comparisons, the gradient itself for the library's own estimates;
  point labels placed with `adjustText`, not hand-tuned offsets. Render every
  figure and check every number and label against the data before committing.

## Method rulings (validated — don't relitigate without new evidence)

- The gradient = slope of ln(rate) on wealth rank 0–1. DHS quintiles: OLS at
  0.1…0.9. Census groups: each at its REALIZED population midpoint, WLS
  weighted by group population share (`asset_index.gradient`). Many households
  share an index value, so cuts tie; a census supports however many groups it
  supports — record it in the `groups` column. Ruled 2026-11-11.
- **Census wealth index = first principal component** (Filmer & Pritchett
  2001; DHS; Lovaton Dávila et al. 2022 for IPUMS-I) of household 0/1
  indicators, one per asset and one per TOILET category, household-weighted
  correlation matrix, oriented to rise with assets owned (`scripts/asset_index.py`,
  shared by all four census scripts). Groups are cut at the boundary between
  distinct scores nearest each person-weighted quintile of all persons in the
  asset universe (ruled 2026-11-16, replacing the score at the quintile,
  which could land at the far edge of a tie block); `share1`–`share5` publish
  each group's share; groups under 10% are merged
  into the smaller neighbour; `MIN_GROUPS = 3`. Ruled 2026-11-11, replacing an
  additive count that had mis-coded INTERNET/WASHER (scored on "no"), TV (only
  code 20) and latrines (scored as flush). The IPUMS yes-codes are documented
  in `asset_index.py` from the .cbk files — check any new variable there.
- ogcore (>= 0.18.0) consumes **gradient / (100 × (1 − p))**: ÷100 because its
  gradients are per centered percentile point, ÷(1 − p) because it reads a
  log-odds slope where the library publishes a log-rate one (p = ogcore's own
  rate at that age, on its scale). Verified by `scripts/check_ogcore_units.py`,
  which runs every DHS quintile set (IMR, U5MR, ASFR) through ogcore's pinned
  `_mean_preserving_logit_rates`; rerun it when ogcore's demographics change.
  The published `slope` stays the log-rate gradient — it is the measured,
  scale-free quantity; the conversion needs the model's p. The grouping is
  ogcore's job — any lambdas vector works with the same gradient.
- Fertility enters by age as **TFR gradient + pooled age offset**
  (`fertility_age_offsets.csv`, built from DHS age-specific rates by wealth
  quintile in `build_gradient_library.py`). Validated: 5 × Σ ASFR reproduces
  DHS's TFR per quintile within rounding; a backtest over consecutive surveys
  shows a country's own age shape predicts about as well overall (better
  under 30, worse from 35), while the pooled offsets have no gaps at 45–49.
  Ruled 2026-11-05 — offsets, not per-country age gradients.
- **Mortality at ages 1–4 uses the country's own CMR gradient** (DHS
  `CM_ECMR_C_CMR`, 4q1), falling back to U5MR + the pooled offset
  (`child_mortality_offset.csv`, −0.53). Ruled 2026-11-16.
  - (1 − IMR)(1 − CMR) reproduces DHS's U5MR per quintile within rounding.
  - CMR is steeper than U5MR in 85% of 74 countries.
  - Backtest over 203 consecutive-survey pairs: own previous CMR 0.43,
    U5MR + offset 0.38, U5MR alone 0.55. The pooled route predicts the next
    survey slightly better. Own CMR was ruled as the measured value for the
    survey in use, as for IMR.
- **MICS is a second survey source** for TFR, IMR and U5MR (ruled 2026-11-13):
  every MICS survey goes into `gradient_library.csv` with `source`; the latest
  file takes the newest survey of either kind (DHS on a same-year tie). MICS
  mortality only from direct (FBH) estimates: UNICEF's CME classification,
  matched by overlapping fieldwork years (the World Bank and UNICEF label some
  surveys differently: Congo 2015-16 vs 2014-15), else the report
  (`mics_methods_reports.csv`); undocumented methods excluded. Every exclusion
  was checked against the MICS reports (2026-11-13; copies at
  mics.ipums.org/mics/resources/enum_materials_pdf/report_<iso2><year>a_<lang>.pdf,
  since mics.unicef.org and its S3 bucket refuse scripted downloads). Findings
  and rulings: the World Bank file holds the adolescent birth rate column under
  TFR for CAR, Chad, Guinea-Bissau, Honduras, São Tomé, Algeria 2019 and
  Tunisia 2018 — true TFR by quintile transcribed from the reports
  (`mics_tfr_from_reports.csv`, with table and page; Honduras's report is only
  on mics.unicef.org, read in a browser after its human check);
  sets with a quintile rate of 3 or less per 1,000 (Paraguay 2016, Tonga 2019,
  Belize 2016) are correct but excluded as too imprecise; the WDI-based TFR
  check flags but does not exclude (North Macedonia 2019 is correct; its survey
  TFR is 1.9); surveys high income in the survey year are out of scope
  (Barbados). Fertility age offsets stay DHS-only. MICS inputs are pinned;
  refresh only with `scripts/fetch_mics.py`, deliberately.
- Adult mortality ranks households by an **asset index**, never post-death
  household income (reverse causation; São Paulo validation: assets monotonic,
  income jagged). Asset components vary by census and are recorded per sample
  in `scripts/build_adult_mortality.py`.
- Deaths are weighted by the supplementary file's own weight where provided,
  else by the linked household's HHWT. Census under-reporting cancels in the
  gradient if wealth-uniform; levels are never published claims.
- Where a sample links only some deaths (za2011a: ~10%), record
  `linked_share` and run the linked-vs-unlinked composition check (province,
  urban, sex, age) before trusting the gradient.
- `MIN_BAND_DEATHS = 900` gates publication of an age-band gradient and of
  45q15 (records at 15–59). Ruled 2026-11-11.
- **Every adult-mortality row carries `se`** (ruled 2026-11-16, review A5).
  - Surveys: cluster bootstrap (PSUs within strata, 200 replicates, seed 1;
    `bootstrap_se` in the survey script).
  - Censuses: Poisson approximation from unweighted death records per wealth
    group (`asset_index.gradient_se`; delta method for 45q15).
  - It measures sampling only, not index or recording error. 45q15 SEs run
    0.015 (Colombia) to 0.11 (Cambodia, Benin), all far below the rule's
    residual SE (0.32), so equal weighting in the rule stays.
- **The 45q15 gradient is fitted on the death-rate scale**:
  slope of ln(−ln(1 − 45q15)) on wealth rank (`asset_index.q45_gradient`,
  used by all four adult-mortality scripts), ruled 2026-11-16.
  - Why: 45q15 is a probability near its ceiling where adult mortality is
    high, so ln(45q15) compressed the gradient (South Africa 2007 −1.23 on
    ln 45q15, −1.77 on this scale, band slopes −1.63/−2.00/−1.58; Lesotho
    −0.36 vs −0.73). OG-Core applies the gradient to annual death rates,
    where this scale is the right one, and uniform under-recording cancels
    on it.
  - The q1..q5 columns still report 45q15 per 1,000; `ratio` is still q1/q5
    of 45q15.
  - Age-band (mx) gradients were always on the rate scale and did not change.
  - The income rule and age offsets were refitted. In-sample, the offsets
    reproduced band gradients better (median error 0.089, was 0.116, on the
    20 observations of the time; leaving each country out, the current figure
    is 0.14). The rule fits less tightly (r −0.77, residual SE 0.31), mainly
    because South Africa 2007 moved.
- **The MORTNUM check gates publication of any new sample.** Compare the
  supplementary per-death file against the same households' own reported
  death counts (MORTNUM in the extract) *within each wealth group*. Even
  record loss cancels out of a gradient; wealth-skewed loss biases it. Flat to
  within a percent or two = publish. This caught br2010a (IPUMS ships 48% of
  the deaths the census reports, loss concentrated in wealthy households),
  np2001a (0.77/0.79/0.90/1.13 - biases flat) and sv2007a (0.96 down to 0.58
  - biases steep). Mark rejects `publish=False` with the evidence in the
  config; never delete the config entry. `estimate` prints the comparison
  (relative to the mean) for every sample with MORTNUM. On the PCA index it
  also rejected za2011a (0.066/0.073/0.064/0.059/0.055 linked/reported -
  biases steep by ~0.3) and mz2007a (0.89/1.09/0.97/1.05 - biases flat by
  ~0.15). za2007a has MORTNUM and passes; za2001a and ci1998a have none.
- Gradient steepness tracks national income, not region: the general
  gradient is linear in ln(GDP per capita, PPP, constant 2021 intl $), over
  every census and survey estimate (current coefficients and fit statistics:
  `data/general_gradient.csv` and the generated general-gradient page; do not
  copy them here). Survey rows enter the rule on the same footing as
  censuses (ruled 2026-11-12). Changes to the set of observations are logged
  in CHANGELOG.md.
  Income measure ruled 2026-11-13: GDP per capita PPP constant
  (NY.GDP.PCAP.PP.KD), the standard for cross-country living-standard and
  health-income comparisons; it replaced Atlas GNI in current US$, which mixed
  price years (applied to recent GNI it made predictions ~0.1 too steep).
  Same fit quality (LOCO MAE 0.175 vs 0.176, on the 17 observations of the
  time). Constant-price GNI (US$ or PPP) was rejected: WDI lacked it for 7 of
  those 17. Inference is
  classical OLS with n - 2 df (ruled 2026-11-12): slope SE 0.091,
  clustered-by-country SE 0.098; publish the 95% prediction interval (~±0.7)
  with any value read off the rule. Income is pinned in
  `data/income_census_years.csv` (WDI revises history; each ICP round revises
  PPPs), with Atlas GNI kept for reference; refresh only with
  `--refresh-income`, deliberately. On the earlier index, excluding South Africa, the
  gradient-vs-HIV-prevalence correlation was +0.00; not re-run since.
  Borrowing tables should key on income level. Within-country change is
  NOT established: South Africa steepened 2001->2007 (-1.16 -> -1.75), India stayed flat
  (-0.83/-0.81/-0.79, 1999-2020, GDP pc PPP $2,954->$7,187). Present "fixed" and
  "follows the income rule" as a range for long OG transitions.
- **DHS household-deaths modules** (`scripts/build_adult_mortality_survey.py`,
  ruled 2026-11-12) are the census design in a survey, not sibling
  histories: deaths of usual members in the 24 months before interview over
  2 × the de jure population, DHS wealth quintiles (OLS at 0.1…0.9), hv005
  weights, the same 900-record minimum; rows go into
  `adult_mortality_gradients.csv` with `source` starting "The DHS Program"
  and `ranking == "dhs_wealth_index"`. Year = the DHS API's survey year
  (NFHS-5 is 2020). The script prints the survey analogues of the census
  gates: records vs the household's own death count, year-2/year-1 recall by
  quintile, unknown date/age by quintile, heaping and a boundary-split
  sensitivity, national 45q15 against WDI, cluster-bootstrap SE. Of the DHS,
  only India qualifies; every Asian DHS since 1997 and every DHS tagged for
  causes of death was scanned (2026-11-12).
- **Bangladesh BMMS 2016** (ruled 2026-11-16: publish under the survey rules)
  goes through the same script (loader "bmms"), with the survey's own wealth
  quintiles and `qhweightoverall`; rows have `ranking ==
  "survey_wealth_index"`. Survey rows are told from census rows by `ranking`
  (anything but "asset_index"), not by source text. Its member file
  (BMMS16_HM) is truncated at 1,048,575 rows in both Dataverse formats —
  persons come from the household file's roster, which matches `dejure`
  exactly. 45q15 gradient −0.07 (bootstrap SE 0.07); own census-style index
  −0.12; rural and urban both near zero; the gradient flattens with time since
  death (−0.16/+0.02/+0.14 by year back), within sampling error.
- The gradient fades with age in every census and survey measured at 15-29
  and an older band (14/14, mean drift +0.94 from 15-29 to the oldest band), and in 5
  censuses, all with GDP pc PPP <= $5,093 (Ethiopia, Uganda, Zambia, Sudan,
  Côte d'Ivoire), it becomes
  positive at older ages -
  measured mortality is higher in wealthier households at 45+. Real
  (low income compresses survival differences) and artefactual (frail elders
  move into better-off households before dying) explanations both fit; no
  within-census check separates them. Say so rather than smoothing it.

## Per-sample gotchas already paid for

- DHS recode gotchas: NFHS-1 (IAHR23) ships the age-at-death number blank for
  every record (the .FRQ file confirms) - unusable; Pakistan 2006-07
  (PKHR53) asked deaths in all 95k households but assets/hv270 only in the
  13.8k long-form ones, whose deaths are mostly women's - unusable. Older
  recodes store numeric codes in object columns and pre-hv270 surveys keep
  the wealth quintile in a separate WI file (whhid = hhid). NFHS-4's module is
  labelled "since January 2011" but its dates begin in 2012. Record visitor
  deaths separately where the module has them (NFHS-1, Pakistan) and keep
  usual members only.

- IPUMS extract variables differ by census — start a new sample's
  `asset_extra` from `WISH` and let the API's 400 errors name what to drop
  (za2001a has no MORTNUM, AUTOS, WASHER, INTERNET; za2007a no AUTOS/WASHER).
  `submit` retries on 400, dropping what the error names, and prints the final
  set to record in SAMPLES. br2010a has no harmonized TOILET (BATH
  stands in); np2001a lacks almost everything.
- **AUTOS code 7 means "has a car, count unspecified", not seven cars** —
  clip it to 1. Treating it as 3 inflated the asset index for every car-owning
  household and materially changed za2011a's gradient (-1.14 -> -0.80, on the
  earlier additive index; za2011a is no longer published).
  Read the .cbk code labels for any new asset variable before trusting it.
- Rank only households actually observed on the asset module. Collective
  dwellings are NIU everywhere, and et2007a asks assets *and* mortality of the
  long-form 20% subsample only (its weights already inflate to national
  totals — do not re-scale). NIU households otherwise sort into the bottom
  group as false paupers.
- Cut placement history, so it is not reintroduced:
  - A cut at the distribution's minimum creates a structurally empty first
    group and silently zeroes the sample (et2007a: 46% of persons hold no
    assets).
  - Dropping a cut at the maximum merged a real top group (until
    2026-11-13; Colombia 2018 fell to 2 groups).
  - Taking the score at the quintile could land at the far edge of a tie
    block (until 2026-11-16; Sierra Leone had 3 groups, now 5).
  - The current rule cuts between distinct scores, at the boundary nearest
    each quintile, so neither failure can occur. A census
  supports however many groups it supports (Ethiopia supports 3; Rwanda
  2002 only 2, so it is not published).
- Supplement serial schemes are not always the extract's: sv2007a appends a
  within-dwelling household suffix, so 0% links until floored to the
  extract's multiples of 1000. A 0% linkage rate means "diagnose the key",
  not "the data is empty".
- **A key that links 100% can still be wrong.** bf1996a's death file keys on
  the DWELLING while the extract keys on dwelling + household suffix, so
  `serial + 1` links every record — by assigning every death to household #1.
  With 34.8% of dwellings holding several households (62.2% of all
  households), most deaths would be charged to the wrong assets. Check the
  *meaning* of a key, not just its match rate. Rejected on that plus a
  2-group index and 29% undetermined ages.
- Death-file schemas vary in three more ways worth handling in config, not
  ad hoc: columns arrive uppercase in some samples (ci1998a); age can be a
  value plus a unit code (bf1996a `agedcode` 1=days 2=months 3=years,
  9/10 unknown); and an in-range value can mean "unknown" (ci1998a codes
  age 99, a 2,209-record spike against 7-141 at each of ages 88-98 — always
  look at the distribution before trusting a top code).
- Where a sample has no MORTNUM the completeness gate cannot be run at all
  (ci1998a). `seqd` is a partial substitute: within-household sequence gaps
  detect records lost inside households, but not whole households missing
  from the file, which is what br2010a's failure looked like. Record which
  check was actually possible.
- **A thin index can fail, not just flatten.** mw1998a's three items (radio,
  electricity, toilet) were published with a caveat until 2026-11-16. The
  same items applied to mw2008a turn its 45q15 gradient from −0.60 to +0.41,
  so they do not rank Malawian households at all. Elsewhere the same thin set
  moves gradients by −0.14 to +0.23. For any new census with few items,
  re-estimate a richer census of the same country (or region) on that item
  set before publishing.
- **Missing age is only harmless if it is wealth-uniform.** The MORTNUM check
  looks at record counts, not age completeness, so a sample can pass it and
  still have age-band gradients biased by skewed age reporting. ci1998a's
  unknown-age share runs 0.11/0.15/0.18/0.15/0.15 across wealth groups —
  flat, so it publishes.
- The IPUMS API has no variable-metadata endpoint — `/metadata/variables`
  404s. Probe availability by submitting a throwaway extract and reading the
  400. `/metadata/samples` does work.
- Supplementary death files have inconsistent schemas: za2011a carries
  `wtmort`, the older SA files carry no weight at all; sex codes are 1/2 but
  arrive as mixed dtypes — coerce numerics explicitly.
- `find_extract_for()` matches extracts to samples via the SAMPLE code
  (ISO-numeric country **zero-padded to 3 digits** + year + "01") — Brazil is
  "076", not "76". Extend `CCODE` when adding countries.
- Weights carry two implied decimals (`dcml=2` in the DDI) — divide by 100.
- macOS `unzip` fails on Latin-1 zip names; use Python zipfile with a
  cp437→latin-1 re-encode when handling NSO archives.

## Verification standard for any new country

1. Extract's weighted population reproduces the census total.
2. Linkage rate measured and recorded; composition check if < 1.
3. MORTNUM wealth-uniformity check passes (see the method rulings above).
4. Envelope check: weighted supplement deaths against the national death
   count (World Bank crude death rate x population). Wealth-uniform
   under-reporting is fine and cancels; record the capture rate as a caveat
   (bj2013a 35% publishes; note its ~16-month window). kh2008a (48%) passes
   every check and was published by ruling 2026-11-16, after being held
   through the new-source review (see CHANGELOG.md).
5. Gradient cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures regenerated and visually inspected; docs regenerated, not edited.
