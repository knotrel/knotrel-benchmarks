#!/usr/bin/env python3
"""Tests for the baseline/candidate (B/C) qualification mode of run_p0_aa.py.

The fixtures use real temporary Git checkouts, real hashed fake binaries and the real
validate_inputs/execute_pilot/observe_child path. Only host state is replaced, so the
tests never depend on AC power or launch a Knotrel benchmark.
"""

from __future__ import annotations

import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for path in (SCRIPTS_DIR, TESTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import prepare_bc_qualification as prep
import run_p0_aa as p0
from test_p0_aa import _make_valid_batch_report, _make_valid_lifecycle_report

CORE_CELL = "core_sparse_traversal_10k_compact-bfs_warmed"
BATCH_CELL = "http_standalone_batch_b64_compact_bfs"
LIFECYCLE_CELL = "http_lifecycle_compact_bfs_small"

FAKE_HOST = {
    "hostname": "test-host",
    "platform": "darwin",
    "platform_machine": "arm64",
    "platform_system": "darwin",
    "competing_workloads": [],
    "power": "Now drawing from 'AC Power'",
    "thermal": "CPU_Speed_Limit = 100",
    "sleep_wake": "kern.sleeptime: { sec = 0, usec = 0 }\nkern.waketime: { sec = 0, usec = 0 }",
}

CORE_REPORT = {
    "schema_version": 2,
    "engine": "knotrel-core/compact-bfs-v1",
    "workload": "chain-split-rejoin-v1",
    "benchmark_version": "0.3.0",
    "compiler": "rustc 1.100.0",
    "os": "macos",
    "arch": "aarch64",
    "debug_assertions": False,
    "timestamp_unix_seconds": 1792860000,
    "config": {"nodes": 1024, "rounds": 100, "seed": 42},
    "warmup": 0,
    "repetitions": [{
        "setup_ns": 45000,
        "workload_wall_ns": 30000,
        "measurements": {
            "connected": {"count": 200, "total_ns": 20000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200,
                          "p99_ns": 250, "max_ns": 300},
            "link": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95,
                     "max_ns": 100},
            "cut": {"count": 100, "total_ns": 5000, "min_ns": 5, "p50_ns": 50, "p95_ns": 90, "p99_ns": 95,
                    "max_ns": 100},
        },
        "query_true": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200,
                       "p99_ns": 250, "max_ns": 300},
        "query_false": {"count": 100, "total_ns": 10000, "min_ns": 10, "p50_ns": 100, "p95_ns": 200,
                        "p99_ns": 250, "max_ns": 300},
        "repeated_queries": None,
    }],
    "trace_fingerprint_fnv1a64": "ea72ce261a96e862",
    "initial_edges": 1023,
    "initial_density": 0.00195,
    "initial_max_degree": 2,
}

DRIVER_TEMPLATE = """#!{python}
# Shared fake measure_e2e driver: reports the server it was told to spawn.
import hashlib, json, sys
args = sys.argv[1:]
server = args[args.index("--server-bin") + 1]
out = args[args.index("--json-out") + 1]
report = json.loads({reports!r})[args[args.index("--scenario") + 1]]
label = "C" if server == {c_server!r} else "B"
with open({log!r}, "a") as fh:
    fh.write(json.dumps({{"role": "driver", "server": server, "label": label}}) + "\\n")
report["server_provenance"]["binary_path"] = server
with open(server, "rb") as fh:
    report["server_provenance"]["binary_sha256"] = hashlib.sha256(fh.read()).hexdigest()
fault = {fault!r}
if fault == "wrong_c_sha" and label == "C":
    report["server_provenance"]["binary_sha256"] = "0" * 64
if fault == "bad_second_run_c" and label == "C":
    report["runs"][1]["seed"] = 7
with open(out, "w") as fh:
    json.dump(report, fh)
if fault == "exit_c" and label == "C":
    sys.stderr.write("fake driver failure diagnostics\\n")
    sys.exit(3)
print("fake driver complete")
"""

HARNESS_TEMPLATE = """#!{python}
# Fake knotrel-benchmarks core harness for label {label}.
import json, os, sys
with open({log!r}, "a") as fh:
    fh.write(json.dumps({{"role": "harness", "binary": os.path.abspath(sys.argv[0])}}) + "\\n")
print({report!r})
"""


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(cwd: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-c", "user.name=test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false",
         *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    ).stdout.strip()


def _repo(path: Path, files: dict) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    for name, text in files.items():
        (path / name).write_text(text)
    _git(path, "add", "-A")
    _git(path, "commit", "-q", "-m", "fixture")
    return _git(path, "rev-parse", "HEAD")


def _lock(core_version: str, extra: str = "") -> str:
    return (
        "version = 4\n\n[[package]]\nname = \"knotrel-benchmarks\"\nversion = \"0.1.0\"\n\n"
        f"[[package]]\nname = \"knotrel-core\"\nversion = \"{core_version}\"\n\n"
        f"[[package]]\nname = \"serde\"\nversion = \"1.0.0\"\n{extra}"
    )


def _executable(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o755)
    return path


