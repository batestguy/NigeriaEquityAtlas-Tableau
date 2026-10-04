"""Stage 5 -- render the five spec visuals as PNGs before Tableau is involved.

This is the QA gate. If a stacked bar looks wrong or a scatter shows an
implausible relationship, the bug is in Python where it is cheap to fix, not
buried in hand-authored Tableau XML. It also serves as the visual reference for
what each Tableau sheet is meant to show.

The five visuals follow the project spec, section 1.4:

  1. State choropleth        filled map, MPI incidence (headcount ratio)
  2. Dimension breakdown     stacked bar, the three dimension contributions
  3. Conflict overlay        scatter, MPI vs Conflict Exposure Index
  4. Climate nexus           MPI vs baseline precipitation (not a single year's
                             anomaly -- see the note in visual 4)
  5. State comparison        radar, one state against the 37-state mean

Visual 4 deliberately departs from the spec, which asked for temperature
anomaly. The per-year anomaly correlation with MPI flips sign between survey
rounds (+0.81 in 2013, -0.43 in 2021) because it is weather noise, while
baseline precipitation holds at rho -0.80. Plotting the anomaly would have
produced a striking but meaningless chart.
"""

from __future__ import annotations

import csv
import json
import math
import textwrap
from pathlib import Path
from typing import Any

import matplotlib
from matplotlib.axes import Axes

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MplPolygon  # noqa: E402

from common import DOCS, PROCESSED, RAW  # noqa: E402

PREVIEW = DOCS / "preview"
ATLAS = PROCESSED / "mpi_atlas_2021.csv"
PANEL = PROCESSED / "mpi_trends_panel.csv"

HEALTH, EDUCATION, LIVING = "#b2182b", "#2166ac", "#1b7837"
GRID = "#d9d9d9"
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


def seq(value: str) -> list[float]:
    return [float(v) for v in value.split()]


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


# ---------------------------------------------------------------- visual 1
def visual_choropleth(rows: list[dict[str, str]]) -> None:
    gj = json.loads((RAW / "nga_adm1.geojson").read_text(encoding="utf-8"))
    value = {r["pcode"]: float(r["headcount_ratio_pct"]) for r in rows}
    label = {r["pcode"]: r["state"] for r in rows}

    fig, ax = plt.subplots(figsize=(8.6, 9.4))
    vals = list(value.values())
    norm = matplotlib.colors.Normalize(vmin=0, vmax=max(vals))
    cmap = plt.get_cmap("YlOrRd")

    for feat in gj["features"]:
        pcode = feat["properties"]["shapeISO"]
        if pcode not in value:
            continue
        colour = cmap(norm(value[pcode]))
        for ring in feature_rings(feat["geometry"]):
            ax.add_patch(MplPolygon(ring, closed=True, facecolor=colour, edgecolor="white", linewidth=0.6))

    centroids = {r["pcode"]: (float(r["lat"]), float(r["lon"])) for r in rows}
    # Nudge labels in the crowded south-east so they do not overprint each other.
    nudges = {
        "NG-DE": (0.0, -0.42), "NG-AN": (0.0, 0.36), "NG-AK": (-0.34, -0.28),
        "NG-CR": (0.14, 0.22), "NG-IM": (-0.34, -0.26), "NG-KN": (-0.30, -0.34),
        "NG-JI": (0.12, 0.32), "NG-AB": (-0.30, 0.20), "NG-BE": (0.0, 0.30),
        "NG-EN": (0.30, 0.18), "NG-RI": (-0.22, -0.30), "NG-BY": (-0.24, -0.24),
        "NG-SO": (0.0, 0.16),
    }
    for pcode, (lat, lon) in centroids.items():
        share = value[pcode]
        dlat, dlon = nudges.get(pcode, (0.0, 0.0))
        ax.text(
            lon + dlon, lat + dlat, label[pcode], fontsize=6.6, ha="center", va="center",
            color="white" if share > 45 else INK, fontweight="bold",
        )

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, fraction=0.030, pad=0.02)
    cb.set_label("Headcount ratio, % of population multidimensionally poor", fontsize=8.5)
    cb.outline.set_visible(False)

    titles(
        ax,
        "Nigeria: multidimensional poverty incidence by state",
        "MICS 2021 · 36 states + FCT · headcount ratio H (% of population "
        "multidimensionally poor). Bauchi, Jigawa, Kebbi and Sokoto carry the "
        "highest incidence; Lagos the lowest.",
        width=104,
    )
    ax.set_xlim(2.4, 15.0)
    ax.set_ylim(3.9, 14.2)
    ax.set_aspect(1.0)
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(PREVIEW / "1_choropleth_mpi.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  1_choropleth_mpi.png")


