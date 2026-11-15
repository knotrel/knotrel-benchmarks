"""Unit tests for scripts/run_metrics_overhead.py (pure functions only)."""

import collections
import difflib
import subprocess
import tempfile
from unittest import mock
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import run_metrics_overhead as mo  # noqa: E402


class ScheduleTest(unittest.TestCase):
    def test_every_round_runs_each_arm_once_and_orders_are_balanced(self):
        entries = mo.schedule(24)
        by_round = collections.defaultdict(list)
        for entry in entries:
            by_round[entry["round"]].append(entry["arm"])
        self.assertEqual(len(by_round), 24)
        for arms in by_round.values():
            self.assertEqual(sorted(arms), sorted(mo.ARMS))
        orders = collections.Counter(tuple(arms) for arms in by_round.values())
        self.assertEqual(len(orders), 6)
        self.assertEqual(set(orders.values()), {4})

    def test_extension_continues_round_numbers_and_rotation(self):
        extension = mo.schedule(12, first_round=24)
        self.assertEqual(extension[0]["round"], 24)
        self.assertEqual(extension[-1]["round"], 35)
        first = [e["arm"] for e in extension if e["round"] == 24]
        self.assertEqual(first, [e["arm"] for e in mo.schedule(1) if e["round"] == 0])


class VerdictTest(unittest.TestCase):
    def test_budget_boundaries(self):
        self.assertEqual(mo.budget_verdict(3.0, (1.0, 6.0), 1.0), "PASS")
        self.assertEqual(mo.budget_verdict(-1.0, (-3.0, 0.5), 1.0), "PASS")
        self.assertEqual(mo.budget_verdict(3.1, (1.0, 5.0), 1.0), "INCONCLUSIVE")
        self.assertEqual(mo.budget_verdict(2.0, (0.0, 6.5), 1.0), "INCONCLUSIVE")
        self.assertEqual(mo.budget_verdict(5.0, (3.5, 7.0), 1.0), "REGRESSION")
        # A slowdown inside the A/A noise is never a confirmed regression.
        self.assertEqual(mo.budget_verdict(5.0, (3.5, 7.0), 6.0), "INCONCLUSIVE")

    def test_evaluate_pairs_by_round(self):
        rounds = {r: {"off": 100.0, "on": 101.0 + (r % 2) * 0.2, "aa": 100.0 + (r % 3 - 1) * 0.1}
                  for r in range(12)}
        result = mo.evaluate(rounds)
        self.assertEqual(result["n"], 12)
        self.assertAlmostEqual(result["on"]["median_pct"], 1.1, places=6)
        self.assertEqual(result["on"]["verdict"], "PASS")
        self.assertLessEqual(result["aa"]["noise_bound_pct"], 0.11)

    def test_bootstrap_is_deterministic(self):
        values = [0.5, 1.0, 2.0, -1.0, 3.0, 0.0]
        first = mo.bootstrap_median_ci(values)
        second = mo.bootstrap_median_ci(list(values))
        self.assertEqual(first, second)