def _http_cell_fields(cell_id: str, scenario: str, old_driver: str, old_server: str) -> dict:
    common = ["--seed", "42", "--runs", "2"]
    if scenario == "standalone-batch":
        extra = {"batch_size": 64, "nodes": 1000, "report_schema": "measure_e2e.batch.v1"}
        argv = [old_driver, "--scenario", scenario] + common + ["--batch-size", "64"]
    else:
        extra = {"tier": "small", "nodes": 1000, "edges": 2000, "events": 500, "queries": 1000,
                 "report_schema": "measure_e2e.v1"}
        argv = [old_driver, "--scenario", scenario, "--dataset", "small"] + common
    argv += ["--engine", "compact-bfs", "--spawn-server", "--server-bin", old_server]
    return dict(
        extra, cell_id=cell_id, type="http", scenario=scenario, workload=scenario, engine="compact-bfs",
        seed=42, repetitions=2, primary_metric="historical", executable=old_driver, server_binary=old_server,
        cwd="/historical", argv=argv, env={"PATH": "/usr/bin:/bin", "KNOTREL_BIN": old_server},
    )


def _two_run_report(report: dict) -> str:
    report = copy.deepcopy(report)
    report["configuration"]["runs"] = 2
    second = copy.deepcopy(report["runs"][0])
    second["run_index"] = 1
    report["runs"].append(second)
    return report


class BCFixture:
    """Two labels with distinct hashed binaries, real checkouts and lockfiles."""

    def __init__(self, root: Path, fault: str = None, harness_commit_differs: bool = False):
        self.root = root
        self.log = root / "launches.jsonl"
        self.checkouts = {}
        commits = {}
        for label in p0.BC_LABELS:
            commits[(label, "knotrel")] = _repo(root / f"src/{label}/knotrel", {"Cargo.lock": _lock("0.2.0"),
                                                                              "README": label})
        bench_commit = _repo(root / "src/bench", {"README": "harness"})
        if harness_commit_differs:
            c_bench_commit = _repo(root / "src/bench-c", {"README": "other harness"})
        self.locks = {
            "B": _executable(root / "inputs/B/Cargo.lock", _lock("0.2.0")),
            "C": _executable(root / "inputs/C/Cargo.lock", _lock("0.3.0")),
        }
        self.sources = {
            CORE_CELL: dict(
                cell_id=CORE_CELL, type="core", workload="chain-split-rejoin-v1", workload_id="sparse", engine="compact-bfs",
                nodes=1024, rounds=100, seed=42, warmup=0, repetitions=1, primary_metric="historical",
                executable="/old/harness", cwd="/historical", env={"PATH": "/usr/bin:/bin"},
                argv=["/old/harness", "--workload", "chain-split-rejoin-v1", "--nodes", "1024", "--rounds", "100",
                      "--seed", "42", "--engine", "compact-bfs", "--warmup", "0", "--repetitions", "1"],
            ),
            BATCH_CELL: _http_cell_fields(BATCH_CELL, "standalone-batch", "/old/driver", "/old/server"),
            LIFECYCLE_CELL: _http_cell_fields(LIFECYCLE_CELL, "lifecycle", "/old/driver", "/old/server"),
        }
        self.servers = {
            label: _executable(root / f"bin/{label}/knotrel-server", f"#!/bin/sh\n# {label} server\nexit 0\n")
            for label in p0.BC_LABELS
        }
        report_cells = {key: dict(cell, runs=2) for key, cell in self.sources.items()}
        reports = {
            "standalone-batch": _two_run_report(_make_valid_batch_report(report_cells[BATCH_CELL])),
            "lifecycle": _two_run_report(_make_valid_lifecycle_report(report_cells[LIFECYCLE_CELL])),
        }
        self.driver = _executable(root / "bin/shared/measure_e2e", DRIVER_TEMPLATE.format(
            python=sys.executable, reports=json.dumps(reports), c_server=str(self.servers["C"]), log=str(self.log),
            fault=fault))
        self.harnesses = {
            label: _executable(root / f"bin/{label}/knotrel-benchmarks", HARNESS_TEMPLATE.format(
                python=sys.executable, label=label, log=str(self.log), report=json.dumps(CORE_REPORT)))
            for label in p0.BC_LABELS
        }
        self.identities = {
            "comparison_identities": {
                label: {
                    "description": f"fixture label {label}",
                    "binaries": {
                        "knotrel_server": {"path": str(self.servers[label]), "sha256": _sha(self.servers[label]),
                                           "source_commit": commits[(label, "knotrel")]},
                        "knotrel_benchmarks": {
                            "path": str(self.harnesses[label]), "sha256": _sha(self.harnesses[label]),
                            "source_commit": c_bench_commit if harness_commit_differs and label == "C" else bench_commit,
                        },
                    },
                    "checkouts": {
                        "knotrel_source": {"path": str(root / f"src/{label}/knotrel"),
                                           "commit": commits[(label, "knotrel")]},
                        "benchmarks_source": {
                            "path": str(root / ("src/bench-c" if harness_commit_differs and label == "C" else "src/bench")),
                            "commit": c_bench_commit if harness_commit_differs and label == "C" else bench_commit,
                        },
                    },
                    "lockfiles": {
                        "knotrel_lock": {"path": str(root / f"src/{label}/knotrel/Cargo.lock"),
                                         "sha256": _sha(root / f"src/{label}/knotrel/Cargo.lock")},
                        "benchmarks_lock_derived": {"path": str(self.locks[label]), "sha256": _sha(self.locks[label])},
                    },
                }
                for label in p0.BC_LABELS
            },
            "shared_binaries": {
                "measure_e2e": {"path": str(self.driver), "sha256": _sha(self.driver),
                                "source_checkout": str(root)},
            },
        }

    def source_manifest(self, cell_ids=None) -> dict:
        cells = [copy.deepcopy(self.sources[c]) for c in (cell_ids or self.sources)]
        return {"checkpoint": "Fixture-Source", "pilot_design": {"cells": cells}}

    def small_plan(self, cell_ids, per_session: int = 2, seeds=(7,)):
        """A non-qualification B/C plan small enough to execute with fake processes."""
        cells = prep.build_cells(self.source_manifest(cell_ids), cell_ids, self.identities["comparison_identities"],
                                 self.identities["shared_binaries"])
        pairs = prep.build_schedule_pairs(cells, seeds, per_session)
        manifest = {
            "schema": "knotrel-p0-pilot-manifest-bc-v1",
            "checkpoint": "BC-Collector-Test",
            "provenance": copy.deepcopy(self.identities),
            "pilot_design": {
                "comparison_mode": p0.BASELINE_CANDIDATE_MODE, "labels": list(p0.BC_LABELS),
                "total_cells": len(cells), "pairs_per_cell": per_session * len(seeds),
                "pairs_per_cell_per_session": per_session, "total_pairs": len(pairs),
                "total_measured_launches": 2 * len(pairs), "sessions_count": len(seeds),
                "session_seeds": list(seeds), "cells": cells,
            },
            "resource_budget": {"bundle_ceiling_bytes": p0.QUALIFICATION_BUNDLE_CEILING_BYTES},
        }
        schedule = {
            "schema": "knotrel-p0-pilot-schedule-bc-v1", "checkpoint": "BC-Collector-Test",
            "total_cells": len(cells), "total_pairs": len(pairs), "total_measured_runs": 2 * len(pairs),
            "sessions": [{"session_id": i, "seed": s, "pair_count": per_session * len(cells), "pre_quiet_seconds": 0}
                         for i, s in enumerate(seeds)],
            "pairs": pairs,
        }
        return manifest, schedule

    def launches(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text().splitlines()]


