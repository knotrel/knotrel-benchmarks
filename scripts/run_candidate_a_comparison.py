#!/usr/bin/env python3
"""Bounded Candidate A vs Baseline Comparison Collector.

Evaluates Candidate A (single-probe endpoint resolution in Graph::link)
against Baseline across a 6-cell core matrix:
- Engines: compact-bfs, compact-workspace
- Workloads:
  1. sustained-churn-blocks-v1, 10,000 nodes, 200 rounds, seed 42, query-percent 10
  2. chain-split-rejoin-v1, 10,000 nodes, 200 rounds, seed 42, native query mix
  3. sustained-churn-blocks-v1, 10,000 nodes, 200 rounds, seed 42, query-percent 90
- Schedule:
  3 sessions, each with 2 pairs per cell (1 baseline-first, 1 candidate-first).
  Total 36 pairs (72 measured invocations).
  Randomized pair order per session with fixed recorded seeds.
- Protocol:
  Warmup 1, repetitions 3.
  15s per-process timeout, 2700s overall deadline, 512 MiB RSS ceiling, 100 MiB evidence ceiling.
  60s quiet before Session 0; 300s cooldown + 60s quiet before Sessions 1 and 2.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re
import signal
import statistics
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_p0_aa import (
    BUILD_PROCESSES,
    host_state,
    observe_child,
    peak_rss,
    validate_host_state,
    directory_size_bytes,
    ProcessInterruptedError,
    capture_failure_reason,
)

# Constants
PER_PROCESS_TIMEOUT_SECONDS = 15.0
OVERALL_DEADLINE_SECONDS = 2700.0
PEAK_RSS_CEILING_BYTES = 536_870_912  # 512 MiB
DISK_CEILING_BYTES = 104_857_600  # 100 MiB
STREAM_LIMIT_BYTES = 1024 * 1024
FAILURE_RESERVE_BYTES = 65536
FAILURE_REASON_CHARACTERS = 2048
JSON_STREAM_BYTES_PER_CAPTURED_BYTE = 8
RAW_STREAM_STORAGE_COPIES = 2
OBSERVATION_ENVELOPE_MARGIN_BYTES = 4096
PRE_SESSION_QUIET_SECONDS = 60.0
INTER_SESSION_COOLDOWN_SECONDS = 300.0

SESSION_SEEDS = (202611080, 202611081, 202611082)

CELL_DEFINITIONS: List[Dict[str, Any]] = [
    {
        "cell_id": "cell_0_bfs_blocks_q10",
        "engine": "compact-bfs",
        "workload": "sustained-churn-blocks-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": 10,
        "expected_fingerprint": "5f45f0168e472074",
        "expected_counts": {"cut": 9308, "link": 8692, "connected": 2000},
    },
    {
        "cell_id": "cell_1_bfs_chain_native",
        "engine": "compact-bfs",
        "workload": "chain-split-rejoin-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": None,
        "expected_fingerprint": "07fe10cf81dc928b",
        "expected_counts": {"cut": 200, "link": 200, "connected": 400},
    },
    {
        "cell_id": "cell_2_bfs_blocks_q90",
        "engine": "compact-bfs",
        "workload": "sustained-churn-blocks-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": 90,
        "expected_fingerprint": "4e3d879b9e2eed27",
        "expected_counts": {"cut": 1296, "link": 704, "connected": 18000},
    },
    {
        "cell_id": "cell_3_ws_blocks_q10",
        "engine": "compact-workspace",
        "workload": "sustained-churn-blocks-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": 10,
        "expected_fingerprint": "5f45f0168e472074",
        "expected_counts": {"cut": 9308, "link": 8692, "connected": 2000},
    },
    {
        "cell_id": "cell_4_ws_chain_native",
        "engine": "compact-workspace",
        "workload": "chain-split-rejoin-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": None,
        "expected_fingerprint": "07fe10cf81dc928b",
        "expected_counts": {"cut": 200, "link": 200, "connected": 400},
    },
    {
        "cell_id": "cell_5_ws_blocks_q90",
        "engine": "compact-workspace",
        "workload": "sustained-churn-blocks-v1",
        "nodes": 10000,
        "rounds": 200,
        "seed": 42,
        "query_percent": 90,
        "expected_fingerprint": "4e3d879b9e2eed27",
        "expected_counts": {"cut": 1296, "link": 704, "connected": 18000},
    },
]


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def generate_schedule(
    cells: List[Dict[str, Any]],
    sessions_count: int = 3,
    session_seeds: Tuple[int, ...] = SESSION_SEEDS,
) -> Dict[str, Any]:
    """Generate balanced 36-pair schedule across 3 sessions."""
    schedule_sessions = []
    global_pair_id = 0

    for s_idx in range(sessions_count):
        session_seed = session_seeds[s_idx]
        session_pairs = []

        for cell in cells:
            for order in ("B_first", "C_first"):
                session_pairs.append({
                    "cell_id": cell["cell_id"],
                    "engine": cell["engine"],
                    "workload": cell["workload"],
                    "nodes": cell["nodes"],
                    "rounds": cell["rounds"],
                    "seed": cell["seed"],
                    "query_percent": cell["query_percent"],
                    "order": order,
                    "expected_fingerprint": cell["expected_fingerprint"],
                    "expected_counts": cell["expected_counts"],
                })

        rng = random.Random(session_seed)
        rng.shuffle(session_pairs)

        finalized_pairs = []
        for p in session_pairs:
            p_copy = dict(p)
            p_copy["pair_id"] = global_pair_id
            p_copy["session"] = s_idx
            finalized_pairs.append(p_copy)
            global_pair_id += 1

        schedule_sessions.append({
            "session_index": s_idx,
            "session_seed": session_seed,
            "pairs": finalized_pairs,
        })

    return {
        "schema": "knotrel-candidate-a-comparison-schedule-v1",
        "total_cells": len(cells),
        "total_sessions": sessions_count,
        "pairs_per_session": len(cells) * 2,
        "total_pairs": global_pair_id,
        "total_invocations": global_pair_id * 2,
        "sessions": schedule_sessions,
    }


def build_command_args(
    binary_path: str,
    cell: Dict[str, Any],
    repetitions: int = 3,
    warmup: int = 1,
) -> List[str]:
    cmd = [
        binary_path,
        "--workload", str(cell["workload"]),
        "--nodes", str(cell["nodes"]),
        "--rounds", str(cell["rounds"]),
        "--seed", str(cell["seed"]),
        "--warmup", str(warmup),
        "--repetitions", str(repetitions),
        "--engine", str(cell["engine"]),
    ]
    if cell.get("query_percent") is not None:
        cmd.extend(["--query-percent", str(cell["query_percent"])])
    return cmd


LATENCY_FIELDS = ("total_ns", "min_ns", "p50_ns", "p95_ns", "p99_ns", "max_ns")
QUANTILE_FIELDS = LATENCY_FIELDS[1:]
REPORT_REPETITIONS = 3
REPORT_WARMUP = 1
REPORT_SCHEMA_VERSION = 2
MAX_REPORT_INTEGER = (1 << 128) - 1


def _unique_json_object(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError(f"Duplicate JSON field: {name}")
        result[name] = value
    return result


def _reject_json_constant(value: str) -> Any:
    raise ValueError(f"Invalid JSON numeric constant: {value}")


def _unsigned_integer(value: Any, field: str, positive: bool = False) -> int:
    if type(value) is not int or not (1 if positive else 0) <= value <= MAX_REPORT_INTEGER:
        raise ValueError(f"Invalid {field}: expected {'positive' if positive else 'nonnegative'} integer")
    return value


def _validate_latency(value: Any, field: str, expected_count: Optional[int] = None) -> int:
    if not isinstance(value, dict):
        raise ValueError(f"Missing or invalid latency {field}")
    if set(value) != {"count", *LATENCY_FIELDS}:
        raise ValueError(f"Missing or unexpected latency fields in {field}")
    count = _unsigned_integer(value.get("count"), f"{field}.count", positive=True)
    if expected_count is not None and count != expected_count:
        raise ValueError(f"{field} count mismatch: {count} != {expected_count}")
    for name in LATENCY_FIELDS:
        _unsigned_integer(value.get(name), f"{field}.{name}")
    quantiles = [value[name] for name in QUANTILE_FIELDS]
    if quantiles != sorted(quantiles):
        raise ValueError(f"Invalid latency ordering in {field}")
    if not count * value["min_ns"] <= value["total_ns"] <= count * value["max_ns"]:
        raise ValueError(f"Invalid latency total in {field}")
    return count


def parse_core_report(stdout: str, cell: Dict[str, Any]) -> Dict[str, Any]:
    """Parse and strictly validate JSON report from knotrel-benchmarks."""
    try:
        data = json.loads(stdout, object_pairs_hook=_unique_json_object,
                  parse_constant=_reject_json_constant)
    except Exception as exc:
        raise ValueError(f"Core stdout is not valid JSON: {exc}") from exc

    if isinstance(data, dict) and "repetitions" in data and "comparisons" not in data:
        report = data
    else:
        raise ValueError("Core stdout JSON has unrecognized schema")

    if type(report.get("schema_version")) is not int or report["schema_version"] != REPORT_SCHEMA_VERSION:
        raise ValueError(f"Unsupported schema_version: {report.get('schema_version')}")
    if "import" in report:
        raise ValueError("Imported workload is not a generated schema-v2 report")

    if report.get("workload") != cell["workload"]:
        raise ValueError("Workload mismatch")
    config = report.get("config")
    if not isinstance(config, dict) or set(config) != {"nodes", "rounds", "seed"}:
        raise ValueError("Invalid workload config")
    for name, value in config.items():
        _unsigned_integer(value, f"config.{name}")
        if value != cell[name]:
            raise ValueError(f"Config {name} mismatch")
    if cell["query_percent"] is None:
        if "query_percent" in report:
            raise ValueError("Unexpected query_percent for native workload")
    elif (_unsigned_integer(report.get("query_percent"), "query_percent")
          != cell["query_percent"]):
        raise ValueError("Query percent mismatch")
    if _unsigned_integer(report.get("warmup"), "warmup") != REPORT_WARMUP:
        raise ValueError("Warmup mismatch")
    if _unsigned_integer(report.get("query_repeats"), "query_repeats") != 0:
        raise ValueError("Query repeats mismatch")

    fp = report.get("trace_fingerprint_fnv1a64")
    if fp != cell["expected_fingerprint"]:
        raise ValueError(f"Trace fingerprint mismatch: {fp} != {cell['expected_fingerprint']}")

    expected_engine_map = {
        "compact-bfs": "knotrel-core/compact-bfs-v1",
        "compact-workspace": "knotrel-core/compact-workspace-v2",
    }
    expected_engine = expected_engine_map.get(cell["engine"], cell["engine"])
    if report.get("engine") != expected_engine:
        raise ValueError(f"Engine mismatch: {report.get('engine')} != {expected_engine}")

    reps = report.get("repetitions")
    if not isinstance(reps, list) or len(reps) != REPORT_REPETITIONS:
        raise ValueError(f"Expected {REPORT_REPETITIONS} repetitions")

    for index, rep in enumerate(reps, start=1):
        prefix = f"repetition {index}"
        if not isinstance(rep, dict):
            raise ValueError(f"Invalid {prefix}")
        if set(rep) != {"setup_ns", "workload_wall_ns", "measurements", "query_true",
                        "query_false", "repeated_queries"}:
            raise ValueError(f"Missing or unexpected repetition fields in {prefix}")
        _unsigned_integer(rep.get("workload_wall_ns"), f"{prefix}.workload_wall_ns", positive=True)
        _unsigned_integer(rep.get("setup_ns"), f"{prefix}.setup_ns")
        measurements = rep.get("measurements")
        if not isinstance(measurements, dict) or set(measurements) != set(cell["expected_counts"]):
            raise ValueError(f"Invalid measurements in {prefix}")
        for operation, count in cell["expected_counts"].items():
            _validate_latency(measurements[operation], f"{prefix}.{operation}", count)
        partition_count = 0
        partition_total = 0
        for name in ("query_true", "query_false"):
            if name not in rep:
                raise ValueError(f"Missing {prefix}.{name}")
            if rep[name] is not None:
                expected = cell["rounds"] if cell["query_percent"] is None else None
                partition_count += _validate_latency(rep[name], f"{prefix}.{name}", expected)
                partition_total += rep[name]["total_ns"]
            elif cell["query_percent"] is None:
                raise ValueError(f"Missing native query partition in {prefix}")
        connected = measurements["connected"]
        if partition_count != connected["count"] or partition_total != connected["total_ns"]:
            raise ValueError(f"Query partition mismatch in {prefix}")
        if "repeated_queries" not in rep or rep["repeated_queries"] is not None:
            raise ValueError(f"Invalid {prefix}.repeated_queries")

    # Extract summary metrics across repetitions
    wall_durations = [r["workload_wall_ns"] for r in reps]
    setup_durations = [r["setup_ns"] for r in reps]
    link_p50s = [r["measurements"]["link"]["p50_ns"] for r in reps]
    query_p50s = [r["measurements"]["connected"]["p50_ns"] for r in reps]

    return {
        "status": "parsed_valid",
        "schema_version": report.get("schema_version"),
        "trace_fingerprint": fp,
        "engine": report.get("engine"),
        "workload": report.get("workload"),
        "repetitions": reps,
        "workload_wall_ns_samples": wall_durations,
        "workload_wall_ns_median": statistics.median(wall_durations),
        "setup_ns_median": statistics.median(setup_durations),
        "link_p50_ns_median": statistics.median(link_p50s),
        "query_p50_ns_median": statistics.median(query_p50s),
        "raw_report": report,
    }


def analyze_comparison(pairs_data: List[Dict[str, Any]], schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Compute per-cell before/after comparison statistics."""
    cell_groups: Dict[str, List[Dict[str, Any]]] = {}
    for p in pairs_data:
        cell_id = p["cell_id"]
        cell_groups.setdefault(cell_id, []).append(p)

    analysis_results: Dict[str, Any] = {}

    for cell_id, pairs in cell_groups.items():
        raw_diffs = []
        rel_diffs = []
        log_ratios = []

        b_walls = []
        c_walls = []
        b_links = []
        c_links = []
        b_queries = []
        c_queries = []
        b_rss = []
        c_rss = []

        p0_is_b_diffs = []
        p0_is_c_diffs = []

        for p in pairs:
            # Baseline is B, Candidate is C
            val_b = p["obs_B"]["parsed"]["workload_wall_ns_median"]
            val_c = p["obs_C"]["parsed"]["workload_wall_ns_median"]

            b_walls.append(val_b)
            c_walls.append(val_c)

            b_links.append(p["obs_B"]["parsed"]["link_p50_ns_median"])
            c_links.append(p["obs_C"]["parsed"]["link_p50_ns_median"])

            b_queries.append(p["obs_B"]["parsed"]["query_p50_ns_median"])
            c_queries.append(p["obs_C"]["parsed"]["query_p50_ns_median"])

            if p["obs_B"]["obs"].get("peak_rss_bytes"):
                b_rss.append(p["obs_B"]["obs"]["peak_rss_bytes"])
            if p["obs_C"]["obs"].get("peak_rss_bytes"):
                c_rss.append(p["obs_C"]["obs"]["peak_rss_bytes"])

            # Difference definition: C - B (negative means candidate is faster)
            diff = val_c - val_b
            rel = (val_c - val_b) / val_b if val_b else 0.0
            log_r = math.log(val_c / val_b) if (val_b > 0 and val_c > 0) else 0.0

            raw_diffs.append(diff)
            rel_diffs.append(rel)
            log_ratios.append(log_r)

            if p["order"] == "B_first":
                p0_is_b_diffs.append(diff)
            else:
                p0_is_c_diffs.append(diff)

        def stats_summary(arr: List[float]) -> Dict[str, Any]:
            if not arr:
                return {}
            n = len(arr)
            mean = statistics.mean(arr)
            std = statistics.stdev(arr) if n > 1 else 0.0
            cv = (std / mean) if mean != 0 else 0.0
            med = statistics.median(arr)
            sorted_arr = sorted(arr)
            q1 = sorted_arr[n // 4]
            q3 = sorted_arr[(3 * n) // 4]
            return {
                "count": n,
                "mean": mean,
                "std": std,
                "cv": cv,
                "median": med,
                "iqr": q3 - q1,
                "min": sorted_arr[0],
                "max": sorted_arr[-1],
            }

        analysis_results[cell_id] = {
            "cell_id": cell_id,
            "engine": pairs[0]["engine"],
            "workload": pairs[0]["workload"],
            "pairs_count": len(pairs),
            "paired_difference_wall_ns": {
                "definition": "Candidate - Baseline (negative means candidate is faster)",
                "raw_diff_mean_ns": statistics.mean(raw_diffs),
                "raw_diff_median_ns": statistics.median(raw_diffs),
                "rel_diff_mean_percent": statistics.mean(rel_diffs) * 100.0,
                "rel_diff_median_percent": statistics.median(rel_diffs) * 100.0,
                "log_ratio_mean": statistics.mean(log_ratios),
                "pairs": [
                    {
                        "pair_id": p["pair_id"],
                        "session": p["session"],
                        "order": p["order"],
                        "val_baseline_ns": p["obs_B"]["parsed"]["workload_wall_ns_median"],
                        "val_candidate_ns": p["obs_C"]["parsed"]["workload_wall_ns_median"],
                        "diff_ns": p["obs_C"]["parsed"]["workload_wall_ns_median"] - p["obs_B"]["parsed"]["workload_wall_ns_median"],
                        "rel_diff_percent": ((p["obs_C"]["parsed"]["workload_wall_ns_median"] - p["obs_B"]["parsed"]["workload_wall_ns_median"]) / p["obs_B"]["parsed"]["workload_wall_ns_median"]) * 100.0,
                    }
                    for p in pairs
                ],
            },
            "order_effects": {
                "B_first_diff_mean_ns": statistics.mean(p0_is_b_diffs) if p0_is_b_diffs else None,
                "C_first_diff_mean_ns": statistics.mean(p0_is_c_diffs) if p0_is_c_diffs else None,
            },
            "metrics": {
                "wall_duration_ns": {
                    "baseline": stats_summary(b_walls),
                    "candidate": stats_summary(c_walls),
                },
                "link_p50_ns": {
                    "baseline": stats_summary(b_links),
                    "candidate": stats_summary(c_links),
                },
                "query_p50_ns": {
                    "baseline": stats_summary(b_queries),
                    "candidate": stats_summary(c_queries),
                },
                "peak_rss_bytes": {
                    "baseline": stats_summary(b_rss) if b_rss else {},
                    "candidate": stats_summary(c_rss) if c_rss else {},
                },
            },
        }

    return {
        "schema": "knotrel-candidate-a-analysis-v1",
        "methodological_disclaimer": "Descriptive paired differences across 6 cells (6 pairs per cell across 3 sessions).",
        "cell_analyses": analysis_results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True, help="New evidence output directory")
    parser.add_argument("--baseline-bin", type=Path, required=True, help="Baseline knotrel-benchmarks binary")
    parser.add_argument("--candidate-bin", type=Path, required=True, help="Candidate knotrel-benchmarks binary")
    parser.add_argument("--dry-run", action="store_true", help="Validate provenance and plan without running")
    parser.add_argument("--execute", action="store_true", help="Execute the 36-pair comparison campaign")
    parser.add_argument("--skip-quiet", action="store_true", help="Skip quiet/cooldown intervals (testing only)")
    parser.add_argument("--fake-runner", action="store_true", help="Use fake child runner for unit testing")
    parser.add_argument("--cwd", type=Path, default=SCRIPTS_DIR, help="Recorded runtime working directory")
    parser.add_argument("--baseline-sha256", default="03dbb4167e6516d0d7e10b691fefe6f5e9d9ed48cf43843307c59d53200d2d27")
    parser.add_argument("--candidate-sha256", default="1c19413d023b3e7278c9cb3b8df7adf4019b50daf9a2b5678fa93791e1b40d4c")
    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("Specify either --dry-run or --execute")

    dest = args.destination.resolve()
    if dest.exists():
        parser.error(f"Destination already exists: {dest}")

    # Provenance verification
    if not args.baseline_bin.is_file():
        parser.error(f"Baseline binary not found: {args.baseline_bin}")
    if not args.candidate_bin.is_file():
        parser.error(f"Candidate binary not found: {args.candidate_bin}")

    b_sha = digest_file(args.baseline_bin)
    c_sha = digest_file(args.candidate_bin)

    expected_b_sha = args.baseline_sha256
    expected_c_sha = args.candidate_sha256
    for expected in (expected_b_sha, expected_c_sha):
        if not re.fullmatch(r"[0-9a-f]{64}", expected):
            parser.error("Expected binary SHA256 must contain 64 lowercase hex characters")

    if b_sha != expected_b_sha:
        raise ValueError(f"Baseline binary SHA256 mismatch: {b_sha} != {expected_b_sha}")
    if c_sha != expected_c_sha:
        raise ValueError(f"Candidate binary SHA256 mismatch: {c_sha} != {expected_c_sha}")

    schedule = generate_schedule(CELL_DEFINITIONS, sessions_count=3)

    if args.dry_run:
        print(f"Dry-run validated successfully:")
        print(f"  Baseline:  {args.baseline_bin} (SHA256: {b_sha})")
        print(f"  Candidate: {args.candidate_bin} (SHA256: {c_sha})")
        print(f"  Schedule:  {schedule['total_cells']} cells, {schedule['total_sessions']} sessions, {schedule['total_pairs']} pairs, {schedule['total_invocations']} invocations.")
        return

    # Check host preconditions
    if not args.fake_runner:
        initial_host = host_state()
        ok, reason = validate_host_state(initial_host, baseline=None, enforce_ac=True)
        if not ok:
            raise RuntimeError(f"Initial host validation failed: {reason}")
    else:
        initial_host = {"fake": True}

    dest.mkdir(parents=True, exist_ok=False)

    start_mono = time.monotonic_ns()
    start_unix = time.time_ns()
    campaign_deadline = time.monotonic() + OVERALL_DEADLINE_SECONDS

    run_meta = {
        "schema": "knotrel-candidate-a-comparison-run-metadata-v1",
        "destination": str(dest),
        "status": "running",
        "start_monotonic_ns": start_mono,
        "start_unix_ns": start_unix,
        "overall_deadline_seconds": OVERALL_DEADLINE_SECONDS,
        "per_process_timeout_seconds": PER_PROCESS_TIMEOUT_SECONDS,
        "disk_ceiling_bytes": DISK_CEILING_BYTES,
        "peak_rss_ceiling_bytes": PEAK_RSS_CEILING_BYTES,
        "binaries": {
            "baseline_bin": str(args.baseline_bin),
            "baseline_sha256": b_sha,
            "candidate_bin": str(args.candidate_bin),
            "candidate_sha256": c_sha,
        },
        "build_env_override": "GIT_CONFIG_GLOBAL=/dev/null",
        "initial_host": initial_host,
        "session_host_states": [],
        "completed_pairs": 0,
        "completed_observations": 0,
    }

    pairs_results = []
    runtime_env = {key: os.environ[key] for key in ("PATH", "HOME", "TMPDIR", "LANG", "LC_ALL", "CARGO_HOME", "RUSTUP_HOME", "SDKROOT") if key in os.environ}
    runtime_env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    run_meta.update(fake_runner=args.fake_runner, runtime_environment=runtime_env,
                    runtime_cwd=str(args.cwd.resolve()), stream_limit_bytes=STREAM_LIMIT_BYTES)
    def encoded(value):
        return (json.dumps(value, indent=2, default=str) + "\n").encode("utf-8")

    def failure_reserve():
        template = dict(run_meta, status="failed", failure_error="\0" * FAILURE_REASON_CHARACTERS,
                        completion_monotonic_ns=(1 << 128) - 1, completion_unix_ns=(1 << 128) - 1,
                        total_wall_duration_seconds=sys.float_info.max)
        observation_errors = 2 * FAILURE_REASON_CHARACTERS * 6
        return max(FAILURE_RESERVE_BYTES, len(encoded(template)) + observation_errors + OBSERVATION_ENVELOPE_MARGIN_BYTES)

    def save(filename, value, failure=False):
        target = dest / filename
        data = encoded(value)
        existing = target.stat().st_size if target.exists() else 0
        ceiling = DISK_CEILING_BYTES if failure else DISK_CEILING_BYTES - failure_reserve()
        if directory_size_bytes(dest) - existing + len(data) > ceiling:
            raise RuntimeError("Campaign evidence budget/ceiling exhausted")
        target.write_bytes(data)

    try:
        save("schedule.json", schedule)
        for s_idx, session_info in enumerate(schedule["sessions"]):
            if time.monotonic() > campaign_deadline:
                raise RuntimeError("Overall campaign deadline exceeded before session start")

            # Session quiet/cooldown
            if not args.skip_quiet and not args.fake_runner:
                if s_idx == 0:
                    print(f"Waiting initial {PRE_SESSION_QUIET_SECONDS}s quiet before Session 0...", flush=True)
                    time.sleep(PRE_SESSION_QUIET_SECONDS)
                else:
                    print(f"Waiting {INTER_SESSION_COOLDOWN_SECONDS}s cooldown + {PRE_SESSION_QUIET_SECONDS}s quiet before Session {s_idx}...", flush=True)
                    time.sleep(INTER_SESSION_COOLDOWN_SECONDS + PRE_SESSION_QUIET_SECONDS)

            pre_session_host = host_state() if not args.fake_runner else {"fake": True}
            if not args.fake_runner:
                ok, reason = validate_host_state(pre_session_host, baseline=initial_host, enforce_ac=True)
                if not ok:
                    raise RuntimeError(f"Session {s_idx} pre-session host check failed: {reason}")

            print(f"--- Starting Session {s_idx} ({len(session_info['pairs'])} pairs) ---", flush=True)

            for p_info in session_info["pairs"]:
                if time.monotonic() > campaign_deadline:
                    raise RuntimeError("Overall campaign deadline exceeded during session")

                pair_id = p_info["pair_id"]
                order = p_info["order"]
                cell_id = p_info["cell_id"]

                # Determine sequence of treatments in pair
                treatments = [("B", str(args.baseline_bin)), ("C", str(args.candidate_bin))] if order == "B_first" else [("C", str(args.candidate_bin)), ("B", str(args.baseline_bin))]

                pair_obs = {}

                for pos_idx, (treat_label, bin_path) in enumerate(treatments):
                    remaining = campaign_deadline - time.monotonic()
                    if remaining <= 0:
                        raise RuntimeError("Overall campaign deadline exceeded before invocation")
                    argv = build_command_args(bin_path, p_info, repetitions=3, warmup=1)
                    invocation = {"cell_id": cell_id, "pair_id": pair_id, "session": s_idx,
                                  "position": pos_idx, "treatment": treat_label, "argv": argv,
                                  "cwd": str(args.cwd.resolve()), "environment": runtime_env}
                    prefix = (["/usr/bin/time", "-l"] if sys.platform == "darwin" else
                              ["/usr/bin/time", "-v"] if sys.platform.startswith("linux") else [])
                    observer_metadata = dict(argv=argv, full_cmd=prefix + argv, cwd=invocation["cwd"], env=runtime_env,
                        stdout="", raw_stderr="", stdout_bytes_base64="", stderr_bytes_base64="",
                        failure_reason="", status="launch_failed", wrapper_pid=(1 << 128) - 1)
                    envelope = dict(invocation, obs=observer_metadata, status="raw_captured", failure_reason=None)
                    metadata_bytes = len(encoded(envelope)) + OBSERVATION_ENVELOPE_MARGIN_BYTES
                    available = (DISK_CEILING_BYTES - failure_reserve() - directory_size_bytes(dest)
                                 - RAW_STREAM_STORAGE_COPIES * metadata_bytes)
                    capture_limit = min(STREAM_LIMIT_BYTES, available //
                                        (JSON_STREAM_BYTES_PER_CAPTURED_BYTE * RAW_STREAM_STORAGE_COPIES))
                    if capture_limit < 1:
                        raise RuntimeError("Campaign evidence budget cannot reserve invocation metadata and bounded streams")

                    if args.fake_runner:
                        # Fake observation for testing
                        mock_report = {
                            "schema_version": 2,
                            "engine": "knotrel-core/compact-bfs-v1" if "bfs" in p_info["engine"] else "knotrel-core/compact-workspace-v2",
                            "workload": p_info["workload"],
                            "config": {"nodes": p_info["nodes"], "rounds": p_info["rounds"], "seed": p_info["seed"]},
                            "warmup": 1,
                            "query_repeats": 0,
                            "trace_fingerprint_fnv1a64": p_info["expected_fingerprint"],
                            "repetitions": [
                                {
                                    "workload_wall_ns": 1000000 if treat_label == "B" else 950000,
                                    "setup_ns": 50000,
                                    "measurements": {
                                        op: {"count": cnt, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 20 * cnt}
                                        for op, cnt in p_info["expected_counts"].items()
                                    },
                                }
                                for _ in range(3)
                            ],
                        }
                        if p_info["query_percent"] is not None:
                            mock_report["query_percent"] = p_info["query_percent"]
                        for repetition in mock_report["repetitions"]:
                            queries = p_info["expected_counts"]["connected"]
                            for name, count in (("query_true", queries // 2), ("query_false", queries - queries // 2)):
                                repetition[name] = dict(repetition["measurements"]["connected"], count=count, total_ns=20 * count)
                            repetition["repeated_queries"] = None
                        obs = {
                            "exit_code": 0,
                            "timed_out": False,
                            "wall_duration_ns": 1050000,
                            "stdout": json.dumps(mock_report),
                            "raw_stderr": "fake",
                            "peak_rss_bytes": 10000000,
                        }
                    else:
                        try:
                            obs = observe_child(argv=argv, cwd=str(args.cwd.resolve()), env=runtime_env,
                                                timeout_seconds=min(PER_PROCESS_TIMEOUT_SECONDS, remaining),
                                                is_core=True, output_limit_bytes=capture_limit)
                        except ProcessInterruptedError as exc:
                            obs = exc.observation
                            obs["failure_reason"] = str(exc)
                    observation_name = f"observation_{pair_id:03d}_pos{pos_idx}_{treat_label}.json"
                    obs = dict(obs)
                    if obs.get("failure_reason"):
                        obs["failure_reason"] = str(obs["failure_reason"])[:FAILURE_REASON_CHARACTERS]
                    record = dict(invocation, obs=obs, status="raw_captured", failure_reason=None)
                    try:
                        save(observation_name, record)
                        capture_error = capture_failure_reason(obs)
                        if capture_error:
                            raise RuntimeError(capture_error)
                        if obs["exit_code"] != 0:
                            raise RuntimeError(f"Child exited with code {obs['exit_code']}")
                        if obs["timed_out"]:
                            raise RuntimeError("Child timed out")
                        if obs.get("peak_rss_bytes") and obs["peak_rss_bytes"] > PEAK_RSS_CEILING_BYTES:
                            raise RuntimeError("Retrospective RSS ceiling exceeded")
                        parsed = parse_core_report(obs["stdout"], p_info)
                    except BaseException as exc:
                        record.update(status="failed", failure_reason=str(exc)[:FAILURE_REASON_CHARACTERS])
                        save(observation_name, record, failure=True)
                        raise
                    record["status"] = "parsed_valid"
                    save(observation_name, record)

                    # Save raw report JSON
                    rep_name = f"report_pair_{pair_id:03d}_pos{pos_idx}_{treat_label}_{cell_id}.json"
                    save(rep_name, parsed["raw_report"])

                    pair_obs[f"pos_{pos_idx}"] = {
                        "position": pos_idx,
                        "treatment": treat_label,
                        "obs": obs,
                        "parsed": parsed,
                        "report_file": rep_name,
                    }
                    run_meta["completed_observations"] += 1

                # Package pair record
                obs_b = pair_obs["pos_0"] if pair_obs["pos_0"]["treatment"] == "B" else pair_obs["pos_1"]
                obs_c = pair_obs["pos_0"] if pair_obs["pos_0"]["treatment"] == "C" else pair_obs["pos_1"]

                pair_record = {
                    "pair_id": pair_id,
                    "session": s_idx,
                    "order": order,
                    "cell_id": cell_id,
                    "engine": p_info["engine"],
                    "workload": p_info["workload"],
                    "obs_B": obs_b,
                    "obs_C": obs_c,
                }
                pairs_results.append(pair_record)

                pair_file = f"pair_{pair_id:03d}_{cell_id}_{order}.json"
                save(pair_file, pair_record)

                run_meta["completed_pairs"] += 1
                diff_ns = obs_c["parsed"]["workload_wall_ns_median"] - obs_b["parsed"]["workload_wall_ns_median"]
                rel_pct = (diff_ns / obs_b["parsed"]["workload_wall_ns_median"]) * 100.0 if obs_b["parsed"]["workload_wall_ns_median"] else 0.0
                print(f"Pair {pair_id:02d} [{cell_id}] ({order}): Baseline={obs_b['parsed']['workload_wall_ns_median']}ns, Candidate={obs_c['parsed']['workload_wall_ns_median']}ns, Diff={diff_ns:+d}ns ({rel_pct:+.2f}%)", flush=True)

            post_session_host = host_state() if not args.fake_runner else {"fake": True}
            run_meta["session_host_states"].append({
                "session_index": s_idx,
                "pre_session": pre_session_host,
                "post_session": post_session_host,
            })

        if pairs_results:
            save("analysis.json", analyze_comparison(pairs_results, schedule))
        run_meta["status"] = "completed"
    except BaseException as exc:
        run_meta["status"] = "failed"
        run_meta["failure_error"] = str(exc)[:FAILURE_REASON_CHARACTERS]
        print(f"\nExecution failed: {exc}", file=sys.stderr)
        raise
    finally:
        comp_mono = time.monotonic_ns()
        comp_unix = time.time_ns()
        run_meta["completion_monotonic_ns"] = comp_mono
        run_meta["completion_unix_ns"] = comp_unix
        run_meta["total_wall_duration_seconds"] = (comp_mono - start_mono) / 1e9

        try:
            save("run_metadata.json", run_meta, failure=True)
        except RuntimeError as exc:
            save("run_metadata.json", dict(status="failed", failure_error=str(exc),
                original_failure=run_meta.get("failure_error"),
                full_metadata_bytes=len(encoded(run_meta)),
                metadata_omitted="Full metadata exceeds the configured evidence budget; no quota bypass attempted"), failure=True)

    print(f"\nCampaign completed successfully in {run_meta['total_wall_duration_seconds']:.2f}s.")
    print(f"Evidence saved to: {dest}")


if __name__ == "__main__":
    main()
