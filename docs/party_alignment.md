# Party alignment and MPI change — pre-registered test

**Status: §1–§3 were fixed and committed before any alignment value or result was
computed.** The commit that adds this file precedes every commit that adds code or
results; `git log --follow docs/party_alignment.md` is the proof. §4 is written by
`scripts/08_party_alignment.py` and must choose its sentence from §3, not compose one.

## 1. Why this replaces the dominant-party label

`data/reference/state_dominant_party.csv` (mode governorship party 1999–2021) cannot
test whether party is associated with poverty:

- 26 of 36 governed states have mode = PDP, which records PDP's national dominance
  1999–2015 rather than anything state-specific. Within the PDP group 2021 MPI runs
  from 0.441 (Bauchi) to near zero.
- The other groups have 1–3 states. All three ANPP-mode states (Zamfara, Yobe,
  Borno) are in the poorest 12 and in the north, so any party gap is the latitude
  gradient again (see the climate finding in `AGENTS.md`).
- A 1999–2021 summary set against a single 2021 MPI has no time alignment and
  cannot separate "party X governs poor states" from "poor states elect party X".

The mode label stays as hover context. It is **not** an explanatory variable.

## 2. The test

**Hypothesis.** Over the years between survey rounds, states whose governor belonged
to the federal ruling party saw MPI fall faster than states whose governor did not.
This is the federal–state alignment argument (aligned states are held to receive
more federal attention and resources). One hypothesis only, chosen 2026-10-09; no
party-family or turnover test will be added after the result is seen.

**Federal ruling party.** PDP from 29 May 1999 to 29 May 2015; APC from 29 May 2015.

**Units.** 36 governed states × 3 intervals between the four harmonised rounds
(2013 DHS → 2016 MICS → 2018 DHS → 2021 MICS) = **108 rows**. **FCT is excluded**
because it has no elected governor; this is a stated exception to the project's
keep-FCT rule, and the output lists it as excluded.

**Governor's party.** From `data/reference/governorship_events.csv`, the event
matrix in `docs/dominant_party.md` in machine-readable form. Party = the platform the
winner ran on in that event (the existing as-won rule; defections do not relabel).
An event takes effect in the year its winner was **seated** (`seated_year`; for
court-installed winners this is the seating year, not the election year). Every
`seated_year` that differs from the election year must cite a source in the file;
none may come from memory.

**Year weighting.** Annual resolution. In any year in which the governing party
changes (a seating, or the 2015 federal handover), the year is split 5/12 to the
outgoing and 7/12 to the incoming party, approximating a late-May change. The same
rule applies to every event, so no event is placed more precisely than another.

**Exposure.** For interval [t0, t1), `aligned_share` = the weighted fraction of the
calendar years t0 … t1−1 in which the governor's party equals the federal party.
Range [0, 1].

**Outcome.** `dmpi_annual` = (MPI_t1 − MPI_t0) / (t1 − t0), from
`data/processed/mpi_trends_panel.csv`. Negative = poverty fell.

**Primary model.** OLS:
`dmpi_annual ~ aligned_share + interval fixed effects + mpi_t0`.
The interval effects absorb the national trend, including the 2015 federal change
itself. `mpi_t0` absorbs the fact that poorer states can fall further in absolute
terms. β = the coefficient on `aligned_share`.

**Inference.**
- p-value: two-sided permutation test. Each state's whole 3-interval alignment
  history is shuffled across states as a unit, the model is refitted, and this is
  repeated 10,000 times with seed 20261009. p = share of |β_perm| ≥ |β_obs|.
- 95% CI for β: state-cluster bootstrap (resample states with replacement), 5,000
  draws, seed 20261009, percentile interval.
- **Detected** means p < 0.05. Nothing else counts as detection.

**Power, reported whatever the result.** The minimum detectable effect (MDE) is the
smallest |β| at which the permutation test (1,000 permutations per run) rejects at
α = 0.05 in ≥ 80% of 500 simulated datasets. Each dataset is the fitted null model
(β = 0) plus state-cluster-resampled residuals plus β·`aligned_share`. Seed 20261009.
Search β on a grid of 0.0005 per year.

**Robustness checks.** These are reported beside the primary result and never
replace it:
- (a) outcome = log(MPI_t1 / MPI_t0) / (t1 − t0) (relative change);
- (b) primary model + `poverty_group` × interval;
- (c) exposure = binary aligned (`aligned_share` ≥ 0.5).

**Known limitations, stated in the output.**
- Sitting-party defections are not modelled, for example the 2013–14 PDP→APC
  governor moves and Ebonyi's 2020 move to APC. A defection sensitivity check may be
  added only with sourced dates, and only as an extra robustness row.
- MPI change carries survey error: OPHI's median relative SE is about 15%, and 41 of
  111 state-period changes are significant.
