# Nigeria Equity Atlas (Tableau)

An interactive atlas of Nigeria's **Multidimensional Poverty Index (MPI)** at state
level — 36 states plus the Federal Capital Territory — disaggregated into its three
dimensions (health, education, living standards), with four survey rounds
(2013–2021). UCDP conflict and Open-Meteo climate figures are carried as measures on
the time panel and the pairs board, not as map layers.

The deliverable is a Tableau Public viz: a cover page, two dashboards (**Overview**
and **A state, in context**) and three reference tabs. The pipeline that builds it is a
set of numbered, independently runnable Python scripts (plus one R script).

```
MICS 2021 baseline · 37 admin-1 units · poverty + conflict + climate + 4 survey rounds
```

## See it live

**[Open the atlas on Tableau Public →](https://public.tableau.com/app/profile/jerry.bannister/viz/Nigeria-MPI-Equity-Atlas)**

[![Demo video: every click and filter in the atlas](docs/demo/01_cover.jpg)](docs/demo/atlas_demo.mp4)

▶ **[Watch the 2:41 demo](docs/demo/atlas_demo.mp4)**: every click, hover and filter,
recorded on the live viz. Music: *Motherland* by Sound Sultan.

### What you can click

| Where | Control | What it does |
|---|---|---|
| **Start here** (cover) | **1 Overview →** / **2 A state, in context →** | open the two dashboards |
| **Overview** | **State** drop-down | filters all three panes to one state; `(All states)` restores the default |
| | hover a state on the poverty map | MPI with its 95% interval, the headcount, average deprivation, number of poor people |
| | hover a state on the cluster map | its neighbourhood type, and its poverty beside its neighbours' average |
| | click a state, or a legend entry | highlights it; click again to clear |
| | hover a bar segment | that state's share of poverty from health, education or living standards |
| **A state, in context** | **Panel state** drop-down | the state shown on the time panel (rank of 37, six measures, four rounds) |
| | **X axis / Y axis** drop-downs | any two of 24 measures on the pairs board, one quadratic fit and 95% band per pane |
| | hover a point | names the state; on the benchmarks band, the values and the direction key |

The three reference tabs (what the words mean, the list of basic needs, how it was
made) are published too:
[words](https://public.tableau.com/views/Nigeria-MPI-Equity-Atlas/Whatthewordsmean) ·
[needs](https://public.tableau.com/views/Nigeria-MPI-Equity-Atlas/Thelistofbasicneeds) ·
[method](https://public.tableau.com/views/Nigeria-MPI-Equity-Atlas/Howwedidit).

| | |
|---|---|
| ![Overview, hover](docs/demo/03_overview_hover.jpg) | ![Overview filtered to Kano](docs/demo/04_overview_kano.jpg) |
| *Overview: hover a state* | *Overview: the State control set to Kano* |
| ![A state, in context](docs/demo/05_context.jpg) | ![National benchmarks](docs/demo/07_context_benchmarks.jpg) |
| *A state, in context: time panel and pairs board* | *Where Nigeria stands: national benchmarks* |

## Quick start

Requirements:

- **Python 3.12** with the packages in `requirements.txt` (`scipy`, `numpy`,
  `matplotlib`, `openpyxl`, `shapely`, `tableauhyperapi`):
  `uv pip install --python <your-python> -r requirements.txt`
- **R** on `PATH` (`Rscript`) with `sf`, `spdep` and `spatialreg`, for stage 09.
- `scripts/run_all.ps1` names its interpreter in `$Python` at the top. Point it at
  yours before the first run.

```powershell
# from the repository root: all 10 stages, stops at the first failure
.\scripts\run_all.ps1
.\scripts\run_all.ps1 -SkipPreviews   # skip stage 05 when iterating on the workbook
```

Or stage by stage, in the order `run_all.ps1` uses (07–09 must run before 05 and 06,
which read their outputs):

```powershell
foreach ($s in '00_validate_reference','01_acquire_mpi','02_acquire_conflict',
               '03_acquire_climate','04_merge','07_kpi_reference','08_party_alignment',
               '09_spatial_diagnostics','05_preview','06_build_twb') {
  & <your-python> "scripts\$s.py"
}
```

There is no test suite: each stage asserts on its own output (37/37 state coverage,
the OPHI-vs-UNDP MPI reconciliation, the extract schema read back from the `.hyper`
files), and a failing assertion stops the run.

`data/raw/` is gitignored and fully re-downloadable, so a clean checkout re-fetches
every source. The pipeline needs no registration, API key or login; only publishing
to Tableau Public needs an account.

## Outputs

| Path | What it is |
|---|---|
| `tableau/Nigeria-MPI-Equity-Atlas.twbx` | the workbook to publish, with six Hyper extracts and the cover image packaged inside |
| `data/processed/mpi_atlas_2021.csv` | 37 rows, one per state, the 2021 baseline |
| `data/processed/mpi_trends_panel.csv` | 148 rows, 37 states × 4 survey rounds |
| `data/processed/mpi_pairs_148.csv` | the pairs board's measures, per state-round |
| `data/processed/mpi_polygons.csv` | simplified state outlines for the maps |
| `data/processed/kpi_dots.csv` | the national benchmarks (Nigeria, sub-Saharan Africa, world) |
| `data/processed/spatial_*.csv` | the pre-registered spatial diagnostic and the cluster map |
| `data/processed/party_alignment_*.csv` | the pre-registered federal-alignment test |
| `data/processed/atlas_vintages.csv` | per-round scale anchors and summary statistics |
| `docs/preview/*.png` | the nine published views, rendered as a pre-Tableau QA gate |
| `docs/normalisation.md` | exactly how every derived index is defined and scaled |
| `docs/data_quality.md` | the caveats a published claim has to carry |

## Documentation

- **[docs/WORKFLOW.md](docs/WORKFLOW.md)** — how the pipeline fits together, how to
  extend it, and the conventions each stage follows.
- **[AGENTS.md](AGENTS.md)** — the authoritative project brief: current state,
  settled corrections to the spec, and the findings that limit what may be claimed.
  **Read this first when picking this up cold**, then
  [docs/SESSION_HANDOFF.md](docs/SESSION_HANDOFF.md) for the latest session and
  [docs/FINAL_PATH.md](docs/FINAL_PATH.md) for the decisions behind the design.
- **[docs/CLAIMS.md](docs/CLAIMS.md)** / **[docs/CAUSAL_DECISION.md](docs/CAUSAL_DECISION.md)**
  — which sentences the data supports, which it does not, and why there is no causal
  claim. Read before writing any caption or quoting a result.
- **[docs/FIX_LEDGER.md](docs/FIX_LEDGER.md)** — every Tableau XML finding and dead end,
  so they are not paid for twice. (`docs/HANDOFF.md` is a historical record.)
- **[docs/PUBLISH.md](docs/PUBLISH.md)** — republishing to Tableau Public after a
  rebuild (File → Save to Tableau Public, same name), and the checks to run on the
  live viz.
- **[docs/normalisation.md](docs/normalisation.md)** / **[docs/data_quality.md](docs/data_quality.md)**
  — metric definitions and caveats. Both are required reading before quoting a number.

## What the data can and cannot support

1. **States cannot be ranked.** OPHI publishes standard errors; the median relative
   SE is 15%, and all 36 pairs of states adjacent in the ranking overlap at 95%. The
   atlas shows bands, never a single "highest" state, and compares the poorest 12
   states with the other 25. Say "poorest states vs the rest", never "north vs south".
2. **No causal claim.** The atlas decomposes poverty; it does not explain it. At
   n = 37 every causal route is closed (`docs/CAUSAL_DECISION.md`).
3. **Health rests on child mortality alone.** Nutrition is missing for all 37 states,
   so the health dimension is re-weighted. Comparisons within Nigeria hold;
   cross-country comparison is not supported.
4. **No conflict–poverty association is detectable, and this design could not
   detect a moderate one.** Spearman rho runs +0.34, −0.20, +0.10, −0.06 across the
   four survey rounds; at n = 37 the power is 0.75 at rho = 0.4. Say "no detectable
   association at |rho| ≲ 0.4", never "not associated". Also, the conflict variable
   undercounts where poverty is highest: five of the poorest 12 states record no UCDP
   event in 2021. Never quote a single round.
5. **Climate overlaps with poverty; it is not shown to drive it.** Baseline
   (1991–2020) precipitation correlates with MPI at rho = −0.80, but precipitation
   tracks latitude (−0.90), and latitude predicts MPI better (+0.82). That is consistent
   with a development gradient, not identified as a climate effect.
6. **Conflict data is UCDP, not ACLED.** ACLED was unobtainable in this environment.
   Event definitions differ, so magnitudes are not comparable to an ACLED figure.

## Sources and licences

| Layer | Source | Licence |
|---|---|---|
| Poverty | OPHI + UNDP Global MPI | CC0 / CC BY |
| Conflict | UCDP Georeferenced Event Dataset | CC BY-IGO |
| Climate | Open-Meteo Archive API | free, keyless |
| Boundaries | geoBoundaries ADM1 | CC BY 4.0 |
| Capitals | GeoNames `cities5000` | CC BY 4.0 |

Exact URLs, SHA-256 digests and fetch dates are recorded in `data/raw/_provenance.csv`
on every run.