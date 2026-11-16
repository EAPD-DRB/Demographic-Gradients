# Using this library for an OG-Core calibration

Guidance for an AI agent (or a person) answering calibration questions with
this repository's data. The first part covers *using* the data; for working
*on* the repository (rebuilding it, adding countries) see
[Working on this repo](#working-on-this-repo) below.

For a specific country, start with its page in
[`docs/countries/`](docs/countries/): it gives the value for each OG-Core input,
the estimates behind them and their sources. Then apply the rules below. Terms
are defined in [`docs/glossary.md`](docs/glossary.md); the methods are
summarized in [`docs/methodology.md`](docs/methodology.md).

The library measures how fertility and mortality differ between poorer and
richer households. OG-Core (version 0.18 and later) can differentiate these
rates across lifetime-income groups; the library provides the measured
differentials, in place of the default assumption of no difference.

## The four inputs and their sources

`ogcore.demographics.get_pop_objs()` takes four arguments that differentiate
demographic rates by income group. The library supplies three:

| Argument | File | Selection | Coverage |
|---|---|---|---|
| `fert_gradient` | `data/gradient_library_latest.csv` + `data/fertility_age_offsets.csv` | `indicator == "TFR"`, plus the offset by age | 96 countries (DHS or MICS) |
| `infmort_gradient` | `data/gradient_library_latest.csv` | `indicator == "IMR"` | 88 countries (DHS or MICS) |
| `mort_gradient` | `data/adult_mortality_gradients.csv` | `measure == "45q15"`, `sex == "all"`, latest year | 15 countries (14 by census, India by DHS survey) |
| `imm_pctiles` | not provided | — | — |

`imm_pctiles` is not a gradient: it is the lifetime-income distribution of new
immigrants (shape num_per × S × J). The library does not provide it; say so
rather than substituting a gradient. `income_percentiles` is the model's own
`lambdas`, not library data.

## The two main rules

**1. Convert the gradient: divide by 100 × (1 − p).** The library's wealth
gradient is a log-rate slope per unit of wealth rank (0 to 1). OG-Core reads a
*log-odds* slope per *centered percentile point*. Pass
`gradient / (100 × (1 − p))`, where p is OG-Core's own mean rate at that age
and period on OG-Core's scale (fertility: births per *person* per year, the UN
rate per 1,000 women divided by 2,000; mortality: annual probability of death).
Omitting the 100 changes results by a factor of 100. Omitting (1 − p)
understates the slope by the factor (1 − p): at median rates, about 1 percent
for adult mortality (where `gradient / 100` is an acceptable approximation),
5 percent for infant mortality and 1–11 percent for fertility depending on age.
Because p varies by age, a converted fertility gradient is a vector by age.
The conversion is verified on the DHS quintile sets for infant mortality,
under-five mortality and age-specific fertility; see
[docs/methods/ogcore-units.md](docs/methods/ogcore-units.md).

**Fertility by age.** Pass `fert_gradient` as a vector by age: the country's
TFR gradient plus the offset for each age from `data/fertility_age_offsets.csv`
(ages below 15 use the 15–19 offset, ages 50 and above the 45–49 offset), then
convert as above. A single TFR gradient at every age reproduces the
differential in completed fertility but not in the timing of births: the
gradient at ages 15–19 is about twice the TFR gradient. Use the pooled offsets,
not a country's own age gradients (`fertility_age_tilts.csv` is supporting
data): over consecutive surveys, a country's own age pattern predicts the next
survey about as well overall (better below 30, worse from 35), and it cannot be
estimated at older ages in many surveys. Details:
[docs/methods/fertility-by-age.md](docs/methods/fertility-by-age.md).

**2. Own estimate first, general gradient as fallback.** If the country has a
row in the relevant file, use it. If not, use the general gradient for adult
mortality (below) or the regional median for fertility and infant mortality.
Never substitute another country's value without saying so; state the source
and the survey or census year.

## Adult mortality for countries without their own estimate

`data/general_gradient.csv` provides a fallback for any country:

    gradient(45q15) = 2.718 − 0.391 × ln(GDP per capita, PPP, constant 2021 international $)

Income is the World Bank's `NY.GDP.PCAP.PP.KD`: it is comparable across
countries and years, so the rule is applied to the same series for any year
with no conversion. Do not plug in GNI in current US dollars (the measure used
before 2026-11-13).

It is fitted on 18 observations: 15 censuses and India's three DHS surveys with
a household-deaths module (NFHS-2, -4, -5), with equal weight. The slope has a
standard error of 0.052 (95% CI −0.501 to −0.282), but a single country can lie
well off the line: the 95% prediction interval for a country without its own
estimate is about ±0.43 (residual standard error 0.19).
Report the prediction interval with any value taken from the rule; the file
holds the terms needed to compute it at any income (formula in
[docs/methods/general-gradient.md](docs/methods/general-gradient.md)).

