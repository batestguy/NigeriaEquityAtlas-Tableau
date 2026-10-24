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

As frozen 2026-10-20 the six value measures below were "green". The 2026-10-21
user amendment **replaced them**: the marks draw each state's **rank** on those
same six measures, and the sheet carries rank variables only — the raw value
columns are now **absent from the extract** (see "Built, 2026-10-21"), so no
returning edit can put a bare value back on a mark. The whitelist the sheet
ships is `rank_mpi`, `rank_headcount`, `rank_intensity`, `rank_events`,
`rank_deaths`, `rank_temp` — same six colours, same captions with a
"· rank (1 = highest)" suffix, same direction (1 = highest ≡ poorest / most
conflict / hottest). The hover's two numeric annotations ride as pre-formatted
string dimensions (`mpi_change_label`, `deaths_high_label`), never as measures,
so they cannot join the Measure Names domain.

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
| all six value measures above | **red — amended out 2026-10-21** | the sheet's variables are ranks only; the values live in `mpi_trends_panel.csv` for the pipeline and the gate, not in the extract a sheet can reach |

## Guardrails baked into the sheet

1. **Tooltip:** the annualised change since the previous round (printed from the
   string column `mpi_change_label`) with the `mpi_change_significant` flag, plus
   the conflict-deaths upper estimate (`deaths_high_label`) where relevant.
   Movement comes pre-labelled as measured or within-noise.
