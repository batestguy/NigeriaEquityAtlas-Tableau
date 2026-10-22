# Brief: "How the measures pair" — bivariate exploration board (two-group split)

Date: 2026-10-21  Status: **Ready with risks** — freeze doc follows after one more data-count pass

## Goal
In the user's words: "bivariate plots of all continuous variables (or logged to
be linear as an option)" — one exploration board inside the published workbook
that shows any x-y pair of continuous measures, split into two panels: the
poorest 12 and the other 25.

## Users & decisions
The atlas author uses it to pattern-hunt (no association claims enter the sheet:
"points only" was the settled answer). A reader who opens it sees the picture
and its printed limits. Who decides what: the author for exploration findings;
any pattern that later becomes a sentence must go through the repo's
pre-registration route (docs/party_alignment.md / spatial_analysis.md pattern)
**before** confirmatory code — settled at "Full discipline".

## What exists (verified against the pipeline, 2026-10-21)
- `data/processed/mpi_trends_panel.csv` — 148 rows (37 states × 4 harmonised
  rounds): mpi, headcount_ratio_pct, intensity_pct, events_per_100k,
  fatalities_per_100k, fatalities_per_100k_high, mpi_change_since_prev/label,
  temp_mean_c, six rank_* columns.
- `data/processed/mpi_atlas_2021.csv` — 37 rows: poverty_group (Poorest 12 /
  Other 25), population, contrib_* dimension shares, conflict index, weather
  anomalies, area columns (exist — column names to be listed in the freeze).
- `data/processed/mpi_polygons.csv` + spatial CSVs — not relevant to this sheet
  except via the existing extract pattern.
- The workbook grammar: six views shipped; palettes, row headers, tooltips,
  window cards all proven; **parameters and calculated fields are NOT proven**
  (never hand-authored in this repo; "Deliberately NO <lod>" is the time panel's
  comment — the construct is genuinely new here).

## Decisions taken in the interview (2026-10-21)
1. Purpose: exploration board, pattern-hunting first — no claim on the sheet
   ("Exploration for me").
2. Placement: inside the published workbook ("Tableau sheet in workbook"), as a
   new tab — proposed tab 4, between the time panel and the reference tabs.
3. Variable scope: "Truly all continuous" — including the red-listed family
   (conflict_exposure_index, temp_anomaly_c, precip_anomaly_pct), on the
   strength that no claim pours from the sheet. The freeze will count the exact
   column list and their sources.
4. Time scope: all four harmonised rounds, each point = a state-round, the two
   panels split by the state's **2021** poverty group (48 points in the poorest
   pane, 100 in the other). The legitimacy sentence: rank persistence
   0.87–0.92 between rounds means the 2021 bottom 12 are essentially the same
   states in every round.
5. Transform: **log1p on the three conflict rates only** (events_per_100k,
   fatalities_per_100k, fatalities_per_100k_high) — logged variants ship as
   ordinary columns written by stage 4; the x/y dropdowns list raw and logged
   variants as separate entries. No interactive transform toggle; no calc field
   for the transform. Zero-event states survive: log1p(0)=0, they sit on the 0
   gridline — no reference-line grammar needed. Any other field stays raw.
6. Mechanics: ONE scatter worksheet with a **dynamic pair-picker** — two
   parameter dropdowns (x-measure, y-measure) plus two case-based calculated
   fields for the dynamic measures. This is the only shape that scales to the
   full pairwise scope (~15 fields ⇝ 105 pairs); a fixed curated sheet set was
   rejected as contradicting "truly all continuous".
7. Panel split reading: headline only — no slope, r, or any statistic drawn or
   printed; the subtitle carries the caveat verbatim: the split is the outcome's
   poorest tail vs the rest; pane slopes are range-restricted and not
   comparable; no test is offered.
8. Default on load: **H (% poor) × log1p events/100k** — interpretable axes,
   zeros visible, and it opens on the pair whose null is already documented
   (FIX_LEDGER A3).
