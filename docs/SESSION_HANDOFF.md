# Handoff — session 2026-10-08 (interactive map: Sheet 1 CLI alternative)

Sheet-by-sheet rebuild started at Sheet 1. The Tableau map sheet cannot become a
filled choropleth from CLI (four blind XML attempts failed, documented in
`docs/PUBLISH.md`), so Sheet 1 now ALSO ships as a CLI-built interactive HTML map.
Tableau workbook untouched in structure; its Sheet-1 subtitle + tooltip fields improved.

## Built this session (all CLI, all in git after this commit)

- `scripts/07_build_interactive_map.py` → `docs/preview/interactive_map.html`
  (self-contained Plotly, ~8.5 MB, works offline): true filled ADM1 polygons,
  5 MPI bands, rich hover (MPI + 95% CI, annotated H/A, poor count, dominant
  party + winning years), All-37 / Poorest-12 / Other-25 buttons each with its
  own viewport fit, cover hero (title, flag bar, flag watermark, unity emblem,
  `cover.jpg` photo slot), honesty footnote.
- `data/reference/state_dominant_party.csv` + `docs/dominant_party.md`: mode
  governorship party 1999–2021 per state, 6 ties listed, full event matrix with
  counts, lineage notes, sources. Rule: one entry per seating event, as-won
  labels, later defections don't rewrite. FCT = no elected governor.
- `poverty_group` (Poorest 12 vs Other 25) added in `04_merge.py` →
  `data/processed/mpi_atlas_2021.csv`; Sheet-1 TWB subtitle + Detail/hover
  fields in `06_build_twb.py`; `.twbx` rebuilt, XML + Hyper validation passed.
- `docs/preview/nigeria_flag.png`: generated asset, embedded base64.

## Decisions (each challengeable, all recorded)

- **D6 cover framing:** rejected "tale of two zones" + northerner-vs-southerner
  imagery. Same rule as ever (AGENTS.md/CLAIMS.md): the 12 poorest ARE the
  northern states at n=37, so zone framing is the same observations wearing a
  geographic label. Cover reads "One country, two realities — poorest states
  vs the rest", no zone labels on imagery.
- **Party is hover-only, never colour** (causal paths closed at n=37).
- **Lagos AD/APC "tie"** is one camp under four labels (AD→AC→ACN→APC),
  counted as-won and noted in `docs/dominant_party.md`. Same for AC/ACN/APC
  fragments in Ogun/Osun/Oyo. **Kwara 1999 recorded APP** (governor list prints
  ANPP; APP is the contemporary platform, same rename as sibling states).
- **2021 endpoint, Fourth Republic only** (1999–2021 governorships; 1991–93
  Third Republic excluded as incomparable).

## Root causes found (do not re-debug)

