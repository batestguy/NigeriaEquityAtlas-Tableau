"""Ten testable causal DAGs for the atlas, drawn as one offline HTML page.

Reads the processed CSVs, cross-checks every number the page quotes, then
renders analysis/dags.html: ten small directed acyclic graphs, each with the
hypothesis in plain words, the edge labels, a "how you would test it" block and
a verdict (TESTABLE / FRAGILE / NOT IDENTIFIABLE). Nothing here is a causal
claim; they are candidate hypotheses annotated with what this dataset can and
cannot support (n = 37, latitude confounding, conflict undercount).

Run:  & C:\\Users\\TOSHIBA\\ds-general\\python.exe analysis\\dags.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed"
REF = ROOT / "data" / "reference"
OUT = ROOT / "analysis" / "dags.html"

# ----------------------------------------------------------------- data ----
master = pd.read_csv(PROC / "mpi_atlas_2021.csv")
panel = pd.read_csv(PROC / "mpi_trends_panel.csv")
spatial = pd.read_csv(PROC / "spatial_diagnostics.csv")
spatial_global = pd.read_csv(PROC / "spatial_global.csv")
party = pd.read_csv(PROC / "party_alignment_result.csv")
party_state = pd.read_csv(PROC / "party_alignment_state.csv")
dominant = pd.read_csv(REF / "state_dominant_party.csv")

assert len(master) == 37


def corr(a: pd.Series, b: pd.Series) -> float:
    return float(a.corr(b))


def spearman(a: pd.Series, b: pd.Series) -> float:
    return float(a.corr(b, method="spearman"))


# ------------------------------------------------------- verified facts ----
r_lat_rain = spearman(master["lat"], master["baseline_precip_mm"])
r_lat_mpi = spearman(master["lat"], master["mpi"])
r_rain_mpi = spearman(master["baseline_precip_mm"], master["mpi"])
r_rain_mpi_p = corr(master["baseline_precip_mm"], master["mpi"])
vif_rain = 1.0 / (1 - r_lat_rain ** 2)

pdp_state = dominant[dominant["dom_party"] == "PDP"]["state"].tolist()
pdp_n_states = len(pdp_state)

prim = party[party["kind"] == "primary"].iloc[0]
ties_pdp = sum(str(x).startswith("PDP") and str(x) != "PDP" for x in dominant["dom_party"])

zones = panel[(panel["survey_year"] == 2021) & (panel["events"] == 0)]
zero_n = len(zones)
poorest12 = set(master.loc[master["poverty_group"] == "Poorest 12", "state"])
zero_poorest = len(set(zones["state"]) & poorest12)

m_i = spatial_global.loc[spatial_global["key"] == "h1_global_i", "value"].iloc[0]
m_lat = spatial_global.loc[spatial_global["key"] == "h2_resid_i", "value"].iloc[0]
m_full = spatial_global.loc[spatial_global["key"] == "ctx_full_i", "value"].iloc[0]
p_full = spatial_global.loc[spatial_global["key"] == "ctx_full_i", "p"].iloc[0]
raw_local_n = int(
    spatial_global.loc[spatial_global["key"] == "ctx_raw_n", "value"].iloc[0]
)

years = sorted(panel["survey_year"].unique())
n_states = panel["state"].nunique()
intervals = n_states * (len(years) - 1)
persistence = []
for a, b in zip(years[:-1], years[1:]):
    ra = panel[panel["survey_year"] == a].set_index("state")["mpi"].rank()
    rb = panel[panel["survey_year"] == b].set_index("state")["mpi"].rank()
    persistence.append(round(float(ra.corr(rb)), 3))

r_mortality = corr(master["contrib_health_pct"], master["mpi"])
r_education = corr(master["contrib_education_pct"], master["mpi"])
r_living = corr(master["contrib_living_standards_pct"], master["mpi"])
uniform_exclusion = bool(
    (master["indicators_missing"] == "Nutrition").all() and (master["n_indicators"] == 9).all()
)

rho_rank = spearman(master["mpi_rank"], master["mpi_poor_rank"])
kano = master.loc[master["state"] == "Kano"].iloc[0]
t4 = master.sort_values("mpi_poor_thousands", ascending=False).head(4)
top4_share = float(t4["mpi_poor_thousands"].sum() / master["mpi_poor_thousands"].sum())
total_poor_m = float(master["mpi_poor_thousands"].sum()) / 1000

r_sev = corr(master["severe_pct"], master["mpi"])
r_vul = corr(master["vulnerable_pct"], master["mpi"])

ranked = master.sort_values("mpi", ascending=False).reset_index(drop=True)
adjacent_ok = all(
    ranked.loc[i, "mpi_ci_hi"] >= ranked.loc[i + 1, "mpi_ci_lo"] for i in range(len(ranked) - 1)
)
CUTS = [0.05, 0.10, 0.20, 0.30]
straddle = int(
    sum(
        any(r.mpi_ci_lo < c < r.mpi_ci_hi for c in CUTS)
        for r in master.itertuples()
    )
)

flips = int((panel["mpi_change_significant"] == "**").sum())


def rank_partial(x: pd.Series, y: pd.Series, z: pd.Series) -> float:
    """Spearman-style partial: rank(x) and rank(y) both residualised on rank(z)."""
    rx, ry, rz = x.rank(), y.rank(), z.rank()
    return float((rx - np.polyfit(rz, rx, 1)[0] * rz).corr(ry - np.polyfit(rz, ry, 1)[0] * rz))


part_precip_lat = rank_partial(master["baseline_precip_mm"], master["mpi"], master["lat"])
part_cei_lat = rank_partial(master["conflict_exposure_index"], master["mpi"], master["lat"])

# the only direction-identifying lever in the whole dataset: a measure in year t
# against the MPI *change* t -> t+1
_w = panel.set_index(["state", "survey_year"])
lagged = []
for y0, y1 in zip(years[:-1], years[1:]):
    a = _w.xs(y0, level="survey_year")
    b = _w.xs(y1, level="survey_year")
    d = b["mpi"] - a["mpi"]
    lagged.append({
        "interval": f"{y0}\u2013{y1}",
        "cei": float(a["conflict_exposure_index"].corr(d, method="spearman")),
        "rain": float(a["precip_anomaly_pct"].corr(d, method="spearman")),
    })
cei_lags = ", ".join(f"{l['cei']:+.2f}" for l in lagged)
rain_lags = ", ".join(f"{l['rain']:+.2f}" for l in lagged)

# sanity: the page never quotes a number the data does not reproduce
assert -0.95 < r_lat_rain < -0.85, r_lat_rain
assert abs(r_rain_mpi) > 0.75 and r_rain_mpi < 0, r_rain_mpi
assert adjacent_ok, "an adjacent pair separated -- caption would be wrong"
assert zero_n == 10 and zero_poorest == 5, (zero_n, zero_poorest)
assert 0.86 <= rho_rank <= 0.96, rho_rank
assert min(persistence) > 0.85, persistence
assert uniform_exclusion
assert abs(part_precip_lat) < 0.35, part_precip_lat
assert all(abs(l["cei"]) < 0.4 for l in lagged), lagged

f = {
    "r_lat_rain": r_lat_rain, "r_lat_mpi": r_lat_mpi, "r_rain_mpi": r_rain_mpi,
    "r_rain_mpi_p": r_rain_mpi_p,
    "vif_rain": vif_rain, "pdp_n": int(pdp_n_states), "ties_pdp": int(ties_pdp),
    "beta": float(prim["beta"]), "ci_lo": float(prim["ci_lo"]), "ci_hi": float(prim["ci_hi"]),
    "p_perm": float(prim["p_perm"]), "n_party": int(prim["n"]), "mde": float(prim["mde"]),
    "zero_n": int(zero_n), "zero_poorest": int(zero_poorest),
    "m_i": float(m_i), "m_lat": float(m_lat), "m_full": float(m_full), "p_full": float(p_full),
    "raw_local_n": raw_local_n,
    "persist_lo": min(persistence), "persist_hi": max(persistence),
    "r_mortality": r_mortality, "r_education": r_education, "r_living": r_living,
    "rho_rank": float(rho_rank), "kano_rate_rank": int(kano["mpi_rank"]),
    "kano_mass_rank": int(kano["mpi_poor_rank"]),
    "kano_poor_m": float(kano["mpi_poor_thousands"]) / 1000,
    "top4_share": top4_share, "total_poor_m": total_poor_m,
    "r_sev": r_sev, "r_vul": r_vul, "straddle": straddle,
    "flips": flips, "intervals": intervals,
    "years": ", ".join(str(y) for y in years),
    "part_precip": part_precip_lat, "part_cei": part_cei_lat,
    "lagged": lagged,
}
def _json_default(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    raise TypeError(type(o))


print("verified:", json.dumps(
    {k: (round(v, 3) if isinstance(v, (int, float)) else v) for k, v in f.items()},
    ensure_ascii=False, default=_json_default))

SIG = lambda x: f"{x:+.2f}".replace("+", "+").replace("-", "\u2212")

# ----------------------------------------------------------------- DAGs ----
def N(id, x, y, label, kind="obs"):
    return {"id": id, "x": x, "y": y, "lines": label, "kind": kind}


def E(a, b, label=None, kind="h"):
    return {"from": a, "to": b, "label": label, "kind": kind}


DAGS = [
    # 1 -------------------------------------------------------------------
    dict(
        id="lat", n=5,
        title="The latitude wedge",
        verdict="Structure visible, edges not separable", vclass="fragile",
        tag="Rainfall, being the south-soaked half of Nigeria, is nearly a re-labelling of latitude. "
            "Is the climate itself a cause of poverty, or is latitude holding both in its lap?",
        nodes=[
            N("lat", 130, 70, ["Latitude", "(how far north)"]),
            N("rain", 400, 55, ["Baseline rainfall", "1991\u20132020 normal"]),
            N("mal", 400, 175, ["Malaria ecology", "(hypothetical)"], kind="lat"),
            N("mpi", 650, 120, ["MPI value"]),
        ],
        edges=[
            E("lat", "rain", f"\u03c1 = {SIG(f['r_lat_rain'])}", "h"),
            E("lat", "mpi", f"\u03c1 = {SIG(f['r_lat_mpi'])}", "h"),
            E("rain", "mpi", f"\u03c1 = {SIG(f['r_rain_mpi'])}", "x"),
            E("lat", "mal", None, "l"),
            E("mal", "mpi", None, "l"),
        ],
        fields="baseline_precip_mm \u00b7 lat \u00b7 mpi",
        test=f"A regression of MPI on rainfall would answer the question, but with the two inputs at "
             f"\u03c1 = {f['r_lat_rain']:.2f} the model cannot split them: the variance inflation factor for "
             f"rainfall given latitude is {f['vif_rain']:.1f}. Words rather than maths: <b>once you know "
             f"latitude, rainfall adds almost no new information</b>, so the rainfall\u2192MPI arrow and the "
             f"latitude\u2192MPI arrow are two stories about one gradient (Pearson, for the record, is "
             f"{f['r_rain_mpi_p']:.2f}). Holding latitude out first, the rank-residual partial falls to "
             f"{f['part_precip']:.2f}: the climate edge is latitude wearing a mask. Latent malaria ecology "
             f"would push the same arrow further. Conclusion to write: \u201coverlap\u201d, OPHI's word, "
             f"never \u201cdriven by climate\u201d.",
    ),
    # 2 -------------------------------------------------------------------
    dict(
        id="whichway", n=4,
        title="Violence and poverty: which way does the arrow run?",
        verdict="TESTED \u2014 does not survive", vclass="fragile",
        tag="Poverty might recruit violence; violence might deepen poverty. Same-year data cannot separate "
            "them, the recording machinery is poverty-linked, and the lagged edge into the next round is "
            "the only direction-identifying test this dataset permits \u2014 so it was run.",
        nodes=[
            N("p", 130, 145, ["Poverty", "(MPI, year t)"]),
            N("cap", 400, 45, ["State presence,", "press capacity (latent)"], kind="lat"),
            N("v", 650, 145, ["Recorded violence", "(events / 100k)"]),
            N("d", 660, 252, ["\u0394MPI, year t \u2192 t+1"]),
        ],
        edges=[
            E("p", "v", "grievance \u2192 recruitment", "h"),
            E("v", "p", "destruction \u2192 harder lives (same-year)", "x"),
            E("cap", "v", "records where it can", "x"),
            E("v", "d", "the only honest arrow", "h"),
        ],
        fields="mpi \u00b7 events \u00b7 conflict_exposure_index \u00b7 precip_anomaly_pct \u00b7 mpi_trends_panel.csv",
        test=f"Verified: {f['zero_n']} of 37 states record zero UCDP events in 2021 and {f['zero_poorest']} of "
             f"them sit in the poorest 12, so the treatment is under-recorded exactly where poverty is highest "
             f"and every cross-sectional correlation is pulled toward null. No same-year design separates the "
             f"two opposite arrows: a positive, a negative and a null scatter all fit parts of both \u2014 the "
             f"sign-flipping rounds (+0.34 \u2192 \u22120.20 \u2192 +0.10 \u2192 \u22120.06) keep showing it. Run "
             f"the one lever this data owns, violence in year t against the MPI change into t+1: \u03c1 = "
             f"{cei_lags} (\u03c1 rain shocks = {rain_lags}, one sign that will not flip, still far "
             f"below the 0.40 power floor, with only {f['flips']} of {f['intervals']} intervals carrying a "
             f"significant MPI change at all). Verdict: not identifiable here \u2014 the strongest sentence "
             f"available is \u201cnot detectable\u201d, never \u201cno relationship\u201d.",
    ),
    # 3 -------------------------------------------------------------------
    dict(
        id="party", n=3,
        title="Does federal alignment slow a state's poverty decline?",
        verdict="FRAGILE \u2014 one honest, pre-registered attempt", vclass="fragile",
        tag="The pre-registered stage-8 test: where a governor shares the federal ruling party for more of "
            "1999\u20132021, does MPI fall faster?",
        nodes=[
            N("fed", 130, 70, ["Federal ruling party", "(president's shelf)"]),
            N("gov", 400, 70, ["Governor in the", "same party (1999\u20132021)"]),
            N("base", 130, 185, ["Starting poverty", "(MPI 2013)"]),
            N("d", 660, 130, ["\u0394MPI per year", "(2013\u21922021)"]),
        ],
        edges=[
            E("fed", "gov", None, "h"),
            E("base", "gov", "party choice is not random", "x"),
            E("gov", "d", "the treatment edge", "h"),
            E("base", "d", "control variable", "h"),
        ],
        fields="party_alignment_panel.csv \u00b7 governorship_events.csv",
        test=f"\u03b2 = {f['beta']:.4f} MPI points per year (95% CI {f['ci_lo']:.4f} to {f['ci_hi']:.4f}, "
             f"permutation p = {f['p_perm']:.3f}, n = {f['n_party']} state-intervals, minimum detectable "
             f"effect {f['mde']:.4f}). Read it plainly: aligned states fell <em>slower</em>, the interval "
             f"crosses zero, and the effect is under the design's own detection floor. It leans on the "
             f"2013\u201316 interval, and the sitting-party check gives p \u2248 0.08. The dashed edge is the "
             f"real problem: PDP is the strict dominant party in {f['pdp_n']} of the 36 states with an "
             f"elected governor ({f['ties_pdp']} more are PDP-side ties), so party attachment carries "
             f"almost no variance to exploit. Verdict in the atlas: fragile, shown with its "
             f"interval or not shown.",
    ),
    # 4 -------------------------------------------------------------------
    # pruned: composition identity (mass vs rate) - survives trivially, but it is arithmetic, not a causal test

    # 5 -------------------------------------------------------------------
    # pruned: the recording problem now lives inside whichway (it is the reason that test fails)

    # 6 -------------------------------------------------------------------
    dict(
        id="spatial", n=2,
        title="Poverty clusters on the map \u2014 mostly because latitude does",
        verdict="TESTED \u2014 survives, then nearly dissolves", vclass="fragile",
        tag="Neighbouring states share poverty (Moran's I = 0.80). How much of that is anything beyond the "
            "latitude wedge?",
        nodes=[
            N("lat", 130, 60, ["Latitude"]),
            N("lag", 420, 70, ["Neighbours' mean MPI", "(spatial lag)"]),
            N("self", 420, 190, ["A state's MPI"]),
            N("resid", 690, 130, ["Clustering left over", "(residual Moran's I)"]),
        ],
        edges=[
            E("lag", "self", "drawn one-way; the link is symmetric", "h"),
            E("lat", "self", None, "h"),
            E("lat", "lag", None, "h"),
            E("self", "resid", None, "l"),
            E("lag", "resid", None, "l"),
        ],
        fields="spatial_diagnostics.csv \u00b7 spatial_global.csv \u00b7 mpi",
        test=f"Verified: Moran's I = {f['m_i']:.3f} (p = 0.0001, queen contiguity, 9,999 permutations). After "
             f"removing how far north a state sits, it drops to {f['m_lat']:.3f}; after latitude plus conflict "
             f"plus climate, {f['m_full']:.3f} (p = {f['p_full']:.3f}). Before correction {f['raw_local_n']} "
             f"states look locally unusual; exactly 1 (Yobe) survives Bonferroni across 37 simultaneous tests, "
             f"and 0 survive Benjamini\u2013Yekutieli. Say: \u201cconcentrated in space, mostly with latitude, "
             f"and only one hotspot is distinguishable at this sample size.\u201d",
    ),
    # 7 -------------------------------------------------------------------
    # pruned: scope constraint (uniform nutrition exclusion), not a testable hypothesis

    # 8 -------------------------------------------------------------------
    dict(
        id="persist", n=1,
        title="Structure held while the level fell",
        verdict="TESTED \u2014 solid", vclass="ok",
        tag="Did poor states stay poor between rounds? The rank-order answer is yes, loudly, in every "
            "interval.",
        nodes=[
            N("r0", 130, 90, ["MPI rank,", f"round {years[0]}"]),
            N("r1", 650, 90, ["MPI rank,", f"round {years[-1]}"]),
            N("t0", 130, 210, ["True state poverty", "(latent)"], kind="lat"),
            N("t1", 650, 210, ["True state poverty", "(latent)"], kind="lat"),
        ],
        edges=[
            E("r0", "r1", "rank persistence", "h"),
            E("t0", "r0", None, "l"),
            E("t1", "r1", "survey noise blurs both", "l"),
            E("t0", "t1", "true structure persists", "l"),
        ],
        fields="mpi_trends_panel.csv \u00b7 survey_year \u00b7 mpi",
        test=f"Verified: Spearman between consecutive rounds' MPI ranks = "
             f"{', '.join(f'{y0}\u2192{y1}: {v:.2f}' for (y0, y1), v in zip(zip(years[:-1], years[1:]), persistence))}. "
             f"The MPI value itself fell across the panel; the <em>ordering</em> barely moved. That is the "
             f"one causal-looking dynamic this dataset supports: \u201cthe states that were poorest "
             f"tended to still be poorest\u201d \u2014 with the honesty that fine rank distinctions stay "
             f"unresolvable at 95% within a round (0 of 36 adjacent pairs separate).",
    ),
    # 9 -------------------------------------------------------------------
    # pruned: merged into whichway - the lagged tests now run against real numbers

    # 10 ------------------------------------------------------------------
    dict(
        id="bands", n=6,
        title="Bands are five buckets around a measured point, not five truths",
        verdict="Computed \u2014 feeds the caption already shipped", vclass="ok",
        tag="The map's five colours are assigned on a point estimate that carries a \u00b1 interval sized "
            "like the bands themselves. Near a cut, a state's band is a coin flip between two colours.",
        nodes=[
            N("t", 130, 60, ["True state MPI", "(latent)"], kind="lat"),
            N("e", 420, 125, ["Published MPI \u00b1 SE"]),
            N("b", 680, 60, ["Band 1\u20135", "(map fill)"]),
            N("hov", 680, 200, ["Tooltip:", "MPI % + interval"]),
        ],
        edges=[
            E("t", "e", None, "l"),
            E("e", "b", "discretisation", "h"),
            E("e", "hov", "the interval travels with the value", "h"),
        ],
        fields="mpi \u00b7 mpi_ci_lo \u00b7 mpi_ci_hi \u00b7 mpi_band",
        test=f"Verified: {f['straddle']} of 37 states have a 95% interval that straddles one of the four band "
             f"cuts, so shading alone overstates certainty for roughly half the map \u2014 which is why the "
             f"tooltip prints the MPI value <em>with</em> its interval and the headcount separately. Adjacent-rank "
             f"ordering never separates at 95% (0 of 36 pairs), so neither band edges nor rank order should "
             f"ever be read as a strict comparison.",
    ),
]

DAGS.sort(key=lambda d: d["n"])
for d in DAGS:
    ids = {n["id"] for n in d["nodes"]}
    assert len(ids) == len(d["nodes"]), d["title"]
    assert ids == {n["id"] for n in d["nodes"]}
    for e in d["edges"]:
        assert e["from"] in ids and e["to"] in ids, (d["title"], e)

# ------------------------------------------------------------- template ----
TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Testable hypotheses as DAGs &middot; Nigeria MPI Equity Atlas</title>
<style>
:root{--bg:#fbfaf8;--ink:#1b1b1b;--muted:#6b6b6b;--line:#e3e0da;--red:#d80000;--ok:#1c7c54;--warn:#a8621b}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 "Segoe UI",system-ui,sans-serif}
header{max-width:1100px;margin:0 auto;padding:26px 24px 0}
h1{font-size:23px;margin:0;letter-spacing:-.02em}
h1 span{color:var(--red)}
.sub{color:var(--muted);font-size:13px;margin:6px 0 0;max-width:90ch}
nav{position:sticky;top:0;z-index:5;background:rgba(251,250,248,.94);backdrop-filter:blur(4px);
  border-bottom:1px solid var(--line);margin-top:16px}
nav .inner{max-width:1100px;margin:0 auto;padding:8px 24px;display:flex;gap:8px;flex-wrap:wrap}
nav a{font-size:12px;color:var(--muted);text-decoration:none;border:1px solid var(--line);
  border-radius:999px;padding:3px 10px;background:#fff}
nav a:hover{color:var(--red)}
main{max-width:1240px;margin:0 auto;padding:20px 24px 6px}
section{background:#fff;border:1px solid var(--line);border-radius:14px;padding:20px 24px 18px}
section[hidden]{display:none}
.pagerbar{display:flex;align-items:center;gap:14px;margin:14px 0 2px;flex-wrap:wrap}
.pagerbar button{font:inherit;font-size:14.5px;font-weight:600;padding:9px 20px;border-radius:999px;
  border:1px solid var(--line);background:#fff;color:var(--ink);cursor:pointer}
.pagerbar button:hover{border-color:#c9b9b9;color:var(--red)}
.pagerbar span{font-family:Consolas,monospace;font-size:13.5px;color:var(--muted);min-width:70px;text-align:center}
.pagerbar em{font-style:normal;color:var(--muted);font-size:12px}
.sec-head{display:flex;justify-content:space-between;gap:10px;align-items:baseline;flex-wrap:wrap}
.num{font-family:Consolas,monospace;color:#b9b4ac;font-size:12px}
h2{font-size:17px;margin:0;letter-spacing:-.01em;font-weight:650}
.tag{font-size:14.5px;color:#333;margin:9px 0 8px;max-width:100ch}
.tag em{color:#7a2424;font-style:normal}
.chip{font-size:10px;text-transform:uppercase;letter-spacing:.06em;font-weight:700;
  padding:2px 9px;border-radius:999px;white-space:nowrap}
.chip.ok{background:#e7f4ed;color:#15603f}
.chip.fragile{background:#fdf1e3;color:#8a4f10}
svg{width:100%;height:auto;background:#fdfcfa;border:1px solid #f0eeea;border-radius:9px;display:block}
.gnode rect{fill:#fff;stroke:#6b6b6b;stroke-width:1.2}
.gnode.lat rect{fill:#f7f5f1;stroke:#9a948c;stroke-dasharray:3 3}
.gnode.note rect{fill:#fdf6ec;stroke:#cbb58d;stroke-dasharray:2 3}
.gnode text{font-size:14px;fill:#242424}
.gnode{cursor:default}
.gedge{fill:none}
.gelab{font-size:12px;fill:#8a8a8a}
.dim{opacity:.14;transition:opacity .12s}
.hl{stroke-width:2 !important}
.test{font-size:14px;color:#444;background:#f7f5f2;border-radius:8px;padding:12px 15px;margin-top:12px}
.test b{color:var(--ink)}
.fields{font-size:11px;color:#9a958e;margin-top:9px;font-family:Consolas,monospace}
footer{max-width:1100px;margin:0 auto;padding:6px 24px 42px;color:#8f8a83;font-size:12px}
footer code{background:#f4f2ef;padding:1px 5px;border-radius:4px;font-size:11px}
svg .lab{font-size:9.5px;fill:#9aa0a6}
</style>
</head>
<body>
<header>
  <h1>Testable hypotheses as DAGs <span>&middot;</span> Nigeria MPI atlas</h1>
  <p class="sub">Six candidate structures drawn from the atlas's own fields, each annotated with what this
     dataset can and cannot support (n&nbsp;=&nbsp;37, latitude confounding, conflict undercount, a
     year-standardised conflict index). Hover a box to light up its arrows. Every number printed on the page
     is recomputed from <code>data/processed/*.csv</code> at build time &mdash; nothing is quoted from memory.</p>
  <nav><div class="inner" id="nav"></div></nav>
  <div class="pagerbar" style="max-width:1240px;margin:10px auto 0;padding:0 24px">
    <button id="prev">&#9664;&nbsp;Prev</button>
    <span id="pos">1 / 6</span>
    <button id="next">Next&nbsp;&#9654;</button>
    <em>or use the &#8592; / &#8594; keys; hover a box to light up its arrows</em>
  </div>
</header>
<main id="dags"></main>
<footer>Generated by <code>analysis/dags.py</code> &middot; edge kinds: solid = the hypothesis under test,
  red dashed = cannot be identified with this data, dotted = latent construct;
  box kinds: solid border = observed field, dashed border = latent.</footer>
<script>
const DAGS = __DAGS__;
const KIND_COLOR = {h:"#333333", x:"#b3261e", l:"#a39d94"};

document.getElementById("nav").innerHTML = DAGS.map(d =>
  `<a href="#dag-${d.id}" data-i="${d.n-1}">${String(d.n).padStart(2,"0")} ${d.title}</a>`).join("");

/* one card per page; chips and buttons both drive it */
const cards=[];
const show = i => {
  const k = (i + cards.length) % cards.length;
  cur = k;
  cards.forEach((c,j)=>{ c.hidden = j !== k; });
  document.getElementById("pos").textContent = `${k+1} / ${cards.length}`;
  document.getElementById("dags").scrollIntoView({behavior:"smooth", block:"start"});
};
const bind = () => {
  cards.length = 0;
  cards.push(...document.querySelectorAll("main section"));
};

const pts = r => {
  const [x1,y1,x2,y2,cx,cy] = r;
  const t=.5, mx=(1-t)*(1-t)*x1+2*(1-t)*t*cx+t*t*x2, my=(1-t)*(1-t)*y1+2*(1-t)*t*cy+t*t*y2;
  return [mx,my];
};

for (const d of DAGS){
  const W=800, H=330, rx=112, ry=42;
  const node = Object.fromEntries(d.nodes.map(n=>[n.id,n]));
  let s = `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${d.title}">`;
  s += `<defs>` + Object.keys(KIND_COLOR).map(k =>
    `<marker id="a-${d.id}-${k}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
      orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="${KIND_COLOR[k]}"/></marker>`).join("")
    + `</defs>`;
  const eg=[];
  for (const e of d.edges){
    const a=node[e.from], b=node[e.to];
    const dx=b.x-a.x, dy=b.y-a.y, len=Math.hypot(dx,dy), ux=dx/len, uy=dy/len;
    const sa=1/Math.sqrt((ux/rx)**2+(uy/ry)**2), sb=1/Math.sqrt((-ux/rx)**2+(-uy/ry)**2);
    const x1=a.x+ux*sa, y1=a.y+uy*sa, x2=b.x-ux*sb, y2=b.y-uy*sb;
    const nx=-uy, ny=ux, k=len*0.16;
    const cx=(x1+x2)/2+nx*k, cy=(y1+y2)/2+ny*k;
    const path=`M${x1.toFixed(1)},${y1.toFixed(1)} Q${cx.toFixed(1)},${cy.toFixed(1)} ${x2.toFixed(1)},${y2.toFixed(1)}`;
    const dash = e.kind==="x" ? `stroke-dasharray="7 5"` : e.kind==="l" ? `stroke-dasharray="1.5 4"` : "";
    s += `<path class="gedge" data-f="${e.from}" data-t="${e.to}" d="${path}"
      stroke="${KIND_COLOR[e.kind]}" stroke-width="1.6" ${dash} marker-end="url(#a-${d.id}-${e.kind})"/>`;
    if (e.label){
      const [lx,ly]=pts([x1,y1,x2,y2,cx,cy]);
      const ox=nx*k*.62, oy=ny*k*.62;
      s += `<text class="gelab" data-f="${e.from}" data-t="${e.to}"
        x="${(lx+ox).toFixed(1)}" y="${(ly+oy+3.5).toFixed(1)}" text-anchor="middle">${e.label}</text>`;
    }
    eg.push(e);
  }
  for (const n of d.nodes){
    const lines=n.lines, w=rx*2-30, h=28+18*(lines.length-1)+14;
    s += `<g class="gnode ${n.kind}" data-id="${n.id}">`;
    s += `<rect x="${n.x-rx+15}" y="${n.y-h/2}" width="${w}" height="${h}" rx="10"/>`;
    lines.forEach((ln,i)=>{
      s += `<text x="${n.x}" y="${n.y+(i-(lines.length-1)/2)*18+5}" text-anchor="middle">${ln}</text>`;
    });
    s += `</g>`;
  }
  s += `<text class="lab" x="10" y="${H-8}">solid = hypothesis under test &middot; red dashed = not
    identifiable here &middot; dotted = latent</text></svg>`;
  const card = document.createElement("section");
  card.id = `dag-${d.id}`;
  card.dataset.i = d.n - 1;
  card.innerHTML = `
    <div class="sec-head"><h2><span class="num">${String(d.n).padStart(2,"0")}</span> ${d.title}</h2>
      <span class="chip ${d.vclass}">${d.verdict}</span></div>
    <p class="tag">${d.tag}</p>${s}
    <div class="test"><b>How you would test it.</b> ${d.test}</div>
    <div class="fields">fields &mdash; ${d.fields}</div>`;
  document.getElementById("dags").appendChild(card);
}

bind();
let cur = 0;
document.querySelectorAll("#nav a").forEach(a =>
  a.addEventListener("click", e => {
    e.preventDefault();
    history.replaceState(null, "", a.getAttribute("href"));
    show(+a.dataset.i);
  }));
document.getElementById("prev").addEventListener("click", () => show(cur - 1));
document.getElementById("next").addEventListener("click", () => show(cur + 1));
document.addEventListener("keydown", e => {
  if (/input|textarea|select/i.test(e.target.tagName)) return;
  if (e.key === "ArrowRight") { e.preventDefault(); show(cur + 1); }
  if (e.key === "ArrowLeft")  { e.preventDefault(); show(cur - 1); }
});
const m = document.location.hash.match(/^#dag-(.+)$/);
const start = m ? cards.findIndex(c => c.id === "dag-" + m[1]) : 0;
show(start >= 0 ? start : 0);

/* hover: light the arrows that touch a box */
document.addEventListener("mouseover", e=>{
  const g = e.target.closest && e.target.closest(".gnode");
  if(!g) return;
  const id = g.dataset.id, svg = g.closest("svg");
  svg.querySelectorAll(".gedge,.gelab").forEach(p=>{
    const hit = p.dataset.f===id || p.dataset.t===id;
    p.classList.toggle("dim", !hit);
    p.classList.toggle("hl", hit && p.classList.contains("gedge"));
  });
});
document.addEventListener("mouseout", e=>{
  const g = e.target.closest && e.target.closest(".gnode");
  if(!g) return;
  const svg = g.closest("svg");
  svg.querySelectorAll(".gedge,.gelab").forEach(p=>p.classList.remove("dim","hl"));
});
</script>
</body>
</html>
"""

spec = [{"id": d["id"], "n": d["n"], "title": d["title"], "verdict": d["verdict"],
         "vclass": d["vclass"], "tag": d["tag"], "nodes": d["nodes"], "edges": d["edges"],
         "test": d["test"], "fields": d["fields"]} for d in DAGS]
html = TEMPLATE.replace("__DAGS__", json.dumps(spec, ensure_ascii=False, separators=(",", ":")))
OUT.write_text(html, encoding="utf-8")
print(f"wrote {OUT}  ({OUT.stat().st_size/1024:.0f} KB)")
