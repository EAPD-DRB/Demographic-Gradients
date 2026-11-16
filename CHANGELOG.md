# Changelog

Changes to published values, methods and rulings, newest first, so that models
using the library know what to update. Current values are always in
[`data/`](data/) and the generated pages; numbers below are as of each date.
The commit history has the full detail.

## 2026-11-16

**Downstream models must update.** The general gradient, the age offsets and
every adult-mortality estimate changed, and `mort_gradient` now has a full
recipe by age. Models that hard-code the rule's coefficients (OG-ETH, OG-PHL)
should read `data/general_gradient.csv` instead, and follow the
[calibration guide](docs/calibration-guide.md).

Methods:
- **Adult-mortality gradient on the death-rate scale.** The 45q15 gradient is
  fitted to −ln(1 − 45q15), the cumulative death rate at 15–59, instead of
  ln(45q15), which understated the gradient where adult mortality is high.
  South Africa 2007 −1.23 → −1.77, Lesotho 2006 −0.36 → −0.73; low-mortality
  countries changed by less than 0.1. The 45q15 levels are unchanged.
- **`mort_gradient` by age:**

  | Ages | Gradient |
  |---|---|
  | 1–4 | the country's child-mortality (4q1) gradient, else under-five + the pooled offset |
  | 5–14 | the 15–29 value |
  | 15–59 | the 45q15 gradient + the band offsets |
  | 60–74 | tapered from the 45–59 value to 0 at age 75 |
  | 75 and over, and the final age | 0 |

  Shown on every country page.
- **Wealth groups** are cut at the boundary between tied scores nearest each
  quintile. Seven censuses gained a group; gradients moved by less than their
  standard errors. Each group's population share is published (`share1`–`share5`).
- **Standard errors** (`se`) for every adult-mortality estimate: cluster
  bootstrap for surveys, Poisson approximation for censuses.

Data:
- Added Colombia 2018 (DANE census), Bangladesh 2016 (BMMS survey) and
  Cambodia 2008 (census, held since 11 November), the first Southeast Asian
  estimate.
- Withdrew Malawi 1998: its three asset items do not rank Malawian households
  by wealth (on the same items, Malawi 2008's gradient turns from −0.60 to
  +0.41).
- Added child mortality at ages 1–4 by wealth (DHS, 74 countries) and the
  pooled offset to the under-five gradient (`child_mortality_offset.csv`).
- Brazil's census child-mortality estimates were rebuilt with the wealth-group
  fix of 13 November, which had not been applied to them: 1991 −1.69 → −1.81.
- Each country's latest GDP per capita is pinned (`income_latest.csv`).
  Country pages now show the general gradient's value with its prediction
  interval, or say that the income lies outside the rule's range.
- Not usable after review: Indonesia's IFLS (cross-check only); census
  household death counts without ages, through an all-ages translation (no
  better than the income rule).

General gradient: 2.975 − 0.432 × ln(GDP per capita, PPP), 19 observations;
residual standard error 0.32. Philippines −1.04, Indonesia −1.19 at 2025
income.

Documentation: a generated [calibration guide](docs/calibration-guide.md)
replaces the user half of AGENTS.md; files, scripts and figures are listed in
[docs/files.md](docs/files.md); this changelog replaces the history in
ROADMAP.md.

## 2026-11-13

- **General gradient on GDP per capita at purchasing-power parity** (constant
  2021 international $), replacing GNI in current US dollars, which mixed
  price levels of different years. 2.610 − 0.378 × ln(GDP per capita, PPP);
  Philippines −0.88, Indonesia −1.01. Models projecting the rule on GNI
  growth must switch income series.
- **MICS surveys added** as a second source for fertility and infant
  mortality (TFR 77 → 96 countries, IMR 78 → 88), with a `source` column.
  Mortality only from direct (birth-history) estimates. Seven fertility sets
  that the World Bank compilation mislabels were replaced by values from the
  survey reports.
- **Wealth-group cut at the maximum score kept**, which had merged a real top
  group; only Malawi 1998 moved among published estimates.
- Nine further census death files screened; none passes the checks.

## 2026-11-12

- **Census wealth index rebuilt on principal components**, replacing an
  additive count with coding errors. General-gradient slope −0.244 → −0.302;
  South Africa's latest estimate becomes 2007 (2011 withdrawn); Ethiopia
  +0.09 → +0.01.
- **India's NFHS surveys** (1999, 2015, 2020) added for adult mortality, the
  first Asian estimates, and included in the income rule.
- The income rule is reported with standard errors and prediction intervals.

## 2026-11-05 to 2026-11-11

- **Conversion to OG-Core units:** pass gradient / (100 × (1 − p)), verified
  against OG-Core's own functions. Plain gradient / 100 understates slopes by
  1–11 percent.
- **Fertility by age:** the TFR gradient plus pooled age offsets.
- Documentation rewritten in statistical-publication style; country pages,
  glossary and methodology added. DHS refresh adds Kenya 2025; Rwanda's 2025
  DHS replaces its 2019–20 rows (its quintile cells are noisy).

## July–August 2026

- The library is first published: DHS wealth gradients for fertility and
  infant mortality, and adult mortality from census household-death records
  (Brazil, South Africa, Ethiopia and comparator countries).
- A general adult-mortality gradient is added as the fallback for countries
  without their own estimate.
- DHS sibling histories are tested for adult mortality and rejected.
- Census child mortality for Brazil is added.
