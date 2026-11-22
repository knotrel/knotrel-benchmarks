"""Tests for the v0.9.0 qualification tooling (results/v0.9.0-qualification).

They pin that the v0.9.0 campaign re-runs the v0.7.0 qualification-3 method unchanged: the
matrix differs from q3's only where the protocol says; the wrappers bind this matrix and
change nothing else; the runner's Part 1 sequence is q3's with only the declared bindings
changed; the launch-environment check uses the runner's arguments; and the new pieces (T5 arm-B
probe revision, Part 2 comparison, Part 3 evaluation) check what they claim.
"""

import copy
import hashlib
import json
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_v070q3_autonomous as q3runner  # noqa: E402
import run_v090q_autonomous as runner  # noqa: E402

V090 = ROOT / "results" / "v0.9.0-qualification"
Q3 = ROOT / "results" / "v0.7.0-qualification-3"
MATRIX = json.loads((V090 / "MATRIX.json").read_text())
Q3_MATRIX = json.loads((Q3 / "MATRIX.json").read_text())
ENV = (V090 / "launch_env_check.sh").read_text()
PREPARE = (V090 / "prepare_campaign.sh").read_text()
CAND = "e827b2a7bb1930b70e75ed7ccff2ac0201db9e40"


class MatrixTest(unittest.TestCase):
    def test_experiments_and_rules_are_q3s_except_t5_arms(self):
        self.assertEqual(MATRIX["rules"], Q3_MATRIX["rules"])
        mine, theirs = copy.deepcopy(MATRIX["experiments"]), copy.deepcopy(Q3_MATRIX["experiments"])
        for m in (mine, theirs):
            m["T5"].pop("arms")
            m["T5"].pop("question")
        self.assertEqual(mine, theirs)
        for key in ("host_conditions", "invalidation", "resource_ceilings", "analysis"):
            self.assertEqual(MATRIX[key], Q3_MATRIX[key], key)

    def test_conformance_policy_unchanged_attempts_one_plus_one(self):
        mine, theirs = MATRIX["conformance"], Q3_MATRIX["conformance"]
        self.assertEqual({k: v for k, v in mine.items() if k != "qualification_3"},
                         {k: v for k, v in theirs.items() if k != "qualification_3"})
        self.assertEqual(mine["qualification_3"]["revision_3"], theirs["qualification_3"]["revision_3"])
        self.assertEqual(mine["qualification_3"]["attempts_cap"], 2)
        self.assertEqual(MATRIX["budget"]["final_cap_minutes"], 105)

    def test_window_multipliers_are_q3s(self):
        self.assertEqual((V090 / "window-multipliers-q3.json").read_bytes(),
                         (Q3 / "window-multipliers-q3.json").read_bytes())

    def test_references_name_the_builds(self):
        refs = json.dumps(MATRIX["references"])
        for sha in (CAND, "9f933a783b043f9f44fd5de014c3c8a93c7922c3", "e3fc7361caf2f29dcf6870e8018b96414ebd927b"):
            self.assertIn(sha, refs)
        for sha in (CAND, "9f933a783b043f9f44fd5de014c3c8a93c7922c3", "e3fc7361caf2f29dcf6870e8018b96414ebd927b",
                    "7116c32e7c3351a995048713032745117fc7df7b", "e843aae2fd6d74a03b834dfe84f9367d7bc897a3"):
            self.assertIn(sha, PREPARE if sha != CAND else PREPARE + CAND)


class BindingTest(unittest.TestCase):
    def test_collector_binds_this_matrix(self):
        import run_v090q_collect as collect
        import run_v070r_collect as base
        self.assertEqual(collect.MATRIX, V090 / "MATRIX.json")
        self.assertEqual(base.MATRIX, V090 / "MATRIX.json")

    def test_report_binds_this_matrix(self):
        import report_v090q_bc as report
        self.assertEqual(report.frozen.MATRIX, V090 / "MATRIX.json")

    def test_analysis_binds_this_matrix(self):
        import analyze_v090q as analysis
        self.assertEqual(analysis.MATRIX, V090 / "MATRIX.json")


