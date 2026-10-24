# Fix ledger

Every defect found by reading the generated workbook, the generated data, and an
adversarial statistical review. **Nothing here is aesthetic.** Aesthetics are
blocked until the claims are defensible — see `docs/CLAIMS.md`.

Severity:
- **BLOCKER** — makes the viz wrong or misleading if published as-is.
- **DEFECT** — visibly broken; a reviewer will point at it.
- **IMPROVEMENT** — worth doing, not load-bearing.

Status: `todo` / `done`.

---

## A. Blockers — statistical and methodological

### A1. "Bauchi has the highest MPI" is not a defensible statement
**Severity BLOCKER · status todo**

OPHI publishes design-based standard errors for exactly these 37 estimates
(`subnational-results-mpi.xlsx`, Table 5.4, "SE & CI Region"). We were not
using them. They are now extracted to `data/interim/mpi_se_ci.csv`.

| | MPI | SE | 95% CI |
|---|---|---|---|
| Bauchi | 0.4411 | 0.0322 | 0.379 – 0.505 |
| Jigawa | 0.4377 | 0.0250 | 0.389 – 0.487 |
| Kebbi | 0.4373 | 0.0327 | 0.375 – 0.502 |
| Sokoto | 0.4372 | 0.0416 | 0.358 – 0.520 |
| Zamfara | 0.3913 | 0.0292 | 0.336 – 0.450 |

Bauchi − Jigawa = 0.0034, z = 0.08. **All 36 adjacent rank pairs have
overlapping 95% intervals — 0 of 36 are distinguishable.** Median CI width is
0.0746, which is 81% of the median MPI value.

**Fix.** Carry `mpi_se`, `mpi_lo`, `mpi_hi` through stage 4 into the extract.
Never assert an ordering; present bands. Replace "Bauchi has the highest MPI"
with "the north-west states occupy the top of the distribution — Bauchi, Jigawa,
Kebbi and Sokoto are statistically indistinguishable at the 95% level."

**Where it lands:** `docs/data_quality.md`, `docs/HANDOFF.md` §5, sheet 1 map
subtitle, and any alt text.

---

### A2. The climate finding is a north–south gradient, not a climate effect
**Severity BLOCKER · status todo**

Baseline 1991–2020 precipitation vs MPI gives rho = −0.801 (p < 1e-33), which
reads as a strong finding. But:

| Correlation | rho |
|---|---|
| baseline precipitation ↔ **latitude** | **−0.903** |
| latitude ↔ MPI | **+0.821** |
| latitude ↔ education contribution | +0.850 |
| latitude ↔ intensity | +0.795 |
| baseline precipitation ↔ education contribution | −0.806 |

Precipitation is almost a restatement of latitude, and latitude alone predicts
MPI *better* than precipitation does. The published claim is therefore "Nigeria
has a north–south development gradient", measured twice — not "climate affects
poverty". Burke, Hsiang & Miguel's survey (2015) shows baseline rainfall has
essentially no cross-sectional relationship with income; the identified
literature uses within-unit variation or panels.

**Fix.** Either relabel the climate layer as a geographic gradient with the
latitude correlation stated alongside, or drop it and replace it with the OPHI
2025 hazard-overlap framing. Do **not** ship rho = −0.80 unqualified.

---

### A3. The conflict null is a measurement artefact, not evidence of absence
**Severity BLOCKER · status todo**

Three independent reasons the null cannot be read as "no relationship":

**(a) Power.** n = 37. Power to detect a true rho: 0.3 → 0.55, 0.4 → 0.75,
0.5 → 0.87. Critical |rho| at n = 37 is 0.326; after Bonferroni ×4 the 2013
round (rho = +0.339, p = 0.040) becomes p = 0.161. Nothing survives.

**(b) Differential undercounting, and it runs the wrong way.** Zero-recorded-event
states are the *poorer* ones:

| Year | zero-event states | their mean MPI | mean MPI elsewhere |
|---|---|---|---|
| 2013 | 16 | 0.137 | 0.243 |
| 2016 | 13 | 0.218 | 0.137 |
| 2018 | 14 | 0.213 | 0.156 |
| 2021 | 10 | **0.218** | **0.142** |

In 2021 the five worst-poverty states in the country — Bauchi (rank 1),
Jigawa (2), Kebbi (3), Katsina (8), Kano (11) — all recorded zero UCDP events.
UCDP GED is newswire-based; its own codebook says "media reporting is not
consistent across time or space". Rural farmer–herder and banditry violence is
exactly what that misses. **The conflict variable fails hardest where poverty is
highest**, which biases the correlation toward zero by construction.

Dropping Borno does not change the picture (2013 +0.339 → +0.316; 2021 −0.061 →
−0.109), so Borno is not the explanation — coverage is.

**(c) The result is robust to the fatality uncertainty band — which is itself
the useful finding.** UCDP publishes `low`/`best`/`high` per event and **all
6,120 events in our window carry all three**. We have been using `best` only.

| 2021 fatality measure | rho with MPI | CEI top state | 2nd |
|---|---|---|---|
| `low` | +0.065 | Borno (100) | Benue (10.1) |
| `best` | +0.026 | Borno (100) | Yobe (12.2) |
| `high` | −0.011 | Borno (100) | Yobe (11.7) |

The null does not move across a ±50% fatality band. That is a *defensible*
statement — the finding is not an artefact of the casualty estimate — and it
should be made explicitly. Note also the `high/best` ratio widens over time
(1.30 in 2013 → 1.75 in 2021), which matters for any future panel work.

**Fix.** Reword from "conflict and poverty are not associated" to "we detect no
stable cross-sectional association, and our design cannot detect one below
|rho| ≈ 0.4". Report the power figure on the sheet. Carry the fatality band
through to the extract so the robustness is visible. Cite Djankov &
Reynal-Querol (2008) — the canonical demonstration that this cross-sectional
correlation is not the causal estimand — and UNDP's 2024 *Poverty amid
conflict*, which asserts the opposite and must be addressed head-on.

