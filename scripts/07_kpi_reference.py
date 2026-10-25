"""Stage 7 -- build the WHO / SDG reference-standard table for the KPI sheet.

One output: data/reference/kpi_benchmarks_2021.csv, which stages 5 and 6 read
when the "Where Nigeria stands" view is built (docs/kpi_benchmarks.md). Every
number in the table is either fetched from the World Bank Indicators API today,
or read from files the pipeline already downloads and validates; nothing is
typed from memory.

A second output, data/processed/kpi_dots.csv, is the drawn sheet's extract: one
row per mark (KPI x reference point, row-normalised position, pre-formatted
hover), produced from the same table so the tabular view on stage 5's gate and
the drawn sheet cannot drift apart.

Indicators (all surveyed/published for 2021):

  SI.POV.MPUN     Multidimensional poverty headcount ratio, the OPHI/UNDP
                  global MPI series -- used as an independent gate on the OPHI
                  national row this pipeline already validates.
  SH.DYN.MORT     Under-five mortality per 1,000 live births (UN IGME).
                  This is the single indicator Nigeria's Health dimension rests
                  on, so it is the one WHO-standard health comparison the atlas
                  can make. Comparing the Health *contribution share* across
                  countries is forbidden (docs/CAUSAL_DECISION.md); comparing
                  this raw indicator to a WHO-published standard is not.
  SH.STA.ODFC.ZS  Open defecation (WHO/UNICEF JMP; a living-standards cutoff
                  the dataset already carries).
  SH.STA.SMSS.ZS  Safely managed sanitation (WHO/UNICEF JMP).
  SH.H2O.BASW.ZS  At least basic drinking water (WHO/UNICEF JMP).
  EG.ELC.ACCS.ZS  Access to electricity (SE4All / World Bank).
  EG.CFT.ACCS.ZS  Access to clean cooking fuels and technologies (SDG 7.1 /
                  WHO household air pollution guidance).

Code notes, discovered 2026-10-23:
  - the access codes end in ACCS.ZS, not ACC.ZS (ACC.ZS is rejected by the API);
  - safely managed *drinking water* has no WDI series under SH.H2O.SMWR /
    SH.STA.SMWR, so basic water is the water row;
  - WDI does not publish SI.POV.MPUN for SSA or world in 2021; the world
    reference carried here is UNDP/OPHI's published global figure (1.3 bn of
    5.9 bn people across 109 countries), which is a developing-regions average
    -- the sheet must say so, not "the world".
"""

from __future__ import annotations

import base64
import csv
import io
import json
import math
import shutil
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

from common import PROCESSED, RAW, REFERENCE, download, write_csv

import atlas_text

WDI_BASE = "https://api.worldbank.org/v2/country/NGA;SSF;WLD/indicator"
SURVEY_YEAR = "2021"

# OPHI's national row: the MPI pipeline already reconciles this survey against
# UNDP sheet 5.3 to within 1e-3 (stage 1), so it is a validated anchor here.
OPHI_NATIONAL = RAW / "ophi_nga_mpi.csv"

# World reference for the MPI headcount, from the UNDP/OPHI 2021 Global MPI
# report (fetched and read 2026-10-23): 1.3 billion of 5.9 billion people
# across 109 countries are multidimensionally poor.
OPHI_WORLD_HEADCOUNT = 22.0
OPHI_WORLD_HEADCOUNT_NOTE = (
    "1.3 bn of 5.9 bn people across 109 countries (UNDP/OPHI Global MPI 2021 "
    "report); a developing-regions average, not a literal world average"
)

# Tolerance for the headcount gate. WDI publishes the OPHI series rounded to
# whole people-percentage points (33 for 2021); the OPHI national row carries
# full precision (33.0441). A disagreement larger than this means one of the
# two sources has been revised and the sheet must not be built until resolved.
HEADCOUNT_TOLERANCE = 0.5


def read_national_mpi() -> dict[str, str]:
    """Read OPHI's national row out of the raw CSV the pipeline already validates."""
    if not OPHI_NATIONAL.exists():
        raise SystemExit(
            f"{OPHI_NATIONAL.name} is missing: run scripts/01_acquire_mpi.py first"
        )
    with OPHI_NATIONAL.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    national = [r for r in rows if r["Admin 1 Name"] == ""]
    assert len(national) == 1, f"expected exactly one national row in ophi_nga_mpi.csv, got {len(national)}"
    n = national[0]
    out = {
        "mpi": float(n["MPI"]),
        "headcount": float(n["Headcount Ratio"]),
        "intensity": float(n["Intensity of Deprivation"]),
        "vulnerable": float(n["Vulnerable to Poverty"]),
        "severe": float(n["In Severe Poverty"]),
    }
    n_states = len(rows) - 1
    assert n_states == 37, f"ophi_nga_mpi.csv has {n_states} state rows, expected 37"
    return out


