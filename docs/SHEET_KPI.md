# Sheet freeze — "Where Nigeria stands" (the KPI board)

Status: **frozen 2026-10-23**, before build. Data: `scripts/07_kpi_reference.py` →
`data/reference/kpi_benchmarks_2021.csv` (verified fetch, see
`docs/kpi_benchmarks.md`) → `data/processed/kpi_dots.csv` (the marks). Grammar
borrowed from proven sheets: Circle marks on one shared pre-normalised measure
(time panel/rank lesson: no computation in the workbook), a nominal field on
Colour mapped by a ds-level palette (`mpi_band` / `spatial_group` /
Measure-Names precedent), a manual sort dictionary for the row order
(composition sheet), and one pre-formatted hover string dimension (time panel
amendment). The workbook goes from eight views to nine; the pairs board moves
from tab 8 to tab 9 and this sheet takes tab 8, after the three reference tabs.

## What the sheet is

One **reference board**: one row per benchmarked KPI, one **map silhouette** per
reference point (the 2026-10-23 user-pass amendment — the marks stopped being
circles: a green map of Nigeria, a blue map of Africa, an orange **globe**
itself, continents cut out of a filled disc). 7 benchmarked rows × their
references = **20 marks** (the headcount row has no sub-Saharan-Africa WDI
figure, so 2 marks there; every other row has 3). The point is "Nigeria beside
its reference points", not "Nigeria graded":

- **Nigeria (2021)** — green `#009E73`, drawn from the atlas's own 37 ADM1
  rings (`data/processed/mpi_polygons.csv`).
- **sub-Saharan Africa (2021)** — Tableau categorical blue `#4E79A7`, Africa
  from Natural Earth 110m (public domain, fetched once, SHA256 in the
  provenance ledger).
- **World (2021)** — **amber `#E69F00` as a globe of vertical meridians only**
  (2026-10-24; supersedes both the earlier orange cut-out and the purple
  coastline globe). Okabe-Ito amber because the board's other two hues are
  already spent on a green landmass (one country) and a blue one (one
  continent) — see "the world's colour" below. For every row this is
  *developed-and-developing-mixed* WDI aggregates; for the poverty headcount it
  is UNDP/OPHI's count across the 109 developing regions' countries, and every
  surface says so.

The shapes identify the series by geometry — colour is the secondary key (the
right-edge colour card + the legend), pinned by the user pass. The images are
stage 7's (`data/reference/kpi_shapes`, keyed by
`atlas_text.KPI_SHAPE_FILES`) and **embedded in the workbook** inside
`<external><shapes>`, so no Shapes-repository copy is needed for the workbook
to render (the one in `My Tableau Repository\Shapes\KPI_Geo` that stage 7
writes, when the shell is allowed to write there, exists only for GUI shape
reassignment — see `docs/PUBLISH.md`).

References only. The five dataset-native rows of the benchmarks table (national
MPI, intensity, severe, vulnerable, poor population) do **not** reach the sheet:
a mark with no standard to sit beside would read as a judgement, and their numbers
are already the reference table's and the maps'.

## The scale (frozen, and why)

Units differ per row (per-1,000 births against percent of people), so the marks
do not share a raw axis. Stage 7 normalises each row separately:
`pos = value / max(that row's Nigeria, SSA, world, SDG benchmark)`. The Columns
axis is therefore 0–1 on every row, states as shares, and **pos is layout, not
data** — the hover prints every raw value so the reader never has to read a
position as a figure. "Largest reference" (not "largest of the plotted marks")
is deliberate: it keeps the SDG benchmark inside the scale even when it exceeds
both Nigeria and world (exact-position-1.0 belongs to the largest reference by
construction — on the headcount and child-death rows that is Nigeria itself,
which is the story, not an axis fault).

## Rows (frozen order)

The row order is the benchmarks table's narrative order, shipped as the manual
sort dictionary in the extract's CSV order. Alphabetical order would bury the
headline row:

1. `Poverty headcount (% of people)` — Nigeria 33, world 22 (UNDP/OPHI)
2. `Child deaths under 5 (per 1,000 births)` — Nigeria 117.6, SSA 77.1, world 39.6, benchmark ≤ 25
3. `Open defecation (% of people)` — Nigeria 18.7, SSA 17.7, world 6.4
4. `Safely managed sanitation (% of people)` — Nigeria 30.8, SSA 24.7, world 56.1
5. `At least basic drinking water (% of people)` — Nigeria 77.8, SSA 64.8, world 90.4
6. `Access to electricity (% of people)` — Nigeria 59.5, SSA 50.7, world 91.3
7. `Clean cooking fuel (% of people)` — Nigeria 22.0, SSA 20.5, world 72.4

