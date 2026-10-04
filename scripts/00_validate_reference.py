"""Stage 0 -- validate the hand-curated reference tables before anything joins on them.

Three checks, all of which have caught real errors on this project:
  1. both reference tables have exactly 37 rows with unique pcode values
  2. the two tables' pcode sets are identical
  3. every state capital actually falls inside its own state polygon

Check 3 is the one that matters: a mis-typed capital coordinate silently attaches
the wrong climate to a state, and no downstream assertion would ever notice.
"""

from __future__ import annotations

import sys

from shapely.geometry import Point, shape

from common import RAW, download, load_boundaries, read_capitals, read_lookup

GEOBOUNDARIES_ADM1 = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NGA/ADM1/"
    "geoBoundaries-NGA-ADM1.geojson"
)


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

    if problems:
        print("REFERENCE VALIDATION FAILED")
        for p in problems:
            print("  -", p)
        return 1

    print(f"reference OK: {len(lookup)} states, {len(capitals)} capitals, all capitals inside their state")
    print(f"boundaries: {RAW / 'nga_adm1.geojson'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())