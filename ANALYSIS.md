# The gradient library, in figures

Documentation of the data in this repo. **This file is generated** by
[`scripts/build_analysis.py`](scripts/build_analysis.py) from the CSVs in
[`data/`](data/); every number below is computed from the data, not hand-typed,
so it cannot drift. Figures come from
[`scripts/make_figures.py`](scripts/make_figures.py) and live in
[`figures/`](figures/). Regenerate everything with `uv run scripts/refresh.py`.

Method pages, the full adult-mortality table, and per-country provenance pages
live under [`docs/`](docs/) — see the map in the [README](README.md).

South Africa is highlighted throughout as the worked example; pass
`--highlight "<country>"` to `make_figures.py` to feature any other.

The **tilt** summarizing each survey is the OLS slope of ln(rate) on wealth-rank
percentile midpoints (quintiles at the 10th…90th percentile) — the same log scale
OG-Core's income-group demographics consume. Negative means the poor have higher
rates; a tilt of −0.79 puts the poorest decile's rate at about
e^(0.79×0.8) ≈ 1.9× the richest decile's.

Coverage: **330 surveys with complete wealth quintets across
78 countries**, giving 891 country-survey-margin tilts (most
recent survey per country used for the library view below).

## Every country, individually

Nearly every line slopes down: the wealth gradient in fertility is close to
universal. South Africa is both low-fertility and mild-gradient (tilt
−0.51 in 2016, vs the pooled median of −0.79).

![Fertility (TFR) by household wealth rank, one line per country](figures/fig1_tfr_gradients.png)

The same universal direction holds for child mortality, with wider spread across
countries. South Africa's non-monotonic top quintiles reflect the small
child-mortality samples in its 2016 survey.

![Under-5 mortality by household wealth rank, one line per country](figures/fig2_u5mr_gradients.png)

### Use infant mortality, not under-5, for `infmort_gradient`

The library carries both. They are not interchangeable, and the difference runs
one way: across the 289 surveys that report both by wealth quintile, the
under-5 tilt is steeper than the infant tilt by a median
0.14, and it is steeper in 84% of
them. The two are strongly correlated (r = 0.94), so the shape of the
story is the same — but the level is not, and the gap reaches
0.67 (Nigeria 2018).

The reason is what under-5 mortality includes. Deaths between ages 1 and 4 are
dominated by diarrhoea, malaria, and malnutrition, which wealth protects against
strongly; infant deaths lean toward prematurity and birth complications, which it
protects against much less. Using under-5 as the infant proxy therefore imports
the steeper child-mortality gradient into a parameter meant to describe infants.
Prefer `indicator == "IMR"`, and fall back to `"U5MR"` only for the surveys that
report no infant quintiles.

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

**Infant mortality tilt by region** — the series `infmort_gradient` should use

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Latin America & Caribbean | 11 | −1.03 | −1.37 to −0.72 | 2.69 |
| South & Southeast Asia | 12 | −0.99 | −1.35 to −0.72 | 2.26 |
| North Africa/West Asia/Europe | 10 | −0.75 | −1.06 to −0.55 | 2.06 |
| Oceania | 1 | −0.72 | (single survey) | 1.74 |
| Central Asia | 5 | −0.55 | −0.90 to −0.17 | 1.53 |
| Sub-Saharan Africa | 39 | −0.52 | −0.67 to −0.22 | 1.52 |

**Under-5 mortality tilt by region** — the fallback, and steeper (see below)

| Region | Countries | Median tilt | IQR | Median poorest/richest ratio |
|---|---|---|---|---|
| Latin America & Caribbean | 11 | −1.26 | −1.46 to −0.91 | 2.80 |
| South & Southeast Asia | 12 | −1.06 | −1.48 to −0.82 | 2.42 |
| North Africa/West Asia/Europe | 10 | −0.85 | −1.25 to −0.76 | 2.38 |
| Oceania | 1 | −0.84 | (single survey) | 1.92 |
| Sub-Saharan Africa | 39 | −0.72 | −0.96 to −0.37 | 1.80 |
| Central Asia | 5 | −0.37 | −0.52 to −0.25 | 1.40 |