def _nine_cell_source(fx: BCFixture) -> dict:
    """Source manifest with all nine approved cell identities (fixture parameters)."""
    cells = []
    for cell_id in p0.QUALIFICATION_CELL_IDS:
        if cell_id.startswith("core_"):
            cell = copy.deepcopy(fx.sources[CORE_CELL])
        elif "lifecycle" in cell_id:
            cell = copy.deepcopy(fx.sources[LIFECYCLE_CELL])
        else:
            cell = copy.deepcopy(fx.sources[BATCH_CELL])
        cell["cell_id"] = cell_id
        cells.append(cell)
    return {"checkpoint": "Fixture-Increment-1", "pilot_design": {"cells": cells}}


class BCTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="knotrel-bc-")
        self.root = Path(self._tmp.name).resolve()

    def tearDown(self):
        self._tmp.cleanup()

    def fixture(self, **kwargs) -> BCFixture:
        return BCFixture(self.root / "fx", **kwargs)

    def execute(self, fx: BCFixture, manifest: dict, schedule: dict, host_side_effect=None):
        p0.save_json(self.root / "manifest.json", manifest)
        p0.save_json(self.root / "schedule.json", schedule)
        dest = self.root / "campaign"
        host = patch("run_p0_aa.host_state", side_effect=host_side_effect or (lambda: dict(FAKE_HOST)))
        with host, redirect_stdout(io.StringIO()):
            try:
                rc = p0.execute_pilot(
                    manifest_path=self.root / "manifest.json", schedule_path=self.root / "schedule.json",
                    destination=dest, enforce_host=False, session_pre_quiet_seconds=0.0,
                    inter_session_cooldown_seconds=0.0, check_provenance=True,
                )
                return rc, dest, None
            except Exception as exc:  # the collector re-raises after recording metadata
                return None, dest, exc