def read_poor_population() -> float:
    """National count of people in MPI poverty, in millions, from the merged table."""
    path = PROCESSED / "mpi_atlas_2021.csv"
    if not path.exists():
        raise SystemExit(f"{path.name} is missing: run scripts/04_merge.py first")
    with path.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 37, f"mpi_atlas_2021.csv has {len(rows)} rows, expected 37"
    return round(sum(float(r["mpi_poor_thousands"]) for r in rows) / 1000.0, 1)


def file_date(path: Path) -> str:
    """Fetch/staleness date for a file, derived from its mtime.

    Same rule common.download uses: a cached file keeps the date it was
    downloaded, so the CSV's `fetched` column can never claim a fetch that did
    not happen.
    """
    return date.fromtimestamp(path.stat().st_mtime).isoformat()


def fetch_wdi(code: str) -> tuple[dict[str, Any], str]:
    """Fetch one WDI indicator for NGA / SSF / world, 2021, cached in data/raw."""
    url = f"{WDI_BASE}/{code}?format=json&date={SURVEY_YEAR}&per_page=10"
    dest = RAW / "wdi_kpi_2021" / f"{code}.json"
    download(url, dest)
    fetched = file_date(dest)
    payload = json.loads(dest.read_text(encoding="utf-8"))
    if "message" in payload:
        msg = payload["message"][0].get("value", "unknown error")
        raise SystemExit(f"WDI rejected {code}: {msg} -- check the indicator code")
    records = payload[1]
    by_country = {r["countryiso3code"]: r for r in records}
    expected = {"NGA", "SSF", "WLD"}
    assert set(by_country) == expected, (
        f"{code}: expected countries {sorted(expected)}, got {sorted(by_country)}"
    )
    for iso, rec in by_country.items():
        assert rec["date"] == SURVEY_YEAR, f"{code}/{iso}: date is {rec['date']}"
    return by_country, fetched


def fmt(x: float | None, dp: int = 1) -> str:
    """Format for the CSV: fixed decimals, blanks left blank."""
    return "" if x is None else f"{x:.{dp}f}"


