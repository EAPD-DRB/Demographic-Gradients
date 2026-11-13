# Fertility and child mortality by wealth: survey estimates

This page describes how [`data/gradient_library_latest.csv`](../../data/gradient_library_latest.csv)
and `gradient_library.csv`, which contains every survey, are constructed by
`scripts/build_gradient_library.py`.

## Data

### Demographic and Health Surveys

The estimates use the [DHS Program indicator API](https://api.dhsprogram.com):
the total fertility rate (`FE_FRTR_W_TFR`), age-specific fertility rates
(`FE_FRTR_W_A15` … `FE_FRTR_W_A45`), the infant mortality rate
(`CM_ECMR_C_IMR`) and the under-five mortality rate (`CM_ECMR_C_U5M`), each by
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
reason for any exclusion are recorded in `mics_surveys.csv`. MICS values are
used subject to the following rules.

- **Child mortality.** MICS surveys estimate child mortality either directly,
  from a full birth history as the DHS does, or indirectly, from the number of
  children ever born and surviving. Only direct estimates are used, according
  to UNICEF's classification of each survey in its child-mortality database
  (`mics_methods_unicef.csv`); surveys UNICEF does not classify are not used.
  Mortality sets with a quintile rate below 5 per 1,000 are also excluded: the
  compilation mostly records whole numbers, and at such levels rounding and small
  numbers of deaths determine the gradient. No DHS set has a rate that low.
- **Fertility.** In some recent surveys the compilation files the adolescent
  birth rate, or values that cannot be total fertility rates, under the total
  fertility rate. A set is used only if the mean of its quintile rates is
  within a factor of 1.4 of the national total fertility rate in the survey
  year (World Development Indicators), the widest discrepancy found among DHS
  surveys.
- **Scope.** Surveys in countries classified by the World Bank as high income
  in the survey year are excluded.

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

## Limitations

See [sources, citation and limitations](../sources.md).
