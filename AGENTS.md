# Using this library for an OG-Core calibration

Guidance for an LLM agent (or a person) answering calibration questions with
this repo's data. It is about *consuming* the data. For working *on* the repo —
regenerating it, adding countries — read `CLAUDE.md` instead.

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
