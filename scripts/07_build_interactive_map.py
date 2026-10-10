"""Stage 7 -- CLI-only interactive filled choropleth (the no-GUI alternative).

Why this exists: Tableau's filled map needs a generated-geographic-field pairing
that only the GUI writes, so it cannot be produced blind from XML. This script
produces the same thing -- true filled ADM1 polygons -- 100% from the CLI with
plotly + the geoBoundaries GeoJSON already in data/raw. No Tableau, no login.

Reads:  data/processed/mpi_atlas_2021.csv (37 rows, incl. poverty_group)
        data/raw/nga_adm1.geojson (37 ADM1 features, keyed by shapeISO == pcode)
        data/reference/state_dominant_party.csv (37 rows: mode acronym, ties,
          winning years of the dominant party/parties -- hover context, §1)
        data/processed/party_alignment_state.csv (stage 8: years aligned with
          the federal ruling party, 1999-2021)
        data/processed/party_alignment_result.csv (stage 8: section 4 sentence,
          primary beta + CI)
Writes: docs/preview/interactive_map.html (self-contained, works offline)

Honesty rules baked in (docs/CLAIMS.md):
- colour is the 5-band mpi_band, never a continuous ramp (median rel SE 15%,
  all 36 adjacent pairs overlap at 95%)
- hover shows MPI + 95% CI, never a bare rank; Borno carries its 7/27-LGA flag
- toggle says Poorest 12 vs Other 25, never north vs south
- party (the dominant 1999-2021 governorship party with its winning years,
  see docs/dominant_party.md, plus years aligned with the federal ruling party
  over the whole 1999-2021 span -- NOT the 2013-21 test window) lives in the HOVER
  only, never on the map and never as colour: it is context, not an
  explanation (every causal path is closed at n=37 -- docs/CAUSAL_DECISION.md)
- the result panel below the map quotes docs/party_alignment.md section 4
  verbatim from stage 8's output; it is never re-worded here
"""

from __future__ import annotations

import base64
import copy
import csv
import html
import json
import re
import sys
from pathlib import Path

import atlas_text
from common import DOCS, PROCESSED, RAW, REFERENCE, alignment_context_line

ATLAS = PROCESSED / "mpi_atlas_2021.csv"
GEOJSON = RAW / "nga_adm1.geojson"
PARTY = REFERENCE / "state_dominant_party.csv"
ALIGN_STATE = PROCESSED / "party_alignment_state.csv"
ALIGN_RESULT = PROCESSED / "party_alignment_result.csv"
OUT = DOCS / "preview" / "interactive_map.html"
FLAG_PNG = DOCS / "preview" / "nigeria_flag.png"
COVER_JPG = DOCS / "preview" / "cover.jpg"

GREEN = "#008751"  # Nigerian flag green

BAND_ORDER = [
    "1. under 0.05",
    "2. 0.05 to 0.10",
    "3. 0.10 to 0.20",
    "4. 0.20 to 0.30",
    "5. 0.30 and above",
]
# ColorBrewer YlOrBr, 5-class sequential -- no red-green, readable by CVD.
BAND_COLORS = ["#ffffd4", "#fed98e", "#fe9929", "#d95f0e", "#993404"]


def read_atlas() -> list[dict[str, str]]:
    with ATLAS.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 37, f"expected 37 states, got {len(rows)}"
    assert {"poverty_group", "mpi_band", "mpi_se"}.issubset(rows[0]), (
        "run scripts/04_merge.py first for poverty_group + SEs"
    )
    return rows


