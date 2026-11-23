"""Tests for the v1.0.0 qualification tooling (results/v1.0.0-qualification).

They pin that the v1.0.0 campaign re-runs the frozen v0.9.0 method on the approved reduced
perimeter: the matrix differs from v0.9.0's only where the plan says (block D absent); the
wrappers bind this matrix and change nothing else; A runs a fixed n = 24 with the
order-statistic interval [r(7), r(18)] and no interim decision; the runner runs the reduced
chain and refuses to start without a real freeze record; the launch check uses the runner's
arguments; block Q keeps its round order, cap and failure rules; and the site export keeps
every verdict as measured. No test measures anything.
"""

import copy
import json
import math
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import analyze_bc_qualification as bc  # noqa: E402
import run_p0_aa as p0  # noqa: E402
import run_v070q3_autonomous as q3runner  # noqa: E402
import run_v090q_autonomous as v090runner  # noqa: E402
import run_v100q_autonomous as runner  # noqa: E402
import test_analyze_bc_qualification as afix  # noqa: E402

V100 = ROOT / "results" / "v1.0.0-qualification"
V090 = ROOT / "results" / "v0.9.0-qualification"
MATRIX = json.loads((V100 / "MATRIX.json").read_text())
V090_MATRIX = json.loads((V090 / "MATRIX.json").read_text())
ENV = (V100 / "launch_env_check.sh").read_text()
PREPARE = (V100 / "prepare_campaign.sh").read_text()
REF = "223f04c10b0af663b54e269e0970ee10ac1dc6b2"
CAND = "d84728381aba5ba6cab6a2c8faf22e16251b554a"  # any 40-character commit: the candidate is a parameter
BASE_PROBES = "53c50e962983886bd7442012aa4c2f561cb5a3fa"


def camp_dir(root: Path) -> Path:
    return root / f"v1.0.0-qualification-{CAND[:7]}-attempt1"


# -- matrix ------------------------------------------------------------------------------------
class MatrixTest(unittest.TestCase):
    def test_rules_are_v090s_except_a(self):
        mine, theirs = dict(MATRIX["rules"]), dict(V090_MATRIX["rules"])
        self.assertIn("FIXED n = 24", mine.pop("A"))
        theirs.pop("A")
        self.assertEqual(mine, theirs)

    def test_a_is_fixed_24_with_v090_cells_and_seeds(self):
        a, old = MATRIX["experiments"]["A"], V090_MATRIX["experiments"]["A"]
        for key in ("cells", "session_seeds", "extension_seeds", "harness"):
            self.assertEqual(a[key], old[key], key)
        self.assertEqual(a["design"]["pairs_per_cell"], 24)
        self.assertEqual(a["design"]["blocks"], 2)
        self.assertEqual(a["design"]["pairs_per_cell_per_block"], 12)
        self.assertIsNone(a["design"]["extension_rule"])
        self.assertIn("none", a["design"]["interim_analysis"])
        self.assertIn("[r(7), r(18)]", a["design"]["interval"])
        self.assertIn("v0.9.0", a["question"])

    def test_other_experiments_unchanged_and_perimeter_selected(self):
        ex, old = MATRIX["experiments"], V090_MATRIX["experiments"]
        for key in ("R", "Rmem", "M_reg"):
            self.assertEqual(ex[key], old[key], key)
        mine, theirs = copy.deepcopy(ex["B_C"]), copy.deepcopy(old["B_C"])
        self.assertEqual(mine.pop("only"), "B4,C")
        self.assertIn("--only B4,C", mine.pop("collector"))
        for m in (mine, theirs):
            m.pop("question")
            theirs.pop("collector", None)
        self.assertEqual(mine, theirs)
        t5, old_t5 = copy.deepcopy(ex["T5"]), copy.deepcopy(old["T5"])
        self.assertIn("core rule", t5.pop("perimeter"))
        for m in (t5, old_t5):
            m.pop("arms")
            m.pop("question")
        self.assertEqual(t5, old_t5)
        self.assertNotIn("M_desc", ex)
        self.assertEqual(sorted(ex), ["A", "B_C", "M_reg", "R", "Rmem", "T5"])

    def test_block_d_is_absent(self):
        for key in list(MATRIX) + list(MATRIX["experiments"]) + list(MATRIX["budget"]) + list(MATRIX["v1_0_0"]):
            self.assertNotIn(key, ("D", "block_D", "part2", "v0_9_0"), key)
        self.assertNotIn("compare_v100q_d", json.dumps(MATRIX))
        self.assertNotIn("part2", MATRIX["budget"]["plan_minutes"])
        self.assertNotIn("D", MATRIX["v1_0_0"]["perimeter"]["included"])
        self.assertFalse((ROOT / "scripts" / "compare_v100q_d.py").exists())

    def test_unchanged_sections(self):
        for key in ("host_conditions", "invalidation", "resource_ceilings", "analysis"):
            self.assertEqual(MATRIX[key], V090_MATRIX[key], key)

    def test_conformance_unchanged_except_series_cap_and_directory(self):
        mine, theirs = MATRIX["conformance"], V090_MATRIX["conformance"]
        self.assertEqual({k: v for k, v in mine.items() if k != "qualification_3"},
                         {k: v for k, v in theirs.items() if k != "qualification_3"})
        q, old = mine["qualification_3"], theirs["qualification_3"]
        self.assertEqual(q["revision_3"], old["revision_3"])
        self.assertEqual((q["attempt_series"], q["attempts_cap"]), ("v100q", 2))
        self.assertTrue(q["first_conforming_attempt_is_final"] and q["every_directory_counts"])
        self.assertIn("v1.0.0-qualification-<cand7>-attemptN", q["campaign_directory"])

    def test_budget_two_separate_caps(self):
        budget = MATRIX["budget"]
        self.assertEqual(budget["final_cap_minutes"], 105)
        self.assertEqual(budget["plan_minutes"], {"part1": 105, "q": 30})
        self.assertEqual(MATRIX["v1_0_0"]["q"]["budget_minutes"], 30)
        self.assertEqual(q3runner.LIMITS["budget_s"], 105 * 60.0)
        self.assertIn("not a shared pool", budget["caps"])

    def test_references_and_unfrozen_candidate(self):
        refs = MATRIX["references"]
        self.assertIn(REF, refs["product_reference"])
        self.assertIsNone(refs["descriptive_reference"])
        self.assertIn(BASE_PROBES, refs["benchmarks_reference"])
        self.assertIn("NOT FROZEN", refs["candidate"])
        self.assertIn("NOT FROZEN", MATRIX["status"])
        self.assertIn(f"REF={REF}", PREPARE)
        self.assertIn(f"BASE_PROBES={BASE_PROBES}", PREPARE)
        self.assertEqual(runner.REFERENCE, REF)

    def test_q_section(self):
        q = MATRIX["v1_0_0"]["q"]
        self.assertEqual(q["deciding"], ["Q1", "Q2", "Q4", "Q5"])
        self.assertIn("same session", q["q5_reference_arm"])
        self.assertIn("candidate first in rounds 1 and 3", q["order"])

    def test_copied_files_are_v090s(self):
        for name in ("window-multipliers-q3.json", "series_budget.sh", "check_restored.sh", "launch_tools.txt"):
            self.assertEqual((V100 / name).read_bytes(), (V090 / name).read_bytes(), name)


# -- freeze ------------------------------------------------------------------------------------
class FreezeTest(unittest.TestCase):
    def test_template_is_not_a_freeze_record(self):
        template = json.loads((V100 / "FREEZE.template.json").read_text())
        self.assertIn("NOT FROZEN", template["status"])
        self.assertIsNone(template["frozen_utc"])
        self.assertEqual((template["campaign"], template["revision"]), (runner.CAMPAIGN, runner.FREEZE_REVISION))
        self.assertEqual(template["reference"]["commit"], REF)
        self.assertEqual(template["probes"]["v0.9.0"], BASE_PROBES)
        self.assertEqual(template["budget_minutes"], {"part1": 105, "q": 30})
        for path in template["file_sha256_paths"]:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_freeze_record_if_present_is_frozen(self):
        path = V100 / "FREEZE.json"
        if not path.exists():
            self.skipTest("not frozen yet")
        freeze = json.loads(path.read_text())
        self.assertTrue(freeze["frozen_utc"])
        self.assertNotIn("NOT FROZEN", str(freeze.get("status", "")))
        self.assertRegex(freeze["candidate"]["commit"], r"^[0-9a-f]{40}$")
        self.assertIn(freeze["core_rule"]["outcome"], runner.CORE_RULE_OUTCOMES)

    def test_frozen_collectors_refuse_without_freeze(self):
        if (V100 / "FREEZE.json").exists():
            self.skipTest("frozen")
        with tempfile.TemporaryDirectory() as d:
            env = {k: v for k, v in os.environ.items() if k not in ("KNOTREL_INTERFERENCE_DIR", "KNOTREL_GATE_DIR")}
            proc = subprocess.run([sys.executable, "scripts/run_v100q_collect.py", "r", "--out", f"{d}/x", "--ref", "a",
                                   "--cand", "b"], cwd=ROOT, env=env, capture_output=True, text=True)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("not frozen", proc.stderr)


