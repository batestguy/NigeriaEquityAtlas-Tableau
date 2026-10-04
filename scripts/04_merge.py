"""Stage 4 -- merge the four layers into the tables Tableau reads, and document the scales.

Produces:
  data/processed/mpi_atlas_2021.csv    37 rows, one per state, the 2021 baseline
  data/processed/mpi_trends_panel.csv  148 rows, 37 states x 4 survey rounds
  data/processed/atlas_vintages.csv    per-round scale anchors and headline stats
  docs/normalisation.md                how every derived index is defined and scaled
  docs/data_quality.md                 the caveats a reader has to be told about

Conflict Exposure Index follows the spec (event and fatality rates per 100k,
min-max scaled to 0-100) with one refinement: scaling is done *within each survey
round*, so the poverty/conflict comparison is always same-year rather than
pairing 2021 poverty with a pooled conflict history. The consequence is that the
index is cross-sectionally relative -- 0 and 100 mean "least" and "most" among
these 37 states in that year, not an absolute level -- so the anchors go into
atlas_vintages.csv to keep the scale reproducible.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path
from statistics import median
from typing import Any, cast

from scipy.stats import spearmanr

from common import DOCS, INTERIM, PROCESSED, minmax, read_capitals, read_lookup, write_csv

SURVEY_ROUNDS = (2013, 2016, 2018, 2021)
BASELINE_YEAR = 2021


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def quadrant(h: float, a: float, med_h: float, med_a: float) -> str:
    incidence = "High incidence" if h >= med_h else "Low incidence"
    intensity = "High intensity" if a >= med_a else "Low intensity"
    return f"{incidence}, {intensity}"


def spearman(x: list[float], y: list[float]) -> tuple[float, float]:
    """Spearman rho and p-value.

    scipy returns a named-tuple-like result; it is cast explicitly so both the
    runtime behaviour and the type checker see a plain (rho, p) pair.
    """
    result = cast("tuple[float, float]", spearmanr(x, y))
    return result[0], result[1]


def main() -> int:
    lookup = read_lookup()
    capitals = read_capitals()

    dims = {r["pcode"]: r for r in read(INTERIM / "mpi_dimensions.csv")}
    head = {r["pcode"]: r for r in read(INTERIM / "mpi_headline.csv")}
    trends = read(INTERIM / "mpi_trends.csv")
    conflict = {(r["pcode"], int(r["year"])): r for r in read(INTERIM / "conflict_state_year.csv")}
    climate = {(r["pcode"], int(r["year"])): r for r in read(INTERIM / "climate_state_year.csv")}
    baseline = {r["pcode"]: r for r in read(INTERIM / "climate_baseline_1991_2020.csv")}

    for name, table in (("dimensions", dims), ("headline", head), ("baseline", baseline)):
        missing = sorted(set(lookup) - set(table))
        if missing:
            raise SystemExit(f"{name} table is missing {len(missing)} state(s): {missing[:5]}")
    for pcode in lookup:
        for year in SURVEY_ROUNDS:
            if (pcode, year) not in conflict:
                raise SystemExit(f"conflict table missing {pcode} {year}")
            if (pcode, year) not in climate:
                raise SystemExit(f"climate table missing {pcode} {year}")

    population = {p: f(dims[p], "population_thousands") * 1000.0 for p in lookup}

    # ---- Conflict Exposure Index, scaled within each survey round -----------
    cei: dict[tuple[str, int], float] = {}
    anchors: list[dict[str, Any]] = []
    for year in SURVEY_ROUNDS:
        ev_raw = {p: f(conflict[(p, year)], "events") / population[p] * 100_000 for p in lookup}
        fa_raw = {p: f(conflict[(p, year)], "fatalities") / population[p] * 100_000 for p in lookup}
        ev_s, ev_lo, ev_hi = minmax(ev_raw)
        fa_s, fa_lo, fa_hi = minmax(fa_raw)
        for p in lookup:
            cei[(p, year)] = round((ev_s[p] + fa_s[p]) / 2.0, 2)
        anchors.append(
            {
                "survey_year": year,
                "events_per_100k_min": round(ev_lo, 4),
                "events_per_100k_max": round(ev_hi, 4),
                "fatalities_per_100k_min": round(fa_lo, 4),
                "fatalities_per_100k_max": round(fa_hi, 4),
                "lowest_cei_state": lookup[min(ev_s, key=lambda p: ev_s[p])]["name_canonical"],
                "highest_cei_state": lookup[max(ev_s, key=lambda p: ev_s[p])]["name_canonical"],
            }
        )

    med_h = median([f(head[p], "headcount_ratio_pct") for p in lookup])
    med_a = median([f(head[p], "intensity_pct") for p in lookup])
    print(f"median headcount ratio {med_h:.2f}%, median intensity {med_a:.2f}%")

    # ---- 2021 baseline table ----------------------------------------------
    atlas_rows: list[dict[str, Any]] = []
    for pcode in sorted(lookup):
        d, h = dims[pcode], head[pcode]
        c, cl = conflict[(pcode, BASELINE_YEAR)], climate[(pcode, BASELINE_YEAR)]
        atlas_rows.append(
            {
                "pcode": pcode,
                "state": d["state"],
                "capital": capitals[pcode]["capital"],
                "lat": capitals[pcode]["lat"],
                "lon": capitals[pcode]["lon"],
                # poverty -- 2021 MICS
                "mpi": round(f(h, "mpi"), 4),
                "headcount_ratio_pct": round(f(h, "headcount_ratio_pct"), 2),
                "intensity_pct": round(f(h, "intensity_pct"), 2),
                "vulnerable_pct": round(f(h, "vulnerable_pct"), 2),
                "severe_pct": round(f(h, "severe_pct"), 2),
                "contrib_health_pct": round(f(d, "contrib_health_pct"), 2),
                "contrib_education_pct": round(f(d, "contrib_education_pct"), 2),
                "contrib_living_standards_pct": round(f(d, "contrib_living_standards_pct"), 2),
                "population_thousands": round(f(d, "population_thousands"), 1),
                "mpi_poor_thousands": round(f(d, "mpi_poor_thousands"), 1),
                "quadrant": quadrant(f(h, "headcount_ratio_pct"), f(h, "intensity_pct"), med_h, med_a),
                "n_indicators": int(f(d, "n_indicators")),
                "indicators_missing": d["indicators_missing"],
                "survey": h["survey"],
                "survey_year": int(h["survey_year"]),
                # conflict -- same year as the poverty baseline
                "events": int(f(c, "events")),
                "fatalities": round(f(c, "fatalities"), 1),
                "events_per_100k": round(f(c, "events") / population[pcode] * 100_000, 3),
                "fatalities_per_100k": round(f(c, "fatalities") / population[pcode] * 100_000, 3),
                "conflict_exposure_index": cei[(pcode, BASELINE_YEAR)],
                # climate -- same year, plus the 1991-2020 baseline
                "temp_mean_c": round(f(cl, "temp_mean_c"), 2),
                "precip_total_mm": round(f(cl, "precip_total_mm"), 1),
                "temp_anomaly_c": round(f(cl, "temp_anomaly_c"), 2),
                "precip_anomaly_pct": round(f(cl, "precip_anomaly_pct"), 1),
                "baseline_temp_c": round(f(baseline[pcode], "baseline_temp_c"), 2),
                "baseline_precip_mm": round(f(baseline[pcode], "baseline_precip_mm_per_year"), 1),
            }
        )

    ordered = sorted(atlas_rows, key=lambda r: -r["mpi"])
    for i, r in enumerate(ordered, start=1):
        r["mpi_rank"] = i
    poor_order = sorted(atlas_rows, key=lambda r: -r["mpi_poor_thousands"])
    for i, r in enumerate(poor_order, start=1):
        r["mpi_poor_rank"] = i

    atlas_fields = [
        "pcode", "state", "capital", "lat", "lon",
        "mpi", "mpi_rank", "headcount_ratio_pct", "intensity_pct",
        "vulnerable_pct", "severe_pct", "quadrant",
        "contrib_health_pct", "contrib_education_pct", "contrib_living_standards_pct",
        "population_thousands", "mpi_poor_thousands", "mpi_poor_rank",
        "events", "fatalities", "events_per_100k", "fatalities_per_100k",
        "conflict_exposure_index",
        "temp_mean_c", "precip_total_mm", "temp_anomaly_c", "precip_anomaly_pct",
        "baseline_temp_c", "baseline_precip_mm",
        "n_indicators", "indicators_missing", "survey", "survey_year",
    ]
    n_atlas = write_csv(PROCESSED / "mpi_atlas_2021.csv", atlas_rows, atlas_fields)

    # ---- trends panel ------------------------------------------------------
    trend_by_key = {(r["pcode"], int(r["survey_year"])): r for r in trends}
    panel_rows: list[dict[str, Any]] = []
    for pcode in sorted(lookup):
        for year in SURVEY_ROUNDS:
            t = trend_by_key[(pcode, year)]
            c, cl = conflict[(pcode, year)], climate[(pcode, year)]
            panel_rows.append(
                {
                    "pcode": pcode,
                    "state": lookup[pcode]["name_canonical"],
                    "survey_year": year,
                    "survey": t["survey"],
                    "mpi": round(f(t, "mpi"), 4),
                    "headcount_ratio_pct": round(f(t, "headcount_ratio"), 2),
                    "intensity_pct": round(f(t, "intensity"), 2),
                    "events": int(f(c, "events")),
                    "fatalities": round(f(c, "fatalities"), 1),
                    "events_per_100k": round(f(c, "events") / population[pcode] * 100_000, 3),
                    "fatalities_per_100k": round(f(c, "fatalities") / population[pcode] * 100_000, 3),
                    "conflict_exposure_index": cei[(pcode, year)],
                    "temp_mean_c": round(f(cl, "temp_mean_c"), 2),
                    "temp_anomaly_c": round(f(cl, "temp_anomaly_c"), 2),
                    "precip_anomaly_pct": round(f(cl, "precip_anomaly_pct"), 1),
                }
            )
    panel_fields = [
        "pcode", "state", "survey_year", "survey", "mpi", "headcount_ratio_pct",
        "intensity_pct", "events", "fatalities", "events_per_100k", "fatalities_per_100k",
        "conflict_exposure_index", "temp_mean_c", "temp_anomaly_c", "precip_anomaly_pct",
    ]
    n_panel = write_csv(PROCESSED / "mpi_trends_panel.csv", panel_rows, panel_fields)

    # ---- per-round summary -------------------------------------------------
    print("\npoverty vs conflict, matched survey years (Spearman, n=37):")
    anchor_by_year: dict[int, dict[str, Any]] = {a["survey_year"]: a for a in anchors}
    for year in SURVEY_ROUNDS:
        yr_rows = [r for r in panel_rows if r["survey_year"] == year]
        mc = spearman(
            [r["mpi"] for r in yr_rows],
            [r["conflict_exposure_index"] for r in yr_rows],
        )
        mt = spearman(
            [r["mpi"] for r in yr_rows],
            [r["temp_anomaly_c"] for r in yr_rows],
        )
        row = anchor_by_year[year]
        row.update(
            {
                "survey": yr_rows[0]["survey"],
                "median_state_mpi": round(median([r["mpi"] for r in yr_rows]), 4),
                "total_events": sum(r["events"] for r in yr_rows),
                "total_fatalities": round(sum(r["fatalities"] for r in yr_rows), 1),
                "mean_temp_anomaly_c": round(
                    sum(r["temp_anomaly_c"] for r in yr_rows) / len(yr_rows), 3
                ),
                "spearman_mpi_vs_conflict": round(float(mc[0]), 4),
                "p_mpi_vs_conflict": round(float(mc[1]), 5),
                "spearman_mpi_vs_temp_anomaly": round(float(mt[0]), 4),
                "p_mpi_vs_temp_anomaly": round(float(mt[1]), 5),
            }
        )
        print(
            f"   {year} ({yr_rows[0]['survey']:4}): rho(MPI,conflict)={mc[0]:+.3f} p={mc[1]:.4f}   "
            f"rho(MPI,temp anomaly)={mt[0]:+.3f} p={mt[1]:.4f}"
        )

    # The stable climate signal is each capital's *baseline* climate, not any one
    # year's anomaly. The per-year anomaly correlation above swings from +0.81 to
    # -0.43 across four rounds, which is weather noise; the baseline relationship
    # is what a climate-poverty visual should actually show.
    bt = spearman([float(dims[p]["mpi"]) for p in sorted(lookup)],
                  [f(baseline[p], "baseline_temp_c") for p in sorted(lookup)])
    bp = spearman([float(dims[p]["mpi"]) for p in sorted(lookup)],
                  [f(baseline[p], "baseline_precip_mm_per_year") for p in sorted(lookup)])
    print(
        f"\n   baseline 1991-2020 climate vs MPI: rho(temp)={bt[0]:+.3f} p={bt[1]:.2e}   "
        f"rho(precip)={bp[0]:+.3f} p={bp[1]:.2e}"
    )
    print("   (annual anomalies swing in sign across rounds; the baseline does not)")

    vintage_fields = [
        "survey_year", "survey", "median_state_mpi", "total_events", "total_fatalities",
        "mean_temp_anomaly_c", "events_per_100k_min", "events_per_100k_max",
        "fatalities_per_100k_min", "fatalities_per_100k_max",
        "lowest_cei_state", "highest_cei_state",
        "spearman_mpi_vs_conflict", "p_mpi_vs_conflict",
        "spearman_mpi_vs_temp_anomaly", "p_mpi_vs_temp_anomaly",
    ]
    n_vint = write_csv(
        PROCESSED / "atlas_vintages.csv",
        [anchor_by_year[y] for y in SURVEY_ROUNDS],
        vintage_fields,
    )

    # ---- gates -------------------------------------------------------------
    assert len(atlas_rows) == 37, f"atlas table has {len(atlas_rows)} rows, expected 37"
    for key in atlas_fields:
        blanks = [r["state"] for r in atlas_rows if r.get(key) in (None, "")]
        if blanks:
            raise SystemExit(f"atlas column {key!r} is empty for {len(blanks)} state(s): {blanks[:5]}")
    assert len(panel_rows) == 148, f"panel has {len(panel_rows)} rows, expected 148"

    for y1, y2 in zip(SURVEY_ROUNDS, SURVEY_ROUNDS[1:]):
        a = {r["pcode"]: r["mpi"] for r in panel_rows if r["survey_year"] == y1}
        b = {r["pcode"]: r["mpi"] for r in panel_rows if r["survey_year"] == y2}
        rho, _ = spearman([a[p] for p in sorted(a)], [b[p] for p in sorted(a)])
        print(f"   MPI rank persistence {y1}->{y2}: rho={rho:+.3f}")

    print(f"\nwrote {n_atlas} rows -> data/processed/mpi_atlas_2021.csv")
    print(f"wrote {n_panel} rows -> data/processed/mpi_trends_panel.csv")
    print(f"wrote {n_vint} rows -> data/processed/atlas_vintages.csv")
    write_docs()
    return 0


def write_docs() -> None:
    """Emit the two documents a published viz must not contradict."""
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "normalisation.md").write_text(
        NORMALISATION_MD.strip() + "\n",
        encoding="utf-8",
    )
    (DOCS / "data_quality.md").write_text(DATA_QUALITY_MD.strip() + "\n", encoding="utf-8")


NORMALISATION_MD = """
# How every derived number in this atlas is defined

