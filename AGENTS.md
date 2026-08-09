# Using this library for an OG-Core calibration

Guidance for an LLM agent (or a person) answering calibration questions with
this repo's data. The first part is about *consuming* the data. For working
*on* the repo — regenerating it, adding countries — see
[Working on this repo](#working-on-this-repo) below.

Answering for one specific country? Its provenance page in
[`docs/countries/`](docs/countries/) assembles every estimate the library
holds for it, the source of each number, and the recommended calibration
route — start there, then apply the rules below.

The library answers one question: **how much does a demographic rate differ
between rich and poor households in a given country?** OG-Core (>= 0.18.0) can
vary fertility and mortality across lifetime-income groups, and these are the
measured gradients that let a calibration set that up instead of assuming no
difference at all.

## The four inputs, and which file each comes from

`ogcore.demographics.get_pop_objs()` takes four demographic distribution
arguments. Three are gradients this library supplies:

| Argument | File | Filter | Coverage |
|---|---|---|---|
| `fert_gradient` | `data/gradient_library_latest.csv` | `indicator == "TFR"` | 77 countries |
| `infmort_gradient` | `data/gradient_library_latest.csv` | `indicator == "IMR"` | 78 countries |
| `mort_gradient` | `data/adult_mortality_gradients.csv` | `measure == "45q15"` | 14 countries |
| `imm_pctiles` | **not in this library** | — | — |

`imm_pctiles` is not a gradient — it is the lifetime-income distribution of new
immigrants (shape num_per × S × J). This repo has nothing for it; say so rather
than substituting a gradient.

`income_percentiles` is not data either: it is the model's own `lambdas`.

## The two rules that matter most

**1. Divide the tilt by 100.** The library's tilt is per unit of wealth rank
(0 to 1). ogcore's gradients are per *centered percentile point*. A tilt of
−0.79 is passed as `-0.0079`. Getting this wrong changes results by 100×. This
is verified against ogcore source, not inferred.

**2. Own measurement first, general gradient as fallback.** If the country has
a row in the relevant file, use it. If it does not, use the general gradient
(adult mortality only — see below). Never silently substitute a different
country's value; state which route was taken and the survey or census year.

## Adult mortality: when a country has no row

`data/general_gradient.csv` holds a fallback usable for **any** country:

    tilt(45q15) = 1.291 − 0.243 × ln(GNI per capita, current US$)      ±0.16

It was chosen by leave-one-out competition against the alternatives — mean
absolute error 0.142, against 0.307 for one tilt applied to every country and
0.221 for regional medians — so it is the documented default, not a guess. It is
most accurate above $1,000 per head (error 0.11) and least accurate below
(0.17). The same file carries by-age offsets and a pooled median for use when no
GNI figure is available.

Worked values at 2024 income: Philippines −0.75, Indonesia −0.78, Ethiopia
−0.41. South Africa should use its own census value (−0.80), not the rule's
−0.83.

**There is no equivalent fallback for fertility or infant mortality, and that is
deliberate.** The same competition was run for them: income beat a single global
number by 0.4% for fertility, against 54% for adult mortality. Those gradients
are near-universal and similar in strength everywhere, so there is nothing for
income to predict. For a country with no DHS survey, use the regional median and
IQR from `ANALYSIS.md` and label it as borrowed.

## Traps that have already caused errors

- **Do not use `U5MR` for `infmort_gradient`.** The library used to ship under-5
  mortality as an infant proxy. It is steeper: across 289 surveys carrying both,
  the under-5 tilt exceeds the infant tilt by a median 0.14, and by 0.67 in
  Nigeria 2018. `IMR` is now measured directly — use it. `U5MR` remains only as
  a fallback for the few surveys with no infant quintiles.
- **Do not pool measurement bases.** `gradient_library*.csv` is DHS survey
  rates. `adult_mortality_gradients.csv` is census death modules.
  `census_child_mortality.csv` is a census cumulative proportion. They agree on
  *tilt* where tested but their levels are not comparable, and their `q1..q5`
  columns are different quantities.
- **The older-age offsets in `general_gradient.csv` are the least trustworthy
  numbers in this repo.** The 45–59 and 60–74 offsets are positive because
  measured mortality rises with wealth at older ages in the poorest countries,
  which is at least partly a reporting artefact. Prefer the 15–29 and 30–44
  offsets when working-age mortality is what matters, and note the caveat.
- **Brazil's DHS row is from 1996 and its child-mortality gradient has since
  halved.** Census estimates put it near −0.85 by 2010 against the DHS row's
  −1.46. Do not use the 1996 figure for a present-day Brazilian calibration
  without saying it is thirty years old; prefer `census_child_mortality.csv`.
- **`groups` is not always 5.** Census-based rows use as many wealth groups as
  the asset distribution supports (3 to 5), with the tilt fitted on each group's
  realized population midpoint. The tilt is still comparable; the `q1..q5`
  columns simply stop early.
- **`linked_share` below 1 means levels are meaningless.** South Africa 2011
  links about 10% of death records. Its tilt is usable; its rate levels are not.

## Sign convention and interpretation

Negative means the poor have higher rates — the usual case for every margin
here. A tilt of −0.79 puts the poorest decile's rate at roughly
e^(0.79 × 0.8) ≈ 1.9× the richest decile's. A positive adult-mortality tilt is
not necessarily an error: several of the poorest countries genuinely measure
that way, for reasons the analysis discusses.

## Long-run runs

Adult-mortality gradient steepness tracks national income (r = −0.88). A model
running decades forward should let the gradient steepen as its own income path
rises rather than holding today's value fixed. Doubling income per head
corresponds to about −0.17 on the tilt. Fertility and infant gradients, by
contrast, are stable across 35 years of surveys *in the pooled median* — though
not necessarily within a fast-developing country, as Brazil shows.

## What to say when asked something this repo cannot answer

Be direct about the gaps rather than interpolating:

- **This library covers developing countries by design.** Every source it draws
  on — DHS surveys and censuses with mortality or fertility modules — is a
  low- or middle-income instrument, and the OG-Core country applications it
  serves are developing-country models. High-income countries are out of scope
  rather than missing, and the income rule must not be extrapolated to them: it
  is fitted between roughly $200 and $10,000 GNI per head, and a prediction at
  $70,000 would be an invention. If asked for a high-income gradient, say the
  library does not cover it.
- There is no Asian observation in the adult-mortality set; the Philippine and
  Indonesian values are extrapolations from an African plus South Africa plus
  Brazil relationship.
- DHS sibling histories were tested as a source for adult mortality and
  rejected: they reproduce national levels exactly but produce wealth gradients
  of the wrong sign, because poorer respondents under-report deaths. Do not
  propose them as a workaround.

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
  headline table, `docs/methods/general-gradient.md`,
  `docs/tables/adult_mortality.md`, and everything under `docs/countries/`
  are written by `scripts/build_analysis.py` from the CSVs (each carries a
  GENERATED banner). Change the generator or the data, then regenerate
  (`uv run scripts/build_analysis.py`, or `uv run scripts/refresh.py` for the
  full DHS refresh). `docs/methods/adult-mortality.md` and
  `docs/methods/dhs-gradients.md` are hand-written method prose — edit those
  directly, but keep any numbers in them qualitative so they cannot drift.
- **No microdata in this repo, ever.** IPUMS extracts and supplementary death
  files stay local (`~/ipums-extracts`, `~/Projects/data`); the IPUMS license
  permits publishing only aggregated estimates — which is what `data/` holds.
- **Secrets live in `.secrets/` (gitignored).** The IPUMS API key is
  `.secrets/ipums_api_key`. Never echo it, never commit it, never pass it
  through chat or commit messages.
- **Replicability rule:** primary hosted data must rebuild from free sources.
  Registration-gated inputs (IPUMS) are acceptable at build time only because
  the hosted outputs are open — the BESFR precedent. Never depend on paid
  sources.
- **Citations are obligations, not decoration:** DHS Program (fertility/child
  mortality); IPUMS International (Ruggles et al., doi:10.18128/D020.V7.7)
  plus the originating statistical office (Statistics South Africa, IBGE, ...)
  for adult mortality. Keep the `source` column accurate per row.

## Method rulings (validated — don't relitigate without new evidence)

- The tilt = OLS slope of ln(rate) on wealth rank 0–1, regressed on each
  group's REALIZED population midpoint (integer asset indices tie at quintile
  cuts; a census supports however many groups it supports — record it in the
  `groups` column).
