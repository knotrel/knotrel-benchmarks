"""Tests for amendment 4: contention-probe revision 3 (bounded ETag refresh,
412 retry, import accounting) and the amendment 4 validity rule.

The probe's own behaviour is unit-tested in Rust against a stub server
(`tools/contention-probe/src/main.rs`, `mod tests`); these tests pin the
source-level contract and the analyzer rule.
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_v060_m_supplement as supplement  # noqa: E402
import analyze_v060_qualification as frozen_v060  # noqa: E402

# Importing the amendment 4 wrapper rebinds module globals (the analyzers'
# MATRIX and the supplement's validity), as its command line needs. Other test
# modules share those modules, so they are restored right after the import.
_first_loaded = "analyze_v070_qualification" in sys.modules
_saved = (frozen_v060.MATRIX, supplement.validity,
          sys.modules["analyze_v070_qualification"].MATRIX if _first_loaded else None)
import analyze_v070r_a4 as a4  # noqa: E402
INSTALLED_VALIDITY = supplement.validity
frozen_v060.MATRIX, supplement.validity = _saved[0], _saved[1]
if _first_loaded:
    sys.modules["analyze_v070_qualification"].MATRIX = _saved[2]
else:  # first loaded by the wrapper: restore its own module-level binding
    import analyze_v070_qualification as _first  # noqa: E402
    _first.MATRIX = ROOT / "results" / "v0.7.0-qualification" / "MATRIX.json"

PROBE = (ROOT / "tools" / "contention-probe" / "src" / "main.rs").read_text()
PROTOCOL = (ROOT / "results" / "v0.7.0-requalification" / "PROTOCOL.md").read_text()


def config(background=None, **extra):
    record = {"kind": "config", "errors": 0, "item_errors": {}, "noop_mutations": 0, "background": background}
    record.update(extra)
    return record


def imports(**overrides):
    base = {"stats_attempts": 1, "stats_refused_503": 0, "stats_io_errors": 0, "refreshes": 1,
            "refresh_exhausted": 0, "refresh_latency_p50_ns": 400000, "refresh_latency_max_ns": 400000,
            "imports_attempted": 6, "imports_completed": 6, "precondition_412": 0, "retries": 0,
            "precondition_after_refresh": 0, "import_starved": False}
    base.update(overrides)
    return base


def import_background(**overrides):
    background = {"kind": "import", "completed": 6, "failures": 0, "refused_503": 0, "failure_kinds": {},
                  "p50_ns": 1, "max_ns": 1, "imports": imports()}
    background.update(overrides)
    return background


class ProbeRevision3(unittest.TestCase):
    def test_revision_and_bounds(self):
        self.assertIn("const PROBE_REVISION: u32 = 3;", PROBE)
        self.assertIn("const REFRESH_ATTEMPTS: u32 = 12;", PROBE)
        self.assertIn("Duration::from_millis(10u64 << attempt.min(4))", PROBE)

    def test_initial_refresh_is_bounded_and_recorded(self):
        start = PROBE.index('if background == "import" {\n                // The stored ETag may be stale')
        block = PROBE[start:start + 800]
        self.assertIn("imports.record(refresh_etag(&mut conn, address))", block)
        self.assertIn('"refresh-exhausted"', block)
        self.assertIn("failures += 1", block)
        # The unretried single stats request of revision 2 is gone.
        self.assertNotIn('match conn.request("GET", "/v1/stats", &[], b"") {\n                    Ok((200, headers, _)) => {\n                        if let Some', PROBE)

    def test_imports_go_through_the_refresh_and_retry_path(self):
        code = PROBE[:PROBE.index("#[cfg(test)]")]
        self.assertEqual(code.count("import_with_refresh("), 2)  # definition and the one call site
        body = PROBE[PROBE.index("fn import_with_refresh("):PROBE.index("/// Source-managed state shared")]
        self.assertEqual(body.count('post_feeder(conn, feeder, "/v1/feeder/import"'), 2)  # one retry at most
        self.assertIn("imports.precondition_after_refresh += 1", body)

    def test_summary_fields(self):
        for key in ("stats_attempts", "stats_refused_503", "refreshes", "refresh_exhausted",
                    "refresh_latency_p50_ns", "refresh_latency_max_ns", "imports_attempted",
                    "imports_completed", "precondition_412", "retries", "precondition_after_refresh",
                    "import_starved"):
            self.assertRegex(PROBE, rf'"{key}":')
        self.assertIn('summary["imports"] = imports.summary(count);', PROBE)

    def test_rust_unit_tests_cover_the_declared_cases(self):
        names = set(re.findall(r"fn (\w+)\(\)", PROBE[PROBE.index("mod tests"):]))
        for name in ("refresh_retries_503_then_reads_the_etag", "persistent_503_exhausts_the_refresh",
                     "a_412_refreshes_and_the_retry_succeeds", "a_412_after_refresh_is_a_recorded_failure",
                     "a_412_with_an_exhausted_refresh_is_not_retried", "fewer_completed_than_attempted_is_starved"):
            self.assertIn(name, names)


class Amendment4Validity(unittest.TestCase):
    def test_installed_over_the_frozen_rule(self):
        self.assertIs(INSTALLED_VALIDITY, a4.validity)
        self.assertIs(a4.FROZEN_VALIDITY, supplement.validity)  # restored for the other test modules
        self.assertIsNot(a4.FROZEN_VALIDITY, a4.validity)

    def test_frozen_reasons_still_apply(self):
        record = config(errors=2, background=import_background(failures=1, failure_kinds={"412 x": 1}))
        reasons = a4.validity(record)
        for reason in a4.FROZEN_VALIDITY(record):
            self.assertIn(reason, reasons)

    def test_non_import_records_are_unchanged(self):
        for background in (None, {"kind": "events", "completed": 10, "failures": 0}):
            record = config(background=background)
            self.assertEqual(a4.validity(record), a4.FROZEN_VALIDITY(record))

    def test_valid_revision_3_import(self):
        self.assertEqual(a4.validity(config(background=import_background())), [])

    def test_starved_import_is_invalid(self):
        for overrides in ({"refresh_exhausted": 1}, {"precondition_after_refresh": 1},
                          {"imports_attempted": 6, "imports_completed": 5}):
            background = import_background(imports=imports(import_starved=True, **overrides))
            reasons = a4.validity(config(background=background))
            self.assertTrue(any(r.startswith("import_starved") for r in reasons), overrides)

    def test_missing_or_unknown_starvation_flag_is_invalid(self):
        background = import_background()
        del background["imports"]
        self.assertIn("missing background imports (probe revision < 3)", a4.validity(config(background=background)))
        no_flag = imports()
        del no_flag["import_starved"]
        reasons = a4.validity(config(background=import_background(imports=no_flag)))
        self.assertTrue(any(r.startswith("import_starved") for r in reasons))

    def test_a3_3_record_shape_stays_invalid(self):
        # a3-3's c64-import row: probe revision 2, six 412s, stats-503.
        background = {"kind": "import", "completed": 0, "failures": 6, "refused_503": 0,
                      "failure_kinds": {"412 precondition_failed": 6, "stats-503": 1}, "p50_ns": 1, "max_ns": 1}
        reasons = a4.validity(config(background=background))
        self.assertTrue(any(r.startswith("background failures=6") for r in reasons))
        self.assertIn("background completed=0", reasons)
        self.assertIn("missing background imports (probe revision < 3)", reasons)


class Protocol(unittest.TestCase):
    def test_section_11_scope(self):
        section = PROTOCOL[PROTOCOL.index("## 11. Amendment 4"):]
        for needle in ("future collections", "a3-3", "INVALID", "analyze_v070r_a4.py", "REFRESH_ATTEMPTS",
                       "import_starved", "FREEZE-A4.json"):
            self.assertIn(needle, section)


if __name__ == "__main__":
    unittest.main()