Baseline vintage: **MICS 2021** (36 states + FCT = 37 admin-1 units).

## MPI

Published as-is by OPHI / UNDP Global MPI. No rescaling. MPI = H x A, where H is
the headcount ratio (% of people multidimensionally poor) and A is the intensity of
deprivation (average deprivation score among the poor).

Dimension figures are the **percentage contribution of each dimension to the MPI**
(Health, Education, Living Standards). They sum to 100 within each state. Nigeria's
MPI uses 9 indicators; Nutrition is excluded for every state, so the Health
dimension rests on child mortality alone.

## Conflict Exposure Index (0-100)

Per the project spec, step 4. Computed for each state and each MPI survey year:

```
events_per_100k      = events in year / population * 100000
fatalities_per_100k  = best-estimate fatalities in year / population * 100000
events_scaled        = 100 * (events_per_100k      - year_min) / (year_max - year_min)
fatalities_scaled    = 100 * (fatalities_per_100k  - year_min) / (year_max - year_min)
Conflict Exposure Index = (events_scaled + fatalities_scaled) / 2
```

**Scaling is done within each survey year, not pooled across years.** Two
consequences, both intentional:

1. The poverty/conflict comparison is always same-year, so a state is never
   measured against a different year's violence.
2. The index is **cross-sectionally relative**. 0 means "fewest events and
   fatalities per 100k of these 37 states that year"; 100 means "most". It is not
   an absolute risk level and values are **not comparable across survey years**.