- ogcore (>= 0.18.0) consumes the tilt **divided by 100** (its gradients are
  per centered percentile point; verified against ogcore source). The
  grouping is ogcore's job — any lambdas vector works with the same tilt.
- Adult mortality ranks households by an **asset index**, never post-death
  household income (reverse causation; São Paulo validation: assets monotonic,
  income jagged). Asset components vary by census and are recorded per sample
  in `scripts/build_adult_mortality.py`.
- Deaths are weighted by the supplementary file's own weight where provided,
  else by the linked household's HHWT. Census under-reporting cancels in the
  tilt if wealth-uniform; levels are never published claims.
- Where a sample links only some deaths (za2011a: ~10%), record
  `linked_share` and run the linked-vs-unlinked composition check (province,
  urban, sex, age) before trusting the tilt.
- `MIN_BAND_DEATHS = 900` gates publication of an age-band tilt.
- **The MORTNUM check gates publication of any new sample.** Compare the
  supplementary per-death file against the same households' own reported
  death counts (MORTNUM in the extract) *within each wealth group*. Even
  record loss cancels out of a tilt; wealth-skewed loss biases it. Flat to
  within a percent or two = publish. This caught br2010a (IPUMS ships 48% of
  the deaths the census reports, loss concentrated in wealthy households),
  np2001a (0.77/0.79/0.90/1.13 - biases flat) and sv2007a (0.96 down to 0.58
  - biases steep). Mark rejects `publish=False` with the evidence in the
  config; never delete the config entry.
- Tilt steepness tracks national income, not HIV or region:
  `tilt ~ 1.25 - 0.24*ln(GNI per capita)`, r = -0.85 over 16 censuses.
  Excluding South Africa the tilt-vs-HIV-prevalence correlation is +0.00.
  Borrowing tables should key on income level; a long OG transition should
  expect the gradient to steepen as the country's income rises.
- The gradient fades with age in every census measured (8/8, mean drift
  +0.78 from 15-29 to 60-74) and in the poorest countries it crosses zero -
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
  household and materially changed za2011a's published tilt (-1.14 -> -0.80).
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
  still have age-band tilts biased by skewed age reporting. ci1998a's
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
5. Tilt cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures regenerated and visually inspected; docs regenerated, not edited.
