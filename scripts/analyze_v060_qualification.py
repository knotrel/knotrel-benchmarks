#!/usr/bin/env python3
"""Analysis of the knotrel v0.6.0 experiments R, Rmem, M_desc and M_reg.

Reads a collector output directory (``run_v060_qualification.py``) and the
frozen matrix, validates identities, and writes ``analysis.json`` and
``analysis.md`` into that directory. Interval and classification come from
``analyze_bc_qualification.summarize_metric`` unchanged.

    analyze_v060_qualification.py r|rmem|mdesc|mreg DIR
        --ref-rev SHA --cand-rev SHA   (r, rmem: build records must match, clean)
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_bc_qualification import TOLERANCES, summarize_metric  # noqa: E402
from cli_paths import confined_directory, contained_file  # noqa: E402

MATRIX = Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "MATRIX.json"
NAME = re.compile(r"^\d{5}-(?P<cell>.+)-(?P<phase>warmup|analyzed)-(?P<index>\d{2})-(?P<arm>ref|cand)$")
MEMORY_TOLERANCE = 0.20


class AnalysisError(Exception):
    """A run that cannot be analyzed (missing, failed or mismatched records)."""


def json_lines(text: str) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip().startswith("{")]


def load_children(directory: Path) -> List[Dict[str, Any]]:
    log = json.loads(contained_file(directory, "run-log.json", "run log").read_text())
    if log.get("stopped") or not log.get("finished"):
        raise AnalysisError(f"run incomplete or stopped: {log.get('stopped')}")
    if log["meta"].get("pilot"):
        raise AnalysisError("pilot runs are never analyzed for decisions")
    children = []
    for child in log["children"]:
        if child["exit"] != 0:
            raise AnalysisError(f"{child['name']} exited {child['exit']}")
        stdout = contained_file(directory / "raw", f"{child['name']}.stdout", "child output").read_text()
        children.append({**child, "records": json_lines(stdout)})
    return children


def check_build(records: List[Dict[str, Any]], expected_rev: str, label: str) -> None:
    build = next((r for r in records if r.get("kind") == "build"), None)
    if build is None:
        raise AnalysisError(f"{label}: no build record")
    if not build["knotrel_rev"].startswith(expected_rev) or build["knotrel_dirty"]:
        raise AnalysisError(f"{label}: built from {build['knotrel_rev']} dirty={build['knotrel_dirty']}, "
                            f"expected {expected_rev} clean")


def verdict_with_improvement(summary: Dict[str, Any]) -> str:
    """The summary's status, plus IMPROVED when the whole interval is below zero."""
    if summary["status"] == "PASS" and summary["interval_log"][1] < 0:
        return "PASS (IMPROVED)"
    return summary["status"]


