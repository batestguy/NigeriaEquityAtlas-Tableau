# Publishing to Tableau Public

Tableau Public has **no write API and no publishing CLI**. `tabcmd` targets Tableau
Server/Cloud, not Tableau Public, and the `tableau` MCP server available here is
read-only (search, metadata, download). Publishing is a GUI action behind an
interactive account login, so this is the one step that has to be done by hand.

Everything up to that point is automated and reproducible: `scripts/06_build_twb.py`
produces a validated `.twbx` with the data packaged inside it.

## What is already built

`tableau/Nigeria-MPI-Equity-Atlas.twbx` contains:

```
Nigeria-MPI-Equity-Atlas.twb     the workbook
Data/mpi_polygons.hyper          7,089 rows, the simplified ADM1 ring vertices the poverty map draws
Data/spatial_polygons.hyper      7,089 rows, the same rings + the neighbourhood type, for the cluster map
Data/mpi_trends_panel.hyper      148 rows (4 harmonised rounds x 37 states), the "A state over time" panel
Data/pairs_board.hyper           148 rows, the pairs board's extract (docs/SHEET_PAIRS.md)
Data/dimension_shares.hyper      37 rows, the three dimension shares per state, for the composition bar (docs/SHEET_DIMENSIONS.md)
```

Five extracts and nothing else. The atlas, party-alignment and spatial-diagnostic
extracts were packaged until 2026-10-18, when the sheets that drew them were withdrawn
(`docs/FIX_LEDGER.md` W1); those `.hyper` files are no longer built or packaged, and
stale copies of them from an earlier build may still be sitting in `tableau/` — they are
gitignored artefacts, so delete them if the folder still lists them. The trends-panel
extract came back on 2026-10-20 as `mpi_trends_panel.hyper` feeding the new sixth view
(`docs/SHEET_TIME_PANEL.md`), and `kpi_dots.hyper` arrived with the KPI board on
2026-10-23 (`docs/SHEET_KPI.md`).

**Tab 1 is the `Overview` dashboard** (2026-10-24, `docs/DASHBOARD.md`): a fixed
1600x1000 page carrying `Where poverty sits`, `Where poverty clusters` and
`How poverty is made up`, with a title-band text zone. It is the page the workbook
opens on, so a viewer meets the country before the tab bar. Its three panels are
the card-independent sheets only — filter/parameter/legend cards are window objects
and do not travel into a dashboard.

The data ships as **Hyper extracts**, not CSV. Tableau Public refuses any workbook whose
datasource is not an extract (*"Workbooks saved to Tableau Public must use extracts"*,
error `3C242D89`) and it does **not** convert a live file on save. Stage 6 writes both
extracts itself with `tableauhyperapi` and validates the schema it wrote back against
the declared columns before packaging.

Stage 6 writes each extract itself with `tableauhyperapi` and validates the schema it
wrote back against the declared columns before packaging.

**The tabs, in tab order** (view 3 added 2026-10-22, view 8 joined 2026-10-21,
view 9, the KPI board, joined 2026-10-23):

