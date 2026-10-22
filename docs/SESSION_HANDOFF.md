# Handoff - sessions 2026-10-22 (composition sheet + white labels + default view), 2026-10-20 (explorer tools, next sheet frozen, then built), 2026-10-18 (reference table), 2026-10-09/10 (party test, map fit)

**Start here.** Pipeline is **9 stages**, all green (`.\scripts\run_all.ps1`, exit 0,
~160 s). The atlas is still **not published** — that remains the one manual
step (your Tableau Public login). Not committed at handoff: **both** the
pairs-board tab and everything the 2026-10-22 sections below describe sit as
working-tree changes stacked on `2f1b7bb`.

## 2026-10-22 (seventh session) - the composition sheet, white numbers, and a default view

The session's three landed results, all verified by render packets in Tableau
Public 2026.2 (evidence `C:\Users\TOSHIBA\AppData\Local\Temp\opencode\render_dim*.png`,
`render_full_dim.png`):

- **The frozen composition sheet is built** (tab 3): `dimension_shares.hyper`
  (3 contrib measures + 4 string dims, MPI deliberately absent), manual bar
  order, Okabe-Ito colours, hover strings from stage 4, gate
  `3_how_poverty_is_made_up.png`. `docs/SHEET_DIMENSIONS.md` carries the
  freeze and the Built record.
- **The segment numbers are bold white** — the label-colour grammar (after a
  six-packet hunt) is a pane-level `<style-rule element='datalabel'>`
  (`color-mode='user'`), the Try-Umphant workbook's byte shape;
  `FIX_LEDGER.md` D-051 records the five shapes that failed out.
- **The sheet defaults to 17 of 37 bars** (the user's request: five poorest +
  the first twelve of the Other 25), with all 37 on an interactive left-rail
  `state` checklist card (`FIX_LEDGER.md` D-052). Subtitle and QA gate
  describe the same default.

One warning for the next session: the whole of the above and the pairs-board
work before it are **uncommitted**, stacked in one tree — separate or commit
consciously.

## 2026-10-20 (sixth session) - the frozen sheet is built

The instruction: build the sixth view exactly as `docs/SHEET_TIME_PANEL.md` freezes it.
Done, end to end, in one commit (this session's):

- **`scripts/atlas_text.py`** gained `PANEL_MEASURES` (the six-measure whitelist: MPI,
  headcount, intensity, conflict events, conflict deaths, capital temperature — each
  with its caption and its hex colour) and `PANEL_DEFAULT_STATE = "Bauchi"`. The
  captions are short on purpose: they are the row headers, the checklist items, the
  colour legend and the tooltip fields, and long captions truncated hard under
  Entire View.
- **`scripts/06_build_twb.py`** writes the third extract (`Data/mpi_trends_panel.hyper`,
  148 rows) whose schema is **asserted** against the whitelist and against the red list
  — the red-list fields (`conflict_exposure_index`, the two anomalies) and the raw
  event/fatality counts are not in the extract at all; `fatalities_per_100k_high` is
  hover-only. The sheet is the Measure-Names small-multiple panel; the two interactive
  cards (Measure Names checklist, state dropdown) declare on the **left** rail because
  right-edge cards do not draw in packets this script builds (`docs/FIX_LEDGER.md` T2).
  The annotations ride a **customized tooltip** because a string dimension on `<lod>`
  splits a Line mark into one-point lines (T1 — found by the render, fixed by moving
  the fields off the mark).
- **`scripts/05_preview.py`** draws the sixth QA gate, `docs/preview/
  3_state_over_time.png` (the naming rule is "N, in tab order" — the reference parts
  renumbered to 4/5/6).
- **Rendered in Tableau Public 2026.2**, twice: as a single-worksheet packet (no tab
  bar to fight) and as the **shipped full workbook** — six tabs in order, "24 marks,
  6 rows by 4 columns", all six whitelist measures ticked with the hover-only and
  system fields unticked, `Bauchi` in the dropdown, subtitle rendering in full.
  Two checks remain interactive-only (hover annotations; checklist ticking) and are
  listed in `docs/PUBLISH.md`. `docs/FIX_LEDGER.md` §H records the render findings.
- Grammar rule update for the record: the Measure Names / Measure Values pair **is**
  buildable from hand-authored XML (rows `([ds].[:Measure Names] +
  [ds].[Multiple Values])`, bare `[:Measure Names]` on colour, union filter keyed by
  quoted field refs), copied from `ClimatechangeprofileNigeria` — the PUBLISH note
  saying the pair could not be made to render is retired.

## 2026-10-20 (fifth session) - offline analysis tools, and the next sheet frozen

The instruction for this pass: build offline HTML tools to inspect every pipeline
output, hypothesise honestly, and decide what earns a place in the workbook.

- **Three self-verifying explorer pages live in `analysis/`** (new top-level folder;
  regenerate with `& C:\Users\TOSHIBA\ds-general\python.exe analysis\<name>.py`):
  `data_explorer.html` (six tabs: master table, scatter lab, four rounds, spatial,
  party, Tableau ideas), `dags.html` (six causal DAGs, one per page, with build-time
  asserts so no page can quote a stale number) and `ci_chart.html` (the MPI dot +
  95% interval mock). All numbers on these pages are **recomputed from
  `data/processed/*.csv` at build time and asserted** — never quoted from memory.
- **Survivorship tally from the DAG pass** (verdicts, not new results): the
  harmonised-series, spatial, dimension-mix and band views survive as tested; the
  party result is fragile-only (fired, then failed every robustness check); the
  climate-precipitation, latitude and conflict associations are not identifiable at
  n = 37 — rhos of −0.80 (precip↔MPI) collapse under the latitude confound
  (partial rank −0.24; latitude↔MPI +0.82 is the twin of the outcome).
- **The next sheet is frozen, not built:** `docs/SHEET_TIME_PANEL.md` — "A state over
  time". Measure Names/Values small multiples, one state picked, any set of whitelisted
  variables ticked, four rounds as line + markers, **no fitted trend line**. Red list:
  `conflict_exposure_index` (re-anchored within each round), `temp_anomaly_c` /
  `precip_anomaly_pct` (four points of weather are not a climate signal). Build
  implications already written down: a third Hyper extract (`mpi_trends_panel.hyper`)
  in stage 6, a sixth QA preview in stage 5.

## 2026-10-18 (fourth session) — five views: two maps and one reference table

The instruction for this pass: keep **tab 1** (`Where poverty sits`) and **tab 2**
(`Where poverty clusters`), merge the two plain-language tabs into **one table** whose
columns are the formula, what the words mean and how we did it, delete everything else,
and colour tab 1 on a red ramp.

- **Seven views were withdrawn** — `Dimension breakdown`, `Poverty vs conflict`,
  `Poverty over time`, `Incidence vs intensity`, `Party alignment and MPI change`, the
  Moran scatter and the `Equity Atlas` dashboard — and with them the offline HTML map,
  so `scripts/07_build_interactive_map.py` is deleted and `run_all.ps1` runs nine
  stages. They are recoverable from git. `docs/FIX_LEDGER.md` **W1** records what each
  withdrawal cost and did not cost; the short version is that no claim was lost, the
  four defects that made three of those sheets wrong (D1–D5) are moot rather than
  fixed, and the analyses behind the rest still run.
- **The merged table ships as three tabs, not one.** Merged, it measured
  **2000 x 8720 px** — thirteen screens on the 687 px window it was reviewed in, and the
  user asked for it split if it was too big. It is cut on the groups it already had:
  `What the words mean` (24 rows, 2000 x 4406), `The list of basic needs` (11 rows,
  2000 x 1821) and `How we did it` (9 rows, 2000 x 2858). Each part repeats the intro and
  the column headers so it stands alone. `docs/FIX_LEDGER.md` **W2**.
- **The height model was one line short, and that was a real defect.** `_estimate_height`
  counted the wrapped text and not the zone's own padding, so Tableau — which ellipsizes
  a text zone's last line rather than growing the zone — cut off the end of every row
  that wrapped. The width model had been right all along (a 480 px cell held the 41
  characters predicted, a 760 px cell the predicted 68). Padding is now part of the
  estimate; before the fix the first row read "a household is poor at 33.3% or more of
  t…".
- **A literal `\n` in the XML fails the load with a useless log.** An over-escaped Python
  escape reached `<dashboards>` as two characters instead of a newline. It is still
  well-formed XML, so the parser accepted it and Tableau's only complaint was
  `D2E8DA72`, "the load was not able to complete successfully", naming nothing.
  `validate()` now fails the build on a literal `\n`, `\t` or `\u` in the XML text.
- **The band ramp is red, and the deepest red is the poorest band.** `#ffe5e5` (under 5%)
  through `#ffb8b8`, `#ff8a8a`, `#f45555` to `#d80000` (30% and above) — one hue, five
  steps, monotone in lightness, so the order is legible without the legend and no
  red–green pair exists anywhere. This is the interpretation of "from bright red to light
  red": attention goes to the poorest band. Flipping it is a one-line change to
  `atlas_text.MPI_BANDS` (stage 5 draws the gate from the same list, so the two cannot
  disagree).
- **The cluster map's legend wording is now specific.**
  `SPATIAL_QUADRANTS` labels each type by both its ingredients —
  `Poorer than average, neighbours poorer too` (grey `#969696`),
  `Poorer than average, neighbours better off` (purple `#54278f`, Nasarawa alone),
  `Better off than average, neighbours poorer` (pale teal `#80cdc1`, no state in 2021),
  `Better off than average, neighbours better off` (deep teal `#01665e`) — and the card is
  captioned `Neighbourhood type (this state's poverty, beside the states it borders')`.
- **Verified by opening the workbook in Tableau Public 2026.2 and looking at it.** The
  tab bar shows exactly five views in the intended order; `Where poverty sits` draws the
  red ramp under white state strokes; `Where poverty clusters` draws the grey north block,
  the deep teal south and purple Nasarawa with its colour card; and all three reference
  parts render with **no ellipsis** in any cell. Getting a specific tab into a capture
  needs care — Tableau's choice of view on load is not dependable (it follows the first
  `<window>` most of the time; the same generated workbook once opened on its second), the
  padded `PrintWindow` capture's pixels are not window coordinates under DPI
  virtualization, and two tab clicks computed the same way landed on different tabs.
  `%TEMP%\opencode\review_tab.py` rebuilds the package with a single `<window>`, and with
  `right` as a second argument keeps only the third column and moves it to x=0 — which is
  how the "How we did it" column, 760 px wide in a canvas that shows ~1340 px of a 2000 px
  dashboard, was read end to end and its longest cell (`Where the numbers come from`,
  which grew when the licence sentence was added) confirmed to render whole.
