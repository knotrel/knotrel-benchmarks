#!/usr/bin/env python3
"""Collector for the declared v0.6.0 M_reg rerun (rerun-Mreg/PROTOCOL-MREG-RERUN.md).

Runs the two M_reg supplement cells with the frozen probe revision 2 binary and
the frozen campaign's servers, reusing the frozen recorder, host checks and pair
scheduling (``run_v060_qualification.py``) and the supplement's probe-revision
check. Before every child it also runs the host-activity check
(``host_activity_monitor.py --check``); a matching process stops the run.
Refuses to run unless ``FREEZE-MREG-RERUN.json`` exists (``--dry-run`` excepted)
and every binary matches the sha256 recorded in the rerun matrix.

    run_v060_mreg_rerun.py --out DIR [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_v060_m_supplement import checked_run  # noqa: E402
from run_v060_qualification import (  # noqa: E402
    Recorder, check_no_builds, paired_experiment, probe_argv, sha256, utc, write_configs,
)

RERUN = Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "supplement-M" / "rerun-Mreg"
MATRIX = RERUN / "MATRIX-MREG-RERUN.json"
FREEZE = RERUN / "FREEZE-MREG-RERUN.json"
MONITOR = Path(__file__).resolve().parent / "host_activity_monitor.py"


def activity_gate(rec: Recorder, label: str) -> None:
    proc = subprocess.run([sys.executable, str(MONITOR), "--check"], capture_output=True, text=True)
    if proc.returncode != 0:
        rec.log["stopped"] = f"activity gate before {label}: {proc.stdout.strip()[:500]}"
        rec.flush()
        raise SystemExit(rec.log["stopped"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text())
    if not args.dry_run and not FREEZE.exists():
        raise SystemExit("MATRIX-MREG-RERUN.json is not frozen (FREEZE-MREG-RERUN.json missing)")
    binaries = matrix["binaries"]
    for name, spec in binaries.items():
        actual = sha256(spec["path"])
        if actual != spec["sha256"]:
            raise SystemExit(f"{name}: sha256 {actual} does not match the declared {spec['sha256']}")
    meta = {"experiment": "M-reg-rerun", "pilot": False, "label": matrix["label"],
            "matrix_sha256": sha256(str(MATRIX)),
            "freeze_sha256": sha256(str(FREEZE)) if FREEZE.exists() else None,
            "binaries": {k: {"path": v["path"], "sha256": v["sha256"]} for k, v in binaries.items()}}
    if args.dry_run:
        print(json.dumps(meta, indent=1))
        return 0
    spec = matrix["M_reg_supplement"]
    servers = {"ref": binaries["ref"]["path"], "cand": binaries["cand"]["path"]}
    rec = Recorder(args.out, meta, enforce_host=True)
    check_no_builds()

    def run_cell(cell, arm, label):
        activity_gate(rec, label)
        path = write_configs([cell["config"]])
        checked_run(rec, label, probe_argv(binaries["probe"]["path"], servers[arm], cell["mode"], cell["lifecycle"],
                                           cell["nodes"], spec["seed"], path))

    paired_experiment(rec, spec["cells"], servers, spec["warmup_pairs"], spec["pairs"], spec["order_seed"], run_cell)
    rec.log["finished"] = utc()
    rec.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
