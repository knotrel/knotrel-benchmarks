"""Tests of the CF5 matrix, runner and analyzer (scripts/cf5_matrix.py, run_cf5.py,
analyze_cf5.py)."""

from __future__ import annotations

import json
import math
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import analyze_cf5 as an  # noqa: E402
import cf5_matrix  # noqa: E402
import run_cf5  # noqa: E402

FAKE = """
import json, sys
args = sys.argv[1:]
engine = args[args.index("--engine") + 1]
if engine == "boom":
    sys.exit(3)
value = {"cf": 70.0e6, "ref": 100.0e6, "same": 100.0e6}[engine]
print(json.dumps({"kind": "build"}))
print(json.dumps({"kind": "pair", "t_ns": value, "ok": engine != "bad", "trace": "x"}))
"""


def tiny_matrix(cf_engine="cf", ref_engine="ref", rule="two_sided", tier=2, check=None):
    def arm(engine):
        return {"tool": "fake", "args": ["--engine", engine], "line": "kind=pair"}
    cell = {"id": "C1", "block": "K1", "tier": tier, "kind": "paired", "family": "F",
            "role": "primary", "reference": "ref", "rule": rule, "arms": {"cf": arm(cf_engine), "ref": arm(ref_engine)},
            "metrics": [{"name": "t_ns", "path": "t_ns", "margin": 0.10, "margin_kind": "time",
                         "direction": "lower_is_better"}]}
    if check:
        cell["check"] = check
    det = {"id": "D1", "block": "K4", "tier": 3, "kind": "deterministic", "family": "F",
           "role": "veto", "reference": "ref", "rule": "deterministic",
           "arms": {"cf": arm("cf"), "ref": arm("ref")},
           "metrics": [{"name": "t_ns", "path": "t_ns", "margin": 0.20, "margin_kind": "memory",
                        "direction": "lower_is_better"}]}
    return {"schema": "cf5-matrix-1",
            "rules": {"cap_hours": 12, "second_session_cap_hours": 8,
                      "block_order": [["V1"], ["K1"], ["K4"]]},
            "cells": [cell, det]}


class Fixture(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        fake = self.dir / "fake.py"
        fake.write_text(FAKE)
        self.tools = self.dir / "tools.json"
        self.tools.write_text(json.dumps({"fake": [sys.executable, str(fake)]}))

    def run_matrix(self, matrix, out, *extra):
        path = self.dir / f"m-{out}.json"
        path.write_text(json.dumps(matrix))
        code = run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                             str(self.dir / out), *extra])
        return code, path


class MatrixTest(unittest.TestCase):
    def test_totals_ids_and_cells(self):
        matrix = cf5_matrix.build()
        self.assertEqual(matrix["total_comparisons"], 226)
        self.assertEqual(matrix["counts"], {"K1": 48, "K2": 18, "K2x": 9, "K3": 36, "K4": 18,
                                            "L1": 11, "L2": 15, "L3": 11, "L4": 10, "S1": 14,
                                            "S3": 7, "V1": 9, "V2": 10, "V3": 10})
        for cell in matrix["cells"]:
            self.assertIn(cell["tier"], (1, 2, 3))
            if cell["kind"] in ("paired", "deterministic"):
                self.assertEqual(set(cell["arms"]), {"cf", "ref"})
                self.assertTrue(cell["metrics"])
                for metric in cell["metrics"]:
                    self.assertEqual(metric["margin"], cf5_matrix.MARGINS[metric["margin_kind"]])

    def test_engine_is_the_only_difference_between_engine_arms(self):
        for cell in cf5_matrix.build()["cells"]:
            if cell["kind"] == "delegated" or cell["block"] in ("V2", "V3"):
                continue
            cf, ref = (cell["arms"][a]["args"] for a in ("cf", "ref"))
            diff = [(a, b) for a, b in zip(cf, ref) if a != b]
            self.assertEqual(len(cf), len(ref), cell["id"])
            self.assertEqual(len(diff), 1, cell["id"])
            self.assertIn("cluster-forest", diff[0][0], cell["id"])

    def test_no_exploratory_parameters_outside_k2x(self):
        for cell in cf5_matrix.build()["cells"]:
            args = cell.get("arms", {}).get("cf", {}).get("args", [])
            if cell["block"] != "K2x" and "--degree" in args:
                self.assertNotEqual(args[args.index("--degree") + 1], "6", cell["id"])


