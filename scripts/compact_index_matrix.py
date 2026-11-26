#!/usr/bin/env python3
"""Generates the knotrel#151 comparison matrix (compact internal node indices, option B64).

    compact_index_matrix.py --out M.json [--windows W.json] [--scale S]

knotrel ``docs/design/compact-node-index.md``, section 6 (approved 2026-11-26: B64
only, strict D4, G1 and G2 both required, M1-iso report-only). Every cell of section
6.4 with its ID, parameters, seeds, arms, metrics, margins and the classification rules
of section 6.6, in the schema of ``cf5_matrix.py`` so that ``run_cf5.py`` executes it:

- arm ``cf`` is the **candidate** (B), arm ``ref`` the **base** (CUR); both run the same
  argv on the probe built against their own checkout (tool keys ``*_cand`` and
  ``*_base``, resolved from the tool map of ``build_151_probes.sh``). Paired log ratios
  are therefore ``ln(B / CUR)`` (``ln(CUR / B)`` for throughput) and the memory ratio is
  ``q = B / CUR``;
- every cell checks ``same_trace: gate``: both arms must print the same gate object
  (input fingerprint, logical counts, ``LifecycleStorage`` entry counts, and for P
  cells the page digests); HTTP cells also check ``errors == 0``;
- windowed cells carry ``window`` (``--k`` base value). ``--windows`` applies the
  pilot-derived factors (``run_151.py propose-windows``; the ``apply_multipliers`` rule
  of ``run_lifecycle_qualification.py``: every windowed cell needs a factor, no unknown
  key); without it the matrix is marked ``windows: unset`` and the campaign refuses it;
- ``--scale S`` divides every node count and hub degree by ``S`` (smoke at reduced sizes
  only; the analyzer and the campaign refuse ``scale != 1``).

Measurement limits (TIMER_LIMITED, CF5 plan section 6.1) use the CF5 clock calibration
(``results/v1.1.0-cf5/timer-calibration``); section 6.5 requires re-calibration when the
host or toolchain differs, recorded with the campaign. Limits that depend on a workload
property (operation or page counts) name the output field the analyzer reads.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
CALIBRATION = ROOT / "results" / "v1.1.0-cf5" / "timer-calibration" / "calibration.json"
PROTOCOL = "knotrel docs/design/compact-node-index.md, section 6 (approved 2026-11-26)"

SEED = 151_2026
MARGINS = {"time": 0.10, "tail": 0.25, "throughput": 0.10}
MEMORY = {"smaller_at_most": 0.90, "larger_at_least": 1.05}
G2_BYTES_PER_EDGE = 8
ENGINES = {"cb": "compact-bfs", "cf": "cluster-forest"}
HUB_DEGREES = (10_000, 100_000, 1_000_000)
HUB_BASE_NODES = 1_000_000
REPS = 5
CURSORS = 100
#: Base windows (``--k``) before the pilot factor.
BASE_K = {"I2": 32, "I3": 32, "R1": 32, "R2": 32, "R3": 32, "R5": 32, "R4": 1, "P1": 1}
#: Block order (section 6.8): tier 1 M; tier 2 hub cells, then Q; tier 3 ordinary cells.
BLOCK_ORDER = [["M"], ["P", "H", "Q"], ["O", "C"]]
TIERS = {"M": 1, "P": 2, "H": 2, "Q": 2, "O": 3, "C": 3}

_CAL = json.loads(CALIBRATION.read_text())
TICK_NS = _CAL["constants"]["tick_ns"]
CLOCK_READ_NS = _CAL["constants"]["clock_read_ns"]


def aggregate(intervals: int = 1, per: int = 1) -> Dict[str, Any]:
    """``intervals`` clock intervals, the metric divided by ``per`` (R4 per cycle)."""
    return {"category": "aggregate", "intervals": intervals, "per": per,
            "limit_ns": round(intervals * (TICK_NS + CLOCK_READ_NS) / per, 3)}


def per_op_sum(ops_field: str) -> Dict[str, Any]:
    """Summed per-operation intervals; the analyzer computes the limit from the
    observation's operation count (``timed_ops_from``), CF5's per_op_sum formula."""
    return {"category": "per_op_sum", "timed_ops_from": ops_field, "limit_ns": None}


def http_percentile() -> Dict[str, Any]:
    return {"category": "http_percentile", "limit_ns": round(TICK_NS + CLOCK_READ_NS, 3)}


def http_sum(intervals_field: str) -> Dict[str, Any]:
    return {"category": "aggregate", "intervals_from": intervals_field, "per": 1,
            "limit_ns": None}


def metric(name: str, path: str, kind: str, measurement: Optional[Dict[str, Any]] = None,
           direction: str = "lower_is_better", role: str = "primary") -> Dict[str, Any]:
    out: Dict[str, Any] = {"name": name, "path": path, "margin_kind": kind,
                           "direction": direction, "role": role}
    if kind == "memory":
        out.update(MEMORY)
        out["margin"] = 1 - MEMORY["smaller_at_most"]
    else:
        out["margin"] = MARGINS[kind]
    if measurement is not None:
        out["measurement"] = measurement
    return out


def arm(tool: str, side: str, args: List[Any], line: str = "last") -> Dict[str, Any]:
    return {"tool": f"{tool}_{side}", "args": [str(a) for a in args], "line": line}


def cell(cell_id: str, group: str, block: str, kind: str, tool: str, args: List[Any],
         metrics: List[Dict[str, Any]], params: Dict[str, Any], line: str = "last",
         check: Optional[Dict[str, Any]] = None, report_only: bool = False,
         window: Optional[int] = None) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "id": cell_id, "group": group, "block": block, "tier": TIERS[block], "kind": kind,
        "rule": "deterministic" if kind == "deterministic" else "two_sided",
        "report_only": report_only, "params": params,
        "arms": {"cf": arm(tool, "cand", args, line), "ref": arm(tool, "base", args, line)},
        "metrics": metrics, "check": {"same_trace": "gate", **(check or {})}}
    if window is not None:
        out["window"] = {"flag": "--k", "base": window, "factor": 1}
    return out


def size_label(n: int) -> str:
    exponent = len(str(n)) - 1
    return f"1e{exponent}" if n == 10 ** exponent else str(n)


class Sizes:
    def __init__(self, scale: int) -> None:
        self.scale = scale

    def __call__(self, n: int) -> int:
        return max(1, n // self.scale)


def workload_args(name: str, nodes: int = 0, degree: int = 0) -> List[Any]:
    args: List[Any] = ["--workload", name]
    if nodes:
        args += ["--nodes", nodes]
    if degree:
        args += ["--degree", degree]
    return args


def memory_cells(s: Sizes) -> List[Dict[str, Any]]:
    cells = []
    m1_graphs = ([("sparse", s(n), 0, f"sparse-{size_label(n)}", n) for n in
                  (10_000, 100_000, 1_000_000)]
                 + [("ring", s(1_000_000), 0, "ring-1e6", 1_000_000)]
                 + [("star", 0, s(d), f"star-{size_label(d)}", d + 1) for d in HUB_DEGREES]
                 + [("hub-in-sparse", s(HUB_BASE_NODES), s(d), f"his-{size_label(d)}",
                     HUB_BASE_NODES + 1) for d in HUB_DEGREES])
    live = [metric("live_after", "live_after", "memory"),
            metric("high_water", "high_water", "memory")]
    for short, engine in ENGINES.items():
        for name, nodes, degree, label, full_v in m1_graphs:
            args = ["compact-import", "--engine", engine] + workload_args(name, nodes, degree) \
                + ["--seed", SEED]
            cells.append(cell(f"M1-{short}-{label}", "M1", "M", "deterministic", "memory_peak",
                              args, live, {"engine": engine, "graph": label, "full_v": full_v,
                                           "nodes": nodes, "degree": degree}))
        args = ["compact-import", "--engine", engine, "--workload", "iso", "--nodes",
                s(1_000_000), "--seed", SEED]
        cells.append(cell(f"M1iso-{short}-iso-1e6", "M1-iso", "M", "deterministic",
                          "memory_peak", args, live,
                          {"engine": engine, "graph": "iso-1e6", "full_v": 1_000_000},
                          report_only=True))
        for name, nodes, degree, label in (("sparse", s(1_000_000), 0, "sparse-1e6"),
                                           ("hub-in-sparse", s(HUB_BASE_NODES), s(1_000_000),
                                            "his-1e6")):
            args = workload_args(name, nodes, degree) + ["--seed", SEED]
            cells.append(cell(f"M2-{short}-{label}", "M2", "M", "deterministic", "memory_peak",
                              ["compact-build", "--engine", engine] + args, live,
                              {"engine": engine, "graph": label, "order": "seeded random; "
                               "hub spokes appended in ascending leaf ID"}))
            cells.append(cell(f"M3-{short}-{label}", "M3", "M", "deterministic", "memory_peak",
                              ["compact-import-http", "--engine", engine] + args
                              + ["--mode", "replace"],
                              [metric("high_water", "high_water", "memory"),
                               metric("live_after_swap", "live_after_swap", "memory")],
                              {"engine": engine, "graph": label, "mode": "replace"}))
        for topology in ("sparse", "hub"):
            for reuse in ("fresh", "same", "toggle"):
                args = ["churn", "--engine", engine, "--topology", topology, "--nodes",
                        s(100_000), "--cycles", 30, "--churn-percent", 5, "--reuse", reuse,
                        "--seed", 5_000_001]
                cells.append(cell(f"M4-{short}-{topology}-1e5-{reuse}", "M4", "M",
                                  "deterministic", "memory_peak", args,
                                  [metric("live_at_end", "live_at_end", "memory"),
                                   metric("high_water", "high_water", "memory")],
                                  {"engine": engine, "graph": f"{topology}-1e5",
                                   "reuse": reuse}, line="kind=churn-end"))
        args = ["mass-removal", "--engine", engine, "--workload", "sparse", "--nodes",
                s(1_000_000), "--seed", SEED, "--percent", 60]
        cells.append(cell(f"M5-{short}-sparse-1e6", "M5", "M", "deterministic", "memory_peak",
                          args, [metric("live_after_removal", "live_after_removal", "memory"),
                                 metric("high_water", "high_water", "memory"),
                                 metric("live_at_end", "live_at_end", "memory")],
                          {"engine": engine, "graph": "sparse-1e6", "percent": 60}))
        # M6 (supporting, report-only): RSS after an add_node + link build of the M1 10^6
        # graphs; both engines (the table lists 6 graphs; run for CB-L and CF-L).
        for name, nodes, degree, label in (
                [("sparse", s(1_000_000), 0, "sparse-1e6"), ("ring", s(1_000_000), 0, "ring-1e6"),
                 ("star", 0, s(1_000_000), "star-1e6")]
                + [("hub-in-sparse", s(HUB_BASE_NODES), s(d), f"his-{size_label(d)}")
                   for d in HUB_DEGREES]):
            args = ["resources", "--arm", "lifecycle", "--engine", engine] \
                + workload_args(name, nodes, degree) + ["--cycles", 0, "--seed", SEED]
            cells.append(cell(f"M6-{short}-{label}", "M6", "M", "deterministic",
                              "core_lifecycle", args,
                              [metric("rss_after_build", "rss_after_build", "memory")],
                              {"engine": engine, "graph": label}, line="kind=workload-rss",
                              report_only=True))
    return cells


def his(s: Sizes, d: int) -> List[Any]:
    return workload_args("hub-in-sparse", s(HUB_BASE_NODES), s(d))


def window_cell(cell_id: str, group: str, block: str, engine: str, wl: List[Any], label: str,
                state: str, op: str, pool: str) -> Dict[str, Any]:
    args = ["window", "--engine", engine] + wl + ["--seed", SEED, "--state", state, "--op", op,
                                                  "--pool", pool, "--k", BASE_K[group],
                                                  "--reps", REPS]
    return cell(cell_id, group, block, "paired", "compact_cells", args,
                [metric("observation_ns", "observation_ns", "time", aggregate())],
                {"engine": engine, "graph": label, "state": state, "op": op, "pool": pool,
                 "reps": REPS}, window=BASE_K[group])


def timed_cells(s: Sizes) -> List[Dict[str, Any]]:
    cells = []
    for short, engine in ENGINES.items():
        # I1: incremental build.
        for n in (100_000, 1_000_000):
            label = f"sparse-{size_label(n)}"
            args = ["build", "--engine", engine] + workload_args("sparse", s(n)) \
                + ["--seed", SEED, "--reps", 3]
            cells.append(cell(f"I1-{short}-{label}", "I1", "O", "paired", "compact_cells", args,
                              [metric("observation_ns", "observation_ns", "time", aggregate())],
                              {"engine": engine, "graph": label, "reps": 3}))
        for d in HUB_DEGREES:
            label = f"his-{size_label(d)}"
            cells.append(window_cell(f"I2-{short}-{label}", "I2", "H", engine, his(s, d), label,
                                     "scrambled", "link", "spokes"))
        sparse6 = workload_args("sparse", s(1_000_000))
        cells.append(window_cell(f"I3-{short}-sparse-1e6", "I3", "H", engine, sparse6,
                                 "sparse-1e6", "ordered", "enable", "edges"))
        cells.append(window_cell(f"R3-{short}-sparse-1e6", "R3", "H", engine, sparse6,
                                 "sparse-1e6", "ordered", "disable", "edges"))
        for d in HUB_DEGREES:
            label = f"his-{size_label(d)}"
            for group, op in (("I3", "enable"), ("R3", "disable"), ("R2", "cut")):
                cells.append(window_cell(f"{group}-{short}-{label}", group, "H", engine,
                                         his(s, d), label, "scrambled", op, "spokes"))
        for n in (100_000, 1_000_000):
            label = f"sparse-{size_label(n)}"
            cells.append(window_cell(f"R1-{short}-{label}", "R1", "O", engine,
                                     workload_args("sparse", s(n)), label, "ordered", "cut",
                                     "edges"))
        for d in HUB_DEGREES:
            label = f"star-{size_label(d)}"
            args = ["degree-remove", "--engine", engine, "--degree", s(d), "--k", BASE_K["R4"],
                    "--reps", REPS]
            cells.append(cell(f"R4-{short}-{label}", "R4", "H", "paired", "compact_cells", args,
                              [metric("per_cycle_ns", "per_cycle_ns", "time",
                                      {**aggregate(per=BASE_K["R4"]), "per_k": True})],
                              {"engine": engine, "graph": label, "reps": REPS},
                              window=BASE_K["R4"]))
        cells.append(window_cell(f"R5-{short}-sparse-1e6", "R5", "O", engine, sparse6,
                                 "sparse-1e6", "ordered", "remove", "nodes"))
        # P1, P2: CB-L everywhere, CF-L at D = 10^6 only (section 6.4).
        for d in HUB_DEGREES:
            if short == "cf" and d != 1_000_000:
                continue
            label = f"his-{size_label(d)}"
            for state in ("ordered", "scrambled"):
                args = ["traverse", "--engine", engine] + his(s, d) + [
                    "--seed", SEED, "--state", state, "--k", BASE_K["P1"], "--reps", REPS]
                cells.append(cell(f"P1-{short}-{label}-{state}", "P1", "P", "paired",
                                  "compact_cells", args,
                                  [metric("observation_ns", "observation_ns", "time",
                                          aggregate())],
                                  {"engine": engine, "graph": label, "state": state,
                                   "page": 1000, "reps": REPS}, window=BASE_K["P1"]))
                args = ["pages", "--engine", engine] + his(s, d) + [
                    "--seed", SEED, "--state", state, "--cursors", CURSORS]
                cells.append(cell(f"P2-{short}-{label}-{state}", "P2", "P", "paired",
                                  "compact_cells", args,
                                  [metric("median_page_ns", "median_page_ns", "time",
                                          aggregate()),
                                   metric("p99_page_ns", "p99_page_ns", "tail", aggregate(),
                                          role="tail")],
                                  {"engine": engine, "graph": label, "state": state,
                                   "cursors": 3 * CURSORS, "page": 1000}))
            args = ["--engine", engine, "--nodes", s(HUB_BASE_NODES), "--degree", s(d),
                    "--seed", SEED, "--cell", "p3", "--cursors", CURSORS]
            cells.append(cell(f"P3-{short}-{label}", "P3", "P", "paired", "http_pages", args,
                              [metric("median_ns", "median_ns", "time", http_percentile()),
                               metric("p99_ns", "p99_ns", "tail", http_percentile(),
                                      role="tail")],
                              {"engine": engine, "graph": label, "state": "scrambled",
                               "cursors": 3 * CURSORS, "server": "fresh per observation"},
                              check={"path": "errors", "equals": 0}))
        args = ["--engine", engine, "--nodes", s(HUB_BASE_NODES), "--degree", s(1_000_000),
                "--seed", SEED, "--cell", "p4", "--cursors", CURSORS]
        cells.append(cell(f"P4-{short}-his-1e6", "P4", "P", "paired", "http_pages", args,
                          [metric("traversal_ns", "traversal_ns", "time",
                                  http_sum("traversal_pages")),
                           metric("page_p99_ns", "page_p99_ns", "tail", http_percentile(),
                                  role="tail")],
                          {"engine": engine, "graph": "his-1e6", "state": "scrambled",
                           "cursors": 3 * CURSORS, "server": "fresh per observation"},
                          check={"path": "errors", "equals": 0}))
        # C1: the existing release-cells churn schedule.
        for topology in ("sparse", "hub"):
            for reuse in ("fresh", "same", "toggle"):
                args = ["churn", "--engine", engine, "--topology", topology, "--nodes",
                        s(100_000), "--cycles", 30, "--churn-percent", 5, "--reuse", reuse,
                        "--seed", 5_000_001]
                cells.append(cell(f"C1-{short}-{topology}-1e5-{reuse}", "C1", "C", "paired",
                                  "release_cells", args,
                                  [metric("observation_ns", "observation_ns", "time",
                                          per_op_sum("operations")),
                                   metric("slowest_op_ns", "slowest_op_ns", "tail",
                                          aggregate(), role="tail")],
                                  {"engine": engine, "graph": f"{topology}-1e5",
                                   "reuse": reuse}))
        args = ["mass-churn", "--engine", engine, "--workload", "sparse", "--nodes",
                s(1_000_000), "--seed", SEED, "--percent", 60]
        cells.append(cell(f"C2-{short}-sparse-1e6", "C2", "C", "paired", "compact_cells", args,
                          [metric("observation_ns", "observation_ns", "time",
                                  per_op_sum("operations")),
                           metric("slowest_op_ns", "slowest_op_ns", "tail", aggregate(),
                                  role="tail")],
                          {"engine": engine, "graph": "sparse-1e6", "percent": 60}))
        for topology in ("sparse", "hub"):
            args = ["--scenario", "ops", "--engine", engine, "--topology", topology,
                    "--nodes", s(10_000), "--requests", 64, "--pairs", 1, "--warmup", 0,
                    "--seed", SEED]
            c3 = cell(f"C3-{short}-{topology}-1e4", "C3", "C", "paired", "http_lifecycle", args,
                      [metric("requests_per_s", "candidate_requests_per_s", "throughput",
                              direction="higher_is_better")],
                      {"engine": engine, "graph": f"{topology}-1e4",
                       "note": "the lifecycle arm of http-lifecycle ops; one pair per process"},
                      line="kind=pair", check={"path": "errors", "equals": 0})
            c3["check"]["same_trace"] = "candidate_stats"
            cells.append(c3)
    return cells


def q_cell() -> Dict[str, Any]:
    return {"id": "Q", "group": "Q", "block": "Q", "tier": TIERS["Q"], "kind": "delegated",
            "rule": "absolute", "report_only": False,
            "params": {"collector": "scripts/inspection_q_151.py",
                       "check": "knotrel scripts/measure-inspection-costs.py, unchanged, "
                                "on both arms; criteria C1-C4 of "
                                "docs/console-inspection-costs.md on the B arm (D5)"},
            "metrics": []}


def apply_windows(cells: List[Dict[str, Any]], factors: Dict[str, int]) -> None:
    """The ``apply_multipliers`` rule: every windowed cell has a factor, no unknown key."""
    windowed = {c["id"] for c in cells if "window" in c}
    unknown, missing = set(factors) - windowed, windowed - set(factors)
    if unknown or missing:
        raise SystemExit(f"window factors: unknown {sorted(unknown)[:5]}, "
                         f"missing {sorted(missing)[:5]}")
    for c in cells:
        if c["id"] not in windowed:
            continue
        factor = int(factors[c["id"]])
        if factor < 1 or factor & (factor - 1) or factor > 64:
            raise SystemExit(f"{c['id']}: factor {factor} is not a power of two in 1..64")
        k = c["window"]["base"] * factor
        for side in ("cf", "ref"):
            args = c["arms"][side]["args"]
            args[args.index("--k") + 1] = str(k)
        c["window"]["factor"] = factor
        c["params"]["k"] = k
        for m in c["metrics"]:
            spec = m.get("measurement", {})
            if spec.get("per_k"):
                m["measurement"] = {**aggregate(spec["intervals"], per=k), "per_k": True}


def build(scale: int = 1, factors: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    s = Sizes(scale)
    cells = memory_cells(s) + timed_cells(s) + [q_cell()]
    for c in cells:
        if "window" in c:
            c["params"]["k"] = c["window"]["base"]
    if factors is not None:
        apply_windows(cells, factors)
    ids = [c["id"] for c in cells]
    assert len(ids) == len(set(ids)), "cell ids are unique"
    counts: Dict[str, int] = {}
    for c in cells:
        counts[c["group"]] = counts.get(c["group"], 0) + 1
    return {
        "schema": "kr151-matrix-1", "protocol": PROTOCOL, "scale": scale,
        "windows": "set" if factors is not None else "unset",
        "arms": {"cf": "candidate (B)", "ref": "base (CUR)"},
        "rules": {"pairs": 24, "warmup_pairs": 2, "interval_order_statistics": [7, 18],
                  "coverage": 0.9773, "margins": MARGINS, "memory": MEMORY,
                  "g1": {"group": "M1", "engine": "compact-bfs",
                         "graphs": ["sparse-1e6", "star-1e6"], "metric": "live_after",
                         "class": "SMALLER"},
                  "g2": {"group": "M1", "min_full_v": 100_000, "metric": "live_after",
                         "min_bytes_per_registered_edge": G2_BYTES_PER_EDGE,
                         "edges_field": "edges_registered"},
                  "decision": "D1-D6 (section 6.7); strict D4: any SLOWER rejects",
                  "report_only_groups": ["M1-iso", "M6"],
                  "window_rule": "faster arm's pilot window >= 2 ms; powers of two, at most "
                                 "64x the base window (run_lifecycle_qualification.py "
                                 "apply_multipliers), capped by the target pool",
                  "measurement_limit": {"calibration": str(CALIBRATION.relative_to(ROOT)),
                                        "tick_ns": TICK_NS, "clock_read_ns": CLOCK_READ_NS},
                  "cap_hours": 1_000, "second_session_cap_hours": 1_000,
                  "tiers": [1, 2, 3], "block_order": BLOCK_ORDER,
                  "seed": SEED},
        "counts": dict(sorted(counts.items())),
        "cells": cells,
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--windows", type=Path)
    parser.add_argument("--scale", type=int, default=1)
    args = parser.parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cli_paths import confined  # noqa: PLC0415
    args.out = confined(args.out, "--out")
    factors = json.loads(confined(args.windows, "--windows").read_text()) \
        if args.windows else None
    matrix = build(args.scale, factors)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(matrix, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"out": str(args.out), "counts": matrix["counts"],
                      "cells": len(matrix["cells"]), "windows": matrix["windows"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