def analyze_r(directory: Path, matrix: Dict[str, Any], ref_rev: str, cand_rev: str) -> Dict[str, Any]:
    spec = matrix["experiments"]["R"]
    cells = {c["id"]: c for c in spec["cells"]}
    pairs: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for child in load_children(directory):
        match = NAME.match(child["name"])
        if not match:
            raise AnalysisError(f"unexpected child name {child['name']}")
        arm = match["arm"]
        check_build(child["records"], ref_rev if arm == "ref" else cand_rev, child["name"])
        if match["phase"] != "analyzed":
            continue
        cell = cells[match["cell"]]
        result = next(r for r in child["records"] if r.get("kind") == cell["command"])
        pairs[match["cell"]][int(match["index"])][arm] = result
    out = {}
    for cell_id, cell in cells.items():
        complete = [p for _, p in sorted(pairs[cell_id].items()) if "ref" in p and "cand" in p]
        if len(complete) != spec["pairs"]:
            raise AnalysisError(f"{cell_id}: {len(complete)} complete pairs, expected {spec['pairs']}")
        # Both arms must do the same logical work.
        for pair in complete:
            for key in ("counts", "operations", "nodes"):
                if key in pair["ref"] and pair["ref"][key] != pair["cand"][key]:
                    raise AnalysisError(f"{cell_id}: {key} differ between arms")
        values = [{"B": p["ref"]["observation_ns"], "C": p["cand"]["observation_ns"]} for p in complete]
        summary = summarize_metric("observation_ns", values, TOLERANCES[cell["tolerance"]])
        extra = {}
        if cell["command"] == "churn":
            extra = {"slowest_op_ns_median": {arm: sorted(p[arm]["slowest_op_ns"] for p in complete)[len(complete) // 2]
                                              for arm in ("ref", "cand")},
                     "compactions": {arm: complete[0][arm]["compactions"] for arm in ("ref", "cand")}}
        out[cell_id] = {**summary, "verdict": verdict_with_improvement(summary), **extra}
    return out


def churn_memory(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    base = next(r for r in records if r.get("kind") == "baseline")
    checkpoints = [r for r in records if r.get("kind") == "checkpoint"]
    if not all(c["logical"] == c["expected"] for c in checkpoints):
        raise AnalysisError("churn logical counts differ from the model")
    net = [c["net_live_heap_bytes"] for c in checkpoints]
    return {"max_net_live": max(net), "first_net_live": net[0], "last_net_live": net[-1],
            "max_net_peak": max(c["peak_heap_bytes"] for c in checkpoints) - base["live_heap_bytes"],
            "engine_vertices_max": max(c["engine_vertices"] for c in checkpoints),
            "compactions": sum(1 for c in checkpoints if c["compacted_in_cycle"])}


def analyze_rmem(directory: Path, matrix: Dict[str, Any], ref_rev: str, cand_rev: str) -> Dict[str, Any]:
    spec = matrix["experiments"]["Rmem"]
    by_name = {c["name"].split("-", 1)[1]: c for c in load_children(directory)}
    out = {}
    for cell in spec["cells"]:
        arms = {}
        for arm, rev in (("ref", ref_rev), ("cand", cand_rev)):
            child = by_name.get(f"{cell['id']}-{arm}")
            if child is None:
                raise AnalysisError(f"{cell['id']}-{arm} missing")
            check_build(child["records"], rev, child["name"])
            if cell["args"][0] == "churn":
                arms[arm] = churn_memory(child["records"])
            else:
                arms[arm] = child["records"][-1]
        metrics = {}
        for metric in cell["metrics"]:
            ref, cand = arms["ref"][metric], arms["cand"][metric]
            change = (cand / ref - 1.0) * 100.0 if ref else math.inf
            metrics[metric] = {"ref": ref, "cand": cand, "change_pct": change,
                               "verdict": "REGRESSION" if cand > ref * (1 + MEMORY_TOLERANCE) else "PASS"}
        out[cell["id"]] = {"metrics": metrics, "ref": arms["ref"], "cand": arms["cand"]}
    return out


def phase(record: Dict[str, Any], series: str) -> Dict[str, Any]:
    return record["server_phases"].get(series, {})


def analyze_mdesc(directory: Path, matrix: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for child in load_children(directory):
        for record in child["records"]:
            if record.get("kind") != "config":
                continue
            kind = 'kind="batch"'
            lock = phase(record, f"knotrel_graph_lock_wait_seconds{{{kind}}}")
            execution = phase(record, f"knotrel_graph_job_execution_seconds{{{kind}}}")
            queue = phase(record, f"knotrel_graph_job_queue_seconds{{{kind}}}")
            latency = record["latency_ns"]
            mean_latency_s = latency["mean"] / 1e9 if latency["mean"] else None
            rows.append({
                "server": child["name"].split("-", 1)[1], "config": record["config"]["id"],
                "mix": record["config"]["mix"], "batch": record["config"]["batch"],
                "clients": record["config"]["clients"], "background": record["config"]["background"],
                "open_rate": record["config"]["open_rate"],
                "requests_per_s": record["requests_per_s"], "operations_per_s": record["operations_per_s"],
                "p50_ns": latency["p50"], "p99_ns": latency["p99"], "p999_ns": latency["p999"], "max_ns": latency["max"],
                "statuses": record["statuses"], "errors": record["errors"],
                "jain": record["fairness"]["jain"], "min_over_max": record["fairness"]["min_over_max"],
                "outstanding_median": record["outstanding_jobs"]["median"],
                "lock_wait_mean_s": lock.get("mean_s"), "execution_mean_s": execution.get("mean_s"),
                "queue_mean_s": queue.get("mean_s"),
                "lock_share_of_latency": (lock["mean_s"] / mean_latency_s) if lock and mean_latency_s else None,
                "background_summary": record["background"], "server_rss_kib": record["server_rss_kib"],
            })
    # Predeclared M5 rule (design section 6), part (i).
    saturated_reads = [r for r in rows if r["mix"] in ("read95", "read100") and r["clients"] >= 16
                       and r["open_rate"] is None and r["background"] == "none"]
    triggered = [r for r in saturated_reads if (r["lock_share_of_latency"] or 0) >= 0.5]
    return {"rows": rows, "m5_rule_i": {"evaluated": len(saturated_reads), "lock_share_at_least_half": len(triggered),
                                        "configs": [f"{r['server']}/{r['config']}" for r in triggered]}}


def analyze_mreg(directory: Path, matrix: Dict[str, Any]) -> Dict[str, Any]:
    spec = matrix["experiments"]["M_reg"]
    cells = {c["id"]: c for c in spec["cells"]}
    pairs: Dict[str, Dict[int, Dict[str, Dict[str, Any]]]] = defaultdict(lambda: defaultdict(dict))
    for child in load_children(directory):
        match = NAME.match(child["name"])
        if not match:
            raise AnalysisError(f"unexpected child name {child['name']}")
        if match["phase"] != "analyzed":
            continue
        record = next(r for r in child["records"] if r.get("kind") == "config")
        if record["errors"] or set(record["statuses"]) - {"200"}:
            raise AnalysisError(f"{child['name']}: errors {record['errors']} statuses {record['statuses']}")
        pairs[match["cell"]][int(match["index"])][match["arm"]] = record
    out = {}
    for cell_id, cell in cells.items():
        complete = [p for _, p in sorted(pairs[cell_id].items()) if "ref" in p and "cand" in p]
        if len(complete) != spec["pairs"]:
            raise AnalysisError(f"{cell_id}: {len(complete)} complete pairs, expected {spec['pairs']}")
        metrics = {}
        for name, rule in cell["metrics"].items():
            def get(record: Dict[str, Any]) -> float:
                value: Any = record
                for part in name.split("."):
                    value = value[part]
                return float(value)
            if rule["direction"] == "higher_is_better":
                values = [{"B": get(p["cand"]), "C": get(p["ref"])} for p in complete]
            else:
                values = [{"B": get(p["ref"]), "C": get(p["cand"])} for p in complete]
            summary = summarize_metric(name, values, TOLERANCES[rule["tolerance"]])
            summary["direction"] = rule["direction"]
            summary["verdict"] = verdict_with_improvement(summary)
            metrics[name] = summary
        statuses = [m["status"] for m in metrics.values()]
        cell_verdict = "REGRESSION" if "REGRESSION" in statuses else ("INCONCLUSIVE" if "INCONCLUSIVE" in statuses else "PASS")
        out[cell_id] = {"verdict": cell_verdict, "metrics": metrics}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=["r", "rmem", "mdesc", "mreg"])
    parser.add_argument("directory", type=Path)
    parser.add_argument("--ref-rev")
    parser.add_argument("--cand-rev")
    args = parser.parse_args()
    directory = confined_directory(args.directory, "directory")
    matrix = json.loads(MATRIX.read_text())
    try:
        if args.experiment == "r":
            result = analyze_r(directory, matrix, args.ref_rev, args.cand_rev)
        elif args.experiment == "rmem":
            result = analyze_rmem(directory, matrix, args.ref_rev, args.cand_rev)
        elif args.experiment == "mdesc":
            result = analyze_mdesc(directory, matrix)
        else:
            result = analyze_mreg(directory, matrix)
    except (AnalysisError, KeyError, StopIteration, ValueError) as error:
        print(f"analysis rejected: {error!r}", file=sys.stderr)
        return 2
    (directory / "analysis.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