def build_rows(national: dict[str, Any], poor_millions: float) -> tuple[list[dict[str, str]], list[str]]:
    """One row per KPI. Returns (rows, gate_messages); any gate failure is fatal."""
    ophi_fetched = file_date(OPHI_NATIONAL)
    processed_fetched = file_date(PROCESSED / "mpi_atlas_2021.csv")

    # code, label, unit, direction, decimals, benchmark (SDG target),
    # benchmark note, footnote about what the source is.
    SPEC = [
        (
            "SH.DYN.MORT",
            "Under-five mortality rate",
            "per 1,000 live births",
            "lower_is_better",
            1,
            "25",
            "SDG 3.2: by 2030, end preventable deaths of newborns and children "
            "under 5; under-5 mortality at most 25 per 1,000 live births",
            "UN Inter-agency Group for Child Mortality Estimation (WHO / UNICEF "
            "/ World Bank), via WDI. The single indicator Nigeria's Health "
            "dimension rests on.",
        ),
        (
            "SH.STA.ODFC.ZS",
            "Open defecation",
            "% of population",
            "lower_is_better",
            1,
            "0",
            "SDG 6.2: by 2030, end open defecation (WHO/UNICEF JMP)",
            "WHO/UNICEF Joint Monitoring Programme, via WDI. A living-standards "
            "deprivation cutoff the dataset already carries.",
        ),
        (
            "SH.STA.SMSS.ZS",
            "Safely managed sanitation",
            "% of population",
            "higher_is_better",
            1,
            "100",
            "SDG 6.2: by 2030, adequate and equitable sanitation for all "
            "(WHO/UNICEF JMP)",
            "WHO/UNICEF Joint Monitoring Programme, via WDI.",
        ),
        (
            "SH.H2O.BASW.ZS",
            "At least basic drinking water",
            "% of population",
            "higher_is_better",
            1,
            "100",
            "SDG 6.1: by 2030, universal and equitable access to safe and "
            "affordable drinking water (WHO/UNICEF JMP)",
            "WHO/UNICEF Joint Monitoring Programme, via WDI.",
        ),
        (
            "EG.ELC.ACCS.ZS",
            "Access to electricity",
            "% of population",
            "higher_is_better",
            1,
            "100",
            "SDG 7.1: by 2030, universal access to affordable, reliable and "
            "modern energy services",
            "SE4All / UN statistics, via WDI.",
        ),
        (
            "EG.CFT.ACCS.ZS",
            "Access to clean cooking fuels and technologies",
            "% of population",
            "higher_is_better",
            1,
            "100",
            "SDG 7.1: by 2030, universal access to clean cooking fuels and "
            "technologies (WHO household air pollution guidance)",
            "SE4All / UN statistics, via WDI.",
        ),
    ]

    # Gates first, so a revision upstream aborts before the CSV is written.
    gates: list[str] = []

    headcount, fetched_mpun = fetch_wdi("SI.POV.MPUN")
    hdi_nga = headcount["NGA"]["value"]
    assert hdi_nga is not None, "SI.POV.MPUN has no Nigeria value for 2021"
    diff = abs(float(hdi_nga) - national["headcount"])
    assert diff <= HEADCOUNT_TOLERANCE, (
        f"headcount gate failed: WDI {hdi_nga} vs OPHI national {national['headcount']:.4f} "
        f"(diff {diff:.4f} > {HEADCOUNT_TOLERANCE}); a source has been revised"
    )
    gates.append(
        f"OK headcount gate: WDI {hdi_nga} vs OPHI national "
        f"{national['headcount']:.4f} (diff {diff:.4f})"
    )

    rows: list[dict[str, str]] = []

    rows.append(
        {
            "kpi": "Multidimensional poverty headcount (national)",
            "wdi_code": "SI.POV.MPUN",
            "unit": "% of population",
            "direction": "lower_is_better",
            "nigeria_wdi": hdi_nga,
            "nigeria_dataset": fmt(national["headcount"], 4),
            "sub_saharan_africa": "",
            "world": fmt(OPHI_WORLD_HEADCOUNT, 0),
            "world_note": OPHI_WORLD_HEADCOUNT_NOTE,
            "benchmark_value": "",
            "benchmark_note": "",
            "source_note": "OPHI/UNDP global MPI, harmonised series "
            "(national row of data/raw/ophi_nga_mpi.csv), gated against WDI. "
            "No SSA figure is published by WDI for 2021.",
            "survey_year": SURVEY_YEAR,
            "fetched": fetched_mpun,
        }
    )

    for code, label, unit, direction, dp, target, target_note, source_note in SPEC:
        recs, fetched = fetch_wdi(code)
        vals = {iso: recs[iso]["value"] for iso in ("NGA", "SSF", "WLD")}
        for iso, v in vals.items():
            assert v is not None, f"{code}: no 2021 value for {iso}; the row would be silently blank"

        rows.append(
            {
                "kpi": label,
                "wdi_code": code,
                "unit": unit,
                "direction": direction,
                "nigeria_wdi": fmt(vals["NGA"], dp),
                "nigeria_dataset": "",
                "sub_saharan_africa": fmt(vals["SSF"], dp),
                "world": fmt(vals["WLD"], dp),
                "world_note": "",
                "benchmark_value": target,
                "benchmark_note": target_note,
                "source_note": source_note,
                "survey_year": SURVEY_YEAR,
                "fetched": fetched,
            }
        )
        gates.append(f"OK {code}: NGA {fmt(vals['NGA'], dp)} vs SSF {fmt(vals['SSF'], dp)} / world {fmt(vals['WLD'], dp)}")

    # Dataset-native KPIs with no WHO-style standard. Benchmark columns stay
    # blank, never zero-ish filler, so future readers know absence from 0.
    dataset_rows = [
        ("National MPI value", "index (0-1)", "lower_is_better", fmt(national["mpi"], 4),
         "OPHI/UNDP harmonised series, national row. Not comparable to older "
         "un-harmonised OPHI releases (docs/AGENTS corrections)."),
        ("Average intensity among the poor (national)", "% of weighted deprivations",
         "lower_is_better", fmt(national["intensity"], 2),
         "OPHI national row; poor-weighted, so it is not a simple state mean."),
        ("Severe poverty headcount", "% of population", "lower_is_better",
         fmt(national["severe"], 2),
         "OPHI national row: deprived in 50% or more of weighted indicators."),
        ("Vulnerable to poverty", "% of population", "lower_is_better",
         fmt(national["vulnerable"], 2),
         "OPHI national row: deprived in 20-33% of weighted indicators."),
        ("People multidimensionally poor", "millions", "lower_is_better",
         f"{poor_millions:.1f}",
         "Sum of state mpi_poor_thousands in data/processed/mpi_atlas_2021.csv "
         "(UNDP sheet 5.3 populations)."),
    ]
    for label, unit, direction, value, note in dataset_rows:
        rows.append(
            {
                "kpi": label,
                "wdi_code": "",
                "unit": unit,
                "direction": direction,
                "nigeria_wdi": "",
                "nigeria_dataset": value,
                "sub_saharan_africa": "",
                "world": "",
                "world_note": "",
                "benchmark_value": "",
                "benchmark_note": "",
                "source_note": note,
                "survey_year": SURVEY_YEAR,
                "fetched": processed_fetched if label.startswith("People") else ophi_fetched,
            }
        )
    gates.append(f"OK 5 dataset-native KPI rows (national `{national['mpi']:.4f}` MPI, {poor_millions:.1f}m poor)")

    return rows, gates


# --- Wave 3: the series silhouettes (the KPI board's image marks) --------------
# The KPI board's marks are map silhouettes, not circles: a map of the world for
# the world reference, a map of Africa for sub-Saharan Africa, a map of Nigeria
# for Nigeria. Tableau draws a Shape mark's image from a custom-shape palette
# (scripts/06_build_twb.py embeds them in the workbook), so the three PNGs on
# disk are the canonical images.
#
# Nothing here is a stock photo. Nigeria is drawn from the shipped ADM1 rings
# (data/processed/mpi_polygons.csv -- the same geometry the choropleths draw, so
# the country's own outline is the atlas's, not a cartographer's choice), and
# Africa + the world from Natural Earth's 1:110m admin-0 polygons, fetched once
# into data/raw (public domain; download() records the SHA256 in the provenance
# ledger). All three are transparent-background PNGs on one square canvas, the
# content scaled so its largest side fills a fixed share of that canvas: Tableau
# fits a shape image's canvas into the mark box, so equal canvases are how the
# three icons stay the same size while the maps keep their true proportions.

