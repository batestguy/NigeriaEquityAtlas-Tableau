# Handoff

State of the project as of this session, for whoever picks it up next — a new agent, a
collaborator, or future me after context is lost.

**Read this before running anything.** It records what was decided, what was actually
verified, and which traps have already been paid for.

---

## 0. Start here if you are picking this up

**The workbook opens in Tableau and every sheet has been looked at.** That was the
open risk for three sessions; it is closed. Two things changed the project beyond the
bug list: the atlas's claims were audited against OPHI's published standard errors,
and the "map" turned out never to have been a map.

**Read `docs/FINAL_PATH.md` first** — it is the routing sheet for the decided route.
Then `docs/CLAIMS.md` before writing any caption.

Next session, the shortest useful path:

```powershell
& C:\Users\TOSHIBA\ds-general\python.exe "scripts\06_build_twb.py"
& C:\TableauPublic\bin\tabpublic.exe "tableau\Nigeria-MPI-Equity-Atlas.twbx"
```

Then: **publish it.** File → Save to Tableau Public, then verify the live URL. The
two GUI upgrades in `docs/PUBLISH.md` are worth ten minutes afterwards.

Nothing needs installing. Nothing needs elevation. Nothing needs an API key.

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
| 6 | `06_build_twb.py` | `tableau/Nigeria-MPI-Equity-Atlas.twbx` (Hyper extracts, opens in Tableau) |

### Not done

**The viz is not published.** This is the one thing left, and it cannot be automated:
Tableau Public has no write API and no publishing CLI (`tabcmd` targets Server/Cloud,
not Public), and the available `tableau` MCP server is read-only. Publishing is a GUI
action behind an account login. Follow `docs/PUBLISH.md`, then verify the live URL with
the MCP server's `get_workbook_image` — that catches a viz which uploaded but renders
empty.

Also not done, and cheap: the two cosmetic fixes and the map confirmation in §3d.

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
- The five preview PNGs were rendered and **looked at**; layout defects were fixed.
- **The workbook opens in Tableau Public 2025.1 with no error dialog and renders
  data.** All five sheets are registered and the dashboard draws. This is new, and
  it is the check the previous session could not perform.
- The two packaged extracts hold 37 and 148 rows, and their **schema is read back out
  of the `.hyper` files** and compared against the declared columns at build time.

