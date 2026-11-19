#!/usr/bin/env python3
"""Qualification 3 B/C decision view (PROTOCOL.md section 4.1).

Reads an ``analyze_lifecycle_qualification.py`` output (``BC-analysis.json``) and the
qualification-3 matrix, and lists every B/C result with its role: timing cells (B1-B4),
B5 memory and the C1-C4 sustained checks. Among B4 timing cells,
for the import, ops, ops-query and events families, the capability-equivalent cell
decides and its frozen counterpart is descriptive (no release verdict); every other
cell decides as before. Statuses are copied unchanged; nothing is recomputed.

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
    rows = []
    ids = {cell["id"] for cell in analysis["timing"]}
    missing = (deciding | descriptive) - ids
    if missing:
        raise SystemExit(f"cells missing from the analysis: {sorted(missing)}")
    for cell in analysis["timing"]:
        role = "descriptive" if cell["id"] in descriptive else "deciding"
        rows.append({"id": cell["id"], "kind": "timing", "role": role, "status": cell["status"],
                     "median_change_pct": cell.get("median_change_pct"),
                     "interval_pct": cell.get("interval_pct"), "tolerance_pct": cell.get("tolerance_pct")})
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


def main() -> int:
    analysis = json.loads(Path(sys.argv[1]).read_text())
    rows = label(analysis, json.loads(MATRIX.read_text()))
    disclosures = [r for r in rows if r["status"] in DISCLOSURE.get(r["kind"], set())]
    print(json.dumps({"rows": rows, "deciding_non_pass": non_pass(rows), "disclosures": disclosures}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