# ---------------------------------------------------------------- visual 2
def visual_dimensions(rows: list[dict[str, str]]) -> None:
    data = sorted(rows, key=lambda r: float(r["mpi"]), reverse=True)
    names = [r["state"] for r in data]
    h = [float(r["contrib_health_pct"]) for r in data]
    e = [float(r["contrib_education_pct"]) for r in data]
    ls = [float(r["contrib_living_standards_pct"]) for r in data]
    y = list(range(len(data)))

    fig, ax = plt.subplots(figsize=(8.2, 9.6))
    ax.barh(y, h, color=HEALTH, label="Health", height=0.72)
    ax.barh(y, e, left=h, color=EDUCATION, label="Education", height=0.72)
    ax.barh(y, ls, left=[a + b for a, b in zip(h, e)], color=LIVING, label="Living standards", height=0.72)

    ax.set_yticks(y, names, fontsize=7.6)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Contribution to the Multidimensional Poverty Index (%)", fontsize=9)
    ax.xaxis.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)

    for i, r in enumerate(data):
        ax.text(
            101.5, i, f"MPI {float(r['mpi']):.3f}",
            va="center", fontsize=6.9, color="#555555", fontfamily="monospace",
        )
    ax.legend(
        loc="upper center", bbox_to_anchor=(0.5, -0.075), ncol=3, frameon=False, fontsize=8.6,
    )
    titles(
        ax,
        "Which dimension drives poverty?",
        "Percentage contribution of each dimension to the MPI, summing to 100% within "
        "each state · states ordered by MPI, highest first · MICS 2021 · Nigeria excludes "
        "the nutrition indicator in every state. The north-west is driven by education and "
        "living standards; the south-east by health.",
        width=104,
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "2_dimension_breakdown.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  2_dimension_breakdown.png")


# ---------------------------------------------------------------- visual 3
def visual_conflict(rows: list[dict[str, str]]) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 6.6))
    zero = [r for r in rows if int(r["events"]) == 0]
    live = [r for r in rows if int(r["events"]) > 0]

    ax.scatter(
        [float(r["mpi"]) for r in zero], [float(r["conflict_exposure_index"]) for r in zero],
        s=70, facecolor="white", edgecolor="#9aa0a6", linewidth=1.3, zorder=3,
        label=f"no recorded events ({len(zero)} states)",
    )
    ax.scatter(
        [float(r["mpi"]) for r in live], [float(r["conflict_exposure_index"]) for r in live],
        s=70, color="#c1272d", alpha=0.85, edgecolor="white", linewidth=0.8, zorder=4,
        label=f"events recorded ({len(live)} states)",
    )
    for r in live:
        if r["state"] in {"Borno", "Benue", "Yobe", "Plateau", "Kaduna", "Nasarawa", "Taraba"}:
            ax.annotate(
                r["state"], (float(r["mpi"]), float(r["conflict_exposure_index"])),
                textcoords="offset points", xytext=(7, 5), fontsize=7.8, color=INK,
            )

    ax.set_xlabel("Multidimensional Poverty Index, 2021 (range 0-1)", fontsize=9)
    ax.set_ylabel("Conflict Exposure Index, 2021 (0-100, relative within 37 states)", fontsize=9)
    ax.grid(True, color=GRID, linewidth=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=8.6, loc="upper left")

    titles(
        ax,
        "Conflict exposure against poverty: no stable relationship",
        "Spearman rho = -0.06 across 37 states in 2021, and rho ranges +0.34 to -0.20 across "
        "the four survey rounds. Borno dominates the index because min-max scaling gives the "
        "single most violent state 100 while the remaining 36 cluster near zero.",
        width=104,
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "3_conflict_overlay.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  3_conflict_overlay.png")