- **Still GUI clicks, both documented in `docs/PUBLISH.md`:** `Fit → Entire View` on each
  map (a geographic sheet crops at a fixed scale, and the dashboard that used to fit
  sheet 1 is withdrawn), axis headers off on both maps, sheet 1's colour legend, and alt
  text per view. Note the cluster map's colour card **does** draw, from the same
  declaration sheet 1 uses — so the sheet-1 legend item should be re-checked with the same
  capture method before it is treated as settled.

## 2026-10-18 (third session) — the spatial sheets: a cluster map beside the poverty map

Stage 9 was registered in the previous session and is now built, and the atlas has a
**second map** at the user's request: `Where poverty clusters`, immediately after
`Where poverty sits`, with the diagnostic scatter (`Do poor states sit next to poor
states?`) immediately after it.

- **The map is the same 37 rings, joined to the neighbourhood type.** Stage 9 now
  writes `data/processed/spatial_polygons.csv` — the polygon table's own columns, in its
  own order, plus `spatial_group`, `spatial_lag_mpi_pct`, `neighbours` — and stage 6
  packages it as a sixth extract (`spatial_polygons.hyper`, 7,089 rows) with its own
  datasource, `Spatial polygons`. It is a separate table rather than extra columns on
  `mpi_polygons.csv` because stage 4 owns that file and runs before stage 9 exists.
  Stage 6 asserts the joined table is the polygon table row for row (pcode, ring, lon,
  lat, point_order) and that the two spatial surfaces agree on which types exist.
- **Colour is descriptive, never significance.** Only one state survives the
  Bonferroni correction and none survives Benjamini–Yekutieli, so a significance map
  would be a single state — and it would invite naming it "the poorest cluster", the
  per-state ordering the atlas withdrew (`docs/FIX_LEDGER.md` A1). All 37 states are
  coloured by type and the count is carried in the hover instead. Recorded as
  **Amendment 1** in `docs/spatial_preregistration.md`: the test, the decision rule and
  the frozen wording are unchanged; the added surface was requested after the result was
  seen, and the amendment is appended rather than folded in.
- **The palette's two pale tints were the wrong way round.** `atlas_text` claimed
  "hue says how poor *this* state is", but the hexes assigned to HL/LH made the hue
  encode the *neighbours*: `high, beside low` drew pale teal and `low, beside high` pale
  purple. Swapped, so the legend rule is now the one the comment states and the one a
  reader can check by eye (purple states are the poor ones). Verified in the rebuilt
  workbook.
