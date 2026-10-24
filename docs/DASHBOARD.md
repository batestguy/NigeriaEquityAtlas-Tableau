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
