#!/usr/bin/env python3
"""Analyzer of the knotrel#151 comparison (compact internal node indices, option B64).

    analyze_151.py --matrix M --run DIR [--run DIR2] [--dispositions D.json] [--out A.json]

knotrel ``docs/design/compact-node-index.md``, sections 6.5-6.7 (approved 2026-11-26).
Run once, after collection by ``run_151.py campaign`` (``run_cf5.py`` sessions; a second
``--run`` is the session 2 resumed from the first, as for CF5). Arm ``cf`` is the
candidate B, arm ``ref`` the base CUR.

- **Timed cells** (I, R, P, C): per metric the 24 paired log ratios ``ln(B / CUR)``
  (``ln(CUR / B)`` for throughput), interval ``[r(7), r(18)]``, margins time 10 %, tail
  25 %, throughput 10 %: FASTER / SLOWER / EQUIVALENT / INCONCLUSIVE, and TIMER_LIMITED by
  the CF5 section 6.1 rule (``analyze_cf5.classify_paired``). Limits that depend on the
  workload (``timed_ops_from``, ``intervals_from``) are computed from the observations,
  which must agree on that count.
- **Memory cells** (M): ``q = B / CUR`` per metric: SMALLER (``q <= 0.90``), LARGER
  (``q >= 1.05``), SIMILAR; UNDEFINED when CUR is not positive. M1-iso and M6 are
  report-only.
- **G1:** CB-L ``M1`` ``sparse-1e6`` and ``star-1e6``: ``live_after`` SMALLER.
  **G2:** every M1 cell with ``V >= 10^5``, both engines: ``(CUR - B) / E_r >= 8`` bytes
  per registered edge on ``live_after`` (``E_r``: the observation's ``edges_registered``,
  equal in both arms).
- **Decision (6.7):** D1 correctness (no failed session or cell), D2 (G1 and G2), D3 (no
  M1-M5 metric LARGER), D4 (no primary or tail metric of I, R, P, C SLOWER; strict),
  D5 (Q: C1-C4 on the candidate, from the delegated collector's ``q.json``), D6 (every
  INCONCLUSIVE, TIMER_LIMITED, UNDEFINED, incomplete or missing result has a written
  maintainer disposition in ``--dispositions``: ``{"CELL[/METRIC]": {"disposition":
  "accept" | "follow-up", "note": ...}}``). REJECT if D1-D5 fails; ADOPT only if D1-D6
  all pass (every disposition ``accept``); otherwise NO DECISION, with what is pending.
- Refused: preparatory or nonconforming runs, a matrix other than the recorded one,
  ``scale != 1``, unset windows, and a quick Q (``q.json`` from ``--quick``).
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyze_cf5 as cf5  # noqa: E402
from cli_paths import confined, confined_directory  # noqa: E402

TIMED_GROUPS = ("I1", "I2", "I3", "R1", "R2", "R3", "R4", "R5", "P1", "P2", "P3", "P4",
                "C1", "C2", "C3")
MEMORY_GROUPS = ("M1", "M2", "M3", "M4", "M5")
NEEDS_DISPOSITION = {"INCONCLUSIVE", "TIMER_LIMITED", "UNDEFINED", "INCOMPLETE", "NOT_RUN"}


def memory_class(b: float, cur: float, rules: Dict[str, float]) -> Dict[str, Any]:
    if cur <= 0:
        return {"q": None, "class": "UNDEFINED"}
    q = b / cur
    if q <= rules["smaller_at_most"]:
        cls = "SMALLER"
    elif q >= rules["larger_at_least"]:
        cls = "LARGER"
    else:
        cls = "SIMILAR"
    return {"q": q, "class": cls}


def per_op_limit(timed_ops: int) -> float:
    """CF5 ``per_op_sum``: timed_ops * read + 3 * tick * sqrt(timed_ops / 6)."""
    return timed_ops * cf5_constants()["read"] + 3 * cf5_constants()["tick"] * \
        math.sqrt(timed_ops / 6)


_CONSTANTS: Dict[str, float] = {}


def cf5_constants() -> Dict[str, float]:
    if not _CONSTANTS:
        import compact_index_matrix as m  # noqa: PLC0415
        _CONSTANTS.update({"tick": m.TICK_NS, "read": m.CLOCK_READ_NS})
    return _CONSTANTS


def resolved(cell: Dict[str, Any], pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The cell with workload-dependent measurement limits filled from the observations."""
    out = copy.deepcopy(cell)
    for m in out["metrics"]:
        spec = m.get("measurement")
        if not spec or spec.get("limit_ns") is not None:
            continue
        field = spec.get("timed_ops_from") or spec.get("intervals_from")
        values = {p[arm]["object"][field] for p in pairs for arm in ("cf", "ref")}
        if len(values) != 1:
            raise SystemExit(f"{cell['id']} {m['name']}: {field} differs between "
                             f"observations: {sorted(values)[:4]}")
        count = values.pop()
        if spec.get("timed_ops_from"):
            spec["timed_ops"] = count
            spec["limit_ns"] = round(per_op_limit(count), 1)
        else:
            spec["intervals"] = count
            c = cf5_constants()
            spec["limit_ns"] = round(count * (c["tick"] + c["read"]) / spec.get("per", 1), 3)
    return out


