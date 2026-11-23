#!/usr/bin/env python3
"""Failures and outcome of a Part 1 attempt of the v1.0.0 qualification (PROTOCOL.md §5.5, §7).

The frozen runner (``run_v070q3_autonomous.Runner.run_step``) turns any failing collector
child into the status FAILED. Plan section 5.5 distinguishes three causes, and only one of
them may lead to a second attempt:

- **product**: a crash or panic of the product, a timeout, a wrong result, a validation
  failure, an unexpected HTTP error. It is a result: the cell is FAIL, the rest of that
  experiment and every later step are not run, and **no second attempt** may follow;
- **infrastructure**: closed-list evidence only (a host power or thermal event, disk full or a
  filesystem error) **and** no product indication. It allows one rerun of the child, which in
  Part 1 is the second attempt;
- **conformance**: a gate, budget, monitor or recovery stop, an interruption, an end-check or
  binary-integrity failure, or a runner error with no failing child. The attempt is
  NONCONFORMING; a second attempt is allowed (the attempts rule).

Ambiguous evidence, including a child failure with no closed-list evidence at all, is
**product** (fail closed). The closed list and the product indications follow
``run_v100q_q.py`` (the same approach as block Q), restricted to what applies to Part 1.

The runner calls ``record`` at its end; it writes ``logs/failures.jsonl`` (one line per cause,
with its evidence) and ``logs/part1-outcome.json`` (the summary below). ``attempt_budget.sh``
refuses a second attempt after a FAILED attempt unless every recorded cause is infrastructure
or conformance.

**Outcome summary.** For a product failure: the failed cell is FAIL; the other cells of that
experiment and every cell of the later steps are "not run", each with the reason; completed
steps are analysed by their frozen analyzers. For any other non-conforming end: no verdict for
the attempt (``conformance.outcome``), and the steps are listed as completed, failed or not run.

    part1_failures_v100q.py summary CAMP [--write]   # print (and with --write, record) the outcome
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))

V100 = "results/v1.0.0-qualification"
#: Steps of the chain, in order, with their experiment (``run_v100q_autonomous.sequence``).
CHAIN: Tuple[Tuple[str, str], ...] = (("A-block1", "A"), ("A-block2", "A"), ("BC", "B_C"), ("T5", "T5"),
                                      ("R", "R"), ("Rmem", "Rmem"), ("Mreg", "M_reg"))
CLASSES = ("product", "infrastructure", "conformance")
#: Statuses that are conformance stops by definition (the runner's own exits).
CONFORMANCE_STATUSES = ("BLOCKED", "BUDGET EXHAUSTED", "MONITOR LOST", "RECOVERY EXHAUSTED", "INTERRUPTED")
CHILD_EXIT = re.compile(r"^(?P<step>[A-Za-z0-9-]+) exited (?P<exit>-?\d+) \(logs/")
#: Closed list of plan section 5.5 that applies to a Part 1 child (matched case-insensitively).
INFRA_LOG = (
    ("disk", re.compile(r"no space left on device|disk full|read-only file system|input/output error", re.I)),
    ("power", re.compile(r"battery power|not on ac power", re.I)),
    ("thermal", re.compile(r"(?<!no )(thermal|performance) warning level", re.I)),
)
#: Anything pointing at the product (or at a product response) makes the failure product.
PRODUCT_LOG = re.compile(
    r"panick|knotrel-server|knotrel-core|knotrel_core|core-lifecycle|http-lifecycle|release-cells|memory-peak|"
    r"contention-probe|assert|validation|invalid record|not valid|mismatch|wrong result|unexpected|"
    r"timed? ?out|timeout|status [45]\d\d|http [45]\d\d|\b[45]\d\d (bad|internal|service|not)|"
    r"item_errors|noop_mutations|\"?\berrors\"?\s*[=:]\s*[1-9]|not equivalent|signal 9|killed|sigkill|oom", re.I)


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def tail(path: Path, lines: int = 40) -> str:
    if not path.exists():
        return ""
    return "\n".join(path.read_text(errors="replace").splitlines()[-lines:])


def classify_child(log_tail: str) -> Dict[str, Any]:
    """Classification of a failed child from the end of its log (fail closed)."""
    reasons = []
    for name, pattern in INFRA_LOG:
        match = pattern.search(log_tail)
        if match:
            reasons.append(f"{name}: {match.group(0)[:160]}")
    product = PRODUCT_LOG.search(log_tail)
    if reasons and not product:
        return {"classification": "infrastructure", "evidence": reasons}
    why = [] if reasons else ["no closed-list infrastructure evidence (ambiguous counts as product)"]
    if product:
        why.append(f"product indication: {product.group(0)[:160]}")
    return {"classification": "product", "evidence": reasons, "why": why}


def step_times(camp: Path) -> Dict[str, Dict[str, str]]:
    """Start and end times of each step from ``logs/chain-steps.txt``."""
    times: Dict[str, Dict[str, str]] = {}
    path = camp / "logs" / "chain-steps.txt"
    for line in (path.read_text().splitlines() if path.exists() else []):
        parts = line.split(" ", 2)
        if len(parts) == 3:
            what = parts[2]
            key = "end" if what == "end" else "start" if what.startswith("start") else None
            if key:
                times.setdefault(parts[0], {})[key] = parts[1]
    return times


def failures(camp: Path, status: str, cause: str) -> List[Dict[str, Any]]:
    """The causes of a non-CONFORMING end, one record each, with evidence."""
    if status == "CONFORMING":
        return []
    base = {"attempt": camp.name, "status": status, "cause": cause, "recorded_utc": utc()}
    if status in CONFORMANCE_STATUSES:
        return [{**base, "kind": "stop", "classification": "conformance",
                 "evidence": [f"{status}: {cause}"]}]
    match = CHILD_EXIT.match(cause)
    if status == "FAILED" and match:
        step = match["step"]
        log = camp / "logs" / f"{step}.log"
        text = log.read_text(errors="replace") if log.exists() else ""
        log_tail = tail(log)
        verdict = classify_child(log_tail)
        experiment = dict(CHAIN).get(step)
        cell, cell_evidence = failed_cell(camp, step, text)
        return [{**base, "kind": "child", "step": step, "experiment": experiment, "exit": int(match["exit"]),
                 "log": f"logs/{step}.log", "log_tail": log_tail, "time": step_times(camp).get(step, {}),
                 "failed_cell": cell, "failed_cell_evidence": cell_evidence, **verdict}]
    if status == "FAILED":
        kind = "runner" if cause.startswith("runner error") else "end_check"
        return [{**base, "kind": kind, "classification": "conformance",
                 "evidence": [f"{status}: {cause}", "no collector child failed"]}]
    # Any other status (an unknown one included): the attempt did not conform, nothing failed.
    return [{**base, "kind": "stop", "classification": "conformance", "evidence": [f"{status}: {cause}"]}]


def core_rule(camp: Path) -> str:
    path = camp / "logs" / "core-rule.json"
    try:
        return json.loads(path.read_text()).get("outcome") or "identical"
    except (OSError, ValueError):
        return "identical"


def planned_cells(camp: Path, experiment: str) -> List[str]:
    """Cell identifiers of an experiment, from the frozen matrix and collectors."""
    if experiment == "A":
        import run_p0_aa
        return list(run_p0_aa.QUALIFICATION_CELL_IDS)
    if experiment == "B_C":
        import run_lifecycle_qualification as lifecycle
        groups = ("B4", "C") if core_rule(camp) != "different" else None
        return [c["id"] for c in lifecycle.matrix("final", "compact-bfs", True)
                if groups is None or c["experiment"] in groups]
    if experiment == "T5":
        return ["T5"]
    matrix = json.loads((SCRIPTS.parent / V100 / "MATRIX.json").read_text())
    return [c["id"] for c in matrix["experiments"][experiment]["cells"]]


def failed_cell(camp: Path, step: str, log_text: str) -> Tuple[Optional[str], str]:
    """The cell named last in the step's log, if any (the collectors log the cell they run)."""
    experiment = dict(CHAIN).get(step)
    if experiment is None:
        return None, f"unknown step {step}"
    try:
        cells = planned_cells(camp, experiment)
    except Exception as error:  # noqa: BLE001 - the summary must still be written
        return None, f"cells of {experiment} unavailable: {error!r}"
    best, where = None, -1
    for cid in cells:
        at = log_text.rfind(cid)
        if at > where or (at == where and best is not None and len(cid) > len(best)):
            best, where = cid, at
    if best is None or where < 0:
        return None, f"no cell of {experiment} named in logs/{step}.log: the maintainer identifies the failed cell"
    return best, f"the last cell of {experiment} named in logs/{step}.log"


