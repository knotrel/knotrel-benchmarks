#!/usr/bin/env python3
"""CF5 block S3: the feeder-under-load protocol with the engine as the only change.

Plan: knotrel ``docs/releases/v1.1.0-cf5-qualification-plan.md``, sections 4 (S3), 8 and 10.
This file rebinds the v1.0.0 block Q runner (``run_v100q_q.py``). It keeps that runner's
rounds, its failure classification, its one-rerun rule and its stop at the deadline, and
only changes the sides:

- **candidate** side: the protocol's seven cells, run on the candidate server with
  ``LOAD_ENGINE=cluster-forest``;
- **reference** side: the same seven cells, run on the **same** candidate server with
  ``LOAD_ENGINE=compact-bfs``.

Each side gets 3 observations per cell, over three rounds, and the side that goes first
alternates (cluster-forest first in rounds 1 and 3). Feeder, load tool and PostgreSQL are the
same for both sides. The load tool, built at the candidate commit, records per observation
the engine it requested and the engine the server reports (``knotrel_build_info``). The
evaluation refuses any observation where either is not its side's engine.

    run_cf5_s3.py run CAMP OUT [--cap-s S]      # CAMP/targets/{cand-server,feeder}
    run_cf5_s3.py evaluate OUT [--out FILE]

**Cap:** 90 minutes from the first step (``CAP_S``), declared in the plan's section 8.
That is about twice the section 11 estimate (0.78 h). When the cap is reached the block is
NONCONFORMING, as in v1.0.0: completed observations are kept, and comparisons that lack
their observations get no verdict.

**Evaluation** (seven comparisons, plan section 4):

- Q1-Q4: the protocol's absolute criteria on the cluster-forest side, with unchanged
  thresholds, computed by ``evaluate_v100q_q.tool_evaluate`` (the port of the load tool's
  ``evaluate``).
- Q5-style: for the three L1 cells with query clients (G100k C=16, G100k C=64, G10k C=16),
  CF median ``query_rps`` must be >= 90 % of the compact-bfs median from the same session,
  and CF median ``query_p99_ms`` <= 125 % of it.

Q1-Q4 are also computed on the compact-bfs side and reported as descriptive.
A failed observation makes every comparison that uses it FAIL. When a reference median is
missing or 0, there is no verdict. Neither case ever counts as a PASS.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_v100q_q as ev  # noqa: E402
import run_v100q_q as q  # noqa: E402

CAP_S = 90 * 60.0
ENGINES = {"candidate": "cluster-forest", "reference": "compact-bfs"}
COMPARED_CELLS = ("L1 G100k C=16", "L1 G100k C=64", "L1 G10k C=16")
RPS_FLOOR, P99_CEILING = 0.90, 1.25
OBSERVATIONS = 3


class S3Runner(q.QRunner):
    """Both sides on the candidate server, all seven cells, ``LOAD_ENGINE`` per side."""

    SIDES = {"candidate": ("cand-server", q.CANDIDATE_CELLS),
             "reference": ("cand-server", q.CANDIDATE_CELLS)}
    ROUNDS = q.ROUNDS

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("cap_s", CAP_S)
        super().__init__(*args, **kwargs)
        self._side: Optional[str] = None

    def binaries(self) -> Dict[str, Path]:
        found = super().binaries()
        found.pop("ref-server")
        return found

    def env(self, server: Path, cells: Sequence[str], step_dir: Path) -> Dict[str, str]:
        env = super().env(server, cells, step_dir)
        if self._side not in ENGINES:
            raise SystemExit(f"no engine bound for side {self._side!r}")
        env["LOAD_ENGINE"] = ENGINES[self._side]
        return env

    def step(self, name: str, side: str, cells: Sequence[str]) -> List[str]:
        self._side = side
        try:
            return super().step(name, side, cells)
        finally:
            self._side = None

    def write_run(self, started: float) -> None:
        super().write_run(started)
        path = self.out / "run.json"
        record = json.loads(path.read_text())
        record["cf5_block"] = "S3"
        record["engines"] = ENGINES
        path.write_text(json.dumps(record, indent=1) + "\n")


def engine_problems(records: Dict[str, List[Dict[str, Any]]]) -> List[str]:
    problems = []
    for side, engine in ENGINES.items():
        for r in records[side]:
            # ``engine`` is what the load tool asked for (LOAD_ENGINE); ``server_engine`` is
            # what the server reports in ``knotrel_build_info``, read back per observation.
            for key in ("engine", "server_engine"):
                if r.get(key) != engine:
                    problems.append(f"{side} {q.cell_key(r)} round {r.get('_round')}: {key} "
                                    f"{r.get(key)!r}, expected {engine!r}")
    return problems


def evaluate(out: Path) -> Dict[str, Any]:
    data = ev.collect(out)
    if data["run"].get("cf5_block") != "S3":
        raise SystemExit(f"{out} is not a CF5 S3 run")
    problems = engine_problems(data["records"])
    if problems:
        raise SystemExit("engine mismatch: " + "; ".join(problems))
    nonconforming = data["run"]["status"] != "COMPLETE"
    cf = ev.tool_evaluate(data["records"]["candidate"])
    cb = ev.tool_evaluate(data["records"]["reference"])

    def state(cells: Sequence[str], paths: Sequence[Sequence[str]],
              sides: Sequence[str]) -> Dict[str, List[str]]:
        failed: List[str] = []
        missing: List[str] = []
        for side in sides:
            for cell in cells:
                obs = [r for r in data["records"][side] if q.cell_key(r) == cell]
                fails = [f for f in data["failures"][side] if f["failed_cell"] == cell]
                failed += [f"{side} {cell}: {f.get('step')} exit {f.get('exit')}" for f in fails]
                failed += [f"{side} {cell} round {r['_round']}: no value for {'.'.join(p)}"
                           for r in obs for p in paths if ev.get(r, p) is None]
                if len(obs) + len(fails) < OBSERVATIONS:
                    missing.append(f"{side} {cell}: {len(obs) + len(fails)} of {OBSERVATIONS}")
                if len(obs) + len(fails) > OBSERVATIONS:
                    raise SystemExit(f"{side} {cell}: more than {OBSERVATIONS} observations")
        return {"failed_observations": failed, "missing_observations": missing}

    def status(passed: Optional[bool], st: Dict[str, List[str]]) -> str:
        if st["failed_observations"]:
            return "FAIL"
        if st["missing_observations"]:
            return "NO_VERDICT"
        return "NO_VERDICT" if passed is None else ("PASS" if passed else "FAIL")

    comparisons: Dict[str, Any] = {}
    for name in ("Q1", "Q2", "Q3", "Q4"):
        cells, paths = ev.USES[name]
        entry = dict(cf["criteria"][name])
        entry.update(state(cells, paths, ("candidate",)))
        entry["status"] = status(entry["pass"], entry)
        comparisons[name] = entry
    for cell in COMPARED_CELLS:
        paths = ev.USES["Q5"][1]  # (queries.requests_per_sec, queries.p99_ms)
        st = state((cell,), paths, ("candidate", "reference"))
        c, r = cf["cells"].get(cell, {}), cb["cells"].get(cell, {})
        cf_rps, cf_p99 = (c.get(m, {}).get("median") for m in ("query_rps", "query_p99_ms"))
        cb_rps, cb_p99 = (r.get(m, {}).get("median") for m in ("query_rps", "query_p99_ms"))
        entry: Dict[str, Any] = {"rule": f"CF median query_rps >= {RPS_FLOOR:.0%} and median "
                                         f"query_p99_ms <= {P99_CEILING:.0%} of compact-bfs",
                                 "query_rps": [cb_rps, cf_rps], "query_p99_ms": [cb_p99, cf_p99],
                                 **st}
        passed: Optional[bool]
        if None in (cf_rps, cf_p99, cb_rps, cb_p99) or cb_rps == 0 or cb_p99 == 0:
            passed = None
            entry["no_verdict_reason"] = "a median is missing or the compact-bfs median is 0"
        else:
            entry["rps_ratio"], entry["p99_ratio"] = cf_rps / cb_rps, cf_p99 / cb_p99
            passed = entry["rps_ratio"] >= RPS_FLOOR and entry["p99_ratio"] <= P99_CEILING
        entry["pass"] = passed
        entry["status"] = status(passed, st)
        comparisons[f"Q5-style {cell}"] = entry
    return {"block": "S3", "schema": "cf5-s3-1", "run_status": data["run"]["status"],
            "run_cause": data["run"]["cause"],
            "s3_status": "NONCONFORMING" if nonconforming else "COMPLETE",
            "engines": ENGINES, "comparisons": comparisons,
            "cluster_forest_cells": cf["cells"], "compact_bfs_cells": cb["cells"],
            "compact_bfs_q1_q4_descriptive": cb["criteria"],
            "reruns": data["run"].get("reruns", {})}


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run")
    run.add_argument("camp", type=Path)
    run.add_argument("out", type=Path)
    run.add_argument("--cap-s", type=float, default=CAP_S)
    run.add_argument("--dry-run", action="store_true",
                     help="check the binaries and the environment, run nothing")
    evaluation = sub.add_parser("evaluate")
    evaluation.add_argument("out", type=Path)
    evaluation.add_argument("--out", dest="result", type=Path)
    args = parser.parse_args(argv)
    if args.command == "run":
        runner = S3Runner(args.camp.resolve(), args.out.resolve(), cap_s=args.cap_s)
        if args.dry_run:
            missing = [f"{k} {p}" for k, p in runner.binaries().items() if not p.exists()]
            if missing:
                print("missing: " + ", ".join(missing))
                return 1
            print("S3 DRY-RUN OK")
            return 0
        return runner.run()
    result = json.dumps(evaluate(args.out), indent=1, sort_keys=True)
    if args.result:
        args.result.write_text(result + "\n")
    else:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