**What LGA-level disaggregation would and would not buy — investigated, and
the answer is mostly "would not".** `adm_2` is already populated for **88.1% of
events across 445 distinct LGAs**, with clean names (zero containing "state",
"rural" or "jhz"), covering 57.5% of Nigeria's 774 LGAs. So the finer geography
is already in `data/raw/ucdp_ged_nga.csv` — no new download is needed, only a
new attribution step.

But it cannot fix this null, for a specific reason worth recording: **the
state-level event count is identical whatever geography you use.** LGA
disaggregation only redistributes events *within* a state. And **all 10
zero-event states in 2021 are zero at LGA level too** — Bauchi, Kano, Katsina,
Jigawa, Kebbi, Kogi, Edo, FCT, Cross River and Bayelsa have no events to
redistribute. The coverage failure is in the source, not the aggregation.

LGA-level data is therefore a *future-design* asset, not a present-tense
rescue. See `docs/CAUSAL_DECISION.md` §6.

---

### A4. The four survey rounds are the standardised MPI series, which OPHI says is not comparable over time
**Severity BLOCKER · status CONFIRMED — decision needed**

**Resolved.** The HDX resource description for the exact file we download reads:
"This resource contains **standardised** MPI estimates and their changes over
time by first-level administrative unit."

`data/raw/ophi_nga_mpi_trends.csv` carries national rows of 0.2304 (2013),
0.2149 (2016), 0.2083 (2018), matching Table 1/2 of the 2023 global MPI
statistical tables — the **standardised** series. OPHI's Methodological Note 58:
"Estimation for a given year will therefore be the most accurate possible figure
using the available data **but may not be comparable across time.** Indicator
definitions must be harmonised for comparability over time."

NBS's own report, quoting the global MPI 2021, gives the **harmonised** Nigeria
series as 0.287 (2013) → 0.254 (2018) — headcount 51.3% → 46.4%, against the
standardised 42.3% → 38.2%. Same surveys, ~9-point headcount difference.

Our rounds alternate DHS and MICS, exactly the case harmonisation exists for.
OPHI itself harmonised Nigeria and reports four points in time (MN 60, 2024) —
that harmonised series is Data Table 6 / the HDX "Global MPI Trends Over Time"
resource, and it is **not** what we downloaded.

**This is the most likely line of expert attack on `Poverty over time`.**

**Two options, take the first:**
1. Re-source the four rounds from the harmonised series. Everything temporal
   depends on this.
2. Keep the standardised series — defensible, since it is "the most accurate
   possible figure" for each year — but stop calling it a trend. "Level in each
   of four survey years, indicator definitions not held constant across them" is
   a legitimate statement. "Poverty fell from 0.230 to 0.175" is not.

Note the awkward consequence: the *level* changes (0.441 → 0.162 mean across
states) are large enough to survive harmonisation, but the exact figures would
move. The rank-persistence finding (0.867–0.924) is a within-file comparison and
is unaffected either way — which is another reason it is the safer headline.

---

### A5. Borno's MPI is not state-representative
**Severity BLOCKER · status todo**

MICS 2021 sampled Borno from 7 accessible LGAs of 27 — 29% of the population
(Nigeria 2021 MICS Survey Findings Report §2.2). The 2018 DHS replaced 39% of
Borno's clusters. Sbarra et al. 2023 (*Scientific Reports* 13:11085) states
Borno estimates "are not representative at the state level". OPHI's first
subnational disaggregation criterion is exactly that.

Borno is simultaneously 51% of all recorded events and 64% of all recorded
fatalities in 2021.

**Fix.** Flag Borno's 2016/2018/2021 MPI as not state-representative in the viz.
It does not rescue the null (A3) — but pairing a whole-state conflict score with
a 7-LGA poverty score is indefensible if unflagged.

---

### A6. `contrib_*_pct` are 0–100 already — a documented defect does not exist
**Severity DEFECT (documentation) · status todo**

`docs/HANDOFF.md` §3d and `docs/PUBLISH.md` both record "contribution values are
0–1 fractions rendered against a 0–100 axis" as an open bug requiring percent
formatting. **That is wrong.** Per-state sums are 99.99–100.01. The columns are
already percentages on a 0–100 scale. No formatting change is needed; the docs
need correcting.

The real problem on `Dimension breakdown` is the three-panes-not-stacked-bar
defect (D2), plus a different issue: contribution shares are only meaningful
where MPI itself is resolvable. Abia's MPI is 0.042 with a 95% CI of 0.030–0.059;
its "57.7% health-driven" share describes 0.002 of index weight.

---

## B. Defects in the generated workbook

Read out of `tableau/Nigeria-MPI-Equity-Atlas.twb`, not the docs.

### D1. `Poverty over time` cannot show a trend
**Severity BLOCKER · status todo**

```xml
<cols>[none:survey_year:nk] + [none:state:nk]</cols>
```

`state` is a **second discrete field on Columns**, so Tableau draws 37
side-by-side single-point panes rather than 37 lines on one axis. The temporal
finding is currently invisible.

**Fix.** `cols` = `survey_year` only; `state` → Colour. Report rank
persistence (0.922, 0.924, 0.867) as the finding — level falls, structure holds.

---

### D2. `Dimension breakdown` draws three panes, not a stacked bar
**Severity DEFECT · status todo**

Three measures on `rows`. Needs Measure Names on Columns / Measure Values on
Rows. Colour should be by dimension, not bound to `contrib_health_pct` — colour
currently carries a *different* measure than bar length.

---

### D3. `Incidence vs intensity` — the size channel duplicates the x-axis
**Severity DEFECT · status todo**

Size = `mpi_poor_thousands`; corr(H, mpi_poor_thousands) = **+0.942**. The chart
encodes headcount twice. Drop the size encoding, or size by something
independent.

---

### D4. The `quadrant` cut is not a quadrant
**Severity DEFECT · status todo**

The label promises two binary dimensions. In fact H spans 1.11–75.36 (**×68**)
while A spans 39.45–61.80 (**×1.6**). The cutpoints sit near the medians, so
the "quadrant" is essentially a poor/rich split with cosmetic jitter. Result:
17 / 2 / 2 / 16 — not the balanced 9/9/9/9 the name implies.

**Fix.** Either cut on the actual medians and say so, or rename to what it is
(an incidence-based poverty class). Add median reference lines.