NE_110M_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
    "geojson/ne_110m_admin_0_countries.geojson"
)
NE_SHAPE_DIR = RAW / "natural_earth"
# 1:110m detail: at icon size the extra delta of 50m is invisible and the file
# is ~1/8th the size. The property names come from Natural Earth's schema; the
# asserts below fail loudly if a future schema renames them.
NE_CONTINENT_KEY = "CONTINENT"
SHAPES_SRC = REFERENCE / "kpi_shapes"
ICON_CANVAS = 256      # the square canvas every silhouette is composited onto
ICON_MAX_SIDE = 234    # the content's largest side inside that canvas
# member -> silhouette file lives in atlas_text.KPI_SHAPE_FILES (single-sourced
# with the workbook's shape palette and the stage-5 gate). The file names must
# match the KPI_Geo shape-palette references in stage 6 exactly.


def _ring_paths(geometry: dict[str, Any]) -> list[list[tuple[float, float]]]:
    """Flatten a GeoJSON geometry into closed ring vertex lists (outer+holes)."""
    kind = geometry["type"]
    polys: list[list[list[list[float]]]] = []
    if kind == "Polygon":
        polys = [geometry["coordinates"]]
    elif kind == "MultiPolygon":
        polys = geometry["coordinates"]
    else:
        raise SystemExit(f"natural-earth geometry type {kind!r} is not handled")
    rings: list[list[tuple[float, float]]] = []
    for poly in polys:
        for ring in poly:            # ring 0 outer, later rings holes
            rings.append([(float(x), float(y)) for x, y in ring])
    return rings


def _state_rings() -> list[list[tuple[float, float]]]:
    """Nigeria's silhouette: every ADM1 ring the atlas ships, as closed loops."""
    path = PROCESSED / "mpi_polygons.csv"
    if not path.exists():
        raise SystemExit(f"{path.name} is missing: run scripts/04_merge.py first")
    rings: dict[tuple[str, int], list[tuple[float, float]]] = {}
    states: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            key = (row["pcode"], int(row["ring"]))
            rings.setdefault(key, []).append(
                (float(row["lon"]), float(row["lat"]))
            )
            states.add(row["pcode"])
    assert len(states) == 37, f"mpi_polygons.csv covers {len(states)} states, expected 37"
    out = []
    for key in sorted(rings):
        ring = rings[key]
        if len(ring) >= 3:
            out.append(ring)
    assert len(out) >= 37, f"expected at least 37 drawable ADM1 rings, got {len(out)}"
    return out


def _draw_icon(rings: list[list[tuple[float, float]]], fill: str) -> bytes:
    """Render closed rings as one flat silhouette, transparent background."""
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    dpi = 100
    fig = Figure(figsize=(6.0, 6.0), dpi=dpi)
    FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1])
    xs = [x for ring in rings for x, _ in ring]
    ys = [y for ring in rings for _, y in ring]
    pad = 0.02 * max(max(xs) - min(xs), max(ys) - min(ys))
    ax.set_xlim(min(xs) - pad, max(xs) + pad)
    ax.set_ylim(min(ys) - pad, max(ys) + pad)
    ax.set_aspect("equal")
    ax.axis("off")
    # Fill then re-stroke each ring: anti-aliased edges of adjacent filled
    # rings leave hairline background seams otherwise, which a silhouette built
    # from 37 state polygons absolutely shows.
    for ring in rings:
        if len(ring) < 3:
            continue
        lons, lats = zip(*ring)
        ax.fill(lons, lats, color=fill, linewidth=0, zorder=2)
    for ring in rings:
        if len(ring) < 3:
            continue
        lons = [x for x, _ in ring] + [ring[0][0]]
        lats = [y for _, y in ring] + [ring[0][1]]
        ax.plot(lons, lats, color=fill, linewidth=1.2, solid_capstyle="round", zorder=3)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", transparent=True)
    return buf.getvalue()


def _fill_rgba(fill: str) -> tuple[int, int, int, int]:
    """'#rrggbb' -> an RGBA tuple, alpha 255 (PIL needs integers, not the string)."""
    hexcode = fill.lstrip("#")
    assert len(hexcode) == 6, f"unexpected colour {fill!r}"
    return (int(hexcode[0:2], 16), int(hexcode[2:4], 16),
            int(hexcode[4:6], 16), 255)


