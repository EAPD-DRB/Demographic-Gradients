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
monotonic while death rates by income group were not. The assets available differ by
census and are recorded for each sample in `scripts/build_adult_mortality.py`.
The number of wealth groups depends on the asset distribution: three where most
households own few of the recorded assets, up to five otherwise (`groups`
column).

## Estimation

Wealth groups are formed by cutting the asset score at the values closest to
the quintile points of its person-weighted distribution among persons aged
15–59. Cut points that coincide, or that fall at the minimum or maximum of the
score, are dropped, which is why some censuses have fewer than five groups. For each group, the age-specific death rate (`mx`) for 15–29,
30–44, 45–59 and 60–74 is the weighted number of deaths at those ages divided
by the weighted population of the same ages in the group. Deaths are weighted
by the weight in the supplementary death file where one is provided, and
otherwise by the household weight. The probability of dying between ages 15
and 60 is computed from the first three bands as
45q15 = 1 − ∏(1 − mx)¹⁵, treating each band's rate as a constant annual
probability. Band rates are published only where the band contains at least
900 death records; 45q15 is published for every sample, with the number of
deaths behind it in `n_deaths`.

The wealth gradient is the ordinary least squares slope of the log rate on
wealth rank, with each group placed at the midpoint of its realized population
share. Because asset indices take discrete values, groups do not always
contain exactly equal shares of the population, and the realized midpoints
are used rather than nominal quintile midpoints.

## Completeness of death reporting

Censuses under-record deaths. Under-recording that is uniform across wealth
groups does not affect a gradient; under-recording that varies with wealth
biases it. Where the census records the number of deaths per household
(`MORTNUM`), the deaths in the supplementary death file were compared with that
number within each wealth group during sample review, and samples in which the
ratio varied with wealth were not published. The check is not part of the
build script, and it could not be made for South Africa 2001 and 2007 or Côte
d'Ivoire 1998, which have no `MORTNUM`.

Four samples are not published: the IPUMS mortality supplement for Brazil 2010
(about half of the deaths the census reports, with the shortfall concentrated
in wealthier households), Nepal 2001 and El Salvador 2007, which failed the
check, and Burkina Faso 1996, whose death records cannot be assigned to
households reliably. Their configuration and the evidence are retained in
`scripts/build_adult_mortality.py` with `publish=False`. The Cambodia 2008
sample was examined and is not published: most of its death records are of
children, and no adult age band reaches the publication threshold. The library
therefore has no census estimate for an Asian country.

Where linkage of death records to households is incomplete (South Africa 2011,
about 9 percent linked), linked and unlinked deaths were compared by province,
residence, sex and age during sample review.

Brazil's estimates were produced by an earlier script using IBGE microdata,
which is not part of the current build.

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
