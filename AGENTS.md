# AGENTS.md — Nigeria MPI Equity Atlas

## What this is

Greenfield project: an interactive **Tableau Public** atlas of Nigeria's Multidimensional Poverty
Index (MPI) at state level (36 states + FCT = 37 rows), disaggregated into the three MPI dimensions
(health, education, living standards), with conflict (ACLED) and climate (Open-Meteo) overlay layers.

The authoritative spec is **`TableauNigeria MPI Equity Atlas.txt`** — read it before planning. It
defines the five visuals, the transformation steps, the deployment workflow, and the free-tier
constraints. Don't restate it here; follow it.

**Machine map:** `ENVIRONMENTS.md` in the project root — **local only, deliberately not
committed** (it documents the machine, not the project). Read §2 (TRAPS), §3 (Python),
§10 (command cookbook) before running anything. It is verified-by-execution and takes
precedence over recollection. If it is missing, the equivalent essentials are in
`docs/WORKFLOW.md` and `docs/HANDOFF.md`.

## Current state

The pipeline is built and runs clean end to end (9 stages via `scripts\run_all.ps1`,
exit 0). `git log` is the reliable history. One caveat, verified 2026-10-18: the repo
carries **no ruff config**, so `ruff check` under 0.16 defaults reports pre-existing style
findings (import order, `dict()` literals) in scripts this work did not touch — the stages
themselves are green. Adding a config that states the intended rule set is an open tidy-up.

