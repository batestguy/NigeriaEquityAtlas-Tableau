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
