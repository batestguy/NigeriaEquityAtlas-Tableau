"""Build a single-file, offline HTML explorer for the atlas's processed data.

Reads everything under ``data/processed/`` and writes
``analysis/data_explorer.html`` -- one self-contained page (no CDN, no network)
with a sortable master table, an interactive scatter lab, per-state small
multiples across the four survey rounds, the spatial and party diagnostics, and
a ranked list of analyses that can actually be shipped in Tableau Public.

Run:  & C:\\Users\\TOSHIBA\\ds-general\\python.exe analysis\\data_explorer.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUT = ROOT / "analysis" / "data_explorer.html"

BANDS = [
    ("1. under 5%", "#ffe5e5"),
    ("2. 5% to 10%", "#ffb8b8"),
    ("3. 10% to 20%", "#ff8a8a"),
    ("4. 20% to 30%", "#f45555"),
    ("5. 30% and above", "#d80000"),
]

# ---------------------------------------------------------------- columns ----
# (column, label, kind, note). ``kind`` drives the scatter lab's axis menus.
COLUMNS: list[tuple[str, str, str, str]] = [
    ("pcode", "P-code", "text", "ISO 3166-2:NG code; the join key everywhere."),
    ("state", "State", "text", "36 states + FCT."),
    ("capital", "Capital", "text", "GeoNames gazetteer build (stage 0)."),
    ("lat", "Latitude", "num", "Capital latitude, decimal degrees north."),
    ("lon", "Longitude", "num", "Capital longitude."),
    ("mpi", "MPI", "num", "Multidimensional Poverty Index value, 0-1. The atlas's headline metric."),
    ("mpi_se", "MPI std. error", "num", "OPHI published standard error."),
    ("mpi_ci_lo", "MPI CI low", "num", "95% lower bound of the MPI value."),
    ("mpi_ci_hi", "MPI CI high", "num", "95% upper bound of the MPI value."),
    ("mpi_rank", "MPI rank", "num", "1 = highest MPI. Not resolvable: all 36 adjacent pairs overlap at 95%."),
    ("headcount_ratio_pct", "Headcount ratio H (%)", "num", "Share of people who are multidimensionally poor."),
    ("headcount_se", "Headcount SE", "num", "Published standard error on H."),
    ("intensity_pct", "Intensity A (%)", "num", "Average share of weighted deprivations among the poor."),
    ("vulnerable_pct", "Vulnerable (%)", "num", "Share at risk: deprivation score 20-33%."),
    ("severe_pct", "Severe (%)", "num", "Share in severe poverty: deprivation score 50%+."),
    ("quadrant", "Quadrant", "text", "Incidence (H) vs intensity (A) against the 37-state median split."),
    ("contrib_health_pct", "Contribution: health (%)", "num", "Share of MPI from the health dimension. Sums to 100 with the other two."),
    ("contrib_education_pct", "Contribution: education (%)", "num", "Share of MPI from education."),
    ("contrib_living_standards_pct", "Contribution: living standards (%)", "num", "Share of MPI from living standards."),
    ("population_thousands", "Population (000s)", "num", "State population used for the per-100k conflict rates."),
    ("mpi_poor_thousands", "Poor people (000s)", "num", "Headcount x population: the mass of poverty, not the rate."),
    ("mpi_poor_rank", "Poor-people rank", "num", "1 = largest number of poor people (differs sharply from mpi_rank)."),
    ("events", "Conflict events", "num", "UCDP GED events attributed to the state, 2021."),
    ("fatalities", "Fatalities", "num", "UCDP GED best estimate, 2021."),
    ("events_per_100k", "Events / 100k", "num", "Population-normalised conflict events."),
    ("fatalities_per_100k", "Fatalities / 100k", "num", "Population-normalised fatalities (best estimate)."),
    ("conflict_exposure_index", "Conflict Exposure Index", "num", "0-100, min-max scaled WITHIN each survey year. Cross-sectionally relative only."),
    ("temp_mean_c", "Temp mean (C)", "num", "2021 annual mean at the capital."),
    ("precip_total_mm", "Precipitation (mm)", "num", "2021 annual total at the capital."),
    ("temp_anomaly_c", "Temp anomaly (C)", "num", "2021 departure from the 1991-2020 baseline."),
    ("precip_anomaly_pct", "Precip anomaly (%)", "num", "2021 departure from the 1991-2020 baseline."),
    ("baseline_temp_c", "Baseline temp (C)", "num", "1991-2020 mean at the capital."),
    ("baseline_precip_mm", "Baseline precip (mm)", "num", "1991-2020 mean at the capital. Correlates with MPI at rho -0.80 -- and with latitude at -0.90."),
    ("mpi_band", "MPI band", "text", "Five-band cut used for the map's fill (MPI value, not H)."),
    ("poverty_group", "Poverty group", "text", "Poorest 12 vs Other 25."),
    ("n_indicators", "Indicators used", "num", "9 for every state: Nutrition is excluded country-wide."),
    ("indicators_missing", "Indicator excluded", "text", "Nutrition for all 37 rows -- a country-wide exclusion, not a per-state gap."),
    ("survey", "Survey", "text", "MICS 2021."),
    ("survey_year", "Survey year", "num", "2021."),
]

PANEL_MEASURES = [
    ("mpi", "MPI value", 3),
    ("headcount_ratio_pct", "Headcount ratio H (%)", 1),
    ("intensity_pct", "Intensity A (%)", 1),
    ("conflict_exposure_index", "Conflict Exposure Index", 1),
    ("temp_anomaly_c", "Temp anomaly (C)", 2),
    ("precip_anomaly_pct", "Precip anomaly (%)", 1),
]


def load() -> dict:
    master = pd.read_csv(PROCESSED / "mpi_atlas_2021.csv", encoding="utf-8")
    panel = pd.read_csv(PROCESSED / "mpi_trends_panel.csv", encoding="utf-8")
    spatial = pd.read_csv(PROCESSED / "spatial_diagnostics.csv", encoding="utf-8")
    spatial_global = pd.read_csv(PROCESSED / "spatial_global.csv", encoding="utf-8")
    party = pd.read_csv(PROCESSED / "party_alignment_result.csv", encoding="utf-8")
    party_state = pd.read_csv(PROCESSED / "party_alignment_state.csv", encoding="utf-8")
    party_panel = pd.read_csv(PROCESSED / "party_alignment_panel.csv", encoding="utf-8")
    vintages = pd.read_csv(PROCESSED / "atlas_vintages.csv", encoding="utf-8")
    dominant = pd.read_csv(
        ROOT / "data" / "reference" / "state_dominant_party.csv", encoding="utf-8"
    )

    assert len(master) == 37, f"expected 37 rows in mpi_atlas_2021.csv, got {len(master)}"
    assert master["mpi"].notna().all(), "missing MPI values"

    def rows(df: pd.DataFrame) -> list[dict]:
        out = df.replace({float("nan"): None}).to_dict(orient="records")
        for rec in out:
            for k, v in rec.items():
                if isinstance(v, float) and v.is_integer() and k in {"survey_year", "mpi_rank"}:
                    rec[k] = int(v)
        return out

    return {
        "master": rows(master),
        "panel": rows(panel),
        "spatial": rows(spatial),
        "spatialGlobal": rows(spatial_global),
        "party": rows(party),
        "partyState": rows(party_state),
        "partyPanel": rows(party_panel),
        "vintages": rows(vintages),
        "dominant": rows(dominant),
        "columns": [
            {"key": k, "label": lab, "kind": kind, "note": note}
            for k, lab, kind, note in COLUMNS
        ],
        "bands": [{"label": l, "color": c} for l, c in BANDS],
        "panelMeasures": [{"key": k, "label": l, "dec": d} for k, l, d in PANEL_MEASURES],
    }


# ----------------------------------------------------------------- ideas ----
# (title, verdict, verdict_class, body, tableau_note)
IDEAS: list[tuple[str, str, str, str, str]] = [
    (
        "Rank with its confidence interval (the honest ranking)",
        "Supported · ship this first",
        "ok",
        "A dot plot of all 37 states on <code>mpi</code>, ordered, with a whisker from "
        "<code>mpi_ci_lo</code> to <code>mpi_ci_hi</code>. Every adjacent pair overlaps, so the "
        "whiskers form one continuous chain down the page. It makes the atlas's core caveat "
        "<em>visible</em> instead of stating it in fine print: bands, yes; a single 'highest' state, no.",
        "Circle mark on MPI, plus a Gantt bar from <code>mpi_ci_lo</code> (size = hi - lo) on a "
        "synchronised dual axis. Sort by MPI descending, hide the axes, keep the state labels. "
        "No calculated field needed.",
    ),
    (
        "Rate versus mass: where the poor people actually are",
        "Supported · strongest story",
        "ok",
        "<code>mpi_rank</code> orders states by <em>rate</em>; <code>mpi_poor_rank</code> orders them "
        "by <em>number of poor people</em> (<code>mpi_poor_thousands</code>). The two orderings are close "
        "overall (rank correlation 0.94) with one decisive exception: Kano is 11th by MPI but 1st by mass, "
        "at 7.3 million poor people. Kano, Katsina, Bauchi and Jigawa hold 26.5 million of the 75.3 million "
        "poor people across the 37 units &mdash; 35% of the total from four states. A slope chart between "
        "the two rankings, or a scatter of rate against headcount, replaces 'poorest 12 states' with "
        "'where the poor actually live'.",
        "Scatter: <code>mpi</code> on X, <code>mpi_poor_thousands</code> on Y, state on detail. Or a "
        "bump chart with <code>mpi_rank</code> and <code>mpi_poor_rank</code> on a dual axis. Both "
        "fields already exist in the extract.",
    ),
    (
        "The dimension mix, stacked to 100%",
        "Supported · decomposition",
        "ok",
        "<code>contrib_health_pct</code> + <code>contrib_education_pct</code> + "
        "<code>contrib_living_standards_pct</code> sum to 100 for every row. A 100% stacked bar per state, "
        "sorted by MPI, shows the mix shifts with poverty &mdash; but not the way you would guess: "
        "education's share rises with MPI (r = 0.76) while health's share falls (r = -0.57), and living "
        "standards' share is flat (r = 0.04). Yobe draws 47% of its MPI from education and only 6% from "
        "health; Adamawa and Taraba are the reverse, 58% and 56% living standards. Caveat: health is child "
        "mortality alone and is re-weighted to a full third, so the mix is not cross-country comparable.",
        "Measure Names / Measure Values on a stacked bar; Percentage of Total on the axis. Colour the "
        "three contributions with three assigned colours, then sort states by MPI descending.",
    ),
    (
        "Incidence x intensity quadrants",
        "Supported",
        "ok",
        "<code>headcount_ratio_pct</code> against <code>intensity_pct</code>, split at the 37-state "
        "median, with <code>quadrant</code> as the colour and a reference line at each median. It "
        "separates 'many people, shallow deprivation' from 'fewer people, deep deprivation' &mdash; two "
        "different policy problems with the same MPI. Be honest about the cells: H spans a factor of 68 "
        "across these states while A spans only 1.6, so the median cut produces a lopsided 17 / 2 / 2 / 16, "
        "and the quadrant names are about incidence and intensity, never 'high' and 'low' poverty.",
        "Scatter plus two reference lines (medians of H and A); colour on the string field "
        "<code>quadrant</code>. No table calculation required.",
    ),
    (
        "Trajectory small multiples, four rounds",
        "Descriptive only",
        "warn",
        "Small multiples of <code>mpi</code> per state across 2013/2016/2018/2021, with the "
        "<code>mpi_change_significant</code> flag marking intervals that clear the CI. Level fell and "
        "structure held (rank persistence 0.87-0.92). Do not fit a trend line, do not aggregate to a "
        "national series, and do not call the four rounds an annual rate.",
        "Small multiples: state on Columns, survey_year on Columns of the inner view, MPI on Rows, "
        "synchronised axes. Or a line chart with state on Detail and a highlight action.",
    ),
    (
        "The spatial cluster map (HH / LL / HL / LH)",
        "Supported · already built",
        "ok",
        "Moran's I = 0.798 (p = 0.0001) on queen contiguity, so poverty is spatially clustered. The "
        "quadrant map colours each state by its own value against its neighbours' mean: HH = poor "
        "among poor, LL = better-off among better-off. Stage 9 verified both the lag and the weights "
        "independently in Python.",
        "Filled map from <code>spatial_polygons.csv</code> (the same Polygon + Path technique as sheet 1), "
        "colour on <code>spatial_quadrant</code>. Ship it as a companion to the choropleth, not a "
        "replacement -- the quadrants are a different question.",
    ),
    (
        "What survives multiple-comparison correction",
        "Supported · cautionary",
        "ok",
        "16 states look locally unusual before correction; exactly 1 (Yobe) survives Bonferroni across "
        "37 tests, and 0 survive Benjamini-Yekutieli. A paired bar of <code>lisa_p</code> vs "
        "<code>lisa_p_bonferroni</code> per state, or a simple two-bar chart of the counts, tells the "
        "reader how much of a cluster map is signal and how much is 37 simultaneous tests.",
        "Bar chart of <code>lisa_p</code> and <code>lisa_p_bonferroni</code> side by side per state, "
        "plus a reference line at 0.05. Fields are in <code>spatial_diagnostics.csv</code>.",
    ),
    (
        "Conflict exposure against poverty",
        "Fragile · undetectable",
        "warn",
        "Spearman rho by round: +0.34 (2013), -0.20 (2016), +0.10 (2018), -0.06 (2021). Power at n = 37 "
        "is 0.75 only at |rho| = 0.4, nothing survives Bonferroni, and in 2021 five of the poorest 12 "
        "states record <em>zero</em> UCDP events. If it is drawn at all, it must be drawn with the "
        "zero-event states visible and labelled -- never as 'no relationship'.",
        "Scatter of <code>events_per_100k</code> vs <code>mpi</code> faceted by year, with the "
        "zero-event states jittered onto the axis and counted in a footnote. A regression-free "
        "scatter; Tableau's trend line must stay off.",
    ),
    (
        "The climate gradient (and why it is a trap)",
        "Fragile · confounded",
        "warn",
        "Baseline precipitation correlates with MPI at rho = -0.80. But precipitation vs latitude is "
        "-0.903 and latitude vs MPI is +0.821, which is <em>stronger</em>. After accounting for latitude, "
        "Moran's I falls from 0.798 to 0.244, and after conflict and climate as well it is 0.108 "
        "(p = 0.107). Any climate view has to carry latitude in the same frame, otherwise it is a "
        "map of the north disguised as weather.",
        "Scatter with <code>latitude</code> on an encoded axis or as a small-multiple dimension, and "
        "the second-order Moran's I printed in the subtitle.",
    ),
    (
        "Party alignment: beta with its interval, and the caveats beside it",
        "Fragile · caveat required",
        "warn",
        "beta = +0.0080 MPI points/year (95% CI -0.0002 to 0.0168, permutation p = 0.036): aligned states "
        "fell <em>slower</em>. The CI crosses zero, |beta| is below the minimum detectable effect (0.0115), "
        "it rests on 2013-16 alone, and the sitting-party check gives p = 0.079. If shown, the interval "
        "and the failure list must be in the same frame -- never a lone bar.",
        "A dot-and-whisker per model row from <code>party_alignment_result.csv</code> (beta, ci_lo, ci_hi) "
        "with a zero reference line, faceted by <code>kind</code>. Text zone carries the caveat line.",
    ),
    (
        "Vulnerable and severe: two populations, not one scale",
        "Supported \u00b7 a genuine surprise in the data",
        "ok",
        "<code>severe_pct</code> tracks the MPI almost perfectly (r = 0.99) &mdash; it is the same north-south "
        "story in a harsher cut. <code>vulnerable_pct</code> does not: r = -0.02 with MPI and -0.09 with "
        "severe poverty. The four highest vulnerable shares belong to Benue (35.0%), Cross River (34.7%), "
        "Ondo (32.4%) and Adamawa (31.2%), and none of those is in the poorest band. So 'at risk of falling "
        "in' and 'already in deep deprivation' are effectively different maps. That is worth showing "
        "precisely because the single MPI number hides it.",
        "Scatter of <code>vulnerable_pct</code> (X) against <code>severe_pct</code> (Y), MPI on size, state "
        "on detail. Two reference lines at the medians give the four corners. Fields already present.",
    ),
    (
        "Legend and labels: the differences that decide comprehension",
        "Polish only",
        "muted",
        "The map's five bands print as percentages of the index (under 5% ... 30% and above) and the "
        "hover prints MPI 44.10% next to 'Of the population, 75.36% are poor'. Those are two different "
        "numbers and swapping them is the easiest error to make. The colour card's title is the field "
        "caption, so <code>mpi_band</code> reads 'MPI band (Multidimensional Poverty Index)'.",
        "Colour card title = field caption (rename the field, do not add a text box). Keep the tooltip's "
        "MPI line and headcount line in fixed order.",
    ),
]


def ideas_html() -> str:
    out = []
    for i, (title, verdict, cls, body, note) in enumerate(IDEAS, 1):
        out.append(
            f"""<article class="idea {cls}">
  <div class="idea-head"><span class="num">{i:02d}</span>
    <h3>{title}</h3><span class="chip {cls}">{verdict}</span></div>
  <p>{body}</p>
  <p class="mech"><strong>In Tableau:</strong> {note}</p>