class MeasuredTreeTest(unittest.TestCase):
    CLEAN = {"code_diff_sha256": mo.sha256_bytes(b""), "untracked_code_files": {}}
    PATCHED = {"code_diff_sha256": mo.sha256_bytes(b"diff"), "untracked_code_files": {"crates/x.rs": "ab"}}

    def test_protocol_constants_are_unchanged(self):
        self.assertEqual(mo.BASELINE_COMMIT, "e1e11818a762baf07575719456a2158959b2e2c8")
        self.assertEqual(mo.RC_COMMIT, "62c2cea9314085f6f7669ebbb7def2be1fa1cb5c")
        self.assertEqual((mo.ARMS, mo.PRIMARY_ROUNDS, mo.EXTENSION_ROUNDS, mo.SESSIONS),
                         (("off", "on", "aa"), 24, 12, 2))
        self.assertEqual((mo.BUDGET_MEDIAN_PCT, mo.BUDGET_UPPER_PCT), (3.0, 6.0))
        self.assertEqual((mo.PROBE_ITERATIONS, mo.BOOTSTRAP_SEED, mo.BOOTSTRAP_RESAMPLES), (2000, 20261115, 10_000))
        self.assertEqual((mo.QUIET_SECONDS, mo.SESSION_COOLDOWN_SECONDS, mo.ROUND_COOLDOWN_SECONDS),
                         (60.0, 120.0, 5.0))

    def test_default_is_the_original_baseline(self):
        args = mo.parse_args(["campaign"])
        self.assertEqual(args.measured_commit, mo.BASELINE_COMMIT)
        self.assertEqual(mo.parse_args(["c", "--measured-commit", mo.RC_COMMIT]).measured_commit, mo.RC_COMMIT)
        with self.assertRaises(SystemExit):
            mo.parse_args(["c", "--measured-commit", "0" * 40])

    def test_baseline_accepts_a_patched_tree(self):
        self.assertIsNone(mo.measured_tree_error(mo.BASELINE_COMMIT, mo.BASELINE_COMMIT, self.PATCHED))

    def test_rc_requires_a_clean_checkout(self):
        self.assertIsNone(mo.measured_tree_error(mo.RC_COMMIT, mo.RC_COMMIT, self.CLEAN))
        self.assertIn("clean", mo.measured_tree_error(mo.RC_COMMIT, mo.RC_COMMIT, self.PATCHED))
        only_untracked = {**self.CLEAN, "untracked_code_files": {"crates/x.rs": "ab"}}
        self.assertIn("clean", mo.measured_tree_error(mo.RC_COMMIT, mo.RC_COMMIT, only_untracked))

    def test_rc_requires_committed_tooling(self):
        dirty = " M tools/hot-path-probes/Cargo.toml\n"
        self.assertIn("tooling", mo.measured_tree_error(mo.RC_COMMIT, mo.RC_COMMIT, self.CLEAN, dirty))
        self.assertIsNone(mo.measured_tree_error(mo.BASELINE_COMMIT, mo.BASELINE_COMMIT, self.PATCHED, dirty))
        self.assertEqual(mo.BENCH_TOOLING_PATHS, ("scripts", "tools/hot-path-probes", "tools/hot-path-probes-rc"))

    def test_probe_selection_keeps_the_historical_probe(self):
        self.assertEqual(mo.PROBE_DIRS[mo.BASELINE_COMMIT], "tools/hot-path-probes")
        self.assertEqual(mo.PROBE_DIRS[mo.RC_COMMIT], "tools/hot-path-probes-rc")
        self.assertEqual(mo.PROBE_TARGET_DIRS[mo.BASELINE_COMMIT], "target")
        self.assertNotEqual(mo.PROBE_TARGET_DIRS[mo.RC_COMMIT], "target")
        self.assertEqual(set(mo.PROBE_DIRS), set(mo.MEASURED_COMMITS))

    def test_rc_probe_differs_only_in_axum_features(self):
        bench = Path(__file__).resolve().parents[2]
        old = (bench / "tools/hot-path-probes/Cargo.lock").read_text().splitlines()
        new = (bench / "tools/hot-path-probes-rc/Cargo.lock").read_text().splitlines()
        removed = [line for line in difflib.unified_diff(old, new, lineterm="", n=0)
                   if line.startswith(("-", "+")) and not line.startswith(("---", "+++"))]
        self.assertEqual(removed, ['- "tracing",', '- "log",'])
        manifest = (bench / "tools/hot-path-probes-rc/Cargo.toml").read_text()
        self.assertIn('path = "../hot-path-probes/src/bin/router-probe.rs"', manifest)
        self.assertIn('axum = { version = "0.8.9", default-features = false, features = ["form", "http1", "json", '
                      '"matched-path", "original-uri", "query", "tokio", "tracing"] }', manifest)

    def test_build_gives_on_and_off_the_same_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            campaign = mo.Campaign(mo.parse_args([tmp, "--measured-commit", mo.RC_COMMIT]))
            campaign.work = Path(tmp) / "work"
            campaign.out = Path(tmp) / "run"
            campaign.out.mkdir()
            calls = []

            def fake_cargo(argv, cwd, env, stdout, stderr, timeout):
                calls.append((argv, cwd, env["CARGO_TARGET_DIR"]))
                built = Path(env["CARGO_TARGET_DIR"]) / "release" / "router-probe"
                built.parent.mkdir(parents=True)
                built.write_bytes(b"probe")
                return subprocess.CompletedProcess(argv, 0)

            with mock.patch.object(mo.subprocess, "run", fake_cargo), \
                    mock.patch.object(campaign, "check_identity"):
                campaign.build()
            self.assertEqual(campaign.binary["on"], campaign.binary["off"])
            self.assertNotEqual(campaign.binary["aa"], campaign.binary["off"])
            self.assertEqual(campaign.argv("on")[:-1], campaign.argv("off"))
            self.assertEqual(campaign.argv("on")[-1], "--metrics")
            (argv, cwd, target), = calls
            self.assertEqual(cwd, campaign.bench / "tools/hot-path-probes-rc")
            self.assertEqual(Path(target).name, "target-rc")
            self.assertIn("--locked", argv)

    def test_rc_requires_the_probe_checkout(self):
        self.assertIn("--knotrel", mo.measured_tree_error(mo.RC_COMMIT, mo.RC_COMMIT, self.CLEAN, "", False))
        self.assertIsNone(mo.measured_tree_error(mo.BASELINE_COMMIT, mo.BASELINE_COMMIT, self.PATCHED, "", False))
        bench = Path(__file__).resolve().parents[2]
        self.assertEqual(mo.probe_knotrel_checkout(bench), (bench.parent / "knotrel").resolve())
        self.assertEqual(Path(mo.parse_args(["c"]).knotrel).resolve(), mo.probe_knotrel_checkout(bench))

    def test_head_must_match_the_measured_commit(self):
        self.assertIn("is not", mo.measured_tree_error(mo.BASELINE_COMMIT, mo.RC_COMMIT, self.CLEAN))
        self.assertIn("is not", mo.measured_tree_error(mo.RC_COMMIT, mo.BASELINE_COMMIT, self.CLEAN))
        self.assertIn("not one of", mo.measured_tree_error("f" * 40, "f" * 40, self.CLEAN))


class ParseTest(unittest.TestCase):
    def test_parse_probe_lines(self):
        stdout = (
            '{"elapsed_ns":"2000","metrics":true,"mode":"timing","requests":2,"scenario":"a","schema":1}\n'
            "noise\n"
            '{"elapsed_ns":"300","metrics":true,"mode":"timing","requests":1,"scenario":"b","schema":1}\n'
        )
        self.assertEqual(mo.parse_probe(stdout), {"a": 1000.0, "b": 300.0})


if __name__ == "__main__":
    unittest.main()