---

### D5. `Poverty vs conflict` sizes by a count on a rate chart
**Severity DEFECT · status todo**

Size = `SUM(fatalities)` — a raw count — on a plot whose x is an index and
whose y is a per-100k min-max rate. Three denominators on one plot, none
labelled. Cleveland & McGill rank area low; Borno's 2,027 fatalities dominate the
size scale and every other state becomes a dot. Use `fatalities_per_100k`, or
drop size.

---

### D6. `quadrant` is on colour only — fails WCAG 1.4.1
**Severity DEFECT · status todo**

Both scatters encode a meaningful categorical dimension on colour with no
second channel. The choropleth is *not* affected (a sequential ramp varies
lightness, which W3C counts as an additional distinction) — do not let anyone
claim otherwise.

**Fix.** `quadrant` → Shape on both scatters. Switch to Tableau's Color Blind
palette. Four members, well inside the ~5 CVD-safe colours available.

---

### D7. No legend zones, no KPI tiles, no methodology text on the dashboard
**Severity BLOCKER · status PARTLY FIXED — text zones and the KPI strip ship; the colour
legend still does not draw**

The `<zones>` block contains five worksheet zones and one empty layout
container. No legend, no text object. The map's colour encoding is unlabelled
and **none of the caveats in `docs/data_quality.md` are visible to a published
viewer.**

**Fix.** One text zone carrying: sources with vintages; Health = child mortality
alone with the Nutrition indicator excluded and Health re-weighted to a full
third; CEI is cross-sectionally relative and not comparable across years; 10 of
37 states recorded zero reported events, reflecting coverage not absence of
violence; state population denominators come from an unstated UNDP vintage
~2% above the 2023 national total; state-level is the finest resolution the
survey supports. Plus 4–5 KPI text tiles.

**Still open (2026-10-18): the colour legend.** Sheet 1 declares the right-edge
`type='color'` card exactly as a Tableau-authored Public workbook declares its working
one, and window `<cards>` **are** honoured — deleting the Marks card from the same block
removes it from the UI — yet no legend renders. Ruled out by experiment: `<simple-id>`
(rejected by this schema, `D2E8DA72`) with and without the reference's
`<document-format-change-manifest>`, the reference's second `rows` strip, and the mark
class (a Circle version of the sheet shows no legend either). The one click that settles
it is **Analysis → Legends → Colour Legend**, then Save; the full account is in
`docs/PUBLISH.md`.

---

### D8. `fatalities_per_100k` typed as string in the panel datasource
**Severity DEFECT (latent) · status todo**

`datatype='string' role='dimension'` in the panel datasource vs
`datatype='real' role='measure'` in the atlas datasource. Nothing puts it on a
shelf today, so it is latent — but it becomes a visible bug the moment anyone
adds it to a tooltip.

---

### D9. The five MPI bands had no colours assigned
**Severity DEFECT · status done (2026-10-18)**

`mpi_band` is a nominal dimension, so Colour drew it in **Tableau's default
categorical palette** — five unrelated hues on a scale whose whole meaning is its
order. Nothing in the workbook declared a palette; `grep palette` over the packaged
`.twb` returned nothing. The defect had never been seen because the one surface that
would have shown it, the colour legend, has never drawn either (see `docs/PUBLISH.md`
open issues).

Stage 6 now assigns the five colours in the polygon datasource (`palette_block`),
with the grammar copied from two real Tableau-authored Public workbooks downloaded
via the MCP server. Colours and order come from `atlas_text.MPI_BANDS`, which stages
5 and 7 also read, so the workbook and both preview maps cannot drift apart; the
colour carries no red-green pair and darkens monotonically.

Found in the same pass, same sheet, all fixed and verified by rendering:

- the stage-5 QA gate rendered a continuous `YlOrRd` ramp of **H**, a different
  measure from the one both maps colour by, so it could not catch a sheet-1
  regression. It now draws the same five bands on the same measure;
- the `mpi_band` caption was written twice and disagreed (datasource vs all six
  worksheet copies). One map now feeds both;
- four detail fields (`mpi`, `mpi_se`, `mpi_ci_lo`, `mpi_ci_hi`) were on the marks
  card whose values never reached a reader.

**Where it lands:** `docs/PUBLISH.md`, `docs/SESSION_HANDOFF.md`, `AGENTS.md` #7.

---

## C. Improvements

### C1. Colour legend range
The Conflict Exposure Index puts Borno at 100 with the other 36 near zero, and
Bradley (2023, *IJGIS*) shows viewers read magnitude off the legend range — so
the 36 read as identical when the arithmetic says otherwise. Consider a log or
rank scale, or a quantile binning, alongside the raw per-100k rates.

### C2. Small-state legibility
Schiewe (*CaGIS* 2019): small areas with extreme values are missed by 30–40% of
map users. Lagos and the FCT are slivers and are the states most likely to be
missed — and the FCT is the most-poverty-dense unit. McNabb et al.: accuracy
degrades below ~10 px of displayed area. Verify at viewport width.

### C3. Alt text
Editable since Tableau 23.2. Objective description only — no "shows the
troubling north-south divide". Guidance: https://trailhead.salesforce.com/content/learn/modules/accessible-data-visualizations-in-tableau/provide-descriptive-text

### C4. Avoid three colour roles on one canvas
Sequential ramp (map), continuous measure (bar sheet), categorical quadrant (two
scatters), and no colour at all (line chart). Tableau's 5-second-test guidance
advises against multiple colour schemes on a single dashboard.

### C5. The five tabs are a lot
Nothing tells a viewer where to start. The dashboard text zone (D7) solves this.

---

## D. Not defects — do not "fix" these

Confirmed clean. Each was a likely criticism; none applies.

- **No rainbow colour map, and no categorical default either.** Tableau's sequential
  default is blue, so the Crameri/Borland critique does not land; but a *nominal* field
  falls back to the categorical palette, which was D9 until 2026-10-18. The bands now
  carry explicit colours (ColorBrewer YlOrBr, monotone in lightness).
- **No 3D, no dual axes, no pie charts, no truncated bar axes.** All clean.
- **The map encodes a rate, not a count.** Avoided the single most common
  choropleth failure.
