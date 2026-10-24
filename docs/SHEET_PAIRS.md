# Sheet freeze — "How measures pair" (the bivariate exploration board)

Status: **frozen 2026-10-21**, before build. Source interview: `docs/BRIEF_PAIRS.md`.
Grammar probes: packets A1–A6 (see `docs/FIX_LEDGER.md` §P). The sheet inside the
six-view freeze breaks it to seven; this doc is the amendment for the seventh.

## What the sheet is

An exploration board *inside* the published workbook: any pairwise scatter of the
continuous measures, split into the two poverty panels. It carries **no claim**.
Points only — no slope, no correlation, no fit, no size channel, no causal
wording. The split is *headline, not test*: the subtitle prints that the panels
cut on the outcome (the 2021 MPI value), that pane slopes are range-restricted
and not comparable, and that no test is offered.

## Grammar findings this freeze stands on (packets A1–A6, 2026-10-21)

1. **Parameters are an inline pseudo-datasource.** There is no `<parameter>`
   element in the 2026.2 schema. The workbook carries a
   `<datasource hasconnection='false' inline='true' name='Parameters'
   version='18.1'>` block whose `<column>` children carry
   `param-domain-type='list'`, a `<calculation class='tableau'
   formula='"default"'>` child (the default) and a `<members>` child (the menu).
   P1 proved it loads.
2. **Cards:** `<card mode='compact' param='[Parameters].[Parameter 1]'
   type='parameter' />` in a window's edge strip renders the dropdown.
   P2 proved it; both cards go on the left rail.
3. **The dynamic measure:** a calc column in the pairs extract,
   `<calculation class='tableau' formula='CASE [Parameters].[Parameter 1]
   WHEN "member" THEN [column] ... END' />`, used on the shelf through a
   `<column-instance derivation='Avg'>`. P3/P4 proved the parameter value
   *drives the payload* deterministically: A3 (default H) reported sheet sum
   4,931.34 = Σ H; A4 (default MPI, changed in **both** the Parameters
   datasource and the sheet-level deps block) reported 25.9903 = Σ mpi.
   **Rule: the sheet-level `<datasource-dependencies datasource='Parameters'>`
   block binds the current value, not the workbook ds block — every param
   column must carry `value=` of the same default in both places.**
4. **Pane split:** `<rows>([ds].[none:poverty_group:nk] + [ds].[avg:pair_y:qk])</rows>`
   stacks the two group panes, each with its own y scale. P5 proved it, 148
   marks in 2 rows × 1 column, group row headers labelled.
5. **log1p lives in the extract,** built by stage 4 as `log1p_*` columns
   (`log1p_events_per_100k`, `log1p_fatalities_per_100k`,
   `log1p_fatalities_per_100k_high`, computed as log(1+value), so the
   zero-event states sit at exactly 0 — on the 0 gridline, all 37 visible).
   The menu maps the logged entry to the extract column; no LOG() in the CASE.
   P6 proved the extract column drives the payload.
