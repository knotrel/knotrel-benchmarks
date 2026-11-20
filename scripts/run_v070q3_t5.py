#!/usr/bin/env python3
"""Collector of check T5 (compaction pauses) of v0.7.0 qualification 3 (PROTOCOL.md section 5.1).

Runs ``core-lifecycle pauses`` on two arms, one fresh process per run, each gated by
``conformance_gate.gated`` (label ``T5:...``):

- ``B``: the probes built against knotrel ``e75ff6a`` (without T1);
- ``C``: the probes built against the candidate (with T1).

Both are the timing build (no allocator counter) of the same frozen probe source.

**Plan.** Three topologies (``sparse``, ``ring``, ``hub``), the frozen C workload (100,000
nodes, fresh-ID churn of 5% per cycle, seed 5000001) for 600 cycles. Per topology: 2 warmup
pairs, then 12 analyzed pairs. A pair is two consecutive runs, one per arm. Warmup pair -2
runs C first, warmup pair -1 runs B first. The first arm of the 12 analyzed pairs comes from
``random.Random(f"{order_seed}:{topology}")`` shuffling six ``C`` and six ``B``. Runs are
interleaved by round: round r runs pair r of every topology, the topologies in an order
shuffled per round with ``random.Random(f"{order_seed}:round:{r}")``.

Writes ``plan.json`` (every run in order) and ``provenance.json`` before the first run,
then per run ``raw/<topology>-<pair>-<arm>.jsonl`` and ``.stderr`` and one line of
``run-log.jsonl``. Stops at the first failing child; never retries or skips a run.

    run_v070q3_t5.py --out DIR --base BIN --cand BIN --order-seed N [--dry-run]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from cli_paths import confined, confined_executable  # noqa: E402

TOPOLOGIES = ("sparse", "ring", "hub")
NODES = 100_000
CYCLES = 600
CHURN_PERCENT = 5
SEED = 5_000_001
WARMUP = 2
PAIRS = 12
ENGINE = "compact-bfs"


def child_args(topology: str) -> List[str]:
    return ["pauses", "--engine", ENGINE, "--topology", topology, "--nodes", str(NODES),
            "--cycles", str(CYCLES), "--churn-percent", str(CHURN_PERCENT), "--seed", str(SEED)]


def first_arms(order_seed: int, topology: str) -> List[str]:
    """First arm of every pair of ``topology``: two warmup pairs, then 12 balanced 6/6."""
    analyzed = ["C"] * (PAIRS // 2) + ["B"] * (PAIRS // 2)
    random.Random(f"{order_seed}:{topology}").shuffle(analyzed)
    return ["C", "B"] + analyzed


def plan(order_seed: int) -> List[Dict[str, Any]]:
    """Every run in order: topology, pair (-2, -1 warmup; 0-11 analyzed), arm, position in pair."""
    firsts = {t: first_arms(order_seed, t) for t in TOPOLOGIES}
    runs: List[Dict[str, Any]] = []
    for r in range(WARMUP + PAIRS):
        topologies = list(TOPOLOGIES)
        random.Random(f"{order_seed}:round:{r}").shuffle(topologies)
        for topology in topologies:
            first = firsts[topology][r]
            for slot, arm in enumerate((first, "B" if first == "C" else "C")):
                runs.append({"topology": topology, "pair": r - WARMUP, "arm": arm, "slot": slot,
                             "id": f"{topology}-{r - WARMUP}-{arm}"})
    return runs


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def host_state() -> Dict[str, Any]:
    try:
        power = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError) as error:
        power = f"unavailable: {error}"
    return {"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "power": power,
            "load": os.getloadavg()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--base", type=Path, required=True, help="core-lifecycle built against e75ff6a (arm B)")
    parser.add_argument("--cand", type=Path, required=True, help="core-lifecycle built against the candidate (arm C)")
    parser.add_argument("--order-seed", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    args.out = confined(args.out, "--out")
    binaries = {"B": confined_executable(args.base, "--base"), "C": confined_executable(args.cand, "--cand")}
    if os.path.realpath(binaries["B"]) == os.path.realpath(binaries["C"]):
        print("--base and --cand are the same file", file=sys.stderr)
        return 2
    if args.out.exists():
        print(f"refusing to reuse existing output directory {args.out}", file=sys.stderr)
        return 2
    runs = plan(args.order_seed)
    provenance = {"order_seed": args.order_seed, "runs": len(runs), "nodes": NODES, "cycles": CYCLES,
                  "churn_percent": CHURN_PERCENT, "seed": SEED, "engine": ENGINE,
                  "warmup": WARMUP, "pairs": PAIRS, "topologies": list(TOPOLOGIES),
                  "binaries": {arm: {"path": str(p.resolve()), "sha256": sha256(p)} for arm, p in binaries.items()}}
    if args.dry_run:
        print(json.dumps({"runs": len(runs), "provenance": provenance}, indent=1))
        return 0
    if os.environ.get("KNOTREL_INTERFERENCE_DIR"):
        return collect_units(args.out, binaries, runs, provenance)
    import conformance_gate  # only a real run is gated (a dry run must not touch the gate)
    (args.out / "raw").mkdir(parents=True)
    (args.out / "plan.json").write_text(json.dumps(runs, indent=1))
    (args.out / "provenance.json").write_text(json.dumps(provenance, indent=1))
    log = (args.out / "run-log.jsonl").open("a")
    for position, run in enumerate(runs):
        argv = [str(binaries[run["arm"]])] + child_args(run["topology"])
        before = host_state()
        start = time.monotonic()
        child = conformance_gate.gated(
            f"T5:{run['id']} {' '.join(argv)}"[:200],
            lambda: subprocess.run(argv, capture_output=True, text=True, env={"PATH": os.environ["PATH"]}))
        elapsed = time.monotonic() - start
        (args.out / "raw" / f"{run['id']}.jsonl").write_text(child.stdout)
        (args.out / "raw" / f"{run['id']}.stderr").write_text(child.stderr)
        record = {"position": position, **run, "argv": argv, "exit": child.returncode,
                  "seconds": round(elapsed, 3), "host_before": before}
        log.write(json.dumps(record) + "\n")
        log.flush()
        print(f"[{position + 1}/{len(runs)}] {run['id']} exit={child.returncode} {elapsed:.1f}s", flush=True)
        if child.returncode != 0:
            print(f"stopping: {run['id']} failed: {child.stderr.strip()[:500]}", file=sys.stderr)
            return 1
    return 0


def collect_units(out: Path, binaries: Dict[str, Path], runs: List[Dict[str, Any]],
                  provenance: Dict[str, Any]) -> int:
    """Revision 3: each **pair** (both runs) is one unit of the interference gate. An invalid
    pair is preserved in ``raw/invalidated/`` and ``invalidated.jsonl`` and repeated whole; the
    run log holds only the valid runs, in plan order."""
    import interference_gate as ig
    g = ig.gate()
    (out / "raw" / "invalidated").mkdir(parents=True)
    (out / "plan.json").write_text(json.dumps(runs, indent=1))
    (out / "provenance.json").write_text(json.dumps(provenance, indent=1))
    log = (out / "run-log.jsonl").open("a")
    position = 0
    for first in range(0, len(runs), 2):
        pair = runs[first:first + 2]
        done: List[Dict[str, Any]] = []

        def both() -> None:
            done.clear()
            for run in pair:
                argv = [str(binaries[run["arm"]])] + child_args(run["topology"])
                before = host_state()
                start = time.monotonic()
                child = g.child(f"T5:{run['id']}", lambda: subprocess.run(
                    argv, capture_output=True, text=True, env={"PATH": os.environ["PATH"]}))
                done.append({"run": run, "argv": argv, "child": child, "before": before,
                             "seconds": round(time.monotonic() - start, 3)})
                if child.returncode != 0:
                    (out / "raw" / f"{run['id']}.jsonl").write_text(child.stdout)
                    (out / "raw" / f"{run['id']}.stderr").write_text(child.stderr)
                    raise SystemExit(f"stopping: {run['id']} failed: {child.stderr.strip()[:500]}")

        def preserve(attempt: int, reasons: List[str]) -> None:
            for d in done:
                name = f"{d['run']['id']}.attempt{attempt}"
                (out / "raw" / "invalidated" / f"{name}.jsonl").write_text(d["child"].stdout)
                (out / "raw" / "invalidated" / f"{name}.stderr").write_text(d["child"].stderr)
            with open(out / "invalidated.jsonl", "a") as handle:
                handle.write(json.dumps({"pair": [r["id"] for r in pair], "attempt": attempt,
                                         "reasons": reasons}) + "\n")

        g.run_unit(f"T5:{pair[0]['topology']}-{pair[0]['pair']}", both, preserve)
        for d in done:
            run = d["run"]
            (out / "raw" / f"{run['id']}.jsonl").write_text(d["child"].stdout)
            (out / "raw" / f"{run['id']}.stderr").write_text(d["child"].stderr)
            log.write(json.dumps({"position": position, **run, "argv": d["argv"], "exit": d["child"].returncode,
                                  "seconds": d["seconds"], "host_before": d["before"]}) + "\n")
            log.flush()
            position += 1
            print(f"[{position}/{len(runs)}] {run['id']} exit={d['child'].returncode} {d['seconds']:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
