# FINAL PATH — the decided route, and why

Written 2026-10-06, after the decision work and after opening the workbook in
Tableau Public and looking at it. This is the routing sheet: what was decided, on
what evidence, what it cost, and what is deliberately left undone.

Supporting documents:
`docs/CLAIMS.md` (permission table) · `docs/CAUSAL_DECISION.md` (why no causal
claim) · `docs/FIX_LEDGER.md` (defect list) · `docs/SESSION_HANDOFF.md` (state)

---

## 1. The decisions

### D1 — MPI series: **keep it. It was already harmonised.**

The open question was whether the four rounds were the *standardised* series, which
OPHI says "may not be comparable across time", or the *harmonised* one, which is
comparable. The HDX resource description for the file we download says
"standardised".

**It is wrong. The file is harmonised.** Verified numerically, not by reading labels:
the 148 admin-1 rows match OPHI Data Table 6.4 to a max absolute difference of
**4.99e-05** — i.e. 4-decimal rounding — and the four national rows match Table 6.1.

This inverts the decision. The recommendation had been to drop the word "fell". That
is no longer necessary, because OPHI harmonised the series and permits strict
comparison.

**What we gained by checking Table 6 anyway:** 111 state-period change rows with
annualised change, t-statistics and significance stars. **41 of 111 are
statistically significant.** That is now in the panel
(`mpi_change_since_prev`, `mpi_change_significant`) and on the dashboard.

**What must change in prose:** earlier publications of Nigerian state MPI for
2013–2018 used un-harmonised estimates and differ by up to 0.17. Any figure a reader
remembers from an older OPHI release is a *different index*. Say so in the viz.

### D2 — Climate layer: **replace the claim, keep the data.**

Baseline precipitation ↔ MPI is −0.80, which looks like a finding. But
precipitation ↔ latitude is **−0.903** and latitude ↔ MPI is **+0.821** — latitude
predicts MPI *better* than precipitation does. The predictor is the outcome's twin.

Burke, Hsiang & Miguel (2015) survey the literature: baseline rainfall has no
cross-sectional relationship with income. The identified work uses panels and
instruments. Dell, Jones & Olken (2009) show cross-sections overstate precisely
because the unobserved heterogeneity is correlated with the predictor — and here that
heterogeneity *is* the north–south development gradient.

**Decision:** the preview panel now plots MPI against **latitude** and says why. The
conflict layer keeps its data and loses its claim. Cost: one of the spec's five
visuals is now a gradient chart. Worth it — the alternative was shipping rho = −0.80
as a climate finding.

### D3 — Conflict layer: **keep it as an honest null with the power floor attached.**

Not as "conflict and poverty are not associated". Three reasons, all measured:

- **Power.** 0.75 at rho = 0.4. Nothing survives Bonferroni.
- **Coverage failure correlated with the outcome.** In 2021 five of the poorest 12 states (Bauchi, Jigawa, Kebbi, Katsina, Kano)
  recorded zero UCDP events; the 10 zero-event states' mean MPI (0.218) exceeds the rest (0.142). The
  instrument fails hardest where the signal should be.
- **Robust to the casualty estimate, and that is worth saying.** Across UCDP's full
  low-to-high band the 2021 correlation runs +0.01 to +0.08. The null is not an
  artefact of the point estimate.

**Decision:** the scatter ships, relabelled, with the power floor and the coverage
caveat on the dashboard. It must also answer UNDP's 2024 *Poverty amid conflict*,
which asserts the opposite using the same conflict source.

### D4 — Causal framing: **none. Decomposition instead.**

Five independent closures, any one fatal — geography/poverty collinearity at n=37,
the within-poor trend reversing, null lag correlations, panel FE absorbing 91% of
variance, no instrument or discontinuity. Full reasoning in `docs/CAUSAL_DECISION.md`.

**What survives is better than what we had:** the dimension shares are an algebraic
identity, so they need no identification. The 17.6-point education-share gap between
the poorest 12 states and the rest is a *group contrast*, which is exactly what
survives a 15% relative SE.

### D5 — Ordering claims: **all withdrawn.**

OPHI publishes design-based standard errors in the file stage 1 already downloads.
Median relative SE **15.1%**. **All 36 adjacent rank pairs overlap at 95%.**
Bauchi − Jigawa = 0.0034, z = 0.08.

**Decision:** SEs wired through to the extract; map colour is a five-band
categorical, not a continuous ramp; "Bauchi has the highest MPI" is removed from every
document.

---

## 2. What the render test found

**Opening the workbook and looking at it was worth more than every schema check.**
The map sheet had never been a map. It drew **74 small lat/lon bar charts** and the
handoff recorded it as "renders". Four approaches, all now documented in
`docs/PUBLISH.md`:

| Attempt | Result |
|---|---|
| `state / SUM(lat) + SUM(lon)` | 74 bar charts — what shipped for the workbook's whole life |
| Hand-written `[Latitude (generated)]` | Red unresolved pill, blank canvas |
| Geographic role alone, no coordinates | 37 numbers as a text table |
| **`AVG(lat)`/`AVG(lon)` + `[Geographical]` semantic roles** | **Works.** Correctly georeferenced |

The shipped sheet is therefore a **georeferenced scatter, not filled polygons**, and
is titled `Where poverty sits` rather than pretending. A filled choropleth is a
one-minute GUI step, documented with the target image
(`docs/preview/1_where_poverty_sits.png` is a true filled map drawn in matplotlib
from the same rows — the geometry was never the problem, only the XML).

`Dimension breakdown` had the same class of problem: the Measure Names/Values pair
drawn from XML produced one 18,000-tall bar per state, because it also needs the
measure-values filter. It ships as three aligned panels and **says so in its title**.

**Method note for next time:** `PrintWindow` with flag `PW_RENDERFULLCONTENT` (0x2)
does capture Tableau's Qt canvas, provided the window is restored and foregrounded
first. The three prior sessions reported "cannot capture the render" — that was a
minimised window, not a capture limitation.

---

## 3. What the atlas now says

**The defensible spine, in order:**

1. **Level fell, structure held.** Rank persistence 0.867–0.924 between consecutive
   rounds; the median state moves 2–3 places. 41 of 111 state-period changes are
   significant on the harmonised series.
2. **The dimension mix differs by poverty level.** The poorest 12 states are 39.9%
   education-driven against 22.3% for the rest — a 17.6-point gap, p = 1e-5. That is
   the headline, and it points at different interventions.
3. **No state ordering is resolvable.** 15% relative SE; all 36 adjacent pairs
   overlap.
4. **No conflict association is detectable** — and the design could not have
   detected one below |rho| ≈ 0.4.
5. **The gradient is geographic.** Latitude predicts MPI better than precipitation.

**Say "poorest states" vs "the rest", never "north" vs "south."** All 12 states with
MPI > 0.20 are in the two northern bands; at n=37 they are the same observations, and
among poor states latitude does *not* predict the dimension mix (r = −0.25). That
correction is applied in `AGENTS.md` and `HANDOFF.md`, which both carried the wrong
framing.

---

## 4. Cost, stated plainly

- **Two of the spec's five visuals are not what the spec asked for.** One is a
  georeferenced scatter rather than a filled choropleth; one is three panels rather
  than a stacked bar. Both are titled honestly. Both are a GUI fix away.
- **No causal claim.** The spec never promised identification, so nothing was lost
  that was on offer.
- **The climate layer is now a gradient chart**, which is less interesting and more
  true.
- **Publishing remains manual** — File → Save to Tableau Public, behind a login. No
  write API exists.

---

## 5. Deliberately not done

| Item | Why not |
|---|---|
| Filled choropleth | Needs GUI-generated geographic fields. One minute by hand; documented with the target image |
| Stacked bar | Needs the Measure Names/Values pair *and* its filter. Five clicks by hand; documented |
| Radar chart | Polygon marks driven by computed path fields — the most fragile part of the grammar to hand-write. Same reason as the previous session |
| LGA-level conflict | `adm_2` is already populated for 88.1% of events across 445 LGAs, but the state-level count is unchanged by it and all 10 zero-event states are zero at LGA level too. A future-design asset, not a present rescue |
| ACLED | Still unobtainable, and UCDP's full fatality band already removes the sensitivity concern |
| Re-running harmonisation | Not needed — it was already the file we had |
| Aesthetics | Deliberately last. Colour palette polish and alt text are in `FIX_LEDGER.md` §C |

---

## 6. Next session, in order

1. **Publish.** Everything that can be verified has been. Open the workbook, confirm
   the five sheets and the two text zones, File → Save to Tableau Public, then verify
   the live URL with the `tableau` MCP `get_workbook_image`.
2. **Paste the attribution** into the viz description — it is already on the canvas,
   but the description is where people look.
3. **GUI fix, five minutes:** the filled choropleth and the stacked bar. Both are
   written up step by step in `docs/PUBLISH.md`.
4. **Alt text** on each sheet: descriptive, objective, no interpretation.
5. **Switch both scatters to the Color Blind palette** to pair with the Shape
   encoding already on `quadrant`.

Nothing on that list requires a decision from the reader. The decisions are all
recorded above.