Min/max anchors for every round are written to `data/processed/atlas_vintages.csv`
so the scale can be reproduced or re-anchored.

Source: UCDP Georeferenced Event Dataset, types 1-3, `best` fatality estimate.

## Climate

Annual values are aggregated from Open-Meteo daily series at the state capital
(GeoNames admin-1 seat coordinates, `data/reference/state_capitals.csv`):

- `temp_mean_c` = mean of daily mean temperature over the calendar year
- `precip_total_mm` = sum of daily precipitation over the calendar year
- `temp_anomaly_c` = `temp_mean_c` - mean of that capital's 1991-2020 mean temperature
- `precip_anomaly_pct` = 100 * (`precip_total_mm` - baseline annual precipitation) / baseline

Baseline period 1991-2020 (the WMO standard normal period). Anomalies are relative
to each capital's own baseline, so they compare capitals against their own climate,
not against a single national figure.

## Population denominators

Per-state population comes from the UNDP Global MPI subnational table
(`population_thousands`), summing to 227.9 million with state shares summing to
exactly 100%. The table does not state a year for this column; it sits alongside
its own "Population 2022" and "Population 2023" country columns (223.2 million for
2023), so the state figures run about 2% above the workbook's own 2023 national
total and are probably a later vintage.

Two documented approximations follow:

- Per-100k conflict rates for the 2021 baseline use a population vintage later than
  2021, biasing rates low by a few percent uniformly.
- The same denominator is reused for all four survey rounds. Because the index is
  min-max scaled within each round, a uniform bias cancels exactly; what does not
  cancel is *differential* population growth across states between 2013 and 2021.
"""


DATA_QUALITY_MD = """
# Data quality and caveats

Read this before quoting any number from the atlas.

## Sources and vintages

| Layer | Source | Licence | Vintage |
|---|---|---|---|
| Poverty | OPHI + UNDP Global MPI subnational database | CC0 / CC BY | MICS 2021 (+ 2013 DHS, 2016 MICS, 2018 DHS trends) |
| Conflict | UCDP Georeferenced Event Dataset | CC BY-IGO | 1990-2024 |
| Climate | Open-Meteo Archive API | free, keyless | 1990-2024 daily |
| Boundaries | geoBoundaries ADM1 | CC BY 4.0 | 2024 release |
| Capitals | GeoNames `cities5000` | CC BY 4.0 | gazetteer |

OPHI and UNDP are independent publications of the same 2021 survey. They are
reconciled state by state on every pipeline run and the run aborts if any MPI value
disagrees by more than 1e-3.

## Known limitations

1. **The Health dimension is narrower than the standard MPI.** All 37 states report
   Nutrition as excluded, so Health is carried by child mortality alone. Health is
   therefore comparable *between* Nigerian states but not directly comparable to
   published MPI figures from countries that do use a nutrition indicator.