def main() -> int:
    try:
        import plotly.graph_objects as go
    except ImportError:
        print("plotly is not installed in this interpreter", file=sys.stderr)
        return 1

    rows = read_atlas()
    gj = json.loads(GEOJSON.read_text(encoding="utf-8"))
    # Top-level `id` per feature: the most standard join key for the mapbox
    # renderer (featureidkey="id" is the default). The RAW file is untouched;
    # this copy lives only inside the HTML. (go.Choropleth on the geo subplot
    # drew a full-frame rectangle inside every path -- verified via the live
    # DOM -- so the map now renders through mapbox instead.)
    gj_plot = copy.deepcopy(gj)
    for feat in gj_plot["features"]:
        feat["id"] = feat["properties"]["shapeISO"]
    geo_ids = {f["properties"]["shapeISO"] for f in gj_plot["features"]}
    row_ids = {r["pcode"] for r in rows}
    assert row_ids == geo_ids, f"join mismatch: {sorted(row_ids ^ geo_ids)[:5]}"

    by_pcode = {r["pcode"]: r for r in rows}
    band_of = {r["pcode"]: r["mpi_band"] for r in rows}
    assert sorted(set(band_of.values())) == BAND_ORDER, "mpi_band values drifted"

    with ALIGN_STATE.open(newline="", encoding="utf-8-sig") as fh:
        align_rows = list(csv.DictReader(fh))
    assert len(align_rows) == 37, f"alignment file has {len(align_rows)} rows, expected 37"
    aligned_of = {r["pcode"]: r["aligned_years_1999_2021"] for r in align_rows}
    span_years = align_rows[0]["span_years"]
    assert set(aligned_of) == row_ids, (
        f"alignment join mismatch: {sorted(set(aligned_of) ^ row_ids)[:5]}"
    )
    with PARTY.open(newline="", encoding="utf-8-sig") as fh:
        party_rows = list(csv.DictReader(fh))
    assert len(party_rows) == 37, f"party file has {len(party_rows)} rows, expected 37"
    party_of = {r["pcode"]: r["dom_party"] for r in party_rows}
    years_of = {r["pcode"]: r["win_years"] for r in party_rows}
    assert set(party_of) == row_ids, (
        f"party join mismatch: {sorted(set(party_of) ^ row_ids)[:5]}"
    )

    poorest = [p for p in by_pcode if by_pcode[p]["poverty_group"] == "Poorest 12"]
    rest = [p for p in by_pcode if by_pcode[p]["poverty_group"] != "Poorest 12"]
    assert len(poorest) == 12 and len(rest) == 25, "poverty_group must be 12 vs 25"

    def band_short(band: str) -> str:
        return band.split(". ", 1)[1].replace(" to ", "–").replace(" and above", "+")

    def dominant_line(pcode: str) -> str:
        party = party_of[pcode]
        if party == "—":
            return "Party: none (FCT has no elected governor)"
        yrs = years_of[pcode].replace(",", ", ")
        if "|" in years_of[pcode]:
            segs = " · ".join(
                f"{p} ({y.replace(',', ', ')})"
                for p, y in (s.split(":") for s in years_of[pcode].split("|"))
            )
            return f"Party that won most often, 1999–2021 (tie): {segs}"
        return f"Party that won most often, 1999–2021: {party} ({yrs})"

    def party_years_line(pcode: str) -> str:
        # Two lines of context: the mode party (§1 of docs/party_alignment.md keeps
        # it as hover context) and the 1999-2021 alignment tally, labelled so it is
        # not mistaken for the 2013-21 test window.
        if party_of[pcode] == "—":
            return dominant_line(pcode)
        return (
            f"{dominant_line(pcode)}<br><i>Governor from the President's party: "
            f"{aligned_of[pcode]} of {span_years} years, 1999–2021</i>"
        )

    def share_words(pct: float) -> str:
        # "about 7 in 10" reads better than "1 in 1" once more than half are poor.
        if pct >= 20:
            return f"about {round(pct / 10)} in 10"
        return f"about 1 in {round(100 / pct)}"

    def poor_fmt(thousands: float) -> str:
        return f"≈{thousands / 1000:.1f}M" if thousands >= 1000 else f"≈{thousands:.0f}k"

    def hover(pcode: str) -> str:
        # Annotated hover: every metric carries its meaning in plain words.
        # Bold header, italic context subtitle, plain facts. (Plotly hover
        # supports <b>/<i>/<br>; arbitrary span colours do not survive, so
        # hierarchy comes from weight + slant, chrome from hoverlabel below.)
        r = by_pcode[pcode]
        h = float(r["headcount_ratio_pct"])
        a = float(r["intensity_pct"])
        base = (
            f"<b>{r['state']}</b><br>"
            f"<i>{r['poverty_group']} · poverty band {band_short(r['mpi_band'])}</i><br>"
            f"Poverty score (MPI) {float(r['mpi']):.3f} "
            f"(likely range {float(r['mpi_ci_lo']):.3f}–{float(r['mpi_ci_hi']):.3f})<br>"
            f"{h:.1f}% of people are poor ({share_words(h)}); "
            f"the poor miss {a:.0f}% of basic needs<br>"
            f"{poor_fmt(float(r['mpi_poor_thousands']))} people are poor<br>"
            f"{party_years_line(pcode)}"
        )
        if pcode == "NG-BO":
            base += "<br><i>⚠ Borno: 7 of 27 LGAs sampled in MICS 2021</i>"
        return base

    HOVER_CHROME = dict(
        bgcolor="white", bordercolor="#8a8a8a",
        font=dict(family="Arial, sans-serif", size=12, color="#22252a"),
    )

    def trace(pcodes: list[str], name: str) -> go.Choroplethmapbox:
        z = [BAND_ORDER.index(band_of[p]) for p in pcodes]
        return go.Choroplethmapbox(
            geojson=gj_plot,
            featureidkey="id",
            locations=pcodes,
            z=z,
            zmin=0,
            zmax=4,
            colorscale=[[i / 4, c] for i, c in enumerate(BAND_COLORS)],
            colorbar=dict(title="MPI band", tickvals=list(range(5)), ticktext=BAND_ORDER),
            hovertext=[hover(p) for p in pcodes],
            hoverinfo="text",
            hoverlabel=HOVER_CHROME,
            marker_line_color="white",
            marker_line_width=1.0,
            marker_opacity=0.93,
            name=name,
        )

    fig = go.Figure()
    fig.add_trace(trace(poorest, "Poorest 12"))
    fig.add_trace(trace(rest, "Other 25"))

    fig.update_layout(
        title=(
            "🇳🇬 Nigeria MPI Equity Atlas — Where poverty sits<br>"
            "<sup>MICS 2021 · 36 states + FCT · 5 bands, not 37 ranks. "
            "Hover over a state for its poverty score.</sup>"
        ),
        mapbox=dict(
            # Blank base: no tile server, no API key, works fully offline.
            # (carto-positron now watermarks without a key.)
            style="white-bg",
            center=dict(lat=9.2, lon=8.5),
            zoom=4.8,
        ),
        # Fixed height: with the default 100%-of-window height, a laptop screen left
        # ~290 px for the map and the fixed zoom cut Nigeria off top and bottom.
        # Zoom and centre are refitted to the real map box by FIT_JS on load,
        # resize and every view button, so no screen width clips a state.
        height=MAP_HEIGHT,
        margin=dict(l=10, r=10, t=170, b=110),
        annotations=[
            dict(
                text=(
                    "All 37 — every state · Poorest 12 — the 12 highest-MPI states, "
                    "held back most by schooling and living standards · "
                    "Other 25 — the rest"
                ),
                x=0,
                y=1.03,
                xref="paper",
                yref="paper",
                xanchor="left",
                showarrow=False,
                font=dict(size=11, color="#444444"),
                align="left",
            ),
            dict(
                text=(
                    "Global MPI, harmonised series (OPHI Table 6, MN 63). Health = child mortality "
                    "alone (Nutrition missing everywhere); within-Nigeria OK, cross-country no.<br>"
                    "Boundaries: geoBoundaries ADM1. Capitals: GeoNames. "
                    "Say Poorest 12 vs Other 25, never north vs south.<br>"
                    "Party (hover only): the party that most often won the governorship, and the "
                    "years the governor shared the President's party, 1999–2021. Colours show poverty, never party."
                ),
                x=0,
                y=-0.14,
                xref="paper",
                yref="paper",
                xanchor="left",
                showarrow=False,
                font=dict(size=10, color="#555555"),
                align="left",
            )
        ],
        updatemenus=[
            # Each button sets trace visibility AND re-fits the viewport, so a
            # filtered view never clips its edge states (Sokoto up north,
            # Borno out east). Keys use Plotly's dotted layout-update syntax.
            dict(
                type="buttons",
                direction="right",
                x=0.0,
                y=1.10,
                xanchor="left",
                yanchor="top",
                showactive=True,
                buttons=[
                    dict(label="All 37", method="restyle", args=[{"visible": [True, True]}]),
                    dict(label="Poorest 12", method="restyle", args=[{"visible": [True, False]}]),
                    dict(label="Other 25", method="restyle", args=[{"visible": [False, True]}]),
                ],
            )
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUT), include_plotlyjs=True, full_html=True,
                   default_height=f"{MAP_HEIGHT}px")
    _add_fit_script({
        "All 37": _bounds(gj_plot, set(by_pcode)),
        "Poorest 12": _bounds(gj_plot, set(poorest)),
        "Other 25": _bounds(gj_plot, set(rest)),
    })
    _add_cover()
    _add_result_panel()
    _add_reader_sections()
    print(f"wrote {OUT.relative_to(Path.cwd())} ({OUT.stat().st_size/1024:.0f} KB)")
    print("bands: " + ", ".join(f"{b}={sum(1 for v in band_of.values() if v==b)}" for b in BAND_ORDER))
    print(f"toggle: Poorest 12 = {len(poorest)}, Other 25 = {len(rest)}")
    return 0


