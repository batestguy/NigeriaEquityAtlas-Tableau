"""Stage 5 -- render the workbook's visuals as PNGs before Tableau is involved.

This is the QA gate. A colour that drifts, a state whose type changes, or a table row
with a missing cell is caught here, in Python, before the workbook is opened -- which
is what a gate is for.

Eight previews, in tab order, one per published view (nine sheets since the
KPI board joined 2026-10-23; the three reference tabs are one sheet in three
files):

1. Where poverty sits            filled choropleth, the five MPI bands the
                                 workbook draws, in the colours it draws them
2. Where poverty clusters        the same rings filled by neighbourhood type
                                 (stage 9), in the four colours the sheet uses
3. How poverty is made up        the stacked composition bar (docs/
                                 SHEET_DIMENSIONS.md): the three dimension
                                 shares per state, bars in the workbook's
                                 hand-computed MPI order, in the sheet's three
                                 colours
4. A state over time             the time panel (docs/SHEET_TIME_PANEL.md): the
                                 default state's six whitelisted measures over the
                                 four rounds, in the six colours the sheet assigns
5. What the words mean           reference tab 1 of 3, as a monospace grid
6. The list of basic needs       reference tab 2 of 3, same gate
7. How we did it                 reference tab 3 of 3 -- the gate for a table
                                 is missing cells and misfiled rows
8. Where Nigeria stands          the KPI board (docs/SHEET_KPI.md): one row
                                 per benchmarked KPI, one dot per reference
                                 point, in the sheet's three colours
9. How measures pair             the pairs board (docs/SHEET_PAIRS.md) on its
                                 default pair, green circles, points only

The reference table is one table shipped as three tabs, cut on the three groups it
already had: as a single dashboard it measured 2000 x 8720 px (docs/FIX_LEDGER.md W2).
The gate follows the tabs, so the numbering is per-part and not per-table.

Previews 2-6 and 9 used to exist: the conflict overlay, the gradient plot, the
radar, the party panel and the Moran scatter. Their sheets were withdrawn on
2026-10-18 (docs/FIX_LEDGER.md W1) and the previews went with them -- a gate for
a sheet that is not in the workbook cannot gate anything. The original dimension
breakdown also went that day, but it came back on 2026-10-22 rebuilt to a frozen
design (preview 3 above); unlike the others its gate survived, rebuilt with it.
The remaining analyses still run: stage 8's party test is pre-registered and its
result is reported in docs/party_alignment.md, and the spatial test behind
preview 2 is reported in docs/spatial_analysis.md.

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
import matplotlib.image as mtpl_image  # noqa: E402
from matplotlib.offsetbox import AnnotationBbox, OffsetImage  # noqa: E402
from matplotlib.patches import Patch, Polygon as MplPolygon  # noqa: E402

import numpy as np  # noqa: E402
from scipy import stats  # noqa: E402
import atlas_text  # noqa: E402
from common import (  # noqa: E402
    DOCS,
    PROCESSED,
    RAW,
    spatial_context_line,
)

PREVIEW = DOCS / "preview"
ATLAS = PROCESSED / "mpi_atlas_2021.csv"
PAIRS = PROCESSED / "mpi_pairs_148.csv"
KPI_DOTS = PROCESSED / "kpi_dots.csv"

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
        f"{atlas_text.MPI_MAP_SUBTITLE} \u00b7 36 states + FCT \u00b7 colour is the "
        f"{atlas_text.MPI_LEGEND_TITLE.lower()} ({atlas_text.MPI_LEGEND_EXPANSION}) "
        f"\u2014 {atlas_text.MPI_LEGEND_MEANING}. The headcount share H is a different "
        "number and is not this colour: OPHI's median relative SE is 15% and all 36 "
        "adjacent rank pairs overlap at 95%, which is why the map bands rather than "
        "ranking; the exact value and its interval are in the workbook's hover.",
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


# ------------------------------------------------- the composition bar (sheet 3)
def visual_dimension_bars(rows: list[dict[str, str]]) -> None:
    """The QA gate for "How poverty is made up": same shares, same order, same colours.

    The sheet stacks each state's MPI split across OPHI's three dimensions -- an
    identity, so the bar always totals 100 -- listed in the hand-computed MPI
    order stage 6 ships as the manual sort dictionary. The gate draws the same
    bars from the same atlas rows with the same three colours sourced from
    `atlas_text.DIMENSION_SHARES`, so a colour that drifts, a share that breaks
    the identity, or a state lost from the order fails here before Tableau
    opens. The drawn subset is the workbook's DEFAULT view (the user's
    2026-10-22 decision): the five poorest states and the first twelve of the
    Other 25, MPI order, with the remaining 20 one tick away on the sheet's
    state filter -- the filter membership is stage 6's to prove, this gate
    proves the 17 bars it draws. The gate labels the wide segments the way the
    sheet's datalabel rule renders its numbers, in white, so a reader comparing
    the two images sees the same thing; the ordering is the point estimate's,
    and all 36 adjacent rank pairs overlap at 95%, which is what the frozen
    subtitle and the footer both say.
    """
    share_fields = [(f, caption) for f, caption, _colour in atlas_text.DIMENSION_SHARES]
    colour_of = {caption: colour for _f, caption, colour in atlas_text.DIMENSION_SHARES}
    assert len(atlas_text.DIMENSION_SHARES) == 3, "expected the three OPHI dimensions"
    assert len(colour_of) == 3, "DIMENSION_SHARES repeats a caption"
    assert len({c for _f, _c, c in atlas_text.DIMENSION_SHARES}) == 3, "colours repeat"

    parsed: list[tuple[str, float, list[float], str]] = []
    for row in rows:
        shares = [float(row[field]) for field, _caption in share_fields]
        assert all(0 <= s <= 100 for s in shares), (
            f"{row['state']}: a dimension share outside 0-100"
        )
        assert abs(sum(shares) - 100) < 0.5, (
            f"{row['state']}: shares total {sum(shares):.2f}, expected 100"
        )
        assert row["mpi_label"].strip() and row["dim_hover"].strip(), (
            f"{row['state']}: the composition sheet's hover strings are blank"
        )
        parsed.append((row["state"], float(row["mpi"]), shares,
                       row["poverty_group"]))
    assert len(parsed) == 37, f"composition gate has {len(parsed)} states, expected 37"
    parsed.sort(key=lambda t: -t[1])
    # The default view (see the docstring): all-per-state asserts above ran on
    # the full 37; the draw below is the 17 the workbook shows on load.
    parsed = parsed[:atlas_text.COMPOSITION_DEFAULT_TOP] + parsed[12:12 + atlas_text.COMPOSITION_DEFAULT_REST]
    expected_default = atlas_text.COMPOSITION_DEFAULT_TOP + atlas_text.COMPOSITION_DEFAULT_REST
    assert len(parsed) == expected_default, (
        f"default view has {len(parsed)} bars, expected {expected_default}"
    )

    # The workbook nests poverty_group above state on Rows, so the two groups
    # print as pane headers with a divider between them. The gate mirrors the
    # marker the user asked for (2026-10-22): the group name on a header slot
    # of its own (the way Tableau's pane headers own a strip) and a divider
    # under each block's last bar.
    slots: list[tuple[str, str]] = []
    last_grp: str | None = None
    for state, _mpi, _shares, grp in parsed:
        if grp != last_grp:
            slots.append(("hdr", grp))
            last_grp = grp
        slots.append(("bar", state))
    headers = [val for kind, val in slots if kind == "hdr"]
    assert len(headers) == 2, (
        f"the default view should span both poverty groups, saw {set(headers)}"
    )
    by_state = {state: (shares, grp) for state, _mpi, shares, grp in parsed}
    ordered = [(state,) + by_state[state] for kind, state, in slots if kind == "bar"]
    assert [st for kind, st in slots if kind == "bar"] == [st for st, _sh, _g in ordered]

    fig, ax = plt.subplots(figsize=(8.2, 10.6 * len(slots) / 37))
    ypos = [i for i, (kind, _val) in enumerate(slots) if kind == "bar"]
    left = [0.0] * len(ypos)
    # Reversed list order: the first render (Tableau Public 2026.2, 2026-10-22)
    # stacks the LAST declared measure nearest the axis -- Living standards,
    # then Health, then Education -- so the gate stacks the same way, from the
    # same single-source list. The colours bind by measure, not by position, so
    # the two surfaces agree either way; this keeps the segment order too.
    for index, (_field, caption, _colour) in enumerate(reversed(atlas_text.DIMENSION_SHARES)):
        which = len(atlas_text.DIMENSION_SHARES) - 1 - index
        widths = [shares[which] for _state, shares, _grp in ordered]
        ax.barh(ypos, widths, left=left, height=0.72, color=colour_of[caption],
                edgecolor="white", linewidth=0.3, label=caption, zorder=3)
        # The workbook labels every segment with its value in white (its
        # datalabel rule); the gate labels the segments wide enough to carry
        # one, white, so a reader comparing the two images sees the same thing.
        for y, w, l in zip(ypos, widths, left):
            if w >= 7:
                ax.text(l + w / 2, y, f"{w:.1f}", ha="center", va="center",
                        fontsize=6.6, color="white", zorder=4)
        left = [l + w for l, w in zip(left, widths)]

    # The group headers sit on their own strip, bold, above their block; the
    # divider runs at the top edge of each header except the first, i.e. one
    # pane line between "Poorest 12" and "Other 25" -- the workbook's pane
    # divider mirrored.
    for i, (kind, val) in enumerate(slots):
        if kind == "hdr":
            ax.text(0, i, val, transform=ax.get_yaxis_transform(), ha="left",
                    va="center", fontsize=8.4, fontweight="bold",
                    color="#222222", zorder=6)
            if i > 0:
                ax.axhline(i - 0.5, color="#444444", linewidth=1.3, zorder=5)

    ax.set_yticks(ypos)
    ax.set_yticklabels([st for kind, st in slots if kind == "bar"], fontsize=7.2)
    ax.invert_yaxis()  # highest MPI at the top: the manual sort dictionary's order
    ax.set_xlim(0, 100)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], fontsize=8)
    ax.grid(axis="x", color="#dddddd", linewidth=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)

    legend = ax.legend(
        title="The three areas\n(share of each state's MPI)",
        loc="center left", bbox_to_anchor=(1.005, 0.5), frameon=False,
        fontsize=7.6, title_fontsize=8, labelspacing=0.8,
    )
    legend._legend_box.align = "left"

    titles(ax, atlas_text.DIMENSIONS_TITLE, atlas_text.DIMENSIONS_SUBTITLE, width=104)
    ax.text(
        0, -0.06, "\n".join(textwrap.wrap(atlas_text.DIMENSIONS_CAVEAT, 104)),
        transform=ax.transAxes, fontsize=7.4, color="#555555", va="top",
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "3_how_poverty_is_made_up.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  3_how_poverty_is_made_up.png")


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
        # Named from 5: the gate's naming rule is "N_name.png, in tab order",
        # and the reference parts are tabs 5-7 (maps 1-2, the composition bar 3,
        # the time panel 4).
        name = f"{4 + part}_{slug}.png"
        figure = plt.figure(figsize=(13.5, max(4.0, len(lines) * 0.135)))
        figure.text(0.005, 1.0, "\n".join(lines), family="monospace", fontsize=7.2,
                    va="top", ha="left")
        figure.savefig(PREVIEW / name, dpi=130, bbox_inches="tight")
        plt.close(figure)
        print(f"  {name}")
        written.append(name)

    # 44 until 2026-10-25, when the cluster map's four frozen reader lines moved
    # off its hover and into a method row (docs/spatial_preregistration.md,
    # amendment 3) -- the pre-registration requires the frozen wording to stay in
    # the workbook, so the row count rose rather than the text being dropped.
    assert seen == 45, f"the reference tabs carry {seen} rows, expected 45"
    return written


# ------------------------------------------------------- the time panel (sheet 3)
def visual_state_over_time() -> None:
    """The QA gate for "A state over time": same measures, same colours, same state.

    The sheet is a Measure Names / Measure Values panel -- one line per ticked
    measure over the four harmonised rounds, one y-axis per measure. The gate draws
    exactly what sheet 3 draws by default: `atlas_text.PANEL_DEFAULT_STATE` on the
    six `atlas_text.PANEL_MEASURES` rows, in the sheet's six colours, from the same
    `mpi_trends_panel.csv` the extract packages. A colour that drifts, a measure
    whose caption changes in one place but not the other, or a default state the
    panel does not contain, is caught here before Tableau is opened.

    What it deliberately does NOT do: fit a trend. Line + markers is the whole
    sentence; a slope through four points is the withdrawn sheet's defect
    (docs/FIX_LEDGER.md W1), and the gate must not re-import it under matplotlib's
    name either. Axes are unscaled per measure, as the sheet's per-measure axes are.
    """
    panel = read(PROCESSED / "mpi_trends_panel.csv")
    assert len(panel) == 148, f"panel has {len(panel)} rows, expected 148"
    years = sorted({int(r["survey_year"]) for r in panel})
    assert years == [2013, 2016, 2018, 2021], f"unexpected rounds {years}"
    per_state: dict[str, list[dict[str, str]]] = {}
    for row in panel:
        per_state.setdefault(row["state"], []).append(row)
    assert len(per_state) == 37, f"panel covers {len(per_state)} states, expected 37"
    assert all(len(rows) == 4 for rows in per_state.values()), (
        "each state must have one row per round in the panel"
    )
    # The rank columns are what the marks show, so the gate recomputes every one
    # of them from the panel's own value columns -- the same independent read
    # stage 6 runs against the extract (04_merge.py's RANK_FIELDS, copied on
    # purpose: a stage-4 edit that re-points a rank at the wrong source field is
    # exactly what this wants to catch).
    RANK_FIELDS: dict[str, str] = {
        "rank_mpi": "mpi",
        "rank_headcount": "headcount_ratio_pct",
        "rank_intensity": "intensity_pct",
        "rank_events": "events_per_100k",
        "rank_deaths": "fatalities_per_100k",
        "rank_temp": "temp_mean_c",
    }
    for year in years:
        yr_rows = [r for r in panel if int(r["survey_year"]) == year]
        for rank_field, value_field in RANK_FIELDS.items():
            yr_rows.sort(key=lambda r: float(r[value_field]), reverse=True)
            rank = 0
            for i, row in enumerate(yr_rows):
                if i and float(row[value_field]) != float(yr_rows[i - 1][value_field]):
                    rank = i
                assert int(row[rank_field]) == rank + 1, (
                    f"{rank_field} in {row['state']} {year} is "
                    f"{row[rank_field]}, recomputation says {rank + 1}"
                )

    name = atlas_text.PANEL_DEFAULT_STATE
    assert name in per_state, f"default state {name!r} missing from the panel"
    rows = sorted(per_state[name], key=lambda r: int(r["survey_year"]))
    measures = atlas_text.PANEL_MEASURES
    assert len(measures) == 6, f"expected the freeze's six measures, got {len(measures)}"
    assert len({m[0] for m in measures}) == 6, "PANEL_MEASURES repeats a column"
    assert len({m[2] for m in measures}) == 6, "PANEL_MEASURES repeats a colour"
    assert len({m[1] for m in measures}) == 6, "PANEL_MEASURES repeats a caption"
    assert set(m[0] for m in measures) == set(RANK_FIELDS), (
        "the gate's whitelist and rank map must name the same columns"
    )

    fig, axes = plt.subplots(2, 3, figsize=(12.6, 7.0))
    for ax, (field, caption, colour) in zip(axes.flat, measures):
        values = [int(float(r[field])) for r in rows]
        # One identical check to the one 06_build_twb.py runs on the extract: a
        # blank measure cell cannot reach the workbook without failing here first.
        for r, v in zip(rows, values):
            assert 1 <= v <= 37, f"rank out of 1-37 in {field} for {name} {r['survey_year']}"
        ax.plot(years, values, color=colour, linewidth=1.6, marker="o",
                markersize=4.5, zorder=3)
        ax.set_xticks(years)
        ax.set_xticklabels([str(y) for y in years], fontsize=8)
        ax.set_ylim(0, 38)  # ranks 1-37, same span on every pane
        ax.grid(axis="y", color="#dddddd", linewidth=0.6, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
        wrapped = textwrap.fill(caption, 30)
        ax.set_ylabel(wrapped, fontsize=8.6, color=INK)
        # The point count is the sentence: four rounds, nothing fitted. The label
        # is the R-prefixed rank the workbook's number format prints -- one
        # formatting of the same integer on both surfaces.
        for y, v in zip(years, values):
            ax.annotate(f"R{v}", (y, v), textcoords="offset points",
                        xytext=(0, 8), ha="center", fontsize=7.0, color="#555555",
                        zorder=4)
    titles_placeholder = None  # noqa: F841 (title drawn by fig.suptitle below)
    fig.suptitle(f"Nigeria, {name}: six measures' ranks over the four survey rounds",
                 fontsize=13, fontweight="700", x=0.07, y=0.985, ha="left")
    fig.text(
        0.065, 0.945,
        textwrap.fill(
            "What it shows: this state's rank of 37 on each measure, round by "
            "round (R1 = the measure's highest value). Read it as level, not "
            "trend: adjacent rank pairs overlap at 95%. Stars on the hover flag "
            "movement OPHI's change test supports. Conflict is UCDP GED, "
            "temperature is the capital's.",
            118,
        ),
        fontsize=8.6, color="#555555", va="top", ha="left", linespacing=1.4,
    )
    fig.tight_layout(rect=(0, 0, 1, 0.83))
    # Named 4_: the gate's naming rule is "N_name.png, in tab order", and this
    # sheet is tab 4 since the composition bar took tab 3 (2026-10-22) -- the
    # three reference parts therefore number 5-7.
    fig.savefig(PREVIEW / "4_state_over_time.png", dpi=170)
    plt.close(fig)
    print("  4_state_over_time.png")


def visual_kpi_board() -> None:
    """8. "Where Nigeria stands" -- the silhouette board against WHO / SDG refs.

    One row per benchmarked KPI, one map silhouette per reference point
    (Nigeria, sub-Saharan Africa where WDI publishes it, world), at the
    row-normalised position `pos` from kpi_dots.csv. The silhouettes are the
    same files the workbook embeds (atlas_text.KPI_SHAPE_FILES ->
    data/reference/kpi_shapes), pasted with AnnotationBbox -- so the gate
    catches what the extract can get wrong: a mark out of (0, 1], a series
    missing, a row whose marks lost their neighbours, or a silhouette file
    that stopped existing. Marks draw in the CSV's row order per row, so
    Nigeria's silhouette lands on top exactly as the sheet draws it; colours
    bind to atlas_text.KPI_SERIES so gate and workbook palette cannot drift.
    """
    col = read(KPI_DOTS)
    # 2026-10-25: seven of the 27 marks are DIRECTION GUIDES (one coloured arrow
    # per row, pointing the way that is good on that row). They carry no hover
    # and no label, so they are validated as guides and drawn as arrows rather
    # than as reference points.
    colours = dict(atlas_text.KPI_SERIES)
    assert len(col) == 20, f"KPI dots gate has {len(col)} rows, expected 20"
    rows: list[tuple[str, list[tuple[str, float, str]]]] = []
    for row in col:
        pos = float(row["pos"])
        assert 0 < pos <= 1.0, f"{row['kpi']} / {row['series']}: pos {pos:.3f} out of (0, 1]"
        assert row["series"] in colours, (
            f"series {row['series']!r} has no colour in atlas_text.KPI_SERIES"
            " or atlas_text.KPI_GUIDE"
        )
        assert row["hover"].strip(), f"{row['kpi']}: empty hover"
        # The printed number is the mark's TRUE share of the row's largest
        # reference; `pos` may be dodged left to clear a neighbour, so the
        # gate must print pos_label the way the sheet does, not pos.
        label = row["pos_label"].strip()
        assert label, f"{row['kpi']} / {row['series']}: empty pos_label"
        assert len(label.split(".")[-1]) == 1, (
            f"{row['kpi']} / {row['series']}: pos_label {label!r} is not one decimal"
        )
        if not rows or rows[-1][0] != row["kpi"]:
            rows.append((row["kpi"], []))
        rows[-1][1].append((row["series"], pos, label))
    assert len(rows) == 7, f"KPI dots gate has {len(rows)} rows of marks, expected 7"

    fig, ax = plt.subplots(figsize=(9.6, 6.0))
    # Bottom reserved for a horizontal legend OUTSIDE the plot: the older
    # lower-right legend sat on top of the electricity row's world mark, which
    # is the one thing a QA gate must never do (2026-10-24 user pass: "labels
    # ... not overlapping").
    fig.subplots_adjust(left=0.295, right=0.985, top=0.74, bottom=0.17)
    names = [r[0] for r in rows]
    shapes_dir = Path(__file__).resolve().parent.parent / "data" / "reference" / "kpi_shapes"
    assert atlas_text.KPI_SHAPE_FILES and set(atlas_text.KPI_SHAPE_FILES) == set(colours), (
        "KPI_SHAPE_FILES and KPI_SERIES name different member sets"
    )
    images = {}
    for member, fname in atlas_text.KPI_SHAPE_FILES.items():
        path = shapes_dir / fname
        assert path.exists(), (
            f"missing silhouette {fname}: run scripts/07_kpi_reference.py first"
        )
        images[member] = mtpl_image.imread(str(path))
    handle_seen: set[str] = set()
    handles = []
    # zoom tracks the sheet's mark-box feel: at 170 dpi the icon canvas spans
    # ~70% of a row band (the fourth 2026-10-23 pass made the maps bigger
    # again, size factor 4.0), so the maps read at row-label scale.
    zoom = 0.115
    for i, (_name, marks) in enumerate(rows):
        y = len(rows) - 1 - i  # first row of the CSV on top, like the sheet
        for series, pos, value_label in marks:
            ab = AnnotationBbox(
                OffsetImage(images[series], zoom=zoom),
                (pos, y), frameon=False, zorder=3,
            )
            ax.add_artist(ab)
            # The sheet prints each mark's TRUE share at one decimal beside it
            # (the 2026-10-23 label pass); the gate prints the same string from
            # the same column -- pos_label, never the dodged `pos` -- so a
            # dodged mark still prints its own value and the two cannot drift.
            ax.annotate(value_label, (pos, y), xytext=(0, 15),
                        textcoords="offset points", ha="center",
                        fontsize=6.0, color="#555555", zorder=4)
            if series not in handle_seen:
                handle_seen.add(series)
                handles.append(plt.Line2D([], [], marker="o", linestyle="none",
                                          markersize=8.5,
                                          markerfacecolor=colours[series],
                                          markeredgecolor="none", label=series))
    ax.set_yticks(range(len(rows)), labels=list(reversed(names)), fontsize=8.6)
    ax.set_xlim(0, 1.04)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    # The axis returned in the third 2026-10-23 user pass, with ticks pinned
    # to 0 / 0.5 / 1 (a manual tick spacing of 0.5 on the sheet); the gate's
    # matplotlib default happened to match, so the ticks are stated explicitly.
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xlabel("Share of the row's largest reference", fontsize=8)
    ax.grid(axis="x", color="#dddddd", linewidth=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    fig.legend(handles=handles, loc="lower center", ncol=3, frameon=False,
               fontsize=8, title="Reference point (2021)", title_fontsize=8,
               bbox_to_anchor=(0.64, 0.005))

    titles(ax, atlas_text.KPI_TITLE, atlas_text.KPI_SUBTITLE, width=84)
    # Named 8_: the gate's naming rule is "N_name.png, in tab order" -- tab 8,
    # after the three reference tabs (5-7); the pairs board moves to 9.
    fig.savefig(PREVIEW / "8_where_nigeria_stands.png", dpi=170)
    plt.close(fig)
    print("  8_where_nigeria_stands.png")


def quadratic_fit_band(
    xs: list[float], ys: list[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Least-squares quadratic through a pane's marks, with its 95% band.

    The same object the workbook's trend line draws (``fit='polynomial'``,
    ``degree='2'``, confidence bands on): a degree-2 least-squares fit of y on
    x over the pane's own marks, and the t-based confidence band for the fitted
    MEAN at each x (Tableau's confidence bands are the same construction).

    Descriptive only. Nothing returned here is reported: no slope is printed,
    no coefficient, no correlation, no p-value -- the freeze's guardlist stands
    (docs/SHEET_PAIRS.md). It exists so the gate draws the line the sheet draws.
    """
    x = np.asarray(xs, dtype=float)
    y = np.asarray(ys, dtype=float)
    design = np.column_stack([x ** 2, x, np.ones_like(x)])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ coef
    dof = len(x) - design.shape[1]
    assert dof > 0, f"a quadratic needs 4+ marks; this pane has {len(x)}"
    sigma2 = float(resid @ resid) / dof
    cov = sigma2 * np.linalg.inv(design.T @ design)
    grid = np.linspace(float(x.min()), float(x.max()), 200)
    gdesign = np.column_stack([grid ** 2, grid, np.ones_like(grid)])
    se = np.sqrt(np.einsum("ij,jk,ik->i", gdesign, cov, gdesign))
    crit = float(stats.t.ppf(0.975, dof))
    fit = gdesign @ coef
    return grid, fit, fit - crit * se, fit + crit * se


