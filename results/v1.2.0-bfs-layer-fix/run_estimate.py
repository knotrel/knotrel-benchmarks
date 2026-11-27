#!/usr/bin/env python3
"""Runs blocks A (K1 workloads, arms prev/fix/v110), B (#181 A probe cells, prev/fix) and C
(feeder under query load, prev/fix) of the bidirectional-BFS per-layer fix impact estimate
(knotrel docs/design/bidirectional-bfs-layer-fix-impact-estimate.md). Raw records only;
analysis is separate.

    run_estimate.py E BLOCK...   (BLOCK: A, B or C)
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

E = Path(sys.argv[1]).resolve()
T = E / "targets"
RAW = E / "raw"
RAW.mkdir(exist_ok=True)
K1 = [("chain-split-rejoin-v1", 10000, 100), ("chain-split-rejoin-v1", 100000, 100),
      ("cycle-alternatives-v1", 10000, 100), ("cycle-alternatives-v1", 100000, 100),
      ("components-join-split-v1", 10000, 100), ("components-join-split-v1", 100000, 100),
      ("hub-alternatives-v1", 10000, 100), ("hub-alternatives-v1", 100000, 100),
      ("sustained-churn-path-v1", 10000, 20), ("sustained-churn-path-v1", 100000, 20),
      ("sustained-churn-blocks-v1", 10000, 20), ("sustained-churn-blocks-v1", 100000, 20),
      ("dense-bridge-churn-v1", 512, 100), ("dense-bridge-churn-v1", 2048, 100),
      ("redundant-bridge-churn-v1", 512, 100), ("redundant-bridge-churn-v1", 2048, 100)]
ROT = [["prev", "fix", "v110"], ["fix", "v110", "prev"], ["v110", "prev", "fix"]]


def log(line):
    with open(E / "run.log", "a") as f:
        f.write(time.strftime("%H:%M:%S ") + line + "\n")


def block_a():
    out = open(RAW / "A.jsonl", "a")
    for block in range(1, 13):
        order = ROT[(block - 1) % 3]
        for wl, n, rounds in K1:
            for arm in order:
                argv = [str(T / f"{arm}-harness/release/knotrel-benchmarks"), "--workload", wl,
                        "--nodes", str(n), "--rounds", str(rounds), "--seed", "42",
                        "--engine", "connectivity-compact-bfs", "--warmup", "1", "--repetitions", "1"]
                done = subprocess.run(argv, capture_output=True, text=True)
                rec = {"block": block, "arm": arm, "workload": wl, "nodes": n, "exit": done.returncode}
                if done.returncode == 0:
                    o = json.loads(done.stdout)
                    rep = o["repetitions"][0]
                    rec.update(engine=o["engine"], fingerprint=o["trace_fingerprint_fnv1a64"],
                               core=o["checkouts_at_run_time"]["core"],
                               workload_wall_ns=rep["workload_wall_ns"],
                               query_true_ns=(rep.get("query_true") or {}).get("total_ns"),
                               query_false_ns=(rep.get("query_false") or {}).get("total_ns"))
                else:
                    rec["stderr"] = done.stderr[-2000:]
                out.write(json.dumps(rec) + "\n")
                out.flush()
                log(f"A block={block} cell={wl}-{n} arm={arm} exit={done.returncode}")


def block_b():
    for block in range(1, 7):
        order = ["prev", "fix"] if block % 2 else ["fix", "prev"]
        for topo in ("sparse", "ring", "hub"):
            for n in (10000, 100000):
                for arm in order:
                    argv = [str(T / f"{arm}-probes/release/core-lifecycle"), "pairs", "--exp", "ops",
                            "--mix", "query", "--engine", "compact-bfs", "--topology", topo,
                            "--nodes", str(n), "--window", "4000", "--seed", "5000001",
                            "--pairs", "2", "--warmup", "1"]
                    path = RAW / "B" / f"{topo}-{n}-{arm}-b{block}.jsonl"
                    path.parent.mkdir(exist_ok=True)
                    with open(path, "w") as f, open(path.with_suffix(".err"), "w") as err:
                        rc = subprocess.run(argv, stdout=f, stderr=err).returncode
                    log(f"B block={block} cell={topo}-{n} arm={arm} exit={rc}")


def block_c():
    url = os.environ["KNOTREL_PG_ADMIN_URL"]
    for rep in range(1, 4):
        order = ["prev", "fix"] if rep % 2 else ["fix", "prev"]
        for arm in order:
            outdir = RAW / "C" / f"{arm}-r{rep}"
            env = {**os.environ, "KNOTREL_BIN": str(T / f"{arm}-server/release/knotrel-server"),
                   "FEEDER_BIN": str(T / "prev-feeder/release/knotrel-pg-feeder"),
                   "KNOTREL_PG_ADMIN_URL": url, "LOAD_OUT": str(outdir), "LOAD_REPS": "1",
                   "LOAD_ENGINE": "compact-bfs", "LOAD_CELLS": "L2 G100k C=0,L2 G100k C=16"}
            outdir.parent.mkdir(exist_ok=True)
            with open(str(outdir) + ".log", "w") as f:
                rc = subprocess.run([str(T / "prev-feeder/release/examples/load")], env=env,
                                    stdout=f, stderr=subprocess.STDOUT).returncode
            log(f"C rep={rep} arm={arm} exit={rc}")


for b in sys.argv[2:]:
    {"A": block_a, "B": block_b, "C": block_c}[b]()
log("done " + " ".join(sys.argv[2:]))