- **Both spatial surfaces share one tooltip and one set of words.** The four frozen
  reader lines, the heading, the no-cause caveat and the technical footer are generated
  once in stage 6 from `atlas_text`; only the "how to read this surface" sentence differs
  (colours on the map, two axes on the scatter). The four lines previously lived only in
  `docs/spatial_analysis.md` §3 despite §3 claiming they were "the wording on the sheet"
  — they are now on both sheets.
- **Renames:** the scatter's QA-gate PNG is `docs/preview/8_spatial_scatter.png`; the
  map's is `docs/preview/7_spatial_clusters_map.png`. Previews 1–6 are unchanged; the
  two spatial previews are appended and numbered in sheet order.
  *Superseded later the same day by the fourth session, which withdrew the scatter, made
  the map the only spatial surface and renumbered previews in tab order — so the cluster
  map's gate is now `docs/preview/2_where_poverty_clusters.png` and the two names above
  no longer exist.*
- **Verified by rendering** (`Tableau Public - render_test`, log line
  `Finished rendering sheet: Where poverty clusters`, no error line): the workbook opens,
  the `Spatial polygons` datasource is in the Data pane, the map draws deep purple north /
  deep teal south with Nasarawa the single pale "high, beside low" state, and the
  right-hand colour card draws with the `Neighbourhood type` title and its swatches.
- **Two things still needing a GUI click**, both on both maps: the axis titles read
  `Avg. lat` / `Avg. lon` (right-click → uncheck **Show Header**), and sheet 1's colour
  legend. The cluster map's own colour card **did** draw in the capture, which
  contradicts the open sheet-1 item at least once — re-check `Where poverty sits` with
  the same padded `PrintWindow` before treating that defect as settled. Neither is
  silently broken: both sheets declare the same card.
- **The `Equity Atlas` dashboard carried the five spec sheets only** — the two spatial
  sheets were standalone tabs, like the party sheet. *All of it was withdrawn the same
  day: the dashboard, the five spec sheets and the scatter (fourth session, below,
  `docs/FIX_LEDGER.md` W1).*


## 2026-10-18 (second session) — sheet 1: the bands have colours, and the gate matches

Sheet-by-sheet pass, starting with the map. Four defects, all fixed in the code path and
verified by rendering the rebuilt workbook in Tableau Public 2026.2 (window title
`Tableau Public - Nigeria-MPI-Equity-Atlas`, log line `Finished rendering sheet: Where
poverty sits`, `rk: ok`). Screenshot capture is scriptable: launch `tabpublic.exe` with
the workbook, then `PrintWindow(hwnd, hdc, 2)` — `CopyFromScreen` grabs whichever window
is on top, which is not Tableau here.

- **The five bands had no colours assigned.** `mpi_band` is a nominal dimension, so
  Colour drew it in Tableau's **default categorical palette** — five unrelated hues on a
  scale whose entire meaning is its order. Nothing in the workbook declared a palette:
  `grep palette` over the packaged `.twb` returned nothing, which is why the defect had
  never been seen (the legend, which would have shown it, has never drawn either).
  Stage 6 now writes the assignment into the polygon datasource (`palette_block`), with
  the grammar copied from two real Tableau-authored Public workbooks downloaded via the
  MCP server (`Ode to Cowbell`, `Clinic Performance Dashboard`). It is not guessable:
  the block sits **inside the `<datasource>`** between `<layout …/>` and
  `<semantic-values>`; the field is named **without** its datasource prefix; a string
  member is a quoted `<bucket>`; `type='palette'` is the discrete form (the continuous
  form is `type='interpolated'`, or `type='custom-interpolated'` with a nested
  `<color-palette>` of hex stops — what both reference workbooks use for their measures).
  Verified by rendering: the map now runs cream → brown from south to north.
- **The colours live in one place now.** `atlas_text.MPI_BANDS` is the list of five
  (label, hex) pairs; stage 6 reads it for the workbook, stage 5 for the QA-gate PNG and
  stage 7 for the HTML map, which previously carried its own copy. Two maps that colour
  the same field differently read as two different findings. Stage 6 asserts the data
  contains no band outside that list, and that no colour repeats.
- **The stage-5 QA gate previewed a different measure from the sheet it gates.**
  `docs/preview/1_where_poverty_sits.png` drew a continuous `YlOrRd` ramp of **H**, the
  headcount ratio; both maps colour the **MPI value** in five bands. A gate that previews
  a chart the workbook does not contain cannot catch a regression in the workbook. It now
  draws `mpi_band` in the five assigned colours, with a discrete five-band legend (not a
  colourbar, which would advertise a resolution the bands do not have) and white labels on
  the two darkest bands. The title now says MPI, and the subtitle keeps the two measures
  apart explicitly.
- **The colour field's caption was written twice and disagreed.** The datasource said
  `MPI band (Multidimensional Poverty Index)`; all six worksheet-level `<column>` copies
  still said `mpi_band`, which is a state Tableau never writes itself. Both are now
  generated from one map, and the Data pane shows the caption (visible in the capture).
  Which of the two the legend reads is still not established — they simply agree now.
- **Four dead fields removed from sheet 1's marks card.** `mpi`, `mpi_se`, `mpi_ci_lo`,
  `mpi_ci_hi` were detail encodings whose values never reach a reader (the customized
  tooltip uses `mpi_pct`, `mpi_ci_lo_pct`, `mpi_ci_hi_pct`), and a comment claimed they
  existed to draw the polygon. They did not.
- **Still open on sheet 1, unchanged:** the colour legend does not draw, so the click
  **Analysis → Legends → Colour Legend**, then Save, is still the one manual step — it
  will now show the ordered ramp under the full caption. The standalone sheet still opens
  cropped at Tableau's fixed map scale (**Fit → Entire View**; the `Equity Atlas`
  dashboard is already fitted). Alt text is still unset.

## 2026-10-18 — the hover, the band labels and the state outlines

Four requested changes to sheet 1, all generated in `scripts/04_merge.py` and
`scripts/06_build_twb.py` and verified by opening the rebuilt workbook in Tableau Public
2026.2 (title `Tableau Public - Nigeria-MPI-Equity-Atlas`, no error dialog, map drawn
with visible borders).

