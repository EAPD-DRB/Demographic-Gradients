# Sources, citation and limitations

## Sources

**Fertility and child mortality.** [DHS Program indicator
API](https://api.dhsprogram.com), wealth-quintile breakdowns of the total
fertility rate (`FE_FRTR_W_TFR`), age-specific fertility rates
(`FE_FRTR_W_A15` … `FE_FRTR_W_A45`), the infant mortality rate (`CM_ECMR_C_IMR`)
and the under-five mortality rate (`CM_ECMR_C_U5M`). Access is free and does not
require registration. Surveys without a complete quintile breakdown are
excluded.

**Adult mortality.** Census microdata with household-death modules, from
[IPUMS International](https://international.ipums.org) (free registration) and,
for Brazil, IBGE's 2010 census sample. Only aggregate estimates are published
here, as the IPUMS license requires; no microdata are included in the
repository.

**National income.** World Bank, GNI per capita, Atlas method
(`NY.GNP.PCAP.CD`).

**OG-Core.** The conversion to OG-Core units is verified against the published
OG-Core source code.

## Reproduction

```
uv run scripts/refresh.py
```

downloads the survey data and rebuilds the DHS-based files, the OG-Core units
check, the figures and the generated pages. Census-based files are rebuilt
separately: adult mortality with `scripts/build_adult_mortality.py` and child
mortality with `scripts/build_census_child_mortality.py` (both require an IPUMS
account), and the general gradient with `scripts/build_general_gradient.py`.
Brazil's adult-mortality estimates come from an earlier IBGE-based script that
is not part of the current build.

## Citation

Cite this repository together with the underlying sources:

- Fertility and child mortality: The DHS Program, ICF.
- Census-based estimates: Ruggles, S. et al., *Integrated Public Use Microdata
  Series, International*, Minneapolis, MN: IPUMS, doi:10.18128/D020.V7.7, and
  the national statistical office that conducted the census (given in the
  `source` column and on each [country page](countries/)).
- Brazil, adult mortality: IBGE, 2010 Census sample microdata.

## Limitations

- **Wealth and lifetime income.** Households are ranked by an asset index at a
  single point in time. Its use for OG-Core's lifetime-income groups assumes
  that asset rank approximates lifetime-income rank.
- **The top of the distribution.** No source distinguishes groups within the
  richest quintile, so values for a model's highest income groups are
  extrapolations.
- **Survey dates.** The latest survey is used for each country; for some
  countries it is from the 1990s. Survey years are given on the country pages.
- **Death reporting.** Census estimates depend on households reporting deaths.
  Under-reporting that is uniform across wealth groups does not affect the
  gradient; samples where it was found to vary with wealth are not published,
  but the check could not be made for every sample
  ([methods](methods/adult-mortality.md)). Deaths that dissolve a household and
  deaths in institutions are not recorded.
- **Sampling uncertainty.** No standard errors are published; each gradient is
  fitted to five or fewer group rates.
- **National income.** The general gradient is estimated on GNI in current
  dollars of the census years; applied to recent GNI without adjustment for
  price change, it predicts a somewhat steeper gradient.
- **Regional coverage of adult mortality.** The general gradient is estimated
  from African censuses and one Brazilian census; there is no Asian census
  estimate, so values for Asian countries are extrapolations.
- **Older ages.** Adult-mortality gradients weaken with age and in several
  low-income censuses become positive after age 45. Estimates for these ages
  are the least certain in the library.
- **High-income countries.** The sources are designed for low- and
  middle-income countries, and the income relationship is estimated only over
  the income range of the censuses used. It should not be extrapolated to
  high-income countries.
