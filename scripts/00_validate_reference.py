"""Stage 0 -- validate the hand-curated reference tables before anything joins on them.

Four checks, the first three of which have caught real errors on this project:
  1. both reference tables have exactly 37 rows with unique pcode values
  2. the two tables' pcode sets are identical
  3. every state capital actually falls inside its own state polygon
  4. governorship_events.csv reproduces the audited mode party in
     state_dominant_party.csv for all 36 governed states, and FCT has no events

Check 3 is the one that matters: a mis-typed capital coordinate silently attaches
the wrong climate to a state, and no downstream assertion would ever notice.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter

from shapely.geometry import Point, shape

from common import RAW, REFERENCE, download, load_boundaries, read_capitals, read_lookup

FCT = "NG-FC"
EVENT_TYPES = {"cycle", "off-cycle", "court", "rerun"}

GEOBOUNDARIES_ADM1 = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NGA/ADM1/"
    "geoBoundaries-NGA-ADM1.geojson"
)


def check_governorship_events(lookup: dict[str, dict[str, str]]) -> list[str]:
    """Gate 4: the machine-readable event matrix must reproduce the audited mode labels.

    Recomputes the mode governorship party per state from governorship_events.csv
    (counting rule in docs/dominant_party.md: mode of as-won labels, ties
    `/`-joined in order of first appearance in the event file) and compares it
    with dom_party in state_dominant_party.csv. FCT must carry no events. Stage 8
    reads the event file, so a transcription error here would reach the result.
    """
    problems: list[str] = []
    with (REFERENCE / "governorship_events.csv").open(newline="", encoding="utf-8") as fh:
        events = list(csv.DictReader(fh))
    with (REFERENCE / "state_dominant_party.csv").open(newline="", encoding="utf-8-sig") as fh:
        dominant = {r["pcode"]: r for r in csv.DictReader(fh)}

    by_state: dict[str, list[dict[str, str]]] = {}
    for ev in events:
        if ev["pcode"] not in lookup:
            problems.append(f"governorship event with unknown pcode {ev['pcode']!r}")
            continue
        if ev["event_type"] not in EVENT_TYPES:
            problems.append(f"{ev['pcode']} {ev['year']}: bad event_type {ev['event_type']!r}")
        if ev["seated_year"] != ev["year"] and not ev["source_note"].strip():
            problems.append(f"{ev['pcode']} {ev['year']}: seated_year differs but has no source")
        by_state.setdefault(ev["pcode"], []).append(ev)

    if FCT in by_state:
        problems.append(f"FCT has {len(by_state[FCT])} governorship events; it must have none")
    if set(dominant) != set(lookup):
        problems.append("state_dominant_party.csv pcodes do not match state_lookup.csv")

    for pcode in sorted(set(lookup) - {FCT}):
        evs = by_state.get(pcode, [])
        counts = Counter(ev["party"] for ev in evs)
        if not counts:
            problems.append(f"{pcode}: no governorship events")
            continue
        top = max(counts.values())
        # Counter preserves first-insertion order, which is the event file's order.
        mode = "/".join(p for p, n in counts.items() if n == top)
        expected = dominant.get(pcode, {}).get("dom_party")
        if mode != expected:
            problems.append(
                f"{pcode}: mode party from governorship_events.csv is {mode!r} "
                f"but state_dominant_party.csv says {expected!r}"
            )
        expected_n = dominant.get(pcode, {}).get("events_n")
        if expected_n is not None and int(expected_n) != len(evs):
            problems.append(f"{pcode}: {len(evs)} events, state_dominant_party.csv says {expected_n}")
    return problems


def main() -> int:
    lookup = read_lookup()
    capitals = read_capitals()
    download(GEOBOUNDARIES_ADM1, RAW / "nga_adm1.geojson")

    problems: list[str] = []

    missing_caps = set(lookup) - set(capitals)
    extra_caps = set(capitals) - set(lookup)
    if missing_caps:
        problems.append(f"states with no capital row: {sorted(missing_caps)}")
    if extra_caps:
        problems.append(f"capital rows with no state: {sorted(extra_caps)}")

    # Every geoboundaries spelling must match what we recorded in the lookup, so a
    # boundary refresh cannot silently change the geometry we join to.
    boundaries = load_boundaries()
    for iso, feat in boundaries.items():
        shape_name = feat["properties"]["shapeName"]
        recorded = lookup.get(iso, {}).get("geoboundaries_name")
        if recorded != shape_name:
            problems.append(
                f"boundary name drift for {iso}: file has {shape_name!r}, lookup has {recorded!r}"
            )

    # Point-in-polygon: each capital must land in the polygon of its own state.
    for iso, row in capitals.items():
        feat = boundaries.get(iso)
        if feat is None:
            problems.append(f"{iso}: no boundary feature")
            continue
        poly = shape(feat["geometry"])
        pt = Point(float(row["lon"]), float(row["lat"]))
        if not poly.covers(pt):
            problems.append(
                f"{iso} ({row['capital']}) capital {row['lat']},{row['lon']} "
                f"is NOT inside its own state polygon"
            )
        expected = lookup.get(iso, {}).get("capital")
        if row["capital"] != expected:
            problems.append(
                f"{iso}: capital name {row['capital']!r} does not match "
                f"state_lookup capital {expected!r}"
            )

    problems.extend(check_governorship_events(lookup))

    if problems:
        print("REFERENCE VALIDATION FAILED")
        for p in problems:
            print("  -", p)
        return 1

    print(f"reference OK: {len(lookup)} states, {len(capitals)} capitals, all capitals inside their state")
    print(f"boundaries: {RAW / 'nga_adm1.geojson'}")
    print("governorship events: mode party matches state_dominant_party.csv for 36 states; FCT has none")
    return 0


if __name__ == "__main__":
    sys.exit(main())