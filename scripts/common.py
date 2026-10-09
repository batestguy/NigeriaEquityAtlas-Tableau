"""Shared paths, provenance and join helpers for the Nigeria MPI Equity Atlas pipeline.

Every script resolves paths relative to the repository root so nothing depends on
the absolute location of this checkout (D: is a removable drive).
"""

from __future__ import annotations

import csv
import hashlib
import json
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA = REPO_ROOT / "data"
RAW = DATA / "raw"
INTERIM = DATA / "interim"
PROCESSED = DATA / "processed"
REFERENCE = DATA / "reference"
DOCS = REPO_ROOT / "docs"

PROVENANCE = RAW / "_provenance.csv"
USER_AGENT = "Mozilla/5.0 (Nigeria MPI Equity Atlas pipeline)"

# Canonical administrative-1 count. FCT is a state here, and dropping it is the
# classic silent bug in Nigeria state-level work.
N_STATES = 37


def ensure_dirs() -> None:
    for d in (RAW, INTERIM, PROCESSED, REFERENCE, DOCS):
        d.mkdir(parents=True, exist_ok=True)


def download(url: str, dest: Path, *, force: bool = False) -> Path:
    """Fetch ``url`` to ``dest`` and record provenance (SHA256, size, fetch date).

    An existing file is reused unless ``force`` is set, but it is still recorded in
    the provenance ledger -- the fetch date comes from the file's mtime, so reusing
    a cached download does not falsify the record.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not force:
        note = "cached"
    else:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=300) as resp:
            dest.write_bytes(resp.read())
        note = "downloaded"
    payload = dest.read_bytes()
    fetched = date.fromtimestamp(dest.stat().st_mtime).isoformat()
    _record_provenance(url, dest, hashlib.sha256(payload).hexdigest(), fetched, note)
    return dest


def _record_provenance(url: str, dest: Path, sha256: str, fetched: str, note: str) -> None:
    """Upsert one row in the provenance ledger (idempotent per filename)."""
    row = {
        "file": dest.name,
        "url": url,
        "sha256": sha256,
        "bytes": dest.stat().st_size,
        "fetched_utc": fetched,
        "note": note,
    }
    existing: list[dict[str, str]] = []
    if PROVENANCE.exists():
        with PROVENANCE.open(newline="", encoding="utf-8") as fh:
            existing = [r for r in csv.DictReader(fh) if r.get("file") != dest.name]
    existing.append({k: str(v) for k, v in row.items()})
    PROVENANCE.parent.mkdir(parents=True, exist_ok=True)
    with PROVENANCE.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerows(sorted(existing, key=lambda r: r["file"]))


def read_lookup() -> dict[str, dict[str, str]]:
    """Load the canonical state lookup, keyed by pcode.

    The lookup is the single source of truth for every join in this project. If a
    source spells a state differently, the spelling lives here -- never in ad-hoc
    normalisation code.
    """
    path = REFERENCE / "state_lookup.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == N_STATES, f"state_lookup.csv has {len(rows)} rows, expected {N_STATES}"
    codes = [r["pcode"] for r in rows]
    assert len(set(codes)) == N_STATES, "state_lookup.csv has duplicate pcode values"
    return {r["pcode"]: r for r in rows}


def read_capitals() -> dict[str, dict[str, str]]:
    path = REFERENCE / "state_capitals.csv"
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == N_STATES, f"state_capitals.csv has {len(rows)} rows, expected {N_STATES}"
    return {r["pcode"]: r for r in rows}


def load_boundaries() -> dict[str, Any]:
    """Load the geoBoundaries Nigeria ADM1 GeoJSON from data/raw, keyed by ISO code."""
    path = RAW / "nga_adm1.geojson"
    assert path.exists(), "boundaries missing: run scripts/01_acquire_mpi.py first"
    gj = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, Any] = {}
    for feat in gj["features"]:
        out[feat["properties"]["shapeISO"]] = feat
    assert len(out) == N_STATES, f"expected {N_STATES} ADM1 features, got {len(out)}"
    return out


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    materialised = list(rows)
    with path.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(materialised)
    return len(materialised)


def minmax(values: dict[str, float]) -> tuple[dict[str, float], float, float]:
    """Min-max scale to 0-100. Returns (scaled, min, max) so anchors can be documented."""
    lo, hi = min(values.values()), max(values.values())
    if hi == lo:
        return {k: 0.0 for k in values}, lo, hi
    return {k: 100.0 * (v - lo) / (hi - lo) for k, v in values.items()}, lo, hi

def alignment_context_line(rows: list[dict[str, str]], alpha: float = 0.05) -> str:
    """One factual line on how far the stage 8 primary result holds up.

    Built only from party_alignment_result.csv rows (kind, short, interval, p_perm),
    so stage 8 (section 4), stage 5 (PNG) and stage 7 (map panel) print the same
    words. "Rests on" names the intervals whose own cross-section has p < alpha when
    that is not all of them; "not robust to" lists every robustness check and every
    leave-one-interval-out fit with p >= alpha. Empty when the primary result is not
    detected, because "not robust" has nothing to qualify then.
    """
    primary = [r for r in rows if r["kind"] == "primary"]
    if len(primary) != 1 or float(primary[0]["p_perm"]) >= alpha:
        return ""
    per = [r for r in rows if r["kind"] == "per_interval"]
    rests = [r["interval"] for r in per if float(r["p_perm"]) < alpha]
    weak = [r["short"] for r in rows if r["kind"] == "robustness" and float(r["p_perm"]) >= alpha]
    loio = [r for r in rows if r["kind"] == "loio"]
    loio_weak = [r for r in loio if float(r["p_perm"]) >= alpha]
    if loio_weak and len(loio_weak) == len(loio):
        weak.append("dropping any one interval")
    else:
        weak.extend(f"dropping {r['interval']}" for r in loio_weak)
    parts = []
    if rests and len(rests) < len(per):
        parts.append(f"Result rests on {' and '.join(rests)}")
    if weak:
        parts.append(f"not robust to {', '.join(weak)}")
    if not parts:
        return "Every robustness and leave-one-interval-out check also has p < 0.05."
    line = "; ".join(parts)
    return line[0].upper() + line[1:] + "."
