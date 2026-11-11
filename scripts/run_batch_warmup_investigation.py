#!/usr/bin/env python3
"""Bounded Investigation Runner: Standalone Batch Warmup Chunking (Chunk 50 vs Chunk 1).

Compares Treatment A (--batch-warmup-chunk-size 50, 1 request of 50 queries) against
Treatment B (--batch-warmup-chunk-size 1, 50 requests of 1 query each) across
measured batch sizes B in {8, 64, 256} under the fixed standalone-batch contract.

Delegates process observation, timeouts, host checks, and JSON qualification to
knotrel-benchmarks/scripts/run_p0_aa.py without modifying historical A/A contracts.
"""

import argparse
import copy
import hashlib
import json
import math
import os
import random
import signal
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import run_p0_aa as p0
from run_p0_aa import (
    EnvironmentalInvalidationError,
    ProcessExecutionError,
    QualificationBlockerError,
    directory_size_bytes,
    host_state,
    observe_child,
    parse_http_batch_json,
    validate_host_state,
    campaign_capture_limit,
    DEFAULT_STREAM_LIMIT_BYTES,
    capture_failure_reason,
)

# Operational limits
PER_PROCESS_TIMEOUT_SECONDS = 15.0
OVERALL_CAMPAIGN_DEADLINE_SECONDS = 2700.0
PEAK_RSS_CEILING_BYTES = 512 * 1024 * 1024  # 512 MiB
DISK_CEILING_BYTES = 100 * 1024 * 1024       # 100 MiB
PRE_SESSION_QUIET_SECONDS = 60.0
INTER_SESSION_COOLDOWN_SECONDS = 300.0

# Fixed Binaries & Hashes
WORKSPACE_DIR = SCRIPTS_DIR.parent.parent
SERVER_BINARY_PATH = WORKSPACE_DIR / "baseline-v0.2.0" / "target" / "release" / "knotrel-server"
SERVER_SHA256 = "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a"

DRIVER_BINARY_PATH = WORKSPACE_DIR / "knotrel" / "target-warmup-investigation" / "release" / "examples" / "measure_e2e"
DRIVER_SHA256 = "0556ff2d208c42b45987cb5b2af4f331d196aeacfcdba81220c3a9c66f0129e9"

ACCEPTED_RELEASE_DRIVER_PATH = WORKSPACE_DIR / "knotrel" / "target" / "release" / "examples" / "measure_e2e"
ACCEPTED_RELEASE_DRIVER_SHA256 = "3dda9c76d3a4e11d801dc06927c43dd95efba708bf0c4157a0455c4083348af3"

FROZEN_BENCHMARKS_PATH = WORKSPACE_DIR / "baseline-v0.2.0" / "target" / "release" / "knotrel-benchmarks"
FROZEN_BENCHMARKS_SHA256 = "9d198be6a621fd34a556df2009058064e7acf9c686a32e100b56fb06207377a8"

# Session Randomization Seeds
SESSION_SEEDS = [202611080, 202611081, 202611082]
BATCH_SIZES = [8, 64, 256]


