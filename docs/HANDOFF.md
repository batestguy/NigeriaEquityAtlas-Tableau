# Handoff

State of the project as of this session, for whoever picks it up next — a new agent, a
collaborator, or future me after context is lost.

**Read this before running anything.** It records what was decided, what was actually
verified, and which traps have already been paid for.

---

## 1. Where things stand

The pipeline is **built, validated and reproducible end to end**: seven stages, exit 0,
ruff clean, re-run from a cleaned `data/` without error.

| Stage | Script | Produces |
|---|---|---|
| 0 | `00_validate_reference.py` | gates 37/37 on the reference tables and capital containment |
| 0 | `00_build_capitals.py` | rebuilds capitals from GeoNames |
| 1 | `01_acquire_mpi.py` | OPHI + UNDP, reconciled on MPI |
| 2 | `02_acquire_conflict.py` | UCDP events attributed to 37 states |
| 3 | `03_acquire_climate.py` | Open-Meteo daily 1990–2024, day-count QC |
| 4 | `04_merge.py` | the three processed tables + normalisation/data-quality docs |
| 5 | `05_preview.py` | the five spec visuals as PNGs |
| 6 | `06_build_twb.py` | `tableau/Nigeria-MPI-Equity-Atlas.twbx` |

### Not done

**The viz is not published.** This is the one thing left, and it cannot be automated:
Tableau Public has no write API and no publishing CLI (`tabcmd` targets Server/Cloud,
not Public), and the available `tableau` MCP server is read-only. Publishing is a GUI
action behind an account login. Follow `docs/PUBLISH.md`, then verify the live URL with
the MCP server's `get_workbook_image` — that catches a viz which uploaded but renders
empty.

---

## 2. Decisions taken (and the reasoning, so they aren't relitigated blindly)

| Decision | Chosen | Why |
|---|---|---|
| Conflict source | **UCDP GED**, not ACLED | ACLED unobtainable; UCDP is open, per-event geocoded, and covers all four survey rounds |
| Publish path | **Build `.twbx`, user clicks Save** | No publish API exists; a web dashboard was the alternative considered and declined |
| Temporal scope | **4-round trend included** | Answers the spec's own critique that it had "no temporal dimension"; makes the conflict scatter matched-year |
| Git | **init'd here, commits per stage** | Reproducibility for a pipeline that re-runs as sources update |

---

## 3. What is verified, and what is *not*

This distinction matters more than anything else in this document.

**Verified by execution:**
- All five sources download and parse; 37/37 coverage at every stage.
- OPHI and UNDP agree on MPI for all 37 states within 1e-3 — checked on every run.
- All 7,418 UCDP events attributed: 7,371 by name, 46 by point-in-polygon, 1 obsolete
  unit, **0 unattributed**.
- Every climate state-year has ≥300 contributing days; extremes are physically
  plausible (Kebbi hottest, Jos/Plateau coolest, Cross River wettest).
- The workbook XML parses, every field reference resolves to a declared column, and
  declared column ordinals match the packaged CSV headers.
- The five preview PNGs were rendered and **looked at**; layout defects were fixed.

**Not verified — no way to verify here:**
- **That the workbook renders correctly in Tableau.** Tableau Desktop 2019.4 is too old
  to open a modern workbook and needs interactive licensing; Tableau Public needs a
  human. This is the main open risk.
- Note: the Tableau MCP analyser reports `rowShelf`, `colShelf` and `worksheetsIncluded`
  as **empty even for the genuine Tableau-authored reference workbook** it was pointed
  at. Those fields are unimplemented in the analyser, so an empty shelf report is *not*
  evidence of a broken sheet — but it also means the analyser cannot confirm the sheets
  are wired. Do not treat it as a green light.

---

## 4. Traps already paid for

Every one of these was found the hard way; re-encountering them will cost time.

**Data sources**
- `data.hdx.humdata.org` **does not resolve** on this network. The legacy
  `data.humdata.org` serves the identical CKAN API and works. Use it everywhere.
- `api.acleddata.com` fails name resolution, and HDX's ACLED copy is aggregated
  country-year/month only — useless for a per-state index.
- The UNDP workbook's hardcoded column indices **will** break silently on a layout
  change. `01_acquire_mpi.py` guards them against the header text; if it trips, re-derive
  the `COL` dict rather than deleting the guard.

**Geodata**
- **Capital coordinates must not be typed from memory.** Several were wrong — one had
  latitude and longitude transposed. They now come from GeoNames' `PPLC`/`PPLA`
  admin-1 seat codes, gated on falling inside the state's own polygon.
