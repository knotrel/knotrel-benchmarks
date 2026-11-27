"""Tests of the v1.2.0 release-qualification tooling (knotrel#182)."""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
os.environ["LIFECYCLE_QUALIFICATION_ROOTS"] = os.pathsep.join(
    filter(None, [os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS"), tempfile.gettempdir()]))
import analyze_lifecycle_qualification as an  # noqa: E402
import summarize_v120q as sm  # noqa: E402
import test_lifecycle_qualification as tl  # noqa: E402
import v120q_matrix as mx  # noqa: E402

SHA = "b" * 64


class MatrixTest(unittest.TestCase):
    def test_blocks_counts_and_order(self):
        m = mx.build()
        self.assertEqual(m["counts"], {"B4": 38, "K1": 16, "K2": 6, "Q": 5, "V1": 9, "V2": 6})
        self.assertEqual(m["rules"]["block_order"], [["V1", "V2"], ["Q", "B4", "K2", "K1"]])
        self.assertEqual(m["rules"]["second_session_cap_hours"], 0)
        self.assertEqual(m["reference"], "v1.1.0")
        self.assertEqual(len({c["id"] for c in m["cells"]}), len(m["cells"]))

    def test_paired_cells_are_regression_checks_candidate_against_v110(self):
        for cell in mx.build()["cells"]:
            if cell["kind"] != "paired":
                continue
            self.assertEqual(cell["rule"], "regression", cell["id"])
            self.assertEqual(cell["reference"], "v1.1.0")
            cf, ref = cell["arms"]["cf"], cell["arms"]["ref"]
            self.assertTrue(cf["tool"].endswith("_cand") and ref["tool"].endswith("_base"), cell["id"])
            self.assertEqual(cf["args"], ref["args"], cell["id"])
            self.assertIn("compact-bfs", " ".join(cf["args"]), cell["id"])
            for metric in cell["metrics"]:
                if metric["margin_kind"] in ("time", "tail"):
                    self.assertIn("measurement", metric, cell["id"])

    def test_b4_sets(self):
        b4 = next(c for c in mx.build()["cells"] if c["id"] == "B4")
        sets = b4["b4"]
        self.assertEqual(len(sets["all"]), 38)
        self.assertEqual(len(sets["deciding"]), 23)
        self.assertEqual(len(sets["descriptive"]), 15)
        self.assertIn(mx.ATOMIC_CELL, sets["deciding"])
        self.assertEqual(sets["atomic"], [mx.ATOMIC_CELL])
        self.assertTrue(set(sets["unqualified"]) <= set(sets["descriptive"]))
        self.assertFalse(set(sets["deciding"]) & set(sets["descriptive"]))
        self.assertEqual(b4["order_seed"], 182400)

    def test_window_multipliers_cover_every_timed_cell_of_the_scope(self):
        factors = mx.window_multipliers()
        b4 = next(c for c in mx.build()["cells"] if c["id"] == "B4")["b4"]
        self.assertTrue(set(b4["all"]) <= set(factors))
        self.assertEqual(len(factors), 75)
        self.assertEqual(factors[mx.ATOMIC_CELL], 1)
        committed = SCRIPTS.parent / "results" / "v1.2.0-qualification" / "window-multipliers.json"
        self.assertEqual(json.loads(committed.read_text()), factors)

    def test_cap_is_recorded_only_when_given(self):
        self.assertEqual(mx.build()["cap"], "unset")
        m = mx.build(cap_hours=6)
        self.assertEqual((m["cap"], m["rules"]["cap_hours"]), ("set", 6))
        for bad in (0, -1, 1_000):
            with self.assertRaises(SystemExit):
                mx.build(cap_hours=bad)


class B4OnlyAnalysisTest(unittest.TestCase):
    """``--expect-only B4`` (plan section 4.2): the complete B4 matrix of the compact-bfs
    scope with the equivalent and atomic references and the frozen multipliers."""

    def b4_cells(self):
        import run_lifecycle_qualification as rlq
        return [c for c in rlq.matrix("final", "compact-bfs", True, True) if c["experiment"] == "B4"]

    def records(self, cell):
        records = tl.pairs([1.0] * 12)
        if re.search(r"-(ops|ops-query|events)-(equivalent|atomic)-", cell["id"]):
            for r in records[2:]:
                r.update({"atomicity_equivalent": True, "reference_max_op_plain_ops": 1,
                          "reference_split_chunks": 0})
        if "-ops-atomic-" in cell["id"]:
            for r in records[2:]:
                r.update({"atomicity_mode": "application_gate", "gate_check": {"pass": True},
                          "reference_gated_chunks": 3, "reference_lifecycle_chunks": 3})
        return records

    def analyze(self, provenance=None, multipliers=SHA, plan=None):
        cells = self.b4_cells() if plan is None else plan
        prov = {"only": "B4", "lifecycle_engines": "compact-bfs", "equivalent_references": True,
                "atomic_references": True, "window_multipliers_sha256": SHA, "cells": len(cells)}
        prov.update(provenance or {})
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tl.write_run(root, cells, {c["id"]: self.records(c) for c in cells}, provenance=prov)
            out = root / "report.json"
            sys.argv = ["x", str(root), "--expect-knotrel-rev", tl.REV, "--expect-multipliers-sha256",
                        multipliers, "--expect-probes-rev", tl.PROBES, "--expect-lifecycle-engines",
                        "compact-bfs", "--expect-equivalent-references", "--expect-atomic-references",
                        "--expect-only", "B4", "--json", str(out)]
            code = an.main()
            return code, (json.loads(out.read_text()) if code == 0 else None)

    def test_complete_b4_run_is_accepted(self):
        code, report = self.analyze()
        self.assertEqual(code, 0)
        self.assertEqual(len(report["timing"]), 38)
        atomic = next(r for r in report["timing"] if r["id"] == mx.ATOMIC_CELL)
        self.assertEqual(atomic["atomicity_mode"], "application_gate")

    def test_b4_run_needs_the_frozen_multipliers(self):
        self.assertEqual(self.analyze(multipliers="none")[0], 3)
        self.assertEqual(self.analyze(provenance={"window_multipliers_sha256": None})[0], 3)

    def test_b4_run_needs_every_cell_and_the_recorded_filter(self):
        self.assertEqual(self.analyze(plan=self.b4_cells()[1:])[0], 3)
        self.assertEqual(self.analyze(provenance={"only": "B4,C"})[0], 3)
        self.assertEqual(self.analyze(provenance={"cells": 37})[0], 3)


class SummaryTest(unittest.TestCase):
    def evaluation(self, c16, c64):
        status = "PASS" if c16 >= 0.5 and c64 >= 0.25 else "FAIL"
        criteria = {name: {"status": "PASS"} for name in ("Q1", "Q2", "Q4", "Q5")}
        criteria["Q3"] = {"status": status, "ratio_c16": c16, "ratio_c64": c64, "rule": "r"}
        return {"criteria": criteria, "run_status": "COMPLETE"}

    def inputs(self):
        m = mx.build(cap_hours=6)
        b4 = next(c for c in m["cells"] if c["id"] == "B4")["b4"]
        timing = [{"id": c, "status": "PASS", "interval_pct": [-1, 1]} for c in b4["all"]]
        timing[b4["all"].index(mx.ATOMIC_CELL)]["atomicity_mode"] = "application_gate"
        cf5 = {"cells": {"V2-x": {"block": "V2", "metrics": {"p99": {"class": "INCONCLUSIVE"}}},
                         "K2-y": {"block": "K2", "state": "NOT_RUN"}}}
        v1 = {"cells": [{"cell_id": "b1", "status": "PASS"}]}
        return m, cf5, v1, {"timing": timing}

    def test_q3_fail_names_the_b2_step(self):
        m, cf5, v1, b4 = self.inputs()
        s = sm.summarize(m, cf5, v1, self.evaluation(0.437, 0.384), b4)
        self.assertEqual(s["q3"]["status"], "FAIL")
        self.assertFalse(s["q3"]["c16_pass"])
        self.assertTrue(s["q3"]["c64_pass"])
        self.assertIn("B2", s["q3"]["next_step"])
        self.assertIn("Q3", s["not_passing_deciding"])
        self.assertIn("V2-x/p99", s["not_passing_deciding"])
        self.assertIn("K2-y", s["not_passing_deciding"])
        self.assertEqual(s["ops_atomic"]["outcome"], "PASS")
        self.assertIn("B2", sm.markdown(s))

    def test_q3_pass_and_unqualified_cells_carry_no_verdict(self):
        m, cf5, v1, b4 = self.inputs()
        s = sm.summarize(m, cf5, v1, self.evaluation(0.6, 0.3), b4)
        self.assertEqual(s["q3"]["status"], "PASS")
        self.assertIn("#87 can close", s["q3"]["next_step"])
        unq = [i for i in s["items"] if i.get("role") == "unqualified"]
        self.assertEqual(len(unq), 4)
        self.assertTrue(all(i["outcome"].startswith("no verdict") for i in unq))

    def test_missing_blocks_are_missing_evidence(self):
        m, _, _, _ = self.inputs()
        s = sm.summarize(m, None, None, None, None)
        self.assertEqual(len(s["missing_evidence"]), 4)
        self.assertIsNone(s["q3"])


if __name__ == "__main__":
    unittest.main()


class QEvaluatorLayoutTest(unittest.TestCase):
    """knotrel#182 attempt 1: run_q.sh writes block Q into ``{run}/Q`` (``{run}`` is run_cf5.py's
    ``delegated/Q-attempt<k>``), and the evaluator refused that name, so the session's own
    evaluation wrote an empty ``Q-evaluation.json``. The evaluator must accept the runner's
    layout with the same verdicts as the v1.0.0 ``part3`` layout, refuse any other name
    explicitly, and never leave a partial output file."""

    def run_q_at(self, root: Path, out: Path):
        import run_v100q_q as q
        import test_v100q as base
        r = q.QRunner(base.QTest().camp(root), out, 1800.0, clock=base.Clock(),
                      launch=base.FakeTool(), state=base.good_state)
        env = {"KNOTREL_PG_ADMIN_URL": "postgres://x", "LOAD_WINDOW_SECS": "5", "LOAD_BACKLOG": "10",
               "LOAD_ARM": "S", "LOAD_REMOTE_SSH": "h"}
        from unittest import mock
        with mock.patch.dict(os.environ, env), mock.patch("sys.stdout"):
            r.run()

    def test_runner_layout_evaluates_like_part3(self):
        import evaluate_v100q_q as ev
        with tempfile.TemporaryDirectory() as d:
            runner = Path(d) / "a" / "delegated" / "Q-attempt1" / "Q"
            legacy = Path(d) / "b" / "part3"
            self.run_q_at(Path(d) / "a", runner)
            self.run_q_at(Path(d) / "b", legacy)
            got, want = ev.evaluate(runner), ev.evaluate(legacy)
        self.assertEqual(got["final_attempt"], "Q-attempt1/Q")
        self.assertEqual(got["superseded_attempts"], [])
        self.assertEqual({k: v["status"] for k, v in got["criteria"].items()},
                         {k: v["status"] for k, v in want["criteria"].items()})

    def test_other_names_fail_explicitly_without_output(self):
        import evaluate_v100q_q as ev
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "delegated" / "Q-attempt1" / "Qx"
            self.run_q_at(Path(d), out)
            target = Path(d) / "Q-evaluation.json"
            with mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d}), \
                    self.assertRaisesRegex(SystemExit, "unexpected Q directory name Qx"):
                ev.main([str(out), "--out", str(target)])
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(d).glob("Q-evaluation*")), [])

    def test_out_is_written_only_after_success(self):
        import evaluate_v100q_q as ev
        from unittest import mock
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "delegated" / "Q-attempt1" / "Q"
            self.run_q_at(Path(d), out)
            target = Path(d) / "Q-evaluation.json"
            with mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d}), mock.patch("sys.stdout"):
                self.assertEqual(ev.main([str(out), "--out", str(target)]), 0)
            self.assertEqual(json.loads(target.read_text())["final_attempt"], "Q-attempt1/Q")

    def test_run_q_uses_the_out_option_and_records_failures(self):
        script = (SCRIPTS.parent / "results/v1.2.0-qualification/run_q.sh").read_text()
        self.assertNotIn('evaluate_v100q_q.py "$RUN/Q" > ', script)
        self.assertIn('--out "$RUN/Q-evaluation.json"', script)
        self.assertIn("Q-evaluation.error.txt", script)


