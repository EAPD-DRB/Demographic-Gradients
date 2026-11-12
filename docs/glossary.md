# Glossary

## Summary measures

### Wealth gradient
The slope of the natural logarithm of a rate on household wealth rank, where
rank runs from 0 (poorest) to 1 (richest). Each wealth group is placed at the
midpoint of its population share (0.1, 0.3, 0.5, 0.7 and 0.9 for DHS quintiles)
and the slope is estimated by least squares, with census groups weighted by
their population share. A negative gradient means the
rate falls as wealth rises. Because the gradient is defined on the log scale,
it does not depend on the level of the rate and can be compared across
countries and indicators. It is the `slope` column in the data files.

### Low/high ratio
The rate in the lowest wealth group divided by the rate in the highest, as in
DHS reports. For census estimates with fewer than five groups, it is not
comparable with a quintile ratio. A ratio of 1 indicates no difference; a ratio above 1 indicates
a higher rate in the poorest households. It is the `ratio` column in the data
files. Because it uses only the two extreme groups, it is more affected by
sampling variation than the gradient. The ratio implied by a gradient, the
fitted value at the lowest quintile divided by the fitted value at the highest,
is exp(−0.8 × gradient).

### Age offsets
Pooled differences between the wealth gradient at a given age and the
gradient in a summary measure. For fertility, the difference between each
age-specific gradient and the TFR gradient, pooled across countries
([fertility by age](methods/fertility-by-age.md)); for adult mortality, the
difference between each age band's gradient and the 45q15 gradient, pooled
across censuses and surveys ([general gradient](methods/general-gradient.md)).

### General gradient
The relationship between the adult-mortality gradient and GNI per capita,
estimated across censuses and surveys, used for countries without their own
estimate. See
[the general gradient](methods/general-gradient.md).

## Wealth ranking

### Wealth quintile
One fifth of the household population ranked by wealth, from the lowest
(poorest) to the highest (richest) quintile. Census-based estimates use as
many groups as the asset distribution supports, between three and five
(`groups` column).

### Asset index
The measure of household wealth. DHS surveys do not collect income, and
census income recorded after a death is affected by the death itself, so
households are ranked by assets: the DHS wealth index in surveys, and in
censuses an index built the same way, the first principal component of
indicators for durable goods and amenities (for example electricity, a
refrigerator, a television or a car) and the type of toilet. Assets reflect
longer-term economic status better than current income.

## Indicators

### Total fertility rate (TFR)
The number of children a woman would have by the end of her childbearing years
at current age-specific fertility rates; five times the sum of the five-year
age-specific fertility rates.

### Age-specific fertility rate (ASFR)
Births per 1,000 women in a five-year age group (15–19, …, 45–49).

### Infant mortality rate (IMR)
Deaths before age one per 1,000 live births. Used for `infmort_gradient`.

### Under-five mortality rate (U5MR)
Deaths before age five per 1,000 live births. Published for comparison; its
gradient is steeper than the infant gradient and it is not used for
`infmort_gradient`.

### 45q15
The probability that a person aged 15 dies before age 60. The library's summary
measure of adult mortality.

### Age-specific death rate (mx)
Deaths per person per year within an age band (15–29, 30–44, 45–59, 60–74);
stored per 1,000 in the data files.

## Sources

### Demographic and Health Surveys (DHS)
Nationally representative household surveys in low- and middle-income
countries, conducted since the 1980s with support from USAID. The DHS Program
publishes fertility and child-mortality indicators by wealth quintile.

### Household-death records
Questions in some censuses, and in a few DHS-type surveys such as India's
National Family Health Survey, on deaths of household members during a recent
period (usually the previous twelve months in censuses; several years in the
Indian surveys, of which the library uses the last two), recorded alongside
the household's characteristics. They are the source for adult mortality by
wealth, which sibling histories cannot measure because they do not identify
the deceased's household.

### IPUMS International
A project at the University of Minnesota that harmonizes census microdata
provided by national statistical offices. Most census estimates in the library
use IPUMS samples; Brazil's adult-mortality estimates use IBGE microdata
directly.

### GNI per capita
Gross national income per person in current US dollars (World Bank, Atlas
method).

## OG-Core

### OG-Core
An open-source overlapping-generations model of the economy. Country
calibrations (OG-ZAF, OG-PHL and others) can differentiate fertility and
mortality across lifetime-income groups.

### Lifetime-income groups (`lambdas`)
The shares of the population in each of the model's income groups. OG-Core
places each group on the income ranking; the library's gradients apply to any
choice of groups.

### `fert_gradient`, `infmort_gradient`, `mort_gradient`, `imm_pctiles`
Arguments of OG-Core's `get_pop_objs` that set differences in demographic rates
across income groups. The library provides the first three; `imm_pctiles`, the
income distribution of new immigrants, is not provided.

### Conversion to OG-Core units
OG-Core expresses differences across groups as a slope in the log-odds of a
rate per centered percentile point. A library gradient is converted by dividing
by 100 × (1 − p), where p is OG-Core's rate at that age. See
[conversion to OG-Core units](methods/ogcore-units.md).
