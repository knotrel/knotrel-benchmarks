#!/usr/bin/env python3
"""Part 3 evaluation of the v0.9.0 qualification (results/v0.9.0-qualification/PROTOCOL.md 4).

Q1-Q4 are the load tool's own evaluation (``summary.json``, criteria of the approved protocol
knotrel docs/integrations/feeder-under-load.md, unchanged). Q5 compares L1 G100k with 16 and
64 clients against the protocol's v0.8.0 baseline summary, as for change A: median query
throughput >= 90 % and median client p99 <= 125 % of the baseline's. Deciding: Q1, Q2, Q4, Q5;
Q3 is the declared limitation of v0.9.0 and is reported as measured.

    evaluate_v090q_part3.py SUMMARY.json BASELINE-SUMMARY.json
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined  # noqa: E402

BASELINE_SHA256 = "bc6e8c094c84a0942d24e4095259d0153f595cb416388afd69392faccc7ef0e6"
DECIDING = ("Q1", "Q2", "Q4", "Q5")


def main(argv: list) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    summary_path, baseline_path = confined(argv[1], "summary"), confined(argv[2], "baseline")
    raw = baseline_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != BASELINE_SHA256:
        raise SystemExit("baseline summary differs from the approved protocol's")
    base = json.loads(raw)["summary"]["cells"]
    run = json.loads(summary_path.read_text())
    summary = run["summary"]
    criteria = dict(summary["criteria"])
    q5 = {"rule": "L1 G100k C=16 and C=64: median query_rps >= 90 % and median query_p99_ms <= 125 % of the v0.8.0 baseline",
          "cells": {}}
    ok = True
    for clients in (16, 64):
        key = f"L1 G100k C={clients}"
        cand, ref = summary["cells"][key], base[key]
        rps = cand["query_rps"]["median"] / ref["query_rps"]["median"]
        p99 = cand["query_p99_ms"]["median"] / ref["query_p99_ms"]["median"]
        cell_ok = rps >= 0.90 and p99 <= 1.25
        ok = ok and cell_ok
        q5["cells"][key] = {"query_rps": [ref["query_rps"]["median"], cand["query_rps"]["median"]],
                            "rps_ratio": rps, "query_p99_ms": [ref["query_p99_ms"]["median"],
                                                               cand["query_p99_ms"]["median"]],
                            "p99_ratio": p99, "pass": cell_ok}
    q5["pass"] = ok
    criteria["Q5"] = q5
    deciding = {q: bool(criteria[q]["pass"]) for q in DECIDING}
    out = {"measurement_secs": run.get("measurement_secs"), "criteria": criteria, "deciding": deciding,
           "part3_pass": all(deciding.values()),
           "Q3": {"status": "PASS" if criteria["Q3"]["pass"] else "FAIL",
                  "note": "declared limitation of v0.9.0 (maintainer decision 2026-11-21); reported as measured"}}
    print(json.dumps(out, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