class Attempt2MatrixTest(unittest.TestCase):
    """Plan section 13: the scope of attempt 2, from the diff v1.1.0..candidate."""

    def test_blocks_cells_and_order(self):
        m = mx.build(attempt=2)
        self.assertEqual(m["attempt"], 2)
        self.assertEqual(m["counts"], {"B4": 38, "Q": 10, "V1": 9, "V2": 6})
        self.assertEqual(m["rules"]["block_order"], [["V1", "V2"], ["Q", "B4"]])
        ids = [c["id"] for c in m["cells"]]
        self.assertFalse([i for i in ids if i.startswith(("K1-", "K2-"))])
        self.assertEqual(ids.index("Q") + 1, ids.index("Q-K4"))
        self.assertIn("section 13", m["plan"])

    def test_v1_roles_and_seeds(self):
        v1 = next(c for c in mx.build(attempt=2)["cells"] if c["id"] == "V1")
        self.assertEqual(sorted(v1["v1"]["deciding"]), sorted(mx.V1_HTTP_CELLS))
        self.assertEqual(len(v1["v1"]["descriptive"]), 4)
        self.assertTrue(all(c.startswith("core_") for c in v1["v1"]["descriptive"]))
        self.assertEqual(v1["seeds"], {"block1": [182210, 182211, 182212],
                                       "block2": [182220, 182221, 182222]})
        self.assertFalse(set(sum(v1["seeds"].values(), [])) & set(sum(mx.V1_SEEDS.values(), [])))

    def test_q_rules_follow_option_b(self):
        cells = {c["id"]: c for c in mx.build(attempt=2)["cells"]}
        self.assertEqual(cells["Q"]["q_rule"]["deciding"], ["Q1", "Q2", "Q4", "Q5"])
        self.assertEqual(cells["Q"]["q_rule"]["reported"], ["Q3"])
        self.assertEqual(cells["Q-K4"]["q_rule"]["deciding"], ["Q1", "Q2", "Q3", "Q4"])
        self.assertEqual(cells["Q-K4"]["q_rule"]["cost"], ["Q5"])
        self.assertIn("KNOTREL_MAX_CONCURRENT_QUERIES=4", cells["Q-K4"]["q_rule"]["mode"])

    def test_attempt1_matrix_is_unchanged(self):
        frozen = (SCRIPTS.parent / "results/v1.2.0-qualification/v120q-matrix.json").read_text()
        self.assertEqual(json.dumps(mx.build(cap_hours=5.0), indent=1, sort_keys=True) + "\n", frozen)