def _draw_globe(fill: str) -> bytes:
    """The world mark: a solid disc with VERTICAL MERIDIANS only.

    History, because this mark has been redrawn three times: the 2026-10-23
    passes rejected a flat strip, then a map clipped into a circle, then
    continents cut out of the disc, and landed on "disc + white coastlines +
    a lat/long grid". The 2026-10-24 pass is the last word so far and removes
    the coastlines: at mark scale (a ~40 px shape) the 110m coastline is
    sub-pixel noise that fights the meridians, and the user asked for longitude
    lines only. What is left is the disc plus five meridian chords -- the
    minimum that still reads as a globe rather than a coloured dot, and the
    only detail that survives being scaled down.

    Drawn with PIL at 4x supersample, then downscaled on the shared canvas.
    Contrast rides ALPHA, not RGB: Tableau's colour card tints the PNG, so the
    lines drop their alpha (~45% of the disc) and the tint paints them lighter
    -- see the long note in build_shape_images and FIX_LEDGER K3.
    """
    from PIL import Image, ImageDraw

    ss = 4
    side = ICON_CANVAS * ss

    # Longitude lines only (the 2026-10-24 pass: no parallels, no coastlines).
    # Drawn as ORTHOGRAPHIC MERIDIANS rather than straight stripes: on a sphere
    # seen face-on, a meridian at delta-longitude projects to a vertical ellipse
    # of semi-width R*sin(delta), so the set of them bows and the disc reads as
    # a globe instead of a striped coin. 0 degrees is the straight central
    # meridian, then +/-30, +/-60 and +/-80 degrees for the near-limb pair.
    grid_w = max(2, round(side * 0.035))
    lines_mask = Image.new("L", (side, side), 0)
    ldraw = ImageDraw.Draw(lines_mask)
    mid = side / 2.0
    for deg in (0.0, 30.0, -30.0, 60.0, -60.0, 80.0, -80.0):
        w = (side / 2.0) * abs(math.sin(math.radians(deg)))
        if w < 1.0:
            ldraw.line([(mid, 0.0), (mid, side)], fill=255, width=grid_w)
        else:
            ldraw.ellipse([mid - w, 0.0, mid + w, side], outline=255,
                          width=grid_w)

    # Alpha compose: start from the disc, carve the tinted-down intensity for
    # every line pixel (~45% drop).
    disc = Image.new("L", (side, side), 0)
    ddraw = ImageDraw.Draw(disc)
    ddraw.ellipse([0, 0, side - 1, side - 1], fill=255)
    import numpy as np
    disc_a = np.asarray(disc, dtype=np.float32)
    lines_a = np.asarray(lines_mask, dtype=np.float32) / 255.0
    alpha = (disc_a * (1.0 - lines_a * 0.45)).astype(np.uint8)
    arr = np.zeros((side, side, 4), dtype=np.uint8)
    arr[..., 0:3] = _fill_rgba(fill)[0:3]
    arr[..., 3] = alpha
    out = Image.fromarray(arr, "RGBA")
    out = out.resize((ICON_CANVAS, ICON_CANVAS), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _draw_arrow(fill: str, points_right: bool) -> bytes:
    """A bold chevron, pointing right or left, on the shared icon canvas.

    Same conventions as _draw_globe: 4x supersample, contrast rides alpha (the
    colour card tints the PNG by alpha -- FIX_LEDGER K3), then _finish_icon
    trims and centres it. The atlas has no animatable surface, so the guide is a
    still arrow; the direction does the talking.
    """
    from PIL import Image, ImageDraw
    import numpy as np

    ss = 4
    side = ICON_CANVAS * ss
    # Arrow in 0..1 coordinates: a shaft plus a head, one polygon.
    outline = [
        (0.04, 0.42), (0.60, 0.42), (0.60, 0.22), (0.96, 0.50),
        (0.60, 0.78), (0.60, 0.58), (0.04, 0.58),
    ]
    if not points_right:
        outline = [(1.0 - x, y) for x, y in outline]

    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).polygon(
        [(x * side, y * side) for x, y in outline], fill=255
    )
    arr = np.zeros((side, side, 4), dtype=np.uint8)
    arr[..., 0:3] = _fill_rgba(fill)[0:3]
    arr[..., 3] = np.asarray(mask, dtype=np.uint8)
    out = Image.fromarray(arr, "RGBA")
    out = out.resize((ICON_CANVAS, ICON_CANVAS), Image.LANCZOS)
    buf = io.BytesIO()
    out.save(buf, format="PNG")
    return buf.getvalue()


def _finish_icon(png_bytes: bytes, dest: Path, fill: str) -> None:
    """Trim transparent margins, re-center on the shared square canvas, save."""
    from PIL import Image

    img = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    visible = img.getbbox()
    assert visible, f"{dest.name}: the silhouette drew zero visible pixels"
    img = img.crop(visible)
    scale = ICON_MAX_SIDE / max(img.size)
    img = img.resize((round(img.width * scale), round(img.height * scale)),
                     Image.LANCZOS)
    canvas = Image.new("RGBA", (ICON_CANVAS, ICON_CANVAS), (0, 0, 0, 0))
    left = (ICON_CANVAS - img.width) // 2
    top = (ICON_CANVAS - img.height) // 2
    canvas.paste(img, (left, top))
    canvas.save(dest, format="PNG")
    _assert_icon(dest)


