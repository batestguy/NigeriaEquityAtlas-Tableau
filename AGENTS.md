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

Nothing is built. The repo contains only the two files above — no git repo, no data, no scripts.
Start from step 1.2 of the spec (data acquisition).

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

Follow the spec's pipeline; each stage should leave a readable artefact in `data/`.

1. MPI state table (HDX direct CSV first — no NBS registration needed; NBS only if HDX lacks a field).
2. ACLED → events + fatalities per state-year. Long format, not wide.
3. Open-Meteo → annual mean temp + total precip per state capital, then join on coordinates.
4. Merge → one tidy state-level table. Assert 37 rows, zero nulls in MPI dimensions.
5. Load into Google Sheets (the only live-refresh intermediary Tableau Public supports).
6. Build the five visuals from the spec's §1.4 table.
7. Publish, then verify the live URL actually renders.

## Verify before claiming done

- Row count is 37 and every state name resolves.
- The published Tableau Public viz loads — screenshot the live URL, don't trust the upload dialog.
- Conflict and climate layers are not silently empty (a join that matches 0 rows looks like a valid
  chart with no data).