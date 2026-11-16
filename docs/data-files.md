# Data files

All files in [`data/`](../data/) are CSV and are rebuilt by the scripts in
[`scripts/`](../scripts/). Terms are defined in the [glossary](glossary.md).

## Files used in a calibration

| File | Contents | Use |
|---|---|---|
| [`gradient_library_latest.csv`](../data/gradient_library_latest.csv) | Wealth gradients from the latest DHS or MICS survey, by country and indicator | `fert_gradient` (`indicator == "TFR"`); `infmort_gradient` (`"IMR"`) |
| [`fertility_age_offsets.csv`](../data/fertility_age_offsets.csv) | Age offsets for fertility, with the validation results | `fert_gradient` by age of mother |
| [`adult_mortality_gradients.csv`](../data/adult_mortality_gradients.csv) | Census and survey estimates of adult mortality by sex and age band | `mort_gradient` (`measure == "45q15"`, `sex == "all"`, latest year) for countries with their own estimate |
| [`general_gradient.csv`](../data/general_gradient.csv) | Income relationship for adult mortality with its standard errors and prediction-interval terms, age offsets and validation statistics | `mort_gradient` for other countries |
| [`census_child_mortality.csv`](../data/census_child_mortality.csv) | Census estimates of child mortality (Brazil 1991, 2000, 2010) | child mortality where the DHS survey is old or absent |

## Common columns

| Column | Definition |
|---|---|
| `indicator` | `TFR`, `IMR`, `U5MR` (DHS and MICS surveys); `AMR` (adult mortality from household-death records); `CHMORT_CENSUS` (census child mortality) |
| `country`, `year` | Country and year of the survey or census |
| `slope` | Wealth gradient |
| `ratio` | Low/high ratio: rate in the lowest wealth group divided by the rate in the highest |
| `q1` … `q5` | Rate in each wealth group, lowest first. Units: births per woman (TFR), deaths per 1,000 live births (IMR, U5MR), deaths per 1,000 (adult mortality: annual rate for `mx`, probability for `45q15`), proportion dead (census child mortality). Blank where a census supports fewer than five groups |

`gradient_library*.csv` also contain `source` (`DHS` or `MICS`).

`adult_mortality_gradients.csv` also contains `sex`; `measure` (`45q15` or `mx`);
`age_lo` and `age_hi`; `n_deaths`; `ranking` (`asset_index` for censuses,
`dhs_wealth_index` for DHS surveys, `survey_wealth_index` for Bangladesh's
BMMS, ranked by the survey's own wealth quintiles); `source` (the census or
survey); `groups` (number of wealth groups); and
`linked_share` (share of the census's death records matched to household
assets; 1 for surveys).

`census_child_mortality.csv` also contains `measure` (proportion of children
ever born who have died: `prop_dead_2529`, mothers aged 25–29, the series used;
`prop_dead_agestd`, standardized over mothers aged 20–39; `prop_dead_all`, all
mothers, for reference); `index` (`full`, all assets in the
census; `common`, assets recorded in all three censuses); `n_mothers`;
`asset_vars`; and `dhs_check` (comparison with the DHS).

## Supporting files

| File | Contents |
|---|---|
| [`gradient_library.csv`](../data/gradient_library.csv) | Wealth gradients for every DHS and MICS survey |
| [`dhs_gradients_raw.csv`](../data/dhs_gradients_raw.csv) | Quintile values as downloaded from the DHS API, including age-specific fertility rates |
| [`fertility_age_tilts.csv`](../data/fertility_age_tilts.csv) | Fertility gradient by age for each survey, from which the age offsets are computed |
| [`general_gradient_points.csv`](../data/general_gradient_points.csv) | Census and survey observations behind the general gradient: UN subregion (`region`), GDP per capita PPP (`gdp_ppp`, the rule's income) and GNI per capita (`gni_atlas`, reference), measured 45q15 gradient (`tilt_45q15`) and leave-one-out prediction |
| [`income_census_years.csv`](../data/income_census_years.csv) | For each census or survey year: GDP per capita, PPP, constant 2021 international $ (`gdp_ppp`, the input to the general gradient) and GNI per capita, Atlas method, current US$ (`gni_atlas`, reference), each with its retrieval date |
| [`mics_quintiles_raw.csv`](../data/mics_quintiles_raw.csv) | MICS quintile values as downloaded from the World Bank's compilation, with the footnote naming the survey, the income group in the survey year and the national TFR |
| [`mics_methods_unicef.csv`](../data/mics_methods_unicef.csv) | UNICEF's classification of each MICS survey's child-mortality estimates: `FBH` (direct, full birth history) or `SBH` (indirect) |
| [`mics_surveys.csv`](../data/mics_surveys.csv) | Each MICS survey, its mortality method, and what is used from it or why it is excluded |
| [`mics_tfr_from_reports.csv`](../data/mics_tfr_from_reports.csv) | Total fertility rate by quintile transcribed from the MICS report (table and page) for surveys whose compiled value is the adolescent birth rate |
| [`mics_methods_reports.csv`](../data/mics_methods_reports.csv) | Child-mortality method from the MICS report, for surveys UNICEF does not classify |
| [`dhs_regions.csv`](../data/dhs_regions.csv) | DHS Program region of each country; countries surveyed only by MICS are assigned to a region (`classification == "assigned"`) |
| [`ogcore_units_check.csv`](../data/ogcore_units_check.csv) | Results of the check that determines the conversion to OG-Core units |

## Comparability

DHS and MICS indicator estimates, adult-mortality estimates from household-death
records and census child-mortality estimates measure different quantities. Their gradients agree where they can be
compared, but their levels (`q1` … `q5`) are not comparable and should not be
pooled.
