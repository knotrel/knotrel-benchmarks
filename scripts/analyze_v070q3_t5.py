#!/usr/bin/env python3
"""Decision analysis of check T5 (compaction pauses), v0.7.0 qualification 3 (PROTOCOL.md 5.1).

Reads only what ``run_v070q3_t5.py`` wrote: ``plan.json``, ``provenance.json``,
``run-log.jsonl`` and ``raw/*.jsonl``. It runs no benchmark.

**Validation (any failure: the analysis stops, exit 1, T5 has no PASS).**
- the plan is the frozen one (``run_v070q3_t5.plan`` with the recorded order seed); every
  run has a raw file and a run-log record with exit 0, AC power recorded before it, in plan
  order;
- every raw file starts with a ``build`` record: arm B built from ``--expect-base-rev``, arm
  C from ``--expect-cand-rev``, probes from ``--expect-probes-rev``, none dirty, timing build;
- a ``pauses_start`` record with the frozen workload, cycle records 1-600 in order and a
  ``pauses_end`` record whose ``max_ns`` is the largest cycle maximum;
- **same duration and workload:** within a topology, every run (both arms, warmup
  included) has the same schedule digest, result digest, number of calls per cycle and
  final logical counts, and the same compaction cycles. A compaction cycle is one after
  which ``retired_vertices`` is lower than after the previous cycle;
- exactly 30 compaction cycles, the last at cycle 600, so the 30 intervals cover every
  cycle; 12 analyzed pairs, six with each arm first.

**Metrics per run.**
- ``P_max``: the longest single lifecycle call of the run (``pauses_end.max_ns``);
- ``P_90``: the per-interval maxima (interval k = the cycles after compaction k-1, up to and
  including compaction k), sorted; the 27th of the 30.

**Per pair** d = ln(C / B) for each metric (C and B runs of the same pair).

**Interval and rule (both metrics, each topology; frozen before collection).** Over the 12
analyzed pairs, sorted d: interval [d(3), d(10)], a distribution-free interval for the
median of d with coverage 1 - 2 P(Bin(12, 1/2) <= 2) = 96.1%. Point estimate: median of d.
With t = 0.25 (the T5 tolerance, MATRIX ``experiments.T5.tolerance``):
- PASS if d(10) <= ln(1.25);
- REGRESSION if d(3) > ln(1.25);
- INCONCLUSIVE otherwise.
This is ``summarize_metric`` of ``analyze_bc_qualification.py``, reused unchanged. Six
deciding results; a non-PASS goes to the maintainer. Absolute values (medians, minima and
maxima per arm, wall and timed run durations) are reported beside each result.

    analyze_v070q3_t5.py T5_DIR --expect-base-rev SHA --expect-cand-rev SHA \\
        --expect-probes-rev SHA [--json OUT]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_v070q3_t5 as collector  # noqa: E402

_spec = importlib.util.spec_from_file_location("analyze_bc_qualification", HERE / "analyze_bc_qualification.py")
_bc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_bc)
summarize_metric = _bc.summarize_metric

TOLERANCE = 0.25
INTERVALS = 30
P90_RANK = 27  # 1-based rank among the 30 sorted interval maxima


class Invalid(Exception):
    """The T5 collection does not satisfy the frozen protocol."""


def lines(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_summary(run_id: str, records: List[Dict[str, Any]], rev: str, probes_rev: str) -> Dict[str, Any]:
    build = records[0] if records else {}
    if build.get("kind") != "build":
        raise Invalid(f"{run_id}: missing build record")
    if build.get("knotrel_rev") != rev or build.get("knotrel_dirty") is not False:
        raise Invalid(f"{run_id}: built from {build.get('knotrel_rev')} dirty={build.get('knotrel_dirty')}, expected {rev}")
    if build.get("probes_rev") != probes_rev or build.get("probes_dirty") is not False:
        raise Invalid(f"{run_id}: probes {build.get('probes_rev')} dirty={build.get('probes_dirty')}")
    if build.get("count_alloc") is not False:
        raise Invalid(f"{run_id}: not the timing build")
    start = [r for r in records if r.get("kind") == "pauses_start"]
    end = [r for r in records if r.get("kind") == "pauses_end"]
    cycles = [r for r in records if r.get("kind") == "cycle"]
    if len(start) != 1 or len(end) != 1:
        raise Invalid(f"{run_id}: {len(start)} start and {len(end)} end records")
    start, end = start[0], end[0]
    want = {"nodes": collector.NODES, "cycles": collector.CYCLES, "churn_percent": collector.CHURN_PERCENT,
            "seed": collector.SEED, "reuse": "fresh"}
    got = {k: start.get(k) for k in want}
    if got != want:
        raise Invalid(f"{run_id}: workload {got}, expected {want}")
    if [r["cycle"] for r in cycles] != list(range(1, collector.CYCLES + 1)):
        raise Invalid(f"{run_id}: cycle records are not 1-{collector.CYCLES} in order")
    if end["max_ns"] != max(r["max_ns"] for r in cycles) or end["calls"] != sum(r["calls"] for r in cycles):
        raise Invalid(f"{run_id}: end record disagrees with the cycle records")
    compactions, previous = [], start["retired_vertices"]
    for r in cycles:
        if r["retired_vertices"] < previous:
            compactions.append(r["cycle"])
        previous = r["retired_vertices"]
    if len(compactions) != INTERVALS or compactions[-1] != collector.CYCLES:
        raise Invalid(f"{run_id}: {len(compactions)} compactions, last at {compactions[-1:]}; "
                      f"expected {INTERVALS}, the last at cycle {collector.CYCLES}")
    maxima, begin = [], 0
    for c in compactions:
        maxima.append(max(r["max_ns"] for r in cycles[begin:c]))
        begin = c
    return {"P_max": float(end["max_ns"]), "P_90": float(sorted(maxima)[P90_RANK - 1]),
            "interval_maxima_ns": maxima, "compactions": compactions,
            "workload": {"schedule_digest": end["schedule_digest"], "result_digest": end["result_digest"],
                         "calls_per_cycle": [r["calls"] for r in cycles], "final_logical": end["final_logical"],
                         "compactions": compactions},
            "wall_ns": end["wall_ns"], "timed_ns": end["timed_ns"], "calls": end["calls"],
            "max_ops": sorted({r["max_op"] for r in cycles if r["cycle"] in compactions})}


def describe(values: List[float]) -> Dict[str, float]:
    return {"median": statistics.median(values), "min": min(values), "max": max(values)}


def analyze(directory: Path, base_rev: str, cand_rev: str, probes_rev: str) -> Dict[str, Any]:
    provenance = json.loads((directory / "provenance.json").read_text())
    expected_plan = collector.plan(int(provenance["order_seed"]))
    if json.loads((directory / "plan.json").read_text()) != expected_plan:
        raise Invalid("plan.json is not the frozen plan for the recorded order seed")
    log = lines(directory / "run-log.jsonl")
    if [r["id"] for r in log] != [r["id"] for r in expected_plan]:
        raise Invalid(f"run log has {len(log)} records, not the {len(expected_plan)} planned runs in order")
    for r in log:
        if r["exit"] != 0:
            raise Invalid(f"{r['id']}: exit {r['exit']}")
        if "AC Power" not in str(r.get("host_before", {}).get("power", "")):
            raise Invalid(f"{r['id']}: AC power not recorded before the run")
        if r["argv"][1:] != collector.child_args(r["topology"]):
            raise Invalid(f"{r['id']}: arguments {r['argv'][1:]}")
    revs = {"B": base_rev, "C": cand_rev}
    runs = {r["id"]: run_summary(r["id"], lines(directory / "raw" / f"{r['id']}.jsonl"), revs[r["arm"]], probes_rev)
            for r in expected_plan}
    results, absolute = [], {}
    for topology in collector.TOPOLOGIES:
        mine = [r for r in expected_plan if r["topology"] == topology]
        reference = runs[mine[0]["id"]]["workload"]
        for r in mine:
            if runs[r["id"]]["workload"] != reference:
                raise Invalid(f"{r['id']}: workload or compaction cycles differ from {mine[0]['id']}")
        analyzed = [r for r in mine if r["pair"] >= 0]
        if len(analyzed) != 2 * collector.PAIRS:
            raise Invalid(f"{topology}: {len(analyzed)} analyzed runs")
        firsts = [r["arm"] for r in analyzed if r["slot"] == 0]
        if firsts.count("C") != collector.PAIRS // 2:
            raise Invalid(f"{topology}: unbalanced order")
        by_pair = {p: {r["arm"]: runs[r["id"]] for r in analyzed if r["pair"] == p} for p in range(collector.PAIRS)}
        arms = {arm: [by_pair[p][arm] for p in range(collector.PAIRS)] for arm in ("B", "C")}
        absolute[topology] = {
            arm: {"wall_ms": describe([x["wall_ns"] / 1e6 for x in arms[arm]]),
                  "timed_ms": describe([x["timed_ns"] / 1e6 for x in arms[arm]]),
                  "mean_call_ns": describe([x["timed_ns"] / x["calls"] for x in arms[arm]]),
                  "calls": arms[arm][0]["calls"],
                  "compacting_call_kinds": sorted({k for x in arms[arm] for k in x["max_ops"]})}
            for arm in ("B", "C")}
        for metric in ("P_max", "P_90"):
            values = [{"B": by_pair[p]["B"][metric], "C": by_pair[p]["C"][metric]} for p in range(collector.PAIRS)]
            summary = summarize_metric(metric, values, TOLERANCE)
            summary.update({
                "id": f"T5-{metric}-{topology}", "topology": topology,
                "absolute_ms": {arm: describe([v[arm] / 1e6 for v in values]) for arm in ("B", "C")},
                "pair_values_ms": [{"pair": p, "B": values[p]["B"] / 1e6, "C": values[p]["C"] / 1e6}
                                   for p in range(collector.PAIRS)]})
            results.append(summary)
    return {"check": "T5", "tolerance": TOLERANCE, "intervals_per_run": INTERVALS, "p90_rank": P90_RANK,
            "provenance": provenance, "results": results, "absolute": absolute,
            "non_pass": [r["id"] for r in results if r["status"] != "PASS"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--expect-base-rev", required=True)
    parser.add_argument("--expect-cand-rev", required=True)
    parser.add_argument("--expect-probes-rev", required=True)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    try:
        out = analyze(args.directory, args.expect_base_rev, args.expect_cand_rev, args.expect_probes_rev)
    except (Invalid, OSError, KeyError, ValueError) as error:
        print(f"T5 INVALID: {error}", file=sys.stderr)
        return 1
    text = json.dumps(out, indent=1)
    if args.json:
        args.json.write_text(text)
    for r in out["results"]:
        print(f"{r['id']}: {r['status']} median {r['median_change_pct']:+.1f}% interval "
              f"[{r['interval_pct'][0]:+.1f}%, {r['interval_pct'][1]:+.1f}%] | B median "
              f"{r['absolute_ms']['B']['median']:.2f} ms, C median {r['absolute_ms']['C']['median']:.2f} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