class PlanGenerationTests(BCTestCase):
    def test_main_plan_matches_approved_design(self):
        fx = self.fixture()
        plan = prep.build_plan(_nine_cell_source(fx), "0" * 64, fx.identities, "main",
                               p0.QUALIFICATION_CELL_IDS, (11, 12, 13))
        design, schedule = plan["manifest"]["pilot_design"], plan["schedule"]
        self.assertEqual((design["total_cells"], design["total_pairs"], design["total_measured_launches"]),
                         (9, 108, 216))
        self.assertEqual(design["additional_child_launches"]["total_child_servers"], 4 * 12 * 2 + 12 * 2 * 2)
        self.assertEqual(design["total_process_launches"], 216 + 144)
        self.assertEqual(plan["manifest"]["resource_budget"]["bundle_ceiling_bytes"], 52_428_800)
        for session in range(3):
            for cell_id in p0.QUALIFICATION_CELL_IDS:
                orders = [p["labels"] for p in schedule["pairs"] if p["session"] == session and p["cell_id"] == cell_id]
                self.assertEqual(sorted(map(tuple, orders)), [("B", "C")] * 2 + [("C", "B")] * 2)
        by_id = {c["cell_id"]: c for c in design["cells"]}
        self.assertEqual(by_id[CORE_CELL]["primary_metric"], "workload_wall_ns")
        self.assertEqual(by_id[LIFECYCLE_CELL]["primary_metric"], "time_to_ready_ms")
        batch = by_id[BATCH_CELL]
        self.assertEqual(batch["primary_metric"], "window_duration_ns")
        self.assertEqual(batch["warmup_chunk_size"], 50)
        for label in p0.BC_LABELS:
            argv = batch["launch_by_label"][label]["argv"]
            self.assertEqual(argv[-2:], ["--batch-warmup-chunk-size", "50"])
            self.assertEqual(argv[argv.index("--server-bin") + 1], str(fx.servers[label]))
            self.assertEqual(by_id[CORE_CELL]["launch_by_label"][label]["argv"][0], str(fx.harnesses[label]))

    def test_seeded_schedule_is_reproducible_and_seed_sensitive(self):
        fx = self.fixture()
        build = lambda seeds: prep.build_plan(_nine_cell_source(fx), "0" * 64, fx.identities, "main",
                                              p0.QUALIFICATION_CELL_IDS, seeds)["schedule"]["pairs"]
        order = lambda pairs: [(p["cell_id"], p["labels"]) for p in pairs]
        self.assertEqual(order(build((1, 2, 3))), order(build((1, 2, 3))))
        self.assertNotEqual(order(build((1, 2, 3))), order(build((4, 5, 6))))

    def test_extension_accepts_approved_subset_only(self):
        fx = self.fixture()
        plan = prep.build_plan(_nine_cell_source(fx), "0" * 64, fx.identities, "extension", [BATCH_CELL], (1, 2, 3))
        self.assertEqual(plan["schedule"]["total_pairs"], 12)
        source = _nine_cell_source(fx)
        source["pilot_design"]["cells"][0]["cell_id"] = "core_unapproved"
        with self.assertRaisesRegex(prep.PlanError, "non-empty subset"):
            prep.build_plan(source, "0" * 64, fx.identities, "extension", ["core_unapproved"], (1, 2, 3))

    def test_main_phase_requires_all_nine_cells(self):
        fx = self.fixture()
        with self.assertRaisesRegex(prep.PlanError, "exactly the approved 9 cells"):
            prep.build_plan(_nine_cell_source(fx), "0" * 64, fx.identities, "main",
                            p0.QUALIFICATION_CELL_IDS[:8], (1, 2, 3))

    def test_generator_cli_refuses_existing_output(self):
        fx = self.fixture()
        p0.save_json(self.root / "identities.json", fx.identities)
        p0.save_json(self.root / "source.json", _nine_cell_source(fx))
        out = self.root / "plan"
        args = [str(out), "--identities", str(self.root / "identities.json"), "--source-manifest",
                str(self.root / "source.json")]
        with redirect_stdout(io.StringIO()):
            self.assertEqual(prep.main(args), 0)
        manifest, schedule = p0.read_json(out / "manifest.json"), p0.read_json(out / "schedule.json")
        self.assertEqual(manifest["pilot_design"]["session_seeds"], list(prep.DEFAULT_SESSION_SEEDS["main"]))
        self.assertEqual(manifest["pilot_design"]["source_manifest"]["sha256"], _sha(self.root / "source.json"))
        p0.validate_inputs(manifest, schedule, check_provenance=True)
        with self.assertRaises(SystemExit), patch("sys.stderr", io.StringIO()):
            prep.main(args)