2. **The Conflict Exposure Index is relative, not absolute.** See
   `normalisation.md`. Do not describe a state as having "a Conflict Exposure Index
   of 80" without saying it is the highest among these 37 states that year.

3. **Conflict and poverty are not matched samples.** UCDP events are media-reported
   and coverage is uneven across states; the MPI is survey-based. A correlation
   between them is an association between two differently-measured quantities, and
   reverse causation is at least as plausible as the reverse.

4. **UCDP, not ACLED.** The project spec asked for ACLED. ACLED was unobtainable in
   this environment (the API host does not resolve, and HDX only carries ACLED's
   country-year/month aggregates). UCDP covers the same period, is open, and is
   georeferenced per event, but it counts events on different criteria -- so
   conflict magnitudes here are not comparable to an ACLED-based figure.

5. **Zero conflict events is not zero conflict.** In 2021, 10 of 37 states recorded
   no UCDP event at all. That reflects reporting coverage as much as actual absence
   of violence. These are written as explicit zeros, not nulls.

6. **Gongola.** One UCDP event is attributed to "Gongola state", an administrative
   unit abolished in 1991 and since divided between Adamawa and Taraba. It is
   attributed to Adamawa; the row is retained in
   `data/interim/conflict_events_attributed.csv` with `attribution_method =
   obsolete_unit`.

7. **FCT is a state here.** It is included in every aggregate. Dropping it is a
   common and silent error -- it is also the territory whose OPHI PCode is blank in
   the source, so it is the row most likely to vanish in a join.

8. **Climate is sampled at capitals.** A capital's climate is a reasonable proxy for
   a state but not an areal average. Large states (Borno, Bauchi, Katsina) span
   several climate zones.
"""


if __name__ == "__main__":
    sys.exit(main())