**Verified 2026-10-06, by opening the workbook and looking at every sheet:**
- `Where poverty sits` renders 37 correctly georeferenced points (latitude axis 7–13,
  Nigeria's actual range), coloured by MPI band. It is **not** a filled map and does
  not claim to be — see `docs/FINAL_PATH.md` §2 for the four approaches that failed
  and the one-minute GUI fix that converts it.
- `Poverty over time` draws 37 lines on one shared axis. `state` is off Columns and
  on Colour, so the trend is finally visible.
- `Dimension breakdown (three panels, not stacked)` renders three aligned panels, and
  says so in its own title.
- Both scatters carry `quadrant` on Colour **and** Shape.
- The dashboard draws its methodology text zone and KPI strip.

**Still not verified:** the filled choropleth (GUI step) and the radar chart.

### 3a. Tableau Public Desktop is installed

**`C:\TableauPublic`, Tableau Public 2025.1, build `20251.25.0313.2002`.** Installed
with:

```powershell
winget install --id Tableau.Public -e --accept-package-agreements --accept-source-agreements --location C:\TableauPublic
```

The installer is a **WiX Burn bundle**, so `--location` is honoured — it landed on
Drive C as asked (1.6 GB), with nothing new under `C:\Program Files\Tableau`. Re-run
without `--location` to accept the default path instead.

Two things worth recording:

- **Do not fetch the installer from `tableau.com`.** Both
  `https://www.tableau.com/downloads/public/pc64` and
  `https://downloads.tableau.com/tssoftware/TableauPublicDesktop-64bit-*.exe` return
  **HTTP 403** from this network. winget is the working route.
- **This is Tableau Public Desktop, not the paid Tableau Desktop.** They are separate
  applications and only the Public one can save to Tableau Public. See §3b for why
  the paid one was removed.

`tableauhyperapi` was added to `requirements.txt` this session and is needed by
stage 6. Without it the pipeline fails at the extract step, not at import.

### 3b. Why Tableau Desktop 2019.4 was removed rather than used

Unchanged, and now historical rather than blocking. It was installed, it parsed the
generated workbook — which is how three schema defects in `06_build_twb.py` were found
— but it could not serve as the render test. That was established by control test: the
*genuine*, Tableau-authored reference workbook (`ClimatechangeprofileNigeria`, version
18.1) also failed on this machine with *"This file was created by a newer version of
Tableau (Incompatible Document)"*. A real Tableau file failing identically proves the
ceiling belonged to the application, not the generated workbook.

**Keep that control-test habit.** It is the single technique that made this session
tractable: opening the *genuine* workbook in the *new* Tableau is what proved the
application was healthy and the generated file was at fault. Six defects were then
found one at a time, each confirmed by the application's own error message rather
than by guessing.

**And keep the habit that found the seventh, which no error message would have
given you: actually look at the render.** Schema validity, a successful load, and a
correct window title are three *different* things from a correct chart. The map sheet
passed all three for three sessions while drawing bar charts instead of Nigeria.

### 3c. The MCP situation is settled — no change needed

The connected `tableau` MCP server (`@wjsutton/tableau-public-mcp-server`) **is
already a Tableau Public server**, not a generic Tableau one. It exposes 22 read tools
(search, profiles, workbook details/contents, thumbnails and rendered images, `.twbx`
download/unpack/analysis) and every one of them has been used successfully here.

Tableau also publishes an official server (`@tableau/mcp-server`), but it is for
**Tableau Cloud/Server only**: it requires a server URL, a site name, and a Personal
Access Token. Tableau Public has none of those, so the official server cannot touch it.
Swapping would buy authenticated access to a product we do not use in exchange for
losing every Public read tool needed for post-publish verification.

No MCP server of any kind can publish to Tableau Public, because Tableau Public
exposes no write API. That constraint is in the product, not the tooling.

- Note: the Tableau MCP analyser reports `rowShelf`, `colShelf` and `worksheetsIncluded`
  as **empty even for the genuine Tableau-authored reference workbook**. Those fields
  are unimplemented in the analyser, so an empty shelf report is *not* evidence of a
  broken sheet — but it also means the analyser cannot confirm the sheets are wired.
  Do not treat it as a green light.

### 3d. What the render test found, and what is still open

Installing Tableau was the right call: it converted "unverifiable" into **six concrete
defects**, every one of which had been invisible to schema validation. They are fixed
and committed to the working tree; `scripts/06_build_twb.py` is the only file changed.

| # | Defect | Error Tableau raised |
|---|---|---|
| 1 | `textscan` `filename` carried `.csv`, and Tableau appends its own | `Unable to connect … mpi_atlas_2021.csv.csv` |
| 2 | Both top-level datasources shared the caption `Nigeria MPI Atlas` | `B5FA1F61` (`UniqueDataSource` assert) |
| 3 | `<cols>` aliased `state` to `[Data].[state]` — `Data` is the *directory*, not the relation | field unresolvable |
| 4 | **No `<column-instance>` elements anywhere** | `9CA7205B` `[sum:lat:qk]` does not exist |
| 5 | Data packaged as CSV | `3C242D89` Tableau Public requires extracts |
| 6 | `<extract>` in the wrong position, with an illegal `object-id` | `D2E8DA72` schema violation |

**Defect 4 is the one to remember.** Tableau builds a datasource's field list from its
`<column>` and `<column-instance>` children. Declaring the columns is *not* enough —
a shelf reference like `[ds].[sum:lat:qk]` with no instance behind it fails. The old
`deps_xml` docstring claimed shelf fields were only needed "by workbook analysers";
that was wrong, and it is why this shipped. Instances are now **derived from the
finished shelves**, so a field cannot reach a shelf without its instance following.

**Defect 5 also falsified a documented assumption**: the generator claimed "Tableau
converts a local extract on publish". It does not — it refuses. Stage 6 now writes
real Hyper extracts with `tableauhyperapi`, and the CSV-alignment gate was replaced by
a stronger one that reads the schema back out of the `.hyper` files. (It immediately
caught that Hyper reports `BIG_INT`, not `BIGINT`.)

**Defect 7 was only findable by looking, and it was the worst of them all.** The
"filled map" had never been a map — it drew **74 small lat/lon bar charts**. Three
prior sessions recorded this sheet as verified because the workbook loaded. It now
renders as a georeferenced scatter called `Where poverty sits`, and upgrading it to
filled polygons is a one-minute GUI step (`docs/PUBLISH.md`). Schema validation cannot
catch this class of defect: the XML is valid, the shelves resolve, and the render is
wrong.

**Still open, both GUI steps, both documented in `docs/PUBLISH.md`:**
- Filled choropleth (needs GUI-generated geographic fields).
- `Dimension breakdown` stacked bar (needs Measure Names/Values *and* its filter).
- The radar chart remains a deliberate GUI step.

**And a correction to this section's old list:** contribution values are *not* 0–1
fractions on a 0–100 axis. Per-state sums are 99.99–100.01. There was never a
formatting bug; the documentation was wrong.

### 3e. Verifying the render without fighting the desktop

**Correction: `PrintWindow` *can* capture Tableau's Qt canvas.** Three prior
sessions recorded that it cannot, and that is what left the map unchecked for three
sessions. Two things were wrong with the attempt:

1. **The window was minimised**, so `GetWindowRect` returned `(-21333, -21333)` with a
   158×26 size. Call **`ShowWindow(h, 9)`** (`SW_RESTORE`) — or `3` to maximise —
   *before* measuring. A screen grab then captures the terminal, because the terminal
   was never occluded by a visible window.
2. **Use flag `0x2`, `PW_RENDERFULLCONTENT`.** Flag `0` renders only Tableau's shell.
   `0x2` reaches the composited canvas.

Working sequence:

1. Launch detached: `Start-Process C:\TableauPublic\bin\tabpublic.exe -ArgumentList '"<path>"'`,
   then `Start-Sleep 60`–80.
2. Confirm the load: `Get-Process tabpublic | Select MainWindowTitle` reads
   `Tableau Public - Nigeria-MPI-Equity-Atlas`. A failed load shows `Book1`.
3. `ShowWindow(h, 3)` to maximise, sleep ~900 ms, then the **`AttachThreadInput`**
   trick (attach to the foreground thread, `BringWindowToTop` +
   `SetForegroundWindow`, detach).
4. `PrintWindow(h, hdc, 2)` into a `Bitmap` sized from `GetWindowRect`. Save as PNG.
   **No sleep after focusing** — another window redraws over Tableau within a second,
   which is why a screen grab must be taken immediately and `PrintWindow` is
   preferable: it captures the window, not the screen.
5. When a dialog is up, prefer the log:
   `%USERPROFILE%\Documents\My Tableau Repository\Logs\log.txt` is JSON-lines and names
   the exact failing field. `Get-Content`, not `ReadAllLines` — Tableau holds the file
   open. `Finished rendering sheet: <name>` lines confirm every sheet rendered even
   when the sheet is off-screen.

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

**Tableau XML — all of these cost a full launch/inspect cycle to find**
- **A shelf reference needs a `<column-instance>`.** Tableau resolves `[ds].[sum:x:qk]`
  against the datasource's field list, which is built from `<column>` **and**
  `<column-instance>` children. Declaring the column alone fails with
  `9CA7205B "the field does not exist in your database"`. Instances belong on the
  **datasource**, not only in the worksheet — the genuine reference workbook keeps
  85 of its 103 there and has no `<datasource-dependencies>` blocks at all.
- **Element order inside `<datasource>` is enforced.** The content model is roughly
  `connection?, …, aliases?, column+, column-instance+, …, extract?, layout?, style?,
  semantic-values?`. Putting `<extract>` before `<aliases>` produced `D2E8DA72`.
  When Tableau reports a schema violation, it prints the **entire allowed content
  model** — read it rather than guessing.
- **`<extract>` does not accept `object-id`.** Only `count`, `enabled`, `units`.
- **Datasource captions must be unique.** Two datasources sharing one caption trips
  a `UniqueDataSource` assert (`B5FA1F61`), even when their `name` attributes differ.
- **`<cols><map>` renames fields, and the value must name the relation, not the
  directory.** `[Data].[state]` silently breaks resolution because `Data` is the
  packaged *directory*. With one connection per datasource the element is unnecessary
  — delete it rather than fix it.
- **Tableau Public only publishes extracts.** `3C242D89`. It does **not** convert a
  live connection on save, contrary to what this project assumed for its whole life.

**The Hyper API (`tableauhyperapi`) — it is unforgiving about syntax**
- Connect with `Connection(endpoint=process.endpoint, database=<path>)`. Passing a
  bare path string as `endpoint` fails: *"'endpoint' must be an Endpoint instance"*,
  and `Endpoint(str(path))` then fails as *must be of the form `<scheme>://<rest>`*.
- `create_mode` belongs to **`Connection`**, not `Endpoint`. Use
  `CreateMode.CREATE_AND_REPLACE`.
- There is **no parameter binding** — no `execute_list_insert`. Only
  `execute_command`, `execute_query`, `execute_list_query`, `execute_scalar_query`.
  Values must be inlined as literals.
- Floats are **`DOUBLE PRECISION`**. Bare `DOUBLE` fails with *"type 'double' does not
  exist"* — it collides with a domain of that name. `REAL` fails too: *"This database
  does not support 32-bit floating points."*
- The catalog reports types back with **different spellings** than the DDL takes:
  `BIGINT` in, `BIG_INT` out; `DOUBLE PRECISION` in, `DOUBLE` out. Keep the two
  mappings separate or the schema validator will fail on a correct file.

**Windows / process notes**
- `TableauTemp` extraction directories and `hyperd.log` appear in the working
  directory. Both are now gitignored; `tableau/*.hyper` and `tableau/*.twbr` too.
- The winget partial that resisted deletion for a whole session was held by
  **Delivery Optimization (`DoSvc`)**. Non-elevated deletion always fails. With
  elevation, `Stop-Service DoSvc` then delete — done, 537 MB reclaimed.

**Analytical traps**
- The UNDP "missing indicator" flag reads `Nutrition` for **all 37** states. That is a
  country-wide exclusion, *not* a per-state comparability break — the first reading of
  it here was wrong.
- A single year's temperature anomaly correlates with MPI at +0.81 in 2013 and −0.43 in
  2021. It flips sign because it measures weather. **But the 1991–2020 baseline is not
  the answer either** — it is a north–south gradient, not climate. Baseline
  precipitation ↔ latitude is −0.903, and latitude ↔ MPI is **+0.821, better than
  precipitation ↔ MPI at −0.801.** Precipitation is the outcome's twin. Use the word
  OPHI uses: *overlap*. Never a causal verb. See `docs/CAUSAL_DECISION.md` §2c.
- Conflict and poverty are **not detectably** associated in these data (rho +0.34 → −0.20
  across rounds). **This is a null with a power floor, not a result about the world.** At
  n = 37 the power is 0.75 at rho = 0.4 and nothing survives Bonferroni; and the
  conflict variable *undercounts where poverty is highest* — in 2021 five of the poorest 12 states (Bauchi, Jigawa, Kebbi, Katsina, Kano)
  record zero UCDP events. Say "we detect none, and our design cannot see
  below |rho| ~ 0.4". See `docs/CAUSAL_DECISION.md` §2a.

---

## 5. Findings that constrain what may be claimed

These are in `docs/normalisation.md` and `docs/data_quality.md` and are regenerated with
the data. Keep them in sync with any viz published from this pipeline.

- On the **harmonised** series (OPHI Data Table 6, MN 63) national MPI runs 0.230 (2013
  DHS) → 0.215 (2016–17 MICS) → 0.208 (2018 DHS) → 0.175 (2021 MICS), but only the
  **2018→2021 step is nationally significant** (t = −3.81, ***); the two earlier steps
  are not (t = −1.57, −0.80). Rank persistence is **0.87–0.92** — the *structure* of
  poverty is stable while the level falls. **41 of 111 state-period changes are
  significant.**
- The **poorest states are education-weighted; the rest are health-weighted**
  (Lagos 70% health, Bauchi 15%). This is the atlas's strongest equity finding
  **and it is a poverty-level contrast, NOT a geographic one.** All 12 states
  with MPI > 0.20 sit in the two northern latitude bands, so at n = 37 "poor"
  and "northern" are the same 12 observations; among poor states latitude does
  *not* predict the dimension mix (r = -0.25). Say "poorest vs the rest", never
  "north vs south", and never with a causal verb. See `docs/CAUSAL_DECISION.md`.
- Bauchi carries the highest MPI point estimate (0.441) but is **not distinguishable
  from Jigawa or Kebbi** — and recorded **zero** UCDP events in 2021. Poverty without
  reported conflict is a notable case, and a case about reporting as much as violence.
- Borno takes Conflict Exposure Index = 100 in 2021 while the other 36 states cluster near
  zero, because min-max scaling is dominated by one extreme observation. The index is
  **cross-sectionally relative** and not comparable across survey years.
- 10 of 37 states recorded no UCDP event in 2021. That reflects reporting coverage as much
  as absence of violence; they are written as explicit zeros, not nulls.

---

## 5a. Read this before writing any claim

**Start with `docs/SESSION_HANDOFF.md`** — it is the current state of the project,
written this session. Then:

- `docs/CAUSAL_DECISION.md` — why the atlas makes **no causal claim** and what it
  makes instead.
- `docs/CLAIMS.md` — the permission table: what may be said, what is blocked, why.
- `docs/FIX_LEDGER.md` — the defect list, severity-ranked, plus what is *not* a defect.

The short version: **every causal path is closed**, on five independent grounds —
geography and poverty level are collinear at n=37, the within-poor trend reverses,
lagged correlations are null, panel fixed effects would absorb 91% of variance, and
there is no instrument or discontinuity. What survives is a **decomposition** claim,
which needs no identification because it is arithmetic on the published index.

Four claims that were wrong, now corrected above:

1. **"Bauchi has the highest MPI"** — OPHI's published standard errors show all 36
   adjacent rank pairs overlap at 95%. See `data/interim/mpi_se_ci.csv`.
2. **The north-west / south-east framing** — a poverty-level contrast wearing a
   geographic label. All 12 states with MPI > 0.20 are in the two northern bands.
3. **"Negative result" on conflict** — a null with a power floor, not a claim about
   the world. The variable undercounts where poverty is highest.
4. **The baseline-precipitation claim** — it is a north–south gradient, not climate.
   Latitude predicts MPI better than precipitation does.

---

## 6. Next steps, in order

**All five sheets have now been opened and looked at** — see `docs/FINAL_PATH.md` §2.
The two remaining GUI items and the publishing sequence:

1. **Publish.** Open the workbook, confirm five sheets and the two text zones, then
   **File → Save to Tableau Public**. Sign-in required; cannot be automated.
2. **Verify the live viz** with `tableau` MCP `get_workbook_image` — this catches a
   viz that uploaded but renders empty.
3. Paste the attribution block from `docs/PUBLISH.md` into the viz description. It is
   already on the dashboard canvas; the description is where people look first.
4. **Filled choropleth (5 min).** `Where poverty sits` is currently a georeferenced
   scatter, which is deliberate and honest, but a filled map is better. Steps in
   `docs/PUBLISH.md`; the target is `docs/preview/1_where_poverty_sits.png`.
5. **Stacked bar (5 min).** `Dimension breakdown` draws three aligned panels. Steps
   in `docs/PUBLISH.md`.
6. Radar chart — still a deliberate GUI step, as above.
7. Alt text per sheet: descriptive, objective, no interpretation.
8. Switch both scatters to the Color Blind palette, to pair with the Shape encoding
   already on `quadrant`.

**Note the `contrib_*_pct` percent-formatting item that used to be on this list is
not a bug** — those columns already sum to 100 per state.

## 7. Environment reminders

- Python: `C:\Users\TOSHIBA\ds-general\python.exe`. Bare `python` is `C:\Python314`, a
  tooling env with none of these packages.
- Tableau Public Desktop: `C:\TableauPublic\bin\tabpublic.exe`, on Drive C. Installed;
  nothing to do.
- **The agent shell is not elevated** and cannot be made so by agreement — elevation
  has to come from a UAC prompt. To run anything privileged, launch it with
  `Start-Process powershell.exe -Verb RunAs -ArgumentList '-File','<script.ps1>'`,
  have the script log its outcome to a file, and poll that file.
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