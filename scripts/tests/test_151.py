"""Tests of the knotrel#151 comparison tooling (compact_index_matrix.py, run_151.py,
analyze_151.py) on synthetic data."""

from __future__ import annotations

import copy
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
os.environ["LIFECYCLE_QUALIFICATION_ROOTS"] = os.pathsep.join(
    filter(None, [os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS"), tempfile.gettempdir()]))
import analyze_151 as an  # noqa: E402
import compact_index_matrix as mx  # noqa: E402
import run_151  # noqa: E402
import run_cf5  # noqa: E402


def windowed_matrix(factor: int = 1):
    base = mx.build()
    factors = {c["id"]: factor for c in base["cells"] if "window" in c}
    return mx.build(factors=factors)


class MatrixTest(unittest.TestCase):
    def test_cell_counts_match_section_6_4(self):
        counts = Counter(c["group"] for c in mx.build()["cells"])
        self.assertEqual(counts["M1"], 20)
        self.assertEqual(counts["M1-iso"], 2)
        letters = Counter()
        for group, n in counts.items():
            if group in ("M1-iso", "M6", "Q"):
                continue
            letters[group[0]] += n
        # Section 6.4 totals: M 42, I 18, R 26, P 22, C 18 classified cells.
        self.assertEqual(dict(letters), {"M": 42, "I": 18, "R": 26, "P": 22, "C": 18})
        self.assertEqual(counts["Q"], 1)

    def test_metric_comparisons_match_section_6_4(self):
        cells = mx.build()["cells"]
        def metrics(letter):
            return sum(len(c["metrics"]) for c in cells if c["group"][0] == letter
                       and not c["report_only"] and c["kind"] != "delegated")
        self.assertEqual(metrics("M"), 86)
        self.assertEqual(metrics("P"), 36)
        self.assertEqual(metrics("C"), 32)
        self.assertEqual(metrics("I") + metrics("R"), 44)

    def test_arms_differ_only_by_tool_and_every_cell_is_gated(self):
        for cell in mx.build()["cells"]:
            if cell["kind"] == "delegated":
                continue
            cf, ref = cell["arms"]["cf"], cell["arms"]["ref"]
            self.assertEqual(cf["args"], ref["args"], cell["id"])
            self.assertTrue(cf["tool"].endswith("_cand") and ref["tool"].endswith("_base"))
            self.assertIn("same_trace", cell["check"])
            for m in cell["metrics"]:
                if m["margin_kind"] in ("time", "tail"):
                    self.assertIn("measurement", m, cell["id"])
            if cell["group"] in ("P3", "P4", "C3"):
                self.assertEqual(cell["check"]["path"], "errors")

    def test_margins_and_memory_rules(self):
        m = mx.build()
        self.assertEqual(m["rules"]["margins"], {"time": 0.10, "tail": 0.25, "throughput": 0.10})
        self.assertEqual(m["rules"]["memory"], {"smaller_at_most": 0.90, "larger_at_least": 1.05})
        self.assertEqual(m["windows"], "unset")

    def test_windows_follow_the_apply_multipliers_rule(self):
        base = mx.build()
        windowed = [c["id"] for c in base["cells"] if "window" in c]
        factors = {cid: 4 for cid in windowed}
        m = mx.build(factors=factors)
        self.assertEqual(m["windows"], "set")
        r4 = next(c for c in m["cells"] if c["group"] == "R4")
        self.assertEqual(r4["params"]["k"], 4)
        self.assertIn("4", r4["arms"]["cf"]["args"])
        self.assertAlmostEqual(r4["metrics"][0]["measurement"]["limit_ns"],
                               (mx.TICK_NS + mx.CLOCK_READ_NS) / 4, places=2)
        with self.assertRaises(SystemExit):
            mx.build(factors={cid: 4 for cid in windowed[1:]})
        with self.assertRaises(SystemExit):
            mx.build(factors={**factors, "nope": 2})
        with self.assertRaises(SystemExit):
            mx.build(factors={**factors, windowed[0]: 3})

    def test_scale_divides_sizes(self):
        m = mx.build(scale=10)
        cell = next(c for c in m["cells"] if c["id"] == "M1-cb-his-1e6")
        args = cell["arms"]["cf"]["args"]
        self.assertEqual(args[args.index("--nodes") + 1], "100000")
        self.assertEqual(args[args.index("--degree") + 1], "100000")


def pair_line(cell, pair, cf, ref, warmup=False, extra=None):
    def obs(arm, values):
        obj = {"gate": {"x": 1}, **(extra or {})}
        for m in cell["metrics"]:
            obj[m["path"]] = values[m["name"]]
        return {"arm": arm, "object": obj, "metrics": dict(values), "wall_s": 1.0}
    return {"cell": cell["id"], "pair": pair, "warmup": warmup, "cf_first": pair % 2 == 0,
            "cf": obs("cf", cf), "ref": obs("ref", ref)}


def synthetic_run(matrix, tmp: Path, time_ratio=1.0, memory_ratio=0.8, overrides=None,
                  q_pass=True, failed=False):
    """A complete session: timed cells at ``time_ratio`` (B / CUR, with small symmetric
    noise), memory cells at ``memory_ratio``; ``overrides``: cell id -> ratio."""
    overrides = overrides or {}
    raw, states = [], {}
    for cell in matrix["cells"]:
        if cell["kind"] == "delegated":
            run_dir = tmp / "delegated" / "Q-attempt1"
            run_dir.mkdir(parents=True, exist_ok=True)
            crit = {c: (q_pass or c != "C2") for c in ("C1", "C2", "C3", "C4")}
            (run_dir / "q.json").write_text(json.dumps({"quick": False, "base": crit,
                                                        "cand": crit, "d5_pass": q_pass}))
            states[cell["id"]] = {"state": "DELEGATED_DONE",
                                  "attempts": [{"run_dir": str(run_dir), "exit": 0}]}
            continue
        ratio = overrides.get(cell["id"], memory_ratio if cell["kind"] == "deterministic"
                              else time_ratio)
        if cell["kind"] == "deterministic":
            for arm, scale in (("cf", ratio), ("ref", 1.0)):
                metrics = {m["name"]: 100e6 * scale for m in cell["metrics"]}
                raw.append({"cell": cell["id"], "arm": arm, "metrics": metrics,
                            "object": {"edges_registered": 1_000_000, "gate": {}}})
            states[cell["id"]] = {"state": "COMPLETE", "pairs": 1}
            continue
        extra = {"operations": 1000, "traversal_pages": 10}
        for i in range(run_cf5.WARMUP + run_cf5.PAIRS):
            noise = 1 + 0.01 * ((i % 5) - 2)
            ref = {m["name"]: 1e7 for m in cell["metrics"]}
            cf = {}
            for m in cell["metrics"]:
                r = ratio * noise
                cf[m["name"]] = 1e7 / r if m["direction"] == "higher_is_better" else 1e7 * r
            raw.append(pair_line(cell, i, cf, ref, warmup=i < run_cf5.WARMUP, extra=extra))
        states[cell["id"]] = {"state": "COMPLETE", "pairs": run_cf5.PAIRS}
    status = {"campaign": "failed" if failed else "complete", "cells": states}
    return {"status": status, "record": {"session": 1}, "raw": raw, "path": tmp}


class AnalyzerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.matrix = windowed_matrix()

    def decide(self, **kwargs):
        dispositions = kwargs.pop("dispositions", None)
        run = synthetic_run(self.matrix, self.tmp, **kwargs)
        return an.analyze(self.matrix, [run], dispositions)

    def test_adopt_when_every_rule_holds(self):
        result = self.decide()
        self.assertEqual(result["decision"]["items"],
                         {"D1": "pass", "D2": "pass", "D3": "pass", "D4": "pass", "D5": "pass",
                          "D6": "pass"})
        self.assertEqual(result["decision"]["result"], "ADOPT")
        cell = result["cells"]["I2-cb-his-1e4"]["metrics"]["observation_ns"]
        self.assertEqual(cell["class"], "EQUIVALENT")
        self.assertEqual(result["cells"]["M1-cb-sparse-1e6"]["metrics"]["live_after"]["class"],
                         "SMALLER")
        # G2: (100e6 - 80e6) / 1e6 = 20 bytes per registered edge.
        self.assertAlmostEqual(
            result["benefit"]["G2"]["bytes_per_registered_edge"]["M1-cf-his-1e6"], 20.0)

    def test_a_single_slower_cell_rejects(self):
        result = self.decide(overrides={"P2-cb-his-1e6-scrambled": 1.3})
        self.assertEqual(result["decision"]["items"]["D4"], "fail")
        self.assertEqual(result["decision"]["result"], "REJECT")
        self.assertIn("P2-cb-his-1e6-scrambled/median_page_ns", result["decision"]["slower"])

    def test_faster_cells_do_not_offset(self):
        result = self.decide(time_ratio=0.5, overrides={"C3-cf-hub-1e4": 1.25})
        self.assertEqual(result["cells"]["I1-cb-sparse-1e5"]["metrics"]["observation_ns"]
                         ["class"], "FASTER")
        # Throughput: B at 1/1.25 of CUR's requests_per_s is SLOWER.
        self.assertEqual(result["decision"]["result"], "REJECT")

    def test_larger_memory_rejects_but_report_only_does_not(self):
        result = self.decide(overrides={"M1iso-cb-iso-1e6": 1.2, "M6-cf-ring-1e6": 1.5})
        self.assertEqual(result["decision"]["items"]["D3"], "pass")
        self.assertTrue(result["cells"]["M1iso-cb-iso-1e6"]["report_only"])
        result = self.decide(overrides={"M4-cb-hub-1e5-same": 1.05})
        self.assertEqual(result["decision"]["items"]["D3"], "fail")

    def test_g1_and_g2(self):
        # q = 0.95: SIMILAR (G1 fails), 5 bytes per edge (G2 fails).
        result = self.decide(memory_ratio=0.95)
        self.assertEqual(result["benefit"]["G1"]["status"], "fail")
        self.assertEqual(result["benefit"]["G2"]["status"], "fail")
        self.assertEqual(result["decision"]["result"], "REJECT")
        # G1 holds but one M1 cell with V >= 10^5 saves less than 8 bytes per edge.
        result = self.decide(overrides={"M1-cf-star-1e5": 0.93})
        self.assertEqual(result["benefit"]["G1"]["status"], "pass")
        self.assertEqual(result["benefit"]["G2"]["status"], "fail")
        # Cells below 10^5 nodes are outside G2.
        result = self.decide(overrides={"M1-cf-sparse-1e4": 0.99})
        self.assertEqual(result["benefit"]["G2"]["status"], "pass")

    def test_inconclusive_needs_a_disposition(self):
        result = self.decide(overrides={"R5-cf-sparse-1e6": 1.10})
        self.assertEqual(result["cells"]["R5-cf-sparse-1e6"]["metrics"]["observation_ns"]
                         ["class"], "INCONCLUSIVE")
        self.assertEqual(result["decision"]["result"], "NO DECISION")
        accepted = self.decide(overrides={"R5-cf-sparse-1e6": 1.10},
                               dispositions={"R5-cf-sparse-1e6": {"disposition": "accept"}})
        self.assertEqual(accepted["decision"]["result"], "ADOPT")
        follow = self.decide(overrides={"R5-cf-sparse-1e6": 1.10},
                             dispositions={"R5-cf-sparse-1e6/observation_ns":
                                           {"disposition": "follow-up"}})
        self.assertEqual(follow["decision"]["result"], "NO DECISION")

    def test_q_failure_and_campaign_failure_reject(self):
        self.assertEqual(self.decide(q_pass=False)["decision"]["items"]["D5"], "fail")
        result = self.decide(failed=True)
        self.assertEqual(result["decision"]["items"]["D1"], "fail")
        self.assertEqual(result["decision"]["result"], "REJECT")

    def test_interval_uses_order_statistics_7_and_18(self):
        cell = next(c for c in self.matrix["cells"] if c["id"] == "I1-cb-sparse-1e6")
        ratios = [math.exp(0.01 * i) for i in range(24)]
        pairs = [pair_line(cell, i, {"observation_ns": 1e7 * r}, {"observation_ns": 1e7})
                 for i, r in enumerate(ratios)]
        out = an.cf5.classify_paired(an.resolved(cell, pairs), pairs)["observation_ns"]
        self.assertAlmostEqual(out["interval_log"][0], 0.06)
        self.assertAlmostEqual(out["interval_log"][1], 0.17)

    def test_workload_dependent_limits_and_timer_limited(self):
        cell = next(c for c in self.matrix["cells"] if c["id"] == "C1-cb-sparse-1e5-fresh")
        pairs = [pair_line(cell, i, {"observation_ns": 1e7, "slowest_op_ns": 100},
                           {"observation_ns": 1e7, "slowest_op_ns": 100},
                           extra={"operations": 750_000}) for i in range(24)]
        resolved = an.resolved(cell, pairs)
        limit = resolved["metrics"][0]["measurement"]["limit_ns"]
        self.assertAlmostEqual(limit, 750_000 * 16 + 3 * mx.TICK_NS * math.sqrt(125_000), 0)
        out = an.cf5.classify_paired(resolved, pairs)
        self.assertEqual(out["slowest_op_ns"]["class"], "TIMER_LIMITED")
        pairs[3]["cf"]["object"]["operations"] = 1
        with self.assertRaises(SystemExit):
            an.resolved(cell, pairs)

    def test_memory_class_boundaries(self):
        rules = mx.MEMORY
        self.assertEqual(an.memory_class(90, 100, rules)["class"], "SMALLER")
        self.assertEqual(an.memory_class(91, 100, rules)["class"], "SIMILAR")
        self.assertEqual(an.memory_class(105, 100, rules)["class"], "LARGER")
        self.assertEqual(an.memory_class(5, 0, rules)["class"], "UNDEFINED")

    def test_refuses_scaled_or_unwindowed_matrices(self):
        run = synthetic_run(self.matrix, self.tmp)
        with self.assertRaises(SystemExit):
            an.analyze(mx.build(), [run])
        scaled = copy.deepcopy(self.matrix)
        scaled["scale"] = 10
        with self.assertRaises(SystemExit):
            an.analyze(scaled, [run])


class ProposeWindowsTest(unittest.TestCase):
    def test_factor_targets_2ms_for_the_faster_arm_and_respects_the_pool(self):
        matrix = mx.build()
        raw = []
        for cell in matrix["cells"]:
            if cell["kind"] != "paired":
                continue
            for i in range(2):
                # cf at 0.3 ms, ref at 0.2 ms: the faster arm needs 10x -> 16.
                raw.append(pair_line(cell, i, {m["name"]: 3e5 for m in cell["metrics"]},
                                     {m["name"]: 2e5 for m in cell["metrics"]},
                                     extra={"observation_ns": 0}))
                for arm, value in (("cf", 3e5), ("ref", 2e5)):
                    raw[-1][arm]["object"]["observation_ns"] = value
        result = run_151.propose(matrix, raw)
        self.assertEqual(result["factors"]["I3-cb-sparse-1e6"], 16)
        self.assertEqual(result["factors"]["R4-cb-star-1e4"], 16)
        self.assertEqual(set(result["factors"]),
                         {c["id"] for c in matrix["cells"] if "window" in c})
        # The proposal feeds the matrix generator unchanged.
        mx.build(factors=result["factors"])
        self.assertGreater(result["estimate_total_h"], 0)

    def test_pool_cap(self):
        matrix = mx.build(scale=1000)  # hub degree 10 at D = 10^4: k = 32 already exceeds it
        cell = next(c for c in matrix["cells"] if c["id"] == "I2-cb-his-1e4")
        raw = [pair_line(cell, i, {"observation_ns": 1e3}, {"observation_ns": 1e3})
               for i in range(2)]
        result = run_151.propose({"cells": [cell]}, raw)
        self.assertEqual(result["factors"]["I2-cb-his-1e4"], 1)


class FreezeTest(unittest.TestCase):
    def test_freeze_refuses_unfrozen_inputs(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "m.json").write_text(json.dumps(mx.build()))
        (tmp / "t.json").write_text(json.dumps({"_build": {"overlay": True}}))
        with self.assertRaises(SystemExit) as caught:
            run_151.main(["freeze", "--matrix", str(tmp / "m.json"), "--tools",
                          str(tmp / "t.json"), "--out", str(tmp / "F.json")])
        message = str(caught.exception)
        self.assertIn("frozen windows", message)
        self.assertIn("--overlay", message)
        self.assertIn("no candidate", message)
        self.assertFalse((tmp / "F.json").exists())

    def test_campaign_refuses_a_scaled_matrix(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "m.json").write_text(json.dumps(mx.build(scale=10)))
        (tmp / "t.json").write_text("{}")
        with self.assertRaises(SystemExit):
            run_151.main(["campaign", "--matrix", str(tmp / "m.json"), "--tools",
                          str(tmp / "t.json"), "--out", str(tmp / "out")])


class SmokeTest(unittest.TestCase):
    def test_smoke_reports_gate_differences_and_repeats(self):
        tmp = Path(tempfile.mkdtemp())
        fake = tmp / "fake.py"
        fake.write_text(
            "import json, sys\n"
            "arm = sys.argv[1]\n"
            "gate = {'x': 2 if arm == 'odd' else 1}\n"
            "print(json.dumps({'kind': 'build'}))\n"
            "print(json.dumps({'v': 5, 'gate': gate, 'errors': 0}))\n")
        tools = {f"t_{side}": [sys.executable, str(fake), arm]
                 for side, arm in (("cand", "even"), ("base", "even"))}
        tools["u_cand"] = [sys.executable, str(fake), "odd"]
        tools["u_base"] = [sys.executable, str(fake), "even"]
        metric = {"name": "v", "path": "v", "margin_kind": "memory", "margin": 0.1,
                  "direction": "lower_is_better"}
        cells = [mx.cell("A", "M1", "M", "deterministic", "t", [], [metric], {}),
                 mx.cell("B", "M1", "M", "deterministic", "u", [], [metric], {})]
        matrix = {"scale": 1, "cells": cells}
        (tmp / "m.json").write_text(json.dumps(matrix))
        (tmp / "t.json").write_text(json.dumps(tools))
        code = run_151.main(["smoke", "--matrix", str(tmp / "m.json"), "--tools",
                             str(tmp / "t.json"), "--out", str(tmp / "out")])
        self.assertEqual(code, 1)
        summary = json.loads((tmp / "out" / "summary.json").read_text())
        self.assertEqual(summary["failed"], ["B"])
        lines = [json.loads(l) for l in (tmp / "out" / "smoke.jsonl").read_text().splitlines()]
        self.assertTrue(lines[0]["deterministic"])


if __name__ == "__main__":
    unittest.main()
