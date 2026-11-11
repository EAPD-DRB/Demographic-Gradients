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
| `fert_gradient` | `data/gradient_library_latest.csv` + `data/fertility_age_offsets.csv` | `indicator == "TFR"`, plus the offset by age | 77 countries |
| `infmort_gradient` | `data/gradient_library_latest.csv` | `indicator == "IMR"` | 78 countries |
| `mort_gradient` | `data/adult_mortality_gradients.csv` | `measure == "45q15"`, `sex == "all"`, latest census (Brazil: mean of `male` and `female`) | 15 countries |
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

## Adult mortality for countries without a census estimate

`data/general_gradient.csv` provides a fallback for any country:

    gradient(45q15) = 1.291 − 0.244 × ln(GNI per capita, Atlas method, current US$)      ±0.16

It was selected by leave-one-country-out prediction error against two
alternatives: mean absolute error 0.136, compared with 0.303 for a single pooled
value and 0.260 for regional medians. The error is 0.11 for censuses above
$1,000 per capita and 0.16 below. The same file contains age offsets and a
pooled median for use when no GNI figure is available. The rule is estimated
on GNI in current dollars of the census years (1998–2013); applying it to a
recent GNI figure without adjusting for price change makes the predicted
gradient somewhat steeper.

Values at 2024 GNI per capita: Philippines −0.76 ($4,470), Indonesia −0.79
($4,920). Countries with their own census estimate (for example South Africa,
−0.80, and Ethiopia, +0.09) use that estimate, not the rule.

**There is no income-based fallback for fertility or infant mortality.** The
same comparison was run for them: an income rule improved on a single pooled
value by 0.4 percent for fertility, against 54 percent for adult mortality,
because these gradients vary little with national income. For a country with no
DHS survey, use the regional median and interquartile range from
[ANALYSIS.md](ANALYSIS.md#regional-medians) and report the value as borrowed.

## Known pitfalls

- **Use `IMR`, not `U5MR`, for `infmort_gradient`.** The under-five gradient is
  steeper: across 291 surveys reporting both, by a median 0.14, and by 0.67 in
  Nigeria 2018. Every survey in the library that reports U5MR by quintile also
  reports IMR; U5MR is published for comparison only.
- **Do not pool measurement bases.** `gradient_library*.csv` contains DHS survey
  rates; `adult_mortality_gradients.csv` census death records;
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
  child-mortality gradient falling from −1.76 (1991) to −0.84 (2010). The census
  measure resembles under-five mortality and probably overstates the infant
  gradient; the alternative is the 1996 DHS infant gradient (−1.37). State
  which is used and why.
- **`groups` is not always 5.** Census rows use as many wealth groups as the
  asset distribution supports (2 to 5), with each group placed at its realized
  population midpoint. The `q1..q5` columns stop at the last group, and the
  low/high ratio then compares the lowest and highest of those groups.
- **`linked_share` below 1 means rate levels are not meaningful.** South Africa
  2011 links about 9 percent of death records; its gradient is used, its
  levels are not.

## Sign and interpretation

A negative gradient means rates are higher in poorer households, which is the
usual case for every indicator here. A gradient of −0.79 implies a fitted rate
in the lowest quintile about e^(0.79 × 0.8) ≈ 1.9 times that in the highest.
The `ratio` column is the measured low/high ratio (q1/q5), which is noisier. A
positive adult-mortality gradient is not necessarily an error: several
low-income censuses record it, for reasons discussed in the general-gradient
documentation.

## Long-run projections

The adult-mortality gradient becomes more negative as national income rises
(r = −0.88 across censuses). A model projecting several decades ahead should
let the gradient steepen along its income path rather than hold it fixed; a
doubling of income per capita corresponds to about −0.17 in the gradient. The
pooled fertility and infant gradients change little across 35 years of
surveys, although a single country can change considerably, as Brazil shows.

## Questions the library cannot answer

State the gap rather than interpolating:

- **High-income countries are outside the library's scope.** Its sources are
  designed for low- and middle-income countries, and the income rule is
  estimated between about $200 and $10,000 GNI per capita. It must not be
  extrapolated to high-income countries; if asked, say the library does not
  cover them.
- There is no Asian census estimate of adult mortality. The Philippine and
  Indonesian values are extrapolations from a relationship estimated on African
  censuses and Brazil.
- DHS sibling histories were tested as a source for adult mortality and
  rejected: they reproduce national levels but give wealth gradients of the
  wrong sign, because poorer respondents under-report deaths. Do not propose
  them as an alternative.

## Citation

Cite The DHS Program for fertility and child mortality; IPUMS International
(Ruggles et al., doi:10.18128/D020.V7.7) plus the originating statistical office
for census-based estimates; IBGE directly for Brazil's adult-mortality rows,
which come from IBGE's own microdata rather than IPUMS. The `source` column is
accurate row by row — use it.

---

# Working on this repo

Demographic-Gradients hosts wealth gradients in demographic rates for OG-Core
country calibrations. Data lives in `data/`, everything is regenerable by
scripts, and the documentation is generated — respect that architecture.

## Non-negotiables

- **Never hand-edit the generated docs** — `ANALYSIS.md`, the README's marked
  coverage table, `docs/methods/general-gradient.md`,
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

- The gradient = OLS slope of ln(rate) on wealth rank 0–1, regressed on each
  group's REALIZED population midpoint (integer asset indices tie at quintile
  cuts; a census supports however many groups it supports — record it in the
  `groups` column).