# -- bindings ----------------------------------------------------------------------------------
class BindingTest(unittest.TestCase):
    def test_collector_binds_this_matrix_and_refuses_mdesc(self):
        import run_v100q_collect as collect
        import run_v070r_collect as base
        self.assertEqual(collect.MATRIX, V100 / "MATRIX.json")
        self.assertEqual(base.MATRIX, V100 / "MATRIX.json")
        proc = subprocess.run([sys.executable, "scripts/run_v100q_collect.py", "mdesc", "--dry-run"], cwd=ROOT,
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_analysis_binds_this_matrix_and_refuses_mdesc(self):
        import analyze_v100q as analysis
        self.assertEqual(analysis.MATRIX, V100 / "MATRIX.json")
        with mock.patch.object(sys, "argv", ["analyze_v100q.py", "mdesc", "x"]), mock.patch("sys.stderr"):
            self.assertEqual(analysis.main(), 2)

    def test_report_binds_this_matrix(self):
        import report_v100q_bc as report
        self.assertEqual(report.frozen.MATRIX, V100 / "MATRIX.json")


# -- runner ------------------------------------------------------------------------------------
class RunnerTest(unittest.TestCase):
    def sequence(self, cls, camp, outcome="identical"):
        calls = []
        r = cls(camp, CAND)
        r.run_step = lambda name, argv, block, dirs=(): calls.append((name, argv, [str(d) for d in dirs]))
        r.analysis = mock.Mock(side_effect=AssertionError("no analysis may run inside the v1.0 chain"))
        if cls is runner.Part1Runner:
            r.freeze = lambda: {"core_rule": {"outcome": outcome}}
        else:
            (r.camp / "A").mkdir(parents=True, exist_ok=True)
            (r.camp / "A" / "decision-analysis-main.json").write_text(json.dumps({"extension_cells_required": []}))
            r.analysis = lambda name, argv: calls.append((name, argv, []))
            r.stamp = lambda *a: None
        r.sequence()
        return r, calls

    def test_chain_is_two_a_blocks_then_b4c_r_rmem_mreg(self):
        with tempfile.TemporaryDirectory() as d:
            _, calls = self.sequence(runner.Part1Runner, camp_dir(Path(d)))
        self.assertEqual([c[0] for c in calls], ["A-block1", "A-block2", "BC", "R", "Rmem", "Mreg"])
        b1, b2 = calls[0][1], calls[1][1]
        self.assertTrue(b1[b1.index("--manifest") + 1].endswith("A/plan/manifest.json"))
        self.assertTrue(b1[b1.index("--execute") + 1].endswith("A/raw-main"))
        self.assertTrue(b2[b2.index("--manifest") + 1].endswith("A/plan-block2/manifest.json"))
        self.assertTrue(b2[b2.index("--execute") + 1].endswith("A/extension/raw-extension"))
        self.assertTrue(calls[1][2][0].endswith("A/extension/raw-extension"))
        bc_args = calls[2][1]
        self.assertEqual(bc_args[bc_args.index("--only") + 1], "B4,C")
        self.assertTrue(all(c[1][1] == "scripts/run_v100q_collect.py" for c in calls))

    def test_steps_after_a_equal_v090s_except_bindings(self):
        with tempfile.TemporaryDirectory() as d:
            camp = camp_dir(Path(d))
            _, mine = self.sequence(runner.Part1Runner, camp)
            _, theirs = self.sequence(v090runner.Part1Runner, camp)
        theirs = {n: a for n, a, _ in theirs}
        swap = {"scripts/run_v090q_collect.py": "scripts/run_v100q_collect.py",
                "results/v0.9.0-qualification/window-multipliers-q3.json":
                    "results/v1.0.0-qualification/window-multipliers-q3.json"}
        for name, argv, _ in mine[2:]:
            expected = [swap.get(x, x) for x in theirs[name]]
            if name == "BC":
                i = expected.index("--window-multipliers")
                expected[i:i] = ["--only", "B4,C"]
            self.assertEqual(argv, expected, name)
        self.assertNotIn("T5", [n for n, _, _ in mine])
        self.assertNotIn("Mdesc", [n for n, _, _ in mine])

    def test_core_rule_different_runs_full_bc_and_t5(self):
        with tempfile.TemporaryDirectory() as d:
            _, calls = self.sequence(runner.Part1Runner, camp_dir(Path(d)), "different")
        self.assertEqual([c[0] for c in calls], ["A-block1", "A-block2", "BC", "T5", "R", "Rmem", "Mreg"])
        self.assertNotIn("--only", calls[2][1])
        t5 = calls[3][1]
        self.assertTrue(t5[t5.index("--base") + 1].endswith("t5base-probes/release/core-lifecycle"))

    def test_unknown_core_rule_refuses(self):
        r = runner.Part1Runner(camp_dir(Path("/nonexistent")), CAND)
        r.freeze = lambda: {"core_rule": {"outcome": "TBD"}}
        with self.assertRaises(runner.Stop):
            r.core_rule_triggered()

    def write_freeze(self, camp, freeze):
        bench = camp / "src" / "cand" / "knotrel-benchmarks" / runner.V100
        bench.mkdir(parents=True, exist_ok=True)
        if freeze is not None:
            (bench / "FREEZE.json").write_text(json.dumps(freeze))

    def test_preflight_requires_a_real_freeze_record(self):
        paths = list(runner.fc.REQUIRED_FROZEN_PATHS)
        good = {"campaign": runner.CAMPAIGN, "revision": 1, "frozen_utc": "2026-11-30T00:00:00Z",
                "candidate": {"commit": CAND}, "reference": {"commit": REF},
                "core_rule": {"outcome": "identical",
                              "comparison": {"file": "v1.0.0-prefreeze-x/logs/core-rule.json", "sha256": "1" * 64}},
                "tooling": {"commit": "2" * 40}, "file_sha256_paths": paths,
                "file_sha256": {p: "0" * 64 for p in paths}}
        template = json.loads((V100 / "FREEZE.template.json").read_text())
        cases = {"absent": None, "template": template,
                 "v090": {**good, "campaign": "v0.9.0 qualification"},
                 "draft": {**good, "frozen_utc": None},
                 "status": {**good, "status": "TEMPLATE - NOT FROZEN"},
                 "candidate": {**good, "candidate": {"commit": "1" * 40}},
                 "reference": {**good, "reference": {"commit": "v0.9.0"}},
                 "core rule": {**good, "core_rule": {}},
                 "hashes": good}
        for name, freeze in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                camp = camp_dir(Path(d))
                self.write_freeze(camp, freeze)
                (camp / "src/cand/knotrel-benchmarks" / runner.V100 / "MATRIX.json").write_text("{}")
                with self.assertRaises(runner.Stop) as stop:
                    runner.Part1Runner(camp, CAND).preflight()
                self.assertEqual(stop.exception.status, "NOT STARTED")
                if name == "hashes":
                    self.assertIn("frozen files differ", stop.exception.cause)

    def test_preflight_requires_full_candidate_sha(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "v1.0.0-qualification-d847283-attempt1"
            with self.assertRaises(runner.Stop):
                runner.Part1Runner(camp, "d847283").preflight()

    def test_records_use_this_directory_and_restore(self):
        seen = {}

        def fake(self_):
            seen["dir"], seen["outputs"] = q3runner.Q3, q3runner.OUTPUTS

        with tempfile.TemporaryDirectory() as d, mock.patch.object(q3runner.Runner, "write_records", fake):
            runner.Part1Runner(Path(d), CAND).write_records()
        self.assertEqual(seen, {"dir": "results/v1.0.0-qualification", "outputs": runner.OUTPUTS})
        self.assertEqual(q3runner.Q3, "results/v0.7.0-qualification-3")
        self.assertEqual(q3runner.OUTPUTS[0], "A/raw-main")

    def test_outputs_include_both_a_blocks(self):
        self.assertIn("A/raw-main", runner.OUTPUTS)
        self.assertIn("A/extension", runner.OUTPUTS)
        self.assertNotIn("Mdesc", runner.OUTPUTS)

    def test_env_check_dry_runs_match_runner(self):
        with tempfile.TemporaryDirectory() as d:
            _, calls = self.sequence(runner.Part1Runner, camp_dir(Path(d)))
        steps = {n: a for n, a, _ in calls}
        flags = lambda ws: [w for w in ws if w.startswith("--") and w not in ("--dry-run", "--execute")]  # noqa: E731
        seen = set()
        for line in ENV.splitlines():
            words = shlex.split(line.replace("$WM", "WM").replace("$ONLY", "--only B4,C")) if line.startswith("run ") else []
            if len(words) > 4 and words[3] == "scripts/run_v100q_collect.py":
                name = words[1]
                self.assertEqual(words[4], steps[name][2], name)
                self.assertEqual(flags(words[5:]), flags(steps[name][3:]), name)
                seen.add(name)
        self.assertEqual(seen, {"A-block1", "A-block2", "BC", "R", "Rmem", "Mreg"})

    def test_bc_passes_the_interference_duplicate_check(self):
        import run_lifecycle_qualification as lifecycle
        with tempfile.TemporaryDirectory() as d:
            _, calls = self.sequence(runner.Part1Runner, camp_dir(Path(d)))
        argv = calls[2][1][3:]
        self.assertNotEqual(argv[argv.index("--core") + 1], argv[argv.index("--core-count") + 1])
        cells = [c for c in lifecycle.matrix("final", "compact-bfs", True) if c["experiment"] in ("B4", "C")]
        self.assertEqual(len([c for c in cells if c["experiment"] == "B4"]), 37)
        self.assertEqual(len([c for c in cells if c["experiment"] == "C"]), 60)

    def test_launch_command(self):
        with tempfile.TemporaryDirectory() as d:
            out = subprocess.run(["sh", str(V100 / "launch_command.sh"), f"{d}/camp", CAND], capture_output=True,
                                 text=True, check=True).stdout
            bad = subprocess.run(["sh", str(V100 / "launch_command.sh"), f"{d}/camp", "short"], capture_output=True)
        self.assertIn(f"scripts/run_v100q_autonomous.py {d}/camp {CAND}", out)
        self.assertIn("run_part3.sh", out)
        self.assertNotIn("--part", out)
        self.assertNotEqual(bad.returncode, 0)


# -- A: fixed n = 24 -----------------------------------------------------------------------------
class FixedTwentyFourTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def blocks(self, ratios1=None, ratios2=None, cells2=None):
        afix.write_matrix(self.root / "b1", ratios1 or {})
        for index, cell_id in enumerate(cells2 or p0.QUALIFICATION_CELL_IDS):
            ratios = (ratios2 or {}).get(cell_id) or {afix.primary(cell_id): [1.0] * 12}
            afix.write_cell(self.root / "b2", cell_id, ratios, first_pair_id=200 + 12 * index, phase="extension")
        return self.root / "b1", self.root / "b2"

    def test_a_uses_n24_and_the_order_statistic_interval(self):
        import analyze_v100q_a as a
        self.assertEqual(a.PAIRS_PER_CELL, 24)
        self.assertEqual(a.INTERVAL_RANKS, (7, 18))
        self.assertAlmostEqual(a.coverage(24, 7), 0.9773, places=4)
        self.assertAlmostEqual(a.coverage(24, 7), 1 - 2 * sum(math.comb(24, i) for i in range(7)) / 2 ** 24)
        self.assertAlmostEqual(a.coverage(12, 3), 0.9614, places=4)
        cell = afix.LIFECYCLE
        first, second = afix.spread(2, 20), afix.spread(6, 25)
        b1, b2 = self.blocks({cell: {afix.primary(cell): first}}, {cell: {afix.primary(cell): second}})
        report = a.analyze(b1, b2)
        self.assertEqual(report["pairs_per_cell"], 24)
        self.assertAlmostEqual(report["interval_coverage"], 0.9773, places=4)
        decided = afix.cell_of(report, cell)
        logs = sorted(math.log(x) for x in first + second)
        self.assertEqual(decided["pairs"], 24)
        self.assertEqual(decided["blocks"], {"block1": 12, "block2": 12})
        self.assertAlmostEqual(decided["primary"]["interval_log"][0], logs[6])
        self.assertAlmostEqual(decided["primary"]["interval_log"][1], logs[17])
        self.assertTrue(all(c["pairs"] == 24 for c in report["cells"]))
        self.assertEqual(len(report["cells"]), 9)

    def test_no_interim_decision_is_computed_or_written(self):
        import analyze_v100q_a as a
        b1, b2 = self.blocks()
        with mock.patch.object(bc, "analyze", side_effect=AssertionError("interim analysis")):
            report = a.analyze(b1, b2)
        for key in ("main_cells", "extension_cells_required", "main_pairs"):
            self.assertNotIn(key, report)
        for cell in report["cells"]:
            self.assertNotIn("extension_required", cell)
        self.assertTrue(all(c["status"] == "PASS" for c in report["cells"]))

    def test_frozen_two_stage_analyzer_refuses_a_full_block_two(self):
        b1, b2 = self.blocks()
        with self.assertRaisesRegex(bc.AnalysisError, "differ from required"):
            bc.analyze(b1, b2, "v0.4.0")

    def test_final_classes_are_the_frozen_ones(self):
        import analyze_v100q_a as a
        cell = afix.LIFECYCLE
        wide = afix.spread(5, 30)
        b1, b2 = self.blocks({cell: {afix.primary(cell): wide}}, {cell: {afix.primary(cell): wide}})
        decided = afix.cell_of(a.analyze(b1, b2), cell)
        self.assertIn(decided["status"], ("INCONCLUSIVE_DISCLOSED", "UNRESOLVED", "REGRESSION"))
        self.assertNotEqual(decided["status"], "INCONCLUSIVE")

    def test_block_two_must_hold_all_nine_cells(self):
        import analyze_v100q_a as a
        b1, b2 = self.blocks(cells2=p0.QUALIFICATION_CELL_IDS[:8])
        with self.assertRaisesRegex(bc.AnalysisError, "block2 cells"):
            a.analyze(b1, b2)

    def test_block_two_after_block_one_and_distinct(self):
        import analyze_v100q_a as a
        b1, _ = self.blocks()
        with self.assertRaisesRegex(bc.AnalysisError, "block 2 is the block 1 directory"):
            a.analyze(b1, b1)

    def test_cli_writes_once(self):
        import analyze_v100q_a as a
        b1, b2 = self.blocks()
        out = self.root / "A.json"
        with mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": ""}), self.assertRaisesRegex(SystemExit, "outside the allowed roots"):
            a.main(["--block1", str(b1), "--block2", str(b2), "--output", str(out)])  # tmp dir is not a root
        roots = mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": str(self.root)})
        roots.start()
        self.addCleanup(roots.stop)
        with mock.patch("sys.stdout"):
            self.assertEqual(a.main(["--block1", str(b1), "--block2", str(b2), "--output", str(out)]), 0)
        self.assertEqual(json.loads(out.read_text())["design"][:15], "fixed n = 24 pe")
        with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
            a.main(["--block1", str(b1), "--block2", str(b2), "--output", str(out)])


# -- B4 and C ------------------------------------------------------------------------------------
class OnlyB4CTest(unittest.TestCase):
    def run_dir(self, root: Path, only="B4,C", drop=None, extra=None):
        import run_lifecycle_qualification as lifecycle
        cells = [c for c in lifecycle.matrix("final", "compact-bfs", True) if c["experiment"] in ("B4", "C")]
        if drop:
            cells = [c for c in cells if c["id"] != drop]
        if extra:
            cells.append(extra)
        (root / "plan").mkdir(parents=True)
        (root / "raw").mkdir()
        (root / "provenance.json").write_text(json.dumps({"profile": "final", "only": only,
                                                          "lifecycle_engines": "compact-bfs",
                                                          "equivalent_references": True,
                                                          "window_multipliers_sha256": "w"}))
        with open(root / "run-log.jsonl", "w") as log:
            for c in cells:
                log.write(json.dumps({"id": c["id"], "exit": 0, "host_before": {"power": "Now drawing from 'AC Power'"}}) + "\n")
                (root / "raw" / f"{c['id']}.jsonl").write_text("")
        return {c["id"]: c for c in cells}

    def validate(self, root, cells):
        import analyze_v100q_bc as w
        with mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": str(root.parent)}):
            return w.validate_only(root, cells, "rev", "w", "compact-bfs", True)

    def test_accepts_exactly_the_b4_and_c_cells(self):
        import analyze_v100q_bc as w
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "BC"
            cells = self.run_dir(root)
            self.assertEqual(len(cells), 97)
            self.assertEqual(self.validate(root, cells)["only"], "B4,C")
        for name, kwargs in {"full": {"only": ""}, "B4": {"only": "B4"},
                             "missing": {"drop": "B4-http-events-compact-bfs-sparse-10000"},
                             "extra": {"extra": {"id": "B1-x", "experiment": "B1"}}}.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                root = Path(d) / "BC"
                cells = self.run_dir(root, **kwargs)
                with self.assertRaises(w.frozen.Invalid):
                    self.validate(root, cells)

    def test_frozen_validate_refuses_only_runs_and_is_restored(self):
        import analyze_v100q_bc as w
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "BC"
            cells = self.run_dir(root)
            with self.assertRaisesRegex(w.frozen.Invalid, "not a complete final run"):
                w.FROZEN_VALIDATE(root, cells, "rev", "w", "compact-bfs", True)
        with w.installed("B4,C"):
            self.assertIs(w.frozen.validate, w.validate_only)
        self.assertIs(w.frozen.validate, w.FROZEN_VALIDATE)
        with w.installed("full"):
            self.assertIs(w.frozen.validate, w.FROZEN_VALIDATE)
        with self.assertRaises(SystemExit), w.installed("B4"):
            pass


class ReportTest(unittest.TestCase):
    def analysis(self):
        eq = MATRIX["experiments"]["B_C"]["equivalent_references"]
        ids = eq["deciding"] + eq["descriptive"] + eq["not_equivalent"]["cells"]
        timing = []
        for cid in ids:
            cell = {"id": cid, "status": "PASS", "median_change_pct": 1.0, "interval_pct": [0.0, 2.0], "tolerance_pct": 25}
            if "-equivalent-" in cid and any(f"-{k}-" in cid for k in ("ops", "ops-query", "events")):
                cell["atomicity_equivalent"] = cid not in eq["not_equivalent"]["cells"]
                cell["reference_max_op_plain_ops"] = 1
            timing.append(cell)
        return {"timing": timing, "memory": [], "sustained": [{"id": "C-rss-lifecycle-x", "C1": "PASS", "C2": "PASS",
                                                               "C4": "EXCEEDS_BUDGET"}]}

    def test_identical_core_rule_needs_no_t5(self):
        import report_v100q_bc as report
        out = report.report(self.analysis(), MATRIX)
        self.assertEqual(out["core_rule"], "identical")
        self.assertFalse([r for r in out["rows"] if r["kind"] == "T5"])
        self.assertEqual([r["id"] for r in out["disclosures"]], ["C-rss-lifecycle-x:C4"])
        self.assertEqual(out["deciding_non_pass"], [])
        self.assertFalse(out["overall"]["release_supported_by_q3"])  # E6 stays unqualified
        roles = {r["id"]: r["role"] for r in out["rows"]}
        self.assertEqual(roles["B4-http-ops-equivalent-compact-bfs-hub-10000"], "not_equivalent")

    def test_cli_arguments(self):
        import report_v100q_bc as report
        with mock.patch("sys.stderr"):
            self.assertEqual(report.main(["x", "a.json"]), 2)
            self.assertEqual(report.main(["x", "a.json", "--core-rule", "different"]), 2)
            self.assertEqual(report.main(["x", "a.json", "--core-rule", "identical", "t5.json"]), 2)


class T5Test(unittest.TestCase):
    def repo(self, root: Path, second: str, source_change: bool = False) -> tuple:
        lock = root / "tools/lifecycle-probes/Cargo.lock"
        lock.parent.mkdir(parents=True)
        body = ('[[package]]\nname = "axum"\nversion = "0.8.9"\n\n[[package]]\nname = "knotrel-core"\nversion = "0.9.0"\n\n'
                '[[package]]\nname = "knotrel-server"\nversion = "0.9.0"\n')
        lock.write_text(body)
        (lock.parent / "src.rs").write_text("fn main() {}\n")
        git = lambda *a: subprocess.run(["git", "-C", str(root), *a], check=True, capture_output=True, text=True).stdout  # noqa: E731
        git("init", "-q")
        git("-c", "user.email=t@t", "-c", "user.name=t", "add", ".")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "a")
        base = git("rev-parse", "HEAD").strip()
        lock.write_text(second)
        if source_change:
            (lock.parent / "src.rs").write_text("fn main() { }\n")
        git("-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "b")
        return base, git("rev-parse", "HEAD").strip(), body

    def test_probe_source_check_allows_only_the_knotrel_version_lines(self):
        import analyze_v100q_t5 as t5
        major = lambda body, v="1.0.0-rc.1": body.replace('"knotrel-core"\nversion = "0.9.0"', f'"knotrel-core"\nversion = "{v}"').replace(  # noqa: E731
            '"knotrel-server"\nversion = "0.9.0"', f'"knotrel-server"\nversion = "{v}"')
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d}):
            root = Path(d) / "ok"
            root.mkdir()
            body = ('[[package]]\nname = "axum"\nversion = "0.8.9"\n\n[[package]]\nname = "knotrel-core"\nversion = "0.9.0"\n\n'
                    '[[package]]\nname = "knotrel-server"\nversion = "0.9.0"\n')
            base, cand, _ = self.repo(root, major(body))
            t5.probe_source_equal(root, base, cand)
            import analyze_v090q_t5 as v090
            with self.assertRaises(v090.frozen.Invalid):
                v090.probe_source_equal(root, base, cand)  # the v0.9.0 check accepts 0.x lines only
        for name, second, change in (("other package", body.replace('"axum"\nversion = "0.8.9"', '"axum"\nversion = "0.8.10"'), False),
                                     ("source", major(body), True)):
            with self.subTest(name), tempfile.TemporaryDirectory() as d, \
                    mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d}):
                root = Path(d) / "r"
                root.mkdir()
                base, cand, _ = self.repo(root, second, change)
                with self.assertRaises(t5.v090.frozen.Invalid):
                    t5.probe_source_equal(root, base, cand)
        self.assertIs(t5.v090.probe_source_equal, t5.FROZEN_CHECK)

    def test_probe_source_check_semver_forms(self):
        """1.0.0 and 1.0.0-rc.1 lines pass; build metadata and malformed versions do not."""
        import analyze_v100q_t5 as t5
        for line, ok in (('+version = "1.0.0"', True), ('+version = "1.0.0-rc.1"', True), ('-version = "0.9.0"', True),
                         ('+version = "1.0.0-rc.1+build.5"', False), ('+version = "1.0.0-"', False),
                         ('+version = "1.0.0-rc..1"', False), ('+version = "1.0"', False)):
            with self.subTest(line):
                self.assertEqual(bool(t5.VERSION_LINE.match(line)), ok)


