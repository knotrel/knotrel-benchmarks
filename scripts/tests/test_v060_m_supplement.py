"""Tests for the declared v0.6.0 M supplement (matrix, validity rule, analysis).

Synthetic collector outputs reuse the helpers of test_v060_qualification.py,
with probe revision 2 fields (`item_errors`, `noop_mutations`, background
`failures`/`completed`) shaped like the real `contention-probe` output.
"""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical  # noqa: E402

historical.ensure()  # earlier campaigns are read from their release tags

import analyze_v060_m_supplement as sup  # noqa: E402
import analyze_v060_qualification as an  # noqa: E402
from test_v060_qualification import Collector, config_record  # noqa: E402

SUPP = json.loads(sup.MATRIX.read_text())
FROZEN = json.loads(an.MATRIX.read_text())


def rev2(record, item_errors=None, noop=0, background=None):
    record = dict(record)
    record.update({"item_errors": item_errors or {}, "noop_mutations": noop, "background": background})
    return record


class SupplementMatrix(unittest.TestCase):
    def test_configs_are_copies_of_frozen_configs(self):
        frozen = {s["id"]: s for s in FROZEN["experiments"]["M_desc"]["servers"]}
        for server in SUPP["M_desc_supplement"]["servers"]:
            source = frozen[server["frozen_server"]]
            for key in ("mode", "lifecycle", "nodes"):
                self.assertEqual(server[key], source[key])
            for config in server["configs"]:
                self.assertIn(config, source["configs"])
        frozen_cells = {c["id"]: c for c in FROZEN["experiments"]["M_reg"]["cells"]}
        for cell in SUPP["M_reg_supplement"]["cells"]:
            self.assertEqual(cell, frozen_cells[cell["id"]])

    def test_source_servers_keep_frozen_order(self):
        frozen = {s["id"]: s for s in FROZEN["experiments"]["M_desc"]["servers"]}
        for server in SUPP["M_desc_supplement"]["servers"]:
            if server["mode"] == "source-managed":
                self.assertEqual(server["configs"], frozen[server["frozen_server"]]["configs"])

    def test_frozen_matrix_hash_recorded(self):
        import hashlib
        self.assertEqual(SUPP["frozen_matrix_sha256"], hashlib.sha256(an.MATRIX.read_bytes()).hexdigest())


class Validity(unittest.TestCase):
    base = config_record("x", "mixed50", 16, 100, 1000, 1e-4, 1000)

    def test_valid_record(self):
        self.assertEqual(sup.validity(rev2(self.base)), [])

    def test_invalid_reasons(self):
        self.assertTrue(sup.validity(rev2(self.base, item_errors={"node_limit_exceeded": 3})))
        self.assertTrue(sup.validity(rev2(self.base, noop=1)))
        self.assertTrue(sup.validity(rev2(self.base, background={"failures": 1, "completed": 5})))
        self.assertTrue(sup.validity(rev2(self.base, background={"failures": 0, "completed": 0})))
        self.assertTrue(sup.validity(self.base))  # revision 1 record lacks the counters

    def test_refusals_alone_do_not_invalidate(self):
        record = rev2(self.base, background={"failures": 0, "completed": 640, "refused_503": 12})
        record["statuses"] = {"200": 10, "503": 5000}
        self.assertEqual(sup.validity(record), [])


class SupplementAnalysis(unittest.TestCase):
    def write_mreg(self, root, bad_cell=None):
        out = Collector(root)
        spec = SUPP["M_reg_supplement"]
        for cell in spec["cells"]:
            for index in range(spec["warmup_pairs"] + spec["pairs"]):
                phase = "warmup" if index < spec["warmup_pairs"] else "analyzed"
                for arm in ("ref", "cand"):
                    noop = 1 if (cell["id"] == bad_cell and phase == "analyzed" and index == 5 and arm == "cand") else 0
                    record = rev2(config_record(cell["id"], "read100", 16, 200 + index, 90_000_000 + index,
                                                1e-2, 80_000_000), noop=noop)
                    out.child(f"{cell['id']}-{phase}-{index:02d}-{arm}", [record])
        out.finish()

    def test_mreg_valid_cells_get_verdicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write_mreg(tmp)
            result = sup.analyze_supplement_mreg(Path(tmp), SUPP)
            self.assertEqual({v["verdict"] for v in result.values()}, {"PASS"})

    def test_mreg_invalid_observation_voids_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = SUPP["M_reg_supplement"]["cells"][0]["id"]
            self.write_mreg(tmp, bad_cell=bad)
            result = sup.analyze_supplement_mreg(Path(tmp), SUPP)
            self.assertEqual(result[bad]["verdict"], "INVALID")
            other = SUPP["M_reg_supplement"]["cells"][1]["id"]
            self.assertEqual(result[other]["verdict"], "PASS")

    def test_mdesc_flags_invalid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Collector(tmp)
            out.child("S-source-off-100k", [
                rev2(config_record("a", "read100", 16, 200, 1000, 1e-4, 1000),
                     background={"kind": "events", "failures": 0, "completed": 640}),
                rev2(config_record("b", "read100", 16, 200, 1000, 1e-4, 1000),
                     background={"kind": "events", "failures": 1, "completed": 0}),
            ])
            out.finish()
            result = sup.analyze_supplement_mdesc(Path(tmp))
            self.assertEqual(result["invalid_configs"], ["S-source-off-100k/b"])


if __name__ == "__main__":
    unittest.main()
