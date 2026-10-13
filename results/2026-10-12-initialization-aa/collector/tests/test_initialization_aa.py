"""Tests of the approved A/A protocol; no benchmark executable is run."""
import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_initialization_aa as aa


def observations():
    result = []
    for pair in aa.schedule(Path("/recorded/binary")):
        for position, label in enumerate(pair["labels"]):
            result.append(dict(session=pair["session"], engine=pair["engine"],
                               pair=pair["pair"], pair_position=position, label=label,
                               observation=pair["pair"] * 2 + position,
                               peak_process_rss_bytes=4096,
                               run=dict(setup_ns=100_000_000,
                                        total_initialization_ns=200_000_000)))
    return result


class ScheduleTests(unittest.TestCase):
    def test_exact_count_rotation_label_balance_and_arguments(self):
        binary = Path("/recorded/binary")
        plan = aa.schedule(binary)
        self.assertEqual(plan, aa.schedule(binary))
        self.assertEqual(len(plan), 72)
        self.assertEqual(aa.SEEDS, (120047, 120048, 120049))
        self.assertEqual(aa.QUIET_SECONDS, 60)
        self.assertEqual(aa.SESSION_GAP_SECONDS, 300)
        for session in range(3):
            group = [p for p in plan if p["session"] == session]
            self.assertEqual(group[0]["engine"], aa.ENGINES[session])
            for engine in aa.ENGINES:
                pairs = [p for p in group if p["engine"] == engine]
                self.assertEqual(len(pairs), 8)
                self.assertEqual(sum(p["labels"][0] == "A" for p in pairs), 4)
        for engine in aa.ENGINES:
            pairs = [p for p in plan if p["engine"] == engine]
            self.assertEqual(len(pairs), 24)
            for pair in pairs:
                self.assertEqual(pair["children"][0], pair["children"][1])
                args = pair["children"][0]
                self.assertEqual(args[args.index("--timing") + 1], "whole")
                self.assertNotIn("--validate", args)
                self.assertNotIn("A", args)
                self.assertNotIn("Aprime", args)

    def test_mutated_arguments_or_order_fail_before_execution(self):
        binary = Path("/recorded/binary")
        for mutation in ("argument", "order", "count", "label"):
            plan = aa.schedule(binary)
            if mutation == "argument":
                plan[0]["children"][1][-1] = "2"
            elif mutation == "order":
                plan[0], plan[1] = plan[1], plan[0]
            elif mutation == "count":
                plan.pop()
            else:
                plan[0]["labels"] = ["A", "A"]
            with self.assertRaises(ValueError):
                aa.validate_schedule(plan, binary)


class AnalysisTests(unittest.TestCase):
    def test_identical_observations_pass_all_fixed_gates(self):
        result = aa.analyze(observations())
        self.assertTrue(result["passed"])
        self.assertFalse(result["stage_b_authorized"])
        self.assertAlmostEqual(result["median_interval_coverage"], 0.9773441553115845)
        for row in result["rows"]:
            for metric in row["metrics"].values():
                self.assertEqual(metric["median_interval_percent"], [0, 0])
                self.assertEqual(metric["tail_count"], 0)
                self.assertTrue(all(metric["checks"].values()))

    def test_precision_and_variability_are_not_loosened(self):
        self.assertEqual(aa.PRECISION, math.log(1.02))
        self.assertEqual(aa.VARIABILITY, math.log(1.03))
        self.assertEqual(aa.TAIL, math.log(1.10))
        for factor, precision, variability in [(1.021, False, True), (1.031, False, False)]:
            rows = observations()
            for row in rows:
                if row["label"] == "Aprime":
                    row["run"]["setup_ns"] *= factor
            metric = aa.analyze(rows)["rows"][0]["metrics"]["setup_ns"]
            self.assertEqual(metric["checks"]["precision"], precision)
            self.assertEqual(metric["checks"]["variability"], variability)
            self.assertFalse(metric["passed"])

    def test_exact_order_statistics_and_tail_count_retain_outliers(self):
        rows = [r for r in observations() if r["engine"] == aa.ENGINES[0]]
        pair_ids = sorted({r["pair"] for r in rows})
        expected = []
        for i, pair_id in enumerate(pair_ids):
            change = (i - 12) / 1000 if i < 21 else .2
            expected.append(change)
            for row in rows:
                if row["pair"] == pair_id and row["label"] == "Aprime":
                    row["run"]["setup_ns"] *= math.exp(change)
        metric = aa.gate_metric(rows, "setup_ns")
        for actual, wanted in zip(metric["median_interval_ranks_7_18_log"],
                                  [sorted(expected)[6], sorted(expected)[17]]):
            self.assertAlmostEqual(actual, wanted)
        self.assertEqual(metric["tail_count"], 3)
        self.assertFalse(metric["checks"]["tails"])
        self.assertEqual(metric["observation_distribution"]["n"], 48)

    def test_labeled_and_chronological_session_gates_are_separate(self):
        rows = observations()
        for row in rows:
            if row["session"] == 1 and row["pair_position"] == 1:
                row["run"]["setup_ns"] *= 1.04
        metric = aa.analyze(rows)["rows"][0]["metrics"]["setup_ns"]
        session = metric["sessions"][1]
        self.assertFalse(session["checks"]["chronological_median"])
        self.assertTrue(session["checks"]["labeled_median"])
        self.assertFalse(metric["passed"])

    def test_startup_gate_uses_first_observation_not_first_label(self):
        rows = observations()
        first = next(r for r in rows if r["engine"] == aa.ENGINES[0] and r["session"] == 2)
        first["run"]["total_initialization_ns"] *= 1.11
        metric = aa.analyze(rows)["rows"][0]["metrics"]["total_initialization_ns"]
        self.assertAlmostEqual(metric["sessions"][2]["startup_ratio"], 1.11)
        self.assertFalse(metric["sessions"][2]["checks"]["startup"])
        self.assertFalse(metric["passed"])
        first["run"]["total_initialization_ns"] = 200_000_000 / 1.11
        self.assertFalse(aa.analyze(rows)["rows"][0]["metrics"]["total_initialization_ns"]
                         ["sessions"][2]["checks"]["startup"])

    def test_partial_stage_cannot_produce_a_passing_analysis(self):
        with self.assertRaises(ValueError):
            aa.analyze(observations()[:-1])


