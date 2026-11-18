#!/usr/bin/env python3
"""Interference marking of the v0.7.0 re-qualification (PROTOCOL.md section 10.3).

Disclosure only: it reads the conformance records of one attempt and never the
measurements, and it invalidates nothing. Written after FREEZE-A3 as section
10.3 specifies, and reviewed independently before the analysis.

For every gated child (``gate/gate-log.jsonl``, kind ``child``):

- ``background_share`` and ``baseline_share``: ``cpu_seconds_by_class`` of that
  class divided by the child's duration (share of one core);
- ``background_pcpu_mean``: mean ``background_pcpu_sum`` of the monitor's
  ``top`` records (``gate/activity-monitor.jsonl``) whose time is within the
  child, divided by 100 (share of one core); ``None`` when no record falls in
  the child (children shorter than the about one-second sampling interval).

A child is marked when any of the three measures is above ``LIMIT`` (0.25, one
quarter of one core). A cell is marked "read with caution" when any of its
children is marked (conservative: one child is enough).

Cells:

- ``A``: the ``cell_id`` of the observation (``A/raw-main`` and
  ``A/extension/raw-extension`` pair files) launched within the child (2 ms
  slack: gate times are rounded to the millisecond), one observation per child;
- ``BC``: the ``id`` of the run-log record at the same position (the collector
  runs the cells in run-log order, one gated child each); the label's program
  and arguments must match the record's ``argv``;
- ``r``, ``mreg``: the label without its repetition suffix
  (``-[warmup-]NN-ref|cand``); ``rmem``: the label without ``-ref|-cand``;
  ``mdesc``: the label.

Quantisation (disclosed, not corrected): ``cpu_seconds_by_class`` comes from
``ps`` CPU times with 0.01 s resolution, so a child shorter than 0.04 s with
one 0.01 s tick of baseline CPU is already above the limit. Each child records
``below_resolution`` (its class CPU is at most two ticks) so the report can
show it; the marking itself follows section 10.3 unchanged.

    report_v070r_interference.py CAMP --out OUT.json [--markdown OUT.md]
"""

from __future__ import annotations

import argparse
import bisect
import glob
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

LIMIT = 0.25
TICK = 0.01
SLACK_S = 0.002
EXPERIMENTS = ("A", "BC", "r", "rmem", "mdesc", "mreg")
REP_SUFFIX = re.compile(r"-(?:warmup-)?\d+-(?:ref|cand)$")
ARM_SUFFIX = re.compile(r"-(?:ref|cand)$")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def top_records(camp: Path) -> Tuple[List[float], List[float]]:
    tops = sorted((r["t"], float(r["background_pcpu_sum"])) for r in load_jsonl(camp / "gate" / "activity-monitor.jsonl")
                  if r.get("k") == "top" and "background_pcpu_sum" in r)
    return [t for t, _ in tops], [v for _, v in tops]


def a_observations(camp: Path) -> List[Tuple[float, str]]:
    out = []
    for pattern in ("A/raw-main/pair_*.json", "A/extension/raw-extension/pair_*.json"):
        for path in glob.glob(str(camp / pattern)):
            for obs in json.loads(Path(path).read_text())["observations"]:
                out.append((obs["launch_unix_ns"] / 1e9, obs["cell_id"]))
    return sorted(out)


def assign_cells(camp: Path, children: List[Dict[str, Any]]) -> List[str]:
    """Cell of every child, in order; raises ValueError when a child cannot be mapped."""
    cells: List[str] = []
    a_obs = a_observations(camp)
    a_times = [t for t, _ in a_obs]
    bc_log = load_jsonl(camp / "BC" / "run-log.jsonl") if (camp / "BC" / "run-log.jsonl").exists() else []
    bc_seen = 0
    a_used: set = set()
    for child in children:
        experiment, _, rest = child["label"].partition(":")
        if experiment == "A":
            # Gate times are rounded to the millisecond: allow SLACK_S on both sides; each
            # observation maps to exactly one child.
            i = bisect.bisect_left(a_times, child["start"] - SLACK_S)
            if i >= len(a_obs) or a_obs[i][0] > child["end"] + SLACK_S or i in a_used:
                raise ValueError(f"A child at {child['start']} has no unused observation launched within it")
            a_used.add(i)
            cells.append(a_obs[i][1])
        elif experiment == "BC":
            if bc_seen >= len(bc_log):
                raise ValueError("more BC children than run-log records")
            record = bc_log[bc_seen]
            bc_seen += 1
            argv = " ".join(str(a) for a in record["argv"])
            if not argv.startswith(rest) and not rest.startswith(argv[:len(rest)]):
                raise ValueError(f"BC child {bc_seen} does not match run-log record {record['id']}")
            cells.append(record["id"])
        elif experiment in ("r", "mreg"):
            cells.append(REP_SUFFIX.sub("", rest))
        elif experiment == "rmem":
            cells.append(ARM_SUFFIX.sub("", rest))
        elif experiment == "mdesc":
            cells.append(rest)
        else:
            raise ValueError(f"unknown experiment in label {child['label']!r}")
    if len(a_used) != len(a_obs):
        raise ValueError(f"{len(a_obs)} A observations but {len(a_used)} A children")
    if bc_seen != len(bc_log):
        raise ValueError(f"{len(bc_log)} BC run-log records but {bc_seen} BC children")
    return cells


