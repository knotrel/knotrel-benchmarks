#!/usr/bin/env python3
"""Experiment A of the v1.0.0 qualification: fixed n = 24, no interim look.

Plan (knotrel ``docs/releases/v1.0.0-qualification-plan.md`` section 5.3, option a, approved
by the maintainer 2026-11-23): every A cell runs 24 pairs in two blocks of 12 (block 1 with
the session seeds, block 2 with the extension seeds); both blocks always run for all nine
cells; nothing is analyzed between them; the analyzer runs once, on all 24 pairs.

The frozen analyzer ``analyze_bc_qualification.py`` implements the v0.9.0 two-stage design: its
``analyze`` computes the n = 12 decision and requires the extension cells to equal the cells it
found INCONCLUSIVE. That interim decision is exactly what option (a) removes, so this module
does not call ``analyze``. It reuses, unchanged, every other frozen piece with rule set
``v0.4.0``:

- ``load_pairs`` with the frozen input checks of each block (block 1 is a ``main`` phase raw
  directory, block 2 an ``extension`` phase one: the plan generator's two phase names, with
  their own manifests and session seeds);
- the approved nine cells (``QUALIFICATION_CELL_IDS``) in **both** blocks, 12 pairs per cell
  per block, each block balanced by ``_check_design`` (two B->C and two C->B pairs per
  session and cell);
- ``_check_consistency`` over both blocks (identities, fingerprints, one timeline), and block
  2 launched after block 1 completed;
- ``evaluate_cell(..., final=True)`` on the 24 pairs of each cell: the frozen interval
  ``[r(7), r(18)]`` (``summarize_metric``, ``INTERVAL_RANKS[24]``), tolerances, report-only
  metrics and final classes (PASS, REGRESSION, INCONCLUSIVE_DISCLOSED, UNRESOLVED).

The 24 pairs of a cell form one sample: the block is recorded per pair (``phase``) but is not
a stratum and is not weighted. No n = 12 decision is computed or written.

    analyze_v100q_a.py --block1 A/raw-main --block2 A/extension/raw-extension --output OUT.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import analyze_bc_qualification as frozen  # noqa: E402

RULES = "v0.4.0"
PAIRS_PER_BLOCK = frozen.MAIN_PAIRS_PER_CELL  # 12
PAIRS_PER_CELL = 2 * PAIRS_PER_BLOCK  # 24
INTERVAL_RANKS = frozen.INTERVAL_RANKS[PAIRS_PER_CELL]  # (7, 18)


def coverage(n: int, k: int) -> float:
    """Coverage of the order-statistic interval ``[r(k), r(n+1-k)]`` for the median of ``n``
    independent continuous observations: ``1 - 2 P(Bin(n, 1/2) <= k - 1)``."""
    tail = sum(math.comb(n, i) for i in range(k)) / 2 ** n
    return 1.0 - 2.0 * tail


def _block(pairs: List[Dict[str, Any]], name: str) -> Dict[str, List[Dict[str, Any]]]:
    """The block's pairs by cell: the approved nine cells, 12 balanced pairs each."""
    cells = frozen._group(pairs)
    if sorted(cells) != sorted(frozen.QUALIFICATION_CELL_IDS):
        raise frozen.AnalysisError(f"{name} cells {sorted(cells)} are not the approved nine "
                                   f"{sorted(frozen.QUALIFICATION_CELL_IDS)}")
    for cell_id, cell_pairs in cells.items():
        if len(cell_pairs) != PAIRS_PER_BLOCK:
            raise frozen.AnalysisError(f"{name} {cell_id}: {len(cell_pairs)} pairs, expected {PAIRS_PER_BLOCK}")
    frozen._check_design(cells, name)
    return cells


def analyze(block1: Path, block2: Path) -> Dict[str, Any]:
    """The final A decision on 24 pairs per cell; raises ``AnalysisError`` on any problem."""
    if Path(block1).resolve() == Path(block2).resolve():
        raise frozen.AnalysisError("block 2 is the block 1 directory")
    first = frozen.load_pairs(block1, "main")
    second = frozen.load_pairs(block2, "extension")
    if min(min(p["launches"]) for p in second) <= max(max(p["completions"]) for p in first):
        raise frozen.AnalysisError("block 2 observations were launched before block 1 ended")
    frozen._check_consistency(first + second)
    cells1 = _block(first, "block1")
    cells2 = _block(second, "block2")
    cells = []
    for cell_id in sorted(frozen.QUALIFICATION_CELL_IDS):
        pairs = list(cells1[cell_id]) + list(cells2[cell_id])
        decision = frozen.evaluate_cell(cell_id, pairs, RULES, final=True)
        if decision["pairs"] != PAIRS_PER_CELL:
            raise frozen.AnalysisError(f"{cell_id}: {decision['pairs']} pairs, expected {PAIRS_PER_CELL}")
        decision.pop("extension_required", None)
        decision.pop("extension_disposition", None)
        decision["blocks"] = {"block1": len(cells1[cell_id]), "block2": len(cells2[cell_id])}
        cells.append(decision)
    low, high = INTERVAL_RANKS
    return {
        "analysis": "knotrel-v1.0.0-qualification-A",
        "design": "fixed n = 24 per cell in two blocks of 12, no interim look (plan section 5.3, option a)",
        "rules": RULES,
        "interval_definition": f"paired log ratios ln(C/B); one-based order statistics n=24 r({low}),r({high})",
        "interval_coverage": coverage(PAIRS_PER_CELL, low),
        "tolerances": frozen.TOLERANCES,
        "pairs_per_cell": PAIRS_PER_CELL,
        "pairs": len(first) + len(second),
        "report_only": {"reason": frozen.REPORT_ONLY_REASON,
                        "metrics_by_cell": {c: list(m) for c, m in frozen.REPORT_ONLY.items()}},
        "inputs": {"script_sha256": frozen._sha256(Path(__file__).read_bytes()),
                   "frozen_analyzer_sha256": frozen._sha256(Path(frozen.__file__).read_bytes()),
                   "block1": frozen._inputs_digest(first, block1, "main"),
                   "block2": frozen._inputs_digest(second, block2, "extension")},
        "phase": "final",
        "cells": cells,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--block1", type=Path, required=True, help="Block 1 raw directory (A/raw-main).")
    parser.add_argument("--block2", type=Path, required=True, help="Block 2 raw directory (A/extension/raw-extension).")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON file (must not exist).")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error(f"{args.output} already exists")
    if not args.output.parent.is_dir():
        parser.error(f"{args.output.parent} is not a directory")
    try:
        report = analyze(args.block1, args.block2)
    except frozen.AnalysisError as error:
        print(f"analysis refused: {error}", file=sys.stderr)
        return 2
    except (TypeError, AttributeError, KeyError, ValueError, ArithmeticError, RecursionError) as error:
        print(f"analysis refused: malformed input ({type(error).__name__}: {error})", file=sys.stderr)
        return 2
    try:
        text = json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n"
    except ValueError as error:
        print(f"analysis refused: non-finite value in the report ({error})", file=sys.stderr)
        return 2
    with args.output.open("x") as handle:
        handle.write(text)
    print("final decision (v0.4.0, n = 24): " + ", ".join(f"{c['cell_id']}={c['status']}" for c in report["cells"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
