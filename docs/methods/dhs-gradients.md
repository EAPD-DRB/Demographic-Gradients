# Fertility & child mortality by wealth: the DHS pipeline

How [`data/gradient_library_latest.csv`](../../data/gradient_library_latest.csv)
and its full-history sibling `gradient_library.csv` are built by
`scripts/build_gradient_library.py`.

## Source

The [DHS Program indicator API](https://api.dhsprogram.com) — indicators
`FE_FRTR_W_TFR` (total fertility), `CM_ECMR_C_IMR` (infant mortality), and
`CM_ECMR_C_U5M` (under-5 mortality), plus the age-specific fertility rates
`FE_FRTR_W_A15` … `FE_FRTR_W_A45`, with the "Wealth quintile"
characteristic breakdown. Wealth quintiles are the DHS household asset index.
Surveys with incomplete quintets are dropped, never imputed. Credit the DHS
Program alongside this repo when using these numbers.

## The tilt

The tilt (`slope`) is the OLS slope of ln(rate) on wealth rank measured 0 to 1
(quintile midpoints at 0.10 … 0.90) — the change in the log rate from the
bottom to the top of the wealth distribution. Negative = poor higher. `ratio`
is the implied poorest/richest **decile** ratio, and `q1..q5` are the five
quintile values behind each tilt.

## Fertility by age

The same script fits a tilt at each five-year age of mother and writes how
far each sits from the survey's TFR tilt. Pooled across countries, those
differences are the **age offsets** in `fertility_age_offsets.csv`; the
per-survey values are in `fertility_age_tilts.csv`. Pooled offsets are the
published route because a country's own age shape predicts its next survey no
better than they do. The numbers, checks and recipe are on the generated
[fertility by age](fertility-by-age.md) page.

## IMR vs U5MR

Both are published, and they are not interchangeable: across the surveys that
report both, the under-5 tilt is steeper than the infant tilt by a median
0.14, because under-5 bundles in ages 1–4, where deaths are dominated by the
sharply wealth-graded infectious causes (diarrhoea, malaria, malnutrition),
while infant deaths lean toward prematurity and birth complications, which
wealth protects against much less. **Use `IMR` for ogcore's
`infmort_gradient`**; `U5MR` is only the fallback for surveys reporting no
infant quintiles. The computed comparison (count, median gap, worst case)
lives in [ANALYSIS.md](../../ANALYSIS.md).

## Limits

See [sources, citation and limits](../sources.md).
