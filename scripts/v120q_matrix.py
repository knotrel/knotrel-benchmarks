#!/usr/bin/env python3
"""Generates the v1.2.0 release-qualification matrix (knotrel#182).

    v120q_matrix.py [--out results/v1.2.0-qualification/v120q-matrix.json] [--cap-hours H]
    v120q_matrix.py --attempt 2 [--out results/v1.2.0-qualification/attempt2/v120q-matrix.json]
                    [--cap-hours H]

**Attempt 2** (plan section 13) qualifies the candidate after the BFS restore (knotrel#205)
and B2 (knotrel#207). Its diff against v1.1.0 changes no executed core code and changes the
server's request path (the optional query limiter, unset by default), so the matrix keeps
the server blocks and drops K1 and K2 (written dispositions):

- V2 unchanged (default mode);
- V1 unchanged as a protocol (its fixed nine cells), with the five HTTP cells deciding and
  the four core cells descriptive (their executed code equals v1.1.0);
- Q in the default mode (cell ``Q``: Q1, Q2, Q4 and Q5 deciding; Q3 reported) and with
  ``KNOTREL_MAX_CONCURRENT_QUERIES=4`` (cell ``Q-K4``: Q1-Q4 deciding, Q3 being the
  release's Q3 statement; Q5 published as the option's cost), the rule the maintainer
  approved for B2 (design option B);
- B4 unchanged.

**Attempt 3** (plan section 14) qualifies ``main`` at 24c2602: attempt 2's candidate plus
knotrel#209 (bidirectional ``Graph::connected``), #210 (FxHash ID maps in every engine) and
#211 (per-thread reused query scratch, at most 256 KiB per thread). The matrix keeps the
attempt-2 blocks, brings K1 and K2 back, makes the four V1 core cells deciding again, and adds:

- K3: query shapes (short and long, connected and disconnected, chains and cycles) at 1 and
  16 threads, ``query-shape-probe shape`` built against each arm; p50 (10 %) and p99 (25 %);
- K4: the five engines #210 touches x ID patterns ``sequential``, ``random``, ``shl16``,
  ``shl32`` (harness ``--id-pattern``), ``workload_wall_ns`` 10 %, 300 s per observation;
- M1: ``query-shape-probe sequence --kind large-then-small`` at 16 and 64 threads: retained
  scratch per thread <= 256 KiB and no allocation per short query (absolute, on the
  candidate), small-query p50 / p99 (regression);
- M2: ``contention-probe --prelude long-chain:600000``, read95 b8, 15 s window, 16 and 64
  clients: throughput 10 %, p99 25 %, server RSS after the window 20 %.

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
#: Attempt 2 (plan section 13): fresh seeds, declared before the freeze.
V1_SEEDS_A2 = {"block1": [182210, 182211, 182212], "block2": [182220, 182221, 182222]}
V1_HTTP_CELLS = ["http_standalone_batch_b1_compact_bfs", "http_standalone_batch_b8_compact_bfs",
                 "http_standalone_batch_b64_compact_bfs", "http_standalone_batch_b256_compact_bfs",
                 "http_lifecycle_compact_bfs_small"]
V1_CORE_CELLS = ["core_sparse_traversal_10k_compact-bfs_warmed",
                 "core_sparse_traversal_10k_compact-workspace_warmed",
                 "core_sustained_churn_10k_compact-bfs_warmed",
                 "core_sustained_churn_10k_compact-workspace_warmed"]
#: Attempt 3 (plan section 14.4): fresh seeds, declared before the freeze.
V1_SEEDS_A3 = {"block1": [182310, 182311, 182312], "block2": [182320, 182321, 182322]}
K3_SHAPES = ("s1", "s2", "l1", "l2", "l3")
K3_THREADS = (1, 16)
K3_VERTICES = 100_000
M1_THREADS = (16, 64)
M1_CHAIN = 1_000_000
M1_SMALL_QUERIES = 10_000
#: The reused-scratch cap of knotrel#211 (bytes per thread).
SCRATCH_CAP_BYTES = 256 * 1024
K4_ENGINES = {"connectivity-compact-bfs": "knotrel-core/connectivity-graph/compact-bfs",
              "compact-workspace": "knotrel-core/compact-workspace-v2",
              "connectivity-ett": "knotrel-core/connectivity-graph/ett",
              "connectivity-hdt": "knotrel-core/connectivity-graph/hdt",
              "connectivity-cluster-forest": "knotrel-core/connectivity-graph/cluster-forest-v1"}
K4_PATTERNS = ("sequential", "random", "shl16", "shl32")
K4_WORKLOAD = "sustained-churn-blocks-v1"
K4_TIMEOUT_S = 300
M2_CLIENTS = (16, 64)
M2_CHAIN = 600_000
MIN_FREE_DISK_GB = 2
Q_LIMIT = 4
#: Attempt 2 Q rule (B2 design option B, approved by the maintainer; plan section 13).
Q_RULES_A2 = {
    "Q": {"mode": "default (KNOTREL_MAX_CONCURRENT_QUERIES unset)",
          "deciding": ["Q1", "Q2", "Q4", "Q5"], "reported": ["Q3"], "cost": []},
    "Q-K4": {"mode": f"KNOTREL_MAX_CONCURRENT_QUERIES={Q_LIMIT}",
             "deciding": ["Q1", "Q2", "Q3", "Q4"], "reported": [], "cost": ["Q5"]},
}
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


def delegated_a2() -> List[Dict[str, Any]]:
    """Attempt 2's delegated cells (plan section 13). ``Q-K4`` runs the same collector against
    the campaign's server variant ``variant-k4`` (prepare_v120q.sh)."""
    sets = b4_sets()
    q_collector = ("run_q.sh (Docker Desktop and the pinned PostgreSQL 18.7 container exist "
                   "only while Q runs, URL never written) -> run_v100q_q.py (candidate: seven "
                   "cells on the candidate server{variant}; Q5 reference: L1 G100k C=16 and "
                   "C=64 on the v1.1.0 server; 3 rounds) -> evaluate_v100q_q.py: Q1-Q5; exit 6 "
                   "(evaluation failed after the measurement) is a tool error, never a verdict")
    assert sorted(V1_HTTP_CELLS + V1_CORE_CELLS) == sorted(_v1_cell_ids())
    return [
        {"id": "V1", "block": "V1", "tier": 1, "kind": "delegated", "comparisons": 9,
         "seeds": V1_SEEDS_A2,
         "v1": {"deciding": V1_HTTP_CELLS, "descriptive": V1_CORE_CELLS,
                "descriptive_reason": "executed core code equal to v1.1.0 (diff of plan section 13)"},
         "collector": "run_p0_aa.py --execute on the two plans of prepare_bc_qualification.py "
                      "(B = v1.1.0, C = candidate), n = 24 fixed; analyze_v100q_a.py rules"},
        {"id": "Q", "block": "Q", "tier": 2, "kind": "delegated", "comparisons": 5,
         "cap_s": Q_CAP_S, "q_rule": Q_RULES_A2["Q"],
         "collector": q_collector.format(variant="")},
        {"id": "Q-K4", "block": "Q", "tier": 2, "kind": "delegated", "comparisons": 5,
         "cap_s": Q_CAP_S, "q_rule": Q_RULES_A2["Q-K4"],
         "collector": q_collector.format(
             variant=f" started with KNOTREL_MAX_CONCURRENT_QUERIES={Q_LIMIT} (variant-k4)")},
        {"id": "B4", "block": "B4", "tier": 2, "kind": "delegated",
         "comparisons": len(sets["all"]), "order_seed": B4_ORDER_SEED, "b4": sets,
         "collector": "run_lifecycle_qualification.py --profile final --only B4 "
                      "--lifecycle-engines compact-bfs --equivalent-references "
                      "--atomic-references --window-multipliers "
                      "results/v1.2.0-qualification/window-multipliers.json; "
                      "analyze_lifecycle_qualification.py --expect-only B4"},
    ]


