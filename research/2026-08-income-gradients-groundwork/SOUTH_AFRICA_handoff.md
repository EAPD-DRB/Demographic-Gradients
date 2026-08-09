# South Africa — income-differentiated mortality data & method (handoff brief)

> Written 2026-08 before the Demographic-Gradients library existed. The
> library's own ZAF census rows (2001/2007/2011) and AGENTS.md precedence rules
> now take priority for calibration; this brief remains useful for its
> Agincourt/HAALSI/SAPRIN/cohort sourcing, the HIV-era caveats, and the
> validation targets.

## Goal & context
Building mortality rates that vary by income group for an OG-Core–family model
(OG-ZAF). OG-Core has `J` lifetime-income groups (default 7), each a fixed
population share `lambdas[j]`. Mortality is age-specific survival `rho`; the
pre-0.18 default came from UN World Population Prospects and was **identical
across income groups**. Target: an age × income-group mortality schedule
`m[age, j]` (equivalently `rho[age,j] ≈ 1 − exp(−m)`), constructed so the
income-weighted average reproduces the national schedule at every age.

**Recommended construction (validated):** keep national `nMx(age)` as the
level; multiply by an adjustment factor `φ(age, q) = m_q / m_national` modelled
log-linear in income rank; normalize `φ` so the share-weighted mean = 1 at each
age → the all-income aggregate reproduces national mortality **exactly**
(verified to ~1e-16 under fixed shares; under survivor-weighting it dips ~1%
below national at ages 40–85 due to mortality selection — only matters if group
shares drift with age, which they don't in fixed-`lambdas` OG-Core).

South Africa is the **best-instrumented of the developing OG countries** for
this — a directly-observed age × wealth-quintile mortality table (Agincourt),
HRS-harmonized aging cohorts, and a national HDSS network.

## 1. National mortality level (the schedule to adjust)

**UN WPP 2024, both sexes, period 2020–2025** (matches OG-Core's own source).
South Africa national e0 = **64.9 yr**.

**Access gotcha:** the WPP Data Portal `/data/` API now returns HTTP 401 (needs
a Bearer token). Get `nMx` from the official **`PPgp/wpp2024` R package**,
dataset `mx5dt$mxB`, location code **710**
(`raw.githubusercontent.com/PPgp/wpp2024/main/data/mx5dt.rda`). Cross-check:
**WHO GHO OData** `https://ghoapi.azureedge.net/api/LIFE_0000000029` (nMx) and
`.../LIFE_0000000030` (nqx), year 2021 — but WHO 2021 captures the COVID peak
(e0 61.5) and runs 15–30% above WPP at adult ages.

National `nMx` by abridged age group (per person-year):

| age | nMx | age | nMx | age | nMx |
|---|---|---|---|---|---|
| <1 | 0.026723 | 30–34 | 0.005081 | 65–69 | 0.037619 |
| 1–4 | 0.002318 | 35–39 | 0.006267 | 70–74 | 0.051479 |
| 5–9 | 0.000531 | 40–44 | 0.007916 | 75–79 | 0.071015 |
| 10–14 | 0.000601 | 45–49 | 0.010440 | 80–84 | 0.096530 |
| 15–19 | 0.001435 | 50–54 | 0.013911 | 85–89 | 0.132927 |
| 20–24 | 0.002616 | 55–59 | 0.019477 | 90–94 | 0.183462 |
| 25–29 | 0.003886 | 60–64 | 0.026810 | 95–99 | 0.250343 |
| | | | | 100+ | 0.339950 |

## 2. Child mortality by income (ages 0–5) — directly observed

**SADHS 2016** (NDoH / Stats SA / SAMRC + ICF), via the **DHS API** (the API,
not the website which blocks scripts):
`https://api.dhsprogram.com/rest/dhs/data?countryIds=ZA&indicatorIds=CM_ECMR_C_NNR,CM_ECMR_C_IMR,CM_ECMR_C_CMR,CM_ECMR_C_U5M&surveyYear=2016&breakdown=all&f=html`
(filter to wealth quintile).

Rates per 1,000, by wealth quintile (Q1 poorest → Q5 richest):

| metric | Q1 | Q2 | Q3 | Q4 | Q5 |
|---|---|---|---|---|---|
| neonatal | 31 | 31 | 21 | 17 | 29 |
| infant (1q0) | 54 | 44 | 46 | 27 | 40 |
| child (4q1) | 14 | 9 | 6 | 8 | 2 |
| under-5 (5q0) | 67 | 52 | 51 | 34 | 41 |

**⚠ Noisy and non-monotonic** (small death counts — e.g. Q5 neonatal 29 > Q4's
17). Do **not** map cells literally. Fit a smooth (log-linear) gradient or
collapse to 3 bins. A log-linear fit gives poorest:richest ≈ **1.55× (infant)**
and **~5× (child 1–4)** — the 1–5 band carries the steepest relative gradient.
Use DHS for the *shape*; take the *level* from the national `nMx` above.

## 3. Adult & old-age mortality by income — South Africa's strength

### PRIMARY: Agincourt HDSS / Kabudula et al. 2017
*Lancet Global Health* 5(9):e924, DOI 10.1016/S2214-109X(17)30297-8,
**PMC5559644**. Rural Mpumalanga, 2001–2013, ~1.06M person-years, SES =
household-asset wealth quintiles (PCA). **Directly computes 45q15, birth-to-5,
and e0 by wealth quintile.** ~**12-year** richest–poorest e0 gap.

Relative Index of Inequality (poorest:richest) by age band & period — the
**child gradient exceeds the adult gradient**, and the gradient is
**time-dependent** (HIV/ART era):

| period | children <5 | women 15+ | men 15+ |
|---|---|---|---|
| 2001–03 | 2.06 | 1.81 | 1.54 |
| 2004–07 | 1.37 | 1.55 | 1.33 |
| 2008–10 | 1.62 | 1.39 | 1.43 |
| 2011–13 (ART era) | 2.38 | 1.29 | 1.38 |

`45q15` by wealth quintile (×1000): women Q1 ~360 → Q5 ~124 (2001–03),
narrowing to Q1 ~326 vs Q5 ~265 by 2011–13; men comparable. Asset-wealth
mortality HR at 50+ ≈ **1.71**.
**⚠ Agincourt is rural and high-HIV — its mortality *level* is well above
national.** Export the *relative* gradient (RII/HR), recalibrate the level to
national (WPP / Stats SA / Thembisa).

### SECONDARY / corroborating
- **SAPRIN** — pooled Agincourt + AHRI + DIMAMO HDSS, all ages, same
  asset-quintile design, fresher than 2013. Cohort profile: *IJE* 51(4):e206,
  **PMC9365637**. Microdata via **DataFirst (UCT)**.
- **HAALSI** — Agincourt, adults **40+**, HRS-harmonized, prospective mortality
  + wealth/education/consumption. **Best old-age × SES source.** ICPSR/NACDA
  **36633**; haalsi.org.
- **WHO SAGE — South Africa**, adults **50+**, longitudinal, verbal-autopsy
  mortality linkable to baseline wealth/education.
- **AHRI** (KwaZulu-Natal HDSS) — HIV + mortality + SES.
- **Bor et al.** — national municipality income-decile mortality by age band;
  gradient **attenuates and largely vanishes at 60+ (especially women)**,
  HIV-era-dependent (verify cite, ~PMC6077134).
- **NIDS** (SALDRU) — national panel, true income + mortality follow-up.
- **SAMRC Burden of Disease Research Unit** — SANBD2 uses population group
  (race) as a coarse national SES proxy. **Stats SA** Census + P0309.3;
  **GBD subnational** (provinces); **Thembisa** (thembisa.org) and ASSA.

## 4. South-Africa-specific modeling notes (important)
- **HIV/TB drives the gradient and makes it double-peaked and time-dependent.**
  Steep early-childhood spike + strong young-adult (≈25–45) elevation; SA male
  modal age-at-death collapsed to **40–44** at the AIDS peak. Much steeper
  pre-ART than post-ART (see RII table). **Pick the calibration period
  deliberately** — use the ART-era/latest gradient for a current model.
- **Old-age compression:** the relative gradient weakens at 60+ and is near-1
  for elderly women. Taper `φ` toward 1.0 at old age — don't hold the
  working-age gradient flat. Highest-leverage assumption; run sensitivity.
- **Population group (race) is a strong, widely-available income proxy in SA**
  (Census, vital stats, SANBD2) — practical alternate SES axis and cross-check.
- **Sexes differ sharply** (men steeper; HIV hump differs by sex). If the model
  is both-sexes, blend with national sex shares and document it.

## 5. First-pass schedule built in `scripts/build_schedules.py`
Child gradient fitted to the SADHS quintile rates (infant 1.55×, child 4.97×);
adult `R(age)` (poorest:richest) = 1.55 at 15–29, **1.72 at 30–34 (HIV hump)**,
1.55 at 35–49, 1.60 at 50–64, 1.45 at 65+, tapering to 1.0 by ~90; 5–15
interpolated. Implied e0 by quintile: **Q1 61.2 → Q5 68.6 (gap 7.5 yr)** —
below Agincourt's ~12 yr because Agincourt is rural/high-HIV on a higher
mortality level; ~7–8 yr is a reasonable **national** both-sexes gap. The
anchors are tunable to hit a chosen target gap, or to match SAPRIN/Thembisa.

## 6. (Optional) fertility by income
- **SADHS 2016** birth histories (DHS Individual Recode) → ASFR by 5-yr age ×
  wealth quintile (TFR 3.1 poorest → 2.1 richest; teen-childbearing 20% Q1 →
  6.5% Q5).
- **Stats SA Census 2011 Fertility report (03-01-63), Table 15** — ASFR by
  5-yr age × **population group**: the only ready-made age × SES fertility
  matrix (Black African schedule peaks 20–24 with high adolescent fertility;
  White peaks 25–34 with near-zero adolescent — a clear left-shift for lower
  SES). Model the **age-tilt**, not just a TFR scaling.

## Key references (verify before citing)
- Kabudula et al. 2017, *Lancet Glob Health* 5(9):e924 — PMC5559644
- SAPRIN cohort profile, *IJE* 2022 51(4):e206 — PMC9365637
- HAALSI — ICPSR/NACDA 36633; haalsi.org
- WHO SAGE — who.int Study on global AGEing and adult health
- UN WPP 2024 — `PPgp/wpp2024` R pkg, `mx5dt`, code 710
- WHO GHO life tables — ghoapi.azureedge.net LIFE_0000000029 / 030
- DHS API (SADHS 2016) — api.dhsprogram.com, countryId ZA
- SAMRC BoD Unit; Stats SA P0309.3; Thembisa
