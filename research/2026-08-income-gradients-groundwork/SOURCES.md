# Source inventory: mortality & fertility by income, per country

Compiled June 2026 across four research rounds (agent-verified citations;
re-verify before formal citation). Countries: the OG-Core calibration set —
US, South Africa, Indonesia, Philippines, Ethiopia — plus cross-country
platforms. The library's own sources (DHS gradient pipeline, IPUMS census
household-deaths modules) are documented in the library itself; this inventory
records the *other* source families, most valuable now for validation, old-age
evidence, and the missing Asian adult observation.

## United States (the near-complete case)

- **Chetty et al. / Health Inequality Project, Online Table 15** — national
  mortality rates by sex × household-income percentile (1–100) × age 40–76 ×
  year. CSV: `healthinequality.org/dl/health_ineq_online_table_15.csv` (CC0).
  Caveats: income is near-peak-working household income (not lifetime
  earnings); stops at age 76. Table 16 = individual income; Tables 1–2 = life
  expectancy by percentile (validation).
- **SSA Actuarial Study No. 129** (Bosley et al.) — mortality by career-average
  (AIME) earnings level; the cleanest lifetime-income concept; PDF only.
  `ssa.gov/oact/NOTES/pdf_studies/study129.pdf`.
- **NLMS** (National Longitudinal Mortality Study) — public-use file, all ages,
  income/education from CPS linkage. **NCHS NHIS-LMF** — poverty-income-ratio
  gradient, nonlinear with inflection near PIR 3.5.
- Fertility: **ACS PUMS / IPUMS `FERTYR`** × age × household income
  (single-year ages, very large sample); NCHS ASFR by education.

## South Africa (best-instrumented of the developing four)

- **Agincourt HDSS / Kabudula et al. 2017**, *Lancet Glob Health* 5(9):e924
  (PMC5559644) — 45q15, birth-to-5, e0 by asset-wealth quintile, 2001–13;
  RII by age band & period (child 2.06→2.38 exceeds adult ~1.3–1.8; ART-era
  narrowing). Rural, high-HIV: export the relative gradient, not the level.
- **SAPRIN** — pooled Agincourt+AHRI+DIMAMO HDSS, all ages, cohort profile
  *IJE* 51(4):e206 (PMC9365637); microdata via DataFirst (UCT).
- **HAALSI** (Agincourt, 40+, HRS-harmonized) — ICPSR/NACDA 36633; best
  old-age × SES source. **WHO SAGE-SA** (50+, verbal-autopsy follow-up).
- **Bor et al.** (~PMC6077134) — municipality income-decile gradient by age;
  attenuates/vanishes at 60+ (esp. women), HIV-era-dependent.
- **NIDS** (SALDRU) — national panel, true income + mortality follow-up.
- National: SAMRC SANBD2 (population group as SES proxy), Stats SA P0309.3,
  Thembisa. Fertility: SADHS 2016 IR file; **Stats SA Census 2011 fertility
  report 03-01-63 Table 15** = ASFR × age × population group (turnkey
  age × SES fertility matrix; clear left-shift for lower SES).

## Indonesia

- **IFLS / Sudharsanan 2019**, *J Gerontol B* 74(3):484 (PMC6377031) — period
  life tables from age 30 by consumption/wealth quartile: men +3.4 (urban) /
  +3.8 (rural) years e30, women's gradient flat/absent; credible to ~age 70–75.
- **Purworejo SAGE HDSS** (PMC3327655) — 60–80+ mortality by education & wealth
  quintile, single rural district; graft for old age.
- **ILAS 2023** (SurveyMETER/ADB, 45+) — future source; baseline only so far.
- Fertility: IDHS 2017 IR file; IFLS ASFR × consumption quartile; BPS
  TFR-by-expenditure-quintile. Key fact: TFR-by-wealth nearly flat (2.9→2.1)
  while teen-childbearing gradient is ~8× — the tempo-dominated case.

## Philippines

- **LSAHP** (DRDF/UPPI, 60+) — Waves 1 (2018–19, n=5,985) → 2 (2023, 1,579
  deaths with informant interviews); mortality-by-wealth-quintile Cox model
  published (Paguirigan 2025). Only direct old-age × SES source; W2 mortality
  microdata may require a direct DRDF request.