def k3() -> List[Dict[str, Any]]:
    """Query shapes (plan section 14.5): the same probe source built against each arm."""
    pct = cf5.measurement("percentile")
    metrics = [cf5.metric("latency_p50_ns", "latency_ns.p50", "time", measurement=pct),
               cf5.metric("latency_p99_ns", "latency_ns.p99", "tail", measurement=pct)]
    cells = []
    for shape in K3_SHAPES:
        for threads in K3_THREADS:
            def tool(name: str) -> Dict[str, Any]:
                return cf5.arm(name, ["shape", "--shape", shape, "--threads", threads,
                                      "--vertices", K3_VERTICES, "--seed", cf5.SEED])
            cells.append(cf5.paired(f"K3-{shape}-t{threads}", "K3", 2, None,
                                    tool("qsp_cand"), tool("qsp_base"), REFERENCE, metrics,
                                    rule="regression",
                                    check={"same_trace": "input_fingerprint_fnv1a64",
                                           "path": "wrong_answers", "equals": 0}))
    return cells


def m1() -> List[Dict[str, Any]]:
    """Reused scratch after a large query (plan section 14.7): absolute rules on the
    candidate, regression on small-query latency."""
    pct = cf5.measurement("percentile")
    metrics = [cf5.metric("small_latency_p50_ns", "small_latency_ns.p50", "time",
                          measurement=pct),
               cf5.metric("small_latency_p99_ns", "small_latency_ns.p99", "tail",
                          measurement=pct)]
    cells = []
    for threads in M1_THREADS:
        def tool(name: str) -> Dict[str, Any]:
            return cf5.arm(name, ["sequence", "--kind", "large-then-small", "--threads", threads,
                                  "--chain-vertices", M1_CHAIN, "--vertices", K3_VERTICES,
                                  "--small-queries", M1_SMALL_QUERIES, "--seed", cf5.SEED])
        cell = cf5.paired(f"M1-large-then-small-t{threads}", "M1", 2, None, tool("qsp_cand"),
                          tool("qsp_base"), REFERENCE, metrics, rule="regression",
                          check={"same_trace": "input_fingerprint_fnv1a64",
                                 "path": "wrong_answers", "equals": 0})
        cell["absolute"] = [
            {"name": "retained_scratch_max_bytes", "path": "retained_after_small_bytes.max",
             "max": SCRATCH_CAP_BYTES, "arm": "cf"},
            {"name": "small_query_allocations_max", "path": "small_allocations_after_100.max",
             "max": 0, "arm": "cf"}]
        cells.append(cell)
    return cells