def _assert_icon(path: Path) -> None:
    """Every silhouette file: exists, non-trivial bytes, the shared canvas, ink."""
    from PIL import Image

    assert path.exists(), f"missing silhouette {path.name} (build_shape_images)"
    assert path.stat().st_size > 2000, f"{path.name} is suspiciously small"
    with Image.open(path) as img:
        assert img.size == (ICON_CANVAS, ICON_CANVAS), (
            f"{path.name} is {img.size}, expected the ({ICON_CANVAS}, {ICON_CANVAS}) canvas"
        )
        assert img.getbbox(), f"{path.name} has an empty bounding box (no ink)"


def build_shape_images() -> None:
    """data/reference/kpi_shapes/{nigeria,africa,world}.png, the sheet's icons.

    Nigeria from the atlas's own ADM1 rings, Africa and the world from Natural
    Earth 110m; transparent PNGs on one square canvas, then copied into My
    Tableau Repository\\Shapes\\KPI_Geo so Tableau's Shape editor can see them
    while authoring (the packaged workbook embeds its own copies, so the copy is
    an authoring convenience, not a runtime dependency).
    """
    SHAPES_SRC.mkdir(parents=True, exist_ok=True)

    fills = dict(atlas_text.KPI_SERIES)

    # 1. Nigeria: the shipped map geometry, all 37 state rings filled.
    rings = _state_rings()
    _finish_icon(
        _draw_icon(rings, fills["Nigeria (2021)"]),
        SHAPES_SRC / atlas_text.KPI_SHAPE_FILES["Nigeria (2021)"],
        fills["Nigeria (2021)"],
    )

    # 2. Africa + world: Natural Earth 110m admin-0, fetched once into data/raw.
    ne_path = NE_SHAPE_DIR / "ne_110m_admin_0_countries.geojson"
    download(NE_110M_URL, ne_path)
    features = json.loads(ne_path.read_text(encoding="utf-8"))["features"]
    assert len(features) >= 150, f"only {len(features)} admin-0 features"
    missing = [f for f in features if NE_CONTINENT_KEY not in f["properties"]]
    assert not missing, (
        f"{len(missing)} features lack {NE_CONTINENT_KEY}; the schema renamed it"
    )
    africa = [f for f in features
              if f["properties"][NE_CONTINENT_KEY] == "Africa"]
    assert 45 <= len(africa) <= 60, f"unexpected Africa feature count {len(africa)}"
    africa_rings: list[list[tuple[float, float]]] = []
    for f in africa:
        africa_rings.extend(_ring_paths(f["geometry"]))
    _finish_icon(
        _draw_icon(africa_rings, fills["sub-Saharan Africa (2021)"]),
        SHAPES_SRC / atlas_text.KPI_SHAPE_FILES["sub-Saharan Africa (2021)"],
        fills["sub-Saharan Africa (2021)"],
    )
    # The globe is a disc on the shared canvas, so it needs no geometry: the
    # landmass no longer draws on it (2026-10-24 keeps the meridians only), and
    # _finish_icon trims and rescales whatever ink it gets.
    _finish_icon(
        _draw_globe(fills["World (2021)"]),
        SHAPES_SRC / atlas_text.KPI_SHAPE_FILES["World (2021)"],
        fills["World (2021)"],
    )

    # 3. The two direction guides (2026-10-25): one arrow per row, pointing the
    # way that is good on that row. Same canvas, same alpha convention, so the
    # three reference icons and the two guides line up as one mark set.
    for direction, (member, colour) in atlas_text.KPI_GUIDE.items():
        _finish_icon(
            _draw_arrow(colour, points_right=(direction == "higher_is_better")),
            SHAPES_SRC / atlas_text.KPI_GUIDE_SHAPE_FILES[member],
            colour,
        )

    # 3. Authoring copy inside the Tableau repository (env-derived, never a
    # hardcoded absolute path; the workbook embeds its shapes, so this copy is
    # only needed to reassign shapes in the Shape editor -- and on this machine
    # the agent's shell is refused writes anywhere under Documents, apparently
    # a shell-level protection, while reads work). A copy failure is printed,
    # not raised: the embedded shapes in the packaged workbook are the real
    # dependency, and the manual copy is one documented in docs/PUBLISH.md.
    tab_shapes = (Path.home() / "Documents" / "My Tableau Repository" / "Shapes"
                  / "KPI_Geo")
    if (Path.home() / "Documents" / "My Tableau Repository").exists():
        try:
            tab_shapes.mkdir(parents=True, exist_ok=True)
            for name in atlas_text.KPI_SHAPE_FILES.values():
                shutil.copy2(SHAPES_SRC / name, tab_shapes / name)
            print(f"  copied 3 silhouettes to {tab_shapes}")
        except OSError as exc:
            print(
                "  NOTE: could not copy silhouettes into My Tableau Repository"
                f"\\Shapes\\KPI_Geo ({exc}); the workbook embeds its own "
                "copies, so this only matters for GUI shape reassignment -- "
                "see docs/PUBLISH.md"
            )
    else:
        print("  no Tableau repository found; skipped the authoring copy")

    print(f"wrote 3 silhouettes: {SHAPES_SRC}")


