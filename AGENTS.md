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
  full DHS refresh). The rest of `README.md`, `docs/glossary.md`,
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

Each is the rule, the reason, and the date ruled. Evidence and the history of
changes are in CHANGELOG.md and in the sample configurations; current values
are in `data/` and the generated pages (do not copy numbers here).

**Gradients**
- Gradient = slope of ln(rate) on wealth rank 0–1. Survey quintiles: OLS at
  0.1…0.9. Census groups: WLS at their realized midpoints, weighted by
  population share (`asset_index.gradient`). 2026-11-11.
- The 45q15 gradient is fitted to −ln(1 − 45q15) (`asset_index.q45_gradient`),
  not to ln(45q15): 45q15 saturates where adult mortality is high, and OG-Core
  applies the gradient to death rates. `q1`–`q5` still report 45q15.
  2026-11-16.
- An age band or 45q15 is published only from 900 death records
  (`MIN_BAND_DEATHS`). 2026-11-11.
- Every adult-mortality row carries `se`: cluster bootstrap for surveys,
  Poisson approximation for censuses (`asset_index.gradient_se`). Sampling
  only; the rule's equal weighting stays because these are far below its
  residual error. 2026-11-16.

**Census wealth ranking**
- Rank by an asset index, never by post-death household income (reverse
  causation).
- Index = first principal component of 0/1 indicators, one per asset and one
  per TOILET category, on the household-weighted correlation matrix, oriented
  to rise with assets (`scripts/asset_index.py`; Filmer and Pritchett 2001;
  DHS; Lovaton Dávila et al. 2022). The IPUMS yes-codes are documented there
  from the .cbk files — check any new variable. 2026-11-11.
- Groups: cut at the boundary between distinct scores nearest each
  person-weighted quintile; merge groups under 10% into the smaller
  neighbour; publish only with at least 3 groups (`MIN_GROUPS`); publish each
  group's share (`share1`–`share5`). 2026-11-16.
- Housing items (floor, walls, water…) stay out of the index; revisit only if
  a country cannot form 3 groups without them. 2026-11-13.

**Census completeness gates** (any new sample)
- MORTNUM check: compare the per-death file with the households' own death
  counts within each wealth group. Flat to within a percent or two: publish.
  Otherwise mark `publish=False` with the evidence in the config, and never
  delete the config entry. Uniform loss cancels in a gradient; wealth-skewed
  loss biases it.
- Deaths are weighted by the death file's own weight, else the household's
  HHWT. Census levels are never published claims.
- Partial linkage: record `linked_share` and compare linked with unlinked
  deaths (province, urban, sex, age) before trusting the gradient.
- A thin index (few asset items): test it on a richer census of the same
  country before publishing (see the gotchas below).

**Surveys**
- Household-death modules (India's NFHS, Bangladesh's BMMS) follow the census
  design: deaths of usual members in the 24 months before the interview over
  2 × the de jure population, the survey's own wealth quintiles and weights,
  the same 900-record minimum. Survey rows are told from census rows by
  `ranking` (anything but `asset_index`). 2026-11-12; BMMS 2026-11-16.
- MICS is a second source for TFR, IMR and U5MR; the latest file takes the
  newest survey of either kind (DHS on a same-year tie). Mortality only from
  direct (full birth history) estimates; sets with a quintile rate of 3 or
  less per 1,000 are excluded as imprecise; surveys of countries that were
  high income in the survey year are out of scope; fertility age offsets stay
  DHS-only. MICS inputs are pinned; refresh only with `scripts/fetch_mics.py`,
  deliberately. 2026-11-13.

**OG-Core inputs**
- Convert with gradient / (100 × (1 − p)), p = OG-Core's own rate at that age
  and period; verified by `scripts/check_ogcore_units.py` (rerun when OG-Core's
  demographics change). The library keeps publishing the log-rate gradient.
  No consumer package. 2026-11-05.
- Fertility by age = TFR gradient + pooled age offsets, not per-country age
  gradients. 2026-11-05.
- Mortality by age: 1–4 own CMR gradient, else U5MR + pooled offset; 5–14 the
  15–29 value; 15–59 the 45q15 gradient + pooled band offsets (not the
  country's own bands); 60–74 tapered from the 45–59 value to 0 at 75; 75+ and
  the final age 0. 2026-11-16.

**General gradient**
- Linear in ln(GDP per capita, PPP, constant 2021 international $,
  `NY.GDP.PCAP.PP.KD`) over every census and survey estimate, equal weights,
  classical OLS with n − 2 df. Publish the 95% prediction interval with any
  value, and never extrapolate beyond the fitted income range (country pages
  give no value outside it). 2026-11-12 and 2026-11-13.
- Income is pinned (`income_census_years.csv`, `income_latest.csv`): the World
  Bank revises history and each ICP round revises PPPs. Refresh only with
  `--refresh-income`, deliberately.
- No income-based fallback for fertility or infant mortality (the guide
  computes why); use regional medians, reported as borrowed.
- Within-country change is not established; present "held fixed" and "follows
  the income rule" as a range for long projections.

**Interpretation**
- The gradient fades with age, and in several low-income censuses turns
  positive at older ages. Real and artefactual explanations both fit and no
  check separates them: say so rather than smoothing it.

## Per-sample gotchas already paid for

- Sources that block or truncate: mics.unicef.org and its S3 bucket refuse
  scripted downloads (MICS reports are mirrored at
  mics.ipums.org/mics/resources/enum_materials_pdf/report_<iso2><year>a_<lang>.pdf);
  DANE's census files sit behind a reCAPTCHA (download by hand); the BMMS 2016
  member file is cut off at 1,048,575 rows in both Dataverse formats (use the
  household file's roster). The World Bank's MICS compilation mislabels
  adolescent birth rates as TFR for several 2018–19 surveys
  (`mics_tfr_from_reports.csv` holds the true values).

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
4. Envelope check: weighted deaths against the national death count (World
   Bank crude death rate × population). Even under-recording cancels; record
   the capture rate as a caveat (Benin 2013 and Cambodia 2008 publish at 35%
   and 48%).
5. Gradient cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures regenerated and visually inspected; docs regenerated, not edited.