- n = 36. A null result is a statement about this design, not about the world.

## 3. Pre-written wording — the only sentences allowed

Let X = |β| expressed as MPI points per year, CI = the 95% bootstrap interval,
MDE = the minimum detectable effect.

- **Detected, β < 0:** "Over 2013–2021, states governed in alignment with the federal
  ruling party saw MPI fall X faster per year than non-aligned states (95% CI …,
  permutation p = …). This is an association within states over time, not an effect
  of party."
- **Detected, β > 0:** "Over 2013–2021, states governed in alignment with the federal
  ruling party saw MPI fall X *slower* per year than non-aligned states (95% CI …,
  permutation p = …). This is an association within states over time, not an effect
  of party."
- **Not detected:** "No association between federal alignment and the pace of MPI
  change is detectable over 2013–2021 (β = …, 95% CI …, permutation p = …). This
  design could not detect an association smaller than MDE per year, so this is not
  evidence that none exists."

Never write "not associated", "party causes", or "aligned states reduced poverty".
Never phrase it as north vs south.

## 4. Result

*Written by `scripts/08_party_alignment.py` on 2026-10-09. Do not edit by hand.*

Over 2013–2021, states governed in alignment with the federal ruling party saw MPI fall 0.0080 MPI points *slower* per year than non-aligned states (95% CI -0.0002 to 0.0168, permutation p = 0.036). This is an association within states over time, not an effect of party.

| Model | β | 95% CI (state-cluster bootstrap) | Permutation p | n |
|---|---|---|---|---|
| Primary: aligned_share (as won) | 0.0080 | -0.0002 to 0.0168 | 0.036 | 108 |
| (a) outcome = log(MPI_t1/MPI_t0)/(t1-t0) | 0.0386 | -0.0385 to 0.1221 | 0.239 | 108 |
| (b) + poverty_group x interval | 0.0081 | 0.0015 to 0.0143 | 0.025 | 108 |
| (c) exposure = aligned_share >= 0.5 | 0.0055 | -0.0021 to 0.0131 | 0.127 | 108 |
| (d) sitting party: as won, switched at sourced defection month (added after the primary result was known, §2 limitation clause) | 0.0070 | -0.0009 to 0.0156 | 0.083 | 108 |
| Leave out 2013–16 (primary model, 2 intervals) | 0.0039 | -0.0027 to 0.0110 | 0.368 | 72 |
| Leave out 2016–18 (primary model, 2 intervals) | 0.0077 | -0.0010 to 0.0167 | 0.088 | 72 |
| Leave out 2018–21 (primary model, 2 intervals) | 0.0117 | -0.0019 to 0.0254 | 0.057 | 72 |
| Interval 2013–16 only (cross-section, aligned_share + mpi_t0) | 0.0159 | 0.0013 to 0.0281 | 0.009 | 36 |
| Interval 2016–18 only (cross-section, aligned_share + mpi_t0) | 0.0043 | -0.0077 to 0.0177 | 0.626 | 36 |
| Interval 2018–21 only (cross-section, aligned_share + mpi_t0) | 0.0008 | -0.0107 to 0.0124 | 0.903 | 36 |

- Result rests on 2013–16; not robust to (a) relative change, (c) binary exposure, (d) sitting party, dropping any one interval.
- Robustness (d) and the leave-one-interval-out and per-interval rows were added after the
  primary result was known. (d) uses the §2 limitation clause (defections only with sourced
  dates, only as an extra robustness row): the as-won party, switched at the month of each
  sourced change in `data/reference/governor_defections.csv` (the Nov 2013 PDP→APC
  governors, the 31 Jul 2013 ACN/ANPP/CPC→APC merger, later moves through Jun 2021), at
  monthly resolution. Successions after impeachment (Adamawa 2014) are not modelled.
  None of these rows replaces the primary result or changes the §3 sentence.
- Permutation p is a Monte Carlo estimate (10,000 draws, seed 20261009), shown to 3 dp.
  Across 10 other seeds the primary p ranged 0.031–0.036,
  so read it as about ±0.005.
- MDE (80% power, α = 0.05, 500 simulated datasets × 1,000 permutations, grid 0.0005): |β| = 0.0115 MPI points per year (β < 0: 0.0115; β > 0: 0.0110).
- n = 108 state-intervals (36 states × 3 intervals) for the full models. FCT excluded: no
  elected governor.
- β is in MPI points (0–1 scale) per year per unit of `aligned_share`; check (a) is in
  log-ratio per year. Bootstrap: 5,000 draws; seed 20261009.
- Limitations: the primary model does not model sitting-party defections (see (d)); MPI
  change carries survey error (median relative SE about 15%); n = 36 states, so a null
  result is a statement about this design, not about the world.
