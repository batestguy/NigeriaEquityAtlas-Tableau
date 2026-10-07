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
**Severity BLOCKER · status todo**

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

---

### D8. `fatalities_per_100k` typed as string in the panel datasource
**Severity DEFECT (latent) · status todo**

`datatype='string' role='dimension'` in the panel datasource vs
`datatype='real' role='measure'` in the atlas datasource. Nothing puts it on a
shelf today, so it is latent — but it becomes a visible bug the moment anyone
adds it to a tooltip.

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

- **No rainbow colour map.** Tableau's sequential default is blue; the
  Crameri/Borland critique does not land.
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