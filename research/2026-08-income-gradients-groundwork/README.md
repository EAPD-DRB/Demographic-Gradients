# Income-gradient groundwork (session notes, June–August 2026)

Exploratory research that preceded and parallels this library: data sources for
mortality and fertility differentiated by income, per country, and a prototype
construction of income-group mortality-rate schedules. Preserved here as
provenance and as a source inventory the library itself does not carry.

**Status relative to the library:** the library supersedes this work for data
collection — its DHS gradient library (78 countries) and census household-deaths
pipeline replaced the hand-stitched per-country approach explored here. What
remains useful:

- [`SOURCES.md`](SOURCES.md) — the per-country source inventory (aging cohorts,
  HDSS sites, panels, national sources) with citations and access notes. Most of
  these sources are *not* used by the library (it uses DHS + census modules) and
  are the natural place to look for validation, old-age evidence, or an Asian
  adult observation (the library's flagged gap).
- [`SOUTH_AFRICA_handoff.md`](SOUTH_AFRICA_handoff.md) — a self-contained
  briefing for calibrating income-differentiated mortality for South Africa,
  written before the library existed. Its Agincourt/HAALSI/SAPRIN sourcing
  complements the library's census-based ZAF rows.
- [`scripts/`](scripts/) — the prototype schedule construction: national UN WPP
  `nMx` × a log-linear-in-rank adjustment factor, normalized so the group
  average reproduces the national schedule exactly (verified to ~1e-16 in
  `verify_aggregate.py`, which also quantifies the survivor-weighting drift).
  The same normalize-to-national idea appears in ogcore's gradient
  implementation; the verification script remains a useful independent check.
- [`figures/`](figures/) and `mortality_rate_schedules.csv` — regenerated
  outputs of those scripts (run any script with the repo's Python; they write
  into this folder).

Two findings worth keeping visible: (1) the LMIC income–mortality gradient is
double-peaked across age (child spike + young-adult HIV/TB/injury hump, old-age
compression) — a high-income donor shape misplaces the steepness; (2) the
income–fertility difference in these countries is an age-*tilt* (poor childbear
younger), not just a TFR level shift — Indonesia's near-flat TFR gradient with
an ~8× teen-childbearing gradient is the clean proof.

History: originally built in a scratch directory during an OG-Core session;
reconstructed into this repo 2026-08-09 (the scratch copy was OS-cleaned). The
only edit to the scripts is the output path (was `/tmp/og_income_demographics`,
now this folder).
