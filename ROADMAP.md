# Roadmap

Open work and items awaiting a ruling. Finished work, rulings and changes to
published values are in [CHANGELOG.md](CHANGELOG.md); method rulings are also
recorded in [AGENTS.md](AGENTS.md#method-rulings-validated--dont-relitigate-without-new-evidence).
The roadmap as it stood before 2026-11-16, with the detail of every finished
item, is in the git history.

Status: `[ ]` open · `[R]` awaiting Marcelo's ruling

## Awaiting a ruling

- [R] **Brazil `infmort_gradient`.** The country page uses the 2010 census
  child-mortality gradient, an under-five-type measure that probably
  overstates the infant gradient. The alternative is the 1996 DHS infant
  gradient. Both are shown on the page; choose one as the default.
- [R] **Updating an old estimate over time.** OG-ETH adds the income rule's
  change since the census year to its measured gradient, then moves it along
  the model's growth path. OG-PHL uses the rule's level directly. *Validate
  before ruling:* backtest on the within-country series (South Africa
  2001 → 2007; India 1999 → 2015 → 2020), predicting the later gradient from
  the earlier one plus the rule's change.

## Open

- [ ] **`imm_pctiles`.** The lifetime-income distribution of new immigrants,
  OG-Core's fourth demographic input, is not provided. Scope before building
  (IPUMS censuses record immigrant status alongside assets).
- [ ] **Compare with Marcelo's improved wealth index** (Wittenberg and
  Leibbrandt 2015 and related materials, in `~/Downloads/Inequality`; move
  them into a readable folder first) and decide which index to use.
- [ ] **Sources not yet examined:**
  - Bangladesh BMMS 2010 (same design as 2016): does the flat adult-mortality
    gradient repeat?
  - DHS household-death modules in Africa (only Asia and Latin America have
    been scanned).
  - MICS surveys after the World Bank's 2022 compilation, which would have to
    be read from the survey reports.
  - The MICS child-mortality method of Guinea-Bissau 2010, Myanmar 2009–10
    and Sudan 2006 (reports not found; excluded meanwhile).
- [ ] **Documentation review of 2026-11-16:** remaining items in
  `REVIEW-2026-11-16.md` (stale statements, glossary gaps). Delete that file
  when they are done.

## Downstream: other repositories

These models use the library and need updating after the changes of
2026-11-16 (see the changelog).

| Model | Status |
|---|---|
| OG-ETH | In production. Passes plain gradient / 100, one TFR gradient at every age and none at ages 45+, uses the under-five gradient at ages 1–4, and hard-codes an income rule on GNI. Needs: the conversion ÷ 100 (1 − p), fertility offsets, the mortality-by-age recipe, and the current rule read from `data/general_gradient.csv` |
| OG-PHL | Gradient work on branch `calib/multi-industry-remittances`, not pushed; same updates as OG-ETH |
| OG-ZAF | Passes no gradients, though South Africa has the library's best-measured estimates |
| OG-IDN, OG-BRA | No gradients |
