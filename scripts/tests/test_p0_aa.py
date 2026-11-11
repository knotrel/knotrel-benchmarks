"""Automated test suite for the Bounded P0 A/A Pilot Collector.

Tests cover:
- Valid schedule and dry-run launching no children or creating directories.
- CLI argument validation and safety requirements.
- Provenance verification: binary SHA-256, Git revisions, permitted staged Cargo.lock.
- Inconsistent inputs: schema, duplicate IDs, counts, label imbalance, argv/cwd/env mismatch.
- Output parsers: core JSON report and actual HTTP Markdown report fixtures.
- Strict parser tightening: exact operation counts, schema, 16-hex fingerprint,
  rejecting 0/0 query count, non-finite/negative metrics, and never substituting zero.
- Correctness disagreement (oracle agreement < 100%) and non-zero exit codes.
- Per-process timeout, monotonic overall deadline expiration, and process group teardown.
- Descendant process cleanup upon timeout / cancellation.
- Environmental invalidations: battery power, sleep/wake, thermal throttling, competing builds.
- Undefined HostPreconditionError fix and strict thermal requirement enforcement.
- Immediate observation persistence before parsing/raising; partial evidence preservation.
- Full end-to-end integration test with real fake processes traversing observe_child()
  and execute_pilot() without simulating the dictionary returned by the helper.
"""

from __future__ import annotations

import contextlib
import atexit
import copy
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import _thread
import threading
import time
import unittest
from unittest.mock import MagicMock, patch

# Sibling imports
SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import run_p0_aa as p0


from synthetic_collector_inputs import write_inputs, synthetic_git_command

SYNTHETIC_INPUTS = tempfile.TemporaryDirectory(prefix="knotrel-collector-fixtures-")
atexit.register(SYNTHETIC_INPUTS.cleanup)
EVIDENCE_ROOT = Path(SYNTHETIC_INPUTS.name)
write_inputs(EVIDENCE_ROOT)
PREFLIGHT_BUNDLE = EVIDENCE_ROOT
CORE_PREFLIGHT_BUNDLE = EVIDENCE_ROOT / "core"
PLAN_BUNDLE = EVIDENCE_ROOT / "pilot-plan"
PROPOSED_PLAN_BUNDLE = EVIDENCE_ROOT / "proposed-plan"
PROPOSED_MANIFEST_PATH = PROPOSED_PLAN_BUNDLE / "manifest.json"
PROPOSED_SCHEDULE_PATH = PROPOSED_PLAN_BUNDLE / "schedule.json"

CORE_SMOKE_JSON_PATH = CORE_PREFLIGHT_BUNDLE / "core_smoke_report.json"
HTTP_REPORT_MD_PATH = PREFLIGHT_BUNDLE / "http/measurement_small_release.md"
HTTP_STDOUT_LOG_PATH = PREFLIGHT_BUNDLE / "http/stdout.log"
SMOKE_B1_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "standalone_batch_smoke_b1.json"
p0.DEFAULT_MANIFEST_PATH = PLAN_BUNDLE / "manifest.json"
p0.DEFAULT_SCHEDULE_PATH = PLAN_BUNDLE / "schedule.json"


