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

Revision 2 also adds check T5 (compaction pauses, ``analyze_v070q3_t5.py`` output): its six
results are deciding rows of kind ``T5``, statuses copied unchanged. ``qualification_scope``
states that the qualification cannot be complete while any requirement is unqualified,
whatever the statuses (maintainer decision 2026-11-20): unqualified requirements never
disappear from the verdict.

    report_v070q3_bc.py BC-analysis.json T5-analysis.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.7.0-qualification-3" / "MATRIX.json"


#: Planner-based equivalent cells: their reference's atomicity must be recorded.
PLANNER_EQUIVALENT = re.compile(r"-(ops|ops-query|events)-equivalent-")

T5_IDS = {f"T5-{m}-{t}" for m in ("P_max", "P_90") for t in ("sparse", "ring", "hub")}

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
        planner_equivalent = PLANNER_EQUIVALENT.search(cell["id"]) is not None
        if planner_equivalent and cell["id"] in (deciding | not_equivalent) and "atomicity_equivalent" not in cell:
            raise SystemExit(f"{cell['id']}: planner equivalent cell without atomicity record (fail-closed)")
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


def t5_rows(t5: dict) -> list:
    """The six T5 results as deciding rows (statuses copied, absolute values kept).

    An analysis that ended invalid (``invalid`` marker) gives six INVALID deciding rows."""
    if t5.get("check") != "T5":
        raise SystemExit("not a T5 analysis")
    if "invalid" in t5:
        return [{"id": i, "kind": "T5", "role": "deciding", "status": "INVALID", "reason": t5["invalid"]}
                for i in sorted(T5_IDS)]
    if sorted(r["id"] for r in t5.get("results", [])) != sorted(T5_IDS):
        raise SystemExit("T5 analysis incomplete: the six results T5-{P_max,P_90}-{sparse,ring,hub} are required")
    return [{"id": r["id"], "kind": "T5", "role": "deciding", "status": r["status"],
             "median_change_pct": r.get("median_change_pct"), "interval_pct": r.get("interval_pct"),
             "tolerance_pct": r.get("tolerance_pct"), "absolute_ms": r.get("absolute_ms")}
            for r in t5["results"]]


def overall(rows: list, unqualified: list) -> dict:
    """The overall verdict of the decision view. Conformance is established separately
    (logs/CONFORMANCE.txt); this view never supports a release while a requirement is
    unqualified or a deciding result is not PASS."""
    failing = non_pass(rows)
    return {"deciding_all_pass": not failing,
            "qualification_complete": not unqualified,
            "release_supported_by_q3": not failing and not unqualified,
            "unqualified_requirements": [u.get("requirement", u) if isinstance(u, dict) else u for u in unqualified],
            "note": "requires also a CONFORMING attempt; unqualified requirements stay in this verdict"}


def scope(unqualified: list) -> dict:
    """Whether q3 can qualify every release requirement (never, while any is unqualified)."""
    return {"complete": not unqualified,
            "unqualified_requirements": len(unqualified),
            "note": ("every requirement is in scope" if not unqualified else
                     "incomplete: the listed requirements are not qualified by q3; no outcome of the "
                     "deciding results makes the qualification complete or removes them from the verdict")}


def non_pass(rows: list) -> list:
    """Deciding results that are neither PASS/IMPROVED nor a defined disclosure category."""
    return [r for r in rows if r["role"] == "deciding" and r["status"] not in ("PASS", "IMPROVED")
            and r["status"] not in DISCLOSURE.get(r["kind"], set())]


def inconsistencies(rows: list) -> list:
    """Cells listed as not equivalent whose records nevertheless show equivalence."""
    return [r["id"] for r in rows if r["role"] == "not_equivalent" and r.get("atomicity_equivalent") is True]


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    analysis = json.loads(Path(sys.argv[1]).read_text())
    matrix = json.loads(MATRIX.read_text())
    rows = label(analysis, matrix) + t5_rows(json.loads(Path(sys.argv[2]).read_text()))
    disclosures = [r for r in rows if r["status"] in DISCLOSURE.get(r["kind"], set())]
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    unqualified = eq["unqualified_requirements"]
    if len(unqualified) < len(eq["not_equivalent"]["cells"]):
        raise SystemExit("fewer unqualified requirements than not-equivalent cells")
    print(json.dumps({"rows": rows, "deciding_non_pass": non_pass(rows), "disclosures": disclosures,
                      "unqualified_requirements": unqualified,
                      "qualification_scope": scope(unqualified),
                      "overall": overall(rows, unqualified),
                      "not_equivalent_inconsistencies": inconsistencies(rows)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
