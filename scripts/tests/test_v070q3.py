"""Tests for the v0.7.0 qualification 3 tooling (results/v0.7.0-qualification-3).

They pin what qualification 3 changes relative to the re-qualification (amendment 3
revision 2) and that nothing else drifts: the chain, the launch-environment check and the
precheck agree on paths and arguments; the B/C cells and window multipliers include exactly
the capability-equivalent cells; the matrix differs from the re-qualification's only where
the protocol says; the collectors and analyzers bind the qualification-3 matrix.
"""

import json
import re
import shlex
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_lifecycle_qualification as lifecycle  # noqa: E402

Q3 = ROOT / "results" / "v0.7.0-qualification-3"
RQ = ROOT / "results" / "v0.7.0-requalification"
MATRIX = json.loads((Q3 / "MATRIX.json").read_text())
RQ_MATRIX = json.loads((RQ / "MATRIX.json").read_text())
CHAIN = (Q3 / "run_final_chain.sh").read_text()
ENV = (Q3 / "launch_env_check.sh").read_text()
PREPARE = (Q3 / "prepare_campaign.sh").read_text()
PRECHECK = (Q3 / "precheck_terminal.sh").read_text()
LAUNCH = (Q3 / "launch_command.sh").read_text()
MULTIPLIERS = json.loads((Q3 / "window-multipliers-q3.json").read_text())


def collector_args(text: str, experiment: str) -> list:
    """Collector arguments for EXPERIMENT: after `run_v070q3_collect.py EXPERIMENT`, or after
    the chain's `step NAME CODE EXPERIMENT`, up to a redirection; --dry-run dropped."""
    for line in text.splitlines():
        if f"run_v070q3_collect.py {experiment} " in line:
            words = shlex.split(line[line.index("run_v070q3_collect.py"):].split(">")[0])
            return [w for w in words[2:] if w != "--dry-run"]
        words = line.split()
        if len(words) > 3 and words[0] == "step" and words[3] == experiment:
            return [w for w in shlex.split(line)[4:] if w != "--dry-run"]
    raise AssertionError(f"no collector call for {experiment}")


class Paths(unittest.TestCase):
    def test_every_script_uses_qualification_3_paths(self):
        for name, text in (("chain", CHAIN), ("env", ENV), ("precheck", PRECHECK), ("launch", LAUNCH)):
            self.assertNotIn("results/v0.7.0-requalification/", text.replace("results/v0.7.0-requalification/prepare_campaign.sh", ""), name)
            self.assertNotIn("run_v070r_collect.py", text, name)
        self.assertIn("MATRIX=$B/results/v0.7.0-qualification-3/MATRIX.json", CHAIN)
        self.assertIn("MATRIX=$B/results/v0.7.0-qualification-3/MATRIX.json", PRECHECK)
        self.assertIn("R=$CAMP/src/cand/knotrel-benchmarks/results/v0.7.0-qualification-3", LAUNCH)

    def test_prepare_requires_freeze_q3_and_series_q3(self):
        self.assertIn("results/v0.7.0-qualification-3/FREEZE.json", PREPARE)
        self.assertIn('[ "$SERIES" = q3 ]', PREPARE)
        self.assertIn("['conformance']['qualification_3']['attempts_cap']", PREPARE)
        self.assertIn("CAMP=/Users/rt/workspace/knotrel/evidence/v0.7.0-qualification-3-$C8", PREPARE)
        self.assertIn("--session-seeds 130720 130721 130722", PREPARE)
        self.assertIn("results/v0.7.0-qualification-3/launch_env_check.sh", PREPARE)
        self.assertNotIn("FREEZE-A3.json", PREPARE)

    def test_chain_extension_seeds(self):
        self.assertIn("--session-seeds 130730 130731 130732", CHAIN)
        # Addendum 1, A5: a3-3's seeds are kept; the whole A experiment matches the re-qualification.
        self.assertEqual(MATRIX["experiments"]["A"], RQ_MATRIX["experiments"]["A"])