- Working age: **no direct source** (the biggest hole in the four-country
  matrix). Bridges: PSA regional life tables ranked by regional poverty
  (area-SES; Abalos & Booth 2020); orphanhood method on census by
  region/education; PURE SE-Asia education RR (has a PH arm). PHL is *not* in
  GBD's subnational program.
- Fertility: NDHS 2022 IR file (TFR 3.1→1.4 by quintile; teen gradient ~5.6×).

## Ethiopia (weakest — gradient only)

- **Butajira HDSS** (PMC2519081; 2008–2019 update PMC9542780) — adult 15–64
  mortality by economic proxies: no-literacy MRR 2.38, non-house-ownership
  1.77, economic-status OR ~1.9–3.4. One district; proxies, not income.
- **Mekonnen et al. 2013**, *Int J Equity Health* (PMC3716728) — national
  wealth-quintile life tables (e0 53.4→62.5, ~9-yr gap) **but the adult
  gradient is modeled from the child differential, not observed**.
- Kilte Awlaelo HDSS (wealth index; weak/NS at old age). LSMS-ISA ESS death
  roster (microdata.worldbank.org/3823) — small-sample supplement.
- Fertility: **use EDHS 2016** (the 2019 EMDHS has no fertility module).
  TFR 6.4→2.6 by quintile — steepest of the four.

## Cross-country platforms & methods

- **DHS Program** — child mortality by wealth quintile (all four) via the API
  (`api.dhsprogram.com`, indicators `CM_ECMR_C_*`; the *website* blocks
  scripts). Fertility: ASFR × quintile computable from IR files
  (`DHS.rates::fert(IRdata, Indicator="asfr", Class="v190")`).
- **GBD/IHME** — does *not* stratify mortality by income within a country
  (SDI is between-country only). Gives subnational life tables (IDN provinces,
  ETH regions, ZAF provinces; not PHL) = geographic proxy, and the 5–14 age
  bands no survey covers.
- **Education–mortality meta-analysis**, *Lancet Public Health* 2024
  (PMC10901745) — 603 studies/59 countries; −1.9%/yr of schooling,
  age-stratified (−2.9%/yr at 18–49 → −0.8%/yr at 70+). The country-neutral
  RR backbone; only 0.6% of observations from sub-Saharan Africa.
- **INDEPTH 7-HDSS pooled** (PMC6534200, incl. ETH Harar/Kersa) — all-cause
  RR 1.42–2.06 poorest-vs-richest, LE gaps 6.4–15.6 yr, gradient larger <15
  than >40. **ALPHA Network** (ZAF ×2 sites; HIV-focused, SES harmonization
  weak). **Gateway to Global Aging** (g2aging.org) — the HRS-family index
  (HAALSI, LASI, SAGE, LSAHP-adjacent).
- **Register countries** (Norway Kinge 2019 JAMA; Finland; Canada CanCHEC
  table 13-10-0759-01; US NLMS) — the only native all-age income × mortality
  data; high-income single-hump age shape, so use for *method*, not as an
  LMIC donor shape. HMD has no income axis.
- **National life tables**: UN WPP 2024 via the `PPgp/wpp2024` R package
  (`mx5dt$mxB`; the WPP portal `/data/` API now requires a Bearer token and
  returns 401 to anonymous calls). Cross-check: WHO GHO OData
  `LIFE_0000000029` (nMx) / `LIFE_0000000030` (nqx) — 2021 values carry the
  COVID peak, 15–30% above WPP 2020–25 at adult ages.

## The two structural findings

1. **Mortality:** the LMIC gradient across age is double-peaked — steep child
   spike (poorest:richest U5MR 1.6–4.4× in the four; the 1–4 band steeper
   still), a young-adult hump where HIV/TB/injury/maternal deaths concentrate
   (dominant in ZAF), shallow 5–15, compressing toward 1 at old age. A
   Nordic/US donor shape (single mid-life hump) misplaces the steepness.
   Old-age behavior is the least-observed, highest-leverage assumption
   everywhere — keep it an explicit, sensitivity-tested switch.
2. **Fertility:** the income difference is an age-tilt (poor concentrate
   childbearing at 15–24; rich delay), driven by marriage age and contraceptive
   onset. Scaling a national ASFR by a TFR ratio erases the signal; tilt the
   age schedule by income group.
