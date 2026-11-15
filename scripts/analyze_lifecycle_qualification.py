#!/usr/bin/env python3
"""Decision analysis for the Knotrel v0.5.0 lifecycle qualification (experiments B and C).

Reads only the raw JSON lines written by ``run_lifecycle_qualification.py`` and the
archived ``plan/matrix.json``. It runs no benchmark.

Rules (frozen in the protocol before the final collection):

- **B1-B4 (paired timing).** Each pair gives ``ln(candidate_ns / reference_ns)``. The
  interval and classification reuse ``summarize_metric`` from
  ``analyze_bc_qualification.py`` unchanged: ``[r(3), r(10)]`` at n = 12; PASS if the
  upper bound <= ln(1 + t), REGRESSION if the lower bound > ln(1 + t), otherwise
  INCONCLUSIVE. ``t`` is the cell's pre-declared tolerance in the matrix. A cell whose
  median window (either arm) is below 1 ms is TIMER_LIMITED: it keeps its numbers and
  carries no verdict. There is no extension.
- **B5 (memory).** Live heap after construction (``count-alloc`` build, one run).
  PASS if lifecycle <= 3.0 x plain, else FAIL. The reference arm is reported only.
- **C (sustained resources), lifecycle arm:**
  - C1: ``engine_vertices <= 2 * nodes + 1024`` at every checkpoint (FAIL otherwise);
  - C2: ``nodes`` equals its construction value at every checkpoint, and for
    ``toggle`` every count equals its construction value (FAIL otherwise);
  - C3 (heap variant): max live heap over cycles 21-30 <= 1.25 x max over cycles 1-10;
  - C4 (rss variant): the same rule on RSS. Allocator retention makes RSS a disclosure
    item: exceeding it is EXCEEDS_BUDGET, not FAIL.
  The reference arm (``fresh`` only) is reported for context, without a verdict.

Usage: ``analyze_lifecycle_qualification.py RUN_DIR [--json OUT] [--markdown OUT]``.
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
_spec = importlib.util.spec_from_file_location("analyze_bc_qualification", HERE / "analyze_bc_qualification.py")
_bc = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_bc)
summarize_metric = _bc.summarize_metric

TIMER_FLOOR_NS = 1_000_000
HEAP_BUDGET = 3.0
GROWTH_BUDGET = 1.25


def lines(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def paired(cell: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    pairs = [r for r in records if r.get("kind") == "pair"]
    verify = [r for r in records if r.get("kind") == "verify"]
    if verify and not verify[0]["match"]:
        raise SystemExit(f"{cell['id']}: digest mismatch")
    if any(r.get("answers_agree") is False for r in pairs):
        raise SystemExit(f"{cell['id']}: connectivity answers disagree")
    values = [{"B": float(r["reference_ns"]), "C": float(r["candidate_ns"])} for r in pairs]
    summary = summarize_metric("window_ns", values, cell["tolerance"])
    if min(summary["B_median"], summary["C_median"]) < TIMER_FLOOR_NS:
        summary["status"] = "TIMER_LIMITED"
    summary["id"] = cell["id"]
    summary["experiment"] = cell["experiment"]
    return summary


def memory(cells: Dict[str, Dict[str, Any]], raw: Path) -> List[Dict[str, Any]]:
    out = []
    for cell_id, cell in cells.items():
        if cell["experiment"] != "B5" or "-plain-" not in cell_id:
            continue
        heap = {}
        for arm in ("plain", "lifecycle", "reference"):
            records = lines(raw / f"{cell_id.replace('-plain-', f'-{arm}-')}.jsonl")
            heap[arm] = records[0]["live_heap_bytes"]
        ratio = heap["lifecycle"] / heap["plain"]
        out.append({"id": cell_id.replace("-plain-", "-"), "heap_bytes": heap,
                    "lifecycle_over_plain": ratio, "reference_over_plain": heap["reference"] / heap["plain"],
                    "status": "PASS" if ratio <= HEAP_BUDGET else "FAIL"})
    return out


def growth(values: List[float]) -> float:
    early = max(values[1:11])
    late = max(values[21:31])
    return late / early


def sustained(cell: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    points = [r for r in records if r.get("kind") == "checkpoint"]
    cid = cell["id"]
    lifecycle = "-lifecycle-" in cid
    result: Dict[str, Any] = {"id": cid, "checkpoints": len(points)}
    if lifecycle:
        first = points[0]["counts"]
        c1 = all(p["counts"]["engine_vertices"] <= 2 * p["counts"]["nodes"] + 1024 for p in points)
        if cid.endswith("toggle-100000"):
            c2 = all(p["counts"] == first for p in points)
        else:
            c2 = all(p["counts"]["nodes"] == first["nodes"] for p in points)
        result.update({"C1": "PASS" if c1 else "FAIL", "C2": "PASS" if c2 else "FAIL",
                       "max_engine_vertices": max(p["counts"]["engine_vertices"] for p in points),
                       "nodes": first["nodes"]})
    key = "live_heap_bytes" if cid.startswith("C-heap") else "rss_bytes"
    series = [float(p[key]) for p in points]
    result["metric"] = key
    result["first"], result["last"], result["max"] = series[0], series[-1], max(series)
    if len(series) >= 31:
        ratio = growth(series)
        result["late_over_early"] = ratio
        if lifecycle:
            ok = ratio <= GROWTH_BUDGET
            result["C3" if key == "live_heap_bytes" else "C4"] = (
                "PASS" if ok else ("FAIL" if key == "live_heap_bytes" else "EXCEEDS_BUDGET"))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run", type=Path)
    parser.add_argument("--json", type=Path)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    cells = {c["id"]: c for c in json.loads((args.run / "plan" / "matrix.json").read_text())}
    raw = args.run / "raw"
    timing, resources = [], []
    for cell_id, cell in cells.items():
        path = raw / f"{cell_id}.jsonl"
        if not path.exists():
            continue
        records = lines(path)
        if cell["experiment"] in ("B1", "B2", "B3", "B4"):
            timing.append(paired(cell, records))
        elif cell["experiment"] == "C":
            resources.append(sustained(cell, records))
    report = {"timing": timing, "memory": memory(cells, raw), "sustained": resources}
    if args.json:
        args.json.write_text(json.dumps(report, indent=1))
    md = ["| Cell | Reference median | Candidate median | Median change | Interval | Tolerance | Status |",
          "|---|---|---|---|---|---|---|"]
    for t in sorted(timing, key=lambda t: t["id"]):
        md.append(f"| {t['id']} | {t['B_median']/1e6:.3f} ms | {t['C_median']/1e6:.3f} ms | "
                  f"{t['median_change_pct']:+.2f}% | [{t['interval_pct'][0]:+.2f}%, {t['interval_pct'][1]:+.2f}%] | "
                  f"{t['tolerance_pct']}% | {t['status']} |")
    md += ["", "| Memory cell | Plain heap | Lifecycle heap | Reference heap | Lifecycle/plain | Status |",
           "|---|---|---|---|---|---|"]
    for m in report["memory"]:
        h = m["heap_bytes"]
        md.append(f"| {m['id']} | {h['plain']/2**20:.1f} MiB | {h['lifecycle']/2**20:.1f} MiB | "
                  f"{h['reference']/2**20:.1f} MiB | {m['lifecycle_over_plain']:.2f}x | {m['status']} |")
    md += ["", "| Sustained cell | Metric | First | Last | Max | Late/early | C1 | C2 | C3/C4 |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(resources, key=lambda r: r["id"]):
        verdict = r.get("C3", r.get("C4", "-"))
        md.append(f"| {r['id']} | {r['metric']} | {r['first']/2**20:.1f} MiB | {r['last']/2**20:.1f} MiB | "
                  f"{r['max']/2**20:.1f} MiB | {r.get('late_over_early', float('nan')):.3f} | "
                  f"{r.get('C1', '-')} | {r.get('C2', '-')} | {verdict} |")
    text = "\n".join(md) + "\n"
    if args.markdown:
        args.markdown.write_text(text)
    else:
        sys.stdout.write(text)
    counts: Dict[str, int] = {}
    for t in timing:
        counts[t["status"]] = counts.get(t["status"], 0) + 1
    print(json.dumps({"timing_status_counts": counts}), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
