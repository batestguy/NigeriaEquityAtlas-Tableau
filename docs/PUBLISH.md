# Publishing to Tableau Public

Tableau Public has **no write API and no publishing CLI**. `tabcmd` targets Tableau
Server/Cloud, not Tableau Public, and the `tableau` MCP server available here is
read-only (search, metadata, download). Publishing is a GUI action behind an
interactive account login, so this is the one step that has to be done by hand.

Everything up to that point is automated and reproducible: `scripts/06_build_twb.py`
produces a validated `.twbx` with the data packaged inside it.

## What is already built

`tableau/Nigeria-MPI-Equity-Atlas.twbx` (13 KB) contains:

```
Nigeria-MPI-Equity-Atlas.twb     the workbook
Data/mpi_atlas_2021.csv          37 rows, one per state
Data/mpi_trends_panel.csv        148 rows, 37 states x 4 survey rounds
```

Five sheets and one dashboard, `Equity Atlas`:

| Sheet | Type | Marks |
|---|---|---|
| MPI by state | filled map | `state` on Detail (geographic role Nigeria), `mpi` on Colour |
| Dimension breakdown | stacked bar | three dimension contributions on Rows, `state` on Columns |
| Poverty vs conflict | scatter | `mpi` x, `conflict_exposure_index` y, `state` labelled, sized by `fatalities` |
| Poverty over time | line | `mpi` by `survey_year`, one line per state (from the panel datasource) |
| Incidence vs intensity | scatter | headcount ratio x intensity, coloured by quadrant, sized by poor count |

The data is packaged as CSV with a `textscan` connection, so there is no live
connection to break. The original spec's Google Sheets intermediary is not needed:
Tableau converts the local file to an extract on save, and the MPI survey only
updates annually, so a 24-hour refresh would be pointless.

## Steps

1. Install **Tableau Public Desktop** (free) from <https://public.tableau.com/app/discover>.
   Do not use Tableau Desktop 2019.4, which is installed on this machine and is far
   too old to open a modern workbook.
2. Sign in to your Tableau Public account.
3. Open `tableau/Nigeria-MPI-Equity-Atlas.twbx`. Tableau will ask to locate the data;
   accept the packaged paths.
4. **File > Save to Tableau Public.**
5. Wait for the upload and the render, then open the live URL and confirm all five
   sheets are present and the map draws Nigeria's states.

## If something looks wrong

Most likely, in order:

- **The map is blank or states are unrecognised.** Tableau's geocoder needs the
  geographic role; the workbook assigns `[Country].[Name] = "Nigeria"` to `state`.
  Confirm via right-click `state` > Geographic Role > State/Province. If any state
  is unresolved, check `docs/data_quality.md` for the FCT naming trap.
- **Marks look wrong on a sheet.** The mark classes and shelves are declared in the
  XML; re-check the sheet against the table above.
- **Tableau reports a data error.** The declared column ordinals are validated
  against the packaged CSV headers at build time, so this would indicate a genuine
  mismatch — re-run `scripts/04_merge.py` then `scripts/06_build_twb.py`.

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

**Colour scales and captions.** The workbook ships with default colour encodings.
Before publishing, set the choropleth to a sequential scale (it is a rate, not a
category) and add the source attribution below the dashboard title.

## Attribution to put in the workbook description

> Poverty: OPHI / UNDP Global MPI (MICS 2021), CC0 / CC BY.
> Conflict: UCDP Georeferenced Event Dataset, CC BY-IGO.
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