It was selected by leave-one-country-out prediction error against two
alternatives: mean absolute error 0.165, compared with 0.330 for a single pooled
value and 0.295 for regional medians, scored on the same 18 observations. The
error is 0.20 below $3,000 per capita (PPP) and 0.14 above. The largest misses
are Malawi 2008 (−0.47 measured against −0.03 predicted), Uganda 2002 (+0.15
against −0.21), India 1999 (−0.73 against −0.39) and Zambia 2010 (−0.14
against −0.47). The same file contains age offsets and a pooled median for use
when no income figure is available.

Values at 2024 GDP per capita (PPP): Philippines −0.90 (95% prediction interval
−1.33 to −0.47; $10,378), Indonesia −1.03 (−1.47 to −0.59; $14,471). Countries with
their own estimate (for example South Africa 2007, −1.23; Ethiopia 2007, +0.01;
India 2020, −0.72; Colombia 2018, −1.18) use that estimate, not the rule.

**There is no income-based fallback for fertility or infant mortality.** The
same comparison was run for them: an income rule improved on a single pooled
value by 0.4 percent for fertility, against 50 percent for adult mortality,
because these gradients vary little with national income. For a country with no
DHS or MICS survey, use the regional median and interquartile range from
[ANALYSIS.md](ANALYSIS.md#regional-medians) and report the value as borrowed.

## Known pitfalls

- **Use `IMR`, not `U5MR`, for `infmort_gradient`.** The under-five gradient is
  steeper: across 339 surveys reporting both, by a median 0.14, and by 0.67 in
  Nigeria 2018. Every survey in the library that reports U5MR by quintile also
  reports IMR; U5MR is published for comparison only.
- **DHS and MICS rows share one basis.** `gradient_library*.csv` holds both,
  marked in `source`. MICS rows are UNICEF survey rates taken from the World
  Bank's compilation (pinned in `mics_quintiles_raw.csv`), mortality only where
  UNICEF records a direct (full birth history) estimate; `mics_surveys.csv`
  says what each survey contributes and why anything is excluded. Name the
  source with the year ("MICS 2019"). A country's history can switch source
  between surveys; part of the change may be the switch.
- **Do not pool measurement bases.** `gradient_library*.csv` contains DHS and
  MICS survey rates; `adult_mortality_gradients.csv` household death records (censuses, and
  for India DHS surveys, whose rows have `ranking == "dhs_wealth_index"`);
  `census_child_mortality.csv` a census cumulative proportion. Their gradients
  agree where they have been compared, but their levels (`q1..q5`) measure
  different quantities.
- **The older-age offsets in `general_gradient.csv` are the least reliable
  values in the library.** The 45–59 and 60–74 offsets are positive because, in
  several low-income censuses, recorded mortality at older ages rises with
  wealth; this is at least partly a reporting effect. Where working-age
  mortality is what matters, rely on the 15–29 and 30–44 offsets and state the
  caveat.
- **Brazil's DHS survey is from 1996.** Census estimates show its
  child-mortality gradient falling from −1.69 (1991) to −0.96 (2010). The census
  measure resembles under-five mortality and probably overstates the infant
  gradient; the alternative is the 1996 DHS infant gradient (−1.37). State
  which is used and why.
- **`groups` is not always 5.** Census rows use as many wealth groups as the
  asset distribution supports (3 to 5; fewer than 3 is not published), with
  each group placed at its realized population midpoint. The `q1..q5` columns stop at the last group, and the
  low/high ratio then compares the lowest and highest of those groups.
- **`linked_share` is the share of death records matched to a household.**
  Every published row is above 0.99 (survey rows are 1 by construction). A sample with low linkage is publishable
  only if linkage does not vary with wealth; South Africa 2011 (9 percent
  linked, linkage lower in richer households) failed that test and is not
  published.

## Sign and interpretation

A negative gradient means rates are higher in poorer households, which is the
usual case for every indicator here. A gradient of −0.79 implies a fitted rate
in the lowest quintile about e^(0.79 × 0.8) ≈ 1.9 times that in the highest.
The `ratio` column is the measured low/high ratio (q1/q5), which is noisier. A
positive adult-mortality gradient is not necessarily an error: several
low-income censuses record it, for reasons discussed in the general-gradient
documentation.

## Long-run projections

Across countries the adult-mortality gradient is more negative at higher
national income (r = −0.88); a doubling of income per capita corresponds to
about −0.27 in the gradient. Within countries the evidence is limited and
mixed: Malawi's gradient steepened between its 1998 and 2008 censuses as income
rose, but India's was −0.73, −0.74 and −0.72 in 1999, 2015 and 2020 while GDP
per capita (PPP) rose from about $3,000 to $7,200. A model projecting several decades ahead
can hold the gradient fixed or let it follow the income relationship; report
which, and treat the two as a range. The
pooled fertility and infant gradients change little across 35 years of
surveys, although a single country can change considerably, as Brazil shows.

## Questions the library cannot answer

State the gap rather than interpolating:

- **High-income countries are outside the library's scope.** Its sources are
  designed for low- and middle-income countries, and the income rule is
  estimated between about $1,100 and $18,000 GDP per capita (PPP, constant
  2021 international $). It must not be
  extrapolated to high-income countries; if asked, say the library does not
  cover them.
- The only Asian estimates of adult mortality are India's (DHS surveys). There
  is none for East or Southeast Asia: the Philippine and Indonesian DHS surveys
  have no module on deaths at all ages, and their values come from a
  relationship estimated mostly on African censuses.
- DHS sibling histories were tested as a source for adult mortality and
  rejected: they reproduce national levels but give wealth gradients of the
  wrong sign, because poorer respondents under-report deaths. Do not propose
  them as an alternative.

## Citation

Cite The DHS Program for fertility and child mortality, and UNICEF (MICS) plus
the originating statistical office for rows with `source == "MICS"`; IPUMS International
(Ruggles et al., doi:10.18128/D020.V7.7) plus the originating statistical office
for census-based estimates; IBGE directly for Brazil's adult-mortality rows,
which come from IBGE's own microdata rather than IPUMS; DANE directly for
Colombia's (2018 census microdata); The DHS Program and IIPS
for India's adult-mortality rows (NFHS). The `source` column is
accurate row by row — use it.

---

# Working on this repo

Demographic-Gradients hosts wealth gradients in demographic rates for OG-Core
country calibrations. Data lives in `data/`, everything is regenerable by
scripts, and the documentation is generated — respect that architecture.

## Non-negotiables

- **Never hand-edit the generated docs** — `ANALYSIS.md`, the README's marked
  coverage table, the marked line-fit table in `docs/methods/dhs-gradients.md`, `docs/methods/general-gradient.md`,
  `docs/methods/ogcore-units.md`, `docs/methods/fertility-by-age.md`,
  `docs/tables/adult_mortality.md`, and
  everything under `docs/countries/`
  are written by `scripts/build_analysis.py` from the CSVs (each carries a
  GENERATED banner). Change the generator or the data, then regenerate
  (`uv run scripts/build_analysis.py`, or `uv run scripts/refresh.py` for the
  full DHS refresh). The rest of `README.md`, `docs/methodology.md`, `docs/glossary.md`,
  `docs/data-files.md`, `docs/sources.md`, `docs/methods/adult-mortality.md`
  and `docs/methods/dhs-gradients.md` are hand-written — edit those directly,
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
  shared by all four census scripts). Groups are cut at the person-weighted
  quintiles of all persons in the asset universe; groups under 10% are merged
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
- Gradient steepness tracks national income, not region:
  `gradient ~ 2.72 - 0.391*ln(GDP per capita, PPP, constant 2021 intl $)`,
  r = -0.88 over 18 observations (15 censuses + India NFHS-2/-4/-5; survey
  rows enter the rule on the same footing as censuses, ruled 2026-11-12;
  Colombia 2018 added 2026-11-16).
  Income measure ruled 2026-11-13: GDP per capita PPP constant
  (NY.GDP.PCAP.PP.KD), the standard for cross-country living-standard and
  health-income comparisons; it replaced Atlas GNI in current US$, which mixed
  price years (applied to recent GNI it made predictions ~0.1 too steep).
  Same fit quality (LOCO MAE 0.175 vs 0.176, on the 17 observations of the
  time). Constant-price GNI (US$ or PPP) was rejected: WDI lacked it for 7 of
  those 17. Inference is
  classical OLS with n - 2 df (ruled 2026-11-12): slope SE 0.052,
  clustered-by-country SE 0.051; publish the 95% prediction interval (~±0.43)
  with any value read off the rule. Income is pinned in
  `data/income_census_years.csv` (WDI revises history; each ICP round revises
  PPPs), with Atlas GNI kept for reference; refresh only with
  `--refresh-income`, deliberately. On the earlier index, excluding South Africa, the
  gradient-vs-HIV-prevalence correlation was +0.00; not re-run since.
  Borrowing tables should key on income level. Within-country change is
  NOT established: Malawi steepened 1998->2008, India stayed flat
  (-0.73/-0.74/-0.72, 1999-2020, GDP pc PPP $2,954->$7,187). Present "fixed" and
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
  sensitivity, national 45q15 against WDI, cluster-bootstrap SE. Only India
  qualifies so far; every Asian DHS since 1997 and every DHS tagged for
  causes of death was scanned (ROADMAP H1).
- The gradient fades with age in every census and survey measured at 15-29
  and an older band (15/15, mean drift +0.88 from 15-29 to the oldest band), and in 4
  censuses, all with GDP pc PPP <= $4,446 (Ethiopia, Uganda, Zambia, Sudan), it becomes
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
- Quantile cuts landing on the distribution's minimum create a structurally
  empty first group and silently zero the whole sample (et2007a: 46% of
  persons hold no assets). Drop a cut at the minimum; KEEP a cut at the
  maximum — households equal to a cut go to the group above, so it isolates
  a real top group (dropping it, as the code did until 2026-11-13, merged
  Colombia 2018 to 2 groups and changed Malawi 1998's grouping). A census
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
   every check but is held by ruling (2026-11-12) until the new-source review
   (ROADMAP H) is finished.
5. Gradient cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures regenerated and visually inspected; docs regenerated, not edited.
