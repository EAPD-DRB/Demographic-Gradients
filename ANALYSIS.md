# The gradient library, in figures

Documentation of the data in this repo. Every figure is generated from the CSVs in
[`data/`](data/) by [`scripts/make_figures.py`](scripts/make_figures.py) and lives
in [`figures/`](figures/). South Africa is highlighted throughout as the worked
example; pass `--highlight "<country>"` to the script to feature any other.

The **tilt** summarizing each survey is the OLS slope of ln(rate) on wealth-rank
percentile midpoints (quintiles at the 10th…90th percentile) — the same log scale
OG-Core's income-group demographics consume. Negative means the poor have higher
rates; a tilt of −0.79 puts the poorest decile's rate at about e^(0.79×0.8) ≈ 1.9×
the richest decile's.

## Every country, individually

Nearly every line slopes down: the wealth gradient in fertility is close to
universal. South Africa is both low-fertility and mild-gradient.

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

## Stability over 35 years of surveys

All 601 surveys plotted by fieldwork year, with a rolling median. The pooled
gradient is nearly flat from 1990 to 2024 — wealth gradients are a stable
structural feature, not an eroding one, so a borrowed gradient is not a decaying
quantity. South Africa's own fertility gradient flattened between its 1998 and
2016 surveys.

![Gradient tilts across survey years, 1990–2024](figures/fig4_slopes_over_time.png)