- `go.Choropleth` on the geo subplot draws a **full-frame rectangle inside
  every path** (proven via live DOM: 37 unique `d` strings, each prefixed with
  the frame rect; viewport colour = last state's band). Fix used: render
  through `Choroplethmapbox` with top-level feature `id`s.
- **carto-positron tiles now need an API key** (watermarked background) →
  `style="white-bg"`, fully offline.
- Plotly hover honours `<b>/<i>/<br>` only; span colours don't survive →
  hierarchy via weight + slant, chrome via `hoverlabel`.
- **Preview serving: NEVER `python -m http.server`** for the 8.5 MB file —
  single-threaded head-of-line blocking hangs the terminal and times out the
  tool call (this session, twice). Pattern that works: temp
  `threaded_server.py` (ThreadingHTTPServer) + `-RedirectStandardOutput`, kill
  afterwards. Launching even that hung at session end — see unverified note.

## ⚠ Verification status — what is PROVEN vs NOT

- PROVEN (screenshotted in headless browser): filled polygons all 37, band
  colours, buttons + per-view viewports with no edge clipping, toggle filter,
  styled hover incl. Lagos tie, Kaduna/Bauchi/Oyo/Abia hovers, party-years lines.
- NOT verified: the final cover build (new 🇳🇬 title, button explainer line,
  flag watermark, cover hero, photo slot, removed on-map labels, annotated
  hover metrics). It completed the build script exit-0 but was never rendered
  before the preview server stopped cooperating. **Next session: serve
  `docs/preview/interactive_map.html` and screenshot top (cover) + map +
  one hover before touching Sheet 2.** Rebuild: `& C:\Users\TOSHIBA\ds-general\python.exe scripts\07_build_interactive_map.py`.

---

# Handoff — session 2026-10-06

State of the project at the end of this session, written for whoever picks it up
next: a new agent, a collaborator, or future me after context is lost.

**This session changed the project's claim, not its code.** The pipeline is
unchanged and still runs clean end to end. What changed is that we now know which
of our findings survive scrutiny, and the answer was not the one we assumed.

---

## 0. Start here

**The workbook builds and opens in Tableau. It is not published. And it currently
makes three claims it cannot support.** Read these four documents before touching
anything:

| Document | What it is |
|---|---|
| `docs/CAUSAL_DECISION.md` | **The decision.** Why the atlas makes no causal claim, what it makes instead, and the five independent reasons every causal path is closed |
| `docs/CLAIMS.md` | **The permission table.** What may be said, what is blocked and why, with wording |
| `docs/FIX_LEDGER.md` | **The defect list.** 6 blockers + 8 workbook defects, severity-ranked, plus what is *not* a defect |
| `docs/HANDOFF.md` §7 | Environment, traps, command cookbook |

Then the shortest useful next action:

```powershell
& C:\Users\TOSHIBA\ds-general\python.exe "scripts\06_build_twb.py"
& C:\TableauPublic\bin\tabpublic.exe "tableau\Nigeria-MPI-Equity-Atlas.twbx"
```

and look at the map. Still the one visual nobody has seen.

---

## 1. What this session did

| | |
|---|---|
| **Read** | Every shelf, mark and encoding out of `tableau/Nigeria-MPI-Equity-Atlas.twb` — not from the docs, which were wrong |
| **Found** | OPHI publishes standard errors in the file the pipeline already downloads; all 36 adjacent rank pairs overlap at 95% |
| **Tested** | Every claim a reviewer would attack, in R, including the falsification test the literature predicts |
| **Researched** | Two adversarial reviews — Tableau viz criticism, and MPI methodology — against primary sources |
| **Wrote** | 3 new docs; corrected 4 false claims in `AGENTS.md` and `HANDOFF.md` |
| **Extracted** | `data/interim/mpi_se_ci.csv` — 37 states × SE, CI bounds, H SE |

Uncommitted working tree. `git log` is not yet the full story.

---

## 2. The four findings that changed the project

### 2a. The standard errors were there all along

`subnational-results-mpi.xlsx` sheet `5.4 SE & CI Region` — the file stage 1
already downloads. Median relative SE **15.1%**. Consequence:

> **All 36 adjacent rank pairs have overlapping 95% intervals. 0 of 36 are
> distinguishable.** Bauchi 0.4411 ± 0.0322 vs Jigawa 0.4377 ± 0.0250 → z = 0.08.

"Bauchi has the highest MPI" — currently asserted in `AGENTS.md`,
`HANDOFF.md` §5 and on the map — is **not a statement the data supports**.
Median CI width (0.075) is 81% of the median MPI value.

### 2b. The north-west / south-east finding is mislabelled

Our own headline: *"the north-west is driven by education and living standards;
the south-east by health."* Tested it:

| Sample | corr(latitude, education contribution) |
|---|---|
| All 37 | +0.850 |
| Not-poor states (n=25) | +0.794 |
| **Poor states (n=12)** | **−0.252** |

All 12 states with MPI > 0.20 sit in the two northern latitude bands; zero sit in
the southern two. At n = 37, "poor" and "northern" are **the same 12
observations**. The gradient is carried entirely by the rich southern states and
does not hold inside the group that matters.

**It is a poverty-level contrast wearing a geographic label.** Say "poorest
states vs the rest". Patched in both files.

### 2c. The climate layer is geography, and we were reporting it as climate

| Correlation | rho |
|---|---|
| baseline precipitation ↔ **latitude** | **−0.903** |
| latitude ↔ MPI | **+0.821** |
| baseline precipitation ↔ MPI | −0.801 |

Latitude predicts MPI *better* than precipitation does. Precipitation is the
outcome's twin. OPHI's own 2025 report used gridded **hazards** (heat, drought,
flood, air pollution) on a harmonised geometry — a strictly stronger design than
37 capital point-samples of annual totals.

### 2d. A documented bug does not exist

`HANDOFF.md` §3d and `PUBLISH.md` both list "contrib values are 0–1 fractions on a
0–100 axis" as an open defect. Per-state sums are **99.99–100.01**. They are
already percentages. The docs were wrong; the workbook is fine.

---

## 3. Why the atlas makes no causal claim

Full reasoning in `docs/CAUSAL_DECISION.md`. Five independent closures, each fatal
alone:

1. **Collinearity** — all 12 poor states are northern; nothing separates the two
   readings.
2. **The within-poor trend reverses** (−0.252).
3. **No temporal ordering** — MPI(t) → conflict(t+1) gives rho −0.073, +0.107,
   +0.017. All p > 0.45. Fearon & Laitin predict a signal; there isn't one.
4. **Panel FE would absorb 91% of variance** — within-state change is 9.1% of
   the cross-state spread. The one available escape is empty.
5. **No instrument, no discontinuity, no exogenous shock.**

**What survives is a decomposition claim**, because the MPI is H × A by
construction and the dimension contributions are an *identity*, not an inference:

| Finding | Value |
|---|---|
| Rank persistence | 0.922, 0.924, 0.867 |
| Education share: poorest 12 vs other 25 | 39.9% vs 22.3% (**17.6 pts**, p = 1e-5) |
| Health share: poorest 12 vs other 25 | 16.3% vs 31.3% (**15.0 pts**, p = 0.006) |

The 17.6-point gap is the headline. A 15% relative SE kills every *ordering*
(all 36 adjacent pairs overlap) but not a *group contrast* — that is the whole
argument for leading with it.

**The strongest defensible sentence:** level fell, structure held, and structure
differs by poverty level in a way that points at different interventions.

---

## 4. Would upgrading UCDP get us data? Investigated — mostly no

The honest answer, since it was asked: **we already have the upgrade, and it does
not rescue the null.**

**Already in `data/raw/ucdp_ged_nga.csv`, never used:**

| Field | Coverage |
|---|---|
| `adm_2` (LGA) | **88.1% of events, 445 distinct LGAs** |
| Name hygiene | Zero values containing "state", "rural" or "jhz" |
| `low` / `best` / `high` | **6,120 of 6,120 events have all three** |
| `where_prec` | 69.8% at exact-or-near location |

**Why it cannot fix the present null:** the state-level event count is *identical*
whatever geography you use — LGA disaggregation only redistributes events within
a state. And **all 10 zero-event states in 2021 are zero at LGA level too**
(Bauchi, Kano, Katsina, Jigawa, Kebbi, Kogi, Edo, FCT, Cross River, Bayelsa —
verified, 0 events each). The coverage failure is in the source, not the
aggregation. No amount of re-cutting fixes it.

**What upgrading *does* buy, and it is real:**

1. **Fatality-band robustness — publishable today.** The null is stable across
   a ±50% casualty band:

   | 2021 measure | rho with MPI | CEI top | 2nd |
   |---|---|---|---|
   | `low` | +0.065 | Borno (100) | Benue (10.1) |
   | `best` | +0.026 | Borno (100) | Yobe (12.2) |
   | `high` | −0.011 | Borno (100) | Yobe (11.7) |

   "Our null is not an artefact of the casualty estimate" is a defensible claim
   we can make today. Also: `high/best` widens over time (1.30 in 2013 → 1.75 in
   2021) — material for any future panel work.
2. **Better future design.** LGA-level conflict + LGA-level MPI (NBS designed the
   2022 survey for 109 senatorial districts) puts outcome and treatment at the
   *same* unit, which dissolves closure 1 above. That is the only route to a real
   causal claim. It is a different project, not a stage-7 change.

**Bottom line:** do not chase ACLED, do not chase LGA for this viz. Carry the
fatality band through (cheap, it makes a robustness claim visible) and record the
LGA route in the docs.

---

## 5. Next steps, in order

Nothing below is aesthetic. Aesthetics are last, and `docs/FIX_LEDGER.md` §C.

### 5.1 Decisions needed (blocking)

| # | Decision | Options |
|---|---|---|
| **D1** | **A4 — MPI series.** The rounds are *standardised* (HDX resource description confirms). OPHI: "may not be comparable across time". | (a) Re-source from the harmonised series (Data Table 6 / HDX trends); (b) keep and drop the word "fell" |
| **D2** | **Climate layer.** | (a) Relabel as gradient and state the latitude correlation beside it; (b) drop the layer and keep three sheets |
| **D3** | **Conflict sheet framing.** | (a) Keep as a documented null with power + band robustness; (b) drop |

Recommendation on D1: **(b)**. Re-sourcing is a download and a re-merge, and the
level numbers would move. The rank-persistence finding — the one we want to lead
with — is a within-file comparison and is unaffected either way. Take the re-source
only if the harmonised subnational tables turn out to carry all 37 states.

### 5.2 Data and code (unblocked, mechanical)

1. **Wire the standard errors through.** Stage 1 reads sheet `5.4`; stage 4 passes
   `mpi_se`, `mpi_lo`, `mpi_hi`, `headcount_se` into `mpi_atlas_2021.csv`; stage 6
   declares them as columns. *(`data/interim/mpi_se_ci.csv` already extracted.)*
2. **Carry the fatality band.** `conflict_state_year.csv` already has
   `fatalities_low` and `fatalities_high`; pass them to the extract.
3. **D1 — `Poverty over time`.** `state` is a second discrete field on Columns, so
   Tableau draws 37 single-point panes. Move to Colour. Ship the trend.
4. **D2 — `Dimension breakdown`.** Measure Names on Columns / Measure Values on
   Rows. Colour by dimension, not by `contrib_health_pct`.
5. **D3–D6 — encoding fixes.** Drop size from `Incidence vs intensity`
   (corr with x-axis = +0.942); fix or rename the `quadrant` cut (H spans ×68, A
   spans ×1.6); size `Poverty vs conflict` by per-100k not raw count; `quadrant` →
   Shape (WCAG 1.4.1).
6. **D7 — dashboard text zone + KPI tiles.** This is where all six caveats must
   live. Highest value-per-hour item in the list.
7. **D8** — `fatalities_per_100k` typed as string in the panel datasource.

### 5.3 Documentation

- `docs/PUBLISH.md` — remove the phantom `contrib_*_pct` bug; add the two new
  caveats; update the sheet table after D1–D3 land.
- `docs/data_quality.md` — rewrite item 1: Health is **re-weighted to a full
  one-third**, and cross-country comparison is therefore forbidden.
- `docs/PUBLISH.md` attribution block — add OPHI MN 62, Table 5.4 as the SE source.

### 5.4 Never verified

**That the map draws Nigeria's 37 polygons.** Still first. Everything else is
downstream of knowing the workbook renders.

---

## 6. What is *not* a defect

Confirmed clean. Each was a likely criticism; none applies. Full list in
`docs/FIX_LEDGER.md` §D — do not "fix" any of these.

- No rainbow colour map. No 3D. No dual axes. No pie charts. No truncated axes.
- The map encodes a rate, not a count — the most common choropleth sin, avoided.
- The choropleth is **not** a WCAG 1.4.1 colour-only violation: a sequential ramp
  varies lightness, which W3C counts as an additional distinction.
- State-vs-national comparison **is** permitted — OPHI MN 56, decomposability.
  Much of the standard advice to the contrary does not apply here.
- Nigeria passed OPHI's subnational criteria (≥85% national / ≥75% per-region
  retained sample, bias analysis). Say so — it converts "no uncertainty shown"
  into "the publisher's own bar was met".