## Stability over survey years

All 891 country-survey-margin tilts plotted by fieldwork year, with a
rolling median. The
pooled gradient is nearly flat across three and a half decades — wealth gradients
are a stable structural feature, not an eroding one, so a borrowed gradient is not
a decaying quantity. South Africa's own fertility gradient flattened between its
1998 and 2016 surveys.

![Gradient tilts across survey years](figures/fig4_slopes_over_time.png)

**Stable across countries is not the same as stable within one.** The flat line
above is a pooled median over many countries; a single fast-developing country
can move a long way underneath it. Brazil is the worked case — see the census
series below, where its child-mortality gradient roughly halves in twenty years.
Read the pooled stability as "a borrowed gradient does not decay", not as "a
country's own gradient will not change".

## Child mortality from censuses, and Brazil's twenty-year trend

The DHS child-mortality gradients above are one survey per country, and for some
countries that survey is old — Brazil's only usable DHS is 1996. Censuses ask
every mother how many children she has borne and how many are still alive, so
the household asset index already used for adult mortality yields a
child-mortality gradient for any census year, including years no survey covers.
These rows live in
[`data/census_child_mortality.csv`](data/census_child_mortality.csv).

The measure is the proportion of children ever born who have died — the classic
Brass indirect indicator, for mothers aged 25–29. It is cumulative rather than a
period rate, so **its levels are not comparable to DHS U5MR levels and must not
be pooled with them.** Only the tilt is comparable.

That comparability was tested rather than assumed. Brazil's 2000 census sits four
years after its 1996 DHS, and the two agree to 0.014: the census
gives −1.45 where the Brazil 1996 DHS U5MR gradient is
−1.46. Two independent sources, with different measures and
different wealth rankings, landing on the same number.

| Census | Groups | Tilt | Poorest/richest | Poorest group's children dead |
|---|---|---|---|---|
| 1991 | 4 | −1.76 | 4.41 | 10.6% |
| 2000 | 4 | −1.45 | 3.20 | 6.2% |
| 2010 | 5 | −0.84 | 2.08 | 2.4% |

**Brazil's child-mortality gradient roughly halved**, from −1.76 in
1991 to −0.84 in 2010. Child mortality fell in every
group, but proportionally faster among the poor, and the poorest-to-richest ratio
narrowed from 4.4× to 2.1×.

That is a real change, not an artefact of the asset index growing richer over
time (1991 offers four asset variables, 2010 offers ten). Re-estimating every
census on only the assets common to all three — electricity, fridge, TV, radio
and cars — the flattening is *larger*, 1.06 against
0.91 on the full index. Both variants are published, tagged by
the `index` column; use `index == "full"`, which supports more wealth groups. The
common-index 2010 estimate collapses to two groups, because by then nearly every
Brazilian household owned all four items — a warning that simple durable-goods
indices stop discriminating as a country gets richer.

**For calibration:** the library's Brazil DHS row is a 1996 tilt of −1.46, and by
2010 the value was near −0.84. A present-day Brazilian calibration
using the DHS row overstates the child-mortality gradient by roughly 0.5.

## Adult mortality gradients (census household-deaths modules)

Adult mortality by wealth comes from census microdata, not DHS surveys — the
household outlives the deceased and reports the death alongside its assets. The
method, the assets-vs-income validation, and the completeness checks are on the
[adult-mortality method page](docs/methods/adult-mortality.md); the full
per-census table is in
[docs/tables/adult_mortality.md](docs/tables/adult_mortality.md); and the
fallback for unmeasured countries is the
[general gradient](docs/methods/general-gradient.md).

The age pattern — steepest at prime working ages, fading in old age — is the
by-age shape ogcore's `mort_gradient` accepts directly, and it holds in every
one of the 18 censuses measured:

![Adult-mortality tilt by age band and country](figures/fig5_amr_age_profile.png)
