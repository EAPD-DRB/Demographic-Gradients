# Methodology

This note summarizes how the estimates in the library are produced and how
they map to OG-Core. Each section links to a detailed page; terms are defined
in the [glossary](glossary.md).

## 1. Purpose and scope

The library measures how fertility and mortality differ between poorer and
richer households in low- and middle-income countries. It supplies three of
the arguments with which OG-Core's `get_pop_objs` differentiates demographic
rates across lifetime-income groups: `fert_gradient` (fertility),
`infmort_gradient` (infant mortality) and `mort_gradient` (mortality by age).
Fertility and child mortality come from surveys of the DHS Program and from
UNICEF's Multiple Indicator Cluster Surveys (MICS); adult
mortality comes from records of deaths in the household, in population
censuses and, for India and Bangladesh, in household surveys; child mortality
for Brazil also comes
from censuses.

## 2. Summary measures

Each differential is summarized by the **wealth gradient** *b*, estimated by
least squares from

    ln(rate_g) = a + b × rank_g

where *g* indexes wealth groups and *rank_g* is the midpoint of group *g* on a
wealth scale from 0 (poorest) to 1 (richest). For DHS quintiles the midpoints
are 0.1, 0.3, 0.5, 0.7 and 0.9, and the fit is ordinary least squares. Census
groups need not be of equal size: each is placed at the midpoint of its
population share, and the fit is weighted by that share. A negative gradient
means the rate falls as wealth rises. On the log scale, the gradient is
unaffected by proportional differences in the level of the rate. Gradients are
most comparable within a source: a census divided into three or four wealth
groups may yield a flatter gradient than a quintile breakdown.

The **low/high ratio**, the rate in the lowest wealth group divided by the
rate in the highest, is reported alongside the gradient. It corresponds to the
ratio published in DHS reports, but it uses only the two extreme groups and is
more affected by sampling variation. For census estimates with fewer than five
groups it is not comparable with a quintile ratio.

No standard errors are published; each gradient is a fit to five or fewer
group rates.

## 3. Wealth ranking

DHS surveys do not collect household income, and income recorded in a census
after a death excludes the earnings of the deceased, so households are ranked
by assets. DHS estimates use the DHS wealth index, a composite index of
household assets and housing characteristics divided into quintiles of the
household population.

Census estimates use an index built the same way (Filmer and Pritchett 2001):
the first principal component of household indicators, one for each durable
good or amenity recorded in the census (for example electricity, a
refrigerator or a television) and one for each type of toilet. The assets
available differ by census. The index is cut at the values closest to the
20th, 40th, 60th and 80th percentiles of its distribution over the household
population. Where many households have the same score, cut points can
coincide, and are then dropped; a cut at the lowest score, which would leave
the lowest group empty, is also dropped. A group holding
less than 10 percent of the population is merged with its smaller neighbour.
A census may therefore yield three, four or five groups; one that yields fewer
than three is not used. Because assets are measured after the death, ranking
by assets reduces but does not remove reverse causation.

## 4. Fertility and infant mortality