- **MPI now reads as a percentage of the index**, in the hover and in the band labels:
  `MPI 44.10% (95% interval 37.90% to 50.50%)` for Bauchi, bands `1. under 5%` … `5. 30%
  and above`. It is **not** the headcount share H, which the same hover prints separately
  as `Of the population, 75.36% are multidimensionally poor`. Stage 4 relabelled
  `mpi_band`; the `N. ` prefix stays because the colour legend sorts alphabetically. Stage
  7 and `scripts/atlas_text.py` were updated to match, so the HTML map and the glossary
  still agree with the workbook. The two decimals are Tableau's default for these percent
  columns — `44.10%` is the data's `44.1`.
- **The hover gained a governorship line** — `Governorship 1999–2021: PDP (14 of 22
  years)`, ties as `PDP/APC (tied)`, FCT as `no elected governor (minister-appointed)`.
  Stage 4's `party_years()` builds it from `data/reference/governorship_events.csv`,
  truncating each tenure at the 1999–2021 window — Anambra's 2021 election seated in 2022,
  which is what the "tenures total 22 years" assertion caught — and asserts the
  years-mode party equals the vetted `dom_party`, or sits inside its tie set.
- **`poverty_group` now says what it is**: `Bauchi · Poorest 12 of the 37 states, by MPI`.
  "Poorest 12" alone does not say 12 of what.
- **The legend names the index in full, the full meaning is italic where italics exist.**
  The Tableau colour card's title is the field caption, so `mpi_band` is now captioned
  `MPI band (Multidimensional Poverty Index)` — a caption cannot be italic, so the
  expansion is where the width allows. Every other legend surface is italic: the tooltip's
  MPI line, the HTML map's Plotly colour-bar title and its narrow-screen legend. All from
  `MPI_LEGEND_*` in `scripts/atlas_text.py`.
- **The state outlines are thick white strokes now.** The grammar that works is
  `has-stroke` / `stroke-color` / `stroke-size` on the **worksheet-level** mark style
  rule. The obvious-looking `border-color` / `border-width` on the same element is
  **inert** — the workbook renders pixel-identically with and without it, at worksheet and
  pane scope. Both names validate (both are in the published schema's `StyleAttribute`
  vocabulary), so only rendering separates them; it took a 4× crop comparison to settle.
- **`<simple-id>` is not available to this workbook.** The reference workbook carries one
  on every worksheet and window and ours had none, which made it the leading explanation
  for the missing colour legend. Adding it — the element alone, or together with the
  reference's `<document-format-change-manifest>` — fails the load with *"no declaration
  found for element 'simple-id'"* (`D2E8DA72`). The reference gets away with it only
  because its manifest switches the newer grammar on, and adding the manifest does not
  rescue us.
- **Still open: the colour legend.** Sheet 1's right-edge `type='color'` card is declared
  byte-for-byte as a working Public workbook declares it, and window cards **are**
  honoured (deleting the Marks card from the same block removes it from the UI), yet no
  legend draws. Ruled out by experiment: the worksheet grammar above, the reference's
  second `rows` strip, and the mark class — a Circle version of the same sheet shows none
  either, so it is not Polygon-specific. Remaining suspects are the extract-backed
  datasource and the XY-polygon view. The one-click fix is **Analysis → Legends → Colour
  Legend**, then Save; `docs/PUBLISH.md` carries the detail.

## 2026-10-17 — `Where poverty sits` is a real filled choropleth

The sheet that was a **scatter of 37 state capitals** is now filled polygons, verified
by opening the rebuilt workbook in Tableau Public 2026.2 and looking at it.

- **Tableau's generated geographic fields cannot be hand-authored.** Re-verified this
  session: referencing `[none:Latitude (generated):qk]` with no `<column>` declaration
  loads as *"does not exist in your database"* (`9CA7205B`); declaring it as a
  `<column>` in the datasource makes the whole workbook fail to open. Both attempts are
  recorded in `docs/PUBLISH.md`.
- **So the geometry ships as data.** Stage 4 now writes
  `data/processed/mpi_polygons.csv` — the ADM1 rings simplified by `shapely`
  (0.005 degrees, topology preserved): 53,489 vertices down to 7,089, with an area
  check per state so simplification cannot eat coastline. The table is
  `state`/`pcode`/`ring`/`point_order`/`lon`/`lat` plus the state's MPI fields per
  vertex. Stage 6 packages it as a fourth extract and the sheet uses mark **Polygon**,
  `AVG(lat)`/`AVG(lon)` with their `[Geographical]` roles, `state`+`pcode`+`ring` on
  Detail, **`point_order` on Path**, `mpi_band` on Colour. No geographic role drives
  the shape at all.
- `ring` and `point_order` must be integer **dimensions** and referenced as `:ok`.
  Referencing an ordinal as `:nk` gives the same `9CA7205B` error — verified.
- **Cosmetic:** a geographic sheet is drawn at a fixed map scale, so a short pane crops
  it. The `Equity Atlas` dashboard carries `<zoom type='entire-view' />` on that
  viewpoint (the Fit control as data, grammar taken from a real Tableau workbook) and
  now shows the whole country. **`<zoom>` on a worksheet `<window>` fails the whole
  workbook load** — do not put it there. The standalone sheet still opens at the default
  map scale; **Fit > Entire View** fixes it by hand.
- `build_hyper` now inserts 500 rows per statement. One INSERT per row was fine at
  37/148 rows and took >15 min at 53k.
- Also this session, unchanged in the workbook: `Party alignment and MPI change` is
  still standalone with mark labels on; `Dimension breakdown` is still three panels.
- **Measure decision (your call, 2026-10-17): the maps keep the MPI value, not H.** The
  spec asks for MPI incidence on the choropleth; it stays on `mpi_band` because the
  atlas's headline, `poverty_group`, `mpi_rank` and rank persistence are all MPI-value
  based, and both measures are equally unorderable (0/36 adjacent pairs separable at 95%
  on each). Recorded as spec correction #7 in `AGENTS.md`. **Resolved 2026-10-18:** the
  stage-5 preview PNG used to draw a continuous **H** ramp, a different measure from both
  maps; it now draws the five `mpi_band` bands on the MPI value in the same colours, so
  the gate, sheet 1 and the HTML map are three renderings of one chart.

## State in one paragraph

The atlas now has: a filled HTML map that fits every screen (`docs/preview/interactive_map.html`,
stage 7); a pre-registered party test (stage 8) whose result is **fragile — "we
can't really tell"**; and two plain-language reader sheets ("What the words mean",
"How we did it") in both the HTML page and the Tableau workbook, written once in
`scripts/atlas_text.py`. The Tableau workbook has 6 worksheets + 3 dashboards
(`Equity Atlas`, `What the words mean`, `How we did it`).

## What changed, by commit

