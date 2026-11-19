"""Tests for report_v070r_cell_conformance.py (per-cell conformance from the gate records)."""

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import report_v070r_cell_conformance as rc  # noqa: E402
from test_v070r_interference import Camp, child  # noqa: E402

END = {"gated": {"r": 2, "mdesc": 1}, "collected": {"r": 2, "mdesc": 1}, "reasons": []}


def camp(children, first="CONFORMING: every gate check passed", end=END, stop=False):
    c = Camp(children)
    (c.path / "logs").mkdir()
    (c.path / "logs/CONFORMANCE.txt").write_text(first + "\n")
    if end is not None:
        (c.path / "logs/end-checks.txt").write_text(repr(end) + "\n")
    if stop:
        (c.path / "gate/gate-stop.json").write_text("{}")
    return c


class CellConformance(unittest.TestCase):
    children = [child("r:R-x-warmup-00-ref", 1, 2), child("r:R-x-analyzed-00-cand", 3, 4), child("mdesc:M-a", 5, 6)]

    def test_all_conforming(self):
        c = camp(self.children)  # keep the temporary directory alive
        rep = rc.report(c.path)
        self.assertEqual((rep["attempt_status"], rep["cells"], rep["cells_conforming"]), ("CONFORMING", 2, 2))
        self.assertEqual(rep["by_experiment"]["r"], {"cells": 1, "conforming": 1, "children": 2})
        self.assertTrue(rep["quiet_period_conforming"])

    def test_one_nonconforming_child_marks_its_cell_only(self):
        bad = dict(self.children[1], conforming=False, reasons=["forbidden: /x"])
        c = camp([self.children[0], bad, self.children[2]])
        rep = rc.report(c.path)
        st = {r["cell"]: r["status"] for r in rep["rows"]}
        self.assertEqual(st, {"R-x": "NONCONFORMING", "M-a": "CONFORMING"})

    def test_attempt_level_failures_mark_every_cell(self):
        for c in (camp(self.children, first="NONCONFORMING: quiet period"),
                  camp(self.children, end=None),
                  camp(self.children, end={**END, "collected": {"r": 1, "mdesc": 1}}),
                  camp(self.children, stop=True)):
            rep = rc.report(c.path)
            self.assertEqual(rep["attempt_status"], "NONCONFORMING")
            self.assertEqual(rep["cells_conforming"], 0)

    def test_markdown_lists_nonconforming_cells(self):
        bad = dict(self.children[2], conforming=False, reasons=["hid reset"])
        c = camp([*self.children[:2], bad])
        md = rc.markdown(rc.report(c.path))
        self.assertIn("1 of 2 cells CONFORMING", md)
        self.assertIn("`M-a`", md)


if __name__ == "__main__":
    unittest.main()
