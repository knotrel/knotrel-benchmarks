#!/usr/bin/env python3
"""Runs the measured blocks of the adaptive-BFS impact estimate (knotrel docs/design/
adaptive-bfs-impact-estimate.md, section 5): K, V, L, then the stop check, then F (unless the
core blocks already decide REJECT), then D is run separately. The 60-minute cap is enforced
here: no block starts if the elapsed host time plus its budget would exceed the cap... the
cap is checked before every observation; when it is reached, the run stops and is INCOMPLETE.

    run_adaptive.py E RUN_NAME core   # K, V, L and the stop check (Docker stopped)
    run_adaptive.py E RUN_NAME F      # F, only if the stop check left the candidate adoptable;
                                      # needs KNOTREL_PG_ADMIN_URL; the cap counts both parts
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

E = Path(sys.argv[1]).resolve()
RUN = E / sys.argv[2]
MODE = sys.argv[3]
B = E / "src/cand/knotrel-benchmarks"
T = E / "targets"
CAP_S = 60 * 60
if MODE == "core":
    RUN.mkdir()
    (RUN / "raw").mkdir()
    START = time.monotonic()
else:
    PRIOR = json.loads((RUN / "status.json").read_text())
    if PRIOR["outcome"] != "core adoptable; F required":
        raise SystemExit(f"F not allowed: {PRIOR['outcome']}")
    START = time.monotonic() - PRIOR["elapsed_s"]
HERE = Path(__file__).resolve().parent
K1 = [(c["id"], c["arms"]["cf"]["args"]) for c in json.loads(
    (HERE.parent / "v1.2.0-qualification/v120q-matrix.json").read_text())["cells"] if c["block"] == "K1"]
ROT = [["v110", "bfs196", "cand"], ["bfs196", "cand", "v110"], ["cand", "v110", "bfs196"]]


class Capped(Exception):
    pass


def log(line):
    with open(RUN / "run.log", "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} t={time.monotonic() - START:7.1f}s {line}\n")


def check_cap():
    if time.monotonic() - START > CAP_S:
        raise Capped()


def host(name):
    out = subprocess.run("date -u +%FT%TZ; vm_stat | grep -E 'Swap(ins|outs)'; pmset -g batt | head -1; uptime",
                         shell=True, capture_output=True, text=True).stdout
    (RUN / f"host-{name}.txt").write_text(out)


def block_k():
    out = open(RUN / "raw/K.jsonl", "a")
    for pair in range(-2, 24):          # -2, -1: warm-up pairs
        order = ROT[(pair + 2) % 3]
        for cell_id, args in K1:
            for arm in order:
                check_cap()
                argv = [str(T / f"{arm}-harness/release/knotrel-benchmarks")] + list(args)
                done = subprocess.run(argv, capture_output=True, text=True)
                rec = {"cell": cell_id, "pair": pair, "arm": arm, "exit": done.returncode}
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
        log(f"K pair {pair} done")


def block_v():
    env = {**os.environ, "LIFECYCLE_QUALIFICATION_ROOTS": str(E)}
    for i in (1, 2):
        check_cap()
        rc = subprocess.run([sys.executable, "scripts/run_p0_aa.py", "--manifest", str(E / f"A/plan{i}/manifest.json"),
                             "--schedule", str(E / f"A/plan{i}/schedule.json"), "--execute", str(RUN / f"raw/V/block{i}")],
                            cwd=B, env=env, stdout=open(RUN / f"V-block{i}.log", "w"), stderr=subprocess.STDOUT).returncode
        log(f"V block{i} exit={rc}")
        if rc != 0:
            raise SystemExit(f"V block{i} failed: exit {rc}")


def block_l():
    (RUN / "raw/L").mkdir()
    for block in range(1, 7):
        order = ROT[(block - 1) % 3]
        for topo in ("sparse", "ring", "hub"):
            for n in (10000, 100000):
                for arm in order:
                    check_cap()
                    path = RUN / "raw/L" / f"{topo}-{n}-{arm}-b{block}.jsonl"
                    argv = [str(T / f"{arm}-probes/release/core-lifecycle"), "pairs", "--exp", "ops", "--mix", "query",
                            "--engine", "compact-bfs", "--topology", topo, "--nodes", str(n), "--window", "4000",
                            "--seed", "5000001", "--pairs", "2", "--warmup", "1"]
                    with open(path, "w") as f, open(path.with_suffix(".err"), "w") as err:
                        rc = subprocess.run(argv, stdout=f, stderr=err).returncode
                    log(f"L block={block} {topo}-{n} {arm} exit={rc}")


def stop_check():
    done = subprocess.run([sys.executable, str(HERE / "analyze_adaptive.py"), str(RUN), "--core-only"],
                          capture_output=True, text=True, env={**os.environ, "LIFECYCLE_QUALIFICATION_ROOTS": str(E)})
    (RUN / "analysis-core.json").write_text(done.stdout)
    if done.returncode != 0:
        (RUN / "analysis-core.err").write_text(done.stderr)
        raise SystemExit("core analysis failed")
    return json.loads(done.stdout)["core_decides_reject"]


def block_f():
    url = os.environ["KNOTREL_PG_ADMIN_URL"]
    (RUN / "raw/F").mkdir()
    for rep in range(1, 4):
        for arm in ROT[(rep - 1) % 3]:
            check_cap()
            outdir = RUN / "raw/F" / f"{arm}-r{rep}"
            env = {**os.environ, "KNOTREL_BIN": str(T / f"{arm}-server/release/knotrel-server"),
                   "FEEDER_BIN": str(T / "feeder/release/knotrel-pg-feeder"), "KNOTREL_PG_ADMIN_URL": url,
                   "LOAD_OUT": str(outdir), "LOAD_REPS": "1", "LOAD_ENGINE": "compact-bfs",
                   "LOAD_CELLS": "L2 G100k C=0,L2 G100k C=16,L2 G100k C=64"}
            with open(str(outdir) + ".log", "w") as f:
                rc = subprocess.run([str(T / "feeder/release/examples/load")], env=env, stdout=f,
                                    stderr=subprocess.STDOUT).returncode
            log(f"F rep={rep} {arm} exit={rc}")


def main():
    status = {"outcome": None}
    try:
        if MODE == "core":
            host("before")
            block_k(); block_v(); block_l()
            host("after-core")
            status["outcome"] = ("REJECT (core); F skipped by protocol" if stop_check()
                                 else "core adoptable; F required")
        else:
            block_f()
            host("after-F")
            status["outcome"] = "F done"
        log(status["outcome"])
    except Capped:
        status["outcome"] = "INCOMPLETE (60-minute cap reached)"
        log(status["outcome"])
    status["elapsed_s"] = time.monotonic() - START
    (RUN / ("status.json" if MODE == "core" else "status-F.json")).write_text(json.dumps(status, indent=1))
    print(json.dumps(status))


main()
