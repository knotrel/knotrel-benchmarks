#!/usr/bin/env python3
"""Part 2 of the v0.9.0 qualification, B4 feeder-events cells: descriptive, no verdict
(results/v0.9.0-qualification/PROTOCOL.md section 3).

Compares the six ``B4-http-events-*`` cells of Part 1 (http-lifecycle built against the
candidate) with the same cells of Part 2 (built against v0.8.0). Each cell is validated and
summarized with the frozen functions of ``analyze_lifecycle_qualification.py`` (``check_build``
and ``paired``: clean builds of the expected knotrel and probe revisions, 2 warmup and 12
balanced pairs, the cell's paired estimator against its own reference arm). The Part 2 run must
be the final profile restricted to ``--only B4`` with the frozen window multipliers.

Reported per cell and version: the reference-arm and lifecycle-arm median windows, the paired
median change and the status the estimator gives (as information; Part 2 decides nothing), and
the ratio of the two versions' lifecycle-arm medians. That ratio compares two runs of the same
session that are not paired, so it is descriptive only.

    compare_v090q_part2.py PART1_BC PART2_BC --cand-rev SHA --cand-probes-rev SHA \\
        --v080-rev SHA --v080-probes-rev SHA --expect-multipliers-sha256 SHA [--json OUT]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_lifecycle_qualification as frozen  # noqa: E402

EVENTS = (
    "B4-http-events-compact-bfs-sparse-10000",
    "B4-http-events-compact-bfs-hub-10000",
    "B4-http-events-compact-bfs-sparse-100000",
    "B4-http-events-equivalent-compact-bfs-sparse-10000",
    "B4-http-events-equivalent-compact-bfs-hub-10000",
    "B4-http-events-equivalent-compact-bfs-sparse-100000",
)


def cell_summary(run: Path, cell_id: str, rev: str, probes_rev: str) -> Dict[str, Any]:
    cells = {c["id"]: c for c in json.loads((run / "plan" / "matrix.json").read_text())}
    log = {r["id"]: r for r in frozen.lines(run / "run-log.jsonl")}
    cell, record = cells[cell_id], log.get(cell_id)
    if record is None or record["exit"] != 0 or "AC Power" not in record["host_before"]["power"]:
        raise frozen.Invalid(f"{run.name}/{cell_id}: missing, failed or not on AC power")
    records = frozen.lines(run / "raw" / f"{cell_id}.jsonl")
    frozen.check_build(cell, records, rev, probes_rev)
    s = frozen.paired(cell, records)
    return {"reference_median_ms": s["B_median"] / 1e6, "lifecycle_median_ms": s["C_median"] / 1e6,
            "median_change_pct": s.get("median_change_pct"), "interval_pct": s.get("interval_pct"),
            "estimator_status": s["status"], "tolerance": cell["tolerance"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("part1", type=Path)
    parser.add_argument("part2", type=Path)
    parser.add_argument("--cand-rev", required=True)
    parser.add_argument("--cand-probes-rev", required=True)
    parser.add_argument("--v080-rev", required=True)
    parser.add_argument("--v080-probes-rev", required=True)
    parser.add_argument("--expect-multipliers-sha256", required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    p2 = json.loads((args.part2 / "provenance.json").read_text())
    if (p2["profile"] != "final" or p2.get("only") != "B4" or not p2.get("equivalent_references")
            or p2.get("window_multipliers_sha256") != args.expect_multipliers_sha256
            or p2.get("lifecycle_engines") != "compact-bfs"):
        raise SystemExit("Part 2 B/C run is not the declared --only B4 final run")
    rows = []
    for cell_id in EVENTS:
        cand = cell_summary(args.part1, cell_id, args.cand_rev, args.cand_probes_rev)
        old = cell_summary(args.part2, cell_id, args.v080_rev, args.v080_probes_rev)
        rows.append({"id": cell_id, "role": "descriptive (no verdict)", "candidate": cand, "v0.8.0": old,
                     "lifecycle_median_ratio_candidate_over_v080": cand["lifecycle_median_ms"] / old["lifecycle_median_ms"]})
    out = {"part": 2, "kind": "B4 feeder events, candidate against v0.8.0", "verdict": None,
           "note": "cross-version ratios compare two unpaired runs of one session; descriptive only", "cells": rows}
    text = json.dumps(out, indent=1)
    if args.json:
        args.json.write_text(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
