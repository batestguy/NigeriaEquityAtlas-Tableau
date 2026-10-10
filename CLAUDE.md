# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

@AGENTS.md

AGENTS.md (imported above) is the authoritative project brief: current state, settled
corrections to the spec, the findings that limit what may be claimed, and the environment
rules. This file adds only what is specific to working on the code. Keep facts in one
place — update AGENTS.md, not this file, when the project state changes.

## Commands

Run everything from the repo root, in PowerShell, with the data-science interpreter.
Bare `python` is a different interpreter with none of the packages.

```powershell
# Full pipeline: 00, 01-04, 08, 05, 06, 07; stops at the first failing stage
.\scripts\run_all.ps1
.\scripts\run_all.ps1 -SkipPreviews      # skip stage 5 when iterating on the workbook

# One stage (none take arguments). Run from the repo root -- stage 7 fails from scripts/
& C:\Users\TOSHIBA\ds-general\python.exe scripts\04_merge.py

# Lint (no project ruff config; ruff is on PATH). Run from scripts\ -- from the root,
# ruff misclassifies the `from common import` lines (I001)
ruff check .

# Dependencies
uv pip install --python C:\Users\TOSHIBA\ds-general\python.exe -r requirements.txt
```

There is no test suite. Each stage's assertions on its own output *are* the tests
(37/37 coverage, the OPHI-vs-UNDP MPI reconciliation at 1e-3, the stage 6 extract gate
that reads the `.hyper` schema back). When a stage fails, fix the cause — never relax
the assertion to get past it.

## Architecture

- **Linear, file-handoff pipeline.** Stages communicate only through files:
  `data/raw/` (downloads, gitignored except `_provenance.csv`) → `data/interim/` →
  `data/processed/` → `tableau/*.twbx` and `docs/preview/`. Re-running a stage
  re-reads its inputs from disk, so you can rerun from any stage onward.
- **`scripts/common.py`** is the shared core: repo-relative paths (`REPO_ROOT`, `RAW`,
  `INTERIM`, `PROCESSED`, `REFERENCE`, `DOCS`), `N_STATES = 37`, `download()` (caches
  in `data/raw/` and appends SHA-256 + fetch date to `_provenance.csv`), the state
  lookup (`read_lookup`), capitals, ADM1 boundaries, `write_csv`, and `minmax`.
  Stages import it as `from common import ...`. New downloads must go through
  `download()` so provenance stays complete.
- **`data/reference/`** holds the hand-curated join keys (state lookup, capitals,
  dominant party). Every source is joined through the lookup — that is how the
  state-name problem is solved. Stage 0 validates these before anything else runs.
- **Stage 4 writes docs too.** `docs/normalisation.md` and `docs/data_quality.md` are
  generated; edit the generator in `04_merge.py`, not the markdown.
- **Stage 6 hand-authors the Tableau XML** and writes Hyper extracts with
  `tableauhyperapi`. Schema-valid XML has repeatedly not been enough — the real check is
  opening the `.twbx` in Tableau Public 2026.2 at
  `C:\Program Files\Tableau\Tableau Public 2026.2\bin\tabpublic.exe` — the
  `C:\TableauPublic` / 2025.1 path in older docs is stale (title must read
  `Nigeria-MPI-Equity-Atlas`, not `Book1`) and reading Tableau's `log.txt` on failure.
- Stage 6/7 build artefacts (`tableau/*.hyper`, `*.twbr`, `hyperd.log`) are gitignored.

## Before changing captions, docs, or chart text

Read `docs/CLAIMS.md`, `docs/CAUSAL_DECISION.md`, and `docs/FIX_LEDGER.md` first. Text
in older files can predate those decisions — for example, `README.md` still frames the
conflict result as a "negative result", which AGENTS.md now forbids.