class ScheduleValidationTests(BCTestCase):
    def setUp(self):
        super().setUp()
        self.fx = self.fixture()
        plan = prep.build_plan(_nine_cell_source(self.fx), "0" * 64, self.fx.identities, "main",
                               p0.QUALIFICATION_CELL_IDS, (1, 2, 3))
        self.manifest, self.schedule = plan["manifest"], plan["schedule"]

    def test_generated_plan_validates(self):
        summary = p0.validate_inputs(self.manifest, self.schedule, check_provenance=False)
        self.assertTrue(summary["baseline_candidate"])
        self.assertEqual(summary["labels"], p0.BC_LABELS)
        self.assertEqual(summary["bundle_ceiling_bytes"], 52_428_800)

    def test_order_imbalance_rejected(self):
        pair = next(p for p in self.schedule["pairs"] if p["labels"] == ["C", "B"])
        pair["labels"] = ["B", "C"]
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "label imbalance"):
            p0.validate_inputs(self.manifest, self.schedule, check_provenance=False)

    def test_cross_session_imbalance_rejected_even_when_cell_totals_balance(self):
        cell_pairs = [p for p in self.schedule["pairs"] if p["cell_id"] == CORE_CELL]
        s0 = next(p for p in cell_pairs if p["session"] == 0 and p["labels"] == ["C", "B"])
        s1 = next(p for p in cell_pairs if p["session"] == 1 and p["labels"] == ["B", "C"])
        s0["labels"], s1["labels"] = ["B", "C"], ["C", "B"]
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "session 0 label imbalance"):
            p0.validate_inputs(self.manifest, self.schedule, check_provenance=False)

    def test_aa_labels_rejected_in_bc_schedule(self):
        self.schedule["pairs"][0]["labels"] = ["A", "Aprime"]
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "B,C or C,B"):
            p0.validate_inputs(self.manifest, self.schedule, check_provenance=False)

    def test_changed_tolerance_inputs_rejected(self):
        for mutate, message in (
            (lambda m: m["resource_budget"].update(bundle_ceiling_bytes=p0.PROPOSED_DISK_CEILING_BYTES),
             "bundle ceiling"),
            (lambda m: m["pilot_design"]["cells"][0].update(primary_metric="setup_ns"), "primary_metric"),
            (lambda m: m["pilot_design"].pop("qualification_protocol"), "must declare qualification_protocol"),
        ):
            manifest = copy.deepcopy(self.manifest)
            mutate(manifest)
            with self.subTest(message), self.assertRaisesRegex(p0.ConfigurationValidationError, message):
                p0.validate_inputs(manifest, self.schedule, check_provenance=False)

    def test_batch_warmup_chunk_required(self):
        manifest, schedule = copy.deepcopy(self.manifest), copy.deepcopy(self.schedule)
        for cell in [c for c in manifest["pilot_design"]["cells"] if c["cell_id"] == BATCH_CELL] + [
                p for p in schedule["pairs"] if p["cell_id"] == BATCH_CELL]:
            cell_launches = cell["launch_by_label"]
            for label in p0.BC_LABELS:
                cell_launches[label]["argv"] = cell_launches[label]["argv"][:-2]
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "batch-warmup-chunk-size 50"):
            p0.validate_inputs(manifest, schedule, check_provenance=False)

    def test_aa_and_bc_inputs_cannot_be_mixed(self):
        schedule = dict(self.schedule, schema="knotrel-p0-pilot-schedule-v1")
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "requires a knotrel-p0-pilot-schedule-bc"):
            p0.validate_inputs(self.manifest, schedule, check_provenance=False)


class LabelBindingTests(BCTestCase):
    """Each label must launch exactly its own binaries; nothing else may differ."""

    def setUp(self):
        super().setUp()
        self.fx = self.fixture()
        self.manifest, self.schedule = self.fx.small_plan([CORE_CELL, BATCH_CELL])

    def mutate_launch(self, cell_id, label, mutate):
        for holder in [c for c in self.manifest["pilot_design"]["cells"] if c["cell_id"] == cell_id] + [
                p for p in self.schedule["pairs"] if p["cell_id"] == cell_id]:
            mutate(holder["launch_by_label"][label])

    def assert_rejected(self, message):
        with self.assertRaisesRegex(p0.ConfigurationValidationError, message):
            p0.validate_inputs(self.manifest, self.schedule, check_provenance=False)

    def test_candidate_launching_baseline_server_rejected(self):
        def swap(launch):
            argv = launch["argv"]
            argv[argv.index("--server-bin") + 1] = str(self.fx.servers["B"])
        self.mutate_launch(BATCH_CELL, "C", swap)
        self.assert_rejected("--server-bin must select label C server")

    def test_candidate_report_expectation_naming_baseline_server_rejected(self):
        self.mutate_launch(BATCH_CELL, "C", lambda l: l.update(server_binary_sha256=_sha(self.fx.servers["B"])))
        self.assert_rejected("report expectations must name label C server")

    def test_knotrel_bin_mismatch_rejected(self):
        self.mutate_launch(BATCH_CELL, "B", lambda l: l["env"].update(KNOTREL_BIN=str(self.fx.servers["C"])))
        self.assert_rejected("KNOTREL_BIN must select label B server")

    def test_baseline_core_launching_candidate_harness_rejected(self):
        self.mutate_launch(CORE_CELL, "B", lambda l: l.update(argv=[str(self.fx.harnesses["C"])] + l["argv"][1:]))
        self.assert_rejected("label B core harness")

    def test_non_binary_argv_difference_rejected(self):
        self.mutate_launch(CORE_CELL, "C", lambda l: l["argv"].extend(["--warmup", "5"]))
        self.assert_rejected("differ in more than their label binary selection")

    def test_non_binary_env_difference_rejected(self):
        self.mutate_launch(BATCH_CELL, "C", lambda l: l["env"].update(EXTRA="1"))
        self.assert_rejected("differ in more than their label binary selection")

    def test_pair_launch_must_match_cell(self):
        self.schedule["pairs"][0]["launch_by_label"]["C"]["argv"].append("--extra")
        self.assert_rejected("does not match cell")


