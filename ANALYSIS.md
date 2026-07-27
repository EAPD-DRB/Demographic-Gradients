# The gradient library, in figures

Documentation of the data in this repo. **This file is generated** by
[`scripts/build_analysis.py`](scripts/build_analysis.py) from the CSVs in
[`data/`](data/); every number below is computed from the data, not hand-typed,
so it cannot drift. Figures come from
[`scripts/make_figures.py`](scripts/make_figures.py) and live in
[`figures/`](figures/). Regenerate both with `uv run scripts/refresh.py`.

South Africa is highlighted throughout as the worked example; pass
`--highlight "<country>"` to `make_figures.py` to feature any other.

The **tilt** summarizing each survey is the OLS slope of ln(rate) on wealth-rank
percentile midpoints (quintiles at the 10th…90th percentile) — the same log scale
OG-Core's income-group demographics consume. Negative means the poor have higher
rates; a tilt of −0.79 puts the poorest decile's rate at about
e^(0.79×0.8) ≈ 1.9× the richest decile's.

Coverage: **601 surveys with complete wealth quintets across
78 countries** (most recent survey per country used for the library
view below).

## Every country, individually

Nearly every line slopes down: the wealth gradient in fertility is close to
universal. South Africa is both low-fertility and mild-gradient (tilt
−0.51 in 2016, vs the pooled median of −0.79).

![Fertility (TFR) by household wealth rank, one line per country](figures/fig1_tfr_gradients.png)

The same universal direction holds for child mortality, with wider spread across
countries. South Africa's non-monotonic top quintiles reflect the small
child-mortality samples in its 2016 survey.

![Under-5 mortality by household wealth rank, one line per country](figures/fig2_u5mr_gradients.png)

## Grouped by region

Each dot is a country's most recent survey; the bar marks the regional
interquartile range and the tick marks the median. Latin America has the steepest
gradients; Sub-Saharan Africa sits mid-range; South Africa is milder than its
region's median on fertility.

![Distribution of gradient tilts by region](figures/fig3_slopes_by_region.png)

**Fertility (TFR) tilt by region**

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Latin America & Caribbean | 11 | −1.17 | −1.27 to −1.03 | 2.58 |
| Sub-Saharan Africa | 39 | −0.81 | −0.94 to −0.60 | 1.96 |
| North Africa/West Asia/Europe | 10 | −0.62 | −0.86 to −0.39 | 1.60 |
| South & Southeast Asia | 11 | −0.54 | −0.69 to −0.45 | 1.59 |
| Central Asia | 5 | −0.53 | −0.77 to −0.41 | 1.62 |
| Oceania | 1 | −0.47 | (single survey) | 1.56 |

**Under-5 mortality tilt by region**

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Latin America & Caribbean | 11 | −1.26 | −1.46 to −0.91 | 2.80 |
| South & Southeast Asia | 12 | −1.06 | −1.48 to −0.82 | 2.42 |
| North Africa/West Asia/Europe | 10 | −0.85 | −1.25 to −0.76 | 2.38 |
| Oceania | 1 | −0.84 | (single survey) | 1.92 |
| Sub-Saharan Africa | 39 | −0.72 | −0.96 to −0.37 | 1.80 |
| Central Asia | 5 | −0.37 | −0.52 to −0.25 | 1.40 |

## Stability over survey years

All 601 surveys plotted by fieldwork year, with a rolling median. The
pooled gradient is nearly flat across three and a half decades — wealth gradients
are a stable structural feature, not an eroding one, so a borrowed gradient is not
a decaying quantity. South Africa's own fertility gradient flattened between its
1998 and 2016 surveys.

![Gradient tilts across survey years](figures/fig4_slopes_over_time.png)

## Adult mortality gradients (census household-deaths modules)

Adult mortality by wealth comes from census microdata, not DHS surveys (see the
README for why). Households are ranked by an asset index; tilts are on the same
log-rate-per-unit-rank scale as the tables above. The age pattern — steep at
prime working ages, fading in old age — is the by-age shape ogcore's
`mort_gradient` accepts directly, and it replicates across every census
measured:

![Adult-mortality tilt by age band and country](figures/fig5_amr_age_profile.png)

`linked` is the share of the census's death records that carry a linkable
household ID; where it is well below 1 (South Africa 2011), rate *levels* are
meaningless but the tilt is unbiased — the linked deaths' composition matches
the unlinked on province, urban/rural, sex, and age (checked per sample).

