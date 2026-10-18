# Pre-registration: do poor states sit next to poor states?

**Committed before any analysis code.** This file and its `docs/FIX_LEDGER.md`
entry are the only changes in their commit — no `.py`, no `.R`, no data. The
analysis stage (`scripts/09_spatial_diagnostics.py`, `scripts/spatial_diagnostics.R`)
is written in a later commit, so `git log` dates the specification before the code.
This follows the same rule the party question followed (`152c13d`).

Status: **frozen 2026-10-18**.

---

## Disclosure: this is a specification freeze, not a blind test

Read-only exploratory computation on 2026-10-18 preceded this file. Nothing was
written to the repository, but the values below were seen. They are disclosed in
full so the registration cannot be read as more than it is.

| Seen during exploration | Value |
|---|---|
| Moran's I of `mpi`, queen contiguity, row-standardised | 0.798 (analytic p 7e-15; permutation floor) |
| Moran's I of `lat` itself | 0.860 |
| Latitude alone, R² | 0.775 |
| Moran's I of the residuals of `mpi ~ lat` | 0.244, p 0.005 |
| Same, after `lat + conflict + climate` | 0.108, p 0.099 |
| Local statistics with raw p < 0.05 | 16 of 37 |
| Local statistics surviving Bonferroni | 1 (Yobe) |
| Queen vs rook neighbour graph | identical |
| Spatial-error vs OLS AIC | −90.7 vs −87.7 |

**What freezing still buys, and it is real:** the statistic, the weights, the
correction and the decision rule cannot now be chosen to suit the result. A
reader cannot ask "would another W matrix have given a nicer answer?" and get a
post-hoc yes.

---

## Hypotheses

**H1 (global).** Moran's I of `mpi` under queen contiguity is greater than 0.
Decision: permutation p < 0.05. *Reported for completeness only. This will
succeed and is not the claim of interest — a smooth north–south gradient
guarantees it.*

**H2 (primary).** Moran's I of the residuals of `mpi ~ lat` is greater than 0.
Decision: permutation p < 0.05. *This is the only version that is not already the
north–south gradient the atlas documents in `docs/FIX_LEDGER.md` A2.*

**H3 (local, secondary).** At least one of the 37 local Moran statistics survives
a Bonferroni correction across 37 tests. Decision: raw p < 0.05/37. Report the
count and the names; **make no claim about a flagged state beyond the count.**

## Specification

- **Weights.** Queen contiguity built from the **raw** `data/raw/nga_adm1.geojson`,
  not from the simplified `data/processed/mpi_polygons.csv` (simplification can
  move a shared corner). Row-standardised. Assertions before any statistic:
  37 units, exactly one connected component, zero units with no neighbour.
- **Latitude.** `lat`, the capital's latitude, already carried in
  `data/processed/mpi_atlas_2021.csv`. No new geocoding.
- **Permutations.** 9,999, `set.seed(20261018)`, recorded in the output. The
  permutation p floors at 1/(nsim+1) = 1e-4; quote the floor, never the analytic
  7e-15, as the permutation value.
- **Multiplicity.** Bonferroni primary. Benjamini–Yekutieli as a sensitivity
  (valid under the dependence spatial statistics induce).
- **No decision is taken on any sensitivity analysis.**

## Pre-declared sensitivities (reported, never decisive)

Rook contiguity; k = 4 nearest-neighbour weights; FCT excluded; residual I after
`lat + conflict + climate`; AIC of spatial-error against OLS.

## Reader-facing wording (frozen)

Frozen because wording written after a result is wording chosen to flatter it.
The sheet and the methodology section carry these words, edited only for line
breaks. Everyday words first; the technical name in brackets after, if at all
(`scripts/atlas_text.py` rule).

**Sheet title** — `Do poor states sit next to poor states?`

**The four lines the sheet carries, in order:**

1. "Yes. States with similar poverty scores do tend to share a border."
2. "But most of that is simply that the north is poorer than the south. How far
   north a state sits explains about three quarters of what looks like
   neighbouring states resembling each other."
3. "Think of a height map. Two neighbours are usually at similar heights because
   the land slopes steadily — not because one hill lifts the next. Take the slope
   out, and only a little resemblance between neighbours is left."
4. "Only 1 of the 37 states stands out on its own, once we allow for having
   looked at 37 states at once."

**Technical line** (small, under the four, the "technical details" pattern the
party panel already uses):

> Moran's I of the poverty score 0.798 (p ≤ 0.0001, 9,999 shuffles). After
> accounting for how far north a state is, 0.244 (p = 0.005). After latitude,
> conflict and climate together, 0.108 (p = 0.099). 16 of 37 states look local
> on their own; 1 (Yobe) still does after correcting for testing all 37 at once.

**Axis titles** (plain, no column names): the vertical axis is "This state's
poverty score (MPI, % of index)"; the horizontal axis is "Average poverty score
of the states it borders (MPI, % of index)".

**The four quadrant labels**, in words rather than letters: "high, beside high";
"high, beside low"; "low, beside high"; "low, beside low".

**Glossary entries** added to `scripts/atlas_text.py`, so the sheet's words are
defined where every other atlas word is: *neighbouring states*, *clustering*,
*explained by how far north a state is*.

**Methodology section** — "9. Do poor states sit next to poor states?", written
in the same voice as section 6 (the climate layer), including its "overlap does
not show that weather causes poverty" construction.

## Limits (pre-declared)

- **No causal or spillover reading.** A spatial coefficient is not "poverty
  spreads to the next state". `docs/CAUSAL_DECISION.md` governs.