MAP_HEIGHT = 860

FIT_JS = """<script>
(function () {
  // Fit the selected view's bounding box into the map's real pixel box.
  // Web-mercator maths for 512 px tiles; 8% padding so edge states never touch.
  var BOUNDS = __BOUNDS__, view = "All 37";
  var g = document.querySelector(".plotly-graph-div");
  function merc(lat) { var r = lat * Math.PI / 180; return Math.log(Math.tan(Math.PI / 4 + r / 2)); }
  function fit() {
    var s = g._fullLayout && g._fullLayout._size;
    if (!s) return;
    var b = BOUNDS[view], w = s.w * 0.92, h = s.h * 0.92;
    var lonSpan = (b[2] - b[0]) * Math.PI / 180, latSpan = merc(b[3]) - merc(b[1]);
    var zoom = Math.log2(Math.min(w * 2 * Math.PI / (lonSpan * 512), h * 2 * Math.PI / (latSpan * 512)));
    var my = (merc(b[1]) + merc(b[3])) / 2;
    var lat = (2 * Math.atan(Math.exp(my)) - Math.PI / 2) * 180 / Math.PI;
    Plotly.relayout(g, {"mapbox.zoom": zoom, "mapbox.center.lat": lat, "mapbox.center.lon": (b[0] + b[2]) / 2});
  }
  // Narrow screens: Plotly never wraps text and a vertical legend eats half the
  // width, so swap to a horizontal legend under the map and pre-broken lines.
  var NARROW = __NARROW__, wide = null, mode = null;
  function arrange() {
    var m = window.innerWidth < 700 ? "narrow" : "wide";
    if (m === mode) return Promise.resolve();
    mode = m;
    var L = g.layout, both = [0, 1];
    if (!wide) {
      wide = {title: L.title.text, a0: L.annotations[0].text, a1: L.annotations[1].text,
              a1y: L.annotations[1].y, a0y: L.annotations[0].y, menuY: L.updatemenus[0].y, margin: Object.assign({}, L.margin),
              cb: JSON.parse(JSON.stringify(g.data[0].colorbar))};
    }
    var n = m === "narrow";
    legend.style.display = n ? "flex" : "none";
    var h = n ? 170 + Math.round((window.innerWidth - 20) * 0.9) + 120 : __HEIGHT__;
    g.style.height = h + "px";
    return Plotly.restyle(g, {"showscale": !n}, both).then(function () {
      return Plotly.relayout(g, n ? {
        "title.text": NARROW.title, "annotations[0].text": NARROW.a0,
        "annotations[1].text": NARROW.a1, "annotations[1].y": -0.04,
        "annotations[1].yanchor": "top", "margin.r": 10, "margin.b": 120, "height": h,
        // Pixel-placed above the map: buttons, then the two-line caption.
        "updatemenus[0].y": 1 + 92 / (h - 290), "annotations[0].y": 1 + 6 / (h - 290),
        "annotations[0].yanchor": "bottom",
        "margin.autoexpand": false
      } : {
        "title.text": wide.title, "annotations[0].text": wide.a0, "annotations[1].text": wide.a1,
        "annotations[1].y": wide.a1y, "annotations[1].yanchor": "auto", "height": h,
        "updatemenus[0].y": wide.menuY, "annotations[0].y": wide.a0y, "annotations[0].yanchor": "auto",
        "margin.r": wide.margin.r, "margin.b": wide.margin.b,
        "margin.autoexpand": true
      });
    });
  }
  // HTML legend for narrow screens, inserted under the map once.
  var legend = document.createElement("div");
  legend.setAttribute("role", "list");
  legend.setAttribute("aria-label", "MPI band");
  legend.style.cssText = "display:none;flex-wrap:wrap;gap:6px 14px;margin:0 10px 12px;" +
    "font:12px Arial,sans-serif;color:#22252a;";
  legend.innerHTML = "<b style='width:100%'>MPI band</b>" + NARROW.ticks.map(function (t, i) {
    return "<span role='listitem' style='display:inline-flex;align-items:center;gap:5px'>" +
      "<span style='width:14px;height:14px;border:1px solid #8a8a8a;background:" +
      NARROW.colors[i] + "'></span>" + t + "</span>";
  }).join("");
  g.parentNode.insertBefore(legend, g.nextSibling);
  function refresh() {
    // Width first (Plotly keeps the old width after a height-only relayout).
    arrange().then(function () { return Plotly.Plots.resize(g); }).then(fit);
  }
  function init() { if (g._fullLayout && g._fullLayout._size) { refresh(); } else { setTimeout(init, 100); } }
  g.on && g.on("plotly_buttonclicked", function (e) { view = e.button.label; fit(); });
  var timer;
  window.addEventListener("resize", function () { clearTimeout(timer); timer = setTimeout(refresh, 250); });
  window.addEventListener("load", init);
})();
</script>"""


