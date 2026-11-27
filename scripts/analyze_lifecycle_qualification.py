#!/usr/bin/env python3
"""Decision analysis for the Knotrel v0.5.0 lifecycle qualification (experiments B and C).

Reads only the raw JSON lines written by ``run_lifecycle_qualification.py``, its
``run-log.jsonl``, ``provenance.json`` and the archived ``plan/matrix.json``. It runs no
benchmark.

**Validation (any failure stops the analysis):** the run is the ``final`` profile with no
``--only`` filter, or with exactly the filter named by ``--expect-only``: ``C`` (the CF5
L2 profile, whose plan must then be the complete C matrix of the expected scope and which
uses no window multipliers: ``--expect-multipliers-sha256 none``) or ``B4`` (the v1.2.0
release qualification, knotrel#182: the complete B4 matrix of the expected scope, with the
frozen window multipliers); the plan and the run log
list each cell once; every matrix cell has a raw file and a run-log record with exit 0, with
AC power recorded before it; ``provenance.json`` names the expected window-multiplier hash;
every raw file starts with a ``build`` record naming the expected knotrel revision and the
expected knotrel-benchmarks (probe source) revision, neither dirty, with the build variant
the cell requires; every timing cell has a matching ``verify``
record, exactly 2 warmup and 12 analyzed pairs, 6 with each arm first.

**Rules (frozen in the protocol before the final collection):**

- **B1-B4 (paired timing).** Each pair gives ``ln(candidate_ns / reference_ns)``. The
  interval and classification reuse ``summarize_metric`` from
  ``analyze_bc_qualification.py`` unchanged: ``[r(3), r(10)]`` at n = 12; PASS if the
  upper bound <= ln(1 + t), REGRESSION if the lower bound > ln(1 + t), otherwise
  INCONCLUSIVE. ``t`` is the cell's pre-declared tolerance. A cell whose median window in
  either arm is below 1 ms is TIMER_LIMITED: numbers are kept, no verdict. No extension.
- **B5 (memory).** Net live heap after construction (``count-alloc`` build, baseline
  subtracted). PASS if lifecycle <= 3.0 x plain, else FAIL. The reference arm is reported.
- **C (sustained resources)**, keyed on each checkpoint's ``cycle`` (0 = construction):
  - C1 (lifecycle): ``engine_vertices <= 2 * nodes + 1024`` at every checkpoint;
  - C2 (both arms): logical counts equal the independently computed expected counts at
    every checkpoint;
  - C3 (heap variant, lifecycle): net heap max over cycles 21-30 <= 1.25 x max over cycles
    1-10, and the least-squares slope over cycles 1-30 times 30 <= 10% of the mean over
    cycles 1-10;
  - C4 (rss variant, lifecycle): the same rules on net RSS; exceeding them is
    EXCEEDS_BUDGET (disclosure: allocator retention), not FAIL.
  Retained capacities (catalog and incident capacities, retired slots) are reported.

Usage::

    analyze_lifecycle_qualification.py RUN_DIR --expect-knotrel-rev SHA \\
        --expect-multipliers-sha256 SHA --expect-probes-rev SHA [--json OUT] [--markdown OUT]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List

from cli_paths import confined, confined_directory, contained_file

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("analyze_bc_qualification", HERE / "analyze_bc_qualification.py")
_bc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_bc)
summarize_metric = _bc.summarize_metric

TIMER_FLOOR_NS = 1_000_000
HEAP_BUDGET = 3.0
GROWTH_BUDGET = 1.25
SLOPE_BUDGET = 0.10
PAIRS = 12
WARMUP = 2


#: Application-gate reference cells (knotrel#180).
ATOMIC_REFERENCE = re.compile(r"-ops-atomic-")


class Invalid(Exception):
    """The run does not satisfy the frozen protocol."""


def lines(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def check_build(cell: Dict[str, Any], records: List[Dict[str, Any]], rev: str, probes_rev: str) -> None:
    build = records[0] if records else {}
    if build.get("kind") != "build":
        raise Invalid(f"{cell['id']}: missing build record")
    if build.get("knotrel_rev") != rev or build.get("knotrel_dirty") is not False:
        raise Invalid(f"{cell['id']}: built from {build.get('knotrel_rev')} dirty={build.get('knotrel_dirty')}")
    if build.get("probes_rev") != probes_rev or build.get("probes_dirty") is not False:
        raise Invalid(f"{cell['id']}: probes built from {build.get('probes_rev')} dirty={build.get('probes_dirty')}")
    if build.get("count_alloc") != (cell["binary"] == "core-count"):
        raise Invalid(f"{cell['id']}: wrong build variant")


def paired(cell: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    verify = [r for r in records if r.get("kind") == "verify"]
    warm = [r for r in records if r.get("kind") == "warmup"]
    pairs = [r for r in records if r.get("kind") == "pair"]
    if cell["binary"] == "core" and (len(verify) != 1 or not verify[0]["match"]):
        raise Invalid(f"{cell['id']}: missing or failed verify record")
    if any(r.get("answers_agree") is False for r in pairs + warm):
        raise Invalid(f"{cell['id']}: connectivity answers disagree")
    if len(warm) != WARMUP or len(pairs) != PAIRS:
        raise Invalid(f"{cell['id']}: {len(warm)} warmup and {len(pairs)} pairs")
    if sum(r["candidate_first"] for r in pairs) != PAIRS // 2:
        raise Invalid(f"{cell['id']}: unbalanced order")
    values = [{"B": float(r["reference_ns"]), "C": float(r["candidate_ns"])} for r in pairs]
    summary = summarize_metric("window_ns", values, cell["tolerance"])
    if min(summary["B_median"], summary["C_median"]) < TIMER_FLOOR_NS:
        summary["status"] = "TIMER_LIMITED"
    # Qualification 3, revision 2: planner references record whether they offered the
    # candidate's isolation (one plain request per lifecycle chunk). Copied, not judged here.
    flags = [r["atomicity_equivalent"] for r in pairs + warm if "atomicity_equivalent" in r]
    if not flags and re.search(r"-(ops|ops-query|events)-equivalent-", cell["id"]):
        raise Invalid(f"{cell['id']}: planner equivalent cell without atomicity records")
    if flags:
        if len(flags) != len(pairs + warm):
            raise Invalid(f"{cell['id']}: atomicity recorded for some pairs only")
        summary["atomicity_equivalent"] = all(flags)
        summary["reference_max_op_plain_ops"] = max(r["reference_max_op_plain_ops"] for r in pairs + warm)
        summary["reference_split_chunks"] = max(r["reference_split_chunks"] for r in pairs + warm)
    # knotrel#180: application-gate references record the gate mode, the gated chunks and
    # the untimed gate check in every pair; missing or mixed records are invalid.
    if ATOMIC_REFERENCE.search(cell["id"]):
        if not flags:
            raise Invalid(f"{cell['id']}: atomic reference cell without atomicity records")
        if any(r.get("atomicity_mode") != "application_gate" for r in pairs + warm):
            raise Invalid(f"{cell['id']}: atomic reference cell without application_gate mode")
        if any(not isinstance(r.get("gate_check"), dict) for r in pairs + warm):
            raise Invalid(f"{cell['id']}: atomic reference cell without gate check records")
        summary["atomicity_mode"] = "application_gate"
        summary["reference_gated_chunks"] = min(r["reference_gated_chunks"] for r in pairs + warm)
        summary["reference_lifecycle_chunks"] = max(r["reference_lifecycle_chunks"] for r in pairs + warm)
        summary["gate_check_pass"] = all(r["gate_check"].get("pass") is True for r in pairs + warm)
        if not summary["gate_check_pass"] or summary["reference_gated_chunks"] != summary["reference_lifecycle_chunks"]:
            summary["atomicity_equivalent"] = False
    summary["id"] = cell["id"]
    summary["experiment"] = cell["experiment"]
    summary["scale"] = cell.get("scale", 1)
    return summary


def checkpoints(cell_id: str, records: List[Dict[str, Any]], expected_cycles: int) -> Dict[int, Dict[str, Any]]:
    points = {r["cycle"]: r for r in records if r.get("kind") == "checkpoint"}
    if sorted(points) != list(range(expected_cycles + 1)):
        raise Invalid(f"{cell_id}: checkpoints {sorted(points)[:3]}... expected cycles 0-{expected_cycles}")
    return points


def memory(cells: Dict[str, Dict[str, Any]], raw: Path) -> List[Dict[str, Any]]:
    out = []
    for cell_id in cells:
        if cells[cell_id]["experiment"] != "B5" or "-plain-" not in cell_id:
            continue
        heap = {}
        for arm in ("plain", "lifecycle", "reference"):
            arm_id = cell_id.replace("-plain-", f"-{arm}-")
            heap[arm] = checkpoints(arm_id, lines(contained_file(raw, f"{arm_id}.jsonl", "raw record")), 0)[0]["net_heap_bytes"]
        ratio = heap["lifecycle"] / heap["plain"]
        out.append({"id": cell_id.replace("-plain-", "-"), "net_heap_bytes": heap,
                    "lifecycle_over_plain": ratio, "reference_over_plain": heap["reference"] / heap["plain"],
                    "status": "PASS" if ratio <= HEAP_BUDGET else "FAIL"})
    return out


def slope(xs: List[float], ys: List[float]) -> float:
    mx, my = statistics.fmean(xs), statistics.fmean(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)


def growth_checks(series: Dict[int, float]) -> Dict[str, Any]:
    early = [series[c] for c in range(1, 11)]
    late = [series[c] for c in range(21, 31)]
    cycles = list(range(1, 31))
    per_cycle = slope([float(c) for c in cycles], [series[c] for c in cycles])
    ratio = max(late) / max(early)
    projected = per_cycle * 30 / statistics.fmean(early)
    return {"late_over_early": ratio, "slope_per_cycle": per_cycle, "projected_growth_30": projected,
            "within": ratio <= GROWTH_BUDGET and projected <= SLOPE_BUDGET}


def sustained(cell: Dict[str, Any], records: List[Dict[str, Any]], cycles: int) -> Dict[str, Any]:
    cid = cell["id"]
    points = checkpoints(cid, records, cycles)
    lifecycle = "-lifecycle-" in cid
    result: Dict[str, Any] = {"id": cid}
    result["C2"] = "PASS" if all(p["counts"]["logical"] == p["expected"] for p in points.values()) else "FAIL"
    first, last = points[0]["counts"], points[cycles]["counts"]
    result["first_counts"], result["last_counts"] = first, last
    if lifecycle:
        ok = all(p["counts"]["engine_vertices"] <= 2 * p["counts"]["logical"][0] + 1024 for p in points.values())
        result["C1"] = "PASS" if ok else "FAIL"
        result["max_engine_vertices"] = max(p["counts"]["engine_vertices"] for p in points.values())
        result["max_retired_vertices"] = max(p["counts"]["retired_vertices"] for p in points.values())
    key = "net_heap_bytes" if cid.startswith("C-heap") else "net_rss_bytes"
    series = {c: float(p[key]) for c, p in points.items()}
    result.update({"metric": key, "first": series[0], "last": series[cycles], "max": max(series.values())})
    if cycles >= 30:
        checks = growth_checks(series)
        result.update(checks)
        if lifecycle:
            if key == "net_heap_bytes":
                result["C3"] = "PASS" if checks["within"] else "FAIL"
            else:
                result["C4"] = "PASS" if checks["within"] else "EXCEEDS_BUDGET"
    return result


#: ``--only`` filters an analysis may expect. CF5 L2 (frozen 2026-11-24) runs
#: ``--profile final --only C``: the sustained-resource rules, which have no timed cell.
EXPECTABLE_ONLY = ("C", "B4")


def unique_ids(records: List[Dict[str, Any]], what: str) -> Dict[str, Dict[str, Any]]:
    """Index records by ``id``, refusing a duplicate instead of keeping the last one."""
    out: Dict[str, Dict[str, Any]] = {}
    for record in records:
        if record["id"] in out:
            raise Invalid(f"{what}: duplicate cell {record['id']}")
        out[record["id"]] = record
    return out


def validate(run: Path, cells: Dict[str, Dict[str, Any]], rev: str, multipliers_sha: str,
             lifecycle_engines: str = "compact-bfs,ett,hdt",
             equivalent_references: bool = False, expected_only: str = "",
             atomic_references: bool = False) -> Dict[str, Any]:
    provenance = json.loads((run / "provenance.json").read_text())
    if expected_only and expected_only not in EXPECTABLE_ONLY:
        raise Invalid(f"--expect-only {expected_only!r} is not an accepted profile {EXPECTABLE_ONLY}")
    if provenance["profile"] != "final" or (provenance.get("only") or "") != expected_only:
        raise Invalid("not a complete final run" if not expected_only
                      else f"not a final --only {expected_only} run")
    # Runs before amendment 4 have no scope field and used every engine.
    if provenance.get("lifecycle_engines", "compact-bfs,ett,hdt") != lifecycle_engines:
        raise Invalid("lifecycle-engine scope differs from the expected scope")
    # v0.7.0 qualification 3: the capability-equivalent B4 cells must be expected
    # explicitly (--expect-equivalent-references) and recorded by the collector.
    if provenance.get("equivalent_references", False) != equivalent_references:
        raise Invalid("equivalent-reference cells differ from the expected matrix")
    # knotrel#180: the application-gate cells likewise (absent from earlier provenance).
    if provenance.get("atomic_references", False) != atomic_references:
        raise Invalid("atomic-reference cells differ from the expected matrix")
    runner = _runner()
    if atomic_references:
        plan = runner.matrix("final", lifecycle_engines, equivalent_references, True)
    else:
        plan = (runner.matrix("final", lifecycle_engines, True) if equivalent_references
                else runner.matrix("final", lifecycle_engines))
    expected = {c["id"] for c in plan if not expected_only or c["experiment"] in expected_only.split(",")}
    if set(cells) != expected:
        raise Invalid(f"plan matrix differs from the {lifecycle_engines} scope "
                      f"(missing {sorted(expected - set(cells))[:3]}, extra {sorted(set(cells) - expected)[:3]})")
    if expected_only == "C":
        # A C-only run scales no timed cell, so it records no multipliers; say so explicitly.
        if multipliers_sha != "none" or provenance.get("window_multipliers_sha256") is not None:
            raise Invalid("a C-only run uses no window multipliers (--expect-multipliers-sha256 none)")
    elif provenance.get("window_multipliers_sha256") != multipliers_sha:
        # A full run and a B4-only run (v1.2.0 release qualification, knotrel#182) scale
        # their timed cells with the frozen multipliers.
        raise Invalid("window multipliers differ from the frozen file")
    if expected_only and provenance.get("cells") != len(expected):
        raise Invalid(f"provenance records {provenance.get('cells')} cells, expected {len(expected)}")
    log = unique_ids(lines(run / "run-log.jsonl"), "run log")
    for cell_id in cells:
        record = log.get(cell_id)
        if record is None or record["exit"] != 0:
            raise Invalid(f"{cell_id}: missing or failed run")
        if "AC Power" not in record["host_before"]["power"]:
            raise Invalid(f"{cell_id}: not on AC power")
        if not contained_file(run / "raw", f"{cell_id}.jsonl", "raw record").exists():
            raise Invalid(f"{cell_id}: missing raw output")
    return provenance


def _runner():
    """The collector module, for the frozen matrix definition."""
    path = Path(__file__).resolve().parent / "run_lifecycle_qualification.py"
    spec = importlib.util.spec_from_file_location("run_lifecycle_qualification", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--expect-knotrel-rev", required=True)
    parser.add_argument("--expect-multipliers-sha256", required=True)
    parser.add_argument("--expect-probes-rev", required=True,
                        help="knotrel-benchmarks commit the probes were built from")
    parser.add_argument("--expect-lifecycle-engines", default="compact-bfs,ett,hdt",
                        help="lifecycle-engine scope of the run (amendment 4: compact-bfs)")
    parser.add_argument("--expect-equivalent-references", action="store_true",
                        help="the run includes the capability-equivalent B4 cells (v0.7.0 qualification 3)")
    parser.add_argument("--expect-atomic-references", action="store_true",
                        help="the run includes the application-gate B4 cells (knotrel#180)")
    parser.add_argument("--expect-only", default="", choices=("",) + EXPECTABLE_ONLY,
                        help="the run's recorded --only filter (CF5 L2: C; v1.2.0 RQ: B4); default: none")
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    args.run = confined_directory(args.run, "run directory")
    json_out = confined(args.json, "--json") if args.json else None
    markdown_out = confined(args.markdown, "--markdown") if args.markdown else None
    try:
        cells = unique_ids(json.loads((args.run / "plan" / "matrix.json").read_text()), "plan")
        validate(args.run, cells, args.expect_knotrel_rev, args.expect_multipliers_sha256,
                 args.expect_lifecycle_engines, args.expect_equivalent_references, args.expect_only,
                 **({"atomic_references": True} if args.expect_atomic_references else {}))
        raw = args.run / "raw"
        timing, resources = [], []
        for cell_id, cell in cells.items():
            records = lines(contained_file(raw, f"{cell_id}.jsonl", "raw record"))
            check_build(cell, records, args.expect_knotrel_rev, args.expect_probes_rev)
            if cell["experiment"] in ("B1", "B2", "B3", "B4"):
                timing.append(paired(cell, records))
            elif cell["experiment"] == "C":
                cycles = int(cell["args"][cell["args"].index("--cycles") + 1])
                resources.append(sustained(cell, records, cycles))
        report = {"timing": timing, "memory": memory(cells, raw), "sustained": resources}
    except Invalid as error:
        print(f"INVALID RUN: {error}", file=sys.stderr)
        return 3
    if json_out is not None:
        json_out.write_text(json.dumps(report, indent=1))
    md = ["| Cell | Scale | Reference median | Candidate median | Median change | Interval | Tolerance | Status |",
          "|---|---|---|---|---|---|---|---|"]
    for t in sorted(timing, key=lambda t: t["id"]):
        md.append(f"| {t['id']} | x{t['scale']} | {t['B_median']/1e6:.3f} ms | {t['C_median']/1e6:.3f} ms | "
                  f"{t['median_change_pct']:+.2f}% | [{t['interval_pct'][0]:+.2f}%, {t['interval_pct'][1]:+.2f}%] | "
                  f"{t['tolerance_pct']}% | {t['status']} |")
    md += ["", "| Memory cell | Plain net heap | Lifecycle net heap | Reference net heap | Lifecycle/plain | Status |",
           "|---|---|---|---|---|---|"]
    for m in report["memory"]:
        h = m["net_heap_bytes"]
        md.append(f"| {m['id']} | {h['plain']/2**20:.1f} MiB | {h['lifecycle']/2**20:.1f} MiB | "
                  f"{h['reference']/2**20:.1f} MiB | {m['lifecycle_over_plain']:.2f}x | {m['status']} |")
    md += ["", "| Sustained cell | Metric | First | Last | Max | Late/early | Projected 30-cycle growth | Max retired slots | C1 | C2 | C3/C4 |",
           "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(resources, key=lambda r: r["id"]):
        verdict = r.get("C3", r.get("C4", "-"))
        md.append(f"| {r['id']} | {r['metric']} | {r['first']/2**20:.1f} MiB | {r['last']/2**20:.1f} MiB | "
                  f"{r['max']/2**20:.1f} MiB | {r.get('late_over_early', float('nan')):.3f} | "
                  f"{r.get('projected_growth_30', float('nan')):+.3f} | {r.get('max_retired_vertices', '-')} | "
                  f"{r.get('C1', '-')} | {r['C2']} | {verdict} |")
    text = "\n".join(md) + "\n"
    if markdown_out is not None:
        markdown_out.write_text(text)
    else:
        sys.stdout.write(text)
    counts: Dict[str, int] = {}
    for t in timing:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    print(json.dumps({"timing_status_counts": counts}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
