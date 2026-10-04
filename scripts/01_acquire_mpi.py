"""Stage 1 -- acquire and reconcile the MPI sources.

Three files, none requiring registration:

  nga_mpi.csv             OPHI, CC0. 37 admin-1 rows + a national row, headline
                          MPI / headcount ratio / intensity / vulnerable / severe.
  nga_mpi_trends.csv      OPHI, CC0. The same 37 states across four survey rounds
                          (2013 DHS, 2016 MICS, 2018 DHS, 2021 MICS).
  subnational-results-mpi.xlsx
                          UNDP Global MPI, CC BY. Sheets 5.1-5.6 add what the CSVs
                          lack: the Health / Education / Living Standards
                          contribution split, indicator-level detail, standard
                          errors, sample sizes and per-state population.

The gate that matters: the UNDP workbook and the OPHI CSV are independent
publications of the same survey. If they disagree about a state, then one of them
has been revised and every downstream number is ambiguous. So the two are compared
state by state and any disagreement beyond rounding aborts the pipeline.

Note on hosts: data.hdx.humdata.org does not resolve on this network; the legacy
data.humdata.org serves the identical CKAN API and is used throughout.
"""

from __future__ import annotations

import csv
import io
import sys
import zipfile
from typing import Any

import openpyxl

from common import INTERIM, RAW, download, read_lookup, write_csv

OPHI_MPI = (
    "https://data.humdata.org/dataset/042c1bf4-2942-475f-8cb2-1fb783f8da91/resource/"
    "601f51cd-c46a-4ab2-ba0f-8bef62329ddc/download/nga_mpi.csv"
)
OPHI_TRENDS = (
    "https://data.humdata.org/dataset/042c1bf4-2942-475f-8cb2-1fb783f8da91/resource/"
    "99381c98-d5de-49cf-81c1-5b54d2cddf2f/download/nga_mpi_trends.csv"
)
UNDP_SUBNATIONAL = (
    "https://data.humdata.org/dataset/42b16840-3a56-4a20-9314-7aa171f1136c/resource/"
    "45b18fbb-ab0d-4f54-ae23-c078f1eccf25/download/subnational-results-mpi.xlsx"
)

# Sheet 5.3 of the UNDP workbook, Nigeria rows. Column indices are fixed by the
# published table layout; verified against the header rows at load time.
UNDP_SHEET = "5.3 Contribution Region"
COL = {
    "region": 6,
    "mpi_country": 7,
    "mpi_region": 8,
    "contrib_health": 9,
    "contrib_education": 10,
    "contrib_living_standards": 11,
    "pop_share_pct": 25,
    "population_thousands": 26,
    "mpi_poor_thousands": 27,
    "n_indicators": 28,
    "indicators_missing": 29,
}
TOLERANCE = 1e-3  # OPHI publishes 4dp, UNDP full precision