# -- Q -------------------------------------------------------------------------------------------
def q_record(cell: str, rep=1, rps=1000.0, p99=100.0, ready=5.0, rate=None, lag=(100.0, 120.0)):
    scenario, graph, clients = cell.split()
    clients = int(clients.split("=")[1])
    if scenario == "L1":
        metrics = {"markers": {"p50_ms": 50.0, "p99_ms": 150.0, "max_ms": 250.0, "timeouts": 0,
                               "first10_median_ms": lag[0], "last10_median_ms": lag[1]},
                   "writer": {"changes_per_sec": 100.0}, "queries": {"requests_per_sec": rps, "p99_ms": p99, "refused_503": 0},
                   "retained_bytes": {"start": 1000, "end": 2000}, "feeder_503_refusals": 0}
    else:
        default = {0: 160000.0, 16: 100000.0, 64: 60000.0}[clients]
        metrics = {"events": 300000, "secs_to_ready": ready, "events_per_sec": default if rate is None else rate,
                   "queries": {"requests_per_sec": rps, "p99_ms": p99}, "feeder_503_refusals": 0}
    return {"scenario": scenario, "graph": graph, "clients": clients, "rep": rep, "window_secs": 60, "backlog": 100000,
            "metrics": metrics}


class FakeTool:
    """Stands in for the load tool: writes results.jsonl and its own summary.json per step."""

    def __init__(self, values=None, fail=None, clock=None, per_step=60.0):
        self.calls, self.values, self.fail = [], values or {}, fail or {}
        self.clock, self.per_step = clock, per_step

    def __call__(self, argv, env, step_dir, timeout_s):
        import evaluate_v100q_q as ev
        side = "candidate" if env["KNOTREL_BIN"].endswith("cand-server/release/knotrel-server") else "reference"
        self.calls.append({"step": step_dir.name, "side": side, "cells": env["LOAD_CELLS"].split(","), "env": env,
                           "timeout": timeout_s})
        if self.clock is not None:
            self.clock.now += self.per_step
            if self.clock.now > self.clock.deadline_hint:
                return -999
        records, code = [], 0
        for cell in env["LOAD_CELLS"].split(","):
            failure = self.fail.get((step_dir.name, cell))
            if failure:
                (step_dir / "load.stderr").write_text(failure)
                code = 101
                break
            records.append(q_record(cell, **self.values.get((side, cell), {})))
        with open(step_dir / "results.jsonl", "w") as handle:
            for r in records:
                handle.write(json.dumps(r) + "\n")
        if code == 0:
            summary = ev.tool_evaluate([ev.flatten(r) for r in records])
            (step_dir / "summary.json").write_text(json.dumps({"measurement_secs": 1.0, "summary": summary}))
        return code


