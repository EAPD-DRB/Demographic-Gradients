# Data files

Everything in [`data/`](../data/), what it holds, and which file to use. All
files are CSV and are rebuilt by the scripts in [`scripts/`](../scripts/). Terms
are explained in the [glossary](glossary.md).

## The files a calibration uses

| File | Holds | Use it for |
|---|---|---|
| [`gradient_library_latest.csv`](../data/gradient_library_latest.csv) | One row per country and measure: the tilt from the latest DHS survey | `fert_gradient` (`indicator == "TFR"`), `infmort_gradient` (`"IMR"`; `"U5MR"` only if no IMR) |
| [`fertility_age_offsets.csv`](../data/fertility_age_offsets.csv) | Seven age offsets to add to a fertility tilt, with the checks behind them | spreading `fert_gradient` by age |
| [`adult_mortality_gradients.csv`](../data/adult_mortality_gradients.csv) | Adult-mortality tilts from censuses, by sex and age band | `mort_gradient` (`measure == "45q15"`) where the country has a census |
| [`general_gradient.csv`](../data/general_gradient.csv) | The rule that predicts the adult tilt from national income, its age offsets and its validation | `mort_gradient` for every other country |
| [`census_child_mortality.csv`](../data/census_child_mortality.csv) | Child-mortality tilts from censuses (Brazil 1991, 2000, 2010) | the child gradient where the survey is old or missing |

## Columns shared by the gradient files

| Column | Meaning |
|---|---|
| `indicator` | The measure: `TFR`, `IMR`, `U5MR` (surveys), `AMR` (adult mortality), `CHMORT_CENSUS` (census child mortality) |
| `country`, `year` | Country and the survey's or census's year |
| `slope` | **The tilt** — the number a calibration uses |
| `ratio` | The measured ratio: the poorest group's rate over the richest group's (`q1` over the last group). Noisier than the fitted [poorest-to-richest ratio](glossary.md#poorest-to-richest-ratio) the docs use |
| `q1` … `q5` | The rate in each wealth fifth, poorest first. Units differ by file: births per woman, deaths per 1,000 births, annual death rates. Blank where a census supports fewer groups |

Extra columns in `adult_mortality_gradients.csv`: `sex`; `measure` (`45q15`
for ages 15–60, `mx` for an age band); `age_lo`, `age_hi`; `n_deaths`;
`ranking` (always the asset index); `source`; `groups` (wealth groups the census
supports); `linked_share` (share of deaths matched to a household's assets —
below 1, the levels are not meaningful but the tilt is).

Extra columns in `census_child_mortality.csv`: `measure` (share of children
who died, mothers aged 25–29); `index` (`full` uses every asset the census
offers; `common` uses only those every census offers — use `full`);
`n_mothers`; `asset_vars`; `dhs_check` (cross-check against a survey).

## Supporting files

| File | Holds |
|---|---|
| [`gradient_library.csv`](../data/gradient_library.csv) | Every survey, not just the latest: the history behind `gradient_library_latest.csv` |
| [`dhs_gradients_raw.csv`](../data/dhs_gradients_raw.csv) | The raw quintile values downloaded from the DHS API, including fertility by age |
| [`fertility_age_tilts.csv`](../data/fertility_age_tilts.csv) | Each survey's fertility tilt at each age, from which the offsets are built. Supporting data: the pooled offsets are as accurate overall and have no gaps at the oldest ages |
| [`general_gradient_points.csv`](../data/general_gradient_points.csv) | Each census behind the general gradient: income, measured tilt and the rule's out-of-sample prediction |
| [`dhs_regions.csv`](../data/dhs_regions.csv) | The DHS Program's region for each country, for borrowing a regional median |
| [`ogcore_units_check.csv`](../data/ogcore_units_check.csv) | The check that sets how a tilt is converted for OG-Core ([explained](methods/ogcore-units.md)) |

## Do not mix

The survey files, the census adult file and the census child file measure
different things. Their tilts agree where tested, but their `q1` … `q5`
levels are not comparable, so never pool them.