- **No red–green pairing** anywhere.
- **`&lt;column-instance&gt;` generation** — the six defects from the last session
  are fixed and the workbook loads and renders.
- **OPHI subnational criteria met.** Nigeria passed OPHI's ≥85% national /
  ≥75% per-region retained-sample and bias-analysis tests. State is the finest
  resolution the survey supports — say so, it defuses the MAUP criticism.
- **State-vs-national comparison is permitted.** OPHI MN 56 explicitly sanctions
  it via population-subgroup decomposability within a country, same year. Much
  of the online advice to the contrary does not apply here.
- **"Negative result" honesty.** `AGENTS.md` already forbids quoting a single
  round. That discipline is right; only the *wording* in A3 needs changing.

---

## E. Order of work

**Before anything is published:**

1. A4 — decide standardised vs harmonised series. Gates `Poverty over time`.
2. A1 — carry SEs through, reword every ordering claim.
3. A2 — relabel or drop the climate layer.
4. A3 — reword the conflict finding, add the power figure.
5. A5 — flag Borno.
6. A6, D7 — correct the docs; add the methodology text zone.
7. D1, D2 — the two broken sheets.
8. D3, D4, D5, D6, D8 — encoding corrections.

**Then, and only then:** C1–C5 aesthetics.

**Never verified:** that the map draws Nigeria's 37 polygons. Still first.

---

## F. Registered before code

Not defects. Listed so a reader can find what was fixed in advance, and check
`git log` that it was.

### F1. Spatial autocorrelation of state MPI (Moran's I)
**Severity n/a — a registered test · status built 2026-10-18**

The full specification is `docs/spatial_preregistration.md`, committed as a
docs-only change before `scripts/09_spatial_diagnostics.py` or
`scripts/spatial_diagnostics.R` existed. It fixes the statistic (Moran's I of
`mpi`, and of the residuals of `mpi ~ lat`), the weights (queen contiguity on the
raw ADM1 file, row-standardised), the permutation count and seed, the correction
(Bonferroni across 37 local tests) and the decision rule, together with the
sensitivity set and the reader-facing wording.

Two things it pre-declares that bear on everything else in this ledger: the raw
global statistic is expected to be dominated by the north–south gradient already
documented in A2, so **the report leads with the latitude-controlled value**; and
no per-state hotspot claim is permitted, because A1 withdrew orderings.
Exploratory computation preceded the registration and is disclosed inside it —
it is a specification freeze, not a blind test.

Built as `scripts/spatial_diagnostics.R` (statistics, sf/spdep/spatialreg) driven by
`scripts/09_spatial_diagnostics.py`, which recomputes the neighbours, the lag, the four
types and Moran's I in Python and fails if the two implementations disagree. Result,
wording and every sensitivity: `docs/spatial_analysis.md` §3.

**One amendment, recorded in the registration rather than folded into it
(`Amendment 1`, 2026-10-18):** a second worksheet — the cluster map `Where poverty
clusters`, immediately after the poverty map — was added at the user's request *after*
the result was seen. The test, the decision rule and the frozen wording are unchanged.
Two things the amendment pins down, because they are consequences of the result rather
than a revision of it: the map colours all 37 states by **neighbourhood type and never
by significance** (one state survives Bonferroni, none survives Benjamini–Yekutieli, so
a significance map would be a single state and would re-import the per-state ordering A1
withdrew), and its four colours encode only the quadrant — which side of the national
average the state is on, and whether its neighbours are on that same side — and never
the poverty ramp. The count is stated in the hover and beside the sheet, not coloured.

**Amendment 2, same date:** the Moran scatter (`Each state against its neighbours`,
sheet 2 until then) is **no longer published as a worksheet**. The registration fixed
the statistical test, the correction and the wording; it did not fix a rendering, and
the user's instruction was to keep two sheets. The amendment is recorded inside
`docs/spatial_preregistration.md` and changes nothing about the decision rule: the
values, the p-values, the corrections and the four frozen reader lines are unchanged
and are still computed by stage 9, still carried in the hover of the surviving map,
and still written out in full in `docs/spatial_analysis.md` §3. What is gone is one
way of drawing them.

---

## G. Withdrawals — 2026-10-18

Not defects either. Recorded because both were decisions about *what the workbook is*,
both were taken on the user's instruction, and both are the reason a reader of an
older note will not find the sheet it names.

### W1. Five chart sheets, the Moran scatter, the "Equity Atlas" dashboard and the HTML map
**Severity n/a — withdrawn · status done**

The workbook carries **two maps and three reference tabs**. Gone, with the user's
instruction ("I only care about MPI bands we built and the [spatial] sheet"):
`Dimension breakdown`, `Poverty vs conflict`, `Poverty over time`,
`Incidence vs intensity`, `Party alignment and MPI change`, the Moran scatter, the
`Equity Atlas` dashboard, and `scripts/07_build_interactive_map.py` with the
`docs/preview/interactive_map.html` it wrote. Recoverable from git; the last commit
that carries them is the parent of this change.

No claim was lost. Every sentence a reader needed from those sheets is a row of the
reference tabs: the four defects D1–D5 that made three of them wrong are moot rather
than fixed, and the analyses behind the other two still run. Stage 2 (conflict), stage
3 (climate) and stage 8 (the pre-registered party test) still execute in
`scripts/run_all.ps1` and still write their outputs — the party result is quoted in
`docs/party_alignment.md`, which is where a claim that fragile belongs.

The pipeline lost a stage and gained nothing: `07_build_interactive_map.py` is deleted
and `run_all.ps1` runs nine stages. The two reader prose dashboards
(`What the words mean`, `How we did it`) were merged into the reference table below.

### W2. The reference table ships as three tabbed parts, not one dashboard
**Severity n/a — split · status done**

The merged table (one row per word, need and worked step; three columns) was built as
a single dashboard and **measured 2000 x 8720 px** when the workbook was opened in
Tableau Public 2026.2 on 2026-10-18 and looked at. The window it was reviewed in is
687 px tall, so that tab was thirteen screens: not a tab anyone reads top to bottom,
and the user's instruction was to split it if it was too big.

