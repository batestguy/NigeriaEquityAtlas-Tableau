# How poverty is made up — the composition sheet

Added 2026-10-22 as tab 3, between the two maps and the time panel, so the story
order is **level (maps) → composition (this) → movement (time panel) →
exploration (pairs board) → words/needs/method**. This doc is its freeze and its
built-the-way-it-actually-renders record. Single-source texts and colours live in
`scripts/atlas_text.py` (`DIMENSIONS_*`, `DIMENSION_SHARES`); the sheet's QA gate
is `docs/preview/3_how_poverty_is_made_up.png` (stage 5).

## The freeze

- **One bar per state**, split across OPHI's three dimensions, all 37 states in
  the data, grouped by `poverty_group` (Poorest 12 / Other 25).
- **The split is an identity**, not a statistic: the three shares of a state's
  own MPI sum to 100 by construction, and stage 4 asserts it per state before
  merge. The sheet can therefore never contradict the maps — recomposition and
  level agree by arithmetic.
- **Extract shape**: `dimension_shares.hyper` carries exactly the three
  `contrib_*_pct` measures plus four string dimensions (`state`,
  `poverty_group`, `dim_hover`, `mpi_label`). The MPI value is deliberately
  **not** in the extract — the bars are ordered by MPI but must not be coloured,
  sorted or labelled by it from within the sheet, so no causal or ranking
  flavour can creep in.
- **Bar order**: shipped as a byte-copied `class='manual'` sort dictionary
  hand-computed in stage 6 `main()` from the atlas MPI, with asserts. The
  subtitle says "bars listed in MPI order, which is not a ranking" and the
  caveat sentence explains why (all 36 adjacent rank pairs overlap at 95%).
- **Colours**: Education `#0072B2`, Health `#E69F00`, Living standards
  `#009E73` (Okabe-Ito), bound by measure key, declared in
  `atlas_text.DIMENSION_SHARES` and written into the workbook palette like the
  maps'. Never coloured by party; never a red/green judgement of the split.