def _bounds(gj: dict, pcodes: set[str]) -> list[float]:
    """[west, south, east, north] of the given states' polygons."""
    xs: list[float] = []
    ys: list[float] = []

    def walk(c: list) -> None:
        if c and isinstance(c[0], (int, float)):
            xs.append(float(c[0]))
            ys.append(float(c[1]))
        else:
            for sub_c in c:
                walk(sub_c)

    for feat in gj["features"]:
        if feat["id"] in pcodes:
            walk(feat["geometry"]["coordinates"])
    assert xs, "no polygons for this view"
    return [min(xs), min(ys), max(xs), max(ys)]


def _add_fit_script(views: dict[str, list[float]]) -> None:
    page = OUT.read_text(encoding="utf-8")
    assert page.count("</body>") == 1
    narrow = {
        "ticks": ["under 0.05", "0.05–0.10", "0.10–0.20", "0.20–0.30", "0.30 and above"],
        "colors": BAND_COLORS,
        "title": (
            "🇳🇬 Nigeria MPI Equity Atlas<br><sup>Where poverty sits · MICS 2021<br>"
            "5 bands, not 37 ranks. Tap a state for details.</sup>"
        ),
        "a0": "Poorest 12 — the 12 highest-MPI states<br>Other 25 — the rest",
        "a1": (
            "Global MPI, harmonised series (OPHI Table 6, MN 63).<br>"
            "Health = child mortality alone; compare within<br>Nigeria only. "
            "Boundaries: geoBoundaries. Capitals: GeoNames.<br>"
            "Party appears in the hover only. Colours show<br>poverty, never party."
        ),
    }
    script = (
        FIT_JS
        .replace("__BOUNDS__", json.dumps({k: [round(v, 4) for v in b] for k, b in views.items()}))
        .replace("__NARROW__", json.dumps(narrow, ensure_ascii=False))
        .replace("__HEIGHT__", str(MAP_HEIGHT))
    )
    OUT.write_text(page.replace("</body>", script + "</body>"), encoding="utf-8")