class DryRunAndConfigurationValidationTests(unittest.TestCase):
    """Tests for dry-run execution, CLI constraints, and strict configuration validation."""

    def setUp(self):
        git_patch = patch("run_p0_aa.command", side_effect=synthetic_git_command)
        git_patch.start()
        self.addCleanup(git_patch.stop)
        self.manifest = p0.read_json(p0.DEFAULT_MANIFEST_PATH)
        self.schedule = p0.read_json(p0.DEFAULT_SCHEDULE_PATH)

    def test_valid_schedule_and_dry_run_launching_no_children(self):
        """Dry-run must validate configuration and read-only provenance without spawning benchmarks."""
        with patch("run_p0_aa.observe_child") as mock_observe, tempfile.TemporaryDirectory() as tmpdir:
            test_dest = Path(tmpdir) / "should_not_be_created"
            rc = p0.run_dry_run(
                manifest_path=p0.DEFAULT_MANIFEST_PATH,
                schedule_path=p0.DEFAULT_SCHEDULE_PATH,
                destination=test_dest,
            )
            self.assertEqual(rc, 0)
            mock_observe.assert_not_called()
            self.assertFalse(test_dest.exists(), "Dry-run must not create destination directory")

    def test_cli_requires_dry_run_or_execute(self):
        """Collector must refuse execution unless --dry-run or --execute is passed."""
        with patch.object(sys, "argv", ["run_p0_aa.py"]):
            with self.assertRaises(SystemExit) as ctx:
                p0.main()
            self.assertEqual(ctx.exception.code, 2)

    def test_cli_execute_requires_destination(self):
        """Collector with --execute must require destination directory."""
        with patch.object(sys, "argv", ["run_p0_aa.py", "--execute"]):
            with self.assertRaises(SystemExit) as ctx:
                p0.main()
            self.assertEqual(ctx.exception.code, 2)

    def test_cli_execute_with_skip_provenance_checks_rejected(self):
        """Combining --execute with --skip-provenance-checks must be rejected without creating destination or launching processes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_dest = Path(tmpdir) / "should_never_exist"
            with patch("run_p0_aa.observe_child") as mock_observe:
                with patch.object(
                    sys,
                    "argv",
                    [
                        "run_p0_aa.py",
                        str(test_dest),
                        "--execute",
                        "--skip-provenance-checks",
                    ],
                ):
                    with self.assertRaises(SystemExit) as ctx:
                        p0.main()
                    self.assertEqual(ctx.exception.code, 2)
                mock_observe.assert_not_called()
                self.assertFalse(test_dest.exists(), "Rejected CLI combination must not create destination directory")

    def test_dry_run_output_reporting_when_provenance_verified(self):
        """When provenance checks are run, dry-run reports 100% valid configuration and provenance."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p0.run_dry_run(
                manifest_path=p0.DEFAULT_MANIFEST_PATH,
                schedule_path=p0.DEFAULT_SCHEDULE_PATH,
                check_provenance=True,
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("DRY-RUN COMPLETE: Configuration and provenance are 100% valid.", out)
        self.assertNotIn("provenance was NOT verified", out)
        self.assertIn("- HTTP Driver Metrics:    p50 and p95 exported; p99, mean, min, max marked unavailable (Markdown table)", out)

    def test_dry_run_output_reporting_when_provenance_skipped(self):
        """When provenance checks are skipped, dry-run reports structural validation passed and provenance NOT verified."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = p0.run_dry_run(
                manifest_path=PROPOSED_MANIFEST_PATH,
                schedule_path=PROPOSED_SCHEDULE_PATH,
                check_provenance=False,
            )
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("DRY-RUN COMPLETE: Structural validation passed; provenance was NOT verified.", out)
        self.assertNotIn("configuration and provenance are 100% valid", out)
        self.assertIn("! PROVENANCE NOT VERIFIED: Structural validation only (--skip-provenance-checks active)", out)
        self.assertIn("measure_e2e.v1", out)
        self.assertIn("measure_e2e.batch.v1", out)

    def test_proposed_manifest_structure_with_mocked_provenance_passes(self):
        """The actual proposed manifest structure passes validate_inputs(check_provenance=True) when driver hash is resolved."""
        manifest = p0.read_json(PROPOSED_MANIFEST_PATH)
        schedule = p0.read_json(PROPOSED_SCHEDULE_PATH)

        # Mock the pending driver hash so it doesn't fail on UNRESOLVED
        mock_driver_hash = "1" * 64
        manifest["provenance"]["binaries"]["measure_e2e"]["sha256"] = mock_driver_hash

        def mock_digest(p):
            p_str = str(p)
            if "measure_e2e" in p_str:
                return mock_driver_hash
            if "knotrel-server" in p_str:
                return manifest["provenance"]["binaries"]["knotrel_server"]["sha256"]
            if "knotrel-benchmarks" in p_str and "Cargo.lock" not in p_str:
                return manifest["provenance"]["binaries"]["knotrel_benchmarks"]["sha256"]
            if "knotrel-benchmarks/Cargo.lock" in p_str or ("benchmarks" in p_str and "Cargo.lock" in p_str):
                return manifest["provenance"]["lockfiles"]["benchmarks_lock_derived_sha256"]
            if "knotrel/Cargo.lock" in p_str or "Cargo.lock" in p_str:
                return manifest["provenance"]["lockfiles"]["knotrel_lock_sha256"]
            return "0" * 64

        def mock_command(args, cwd=None):
            if args == ["git", "rev-parse", "HEAD"]:
                if "benchmarks" in str(cwd):
                    return manifest["provenance"]["knotrel_benchmarks_commit"]
                return manifest["provenance"]["knotrel_baseline_commit"]
            if args == ["git", "status", "--porcelain"]:
                return ""
            if args == ["git", "diff", "--name-only"]:
                return ""
            if args == ["git", "diff", "--cached", "--name-only"]:
                return "Cargo.lock"
            return ""

        with patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "is_dir", return_value=True), \
             patch("os.access", return_value=True), \
             patch("run_p0_aa.digest", side_effect=mock_digest), \
             patch("run_p0_aa.command", side_effect=mock_command):
            val = p0.validate_inputs(manifest, schedule, check_provenance=True)
            self.assertEqual(val["status"], "valid")
            self.assertEqual(val["total_cells"], 17)
            self.assertEqual(val["total_pairs"], 102)
            self.assertEqual(val["total_measured_runs"], 204)
            self.assertEqual(val["total_process_launches"], 324)

    def test_lockfile_provenance_validation_and_rejection(self):
        """Omission of lockfiles object or required lockfile hash fields raises ConfigurationValidationError."""
        manifest = p0.read_json(PROPOSED_MANIFEST_PATH)
        schedule = p0.read_json(PROPOSED_SCHEDULE_PATH)
        mock_driver_hash = "1" * 64
        manifest["provenance"]["binaries"]["measure_e2e"]["sha256"] = mock_driver_hash

        def mock_digest(p):
            p_str = str(p)
            if "measure_e2e" in p_str:
                return mock_driver_hash
            if "knotrel-server" in p_str:
                return manifest["provenance"]["binaries"]["knotrel_server"]["sha256"]
            if "knotrel-benchmarks" in p_str and "Cargo.lock" not in p_str:
                return manifest["provenance"]["binaries"]["knotrel_benchmarks"]["sha256"]
            if "knotrel-benchmarks/Cargo.lock" in p_str or ("benchmarks" in p_str and "Cargo.lock" in p_str):
                return manifest["provenance"]["lockfiles"]["benchmarks_lock_derived_sha256"]
            if "knotrel/Cargo.lock" in p_str or "Cargo.lock" in p_str:
                return manifest["provenance"]["lockfiles"]["knotrel_lock_sha256"]
            return "0" * 64

        def mock_command(args, cwd=None):
            if args == ["git", "rev-parse", "HEAD"]:
                if "benchmarks" in str(cwd):
                    return manifest["provenance"]["knotrel_benchmarks_commit"]
                return manifest["provenance"]["knotrel_baseline_commit"]
            if args == ["git", "status", "--porcelain"]:
                return ""
            if args == ["git", "diff", "--name-only"]:
                return ""
            if args == ["git", "diff", "--cached", "--name-only"]:
                return "Cargo.lock"
            return ""

        # 1. Complete omission of lockfiles object
        m1 = copy.deepcopy(manifest)
        del m1["provenance"]["lockfiles"]
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "is_dir", return_value=True), \
             patch("os.access", return_value=True), \
             patch("run_p0_aa.digest", side_effect=mock_digest), \
             patch("run_p0_aa.command", side_effect=mock_command):
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(m1, schedule, check_provenance=True)
            self.assertIn("Manifest provenance missing required 'lockfiles' object", str(ctx.exception))

        # 2. Omission of knotrel_lock_sha256
        m2 = copy.deepcopy(manifest)
        del m2["provenance"]["lockfiles"]["knotrel_lock_sha256"]
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "is_dir", return_value=True), \
             patch("os.access", return_value=True), \
             patch("run_p0_aa.digest", side_effect=mock_digest), \
             patch("run_p0_aa.command", side_effect=mock_command):
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(m2, schedule, check_provenance=True)
            self.assertIn("knotrel_lock_sha256", str(ctx.exception))

        # 3. Omission of benchmarks_lock_derived_sha256
        m3 = copy.deepcopy(manifest)
        del m3["provenance"]["lockfiles"]["benchmarks_lock_derived_sha256"]
        with patch.object(Path, "is_file", return_value=True), \
             patch.object(Path, "is_dir", return_value=True), \
             patch("os.access", return_value=True), \
             patch("run_p0_aa.digest", side_effect=mock_digest), \
             patch("run_p0_aa.command", side_effect=mock_command):
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(m3, schedule, check_provenance=True)
            self.assertIn("benchmarks_lock_derived_sha256", str(ctx.exception))

    def test_identity_hash_mismatch_rejected(self):
        """Mutated binary hash in manifest must fail validation with actionable error."""
        manifest = copy.deepcopy(self.manifest)
        manifest["provenance"]["binaries"]["knotrel_benchmarks"]["sha256"] = "0" * 64
        with self.assertRaises(p0.ConfigurationValidationError) as ctx:
            p0.validate_inputs(manifest, self.schedule, check_provenance=True)
        self.assertIn("SHA-256 mismatch", str(ctx.exception))

    def test_git_revision_mismatch_rejected(self):
        """Mutated commit revision in manifest must fail validation."""
        manifest = copy.deepcopy(self.manifest)
        manifest["provenance"]["knotrel_baseline_commit"] = "0" * 40
        with self.assertRaises(p0.ConfigurationValidationError) as ctx:
            p0.validate_inputs(manifest, self.schedule, check_provenance=True)
        self.assertIn("Knotrel baseline commit mismatch", str(ctx.exception))

    def test_unexpected_dirty_git_state_rejected(self):
        """Unexpected git status in baseline knotrel checkout must fail validation."""
        with patch("run_p0_aa.command") as mock_cmd:
            def side_effect(args, cwd=None):
                if args == ["git", "rev-parse", "HEAD"]:
                    return self.manifest["provenance"]["knotrel_baseline_commit"]
                if args == ["git", "status", "--porcelain"]:
                    return "M some_dirty_file.rs"
                return ""
            mock_cmd.side_effect = side_effect
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)
            self.assertIn("must be clean", str(ctx.exception))

    def test_permitted_staged_cargo_lock_accepted(self):
        """The permitted staged Cargo.lock derivation in baseline benchmarks must be accepted."""
        summary = p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)
        self.assertEqual(summary["status"], "valid")
        self.assertEqual(summary["total_cells"], 31)
        self.assertEqual(summary["total_pairs"], 186)
        self.assertEqual(summary["total_measured_runs"], 372)

    def test_unexpected_unstaged_or_extra_staged_changes_rejected(self):
        """Any unstaged changes or extra staged files in baseline benchmarks must fail validation."""
        k_base = Path(self.manifest["provenance"]["knotrel_baseline_checkout"])
        b_base = Path(self.manifest["provenance"]["knotrel_benchmarks_checkout"])
        with patch("run_p0_aa.command") as mock_cmd:
            def side_effect(args, cwd=None):
                if args == ["git", "rev-parse", "HEAD"]:
                    if cwd == k_base:
                        return self.manifest["provenance"]["knotrel_baseline_commit"]
                    return self.manifest["provenance"]["knotrel_benchmarks_commit"]
                if args == ["git", "status", "--porcelain"]:
                    return ""
                if args == ["git", "diff", "--name-only"]:
                    return "unexpected_file.rs"
                if args == ["git", "diff", "--cached", "--name-only"]:
                    return "Cargo.lock"
                return ""
            mock_cmd.side_effect = side_effect
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)
            self.assertIn("Unexpected unstaged changes", str(ctx.exception))

    def test_invalid_counts_and_duplicate_ids_rejected(self):
        """Mutating total_cells, duplicate cell IDs, or pair IDs must fail validation."""
        # 1. Total cells mismatch
        m1 = copy.deepcopy(self.manifest)
        m1["pilot_design"]["total_cells"] = 30
        with self.assertRaises(p0.ConfigurationValidationError):
            p0.validate_inputs(m1, self.schedule, check_provenance=False)

        # 2. Duplicate cell_id
        m2 = copy.deepcopy(self.manifest)
        m2["pilot_design"]["cells"][1]["cell_id"] = m2["pilot_design"]["cells"][0]["cell_id"]
        with self.assertRaises(p0.ConfigurationValidationError):
            p0.validate_inputs(m2, self.schedule, check_provenance=False)

        # 3. Duplicate pair_id in schedule
        s1 = copy.deepcopy(self.schedule)
        s1["pairs"][1]["pair_id"] = 0
        with self.assertRaises(p0.ConfigurationValidationError):
            p0.validate_inputs(self.manifest, s1, check_provenance=False)

    def test_label_imbalance_rejected(self):
        """Cell with imbalanced labels (e.g. 4 A-then-Aprime instead of 3/3) must fail validation."""
        s = copy.deepcopy(self.schedule)
        cell0_id = self.manifest["pilot_design"]["cells"][0]["cell_id"]
        cell0_pairs = [p for p in s["pairs"] if p["cell_id"] == cell0_id]
        target = next(p for p in cell0_pairs if p["labels"] == ["Aprime", "A"])
        target["labels"] = ["A", "Aprime"]
        with self.assertRaises(p0.ConfigurationValidationError) as ctx:
            p0.validate_inputs(self.manifest, s, check_provenance=False)
        self.assertIn("label imbalance", str(ctx.exception))

    def test_mismatched_argv_cwd_env_rejected(self):
        """Any discrepancy between cell definition and scheduled pair must fail validation."""
        for field, bad_val in [
            ("cwd", "/tmp/wrong_cwd"),
            ("argv", ["wrong_bin", "--foo"]),
            ("env", {"WRONG": "1"}),
        ]:
            s = copy.deepcopy(self.schedule)
            s["pairs"][0][field] = bad_val
            with self.assertRaises(p0.ConfigurationValidationError) as ctx:
                p0.validate_inputs(self.manifest, s, check_provenance=False)
            self.assertIn(f"{field} mismatch", str(ctx.exception))


class TightenedOutputParsingTests(unittest.TestCase):
    """Tests for tightened core JSON and HTTP Markdown parsers."""

    def setUp(self):
        self.manifest = p0.read_json(p0.DEFAULT_MANIFEST_PATH)
        self.cells = {c["cell_id"]: c for c in self.manifest["pilot_design"]["cells"]}

    def test_core_json_parsing_from_preflight_fixture(self):
        """Parse real preflight core_smoke_report.json and verify extracted metrics."""
        self.assertTrue(CORE_SMOKE_JSON_PATH.is_file(), "core_smoke_report.json fixture missing")
        stdout = CORE_SMOKE_JSON_PATH.read_text()
        cell = self.cells["core_sparse_traversal_compact-bfs_fresh"]
        test_cell = copy.deepcopy(cell)
        test_cell["nodes"] = 128
        test_cell["rounds"] = 10

        parsed = p0.parse_core_output(stdout, stderr="", cell=test_cell)
        self.assertEqual(parsed["workload"], "chain-split-rejoin-v1")
        self.assertEqual(parsed["engine"], "knotrel-core/compact-bfs-v1")
        self.assertEqual(parsed["warmup"], 0)
        self.assertEqual(parsed["trace_fingerprint_fnv1a64"], "ea72ce261a96e862")
        self.assertEqual(parsed["setup_ns"], 46916)
        self.assertEqual(parsed["workload_wall_ns"], 25875)
        self.assertEqual(parsed["measurements"]["connected"]["count"], 20)
        self.assertEqual(parsed["measurements"]["link"]["count"], 10)
        self.assertEqual(parsed["measurements"]["cut"]["count"], 10)

    def test_core_parser_rejects_missing_fingerprint_or_wrong_operation_counts(self):
        """Core parser must reject missing/invalid fingerprint and operation count discrepancies."""
        cell = copy.deepcopy(self.cells["core_sparse_traversal_compact-bfs_fresh"])
        cell["nodes"] = 128
        cell["rounds"] = 10

        base_report = {
            "schema_version": 2,
            "engine": "knotrel-core/compact-bfs-v1",
            "workload": "chain-split-rejoin-v1",
            "config": {"nodes": 128, "rounds": 10, "seed": 42},
            "warmup": 0,
            "repetitions": [
                {
                    "setup_ns": 1000,
                    "workload_wall_ns": 2000,
                    "measurements": {
                        "connected": {"count": 20, "total_ns": 200, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "link": {"count": 10, "total_ns": 100, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "cut": {"count": 10, "total_ns": 100, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                    },
                }
            ],
            "trace_fingerprint_fnv1a64": "0123456789abcdef",
        }

        # 1. Missing or invalid fingerprint
        rep_bad_fp = copy.deepcopy(base_report)
        rep_bad_fp["trace_fingerprint_fnv1a64"] = "short"
        with self.assertRaises(p0.QualificationBlockerError):
            p0.parse_core_output(json.dumps(rep_bad_fp), "", cell)

        # 2. Wrong operation counts (e.g. cut count = 9 instead of 10)
        rep_bad_cnt = copy.deepcopy(base_report)
        rep_bad_cnt["repetitions"][0]["measurements"]["cut"]["count"] = 9
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_bad_cnt), "", cell)
        self.assertIn("Expected 10 cuts, got 9", str(ctx.exception))

        # 3. Non-monotonic percentiles
        rep_bad_perc = copy.deepcopy(base_report)
        rep_bad_perc["repetitions"][0]["measurements"]["connected"]["p50_ns"] = 50
        rep_bad_perc["repetitions"][0]["measurements"]["connected"]["p95_ns"] = 30  # p50 > p95!
        with self.assertRaises(p0.QualificationBlockerError):
            p0.parse_core_output(json.dumps(rep_bad_perc), "", cell)

    def test_sustained_churn_path_operation_counts(self):
        """Sustained churn path must accept exact frozen trace generator counts (716 cuts, 284 links, 1000 queries)

        and reject incorrect balanced 500/500 or tampered counts.
        """
        cell_sustained = {
            "cell_id": "core_sustained_churn_compact-bfs_fresh",
            "type": "core",
            "workload": "sustained-churn-path-v1",
            "workload_id": "sustained_churn",
            "nodes": 1000,
            "rounds": 20,
            "seed": 42,
            "query_percent": 50,
            "engine": "compact-bfs",
            "warmup": 0,
            "repetitions": 1,
        }

        base_report = {
            "schema_version": 2,
            "engine": "knotrel-core/compact-bfs-v1",
            "workload": "sustained-churn-path-v1",
            "config": {"nodes": 1000, "rounds": 20, "seed": 42},
            "warmup": 0,
            "repetitions": [
                {
                    "setup_ns": 1000,
                    "workload_wall_ns": 2000,
                    "measurements": {
                        "connected": {"count": 1000, "total_ns": 10000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "link": {"count": 284, "total_ns": 2840, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "cut": {"count": 716, "total_ns": 7160, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                    },
                }
            ],
            "trace_fingerprint_fnv1a64": "0123456789abcdef",
        }

        # 1. Accept valid scheduled sustained-workload counts
        repetition = base_report["repetitions"][0]
        repetition["query_true"] = None
        repetition["query_false"] = copy.deepcopy(repetition["measurements"]["connected"])
        repetition["repeated_queries"] = None
        parsed = p0.parse_core_output(json.dumps(base_report), "", cell_sustained)
        self.assertEqual(parsed["measurements"]["cut"]["count"], 716)
        self.assertEqual(parsed["measurements"]["link"]["count"], 284)
        self.assertEqual(parsed["measurements"]["connected"]["count"], 1000)

        # 2. Reject incorrect balanced 500/500 report
        rep_balanced = copy.deepcopy(base_report)
        rep_balanced["repetitions"][0]["measurements"]["cut"]["count"] = 500
        rep_balanced["repetitions"][0]["measurements"]["link"]["count"] = 500
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_balanced), "", cell_sustained)
        self.assertIn("Expected 716 cuts, got 500", str(ctx.exception))

        # 3. Reject tampered counts (e.g. cut=715)
        rep_tampered = copy.deepcopy(base_report)
        rep_tampered["repetitions"][0]["measurements"]["cut"]["count"] = 715
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_tampered), "", cell_sustained)
        self.assertIn("Expected 716 cuts, got 715", str(ctx.exception))

        # 4. Reject tampered query counts (e.g. connected=999)
        rep_tampered_q = copy.deepcopy(base_report)
        rep_tampered_q["repetitions"][0]["measurements"]["connected"]["count"] = 999
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_tampered_q), "", cell_sustained)
        self.assertIn("Expected 1000 queries, got 999", str(ctx.exception))

    def test_dense_bridge_and_chain_operation_counts(self):
        """Preserve valid chain (100 cut, 100 link, 200 query) and dense-bridge (500 cut, 500 link, 1000 query) parsing and reject tampering."""
        # Dense bridge
        cell_dense = {
            "cell_id": "core_dense_alternatives_compact-bfs_fresh",
            "type": "core",
            "workload": "dense-bridge-churn-v1",
            "workload_id": "dense_alternatives",
            "nodes": 128,
            "rounds": 20,
            "seed": 42,
            "query_percent": 50,
            "engine": "compact-bfs",
            "warmup": 0,
            "repetitions": 1,
        }
        rep_dense = {
            "schema_version": 2,
            "engine": "knotrel-core/compact-bfs-v1",
            "workload": "dense-bridge-churn-v1",
            "config": {"nodes": 128, "rounds": 20, "seed": 42},
            "warmup": 0,
            "repetitions": [
                {
                    "setup_ns": 1000,
                    "workload_wall_ns": 2000,
                    "measurements": {
                        "connected": {"count": 1000, "total_ns": 10000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "link": {"count": 500, "total_ns": 5000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "cut": {"count": 500, "total_ns": 5000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                    },
                }
            ],
            "trace_fingerprint_fnv1a64": "0123456789abcdef",
        }
        repetition = rep_dense["repetitions"][0]
        repetition["query_true"] = None
        repetition["query_false"] = copy.deepcopy(repetition["measurements"]["connected"])
        repetition["repeated_queries"] = None
        parsed = p0.parse_core_output(json.dumps(rep_dense), "", cell_dense)
        self.assertEqual(parsed["measurements"]["cut"]["count"], 500)
        self.assertEqual(parsed["measurements"]["link"]["count"], 500)

        # Dense bridge tampered
        rep_dense_tampered = copy.deepcopy(rep_dense)
        rep_dense_tampered["repetitions"][0]["measurements"]["cut"]["count"] = 501
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_dense_tampered), "", cell_dense)
        self.assertIn("Expected 500 cuts, got 501", str(ctx.exception))

        # Chain
        cell_chain = {
            "cell_id": "core_sparse_traversal_compact-bfs_fresh",
            "type": "core",
            "workload": "chain-split-rejoin-v1",
            "workload_id": "sparse_traversal",
            "nodes": 1024,
            "rounds": 100,
            "seed": 42,
            "query_percent": 50,
            "engine": "compact-bfs",
            "warmup": 0,
            "repetitions": 1,
        }
        rep_chain = {
            "schema_version": 2,
            "engine": "knotrel-core/compact-bfs-v1",
            "workload": "chain-split-rejoin-v1",
            "config": {"nodes": 1024, "rounds": 100, "seed": 42},
            "warmup": 0,
            "repetitions": [
                {
                    "setup_ns": 1000,
                    "workload_wall_ns": 2000,
                    "measurements": {
                        "connected": {"count": 200, "total_ns": 2000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "link": {"count": 100, "total_ns": 1000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                        "cut": {"count": 100, "total_ns": 1000, "min_ns": 10, "p50_ns": 10, "p95_ns": 10, "p99_ns": 10, "max_ns": 10},
                    },
                }
            ],
            "trace_fingerprint_fnv1a64": "0123456789abcdef",
        }
        repetition = rep_chain["repetitions"][0]
        repetition["query_true"] = None
        repetition["query_false"] = copy.deepcopy(repetition["measurements"]["connected"])
        repetition["repeated_queries"] = None
        parsed_ch = p0.parse_core_output(json.dumps(rep_chain), "", cell_chain)
        self.assertEqual(parsed_ch["measurements"]["cut"]["count"], 100)

        # Chain tampered
        rep_chain_tampered = copy.deepcopy(rep_chain)
        rep_chain_tampered["repetitions"][0]["measurements"]["link"]["count"] = 99
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_core_output(json.dumps(rep_chain_tampered), "", cell_chain)
        self.assertIn("Expected 100 links, got 99", str(ctx.exception))

    def test_http_markdown_parsing_from_preflight_fixture(self):
        """Parse real preflight HTTP report markdown and verify exported and unavailable metrics."""
        self.assertTrue(HTTP_REPORT_MD_PATH.is_file(), "measurement_small_release.md fixture missing")
        stdout = HTTP_REPORT_MD_PATH.read_text()
        cell = self.cells["http_lifecycle_compact_bfs_small"]

        parsed = p0.parse_http_output(stdout, stderr="", cell=cell)
        exp = parsed["exported_metrics"]
        self.assertEqual(exp["import_duration_ms"], 2.97)
        self.assertEqual(exp["catchup_duration_ms"], 2.77)
        self.assertEqual(exp["time_to_ready_ms"], 6.37)
        self.assertEqual(exp["query_qps"], 9458.8)
        self.assertEqual(exp["query_latency_p50_us"], 87.1)
        self.assertEqual(exp["query_latency_p95_us"], 168.1)
        self.assertEqual(exp["oracle_agreement_raw"], "1000/1000 (100.00%)")
        self.assertEqual(exp["oracle_agreement_pct"], 100.0)
        self.assertEqual(exp["final_sampled_rss_mib"], 7.55)
        self.assertEqual(exp["sampled_max_rss_mib"], 7.55)
        self.assertEqual(exp["restart_recovery_ms"], 34.98)

        unavail = parsed["unavailable_metrics"]
        for m in ("query_latency_p99_us", "query_latency_mean_us", "query_latency_min_us", "query_latency_max_us"):
            self.assertIsNone(unavail[m]["value"])
            self.assertIn("internal calculation does not make them observable", unavail[m]["reason"])
            self.assertIn("must not be modified or rebuilt", unavail[m]["reason"])

    def test_http_parser_rejects_zero_queries_and_missing_or_invalid_metrics(self):
        """HTTP parser must reject 0/0 queries, missing columns, non-finite values, and no zero substitution."""
        cell = self.cells["http_lifecycle_compact_bfs_small"]

        # 1. Reject 0/0
        report_0_0 = (
            "| Run # | Import (ms) | Catch-up (ms) | Time-to-Ready (ms) | Query QPS | Latency p50 (µs) | Latency p95 (µs) | Oracle Agreement | Final Sampled RSS (MiB) | Sampled Max RSS (MiB)* | Restart Recovery (ms) |\n"
            "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
            "| **#1** | `2.97` | `2.77` | `6.37` | `9458.8` | `87.1` | `168.1` | `0/0 (100.00%)` | `7.55` | `7.55` | `34.98` |\n"
        )
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_output(report_0_0, "", cell)
        self.assertIn("0/0 is strictly rejected", str(ctx.exception))

        # 2. Reject missing column
        report_missing_col = (
            "| Run # | Import (ms) | Catch-up (ms) | Time-to-Ready (ms) | Latency p50 (µs) | Latency p95 (µs) | Oracle Agreement | Final Sampled RSS (MiB) | Sampled Max RSS (MiB)* | Restart Recovery (ms) |\n"
            "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
            "| **#1** | `2.97` | `2.77` | `6.37` | `87.1` | `168.1` | `1000/1000 (100.00%)` | `7.55` | `7.55` | `34.98` |\n"
        )
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_output(report_missing_col, "", cell)
        self.assertIn("missing required column 'Query QPS'", str(ctx.exception))

        # 3. Reject non-finite value (NaN / Inf)
        report_nan = (
            "| Run # | Import (ms) | Catch-up (ms) | Time-to-Ready (ms) | Query QPS | Latency p50 (µs) | Latency p95 (µs) | Oracle Agreement | Final Sampled RSS (MiB) | Sampled Max RSS (MiB)* | Restart Recovery (ms) |\n"
            "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
            "| **#1** | `NaN` | `2.77` | `6.37` | `9458.8` | `87.1` | `168.1` | `1000/1000 (100.00%)` | `7.55` | `7.55` | `34.98` |\n"
        )
        with self.assertRaises(p0.QualificationBlockerError):
            p0.parse_http_output(report_nan, "", cell)


class HostValidationAndThermalRequirementsTests(unittest.TestCase):
    """Tests for HostPreconditionError and strict thermal requirement enforcement."""

    def test_host_precondition_error_defined_and_raised(self):
        """HostPreconditionError must be a subclass of CollectorError and raised on preflight failure."""
        self.assertTrue(issubclass(p0.HostPreconditionError, p0.CollectorError))
        h_bad = {"power": "Now drawing from 'Battery Power'", "competing_workloads": []}
        with tempfile.TemporaryDirectory() as tmpdir:
            dest = Path(tmpdir) / "test_out"
            with patch("run_p0_aa.host_state", return_value=h_bad), patch("run_p0_aa.command", side_effect=synthetic_git_command):
                with self.assertRaises(p0.HostPreconditionError):
                    p0.execute_pilot(
                        manifest_path=p0.DEFAULT_MANIFEST_PATH,
                        schedule_path=p0.DEFAULT_SCHEDULE_PATH,
                        destination=dest,
                        enforce_host=True,
                    )

    def test_thermal_requirement_not_weakened(self):
        """Missing CPU_Speed_Limit on unsupported platforms or corrupted output must block execution and not be silently weakened."""
        # Intel Darwin without CPU_Speed_Limit
        h_intel_missing = {
            "platform_system": "darwin",
            "platform_machine": "x86_64",
            "power": "Now drawing from 'AC Power'",
            "thermal": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded",
            "competing_workloads": [],
        }
        ok, err = p0.validate_host_state(h_intel_missing, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("unsupported platform (darwin x86_64)", err)

        # Throttled CPU (< 100)
        h_throttled = {
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "power": "Now drawing from 'AC Power'",
            "thermal": "CPU_Speed_Limit = 80",
            "competing_workloads": [],
        }
        ok, err = p0.validate_host_state(h_throttled, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("CPU_Speed_Limit = 80% (!= 100)", err)

        # Valid unthrottled CPU (100)
        h_unthrottled = {
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "power": "Now drawing from 'AC Power'",
            "thermal": "CPU_Speed_Limit = 100",
            "competing_workloads": [],
        }
        ok, err = p0.validate_host_state(h_unthrottled, enforce_ac=True)
        self.assertTrue(ok)
        self.assertIsNone(err)
        self.assertEqual(h_unthrottled.get("thermal_validation_mode"), "darwin_cpu_speed_limit")

    def test_accepted_apple_silicon_categorical_observations(self):
        """Accepted Apple Silicon categorical observations must validate and record mode/limitations."""
        valid_therm_stdout = (
            "Note: No thermal warning level has been recorded\n"
            "Note: No performance warning level has been recorded\n"
            "Note: No CPU power status has been recorded\n"
        )
        for level in ("Great", "OK"):
            valid_sysload_stdout = (
                f"2026-10-26 08:00:00 +0100\n  combined level = OK\n"
                f"  - user level = OK\n  - battery level = OK\n  - thermal level = {level}\n"
            )
            h_valid = {
                "platform_system": "darwin",
                "platform_machine": "arm64",
                "power": "Now drawing from 'AC Power'\n -InternalBattery-0 100%",
                "competing_workloads": [],
                "pmset_therm": {
                    "command": ["pmset", "-g", "therm"],
                    "exit_code": 0,
                    "stdout": valid_therm_stdout,
                    "stderr": "",
                },
                "pmset_sysload": {
                    "command": ["pmset", "-g", "sysload"],
                    "exit_code": 0,
                    "stdout": valid_sysload_stdout,
                    "stderr": "",
                },
            }
            ok, err = p0.validate_host_state(h_valid, enforce_ac=True)
            self.assertTrue(ok, f"Expected validation success for thermal level {level}, got {err}")
            self.assertIsNone(err)
            self.assertEqual(h_valid.get("thermal_validation_mode"), "darwin_arm64_categorical_advisory")
            self.assertIn(
                "No disqualifying condition was observed at the sampled boundaries. "
                "Throttling or frequency changes between observations remain possible.",
                h_valid.get("thermal_telemetry_limitations", ""),
            )

    def test_explicit_cpu_speed_reduction_despite_clean_advisories(self):
        """Explicit CPU speed reduction (< 100) must be rejected even if categorical advisories are clean."""
        h_reduced = {
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "power": "Now drawing from 'AC Power'",
            "competing_workloads": [],
            "pmset_therm": {
                "command": ["pmset", "-g", "therm"],
                "exit_code": 0,
                "stdout": (
                    "CPU_Speed_Limit = 85\n"
                    "Note: No thermal warning level has been recorded\n"
                    "Note: No performance warning level has been recorded\n"
                    "Note: No CPU power status has been recorded\n"
                ),
                "stderr": "",
            },
            "pmset_sysload": {
                "command": ["pmset", "-g", "sysload"],
                "exit_code": 0,
                "stdout": "combined level = OK\n  - thermal level = Great\n",
                "stderr": "",
            },
        }
        ok, err = p0.validate_host_state(h_reduced, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("CPU_Speed_Limit = 85% (!= 100)", err)
        self.assertNotIn("darwin_arm64_categorical_advisory", h_reduced.get("thermal_validation_mode", ""))

    def test_warnings_contradictory_malformed_and_command_failures(self):
        """Reject explicit warnings, contradictory output, malformed output, and command failures."""
        base_h = {
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "power": "Now drawing from 'AC Power'",
            "competing_workloads": [],
        }

        # 1. Explicit warning in pmset -g therm
        h_warn = copy.deepcopy(base_h)
        h_warn["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Thermal warning level = Warning\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_warn["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "thermal level = Great\n", "stderr": ""}
        ok, err = p0.validate_host_state(h_warn, enforce_ac=True)
        self.assertFalse(ok)
        self.assertTrue("Missing recognized thermal advisory note" in err or "Explicit thermal warning" in err)

        # 2. Contradictory / unexpected extra line in pmset -g therm
        h_contra = copy.deepcopy(base_h)
        h_contra["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": (
                "Note: No thermal warning level has been recorded\n"
                "Note: No performance warning level has been recorded\n"
                "Note: No CPU power status has been recorded\n"
                "Unexpected extra line in pmset output\n"
            ),
            "stderr": "",
        }
        h_contra["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "thermal level = Great\n", "stderr": ""}
        ok, err = p0.validate_host_state(h_contra, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Unrecognized or contradictory output in pmset -g therm", err)

        # 3. Missing 3rd note (only 2 notes)
        h_missing_note = copy.deepcopy(base_h)
        h_missing_note["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": (
                "Note: No thermal warning level has been recorded\n"
                "Note: No performance warning level has been recorded\n"
            ),
            "stderr": "",
        }
        h_missing_note["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "thermal level = Great\n", "stderr": ""}
        ok, err = p0.validate_host_state(h_missing_note, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Missing recognized thermal advisory note", err)

        # 4. Malformed sysload
        h_malformed_sys = copy.deepcopy(base_h)
        h_malformed_sys["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_malformed_sys["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "no levels recorded here\n", "stderr": ""}
        ok, err = p0.validate_host_state(h_malformed_sys, enforce_ac=True)
        self.assertFalse(ok)
        self.assertTrue("Missing thermal level in pmset -g sysload" in err or "Malformed" in err)

        # 5. Disqualifying sysload levels: Warning, Urgent, Critical
        for disq_lvl in ("Warning", "Urgent", "Critical"):
            h_disq = copy.deepcopy(base_h)
            h_disq["pmset_therm"] = {
                "command": ["pmset", "-g", "therm"],
                "exit_code": 0,
                "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
                "stderr": "",
            }
            h_disq["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": f"combined level = OK\n  - thermal level = {disq_lvl}\n", "stderr": ""}
            ok, err = p0.validate_host_state(h_disq, enforce_ac=True)
            self.assertFalse(ok)
            self.assertTrue("Disqualifying sysload thermal level" in err or "Degraded system load" in err)

        # 6. Command failure: pmset -g therm exit_code != 0
        h_fail_therm = copy.deepcopy(base_h)
        h_fail_therm["pmset_therm"] = {"command": ["pmset", "-g", "therm"], "exit_code": 1, "stdout": "", "stderr": "permission denied"}
        h_fail_therm["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "thermal level = Great\n", "stderr": ""}
        ok, err = p0.validate_host_state(h_fail_therm, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("pmset -g therm failed with exit code 1", err)

        # 7. Command failure: pmset -g sysload exit_code != 0
        h_fail_sysload = copy.deepcopy(base_h)
        h_fail_sysload["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_fail_sysload["pmset_sysload"] = {"command": ["pmset", "-g", "sysload"], "exit_code": 2, "stdout": "", "stderr": "sysload error"}
        ok, err = p0.validate_host_state(h_fail_sysload, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("pmset -g sysload failed with exit code 2", err)

        # 8. Command failure with CPU_Speed_Limit = 100 in stdout (Defect 1 regression test)
        h_fail_therm_speed100 = copy.deepcopy(base_h)
        h_fail_therm_speed100["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 1,
            "stdout": "CPU_Speed_Limit = 100\n",
            "stderr": "error reading hardware",
        }
        ok, err = p0.validate_host_state(h_fail_therm_speed100, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("pmset -g therm failed with exit code 1", err)

        # 9. Duplicate / conflicting sysload fields (Great and Unknown) (Defect 2 regression test)
        h_dup_sys = copy.deepcopy(base_h)
        h_dup_sys["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_dup_sys["pmset_sysload"] = {
            "command": ["pmset", "-g", "sysload"],
            "exit_code": 0,
            "stdout": "combined level = OK\n  thermal level = Great\n  thermal level = Unknown\n",
            "stderr": "",
        }
        ok, err = p0.validate_host_state(h_dup_sys, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Duplicate or conflicting thermal fields detected in pmset -g sysload", err)

        # 10. Unknown sysload thermal value alone (Defect 2 regression test)
        h_unk_sys = copy.deepcopy(base_h)
        h_unk_sys["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_unk_sys["pmset_sysload"] = {
            "command": ["pmset", "-g", "sysload"],
            "exit_code": 0,
            "stdout": "combined level = OK\n  - thermal level = Unknown\n",
            "stderr": "",
        }
        ok, err = p0.validate_host_state(h_unk_sys, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Unknown or unrecognized sysload thermal level detected", err)

        # 11. Malformed sysload thermal line: valid prefix with extra characters (Defect 2 regression test)
        h_prefix_sys = copy.deepcopy(base_h)
        h_prefix_sys["pmset_therm"] = {
            "command": ["pmset", "-g", "therm"],
            "exit_code": 0,
            "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
            "stderr": "",
        }
        h_prefix_sys["pmset_sysload"] = {
            "command": ["pmset", "-g", "sysload"],
            "exit_code": 0,
            "stdout": "combined level = OK\n  - thermal level = Great extra trailing text\n",
            "stderr": "",
        }
        ok, err = p0.validate_host_state(h_prefix_sys, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Malformed thermal level line in pmset -g sysload", err)

    def test_no_fallback_on_unsupported_platforms(self):
        """Categorical fallback must be rejected on unsupported platforms (e.g. Darwin x86_64 or Linux)."""
        clean_arm_notes = (
            "Note: No thermal warning level has been recorded\n"
            "Note: No performance warning level has been recorded\n"
            "Note: No CPU power status has been recorded\n"
        )
        # Darwin x86_64 without CPU_Speed_Limit
        h_intel = {
            "platform_system": "darwin",
            "platform_machine": "x86_64",
            "power": "Now drawing from 'AC Power'",
            "competing_workloads": [],
            "pmset_therm": {"command": ["pmset", "-g", "therm"], "exit_code": 0, "stdout": clean_arm_notes, "stderr": ""},
            "pmset_sysload": {"command": ["pmset", "-g", "sysload"], "exit_code": 0, "stdout": "thermal level = Great\n", "stderr": ""},
        }
        ok, err = p0.validate_host_state(h_intel, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("unsupported platform (darwin x86_64)", err)
        self.assertIn("categorical fallback is permitted only on explicitly identified Darwin arm64 hosts", err)

        # Linux x86_64
        h_linux = {
            "platform_system": "linux",
            "platform_machine": "x86_64",
            "power": "Now drawing from 'AC Power'",
            "competing_workloads": [],
        }
        ok, err = p0.validate_host_state(h_linux, enforce_ac=True)
        self.assertFalse(ok)
        self.assertIn("Unsupported platform for thermal validation: linux x86_64", err)


class RealProcessOrchestrationIntegrationTests(unittest.TestCase):
    """End-to-end integration tests using fake processes traversing observe_child() and execute_pilot().

    DOES NOT mock observe_child() or simulate the dictionary returned by the helper!
    """

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

        # Create fake core benchmark script
        self.fake_core_script = self.tmpdir / "fake_core_bench.py"
        self.fake_core_script.write_text(
            """#!/usr/bin/env python3
