# Fertility and child mortality by wealth: survey estimates

This page describes how [`data/gradient_library_latest.csv`](../../data/gradient_library_latest.csv)
and `gradient_library.csv`, which contains every survey, are constructed by
`scripts/build_gradient_library.py`.

## Data

The estimates use the [DHS Program indicator API](https://api.dhsprogram.com):
the total fertility rate (`FE_FRTR_W_TFR`), age-specific fertility rates
(`FE_FRTR_W_A15` … `FE_FRTR_W_A45`), the infant mortality rate
(`CM_ECMR_C_IMR`) and the under-five mortality rate (`CM_ECMR_C_U5M`), each by
wealth quintile. Wealth quintiles are those of the DHS wealth index, an index
of household assets and housing characteristics. Surveys without a value for
every quintile are excluded; no values are imputed. The reference periods are
those of the published DHS indicators.

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
