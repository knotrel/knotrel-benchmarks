#!/usr/bin/env python3
"""CF5 analyzer (knotrel ``docs/releases/v1.1.0-cf5-qualification-plan.md``, sections 6-8, 12).

    analyze_cf5.py --matrix M --run DIR [--run DIR2] [--out analysis.json]

Run once, after collection (and after the second session, passed as a second ``--run``;
its cells replace only INCOMPLETE and NOT_RUN cells of the first, never combining pairs).
Refuses preparatory runs and runs whose recorded matrix hash differs from ``--matrix``.

- Paired cells: per metric, the 24 log ratios ``ln(cf / ref)`` (``ln(ref / cf)`` for
  higher-is-better metrics), interval ``[r(7), r(18)]`` (coverage 97.73 %).
  ``two_sided``: FASTER / SLOWER / EQUIVALENT / INCONCLUSIVE; ``regression`` (V2):
  PASS / REGRESSION / INCONCLUSIVE, never merged. TIMER_LIMITED (no class) when an arm's
  median of a time metric (margin kind ``time`` or ``tail``, all recorded in ns; a sum for
  K2's ``query_ns``; a client p99 such as ``latency_ns.p99``) is below 1 ms.
- Deterministic cells: ``q = cf / ref``: SMALLER / LARGER / SIMILAR; UNDEFINED (no class)
  when the reference value is not positive.
- INCOMPLETE cells are published with their pairs' medians and no class; session-1
  partial pairs of a cell completed in session 2 are kept, labelled, and not combined.
- Family statements (section 12), per family and reference engine, from the matrix's
  ``family`` and ``role``: P = the first-metric class (or state) of each primary cell,
  A = every metric class (or state) of every cell. In order: mixed results, insufficient
  evidence, prefer cluster-forest, prefer the reference, no difference beyond the margins,
  isolated differences. Named cells: those against a preference; for mixed results, every
  cell with a favourable or unfavourable class; for insufficient evidence, every cell
  without evidence. No statement is produced when a session failed the correctness gate.
- Refused: a NONCONFORMING session (interrupted or runner error, section 9); a second run
  that is not the session 2 resumed from the first run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any, Dict, List, Optional

LOWER, UPPER = 7, 18  # one-based order statistics at n = 24
N = 24
TIMER_LIMIT_NS = 1_000_000
FAVOURABLE = {"FASTER", "SMALLER"}
UNFAVOURABLE = {"SLOWER", "LARGER"}
NEUTRAL = {"EQUIVALENT", "SIMILAR"}
NO_EVIDENCE = {"INCONCLUSIVE", "INCOMPLETE", "NOT_RUN", "TIMER_LIMITED", "FAILED", "UNDEFINED"}
TIME_KINDS = {"time", "tail"}


def interval(ratios: List[float]) -> Optional[List[float]]:
    if len(ratios) != N:
        return None
    ordered = sorted(ratios)
    return [ordered[LOWER - 1], ordered[UPPER - 1]]


def two_sided(lo: float, hi: float, margin: float) -> str:
    if hi < math.log(1 - margin):
        return "FASTER"
    if lo > math.log(1 + margin):
        return "SLOWER"
    if math.log(1 - margin) <= lo and hi <= math.log(1 + margin):
        return "EQUIVALENT"
    return "INCONCLUSIVE"


def regression(lo: float, hi: float, margin: float) -> str:
    if hi <= math.log(1 + margin):
        return "PASS"
    if lo > math.log(1 + margin):
        return "REGRESSION"
    return "INCONCLUSIVE"


def deterministic(cf: float, ref: float, margin: float) -> str:
    if ref <= 0:
        return "UNDEFINED"
    q = cf / ref
    if q <= 1 - margin:
        return "SMALLER"
    if q >= 1 + margin:
        return "LARGER"
    return "SIMILAR"


def log_ratio(cf: float, ref: float, direction: str) -> float:
    return math.log(ref / cf) if direction == "higher_is_better" else math.log(cf / ref)


def medians(cell: Dict[str, Any], pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {m["name"]: {"cf_median": statistics.median(p["cf"]["metrics"][m["name"]]
                                                       for p in pairs),
                        "ref_median": statistics.median(p["ref"]["metrics"][m["name"]]
                                                        for p in pairs), "n": len(pairs)}
            for m in cell["metrics"]} if pairs else {}


def classify_paired(cell: Dict[str, Any], pairs: List[Dict[str, Any]]) -> Dict[str, Any]:
    out = medians(cell, pairs)
    for metric in cell["metrics"]:
        name = metric["name"]
        result = out[name]
        if metric.get("margin_kind") in TIME_KINDS and \
                min(result["cf_median"], result["ref_median"]) < TIMER_LIMIT_NS:
            result["class"] = "TIMER_LIMITED"
            continue
        ratios = [log_ratio(p["cf"]["metrics"][name], p["ref"]["metrics"][name],
                            metric["direction"]) for p in pairs]
        bounds = interval(ratios)
        if bounds is None:
            result["class"] = "INCOMPLETE"
            continue
        result["interval_log"] = bounds
        result["median_log"] = statistics.median(ratios)
        rule = regression if cell["rule"] == "regression" else two_sided
        result["class"] = rule(bounds[0], bounds[1], metric["margin"])
    return out


def family_statement(primary: List[str], every: List[str]) -> str:
    """Section 12. ``primary``: first-metric class (or state) of each primary cell;
    ``every``: every metric class (or state) of every cell of the family."""
    favourable = any(c in FAVOURABLE for c in every)
    unfavourable = any(c in UNFAVOURABLE for c in every)
    if favourable and unfavourable:
        return "mixed results"
    if any(c in NO_EVIDENCE for c in every):
        return "insufficient evidence"
    if not primary:
        return "insufficient evidence"
    if favourable and all(c in FAVOURABLE | NEUTRAL for c in primary) and \
            2 * sum(c in FAVOURABLE for c in primary) >= len(primary):
        return "prefer cluster-forest"
    if unfavourable and all(c in UNFAVOURABLE | NEUTRAL for c in primary) and \
            2 * sum(c in UNFAVOURABLE for c in primary) >= len(primary):
        return "prefer reference"
    if all(c in NEUTRAL for c in every):
        return "no difference beyond the margins"
    return "isolated differences"


def load_run(run: Path, matrix_sha: Optional[str] = None) -> Dict[str, Any]:
    status = json.loads((run / "status.json").read_text())
    record = json.loads((run / "record.json").read_text())
    if status.get("preparatory") or record.get("preparatory"):
        raise SystemExit(f"{run} is a preparatory run; it is never classified")
    if matrix_sha and record.get("matrix_sha256") != matrix_sha:
        raise SystemExit(f"{run} was collected with another matrix")
    if status.get("campaign") == "nonconforming":
        raise SystemExit(f"{run} is NONCONFORMING ({status.get('end_cause')}): no classes")
    raw = [json.loads(line) for line in (run / "raw.jsonl").read_text().splitlines() if line]
    return {"status": status, "record": record, "raw": raw, "path": run.resolve()}


def check_sessions(runs: List[Dict[str, Any]]) -> None:
    """The first run is a session 1; a second run is the session 2 resumed from it."""
    if runs[0]["record"].get("session") != 1:
        raise SystemExit("the first --run must be a session 1")
    if len(runs) == 2:
        second = runs[1]["record"]
        resumed = second.get("resume_from")
        if second.get("session") != 2 or not resumed or \
                Path(resumed).resolve() != runs[0]["path"]:
            raise SystemExit("the second --run must be the session 2 resumed from the first")


def analyze(matrix: Dict[str, Any], runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    states: Dict[str, Dict[str, Any]] = {}
    lines_by_cell: Dict[str, List[Dict[str, Any]]] = {}
    partial_session1: Dict[str, List[Dict[str, Any]]] = {}
    for index, run in enumerate(runs):
        for cell_id, state in run["status"]["cells"].items():
            if index > 0 and states.get(cell_id, {}).get("state") not in ("INCOMPLETE",
                                                                          "NOT_RUN"):
                continue
            if index > 0 and cell_id in lines_by_cell:
                partial_session1[cell_id] = lines_by_cell.pop(cell_id)
            states[cell_id] = state
            lines_by_cell[cell_id] = [l for l in run["raw"] if l.get("cell") == cell_id
                                      and "failed_observation" not in l]
    failed = any(r["status"]["campaign"] == "failed" for r in runs)
    cells_out: Dict[str, Dict[str, Any]] = {}
    for cell in matrix["cells"]:
        state = states.get(cell["id"], {"state": "NOT_RUN"})
        entry: Dict[str, Any] = {"block": cell["block"], "family": cell.get("family"),
                                 "role": cell.get("role"), "reference": cell.get("reference"),
                                 "state": state["state"]}
        lines = lines_by_cell.get(cell["id"], [])
        if cell["kind"] == "paired":
            measured = [l for l in lines if not l.get("warmup")]
            if state["state"] == "COMPLETE":
                entry["metrics"] = classify_paired(cell, measured)
            elif measured:
                entry["incomplete_medians"] = medians(cell, measured)
            if cell["id"] in partial_session1:
                old = [l for l in partial_session1[cell["id"]] if not l.get("warmup")]
                entry["session_1_partial"] = {"label": "INCOMPLETE-session-1",
                                              "medians": medians(cell, old)}
        elif cell["kind"] == "deterministic" and state["state"] == "COMPLETE":
            arms = {l["arm"]: l["metrics"] for l in lines}
            entry["metrics"] = {m["name"]: {"cf": arms["cf"][m["name"]],
                                            "ref": arms["ref"][m["name"]],
                                            "class": deterministic(arms["cf"][m["name"]],
                                                                   arms["ref"][m["name"]],
                                                                   m["margin"])}
                                for m in cell["metrics"]}
        cells_out[cell["id"]] = entry
    statements: Dict[str, Dict[str, Any]] = {}
    if failed:
        statements = {"not_produced": "a session failed the correctness gate"}
    else:
        groups: Dict[tuple, List[tuple]] = {}
        for cell_id, entry in cells_out.items():
            if entry["family"] is None:
                continue
            groups.setdefault((entry["family"], entry["reference"]), []).append((cell_id, entry))
        for (family, reference), members in groups.items():
            primary, every, directions = [], [], {}
            for cell_id, entry in members:
                if "metrics" in entry:
                    classes = [m["class"] for m in entry["metrics"].values()]
                else:
                    classes = [entry["state"]]
                every.extend(classes)
                if entry["role"] == "primary":
                    primary.append(classes[0])
                directions[cell_id] = classes
            statement = family_statement(primary, every)
            named_classes = {"prefer reference": FAVOURABLE,
                             "prefer cluster-forest": UNFAVOURABLE,
                             "mixed results": FAVOURABLE | UNFAVOURABLE,
                             "isolated differences": FAVOURABLE | UNFAVOURABLE,
                             "insufficient evidence": NO_EVIDENCE}.get(statement, set())
            named = sorted(cid for cid, classes in directions.items()
                           if any(c in named_classes for c in classes))
            statements.setdefault(family, {})[reference] = {"statement": statement,
                                                            "named_cells": named}
    return {"schema": "cf5-analysis-2", "campaign_failed": failed, "cells": cells_out,
            "family_statements": statements}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if len(args.run) > 2:
        parser.error("at most two sessions")
    text = args.matrix.read_bytes()
    sha = hashlib.sha256(text).hexdigest()
    runs = [load_run(r, sha) for r in args.run]
    check_sessions(runs)
    result = analyze(json.loads(text), runs)
    out = json.dumps(result, indent=1, sort_keys=True)
    if args.out:
        args.out.write_text(out + "\n")
    else:
        print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