def _add_result_panel() -> None:
    """Append the stage 8 result below the map: the section 4 sentence, verbatim,
    and a mini chart of the primary estimate with its 95% CI.

    The sentence is read from stage 8's output (it chose it from the
    pre-registered templates); markdown *italics* become <i>. Neutral greys only.
    """
    with ALIGN_RESULT.open(newline="", encoding="utf-8-sig") as fh:
        res = list(csv.DictReader(fh))
    primary = res[0]
    assert primary["kind"] == "primary" and primary["sentence"], (
        "run scripts/08_party_alignment.py first"
    )
    checks = [r for r in res if r["kind"] in {"robustness", "loio"}]
    assert checks, "party_alignment_result.csv has no robustness rows"
    context = alignment_context_line(res)
    rows_html = "".join(
        f'<tr><td style="padding:2px 10px 2px 0;">{html.escape(r["short"])}</td>'
        f'<td style="padding:2px 8px;text-align:right;">{float(r["beta"]):+.4f}</td>'
        f'<td style="padding:2px 8px;text-align:right;white-space:nowrap;">'
        f'{float(r["ci_lo"]):+.4f} to {float(r["ci_hi"]):+.4f}</td>'
        f'<td style="padding:2px 0 2px 8px;text-align:right;">{r["p_perm"]}</td></tr>'
        for r in checks
    )
    checks_html = (
        '<table style="border-collapse:collapse;font-size:12px;color:#333;">'
        '<thead><tr style="color:#666;border-bottom:1px solid #d9d9d9;">'
        '<th style="text-align:left;padding:2px 10px 4px 0;font-weight:600;">Check</th>'
        '<th style="text-align:right;padding:2px 8px 4px;font-weight:600;">β</th>'
        '<th style="text-align:right;padding:2px 8px 4px;font-weight:600;">95% CI</th>'
        '<th style="text-align:right;padding:2px 0 4px 8px;font-weight:600;">p</th></tr></thead>'
        f"<tbody>{rows_html}</tbody></table>"
    )
    context_html = (
        f'<p style="margin:12px 0 0;font-size:13px;font-weight:700;">{html.escape(context)}</p>'
        if context else ""
    )
    sentence = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", html.escape(primary["sentence"]))
    beta, lo, hi = (float(primary[k]) for k in ("beta", "ci_lo", "ci_hi"))

    # Mini chart: an axis symmetric about zero, the CI as a bar, beta as a dot.
    width, height, pad = 520, 96, 40
    span = max(abs(lo), abs(hi), abs(beta)) * 1.25

    def sx(v: float) -> float:
        return pad + (v + span) / (2 * span) * (width - 2 * pad)

    ticks = [-span * 0.8, -span * 0.4, 0.0, span * 0.4, span * 0.8]
    tick_svg = "".join(
        f'<line x1="{sx(t):.1f}" y1="58" x2="{sx(t):.1f}" y2="62" stroke="#8a8a8a"/>'
        f'<text x="{sx(t):.1f}" y="75" font-size="10" text-anchor="middle" fill="#555">{t:+.3f}</text>'
        for t in ticks
    )
    svg = (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Primary estimate {beta:+.4f}, 95% CI {lo:+.4f} to {hi:+.4f}" '
        'style="max-width:100%;height:auto;display:block;">'
        f'<line x1="{pad}" y1="58" x2="{width - pad}" y2="58" stroke="#8a8a8a"/>'
        f'<line x1="{sx(0):.1f}" y1="28" x2="{sx(0):.1f}" y2="58" stroke="#8a8a8a" stroke-dasharray="3,3"/>'
        f'<line x1="{sx(lo):.1f}" y1="38" x2="{sx(hi):.1f}" y2="38" stroke="#4a4f57" stroke-width="3"/>'
        f'<line x1="{sx(lo):.1f}" y1="32" x2="{sx(lo):.1f}" y2="44" stroke="#4a4f57" stroke-width="2"/>'
        f'<line x1="{sx(hi):.1f}" y1="32" x2="{sx(hi):.1f}" y2="44" stroke="#4a4f57" stroke-width="2"/>'
        f'<circle cx="{sx(beta):.1f}" cy="38" r="6" fill="#22252a"/>'
        f'<text x="{sx(beta):.1f}" y="22" font-size="11" text-anchor="middle" fill="#22252a">'
        f"β {beta:+.4f} (95% CI {lo:+.4f} to {hi:+.4f})</text>{tick_svg}"
        f'<text x="{width / 2:.0f}" y="92" font-size="10" text-anchor="middle" fill="#555">'
        "MPI change per year per unit of aligned share (primary model)</text></svg>"
    )
    lead, summary = _plain_summary(res, checks)
    plain_rows = "".join(
        f'<tr style="border-top:1px solid #eee;"><td style="padding:5px 12px 5px 0;">'
        f"{html.escape(_plain_check_label(r))}</td>"
        f'<td style="padding:5px 0;font-weight:600;white-space:nowrap;">'
        f'{"Yes" if float(r["p_perm"]) < 0.05 else "No"}</td></tr>'
        for r in checks
    )
    panel = f"""<style>
.pa-panel summary{{display:inline-block;cursor:pointer;list-style:none;margin:14px 10px 0 0;
padding:8px 14px;border:1px solid #4a4f57;border-radius:999px;font-size:14px;font-weight:600;
color:#22252a;background:#fff;}}
.pa-panel summary::-webkit-details-marker{{display:none;}}
.pa-panel summary:hover{{background:#f2f3f5;}}
.pa-panel summary:focus-visible{{outline:3px solid #1f6feb;outline-offset:2px;}}
.pa-panel details[open] > summary{{background:#22252a;color:#fff;}}
.pa-panel details > div{{margin-top:14px;}}
.pa-panel .pa-swipe{{display:none;}}
@media (max-width:699px){{.pa-panel .pa-swipe{{display:block;}}}}
</style>
<div class="pa-panel" id="party-question" style="font-family:-apple-system,'Segoe UI',Arial,sans-serif;max-width:860px;
margin:8px auto 40px;padding:18px 22px;border:1px solid #d9d9d9;border-radius:10px;color:#22252a;">
<h2 style="margin:0 0 10px;font-size:20px;line-height:1.3;">Does having a governor from the
President's party help a state cut poverty faster?</h2>
<p style="margin:0 0 8px;font-size:17px;font-weight:700;">{html.escape(lead)}</p>
<p style="margin:0 0 14px;font-size:15px;line-height:1.6;max-width:70ch;">{html.escape(summary)}</p>
<p style="margin:0 0 4px;font-size:14px;font-weight:700;">We re-tested it in {len(checks)} other ways.
Was the gap still there?</p>
<table style="border-collapse:collapse;font-size:14px;color:#333;margin-bottom:4px;">
<tbody>{plain_rows}</tbody></table>
<details>
<summary>Why we can't say the party caused it</summary>
<div>{_causal_graph_html()}</div>
</details>
<details>
<summary>Technical details</summary>
<div>
<p style="margin:0 0 6px;font-size:12px;letter-spacing:2px;color:#555;font-weight:700;">
PRE-REGISTERED TEST · FEDERAL ALIGNMENT AND MPI CHANGE, 2013–2021</p>
<p style="margin:0 0 6px;font-size:13px;color:#555;">The exact wording below was fixed before
the analysis was run (docs/party_alignment.md).</p>
<div style="display:flex;flex-wrap:wrap;gap:18px 28px;align-items:flex-start;">
<div style="flex:1 1 400px;min-width:0;">
<p style="margin:0 0 12px;font-size:15px;line-height:1.5;">{sentence}</p>
{svg}
</div>
<div style="flex:0 1 360px;min-width:0;overflow-x:auto;">
<p style="margin:0 0 6px;font-size:11px;letter-spacing:1px;color:#666;font-weight:700;">
ROBUSTNESS AND LEAVE-ONE-INTERVAL-OUT</p>
{checks_html}
</div>
</div>
{context_html}
<p style="margin:10px 0 0;font-size:11px;color:#666;">n = {primary["n"]} state-intervals; FCT
excluded (no elected governor). Minimum detectable effect {primary["mde"]} per year. Check (d)
and the interval rows were added after the primary result was known. Permutation p is a Monte
Carlo estimate (about ±0.005). Per-interval estimates and method: docs/party_alignment.md §4.</p>
</div>
</details>
</div>"""
    page = OUT.read_text(encoding="utf-8")
    assert page.count("</body>") == 1
    OUT.write_text(page.replace("</body>", panel + "</body>"), encoding="utf-8")


PLAIN_CHECK_LABELS = {
    "(a)": "Measuring the change in percent instead of points",
    "(b)": "Letting poorer and less-poor states follow their own trends",
    "(c)": "Counting a state simply as 'in' or 'out' of the President's party",
    "(d)": "Counting governors who switched party under their new party",
}


