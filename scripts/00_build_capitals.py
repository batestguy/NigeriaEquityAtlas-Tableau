"""Rebuild data/reference/state_capitals.csv from the GeoNames gazetteer.

Why not geocoding: the capital coordinates typed from memory were wrong (one had
latitude and longitude transposed, and three had outright wrong positions), and
OpenStreetMap geocoding proved unreliable for Nigeria -- it returned a *different*
place named "Lafia" that lies in Adamawa, and could not resolve four major cities
at all. GeoNames tags each admin-1 seat with a dedicated feature code, so the
match is a data fact rather than a search result:

    PPLC = capital of a first-order administrative division
    PPLA = seat of a first-order administrative division

Those 37 Nigerian features map one-to-one onto our canonical capital list by
name, and each matched coordinate is additionally required to fall inside its own
ADM1 polygon. Both checks must pass, so a renamed or relocated capital fails
loudly instead of silently attaching the wrong climate to a state.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from shapely.geometry import Point, shape

from common import RAW, REFERENCE, download, load_boundaries, read_lookup, write_csv

CITIES5000 = "https://download.geonames.org/export/dump/cities5000.zip"
GEOBOUNDARIES_ADM1 = (
    "https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/NGA/ADM1/"
    "geoBoundaries-NGA-ADM1.geojson"
)
ADMIN1_SEAT_CODES = ("PPLC", "PPLA")


def load_admin1_seats(zip_path: Path) -> dict[str, dict[str, str]]:
    """Return Nigeria's admin-1 seats from the GeoNames dump, keyed by place name."""
    with zipfile.ZipFile(zip_path) as zf:
        raw = zf.read("cities5000.txt").decode("utf-8")
    seats: dict[str, dict[str, str]] = {}
    for line in raw.splitlines():
        f = line.split("\t")
        if len(f) < 15 or f[8] != "NG" or f[7] not in ADMIN1_SEAT_CODES:
            continue
        seats[f[1].strip().lower()] = {
            "geonameid": f[0],
            "name": f[1],
            "lat": f[4],
            "lon": f[5],
            "feature_code": f[7],
            "admin1": f[10],
            "population": f[14],
        }
    return seats


def main() -> int:
    download(CITIES5000, RAW / "geonames_cities5000.zip")
    download(GEOBOUNDARIES_ADM1, RAW / "nga_adm1.geojson")

    lookup = read_lookup()
    boundaries = load_boundaries()
    seats = load_admin1_seats(RAW / "geonames_cities5000.zip")
    print(f"GeoNames: {len(seats)} Nigerian admin-1 seats")

    rows: list[dict[str, str]] = []
    log: list[dict[str, str]] = []
    problems: list[str] = []

    for pcode, meta in sorted(lookup.items()):
        capital = meta["capital"]
        seat = seats.get(capital.strip().lower())
        if seat is None:
            problems.append(f"{pcode} {meta['name_canonical']}: no GeoNames admin-1 seat named {capital!r}")
            continue
        pt = Point(float(seat["lon"]), float(seat["lat"]))
        if not shape(boundaries[pcode]["geometry"]).covers(pt):
            problems.append(
                f"{pcode} {meta['name_canonical']}: {capital} seat {seat['lat']},{seat['lon']} "
                f"falls outside its own ADM1 polygon"
            )
            continue
        rows.append(
            {
                "pcode": pcode,
                "capital": capital,
                "lat": f"{float(seat['lat']):.4f}",
                "lon": f"{float(seat['lon']):.4f}",
            }
        )
        log.append(
            {
                "pcode": pcode,
                "state": meta["name_canonical"],
                "capital": capital,
                "geonameid": seat["geonameid"],
                "feature_code": seat["feature_code"],
                "geonames_admin1": seat["admin1"],
                "population": seat["population"],
                "lat": rows[-1]["lat"],
                "lon": rows[-1]["lon"],
            }
        )
        print(
            f"  [ok] {pcode} {meta['name_canonical']:12} {capital:14}"
            f" -> {rows[-1]['lat']},{rows[-1]['lon']}  [{seat['feature_code']}]"
        )

    if problems or len(rows) != len(lookup):
        print("\nFAILED:")
        for p in problems:
            print("  -", p)
        print(f"  matched {len(rows)} of {len(lookup)}")
        return 1

    n = write_csv(REFERENCE / "state_capitals.csv", rows, ["pcode", "capital", "lat", "lon"])
    write_csv(
        REFERENCE / "capitals_source.csv",
        log,
        ["pcode", "state", "capital", "geonameid", "feature_code", "geonames_admin1", "population", "lat", "lon"],
    )
    print(f"\nwrote {n} capitals to data/reference/state_capitals.csv (+ capitals_source.csv)")
    return 0


if __name__ == "__main__":
    sys.exit(main())