def merge_runs(runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Per cell: state and lines; a session 2 replaces only INCOMPLETE and NOT_RUN cells."""
    states: Dict[str, Dict[str, Any]] = {}
    lines: Dict[str, List[Dict[str, Any]]] = {}
    for index, run in enumerate(runs):
        for cell_id, state in run["status"]["cells"].items():
            if index > 0 and states.get(cell_id, {}).get("state") not in ("INCOMPLETE",
                                                                          "NOT_RUN"):
                continue
            states[cell_id] = state
            lines[cell_id] = [l for l in run["raw"] if l.get("cell") == cell_id
                              and "failed_observation" not in l]
    return {"states": states, "lines": lines}


def q_result(states: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    state = states.get("Q", {"state": "NOT_RUN"})
    if state.get("state") != "DELEGATED_DONE":
        return {"state": state.get("state"), "d5": "pending"}
    run_dir = Path(state["attempts"][-1]["run_dir"])
    path = run_dir / "q.json"
    if not path.is_file():
        return {"state": "MISSING", "d5": "pending", "path": str(path)}
    q = json.loads(path.read_text())
    if q.get("quick"):
        raise SystemExit("the Q check ran with --quick: refused")
    return {"state": "DONE", "base": q.get("base"), "cand": q.get("cand"),
            "d5": "pass" if q.get("d5_pass") else "fail"}


def analyze(matrix: Dict[str, Any], runs: List[Dict[str, Any]],
            dispositions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if matrix.get("scale", 1) != 1:
        raise SystemExit("a scaled (smoke) matrix is never classified")
    if matrix.get("windows") != "set":
        raise SystemExit("the matrix windows are unset: no frozen campaign")
    dispositions = dispositions or {}
    rules = matrix["rules"]
    merged = merge_runs(runs)
    failed = any(r["status"]["campaign"] == "failed" for r in runs)
    cells: Dict[str, Dict[str, Any]] = {}
    for cell in matrix["cells"]:
        state = merged["states"].get(cell["id"], {"state": "NOT_RUN"})
        entry: Dict[str, Any] = {"group": cell["group"], "block": cell["block"],
                                 "report_only": cell.get("report_only", False),
                                 "state": state["state"]}
        lines = merged["lines"].get(cell["id"], [])
        if cell["kind"] == "paired":
            measured = [l for l in lines if not l.get("warmup")]
            if state["state"] == "COMPLETE":
                entry["metrics"] = cf5.classify_paired(resolved(cell, measured), measured)
            elif measured:
                entry["incomplete_medians"] = cf5.medians(cell, measured)
        elif cell["kind"] == "deterministic" and state["state"] == "COMPLETE":
            arms = {l["arm"]: l for l in lines}
            entry["metrics"] = {}
            for m in cell["metrics"]:
                b, cur = arms["cf"]["metrics"][m["name"]], arms["ref"]["metrics"][m["name"]]
                entry["metrics"][m["name"]] = {"cf": b, "ref": cur,
                                               **memory_class(b, cur, rules["memory"])}
            entry["edges_registered"] = arms["ref"].get("object", {}).get(
                rules["g2"]["edges_field"])
        elif cell["kind"] == "delegated":
            entry["q"] = q_result(merged["states"])
        cells[cell["id"]] = entry
    by_id = {c["id"]: c for c in matrix["cells"]}

    # G1 and G2 (section 6.6).
    g1_spec, g2_spec = rules["g1"], rules["g2"]
    g1_cells = {cid: c for cid, c in by_id.items() if c["group"] == g1_spec["group"]
                and c["params"]["engine"] == g1_spec["engine"]
                and c["params"]["graph"] in g1_spec["graphs"]}
    g1_items = {cid: cells[cid].get("metrics", {}).get(g1_spec["metric"], {}).get("class",
                                                                                   "MISSING")
                for cid in sorted(g1_cells)}
    g1 = "pending" if any(v in ("MISSING", "UNDEFINED") for v in g1_items.values()) or \
        len(g1_items) != len(g1_spec["graphs"]) else \
        ("pass" if all(v == g1_spec["class"] for v in g1_items.values()) else "fail")
    g2_items: Dict[str, Any] = {}
    for cid, c in sorted(by_id.items()):
        if c["group"] != g2_spec["group"] or c["params"]["full_v"] < g2_spec["min_full_v"]:
            continue
        m = cells[cid].get("metrics", {}).get(g2_spec["metric"])
        edges = cells[cid].get("edges_registered")
        if m is None or not edges:
            g2_items[cid] = None
            continue
        g2_items[cid] = (m["ref"] - m["cf"]) / edges
    if any(v is None for v in g2_items.values()):
        g2 = "pending"
    else:
        g2 = "pass" if all(v >= g2_spec["min_bytes_per_registered_edge"]
                           for v in g2_items.values()) else "fail"

    # Decision items.
    larger, slower, needs = [], [], []
    for cid, entry in cells.items():
        cell = by_id[cid]
        if cell["kind"] == "delegated":
            continue
        if "metrics" not in entry:
            if not entry["report_only"]:
                needs.append({"item": cid, "class": entry["state"]})
            continue
        for name, m in entry["metrics"].items():
            cls = m["class"]
            if cell["group"] in MEMORY_GROUPS and cls == "LARGER":
                larger.append(f"{cid}/{name}")
            if cell["group"] in TIMED_GROUPS and cls == "SLOWER":
                slower.append(f"{cid}/{name}")
            if cls in NEEDS_DISPOSITION and not entry["report_only"]:
                needs.append({"item": f"{cid}/{name}", "class": cls})
    cell_failed = [cid for cid, e in cells.items() if e["state"] == "FAILED"]
    d1 = "fail" if failed or cell_failed else "pass"
    d2 = "pass" if g1 == "pass" and g2 == "pass" else \
        ("fail" if "fail" in (g1, g2) else "pending")
    d3 = "fail" if larger else "pass"
    d4 = "fail" if slower else "pass"
    q = cells.get("Q", {}).get("q", {"d5": "pending"})
    d5 = q["d5"]
    unresolved, follow_up = [], []
    for item in needs:
        cid = item["item"].split("/")[0]
        given = dispositions.get(item["item"]) or dispositions.get(cid)
        if not given:
            unresolved.append(item)
        elif given.get("disposition") != "accept":
            follow_up.append({**item, "disposition": given})
    d6 = "pass" if not unresolved and not follow_up else "pending"
    items = {"D1": d1, "D2": d2, "D3": d3, "D4": d4, "D5": d5, "D6": d6}
    if "fail" in (d1, d2, d3, d4, d5):
        decision = "REJECT"
    elif all(v == "pass" for v in items.values()):
        decision = "ADOPT"
    else:
        decision = "NO DECISION"
    return {"schema": "kr151-analysis-1", "protocol": matrix.get("protocol"),
            "arms": {"cf": "candidate (B)", "ref": "base (CUR)"},
            "campaign_failed": failed, "cells": cells,
            "benefit": {"G1": {"status": g1, "classes": g1_items},
                        "G2": {"status": g2, "bytes_per_registered_edge": g2_items}},
            "decision": {"result": decision, "items": items, "failed_cells": cell_failed,
                         "larger": larger, "slower": slower,
                         "needs_disposition": unresolved, "follow_up": follow_up,
                         "q": q}}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--dispositions", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if len(args.run) > 2:
        parser.error("at most two sessions")
    args.matrix = confined(args.matrix, "--matrix")
    args.run = [confined_directory(r, "--run") for r in args.run]
    dispositions = json.loads(confined(args.dispositions, "--dispositions").read_text()) \
        if args.dispositions else None
    if args.out:
        args.out = confined(args.out, "--out")
        if args.out.exists():
            parser.error(f"{args.out} already exists")
    text = args.matrix.read_bytes()
    sha = hashlib.sha256(text).hexdigest()
    runs = [cf5.load_run(r, sha) for r in args.run]
    cf5.check_sessions(runs)
    result = analyze(json.loads(text), runs, dispositions)
    out = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        with args.out.open("x") as handle:
            handle.write(out + "\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