| Tab | Type (mark class) | What it carries |
|---|---|---|
| Where poverty sits | **filled map (*Polygon*)** | `AVG(lat)` on Rows, `AVG(lon)` on Columns (both `[Geographical]` roles, so the sheet stays a geographic map); `state` + `pcode` + `ring` on Detail; `point_order` on **Path**; `mpi_band` on Colour; `state` on Text. Datasource: `Nigeria MPI polygons`. Hover carries `mpi`, `mpi_se`, `mpi_ci_lo`, `mpi_ci_hi`, `headcount_ratio_pct`, `intensity_pct`, `mpi_poor_thousands`, `poverty_group`, `mpi_pct`, `mpi_ci_lo_pct`, `mpi_ci_hi_pct`, `gov_party` |
| Where poverty clusters | **filled map (*Polygon*)** | the same shelves, from `spatial_polygons.csv`: `spatial_group` on Colour, `mpi_pct` + `spatial_lag_mpi_pct` + `neighbours` on Detail for the hover. Datasource: `Spatial polygons`. **Descriptive, not a significance map** — one state survives the correction, so a significance map would be one state; the count is in the hover |
| How poverty is made up | **stacked bar (*Bar*)**, one per state | the three dimension shares on Measure Names / Measure Values from `dimension_shares.hyper`: `state` on Rows, the generated field on Columns, Colour = Measure Names, the three-member union filter, bars ordered by a **manual sort dictionary** hand-computed from the atlas MPI (the MPI value itself is NOT in the extract). **Default view (2026-10-22, the user's decision): the five poorest states and the first twelve of the Other 25 - 17 bars - with all 37 readable on the interactive left-rail `state` checklist card (`(All)` adds everything in one tick; 17 pre-ticked; the manual MPI order survives the filter). Rows nest `poverty_group` above `state`, so the sheet prints a **"Poorest 12" block and an "Other 25" block with a pane divider** between them (`docs/SHEET_DIMENSIONS.md`).** The segment value labels are **bold white** via a pane-level `<style-rule element='datalabel'>` (`color-mode='user'`), the Label card's custom colour, so the numbers read on the dark green/orange/blue fills. Hover: state, `mpi_label`, the segment's area name, `dim_hover` (the full split, pre-formatted) + the caveat. Datasource: `Poverty composition` (`docs/SHEET_DIMENSIONS.md`) |
| A state over time | **small-multiple lines (*Line*)** | the Measure Names / Measure Values panel from `mpi_trends_panel.hyper`: one pane per monitored measure × four rounds, Bauchi default via the `state` filter, the six-measure whitelist via the Measure Names union filter, both exposed as interactive cards on the **left** rail (right-edge cards do not draw in packets built by stage 6). No trend is fitted anywhere; the hover annotates `survey`, the annualised `mpi_change_since_prev`, the `mpi_change_significant` stars and `fatalities_per_100k_high` (`docs/SHEET_TIME_PANEL.md`) |
| What the words mean | **text zones** (part 1 of 3) | the reference table, 24 rows: the word, its formula or weight, what it means, how it was made |
| The list of basic needs | **text zones** (part 2 of 3) | the same three columns, 11 rows: the nine needs in three areas, each with its weight and what counts as missing |
| How we did it | **text zones** (part 3 of 3) | the same three columns, 9 rows: a worked step per section, from the survey to the party question |
| Where Nigeria stands | **silhouette board (*Shape*)**, one row per benchmarked KPI | the KPI board from `kpi_dots.hyper` (stage 7): 7 benchmarked national KPIs and their reference points = **20 map silhouettes — a green Nigeria map, a blue Africa map, and an amber globe carrying vertical meridians only (2026-10-24 pass: Okabe-Ito `#E69F00`, orthographic meridians instead of coastlines; the lines ride on alpha, so the colour card paints them lighter — see `docs/SHEET_KPI.md` built record, `FIX_LEDGER.md` K3/M5)** — on a shared axis that is each row's own scale (`pos = value / the row's largest reference`; stage 7 normalises and **dodges** marks that would collide, keeping the row maximum at 1.0 — the printed number is the TRUE share, a pre-formatted `pos_label` string on the Label pill at **6 pt** with `mark-labels-cull` as the backstop; each row header ends in a **direction arrow**, `▼` lower is better / `▲` higher is better, asserted against the benchmarks CSV's `direction`; the header column is pinned to 230 px by the composition sheet's field-scoped width rule; the axis' own tick rule (`major-spacing='0.5'` → 0 / 0.5 / 1) is still **screen-unverified** — delete `kpi_table_style()`'s axis rule if inert at publish; hover carries the actual values at one decimal with the benchmark text and the source, pre-formatted). The images are **embedded in the workbook** inside `<external><shapes>` (`KPI_Geo/…`, mapped member-by-member by the ds-level `type='shape'` rule, `docs/SHEET_KPI.md`), so publishing needs no Shapes-repository copy; the optional authoring copy into `My Tableau Repository\Shapes\KPI_Geo` is written by stage 7 when the shell may write there and restores nothing if the workbook is re-fetched. Colour = `series` via a ds-level palette (`atlas_text.KPI_SERIES`), rows in the benchmarks table's order via a manual sort dictionary (headcount first; marks ordered so Nigeria draws last/on top). National figures only, no state panel; `docs/SHEET_KPI.md` carries the can/may-not list and the pending packet checks |
| How measures pair | **point cloud (*Circle*)**, one pane per state-round pair | the pairs board from `pairs_board.hyper`: both axes driven by the inline Parameters dropdowns; circles filled **one green** (`#009E73`, `atlas_text.PAIRS_POINT_COLOUR`) via a pane-level `<format attr='mark-color'>`, no colour pill and therefore no colour legend; **one quadratic trend line per pane with its 95% confidence band** (`<trendline fit='polynomial' degree='2' enable-confidence-bands='true'>`, painted `#4D4D4D` by a pane-level `<style-rule element='trendline'>`; asked for in white, which is invisible on the white pane — `docs/SHEET_PAIRS.md` "Trend line", 2026-10-24), **instant analytics off so the hover cannot print the model equation**; hover = **the state name only**; looking only — the line describes each pane's own marks, so **no slope, coefficient, correlation or claim is printed** (`docs/SHEET_PAIRS.md`) |

The three reference tabs are **one table paginated on its own groups**, not three
documents. It was two prose dashboards (`What the words mean`, `How we did it`) until it
was merged into a single three-column table on 2026-10-18, and then split because the
merged version measured **2000 x 8720 px** — thirteen screens on the 687 px window it
was reviewed in (`docs/FIX_LEDGER.md` W2). Each part repeats the intro and the column
headers on purpose, so a reader who arrives on part 3 from the tab bar is told what the
columns are. It is a layout of text zones by design: a datasource-backed text table of
paragraph-length cells would paginate itself around the reader, not by the groups the
table already had. (The Measure Names / Measure Values pair itself *does* render from
hand-written XML — the time panel is built on it since 2026-10-20 — the earlier "could
not make it render" claim applied to a filtered text table and is retired.)

**Verified by opening the workbook in Tableau Public 2026.2 and looking at it:** the
poverty map and the five spec sheets on 2026-10-06; the party sheet and the reader
dashboards on 2026-10-09/10; the cluster map and all three reference parts on
2026-10-18, and then the **shipped** workbook of that date — window title
`Tableau Public - Nigeria-MPI-Equity-Atlas` (not `Book1`), tab bar exactly
`Where poverty sits` / `Where poverty clusters` / `What the words mean` /
`The list of basic needs` / `How we did it`, no error dialog, the poverty map drawing the
red ramp under white state strokes, and the cluster map drawing grey north / deep teal
south / purple Nasarawa with its colour card. On **2026-10-20** the shipped workbook
opened again with the sixth view in place: tab bar
`Where poverty sits` / `Where poverty clusters` / `A state over time` / `What the words
mean` / `The list of basic needs` / `How we did it`, the time sheet drawing "24 marks,
6 rows by 4 columns" (six whitelist measures × four rounds, lines connecting, labels on
marks), the subtitle in full, the state dropdown pinned to `Bauchi`, and the Measure
Names checklist showing the six whitelist measures ticked with
`fatalities_per_100k_high` and the generated system fields unticked. In each case what
was checked is the top of
the tab at a 1295x687 window — the reference parts have not been scrolled to the end on
screen, and neither map has been panned. The third column of the reference table, which
the window is too narrow to show, was read end to end in a review copy that keeps that
column and drops the other two. The time panel was additionally reviewed as a
**single-worksheet packet** (`%TEMP%\opencode\review_time_only.twbx`, built by
`%TEMP%\opencode\make_time_only.py` — one worksheet, no dashboards, one window), which
removes the tab-bar ambiguity entirely and is how the render findings in
`docs/FIX_LEDGER.md` §H were observed.

**Tab order is the `<windows>` order**: `Where poverty sits`, then `Where poverty
clusters`, then the three reference parts. **Which tab opens is not dependable, though:**
Tableau Public follows the first `<window>` on load most of the time, and the exceptions
are not explainable from the file (the same generated workbook opened on its second
window once). Treat the workbook as opening *on the maps*, and click the tab you want —
and do not try to script that click: the padded `PrintWindow` capture's pixels are not
window coordinates under DPI virtualization, and two clicks computed from the same
capture landed on different tabs. To get one view reliably, `%TEMP%\opencode\review_tab.py
"<tab name>"` rebuilds the package with a single `<window>` (and, with `right` as a second
argument, with the third column moved to x=0, which is how a column wider than the canvas
can be read at all).

## Steps

**Tableau Public Desktop 2026.2 is already installed** at
`C:\Program Files\Tableau\Tableau Public 2026.2\bin\tabpublic.exe`
(`winget install --id Tableau.Public -e`). Nothing to do here. The old
`C:\TableauPublic` (2025.1) path no longer exists. To reinstall on another machine
use the same command — not the vendor site, where
`tableau.com/downloads/public/pc64` and `downloads.tableau.com` both return
**HTTP 403** on this network.

Do **not** install Tableau Desktop (the paid product): a different application,
cannot open modern workbooks on an older release, and cannot save to Tableau
Public. See `docs/HANDOFF.md` §3b.

1. Sign in to your Tableau Public account.
2. Open `tableau/Nigeria-MPI-Equity-Atlas.twbx`. **It has been opened successfully on
   this machine** — it loads with no error dialog and renders (see `HANDOFF.md` §3).
   Re-verified 2026-10-23 on the current build: title reads `Nigeria-MPI-Equity-Atlas`
   and the KPI board's 20 silhouette marks draw (in-app PrintWindow captures). Open
   it the way the file association does — double-click, or `Invoke-Item` in
   PowerShell: a direct `tabpublic.exe <path>` argument launch opens an empty
   `Book2` on this machine even though the file is fine (`FIX_LEDGER.md` K1). If
   loads start failing with recovery/extract dialogs, purge the autosave state
   first (any `*.twbr` beside the .twbx, the
   `HKCU\...\Tableau Public 2026.2\Autosave File Map` registry values,
   `%TEMP%\TableauTemp\`), then relaunch.
3. **File > Save to Tableau Public.**
4. Wait for the upload and the render, then open the live URL and confirm all **ten tabs**
   (the `Overview` dashboard first, then the nine views) and that `Where poverty sits`
   draws the filled choropleth, not a scatter of points. Fetch it with the `tableau` MCP
   `get_workbook_image` rather than trusting the upload dialog.

## The map, and why it is drawn from shipped geometry

**`Where poverty sits` is a filled choropleth as of 2026-10-17**, verified by opening
the rebuilt workbook in Tableau Public 2026.2 and looking at it.

It is **not** built on Tableau's geographic engine. Tableau's generated geographic
fields are synthesised by the application and cannot be hand-authored at all:

| Attempt | Result |
|---|---|
| `cols = state / SUM(lat) + SUM(lon)` | 74 small lat/lon **bar charts**. This shipped for the workbook's whole life; the handoff called it "renders". |
| `[none:Latitude (generated):qk]` on the shelves, no `<column>` declaration | **Failed to load**: *"The field '[none:Latitude (generated):qk]' in the datasource 'federated.0mpiatlas2021' does not exist in your database"*, error `9CA7205B`. Re-verified 2026-10-17. |
| The same fields declared as `<column>` in the datasource | **Worse**: *"Errors occurred while trying to load the workbook"*. The workbook does not open at all. |
| Geographic role on `state` alone, no coordinates | 37 coloured numbers as a **text table**. |
| `AVG(lat)` / `AVG(lon)` with `[Geographical]` roles (the previous shipped sheet) | Works, but it is a **scatter of 37 capital points**, not polygons. |

The reference workbook the schema was originally taken from
(`ClimatechangeprofileNigeria`) turned out to draw its "map" as a **background image**
(`Image/nigeria.png`), so it never had the idiom to copy either.

**What ships instead.** Stage 4 writes `data/processed/mpi_polygons.csv` — one row per
vertex of each geoBoundaries ADM1 ring, with `state`, `pcode`, `ring`, `point_order`,
`lon`, `lat` and the state's MPI fields carried per vertex. The rings are simplified
with `shapely`, tolerance 0.005 degrees and `preserve_topology=True`: the raw file's
53,489 vertices come down to 7,089, which is sub-pixel at the map zone's scale and keeps
the committed table at 762 KB. Stage 4 asserts every state stays within 2% of its
original area, so the simplification cannot quietly eat coastline. Stage 6 packages the
result as `Data/mpi_polygons.hyper` and the sheet draws it with a **Polygon mark plus a
Path field**:

- `AVG(lat)` on Rows, `AVG(lon)` on Columns — the column names matter: `col_block`
  gives `lat`/`lon` their `[Geographical]` roles, so the sheet is still a geographic
  map rather than a plain XY plot.
- `state`, `pcode` and `ring` on Detail. `ring` keeps a state's disjoint parts (Nile
  delta islands, riverine fragments) from being joined into one polygon.
- `point_order` on **Path** closes each ring. It is an integer *dimension*
  (`type='ordinal'`), so it must be referenced as `[none:point_order:ok]`; referencing
  an ordinal as `:nk` produces the same `9CA7205B` "does not exist" error.
- `mpi_band` on Colour, `state` on Text.
- The state outlines are the polygon **stroke**, declared on the sheet's *worksheet-level*
  mark style rule: `has-stroke='true'`, `stroke-color='#FFFFFF'`, `stroke-size='3'`.
  The obvious-looking `border-color`/`border-width` pair is **inert** on a mark — the
  workbook loads and renders identically with and without it, at both worksheet and pane
  scope (compared pixel-for-pixel against a 4× crop, 2026-10-18). `border-*` styles the
  borders of table cells and headers; a polygon's outline is a stroke. Both names sit in
  the published schema's `StyleAttribute` vocabulary, so a schema check does **not**
  distinguish them — only rendering does. Without the stroke the states read as one field
  of colour and you cannot tell which one the cursor is over.

**Colour is the MPI value, not incidence (H).** The spec's visual table asks for
"State → MPI incidence", but both maps colour by the MPI value in five bands and carry H
in the tooltip. `poverty_group` (Poorest 12), `mpi_rank` and the rank-persistence figures
are all built on the MPI value, so colouring by H would key the fill to one measure and
the hover to another; the band cut is justified by OPHI's *published* SEs for the MPI
value; and neither measure is orderable anyway (0 of 36 adjacent pairs separate at 95% on
both). It is recorded as correction #7 in `AGENTS.md`. **The QA gate agrees:** since
2026-10-18 `scripts/05_preview.py` draws `docs/preview/1_where_poverty_sits.png` as the
same five bands on the same measure in the same colours, so the PNG and sheet 1 are two
renderings of one chart. Before that the PNG was a continuous `YlOrRd` ramp of H — a
different measure, which meant the gate could not catch a sheet-1 regression.

**The five bands carry assigned colours.** A nominal dimension on Colour draws in
Tableau's *default categorical* palette unless the workbook assigns a palette, which
would put five unrelated hues on a scale whose whole meaning is its order. Stage 6 writes
the assignment into the polygon datasource:

```xml
<layout dim-ordering='alphabetic' … />
<style>
  <style-rule element='mark'>
    <encoding attr='color' field='[none:mpi_band:nk]' type='palette'>
      <map to='#ffe5e5'><bucket>&quot;1. under 5%&quot;</bucket></map>
      …
    </encoding>
  </style-rule>
</style>
<semantic-values>
```

The grammar comes from two real Tableau-authored Public workbooks (`Ode to Cowbell`,
`Clinic Performance Dashboard`), because it is not guessable: the block lives **inside the
`<datasource>`**, between `<layout …/>` and `<semantic-values>`; the field is named
**without** its datasource prefix; and a string member is a quoted `<bucket>` with the
quotes escaped. `type='palette'` is the discrete form — the continuous form is
`type='interpolated'` or `type='custom-interpolated'` with a nested `<color-palette>` of
hex stops, which is what those reference workbooks use for their measures.
`type='palette'` renders the ordered ramp: verified in the application on 2026-10-18.
The five hex values are the single list in `atlas_text.MPI_BANDS`, read by the workbook
(stage 6) and by the QA-gate PNG (stage 5), so the gate and the sheet cannot drift apart
— which they once did, when the gate drew a continuous ramp of a different measure.

**The ramp is red, and it runs light to dark with the poverty.** `#ffe5e5` (under 5%)
through `#ffb8b8`, `#ff8a8a`, `#f45555` to `#d80000` (30% and above) — five steps of one
hue, monotonically darkening, so the band order is legible without the legend and no
red-green pair exists anywhere in the workbook. The deepest red is the poorest band, so
the states the atlas is about carry the most ink; the palest band is nearly white on a
white canvas, which is why the state strokes are white and thick. Two things follow that
are worth knowing before someone "improves" the palette: the ramp is **ordinal, not
diverging** (there is no natural midpoint to hang a two-tone scale on), and red is doing
duty as a magnitude ramp here, not as an alarm — the atlas makes no per-state ranking
claim (`docs/CLAIMS.md`), so nothing in the ramp should be read as "this one is the
worst".

**One field, one caption.** A caption is written twice — on the datasource `<column>` and
repeated in every worksheet's `<datasource-dependencies>` — so both are generated from
one map in stage 6. Built separately they disagreed (`MPI band (Multidimensional Poverty
Index)` on the datasource, `mpi_band` in the worksheet), a state Tableau never writes
itself; which of the two the shelf pill and legend read is not established here, so the
two are made to agree rather than argued about.

**Bands and hover read as percentages.** `mpi_band` labels are percentages *of the
index* — `1. under 5%` through `5. 30% and above`; the `N. ` prefix is a sort key,
because the colour legend sorts alphabetically. Per state the hover now says, for Bauchi,
`MPI 44.10% (95% interval 37.90% to 50.50%)` and, for the headcount, `Of the population,
75.36% are multidimensionally poor`. (Those are Tableau's default two decimals on the
percent columns; say the word and they can be set to one decimal or whole numbers.)
The two percentages are different measures on purpose and
must not be swapped: the first is the MPI value, the second is H. `poverty_group` also
carries its own definition there — `Bauchi · Poorest 12 of the 37 states, by MPI` — and
the governorship line reads `Governorship 1999–2021: PDP (14 of 22 years)`, with ties as
`PDP/APC (tied)` and the FCT as `no elected governor (minister-appointed)`. The years are
computed in stage 4 from `data/reference/governorship_events.csv` and asserted against
the vetted `dom_party`. **Party is hover context only; the fill never encodes party.**

**The legend names the index in full.** A colour card's title is the colour field's
*caption* (it cannot be italic — a caption is plain text), so stage 6 now sets
`mpi_band`'s caption to `MPI band (Multidimensional Poverty Index)` instead of the
internal column name. The caption is one word list for the whole workbook: it is also
what the Data pane and the shelf pill show. The full meaning sentence —
*"the share of people who are poor multiplied by how deprived they are on average, as a
percentage of the index"* — lives in the tooltip's italic MPI line and, expanded, in the
QA-gate PNG's colour-bar title and subtitle. All of it comes from `MPI_LEGEND_*` in
`scripts/atlas_text.py`, so the caption, the tooltip and the gate cannot drift apart.
Since the caption is what the legend card keys on, hand-changing the caption in the GUI
would desync the workbook from the generator.

**One cosmetic consequence, and its fix.** A geographic sheet is drawn at a fixed map
scale, so a pane of the wrong shape crops it. At the 1295x687 window this was reviewed in
(the shipped workbook, 2026-10-18) both maps render the whole country — an earlier note
here said sheet 1 showed "roughly the northern four-fifths", which that capture does not
support — but the scale is fixed and a shorter pane will cut the south coast, so `Fit →
Entire View` is still the first GUI click. This used to be fixed without the GUI: the
withdrawn `Equity Atlas` dashboard carried `<zoom type='entire-view' />` on the `Where
poverty sits` viewpoint, which is the Fit control stored as data (grammar taken from a
real Tableau-authored workbook, and verified by rendering the dashboard zone). With that
dashboard gone (`docs/FIX_LEDGER.md` W1) locating the maps whole is a click, and it has
moved to the GUI list below. **`<zoom>` is not legal on a worksheet `<window>`** —
putting it there makes the whole workbook fail to load.

`scripts/05_preview.py` also renders the same choropleth in matplotlib
(`docs/preview/1_where_poverty_sits.png`), which is the pre-Tableau QA gate. The preview
draws from the raw GeoJSON, not from the simplified table the workbook ships — it renders
large and wants the full-resolution coastline; the two differ by less than a pixel in the
workbook.

## Open issues, all safe to fix in the GUI

- **The maps can open cropped.** A geographic sheet holds a fixed map scale, so a pane
  whose shape differs from the map's cuts the south coast. In the 1295x687 window the
  shipped workbook was reviewed in, both maps render whole (2026-10-18). Until the same
  date the withdrawn `Equity Atlas` dashboard fitted sheet 1
  (`<zoom type='entire-view' />` on that viewpoint); with the dashboard gone
  (`docs/FIX_LEDGER.md` W1) this is a click. **To fix by hand:** open each map, **Fit →
  Entire View**, then File → Save.
- **The colour legend does not draw on `Where poverty sits`.** The card that should draw
  it is declared exactly as a Tableau-authored workbook declares one — the sheet's window
  carries
  `<card pane-specification-id='0' param='[federated.0mpipolygons].[none:mpi_band:nk]' type='color' />`
  on the right edge — and window cards **are** honoured: deleting the Marks card from the
  same `<cards>` block removes it from the UI, so the block is definitely read. Ruled out
  by experiment on 2026-10-18: the modern-format grammar (`<simple-id>` and the
  reference's `<document-format-change-manifest>` are both rejected here — *"no
  declaration found for element 'simple-id'"*, `D2E8DA72`), the reference's second `rows`
  strip, the mark class (a Circle version of the same sheet shows no legend either, so it
  is not Polygon-specific), and the missing palette (the bands now have assigned colours
  and a defined sort order, and the legend still does not appear). Remaining suspects are
  the extract-backed datasource and the XY-polygon view. **To fix by hand** — the one
  click that has to happen before this sheet ships: open the sheet,
  **Analysis → Legends → Colour Legend**, then File → Save. What that click shows is the
  ordered five-step red ramp under the `MPI band (Multidimensional Poverty Index)` title,
  because both halves of the legend are already declared in the workbook. Whatever
  reproduces the click's state has to be found by saving and diffing, not by guessing at
  the card again.
- **Both maps show `Avg. lat` / `Avg. lon` as axis titles.** They are real axis titles
  for custom coordinate fields, not generated Latitude/Longitude, so Tableau prints the
  field captions. A map should not show them. **To fix by hand:** right-click each axis
  → uncheck **Show Header**, on both map sheets, then Save. Doing it in XML needs an
  axis/header style rule whose grammar is unverified here (the `border-*` lesson,
  `docs/SESSION_HANDOFF.md`), and a wrong guess fails the workbook open rather than
  failing quietly — so it is a GUI step.
- **The cluster map's colour card does draw on the worksheet**, as of 2026-10-18: a
  1295-px capture of `Where poverty clusters` shows the right-hand strip with the
  `Neighbourhood type` title and the swatches, from the same `type='color'` window card
  grammar sheet 1 uses. That contradicts the open item above at least once, so
  re-check `Where poverty sits` with the same capture method before concluding that its
  legend is broken — the earlier conclusion may have been drawn from a capture that
  clipped the right edge. Not resolved here; both sheets ship the same declaration.

- **Alt text is not set on any tab** (ten tabs as of 2026-10-25). Tableau auto-generates a description;
  edit it per view, then Save. Keep it descriptive and objective, not interpretive: for
  `Where poverty sits` that means naming the measure, the five bands and the period, not
  asserting which state is worst — no single state holds the highest score defensibly
  (`docs/CLAIMS.md`). For `A state over time`, name the panel (one small chart per
  monitored measure, four harmonised survey rounds, one state at a time) — the wording
  is drafted in `docs/SHEET_TIME_PANEL.md`.
- **The time panel's interactions are only open-state-verified.** Captures cannot press
  a mouse button or read a tooltip (tooltips are separate popup windows a PrintWindow
  capture never sees), so two checks remain for a human at publish time, on the
  published viz:
  1. **Hover a point** and confirm the annotations read out: the survey round
     (e.g. `DHS 2013`), the annualised `Mean annual change since the previous round`,
     the `Movement the OPHI change test calls significant` stars, and the
     `Conflict deaths ... (upper estimate)` number. If a field shows the
     "not in the view" placeholder instead of a value, report it — the customized
     tooltip is the one construct on the sheet without a copied precedent.
  2. **Tick measures off in the Measure Names checklist** — untick MPI, tick Mean
     temp; the pane count should follow the ticks. One session observed the checklist
     widen back to nine rows after a mark selection (`docs/FIX_LEDGER.md` T4); if that
     reproduces on the publish, remove the two `param` filter cards
     (checklist + state dropdown) and rely on the standard Filters shelf card, which
     exposes the same two filters and demonstrably works.

- **The composition sheet's interactions are likewise only open-state-verified**
  (2026-10-22 packet `render_dim7.png`): the renders show the 17-bar default, the bold
  white segment numbers and the left-rail `state` checklist with the intended ticks, but
  a human must confirm:
  1. **Hover a segment** and confirm the tooltip reads out: the state, the MPI label,
      the segment's area name (`Area being shown: ...`), the full `dim_hover` split and
      the caveat line. Same placeholder caveat as the time panel above.
  2. **Tick a new state on the `state` checklist** (e.g. Rivers) and confirm its bar
      appears **in MPI position** in its group block (the manual sort survives the
      filter), then untick back to the 17-bar default; `(All)` should add all 37 at
      once. If the group header column shows `Poorest` wrapping, drag its splitter
      wider (cosmetic; an XML width rule was tried and did not take).
  3. **Eye-check the thin-segment labels**: slivers under ~5% wide can print a number
      wider than the segment; Tableau culls only when `mark-labels-cull` is on, which
      this sheet does not set (the shared pane template cannot gain it without losing
      the time panel's R-labels). If a collision shows on a wide window, switching this
      sheet's Label card to "never overlap" at publish time is a safe GUI fix.
  4. **The colour card** on this sheet's right edge is declared exactly like the
      cluster map's (the one proven to draw); if the legend fails to show on this
      sheet too, it joins the `Where poverty sits` defect family — the fix is one
      click of **Analysis → Legends → Colour Legend**, then Save.

- **The pairs board's interactions are likewise only open-state-verified**
  (2026-10-22: green circles render-verified on the packet and the full
  workbook; a human must confirm on the published viz):
  1. **Hover a point** and confirm the tooltip prints **the state name and
     nothing else** (one bold line — `docs/SHEET_PAIRS.md` Built). The caveat
     sentences live in the subtitle, not the hover.
  2. **Switch each dropdown** (X then Y) and confirm the payload follows the
     card; zero-event states stay on the 0 gridline whenever Y is a logged
     axis.
  3. **Eye-check the circles are green on both panes** and that no colour
     legend card prints (the sheet has no colour pill by design; if one
     appears, the pane `mark-color` rule was lost).
  4. **Note the open-state finding** (`docs/SHEET_PAIRS.md` Built): a fresh
     open sometimes carries non-default card selections; check the shipped
     defaults (X = `H (% poor)`, Y = `Events log`) on the published viz.
  5. **The trend line (2026-10-24).** Both panes must show a **quadratic curve
     with its shaded 95% confidence band**, in dark ink. Hover a pane and
     confirm **no model equation or p-value appears** (instant analytics is
     off on purpose — that readout is exactly what the sheet's guardlist
     forbids). Switch a dropdown and confirm **both** panes re-fit. If a line
     is missing, the `<trendline>` element was lost between build and upload —
     stage 6 now asserts it; if the line is there but **pale/invisible**, the
     `stroke-color` format on `element='trendline'` was lost and the line fell
     back to a light default.

- **The KPI board's 2026-10-24 pass is only gate-and-probe verified**, so it
  wants five eyes on the published viz (`docs/SHEET_KPI.md`, built record):
  1. **Both arrows print in the row headers** — `▼` on the first three rows,
     `▲` on the last four. A missing glyph means the member strings were
     rewritten somewhere between the extract and the sheet.
  2. **The world marks are amber with visible vertical meridians** (not a flat
     disc, not a purple one). A flat disc means the `type='shape'` rule stopped
     binding; purple means the palette member went back to the old hex.
  3. **No two silhouettes touch** on any row, and no printed number sits on
     another. The dodge is data-side (`FIX_LEDGER.md` M1), so a collision means
     the extract was rebuilt without it.
  4. **The colour card draws** and shows three members (the sheet's one
     right-edge card, now on its third hue).
  5. **Labels are still legible at the published size** at `font-size='6'`; if
     they are too small, the pane datalabel font-size is one number in stage 6.
  6. At the published width each row label takes one or two lines; three lines
     means the 230 px header rule (`kpi_table_style`) was lost.

## If something looks wrong

Most likely, in order:

- **`Where poverty sits` shows text or numbers instead of a map, or draws unconnected
  lines.** Either the lat/lon `[Geographical]` roles are missing (confirm via
  right-click `lat` → Geographic Role → Latitude, `lon` → Longitude), or the Path
  field is gone. Without `point_order` on Path the vertices are not connected.
- **`Where poverty sits` is empty.** `mpi_polygons.hyper` did not make it into the
  package, or `ring`/`point_order` lost their ordinal type — they must be declared
  `datatype='integer'` *dimensions*. Re-run `scripts/04_merge.py` then
  `scripts/06_build_twb.py` and confirm the package lists three `.hyper` files.
- **"must use extracts" (3C242D89).** A `.twbx` built by an older revision of stage 6
  still packages CSV. Re-run `scripts/06_build_twb.py` and confirm the package
  contents list `.hyper` files.
- **"The field '[sum:x:qk]' does not exist" (9CA7205B).** A shelf reference with no
  matching `<column-instance>`. The generator now derives these from the shelves; if
  you hand-edit the XML, add one per shelf field.
- **Marks look wrong on a sheet.** The mark classes and shelves are declared in the
  XML; re-check the sheet against the table above.
- **Tableau reports a data error.** The extract schema is validated against the
  declared columns at build time, so this would indicate a genuine mismatch — re-run
  `scripts/04_merge.py` then `scripts/06_build_twb.py`.

## What is left deliberately to the GUI

Four clicks per map, and the workbook is done. All of them are changes that fail the
workbook open rather than failing quietly when attempted in XML — the `border-*` lesson,
`docs/SESSION_HANDOFF.md` — so they are not attempted in XML here:

1. **Fit → Entire View** on each map, so the country is not cropped.
2. **Right-click each axis → uncheck Show Header** on each map, so `Avg. lat` / `Avg. lon`
   stop printing as titles.
3. **Analysis → Legends → Colour Legend** on `Where poverty sits`. `Where poverty
   clusters` already draws its card from the same declaration, so it needs no click.
4. **Description / alt text** per view.

Then File → Save.

**The radar chart is withdrawn, not pending.** It was the one spec visual never
generated — its `Angle` / `Wedge Size` polar encodings stayed unverified from XML — and it
went with the other spec sheets on 2026-10-18 (`docs/FIX_LEDGER.md` W1). Its Polygon-mark
half is no longer the blocker: `Where poverty sits` is a Polygon mark with an
integer-dimension Path field, built entirely from XML. If the radar is ever wanted, the
grammar that is missing is the polar encoding, not the mark.

**Colour scales and captions.** Both palettes are generated and written into their
datasources by stage 6 — `atlas_text.MPI_BANDS` for the five-step red poverty ramp,
`atlas_text.SPATIAL_QUADRANTS` for the four neighbourhood types — so neither map needs a
GUI step to colour itself, and hand-editing a colour in the GUI would desync the workbook
from its generator.

## Attribution — in the workbook, and in its description

Part 3's first row, `Where the numbers come from`, carries the sources and the licences in
the same plain language as the rest of the table, so attribution ships inside the
workbook and does not depend on the description field being filled in. Paste the same into
the workbook description as well:

> Poverty: OPHI / UNDP Global MPI, harmonised series (Data Table 6, MN 63),
> MICS 2021, CC0 / CC BY. Standard errors from Table 5.4; harmonised state-level
> changes from Table 6.4.
> Conflict: UCDP Georeferenced Event Dataset 24.1, CC BY-IGO. The exposure index is
> relative within each survey year, and its 2021 correlation with MPI is +0.01 to
> +0.08 across UCDP's full low-to-high fatality band.
> Climate: Open-Meteo Archive API. Boundaries: geoBoundaries ADM1, CC BY 4.0.
> Capitals: GeoNames, CC BY 4.0. Conflict Exposure Index is relative within each
> survey year — see `docs/normalisation.md`.

## Verifying the live viz afterwards

Once published, the viz can be checked from the command line with the `tableau`
MCP server, which is read-only but sufficient for verification:

- `get_workbook_details` — confirms the views and their types
- `get_workbook_contents` — confirms all nine views exist (two maps, the
  stacked composition bar, the time panel, three reference tabs, the KPI
  board, the pairs board)
- `get_workbook_image` — fetches a rendered PNG of a named view, proving it draws

This is the step that catches a viz that uploaded but renders empty.
## 2026-10-25 — the Overview's selector and legends (new checks)

The Overview page now carries a `paramctrl` state selector and two `type-v2='color'`
legend zones (`docs/DASHBOARD.md`, `docs/FIX_LEDGER.md` §Q). All three were
render-verified locally; these are the extra things to confirm on the **published**
viz, because a publish re-saves the workbook and interaction cannot be captured
from a packet:

1. **The selector** in the title band reads `State` and lists `(All states)` plus
   the 37 states. Pick a state and confirm **all three panes move together** — both
   maps collapse to that polygon, the composition shows that one bar. Then set it
   back to `(All states)` and confirm the composition returns to **18 bars** (6 of the 12, 12 of the 25).
2. **All three legends** print their full titles and every member label:
   `MPI band (Multidimensional Poverty Index)` with five bands,
   `Neighbourhood type (this state's poverty, beside the states it borders')` with
   three types (the fourth has no state in 2021), and `Measure Names` with
   Education / Health / Living standards. If a label truncates, that legend zone
   lost width during the re-save.
3. **The composition tab** still opens on 17 bars with the `State` control on its
   left rail and **no** state checklist (retired, `docs/SHEET_DIMENSIONS.md`
   amendment 2).
4. **The cluster map's hover** is five short lines ending in the no-spillover
   caveat. If the four-paragraph essay reappears, the short tooltip was lost.

Note on the old colour-legend item above: the legend **zone** on the dashboard
draws, which is new evidence that only the sheet-1 **window card** is broken. The
`Analysis -> Legends -> Colour Legend` click is now needed for the *tab* only.

## 2026-10-25 — the second dashboard (new checks)

`A state, in context` is tab 2, 1600x1300, carrying `A state over time`,
`How measures pair` and `Where Nigeria stands` (`docs/DASHBOARD.md`). It
**overrides** the "no state-level panel" rule in `docs/SHEET_KPI.md` (amendment
1); the mitigation is the page subtitle plus the KPI band's own title, subtitle,
direction key and legend.

On the published viz:

1. **The page scrolls**: it is 1300 px tall, so a browser window shows the top
   row and the KPI band is reached by scrolling. Confirm nothing is cut off at
   the bottom.
2. **The three controls** read `Panel state: Bauchi`, `X axis: H (% poor)`,
   `Y axis: UCDP events per 100k, log(1+rate)`. Change the panel state and
   confirm all six panes move together; change X and Y and confirm both scatter
   panes re-fit, bands included.
3. **The KPI legend** prints `Reference point (2021)` with Nigeria, sub-Saharan
   Africa and World in full.
4. **The time tab** now carries a `Panel state` parameter card in place of its
   old state dropdown; confirm it still opens on Bauchi.

## 2026-10-25 — the KPI direction guides (new checks)

`Where Nigeria stands` gained one coloured arrow per row (vermillion pointing
left = lower is better, purple pointing right = higher is better), drawn before
the silhouettes (`docs/SHEET_KPI.md` amendment 2). On the published viz:

1. **Every row shows an arrow at the left edge**: the first three point left and
   are vermillion; the last four point right and are purple.
2. **The legend** is titled `Reference point / direction` and lists five
   entries — the two direction sentences plus the three reference points.
3. **No arrow prints a number**, and no arrow shows a hover.
4. If the arrows are missing entirely, the embedded shapes were lost in the
   re-save; the row headers' ▼/▲ glyphs still carry the direction.

## 2026-10-25 — the cover's clickable contents (new checks)

The two contents headings on `Start here` are navigation buttons (`FIX_LEDGER` §U).

1. On the live viz, click **1 Overview →** and **2 A state, in context →**: each
   should open its dashboard. (In the desktop app they fire only on Alt+click or
   in presentation mode, F7.)
2. The viz should open on `Start here`. If it opens elsewhere, select the cover
   tab before publishing — the tab showing at publish time is the one readers land on.
