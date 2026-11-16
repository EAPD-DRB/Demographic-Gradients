# Sources, citation and limitations

## Sources

**Fertility and child mortality.** [DHS Program indicator
API](https://api.dhsprogram.com), wealth-quintile breakdowns of the total
fertility rate (`FE_FRTR_W_TFR`), age-specific fertility rates
(`FE_FRTR_W_A15` … `FE_FRTR_W_A45`), the infant mortality rate (`CM_ECMR_C_IMR`)
the under-five mortality rate (`CM_ECMR_C_U5M`) and child mortality at ages 1–4
(`CM_ECMR_C_CMR`). Access is free and does not
require registration. Surveys without a complete quintile breakdown are
excluded. Multiple Indicator Cluster Survey (MICS) rates by wealth quintile
come from the World Bank's [Health Nutrition and Population Statistics by
Wealth Quintile](https://databank.worldbank.org/source/health-nutrition-and-population-statistics-by-wealth-quintile)
database, which compiles them from the MICS reports; UNICEF's child-mortality
database ([data.unicef.org](https://data.unicef.org)) records whether each
survey's mortality rates are direct or indirect estimates, and the World Bank's
historical income classification and World Development Indicators supply the
checks described in [the methods](methods/dhs-gradients.md#multiple-indicator-cluster-surveys).
A copy of these downloads is kept in `data/` and refreshed with
`scripts/fetch_mics.py`.

**Adult mortality.** Census microdata with household-death modules, from
[IPUMS International](https://international.ipums.org) (free registration) and,
for Brazil, IBGE's 2010 census sample; for Colombia, DANE's 2018 census
([microdata catalogue](https://microdatos.dane.gov.co/index.php/catalog/643),
free of charge; redistribution of the microdata is not permitted); for India,
the household recode files of
the National Family Health Survey from the [DHS Program](https://dhsprogram.com)
(free registration and project approval); for Bangladesh, the Maternal
Mortality and Health Care Survey 2016 from
[UNC Dataverse](https://doi.org/10.15139/S3/X33NIZ) (open, CC0). Only aggregate estimates are
published here, as the IPUMS license and the DHS terms of use require; no
microdata are included in the repository.

**National income.** World Bank, GDP per capita, PPP, constant 2021
international dollars (`NY.GDP.PCAP.PP.KD`), for the general gradient; GNI per
capita, Atlas method (`NY.GNP.PCAP.CD`), is kept beside it for reference.

**OG-Core.** The conversion to OG-Core units is verified against the published
OG-Core source code.

## Reproduction

```
uv run scripts/refresh.py
```

downloads the DHS data and rebuilds the survey-based files, the OG-Core units
check, the figures and the generated pages. Census-based files are rebuilt
separately: adult mortality with `scripts/build_adult_mortality.py` and child
mortality with `scripts/build_census_child_mortality.py` (both require an IPUMS
account), Brazil's adult mortality with
`scripts/build_adult_mortality_brazil.py` (downloads IBGE's public microdata,
about 1.5 GB), Colombia's with `scripts/build_adult_mortality_colombia.py`
(reads DANE's department files, about 2.5 GB, downloaded by hand because each
download is behind a CAPTCHA), India's adult mortality with
`scripts/build_adult_mortality_survey.py` (requires the DHS household recode
files, and for Bangladesh the BMMS household file), and the general gradient with `scripts/build_general_gradient.py`.
The census scripts share the asset index in `scripts/asset_index.py`.

## Citation

Cite this repository together with the underlying sources:

- Fertility and child mortality: The DHS Program, ICF; for MICS surveys, UNICEF
  and the national statistical office that conducted the survey (`source ==
  "MICS"`), as compiled by the World Bank.
- Census-based estimates: Ruggles, S. et al., *Integrated Public Use Microdata
  Series, International*, Minneapolis, MN: IPUMS, doi:10.18128/D020.V7.7, and
  the national statistical office that conducted the census (given in the
  `source` column and on each [country page](countries/)).
- Brazil, adult mortality: IBGE, 2010 Census sample microdata.
- Colombia, adult mortality: Departamento Administrativo Nacional de
  Estadística (DANE), Censo Nacional de Población y Vivienda 2018, microdata.
- Bangladesh, adult mortality: National Institute of Population Research and
  Training (NIPORT), icddr,b and MEASURE Evaluation, Bangladesh Maternal
  Mortality and Health Care Survey 2016, doi:10.15139/S3/X33NIZ.
- India, adult mortality: International Institute for Population Sciences
  (IIPS) and ICF, National Family Health Survey (NFHS-2, NFHS-4, NFHS-5),
  through The DHS Program.

## Limitations

- **Wealth and lifetime income.** Households are ranked by an asset index at a
  single point in time. Its use for OG-Core's lifetime-income groups assumes
  that asset rank approximates lifetime-income rank.
- **The top of the distribution.** No source distinguishes groups within the
  richest quintile, so values for a model's highest income groups are
  extrapolations.
- **Survey dates.** The latest survey is used for each country; for some
  countries it is from the 1990s. Survey years are given on the country pages.
- **Death reporting.** Adult-mortality estimates depend on households reporting deaths.
  Under-reporting that is uniform across wealth groups does not affect the
  gradient; samples where it was found to vary with wealth are not published,
  but the check cannot be made for censuses that do not record the number of
  deaths per household. In surveys, reporting of deaths falls with time since
  the death, which is why only the two years before the interview are used
  ([methods](methods/adult-mortality.md)). Deaths that dissolve a household and
  deaths in institutions are not recorded.
- **Sampling uncertainty.** Adult-mortality gradients carry a standard error of
  sampling variability (`se`), which leaves out errors in the wealth ranking and
  in death recording; the scatter of countries around the general gradient is
  several times larger than these standard errors. DHS and MICS gradients are
  published without standard errors.
- **National income.** Purchasing-power parities are revised with each round
  of the International Comparison Program; the income figures behind the
  general gradient are pinned with their retrieval date, and a country's
  income should be taken from the same series and vintage where possible.
- **Regional coverage of adult mortality.** The general gradient is estimated
  mainly from African censuses, with two Latin American censuses, one
  Southeast Asian census (Cambodia 2008, a thin sample) and the surveys of
  India and Bangladesh; there is no estimate for East Asia, so values for
  East and Southeast Asian countries rest largely on a relationship estimated
  outside the region.
- **Older ages.** Adult-mortality gradients weaken with age and in several
  low-income censuses become positive at older ages. Estimates for these ages
  are the least certain in the library.
- **High-income countries.** The sources are designed for low- and
  middle-income countries, and the income relationship is estimated only over
  the income range of the censuses and surveys used. It should not be extrapolated to
  high-income countries.