It is now parts 1–3 of one table, cut on the groups the table already had — the words
(24 rows, 2000 x 4406), the list of basic needs (11 rows, 2000 x 1821), the method
(9 rows, 2000 x 2858). Each part repeats the intro and the column headers, because
each tab has to stand alone for a reader who arrives on it from the tab bar. The
columns do not change between parts and no row was re-cut: this is pagination, not a
return to the two prose pages the merge replaced.

Two things were learned in the render that fixed a real defect rather than a size
one, and both are recorded where they belong in the code:

- **The height model was one line short.** `_estimate_height` counted the text and not
  the zone's own vertical margin, so every row that wrapped was ellipsized by Tableau
  — which truncates the last line instead of growing the zone. The width model was
  already right (a 480 px cell held 41 characters, a 760 px cell 68, exactly as
  predicted), so the fix was to make the padding part of the estimate. Before the fix,
  the first row of the table read "a household is poor at 33.3% or more of t…".
- **A literal `\n` in the XML is a load failure with no useful log line.** A Python
  escape that reached the file instead of being interpreted is still well-formed XML,
  so the parser accepts it and Tableau's only complaint is `D2E8DA72`, "the load was
  not able to complete successfully", with nothing naming the element. `validate()`
  now fails the build on a literal `\n`, `\t` or `\u` in the XML text.

## H. The "A state over time" build - 2026-10-20

Render findings from building the sixth view (design freeze in
`docs/SHEET_TIME_PANEL.md`, grammar copied from real workbooks fetched via the
`tableau` MCP server). These are the render-test lessons beyond what that doc
records; every one was observed in Tableau Public 2026.2, not inferred.

- **T1. A dimension on detail splits a Line mark into one-point lines**
  **Severity DEFECT - fixed during build, status done.** The first render drew
  six panes x four rounds of isolated dots with no connecting lines, because
  `survey` and `mpi_change_significant` (string dimensions) were on `<lod>`
  fields: per-round values differ (DHS -> MICS, blank -> **), so each mark was
  its own line. Marked measures (`mpi_change_since_prev`,
  `fatalities_per_100k_high`) cannot split a line, but there was no way to keep
  the string annotations off the mark's identity at all - so the `<lod>` list
  went entirely and the annotations moved into the customized tooltip. The fix
  is verified in the render: all four rounds connect in all six panes.
- **T2. Left-edge cards draw; right-edge cards do not**
  **Severity DEFECT (open W-singleton class) - reproduced, status documented.**
  The state dropdown (`mode='dropdown' param='[ds].[none:state:nk]'`) is copied
  byte-equivalent from HRAnalytics and did not render on a right strip - the
  first time the map colour legend's "declared but not drawn" defect (section B)
  has been reproduced with a second card type, ruling out the colour-card
  grammar specifically. The time panel's two interactive cards therefore
  declare on the LEFT strip (above `<card type='marks' />`), where both render.
  Whether the maps' colour legends can take the same left-strip treatment is
  untested; it is the obvious next experiment for that open defect.
- **T3. `<card type='title' />` is required for a worksheet title**
  **Severity IMPROVEMENT - fixed during build, status done.** Without the title
  strip on the top edge the sheet's title and frozen two-line subtitle never
  render. Added (`strip size='31'`), and the subtitle draws in full.
- **T4. Hyper-extract system fields leak into the Measure Names domain**
  **Severity IMPROVEMENT (accepted wart) - status todo, documented.**
  "Migrated Data (Count)" and "Latitude/Longitude (generated)" are added by
  Tableau to every Hyper extract (the two map extracts carry them too) and
  cannot be deleted. The union filter excludes them and they draw unchecked;
  a determined reader can still tick "Count of Migrated Data" and get a
  nonsense line. A Measure-Names allowlist via a Tableau set is the future
  guard; not attempted in v1. One repro of the measure checklist widening after
  a mark selection was observed mid-session; if it reproduces on the published
  viz, drop the `param` filter cards and rely on the standard Filters shelf
  card. Listed in `docs/PUBLISH.md` checks.

## H2. The rank amendment - 2026-10-21

The user amended the freeze: ranks replace the values on the marks, and the
sheet carries **rank variables only** (full record in
`docs/SHEET_TIME_PANEL.md`, section "Built, 2026-10-21"). The render-test
findings beyond what that doc records:

- **T5. A sheet-level `attr='number-format'` rule does not exist in the 2026.2
  schema**
  **Severity DEFECT (build-time) - fixed by finding the real serialisation,
  status done.** Both field-scoped and mark-scoped
  `<style-rule><format attr='number-format' .../></style-rule>` fail the whole
  workbook load with the modal "Unable to complete action", error code
  `D2E8DA72`, full text `Error(549,65): value 'number-format' not in
  enumeration` (read via the modal's Copy Error Message button - the un-assumed
  step that ended the bisect). The `<format>` attr enum, dumped from
  `tabfileformat.dll`'s data tables, has ~140 values and does not contain
  `number-format` at all, so no placement of the old form can work. The real
  serialisation is **`default-format='"R"0'` on the `<column>` element** - found
  in the same enum dump (`column` attributes include `decimals` and
  `default-format`), confirmed by a load test, and shipped in
  `col_block(number_format=...)`. With it the workbook loads and the integer
  marks print bare integers (the pre-amendment "36.00"-style two-decimal dust
  gone); the quoted-literal "R" prefix itself does not render, so the R-wording
  stays in the caption/subtitle prose.