class CollectionTests(unittest.TestCase):
    def test_failed_host_preflight_launches_no_children_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            reference = root / "reference"
            reference.mkdir()
            (reference / "manifest.json").write_text(json.dumps(
                {"cases": [{"command": ["/usr/bin/time", "-l", "/recorded/binary"]}]}))
            destination = root / "result"
            state = dict(power="Battery Power", known_workloads=[])
            with patch.object(aa, "REFERENCE", reference), \
                    patch.object(sys, "argv", ["run_initialization_aa.py", str(destination)]), \
                    patch.object(aa, "host_state", return_value=state), \
                    patch.object(aa, "preflight") as preflight, \
                    patch.object(aa, "observe") as observe:
                with self.assertRaisesRegex(ValueError, "AC power"):
                    aa.main()
                preflight.assert_not_called()
                observe.assert_not_called()
            manifest = json.loads((destination / "manifest.json").read_text())
            self.assertEqual(manifest["status"], "stopped")
            self.assertEqual(manifest["observations"], [])
            self.assertEqual(manifest["host_preflight"], state)

    def test_power_sleep_priority_and_workload_changes_stop(self):
        baseline = dict(power="Now drawing from 'AC Power'", known_workloads=[],
                        power_configuration="normal", sleep_wake="unchanged", collector_nice=0)
        aa.validate_host(baseline, baseline)
        for key, value in [("power", "Battery Power"), ("known_workloads", [{"name": "rustc"}]),
                           ("power_configuration", "low"), ("sleep_wake", "woke"),
                           ("collector_nice", 1)]:
            current = baseline | {key: value}
            with self.assertRaises(ValueError):
                aa.validate_host(current, baseline)

    def test_pair_is_buffered_and_first_child_failure_stops(self):
        pair = aa.schedule(Path("/recorded/binary"))[0]
        payload = dict(schema_version=1, measurement="initialization-only",
                       debug_assertions=False, warmup=0, validated_dynamic_continuation=False,
                       surface="adapter", timing="whole", workload="dense-bridge-churn-v1",
                       engine="knotrel-core/compact-bfs-v1",
                       config=dict(nodes=512, rounds=1, seed=42),
                       repetitions=[dict(initial_edges=65281, trace_fingerprint_fnv1a64="same",
                                         setup_ns=100, total_initialization_ns=200)])
        raw = dict(stdout=json.dumps(payload), stderr="4096 maximum resident set size\n",
                   exit_code=0, timed_out=False)
        for fail in (False, True):
            calls = []
            with tempfile.TemporaryDirectory() as directory:
                destination = Path(directory)
                def observe(args, env):
                    self.assertEqual(list(destination.iterdir()), [])
                    calls.append((copy.deepcopy(args), copy.deepcopy(env)))
                    return raw | (dict(exit_code=1) if fail else {})
                with patch.object(aa, "validate_provenance"), patch.object(aa, "host_state", return_value={}), \
                        patch.object(aa, "validate_host"), patch.object(aa, "binary_stat", return_value=[]), \
                        patch.object(aa, "observe", side_effect=observe):
                    kwargs = (pair, Path("/recorded/binary"),
                              dict(binary_stat=[], host={}, expected_trace="same"),
                              {"FIXED": "yes"}, destination)
                    if fail:
                        with self.assertRaises(RuntimeError):
                            aa.collect_pair(*kwargs)
                        self.assertEqual(len(calls), 1)
                    else:
                        result = aa.collect_pair(*kwargs)
                        self.assertEqual(len(result), 2)
                        self.assertEqual(calls[0], calls[1])
                    self.assertTrue((destination / "pair-00.json").exists())


if __name__ == "__main__":
    unittest.main()
