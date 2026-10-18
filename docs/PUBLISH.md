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
```

Two extracts and nothing else. The atlas, trends-panel, party-alignment and
spatial-diagnostic extracts were packaged until 2026-10-18, when the sheets that drew
them were withdrawn (`docs/FIX_LEDGER.md` W1); those four `.hyper` files are no longer
built or packaged, and stale copies of them from an earlier build may still be sitting
in `tableau/` — they are gitignored artefacts, so delete them if the folder still lists
them.

The data ships as **Hyper extracts**, not CSV. Tableau Public refuses any workbook whose
datasource is not an extract (*"Workbooks saved to Tableau Public must use extracts"*,
error `3C242D89`) and it does **not** convert a live file on save. Stage 6 writes both
extracts itself with `tableauhyperapi` and validates the schema it wrote back against
the declared columns before packaging.

**Two worksheets and three dashboards.**

| Tab | Type (mark class) | What it carries |
|---|---|---|
| Where poverty sits | **filled map (*Polygon*)** | `AVG(lat)` on Rows, `AVG(lon)` on Columns (both `[Geographical]` roles, so the sheet stays a geographic map); `state` + `pcode` + `ring` on Detail; `point_order` on **Path**; `mpi_band` on Colour; `state` on Text. Datasource: `Nigeria MPI polygons`. Hover carries `mpi`, `mpi_se`, `mpi_ci_lo`, `mpi_ci_hi`, `headcount_ratio_pct`, `intensity_pct`, `mpi_poor_thousands`, `poverty_group`, `mpi_pct`, `mpi_ci_lo_pct`, `mpi_ci_hi_pct`, `gov_party` |
| Where poverty clusters | **filled map (*Polygon*)** | the same shelves, from `spatial_polygons.csv`: `spatial_group` on Colour, `mpi_pct` + `spatial_lag_mpi_pct` + `neighbours` on Detail for the hover. Datasource: `Spatial polygons`. **Descriptive, not a significance map** — one state survives the correction, so a significance map would be one state; the count is in the hover |
| What the words mean | **text zones** (part 1 of 3) | the reference table, 24 rows: the word, its formula or weight, what it means, how it was made |
| The list of basic needs | **text zones** (part 2 of 3) | the same three columns, 11 rows: the nine needs in three areas, each with its weight and what counts as missing |
| How we did it | **text zones** (part 3 of 3) | the same three columns, 9 rows: a worked step per section, from the survey to the party question |

The three reference tabs are **one table paginated on its own groups**, not three
documents. It was two prose dashboards (`What the words mean`, `How we did it`) until it
was merged into a single three-column table on 2026-10-18, and then split because the
merged version measured **2000 x 8720 px** — thirteen screens on the 687 px window it
was reviewed in (`docs/FIX_LEDGER.md` W2). Each part repeats the intro and the column
headers on purpose, so a reader who arrives on part 3 from the tab bar is told what the
columns are. It is a layout of text zones, not a datasource: a real multi-column Tableau
text table needs the Measure Names / Measure Values pair *and* its filter, which this
project could not make render from hand-written XML — the note is above
`table_dashboards` in stage 6.

**Verified by opening the workbook in Tableau Public 2026.2 and looking at it:** the
poverty map and the five spec sheets on 2026-10-06; the party sheet and the reader
dashboards on 2026-10-09/10; the cluster map and all three reference parts on
2026-10-18. In each case what was checked is the top of the tab at a 1295x687 window —
the reference parts have not been scrolled to the end on screen, and neither has the
map been panned.

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
3. **File > Save to Tableau Public.**
4. Wait for the upload and the render, then open the live URL and confirm all five tabs
   are present and that `Where poverty sits` draws the filled choropleth, not a scatter
   of points. Fetch it with the `tableau` MCP `get_workbook_image` rather than trusting
   the upload dialog.

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
scale, so a short pane crops it — `Where poverty sits` shows roughly the northern
four-fifths at a 1295x687 window. This used to be fixed without the GUI: the withdrawn
`Equity Atlas` dashboard carried `<zoom type='entire-view' />` on the `Where poverty
sits` viewpoint, which is the Fit control stored as data (grammar taken from a real
Tableau-authored workbook, and verified by rendering the dashboard zone). With that
dashboard gone (`docs/FIX_LEDGER.md` W1) locating the map whole is a click, and it has
moved to the GUI list below. **`<zoom>` is not legal on a worksheet `<window>`** —
putting it there makes the whole workbook fail to load.

`scripts/05_preview.py` also renders the same choropleth in matplotlib
(`docs/preview/1_where_poverty_sits.png`), which is the pre-Tableau QA gate. The preview
draws from the raw GeoJSON, not from the simplified table the workbook ships — it renders
large and wants the full-resolution coastline; the two differ by less than a pixel in the
workbook.

## Open issues, all safe to fix in the GUI

- **`Where poverty sits` opens cropped.** A geographic sheet is drawn at a fixed map
  scale, so a short pane cuts off the south. Until 2026-10-18 the withdrawn `Equity
  Atlas` dashboard fitted it (`<zoom type='entire-view' />` on that viewpoint); with the
  dashboard gone (`docs/FIX_LEDGER.md` W1) this is a click. **To fix by hand:** open the
  sheet, **Fit → Entire View**, then File → Save.
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

- **Alt text is not set on any of the five tabs.** Tableau auto-generates a description;
  edit it per view, then Save. Keep it descriptive and objective, not interpretive: for
  `Where poverty sits` that means naming the measure, the five bands and the period, not
  asserting which state is worst — no single state holds the highest score defensibly
  (`docs/CLAIMS.md`).

## If something looks wrong

Most likely, in order:

- **`Where poverty sits` shows text or numbers instead of a map, or draws unconnected
  lines.** Either the lat/lon `[Geographical]` roles are missing (confirm via
  right-click `lat` → Geographic Role → Latitude, `lon` → Longitude), or the Path
  field is gone. Without `point_order` on Path the vertices are not connected.
- **`Where poverty sits` is empty.** `mpi_polygons.hyper` did not make it into the
  package, or `ring`/`point_order` lost their ordinal type — they must be declared
  `datatype='integer'` *dimensions*. Re-run `scripts/04_merge.py` then
  `scripts/06_build_twb.py` and confirm the package lists two `.hyper` files.
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
- `get_workbook_contents` — confirms all five views exist (two maps, three reference tabs)
- `get_workbook_image` — fetches a rendered PNG of a named view, proving it draws

This is the step that catches a viz that uploaded but renders empty.