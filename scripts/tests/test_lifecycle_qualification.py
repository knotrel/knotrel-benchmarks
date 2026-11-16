"""Unit tests for the v0.5.0 lifecycle qualification collector and analysis."""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze_lifecycle_qualification as an  # noqa: E402
import cli_paths  # noqa: E402
import run_lifecycle_qualification as run  # noqa: E402

# The analyses below read and write temporary directories; grant that root
# explicitly, as an operator would for a run outside the default roots.
os.environ["LIFECYCLE_QUALIFICATION_ROOTS"] = tempfile.gettempdir()

REV = "a" * 40
SHA = "b" * 64


PROBES = "c" * 40


def build(count_alloc=False, rev=REV, dirty=False, probes=PROBES, probes_dirty=False):
    return {"kind": "build", "knotrel_rev": rev, "knotrel_dirty": dirty, "count_alloc": count_alloc,
            "probes_rev": probes, "probes_dirty": probes_dirty}


def write_run(root: Path, cells, raws, provenance=None, log_overrides=None) -> None:
    (root / "plan").mkdir(parents=True)
    (root / "raw").mkdir()
    (root / "plan" / "matrix.json").write_text(json.dumps(cells))
    for cell_id, records in raws.items():
        (root / "raw" / f"{cell_id}.jsonl").write_text("\n".join(json.dumps(r) for r in records) + "\n")
    prov = {"profile": "final", "only": "", "window_multipliers_sha256": SHA}
    prov.update(provenance or {})
    (root / "provenance.json").write_text(json.dumps(prov))
    log = []
    for cell in cells:
        record = {"id": cell["id"], "exit": 0, "host_before": {"power": "Now drawing from 'AC Power'"}}
        record.update((log_overrides or {}).get(cell["id"], {}))
        log.append(json.dumps(record))
    (root / "run-log.jsonl").write_text("\n".join(log) + "\n")


def pairs(ratios, reference_ns=5_000_000, balanced=True, warmup=2):
    records = [build(), {"kind": "verify", "match": True}]
    records += [{"kind": "warmup", "pair": -1 - i, "candidate_first": i % 2 == 0,
                 "reference_ns": reference_ns, "candidate_ns": reference_ns} for i in range(warmup)]
    records += [{"kind": "pair", "pair": i, "candidate_first": (i % 2 == 0) if balanced else True,
                 "reference_ns": reference_ns, "candidate_ns": int(reference_ns * r)}
                for i, r in enumerate(ratios)]
    return records


class MatrixTests(unittest.TestCase):
    def test_matrix_is_deterministic_and_unique(self):
        first, second = run.matrix("final"), run.matrix("final")
        self.assertEqual(first, second)
        ids = [c["id"] for c in first]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual([c["id"] for c in run.matrix("pilot")], ids)

    def test_multipliers_must_cover_exactly_the_timed_cells(self):
        cells = run.matrix("final")
        timed = {c["id"]: 1 for c in cells if c["experiment"] in ("B1", "B2", "B3", "B4")}
        with self.assertRaises(SystemExit):
            run.apply_multipliers(run.matrix("final"), {**timed, "B9-unknown": 2})
        missing = dict(timed)
        missing.pop(next(iter(missing)))
        with self.assertRaises(SystemExit):
            run.apply_multipliers(run.matrix("final"), missing)

    def test_multipliers_scale_windows_and_requests(self):
        cells = run.matrix("final")
        factors = {c["id"]: 1 for c in cells if c["experiment"] in ("B1", "B2", "B3", "B4")}
        factors["B1-ops-ett-ring-1000-query"] = 8
        factors["B4-http-import-compact-bfs-sparse-10000"] = 4
        run.apply_multipliers(cells, factors)
        by_id = {c["id"]: c for c in cells}
        args = by_id["B1-ops-ett-ring-1000-query"]["args"]
        self.assertEqual(args[args.index("--window") + 1], "32000")
        args = by_id["B4-http-import-compact-bfs-sparse-10000"]["args"]
        self.assertEqual(args[args.index("--requests") + 1], "4")


