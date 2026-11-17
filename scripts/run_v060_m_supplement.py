#!/usr/bin/env python3
"""Collector for the declared v0.6.0 supplementary contention run (M supplement).

Reads ``results/v0.6.0-qualification/supplement-M/MATRIX-M-SUPPLEMENT.json`` and
refuses to run unless ``FREEZE-M-SUPPLEMENT.json`` exists next to it
(``--dry-run`` excepted). It reuses the frozen collector's recorder, host checks,
probe arguments and pair scheduling unchanged (``run_v060_qualification.py``),
and checks that every probe run reports probe revision 2.

Usage (from the knotrel-benchmarks root)::

    run_v060_m_supplement.py mdesc --out DIR --probe BIN --server BIN
    run_v060_m_supplement.py mreg  --out DIR --probe BIN --ref BIN --cand BIN
        [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_v060_qualification import (  # noqa: E402
    Recorder, check_no_builds, last_json, paired_experiment, probe_argv, sha256, utc, write_configs,
)

SUPPLEMENT = Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "supplement-M"
MATRIX = SUPPLEMENT / "MATRIX-M-SUPPLEMENT.json"
FREEZE = SUPPLEMENT / "FREEZE-M-SUPPLEMENT.json"
PROBE_REVISION = 2


def checked_run(rec: Recorder, label: str, argv) -> str:
    stdout = rec.run(label, argv)
    start = last_json(stdout.splitlines()[0] + "\n", "start")
    if start.get("probe_revision") != PROBE_REVISION:
        rec.log["stopped"] = f"{label}: probe revision {start.get('probe_revision')}, expected {PROBE_REVISION}"
        rec.flush()
        raise SystemExit(rec.log["stopped"])
    return stdout


def cmd_mdesc(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["M_desc_supplement"]
    check_no_builds()
    for server in spec["servers"]:
        path = write_configs(server["configs"])
        (rec.out / f"{server['id']}.configs.jsonl").write_text(Path(path).read_text())
        checked_run(rec, server["id"], probe_argv(args.probe, args.server, server["mode"], server["lifecycle"],
                                                  server["nodes"], spec["seed"], path))


def cmd_mreg(args: argparse.Namespace, matrix: Dict[str, Any], rec: Recorder) -> None:
    spec = matrix["M_reg_supplement"]
    servers = {"ref": args.ref, "cand": args.cand}
    check_no_builds()

    def run_cell(cell, arm, label):
        path = write_configs([cell["config"]])
        checked_run(rec, label, probe_argv(args.probe, servers[arm], cell["mode"], cell["lifecycle"],
                                           cell["nodes"], spec["seed"], path))

    paired_experiment(rec, spec["cells"], servers, spec["warmup_pairs"], spec["pairs"], spec["order_seed"], run_cell)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("experiment", choices=["mdesc", "mreg"])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--ref")
    parser.add_argument("--cand")
    parser.add_argument("--probe", required=True)
    parser.add_argument("--server")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text())
    if not args.dry_run and not FREEZE.exists():
        raise SystemExit("MATRIX-M-SUPPLEMENT.json is not frozen (FREEZE-M-SUPPLEMENT.json missing)")
    binaries = {k: getattr(args, k) for k in ("ref", "cand", "probe", "server") if getattr(args, k)}
    meta = {"experiment": f"M-supplement-{args.experiment}", "pilot": False, "label": matrix["label"],
            "matrix_sha256": sha256(str(MATRIX)),
            "freeze_sha256": sha256(str(FREEZE)) if FREEZE.exists() else None,
            "binaries": {k: {"path": v, "sha256": sha256(v)} for k, v in binaries.items()}}
    if args.dry_run:
        print(json.dumps(meta, indent=1))
        return 0
    rec = Recorder(args.out, meta, enforce_host=True)
    {"mdesc": cmd_mdesc, "mreg": cmd_mreg}[args.experiment](args, matrix, rec)
    rec.log["finished"] = utc()
    rec.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
