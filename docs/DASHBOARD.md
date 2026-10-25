# The Overview dashboard (tab 1)

Status: **built 2026-10-24**, render-verified. One page that shows three of the
shipped sheets at once. Grammar provenance, layout decisions and what is
deliberately absent are all below; the build lives in
`06_build_twb.py::overview_dashboard_xml()`.

## What it is

A fixed **1600 x 1000** Tableau dashboard named `Overview`, first in the window
list so the workbook opens on it:

| Zone | Sheet | Geometry (px) |
|---|---|---|
| title band (text zone) | — | 0,0 1600x64 |
| top left | `Where poverty sits` | 0,64 790x400 |
| top right | `Where poverty clusters` | 798,64 802x400 |
| bottom, full width | `How poverty is made up` | 0,472 1600x528 |

Title band: **Nigeria MPI Equity Atlas**  one country, two realities · 2021
(`atlas_text.OVERVIEW_TITLE` / `OVERVIEW_SUBTITLE`, the project's own D6
framing).

## Grammar, and where each piece came from

Nothing here was guessed. Two sources, both real files:

1. **The dashboard shell** — `<dashboard>`, a bare `<style />`, `<size>` with the
   four bounds, `<zones>` with a `layout-basic` root at `100000 x 100000` and
   children carrying absolute `x/y/w/h`: our own three reference dashboards,
   which already load and render (this file's output since 2026-10-18).
2. **The pieces our file did not have** — from
   `SoftwareRetailAnalytics.twbx`, the Tableau Public dashboard the author
   pointed at (downloaded and unpacked 2026-10-24 via the `tableau` MCP server,
   `docs/FIX_LEDGER.md` §O):
   - an **embedded worksheet zone**: `<zone … name='<sheet>'>` with **no**
     `type-v2`, a `<layout-cache type-h='cell' type-w='cell' />` child and a
     `<zone-style>` (its id 128);
   - the **viewpoint** that binds the sheet's zoom:
     `<viewpoint name='<sheet>'><zoom type='entire-view' /></viewpoint>` inside
     the dashboard's `<window>` (its `d1. Performance Overview` window);
   - **coordinates are 1/100000 of the canvas, per axis**, so x/w are fractions
     of the width and y/h of the height — the helper in the builder converts per
     axis rather than reusing one scale.
3. **The page title is a TEXT ZONE, not `<layout-options><title>`.** The
   layout-options block is what Tableau-authored files carry and our other
   dashboards declare it, but it did **not** render on this dashboard
   (2026-10-24 render: the page opened with no title band), while a text zone is
   the object the reference dashboards already prove. Recorded so nobody
   re-tries the layout-options lane expecting a title.

## Why three panels, and why these three

The first build was a 2x2 with the time panel in the fourth cell. The render
settled it: **a dashboard is not a contact sheet.** At a quarter-page each, the
composition bar compressed to ~15 px per row (labels colliding) and the time
panel's small-multiple labels truncated to "Conflic..". The maps are indifferent
to size, so they get the top row; the composition gets the full width below,
where 17 bars breathe.

The **time panel** stays a tab: it is a page of six small multiples pinned to one
state, and at card size it is decoration rather than information. The **KPI
board** is deliberately absent: it is national while these three are state-level,
and `docs/SHEET_KPI.md` ("No state-level panel", inverted) forbids reading a
state's figure against a country average — adjacency on one page would invite
exactly that. The **pairs board** is the interactive coda and stays a tab.

## What an embedded sheet does NOT bring with it

Cards are window-level objects, not part of a worksheet, so on the dashboard the
sheets appear **without** their left-rail filter/parameter cards and without
their colour legends. That is why only these three sheets are used: none of them
depends on a card to be read (the maps' colour legend is a known open defect,
`docs/PUBLISH.md`; the composition's state checklist only adds states to a
default that already shows 17). Putting the composition's checklist or the time
panel's measure picker on the page means adding **filter / parameter-control /
legend zones** — three zone types we have not yet proven. That is the next wave
if the reader needs the interaction, and the reference workbook carries all three
(`paramctrl` x2, `color` x3) as the source to copy.

## Also landed in the same pass

Both map sheets had their **lat/lon axes** printing on the dashboard (a hand-drawn
polygon map with a 3..15 longitude ruler looks like a scatter plot). They are now
hidden with `<style-rule element='axis'>` + `attr='display'` naming the field per
scope — the same attribute shape the composition sheet already uses to drop its
generated "Multiple Values" axis (`map_axis_hidden()`, stage 6). This fixes the
two map **tabs** as well, and closes the "axis headers off" item that had been
sitting in `docs/PUBLISH.md` as a GUI click.

## Publish-time checks

1. The page opens **first** and the title band reads the two runs (bold name,
   smaller framing line).
2. All three panels draw, with their own titles and subtitles inside the border.
3. No lat/lon rulers on either map.
4. The composition's 17 rows do **not** collide at the published size; if they
   do, raise `map_h` in `overview_dashboard_xml()` (400 -> 360 buys the bar 40 px)
   rather than shrinking the font.
5. The published viz scales the fixed canvas to the browser; check nothing
   important lives in the outer 8 px on a narrow window.
6. Clicking a panel does nothing (no actions): if navigation is wanted, it is a
   `goto-sheet` **button zone** (`<button action='tabdoc:goto-sheet …'>` with a
   `<button-visual-state><image-path>`), the shape the reference file uses 81
   times.

---

## 2026-10-25 — the state selector and the two colour legends

Status: **built and render-verified** in Tableau Public 2026.2 (captures
`%TEMP%\opencode\overview_final3.png`, `filter_kano_test.png`,
`dim_tab_check.png`). Grammar and dead ends: `docs/FIX_LEDGER.md` §Q.

### The page now carries four kinds of zone

| Zone | Kind | Geometry (canvas px) |
|---|---|---|
| title band | `type-v2='text'` | 0,0 1236x64 |
| state selector | `type-v2='paramctrl'` | 1244,10 348x44 |
| `Where poverty sits` | embedded sheet | 0,64 480x372 |
| `Where poverty clusters` | embedded sheet | 488,64 480x372 |
| MPI band legend | `type-v2='color'` | 976,64 624x190 |
| Neighbourhood legend | `type-v2='color'` | 976,254 624x182 |
| `How poverty is made up` | embedded sheet | 0,444 1600x556 |

The maps ceded 310 px of width to the legend column. The composition gained the
freed 76 px of height (528 -> 556) and is now 32 px per bar at the 17-bar default.

### What the selector does

One workbook parameter, `State select` (caption **State**), list domain:
`(All states)` then the 37 states. Each of the three extracts carries a calculated
boolean `state_match` and the sheet filters on it, so a pick moves **all three
panes at once** — which a filter card could not do, since the panes read three
different datasources (§Q3). `(All states)` is the shipped default.

On the composition the "(All states)" arm also carries the 17-bar default, so the
page opens exactly as it did before; a pick overrides it. The composition tab's
old 17-of-37 checklist card is retired in favour of the same parameter card
(`docs/SHEET_DIMENSIONS.md`, amendment 2).

### What the legends do

Each map gets its own `type-v2='color'` zone bound by `name` to its sheet. The
title is the colour field's caption, so both titles say what is being compared:
`MPI band (Multidimensional Poverty Index)` and `Neighbourhood type (this state's
poverty, beside the states it borders')`. Members are whatever is in view: three
of the four neighbourhood types at "(All states)", one member per legend when a
single state is picked.

This **closes the colour-legend question for the dashboard**, and it narrowed the
old open item: a legend zone draws even though `Where poverty sits`'s own window
card does not. The card defect on that **tab** stays open (`docs/PUBLISH.md`).

### Publish-time checks added

1. The selector lists `(All states)` plus 37 names, and picking one moves all
   three panes together (hover a map afterwards to confirm the number belongs to
   that state).
2. Both legend titles print in full and every member label is complete.
3. The composition still opens on 17 bars; the left control on that tab reads
   `(All states)`.

### Second pass, same day — the composition's legend

The Overview now carries **three** `type-v2='color'` zones: the two map legends
(stacked, 624 px column) and the composition's `Measure Names` legend in the
composition row's right-hand 292 px (`param='[federated.0mpidimshare].[:Measure
Names]'`, referenced bare like its palette buckets). The composition pane is
therefore 1300 px rather than 1600, which wraps its subtitle to two lines — read
and accepted. The three members print as Education / Health / Living standards.

Also in this pass: the cluster hover's `spatial_group` was restored to a `none:`
dimension reference (a `sum:` aggregate over a string column prints an aggregate
instead of the member's words) and stage 6 now asserts both leading hover fields
are dimension references (`FIX_LEDGER` §Q7).

---

## 2026-10-25 (second page) — "A state, in context"

Status: **built and render-verified** (captures `%TEMP%\opencode\context_only2.png`
at full size, `context_whole2.png` with the canvas scaled to see the whole page).
Build: `06_build_twb.py::context_dashboard_xml()`.

The author asked for `Where Nigeria stands`, `How measures pair` and
`A state over time` on one page. This is that page — and it **overrides a frozen
rule** in `docs/SHEET_KPI.md` ("No state-level panel"), recorded as amendment 1
there with the mitigation.

### Layout (1600 x 1300)

| Zone | Sheet | Geometry (px) |
|---|---|---|
| title band (text) | — | 0,0 1000x150 |
| panel state control | `paramctrl` | 1020,10 570x40 |
| pairs X control | `paramctrl` | 1020,60 570x40 |
| pairs Y control | `paramctrl` | 1020,110 570x40 |
| top left | `A state over time` | 0,150 880x620 |
| top right | `How measures pair` | 888,150 712x620 |
| bottom band | `Where Nigeria stands` | 0,778 1316x512 |
| KPI colour legend | `type-v2='color'` | 1324,778 276x512 |

The page is **1300 tall**, so in a 1030 px window it does not fit on screen —
by design, a reader scrolls. It renders correctly at full size and, because zone
coordinates are fractions of the canvas, it can be checked whole by rebuilding
with a smaller `<size>` (see `FIX_LEDGER` §S3).

### Controls, and why there are three

Cards do not travel (`FIX_LEDGER` O6). Without zones the two interactive sheets
would open frozen, so:

- **Panel state** — the time panel's own parameter (caption "Panel state"),
  driving `[state] = [Parameters].[Panel state]`. It is deliberately **not** the
  Overview's `State select`: that one has an `(All states)` member, which on a
  six-pane panel would draw 37 lines into every pane. The tab carries the same
  control as a parameter card, replacing its old dropdown.
- **X axis / Y axis** — the pairs board's two existing parameters.

**Not provided:** the panel's Measure Names checklist. Turning it into a
dashboard control needs a third parameter plus a whitelist calculation; the page
therefore shows the six default measures.

### What is deliberately absent

The two maps and the composition stay on the `Overview`; this page is the
"into the detail" page, not a second front door. Nothing links the two pages yet
(no `goto-sheet` button zone) — the tab bar is the navigation.
## Axis labels, a final sweep (2026-10-25)

Every axis on every surface was read off a render and fixed where it printed an
internal name or said nothing:

| Sheet | Before | After |
|---|---|---|
| How measures pair | `Avg. value of the chosen X measure` | `Avg. X` (and `Avg. Y`) â€” the dropdowns are already labelled "X axis measure" / "Y axis measure", so the axis only has to say *a mean of that* |
| A state over time | `survey_year` (raw field name) | `Survey round` |
| Where Nigeria stands | `Avg. Share of the row's largest reference` | unchanged â€” it says what it is |
| Where Nigeria stands (rows) | `Poverty headcount (% of people) â–¼` | `Poverty headcount (%) Â· lower is better` |
| Both maps | `Avg. lat` / `Avg. lon` | hidden (2026-10-24, `map_axis_hidden`) |
| How poverty is made up | `Multiple Values` | hidden (`dim_table_style`) |

Verified by capture on all three tabs. On the `A state, in context` page the KPI
band's row labels truncate ("lower is bettâ€¦") because the band is 1316 px wide
there; the tab shows them whole, and the page is a secondary surface for that
board.

## The cover tab (2026-10-25) â€” built in the GUI, not in XML

**Status: the XML route failed the load; the GUI route is the shipping path.**

The author's ask: publish the two dashboards with an illustration as an intro
page, with a contents list and intro text on it, and the other sheets hidden.

### What is in the repo

- `tableau/assets/cover.jpg` â€” the illustration (1408x768, 1.83:1). It is the
  picture the polish plan asked for: two women, northern and southern attire,
  embracing, against a green market.
- `atlas_text.COVER_*` â€” the cover's words: the D6 title, the subtitle, a
  three-sentence intro, the two contents entries, and the credit line.
- `06_build_twb.py::cover_dashboard_xml()` â€” the page built as XML (1408x768 so
  the image is 1:1; a 566 px opaque panel on the left third carrying the text).
  **It is not wired into the workbook**, because every version of it failed to
  load:
  - full-bleed `type-v2='bitmap'` zone + the file packaged under `Image/` â€”
    workbook opened with an empty title (the load-failure signature);
  - the same zone with a `<zone-style>` child (the shape all 18 reference bitmap
    zones carry) â€” same failure;
  - the text panel alone, no bitmap at all â€” same failure.

  So the fault is in the page, not only the image, and it is not yet isolated.
  The next session should bisect it with a **single-dashboard packet**: the cover
  page alone in a scratch workbook, one variable per build, the way Â§O did the
  Overview. Schema-validity is not evidence here â€” the file validated and still
  would not open.

### The route that works, by hand (about two minutes)

1. Open `tableau/Nigeria-MPI-Equity-Atlas.twbx`, go to the `Overview` tab.
2. `Dashboard â†’ New Dashboard`; rename its tab **Start here**.
3. With the new dashboard open: `Insert â†’ Image`, choose
   `tableau/assets/cover.jpg`. Tableau copies the file into the workbook on save.
4. Size the image to fill the page (the canvas is 16:10; the image is 1.83:1, so
   drag it to the full width and let it crop top/bottom slightly).
5. Add a text box over its left third, background `#0B2E1D`, and paste the words
   from `atlas_text.COVER_TITLE`, `COVER_SUBTITLE`, `COVER_INTRO`, `COVER_TOC`
   and `COVER_CREDIT`.
6. Drag the **Start here** tab to the far left so it opens first.
7. To hide the building-block sheets (both maps, composition, time panel, KPI
   board, pairs board): right-click each tab â†’ **Hide**. They stay usable by the
   dashboards; only their tabs go.
8. `File â†’ Save to Tableau Public`.

`scripts/06_build_twb.py::hide_worksheet_tabs()` does step 7 in XML and is
exercised by `ATLAS_KEEP_TABS=1` (which keeps the tabs); it was left switched off
because it could not be verified against a workbook that also had a cover.

### Before publishing

The illustration's provenance is still **UNKNOWN** in `docs/POLISH_PLAN.md`.
Tableau Public is a public upload under the author's name: the terms must be
recorded before the cover ships.

