#!/usr/bin/env python3
"""Generates the CF5 matrix (knotrel ``docs/releases/v1.1.0-cf5-qualification-plan.md``).

    cf5_matrix.py [--out results/v1.1.0-cf5/cf5-matrix.json]

Every cell of the plan's section 4, with its arms (tool key and argv), metrics (JSON path,
direction, margin), tier and rule. Tool keys are resolved by ``run_cf5.py`` from the
campaign's tool map, so the matrix holds no machine paths. Cells of kind ``delegated`` are
run by an existing collector (named in the cell) and analyzed by its own analyzer; they are
listed so the totals and the order are complete.

Parameters come from existing qualification matrices: K1 rounds are the v1.0.0 A core
cells' (100 rounds for one-shot families, 20 for the sustained ones, seed 42); L1, L3, L4,
S1 and V2 reuse the v1.0.0 B4, R, Rmem and M_reg cells with the engine as the only change.
Nothing here is derived from measured results.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent.parent
V100 = ROOT / "results" / "v1.0.0-qualification" / "MATRIX.json"
DEFAULT_OUT = ROOT / "results" / "v1.1.0-cf5" / "cf5-matrix.json"
CALIBRATION = ROOT / "results" / "v1.1.0-cf5" / "timer-calibration" / "calibration.json"

MARGINS = {"time": 0.10, "tail": 0.25, "throughput": 0.10, "memory": 0.20}
REFERENCES = ("compact-bfs", "ett", "hdt")
CONNECTIVITY = {e: f"connectivity-{e}" for e in ("compact-bfs", "ett", "hdt", "cluster-forest")}

ONE_SHOT = ("chain-split-rejoin-v1", "cycle-alternatives-v1", "components-join-split-v1",
            "hub-alternatives-v1")
SUSTAINED = ("sustained-churn-path-v1", "sustained-churn-blocks-v1")
DENSE = ("dense-bridge-churn-v1", "redundant-bridge-churn-v1")
K1_SIZES = (10_000, 100_000)
DENSE_SIZES = (512, 2_048)
K2_SIZES = (10_000, 100_000, 1_000_000)
K2_DEGREES = (4, 16)
K2X_SIZES = (2 ** 14, 2 ** 17, 2 ** 20)
K2X_DEGREE = 6  # E = 3V
SEED = 42


def metric(name: str, path: str, kind: str, direction: str = "lower_is_better",
           measurement: Dict[str, Any] | None = None) -> Dict[str, Any]:
    out = {"name": name, "path": path, "margin_kind": kind, "margin": MARGINS[kind],
           "direction": direction}
    if measurement is not None:
        out["measurement"] = measurement
    return out


# Measurement limit (plan section 6.1), from the instrument calibration fixed before the
# campaign. ``limit_ns`` estimates (not a guaranteed bound) the additive error of one value:
# - ``aggregate``: ``intervals`` clock intervals, nothing timed inside: intervals * (tick + read);
# - ``instrumented_aggregate``: one interval around ``timed_ops`` individually timed
#   operations (K1, V2, V3 harness): tick + read + timed_ops * (harness gap + read);
# - ``per_op_sum``: sum of ``timed_ops`` per-operation intervals (L3 churn):
#   timed_ops * read + 3 * tick * sqrt(timed_ops / 6) (quantization, three standard deviations);
# - ``http_percentile``: one client request interval (closed loop): tick + read.
_CAL = json.loads(CALIBRATION.read_text())
TICK_NS = _CAL["constants"]["tick_ns"]
CLOCK_READ_NS = _CAL["constants"]["clock_read_ns"]
HARNESS_GAP_NS = _CAL["constants"]["harness_gap_ns"]
WORKLOAD_OPS = {k: v for k, v in _CAL["workload_operations"].items() if k != "source"}
L3_CHURN_OPS = {k: v for k, v in _CAL["l3_churn_operations"].items() if k != "source"}


def measurement(category: str, intervals: int = 1, timed_ops: int = 0,
                gap_ns: float = 0) -> Dict[str, Any]:
    if category == "aggregate":
        limit = intervals * (TICK_NS + CLOCK_READ_NS)
    elif category == "instrumented_aggregate":
        limit = TICK_NS + CLOCK_READ_NS + timed_ops * (gap_ns + CLOCK_READ_NS)
    elif category == "per_op_sum":
        limit = timed_ops * CLOCK_READ_NS + 3 * TICK_NS * math.sqrt(timed_ops / 6)
    elif category == "http_percentile":
        limit = TICK_NS + CLOCK_READ_NS
    else:
        raise ValueError(category)
    out: Dict[str, Any] = {"category": category, "limit_ns": round(limit, 1)}
    if category == "aggregate":
        out["intervals"] = intervals
    if timed_ops:
        out["timed_ops"] = timed_ops
    if gap_ns:
        out["gap_ns"] = gap_ns
    return out


def wall(workload: str, *tools: str) -> Dict[str, Any]:
    # Two arms on different harness binaries: the larger gap (symmetric bound).
    return measurement("instrumented_aggregate", timed_ops=WORKLOAD_OPS[workload],
                       gap_ns=max(HARNESS_GAP_NS[t] for t in tools))


AGG1 = measurement("aggregate")


MREG_CHECK = {"path": "errors", "equals": 0}


def paired(cell_id: str, block: str, tier: int, family: str | None, cf: Dict[str, Any],
           ref: Dict[str, Any], reference: str, metrics: List[Dict[str, Any]],
           rule: str = "two_sided", check: Dict[str, Any] | None = None,
           role: str = "primary") -> Dict[str, Any]:
    """``family``/``role``: the CF6 family the cell belongs to (plan section 12) and whether
    its first metric counts toward a preference (``primary``) or the cell only vetoes
    (``veto``); ``None`` for blocks without family statements (V, S3, L2)."""
    cell = {"id": cell_id, "block": block, "tier": tier, "kind": "paired", "family": family,
            "role": role, "reference": reference, "rule": rule, "arms": {"cf": cf, "ref": ref},
            "metrics": metrics}
    if check:
        cell["check"] = check
    return cell


def arm(tool: str, args: List[str], line: str = "whole",
        checks: List[Dict[str, Any]] | None = None) -> Dict[str, Any]:
    """``line``: ``whole`` (stdout is one JSON object), ``last`` (last JSON line), or
    ``kind=X`` (the first JSON line whose ``kind`` is X). ``checks``: arm-level gates
    ``{"line", "path", "equals"}`` (for example the engine the tool reports)."""
    out = {"tool": tool, "args": [str(a) for a in args], "line": line}
    if checks:
        out["checks"] = checks
    return out


def engine_check(path: str, value: str, line: str | None = None) -> List[Dict[str, Any]]:
    item: Dict[str, Any] = {"path": path, "equals": value}
    if line:
        item["line"] = line
    return [item]


HARNESS_IDENTITY = {
    "compact-bfs": "knotrel-core/connectivity-graph/compact-bfs",
    "ett": "knotrel-core/connectivity-graph/ett",
    "hdt": "knotrel-core/connectivity-graph/hdt",
    "cluster-forest": "knotrel-core/connectivity-graph/cluster-forest-v1",
}

#: Engine identities the v1.0.0 A harness (df635a1e) reports, for the V2 and V3 core cells.
A_IDENTITY = {
    "ett-scan": "knotrel-core/ett-pruned-v2",
    "hdt": "knotrel-core/hdt-sparse-levels-v3",
    "compact-bfs": "knotrel-core/compact-bfs-v1",
    "compact-workspace": "knotrel-core/compact-workspace-v2",
}


def k1() -> List[Dict[str, Any]]:
    cells = []
    for workload in ONE_SHOT + SUSTAINED + DENSE:
        sizes = DENSE_SIZES if workload in DENSE else K1_SIZES
        rounds = 20 if workload in SUSTAINED else 100
        for nodes in sizes:
            def harness(engine: str) -> Dict[str, Any]:
                return arm("harness", ["--workload", workload, "--nodes", nodes, "--rounds",
                                       rounds, "--seed", SEED, "--engine", CONNECTIVITY[engine],
                                       "--warmup", 1, "--repetitions", 1],
                           checks=engine_check("engine", HARNESS_IDENTITY[engine]))
            for ref in REFERENCES:
                cells.append(paired(f"K1-{workload}-{nodes}-vs-{ref}", "K1", 2, workload,
                                    harness("cluster-forest"), harness(ref), ref,
                                    [metric("workload_wall_ns", "repetitions.0.workload_wall_ns",
                                            "time", measurement=wall(workload, "harness"))],
                                    check={"same_trace": "trace_fingerprint_fnv1a64"}))
    return cells


def core_cells(block: str, tier: int, mode: str, sizes, degrees, metrics, family_fmt: str,
               role: str = "primary") -> List[Dict[str, Any]]:
    cells = []
    for degree in degrees:
        for vertices in sizes:
            def tool(engine: str) -> Dict[str, Any]:
                return arm("cf5_core", [mode, "--engine", CONNECTIVITY[engine], "--vertices",
                                        vertices, "--degree", degree, "--seed", SEED],
                           checks=engine_check("engine", CONNECTIVITY[engine]))
            for ref in REFERENCES:
                cells.append(paired(f"{block}-d{degree}-{vertices}-vs-{ref}", block, tier,
                                    family_fmt.format(degree=degree), tool("cluster-forest"),
                                    tool(ref), ref, metrics,
                                    check={"same_trace": "edges_fingerprint"}, role=role))
    return cells


def k3_families() -> List[Dict[str, Any]]:
    cells = []
    for family in ONE_SHOT + SUSTAINED:
        def tool(engine: str) -> Dict[str, Any]:
            return arm("cf5_core", ["construct", "--engine", CONNECTIVITY[engine], "--family",
                                    family, "--vertices", 100_000, "--seed", SEED],
                       checks=engine_check("engine", CONNECTIVITY[engine]))
        for ref in REFERENCES:
            cells.append(paired(f"K3-{family}-100000-vs-{ref}", "K3", 3, "K3-families",
                                tool("cluster-forest"), tool(ref), ref,
                                [metric("construct_ns", "result.construct_ns", "time",
                                        measurement=AGG1)],
                                check={"same_trace": "edges_fingerprint"}))
    return cells


def k4() -> List[Dict[str, Any]]:
    cells = []
    names = ("live_after_construction", "live_after_inserts", "live_after_deletes", "peak")
    for degree in K2_DEGREES:
        for vertices in K2_SIZES:
            def tool(engine: str) -> Dict[str, Any]:
                return arm("memory_peak", ["cf5-random", "--engine", engine, "--vertices",
                                           vertices, "--degree", degree, "--seed", SEED], "last",
                           checks=[{"path": "engine", "equals": engine},
                                   {"path": "peak_exact", "equals": True}])
            for ref in REFERENCES:
                cells.append({"id": f"K4-d{degree}-{vertices}-vs-{ref}", "block": "K4",
                              "tier": 3, "kind": "deterministic", "family": f"K2-d{degree}",
                              "role": "veto",
                              "reference": ref, "rule": "deterministic",
                              "arms": {"cf": tool("cluster-forest"), "ref": tool(ref)},
                              # Section 4.1: the K4 graph must be the K2 cell's graph.
                              "check": {"same_trace": "edges_fingerprint",
                                        "same_trace_as": f"K2-d{degree}-{vertices}-vs-{ref}"},
                              "metrics": [metric(n, n, "memory") for n in names]})
    return cells


def v100_cells(experiment: str) -> List[Dict[str, Any]]:
    return json.loads(V100.read_text())["experiments"][experiment]["cells"]


def with_engine(args: List[str], engine: str) -> List[str]:
    args = list(args)
    if "--engine" in args:
        args[args.index("--engine") + 1] = engine
    else:
        args[1:1] = ["--engine", engine]
    return args


def l1() -> List[Dict[str, Any]]:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import run_lifecycle_qualification as rlq  # noqa: E402
    deciding = json.loads(V100.read_text())["experiments"]["B_C"]["equivalent_references"][
        "deciding"]
    by_id = {c["id"]: c for c in rlq.matrix("final", "compact-bfs", True)}
    cells = []
    for cell_id in deciding:
        base = by_id[cell_id]["args"]
        # One measured pair per invocation after one in-process warmup pair (no cold
        # start inside the window); the plain arm always runs compact-bfs, so the
        # answers check compares the lifecycle arm with an independent engine for CF,
        # and both arms do the same reference work.
        def probe(engine: str) -> Dict[str, Any]:
            args = with_engine(base, engine)
            args[args.index("--pairs") + 1] = "1"
            args[args.index("--warmup") + 1] = "1"
            return arm("http_lifecycle", args + ["--reference-engine", "compact-bfs"],
                       "kind=pair", [{"path": "engine", "equals": engine},
                                     {"path": "reference_engine", "equals": "compact-bfs"}])
        # The metric is a window wall time: the time margin (10 %), not the B4
        # tolerance, which bounded lifecycle overhead against plain mode.
        cells.append(paired(f"L1-{cell_id}", "L1", 2, "L", probe("cluster-forest"),
                            probe("compact-bfs"), "compact-bfs",
                            [metric("candidate_ns", "candidate_ns", "time", measurement=AGG1)],
                            check={"path": "answers_agree", "equals": True}))
    return cells


def l3_measurement(cell: Dict[str, Any]) -> Dict[str, Any]:
    # churn: the sum of per-operation intervals; imports: the median of single intervals.
    if cell["args"][0] == "churn":
        return measurement("per_op_sum", timed_ops=L3_CHURN_OPS[cell["id"]])
    return AGG1


def l3() -> List[Dict[str, Any]]:
    cells = []
    for cell in v100_cells("R"):
        cells.append(paired(f"L3-{cell['id']}", "L3", 3, "L",
                            arm("release_cells", with_engine(cell["args"], "cluster-forest"),
                                "last", engine_check("engine", "cluster-forest")),
                            arm("release_cells", with_engine(cell["args"], "compact-bfs"),
                                "last", engine_check("engine", "compact-bfs")),
                            "compact-bfs", [metric("observation_ns", "observation_ns", "time",
                                                   measurement=l3_measurement(cell))],
                            # release-cells emits no fingerprint: its churn cells report the
                            # operation count (equal counts checked); its import cells build the
                            # same seeded topology from identical argv but the engine.
                            check={"same_trace": "operations"}
                            if cell["args"][0] == "churn" else None))
    return cells


def l4() -> List[Dict[str, Any]]:
    cells = []
    for cell in v100_cells("Rmem"):
        line = "derive=churn_memory" if cell["args"][0] == "churn" else "last"
        cells.append({"id": f"L4-{cell['id']}", "block": "L4", "tier": 3,
                      "kind": "deterministic", "family": "L", "role": "veto",
                      "reference": "compact-bfs",
                      "rule": "deterministic",
                      "arms": {e: arm("memory_peak", with_engine(cell["args"], engine), line,
                                      engine_check("engine", engine, "kind=baseline"
                                                   if cell["args"][0] == "churn" else None))
                               for e, engine in (("cf", "cluster-forest"),
                                                 ("ref", "compact-bfs"))},
                      "metrics": [metric(n, n, "memory") for n in cell["metrics"]]})
    return cells


def mreg_arm(tool: str, cell: Dict[str, Any], engine: str) -> Dict[str, Any]:
    # One probe binary (it links no knotrel crate); `contention` and `contention_v100` differ
    # only by `--server-bin` (candidate or v1.0.0 server).
    return arm(tool, ["--mode", cell["mode"], "--lifecycle", str(cell["lifecycle"]).lower(),
                      "--nodes", cell["nodes"], "--seed", 7, "--engine", engine,
                      "--configs-json", json.dumps(cell["config"], sort_keys=True)],
               "kind=config", engine_check("engine", engine, "kind=start"))


MREG_METRICS = [metric("requests_per_s", "requests_per_s", "throughput", "higher_is_better"),
                metric("latency_ns.p99", "latency_ns.p99", "tail",
                       measurement=measurement("http_percentile"))]


def s1() -> List[Dict[str, Any]]:
    cells = []
    for cell in v100_cells("M_reg"):
        refs = ("compact-bfs",) if cell["lifecycle"] else REFERENCES
        for ref in refs:
            cells.append(paired(f"S1-{cell['id']}-vs-{ref}", "S1", 2,
                                "S1-lifecycle-on" if cell["lifecycle"] else "S1-lifecycle-off",
                                mreg_arm("contention", cell, "cluster-forest"),
                                mreg_arm("contention", cell, ref), ref, MREG_METRICS,
                                check=MREG_CHECK))
    return cells


def v2_v3() -> List[Dict[str, Any]]:
    cells = []
    for cell in v100_cells("M_reg"):
        cells.append(paired(f"V2-{cell['id']}", "V2", 1, None,
                            mreg_arm("contention", cell, "compact-bfs"),
                            mreg_arm("contention_v100", cell, "compact-bfs"), "v1.0.0",
                            MREG_METRICS, rule="regression", check=MREG_CHECK))
    for workload, rounds in (("chain-split-rejoin-v1", 100), ("sustained-churn-path-v1", 20)):
        for engine in ("ett-scan", "hdt"):
            def h(tool: str) -> Dict[str, Any]:
                return arm(tool, ["--workload", workload, "--nodes", 100_000, "--rounds", rounds,
                                  "--seed", SEED, "--engine", engine, "--warmup", 1,
                                  "--repetitions", 1],
                           checks=engine_check("engine", A_IDENTITY[engine]))
            cells.append(paired(f"V2-{workload}-100000-{engine}", "V2", 1, None,
                                h("harness_a_candidate"), h("harness_a_v100"), "v1.0.0",
                                [metric("workload_wall_ns", "repetitions.0.workload_wall_ns",
                                        "time", measurement=wall(workload, "harness_a_candidate",
                                                                 "harness_a_v100"))],
                                rule="regression",
                                check={"same_trace": "trace_fingerprint_fnv1a64"}))
    for workload, rounds in (("chain-split-rejoin-v1", 100), ("sustained-churn-path-v1", 20)):
        for engine in ("compact-bfs", "compact-workspace"):
            def a(tool: str, kind: str, identity: str) -> Dict[str, Any]:
                return arm(tool, ["--workload", workload, "--nodes", 10_000, "--rounds", rounds,
                                  "--seed", SEED, "--engine", kind, "--warmup", 1,
                                  "--repetitions", 1], checks=engine_check("engine", identity))
            cells.append(paired(f"V3-{workload}-10000-vs-v100-{engine}", "V3", 3, None,
                                a("harness", CONNECTIVITY["cluster-forest"],
                                  HARNESS_IDENTITY["cluster-forest"]),
                                a("harness_a_v100", engine, A_IDENTITY[engine]), f"v1.0.0 {engine}",
                                [metric("workload_wall_ns", "repetitions.0.workload_wall_ns",
                                        "time", measurement=wall(workload, "harness",
                                                                 "harness_a_v100"))],
                                check={"same_trace": "trace_fingerprint_fnv1a64"}))
    for cell in v100_cells("M_reg"):
        cells.append(paired(f"V3-{cell['id']}", "V3", 3, None,
                            mreg_arm("contention", cell, "cluster-forest"),
                            mreg_arm("contention_v100", cell, "compact-bfs"),
                            "v1.0.0 compact-bfs", MREG_METRICS, check=MREG_CHECK))
    return cells


def delegated() -> List[Dict[str, Any]]:
    # Commands and declared seeds: results/v1.1.0-cf5/prepare_cf5.sh (tool map ``_delegated``).
    return [
        {"id": "V1", "block": "V1", "tier": 1, "kind": "delegated", "comparisons": 9,
         "collector": "run_p0_aa.py --execute on the two plans of prepare_bc_qualification.py "
                      "(B = v1.0.0, C = candidate; seeds 141240-141242 and 141250-141252), "
                      "n = 24 fixed; analyze_v100q_a.py rules"},
        {"id": "L2", "block": "L2", "tier": 3, "kind": "delegated", "comparisons": 15,
         "collector": "run_lifecycle_qualification.py --profile final --only C "
                      "--lifecycle-engines cluster-forest --order-seed 51240; "
                      "analyze_lifecycle_qualification.py C1-C4"},
        {"id": "S3", "block": "S3", "tier": 2, "kind": "delegated", "comparisons": 7,
         "collector": "run_cf5_s3.py run (v1.0.0 Q runner, both sides on the candidate server, "
                      "LOAD_ENGINE cluster-forest / compact-bfs, 3 observations each, 90-minute "
                      "cap); run_cf5_s3.py evaluate: Q1-Q4 on CF, Q5-style on the 3 L1 query cells"},
    ]


def build() -> Dict[str, Any]:
    cells = (k1()
             + core_cells("K2", 2, "staged", K2_SIZES, K2_DEGREES,
                          # 10 insertion and 10 deletion stages; 20 query batches.
                          [metric("update_ns", "result.update_ns", "time",
                                  measurement=measurement("aggregate", intervals=20)),
                           metric("query_ns", "result.query_ns", "time",
                                  measurement=measurement("aggregate", intervals=20))],
                          "K2-d{degree}")
             + core_cells("K2x", 3, "all", K2X_SIZES, (K2X_DEGREE,),
                          [metric("delete_ns", "result.delete_ns", "time", measurement=AGG1),
                           metric("insert_ns", "result.insert_ns", "time", measurement=AGG1)],
                          "K2x")
             + core_cells("K3", 3, "construct", K2_SIZES, K2_DEGREES,
                          [metric("construct_ns", "result.construct_ns", "time",
                                  measurement=AGG1)], "K2-d{degree}",
                          role="veto")
             + k3_families() + k4() + l1() + l3() + l4() + s1() + v2_v3() + delegated())
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids)), "cell ids are unique"
    counts: Dict[str, int] = {}
    for cell in cells:
        counts[cell["block"]] = counts.get(cell["block"], 0) + cell.get("comparisons", 1)
    return {
        "schema": "cf5-matrix-1",
        "plan": "knotrel docs/releases/v1.1.0-cf5-qualification-plan.md",
        "rules": {"pairs": 24, "warmup_pairs": 2, "interval_order_statistics": [7, 18],
                  "coverage": 0.9773, "margins": MARGINS, "cap_hours": 15,
                  "measurement_limit": {"calibration": str(CALIBRATION.relative_to(ROOT)),
                                        "tick_ns": TICK_NS, "clock_read_ns": CLOCK_READ_NS,
                                        "harness_gap_ns": HARNESS_GAP_NS},
                  "second_session_cap_hours": 8, "tiers": [1, 2, 3],
                  # Priority order of blocks within each tier (plan section 8).
                  "block_order": [["V1", "V2"], ["K1", "K2", "S1", "L1", "S3"],
                                  ["K3", "K4", "L3", "L4", "L2", "V3", "K2x"]]},
        "counts": dict(sorted(counts.items())),
        "total_comparisons": sum(counts.values()),
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cli_paths import confined  # noqa: PLC0415
    args.out = confined(args.out, "--out")
    matrix = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(matrix, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"out": str(args.out), "counts": matrix["counts"],
                      "total": matrix["total_comparisons"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