class Clock:
    def __init__(self):
        self.now, self.deadline_hint = 1000.0, float("inf")

    def __call__(self):
        return self.now


def good_state(_out):
    return {"utc": "t", "power": "Now drawing from 'AC Power'\n", "therm": "Note: No thermal warning level has been recorded",
            "free_bytes": 10 ** 11, "docker": "knotrel-pg-test-18 postgres:18.7 Up"}


class QTest(unittest.TestCase):
    def camp(self, root: Path) -> Path:
        camp = camp_dir(root)
        for p in ("cand-server/release/knotrel-server", "ref-server/release/knotrel-server",
                  "feeder/release/knotrel-pg-feeder", "feeder/release/examples/load"):
            (camp / "targets" / p).parent.mkdir(parents=True, exist_ok=True)
            (camp / "targets" / p).write_text("x")
        return camp

    def run_q(self, root, tool, cap_s=1800.0, clock=None):
        import run_v100q_q as q
        clock = clock or Clock()
        r = q.QRunner(self.camp(root), root / "part3", cap_s, clock=clock, launch=tool, state=good_state)
        with mock.patch.dict(os.environ, {"KNOTREL_PG_ADMIN_URL": "postgres://x", "LOAD_WINDOW_SECS": "5",
                                          "LOAD_BACKLOG": "10", "LOAD_ARM": "S", "LOAD_REMOTE_SSH": "h"}), \
                mock.patch("sys.stdout"):
            code = r.run()
        return r, code

    def test_round_order_cells_and_environment(self):
        import run_v100q_q as q
        tool = FakeTool()
        with tempfile.TemporaryDirectory() as d:
            r, code = self.run_q(Path(d), tool)
            run = json.loads((Path(d) / "part3" / "run.json").read_text())
            self.assertNotIn("postgres://", (Path(d) / "part3" / "run.json").read_text())
        self.assertEqual(code, 0)
        self.assertEqual(run["status"], "COMPLETE")
        self.assertEqual([c["step"] for c in tool.calls],
                         ["round1-candidate", "round1-reference", "round2-reference", "round2-candidate",
                          "round3-candidate", "round3-reference"])
        for call in tool.calls:
            env = call["env"]
            self.assertEqual(env["LOAD_REPS"], "1")
            for removed in ("LOAD_WINDOW_SECS", "LOAD_BACKLOG", "LOAD_ARM", "LOAD_REMOTE_SSH"):
                self.assertNotIn(removed, env)
            expected = q.CANDIDATE_CELLS if call["side"] == "candidate" else q.REFERENCE_CELLS
            self.assertEqual(tuple(call["cells"]), expected)
            server = "cand-server" if call["side"] == "candidate" else "ref-server"
            self.assertTrue(env["KNOTREL_BIN"].endswith(f"{server}/release/knotrel-server"))
            self.assertTrue(env["FEEDER_BIN"].endswith("feeder/release/knotrel-pg-feeder"))
        self.assertEqual(len(q.CANDIDATE_CELLS), 7)
        self.assertEqual(q.REFERENCE_CELLS, ("L1 G100k C=16", "L1 G100k C=64"))

    def test_cap_makes_q_nonconforming_and_keeps_observations(self):
        import evaluate_v100q_q as ev
        clock = Clock()
        tool = FakeTool(clock=clock, per_step=400.0)
        clock.deadline_hint = 1000.0 + 1800.0
        with tempfile.TemporaryDirectory() as d:
            r, code = self.run_q(Path(d), tool, clock=clock)
            out = ev.evaluate(Path(d) / "part3")
            failures = (Path(d) / "part3" / "failures.jsonl").read_text()
        self.assertEqual(code, 1)
        self.assertEqual(r.status, "NONCONFORMING")
        self.assertIn("Q BUDGET EXHAUSTED", r.cause)
        self.assertIn("cap", failures)
        self.assertEqual(len(tool.calls), 5)  # the sixth step would start after the deadline
        self.assertTrue(all(c["timeout"] <= 1800.0 for c in tool.calls))
        self.assertEqual(out["q_status"], "NONCONFORMING")
        self.assertIsNone(out["q_pass"])
        self.assertIsNone(out["criteria"]["Q5"]["status"])  # reference lacks round 3

    def test_infrastructure_failure_reruns_once(self):
        tool = FakeTool(fail={("round1-candidate", "L1 G100k C=64"): "Error: No space left on device (os error 28)",
                              ("round1-candidate-cont1", "L1 G100k C=64"): "Error: No space left on device"})
        with tempfile.TemporaryDirectory() as d:
            r, _ = self.run_q(Path(d), tool)
            failures = [json.loads(x) for x in (Path(d) / "part3" / "failures.jsonl").read_text().splitlines()]
            import evaluate_v100q_q as ev
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual([f["classification"] for f in failures], ["infrastructure", "infrastructure"])
        self.assertEqual([f["rerun"] for f in failures], [True, False])
        self.assertEqual(r.reruns, {"round1-candidate:L1 G100k C=64": "round1-candidate"})  # per observation (N4)
        steps = [c["step"] for c in tool.calls]
        self.assertEqual(steps[:3], ["round1-candidate", "round1-candidate-cont1", "round1-candidate-cont2"])
        self.assertEqual(tool.calls[2]["cells"], ["L1 G10k C=16", "L2 G100k C=0", "L2 G100k C=16", "L2 G100k C=64"])
        # The second infrastructure failure loses the observation: Q is NONCONFORMING (it allows the
        # one rerun of Q), and the criterion using it has no verdict rather than FAIL (B4).
        self.assertEqual(r.status, "NONCONFORMING")
        self.assertEqual(r.infrastructure_exhausted, ["round1-candidate:L1 G100k C=64"])
        self.assertIsNone(out["criteria"]["Q2"]["status"])
        self.assertEqual(out["criteria"]["Q1"]["status"], "PASS")  # C=16 observations unaffected

    def test_product_and_ambiguous_failures_are_not_infrastructure(self):
        import run_v100q_q as q
        ok = good_state(None)
        for text in ("thread 'main' panicked: knotrel-server exited with status 101",
                     "Error: No space left on device while the feeder was not ready",
                     "thread 'main' panicked at examples/load.rs:400: called unwrap() on an Err value"):
            self.assertEqual(q.classify_failure(text, ok, ok)["classification"], "not_infrastructure", text)
        self.assertEqual(q.classify_failure("connection refused (os error 61) to 127.0.0.1:55432 postgres", ok, ok)
                         ["classification"], "infrastructure")
        battery = dict(ok, power="Now drawing from 'Battery Power'")
        self.assertEqual(q.classify_failure("anything", ok, battery)["classification"], "infrastructure")

    def test_product_failure_counts_as_measured_and_fails_its_criteria(self):
        import evaluate_v100q_q as ev
        tool = FakeTool(fail={("round2-candidate", "L1 G100k C=16"): "panicked: knotrel-server crashed"})
        with tempfile.TemporaryDirectory() as d:
            self.run_q(Path(d), tool)
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual(out["q_status"], "COMPLETE")
        for name in ("Q1", "Q2", "Q5"):
            self.assertEqual(out["criteria"][name]["status"], "FAIL", name)
        self.assertEqual(out["criteria"]["Q4"]["status"], "PASS")
        self.assertFalse(out["q_pass"])

    def test_q5_against_same_session_reference(self):
        import evaluate_v100q_q as ev
        cases = {"pass": ({"rps": 901.0, "p99": 124.0}, "PASS"), "slow": ({"rps": 899.0, "p99": 100.0}, "FAIL"),
                 "tail": ({"rps": 1000.0, "p99": 126.0}, "FAIL")}
        for name, (cand, expected) in cases.items():
            values = {("candidate", c): cand for c in ev.Q5_CELLS}
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                self.run_q(Path(d), FakeTool(values=values))
                out = ev.evaluate(Path(d) / "part3")
                self.assertEqual(out["criteria"]["Q5"]["status"], expected)
                self.assertEqual(out["criteria"]["Q5"]["cells"]["L1 G100k C=16"]["query_rps"][0], 1000.0)
                self.assertEqual(out["q_pass"], expected == "PASS")
                self.assertEqual(out["observations"]["reference"], {c: 3 for c in ev.Q5_CELLS})

    def test_missing_value_fails_the_criterion(self):
        import evaluate_v100q_q as ev
        values = {("candidate", "L2 G100k C=64"): {"ready": None}}
        with tempfile.TemporaryDirectory() as d:
            self.run_q(Path(d), FakeTool(values=values))
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual(out["criteria"]["Q4"]["status"], "FAIL")
        self.assertTrue(out["criteria"]["Q4"]["failed_observations"])

    def test_q3_classified_as_measured(self):
        import evaluate_v100q_q as ev
        values = {("candidate", "L2 G100k C=16"): {"rate": 20000.0}}
        with tempfile.TemporaryDirectory() as d:
            self.run_q(Path(d), FakeTool(values=values))
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual(out["Q3"]["status"], "FAIL")
        self.assertNotIn("Q3", out["deciding"])
        self.assertTrue(out["q_pass"])

    def test_port_must_match_the_tools_own_summary(self):
        import evaluate_v100q_q as ev
        with tempfile.TemporaryDirectory() as d:
            self.run_q(Path(d), FakeTool())
            path = Path(d) / "part3" / "round1-reference" / "summary.json"
            summary = json.loads(path.read_text())
            summary["summary"]["cells"]["L1 G100k C=16"]["query_rps"]["median"] += 1.0
            path.write_text(json.dumps(summary))
            with self.assertRaisesRegex(SystemExit, "not faithful"):
                ev.evaluate(Path(d) / "part3")

    def test_port_median_and_missing_values(self):
        import evaluate_v100q_q as ev
        self.assertEqual(ev.median([3.0, 1.0, 2.0]), 2.0)
        self.assertEqual(ev.median([1.0, 2.0, 3.0, 4.0]), 2.5)
        self.assertIsNone(ev.median([]))
        self.assertIsNone(ev.get({"a": {"b": None}}, ("a", "b")))
        self.assertIsNone(ev.get({"a": True}, ("a",)))

    def test_v080_baseline_hash_checked(self):
        import evaluate_v100q_q as ev
        with tempfile.TemporaryDirectory() as d:
            self.run_q(Path(d), FakeTool())
            bad = Path(d) / "b.json"
            bad.write_text("{}")
            with self.assertRaisesRegex(SystemExit, "baseline"):
                ev.evaluate(Path(d) / "part3", bad)

    def test_run_part3_preconditions(self):
        text = (V100 / "run_part3.sh").read_text()
        self.assertIn("^CONFORMING", text)
        self.assertIn("run_v100q_q.py", text)
        self.assertIn("evaluate_v100q_q.py", text)
        self.assertIn("NONCONFORMING", text)
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "camp"
            (camp / "logs").mkdir(parents=True)
            (camp / "logs" / "CONFORMANCE.txt").write_text("BUDGET EXHAUSTED: x\n")
            proc = subprocess.run(["sh", str(V100 / "run_part3.sh"), str(camp)], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)
            self.assertIn("Part 1 is not CONFORMING", proc.stderr)
            proc = subprocess.run(["sh", str(V100 / "run_part3.sh"), str(camp), "2"], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3)


