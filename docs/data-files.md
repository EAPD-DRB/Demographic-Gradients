# Data files

All files in [`data/`](../data/) are CSV and are rebuilt by the scripts in
[`scripts/`](../scripts/). Terms are defined in the [glossary](glossary.md).

## Files used in a calibration

| File | Contents | Use |
|---|---|---|
| [`gradient_library_latest.csv`](../data/gradient_library_latest.csv) | Wealth gradients from the latest DHS survey, by country and indicator | `fert_gradient` (`indicator == "TFR"`); `infmort_gradient` (`"IMR"`) |
| [`fertility_age_offsets.csv`](../data/fertility_age_offsets.csv) | Age offsets for fertility, with the validation results | `fert_gradient` by age of mother |
| [`adult_mortality_gradients.csv`](../data/adult_mortality_gradients.csv) | Census estimates of adult mortality by sex and age band | `mort_gradient` (`measure == "45q15"`, `sex == "all"`, latest census) for countries with a census estimate |
| [`general_gradient.csv`](../data/general_gradient.csv) | Income relationship for adult mortality with its standard errors and prediction-interval terms, age offsets and validation statistics | `mort_gradient` for other countries |
| [`census_child_mortality.csv`](../data/census_child_mortality.csv) | Census estimates of child mortality (Brazil 1991, 2000, 2010) | child mortality where the DHS survey is old or absent |

## Common columns

| Column | Definition |
|---|---|
| `indicator` | `TFR`, `IMR`, `U5MR` (DHS); `AMR` (census adult mortality); `CHMORT_CENSUS` (census child mortality) |
| `country`, `year` | Country and year of the survey or census |
| `slope` | Wealth gradient |
| `ratio` | Low/high ratio: rate in the lowest wealth group divided by the rate in the highest |
| `q1` … `q5` | Rate in each wealth group, lowest first. Units: births per woman (TFR), deaths per 1,000 live births (IMR, U5MR), deaths per 1,000 (adult mortality: annual rate for `mx`, probability for `45q15`), proportion dead (census child mortality). Blank where a census supports fewer than five groups |

`adult_mortality_gradients.csv` also contains `sex`; `measure` (`45q15` or `mx`);
`age_lo` and `age_hi`; `n_deaths`; `ranking` (asset index); `source`; `groups`
(number of wealth groups); and `linked_share` (share of the census's death
records matched to household assets).

`census_child_mortality.csv` also contains `measure` (proportion of children
ever born who have died: `prop_dead_2529`, mothers aged 25–29, the series used;
`prop_dead_agestd`, standardized over mothers aged 20–39; `prop_dead_all`, all
mothers, for reference); `index` (`full`, all assets in the
census; `common`, assets recorded in all three censuses); `n_mothers`;
`asset_vars`; and `dhs_check` (comparison with the DHS).

## Supporting files

| File | Contents |
|---|---|
| [`gradient_library.csv`](../data/gradient_library.csv) | Wealth gradients for every DHS survey |
| [`dhs_gradients_raw.csv`](../data/dhs_gradients_raw.csv) | Quintile values as downloaded from the DHS API, including age-specific fertility rates |
| [`fertility_age_tilts.csv`](../data/fertility_age_tilts.csv) | Fertility gradient by age for each survey, from which the age offsets are computed |
| [`general_gradient_points.csv`](../data/general_gradient_points.csv) | Census observations behind the general gradient: GNI per capita, measured 45q15 gradient (`tilt_45q15`) and leave-one-out prediction |
| [`gni_census_years.csv`](../data/gni_census_years.csv) | GNI per capita (World Bank, Atlas method, current US$) for each census year, with the retrieval date; the input to the general gradient |
| [`dhs_regions.csv`](../data/dhs_regions.csv) | DHS Program region of each country |
| [`ogcore_units_check.csv`](../data/ogcore_units_check.csv) | Results of the check that determines the conversion to OG-Core units |

## Comparability

Survey estimates, census adult-mortality estimates and census child-mortality
estimates measure different quantities. Their gradients agree where they can be
compared, but their levels (`q1` … `q5`) are not comparable and should not be
pooled.
