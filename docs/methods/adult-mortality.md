# Adult mortality by wealth: the census household-deaths method

How the estimates in
[`data/adult_mortality_gradients.csv`](../../data/adult_mortality_gradients.csv)
are built. The full per-census table is in
[`docs/tables/adult_mortality.md`](../tables/adult_mortality.md); per-country
provenance is on the [country pages](../countries/); the fallback for
countries with no measurement is the
[general gradient](general-gradient.md).

## Why censuses, not surveys

Adult mortality by wealth cannot come from DHS-type surveys: the dead are not
interviewed, and sibling survival reports carry no wealth data for the
deceased's own household. It CAN come from census **household deaths modules**:
the household outlives the deceased and reports the death (age, sex, occurred
in the last 12 months) alongside its assets. Fourteen countries have usable
modules — sixteen censuses, roughly 140,000 adult (15–59) death records.
Brazil 2010 and South Africa 2001/2007/2011 establish the method; Ethiopia
2007 covers the remaining OG-family country with a census mortality module;
and Zambia, Malawi, Mozambique, Uganda, Rwanda, Senegal, Sierra Leone,
Lesotho, Benin, Sudan and South Sudan give the borrowing set its spread.

## Assets, not income

Households are ranked by an **asset index**, never post-death household
income: a death mechanically removes the deceased's earnings from post-death
income (reverse causation), while assets are shock-stable. Validated on São
Paulo, where assets gave clean monotonic gradients and income did not. Asset
components vary by census and are recorded per sample in
`scripts/build_adult_mortality.py`; a census supports however many wealth
groups its asset distribution supports (the `groups` column: three where
assets are sparse, five where they are not).

## The pipeline

Every census except Brazil is built by `scripts/build_adult_mortality.py` —
the universal IPUMS pipeline (slim extracts of ~12 variables, tens of MB per
census). Microdata stays local per the IPUMS license; the published aggregates
are explicitly permitted. Brazil comes from IBGE's own open microdata, because
IPUMS's supplementary death file for that census holds only 48% of the deaths
the census itself reports and loses them mainly in wealthy households (see
[the Brazil page](../countries/brazil.md)).

The tilt is the OLS slope of ln(rate) on wealth rank 0–1, regressed on each
group's realized population midpoint. Deaths are weighted by the supplementary
file's own weight where provided, else by the linked household's weight. Age
bands publish only above 900 death records (`MIN_BAND_DEATHS`).

## The completeness gate

**The MORTNUM check gates publication of any sample.** The supplementary
per-death file is compared, *within each wealth group*, against the same
households' own reported death counts. Even (wealth-uniform) record loss
cancels out of a tilt; wealth-skewed loss biases it. Census under-reporting
of deaths is common — capture against national death counts runs from 35%
(Benin) to over 100% where census and UN estimates disagree — and is
acceptable only when uniform across wealth.

Three samples were built, checked, and **rejected** because their loss is
wealth-skewed: the IPUMS supplement for Brazil 2010 (48% capture, skewed to
wealthy households), Nepal 2001 (biases the gradient flat) and El Salvador
2007 (biases it steep). Their configurations and the evidence stay in
`scripts/build_adult_mortality.py` — rejected, not deleted. Cambodia 2008 was
examined for an Asian observation but its death records are overwhelmingly
children, leaving every adult band below the publication minimum — which is
why the library has **no Asian adult observation at all**.

## Verification standard for any new country

1. Extract's weighted population reproduces the census total.
2. Linkage rate measured and recorded; composition check if < 1.
3. MORTNUM wealth-uniformity check passes.
4. Envelope check: weighted supplement deaths against the national death
   count; record the capture rate.
5. Tilt cross-checked against the library's existing range and any published
   national evidence.
6. The shipped script — not session code — produces the committed rows,
   byte-identically on a re-run.
7. Figures and docs regenerated, not edited.
