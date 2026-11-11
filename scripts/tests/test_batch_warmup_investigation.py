#!/usr/bin/env python3
"""Tests for Standalone Batch Warmup Investigation Runner."""

import copy
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
sys.path.insert(0, str(SCRIPTS_DIR))

import run_batch_warmup_investigation as inv
import run_p0_aa as p0


class TestBatchWarmupInvestigation(unittest.TestCase):
    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def test_schedule_generation_balance(self):
        """Schedule must generate exactly 18 pairs across 3 sessions with balanced treatments."""
        sched = inv.generate_schedule(self.tmpdir / "dest")
        self.assertEqual(sched["total_sessions"], 3)
        self.assertEqual(sched["total_pairs"], 18)
        self.assertEqual(sched["total_invocations"], 36)

        # Count pairs per batch size and order
        counts = {}
        for p in sched["pairs"]:
            b = p["batch_size"]
            order = p["treatment_order"]
            counts[(b, order)] = counts.get((b, order), 0) + 1

            # Check member contracts
            self.assertEqual(len(p["members"]), 2)
            m0, m1 = p["members"][0], p["members"][1]
            if order == "A_first":
                self.assertEqual(m0["treatment"], "A")
                self.assertEqual(m0["warmup_chunk_size"], 50)
                self.assertEqual(m0["expected_warmup_requests"], 1)
                self.assertIn("--batch-warmup-chunk-size", m0["argv"])
                self.assertEqual(m0["argv"][m0["argv"].index("--batch-warmup-chunk-size") + 1], "50")

                self.assertEqual(m1["treatment"], "B")
                self.assertEqual(m1["warmup_chunk_size"], 1)
                self.assertEqual(m1["expected_warmup_requests"], 50)
                self.assertIn("--batch-warmup-chunk-size", m1["argv"])
                self.assertEqual(m1["argv"][m1["argv"].index("--batch-warmup-chunk-size") + 1], "1")
            else:
                self.assertEqual(m0["treatment"], "B")
                self.assertEqual(m0["warmup_chunk_size"], 1)
                self.assertEqual(m1["treatment"], "A")
                self.assertEqual(m1["warmup_chunk_size"], 50)

        # Every batch size in {8, 64, 256} must have exactly 3 A_first and 3 B_first pairs
        for b in [8, 64, 256]:
            self.assertEqual(counts.get((b, "A_first")), 3)
            self.assertEqual(counts.get((b, "B_first")), 3)

    def test_fake_process_orchestration_success(self):
        """Execute runner with a mock executable that writes valid JSON for both chunk sizes."""
        fake_driver = self.tmpdir / "mock_driver.py"
        fake_driver.write_text(
            """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
json_out = Path(args[args.index("--json-out") + 1])
batch_size = int(args[args.index("--batch-size") + 1])
chunk_size = int(args[args.index("--batch-warmup-chunk-size") + 1])
req_count = (50 + chunk_size - 1) // chunk_size

full_b = 2000 // batch_size
rem_b = 2000 % batch_size
req_count_b = full_b + (1 if rem_b > 0 else 0)

report = {
    "schema_version": "measure_e2e.batch.v1",
    "driver": {"name": "measure_e2e", "version": "0.3.0", "build_profile": "release"},
    "server_provenance": {
        "binary_path": "/path/to/server",
        "binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        "instance_id": "srv-fake-123"
    },
    "configuration": {
        "scenario": "standalone-batch",
        "trace_identity": "deterministic_500_round_link_cut_reversal",
        "node_count": 1000,
        "seed": 42,
        "batch_size": batch_size,
        "total_logical_operations": 2000,
        "link_operations": 500,
        "cut_operations": 500,
        "query_operations": 1000,
        "actual_request_count": req_count_b,
        "full_batches": full_b,
        "partial_batch_size": rem_b if rem_b > 0 else None,
        "requested_engine": "compact-bfs",
        "effective_engine": "compact-bfs",
        "warmup_chunk_size": chunk_size,
        "runs": 1
    },
    "runs": [{
        "run_index": 1,
        "seed": 42,
        "setup": {"duration_ns": 1000000, "duration_ms": 1.0, "created_nodes": 1000, "initial_state_version": "1000"},
        "warmup": {
            "duration_ns": 500000 * req_count,
            "duration_ms": 0.5 * req_count,
            "query_count": 50,
            "request_count": req_count,
            "post_warmup_state_version": "1000"
        },
        "measurement_window": {
            "duration_ns": 20000000,
            "duration_ms": 20.0,
            "total_logical_operations": 2000,
            "effective_mutations": 1000,
            "elapsed_window_ns_per_logical_op": 10000.0,
            "logical_ops_per_sec": 100000.0,
            "requests_per_sec": 12500.0
        },
        "request_latency": {
            "total_requests": req_count_b,
            "latency_ns": {"min": 50000, "mean": 100000, "p50": 95000, "p95": 150000, "p99": 180000, "max": 200000},
            "latency_us": {"min": 50.0, "mean": 100.0, "p50": 95.0, "p95": 150.0, "p99": 180.0, "max": 200.0}
        },
        "verification": {
            "all_items_matched": True,
            "total_verified_items": 2000,
            "expected_final_state_version": "2000",
            "actual_final_state_version": "2000",
            "final_node_count": 1000,
            "final_edge_count": 0
        },
        "memory": {
            "sampled_final_rss_kib": 6000,
            "sampled_final_rss_bytes": 6000 * 1024,
            "sampled_max_rss_kib": 6000,
            "sampled_max_rss_bytes": 6000 * 1024,
            "sampling_interval_ms": 25
        }
    }]
}
json_out.parent.mkdir(parents=True, exist_ok=True)
json_out.write_text(json.dumps(report))
sys.exit(0)
"""
        )
        fake_driver.chmod(0o755)

        dest = self.tmpdir / "investigation_dest"
        fake_host = {
            "platform": "darwin",
            "power": "Now drawing from 'AC Power'\n -InternalBattery-0 100%",
            "thermal": "Note: No thermal warning level has been recorded",
            "pmset_therm": {"exit_code": 0, "stdout": "No thermal warning", "stderr": ""},
            "pmset_sysload": {"exit_code": 0, "stdout": "thermal level = Great", "stderr": ""},
            "competing_workloads": [],
            "load_average": [1.0, 1.0, 1.0],
            "collector_nice": 0,
        }

        with patch("run_batch_warmup_investigation.host_state", return_value=fake_host):
            rc = inv.execute_investigation(
                destination=dest,
                driver_bin=fake_driver,
                cwd=self.tmpdir,
                enforce_host=False,
                pre_quiet_seconds=0.0,
                inter_cooldown_seconds=0.0,
                check_provenance=False,
            )
            self.assertEqual(rc, 0)

        # Verify artifacts
        self.assertTrue((dest / "schedule.json").is_file())
        self.assertTrue((dest / "run_metadata.json").is_file())
        self.assertTrue((dest / "analysis.json").is_file())

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "completed")
        self.assertEqual(meta["completed_pairs"], 18)
        self.assertEqual(meta["completed_observations"], 36)

        # Check an individual pair
        pair0 = p0.read_json(dest / f"pair_000_b{meta['session_seeds'][0] and 8 or 8}_{'A_first'}.json" if (dest / "pair_000_b8_A_first.json").is_file() else list(dest.glob("pair_000_*.json"))[0])
        self.assertEqual(len(pair0["observations"]), 2)
        obs0 = pair0["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertIn("warmup_chunk_size", obs0)

        # Check analysis output
        analysis = p0.read_json(dest / "analysis.json")
        self.assertIn("batch_analyses", analysis)
        self.assertIn("b8", analysis["batch_analyses"])
        self.assertIn("b64", analysis["batch_analyses"])
        self.assertIn("b256", analysis["batch_analyses"])
        b8 = analysis["batch_analyses"]["b8"]
        self.assertEqual(len(b8["paired_deltas"]["pairs"]), 6)

    def test_fake_process_failure_stops_and_preserves_evidence(self):
        """When child fails, runner stops immediately without retrying and preserves evidence."""
        failing_driver = self.tmpdir / "failing_driver.py"
        failing_driver.write_text(
            """#!/usr/bin/env python3
import sys
sys.stderr.write("Fatal crash in driver\\n")
sys.exit(1)
"""
        )
        failing_driver.chmod(0o755)

        dest = self.tmpdir / "failing_dest"
        fake_host = {
            "platform": "darwin",
            "power": "Now drawing from 'AC Power'",
            "thermal": "clean",
            "pmset_therm": {"exit_code": 0, "stdout": "", "stderr": ""},
            "pmset_sysload": {"exit_code": 0, "stdout": "", "stderr": ""},
            "competing_workloads": [],
            "load_average": [1.0, 1.0, 1.0],
            "collector_nice": 0,
        }

        with patch("run_batch_warmup_investigation.host_state", return_value=fake_host):
            with self.assertRaises(inv.ProcessExecutionError):
                inv.execute_investigation(
                    destination=dest,
                    driver_bin=failing_driver,
                    cwd=self.tmpdir,
                    enforce_host=False,
                    pre_quiet_seconds=0.0,
                    inter_cooldown_seconds=0.0,
                    check_provenance=False,
                )

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_process_execution_failure")
        self.assertEqual(meta["completed_observations"], 0)

    def test_mismatched_warmup_chunk_rejected(self):
        """When a child produces a report with mismatched warmup_chunk_size, runner aborts."""
        mismatched_driver = self.tmpdir / "mismatched_driver.py"
        mismatched_driver.write_text(
            """#!/usr/bin/env python3
import json
import sys
from pathlib import Path

args = sys.argv[1:]
json_out = Path(args[args.index("--json-out") + 1])
batch_size = int(args[args.index("--batch-size") + 1])
# Deliberately emit chunk 8 regardless of requested chunk size
chunk_size = 8
req_count = 7

full_b = 2000 // batch_size
rem_b = 2000 % batch_size
req_count_b = full_b + (1 if rem_b > 0 else 0)

report = {
    "schema_version": "measure_e2e.batch.v1",
    "driver": {"name": "measure_e2e", "version": "0.3.0", "build_profile": "release"},
    "server_provenance": {
        "binary_path": "/path/to/server",
        "binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        "instance_id": "srv-fake-123"
    },
    "configuration": {
        "scenario": "standalone-batch",
        "trace_identity": "deterministic_500_round_link_cut_reversal",
        "node_count": 1000,
        "seed": 42,
        "batch_size": batch_size,
        "total_logical_operations": 2000,
        "link_operations": 500,
        "cut_operations": 500,
        "query_operations": 1000,
        "actual_request_count": req_count_b,
        "full_batches": full_b,
        "partial_batch_size": rem_b if rem_b > 0 else None,
        "requested_engine": "compact-bfs",
        "effective_engine": "compact-bfs",
        "warmup_chunk_size": chunk_size,
        "runs": 1
    },
    "runs": [{
        "run_index": 1,
        "seed": 42,
        "setup": {"duration_ns": 1000000, "duration_ms": 1.0, "created_nodes": 1000, "initial_state_version": "1000"},
        "warmup": {
            "duration_ns": 500000 * req_count,
            "duration_ms": 0.5 * req_count,
            "query_count": 50,
            "request_count": req_count,
            "post_warmup_state_version": "1000"
        },
        "measurement_window": {
            "duration_ns": 20000000,
            "duration_ms": 20.0,
            "total_logical_operations": 2000,
            "effective_mutations": 1000,
            "elapsed_window_ns_per_logical_op": 10000.0,
            "logical_ops_per_sec": 100000.0,
            "requests_per_sec": 12500.0
        },
        "request_latency": {
            "total_requests": req_count_b,
            "latency_ns": {"min": 50000, "mean": 100000, "p50": 95000, "p95": 150000, "p99": 180000, "max": 200000},
            "latency_us": {"min": 50.0, "mean": 100.0, "p50": 95.0, "p95": 150.0, "p99": 180.0, "max": 200.0}
        },
        "verification": {
            "all_items_matched": True,
            "total_verified_items": 2000,
            "expected_final_state_version": "2000",
            "actual_final_state_version": "2000",
            "final_node_count": 1000,
            "final_edge_count": 0
        },
        "memory": {
            "sampled_final_rss_kib": 6000,
            "sampled_final_rss_bytes": 6000 * 1024,
            "sampled_max_rss_kib": 6000,
            "sampled_max_rss_bytes": 6000 * 1024,
            "sampling_interval_ms": 25
        }
    }]
}
json_out.parent.mkdir(parents=True, exist_ok=True)
json_out.write_text(json.dumps(report))
sys.exit(0)
"""
        )
        mismatched_driver.chmod(0o755)

        dest = self.tmpdir / "mismatched_dest"
        fake_host = {
            "platform": "darwin",
            "power": "Now drawing from 'AC Power'",
            "thermal": "clean",
            "pmset_therm": {"exit_code": 0, "stdout": "", "stderr": ""},
            "pmset_sysload": {"exit_code": 0, "stdout": "", "stderr": ""},
            "competing_workloads": [],
            "load_average": [1.0, 1.0, 1.0],
            "collector_nice": 0,
        }

        with patch("run_batch_warmup_investigation.host_state", return_value=fake_host):
            with self.assertRaises(inv.QualificationBlockerError):
                inv.execute_investigation(
                    destination=dest,
                    driver_bin=mismatched_driver,
                    cwd=self.tmpdir,
                    enforce_host=False,
                    pre_quiet_seconds=0.0,
                    inter_cooldown_seconds=0.0,
                    check_provenance=False,
                )

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_qualification_blocker")
        self.assertIn("Warmup chunk size does not match", meta["error"])


if __name__ == "__main__":
    unittest.main()