def compute_sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def generate_schedule(
    destination: Path,
    driver_bin: Path = DRIVER_BINARY_PATH,
    server_bin: Path = SERVER_BINARY_PATH,
    session_seeds: List[int] = SESSION_SEEDS,
    cwd: Optional[Path] = None,
) -> Dict[str, Any]:
    """Generate and return the 18-pair balanced schedule across 3 sessions."""
    schedule_pairs = []
    global_pair_id = 0

    for session_idx, seed in enumerate(session_seeds):
        session_pairs = []
        for b in BATCH_SIZES:
            # Pair 1: A then B
            session_pairs.append({
                "session": session_idx,
                "batch_size": b,
                "treatment_order": "A_first",
                "members": [
                    {"position": 0, "treatment": "A", "warmup_chunk_size": 50, "expected_warmup_requests": 1},
                    {"position": 1, "treatment": "B", "warmup_chunk_size": 1, "expected_warmup_requests": 50},
                ],
            })
            # Pair 2: B then A
            session_pairs.append({
                "session": session_idx,
                "batch_size": b,
                "treatment_order": "B_first",
                "members": [
                    {"position": 0, "treatment": "B", "warmup_chunk_size": 1, "expected_warmup_requests": 50},
                    {"position": 1, "treatment": "A", "warmup_chunk_size": 50, "expected_warmup_requests": 1},
                ],
            })

        # Reproducibly shuffle session pairs using the recorded session seed
        rng = random.Random(seed)
        rng.shuffle(session_pairs)

        for p in session_pairs:
            p["pair_id"] = global_pair_id
            for m in p["members"]:
                pos = m["position"]
                trt = m["treatment"]
                chunk = m["warmup_chunk_size"]
                b = p["batch_size"]
                json_path = (destination / f"report_pair_{global_pair_id:03d}_pos{pos}_{trt}_b{b}.json").resolve()
                m["json_report_path"] = str(json_path)
                m["argv"] = [
                    str(driver_bin),
                    "--scenario", "standalone-batch",
                    "--engine", "compact-bfs",
                    "--batch-size", str(b),
                    "--runs", "1",
                    "--spawn-server",
                    "--server-bin", str(server_bin),
                    "--batch-warmup-chunk-size", str(chunk),
                    "--json-out", str(json_path),
                ]
                m["cwd"] = str((cwd or WORKSPACE_DIR / "knotrel").resolve())
                m["env"] = {}
                m["cell_contract"] = {
                    "scenario": "standalone-batch",
                    "engine": "compact-bfs",
                    "requested_engine": "compact-bfs",
                    "effective_engine": "compact-bfs",
                    "nodes": 1000,
                    "node_count": 1000,
                    "seed": 42,
                    "batch_size": b,
                    "warmup_chunk_size": chunk,
                    "expected_warmup_requests": m["expected_warmup_requests"],
                }
            schedule_pairs.append(p)
            global_pair_id += 1

    return {
        "schema": "knotrel-batch-warmup-investigation-schedule-v1",
        "description": "18-pair balanced schedule comparing standalone-batch warmup chunk size 50 vs 1",
        "total_sessions": len(session_seeds),
        "session_seeds": session_seeds,
        "batch_sizes": BATCH_SIZES,
        "total_pairs": len(schedule_pairs),
        "total_invocations": len(schedule_pairs) * 2,
        "pairs": schedule_pairs,
    }


def validate_provenance_and_binaries(
    driver_bin: Path = DRIVER_BINARY_PATH,
    server_bin: Path = SERVER_BINARY_PATH,
) -> Dict[str, Any]:
    """Strictly verify binary and lockfile provenance."""
    if not server_bin.is_file():
        raise QualificationBlockerError(f"Baseline server binary not found at {server_bin}")
    actual_server_sha = compute_sha256(server_bin)
    if actual_server_sha != SERVER_SHA256:
        raise QualificationBlockerError(f"Server binary SHA-256 mismatch: {actual_server_sha} != {SERVER_SHA256}")

    if not driver_bin.is_file():
        raise QualificationBlockerError(f"Candidate driver binary not found at {driver_bin}")
    actual_driver_sha = compute_sha256(driver_bin)
    if actual_driver_sha != DRIVER_SHA256:
        raise QualificationBlockerError(f"Driver binary SHA-256 mismatch: {actual_driver_sha} != {DRIVER_SHA256}")

    # Check preserved release driver untouched
    if not ACCEPTED_RELEASE_DRIVER_PATH.is_file():
        raise QualificationBlockerError(f"Accepted release driver not found at {ACCEPTED_RELEASE_DRIVER_PATH}")
    rel_sha = compute_sha256(ACCEPTED_RELEASE_DRIVER_PATH)
    if rel_sha != ACCEPTED_RELEASE_DRIVER_SHA256:
        raise QualificationBlockerError(f"Accepted release driver was modified: {rel_sha} != {ACCEPTED_RELEASE_DRIVER_SHA256}")

    # Check preserved core harness untouched
    if not FROZEN_BENCHMARKS_PATH.is_file():
        raise QualificationBlockerError(f"Frozen benchmarks binary not found at {FROZEN_BENCHMARKS_PATH}")
    bench_sha = compute_sha256(FROZEN_BENCHMARKS_PATH)
    if bench_sha != FROZEN_BENCHMARKS_SHA256:
        raise QualificationBlockerError(f"Frozen benchmarks binary was modified: {bench_sha} != {FROZEN_BENCHMARKS_SHA256}")

    # Check working trees for unexpected unstaged changes
    for repo in [WORKSPACE_DIR / "knotrel", WORKSPACE_DIR / "knotrel-benchmarks"]:
        res = subprocess.run(["git", "-C", str(repo), "diff", "--name-only"], capture_output=True, text=True)
        if res.returncode != 0:
            raise QualificationBlockerError(f"Failed to check git diff in {repo}: {res.stderr}")
        unstaged = res.stdout.strip().splitlines()
        if unstaged:
            raise QualificationBlockerError(f"Unexpected unstaged modifications in {repo}: {unstaged}")

    return {
        "server_bin": str(server_bin),
        "server_sha256": actual_server_sha,
        "driver_bin": str(driver_bin),
        "driver_sha256": actual_driver_sha,
        "accepted_release_driver_sha256": rel_sha,
        "frozen_benchmarks_sha256": bench_sha,
    }


