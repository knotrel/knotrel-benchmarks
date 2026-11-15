"""Tests for scripts/analyze_bc_qualification.py.

Synthetic tests build raw pair records in the format written by run_p0_aa.py. The
reproduction tests recompute the retained v0.3.0 campaign from its raw records and compare
the result with the decision reports retained next to them; they are skipped when that
evidence directory is not present. No expected value is encoded in the analysis itself.
"""

import copy
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import analyze_bc_qualification as bc  # noqa: E402
import run_p0_aa as p0  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
V030 = ROOT.parent / "evidence/v0.3.0-qualification-20261112T224213Z-6a1267f"
CORE = "core_sustained_churn_10k_compact-bfs_warmed"
BATCH = "http_standalone_batch_b8_compact_bfs"
LIFECYCLE = "http_lifecycle_compact_bfs_small"
SPARSE_WS = "core_sparse_traversal_10k_compact-workspace_warmed"


PHASE_START_NS = {"main": 10**18, "extension": 2 * 10**18}


def observation(cell_id, pair_id, label, metrics, position=0, session=0, phase="main"):
    """One parsed_valid observation; ``metrics`` maps metric name to value."""
    family = bc.family_of(cell_id)
    obs = {"cell_id": cell_id, "pair_id": pair_id, "label": label, "status": "parsed_valid",
           "exit_code": 0, "timed_out": False, "error": None, "pair_position": position,
           "session": session, "launch_unix_ns": PHASE_START_NS[phase] + pair_id * 1000 + position * 10,
           "completion_unix_ns": PHASE_START_NS[phase] + pair_id * 1000 + position * 10 + 5,
           "binary_identity": {"sha256": f"{label}-{family}"}}
    if family == "core":
        obs["peak_rss_bytes"] = metrics["peak_rss_bytes"]
        obs["parsed_metrics"] = {
            "workload_wall_ns": metrics["workload_wall_ns"],
            "trace_fingerprint_fnv1a64": "f00d",
            "measurements": {op: {"p99_ns": metrics[f"{op}_p99_ns"]} for op in ("connected", "link", "cut")},
        }
    else:
        exported = {k: v for k, v in metrics.items()}
        if family == "standalone-batch":
            exported["all_items_matched"] = True
        else:
            exported["oracle_agreement_pct"] = 100.0
        obs["parsed_metrics"] = {"exported_metrics": exported}
    return obs


def baseline_metrics(cell_id):
    return {name: 1000.0 for name, _, _ in bc.FAMILIES[bc.family_of(cell_id)]}


def write_manifest(directory, phase):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "manifest.json").write_text(json.dumps({"pilot_design": {"phase": phase}}))