class ChainAndDryRunsAgree(unittest.TestCase):
    def test_collector_arguments_match(self):
        for experiment in ("bc", "r", "rmem", "mdesc", "mreg"):
            chain, env = collector_args(CHAIN, experiment), collector_args(ENV, experiment)
            # --out differs (the dry run's path is never created); everything else is identical.
            strip = lambda a: [x for i, x in enumerate(a) if not (x == "--out" or (i and a[i - 1] == "--out"))]
            self.assertEqual(strip(chain), strip(env), experiment)

    def test_bc_uses_equivalent_cells_and_q3_multipliers(self):
        args = collector_args(CHAIN, "bc")
        self.assertIn("--equivalent-references", args)
        self.assertEqual(args[args.index("--window-multipliers") + 1], "results/v0.7.0-qualification-3/window-multipliers-q3.json")
        self.assertEqual(args[args.index("--order-seed") + 1], "50720")


class Cells(unittest.TestCase):
    def test_equivalent_cells_and_their_multipliers(self):
        frozen = lifecycle.matrix("final", "compact-bfs")
        q3 = lifecycle.matrix("final", "compact-bfs", True)
        added = [c for c in q3 if c["id"] not in {f["id"] for f in frozen}]
        self.assertEqual(len(added), 13)
        eq = MATRIX["experiments"]["B_C"]["equivalent_references"]
        # Revision 2: the hub ops and events equivalent cells run unchanged but are not equivalent.
        not_equivalent = eq["not_equivalent"]["cells"]
        self.assertEqual(sorted(not_equivalent), ["B4-http-events-equivalent-compact-bfs-hub-10000",
                                                  "B4-http-ops-equivalent-compact-bfs-hub-10000"])
        deciding = eq["deciding"] + not_equivalent
        descriptive = eq["descriptive"]
        self.assertEqual(len(eq["deciding"]), 11)
        self.assertEqual(len(eq["unqualified_requirements"]), 2)
        self.assertEqual(sorted(c["id"] for c in added), sorted(deciding))
        self.assertEqual(sorted(d.replace("-equivalent", "") for d in deciding), sorted(descriptive))
        by_id = {c["id"]: c for c in q3}
        for cell in added:
            twin = by_id[cell["id"].replace("-equivalent", "")]
            self.assertEqual(cell["tolerance"], twin["tolerance"])
            self.assertEqual(MULTIPLIERS[cell["id"]], MULTIPLIERS[twin["id"]])
            scenario = cell["args"][cell["args"].index("--scenario") + 1]
            self.assertEqual(scenario, twin["args"][twin["args"].index("--scenario") + 1] + "-equivalent")
            strip = lambda a: [x for i, x in enumerate(a) if not (x == "--scenario" or (i and a[i - 1] == "--scenario"))]
            self.assertEqual(strip(cell["args"]), strip(twin["args"]))
        lifecycle.apply_multipliers(q3, MULTIPLIERS)  # complete, no unknown key

    def test_default_matrix_unchanged(self):
        self.assertEqual(len(lifecycle.matrix("final", "compact-bfs")), 127)
        self.assertFalse(any("equivalent" in c["id"] for c in lifecycle.matrix("final", "compact-bfs")))


class MatrixDelta(unittest.TestCase):
    def test_only_declared_differences(self):
        changed = {k for k in set(MATRIX) | set(RQ_MATRIX) if MATRIX.get(k) != RQ_MATRIX.get(k)}
        self.assertEqual(changed, {"schema", "status", "references", "experiments", "analysis", "conformance"})
        self.assertEqual(MATRIX["rules"], RQ_MATRIX["rules"])
        conf = {k: v for k, v in MATRIX["conformance"].items() if k != "qualification_3"}
        self.assertEqual(conf, RQ_MATRIX["conformance"])
        self.assertEqual(MATRIX["conformance"]["qualification_3"]["attempt_series"], "q3")
        self.assertEqual(MATRIX["conformance"]["qualification_3"]["attempts_cap"], 3)
        for name in ("R", "Rmem", "M_desc", "M_reg"):
            a, b = dict(MATRIX["experiments"][name]), dict(RQ_MATRIX["experiments"][name])
            a.pop("question"), b.pop("question")
            self.assertEqual(a, b, name)

    def test_thresholds_unchanged(self):
        frozen = {c["id"]: c.get("tolerance") for c in lifecycle.matrix("final", "compact-bfs")}
        q3 = {c["id"]: c.get("tolerance") for c in lifecycle.matrix("final", "compact-bfs", True)}
        for cell_id, tolerance in frozen.items():
            self.assertEqual(q3[cell_id], tolerance)