| Country | Year | Sex | Ages | Measure | Tilt | Poorest/richest | Death records | Linked |
|---|---|---|---|---|---|---|---|---|
| Brazil | 2010 | male | 15–29 | mx | −1.41 | 2.98 | 6,876 | 100% |
| Brazil | 2010 | male | 30–44 | mx | −1.54 | 3.42 | 7,328 | 100% |
| Brazil | 2010 | male | 45–59 | mx | −0.77 | 1.84 | 11,251 | 100% |
| Brazil | 2010 | male | 60–74 | mx | −0.13 | 1.05 | 16,459 | 100% |
| Brazil | 2010 | male | 15–59 | 45q15 | −0.99 | 2.19 | 25,455 | 100% |
| Brazil | 2010 | female | 15–29 | mx | −0.99 | 2.19 | 1,881 | 100% |
| Brazil | 2010 | female | 30–44 | mx | −1.23 | 2.79 | 3,312 | 100% |
| Brazil | 2010 | female | 45–59 | mx | −0.97 | 2.26 | 6,896 | 100% |
| Brazil | 2010 | female | 60–74 | mx | −0.25 | 1.23 | 12,161 | 100% |
| Brazil | 2010 | female | 15–59 | 45q15 | −0.98 | 2.28 | 12,089 | 100% |
| South Africa | 2001 | all | 15–29 | mx | −0.91 | 1.97 | 5,939 | 100% |
| South Africa | 2001 | all | 30–44 | mx | −1.17 | 2.55 | 8,504 | 100% |
| South Africa | 2001 | all | 45–59 | mx | −0.86 | 1.95 | 5,750 | 100% |
| South Africa | 2001 | all | 60–74 | mx | −0.32 | 1.28 | 5,489 | 100% |
| South Africa | 2001 | all | 15–59 | 45q15 | −0.79 | 1.85 | 20,193 | 100% |
| South Africa | 2001 | male | 15–29 | mx | −0.79 | 1.84 | 2,835 | 100% |
| South Africa | 2001 | male | 30–44 | mx | −1.13 | 2.56 | 4,564 | 100% |
| South Africa | 2001 | male | 45–59 | mx | −0.82 | 1.94 | 3,558 | 100% |
| South Africa | 2001 | male | 60–74 | mx | −0.51 | 1.47 | 2,983 | 100% |
| South Africa | 2001 | male | 15–59 | 45q15 | −0.70 | 1.77 | 10,957 | 100% |
| South Africa | 2001 | female | 15–29 | mx | −1.03 | 2.12 | 3,104 | 100% |
| South Africa | 2001 | female | 30–44 | mx | −1.22 | 2.57 | 3,940 | 100% |
| South Africa | 2001 | female | 45–59 | mx | −0.94 | 2.02 | 2,192 | 100% |
| South Africa | 2001 | female | 60–74 | mx | −0.21 | 1.19 | 2,506 | 100% |
| South Africa | 2001 | female | 15–59 | 45q15 | −0.89 | 1.97 | 9,236 | 100% |
| South Africa | 2007 | all | 15–29 | mx | −1.21 | 2.35 | 2,421 | 100% |
| South Africa | 2007 | all | 30–44 | mx | −1.25 | 2.41 | 4,353 | 100% |
| South Africa | 2007 | all | 45–59 | mx | −1.21 | 2.25 | 2,693 | 100% |
| South Africa | 2007 | all | 60–74 | mx | −0.56 | 1.41 | 1,963 | 100% |
| South Africa | 2007 | all | 15–59 | 45q15 | −0.80 | 1.73 | 9,467 | 100% |
| South Africa | 2007 | male | 15–29 | mx | −1.18 | 2.31 | 1,071 | 100% |
| South Africa | 2007 | male | 30–44 | mx | −1.15 | 2.27 | 2,207 | 100% |
| South Africa | 2007 | male | 45–59 | mx | −1.06 | 2.05 | 1,603 | 100% |
| South Africa | 2007 | male | 60–74 | mx | −0.59 | 1.47 | 1,061 | 100% |
| South Africa | 2007 | male | 15–59 | 45q15 | −0.68 | 1.60 | 4,881 | 100% |
| South Africa | 2007 | female | 15–29 | mx | −1.24 | 2.40 | 1,350 | 100% |
| South Africa | 2007 | female | 30–44 | mx | −1.34 | 2.53 | 2,146 | 100% |
| South Africa | 2007 | female | 45–59 | mx | −1.40 | 2.51 | 1,090 | 100% |
| South Africa | 2007 | female | 60–74 | mx | −0.62 | 1.41 | 902 | 100% |
| South Africa | 2007 | female | 15–59 | 45q15 | −0.92 | 1.87 | 4,586 | 100% |
| South Africa | 2011 | all | 30–44 | mx | −1.45 | 3.47 | 988 | 10% |
| South Africa | 2011 | all | 15–59 | 45q15 | −1.14 | 2.63 | 2,245 | 10% |
| South Africa | 2011 | male | 15–59 | 45q15 | −0.99 | 2.38 | 1,193 | 10% |
| South Africa | 2011 | female | 15–59 | 45q15 | −1.30 | 2.93 | 1,048 | 10% |

Ranking: household asset index (see README for the income-vs-assets validation and the build pipeline; asset components vary by census and are recorded in `scripts/build_adult_mortality.py`).
