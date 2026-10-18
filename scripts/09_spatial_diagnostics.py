"""Stage 9 -- the spatial diagnostic for sheet 1's map.

Question: do poor states sit next to poor states? The specification was frozen in
docs/spatial_preregistration.md *before* this file existed: the statistic, the
weights, the permutation count and seed, the correction, the decision rule and the
wording. Nothing here chooses any of them.

This is a thin, strict wrapper around scripts/spatial_diagnostics.R, because this
pipeline's Python has no libpysal/esda while spdep and spatialreg are the reference
implementations. R writes the raw tables into data/interim; everything a reader
sees is checked, verified and written here:

  data/processed/spatial_diagnostics.csv    37 rows: lag, neighbourhood type, local p
  data/processed/spatial_global.csv         the global statistics, looked up by key
  data/processed/spatial_polygons.csv       the map's ring vertices + those types
  docs/spatial_analysis.md                  section 3 only (under "## 3. Result")

The independent checks matter more than the wrapper. Neighbours, the spatial lag,
the four neighbourhood types and Moran's I are all recomputed in Python from the raw
GeoJSON and the atlas and compared against R's output, so this stage fails if the
two implementations ever disagree rather than publishing whichever ran last.

The four lines the sheet carries are frozen text in scripts/atlas_text.py. This
stage asserts that the figures those lines state are still the figures in the data,
so the wording and the numbers cannot drift apart silently.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from datetime import date, timezone, datetime
from pathlib import Path

import atlas_text
from common import (
    DOCS,
    INTERIM,
    N_STATES,
    PROCESSED,
    RAW,
    REPO_ROOT,
    spatial_context_line,
    write_csv,
)

ATLAS = PROCESSED / "mpi_atlas_2021.csv"
POLY = PROCESSED / "mpi_polygons.csv"
R_SCRIPT = REPO_ROOT / "scripts" / "spatial_diagnostics.R"
GEOJSON = RAW / "nga_adm1.geojson"

R_STATE = INTERIM / "spatial_diagnostics.csv"
R_GLOBAL = INTERIM / "spatial_global.csv"
R_META = INTERIM / "spatial_weights_meta.csv"

OUT_STATE = PROCESSED / "spatial_diagnostics.csv"
OUT_GLOBAL = PROCESSED / "spatial_global.csv"
OUT_POLY = PROCESSED / "spatial_polygons.csv"
NOTE = DOCS / "spatial_analysis.md"

# Appended to the polygon table's own columns, in this order: the cluster map's
# extract is built from the joined file, and stage 6 checks the packaged schema
# positionally, so the order here and SPATIAL_POLY_COLUMNS in stage 6 must agree.
POLY_SPATIAL_FIELDS = ["spatial_group", "spatial_lag_mpi_pct", "neighbours"]

STATE_FIELDS = [
    "pcode", "state", "lat", "mpi", "mpi_pct", "neighbours",
    "spatial_lag_mpi", "spatial_lag_mpi_pct", "spatial_quadrant", "spatial_group",
    "lisa_i", "lisa_z", "lisa_p", "lisa_p_bonferroni", "lisa_p_by", "run_date",
]
GLOBAL_FIELDS = ["key", "kind", "short", "statistic", "value", "p", "nsim", "n",
                 "note", "run_date"]

TOL = 1e-6


def find_rscript() -> str:
    """Rscript on PATH, else the interpreter ENVIRONMENTS.md records for this machine."""
    found = shutil.which("Rscript")
    if found:
        return found
    fallback = Path("C:/Program Files/R/R-4.5.2/bin/Rscript.exe")
    if fallback.exists():
        return str(fallback)
    raise SystemExit("Rscript not found; install R or put it on PATH (ENVIRONMENTS.md s3)")


def run_r() -> None:
    for path in (ATLAS, R_SCRIPT, GEOJSON):
        if not path.exists():
            raise SystemExit(f"missing {path}")
    print(f"running {R_SCRIPT.name} ...")
    done = subprocess.run(
        [find_rscript(), "--vanilla", str(R_SCRIPT), str(REPO_ROOT)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    if done.returncode != 0:
        raise SystemExit(f"spatial_diagnostics.R failed (exit {done.returncode}):\n{done.stderr}")
    for line in (done.stdout or "").splitlines():
        print(f"  {line}")
    for path in (R_STATE, R_GLOBAL, R_META):
        if not path.exists():
            raise SystemExit(f"R did not write {path}")


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh)]


def adjacency() -> dict[str, set[str]]:
    """Queen contiguity, recomputed from the raw GeoJSON.

    Two states are neighbours when they share at least one boundary vertex, which is
    the rule spdep applies; coordinates are rounded to 6dp so that float noise in the
    file cannot break a shared corner. This reproduces R's neighbour counts for all
    37 states -- which is the point of computing it twice.
    """
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    points: dict[str, set[tuple[float, float]]] = {}
    for feature in gj["features"]:
        pcode = feature["properties"]["shapeISO"]
        geom = feature["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        pts: set[tuple[float, float]] = set()
        for poly in polys:
            for ring in poly:
                for point in ring:
                    pts.add((round(point[0], 6), round(point[1], 6)))
        points[pcode] = pts
    return {
        p: {q for q, other in points.items() if q != p and (points[p] & other)}
        for p in points
    }


def morans_i(values: list[float], neighbours: dict[str, set[str]], order: list[str]) -> float:
    """Moran's I under row-standardised weights, from the definition.

    I = (n / S0) * (z' W z) / (z' z). Row-standardisation makes every row sum to 1, so
    S0 = n and I is the slope of the regression of the spatial lag on the value, both
    centred -- which is why the scatter on the sheet has this number as its slope.
    """
    n = len(order)
    mean = sum(values) / n
    z = {p: v - mean for p, v in zip(order, values)}
    numer = 0.0
    for p in order:
        w = 1.0 / len(neighbours[p])
        numer += z[p] * sum(w * z[q] for q in neighbours[p])
    return numer / sum(v * v for v in z.values())


def verify(rows: list[dict[str, str]], atlas: list[dict[str, str]],
           adj: dict[str, set[str]], i_r: float) -> None:
    """Recompute everything stage 9 can and compare with R."""
    mpi = {r["pcode"]: float(r["mpi"]) for r in atlas}
    order = [r["pcode"] for r in atlas]
    by_pcode = {r["pcode"]: r for r in rows}

    assert len(rows) == N_STATES, f"expected {N_STATES} states, got {len(rows)}"
    assert set(by_pcode) == set(order), "the spatial table and the atlas cover different states"

    for pcode in order:
        want = int(by_pcode[pcode]["neighbours"])
        assert want > 0, f"{pcode} has no neighbour; it would drop out of every statistic"
        assert len(adj[pcode]) == want, (
            f"{pcode}: python adjacency finds {len(adj[pcode])} neighbours, R found "
            f"{want} -- the two weight matrices disagree, so nothing here is comparable"
        )

    mean_mpi = sum(mpi.values()) / len(order)
    for pcode in order:
        lag = sum(mpi[q] for q in adj[pcode]) / len(adj[pcode])
        assert abs(lag - float(by_pcode[pcode]["spatial_lag_mpi"])) < TOL, (
            f"{pcode}: python lag {lag:.9f} != R lag {by_pcode[pcode]['spatial_lag_mpi']}"
        )
        z_own, z_lag = mpi[pcode] - mean_mpi, lag - mean_mpi
        want_quad = ("HH" if z_own > 0 and z_lag > 0 else
                     "HL" if z_own > 0 else
                     "LH" if z_lag > 0 else "LL")
        assert by_pcode[pcode]["spatial_quadrant"] == want_quad, (
            f"{pcode}: R type {by_pcode[pcode]['spatial_quadrant']}, python says {want_quad}"
        )

    i_py = morans_i([mpi[p] for p in order], adj, order)
    assert abs(i_py - i_r) < TOL, (
        f"Moran's I: python {i_py:.9f} != R {i_r:.9f} -- the published headline number "
        "would depend on which implementation ran"
    )


def check_frozen_wording(by_key: dict[str, dict[str, str]]) -> None:
    """The four lines are frozen text; fail if the data has moved away from them."""
    r2 = float(by_key["ctx_lat_r2"]["value"])
    assert 0.70 <= r2 <= 0.80, (
        "atlas_text.SPATIAL_READER_LINES line 2 says 'about three quarters'; the data "
        f"now says {r2:.2f}. Reword the line (and the registration) before shipping."
    )
    survivors = float(by_key["h3_survivors_n"]["value"])
    assert survivors == 1, (
        "atlas_text.SPATIAL_READER_LINES line 4 says 'Only 1 of the 37 states'; the data "
        f"now says {survivors:.0f}. Reword the line before shipping."
    )


def fmt(x: float, dp: int) -> str:
    text = f"{x:.{dp}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def p_text(entry: dict[str, str]) -> str:
    if entry["p"] == "":
        return "\u2014"
    p = float(entry["p"])
    floor = 1.0 / (float(entry["nsim"]) + 1.0)
    return "\u2264 " + fmt(floor, 4) if p <= floor + 1e-12 else fmt(p, 4)


def display_value(entry: dict[str, str]) -> str:
    """A count prints as an integer; every other statistic as 4 decimal places."""
    if entry["statistic"] == "n_states":
        return entry["value"]
    return fmt(float(entry["value"]), 4)


def verdict(entry: dict[str, str]) -> str:
    if entry["key"] == "h3_survivors_n":
        return "detected" if float(entry["value"]) >= 1 else "not detected"
    return "detected" if float(entry["p"]) < 0.05 else "not detected"


def section_text(rows: list[dict[str, str]], global_rows: list[dict[str, str]],
                 meta: dict[str, str]) -> str:
    by_key = {r["key"]: r for r in global_rows}
    lines: list[str] = [
        "*(Generated by `scripts/09_spatial_diagnostics.py` from "
        "`data/processed/spatial_global.csv`. Do not edit by hand.)*",
        "",
        spatial_context_line(global_rows),
        "",
        "### The pre-registered decisions",
        "",
        "| | hypothesis | statistic | value | p | decision |",
        "|---|---|---|---|---|---|",
    ]
    for key in ("h1_global_i", "h2_resid_i", "h3_survivors_n"):
        entry = by_key[key]
        lines.append(
            f"| {entry['kind']} | {entry['short']} | {entry['statistic']} | "
            f"{display_value(entry)} | {p_text(entry)} | {verdict(entry)} |"
        )
    lines += [
        "",
        "H1 is expected to be detected: a smooth north-south gradient guarantees it, "
        "which is exactly why H2 is the hypothesis of interest. H2 stays detected once "
        "the slope is removed. H3 is a count only -- no claim is made about the state it "
        "names, because orderings are not resolvable here "
        "(docs/FIX_LEDGER.md A1).",
        "",
        f"### The wording on the sheet ({atlas_text.SPATIAL_READING_HEADING})",
        "",
    ]
    for i, line in enumerate(atlas_text.SPATIAL_READER_LINES, start=1):
        lines.append(f"{i}. {line}")
    lines += [
        "",
        "### Every figure, and the sensitivities it survived",
        "",
        "| kind | statistic | value | p | note |",
        "|---|---|---|---|---|",
    ]
    for entry in global_rows:
        lines.append(
            f"| {entry['kind']} | {entry['short']} | {display_value(entry)} | "
            f"{p_text(entry)} | {entry['note']} |"
        )
    same = "queen and rook contiguity give the same neighbour graph" if (
        meta["queen_equals_rook"] == "TRUE"
    ) else "queen and rook contiguity give different neighbour graphs"
    singles = meta["single_neighbour_states"]
    lines += [
        "",
        f"Neighbours per state: min {meta['neighbours_min']}, median "
        f"{meta['neighbours_median']}, max {meta['neighbours_max']}; {same}; "
        f"{singles} has a single neighbour, so its own local statistic is the weakest "
        f"in the set.",
        "",
        f"Seed {meta['seed']}, {int(meta['permutations']):,} permutations, weights "
        f"row-standardised from `{meta['geojson']}` (the raw borders, not the simplified "
        f"rings the map draws). Permutation p cannot go below "
        f"1/(permutations+1), so 0.0001 is the floor and is written as an inequality.",
        "",
    ]
    return "\n".join(lines)


def polygon_rows(
    state_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], list[str]]:
    """The map's ring vertices, plus the neighbourhood type of the state they draw.

    Stage 4 owns `mpi_polygons.csv` and runs long before any spatial result exists, so
    this stage does not edit it: it writes the joined copy the cluster map's extract is
    built from. Columns are the polygon table's own, in its own order, with the spatial
    fields appended -- stage 6 reads the packaged extract's schema back positionally, so
    the two orders have to be the same one.
    """
    poly = read(POLY)
    assert poly, f"{POLY.name} is empty"
    assert "pcode" in poly[0], f"{POLY.name} has no pcode column to join on"

    by_pcode = {r["pcode"]: r for r in state_rows}
    missing = sorted({r["pcode"] for r in poly} - set(by_pcode))
    assert not missing, f"map rings for states with no spatial result: {missing}"

    joined = [
        {**row, **{field: by_pcode[row["pcode"]][field] for field in POLY_SPATIAL_FIELDS}}
        for row in poly
    ]
    assert len(joined) == len(poly), "the join changed the number of vertices"
    covered = {r["pcode"] for r in joined}
    assert len(covered) == N_STATES, (
        f"the joined map table covers {len(covered)} states, expected {N_STATES}"
    )
    return joined, list(poly[0].keys()) + POLY_SPATIAL_FIELDS


def write_section(text: str) -> None:
    """Replace the body of '## 3. Result' in the note, leaving the rest untouched."""
    marker = "## 3. Result"
    body = NOTE.read_text(encoding="utf-8")
    head, found, rest = body.partition(marker)
    assert found, f"{NOTE.name} has no '{marker}' heading"
    cut = rest.find("\n## ")
    tail = rest[cut:] if cut >= 0 else ""
    NOTE.write_text(f"{head}{marker}\n\n{text.rstrip()}\n{tail}", encoding="utf-8")


def ascii_safe(text: str) -> str:
    """The Windows console this runs under is cp1252, which has no ≤ or ≥.

    The markdown keeps the real characters; only the console summary is transliterated,
    so a stage cannot fail on the encoding of its own progress report.
    """
    for fancy, plain in (("\u2264", "<="), ("\u2265", ">="), ("\u2013", "-"),
                         ("\u2014", "-"), ("\u2009", " "), ("\u00a0", " ")):
        text = text.replace(fancy, plain)
    return text


def main() -> int:
    run_r()

    atlas = read(ATLAS)
    rows = read(R_STATE)
    global_rows = read(R_GLOBAL)
    meta = {r["metric"]: r["value"] for r in read(R_META)}
    by_key = {r["key"]: r for r in global_rows}

    adj = adjacency()
    verify(rows, atlas, adj, float(by_key["h1_global_i"]["value"]))
    check_frozen_wording(by_key)

    label_of = {code: words for code, words, _ in atlas_text.SPATIAL_QUADRANTS}
    unexpected = sorted({r["spatial_quadrant"] for r in rows} - set(label_of))
    assert not unexpected, f"neighbourhood types with no reader words: {unexpected}"

    run_date = datetime.now(timezone.utc).astimezone().date().isoformat()
    state_rows = [
        {
            **r,
            "mpi_pct": fmt(float(r["mpi"]) * 100, 2),
            "spatial_lag_mpi_pct": fmt(float(r["spatial_lag_mpi"]) * 100, 2),
            "spatial_group": label_of[r["spatial_quadrant"]],
            "run_date": run_date,
        }
        for r in rows
    ]
    write_csv(OUT_STATE, state_rows, STATE_FIELDS)
    write_csv(OUT_GLOBAL, [{**r, "run_date": run_date} for r in global_rows], GLOBAL_FIELDS)
    poly_out, poly_fields = polygon_rows(state_rows)
    write_csv(OUT_POLY, poly_out, poly_fields)
    write_section(section_text(rows, global_rows, meta))

    counts: dict[str, int] = {}
    for r in state_rows:
        counts[r["spatial_group"]] = counts.get(r["spatial_group"], 0) + 1
    print()
    print(ascii_safe(
        f"Moran's I {display_value(by_key['h1_global_i'])} "
        f"(p {p_text(by_key['h1_global_i'])}), after latitude "
        f"{display_value(by_key['h2_resid_i'])} (p {p_text(by_key['h2_resid_i'])}) "
        f"\u2014 verified in python to {TOL:g}"
    ))
    print(ascii_safe(f"neighbourhoods: " + ", ".join(
        f"{k} {v}" for k, v in sorted(counts.items())
    )))
    print(f"stands out after correction: {by_key['h3_survivors_n']['note'] or 'none'}")
    print(f"wrote 37 rows -> {OUT_STATE.relative_to(REPO_ROOT)}")
    print(f"wrote {len(global_rows)} rows -> {OUT_GLOBAL.relative_to(REPO_ROOT)}")
    print(
        f"wrote {len(poly_out)} map vertices -> {OUT_POLY.relative_to(REPO_ROOT)} "
        f"(+ {', '.join(POLY_SPATIAL_FIELDS)})"
    )
    print(f"wrote section 3 -> {NOTE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
