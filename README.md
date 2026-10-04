# Nigeria Equity Atlas (Tableau)

An interactive atlas of Nigeria's **Multidimensional Poverty Index (MPI)** at state
level — 36 states plus the Federal Capital Territory — disaggregated into its three
dimensions (health, education, living standards), with UCDP conflict and Open-Meteo
climate layers, plus a four-round poverty trend panel.

The deliverable is a Tableau Public viz. The pipeline that builds it is a set of
numbered, independently runnable Python scripts.

```
MICS 2021 baseline · 37 admin-1 units · poverty + conflict + climate + 4 survey rounds
```

## Quick start

```powershell
# from the repository root
.\scripts\run_all.ps1
```

Or stage by stage:

```powershell
foreach ($s in '00_validate_reference','01_acquire_mpi','02_acquire_conflict',
               '03_acquire_climate','04_merge','05_preview','06_build_twb') {
  & C:\Users\TOSHIBA\ds-general\python.exe "scripts\$s.py"
}
```

Requires Python 3.12 with `scipy`, `matplotlib`, `openpyxl` and `shapely`:

```powershell
uv pip install --python C:\Users\TOSHIBA\ds-general\python.exe -r requirements.txt
```

`data/raw/` is gitignored and fully re-downloadable, so a clean checkout re-fetches
every source. Nothing in the pipeline needs a registration, an API key, or a login.

## Outputs

| Path | What it is |
|---|---|
| `tableau/Nigeria-MPI-Equity-Atlas.twbx` | the workbook to publish, with data packaged inside |
| `data/processed/mpi_atlas_2021.csv` | 37 rows, one per state, the 2021 baseline |
| `data/processed/mpi_trends_panel.csv` | 148 rows, 37 states × 4 survey rounds |
| `data/processed/atlas_vintages.csv` | per-round scale anchors and summary statistics |
| `docs/preview/*.png` | the five spec visuals, rendered as a QA gate |
| `docs/normalisation.md` | exactly how every derived index is defined and scaled |
| `docs/data_quality.md` | the caveats a published claim has to carry |

## Documentation

- **[docs/WORKFLOW.md](docs/WORKFLOW.md)** — how the pipeline fits together, how to
  extend it, and the conventions each stage follows.
- **[docs/HANDOFF.md](docs/HANDOFF.md)** — state of the project, decisions taken,
  what is verified versus assumed, and the traps already paid for. **Read this first
  when picking this up cold.**
- **[docs/PUBLISH.md](docs/PUBLISH.md)** — the one manual step: publishing to Tableau
  Public, plus the two chart fragments deliberately left to the GUI.
- **[docs/normalisation.md](docs/normalisation.md)** / **[docs/data_quality.md](docs/data_quality.md)**
  — metric definitions and caveats. Both are required reading before quoting a number.

## Three things worth knowing before using this

1. **Conflict does not predict poverty in these data.** Spearman rho ranges from
   +0.34 to −0.20 across the four survey rounds. It is reported as a negative result;
   no single round should be quoted as the finding.
2. **Climate is shown as a 1991–2020 baseline, not a single year's anomaly.** The
   anomaly correlation flips sign between rounds (+0.81 in 2013, −0.43 in 2021), so
   it measures weather. Baseline precipitation holds at rho = −0.80 (p < 0.001).
3. **Conflict data is UCDP, not ACLED.** ACLED was unobtainable in this environment.
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