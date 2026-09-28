"""Independent-oracle and cache correctness tests without GraphScope installed."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'adapters/graphscope'))
import probe


class ProbeTests(unittest.TestCase):
    def test_topology_cases_have_independently_valid_answers(self):
        for case in probe.contract_cases():
            probe.validate_case(case)

    def test_wrong_expected_answer_is_rejected_before_backend(self):
        case = copy.deepcopy(probe.contract_cases()[0])
        query = next(op for op in case['operations'] if op['op'] == 'connected')
        query['expected'] = not query['expected']
        with self.assertRaises(ValueError):
            probe.validate_case(case)

    def test_same_query_is_checked_again_after_state_changes(self):
        case = probe.contract_cases()[0]
        answers = [op['expected'] for op in case['operations'] if op['op'] == 'connected']
        self.assertIn(False, answers)
        self.assertIn(True, answers)
        self.assertGreaterEqual(len(answers), 6)

    def test_oracle_rejects_invalid_or_ineffective_updates(self):
        for op in [{'op': 'link', 'source': 0, 'target': 0},
                   {'op': 'cut', 'source': 0, 'target': 2, 'changed': True},
                   {'op': 'connected', 'source': 0, 'target': 99, 'expected': False}]:
            case = {'name': 'bad', 'nodes': [0, 1, 2], 'initial_edges': [[0, 1]], 'operations': [op]}
            with self.assertRaises(ValueError):
                probe.validate_case(case)

    def test_export_preserves_u64_and_rejects_unsupported_schema(self):
        envelope = {'schema_version': 1, 'workload': 'test', 'config': {'nodes': 2},
                    'trace': {'initial_edges': [[0, 1]], 'operations': []}}
        self.assertEqual(probe.from_export(envelope)['nodes'], [0, 1])
        envelope['schema_version'] = 2
        with self.assertRaises(ValueError):
            probe.from_export(envelope)
        self.assertEqual(probe.node_key(2**64-1), '18446744073709551615')
        for value in [-1, 2**64, True, 1.2]:
            with self.assertRaises(ValueError):
                probe.node_key(value)


if __name__ == '__main__':
    unittest.main()