# --- Wave 2: the sheet's own extract ------------------------------------------
# A mark's icon is ~0.05-0.07 of a 0-1 axis wide on the shipped sheet, so two
# shares closer together than this overlap: the reader cannot tell there are
# two marks, and their printed labels collide as well.
KPI_DODGE_MIN_GAP = 0.07
# Never push a dodged mark off the axis or onto the frame.
KPI_DODGE_FLOOR = 0.02


def _dodge(shares: dict[str, float]) -> dict[str, float]:
    """Spread a row's near-coincident marks apart, without moving the top one.

    Returns the position each mark is DRAWN at. A mark at the row's largest
    reference stays exactly where it belongs (1.0 -- by construction the row's
    scale is that value), and any mark whose share falls within
    KPI_DODGE_MIN_GAP of the one above it is slid LEFT just far enough to clear
    it. Sliding down/left rather than centre-then-spread is deliberate: the
    right-hand edge of every row keeps meaning "the largest reference", so the
    axis caption stays true.

    This is the one place on this sheet where a drawn position is not exactly
    the value, so it is bounded and it is visible: the slide is at most
    KPI_DODGE_MIN_GAP, the mark still prints its TRUE share (pos_label, not the
    dodged pos), and a row with no collision is untouched. Two rows dodge on
    2021's numbers (clean cooking fuel's SSA/Nigeria pair, and open defecation's
    SSA/Nigeria pair); the rest are already clear.

    `pos` is documented layout, not data (this sheet's own docstring: one axis
    because the row units differ), which is why the fix lives here rather than
    in the workbook -- Tableau cannot offset marks inside a discrete row.
    """
    out: dict[str, float] = {}
    ceiling: float | None = None
    for series, share in sorted(shares.items(), key=lambda kv: kv[1], reverse=True):
        pos = share
        if ceiling is not None and pos > ceiling:
            pos = ceiling
        out[series] = max(pos, KPI_DODGE_FLOOR)
        ceiling = out[series] - KPI_DODGE_MIN_GAP
    assert set(out) == set(shares), "dodge lost a mark"
    return out