Rates by wealth quintile are taken from the DHS Program indicator API: the
total fertility rate (TFR), age-specific fertility rates (ASFR), the infant
mortality rate (IMR) and the under-five mortality rate (U5MR). The surveys are
Demographic and Health Surveys and, for a few countries, Malaria Indicator
Surveys. TFR, IMR and U5MR from MICS surveys are added from the World Bank's
compilation of survey results, with infant and under-five mortality only where
they are direct estimates from a full birth history, as in the DHS, and with
checks that exclude values filed under the wrong indicator
([details](methods/dhs-gradients.md#multiple-indicator-cluster-surveys)). All
surveys are kept; each row records its source. Fertility rates refer to the three years before the survey and
mortality rates to the ten years before it. Surveys without a positive value
for every quintile are excluded. A gradient is estimated for each survey, and
calibrations use the latest survey for each country
([details](methods/dhs-gradients.md)).

**Infant mortality.** `infmort_gradient` uses the IMR gradient. The U5MR
includes deaths at ages 1–4, which are more strongly associated with wealth,
and its gradient is steeper; it is published for comparison.

**Fertility by age.** The fertility differential is larger at ages 15–19 and
40–49 than at 25–34. A gradient is estimated for the ASFR of each five-year age
group, and its difference from the survey's TFR gradient is computed. The
median of these differences across countries' latest surveys gives the **age
offsets**; a country's fertility gradient at age *a* is its TFR gradient plus
the offset for *a*. In a comparison over consecutive surveys of the same
country, the pooled offsets (estimated without that country) predicted the
next survey's age pattern considerably better than a single TFR gradient. The
country's own previous survey performed about as well overall, better at
15–24 and worse at 35–44. Pooled offsets are used because they are available
for every country and age; the 45–49 offset rests on fewer countries than the
others ([details](methods/fertility-by-age.md)).

**Countries without a survey.** The regional median gradient is used, with the
interquartile range as a sensitivity range.

## 5. Child mortality from censuses

Censuses record, for each woman, the number of children ever born and the
number surviving. For mothers aged 25–29 the proportion who have died, the
standard indirect (Brass) measure, approximates mortality before about age
three. It is cumulative, so its levels are not comparable with survey rates.
Census estimates are currently available only for Brazil (1991, 2000 and
2010). For the 2000 census, the gradient in this measure is close to the
under-five mortality gradient in the 1996 DHS; this is the only comparison
available. Because the measure resembles under-five rather than infant
mortality, using it for Brazil's `infmort_gradient` probably overstates the
infant gradient somewhat.

## 6. Adult mortality from household-death records

Surveys usually provide adult mortality only through sibling histories, which
record deaths of the respondent's siblings but not the deceased's own
household; in tests on DHS data, under-reporting of deaths by poorer
respondents produced gradients of implausible sign. The library therefore uses
censuses and surveys that record deaths of household members during a recent
reference period alongside the household's characteristics
([details](methods/adult-mortality.md)). Census samples come from IPUMS
International, for Brazil from IBGE's 2010 census sample microdata, and for
Colombia from DANE's 2018 census microdata; the reference period is usually
twelve months (calendar year 2017 for Colombia). Survey estimates come from India's
National Family Health Survey and Bangladesh's Maternal Mortality and Health
Care Survey 2016, using deaths in the two years before the interview, with
households ranked by each survey's own wealth quintiles.

For each wealth group, the death rate in each age band (15–29, 30–44, 45–59
and 60–74) is the weighted number of deaths divided by the weighted population
of the same age. The probability of dying between ages 15 and 60 is

    45q15 = 1 − (1 − m₁₅)¹⁵ (1 − m₃₀)¹⁵ (1 − m₄₅)¹⁵

where *m_x* is the death rate in the band starting at age *x* (for surveys,
deaths in the two-year window divided by twice the population), treated as a
constant annual probability. Band rates and 45q15 are published only where
they rest on at least 900 death records; the number of records behind each
estimate is given in the `n_deaths` column. Rates are stored per 1,000.

The 45q15 gradient is fitted to −ln(1 − 45q15), the cumulative death rate
over ages 15–59, not to 45q15 itself. A probability cannot exceed 1, so where
adult mortality is high, 45q15 differs between wealth groups by less than the
death rates behind it, and a gradient fitted to it would understate the
gradient in death rates, which is what OG-Core applies. The cumulative death
rate is proportional to the death rates, so its gradient is also unaffected by
under-recording that is uniform across wealth groups.

`mort_gradient` uses the 45q15 gradient, spread across ages 15–59 with the
pooled age offsets described in section 7; ages 5–14 take the 15–29 value;
ages 60–74 take the 45–59 value, tapered to zero by age 75; and ages 75 and
above and the model's final age take no gradient. The treatment of ages 1–4 is
still to be decided. The full rule is on the
[general-gradient page](methods/general-gradient.md#age-pattern) and each
country page.

**Death reporting.** Censuses under-record deaths. Under-recording that is the
same in every wealth group does not affect the gradient; under-recording that
varies with wealth does. Where the census records the number of deaths per
household, the weighted death records are compared with that number within
each wealth group; the build script prints the comparison for every such
sample, and samples in which the ratio varies with wealth are not published.
The check cannot be made for South Africa 2001 or Côte d'Ivoire 1998, which do
not record that number. South Africa 2011, Mozambique 2007, Nepal 2001,
El Salvador 2007 and the IPUMS supplement for Brazil 2010 are not published on
these grounds; Burkina Faso 1996 is not published because its deaths cannot be
assigned to households reliably, Rwanda 2002 because it yields two wealth
groups. Censuses and surveys also
miss deaths that dissolve a household and deaths in institutions.

Survey records are part of the household interview, so no records are lost
between the interview and the data file. The survey script instead compares,
by wealth quintile, deaths reported for the second year before the interview
with those for the first (recall), and the shares of deaths with unknown age
or date. Of the Indian surveys, NFHS-1 (1992–93) is not used because its data
file contains no age at death; the Pakistan 2006–07 survey is not used because
only a subsample with too few deaths can be ranked by wealth.

## 7. Countries without an adult-mortality estimate

Across countries, the adult-mortality gradient becomes more negative as
income rises. The **general gradient** is the least-squares regression of the
45q15 gradient on the logarithm of GDP per capita at purchasing-power parity,
in constant international dollars (World Bank), in the census or survey year:
the conventional measure for comparing living standards across countries and
over time. Census and survey
observations enter with equal weight. Most observations are African censuses;
the others are Brazil's 2010 census and India's surveys. The rule was selected
over a single pooled value and over regional medians by leave-one-country-out
prediction error, all three scored on the same observations. Standard errors
and confidence intervals are conventional OLS ones. For a country without its
own estimate the rule is reported with a 95% prediction interval, which is
much wider than the confidence interval of the line because individual
countries scatter around it. Within countries the evidence on change over time
is limited: Malawi's gradient steepened between two censuses as income rose,
while India's changed little over two decades of rising income. The rule is
spread across age bands by adding the median difference, across estimates,
between each band's gradient and the 45q15 gradient; these offsets are fitted
in-sample, and those for ages 45–59 and 60–74 are the least reliable
([details](methods/general-gradient.md)).

Because income is measured in constant prices and at purchasing-power parity,
the rule applies to the same series for any year without conversion. It
replaced an earlier version estimated on GNI in current US dollars, which
mixed the price levels of different years and fitted about equally well. The
rule should not be extrapolated outside the income range of the observations.

## 8. Conversion to OG-Core

OG-Core expresses differences across income groups as a slope in the log-odds
of a rate per centered percentile point (percentile rank minus 50), applied
through a mean-preserving logistic function. A wealth gradient is converted by
dividing it by 100 × (1 − p), where p is OG-Core's own rate at that age:
births per person per year for fertility (the ASFR per 1,000 women divided by
2,000) and the annual probability of death for mortality. The conversion was
checked by passing every DHS quintile set for infant mortality, under-five
mortality and age-specific fertility through OG-Core's function; after
conversion the remaining discrepancy is small except at ages 45–49. Adult
mortality sets were not tested; at adult death rates 1 − p is close to one
([details](methods/ogcore-units.md)).

## 9. Quality checks

| Check | What it tests |
|---|---|
| Five times the sum of the ASFRs compared with the published TFR, by quintile | consistency of the fertility inputs |
| Deaths in the death file compared with household-reported deaths, by wealth group, where available | whether under-recording varies with wealth |
| Minimum of three wealth groups and 900 death records per estimate | stability of each adult-mortality estimate |
| Survey deaths reported for the second year before interview compared with the first, by wealth quintile | whether recall of deaths varies with wealth |
| Census and DHS child-mortality gradients compared for Brazil 2000 | comparability of the two sources (one comparison) |
| Leave-one-country-out prediction of each census or survey by the general gradient | out-of-sample accuracy of the income rule |
| Pooled fertility offsets compared with country-specific patterns over consecutive surveys | choice of pooled offsets |
| Conversion tested against OG-Core's code for DHS quintile sets | correct units for the model |
| MICS fertility rates compared with the national TFR; MICS mortality limited to direct estimates | that MICS values measure the same quantities as the DHS values |

Re-running the scripts on the same inputs reproduces the published census
and survey adult-mortality files exactly, including Brazil's rows. The income figures behind
the general gradient are stored with their retrieval date, since the World
Bank revises historical values and purchasing-power parities. DHS-based files are downloaded from the DHS
Program API and reflect the download date given in the README; MICS values are
kept as downloaded from the World Bank's compilation, which is no longer
updated.

## 10. Limitations

Asset rank is used as a proxy for lifetime income; no source distinguishes
groups within the richest quintile; some surveys are old; older-age
adult-mortality estimates are uncertain; the only Asian adult-mortality
estimates are India's; and no sampling uncertainty is published. See
[sources, citation and limitations](sources.md).