def write_cell(directory, cell_id, ratios, first_pair_id=0, overrides=None, phase="main"):
    """Write len(ratios) pairs. ``ratios`` maps metric name to a list of C/B ratios
    (metrics not listed get ratio 1.0); ``overrides`` edits one pair's raw record."""
    directory = Path(directory)
    write_manifest(directory, phase)
    count = len(next(iter(ratios.values())))
    for i in range(count):
        pair_id = first_pair_id + i
        base = baseline_metrics(cell_id)
        cand = {name: base[name] * ratios.get(name, [1.0] * count)[i] for name in base}
        # Balanced design: sessions of four pairs, alternating B->C and C->B.
        labels = ["B", "C"] if i % 2 == 0 else ["C", "B"]
        session = (i // 4) % 3
        values = {"B": base, "C": cand}
        record = {"cell_id": cell_id, "pair_id": pair_id, "session": session, "labels": labels,
                  "observations": [observation(cell_id, pair_id, label, values[label], position, session, phase)
                                   for position, label in enumerate(labels)]}
        if overrides and i in overrides:
            overrides[i](record)
        (directory / f"pair_{pair_id:03d}_{cell_id}.json").write_text(json.dumps(record))


def write_matrix(directory, ratios_by_cell, overrides_by_cell=None):
    """Write 12 pairs for each of the nine approved cells; unlisted cells have ratio 1.0."""
    overrides_by_cell = overrides_by_cell or {}
    for index, cell_id in enumerate(p0.QUALIFICATION_CELL_IDS):
        ratios = ratios_by_cell.get(cell_id) or {primary(cell_id): [1.0] * 12}
        write_cell(directory, cell_id, ratios, first_pair_id=12 * index,
                   overrides=overrides_by_cell.get(cell_id))


def cell_of(report, cell_id, key="cells"):
    return next(c for c in report[key] if c["cell_id"] == cell_id)


def metric_of(cell, name):
    return next(m for m in [cell["primary"]] + cell["supporting"] if m["metric"] == name)


def set_session(record, session):
    """Move a pair to another session consistently (record and observations)."""
    record["session"] = session
    for obs in record["observations"]:
        obs["session"] = session


def swap_order(record):
    """Reverse a pair's launch order consistently (labels, positions, launch times)."""
    record["labels"].reverse()
    observations = record["observations"]
    times = [(obs["launch_unix_ns"], obs["completion_unix_ns"]) for obs in observations]
    observations.reverse()
    for position, obs in enumerate(observations):
        obs["pair_position"] = position
        obs["launch_unix_ns"], obs["completion_unix_ns"] = times[position]


def spread(center_pct, half_width_pct, n=12):
    """n ratios whose log values are evenly spaced around ln(1 + center)."""
    center = math.log1p(center_pct / 100)
    half = math.log1p(half_width_pct / 100)
    return [math.exp(center - half + 2 * half * i / (n - 1)) for i in range(n)]


def primary(cell_id):
    return bc.FAMILIES[bc.family_of(cell_id)][0][0]


class IntervalAndThresholdTest(unittest.TestCase):
    def test_order_statistics_n12_and_n24(self):
        values = [{"B": 1.0, "C": math.exp(x / 100)} for x in range(12, 0, -1)]
        s = bc.summarize_metric("m", values, 0.10)
        self.assertAlmostEqual(s["interval_log"][0], 0.03)
        self.assertAlmostEqual(s["interval_log"][1], 0.10)
        self.assertAlmostEqual(s["median_log_ratio"], 0.065)
        values24 = [{"B": 1.0, "C": math.exp(x / 100)} for x in range(1, 25)]
        s24 = bc.summarize_metric("m", values24, 0.10)
        self.assertAlmostEqual(s24["interval_log"][0], 0.07)
        self.assertAlmostEqual(s24["interval_log"][1], 0.18)

    def test_other_sample_sizes_are_refused(self):
        for n in (11, 13, 23, 36):
            with self.assertRaises(bc.AnalysisError):
                bc.summarize_metric("m", [{"B": 1.0, "C": 1.0}] * n, 0.10)

    def test_classification_boundaries(self):
        t = math.log(1.0 + 0.10)  # the script's threshold
        self.assertEqual(bc.classify(-0.1, t, t), bc.PASS)  # upper equal to t passes
        self.assertEqual(bc.classify(t, t + 1e-12, t), bc.INCONCLUSIVE)  # lower equal to t is not a regression
        self.assertEqual(bc.classify(t + 1e-12, 1.0, t), bc.REGRESSION)
        self.assertEqual(bc.classify(-1.0, 1.0, t), bc.INCONCLUSIVE)

    def test_tolerances_per_metric_kind(self):
        tol = {name: key for name, _, key in bc.FAMILIES["core"]}
        self.assertEqual(tol["workload_wall_ns"], "primary")
        self.assertEqual(tol["cut_p99_ns"], "query_tail")
        self.assertEqual(tol["peak_rss_bytes"], "rss")
        self.assertEqual(bc.TOLERANCES, {"primary": 0.10, "query_tail": 0.25, "rss": 0.20})
        # A +15% p99 passes its 25% tolerance; the same shift fails the 10% primary one.
        values = [{"B": 1.0, "C": 1.15}] * 12
        self.assertEqual(bc.summarize_metric("p99", values, 0.25)["status"], bc.PASS)
        self.assertEqual(bc.summarize_metric("primary", values, 0.10)["status"], bc.REGRESSION)

    def test_percent_conversion(self):
        s = bc.summarize_metric("m", [{"B": 2.0, "C": 2.2}] * 12, 0.10)
        self.assertAlmostEqual(s["median_change_pct"], 10.0)
        self.assertAlmostEqual(s["ratio_of_medians_change_pct"], 10.0)
        self.assertEqual(s["status"], bc.PASS)  # exactly at tolerance


class CellDecisionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def run_cell(self, cell_id, main_ratios, extension_ratios=None, rules="v0.4.0"):
        write_matrix(self.root / "main", {cell_id: main_ratios})
        if extension_ratios is None:
            return cell_of(bc.analyze(self.root / "main", None, rules), cell_id)
        write_cell(self.root / "ext", cell_id, extension_ratios, first_pair_id=100, phase="extension")
        return cell_of(bc.analyze(self.root / "main", self.root / "ext", rules), cell_id)

    def test_all_pass(self):
        cell = self.run_cell(BATCH, {primary(BATCH): spread(0, 3)})
        self.assertEqual(cell["status"], bc.PASS)
        self.assertFalse(cell["extension_required"])

    def test_primary_regression(self):
        cell = self.run_cell(BATCH, {primary(BATCH): spread(25, 5)})
        self.assertEqual(cell["status"], bc.REGRESSION)

    def test_supporting_regression_is_not_overridden_by_primary(self):
        for rules in bc.RULESETS:
            with self.subTest(rules=rules):
                self.root = Path(tempfile.mkdtemp(dir=self.tmp.name))
                cell = self.run_cell(BATCH, {primary(BATCH): spread(-20, 2),
                                             "request_latency_p99_ns": spread(60, 5)}, rules=rules)
                self.assertEqual(cell["primary_status"], bc.PASS)
                self.assertEqual(cell["status"], bc.REGRESSION)
                self.assertEqual(cell["supporting_regressions"], ["request_latency_p99_ns"])

    def test_v040_supporting_inconclusive_blocks_pass_and_requires_extension(self):
        cell = self.run_cell(BATCH, {primary(BATCH): spread(0, 3),
                                     "sampled_max_rss_bytes": spread(5, 30)})
        self.assertEqual(cell["primary_status"], bc.PASS)
        self.assertEqual(cell["status"], bc.INCONCLUSIVE)
        self.assertTrue(cell["extension_required"])

    def test_v030_supporting_inconclusive_is_reported_only(self):
        cell = self.run_cell(BATCH, {primary(BATCH): spread(0, 3),
                                     "sampled_max_rss_bytes": spread(5, 30)}, rules="v0.3.0")
        self.assertEqual(cell["status"], bc.PASS)
        self.assertFalse(cell["extension_required"])

    def test_v040_disclosure_requires_every_supporting_metric_to_pass(self):
        wide = {primary(LIFECYCLE): spread(5, 30)}
        cell = self.run_cell(LIFECYCLE, wide, extension_ratios={primary(LIFECYCLE): spread(5, 30)})
        self.assertEqual(cell["pairs"], 24)
        self.assertEqual(cell["status"], bc.INCONCLUSIVE_DISCLOSED)

    def test_v040_primary_inconclusive_with_supporting_inconclusive_is_unresolved(self):
        ratios = {primary(LIFECYCLE): spread(5, 30), "query_latency_p99_ns": spread(10, 40)}
        cell = self.run_cell(LIFECYCLE, ratios, extension_ratios=copy.deepcopy(ratios))
        self.assertEqual(cell["status"], bc.UNRESOLVED)

    def test_v040_primary_pass_with_supporting_inconclusive_after_extension_is_unresolved(self):
        ratios = {primary(LIFECYCLE): spread(0, 3), "query_latency_p99_ns": spread(10, 40)}
        cell = self.run_cell(LIFECYCLE, ratios, extension_ratios=copy.deepcopy(ratios))
        self.assertEqual(cell["status"], bc.UNRESOLVED)

    def test_inconclusive_with_median_above_tolerance_after_extension_is_regression(self):
        ratios = {primary(LIFECYCLE): spread(12, 30)}
        for rules in bc.RULESETS:
            with self.subTest(rules=rules):
                self.root = Path(tempfile.mkdtemp(dir=self.tmp.name))
                cell = self.run_cell(LIFECYCLE, ratios, extension_ratios=ratios, rules=rules)
                self.assertEqual(cell["status"], bc.REGRESSION if rules == "v0.4.0" else bc.INCONCLUSIVE)
                if rules == "v0.3.0":
                    self.assertEqual(cell["extension_disposition"], bc.D6_REGRESSION)

    def test_v030_disclosure_after_extension(self):
        ratios = {primary(LIFECYCLE): spread(5, 30)}
        cell = self.run_cell(LIFECYCLE, ratios, extension_ratios=ratios, rules="v0.3.0")
        self.assertEqual(cell["extension_disposition"], bc.D6_PERMITTED)

    def test_inconclusive_cell_without_extension_data_is_refused(self):
        write_matrix(self.root / "main", {LIFECYCLE: {primary(LIFECYCLE): spread(5, 30)},
                                          BATCH: {primary(BATCH): spread(0, 30)}})
        write_cell(self.root / "ext", BATCH, {primary(BATCH): spread(0, 2)}, first_pair_id=100, phase="extension")
        with self.assertRaisesRegex(bc.AnalysisError, "differ from required"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")

    def test_extension_must_contain_exactly_the_required_cells(self):
        write_matrix(self.root / "main", {LIFECYCLE: {primary(LIFECYCLE): spread(5, 30)}})
        write_cell(self.root / "ext", LIFECYCLE, {primary(LIFECYCLE): spread(5, 30, n=6)}, first_pair_id=100, phase="extension")
        with self.assertRaisesRegex(bc.AnalysisError, "expected 12"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")
        self.root = Path(tempfile.mkdtemp(dir=self.tmp.name))
        write_matrix(self.root / "main", {LIFECYCLE: {primary(LIFECYCLE): spread(5, 30)}})
        write_cell(self.root / "ext", LIFECYCLE, {primary(LIFECYCLE): spread(5, 30)}, first_pair_id=100, phase="extension")
        write_cell(self.root / "ext", BATCH, {primary(BATCH): spread(0, 2)}, first_pair_id=200, phase="extension")
        with self.assertRaisesRegex(bc.AnalysisError, "differ from required"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")

    def test_main_report_lists_extension_cells(self):
        write_matrix(self.root / "main", {LIFECYCLE: {primary(LIFECYCLE): spread(5, 30)},
                                          CORE: {primary(CORE): spread(0, 2)}})
        report = bc.analyze(self.root / "main", None, "v0.4.0")
        self.assertEqual(report["phase"], "main")
        self.assertEqual(report["extension_cells_required"], [LIFECYCLE])

    def test_v040_final_report_keeps_the_n12_decision(self):
        ratios = {primary(LIFECYCLE): spread(5, 30)}
        write_matrix(self.root / "main", {LIFECYCLE: ratios})
        write_cell(self.root / "ext", LIFECYCLE, ratios, first_pair_id=100, phase="extension")
        report = bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")
        self.assertEqual(cell_of(report, LIFECYCLE, "main_cells")["pairs"], 12)
        self.assertEqual(cell_of(report, LIFECYCLE, "main_cells")["status"], bc.INCONCLUSIVE)
        self.assertEqual(cell_of(report, LIFECYCLE)["pairs"], 24)
        self.assertEqual(len(report["main_cells"]), 9)


class CrossPhaseTest(unittest.TestCase):
    """The extension must be new, later data from the same binaries."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.ratios = {primary(LIFECYCLE): spread(5, 30)}
        write_matrix(self.root / "main", {LIFECYCLE: self.ratios})

    def tearDown(self):
        self.tmp.cleanup()

    def test_valid_extension_is_accepted_with_input_provenance(self):
        write_cell(self.root / "ext", LIFECYCLE, self.ratios, first_pair_id=100, phase="extension")
        report = bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")
        self.assertEqual(report["inputs"]["main"]["pair_files"], 108)
        self.assertEqual(report["inputs"]["extension"]["pair_files"], 12)
        self.assertEqual(len(report["inputs"]["script_sha256"]), 64)
        self.assertNotIn("extension_pair_ids_overlap_main", report)

    def test_same_directory_is_refused(self):
        with self.assertRaisesRegex(bc.AnalysisError, "is the main directory"):
            bc.analyze(self.root / "main", self.root / "main", "v0.3.0")

    def test_copied_main_observations_are_refused(self):
        ext = self.root / "ext"
        write_manifest(ext, "extension")
        for path in self.root.glob(f"main/pair_*_{LIFECYCLE}.json"):
            shutil.copyfile(path, ext / path.name)
        with self.assertRaisesRegex(bc.AnalysisError, "identical to|same launch time|before the main phase"):
            bc.analyze(self.root / "main", ext, "v0.3.0")

    def test_copied_main_pairs_with_new_ids_and_times_shifted_are_refused(self):
        def shifted_copy(r):  # a main observation re-labelled as extension: same launch time
            for obs in r["observations"]:
                obs["launch_unix_ns"] -= 10**18
                obs["completion_unix_ns"] -= 10**18
        write_cell(self.root / "ext", LIFECYCLE, self.ratios, first_pair_id=100, phase="extension",
                   overrides={0: shifted_copy})
        with self.assertRaisesRegex(bc.AnalysisError, "before the main phase ended"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.3.0")

    def test_extension_overlapping_a_running_main_observation_is_refused(self):
        last_main = max(json.loads(f.read_text())["observations"][1]["launch_unix_ns"]
                        for f in (self.root / "main").glob("pair_*.json"))

        def just_after_last_launch(r):
            for k, obs in enumerate(r["observations"]):
                obs["launch_unix_ns"] = last_main + 1 + k * 10 + (r["pair_id"] - 100) * 100
                obs["completion_unix_ns"] = obs["launch_unix_ns"] + 5
        write_cell(self.root / "ext", LIFECYCLE, self.ratios, first_pair_id=100, phase="extension",
                   overrides={i: just_after_last_launch for i in range(12)})
        with self.assertRaisesRegex(bc.AnalysisError, "before the main phase ended"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.3.0")

    def test_extension_launched_before_main_ended_is_refused(self):
        def early(r):
            for obs in r["observations"]:
                obs["launch_unix_ns"] -= 2 * 10**18 - 10**17
                obs["completion_unix_ns"] -= 2 * 10**18 - 10**17
        write_cell(self.root / "ext", LIFECYCLE, self.ratios, first_pair_id=100, phase="extension",
                   overrides={i: early for i in range(12)})
        with self.assertRaisesRegex(bc.AnalysisError, "before the main phase ended"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.3.0")

    def test_extension_with_other_binaries_is_refused(self):
        def rebuilt(r):
            for obs in r["observations"]:
                if obs["label"] == "C":
                    obs["binary_identity"] = {"sha256": "rebuilt"}
        write_cell(self.root / "ext", LIFECYCLE, self.ratios, first_pair_id=100, phase="extension",
                   overrides={i: rebuilt for i in range(12)})
        with self.assertRaisesRegex(bc.AnalysisError, "binary identity"):
            bc.analyze(self.root / "main", self.root / "ext", "v0.4.0")


class ReportOnlyTest(unittest.TestCase):
    """Decision G3a-1: core link/cut p99 are reported without a verdict, under v0.4.0 only."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def analyze(self, ratios_by_cell, rules="v0.4.0"):
        directory = Path(tempfile.mkdtemp(dir=self.tmp.name))
        write_matrix(directory, ratios_by_cell)
        return bc.analyze(directory, None, rules)

    def test_exclusion_list_is_exactly_core_link_and_cut(self):
        core_cells = [c for c in p0.QUALIFICATION_CELL_IDS if bc.family_of(c) == "core"]
        self.assertEqual(sorted(bc.REPORT_ONLY), sorted(core_cells))
        self.assertEqual(len(core_cells), 4)
        for metrics in bc.REPORT_ONLY.values():
            self.assertEqual(metrics, ("link_p99_ns", "cut_p99_ns"))
        core_metrics = [name for name, _, _ in bc.FAMILIES["core"]]
        self.assertTrue(set(bc.REPORT_ONLY[SPARSE_WS]) <= set(core_metrics))

    def test_report_only_metric_never_passes_and_carries_no_verdict(self):
        cell = cell_of(self.analyze({}), SPARSE_WS)  # every ratio 1.0: would be PASS if gated
        self.assertEqual(cell["status"], bc.PASS)
        self.assertEqual(cell["report_only_metrics"], ["link_p99_ns", "cut_p99_ns"])
        for name in ("link_p99_ns", "cut_p99_ns"):
            metric = metric_of(cell, name)
            self.assertEqual(metric["status"], bc.REPORT_ONLY_STATUS)
            self.assertFalse(metric["gated"])
            for key in ("tolerance_pct", "tolerance_log", "lower_bound_exceeds_tolerance",
                        "median_exceeds_tolerance"):
                self.assertIsNone(metric[key], key)

    def test_report_only_values_are_kept_and_do_not_drive_the_outcome(self):
        quantized = [2.0 if i % 3 else 1.0 for i in range(12)]  # one-tick steps: +100%
        cell = cell_of(self.analyze({SPARSE_WS: {primary(SPARSE_WS): [1.0] * 12,
                                                 "link_p99_ns": [3.0] * 12,
                                                 "cut_p99_ns": quantized}}), SPARSE_WS)
        self.assertEqual(cell["status"], bc.PASS)
        self.assertFalse(cell["extension_required"])
        self.assertEqual(cell["supporting_regressions"], [])
        link = metric_of(cell, "link_p99_ns")
        self.assertAlmostEqual(link["median_change_pct"], 200.0)
        self.assertAlmostEqual(link["interval_pct"][0], 200.0)
        self.assertEqual(len(link["pair_values"]), 12)
        self.assertEqual(link["pair_values"][0]["C"] / link["pair_values"][0]["B"], 3.0)

    def test_other_core_supporting_metrics_stay_strict(self):
        for name in ("connected_p99_ns", "peak_rss_bytes"):
            with self.subTest(metric=name):
                cell = cell_of(self.analyze({SPARSE_WS: {primary(SPARSE_WS): [1.0] * 12,
                                                         name: spread(5, 40)}}), SPARSE_WS)
                self.assertEqual(metric_of(cell, name)["status"], bc.INCONCLUSIVE)
                self.assertTrue(metric_of(cell, name)["gated"])
                self.assertEqual(cell["status"], bc.INCONCLUSIVE)
                self.assertTrue(cell["extension_required"])

    def test_http_p99_is_not_exempt(self):
        for cell_id, name in ((BATCH, "request_latency_p99_ns"), (LIFECYCLE, "query_latency_p99_ns")):
            with self.subTest(cell=cell_id):
                cell = cell_of(self.analyze({cell_id: {primary(cell_id): [1.0] * 12,
                                                       name: spread(5, 60)}}), cell_id)
                self.assertEqual(cell["report_only_metrics"], [])
                self.assertEqual(metric_of(cell, name)["status"], bc.INCONCLUSIVE)
                self.assertEqual(cell["status"], bc.INCONCLUSIVE)

    def test_report_lists_the_exclusions(self):
        report = self.analyze({})
        self.assertEqual(report["report_only"]["metrics_by_cell"],
                         {c: list(m) for c, m in bc.REPORT_ONLY.items()})
        self.assertIn("timer", report["report_only"]["reason"])

    def test_v030_rules_are_unchanged(self):
        ratios = {SPARSE_WS: {primary(SPARSE_WS): [1.0] * 12, "cut_p99_ns": [3.0] * 12}}
        v030 = cell_of(self.analyze(ratios, rules="v0.3.0"), SPARSE_WS)
        self.assertEqual(v030["status"], bc.REGRESSION)
        self.assertEqual(v030["supporting_regressions"], ["cut_p99_ns"])
        self.assertNotIn("report_only_metrics", v030)
        self.assertEqual(metric_of(v030, "cut_p99_ns")["status"], bc.REGRESSION)
        self.assertNotIn("report_only", self.analyze(ratios, rules="v0.3.0"))


class InvalidDataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name) / "main"

    def tearDown(self):
        self.tmp.cleanup()

    def assert_refused(self, cell_id, mutate, message):
        write_cell(self.dir, cell_id, {primary(cell_id): spread(0, 2)}, overrides={4: mutate})
        with self.assertRaisesRegex(bc.AnalysisError, message):
            bc.analyze(self.dir, None, "v0.4.0")

    def test_empty_directory(self):
        write_manifest(self.dir, "main")
        with self.assertRaisesRegex(bc.AnalysisError, "No pair"):
            bc.load_pairs(self.dir, "main")

    def test_missing_metric(self):
        self.assert_refused(BATCH, lambda r: r["observations"][1]["parsed_metrics"]["exported_metrics"]
                            .pop("request_latency_p99_ns"), "missing field")

    def test_non_positive_non_finite_and_non_numeric_values(self):
        for bad in (0, -5, float("nan"), float("inf"), "12", None, True):
            with self.subTest(bad=bad):
                self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"

                def mutate(r, bad=bad):
                    r["observations"][0]["parsed_metrics"]["exported_metrics"]["window_duration_ns"] = bad
                with self.assertRaises(bc.AnalysisError):
                    write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: mutate})
                    bc.analyze(self.dir, None, "v0.4.0")

    def test_process_failures(self):
        mutations = {
            "status": lambda r: r["observations"][0].update(status="capture_failed"),
            "exit": lambda r: r["observations"][0].update(exit_code=1),
            "timeout": lambda r: r["observations"][1].update(timed_out=True),
            "error": lambda r: r["observations"][1].update(error="boom"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
                self.assert_refused(CORE, mutate, "status|process failure")

    def test_label_problems(self):
        self.assert_refused(CORE, lambda r: r["observations"][1].update(label="B"), "exactly one B and one C")
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        self.assert_refused(CORE, lambda r: r["observations"].pop(), "exactly 2 observations")

    def test_identity_mismatch(self):
        self.assert_refused(CORE, lambda r: r["observations"][0].update(pair_id=999), "identity")

    def test_correctness_guardrails(self):
        self.assert_refused(CORE, lambda r: r["observations"][1]["parsed_metrics"]
                            .update(trace_fingerprint_fnv1a64="beef"), "fingerprint")
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        self.assert_refused(BATCH, lambda r: r["observations"][1]["parsed_metrics"]["exported_metrics"]
                            .update(all_items_matched=False), "all_items_matched")
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        self.assert_refused(LIFECYCLE, lambda r: r["observations"][0]["parsed_metrics"]["exported_metrics"]
                            .update(oracle_agreement_pct=99.9), "oracle")

    def test_unknown_cell_and_unreadable_record(self):
        self.assert_refused(BATCH, lambda r: r.update(cell_id="mystery_cell"), "identity|Unknown cell")
        bad_dir = Path(tempfile.mkdtemp(dir=self.tmp.name))
        (bad_dir / "pair_000_x.json").write_text("{not json")
        with self.assertRaisesRegex(bc.AnalysisError, "unreadable"):
            bc.load_pairs(bad_dir, "main")

    def test_record_escaping_the_raw_directory_is_refused(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)})
        victim = next(self.dir.glob("pair_003_*"))
        outside = Path(tempfile.mkdtemp(dir=self.tmp.name)) / victim.name
        outside.write_bytes(victim.read_bytes())
        victim.unlink()
        victim.symlink_to(outside)
        with self.assertRaisesRegex(bc.AnalysisError, "outside the raw directory"):
            bc.load_pairs(self.dir, "main")

    def test_missing_raw_directory_is_refused(self):
        with self.assertRaisesRegex(bc.AnalysisError, "not accessible"):
            bc.load_pairs(Path(self.tmp.name) / "does-not-exist", "main")

    def test_duplicate_pair_ids(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)})
        record = json.loads(next(self.dir.glob("pair_003_*")).read_text())
        (self.dir / "pair_003_copy.json").write_text(json.dumps(record))
        with self.assertRaisesRegex(bc.AnalysisError, "duplicate"):
            bc.load_pairs(self.dir, "main")

    def test_wrong_pair_count(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2, n=11)})
        with self.assertRaisesRegex(bc.AnalysisError, "expected 12"):
            bc.analyze(self.dir, None, "v0.4.0")

    def test_v040_requires_the_approved_nine_cells(self):
        write_matrix(self.dir, {})
        next(self.dir.glob(f"pair_*_{BATCH}.json"))  # present
        for path in self.dir.glob(f"pair_*_{BATCH}.json"):
            path.unlink()
        with self.assertRaisesRegex(bc.AnalysisError, "approved nine"):
            bc.analyze(self.dir, None, "v0.4.0")

    def test_v040_requires_the_balanced_design(self):
        mutations = {
            "session": lambda r: set_session(r, 2),
            "order": swap_order,
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                directory = Path(tempfile.mkdtemp(dir=self.tmp.name))
                write_matrix(directory, {}, overrides_by_cell={LIFECYCLE: {0: mutate}})
                with self.assertRaisesRegex(bc.AnalysisError, "balanced design"):
                    bc.analyze(directory, None, "v0.4.0")

    def test_v040_requires_a_balanced_extension(self):
        ratios = {primary(LIFECYCLE): spread(5, 30)}
        root = Path(self.tmp.name)
        write_matrix(root / "m", {LIFECYCLE: ratios})
        write_cell(root / "e", LIFECYCLE, ratios, first_pair_id=100,
                   overrides={4: lambda r: set_session(r, 0)}, phase="extension")
        with self.assertRaisesRegex(bc.AnalysisError, "extension .*balanced design"):
            bc.analyze(root / "m", root / "e", "v0.4.0")

    def test_malformed_types_are_refused_not_crashed(self):
        mutations = {
            "pair_id list": lambda r: r.update(pair_id=[1]),
            "pair_id bool": lambda r: r.update(pair_id=True),
            "cell_id int": lambda r: r.update(cell_id=7),
            "session bool": lambda r: r.update(session=True),
            "session float": lambda r: r.update(session=1.0),
            "observation session float": lambda r: r["observations"][1].update(session=float(r["session"])),
            "pair_position float": lambda r: r["observations"][0].update(pair_position=0.0),
            "completion missing": lambda r: r["observations"][1].pop("completion_unix_ns"),
            "labels dicts": lambda r: r.update(labels=[{}, {}]),
            "labels missing": lambda r: r.pop("labels"),
            "parsed_metrics": lambda r: r["observations"][0].update(parsed_metrics=[]),
            "binary identity": lambda r: r["observations"][0].pop("binary_identity"),
            "launch time": lambda r: r["observations"][0].update(launch_unix_ns="soon"),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
                write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: mutate})
                with self.assertRaises(bc.AnalysisError):
                    bc.analyze(self.dir, None, "v0.3.0")

    def test_observation_order_must_match_labels(self):
        mutations = {
            "swapped labels": lambda r: r.update(labels=list(reversed(r["labels"]))),
            "position": lambda r: r["observations"][0].update(pair_position=1),
            "session": lambda r: r["observations"][1].update(session=2),
            "launch order": lambda r: r["observations"][1].update(
                launch_unix_ns=r["observations"][0]["launch_unix_ns"] - 1),
        }
        for name, mutate in mutations.items():
            with self.subTest(name=name):
                self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
                write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: mutate})
                with self.assertRaisesRegex(bc.AnalysisError, "labels|session|launched"):
                    bc.analyze(self.dir, None, "v0.3.0")

    def test_manifest_must_declare_the_phase(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)})
        write_manifest(self.dir, "extension")
        with self.assertRaisesRegex(bc.AnalysisError, "declares phase"):
            bc.analyze(self.dir, None, "v0.3.0")
        (self.dir / "manifest.json").unlink()
        with self.assertRaisesRegex(bc.AnalysisError, "unreadable"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_binary_identity_and_fingerprint_must_not_drift(self):
        write_cell(self.dir, CORE, {primary(CORE): spread(0, 2)},
                   overrides={5: lambda r: r["observations"][1].update(binary_identity={"sha256": "other"})})
        with self.assertRaisesRegex(bc.AnalysisError, "binary identity"):
            bc.analyze(self.dir, None, "v0.3.0")

        def refingerprint(r):
            for obs in r["observations"]:
                obs["parsed_metrics"]["trace_fingerprint_fnv1a64"] = "beef"
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        write_cell(self.dir, CORE, {primary(CORE): spread(0, 2)}, overrides={5: refingerprint})
        with self.assertRaisesRegex(bc.AnalysisError, "fingerprint differs"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_duplicate_observation_within_a_phase_is_refused(self):
        write_cell(self.dir, CORE, {primary(CORE): spread(0, 2)})
        source = json.loads(next(self.dir.glob("pair_003_*")).read_text())
        target = next(self.dir.glob("pair_001_*"))
        source["pair_id"] = 1
        for obs in source["observations"]:
            obs["pair_id"] = 1
        target.write_text(json.dumps(source))
        with self.assertRaisesRegex(bc.AnalysisError, "same launch time"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_overlapping_observations_are_refused(self):
        def b_and_c_together(r):
            r["observations"][0]["completion_unix_ns"] = r["observations"][1]["launch_unix_ns"] + 1
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: b_and_c_together})
        with self.assertRaisesRegex(bc.AnalysisError, "before position 0 completed"):
            bc.analyze(self.dir, None, "v0.3.0")

        def runs_into_next_pair(r):
            r["observations"][1]["completion_unix_ns"] += 5000
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: runs_into_next_pair})
        with self.assertRaisesRegex(bc.AnalysisError, "launched before .* completed"):
            bc.analyze(self.dir, None, "v0.3.0")

        def no_duration(r):
            r["observations"][0]["completion_unix_ns"] = r["observations"][0]["launch_unix_ns"]
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: no_duration})
        with self.assertRaisesRegex(bc.AnalysisError, "completion is not after launch"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_identical_b_and_c_binaries_are_refused(self):
        def same(r):
            for obs in r["observations"]:
                obs["binary_identity"] = {"sha256": "same"}
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={i: same for i in range(12)})
        with self.assertRaisesRegex(bc.AnalysisError, "same .* binary identity"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_fingerprint_must_be_a_non_empty_string(self):
        for bad in (None, "", 7):
            with self.subTest(bad=bad):
                def set_print(r, bad=bad):
                    for obs in r["observations"]:
                        obs["parsed_metrics"]["trace_fingerprint_fnv1a64"] = bad
                self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
                write_cell(self.dir, CORE, {primary(CORE): spread(0, 2)},
                           overrides={i: set_print for i in range(12)})
                with self.assertRaisesRegex(bc.AnalysisError, "fingerprint"):
                    bc.analyze(self.dir, None, "v0.3.0")

    def test_overflow_and_non_finite_ratios_are_refused(self):
        def huge(r):
            r["observations"][0]["parsed_metrics"]["exported_metrics"]["window_duration_ns"] = 10**400
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={4: huge})
        with self.assertRaisesRegex(bc.AnalysisError, "overflows"):
            bc.analyze(self.dir, None, "v0.3.0")

        def extreme(r):
            for obs in r["observations"]:
                obs["parsed_metrics"]["exported_metrics"]["window_duration_ns"] = 1e-300 if obs["label"] == "B" else 1e300
        self.dir = Path(tempfile.mkdtemp(dir=self.tmp.name)) / "main"
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)}, overrides={i: extreme for i in range(12)})
        with self.assertRaisesRegex(bc.AnalysisError, "finite"):
            bc.analyze(self.dir, None, "v0.3.0")

    def test_deeply_nested_record_is_refused(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)})
        (self.dir / "pair_999_deep.json").write_text("[" * 100000)
        out = Path(self.tmp.name) / "deep.json"
        self.assertEqual(bc.main(["--main", str(self.dir), "--rules", "v0.3.0", "--output", str(out)]), 2)
        self.assertFalse(out.exists())

    def test_cli_rejects_a_missing_output_directory(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2)})
        out = Path(self.tmp.name) / "absent" / "out.json"
        with self.assertRaises(SystemExit):
            bc.main(["--main", str(self.dir), "--rules", "v0.3.0", "--output", str(out)])
        self.assertFalse(out.exists())

    def test_cli_refuses_and_writes_nothing(self):
        write_cell(self.dir, BATCH, {primary(BATCH): spread(0, 2, n=11)})
        out = Path(self.tmp.name) / "out.json"
        self.assertEqual(bc.main(["--main", str(self.dir), "--rules", "v0.4.0", "--output", str(out)]), 2)
        self.assertFalse(out.exists())


