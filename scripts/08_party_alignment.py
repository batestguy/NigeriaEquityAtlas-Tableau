"""Stage 8 -- the pre-registered federal-alignment test (docs/party_alignment.md §2).

Question: over the years between survey rounds, did MPI fall faster in states whose
governor belonged to the federal ruling party? This script implements §2 of the
spec exactly and writes §4 from the §3 sentence templates. It composes no prose of
its own beyond the numbers.

Reads:
  data/reference/governorship_events.csv  as-won party per seating event (gated in stage 0)
  data/reference/federal_party.csv        PDP from 1999-05-29, APC from 2015-05-29
  data/processed/mpi_trends_panel.csv     harmonised MPI, 37 states x 4 rounds
  data/processed/mpi_atlas_2021.csv       poverty_group (robustness check b)
  data/reference/governor_defections.csv  sourced sitting-party changes (robustness check d)

Produces:
  data/processed/party_alignment_panel.csv   108 rows: 36 states x 3 intervals
  data/processed/party_alignment_state.csv   37 rows: aligned years 1999-2021 (map hover)
  data/processed/party_alignment_result.csv  primary, robustness (a)-(d), leave-one-interval-out
                                             and per-interval rows, MDE, §4 sentence
  docs/party_alignment.md                    §4 only (text under "## 4. Result")

FCT is excluded from the test (no elected governor) and is listed as excluded.

Robustness row (d) and the interval-dependence rows were added on 2026-10-09 AFTER
the primary result was known: (d) under the §2 limitation clause (defections only
with sourced dates, only as an extra robustness row), the interval rows as factual
context. Neither changes the primary model or the §3 sentence it selects.
"""

from __future__ import annotations

import csv
import sys
from datetime import date, datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import numpy as np

from common import (
    DOCS,
    PROCESSED,
    REFERENCE,
    alignment_context_line,
    read_lookup,
    write_csv,
)

SEED = 20261009
N_PERM = 10_000
N_BOOT = 5_000
MDE_DATASETS = 500
MDE_PERMS = 1_000
MDE_STEP = 0.0005
MDE_MAX = 0.05
ALPHA = 0.05

FCT = "NG-FC"
INTERVALS = ((2013, 2016), (2016, 2018), (2018, 2021))
ROUND_SURVEY = {2013: "DHS", 2016: "MICS", 2018: "DHS", 2021: "MICS"}
MPI_SERIES = "OPHI harmonised (Data Table 6, MN 63)"
SPAN_FIRST, SPAN_LAST = 1999, 2021
# A change of governing party within a year is placed in late May: 5/12 of the year
# goes to the outgoing party and 7/12 to the incoming one (spec §2, year weighting).
W_OUT, W_IN = 5 / 12, 7 / 12
# The same rule at monthly resolution: a seating takes effect after month 5 (May).
SEAT_MONTH = 5
N_SEED_CHECK = 10
INTERVAL_LABEL = {(2013, 2016): "2013–16", (2016, 2018): "2016–18", (2018, 2021): "2018–21"}

EVENTS = REFERENCE / "governorship_events.csv"
FEDERAL = REFERENCE / "federal_party.csv"
DEFECTIONS = REFERENCE / "governor_defections.csv"
PANEL_IN = PROCESSED / "mpi_trends_panel.csv"
ATLAS = PROCESSED / "mpi_atlas_2021.csv"
PANEL_OUT = PROCESSED / "party_alignment_panel.csv"
STATE_OUT = PROCESSED / "party_alignment_state.csv"
RESULT_OUT = PROCESSED / "party_alignment_result.csv"
SPEC = DOCS / "party_alignment.md"


