#!/usr/bin/env python3
"""Collector for v0.7.0 contention diagnostics (``MATRIX-DIAG-*.json``).

Diagnostics decide retain/reject of a v0.7.0 candidate only; they never
replace a qualification verdict. Reuses the frozen v0.6.0 recorder, host
checks (AC power, no thermal warning) and pair scheduling, and the M_reg
rerun's host-activity gate before every child. Refuses to run unless every
binary matches the sha256 declared in the matrix.

    run_v070_diagnostic_probe.py --matrix FILE --out DIR [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_v060_qualification import (  # noqa: E402
    Recorder, check_no_builds, paired_experiment, probe_argv, sha256, utc, write_configs,
)

MONITOR = Path(__file__).resolve().parent / "host_activity_monitor.py"


def activity_gate(rec: Recorder, label: str) -> None:
    proc = subprocess.run([sys.executable, str(MONITOR), "--check"], capture_output=True, text=True)
    if proc.returncode != 0:
        rec.log["stopped"] = f"activity gate before {label}: {proc.stdout.strip()[:500]}"
        rec.flush()
        raise SystemExit(rec.log["stopped"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(args.matrix.read_text())
    binaries = matrix["binaries"]
    for name, spec in binaries.items():
        actual = sha256(spec["path"])
        if actual != spec["sha256"]:
            raise SystemExit(f"{name}: sha256 {actual} does not match the declared {spec['sha256']}")
    meta = {"experiment": matrix["schema"], "label": matrix["label"], "matrix_sha256": sha256(str(args.matrix)),
            "binaries": binaries}
    if args.dry_run:
        print(json.dumps(meta, indent=1))
        return 0
    design = matrix["design"]
    servers = {"ref": binaries["ref"]["path"], "cand": binaries["cand"]["path"]}
    rec = Recorder(args.out, meta, enforce_host=True)
    check_no_builds()

    def run_cell(cell, arm, label):
        activity_gate(rec, label)
        path = write_configs([cell["config"]])
        rec.run(label, probe_argv(binaries["probe"]["path"], servers[arm], cell["mode"], cell["lifecycle"],
                                  cell["nodes"], design["seed"], path))

    paired_experiment(rec, matrix["cells"], servers, design["warmup_pairs"], design["pairs"],
                      design["order_seed"], run_cell)
    rec.log["finished"] = utc()
    rec.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
