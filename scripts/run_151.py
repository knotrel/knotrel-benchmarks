#!/usr/bin/env python3
"""Runner of the knotrel#151 comparison (compact internal node indices, option B64).

    run_151.py smoke --matrix M --tools T --out DIR [--cells ID,..] [--with-q]
    run_151.py pilot --matrix M --tools T --out DIR
    run_151.py propose-windows --matrix M --pilot DIR --out W.json [--estimate E.json]
    run_151.py freeze --matrix M --tools T --out FREEZE.json
    run_151.py campaign --matrix M --tools T --out DIR [--session 2 --resume-from DIR1]

knotrel ``docs/design/compact-node-index.md``, sections 6.5 and 6.8. The matrix comes
from ``compact_index_matrix.py``, the tool map from ``build_151_probes.sh``. Arm ``cf``
is the candidate (B), arm ``ref`` the base (CUR).

- ``smoke``: tier-1 smoke, not a measurement. Every paired and deterministic cell runs
  each arm once (deterministic cells twice), with every gate of the campaign (exit
  status, parsable output, ``errors == 0``, both arms' ``gate`` objects equal); for
  deterministic cells it records whether metrics and gate repeat. Unlike the campaign it
  continues after a failure and reports every cell (``DIR/smoke.jsonl``,
  ``DIR/summary.json``); exit 1 if any cell failed. The delegated Q check runs only with
  ``--with-q`` (in its ``--quick`` form, recorded as such).
- ``pilot``: ``run_cf5.py --preparatory --pairs 2 --warmup 0 --no-smoke`` (every cell,
  never used for decisions; the analyzer refuses it).
- ``propose-windows``: from a pilot, the window factor of every windowed cell: the
  smallest power of two (at most 64) bringing the faster arm's median pilot window to
  2 ms (``derive_lifecycle_window_multipliers.factor``), capped so that ``k`` stays
  within the cell's target pool; and (``--estimate``) each cell's estimated campaign
  duration (24 + 2 pairs; deterministic cells once per arm). Then regenerate the matrix
  with ``compact_index_matrix.py --windows W.json`` and freeze it.
- ``freeze``: writes the freeze record section 6.5 requires before the first observation
  (matrix SHA-256, base, candidate and knotrel-benchmarks SHAs, executable and lockfile
  hashes, host description, the derived order seed) to a new file, and names it as
  ``_freeze`` in the tool map. Refuses a scaled matrix, unset windows, dirty checkouts or
  an overlay build. Commit the record (proposed: ``results/v1.2.0-151/FREEZE.json``).
- ``campaign``: the frozen campaign through ``run_cf5.py`` (24 pairs, 2 warmup, 12/12
  balanced order from a seed derived from the matrix SHA-256 and the candidate SHA; the
  tool map must name ``_freeze`` with both). Refuses a scaled matrix or unset windows.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_cf5  # noqa: E402
from cli_paths import confined, confined_directory  # noqa: E402
from derive_lifecycle_window_multipliers import CAP, factor  # noqa: E402

PAIRS, WARMUP = run_cf5.PAIRS, run_cf5.WARMUP


def gate_of(cell: Dict[str, Any], record: Dict[str, Any]) -> Any:
    return record["object"].get(cell.get("check", {}).get("same_trace", "gate"))


def smoke_cell(cell: Dict[str, Any], tools: Dict[str, Any], scratch: Path) -> Dict[str, Any]:
    entry: Dict[str, Any] = {"cell": cell["id"], "kind": cell["kind"], "ok": True}
    try:
        first = {a: run_cf5.run_arm_retrying(cell, a, tools, scratch) for a in ("cf", "ref")}
        entry["wall_s"] = {a: round(first[a]["wall_s"], 3) for a in first}
        entry["metrics"] = {a: first[a]["metrics"] for a in first}
        run_cf5.same_trace(cell, first["cf"], first["ref"])
        entry["gate_equal"] = True
        if cell["kind"] == "deterministic":
            repeats = {}
            for a in ("cf", "ref"):
                again = run_cf5.run_arm_retrying(cell, a, tools, scratch)
                repeats[a] = {"metrics": again["metrics"] == first[a]["metrics"],
                              "gate": gate_of(cell, again) == gate_of(cell, first[a])}
                if not repeats[a]["metrics"]:
                    entry.setdefault("repeat_metrics", {})[a] = again["metrics"]
            entry["repeats"] = repeats
            entry["deterministic"] = all(r["metrics"] and r["gate"] for r in repeats.values())
    except run_cf5.GateFailure as failure:
        entry.update({"ok": False, "failure": str(failure)})
        record = getattr(failure, "record", None)
        if isinstance(record, dict):
            entry["stderr_tail"] = record.get("stderr_tail", "")[-800:]
    return entry


def smoke(args: argparse.Namespace) -> int:
    matrix = json.loads(args.matrix.read_text())
    tools = json.loads(args.tools.read_text())
    cells = matrix["cells"]
    if args.cells:
        wanted = set(args.cells.split(","))
        cells = [c for c in cells if c["id"] in wanted or c["group"] in wanted]
    args.out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="kr151-smoke-"))
    start = time.monotonic()
    results = []
    with (args.out / "smoke.jsonl").open("w") as log:
        for cell in cells:
            if cell["kind"] == "delegated":
                if not args.with_q:
                    entry = {"cell": cell["id"], "kind": "delegated", "ok": True,
                             "skipped": "run with --with-q"}
                else:
                    spec = json.loads(json.dumps(tools["_delegated"][cell["id"]]))
                    spec["argv"] = spec["argv"] + ["--quick"]
                    t0 = time.monotonic()
                    try:
                        state = run_cf5.run_delegated(cell, {"_delegated": {cell["id"]: spec}},
                                                      args.out)
                        entry = {"cell": cell["id"], "kind": "delegated", "ok": True,
                                 "state": state["state"], "quick": True}
                    except run_cf5.GateFailure as failure:
                        entry = {"cell": cell["id"], "kind": "delegated", "ok": False,
                                 "failure": str(failure)}
                    entry["wall_s"] = round(time.monotonic() - t0, 3)
            else:
                entry = smoke_cell(cell, tools, scratch)
            results.append(entry)
            log.write(json.dumps(entry) + "\n")
            log.flush()
            print(json.dumps({k: entry.get(k) for k in ("cell", "ok", "deterministic",
                                                         "wall_s", "failure")}), flush=True)
    summary = {"schema": "kr151-smoke-1", "not_a_measurement": True,
               "matrix_scale": matrix.get("scale"), "cells": len(results),
               "failed": [r["cell"] for r in results if not r["ok"]],
               "not_repeating": [r["cell"] for r in results if r.get("deterministic") is False],
               "wall_s": round(time.monotonic() - start, 1)}
    (args.out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary))
    return 0 if not summary["failed"] else 1


def pilot(args: argparse.Namespace) -> int:
    return run_cf5.main(["--matrix", str(args.matrix), "--tools", str(args.tools),
                         "--out", str(args.out), "--preparatory", "--pairs", "2",
                         "--warmup", "0", "--no-smoke"])


def pool_size(cell: Dict[str, Any]) -> Optional[int]:
    """Targets available to a windowed cell (``k`` may not exceed it)."""
    p = cell["params"]
    if cell["group"] in ("R4", "P1"):
        return None
    graph = p["graph"]
    if p.get("pool") == "spokes":
        return int(cell["arms"]["cf"]["args"][cell["arms"]["cf"]["args"].index("--degree") + 1])
    args = cell["arms"]["cf"]["args"]
    nodes = int(args[args.index("--nodes") + 1])
    if p.get("pool") == "nodes":
        return nodes
    if graph.startswith("sparse"):
        return int(nodes * 1.9)  # deduplicated 2n draws: about 1.99 n edges
    return None


def propose(matrix: Dict[str, Any], raw: List[Dict[str, Any]]) -> Dict[str, Any]:
    factors, notes, estimate = {}, {}, {}
    by_cell: Dict[str, List[Dict[str, Any]]] = {}
    for line in raw:
        if "cell" in line and "failed_observation" not in line:
            by_cell.setdefault(line["cell"], []).append(line)
    for cell in matrix["cells"]:
        lines = by_cell.get(cell["id"], [])
        if cell["kind"] == "paired":
            pairs = [l for l in lines if "cf" in l]
            if "window" in cell:
                if not pairs:
                    raise SystemExit(f"{cell['id']}: no pilot pairs")
                fastest = min(statistics.median(p[a]["object"]["observation_ns"] for p in pairs)
                              for a in ("cf", "ref"))
                f = factor(fastest)
                pool = pool_size(cell)
                if pool:
                    while f > 1 and cell["window"]["base"] * f > pool:
                        f //= 2
                factors[cell["id"]] = f
                notes[cell["id"]] = {"fastest_median_window_ns": fastest, "factor": f,
                                     "at_cap": f == CAP, "pool": pool}
            if pairs:
                walls = [p[a]["wall_s"] for p in pairs for a in ("cf", "ref")]
                per_obs = statistics.mean(walls)
                if "window" in cell:
                    reps = int(cell["params"].get("reps", 1))
                    window_s = notes[cell["id"]]["fastest_median_window_ns"] / 1e9
                    per_obs += (factors[cell["id"]] - 1) * reps * window_s * 2
                estimate[cell["id"]] = round(per_obs * 2 * (PAIRS + WARMUP), 1)
        elif cell["kind"] == "deterministic" and lines:
            estimate[cell["id"]] = round(sum(l["wall_s"] for l in lines), 1)
    return {"factors": factors, "notes": notes, "estimate_s": estimate,
            "estimate_total_h": round(sum(estimate.values()) / 3600, 2)}


def propose_windows(args: argparse.Namespace) -> int:
    args.matrix = confined(args.matrix, "--matrix")
    args.pilot = confined_directory(args.pilot, "--pilot")
    args.out = confined(args.out, "--out")
    if args.estimate:
        args.estimate = confined(args.estimate, "--estimate")
    matrix = json.loads(args.matrix.read_text())
    status = json.loads((args.pilot / "status.json").read_text())
    if not status.get("preparatory"):
        raise SystemExit("propose-windows reads a pilot (preparatory) run only")
    raw = [json.loads(l) for l in (args.pilot / "raw.jsonl").read_text().splitlines() if l]
    result = propose(matrix, raw)
    args.out.write_text(json.dumps(result["factors"], indent=1, sort_keys=True) + "\n")
    if args.estimate:
        args.estimate.write_text(json.dumps(result, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"windowed": len(result["factors"]),
                      "scaled": sum(f > 1 for f in result["factors"].values()),
                      "at_cap": sum(f == CAP for f in result["factors"].values()),
                      "estimate_total_h": result["estimate_total_h"]}))
    return 0


def freeze(args: argparse.Namespace) -> int:
    text = args.matrix.read_bytes()
    matrix = json.loads(text)
    tools = json.loads(args.tools.read_text())
    problems = []
    if matrix.get("scale", 1) != 1 or matrix.get("windows") != "set":
        problems.append("the matrix needs scale 1 and frozen windows")
    if tools.get("_build", {}).get("overlay"):
        problems.append("the tools were built with --overlay")
    prov = run_cf5.provenance(tools)
    problems += [f"checkout {name} is dirty" for name, c in prov["checkouts"].items()
                 if c["dirty"]]
    candidate = prov["checkouts"].get("candidate", {}).get("sha")
    if not candidate:
        problems.append("no candidate checkout SHA")
    if args.out.exists():
        problems.append(f"{args.out} exists")
    if problems:
        raise SystemExit("NOT FROZEN: " + "; ".join(problems))
    matrix_sha = run_cf5.sha256_bytes(text)
    record = {"schema": "kr151-freeze-1", "protocol": matrix.get("protocol"),
              "matrix_sha256": matrix_sha, "candidate": candidate,
              "base": prov["checkouts"].get("base", {}).get("sha"),
              "benchmarks": prov["checkouts"].get("benchmarks", {}).get("sha"),
              "order_seed": run_cf5.derived_seed(matrix_sha, candidate),
              "provenance": prov, "build": tools.get("_build"),
              "host": run_cf5.host_description(), "time": time.time()}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x") as handle:
        handle.write(json.dumps(record, indent=1, sort_keys=True) + "\n")
    tools["_freeze"] = str(args.out.resolve())
    args.tools.write_text(json.dumps(tools, indent=1) + "\n")
    print(json.dumps({"freeze": str(args.out), "order_seed": record["order_seed"]}))
    return 0


def campaign(args: argparse.Namespace) -> int:
    matrix = json.loads(args.matrix.read_text())
    if matrix.get("scale", 1) != 1 or matrix.get("windows") != "set":
        raise SystemExit("NOT STARTED: the campaign needs scale 1 and frozen windows")
    argv = ["--matrix", str(args.matrix), "--tools", str(args.tools), "--out", str(args.out)]
    if args.session == 2:
        argv += ["--session", "2", "--resume-from", str(args.resume_from)]
    return run_cf5.main(argv)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("smoke", "pilot", "freeze", "campaign"):
        p = sub.add_parser(name)
        p.add_argument("--matrix", type=Path, required=True)
        p.add_argument("--tools", type=Path, required=True)
        p.add_argument("--out", type=Path, required=True)
        if name == "smoke":
            p.add_argument("--cells")
            p.add_argument("--with-q", action="store_true")
        if name == "campaign":
            p.add_argument("--session", type=int, choices=(1, 2), default=1)
            p.add_argument("--resume-from", type=Path)
    p = sub.add_parser("propose-windows")
    p.add_argument("--matrix", type=Path, required=True)
    p.add_argument("--pilot", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--estimate", type=Path)
    args = parser.parse_args(argv)
    args.matrix = confined(args.matrix, "--matrix")
    if args.command == "propose-windows":
        args.pilot = confined_directory(args.pilot, "--pilot")
        args.out = confined(args.out, "--out")
        if args.estimate:
            args.estimate = confined(args.estimate, "--estimate")
        return propose_windows(args)
    args.tools = confined(args.tools, "--tools")
    args.out = confined(args.out, "--out")
    return {"smoke": smoke, "pilot": pilot, "freeze": freeze,
            "campaign": campaign}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