- **T6. An integer measure declared `type='ordinal'` falls out of the Measure
  Names domain**
  **Severity DEFECT - fixed during build, status done.** With the rank columns
  `datatype='integer'` and the datatype->type zip giving them `type='ordinal'`,
  the union filter's `[sum:rank_X:qk]` members and the palette buckets did not
  match the fields' domain keys. Symptom cluster, all from one load: the
  Measure Names checklist showed the datasource's raw field names
  (`events_per_100k`, `mpi`, ...) rather than the member captions, exactly one
  arbitrary tick, the state filter slid to a random member ("Ekiti"), the
  palette fell back to Tableau's default categoricals, and Tableau's generated
  "Count of Migrated Data" drew as a drawn pane. The fix is one rule in
  `col_block`: a measure is always `type='quantitative'` whatever its datatype.
  Verified fixed: stored members bind (six ticked; "(All)" and "Count of
  Migrated Data" unticked), the six assigned colours draw, Bauchi stays pinned.
  The two first observations of the symptom pair (one capture looked
  bound-but-captioned) were transient load states of the same broken key
  resolution; the col_block fix made the load deterministic.
- **T7. The Measure Names domain = the datasource's measures**
  **Severity IMPROVEMENT - acted on, status done.** Everything the extract
  declares as a measure is a candidate member of the domain, so hover fields
  that were numeric measures (`mpi_change_since_prev`,
  `fatalities_per_100k_high`) appeared in the measure checklist even though
  they were never on a shelf. The amendment removes them as measures: stage 04
  pre-formats the annotations into string columns (`mpi_change_label`,
  `deaths_high_label`, TEXT in the extract), the tooltip prints the strings,
  and the domain shows the six ranks and the system leaks, nothing else. The
  red-list assert grew the same fields so the removal cannot silently revert.

## P. The parameters probes - 2026-10-21

Six packets against Tableau Public 2026.2 (tabpublic.exe, load-and-look),
settling every open grammar question for the "How measures pair" sheet
(`docs/SHEET_PAIRS.md`). Workbooks under `C:\Users\TOSHIBA\AppData\Local\Temp\opencode\packetA*.twbx`,
builders `packet_builder.py` / `build_packetA3.py` / `build_packetA5.py` alongside.

- **P1. Parameters are an inline pseudo-datasource, packed and proven**
  There is no `<parameter>` element in the 2026.2 schema. The shipped shape is
  `<datasource hasconnection='false' inline='true' name='Parameters'
  version='18.1'>` whose `<column>` children carry `param-domain-type='list'`,
  a `<calculation class='tableau' formula='"default"'>` child and a
  `<members>` child (one `<member value='"..."' />` per menu entry). Packet A1:
  added to the workbook-level `<datasources>` block, unused, loads clean.
- **P2. The card renders even with the parameter unused**
  `<card mode='compact' param='[Parameters].[Parameter 1]' type='parameter' />`
  inside the window's left-edge `<strip>` draws the dropdown at load. Packet A2.
- **P3. The table content model is exact: view, style, panes, rows, cols**
  Packet A3's first load died with `D2E8DA72`: `detail` is not an encoding
  element (the allowed set is
  `(color|size|text|shape|wedge-size|lod|geometry|image|tooltip|path|level|edge|custom)`;
  Detail-card state = `<lod>`), and `<cols>` must come **after** `<rows>` in a
  `<table>`. Corrected once; the sheet then loads and draws.
- **P4. The sheet-level deps block binds the parameter's current value**
  Packet A4 first shipped the MPI default in the Parameters datasource only and
  still computed H (status bar SUM = 4931.34). With the same default mirrored
  into the worksheet's `<datasource-dependencies datasource='Parameters'>`
  column (`value=` / formula), the payload switched to MPI and the status bar
  read exactly 25.9903 = **sum of mpi over the 148 marks**. Deterministic
  proof that `CASE [Parameters].[Parameter n] WHEN ... THEN [col] END`
  calc columns resolve from the bound value. Rule for the builder: every
  parameter column carries the same `value=` at both places.
- **P5. The pane split is a paren-plus rows shelf**
  `<rows>([ds].[none:poverty_group:nk] + [ds].[avg:pair_y:qk])</rows>` stacks
  the two poverty-group panes, each with its own y scale, row headers rendered
  ("Other 25", "Poorest 12"), 148 marks held by `<lod>` Detail on state +
  survey_year. Packet A5, with the group stamped onto all 148 panel rows.
- **P6. log1p as an extract column drives the payload**
  Packet A6 defaulted X to the extracted `log1p_events` column
  (log(1+events_per_100k), zeros = exactly 0). Payload resolved from the
  extract column, zero-event states on the 0 gridline; no LOG() needed in the
  CASE. Stage 04 will therefore ship `log1p_*` columns and the menu maps them.
- **P7 (open finding). The map's colour legend rendered in these packets**
  The "Where poverty sits" colour legend - declared in the shipped workbook and
  documented as never drawing (see §B defect list) - **draws** in packets A5/A6,
  whose only structural additions are the Parameters datasource, the pairs
  datasource, the seventh worksheet and `Data/pairs_probe.hyper`. Cause not yet
  isolated. To be checked on the first real build that carries the same
  additions; if the legend draws there, the defect closes as an incidental fix
  and §B is amended.
- **P8 (unverified). Titles binding parameters**
  The A5/A6 title run used
  `<run><![CDATA[<[Parameters].[Parameter 1]>]]></run>` but the capture never
  showed the title area, so whether worksheet titles render a parameter value
  is unresolved. Verify at build time before finalising title text.

- **D-051 (2026-10-22). Mark-label colour: the datalabel rule is the grammar**
  The composition sheet asked for white segment numbers. Six packets, one
  variable each: worksheet-level plain `element='label'` colours EVERY label
  (row headers went white-on-white, render_dim2); field-scoped on Measure
  Values inert at worksheet level (dim3) and pane level (dim4); pane-level
  plain `element='label'` inert (dim5); emitting a style-rule outside the
  pane's `<style>` block fails the whole open ("Unable to complete action").
  Landed: pane-level `<style-rule element='datalabel'>` with
  `color-mode='user'`, `color`, `font-weight='bold'`, copied byte-shape from
  Try-UmphantStartGallagherPremOpeningWeekend.twbx, before the mark rule,
  inside `<pane><style>`. Renders bold white on all three fills, headers
  ink (render_dim6/7). Generator: `worksheet_xml(label_colour=...)`; scoped
  to the composition sheet via generated XML check (1 occurrence).
- **D-052 (2026-10-22). The composition sheet defaults to 17 of 37 bars**
  User request: "show five states in poorest and 12 in other, give me the
  option of adding more states". Default ticks ranks 1-5 and 13-24 of the
  manual MPI order (five poorest, then the first twelve of the Other 25);
  all 37 on a left-rail `state` checklist card — the time panel's proven
  card shape with a multi-member `union user:op='manual'` categorical
  filter (the Measure Names filter's own shape) on `state`. Manual bar
  order survives the filter (render_dim7). Subtitle, QA gate (17 drawn,
  full-37 asserts) and checklist ticks all describe the same default.
- **D-053 (2026-10-22). The group divider: nested rows render the boundary**
  User: "no extra button to add states, and a clear axis marker between poor
  states and others". The button was there (packets proved it draws — byte-
  identical window XML, review_tab copies verbatim) but it needed to be more
  obvious, so the subtitle now names the control and the card renders `(All)`.
  Marker: Rows now nest `poverty_group` above `state` (the pairs board's
  paren-plus shelf shape, P5), plus a manual sort on the group so "Poorest 12"
  precedes "Other 25" (a plain string-bucket dictionary, the proven sort
  grammar). The sheet prints two blocks with a pane divider, MPI order inside
  each; default ticks unchanged (render_dim8/9). Cosmetic leftovers recorded
  in docs/SHEET_DIMENSIONS.md: header caption truncation and the "Poorest 12"
  line-wrap (the header-width rule value='92' did not take here).
  Full workbook still loads (title Nigeria-MPI-Equity-Atlas).
- **D-054 (2026-10-22). The pairs board's circles: mark-color is the grammar, and `<style />` is load-required**
  User request: green circles, state-name-only hover. Six colour shapes,
  one variable per packet, all render-verified (green1..markcolor2):
  pane-level plain `<format attr='color'>` inert (loaded, stayed blue);
  pane-level `<encoding>` palette map with the colour pill present loaded but
  the pill's default categorical palette won through (blue + one stray
  orange dot); table-level `<encoding>` rule (ds-qualified, then unqualified,
  the real-workbook form) inert the same way; a **ds-level palette** on the
  pairs datasource (`palette=` on `datasource_xml`, the placement the map
  sheets render from) **failed the load outright** - grey empty shell, packet
  and full workbook, no dialog; pane-level `<format attr='mark-color'>` -
  FinanceDashboard's 52-hit shape, scope verified - appeared to fail the load
  too. Bracketing the failing build against the pre-session one (twb diff)
  found the actual breaker: **deleting `<table>`'s `<style>` element fails
  the load even with no rules in it** - the element is required present, and
  every earlier "mark-color failed" call was that deletion, not the format.
  With `<style />` restored, pane `mark-color` renders the green on both
  panes (render_pairs_markcolor2), no stray dot, and the full workbook loads
  (render_full_green_ok). Landed config: no colour pill, pane rule =
  `mark-color` + `mark-labels-show`. Generator: `pairs_worksheet_xml()`.
  Hover reduced to the bold state run (caveat wording stays in the subtitle;
  `atlas_text.PAIRS_TOOLTIP_CAVEAT` withdrawn). Stage 5 gained
  `8_how_measures_pair.png` (the gate's first scatter view; pairs is tab 8).
  Open finding, not a defect: a fresh open sometimes carries non-default
  parameter-card selections and the payload follows the cards
  (docs/SHEET_PAIRS.md Built).

## K. The KPI board's session - 2026-10-23

### K1. Tableau's own autosave state poisoned whole mornings of loads
**Severity DEFECT - status done (workaround documented)**
Every force-kill of tabpub lands a `.twbr` autosave NEXT TO the source workbook
(`tableau/~Nigeria-MPI-Equity-Atlas__<pid>.twbr`), indexed in
`HKCU\Software\Tableau\Tableau Public 2026.2\Autosave File Map`, and every later
open trips through File Recovery / Extract-Not-Found restore chains
(`Data/Data/<extract>.hyper` double-path errors - the restore copy, not the
file). Purge recipe, verified: kill tabpub, delete any `*.twbr` beside the
.twbx, delete the `Autosave File Map` registry values, delete
`%TEMP%\TableauTemp\`. After the purge, bare launch is clean and the twbx opens
normally. UIA helpers live in `%TEMP%\opencode\` (`dump_uia.ps1`,
`dismiss_chain.ps1`, `clear_recovery2.ps1`); `My Tableau Repository\Logs` is
stale - read the dialogs, not the log.
**Open the twbx via `Invoke-Item` (the double-click association route).** A
direct `tabpublic.exe <path>` argument launch opens an empty `Book2` on this
combo (twbx contents unaffected - association route loads them, same minute,
same file). Commands that bypass the association must go through it.

### K2. `default-format` on the <column> does not reach mark LABELS here
**Severity DEFECT - status done (data-side lane shipped)**
The ds-level `<column … default-format='0.0'>` was landed for `pos` in both
copies (worksheet deps + datasource), the same lane the rank panel's
`'"R"0'` lane documents. Labels still printed Tableau's General 4-decimal
(0.3367) every time; the lane never worked for labels on these
federated-extract sheets (the rank panel's bare-integer look needs no
formatting - integers print bare under General too, so it never failed
visibly). The shipped fix is data-side: stage 7 writes `pos_label`
(`0.3`) and the sheet puts that string on the Label pill (`<text column=…>`,
CH24 Shape/Legend byte-shape). The `default-format` stays for the axis.
Number formats WOULD be needed for any aggregate on Label - avoid his lane.

### K3. Colour-card tint eats a shape's RGB; contrast must ride alpha
**Severity IMPROVEMENT turned DESIGN FACT - status done**
With `series` on Colour + a ds-level palette, the Shape marks render as the
SERIES colour keyed by the PNG's alpha - interior RGB detail (white
coastlines/graticule on the purple disc) silently fuses into the disc
(verified in-app: flat violet circle while the same PNG shows its lines in
the QA gate). Anything a shape must show besides its silhouette therefore
encodes as alpha: the world globe draws the disc at full alpha and the
longitude lines + coastlines at reduced alpha (~55% / 75%), so the tint
paints them lighter. Stage 7 `_draw_globe` carries the model and rationale."

### K4. Session-restore hijacks the second launch
**Severity IMPROVEMENT - status observed**
Tab_Public sometimes splits off a second bare-shell process on `Invoke-Item`,
whose own session-restore shows the Extract-Not-Found dialog for the atlas'
extracts. Kill that shell (no workbook open, no autosave at risk), keep the
window titled `… - Nigeria-MPI-Equity-Atlas`.

---

## L. The trend-line session (2026-10-24)

Everything here was paid for once so it is not paid for again. L1 is the one
that changes how grammar is sourced; L2-L6 are why the GUI could not be driven.

### L1. A trend line cannot be packet-sourced; Tableau publishes the schema
**Severity IMPROVEMENT turned METHOD - status done**
There is **no public `.twb` that serialises a `<trendline>`**. GitHub code
search: `polyDegree extension:twb` -> 0 hits; the two `"trend-line"` `.twb`
results only mention it in title text. `.twbr` autosaves written beside the
workbook are plain workbook XML (`build 20262.26.0912.1023`) with **zero**
`<trend` tags -- they are not a serialiser either.

The grammar came instead from **Tableau's own published schema**:
`github.com/tableau/tableau-document-schemas`, `schemas/2026_1/twb_2026.1.0.xsd`
and `schemas/2026_2/twb_2026.2.0.xsd` (use 2026.2 -- it matches the installed
Public build `20262.26.0528.2205`). Group `PaneSpecification-Trendline-G` gives
the element and its required attributes; `TrendLineFitType-ST` gives the fit
vocabulary (`linear | polynomial | log | exp | power`); `StyleElement-ST` /
`StyleAttribute-ST` give `element='trendline'` with `stroke-color` /
`stroke-size`. The group's **position in `PaneSpecification-G` is fixed**: after
hidden-fields/drop-line, before `reference-line*` and `customized-tooltip`.

To validate a workbook against it, the two `xs:import`s have to be stubbed
locally (`http://www.tableausoftware.com/xml/user` -> `UserAttributes-AG` with
`<xs:anyAttribute/>`, and `http://www.w3.org/XML/1998/namespace` -> the
`base`/`lang`/`space`/`id` attribute declarations), otherwise libxml2 fails on
the FIRST unresolved QName and never reaches the document. Recipe:
`C:\Users\TOSHIBA\AppData\Local\Temp\opencode\twb_2026.2.0.local.xsd` +
`user_stub.xsd` + `xml_stub.xsd`, then `lxml.etree.XMLSchema(...).validate(...)`.
The atlas validates with **0 errors mentioning `trendline`**; the 30 others are
the known tolerated deviations (`extract/@object-id` missing,
`layout/@dim-percentage` + `@measure-percentage`, the `simple-id` elements this
schema *requires* but Tableau's own loader rejects with `D2E8DA72`, and one
`sort` ordering).