import json
import sys

# Emit valid core report for chain-split-rejoin-v1, nodes=1024, rounds=100
report = {
    "schema_version": 2,
    "engine": "knotrel-core/compact-bfs-v1",
    "workload": "chain-split-rejoin-v1",
    "benchmark_version": "0.3.0",
    "compiler": "rustc 1.98.1",
    "os": "macos",
    "arch": "aarch64",
    "debug_assertions": False,
    "timestamp_unix_seconds": 1792860000,
    "config": {"nodes": 1024, "rounds": 100, "seed": 42},
    "warmup": 0,
    "repetitions": [
        {
            "setup_ns": 45000,
            "workload_wall_ns": 30000,
            "measurements": {
                "connected": {"count": 200, "total_ns": 20000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
                "link": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95, "max_ns": 100},
                "cut": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95, "max_ns": 100},
            },
            "query_true": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
            "query_false": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
            "repeated_queries": None
        }
    ],
    "trace_fingerprint_fnv1a64": "ea72ce261a96e862",
    "initial_edges": 1023,
    "initial_density": 0.00195,
    "initial_max_degree": 2
}
print(json.dumps(report))
sys.exit(0)
"""
        )
        self.fake_core_script.chmod(0o755)

        # Create fake HTTP benchmark script
        self.fake_http_script = self.tmpdir / "fake_http_bench.py"
        self.fake_http_script.write_text(
            """#!/usr/bin/env python3
import sys

table = \"\"\"
### Knotrel End-to-End Measurement Report (Feature 0.2.6)

