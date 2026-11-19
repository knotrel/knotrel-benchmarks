#!/usr/bin/env python3
"""Per-cell experimental conformance of a v0.7.0 re-qualification attempt.

It replaces, for the re-qualification, the first campaign's cross-check
(``analyze_v070_conformance.py``). That script reads the first campaign's
monitor format (``kind``/``utc``/``args`` records of the top five processes)
and classes Terminal.app as a user application; the re-qualification monitor
writes another format, and amendment 2 makes Terminal.app the controller. The
re-qualification gate already decides conformance for every measured child,
before and after it, against the allow-list monitor; this script only
collects those decisions per cell. It reads conformance records only, never
measurements, and changes nothing.

Per cell (cells as in ``report_v070r_interference.py``):
- ``children``: gated children of the cell;
- ``conforming_children``: children whose gate record has ``conforming``
  true and no ``reasons``;
- ``status``: CONFORMING when every child is, and the attempt as a whole is
  CONFORMING (``logs/CONFORMANCE.txt`` first line, the end checks with gated
  counts equal to collected counts and no reasons, and no ``gate/gate-stop.json``);
  NONCONFORMING otherwise.

    report_v070r_cell_conformance.py CAMP --out OUT.json [--markdown OUT.md]
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_v070r_interference as ri  # noqa: E402


def attempt_checks(camp: Path) -> Dict[str, Any]:
    first = (camp / "logs" / "CONFORMANCE.txt").read_text().splitlines()[0]
    end_path = camp / "logs" / "end-checks.txt"  # absent when the chain stopped before its end checks
    end = (ast.literal_eval(end_path.read_text().strip().splitlines()[-1]) if end_path.exists()
           else {"gated": None, "collected": None, "reasons": ["no end checks (chain stopped earlier)"]})
    return {
        "conformance_line": first,
        "attempt_conforming": first.startswith("CONFORMING"),
        "gate_stop": (camp / "gate" / "gate-stop.json").exists(),
        "gated": end["gated"], "collected": end["collected"], "end_check_reasons": end["reasons"],
        "end_checks_ok": end["gated"] is not None and end["gated"] == end["collected"] and not end["reasons"],
    }


def report(camp: Path) -> Dict[str, Any]:
    checks = attempt_checks(camp)
    whole = checks["attempt_conforming"] and checks["end_checks_ok"] and not checks["gate_stop"]
    children = [r for r in ri.load_jsonl(camp / "gate" / "gate-log.jsonl")
                if r.get("kind") == "child" and r["label"].partition(":")[0] in ri.EXPERIMENTS]
    quiet = [r for r in ri.load_jsonl(camp / "gate" / "gate-log.jsonl") if r.get("label") == "quiet-period"]
    cells = ri.assign_cells(camp, children)
    rows: Dict[tuple, Dict[str, Any]] = {}
    for child, cell in zip(children, cells):
        experiment = child["label"].partition(":")[0]
        row = rows.setdefault((experiment, cell), {"experiment": experiment, "cell": cell, "children": 0,
                                                   "conforming_children": 0, "reasons": []})
        row["children"] += 1
        ok = child.get("conforming") is True and not child.get("reasons")
        row["conforming_children"] += ok
        if not ok:
            row["reasons"].append({"label": child["label"], "reasons": child.get("reasons")})
    out = sorted(rows.values(), key=lambda r: (ri.EXPERIMENTS.index(r["experiment"]), r["cell"]))
    for row in out:
        row["status"] = "CONFORMING" if whole and row["children"] == row["conforming_children"] else "NONCONFORMING"
    return {
        "camp": str(camp), "attempt": checks, "attempt_status": "CONFORMING" if whole else "NONCONFORMING",
        "quiet_period_conforming": bool(quiet) and all(q.get("conforming") is True and not q.get("reasons") for q in quiet),
        "children": len(children), "cells": len(out),
        "cells_conforming": sum(r["status"] == "CONFORMING" for r in out),
        "by_experiment": {e: {"cells": sum(r["experiment"] == e for r in out),
                              "conforming": sum(r["experiment"] == e and r["status"] == "CONFORMING" for r in out),
                              "children": sum(r["children"] for r in out if r["experiment"] == e)}
                          for e in ri.EXPERIMENTS},
        "rows": out,
    }


def markdown(rep: Dict[str, Any]) -> str:
    a = rep["attempt"]
    lines = [f"Per-cell conformance: {rep['cells_conforming']} of {rep['cells']} cells CONFORMING "
             f"({rep['children']} gated children). Attempt: {rep['attempt_status']}.", "",
             f"- `logs/CONFORMANCE.txt`: {a['conformance_line']}",
             f"- End checks: gated {a['gated']} = collected {a['collected']}; reasons {a['end_check_reasons']}; "
             f"gate stop: {a['gate_stop']}; quiet period conforming: {rep['quiet_period_conforming']}.", "",
             "| Experiment | Cells | CONFORMING | Gated children |", "|---|---|---|---|"]
    for e, v in rep["by_experiment"].items():
        lines.append(f"| {e} | {v['cells']} | {v['conforming']} | {v['children']} |")
    bad = [r for r in rep["rows"] if r["status"] != "CONFORMING"]
    if bad:
        lines += ["", "| Experiment | Cell | Conforming children | Reasons |", "|---|---|---|---|"]
        for r in bad:
            lines.append(f"| {r['experiment']} | `{r['cell']}` | {r['conforming_children']} / {r['children']} | {r['reasons'][:3]} |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("camp", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    rep = report(args.camp)
    args.out.write_text(json.dumps(rep, indent=1) + "\n")
    if args.markdown:
        args.markdown.write_text(markdown(rep))
    print(f"{rep['cells_conforming']} of {rep['cells']} cells CONFORMING; attempt {rep['attempt_status']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