# -- core rule, probe compatibility ---------------------------------------------------------------
class CliConfinementTest(unittest.TestCase):
    """Every path taken from the command line is confined (cli_paths), as in v0.9.0."""

    def test_paths_outside_the_allowed_roots_are_refused(self):
        import core_rule_v100q as core
        import evaluate_v100q_q as ev
        import probe_compat_v100q as pc
        import report_v100q_bc as report
        import run_v100q_q as q
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": ""}):
            calls = {"core rule": lambda: core.main(["x", d, f"{d}/o.json"]),
                     "report": lambda: report.main(["x", f"{d}/a.json", "--core-rule", "identical"]),
                     "evaluate": lambda: ev.main([d]),
                     "Q runner": lambda: q.main([d, f"{d}/part3"]),
                     "probe compat": lambda: pc.main(["x", d, f"{d}/o"])}
            for name, call in calls.items():
                with self.subTest(name), self.assertRaisesRegex(SystemExit, "outside the allowed roots"):
                    call()
            with self.subTest("option-like"), self.assertRaisesRegex(SystemExit, "invalid path"):
                core.main(["x", d, "--output=x"])


class CoreRuleTest(unittest.TestCase):
    def test_outcome(self):
        import core_rule_v100q as core
        same = core.compare(Path("/t"), digest=lambda p: "a")
        self.assertEqual(same["outcome"], "identical")
        self.assertEqual(len(same["pairs"]), 3)
        diff = core.compare(Path("/t"), digest=lambda p: "b" if "harness" in str(p) and "A-C" in str(p) else "a")
        self.assertEqual(diff["outcome"], "different")
        self.assertIn("T5", diff["consequence"])
        built = PREPARE.replace("$T/", "targets/").replace("targets/A-$X-harness", "targets/A-B-harness targets/A-C-harness")
        for name, cand, ref in core.PAIRS:
            for target in (cand, ref):
                self.assertTrue(f"targets/{target.split('/')[0]}" in built, target)