def outcome(camp: Path, status: str, cause: str, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """The Part 1 outcome of plan section 5.5: FAIL, not run, completed, with reasons."""
    times = step_times(camp)
    chain = [(s, e) for s, e in CHAIN if s != "T5" or core_rule(camp) == "different"]
    product = next((r for r in records if r.get("classification") == "product"), None)
    steps, cells = [], {}
    failed_step = product["step"] if product else None
    reached = False
    for step, experiment in chain:
        if step == failed_step:
            state, reason = "failed", f"product failure (exit {product['exit']}): {', '.join(product.get('why', []))}"
            reached = True
        elif reached:
            state, reason = "not run", f"the chain stopped at {failed_step} after a product failure (plan section 5.5)"
        elif "end" in times.get(step, {}):
            state, reason = "completed", ("analysed by its frozen analyzer (PROTOCOL section 6)" if product else
                                          "no verdict: the attempt did not conform")
        elif "start" in times.get(step, {}):
            state, reason = "stopped", f"{status}: {cause}"
        else:
            state, reason = "not run", f"the attempt ended before this step ({status})"
        steps.append({"step": step, "experiment": experiment, "state": state, "reason": reason, **times.get(step, {})})
    if product:
        failed_experiment = product["experiment"]
        for step, experiment in chain:
            entry = next(s for s in steps if s["step"] == step)
            if entry["state"] == "completed" or experiment in cells:
                continue
            listed = []
            for cid in planned_cells(camp, experiment):
                if experiment == failed_experiment and cid == product.get("failed_cell"):
                    listed.append({"id": cid, "verdict": "FAIL",
                                   "reason": f"product failure in {product['step']} ({product['failed_cell_evidence']})"})
                elif experiment == failed_experiment:
                    listed.append({"id": cid, "verdict": "not run",
                                   "reason": f"{failed_experiment} stopped at the product failure in {product['step']}; "
                                             "the frozen analyzer refuses incomplete data, so no other cell of it has a verdict"})
                else:
                    listed.append({"id": cid, "verdict": "not run",
                                   "reason": f"the chain stopped at {product['step']} after a product failure"})
            cells[experiment] = listed
        if product.get("failed_cell") is None:
            cells.setdefault(failed_experiment, []).insert(0, {
                "id": None, "verdict": "FAIL", "reason": f"product failure in {product['step']}: {product['failed_cell_evidence']}"})
    allowed, why = attempt2_allowed(status, records)
    return {"attempt": camp.name, "status": status, "cause": cause, "core_rule": core_rule(camp),
            "classifications": [r["classification"] for r in records], "steps": steps, "cells": cells,
            "attempt2_allowed": allowed, "attempt2_reason": why,
            "rule": "plan section 5.5: a product failure is a result (FAIL, the rest of its experiment and later steps "
                    "not run) and is never rerun; only infrastructure or conformance causes allow a second attempt"}


def attempt2_allowed(status: str, records: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Whether this attempt's end allows a second attempt (the same rule as attempt_budget.sh)."""
    if status == "CONFORMING":
        return False, "CONFORMING: the first CONFORMING attempt is final"
    if not records:
        return False, "no recorded cause: the maintainer decides"
    bad = [r for r in records if r.get("classification") not in ("infrastructure", "conformance")]
    if bad:
        return False, f"{bad[0].get('classification')} failure in {bad[0].get('step')}: never rerun (plan section 5.5)"
    return True, "every recorded cause is " + " or ".join(sorted({r["classification"] for r in records}))


def record(camp: Path, status: str, cause: str) -> Dict[str, Any]:
    """Writes ``logs/failures.jsonl`` and ``logs/part1-outcome.json``; returns the outcome."""
    records = failures(camp, status, cause)
    (camp / "logs").mkdir(parents=True, exist_ok=True)
    with open(camp / "logs" / "failures.jsonl", "w") as handle:
        for r in records:
            handle.write(json.dumps(r) + "\n")
    result = outcome(camp, status, cause, records)
    (camp / "logs" / "part1-outcome.json").write_text(json.dumps(result, indent=1) + "\n")
    return result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    summary = sub.add_parser("summary")
    summary.add_argument("camp", type=Path)
    summary.add_argument("--write", action="store_true", help="also write logs/failures.jsonl and part1-outcome.json")
    args = parser.parse_args(argv)
    from cli_paths import confined_directory
    camp = confined_directory(args.camp, "CAMP")
    line = (camp / "logs" / "CONFORMANCE.txt").read_text().splitlines()[0]
    status, _, cause = line.partition(": ")
    if args.write:
        result = record(camp, status, cause)
    else:
        result = outcome(camp, status, cause, failures(camp, status, cause))
    print(json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
