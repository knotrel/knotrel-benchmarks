#!/usr/bin/env python3
"""Derives the frozen window multipliers for the v0.5.0 lifecycle qualification.

Reads a ``--profile pilot`` run of ``run_lifecycle_qualification.py`` and writes
``{cell id: factor}`` for every B1-B4 cell: the smallest power of two (at most 64) that
brings the *faster* arm's median pilot window to at least 2 ms. Only window durations are
used; no ratio or verdict is computed. Usage: ``derive_... PILOT_DIR OUT.json``.
"""

from __future__ import annotations

import json
import math
import statistics
import sys
from pathlib import Path

TARGET_NS = 2_000_000
CAP = 64


def factor(fastest_ns: float) -> int:
    if fastest_ns >= TARGET_NS:
        return 1
    return min(CAP, 2 ** math.ceil(math.log2(TARGET_NS / max(fastest_ns, 1.0))))


def main() -> int:
    pilot, out = Path(sys.argv[1]), Path(sys.argv[2])
    cells = json.loads((pilot / "plan" / "matrix.json").read_text())
    result = {}
    for cell in cells:
        if cell["experiment"] not in ("B1", "B2", "B3", "B4"):
            continue
        records = [json.loads(line) for line in (pilot / "raw" / f"{cell['id']}.jsonl").read_text().splitlines()]
        pairs = [r for r in records if r.get("kind") == "pair"]
        if not pairs:
            raise SystemExit(f"{cell['id']}: no pilot pairs")
        fastest = min(statistics.median(r["candidate_ns"] for r in pairs),
                      statistics.median(r["reference_ns"] for r in pairs))
        result[cell["id"]] = factor(fastest)
    out.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(f"{sum(f > 1 for f in result.values())} of {len(result)} cells scaled; "
          f"{sum(f == CAP for f in result.values())} at the cap", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