def read(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- exposure


def party_by_year(seatings: list[tuple[int, str]]) -> dict[int, tuple[str | None, str | None]]:
    """(party in force at the start of each year, party in force at its end).

    ``seatings`` is (seated_year, party) in file order; a later seating in the same
    year supersedes an earlier one, so the end-of-year party is the last seated.
    """
    out: dict[int, tuple[str | None, str | None]] = {}
    current: str | None = None
    for year in range(SPAN_FIRST, SPAN_LAST + 1):
        start = current
        for seated, party in seatings:
            if seated == year:
                current = party
        out[year] = (start, current)
    return out


def year_weights(
    gov: dict[int, tuple[str | None, str | None]],
    fed: dict[int, tuple[str | None, str | None]],
) -> dict[int, float]:
    """Weighted aligned fraction of each calendar year.

    5/12 x [outgoing governor party == outgoing federal party] +
    7/12 x [incoming governor party == incoming federal party]. With no change in
    either series this is simply 0 or 1, so the split only matters in a changeover
    year (a seating that changes party, or the 2015 federal handover).
    """
    w: dict[int, float] = {}
    for year, (g0, g1) in gov.items():
        f0, f1 = fed[year]
        w[year] = W_OUT * (g0 is not None and g0 == f0) + W_IN * (g1 is not None and g1 == f1)
    return w


def monthly_weights(
    seatings: list[tuple[int, str]],
    changes: list[tuple[int, int, str, str]],
    fed_seatings: list[tuple[int, str]],
) -> dict[int, float]:
    """Aligned fraction of each year at monthly resolution, with sitting-party changes.

    Robustness check (d). Seatings and the federal handover take effect after month 5,
    which is the 5/12-7/12 rule expressed in months; a sitting-party change dated in
    month m (``changes`` = (year, month, from_party, to_party)) takes effect after
    month m. With no changes this reproduces ``year_weights`` exactly, which main()
    asserts for every state.
    """
    timeline: list[tuple[int, int, int, str, str | None, str]] = []
    for i, (year, party) in enumerate(seatings):
        timeline.append((year, SEAT_MONTH, i, "gov", None, party))
    for j, (year, month, frm, to) in enumerate(changes):
        timeline.append((year, month, len(seatings) + j, "gov", frm, to))
    for j, (year, party) in enumerate(fed_seatings):
        timeline.append((year, SEAT_MONTH, -1 - j, "fed", None, party))
    timeline.sort(key=lambda e: (e[0], e[1], e[2]))

    gov: str | None = None
    fed: str | None = None
    pos = 0
    out: dict[int, float] = {}
    for year in range(SPAN_FIRST, SPAN_LAST + 1):
        aligned = 0
        for month in range(1, 13):
            # Apply every event dated strictly before this month.
            while pos < len(timeline) and (timeline[pos][0], timeline[pos][1]) < (year, month):
                _, _, _, who, frm, to = timeline[pos]
                if who == "fed":
                    fed = to
                else:
                    assert frm is None or gov in (frm, to), (
                        f"defection {frm}->{to} in {timeline[pos][0]} does not match sitting party {gov}"
                    )
                    gov = to
                pos += 1
            aligned += gov is not None and gov == fed
        out[year] = aligned / 12
    return out


# --------------------------------------------------------------------------- estimation


def ols_beta(y: np.ndarray, x: np.ndarray, z: np.ndarray) -> float:
    """Coefficient on ``x`` in y ~ x + z (z already holds the intercept)."""
    design = np.column_stack([x, z])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(coef[0])


def residual_maker(z: np.ndarray) -> np.ndarray:
    """M_Z = I - Z(Z'Z)^+Z'. By Frisch-Waugh-Lovell, beta = (M x)'(M y) / (M x)'(M x)."""
    return np.eye(z.shape[0]) - z @ np.linalg.pinv(z)


def perm_betas(
    y: np.ndarray, hist: np.ndarray, z: np.ndarray, perms: np.ndarray
) -> np.ndarray:
    """beta for each row of ``perms`` (state permutations), via FWL, vectorised.

    ``hist`` is the (n_states, 3) exposure history; row i of a permutation hands
    state i the whole 3-interval history of state perms[k, i].
    """
    m = residual_maker(z)
    my = m @ y
    xs = hist[perms].reshape(perms.shape[0], -1).T  # (108, n_perm), state-major rows
    mx = m @ xs
    return (mx * my[:, None]).sum(axis=0) / (mx * mx).sum(axis=0)


def permutation_p(
    y: np.ndarray, hist: np.ndarray, z: np.ndarray, n_perm: int, seed: int
) -> tuple[float, float]:
    beta_obs = ols_beta(y, hist.reshape(-1), z)
    rng = np.random.default_rng(seed)
    perms = np.array([rng.permutation(hist.shape[0]) for _ in range(n_perm)])
    betas = perm_betas(y, hist, z, perms)
    p = float(np.mean(np.abs(betas) >= abs(beta_obs) - 1e-12))
    return beta_obs, p


def cluster_bootstrap_ci(
    y: np.ndarray, hist: np.ndarray, z: np.ndarray, n_boot: int, seed: int
) -> tuple[float, float]:
    """Percentile 95% CI from resampling states (all three of their rows) with replacement."""
    n_states, k = hist.shape
    yy = y.reshape(n_states, k)
    zz = z.reshape(n_states, k, -1)
    rng = np.random.default_rng(seed)
    betas = np.empty(n_boot)
    for b in range(n_boot):
        idx = rng.integers(0, n_states, n_states)
        betas[b] = ols_beta(yy[idx].reshape(-1), hist[idx].reshape(-1), zz[idx].reshape(n_states * k, -1))
    lo, hi = np.percentile(betas, [2.5, 97.5])
    return float(lo), float(hi)


def minimum_detectable_effect(
    y: np.ndarray, hist: np.ndarray, z: np.ndarray, seed: int
) -> tuple[float | None, float | None, list[tuple[float, float, float]]]:
    """Smallest |beta| on a 0.0005 grid that the permutation test detects in >= 80% of runs.

    Each simulated dataset = fitted null model (y ~ z, beta = 0) + state-cluster-
    resampled residuals + beta * aligned_share; it is tested with 1,000 permutations.
    The same 500 residual draws and permutation sets are reused at every grid
    point, so power is a function of beta alone. Because the estimator is linear in
    y, beta_hat(beta) = beta_hat(0) + beta * slope, which makes the grid cheap.
    Returns the MDE for beta < 0 and beta > 0 separately, plus the power curve.
    """
    n_states, k = hist.shape
    x = hist.reshape(-1)
    m = residual_maker(z)
    fitted0 = y - m @ y
    resid0 = (m @ y).reshape(n_states, k)
    rng = np.random.default_rng(seed)

    obs0 = np.empty(MDE_DATASETS)
    perm0 = np.empty((MDE_DATASETS, MDE_PERMS))
    perm_slope = np.empty((MDE_DATASETS, MDE_PERMS))
    mx_obs = m @ x
    for d in range(MDE_DATASETS):
        idx = rng.integers(0, n_states, n_states)
        base = fitted0 + resid0[idx].reshape(-1)
        perms = np.array([rng.permutation(n_states) for _ in range(MDE_PERMS)])
        obs0[d] = mx_obs @ base / (mx_obs @ mx_obs)
        # The observed regressor gives slope exactly 1; a permuted one gives
        # (M x_perm)'x / (M x_perm)'(M x_perm).
        xs = hist[perms].reshape(MDE_PERMS, -1).T
        mxs = m @ xs
        denom = (mxs * mxs).sum(axis=0)
        perm0[d] = (mxs * (m @ base)[:, None]).sum(axis=0) / denom
        perm_slope[d] = (mxs * x[:, None]).sum(axis=0) / denom

    def power(beta: float) -> float:
        b_obs = obs0 + beta
        b_perm = perm0 + beta * perm_slope
        p = np.mean(np.abs(b_perm) >= np.abs(b_obs)[:, None] - 1e-12, axis=1)
        return float(np.mean(p < ALPHA))

    curve: list[tuple[float, float, float]] = []
    mde_neg = mde_pos = None
    n_steps = round(MDE_MAX / MDE_STEP)
    for i in range(1, n_steps + 1):
        g = round(i * MDE_STEP, 6)
        pw_neg, pw_pos = power(-g), power(g)
        curve.append((g, pw_neg, pw_pos))
        if mde_neg is None and pw_neg >= 0.8:
            mde_neg = g
        if mde_pos is None and pw_pos >= 0.8:
            mde_pos = g
        if mde_neg is not None and mde_pos is not None:
            break
    return mde_neg, mde_pos, curve


# --------------------------------------------------------------------------- reporting


def fmt(v: float) -> str:
    return f"{v:.4f}"


def fmt_p(p: float) -> str:
    """Three decimals, half-up, so 0.0355 prints 0.036 rather than float-rounding to 0.035."""
    return str(Decimal(str(round(p, 6))).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def choose_sentence(beta: float, lo: float, hi: float, p: float, mde: float | None) -> str:
    """Exactly one §3 template, filled. Nothing else may be composed here."""
    ci = f"{fmt(lo)} to {fmt(hi)}"
    if p < ALPHA:
        slower = "" if beta < 0 else "*slower* "
        faster = "faster " if beta < 0 else ""
        word = f"{faster}{slower}".strip()
        return (
            "Over 2013–2021, states governed in alignment with the federal ruling party saw "
            f"MPI fall {fmt(abs(beta))} MPI points {word} per year than non-aligned states "
            f"(95% CI {ci}, permutation p = {fmt_p(p)}). This is an association within "
            "states over time, not an effect of party."
        )
    mde_txt = fmt(mde) if mde is not None else f"{MDE_MAX} (no grid point reached 80% power)"
    return (
        "No association between federal alignment and the pace of MPI change is detectable "
        f"over 2013–2021 (β = {fmt(beta)}, 95% CI {ci}, permutation p = {fmt_p(p)}). This "
        f"design could not detect an association smaller than {mde_txt} MPI points per year, "
        "so this is not evidence that none exists."
    )


def write_section4(
    sentence: str,
    results: list[dict[str, str]],
    mde_line: str,
    seed_range: tuple[float, float],
    run_date: str,
) -> None:
    text = SPEC.read_text(encoding="utf-8")
    head = "## 4. Result"
    assert text.count(head) == 1, "docs/party_alignment.md must contain exactly one '## 4. Result'"
    before = text.split(head)[0]
    rows = "\n".join(
        f"| {r['model']} | {r['beta']} | {r['ci_lo']} to {r['ci_hi']} | {r['p_perm']} | {r['n']} |"
        for r in results
    )
    context = alignment_context_line(results)
    body = f"""{head}

*Written by `scripts/08_party_alignment.py` on {run_date}. Do not edit by hand.*

{sentence}

| Model | β | 95% CI (state-cluster bootstrap) | Permutation p | n |
|---|---|---|---|---|
{rows}

- {context or "No check listed above has permutation p ≥ 0.05."}
- Robustness (d) and the leave-one-interval-out and per-interval rows were added after the
  primary result was known. (d) uses the §2 limitation clause (defections only with sourced
  dates, only as an extra robustness row): the as-won party, switched at the month of each
  sourced change in `data/reference/governor_defections.csv` (the Nov 2013 PDP→APC
  governors, the 31 Jul 2013 ACN/ANPP/CPC→APC merger, later moves through Jun 2021), at
  monthly resolution. Successions after impeachment (Adamawa 2014) are not modelled.
  None of these rows replaces the primary result or changes the §3 sentence.
- Permutation p is a Monte Carlo estimate ({N_PERM:,} draws, seed {SEED}), shown to 3 dp.
  Across {N_SEED_CHECK} other seeds the primary p ranged {fmt_p(seed_range[0])}–{fmt_p(seed_range[1])},
  so read it as about ±0.005.
- {mde_line}
- n = 108 state-intervals (36 states × 3 intervals) for the full models. FCT excluded: no
  elected governor.
- β is in MPI points (0–1 scale) per year per unit of `aligned_share`; check (a) is in
  log-ratio per year. Bootstrap: {N_BOOT:,} draws; seed {SEED}.
- Limitations: the primary model does not model sitting-party defections (see (d)); MPI
  change carries survey error (median relative SE about 15%); n = 36 states, so a null
  result is a statement about this design, not about the world.
"""
    SPEC.write_text(before + body, encoding="utf-8")


def subset_design(
    kept: list[int], y_full: np.ndarray, hist_full: np.ndarray, mpi_t0: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """y, exposure history and controls restricted to the interval indices ``kept``."""
    n_states, k = hist_full.shape
    yy = y_full.reshape(n_states, k)[:, kept].reshape(-1)
    hh = hist_full[:, kept]
    m0 = mpi_t0.reshape(n_states, k)[:, kept].reshape(-1)
    dummies = [
        np.tile(np.eye(len(kept))[i], n_states) for i in range(1, len(kept))
    ]
    zz = np.column_stack([np.ones(len(yy)), *dummies, m0])
    return yy, hh, zz


# --------------------------------------------------------------------------- main


def main() -> int:
    lookup = read_lookup()
    governed = sorted(p for p in lookup if p != FCT)
    assert len(governed) == 36

    events = read(EVENTS)
    assert not [e for e in events if e["pcode"] == FCT], "FCT must have no governorship events"
    seatings: dict[str, list[tuple[int, str]]] = {}
    for e in events:
        seatings.setdefault(e["pcode"], []).append((int(e["seated_year"]), e["party"]))
    assert set(seatings) == set(governed), "every governed state needs events"

    fed_rows = read(FEDERAL)
    fed_seatings = [(date.fromisoformat(r["from_date"]).year, r["party"]) for r in fed_rows]
    assert fed_seatings == [(1999, "PDP"), (2015, "APC")], f"unexpected federal series {fed_seatings}"
    fed = party_by_year(fed_seatings)

    weights: dict[str, dict[int, float]] = {
        p: year_weights(party_by_year(seatings[p]), fed) for p in governed
    }

    changes: dict[str, list[tuple[int, int, str, str]]] = {}
    for d in read(DEFECTIONS):
        when = date.fromisoformat(d["date"])
        assert d["pcode"] in seatings, f"defection for ungoverned unit {d['pcode']}"
        assert d["source_url"].startswith("http"), f"{d['pcode']} {d['date']}: defection needs a source"
        changes.setdefault(d["pcode"], []).append((when.year, when.month, d["from_party"], d["to_party"]))
    # The monthly series must reproduce the annual one when no change is applied.
    for p in governed:
        plain = monthly_weights(seatings[p], [], fed_seatings)
        assert all(abs(plain[y] - weights[p][y]) < 1e-12 for y in plain), f"{p}: monthly != annual"
    weights_d: dict[str, dict[int, float]] = {
        p: monthly_weights(seatings[p], changes.get(p, []), fed_seatings) for p in governed
    }

    # Sanity: pre-2015 years of states never governed by PDP before 2015 are unaligned.
    for p in ("NG-LA", "NG-BO"):
        pre = [weights[p][y] for y in range(2000, 2015)]
        assert all(w == 0.0 for w in pre), f"{p}: non-PDP years before 2015 must be unaligned"
        assert abs(weights[p][2015] - W_IN) < 1e-12, f"{p}: 2015 should be 7/12 aligned (APC from May)"
    # 1999 only counts from the late-May seating: at most 7/12 of it can be aligned.
    assert all(weights[p][1999] <= W_IN + 1e-12 for p in governed)

    panel = {(r["pcode"], int(r["survey_year"])): r for r in read(PANEL_IN)}
    atlas = {r["pcode"]: r for r in read(ATLAS)}
    run_date = datetime.now(tz=timezone.utc).date().isoformat()

    rows: list[dict[str, object]] = []
    for p in governed:
        for t0, t1 in INTERVALS:
            share = sum(weights[p][y] for y in range(t0, t1)) / (t1 - t0)
            share_d = sum(weights_d[p][y] for y in range(t0, t1)) / (t1 - t0)
            m0 = float(panel[(p, t0)]["mpi"])
            m1 = float(panel[(p, t1)]["mpi"])
            rows.append(
                {
                    "pcode": p,
                    "state": lookup[p]["name_canonical"],
                    "interval": f"{t0}-{t1}",
                    "t0": t0,
                    "t1": t1,
                    "aligned_share": round(share, 6),
                    "aligned_binary": int(share >= 0.5),
                    "aligned_share_sitting": round(share_d, 6),
                    "mpi_t0": m0,
                    "mpi_t1": m1,
                    "dmpi_annual": round((m1 - m0) / (t1 - t0), 6),
                    "dlogmpi_annual": round(float(np.log(m1 / m0)) / (t1 - t0), 6),
                    "poverty_group": atlas[p]["poverty_group"],
                    "survey_t0": f"{ROUND_SURVEY[t0]} {t0}",
                    "survey_t1": f"{ROUND_SURVEY[t1]} {t1}",
                    "mpi_series": MPI_SERIES,
                    "run_date": run_date,
                }
            )
    assert len(rows) == 108, f"expected 108 state-intervals, got {len(rows)}"
    assert all(0.0 <= float(r["aligned_share"]) <= 1.0 for r in rows), "aligned_share out of [0,1]"

    # Arrays in state-major order: row = state * 3 + interval.
    n_states, k = len(governed), len(INTERVALS)
    hist = np.array([float(r["aligned_share"]) for r in rows]).reshape(n_states, k)
    hist_bin = (hist >= 0.5).astype(float)
    hist_d = np.array([float(r["aligned_share_sitting"]) for r in rows]).reshape(n_states, k)
    y = np.array([float(r["dmpi_annual"]) for r in rows])
    y_log = np.array([float(r["dlogmpi_annual"]) for r in rows])
    mpi_t0 = np.array([float(r["mpi_t0"]) for r in rows])
    fe = np.array([[float(r["t0"] == t0) for t0, _ in INTERVALS[1:]] for r in rows])
    z = np.column_stack([np.ones(len(rows)), fe, mpi_t0])
    poor = np.array([float(r["poverty_group"] == "Poorest 12") for r in rows])
    poor_x_int = np.column_stack([poor * (np.array([r["t0"] for r in rows]) == t0) for t0, _ in INTERVALS])
    z_b = np.column_stack([z, poor_x_int])

    # (kind, short label for compact displays, table label, interval, y, exposure, controls)
    Spec = tuple[str, str, str, str, np.ndarray, np.ndarray, np.ndarray]
    specs: list[Spec] = [
        ("primary", "primary", "Primary: aligned_share (as won)", "", y, hist, z),
        ("robustness", "(a) relative change", "(a) outcome = log(MPI_t1/MPI_t0)/(t1-t0)", "",
         y_log, hist, z),
        ("robustness", "(b) + poverty group × interval", "(b) + poverty_group x interval", "",
         y, hist, z_b),
        ("robustness", "(c) binary exposure", "(c) exposure = aligned_share >= 0.5", "",
         y, hist_bin, z),
        ("robustness", "(d) sitting party", ("(d) sitting party: as won, switched at sourced "
         "defection month (added after the primary result was known, §2 limitation clause)"), "",
         y, hist_d, z),
    ]
    for drop, (t0, t1) in enumerate(INTERVALS):
        label = INTERVAL_LABEL[(t0, t1)]
        kept = [i for i in range(k) if i != drop]
        yy, hh, zz = subset_design(kept, y, hist, mpi_t0)
        specs.append(("loio", f"dropping {label}", f"Leave out {label} (primary model, 2 intervals)",
                      label, yy, hh, zz))
    for only, (t0, t1) in enumerate(INTERVALS):
        label = INTERVAL_LABEL[(t0, t1)]
        yy, hh, zz = subset_design([only], y, hist, mpi_t0)
        specs.append(("per_interval", f"{label} only", (f"Interval {label} only (cross-section, "
                      "aligned_share + mpi_t0)"), label, yy, hh, zz))

    results: list[dict[str, str]] = []
    primary: tuple[float, float, float, float] | None = None
    for kind, short, name, interval, yy, hh, zz in specs:
        beta, p = permutation_p(yy, hh, zz, N_PERM, SEED)
        lo, hi = cluster_bootstrap_ci(yy, hh, zz, N_BOOT, SEED)
        if primary is None:
            primary = (beta, lo, hi, p)
            # The seed must reproduce p exactly.
            beta2, p2 = permutation_p(yy, hh, zz, N_PERM, SEED)
            assert beta2 == beta and p2 == p, "seed does not reproduce the permutation p"
        results.append(
            {"kind": kind, "short": short, "interval": interval, "model": name,
             "beta": fmt(beta), "ci_lo": fmt(lo), "ci_hi": fmt(hi), "p_perm": fmt_p(p),
             "n": str(len(yy))}
        )
        print(f"{short:32s} n={len(yy):3d} beta={beta:+.5f}  CI [{lo:+.5f}, {hi:+.5f}]  p={p:.4f}")
    assert primary is not None
    beta, lo, hi, p = primary
    assert [r["kind"] for r in results].count("primary") == 1 and results[0]["kind"] == "primary"

    # Monte Carlo spread of the primary p across other seeds (reported, never used).
    seed_ps = [permutation_p(y, hist, z, N_PERM, SEED + i)[1] for i in range(1, N_SEED_CHECK + 1)]
    seed_range = (min(seed_ps), max(seed_ps))
    print(f"primary p across {N_SEED_CHECK} other seeds: {seed_range[0]:.4f}-{seed_range[1]:.4f}")

    mde_neg, mde_pos, _curve = minimum_detectable_effect(y, hist, z, SEED)
    # Conservative reading of "smallest |beta|": the magnitude detected with >= 80%
    # power whichever the sign. Both one-sided values are reported beside it.
    mde = None if mde_neg is None or mde_pos is None else max(mde_neg, mde_pos)
    print(f"MDE: beta<0 {mde_neg}, beta>0 {mde_pos} -> |beta| {mde}")
    mde_line = (
        f"MDE (80% power, α = 0.05, {MDE_DATASETS} simulated datasets × {MDE_PERMS:,} "
        f"permutations, grid {MDE_STEP}): |β| = {fmt(mde) if mde is not None else 'not reached'} "
        f"MPI points per year (β < 0: {fmt(mde_neg) if mde_neg else 'not reached'}; "
        f"β > 0: {fmt(mde_pos) if mde_pos else 'not reached'})."
    )

    sentence = choose_sentence(beta, lo, hi, p, mde)
    write_section4(sentence, results, mde_line, seed_range, run_date)

    for r in results:
        r.update({"mde": fmt(mde) if mde is not None else "", "run_date": run_date})
    results[0]["sentence"] = sentence
    write_csv(
        RESULT_OUT,
        results,
        ["kind", "short", "interval", "model", "beta", "ci_lo", "ci_hi", "p_perm", "n", "mde",
         "run_date", "sentence"],
    )
    print(alignment_context_line(results))

    write_csv(
        PANEL_OUT,
        rows,
        [
            "pcode", "state", "interval", "t0", "t1", "aligned_share", "aligned_binary",
            "aligned_share_sitting", "mpi_t0", "mpi_t1", "dmpi_annual", "dlogmpi_annual", "poverty_group",
            "survey_t0", "survey_t1", "mpi_series", "run_date",
        ],
    )

    span = W_IN + (SPAN_LAST - SPAN_FIRST)
    state_rows: list[dict[str, object]] = []
    for p in sorted(lookup):
        if p == FCT:
            aligned, note = "—", "excluded: no elected governor"
        else:
            aligned, note = f"{sum(weights[p].values()):.1f}", ""
        state_rows.append(
            {
                "pcode": p,
                "state": lookup[p]["name_canonical"],
                "aligned_years_1999_2021": aligned,
                "span_years": f"{span:.1f}",
                "note": note,
                "run_date": run_date,
            }
        )
    assert len(state_rows) == 37
    write_csv(STATE_OUT, state_rows, ["pcode", "state", "aligned_years_1999_2021", "span_years", "note", "run_date"])

    print(f"\n{sentence}\n")
    print(f"wrote 108 rows -> {PANEL_OUT.relative_to(PANEL_OUT.parents[2])}")
    print(f"wrote 37 rows  -> {STATE_OUT.relative_to(STATE_OUT.parents[2])} (FCT excluded from the test)")
    print(f"wrote section 4 -> {SPEC.relative_to(SPEC.parents[1])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
