"""Unit tests for the v0.5.0 lifecycle qualification collector and analysis."""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze_lifecycle_qualification as an  # noqa: E402
import run_lifecycle_qualification as run  # noqa: E402


def write_run(root: Path, cells, raws) -> None:
    (root / "plan").mkdir(parents=True)
    (root / "raw").mkdir()
    (root / "plan" / "matrix.json").write_text(json.dumps(cells))
    for cell_id, records in raws.items():
        (root / "raw" / f"{cell_id}.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")


def pairs(ratios, reference_ns=5_000_000):
    return [{"kind": "verify", "match": True}] + [
        {"kind": "pair", "pair": i, "candidate_first": i % 2 == 0,
         "reference_ns": reference_ns, "candidate_ns": int(reference_ns * r)}
        for i, r in enumerate(ratios)]


class MatrixTests(unittest.TestCase):
    def test_matrix_is_deterministic_and_unique(self):
        first, second = run.matrix("final"), run.matrix("final")
        self.assertEqual(first, second)
        ids = [c["id"] for c in first]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 188)

    def test_pilot_differs_only_in_repetitions(self):
        strip = lambda cells: [  # noqa: E731
            [a for a in c["args"] if a not in ("2", "12", "0", "3", "30")] for c in cells]
        self.assertEqual([c["id"] for c in run.matrix("pilot")], [c["id"] for c in run.matrix("final")])
        self.assertEqual(len(strip(run.matrix("pilot"))), len(strip(run.matrix("final"))))

    def test_multipliers_scale_windows_and_requests_but_not_imports(self):
        cells = run.matrix("final")
        by_id = {c["id"]: c for c in cells}
        run.apply_multipliers(cells, {"B1-ops-ett-ring-1000-query": 8,
                                      "B4-http-optin-query-ett-10000": 2,
                                      "B4-http-import-compact-bfs-10000": 2})
        args = by_id["B1-ops-ett-ring-1000-query"]["args"]
        self.assertEqual(args[args.index("--window") + 1], "32000")
        args = by_id["B4-http-optin-query-ett-10000"]["args"]
        self.assertEqual(args[args.index("--requests") + 1], "8")
        args = by_id["B4-http-import-compact-bfs-10000"]["args"]
        self.assertEqual(args[args.index("--requests") + 1], "1")


class AnalysisTests(unittest.TestCase):
    def analyze(self, cells, raws):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_run(root, cells, raws)
            out = root / "report.json"
            sys.argv = ["x", str(root), "--json", str(out), "--markdown", str(root / "r.md")]
            self.assertEqual(an.main(), 0)
            return json.loads(out.read_text())

    def cell(self, cid, tolerance=0.25):
        return {"id": cid, "experiment": "B1", "tolerance": tolerance, "binary": "core", "args": []}

    def test_classification_uses_order_statistic_interval(self):
        cells = [self.cell("pass"), self.cell("regression"), self.cell("inconclusive"), self.cell("timer")]
        raws = {
            "pass": pairs([1.0, 1.01, 0.99, 1.02, 0.98, 1.0, 1.03, 0.97, 1.0, 1.01, 0.99, 1.0]),
            "regression": pairs([1.4] * 12),
            "inconclusive": pairs([1.0, 1.1, 1.2, 1.3, 1.4, 1.1, 1.2, 1.3, 1.0, 1.2, 1.25, 1.35]),
            "timer": pairs([1.0] * 12, reference_ns=500_000),
        }
        report = {t["id"]: t for t in self.analyze(cells, raws)["timing"]}
        self.assertEqual(report["pass"]["status"], "PASS")
        self.assertEqual(report["regression"]["status"], "REGRESSION")
        self.assertEqual(report["inconclusive"]["status"], "INCONCLUSIVE")
        self.assertEqual(report["timer"]["status"], "TIMER_LIMITED")
        ratios = sorted(math.log(r) for r in [1.0, 1.1, 1.2, 1.3, 1.4, 1.1, 1.2, 1.3, 1.0, 1.2, 1.25, 1.35])
        self.assertAlmostEqual(report["inconclusive"]["interval_log"][0], ratios[2], places=6)
        self.assertAlmostEqual(report["inconclusive"]["interval_log"][1], ratios[9], places=6)

    def test_digest_mismatch_stops_analysis(self):
        raws = {"bad": [{"kind": "verify", "match": False}]}
        with self.assertRaises(SystemExit):
            self.analyze([self.cell("bad")], raws)

    def test_sustained_rules(self):
        def checkpoints(heap, engine=lambda c: 100_000, nodes=100_000):
            return [{"kind": "checkpoint", "cycle": c,
                     "counts": {"nodes": nodes, "edges": 5, "active_nodes": nodes, "enabled_edges": 5,
                                "effective_edges": 5, "engine_vertices": engine(c)},
                     "live_heap_bytes": heap(c), "rss_bytes": heap(c)} for c in range(31)]
        cells = [{"id": f"C-heap-lifecycle-ett-sparse-{m}-100000", "experiment": "C", "binary": "core-count",
                  "args": []} for m in ("flat", "grow", "slots")]
        raws = {
            cells[0]["id"]: checkpoints(lambda c: 1000),
            cells[1]["id"]: checkpoints(lambda c: 1000 + 100 * c),
            cells[2]["id"]: checkpoints(lambda c: 1000, engine=lambda c: 300_000),
        }
        report = {r["id"]: r for r in self.analyze(cells, raws)["sustained"]}
        self.assertEqual(report[cells[0]["id"]]["C3"], "PASS")
        self.assertEqual(report[cells[1]["id"]]["C3"], "FAIL")
        self.assertEqual(report[cells[2]["id"]]["C1"], "FAIL")


if __name__ == "__main__":
    unittest.main()
