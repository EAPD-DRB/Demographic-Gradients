# Glossary

Every term and abbreviation used in this library, in plain language.

## The core ideas

### Gradient
How a rate (births, infant deaths, adult deaths) changes from poor to rich
households. A *steep* gradient means the poor and rich differ a lot; a *flat*
one means they barely differ.

### Tilt
The library's one-number summary of a gradient: the slope of the log of the
rate across households ranked from poorest (0) to richest (1). **Negative
means the poor have the higher rate**, which is the usual case. Because it is
a slope on a log scale, a tilt works the same way whatever the level of the
rate, so tilts can be compared across countries and years. In the data files
it is the `slope` column.

### Poorest ÷ richest tenth
The tilt turned into a ratio anyone can read: the poorest tenth of households'
rate divided by the richest tenth's, which is e^(−0.8 × tilt). A tilt of −0.79
is about 1.9×, meaning the poorest tenth has almost twice the richest tenth's
rate. 1× means no difference. The figures use this ratio; the `ratio` column in
the data files holds it too.

### Wealth fifths (quintiles)
Households ranked by wealth and split into five equal groups, from the poorest
fifth (Q1) to the richest fifth (Q5). Surveys publish rates for each fifth; the
`q1` … `q5` columns hold them. Some censuses support only three or four groups
(`groups` column).

### Asset index
How "wealth" is measured. Neither surveys nor censuses ask reliably about
income, so households are ranked by what they own and how they live: a
fridge, a car, electricity, the floor, the toilet. Assets are also more stable
than income: a death in the family can change a household's income, but
rarely its assets.

### Age offsets
Numbers added to a country's fertility tilt to get the tilt at each age of
mother. They exist because the fertility gap is mostly about timing: poorer
women have children younger. See [fertility by age](methods/fertility-by-age.md).

### General gradient
The library's rule for adult mortality in a country with no census
measurement: a formula that predicts the tilt from national income per person.
See [the general gradient](methods/general-gradient.md).

## Measures

### TFR — total fertility rate
The number of children a woman would have over her life at current rates.
"Births per woman."

### ASFR — age-specific fertility rate
Births per 1,000 women in a five-year age group (15–19, 20–24, ...). Five times
the sum of the ASFRs is the TFR.

### IMR — infant mortality rate
Deaths before age one per 1,000 live births. Feeds `infmort_gradient`.

### U5MR — under-five mortality rate
Deaths before age five per 1,000 live births. Kept only as a fallback for
surveys without an infant figure: its gradient is steeper than the infant
one, so it is not a substitute.

### 45q15 — adult mortality
The chance that someone who reaches 15 dies before 60. The library's summary
of adult mortality, and the basis of `mort_gradient`.

### mx — age-specific death rate
Deaths per person per year within an age band (15–29, 30–44, ...). The library
publishes adult tilts by band as well as for 45q15.

## Sources

### DHS — Demographic and Health Surveys
Large household surveys run in developing countries, with funding from USAID,
since the 1980s. They publish fertility and child mortality by wealth fifth,
which is where the library's birth and infant figures come from.

### Census household deaths module
A set of questions in some censuses asking each household about deaths in the
past year. It is the only large source of adult deaths matched to household
wealth, because household surveys interview the living.

### IPUMS International
A University of Minnesota project that harmonizes census microdata from
national statistical offices. Most of the library's census samples come
through it; Brazil's come directly from IBGE, Brazil's statistical office.

### GNI per capita
Gross national income per person, in current US dollars (World Bank). The
general gradient uses it to predict adult-mortality tilts.

## OG-Core terms

### OG-Core
An open-source overlapping-generations economic model. Country versions
(OG-ZAF, OG-PHL, ...) simulate how policies affect households of different
ages and lifetime incomes.

### Lifetime-income groups (`lambdas`)
The income groups an OG-Core model splits each age into. The library's tilts
work for any choice of groups; OG-Core places each group on the wealth ranking
itself.

### `fert_gradient`, `infmort_gradient`, `mort_gradient`, `imm_pctiles`
The four arguments of OG-Core's `get_pop_objs` that let demographics differ by
income group. The library supplies the first three; it has nothing for
`imm_pctiles`, the income distribution of new immigrants.

### Converting a tilt for OG-Core
OG-Core reads a slightly different quantity from the tilt, so each tilt is
passed as `tilt / (100 × (1 − p))`, with p OG-Core's own rate at that age. See
[passing a tilt to OG-Core](methods/ogcore-units.md).