class ProbeCompatTest(unittest.TestCase):
    def test_reduced_arguments(self):
        import probe_compat_v100q as pc
        args = ["--scenario", "events", "--nodes", "100000", "--requests", "40", "--pairs", "12", "--warmup", "2",
                "--cycles", "30", "--reps", "21", "--seed", "5000001"]
        out = pc.smaller(args)
        values = dict(zip(out[::2], out[1::2]))
        self.assertEqual(values, {"--scenario": "events", "--nodes": "100000", "--requests": "2", "--pairs": "2",
                                  "--warmup": "0", "--cycles": "2", "--reps": "1", "--seed": "5000001"})
        self.assertEqual(pc.smaller(["import-core", "--nodes", "10"]), ["import-core", "--nodes", "10"])


# -- site export ----------------------------------------------------------------------------------
def export_inputs(a_status="PASS"):
    metric = lambda name, b, c, lo, hi, status="PASS", n=12: {  # noqa: E731
        "metric": name, "pairs": n, "B_median": b, "C_median": c, "interval_log": [lo, hi],
        "interval_pct": [(math.exp(lo) - 1) * 100, (math.exp(hi) - 1) * 100], "status": status}
    a_cells = [{"cell_id": cid, "status": a_status, "pairs": 24,
                "primary": metric("workload_wall_ns", 100.0, 101.0, -0.01, 0.03, n=24),
                "supporting": [metric("peak_rss_bytes", 10.0, 10.0, -0.01, 0.01, n=24),
                               dict(metric("link_p99_ns", 40.0, 40.0, 0, 0, n=24), status="REPORT_ONLY")]}
               for cid in p0.QUALIFICATION_CELL_IDS]
    eq = MATRIX["experiments"]["B_C"]["equivalent_references"]
    timing, rows = [], []
    for role, ids in (("deciding", eq["deciding"]), ("descriptive", eq["descriptive"]),
                      ("not_equivalent", eq["not_equivalent"]["cells"])):
        for cid in ids:
            timing.append(dict(metric("window_ns", 5e6, 5.1e6, 0.0, 0.04), id=cid, experiment="B4"))
            rows.append({"id": cid, "kind": "timing", "role": role, "status": "PASS"})
    sustained = [{"id": "C-heap-lifecycle-x", "metric": "net_heap_bytes", "late_over_early": 1.01, "C1": "PASS",
                  "C2": "PASS", "C3": "PASS"},
                 {"id": "C-rss-lifecycle-x", "metric": "net_rss_bytes", "late_over_early": 1.4, "C1": "PASS",
                  "C2": "PASS", "C4": "EXCEEDS_BUDGET"}]
    rows += [{"id": "C-heap-lifecycle-x:C1", "kind": "C1", "role": "deciding", "status": "PASS"},
             {"id": "C-heap-lifecycle-x:C2", "kind": "C2", "role": "deciding", "status": "PASS"},
             {"id": "C-heap-lifecycle-x:C3", "kind": "C3", "role": "deciding", "status": "PASS"},
             {"id": "C-rss-lifecycle-x:C4", "kind": "C4", "role": "deciding", "status": "EXCEEDS_BUDGET"}]
    r = {"R-core-import-sparse-10k-20-10": dict(metric("observation_ns", 1e6, 0.98e6, -0.03, -0.01),
                                                verdict="PASS (IMPROVED)")}
    rmem = {"Rmem-import-core-20-10": {"metrics": {"peak_after": {"ref": 100, "cand": 100, "change_pct": 0.0, "verdict": "PASS"},
                                                   "live_after": {"ref": 0, "cand": 0, "change_pct": 0.0, "verdict": "PASS"}}}}
    mreg = {"result": {"Mreg-x": {"verdict": "PASS", "metrics": {
        "requests_per_s": dict(metric("requests_per_s", 350.0, 340.0, -0.05, 0.02), direction="higher_is_better"),
        "latency_ns.p99": dict(metric("latency_ns.p99", 9e7, 9.1e7, -0.02, 0.04), direction="lower_is_better")}}}}
    crit = {"Q1": {"status": "PASS", "marker_p99_ms": 150.0, "marker_max_ms": 250.0},
            "Q2": {"status": "PASS"}, "Q3": {"status": "FAIL", "ratio_c16": 0.18, "ratio_c64": 0.1},
            "Q4": {"status": "PASS", "secs_to_ready_c64": 5.7},
            "Q5": {"status": "PASS", "failed_observations": [], "missing_observations": [], "cells": {
                c: {"query_rps": [1000.0, 990.0], "rps_pass": True, "query_p99_ms": [100.0, 101.0], "p99_pass": True}
                for c in ("L1 G100k C=16", "L1 G100k C=64")}}}
    freeze = {"campaign": "v1.0.0 qualification", "frozen_utc": "2026-11-30T00:00:00Z",
              "candidate": {"commit": CAND}, "reference": {"tag": "v0.9.0", "commit": REF}}
    return {"freeze": freeze, "a": {"pairs_per_cell": 24, "phase": "final", "cells": a_cells},
            "bc": {"timing": timing, "sustained": sustained}, "bc_report": {"rows": rows}, "r": r, "rmem": rmem,
            "mreg": mreg, "q": {"q_status": "COMPLETE", "run_cause": None, "criteria": crit, "Q5_v0_8_0": {"cells": {}}}}