class Bindings(unittest.TestCase):
    def test_collector_and_analyzer_bind_q3_matrix(self):
        collect = (ROOT / "scripts" / "run_v070q3_collect.py").read_text()
        self.assertIn('"v0.7.0-qualification-3" / "MATRIX.json"', collect)
        analyze = (ROOT / "scripts" / "analyze_v070q3.py").read_text()
        self.assertIn('"v0.7.0-qualification-3" / "MATRIX.json"', analyze)
        self.assertIn("a4.installed()", analyze)


if __name__ == "__main__":
    unittest.main()


class Report(unittest.TestCase):
    def test_roles(self):
        import report_v070q3_bc as report
        eq = MATRIX["experiments"]["B_C"]["equivalent_references"]
        timing = [{"id": i, "status": "PASS"} for i in eq["deciding"] + eq["descriptive"]]
        timing += [{"id": i, "status": "PASS", "atomicity_equivalent": False}
                   for i in eq["not_equivalent"]["cells"]]
        timing.append({"id": "B1-ops-compact-bfs-sparse-1000-query", "status": "INCONCLUSIVE"})
        timing[len(eq["deciding"])]["status"] = "REGRESSION"  # a descriptive cell
        rows = report.label({"timing": timing}, MATRIX)
        roles = {r["id"]: r["role"] for r in rows}
        self.assertTrue(all(roles[i] == "descriptive" for i in eq["descriptive"]))
        self.assertTrue(all(roles[i] == "deciding" for i in eq["deciding"]))
        self.assertEqual(roles["B1-ops-compact-bfs-sparse-1000-query"], "deciding")
        with self.assertRaises(SystemExit):
            report.label({"timing": timing[1:]}, MATRIX)
        full = {"timing": timing,
                "memory": [{"id": "B5-memory-x", "status": "FAIL"}],
                "sustained": [{"id": "C-heap-x", "C1": "PASS", "C3": "FAIL"}, {"id": "C-rss-x", "C4": "EXCEEDS_BUDGET"}]}
        bad = {r["id"] for r in report.non_pass(report.label(full, MATRIX))}
        self.assertIn("B5-memory-x", bad)
        self.assertIn("C-heap-x:C3", bad)
        self.assertNotIn("C-rss-x:C4", bad)  # disclosure category
        self.assertIn("B1-ops-compact-bfs-sparse-1000-query", bad)
        self.assertFalse(any(eq_id in bad for eq_id in eq["descriptive"]))
        self.assertFalse(any(eq_id in bad for eq_id in eq["not_equivalent"]["cells"]))
        self.assertTrue(all(roles[i] == "not_equivalent" for i in eq["not_equivalent"]["cells"]))

    def test_atomicity_fail_closed(self):
        import report_v070q3_bc as report
        eq = MATRIX["experiments"]["B_C"]["equivalent_references"]
        cells = eq["deciding"] + eq["descriptive"] + eq["not_equivalent"]["cells"]
        timing = [{"id": i, "status": "PASS"} for i in cells]
        split = next(i for i in eq["deciding"] if "-ops-equivalent-" in i)
        timing[cells.index(split)]["atomicity_equivalent"] = False
        rows = report.label({"timing": timing}, MATRIX)
        row = next(r for r in rows if r["id"] == split)
        self.assertEqual((row["status"], row["measured_status"]), ("NOT_EQUIVALENT", "PASS"))
        self.assertIn(split, {r["id"] for r in report.non_pass(rows)})
        listed = eq["not_equivalent"]["cells"][0]
        timing[cells.index(listed)]["atomicity_equivalent"] = True
        self.assertEqual(report.inconsistencies(report.label({"timing": timing}, MATRIX)), [listed])

    def test_analyzer_copies_atomicity(self):
        import analyze_lifecycle_qualification as analyzer
        cell = {"id": "B4-http-ops-equivalent-x", "binary": "http", "tolerance": 0.25, "experiment": "B4"}
        def recs(flag):
            out = []
            for k, i in enumerate(range(-2, 12)):
                out.append({"kind": "warmup" if i < 0 else "pair", "candidate_first": k % 2 == 0,
                            "reference_ns": 4e6, "candidate_ns": 4e6 + k, "answers_agree": True,
                            "atomicity_equivalent": flag, "reference_split_chunks": 0 if flag else 2,
                            "reference_max_op_plain_ops": 10 if flag else 1565})
            return out
        self.assertTrue(analyzer.paired(cell, recs(True))["atomicity_equivalent"])
        summary = analyzer.paired(cell, recs(False))
        self.assertEqual((summary["atomicity_equivalent"], summary["reference_max_op_plain_ops"]), (False, 1565))
        partial = recs(True)
        del partial[3]["atomicity_equivalent"]
        with self.assertRaises(analyzer.Invalid):
            analyzer.paired(cell, partial)


