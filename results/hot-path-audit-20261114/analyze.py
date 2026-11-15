#!/usr/bin/env python3
"""Regenerates every table of the hot-path audit campaign from raw artifacts.

Reads `run/observations.jsonl`, verifies the sha256 of every archived child
stream, re-parses the raw stdout of each observation and writes:

- `analysis/observations.csv`: one normalized row per metric value;
- `analysis/summary.json`: per-cell statistics, paired deltas and verdicts;
- `REPORT.md`: the campaign report (identities, verification, correctness,
  allocation counts, confirmed improvements, regressions, inconclusive
  measurements, mechanism microbenchmarks, end-to-end HTTP);
- `manifest.json`: every artifact in the campaign directory with its size,
  sha256 and description.

Outputs are deterministic: the bootstrap uses a fixed seed and nothing
depends on the time of analysis. `--check` regenerates into a temporary copy
and fails if any committed output differs.

Statistics. Each measured process yields one value per metric (the median
of its repetitions where a process repeats internally; the fastest
repetition is never selected). For every round, the candidate and A/A arms
are compared with the baseline of the same round:
`100 * (arm / base - 1)`, positive meaning slower. The paired median and a
95% percentile-bootstrap interval of the median (10,000 resamples, seed
20261115) summarize those changes. The A/A noise bound is the larger
magnitude of the A/A interval's endpoints. A timing change is **confirmed**
only if its interval excludes zero and its median magnitude exceeds the A/A
bound; it is a confirmed improvement when negative and a confirmed
regression when positive. Everything else is **inconclusive**. With many
cells, some intervals will exclude zero by chance; the A/A bound guards
against, but does not eliminate, false discoveries.

Usage: python3 analyze.py [--check]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import random
import re
import shutil
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

HERE = Path(__file__).resolve().parent
BOOTSTRAP_SEED = 20261115
BOOTSTRAP_RESAMPLES = 10_000
OUTPUTS = ("analysis/observations.csv", "analysis/summary.json", "REPORT.md", "manifest.json")

# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------


def quartiles(values: Sequence[float]) -> Tuple[float, float, float]:
    """Q1, median, Q3 using the inclusive method (defined for n >= 1)."""
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0], ordered[0], ordered[0]
    q1, q2, q3 = statistics.quantiles(ordered, n=4, method="inclusive")
    return q1, q2, q3


def describe(values: Sequence[float]) -> Dict[str, Any]:
    """Sample count, median, quartiles, IQR, MAD, min and max."""
    q1, median, q3 = quartiles(values)
    mad = statistics.median(abs(v - median) for v in values)
    return {"n": len(values), "median": median, "q1": q1, "q3": q3, "iqr": q3 - q1,
            "mad": mad, "min": min(values), "max": max(values)}


def bootstrap_median_ci(values: Sequence[float], seed: int = BOOTSTRAP_SEED,
                        resamples: int = BOOTSTRAP_RESAMPLES) -> Tuple[float, float]:
    """95% percentile-bootstrap interval of the median."""
    rng = random.Random(seed)
    data = list(values)
    medians = sorted(statistics.median(rng.choices(data, k=len(data))) for _ in range(resamples))
    return medians[int(0.025 * resamples)], medians[int(0.975 * resamples) - 1]


def sign_test_p(changes: Sequence[float]) -> float:
    """Two-sided exact sign test p-value (zeros dropped)."""
    nonzero = [c for c in changes if c != 0]
    n = len(nonzero)
    if n == 0:
        return 1.0
    k = min(sum(c > 0 for c in nonzero), sum(c < 0 for c in nonzero))
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def verdict(change_ci: Tuple[float, float], change_median: float, noise_bound: float) -> str:
    """Confirmed improvement / confirmed regression / inconclusive."""
    low, high = change_ci
    if high < 0 and -change_median > noise_bound:
        return "confirmed improvement"
    if low > 0 and change_median > noise_bound:
        return "confirmed regression"
    return "inconclusive"


def paired_changes(by_round: Dict[int, Dict[str, float]], arm: str, ref: str = "base") -> List[float]:
    """Per-round percent change of `arm` relative to `ref` (positive = larger)."""
    return [100.0 * (values[arm] / values[ref] - 1.0)
            for _, values in sorted(by_round.items()) if arm in values and ref in values]


def compare(by_round: Dict[int, Dict[str, float]]) -> Dict[str, Any]:
    """Paired comparison of candidate and A/A against the baseline."""
    result: Dict[str, Any] = {}
    aa = paired_changes(by_round, "aa")
    aa_ci = bootstrap_median_ci(aa) if aa else (0.0, 0.0)
    noise = max(abs(aa_ci[0]), abs(aa_ci[1]))
    result["aa"] = {"changes_pct": aa, "median_pct": statistics.median(aa) if aa else None,
                    "ci95_pct": list(aa_ci), "noise_bound_pct": noise}
    cand = paired_changes(by_round, "cand")
    if cand:
        ci = bootstrap_median_ci(cand)
        median = statistics.median(cand)
        result["cand"] = {"changes_pct": cand, "median_pct": median, "ci95_pct": list(ci),
                          "sign_test_p": sign_test_p(cand),
                          "verdict": verdict(ci, median, noise)}
    return result


# ---------------------------------------------------------------------------
# Parsing raw artifacts
# ---------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 16):
            digest.update(chunk)
    return digest.hexdigest()


def load_observations(run: Path) -> List[Dict[str, Any]]:
    """Observation records, with archived stream hashes verified."""
    records = [json.loads(line) for line in (run / "observations.jsonl").read_text().splitlines() if line]
    for record in records:
        for stream in ("stdout", "stderr"):
            path = run / record[f"{stream}_path"]
            if sha256_file(path) != record[f"{stream}_sha256"]:
                raise ValueError(f"hash mismatch for {path}")
    return records


def json_lines(text: str) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip().startswith("{")]


def parse_init(stdout: str) -> Dict[str, Any]:
    report = json.loads(stdout)
    reps = report["repetitions"]
    return {
        "metrics": {"total_initialization_ns": statistics.median(r["total_initialization_ns"] for r in reps)},
        "fingerprints": sorted({r["trace_fingerprint_fnv1a64"] for r in reps}),
        "validated": report.get("validated_dynamic_continuation"),
        "repetitions": len(reps),
    }


def parse_dynamic(stdout: str) -> Dict[str, Any]:
    report = json.loads(stdout)
    reps = report["repetitions"]
    metrics = {"workload_wall_ns": statistics.median(r["workload_wall_ns"] for r in reps)}
    counts = {}
    for op in ("link", "cut", "connected"):
        present = [r["measurements"][op] for r in reps if r["measurements"].get(op)]
        if present:
            metrics[f"{op}_total_ns"] = statistics.median(m["total_ns"] for m in present)
            counts[op] = sorted({m["count"] for m in present})
    return {"metrics": metrics, "fingerprints": [report["trace_fingerprint_fnv1a64"]],
            "operation_counts": counts, "repetitions": len(reps)}


def parse_probe_timing(stdout: str) -> Dict[str, Any]:
    metrics = {}
    for record in json_lines(stdout):
        metrics[f"{record['scenario']}_ns_per_request"] = int(record["elapsed_ns"]) / record["requests"]
    return {"metrics": metrics}


def parse_probe_count(stdout: str) -> Dict[str, Dict[str, float]]:
    out = {}
    for record in json_lines(stdout):
        requests = record["requests"]
        out[record["scenario"]] = {
            "allocation_events_per_request": (record["allocations"] + record["reallocations"]) / requests,
            "allocations_per_request": record["allocations"] / requests,
            "reallocations_per_request": record["reallocations"] / requests,
            "bytes_allocated_per_request": record["bytes_allocated"] / requests,
        }
    return out


E2E_COLUMNS = ("import_ms", "catchup_ms", "time_to_ready_ms", "query_qps", "latency_p50_us",
               "latency_p95_us", "oracle_agreement", "final_rss_mib", "sampled_max_rss_mib",
               "restart_recovery_ms")


def parse_e2e(stdout: str) -> Dict[str, Any]:
    rows = [line for line in stdout.splitlines() if line.startswith("| **#1**")]
    if len(rows) != 1:
        raise ValueError("expected exactly one measure_e2e result row")
    cells = re.findall(r"`([^`]*)`", rows[0])
    values = dict(zip(E2E_COLUMNS, cells))
    agreement = re.match(r"(\d+)/(\d+)", values["oracle_agreement"])
    metrics = {key: float(value) for key, value in values.items() if key != "oracle_agreement"}
    return {"metrics": metrics, "oracle": [int(agreement.group(1)), int(agreement.group(2))]}


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


def analyze(campaign: Path) -> Dict[str, Any]:
    run = campaign / "run"
    records = load_observations(run)
    rows: List[Dict[str, Any]] = []
    timed: Dict[Tuple[str, str], Dict[int, Dict[str, float]]] = {}
    fingerprints: Dict[str, Dict[str, set]] = {}
    init_validation: List[Dict[str, Any]] = []
    verify: Dict[Tuple[bool, str], Dict[str, set]] = {}
    counts: Dict[Tuple[bool, str, str], Dict[str, List[float]]] = {}
    micro: Dict[Tuple[str, int], List[List[float]]] = {}
    e2e: Dict[int, Dict[str, Dict[str, float]]] = {}
    e2e_oracle: List[Dict[str, Any]] = []
    peak_rss: Dict[Tuple[str, str], List[float]] = {}

    for record in records:
        stdout = (run / record["stdout_path"]).read_text()
        kind = record.get("kind")
        base_row = {"sequence": record["sequence"], "section": record["section"], "kind": kind,
                    "cell": record.get("cell", ""), "arm": record.get("arm", ""),
                    "session": record.get("session", ""), "round": record.get("round", ""),
                    "position": record.get("position", "")}
        if record["section"] == "timed":
            parsed = {"init": parse_init, "dynamic": parse_dynamic, "probe": parse_probe_timing}[kind](stdout)
            for metric, value in parsed["metrics"].items():
                rows.append({**base_row, "metric": metric, "value": value})
                timed.setdefault((record["cell"], metric), {}).setdefault(record["round"], {})[record["arm"]] = value
            for fingerprint in parsed.get("fingerprints", []):
                fingerprints.setdefault(record["cell"], {}).setdefault(record["arm"], set()).add(fingerprint)
            if record.get("peak_rss_bytes"):
                peak_rss.setdefault((record["cell"], record["arm"]), []).append(record["peak_rss_bytes"])
                rows.append({**base_row, "metric": "process_peak_rss_bytes", "value": record["peak_rss_bytes"]})
        elif kind == "init-validate":
            parsed = parse_init(stdout)
            init_validation.append({"cell": record["cell"], "arm": record["arm"],
                                    "validated": parsed["validated"], "fingerprints": parsed["fingerprints"]})
        elif kind == "router-verify":
            for line in json_lines(stdout):
                verify.setdefault((record["metrics"], line["scenario"]), {}).setdefault(
                    record["arm"], set()).add(line["digest"])
        elif kind == "router-count":
            for scenario, values in parse_probe_count(stdout).items():
                for metric, value in values.items():
                    counts.setdefault((record["metrics"], scenario, metric), {}).setdefault(
                        record["arm"], []).append(value)
                    rows.append({**base_row, "cell": f"probe/count/metrics-{'on' if record['metrics'] else 'off'}",
                                 "metric": f"{scenario}_{metric}", "value": value})
        elif kind == "job-tracking":
            for line in json_lines(stdout):
                micro.setdefault((line["benchmark"], line["threads"]), []).append(line["ns_per_op"])
                for value in line["ns_per_op"]:
                    rows.append({**base_row, "cell": f"micro/{line['benchmark']}/t{line['threads']}",
                                 "metric": "ns_per_op", "value": value})
        elif kind == "e2e-lifecycle-large":
            parsed = parse_e2e(stdout)
            e2e.setdefault(record["round"], {})[record["arm"]] = parsed["metrics"]
            e2e_oracle.append({"round": record["round"], "arm": record["arm"], "oracle": parsed["oracle"]})
            for metric, value in parsed["metrics"].items():
                rows.append({**base_row, "cell": "e2e/lifecycle/large", "metric": metric, "value": value})

    summary: Dict[str, Any] = {"timed": [], "allocation": [], "micro": [], "e2e": [], "correctness": {}}
    for (cell, metric), by_round in sorted(timed.items()):
        arms = sorted({arm for values in by_round.values() for arm in values})
        entry = {"cell": cell, "metric": metric,
                 "arms": {arm: describe([v[arm] for v in by_round.values() if arm in v]) for arm in arms},
                 **compare(by_round)}
        summary["timed"].append(entry)
    for (metrics, scenario, metric), by_arm in sorted(counts.items()):
        summary["allocation"].append({
            "metrics": metrics, "scenario": scenario, "metric": metric,
            "values": {arm: values for arm, values in sorted(by_arm.items())},
            "repeat_spread_pct": {arm: 100.0 * (max(values) - min(values)) / statistics.median(values)
                                  if statistics.median(values) else 0.0
                                  for arm, values in sorted(by_arm.items())},
        })
    for (benchmark, threads), runs in sorted(micro.items()):
        summary["micro"].append({"benchmark": benchmark, "threads": threads,
                                 "runs": [describe(run_values) for run_values in runs],
                                 "all_samples": describe([v for r in runs for v in r])})
    for metric in E2E_COLUMNS:
        if metric == "oracle_agreement":
            continue
        by_round = {r: {arm: values[metric] for arm, values in arms.items()} for r, arms in e2e.items()}
        if by_round:
            summary["e2e"].append({"metric": metric, "arms": {
                arm: describe([v[arm] for v in by_round.values() if arm in v])
                for arm in sorted({a for v in by_round.values() for a in v})}, **compare(by_round)})
    summary["correctness"] = {
        "trace_fingerprints_identical_across_arms": {
            cell: len({fp for arm_fps in arms.values() for fp in arm_fps}) == 1
            for cell, arms in sorted(fingerprints.items())},
        "trace_fingerprints": {cell: {arm: sorted(fps) for arm, fps in sorted(arms.items())}
                               for cell, arms in sorted(fingerprints.items())},
        "init_validation": sorted(init_validation, key=lambda v: (v["cell"], v["arm"])),
        "router_digests": [{"metrics": metrics, "scenario": scenario,
                            "digests": {arm: sorted(d) for arm, d in sorted(arms.items())},
                            "identical": len({x for d in arms.values() for x in d}) == 1}
                           for (metrics, scenario), arms in sorted(verify.items())],
        "e2e_oracle": sorted(e2e_oracle, key=lambda v: (v["round"], v["arm"])),
    }
    summary["peak_rss_bytes"] = [{"cell": cell, "arm": arm, **describe(values)}
                                 for (cell, arm), values in sorted(peak_rss.items())]
    return {"rows": rows, "summary": summary}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def fmt(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "–"
    if abs(value) >= 1e5:
        return f"{value:,.0f}"
    return f"{value:,.{digits}f}"


def pct(value: Optional[float]) -> str:
    return "–" if value is None else f"{value:+.2f}%"


def timed_table(entries: Iterable[Dict[str, Any]], unit: str) -> List[str]:
    lines = [
        f"| Cell | Metric | n | Base median (IQR) {unit} | Candidate median (IQR) {unit} | A/A median (IQR) {unit} "
        "| Paired change [95% CI] | A/A bound | Sign test p |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for e in entries:
        arms = e["arms"]

        def stat(arm: str) -> str:
            if arm not in arms:
                return "–"
            a = arms[arm]
            return f"{fmt(a['median'])} ({fmt(a['iqr'])})"

        cand = e.get("cand", {})
        ci = cand.get("ci95_pct", [None, None])
        lines.append(
            f"| `{e['cell']}` | `{e['metric']}` | {arms.get('base', {}).get('n', 0)} | {stat('base')} | "
            f"{stat('cand')} | {stat('aa')} | {pct(cand.get('median_pct'))} [{pct(ci[0])}, {pct(ci[1])}] | "
            f"±{e['aa']['noise_bound_pct']:.2f}% | {fmt(cand.get('sign_test_p'), 4)} |")
    return lines


def render_report(campaign: Path, summary: Dict[str, Any]) -> str:
    run = campaign / "run"
    provenance = json.loads((run / "provenance.json").read_text())
    binaries = json.loads((run / "builds" / "binaries.json").read_text())
    verification = json.loads((run / "verification" / "summary.json").read_text()) \
        if (run / "verification" / "summary.json").exists() else []
    environment = json.loads((run / "environment.json").read_text())
    schedule = json.loads((run / "schedule.json").read_text())
    host_lines = []
    for command in environment["host"]["commands"]:
        text = command["stdout"].strip()
        if command["argv"][:1] in (["sw_vers"], ["sysctl"], ["uname"]) or command["argv"][:2] in (
                ["pmset", "-g"],) or command["argv"][1:2] == [f"+{provenance['toolchain']}"]:
            host_lines.append(f"$ {' '.join(command['argv'])}\n{text}")

    out: List[str] = []
    w = out.append
    w("# Hot-Path Audit: Baseline versus Candidate (generated)\n")
    w("Generated by `analyze.py` from the raw artifacts in `run/`. Do not edit by hand; "
      "regenerate with `python3 analyze.py`. Narrative and decisions: [README.md](README.md).\n")
    w("## Identities\n")
    k = provenance["knotrel"]
    b = provenance["knotrel_benchmarks"]
    w("| Item | Value |\n| --- | --- |")
    w(f"| Baseline | knotrel `{provenance['baseline']['commit']}` via `{provenance['baseline']['materialization']}` |")
    w(f"| Candidate | `{provenance['candidate']['materialization']}`; code patch sha256 "
      f"`{provenance['candidate']['code_patch_sha256']}` |")
    w(f"| Candidate code diff sha256 (`git diff HEAD -- . ':(exclude)docs'`) | `{k['diff_head_code_only_sha256']}` |")
    w(f"| knotrel branch / HEAD | `{k['branch']}` / `{k['head']}` |")
    w(f"| knotrel staged == working tree | {k['staged_equals_worktree']} |")
    w(f"| knotrel diff sha256: unstaged / staged / HEAD | `{k['diff_unstaged_sha256'][:16]}…` / "
      f"`{k['diff_staged_sha256'][:16]}…` / `{k['diff_head_sha256'][:16]}…` |")
    w(f"| knotrel-benchmarks branch / HEAD | `{b['branch']}` / `{b['head']}` |")
    w(f"| knotrel-benchmarks diff sha256: unstaged / staged | `{b['diff_unstaged_sha256'][:16]}…` / "
      f"`{b['diff_staged_sha256'][:16]}…` |")
    w(f"| Toolchain | `{provenance['toolchain']}` |")
    w("")
    w("Binary sha256 (A/A copies are byte-identical to the baseline):\n")
    w("| Tool | Baseline | Candidate |\n| --- | --- | --- |")
    for tool in sorted(binaries["sha256"]["base"]):
        w(f"| `{tool}` | `{binaries['sha256']['base'][tool][:16]}…` | `{binaries['sha256']['cand'][tool][:16]}…` |")
    w("\n## Host\n")
    w("```text\n" + "\n\n".join(host_lines) + "\n```\n")
    w(f"Schedule: {schedule['rounds']} rounds in {schedule['sessions']} sessions, arms "
      f"{', '.join(schedule['arms'])}, every round runs each cell once with each arm once in a counterbalanced "
      f"order (all {math.factorial(len(schedule['arms']))} orders equally often), seed {schedule['seed']}; "
      f"{schedule['quiet_seconds']:.0f} s quiet before the first session, "
      f"{schedule['session_cooldown_seconds']:.0f} s between sessions, "
      f"{schedule['round_cooldown_seconds']:.0f} s between rounds.\n")
    w("## Repository Verification\n")
    if verification:
        w("| Check | Exit |\n| --- | ---: |")
        for v in verification:
            w(f"| `{v['label']}`: `{' '.join(v['argv'][-8:])}` | {v['exit_code']} |")
    else:
        w("Not run in this campaign.")
    c = summary["correctness"]
    w("\n## Correctness\n")
    w("| Check | Result |\n| --- | --- |")
    w(f"| Trace fingerprints identical across arms (all timed core cells) | "
      f"{all(c['trace_fingerprints_identical_across_arms'].values())} "
      f"({len(c['trace_fingerprints_identical_across_arms'])} cells) |")
    w(f"| Initialization dynamic-continuation oracle (`--validate`) | "
      f"{sum(v['validated'] is True for v in c['init_validation'])}/{len(c['init_validation'])} passed |")
    w(f"| Router verification digests identical, baseline vs candidate | "
      f"{sum(d['identical'] for d in c['router_digests'])}/{len(c['router_digests'])} scenario×metrics |")
    agree = [o["oracle"] for o in c["e2e_oracle"]]
    w(f"| End-to-end oracle agreement | {sum(a == b for a, b in agree)}/{len(agree)} runs at 100% |")
    w("\nDynamic runs check every mutation and query against topology-derived expected answers and exit "
      "non-zero on a mismatch; every timed observation exited 0.\n")
    w("## Allocation Counts (counting allocator; not timings)\n")
    w("System allocator wrapped by `stats_alloc`. Allocation events = allocations + reallocations, per request, "
      "inside each timed window. Every repeat is listed in `analysis/summary.json`; background runtime work "
      "makes counts vary slightly between repeats, so the largest spread (max - min, relative to the median) "
      "is shown.\n")
    w("| Metrics | Scenario | Baseline (median of repeats) | Candidate (median of repeats) | Change "
      "| Largest repeat spread |\n| --- | --- | ---: | ---: | ---: | ---: |")
    for a in summary["allocation"]:
        if a["metric"] != "allocation_events_per_request":
            continue
        base = statistics.median(a["values"]["base"])
        cand = statistics.median(a["values"]["cand"])
        spread = max(a["repeat_spread_pct"].values())
        w(f"| {'on' if a['metrics'] else 'off'} | `{a['scenario']}` | {fmt(base, 2)} | {fmt(cand, 2)} | "
          f"{pct(100 * (cand / base - 1))} | {spread:.3f}% |")
    groups = {"confirmed improvement": [], "confirmed regression": [], "inconclusive": []}
    for entry in summary["timed"]:
        groups[entry["cand"]["verdict"]].append(entry)
    for title, key in (("Confirmed Improvements", "confirmed improvement"),
                       ("Confirmed Regressions", "confirmed regression"),
                       ("Inconclusive Measurements", "inconclusive")):
        w(f"\n## {title}\n")
        if not groups[key]:
            w("None.")
            continue
        w("Values are nanoseconds (per process; router rows per request). Change = candidate vs baseline of the "
          "same round, negative = faster.\n")
        out.extend(timed_table(groups[key], "ns"))
    w("\n## Mechanism Microbenchmarks (pattern replicas, not request-level effects)\n")
    w("| Benchmark | Threads | Median ns/op per run | Median of all samples (IQR) | n |\n| --- | ---: | --- | ---: | ---: |")
    for m in summary["micro"]:
        runs = ", ".join(fmt(r["median"]) for r in m["runs"])
        s = m["all_samples"]
        w(f"| `{m['benchmark']}` | {m['threads']} | {runs} | {fmt(s['median'])} ({fmt(s['iqr'])}) | {s['n']} |")
    w("\n## End-to-End HTTP (separate measurement)\n")
    w("`measure_e2e --scenario lifecycle --dataset large` against each arm's release server (mimalloc, loopback "
      "TCP, `Connection: close`). Connection setup can dominate request timings; these rows are not combined with "
      "the in-process results.\n")
    if summary["e2e"]:
        w("| Metric | n | Base median (IQR) | Candidate median (IQR) | A/A median (IQR) | Paired change [95% CI] "
          "| A/A bound | Verdict |\n| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |")
        for e in summary["e2e"]:
            arms = e["arms"]
            cand = e["cand"]
            stat = {a: f"{fmt(arms[a]['median'])} ({fmt(arms[a]['iqr'])})" if a in arms else "–"
                    for a in ("base", "cand", "aa")}
            w(f"| `{e['metric']}` | {arms['base']['n']} | {stat['base']} | {stat['cand']} | {stat['aa']} | "
              f"{pct(cand['median_pct'])} [{pct(cand['ci95_pct'][0])}, {pct(cand['ci95_pct'][1])}] | "
              f"±{e['aa']['noise_bound_pct']:.2f}% | {cand['verdict']} |")
    w("\nFor throughput (`query_qps`) a positive change means more requests per second; the verdict labels "
      "apply the slower-is-positive convention mechanically and must be read accordingly.\n")
    return "\n".join(out) + "\n"


def write_outputs(campaign: Path, result: Dict[str, Any]) -> None:
    analysis = campaign / "analysis"
    analysis.mkdir(exist_ok=True)
    fields = ["sequence", "section", "kind", "cell", "arm", "session", "round", "position", "metric", "value"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in sorted(result["rows"], key=lambda r: (r["sequence"], r["cell"], r["metric"])):
        writer.writerow({key: row.get(key, "") for key in fields})
    (analysis / "observations.csv").write_text(buffer.getvalue())
    (analysis / "summary.json").write_text(json.dumps(result["summary"], indent=2, sort_keys=True) + "\n")
    (campaign / "REPORT.md").write_text(render_report(campaign, result["summary"]))
    write_manifest(campaign)


DESCRIPTIONS = [
    ("README.md", "Campaign narrative, decisions and reproduction instructions (hand-written)."),
    ("REPORT.md", "Generated report: identities, verification, correctness, allocations, verdict tables."),
    ("analyze.py", "Regenerates analysis/, REPORT.md and manifest.json from run/ (stdlib Python)."),
    ("tests/", "Unit tests for analyze.py with synthetic inputs."),
    ("analysis/observations.csv", "Normalized observations: one row per metric value."),
    ("analysis/summary.json", "Per-cell statistics, paired deltas, intervals, verdicts and correctness."),
    ("provenance/", "Proof that the candidate equals the verified final tree (reconstruction script and inputs)."),
    ("run/provenance.json", "Baseline/candidate identities, Git state and diff hashes of both repositories."),
    ("run/candidate/", "Immutable candidate representation: code and full patches, reconstruction hashes."),
    ("run/environment.json", "Host, OS, CPU, memory, power, compiler, Cargo, allocator metadata, collector argv."),
    ("run/schedule.json", "Balanced interleaved schedule, archived before the first observation."),
    ("run/builds/", "Build commands, logs and binary hashes."),
    ("run/locks/", "Cargo.lock of every build (dependency metadata)."),
    ("run/verification/", "knotrel-benchmarks verification logs (fmt, Clippy, tests, doctests, Rustdoc)."),
    ("run/raw/", "Raw stdout/stderr of every child, referenced by observations.jsonl."),
    ("run/observations.jsonl", "One record per child: argv, env, cwd, timestamps, exit status, stream hashes."),
    ("run/host-checks.jsonl", "Host state (power, thermal, load, competing processes) at each check point."),
    ("run/collector.log", "Collector progress log."),
    ("run/DONE", "Completion marker with observation count."),
    ("run/STOPPED", "Stop reason (only present if the collector stopped early)."),
]


def describe_path(relative: str) -> str:
    for prefix, text in DESCRIPTIONS:
        if relative == prefix or (prefix.endswith("/") and relative.startswith(prefix)):
            return text
    return "Campaign artifact."


def write_manifest(campaign: Path) -> None:
    entries = []
    for path in sorted(campaign.rglob("*")):
        if path.is_dir() or "__pycache__" in path.parts:
            continue
        relative = path.relative_to(campaign).as_posix()
        if relative == "manifest.json":
            continue
        entries.append({"path": relative, "bytes": path.stat().st_size, "sha256": sha256_file(path),
                        "description": describe_path(relative)})
    manifest = {"schema": "knotrel-hot-path-audit-manifest-v1",
                "campaign": "hot-path-audit-20261114",
                "regenerate": "python3 results/hot-path-audit-20261114/analyze.py",
                "files": entries}
    (campaign / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def check(campaign: Path) -> int:
    """Regenerates into a temporary copy and compares with committed outputs."""
    with tempfile.TemporaryDirectory() as temporary:
        copy = Path(temporary) / campaign.name
        shutil.copytree(campaign, copy, ignore=shutil.ignore_patterns("__pycache__"))
        for relative in OUTPUTS:
            target = copy / relative
            if target.exists():
                target.unlink()
        write_outputs(copy, analyze(copy))
        differing = [relative for relative in OUTPUTS
                     if not (campaign / relative).exists()
                     or (campaign / relative).read_bytes() != (copy / relative).read_bytes()]
    if differing:
        print("outputs differ from a clean regeneration: " + ", ".join(differing))
        return 1
    print("clean regeneration matches committed outputs: " + ", ".join(OUTPUTS))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="verify committed outputs regenerate exactly")
    parser.add_argument("--campaign", default=str(HERE), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    campaign = Path(args.campaign).resolve()
    if args.check:
        return check(campaign)
    write_outputs(campaign, analyze(campaign))
    print(f"wrote {', '.join(OUTPUTS)} in {campaign}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