class Attempt2SummaryTest(unittest.TestCase):
    def evaluation(self, c16, c64, q5="PASS"):
        return {"criteria": {**{n: {"status": "PASS"} for n in ("Q1", "Q2", "Q4")},
                             "Q5": {"status": q5},
                             "Q3": {"status": "PASS" if c16 >= 0.5 and c64 >= 0.25 else "FAIL",
                                    "ratio_c16": c16, "ratio_c64": c64, "rule": "r"}},
                "run_status": "COMPLETE"}

    def inputs(self):
        m = mx.build(cap_hours=3, attempt=2)
        b4 = next(c for c in m["cells"] if c["id"] == "B4")["b4"]
        timing = [{"id": c, "status": "PASS", "interval_pct": [-1, 1]} for c in b4["all"]]
        cf5 = {"cells": {"V2-x": {"block": "V2", "metrics": {"p99": {"class": "PASS"}}}}}
        v1 = {"cells": [{"cell_id": c, "status": "PASS"} for c in mx.V1_HTTP_CELLS]
              + [{"cell_id": mx.V1_CORE_CELLS[1], "status": "REGRESSION"}]}
        return m, cf5, v1, {"timing": timing}

    def test_roles_decide_and_q3_comes_from_k4(self):
        m, cf5, v1, b4 = self.inputs()
        s = sm.summarize(m, cf5, v1, self.evaluation(0.16, 0.09), b4,
                         q_k4=self.evaluation(0.56, 0.55, q5="FAIL"))
        self.assertEqual(s["not_passing_deciding"], [])
        self.assertEqual(s["q3"]["status"], "PASS")
        self.assertIn("=4", s["q3_mode"])
        self.assertEqual(s["q3_default_mode"]["status"], "FAIL")
        roles = {i["item"]: (i.get("role"), i["outcome"]) for i in s["items"]}
        self.assertEqual(roles["Q/Q3"], ("reported", "FAIL"))
        self.assertEqual(roles["Q-K4/Q5"], ("cost", "FAIL"))
        self.assertEqual(roles[mx.V1_CORE_CELLS[1]], ("descriptive", "REGRESSION"))
        text = sm.markdown(s)
        self.assertIn("Default mode (reported, not deciding)", text)
        self.assertIn("| `Q-K4/Q5` | cost | FAIL |", text)

    def test_deciding_failures_are_listed(self):
        m, cf5, v1, b4 = self.inputs()
        s = sm.summarize(m, cf5, v1, self.evaluation(0.16, 0.09, q5="FAIL"), b4,
                         q_k4=self.evaluation(0.45, 0.30))
        self.assertEqual(sorted(s["not_passing_deciding"]), ["Q-K4/Q3", "Q/Q5"])

    def test_tool_error_is_missing_evidence_not_a_failure(self):
        m, cf5, v1, b4 = self.inputs()
        status = {"cells": {"Q-K4": {"state": "TOOL_ERROR"}}}
        s = sm.summarize(m, cf5, v1, self.evaluation(0.16, 0.09), b4, q_k4=None, status=status)
        self.assertEqual(s["tool_errors"], ["Q-K4"])
        self.assertTrue(any("tool error" in x for x in s["missing_evidence"]))
        self.assertNotIn("Q-K4/Q3", s["not_passing_deciding"])
        self.assertIsNone(s["q3"])


class Attempt2RunnerTest(unittest.TestCase):
    def test_runner_check_passes(self):
        import check_v120q_q_runner as chk
        from unittest import mock
        with mock.patch("sys.stdout"):
            self.assertEqual(chk.main([]), 0)

    def test_run_q_tool_error_branch_and_variant(self):
        script = (SCRIPTS.parent / "results/v1.2.0-qualification/run_q.sh").read_text()
        self.assertIn("exit 6", script)
        self.assertIn('run_v100q_q.py "$QCAMP"', script)
        self.assertIn('"$CAMP/binaries-sha256.txt"', script)

    def test_prepare_attempt2_wiring(self):
        script = (SCRIPTS.parent / "results/v1.2.0-qualification/prepare_v120q.sh").read_text()
        for needle in ("variant-k4", "KNOTREL_MAX_CONCURRENT_QUERIES=4", "check_v120q_q_runner.py",
                       "MIN_FREE_GB", "182210 182211 182212", '"tool_error_exit"'):
            self.assertIn(needle, script)