def execute_investigation(
    destination: Path,
    driver_bin: Path = DRIVER_BINARY_PATH,
    server_bin: Path = SERVER_BINARY_PATH,
    enforce_host: bool = True,
    pre_quiet_seconds: float = PRE_SESSION_QUIET_SECONDS,
    inter_cooldown_seconds: float = INTER_SESSION_COOLDOWN_SECONDS,
    check_provenance: bool = True,
    cwd: Optional[Path] = None,
) -> int:
    """Execute the complete standalone-batch warmup investigation campaign."""
    destination = destination.resolve()
    if destination.exists():
        raise QualificationBlockerError(f"Destination directory already exists: {destination}")

    start_monotonic_ns = time.monotonic_ns()
    start_unix_ns = time.time_ns()

    # Preflight host validation
    initial_host = host_state()
    if enforce_host:
        h_ok, h_err = validate_host_state(initial_host, enforce_ac=True)
        if not h_ok:
            raise EnvironmentalInvalidationError(f"Host preflight validation failed: {h_err}")

    # Provenance verification
    prov_meta = {}
    if check_provenance:
        prov_meta = validate_provenance_and_binaries(driver_bin, server_bin)

    destination.mkdir(parents=True, exist_ok=False)

    schedule_data = generate_schedule(destination, driver_bin, server_bin, cwd=cwd)
    p0.save_json(destination / "schedule.json", schedule_data)

    metadata: Dict[str, Any] = {
        "schema": "knotrel-batch-warmup-investigation-metadata-v1",
        "status": "in_progress",
        "destination": str(destination),
        "start_monotonic_ns": start_monotonic_ns,
        "start_unix_ns": start_unix_ns,
        "overall_deadline_seconds": OVERALL_CAMPAIGN_DEADLINE_SECONDS,
        "per_process_timeout_seconds": PER_PROCESS_TIMEOUT_SECONDS,
        "peak_rss_ceiling_bytes": PEAK_RSS_CEILING_BYTES,
        "disk_ceiling_bytes": DISK_CEILING_BYTES,
        "pre_session_quiet_seconds": pre_quiet_seconds,
        "inter_session_cooldown_seconds": inter_cooldown_seconds,
        "total_pairs": len(schedule_data["pairs"]),
        "total_invocations": schedule_data["total_invocations"],
        "completed_pairs": 0,
        "completed_observations": 0,
        "session_seeds": SESSION_SEEDS,
        "provenance": prov_meta,
        "initial_host": initial_host,
        "session_host_states": [],
    }
    p0.save_json(destination / "run_metadata.json", metadata)

    observations: List[Dict[str, Any]] = []

    try:
        # Group pairs by session
        sessions_map: Dict[int, List[Dict[str, Any]]] = {}
        for p in schedule_data["pairs"]:
            sessions_map.setdefault(p["session"], []).append(p)

        for session_idx in sorted(sessions_map.keys()):
            # Enforce inter-session cooldown
            if session_idx > 0 and inter_cooldown_seconds > 0:
                print(f"[Session {session_idx}] Cooldown: waiting {inter_cooldown_seconds}s...")
                time.sleep(inter_cooldown_seconds)

            # Pre-session host validation
            pre_host = host_state()
            if enforce_host:
                h_ok, h_err = validate_host_state(pre_host, baseline=initial_host, enforce_ac=True)
                if not h_ok:
                    raise EnvironmentalInvalidationError(
                        f"Environmental invalidation before session {session_idx}: {h_err}"
                    )

            # Enforce pre-session quiet period
            if pre_quiet_seconds > 0:
                print(f"[Session {session_idx}] Quiet period: waiting {pre_quiet_seconds}s...")
                time.sleep(pre_quiet_seconds)

            session_host_entry = {
                "session_idx": session_idx,
                "pre_session_host": pre_host,
                "post_session_host": None,
            }

            # Execute pairs in this session
            for pair in sessions_map[session_idx]:
                pair_record = {
                    "pair_id": pair["pair_id"],
                    "session": session_idx,
                    "batch_size": pair["batch_size"],
                    "treatment_order": pair["treatment_order"],
                    "observations": [],
                }

                for member in pair["members"]:
                    pos = member["position"]
                    trt = member["treatment"]
                    chunk = member["warmup_chunk_size"]
                    b = pair["batch_size"]
                    json_path = Path(member["json_report_path"])

                    # Check overall deadline
                    elapsed_campaign_s = (time.monotonic_ns() - start_monotonic_ns) / 1e9
                    if elapsed_campaign_s > OVERALL_CAMPAIGN_DEADLINE_SECONDS:
                        raise QualificationBlockerError(
                            f"Overall campaign deadline exceeded: {elapsed_campaign_s:.2f}s > "
                            f"{OVERALL_CAMPAIGN_DEADLINE_SECONDS}s"
                        )

                    # Execute child measurement
                    capture_limit = campaign_capture_limit(destination, DISK_CEILING_BYTES)
                    obs_res = observe_child(
                        argv=member["argv"],
                        cwd=member["cwd"],
                        env=member["env"],
                        timeout_seconds=PER_PROCESS_TIMEOUT_SECONDS,
                        is_core=False,
                        output_limit_bytes=capture_limit,
                    )

                    obs_item: Dict[str, Any] = {
                        "pair_id": pair["pair_id"],
                        "session": session_idx,
                        "batch_size": b,
                        "position": pos,
                        "treatment": trt,
                        "warmup_chunk_size": chunk,
                        "expected_warmup_requests": member["expected_warmup_requests"],
                        "launch_monotonic_ns": obs_res["launch_monotonic_ns"],
                        "completion_monotonic_ns": obs_res["completion_monotonic_ns"],
                        "launch_unix_ns": obs_res["launch_unix_ns"],
                        "completion_unix_ns": obs_res["completion_unix_ns"],
                        "wall_duration_ns": obs_res["wall_duration_ns"],
                        "exit_code": obs_res["exit_code"],
                        "timed_out": obs_res["timed_out"],
                        "argv": member["argv"],
                        "cwd": member["cwd"],
                        "env": member["env"],
                        "json_report_path": str(json_path),
                        "stdout": obs_res["stdout"],
                        "raw_stderr": obs_res["raw_stderr"],
                        "peak_rss_bytes": obs_res["peak_rss_bytes"],
                        "status": "pending_validation",
                        "error": None,
                        "parsed_metrics": None,
                    }
                    obs_item["capture"] = {key: value for key, value in obs_res.items() if key in (
                        "status", "failure_reason", "output_limit_exceeded", "direct_child_reaped",
                        "output_limit_bytes", "stdout_bytes_captured", "stderr_bytes_captured",
                        "stdout_bytes_base64", "stderr_bytes_base64")}
                    pair_record["observations"].append(obs_item)

                    pair_filename = (
                        destination / f"pair_{pair['pair_id']:03d}_b{b}_{pair['treatment_order']}.json"
                    )

                    # Check timeout
                    if obs_res["timed_out"]:
                        err_msg = f"Invocation timed out after {PER_PROCESS_TIMEOUT_SECONDS}s"
                        obs_item["status"] = "timed_out"
                        obs_item["error"] = err_msg
                        p0.save_json(pair_filename, pair_record)
                        raise ProcessExecutionError(err_msg)

                    # Check exit code
                    if obs_res["exit_code"] != 0:
                        err_msg = f"Child exited with nonzero status {obs_res['exit_code']}: {obs_res['raw_stderr']}"
                        obs_item["status"] = "process_error"
                        obs_item["error"] = err_msg
                        p0.save_json(pair_filename, pair_record)
                        raise ProcessExecutionError(err_msg)

                    # Check report file exists
                    capture_error = capture_failure_reason(obs_res)
                    if capture_error:
                        obs_item.update(status="process_error", error=capture_error)
                        p0.save_json(pair_filename, pair_record)
                        raise ProcessExecutionError(capture_error)
                    if not json_path.is_file():
                        err_msg = f"Expected JSON report file was not written: {json_path}"
                        obs_item["status"] = "missing_report"
                        obs_item["error"] = err_msg
                        p0.save_json(pair_filename, pair_record)
                        raise QualificationBlockerError(err_msg)

                    # Parse and qualify JSON report
                    try:
                        if json_path.stat().st_size > DEFAULT_STREAM_LIMIT_BYTES:
                            raise QualificationBlockerError("HTTP JSON report file exceeds parser byte limit")
                        report_data = p0.read_json(json_path)
                        parsed = parse_http_batch_json(
                            report_data,
                            member["cell_contract"],
                            expected_server_sha=prov_meta.get("server_sha256", SERVER_SHA256),
                        )
                        obs_item["parsed_metrics"] = parsed
                        obs_item["status"] = "parsed_valid"
                    except Exception as e:
                        obs_item["status"] = "qualification_blocker"
                        obs_item["error"] = str(e)
                        p0.save_json(pair_filename, pair_record)
                        raise

                    # Check retrospective peak RSS ceiling
                    if obs_res["peak_rss_bytes"] and obs_res["peak_rss_bytes"] > PEAK_RSS_CEILING_BYTES:
                        err_msg = f"Peak RSS exceeded: {obs_res['peak_rss_bytes']} > {PEAK_RSS_CEILING_BYTES}"
                        obs_item["status"] = "rss_ceiling_violation"
                        obs_item["error"] = err_msg
                        p0.save_json(pair_filename, pair_record)
                        raise QualificationBlockerError(err_msg)

                    observations.append(obs_item)
                    p0.save_json(pair_filename, pair_record)
                    metadata["completed_observations"] = len(observations)
                    metadata["completed_pairs"] = len(observations) // 2
                    p0.save_json(destination / "run_metadata.json", metadata)

            # Post-session host validation
            post_host = host_state()
            session_host_entry["post_session_host"] = post_host
            metadata["session_host_states"].append(session_host_entry)
            p0.save_json(destination / "run_metadata.json", metadata)

            if enforce_host:
                h_ok, h_err = validate_host_state(post_host, baseline=initial_host, enforce_ac=True)
                if not h_ok:
                    raise EnvironmentalInvalidationError(
                        f"Environmental invalidation at session {session_idx} conclusion: {h_err}"
                    )

            # Check disk usage
            current_disk = directory_size_bytes(destination)
            if current_disk > DISK_CEILING_BYTES:
                raise QualificationBlockerError(
                    f"Disk ceiling exceeded: {current_disk} > {DISK_CEILING_BYTES} bytes"
                )

        # All 18 pairs successfully completed
        analysis_data = analyze_investigation(observations)
        p0.save_json(destination / "analysis.json", analysis_data)

        metadata["status"] = "completed"
        metadata["completion_monotonic_ns"] = time.monotonic_ns()
        metadata["completion_unix_ns"] = time.time_ns()
        p0.save_json(destination / "run_metadata.json", metadata)

        print(f"Investigation completed successfully. All {len(schedule_data['pairs'])} pairs verified.")
        return 0

    except QualificationBlockerError as e:
        metadata["status"] = "aborted_qualification_blocker"
        metadata["error"] = str(e)
        p0.save_json(destination / "run_metadata.json", metadata)
        raise
    except EnvironmentalInvalidationError as e:
        metadata["status"] = "aborted_environmental_invalidation"
        metadata["error"] = str(e)
        p0.save_json(destination / "run_metadata.json", metadata)
        raise
    except ProcessExecutionError as e:
        metadata["status"] = "aborted_process_execution_failure"
        metadata["error"] = str(e)
        p0.save_json(destination / "run_metadata.json", metadata)
        raise
    except Exception as e:
        metadata["status"] = "aborted_unexpected_exception"
        metadata["error"] = str(e)
        p0.save_json(destination / "run_metadata.json", metadata)
        raise