def k4() -> List[Dict[str, Any]]:
    """ID maps (plan section 14.6): every engine #210 touches x four ID patterns."""
    cells = []
    for engine, identity in K4_ENGINES.items():
        for pattern in K4_PATTERNS:
            def harness(name: str) -> Dict[str, Any]:
                return cf5.arm(name, ["--workload", K4_WORKLOAD, "--nodes", 10_000,
                                      "--rounds", 20, "--seed", cf5.SEED, "--engine", engine,
                                      "--warmup", 1, "--repetitions", 1,
                                      "--id-pattern", pattern],
                               checks=cf5.engine_check("engine", identity))
            cell = cf5.paired(f"K4-{engine}-{pattern}", "K4", 2, None, harness("harness_cand"),
                              harness("harness_base"), REFERENCE,
                              [cf5.metric("workload_wall_ns", "repetitions.0.workload_wall_ns",
                                          "time", measurement=cf5.wall(K4_WORKLOAD, "harness"))],
                              rule="regression",
                              check={"same_trace": "trace_fingerprint_fnv1a64"})
            cell["timeout_s"] = K4_TIMEOUT_S
            cells.append(cell)
    return cells


def m2() -> List[Dict[str, Any]]:
    """Process memory at the server (plan section 14.7): one long-chain query per client,
    then read95 b8 for a 15 s window."""
    metrics = cf5.MREG_METRICS + [cf5.metric("server_rss_kib", "server_rss_kib", "memory")]
    cells = []
    for clients in M2_CLIENTS:
        cell_id = f"M2-standalone-off-read95-b8-c{clients}-100k-chain{M2_CHAIN}"
        spec = {"mode": "standalone", "lifecycle": False, "nodes": 100_000,
                "config": {"id": cell_id, "mix": "read95", "batch": 8, "clients": clients,
                           "warmup_ms": 1000, "measure_ms": 15_000, "open_rate": None,
                           "background": "none"}}
        def probe(name: str) -> Dict[str, Any]:
            out = cf5.mreg_arm(name, spec, ENGINE)
            out["args"] += ["--prelude", f"long-chain:{M2_CHAIN}"]
            return out
        cells.append(cf5.paired(cell_id, "M2", 2, None, probe("contention_cand"),
                                probe("contention_base"), REFERENCE, metrics,
                                rule="regression", check=cf5.MREG_CHECK))
    return cells