@unittest.skipUnless(V030.is_dir(), f"retained v0.3.0 evidence not found at {V030}")
class V030ReproductionTest(unittest.TestCase):
    """Recompute the v0.3.0 campaign from raw pairs and compare with its retained reports."""

    SCALARS = ("B_median", "C_median", "median_change_pct", "ratio_of_medians_change_pct")

    @classmethod
    def setUpClass(cls):
        cls.main = bc.analyze(V030 / "raw-main", None, "v0.3.0")
        cls.final = bc.analyze(V030 / "raw-main", V030 / "extension/raw-extension", "v0.3.0")
        cls.ref_main = json.loads((V030 / "decision-analysis.json").read_text())
        cls.ref_final = json.loads((V030 / "final-decision-analysis.json").read_text())

    def compare_cell(self, ours, ref):
        for key in self.SCALARS:
            self.assertAlmostEqual(ours[key], ref[key], places=9, msg=key)
        self.assertEqual(ours["pairs"], ref["pairs"])
        self.assertEqual(ours["primary_metric"], ref["primary_metric"])
        for a, b in zip(ours["primary_interval_pct"], ref["primary_interval_pct"]):
            self.assertAlmostEqual(a, b, places=9)
        self.assertEqual(ours["primary_status"], ref["primary_status"])
        self.assertEqual(ours["status"], ref["status"])
        self.assertEqual(ours["supporting_regressions"], ref["supporting_regressions"])
        if "supporting" in ref:
            self.assertEqual([m["metric"] for m in ours["supporting"]], [m["metric"] for m in ref["supporting"]])
            for mine, theirs in zip(ours["supporting"], ref["supporting"]):
                for key in ("B_median", "C_median", "median_change_pct"):
                    self.assertAlmostEqual(mine[key], theirs[key], places=9, msg=f"{mine['metric']} {key}")
                for a, b in zip(mine["interval_pct"], theirs["interval_pct"]):
                    self.assertAlmostEqual(a, b, places=9)
                self.assertEqual(mine["tolerance_pct"], theirs["tolerance_pct"])
                self.assertEqual(mine["lower_bound_exceeds_tolerance"], theirs["lower_bound_exceeds_tolerance"])

    def test_main_phase(self):
        ref_cells = {c["cell_id"]: c for c in self.ref_main["cells"]}
        self.assertEqual(sorted(ref_cells), [c["cell_id"] for c in self.main["cells"]])
        self.assertEqual(self.main["extension_cells_required"], sorted(self.ref_main["extension_cells_required"]))
        self.assertEqual(self.main["main_pairs"], self.ref_main["pairs"])
        for cell in self.main["cells"]:
            with self.subTest(cell=cell["cell_id"]):
                self.compare_cell(cell, ref_cells[cell["cell_id"]])
                self.assertEqual(cell["primary_tolerance_pct"], ref_cells[cell["cell_id"]]["primary_tolerance_pct"])

    def test_final_decision(self):
        ref_cells = self.ref_final["cells"]
        self.assertEqual(sorted(ref_cells), [c["cell_id"] for c in self.final["cells"]])
        self.assertEqual(self.final["extension_pairs"], self.ref_final["extension_counts"]["pairs"])
        for cell in self.final["cells"]:
            with self.subTest(cell=cell["cell_id"]):
                ref = ref_cells[cell["cell_id"]]
                self.compare_cell(cell, ref)
                self.assertEqual(cell["extension_disposition"], ref["extension_disposition"])


if __name__ == "__main__":
    unittest.main()
