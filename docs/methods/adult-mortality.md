# Adult mortality by wealth: census household-death records

This page describes how the estimates in
[`data/adult_mortality_gradients.csv`](../../data/adult_mortality_gradients.csv)
are constructed. All estimates are listed in
[the full table](../tables/adult_mortality.md); countries without an estimate
use the [general gradient](general-gradient.md).

## Data

Household surveys cannot measure adult mortality by household wealth, since
the deceased are not interviewed, and sibling histories do not record the
deceased person's household. Some censuses, however, ask each household about
deaths of members during a recent reference period (usually the previous
twelve months), with the age and sex of the deceased. These records, linked to
the household's assets, are the basis of the estimates. The census samples
come from IPUMS International; Brazil's come from IBGE's 2010 census sample
microdata. Microdata are processed locally and only aggregate estimates are
published, as the IPUMS license requires.

## Wealth ranking

Households are ranked by an asset index rather than by income. Household income
recorded after a death excludes the earnings of the deceased, so ranking by
income would partly reflect the death itself; assets are less affected. In a
comparison using the São Paulo census data, death rates by asset group were
monotonic while death rates by income group were not.

The index is the first principal component of household indicators, one for
each durable good or amenity recorded in the census and one for each type of
toilet, following Filmer and Pritchett (2001) and the DHS wealth index. It is
computed from the household-weighted correlation matrix of the indicators and
oriented so that it rises with the number of assets owned
(`scripts/asset_index.py`). The assets available differ by census and are
recorded for each sample in `scripts/build_adult_mortality.py`; for Brazil the
index uses ten durable goods and the number of bathrooms.

## Estimation

Wealth groups are formed by cutting the index at the values closest to the
20th, 40th, 60th and 80th percentiles of its distribution over the household
population. Where many households share a score, cut points can coincide or
fall at the minimum or maximum, and are dropped; a group holding less than 10
percent of the population is merged with its smaller neighbour. The number of
groups therefore depends on the asset distribution (`groups` column): fewer
than five where many households share the same index value, as where most own
none of the recorded assets. A census yielding fewer than three groups is not
published.

For each group, the age-specific death rate (`mx`) for 15–29, 30–44, 45–59 and
60–74 is the weighted number of deaths at those ages divided by the weighted
population of the same ages in the group. Deaths are weighted by the weight in
the supplementary death file where one is provided, and otherwise by the
household weight. The probability of dying between ages 15 and 60 is computed
from the first three bands as 45q15 = 1 − ∏(1 − mx)¹⁵, treating each band's
rate as a constant annual probability. Band rates and 45q15 are published only
where they rest on at least 900 death records, given in `n_deaths`.

The wealth gradient is the slope of the log rate on wealth rank, with each
group placed at the midpoint of its realized population share and weighted by
that share. Because the index takes a limited number of distinct values,
groups do not always contain equal shares of the population, and the realized
midpoints are used rather than nominal quintile midpoints.

## Completeness of death reporting

Censuses under-record deaths. Under-recording that is uniform across wealth
groups does not affect a gradient; under-recording that varies with wealth
biases it. Where the census records the number of deaths per household
(`MORTNUM`), the weighted death records are compared with that number within
each wealth group. `scripts/build_adult_mortality.py` prints the comparison
for every sample; samples in which the ratio varies with wealth are not
published. The check cannot be made for South Africa 2001 or Côte d'Ivoire
1998, which have no `MORTNUM`.

The following samples are not published. Their configuration and the evidence
are retained in `scripts/build_adult_mortality.py` with `publish=False`.

| Sample | Reason |
|---|---|
| South Africa 2011 | About 9 percent of death records link to a household, and the linked share is lower in wealthier households; the gradient would be too steep |
| Mozambique 2007 | Death records short in the lowest wealth group; the gradient would be too flat |
| Nepal 2001 | Death records short in the poorer groups |
| El Salvador 2007 | Death records short in the richer groups |
| Brazil 2010 (IPUMS supplement) | About half of the deaths the census reports, with the shortfall concentrated in wealthier households; Brazil's estimates use IBGE's own microdata instead |
| Burkina Faso 1996 | Death records identify the dwelling, not the household, so deaths cannot be assigned to households reliably |
| Rwanda 2002 | Only two wealth groups |
| Cambodia 2008 | Held pending a second Asian source: it passes the checks, but it would be the only Asian census in the set |

The library therefore has no census estimate for an Asian country.

Brazil's estimates are produced by `scripts/build_adult_mortality_brazil.py`,
which downloads the 2010 census sample microdata from IBGE's public server
and applies the same index and rules.

## Verification for new samples

1. The weighted population of the extract reproduces the census total.
2. The share of death records linked to households is recorded; where it is
   below one, linked and unlinked deaths are compared by province, residence,
   sex and age.
3. The `MORTNUM` check shows no systematic variation with wealth.
4. Recorded deaths are compared with the expected national total (crude death
   rate × population), and the coverage is recorded.
5. The gradient is compared with the library's existing range and with
   published national evidence.
6. The published rows are produced by the committed script and are reproduced
   exactly on a re-run.
7. Figures and documentation are regenerated.