6. **Table order in `<table>`:** view, style, panes, rows, cols (rows before
   cols — P3's dialog gave the exact content model).
7. **Open from packet, unverified in packet:** the worksheet-title run
   `<run><![CDATA[<[Parameters].[Parameter 1]>]]></run>` was shipped in A5/A6
   but the title was never seen rendered in the captures; whether titles bind
   parameters is verified at build time before the title text is final.

## The menu (frozen)

29 entries, one WHEN-clause each. From the panel (round-wise, 148 rows):
`mpi`, `headcount_ratio_pct` (H), `intensity_pct` (A), `mpi_change_since_prev`,
`temp_mean_c`, `events_per_100k`, `log1p_events_per_100k`,
`fatalities_per_100k`, `log1p_fatalities_per_100k`,
`fatalities_per_100k_high`, `log1p_fatalities_per_100k_high`.
From the atlas 2021 CSV (constant per state, joined onto all four rounds of
that state): `mpi_se`, `headcount_se`, `intensity_se`, `population_thousands`,
`mpi_poor_thousands`, `conflict_exposure_index`, `temp_anomaly_c`,
`precip_anomaly_pct`, `baseline_temp_c`, `baseline_precip_mm`, `precip_total_mm`,
`vulnerable_pct`, `severe_pct`, `contrib_health_pct`, `contrib_education_pct`,
`contrib_living_pct`, `lat`, `lon`.
Ranks are **out** (the board reads levels; rank axes were rejected in the
interview). The 2021-only extras being constant across a state's four rounds
is accepted — the freeze notes it in the subtitle.

## Sheet spec

- Tab 4 — between "A state over time" and "What the words mean"; the three
  reference dashboards shift one tab later.
- Caption/title: **"How measures pair"**; title carries the caveat sentence.
- Columns = `Avg(Pair X)`; Rows = `(poverty_group + Avg(Pair Y))` → two stacked
  panes (`Other 25`, `Poorest 12`), split on the **2021** poverty group, the
  stamp justified by rank persistence 0.87–0.92 between rounds.
- Mark: Circle; `<lod>` Detail on `state` and `survey_year` (keeps all 148
  marks; every mark = one state-round).
- Two parameter cards on the left rail: X axis measure, then Y axis measure.
- Defaults: **X = `H (% poor)`**, **Y = `Events log`** (the documented-null pair,
  A3 in the interview; `params.H x log1p-events`).
- Hover: the atlas hover pattern via `<customized-tooltip>` — bold state, the
  round (`survey_year` + `survey`), then the Pair X and Pair Y runs with the
  two parameter values in the copy, plus poverty_group; nothing added beyond
  what the packet showed.
- No colour encoding, no size, no fit, no reference lines. Default circle fill.
- Axes: default tick format, default axis captions ("Avg Pair X"/"Avg Pair Y");
  if the title accepts the parameter bind (finding 7), the captions gain the
  current member name; otherwise both titles and captions stay plain — the
  chosen pair is visible in the dropdowns themselves.

## What this sheet may not say

The same guardlist as the withdrawn chart sheets, plus prompt items:
- no "conflict causes poverty" or any causal wording;
- no "not associated" (power floor |rho|≈0.4, and the conflict variable
  undercounts where poverty is highest);
- no "north vs south" (say "poorest states vs the rest");
- no per-pane slope/correlation/r printed or implied;
- no size channel on any mark;
- no rank framing (measure levels, not orderings).

## Unknowns recorded

- Population vintage behind stage 2's per-100k conflict rates is still
  UNKNOWN pending reading `scripts/02_acquire_conflict.py`; the freeze keeps
  that flag and the pairs extract carries the columns as stage 2 published them.
- Whether the worksheet title binds parameters (finding 7 above).

## Stage changes this freeze requires

- `04_merge.py`: stamp `poverty_group` onto all 148 panel rows; write the three
  `log1p_*` columns; write `data/processed/mpi_pairs_148.csv` (panel rows + the
  18 atlas constants joined by pcode).
- `06_build_twb.py`: build `pairs_board.hyper` (28 columns + ids), the
  Parameters datasource builder, the "How measures pair" sheet + window
  (both param cards), insert the tab at position 4; extend the schema and
  hyper list asserts from 3 to 4 extracts.
- `05_preview.py`: new gate PNG `7_how_pairs_default.png` drawing the default
  state (H × log1p events, two panes) from the same CSV columns stage 6 packs.
- Publish-time manual checks: switch x and y via both cards, confirm payload
  changes, confirm zero-event states stay on the 0 gridline on logged axes.

## Built (2026-10-22) — deltas against this freeze

Recorded here rather than silently absorbed into the freeze bullets above.

- **Tab 8, not tab 4.** The build placed the sheet last, after the three
  reference tabs, and that is what shipped and verified. The freeze's
  "insert at position 4" bullet is superseded. The stage-5 gate PNG is named
  `8_how_measures_pair.png` (tab order), not the planned `7_how_pairs_default.png`.
- **Hover = the state name only** (user request, 2026-10-22). One bold run in
  the `<customized-tooltip>`; the round, poverty_group, the two Pair values
  and the caveat runs are gone. The caveat sentences stay on-sheet in the
  subtitle, so the guardlist's wording is not lost — it just no longer rides
  the hover. `atlas_text.PAIRS_TOOLTIP_CAVEAT` was withdrawn with it.
- **Circle fill = one green**, the atlas's Okabe-Ito green `#009E73`
  (`atlas_text.PAIRS_POINT_COLOUR`, the living-standards share's green), via a
  **pane-level `<format attr='mark-color'>`** — the shape FinanceDashboard
  serialises (52 hits, verified at `<pane>` scope).
- **No colour pill.** A `<color column=...>` encoding engaged Tableau's
  categorical-palette machinery, which overrode every style rule tried and
  painted one stray default-palette orange dot. The fill comes solely from the
  pane mark rule, so no colour legend exists on this sheet and none is needed.
- **The colour grammar saga** (six packets, all render-verified; the losing
  shapes are recorded so nobody re-tries them):
  1. pane-level plain `<format attr='color' value=#009E73>` — inert (loaded;
     circles stayed blue);
  2. pane-level `<encoding>` palette map (both group buckets → one green) with
     the colour pill present — loaded; circles stayed blue + **one stray
     orange dot** (the pill's default categorical palette winning through);
  3. table-level `<encoding>` rule, ds-qualified then unqualified field,
     with the pill — same: loaded, stayed blue;
  4. **datasource-level palette** (`palette=` on `datasource_xml`, the
     placement the map sheets render from) on the *pairs* datasource —
     **failed the LOAD outright**: grey empty shell, both packet and full
     workbook, no error dialog. Not one to retry here;
  5. pane-level `<format attr='mark-color'>` — initially appeared to fail the
     load, but see 6;
  6. **the real finding: `<table>` requires its `<style>` element present
     even when empty.** Builds with `<style />` deleted under the pairs
     table failed the load with a grey empty shell on clean starts, packet
     and full workbook alike. Discovered by bracketing the failing build
     against the pre-session build (twb diff: the element and the tooltip
     runs were the only deltas). With `<style />` restored, `mark-color`
     renders the green (5 was never the breaker).
- **Stage-5 gate added:** `visual_pairs_board()` → `8_how_measures_pair.png`
  (default pair H × log1p events, panes 'Other 25' above 'Poorest 12',
  green points, no fit), so the pairs board is no longer the one published
  view without a QA-preview.
- **Reproducibility finding (open):** full-workbook renders sometimes open
  with the parameter cards on *non-file-default* selections (observed:
  Y = capital rainfall, temperature) and the chart follows the cards — the
  board's interactivity is proven working (payload tracks the dropdown), but
  which selections a fresh open carries is not deterministic from the file.
  Watch it at publish time; the shipped defaults ARE declared in the file
  (X = `H (% poor)`, Y = `Events log`) and the final verified render opened
  on exactly that pair.
- **Verified by render** (2026-10-22): `render_pairs_markcolor2.png`,
  `render_full_green_ok.png` — green circles on both panes, defaults correct,
  full workbook loads (`Tableau Public - Nigeria-MPI-Equity-Atlas`). The
  hover's on-screen content cannot be captured by PrintWindow; tooltip = one
  state-name run is XML-verified and goes to the publish-time manual checks.

## Trend line (2026-10-24) — the freeze's "no fit" is amended

The author's request: a **quadratic trend line with confidence bands, one per
pane**, asked for in white. This is an explicit override of the freeze bullets
"points only — no slope, no correlation, no fit" and "no colour encoding, no
size, no fit, no reference lines"; the substance of the guardlist is preserved
in the form the line takes (below), not silently dropped.

**What shipped, in the pairs `<pane>`:**

```xml
<trendline enabled='true' fit='polynomial' degree='2' exclude-intercept='false'
           enable-confidence-bands='true' exclude-color='false'
           enable-instant-analytics='false' enable-tooltips='true' />
```

plus a pane style rule

```xml
<style-rule element='trendline'>
  <format attr='stroke-color' value='#4D4D4D' />
  <format attr='stroke-size' value='2' />
</style-rule>
```

`exclude-color='false'` is the dialog's "allow a trend line per colour". There
is no colour pill on this sheet, so the split that produces **one line per pane**
is `poverty_group` on Rows: each pane is fitted on its own marks. `degree` only
means anything for `fit='polynomial'`. The element sits **after `</encodings>`
and before `<customized-tooltip>`** — that position is fixed by the schema's
sequence, not a preference.

### Where the grammar came from (no packet exists)

This is the first thing in the workbook whose XML came from a **specification**
rather than a render packet, and the reason is worth recording:

- GitHub code search finds **no public `.twb` that serialises a trend line**
  (`polyDegree extension:twb` → 0 hits; the two `"trend-line"` `.twb` hits only
  mention it in a title string). A reference packet cannot be obtained this way.
- The Save-As route (set the dialog state in-app, save, read the XML) was
  attempted and is not available to automation on this machine: the Trend Lines
  dialog is a Qt window **invisible to UIA** (root children show only
  `TMainWindow`), and this session's console steals the foreground from the app
  between shell invocations, so the two synthetic clicks it needs (tick "Show
  confidence bands", OK) could not be landed reliably. The dialog's state was
  confirmed visually first: Model Type **Polynomial, degree 2**, Factor
  **`poverty_group`**, and **Show confidence bands the only unticked box**.
- **Tableau publishes its own TWB schema**: `github.com/tableau/tableau-document-schemas`,
  `schemas/2026_1/twb_2026.1.0.xsd` and `schemas/2026_2/twb_2026.2.0.xsd`
  (the 2026.2 file is the one matching the installed Public build,
  `20262.26.0528.2205`). Both carry the identical group
  **`PaneSpecification-Trendline-G`**, whose content model is exactly the
  element above: `id  enabled | fit | exclude-intercept |
  enable-confidence-bands | exclude-color | enable-instant-analytics |
  enable-tooltips | degree`, `fit` from `TrendLineFitType-ST`
  (`linear | polynomial | log | exp | power`), and an optional
  `excluded-factors` child. `StyleElement-ST` in the same file enumerates
  `trendline` beside `mark` / `refline` / `gridline`, and `StyleAttribute-ST`
  carries `stroke-color` / `stroke-size` — which is what the style rule above
  uses.
- **Verification used**: the built twb was validated against the 2026.2 schema
  with lxml (the two `xs:import`s stubbed locally, `user` → `UserAttributes-AG`
  and `xml:base`). Result: **0 errors mentioning `trendline`**. The 30 errors it
  does report are the pre-existing, Tableau-tolerated deviations already in the
  ledger (`extract/@object-id` missing, `layout/@dim-percentage` +
  `@measure-percentage`, the `simple-id` elements this schema *requires* but
  Tableau's own loader rejects — `D2E8DA72` — and one `sort` ordering), all
  unchanged by this work. Schema-validity is still *not* sufficient on its own
  (`AGENTS.md` has six defects that got past it), so the line was then
  **render-verified**: both panes draw a degree-2 curve with a dotted band.

### White does not work on this sheet — verified, not assumed

The request was a **white** line. Built with `stroke-color='#FFFFFF'` the line
and both band edges **vanish** into the white pane (every mark and gridline
stayed; only the trend paint disappeared), and re-painting it `#4D4D4D` brought
them straight back at the same geometry — so the rule is live and the colour is
simply invisible. Shipped value: `#4D4D4D`, a neutral dark ink that reads as an
overlay the marks sit on top of rather than as a second series, and that cannot
be confused with the green fill. Going white is the one hex in
`atlas_text.PAIRS_TREND_COLOUR`.

### `enable-instant-analytics='false'` on purpose

Instant analytics is what makes Tableau print the **fitted model's equation and
p-value** in the hover. That is precisely what this sheet's guardlist forbids
("no per-pane slope/correlation/r printed or implied"), so the switch is off;
`enable-tooltips='true'` keeps the ordinary hover. The hover is still the state
name only (2026-10-22 decision, unchanged).

### What the line may and may not be read as

`docs/CAUSAL_DECISION.md` governs. The line is a **description of each pane's
own marks** — a degree-2 least-squares fit — not a result:

- **no slope, no coefficient, no correlation, no p-value is printed anywhere**,
  on the sheet or in the gate; the sheet prints no fit statistic at all;
- the **panes are cut on the outcome** (the 2021 poorest-12 split), so the two
  lines are **range-restricted and not comparable to each other** — the
  subtitle says so, as it did before the line existed;
- the bands are the **95% confidence band for the fitted mean** (Tableau's
  default), not a prediction interval for a state, and they are wide because
  each pane covers only part of the x range;
- the **subtitle was amended** to carry the new sentence
  `atlas_text.PAIRS_SUBTITLE`: "each pane's quadratic line only describes its
  own marks -- no slope, no coefficient, no claim". Sheet and gate read the
  same constant.

### Gate changes (stage 5) and the build gate (stage 6)

- `05_preview.py` now draws the **same fit** in the **same colour**:
  `quadratic_fit_band()` (numpy `lstsq` + the t-based 95% band for the fitted
  mean, `scipy.stats.t`), one per pane, under the marks. The gate's rule — the
  PNG and the sheet must not be able to disagree — is what makes this a
  requirement rather than a nicety; `docs/preview/9_how_measures_pair.png`
  shows the banded fit.
- `06_build_twb.py`'s `validate()` now **asserts** the trendline: exactly one
  `<trendline>` in the workbook, carrying `enabled='true'`, `fit='polynomial'`,
  `degree='2'`, `enable-confidence-bands='true'`. A dropped or down-graded
  element would still load and still render — just without the line.

### Publish-time checks this adds

1. The hover must **not** print a model equation or p-value (instant analytics
   off) — check by hovering a pane.
2. Both panes show the line **and** its band, and switching the pair via either
   dropdown re-fits both panes.
3. The subtitle's three lines still fit the title block at the published window
   size (it grew by one clause, 2026-10-24).