class PreFreezeReviewBlockers(unittest.TestCase):
    """B1-B3 of the pre-freeze review."""

    def test_b1_recorder_freeze_file_is_the_q3_freeze_record(self):
        import run_v060_qualification as recorder
        source = (ROOT / "scripts" / "run_v060_qualification.py").read_text()
        self.assertIn('freeze = MATRIX.parent / "FREEZE.json"', source)
        self.assertIn("results/v0.7.0-qualification-3/FREEZE.json", PREPARE)
        self.assertIn('[ -f "$R/FREEZE.json" ]', ENV)
        self.assertTrue(recorder)  # importable

    def test_b2_analyzer_expects_equivalent_cells(self):
        import tempfile
        import analyze_lifecycle_qualification as analyzer
        cells = {c["id"]: c for c in lifecycle.matrix("final", "compact-bfs", True)}
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            for flag, expect, ok in ((True, True, True), (False, True, False), (True, False, False)):
                (run / "provenance.json").write_text(json.dumps(
                    {"profile": "final", "only": "", "lifecycle_engines": "compact-bfs",
                     "equivalent_references": flag, "window_multipliers_sha256": "x"}))
                (run / "run-log.jsonl").write_text("")
                try:
                    analyzer.validate(run, cells, "rev", "x", "compact-bfs", expect)
                    reached = True
                except analyzer.Invalid as error:
                    reached = "missing or failed run" in str(error)  # past the matrix checks
                self.assertEqual(reached, ok, (flag, expect))

    def test_b3_frozen_order_unchanged(self):
        import random
        frozen = lifecycle.matrix("final", "compact-bfs")
        q3 = lifecycle.matrix("final", "compact-bfs", True)
        expected = list(range(len(frozen)))
        random.Random(50720).shuffle(expected)
        frozen_order = [frozen[i]["id"] for i in expected]
        self.assertEqual([frozen[i]["id"] for i in lifecycle.run_order(frozen, 50720)], frozen_order)
        q3_order = [q3[i]["id"] for i in lifecycle.run_order(q3, 50720)]
        self.assertEqual(len(q3_order), 140)
        self.assertEqual([x for x in q3_order if "-equivalent-" not in x], frozen_order)
        for k, cell_id in enumerate(q3_order):
            if "-equivalent-" in cell_id:
                self.assertEqual(q3_order[k - 1], cell_id.replace("-equivalent-", "-"))
        a33 = Path("/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-e75ff6a-a3-attempt3/BC/plan/order.json")
        if a33.exists():
            self.assertEqual(json.loads(a33.read_text()), frozen_order)


T5 = MATRIX["experiments"]["T5"]
T1BASE = "e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc"
CAND = "fa5f3a9eac24873dd2d8d3e0a2c21764cfff9373"
PROBES = "p" * 40


def t5_args(text: str) -> list:
    for line in text.splitlines():
        if "run_v070q3_t5.py" in line and "--out" in line:
            words = shlex.split(line[line.index("run_v070q3_t5.py"):].split(">")[0])
            out = [w for w in words[1:] if w != "--dry-run"]
            i = out.index("--out")
            return out[:i] + out[i + 2:]
    raise AssertionError("no T5 collector call")