| Run # | Import (ms) | Catch-up (ms) | Time-to-Ready (ms) | Query QPS | Latency p50 (µs) | Latency p95 (µs) | Oracle Agreement | Final Sampled RSS (MiB) | Sampled Max RSS (MiB)* | Restart Recovery (ms) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **#1** | `2.97` | `2.77` | `6.37` | `9458.8` | `87.1` | `168.1` | `1000/1000 (100.00%)` | `7.55` | `7.55` | `34.98` |
\"\"\"
print(table.strip())
sys.exit(0)
"""
        )
        self.fake_http_script.chmod(0o755)

        # Build self-contained mini-manifest and mini-schedule
        self.mini_manifest_path = self.tmpdir / "manifest.json"
        self.mini_schedule_path = self.tmpdir / "schedule.json"

        cell_core = {
            "cell_id": "core_cell_1",
            "type": "core",
            "workload": "chain-split-rejoin-v1",
            "workload_id": "sparse_traversal",
            "nodes": 1024,
            "rounds": 100,
            "seed": 42,
            "engine": "compact-bfs",
            "warmup": 0,
            "repetitions": 1,
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, str(self.fake_core_script)],
            "env": {"PATH": "/usr/bin:/bin", "RUST_BACKTRACE": "1"},
        }
        cell_http = {
            "cell_id": "http_cell_1",
            "type": "http",
            "workload": "source-managed-lifecycle",
            "workload_id": "http_small",
            "queries": 1000,
            "runs": 1,
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, str(self.fake_http_script)],
            "env": {"PATH": "/usr/bin:/bin", "RUST_BACKTRACE": "1"},
        }

        self.mini_manifest = {
            "schema": "knotrel-p0-pilot-manifest-v1",
            "pilot_design": {
                "total_cells": 31,
                "total_pairs": 186,
                "total_measured_launches": 372,
                "cells": [cell_core, cell_http],
            },
        }

        pair_core = {
            "pair_id": 0,
            "cell_id": "core_cell_1",
            "session": 0,
            "labels": ["A", "Aprime"],
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, str(self.fake_core_script)],
            "env": {"PATH": "/usr/bin:/bin", "RUST_BACKTRACE": "1"},
        }
        pair_http = {
            "pair_id": 1,
            "cell_id": "http_cell_1",
            "session": 0,
            "labels": ["Aprime", "A"],
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, str(self.fake_http_script)],
            "env": {"PATH": "/usr/bin:/bin", "RUST_BACKTRACE": "1"},
        }

        self.mini_schedule = {
            "schema": "knotrel-p0-pilot-schedule-v1",
            "total_cells": 31,
            "total_pairs": 186,
            "total_measured_runs": 372,
            "sessions": [{"session_id": 0, "seed": 120047, "pair_count": 62}],
            "pairs": [pair_core, pair_http],
        }

        p0.save_json(self.mini_manifest_path, self.mini_manifest)
        p0.save_json(self.mini_schedule_path, self.mini_schedule)

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    FAKE_HOST = {
        "hostname": "test-host",
        "os": "darwin",
        "competing_workloads": [],
        "available_disk_bytes": 100 * 1024**3,
        "power": "Now drawing from 'AC Power'\n -InternalBattery-0 100%",
        "thermal": "CPU_Speed_Limit = 100",
        "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
        "power_configuration": "sleep 0",
    }

    def test_real_orchestration_fake_campaign_successful(self):
        """Execute real execute_pilot() traversing real observe_child() with fake executables."""
        dest = self.tmpdir / "campaign_output"
        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=self.FAKE_HOST):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            # Execute with real child process spawns
            rc = p0.execute_pilot(
                manifest_path=self.mini_manifest_path,
                schedule_path=self.mini_schedule_path,
                destination=dest,
                enforce_host=False,
                session_pre_quiet_seconds=0.0,
                inter_session_cooldown_seconds=0.0,
                check_provenance=False,
            )
            self.assertEqual(rc, 0)

        # Verify artifacts
        self.assertTrue((dest / "manifest.json").is_file())
        self.assertTrue((dest / "schedule.json").is_file())
        self.assertTrue((dest / "run_metadata.json").is_file())
        self.assertTrue((dest / "analysis.json").is_file())

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "completed")
        self.assertEqual(meta["completed_pairs"], 2)
        self.assertEqual(meta["completed_observations"], 4)

        # Verify pair records
        pair0 = p0.read_json(dest / "pair_000_core_cell_1.json")
        self.assertEqual(len(pair0["observations"]), 2)
        obs_a = pair0["observations"][0]
        self.assertEqual(obs_a["label"], "A")
        self.assertEqual(obs_a["exit_code"], 0)
        self.assertFalse(obs_a["timed_out"])
        self.assertIn("launch_monotonic_ns", obs_a)
        self.assertIn("completion_monotonic_ns", obs_a)
        self.assertGreater(obs_a["completion_monotonic_ns"], obs_a["launch_monotonic_ns"])
        self.assertEqual(obs_a["status"], "parsed_valid")
        self.assertEqual(obs_a["parsed_metrics"]["workload_wall_ns"], 30000)

        pair1 = p0.read_json(dest / "pair_001_http_cell_1.json")
        self.assertEqual(len(pair1["observations"]), 2)
        obs_http = pair1["observations"][0]
        self.assertEqual(obs_http["label"], "Aprime")
        self.assertEqual(obs_http["exit_code"], 0)
        self.assertEqual(obs_http["parsed_metrics"]["exported_metrics"]["query_qps"], 9458.8)

    def test_real_orchestration_persists_raw_output_before_process_failure(self):
        """When a real child exits with error, raw output and exit status must be persisted before raising."""
        failing_script = self.tmpdir / "failing_bench.py"
        failing_script.write_text(
            """#!/usr/bin/env python3
import sys
sys.stderr.write("Fatal crash in graph engine!\\n")
sys.stdout.write("Partial engine log output\\n")
sys.exit(101)
"""
        )
        failing_script.chmod(0o755)

        sched = copy.deepcopy(self.mini_schedule)
        sched["pairs"][0]["argv"] = [sys.executable, str(failing_script)]
        p0.save_json(self.mini_schedule_path, sched)

        dest = self.tmpdir / "failing_output"
        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=self.FAKE_HOST):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            with self.assertRaises(p0.ProcessExecutionError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
            self.assertIn("exited with non-zero code 101", str(ctx.exception))

        # Check that observation was persisted on disk BEFORE raising!
        pair_file = dest / "pair_000_core_cell_1.json"
        self.assertTrue(pair_file.is_file(), "Incomplete pair file must be persisted on disk")
        saved_pair = p0.read_json(pair_file)
        self.assertEqual(len(saved_pair["observations"]), 1)
        failed_obs = saved_pair["observations"][0]
        self.assertEqual(failed_obs["exit_code"], 101)
        self.assertEqual(failed_obs["status"], "exit_code_failure")
        self.assertIn("Partial engine log output", failed_obs["stdout"])
        self.assertIn("Fatal crash in graph engine!", failed_obs["raw_stderr"])

        # Check metadata records failure
        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class3_process_execution_failure")
        self.assertEqual(meta["failure_record"]["failure_class"], "class3_process_execution_failure")

    def test_real_orchestration_persists_raw_output_before_parsing_failure(self):
        """When a real child emits corrupt output, raw stdout must be persisted before QualificationBlockerError."""
        corrupt_script = self.tmpdir / "corrupt_bench.py"
        corrupt_script.write_text(
            """#!/usr/bin/env python3
import sys
sys.stdout.write("{ corrupt json output\\n")
sys.exit(0)
"""
        )
        corrupt_script.chmod(0o755)

        sched = copy.deepcopy(self.mini_schedule)
        sched["pairs"][0]["argv"] = [sys.executable, str(corrupt_script)]
        p0.save_json(self.mini_schedule_path, sched)

        dest = self.tmpdir / "corrupt_output"
        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=self.FAKE_HOST):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            with self.assertRaises(p0.QualificationBlockerError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
            self.assertIn("Core stdout is not valid JSON", str(ctx.exception))

        pair_file = dest / "pair_000_core_cell_1.json"
        self.assertTrue(pair_file.is_file())
        saved_pair = p0.read_json(pair_file)
        self.assertEqual(len(saved_pair["observations"]), 1)
        corrupt_obs = saved_pair["observations"][0]
        self.assertEqual(corrupt_obs["exit_code"], 0)
        self.assertEqual(corrupt_obs["status"], "qualification_blocker")
        self.assertIn("{ corrupt json output", corrupt_obs["stdout"])

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class1_qualification_blocker")

    def test_trace_identity_fingerprint_mismatch_stops_qualification_retaining_both_outputs(self):
        """When two observations for the same workload have different fingerprints, qualification stops and retains both outputs."""
        state_file = self.tmpdir / "fp_divergence_state.txt"
        divergent_script = self.tmpdir / "divergent_fp_bench.py"
        divergent_script.write_text(f"""#!/usr/bin/env python3
import json, sys
from pathlib import Path

state_p = Path({repr(str(state_file))})
if not state_p.exists():
    state_p.write_text("1")
    fp = "1111222233334444"
else:
    fp = "5555666677778888"

report = {{
    "schema_version": 2,
    "workload": "chain-split-rejoin-v1",
    "engine": "knotrel-core/compact-bfs-v1",
    "trace_fingerprint_fnv1a64": fp,
    "config": {{"nodes": 1024, "rounds": 100, "seed": 42}},
    "warmup": 0,
    "repetitions": [{{
        "setup_ns": 1000,
        "workload_wall_ns": 30000,
        "measurements": {{
            "cut": {{"count": 100, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 2000}},
            "link": {{"count": 100, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 2000}},
            "connected": {{"count": 200, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 4000}}
        }},
        "query_true": {{"count": 100, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 2000}},
        "query_false": {{"count": 100, "min_ns": 10, "p50_ns": 20, "p95_ns": 30, "p99_ns": 40, "max_ns": 50, "total_ns": 2000}},
        "repeated_queries": None
    }}]
}}
sys.stdout.write(json.dumps(report) + "\\n")
sys.exit(0)
""")
        divergent_script.chmod(0o755)

        sched = copy.deepcopy(self.mini_schedule)
        sched["pairs"][0]["argv"] = [sys.executable, str(divergent_script)]
        p0.save_json(self.mini_schedule_path, sched)

        dest = self.tmpdir / "divergent_fp_output"
        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=self.FAKE_HOST):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            with self.assertRaises(p0.QualificationBlockerError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
            self.assertIn("Trace identity consistency violation", str(ctx.exception))
            self.assertIn("1111222233334444", str(ctx.exception))
            self.assertIn("5555666677778888", str(ctx.exception))

        pair_file = dest / "pair_000_core_cell_1.json"
        self.assertTrue(pair_file.is_file(), "Pair file must exist on disk")
        saved_pair = p0.read_json(pair_file)
        self.assertEqual(len(saved_pair["observations"]), 2, "Both outputs must be retained")
        obs0 = saved_pair["observations"][0]
        obs1 = saved_pair["observations"][1]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertEqual(obs0["parsed_metrics"]["trace_fingerprint_fnv1a64"], "1111222233334444")
        self.assertEqual(obs1["status"], "qualification_blocker")
        self.assertIn("1111222233334444", obs1["error"])
        self.assertIn("5555666677778888", obs1["stdout"])

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class1_qualification_blocker")
        self.assertEqual(meta["failure_record"]["failure_class"], "class1_fatal_qualification_blocker")

    def test_real_fake_process_abnormal_parent_exit_kills_surviving_descendants(self):
        """Descendants surviving abnormal parent exit (both closing pipes and holding pipes open) must be reaped."""
        # Case 1: Descendant closes inherited output pipes
        marker1 = self.tmpdir / "descendant_pid_closed.txt"
        script1 = self.tmpdir / "abnormal_parent_closed.py"
        script1.write_text(f"""#!/usr/bin/env python3
import sys, subprocess, time
p = subprocess.Popen([sys.executable, "-c", "import time, sys; sys.stdout.close(); sys.stderr.close(); time.sleep(60)"], close_fds=True)
with open({repr(str(marker1))}, "w") as f:
    f.write(str(p.pid))
sys.stderr.write("Crash occurred after spawning detached descendant\\n")
sys.exit(42)
""")
        script1.chmod(0o755)

        res1 = p0.observe_child(
            argv=[sys.executable, str(script1)],
            cwd=str(self.tmpdir),
            env={"PATH": "/usr/bin:/bin"},
            timeout_seconds=5.0,
            is_core=False,
        )
        self.assertEqual(res1["exit_code"], 42)
        self.assertIn("Crash occurred after spawning detached descendant", res1["raw_stderr"])
        self.assertFalse(res1["timed_out"])

        d_pid1 = int(marker1.read_text().strip())
        killed1 = False
        for _ in range(20):
            try:
                os.kill(d_pid1, 0)
                time.sleep(0.05)
            except ProcessLookupError:
                killed1 = True
                break
        self.assertTrue(killed1, f"Descendant process {d_pid1} must be terminated upon abnormal parent exit")

        # Case 2: Descendant keeps inherited output pipes open
        marker2 = self.tmpdir / "descendant_pid_open.txt"
        script2 = self.tmpdir / "abnormal_parent_open.py"
        script2.write_text(f"""#!/usr/bin/env python3
import sys, subprocess, time
p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
with open({repr(str(marker2))}, "w") as f:
    f.write(str(p.pid))
sys.stderr.write("Crash with open pipe descendant\\n")
sys.exit(43)
""")
        script2.chmod(0o755)

        t_start = time.monotonic()
        res2 = p0.observe_child(
            argv=[sys.executable, str(script2)],
            cwd=str(self.tmpdir),
            env={"PATH": "/usr/bin:/bin"},
            timeout_seconds=5.0,
            is_core=False,
        )
        t_elapsed = time.monotonic() - t_start
        self.assertLess(t_elapsed, 2.5, "Should promptly terminate descendant holding pipes rather than blocking")
        self.assertEqual(res2["exit_code"], 43)
        self.assertIn("Crash with open pipe descendant", res2["raw_stderr"])
        self.assertFalse(res2["timed_out"])

        d_pid2 = int(marker2.read_text().strip())
        killed2 = False
        for _ in range(20):
            try:
                os.kill(d_pid2, 0)
                time.sleep(0.05)
            except ProcessLookupError:
                killed2 = True
                break
        self.assertTrue(killed2, f"Descendant process {d_pid2} holding pipes open must be terminated")

    def test_real_fake_process_cancellation_after_emitting_output_preserves_evidence(self):
        """When execution is cancelled after emitting output, recovered output is preserved before propagating interrupt."""
        script_cancel = self.tmpdir / "cancellable_bench.py"
        script_cancel.write_text("""#!/usr/bin/env python3