| Stage | Script | Output |
|---|---|---|
| 0 | `00_validate_reference.py` | asserts 37/37 on both reference tables; capitals inside their own polygons |
| 0 | `00_build_capitals.py` | rebuilds capitals from the GeoNames gazetteer (not from memory) |
| 1 | `01_acquire_mpi.py` | OPHI + UNDP; **reconciles the two publications on MPI and aborts above 1e-3** |
| 2 | `02_acquire_conflict.py` | UCDP GED attributed to 37 states, method recorded per event |
| 3 | `03_acquire_climate.py` | Open-Meteo daily 1990-2024 for 37 capitals, QC'd on contributing-day count |
| 4 | `04_merge.py` | the three processed tables + `mpi_polygons.csv` (simplified ADM1 ring vertices for the map, area-checked) + `docs/normalisation.md`, `docs/data_quality.md` |
| 5 | `05_preview.py` | the workbook's visuals as PNGs - the pre-Tableau QA gate (9 now, one per published view: the two maps, the composition bar, the time panel, the three reference tabs, the KPI board and the pairs board) |
| 6 | `06_build_twb.py` | `tableau/Nigeria-MPI-Equity-Atlas.twbx` — **nine views and six Hyper extracts** (`mpi_polygons.hyper`, `spatial_polygons.hyper`, `mpi_trends_panel.hyper`, `pairs_board.hyper`, `dimension_shares.hyper`, `kpi_dots.hyper`); `Where poverty sits` and `Where poverty clusters` are **real filled choropleths** (Polygon mark + Path) with **thick white state strokes**, the first banded on the five-step red ramp; `A state over time` is the Measure-Names small-multiple panel (one pane per monitored measure × four rounds, Bauchi default, six-measure whitelist, interactive cards on the **left** rail — right-edge cards do not draw in packets this script builds, FIX_LEDGER §H); the 2026-10-21 amendment (FIX_LEDGER §H2) makes it a **rank** panel: the marks draw each state's rank of 37 on those measures (1 = highest, bare-integer labels via the field's `default-format` number format, direction key in the captions and subtitle), and no other variables are in the extract — the hover annotations are pre-formatted string dimensions; the field number format goes on the `<column>` (`default-format`, since a sheet-level `attr='number-format'` rule is rejected by the 2026.2 schema, D2E8DA72) and an integer measure must stay `type='quantitative'` to keep its Measure-Names domain key; `How poverty is made up` (tab 3, 2026-10-22, `docs/SHEET_DIMENSIONS.md`) stacks the three dimension shares per state — its segment numbers are **bold white** via a pane-level `<style-rule element='datalabel'>` (`color-mode='user'`, FIX_LEDGER D-051; the five failed shapes are recorded there), defaults to **17 of 37 bars** (5 poorest + first 12 of the Other 25, all 37 on a left-rail `state` checklist card, D-052) and Rows nest `poverty_group` above `state` so the two blocks read with a pane divider (D-053); `How measures pair` is the pairs board, parameter-driven, looking only (`docs/SHEET_PAIRS.md`): circles filled **one green** via a pane-level `<format attr='mark-color'>` (no colour pill, no colour legend), hover = **the state name only** (D-054; the five dead colour shapes and the load-required empty `<style />` finding are recorded there); `What the words mean` / `The list of basic needs` / `How we did it` are one reference table shipped as three text-zone tabs; `Where Nigeria stands` (tab 8, 2026-10-23, `docs/SHEET_KPI.md`) is the KPI board from stage 7's `kpi_dots.hyper` — one mark per reference point, and the same day's user pass turned the marks into **map silhouettes**: a green Nigeria map (drawn from the atlas's own ADM1 rings), a blue map of Africa and a purple globe itself (Natural Earth 110m; its white longitude lines and coastlines ride on reduced alpha because the colour-card tint keys the mark to the PNG's alpha, FIX_LEDGER §K3), images **embedded in the twb inside `<external><shapes>`** with the grammar copied byte-precise from the CH24 churn twb (`type='shape'`, `map to='KPI_Geo/file.png'`; no Shapes-repository copy is a runtime dependency), pane size factor 4.0 with one-decimal pre-formatted labels (`pos_label` on the Label pill — the twb number-format lanes are inert for labels here, §K2) at 7 pt and `mark-labels-cull` for the near-coincident pair; axis tick rule `major-spacing='0.5'` present but screen-unverified; colour = `series` via the ds-level palette + a right-edge colour card (the composition sheet's shape; the pairs-datasource palette failure is why the three-colour load is a packet check), rows in the benchmarks CSV order via a manual sort dictionary with the marks ordered so Nigeria draws last/on top, hover = one pre-formatted string dimension (values at one decimal) + the static direction key, `pos` row-normalised (layout, not data) and the position axis visible again (the axis-off rule removed in the 2026-10-23 pass); the pairs board moved to tab 9. Full workbook opens with no error dialog (2026-10-23, after the autosave purge, FIX_LEDGER §K1 — open via the file-association route, never a direct argument); the two newest tabs are render-verified in-app, publish-time interaction checks pending |
| 8 | `08_party_alignment.py` | pre-registered federal-alignment test (`docs/party_alignment.md`): `party_alignment_{panel,state,result}.csv`, fills §4. Runs after 04; 05 reads its outputs |
| 9 | `09_spatial_diagnostics.py` | pre-registered spatial diagnostic (`docs/spatial_analysis.md`, freeze in `docs/spatial_preregistration.md`): shells to `scripts/spatial_diagnostics.R` (sf/spdep/spatialreg), verifies Moran's I, the lag and the neighbourhood types independently in Python, writes `spatial_global.csv` + `spatial_diagnostics.csv` + `spatial_polygons.csv` (the map's rings joined to the types, for the cluster map), fills §3. Runs after 08; 05–06 read its outputs |