def t5_fixture(directory: Path, scale=lambda run, kind: 1.0, compactions=30, mutate=None):
    """A complete synthetic T5 collection. ``scale(run, kind)`` multiplies run timings."""
    import run_v070q3_t5 as collector
    runs = collector.plan(T5["design"]["order_seed"])
    (directory / "raw").mkdir(parents=True)
    (directory / "plan.json").write_text(json.dumps(runs))
    (directory / "provenance.json").write_text(json.dumps({"order_seed": T5["design"]["order_seed"]}))
    step = collector.CYCLES // compactions
    log = []
    for position, run in enumerate(runs):
        rev = T1BASE if run["arm"] == "B" else CAND
        out = [{"kind": "build", "knotrel_rev": rev, "knotrel_dirty": False, "probes_rev": PROBES,
                "probes_dirty": False, "count_alloc": False},
               {"kind": "pauses_start", "nodes": 100000, "cycles": 600, "churn_percent": 5, "seed": 5000001,
                "reuse": "fresh", "retired_vertices": 0}]
        retired, longest = 0, 0
        for cycle in range(1, 601):
            compacting = cycle % step == 0
            retired = 1000 if compacting else retired + 5000
            max_ns = int((10_000_000 + 1000 * cycle) * scale(run, "compaction")) if compacting else 5000
            longest = max(longest, max_ns)
            out.append({"kind": "cycle", "cycle": cycle, "calls": 20000, "max_ns": max_ns,
                        "max_op": "remove_node" if compacting else "add_node", "sum_ns": 1,
                        "retired_vertices": retired})
        out.append({"kind": "pauses_end", "calls": 12_000_000, "max_ns": longest, "timed_ns": 6_000_000_000,
                    "wall_ns": 6_500_000_000, "schedule_digest": "s", "result_digest": "r",
                    "final_logical": [1, 2, 3, 4, 5]})
        if mutate:
            mutate(run, out)
        (directory / "raw" / f"{run['id']}.jsonl").write_text("\n".join(json.dumps(r) for r in out))
        log.append({"position": position, **run, "argv": ["bin"] + collector.child_args(run["topology"]),
                    "exit": 0, "host_before": {"power": "Now drawing from 'AC Power'"}})
    (directory / "run-log.jsonl").write_text("\n".join(json.dumps(r) for r in log))