def _plain_check_label(row: dict[str, str]) -> str:
    """Everyday wording for one robustness row; fails loudly on an unknown check."""
    if row["kind"] == "loio":
        return f"Leaving out the years {row['interval']}"
    key = row["short"].split(" ", 1)[0]
    assert key in PLAIN_CHECK_LABELS, f"no plain label for check {row['short']!r}"
    return PLAIN_CHECK_LABELS[key]


def _plain_summary(res: list[dict[str, str]], checks: list[dict[str, str]]) -> tuple[str, str]:
    """A plain-language reading of the pre-registered result, built from the CSV.

    It may not say more than the section 4 sentence plus the robustness rows:
    direction and size only when detected, how many re-tests kept the gap, and
    no cause. The exact pre-registered sentence stays under "Technical details".
    """
    primary = res[0]
    beta, p = float(primary["beta"]), float(primary["p_perm"])
    held = sum(float(r["p_perm"]) < 0.05 for r in checks)
    years = "Between 2013 and 2021"
    who = "states whose governor belonged to the President's party"
    no_gov = "FCT is left out because it has no elected governor."
    if p >= 0.05:
        return (
            "Short answer: we can't see a clear link.",
            (
                f"{years}, poverty did not fall at a clearly different pace in {who} "
                "than in other states. With only 36 states and four surveys, a small "
                f"difference could still exist without us being able to see it. {no_gov}"
            ),
        )
    pace = "a little more slowly" if beta > 0 else "a little faster"
    if held == len(checks):
        return (
            "Short answer: there is a small gap, and it held up when we re-tested it.",
            (
                f"{years}, poverty fell {pace} in {who} than in other states. The gap "
                f"was still there in all {len(checks)} re-tests. That shows a pattern, "
                f"not that the party caused it. {no_gov}"
            ),
        )
    per = [r for r in res if r["kind"] == "per_interval"]
    rests = [r["interval"] for r in per if float(r["p_perm"]) < 0.05]
    where = (
        f", it comes mostly from {' and '.join(rests)}"
        if rests and len(rests) < len(per) else ""
    )
    return (
        "Short answer: we can't really tell.",
        (
            f"{years}, poverty fell {pace} in {who} than in other states. But the gap "
            f"is small{where}, and it was still there in only {held} of {len(checks)} "
            "re-tests. Treat it as a hint, not a finding. Even a solid gap would not "
            f"show that the party caused it. {no_gov}"
        ),
    )


def _causal_graph_html() -> str:
    """A plain-language cause-and-effect diagram: why the party comparison can show
    a pattern but not a cause. Inline SVG, greys only, readable without colour."""
    box = (
        '<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" '
        'stroke="#4a4f57" stroke-width="1.5"/>'
    )

    def node(x: int, y: int, w: int, h: int, lines: list[str], *, fill: str = "#fff",
             bold: bool = False) -> str:
        weight = ' font-weight="700"' if bold else ""
        cy = y + h / 2 - (len(lines) - 1) * 9
        text = "".join(
            f'<text x="{x + w / 2:.0f}" y="{cy + i * 18 + 5:.0f}" font-size="14" '
            f'text-anchor="middle" fill="#22252a"{weight}>{html.escape(t)}</text>'
            for i, t in enumerate(lines)
        )
        return box.format(x=x, y=y, w=w, h=h, fill=fill) + text

    def arrow(x1: float, y1: float, x2: float, y2: float, *, dashed: bool = False) -> str:
        dash = ' stroke-dasharray="7,5"' if dashed else ""
        return (
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#4a4f57" '
            f'stroke-width="2"{dash} marker-end="url(#pa-arrow)"/>'
        )

    svg = (
        '<svg viewBox="0 0 760 430" role="img" aria-labelledby="pa-dag-title pa-dag-desc" '
        'style="width:100%;min-width:640px;max-width:760px;height:auto;display:block;" '
        'font-family="-apple-system,Segoe UI,Arial,sans-serif">'
        '<title id="pa-dag-title">Why party cannot be shown to cause the poverty change</title>'
        '<desc id="pa-dag-desc">Four other things push on the comparison: where a state is '
        "and how poor it already was, which affects both its party and its poverty; voters "
        "choosing governors; the big national events around the 2015 change of President; "
        "and survey error in measuring poverty. The arrow from party to poverty is the "
        "question mark we tested.</desc>"
        '<defs><marker id="pa-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" '
        'markerHeight="8" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" '
        'fill="#4a4f57"/></marker></defs>'
        # the tested question
        + node(20, 170, 220, 74, ["Governor is from the", "President's party"], fill="#f2f3f5", bold=True)
        + node(520, 170, 220, 74, ["How fast poverty", "fell in the state"], fill="#f2f3f5", bold=True)
        + arrow(240, 207, 516, 207, dashed=True)
        + '<text x="380" y="196" font-size="22" font-weight="700" text-anchor="middle" fill="#22252a">?</text>'
        + '<text x="380" y="232" font-size="12" text-anchor="middle" fill="#555">what we tested</text>'
        # 1: region and starting poverty -> both
        + node(260, 14, 240, 62, ["1. Where the state is and", "how poor it already was"])
        + arrow(300, 76, 170, 166) + arrow(460, 76, 590, 166)
        # 2: voters -> party
        + node(20, 330, 200, 62, ["2. Who voters chose"])
        + arrow(120, 330, 120, 248)
        # 3: national events around 2015 -> both
        + node(260, 330, 240, 62, ["3. Big events around 2015:", "oil price fall, recession"])
        + arrow(300, 330, 200, 248) + arrow(460, 330, 560, 248)
        # 4: survey error -> measured poverty change
        + node(540, 330, 200, 62, ["4. Survey error", "(only 4 surveys)"])
        + arrow(640, 330, 640, 248)
        + "</svg>"
    )
    notes = [
        ("Where the state is and how poor it already was",
         "shapes both which party tends to win and how much poverty can fall."),
        ("Who voters chose",
         ("decides the governor's party, so party is not handed out at random the "
          "way a fair test would need.")),
        ("Big events around 2015",
         ("the President's party changed in 2015, the same time as an oil price fall "
          "and a recession, so we can't pull party apart from timing.")),
        ("Survey error",
         ("poverty is measured by surveys only four times, giving each state just "
          "three changes to compare, each with some error.")),
    ]
    items = "".join(
        f'<li style="margin:0 0 6px;"><b>{html.escape(t)}</b> {html.escape(d)}</li>'
        for t, d in notes
    )
    return (
        '<p class="pa-swipe" style="margin:0 0 6px;font-size:13px;color:#555;">'
        "Swipe sideways to see the whole diagram.</p>"
        f'<div style="overflow-x:auto;">{svg}</div>'
        '<p style="margin:12px 0 6px;font-size:15px;line-height:1.6;max-width:70ch;">The dashed '
        "arrow is the question we asked. The four numbered boxes also push on the result, and "
        "we can't fully separate them from the party effect:</p>"
        f'<ol style="margin:0 0 8px 20px;padding:0;font-size:15px;line-height:1.6;max-width:70ch;">{items}</ol>'
        '<p style="margin:0;font-size:15px;line-height:1.6;max-width:70ch;">To prove cause and '
        "effect we would need something like a fair experiment. We don't have one, so the atlas "
        "only describes patterns.</p>"
    )


