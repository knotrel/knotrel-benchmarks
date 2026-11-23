#!/usr/bin/env python3
"""Block Q of the v1.0.0 qualification: feeder under load, with the Q5 reference arm.

Plan (knotrel ``docs/releases/v1.0.0-qualification-plan.md`` sections 5.5, 5.7 and 9; matrix
``v1_0_0.q``). The approved protocol (knotrel ``docs/integrations/feeder-under-load.md``) is
run by its own load tool, built at the candidate commit, unchanged:

- **Candidate:** the seven cells, 3 observations each, on the candidate server.
- **Q5 reference arm:** L1 G100k C=16 and C=64, 3 observations each, on the v0.9.0 server, in
  the same session, with the same feeder, tool and PostgreSQL.
- **Order: three rounds.** Each round runs one repetition of the candidate's seven cells and
  one of the two reference cells; the side that goes first alternates (candidate first in
  rounds 1 and 3). Each step is one tool invocation with ``LOAD_REPS=1`` and ``LOAD_CELLS``;
  ``LOAD_WINDOW_SECS``, ``LOAD_BACKLOG`` and every R2/burn variable are removed from the
  environment, so the tool's defaults (60 s window, 100,000 backlog) apply.
- **Cap: 30 minutes** of wall time from the first step (``--cap-s``). A step that would start
  after the deadline does not start; a running step is stopped at the deadline. Either way
  block Q is NONCONFORMING: the completed observations are kept, and criteria whose cells lack
  their three observations get no verdict (``evaluate_v100q_q.py``).
- **Failures.** A step that exits non-zero is recorded in ``failures.jsonl`` with its
  evidence: exit status, the time, the last lines of its stderr, and the host state before and
  after (``pmset`` power and thermal state, free disk space, the Docker container list). The
  failed observation is the first cell of the step without a result line. It is classified
  ``infrastructure`` only when the evidence matches a closed list (plan section 5.5): a power
  or thermal event, disk full or a filesystem error, loss of the PostgreSQL container or its
  loopback connection; and nothing in the stderr points at the product (a panic or crash of
  the knotrel server or feeder, a readiness timeout, an HTTP error from the server). Anything
  else, including ambiguous evidence, is ``not_infrastructure`` (fail closed): the failed
  observation counts as measured, with its failure, and is never rerun. An infrastructure
  failure allows **one** rerun of that observation (once per round, side and cell, recorded
  with its cause); a second infrastructure failure of the same observation loses it, and block
  Q is then NONCONFORMING (``infrastructure_exhausted`` in ``run.json``), which allows the one
  rerun of Q as a whole. After a failure, the step's remaining cells run in a continuation
  step, so no other observation is lost.
- **Second attempt of Q** (``--attempt2-gate DIR``, used by ``run_part3.sh CAMP 2``): allowed
  only if the first ended other than COMPLETE, and only for the cap (NONCONFORMING), an
  infrastructure failure whose rerun was used up (NONCONFORMING), or a runner or tooling error
  (FAILED) with no product failure recorded. ``--write-marker`` then writes
  ``superseded_by.json`` into the first attempt; the evaluator accepts only the final attempt.
- **Cells** (``--check-cells LOAD_RS``, used by ``launch_env_check.sh``): every ``LOAD_CELLS``
  value of the plan must be a cell key of the load tool (its ``CELLS`` table, in its order); the
  tool silently skips an unknown key, so a typo would lose observations.

The PostgreSQL admin URL comes from the environment (``KNOTREL_PG_ADMIN_URL``) and is never
written. Outputs (``OUT``, which must not exist): one directory per step (the tool's
``results.jsonl``, ``summary.json``, stdout and stderr), ``steps.jsonl``, ``failures.jsonl``,
``host-*.txt`` and ``run.json`` (status, times, binaries and their SHA-256).

    run_v100q_q.py CAMP OUT [--cap-s 1800]
    run_v100q_q.py --check-cells LOAD_RS
    run_v100q_q.py --attempt2-gate PART3_DIR [--write-marker NEW_NAME]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined, confined_directory  # noqa: E402

CAP_S = 30 * 60.0
CANDIDATE_CELLS = ("L1 G100k C=0", "L1 G100k C=16", "L1 G100k C=64", "L1 G10k C=16",
                   "L2 G100k C=0", "L2 G100k C=16", "L2 G100k C=64")
REFERENCE_CELLS = ("L1 G100k C=16", "L1 G100k C=64")
ROUNDS = ((1, ("candidate", "reference")), (2, ("reference", "candidate")), (3, ("candidate", "reference")))
SIDES = {"candidate": ("cand-server", CANDIDATE_CELLS), "reference": ("ref-server", REFERENCE_CELLS)}
#: Environment variables the protocol run must not set (tool defaults apply; no R2 variant).
REMOVED_ENV = ("LOAD_REPS", "LOAD_CELLS", "LOAD_WINDOW_SECS", "LOAD_BACKLOG", "LOAD_ARM", "LOAD_CALIBRATION",
               "LOAD_R2_DECIDE", "LOAD_BURN_DUTY", "LOAD_OUT", "LOAD_PG_PROCESS_PATTERNS")
REMOVED_PREFIXES = ("LOAD_REMOTE_",)

#: Evidence patterns of plan section 5.5 (closed list). Matched case-insensitively.
INFRA_STDERR = (
    ("disk", re.compile(r"no space left on device|disk full|read-only file system|input/output error", re.I)),
    ("postgres", re.compile(r"connection refused.*(5432|postgres)|(postgres|5432).*connection refused|"
                            r"docker:? .*error|error response from daemon|container .* (exited|not running)", re.I)),
)
#: Anything pointing at the product makes the failure not infrastructure (fail closed).
PRODUCT_STDERR = re.compile(r"knotrel-server|knotrel-pg-feeder|feeder.*(ready|panick|exit)|not ready|"
                            r"status (4|5)\d\d|\b(4|5)\d\d\b.*(knotrel|/v1/)|server (crash|exited|died)", re.I)


def utc(t: Optional[float] = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() if t is None else t))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def run_quiet(argv: Sequence[str]) -> str:
    try:
        proc = subprocess.run(list(argv), capture_output=True, text=True, timeout=20)
        return (proc.stdout + proc.stderr).strip()
    except (OSError, subprocess.SubprocessError) as error:
        return f"unavailable: {error}"


def host_state(out: Path) -> Dict[str, Any]:
    """Evidence of the host state: power, thermal, free disk, the Docker container list."""
    free = shutil.disk_usage(out).free if out.exists() else None
    return {"utc": utc(), "power": run_quiet(["pmset", "-g", "batt"]), "therm": run_quiet(["pmset", "-g", "therm"]),
            "free_bytes": free,
            "docker": run_quiet(["docker", "ps", "-a", "--format", "{{.Names}} {{.Image}} {{.Status}}"])}


def cell_key(record: Dict[str, Any]) -> str:
    """The tool's cell key (``cell_key`` in load.rs)."""
    return f"{record['scenario']} {record['graph']} C={record['clients']}"