2. **Subtitle (once, not per dot):** the rank direction key ("1 = the measure's
   highest value; a higher rank means away from the extreme") plus the overlap
   caveat — OPHI's significance test flags a movement, and neighbouring states'
   95% intervals overlap for every adjacent rank pair, so read within-state
   movement.
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

## Built, 2026-10-20 — the decisions above were resolved as follows

The sheet is built: `06_build_twb.py` writes the third extract
(`Data/mpi_trends_panel.hyper`, 148 rows, schema asserted against both the whitelist
and the red list — the red-list fields and the raw counts are **not at all**), the
Measure Names / Measure Values worksheet, and the interactive cards. The build's
grammar findings, each verified by opening the packet in Tableau Public 2026.2
(single-worksheet review copy `review_time_only.twbx`):

- **The Measure Names / Measure Values construct works from hand-authored XML.**
  Rows `([ds].[:Measure Names] + [ds].[Multiple Values])`, colour `[:Measure Names]`,
  palette buckets keyed by quoted field refs — all copied from
  `ClimatechangeprofileNigeria` (Tableau MCP). The open state draws "24 marks, 6 rows
  by 4 columns": six whitelist measures × four rounds, no red-list measure, and
  `fatalities_per_100k_high` correctly present-but-unticked in the checklist.
- **A dimension on `<lod>`/detail splits a line into one-point lines.** The first
  render drew isolated dots: `survey` and `mpi_change_significant` are string
  dimensions and their per-round values differ, so each mark became its own "line".
  Fix: no `<lod>` fields at all; the annotations ride in the **customized tooltip**,
  whose off-view field references resolve to the mark's own (state, round) context.
  Hover behaviour itself is verified at publish time (tooltips are separate popup
  windows a PrintWindow capture cannot see).
- **Left-edge cards draw; right-edge cards do not** in packets built by this script —
  the same class of defect as the map colour legend (docs/FIX_LEDGER.md), now reproduced with
  a plain `mode='dropdown'` filter card copied byte-for-byte from HRAnalytics. So the
  state dropdown and the Measure Names checklist declare on the LEFT strip above
  `<card type='marks' />`, where both render. The side is cosmetic; the interaction
  is not.
- **The `<title>` card had to be added** to the top strip (`strip size='31'`), or the
  sheet's title and frozen subtitle never render.
- **Captions double as row headers**, so `atlas_text.PANEL_MEASURES` captions are
  short and unit-honest ("MPI (0–1 scale)", "Headcount H (% poor)", "Intensity A
  (% missing among the poor)", "Conflict events/deaths per 100k", "Mean temp at the
  capital (°C)") — long captions truncated hard under Entire View.
- **System-generated fields leak into the Measure Names domain** ("Migrated Data
  (Count)", "Latitude/Longitude (generated)" — Tableau adds them to every Hyper
  extract; the older two extracts have them too). They cannot be deleted; the union
  filter excludes them, and they render unchecked. A reader can tick "Count of
  Migrated Data" — the sheet would draw a nonsense 37-identity line — this is the one
  cosmetic wart left knowingly; a future guard could be a Measure-Names allowlist via
  a Tableau set, not attempted in v1.
- **The QA preview is `docs/preview/3_state_over_time.png`** — the stage-5 naming rule
  is "N, in tab order" (the sheet is tab 3; the three reference parts renumbered to
  4/5/6), taking precedence over this doc's earlier "6_state_over_time.png" guess.
- **Known publish-time checks still to do** (cannot be done from captures): confirm
  the hover shows the four annotation fields, and that ticking/unticking measures in
  the checklist leaves the view consistent (a mid-session observation showed the
  measure set widening after a mark selection — one repro, not understood; if it
  reproduces on the published viz, drop the `param` cards and rely on the standard
  Filters shelf card, whose dropdown works).

## Built, 2026-10-21 — the rank amendment

The marks no longer draw the raw values; they draw each state's **rank of the 37
states in that survey round**, and the sheet now carries **rank variables only** —
the user asked that every non-rank variable leave the sheet, and it left the
*extract*, not just the canvas. Recorded against the freeze:

- **The marks draw ranks** (`04_merge.py` `RANK_FIELDS`: six rank columns over the
  148 panel rows, descending competition ranks per round, asserted 1–37 and
  rank-1 = the round's highest value). Direction key: 1 = the measure's highest
  value — poorest MPI, most conflict, hottest capital; ties share the better rank;
  a higher number means the state moved away from the extreme. The key rides the
  row-header captions ("… · rank (1 = highest)") and the sheet subtitle; it is
  **not** a confidence claim — the subtitle carries OPHI's overlap caveat.
- **Labels print bare integers, not "R32".** The R prefix was tried in the field's
  own number format (`default-format='"R"0'` on the `<column>`) and the integer
  format part took (the old two-decimal "36.00" misprint is gone) but the quoted
  literal prefix did not render in Tableau Public 2026.2. The key text is prose:
  captions + subtitle. The stage-5 gate prints `R{v}`-annotated points of the same
  integers; the two surfaces agree on every number and every colour.
- **Where a field number format serialises (that-bisect finding).** A
  `<style-rule>`-level `attr='number-format'` — field-scoped or mark-scoped —
  fails the whole workbook load: *Error D2E8DA72, "value 'number-format' not in
  enumeration"* (the attr enum, read out of `tabfileformat.dll`, does not contain
  it at all). The application stores a field format as **`default-format` on the
  `<column>`** — with it the workbook loads.
- **An integer measure must be declared `type='quantitative'`.** With the zip
  datatype→type mapping applying `ordinal` to the integer rank columns, the
  measures fell out of the quantitative Measure Names domain: their domain keys
  were no longer the `[sum:X:qk]` refs the union-filter members and palette
  buckets use, and the whole microcosm silently unbound — the checklist showed
  raw field names, one arbitrary tick, the state filter slid to "Ekiti", default
  pastel palette, and Tableau's generated "Count of Migrated Data" drew as a
  pane. Verified fixed by the render test after the change: stored members bind
  (six ticked, "(All)" and "Count of Migrated Data" not), the six assigned
  colours draw, state pinned to Bauchi.
- **The extract carries ranks and string hovers only.** Dropped from the schema
  (and from the red list's assertion, so they cannot silently return): `mpi`,
  `headcount_ratio_pct`, `intensity_pct`, `events_per_100k`,
  `fatalities_per_100k`, `fatalities_per_100k_high`, `mpi_change_since_prev`,
  `temp_mean_c`. The hover's two numeric annotations became pre-formatted STRING
  dimensions (`mpi_change_label`, `deaths_high_label`, written in stage 4) so
  they cannot re-enter the Measure Names domain; the Measure Names checklist now
  lists the six rank captions and nothing else but the system leak. The full
  value columns remain in `data/processed/mpi_trends_panel.csv`, where the
  pipeline's later stages and the QA gate read them.
- **Charts in the render test agreed with the gate**: same six measures, same
  captions, same colours, Bauchi default, Entire View. The publish-time checks
  above are unchanged.

---

## Amendment - 2026-10-24: one direction key, not seven

Two changes, both word-count only:

1. **The six row-header captions lose their suffix.** They read
   `MPI · rank`, `H % poor · rank`, `Intensity A · rank`, `Conflict events/100k ·
   rank`, `Conflict deaths/100k · rank`, `Capital temp · rank` — i.e. the
   `(1 = highest)` parenthetical is gone from all six and now appears ONCE, in
   the subtitle the freeze already requires it in ("1 = highest"). Six copies of
   the same three words on the row-header rail bought nothing and cost width.
2. **The subtitle is rewritten to say what the figure is** (240 -> 130 chars):

   > One state's rank of 37 on six measures, four rounds · 1 = highest ·
   > stars = significant change · ranks overlap at 95%, so no trend

   Every frozen element survives: the direction key, the star meaning, and the
   OPHI overlap caveat that forbids reading movement between states. What went
   was the parenthetical examples of what "highest" means per measure (poorest
   MPI, most conflict, hottest capital) — the captions name the measure, so the
   examples were restating the row header.

The stage-5 gate's own paragraph was cut from nine lines to three for the same
reason; it is a QA artefact, not a published page, but it had become the longest
block of prose in the repo's renders.
