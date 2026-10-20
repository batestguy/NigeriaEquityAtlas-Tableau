# Next sheet: "A state over time" — design freeze

Decided 2026-10-20, from the offline data-explorer sessions (`analysis/dags.html`,
`analysis/data_explorer.html`). This is the specification for the **sixth view** — the
first sheet to be added since the 2026-10-18 withdrawal wave (FIX_LEDGER W1). Build it
only as written here; every guardrail below exists because a version of this sheet was
already withdrawn once.

## What the sheet is

The user picks **one state** (37 options, FCT included), then ticks **any set of
variables to monitor**, and sees each chosen variable as a **line with markers over the
four survey rounds** (2013, 2016, 2018, 2021). One small chart per variable, each with
its own y-axis.

This is a **description of measured points**, not a trend analysis:

- **No fitted trend line.** Tableau's Analytics-pane trend models stay off this sheet.
  Four points per line cannot support a slope, and a trend sheet is exactly what was
  withdrawn in W1.
- **No forecast, no projection, no "falling/steady" caption language** beyond what the
  `mpi_change_significant` flags earn (only 15 of 111 state-intervals earn the flag).
- **Movement, not levels.** The defensible read is *within one state over time*.
  Cross-state level comparison is forbidden from this sheet — all 36 adjacent rank
  pairs overlap at 95% (OPHI SEs, `data/interim/mpi_se_ci.csv`). A subtitle line says
  so once.

## The Tableau construct

Do not use a parameter-driven measure switch — it forces one shared axis and MPI
(0–0.45) dies against H (0–75) on it. Use the Measure Names / Measure Values machinery
instead, which gives **one honest axis per selected variable**:

| Shelf | Field |
|---|---|
| Columns | `survey_year` |
| Rows | `Measure Names`, then `Measure Values` |
| Measure Values shelf | all whitelisted measures (table below) |
| Measure Names filter | shown as checkboxes — this *is* the "variables to monitor" multi-select |
| State filter | single-select dropdown, FCT in the list |
| Mark | Line, markers on |

Because `Measure Names` sits on Rows, each variable small-multiples into its own axis
range. No normalisation is used anywhere — normalising would reintroduce the
within-year relativity the conflict index already demonstrates the danger of.

## Variable whitelist (what may go on the sheet)

| Field | Status | Note |
|---|---|---|
| `mpi` | green | harmonised OPHI series, verified 4 dp against Table 6.4 on all 148 rows |
| `headcount_ratio_pct` (H) | green | the most interpretable; H and A often move in opposite directions — that contrast is the sheet's best story ("fewer poor" ≠ "less deep") |
| `intensity_pct` (A) | green | as above |
| `events_per_100k` | green | absolute, population-normalised |
| `fatalities_per_100k` | green | carry `fatalities_per_100k_high` in the tooltip, not as a second line |
| `temp_mean_c` | green (descriptive) | capital-station weather; label as such |

| Field | Status | Reason |
|---|---|---|
| `conflict_exposure_index` | **red — excluded** | min-max scaled **within** each survey round; its 0 and 100 are different states every year. A time-series of it charts the re-anchoring, not violence |
| `temp_anomaly_c`, `precip_anomaly_pct` | **red — excluded** | four rounds of weather at one city is not a climate signal; trending it manufactures a story from noise |
| `events`, `fatalities` (raw) | amber — default off | not wrong but scale-dominated (Lagos vs Bayelsa); per-100k is the defensible pair |
| dimension `contrib_*`, severe/vulnerable, population, bands, ranks | absent | 2021-only columns; the panel does not carry them. The tab's subtitle must say the picker covers "what moves across rounds", not everything |

## Guardrails baked into the sheet

1. **Tooltip:** `mpi_change_since_prev` with the `mpi_change_significant` flag, plus
   `fatalities_per_100k_high` where relevant. Movement comes pre-labelled as measured
   or within-noise.
2. **Subtitle (once, not per dot):** intervals are flagged only where OPHI's
   significance test passes; neighbouring states' 95% intervals overlap for every
   adjacent rank pair, so read within-state movement.
3. **No state-vs-state colouring, no party anything** on this sheet. Party is hover
   context on the maps only.
4. **Default state on load:** a poorest-12 state (Bauchi is the natural pick — it is
   the hover example everywhere else), so the sheet never opens blank.

## Optional upgrades (not v1)

- Grey **37-state median reference line per round, per variable** (window median
  across states at the same year) — shows "my state vs the pack" without comparing CIs.
- `poverty_group` colour context for the selected state's line.

## Data / build implications

- **Stage 6 grows a third Hyper extract**: `mpi_trends_panel.hyper` written from
  `data/processed/mpi_trends_panel.csv` (148 rows), alongside
  `mpi_polygons.hyper` and `spatial_polygons.hyper`. `06_build_twb.py` already writes
  Hyper directly with `tableauhyperapi`, so this is an addition inside stage 6, not a
  new stage.
- **Stage 5 QA gate grows a sixth preview PNG** (`docs/preview/6_state_over_time.png`)
  drawn from the same panel CSV with the same whitelist — the gate and the sheet must
  not be able to disagree (same rule as the maps, FIX_LEDGER W1/W2).
- Panel fields that must NOT enter the extract's measure list: `conflict_exposure_index`,
  `temp_anomaly_c`, `precip_anomaly_pct` — either excluded from the Hyper schema or
  blocked by the Measure Names filter, so a future edit cannot silently reintroduce them.

## Open decisions at build time

- Whether the raw `events`/`fatalities` measures ship hidden (amber) or not at all.
- Exact wording of the two subtitle lines (write against `docs/CLAIMS.md` and
  `docs/CAUSAL_DECISION.md`, then verify in the claims pass).
