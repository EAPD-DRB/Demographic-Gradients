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

## Per-sample gotchas already paid for

- IPUMS extract variables differ by census — submit with the full wish list
  and let the API's 400 errors name what to drop (za2001a has no MORTNUM,
  AUTOS, WASHER, INTERNET; za2007a no AUTOS/WASHER).
- Supplementary death files have inconsistent schemas: za2011a carries
  `wtmort`, the older SA files carry no weight at all; sex codes are 1/2 but
  arrive as mixed dtypes — coerce numerics explicitly.
- `find_extract_for()` matches extracts to samples via the SAMPLE code
  (ISO-numeric country + year + "01"); the country-code mapping currently
  covers za/br only — extend it when adding countries (Ethiopia = 231).
- Weights carry two implied decimals (`dcml=2` in the DDI) — divide by 100.
- macOS `unzip` fails on Latin-1 zip names; use Python zipfile with a
  cp437→latin-1 re-encode when handling NSO archives.

## Verification standard for any new country

1. Extract's weighted population reproduces the census total.
2. Linkage rate measured and recorded; composition check if < 1.
3. Tilt cross-checked against the library's existing range and any published
   national evidence.
4. The shipped script — not session code — produces the committed rows.
5. Figures regenerated and visually inspected; docs regenerated, not edited.