| Commit | What |
|---|---|
| `152c13d` | Pre-registration of the party test (`docs/party_alignment.md` §1–§3). **Never edit §1–§3.** |
| `ac3b81e` `7041f4f` | `data/reference/governorship_events.csv` (231 seatings, every off-cycle/court date sourced), `governor_defections.csv` (24 sourced sitting-party changes), `federal_party.csv`; stage 0 gate recomputes `dom_party` exactly |
| `aeb3c0c` `4117988` `dae341b` | Stage 8 `08_party_alignment.py`: primary β +0.0080/yr, permutation p 0.036, CI −0.0002 to 0.0168, MDE 0.0115; fails (a) relative change, (c) binary, (d) sitting party p 0.079, and dropping any interval; holds only under (b). Rests on 2013–16. |
| `89a83e9` | Result in PNG, map panel, Tableau sheet "Party alignment and MPI change" |
| `f639c16` | CLAIMS / CAUSAL_DECISION §2d / AGENTS findings for party |
| `93b7c2e` | Map fit fix (was always clipped top+bottom), phone layout, plain-language party panel + "why we can't say it caused it" diagram, hover wording, "1 in 1" bug |
| `d4993b0` | Reader sheets (HTML + Tableau); **"five poorest states had zero events" corrected everywhere** — it is five *of the poorest 12* (Bauchi, Jigawa, Kebbi, Katsina, Kano); 10 of 37 states had none |
| this commit | `CLAUDE.md` (imports AGENTS.md) + this handoff |

## Verified by execution vs not

- **Verified:** run_all exit 0; stage 8 numbers reproduced independently by two
  reviewers; §1–§3 byte-identical to `152c13d`; workbook opens in Tableau Public
  2026.2 with title `Nigeria-MPI-Equity-Atlas`, no non-telemetry log errors; both
  reader dashboards render (top of each seen); HTML map fits at 1366×768 and
  390×844 with no sideways scroll; all 3 view buttons refit.
- **Not verified:** the *lower part* of the Tableau "What the words mean" dashboard
  (1000×4126 px) was never scrolled on screen — reviewer judged clipping unlikely
  from the zone-height code. The stage 7 cover hero itself (photo slot etc.) has
  been seen only incidentally.

## Next steps, in order

1. **Scroll both reader dashboards in Tableau** (5 min). Open the workbook
   (`C:\Program Files\Tableau\Tableau Public 2026.2\bin\tabpublic.exe tableau\Nigeria-MPI-Equity-Atlas.twbx`),
   go to *What the words mean* and *How we did it*, scroll to the bottom; if text
   is clipped, raise `READER_PAD` or the per-line factor in `_estimate_height`
   (`scripts/06_build_twb.py`) and rebuild stage 6.
2. **GUI fixes before publishing** (`docs/PUBLISH.md`): `Dimension breakdown` →
   stacked bar. The filled choropleth was done on 2026-10-17 — only the *standalone*
   map sheet still opens cropped (dashboard is fitted); **Fit > Entire View** on it.
   Optionally put the party sheet on the `Equity Atlas` dashboard (it is standalone
   now) and turn its mark labels off.
3. **Publish**: File → Save to Tableau Public. Paste attribution into the
   description. Then verify with the `tableau` MCP `get_workbook_image`.