import sys, time
sys.stdout.write("EMITTED_OUTPUT_BEFORE_INTERRUPT\\n")
sys.stdout.flush()
time.sleep(60)
""")
        script_cancel.chmod(0o755)

        sched = copy.deepcopy(self.mini_schedule)
        sched["pairs"][0]["argv"] = [sys.executable, str(script_cancel)]
        p0.save_json(self.mini_schedule_path, sched)

        dest = self.tmpdir / "cancel_output"

        def interrupt_timer():
            time.sleep(0.2)
            _thread.interrupt_main()

        t = threading.Thread(target=interrupt_timer)
        t.daemon = True
        t.start()

        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=self.FAKE_HOST):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            with self.assertRaises(KeyboardInterrupt):
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )

        pair_file = dest / "pair_000_core_cell_1.json"
        self.assertTrue(pair_file.is_file(), "Incomplete pair file must be preserved on disk")
        saved_pair = p0.read_json(pair_file)
        self.assertEqual(len(saved_pair["observations"]), 1)
        cancelled_obs = saved_pair["observations"][0]
        self.assertEqual(cancelled_obs["status"], "cancelled")
        self.assertIn("EMITTED_OUTPUT_BEFORE_INTERRUPT", cancelled_obs["stdout"])

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_cancellation")
        self.assertEqual(meta["failure_record"]["failure_class"], "cancellation")

    def test_mocked_host_state_change_at_final_session_prevents_completed_status(self):
        """When the host observation changes at session conclusion, EnvironmentalInvalidationError is raised and completed status is not written."""
        dest = self.tmpdir / "host_invalidation_output"
        bad_host = copy.deepcopy(self.FAKE_HOST)
        bad_host["sleep_wake"] = "kern.sleeptime: { sec = 999999, usec = 0 }\\nkern.waketime: { sec = 999999, usec = 10 }"

        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", side_effect=[self.FAKE_HOST, self.FAKE_HOST, bad_host]):
            mock_val.return_value = {
                "status": "valid",
                "cells": {"core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                          "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1]}
            }
            with self.assertRaises(p0.EnvironmentalInvalidationError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=True,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
            self.assertIn("Sleep/wake event detected", str(ctx.exception))

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class2_environmental_invalidation")
        self.assertNotEqual(meta["status"], "completed")
        self.assertIsNotNone(meta["failure_record"])
        self.assertEqual(meta["failure_record"]["failure_class"], "class2_environmental_invalidation")

        self.assertIn("session_host_states", meta)
        self.assertEqual(len(meta["session_host_states"]), 1)
        self.assertEqual(meta["session_host_states"][0]["post_session_host"]["sleep_wake"], bad_host["sleep_wake"])

        pair0_file = dest / "pair_000_core_cell_1.json"
        self.assertTrue(pair0_file.is_file())

    def test_mocked_host_thermal_invalidation_at_final_session_boundary(self):
        """When host thermal advisory degrades at the final session boundary, EnvironmentalInvalidationError is raised."""
        dest = self.tmpdir / "thermal_invalidation_output"
        arm_healthy = {
            "hostname": "test-arm-host",
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "platform": "macOS-arm64",
            "competing_workloads": [],
            "available_disk_bytes": 100 * 1024**3,
            "power": "Now drawing from 'AC Power'\n -InternalBattery-0 100%",
            "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
            "power_configuration": "sleep 0",
            "pmset_therm": {
                "command": ["pmset", "-g", "therm"],
                "exit_code": 0,
                "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
                "stderr": "",
            },
            "pmset_sysload": {
                "command": ["pmset", "-g", "sysload"],
                "exit_code": 0,
                "stdout": "combined level = OK\n  - thermal level = Great\n",
                "stderr": "",
            },
        }

        # Degraded host at final session
        arm_degraded = copy.deepcopy(arm_healthy)
        arm_degraded["pmset_sysload"]["stdout"] = "combined level = OK\n  - thermal level = Urgent\n"

        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", side_effect=[arm_healthy, arm_healthy, arm_degraded]):
            mock_val.return_value = {
                "status": "valid",
                "cells": {
                    "core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                    "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1],
                },
            }
            with self.assertRaises(p0.EnvironmentalInvalidationError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.mini_manifest_path,
                    schedule_path=self.mini_schedule_path,
                    destination=dest,
                    enforce_host=True,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
            self.assertIn("Disqualifying sysload thermal level detected", str(ctx.exception))

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class2_environmental_invalidation")
        self.assertNotEqual(meta["status"], "completed")
        self.assertEqual(meta["failure_record"]["failure_class"], "class2_environmental_invalidation")

    def test_persistence_of_telemetry_and_validation_mode(self):
        """Verified execution must persist validation mode, telemetry limitations, and raw outputs into run_metadata.json."""
        dest = self.tmpdir / "persisted_telemetry_output"
        arm_healthy = {
            "hostname": "test-arm-host",
            "platform_system": "darwin",
            "platform_machine": "arm64",
            "platform": "macOS-arm64",
            "competing_workloads": [],
            "available_disk_bytes": 100 * 1024**3,
            "power": "Now drawing from 'AC Power'\n -InternalBattery-0 100%",
            "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
            "power_configuration": "sleep 0",
            "pmset_therm": {
                "command": ["pmset", "-g", "therm"],
                "exit_code": 0,
                "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
                "stderr": "",
            },
            "pmset_sysload": {
                "command": ["pmset", "-g", "sysload"],
                "exit_code": 0,
                "stdout": "combined level = OK\n  - thermal level = Great\n",
                "stderr": "",
            },
        }

        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=arm_healthy):
            mock_val.return_value = {
                "status": "valid",
                "cells": {
                    "core_cell_1": self.mini_manifest["pilot_design"]["cells"][0],
                    "http_cell_1": self.mini_manifest["pilot_design"]["cells"][1],
                },
            }
            rc = p0.execute_pilot(
                manifest_path=self.mini_manifest_path,
                schedule_path=self.mini_schedule_path,
                destination=dest,
                enforce_host=True,
                session_pre_quiet_seconds=0.0,
                inter_session_cooldown_seconds=0.0,
                check_provenance=False,
            )
            self.assertEqual(rc, 0)

        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "completed")
        self.assertEqual(meta["thermal_validation_mode"], "darwin_arm64_categorical_advisory")
        self.assertIn("No disqualifying condition was observed at the sampled boundaries.", meta["thermal_telemetry_limitations"])
        self.assertIn("Throttling or frequency changes between observations remain possible.", meta["thermal_telemetry_limitations"])

        # Check raw command outputs in initial host state
        init_h = meta["initial_host_state"]
        self.assertEqual(init_h["pmset_therm"]["exit_code"], 0)
        self.assertIn("Note: No thermal warning level has been recorded", init_h["pmset_therm"]["stdout"])
        self.assertEqual(init_h["pmset_sysload"]["exit_code"], 0)
        self.assertIn("thermal level = Great", init_h["pmset_sysload"]["stdout"])

        # Check session host states
        self.assertGreater(len(meta["session_host_states"]), 0)
        for s_entry in meta["session_host_states"]:
            post_h = s_entry["post_session_host"]
            self.assertEqual(post_h["thermal_validation_mode"], "darwin_arm64_categorical_advisory")
            self.assertEqual(post_h["pmset_therm"]["exit_code"], 0)
            self.assertEqual(post_h["pmset_sysload"]["exit_code"], 0)


class DescriptiveAnalysisTests(unittest.TestCase):
    """Tests for descriptive exploratory analysis rules."""

    def test_descriptive_analysis_metrics(self):
        """Verifies paired differences, log ratios, order categorization, CV, and disclaimer."""
        manifest = p0.read_json(p0.DEFAULT_MANIFEST_PATH)
        cell_map = {c["cell_id"]: c for c in manifest["pilot_design"]["cells"]}
        cell_id = "core_sparse_traversal_compact-bfs_fresh"

        observations = [
            # Pair 0: A=1000, Aprime=1050 (A first)
            {"cell_id": cell_id, "pair_id": 0, "pair_position": 0, "label": "A", "parsed_metrics": {"workload_wall_ns": 1000}},
            {"cell_id": cell_id, "pair_id": 0, "pair_position": 1, "label": "Aprime", "parsed_metrics": {"workload_wall_ns": 1050}},
            # Pair 1: Aprime=1040, A=1010 (Aprime first)
            {"cell_id": cell_id, "pair_id": 1, "pair_position": 0, "label": "Aprime", "parsed_metrics": {"workload_wall_ns": 1040}},
            {"cell_id": cell_id, "pair_id": 1, "pair_position": 1, "label": "A", "parsed_metrics": {"workload_wall_ns": 1010}},
        ]

        analysis = p0.analyze_pilot(observations, cell_map)
        self.assertEqual(analysis["analysis_type"], "exploratory_descriptive")
        self.assertIn("No statistical confidence", analysis["methodological_disclaimer"])
        self.assertIn("Automatic percentage gates (such as CV > 5%) are rejected", analysis["methodological_disclaimer"])

        cell_res = analysis["cells"][0]
        self.assertEqual(cell_res["cell_id"], cell_id)
        self.assertEqual(cell_res["pairs_completed"], 2)

        # Pair 0 delta: 1050 - 1000 = 50, rel = 0.05
        p0_delta = cell_res["paired_deltas"][0]
        self.assertEqual(p0_delta["diff"], 50)
        self.assertAlmostEqual(p0_delta["relative_diff"], 0.05)
        self.assertAlmostEqual(p0_delta["log_ratio"], math.log(1050 / 1000))
        self.assertEqual(p0_delta["order"], "A_first")

        # Pair 1 delta: 1040 - 1010 = 30
        p1_delta = cell_res["paired_deltas"][1]
        self.assertEqual(p1_delta["diff"], 30)
        self.assertEqual(p1_delta["order"], "Aprime_first")

        # Summary statistics
        self.assertIsNotNone(cell_res["summary"]["mean"])
        self.assertIsNotNone(cell_res["summary"]["cv"])
        self.assertIsNotNone(cell_res["summary"]["iqr"])


class AdditiveWaitingScheduleAndDeadlineTests(unittest.TestCase):
    """Deterministic tests proving additive quiet and cooldown periods with overall deadline enforcement."""

    class ControlledClock:
        def __init__(self, start_time: float = 1000.0):
            self.current_time = start_time
            self.sleep_intervals: List[float] = []

        def monotonic(self) -> float:
            return self.current_time

        def sleep(self, seconds: float) -> None:
            self.sleep_intervals.append(seconds)
            self.current_time += seconds

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

        self.cell_core = {
            "cell_id": "cell_0",
            "type": "core",
            "workload": "chain-split-rejoin-v1",
            "workload_id": "sparse_traversal",
            "nodes": 1024,
            "rounds": 100,
            "seed": 42,
            "engine": "compact-bfs",
            "warmup": 0,
            "repetitions": 1,
            "cwd": str(self.tmpdir),
            "argv": ["/fake/bin"],
            "env": {},
        }
        self.manifest = {
            "schema": "knotrel-p0-pilot-manifest-v1",
            "pilot_design": {
                "total_cells": 31,
                "total_pairs": 186,
                "total_measured_launches": 372,
                "cells": [self.cell_core],
            },
        }
        self.schedule = {
            "schema": "knotrel-p0-pilot-schedule-v1",
            "sessions": [
                {"session_id": 0, "pair_count": 1, "pre_quiet_seconds": 60.0, "seed": 42},
                {"session_id": 1, "pair_count": 1, "pre_quiet_seconds": 60.0, "seed": 43},
                {"session_id": 2, "pair_count": 1, "pre_quiet_seconds": 60.0, "seed": 44},
            ],
            "pairs": [
                {
                    "pair_id": 0,
                    "session": 0,
                    "cell_id": "cell_0",
                    "labels": ["A", "Aprime"],
                    "argv": ["/fake/bin"],
                    "cwd": "/fake/cwd",
                    "env": {},
                },
                {
                    "pair_id": 1,
                    "session": 1,
                    "cell_id": "cell_0",
                    "labels": ["Aprime", "A"],
                    "argv": ["/fake/bin"],
                    "cwd": "/fake/cwd",
                    "env": {},
                },
                {
                    "pair_id": 2,
                    "session": 2,
                    "cell_id": "cell_0",
                    "labels": ["A", "Aprime"],
                    "argv": ["/fake/bin"],
                    "cwd": "/fake/cwd",
                    "env": {},
                },
            ],
        }
        self.m_path = self.tmpdir / "manifest.json"
        self.s_path = self.tmpdir / "schedule.json"
        p0.save_json(self.m_path, self.manifest)
        p0.save_json(self.s_path, self.schedule)

        valid_report = {
            "schema_version": 2,
            "engine": "knotrel-core/compact-bfs-v1",
            "workload": "chain-split-rejoin-v1",
            "benchmark_version": "0.3.0",
            "compiler": "rustc 1.98.1",
            "os": "macos",
            "arch": "aarch64",
            "debug_assertions": False,
            "timestamp_unix_seconds": 1792860000,
            "config": {"nodes": 1024, "rounds": 100, "seed": 42},
            "warmup": 0,
            "repetitions": [
                {
                    "setup_ns": 45000,
                    "workload_wall_ns": 30000,
                    "measurements": {
                        "connected": {"count": 200, "total_ns": 20000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
                        "link": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95, "max_ns": 100},
                        "cut": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95, "max_ns": 100},
                    },
                    "query_true": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
                    "query_false": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200, "p99_ns": 250, "max_ns": 300},
                    "repeated_queries": None,
                }
            ],
            "trace_fingerprint_fnv1a64": "ea72ce261a96e862",
            "initial_edges": 1023,
            "initial_density": 0.00195,
            "initial_max_degree": 2,
        }
        self.fake_obs = {
            "full_cmd": ["/fake/bin"],
            "wrapper_pid": 1234,
            "launch_monotonic_ns": 1000,
            "completion_monotonic_ns": 2000,
            "launch_unix_ns": 1000,
            "completion_unix_ns": 2000,
            "wall_duration_ns": 1000,
            "exit_code": 0,
            "timed_out": False,
            "stdout": json.dumps(valid_report),
            "raw_stderr": "",
            "peak_rss_bytes": 1048576,
            "wrapper_diagnostics": {"real": 0.01, "user": 0.01, "sys": 0.0, "maxrss": 1048576},
        }

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def _fake_host_state(self, clock):
        return {
            "platform": "darwin",
            "platform_machine": "arm64",
            "platform_system": "darwin",
            "power": "Now drawing from 'AC Power'",
            "pmset_therm": {
                "command": ["pmset", "-g", "therm"],
                "exit_code": 0,
                "stdout": "Note: No thermal warning level has been recorded\nNote: No performance warning level has been recorded\nNote: No CPU power status has been recorded\n",
                "stderr": "",
            },
            "pmset_sysload": {
                "command": ["pmset", "-g", "sysload"],
                "exit_code": 0,
                "stdout": "combined level = OK\n  - thermal level = Great\n",
                "stderr": "",
            },
            "competing_workloads": [],
            "sleep_wake": "kern.sleeptime: 0\nkern.waketime: 0",
            "current_time": clock.monotonic(),
        }

    def test_additive_waiting_schedule_60s_then_360s_then_360s(self):
        """Collector must enforce additive 60s before session 0 and 300+60s before sessions 1 and 2."""
        dest = self.tmpdir / "output_additive"
        clock = self.ControlledClock(start_time=1000.0)

        with patch("run_p0_aa.observe_child", return_value=self.fake_obs), \
             patch("run_p0_aa.host_state", side_effect=lambda: self._fake_host_state(clock)), \
             patch("run_p0_aa.validate_inputs", return_value={"status": "valid", "cells": {"cell_0": self.cell_core}}):

            rc = p0.execute_pilot(
                manifest_path=self.m_path,
                schedule_path=self.s_path,
                destination=dest,
                enforce_host=False,
                session_pre_quiet_seconds=60.0,
                inter_session_cooldown_seconds=300.0,
                overall_deadline_seconds=2700.0,
                check_provenance=False,
                sleep_fn=clock.sleep,
                monotonic_fn=clock.monotonic,
            )

        self.assertEqual(rc, 0)

        # Session 0: 60s quiet = 12 steps of 5.0s
        s0_sleeps = clock.sleep_intervals[:12]
        self.assertEqual(len(s0_sleeps), 12)
        self.assertEqual(sum(s0_sleeps), 60.0)

        # Session 1: 300s cooldown (60 steps) + 60s quiet (12 steps) = 360.0s (72 steps)
        s1_sleeps = clock.sleep_intervals[12:12+72]
        self.assertEqual(len(s1_sleeps), 72)
        self.assertEqual(sum(s1_sleeps), 360.0)

        # Session 2: 300s cooldown (60 steps) + 60s quiet (12 steps) = 360.0s (72 steps)
        s2_sleeps = clock.sleep_intervals[12+72:12+72+72]
        self.assertEqual(len(s2_sleeps), 72)
        self.assertEqual(sum(s2_sleeps), 360.0)

        # Total sleep across all 3 sessions = 60 + 360 + 360 = 780.0s
        self.assertEqual(len(clock.sleep_intervals), 156)
        self.assertEqual(sum(clock.sleep_intervals), 780.0)

        # Verify completed run metadata
        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "completed")
        self.assertEqual(meta["completed_pairs"], 3)

    def test_overall_deadline_enforced_during_quiet_period(self):
        """Overall campaign deadline must be enforced during session quiet periods."""
        dest = self.tmpdir / "output_deadline_quiet"
        clock = self.ControlledClock(start_time=1000.0)

        with patch("run_p0_aa.observe_child", return_value=self.fake_obs), \
             patch("run_p0_aa.host_state", side_effect=lambda: self._fake_host_state(clock)), \
             patch("run_p0_aa.validate_inputs", return_value={"status": "valid", "cells": {"cell_0": self.cell_core}}):

            with self.assertRaises(p0.ProcessExecutionError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.m_path,
                    schedule_path=self.s_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=60.0,
                    inter_session_cooldown_seconds=300.0,
                    overall_deadline_seconds=35.0,  # Expires during session 0 quiet period (60s)
                    check_provenance=False,
                    sleep_fn=clock.sleep,
                    monotonic_fn=clock.monotonic,
                )

            self.assertIn("Overall campaign deadline expired during session quiet period", str(ctx.exception))

    def test_overall_deadline_enforced_during_cooldown(self):
        """Overall campaign deadline must be enforced during inter-session cooldown."""
        dest = self.tmpdir / "output_deadline_cooldown"
        clock = self.ControlledClock(start_time=1000.0)

        with patch("run_p0_aa.observe_child", return_value=self.fake_obs), \
             patch("run_p0_aa.host_state", side_effect=lambda: self._fake_host_state(clock)), \
             patch("run_p0_aa.validate_inputs", return_value={"status": "valid", "cells": {"cell_0": self.cell_core}}):

            with self.assertRaises(p0.ProcessExecutionError) as ctx:
                p0.execute_pilot(
                    manifest_path=self.m_path,
                    schedule_path=self.s_path,
                    destination=dest,
                    enforce_host=False,
                    session_pre_quiet_seconds=60.0,
                    inter_session_cooldown_seconds=300.0,
                    overall_deadline_seconds=200.0,  # Allows session 0 (60s), expires during session 1 cooldown (300s)
                    check_provenance=False,
                    sleep_fn=clock.sleep,
                    monotonic_fn=clock.monotonic,
                )

            self.assertIn("Overall campaign deadline expired during inter-session cooldown", str(ctx.exception))


def _make_valid_lifecycle_report(cell: dict, server_bin: str = None, server_sha: str = None) -> dict:
    return {
        "schema_version": "measure_e2e.v1",
        "driver": {
            "name": "measure_e2e",
            "version": "0.3.0",
            "build_profile": "release (optimized performance build)",
        },
        "server_provenance": {
            "binary_path": server_bin or cell.get("server_binary", "/fake/server"),
            "binary_sha256": server_sha or cell.get("server_binary_sha256", "a" * 64),
            "instance_id": "srv-12345-abcdef0123456789-0001",
        },
        "configuration": {
            "dataset_tier": cell.get("tier", "small"),
            "node_count": cell.get("nodes", 1000),
            "edge_count": cell.get("edges", 2000),
            "event_count": cell.get("events", 500),
            "query_count": cell.get("queries", 1000),
            "batch_size": cell.get("batch_size", 100),
            "seed": cell.get("seed", 42),
            "runs": cell.get("repetitions", cell.get("runs", 1)),
            "requested_engine": cell["engine"],
            "effective_engine": cell["engine"],
            "engine_experimental": False,
            "spawn_server": True,
            "server_address": "127.0.0.1:54321",
        },
        "timing_boundaries": {
            "units": {"duration_ns": "raw Instant", "duration_ms": "ms"},
            "phase_definitions": {"snapshot_import": "desc"},
        },
        "runs": [
            {
                "run_index": 0,
                "seed": cell.get("seed", 42),
                "snapshot_import": {
                    "duration_ns": 1500000,
                    "duration_ms": 1.5,
                    "elements_per_sec": 2000000.0,
                    "element_count": cell.get("nodes", 1000) + cell.get("edges", 2000),
                },
                "catch_up": {
                    "duration_ns": 2000000,
                    "duration_ms": 2.0,
                    "events_per_sec": 250000.0,
                    "event_count": cell.get("events", 500),
                    "batch_count": 5,
                },
                "barrier": {
                    "duration_ns": 500000,
                    "duration_ms": 0.5,
                },
                "registration_through_barrier": {
                    "duration_ns": 4000000,
                    "duration_ms": 4.0,
                },
                "query": {
                    "total_queries": cell.get("queries", 1000),
                    "verified_queries": cell.get("queries", 1000),
                    "oracle_agreement_pct": 100.0,
                    "qps": 12000.0,
                    "total_duration_ns": 83333333,
                    "total_duration_ms": 83.333,
                    "latency_ns": {
                        "min": 40,
                        "mean": 83.3,
                        "p50": 80,
                        "p95": 140,
                        "p99": 200,
                        "max": 500,
                    },
                    "latency_us": {
                        "min": 0.04,
                        "mean": 0.0833,
                        "p50": 0.08,
                        "p95": 0.14,
                        "p99": 0.20,
                        "max": 0.50,
                    },
                },
                "memory": {
                    "sampled_final_rss_kib": 8192,
                    "sampled_final_rss_bytes": 8388608,
                    "sampled_max_rss_kib": 8192,
                    "sampled_max_rss_bytes": 8388608,
                    "sampling_interval_ms": 25,
                    "note": "ps polling",
                },
                "restart_recovery": {
                    "duration_ns": 35000000,
                    "duration_ms": 35.0,
                },
            }
        ],
        "summary": None,
    }


def _make_valid_batch_report(cell: dict, batch_size: int = 64, server_bin: str = None, server_sha: str = None) -> dict:
    total_ops = 2000
    b = batch_size
    full_b = total_ops // b
    rem = total_ops % b
    part_b = rem if rem > 0 else None
    actual_reqs = full_b + (1 if rem > 0 else 0)

    return {
        "schema_version": "measure_e2e.batch.v1",
        "driver": {
            "name": "measure_e2e",
            "version": "0.3.0",
            "build_profile": "release (optimized performance build)",
        },
        "server_provenance": {
            "binary_path": server_bin or cell.get("server_binary", "/fake/server"),
            "binary_sha256": server_sha or cell.get("server_binary_sha256", "b" * 64),
            "instance_id": "srv-99999-abcdef0123456789-0001",
        },
        "configuration": {
            "scenario": "standalone-batch",
            "trace_identity": "deterministic_500_round_link_cut_reversal",
            "workload_description": "500 rounds of reversible operations",
            "topology": "1000 isolated nodes",
            "node_count": 1000,
            "seed": cell.get("seed", 42),
            "batch_size": b,
            "total_logical_operations": total_ops,
            "link_operations": 500,
            "cut_operations": 500,
            "query_operations": 1000,
            "actual_request_count": actual_reqs,
            "full_batches": full_b,
            "partial_batch_size": part_b,
            "warmup": "50 queries via /v1/batch",
            "connection_model": "sequential loopback TCP Connection: close",
            "runs": cell.get("repetitions", cell.get("runs", 1)),
            "requested_engine": cell["engine"],
            "effective_engine": cell["engine"],
            "engine_experimental": False,
            "spawn_server": True,
            "server_address": "127.0.0.1:54321",
        },
        "timing_boundaries": {
            "units": {"duration_ns": "ns"},
            "notes": {"latency_concept": "notes"},
        },
        "runs": [
            {
                "run_index": 0,
                "seed": cell.get("seed", 42),
                "setup": {
                    "duration_ns": 5000000,
                    "duration_ms": 5.0,
                    "created_nodes": 1000,
                    "initial_state_version": "1000",
                },
                "warmup": {
                    "duration_ns": 2000000,
                    "duration_ms": 2.0,
                    "query_count": 50,
                    "post_warmup_state_version": "1000",
                },
                "measurement_window": {
                    "duration_ns": 25000000,
                    "duration_ms": 25.0,
                    "total_logical_operations": 2000,
                    "effective_mutations": 1000,
                    "elapsed_window_ns_per_logical_op": 12500.0,
                    "logical_ops_per_sec": 80000.0,
                    "requests_per_sec": (actual_reqs / 0.025),
                },
                "request_latency": {
                    "total_requests": actual_reqs,
                    "latency_ns": {
                        "min": 100000,
                        "mean": 700000.0,
                        "p50": 650000,
                        "p95": 900000,
                        "p99": 950000,
                        "max": 1000000,
                    },
                    "latency_us": {
                        "min": 100.0,
                        "mean": 700.0,
                        "p50": 650.0,
                        "p95": 900.0,
                        "p99": 950.0,
                        "max": 1000.0,
                    },
                },
                "verification": {
                    "all_items_matched": True,
                    "total_verified_items": 2000,
                    "expected_final_state_version": "2000",
                    "actual_final_state_version": "2000",
                    "final_node_count": 1000,
                    "final_edge_count": 0,
                },
                "memory": {
                    "sampled_final_rss_kib": 9216,
                    "sampled_final_rss_bytes": 9437184,
                    "sampled_max_rss_kib": 9216,
                    "sampled_max_rss_bytes": 9437184,
                    "sampling_interval_ms": 25,
                    "note": "ps polling",
                },
            }
        ],
        "summary": None,
    }


class HttpJsonReportParserTests(unittest.TestCase):
    """Unit tests for strict parsing and validation of measure_e2e.v1 and measure_e2e.batch.v1 reports."""

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)
        self.cell_lifecycle = {
            "cell_id": "http_lifecycle_compact_bfs_small",
            "type": "http",
            "engine": "compact-bfs",
            "tier": "small",
            "nodes": 1000,
            "edges": 2000,
            "events": 500,
            "queries": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.v1",
            "server_binary": "/path/to/knotrel-server",
            "server_binary_sha256": "a" * 64,
        }
        self.cell_batch = {
            "cell_id": "http_standalone_batch_b64_compact_bfs",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 64,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": "/path/to/knotrel-server",
            "server_binary_sha256": "b" * 64,
        }

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def test_batch_warmup_regimes_cannot_be_mixed(self):
        report = _make_valid_batch_report(self.cell_batch)
        report["configuration"]["warmup_chunk_size"] = 8
        report["runs"][0]["warmup"]["request_count"] = 7
        with self.assertRaises(p0.QualificationBlockerError):
            p0.parse_http_batch_json(report, self.cell_batch)
        cell = dict(self.cell_batch, warmup_chunk_size=8)
        p0.parse_http_batch_json(report, cell)
        report["runs"][0]["warmup"]["request_count"] = 1
        with self.assertRaises(p0.QualificationBlockerError):
            p0.parse_http_batch_json(report, cell)

    def test_valid_lifecycle_report_parsing(self):
        """Valid measure_e2e.v1 JSON report passes validation with exact expected metrics."""
        report = _make_valid_lifecycle_report(self.cell_lifecycle)
        rpath = self.tmpdir / "report_lifecycle.json"
        p0.save_json(rpath, report)

        parsed = p0.parse_http_json_report(rpath, self.cell_lifecycle)
        self.assertEqual(parsed["schema_version"], "measure_e2e.v1")
        exp = parsed["exported_metrics"]
        self.assertEqual(exp["oracle_agreement_pct"], 100.0)
        self.assertEqual(exp["time_to_ready_ms"], 4.0)
        self.assertEqual(exp["query_qps"], 12000.0)
        self.assertEqual(exp["query_latency_p50_us"], 0.08)
        self.assertEqual(exp["query_latency_p95_us"], 0.14)
        self.assertEqual(exp["query_latency_p99_us"], 0.20)
        self.assertAlmostEqual(exp["final_sampled_rss_mib"], 8.0)

    def test_valid_batch_report_parsing_across_sizes(self):
        """Synthetic valid measure_e2e.batch.v1 reports pass across B in {1, 8, 64, 256}."""
        for b in (1, 8, 64, 256):
            cell = copy.deepcopy(self.cell_batch)
            cell["batch_size"] = b
            report = _make_valid_batch_report(cell, batch_size=b)
            rpath = self.tmpdir / f"report_batch_{b}.json"
            p0.save_json(rpath, report)

            parsed = p0.parse_http_json_report(rpath, cell)
            self.assertEqual(parsed["schema_version"], "measure_e2e.batch.v1")
            exp = parsed["exported_metrics"]
            self.assertEqual(exp["batch_size"], b)
            self.assertEqual(exp["total_logical_operations"], 2000)
            self.assertEqual(exp["effective_mutations"], 1000)
            self.assertEqual(exp["verified_items"], 2000)
            self.assertTrue(exp["all_items_matched"])
            self.assertEqual(exp["window_duration_ms"], 25.0)

    def test_actual_smoke_b1_captured_fixture_accepted(self):
        """Captured smoke execution report (B=1) from actual driver passes qualification with exact emitted schema."""
        self.assertTrue(SMOKE_B1_FIXTURE_PATH.is_file(), f"Fixture missing at {SMOKE_B1_FIXTURE_PATH}")
        cell_b1 = {
            "cell_id": "http_standalone_batch_b1_compact_bfs",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 1,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": "/synthetic/knotrel-server",
            "server_binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        }
        parsed = p0.parse_http_json_report(SMOKE_B1_FIXTURE_PATH, cell_b1)
        self.assertEqual(parsed["schema_version"], "measure_e2e.batch.v1")
        exp = parsed["exported_metrics"]
        self.assertEqual(exp["batch_size"], 1)
        self.assertEqual(exp["total_requests"], 2000)
        self.assertEqual(exp["total_logical_operations"], 2000)
        self.assertEqual(exp["effective_mutations"], 1000)
        self.assertEqual(exp["verified_items"], 2000)
        self.assertTrue(exp["all_items_matched"])
        self.assertEqual(exp["final_sampled_rss_mib"], 7.09)
        self.assertEqual(exp["sampled_max_rss_mib"], 7.09)
        self.assertAlmostEqual(exp["window_duration_ms"], 187.35, places=2)

    def test_batch_report_rejected_on_trace_identity_mismatch(self):
        """Captured smoke report must be rejected if trace_identity does not match the driver's exact contract."""
        cell_b1 = {
            "cell_id": "http_standalone_batch_b1_compact_bfs",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 1,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": "/synthetic/knotrel-server",
            "server_binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        }
        raw_data = json.loads(SMOKE_B1_FIXTURE_PATH.read_text(encoding="utf-8"))

        for bad_id in ("splitmix64-seed42-500rounds-2000ops", "custom_trace_v2", "", "unknown_identity"):
            corrupted = copy.deepcopy(raw_data)
            corrupted["configuration"]["trace_identity"] = bad_id
            rpath = self.tmpdir / f"corrupted_trace_{hash(bad_id)}.json"
            p0.save_json(rpath, corrupted)

            with self.assertRaises(p0.QualificationBlockerError) as ctx:
                p0.parse_http_json_report(rpath, cell_b1)
            self.assertIn("Trace identity mismatch", str(ctx.exception))

    def test_batch_report_rejected_on_seed_mismatch(self):
        """Captured smoke report must be rejected if configuration seed does not match the manifest."""
        cell_b1 = {
            "cell_id": "http_standalone_batch_b1_compact_bfs",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 1,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": "/synthetic/knotrel-server",
            "server_binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        }
        raw_data = json.loads(SMOKE_B1_FIXTURE_PATH.read_text(encoding="utf-8"))
        raw_data["configuration"]["seed"] = 9999
        rpath = self.tmpdir / "corrupted_seed.json"
        p0.save_json(rpath, raw_data)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, cell_b1)
        self.assertIn("Seed mismatch", str(ctx.exception))

    def test_batch_report_rejected_on_node_count_mismatch(self):
        """Captured smoke report must be rejected if node_count does not match manifest expectations."""
        cell_b1 = {
            "cell_id": "http_standalone_batch_b1_compact_bfs",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 1,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": "/synthetic/knotrel-server",
            "server_binary_sha256": "b156d39718434fb395cc19d2937513376f99819c8ac5e48963a3f776ab44ed4a",
        }
        raw_data = json.loads(SMOKE_B1_FIXTURE_PATH.read_text(encoding="utf-8"))
        raw_data["configuration"]["node_count"] = 500
        rpath = self.tmpdir / "corrupted_nodes.json"
        p0.save_json(rpath, raw_data)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, cell_b1)
        self.assertIn("Node count mismatch", str(ctx.exception))

    def test_batch_accounting_exactness_across_batch_sizes(self):
        """Synthetic batch reports must enforce the exact Rust schema batch accounting across sizes."""
        batch_expectations = {
            1: {"reqs": 2000, "full": 2000, "part": None},
            8: {"reqs": 250, "full": 250, "part": None},
            64: {"reqs": 32, "full": 31, "part": 16},
            256: {"reqs": 8, "full": 7, "part": 208},
        }
        for b, exp in batch_expectations.items():
            cell = copy.deepcopy(self.cell_batch)
            cell["batch_size"] = b
            report = _make_valid_batch_report(cell, batch_size=b)
            self.assertEqual(report["configuration"]["actual_request_count"], exp["reqs"])
            self.assertEqual(report["configuration"]["full_batches"], exp["full"])
            self.assertEqual(report["configuration"]["partial_batch_size"], exp["part"])

            # Corrupt request count
            bad_req_rep = copy.deepcopy(report)
            bad_req_rep["configuration"]["actual_request_count"] = exp["reqs"] + 1
            rpath = self.tmpdir / f"bad_req_{b}.json"
            p0.save_json(rpath, bad_req_rep)
            with self.assertRaises(p0.QualificationBlockerError) as ctx:
                p0.parse_http_json_report(rpath, cell)
            self.assertIn("Batch request count mismatch", str(ctx.exception))

            # Corrupt partial batch size
            if exp["part"] is not None:
                bad_part_rep = copy.deepcopy(report)
                bad_part_rep["configuration"]["partial_batch_size"] = exp["part"] + 1
                rpath2 = self.tmpdir / f"bad_part_{b}.json"
                p0.save_json(rpath2, bad_part_rep)
                with self.assertRaises(p0.QualificationBlockerError) as ctx2:
                    p0.parse_http_json_report(rpath2, cell)
                self.assertIn("Partial batch size mismatch", str(ctx2.exception))

    def test_rejection_of_wrong_engine_in_json(self):
        """Reporting effective or requested engine different from manifest cell must be rejected."""
        report = _make_valid_lifecycle_report(self.cell_lifecycle)
        report["configuration"]["effective_engine"] = "ett"
        rpath = self.tmpdir / "report_wrong_engine.json"
        p0.save_json(rpath, report)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, self.cell_lifecycle)
        self.assertIn("Effective engine mismatch", str(ctx.exception))

    def test_rejection_of_server_provenance_mismatch(self):
        """Mismatched server binary path or SHA-256 must be rejected."""
        # 1. Path mismatch
        r1 = _make_valid_lifecycle_report(self.cell_lifecycle)
        r1["server_provenance"]["binary_path"] = "/different/path/knotrel-server"
        p1 = self.tmpdir / "mismatch_path.json"
        p0.save_json(p1, r1)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p1, self.cell_lifecycle)
        self.assertIn("Server binary mismatch", str(ctx.exception))

        # 2. SHA-256 mismatch
        r2 = _make_valid_lifecycle_report(self.cell_lifecycle)
        r2["server_provenance"]["binary_sha256"] = "f" * 64
        p2 = self.tmpdir / "mismatch_sha.json"
        p0.save_json(p2, r2)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p2, self.cell_lifecycle)
        self.assertIn("Server binary SHA-256 mismatch", str(ctx.exception))

    def test_rejection_of_missing_repetitions(self):
        """Empty runs array or count mismatch must be rejected."""
        report = _make_valid_lifecycle_report(self.cell_lifecycle)
        report["runs"] = []
        rpath = self.tmpdir / "report_empty_runs.json"
        p0.save_json(rpath, report)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, self.cell_lifecycle)
        self.assertIn("Runs array length mismatch", str(ctx.exception))

    def test_rejection_of_incorrect_batch_accounting(self):
        """Incorrect actual_request_count or full_batches in standalone batch report must be rejected."""
        cell = copy.deepcopy(self.cell_batch)
        cell["batch_size"] = 64
        report = _make_valid_batch_report(cell, batch_size=64)
        report["configuration"]["actual_request_count"] = 31  # should be 32 (31 full + 1 partial)
        rpath = self.tmpdir / "report_bad_batch_count.json"
        p0.save_json(rpath, report)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, cell)
        self.assertIn("Batch request count mismatch", str(ctx.exception))

    def test_rejection_of_invalid_metrics_and_distributions(self):
        """Negative metrics, non-finite values, or inverted percentiles must be rejected."""
        # 1. Negative duration
        r1 = _make_valid_lifecycle_report(self.cell_lifecycle)
        r1["runs"][0]["snapshot_import"]["duration_ms"] = -1.0
        p1 = self.tmpdir / "neg_duration.json"
        p0.save_json(p1, r1)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p1, self.cell_lifecycle)
        self.assertIn("invalid or negative", str(ctx.exception))

        # 2. Inconsistent percentiles (p50 > p95)
        r2 = _make_valid_lifecycle_report(self.cell_lifecycle)
        r2["runs"][0]["query"]["latency_us"]["p50"] = 10.0
        r2["runs"][0]["query"]["latency_us"]["p95"] = 5.0
        p2 = self.tmpdir / "inverted_p50_p95.json"
        p0.save_json(p2, r2)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p2, self.cell_lifecycle)
        self.assertIn("Inconsistent percentile ordering", str(ctx.exception))

        # 3. Mean outside min-max
        r3 = _make_valid_lifecycle_report(self.cell_lifecycle)
        r3["runs"][0]["query"]["latency_us"]["mean"] = 999.0
        r3["runs"][0]["query"]["latency_us"]["max"] = 50.0
        p3 = self.tmpdir / "mean_out_of_bounds.json"
        p0.save_json(p3, r3)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p3, self.cell_lifecycle)
        self.assertIn("Mean outside [min, max]", str(ctx.exception))

    def test_rejection_of_measured_zero_rss(self):
        """Measured zero for sampled RSS must be rejected as an invalid metric."""
        report = _make_valid_lifecycle_report(self.cell_lifecycle)
        report["runs"][0]["memory"]["sampled_final_rss_bytes"] = 0
        rpath = self.tmpdir / "zero_rss.json"
        p0.save_json(rpath, report)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, self.cell_lifecycle)
        self.assertIn("measured zero is rejected", str(ctx.exception))

    def test_rejection_of_oracle_agreement_failure(self):
        """Oracle agreement under 100% must fail qualification."""
        report = _make_valid_lifecycle_report(self.cell_lifecycle)
        report["runs"][0]["query"]["oracle_agreement_pct"] = 99.9
        rpath = self.tmpdir / "bad_oracle.json"
        p0.save_json(rpath, report)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(rpath, self.cell_lifecycle)
        self.assertIn("Oracle agreement failure", str(ctx.exception))

    def test_rejection_of_batch_verification_failure(self):
        """Batch verification with all_items_matched=False or mutated final edges must fail."""
        # 1. all_items_matched is False
        r1 = _make_valid_batch_report(self.cell_batch)
        r1["runs"][0]["verification"]["all_items_matched"] = False
        p1 = self.tmpdir / "unmatched_items.json"
        p0.save_json(p1, r1)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p1, self.cell_batch)
        self.assertIn("all_items_matched is false", str(ctx.exception))

        # 2. Final edge count not 0
        r2 = _make_valid_batch_report(self.cell_batch)
        r2["runs"][0]["verification"]["final_edge_count"] = 1
        p2 = self.tmpdir / "dangling_edges.json"
        p0.save_json(p2, r2)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p2, self.cell_batch)
        self.assertIn("Final edge count mismatch", str(ctx.exception))

    def test_rejection_of_absent_and_malformed_json_reports(self):
        """Missing report file or non-JSON syntax must raise QualificationBlockerError."""
        # 1. Non-existent file
        non_existent = self.tmpdir / "non_existent.json"
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(non_existent, self.cell_lifecycle)
        self.assertIn("Expected HTTP JSON report file does not exist", str(ctx.exception))

        # 2. Malformed JSON
        malformed = self.tmpdir / "malformed.json"
        malformed.write_text("{ this is not valid json }")
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(malformed, self.cell_lifecycle)
        self.assertIn("malformed JSON", str(ctx.exception))

    def test_server_provenance_rejection_lifecycle(self):
        """measure_e2e.v1 reports must reject missing, null, empty, malformed, or mismatched SHA-256."""
        # 1. Missing binary_sha256
        r_missing = _make_valid_lifecycle_report(self.cell_lifecycle)
        del r_missing["server_provenance"]["binary_sha256"]
        p_missing = self.tmpdir / "lifecycle_missing_sha.json"
        p0.save_json(p_missing, r_missing)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_missing, self.cell_lifecycle)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 2. None binary_sha256
        r_none = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_none["server_provenance"]["binary_sha256"] = None
        p_none = self.tmpdir / "lifecycle_none_sha.json"
        p0.save_json(p_none, r_none)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_none, self.cell_lifecycle)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 3. Empty binary_sha256
        r_empty = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_empty["server_provenance"]["binary_sha256"] = ""
        p_empty = self.tmpdir / "lifecycle_empty_sha.json"
        p0.save_json(p_empty, r_empty)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_empty, self.cell_lifecycle)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 4. Malformed binary_sha256
        r_malformed = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_malformed["server_provenance"]["binary_sha256"] = "1234abcd"
        p_malformed = self.tmpdir / "lifecycle_malformed_sha.json"
        p0.save_json(p_malformed, r_malformed)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_malformed, self.cell_lifecycle)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 5. Mismatched binary_sha256
        r_mismatch = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_mismatch["server_provenance"]["binary_sha256"] = "f" * 64
        p_mismatch = self.tmpdir / "lifecycle_mismatch_sha.json"
        p0.save_json(p_mismatch, r_mismatch)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_mismatch, self.cell_lifecycle)
        self.assertIn("Server binary SHA-256 mismatch", str(ctx.exception))

        # 6. Mismatched binary_path
        r_bad_path = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_bad_path["server_provenance"]["binary_path"] = "/unexpected/knotrel-server"
        p_bad_path = self.tmpdir / "lifecycle_bad_path.json"
        p0.save_json(p_bad_path, r_bad_path)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_bad_path, self.cell_lifecycle)
        self.assertIn("Server binary mismatch", str(ctx.exception))

    def test_server_provenance_rejection_batch(self):
        """measure_e2e.batch.v1 reports must reject missing, null, empty, malformed, or mismatched SHA-256."""
        # 1. Missing binary_sha256
        r_missing = _make_valid_batch_report(self.cell_batch)
        del r_missing["server_provenance"]["binary_sha256"]
        p_missing = self.tmpdir / "batch_missing_sha.json"
        p0.save_json(p_missing, r_missing)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_missing, self.cell_batch)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 2. None binary_sha256
        r_none = _make_valid_batch_report(self.cell_batch)
        r_none["server_provenance"]["binary_sha256"] = None
        p_none = self.tmpdir / "batch_none_sha.json"
        p0.save_json(p_none, r_none)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_none, self.cell_batch)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 3. Empty binary_sha256
        r_empty = _make_valid_batch_report(self.cell_batch)
        r_empty["server_provenance"]["binary_sha256"] = ""
        p_empty = self.tmpdir / "batch_empty_sha.json"
        p0.save_json(p_empty, r_empty)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_empty, self.cell_batch)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 4. Malformed binary_sha256
        r_malformed = _make_valid_batch_report(self.cell_batch)
        r_malformed["server_provenance"]["binary_sha256"] = "1234abcd"
        p_malformed = self.tmpdir / "batch_malformed_sha.json"
        p0.save_json(p_malformed, r_malformed)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_malformed, self.cell_batch)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))

        # 5. Mismatched binary_sha256
        r_mismatch = _make_valid_batch_report(self.cell_batch)
        r_mismatch["server_provenance"]["binary_sha256"] = "f" * 64
        p_mismatch = self.tmpdir / "batch_mismatch_sha.json"
        p0.save_json(p_mismatch, r_mismatch)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_mismatch, self.cell_batch)
        self.assertIn("Server binary SHA-256 mismatch", str(ctx.exception))

        # 6. Mismatched binary_path
        r_bad_path = _make_valid_batch_report(self.cell_batch)
        r_bad_path["server_provenance"]["binary_path"] = "/unexpected/knotrel-server"
        p_bad_path = self.tmpdir / "batch_bad_path.json"
        p0.save_json(p_bad_path, r_bad_path)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_bad_path, self.cell_batch)
        self.assertIn("Server binary mismatch", str(ctx.exception))

    def test_server_provenance_resolution_from_manifest(self):
        """When cell omits server_binary_sha256, expected server SHA must resolve from manifest authoritative binary."""
        cell_without_sha = copy.deepcopy(self.cell_lifecycle)
        del cell_without_sha["server_binary_sha256"]
        del cell_without_sha["server_binary"]

        manifest = {
            "provenance": {
                "binaries": {
                    "knotrel_server": {
                        "path": "/canonical/knotrel-server",
                        "sha256": "d" * 64,
                    }
                }
            }
        }

        # 1. Matching report passes
        r_valid = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_valid["server_provenance"]["binary_path"] = "/canonical/knotrel-server"
        r_valid["server_provenance"]["binary_sha256"] = "d" * 64
        p_valid = self.tmpdir / "lifecycle_manifest_resolved.json"
        p0.save_json(p_valid, r_valid)
        parsed = p0.parse_http_json_report(p_valid, cell_without_sha, manifest=manifest)
        self.assertEqual(parsed["schema_version"], "measure_e2e.v1")

        # 2. Mismatched SHA fails
        r_mismatch = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_mismatch["server_provenance"]["binary_path"] = "/canonical/knotrel-server"
        r_mismatch["server_provenance"]["binary_sha256"] = "e" * 64
        p_mismatch = self.tmpdir / "lifecycle_manifest_mismatch.json"
        p0.save_json(p_mismatch, r_mismatch)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_mismatch, cell_without_sha, manifest=manifest)
        self.assertIn("Server binary SHA-256 mismatch", str(ctx.exception))

        # 3. Missing SHA in report fails
        r_missing = _make_valid_lifecycle_report(self.cell_lifecycle)
        r_missing["server_provenance"]["binary_path"] = "/canonical/knotrel-server"
        del r_missing["server_provenance"]["binary_sha256"]
        p_missing = self.tmpdir / "lifecycle_manifest_missing.json"
        p0.save_json(p_missing, r_missing)
        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            p0.parse_http_json_report(p_missing, cell_without_sha, manifest=manifest)
        self.assertIn("missing, null, empty, or malformed", str(ctx.exception))