class CliPathTests(unittest.TestCase):
    def test_paths_must_stay_inside_the_allowed_roots(self):
        repo_file = Path(run.__file__)
        self.assertEqual(cli_paths.confined(repo_file, "x"), repo_file.resolve())
        for bad in ("-rf", "/etc/passwd", str(repo_file.parent / ".." / ".." / ".." / ".." / "etc")):
            with self.assertRaises(SystemExit):
                cli_paths.confined(bad, "x")
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "tool"
            script.write_text("#!/bin/sh\n")
            with self.assertRaises(SystemExit):
                cli_paths.confined_executable(script, "x")  # not executable
            script.chmod(0o755)
            self.assertEqual(cli_paths.confined_executable(script, "x"), script.resolve())
            with self.assertRaises(SystemExit):
                cli_paths.confined_directory(script, "x")

    def test_data_derived_names_cannot_leave_their_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = Path(tmp) / "raw"
            raw.mkdir()
            self.assertEqual(cli_paths.contained_file(raw, "B1-x.jsonl", "x"), (raw / "B1-x.jsonl").resolve())
            (raw / "link.jsonl").symlink_to(Path(tmp) / "elsewhere.jsonl")
            for bad in ("../escape.jsonl", "sub/inner.jsonl", "/etc/passwd", "link.jsonl"):
                with self.assertRaises(SystemExit):
                    cli_paths.contained_file(raw, bad, "x")