- The six XML defects found by loading in real Tableau are fixed and committed to
  the working tree; the workbook loads and renders.

---

## 7. Environment

- Python: `C:\Users\TOSHIBA\ds-general\python.exe`. Bare `python` is `C:\Python314`.
- Tableau Public Desktop 2025.1: `C:\TableauPublic\bin\tabpublic.exe`. Installed.
- R 4.5.2 via `Rscript`; the `rmcp` server works and is the fastest way to audit
  statistics. **`dplyr` is allowlisted; `psych` is not** — `partial.cor` is
  unavailable, use rank-based contrasts instead.
- `ruff` is **not** installed in `ds-general`. Lint via a different route or skip.
- Shell state does not persist between calls. Chain with `;` / `&&`.
- `D:\` is a **removable USB SSD**. Copy to `C:\Users\TOSHIBA` before unplugging.
- Full machine map: `ENVIRONMENTS.md` (local only, gitignored by design).

**Traps already paid for** — full list in `docs/HANDOFF.md` §4. The short ones:
`data.hdx.humdata.org` does not resolve (use `data.humdata.org`); do not fetch the
Tableau installer from `tableau.com` (403, use winget); the agent shell is not
elevated; `Get-Content` not `ReadAllLines` on Tableau's log file.

---

## 8. References behind this session's judgements

**Methodology of the index**
- Alkire, S. & Foster, J.E. (2011). "Counting and multidimensional poverty
  measurement." *Journal of Public Economics* 95(7–8): 476–487.
- Alkire, S., Mishra, R., Selden, L. & Suppa, N. (2025). *Global MPI 2025:
  disaggregation results and methodological note.* OPHI Methodological Note 62.
  — **source of Table 5.4, the standard errors, and the disaggregation criteria.**
- OPHI Methodological Note 58 (2024) — "may not be comparable across time."
- OPHI Methodological Note 56 (2023) — decomposability; state vs national.
- OPHI Methodological Note 63 (2025) — DHS/MICS harmonisation.
- UNDP & OPHI (2024). *Global MPI 2024: Poverty amid conflict.*

**The conflicts we found with ourselves**
- Djankov, S. & Reynal-Querol, M. (2008). "Poverty and Civil War: Revisiting the
  Evidence." CEPR DP 6980. — the cross-sectional correlation is not the estimand.
- Fearon, J.D. & Laitin, D.D. (2003). "Ethnicity, Insurgency, and Civil War."
  *APSR* 97(1): 75–90. — the recruitment channel we tested (null).
- Abidoye, B.O. & Calì, M. (2021). "Income shocks and conflict: evidence from
  Nigeria." *Journal of African Economies* 30(5): 480–509. — the identification
  strategy we do not have.
- UCDP GED Codebook v24.1. — media-construction and spatial-coverage limits.
- Sbarra, N. et al. (2023). *Scientific Reports* 13:11085. — Borno estimates not
  state-representative.

**The climate and ecology reasoning**
- Burke, M., Hsiang, S. & Miguel, E. (2015). "Global nonlinear effects of
  temperature on economic production." *Nature* 527: 235–239.
- Dell, D.C., Jones, B.D. & Olken, A.B. (2009). "Temperature and Income."
  *AER* 99(2): 198–204. — cross-sections overstate; the heterogeneity is ours.
- Lavers, A. & Villarini, G. (2022). "An evaluation of ERA5 precipitation."
  *QJRMS*. — the wet bias and the missed orographic enhancement.
- Robinson, W.S. (1950). "Ecological Correlations." *ASR* 15: 351–357.
- Openshaw, S. (1983). *The Modifiable Areal Unit Problem.* CATMOG 38.

**Visualisation criticism**
- Beconytė, V. et al. (2022). "Where Maps Lie." *ISPRS IJGI* 11(1): 64.
- Schiewe, J. (2019). *CaGIS* — small areas missed by 30–40% of map users.
- Cleveland, W.S. & McGill, R. (1985). *Science* 229: 828–833.
- Bradley, W. (2023). *IJGIS* — viewers read magnitude off the legend range.
- Crameri, F., Kok-Slok, S. & Le Blanc, S. (2020). *Nature Communications* 11:5444.
- W3C. WCAG 2.1 SC 1.4.1, SC 1.4.11.
- Tableau, *Visual Analytics Best Practices: A Guidebook*.

---

## 9. Honest assessment

The pipeline is good — reproducible, gated, every source reconciled, 37/37
asserted at every stage, 7,418 events attributed with 0 unattributed, a sign flip
that killed a single-year approach. **None of that is visible to a published
viewer**, which is the actual opportunity.

The spec asked for a choropleth, a stacked bar, two scatters and a radar. It did
not promise identification. Adopting a causal framing we cannot support would be
volunteering for a fight nobody asked us into — and it would cost us the two
overlays that make the viz interesting in exchange for nothing.

One defensible finding beats three undefendable ones. Lead with the group
contrast; keep the conflict layer as an honest null with its power floor attached;
drop or relabel the climate layer; and put the caveats on the canvas where a
reviewer will actually read them.