9. Governance: full discipline — freeze doc, stage-5 gate entry, FIX_LEDGER
   section, "what this sheet may not say" list, pre-registration for any later
   pattern-claim.

## Constraints
- Grammar risk is the build's critical path: three unproven constructs, each to
  be proven by its own packet bisect before the sheet is written with them —
  (a) the workbook `<parameters>` block; (b) `parameter-ctrl` cards in the
  window strip (present in the schema enum dumped from tabfileformat.dll on
  2026-10-21 — promising); (c) a case-based calculated field
  (`CASE WHEN [p] = 'a' THEN [colA] ... END`) resolving as a shelf measure.
- `poverty_group` must be stamped onto all 148 panel rows in stage 4 first
  (2021-only today).
- The stage-5 gate can only assert the sheet's **default** state (parameters
  bind at load); parameter interactions stay publish-time manual checks like
  the time panel's.
- Boots-on convention: no causal language anywhere on the sheet; "poorest
  states vs the rest", never "north vs south"; overlap caveat printed.

## Success criteria (checkable)
- The workbook loads in Tableau Public 2026.2 with the new tab present, no
  error dialog; default pair H × log1p(events/100k) draws 148 marks in two
  panes (48 / 100).
- Changing x/y via the dropdowns re-draws the scatter with a new axis for any
  of the whitelisted continuous fields (raw and logged conflict variants).
- Zero-event states remain visible on the log1p axes.
- Stage 5 regenerates the gate PNG for the default state; red-list + hover
  asserts extend to the new schema; the full run_all stays exit 0.
- No statistic, slope, or association wording appears on the canvas; hover
  prints `state · round — X-value · Y-value` (round out: 2018 DHS style).

## Out of scope
- Any statistical test, fit, or correlation readout on the sheet.
- Rank axes as an option (rejected: range collapse inside the two groups makes
  the scatter nearly vertical).
- Porting whatever pattern-hunting finds into the workbook's claims — that goes
  through pre-registration, not this sheet.
- Logged variants of anything but the three conflict rates.

## Smallest useful version
One sheet, default pair H × log1p(events/100k), two panes, pair-picker working
for at least the six whitelist fields; extend the dropdown list to the remaining
fields after the constructs hold.

## Open questions / UNKNOWNs
- Exact membership of "all continuous": the atlas_2021 area/density columns'
  names and per-field presence need a one-pass list before the freeze counts it.
- Population vintage behind the earlier per-100k conflict rates (stage 2): the
  rates across the four rounds need their denominators' provenance stated in
  the freeze or marked UNKNOWN.
- Table name / tab title: working title "How the measures pair" — user has
  approved provisionally; final name set in the freeze.

## Risks
- The case-based calc field may not resolve from hand-authored XML (the failure
  mode that killed several grammers) — mitigated by the one-construct packet
  order and the established bisect discipline.
- The `<parameters>` block may carry another schema enum quirk (see T5's
  'not in enumeration' class).
- The red-listed fields' re-entry into a sheet schema contradicts the freeze's
  letter — resolved by the freeze re-scoping the red list per-sheet (this
  sheet's red list = the withdrawn sheets' defects: size channels, trend fits,
  causal wording).
- Pattern-hunting temptation: any interesting-looking pair will tempt a claim;
  the full-discipline guard is the answer and was accepted.

## Recommended next step
1. Data pass: list every continuous column with its source row scope (or
   UNKNOWN) — the freeze's variable table.
2. Prove the three grammar constructs in bisect packets, in order: (a) load a
   workbook with an unused `<parameters>` block; (b) add one `parameter-ctrl`
   card and one calc field on an existing sheet in a review packet; (c) the
   dynamic pair-picker.
3. Draft `docs/SHEET_PAIRS.md` freeze from this brief + the grammar findings;
   then stage-4 group stamp + extract columns; stages 5/6; render test.
