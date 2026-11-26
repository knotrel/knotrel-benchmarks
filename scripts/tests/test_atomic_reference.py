"""Tests for the application-gate (``-atomic``) B4 reference (knotrel#180, decision M1(b)).

They pin that the new cell exists only on request, for ``ops`` on the compact-bfs hub 10k
with its counterpart's requests and tolerance; that the run order keeps the frozen and the
qualification-3 sequences and places the ``-atomic`` twin after its counterpart; that the
analyzer requires the gate records; and that the decision view classifies the cell with the
fail-closed rule while reading every historical matrix as before. No test measures anything.
"""

import copy
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import importlib.util  # noqa: E402

import analyze_lifecycle_qualification as analyzer  # noqa: E402
import report_v070q3_bc as frozen_report  # noqa: E402
import run_lifecycle_qualification as lifecycle  # noqa: E402


def _private_report():
    """``report_v100q_bc`` loaded under a private name: importing it rebinds the shared
    ``report_v070q3_bc.MATRIX``, which other test modules pin, so the binding is restored
    and the module cache is left untouched."""
    saved = frozen_report.MATRIX
    spec = importlib.util.spec_from_file_location("_atomic_report_v100q_bc",
                                                  ROOT / "scripts" / "report_v100q_bc.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    frozen_report.MATRIX = saved
    return module


report = _private_report()

ATOMIC = "B4-http-ops-atomic-compact-bfs-hub-10000"
COUNTERPART = "B4-http-ops-compact-bfs-hub-10000"
EQUIVALENT = "B4-http-ops-equivalent-compact-bfs-hub-10000"
V100_MATRIX = json.loads((ROOT / "results" / "v1.0.0-qualification" / "MATRIX.json").read_text())


def atomic_matrix() -> dict:
    """The v1.0.0 matrix plus an ``atomic_references`` block, as a next qualification would."""
    matrix = copy.deepcopy(V100_MATRIX)
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    eq["unqualified_requirements"] = eq["unqualified_requirements"][1:]  # events only
    matrix["experiments"]["B_C"]["atomic_references"] = {
        "cells": [ATOMIC], "atomicity_rule": "application_gate",
        "residual_difference": "isolation only for readers through the application"}
    return matrix


def timing_rows(matrix: dict, atomic_flag=True) -> list:
    eq = matrix["experiments"]["B_C"]["equivalent_references"]
    rows = []
    for cell_id in eq["deciding"] + eq["descriptive"] + eq["not_equivalent"]["cells"]:
        row = {"id": cell_id, "status": "PASS"}
        if frozen_report.PLANNER_EQUIVALENT.search(cell_id):
            row["atomicity_equivalent"] = cell_id not in eq["not_equivalent"]["cells"]
        rows.append(row)
    if matrix["experiments"]["B_C"].get("atomic_references"):
        rows.append({"id": ATOMIC, "status": "PASS", "atomicity_equivalent": atomic_flag,
                     "atomicity_mode": "application_gate", "reference_gated_chunks": 37,
                     "reference_split_chunks": 2})
    return rows


class Cells(unittest.TestCase):
    def test_without_the_flag_every_matrix_is_unchanged(self):
        for equivalent in (False, True):
            plain = lifecycle.matrix("final", "compact-bfs", equivalent)
            self.assertEqual(plain, lifecycle.matrix("final", "compact-bfs", equivalent, False))
            self.assertFalse(any("-atomic-" in c["id"] for c in plain))

    def test_atomic_cell_definition(self):
        base = lifecycle.matrix("final", "compact-bfs", True)
        cells = lifecycle.matrix("final", "compact-bfs", True, True)
        self.assertEqual([c["id"] for c in cells if c["id"] not in {b["id"] for b in base}], [ATOMIC])
        by_id = {c["id"]: c for c in cells}
        atomic, counterpart = by_id[ATOMIC], by_id[COUNTERPART]
        self.assertEqual((atomic["experiment"], atomic["binary"], atomic["tolerance"]), ("B4", "http", 0.25))
        self.assertEqual(atomic["tolerance"], counterpart["tolerance"])
        args = dict(zip(atomic["args"][::2], atomic["args"][1::2]))
        self.assertEqual(args["--scenario"], "ops-atomic")
        self.assertEqual(args["--requests"], "40")
        self.assertEqual(atomic["args"], [a if a != "ops" else "ops-atomic" for a in counterpart["args"]])
        # Only ops: events (and every other family, engine, topology) gets no atomic cell.
        every = lifecycle.matrix("final", "compact-bfs,ett,hdt,cluster-forest", True, True)
        self.assertEqual([c["id"] for c in every if "-atomic-" in c["id"]], [ATOMIC])
        # Pilot profile: same cell, pilot repetitions.
        pilot = {c["id"]: c for c in lifecycle.matrix("pilot", "compact-bfs", True, True)}
        self.assertIn(ATOMIC, pilot)
        # Window multipliers must cover it like any other B4 cell.
        with self.assertRaises(SystemExit):
            lifecycle.apply_multipliers(cells, {c["id"]: 1 for c in base
                                                if c["experiment"] in ("B1", "B2", "B3", "B4")})

    def test_dry_run_records_the_flag_only_when_set(self):
        import inspect
        source = inspect.getsource(lifecycle.main)
        self.assertIn('**({"atomic_references": True} if args.atomic_references else {})', source)


class Order(unittest.TestCase):
    def test_frozen_and_equivalent_orders_are_unchanged(self):
        frozen = lifecycle.matrix("final", "compact-bfs")
        q3 = lifecycle.matrix("final", "compact-bfs", True)
        both = lifecycle.matrix("final", "compact-bfs", True, True)
        for seed in (1, 50720, 2026):
            expected = list(range(len(frozen)))
            random.Random(seed).shuffle(expected)
            frozen_order = [frozen[i]["id"] for i in expected]
            q3_order = [q3[i]["id"] for i in lifecycle.run_order(q3, seed)]
            order = [both[i]["id"] for i in lifecycle.run_order(both, seed)]
            self.assertEqual(sorted(order), sorted(c["id"] for c in both))
            self.assertEqual([x for x in order if "-atomic-" not in x], q3_order)
            self.assertEqual([x for x in order if "-equivalent-" not in x and "-atomic-" not in x],
                             frozen_order)
            k = order.index(ATOMIC)
            self.assertEqual(order[k - 2:k], [COUNTERPART, EQUIVALENT])

    def test_atomic_twin_without_equivalent_follows_its_counterpart(self):
        cells = lifecycle.matrix("final", "compact-bfs", False, True)
        order = [cells[i]["id"] for i in lifecycle.run_order(cells, 7)]
        self.assertEqual(order[order.index(ATOMIC) - 1], COUNTERPART)

    def test_duplicate_or_orphan_twins_are_refused(self):
        cells = lifecycle.matrix("final", "compact-bfs", True, True)
        atomic = next(c for c in cells if c["id"] == ATOMIC)
        with self.assertRaises(SystemExit):
            lifecycle.run_order(cells + [dict(atomic)], 1)
        orphan = [c for c in cells if c["id"] != COUNTERPART]
        with self.assertRaises(SystemExit):
            lifecycle.run_order(orphan, 1)


def records(**overrides) -> list:
    out = []
    for k, i in enumerate(range(-2, 12)):
        record = {"kind": "warmup" if i < 0 else "pair", "candidate_first": k % 2 == 0,
                  "reference_ns": 4e6, "candidate_ns": 4e6 + k, "answers_agree": True,
                  "atomicity_equivalent": True, "reference_split_chunks": 2,
                  "reference_max_op_plain_ops": 1565, "atomicity_mode": "application_gate",
                  "reference_gated_chunks": 37, "reference_lifecycle_chunks": 37,
                  "gate_check": {"pass": True, "replayed_split_chunks": 2}}
        record.update(overrides)
        out.append(record)
    return out


class Analyzer(unittest.TestCase):
    CELL = {"id": ATOMIC, "binary": "http", "tolerance": 0.25, "experiment": "B4"}

    def test_copies_the_gate_records(self):
        summary = analyzer.paired(self.CELL, records())
        self.assertTrue(summary["atomicity_equivalent"])
        self.assertEqual((summary["atomicity_mode"], summary["reference_gated_chunks"],
                          summary["reference_split_chunks"], summary["gate_check_pass"]),
                         ("application_gate", 37, 2, True))

    def test_missing_or_wrong_records_are_invalid(self):
        for broken in ({"atomicity_mode": None}, {"gate_check": None}):
            with self.assertRaises(analyzer.Invalid):
                analyzer.paired(self.CELL, records(**broken))
        none = records()
        for r in none:
            del r["atomicity_equivalent"]
        with self.assertRaises(analyzer.Invalid):
            analyzer.paired(self.CELL, none)

    def test_ungated_chunks_or_failed_check_are_not_equivalent(self):
        self.assertFalse(analyzer.paired(self.CELL, records(atomicity_equivalent=False))["atomicity_equivalent"])
        self.assertFalse(analyzer.paired(self.CELL, records(reference_gated_chunks=36))["atomicity_equivalent"])
        failed = analyzer.paired(self.CELL, records(gate_check={"pass": False}))
        self.assertFalse(failed["atomicity_equivalent"])
        self.assertFalse(failed["gate_check_pass"])

    def test_equivalent_cells_are_unaffected(self):
        cell = dict(self.CELL, id=EQUIVALENT)
        plain = records()
        for r in plain:
            for key in ("atomicity_mode", "reference_gated_chunks", "reference_lifecycle_chunks", "gate_check"):
                del r[key]
            r["atomicity_equivalent"] = False
        summary = analyzer.paired(cell, plain)
        self.assertFalse(summary["atomicity_equivalent"])
        self.assertNotIn("atomicity_mode", summary)


class Report(unittest.TestCase):
    def test_historical_matrix_output_is_unchanged(self):
        out = report.report({"timing": timing_rows(V100_MATRIX)}, V100_MATRIX)
        self.assertNotIn("atomic_references", out)
        self.assertEqual(frozen_report.uncovered_not_equivalent(V100_MATRIX),
                         V100_MATRIX["experiments"]["B_C"]["equivalent_references"]["not_equivalent"]["cells"])

    def test_atomic_cell_decides(self):
        matrix = atomic_matrix()
        out = report.report({"timing": timing_rows(matrix)}, matrix)
        row = next(r for r in out["rows"] if r["id"] == ATOMIC)
        self.assertEqual((row["role"], row["status"], row["atomicity_mode"], row["reference_gated_chunks"]),
                         ("deciding", "PASS", "application_gate", 37))
        self.assertEqual(out["atomic_references"]["atomicity_rule"], "application_gate")
        self.assertEqual(out["deciding_non_pass"], [])
        # The ops hub requirement is decided by the atomic twin; events stays unqualified.
        self.assertEqual(frozen_report.uncovered_not_equivalent(matrix), [EQUIVALENT.replace("-ops-", "-events-")])
        self.assertEqual(len(out["unqualified_requirements"]), 1)
        self.assertEqual({r["id"]: r["role"] for r in out["rows"]}[EQUIVALENT], "not_equivalent")

    def test_fail_closed(self):
        matrix = atomic_matrix()
        out = report.report({"timing": timing_rows(matrix, atomic_flag=False)}, matrix)
        row = next(r for r in out["rows"] if r["id"] == ATOMIC)
        self.assertEqual((row["status"], row["measured_status"]), ("NOT_EQUIVALENT", "PASS"))
        self.assertIn(ATOMIC, {r["id"] for r in out["deciding_non_pass"]})
        self.assertFalse(out["overall"]["deciding_all_pass"])
        # A mode other than the rule's is not equivalent either.
        rows = timing_rows(matrix)
        rows[-1]["atomicity_mode"] = "plain_request"
        row = next(r for r in report.report({"timing": rows}, matrix)["rows"] if r["id"] == ATOMIC)
        self.assertEqual(row["status"], "NOT_EQUIVALENT")
        # No atomicity record at all: refused.
        rows = timing_rows(matrix)
        del rows[-1]["atomicity_equivalent"]
        with self.assertRaises(SystemExit):
            report.report({"timing": rows}, matrix)
        # Missing from the analysis: refused.
        with self.assertRaises(SystemExit):
            report.report({"timing": timing_rows(matrix)[:-1]}, matrix)

    def test_block_must_be_well_formed(self):
        for bad in ({"cells": [ATOMIC], "atomicity_rule": "plain_request"},
                    {"cells": [], "atomicity_rule": "application_gate"},
                    {"cells": [EQUIVALENT], "atomicity_rule": "application_gate"}):
            matrix = atomic_matrix()
            matrix["experiments"]["B_C"]["atomic_references"] = bad
            with self.assertRaises(SystemExit):
                frozen_report.label({"timing": timing_rows(matrix)}, matrix)

    def test_unqualified_events_requirement_is_still_required(self):
        matrix = atomic_matrix()
        matrix["experiments"]["B_C"]["equivalent_references"]["unqualified_requirements"] = []
        with self.assertRaises(SystemExit):
            report.report({"timing": timing_rows(matrix)}, matrix)


if __name__ == "__main__":
    unittest.main()