- **OpenStreetMap geocoding is unusable for Nigerian capitals here.** Nominatim returned
  a *different place named "Lafia"* that lies in **Adamawa**, and could not resolve
  Ikeja, Abakaliki, Birnin Kebbi or Port Harcourt at all. GeoNames is the reliable source.
- Nominal containment testing is necessary but **not sufficient**: it happily accepts any
  building in the right state (an early build resolved "Osun" to *Osun Capital Hotel*).
  A settlement-class filter is also required.

**APIs**
- Open-Meteo's free tier rate-limits on **request count per hour**, not data volume.
  The whole 37-capital, 35-year pull is therefore a **single** request. The cache is
  keyed by state code and resumes rather than restarting.
- The 429 body is worth reading: `{"reason": "Hourly API request limit exceeded"}`. A
  short backoff just burns attempts.

**Analytical traps**
- The UNDP "missing indicator" flag reads `Nutrition` for **all 37** states. That is a
  country-wide exclusion, *not* a per-state comparability break — the first reading of
  it here was wrong.
- A single year's temperature anomaly correlates with MPI at +0.81 in 2013 and −0.43 in
  2021. It flips sign because it measures weather. **Use the 1991–2020 baseline** (rho
  = −0.80) for any climate–poverty claim.
- Conflict and poverty are **not** associated in these data (rho +0.34 → −0.20 across
  rounds). This is a real negative result. Do not rescue it by quoting one round.

---

## 5. Findings that constrain what may be claimed

These are in `docs/normalisation.md` and `docs/data_quality.md` and are regenerated with
the data. Keep them in sync with any viz published from this pipeline.

- MPI falls 0.230 → 0.175 nationally across the four rounds, but **rank persistence is
  0.87–0.92** — the *structure* of poverty is stable while the level falls.
- The **north-west is driven by education and living standards; the south-east by
  health** (Lagos is 70% health-driven, Bauchi only 15%). This is the atlas's strongest
  equity finding.
- Bauchi has the highest MPI (0.441) but **zero** UCDP events in 2021. Poverty without
  recorded conflict is a notable case.
- Borno takes Conflict Exposure Index = 100 in 2021 while the other 36 states cluster near
  zero, because min-max scaling is dominated by one extreme observation. The index is
  **cross-sectionally relative** and not comparable across survey years.
- 10 of 37 states recorded no UCDP event in 2021. That reflects reporting coverage as much
  as absence of violence; they are written as explicit zeros, not nulls.

---

## 6. Next steps, in order

1. **Install Tableau Public Desktop** (free) — *not* Tableau Desktop 2019.4, which is
   installed on this machine and too old to open the workbook.
2. Open `tableau/Nigeria-MPI-Equity-Atlas.twbx`; accept the packaged data paths.
3. **File → Save to Tableau Public.**
4. Confirm on the live URL that all five sheets render and the map draws Nigeria's states.
5. Add the radar chart per `docs/PUBLISH.md` (deliberately left to the GUI — a polygon
   mark driven by computed path fields is the most fragile part of the grammar to
   hand-write).
6. Set the choropleth to a sequential colour scale — it encodes a rate, not a category.
7. Paste the attribution block from `docs/PUBLISH.md` into the viz description.
8. Verify with `tableau` MCP `get_workbook_image`.

## 7. Environment reminders

- Python: `C:\Users\TOSHIBA\ds-general\python.exe`. Bare `python` is `C:\Python314`, a
  tooling env with none of these packages.
- `D:\` is a **removable USB SSD**. Copy this repository to `C:\Users\TOSHIBA` before
  unplugging, or the work disappears.
- Shell state does not persist between tool calls; chain commands with `;` / `&&`.
- Full machine map: `ENVIRONMENTS.md` (local only — see §8).

---

## 8. Repository hygiene note

`ENVIRONMENTS.md` is a machine-specific map (user name, drive layout, git config, and
the *names* — not values — of API keys present in the environment, plus paths to files
holding database credentials). It is useful locally and is **intentionally not
committed**: the repository is public, and that file describes the machine rather than
the project. It stays on disk and is listed in `.gitignore`.

If you clone this repository elsewhere, `docs/WORKFLOW.md` and this file carry the
essentials, but the environment-specific detail (which interpreter, which drives exist)
will not be there — expect to substitute your own paths in `scripts/run_all.ps1`.