def read_csv_rows(path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as fh:
        return list(csv.DictReader(fh))


def _f(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_undp_nigeria(path) -> list[dict[str, Any]]:
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb[UNDP_SHEET]
    rows = [list(r) for r in ws.iter_rows(values_only=True)]

    # Guard the hardcoded column indices against a silent upstream layout change.
    # Row 4 is the merged group header ("Subnational region"); the per-column
    # labels in row 6 carry the dimension names. The arithmetic check further down
    # (contributions must sum to 100) is the real guarantee that these three
    # columns are the three dimensions.
    region_header = " ".join(str(rows[4][COL["region"]] or "").split()).lower()
    if region_header != "subnational region":
        raise SystemExit(
            f"{UNDP_SHEET!r} layout changed: column {COL['region']} is {rows[4][COL['region']]!r}, "
            "expected 'Subnational region'. Re-check COL in this script."
        )
    groups = [
        " ".join(str(rows[6][COL[k]] or "").split())
        for k in ("contrib_health", "contrib_education", "contrib_living_standards")
    ]
    if groups != ["Health", "Education", "Living Standards"]:
        raise SystemExit(
            f"{UNDP_SHEET!r} dimension columns moved: got {groups}, "
            "expected ['Health', 'Education', 'Living Standards']"
        )

    out: list[dict[str, Any]] = []
    for r in rows:
        if len(r) > COL["indicators_missing"] and r[2] and str(r[2]).strip() == "Nigeria":
            out.append(
                {
                    "region": str(r[COL["region"]]).strip(),
                    "survey": str(r[4]).strip(),
                    "year": str(r[5]).strip(),
                    "mpi_country": _f(r[COL["mpi_country"]]),
                    "mpi": _f(r[COL["mpi_region"]]),
                    "contrib_health": _f(r[COL["contrib_health"]]),
                    "contrib_education": _f(r[COL["contrib_education"]]),
                    "contrib_living_standards": _f(r[COL["contrib_living_standards"]]),
                    "pop_share_pct": _f(r[COL["pop_share_pct"]]),
                    "population_thousands": _f(r[COL["population_thousands"]]),
                    "mpi_poor_thousands": _f(r[COL["mpi_poor_thousands"]]),
                    "n_indicators": _f(r[COL["n_indicators"]]),
                    "indicators_missing": str(r[COL["indicators_missing"]] or "").strip(),
                }
            )
    return out


def main() -> int:
    lookup = read_lookup()
    name_to_pcode = {m["name_canonical"]: p for p, m in lookup.items()}

    mpi_path = download(OPHI_MPI, RAW / "ophi_nga_mpi.csv")
    trends_path = download(OPHI_TRENDS, RAW / "ophi_nga_mpi_trends.csv")
    undp_path = download(UNDP_SUBNATIONAL, RAW / "undp_subnational_results_mpi.xlsx")

    # ---- OPHI headline -----------------------------------------------------
    ophi_admin1 = [r for r in read_csv_rows(mpi_path) if r["Admin 1 Name"].strip()]
    assert len(ophi_admin1) == 37, f"OPHI headline has {len(ophi_admin1)} admin-1 rows, expected 37"

    headline: dict[str, dict[str, Any]] = {}
    for r in ophi_admin1:
        pcode = name_to_pcode.get(r["Admin 1 Name"].strip())
        assert pcode, f"OPHI state {r['Admin 1 Name']!r} is not in state_lookup.csv"
        headline[pcode] = {
            "mpi": _f(r["MPI"]),
            "headcount_ratio": _f(r["Headcount Ratio"]),
            "intensity": _f(r["Intensity of Deprivation"]),
            "vulnerable": _f(r["Vulnerable to Poverty"]),
            "severe": _f(r["In Severe Poverty"]),
            "ophi_pcode_in_source": r["Admin 1 PCode"].strip(),
            "survey": r["Survey"].strip(),
            "survey_year": int(r["Start Date"][:4]),
        }
    print(f"OPHI headline: {len(headline)} admin-1 rows")

    # ---- OPHI trends -------------------------------------------------------
    trend_rows = [r for r in read_csv_rows(trends_path) if r["Admin 1 Name"].strip()]
    rounds = sorted({(int(r["Start Date"][:4]), r["Survey"].strip()) for r in trend_rows})
    print(f"OPHI trends: {len(trend_rows)} admin-1 rows across {len(rounds)} rounds {rounds}")
    assert len(trend_rows) == 148, f"expected 37 states x 4 rounds = 148 trend rows, got {len(trend_rows)}"

    trend_out: list[dict[str, Any]] = []
    for r in trend_rows:
        pcode = name_to_pcode.get(r["Admin 1 Name"].strip())
        assert pcode, f"trend state {r['Admin 1 Name']!r} not in state_lookup"
        trend_out.append(
            {
                "pcode": pcode,
                "state": lookup[pcode]["name_canonical"],
                "survey_year": int(r["Start Date"][:4]),
                "survey": r["Survey"].strip(),
                "mpi": _f(r["MPI"]),
                "headcount_ratio": _f(r["Headcount Ratio"]),
                "intensity": _f(r["Intensity of Deprivation"]),
            }
        )

    # ---- UNDP subnational --------------------------------------------------
    undp = load_undp_nigeria(undp_path)
    print(f"UNDP subnational: {len(undp)} Nigeria rows")
    if len(undp) != 37:
        raise SystemExit(f"UNDP Nigeria rows = {len(undp)}, expected 37")

    undp_by_name = {r["region"]: r for r in undp}
    missing = set(name_to_pcode) - set(undp_by_name)
    if missing:
        raise SystemExit(f"UNDP is missing regions present in state_lookup: {sorted(missing)}")

    # ---- reconciliation gate ----------------------------------------------
    # The two publications must agree. Disagreement means a silent revision, which
    # would make every downstream figure ambiguous about which vintage it is.
    mismatches: list[str] = []
    vintages = set()
    for pcode, h in headline.items():
        u = undp_by_name[lookup[pcode]["name_canonical"]]
        vintages.add((u["survey"], u["year"]))
        for field in ("mpi",):
            if h[field] is None or u[field] is None:
                mismatches.append(f"{pcode}: {field} missing (OPHI={h[field]}, UNDP={u[field]})")
            elif abs(h[field] - u[field]) > TOLERANCE:
                mismatches.append(
                    f"{pcode}: {field} OPHI={h[field]:.6f} vs UNDP={u[field]:.6f} "
                    f"(diff {abs(h[field] - u[field]):.2e})"
                )
    if vintages != {("MICS", "2021")}:
        raise SystemExit(f"unexpected UNDP vintage(s) {vintages}; this pipeline targets MICS 2021")
    if mismatches:
        print("\nRECONCILIATION FAILED -- OPHI and UNDP disagree:")
        for m in mismatches[:20]:
            print("  -", m)
        return 1

    # ---- dimension contributions ------------------------------------------
    dim_rows: list[dict[str, Any]] = []
    for pcode in sorted(lookup):
        u = undp_by_name[lookup[pcode]["name_canonical"]]
        share_sum = u["contrib_health"] + u["contrib_education"] + u["contrib_living_standards"]
        if abs(share_sum - 100.0) > 0.5:
            raise SystemExit(
                f"{pcode}: dimension contributions sum to {share_sum:.2f}, expected 100"
            )
        for field in ("contrib_health", "contrib_education", "contrib_living_standards"):
            if u[field] is None:
                raise SystemExit(f"{pcode}: {field} is null; dimension breakdown incomplete")
        dim_rows.append(
            {
                "pcode": pcode,
                "state": lookup[pcode]["name_canonical"],
                "mpi_country": u["mpi_country"],
                "mpi": u["mpi"],
                "contrib_health_pct": u["contrib_health"],
                "contrib_education_pct": u["contrib_education"],
                "contrib_living_standards_pct": u["contrib_living_standards"],
                "population_thousands": u["population_thousands"],
                "mpi_poor_thousands": u["mpi_poor_thousands"],
                "pop_share_pct": u["pop_share_pct"],
                "n_indicators": u["n_indicators"],
                "indicators_missing": u["indicators_missing"],
                "survey": u["survey"],
                "survey_year": u["year"],
            }
        )

    n = write_csv(
        INTERIM / "mpi_dimensions.csv",
        dim_rows,
        [
            "pcode", "state", "mpi_country", "mpi",
            "contrib_health_pct", "contrib_education_pct", "contrib_living_standards_pct",
            "population_thousands", "mpi_poor_thousands", "pop_share_pct",
            "n_indicators", "indicators_missing", "survey", "survey_year",
        ],
    )
    write_csv(
        INTERIM / "mpi_trends.csv",
        trend_out,
        ["pcode", "state", "survey_year", "survey", "mpi", "headcount_ratio", "intensity"],
    )
    # Headline H/A come from the OPHI CSV (the UNDP contribution sheet does not
    # carry them). They are needed for the incidence x intensity quadrant.
    headline_rows = [
        {
            "pcode": pcode,
            "state": lookup[pcode]["name_canonical"],
            "mpi": headline[pcode]["mpi"],
            "headcount_ratio_pct": round(headline[pcode]["headcount_ratio"], 4),
            "intensity_pct": round(headline[pcode]["intensity"], 4),
            "vulnerable_pct": round(headline[pcode]["vulnerable"], 4),
            "severe_pct": round(headline[pcode]["severe"], 4),
            "survey": headline[pcode]["survey"],
            "survey_year": headline[pcode]["survey_year"],
        }
        for pcode in sorted(lookup)
    ]
    for key in ("headcount_ratio", "intensity", "vulnerable", "severe"):
        nulls = [r["state"] for r in headline_rows if r[f"{key}_pct"] is None]
        if nulls:
            raise SystemExit(f"{key} missing for {len(nulls)} state(s): {nulls[:5]}")
    write_csv(
        INTERIM / "mpi_headline.csv",
        headline_rows,
        ["pcode", "state", "mpi", "headcount_ratio_pct", "intensity_pct",
         "vulnerable_pct", "severe_pct", "survey", "survey_year"],
    )

    missing_inds = {r["indicators_missing"] for r in dim_rows if r["indicators_missing"]}
    uniform = len({r["indicators_missing"] for r in dim_rows}) == 1
    print(f"\nwrote {n} dimension rows -> data/interim/mpi_dimensions.csv")
    print("wrote 37 headline rows -> data/interim/mpi_headline.csv")
    print(f"wrote {len(trend_out)} trend rows -> data/interim/mpi_trends.csv")
    print(f"reconciliation: OPHI and UNDP agree on MPI for all {len(headline)} states (tol {TOLERANCE})")
    if missing_inds and uniform:
        # A uniform note is a country-wide exclusion, not a per-state gap: the MPI
        # is built from 9 indicators and Nutrition is one of them dropped nationwide.
        print(
            f"NOTE: every state reports the same excluded indicator {sorted(missing_inds)}, "
            f"on {int(dim_rows[0]['n_indicators'])} indicators. The Health dimension therefore rests "
            "on child mortality alone -- comparable across states, but narrower than the standard MPI."
        )
    elif missing_inds:
        partial = sorted(r["state"] for r in dim_rows if r["indicators_missing"])
        print(f"NOTE: {len(partial)} state(s) report a missing indicator -- Health is not comparable everywhere.")
    return 0


if __name__ == "__main__":
    sys.exit(main())