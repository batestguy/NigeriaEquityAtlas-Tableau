"""Stage 3 -- acquire climate for each state capital from the Open-Meteo archive.

The archive API is keyless, so this is the one layer with no access friction at
all. Two deliberate choices:

* Coordinates come from data/reference/state_capitals.csv (GeoNames admin-1
  seats), not from polygon centroids. A centroid is not a capital, and sampling
  the geometric middle of Borno would quietly report the wrong climate.
* Each response is QC'd on day coverage. Open-Meteo interpolates gaps, so a year
  with missing days still returns a plausible-looking mean; counting the days that
  actually contributed is what makes a bad year visible instead of smooth.

Anomalies are computed against the 1991-2020 baseline (the WMO standard normal
period), which is the baseline the archive's own climatology comparisons use.
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from typing import Any

from common import INTERIM, RAW, read_capitals, read_lookup, write_csv

OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive"
START_YEAR, END_YEAR = 1990, 2024
BASELINE = (1991, 2020)
BATCH_SIZE = 37
MIN_DAYS = 300  # a year with fewer contributing days is flagged, not trusted
TIMEZONE = "Africa/Lagos"
BATCH_PAUSE_SECONDS = 20
MAX_ATTEMPTS = 8

RAW_CLIMATE = RAW / "openmeteo_capitals_1990_2024.json"


def fetch_batch(lats: list[float], lons: list[float]) -> list[dict[str, Any]]:
    """One bulk request, retried with backoff.

    Open-Meteo's free tier rate-limits on *request count* per hour, not on data
    volume, so the entire 37-capital, 35-year pull is issued as a single request
    instead of a series of batches. The error body is printed because the limit
    messages are specific and actionable ("Hourly API request limit exceeded").
    """
    params = {
        "latitude": ",".join(f"{v:.4f}" for v in lats),
        "longitude": ",".join(f"{v:.4f}" for v in lons),
        "start_date": f"{START_YEAR}-01-01",
        "end_date": f"{END_YEAR}-12-31",
        "daily": "temperature_2m_mean,precipitation_sum",
        "timezone": TIMEZONE,
    }
    url = f"{OPEN_METEO}?{urllib.parse.urlencode(params)}"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={"User-Agent": "NigeriaMPIEquityAtlas/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=600) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload if isinstance(payload, list) else [payload]
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == MAX_ATTEMPTS:
                raise
            reason = ""
            try:
                reason = json.loads(exc.read().decode("utf-8", "replace")).get("reason", "")
            except Exception:  # noqa: BLE001 - diagnostic only
                pass
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after:
                wait = float(retry_after)
            elif "hour" in reason.lower():
                wait = 600.0  # quota resets hourly, so short backoff just burns attempts
            else:
                wait = min(20 * attempt, 120)
            print(
                f"    HTTP {exc.code}: {reason or 'rate limited'} -- retrying in {wait/60:.1f} min "
                f"(attempt {attempt}/{MAX_ATTEMPTS})",
                flush=True,
            )
            time.sleep(wait)
    raise RuntimeError("unreachable")


def main() -> int:
    lookup = read_lookup()
    capitals = read_capitals()
    codes = sorted(lookup)
    for p in codes:
        assert p in capitals, f"{p} has no capital coordinates"

    # ---- fetch -------------------------------------------------------------
    # The cache is keyed by pcode, not by position, and rewritten after every
    # batch. A rate limit or crash then resumes by asking for exactly the capitals
    # that are still missing, regardless of how earlier batches were sized.
    cache: dict[str, dict[str, Any]] = {}
    if RAW_CLIMATE.exists():
        cached = json.loads(RAW_CLIMATE.read_text(encoding="utf-8"))
        if isinstance(cached, dict):
            responses = cached.get("responses", {})
            cache = {str(k): v for k, v in dict(responses).items()}
        else:
            # Legacy positional cache from an earlier batch size: adopt it, since
            # those batches were contiguous leading slices of the sorted code list.
            for pcode, payload in zip(codes, list(cached)):
                cache[pcode] = payload
        print(f"cache: {len(cache)}/{len(codes)} capitals already pulled")

    def save_cache() -> None:
        RAW_CLIMATE.parent.mkdir(parents=True, exist_ok=True)
        tmp = RAW_CLIMATE.with_suffix(".json.part")
        tmp.write_text(json.dumps({"responses": cache}), encoding="utf-8")
        tmp.replace(RAW_CLIMATE)

    missing = [c for c in codes if c not in cache]
    while missing:
        chunk = missing[:BATCH_SIZE]
        print(f"  fetching {len(chunk)} capitals ({chunk[0]}..{chunk[-1]}) ...", flush=True)
        responses = fetch_batch(
            [float(capitals[c]["lat"]) for c in chunk],
            [float(capitals[c]["lon"]) for c in chunk],
        )
        assert len(responses) == len(chunk), f"asked for {len(chunk)} locations, got {len(responses)}"
        cache.update(dict(zip(chunk, responses)))
        save_cache()
        print(f"  cached {len(cache)}/{len(codes)} ({RAW_CLIMATE.stat().st_size/1e6:.1f} MB)")
        missing = [c for c in codes if c not in cache]
        if missing:
            time.sleep(BATCH_PAUSE_SECONDS)

    payloads = [cache[c] for c in codes]
    assert len(payloads) == len(codes), f"got {len(payloads)} responses for {len(codes)} capitals"

    # ---- aggregate daily -> annual -----------------------------------------
    # annual[(pcode, year)] = {"t": [...], "p": [...]}
    annual: dict[tuple[str, int], dict[str, list[float | None]]] = defaultdict(
        lambda: {"t": [], "p": []}
    )
    for pcode, payload in zip(codes, payloads):
        daily = payload.get("daily", {})
        times = daily.get("time", [])
        temps = daily.get("temperature_2m_mean", [])
        precips = daily.get("precipitation_sum", [])
        for t, tv, pv in zip(times, temps, precips):
            year = int(t[:4])
            annual[(pcode, year)]["t"].append(tv)
            annual[(pcode, year)]["p"].append(pv)

    lo, hi = BASELINE
    rows: list[dict[str, Any]] = []
    incomplete: list[tuple[str, int]] = []
    baseline_cache: dict[str, dict[str, float]] = {}

    for pcode in codes:
        # baseline means over the reference period
        t_vals, p_vals = [], []
        for year in range(lo, hi + 1):
            cell = annual.get((pcode, year))
            if not cell:
                continue
            t_vals += [v for v in cell["t"] if v is not None]
            p_vals += [v for v in cell["p"] if v is not None]
        t_base = sum(t_vals) / len(t_vals) if t_vals else float("nan")
        p_base = sum(p_vals) if p_vals else float("nan")
        p_base_mean_annual = p_base / (hi - lo + 1)
        baseline_cache[pcode] = {"temp": t_base, "precip_mean_annual": p_base_mean_annual}

        for year in range(START_YEAR, END_YEAR + 1):
            cell = annual.get((pcode, year))
            if cell is None:
                raise SystemExit(f"{pcode}: no Open-Meteo data for {year}")
            t_ok = [v for v in cell["t"] if v is not None]
            p_ok = [v for v in cell["p"] if v is not None]
            if len(t_ok) < MIN_DAYS or len(p_ok) < MIN_DAYS:
                incomplete.append((lookup[pcode]["name_canonical"], year))
            t_mean = sum(t_ok) / len(t_ok)
            p_total = sum(p_ok)
            rows.append(
                {
                    "pcode": pcode,
                    "state": lookup[pcode]["name_canonical"],
                    "capital": capitals[pcode]["capital"],
                    "year": year,
                    "temp_mean_c": round(t_mean, 3),
                    "precip_total_mm": round(p_total, 1),
                    "temp_anomaly_c": round(t_mean - t_base, 3),
                    "precip_anomaly_mm": round(p_total - p_base_mean_annual, 1),
                    "precip_anomaly_pct": round(100.0 * (p_total - p_base_mean_annual) / p_base_mean_annual, 1),
                    "days_temp": len(t_ok),
                    "days_precip": len(p_ok),
                }
            )

    # ---- gates --------------------------------------------------------------
    expected = len(codes) * (END_YEAR - START_YEAR + 1)
    assert len(rows) == expected, f"expected {expected} state-years, got {len(rows)}"
    for key in ("temp_mean_c", "precip_total_mm", "temp_anomaly_c"):
        blanks = [r for r in rows if r[key] is None]
        assert not blanks, f"{len(blanks)} rows have null {key}"

    write_csv(
        INTERIM / "climate_state_year.csv",
        rows,
        ["pcode", "state", "capital", "year", "temp_mean_c", "precip_total_mm",
         "temp_anomaly_c", "precip_anomaly_mm", "precip_anomaly_pct", "days_temp", "days_precip"],
    )
    write_csv(
        INTERIM / "climate_baseline_1991_2020.csv",
        [
            {
                "pcode": p,
                "state": lookup[p]["name_canonical"],
                "capital": capitals[p]["capital"],
                "baseline_temp_c": round(baseline_cache[p]["temp"], 3),
                "baseline_precip_mm_per_year": round(baseline_cache[p]["precip_mean_annual"], 1),
            }
            for p in codes
        ],
        ["pcode", "state", "capital", "baseline_temp_c", "baseline_precip_mm_per_year"],
    )

    hottest = max(rows, key=lambda r: r["temp_mean_c"])
    coolest = min(rows, key=lambda r: r["temp_mean_c"])
    wettest = max(rows, key=lambda r: r["precip_total_mm"])
    print(f"\nwrote {len(rows)} state-years -> data/interim/climate_state_year.csv")
    print(f"baseline {lo}-{hi}; hottest cell {hottest['state']} {hottest['year']} {hottest['temp_mean_c']}C")
    print(f"                    coolest cell {coolest['state']} {coolest['year']} {coolest['temp_mean_c']}C")
    print(f"           wettest cell {wettest['state']} {wettest['year']} {wettest['precip_total_mm']}mm")
    if incomplete:
        print(f"WARNING: {len(incomplete)} state-year(s) below {MIN_DAYS} contributing days:")
        for s, y in incomplete[:10]:
            print(f"    {s} {y}")
    else:
        print(f"QC: all {len(rows)} state-years have >= {MIN_DAYS} contributing days")
    return 0


if __name__ == "__main__":
    sys.exit(main())