class HttpJsonProcessIntegrationTests(unittest.TestCase):
    """Integration tests with fake processes executing through execute_pilot and observe_child."""

    def setUp(self):
        self.tmpdir_obj = tempfile.TemporaryDirectory()
        self.tmpdir = Path(self.tmpdir_obj.name)

        self.fake_server_bin = self.tmpdir / "knotrel-server"
        self.fake_server_bin.write_text("#!/bin/sh\nexit 0\n")
        self.fake_server_bin.chmod(0o755)

        self.cell_lifecycle = {
            "cell_id": "cell_lifecycle",
            "type": "http",
            "engine": "compact-bfs",
            "tier": "small",
            "nodes": 1000,
            "edges": 2000,
            "events": 500,
            "queries": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.v1",
            "server_binary": str(self.fake_server_bin),
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, "DRIVER_PLACEHOLDER"],
            "env": {"PATH": "/usr/bin:/bin"},
        }
        self.cell_batch = {
            "cell_id": "cell_batch",
            "type": "http",
            "engine": "compact-bfs",
            "batch_size": 64,
            "nodes": 1000,
            "seed": 42,
            "runs": 1,
            "report_schema": "measure_e2e.batch.v1",
            "server_binary": str(self.fake_server_bin),
            "cwd": str(self.tmpdir),
            "argv": [sys.executable, "DRIVER_PLACEHOLDER"],
            "env": {"PATH": "/usr/bin:/bin"},
        }

    def tearDown(self):
        self.tmpdir_obj.cleanup()

    def _run_mini_pilot(self, cell, driver_script):
        cell_def = copy.deepcopy(cell)
        cell_def["argv"] = [sys.executable, str(driver_script)]

        manifest = {
            "schema": "knotrel-p0-pilot-manifest-v1",
            "checkpoint": "P0-Coverage-Increment-1-Test",
            "pilot_design": {
                "total_cells": 1,
                "total_pairs": 1,
                "total_measured_launches": 2,
                "sessions_count": 1,
                "cells": [cell_def],
            },
            "provenance": {},
        }
        schedule = {
            "schema": "knotrel-p0-pilot-schedule-v1",
            "checkpoint": "P0-Coverage-Increment-1-Test",
            "total_cells": 1,
            "total_pairs": 1,
            "total_measured_runs": 2,
            "sessions": [
                {"session_id": 0, "seed": 120050, "pair_count": 1, "pre_quiet_seconds": 0}
            ],
            "pairs": [
                {
                    "pair_id": 0,
                    "session": 0,
                    "cell_id": cell_def["cell_id"],
                    "labels": ["A", "Aprime"],
                    "cwd": str(self.tmpdir),
                    "argv": [sys.executable, str(driver_script)],
                    "env": {"PATH": "/usr/bin:/bin"},
                }
            ],
        }

        m_path = self.tmpdir / "manifest.json"
        s_path = self.tmpdir / "schedule.json"
        dest = self.tmpdir / f"dest_{cell_def['cell_id']}"
        p0.save_json(m_path, manifest)
        p0.save_json(s_path, schedule)

        fake_host = {
            "platform": "darwin",
            "platform_machine": "arm64",
            "platform_system": "darwin",
            "power": "Now drawing from 'AC Power'",
            "thermal": "CPU_Speed_Limit = 100",
            "competing_workloads": [],
            "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
        }

        with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=fake_host):
            mock_val.return_value = {
                "status": "valid",
                "cells": {cell_def["cell_id"]: cell_def},
                "sessions_count": 1,
            }
            rc = p0.execute_pilot(
                manifest_path=m_path,
                schedule_path=s_path,
                destination=dest,
                enforce_host=False,
                session_pre_quiet_seconds=0.0,
                inter_session_cooldown_seconds=0.0,
                check_provenance=False,
            )
        return rc, dest

    def test_fake_process_successful_lifecycle_execution(self):
        """Fake driver emitting measure_e2e.v1 to allocated --json-out succeeds and records observations."""
        script = self.tmpdir / "fake_driver_lifecycle.py"
        rep = _make_valid_lifecycle_report(self.cell_lifecycle)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = Path(sys.argv[i + 1])
        break

