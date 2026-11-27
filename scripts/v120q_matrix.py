#!/usr/bin/env python3
"""Generates the v1.2.0 release-qualification matrix (knotrel#182).

    v120q_matrix.py [--out results/v1.2.0-qualification/v120q-matrix.json] [--cap-hours H]

Plan: knotrel ``docs/releases/v1.2.0-qualification-plan.md``. The scope comes from the
diff ``v1.1.0..candidate`` (plan section 3): the only executed change is
``Graph::connected`` (bidirectional BFS, knotrel#196), reached by every ``compact-bfs``
query (core plain engine, ``LifecycleGraph``, server, feeder deployment). The matrix uses
the CF5 schema (``cf5_matrix.py``), so ``run_cf5.py`` executes it and ``analyze_cf5.py``
classifies its paired cells:

- arm ``cf`` is the **candidate**, arm ``ref`` is **v1.1.0**; every paired cell is a
  ``regression`` check (PASS / REGRESSION / INCONCLUSIVE, with the CF5 section 6.1
  measurement limit), interval of ``ln(candidate / v1.1.0)``;
- V2: the six v1.0.0 M_reg cells with ``compact-bfs``, contention probe against the
  candidate server and the v1.1.0 server;
- K2: ``cf5-core staged`` with ``connectivity-compact-bfs`` (degrees 4 and 16, 10^4 to
  10^6 vertices), the same tool source built against each arm;
- K1: the connectivity harness families (CF5 K1 workloads, sizes and rounds) with
  ``connectivity-compact-bfs``, the same harness source built against each arm;
- delegated V1 (v1.0.0 A protocol, B = v1.1.0, C = candidate), Q (v1.0.0 block Q runner,
  Q5 reference on v1.1.0) and B4 (``--only B4`` with the equivalent and atomic
  references), with the B4 deciding, descriptive and atomic sets of plan section 4.2.

``--cap-hours`` records the budget (plan section 8), derived from the preparatory duration
trial before the freeze; without it the matrix carries a placeholder (``cap: unset``),
which ``freeze_v120q.py`` refuses. There is no second session. Tool keys are resolved by
``run_cf5.py`` from the campaign's tool map (``prepare_v120q.sh``), so the matrix holds no
machine paths.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cf5_matrix as cf5  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "results" / "v1.2.0-qualification" / "v120q-matrix.json"
PLAN = "knotrel docs/releases/v1.2.0-qualification-plan.md"
REFERENCE = "v1.1.0"
ENGINE = "compact-bfs"
ATOMIC_CELL = "B4-http-ops-atomic-compact-bfs-hub-10000"
K2_SIZES = (10_000, 100_000, 1_000_000)
K2_DEGREES = (4, 16)
B4_ORDER_SEED = 182400
V1_SEEDS = {"block1": [182110, 182111, 182112], "block2": [182120, 182121, 182122]}
Q_CAP_S = 45 * 60
PLACEHOLDER_CAP = 1_000


def v2() -> List[Dict[str, Any]]:
    cells = []
    for cell in cf5.v100_cells("M_reg"):
        cells.append(cf5.paired(f"V2-{cell['id']}", "V2", 1, None,
                                cf5.mreg_arm("contention_cand", cell, ENGINE),
                                cf5.mreg_arm("contention_base", cell, ENGINE), REFERENCE,
                                cf5.MREG_METRICS, rule="regression", check=cf5.MREG_CHECK))
    return cells


def k2() -> List[Dict[str, Any]]:
    engine = cf5.CONNECTIVITY[ENGINE]
    metrics = [cf5.metric("update_ns", "result.update_ns", "time",
                          measurement=cf5.measurement("aggregate", intervals=20)),
               cf5.metric("query_ns", "result.query_ns", "time",
                          measurement=cf5.measurement("aggregate", intervals=20))]
    cells = []
    for degree in K2_DEGREES:
        for vertices in K2_SIZES:
            def tool(name: str) -> Dict[str, Any]:
                return cf5.arm(name, ["staged", "--engine", engine, "--vertices", vertices,
                                      "--degree", degree, "--seed", cf5.SEED],
                               checks=cf5.engine_check("engine", engine))
            cells.append(cf5.paired(f"K2-d{degree}-{vertices}", "K2", 2, None,
                                    tool("cf5_core_cand"), tool("cf5_core_base"), REFERENCE,
                                    metrics, rule="regression",
                                    check={"same_trace": "edges_fingerprint"}))
    return cells


def k1() -> List[Dict[str, Any]]:
    engine = cf5.CONNECTIVITY[ENGINE]
    cells = []
    for workload in cf5.ONE_SHOT + cf5.SUSTAINED + cf5.DENSE:
        sizes = cf5.DENSE_SIZES if workload in cf5.DENSE else cf5.K1_SIZES
        rounds = 20 if workload in cf5.SUSTAINED else 100
        for nodes in sizes:
            def harness(name: str) -> Dict[str, Any]:
                return cf5.arm(name, ["--workload", workload, "--nodes", nodes, "--rounds",
                                      rounds, "--seed", cf5.SEED, "--engine", engine,
                                      "--warmup", 1, "--repetitions", 1],
                               checks=cf5.engine_check("engine", cf5.HARNESS_IDENTITY[ENGINE]))
            # Both arms are the CF5 harness source (calibrated gap ``harness``) built
            # against each knotrel checkout.
            cells.append(cf5.paired(f"K1-{workload}-{nodes}", "K1", 2, None,
                                    harness("harness_cand"), harness("harness_base"),
                                    REFERENCE,
                                    [cf5.metric("workload_wall_ns",
                                                "repetitions.0.workload_wall_ns", "time",
                                                measurement=cf5.wall(workload, "harness"))],
                                    rule="regression",
                                    check={"same_trace": "trace_fingerprint_fnv1a64"}))
    return cells


def b4_sets() -> Dict[str, List[str]]:
    """Deciding, descriptive and unqualified B4 cells (plan section 4.2)."""
    import run_lifecycle_qualification as rlq  # noqa: PLC0415
    v100 = json.loads(cf5.V100.read_text())["experiments"]["B_C"]["equivalent_references"]
    cells = [c["id"] for c in rlq.matrix("final", ENGINE, True, True)
             if c["experiment"] == "B4"]
    descriptive = set(v100["descriptive"]) | set(v100["not_equivalent"]["cells"])
    assert ATOMIC_CELL in cells, "the atomic reference cell is in the B4 scope"
    assert descriptive <= set(cells), "every v1.0.0 descriptive cell is in the B4 scope"
    return {"all": cells,
            "deciding": [c for c in cells if c not in descriptive],
            "descriptive": [c for c in cells if c in descriptive],
            "unqualified": ["B4-http-ops-compact-bfs-hub-10000",
                            "B4-http-events-compact-bfs-hub-10000",
                            *v100["not_equivalent"]["cells"]],
            "atomic": [ATOMIC_CELL]}


def delegated() -> List[Dict[str, Any]]:
    # Commands: results/v1.2.0-qualification/prepare_v120q.sh (tool map ``_delegated``).
    sets = b4_sets()
    return [
        {"id": "V1", "block": "V1", "tier": 1, "kind": "delegated", "comparisons": 9,
         "seeds": V1_SEEDS,
         "collector": "run_p0_aa.py --execute on the two plans of prepare_bc_qualification.py "
                      "(B = v1.1.0, C = candidate), n = 24 fixed; analyze_v100q_a.py rules"},
        {"id": "Q", "block": "Q", "tier": 2, "kind": "delegated", "comparisons": 5,
         "cap_s": Q_CAP_S,
         "collector": "run_q.sh (Docker Desktop and the pinned PostgreSQL 18.7 container exist "
                      "only while Q runs, URL never written) -> run_v100q_q.py (candidate: seven "
                      "cells on the candidate server; Q5 reference: L1 G100k C=16 and C=64 on "
                      "the v1.1.0 server; 3 rounds) -> evaluate_v100q_q.py: Q1-Q5"},
        {"id": "B4", "block": "B4", "tier": 2, "kind": "delegated",
         "comparisons": len(sets["all"]), "order_seed": B4_ORDER_SEED, "b4": sets,
         "collector": "run_lifecycle_qualification.py --profile final --only B4 "
                      "--lifecycle-engines compact-bfs --equivalent-references "
                      "--atomic-references --window-multipliers "
                      "results/v1.2.0-qualification/window-multipliers.json; "
                      "analyze_lifecycle_qualification.py --expect-only B4"},
    ]


def window_multipliers() -> Dict[str, int]:
    """The frozen v1.0.0 B4 factors plus the atomic cell's (its ``ops`` hub counterpart's)."""
    frozen = json.loads((ROOT / "results" / "v1.0.0-qualification"
                         / "window-multipliers-q3.json").read_text())
    sets = b4_sets()
    factors = {c: int(frozen[c]) for c in sets["all"] if c != ATOMIC_CELL}
    factors[ATOMIC_CELL] = int(frozen["B4-http-ops-compact-bfs-hub-10000"])
    assert set(factors) == set(sets["all"])
    return dict(sorted(factors.items()))


def build(cap_hours: Optional[float] = None) -> Dict[str, Any]:
    if cap_hours is not None and not 0 < cap_hours < PLACEHOLDER_CAP:
        raise SystemExit(f"--cap-hours must be in (0, {PLACEHOLDER_CAP}), got {cap_hours}")
    cells = v2() + k2() + k1() + delegated()
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids)), "cell ids are unique"
    counts: Dict[str, int] = {}
    for cell in cells:
        counts[cell["block"]] = counts.get(cell["block"], 0) + cell.get("comparisons", 1)
    return {
        "schema": "cf5-matrix-1",
        "plan": PLAN,
        "reference": REFERENCE,
        "cap": "set" if cap_hours is not None else "unset",
        "rules": {"pairs": 24, "warmup_pairs": 2, "interval_order_statistics": [7, 18],
                  "coverage": 0.9773, "margins": cf5.MARGINS,
                  "cap_hours": cap_hours if cap_hours is not None else PLACEHOLDER_CAP,
                  "second_session_cap_hours": 0,
                  "measurement_limit": {"calibration": str(cf5.CALIBRATION.relative_to(ROOT)),
                                        "tick_ns": cf5.TICK_NS,
                                        "clock_read_ns": cf5.CLOCK_READ_NS,
                                        "harness_gap_ns": cf5.HARNESS_GAP_NS},
                  "tiers": [1, 2],
                  # Priority order of blocks within each tier (plan section 8).
                  "block_order": [["V1", "V2"], ["Q", "B4", "K2", "K1"]]},
        "counts": dict(sorted(counts.items())),
        "total_comparisons": sum(counts.values()),
        "cells": cells,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--cap-hours", type=float)
    parser.add_argument("--window-multipliers", type=Path,
                        help="also write the B4 window multipliers (plan section 4.2) here")
    args = parser.parse_args(argv)
    from cli_paths import confined  # noqa: PLC0415
    out = confined(args.out, "--out")
    matrix = build(float(args.cap_hours) if args.cap_hours is not None else None)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(matrix, indent=1, sort_keys=True) + "\n")
    if args.window_multipliers:
        wm = confined(args.window_multipliers, "--window-multipliers")
        wm.write_text(json.dumps(window_multipliers(), indent=1) + "\n")
    print(json.dumps({"out": str(out), "counts": matrix["counts"],
                      "total": matrix["total_comparisons"], "cap": matrix["cap"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