4. **Host the HTML page** if wanted (it is self-contained, 8.5 MB, offline).
5. **Housekeeping:** `AGENTS.md` says "ruff clean" — not true: pre-existing
   findings 05=3, 06=4, 07=14 (run ruff from `scripts\`; from the root it
   misreads the `common` imports). The static preview PNG and the Tableau party
   sheet still use technical wording, not the plain-language version.
   `.codewhale/` is an unknown tool's state dir, untracked — gitignore or delete.

## Traps paid for this session (do not re-learn)

- **Tableau path changed:** 2026.2 at `C:\Program Files\Tableau\Tableau Public 2026.2\`.
  `C:\TableauPublic` no longer exists.
- **Capturing a Tableau dashboard:** SendKeys Ctrl+Tab does not reach Tableau.
  Instead build a scratch copy of the `.twbx` with the target dashboard's
  `<window>` moved to the top of `<windows>` (the twb uses CRLF), open it, and
  PrintWindow (flag 2). Opening the real file always lands on the first sheet.
- **Headless Chrome cannot draw the map** (mapbox needs WebGL); use the
  chrome-devtools MCP. Its `emulate` viewport change fires no resize event —
  reload after emulating, or the plot keeps the old width.
- **Never `git stash` while another agent has uncommitted work** — a stash during
  an executor's lint comparison made a concurrent stage 7 build emit an old page.
  Compare against HEAD with `git show HEAD:<file> > scratch` instead.
- **Two processes rebuilding `interactive_map.html` at once** corrupts it
  (`</body>` assertion fails). Run stage 7 from one place at a time.
- Subagents can stop on the usage cap mid-task without reporting — verify their
  work yourself before trusting it (this happened to the Tableau-dashboard executor).

## Rules that now apply (also in AGENTS.md / CLAIMS.md)

- Party: show the §3 sentence verbatim **with** its robustness line; the map
  panel leads with a plain-language reading generated from the result CSV.
  Never colour by party. Mode party is hover context only.
- Reader text lives only in `scripts/atlas_text.py`; every figure in it must trace
  to the repo or a cited OPHI source listed in its docstring.

---

# Handoff — session 2026-10-08 (interactive map: Sheet 1 CLI alternative)

Sheet-by-sheet rebuild started at Sheet 1. The Tableau map sheet cannot become a
filled choropleth from CLI (four blind XML attempts failed, documented in
`docs/PUBLISH.md`), so Sheet 1 now ALSO ships as a CLI-built interactive HTML map.
Tableau workbook untouched in structure; its Sheet-1 subtitle + tooltip fields improved.

## Built this session (all CLI, all in git after this commit)

- `scripts/07_build_interactive_map.py` → `docs/preview/interactive_map.html`
  (self-contained Plotly, ~8.5 MB, works offline): true filled ADM1 polygons,
  5 MPI bands, rich hover (MPI + 95% CI, annotated H/A, poor count, dominant
  party + winning years), All-37 / Poorest-12 / Other-25 buttons each with its
  own viewport fit, cover hero (title, flag bar, flag watermark, unity emblem,
  `cover.jpg` photo slot), honesty footnote.
- `data/reference/state_dominant_party.csv` + `docs/dominant_party.md`: mode
  governorship party 1999–2021 per state, 6 ties listed, full event matrix with
  counts, lineage notes, sources. Rule: one entry per seating event, as-won
  labels, later defections don't rewrite. FCT = no elected governor.
- `poverty_group` (Poorest 12 vs Other 25) added in `04_merge.py` →
  `data/processed/mpi_atlas_2021.csv`; Sheet-1 TWB subtitle + Detail/hover
  fields in `06_build_twb.py`; `.twbx` rebuilt, XML + Hyper validation passed.
- `docs/preview/nigeria_flag.png`: generated asset, embedded base64.

## Decisions (each challengeable, all recorded)

- **D6 cover framing:** rejected "tale of two zones" + northerner-vs-southerner
  imagery. Same rule as ever (AGENTS.md/CLAIMS.md): the 12 poorest ARE the
  northern states at n=37, so zone framing is the same observations wearing a
  geographic label. Cover reads "One country, two realities — poorest states
  vs the rest", no zone labels on imagery.
- **Party is hover-only, never colour** (causal paths closed at n=37).
- **Lagos AD/APC "tie"** is one camp under four labels (AD→AC→ACN→APC),
  counted as-won and noted in `docs/dominant_party.md`. Same for AC/ACN/APC
  fragments in Ogun/Osun/Oyo. **Kwara 1999 recorded APP** (governor list prints
  ANPP; APP is the contemporary platform, same rename as sibling states).
- **2021 endpoint, Fourth Republic only** (1999–2021 governorships; 1991–93
  Third Republic excluded as incomparable).

## Root causes found (do not re-debug)

- `go.Choropleth` on the geo subplot draws a **full-frame rectangle inside
  every path** (proven via live DOM: 37 unique `d` strings, each prefixed with
  the frame rect; viewport colour = last state's band). Fix used: render
  through `Choroplethmapbox` with top-level feature `id`s.
- **carto-positron tiles now need an API key** (watermarked background) →
  `style="white-bg"`, fully offline.
- Plotly hover honours `<b>/<i>/<br>` only; span colours don't survive →
  hierarchy via weight + slant, chrome via `hoverlabel`.
- **Preview serving: NEVER `python -m http.server`** for the 8.5 MB file —
  single-threaded head-of-line blocking hangs the terminal and times out the
  tool call (this session, twice). Pattern that works: temp
  `threaded_server.py` (ThreadingHTTPServer) + `-RedirectStandardOutput`, kill
  afterwards. Launching even that hung at session end — see unverified note.

## ⚠ Verification status — what is PROVEN vs NOT

- PROVEN (screenshotted in headless browser): filled polygons all 37, band
  colours, buttons + per-view viewports with no edge clipping, toggle filter,
  styled hover incl. Lagos tie, Kaduna/Bauchi/Oyo/Abia hovers, party-years lines.
- NOT verified: the final cover build (new 🇳🇬 title, button explainer line,
  flag watermark, cover hero, photo slot, removed on-map labels, annotated
  hover metrics). It completed the build script exit-0 but was never rendered
  before the preview server stopped cooperating. **Next session: serve
  `docs/preview/interactive_map.html` and screenshot top (cover) + map +
  one hover before touching Sheet 2.** Rebuild: `& C:\Users\TOSHIBA\ds-general\python.exe scripts\07_build_interactive_map.py`.

---

# Handoff — session 2026-10-06

State of the project at the end of this session, written for whoever picks it up
next: a new agent, a collaborator, or future me after context is lost.

**This session changed the project's claim, not its code.** The pipeline is
unchanged and still runs clean end to end. What changed is that we now know which
of our findings survive scrutiny, and the answer was not the one we assumed.

---

## 0. Start here

**The workbook builds and opens in Tableau. It is not published. And it currently
makes three claims it cannot support.** Read these four documents before touching
anything:

| Document | What it is |
|---|---|
| `docs/CAUSAL_DECISION.md` | **The decision.** Why the atlas makes no causal claim, what it makes instead, and the five independent reasons every causal path is closed |
| `docs/CLAIMS.md` | **The permission table.** What may be said, what is blocked and why, with wording |
| `docs/FIX_LEDGER.md` | **The defect list.** 6 blockers + 8 workbook defects, severity-ranked, plus what is *not* a defect |
| `docs/HANDOFF.md` §7 | Environment, traps, command cookbook |

Then the shortest useful next action:

```powershell
& C:\Users\TOSHIBA\ds-general\python.exe "scripts\06_build_twb.py"
& C:\TableauPublic\bin\tabpublic.exe "tableau\Nigeria-MPI-Equity-Atlas.twbx"
```

and look at the map. Still the one visual nobody has seen.

---

## 1. What this session did

| | |
|---|---|
| **Read** | Every shelf, mark and encoding out of `tableau/Nigeria-MPI-Equity-Atlas.twb` — not from the docs, which were wrong |
| **Found** | OPHI publishes standard errors in the file the pipeline already downloads; all 36 adjacent rank pairs overlap at 95% |
| **Tested** | Every claim a reviewer would attack, in R, including the falsification test the literature predicts |
| **Researched** | Two adversarial reviews — Tableau viz criticism, and MPI methodology — against primary sources |
| **Wrote** | 3 new docs; corrected 4 false claims in `AGENTS.md` and `HANDOFF.md` |
| **Extracted** | `data/interim/mpi_se_ci.csv` — 37 states × SE, CI bounds, H SE |

Uncommitted working tree. `git log` is not yet the full story.

---

## 2. The four findings that changed the project

### 2a. The standard errors were there all along

`subnational-results-mpi.xlsx` sheet `5.4 SE & CI Region` — the file stage 1
already downloads. Median relative SE **15.1%**. Consequence:

> **All 36 adjacent rank pairs have overlapping 95% intervals. 0 of 36 are
> distinguishable.** Bauchi 0.4411 ± 0.0322 vs Jigawa 0.4377 ± 0.0250 → z = 0.08.

"Bauchi has the highest MPI" — currently asserted in `AGENTS.md`,
`HANDOFF.md` §5 and on the map — is **not a statement the data supports**.
Median CI width (0.075) is 81% of the median MPI value.

### 2b. The north-west / south-east finding is mislabelled

Our own headline: *"the north-west is driven by education and living standards;
the south-east by health."* Tested it:

| Sample | corr(latitude, education contribution) |
|---|---|
| All 37 | +0.850 |
| Not-poor states (n=25) | +0.794 |
| **Poor states (n=12)** | **−0.252** |

All 12 states with MPI > 0.20 sit in the two northern latitude bands; zero sit in
the southern two. At n = 37, "poor" and "northern" are **the same 12
observations**. The gradient is carried entirely by the rich southern states and
does not hold inside the group that matters.

**It is a poverty-level contrast wearing a geographic label.** Say "poorest
states vs the rest". Patched in both files.

### 2c. The climate layer is geography, and we were reporting it as climate

| Correlation | rho |
|---|---|
| baseline precipitation ↔ **latitude** | **−0.903** |
| latitude ↔ MPI | **+0.821** |
| baseline precipitation ↔ MPI | −0.801 |

Latitude predicts MPI *better* than precipitation does. Precipitation is the
outcome's twin. OPHI's own 2025 report used gridded **hazards** (heat, drought,
flood, air pollution) on a harmonised geometry — a strictly stronger design than
37 capital point-samples of annual totals.

### 2d. A documented bug does not exist

`HANDOFF.md` §3d and `PUBLISH.md` both list "contrib values are 0–1 fractions on a
0–100 axis" as an open defect. Per-state sums are **99.99–100.01**. They are
already percentages. The docs were wrong; the workbook is fine.

---

## 3. Why the atlas makes no causal claim

Full reasoning in `docs/CAUSAL_DECISION.md`. Five independent closures, each fatal
alone:

1. **Collinearity** — all 12 poor states are northern; nothing separates the two
   readings.
2. **The within-poor trend reverses** (−0.252).
3. **No temporal ordering** — MPI(t) → conflict(t+1) gives rho −0.073, +0.107,
   +0.017. All p > 0.45. Fearon & Laitin predict a signal; there isn't one.
4. **Panel FE would absorb 91% of variance** — within-state change is 9.1% of
   the cross-state spread. The one available escape is empty.
5. **No instrument, no discontinuity, no exogenous shock.**

**What survives is a decomposition claim**, because the MPI is H × A by
construction and the dimension contributions are an *identity*, not an inference:

| Finding | Value |
|---|---|
| Rank persistence | 0.922, 0.924, 0.867 |
| Education share: poorest 12 vs other 25 | 39.9% vs 22.3% (**17.6 pts**, p = 1e-5) |
| Health share: poorest 12 vs other 25 | 16.3% vs 31.3% (**15.0 pts**, p = 0.006) |

The 17.6-point gap is the headline. A 15% relative SE kills every *ordering*
(all 36 adjacent pairs overlap) but not a *group contrast* — that is the whole
argument for leading with it.

**The strongest defensible sentence:** level fell, structure held, and structure
differs by poverty level in a way that points at different interventions.

---

## 4. Would upgrading UCDP get us data? Investigated — mostly no

The honest answer, since it was asked: **we already have the upgrade, and it does
not rescue the null.**

**Already in `data/raw/ucdp_ged_nga.csv`, never used:**

| Field | Coverage |
|---|---|
| `adm_2` (LGA) | **88.1% of events, 445 distinct LGAs** |
| Name hygiene | Zero values containing "state", "rural" or "jhz" |
| `low` / `best` / `high` | **6,120 of 6,120 events have all three** |
| `where_prec` | 69.8% at exact-or-near location |

**Why it cannot fix the present null:** the state-level event count is *identical*
whatever geography you use — LGA disaggregation only redistributes events within
a state. And **all 10 zero-event states in 2021 are zero at LGA level too**
(Bauchi, Kano, Katsina, Jigawa, Kebbi, Kogi, Edo, FCT, Cross River, Bayelsa —
verified, 0 events each). The coverage failure is in the source, not the
aggregation. No amount of re-cutting fixes it.

**What upgrading *does* buy, and it is real:**

1. **Fatality-band robustness — publishable today.** The null is stable across
   a ±50% casualty band:

   | 2021 measure | rho with MPI | CEI top | 2nd |
   |---|---|---|---|
   | `low` | +0.065 | Borno (100) | Benue (10.1) |
   | `best` | +0.026 | Borno (100) | Yobe (12.2) |
   | `high` | −0.011 | Borno (100) | Yobe (11.7) |

   "Our null is not an artefact of the casualty estimate" is a defensible claim
   we can make today. Also: `high/best` widens over time (1.30 in 2013 → 1.75 in
   2021) — material for any future panel work.
2. **Better future design.** LGA-level conflict + LGA-level MPI (NBS designed the
   2022 survey for 109 senatorial districts) puts outcome and treatment at the
   *same* unit, which dissolves closure 1 above. That is the only route to a real
   causal claim. It is a different project, not a stage-7 change.

**Bottom line:** do not chase ACLED, do not chase LGA for this viz. Carry the
fatality band through (cheap, it makes a robustness claim visible) and record the
LGA route in the docs.

---

## 5. Next steps, in order

Nothing below is aesthetic. Aesthetics are last, and `docs/FIX_LEDGER.md` §C.

### 5.1 Decisions needed (blocking)

| # | Decision | Options |
|---|---|---|
| **D1** | **A4 — MPI series.** The rounds are *standardised* (HDX resource description confirms). OPHI: "may not be comparable across time". | (a) Re-source from the harmonised series (Data Table 6 / HDX trends); (b) keep and drop the word "fell" |
| **D2** | **Climate layer.** | (a) Relabel as gradient and state the latitude correlation beside it; (b) drop the layer and keep three sheets |
| **D3** | **Conflict sheet framing.** | (a) Keep as a documented null with power + band robustness; (b) drop |

Recommendation on D1: **(b)**. Re-sourcing is a download and a re-merge, and the
level numbers would move. The rank-persistence finding — the one we want to lead
with — is a within-file comparison and is unaffected either way. Take the re-source
only if the harmonised subnational tables turn out to carry all 37 states.

### 5.2 Data and code (unblocked, mechanical)

1. **Wire the standard errors through.** Stage 1 reads sheet `5.4`; stage 4 passes
   `mpi_se`, `mpi_lo`, `mpi_hi`, `headcount_se` into `mpi_atlas_2021.csv`; stage 6
   declares them as columns. *(`data/interim/mpi_se_ci.csv` already extracted.)*
2. **Carry the fatality band.** `conflict_state_year.csv` already has
   `fatalities_low` and `fatalities_high`; pass them to the extract.
3. **D1 — `Poverty over time`.** `state` is a second discrete field on Columns, so
   Tableau draws 37 single-point panes. Move to Colour. Ship the trend.
4. **D2 — `Dimension breakdown`.** Measure Names on Columns / Measure Values on
   Rows. Colour by dimension, not by `contrib_health_pct`.
5. **D3–D6 — encoding fixes.** Drop size from `Incidence vs intensity`
   (corr with x-axis = +0.942); fix or rename the `quadrant` cut (H spans ×68, A
   spans ×1.6); size `Poverty vs conflict` by per-100k not raw count; `quadrant` →
   Shape (WCAG 1.4.1).
6. **D7 — dashboard text zone + KPI tiles.** This is where all six caveats must
   live. Highest value-per-hour item in the list.
7. **D8** — `fatalities_per_100k` typed as string in the panel datasource.

### 5.3 Documentation

- `docs/PUBLISH.md` — remove the phantom `contrib_*_pct` bug; add the two new
  caveats; update the sheet table after D1–D3 land.
- `docs/data_quality.md` — rewrite item 1: Health is **re-weighted to a full
  one-third**, and cross-country comparison is therefore forbidden.
- `docs/PUBLISH.md` attribution block — add OPHI MN 62, Table 5.4 as the SE source.

### 5.4 Never verified

**That the map draws Nigeria's 37 polygons.** Still first. Everything else is
downstream of knowing the workbook renders.

---

## 6. What is *not* a defect

Confirmed clean. Each was a likely criticism; none applies. Full list in
`docs/FIX_LEDGER.md` §D — do not "fix" any of these.

- No rainbow colour map. No 3D. No dual axes. No pie charts. No truncated axes.
- The map encodes a rate, not a count — the most common choropleth sin, avoided.
- The choropleth is **not** a WCAG 1.4.1 colour-only violation: a sequential ramp
  varies lightness, which W3C counts as an additional distinction.
- State-vs-national comparison **is** permitted — OPHI MN 56, decomposability.
  Much of the standard advice to the contrary does not apply here.
- Nigeria passed OPHI's subnational criteria (≥85% national / ≥75% per-region
  retained sample, bias analysis). Say so — it converts "no uncertainty shown"
  into "the publisher's own bar was met".
- The six XML defects found by loading in real Tableau are fixed and committed to
  the working tree; the workbook loads and renders.

---

## 7. Environment

- Python: `C:\Users\TOSHIBA\ds-general\python.exe`. Bare `python` is `C:\Python314`.
- Tableau Public Desktop 2025.1: `C:\TableauPublic\bin\tabpublic.exe`. Installed.
- R 4.5.2 via `Rscript`; the `rmcp` server works and is the fastest way to audit
  statistics. **`dplyr` is allowlisted; `psych` is not** — `partial.cor` is
  unavailable, use rank-based contrasts instead.
- `ruff` is **not** installed in `ds-general`. Lint via a different route or skip.
- Shell state does not persist between calls. Chain with `;` / `&&`.
- `D:\` is a **removable USB SSD**. Copy to `C:\Users\TOSHIBA` before unplugging.
- Full machine map: `ENVIRONMENTS.md` (local only, gitignored by design).

**Traps already paid for** — full list in `docs/HANDOFF.md` §4. The short ones:
`data.hdx.humdata.org` does not resolve (use `data.humdata.org`); do not fetch the
Tableau installer from `tableau.com` (403, use winget); the agent shell is not
elevated; `Get-Content` not `ReadAllLines` on Tableau's log file.

---

## 8. References behind this session's judgements

**Methodology of the index**
- Alkire, S. & Foster, J.E. (2011). "Counting and multidimensional poverty
  measurement." *Journal of Public Economics* 95(7–8): 476–487.
- Alkire, S., Mishra, R., Selden, L. & Suppa, N. (2025). *Global MPI 2025:
  disaggregation results and methodological note.* OPHI Methodological Note 62.
  — **source of Table 5.4, the standard errors, and the disaggregation criteria.**
- OPHI Methodological Note 58 (2024) — "may not be comparable across time."
- OPHI Methodological Note 56 (2023) — decomposability; state vs national.
- OPHI Methodological Note 63 (2025) — DHS/MICS harmonisation.
- UNDP & OPHI (2024). *Global MPI 2024: Poverty amid conflict.*

**The conflicts we found with ourselves**
- Djankov, S. & Reynal-Querol, M. (2008). "Poverty and Civil War: Revisiting the
  Evidence." CEPR DP 6980. — the cross-sectional correlation is not the estimand.
- Fearon, J.D. & Laitin, D.D. (2003). "Ethnicity, Insurgency, and Civil War."
  *APSR* 97(1): 75–90. — the recruitment channel we tested (null).
- Abidoye, B.O. & Calì, M. (2021). "Income shocks and conflict: evidence from
  Nigeria." *Journal of African Economies* 30(5): 480–509. — the identification
  strategy we do not have.
- UCDP GED Codebook v24.1. — media-construction and spatial-coverage limits.
- Sbarra, N. et al. (2023). *Scientific Reports* 13:11085. — Borno estimates not
  state-representative.

**The climate and ecology reasoning**
- Burke, M., Hsiang, S. & Miguel, E. (2015). "Global nonlinear effects of
  temperature on economic production." *Nature* 527: 235–239.
- Dell, D.C., Jones, B.D. & Olken, A.B. (2009). "Temperature and Income."
  *AER* 99(2): 198–204. — cross-sections overstate; the heterogeneity is ours.
- Lavers, A. & Villarini, G. (2022). "An evaluation of ERA5 precipitation."
  *QJRMS*. — the wet bias and the missed orographic enhancement.
- Robinson, W.S. (1950). "Ecological Correlations." *ASR* 15: 351–357.
- Openshaw, S. (1983). *The Modifiable Areal Unit Problem.* CATMOG 38.

**Visualisation criticism**
- Beconytė, V. et al. (2022). "Where Maps Lie." *ISPRS IJGI* 11(1): 64.
- Schiewe, J. (2019). *CaGIS* — small areas missed by 30–40% of map users.
- Cleveland, W.S. & McGill, R. (1985). *Science* 229: 828–833.
- Bradley, W. (2023). *IJGIS* — viewers read magnitude off the legend range.
- Crameri, F., Kok-Slok, S. & Le Blanc, S. (2020). *Nature Communications* 11:5444.
- W3C. WCAG 2.1 SC 1.4.1, SC 1.4.11.
- Tableau, *Visual Analytics Best Practices: A Guidebook*.

---

## 9. Honest assessment

The pipeline is good — reproducible, gated, every source reconciled, 37/37
asserted at every stage, 7,418 events attributed with 0 unattributed, a sign flip
that killed a single-year approach. **None of that is visible to a published
viewer**, which is the actual opportunity.

The spec asked for a choropleth, a stacked bar, two scatters and a radar. It did
not promise identification. Adopting a causal framing we cannot support would be
volunteering for a fight nobody asked us into — and it would cost us the two
overlays that make the viz interesting in exchange for nothing.

One defensible finding beats three undefendable ones. Lead with the group
contrast; keep the conflict layer as an honest null with its power floor attached;
drop or relabel the climate layer; and put the caveats on the canvas where a
reviewer will actually read them.
