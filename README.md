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

## Where to find what

| You want | Go to |
|---|---|
| Use the data in a calibration (input→file map, precedence, traps) | [AGENTS.md](AGENTS.md) |
| One country's estimates and where each number comes from | [docs/countries/](docs/countries/) |
| The figures, regional tables, and findings | [ANALYSIS.md](ANALYSIS.md) |
| How the DHS gradients are built | [docs/methods/dhs-gradients.md](docs/methods/dhs-gradients.md) |
| How adult mortality is measured (census death modules) | [docs/methods/adult-mortality.md](docs/methods/adult-mortality.md) |
| The fallback for countries with no adult measurement | [docs/methods/general-gradient.md](docs/methods/general-gradient.md) |
| The full per-census adult-mortality table | [docs/tables/adult_mortality.md](docs/tables/adult_mortality.md) |
| Working on the repo (regeneration, IPUMS rules) | [AGENTS.md → Working on this repo](AGENTS.md#working-on-this-repo) |

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

Fertility and child mortality come from DHS wealth-quintile breakdowns
([method](docs/methods/dhs-gradients.md)). Adult mortality cannot come from
surveys — the dead are not interviewed — so it comes from census **household
deaths modules**, with households ranked by a shock-stable asset index
([method](docs/methods/adult-mortality.md)). Countries with no census
measurement use the income-keyed
[general gradient](docs/methods/general-gradient.md).

## The file your model ingests

One CSV, one row per country and margin (most recent survey):

```
https://raw.githubusercontent.com/EAPD-DRB/Demographic-Gradients/main/data/gradient_library_latest.csv
```

Columns: `indicator` (TFR, IMR, or U5MR), `country`, `year`, **`slope`** (the
tilt — see below), `ratio` (poorest/richest decile), and `q1..q5` (the five
quintile values behind it).

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
For infant mortality use `IMR`, not `U5MR` — the under-5 tilt is steeper by a
median 0.14 ([why](docs/methods/dhs-gradients.md)).

## The headline numbers (latest survey per country)

<!-- AUTO-GENERATED by scripts/build_analysis.py — do not edit by hand -->
| Margin | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Fertility (TFR) | 77 | **−0.79** | −0.97 to −0.53 | 1.90 |
| Infant mortality | 78 | **−0.64** | −0.96 to −0.39 | 1.70 |
| Under-5 mortality (fallback) | 78 | **−0.82** | −1.16 to −0.54 | 1.96 |
| Adult mortality (45q15) | 15 | **−0.36** | −0.61 to −0.06 | 1.32 |
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
   not borrow that median — use the income relationship in the
   [general gradient](docs/methods/general-gradient.md).

## Contents

```
data/
  gradient_library_latest.csv   fertility & child mortality — one tilt per
                                country/margin (most recent survey)
  adult_mortality_gradients.csv adult mortality tilts by sex and age band
  general_gradient.csv          the fallback adult-mortality gradient (income
                                rule, by-age offsets, validation errors)
  census_child_mortality.csv    child mortality by wealth from census microdata,
                                where the DHS survey is old or absent
  gradient_library.csv          every survey (601 rows; time trends)
  dhs_gradients_raw.csv         the underlying quintile-level observations
  dhs_regions.csv               DHS Program country -> region map (for borrowing)
docs/
  methods/                      how each estimate family is built
  tables/                       the full adult-mortality table
  countries/                    per-country provenance pages (generated)
figures/                        the five figures shown in ANALYSIS.md
scripts/
  build_gradient_library.py     pull the DHS API on demand, rewrite data/
  build_adult_mortality.py      the universal IPUMS pipeline: submit slim
                                extracts, download, estimate the tilts
  build_general_gradient.py     fit + leave-one-out validate the fallback
  build_census_child_mortality.py  child mortality by wealth from censuses
  make_figures.py               rebuild figures/ from data/
  build_analysis.py             regenerate ANALYSIS.md, README numbers, and
                                the generated docs/ pages from data/
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
  row by row (each [country page](docs/countries/) carries its citation).
  Brazil is not an IPUMS product — it is built from IBGE's own open 2010
  census sample microdata and should be cited to IBGE. The IPUMS-based
  estimates rebuild only with an IPUMS account (free registration): the
  extracts come via the API and the supplementary per-death files from
  https://international.ipums.org/international/mort_fert_mig.shtml — both
  stay local; only the aggregated tilts here are redistributed, which the
  license explicitly permits.

## Honest limits

- Quintiles are household-based cross-sections, not lifetime individual rank —
  the standing assumption is that asset rank proxies lifetime-income rank.
- No quintile design resolves a top-1% income group; tilts there are
  extrapolation.
- **Some DHS rows are old** (Brazil: 1996, and its child gradient has roughly
  halved since). Check the `year` column before using a row.
- Adult-mortality gradients rest on a household's own recall of deaths;
  under-reporting is common and cancels out of a tilt only when
  wealth-uniform — the published samples are the ones where it is
  ([completeness gate](docs/methods/adult-mortality.md)).
- The general gradient rests on sixteen censuses, eleven African and none
  Asian; predictions for Asian countries are extrapolation, and its 45–59 and
  60–74 age offsets are the least trustworthy numbers in the library
  ([why](docs/methods/general-gradient.md)).