Row 1's source line reads OPHI/UNDP global MPI; rows 2–4 UN IGME / WHO-UNICEF
JMP; rows 6–7 SE4All, all via World Bank WDI, all 2021, fetch dated in
`docs/kpi_benchmarks.md`. Values are point estimates; no intervals are drawn.

## The hover (frozen, amended 2026-10-23: one decimal, no numbers on the sheet)

One pre-formatted string dimension (`hover`, stage 7 composes it; the custom
tooltip prints it verbatim, bold) — the values **at one decimal** (the
user-pass rule: figures appear on hover only; the sheet itself prints no
numbers, see below), the benchmark text and the source, e.g. the child-deaths
row reads:

> Child deaths under 5 (per 1,000 births): Nigeria 117.6 per 1,000 live births ·
> sub-Saharan Africa (2021) 77.1 · World (2021) 39.6 · benchmark: 25 (SDG 3.2: by
> 2030, … at most 25 per 1,000 live births) · source: UN IGME, via WDI (2021)

(The headcount row's Nigeria value prints 33.0, not the dataset's 33.0441 — the
hover rounds what the reader acts on; the drawn `pos` keeps full precision.)

A second, static italic run carries the direction key
(`atlas_text.KPI_TOOLTIP_NOTE`): `▼ lower is better · ▲ higher is better`, the
world figures are other countries' statistics, for comparison only; **no view of
what makes any row the size it is** — the sheet carries no causal sentence. Since
2026-10-24 the same two glyphs also print **once per row, in the row header**
(`Poverty headcount (% of people) ▼`, `Clean cooking fuel (% of people) ▲`), so
the reader does not have to map "first three rows" onto the board by counting.
There is still deliberately **no per-mark good/bad badge**: a row's direction is
not a value's status ("not on track" needs a trajectory, and this atlas carries
none for these indicators), so the arrow says which end of that row is the good
end, never that a particular mark is good or bad.

## May not say (same discipline as SHEET_PAIRS's guardlist)

- **No "WHO standard met / not met"** as a badge or fill; the dot positions do
  the comparing, the words stay proportionate.
- **No state-level panel.** The benchmarks are national; putting a state on
  this sheet would compare a state with a world average as if they were the
  same kind of thing. The state panel the atlas already has is the time
  tab; this one stays national.
- **No Health-share comparison across countries.** Nigeria's Health dimension
  is structurally heavier (child mortality alone, re-weighted to a full third);
  what may be compared is the *raw* under-5 mortality indicator against
  UN IGME/WHO references — which is what row 2 is (`docs/CAUSAL_DECISION.md`).
- **"World" must never silently mean "every country".** On the headcount row it
  is the 109 developing regions' total; on the WDI rows it is the World Bank's
  aggregate. Both are named in the hover/subtitle.
- **No rank language between rows.** Each row has its own scale; "Nigeria is
  worst on the child-deaths row" is unavailable on this sheet the same way the
  state ordering was withdrawn (overlapping references do not resolve order).

## Palette risk (carried, packet check pending)

The pairs datasource could not take a ds-level palette (fail-the-load grey
shell, `docs/SHEET_PAIRS.md` 2026-10-22), but the maps', the time panel's and
the composition sheet's ds-level palettes all render, and this datasource has
their shape (plain columns holding real member strings), not the pairs'
param/CASE shape. The colour card rides the **right edge**, the composition
sheet's shape — the one right-edge colour card this generator has proven
renders (sheet 1's identical declaration never has; the Analysis → Legends →
Colour Legend fallback stays in `docs/PUBLISH.md`). **Pending manual checks:**
(1) the sheet loads with the three colours correct and no mark in the default
palette **and the three silhouettes render as their members** (green Nigeria
map, blue Africa map, orange globe — a missing/blank shape means the
`type='shape'` rule did not bind); (2) the colour legend draws (or the reader
needs the one-click fallback); (3) the hover prints the composed line, not
field soup; (4) the manual row order holds (headcount first, cooking last);
(5) no numbers print on the sheet (the axis-off rule hides ticks + title; if
they still print, the scope='cols' axis rule is inert and needs a packet).

