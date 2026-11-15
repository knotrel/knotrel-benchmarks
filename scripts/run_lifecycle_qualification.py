#!/usr/bin/env python3
"""Collector for the Knotrel v0.5.0 lifecycle qualification (experiments B and C).

Experiment A (existing behavior against v0.4.0) uses the v0.4.0 B/C pipeline
(``prepare_bc_qualification.py``, ``run_p0_aa.py``, ``analyze_bc_qualification.py``)
unchanged and is not run by this script.

The matrix is generated deterministically by :func:`matrix` and archived in
``plan/matrix.json`` before the first measurement. Cells run one at a time in an
order shuffled with ``--order-seed``. Each child's argv, timestamps, exit status,
stdout (raw JSON lines) and stderr are written under ``raw/``. The collector stops
at the first failing child; it never retries or skips a cell.

Usage (from the knotrel-benchmarks root, with ``tools/lifecycle-probes`` built in
both the default and ``count-alloc`` variants)::

    run_lifecycle_qualification.py --out DIR --profile pilot|final \\
        --core BIN --core-count BIN --http BIN --order-seed N [--dry-run]

``--profile pilot`` runs every cell with two pairs and no warmup (B) and three
cycles (C) to estimate durations; it is never used for decisions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

ENGINES = ("compact-bfs", "ett", "hdt")
SEED = 5_000_001


def apply_multipliers(cells: List[Dict[str, Any]], multipliers: Dict[str, int]) -> None:
    """Scales B1-B3 ``--window`` and B4 ``--requests`` by the pilot-derived factor.

    Factors come from the pilot's reference-arm medians only (target window >= 2 ms,
    powers of two, at most 16); they are archived with the plan. Single-request import
    scenarios cannot be scaled and keep their factor implicit at 1.
    """
    for cell in cells:
        factor = multipliers.get(cell["id"], 1)
        if factor == 1:
            continue
        flag = "--requests" if cell["experiment"] == "B4" else "--window"
        if cell["experiment"] == "B4" and "-import" in cell["id"]:
            continue
        index = cell["args"].index(flag) + 1
        cell["args"][index] = str(int(cell["args"][index]) * factor)
        cell["scale"] = factor


def matrix(profile: str) -> List[Dict[str, Any]]:
    """Every cell of experiments B and C. ``profile`` only shrinks repetition counts."""
    pairs, warmup = (2, 0) if profile == "pilot" else (12, 2)
    cycles = 3 if profile == "pilot" else 30
    cells: List[Dict[str, Any]] = []

    def pair_args(**kv: Any) -> List[str]:
        out: List[str] = []
        for key, value in kv.items():
            out += [f"--{key.replace('_', '-')}", str(value)]
        return out + ["--pairs", str(pairs), "--warmup", str(warmup), "--seed", str(SEED)]

    for engine in ENGINES:
        for topology in ("sparse", "ring", "hub"):
            for nodes in (1_000, 10_000, 100_000):
                for mix in ("query", "mutation"):
                    cells.append({
                        "id": f"B1-ops-{engine}-{topology}-{nodes}-{mix}", "experiment": "B1",
                        "tolerance": 0.25, "binary": "core",
                        "args": ["pairs"] + pair_args(exp="ops", engine=engine, topology=topology,
                                                      nodes=nodes, mix=mix, window=4000)})
        for topology in ("sparse", "hub"):
            for nodes in (10_000, 100_000):
                cells.append({
                    "id": f"B2-optin-{engine}-{topology}-{nodes}", "experiment": "B2",
                    "tolerance": 0.50, "binary": "core",
                    "args": ["pairs"] + pair_args(exp="optin", engine=engine, topology=topology,
                                                  nodes=nodes, mix="legacy", window=4000)})
        for degree, window in ((16, 3000), (256, 600), (4096, 300), (16384, 60)):
            cells.append({
                "id": f"B3-degree-{engine}-{degree}", "experiment": "B3", "tolerance": 0.25,
                "binary": "core",
                "args": ["pairs"] + pair_args(exp="degree", engine=engine, degree=degree,
                                              window=window, topology="sparse", nodes=0,
                                              mix="mutation")})
        for scenario, tolerance, requests in (("optin-mutation", 0.50, 40), ("optin-query", 0.25, 4),
                                              ("ops", 0.25, 40), ("events", 0.25, 40),
                                              ("import", 1.00, 1), ("import-optin", 1.00, 1)):
            cells.append({
                "id": f"B4-http-{scenario}-{engine}-10000", "experiment": "B4",
                "tolerance": tolerance, "binary": "http",
                "args": pair_args(scenario=scenario, engine=engine, nodes=10_000, requests=requests)})
    for scenario in ("import", "import-optin"):
        cells.append({
            "id": f"B4-http-{scenario}-compact-bfs-100000", "experiment": "B4", "tolerance": 1.00,
            "binary": "http",
            "args": pair_args(scenario=scenario, engine="compact-bfs", nodes=100_000, requests=1)})
    for engine in ENGINES:
        for topology in ("sparse", "hub"):
            for arm in ("plain", "lifecycle", "reference"):
                cells.append({
                    "id": f"B5-memory-{arm}-{engine}-{topology}-100000", "experiment": "B5",
                    "binary": "core-count",
                    "args": ["resources", "--arm", arm, "--engine", engine, "--topology", topology,
                             "--nodes", "100000", "--cycles", "0", "--churn-percent", "0",
                             "--reuse", "none", "--seed", str(SEED)]})
        for topology in ("sparse", "ring", "hub"):
            for reuse in ("fresh", "same", "toggle"):
                for variant, binary in (("heap", "core-count"), ("rss", "core")):
                    for arm in (("lifecycle", "reference") if reuse == "fresh" else ("lifecycle",)):
                        cells.append({
                            "id": f"C-{variant}-{arm}-{engine}-{topology}-{reuse}-100000",
                            "experiment": "C", "binary": binary,
                            "args": ["resources", "--arm", arm, "--engine", engine,
                                     "--topology", topology, "--nodes", "100000",
                                     "--cycles", str(cycles), "--churn-percent", "5",
                                     "--reuse", reuse, "--seed", str(SEED)]})
    return cells


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(directory: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(directory), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def host_state() -> Dict[str, Any]:
    def run(cmd: List[str]) -> str:
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=10).stdout.strip()
        except (OSError, subprocess.SubprocessError) as error:
            return f"unavailable: {error}"
    return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "power": run(["pmset", "-g", "batt"]),
            "load": os.getloadavg(), "therm": run(["pmset", "-g", "therm"])}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--profile", choices=("pilot", "final"), required=True)
    parser.add_argument("--core", type=Path, required=True)
    parser.add_argument("--core-count", type=Path, required=True)
    parser.add_argument("--http", type=Path, required=True)
    parser.add_argument("--order-seed", type=int, required=True)
    parser.add_argument("--knotrel", type=Path, required=True, help="candidate knotrel checkout")
    parser.add_argument("--only", default="", help="comma-separated experiment filter (B1,B2,...,C)")
    parser.add_argument("--window-multipliers", type=Path,
                        help="pilot-derived JSON {cell id: factor}; archived in plan/")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        print(f"refusing to reuse existing output directory {args.out}", file=sys.stderr)
        return 2
    binaries = {"core": args.core, "core-count": args.core_count, "http": args.http}
    cells = matrix(args.profile)
    if args.window_multipliers:
        apply_multipliers(cells, json.loads(args.window_multipliers.read_text()))
    if args.only:
        wanted = set(args.only.split(","))
        cells = [cell for cell in cells if cell["experiment"] in wanted]
    order = list(range(len(cells)))
    random.Random(args.order_seed).shuffle(order)
    provenance = {
        "profile": args.profile, "order_seed": args.order_seed, "seed": SEED,
        "knotrel": {"path": str(args.knotrel.resolve()), "head": git(args.knotrel, "rev-parse", "HEAD"),
                    "dirty": git(args.knotrel, "status", "--porcelain")},
        "benchmarks": {"head": git(Path.cwd(), "rev-parse", "HEAD"),
                       "dirty": git(Path.cwd(), "status", "--porcelain")},
        "binaries": {name: {"path": str(path.resolve()), "sha256": sha256(path)} for name, path in binaries.items()},
        "rustc": subprocess.run(["rustc", "+1.100.0", "-Vv"], capture_output=True, text=True).stdout,
        "platform": platform.platform(), "machine": platform.machine(),
        "window_multipliers": (str(args.window_multipliers.resolve()) if args.window_multipliers else None),
        "window_multipliers_sha256": (sha256(args.window_multipliers) if args.window_multipliers else None),
    }
    if args.dry_run:
        print(json.dumps({"cells": len(cells), "provenance": provenance}, indent=1))
        return 0
    (args.out / "plan").mkdir(parents=True)
    (args.out / "raw").mkdir()
    (args.out / "plan" / "matrix.json").write_text(json.dumps(cells, indent=1))
    (args.out / "plan" / "order.json").write_text(json.dumps([cells[i]["id"] for i in order], indent=1))
    (args.out / "provenance.json").write_text(json.dumps(provenance, indent=1))
    log = (args.out / "run-log.jsonl").open("a")
    for position, index in enumerate(order):
        cell = cells[index]
        argv = [str(binaries[cell["binary"]])] + cell["args"]
        before = host_state()
        start = time.monotonic()
        child = subprocess.run(argv, capture_output=True, text=True, env={"PATH": os.environ["PATH"]})
        elapsed = time.monotonic() - start
        (args.out / "raw" / f"{cell['id']}.jsonl").write_text(child.stdout)
        (args.out / "raw" / f"{cell['id']}.stderr").write_text(child.stderr)
        record = {"position": position, "id": cell["id"], "argv": argv, "exit": child.returncode,
                  "seconds": round(elapsed, 3), "host_before": before}
        log.write(json.dumps(record) + "\n")
        log.flush()
        print(f"[{position + 1}/{len(cells)}] {cell['id']} exit={child.returncode} {elapsed:.1f}s", flush=True)
        if child.returncode != 0:
            print(f"stopping: {cell['id']} failed: {child.stderr.strip()[:500]}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
