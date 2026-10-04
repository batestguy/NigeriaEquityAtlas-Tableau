"""Stage 2 -- acquire conflict events and attribute them to states.

Source: UCDP Georeferenced Event Dataset (GED) for Nigeria, distributed on HDX
under CC BY-IGO. The spec asked for ACLED, but ACLED is not obtainable here: the
API host does not resolve on this network and the HDX copy of ACLED's Nigeria
weekly file is aggregated country-year/month only, which cannot support a
per-state index. UCDP is open, needs no key, is georeferenced to the event, and
covers 1990-2024 so it spans all four MPI survey rounds.

Attribution runs in three passes, each recorded in the output so the method is
auditable rather than assumed:

  1. adm_1 name matched against the spelling table in state_lookup.csv
  2. if the name is absent or unrecognised, fall back to a point-in-polygon test
     against the ADM1 geometry using the event's own coordinates
  3. anything still unattributed is written out for inspection, never dropped

The known traps are handled explicitly: FCT is spelled three different ways, 46
events carry a blank adm_1, and one event sits in "Gongola state", a province
dissolved in 1991 whose territory is now Adamawa.
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from typing import Any

from shapely.geometry import Point, shape

from common import INTERIM, RAW, download, load_boundaries, read_lookup, write_csv

UCDP_NGA = (
    "https://data.humdata.org/dataset/a2260243-108d-4df4-a7e6-a010bcbb553f/"
    "resource/9e2fcefc-24ab-4903-88fd-fa089c8edc2b/download/conflict_data_nga.csv"
)

# One event is attributed to Gongola, an administrative unit abolished in 1991 and
# since divided between Adamawa and Taraba. Attributed to Adamawa with the count
# surfaced in docs/data_quality.md rather than silently reassigned.
OBSOLETE_UNITS = {"Gongola state": "NG-AD"}


def _f(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def main() -> int:
    download(UCDP_NGA, RAW / "ucdp_ged_nga.csv")
    lookup = read_lookup()
    boundaries = load_boundaries()
    polys = {iso: shape(feat["geometry"]) for iso, feat in boundaries.items()}

    raw_to_pcode = {m["ucdp_adm1_raw"]: p for p, m in lookup.items()}
    name_to_pcode = {m["name_canonical"]: p for p, m in lookup.items()}

    events: list[dict[str, Any]] = []
    with (RAW / "ucdp_ged_nga.csv").open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            if (row.get("country") or "").strip() != "Nigeria":
                continue
            if (row.get("type_of_violence") or "").strip() not in {"1", "2", "3"}:
                continue
            adm1 = (row.get("adm_1") or "").strip()
            events.append(
                {
                    "event_id": row.get("id", ""),
                    "year": int(row["year"]),
                    "type": int(row["type_of_violence"]),
                    "adm1_raw": adm1,
                    "lat": _f(row.get("latitude")) if row.get("latitude") else None,
                    "lon": _f(row.get("longitude")) if row.get("longitude") else None,
                    "fatalities": _f(row.get("best")),
                    "fatalities_high": _f(row.get("high")),
                    "fatalities_low": _f(row.get("low")),
                }
            )
    print(f"UCDP events for Nigeria (types 1-3): {len(events)}")

    # ---- attribute each event ----------------------------------------------
    unattributed: list[dict[str, Any]] = []
    method_counts: dict[str, int] = defaultdict(int)
    per_event: list[dict[str, Any]] = []
    for ev in events:
        pcode = raw_to_pcode.get(ev["adm1_raw"]) or name_to_pcode.get(ev["adm1_raw"])
        method = "adm1_name"
        if pcode is None and ev["adm1_raw"] in OBSOLETE_UNITS:
            pcode, method = OBSOLETE_UNITS[ev["adm1_raw"]], "obsolete_unit"
        if pcode is None:
            pcode, method = None, "point_in_polygon"
            if ev["lat"] is not None and ev["lon"] is not None:
                pt = Point(ev["lon"], ev["lat"])
                for iso, poly in polys.items():
                    if poly.covers(pt):
                        pcode = iso
                        break
        if pcode is None:
            unattributed.append(ev)
            method = "unattributed"
        method_counts[method] += 1
        if pcode:
            per_event.append({**ev, "pcode": pcode, "attribution_method": method})

    print("attribution methods: " + ", ".join(f"{k}={v}" for k, v in sorted(method_counts.items())))
    if unattributed:
        print(f"WARNING: {len(unattributed)} events could not be attributed; see the audit file")
        for ev in unattributed[:5]:
            print(f"   id={ev['event_id']} adm1={ev['adm1_raw']!r} year={ev['year']}")

    # ---- aggregate to state x year (long format) ----------------------------
    agg: dict[tuple[str, int], dict[str, float]] = defaultdict(
        lambda: {"events": 0.0, "fatalities": 0.0, "fatalities_high": 0.0, "fatalities_low": 0.0}
    )
    for ev in per_event:
        cell = agg[(ev["pcode"], ev["year"])]
        cell["events"] += 1
        cell["fatalities"] += ev["fatalities"]
        cell["fatalities_high"] += ev["fatalities_high"]
        cell["fatalities_low"] += ev["fatalities_low"]

    years = sorted({y for _, y in agg})
    print(f"event years: {min(years)}-{max(years)}")

    # Every state must appear in every year, including the 9 states with no 2021
    # events. A missing row would render as a hole on the map, so zeros are written
    # explicitly and distinguish "no events" from "not measured".
    long_rows: list[dict[str, Any]] = []
    for pcode in sorted(lookup):
        for year in years:
            cell = agg.get((pcode, year), None)
            long_rows.append(
                {
                    "pcode": pcode,
                    "state": lookup[pcode]["name_canonical"],
                    "year": year,
                    "events": int(cell["events"]) if cell else 0,
                    "fatalities": round(cell["fatalities"], 1) if cell else 0.0,
                    "fatalities_high": round(cell["fatalities_high"], 1) if cell else 0.0,
                    "fatalities_low": round(cell["fatalities_low"], 1) if cell else 0.0,
                }
            )

    # ---- gates --------------------------------------------------------------
    covered = {p for p, _ in agg}
    missing_states = sorted(set(lookup) - covered)
    if missing_states:
        raise SystemExit(f"states with no conflict events in any year: {missing_states}")

    total_events = sum(r["events"] for r in long_rows)
    total_fatal = sum(r["fatalities"] for r in long_rows)
    print(f"coverage: all {len(lookup)} states present across {len(years)} years "
          f"({len(long_rows)} rows, {total_events} events, {total_fatal:.0f} fatalities)")

    round_years = (2013, 2016, 2018, 2021)
    print("MPI survey rounds -- 2021 event counts per state:")
    for y in round_years:
        rows = [r for r in long_rows if r["year"] == y]
        zero = [r["state"] for r in rows if r["events"] == 0]
        print(f"   {y}: {sum(r['events'] for r in rows):4d} events, {len(zero):2d} states with none"
              + (f" ({', '.join(zero[:5])})" if zero else ""))

    n = write_csv(
        INTERIM / "conflict_state_year.csv",
        long_rows,
        ["pcode", "state", "year", "events", "fatalities", "fatalities_high", "fatalities_low"],
    )
    write_csv(
        INTERIM / "conflict_events_attributed.csv",
        per_event,
        ["event_id", "pcode", "year", "type", "adm1_raw", "lat", "lon",
         "fatalities", "attribution_method"],
    )
    write_csv(
        INTERIM / "conflict_unattributed.csv",
        unattributed,
        ["event_id", "year", "type", "adm1_raw", "lat", "lon", "fatalities"],
    )
    print(f"\nwrote {n} rows -> data/interim/conflict_state_year.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())