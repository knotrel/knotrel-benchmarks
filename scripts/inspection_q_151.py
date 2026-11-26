#!/usr/bin/env python3
"""Inspection cost check Q of the knotrel#151 comparison (delegated collector).

    inspection_q_151.py --base-server S0 --cand-server S1 --base-checkout K0
                        --cand-checkout K1 --out DIR [--quick]

knotrel ``docs/design/compact-node-index.md``, section 6.4 (Q) and 6.7 (D5): each arm's
own, unchanged ``scripts/measure-inspection-costs.py`` (500 000 nodes, 1 500 000 edges,
one 20 000-neighbor hub; criteria C1-C4 of ``docs/console-inspection-costs.md``) runs
against that arm's ``knotrel-server``; CUR (base) is the reference, D5 needs C1-C4 on the
candidate. Writes ``DIR/q-base.json``, ``DIR/q-cand.json`` (the scripts' reports) and
``DIR/q.json``: ``{"base": criteria, "cand": criteria, "d5_pass": bool, "quick": bool,
"script_sha256": {...}}``. Exit 0 when both checks ran (the criteria are judged by the
analyzer), 1 otherwise. ``--quick`` (the script's reduced sizes) is for smoke runs only
and is recorded; the analyzer refuses a quick Q.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional


def run_check(checkout: Path, server: str, quick: bool) -> dict:
    script = checkout / "scripts" / "measure-inspection-costs.py"
    argv = [sys.executable, str(script), server] + (["--quick"] if quick else [])
    done = subprocess.run(argv, capture_output=True, text=True, check=True)
    return json.loads(done.stdout)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-server", required=True)
    parser.add_argument("--cand-server", required=True)
    parser.add_argument("--base-checkout", type=Path, required=True)
    parser.add_argument("--cand-checkout", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    summary = {"quick": args.quick, "script_sha256": {}}
    try:
        for arm, checkout, server in (("base", args.base_checkout, args.base_server),
                                      ("cand", args.cand_checkout, args.cand_server)):
            script = checkout / "scripts" / "measure-inspection-costs.py"
            summary["script_sha256"][arm] = hashlib.sha256(script.read_bytes()).hexdigest()
            report = run_check(checkout, server, args.quick)
            (args.out / f"q-{arm}.json").write_text(json.dumps(report, indent=1) + "\n")
            summary[arm] = report["criteria"]
    except (OSError, subprocess.CalledProcessError, ValueError, KeyError) as error:
        summary["error"] = str(error)
        (args.out / "q.json").write_text(json.dumps(summary, indent=1) + "\n")
        print(f"inspection_q_151: {error}", file=sys.stderr)
        return 1
    summary["d5_pass"] = all(summary["cand"].get(c) is True for c in ("C1", "C2", "C3", "C4"))
    (args.out / "q.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
