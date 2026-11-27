#!/usr/bin/env python3
"""Release-level summary of the v1.2.0 release qualification (knotrel#182).

Plan: knotrel ``docs/releases/v1.2.0-qualification-plan.md``, sections 4 and 6. Reads the
outputs of the block analyzers, each run once after the session (commands in the campaign's
``ANALYSIS-COMMANDS.txt``), and changes no class:

- ``--cf5``: ``analyze_cf5.py`` on the session (V2, K1, K2: regression checks, PASS /
  REGRESSION / INCONCLUSIVE / TIMER_LIMITED, or INCOMPLETE / NOT_RUN);
- ``--v1``: ``analyze_v100q_a.py`` (the frozen v1.0.0 A rules; ``status`` per cell);
- ``--q``: ``evaluate_v100q_q.py`` (Q1-Q5);
- ``--b4``: ``analyze_lifecycle_qualification.py --expect-only B4`` (``timing`` statuses),
  with the deciding, descriptive and unqualified sets the matrix's B4 cell records.

Output: every item listed by outcome, never merged (plan section 6.4), the B4 deciding
outcomes, the ``ops-atomic`` outcome and the Q3 statement of plan section 6.3, which names
the #87 B2 decision as the next step when Q3 is FAIL. A block whose input is missing is
listed as missing evidence, never as a result.

    summarize_v120q.py --matrix M [--cf5 A.json] [--v1 V1.json] [--q Q.json] [--b4 B4.json]
                       --out SUMMARY.json [--markdown SUMMARY.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cli_paths import confined  # noqa: E402

PASSING = {"PASS"}
B2_STEP = ("#87 step B2: bounded concurrent query execution, designed and measured as an "
           "impact estimate against Q1-Q5 with unchanged thresholds (plan section 6.3)")


def load(path: Optional[Path], what: str) -> Optional[Any]:
    return json.loads(confined(path, what).read_text()) if path else None


def cf5_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = []
    for cell_id, cell in sorted(analysis["cells"].items()):
        if cell.get("state") not in (None, "COMPLETE"):
            items.append({"block": cell.get("block"), "item": cell_id, "outcome": cell["state"]})
            continue
        for name, metric in sorted((cell.get("metrics") or {}).items()):
            if isinstance(metric, dict) and "class" in metric:
                items.append({"block": cell.get("block"), "item": f"{cell_id}/{name}",
                              "outcome": metric["class"],
                              "interval_log": metric.get("interval_log")})
    return items


def v1_items(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    cells = analysis["cells"]
    cells = cells if isinstance(cells, list) else list(cells.values())
    return [{"block": "V1", "item": c["cell_id"], "outcome": c["status"],
             "primary_interval_pct": c.get("primary_interval_pct")} for c in cells]


def b4_items(analysis: Dict[str, Any], sets: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    by_id = {r["id"]: r for r in analysis["timing"] if r["id"].startswith("B4-")}
    missing = sorted(set(sets["all"]) - set(by_id))
    items = []
    for cell_id in sets["all"]:
        role = ("deciding" if cell_id in sets["deciding"]
                else "unqualified" if cell_id in sets["unqualified"] else "descriptive")
        record = by_id.get(cell_id)
        outcome = record["status"] if record else "MISSING"
        if role == "unqualified":
            outcome = f"no verdict (measured: {outcome})"
        items.append({"block": "B4", "item": cell_id, "role": role, "outcome": outcome,
                      "interval_pct": record.get("interval_pct") if record else None,
                      **({"atomicity_mode": record["atomicity_mode"]}
                         if record and "atomicity_mode" in record else {})})
    if missing:
        raise SystemExit(f"B4 analysis lacks cells {missing[:3]}")
    return items


def q_statement(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    q3 = evaluation["criteria"]["Q3"]
    status = q3.get("status")
    statement = {
        "status": status,
        "c16_share": q3.get("ratio_c16"), "c16_threshold": 0.50,
        "c16_pass": None if q3.get("ratio_c16") is None else q3["ratio_c16"] >= 0.50,
        "c64_share": q3.get("ratio_c64"), "c64_threshold": 0.25,
        "c64_pass": None if q3.get("ratio_c64") is None else q3["ratio_c64"] >= 0.25,
        "rule": q3.get("rule"),
    }
    if status == "PASS":
        statement["next_step"] = "#87 can close with the #180 ledger row (plan section 6.3)"
    elif status == "FAIL":
        statement["next_step"] = B2_STEP
    else:
        statement["next_step"] = "no verdict: missing evidence (plan section 6.3)"
    return statement


def summarize(matrix: Dict[str, Any], cf5: Optional[Dict[str, Any]], v1: Optional[Dict[str, Any]],
              q: Optional[Dict[str, Any]], b4: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    sets = next(c for c in matrix["cells"] if c["id"] == "B4")["b4"]
    items: List[Dict[str, Any]] = []
    missing: List[str] = []
    if cf5 is not None:
        items += cf5_items(cf5)
    else:
        missing.append("V2, K1, K2 (analyze_cf5.py output)")
    if v1 is not None:
        items += v1_items(v1)
    else:
        missing.append("V1 (analyze_v100q_a.py output)")
    if b4 is not None:
        items += b4_items(b4, sets)
    else:
        missing.append("B4 (analyze_lifecycle_qualification.py output)")
    q_summary = None
    if q is not None:
        q_summary = {name: q["criteria"][name].get("status") for name in ("Q1", "Q2", "Q3", "Q4", "Q5")}
        items += [{"block": "Q", "item": name, "outcome": status} for name, status in q_summary.items()]
    else:
        missing.append("Q (evaluate_v100q_q.py output)")
    deciding = [i for i in items if i.get("role", "deciding") == "deciding"]
    by_outcome: Dict[str, List[str]] = {}
    for item in deciding:
        by_outcome.setdefault(str(item["outcome"]), []).append(item["item"])
    atomic = next((i for i in items if i["item"] == sets["atomic"][0]), None)
    return {
        "schema": "v120q-summary-1",
        "plan": matrix.get("plan"),
        "reference": matrix.get("reference"),
        "deciding_by_outcome": dict(sorted(by_outcome.items())),
        "not_passing_deciding": sorted(i["item"] for i in deciding
                                       if str(i["outcome"]) not in PASSING),
        "ops_atomic": atomic,
        "q": q_summary,
        "q3": q_statement(q) if q is not None else None,
        "q_run_status": q.get("run_status") if q is not None else None,
        "missing_evidence": missing,
        "items": items,
    }


def markdown(summary: Dict[str, Any]) -> str:
    lines = ["# v1.2.0 release qualification: summary", "",
             f"Reference: {summary['reference']}. Plan: {summary['plan']}.", "",
             "## Deciding items by outcome", "", "| Outcome | Count | Items |", "|---|---|---|"]
    for outcome, names in summary["deciding_by_outcome"].items():
        shown = ", ".join(f"`{n}`" for n in names) if outcome not in PASSING else "—"
        lines.append(f"| {outcome} | {len(names)} | {shown} |")
    q3 = summary.get("q3")
    if q3:
        lines += ["", "## Q3 (feeder catch-up under query load)", "",
                  f"**{q3['status']}**. C=16 share {q3['c16_share']:.1%} against "
                  f"{q3['c16_threshold']:.0%} ({'pass' if q3['c16_pass'] else 'fail'}); "
                  f"C=64 share {q3['c64_share']:.1%} against {q3['c64_threshold']:.0%} "
                  f"({'pass' if q3['c64_pass'] else 'fail'}).", "",
                  f"Next step: {q3['next_step']}."]
    atomic = summary.get("ops_atomic")
    if atomic:
        lines += ["", "## `ops-atomic` (hub 10k, deciding)", "",
                  f"`{atomic['item']}`: **{atomic['outcome']}**, interval "
                  f"{atomic.get('interval_pct')} %."]
    if summary["missing_evidence"]:
        lines += ["", "## Missing evidence", ""] + [f"- {m}" for m in summary["missing_evidence"]]
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--cf5", type=Path)
    parser.add_argument("--v1", type=Path)
    parser.add_argument("--q", type=Path)
    parser.add_argument("--b4", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    summary = summarize(load(args.matrix, "--matrix"), load(args.cf5, "--cf5"),
                        load(args.v1, "--v1"), load(args.q, "--q"), load(args.b4, "--b4"))
    out = confined(args.out, "--out")
    out.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    if args.markdown:
        confined(args.markdown, "--markdown").write_text(markdown(summary))
    print(json.dumps({k: summary[k] for k in ("deciding_by_outcome", "q3", "missing_evidence")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
