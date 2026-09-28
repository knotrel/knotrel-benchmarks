"""Behavior checks for cache-regime scheduling and trace validation."""
import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'adapters/graphscope'))
import run_baseline


class CacheProtocolTests(unittest.TestCase):
    def test_balanced_independent_process_cases(self):
        cases = run_baseline.run_cases([8], ['chain-split-rejoin-v1'], 3, 'both', 7)
        self.assertEqual(len(cases), 6)
        self.assertEqual({(c['trial'], c['warmup']) for c in cases},
                         {(i, w) for i in range(3) for w in (0, 1)})
        self.assertEqual(cases, run_baseline.run_cases([8], ['chain-split-rejoin-v1'], 3, 'both', 7))
        self.assertEqual(len({c['name'] for c in cases}), 6)

    def test_rotation_balances_each_engine_position(self):
        orders = [run_baseline.engine_order('all', i) for i in range(len(run_baseline.ENGINES))]
        for position in range(len(run_baseline.ENGINES)):
            self.assertEqual({order[position] for order in orders}, set(run_baseline.ENGINES))
        for invalid in ['typo', 'reference-bfs,reference-bfs']:
            with self.assertRaises(ValueError):
                run_baseline.engine_order(invalid, 0)

    def test_invalid_sampling_rejected(self):
        for trials in [0, -1]:
            with self.assertRaises(ValueError):
                run_baseline.run_cases([8], ['chain-split-rejoin-v1'], trials, 'both', 7)


if __name__ == '__main__':
    unittest.main()
