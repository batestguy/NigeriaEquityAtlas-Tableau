# Publishing to Tableau Public

Tableau Public has **no write API and no publishing CLI**. `tabcmd` targets Tableau
Server/Cloud, not Tableau Public, and the `tableau` MCP server available here is
read-only (search, metadata, download). Publishing is a GUI action behind an
interactive account login, so this is the one step that has to be done by hand.

Everything up to that point is automated and reproducible: `scripts/06_build_twb.py`
produces a validated `.twbx` with the data packaged inside it.

## What is already built

`tableau/Nigeria-MPI-Equity-Atlas.twbx` (25 KB) contains:

```
Nigeria-MPI-Equity-Atlas.twb     the workbook
Data/mpi_atlas_2021.hyper       37 rows, one per state
Data/mpi_trends_panel.hyper     148 rows, 37 states x 4 survey rounds
```

The data ships as **Hyper extracts**, not CSV. This is not a preference: Tableau
Public refuses any workbook whose datasource is not an extract — *"Workbooks saved
to Tableau Public must use extracts"*, error `3C242D89` — and it does **not**
convert a live file on save. Stage 6 writes the extracts itself with
`tableauhyperapi`, and validates the schema it wrote back against the declared
columns before packaging.

Five sheets and one dashboard, `Equity Atlas`. **Verified by opening the workbook
in Tableau Public and looking at every sheet on 2026-10-06.**

| Sheet | Type | Marks |
|---|---|---|
| Where poverty sits | georeferenced scatter | `AVG(lon)` x, `AVG(lat)` y, `state` on Detail (geographic role), `mpi_band` on Colour, `mpi` labelled |
| Dimension breakdown (three panels, not stacked) | bar | three dimension contributions on Rows, `state` on Columns |
| Poverty vs conflict | scatter | `mpi` x, `conflict_exposure_index` y, `state` labelled, `quadrant` on Colour **and Shape** |
| Poverty over time | line | `mpi` by `survey_year` on Columns, `state` on Colour — one line per state on one axis |
| Incidence vs intensity | scatter | headcount ratio x intensity, `quadrant` on Colour and Shape, `state` labelled |

Two sheets carry their limitation in the **title**, deliberately:

- **`Where poverty sits` is not a filled map.** It is a correctly georeferenced
  scatter of the 37 state capitals. See "The map problem" below.
- **`Dimension breakdown (three panels, not stacked)` is not a stacked bar.**

## Steps

**Tableau Public Desktop 2025.1 is already installed** at `C:\TableauPublic`
(`winget install --id Tableau.Public -e`). Nothing to do here. To reinstall on
another machine use the same command — not the vendor site, where
`tableau.com/downloads/public/pc64` and `downloads.tableau.com` both return
**HTTP 403** on this network.

Do **not** install Tableau Desktop (the paid product): a different application,
cannot open modern workbooks on an older release, and cannot save to Tableau
Public. See `docs/HANDOFF.md` §3b.

1. Sign in to your Tableau Public account.
2. Open `tableau/Nigeria-MPI-Equity-Atlas.twbx`. **It has been opened successfully on
   this machine** — it loads with no error dialog and renders (see `HANDOFF.md` §3).
3. **File > Save to Tableau Public.**
4. Wait for the upload and the render, then open the live URL and confirm all five
   sheets are present and that `Where poverty sits` shows 37 points.

## The map problem — what was tried, and why it is not a filled map

**This was verified in the application on 2026-10-06 and four approaches failed.**
Recording them so nobody repeats the cycle:

| Attempt | Result |
|---|---|
| `cols = state / SUM(lat) + SUM(lon)` | 74 small lat/lon **bar charts**. This is what shipped for the workbook's whole life; the handoff called it "renders". |
| Hand-written `[Latitude (generated)]` / `[Longitude (generated)]` | Red unresolved pill on Columns, blank canvas. Tableau synthesises these; declaring them conflicts with the real definition. |
| No coordinates at all, geographic role on `state` alone | 37 coloured numbers as a **text table**. The role alone is not sufficient. |
| **`AVG(lat)` / `AVG(lon)` with `[Geographical]` semantic roles on both** | **Works.** Correctly georeferenced, latitude axis 7–13 as Nigeria actually is, 37 labelled points coloured by band. |

So the shipped sheet is a **georeferenced scatter**, not filled polygons. A filled
map needs the generated-geographic-field pairing, which Tableau only writes when a
sheet is built through the GUI.

**To upgrade it to a real filled choropleth — one minute, by hand:**

1. Open `Where poverty sits`.
2. On the Data pane, right-click `lat` → **Geographic Role** → **Latitude**. Same
   for `lon` → **Longitude**.
3. Double-click `state` in the Data pane. Tableau rebuilds the sheet as a filled map
   using its built-in Nigeria ADM1 geography.

`scripts/05_preview.py` renders what that will look like:
`docs/preview/1_where_poverty_sits.png` is a true filled choropleth drawn in
matplotlib from the same 37 rows, so the target is documented.

## Open issues, all safe to fix in the GUI

- **`Dimension breakdown` is not a stacked bar.** Three measures on Rows give three
  aligned panes. The Measure Names/Values pair was tried from XML and drew one
  18,000-tall bar per state, because a hand-written pair also needs the
  measure-values filter. **To fix by hand:** Analysis → Measure Names → Columns;
  Measure Values → Rows; `state` → Columns (below Measure Names); `state` → Detail;
  Colour → the *Measure Names* field so each dimension gets its own colour.
- **The radar chart is still not generated** — see below.
- **Alt text is not set.** Tableau auto-generates a description; edit it on each
  sheet. Keep it descriptive and objective, not interpretive.
- **No legend zones were verified on the published dashboard.** The workbook declares
  the text and KPI zones; colour legends render from the Marks card on each sheet,
  but check them on the live viz.

## If something looks wrong

Most likely, in order:

- **`Where poverty sits` shows text or numbers instead of points.** The lat/lon
  semantic roles are missing. Confirm via right-click `lat` → Geographic Role →
  Latitude, and `lon` → Longitude.
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

## Two things left deliberately to the GUI

**The radar chart** (the spec's fifth visual) is not generated. A radar needs a
polygon mark driven by computed path fields, the most fragile part of Tableau's XML
grammar to hand-write. To add it:

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
- `get_workbook_contents` — confirms all five sheets and the dashboard exist
- `get_workbook_image` — fetches a rendered PNG of a named view, proving it draws

This is the step that catches a viz that uploaded but renders empty.