Stage 4 also writes `poverty_group` (Poorest 12 vs Other 25) into
`mpi_atlas_2021.csv`; `data/reference/state_dominant_party.csv` +
`docs/dominant_party.md` carry the mode governorship party 1999–2021 per state
(6 ties, FCT none, full event matrix + sources). The mode label is hover context
only; whether party is associated with poverty is the stage 8 test (see Findings).
`data/reference/governorship_events.csv` (every seating, sourced `seated_year`) and
`governor_defections.csv` (sourced sitting-party changes) feed it; stage 0 asserts
the events recompute `dom_party` exactly. Never colour by party. Cover framing decision (D6: "one country, two realities", never "two
zones") is recorded in `docs/SESSION_HANDOFF.md` 2026-10-08.

Stage 4 also builds the hover's governorship line (`gov_party`, e.g. `PDP (14 of 22
years)`; ties `PDP/APC (tied)`; FCT `no elected governor (minister-appointed)`) and the
`mpi_pct` / `mpi_ci_lo_pct` / `mpi_ci_hi_pct` columns the tooltip prints. Party is hover
context only, never the fill. `poverty_group` stays a bare label in the extract, so the
tooltip's first line carries the static suffix that completes it — `Bauchi · Poorest 12
of the 37 states, by MPI`.

**Remaining manual step:** publishing, and it needs your account login. Tableau Public
2026.2 **is installed** at `C:\Program Files\Tableau\Tableau Public 2026.2\bin\tabpublic.exe`
(the old `C:\TableauPublic` 2025.1 path no longer exists) — nothing to install. The
open-and-render check it unblocked has been done: the workbook loads with no error
dialog and draws. There is no write API or publishing CLI for Tableau Public. Follow
`docs/PUBLISH.md`, then verify the live URL with the MCP server's
`get_workbook_image`.

**The route is decided and written up: \docs/FINAL_PATH.md\** -- read that first.
It records the five decisions (D1 harmonised series, D2 climate layer, D3 conflict
layer, D4 no causal claim, D5 orderings withdrawn), what the Tableau render test
found, and what is deliberately left to the GUI.

**The next build phase is pre-documented: \docs/POLISH_PLAN.md\** (2026-10-22)
-- the cover tab ("One Country. Two Realities.", illustration, cover-only
faint green-white-green Nigeria watermark), **Nigerian-themed colour system**
(flag green #008751 for chrome; data encodings reviewed per surface,
severity ramps stay orderable), the sheet-by-sheet polish pass (each tab's
four axes before the next tab, next session, publishing only after the whole
pass), their guardlist and unknowns; wave 0 proves the dashboard grammar
before any of it touches the shipped twb.

**Latest sheet (built 2026-10-20, pending publish-time interaction checks):**
\docs/SHEET_TIME_PANEL.md\ — "A state over time", the Measure-Names small-multiple
panel view. Built to the freeze; the grammar findings and the two remaining manual
checks (hover annotations, checklist ticking) are recorded there and in
`docs/PUBLISH.md`. Changes against the freeze are in the doc's "Built" section,
not silently absorbed.

**Session docs.** \docs/SESSION_HANDOFF.md\ (current state, next steps),
\docs/CAUSAL_DECISION.md\, \docs/CLAIMS.md\, \docs/FIX_LEDGER.md\ (§H = the time
panel's render findings),
\docs/SHEET_TIME_PANEL.md\ (the time panel's design freeze + build record).

**Before publishing, read `docs/CLAIMS.md`, `docs/FIX_LEDGER.md` and
`docs/CAUSAL_DECISION.md`.** They supersede the earlier assumption that the open
items were cosmetic. They are not: the atlas currently makes three claims it cannot
support, and OPHI's standard errors — published in a file the pipeline already
downloads — show that **all 36 adjacent state rank pairs overlap at 95%**. So
"Bauchi has the highest MPI" is not available, and neither is a causal claim.

**The workbook is six views, as of 2026-10-20** — the two maps, the time panel and the
three reference tabs (`docs/FIX_LEDGER.md` W1, §H). Where the old defect list stands:

- The map was never a map (it drew 74 bar charts) and is now a real filled choropleth
  called `Where poverty sits` — drawn with a Polygon mark + Path field from
  `mpi_polygons.csv`, because Tableau's generated geographic fields cannot be
  hand-authored at all (error `9CA7205B`, or a hard load failure). Its state outlines are
  strokes, not borders: `has-stroke` / `stroke-color` / `stroke-size` on the
  worksheet-level mark style rule. `border-color` / `border-width` look right and
  validate, but are **inert** on a mark (rendered pixel-identically with and without).
- The five bands carry assigned colours rather than Tableau's categorical default, and the
  ramp is red — `#ffe5e5` under 5% to `#d80000` 30% and above, deepest = poorest. The QA
  gate draws the same bands from the same list, so the two cannot disagree.
- `Poverty over time`'s unsupportable trend, `Dimension breakdown`'s three panes instead of
  a stacked bar and the two scatter defects are **moot rather than fixed** — those sheets
  are withdrawn, and every sentence a reader needed from them is a row of the reference
  table. The `contrib_*_pct` percent-formatting item was never a bug: those columns already
  sum to 100.
- Still open, and documented step by step in `docs/PUBLISH.md`: the **colour legend does
  not draw** on `Where poverty sits` even though its right-edge card is declared exactly as
  a working Public workbook declares it (window cards *are* honoured — removing the Marks
  card from the same block removes it from the UI; `<simple-id>` and the reference's
  manifest are rejected by this schema, `D2E8DA72`; the `rows` strip and the mark class are
  ruled out). The one click is Analysis → Legends → Colour Legend, then Save. The cluster
  map's colour card **does** draw from the same declaration, so re-check sheet 1 before
  treating that as settled. Axis headers off and `Fit → Entire View` on both maps, and alt
  text per view, are also GUI clicks.

