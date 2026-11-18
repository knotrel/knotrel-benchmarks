"""Tests for the interference marking (PROTOCOL.md 10.3), report_v070r_interference.py."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import report_v070r_interference as ri  # noqa: E402


def child(label, start, end, background=0.0, baseline=0.0):
    return {"kind": "child", "label": label, "start": start, "end": end,
            "cpu_seconds_by_class": {"system": 0.1, "baseline": baseline, "background": background},
            "conforming": True, "reasons": []}


class Camp:
    def __init__(self, children, tops=(), a_obs=(), bc=()):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)
        (self.path / "gate").mkdir()
        (self.path / "gate/gate-log.jsonl").write_text(
            "\n".join(json.dumps(c) for c in [{"kind": "child", "label": "quiet-period", "start": 0, "end": 1}, *children]) + "\n")
        (self.path / "gate/activity-monitor.jsonl").write_text("\n".join(
            [json.dumps({"k": "hb", "t": 0, "seq": 1, "v": 0})] +
            [json.dumps({"k": "top", "t": t, "background_pcpu_sum": v, "processes": []}) for t, v in tops]) + "\n")
        (self.path / "A/raw-main").mkdir(parents=True)
        for i, (t, cell) in enumerate(a_obs):
            (self.path / f"A/raw-main/pair_{i:03d}_{cell}.json").write_text(json.dumps(
                {"cell_id": cell, "observations": [{"cell_id": cell, "launch_unix_ns": int(t * 1e9)}]}))
        (self.path / "BC").mkdir()
        (self.path / "BC/run-log.jsonl").write_text("".join(
            json.dumps({"position": n, "id": i, "argv": a, "seconds": sec}) + "\n" for n, (i, a, sec) in enumerate(bc)))


class Measures(unittest.TestCase):
    def test_shares_and_limit_strictly_above(self):
        m = ri.child_measures(child("r:x-00-ref", 10, 12, background=0.5, baseline=0.4), [], [])
        self.assertAlmostEqual(m["background_share"], 0.25)
        self.assertAlmostEqual(m["baseline_share"], 0.2)
        self.assertEqual(m["over"], [])  # exactly 25 % is not above
        m = ri.child_measures(child("r:x-00-ref", 10, 12, background=0.52), [], [])
        self.assertEqual(m["over"], ["background_share"])
        self.assertFalse(m["below_resolution"])

    def test_pcpu_mean_within_child_only(self):
        times, values = [9.0, 10.5, 11.5, 12.5], [90.0, 20.0, 40.0, 90.0]
        m = ri.child_measures(child("r:x-00-ref", 10, 12), times, values)
        self.assertAlmostEqual(m["background_pcpu_mean"], 0.30)
        self.assertEqual(m["top_samples"], 2)
        self.assertEqual(m["over"], ["background_pcpu_mean"])
        short = ri.child_measures(child("r:x-00-ref", 10.6, 10.7), times, values)
        self.assertIsNone(short["background_pcpu_mean"])

    def test_one_tick_in_a_short_child_is_marked_and_flagged_as_resolution(self):
        m = ri.child_measures(child("A:x", 10.0, 10.035, baseline=0.01), [], [])
        self.assertEqual(m["over"], ["baseline_share"])
        self.assertTrue(m["below_resolution"])

    def test_epoch_scale_tick_at_exactly_25_percent_is_not_above(self):
        start = 1795033218.936
        m = ri.child_measures(child("A:x", start, start + 0.040, baseline=0.01), [], [])
        self.assertEqual(m["over"], [])
        m = ri.child_measures(child("A:x", start, start + 0.039, baseline=0.01), [], [])
        self.assertEqual(m["over"], ["baseline_share"])

    def test_pcpu_only_over_is_not_resolution(self):
        m = ri.child_measures(child("r:x", 10, 12), [10.5, 11.5], [40.0, 40.0])
        self.assertEqual(m["over"], ["background_pcpu_mean"])
        self.assertFalse(m["below_resolution"])

    def test_missing_cpu_refused(self):
        bad = child("r:x", 10, 12)
        bad["cpu_seconds_by_class"] = None
        with self.assertRaises(ValueError):
            ri.child_measures(bad, [], [])

    def test_zero_duration_refused(self):
        with self.assertRaises(ValueError):
            ri.child_measures(child("r:x", 5, 5), [], [])


class Cells(unittest.TestCase):
    def test_cell_keys_and_conservative_marking(self):
        camp = Camp([
            child("A:/t/measure_e2e --scenario a", 100.0, 101.0, baseline=0.5),
            child("A:/t/measure_e2e --scenario a", 102.0, 103.0),
            child("BC:/t/core-lifecycle resources --arm lifecycle", 110.0, 111.0),
            child("r:R-churn-fresh-sparse-100k-warmup-00-ref", 120.0, 121.0),
            child("r:R-churn-fresh-sparse-100k-analyzed-13-cand", 122.0, 123.0, background=0.3),
            child("rmem:Rmem-import-core-20-10-ref", 130.0, 131.0),
            child("rmem:Rmem-import-core-20-10-cand", 132.0, 133.0),
            child("mdesc:M-standalone-off-10k", 140.0, 141.0),
            child("mreg:Mreg-standalone-off-read95-b1-c4-10k-none-warmup-01-cand", 150.0, 151.0),
            child("mreg:Mreg-standalone-off-read95-b1-c4-10k-none-analyzed-00-ref", 152.0, 153.0),
        ], a_obs=[(99.9995, "cellA"), (102.0005, "cellA")],
            bc=[("C-heap-x", ["/t/core-lifecycle", "resources", "--arm", "lifecycle", "--seed", "1"], 1.2)])
        rep = ri.report(camp.path)
        rows = {(r["experiment"], r["cell"]): r for r in rep["rows"]}
        self.assertEqual(set(rows), {("A", "cellA"), ("BC", "C-heap-x"), ("r", "R-churn-fresh-sparse-100k"),
                                     ("rmem", "Rmem-import-core-20-10"), ("mdesc", "M-standalone-off-10k"),
                                     ("mreg", "Mreg-standalone-off-read95-b1-c4-10k-none")})
        self.assertTrue(rows[("A", "cellA")]["read_with_caution"])
        self.assertEqual((rows[("A", "cellA")]["children"], rows[("A", "cellA")]["children_over"]), (2, 1))
        self.assertTrue(rows[("r", "R-churn-fresh-sparse-100k")]["read_with_caution"])
        self.assertFalse(rows[("mdesc", "M-standalone-off-10k")]["read_with_caution"])
        self.assertEqual(rep["cells_read_with_caution"], 2)
        self.assertEqual(rows[("r", "R-churn-fresh-sparse-100k")]["children"], 2)  # warmup + analyzed: one cell
        self.assertEqual(rows[("mreg", "Mreg-standalone-off-read95-b1-c4-10k-none")]["children"], 2)
        self.assertEqual(rep["children"], 10)  # quiet-period excluded
        self.assertIn("2 of 6 cells", ri.markdown(rep))

    def test_unmapped_a_child_and_bc_mismatch_refused(self):
        camp = Camp([child("A:/t/x", 100.0, 101.0)], a_obs=[(50.0, "cellA")])
        with self.assertRaises(ValueError):
            ri.report(camp.path)
        camp = Camp([child("BC:/t/http-lifecycle --scenario x", 1.0, 2.0)], bc=[("B4", ["/t/core-lifecycle", "ops"], 9)])
        with self.assertRaises(ValueError):
            ri.report(camp.path)
        camp = Camp([child("BC:", 1.0, 2.0)], bc=[("B4", ["/t/core-lifecycle", "ops"], 9)])  # empty label
        with self.assertRaises(ValueError):
            ri.report(camp.path)
        camp = Camp([child("BC:/t/core-lifecycle ops", 1.0, 20.0)], bc=[("B4", ["/t/core-lifecycle", "ops"], 9)])  # too long
        with self.assertRaises(ValueError):
            ri.report(camp.path)
        camp = Camp([child("r:R-churn-fresh-sparse-100k-13-cand", 1.0, 2.0)])  # not the analyzer's cell form
        with self.assertRaises(ValueError):
            ri.report(camp.path)
        camp = Camp([], bc=[("B4", ["/t/core-lifecycle", "ops"], 9)])
        with self.assertRaises(ValueError):
            ri.report(camp.path)


if __name__ == "__main__":
    unittest.main()