def analyze_investigation(observations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform offline statistical analysis comparing Treatment A and Treatment B per batch size."""
    by_batch: Dict[int, List[Dict[str, Any]]] = {}
    for obs in observations:
        b = obs["batch_size"]
        by_batch.setdefault(b, []).append(obs)

    batch_analyses = {}
    for b in BATCH_SIZES:
        obs_b = by_batch.get(b, [])
        # Separate treatments
        obs_a = [o for o in obs_b if o["treatment"] == "A"]
        obs_b_trt = [o for o in obs_b if o["treatment"] == "B"]

        # Extract primary metrics
        # Window duration (ms)
        win_a = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_a]
        win_b = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_b_trt]

        # Warmup duration (ms)
        warmup_a_ms = [o["parsed_metrics"]["exported_metrics"]["warmup_duration_ms"] for o in obs_a]
        warmup_b_ms = [o["parsed_metrics"]["exported_metrics"]["warmup_duration_ms"] for o in obs_b_trt]

        # Mean request latency (us)
        lat_a_us = [o["parsed_metrics"]["exported_metrics"]["request_latency_mean_us"] for o in obs_a]
        lat_b_us = [o["parsed_metrics"]["exported_metrics"]["request_latency_mean_us"] for o in obs_b_trt]

        # Process wall duration (ms)
        wall_a_ms = [o["wall_duration_ns"] / 1e6 for o in obs_a]
        wall_b_ms = [o["wall_duration_ns"] / 1e6 for o in obs_b_trt]

        def _stats(vals: List[float]) -> Dict[str, Any]:
            if not vals:
                return {}
            m = statistics.mean(vals)
            med = statistics.median(vals)
            s = statistics.stdev(vals) if len(vals) > 1 else 0.0
            cv = s / m if m != 0 else 0.0
            sorted_v = sorted(vals)
            n = len(sorted_v)
            mid = n // 2
            lower = sorted_v[:mid]
            upper = sorted_v[mid:] if n % 2 == 0 else sorted_v[mid + 1 :]
            q1 = statistics.median(lower) if lower else sorted_v[0]
            q3 = statistics.median(upper) if upper else sorted_v[-1]
            return {
                "count": len(vals),
                "mean": m,
                "median": med,
                "std": s,
                "cv": cv,
                "q1": q1,
                "q3": q3,
                "iqr": q3 - q1,
                "min": min(vals),
                "max": max(vals),
            }

        # Paired differences within each pair: diff = B - A, rel_diff = (B - A) / A
        pairs_dict: Dict[int, Dict[str, Any]] = {}
        for o in obs_b:
            pairs_dict.setdefault(o["pair_id"], {})[o["treatment"]] = o

        paired_deltas = []
        for pid, members in sorted(pairs_dict.items()):
            if "A" in members and "B" in members:
                ma = members["A"]
                mb = members["B"]
                wa = ma["parsed_metrics"]["exported_metrics"]["window_duration_ms"]
                wb = mb["parsed_metrics"]["exported_metrics"]["window_duration_ms"]
                raw_d = wb - wa
                rel_d = raw_d / wa if wa != 0 else 0.0
                sym_denom = (wa + wb) / 2.0
                sym_d = raw_d / sym_denom if sym_denom != 0 else 0.0
                log_r = math.log(wb / wa) if wa > 0 and wb > 0 else 0.0
                first_trt = "A" if ma["position"] == 0 else "B"
                paired_deltas.append({
                    "pair_id": pid,
                    "session": ma["session"],
                    "order": f"{first_trt}_first",
                    "val_A": wa,
                    "val_B": wb,
                    "diff_B_minus_A": raw_d,
                    "rel_diff": rel_d,
                    "sym_rel_diff": sym_d,
                    "log_ratio": log_r,
                })

        # Position effects within Treatment A and Treatment B
        pos0_a = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_a if o["position"] == 0]
        pos1_a = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_a if o["position"] == 1]
        pos0_b = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_b_trt if o["position"] == 0]
        pos1_b = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_b_trt if o["position"] == 1]

        # Session shifts
        sess_a = {}
        sess_b = {}
        for s_idx in [0, 1, 2]:
            s_obs_a = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_a if o["session"] == s_idx]
            s_obs_b = [o["parsed_metrics"]["exported_metrics"]["window_duration_ms"] for o in obs_b_trt if o["session"] == s_idx]
            sess_a[f"session_{s_idx}"] = _stats(s_obs_a)
            sess_b[f"session_{s_idx}"] = _stats(s_obs_b)

        batch_analyses[f"b{b}"] = {
            "batch_size": b,
            "treatment_A_window_ms": _stats(win_a),
            "treatment_B_window_ms": _stats(win_b),
            "treatment_A_warmup_ms": _stats(warmup_a_ms),
            "treatment_B_warmup_ms": _stats(warmup_b_ms),
            "treatment_A_req_latency_us": _stats(lat_a_us),
            "treatment_B_req_latency_us": _stats(lat_b_us),
            "treatment_A_wall_ms": _stats(wall_a_ms),
            "treatment_B_wall_ms": _stats(wall_b_ms),
            "paired_deltas": {
                "definition_raw": "B - A",
                "definition_rel": "(B - A) / A",
                "definition_sym": "(B - A) / ((A + B) / 2)",
                "pairs": paired_deltas,
                "mean_raw_diff": statistics.mean([d["diff_B_minus_A"] for d in paired_deltas]) if paired_deltas else 0.0,
                "median_raw_diff": statistics.median([d["diff_B_minus_A"] for d in paired_deltas]) if paired_deltas else 0.0,
                "mean_rel_diff": statistics.mean([d["rel_diff"] for d in paired_deltas]) if paired_deltas else 0.0,
                "median_rel_diff": statistics.median([d["rel_diff"] for d in paired_deltas]) if paired_deltas else 0.0,
            },
            "position_effects": {
                "treatment_A": {
                    "pos0_mean": statistics.mean(pos0_a) if pos0_a else 0.0,
                    "pos1_mean": statistics.mean(pos1_a) if pos1_a else 0.0,
                    "diff_p1_minus_p0": (statistics.mean(pos1_a) - statistics.mean(pos0_a)) if pos0_a and pos1_a else 0.0,
                },
                "treatment_B": {
                    "pos0_mean": statistics.mean(pos0_b) if pos0_b else 0.0,
                    "pos1_mean": statistics.mean(pos1_b) if pos1_b else 0.0,
                    "diff_p1_minus_p0": (statistics.mean(pos1_b) - statistics.mean(pos0_b)) if pos0_b and pos1_b else 0.0,
                },
            },
            "session_effects": {
                "treatment_A": sess_a,
                "treatment_B": sess_b,
            },
        }

    return {
        "schema": "knotrel-batch-warmup-investigation-analysis-v1",
        "methodological_disclaimer": (
            "Descriptive exploratory comparison of standalone-batch warmup configurations only. "
            "Treatment A uses 1 request of 50 queries; Treatment B uses 50 requests of 1 query. "
            "No algorithm improvement, release performance claim, or P0/M3.1/v0.3.0 milestone completion is asserted."
        ),
        "batch_analyses": batch_analyses,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path, help="New evidence destination directory.")
    parser.add_argument("--execute", action="store_true", help="Explicit confirmation required to execute the live investigation.")
    parser.add_argument("--dry-run", action="store_true", help="Validate schedule and provenance without running benchmarks.")
    parser.add_argument("--skip-host-checks", action="store_true", help="Skip strict AC power and thermal validation (for unit testing).")
    parser.add_argument("--skip-provenance-checks", action="store_true", help="Skip binary provenance checks (for unit testing).")
    parser.add_argument("--driver-bin", type=Path, default=DRIVER_BINARY_PATH, help="Path to measure_e2e binary.")
    parser.add_argument("--server-bin", type=Path, default=SERVER_BINARY_PATH, help="Path to knotrel-server binary.")
    parser.add_argument("--cwd", type=Path, default=WORKSPACE_DIR / "knotrel", help="Runtime working directory.")

    args = parser.parse_args()

    if not args.dry_run and not args.execute:
        parser.error("Either --dry-run or --execute must be specified.")

    if args.dry_run:
        print("=== BATCH WARMUP INVESTIGATION (DRY-RUN) ===")
        prov = validate_provenance_and_binaries(args.driver_bin, args.server_bin) if not args.skip_provenance_checks else {}
        print("Provenance verified:", prov)
        h = host_state()
        if not args.skip_host_checks:
            ok, err = validate_host_state(h, enforce_ac=True)
            if not ok:
                print(f"Host validation failed: {err}")
                return 1
            print("Host validation passed (AC power, thermal headroom, 0 competing workloads).")
        sched = generate_schedule(args.destination, args.driver_bin, args.server_bin, cwd=args.cwd)
        print(f"Schedule generated: {sched['total_pairs']} pairs across {sched['total_sessions']} sessions.")
        print("Dry run complete. No benchmarks were run.")
        return 0

    return execute_investigation(
        destination=args.destination,
        driver_bin=args.driver_bin,
        server_bin=args.server_bin,
        enforce_host=not args.skip_host_checks,
        check_provenance=not args.skip_provenance_checks,
        cwd=args.cwd,
    )


if __name__ == "__main__":
    sys.exit(main())