## Corrections to the original spec

The spec was written before the sources were checked. These are settled now:

1. **Use `data.humdata.org`, not `data.hdx.humdata.org`.** The canonical HDX host
   does not resolve on this network; the legacy host serves the identical CKAN API.
2. **No NBS registration is needed.** OPHI and UNDP publish the state-level MPI
   directly, with the dimension breakdown the NBS route would have needed.
3. **ACLED is unobtainable.** `api.acleddata.com` fails name resolution, and HDX
   carries only ACLED's country-year/month aggregates, which cannot support a
   per-state index. **UCDP GED replaces it** (open, per-event geocoding, 1990-2024).
   Conflict magnitudes are therefore not comparable to an ACLED-based figure.
4. **The Google Sheets intermediary is unnecessary.** The workbook ships a packaged
   Hyper extract; there is no live connection to break, and the survey updates
   annually, so a 24-hour refresh would buy nothing.
5. **The radar chart is not generated, and is withdrawn.** Its `Angle`/`Wedge Size` polar
   encodings were never verified from XML; the Polygon-mark half is no longer the blocker
   (`Where poverty sits` is a Polygon mark with a Path field, generated from XML,
   2026-10-17). It went with the other spec sheets on 2026-10-18 (`docs/FIX_LEDGER.md`
   W1), so no radar is planned.
6. **The packaged data must be a Hyper extract, not a CSV.** Tableau Public refuses
   any workbook whose datasource is not an extract (`3C242D89`) and does *not* convert
   one on save — this project assumed it did, for its whole life. Stage 6 writes the
   `.hyper` files itself with `tableauhyperapi`.
7. **The choropleth is banded on the MPI value, not on MPI incidence (H).** The spec's
   visual table says *"State choropleth | Filled map | State → MPI incidence"*. What
   ships — and what shipped before the map was a real map — colours by the MPI value in
   five bands, with H carried in the tooltip. Three reasons, decided 2026-10-17:
   the MPI value is the atlas's headline metric, and `poverty_group` (Poorest 12),
   `mpi_rank` and the rank-persistence figures are all built on it, so colouring by H
   would key the fill to one measure and the hover's poverty group to another; the
   five-band cut is justified by OPHI's *published* standard errors for the MPI value
   (median CI width 0.075 against a median MPI of 0.092); and it is not a statistical
   choice either way, because **both** measures are equally unorderable — 0 of 36
   adjacent state pairs separate at 95% on H (median relative SE 14.3%) exactly as on
   the MPI value (15.1%). **Every surface draws the same chart**: sheet 1 colours
   `mpi_band` in the five colours of `atlas_text.MPI_BANDS`, and since 2026-10-18 the
   pre-Tableau QA gate (`docs/preview/1_where_poverty_sits.png`, stage 5) does too — it
   used to render a continuous `YlOrRd` ramp of H, a different measure from the one the
   map colours by, which meant the gate could not catch a sheet-1 regression.
   Stage 6 writes those five colours into the workbook's own palette block, because a
   nominal field on Colour otherwise draws in Tableau's default categorical palette —
   five unrelated hues on a scale whose meaning is its order. The grammar is not
   guessable and lives in `06_build_twb.py` (`palette_block`); `docs/PUBLISH.md` carries
   it.

   Both the bands and the hover print that MPI value as a **percentage of the index**,
   not as a decimal: bands `1. under 5%` … `5. 30% and above` (the `N. ` prefix is a sort
   key — the colour legend sorts alphabetically) and, for Bauchi, `MPI 44.10% (95%
   interval 37.90% to 50.50%)`. The headcount is printed separately in the same hover as
   `Of the population, 75.36% are multidimensionally poor`, so the two percentages must
   never be swapped: the first is the MPI value, the second is H. (Percent fields render at
   Tableau's default two decimals; `44.10%` is the same number as the data's `44.1`.)

   The legend expands the acronym: the Tableau colour card's title **is** the colour
   field's caption, so `mpi_band` is captioned
   `MPI band (Multidimensional Poverty Index)` rather than the internal column name. A
   caption is plain text — the expanded form of the full meaning lives in the tooltip's
   MPI line and in the QA-gate PNG's colour-bar title and subtitle, all sourced from
   `MPI_LEGEND_*` in `scripts/atlas_text.py`.

