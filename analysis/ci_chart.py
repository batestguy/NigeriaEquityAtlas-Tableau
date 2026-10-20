"""Quick mock of the Tableau dual-axis view: circle (MPI) + Gantt bar (95% CI).

Builds analysis/ci_chart.html -- a standalone SVG page with one row per state:
a dot at the MPI value and a whisker from mpi_ci_lo to mpi_ci_hi, which is what
Tableau draws as a Gantt bar (start = ci_lo, Size = hi - lo) on a synchronised
second axis.

Run:  & C:\\Users\\TOSHIBA\\ds-general\\python.exe analysis\\ci_chart.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis" / "ci_chart.html"

BANDS = [
    ("1. under 5%", "#ffe5e5"),
    ("2. 5% to 10%", "#ffb8b8"),
    ("3. 10% to 20%", "#ff8a8a"),
    ("4. 20% to 30%", "#f45555"),
    ("5. 30% and above", "#d80000"),
]
BAND_COLOR = dict(BANDS)

df = pd.read_csv(ROOT / "data" / "processed" / "mpi_atlas_2021.csv")
assert len(df) == 37
df = df.sort_values("mpi", ascending=False).reset_index(drop=True)
# every adjacent pair's CI must overlap for the caption to say so
overlaps = all(
    df.loc[i, "mpi_ci_hi"] >= df.loc[i + 1, "mpi_ci_lo"]
    for i in range(len(df) - 1)
)
assert overlaps, "an adjacent pair separated -- the caption would be wrong"

rows = [
    {
        "state": r.state,
        "band": r.mpi_band,
        "mpi": round(r.mpi, 4),
        "lo": round(r.mpi_ci_lo, 4),
        "hi": round(r.mpi_ci_hi, 4),
        "h": round(r.headcount_ratio_pct, 2),
        "group": r.poverty_group,
    }
    for r in df.itertuples()
]

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>The honest ranking - MPI dot + 95% interval</title>
<style>
body{margin:0;background:#fbfaf8;color:#1b1b1b;font:14px/1.5 "Segoe UI",system-ui,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:26px 20px 50px}
h1{font-size:21px;margin:0;letter-spacing:-.02em}
h1 span{color:#d80000}
.sub{color:#6b6b6b;font-size:13px;margin:6px 0 18px;max-width:80ch}
svg{display:block;background:#fff;border:1px solid #e3e0da;border-radius:10px}
text{font-family:inherit}
.legend{display:flex;gap:14px;flex-wrap:wrap;font-size:12px;color:#6b6b6b;margin:12px 0}
.legend i{width:11px;height:11px;border-radius:3px;display:inline-block;margin-right:4px;vertical-align:-1px}
.recipe{margin-top:18px;background:#fff;border:1px solid #e3e0da;border-radius:10px;padding:14px 16px;
  font-size:12.5px;color:#444}
.recipe b{color:#1b1b1b}
.recipe code{font-family:Consolas,monospace;font-size:11.5px;background:#f4f2ef;padding:1px 5px;border-radius:4px}
#tip{position:fixed;pointer-events:none;background:#161616;color:#fff;font-size:12px;padding:7px 10px;
  border-radius:6px;opacity:0;transition:opacity .1s;z-index:9;line-height:1.5;white-space:nowrap}
</style>
</head>
<body>
<div class="wrap">
  <h1>The honest ranking <span>&middot;</span> MPI with its 95% interval</h1>
  <p class="sub">Each row is a state. The dot is the MPI value; the whisker is OPHI's published 95% interval.
     In Tableau this is <b>two marks on one dual axis</b>: a Circle at <code>mpi</code> and a Gantt bar that
     starts at <code>mpi_ci_lo</code> with <code>Size = mpi_ci_hi - mpi_ci_lo</code>. Every adjacent pair
     overlaps, so there is no defensible "first" or "second" -- only bands.</p>
  <svg id="chart" role="img" aria-label="MPI dot plot with 95% intervals for 37 states"></svg>
  <div class="legend" id="legend"></div>
  <div class="recipe">
    <b>Tableau recipe.</b> Rows: <code>state</code>. Columns: <code>mpi_ci_lo</code> (Gantt bar; Size =
    calculated field <code>mpi_ci_hi - mpi_ci_lo</code>; hide its axis heading) and <code>mpi</code>
    (Circle) &rarr; right-click the second MPI pill &rarr; <i>Dual Axis</i>, then right-click the
    axis itself &rarr; <i>Synchronize Axis</i> (Tableau adds a warning triangle until you do). Sort
    <code>state</code> by MPI descending, hide axis headings, colour the circle by
    <code>mpi_band</code> with the atlas ramp, whisker in light grey.
  </div>
</div>
<div id="tip"></div>
<script>
const ROWS = __ROWS__;
const BANDS = __BANDS__;
const BAND_COLOR = {}; BANDS.forEach(([k,c])=>BAND_COLOR[k]=c);
const pct = v => (v*100).toLocaleString("en-US",{minimumFractionDigits:2,maximumFractionDigits:2}) + "%";

const W=820, rowH=30, topPad=40, botPad=60;
const H = topPad + rowH*ROWS.length + botPad;
const lo = Math.min(...ROWS.map(r=>r.lo)), hi = Math.max(...ROWS.map(r=>r.hi));
const pad = (hi-lo)*0.03;
const x0 = 0, x1 = Math.ceil((hi+pad)*10)/10;
const sx = v => 170 + (v-x0)/(x1-x0) * (W-190);

let s = `<g>`;
for (let t=Math.ceil(x0*100)/100; t<=x1+1e-9; t=t+0.05){
  const xx=sx(t);
  s += `<line x1="${xx}" y1="${topPad-8}" x2="${xx}" y2="${H-botPad+8}" stroke="#eef0f2"/>`;
  s += `<text x="${xx}" y="${H-34}" font-size="10.5" fill="#9aa0a6" text-anchor="middle">${pct(t)}</text>`;
}
ROWS.forEach((r,i)=>{
  const y = topPad + i*rowH + rowH/2;
  s += `<text x="160" y="${y+4}" font-size="12.5" fill="#333" text-anchor="end">${r.state}</text>`;
  s += `<line x1="${sx(r.lo)}" y1="${y}" x2="${sx(r.hi)}" y2="${y}" stroke="#dcd8d2" stroke-width="7"
          stroke-linecap="round" class="wh"/>`;
  s += `<circle cx="${sx(r.mpi)}" cy="${y}" r="5.6" fill="${BAND_COLOR[r.band]}" fill-opacity=".9"
          stroke="#fff" stroke-width="1" class="pt" data-i="${i}"/>`;
  if (i>0){
    const p = ROWS[i-1];
    const ov = r.hi >= p.lo;   // adjacent overlap marker
    if (!ov) s += `<text x="${W-14}" y="${y-8}" font-size="10" fill="#a80000" text-anchor="end">separates</text>`;
  }
});
s += `<text x="170" y="${H-10}" font-size="10.5" fill="#9aa0a6">MPI value as % of the index (95% interval)</text>`;
s += `<text x="${sx(x0)+2}" y="${topPad-14}" font-size="10.5" fill="#9aa0a6">0.0%</text>`;
s += `<text x="${sx(x1)-2}" y="${topPad-14}" font-size="10.5" fill="#9aa0a6" text-anchor="end">${pct(x1)}</text>`;
document.getElementById("chart").innerHTML = s;
document.getElementById("chart").setAttribute("viewBox",`0 0 ${W} ${H}`);
document.getElementById("chart").setAttribute("height", H);
BANDS.forEach(([k,c]) => document.getElementById("legend").insertAdjacentHTML("beforeend",
  `<span><i style="background:${c}"></i>${k}</span>`));

const tip = document.getElementById("tip");
document.addEventListener("mousemove", e=>{
  const d = e.target.closest && e.target.closest(".pt");
  if (!d){ tip.style.opacity=0; return; }
  const r = ROWS[+d.dataset.i];
  tip.innerHTML = `<b>${r.state}</b> &middot; ${r.group}<br>MPI ${pct(r.mpi)}
    &nbsp;(95% interval ${pct(r.lo)} to ${pct(r.hi)})<br>Headcount ratio ${r.h}% of the population`;
  tip.style.left = (e.clientX+14)+"px";
  tip.style.top = (e.clientY-12)+"px";
  tip.style.opacity = 1;
});
</script>
</body>
</html>
"""

html = (
    TEMPLATE.replace("__ROWS__", json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
    .replace("__BANDS__", json.dumps(BANDS))
)
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
print("adjacent pairs overlap at 95%:", overlaps)
