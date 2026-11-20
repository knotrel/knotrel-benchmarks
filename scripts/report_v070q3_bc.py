#!/usr/bin/env python3
"""Qualification 3 B/C decision view (PROTOCOL.md section 4.1).

Reads an ``analyze_lifecycle_qualification.py`` output (``BC-analysis.json``) and the
qualification-3 matrix, and lists every B/C result with its role: timing cells (B1-B4),
B5 memory and the C1-C4 sustained checks. Among B4 timing cells,
for the import, ops, ops-query and events families, the capability-equivalent cell
decides and its frozen counterpart is descriptive (no release verdict); every other
cell decides as before. Statuses are copied unchanged; nothing is recomputed.

Revision 2 (maintainer decision 2026-11-20, PROTOCOL section 4.3): an equivalent cell
whose reference cannot offer the candidate's atomicity is not equivalent. The matrix lists
those cells under ``not_equivalent`` (descriptive, no verdict) and the requirement they
would have qualified under ``unqualified_requirements``. A deciding equivalent cell whose
records show ``atomicity_equivalent: false`` is reported as ``NOT_EQUIVALENT`` among the
deciding non-PASS results (fail-closed); a listed cell whose records show equivalence is
reported as an inconsistency. Unqualified requirements are always listed.

    report_v070q3_bc.py BC-analysis.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-qualification-3" / "MATRIX.json"


#: Disclosure categories already defined by the frozen rules (not a failure).
DISCLOSURE = {"C4": {"EXCEEDS_BUDGET"}}


def label(analysis: dict, matrix: dict) -> list:
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    deciding, descriptive = set(eq["deciding"]), set(eq["descriptive"])
    not_equivalent = set(eq.get("not_equivalent", {}).get("cells", []))
    if deciding & (descriptive | not_equivalent) or descriptive & not_equivalent:
        raise SystemExit("a cell has more than one role in the matrix")
    rows = []
    ids = {cell["id"] for cell in analysis["timing"]}
    missing = (deciding | descriptive | not_equivalent) - ids
    if missing:
        raise SystemExit(f"cells missing from the analysis: {sorted(missing)}")
    for cell in analysis["timing"]:
        role = ("descriptive" if cell["id"] in descriptive
                else "not_equivalent" if cell["id"] in not_equivalent else "deciding")
        row = {"id": cell["id"], "kind": "timing", "role": role, "status": cell["status"],
               "median_change_pct": cell.get("median_change_pct"),
               "interval_pct": cell.get("interval_pct"), "tolerance_pct": cell.get("tolerance_pct")}
        if "atomicity_equivalent" in cell:
            row["atomicity_equivalent"] = cell["atomicity_equivalent"]
            row["reference_max_op_plain_ops"] = cell.get("reference_max_op_plain_ops")
            if role == "deciding" and cell["id"] in deciding and not cell["atomicity_equivalent"]:
                row["measured_status"], row["status"] = cell["status"], "NOT_EQUIVALENT"
        rows.append(row)
    for cell in analysis.get("memory", []):
        rows.append({"id": cell["id"], "kind": "B5", "role": "deciding", "status": cell["status"],
                     "lifecycle_over_plain": cell.get("lifecycle_over_plain")})
    for cell in analysis.get("sustained", []):
        for rule in ("C1", "C2", "C3", "C4"):
            if rule in cell:
                rows.append({"id": f"{cell['id']}:{rule}", "kind": rule, "role": "deciding", "status": cell[rule]})
    return rows


def non_pass(rows: list) -> list:
    """Deciding results that are neither PASS/IMPROVED nor a defined disclosure category."""
    return [r for r in rows if r["role"] == "deciding" and r["status"] not in ("PASS", "IMPROVED")
            and r["status"] not in DISCLOSURE.get(r["kind"], set())]


def inconsistencies(rows: list) -> list:
    """Cells listed as not equivalent whose records nevertheless show equivalence."""
    return [r["id"] for r in rows if r["role"] == "not_equivalent" and r.get("atomicity_equivalent") is True]


def main() -> int:
    analysis = json.loads(Path(sys.argv[1]).read_text())
    matrix = json.loads(MATRIX.read_text())
    rows = label(analysis, matrix)
    disclosures = [r for r in rows if r["status"] in DISCLOSURE.get(r["kind"], set())]
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    print(json.dumps({"rows": rows, "deciding_non_pass": non_pass(rows), "disclosures": disclosures,
                      "unqualified_requirements": eq.get("unqualified_requirements", []),
                      "not_equivalent_inconsistencies": inconsistencies(rows)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