class ScheduleTest(unittest.TestCase):
    def test_balanced_interleaved_and_tiered(self):
        matrix = cf5_matrix.build()
        order = run_cf5.block_order(matrix)
        steps = run_cf5.schedule(matrix["cells"], 11, 24, 2, order)
        self.assertEqual(steps[0]["kind"], "smoke")
        tiers = [s["tier"] for s in steps]
        self.assertEqual(tiers, sorted(tiers))
        # Blocks are contiguous, in priority order: a cap cuts the last blocks only.
        blocks = [s["block"] for s in steps[1:]]
        runs = [b for i, b in enumerate(blocks) if i == 0 or blocks[i - 1] != b]
        self.assertEqual(len(runs), len(set(runs)))
        self.assertEqual(runs, [b for b in order if b in set(runs)])
        first = Counter(s["cell"] for s in steps if s["kind"] == "pair" and not s["warmup"]
                        and s["cf_first"])
        total = Counter(s["cell"] for s in steps if s["kind"] == "pair" and not s["warmup"])
        for cell_id, n in total.items():
            self.assertEqual(n, 24)
            self.assertEqual(first[cell_id], 12)
        self.assertEqual(steps, run_cf5.schedule(matrix["cells"], 11, 24, 2, order))


class RunnerTest(Fixture):
    def test_complete_run_and_classes(self):
        code, path = self.run_matrix(tiny_matrix(), "r1")
        self.assertEqual(code, 0)
        status = json.loads((self.dir / "r1" / "status.json").read_text())
        self.assertEqual(status["campaign"], "complete")
        self.assertEqual(status["cells"]["C1"], {"state": "COMPLETE", "pairs": 24})
        record = json.loads((self.dir / "r1" / "record.json").read_text())
        self.assertFalse(record["preparatory"])
        result = an.analyze(json.loads(path.read_text()), [an.load_run(self.dir / "r1")])
        self.assertEqual(result["cells"]["C1"]["metrics"]["t_ns"]["class"], "FASTER")
        self.assertEqual(result["cells"]["D1"]["metrics"]["t_ns"]["class"], "SMALLER")

    def test_preparatory_runs_are_never_classified(self):
        code, _ = self.run_matrix(tiny_matrix(), "p", "--preparatory", "--pairs", "2",
                                  "--warmup", "0", "--order-seed", "7")
        self.assertEqual(code, 0)
        with self.assertRaises(SystemExit):
            an.load_run(self.dir / "p")

    def test_reduced_pairs_need_preparatory(self):
        for flags in (["--pairs", "2"], ["--order-seed", "1"], ["--cap-hours", "1"],
                      ["--blocks", "K1"], ["--no-smoke"]):
            with self.assertRaises(SystemExit):
                self.run_matrix(tiny_matrix(), "x", *flags)

    def test_correctness_gate_stops_the_campaign(self):
        code, _ = self.run_matrix(tiny_matrix(cf_engine="boom"), "g")
        self.assertEqual(code, 1)
        status = json.loads((self.dir / "g" / "status.json").read_text())
        self.assertEqual(status["campaign"], "failed")
        self.assertEqual(status["cells"]["C1"]["state"], "FAILED")
        raw = (self.dir / "g" / "raw.jsonl").read_text()
        self.assertIn("failed_observation", raw, "the failed observation is recorded")
        code, _ = self.run_matrix(tiny_matrix(cf_engine="bad", check={"path": "ok",
                                                                      "equals": True}), "g2")
        self.assertEqual(code, 1)

    def test_cap_and_second_session(self):
        capped = tiny_matrix()
        capped["rules"]["cap_hours"] = 0.0000001
        code, path = self.run_matrix(capped, "s1")
        self.assertEqual(code, 0)
        status = json.loads((self.dir / "s1" / "status.json").read_text())
        self.assertEqual(status["campaign"], "incomplete")
        self.assertIn(status["cells"]["C1"]["state"], ("INCOMPLETE", "NOT_RUN"))
        # Session 2 runs exactly the incomplete cells, from scratch.
        code = run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                             str(self.dir / "s2"), "--session", "2",
                             "--resume-from", str(self.dir / "s1")])
        self.assertEqual(code, 0)
        record = json.loads((self.dir / "s2" / "record.json").read_text())
        incomplete = {c for c, s in status["cells"].items()
                      if s["state"] in ("INCOMPLETE", "NOT_RUN")}
        self.assertEqual(set(record["cells"]), incomplete)
        # Session 2 used the matrix with the tiny cap too (same hash); its cap is 8 h.
        result = an.analyze(json.loads(path.read_text()),
                            [an.load_run(self.dir / "s1"), an.load_run(self.dir / "s2")])
        self.assertEqual(result["cells"]["C1"]["metrics"]["t_ns"]["n"], 24)

    def test_session_two_never_repeats_complete_cells(self):
        code, path = self.run_matrix(tiny_matrix(), "c1")
        code = run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                             str(self.dir / "c2"), "--session", "2",
                             "--resume-from", str(self.dir / "c1")])
        record = json.loads((self.dir / "c2" / "record.json").read_text())
        self.assertEqual(record["cells"], [])

    def test_session_two_refused_after_a_gate_failure_or_another_matrix(self):
        self.run_matrix(tiny_matrix(cf_engine="boom"), "f1")
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", str(self.dir / "m-f1.json"), "--tools", str(self.tools),
                          "--out", str(self.dir / "f2"), "--session", "2",
                          "--resume-from", str(self.dir / "f1")])
        capped = tiny_matrix()
        capped["rules"]["cap_hours"] = 0.0000001
        self.run_matrix(capped, "h1")
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", str(self.dir / "m-f1.json"), "--tools", str(self.tools),
                          "--out", str(self.dir / "h2"), "--session", "2",
                          "--resume-from", str(self.dir / "h1")])

    def test_record_and_smoke(self):
        self.run_matrix(tiny_matrix(), "rs")
        record = json.loads((self.dir / "rs" / "record.json").read_text())
        self.assertTrue(record["order_seed_derived"])
        self.assertIn(sys.executable, record["provenance"]["executables"])
        self.assertIn("cpu", record["host"])
        smoke = [json.loads(l) for l in (self.dir / "rs" / "smoke.jsonl").read_text().splitlines()]
        self.assertEqual({(e["cell"], e["arm"]) for e in smoke}, {("C1", "cf"), ("C1", "ref")})
        raw = [json.loads(l) for l in (self.dir / "rs" / "raw.jsonl").read_text().splitlines()]
        self.assertIn("object", raw[-1]["cf"] if "cf" in raw[-1] else raw[-1])