### L2. The Trend Lines dialog is invisible to UIA
**Severity IMPROVEMENT - status known**
`Trend Lines Options` is a Qt window (`Qt6511QWindow`). `EnumWindows` sees it,
UIA does not: the process' root children list only `TMainWindow`, so no
checkbox can be ticked by name. It must be driven by pixels, which is fine
until L4.

### L3. `Show Trend Lines` is a TOGGLE, and `Edit` is disabled while it is off
**Severity DEFECT in any automation - status known**
Invoking `Analysis > Trend Lines > Show Trend Lines` when a line is already on
turns it OFF, and `Edit All Trend Lines...` then reports `IsEnabled=False` and
swallows the invoke silently (no error, no dialog). Deterministic order: read
`Edit`'s enabled state FIRST; if enabled, invoke it; else invoke `Show`, wait,
re-open the menu, then invoke `Edit`.

### L4. A locked screen silently swallows every synthetic click
**Severity DEFECT in any automation - status known**
While the workstation is locked, `GetForegroundWindow` returns the lock screen,
every `WindowFromPoint` returns `LockScreenBackstopFrame`, and `OpenInputDesktop`
is `False`: clicks land nowhere and captured windows are stale. After unlock,
coordinates map **1:1 (k ~= 0.985-1.0)**. An earlier session's "divide by 1.4764"
DPI correction was **wrong** and made good clicks miss; do not reintroduce a
constant scale factor -- measure it (UIA `BoundingRectangle.Width` /
`GetWindowRect` width) or use k = 1.

