"""Unit tests for scripts/run_metrics_overhead.py (pure functions only)."""

import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_metrics_overhead as mo  # noqa: E402


class ScheduleTest(unittest.TestCase):
    def test_every_round_runs_each_arm_once_and_orders_are_balanced(self):
        entries = mo.schedule(24)
        by_round = collections.defaultdict(list)
        for entry in entries:
            by_round[entry["round"]].append(entry["arm"])
        self.assertEqual(len(by_round), 24)
        for arms in by_round.values():
            self.assertEqual(sorted(arms), sorted(mo.ARMS))
        orders = collections.Counter(tuple(arms) for arms in by_round.values())
        self.assertEqual(len(orders), 6)
        self.assertEqual(set(orders.values()), {4})

    def test_extension_continues_round_numbers_and_rotation(self):
        extension = mo.schedule(12, first_round=24)
        self.assertEqual(extension[0]["round"], 24)
        self.assertEqual(extension[-1]["round"], 35)
        first = [e["arm"] for e in extension if e["round"] == 24]
        self.assertEqual(first, [e["arm"] for e in mo.schedule(1) if e["round"] == 0])


class VerdictTest(unittest.TestCase):
    def test_budget_boundaries(self):
        self.assertEqual(mo.budget_verdict(3.0, (1.0, 6.0), 1.0), "PASS")
        self.assertEqual(mo.budget_verdict(-1.0, (-3.0, 0.5), 1.0), "PASS")
        self.assertEqual(mo.budget_verdict(3.1, (1.0, 5.0), 1.0), "INCONCLUSIVE")
        self.assertEqual(mo.budget_verdict(2.0, (0.0, 6.5), 1.0), "INCONCLUSIVE")
        self.assertEqual(mo.budget_verdict(5.0, (3.5, 7.0), 1.0), "REGRESSION")
        # A slowdown inside the A/A noise is never a confirmed regression.
        self.assertEqual(mo.budget_verdict(5.0, (3.5, 7.0), 6.0), "INCONCLUSIVE")

    def test_evaluate_pairs_by_round(self):
        rounds = {r: {"off": 100.0, "on": 101.0 + (r % 2) * 0.2, "aa": 100.0 + (r % 3 - 1) * 0.1}
                  for r in range(12)}
        result = mo.evaluate(rounds)
        self.assertEqual(result["n"], 12)
        self.assertAlmostEqual(result["on"]["median_pct"], 1.1, places=6)
        self.assertEqual(result["on"]["verdict"], "PASS")
        self.assertLessEqual(result["aa"]["noise_bound_pct"], 0.11)

    def test_bootstrap_is_deterministic(self):
        values = [0.5, 1.0, 2.0, -1.0, 3.0, 0.0]
        self.assertEqual(mo.bootstrap_median_ci(values), mo.bootstrap_median_ci(values))


class ParseTest(unittest.TestCase):
    def test_parse_probe_lines(self):
        stdout = (
            '{"elapsed_ns":"2000","metrics":true,"mode":"timing","requests":2,"scenario":"a","schema":1}\n'
            "noise\n"
            '{"elapsed_ns":"300","metrics":true,"mode":"timing","requests":1,"scenario":"b","schema":1}\n'
        )
        self.assertEqual(mo.parse_probe(stdout), {"a": 1000.0, "b": 300.0})


if __name__ == "__main__":
    unittest.main()