def visual_pairs_board() -> None:
    """9. The pairs board on its default pair, the gate for colour and shape.

    One green circle per state-round, the two poverty-group panes stacked the
    way the workbook stacks them ('Other 25' above 'Poorest 12' -- the group
    field's alphabetical order, P5), one quadratic trend line per pane with its
    95% confidence band, no size channel. A trend line was ADDED to the sheet on
    2026-10-24 at the author's request, against the freeze's original "no fit"
    guardlist; the guardlist's substance survives in the form the line takes --
    the line is a description of each pane's own marks, and no slope, no
    coefficient, no correlation and no claim is printed anywhere
    (docs/SHEET_PAIRS.md, "Trend line"). Colour binds to
    atlas_text.PAIRS_POINT_COLOUR and the line to PAIRS_TREND_COLOUR so the gate
    and the sheet cannot disagree.
    """
    col = read(PAIRS)
    assert len(col) == 148, f"pairs gate has {len(col)} rows, expected 148"
    by_group: dict[str, list[tuple[float, float]]] = {}
    for row in col:
        h, y = float(row["headcount_ratio_pct"]), float(row["log1p_events_per_100k"])
        assert 0 <= h <= 100 and y >= 0, f"{row['state']}: out-of-range pair"
        by_group.setdefault(row["poverty_group"], []).append((h, y))
    assert set(by_group) == {atlas_text.POVERTY_GROUP_TOP, atlas_text.POVERTY_GROUP_REST}

    fig, axes = plt.subplots(
        2, 1, figsize=(7.4, 7.4), sharex=True,
        gridspec_kw={"height_ratios": [
            len(by_group[atlas_text.POVERTY_GROUP_REST]),
            len(by_group[atlas_text.POVERTY_GROUP_TOP]),
        ]},
    )
    groups = (atlas_text.POVERTY_GROUP_REST, atlas_text.POVERTY_GROUP_TOP)
    for ax, group in zip(axes, groups):
        pts = by_group[group]
        ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=28,
                   color=atlas_text.PAIRS_POINT_COLOUR, edgecolors="none", zorder=3)
        grid, fit, lo, hi = quadratic_fit_band(
            [p[0] for p in pts], [p[1] for p in pts],
        )
        ax.fill_between(grid, lo, hi, color=atlas_text.PAIRS_TREND_COLOUR,
                        alpha=0.10, linewidth=0, zorder=1)
        ax.plot(grid, fit, color=atlas_text.PAIRS_TREND_COLOUR, linewidth=1.5,
                solid_capstyle="round", zorder=4)
        ax.set_ylabel(group, fontsize=8)
        ax.grid(axis="both", color="#dddddd", linewidth=0.6, zorder=0)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Other 25 \u2014 pair Y (log(1+rate))", fontsize=8)
    axes[1].set_xlabel("Pair X \u2014 the dropdowns choose it", fontsize=8)
    axes[1].set_ylabel("Poorest 12 \u2014 pair Y (log(1+rate))", fontsize=8)

    # Figure-level title (two axes, so the shared titles() helper's single-axes
    # assumptions don't apply): title left, subtitle wrapped under it, layout
    # reserved above the top pane.
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.suptitle(atlas_text.PAIRS_TITLE, fontsize=13, fontweight="700",
                 ha="left", x=0.04, y=0.985)
    fig.text(0.04, 0.955, "\n".join(textwrap.wrap(atlas_text.PAIRS_SUBTITLE, 112)),
             fontsize=8.6, color="#555555", va="top", ha="left", linespacing=1.35)
    # Named 9_: the gate's naming rule is "N_name.png, in tab order", and the
    # pairs board is tab 9 -- last, after the KPI board took tab 8 (2026-10-23,
    # docs/SHEET_KPI.md); the three reference tabs are 5-7.
    fig.savefig(PREVIEW / "9_how_measures_pair.png", dpi=170)
    plt.close(fig)
    print("  9_how_measures_pair.png")


def main() -> int:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    rows = read(ATLAS)
    assert len(rows) == 37, f"expected 37 states, got {len(rows)}"
    atlas_text.table_rows()  # asserts every reference-tab cell is present

    print("rendering previews:")
    visual_choropleth(rows)
    visual_spatial_clusters()
    visual_dimension_bars(rows)
    visual_state_over_time()
    visual_kpi_board()
    visual_pairs_board()
    # The kept set is what this run wrote, not a second list that can drift from it.
    kept = {"1_where_poverty_sits.png", "2_where_poverty_clusters.png",
            "3_how_poverty_is_made_up.png", "4_state_over_time.png",
            "8_where_nigeria_stands.png", "9_how_measures_pair.png"}
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