class T5Check(unittest.TestCase):
    def test_chain_env_and_prepare(self):
        self.assertEqual(t5_args(CHAIN), t5_args(ENV))
        args = t5_args(CHAIN)
        self.assertEqual(args[args.index("--order-seed") + 1], str(T5["design"]["order_seed"]))
        self.assertEqual(args[args.index("--base") + 1], "$T/t1base-probes/release/core-lifecycle")
        self.assertEqual(args[args.index("--cand") + 1], "$T/cand-probes/release/core-lifecycle")
        self.assertIn(f"T1BASE={T1BASE}", PREPARE)
        self.assertIn('clone "$KREPO" "$CAMP/src/t1base/knotrel" "$T1BASE"', PREPARE)
        self.assertIn('clone "$BREPO" "$CAMP/src/t1base/knotrel-benchmarks" "$FREEZE"', PREPARE)
        self.assertIn("CARGO_TARGET_DIR=$T/t1base-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle", PREPARE)
        # T5 runs after B/C and before R; its output is checksummed and refuses a relaunch.
        self.assertLess(CHAIN.index("stamp BC end"), CHAIN.index("stamp T5 start"))
        self.assertLess(CHAIN.index("stamp T5 end"), CHAIN.index("step R 8"))
        self.assertIn('"$CAMP/T5"', CHAIN.split("refusing to relaunch")[0])
        self.assertIn("find A BC T5 R Rmem Mdesc Mreg gate", CHAIN)

    def test_constants_match_matrix(self):
        import analyze_v070q3_t5 as analyzer
        import run_v070q3_t5 as collector
        w = T5["workload"]
        self.assertEqual((collector.NODES, collector.CYCLES, collector.CHURN_PERCENT, collector.SEED, collector.ENGINE),
                         (w["nodes"], w["cycles"], w["churn_percent"], w["seed"], w["engine"]))
        self.assertEqual(list(collector.TOPOLOGIES), w["topologies"])
        self.assertEqual((collector.WARMUP, collector.PAIRS), (T5["design"]["warmup_pairs"], T5["design"]["pairs"]))
        self.assertEqual(analyzer.TOLERANCE, T5["tolerance"])
        self.assertEqual((analyzer.INTERVALS, analyzer.P90_RANK), (30, 27))

    def test_plan(self):
        import run_v070q3_t5 as collector
        runs = collector.plan(50730)
        self.assertEqual(runs, collector.plan(50730))
        self.assertEqual(len(runs), 3 * 14 * 2)
        for topology in collector.TOPOLOGIES:
            mine = [r for r in runs if r["topology"] == topology]
            firsts = [r["arm"] for r in mine if r["slot"] == 0]
            self.assertEqual(firsts[:2], ["C", "B"])
            self.assertEqual(firsts[2:].count("C"), 6)
            for p in range(-2, 12):
                pair = [r for r in mine if r["pair"] == p]
                self.assertEqual(sorted(r["arm"] for r in pair), ["B", "C"])
                self.assertEqual(runs.index(pair[1]), runs.index(pair[0]) + 1)  # consecutive

    def analyze(self, **kw):
        import tempfile
        import analyze_v070q3_t5 as analyzer
        with tempfile.TemporaryDirectory() as tmp:
            t5_fixture(Path(tmp), **kw)
            return analyzer.analyze(Path(tmp), T1BASE, CAND, PROBES)

    def test_statuses(self):
        same = self.analyze()
        self.assertEqual([r["status"] for r in same["results"]], ["PASS"] * 6)
        self.assertEqual(same["non_pass"], [])
        p90 = next(r for r in same["results"] if r["id"] == "T5-P_90-ring")
        self.assertAlmostEqual(p90["absolute_ms"]["B"]["median"], 10.540)  # 27th of 30 = compaction at 540
        worse = self.analyze(scale=lambda run, kind: 1.4 if run["arm"] == "C" else 1.0)
        self.assertEqual({r["status"] for r in worse["results"]}, {"REGRESSION"})
        # Within the tolerance on some pairs only: the interval straddles ln(1.25).
        mixed = self.analyze(scale=lambda run, kind: (1.4 if run["pair"] % 2 else 1.0) if run["arm"] == "C" else 1.0)
        self.assertEqual({r["status"] for r in mixed["results"]}, {"INCONCLUSIVE"})

    def test_invalid(self):
        import analyze_v070q3_t5 as analyzer
        def other_digest(run, out):
            if run["id"] == "hub-3-C":
                out[-1]["result_digest"] = "x"
        def dirty(run, out):
            if run["id"] == "ring-0-B":
                out[0]["knotrel_rev"] = CAND
        def lost_cycle(run, out):
            if run["id"] == "sparse-5-B":
                del out[100]
        for kw in ({"mutate": other_digest}, {"mutate": dirty}, {"mutate": lost_cycle}, {"compactions": 20}):
            with self.assertRaises(analyzer.Invalid, msg=str(kw)):
                self.analyze(**kw)

    def test_report_rows_and_scope(self):
        import report_v070q3_bc as report
        rows = report.t5_rows(self.analyze())
        self.assertEqual(len(rows), 6)
        self.assertTrue(all(r["role"] == "deciding" and r["kind"] == "T5" for r in rows))
        with self.assertRaises(SystemExit):
            report.t5_rows({"check": "T5", "results": []})
        unqualified = MATRIX["experiments"]["B_C"]["equivalent_references"]["unqualified_requirements"]
        self.assertFalse(report.scope(unqualified)["complete"])
        self.assertTrue(report.scope([])["complete"])
        bad = [dict(r, status="INCONCLUSIVE") for r in rows]
        self.assertEqual(len(report.non_pass(bad)), 6)

    def test_gate_counts_t5(self):
        import tempfile
        import conformance_gate as cg
        with tempfile.TemporaryDirectory() as tmp:
            camp = Path(tmp)
            self.assertEqual(cg.collector_counts(camp)["T5"], 0)
            (camp / "T5").mkdir()
            (camp / "T5" / "run-log.jsonl").write_text("{}\n{}\n")
            self.assertEqual(cg.collector_counts(camp)["T5"], 2)
            self.assertIn("T5: 2 children recorded by the collector, 0 gated", cg.verify_gating(camp, camp / "gate"))