class ProvenanceTests(BCTestCase):
    def setUp(self):
        super().setUp()
        self.fx = self.fixture()
        self.manifest, self.schedule = self.fx.small_plan([CORE_CELL, BATCH_CELL])

    def assert_rejected(self, message):
        with self.assertRaisesRegex(p0.ConfigurationValidationError, message):
            p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)

    def test_valid_provenance_accepted(self):
        p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)

    def test_hash_mismatch_rejected_for_each_label_and_role(self):
        targets = [("B", "knotrel_server", self.fx.servers["B"]), ("C", "knotrel_server", self.fx.servers["C"]),
                   ("B", "knotrel_benchmarks", self.fx.harnesses["B"]),
                   ("C", "knotrel_benchmarks", self.fx.harnesses["C"])]
        for label, role, path in targets:
            original = path.read_bytes()
            path.write_bytes(original + b"# tampered\n")
            try:
                with self.subTest(label=label, role=role):
                    self.assert_rejected(f"Label {label} binary {role} SHA-256 mismatch")
            finally:
                path.write_bytes(original)
        p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)

    def test_shared_driver_hash_mismatch_rejected(self):
        self.fx.driver.write_text(self.fx.driver.read_text() + "# tampered\n")
        self.assert_rejected("Shared binary measure_e2e SHA-256 mismatch")

    def test_unresolved_candidate_hash_rejected(self):
        self.manifest, self.schedule = self.fx.small_plan([CORE_CELL])
        self.manifest["provenance"]["comparison_identities"]["C"]["binaries"]["knotrel_benchmarks"]["sha256"] = "UNRESOLVED"
        self.assert_rejected("Label C binary knotrel_benchmarks SHA-256 is unresolved")

    def test_checkout_head_mismatch_rejected(self):
        checkout = self.root / "fx/src/C/knotrel"
        (checkout / "README").write_text("moved")
        _git(checkout, "commit", "-q", "-am", "move head")
        self.assert_rejected("Label C checkout knotrel_source commit mismatch")

    def test_dirty_checkout_rejected(self):
        (self.root / "fx/src/B/knotrel/untracked.rs").write_text("")
        self.assert_rejected("Label B checkout knotrel_source must be clean")

    def test_permitted_lockfile_change_requires_declaration_and_hash(self):
        checkout = self.root / "fx/src/C/knotrel"
        lock = checkout / "Cargo.lock"
        lock.write_text(_lock("0.3.0"))
        self.assert_rejected("Label C lockfile knotrel_lock hash mismatch")
        identity = self.manifest["provenance"]["comparison_identities"]["C"]
        identity["lockfiles"]["knotrel_lock"]["sha256"] = _sha(lock)
        self.assert_rejected("must be clean; unexpected change 'Cargo.lock'")
        identity["checkouts"]["knotrel_source"]["permitted_changes"] = ["Cargo.lock"]
        p0.validate_inputs(self.manifest, self.schedule, check_provenance=True)

    def test_binary_source_commit_must_match_checkout(self):
        self.manifest["provenance"]["comparison_identities"]["B"]["binaries"]["knotrel_server"]["source_commit"] = "f" * 40
        self.assert_rejected("Label B binary knotrel_server source_commit")

    def test_harness_commits_must_match_across_labels(self):
        fx = BCFixture(self.root / "fx-split", harness_commit_differs=True)
        manifest, schedule = fx.small_plan([CORE_CELL])
        with self.assertRaisesRegex(p0.ConfigurationValidationError, "same harness commit"):
            p0.validate_inputs(manifest, schedule, check_provenance=True)

    def test_derived_lock_rule(self):
        self.assertEqual(p0.derived_lock_disallowed_differences(_lock("0.2.0"), _lock("0.3.0")), [])
        self.assertTrue(p0.derived_lock_disallowed_differences(_lock("0.2.0"), _lock("0.2.0").replace("1.0.0", "1.0.1")))
        self.assertTrue(p0.derived_lock_disallowed_differences(_lock("0.2.0"), _lock("0.3.0", "\n[[package]]\nname = \"x\"\n")))
        self.fx.locks["C"].write_text(_lock("0.3.0").replace("1.0.0", "1.0.1"))
        identity = self.manifest["provenance"]["comparison_identities"]["C"]
        identity["lockfiles"]["benchmarks_lock_derived"]["sha256"] = _sha(self.fx.locks["C"])
        self.assert_rejected("differ beyond the knotrel-core version line")


