"""Stage 5 -- render the workbook's visuals as PNGs before Tableau is involved.

This is the QA gate. A colour that drifts, a state whose type changes, or a table row
with a missing cell is caught here, in Python, before the workbook is opened -- which
is what a gate is for.

Five previews, in tab order, one per published view:

1. Where poverty sits            filled choropleth, the five MPI bands the
                                 workbook draws, in the colours it draws them
2. Where poverty clusters        the same rings filled by neighbourhood type
                                 (stage 9), in the four colours the sheet uses
3. What the words mean           reference tab 1 of 3, as a monospace grid
4. The list of basic needs       reference tab 2 of 3, same gate
5. How we did it                 reference tab 3 of 3 -- the gate for a table
                                 is missing cells and misfiled rows

The reference table is one table shipped as three tabs, cut on the three groups it
already had: as a single dashboard it measured 2000 x 8720 px (docs/FIX_LEDGER.md W2).
The gate follows the tabs, so the numbering is per-part and not per-table.

Previews 2-6 and 8 used to exist: the dimension breakdown, the conflict overlay, the
gradient plot, the radar, the party panel and the Moran scatter. Their sheets were
withdrawn on 2026-10-18 (docs/FIX_LEDGER.md W1) and the previews went with them --
a gate for a sheet that is not in the workbook cannot gate anything. The analyses
themselves still run: stage 8's party test is pre-registered and its result is
reported in docs/party_alignment.md, and the spatial test behind preview 2 is
reported in docs/spatial_analysis.md.

One departure from the spec survives, deliberately: there is no radar chart. The
polygon-mark grammar it needs is the most fragile part of the Tableau schema to
hand-write, docs/PUBLISH.md records it as a GUI step, and the spec's remaining
visuals have been withdrawn anyway.
"""
from __future__ import annotations

import csv
import json
import re
import textwrap
from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.axes import Axes

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch, Polygon as MplPolygon  # noqa: E402

import atlas_text  # noqa: E402
from common import (  # noqa: E402
    DOCS,
    PROCESSED,
    RAW,
    spatial_context_line,
)

PREVIEW = DOCS / "preview"
ATLAS = PROCESSED / "mpi_atlas_2021.csv"

INK = "#22252a"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 9,
    "axes.edgecolor": "#8a8a8a",
    "axes.labelcolor": INK,
    "text.color": INK,
    "xtick.color": "#555555",
    "ytick.color": "#555555",
    "figure.facecolor": "white",
    "savefig.facecolor": "white",
})


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def titles(ax: Axes, main: str, sub: str, *, width: int = 96) -> None:
    """Draw a title with a subtitle underneath it, without the two colliding.

    matplotlib positions a title in points above the axes, so the same title pad
    that clears the axis on a tall figure collides with the subtitle on a short
    one. The subtitle is wrapped to a character width and the title pad is
    derived from the number of lines it needs.
    """
    lines = textwrap.wrap(sub, width=width)
    sub_pt = 8.6
    gap_pt = sub_pt * len(lines) * 1.35 + 10
    ax.set_title(main, fontsize=13, fontweight="700", loc="left", pad=gap_pt + 10)
    ax.text(
        0,
        1.0,
        "\n".join(lines),
        transform=ax.transAxes,
        fontsize=sub_pt,
        color="#555555",
        va="bottom",
        linespacing=1.35,
    )


def feature_rings(geom: dict[str, Any]) -> list[list[list[float]]]:
    """Extract exterior+interior rings as (lon, lat) pairs."""
    t = geom["type"]
    polys = [geom["coordinates"]] if t == "Polygon" else geom["coordinates"]
    rings: list[list[list[float]]] = []
    for poly in polys:
        for ring in poly:
            rings.append([[pt[0], pt[1]] for pt in ring])
    return rings


# Where each state's name is drawn, in degrees away from its capital. The south-east
# is crowded, so those labels are nudged apart; shared by the two map previews so the
# poverty map and the cluster map label the same country the same way.
LABEL_NUDGES: dict[str, tuple[float, float]] = {
    "NG-DE": (0.0, -0.42), "NG-AN": (0.0, 0.36), "NG-AK": (-0.34, -0.28),
    "NG-CR": (0.14, 0.22), "NG-IM": (-0.34, -0.26), "NG-KN": (-0.30, -0.34),
    "NG-JI": (0.12, 0.32), "NG-AB": (-0.30, 0.20), "NG-BE": (0.0, 0.30),
    "NG-EN": (0.30, 0.18), "NG-RI": (-0.22, -0.30), "NG-BY": (-0.24, -0.24),
    "NG-SO": (0.0, 0.16),
}


