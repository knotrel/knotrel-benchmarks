"""Tests of the CF5 matrix, runner and analyzer (scripts/cf5_matrix.py, run_cf5.py,
analyze_cf5.py)."""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
# Command-line paths are confined (cli_paths); the temporary directories are granted here.
os.environ["LIFECYCLE_QUALIFICATION_ROOTS"] = os.pathsep.join(
    filter(None, [os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS"), tempfile.gettempdir()]))
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
trace = args[args.index("--trace") + 1] if "--trace" in args else "x"
print(json.dumps({"kind": "pair", "t_ns": value, "ok": engine != "bad", "trace": trace}))
"""


def tiny_matrix(cf_engine="cf", ref_engine="ref", rule="two_sided", tier=2, check=None):
    def arm(engine):
        return {"tool": "fake", "args": ["--engine", engine], "line": "kind=pair"}
    cell = {"id": "C1", "block": "K1", "tier": tier, "kind": "paired", "family": "F",
            "role": "primary", "reference": "ref", "rule": rule, "arms": {"cf": arm(cf_engine), "ref": arm(ref_engine)},
            "metrics": [{"name": "t_ns", "path": "t_ns", "margin": 0.10, "margin_kind": "time",
                         "direction": "lower_is_better",
                         "measurement": {"category": "aggregate", "intervals": 1,
                                         "limit_ns": 57.7}}]}
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
        # A clean candidate checkout and a freeze record: a non-preparatory session refuses
        # to start without them.
        import subprocess
        self.cand = self.dir / "cand"
        self.cand.mkdir()
        git = ["git", "-C", str(self.cand), "-c", "user.name=t", "-c", "user.email=t@t"]
        subprocess.run(git[:3] + ["init", "-q"], check=True)
        subprocess.run(git + ["commit", "-q", "--allow-empty", "-m", "c"], check=True)
        self.cand_sha = subprocess.run(git[:3] + ["rev-parse", "HEAD"], capture_output=True,
                                       text=True, check=True).stdout.strip()
        self.freeze = self.dir / "FREEZE.json"
        self.write_tools()

    def write_tools(self, **extra):
        tools = {"fake": [sys.executable, str(self.dir / "fake.py")],
                 "_checkouts": {"candidate": str(self.cand)}, "_freeze": str(self.freeze)}
        tools.update(extra)
        self.tools.write_text(json.dumps(tools))

    def freeze_matrix(self, path, candidate=None):
        self.freeze.write_text(json.dumps({
            "candidate": candidate or self.cand_sha,
            "matrix_sha256": run_cf5.sha256_bytes(path.read_bytes())}))

    def run_matrix(self, matrix, out, *extra):
        path = self.dir / f"m-{out}.json"
        path.write_text(json.dumps(matrix))
        self.freeze_matrix(path)
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
        # A complete session 1 leaves nothing to complete: no second session at all.
        code, path = self.run_matrix(tiny_matrix(), "c1")
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                          str(self.dir / "c2"), "--session", "2",
                          "--resume-from", str(self.dir / "c1")])
        self.assertFalse((self.dir / "c2").exists())

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


# -- S3 (run_cf5_s3.py) --------------------------------------------------------------------------
class S3Tool:
    """Stands in for the load tool; the side comes from LOAD_ENGINE, as in the real rebinding."""

    def __init__(self, values=None, fail=None, wrong_engine=None):
        self.calls, self.values, self.fail = [], values or {}, fail or {}
        self.wrong_engine = wrong_engine

    def __call__(self, argv, env, step_dir, timeout_s):
        import evaluate_v100q_q as ev
        from test_v100q import q_record
        engine = env["LOAD_ENGINE"]
        self.calls.append({"step": step_dir.name, "engine": engine, "bin": env["KNOTREL_BIN"],
                           "cells": env["LOAD_CELLS"].split(",")})
        records, code = [], 0
        for cell in env["LOAD_CELLS"].split(","):
            if (step_dir.name, cell) in self.fail:
                (step_dir / "load.stderr").write_text(self.fail[(step_dir.name, cell)])
                code = 101
                break
            record = q_record(cell, **self.values.get((engine, cell), {}))
            record["engine"] = engine
            record["server_engine"] = self.wrong_engine if self.wrong_engine and \
                step_dir.name == "round2-candidate" else engine
            records.append(record)
        with open(step_dir / "results.jsonl", "w") as handle:
            for r in records:
                handle.write(json.dumps(r) + "\n")
        if code == 0:
            summary = ev.tool_evaluate([ev.flatten(r) for r in records])
            (step_dir / "summary.json").write_text(json.dumps({"measurement_secs": 1.0,
                                                               "summary": summary}))
        return code


class S3Test(unittest.TestCase):
    def run_s3(self, root: Path, tool) -> int:
        import os
        from unittest import mock
        import run_cf5_s3
        camp = root / "camp"
        for p in ("cand-server/release/knotrel-server", "feeder/release/knotrel-pg-feeder",
                  "feeder/release/examples/load"):
            (camp / "targets" / p).parent.mkdir(parents=True, exist_ok=True)
            (camp / "targets" / p).write_text("x")
        runner = run_cf5_s3.S3Runner(camp, root / "S3", launch=tool,
                                     state=lambda _o: {"free_bytes": 10 ** 11})
        with mock.patch.dict(os.environ, {"KNOTREL_PG_ADMIN_URL": "postgres://x",
                                          "LOAD_ENGINE": "hdt"}), mock.patch("sys.stdout"):
            return runner.run()

    def test_sides_share_the_candidate_server_and_differ_by_engine(self):
        import run_v100q_q as q
        tool = S3Tool()
        with tempfile.TemporaryDirectory() as d:
            code = self.run_s3(Path(d), tool)
            run = json.loads((Path(d) / "S3" / "run.json").read_text())
            import run_cf5_s3
            result = run_cf5_s3.evaluate(Path(d) / "S3")
        self.assertEqual(code, 0)
        self.assertEqual(run["cf5_block"], "S3")
        self.assertEqual(run["cap_s"], 90 * 60.0)
        self.assertNotIn("ref-server", run["binaries"])
        self.assertEqual([c["step"] for c in tool.calls],
                         ["round1-candidate", "round1-reference", "round2-reference",
                          "round2-candidate", "round3-candidate", "round3-reference"])
        for call in tool.calls:
            self.assertTrue(call["bin"].endswith("cand-server/release/knotrel-server"))
            self.assertEqual(tuple(call["cells"]), q.CANDIDATE_CELLS)
            self.assertEqual(call["engine"], "cluster-forest" if call["step"].endswith("candidate")
                             else "compact-bfs")
        # The v1.0.0 runner itself is unchanged by the rebinding.
        self.assertEqual(q.QRunner.SIDES["reference"], ("ref-server", q.REFERENCE_CELLS))
        self.assertEqual(len(result["comparisons"]), 7)
        self.assertEqual({c["status"] for c in result["comparisons"].values()}, {"PASS"})

    def test_q5_style_thresholds_against_compact_bfs(self):
        values = {("cluster-forest", "L1 G100k C=16"): {"rps": 899.0},
                  ("cluster-forest", "L1 G100k C=64"): {"p99": 126.0},
                  ("cluster-forest", "L1 G10k C=16"): {"rps": 900.0, "p99": 125.0}}
        with tempfile.TemporaryDirectory() as d:
            self.run_s3(Path(d), S3Tool(values=values))
            import run_cf5_s3
            result = run_cf5_s3.evaluate(Path(d) / "S3")["comparisons"]
        self.assertEqual(result["Q5-style L1 G100k C=16"]["status"], "FAIL")
        self.assertEqual(result["Q5-style L1 G100k C=64"]["status"], "FAIL")
        self.assertEqual(result["Q5-style L1 G10k C=16"]["status"], "PASS")

    def test_engine_mismatch_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            self.run_s3(Path(d), S3Tool(wrong_engine="compact-bfs"))
            import run_cf5_s3
            with self.assertRaises(SystemExit) as raised:
                run_cf5_s3.evaluate(Path(d) / "S3")
        self.assertIn("engine mismatch", str(raised.exception))

    def test_a_product_failure_fails_its_comparisons_never_passes(self):
        fail = {("round2-reference", "L1 G100k C=16"): "thread 'main' panicked in knotrel-server"}
        with tempfile.TemporaryDirectory() as d:
            self.run_s3(Path(d), S3Tool(fail=fail))
            import run_cf5_s3
            result = run_cf5_s3.evaluate(Path(d) / "S3")["comparisons"]
        self.assertEqual(result["Q5-style L1 G100k C=16"]["status"], "FAIL")
        self.assertEqual(result["Q1"]["status"], "PASS")  # Q1 reads the CF side only


class DelegatedTest(unittest.TestCase):
    def test_unset_required_environment_stops_before_the_record(self):
        import os
        from unittest import mock
        steps = [{"cell": "S3", "kind": "delegated"}, {"cell": "V1", "kind": "delegated"}]
        tools = {"_delegated": {"S3": {"argv": ["true"], "requires_env": ["KNOTREL_PG_ADMIN_URL"]},
                                "V1": {"argv": ["true"]}}}
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(run_cf5.missing_delegated_env(steps, tools),
                             ["S3: KNOTREL_PG_ADMIN_URL"])
        with mock.patch.dict(os.environ, {"KNOTREL_PG_ADMIN_URL": "postgres://x"}):
            self.assertEqual(run_cf5.missing_delegated_env(steps, tools), [])

    def test_delegated_collector_files_are_hashed(self):
        with tempfile.TemporaryDirectory() as d:
            script = Path(d) / "V1.sh"
            script.write_text("echo one\n")
            tools = {"_delegated": {"V1": {"argv": ["/bin/sh", str(script)]},
                                    "L2": {"argv": ["python3", "rel.py"], "cwd": d}}}
            (Path(d) / "rel.py").write_text("x")
            first = run_cf5.provenance(tools)["delegated"]
            script.write_text("echo two\n")
            second = run_cf5.provenance(tools)["delegated"]
        self.assertIn(str(script), first["V1"])
        self.assertIn("rel.py", first["L2"])
        self.assertNotEqual(first["V1"][str(script)], second["V1"][str(script)])

    def test_delegated_collector_receives_its_environment(self):
        # Regression: the L2 collector needs LIFECYCLE_QUALIFICATION_ROOTS (path confinement);
        # without it the collector refuses its --out and the cell is DELEGATED_FAILED.
        with tempfile.TemporaryDirectory() as d:
            tools = {"_delegated": {"L2": {
                "argv": [sys.executable, "-c",
                         "import os, sys; sys.exit(0 if os.environ.get('ROOTS_X') == 'ok' else 4)"],
                "env": {"ROOTS_X": "ok"}}}}
            state = run_cf5.run_delegated({"id": "L2"}, tools, Path(d))
            tools["_delegated"]["L2"].pop("env")
            with self.assertRaises(run_cf5.GateFailure):
                run_cf5.run_delegated({"id": "L2"}, tools, Path(d))
        self.assertEqual(state["state"], "DELEGATED_DONE")

def limit_cell(limit, kind="time", rule="two_sided", name="latency_ns.p99"):
    margin = {"time": 0.10, "tail": 0.25}[kind]
    return {"id": "X", "rule": rule, "metrics": [
        {"name": name, "margin_kind": kind, "margin": margin, "direction": "lower_is_better",
         "measurement": {"category": "aggregate", "limit_ns": limit}}]}


def spread_pairs(cf_values, ref, name="latency_ns.p99"):
    return [{"cf": {"metrics": {name: v}}, "ref": {"metrics": {name: ref}}} for v in cf_values]


class MeasurementLimitTest(unittest.TestCase):
    """Plan section 6.1 (revision 5): TIMER_LIMITED from the measured limit and the margin."""

    def test_median_at_most_twice_the_limit_is_timer_limited_with_values_kept(self):
        pairs = spread_pairs([100.0] * 24, 120.0)
        result = an.classify_paired(limit_cell(57.7), pairs)["latency_ns.p99"]
        self.assertEqual(result["class"], "TIMER_LIMITED")
        self.assertEqual((result["cf_median"], result["ref_median"]), (100.0, 120.0))
        self.assertNotIn("interval_log", result)

    def test_small_limit_keeps_the_plan_class_away_from_the_margin(self):
        pairs = spread_pairs([1.0e6 * (1.0 + 0.0009 * i) for i in range(24)], 1.0e6)
        result = an.classify_paired(limit_cell(57.7), pairs)["latency_ns.p99"]
        self.assertEqual(result["class"], "EQUIVALENT")
        self.assertNotIn("class_without_limit", result)

    def test_small_limit_still_blocks_equivalence_at_the_margin(self):
        # Review of revision 5: a limit below a tenth of the margin was exempt; now any limit
        # that moves the class prevents it. Upper bound just inside ln(1.1), delta ~ 1.2e-4.
        edge = math.exp(math.log(1.1) - 5e-5)
        values = [1.0e6] * 6 + [1.0e6 * edge] * 12 + [1.2e6] * 6
        result = an.classify_paired(limit_cell(57.7), spread_pairs(values, 1.0e6))
        self.assertEqual(result["latency_ns.p99"]["class"], "TIMER_LIMITED")
        self.assertEqual(result["latency_ns.p99"]["class_without_limit"], "EQUIVALENT")

    def test_small_limit_still_blocks_pass_at_the_margin(self):
        edge = math.exp(math.log(1.1) - 5e-5)
        values = [1.0e6] * 6 + [1.0e6 * edge] * 12 + [1.2e6] * 6
        result = an.classify_paired(limit_cell(57.7, rule="regression"),
                                    spread_pairs(values, 1.0e6))
        self.assertEqual(result["latency_ns.p99"]["class"], "TIMER_LIMITED")
        self.assertEqual(result["latency_ns.p99"]["class_without_limit"], "PASS")

    def test_unquantified_effects_are_reported_per_metric(self):
        cell = limit_cell(57.7)
        cell["metrics"][0]["measurement"]["category"] = "instrumented_aggregate"
        result = an.classify_paired(cell, spread_pairs([1e6] * 24, 1e6))["latency_ns.p99"]
        self.assertTrue(any("overlap" in e for e in result["not_in_limit"]))
        self.assertTrue(any("not guaranteed" in e for e in result["not_in_limit"]))

    def test_equivalence_inside_the_limit_is_timer_limited_never_equivalent(self):
        # limit 4 us on 100 us arms: delta ~ 0.08 > 0.0095; [lo, hi] inside +-ln(1.1) but
        # the widened interval is not: TIMER_LIMITED, the unwidened class only reported.
        pairs = spread_pairs([100_000.0 * (1.0 + 0.002 * i) for i in range(24)], 100_000.0)
        result = an.classify_paired(limit_cell(4_000.0), pairs)["latency_ns.p99"]
        self.assertEqual(result["class"], "TIMER_LIMITED")
        self.assertEqual(result["class_without_limit"], "EQUIVALENT")

    def test_difference_beyond_the_limit_keeps_its_class(self):
        pairs = spread_pairs([40_000.0 + 10.0 * i for i in range(24)], 100_000.0)
        result = an.classify_paired(limit_cell(2_000.0), pairs)["latency_ns.p99"]
        self.assertGreater(result["limit_log"], 0.1 * math.log(1.1))
        self.assertEqual(result["class"], "FASTER")

    def test_regression_rule_never_passes_inside_the_limit(self):
        pairs = spread_pairs([100_000.0 * (1.0 + 0.003 * i) for i in range(24)], 100_000.0)
        result = an.classify_paired(limit_cell(4_000.0, rule="regression"), pairs)
        self.assertEqual(result["latency_ns.p99"]["class"], "TIMER_LIMITED")
        self.assertEqual(result["latency_ns.p99"]["class_without_limit"], "PASS")

    def test_time_metric_without_a_limit_is_refused(self):
        cell = limit_cell(1.0)
        cell["metrics"][0].pop("measurement")
        with self.assertRaises(SystemExit):
            an.classify_paired(cell, spread_pairs([1e6] * 24, 1e6))

    def test_matrix_limits_follow_the_calibration(self):
        m = cf5_matrix
        tick, read = m.TICK_NS, m.CLOCK_READ_NS
        cells = {c["id"]: c for c in m.build()["cells"]}
        for cell in cells.values():
            for metric in cell.get("metrics", []):
                if metric["margin_kind"] in ("time", "tail"):
                    self.assertGreater(metric["measurement"]["limit_ns"], 0, cell["id"])
        k1 = cells["K1-chain-split-rejoin-v1-10000-vs-hdt"]["metrics"][0]["measurement"]
        self.assertAlmostEqual(k1["limit_ns"], tick + read + 400 * (34 + read), places=0)
        v2 = cells["V2-sustained-churn-path-v1-100000-hdt"]["metrics"][0]["measurement"]
        self.assertAlmostEqual(v2["limit_ns"], tick + read + 2000 * (26 + read), places=0)
        k2 = cells["K2-d4-10000-vs-ett"]["metrics"][1]["measurement"]
        self.assertAlmostEqual(k2["limit_ns"], 20 * (tick + read), places=0)
        churn = cells["L3-R-churn-toggle-sparse-100k"]["metrics"][0]["measurement"]
        self.assertAlmostEqual(churn["limit_ns"],
                               570151 * read + 3 * tick * math.sqrt(570151 / 6), places=0)
        p99 = cells["S1-Mreg-standalone-off-read95-b8-c16-100k-none-vs-ett"]["metrics"][1]
        self.assertAlmostEqual(p99["measurement"]["limit_ns"], tick + read, places=0)


class ReportNotesTest(unittest.TestCase):
    def test_v1_s3_notes_and_limits_are_in_every_analysis(self):
        matrix = {"cells": [{"id": "V1", "block": "V1", "kind": "delegated"},
                            {"id": "S3", "block": "S3", "kind": "delegated"}]}
        run = {"status": {"campaign": "complete", "cells": {}}, "raw": []}
        result = an.analyze(matrix, [run])
        self.assertIn("not applied", result["cells"]["V1"]["protocol_note"])
        self.assertIn("no general guarantee", result["cells"]["V1"]["protocol_note"])
        self.assertIn("feeder protocol", result["cells"]["S3"]["protocol_note"])
        self.assertTrue(any("not quantified" in n for n in result["report_notes"]))
        self.assertTrue(any("estimate" in n for n in result["report_notes"]))


class PathConfinementTest(unittest.TestCase):
    """SonarCloud S8707 on PR #35: command-line paths outside the allowed roots are refused."""

    def test_paths_outside_the_roots_are_refused(self):
        outside = "/private/etc/cf5-not-allowed" if sys.platform == "darwin" else "/etc/cf5-x"
        with self.assertRaises(SystemExit):
            an.main(["--matrix", outside, "--run", outside])
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", outside, "--tools", outside, "--out", outside])
        with self.assertRaises(SystemExit):
            an.main(["--matrix", "-x", "--run", tempfile.gettempdir()])


class ReviewRegressionTest(Fixture):
    """One deterministic regression per finding of the independent tooling review."""

    def det_matrix(self, cf_trace, ref_trace, cross=False):
        m = tiny_matrix(check={"same_trace": "trace"})
        det = m["cells"][1]
        det["arms"]["cf"]["args"] += ["--trace", cf_trace]
        det["arms"]["ref"]["args"] += ["--trace", ref_trace]
        det["check"] = {"same_trace": "trace"}
        if cross:
            det["check"]["same_trace_as"] = "C1"
        return m

    def test_b1_client_p99_below_1ms_is_classified_by_its_measured_limit(self):
        # Superseded rule (revision 5, section 6.1): a closed-loop client p99 is one request
        # interval (limit tick + clock read, about 58 ns), so 0.4-0.5 ms is resolvable and
        # gets the plan's class, not TIMER_LIMITED as under the uniform 1 ms threshold.
        pairs = [{"cf": {"metrics": {"latency_ns.p99": 520_000.0}},
                  "ref": {"metrics": {"latency_ns.p99": 400_000.0}}}] * 24
        result = an.classify_paired(limit_cell(57.7, "tail"), pairs)["latency_ns.p99"]
        self.assertEqual(result["class"], "SLOWER")
        self.assertEqual(result["measurement_limit_ns"], 57.7)

    def test_b2_deterministic_arms_must_run_the_same_input(self):
        code, _ = self.run_matrix(self.det_matrix("x", "y"), "d1")
        status = json.loads((self.dir / "d1" / "status.json").read_text())
        self.assertEqual((code, status["campaign"]), (1, "failed"))
        self.assertEqual(status["cells"]["D1"]["state"], "FAILED")

    def test_b2_k4_input_must_equal_its_k2_cell(self):
        code, _ = self.run_matrix(self.det_matrix("y", "y", cross=True), "d2")
        status = json.loads((self.dir / "d2" / "status.json").read_text())
        self.assertEqual(status["campaign"], "failed")
        self.assertIn("input differs from C1", status["cells"]["D1"]["reason"])
        code, _ = self.run_matrix(self.det_matrix("x", "x", cross=True), "d3")
        self.assertEqual(json.loads((self.dir / "d3" / "status.json").read_text())["campaign"],
                         "complete")

    def capped(self, out):
        m = tiny_matrix()
        m["rules"]["cap_hours"] = 0.0000001
        return self.run_matrix(m, out)[1]

    def session2(self, path, out, resume):
        return run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                             str(self.dir / out), "--session", "2",
                             "--resume-from", str(self.dir / resume)])

    def test_s1_no_third_session(self):
        path = self.capped("t1")
        self.assertEqual(self.session2(path, "t2", "t1"), 0)
        with self.assertRaises(SystemExit):   # a second session 2 from the same session 1
            self.session2(path, "t2b", "t1")
        with self.assertRaises(SystemExit):   # resuming from a session 2
            self.session2(path, "t3", "t2")
        runs = [an.load_run(self.dir / "t2"), an.load_run(self.dir / "t1")]
        with self.assertRaises(SystemExit):
            an.check_sessions(runs)
        an.check_sessions([an.load_run(self.dir / "t1"), an.load_run(self.dir / "t2")])

    def test_s2_delegated_outcomes(self):
        with tempfile.TemporaryDirectory() as d:
            marker = Path(d) / "first-failed"
            flaky = (f"import os, sys; p = {str(marker)!r}\n"
                     "if not os.path.exists(p): open(p, 'w').close(); sys.exit(9)\n")
            tools = {"_delegated": {
                "S3": {"argv": [sys.executable, "-c", "import sys; sys.exit(1)"],
                       "incomplete_exit": [1]},
                "V1": {"argv": [sys.executable, "-c", flaky]},
                "L2": {"argv": [sys.executable, "-c", "import sys; print(sys.argv[1])", "{run}"]}}}
            s3 = run_cf5.run_delegated({"id": "S3"}, tools, Path(d))
            v1 = run_cf5.run_delegated({"id": "V1"}, tools, Path(d))
            l2 = run_cf5.run_delegated({"id": "L2"}, tools, Path(d))
            l2_log = Path(l2["attempts"][0]["log"]).read_text()
        self.assertEqual(s3["state"], "INCOMPLETE")
        self.assertEqual((v1["state"], [a["exit"] for a in v1["attempts"]]),
                         ("DELEGATED_DONE", [9, 0]))
        self.assertIn("delegated/L2-attempt1", l2_log)
        self.assertEqual(run_cf5.missing_delegated_env([{"cell": "V1", "kind": "delegated"}],
                                                       {"_delegated": {}}),
                         ["V1: no collector command in the tool map"])

    def test_s3_interruption_is_nonconforming_not_a_cap(self):
        from unittest import mock
        path = self.dir / "m-i1.json"
        path.write_text(json.dumps(tiny_matrix()))
        self.freeze_matrix(path)
        with mock.patch.object(run_cf5, "run_arm_retrying", side_effect=KeyboardInterrupt):
            code = run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                                 str(self.dir / "i1")])
        status = json.loads((self.dir / "i1" / "status.json").read_text())
        self.assertEqual((code, status["campaign"], status["end_cause"]),
                         (1, "nonconforming", "interrupted"))
        with self.assertRaises(SystemExit):
            self.session2(path, "i2", "i1")
        with self.assertRaises(SystemExit):
            an.load_run(self.dir / "i1")

    def test_s6_session_refused_without_matching_freeze(self):
        path = self.dir / "m-z.json"
        path.write_text(json.dumps(tiny_matrix()))
        self.freeze_matrix(path, candidate="0" * 40)
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                          str(self.dir / "z1")])
        self.freeze.write_text(json.dumps({"candidate": self.cand_sha, "matrix_sha256": "0"}))
        with self.assertRaises(SystemExit):
            run_cf5.main(["--matrix", str(path), "--tools", str(self.tools), "--out",
                          str(self.dir / "z2")])
        self.assertFalse((self.dir / "z1").exists() or (self.dir / "z2").exists())

    def test_s8_dirty_or_missing_candidate_is_refused(self):
        (self.cand / "dirt").write_text("x")
        with self.assertRaises(SystemExit):
            self.run_matrix(tiny_matrix(), "y1")
        (self.cand / "dirt").unlink()
        self.write_tools(_checkouts={})
        with self.assertRaises(SystemExit):
            self.run_matrix(tiny_matrix(), "y2")

    def test_nit_mixed_and_insufficient_statements_name_their_cells(self):
        matrix = {"cells": [
            {"id": "A", "block": "K1", "family": "F", "role": "primary", "reference": "r",
             "kind": "deterministic", "metrics": [{"name": "m", "margin": 0.2}]},
            {"id": "B", "block": "K1", "family": "F", "role": "primary", "reference": "r",
             "kind": "deterministic", "metrics": [{"name": "m", "margin": 0.2}]},
            {"id": "C", "block": "K1", "family": "F", "role": "veto", "reference": "r",
             "kind": "deterministic", "metrics": [{"name": "m", "margin": 0.2}]}]}
        raw = [{"cell": "A", "arm": "cf", "metrics": {"m": 1.0}},
               {"cell": "A", "arm": "ref", "metrics": {"m": 2.0}},
               {"cell": "B", "arm": "cf", "metrics": {"m": 2.0}},
               {"cell": "B", "arm": "ref", "metrics": {"m": 1.0}}]
        run = {"status": {"campaign": "incomplete",
                          "cells": {"A": {"state": "COMPLETE"}, "B": {"state": "COMPLETE"},
                                    "C": {"state": "NOT_RUN"}}}, "raw": raw}
        result = an.analyze(matrix, [run])["family_statements"]["F"]["r"]
        self.assertEqual(result, {"statement": "mixed results", "named_cells": ["A", "B"]})


if __name__ == "__main__":
    unittest.main()