# ---------------------------------------------------------------- visual 4
def visual_climate(rows: list[dict[str, str]], panel: list[dict[str, str]]) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 6.0))

    xs = [float(r["baseline_precip_mm"]) for r in rows]
    ys = [float(r["mpi"]) for r in rows]
    ax1.scatter(xs, ys, s=64, color="#2166ac", alpha=0.8, edgecolor="white", linewidth=0.8, zorder=3)
    for r in rows:
        offsets = {
            "Bauchi": (7, 4), "Borno": (7, 4), "Ogun": (7, 4), "Cross River": (-58, 4),
            "Sokoto": (-46, 4), "Jigawa": (7, 4), "Kebbi": (7, -10), "Lagos": (7, -10),
        }
        dx, dy = offsets.get(r["state"], (7, 4))
        ax1.annotate(
            r["state"], (float(r["baseline_precip_mm"]), float(r["mpi"])),
            textcoords="offset points", xytext=(dx, dy), fontsize=7.8,
        )
    ax1.set_xlabel("Baseline annual precipitation at the state capital, 1991-2020 (mm)", fontsize=9)
    ax1.set_ylabel("MPI, 2021", fontsize=9)
    ax1.set_title("The stable climate signal: dry states are poor", fontsize=10.5, fontweight="700", loc="left", pad=26)
    ax1.text(
        0, 1.012, "Spearman rho = -0.80 (p < 0.001) across 37 states",
        transform=ax1.transAxes, fontsize=8.3, color="#555555",
    )
    ax1.grid(True, color=GRID, linewidth=0.6)
    ax1.set_axisbelow(True)
    for side in ("top", "right"):
        ax1.spines[side].set_visible(False)

    rounds = sorted({int(r["survey_year"]) for r in panel})
    for pcode in sorted({r["pcode"] for r in panel}):
        state = next(r["state"] for r in panel if r["pcode"] == pcode)
        series = {int(r["survey_year"]): float(r["mpi"]) for r in panel if r["pcode"] == pcode}
        if state in {"Bauchi", "Borno", "Kano", "Lagos"}:
            ax2.plot(rounds, [series[y] for y in rounds], marker="o", linewidth=2.0,
                     markersize=4.5, label=state)
        else:
            ax2.plot(rounds, [series[y] for y in rounds], color="#c8ccd1", linewidth=0.8, alpha=0.6)
    ax2.set_xticks(rounds, [f"{y}\n{s}" for y, s in
                            zip(rounds, ["DHS", "MICS", "DHS", "MICS"])], fontsize=8)
    ax2.set_ylabel("MPI", fontsize=9)
    ax2.set_xlabel("Survey round", fontsize=9)
    ax2.set_title("Poverty structure is stable across four survey rounds", fontsize=10.5,
                  fontweight="700", loc="left", pad=26)
    ax2.text(
        0, 1.012, "Rank persistence rho = 0.87-0.92 between consecutive rounds;\n"
                   "national MPI fell 0.230 -> 0.175",
        transform=ax2.transAxes, fontsize=8.3, color="#555555", linespacing=1.35,
    )
    ax2.grid(True, color=GRID, linewidth=0.6)
    ax2.set_axisbelow(True)
    for side in ("top", "right"):
        ax2.spines[side].set_visible(False)
    ax2.legend(frameon=False, fontsize=8.4, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 0.93))

    fig.suptitle(
        "Climate and poverty over time",
        fontsize=13, fontweight="700", x=0.007, ha="left", y=1.10,
    )
    fig.text(
        0.007, 1.035,
        "The left panel uses each capital's 1991-2020 baseline, not a single year's "
        "anomaly: the per-year anomaly correlation with MPI flips sign between survey "
        "rounds (+0.81 in 2013, -0.43 in 2021), so plotting it would show weather, not climate.",
        fontsize=8.5, color="#555555", va="bottom",
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "4_climate_and_trend.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  4_climate_and_trend.png")


# ---------------------------------------------------------------- visual 5
def visual_radar(rows: list[dict[str, str]]) -> None:
    focus = "Bauchi"
    others = ["Kano", "Borno", "Lagos", "FCT"]
    dims = ["Health", "Education", "Living standards"]
    keys = ["contrib_health_pct", "contrib_education_pct", "contrib_living_standards_pct"]
    by_state = {r["state"]: r for r in rows}
    mean = [sum(float(r[k]) for r in rows) / len(rows) for k in keys]

    n = len(dims)
    angles = [i / n * 2 * math.pi for i in range(n)] + [0.0]

    def close(vals: list[float]) -> list[float]:
        return vals + vals[:1]

    fig, ax = plt.subplots(figsize=(7.6, 7.6), subplot_kw={"polar": True})
    ax.plot(angles, close(mean), color="#555555", linewidth=2.0, linestyle="--", label="37-state mean")
    ax.fill(angles, close(mean), color="#555555", alpha=0.07)
    palette = ["#b2182b", "#2166ac", "#1b7837", "#7b3294", "#e08214"]
    for colour, state in zip(palette, others + [focus]):
        vals = [float(by_state[state][k]) for k in keys]
        lw, alpha = (2.8, 0.22) if state == focus else (1.4, 0.0)
        ax.plot(angles, close(vals), color=colour, linewidth=lw, label=f"{state} (MPI {float(by_state[state]['mpi']):.3f})")
        ax.fill(angles, close(vals), color=colour, alpha=alpha)

    ax.set_xticks(angles[:-1], dims, fontsize=10.5, fontweight="600")
    ax.set_ylim(0, 80)
    ax.set_yticks([20, 40, 60, 80], ["20%", "40%", "60%", "80%"], fontsize=8, color="#777777")
    ax.grid(color=GRID, linewidth=0.7)
    ax.spines["polar"].set_color("#c8ccd1")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.06), ncol=3, frameon=False, fontsize=8.4)
    fig.suptitle(
        "Dimension profile: Bauchi against selected comparators",
        fontsize=13, fontweight="700", x=0.02, ha="left", y=1.10,
    )
    fig.text(
        0.02, 1.035,
        "Percentage contribution of each dimension to the MPI, MICS 2021. Bauchi has the "
        "highest MPI of the 37 states,\nbut its poverty is driven by education and living "
        "standards rather than health — Lagos shows the opposite profile.",
        fontsize=8.5, color="#555555", va="bottom", linespacing=1.4,
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "5_state_radar.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  5_state_radar.png")


def main() -> int:
    PREVIEW.mkdir(parents=True, exist_ok=True)
    rows = read(ATLAS)
    panel = read(PANEL)
    assert len(rows) == 37, f"expected 37 states, got {len(rows)}"
    assert len(panel) == 148, f"expected 148 panel rows, got {len(panel)}"

    print("rendering previews:")
    visual_choropleth(rows)
    visual_dimensions(rows)
    visual_conflict(rows)
    visual_climate(rows, panel)
    visual_radar(rows)
    print(f"\nwrote 5 previews to {PREVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())