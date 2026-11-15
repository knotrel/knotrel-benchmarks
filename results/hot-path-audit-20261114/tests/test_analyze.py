"""Tests for the campaign analysis with a synthetic run directory."""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

CAMPAIGN = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CAMPAIGN))

import analyze  # noqa: E402


def write(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return hashlib.sha256(text.encode()).hexdigest()


def synthetic_campaign(root: Path, cand_factor: float = 0.9, rounds: int = 6) -> Path:
    """Builds a minimal but complete campaign directory."""
    campaign = root / "hot-path-audit-20261114"
    run = campaign / "run"
    run.mkdir(parents=True)
    state = {"head": "h", "branch": "b", "staged_equals_worktree": True, "diff_unstaged_sha256": "0" * 64,
             "diff_staged_sha256": "1" * 64, "diff_head_sha256": "2" * 64, "diff_head_code_only_sha256": "3" * 64}
    write(run / "provenance.json", json.dumps({
        "toolchain": "1.100.0", "knotrel": state, "knotrel_benchmarks": state,
        "baseline": {"commit": "e1e1181", "materialization": "git archive e1e1181"},
        "candidate": {"materialization": "archive + patch", "code_patch_sha256": "4" * 64}}))
    tools = {"router-probe-timing": "x" * 64}
    write(run / "builds" / "binaries.json", json.dumps({"sha256": {"base": tools, "cand": tools, "aa": tools}}))
    write(run / "environment.json", json.dumps({"host": {"commands": [
        {"argv": ["uname", "-a"], "stdout": "Darwin test", "exit_code": 0}]}}))
    write(run / "schedule.json", json.dumps({"rounds": rounds, "sessions": 2, "arms": ["base", "cand", "aa"],
                                            "seed": 1, "quiet_seconds": 60, "session_cooldown_seconds": 120,
                                            "round_cooldown_seconds": 5}))
    write(run / "verification" / "summary.json", json.dumps([{"label": "bench-fmt", "argv": ["cargo", "fmt"],
                                                              "exit_code": 0}]))
    records = []
    sequence = 0

    def add(section: str, label: dict, stdout: str) -> None:
        nonlocal sequence
        stem = f"raw/{section}/{sequence:05d}"
        records.append({"sequence": sequence, "section": section, **label,
                        "stdout_path": f"{stem}.stdout", "stderr_path": f"{stem}.stderr",
                        "stdout_sha256": write(run / f"{stem}.stdout", stdout),
                        "stderr_sha256": write(run / f"{stem}.stderr", ""),
                        "peak_rss_bytes": 1000 + sequence})
        sequence += 1

    jitter = [1.0, 1.01, 0.99, 1.005, 0.995, 1.002]
    for r in range(rounds):
        for arm in ("base", "cand", "aa"):
            factor = (cand_factor if arm == "cand" else 1.0) * jitter[(r + len(arm)) % len(jitter)]
            label = {"kind": "init", "cell": "init/hdt/chain/200000", "arm": arm, "round": r, "session": r // 3,
                     "position": 0}
            add("timed", label, json.dumps({"validated_dynamic_continuation": False, "repetitions": [
                {"total_initialization_ns": int(1e8 * factor * j), "trace_fingerprint_fnv1a64": "abc"}
                for j in (1.0, 1.01, 0.99)]}))
            label = {**label, "kind": "dynamic", "cell": "dynamic/hdt/blocks/10000x200"}
            add("timed", label, json.dumps({"trace_fingerprint_fnv1a64": "def", "repetitions": [
                {"workload_wall_ns": int(5e7 * jitter[r % 6]), "measurements": {
                    "link": {"count": 10, "total_ns": 100}, "cut": {"count": 10, "total_ns": 200},
                    "connected": {"count": 20, "total_ns": 300}}}]}))
            label = {**label, "kind": "probe", "cell": "probe/timing/metrics-off"}
            add("timed", label, json.dumps({"scenario": "single_connected", "requests": 100,
                                            "elapsed_ns": str(int(1e6 * factor))}) + "\n")
    for arm in ("base", "cand"):
        add("correctness", {"kind": "init-validate", "cell": "init/hdt/chain/200000", "arm": arm},
            json.dumps({"validated_dynamic_continuation": True, "repetitions": [
                {"total_initialization_ns": 1, "trace_fingerprint_fnv1a64": "abc"}]}))
        add("correctness", {"kind": "router-verify", "metrics": False, "arm": arm},
            json.dumps({"scenario": "single_connected", "digest": "00ff"}) + "\n")
        add("allocation", {"kind": "router-count", "metrics": False, "arm": arm},
            json.dumps({"scenario": "single_connected", "requests": 10,
                        "allocations": 960 if arm == "base" else 800, "reallocations": 0,
                        "bytes_allocated": 100}) + "\n")
    add("micro", {"kind": "job-tracking"}, json.dumps({"benchmark": "job_track_release_atomic", "threads": 1,
                                                       "ns_per_op": [7.0, 7.1, 7.2]}) + "\n")
    for r in range(rounds):
        for arm in ("base", "cand", "aa"):
            row = "| **#1** | `80.0` | `40.0` | `120.0` | `500.0` | `1000.0` | `5000.0` | `5000/5000 (100.00%)` " \
                  "| `40.0` | `50.0` | `170.0` |"
            add("e2e", {"kind": "e2e-lifecycle-large", "round": r, "arm": arm}, "header\n" + row + "\n")
    write(run / "observations.jsonl", "".join(json.dumps(r) + "\n" for r in records))
    return campaign


class StatisticsTests(unittest.TestCase):
    def test_describe_and_quartiles(self) -> None:
        d = analyze.describe([1, 2, 3, 4, 5])
        self.assertEqual((d["n"], d["median"], d["q1"], d["q3"], d["iqr"], d["mad"]), (5, 3, 2, 4, 2, 1))
        self.assertEqual(analyze.describe([7])["iqr"], 0)

    def test_bootstrap_is_deterministic_and_brackets_median(self) -> None:
        values = [-10.0, -9.0, -11.0, -10.5, -9.5, -10.2]
        low, high = analyze.bootstrap_median_ci(values)
        self.assertEqual((low, high), analyze.bootstrap_median_ci(values))
        self.assertLessEqual(low, -10.0)
        self.assertGreaterEqual(high, -10.5)

    def test_sign_test(self) -> None:
        self.assertAlmostEqual(analyze.sign_test_p([-1] * 6), 2 / 64)
        self.assertEqual(analyze.sign_test_p([0, 0]), 1.0)
        self.assertEqual(analyze.sign_test_p([-1, 1]), 1.0)

    def test_verdict_rules(self) -> None:
        self.assertEqual(analyze.verdict((-12, -8), -10, 2), "confirmed improvement")
        self.assertEqual(analyze.verdict((-12, -1), -1.5, 2), "inconclusive")
        self.assertEqual(analyze.verdict((-3, 1), -1, 0.5), "inconclusive")
        self.assertEqual(analyze.verdict((4, 9), 6, 2), "confirmed regression")

    def test_paired_changes_use_same_round(self) -> None:
        by_round = {0: {"base": 100.0, "cand": 90.0}, 1: {"base": 200.0, "cand": 220.0}, 2: {"base": 1.0}}
        changes = analyze.paired_changes(by_round, "cand")
        self.assertEqual(len(changes), 2)
        self.assertAlmostEqual(changes[0], -10.0)
        self.assertAlmostEqual(changes[1], 10.0)


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.campaign = synthetic_campaign(Path(self.temporary.name))

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_full_pipeline_and_clean_regeneration(self) -> None:
        result = analyze.analyze(self.campaign)
        analyze.write_outputs(self.campaign, result)
        summary = json.loads((self.campaign / "analysis" / "summary.json").read_text())
        verdicts = {(e["cell"], e["metric"]): e["cand"]["verdict"] for e in summary["timed"]}
        self.assertEqual(verdicts[("init/hdt/chain/200000", "total_initialization_ns")], "confirmed improvement")
        self.assertEqual(verdicts[("dynamic/hdt/blocks/10000x200", "workload_wall_ns")], "inconclusive")
        self.assertEqual(verdicts[("probe/timing/metrics-off", "single_connected_ns_per_request")],
                         "confirmed improvement")
        self.assertTrue(all(summary["correctness"]["trace_fingerprints_identical_across_arms"].values()))
        self.assertTrue(all(d["identical"] for d in summary["correctness"]["router_digests"]))
        allocation = [a for a in summary["allocation"] if a["metric"] == "allocation_events_per_request"]
        self.assertEqual(allocation[0]["values"], {"base": [96.0], "cand": [80.0]})
        report = (self.campaign / "REPORT.md").read_text()
        for heading in ("## Confirmed Improvements", "## Confirmed Regressions", "## Inconclusive Measurements",
                        "## Allocation Counts", "## End-to-End HTTP"):
            self.assertIn(heading, report)
        manifest = json.loads((self.campaign / "manifest.json").read_text())
        paths = {entry["path"] for entry in manifest["files"]}
        self.assertIn("REPORT.md", paths)
        self.assertIn("run/observations.jsonl", paths)
        self.assertNotIn("manifest.json", paths)
        self.assertEqual(analyze.check(self.campaign), 0)

    def test_check_detects_stale_outputs(self) -> None:
        analyze.write_outputs(self.campaign, analyze.analyze(self.campaign))
        report = self.campaign / "REPORT.md"
        report.write_text(report.read_text() + "edited\n")
        self.assertEqual(analyze.check(self.campaign), 1)

    def test_tampered_raw_stream_is_rejected(self) -> None:
        raw = next((self.campaign / "run" / "raw" / "timed").glob("*.stdout"))
        raw.write_text(raw.read_text() + " ")
        with self.assertRaises(ValueError):
            analyze.analyze(self.campaign)


if __name__ == "__main__":
    unittest.main()
