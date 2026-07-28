# Working conventions for this repo

Demographic-Gradients hosts wealth gradients in demographic rates for OG-Core
country calibrations. Data lives in `data/`, everything is regenerable by
scripts, and the documentation is generated — respect that architecture.

## Non-negotiables

- **Never hand-edit `ANALYSIS.md` or the README's marked headline table** —
  both are written by `scripts/build_analysis.py` from the CSVs. Change the
  generator or the data, then regenerate (`uv run scripts/build_analysis.py`,
  or `uv run scripts/refresh.py` for the full DHS refresh).
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
