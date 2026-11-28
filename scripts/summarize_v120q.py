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
                       [--q-k4 QK4.json] [--status STATUS.json]
                       --out SUMMARY.json [--markdown SUMMARY.md]

Attempt 2 (plan section 13; the matrix's ``attempt``): V1 cells carry the matrix's deciding
and descriptive roles; ``--q`` is the default-mode cell ``Q`` and ``--q-k4`` the cell
``Q-K4``, each with its matrix ``q_rule`` (deciding, reported, cost); the Q3 statement comes
from ``Q-K4``, with the default-mode Q3 reported next to it. ``--status`` (run_cf5.py's
``status.json``) names delegated cells in ``TOOL_ERROR`` (their evaluation failed after the
measurement): listed as missing evidence from a tool error, never as a failed criterion.

Attempt 3 (plan section 14): every V1 cell is deciding; ``--cf5`` also carries K3, K4, M1 and
M2, and M1's absolute rules (retained scratch per thread at most 256 KiB, no allocation per
short query) are items of their own; Q and Q-K4 as in attempt 2, plus the joint table of
section 14.8 (Q3 shares next to Q5 throughput and p99 ratios, per mode, with attempt 2's
values for 977e54d in their own column); and the four items of section 14.9 with their
class on 24c2602 next to their class on 977e54d.
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
        for name, rule in sorted((cell.get("absolute") or {}).items()):
            # Attempt 3, M1: absolute rules on the candidate, items of their own. A FAIL is
            # final even in an incomplete cell.
            if rule["class"] == "FAIL" or cell.get("state") in (None, "COMPLETE"):
                items.append({"block": cell.get("block"), "item": f"{cell_id}/{name}",
                              "outcome": rule["class"], "worst": rule.get("worst"),
                              "max": rule.get("max")})
        if cell.get("state") not in (None, "COMPLETE"):
            items.append({"block": cell.get("block"), "item": cell_id, "outcome": cell["state"]})
            continue
        for name, metric in sorted((cell.get("metrics") or {}).items()):
            if isinstance(metric, dict) and "class" in metric:
                items.append({"block": cell.get("block"), "item": f"{cell_id}/{name}",
                              "outcome": metric["class"],
                              "interval_log": metric.get("interval_log")})
    return items


