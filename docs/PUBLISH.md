# Publishing to Tableau Public

Tableau Public has **no write API and no publishing CLI**. `tabcmd` targets Tableau
Server/Cloud, not Tableau Public, and the `tableau` MCP server available here is
read-only (search, metadata, download). Publishing is a GUI action behind an
interactive account login, so this is the one step that has to be done by hand.

Everything up to that point is automated and reproducible: `scripts/06_build_twb.py`
produces a validated `.twbx` with the data packaged inside it.

## What is already built

`tableau/Nigeria-MPI-Equity-Atlas.twbx` (125 KB) contains:

```
Nigeria-MPI-Equity-Atlas.twb     the workbook
Data/mpi_atlas_2021.hyper        37 rows, one per state
Data/mpi_trends_panel.hyper      148 rows, 37 states x 4 survey rounds
Data/party_alignment_panel.hyper 108 rows, 36 states x 3 intervals (FCT excluded)
Data/mpi_polygons.hyper          7,089 rows, the simplified ADM1 ring vertices the map draws
```

The data ships as **Hyper extracts**, not CSV. This is not a preference: Tableau
Public refuses any workbook whose datasource is not an extract — *"Workbooks saved
to Tableau Public must use extracts"*, error `3C242D89` — and it does **not**
convert a live file on save. Stage 6 writes the extracts itself with
`tableauhyperapi`, and validates the schema it wrote back against the declared
columns before packaging.

**Six sheets and three dashboards.** The five spec sheets sit on the `Equity Atlas`
dashboard; the party sheet is standalone. `Equity Atlas` also carries two text zones
(the attribution paragraph and the KPI strip). **The five spec sheets were verified by
opening the workbook in Tableau Public and looking at every sheet on 2026-10-06; the
party sheet and the two reader dashboards were added and verified on 2026-10-09/10.**
The lower part of `What the words mean` has never been scrolled on screen — see
`docs/SESSION_HANDOFF.md`.

| Sheet | Type (mark class) | What it carries |
|---|---|---|
| Where poverty sits | **filled map (*Polygon*)** | `AVG(lat)` on Rows, `AVG(lon)` on Columns (both `[Geographical]` roles, so the sheet stays a geographic map); `state` + `pcode` + `ring` on Detail; `point_order` on **Path**; `mpi_band` on Colour; `state` on Text. Datasource: `Nigeria MPI polygons`. Hover carries `mpi`, `mpi_se`, `mpi_ci_lo`, `mpi_ci_hi`, `headcount_ratio_pct`, `intensity_pct`, `mpi_poor_thousands`, `poverty_group`, `mpi_pct`, `mpi_ci_lo_pct`, `mpi_ci_hi_pct`, `gov_party` |
| Dimension breakdown (three panels, not stacked) | bar (*Bar*) | `SUM(contrib_health_pct) + SUM(contrib_education_pct) + SUM(contrib_living_standards_pct)` on Rows, `state` on Columns |
| Poverty vs conflict | scatter (*Circle*) | `SUM(conflict_exposure_index)` on Rows, `SUM(mpi)` on Columns, `state` on Detail and Text, `quadrant` on Colour **and** Shape |
| Poverty over time | line (*Line*) | `SUM(mpi)` on Rows, `survey_year` (string) on Columns, `state` on **Colour** and Detail — one line per state on one axis. Datasource: `Nigeria MPI trends panel` |
| Incidence vs intensity | scatter (*Circle*) | `SUM(intensity_pct)` on Rows, `SUM(headcount_ratio_pct)` on Columns, `state` on Detail and Text, `quadrant` on Colour and Shape |
| Party alignment and MPI change | scatter (*Circle*) | `SUM(dmpi_annual)` on Rows, `SUM(aligned_share)` on Columns, `state` on Detail, `interval` on Colour. Datasource: `Party alignment panel`. **Not on the `Equity Atlas` dashboard — it is standalone** |

The three dashboards:

| Dashboard | Contents |
|---|---|
| `Equity Atlas` | the five spec sheets above (2 text zones: attribution + KPI strip) |
| `What the words mean` | 3 text zones — the plain-language reader sheet |
| `How we did it` | 2 text zones — sources, method, uncertainty, limits |

Two sheets carry their limitation in the **title**, deliberately:

- **`Where poverty sits` is a filled map as of 2026-10-17**, drawn from the shipped
  ADM1 rings. It used to be a georeferenced scatter of the 37 capitals; see
  "The map, and why it is drawn from shipped geometry" below.
- **`Dimension breakdown (three panels, not stacked)` is not a stacked bar.**

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
4. Wait for the upload and the render, then open the live URL and confirm all six
   sheets are present and that `Where poverty sits` draws the filled choropleth, not
   a scatter of points. Fetch it with the `tableau` MCP `get_workbook_image` rather
   than trusting the upload dialog.

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
same five bands on the same measure in the same colours, so the PNG, sheet 1 and the HTML
map are three renderings of one chart. Before that the PNG was a continuous `YlOrRd` ramp
of H — a different measure, which meant the gate could not catch a sheet-1 regression.

**The five bands carry assigned colours.** A nominal dimension on Colour draws in
Tableau's *default categorical* palette unless the workbook assigns a palette, which
would put five unrelated hues on a scale whose whole meaning is its order. Stage 6 writes
the assignment into the polygon datasource:

```xml
<layout dim-ordering='alphabetic' … />
<style>
  <style-rule element='mark'>
    <encoding attr='color' field='[none:mpi_band:nk]' type='palette'>
      <map to='#ffffd4'><bucket>&quot;1. under 5%&quot;</bucket></map>
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
The five hex values are the single list in `atlas_text.MPI_BANDS`, read by stage 6 (the
workbook), stage 5 (the QA-gate PNG) and stage 7 (the HTML map), so the two maps cannot
drift apart. ColorBrewer YlOrBr, 5-class: no red-green pair, and it darkens
monotonically, so the band order is legible without the legend. The lowest band is a pale
cream; on a white canvas it reads as "light", which is the point, and the white state
strokes keep its outline visible.

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
percentage of the index"* — lives in the tooltip's italic MPI line and, italicised, in the
HTML map's colour-bar title and narrow-screen legend. All of it comes from
`MPI_LEGEND_*` in `scripts/atlas_text.py`, so the five surfaces cannot drift apart.
Since the caption is what the legend card keys on, hand-changing the caption in the GUI
would desync the workbook from the generator.

**One cosmetic consequence, and its fix.** A geographic sheet is drawn at a fixed map
scale, so a short pane crops it — the standalone sheet shows roughly the northern
four-fifths at a 1295x687 window. The dashboard fixes this without the GUI:
`<zoom type='entire-view' />` is written into the `Where poverty sits` viewpoint of the
`Equity Atlas` dashboard window, which is the dashboard's Fit control stored as data
(grammar taken from a real Tableau-authored workbook, and verified by rendering the
dashboard zone). **`<zoom>` is not legal on a worksheet `<window>`** — putting it there
makes the whole workbook fail to load. So the standalone sheet still opens at Tableau's
default map scale; click **Fit > Entire View** on it if you want it whole.

`scripts/05_preview.py` also renders the same choropleth in matplotlib
(`docs/preview/1_where_poverty_sits.png`), which is the pre-Tableau QA gate. Stages 5
and 7 draw from the raw GeoJSON, not from this simplified table — they render large and
want the full-resolution coastline; the two differ by less than a pixel in the workbook.

## Open issues, all safe to fix in the GUI

- **The standalone `Where poverty sits` sheet opens cropped.** A geographic sheet draws
  at a fixed map scale, so a short pane cuts off the south. The `Equity Atlas` dashboard
  is already fitted (`<zoom type='entire-view' />` on that viewpoint). **To fix the sheet
  itself by hand:** Fit → Entire View.
- **`Dimension breakdown (three panels, not stacked)` is not a stacked bar.** Three
  measures on Rows give three aligned panes. The Measure Names/Values pair was tried
  from XML and drew one 18,000-tall bar per state, because a hand-written pair also
  needs the measure-values filter. **To fix by hand:** Analysis → Measure Names →
  Columns; Measure Values → Rows; `state` → Columns (below Measure Names); `state` →
  Detail; Colour → the *Measure Names* field so each dimension gets its own colour.
- **The radar chart is still not generated** — see below.
- **`Party alignment and MPI change` is standalone and labelled.** It is not on the
  `Equity Atlas` dashboard, and its mark labels are on (36 states × 3 intervals). Drag
  it onto `Equity Atlas` if it should ship there, and turn Mark Labels off on the Marks
  card to quiet it. It must keep the §3 pre-registered sentence verbatim with its
  robustness line beside it — see `docs/CLAIMS.md` and `docs/party_alignment.md`.
- **Alt text is not set.** Tableau auto-generates a description; edit it on each
  sheet. Keep it descriptive and objective, not interpretive.
- **No legend zones were verified on the published dashboard.** The workbook declares
  the text and KPI zones; colour legends render from the Marks card on each sheet,
  but check them on the live viz.
- **The colour legend does not draw on `Where poverty sits`, though the card that should
  draw it is declared exactly as a Tableau-authored workbook declares one.** The sheet's
  window carries
  `<card pane-specification-id='0' param='[federated.0mpipolygons].[none:mpi_band:nk]' type='color' />`
  on the right edge — byte-for-byte the shape of the working colour card on the
  `percapita` sheet of a real Public workbook — and window cards **are** honoured:
  deleting the Marks card from that same `<cards>` block removes it from the UI, so the
  block is definitely read. Ruled out by experiment on 2026-10-18: the modern-format
  grammar (`<simple-id>` and the reference's `<document-format-change-manifest>` are both
  rejected here — *"no declaration found for element 'simple-id'"*, `D2E8DA72`), the
  reference's second `rows` strip, the mark class (a Circle version of the same sheet
  shows no legend either, so it is not Polygon-specific), and — as of 2026-10-18 — the
  missing palette: the bands now have assigned colours and a defined sort order, and the
  legend still does not appear. Remaining suspects are the extract-backed datasource and
  the XY-polygon view. **To fix by hand** — the one click that has to happen before this
  sheet ships: open the sheet,
  **Analysis → Legends → Colour Legend**, then File → Save. What that click will now show
  is the ordered five-step ramp on the `MPI band (Multidimensional Poverty Index)` title,
  because both halves of the legend are already declared in the workbook. Whatever
  reproduces the click's state has to be found by saving and diffing, not by guessing at
  the card again. The dashboard's own `type-v2='color'` zone for `mpi_band` is likewise
  unverified: the worksheet opens by default and the legend has only ever been checked
  there.

## If something looks wrong

Most likely, in order:

- **`Where poverty sits` shows text or numbers instead of a map, or draws unconnected
  lines.** Either the lat/lon `[Geographical]` roles are missing (confirm via
  right-click `lat` → Geographic Role → Latitude, `lon` → Longitude), or the Path
  field is gone. Without `point_order` on Path the vertices are not connected.
- **`Where poverty sits` is empty.** `mpi_polygons.hyper` did not make it into the
  package, or `ring`/`point_order` lost their ordinal type — they must be declared
  `datatype='integer'` *dimensions*. Re-run `scripts/04_merge.py` then
  `scripts/06_build_twb.py` and confirm the package lists four `.hyper` files.
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

**The radar chart** (the spec's fifth visual) is not generated. A radar needs a
polygon mark driven by computed path fields. Since 2026-10-17 the Polygon-mark half of
that grammar is **proven**: `Where poverty sits` is a Polygon mark with an
integer-dimension Path field, built entirely from XML. What is still unverified is the
polar encoding (`Angle` / `Wedge Size`), which the map does not use. To add it:

1. Use `docs/preview/5_state_radar.png` as the design reference.
2. Create a new sheet, `Analysis > Create > Parameters` is not needed — instead drag
   `contrib_health_pct`, `contrib_education_pct` and `contrib_living_standards_pct`
   onto **Angle** via the tooltip's field picker, and `mpi` onto **Size**.
3. Set the mark type to **Polygon**, put `state` on Detail and Colour.
4. Add `AVG(contrib_health_pct)` etc. as Reference Lines to draw the 37-state mean.

**Colour scales and captions.** The methodology text and the KPI strip are already
on the dashboard canvas, generated in `06_build_twb.py` — so the attribution, the
Nutrition exclusion, the standard errors and the conflict caveats are visible to a
reader without them reading the description. Switch both scatters to Tableau's
**Color Blind** palette, which pairs with the Shape encoding already on `quadrant`.

## Attribution — already on the dashboard canvas

The dashboard carries this as a text zone, so it does not depend on the description
field being filled in. Paste into the workbook description as well:

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
- `get_workbook_contents` — confirms all six sheets and the three dashboards exist
- `get_workbook_image` — fetches a rendered PNG of a named view, proving it draws

This is the step that catches a viz that uploaded but renders empty.