## Built record

- Stage 7 extended (`build_dots`): asserts 7 benchmark rows + 5 native rows,
  20 marks, every mark's `pos` in (0, 1], series labels equal
  `atlas_text.KPI_SERIES`'s members, SSA absent exactly on the headcount row.
  **2026-10-23 amendment:** marks appended in reversed series order per row
  (Nigeria last → drawn on top of the one near-coincident pair, clean cooking
  fuel); hover values printed at one decimal; `build_shape_images()` renders
  the three silhouettes (Nigeria from the shipped ADM1 rings; Africa flat,
  world a solid cut-out globe, from Natural Earth 110m; transparent PNGs on
  one square canvas) + the best-effort authoring copy.
- Stage 5 (`visual_kpi_board`): gate PNG `8_where_nigeria_stands.png` — one row
  per KPI, the silhouettes pasted at the marks' positions (`AnnotationBbox`),
  grid without tick numbers; legend; the pairs gate renamed
  `9_how_measures_pair.png` (kept-set updated; stale
  `8_how_measures_pair.png` pruned by the stage's own sweep).
- Stage 6: constants (`KP_*`), extract `kpi_dots.hyper` (20 rows) declared as
  `KP_COLUMNS` (kpi/series/hover string dims + pos real measure), worksheet via
  `worksheet_xml` (rows `[none:kpi:nk]`, cols `avg:pos:qk`, mark **Shape**, lod
  hover + colour+shape encodings on `series`, pane size factor 2.5, manual sort
  dictionary on the CSV order, table-level axis-off rule hiding the position
  axis' numbers), window with left rail + right colour card + top
  columns/title, datasource with `palette_block` colour palette **plus the
  `type='shape'` rule mapping each member to its KPI_Geo silhouette**, and
  `shape_pack_xml()` embedding the three PNGs in `<external><shapes>` before
  `</workbook>`. Grammar source: `CH24_BBOD_ChurnTurnover_Updated.twb`
  (roemeren/tableau-workbook-extractor sample, fetched 2026-10-23), which
  carries all three pieces; `type='shape'` (never `type='palette'`), the
  `map to` = `palette-folder/file.png` (the pane-level constant
  `<format attr='shape' value='Other/transparent.png'/>` in the same twb and
  HR #RWFD confirms the reference form), and the `<shape name=` embedding with
  the same folder-prefixed name.
  validate()/hyper-schema/pack extended. 2026-10-23 exit 0 (twb 249 KB with the
  embedded base64), extract schema read back matches; **interactive render
  checks pending** (colour card draws and binds the three hues; silhouette
  marks render at the pane size; no numbers visible on the sheet; hover prints
  the one-decimal line; manual row order holds).

---

## Built record — 2026-10-23 follow-up passes (everything below supersedes older lines)

Five same-day user passes changed the board after the freeze. What now ships:

- **World = purple globe with longitude lines.** KPI_SERIES world member is
  #9467BD (purple; Africa keeps blue, Nigeria green — the colour card follows
  the constant). The globe draws as a solid disc **carved in alpha**: the
  colour card TINTS Shape marks by the PNG's alpha (in-app evidence: the
  africa/nigeria members match their series hue and a white-line world.png
  fused into a flat violet disc), so the visible white geometry rides on
  alpha-forgiveness, not RGB — meridian lines every 60° at ~55% of the
  disc's tint, coastlines every ≥0.2%-of-disc landmass at ~75%, RDP-decimated
  (_draw_globe in stage 7). Parallels were built and withdrawn the same day:
  the user narrowed the ask to "maybe just longitude lines".
- **Labels beside the marks: pre-formatted strings.** The twb number-format
  lanes (ds-level default-format='0.0' on pos in both copies, pane
  datalabel rules) turn out inert for these federated-extract sheets' LABELS
  — the label printed Tableau's General 4-decimal line (0.3367) at every
  attempt, the same reason the rank panel's "\"R\"0" integer print was
  never actually exercised. The lane that works is the atlas's own
  pre-formatted-string trick: stage 7 writes pos_label ( .3), the KPI
  sheet puts it on the **Label pill** (<text column=… none:pos_label:nk>,
  the CH24 Shape/Legend byte-shape), mark-labels-show turns printing on.
  pos stays the position encoding; its default-format stays for the axis.
- **Overlap handled by culling.** The one near-coincident pair (clean cooking
  fuel: Nigeria 1.0 vs sub-Saharan Africa ~0.93, ~2% of the axis apart) drew
  colliding labels; mark-labels-cull='true' (real-grammar, HR #RWFD) lets
  Tableau drop the collided label; marks still draw in the extract order, so
  Nigeria stays in front (cook row: green over blue), the hover still says
  both values at one decimal.
- **Bigger maps, smaller values.** Size factor 4.0 (twice the frozen 2.5);
  the surviving label font is 7 under the pane datalabel rule
  (color-mode='auto' font-size='7', HR's integer font sizes). The
  pre-tableau gate renders the same: 8_where_nigeria_stands.png at
  zoom 0.115, one-decimal annotate at 6pt, offset labels on tied marks.
- **Position axis rule present but unverified.** The worksheet-level axis
  rule carries <encoding attr='space' … major-origin='0' major-spacing='0.5'
  scope='cols' type='space'> (hr_rwfd byte-shape) intended to pin ticks to
  0 / 0.5 / 1. The workbook loads with it (2026-10-23, no error dialog), but
  the tick positions are NOT yet verified on screen — the small session window
  clips the axis row. If it proves inert at publish, delete kpi_axis_ticks()
  and let Tableau pick its default ticks.
- **In-app verified 2026-10-23** (PrintWindow captures of the loaded twbx):
  title Tableau Public - Nigeria-MPI-Equity-Atlas, no dialogs, 20 marks,
  the meridian globe renders, labels  .3/0.3/0.4/0.5/… at the small font,
  hover tooltip prints the one-decimal values line plus the direction key.
  Still pending publish-time checks: hover on a cull-hidden mark, the
  checklist of colour-card hues, the axis tick row.

---

## Built record - 2026-10-24 pass (arrows, dodge, amber globe, quarter-length labels)

The pass answered five things at once. Everything below was verified twice: in
the stage-5 gate PNG and in the running app, by loading a probe of the built
package pruned to this one sheet (`probe_only.py`, because Tableau re-opens a
workbook on the sheet it last showed, never on the first `<window>` -
`FIX_LEDGER` L6).

### 1. The world's globe is meridians only

`_draw_globe` no longer strokes Natural Earth's coastlines. At mark scale (a
~40 px shape) the 110m coastline is sub-pixel noise that fought the graticule,
and the ask was longitude lines only. What is left is the disc plus **seven
orthographic meridians** (0, +/-30, +/-60, +/-80 degrees): on a sphere seen
face-on a meridian projects to a vertical ellipse of semi-width
`R*sin(delta)`, so the set bows and the disc reads as a globe instead of a
striped coin. Because the mark is now pure geometry, `_draw_globe` takes no
coordinates at all - the disc fills the icon canvas and `_finish_icon` trims it -
and the Douglas-Peucker helper that only the coastline layer used is gone.

### 2. The world's colour: amber `#E69F00`, and why that hex

`atlas_text.KPI_SERIES` world member is now **amber**, not the purple. The
board already spends a **green** landmass (one country) and a **blue** one (one
continent), so the third mark cannot be green or blue; amber is the hue that
stays clear of both for a colour-blind reader too (it is Okabe-Ito's partner to
`#009E73`, which the Nigeria mark already uses), it exists in the project's
palette vocabulary already (the composition sheet's Education share), and on a
disc with meridians it reads as sand/land under a graticule - "the planet" -
rather than as a fourth brand colour. Purple is a one-hex revert if the amber
reads wrong. Note that the colour is *not* carrying any judgement: the arrows
(below) carry direction, the hue carries identity.

### 3. Per-row direction arrows, in the row header

`KPI_ROW_LABELS` now ends each row label with `▼` (lower is better) or `▲`
(higher is better), and `atlas_text.KPI_DIRECTION_ARROW` maps the two glyphs to
the benchmarks CSV's `direction` values. Stage 7 **asserts** each label's glyph
against the CSV, so a re-sourced or re-ordered row cannot leave an arrow
pointing the wrong way. The glyph rides the dimension member text - a data
value - so the manual sort dictionary still matches and **no new column,
encoding or mark** was needed; the alternative (a second axis or a badge on the
marks) would have put a status on a data point, which the guardlist forbids.
The subtitle and the hover key now read `▼ lower is better · ▲ higher is
better` (previously "first three rows ... the rest ...", which forced the reader
to count rows on a board that has arrows now).

Four labels were **shortened** in the same pass, because the arrow lengthened
them and the header column is 230 px: "Child deaths under 5
(per 1,000 births)" -> "Under-5 deaths per 1,000 births", "At least basic
drinking water (% of people)" -> "Basic drinking water (% of people)", "Access
to electricity (% of people)" -> "Electricity access (% of people)", "Safely
managed sanitation (% of people)" -> "Safely managed sanitation (%)". Same
units, fewer words; the hover and the reference table still carry the full
names.

### 4. Dodge: overlapping silhouettes are spread, without lying about the value

Tableau cannot offset marks inside a discrete row, so the dodge is done in the
data (`_dodge`, stage 7) and `pos` - already documented as **layout, not data**
- carries it. Rules, in order:

- the mark at the row's largest reference stays exactly at 1.0, so the right
  edge keeps meaning what the axis caption says;
- any mark within `KPI_DODGE_MIN_GAP` (0.07 of the axis, roughly one icon) of
  the one above it slides **left** just far enough to clear, floored at 0.02;
- the printed number is the mark's **true share** (`pos_label`), never the
  dodged position, and the hover still prints the raw values.

On 2021's numbers two rows dodge: open defecation (SSA 0.9465 -> 0.93 against
Nigeria 1.0) and clean cooking fuel (SSA 0.2831 -> 0.2339 against Nigeria
0.3039). Every other row is untouched. The stage-5 gate reads `pos_label` for
the number (it used to recompute `f"{pos:.1f}"`, which would have printed the
dodged value) and plots `pos`, so gate and sheet agree mark for mark.

### 5. Smaller value labels, and a legend that stops covering a mark

- The pane datalabel rule's `font-size` goes 7 -> **6**; `mark-labels-cull`
  stays on as the backstop.
- The gate's legend moved from inside the plot (lower right, where it sat **on
  top of the electricity row's world mark**) to a horizontal strip **below the
  axis**, which is the one overlap a QA gate must never ship.
- The row header column is pinned to **230 px** with the field-scoped width rule
  the composition sheet already ships and the one sourced from
  ClinicPerformanceDashboard/FinanceDashboard
  (`<style-rule element='header'><format attr='width' field=... />`), so the
  longer labels print on one or two lines instead of three.

### Publish-time checks this adds

1. Both glyphs render **in the row headers**, `▼` on the first three rows and
   `▲` on the last four (a missing glyph means the member strings were
   rewritten somewhere between the extract and the sheet).
2. The world marks are **amber with visible vertical meridians**; if the disc is
   flat or striped-but-wrong, the shape file did not rebind (the `type='shape'`
   rule) rather than the colour being wrong.
3. **No two silhouettes touch** on any row, and no printed number sits on
   another one.
4. The colour card still draws (it is the sheet's one right-edge card, and it
   is now the third hue).
5. At the published width the header column shows each label on one or two
   lines - if it wraps to three, the 230 px rule was lost.

---

## Amendment - 2026-10-24 (later pass): the subtitle, and where the world caveat went

`KPI_SUBTITLE` was 346 characters; it is now 135:

> How Nigeria compares with Africa, the world and the SDG target, 2021 ·
> each row is its own scale · ▼ lower is better, ▲ higher is better

- The sentences that went were the ones the sheet itself already answers:
  *"a mark's number is its share of that row's largest reference"* is now the
  Column axis' own caption (`Share of the row's largest reference`), and
  *"the actual values, benchmark and source are on hover, at one decimal"* is
  what a hover is for.
- **The world caveat moved, it did not disappear.** "The world line is
  developing countries (109 of them, OPHI/UNDP), not every country" is a
  standing rule for this sheet ("May not say", above: both named in
  hover/subtitle). It now rides the number it qualifies: the headcount row's
  hover prints `World 22.0 (109 developing countries)` (stage 7 special-cases
  the `SI.POV.MPUN` row), and the other rows' world figures are the World Bank
  aggregate named by their own source string.
- `"point estimates"` moved into `KPI_TOOLTIP_NOTE` (the hover's second line),
  which also still carries the direction key and the no-causal-view sentence.
- Toolbar words shortened with it: the Column axis caption is now
  `Share of the row's largest reference` (was "…largest reference point"), the
  Label pill's caption is `Share (one decimal)` (was "Value beside the map"),
  and the tooltip's caption is `Values` (was "Values behind this mark").