class RunnerTest(unittest.TestCase):
    def sequence(self, cls, camp):
        calls = []
        r = cls(camp, CAND)
        r.run_step = lambda name, argv, block, dirs=(): calls.append((name, argv))
        r.analysis = lambda name, argv: calls.append((name, argv))
        (r.camp / "A").mkdir(parents=True, exist_ok=True)
        (r.camp / "A" / "decision-analysis-main.json").write_text(json.dumps({"extension_cells_required": ["x"]}))
        r.sequence()
        return r, calls

    def test_part1_is_q3_with_declared_bindings(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            _, mine = self.sequence(runner.Part1Runner, camp)
            _, theirs = self.sequence(q3runner.Runner, camp)
        self.assertEqual([n for n, _ in mine], [n for n, _ in theirs])
        swap = {"scripts/run_v070q3_collect.py": "scripts/run_v090q_collect.py",
                "v0.7.0-Qualification3-A-Extension": "v0.9.0-Qualification-A-Extension",
                "results/v0.7.0-qualification-3/window-multipliers-q3.json":
                    "results/v0.9.0-qualification/window-multipliers-q3.json"}
        for (name, a), (_, b) in zip(mine, theirs):
            b = [swap.get(x, x) for x in b]
            b = [x.replace("/t1base-probes/", "/t5base-probes/") for x in b]
            self.assertEqual(a, b, name)

    def test_part2_sequence(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            r, calls = self.sequence(runner.Part2Runner, camp)
        self.assertEqual([n for n, _ in calls], ["BC", "Mreg"])
        bc, mreg = calls[0][1], calls[1][1]
        self.assertEqual(bc[bc.index("--only") + 1], "B4")
        self.assertTrue(bc[bc.index("--http") + 1].endswith("v080-probes/release/http-lifecycle"))
        self.assertTrue(bc[bc.index("--out") + 1].endswith("part2/BC"))
        self.assertTrue(mreg[mreg.index("--ref") + 1].endswith("v080-server/release/knotrel-server"))
        self.assertTrue(mreg[mreg.index("--cand") + 1].endswith("cand-server/release/knotrel-server"))
        self.assertEqual(r.limits["budget_s"], 20 * 60.0)
        self.assertEqual(q3runner.LIMITS["budget_s"], 105 * 60.0)

    def test_import_leaves_q3_runner_unchanged(self):
        self.assertEqual(q3runner.Q3, "results/v0.7.0-qualification-3")
        self.assertEqual(q3runner.OUTPUTS[0], "A/raw-main")

    def test_records_use_this_directory_and_part_outputs(self):
        seen = {}

        def fake(self_):
            seen["q3"], seen["outputs"] = q3runner.Q3, q3runner.OUTPUTS

        with tempfile.TemporaryDirectory() as d, mock.patch.object(q3runner.Runner, "write_records", fake):
            runner.Part2Runner(Path(d), CAND).write_records()
        self.assertEqual(seen, {"q3": "results/v0.9.0-qualification", "outputs": ("BC", "Mreg", "gate")})
        self.assertEqual(q3runner.Q3, "results/v0.7.0-qualification-3")

    def test_part2_bc_passes_the_interference_duplicate_check(self):
        import run_lifecycle_qualification as lifecycle
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            _, calls = self.sequence(runner.Part2Runner, camp)
            argv = calls[0][1][3:]
            for flag in ("--core", "--core-count", "--http"):
                path = Path(argv[argv.index(flag) + 1])
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("")
            self.assertNotEqual(argv[argv.index("--core") + 1], argv[argv.index("--core-count") + 1])
            binaries = {name: str(Path(argv[argv.index(flag) + 1]).resolve()) for name, flag in
                        (("core", "--core"), ("core-count", "--core-count"), ("http", "--http"))}
            seen = set()
            for cell in lifecycle.matrix("final", "compact-bfs", True):
                key = (binaries[cell["binary"]], *map(str, cell["args"]))
                self.assertNotIn(key, seen, cell["id"])
                seen.add(key)

    def test_part2_refuses_without_conforming_part1(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            (camp / "logs").mkdir(parents=True)
            (camp / "logs" / "CONFORMANCE.txt").write_text("BUDGET EXHAUSTED: x\n")
            with self.assertRaises(runner.Stop):
                runner.Part2Runner(camp, CAND).preflight()

    def test_preflight_requires_this_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            bench = camp / "src" / "cand" / "knotrel-benchmarks" / "results" / "v0.9.0-qualification"
            bench.mkdir(parents=True)
            for freeze in ({"revision": 3, "campaign": "v0.7.0 qualification 3"},
                           {"revision": 1, "campaign": "v0.9.0 qualification", "candidate": {"commit": "0" * 40}}):
                (bench / "FREEZE.json").write_text(json.dumps(freeze))
                with self.assertRaises(runner.Stop) as stop:
                    runner.Part1Runner(camp, CAND).preflight()
                self.assertEqual(stop.exception.status, "NOT STARTED")

    def test_env_check_dry_runs_match_runner(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / f"v0.9.0-qualification-{CAND[:7]}-attempt1"
            _, part1 = self.sequence(runner.Part1Runner, camp)
        steps = {n: a for n, a in part1}
        for line in ENV.splitlines():
            if line.startswith("run BC "):
                words = shlex.split(line.replace("$WM", "results/v0.9.0-qualification/window-multipliers-q3.json"))
                env_bc = [w for w in words[3:] if w != "--dry-run"]
                runner_bc = steps["BC"][1:]
                self.assertEqual(env_bc[0:2], runner_bc[0:2])
                flags = lambda ws: [w for w in ws if w.startswith("--")]  # noqa: E731
                self.assertEqual(flags(env_bc), flags(runner_bc))


class T5Test(unittest.TestCase):
    def test_probe_source_equal(self):
        import analyze_v090q_t5 as t5
        t5.probe_source_equal(ROOT, "7116c32e7c3351a995048713032745117fc7df7b",
                              "e843aae2fd6d74a03b834dfe84f9367d7bc897a3")
        older = subprocess.run(["git", "-C", str(ROOT), "log", "-1", "--format=%H", "7116c32e", "--",
                                "tools/lifecycle-probes/src"], capture_output=True, text=True, check=True).stdout.strip()
        with self.assertRaises(t5.frozen.Invalid):
            t5.probe_source_equal(ROOT, f"{older}~1", "7116c32e7c3351a995048713032745117fc7df7b")


class Part3Test(unittest.TestCase):
    def summary(self, rps, p99, q):
        cells = {f"L1 G100k C={c}": {"query_rps": {"median": rps}, "query_p99_ms": {"median": p99}} for c in (16, 64)}
        return {"measurement_secs": 1.0, "summary": {"cells": cells, "criteria": {
            k: {"pass": v} for k, v in q.items()}}}

    def run_eval(self, cand, base):
        import evaluate_v090q_part3 as ev
        with tempfile.TemporaryDirectory() as d:
            c, b = Path(d) / "c.json", Path(d) / "b.json"
            c.write_text(json.dumps(cand))
            b.write_text(json.dumps(base))
            with mock.patch.object(ev, "BASELINE_SHA256", hashlib.sha256(b.read_bytes()).hexdigest()), \
                    mock.patch("sys.stdout") as out:
                ev.main(["x", str(c), str(b)])
            return json.loads("".join(call.args[0] for call in out.write.call_args_list))

    def test_q5_and_deciding(self):
        q = {"Q1": True, "Q2": True, "Q3": False, "Q4": True}
        base = self.summary(1000.0, 100.0, q)
        ok = self.run_eval(self.summary(901.0, 124.0, q), base)
        self.assertTrue(ok["part3_pass"])
        self.assertEqual(ok["Q3"]["status"], "FAIL")
        slow = self.run_eval(self.summary(899.0, 100.0, q), base)
        self.assertFalse(slow["criteria"]["Q5"]["pass"])
        self.assertFalse(slow["part3_pass"])
        q2 = dict(q, Q2=False)
        self.assertFalse(self.run_eval(self.summary(1000.0, 100.0, q2), base)["part3_pass"])

    def test_baseline_hash_checked(self):
        import evaluate_v090q_part3 as ev
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "b.json"
            b.write_text("{}")
            with self.assertRaises(SystemExit):
                ev.main(["x", str(b), str(b)])


if __name__ == "__main__":
    unittest.main()
