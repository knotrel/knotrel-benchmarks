"""Deterministic protocol and statistical-accounting regression tests."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_initialization import cases, distribution, paired_interval, validate_report


class InitializationTests(unittest.TestCase):
    def test_fixed_matrix_and_balanced_adjacent_pairs(self):
        self.assertEqual(len(cases("baseline")), 72)
        for stage in ["calibration", "limits"]:
            plan = cases(stage)
            self.assertEqual(len(plan), 36)
            self.assertEqual(plan, cases(stage))
            for a, b in zip(plan[::2], plan[1::2]):
                for key in ["trial", "engine", "nodes", "workload"]:
                    self.assertEqual(a[key], b[key])
            for engine in ["compact-bfs", "ett-scan", "hdt"]:
                first = [c for c in plan[::2] if c["engine"] == engine]
                field = "timing" if stage == "calibration" else "surface"
                self.assertEqual(len({c[field] for c in first}), 2)
                self.assertEqual(sum(c[field] == first[0][field] for c in first), 3)

    def test_statistics_include_adverse_observations(self):
        summary = distribution([1, 2, 3, 4, 5, 100])
        self.assertEqual(summary["median"], 3.5)
        self.assertEqual(summary["max"], 100)
        self.assertEqual(paired_interval([4] * 6), [4, 4])
        self.assertEqual(paired_interval([-4] * 6), [-4, -4])

    def test_accounting_mismatch_is_rejected(self):
        case = cases("baseline")[0]
        names = {"compact-bfs": "knotrel-core/compact-bfs-v1",
                 "ett-scan": "knotrel-core/ett-pruned-v2",
                 "hdt": "knotrel-core/hdt-sparse-levels-v3"}
        report = dict(schema_version=1, measurement="initialization-only",
                      debug_assertions=False, warmup=0, validated_dynamic_continuation=False,
                      surface="adapter", timing="phases", engine=names[case["engine"]],
                      workload=case["workload"],
                      config=dict(nodes=case["nodes"], rounds=1, seed=42),
                      repetitions=[dict(setup_ns=100, total_initialization_ns=120,
                                        phases=dict(node_vector_ns=5, adapter_validation_ns=5,
                                                    vertex_registration_ns=20, constructor_other_ns=5,
                                                    initial_edges_ns=60, setup_other_ns=5,
                                                    input_generation_ns=10,
                                                    trace_encoding_fingerprint_ns=10))])
        validate_report(report, case)
        report["repetitions"][0]["setup_ns"] = 99
        with self.assertRaisesRegex(ValueError, "accounting"):
            validate_report(report, case)


if __name__ == "__main__":
    unittest.main()