class ExecutionTests(BCTestCase):
    def test_each_label_runs_its_own_binaries_and_every_report_is_validated(self):
        fx = self.fixture()
        manifest, schedule = fx.small_plan([CORE_CELL, BATCH_CELL, LIFECYCLE_CELL])
        rc, dest, exc = self.execute(fx, manifest, schedule)
        self.assertIsNone(exc)
        self.assertEqual(rc, 0)
        launches = fx.launches()
        self.assertEqual(len(launches), 2 * schedule["total_pairs"])
        seen = set()
        for pair in schedule["pairs"]:
            record = p0.read_json(dest / f"pair_{pair['pair_id']:03d}_{pair['cell_id']}.json")
            self.assertEqual([o["label"] for o in record["observations"]], pair["labels"])
            for obs in record["observations"]:
                label = obs["label"]
                self.assertEqual(obs["status"], "parsed_valid")
                self.assertEqual(obs["session"], pair["session"])
                if pair["cell_type"] == "core":
                    self.assertEqual(obs["argv"][0], str(fx.harnesses[label]))
                    self.assertEqual(obs["binary_identity"]["knotrel_benchmarks_sha256"], _sha(fx.harnesses[label]))
                    self.assertGreater(obs["peak_rss_bytes"], 0)
                else:
                    server = obs["argv"][obs["argv"].index("--server-bin") + 1]
                    self.assertEqual(server, str(fx.servers[label]))
                    self.assertEqual(obs["env"]["KNOTREL_BIN"], str(fx.servers[label]))
                    self.assertEqual(obs["binary_identity"]["knotrel_server_sha256"], _sha(fx.servers[label]))
                    report = p0.read_json(Path(obs["json_report_path"]))
                    self.assertEqual(report["server_provenance"]["binary_path"], str(fx.servers[label]))
                    self.assertEqual(len(report["runs"]), 2)
                seen.add((pair["cell_id"], label))
        self.assertEqual(len(seen), 6)
        harness_runs = {Path(entry["binary"]).resolve() for entry in launches if entry["role"] == "harness"}
        self.assertEqual(harness_runs, {fx.harnesses["B"].resolve(), fx.harnesses["C"].resolve()})
        self.assertEqual({e["label"] for e in launches if e["role"] == "driver"}, {"B", "C"})
        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "completed")
        self.assertEqual(meta["comparison_mode"], p0.BASELINE_CANDIDATE_MODE)
        self.assertEqual(meta["label_binary_sha256"]["C"]["knotrel_server"], _sha(fx.servers["C"]))
        analysis = p0.read_json(dest / "analysis.json")
        self.assertEqual(analysis["labels"], ["B", "C"])
        self.assertTrue(analysis["decision_status"].startswith("not_applied"))
        metrics = {c["cell_id"]: c["primary_metric"] for c in analysis["cells"]}
        self.assertEqual(metrics[BATCH_CELL], "window_duration_ns")
        for cell in analysis["cells"]:
            self.assertEqual(cell["pairs_completed"], 2)
            for delta in cell["paired_deltas"]:
                self.assertIn("val_B", delta)
                self.assertIn("val_C", delta)
                self.assertEqual(set(delta["supporting"]), {"B", "C"})

    def assert_halted(self, dest, exc, exc_type, status, failing_label):
        """The failed attempt is preserved, marked invalid, and nothing runs or is analysed after it."""
        self.assertIsInstance(exc, exc_type)
        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], status)
        self.assertEqual(meta["failure_record"]["error"], str(exc))
        self.assertFalse((dest / "analysis.json").exists())
        attempts = [o for f in sorted(dest.glob("pair_*.json")) for o in p0.read_json(f)["observations"]]
        failed = [o for o in attempts if o["status"] != "parsed_valid"]
        self.assertEqual(len(failed), 1)
        self.assertEqual(attempts[-1]["status"], failed[0]["status"])
        self.assertEqual(failed[0]["label"], failing_label)
        self.assertEqual(meta["completed_observations"], len(attempts))
        self.assertEqual(meta["completed_pairs"], (len(attempts) - 1) // 2)
        return meta, failed[0]

    def test_candidate_report_naming_wrong_server_hash_halts_class1(self):
        fx = self.fixture(fault="wrong_c_sha")
        manifest, schedule = fx.small_plan([BATCH_CELL])
        _, dest, exc = self.execute(fx, manifest, schedule)
        meta, failed = self.assert_halted(dest, exc, p0.QualificationBlockerError,
                                          "aborted_class1_qualification_blocker", "C")
        self.assertIn("SHA", failed["error"])
        self.assertTrue(Path(failed["json_report_path"]).is_file())

    def test_malformed_later_run_entry_halts_class1(self):
        fx = self.fixture(fault="bad_second_run_c")
        manifest, schedule = fx.small_plan([LIFECYCLE_CELL])
        _, dest, exc = self.execute(fx, manifest, schedule)
        _, failed = self.assert_halted(dest, exc, p0.QualificationBlockerError,
                                       "aborted_class1_qualification_blocker", "C")
        self.assertIn("run 1", failed["error"])

    def test_process_failure_preserves_evidence_and_halts_class3(self):
        fx = self.fixture(fault="exit_c")
        manifest, schedule = fx.small_plan([BATCH_CELL, LIFECYCLE_CELL])
        _, dest, exc = self.execute(fx, manifest, schedule)
        meta, failed = self.assert_halted(dest, exc, p0.ProcessExecutionError,
                                          "aborted_class3_process_execution_failure", "C")
        self.assertEqual(failed["exit_code"], 3)
        self.assertEqual(failed["status"], "exit_code_failure")
        self.assertIn("fake driver failure diagnostics", failed["raw_stderr"])
        self.assertTrue(Path(failed["json_report_path"]).is_file())
        self.assertIsNone(failed["parsed_metrics"])
        attempted = len(fx.launches())
        self.assertLess(attempted, 2 * schedule["total_pairs"])
        self.assertEqual(attempted, meta["completed_observations"])

    def test_rss_ceiling_violation_is_class3_in_bc_mode(self):
        fx = self.fixture()
        manifest, schedule = fx.small_plan([CORE_CELL])
        with patch.object(p0, "PROPOSED_PEAK_RSS_CEILING_BYTES", 1):
            _, dest, exc = self.execute(fx, manifest, schedule)
        _, failed = self.assert_halted(dest, exc, p0.ProcessExecutionError,
                                       "aborted_class3_process_execution_failure", schedule["pairs"][0]["labels"][0])
        self.assertEqual(failed["status"], "rss_ceiling_violation")
        self.assertIn("Peak RSS ceiling exceeded", failed["error"])

    def test_missing_core_peak_rss_is_class3_in_bc_mode(self):
        fx = self.fixture()
        manifest, schedule = fx.small_plan([CORE_CELL])
        with patch.object(p0, "peak_rss", return_value=None):
            _, dest, exc = self.execute(fx, manifest, schedule)
        _, failed = self.assert_halted(dest, exc, p0.ProcessExecutionError,
                                       "aborted_class3_process_execution_failure", schedule["pairs"][0]["labels"][0])
        self.assertIn("no retrospective peak RSS", failed["error"])

    def test_binary_drift_between_sessions_halts_class1(self):
        fx = self.fixture()
        manifest, schedule = fx.small_plan([CORE_CELL], seeds=(7, 8))
        calls = []

        def host_state():
            calls.append(1)
            if len(calls) == 2:  # post-session host check of session 0
                fx.servers["C"].write_text(fx.servers["C"].read_text() + "# rebuilt\n")
            return dict(FAKE_HOST)

        _, dest, exc = self.execute(fx, manifest, schedule, host_side_effect=host_state)
        self.assertIsInstance(exc, p0.QualificationBlockerError)
        self.assertIn("Identity drift detected at session 1 start", str(exc))
        meta = p0.read_json(dest / "run_metadata.json")
        self.assertEqual(meta["status"], "aborted_class1_qualification_blocker")
        self.assertEqual(meta["completed_pairs"], 2)

    def test_execution_rejects_tampered_candidate_before_any_launch(self):
        fx = self.fixture()
        manifest, schedule = fx.small_plan([CORE_CELL, BATCH_CELL])
        fx.harnesses["C"].write_text(fx.harnesses["C"].read_text() + "# tampered\n")
        _, dest, exc = self.execute(fx, manifest, schedule)
        self.assertIsInstance(exc, p0.ConfigurationValidationError)
        self.assertEqual(fx.launches(), [])


class CompatibilityTests(BCTestCase):
    def test_same_binary_bc_validates_and_is_flagged_in_dry_run(self):
        fx = self.fixture()
        identities = fx.identities["comparison_identities"]
        identities["C"] = copy.deepcopy(identities["B"])
        manifest, schedule = fx.small_plan([CORE_CELL, BATCH_CELL])
        p0.validate_inputs(manifest, schedule, check_provenance=True)
        p0.save_json(self.root / "m.json", manifest)
        p0.save_json(self.root / "s.json", schedule)
        out = io.StringIO()
        with patch("run_p0_aa.host_state", return_value=dict(FAKE_HOST)), redirect_stdout(out):
            rc = p0.run_dry_run(self.root / "m.json", self.root / "s.json", None, check_provenance=True)
        self.assertEqual(rc, 0)
        self.assertIn("byte-identical", out.getvalue())

    def test_aa_resolution_is_unchanged(self):
        cell = {"cell_id": "x", "argv": ["a"], "cwd": "/c", "env": {"K": "v"}}
        pair = {"argv": ["a"], "cwd": "/c", "env": {"K": "v"}}
        launch, effective = p0.resolve_launch(cell, pair, "A", False)
        self.assertEqual(launch, {"argv": ["a"], "cwd": "/c", "env": {"K": "v"}})
        self.assertIs(effective, cell)
        self.assertEqual(p0.comparison_labels({}), ("A", "Aprime"))
        self.assertEqual(p0.bundle_ceiling_bytes({}), p0.PROPOSED_DISK_CEILING_BYTES)

    def test_aa_analysis_keys_unchanged(self):
        cell_map = {"c": {"type": "core", "primary_metric": "workload_wall_ns"}}
        obs = [
            {"cell_id": "c", "pair_id": 0, "label": "A", "pair_position": 0, "parsed_metrics": {"workload_wall_ns": 100}},
            {"cell_id": "c", "pair_id": 0, "label": "Aprime", "pair_position": 1,
             "parsed_metrics": {"workload_wall_ns": 110}},
        ]
        analysis = p0.analyze_pilot(obs, cell_map)
        delta = analysis["cells"][0]["paired_deltas"][0]
        self.assertEqual(set(delta), {"pair_id", "val_A", "val_Aprime", "diff", "relative_diff", "log_ratio", "order"})
        self.assertNotIn("labels", analysis)

    def test_skip_host_checks_rejected_for_qualification_execute(self):
        fx = self.fixture()
        plan = prep.build_plan(_nine_cell_source(fx), "0" * 64, fx.identities, "main",
                               p0.QUALIFICATION_CELL_IDS, (1, 2, 3))
        p0.save_json(self.root / "m.json", plan["manifest"])
        argv = ["run_p0_aa.py", str(self.root / "dest"), "--manifest", str(self.root / "m.json"), "--schedule",
                str(self.root / "s.json"), "--execute", "--skip-host-checks"]
        err = io.StringIO()
        with patch.object(sys, "argv", argv), patch("sys.stderr", err), self.assertRaises(SystemExit):
            p0.main()
        self.assertIn("--skip-host-checks is not permitted", err.getvalue())
        self.assertFalse((self.root / "dest").exists())


if __name__ == "__main__":
    unittest.main()
