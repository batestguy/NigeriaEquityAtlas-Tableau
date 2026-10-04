# Workflow

How this project is built, how to run it, and how to extend it without breaking the
guarantees the current stages enforce.

## Design

Seven numbered stages, each independently runnable, each writing a readable artefact
that the next one consumes. Every stage **fails loudly rather than degrading quietly**
— that is the single most important property of the pipeline, because every real error
found during this build was a *silent* one.

```
 00  reference layer  ──► state_lookup.csv, state_capitals.csv   (hand-curated, committed)
 01  poverty         ──► mpi_dimensions, mpi_headline, mpi_trends
 02  conflict        ──► conflict_state_year, conflict_events_attributed
 03  climate         ──► climate_state_year, climate_baseline_1991_2020
 04  merge           ──► mpi_atlas_2021, mpi_trends_panel, atlas_vintages + docs
 05  preview         ──► docs/preview/*.png                     (visual QA gate)
 06  workbook        ──► tableau/Nigeria-MPI-Equity-Atlas.twbx
```

Run everything with `.\scripts\run_all.ps1`.

## The rule that shapes everything: one canonical key

Every state is identified by its **ISO 3166-2:NG code** (`NG-AB`, `NG-FC`, …) and
every join in the project goes through `data/reference/state_lookup.csv`.

That file exists because the five sources spell the same 37 units five different ways.
`FCT` alone is called `FCT` (OPHI, UNDP), `Abuja Federal Capital Territory`
(geoBoundaries) and `Federal Capital territory` (UCDP) — and its OPHI PCode is blank in
all four survey rounds, making it the row most likely to silently vanish from a join.

**When a new source disagrees about a state name, add the spelling to
`state_lookup.csv`. Do not normalise it in code.** Normalisation logic scattered across
stages is how state attribution quietly rots.

## Stage contracts

Each stage asserts on its own output. If an assertion trips, the pipeline stops — do
not loosen an assertion to make a run pass. Fix the cause or record the reason.

| Stage | Asserts |
|---|---|
| `00_validate_reference` | 37 unique pcodes; both tables agree; every capital falls inside its own ADM1 polygon |
| `01_acquire_mpi` | 37 admin-1 rows; 148 trend rows; OPHI and UNDP agree on MPI within 1e-3; dimensions sum to 100; UNDP workbook layout unchanged |
| `02_acquire_conflict` | every event attributed (0 unattributed); all 37 states present in every year |
| `03_acquire_climate` | 37 capitals × 35 years; no nulls; every state-year has ≥300 contributing days |
| `04_merge` | 37 atlas rows, 148 panel rows, zero empty cells, all layer keys present for all 37 × 4 |
| `05_preview` | 37 and 148 rows |
| `06_build_twb` | XML parses; every field reference resolves to a declared column; declared column ordinals match the packaged CSV headers |

Two of those deserve comment because they guard against failures Tableau cannot report:

- **`01` reconciles OPHI against the UNDP workbook.** They are independent publications
  of the same survey. If they disagree, one has been revised and every downstream number
  is ambiguous about which vintage it is. This aborts rather than picking one.
- **`06` checks column ordinals against the CSV headers.** A mismatch attaches the
  wrong field to every visual and Tableau raises no error at all.

## Why previews exist

`05_preview.py` renders the five spec visuals in matplotlib *before* Tableau is
involved. If a stacked bar looks wrong or a scatter shows an implausible relationship,
the bug is in Python where it is cheap to fix and obvious to see — not buried in
hand-authored XML where nobody would notice. Treat these PNGs as the design contract
for the Tableau sheets.

The previews also caught a genuine analytical error: the spec asked for a
temperature-anomaly chart, and rendering it made the sign-flipping correlation
impossible to miss.

## Adding a source

1. Put the download in `scripts/`, using `common.download()` so the URL, SHA-256 and
   fetch date land in `data/raw/_provenance.csv` automatically.
2. Add a `DOWNLOAD`-style constant near the top with the URL in a named constant.
3. Map any state naming through `state_lookup.csv` before aggregating.
4. Write a long-format interim table keyed on `pcode`.
5. Assert 37/37 coverage before merging.
6. Merge in `04_merge.py` and add the new columns to `atlas_fields`.

## Reproducibility

- `data/raw/` is gitignored and re-downloadable; `data/interim/` and
  `data/processed/` are committed so results are inspectable without network access.
- `data/raw/_provenance.csv` records the URL, SHA-256, byte count and fetch date of
  every source, and is updated on every run (re-running against a cached download does
  not falsify the record — the date comes from the file's mtime).
- Network calls are cached on disk so a re-run does not re-hit an API. The Open-Meteo
  cache is keyed by state code and resumes after a rate limit rather than restarting.
- Python dependencies are pinned in `requirements.txt`.

## Adding a chart to the workbook

1. Add the worksheet in `06_build_twb.py`, declaring its mark class and encodings.
2. Every column it references must exist in the CSV, otherwise the build fails.
3. Re-run `06_build_twb.py`, then unpack the result and inspect the structure.
4. Check the corresponding preview in `docs/preview/` shows the same thing.

**Keep it simple.** Every extra field reference is another chance to ship a sheet that
opens with an error dialog, and there is no way to render-test a hand-authored workbook
in this environment — see `docs/HANDOFF.md` for exactly what is and is not verified.

## Adding data-quality context to a claim

If a number changes, `docs/normalisation.md` and `docs/data_quality.md` are regenerated
by `04_merge.py` and must be updated in the same commit. Those two files are what stop
a later reader from over-claiming from a chart.