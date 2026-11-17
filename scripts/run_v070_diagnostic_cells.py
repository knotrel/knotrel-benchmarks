#!/usr/bin/env python3
"""Collector for v0.7.0 in-process diagnostics (``MATRIX-DIAG-Db.json``).

Runs paired R cells (``release-cells``, fresh process per observation,
balanced order) and deterministic Rmem cells (``memory-peak``, one run per
arm) with the frozen v0.6.0 recorder, host checks and pair scheduling, plus
the host-activity gate before every child. Refuses to run unless every
binary matches the sha256 declared in the matrix. Diagnostic only.

    run_v070_diagnostic_cells.py --matrix FILE --out DIR [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_v060_qualification import Recorder, check_no_builds, paired_experiment, sha256, utc  # noqa: E402
from run_v070_diagnostic_probe import activity_gate  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    for tool, arms in matrix["binaries"].items():
        for arm, spec in arms.items():
            actual = sha256(spec["path"])
            if actual != spec["sha256"]:
                raise SystemExit(f"{tool}/{arm}: sha256 {actual} does not match {spec['sha256']}")
    meta = {"experiment": matrix["schema"], "label": matrix["label"], "matrix_sha256": sha256(str(args.matrix)),
            "binaries": matrix["binaries"]}
    if args.dry_run:
        print(json.dumps(meta, indent=1))
        return 0
    rec = Recorder(args.out, meta, enforce_host=True)
    check_no_builds()
    r_bins = {arm: spec["path"] for arm, spec in matrix["binaries"]["R"].items()}

    def run_cell(cell, arm, label):
        activity_gate(rec, label)
        rec.run(label, [r_bins[arm]] + cell["args"])

    spec = matrix["R"]
    paired_experiment(rec, spec["cells"], r_bins, spec["warmup_pairs"], spec["pairs"], spec["order_seed"], run_cell)
    for cell in matrix["Rmem"]["cells"]:
        for arm, binary in matrix["binaries"]["Rmem"].items():
            label = f"{cell['id']}-{arm}"
            activity_gate(rec, label)
            rec.run(label, [binary["path"]] + cell["args"])
    rec.log["finished"] = utc()
    rec.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