if json_out:
    json_out.write_text({repr(rep_json)})

sys.stdout.write("Fake driver execution complete\\n")
sys.exit(0)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        rc, dest = self._run_mini_pilot(self.cell_lifecycle, script)
        self.assertEqual(rc, 0)
        pair_rec = p0.read_json(dest / "pair_000_cell_lifecycle.json")
        self.assertEqual(len(pair_rec["observations"]), 2)
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertEqual(obs0["exit_code"], 0)
        self.assertIsNotNone(obs0["json_report_path"])
        self.assertTrue(Path(obs0["json_report_path"]).exists())
        self.assertEqual(obs0["parsed_metrics"]["schema_version"], "measure_e2e.v1")

    def test_fake_process_successful_batch_execution(self):
        """Fake driver emitting measure_e2e.batch.v1 to allocated --json-out succeeds and records observations."""
        script = self.tmpdir / "fake_driver_batch.py"
        rep = _make_valid_batch_report(self.cell_batch, batch_size=64)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = Path(sys.argv[i + 1])
        break

if json_out:
    json_out.write_text({repr(rep_json)})

sys.stdout.write("Fake batch driver execution complete\\n")
sys.exit(0)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        rc, dest = self._run_mini_pilot(self.cell_batch, script)
        self.assertEqual(rc, 0)
        pair_rec = p0.read_json(dest / "pair_000_cell_batch.json")
        self.assertEqual(len(pair_rec["observations"]), 2)
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertEqual(obs0["exit_code"], 0)
        self.assertEqual(obs0["parsed_metrics"]["schema_version"], "measure_e2e.batch.v1")

    def test_fake_process_nonzero_exit_despite_valid_json_report(self):
        """Fake driver writing valid JSON report but exiting with nonzero code must be rejected and fail execution."""
        script = self.tmpdir / "fake_driver_failing_exit.py"
        rep = _make_valid_batch_report(self.cell_batch, batch_size=64)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import sys
