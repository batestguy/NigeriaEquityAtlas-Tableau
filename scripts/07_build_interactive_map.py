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
            return "Dominant party 1999–2021: none (no elected governor)"
        yrs = years_of[pcode].replace(",", ", ")
        if "|" in years_of[pcode]:
            segs = " · ".join(
                f"{p} ({y.replace(',', ', ')})"
                for p, y in (s.split(":") for s in years_of[pcode].split("|"))
            )
            return f"Dominant 1999–2021 (tie): {segs}"
        return f"Dominant 1999–2021: {party} ({yrs})"

    def party_years_line(pcode: str) -> str:
        # Two lines of context: the mode party (§1 of docs/party_alignment.md keeps
        # it as hover context) and the 1999-2021 alignment tally, labelled so it is
        # not mistaken for the 2013-21 test window.
        if party_of[pcode] == "—":
            return dominant_line(pcode)
        return (
            f"{dominant_line(pcode)}<br><i>Whole period 1999–2021: aligned with the federal "
            f"ruling party {aligned_of[pcode]} of {span_years} yrs (not the 2013–21 test)</i>"
        )

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
            f"MPI {float(r['mpi']):.3f} (95% CI {float(r['mpi_ci_lo']):.3f}–{float(r['mpi_ci_hi']):.3f})<br>"
            f"{h:.1f}% of people are poor (≈1 in {round(100 / h)}); "
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
            "Hover any state for MPI + 95% CI.</sup>"
        ),
        mapbox=dict(
            # Blank base: no tile server, no API key, works fully offline.
            # (carto-positron now watermarks without a key.)
            style="white-bg",
            center=dict(lat=9.2, lon=8.5),
            zoom=4.8,
        ),
        margin=dict(l=10, r=10, t=200, b=80),
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
                    "Party = dominant governorship party and years aligned with the federal "
                    "ruling party, 1999–2021 (hover); context only, never colour."
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
                y=1.12,
                xanchor="left",
                yanchor="top",
                showactive=True,
                buttons=[
                    dict(label="All 37", method="update",
                         args=[{"visible": [True, True]},
                               {"mapbox.center.lat": 9.2, "mapbox.center.lon": 8.5,
                                "mapbox.zoom": 4.8}]),
                    dict(label="Poorest 12", method="update",
                         args=[{"visible": [True, False]},
                               {"mapbox.center.lat": 11.0, "mapbox.center.lon": 9.3,
                                "mapbox.zoom": 5.2}]),
                    dict(label="Other 25", method="update",
                         args=[{"visible": [False, True]},
                               {"mapbox.center.lat": 7.4, "mapbox.center.lon": 7.0,
                                "mapbox.zoom": 5.0}]),
                ],
            )
        ],
    )

    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(OUT), include_plotlyjs=True, full_html=True)
    _add_cover()
    _add_result_panel()
    print(f"wrote {OUT.relative_to(Path.cwd())} ({OUT.stat().st_size/1024:.0f} KB)")
    print("bands: " + ", ".join(f"{b}={sum(1 for v in band_of.values() if v==b)}" for b in BAND_ORDER))
    print(f"toggle: Poorest 12 = {len(poorest)}, Other 25 = {len(rest)}")
    return 0


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
    panel = f"""<div style="font-family:-apple-system,'Segoe UI',Arial,sans-serif;max-width:860px;
margin:8px auto 40px;padding:18px 22px;border:1px solid #d9d9d9;border-radius:10px;color:#22252a;">
<p style="margin:0 0 6px;font-size:12px;letter-spacing:2px;color:#555;font-weight:700;">
PRE-REGISTERED TEST · FEDERAL ALIGNMENT AND MPI CHANGE, 2013–2021</p>
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
Carlo estimate (about ±0.005). Method: docs/party_alignment.md.</p>
</div>"""
    page = OUT.read_text(encoding="utf-8")
    assert page.count("</body>") == 1
    OUT.write_text(page.replace("</body>", panel + "</body>"), encoding="utf-8")


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
.atlas-scroll{{margin-top:38px;color:{GREEN};font-weight:700;font-size:15px;}}
</style>
<div class="atlas-cover">
<div class="atlas-watermark"></div>
<div class="atlas-flagbar"></div>
<p class="atlas-eyebrow">🇳🇬 NIGERIA · MULTIDIMENSIONAL POVERTY EQUITY ATLAS · MICS 2021</p>
<h1>One country, two realities.</h1>
<p class="atlas-sub">Poverty fell, but its shape held: the poorest states are held
back by schooling and living standards far more than the rest. Hover, filter and compare.</p>
<div class="atlas-chips"><span>National MPI 0.175</span><span>37 states + FCT</span>
<span>4 survey rounds</span><span>Read bands, not ranks</span></div>
{visual}
<p class="atlas-scroll">Scroll to explore the map ↓</p>
</div>"""
    html = OUT.read_text(encoding="utf-8")
    html = html.replace("<body>", "<body>" + cover, 1)
    OUT.write_text(html, encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