def delegated_a3() -> List[Dict[str, Any]]:
    """Attempt 3's delegated cells (plan section 14): attempt 2's, with every V1 cell deciding
    and fresh V1 seeds."""
    cells = delegated_a2()
    v1 = cells[0]
    assert v1["id"] == "V1"
    v1["seeds"] = V1_SEEDS_A3
    v1["v1"] = {"deciding": V1_HTTP_CELLS + V1_CORE_CELLS, "descriptive": [],
                "descriptive_reason": None}
    return cells


def _v1_cell_ids() -> List[str]:
    import run_p0_aa  # noqa: PLC0415
    return list(run_p0_aa.QUALIFICATION_CELL_IDS)


def window_multipliers() -> Dict[str, int]:
    """The frozen v1.0.0 factors for every timed (B1-B4) cell of the scope, which
    ``apply_multipliers`` requires before ``--only`` applies, plus the atomic cell's (its
    ``ops`` hub counterpart's)."""
    import run_lifecycle_qualification as rlq  # noqa: PLC0415
    frozen = json.loads((ROOT / "results" / "v1.0.0-qualification"
                         / "window-multipliers-q3.json").read_text())
    timed = [c["id"] for c in rlq.matrix("final", ENGINE, True, True)
             if c["experiment"] in ("B1", "B2", "B3", "B4")]
    factors = {c: int(frozen[c]) for c in timed if c != ATOMIC_CELL}
    factors[ATOMIC_CELL] = int(frozen["B4-http-ops-compact-bfs-hub-10000"])
    assert set(factors) == set(timed)
    return dict(sorted(factors.items()))


def build(cap_hours: Optional[float] = None, attempt: int = 1) -> Dict[str, Any]:
    if cap_hours is not None and not 0 < cap_hours < PLACEHOLDER_CAP:
        raise SystemExit(f"--cap-hours must be in (0, {PLACEHOLDER_CAP}), got {cap_hours}")
    if attempt not in (1, 2, 3):
        raise SystemExit(f"--attempt must be 1, 2 or 3, got {attempt}")
    if attempt == 1:
        cells = v2() + k2() + k1() + delegated()
    elif attempt == 2:
        cells = v2() + delegated_a2()
    else:
        cells = v2() + k2() + k1() + k3() + k4() + m1() + m2() + delegated_a3()
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids)), "cell ids are unique"
    counts: Dict[str, int] = {}
    for cell in cells:
        counts[cell["block"]] = counts.get(cell["block"], 0) + cell.get("comparisons", 1)
    matrix = {
        "schema": "cf5-matrix-1",
        "plan": {1: PLAN, 2: PLAN + ", section 13 (attempt 2)",
                 3: PLAN + ", section 14 (attempt 3)"}[attempt],
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
    if attempt == 2:
        matrix["attempt"] = 2
        matrix["rules"]["block_order"] = [["V1", "V2"], ["Q", "B4"]]
    if attempt == 3:
        matrix["attempt"] = 3
        # Plan section 14.11: K2, the longest block, last, so a cap cuts it first.
        matrix["rules"]["block_order"] = [["V1", "V2"],
                                          ["K1", "K3", "M1", "M2", "K4", "Q", "B4", "K2"]]
        matrix["rules"]["min_free_disk_gb"] = MIN_FREE_DISK_GB
    return matrix


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--attempt", type=int, choices=(1, 2, 3), default=1)
    parser.add_argument("--cap-hours", type=float)
    parser.add_argument("--window-multipliers", type=Path,
                        help="also write the B4 window multipliers (plan section 4.2) here")
    args = parser.parse_args(argv)
    from cli_paths import confined  # noqa: PLC0415
    default = (DEFAULT_OUT if args.attempt == 1
               else DEFAULT_OUT.parent / f"attempt{args.attempt}" / DEFAULT_OUT.name)
    out = confined(args.out or default, "--out")
    matrix = build(float(args.cap_hours) if args.cap_hours is not None else None, args.attempt)
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