## Findings that constrain what may be claimed

- **No conflict-poverty association is *detectable*, and the design cannot detect one.**
  Spearman rho is +0.34 (2013), -0.20 (2016), +0.10 (2018), -0.06 (2021). Power at
  n=37 is 0.75 at rho=0.4 and nothing survives Bonferroni. Worse, the conflict variable
  *undercounts where poverty is highest*: in 2021 five of the poorest 12 states (Bauchi, Jigawa, Kebbi, Katsina, Kano)
  record zero UCDP events (10 of 37 states do). Never report this as a negative result about the world.
- **Climate is a north-south gradient, not a driver.** Baseline 1991-2020
  precipitation correlates with MPI at rho = -0.80, but precipitation <-> latitude is
  -0.903 and latitude <-> MPI is **+0.821 — better than precipitation <-> MPI at
  -0.801.** The predictor is the outcome's twin. Use OPHI's word: *overlap*.
- **The Conflict Exposure Index is cross-sectionally relative**, scaled within each
  survey year. Borno takes 100 in 2021 and the other 36 states cluster near zero.
  Anchors are in `data/processed/atlas_vintages.csv`.
- **Health rests on child mortality alone**, and is re-weighted to a full one-third.
  The UNDP "missing indicator" flag reads `Nutrition` for all 37 states — a
  country-wide exclusion, *not* a per-state gap, so within-Nigeria comparison holds.
  But Nigeria's Health dimension is structurally heavier than a country's with all
  ten indicators, so cross-country comparison is forbidden.
- **MPI rank persistence is 0.87-0.92** between consecutive survey rounds. Level fell;
  structure held.
- **The north-west/south-east dimension split is a poverty-level contrast, not a
  geographic one.** All 12 states with MPI > 0.20 sit in the two northern latitude
  bands, and among poor states latitude does *not* predict the dimension mix
  (r = -0.25). Say "poorest states vs the rest".
- **Federal party alignment: a fragile result, not a finding.** Pre-registered
  (`152c13d`, before any code): within-state ΔMPI per year 2013–21 on the share of
  years the governor shared the federal ruling party, n = 108 state-intervals (FCT
  has no governor). The pre-set rule (p < 0.05) fired: β = +0.008/yr, i.e. aligned
  states' MPI fell *slower*, permutation p = 0.036, but the 95% CI crosses 0 and
  |β| < MDE 0.0115. It rests on 2013–16 alone and fails the sitting-party
  (defection) check (p ≈ 0.08), relative change, binary exposure and dropping any
  interval; it holds only with poverty group × interval. **No sheet has drawn it since
  2026-10-18** (`docs/FIX_LEDGER.md` W1) — the result lives in
  `docs/party_alignment.md`, where the §3 sentence appears verbatim *with* the robustness
  context line beside it — never alone, never as "party affects poverty". The
  dominant-party (mode) label cannot test anything: 26 of 36 states are PDP.

## Environment rules that matter here

| Need | Use | Never |
|---|---|---|
| Python / data work | `& C:\Users\TOSHIBA\ds-general\python.exe` | bare `python` (= C:\Python314, tooling-only) |
| Install | `uv pip install --python C:\Users\TOSHIBA\ds-general\python.exe <pkg>` | `pip install` into the wrong interpreter |
| Stats / geo | `Rscript` | bare `R` (PowerShell alias for `Invoke-History`) |
| Tableau | `C:\Program Files\Tableau\Tableau Public 2026.2\bin\tabpublic.exe` (installed; `winget install --id Tableau.Public -e` to reinstall) | Tableau Desktop (paid; different app, cannot publish to Public) |
| Tableau (analysis) | `tableau` MCP server (Public API, read-only) | direct downloads from `tableau.com` — HTTP 403 here |
| Shell | one call, chained with `;` or `&&` | assuming state persists between calls |

