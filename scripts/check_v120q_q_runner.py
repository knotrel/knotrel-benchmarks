#!/usr/bin/env python3
"""Pre-collection check of the v1.2.0 block-Q runner chain (knotrel#182, plan section 13).

    check_v120q_q_runner.py CAMP --out CAMP/logs/Q-runner-check.json [--fail-sample Q_DIR]

Checks, with the real functions and no measurement:

1. **Layout.** For each Q cell of the attempt-2 matrix (``Q``, ``Q-K4``), the directory the
   runner gives the collector (``run_cf5.delegated_run_dir``), plus the ``Q`` subdirectory
   that ``run_q.sh`` writes, is accepted by the evaluator (``evaluate_v100q_q.attempts``) as
   a final attempt. A misnamed directory is refused explicitly.
2. **Tool error versus failed criterion.** ``run_cf5.run_delegated`` with stand-in
   collectors: exit 0 is ``DELEGATED_DONE``, exit 1 (the Q cap) ``INCOMPLETE``, exit 6 (the
   evaluation failed after the measurement) ``TOOL_ERROR`` with a single attempt (never
   rerun). A failed criterion is not an exit status at all: the evaluator exits 0 and writes
   ``FAIL`` in the evaluation, as checked by ``run_q.sh``'s tool-error branch, which exits 6
   only when ``evaluate_v100q_q.py`` fails. With ``--fail-sample`` (a measured Q run with a
   failed criterion, such as attempt 1's ``delegated/Q-attempt1/Q``), the evaluator is run on
   it: it must return an evaluation with a ``FAIL`` and raise nothing.
3. **Collector wiring.** ``run_q.sh`` holds the exit-6 branch, and the campaign's tool map
   gives both Q cells ``tool_error_exit`` [6] and ``incomplete_exit`` [1], with ``Q-K4``
   naming the ``variant-k4`` server variant.

Exit 0 when every check holds; 1 otherwise, with the failed checks in the output.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evaluate_v100q_q as ev  # noqa: E402
import run_cf5  # noqa: E402
from cli_paths import confined  # noqa: E402

Q_CELLS = ("Q", "Q-K4")


def layout_checks(scratch: Path) -> List[Dict[str, Any]]:
    results = []
    for cell in Q_CELLS:
        q_dir = run_cf5.delegated_run_dir(scratch, cell, 1) / "Q"
        q_dir.mkdir(parents=True)
        try:
            final = ev.attempts(q_dir)["final_attempt"]
            ok = final == f"{cell}-attempt1/Q"
            results.append({"check": f"layout {cell}", "path": str(q_dir.relative_to(scratch)),
                            "final_attempt": final, "ok": ok})
        except SystemExit as refused:
            results.append({"check": f"layout {cell}", "ok": False, "refused": str(refused)})
    wrong = scratch / "delegated" / "run" / "Q"
    wrong.mkdir(parents=True)
    try:
        ev.attempts(wrong)
        results.append({"check": "misnamed layout refused", "ok": False})
    except SystemExit as refused:
        results.append({"check": "misnamed layout refused", "ok": True, "message": str(refused)})
    return results


def exit_checks(scratch: Path) -> List[Dict[str, Any]]:
    results = []
    expected = {0: ("DELEGATED_DONE", 1), 1: ("INCOMPLETE", 1), 6: ("TOOL_ERROR", 1)}
    for code, (state, attempts) in expected.items():
        out = scratch / f"exit{code}"
        out.mkdir()
        tools = {"_delegated": {"Q": {"argv": [sys.executable, "-c", f"raise SystemExit({code})"],
                                      "incomplete_exit": [1], "tool_error_exit": [6]}}}
        got = run_cf5.run_delegated({"id": "Q"}, tools, out)
        ok = got["state"] == state and len(got["attempts"]) == attempts
        results.append({"check": f"collector exit {code}", "expected": state,
                        "state": got["state"], "attempts": len(got["attempts"]), "ok": ok})
    return results


def fail_sample_check(q_dir: Path) -> List[Dict[str, Any]]:
    try:
        evaluation = ev.evaluate(q_dir, None)
    except SystemExit as refused:
        return [{"check": "failed criterion is a verdict, not a tool error", "ok": False,
                 "refused": str(refused)}]
    failed = sorted(name for name, c in evaluation["criteria"].items()
                    if isinstance(c, dict) and c.get("status") == "FAIL")
    return [{"check": "failed criterion is a verdict, not a tool error", "sample": str(q_dir),
             "failed_criteria": failed, "ok": bool(failed)}]


def wiring_checks(camp: Optional[Path], run_q: Path) -> List[Dict[str, Any]]:
    text = run_q.read_text()
    results = [{"check": "run_q.sh exits 6 when the evaluation fails",
                "ok": "exit 6" in text and "evaluate_v100q_q.py" in text}]
    if camp is None:
        return results
    tools = json.loads((camp / "tools.json").read_text())["_delegated"]
    for cell in Q_CELLS:
        spec = tools.get(cell, {})
        ok = spec.get("tool_error_exit") == [6] and spec.get("incomplete_exit") == [1]
        if cell == "Q-K4":
            ok = ok and spec.get("argv", [])[-1:] == ["variant-k4"]
        results.append({"check": f"tool map {cell}", "ok": ok,
                        "argv_tail": spec.get("argv", [])[-2:]})
    return results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("camp", type=Path, nargs="?")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--fail-sample", type=Path)
    args = parser.parse_args(argv)
    camp = confined(args.camp, "CAMP") if args.camp else None
    run_q = Path(__file__).resolve().parent.parent / "results" / "v1.2.0-qualification" / "run_q.sh"
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        (scratch / "layout").mkdir()
        (scratch / "exits").mkdir()
        checks = (layout_checks(scratch / "layout") + exit_checks(scratch / "exits")
                  + wiring_checks(camp, run_q))
    if args.fail_sample:
        checks += fail_sample_check(confined(args.fail_sample, "--fail-sample"))
    record = {"schema": "v120q-q-runner-check-1", "ok": all(c["ok"] for c in checks),
              "checks": checks}
    text = json.dumps(record, indent=1)
    if args.out:
        confined(args.out, "--out").write_text(text + "\n")
    print(text)
    return 0 if record["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
