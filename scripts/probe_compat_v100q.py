#!/usr/bin/env python3
"""Probe compatibility check of the v1.0.0 qualification (plan section 13 item 6), functional only.

Not a measurement and never qualification data: every probe of the perimeter runs once on a
reduced input against the builds of a prepared campaign directory, to show before the freeze
that the probes accept the candidate (D1 refuses delivery sequence 0, #114 refuses empty or
oversized positions and event IDs, ``#[non_exhaustive]`` types must still compile, and #112
labels ``knotrel_graph_jobs_outstanding`` by lane). Timings in the outputs are meaningless
(tiny inputs, no gate, no order) and must not be reported.

Inputs keep each cell's frozen graph size (``--nodes``) and only reduce repetitions: a
smaller graph is not the same workload (at 1,000 nodes the ``events`` trace is refused with
422 by v0.9.0 and the candidate alike, an artifact of the reduction, not of the server).

- ``http-lifecycle`` (candidate build): every B4 cell's scenario and arguments with
  ``--requests <= 2 --pairs 2 --warmup 0``. The probe asserts a success status on
  every request (``send``), so exit 0 means the server accepted every event and import body.
  Checked: exit 0, a ``build`` record of the candidate commit, pair records, and no
  ``answers_agree: false``.
- ``core-lifecycle`` and its ``count-alloc`` build (candidate): one C cell each, 2 cycles. Checked: exit 0 and checkpoint records.
- ``release-cells`` and ``memory-peak`` (candidate and reference builds): every R and Rmem
  cell (2 cycles, 1 rep, no warmup). Checked: exit 0 and the build record of
  each arm's commit.
- ``contention-probe`` against the candidate and the v0.9.0 server: every M_reg cell with
  its frozen size and window. Checked: exit 0 and the frozen M_reg validity rule
  (``analyze_v070r_a4.validity``: no errors, no item errors, no no-op mutations, background
  completed without failures or import starvation) plus status 200 only. The number of
  ``outstanding_jobs`` samples is reported: an empty series (expected on the candidate, whose
  gauge carries a ``lane`` label) must not fail the probe.

    probe_compat_v100q.py CAMP OUT_DIR
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import analyze_v070r_a4 as a4  # noqa: E402
import run_lifecycle_qualification as lifecycle  # noqa: E402
from cli_paths import confined, confined_directory  # noqa: E402

MATRIX = SCRIPTS.parent / "results" / "v1.0.0-qualification" / "MATRIX.json"


def replace(args: List[str], flag: str, value: str) -> List[str]:
    """``args`` with the value after ``flag`` replaced (unchanged if the flag is absent)."""
    out = list(args)
    if flag in out:
        out[out.index(flag) + 1] = value
    return out


def smaller(args: List[str]) -> List[str]:
    args = replace(args, "--cycles", "2")
    args = replace(args, "--reps", "1")
    args = replace(args, "--warmup", "0")
    if "--requests" in args:
        args = replace(args, "--requests", str(min(2, int(args[args.index("--requests") + 1]))))
    return replace(args, "--pairs", "2")


def records(stdout: str) -> List[Dict[str, Any]]:
    out = []
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass
    return out


class Check:
    def __init__(self, out: Path):
        self.out, self.rows, self.n = out, [], 0

    def run(self, name: str, argv: List[str], checks) -> Dict[str, Any]:
        self.n += 1
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=600)
        stem = f"{self.n:03d}-{name}"
        (self.out / f"{stem}.stdout").write_text(proc.stdout)
        (self.out / f"{stem}.stderr").write_text(proc.stderr)
        problems = [] if proc.returncode == 0 else [f"exit {proc.returncode}: {proc.stderr.strip()[-300:]}"]
        recs = records(proc.stdout)
        if proc.returncode == 0:
            problems += checks(recs)
        row = {"name": name, "argv": argv, "exit": proc.returncode, "ok": not problems, "problems": problems}
        self.rows.append(row)
        print(f"[{'ok' if not problems else 'FAIL'}] {name}" + (f": {problems}" if problems else ""), flush=True)
        return row


def build_ok(rev: str):
    def check(recs: List[Dict[str, Any]]) -> List[str]:
        build = recs[0] if recs else {}
        if build.get("kind") != "build":
            return ["no build record first"]
        if build.get("knotrel_rev") != rev:
            return [f"built from {build.get('knotrel_rev')}, expected {rev}"]
        return []
    return check


def main(argv: List[str]) -> int:
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    camp, out = confined_directory(argv[1], "CAMP"), confined(argv[2], "OUT_DIR")
    out.mkdir(parents=True)
    t = camp / "targets"
    rev = {side: subprocess.run(["git", "-C", str(camp / "src" / side / "knotrel"), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip() for side in ("cand", "ref")}
    matrix = json.loads(MATRIX.read_text())
    c = Check(out)
    cells = lifecycle.matrix("final", "compact-bfs", True)
    for cell in [x for x in cells if x["experiment"] == "B4"]:
        def b4(recs, check=build_ok(rev["cand"])):
            problems = check(recs)
            if not [r for r in recs if r.get("kind") == "pair"]:
                problems.append("no pair record")
            if any(r.get("answers_agree") is False for r in recs):
                problems.append("connectivity answers disagree")
            return problems
        c.run(cell["id"], [str(t / "cand-probes/release/http-lifecycle")] + smaller(cell["args"]), b4)
    for binary, target in (("core", "cand-probes"), ("core-count", "cand-probes-count")):
        cell = next(x for x in cells if x["experiment"] == "C" and x["binary"] == binary)
        def ck(recs, check=build_ok(rev["cand"])):
            problems = check(recs)
            if not [r for r in recs if r.get("kind") == "checkpoint"]:
                problems.append("no checkpoint record")
            return problems
        c.run(f"{cell['id']}[{binary}]", [str(t / target / "release/core-lifecycle")] + smaller(cell["args"]), ck)
    for side, probes, peak in (("cand", "cand-probes", "cand-probes-peak"), ("ref", "ref-probes", "ref-probes-peak")):
        for cell in matrix["experiments"]["R"]["cells"]:
            c.run(f"{cell['id']}[{side}]", [str(t / probes / "release/release-cells")] + smaller(cell["args"]),
                  build_ok(rev[side]))
        for cell in matrix["experiments"]["Rmem"]["cells"]:
            c.run(f"{cell['id']}[{side}]", [str(t / peak / "release/memory-peak")] + smaller(cell["args"]),
                  build_ok(rev[side]))
    outstanding: Dict[str, Any] = {}
    for side, server in (("cand", "cand-server"), ("ref", "ref-server")):
        for cell in matrix["experiments"]["M_reg"]["cells"]:
            with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as handle:
                handle.write(json.dumps(cell["config"]) + "\n")
            argv_ = [str(t / "contention/release/contention-probe"), "--server-bin", str(t / server / "release/knotrel-server"),
                     "--mode", cell["mode"], "--lifecycle", str(cell["lifecycle"]).lower(), "--nodes", str(cell["nodes"]),
                     "--seed", str(matrix["experiments"]["M_reg"]["seed"]), "--configs", handle.name]

            def mreg(recs, key=f"{cell['id']}[{side}]"):
                config = [r for r in recs if r.get("kind") == "config"]
                if len(config) != 1:
                    return [f"{len(config)} config records"]
                record = config[0]
                problems = a4.validity(record)
                if set(record.get("statuses", {})) - {"200"}:
                    problems.append(f"statuses {record.get('statuses')}")
                outstanding[key] = record.get("outstanding_jobs")
                return problems
            c.run(f"{cell['id']}[{side}]", argv_, mreg)
            Path(handle.name).unlink()
    summary = {"kind": "probe compatibility check (plan section 13 item 6): functional only, not qualification data",
               "candidate": rev["cand"], "reference": rev["ref"], "runs": len(c.rows),
               "failed": [r["name"] for r in c.rows if not r["ok"]], "outstanding_jobs": outstanding, "rows": c.rows}
    (out / "compat.json").write_text(json.dumps(summary, indent=1) + "\n")
    print(f"probe compatibility: {len(c.rows)} runs, {len(summary['failed'])} failed")
    return 0 if not summary["failed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
