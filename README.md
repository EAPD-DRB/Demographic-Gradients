# Demographic-Gradients

Income- and wealth-gradients in demographic rates, for the OG-Core country model
family (OG-USA, OG-ZAF, OG-PHL, OG-IDN, OG-ETH, OG-BRA, ...). Since ogcore 0.18.0
the model's demographics can vary across the lifetime-income groups; this repo
collects the measured gradients a country calibration needs to set that up — from
the country's own survey when it has one, or borrowed from a documented range when
it doesn't.

It plays the same role for demographic *differentials* that
[EAPD-DRB/Population-Data](https://github.com/EAPD-DRB/Population-Data) plays for
population *levels*: a stable, reproducible mirror the country repos reference by
raw URL.

**See [ANALYSIS.md](ANALYSIS.md)** for the figures and regional tables.

## What this repo provides

Three of the gradient inputs `ogcore.demographics.get_pop_objs()` (>= 0.18.0)
accepts:

| OG-Core input | What it does | Coverage | Where |
|---|---|---|---|
| `fert_gradient` | tilts fertility across income rank | 77 countries | `data/gradient_library_latest.csv`, rows with `indicator == "TFR"` |
| `infmort_gradient` | tilts infant mortality across income rank | 78 countries | same file, `indicator == "IMR"` (fall back to `"U5MR"`) |
| `mort_gradient` | tilts adult mortality across income rank, by age | 14 countries measured, **any country via the general gradient** | `data/adult_mortality_gradients.csv`; fallback in `data/general_gradient.csv` |

(`income_percentiles`, the argument that accompanies any gradient, is not data —
it is the model's own `lambdas` vector.)

## Adult mortality gradients

Adult mortality by wealth cannot come from DHS-type surveys (the dead are not
interviewed, and sibling reports carry no wealth data). It CAN come from census
**household deaths modules**: the household outlives the deceased and reports the
death (age, sex, last 12 months) alongside its assets.
`data/adult_mortality_gradients.csv` holds these estimates — per country, sex,
and age band (`measure == "mx"`), plus a 15–59 summary (`measure == "45q15"`) —
on the same tilt scale as the fertility file.

Fourteen countries, sixteen censuses, 140,000 adult (15–59) death records:
Brazil 2010 and South Africa 2001/2007/2011 establish the method; Ethiopia
2007 covers the remaining OG-family country with a census mortality module;
and Zambia, Malawi, Mozambique, Uganda, Rwanda, Senegal, Sierra Leone,
Lesotho, Benin, Sudan and South Sudan give the borrowing set its spread.
Households are ranked by an **asset index**, not measured income: a death
mechanically removes the deceased's earnings from post-death household
income, while assets are shock-stable (validated on São Paulo, where assets
gave clean monotonic gradients and income did not).

Every census except Brazil is built by `scripts/build_adult_mortality.py` —
the universal IPUMS pipeline (slim extracts of ~12 variables, tens of MB per
census; microdata stays local per the IPUMS license, and these published
aggregates are explicitly permitted). Brazil comes from IBGE's own open
microdata, because IPUMS's supplementary death file for that census holds
only 48% of the deaths the census itself reports and loses them mainly in
wealthy households.

### The general gradient — usable by any country

**Own measurement first; the general gradient is the fallback that is always
available.** It lives in `data/general_gradient.csv`:

    tilt(45q15) = 1.291 − 0.243 × ln(GNI per capita, current US$)      ±0.16

The rule was picked by competition, each candidate judged by leaving one census
out of the fit and predicting it — the honest test, since a country using the
fallback is not in the fit:

| Candidate rule | Mean absolute error |
|---|---|
| One tilt for every country (pooled median −0.36) | 0.307 |
| **Read it off national income** | **0.142** |
| The country's regional median | 0.221 |

Income is wrong by less than half as much as a single global number and a third
less than regional medians, so the general gradient is keyed to income rather
than region. It predicts best in the middle-income range where the countries
needing it sit (mean error 0.11 above $1,000 per head, 0.17 below), and it
reproduces South Africa's own census measurement to within a rounding error.

Worked values at 2024 income: **Philippines −0.75, Indonesia −0.78, Ethiopia
−0.41**. The file also carries by-age offsets, so a model can spread the summary
tilt across bands, and a pooled median for use where no GNI figure exists.

A model running decades forward should let the gradient steepen as its income
path rises rather than holding today's value fixed.

Two caveats that matter for anyone borrowing. Eleven of the sixteen censuses
are African, and there is **no Asian observation at all** — Cambodia 2008's
death records are overwhelmingly children, leaving every adult band below
this library's minimum. And in the poorest countries the gradient turns
positive at older ages, which may be real or may reflect frail elderly
relatives moving into better-off households before they die; see
[ANALYSIS.md](ANALYSIS.md) for the evidence and why no within-census check
separates the two. HIV does not explain the pattern.

### What is deliberately not here

Three samples were built, checked, and rejected because their death records
go missing unevenly across rich and poor, which biases a tilt rather than
merely adding noise: the IPUMS supplement for Brazil 2010 (48% capture,
skewed to wealthy households), Nepal 2001 (biases the gradient flat) and El
Salvador 2007 (biases it steep). Their configurations and the evidence stay
in `scripts/build_adult_mortality.py` — rejected, not deleted.

## The file your model ingests

One CSV, one row per country and margin (most recent survey):

```
https://raw.githubusercontent.com/EAPD-DRB/Demographic-Gradients/main/data/gradient_library_latest.csv
```

Columns: `indicator` (TFR, IMR, or U5MR), `country`, `year`, **`slope`** (the
tilt — see below), `ratio` (poorest/richest decile), and `q1..q5` (the five
quintile values behind it).

For `infmort_gradient`, use **`IMR`** — it is the series ogcore's infant
parameter actually represents. `U5MR` is kept as the fallback for the few
surveys reporting no infant quintiles, but it is not a neutral substitute:
across the 289 surveys carrying both, the under-5 tilt is steeper by a median
0.14, because under-5 bundles in ages 1–4, where deaths are dominated by the
sharply wealth-graded infectious causes. See [ANALYSIS.md](ANALYSIS.md).

The **tilt** (`slope`) is the OLS slope of ln(rate) on wealth rank measured 0 to
1 (quintile midpoints at 0.10 ... 0.90), i.e. the change in the log rate from the
bottom to the top of the wealth distribution. Negative = poor higher.

**Unit conversion for ogcore (verified against ogcore 0.18.0):** ogcore evaluates
its gradients on a centered percentile-point scale (each income group's midpoint
lies between −50 and +50), so its slope is per *percentile point* while the
library's is per *unit of rank* — **divide the library tilt by 100** before
passing it (see the example below). Sign convention matches (negative = poor
higher on both sides). ogcore applies the slope through a logistic (log-odds)
form and re-solves the level so the UN aggregate rates are preserved exactly;
for rates of these magnitudes the library's log-rate slope and ogcore's log-odds
slope coincide to first order. The grouping itself needs nothing from this
library: ogcore derives each group's midpoint from the `lambdas` you pass, so
any number of income groups, of any sizes, consumes the same tilt.

## Using it in a country calibration

```python
import pandas as pd

LIB = (
    "https://raw.githubusercontent.com/EAPD-DRB/Demographic-Gradients/"
    "main/data/gradient_library_latest.csv"
)
lib = pd.read_csv(LIB)

# 1. Own data first: the country's own most recent DHS tilt
fert_tilt = lib.query("indicator == 'TFR' and country == 'South Africa'")["slope"].iloc[0]

# 2. No own survey? Borrow the regional median, and use the regional IQR
#    as the sensitivity band (regions in data/dhs_regions.csv):
# regions = pd.read_csv(".../data/dhs_regions.csv")
# ssa = lib.merge(regions).query("indicator == 'TFR' and region == 'Sub-Saharan Africa'")
# fert_tilt = ssa["slope"].median()

# 3. Feed it to ogcore (>= 0.18.0) in your Calibration's demographics call.
#    Divide by 100: the library tilt is per unit of rank, ogcore's gradient is
#    per percentile point (see "Unit conversion" above). A scalar applies the
#    same tilt at every age:
# pop_dict = demographics.get_pop_objs(
#     p.E, p.S, p.T, 0, 99,
#     country_id="710",
#     income_percentiles=list(p.lambdas),
#     fert_gradient=fert_tilt / 100,
# )
```

Either way beats the current default of assuming no gradient at all — the library
shows a tilt of zero is wrong essentially everywhere. Document which route you
took (own survey vs borrowed, with the survey year) in your calibration docs.

## The headline numbers (latest survey per country)

<!-- AUTO-GENERATED by scripts/build_analysis.py — do not edit by hand -->
| Margin | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Fertility (TFR) | 77 | **−0.79** | −0.97 to −0.53 | 1.90 |
| Infant mortality | 78 | **−0.64** | −0.96 to −0.39 | 1.70 |
| Under-5 mortality (fallback) | 78 | **−0.82** | −1.16 to −0.54 | 1.96 |
| Adult mortality (45q15) | 14 | **−0.36** | −0.69 to −0.14 | 1.32 |
<!-- END AUTO-GENERATED -->

*(330 surveys, 78 countries; DHS API pull of 28 July 2026. Regenerate with
`uv run scripts/refresh.py`.)*

Three structural findings (see [ANALYSIS.md](ANALYSIS.md)):

1. **The gradients are near-universal**: essentially every country's fertility and
   child-mortality rates decline with wealth rank.
2. **They are stable**: the pooled median fertility and child-mortality tilt is
   flat across 35 years of surveys (1990–2024). A borrowed gradient is not a
   decaying quantity.
3. **Adult mortality is the exception, and its level is an income story**: the
   adult median above is much flatter than the other two because the sample
   is mostly low-income countries, where the gradient is genuinely flat. Do
   not borrow that median — use the income relationship above.

## Contents

```
data/
  gradient_library_latest.csv   fertility & child mortality — one tilt per
                                country/margin (most recent survey)
  adult_mortality_gradients.csv adult mortality tilts by sex and age band
  general_gradient.csv          the fallback adult-mortality gradient (income
                                rule, by-age offsets, validation errors)
  gradient_library.csv          every survey (601 rows; time trends)
  dhs_gradients_raw.csv         the underlying quintile-level observations
  dhs_regions.csv               DHS Program country -> region map (for borrowing)
figures/                        the five figures shown in ANALYSIS.md
scripts/
  build_gradient_library.py     pull the DHS API on demand, rewrite data/
  build_adult_mortality.py      the universal IPUMS pipeline: submit slim
                                extracts, download, estimate the tilts
  build_general_gradient.py     fit + leave-one-out validate the fallback
  make_figures.py               rebuild figures/ from data/
  build_analysis.py             regenerate ANALYSIS.md + README numbers from data/
  refresh.py                    all three in order, plus the vintage stamp
ANALYSIS.md                     the figures and regional tables (generated)
```

## Reproducibility

Everything rebuilds from public, registration-free sources with one command:

```
uv run scripts/refresh.py
```

Data sources and required citations:

- Fertility and child mortality: the
  [DHS Program indicator API](https://api.dhsprogram.com) (indicators
  `FE_FRTR_W_TFR`, `CM_ECMR_C_IMR`, `CM_ECMR_C_U5M`, characteristic "Wealth
  quintile"). Credit
  the DHS Program alongside this repo. Wealth quintiles are the DHS household
  asset index; surveys with incomplete quintets are dropped, never imputed.
- Adult mortality: census microdata via IPUMS International — cite *Ruggles
  et al., Integrated Public Use Microdata Series, International. Minneapolis,
  MN: IPUMS (doi:10.18128/D020.V7.7)* and acknowledge the originating
  statistical office for every census used, which the `source` column records
  row by row: Statistics South Africa; Central Statistical Agency, Ethiopia;
  Central Statistical Office, Zambia; National Statistical Office, Malawi;
  Instituto Nacional de Estatística, Mozambique; Uganda Bureau of Statistics;
  National Institute of Statistics of Rwanda; Agence Nationale de la
  Statistique et de la Démographie, Senegal; Statistics Sierra Leone; Bureau
  of Statistics, Lesotho; Institut National de la Statistique et de l'Analyse
  Économique, Benin; Central Bureau of Statistics, Sudan; and the Southern
  Sudan Centre for Census, Statistics and Evaluation. Brazil is not an IPUMS
  product — it is built from IBGE's own open 2010 census sample microdata and
  should be cited to IBGE. The IPUMS-based estimates rebuild only with an
  IPUMS account (free registration):
  the extracts come via the API and the supplementary per-death files from
  https://international.ipums.org/international/mort_fert_mig.shtml — both
  stay local; only the aggregated tilts here are redistributed, which the
  license explicitly permits.

## Honest limits

- Quintiles are household-based cross-sections, not lifetime individual rank —
  the standing assumption is that asset rank proxies lifetime-income rank.
- No quintile design resolves a top-1% income group; tilts there are
  extrapolation.
- U5MR quintile cells are noisy in low-mortality countries (South Africa 2016
  visibly so — see ANALYSIS.md).
- Infant mortality is now measured directly rather than proxied by under-5, so
  the old proxy caveat is gone — but the two differ by a median 0.14 in tilt,
  so any calibration built on the earlier `U5MR` figures overstates its infant
  gradient and is worth revisiting.
- Adult-mortality gradients come from a household's own recall of deaths in
  the past 12 months. Under-reporting is common (capture against national
  death counts runs from 35% in Benin to over 100% where census and UN
  estimates disagree) and cancels out of a tilt only if it is uniform across
  wealth. The published samples are the ones where it is; see the completeness
  check in `scripts/build_adult_mortality.py`.
- The general adult-mortality gradient rests on sixteen censuses, eleven of them
  African and none Asian, so its predictions for Asian countries are
  extrapolation. A predicted tilt carries roughly ±0.16 at one standard
  deviation.
- Within the by-age offsets, **the 45–59 and 60–74 numbers are the least
  trustworthy**: they are positive because measured mortality rises with wealth
  at older ages in the poorest countries, and independent evidence from DHS
  sibling histories suggests that is at least partly a reporting artefact rather
  than a real pattern. Prefer the 15–29 and 30–44 offsets where working-age
  mortality is what matters.
- Adult tilts are estimated on however many wealth groups a census's asset
  distribution supports (the `groups` column: three where assets are sparse,
  five where they are not), and age bands publish only above 900 death
  records.