class ScopeTests(unittest.TestCase):
    def test_compact_bfs_scope_keeps_every_compact_bfs_cell_and_only_non_lifecycle_others(self):
        full = run.matrix("final")
        scoped = run.matrix("final", "compact-bfs")
        engine = lambda c: c["args"][c["args"].index("--engine") + 1]
        self.assertEqual([c for c in full if engine(c) == "compact-bfs"],
                         [c for c in scoped if engine(c) == "compact-bfs"])
        others = [c["id"] for c in scoped if engine(c) != "compact-bfs"]
        self.assertEqual(others, ["B4-http-metrics-legacy-ett-sparse-10000",
                                  "B4-http-metrics-legacy-hdt-sparse-10000"])
        self.assertEqual(len(scoped), 127)
        self.assertEqual(run.matrix("final", "compact-bfs,ett,hdt"), full)
        with self.assertRaises(SystemExit):
            run.matrix("final", "compact-bfs,unknown")

    def test_analysis_rejects_a_plan_outside_the_expected_scope(self):
        cells = [c for c in run.matrix("final", "compact-bfs") if c["experiment"] == "B1"][:1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_run(root, cells, {cells[0]["id"]: pairs([1.0] * 12)},
                      provenance={"lifecycle_engines": "compact-bfs"})
            sys.argv = ["x", str(root), "--expect-knotrel-rev", REV, "--expect-multipliers-sha256", SHA,
                        "--expect-probes-rev", PROBES, "--expect-lifecycle-engines", "compact-bfs"]
            self.assertEqual(an.main(), 3)  # one cell is not the full 127-cell scope
            sys.argv[-1] = "compact-bfs,ett,hdt"
            self.assertEqual(an.main(), 3)  # scope recorded differs from the expected scope


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        # These tests use synthetic plans; the scope check is covered by ScopeTests.
        self._runner = an._runner

    def tearDown(self):
        an._runner = self._runner

    def analyze(self, cells, raws, **kwargs):
        an._runner = lambda: types.SimpleNamespace(matrix=lambda profile, engines: cells)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_run(root, cells, raws, **kwargs)
            out = root / "report.json"
            sys.argv = ["x", str(root), "--expect-knotrel-rev", REV, "--expect-multipliers-sha256", SHA,
                        "--expect-probes-rev", PROBES,
                        "--json", str(out), "--markdown", str(root / "r.md")]
            code = an.main()
            return code, (json.loads(out.read_text()) if code == 0 else None)

    def cell(self, cid, tolerance=0.25):
        return {"id": cid, "experiment": "B1", "tolerance": tolerance, "binary": "core", "args": []}

    def test_classification_uses_order_statistic_interval(self):
        cells = [self.cell("pass"), self.cell("regression"), self.cell("inconclusive"), self.cell("timer")]
        incon = [1.0, 1.1, 1.2, 1.3, 1.4, 1.1, 1.2, 1.3, 1.0, 1.2, 1.25, 1.35]
        raws = {
            "pass": pairs([1.0, 1.01, 0.99, 1.02, 0.98, 1.0, 1.03, 0.97, 1.0, 1.01, 0.99, 1.0]),
            "regression": pairs([1.4] * 12),
            "inconclusive": pairs(incon),
            "timer": pairs([1.0] * 12, reference_ns=500_000),
        }
        code, report = self.analyze(cells, raws)
        self.assertEqual(code, 0)
        status = {t["id"]: t for t in report["timing"]}
        self.assertEqual(status["pass"]["status"], "PASS")
        self.assertEqual(status["regression"]["status"], "REGRESSION")
        self.assertEqual(status["inconclusive"]["status"], "INCONCLUSIVE")
        self.assertEqual(status["timer"]["status"], "TIMER_LIMITED")
        ratios = sorted(math.log(r) for r in incon)
        self.assertAlmostEqual(status["inconclusive"]["interval_log"][0], ratios[2], places=6)
        self.assertAlmostEqual(status["inconclusive"]["interval_log"][1], ratios[9], places=6)

    def test_invalid_runs_are_rejected(self):
        ok = pairs([1.0] * 12)
        cases = [
            ({"c": [build(), {"kind": "verify", "match": False}] + ok[2:]}, {}),
            ({"c": pairs([1.0] * 12, balanced=False)}, {}),
            ({"c": pairs([1.0] * 12, warmup=0)}, {}),
            ({"c": [build(rev="f" * 40)] + ok[1:]}, {}),
            ({"c": [build(dirty=True)] + ok[1:]}, {}),
            ({"c": [build(probes="d" * 40)] + ok[1:]}, {}),
            ({"c": [build(probes_dirty=True)] + ok[1:]}, {}),
            ({"c": ok}, {"provenance": {"only": "B1"}}),
            ({"c": ok}, {"provenance": {"window_multipliers_sha256": "0" * 64}}),
            ({"c": ok}, {"log_overrides": {"c": {"exit": 1}}}),
            ({"c": ok}, {"log_overrides": {"c": {"host_before": {"power": "Battery Power"}}}}),
        ]
        for raws, kwargs in cases:
            code, _ = self.analyze([self.cell("c")], raws, **kwargs)
            self.assertEqual(code, 3, kwargs or raws["c"][:2])
        code, _ = self.analyze([self.cell("c"), self.cell("missing")], {"c": ok})
        self.assertEqual(code, 3)

    def test_sustained_rules(self):
        def run_records(heap, engine=lambda c: 100_000, wrong=False):
            records = [build(count_alloc=True)]
            for c in range(31):
                logical = [100_000, 5, 100_000, 5, 5]
                expected = list(logical)
                if wrong and c == 7:
                    expected[2] -= 1
                records.append({"kind": "checkpoint", "cycle": c, "expected": expected,
                                "counts": {"logical": logical, "engine_vertices": engine(c),
                                           "retired_vertices": engine(c) - 100_000},
                                "net_heap_bytes": heap(c), "net_rss_bytes": heap(c)})
            return records
        names = ("flat", "grow", "slots", "counts", "linear")
        cells = [{"id": f"C-heap-lifecycle-ett-sparse-{m}-100000", "experiment": "C", "binary": "core-count",
                  "args": ["resources", "--cycles", "30"]} for m in names]
        raws = {
            cells[0]["id"]: run_records(lambda c: 1000),
            cells[1]["id"]: run_records(lambda c: 1000 + 100 * c),
            cells[2]["id"]: run_records(lambda c: 1000, engine=lambda c: 300_000),
            cells[3]["id"]: run_records(lambda c: 1000, wrong=True),
            cells[4]["id"]: run_records(lambda c: 1000 + 5 * c),
        }
        code, report = self.analyze(cells, raws)
        self.assertEqual(code, 0)
        result = {r["id"]: r for r in report["sustained"]}
        self.assertEqual(result[cells[0]["id"]]["C3"], "PASS")
        self.assertEqual(result[cells[1]["id"]]["C3"], "FAIL")
        self.assertEqual(result[cells[2]["id"]]["C1"], "FAIL")
        self.assertEqual(result[cells[3]["id"]]["C2"], "FAIL")
        # 5 bytes per cycle on ~1,027: max ratio passes, projected 30-cycle growth (14.6%) fails.
        self.assertEqual(result[cells[4]["id"]]["C3"], "FAIL")

    def test_missing_checkpoint_is_invalid(self):
        cell = {"id": "C-heap-lifecycle-ett-sparse-x-100000", "experiment": "C", "binary": "core-count",
                "args": ["resources", "--cycles", "30"]}
        records = [build(count_alloc=True)] + [
            {"kind": "checkpoint", "cycle": c, "expected": [1, 0, 1, 0, 0],
             "counts": {"logical": [1, 0, 1, 0, 0], "engine_vertices": 1, "retired_vertices": 0},
             "net_heap_bytes": 1, "net_rss_bytes": 1} for c in range(30)]
        code, _ = self.analyze([cell], {cell["id"]: records})
        self.assertEqual(code, 3)


if __name__ == "__main__":
    unittest.main()
