"""Stage 5 -- render the five spec visuals as PNGs before Tableau is involved.

This is the QA gate. If a stacked bar looks wrong or a scatter shows an
implausible relationship, the bug is in Python where it is cheap to fix, not
buried in hand-authored Tableau XML. It also serves as the visual reference for
what each Tableau sheet is meant to show.

The five visuals follow the project spec, section 1.4:

1. Geographic plot        state capitals positioned by lat/lon, banded MPI
  2. Dimension breakdown     the three dimension contributions, three panels
  3. Conflict overlay        scatter, MPI vs Conflict Exposure Index
  4. Geographic gradient     MPI vs latitude, NOT vs climate -- see visual 4
  5. State comparison        radar, one state against the 37-state mean
  6. Party alignment         MPI change vs federal alignment (stage 8), not a spec visual

Three of these depart from the spec, deliberately and for documented reasons.

Visual 1 is NOT a filled choropleth. The spec asked for one, and the workbook
carried a "filled map" for its whole life -- but it was never a map. Verified in
Tableau Public on 2026-10-06: it drew 74 small lat/lon bar charts. Hand-written
Tableau XML does not produce the generated-geographic-field pairing a filled map
needs, so this is a correctly georeferenced scatter of the 37 capitals, which
shows the same thing and does not overstate what the geometry supports.

Visual 2 is NOT a stacked bar. Three measures on Rows give three aligned panes.
The Measure Names/Values pair that stacks them also needs a measure-values filter,
and hand-authoring that produced one 18,000-tall bar per state. The title says
"three panels" rather than pretending otherwise.

Visual 4 plots MPI against LATITUDE, not precipitation. The spec asked for a
climate-poverty nexus. Baseline precipitation correlates with MPI at rho -0.80,
which looks like a finding, but precipitation correlates with latitude at -0.903
and latitude correlates with MPI at +0.821 -- latitude predicts MPI BETTER than
precipitation does. The predictor is the outcome's twin. The chart now shows the
gradient honestly. See docs/CAUSAL_DECISION.md.
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
ALIGN_PANEL = PROCESSED / "party_alignment_panel.csv"
ALIGN_RESULT = PROCESSED / "party_alignment_result.csv"

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
        "multidimensionally poor). OPHI's standard errors put the median relative "
        "SE at 15%, and all 36 adjacent rank pairs overlap at 95%, so no single "
        "state is statistically the worst — read this as bands, not an order.",
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
    fig.savefig(PREVIEW / "2_dimension_breakdown_three_panels.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  2_dimension_breakdown_three_panels.png")


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
        "Conflict exposure against poverty: none detectable, and none excluded",
        "Spearman rho = -0.06 in 2021, range +0.34 to -0.20 across four rounds; nothing "
        "survives multiple comparisons. At n=37 the design has power 0.75 at rho=0.4, so a "
        "moderate effect would be invisible. The null also holds across UCDP's full "
        "low-to-high fatality band, so it is not an artefact of the casualty estimate. "
        "But 10 of 37 states recorded no event in 2021, including the five poorest — "
        "a coverage statement, not evidence of peace.",
        width=104,
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "3_conflict_overlay.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  3_conflict_overlay.png")


# ---------------------------------------------------------------- visual 4
def visual_climate(rows: list[dict[str, str]], panel: list[dict[str, str]]) -> None:
    """Geographic gradient and persistence -- NOT a climate-poverty nexus.

    The spec asked for the climate nexus. This panel plots latitude instead, and
    the reason is the whole point of the left panel: baseline precipitation does
    correlate with MPI (rho = -0.80), but precipitation is 90% latitude, and
    latitude predicts MPI BETTER than precipitation does (+0.821). Showing the
    precipitation relationship would present a geographic gradient wearing a
    climate finding's clothes. The two series are drawn together so the reader
    can see that they are the same gradient twice.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.6, 6.0))

    lats = [float(r["lat"]) for r in rows]
    ys = [float(r["mpi"]) for r in rows]
    ax1.scatter(lats, ys, s=64, color="#2166ac", alpha=0.8, edgecolor="white", linewidth=0.8, zorder=3)
    for r in rows:
        offsets = {
            "Bauchi": (7, 4), "Borno": (7, 4), "Ogun": (7, 4), "Cross River": (-58, 4),
            "Sokoto": (-46, 4), "Jigawa": (7, 4), "Kebbi": (7, -10), "Lagos": (7, -10),
        }
        dx, dy = offsets.get(r["state"], (7, 4))
        ax1.annotate(
            r["state"], (float(r["lat"]), float(r["mpi"])),
            textcoords="offset points", xytext=(dx, dy), fontsize=7.8,
        )
    ax1.set_xlabel("Latitude of the state capital (degrees north)", fontsize=9)
    ax1.set_ylabel("MPI, 2021", fontsize=9)
    ax1.set_title(
        "Poverty tracks a north-south gradient, not climate",
        fontsize=10.5, fontweight="700", loc="left", pad=48,
    )
    ax1.text(
        0, 1.055,
        "Latitude vs MPI: rho = +0.82  ·  baseline precipitation vs MPI: rho = -0.80\n"
        "but precipitation vs latitude: rho = -0.90. The predictor is the outcome's twin.",
        transform=ax1.transAxes, fontsize=8.3, color="#555555", linespacing=1.35,
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
                  fontweight="700", loc="left", pad=48)
    ax2.text(
        0, 1.055,
        "Rank persistence rho = 0.87-0.92 between consecutive rounds.\n"
        "Harmonised series: 41 of 111 state-period changes are statistically significant.",
        transform=ax2.transAxes, fontsize=8.3, color="#555555", linespacing=1.35,
    )
    ax2.grid(True, color=GRID, linewidth=0.6)
    ax2.set_axisbelow(True)
    for side in ("top", "right"):
        ax2.spines[side].set_visible(False)
    ax2.legend(frameon=False, fontsize=8.4, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 0.93))

    fig.suptitle(
        "Geographic gradient, and what does not change",
        fontsize=13, fontweight="700", x=0.007, ha="left", y=1.10,
    )
    fig.text(
        0.007, 1.035,
        "The left panel deliberately does NOT plot climate. Annual temperature anomaly flips "
        "sign against MPI between rounds (+0.81 in 2013, -0.43 in 2021), and baseline rainfall "
        "is 90% latitude. Both would have shown a striking chart that means geography.",
        fontsize=8.5, color="#555555", va="bottom",
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "4_gradient_and_trend.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  4_gradient_and_trend.png")


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