### L5. The harness console owns the foreground between shell calls
**Severity IMPROVEMENT - status known**
In this environment the console window (`VirtualConsoleClass`) takes the
foreground back after each `shell` invocation. From a child process
`SetForegroundWindow` + `AttachThreadInput` still returns `False`, so:
**keyboard input (e.g. `Alt+A`) is eaten by the console**, while **UIA-driven
mouse clicks on Tableau do work** (they only need the coordinates to be right).
Two corollaries:

- Drive menus by **UIA rect + mouse click** (`uia_click_path.ps1`), never by
  mnemonics.
- A **narrow window collapses Tableau's menu bar to `File | Help`**, which is
  what a `MISS: Window menu` actually means -- resize/maximise first, then look
  for the menu.

### L6. A workbook opens on the sheet it last showed, not the first `<window>`
**Severity IMPROVEMENT - status done**
Reordering `<windows>` puts a sheet first in the file but not on screen:
Tableau restored the last-viewed sheet for that path. To force a sheet for a
render check, **prune the probe to that one worksheet and window**
(`C:\Users\TOSHIBA\AppData\Local\Temp\opencode\probe_only.py`: lxml, remove
every other `<worksheet>` and `<window>`, rezip as `probe.twbx`).
`tableau/*.twb` is never touched by a probe.

### L7. `element='trendline'` + `stroke-color` is live (the white test)
**Severity IMPROVEMENT turned DESIGN FACT - status done**
A pane-level `<style-rule element='trendline'>` with
`<format attr='stroke-color' .../>` and `stroke-size` paints the fitted line and
its band edges. Proven by contrast, not by eye: built white (`#FFFFFF`) the line
and both band edges disappear while every mark and gridline stays; repainted
`#4D4D4D` at the same geometry they return, thicker. So **white on this sheet's
white pane is invisible** and the shipped colour is the dark ink
(`atlas_text.PAIRS_TREND_COLOUR`). `docs/SHEET_PAIRS.md` "Trend line" is the
build record.