from pathlib import Path

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = Path(sys.argv[i + 1])
        break

if json_out:
    json_out.write_text({repr(rep_json)})

sys.stderr.write("Server exited abnormally post-report\\n")
sys.exit(1)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        with self.assertRaises(p0.ProcessExecutionError) as ctx:
            self._run_mini_pilot(self.cell_batch, script)
        self.assertIn("exited with non-zero code 1", str(ctx.exception))

        dest = self.tmpdir / f"dest_{self.cell_batch['cell_id']}"
        pair_rec = p0.read_json(dest / "pair_000_cell_batch.json")
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "exit_code_failure")
        self.assertEqual(obs0["exit_code"], 1)
        self.assertIn("Server exited abnormally", obs0["raw_stderr"])
        self.assertIsNotNone(obs0["json_report_path"])
        self.assertTrue(Path(obs0["json_report_path"]).exists(), "Report artifact must be retained on failure")

    def test_fake_process_absent_json_report_raises_qualification_blocker(self):
        """Driver exiting 0 without creating the required JSON report file must raise QualificationBlockerError."""
        script = self.tmpdir / "fake_driver_no_json.py"
        script.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
        script.chmod(0o755)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            self._run_mini_pilot(self.cell_batch, script)
        self.assertIn("Expected HTTP JSON report file does not exist", str(ctx.exception))

    def test_rejection_of_unresolved_binary_hash_in_manifest(self):
        """Manifest with unresolved binary SHA-256 must be rejected by validate_inputs."""
        manifest = p0.read_json(p0.DEFAULT_MANIFEST_PATH)
        schedule = p0.read_json(p0.DEFAULT_SCHEDULE_PATH)
        m = copy.deepcopy(manifest)
        m["provenance"]["binaries"]["knotrel_server"]["sha256"] = "UNRESOLVED_PENDING_BUILD"

        with self.assertRaises(p0.ConfigurationValidationError) as ctx:
            p0.validate_inputs(m, schedule, check_provenance=True)
        self.assertIn("SHA-256 is unresolved", str(ctx.exception))

    def _run_mini_pilot_with_relative_dest(
        self, cell, driver_script, rel_dest_name="rel_campaign_output", child_cwd=None, absolute_dest=False
    ):
        collector_cwd = self.tmpdir / "collector_env"
        collector_cwd.mkdir(parents=True, exist_ok=True)
        if child_cwd is None:
            child_cwd = self.tmpdir / "child_env"
            child_cwd.mkdir(parents=True, exist_ok=True)

        cell_def = copy.deepcopy(cell)
        cell_def["argv"] = [sys.executable, str(driver_script)]
        cell_def["cwd"] = str(child_cwd)

        manifest = {
            "schema": "knotrel-p0-pilot-manifest-v1",
            "checkpoint": "P0-Coverage-Increment-1-Test",
            "pilot_design": {
                "total_cells": 1,
                "total_pairs": 1,
                "total_measured_launches": 2,
                "sessions_count": 1,
                "cells": [cell_def],
            },
            "provenance": {},
        }
        schedule = {
            "schema": "knotrel-p0-pilot-schedule-v1",
            "checkpoint": "P0-Coverage-Increment-1-Test",
            "total_cells": 1,
            "total_pairs": 1,
            "total_measured_runs": 2,
            "sessions": [
                {"session_id": 0, "seed": 120050, "pair_count": 1, "pre_quiet_seconds": 0}
            ],
            "pairs": [
                {
                    "pair_id": 0,
                    "session": 0,
                    "cell_id": cell_def["cell_id"],
                    "labels": ["A", "Aprime"],
                    "cwd": str(child_cwd),
                    "argv": [sys.executable, str(driver_script)],
                    "env": {"PATH": "/usr/bin:/bin"},
                }
            ],
        }

        m_path = collector_cwd / "manifest.json"
        s_path = collector_cwd / "schedule.json"
        dest_arg = (collector_cwd / rel_dest_name).resolve() if absolute_dest else Path(rel_dest_name)
        p0.save_json(m_path, manifest)
        p0.save_json(s_path, schedule)

        fake_host = {
            "platform": "darwin",
            "platform_machine": "arm64",
            "platform_system": "darwin",
            "power": "Now drawing from 'AC Power'",
            "thermal": "CPU_Speed_Limit = 100",
            "competing_workloads": [],
            "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
        }

        orig_cwd = os.getcwd()
        try:
            os.chdir(collector_cwd)
            with patch("run_p0_aa.validate_inputs") as mock_val, patch("run_p0_aa.host_state", return_value=fake_host):
                mock_val.return_value = {
                    "status": "valid",
                    "cells": {cell_def["cell_id"]: cell_def},
                    "sessions_count": 1,
                }
                rc = p0.execute_pilot(
                    manifest_path=m_path,
                    schedule_path=s_path,
                    destination=dest_arg,
                    enforce_host=False,
                    session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0,
                    check_provenance=False,
                )
        finally:
            os.chdir(orig_cwd)
        return rc, (collector_cwd / rel_dest_name).resolve()

    def test_relative_destination_with_differing_child_cwd_batch(self):
        """Regression test: Child with differing cwd must receive absolute --json-out for standalone batch reports."""
        script = self.tmpdir / "fake_driver_rel_dest_batch.py"
        rep = _make_valid_batch_report(self.cell_batch, batch_size=64)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import os
import sys

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = sys.argv[i + 1]
        break

if json_out:
    try:
        with open(json_out, "w") as f:
            f.write({repr(rep_json)})
    except Exception as e:
        sys.stderr.write(f"Failed to create JSON report file '{{json_out}}': {{e}}\\n")
        sys.exit(1)

sys.stdout.write("Fake batch driver completed\\n")
sys.exit(0)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        rc, dest = self._run_mini_pilot_with_relative_dest(self.cell_batch, script, rel_dest_name="rel_batch_dest")
        self.assertEqual(rc, 0)
        pair_rec = p0.read_json(dest / "pair_000_cell_batch.json")
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertEqual(obs0["exit_code"], 0)
        self.assertTrue(Path(obs0["json_report_path"]).is_absolute(), "Report path must be absolute")
        self.assertTrue(Path(obs0["json_report_path"]).exists(), "Report must exist at absolute location")
        self.assertEqual(obs0["parsed_metrics"]["schema_version"], "measure_e2e.batch.v1")

    def test_relative_destination_with_differing_child_cwd_lifecycle(self):
        """Regression test: Child with differing cwd must receive absolute --json-out for lifecycle reports."""
        script = self.tmpdir / "fake_driver_rel_dest_lifecycle.py"
        rep = _make_valid_lifecycle_report(self.cell_lifecycle)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import os
import sys

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = sys.argv[i + 1]
        break

if json_out:
    try:
        with open(json_out, "w") as f:
            f.write({repr(rep_json)})
    except Exception as e:
        sys.stderr.write(f"Failed to create JSON report file '{{json_out}}': {{e}}\\n")
        sys.exit(1)

sys.stdout.write("Fake lifecycle driver completed\\n")
sys.exit(0)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        rc, dest = self._run_mini_pilot_with_relative_dest(self.cell_lifecycle, script, rel_dest_name="rel_life_dest")
        self.assertEqual(rc, 0)
        pair_rec = p0.read_json(dest / "pair_000_cell_lifecycle.json")
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertEqual(obs0["exit_code"], 0)
        self.assertTrue(Path(obs0["json_report_path"]).is_absolute(), "Report path must be absolute")
        self.assertTrue(Path(obs0["json_report_path"]).exists(), "Report must exist at absolute location")
        self.assertEqual(obs0["parsed_metrics"]["schema_version"], "measure_e2e.v1")

    def test_absolute_destination_with_differing_child_cwd(self):
        """Absolute destinations continue to work seamlessly with differing child cwd."""
        script = self.tmpdir / "fake_driver_abs_dest.py"
        rep = _make_valid_batch_report(self.cell_batch, batch_size=64)
        rep_json = json.dumps(rep)
        script_code = f"""#!/usr/bin/env python3
import json
import os
import sys

json_out = None
for i, arg in enumerate(sys.argv):
    if arg == "--json-out" and i + 1 < len(sys.argv):
        json_out = sys.argv[i + 1]
        break

if json_out:
    try:
        with open(json_out, "w") as f:
            f.write({repr(rep_json)})
    except Exception as e:
        sys.stderr.write(f"Failed to create JSON report file '{{json_out}}': {{e}}\\n")
        sys.exit(1)

sys.stdout.write("Fake driver completed\\n")
sys.exit(0)
"""
        script.write_text(script_code)
        script.chmod(0o755)

        rc, dest = self._run_mini_pilot_with_relative_dest(
            self.cell_batch, script, rel_dest_name="abs_batch_dest", absolute_dest=True
        )
        self.assertEqual(rc, 0)
        pair_rec = p0.read_json(dest / "pair_000_cell_batch.json")
        obs0 = pair_rec["observations"][0]
        self.assertEqual(obs0["status"], "parsed_valid")
        self.assertTrue(Path(obs0["json_report_path"]).is_absolute())

    def test_relative_destination_existing_directory_rejected(self):
        """Destination directory already existing must be rejected with FileExistsError even when specified relatively."""
        collector_cwd = self.tmpdir / "collector_env_existing"
        collector_cwd.mkdir(parents=True, exist_ok=True)
        existing_rel = "already_exists_dir"
        (collector_cwd / existing_rel).mkdir(parents=True, exist_ok=True)

        m_path = collector_cwd / "manifest.json"
        s_path = collector_cwd / "schedule.json"
        p0.save_json(m_path, {})
        p0.save_json(s_path, {})

        orig_cwd = os.getcwd()
        try:
            os.chdir(collector_cwd)
            with self.assertRaises(FileExistsError) as ctx:
                p0.execute_pilot(m_path, s_path, destination=Path(existing_rel), enforce_host=False)
            self.assertIn("Destination directory already exists", str(ctx.exception))
        finally:
            os.chdir(orig_cwd)

    def test_relative_destination_missing_report_fails_qualification(self):
        """Relative destination where child exits 0 without creating report must fail with QualificationBlockerError."""
        script = self.tmpdir / "fake_driver_rel_no_report.py"
        script.write_text("#!/usr/bin/env python3\nimport sys\nsys.exit(0)\n")
        script.chmod(0o755)

        with self.assertRaises(p0.QualificationBlockerError) as ctx:
            self._run_mini_pilot_with_relative_dest(self.cell_batch, script, rel_dest_name="rel_missing_rep")
        self.assertIn("Expected HTTP JSON report file does not exist", str(ctx.exception))

    def test_relative_destination_nonzero_child_exit_fails(self):
        """Relative destination where child exits with nonzero code must fail with ProcessExecutionError."""
        script = self.tmpdir / "fake_driver_rel_nonzero_exit.py"
        script.write_text("#!/usr/bin/env python3\nimport sys\nsys.stderr.write('crash\\n')\nsys.exit(1)\n")
        script.chmod(0o755)

        with self.assertRaises(p0.ProcessExecutionError) as ctx:
            self._run_mini_pilot_with_relative_dest(self.cell_batch, script, rel_dest_name="rel_crash_rep")
        self.assertIn("exited with non-zero code 1", str(ctx.exception))



if __name__ == "__main__":
    unittest.main()