def v1_items(analysis: Dict[str, Any], sets: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cells = analysis["cells"]
    cells = cells if isinstance(cells, list) else list(cells.values())
    items = []
    for c in cells:
        item = {"block": "V1", "item": c["cell_id"], "outcome": c["status"],
                "primary_interval_pct": c.get("primary_interval_pct")}
        if sets is not None:
            item["role"] = "deciding" if c["cell_id"] in sets["deciding"] else "descriptive"
        items.append(item)
    if sets is not None:
        absent = sorted(set(sets["deciding"]) - {c["cell_id"] for c in cells})
        if absent:
            raise SystemExit(f"V1 analysis lacks deciding cells {absent}")
    return items


def q_items(cell: str, evaluation: Dict[str, Any], rule: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """One item per criterion. With a rule (attempt 2), each criterion is ``deciding``,
    ``reported`` (measured, not deciding in this mode) or ``cost`` (published operational
    cost of the option); a missing status is a criterion without its observations."""
    items = []
    for name in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        status = evaluation["criteria"][name].get("status")
        item = {"block": "Q", "item": name if rule is None else f"{cell}/{name}",
                "outcome": status if status is not None else "NO_VERDICT"}
        if rule is not None:
            item["role"] = ("deciding" if name in rule["deciding"]
                            else "cost" if name in rule["cost"] else "reported")
        items.append(item)
    return items


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


#: Plan section 14.9: the four deciding items without a verdict on 977e54d (attempt 2), with
#: the metric that set each class there. Their classes stay with 977e54d.
OPEN_ITEMS_A2 = [
    {"item": "B4-http-metrics-ops-compact-bfs-sparse-10000", "block": "B4",
     "class_977e54d": "INCONCLUSIVE", "cause_977e54d": "window time [+1.58, +7.08] %, tolerance 6 %"},
    {"item": "http_lifecycle_compact_bfs_small", "block": "V1",
     "class_977e54d": "INCONCLUSIVE_DISCLOSED",
     "cause_977e54d": "primary time_to_ready_ms [-20.2, +23.6] %, tolerance 10 %"},
    {"item": "http_standalone_batch_b1_compact_bfs", "block": "V1",
     "class_977e54d": "UNRESOLVED",
     "cause_977e54d": "supporting request_latency_p99_ns [-42.1, +78.3] %, tolerance 25 %"},
    {"item": "http_standalone_batch_b256_compact_bfs", "block": "V1",
     "class_977e54d": "UNRESOLVED",
     "cause_977e54d": "supporting sampled_max_rss_bytes [-0.23, +22.47] %, tolerance 20 %"},
]
#: Attempt 2's Q values for 977e54d (attempt2/REPORT.md), shown in their own column.
Q_JOINT_A2 = {"Q": {"q3": [0.219, 0.116], "q5_rps": [1.072, 1.013], "q5_p99": [1.035, 1.031]},
              "Q-K4": {"q3": [0.555, 0.549], "q5_rps": [0.851, 0.880], "q5_p99": [0.294, 0.292]}}


def q_joint(cell: str, evaluation: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Plan section 14.8: the feeder's recovery (Q3 shares) next to the query cost (Q5
    throughput and p99 ratios against v1.1.0), for one mode."""
    row: Dict[str, Any] = {"cell": cell, "977e54d": Q_JOINT_A2[cell]}
    if evaluation is None:
        row["24c2602"] = None
        return row
    q3 = evaluation["criteria"]["Q3"]
    q5 = evaluation["criteria"]["Q5"].get("cells") or {}
    def ratios(key: str) -> List[Optional[float]]:
        return [q5.get(f"L1 G100k C={c}", {}).get(key) for c in (16, 64)]
    row["24c2602"] = {"q3": [q3.get("ratio_c16"), q3.get("ratio_c64")],
                      "q3_status": q3.get("status"),
                      "q5_rps": ratios("rps_ratio"), "q5_p99": ratios("p99_ratio"),
                      "q5_status": evaluation["criteria"]["Q5"].get("status")}
    return row


def summarize(matrix: Dict[str, Any], cf5: Optional[Dict[str, Any]], v1: Optional[Dict[str, Any]],
              q: Optional[Dict[str, Any]], b4: Optional[Dict[str, Any]],
              q_k4: Optional[Dict[str, Any]] = None,
              status: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    by_id = {c["id"]: c for c in matrix["cells"]}
    sets = by_id["B4"]["b4"]
    attempt = matrix.get("attempt", 1)
    attempt2 = attempt in (2, 3)
    items: List[Dict[str, Any]] = []
    missing: List[str] = []
    tool_errors = sorted(cid for cid, s in ((status or {}).get("cells") or {}).items()
                         if s.get("state") == "TOOL_ERROR")
    paired_blocks = {1: "V2, K1, K2", 2: "V2", 3: "V2, K1, K2, K3, K4, M1, M2"}[attempt]
    if cf5 is not None:
        items += cf5_items(cf5)
    else:
        missing.append(f"{paired_blocks} (analyze_cf5.py output)")
    if v1 is not None:
        items += v1_items(v1, by_id["V1"].get("v1"))
    else:
        missing.append("V1 (analyze_v100q_a.py output)")
    if b4 is not None:
        items += b4_items(b4, sets)
    else:
        missing.append("B4 (analyze_lifecycle_qualification.py output)")
    q_summary = None
    q_cells = (("Q", q), ("Q-K4", q_k4)) if attempt2 else (("Q", q),)
    for cell, evaluation in q_cells:
        if evaluation is not None:
            items += q_items(cell, evaluation, by_id[cell].get("q_rule") if attempt2 else None)
        elif cell in tool_errors:
            missing.append(f"{cell} (tool error: the evaluation failed after the measurement; "
                           "no verdict, not a failed criterion)")
        else:
            missing.append(f"{cell} (evaluate_v100q_q.py output)")
    if q is not None:
        q_summary = {name: q["criteria"][name].get("status") for name in ("Q1", "Q2", "Q3", "Q4", "Q5")}
    q3_source = q_k4 if attempt2 else q
    deciding = [i for i in items if i.get("role", "deciding") == "deciding"]
    by_outcome: Dict[str, List[str]] = {}
    for item in deciding:
        by_outcome.setdefault(str(item["outcome"]), []).append(item["item"])
    atomic = next((i for i in items if i["item"] == sets["atomic"][0]), None)
    extra: Dict[str, Any] = {}
    if attempt == 3:
        extra["q_joint"] = [q_joint("Q", q), q_joint("Q-K4", q_k4)]
        found = {i["item"]: i for i in items}
        extra["open_items"] = [dict(o, outcome_24c2602=(found[o["item"]]["outcome"]
                                                        if o["item"] in found else "MISSING"))
                               for o in OPEN_ITEMS_A2]
    return {
        **extra,
        "schema": {1: "v120q-summary-1", 2: "v120q-summary-2", 3: "v120q-summary-3"}[attempt],
        "plan": matrix.get("plan"),
        "reference": matrix.get("reference"),
        "deciding_by_outcome": dict(sorted(by_outcome.items())),
        "not_passing_deciding": sorted(i["item"] for i in deciding
                                       if str(i["outcome"]) not in PASSING),
        "ops_atomic": atomic,
        "q": q_summary,
        "q_k4": ({name: q_k4["criteria"][name].get("status") for name in ("Q1", "Q2", "Q3", "Q4", "Q5")}
                 if q_k4 is not None else None),
        "q3": q_statement(q3_source) if q3_source is not None else None,
        "q3_mode": by_id["Q-K4"]["q_rule"]["mode"] if attempt2 else "default",
        "q3_default_mode": q_statement(q) if attempt2 and q is not None else None,
        "q_run_status": q.get("run_status") if q is not None else None,
        "q_k4_run_status": q_k4.get("run_status") if q_k4 is not None else None,
        "tool_errors": tool_errors,
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
    if q3 and q3.get("c16_share") is not None and q3.get("c64_share") is not None:
        lines += ["", "## Q3 (feeder catch-up under query load)", "",
                  f"Mode: {summary.get('q3_mode', 'default')}.", "",
                  f"**{q3['status']}**. C=16 share {q3['c16_share']:.1%} against "
                  f"{q3['c16_threshold']:.0%} ({'pass' if q3['c16_pass'] else 'fail'}); "
                  f"C=64 share {q3['c64_share']:.1%} against {q3['c64_threshold']:.0%} "
                  f"({'pass' if q3['c64_pass'] else 'fail'}).", "",
                  f"Next step: {q3['next_step']}."]
        default = summary.get("q3_default_mode")
        if default and default.get("c16_share") is not None:
            lines += ["", f"Default mode (reported, not deciding): **{default['status']}**, C=16 "
                      f"{default['c16_share']:.1%}, C=64 {default['c64_share']:.1%}."]
    reported = [i for i in summary["items"] if i.get("role") in ("reported", "cost", "descriptive")
                and i["block"] in ("Q", "V1")]
    if reported:
        lines += ["", "## Reported, cost and descriptive items (not deciding)", "",
                  "| Item | Role | Outcome |", "|---|---|---|"]
        lines += [f"| `{i['item']}` | {i['role']} | {i['outcome']} |" for i in reported]
    joint = summary.get("q_joint")
    if joint:
        def pair(values: Optional[List[Optional[float]]], pct: bool) -> str:
            if not values or any(v is None for v in values):
                return "—"
            return " / ".join(f"{v:.1%}" if pct else f"{v:.3f}" for v in values)
        lines += ["", "## Feeder recovery and query cost (plan section 14.8)", "",
                  "| Mode | Candidate | Q3 share C=16 / C=64 | Q5 throughput ratio C=16 / C=64 "
                  "| Q5 p99 ratio C=16 / C=64 |", "|---|---|---|---|---|"]
        for row in joint:
            for cand in ("24c2602", "977e54d"):
                v = row.get(cand) or {}
                lines.append(f"| {row['cell']} | {cand} | {pair(v.get('q3'), True)} | "
                             f"{pair(v.get('q5_rps'), False)} | {pair(v.get('q5_p99'), False)} |")
    open_items = summary.get("open_items")
    if open_items:
        lines += ["", "## Items without a verdict on 977e54d (plan section 14.9)", "",
                  "| Item | 977e54d | Cause on 977e54d | 24c2602 |", "|---|---|---|---|"]
        lines += [f"| `{o['item']}` | {o['class_977e54d']} | {o['cause_977e54d']} | "
                  f"{o['outcome_24c2602']} |" for o in open_items]
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
    parser.add_argument("--q-k4", type=Path, dest="q_k4")
    parser.add_argument("--status", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args(argv)
    summary = summarize(load(args.matrix, "--matrix"), load(args.cf5, "--cf5"),
                        load(args.v1, "--v1"), load(args.q, "--q"), load(args.b4, "--b4"),
                        load(args.q_k4, "--q-k4"), load(args.status, "--status"))
    out = confined(args.out, "--out")
    out.write_text(json.dumps(summary, indent=1, sort_keys=True) + "\n")
    if args.markdown:
        confined(args.markdown, "--markdown").write_text(markdown(summary))
    print(json.dumps({k: summary[k] for k in ("deciding_by_outcome", "q3", "missing_evidence")},
                     indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
