"""The peak RSS parser normalizes units without treating absent data as zero."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from run_scale import peak_rss, run_measurement

class RssTests(unittest.TestCase):
    def test_units_and_missing_values(self):
        self.assertEqual(peak_rss('  123456  maximum resident set size\n', 'darwin'), 123456)
        self.assertEqual(peak_rss('Maximum resident set size (kbytes): 123\n', 'linux'), 125952)
        self.assertIsNone(peak_rss('permission denied', 'darwin'))
        self.assertIsNone(peak_rss('', 'linux'))

    def test_timeout_is_recorded_and_success_returns_output(self):
        result, timed_out = run_measurement([sys.executable, '-c', 'import time; time.sleep(5)'], 0.05)
        self.assertTrue(timed_out)
        self.assertEqual(result.returncode, 124)
        result, timed_out = run_measurement([sys.executable, '-c', 'print(42)'], 5)
        self.assertFalse(timed_out)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), '42')
