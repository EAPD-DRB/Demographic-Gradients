# Sources, citation and limits

## Where the data come from

**Births and infant deaths:** the [DHS Program indicator
API](https://api.dhsprogram.com), using its wealth-quintile breakdowns of total
fertility (`FE_FRTR_W_TFR`), fertility by age (`FE_FRTR_W_A15` …
`FE_FRTR_W_A45`), infant mortality (`CM_ECMR_C_IMR`) and under-five mortality
(`CM_ECMR_C_U5M`). The API is free and needs no registration. Surveys missing
any wealth fifth are dropped, never filled in.

**Adult deaths:** census microdata with a household deaths module, from
[IPUMS International](https://international.ipums.org) (free registration), and
for Brazil directly from IBGE's open 2010 census sample. Only aggregated tilts
are published here, as the IPUMS licence requires; the microdata never enter
this repository.

**National income:** World Bank GNI per capita (`NY.GNP.PCAP.CD`), free API.

**OG-Core:** the unit conversion is checked against OG-Core's own published
source code.

## Rebuilding everything

```
uv run scripts/refresh.py
```

re-downloads the survey data and rebuilds every derived file, figure and
generated page. The census estimates rebuild with
`scripts/build_adult_mortality.py`, which needs an IPUMS account.

## How to cite

Cite this repository, and credit the sources behind the numbers you use:

- **Births, infant and child deaths (surveys):** The DHS Program, ICF.
- **Adult deaths and census child deaths:** Ruggles, S. et al., *Integrated
  Public Use Microdata Series, International*, Minneapolis, MN: IPUMS,
  doi:10.18128/D020.V7.7, **and** the national statistical office that ran the
  census. The `source` column names it row by row, and each
  [country page](countries/) repeats it.
- **Brazil's adult mortality:** IBGE, Census 2010 sample microdata (not via
  IPUMS).

## What the data cannot tell you

- **Wealth is not lifetime income.** Households are ranked by assets at one
  moment. The library assumes that ranking stands in for the lifetime-income
  groups OG-Core uses.
- **The top 1% is invisible.** No source splits the richest fifth further, so
  values for a model's top income groups are extrapolated.
- **Some surveys are old.** Each country's latest survey is used, and for a
  few countries it dates from the 1990s. Check the year on the country page.
- **Adult deaths depend on households reporting them.** Under-reporting
  cancels out of a tilt only if it is the same for rich and poor; censuses that
  fail that check are not published ([method](methods/adult-mortality.md)).
- **Adult mortality has no Asian measurement.** The general gradient is fitted
  mostly on African censuses plus South Africa and Brazil, so for Asian
  countries it is an extrapolation.
- **Older-age adult values are the least certain** in the library: the
  gradient fades and can reverse after 45, partly for real reasons and partly
  because of how deaths of elderly relatives get reported.
- **High-income countries are out of scope.** Every source used here is a
  developing-country instrument, and the income rule is fitted only within the
  income range of the censuses behind it. Do not extrapolate it to rich
  countries.
