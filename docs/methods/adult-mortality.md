# Adult mortality by wealth: household-death records

This page describes how the estimates in
[`data/adult_mortality_gradients.csv`](../../data/adult_mortality_gradients.csv)
are constructed. All estimates are listed in
[the full table](../tables/adult_mortality.md); countries without an estimate
use the [general gradient](general-gradient.md).

## Data

Measuring adult mortality by household wealth requires deaths recorded against
the deceased person's own household. Sibling histories, the usual survey
source of adult mortality, do not provide this: they record deaths of the
respondent's siblings, who mostly lived in other households. Some censuses,
and a few DHS-type surveys, instead ask each household about deaths of its
members during a recent reference period, with the age and sex of the
deceased. These records, linked to the household's assets, are the basis of
the estimates.

- **Censuses.** Samples come from IPUMS International; Brazil's come from
  IBGE's 2010 census sample microdata, and Colombia's from DANE's 2018 census
  microdata (a full count). The reference period is usually the previous
  twelve months; in Colombia it is calendar year 2017.
- **DHS surveys.** India's National Family Health Survey records deaths of
  usual household members since a fixed date several years before the
  interview, with sex, age and month and year of death. The estimates use the
  deaths of the two years before the interview, since reporting of earlier
  deaths falls off.
- **Bangladesh Maternal Mortality and Health Care Survey 2016 (BMMS).** The
  same design: every death of a usual household member since April 2013 in
  about 298,000 households, with sex, age and date of death. It is processed
  by the same script and rules, with the survey's own wealth quintiles. The
  data are open (UNC Dataverse, CC0). The survey's household-member file is
  incomplete (cut off at a spreadsheet row limit), so persons are taken from
  the roster in the household file, which agrees with the survey's own count.

Microdata are processed locally and only aggregate estimates are published,
as the IPUMS license and the DHS terms of use require.

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

Survey estimates use the DHS wealth index distributed with each survey, an
index of the same kind built from a larger set of assets and housing
characteristics, divided into quintiles of the household population.

## Estimation

In censuses, wealth groups are formed by cutting the index at the values closest to the
20th, 40th, 60th and 80th percentiles of its distribution over the household
population; a household whose score equals a cut point belongs to the group
above it. Where many households share a score, cut points can coincide, and
are then dropped; so is a cut at the minimum score, which would leave the
lowest group empty. A cut at the maximum is kept: it separates the households
with the highest score into a group of their own. A group holding less than 10
percent of the population is merged with its smaller neighbour. The number of
groups therefore depends on the asset distribution (`groups` column): fewer
than five where many households share the same index value, as where most own
none of the recorded assets. A census yielding fewer than three groups is not
published. Survey estimates use the five DHS wealth quintiles.

For each group, the age-specific death rate (`mx`) for 15–29, 30–44, 45–59 and
60–74 is the weighted number of deaths at those ages divided by the weighted
population of the same ages in the group. In censuses, deaths are weighted by
the weight in the supplementary death file where one is provided, and
otherwise by the household weight. In surveys, deaths and population are
weighted by the household sample weight; the population is the de jure
(usual-resident) household population, and the deaths of the two-year window
are divided by twice that population. The probability of dying between ages 15 and 60 is computed
from the first three bands as 45q15 = 1 − ∏(1 − mx)¹⁵, treating each band's
rate as a constant annual probability. Band rates and 45q15 are published only
where they rest on at least 900 death records, given in `n_deaths`.

The wealth gradient is the slope of the log rate on wealth rank, with each
group placed at the midpoint of its realized population share and weighted by
that share. Because the census index takes a limited number of distinct
values, groups do not always contain equal shares of the population, and the
realized midpoints are used rather than nominal quintile midpoints. DHS
quintiles hold equal shares, and the fit reduces to ordinary least squares at
0.1, 0.3, 0.5, 0.7 and 0.9.

## Completeness of death reporting

### Censuses

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
| Benin 1992, Lesotho 1996 | Fewer than 900 adult death records |
| Benin 2002, Guinea 1983, Indonesia 1976, Malawi 1987, Mali 1987 and 1998 | Too few recorded assets for three wealth groups |
| El Salvador 1992 | Death records short in the richer groups, and some not linked to a household |
| Cambodia 2008 | Held pending review; it passes the checks |

Brazil's estimates are produced by `scripts/build_adult_mortality_brazil.py`,
which downloads the 2010 census sample microdata from IBGE's public server
and applies the same index and rules.

Colombia's estimates are produced by `scripts/build_adult_mortality_colombia.py`
from DANE's 2018 census microdata, which are free of charge but are downloaded
by hand (each department file is behind a CAPTCHA). The census records no
durable goods, so its index uses electricity, internet and toilet type, the
fewest items of any census in the library. Each household's count of its
deaths is taken from the same questionnaire as the death records and agrees
with them exactly, so the completeness check cannot detect lost records; the
national envelope check is the main test of completeness. The script also
prints, for comparison only, the gradient on an index that adds housing
materials and services; the two are similar ([country page](../countries/colombia.md)).

### Surveys

Survey estimates are produced by `scripts/build_adult_mortality_survey.py`,
which prints the following checks for each survey:

- recorded death records against the number of deaths each household reports,
  by quintile (records lost to the questionnaire's limit on the number of
  deaths would show here);
- recall: adult deaths in the second year before the interview relative to
  the first, by quintile; forgetting that varies with wealth would show as a
  trend;
- the shares of deaths with unknown date or unknown age, by quintile;
- age heaping at ages ending in 0 or 5, by quintile, and the gradient with
  persons and deaths at the band boundaries divided between adjacent bands;
- the national 45q15 by sex, for comparison with UN and World Bank estimates;
- a cluster-bootstrap standard error of the 45q15 gradient.

Age heaping is more common in poorer households in the Indian surveys, but
dividing the boundary ages changes the gradient little. For the 2019–21
survey, whose fieldwork spanned the onset of COVID-19, the gradient is also
computed separately for deaths and exposure before and from March 2020. It is
flatter in the later period, which accounts for a minority of the exposure;
the published value covers the whole period and lies close to the
pre-pandemic one (see the [India page](../countries/india.md)).

| Survey | Reason not published |
|---|---|
| India NFHS-1, 1992–93 | The released data file contains no age at death |
| Pakistan 2006–07 | Deaths were recorded in all households, but assets only in the subsample given the full questionnaire; that subsample has too few adult deaths, most of them of women |

The DHS surveys of the Philippines, Indonesia, Bangladesh, Cambodia, Nepal and
other Asian countries were examined and have no module recording deaths at all
ages. India and Bangladesh (through the BMMS, not the DHS) are therefore the
only Asian countries with an estimate.

Bangladesh's gradient is close to zero, far less steep than the general
gradient at its income, although the survey passes every check above and an
asset index built as for the censuses gives a similar value. It is published
as measured. The gradient weakens with time since death, which is consistent
with recall fading faster in poorer households; the differences between years
are within sampling error ([Bangladesh page](../countries/bangladesh.md)).

## Verification for new samples

For censuses:

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
