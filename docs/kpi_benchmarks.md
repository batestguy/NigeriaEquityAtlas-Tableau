# KPI benchmarks: Nigeria vs WHO / SDG reference standards, 2021

Stage 7 (`scripts/07_kpi_reference.py`) fetches and publishes
`data/reference/kpi_benchmarks_2021.csv` — one row per KPI, with Nigeria (WDI),
Nigeria (this pipeline's own validated national figures), Sub-Saharan Africa,
world, and the SDG benchmark where one exists. All fetched values are 2021,
dowloaded from the World Bank Indicators API on 2026-10-23 (see
`data/raw/wdi_kpi_2021/*.json` and `_provenance.csv`).

## Gating: every Nigeria number on the sheet is checked twice

## Headcount gate

`SI.POV.MPUN` (World Bank's copy of the OPHI/UNDP global MPI headcount) for
Nigeria/2021 is **33**. The OPHI national row this pipeline already reconciles
against UNDP sheet 5.3 (stage 1, tolerance 1e-3) gives **33.0441**. The two must
agree within 0.5 points before the CSV is written — that is, the sheet's KPI
values inherit the OPHI authoritative values while the fetched national figure
serves as a cross-check that the external source has not been revised.

## Code notes (discovered by fetch, 2026-10-23)

| Code | Watch out |
|---|---|
| `EG.ELC.ACCS.ZS`, `EG.CFT.ACCS.ZS` | access indicators end in `ACCS.ZS`; `ACC.ZS` is rejected by the API |
| `SH.STA.SMSS.ZS` | safely managed **sanitation** is published; safely managed **drinking water** (`SH.H2O.SMWR.ZS`, `SH.STA.SMWR.ZS`) is not, so basic water (`SH.H2O.BASW.ZS`) is the water row |
| `SI.POV.MPUN` | WDI publishes no SSA or world value for 2021; the world figure carried in the CSV (22%) is from the UNDP/OPHI *2021 Global MPI* report: 1.3 bn of 5.9 bn people across 109 countries. **It is a developing-regions average, not a literal whole-world figure.** |

## What the sheet may and may not say

- **Health dimension:** Nigeria's Health contribution *share* must never be
  compared with other countries (structurally heavier: child mortality alone,
  re-weighted to ⅓; see `docs/CAUSAL_DECISION.md`). Comparing the raw under-5
  mortality *indicator* to WHO-published standards is fine.
- **No causal language** anywhere on the sheet — proportionate comparisons only
  ("-- times the standard", "X points above/below"), never "causes" or "driven by".
- **"World" line means developing regions** on the MPI rows; it is tracked by
  `world_note` in the CSV, and the sheet's caption must say so.
- **Vintages:** survey year 2021 (MICS/DHS harmonised series), benchmarks
  fetched 2026-10-23. Both dates print in the source note and caption.
- Conflicts / climate metrics are dataset context with **no WHO standard**, and
  belong to tiers of their own if added on the sheet at all. They must not sit
  in the same visual as the tiered rows above.

## Values (verified on fetch, 2026-10-23)

| KPI | Nigeria | Sub-Saharan Africa | World | SDG benchmark |
|---|---|---|---|---|
| Multidimensional poverty headcount (national), % | **33.0** (pipeline: 33.0441) | — | 22* | — |
| Under-five mortality, per 1,000 live births | **117.6** | 77.1 | 39.6 | ≤ 25 (SDG 3.2) |
| Open defecation, % | **18.7** | 17.7 | 6.4 | 0 (SDG 6.2) |
| Safely managed sanitation, % | **30.8** | 24.7 | 56.1 | 100 (SDG 6.2) |
| At least basic drinking water, % | **77.8** | 64.8 | 90.4 | 100 (SDG 6.1) |
| Access to electricity, % | **59.5** | 50.7 | 91.3 | 100 (SDG 7.1) |
| Access to clean cooking fuels and technologies, % | **22.0** | 20.5 | 72.4 | 100 (SDG 7.1) |

\* developing-regions figure across 109 countries (not in WDI; see note above).

Dataset-native KPI rows (no standards, not fetched): national MPI **0.1748**,
average intensity **52.90** (poor-weighted, not a state mean), severe headcount
**18.10%**, vulnerable-to-poverty **16.62%**, poor population
**75.3 million** (sum of `mpi_poor_thousands` in `mpi_atlas_2021.csv`).

## Where the numbers come from

- WDI API v2 JSON per-indicator (three countries: `NGA`, `SSF`, `WLD`), fetched
  to `data/raw/wdi_kpi_2021/<code>.json`, cached — stage 7 reuses them offline.
- Nigeria-known figures from OPHI's raw national row (`data/raw/ophi_nga_mpi.csv`,
  validated by stage 1) and the merged table (`data/processed/mpi_atlas_2021.csv`).