class ExportTest(unittest.TestCase):
    URLS = {"campaign": "https://github.com/knotrel/knotrel-benchmarks/tree/x/results/v1.0.0-qualification",
            "evidence": "https://github.com/knotrel/knotrel-benchmarks/tree/x/results/v1.0.0-qualification/analysis"}

    def export(self, inputs):
        """Build the comparison and check it against the site schema 2."""
        import build_site
        import export_v100q_site as ex
        comparison, excluded = ex.build(inputs, self.URLS, "Apple M3 4P+4E, 16 GB")
        build_site.validate({"schema_version": 2, "releases": [{"version": "1.0.0", "status": "published",
                                                                 "schema_version": 2, "baseline_policy": "p",
                                                                 "comparisons": [comparison]}]})
        return comparison["results"], excluded, comparison

    def assert_unmeasured(self, r):
        import build_site
        self.assertTrue(r["status_reason"].strip())
        self.assertFalse([k for k in build_site.MEASUREMENTS if r.get(k) is not None])

    def test_rows_validate_and_keep_intervals_and_verdicts(self):
        rows, excluded, comparison = self.export(export_inputs())
        self.assertEqual((comparison["reference_version"], comparison["reference_sha"]), ("0.9.0", REF))
        self.assertTrue(all(r["status"] == "completed" for r in rows))
        a_row = next(r for r in rows if r["experiment"] == "A")
        self.assertIn("97.73 %", a_row["ci_method"])
        self.assertIn("not a 95 % interval", a_row["ci_method"])
        self.assertEqual(a_row["runs"], 24)
        self.assertAlmostEqual(a_row["delta_ci95"][1], (math.exp(0.03) - 1) * 100)
        b4 = [r for r in rows if r.get("experiment") == "B4"]
        self.assertEqual(len(b4), 24)  # the 11 listed deciding + 13 descriptive; the 2 E6 cells are report-only
        self.assertTrue(all("96.14 %" in r["ci_method"] and "not v0.9.0" in r["ci_method"] for r in b4))
        self.assertEqual(sorted({(r["role"] == "deciding", r["category"]) for r in b4}),
                         [(False, "disclosure"), (True, "decisive")])
        rmem = [r for r in rows if r["experiment"] == "Rmem" and r["metric"] == "peak_after"]
        self.assertEqual(len(rmem), 1)
        self.assertIsNone(rmem[0]["delta_ci95"])
        self.assertEqual(rmem[0]["ci_unavailable_reason"], "deterministic counts, one run per arm")
        q = [r for r in rows if r["experiment"] == "Q"]
        self.assertTrue(all(r["ci_unavailable_reason"] == "3 observations; the protocol reports the median and range"
                            for r in q if r["criterion"] != "Q2"))
        self.assertEqual({r["verdict"] for r in q if r["criterion"] == "Q3"}, {"FAIL"})
        self.assertEqual({r["category"] for r in q}, {"decisive"})
        mreg = next(r for r in rows if r["metric"] == "requests_per_s")
        self.assertEqual((mreg["candidate"], mreg["reference"], mreg["direction"]), (350.0, 340.0, "higher"))
        self.assertAlmostEqual(mreg["delta_ci95"][0], (math.exp(-0.02) - 1) * 100)
        ids = [e["id"] for e in excluded]
        e6 = MATRIX["experiments"]["B_C"]["equivalent_references"]["not_equivalent"]["cells"]
        # Plan section 11: only E6 and Q5 against v0.8.0 stay in the campaign report (plus the A
        # supporting metrics that the frozen analyzer marks REPORT_ONLY, which have no verdict).
        self.assertEqual(sorted(i for i in ids if not i.endswith(":link_p99_ns")), sorted(e6 + ["Q5 against v0.8.0"]))
        self.assertTrue(all(e["status"] == "REPORT_ONLY" for e in excluded if e["id"].endswith(":link_p99_ns")))
        for scenario in ("C-heap-lifecycle-x C1 (rule at every checkpoint)", "C-heap-lifecycle-x C2 (rule at every checkpoint)",
                         "Q2 L1 (rule on every observation)"):
            r = next(x for x in rows if x["scenario"] == scenario)
            self.assertEqual((r["verdict"], r["category"], r["status"], r["reference_kind"]),
                             ("PASS", "decisive", "completed", "threshold"))
            self.assertTrue(r["estimate_unavailable_reason"])
            self.assertFalse([k for k in ("delta_pct", "delta_ci95", "candidate", "reference") if r.get(k) is not None])
        self.assertFalse([r for r in rows if r["scenario"] in e6])  # E6: campaign report only (plan section 11)

    def test_a_classes_are_published_verbatim(self):
        for status in ("PASS", "REGRESSION", "INCONCLUSIVE_DISCLOSED", "UNRESOLVED"):
            with self.subTest(status):
                rows, _, _ = self.export(export_inputs(status))
                a = [r for r in rows if r["experiment"] == "A" and r["role"] == "deciding"]
                self.assertEqual(len(a), len(p0.QUALIFICATION_CELL_IDS))
                self.assertEqual({(r["verdict"], r["category"], r["status"]) for r in a},
                                 {(status, "decisive", "completed")})

    def test_b4_classes_categories_and_not_equivalent(self):
        inputs = export_inputs()
        rows_in = inputs["bc_report"]["rows"]
        deciding = [r for r in rows_in if r["kind"] == "timing" and r["role"] == "deciding"]
        descriptive = [r for r in rows_in if r["kind"] == "timing" and r["role"] == "descriptive"]
        deciding[0]["status"] = "TIMER_LIMITED"
        deciding[1].update(status="NOT_EQUIVALENT", measured_status="PASS")
        deciding[2]["status"] = "INCONCLUSIVE"
        deciding[3]["status"] = "REGRESSION"
        high = next(r for r in descriptive if "import-high" in r["id"])
        high["status"] = "REGRESSION"
        rows, _, _ = self.export(inputs)
        by_id = {r["scenario"]: r for r in rows if r["experiment"] == "B4"}
        for cell, verdict in ((deciding[0]["id"], "TIMER_LIMITED"), (deciding[1]["id"], "NOT_EQUIVALENT"),
                              (deciding[2]["id"], "INCONCLUSIVE"), (deciding[3]["id"], "REGRESSION")):
            self.assertEqual((by_id[cell]["verdict"], by_id[cell]["category"], by_id[cell]["status"]),
                             (verdict, "decisive", "completed"))
            self.assertIsNotNone(by_id[cell]["candidate"])  # TIMER_LIMITED keeps its numbers
        self.assertEqual(by_id[deciding[1]["id"]]["measured_status"], "PASS")
        h = by_id[f"{high['id']} (descriptive)"]
        self.assertEqual((h["verdict"], h["category"], h["status"]), ("REGRESSION", "disclosure", "completed"))

    def test_c3_decisive_and_c4_disclosure(self):
        inputs = export_inputs()
        next(r for r in inputs["bc_report"]["rows"] if r["kind"] == "C3")["status"] = "FAIL"
        rows, _, _ = self.export(inputs)
        c = {r["metric"].split(" ")[0]: r for r in rows if r["experiment"] == "C"}
        self.assertEqual((c["net_heap_bytes"]["verdict"], c["net_heap_bytes"]["category"]), ("FAIL", "decisive"))
        self.assertEqual((c["net_rss_bytes"]["verdict"], c["net_rss_bytes"]["category"], c["net_rss_bytes"]["status"]),
                         ("EXCEEDS_BUDGET", "disclosure", "completed"))

    def test_r_qualifier_and_rmem_regression(self):
        inputs = export_inputs()
        inputs["rmem"]["Rmem-import-core-20-10"]["metrics"]["peak_after"].update(cand=130, verdict="REGRESSION")
        rows, _, _ = self.export(inputs)
        r = next(x for x in rows if x["experiment"] == "R")
        self.assertEqual((r["verdict"], r["metric_status"], r["category"]), ("PASS (IMPROVED)", "PASS", "decisive"))
        self.assertTrue(r["improved"])
        self.assertEqual(next(x for x in rows if x["experiment"] == "Rmem")["verdict"], "REGRESSION")
        inputs = export_inputs()
        inputs["r"]["R-core-import-sparse-10k-20-10"].update(status="INCONCLUSIVE", verdict="INCONCLUSIVE")
        rows, _, _ = self.export(inputs)
        self.assertEqual(next(x for x in rows if x["experiment"] == "R")["verdict"], "INCONCLUSIVE")

    def test_mreg_invalid_cells(self):
        inputs = export_inputs()
        inputs["mreg"]["result"]["Mreg-bad"] = {"verdict": "INVALID", "invalid_observations": ["Mreg-bad-cand-3: import_starved=True"]}
        inputs["mreg"]["result"]["Mreg-x"]["verdict"] = "INVALID"
        rows, excluded, _ = self.export(inputs)
        bad = next(r for r in rows if r["scenario"] == "Mreg-bad")
        self.assertEqual((bad["verdict"], bad["category"], bad["status"]), ("INVALID", "decisive", "failed"))
        self.assertIn("import_starved=True", bad["status_reason"])
        self.assert_unmeasured(bad)
        self.assertNotIn("Mreg-bad", [e["id"] for e in excluded])
        self.assertEqual({(r["verdict"], r["status"]) for r in rows if r["scenario"] == "Mreg-x"}, {("INVALID", "completed")})

    def test_q_nonconforming_and_failed_criteria(self):
        inputs = export_inputs()
        q = inputs["q"]
        q.update(q_status="NONCONFORMING", run_cause="cap")
        q["criteria"]["Q4"].update(status=None, missing_observations=["candidate L2 G100k C=64: 2 of 3 observations"])
        q["criteria"]["Q1"].update(status="FAIL", marker_p99_ms=None, marker_max_ms=None,
                                   failed_observations=["candidate L1 G100k C=16: run exit 101 (product)"])
        q["criteria"]["Q5"].update(status=None, missing_observations=["reference L1 G100k C=64: 1 of 3 observations"])
        q["criteria"]["Q5"]["cells"]["L1 G100k C=64"] = {"pass": False, "reason": "a median is missing"}
        rows, _, _ = self.export(inputs)
        q4 = next(r for r in rows if r.get("criterion") == "Q4")
        self.assertEqual((q4["verdict"], q4["status"], q4["category"]), (None, "nonconforming", "decisive"))
        self.assertIn("2 of 3 observations", q4["status_reason"])
        self.assert_unmeasured(q4)
        q1 = [r for r in rows if r.get("criterion") == "Q1"]
        self.assertEqual({(r["verdict"], r["status"]) for r in q1}, {("FAIL", "failed")})
        self.assertIn("exit 101", q1[0]["status_reason"])
        for r in q1:
            self.assert_unmeasured(r)
        q5 = [r for r in rows if r.get("criterion") == "Q5"]
        self.assertEqual(len(q5), 4)
        self.assertEqual({(r["verdict"], r["status"]) for r in q5}, {(None, "nonconforming")})

    def test_q_inconsistent_inputs_fail_closed(self):
        import export_v100q_site as ex
        inputs = export_inputs()
        inputs["q"]["criteria"]["Q4"]["status"] = None  # no verdict although block Q is COMPLETE
        with self.assertRaisesRegex(ex.ExportError, "no verdict"):
            ex.build(inputs, self.URLS, "env")
        inputs = export_inputs()
        inputs["q"]["criteria"]["Q4"]["secs_to_ready_c64"] = None  # PASS without a value
        with self.assertRaisesRegex(ex.ExportError, "without a value"):
            ex.build(inputs, self.URLS, "env")

    def test_deciding_rule_verdicts_are_published(self):
        """N3: C2 FAIL, Q2 FAIL, an M_reg INVALID cell and an Rmem zero reference are site rows."""
        inputs = export_inputs()
        next(r for r in inputs["bc_report"]["rows"] if r["id"] == "C-heap-lifecycle-x:C2")["status"] = "FAIL"
        inputs["q"]["criteria"]["Q2"].update(status="FAIL", failed_observations=["candidate L1 G100k C=16 round 2: lag over 3 s"])
        inputs["mreg"]["result"]["Mreg-bad"] = {"verdict": "INVALID", "invalid_observations": ["Mreg-bad-ref-1: errors 3"]}
        inputs["rmem"]["Rmem-import-core-20-10"]["metrics"]["live_after"].update(cand=64, verdict="REGRESSION")
        rows, excluded, _ = self.export(inputs)
        c2 = next(r for r in rows if r["scenario"] == "C-heap-lifecycle-x C2 (rule at every checkpoint)")
        self.assertEqual((c2["verdict"], c2["category"], c2["status"]), ("FAIL", "decisive", "completed"))
        q2 = next(r for r in rows if r.get("criterion") == "Q2")
        self.assertEqual((q2["verdict"], q2["category"], q2["status"], q2["reference_kind"]),
                         ("FAIL", "decisive", "completed", "threshold"))
        self.assertIn("lag over 3 s", q2["estimate_unavailable_reason"])
        bad = next(r for r in rows if r["scenario"] == "Mreg-bad")
        self.assertEqual((bad["verdict"], bad["status"]), ("INVALID", "failed"))
        live = next(r for r in rows if r["experiment"] == "Rmem" and r["metric"] == "live_after")
        self.assertEqual((live["verdict"], live["category"], live["status"], live["candidate"], live["reference"]),
                         ("REGRESSION", "decisive", "completed", 64, 0))
        self.assertIsNone(live.get("delta_pct"))
        self.assertIn("zero", live["estimate_unavailable_reason"])
        for r in (c2, q2):
            self.assertFalse([k for k in ("delta_pct", "delta_ci95", "candidate", "reference") if r.get(k) is not None])
        ids = {e["id"] for e in excluded}
        self.assertFalse(ids & {"C-heap-lifecycle-x:C2", "Q2", "Mreg-bad", "Rmem-import-core-20-10:live_after"})

    def test_core_rule_rows_and_unknown_kinds(self):
        import export_v100q_site as ex
        inputs = export_inputs()
        inputs["bc_report"]["rows"] += [{"id": "B5-x", "kind": "B5", "role": "deciding", "status": "FAIL"},
                                        {"id": "T5-P_max-hub", "kind": "T5", "role": "deciding", "status": "INVALID",
                                         "reason": "no build record"}]
        rows, _, _ = self.export(inputs)
        b5 = next(r for r in rows if r["scenario"] == "B5-x")
        self.assertEqual((b5["verdict"], b5["status"]), ("FAIL", "completed"))
        t5 = next(r for r in rows if r["scenario"] == "T5-P_max-hub")
        self.assertEqual((t5["verdict"], t5["status"]), ("INVALID", "failed"))
        inputs["bc_report"]["rows"].append({"id": "Z", "kind": "Z9", "role": "deciding", "status": "PASS"})
        with self.assertRaisesRegex(ex.ExportError, "unknown B/C row kind"):
            ex.build(inputs, self.URLS, "env")

    def test_not_run_rows(self):
        import export_v100q_site as ex
        inputs = export_inputs()
        inputs["not_run"] = [{"experiment": "R", "scenario": "R-core-churn-x", "metric": "observation_ns",
                              "reason": "R stopped after the product failure of R-core-import-y (plan section 5.5)"}]
        rows, _, _ = self.export(inputs)
        nr = next(r for r in rows if r["scenario"] == "R-core-churn-x")
        self.assertEqual((nr["verdict"], nr["category"], nr["status"]), ("NOT_RUN", "decisive", "not_run"))
        self.assert_unmeasured(nr)
        for bad, message in (({"reason": ""}, "needs a reason"), ({"reason": None}, "needs a reason"),
                             ({"scenario": "R-core-import-sparse-10k-20-10"}, "classified"),
                             ({"category": "optional"}, "unknown category"), ({"metric": " "}, "metric is required")):
            entry = dict(inputs["not_run"][0], **bad)
            with self.subTest(bad), self.assertRaisesRegex(ex.ExportError, message):
                ex.build(dict(inputs, not_run=[entry]), self.URLS, "env")

    def test_unknown_classes_still_fail_closed(self):
        import export_v100q_site as ex
        with self.assertRaisesRegex(ex.ExportError, "PASS_ISH"):
            ex.build(export_inputs("PASS_ISH"), self.URLS, "env")
        inputs = export_inputs()
        inputs["bc_report"]["rows"][0]["status"] = "TIMER_LIMITED?"
        with self.assertRaisesRegex(ex.ExportError, "TIMER_LIMITED"):
            ex.build(inputs, self.URLS, "env")
        inputs = export_inputs()
        inputs["r"]["R-core-import-sparse-10k-20-10"]["verdict"] = "PASS (FASTER)"
        with self.assertRaisesRegex(ex.ExportError, "PASS \\(FASTER\\)"):
            ex.build(inputs, self.URLS, "env")
        inputs = export_inputs()
        inputs["mreg"]["result"]["Mreg-bad"] = {"verdict": "PASS"}  # no metrics, yet not INVALID
        with self.assertRaisesRegex(ex.ExportError, "impossible"):
            ex.build(inputs, self.URLS, "env")
        inputs = export_inputs()
        inputs["bc_report"]["rows"][0]["role"] = "advisory"
        with self.assertRaisesRegex(ex.ExportError, "unknown B4 role"):
            ex.build(inputs, self.URLS, "env")

    def test_cli_never_publishes(self):
        import export_v100q_site as ex
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            paths = {}
            for key, value in export_inputs().items():
                paths[key] = root / f"{key}.json"
                paths[key].write_text(json.dumps(value))
            decision = root / "DECISION.md"
            base = ["--freeze", str(paths["freeze"]), "--a", str(paths["a"]), "--bc", str(paths["bc"]),
                    "--bc-report", str(paths["bc_report"]), "--r", str(paths["r"]), "--rmem", str(paths["rmem"]),
                    "--mreg", str(paths["mreg"]), "--q", str(paths["q"]), "--campaign-url", self.URLS["campaign"],
                    "--evidence-url", self.URLS["evidence"], "--environment", "env",
                    "--releases", str(ROOT / "docs/data/releases.json"), "--decision", str(decision)]
            out = ["--out", str(root / "releases.json"), "--report-only", str(root / "excluded.json")]
            not_run = root / "not_run.json"
            not_run.write_text(json.dumps({"not_run": [{"experiment": "R", "scenario": "R-core-churn-x",
                                                        "metric": "observation_ns", "reason": "chain stopped"}]}))
            with mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": ""}), self.assertRaisesRegex(SystemExit, "outside the allowed roots"):
                ex.main(base + out)  # paths outside the allowed roots are refused
            roots = mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d})
            roots.start()
            self.addCleanup(roots.stop)
            with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
                ex.main(base + out)  # no decision record yet
            decision.write_text("# decision\n")
            with self.assertRaises(SystemExit), mock.patch("sys.stderr"):
                ex.main(base + ["--out", str(ROOT / "docs/data/x.json"), "--report-only", str(root / "e.json")])
            before = (ROOT / "docs/data/releases.json").read_bytes()
            with mock.patch("sys.stdout"):
                self.assertEqual(ex.main(base + out + ["--not-run", str(not_run)]), 0)
            self.assertEqual((ROOT / "docs/data/releases.json").read_bytes(), before)
            data = json.loads((root / "releases.json").read_text())
        entry = next(r for r in data["releases"] if r["version"] == "1.0.0")
        self.assertEqual(entry["status"], "published")
        self.assertEqual((data["schema_version"], entry["schema_version"]), (2, 2))
        self.assertIn("R-core-churn-x", [r["scenario"] for r in entry["comparisons"][0]["results"]])
        self.assertEqual(json.loads(before)["releases"][0]["status"], "planned")


if __name__ == "__main__":
    unittest.main()