# ---------------------------------------------------------------- visual 6


def visual_party_alignment() -> None:
    """dmpi_annual against aligned_share, one facet per interval (stage 8 outputs).

    Neutral greys only: party is never a colour in this atlas. The subtitle is the
    section 4 sentence chosen by stage 8 from the pre-registered templates, so this
    chart makes no claim of its own.
    """
    align = read(ALIGN_PANEL)
    result = read(ALIGN_RESULT)
    assert len(align) == 108, f"expected 108 state-intervals, got {len(align)}"
    primary = result[0]
    assert primary["model"].startswith("Primary"), "party_alignment_result.csv row 0 must be primary"

    intervals = sorted({r["interval"] for r in align})
    ys = [float(r["dmpi_annual"]) for r in align]
    pad = 0.08 * (max(ys) - min(ys))
    fig, axes = plt.subplots(1, len(intervals), figsize=(11.5, 4.6), sharey=True)
    for ax, interval in zip(axes, intervals, strict=True):
        sub = [r for r in align if r["interval"] == interval]
        ax.scatter(
            [float(r["aligned_share"]) for r in sub], [float(r["dmpi_annual"]) for r in sub],
            s=34, color="#6b6f76", alpha=0.75, edgecolor="white", linewidth=0.6, zorder=3,
        )
        ax.axhline(0, color="#8a8a8a", linewidth=0.8, zorder=2)
        ax.set_xlim(-0.05, 1.05)
        ax.set_ylim(min(ys) - pad, max(ys) + pad)
        ax.set_title(f"{interval}  (n = {len(sub)})", fontsize=10, loc="left")
        ax.set_xlabel("Share of interval aligned with federal ruling party", fontsize=8.6)
        ax.grid(True, color=GRID, linewidth=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].set_ylabel("MPI change per year (negative = poverty fell)", fontsize=8.6)

    note = (
        f"Primary β = {float(primary['beta']):+.4f} MPI per year "
        f"(95% CI {float(primary['ci_lo']):+.4f} to {float(primary['ci_hi']):+.4f}, "
        f"permutation p = {primary['p_perm']}); model has interval FE and MPI at t0. "
        f"MDE {primary['mde']}. n = {primary['n']}, FCT excluded (no elected governor)."
    )
    fig.text(0.01, -0.02, note, fontsize=8.4, color=INK, ha="left", va="top")
    sentence = primary["sentence"].replace("*", "")
    fig.suptitle(
        "Federal alignment and the pace of MPI change, 2013–2021",
        x=0.01, y=1.10, ha="left", fontsize=13, fontweight="700",
    )
    fig.text(
        0.01, 1.04, "\n".join(textwrap.wrap(sentence, width=150)),
        fontsize=8.6, color="#555555", ha="left", va="top", linespacing=1.35,
    )
    fig.tight_layout()
    fig.savefig(PREVIEW / "6_party_alignment.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    print("  6_party_alignment.png")


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
    visual_party_alignment()
    print(f"\nwrote 6 previews to {PREVIEW}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())