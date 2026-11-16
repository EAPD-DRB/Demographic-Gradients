# Fertility and child mortality by wealth: survey estimates

This page describes how [`data/gradient_library_latest.csv`](../../data/gradient_library_latest.csv)
and `gradient_library.csv`, which contains every survey, are constructed by
`scripts/build_gradient_library.py`.

## Data

### Demographic and Health Surveys

The estimates use the [DHS Program indicator API](https://api.dhsprogram.com):
the total fertility rate (`FE_FRTR_W_TFR`), age-specific fertility rates
(`FE_FRTR_W_A15` … `FE_FRTR_W_A45`), the infant mortality rate
(`CM_ECMR_C_IMR`), the under-five mortality rate (`CM_ECMR_C_U5M`) and child
mortality at ages 1–4 (`CM_ECMR_C_CMR`, 4q1), each by
wealth quintile. Wealth quintiles are those of the DHS wealth index, an index
of household assets and housing characteristics. Surveys without a value for
every quintile are excluded; no values are imputed. The reference periods are
those of the published DHS indicators.

### Multiple Indicator Cluster Surveys

UNICEF's Multiple Indicator Cluster Surveys (MICS) publish the same three rates
by wealth quintile in their survey reports, but not through a public API. The
library takes them from the World Bank's *Health Nutrition and Population
Statistics by Wealth Quintile* database, which compiles survey results and
names the survey behind each value in a footnote. Values whose footnote names
a MICS survey are used; the database's DHS values are copies of the DHS
indicators and are taken from the DHS API instead. The database is no longer
updated, and a copy is kept in the repository (`mics_quintiles_raw.csv`,
written by `scripts/fetch_mics.py`). Each MICS survey's classification and the
reason for any exclusion are recorded in `mics_surveys.csv`. The compiled
values were checked against the MICS survey reports for every excluded set and
a sample of included ones; apart from the error described under fertility,
they reproduce the reports' tables exactly. MICS values are used subject to
the following rules.

- **Child mortality.** MICS surveys estimate child mortality either directly,
  from a full birth history as the DHS does, or indirectly, from the number of
  children ever born and surviving. Only direct estimates are used, according
  to UNICEF's classification of each survey in its child-mortality database
  (`mics_methods_unicef.csv`), or the survey report where UNICEF has no record
  (`mics_methods_reports.csv`). Surveys whose method is not documented in
  either are not used. A survey is matched to UNICEF's record by overlapping
  fieldwork years, since the two sources sometimes label the same survey with
  different years. Mortality sets with a quintile rate of 3 or less per 1,000
  are excluded: such rates are correct as published but rest on very few
  deaths, and rounding alone changes the gradient substantially. No DHS set has
  a rate below 5.
- **Fertility.** For seven surveys of 2018–19 the compilation files the
  adolescent birth rate, the column beside the total fertility rate in the
  MICS fertility table, under the total fertility rate. The total fertility
  rates by quintile for these surveys are taken from the reports
  (`mics_tfr_from_reports.csv`, with table and page); where the report has not
  been read, the set is excluded. As a guard against similar errors, the build
  stops if any other MICS set's quintile mean differs from the national total
  fertility rate (World Development Indicators) by more than a factor of 1.4,
  the widest discrepancy among DHS surveys, unless the set has been checked
  against its report. A survey's own national rate can differ from the WDI
  estimate; North Macedonia 2018–19 (1.9 against 1.34) is correct as published.
- **Scope.** Surveys in countries classified by the World Bank as high income
  in the survey year are excluded.
- **Reference period.** MICS rates by wealth refer to the five or ten years
  before the survey, depending on the survey; DHS rates by wealth refer to ten
  years. The measure is the same, but some MICS sets rest on fewer births.

The compilation has no age-specific fertility rates by quintile, so the age
offsets below rest on DHS surveys only. Where a country has a DHS and a MICS
survey in the same year, the DHS survey is treated as the latest. Countries
with a MICS survey but none from the DHS are placed in the DHS Program's
regions for the regional medians (`dhs_regions.csv`, `classification ==
"assigned"`).

The two sources agree as closely as consecutive surveys of one source: the
difference between a MICS gradient and a DHS gradient for the same country
within three years varies about as much as the difference between consecutive
DHS surveys. Where they alternate, part of a country's change over time may
reflect the change of source; the `source` column identifies it.

## Wealth gradient and low/high ratio

The wealth gradient (`slope`) is the ordinary least squares slope of the log
rate on wealth rank, with the five quintiles placed at rank midpoints 0.1, 0.3,
0.5, 0.7 and 0.9. It measures the proportional change in the rate across the
wealth distribution; a negative value means the rate falls as wealth rises.
The low/high ratio (`ratio`) is the rate in the lowest quintile divided by the
rate in the highest (`q1 / q5`). The gradient uses all five quintiles and is
therefore less affected by sampling variation in a single quintile.

### Fit of the straight line

The gradient assumes that the log rate falls along a straight line across the
wealth distribution, the form in which OG-Core accepts a differential. The
table compares that line with the five quintile rates in each country's latest
survey. For fertility the line fits closely. For infant mortality the quintile
rates tend to bend: they vary little across the poorer quintiles and fall more
in the richest, so the line slightly overstates the differences among poorer
households and understates the fall at the top. Part of the poorer fit for
infant mortality is sampling variation, since each quintile rate rests on
relatively few deaths.

<!-- AUTO-GENERATED by scripts/build_analysis.py — do not edit by hand -->
| Indicator | Countries | Lowest | Second | Middle | Fourth | Highest | Median R² | Falls faster toward the top |
|---|---|---|---|---|---|---|---|---|
| Total fertility rate | 96 | −0.3 | −0.8 | +1.3 | +2.1 | −1.5 | 0.94 | 59% |
| Infant mortality rate | 88 | −4.8 | −0.2 | +2.8 | +4.1 | −4.7 | 0.70 | 70% |

Quintile columns: median across countries of the difference between the published rate and the fitted line, in percent of the fitted value. R²: share of the variation in the five log rates that the line accounts for. Last column: share of countries whose quintile rates bend downward toward the richest quintile (negative quadratic term).
<!-- END AUTO-GENERATED -->

## Fertility by age of mother

The same procedure is applied to each age-specific fertility rate. The
difference between each age gradient and the survey's TFR gradient, pooled
across countries' latest surveys, gives the age offsets in
`fertility_age_offsets.csv`; the survey-level values are in
`fertility_age_tilts.csv`. Results and validation are reported in
[fertility by age](fertility-by-age.md).

## Infant and under-five mortality

Both are published, but they are not interchangeable. The gradient in
under-five mortality is steeper in most surveys (see
[Main results](../../ANALYSIS.md#infant-and-under-five-mortality)), consistent
with the larger share of infectious causes in deaths at ages 1–4.
`infmort_gradient` uses the infant mortality rate; every survey in the library
that reports the under-five rate by quintile also reports the infant rate.

Child mortality at ages 1–4 (`CMR`) is what `mort_gradient` uses at those ages.
Its gradient is steeper than the under-five gradient in most surveys, since
under-five mortality includes infant deaths, whose gradient is flatter. It is
available from DHS surveys only (the MICS compilation does not report it), and
not where a wealth quintile records no child deaths. In those cases the
under-five gradient is used with a pooled offset
([age pattern](general-gradient.md#age-pattern); `child_mortality_offset.csv`).

## Limitations

See [sources, citation and limitations](../sources.md).