def child_measures(child: Dict[str, Any], times: List[float], values: List[float]) -> Dict[str, Any]:
    duration = child["end"] - child["start"]
    cpu = child.get("cpu_seconds_by_class") or {}
    if duration <= 0:
        raise ValueError(f"child {child['label']!r} has duration {duration}")
    i, j = bisect.bisect_left(times, child["start"]), bisect.bisect_right(times, child["end"])
    samples = values[i:j]
    m = {
        "duration_s": round(duration, 3),
        "background_share": cpu.get("background", 0.0) / duration,
        "baseline_share": cpu.get("baseline", 0.0) / duration,
        "background_pcpu_mean": (sum(samples) / len(samples) / 100.0) if samples else None,
        "top_samples": len(samples),
    }
    over = [k for k in ("background_share", "baseline_share", "background_pcpu_mean") if m[k] is not None and m[k] > LIMIT]
    m["over"] = over
    m["below_resolution"] = bool(over) and all(
        k == "background_pcpu_mean" or cpu.get(k.split("_")[0], 0.0) <= 2 * TICK + 1e-9 for k in over)
    return m


def report(camp: Path) -> Dict[str, Any]:
    children = [r for r in load_jsonl(camp / "gate" / "gate-log.jsonl")
                if r.get("kind") == "child" and r["label"].partition(":")[0] in EXPERIMENTS]
    times, values = top_records(camp)
    cells = assign_cells(camp, children)
    per_cell: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for child, cell in zip(children, cells):
        experiment = child["label"].partition(":")[0]
        m = child_measures(child, times, values)
        c = per_cell.setdefault((experiment, cell), {
            "experiment": experiment, "cell": cell, "children": 0, "children_over": 0,
            "children_over_below_resolution": 0, "children_without_top_sample": 0,
            "max_background_share": 0.0, "max_baseline_share": 0.0, "max_background_pcpu_mean": None})
        c["children"] += 1
        c["children_over"] += bool(m["over"])
        c["children_over_below_resolution"] += m["below_resolution"]
        c["children_without_top_sample"] += m["top_samples"] == 0
        c["max_background_share"] = max(c["max_background_share"], m["background_share"])
        c["max_baseline_share"] = max(c["max_baseline_share"], m["baseline_share"])
        if m["background_pcpu_mean"] is not None:
            c["max_background_pcpu_mean"] = max(c["max_background_pcpu_mean"] or 0.0, m["background_pcpu_mean"])
    rows = sorted(per_cell.values(), key=lambda c: (EXPERIMENTS.index(c["experiment"]), c["cell"]))
    for c in rows:
        c["read_with_caution"] = c["children_over"] > 0
    return {
        "camp": str(camp), "limit_share_of_one_core": LIMIT, "rule": "PROTOCOL.md section 10.3 (disclosure only)",
        "children": len(children), "cells": len(rows),
        "cells_read_with_caution": sum(c["read_with_caution"] for c in rows),
        "rows": rows,
    }


def markdown(rep: Dict[str, Any]) -> str:
    lines = [f"Interference marking (PROTOCOL.md 10.3): {rep['cells_read_with_caution']} of {rep['cells']} cells "
             f"read with caution ({rep['children']} gated children, limit {rep['limit_share_of_one_core']:.0%} of one core).",
             "", "| Experiment | Cell | Children over / all | Over only by ps resolution | Max background | Max baseline | Max background %CPU mean |",
             "|---|---|---|---|---|---|---|"]
    pct = lambda v: "n/a" if v is None else f"{v:.1%}"
    for c in rep["rows"]:
        if c["read_with_caution"]:
            lines.append(f"| {c['experiment']} | `{c['cell']}` | {c['children_over']} / {c['children']} | "
                         f"{c['children_over_below_resolution']} | {pct(c['max_background_share'])} | "
                         f"{pct(c['max_baseline_share'])} | {pct(c['max_background_pcpu_mean'])} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("camp", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    rep = report(args.camp)
    args.out.write_text(json.dumps(rep, indent=1) + "\n")
    if args.markdown:
        args.markdown.write_text(markdown(rep))
    print(f"{rep['cells_read_with_caution']} of {rep['cells']} cells read with caution")
    return 0


if __name__ == "__main__":
    sys.exit(main())
