# AGENTS.md — Nigeria MPI Equity Atlas

## What this is

Greenfield project: an interactive **Tableau Public** atlas of Nigeria's Multidimensional Poverty
Index (MPI) at state level (36 states + FCT = 37 rows), disaggregated into the three MPI dimensions
(health, education, living standards), with conflict (ACLED) and climate (Open-Meteo) overlay layers.

The authoritative spec is **`TableauNigeria MPI Equity Atlas.txt`** — read it before planning. It
defines the five visuals, the transformation steps, the deployment workflow, and the free-tier
constraints. Don't restate it here; follow it.

**Machine map:** `ENVIRONMENTS.md` at the project root. Read §2 (TRAPS), §3 (Python), §10 (command
cookbook) before running anything. It is verified-by-execution and takes precedence over recollection.

## Current state

The pipeline is built and runs clean end to end (7 stages, exit 0, ruff clean).
Four commits, one per stage. `git log` is the reliable history.

| Stage | Script | Output |
|---|---|---|
| 0 | `00_validate_reference.py` | asserts 37/37 on both reference tables; capitals inside their own polygons |
| 0 | `00_build_capitals.py` | rebuilds capitals from the GeoNames gazetteer (not from memory) |
| 1 | `01_acquire_mpi.py` | OPHI + UNDP; **reconciles the two publications on MPI and aborts above 1e-3** |
| 2 | `02_acquire_conflict.py` | UCDP GED attributed to 37 states, method recorded per event |
| 3 | `03_acquire_climate.py` | Open-Meteo daily 1990-2024 for 37 capitals, QC'd on contributing-day count |
| 4 | `04_merge.py` | the three processed tables + `docs/normalisation.md`, `docs/data_quality.md` |
| 5 | `05_preview.py` | the five spec visuals as PNGs — the pre-Tableau QA gate |
| 6 | `06_build_twb.py` | `tableau/Nigeria-MPI-Equity-Atlas.twbx`, validated then packaged |

**Remaining manual step:** publishing. There is no write API or publishing CLI for
Tableau Public — it is a GUI action behind an account login. Follow `docs/PUBLISH.md`.

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
   CSV extract; there is no live connection to break, and the survey updates
   annually, so a 24-hour refresh would buy nothing.
5. **The radar chart is not generated.** A polygon mark driven by computed path
   fields is too fragile to hand-author blind; it is a documented GUI step.

## Findings that constrain what may be claimed

- **Conflict and poverty are not associated in these data.** Spearman rho is +0.34
  (2013), -0.20 (2016), +0.10 (2018), -0.06 (2021). Report it as a negative result;
  never quote a single round as the finding.
- **Climate must be shown as baseline, not anomaly.** A single year's anomaly
  correlates with MPI at +0.81 in 2013 and -0.43 in 2021 — it flips sign, so it is
  weather. Baseline 1991-2020 precipitation holds at rho = -0.80 (p < 0.001).
- **The Conflict Exposure Index is cross-sectionally relative**, scaled within each
  survey year. Borno takes 100 in 2021 and the other 36 states cluster near zero.
  Anchors are in `data/processed/atlas_vintages.csv`.
- **Health rests on child mortality alone.** The UNDP "missing indicator" flag reads
  `Nutrition` for all 37 states — a country-wide exclusion, *not* a per-state gap.
  (This corrects an earlier reading of it as a comparability break.)
- **MPI rank persistence is 0.87-0.92** between consecutive survey rounds.

## Environment rules that matter here

| Need | Use | Never |
|---|---|---|
| Python / data work | `& C:\Users\TOSHIBA\ds-general\python.exe` | bare `python` (= C:\Python314, tooling-only) |
| Install | `uv pip install --python C:\Users\TOSHIBA\ds-general\python.exe <pkg>` | `pip install` into the wrong interpreter |
| Stats / geo | `Rscript` | bare `R` (PowerShell alias for `Invoke-History`) |
| Tableau | `tableau` MCP server (Public API) | Tableau Desktop 2019.4 (too old to trust) |
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
  survey is 2021 and will silently disagree with newer figures.

## Build order

Already implemented as numbered scripts. To rebuild from scratch, run them in order:

```powershell
foreach ($s in '00_validate_reference','01_acquire_mpi','02_acquire_conflict',
               '03_acquire_climate','04_merge','05_preview','06_build_twb') {
  & C:\Users\TOSHIBA\ds-general\python.exe "scripts\$s.py"
}
```

`data/raw/` is gitignored and re-downloadable, so a clean checkout re-fetches
everything. The Open-Meteo cache is keyed by pcode and resumes after a rate limit.

## Verify before claiming done

- Row count is 37 and every state name resolves.
- The published Tableau Public viz loads — fetch its image via the `tableau` MCP
  server rather than trusting the upload dialog.
- Conflict and climate layers are not silently empty (a join that matches 0 rows looks
  like a valid chart with no data).