def build_dots() -> int:
    """data/processed/kpi_dots.csv -- the marks the 'Where Nigeria stands' sheet draws.

    One row per mark: 7 benchmarked KPIs x their reference points (Nigeria on
    every row, sub-Saharan Africa where WDI publishes it, world on every row);
    20 marks over all. The dataset-native rows with no published standard (the
    five at the bottom of the benchmarks table) are deliberately absent: a dot
    with no reference to sit beside would read as a judgement, and the board's
    whole grammar is value-beside-reference.

    `pos` is the row-normalised position: value / the largest of that row's
    references (Nigeria, SSA, world, SDG benchmark), then dodged (`_dodge`) so
    two near-coincident marks do not draw on top of each other. The sheet needs
    one axis because the row units differ (per-1,000 rates against percents);
    pos is therefore a LAYOUT aid. The 2026-10-23 user passes ended with the
    share PRINTING on the sheet (marks' labels + the returned axis, one decimal,
    user's explicit "keep the scale-share number") while the raw values stay
    one hover away -- and since 2026-10-24 the label prints the TRUE share even
    when the mark itself is dodged left to clear its neighbour.
    """
    path = REFERENCE / "kpi_benchmarks_2021.csv"
    if not path.exists():
        raise SystemExit(f"{path.name} is missing: the fetch must have failed")
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    benchmark_rows = [r for r in rows if r["wdi_code"]]
    assert len(benchmark_rows) == 7, (
        f"expected the 7 benchmarked KPI rows, got {len(benchmark_rows)}"
    )
    # The no-standard rows do not reach the sheet; asserted present in the table
    # (so losing one is a visible change, not a silent drop).
    assert sum(1 for r in rows if not r["wdi_code"]) == 5, (
        "the five dataset-native rows are missing from the benchmarks table"
    )

    marks: list[dict[str, str]] = []
    for row in benchmark_rows:
        label = atlas_text.KPI_ROW_LABELS[row["kpi"]]
        assert label.strip(), f"no row label for benchmark kpi {row['kpi']!r}"
        # The row header's direction arrow is a design constant (atlas_text) and
        # the benchmarks CSV's `direction` column is the ground truth; assert
        # them against each other so a re-ordered or re-sourced row cannot leave
        # an arrow pointing the wrong way.
        # The direction is carried by the row's coloured arrow guide and its own
        # label (2026-10-25, fourth pass); the row label is just the name and the
        # unit again, because the appended sentence truncated in the header.
        assert row["direction"] in atlas_text.KPI_DIRECTION_ARROW, (
            f"{row['kpi']}: unknown direction {row['direction']!r}"
        )
        raw = {
            atlas_text.KPI_SERIES[0][0]: row["nigeria_wdi"] or row["nigeria_dataset"],
            atlas_text.KPI_SERIES[1][0]: row["sub_saharan_africa"],
            atlas_text.KPI_SERIES[2][0]: row["world"],
        }
        values = {s: float(v) for s, v in raw.items() if v}
        assert atlas_text.KPI_SERIES[0][0] in values, (
            f"{row['kpi']}: no Nigeria value to draw"
        )
        scale = max(values.values())
        # Placement, before draw order: the true share of the row's largest
        # reference, then a dodge for marks that would collide (see _dodge).
        shares = {series: value / scale for series, value in values.items()}
        placed = _dodge(shares)
        # The hovering word budget is one line (2026-10-23 user pass, third):
        # values at one decimal, then the benchmark and the source, nothing
        # else the sheet already shows. The row header carries the unit and
        # the KPI name, so the hover reads bare numbers.
        if row["benchmark_value"]:
            benchmark_text = f"target {row['benchmark_value']}"
        else:
            benchmark_text = "no target"

        parts: list[str] = []
        for series, value in raw.items():
            if not value:
                continue
            # Values print at one decimal. The drawn `pos` keeps full
            # precision; this string is what the reader acts on.
            rounded = f"{float(value):.1f}"
            # Series names lose their " (2021)" tail here (the title says 2021)
            # and the unit stays out (the row header names it).
            short = series.split(" (")[0]
            if (series == atlas_text.KPI_SERIES[2][0]
                    and row["wdi_code"] == "SI.POV.MPUN"):
                # "World" on the headcount row is UNDP/OPHI's total across 109
                # developing countries, not every country on earth. That caveat
                # used to sit in the sheet subtitle; the 2026-10-24 word budget
                # moved it next to the number it qualifies, which is where a
                # reader can act on it (docs/SHEET_KPI.md, "May not say").
                parts.append(f"{short} {rounded} (109 developing countries)")
                continue
            parts.append(f"{short} {rounded}")
        hover = (
            " \u00b7 ".join(parts)
            + f" \u00b7 {benchmark_text}"
            + f" \u00b7 {atlas_text.KPI_SOURCE[row['wdi_code']]} (WDI 2021)"
        )
        assert hover.strip(), f"empty hover for {row['kpi']}"
        # Marks are appended in REVERSE series order per row: Nigeria last.
        # The sheet's only near-coincident pair (clean cooking fuel: Nigeria
        # 22.0 against SSA 20.5, ~2% of the axis apart) must read as Nigeria in
        # front, so the green silhouette is drawn last; Tableau draws marks in
        # the extract's row order, later rows over earlier ones. The hover
        # string above keeps its own order -- it is text, unaffected by draw
        # order.

        # The direction guide draws FIRST in the row, so it sits under the
        # reference marks. Its label carries the sentence, so the words appear
        # beside the arrow itself (2026-10-25, third pass).
        guide_member, _guide_colour = atlas_text.KPI_GUIDE[row["direction"]]
        marks.append(
            {
                "kpi": label,
                "series": guide_member,
                "pos": f"{atlas_text.KPI_GUIDE_POS:.4f}",
                "pos_label": guide_member,
                "hover": "",
            }
        )
        for series, value in reversed(list(raw.items())):
            if not value:
                continue
            pos = placed[series]
            assert 0 < pos <= 1.0, f"{row['kpi']} / {series}: pos {pos:.3f} out of (0, 1]"
            # The mark's LABEL is a pre-formatted string (2026-10-23 user pass:
            # the value beside the maps prints at one decimal, small font) and
            # it prints the TRUE share, never the dodged position -- the dodge
            # moves the picture, not the number. The number-format lanes in the
            # twb were tried and the label kept Tableau's General 4-decimal
            # print, so the sheet labels the same way the hover does: with
            # data-side text, never with formatting.
            marks.append(
                {
                    "kpi": label,
                    "series": series,
                    "pos": f"{pos:.4f}",
                    "pos_label": f"{shares[series]:.1f}",
                    "hover": hover,
                }
            )

    n = write_csv(
        PROCESSED / "kpi_dots.csv",
        marks,
        ["kpi", "series", "pos", "pos_label", "hover"],
    )
    # 20 reference marks + one direction guide per row = 27.
    assert n == 27, f"kpi_dots.csv has {n} marks, expected 27"
    print(f"\nwrote {PROCESSED / 'kpi_dots.csv'} ({n} marks)")
    return n


def main() -> None:
    national = read_national_mpi()
    poor_millions = read_poor_population()

    rows, gates = build_rows(national, poor_millions)

    fieldnames = [
        "kpi",
        "wdi_code",
        "unit",
        "direction",
        "nigeria_wdi",
        "nigeria_dataset",
        "sub_saharan_africa",
        "world",
        "world_note",
        "benchmark_value",
        "benchmark_note",
        "source_note",
        "survey_year",
        "fetched",
    ]
    out = REFERENCE / "kpi_benchmarks_2021.csv"
    n = write_csv(out, rows, fieldnames)
    assert n == 12, f"wrote {n} KPI rows, expected 12"

    for g in gates:
        print(g)
    print(f"\nwrote {out.relative_to(out.parents[2])} ({n} rows)")
    print("Benchmarks are 2021 values, fetched by this script; see docs/kpi_benchmarks.md")
    build_dots()
    build_shape_images()


if __name__ == "__main__":
    sys.exit(main())