- `D:\` is an **external USB SSD**. Everything here disappears if it's unplugged. Anything that must
  survive goes to `C:\Users\TOSHIBA`.
- 15.9 GB RAM, no GPU. The MPI dataset is ~37 rows — compute is never the constraint. Don't reach for
  Colab.
- No `jq`, no `fd`, no `magick`. Use `python -c` or `ConvertFrom-Json`.

## Credentials

- **ACLED requires an API key** (`developer.acleddata.com` + registered email). None is present in
  this environment. Ask the user for it; do not try to scrape around the API and do not commit it.
- Open-Meteo is keyless — use it freely.
- Read the key from the environment, never hardcode it in a script or a committed file.

## Intended layout

```
data/
  raw/        downloaded source files, unmodified, never edited in place
  interim/    merged/aggregated intermediates
  processed/  the single tidy table Tableau reads (one row per state)
scripts/      numbered, runnable end-to-end: 01_acquire_*.py, 02_transform_*.py ...
docs/         short notes; the spec lives at the root, not here
```

## Conventions

- **Python:** pandas or polars, snake_case, type hints, `pathlib` for paths, no notebooks as the
  source of truth (use `.py` + `.qmd`/Quarto for anything reported).
- **State names are the #1 failure mode.** MPI (NBS/HDX), ACLED, and Open-Meteo all spell the 37
  units differently. Build one explicit lookup table, join on it, and assert 37/37 coverage before
  merging. Never fuzzy-match silently.
- **Normalisation:** Conflict Exposure Index is 0–100 per the spec (per-100k population, min-max).
  Document the min/max endpoints in the output so the scale is reproducible.
- **FCT is a state here.** Keep it in every aggregate; it is the most-poverty-dense unit and dropping
  it is a classic silent bug.
- **No secrets, no absolute machine paths** in committed scripts — resolve paths relative to the repo
  root.
- **Cite the vintage.** Every output table carries the survey year and the download date; the MPI
  survey is 2021 and will silently disagree with newer figures. The four rounds we download are the
  *harmonised* series (OPHI Data Table 6, MN 63) — verified numerically against Table 6.4 to 4dp on
  all 148 admin-1 rows, despite the HDX resource description saying "standardised". Comparability
  across rounds therefore holds. The flip side: **earlier publications of Nigerian state MPI for
  2013–2018 used un-harmonised estimates and differ by up to 0.17**, so never compare our figures
  with an older OPHI release.
- **No causal language.** The atlas makes a **decomposition** claim, not a causal one. Every causal
  path is closed at n=37; read `docs/CAUSAL_DECISION.md` before writing a caption. Two specifics:
  say "poorest states vs the rest", never "north vs south" (all 12 states with MPI > 0.20 are in the
  two northern bands, so the two are the same observations), and never "not associated" as a claim
  about the world (the design's power floor is |rho| ~ 0.4, and the conflict variable undercounts
  where poverty is highest).
- **Orderings are not resolvable.** OPHI publishes standard errors (`subnational-results-mpi.xlsx`,
  sheet `5.4 SE & CI Region`, extracted to `data/interim/mpi_se_ci.csv`); median relative SE is 15%
  and **all 36 adjacent rank pairs overlap at 95%**. Present bands, never a single "highest" state.

## Build order

Already implemented as numbered scripts. `scripts\run_all.ps1` is the canonical order
(9 stages); to run them by hand:

```powershell
foreach ($s in '00_validate_reference','01_acquire_mpi','02_acquire_conflict',
               '03_acquire_climate','04_merge','08_party_alignment',
               '09_spatial_diagnostics','05_preview','06_build_twb') {
  & C:\Users\TOSHIBA\ds-general\python.exe "scripts\$s.py"
}
```

`data/raw/` is gitignored and re-downloadable, so a clean checkout re-fetches
everything. The Open-Meteo cache is keyed by pcode and resumes after a rate limit.

## Verify before claiming done

- Row count is 37 and every state name resolves.
- `scripts/06_build_twb.py` exits 0 **and** the package contains `.hyper` files, not
  CSV. Its extract gate reads the schema back out of the files Tableau will open.
- The workbook opens in Tableau Public with no error dialog. Check the window title
  reads `Nigeria-MPI-Equity-Atlas`; a failed load shows `Book1`. When in doubt read
  `%USERPROFILE%\Documents\My Tableau Repository\Logs\log.txt` — it names the exact
  failing field. Schema-valid XML is **not** sufficient; six defects got past it.
- The published Tableau Public viz loads — fetch its image via the `tableau` MCP
  server rather than trusting the upload dialog.
- Conflict and climate layers are not silently empty (a join that matches 0 rows looks
  like a valid chart with no data).