def draw_rings(
    ax: Axes,
    gj: dict[str, Any],
    fill: dict[str, str],
    colour_of: dict[str, str],
    labels: dict[str, str],
    centroids: dict[str, tuple[float, float]],
    *,
    ink_on: set[str] = frozenset(),
) -> None:
    """Draw the ADM1 polygons with one fill colour per pcode, and name the states.

    Shared by the two map previews: sheet 1 colours the rings by poverty band, the
    cluster map by neighbourhood type, and the country, the borders and the label
    positions have to look identical either way. `ink_on` names the states whose label
    is drawn in ink rather than white -- on a dark fill, ink is unreadable.
    """
    for feat in gj["features"]:
        pcode = feat["properties"]["shapeISO"]
        if pcode not in fill:
            continue
        for ring in feature_rings(feat["geometry"]):
            ax.add_patch(
                MplPolygon(ring, closed=True, facecolor=colour_of[fill[pcode]],
                           edgecolor="white", linewidth=0.6)
            )
    for pcode, name in labels.items():
        lat, lon = centroids[pcode]
        dlat, dlon = LABEL_NUDGES.get(pcode, (0.0, 0.0))
        ax.text(
            lon + dlon, lat + dlat, name, fontsize=6.6, ha="center", va="center",
            color=INK if pcode in ink_on else "white", fontweight="bold",
        )