</article>"""
        )
    return "\n".join(out)


# ------------------------------------------------------------------ page ----
def build() -> Path:
    data = load()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = TEMPLATE.replace("__DATA__", payload).replace("__IDEAS__", ideas_html())
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    return OUT


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nigeria MPI Equity Atlas - Data Explorer</title>
<style>
:root{
  --bg:#fbfaf8; --panel:#fff; --ink:#1b1b1b; --muted:#6b6b6b; --line:#e3e0da;
  --red:#d80000; --red-soft:#f45555; --accent:#0b4f6c; --ok:#1c7c54; --warn:#a8621b;
  --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 "Segoe UI",system-ui,-apple-system,sans-serif}
header{padding:28px 32px 0;max-width:1400px;margin:0 auto}
h1{margin:0;font-size:26px;letter-spacing:-.02em}
h1 span{color:var(--red)}
.sub{margin:6px 0 0;color:var(--muted);font-size:13.5px;max-width:78ch}
.badges{margin:14px 0 0;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:#fff;border:1px solid var(--line);border-radius:999px;
  padding:3px 11px;font-size:12px;color:var(--muted)}
.badge b{color:var(--ink);font-weight:600}
nav{display:flex;gap:2px;flex-wrap:wrap;margin:20px 0 0;border-bottom:1px solid var(--line)}
nav button{appearance:none;border:0;background:none;font:inherit;font-size:13.5px;
  padding:9px 14px;cursor:pointer;color:var(--muted);border-bottom:2px solid transparent;
  margin-bottom:-1px}
nav button:hover{color:var(--ink)}
nav button[aria-selected="true"]{color:var(--red);border-bottom-color:var(--red);font-weight:600}
main{max-width:1400px;margin:0 auto;padding:22px 32px 80px}
section[hidden]{display:none}
h2{font-size:17px;margin:0 0 4px;letter-spacing:-.01em}
.lede{color:var(--muted);font-size:13.5px;margin:0 0 18px;max-width:88ch}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:16px 18px;margin:0 0 18px}
.card h3{font-size:13px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted);margin:0 0 10px}
.thead{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end;margin-bottom:12px}
label.f{display:flex;flex-direction:column;gap:4px;font-size:11.5px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em}
select,input[type=search]{font:inherit;font-size:13.5px;padding:6px 9px;border:1px solid var(--line);
  border-radius:7px;background:#fff;color:var(--ink);min-width:150px}
input[type=search]{min-width:220px}
.tablewrap{overflow:auto;max-height:70vh;border:1px solid var(--line);border-radius:9px;background:#fff}
table{border-collapse:collapse;width:100%;font-size:12.5px;white-space:nowrap}
th,td{padding:6px 10px;text-align:right;border-bottom:1px solid #f0eeea}
th{position:sticky;top:0;background:#f6f4f1;z-index:2;font-weight:600;font-size:11.5px;
  text-transform:uppercase;letter-spacing:.04em;color:#444;cursor:pointer;user-select:none}
th:hover{background:#efece7}
th.sorted{color:var(--red)}
td:first-child,th:first-child{text-align:left;position:sticky;left:0;background:#fff;z-index:1}
th:first-child{background:#f6f4f1;z-index:3}
tbody tr:hover td{background:#fff8f6}
tbody tr:hover td:first-child{background:#fff8f6}
td.num{font-family:var(--mono);font-size:12px}
.bar{display:inline-block;height:8px;border-radius:2px;background:var(--red-soft);vertical-align:middle}
.pill{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;background:#f1efec;color:#555}
.p1{background:#fde8e8;color:#8c1111}
.note{font-size:12.5px;color:var(--muted);margin:10px 0 0}
.note code,.card code,td code{font-family:var(--mono);font-size:11.5px;background:#f4f2ef;
  padding:1px 5px;border-radius:4px;color:#333}
.grid2{display:grid;grid-template-columns:minmax(0,1.55fr) minmax(280px,1fr);gap:18px;align-items:start}
@media(max-width:1000px){.grid2{grid-template-columns:1fr}}
#scatter{width:100%;height:auto;display:block;background:#fff;border-radius:8px}
.axis line{stroke:#e8e5e0}.axis text{font-size:10.5px;fill:#8a8a8a}
.axis path{stroke:#d8d5d0}
.dot{cursor:pointer;transition:opacity .12s}
.dot:hover{stroke:#111;stroke-width:1.4}
.lbl{font-size:9.5px;fill:#3a3a3a;pointer-events:none}
.stats div{display:flex;justify-content:space-between;gap:10px;padding:5px 0;
  border-bottom:1px solid #f2f0ec;font-size:13px}
.stats div:last-child{border-bottom:0}
.stats span:first-child{color:var(--muted)}
.stats span:last-child{font-family:var(--mono);font-size:12.5px}
.warnbox{margin-top:12px;padding:10px 12px;border-left:3px solid var(--warn);
  background:#fdf6ee;font-size:12.5px;color:#5c3d13;border-radius:0 6px 6px 0}
#tip{position:fixed;pointer-events:none;background:#161616;color:#fff;font-size:12px;
  padding:6px 9px;border-radius:6px;opacity:0;transition:opacity .1s;z-index:99;
  white-space:nowrap;line-height:1.45}
.spark-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.spark{background:#fff;border:1px solid var(--line);border-radius:8px;padding:8px 9px 6px}
.spark h4{margin:0;font-size:11.5px;font-weight:600;display:flex;justify-content:space-between;gap:6px}
.spark h4 em{font-style:normal;color:var(--muted);font-family:var(--mono);font-size:10.5px}
.spark svg{display:block;width:100%;height:44px;margin-top:4px;overflow:visible}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:var(--muted);margin:0 0 12px}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:5px;
  vertical-align:-1px}
.idea{border-left:3px solid var(--line);padding-left:16px;margin:0 0 22px}
.idea.ok{border-left-color:var(--ok)}
.idea.warn{border-left-color:var(--warn)}
.idea.muted{border-left-color:#c9c5bf}
.idea-head{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.idea-head h3{font-size:15px;margin:0;text-transform:none;letter-spacing:0;color:var(--ink);font-weight:650}
.num{font-family:var(--mono);font-size:11px;color:#b9b4ac}
.chip{font-size:10.5px;text-transform:uppercase;letter-spacing:.06em;padding:2px 8px;
  border-radius:999px;font-weight:600}
.chip.ok{background:#e7f4ed;color:#15603f}
.chip.warn{background:#fdf1e3;color:#8a4f10}
.chip.muted{background:#f1efec;color:#666}
.idea p{font-size:13.5px;margin:7px 0 0;max-width:95ch;color:#2c2c2c}
.idea .mech{font-size:12.5px;color:#4a4a4a;background:#f7f5f2;padding:8px 11px;border-radius:6px}
details{margin-top:14px}
summary{cursor:pointer;font-size:13px;color:var(--accent);font-weight:600}
dt{font-family:var(--mono);font-size:12px;color:#111;margin-top:9px}
dd{margin:1px 0 0 0;font-size:12.5px;color:var(--muted)}
footer{max-width:1400px;margin:0 auto;padding:0 32px 40px;color:#8f8a83;font-size:12px}
</style>
</head>
<body>
<header>
  <h1>Nigeria MPI Equity Atlas <span>&middot;</span> Data Explorer</h1>
  <p class="sub">Everything the pipeline has produced, in one page, so you can look before you hypothesise.
     One row per state, four harmonised survey rounds, with the conflict, climate, spatial and party layers
     joined on. Read the constraints box in the scatter lab before trusting anything you find here.</p>
  <div class="badges" id="badges"></div>
  <nav role="tablist" id="tabs">
    <button role="tab" aria-selected="true" data-tab="master">Master table</button>
    <button role="tab" aria-selected="false" data-tab="lab">Scatter lab</button>
    <button role="tab" aria-selected="false" data-tab="panel">Four rounds</button>
    <button role="tab" aria-selected="false" data-tab="spatial">Spatial</button>
    <button role="tab" aria-selected="false" data-tab="party">Party</button>
    <button role="tab" aria-selected="false" data-tab="ideas">Tableau ideas</button>
  </nav>
</header>
<main>
  <section id="tab-master">
    <h2>The master table</h2>
    <p class="lede">37 rows, one per state plus the FCT. Click any column header to sort.
       The bar in the MPI column is drawn from the same five bands the workbook's map uses.</p>
    <div class="thead">
      <label class="f">Filter states<input type="search" id="masterFilter" placeholder="e.g. Kano, 20-30, NG-KD"></label>
      <label class="f">Rows
        <select id="masterRows">
          <option value="key">Key columns</option>
          <option value="all">All 39 columns</option>
        </select>
      </label>
    </div>
    <div class="tablewrap"><table id="masterTable"><thead></thead><tbody></tbody></table></div>
    <details>
      <summary>Column dictionary (39 fields)</summary>
      <dl id="dict"></dl>
    </details>
  </section>

  <section id="tab-lab" hidden>
    <h2>Scatter lab</h2>
    <p class="lede">Pick any two numeric fields. The readout gives Pearson r and Spearman rho on all 37 rows,
       plus the ordinary least squares slope. Correlations here are <em>associations</em> at n = 37 &mdash; the
       design's detection floor is roughly |rho| = 0.4, so most values between -0.2 and +0.2 are indistinguishable
       from noise.</p>
    <div class="grid2">
      <div class="card">
        <div class="thead">
          <label class="f">X axis<select id="xSel"></select></label>
          <label class="f">Y axis<select id="ySel"></select></label>
          <label class="f">Colour by<select id="cSel">
            <option value="poverty_group">Poverty group</option>
            <option value="mpi_band">MPI band</option>
            <option value="quadrant">Incidence/intensity quadrant</option>
            <option value="none">None</option>
          </select></label>
          <label class="f" style="flex-direction:row;align-items:center;gap:7px;text-transform:none;
                 letter-spacing:0;font-size:13px;color:var(--ink);padding-bottom:7px">
            <input type="checkbox" id="labLbl"> labels
          </label>
          <label class="f" style="flex-direction:row;align-items:center;gap:7px;text-transform:none;
                 letter-spacing:0;font-size:13px;color:var(--ink);padding-bottom:7px">
            <input type="checkbox" id="labMed"> medians
          </label>
        </div>
        <svg id="scatter" viewBox="0 0 760 560" role="img" aria-label="Scatter plot"></svg>
        <div class="legend" id="labLegend"></div>
      </div>
      <div>
        <div class="card">
          <h3>Readout</h3>
          <div class="stats" id="labStats"></div>
          <div class="warnbox" id="labWarn"></div>
        </div>
        <div class="card">
          <h3>Constraints that bound any reading</h3>
          <p class="note" style="margin-top:0">
            <b>n = 37.</b> Power 0.75 only at |rho| = 0.40; nothing survives Bonferroni across the four rounds.<br>
            <b>Orderings are unresolved.</b> All 36 adjacent state pairs overlap at 95% on both the MPI value and H.<br>
            <b>Latitude is the confounder.</b> Precip vs MPI rho = -0.80; precip vs latitude -0.90; latitude vs MPI +0.82.<br>
            <b>Conflict undercounts the poorest.</b> Five of the poorest 12 states record zero UCDP events in 2021.<br>
            <b>No causal claim.</b> This is a decomposition, not an effect. See <code>docs/CAUSAL_DECISION.md</code>.
          </p>
        </div>
      </div>
    </div>
  </section>

  <section id="tab-panel" hidden>
    <h2>Four harmonised rounds</h2>
    <p class="lede">One panel per state, 2013 &rarr; 2016 &rarr; 2018 &rarr; 2021, all on a shared scale so the
       cells are comparable. Level fell; structure held (rank persistence 0.87&ndash;0.92).</p>
    <div class="thead">
      <label class="f">Measure<select id="panelSel"></select></label>
      <label class="f">Order cells by<select id="panelSort">
        <option value="name">State name</option>
        <option value="last">Final value</option>
        <option value="change">Change over the panel</option>
      </select></label>
    </div>
    <div class="spark-grid" id="sparks"></div>
  </section>

  <section id="tab-spatial" hidden>
    <h2>Spatial diagnostics</h2>
    <p class="lede">Pre-registered in <code>docs/spatial_preregistration.md</code>, computed in R (sf/spdep/spatialreg),
       then verified independently in Python. Moran's I on the MPI value with queen contiguity.</p>
    <div class="card">
      <h3>Global and sensitivity statistics</h3>
      <div class="tablewrap" style="max-height:none"><table id="spatialGlobalTable"><thead></thead><tbody></tbody></table></div>
    </div>
    <div class="card">
      <h3>Per-state: local lag and quadrant</h3>
      <div class="tablewrap"><table id="spatialTable"><thead></thead><tbody></tbody></table></div>
      <p class="note"><b>Read the <code>lisa_p_bonferroni</code> column, not <code>lisa_p</code>.</b>
       16 states look local before correction; 1 survives it.</p>
    </div>
  </section>

  <section id="tab-party" hidden>
    <h2>Federal party alignment</h2>
    <p class="lede">Pre-registered before any code was written. The rule fired at p &lt; 0.05, and the result then
       failed four of its own robustness checks &mdash; so it is reported as a fragile association, with the
       failures in the same frame, or not at all.</p>
    <div class="card">
      <h3>Models: beta, 95% CI, permutation p</h3>
      <div class="tablewrap" style="max-height:none"><table id="partyTable"><thead></thead><tbody></tbody></table></div>
    </div>
    <div class="card">
      <h3>Years aligned with the federal ruling party, 1999&ndash;2021</h3>
      <div class="tablewrap"><table id="partyStateTable"><thead></thead><tbody></tbody></table></div>
      <p class="note">FCT has no elected governor and is therefore absent from every party model.</p>
    </div>
  </section>

  <section id="tab-ideas" hidden>
    <h2>What can actually be presented in Tableau</h2>
    <p class="lede">Twelve views, ranked by how much the data can carry. Green means the claim survives the
       project's own constraints; amber means it can be drawn only with the caveat in the same frame;
       grey is polish. Every field named here is already in <code>tableau/*.hyper</code>.</p>
    __IDEAS__
  </section>
</main>
<footer>Generated by <code>analysis/data_explorer.py</code> from <code>data/processed/*.csv</code>.
  Offline and self-contained &mdash; no network calls, no external assets.</footer>
<div id="tip"></div>
<script>
const DATA = __DATA__;
</script>
<script>
(function(){
"use strict";
const $=(s,r=document)=>r.querySelector(s), $$=(s,r=document)=>[...r.querySelectorAll(s)];
const BAND_COLOR={}; DATA.bands.forEach(b=>BAND_COLOR[b.label]=b.color);
const GROUP_COLOR={"Poorest 12":"#d80000","Other 25":"#7a8b99"};
const QUAD_COLOR={"HH":"#a51818","LL":"#2f7d9e","HL":"#e08a2e","LH":"#7f9f3a"};
const fmt=(v,d)=>{ if(v===null||v===undefined||v==="")return "\u2014";
  const n=Number(v); if(Number.isNaN(n))return String(v);
  return n.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d}); };
const num=v=>{const n=Number(v);return Number.isFinite(n)?n:null;};
/* two-dp for measured values, whole numbers for counts, four dp for small indices */
const fmtNum=v=>Number.isInteger(v)?fmt(v,0):(Math.abs(v)<1?fmt(v,4):fmt(v,2));

/* ---- badges ---- */
$("#badges").innerHTML=[
  ["rows",DATA.master.length],["states + FCT",DATA.master.length],
  ["survey rounds",new Set(DATA.panel.map(r=>r.survey_year)).size],
  ["fields",DATA.columns.length],
  ["spatial unit","LGA-free: state only"],
  ["vintage","MPI 2021"]
].map(([k,v])=>`<span class="badge">${k} <b>${v}</b></span>`).join("");

/* ---- tabs ---- */
$$("#tabs button").forEach(b=>b.addEventListener("click",()=>{
  $$("#tabs button").forEach(o=>o.setAttribute("aria-selected",String(o===b)));
  $$("main section").forEach(s=>{s.hidden = s.id!=="tab-"+b.dataset.tab;});
  if(b.dataset.tab==="lab") drawScatter();
  if(b.dataset.tab==="panel") drawSparks();
}));

/* ================= master table ================= */
const KEY=["state","mpi","mpi_band","mpi_rank","headcount_ratio_pct","intensity_pct",
  "contrib_health_pct","contrib_education_pct","contrib_living_standards_pct",
  "mpi_poor_thousands","events_per_100k","conflict_exposure_index","baseline_precip_mm","poverty_group"];
let mCols=KEY.slice(), mSort={key:"mpi",dir:-1};
const mLabel=k=>(DATA.columns.find(c=>c.key===k)||{label:k}).label;

function bandIndex(label){ return DATA.bands.findIndex(b=>b.label===label); }

function renderMaster(){
  const q=$("#masterFilter").value.trim().toLowerCase();
  let rows=DATA.master.filter(r=>!q || Object.values(r).some(v=>String(v).toLowerCase().includes(q)));
  rows.sort((a,b)=>{
    const x=a[mSort.key], y=b[mSort.key];
    if(x===null||x===undefined) return 1; if(y===null||y===undefined) return -1;
    if(typeof x==="number"&&typeof y==="number") return (x-y)*mSort.dir;
    return String(x).localeCompare(String(y))*mSort.dir;
  });
  const head=`<tr>${mCols.map(k=>
    `<th data-k="${k}" class="${mSort.key===k?"sorted":""}">${mLabel(k)}${
      mSort.key===k?(mSort.dir<0?" \u2193":" \u2191"):""}</th>`).join("")}</tr>`;
  const body=rows.map(r=>`<tr>${mCols.map(k=>{
    let v=r[k], cell;
    if(k==="mpi"){
      const bi=bandIndex(r.mpi_band), w=Math.max(3,Math.round((num(v)/0.45)*42));
      cell=`<span class="num">${fmt(v,3)}</span> <span class="bar" style="width:${w}px;
        background:${DATA.bands[Math.max(0,bi)]?DATA.bands[Math.max(0,bi)].color:"#ccc"}"></span>`;
      return `<td class="num">${cell}</td>`;
    }
    if(k==="state") return `<td><b>${v}</b></td>`;
    if(k==="mpi_band") return `<td><span class="pill" style="background:${
      BAND_COLOR[v]};color:${bandIndex(v)>=3?"#fff":"#7a1111"}">${v}</span></td>`;
    if(k==="poverty_group") return `<td>${v}</td>`;
    if(k==="mpi_rank"||k==="mpi_poor_thousands") return `<td class="num">${fmt(v,k==="mpi_rank"?0:1)}</td>`;
    if(typeof v==="number") return `<td class="num">${fmtNum(v)}</td>`;
    return `<td>${v??"\u2014"}</td>`;
  }).join("")}</tr>`).join("");
  $("#masterTable thead").innerHTML=head;
  $("#masterTable tbody").innerHTML=body;
  $$("#masterTable th").forEach(th=>th.addEventListener("click",()=>{
    const k=th.dataset.k;
    mSort = mSort.key===k ? {key:k,dir:-mSort.dir} : {key:k,dir:-1};
    renderMaster();
  }));
}
$("#masterRows").addEventListener("change",e=>{
  mCols = e.target.value==="all" ? DATA.columns.map(c=>c.key) : KEY.slice();
  renderMaster();
});
$("#masterFilter").addEventListener("input",renderMaster);
$("#dict").innerHTML=DATA.columns.map(c=>
  `<dt>${c.key} <span style="color:#b9b4ac">${c.label}</span></dt><dd>${c.note}</dd>`).join("");

/* ================= scatter lab ================= */
const NUM=DATA.columns.filter(c=>c.kind==="num"&&c.key!=="survey_year");
NUM.forEach(c=>{
  const o=`<option value="${c.key}">${c.label}</option>`;
  $("#xSel").insertAdjacentHTML("beforeend",o);
  $("#ySel").insertAdjacentHTML("beforeend",o);
});
$("#xSel").value="baseline_precip_mm"; $("#ySel").value="mpi";

function ranks(arr){
  const idx=arr.map((v,i)=>[v,i]).sort((a,b)=>a[0]-b[0]);
  const r=new Array(arr.length);
  let i=0;
  while(i<idx.length){
    let j=i; while(j+1<idx.length && idx[j+1][0]===idx[i][0]) j++;
    const avg=(i+j)/2+1;
    for(let k=i;k<=j;k++) r[idx[k][1]]=avg;
    i=j+1;
  }
  return r;
}
function pearson(a,b){
  const n=a.length, ma=a.reduce((s,v)=>s+v,0)/n, mb=b.reduce((s,v)=>s+v,0)/n;
  let sxy=0,sxx=0,syy=0;
  for(let i=0;i<n;i++){const dx=a[i]-ma,dy=b[i]-mb;sxy+=dx*dy;sxx+=dx*dx;syy+=dy*dy;}
  return sxy/Math.sqrt(sxx*syy);
}
function spearman(a,b){ return pearson(ranks(a),ranks(b)); }
function slope(a,b){
  const n=a.length, ma=a.reduce((s,v)=>s+v,0)/n, mb=b.reduce((s,v)=>s+v,0)/n;
  let sxy=0,sxx=0; for(let i=0;i<n;i++){sxy+=(a[i]-ma)*(b[i]-mb);sxx+=(a[i]-ma)**2;}
  return {m:sxy/sxx, c:mb-(sxy/sxx)*ma};
}
const median=a=>{const s=[...a].sort((x,y)=>x-y),n=s.length;
  return n%2?s[(n-1)/2]:(s[n/2-1]+s[n/2])/2;};

const axisFmt=(v,step)=>{
  const d = step>=1 ? 0 : Math.min(4, Math.max(1, Math.ceil(-Math.log10(step))));
  return v.toLocaleString("en-US",{minimumFractionDigits:d,maximumFractionDigits:d,
    useGrouping: Math.abs(v) >= 10000});
};
function niceScale(lo,hi,steps){
  if(!(hi>lo)){const c=(hi+lo)/2||0; lo=c-1; hi=c+1;}
  const raw=(hi-lo)/steps;
  const mag=Math.pow(10,Math.floor(Math.log10(raw)));
  const norm=raw/mag;
  const mult = norm<=1?1:norm<=2?2:norm<=2.5?2.5:norm<=5?5:10;
  const step=mult*mag;
  const lo2=Math.floor(lo/step)*step, hi2=Math.ceil(hi/step)*step;
  const ticks=[];
  for(let v=lo2; v<=hi2+step*1e-9; v+=step) ticks.push(Math.round(v/step)*step);
  return {ticks, lo:lo2, hi:hi2, step};
}
function domain(min,max){
  const span=max-min, pad=span*0.06;
  let lo=min-pad, hi=max+pad;
  if(min>=0 && lo < span*0.25) lo=0;      // snap to zero when it is close
  if(max<=0 && hi > -span*0.25) hi=0;
  return niceScale(lo,hi,5);
}

function drawScatter(){
  const xk=$("#xSel").value, yk=$("#ySel").value, ck=$("#cSel").value;
  const pts=DATA.master.map(r=>({s:r.state,x:num(r[xk]),y:num(r[yk]),
    g:ck==="none"?null:r[ck]})).filter(p=>p.x!==null&&p.y!==null);
  const W=760,H=560,m={t:18,r:18,b:52,l:74};
  const xs=pts.map(p=>p.x), ys=pts.map(p=>p.y);
  const XD=domain(Math.min(...xs),Math.max(...xs));
  const YD=domain(Math.min(...ys),Math.max(...ys));
  const X0=XD.lo, X1=XD.hi, Y0=YD.lo, Y1=YD.hi;
  const sx=v=>m.l+((v-X0)/(X1-X0))*(W-m.l-m.r);
  const sy=v=>H-m.b-((v-Y0)/(Y1-Y0))*(H-m.t-m.b);

  let svg=`<g class="axis">`;
  XD.ticks.forEach(vx=>{
    svg+=`<line x1="${sx(vx)}" y1="${sy(Y0)}" x2="${sx(vx)}" y2="${sy(Y1)}"/>`;
    svg+=`<text x="${sx(vx)}" y="${H-m.b+18}" text-anchor="middle">${axisFmt(vx,XD.step)}</text>`;
  });
  YD.ticks.forEach(vy=>{
    svg+=`<line x1="${m.l}" y1="${sy(vy)}" x2="${W-m.r}" y2="${sy(vy)}"/>`;
    svg+=`<text x="${m.l-9}" y="${sy(vy)+3.5}" text-anchor="end">${axisFmt(vy,YD.step)}</text>`;
  });
  svg+=`<line x1="${m.l}" y1="${sy(Y0)}" x2="${W-m.r}" y2="${sy(Y0)}" stroke="#c9c5c0"/>`;
  svg+=`<line x1="${m.l}" y1="${sy(Y0)}" x2="${m.l}" y2="${sy(Y1)}" stroke="#c9c5c0"/>`;
  svg+=`<text x="${(W+m.l)/2}" y="${H-14}" text-anchor="middle" font-size="12" fill="#555">
    ${mLabel(xk)}</text>`;
  svg+=`<text transform="translate(18,${(H-m.b+m.t)/2}) rotate(-90)" text-anchor="middle"
    font-size="12" fill="#555">${mLabel(yk)}</text></g>`;

  svg+=`<defs><clipPath id="plotClip"><rect x="${m.l}" y="${m.t}"
    width="${W-m.l-m.r}" height="${H-m.t-m.b}"/></clipPath></defs><g clip-path="url(#plotClip)">`;
  if($("#labMed").checked){
    const mx=median(xs), my=median(ys);
    svg+=`<line x1="${sx(mx)}" y1="${m.t}" x2="${sx(mx)}" y2="${H-m.b}"
      stroke="#c8c4be" stroke-dasharray="4 4"/>`;
    svg+=`<line x1="${m.l}" y1="${sy(my)}" x2="${W-m.r}" y2="${sy(my)}"
      stroke="#c8c4be" stroke-dasharray="4 4"/>`;
  }

  const a=pts.map(p=>p.x), b=pts.map(p=>p.y);
  const f=slope(a,b);
  svg+=`<line x1="${sx(X0)}" y1="${sy(f.m*X0+f.c)}" x2="${sx(X1)}" y2="${sy(f.m*X1+f.c)}"
    stroke="#b3261e" stroke-width="1.6" stroke-dasharray="6 4" opacity=".8"/></g>`;

  const col=p=>!p.g?"#7a8b99":(GROUP_COLOR[p.g]||QUAD_COLOR[p.g]||BAND_COLOR[p.g]||"#7a8b99");
  pts.sort((p,q)=>(p.g===q.g?0:p.g>q.g?1:-1));
  svg+=pts.map(p=>`<circle class="dot" cx="${sx(p.x).toFixed(1)}" cy="${sy(p.y).toFixed(1)}"
    r="5.4" fill="${col(p)}" fill-opacity=".82" data-s="${p.s}" data-x="${p.x}"
    data-y="${p.y}" data-xn="${mLabel(xk)}" data-yn="${mLabel(yk)}"/>`).join("");
  if($("#labLbl").checked){
    svg+=pts.map(p=>`<text class="lbl" x="${sx(p.x)+7}" y="${sy(p.y)+3.5}">${p.s}</text>`).join("");
  }
  $("#scatter").innerHTML=svg;

  const r=pearson(a,b), rho=spearman(a,b);
  const t=r*Math.sqrt((a.length-2)/Math.max(1e-12,1-r*r));
  $("#labStats").innerHTML=[
    ["n",a.length],
    ["Pearson r",fmt(r,3)],
    ["Spearman rho",fmt(rho,3)],
    ["OLS slope",fmt(f.m,Math.abs(f.m)<0.01?5:3)],
    ["R squared",fmt(r*r,3)],
    ["approx t",fmt(t,2)],
    ["detection floor","|rho| ~ 0.40"]
  ].map(([k,v])=>`<div><span>${k}</span><span>${v}</span></div>`).join("");
  const strong=Math.abs(rho)>=0.4;
  $("#labWarn").innerHTML= strong
    ? `<b>|rho| is at or above the detection floor.</b> The association is visible at this n &mdash; it is still
       not a causal claim, and if it involves conflict or climate, check the undercount and the latitude
       confound before writing a sentence.`
    : `<b>|rho| is below the detection floor (0.40).</b> Treat this as <em>not detectable at n = 37</em>,
       not as evidence of no relationship &mdash; and if either axis is conflict, remember the variable
       undercounts where poverty is highest.`;

  const lg=$("#labLegend");
  if(ck==="none"){ lg.innerHTML=""; return; }
  const keys=[...new Set(pts.map(p=>p.g))];
  lg.innerHTML=keys.map(k=>`<span><i style="background:${GROUP_COLOR[k]||QUAD_COLOR[k]||BAND_COLOR[k]||"#7a8b99"}"></i>${k}</span>`).join("");
}
["xSel","ySel","cSel","labLbl","labMed"].forEach(id=>
  $("#"+id).addEventListener("change",drawScatter));

const tip=$("#tip");
document.addEventListener("mousemove",e=>{
  const d=e.target.closest?e.target.closest(".dot"):null;
  if(!d){tip.style.opacity=0;return;}
  tip.innerHTML=`<b>${d.dataset.s}</b><br>${d.dataset.xn} ${fmt(d.dataset.x,3)}
    &middot; ${d.dataset.yn} ${fmt(d.dataset.y,3)}`;
  tip.style.left=(e.clientX+14)+"px"; tip.style.top=(e.clientY-10)+"px";
  tip.style.opacity=1;
});

/* ================= four rounds ================= */
DATA.panelMeasures.forEach(m=>$("#panelSel").insertAdjacentHTML("beforeend",
  `<option value="${m.key}">${m.label}</option>`));
$("#panelSel").value="mpi";
let panelSort="name";

function drawSparks(){
  const mk=$("#panelSel").value;
  const meta=DATA.panelMeasures.find(m=>m.key===mk);
  const byState={};
  DATA.panel.forEach(r=>{ (byState[r.state]=byState[r.state]||[]).push(r); });
  let states=Object.keys(byState);
  const vals=DATA.panel.map(r=>num(r[mk])).filter(v=>v!==null);
  const lo=Math.min(...vals), hi=Math.max(...vals);
  const pad=(hi-lo)*0.12||1;
  const y0=lo-pad, y1=hi+pad;
  const years=[...new Set(DATA.panel.map(r=>r.survey_year))].sort((a,b)=>a-b);
  const W=150,H=44;
  const sx=i=>8+i*((W-24)/(years.length-1));
  const sy=v=>H-6-((v-y0)/(y1-y0))*(H-14);

  if(panelSort==="last") states.sort((a,b)=>num(last(b,mk))-num(last(a,mk)));
  else if(panelSort==="change") states.sort((a,b)=>chg(b,mk)-chg(a,mk));
  function last(s,k){const rows=byState[s].slice().sort((p,q)=>p.survey_year-q.survey_year);
    return rows[rows.length-1][k];}
  function chg(s,k){const rows=byState[s].slice().sort((p,q)=>p.survey_year-q.survey_year);
    return num(rows[rows.length-1][k])-num(rows[0][k]);}

  const flat=Math.abs(y1-y0)<1e-9;
  $("#sparks").innerHTML=states.map(s=>{
    const rows=byState[s].slice().sort((p,q)=>p.survey_year-q.survey_year);
    const pts=rows.map((r,i)=>({x:sx(i),y:flat?H/2:sy(num(r[mk])),v:num(r[mk]),yr:r.survey_year}));
    const d=chg(s,mk);
    const stroke = d>0 ? "#c0392b" : d<0 ? "#1c7c54" : "#999";
    const path=pts.map((p,i)=>`${i?"L":"M"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const lastV=fmt(pts[pts.length-1].v,meta.dec);
    const delta=(d>=0?"+":"")+fmt(d,meta.dec);
    return `<div class="spark"><h4>${s}<em>${lastV}</em></h4>
      <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${s} ${meta.label}">
        <path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.7"
          stroke-linejoin="round" stroke-linecap="round"/>
        ${pts.map(p=>`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="2.2" fill="${stroke}">
          <title>${s} ${p.yr}: ${fmt(p.v,meta.dec)}</title></circle>`).join("")}
      </svg>
      <div style="font-size:10px;color:#8a8a8a;display:flex;justify-content:space-between">
        <span>${years[0]}</span><span style="font-family:var(--mono)">${delta}</span><span>${years[years.length-1]}</span>
      </div></div>`;
  }).join("");
}
$("#panelSel").addEventListener("change",drawSparks);
$("#panelSort").addEventListener("change",e=>{panelSort=e.target.value;drawSparks();});

/* ================= generic sortable table ================= */
function sortTable(tbl, cols, rows){
  let sk=cols[0].key, sd=1;
  function paint(){
    tbl.querySelector("thead").innerHTML=`<tr>${cols.map(c=>
      `<th data-k="${c.key}" class="${sk===c.key?"sorted":""}">${c.label}${
        sk===c.key?(sd<0?" \u2193":" \u2191"):""}</th>`).join("")}</tr>`;
    const sorted=[...rows].sort((a,b)=>{
      const x=a[sk],y=b[sk];
      if(x===null||x===undefined) return 1; if(y===null||y===undefined) return -1;
      if(typeof x==="number"&&typeof y==="number") return (x-y)*sd;
      return String(x).localeCompare(String(y))*sd;
    });
    tbl.querySelector("tbody").innerHTML=sorted.map(r=>`<tr>${cols.map(c=>{
      const v=r[c.key];
      if(typeof v==="number") return `<td class="num">${fmtNum(v)}</td>`;
      return `<td>${v??"\u2014"}</td>`;
    }).join("")}</tr>`).join("");
    $$("th",tbl).forEach(th=>th.addEventListener("click",()=>{
      const k=th.dataset.k;
      if(sk===k) sd=-sd; else {sk=k;sd=1;}
      paint();
    }));
  }
  paint();
}

sortTable($("#spatialGlobalTable"),
  [{key:"kind",label:"Kind"},{key:"short",label:"What it tests"},
   {key:"statistic",label:"Statistic"},{key:"value",label:"Value"},
   {key:"p",label:"p"},{key:"n",label:"n"},{key:"note",label:"Note"}],
  DATA.spatialGlobal);

sortTable($("#spatialTable"),
  [{key:"state",label:"State"},{key:"mpi_pct",label:"MPI %"},{key:"neighbours",label:"Neighbours"},
   {key:"spatial_lag_mpi_pct",label:"Lag MPI %"},{key:"spatial_quadrant",label:"Quadrant"},
   {key:"spatial_group",label:"Reading"},{key:"lisa_i",label:"Local I"},
   {key:"lisa_p",label:"p"},{key:"lisa_p_bonferroni",label:"p (Bonferroni)"}],
  DATA.spatial);

sortTable($("#partyTable"),
  [{key:"kind",label:"Block"},{key:"short",label:"Model"},{key:"beta",label:"beta"},
   {key:"ci_lo",label:"CI low"},{key:"ci_hi",label:"CI high"},{key:"p_perm",label:"p (perm)"},
   {key:"n",label:"n"},{key:"mde",label:"MDE"}],
  DATA.party);

const partyStateRows=DATA.partyState.map(r=>Object.assign({},r,
  {share_pct: r.aligned_years_1999_2021!==null && r.span_years
    ? (r.aligned_years_1999_2021/r.span_years*100) : null}));
sortTable($("#partyStateTable"),
  [{key:"state",label:"State"},{key:"aligned_years_1999_2021",label:"Years aligned"},
   {key:"span_years",label:"Span"},{key:"share_pct",label:"Share %"}],
  partyStateRows);

/* ---- boot ---- */
renderMaster();
drawScatter();
drawSparks();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    p = build()
    size = p.stat().st_size / 1024
    print(f"wrote {p}  ({size:.0f} KB)")
    d = load()
    print(f"  master rows: {len(d['master'])}")
    print(f"  panel rows:  {len(d['panel'])}  rounds: "
          f"{sorted({r['survey_year'] for r in d['panel']})}")
    print(f"  spatial rows:{len(d['spatial'])}   party models: {len(d['party'])}")