- **No named worst cluster, no ranked hotspot.** Orderings are unresolvable: 0 of
  36 adjacent rank pairs separate at 95% (`docs/FIX_LEDGER.md` A1).
- **No "north vs south".** All 12 states with MPI > 0.20 lie in the two northern
  latitude bands, so "poorest states vs the rest" is the same observations.
- **Low power at n = 37.** A failure of H2 would not be evidence of independence;
  the design's power floor is |rho| ≈ 0.4.
- **State aggregates only.** The pipeline holds no local-government-area poverty
  data, so nothing here is about within-state or household variation; contiguity
  weights also treat states of very different size and population as equal units.
- **Adjacency is a model choice, not a measurement.** Neighbours sharing a border
  is not evidence they interact. Lagos has one neighbour (Ogun), so its local
  statistic is the weakest in the set and must be read as such.

## Declared outputs

- `data/processed/spatial_diagnostics.csv` — 37 rows, one per state.
- `data/processed/spatial_global.csv` — the global statistics and provenance.
- `data/interim/spatial_weights_meta.csv` — the weight-matrix diagnostics.
- `docs/spatial_analysis.md` — the numbers above, generated.
- `docs/preview/9_spatial_diagnostic.png` — the stage-5 visual gate for the sheet.
- One new workbook worksheet, a scatter of each state's poverty score against the
  average of its neighbours', coloured by the four quadrant words above, plus a
  methodology section and glossary entries.

## Decision rule if H2 fails

If H2 returns p ≥ 0.05, the sheet ships as "no neighbour resemblance beyond the
north–south slope" with the same four-line structure adjusted to say so, and no
maps, hotspot layers or per-state highlight are drawn. The workbook is not
adjusted afterwards to make the result look stronger.

## Amendment 1 (2026-10-18): an added surface, not a changed test

**Nothing the test consists of has changed.** The statistic, the weights, the
permutation count and seed, the corrections, the decision rule, the sensitivities and
the wording of the four reading lines are exactly as frozen above, and every number in
§3 of `docs/spatial_analysis.md` comes from that test, run by the code in
`scripts/spatial_diagnostics.R` as first conceived.

What changed, and it changed **after H2 and H3 were seen**, is presentation. The
declared output was one worksheet — the scatter. A second worksheet has been added at
the user's request: the same 37 state polygons sheet 1 draws, coloured by the four
neighbourhood types. It sits immediately after the poverty map in the tab order, and
the scatter sits immediately after it. The gate PNG for the scatter is renamed
`8_spatial_scatter.png`; the map's is `7_spatial_clusters_map.png`. This amendment is
dated and appended rather than folded into the sections above, because editing a
frozen specification in place would hide exactly the thing pre-registration exists to
expose.

Two consequences follow from the result rather than from any revision of the test, and
both are deliberate:

1. **The map's colours are descriptive, never a significance map.** H3 leaves one
   state surviving Bonferroni and none surviving Benjamini–Yekutieli (§3). A map
   coloured by significance would therefore be a single state on a field of grey, and
   it would invite the reader to name that state as "the poorest cluster" — the
   per-state ordering this atlas withdrew (`docs/FIX_LEDGER.md` A1). The count is
   stated instead: in the hovering text, in §3, and in the plain-language reading
   beside both surfaces. No claim about the named state survives beyond the count,
   which is what H3 already required.
2. **The four colours encode only the quadrant.** Which side of the national average
   the state is on (hue), and whether its neighbours are on that same side (shade).
   Nothing else — no third variable, and specifically not the poverty ramp, so the
   sheet cannot be read as a second poverty map.

The added surface does not touch the decision rule above, and it was not used to
justify any change to the statistics.

## Amendment 2 (2026-10-18): the scatter is no longer published

**Nothing the test consists of has changed either.** Same statistic, same weights, same
permutation count and seed, same corrections, same decision rule, same sensitivities,
same frozen reading lines. Stage 9 still runs the test, still verifies the R result in
Python to 1e-06, and still writes every number to `docs/spatial_analysis.md` §3 and to
the four CSVs listed under *Declared outputs*.

What changed is again presentation, and — as with Amendment 1 — it changed after the
result was seen. The user's instruction on 2026-10-18 was that the workbook carry two
maps and the reference table, and no more. The scatter worksheet is therefore not
published. Of the two spatial surfaces Amendment 1 declared, one remains: the cluster
map, whose hover carries the same four frozen lines and the same technical footer it
shared with the scatter. A reader who wants the numbers themselves has §3; a reader who
wants the comparison drawn has the neighbourhood types on the map. What is gone is one
way of drawing them.

Two knock-on effects, recorded because the paragraphs above name things that no longer
exist:

- The stage-5 visual gate for the scatter is deleted with the sheet. A gate for a sheet
  the workbook does not contain cannot gate anything. The cluster map's gate survives
  and is renamed by tab order: it is `docs/preview/2_where_poverty_clusters.png`, not
  the `7_spatial_clusters_map.png` Amendment 1 named, because previews are now numbered
  in tab order and the withdrawn sheets' previews are gone. The rename changes no
  content: it is the same rings, the same four colours from `atlas_text.SPATIAL_QUADRANTS`
  and the same reading.
- The words in the four lines, the legend caption and the type labels are unchanged.
  `atlas_text.SPATIAL_QUADRANTS` still names the four types and assigns the four
  colours, and stage 6 still writes that palette into the workbook, so the frozen
  wording is carried by the surviving surface exactly as registered.

The withdrawal does not touch the decision rule above, and it was not used to justify
any change to the statistics.