def completed_cells(step_dir: Path) -> List[str]:
    path = step_dir / "results.jsonl"
    if not path.exists():
        return []
    return [cell_key(json.loads(line)) for line in path.read_text().splitlines() if line.strip()]


def classify_failure(stderr_tail: str, before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    """``infrastructure`` only for closed-list evidence with no product indication; else not.

    Power evidence is a ``pmset -g batt`` first line reading "Battery Power"; thermal evidence
    a recorded thermal or performance warning level. Unavailable readings are no evidence."""
    reasons = []
    for state in (before, after):
        # Only a positive battery reading is power evidence; an unavailable or unparsable
        # pmset output is no evidence (finding N5).
        if "Battery Power" in (str(state.get("power", "")).splitlines() or [""])[0]:
            reasons.append(f"power: {str(state.get('power', ''))[:120]}")
        therm = str(state.get("therm", ""))
        if re.search(r"(thermal|performance) warning level", therm, re.I) and "No thermal warning level" not in therm:
            reasons.append(f"thermal: {therm[:160]}")
    for name, pattern in INFRA_STDERR:
        match = pattern.search(stderr_tail)
        if match:
            reasons.append(f"{name}: {match.group(0)[:160]}")
    if after.get("free_bytes") is not None and after["free_bytes"] < 512 * 1024 ** 2:
        reasons.append(f"disk: {after['free_bytes']} bytes free")
    product = PRODUCT_STDERR.search(stderr_tail)
    if reasons and not product:
        return {"classification": "infrastructure", "evidence": reasons}
    why = ["no closed-list infrastructure evidence"] if not reasons else []
    if product:
        why.append(f"product indication: {product.group(0)[:160]}")
    return {"classification": "not_infrastructure", "evidence": reasons, "why": why}


TOOL_CELL = re.compile(r'Cell\s*\{\s*scenario:\s*"(L\d)",\s*graph:\s*"(G\w+)",\s*clients:\s*(\d+),?\s*\}')


def tool_cell_keys(load_rs: str) -> List[str]:
    """Cell keys of the load tool's ``CELLS`` table (``examples/load.rs``), in its order."""
    start = load_rs.find("const CELLS")
    if start < 0:
        return []
    end = load_rs.find("];", start)
    return [f"{a} {b} C={c}" for a, b, c in TOOL_CELL.findall(load_rs[start:end])]


def cell_problems(load_rs: str) -> List[str]:
    """Every ``LOAD_CELLS`` value of the three rounds must be a tool cell key, in tool order
    (the failed observation of a step is the first planned cell without a result)."""
    keys = tool_cell_keys(load_rs)
    if not keys:
        return ["no CELLS table in the load tool source"]
    problems = []
    for number, order in ROUNDS:
        for side in order:
            cells = list(SIDES[side][1])
            unknown = [c for c in cells if c not in keys]
            if unknown:
                problems.append(f"round{number}-{side}: LOAD_CELLS {unknown} are not cells of the load tool {keys}")
            elif cells != [k for k in keys if k in cells]:
                problems.append(f"round{number}-{side}: LOAD_CELLS {cells} are not in the tool's order {keys}")
    return problems


def attempt2_gate(part3: Path) -> Tuple[bool, str]:
    """Whether block Q may be run a second time after the attempt in ``part3`` (plan section 9).

    Allowed only if that attempt did not end COMPLETE and its cause is the cap or an
    infrastructure failure whose rerun was used up (both NONCONFORMING), or a runner or tooling
    error (FAILED) with no product failure recorded in ``failures.jsonl``. A COMPLETE Q is
    final whatever ``failures.jsonl`` holds; a result never buys a second attempt."""
    try:
        run = json.loads((part3 / "run.json").read_text())
    except (OSError, ValueError) as error:
        return False, f"no readable run.json in {part3}: {error}"
    if (part3 / "superseded_by.json").exists():
        return False, f"{part3} is already superseded"
    status = run.get("status")
    failures = []
    path = part3 / "failures.jsonl"
    if path.exists():
        failures = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    product = [f for f in failures if f.get("failed_cell") and f.get("classification") != "infrastructure"]
    if status == "COMPLETE":
        return False, "Q ended COMPLETE: it is final, whatever failures.jsonl holds"
    if status == "NONCONFORMING":
        if run.get("cap_reached"):
            return True, "the first Q exceeded its cap (NONCONFORMING)"
        if run.get("infrastructure_exhausted"):
            return True, f"infrastructure failure after its one rerun: {run['infrastructure_exhausted']}"
        return False, f"NONCONFORMING without a recorded cap or exhausted infrastructure rerun: {run.get('cause')}"
    if status == "FAILED":
        if product:
            return False, f"FAILED with a product failure recorded ({product[0].get('step')} {product[0].get('failed_cell')})"
        return True, f"runner or tooling error with no product failure: {run.get('cause')}"
    return False, f"status {status!r} allows no second attempt"


class QRunner:
    """Runs the three rounds under the cap; ``launch`` is injectable for tests."""

    def __init__(self, camp: Path, out: Path, cap_s: float = CAP_S, clock: Callable[[], float] = time.time,
                 launch: Optional[Callable[..., int]] = None, state: Callable[[Path], Dict[str, Any]] = host_state):
        self.camp, self.out, self.cap_s, self.clock = camp, out, cap_s, clock
        self.launch = launch or self.launch_tool
        self.state = state
        self.targets = camp / "targets"
        self.reruns: Dict[str, str] = {}
        #: Observations lost to a second infrastructure failure (their one rerun used up).
        self.infrastructure_exhausted: List[str] = []
        self.status, self.cause = "INCOMPLETE", "the runner ended before its last step"
        self.deadline = 0.0
        self.cap_reached = False

    # -- environment -------------------------------------------------------------------
    def binaries(self) -> Dict[str, Path]:
        t = self.targets
        return {"cand-server": t / "cand-server/release/knotrel-server", "ref-server": t / "ref-server/release/knotrel-server",
                "feeder": t / "feeder/release/knotrel-pg-feeder", "load": t / "feeder/release/examples/load"}

    def env(self, server: Path, cells: Sequence[str], step_dir: Path) -> Dict[str, str]:
        env = {k: v for k, v in os.environ.items()
               if k not in REMOVED_ENV and not k.startswith(REMOVED_PREFIXES)}
        if not env.get("KNOTREL_PG_ADMIN_URL"):
            raise SystemExit("KNOTREL_PG_ADMIN_URL is not set")
        env.update({"KNOTREL_BIN": str(server), "FEEDER_BIN": str(self.binaries()["feeder"]), "LOAD_OUT": str(step_dir),
                    "LOAD_REPS": "1", "LOAD_CELLS": ",".join(cells)})
        return env

    def launch_tool(self, argv: List[str], env: Dict[str, str], step_dir: Path, timeout_s: float) -> int:
        """Runs one tool invocation in its own session; on timeout, stops its process group."""
        with open(step_dir / "load.stdout", "w") as stdout, open(step_dir / "load.stderr", "w") as stderr:
            child = subprocess.Popen(argv, env=env, stdout=stdout, stderr=stderr, start_new_session=True)
            try:
                return child.wait(timeout=max(timeout_s, 0.0))
            except subprocess.TimeoutExpired:
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(child.pid, sig)
                    except (ProcessLookupError, PermissionError):
                        pass
                    try:
                        child.wait(timeout=20)
                        break
                    except subprocess.TimeoutExpired:
                        continue
                return -999

    # -- records -----------------------------------------------------------------------
    def append(self, name: str, record: Dict[str, Any]) -> None:
        with open(self.out / name, "a") as handle:
            handle.write(json.dumps(record) + "\n")

    def write_run(self, started: float) -> None:
        binaries = {k: {"path": str(p), "sha256": sha256(p) if p.exists() else None} for k, p in self.binaries().items()}
        record = {"status": self.status, "cause": self.cause, "started_utc": utc(started), "ended_utc": utc(),
                  "cap_s": self.cap_s, "deadline_utc": utc(self.deadline), "seconds": round(self.clock() - started, 1),
                  "rounds": [{"round": r, "order": list(order)} for r, order in ROUNDS],
                  "cells": {side: list(cells) for side, (_, cells) in SIDES.items()},
                  "reruns": self.reruns, "infrastructure_exhausted": self.infrastructure_exhausted,
                  "cap_reached": self.cap_reached, "binaries": binaries,
                  "removed_env": list(REMOVED_ENV) + [p + "*" for p in REMOVED_PREFIXES]}
        (self.out / "run.json").write_text(json.dumps(record, indent=1) + "\n")

    # -- steps -------------------------------------------------------------------------
    def step(self, name: str, side: str, cells: Sequence[str]) -> List[str]:
        """Runs ``cells`` of ``side`` in one tool invocation (with continuations after a failure).
        Returns the cells that were never observed because the cap was reached."""
        server = self.binaries()[SIDES[side][0]]
        pending, attempt = list(cells), 0
        while pending:
            remaining = self.deadline - self.clock()
            if remaining <= 0:
                return pending
            step_dir = self.out / (name if attempt == 0 else f"{name}-cont{attempt}")
            step_dir.mkdir()
            before = self.state(self.out)
            began = self.clock()
            argv = ["/usr/bin/caffeinate", "-dimsu", str(self.binaries()["load"])]
            code = self.launch(argv, self.env(server, pending, step_dir), step_dir, remaining)
            after = self.state(self.out)
            done = completed_cells(step_dir)
            self.append("steps.jsonl", {"step": step_dir.name, "side": side, "cells": pending, "exit": code,
                                        "started_utc": utc(began), "seconds": round(self.clock() - began, 1),
                                        "completed": done})
            if code == 0 and sorted(done) == sorted(pending):
                return []
            if code == -999:
                self.append("failures.jsonl", {"step": step_dir.name, "side": side, "utc": utc(), "exit": code,
                                               "cause": "stopped at the Q deadline (cap)", "completed": done})
                return [c for c in pending if c not in done]
            missing = [c for c in pending if c not in done]
            failed = missing[0] if missing else None
            tail = "\n".join((step_dir / "load.stderr").read_text(errors="replace").splitlines()[-40:]) \
                if (step_dir / "load.stderr").exists() else ""
            verdict = classify_failure(tail, before, after)
            # One rerun per observation: the round, the side and the cell (finding N4).
            key = f"{name}:{failed}"
            infra = verdict["classification"] == "infrastructure" and failed is not None
            rerun = infra and key not in self.reruns
            if infra and not rerun:
                self.infrastructure_exhausted.append(key)
            self.append("failures.jsonl", {"step": step_dir.name, "side": side, "utc": utc(), "exit": code,
                                           "failed_cell": failed, "completed": done, "stderr_tail": tail,
                                           "host_before": before, "host_after": after, **verdict,
                                           "rerun": rerun})
            if rerun:
                self.reruns[key] = step_dir.name
                pending = missing
            else:
                pending = missing[1:]
            attempt += 1
        return []

    def run(self) -> int:
        binaries = self.binaries()
        for name, path in binaries.items():
            if not path.exists():
                raise SystemExit(f"missing {name} binary {path}")
        self.out.mkdir(parents=True)
        (self.out / "host-before.txt").write_text(json.dumps(self.state(self.out), indent=1) + "\n")
        started = self.clock()
        self.deadline = started + self.cap_s
        unobserved: Dict[str, List[str]] = {}
        try:
            for number, order in ROUNDS:
                for side in order:
                    left = self.step(f"round{number}-{side}", side, SIDES[side][1])
                    if left:
                        unobserved[f"round{number}-{side}"] = left
            self.cap_reached = bool(unobserved)
            causes = []
            if unobserved:
                causes.append(f"Q BUDGET EXHAUSTED ({self.cap_s / 60:.0f} min): unobserved {unobserved}")
            if self.infrastructure_exhausted:
                causes.append(f"INFRASTRUCTURE FAILURE after the one rerun: lost {self.infrastructure_exhausted}")
            if causes:
                self.status, self.cause = "NONCONFORMING", "; ".join(causes)
            else:
                self.status, self.cause = "COMPLETE", "every planned observation ran within the cap"
        except BaseException as error:  # noqa: BLE001 - any stop still writes the run record
            self.status, self.cause = "FAILED", f"runner error: {error!r}"
            raise
        finally:
            (self.out / "host-after.txt").write_text(json.dumps(self.state(self.out), indent=1) + "\n")
            self.write_run(started)
        print(f"Q {self.status}: {self.cause}")
        return 0 if self.status == "COMPLETE" else 1


def gate_main(argv: Sequence[str]) -> int:
    """``--check-cells LOAD_RS`` and ``--attempt2-gate DIR [--write-marker NAME]``."""
    if argv[0] == "--check-cells" and len(argv) == 2:
        problems = cell_problems(Path(argv[1]).read_text())
        for p in problems:
            print(p, file=sys.stderr)
        if not problems:
            print("Q cells ok: " + ", ".join(tool_cell_keys(Path(argv[1]).read_text())))
        return 1 if problems else 0
    if argv[0] == "--attempt2-gate" and len(argv) in (2, 4) and (len(argv) == 2 or argv[2] == "--write-marker"):
        part3 = Path(argv[1])
        allowed, reason = attempt2_gate(part3)
        print(reason, file=sys.stdout if allowed else sys.stderr)
        if allowed and len(argv) == 4:
            (part3 / "superseded_by.json").write_text(json.dumps(
                {"superseded_by": argv[3], "utc": utc(), "reason": reason,
                 "rule": "plan section 9: Q rerun once as a whole; only the final attempt is evaluated and published"},
                indent=1) + "\n")
        return 0 if allowed else 1
    print(__doc__, file=sys.stderr)
    return 2


def main(argv: Optional[Sequence[str]] = None) -> int:
    args_in = list(sys.argv[1:] if argv is None else argv)
    if args_in and args_in[0] in ("--check-cells", "--attempt2-gate"):
        return gate_main(args_in)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("camp", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--cap-s", type=float, default=CAP_S)
    args = parser.parse_args(args_in)
    args.camp = confined_directory(args.camp, "CAMP")
    args.out = confined(args.out, "OUT")
    if args.out.exists():
        parser.error(f"refusing to reuse {args.out}")
    if args.cap_s != CAP_S:
        print(f"note: cap {args.cap_s} s differs from the frozen {CAP_S} s (tests and smoke runs only)", file=sys.stderr)
    return QRunner(args.camp.resolve(), args.out.resolve(), args.cap_s).run()


if __name__ == "__main__":
    sys.exit(main())
