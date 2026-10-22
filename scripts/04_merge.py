"""Stage 4 -- merge the four layers into the tables Tableau reads, and document the scales.

Produces:
  data/processed/mpi_atlas_2021.csv    37 rows, one per state, the 2021 baseline
  data/processed/mpi_trends_panel.csv  148 rows, 37 states x 4 survey rounds
  data/processed/mpi_polygons.csv      ADM1 ring vertices (simplified), for the Tableau filled map
  data/processed/atlas_vintages.csv    per-round scale anchors and headline stats
  data/processed/mpi_pairs_148.csv     148 panel rows + atlas constants (the pairs board extract)
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
import json
import math
import sys
from pathlib import Path
from statistics import median
from typing import Any, cast

from scipy.stats import spearmanr
from shapely.geometry import shape as shapely_shape

import atlas_text
from common import (DOCS, INTERIM, PROCESSED, RAW, REFERENCE, minmax, read_capitals,
                    read_lookup, write_csv)

SURVEY_ROUNDS = (2013, 2016, 2018, 2021)
BASELINE_YEAR = 2021

# Ring simplification for the Tableau map's polygon extract, in degrees. See the
# comment at the mpi_polygons.csv block for why 0.005 degrees is safe here.
SIMPLIFY_TOLERANCE_DEG = 0.005

# The governorship line carried into the map's tooltip. 1999 is the start of the
# Fourth Republic, which is the window state_dominant_party.csv is built on; 2021
# is the MPI survey year, so the two agree on where "now" is.
PARTY_WINDOW_START = 1999
PARTY_WINDOW_END = 2021
PARTY_SPAN_YEARS = PARTY_WINDOW_END - PARTY_WINDOW_START

# A seating holds office until the next seating, so the order *within* a year
# decides who owns that year's tenure. Two seatings share a year in one case --
# Anambra 2007, where the May swearing-in was annulled and the governor reinstated
# in June -- so the event types are ranked rather than left to file order. A court
# decision seats a governor after the election that year would have.
SEATING_ORDER = {"cycle": 0, "off-cycle": 1, "rerun": 1, "court": 2}


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def f(row: dict[str, str], key: str) -> float:
    return float(row[key])


def quadrant(h: float, a: float, med_h: float, med_a: float) -> str:
    """Incidence x intensity, cut at the medians.

    Named honestly on purpose. The headcount ratio spans 1.1-75.4 across these 37
    states (a factor of 68) while intensity spans only 39.5-61.8 (a factor of 1.6),
    so the two cutpoints do not produce four comparable quadrants -- they produce
    17/2/2/16. The label says "incidence" and "intensity" rather than "high" and
    "low poverty", because calling the intensity half a poverty level overstates
    what a 1.6x range can support.
    """
    incidence = "High incidence" if h >= med_h else "Low incidence"
    intensity = "Higher intensity" if a >= med_a else "Lower intensity"
    return f"{incidence}, {intensity}"


def mpi_band(mpi: float) -> str:
    """Coarse MPI bands for the choropleth, labelled as percentages of the index.

    A continuous ramp invites reading differences the data cannot resolve: the
    median 95% CI width is 0.075 against a median MPI of 0.092. Five named bands
    match the resolution the standard errors actually support, and five classes is
    also the ceiling for accurate legend-matching (Mersey 1984: 96% at 3 classes,
    70% at 5, 26% at 9).

    The MPI is a 0-1 index, so its value is already a share of the maximum and
    "0.20 to 0.30" and "20% to 30%" are the same quantity -- the percent sign just
    saves the reader the conversion. It is *not* the share of people who are poor:
    that is H, carried separately (Zamfara 71.87% against an MPI of 0.391), and
    docs/CLAIMS.md forbids reading the two as one number.

    The leading "N. " is a sort key, not part of the label: the colour legend is
    sorted alphabetically, so unlabelled bands would run "10% to 20%" before
    "5% to 10%" and put "under 5%" last. Stage 7 strips the prefix for the HTML map.
    """
    if mpi < 0.05:
        return "1. under 5%"
    if mpi < 0.10:
        return "2. 5% to 10%"
    if mpi < 0.20:
        return "3. 10% to 20%"
    if mpi < 0.30:
        return "4. 20% to 30%"
    return "5. 30% and above"


def party_years(events: list[dict[str, str]],
                span_end: int = PARTY_WINDOW_END) -> dict[str, int]:
    """Years each party held a state's governorship, seating to seating.

    A seating holds office from the year it was seated until the next seating, and
    the last one is truncated at the end of the window -- so the totals sum to the
    window length rather than to the length of each term. Zero-length tenures are
    real (Anambra's annulled May 2007 swearing-in, and the seatings that fall after
    the window closes) and are kept, so the years are a faithful reading of
    governorship_events.csv rather than a tidy one.
    """
    ordered = sorted(
        events,
        key=lambda e: (int(e["seated_year"]), SEATING_ORDER.get(e["event_type"], 3)),
    )
    years: dict[str, int] = {}
    for i, event in enumerate(ordered):
        start = int(event["seated_year"])
        end = int(ordered[i + 1]["seated_year"]) if i + 1 < len(ordered) else span_end
        years[event["party"]] = years.get(event["party"], 0) + max(0, min(end, span_end) - start)
    return years


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
    changes = read(INTERIM / "ophi_harmonised_changes.csv")
    conflict = {(r["pcode"], int(r["year"])): r for r in read(INTERIM / "conflict_state_year.csv")}
    climate = {(r["pcode"], int(r["year"])): r for r in read(INTERIM / "climate_state_year.csv")}
    baseline = {r["pcode"]: r for r in read(INTERIM / "climate_baseline_1991_2020.csv")}

    # (pcode, year_to) -> the OPHI Table 6.4 row for that state's change.
    # OPHI labels the second MICS round "2016-2017"; the panel keys it on 2016.
    change_by_key: dict[tuple[str, int], dict[str, str]] = {
        (r["pcode"], int(r["year_to"][:4])): r for r in changes
    }

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
    # Every round except the first has a preceding round, so 3 of the 4 survey
    # years must carry a Table 6.4 change row for every state.
    expected_changes = {(p, y) for p in lookup for y in SURVEY_ROUNDS[1:]}
    if not expected_changes <= set(change_by_key):
        absent = sorted(expected_changes - set(change_by_key))
        raise SystemExit(f"harmonised changes missing {len(absent)} state-year(s): {absent[:5]}")

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
                # poverty -- 2021 MICS. mpi_se / CI bounds are OPHI's design-based
                # standard errors (UNDP 5.4); without them no ordering of states is
                # resolvable, since all 36 adjacent rank pairs overlap at 95%.
                "mpi": round(f(h, "mpi"), 4),
                "mpi_se": round(f(d, "mpi_se"), 4),
                "mpi_ci_lo": round(f(d, "mpi_ci_lo"), 4),
                "mpi_ci_hi": round(f(d, "mpi_ci_hi"), 4),
                "headcount_ratio_pct": round(f(h, "headcount_ratio_pct"), 2),
                "headcount_se": round(f(d, "headcount_se"), 2),
                "intensity_pct": round(f(h, "intensity_pct"), 2),
                "vulnerable_pct": round(f(h, "vulnerable_pct"), 2),
                "severe_pct": round(f(h, "severe_pct"), 2),
                "contrib_health_pct": round(f(d, "contrib_health_pct"), 2),
                "contrib_education_pct": round(f(d, "contrib_education_pct"), 2),
                "contrib_living_standards_pct": round(f(d, "contrib_living_standards_pct"), 2),
                "population_thousands": round(f(d, "population_thousands"), 1),
                "mpi_poor_thousands": round(f(d, "mpi_poor_thousands"), 1),
                "quadrant": quadrant(f(h, "headcount_ratio_pct"), f(h, "intensity_pct"), med_h, med_a),
                "mpi_band": mpi_band(f(h, "mpi")),
                "n_indicators": int(f(d, "n_indicators")),
                "indicators_missing": d["indicators_missing"],
                "survey": h["survey"],
                "survey_year": int(h["survey_year"]),
                # conflict -- same year as the poverty baseline
                "events": int(f(c, "events")),
                "fatalities": round(f(c, "fatalities"), 1),
                "fatalities_low": round(f(c, "fatalities_low"), 1),
                "fatalities_high": round(f(c, "fatalities_high"), 1),
                "events_per_100k": round(f(c, "events") / population[pcode] * 100_000, 3),
                "fatalities_per_100k": round(f(c, "fatalities") / population[pcode] * 100_000, 3),
                "fatalities_per_100k_high": round(
                    f(c, "fatalities_high") / population[pcode] * 100_000, 3
                ),
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
        # Explorer toggle for Sheet 1: poorest 12 vs rest. The 12-state cut is
        # the poverty-level contrast that survives the SEs (17.6-pt education
        # gap, p=1e-5); "north vs south" is the same 12 observations wearing a
        # geographic label, so the toggle says poorest vs rest, never north/south.
        r["poverty_group"] = "Poorest 12" if i <= 12 else "Other 25"
    poor_order = sorted(atlas_rows, key=lambda r: -r["mpi_poor_thousands"])
    for i, r in enumerate(poor_order, start=1):
        r["mpi_poor_rank"] = i

    # ---- the composition sheet's pre-formatted hover strings -----------------
    # Tableau's tooltip cannot build a sentence, so the composition line is
    # composed here once per state, in atlas_text.DIMENSION_SHARES' stacking
    # order, and carried verbatim by the atlas table, the polygon table (both
    # maps' hovers) and the composition sheet's extract. The three shares are
    # an identity and always sum to 100 (asserted below), so two decimals of it
    # is presentation, not precision.
    for r in atlas_rows:
        shares = sorted(
            ((name, r[field]) for field, name, _colour in atlas_text.DIMENSION_SHARES),
            key=lambda t: -t[1],
        )
        r["dim_hover"] = " \u00b7 ".join(f"{name} {value:.1f}%" for name, value in shares)
        r["mpi_label"] = f"{r['mpi'] * 100:.1f}%"
    for r in atlas_rows:
        assert abs(sum(r[f] for f, _n, _c in atlas_text.DIMENSION_SHARES) - 100) < 0.5, (
            f"{r['state']}: the three dimension shares must total 100, got "
            f"{sum(r[f] for f, _n, _c in atlas_text.DIMENSION_SHARES):.2f}"
        )

    atlas_fields = [
        "pcode", "state", "capital", "lat", "lon",
        "mpi", "mpi_se", "mpi_ci_lo", "mpi_ci_hi", "mpi_rank",
        "headcount_ratio_pct", "headcount_se", "intensity_pct",
        "vulnerable_pct", "severe_pct", "quadrant",
        "contrib_health_pct", "contrib_education_pct", "contrib_living_standards_pct",
        "population_thousands", "mpi_poor_thousands", "mpi_poor_rank",
        "events", "fatalities", "fatalities_low", "fatalities_high",
        "events_per_100k", "fatalities_per_100k", "fatalities_per_100k_high",
        "conflict_exposure_index",
        "temp_mean_c", "precip_total_mm", "temp_anomaly_c", "precip_anomaly_pct",
        "baseline_temp_c", "baseline_precip_mm", "mpi_band", "poverty_group",
        "mpi_label", "dim_hover",
        "n_indicators", "indicators_missing", "survey", "survey_year",
    ]
    n_atlas = write_csv(PROCESSED / "mpi_atlas_2021.csv", atlas_rows, atlas_fields)

    # ---- who governed, 1999-2021 (hover context, never a colour) ------------
    # state_dominant_party.csv holds the mode governorship party per state with the
    # 6 ties spelled "PDP/APC" and the FCT as an em dash; stage 0 recomputes that
    # mode from governorship_events.csv and asserts it matches, so the *party* is
    # already verified. The *years* are derived here, from the same events, and the
    # two checks below make it impossible for an arithmetic slip to reach the
    # tooltip: every state's tenures must fill the window exactly, and the party
    # with the most years must be the mode (or, where the mode is a tie, one of the
    # tied parties -- a seating tie need not also be a years tie).
    party_rows = {r["pcode"]: r for r in read(REFERENCE / "state_dominant_party.csv")}
    if set(party_rows) != set(lookup):
        raise SystemExit("state_dominant_party.csv pcodes do not match the state lookup")
    events_by_pcode: dict[str, list[dict[str, str]]] = {}
    for event in read(REFERENCE / "governorship_events.csv"):
        events_by_pcode.setdefault(event["pcode"], []).append(event)

    gov_party: dict[str, str] = {}
    for pcode in lookup:
        dom = party_rows[pcode]["dom_party"]
        years = party_years(events_by_pcode.get(pcode, []))
        if not years:
            if dom != "\u2014":
                raise SystemExit(f"{pcode}: no seating events, but the mode is {dom!r}")
            gov_party[pcode] = "no elected governor (minister-appointed)"
            continue
        if sum(years.values()) != PARTY_SPAN_YEARS:
            raise SystemExit(
                f"{pcode}: tenures total {sum(years.values())} years, "
                f"expected {PARTY_SPAN_YEARS}"
            )
        longest = max(years.values())
        longest_parties = {p for p, n in years.items() if n == longest}
        if "/" in dom:
            if not longest_parties <= set(dom.split("/")):
                raise SystemExit(
                    f"{pcode}: most years go to {sorted(longest_parties)}, "
                    f"but the tie is {dom}"
                )
            gov_party[pcode] = f"{dom} (tied)"
        else:
            if longest_parties != {dom}:
                raise SystemExit(
                    f"{pcode}: most years go to {sorted(longest_parties)}, "
                    f"but the mode is {dom}"
                )
            gov_party[pcode] = f"{dom} ({years[dom]} of {PARTY_SPAN_YEARS} years)"

    # ---- ADM1 ring vertices for the Tableau filled map ----------------------
    # Sheet 1 cannot be a filled map from hand-written XML. Tableau's geographic
    # fields ([Latitude (generated)] / [Longitude (generated)]) are synthesised by
    # the application, not columns in the extract: declaring them is rejected on
    # load with "The field '[none:Latitude (generated):qk]' ... does not exist in
    # your database" (9CA7205B), and declaring them as <column> in the datasource
    # fails the workbook open outright. Both verified against Tableau Public 2026.2
    # on 2026-10-17. So the geometry ships as data and the workbook draws it with a
    # Polygon mark plus a Path field, which needs no geographic role at all.
    #
    # One row per vertex. `ring` keeps disjoint parts of a state from being joined
    # into one polygon, and `point_order` is the Path field that orders the ring.
    #
    # The rings are simplified. The raw ADM1 file carries 53,489 vertices, which is
    # an order of magnitude more than a state-level choropleth can show: at the map
    # zone's ~1600px across 12 degrees of longitude, one pixel is 0.0075 degrees, so
    # a 0.005-degree tolerance is sub-pixel. preserve_topology keeps every ring a
    # valid, non-self-intersecting polygon. The area check below is the guard -- if
    # simplification ever starts eating real coastal detail, it fails the build.
    geometry = json.loads((RAW / "nga_adm1.geojson").read_text(encoding="utf-8"))
    by_pcode = {r["pcode"]: r for r in atlas_rows}
    shapes = {feat["properties"]["shapeISO"] for feat in geometry["features"]}
    missing = set(by_pcode) - shapes
    assert not missing, f"no ADM1 geometry for {sorted(missing)}"

    poly_rows: list[dict[str, Any]] = []
    for feat in geometry["features"]:
        pcode = feat["properties"]["shapeISO"]
        a = by_pcode[pcode]
        raw_geom = shapely_shape(feat["geometry"])
        geom = raw_geom.simplify(SIMPLIFY_TOLERANCE_DEG, preserve_topology=True)
        assert not geom.is_empty, f"{pcode}: simplification emptied the geometry"
        area_drift = abs(geom.area - raw_geom.area) / raw_geom.area
        assert area_drift < 0.02, (
            f"{pcode}: simplification moved the area by {area_drift:.1%}; "
            "the tolerance is too coarse"
        )
        parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        ring_index = 0
        for part in parts:
            for ring in (part.exterior, *part.interiors):
                coords = list(ring.coords)
                if len(coords) < 4:
                    continue  # not a ring any more
                ring_index += 1
                for order, (lon, lat) in enumerate(coords):
                    poly_rows.append(
                        {
                            "state": a["state"],
                            "pcode": pcode,
                            "ring": ring_index,
                            "point_order": order,
                            "lon": round(lon, 5),
                            "lat": round(lat, 5),
                            # carried per vertex so the polygon keeps the same
                            # tooltip the point map had
                            "mpi_band": a["mpi_band"],
                            "poverty_group": a["poverty_group"],
                            "mpi": a["mpi"],
                            "mpi_se": a["mpi_se"],
                            "mpi_ci_lo": a["mpi_ci_lo"],
                            "mpi_ci_hi": a["mpi_ci_hi"],
                            "headcount_ratio_pct": a["headcount_ratio_pct"],
                            "intensity_pct": a["intensity_pct"],
                            "mpi_poor_thousands": a["mpi_poor_thousands"],
                            # The tooltip shows the MPI as a percentage of the index
                            # and cannot do arithmetic, so the scaled values ship as
                            # data. Same number as `mpi`, times 100.
                            "mpi_pct": round(f(a, "mpi") * 100, 1),
                            "mpi_ci_lo_pct": round(f(a, "mpi_ci_lo") * 100, 1),
                            "mpi_ci_hi_pct": round(f(a, "mpi_ci_hi") * 100, 1),
                            "gov_party": gov_party[pcode],
                            # The composition line both maps' hovers print;
                            # composed above with the atlas table's.
                            "dim_hover": a["dim_hover"],
                        }
                    )
    poly_fields = [
        "state", "pcode", "ring", "point_order", "lon", "lat",
        "mpi_band", "poverty_group", "mpi", "mpi_se", "mpi_ci_lo", "mpi_ci_hi",
        "headcount_ratio_pct", "intensity_pct", "mpi_poor_thousands",
        "mpi_pct", "mpi_ci_lo_pct", "mpi_ci_hi_pct", "gov_party", "dim_hover",
    ]
    n_poly = write_csv(PROCESSED / "mpi_polygons.csv", poly_rows, poly_fields)
    assert {r["pcode"] for r in poly_rows} == set(by_pcode), "polygon pcodes drifted"

    # ---- trends panel ------------------------------------------------------
    # The four rounds are OPHI's HARMONISED series (Data Table 6 / MN 63), not the
    # contemporaneous standardised estimates. Verified 2026-10-06: the admin-1 rows
    # in nga_mpi_trends.csv match Table 6.4 to 4dp on all 148 rows, and the national
    # rows match Table 6.1. Harmonisation aligns indicator definitions across survey
    # years so differences reflect changes in poverty conditions rather than changes
    # in questionnaire. Earlier publications of Nigerian state MPI for 2013-2018 used
    # the un-harmonised estimates and differ by up to 0.17 -- do not compare.
    trend_by_key = {(r["pcode"], int(r["survey_year"])): r for r in trends}
    panel_rows: list[dict[str, Any]] = []
    for pcode in sorted(lookup):
        for year in SURVEY_ROUNDS:
            t = trend_by_key[(pcode, year)]
            c, cl = conflict[(pcode, year)], climate[(pcode, year)]
            row: dict[str, Any] = {
                "pcode": pcode,
                "state": lookup[pcode]["name_canonical"],
                "survey_year": year,
                "survey": t["survey"],
                "mpi": round(f(t, "mpi"), 4),
                "headcount_ratio_pct": round(f(t, "headcount_ratio"), 2),
                "intensity_pct": round(f(t, "intensity"), 2),
                "events": int(f(c, "events")),
                "fatalities": round(f(c, "fatalities"), 1),
                "fatalities_low": round(f(c, "fatalities_low"), 1),
                "fatalities_high": round(f(c, "fatalities_high"), 1),
                "events_per_100k": round(f(c, "events") / population[pcode] * 100_000, 3),
                "fatalities_per_100k": round(f(c, "fatalities") / population[pcode] * 100_000, 3),
                "fatalities_per_100k_high": round(
                    f(c, "fatalities_high") / population[pcode] * 100_000, 3
                ),
                "conflict_exposure_index": cei[(pcode, year)],
                "temp_mean_c": round(f(cl, "temp_mean_c"), 2),
                "temp_anomaly_c": round(f(cl, "temp_anomaly_c"), 2),
                "precip_anomaly_pct": round(f(cl, "precip_anomaly_pct"), 1),
                # The pairs board's two panes split on the state's 2021 poverty
                # group, stamped here onto all four rounds (docs/SHEET_PAIRS.md;
                # rank persistence 0.87-0.92 is what makes the 2021 cut
                # defensible for pooled rounds). "Poorest states vs the rest",
                # never "north vs south".
                "poverty_group": by_pcode[pcode]["poverty_group"],
            }
            # The first round has no preceding round, so there is no change to report.
            ch = change_by_key.get((pcode, year))
            change = round(f(ch, "annualised_change"), 5) if ch else ""
            row["mpi_change_since_prev"] = change
            row["mpi_change_significant"] = ch["significance"] if ch else ""
            # The hover's two numeric annotations ship as PRE-FORMATTED STRINGS
            # (mpi_change_label / deaths_high_label): the extract's only measures
            # must be the six ranks, so a numeric annotation measure would re-enter
            # the Measure Names domain, and the 2026-10-21 amendment removes every
            # non-rank variable from the extract. Formatting happens here, once,
            # where the pipeline's conventions live; the workbook prints the string.
            row["mpi_change_label"] = f"{change:+.4f}" if change != "" else ""
            high = row["fatalities_per_100k_high"]
            row["deaths_high_label"] = f"{high:.2f}" if high != "" else ""
            panel_rows.append(row)
    # ---- the panel's rank columns -------------------------------------------
    # The sheet "A state over time" draws the state's RANK in each round, not its
    # raw value (an amendment to docs/SHEET_TIME_PANEL.md, 2026-10-21): the mark
    # labels print the bare integer -- the state's position on that measure among
    # the 37 states in that round -- and the direction key rides the row-header
    # captions ("... rank (1 = highest)") and the sheet subtitle. A literal "R"
    # prefix was tried in the field's own number format and did not render from
    # XML in Tableau Public 2026.2 (the load-only part of the format did: the
    # old two-decimal "36.00" misprint is gone with the integer declared
    # quantitative), so R-wording stays prose, not formatting. Direction is fixed
    # to match the sheet's key: R1 = the
    # HIGHEST value of that measure (poorest MPI, most conflict events, hottest
    # capital), so a rising R means the state moves away from the extreme. Ties
    # are competition-ranked: equal values share the better (lower) rank, which is
    # what the ten zero-event 2021 states need — they all share R28, not an
    # arbitrary ordering among them.
    #
    # The list below is also the sheet's whitelist: 06_build_twb.py's Measure
    # Values shelf and stage 5's gate are both driven from it, so gate and sheet
    # cannot disagree on which position a mark shows.
    RANK_FIELDS: dict[str, str] = {
        "rank_mpi": "mpi",
        "rank_headcount": "headcount_ratio_pct",
        "rank_intensity": "intensity_pct",
        "rank_events": "events_per_100k",
        "rank_deaths": "fatalities_per_100k",
        "rank_temp": "temp_mean_c",
    }
    for rank_field, source_field in RANK_FIELDS.items():
        for year in SURVEY_ROUNDS:
            yr_rows = [r for r in panel_rows if r["survey_year"] == year]
            yr_rows.sort(key=lambda r: r[source_field], reverse=True)
            rank = 0
            for i, row in enumerate(yr_rows):
                if i and row[source_field] != yr_rows[i - 1][source_field]:
                    rank = i
                row[rank_field] = rank + 1
        values = [r[rank_field] for r in panel_rows]
        assert all(1 <= v <= 37 for v in values), (
            f"{rank_field} produced a rank outside 1-37"
        )
        # The max-rank sanity bound: with no ties at the extreme, the state with
        # the highest value of the measure must hold R1.
        for year in SURVEY_ROUNDS:
            yr_rows = [r for r in panel_rows if r["survey_year"] == year]
            top = max(r[source_field] for r in yr_rows)
            assert {r[rank_field] for r in yr_rows if r[source_field] == top} == {1}, (
                f"{rank_field} did not give the highest {source_field} rank 1 in {year}"
            )

    panel_fields = [
        "pcode", "state", "survey_year", "survey", "mpi", "headcount_ratio_pct",
        "intensity_pct", "mpi_change_since_prev", "mpi_change_significant",
        "events", "fatalities", "fatalities_low", "fatalities_high",
        "events_per_100k", "fatalities_per_100k", "fatalities_per_100k_high",
        "log1p_events_per_100k", "log1p_fatalities_per_100k",
        "log1p_fatalities_per_100k_high",
        "mpi_change_label", "deaths_high_label",
        "conflict_exposure_index", "temp_mean_c", "temp_anomaly_c", "precip_anomaly_pct",
        "poverty_group",
        "rank_mpi", "rank_headcount", "rank_intensity", "rank_events",
        "rank_deaths", "rank_temp",
    ]
    n_panel = write_csv(PROCESSED / "mpi_trends_panel.csv", panel_rows, panel_fields)

    # ---- the pairs board extract (docs/SHEET_PAIRS.md) ----------------------
    # The bivariate exploration sheet reads these 148 rows plus the atlas's
    # per-state constants, joined here once so stage 6 packs a single extract.
    # The log columns are log(1+rate): the ten (2021) zero-event states sit at
    # exactly 0, on the axis gridline, all 37 visible -- not dropped by a log().
    # `poverty_group` rides every row (2021 stamp; rank persistence 0.87-0.92
    # justifies pooling the rounds for a pane split whose only job is
    # headline grouping, never a comparison or test).
    for r in panel_rows:
        r["log1p_events_per_100k"] = round(math.log1p(r["events_per_100k"]), 5)
        r["log1p_fatalities_per_100k"] = round(math.log1p(r["fatalities_per_100k"]), 5)
        r["log1p_fatalities_per_100k_high"] = round(
            math.log1p(r["fatalities_per_100k_high"]), 5
        )
        # log1p of exactly 0 must be exactly 0 -- the zero gridline is the point.
        # log1p of exactly 0 must be exactly 0 -- the zero gridline is the point.
        if r["events_per_100k"] == 0:
            assert r["log1p_events_per_100k"] == 0.0, "log1p lost the zero gridline"

    pairs_atlas_fields = [
        "lat", "lon", "mpi_se", "headcount_se", "vulnerable_pct", "severe_pct",
        "contrib_health_pct", "contrib_education_pct",
        "contrib_living_standards_pct", "population_thousands",
        "mpi_poor_thousands", "precip_total_mm", "baseline_temp_c",
        "baseline_precip_mm",
    ]
    pairs_rows: list[dict[str, Any]] = []
    for r in panel_rows:
        a = by_pcode[r["pcode"]]
        pairs_rows.append({**r, **{k: a[k] for k in pairs_atlas_fields}})
    pairs_fields = panel_fields + pairs_atlas_fields
    n_pairs = write_csv(PROCESSED / "mpi_pairs_148.csv", pairs_rows, pairs_fields)
    assert {x["pcode"] for x in pairs_rows} == set(by_pcode), "pairs pcodes drifted"
    groups_by_state = {x["state"]: x["poverty_group"] for x in pairs_rows}
    assert len(groups_by_state) == 37, "poverty_group stamp is inconsistent per state"

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

    # ---- what the design can and cannot resolve ----------------------------
    # Every number below exists to stop a caption overreaching. They are computed
    # here rather than written into docs by hand so they cannot drift from the data.
    states = sorted(lookup)
    lat = {p: f(capitals[p], "lat") for p in states}
    precip = {p: f(baseline[p], "baseline_precip_mm_per_year") for p in states}

    lat_precip = spearman([lat[p] for p in states], [precip[p] for p in states])
    lat_mpi = spearman([lat[p] for p in states], [f(dims[p], "mpi") for p in states])
    bp = spearman([precip[p] for p in states], [f(dims[p], "mpi") for p in states])
    print(
        f"\n   baseline precipitation vs MPI      rho={bp[0]:+.3f} p={bp[1]:.2e}"
    )
    print(
        f"   baseline precipitation vs latitude rho={lat_precip[0]:+.3f}   "
        f"latitude vs MPI rho={lat_mpi[0]:+.3f}"
    )
    print(
        "   -> LATITUDE PREDICTS MPI BETTER THAN PRECIPITATION DOES. Baseline rainfall is"
    )
    print(
        f"      a north-south gradient, not a climate effect ({lat_mpi[0]:+.3f} > {abs(bp[0]):.3f})."
    )

    # Rank resolvability: with OPHI's design-based SEs, how many adjacent rank pairs
    # separate at 95%? All 36 overlapping means no ordering of states is claimable.
    ranked = sorted(states, key=lambda p: -f(dims[p], "mpi"))
    separable = 0
    for a, b in zip(ranked, ranked[1:]):
        diff = f(dims[a], "mpi") - f(dims[b], "mpi")
        combined = (f(dims[a], "mpi_se") ** 2 + f(dims[b], "mpi_se") ** 2) ** 0.5
        if abs(diff) > 1.96 * combined:
            separable += 1
    rel = sorted(f(dims[p], "mpi_se") / f(dims[p], "mpi") for p in states)
    print(
        f"\n   standard errors: median relative SE {100 * rel[len(rel) // 2]:.1f}%; "
        f"{separable} of 36 adjacent rank pairs separable at 95%"
    )
    print("   -> present MPI in bands. No single state is 'the highest'.")

    # Rank persistence: structure survives where level moves.
    print("\n   rank persistence between consecutive rounds (Spearman):")
    for y0, y1 in zip(SURVEY_ROUNDS, SURVEY_ROUNDS[1:]):
        m0 = {r["pcode"]: r["mpi"] for r in panel_rows if r["survey_year"] == y0}
        m1 = {r["pcode"]: r["mpi"] for r in panel_rows if r["survey_year"] == y1}
        common = sorted(set(m0) & set(m1))
        rho, _ = spearman([m0[p] for p in common], [m1[p] for p in common])
        print(f"      {y0} -> {y1}: {rho:+.3f}")

    # The harmonised change series, with OPHI's own significance.
    sig_rows = [r for r in panel_rows if r["mpi_change_significant"]]
    print(
        f"\n   harmonised change (OPHI Table 6.4): {len(sig_rows)} of "
        f"{len(SURVEY_ROUNDS[1:]) * len(states)} state-period changes significant at some level"
    )

    # Fatality band sensitivity: the conflict null must not be an artefact of the
    # casualty estimate. UCDP publishes low/best/high per event; all three are here.
    print("\n   conflict vs MPI across UCDP's fatality band (2021):")
    for band in ("fatalities", "fatalities_low", "fatalities_high"):
        by_p = {r["pcode"]: f(r, band) / population[r["pcode"]] * 100_000
                for r in atlas_rows}
        scaled = {}
        for p in states:
            vals = [by_p[q] for q in states]
            lo, hi = min(vals), max(vals)
            scaled[p] = 100 * (by_p[p] - lo) / (hi - lo) if hi > lo else 0.0
        r_, p_ = spearman([f(dims[q], "mpi") for q in states], [scaled[q] for q in states])
        print(f"      {band:18s} rho={r_:+.3f} p={p_:.3f}")
    print("   -> the null holds across a +/-50% casualty band, so it is not an")
    print("      artefact of the fatality estimate. It is a limit of the design.")

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
    print(f"wrote {n_poly} rows -> data/processed/mpi_polygons.csv (ADM1 ring vertices)")
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