- ogcore (>= 0.18.0) consumes **gradient / (100 × (1 − p))**: ÷100 because its
  gradients are per centered percentile point, ÷(1 − p) because it reads a
  log-odds slope where the library publishes a log-rate one (p = ogcore's own
  rate at that age, on its scale). Verified by `scripts/check_ogcore_units.py`,
  which runs every quintile set through ogcore's pinned
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
- `MIN_BAND_DEATHS = 900` gates publication of an age-band gradient.
- **The MORTNUM check gates publication of any new sample.** Compare the
  supplementary per-death file against the same households' own reported
  death counts (MORTNUM in the extract) *within each wealth group*. Even
  record loss cancels out of a gradient; wealth-skewed loss biases it. Flat to
  within a percent or two = publish. This caught br2010a (IPUMS ships 48% of
  the deaths the census reports, loss concentrated in wealthy households),
  np2001a (0.77/0.79/0.90/1.13 - biases flat) and sv2007a (0.96 down to 0.58
  - biases steep). Mark rejects `publish=False` with the evidence in the
  config; never delete the config entry.
- Gradient steepness tracks national income, not HIV or region:
  `gradient ~ 1.29 - 0.244*ln(GNI per capita)`, r = -0.88 over 17 censuses.
  Excluding South Africa the gradient-vs-HIV-prevalence correlation is +0.00.
  Borrowing tables should key on income level; a long OG transition should
  expect the gradient to steepen as the country's income rises.
- The gradient fades with age in every census measured at more than one
  age (13/13, mean drift +0.83 from 15-29 to the oldest band) and in the poorest countries it becomes positive at older ages -
  measured mortality is higher in wealthier households at 45+. Real
  (low income compresses survival differences) and artefactual (frail elders
  move into better-off households before dying) explanations both fit; no
  within-census check separates them. Say so rather than smoothing it.

## Per-sample gotchas already paid for

- IPUMS extract variables differ by census — submit with the full wish list
  and let the API's 400 errors name what to drop (za2001a has no MORTNUM,
  AUTOS, WASHER, INTERNET; za2007a no AUTOS/WASHER). `submit` now does this
  automatically: it retries on 400, dropping what the error names, and prints
  the final set to record in SAMPLES. br2010a has no harmonized TOILET (BATH
  stands in); np2001a lacks almost everything.
- **AUTOS code 7 means "has a car, count unspecified", not seven cars** —
  clip it to 1. Treating it as 3 inflated the asset index for every car-owning
  household and materially changed za2011a's published gradient (-1.14 -> -0.80).
  Read the .cbk code labels for any new asset variable before trusting it.
- Rank only households actually observed on the asset module. Collective
  dwellings are NIU everywhere, and et2007a asks assets *and* mortality of the
  long-form 20% subsample only (its weights already inflate to national
  totals — do not re-scale). NIU households otherwise sort into the bottom
  group as false paupers.
- Quantile cuts landing on the distribution's minimum create a structurally
  empty first group and silently zero the whole sample (et2007a: 46% of
  persons hold no assets). Drop cuts at the min/max; a census supports
  however many groups it supports (Ethiopia and Rwanda support 3).
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
   (bj2013a 35%, kh2008a 49% both publish; note bj2013a's ~16-month window).
5. Gradient cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures regenerated and visually inspected; docs regenerated, not edited.