- **Default view** (added 2026-10-22 at the user's request): the **five poorest
  states and the first twelve of the Other 25** — 17 bars — with **all 37
  states readable and tickable on an interactive left-rail `state` checklist
  card** (an `(All)` tick on top adds the rest in one tick). "First" means
  highest MPI first within each group, so the default ticks ranks 1–5 and
  ranks 13–24; the manual MPI order of the surviving bars survives the filter.
  `DIMENSIONS_SUBTITLE` states the default and where the control lives.
- **Group marker** (added 2026-10-22, the user's "clear axis marker"): Rows
  nest `poverty_group` above `state` — the same paren-plus shelf grammar the
  pairs board's pane split uses (FIX_LEDGER P5) — so the sheet prints a
  **"Poorest 12" block and an "Other 25" block with a pane divider between
  them**, each keeping MPI order (a manual sort pins the group blocks in that
  order, since alphabetical would put "Other 25" on top). Colours bind by
  measure key, so nothing else moves.

## The grammar that renders (proven, not guessed)

- The stacked bar is a **Bar mark** on Measure Names / Measure Values with a
  three-member union filter — the same generated-field grammar the time panel
  shipped first.
- **The segment numbers are bold white.** The real serialisation of the Label
  card's custom colour is a **pane-level** `<style-rule element='datalabel'>`
  with `<format attr='color-mode' value='user' />`,
  `<format attr='color' value='#FFFFFF' />` and
  `<format attr='font-weight' value='bold' />`, inside the pane's `<style>`
  before the mark rule. Copied byte-shape from
  `Try-UmphantStartGallagherPremOpeningWeekend.twbx`, which labels its marks
  white on dark fills the same way. Scoped to data labels only: row headers
  keep their ink.
- **The state checklist** is the time panel's proven interactive-card shape
  (`<card mode='checklist' param='[ds].[none:state:nk]' type='filter'
  values='database' />`) transplanted to the `state` column, with the default
  ticks as a `union user:op='manual'` categorical filter on the rows — the
  Measure Names filter's own multi-member shape, applied to `state`.
- `label_colour` is a parameter of `worksheet_xml`; every other sheet passes
  nothing and is untouched.

## Built — what the renders said, and what changed

One variable per packet, Tableau Public 2026.2, 2026-10-22.

**Stack order deviates from the freeze list.** Tableau stacks the **last
declared measure nearest the axis**, so the first render showed Living
standards | Health | Education left-to-right, not the freeze's Education-first
intent. Accepted rather than fought: the colours bind by measure key, so both
surfaces still read the same three areas; the stage-5 gate stacks **reversed
off the same single-source list** so the two cannot disagree, and the
`atlas_text` comment records the deviation. The claim discipline is untouched:
the subtitle freezes the *bar order* (MPI order, not a ranking), not the stack
order.

**The label-colour saga** (in the order attempted):
1. Worksheet-level plain `<style-rule element='label'>` + `attr='color'` —
   the GlobeMap shape — **had effect but is global**: the row headers went
   white-on-white and vanished (`render_dim2`).
2. Worksheet-level, field-scoped on `[ds].[Multiple Values]` — inert;
   headers restored, numbers stayed ink (`render_dim3`).
3. Pane-level, field-scoped — inert (`render_dim4`).
4. Pane-level plain `element='label'` (GlobeMap's exact byte position) —
   inert (`render_dim5`).
5. One detour that **failed the load** ("Unable to complete action"): the new
   rule was emitted *outside* the pane's `<style>` block — a stray
   `<style-rule>` directly under `<pane>` — which the schema will not
   statelessly repair; the placement, not the attrs, failed it.
6. **Landed**: pane-level `element='datalabel'` (`color-mode='user'`,
   `color`, `font-weight='bold'`) from the Try-Umphant workbook — numbers bold
   white on every fill, headers untouched (`render_dim6`, `render_dim7`); the
   full workbook still loads with the other four worksheets unaffected
   (`render_full_dim.png`, title `Nigeria-MPI-Equity-Atlas`).

**The default view and the group marker** are the deltas from four places:
`dim_filters` (the state union filter, 17 members, plus the group's manual
sort pinning "Poorest 12" first), `sheet_dim`'s nested rows
(`poverty_group + state`), the dim window (the checklist card, which renders
with an `(All)` tick), and the stage-5 gate (headers on their own slots, a
divider at the block boundary, the same 17 drawn, full-37 asserts before the
subset). Packets `render_dim8/9.png` prove both: the block split with its
divider, MPI order inside each block, white numbers, the checklist ticks.
Two COSMETIC nits left for the GUI pass rather than more XML cycles: the axis
strip's `Poverty group` caption truncates to `Poverty ..`, and `Poorest 12`
wraps to two lines in the group header column while `Other 25` fits — drag
the column splitter wider at publish (an XML header-width rule was tried,
`value='92'`, and did not widen it here). Numbers the two surfaces print
differ by rounding by design: the on-segment labels show the data's default
two decimals (`53.77`), the hover strings one (`53.8%`).

## Manual items left for publish time

In `docs/PUBLISH.md` "The composition sheet's interactions are likewise only
open-state-verified": hover the tooltip, tick a new state and verify it lands
in MPI position, eye-check thin-segment label collisions, and confirm the
colour card draws — plus the atlas-wide items (sheet 1's legend click, alt
text, axis headers off). This sheet needs no Fit click: the 17-bar default
fits its window with Entire View already declared.

---

## Amendment - 2026-10-24: the subtitle's word budget

The freeze's subtitle ran to 421 characters and five wrapped lines above a
17-bar chart. It is now:

> What each state's poverty is made of · shares of the MPI, adding to 100 ·
> MPI order, not a ranking · 17 of 37 bars: the left card adds the rest

What survived, and why each one had to: the meaning (what the bar IS), that the
shares add to 100, the two clauses the freeze pins (`MPI order, not a ranking`
and the default-plus-where-the-control-is sentence), and nothing else.

What left the subtitle, and where it went:

- *"health is child mortality only (nutrition is excluded for every state), so it
  carries the full one-third weight"* -> into `atlas_text.DIMENSIONS_CAVEAT`,
  the italic line of the sheet's hover, compressed to "Health = child deaths
  only here (no nutrition, for any state), so it carries the full one-third."
  The hover is where a reader is already reading the segments' numbers, so the
  sentence now sits beside the thing it qualifies.
- *"the split is exact"* -> dropped; the printed one-decimal segments and the
  axis say it.
- *"add any other state from the state checklist card on the left rail"* ->
  compressed to "the left card adds the rest" (same instruction, ten words
  fewer).

---

## Amendment 2 (2026-10-25) — the row set is parameter-driven; the checklist is retired

**Why.** The Overview dashboard gained a state selector that must move all three
panes at once (`docs/DASHBOARD.md`, 2026-10-25). The three panes read three
extracts, so the selector is a workbook parameter plus one calculated filter per
extract — not a filter card (`docs/FIX_LEDGER.md` §Q3).

**What changed on this sheet.**

- The `state` filter is now a **categorical filter on the calculated boolean**
  `state_match` instead of a manual union of 17 members. The calculation's
  `(All states)` arm carries the same 17 names
  (`dim_bar_order[:5] + dim_bar_order[12:24]`), so **the shipped default is
  unchanged**: 17 bars, same states, same MPI order (verified: the status bar
  reads "17 rows by 1 column"). A single pick from the selector overrides the 17.
- The **left-rail `state` checklist card is retired**, replaced by the same
  parameter card the dashboard's `paramctrl` zone drives. Two controls over one
  row set could not be reconciled: two ANDed filters mean a pick outside the 17
  would have drawn a silently empty pane.

**What was lost, stated plainly.** The checklist allowed ticking *several* states
at once, including states outside the default 17. That is gone: the selector is
one state or all-states. Any future multi-select needs a second parameter and a
different calculation, not a re-instated filter.

**What did not change.** The 17-bar default, the bar order, the two group blocks
`Poorest 12` / `Other 25` with the pane divider, the white segment numbers, the
hover, and the caveat line. Stage 5's gate still draws 17 bars from the same
constants.

**Wording.** `atlas_text.DIMENSIONS_SUBTITLE` no longer says "the left card adds
the rest" — it now reads "17 of 37 bars by default: the left control picks a
state".