# ---------------------------------------------------------------- visual 1
def visual_choropleth(rows: list[dict[str, str]]) -> None:
    """The QA gate for sheet 1: the same measure, the same bands, the same colours.

    It used to draw a continuous ramp of H, the *headcount ratio*, which is not the
    measure the map colours by -- the map colours the MPI value in five bands. A gate
    that previews a chart the workbook does not contain cannot catch a regression in
    the workbook, so this now draws what sheet 1 draws: mpi_band, in the five colours
    from atlas_text. The two measures must never be swapped on the reader: H is the
    share of people who are poor, the MPI value is that share multiplied by how
    deprived they are on average, and it is the second one here.
    """
    gj = json.loads((RAW / "nga_adm1.geojson").read_text(encoding="utf-8"))
    band = {r["pcode"]: r["mpi_band"] for r in rows}
    label = {r["pcode"]: r["state"] for r in rows}

    order = [name for name, _ in atlas_text.MPI_BANDS]
    colour_of = dict(atlas_text.MPI_BANDS)
    depth = {name: i for i, name in enumerate(order)}
    unexpected = sorted(set(band.values()) - set(order))
    assert not unexpected, f"mpi_band values not in atlas_text.MPI_BANDS: {unexpected}"

    fig, ax = plt.subplots(figsize=(8.6, 9.4))
    centroids = {r["pcode"]: (float(r["lat"]), float(r["lon"])) for r in rows}
    # White labels on the two darkest bands, ink on the three light ones. The old
    # threshold was the H value, which is a different number. (`ink_on` names the
    # states drawn in ink; everything else is white -- so it is the *light* bands.)
    dark = {pcode for pcode in band if depth[band[pcode]] >= 3}
    light = set(band) - dark
    draw_rings(ax, gj, band, colour_of, label, centroids, ink_on=light)

    # A discrete legend, in band order -- not a continuous colourbar, which would
    # advertise a resolution the five bands do not have. The "N. " sort key is
    # stripped the same way stage 7 strips it for the HTML legend.
    def band_short(name: str) -> str:
        return name.split(". ", 1)[1].replace(" to ", "\u2013").replace(" and above", "+")

    handles = [
        Patch(facecolor=colour, edgecolor="#8a8a8a", linewidth=0.5, label=band_short(name))
        for name, colour in atlas_text.MPI_BANDS
    ]
    legend = ax.legend(
        handles=handles, title=f"{atlas_text.MPI_LEGEND_TITLE}\n({atlas_text.MPI_LEGEND_EXPANSION})",
        loc="center left", bbox_to_anchor=(1.005, 0.5), frameon=False,
        fontsize=7.6, title_fontsize=8, labelspacing=0.8,
    )
    legend._legend_box.align = "left"

    titles(
        ax,
        f"Nigeria: {atlas_text.MPI_LEGEND_EXPANSION} (MPI) by state",
        f"MICS 2021 \u00b7 36 states + FCT \u00b7 colour is the {atlas_text.MPI_LEGEND_TITLE.lower()} "
        f"({atlas_text.MPI_LEGEND_EXPANSION}) \u2014 {atlas_text.MPI_LEGEND_MEANING}. The headcount "
        "share H is a different number and is not this colour. OPHI's standard errors put "
        "the median relative SE at 15%, and all 36 adjacent rank pairs overlap at 95%, so "
        "five bands is the most the data supports; the exact value and its interval are in "
        "the workbook's hover.",
        width=104,
    )
    ax.set_xlim(2.4, 15.0)
    ax.set_ylim(3.9, 14.2)
    ax.set_aspect(1.0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(PREVIEW / "1_where_poverty_sits.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  1_where_poverty_sits.png")


# ------------------------------------------------- the spatial clustering map
def visual_spatial_clusters() -> None:
    """The QA gate for the cluster map: the same four types, in the same four colours.

    The map draws the ADM1 rings with `spatial_group` as the fill, so the gate draws
    the same rings from the same raw file with the same hexes from atlas_text, and
    prints the reading the sheet's hover carries. A colour that drifts, or a state
    whose type changes, is caught here before Tableau is opened -- which is what a gate
    is for.

    It is deliberately NOT a significance map: one state survives the correction and
    none survives the stricter variant, so the map colours all 37 states by type and
    the count goes in the footnote as a number. A map of what is significant would be
    one state, and it would invite naming it "the poorest cluster", which is the
    per-state ordering the atlas withdrew (docs/FIX_LEDGER.md A1).
    """
    rows = read(PROCESSED / "spatial_diagnostics.csv")
    global_rows = read(PROCESSED / "spatial_global.csv")
    atlas = read(ATLAS)
    assert len(rows) == 37, f"expected 37 states, got {len(rows)}"

    order = [words for _, words, _ in atlas_text.SPATIAL_QUADRANTS]
    colour_of = {words: colour for _, words, colour in atlas_text.SPATIAL_QUADRANTS}
    group = {r["pcode"]: r["spatial_group"] for r in rows}
    unexpected = sorted(set(group.values()) - set(colour_of))
    assert not unexpected, f"neighbourhood types with no colour: {unexpected}"

    gj = json.loads((RAW / "nga_adm1.geojson").read_text(encoding="utf-8"))
    labels = {r["pcode"]: r["state"] for r in atlas}
    centroids = {r["pcode"]: (float(r["lat"]), float(r["lon"])) for r in atlas}

    fig, ax = plt.subplots(figsize=(8.6, 9.4))
    # Ink labels over the two pale tints, white over the two deep fills -- the same
    # rule as the poverty map, where the two darkest bands take white.
    draw_rings(
        ax, gj, group, colour_of, labels, centroids,
        ink_on={p for p in group if group[p] not in atlas_text.SPATIAL_DEEP_TYPES},
    )

    counts: dict[str, int] = {words: 0 for words in order}
    for words in group.values():
        counts[words] += 1
    handles = [
        Patch(facecolor=colour_of[words], edgecolor="#8a8a8a", linewidth=0.5,
              label=f"{words} ({counts[words]})")
        for words in order
    ]
    legend = ax.legend(
        handles=handles,
        title=f"{atlas_text.SPATIAL_LEGEND_TITLE}\n({atlas_text.SPATIAL_LEGEND_MEANING})",
        loc="center left", bbox_to_anchor=(1.005, 0.5), frameon=False,
        fontsize=7.6, title_fontsize=8, labelspacing=0.8,
    )
    legend._legend_box.align = "left"

    titles(
        ax,
        f"Nigeria: {atlas_text.SPATIAL_MAP_TITLE}",
        f"{atlas_text.SPATIAL_MAP_SUBTITLE}. {atlas_text.SPATIAL_MAP_READING}",
        width=104,
    )
    technical = spatial_context_line(global_rows)
    ax.text(
        0, -0.05, "\n".join(textwrap.wrap(technical, 104)),
        transform=ax.transAxes, fontsize=7.4, color="#555555", va="top",
    )
    ax.set_xlim(2.4, 15.0)
    ax.set_ylim(3.9, 14.2)
    ax.set_aspect(1.0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(PREVIEW / "2_where_poverty_clusters.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  2_where_poverty_clusters.png")


# ------------------------------------------------- the reference tab (sheet 3)
def visual_reference_table() -> list[str]:
    """The QA gate for the reference tabs: every cell present, columns still aligned.

    The tabs are text, not charts, so this is not a pixel-for-pixel preview of the
    Tableau dashboards -- it is the same rows, the same three columns and the same
    wrapping width, one PNG per part, named in tab order. What it catches is what the
    tab can actually get wrong: a missing cell, an empty group, or a cell so long that
    its row grows past its neighbours and the columns stop lining up. Rendering it as
    a monospace grid is deliberate: the question this gate answers is "is anything
    missing or misfiled", and a grid shows that at a glance where a chart of the same
    words would not.

    Returns the file names it wrote, so the caller does not keep a second copy of the
    naming rule.
    """
    column_chars = [34, 42, 42]
    written: list[str] = []

    def wrapped(text: str, width: int) -> list[str]:
        return textwrap.wrap(text, width=width) or [""]

    groups = atlas_text.table_rows()
    assert len(groups) == 3, f"expected three reference tabs, got {len(groups)}"
    seen = 0
    for part, (heading, intro, rows) in enumerate(groups, 1):
        assert rows, f"the reference tab {heading!r} has no rows"
        lines: list[str] = []

        def row_of(cells: list[list[str]], _lines: list[str] = lines) -> None:
            height = max(len(cell) for cell in cells)
            for index in range(height):
                _lines.append("  ".join(
                    (cells[column][index] if index < len(cells[column]) else "")
                    .ljust(column_chars[column])
                    for column in range(len(column_chars))
                ))

        lines.extend(wrapped(atlas_text.TABLE_INTRO, sum(column_chars) + 4))
        lines.append("")
        lines.append(f"PART {part} OF {len(groups)} \u00b7 {heading.upper()}")
        lines.extend(wrapped(intro, sum(column_chars) + 4))
        lines.append("")
        row_of([wrapped(header, column_chars[i])
                for i, header in enumerate(atlas_text.TABLE_HEADERS)])
        for row in rows:
            for column, text in row.items():
                assert text.strip(), f"{heading}: empty {column!r} in {row['word']!r}"
            row_of([
                [row["word"].upper()] + wrapped(row["formula"], column_chars[0]),
                wrapped(row["meaning"], column_chars[1]),
                wrapped(row["method"], column_chars[2]),
            ])
            seen += 1
            lines.append("")

        slug = re.sub(r"[^a-z0-9]+", "_", heading.lower()).strip("_")
        name = f"{2 + part}_{slug}.png"
        figure = plt.figure(figsize=(13.5, max(4.0, len(lines) * 0.135)))
        figure.text(0.005, 1.0, "\n".join(lines), family="monospace", fontsize=7.2,
                    va="top", ha="left")
        figure.savefig(PREVIEW / name, dpi=130, bbox_inches="tight")
        plt.close(figure)
        print(f"  {name}")
        written.append(name)

    assert seen == 44, f"the reference tabs carry {seen} rows, expected 44"
    return written


def main() -> int:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    rows = read(ATLAS)
    assert len(rows) == 37, f"expected 37 states, got {len(rows)}"
    atlas_text.table_rows()  # asserts every reference-tab cell is present

    print("rendering previews:")
    visual_choropleth(rows)
    visual_spatial_clusters()
    # The kept set is what this run wrote, not a second list that can drift from it.
    kept = {"1_where_poverty_sits.png", "2_where_poverty_clusters.png"}
    kept.update(visual_reference_table())

    # The directory holds this stage's output and nothing else, so a preview that a
    # withdrawn sheet used to produce is removed here rather than left to look like
    # current output. The naming rule (N_name.png, in tab order) is this stage's.
    for stale in sorted(PREVIEW.glob("*.png")):
        if stale.name not in kept:
            stale.unlink()
            print(f"  removed withdrawn preview {stale.name}")

    print(f"\nwrote {len(kept)} previews to {PREVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