def _add_reader_sections() -> None:
    """Append the two reader sheets from scripts/atlas_text.py: what the words mean,
    and how the atlas was made, in plain language. Same text as the Tableau
    dashboards (stage 6)."""
    e = html.escape
    terms = "".join(
        f'<div class="rd-term"><dt>{e(t["term"])}</dt><dd>{e(t["meaning"])}</dd></div>'
        for t in atlas_text.TERMS
    )
    rows = "".join(
        f'<tr><td data-label="Area">{e(i["area"])}</td>'
        f'<td data-label="Need"><b>{e(i["need"])}</b></td>'
        f'<td data-label="Weight" class="rd-num">{e(i["weight"])}</td>'
        f'<td data-label="Missing if">{e(i["missing_if"])}</td></tr>'
        for i in atlas_text.INDICATORS
    )
    example = "".join(
        f'<tr><td>{e(item)}</td><td class="rd-num">{e(w)}</td></tr>'
        for item, w in atlas_text.EXAMPLE_LINES
    )
    method = "".join(
        f'<h3>{e(s["heading"])}</h3>' + "".join(f"<p>{e(par)}</p>" for par in s["paragraphs"])
        for s in atlas_text.METHOD
    )
    block = f"""<style>
.rd{{font-family:-apple-system,'Segoe UI',Arial,sans-serif;max-width:860px;margin:0 auto 40px;
padding:20px 22px;border:1px solid #d9d9d9;border-radius:10px;color:#22252a;line-height:1.6;}}
.rd h2{{font-size:24px;margin:0 0 6px;}} .rd h3{{font-size:17px;margin:22px 0 4px;}}
.rd p{{font-size:15px;margin:0 0 10px;max-width:72ch;}}
.rd dl{{margin:12px 0 0;}} .rd-term{{padding:10px 0;border-top:1px solid #eee;}}
.rd dt{{font-weight:700;font-size:15px;}} .rd dd{{margin:2px 0 0;font-size:15px;max-width:72ch;}}
.rd-scroll{{overflow-x:auto;margin:10px 0;}}
.rd table{{border-collapse:collapse;font-size:14px;width:100%;min-width:560px;}}
.rd th{{text-align:left;font-size:12px;letter-spacing:1px;color:#555;padding:6px 10px 6px 0;
border-bottom:2px solid #d9d9d9;}}
.rd td{{padding:7px 10px 7px 0;border-top:1px solid #eee;vertical-align:top;}}
.rd .rd-num{{white-space:nowrap;}}
.rd .rd-example{{background:#f6f7f8;border-radius:8px;padding:14px 16px;margin:16px 0 0;}}
.rd .rd-example table{{min-width:0;}}
@media (max-width:599px){{
.rd .rd-needs table,.rd .rd-needs tbody,.rd .rd-needs tr,.rd .rd-needs td{{display:block;min-width:0;}}
.rd .rd-needs thead{{display:none;}}
.rd .rd-needs tr{{border-top:1px solid #d9d9d9;padding:8px 0;}}
.rd .rd-needs td{{border:0;padding:2px 0;}}
.rd .rd-needs td::before{{content:attr(data-label) ": ";color:#555;font-size:13px;}}
}}
.rd .rd-top{{font-size:14px;}} .rd .rd-top a{{color:#22252a;}}
</style>
<section class="rd" id="words" aria-labelledby="words-h">
<h2 id="words-h">{e(atlas_text.WORDS_TITLE)}</h2>
<p>{e(atlas_text.WORDS_INTRO)}</p>
<dl>{terms}</dl>
<h3>{e(atlas_text.INDICATORS_TITLE)}</h3>
<p>{e(atlas_text.INDICATORS_INTRO)}</p>
<div class="rd-scroll rd-needs"><table>
<thead><tr><th>AREA</th><th>NEED</th><th>WEIGHT</th><th>MISSING IF…</th></tr></thead>
<tbody>{rows}</tbody></table></div>
<p>{e(atlas_text.INDICATORS_NOTE)}</p>
<div class="rd-example"><h3 style="margin-top:0;">{e(atlas_text.EXAMPLE_TITLE)}</h3>
<table><tbody>{example}
<tr><td><b>Deprivation score</b></td><td class="rd-num"><b>{e(atlas_text.EXAMPLE_TOTAL)}</b></td></tr>
</tbody></table>
<p style="margin:10px 0 0;">{e(atlas_text.EXAMPLE_VERDICT)}</p></div>
<p class="rd-top" style="margin-top:16px;"><a href="#atlas-map">Back to the map ↑</a></p>
</section>
<section class="rd" id="method" aria-labelledby="method-h">
<h2 id="method-h">{e(atlas_text.METHOD_TITLE)}</h2>
<p>{e(atlas_text.METHOD_INTRO)}</p>
{method}
<p class="rd-top" style="margin-top:16px;"><a href="#atlas-map">Back to the map ↑</a></p>
</section>"""
    page = OUT.read_text(encoding="utf-8")
    assert page.count("</body>") == 1
    OUT.write_text(page.replace("</body>", block + "</body>"), encoding="utf-8")