class ClassTest(unittest.TestCase):
    def test_two_sided(self):
        m = 0.10
        self.assertEqual(an.two_sided(math.log(0.5), math.log(0.85), m), "FASTER")
        self.assertEqual(an.two_sided(math.log(1.2), math.log(1.5), m), "SLOWER")
        self.assertEqual(an.two_sided(math.log(0.95), math.log(1.05), m), "EQUIVALENT")
        self.assertEqual(an.two_sided(math.log(0.95), math.log(1.2), m), "INCONCLUSIVE")

    def test_regression_is_not_inconclusive(self):
        t = 0.10
        self.assertEqual(an.regression(math.log(0.9), math.log(1.05), t), "PASS")
        self.assertEqual(an.regression(math.log(1.15), math.log(1.3), t), "REGRESSION")
        self.assertEqual(an.regression(math.log(1.0), math.log(1.2), t), "INCONCLUSIVE")

    def test_interval_needs_exactly_24(self):
        self.assertIsNone(an.interval([0.0] * 23))
        ratios = [float(i) for i in range(24)]
        self.assertEqual(an.interval(ratios), [6.0, 17.0])

    def test_family_statements_separate_mixed_from_missing(self):
        def f(classes):
            return an.family_statement(classes, classes)
        self.assertEqual(f(["FASTER", "SLOWER"]), "mixed results")
        self.assertEqual(f(["FASTER", "SLOWER", "INCONCLUSIVE"]), "mixed results")
        self.assertEqual(f(["FASTER", "INCONCLUSIVE"]), "insufficient evidence")
        self.assertEqual(f(["EQUIVALENT", "NOT_RUN"]), "insufficient evidence")
        self.assertEqual(f(["FASTER", "FASTER", "EQUIVALENT"]), "prefer cluster-forest")
        self.assertEqual(f(["SLOWER", "SLOWER"]), "prefer reference")
        self.assertEqual(f(["EQUIVALENT", "SIMILAR"]), "no difference beyond the margins")
        self.assertEqual(f(["INCONCLUSIVE"]), "insufficient evidence")

    def test_minority_favourable_is_not_a_preference(self):
        # One FASTER among three EQUIVALENT: below half, so no preference, and not missing
        # evidence either.
        c = ["FASTER", "EQUIVALENT", "EQUIVALENT", "EQUIVALENT"]
        self.assertEqual(an.family_statement(c, c), "isolated differences")
        c = ["SLOWER", "EQUIVALENT", "EQUIVALENT"]
        self.assertEqual(an.family_statement(c, c), "isolated differences")

    def test_primary_counts_and_veto_metrics(self):
        # Primary metrics FASTER at 2 of 3 cells; secondary metrics EQUIVALENT: preference.
        self.assertEqual(an.family_statement(["FASTER", "FASTER", "EQUIVALENT"],
                                             ["FASTER", "EQUIVALENT", "FASTER", "EQUIVALENT",
                                              "EQUIVALENT", "EQUIVALENT"]),
                         "prefer cluster-forest")
        # A LARGER veto metric (memory) turns it into mixed results.
        self.assertEqual(an.family_statement(["FASTER", "FASTER"],
                                             ["FASTER", "FASTER", "LARGER"]), "mixed results")

    def test_undefined_ratio(self):
        self.assertEqual(an.deterministic(5.0, 0.0, 0.2), "UNDEFINED")
        self.assertEqual(an.deterministic(-5.0, -10.0, 0.2), "UNDEFINED")


if __name__ == "__main__":
    unittest.main()