def flag_data_uri() -> str:
    """Nigerian flag PNG (green-white-green), generated once, embedded base64."""
    if not FLAG_PNG.exists():
        from PIL import Image

        img = Image.new("RGB", (300, 200), "white")
        green = Image.new("RGB", (100, 200), GREEN)
        img.paste(green, (0, 0))
        img.paste(green, (200, 0))
        img.save(FLAG_PNG)
    return "data:image/png;base64," + base64.b64encode(FLAG_PNG.read_bytes()).decode()


def _add_cover() -> None:
    """Prepend a cover hero to the map HTML: title, flag, unity emblem, chips.

    Framing is deliberate: "one country, two realities — poorest states vs
    the rest". Never "two zones" / north-vs-south: at n=37 those are the same
    12 observations wearing a geographic label (docs/CAUSAL_DECISION.md), and
    the atlas rules forbid it (docs/CLAIMS.md). Imagery is two Nigerians as
    one people, with no zone labels.

    Photo slot: drop a licensed photo at docs/preview/cover.jpg and rebuild
    to feature it in the hero; otherwise a vector emblem shows. No
    hotlinking: the file stays fully offline and self-contained.
    """
    if COVER_JPG.exists():
        photo = (
            "data:image/jpeg;base64,"
            + base64.b64encode(COVER_JPG.read_bytes()).decode()
        )
        visual = (
            '<img src="' + photo + '" alt="Two Nigerians shaking hands" '
            'style="max-width:620px;width:92%;border-radius:14px;margin:26px auto 0;display:block;">'
        )
    else:
        visual = (
            '<svg width="300" height="150" viewBox="0 0 300 150" role="img" '
            'aria-label="Two overlapping circles in Nigerian green, symbolising unity" '
            'style="margin:26px auto 0;display:block;">'
            f'<circle cx="118" cy="75" r="52" fill="none" stroke="{GREEN}" stroke-width="10"/>'
            '<circle cx="182" cy="75" r="52" fill="none" stroke="#22252a" stroke-width="10"/>'
            f'<circle cx="150" cy="75" r="10" fill="{GREEN}"/>'
            "</svg>"
            '<p style="color:#777;font-size:12px;">Add <code>docs/preview/cover.jpg</code> '
            "and rebuild to feature a photo here.</p>"
        )
    cover = f"""<style>
.atlas-cover{{font-family:-apple-system,'Segoe UI',Arial,sans-serif;text-align:center;
padding:0 20px 60px;margin:0;position:relative;overflow:hidden;}}
.atlas-watermark{{position:absolute;inset:0;pointer-events:none;opacity:.06;
background:url("{flag_data_uri()}") center 38%/min(880px,95%) no-repeat;}}
.atlas-flagbar{{height:12px;margin:0 -8px;position:relative;
background:linear-gradient(to right,{GREEN} 0 33.3%,#fff 33.3% 66.6%,{GREEN} 66.6% 100%);
border-bottom:1px solid #e3e3e3;}}
.atlas-eyebrow{{color:{GREEN};letter-spacing:3px;font-size:13px;font-weight:700;margin:44px 0 10px;}}
.atlas-cover h1{{font-family:Georgia,'Times New Roman',serif;font-size:56px;margin:0 0 12px;color:#1a1a1a;}}
.atlas-sub{{font-size:18px;color:#444;max-width:720px;margin:0 auto;line-height:1.55;}}
.atlas-chips{{margin:24px 0 0;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;}}
.atlas-chips span{{border:1px solid #c9c9c9;border-radius:999px;padding:7px 16px;font-size:13px;color:#333;background:#fff;}}
.atlas-nav{{margin-top:34px;display:flex;gap:10px;justify-content:center;flex-wrap:wrap;}}
.atlas-nav a{{color:{GREEN};font-weight:700;font-size:15px;text-decoration:none;
border:2px solid {GREEN};border-radius:999px;padding:8px 16px;background:#fff;}}
.atlas-nav a:hover,.atlas-nav a:focus-visible{{background:{GREEN};color:#fff;}}
</style>
<div class="atlas-cover">
<div class="atlas-watermark"></div>
<div class="atlas-flagbar"></div>
<p class="atlas-eyebrow">🇳🇬 NIGERIA · MULTIDIMENSIONAL POVERTY EQUITY ATLAS · MICS 2021</p>
<h1>One country, two realities.</h1>
<p class="atlas-sub">Poverty fell, but its shape held: the poorest states are held
back by schooling and living standards far more than the rest. Hover, filter and compare.</p>
<div class="atlas-chips"><span>National MPI 0.175</span><span>36 states + FCT</span>
<span>4 survey rounds</span><span>Read bands, not ranks</span></div>
{visual}
<nav class="atlas-nav" aria-label="Sections">
<a href="#atlas-map">The map ↓</a><a href="#party-question">The party question</a>
<a href="#words">What the words mean</a><a href="#method">How we did it</a></nav>
</div><div id="atlas-map"></div>"""
    html = OUT.read_text(encoding="utf-8")
    html = html.replace("<body>", "<body>" + cover, 1)
    OUT.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
