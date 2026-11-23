"""Tests for the fixes of the independent review of the v1.0.0 qualification tooling.

Each class names the finding it covers: B1 (probe lockfile version), B2 (freeze guards), N6
(prepare's helpers), B3 (Part 1 failure classification and attempt budget), B4 (Q attempt 2),
N1 (PostgreSQL start), N4 (rerun allowance per observation), N5 (power evidence), S1 (removed
environment), S2 (Q verdicts without a value), S3 (prepare before the campaign directory),
S4/B5 (decision rule text), S5 (Q cells against the load tool). No test measures anything.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import evaluate_v100q_q as ev  # noqa: E402
import freeze_check_v100q as fc  # noqa: E402
import part1_failures_v100q as p1  # noqa: E402
import run_v100q_autonomous as runner  # noqa: E402
import run_v100q_q as q  # noqa: E402
import test_v100q as base  # noqa: E402

V100 = ROOT / "results" / "v1.0.0-qualification"
TEMPLATE = json.loads((V100 / "FREEZE.template.json").read_text())
PREPARE = (V100 / "prepare_campaign.sh").read_text()
PART3 = (V100 / "run_part3.sh").read_text()
PROTOCOL = (V100 / "PROTOCOL.md").read_text()
MATRIX = json.loads((V100 / "MATRIX.json").read_text())
CAND, REF = base.CAND, base.REF


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t", *args],
                          check=True, capture_output=True, text=True).stdout


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def good_freeze(paths, hashes, tooling, core_sha="1" * 64):
    return {"campaign": fc.CAMPAIGN, "revision": 1, "frozen_utc": "2026-11-30T00:00:00Z",
            "candidate": {"commit": CAND, "version": "1.0.0-rc.1"}, "reference": {"commit": REF},
            "core_rule": {"outcome": "identical", "comparison": {"file": "x", "sha256": core_sha}},
            "tooling": {"commit": tooling}, "file_sha256_paths": list(paths), "file_sha256": dict(hashes)}


def frozen_repo(repo: Path, mutate=None, core_sha="1" * 64):
    """A Git repository holding every required file, a tooling commit and a freeze commit."""
    repo.mkdir(parents=True, exist_ok=True)
    git(repo, "init", "-q")
    hashes = {}
    for path in fc.REQUIRED_FROZEN_PATHS:
        f = repo / path
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_bytes(f"content of {path}\n".encode())
        hashes[path] = sha(f.read_bytes())
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "tooling")
    tooling = git(repo, "rev-parse", "HEAD").strip()
    freeze = good_freeze(fc.REQUIRED_FROZEN_PATHS, hashes, tooling, core_sha)
    if mutate:
        mutate(repo, freeze)
    (repo / fc.FREEZE_PATH).write_text(json.dumps(freeze))
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "freeze")
    return freeze, tooling, git(repo, "rev-parse", "HEAD").strip()


# -- B1 -------------------------------------------------------------------------------------------
class ProbeLockVersionTest(unittest.TestCase):
    def lock_versions(self):
        text = (ROOT / "tools/lifecycle-probes/Cargo.lock").read_text()
        return {n: re.findall(rf'name = "{n}"\nversion = "([^"]+)"', text) for n in ("knotrel-core", "knotrel-server")}

    def test_probe_lockfile_names_the_freeze_record_version(self):
        records = [TEMPLATE]
        if (V100 / "FREEZE.json").exists():
            records.append(json.loads((V100 / "FREEZE.json").read_text()))
        for record in records:
            want = record["candidate"]["version"]
            self.assertEqual(self.lock_versions(), {"knotrel-core": [want], "knotrel-server": [want]})

    def test_prepare_checks_the_lockfile_against_the_candidate_before_building(self):
        check = PREPARE.index('CAND_VERSION=$(git -C "$KREPO" show "$CAND:Cargo.toml"')
        self.assertLess(check, PREPARE.index('mkdir -p "$CAMP/logs"'))
        self.assertLess(check, PREPARE.index("cargo +1.100.0 build"))
        self.assertIn("tools/lifecycle-probes/Cargo.lock", PREPARE[check:check + 400])
        self.assertIn("candidate.version", PREPARE)

    def test_plan_citation(self):
        for text in (PROTOCOL, TEMPLATE["plan"]):
            self.assertNotIn("d847283", text)
            flat = " ".join(re.sub(r"[`,()]", " ", text).split())
            self.assertIn("origin/main at the freeze which records candidate 0c49b2a 1.0.0-rc.1", flat)


# -- B2 -------------------------------------------------------------------------------------------
class FreezeGuardTest(unittest.TestCase):
    def test_template_lists_every_required_and_every_new_file(self):
        listed = set(TEMPLATE["file_sha256_paths"])
        self.assertLessEqual(set(fc.REQUIRED_FROZEN_PATHS), listed)
        for path in ("scripts/freeze_check_v100q.py", "scripts/part1_failures_v100q.py",
                     "results/v1.0.0-qualification/attempt_budget.sh", "scripts/tests/test_v100q_review.py"):
            self.assertIn(path, listed)
        for path in listed:
            self.assertTrue((ROOT / path).is_file(), path)

    def test_record_problems(self):
        paths = list(fc.REQUIRED_FROZEN_PATHS)
        good = good_freeze(paths, {p: "0" * 64 for p in paths}, "2" * 40)
        self.assertEqual(fc.record_problems(good, CAND), [])
        cases = {
            "reference": dict(good, reference={"commit": "3" * 40}),
            "keys differ": dict(good, file_sha256={p: "0" * 64 for p in paths[1:]}),
            "unlisted hash": dict(good, file_sha256={**good["file_sha256"], "x.py": "0" * 64}),
            "required missing": dict(good, file_sha256_paths=paths[1:], file_sha256={p: "0" * 64 for p in paths[1:]}),
            "no comparison hash": dict(good, core_rule={"outcome": "identical", "comparison": "TBD"}),
            "tooling": dict(good, tooling={"commit": "TBD"}),
        }
        for name, record in cases.items():
            with self.subTest(name):
                self.assertTrue(fc.record_problems(record, CAND))
        self.assertIn("reference", fc.record_problems(cases["reference"], CAND)[0])

    def test_core_rule_hash(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "core-rule.json"
            path.write_text(json.dumps({"outcome": "identical"}))
            good = {"core_rule": {"outcome": "identical", "comparison": {"sha256": sha(path.read_bytes())}}}
            self.assertEqual(fc.core_rule_problems(good, path), [])
            bad = {"core_rule": {"outcome": "identical", "comparison": {"sha256": "0" * 64}}}
            self.assertIn("SHA-256", fc.core_rule_problems(bad, path)[0])
            self.assertTrue(fc.core_rule_problems(good, Path(d) / "absent.json"))
            other = {"core_rule": {"outcome": "different", "comparison": {"sha256": sha(path.read_bytes())}}}
            self.assertIn("outcome", fc.core_rule_problems(other, path)[0])

    def test_freeze_commit_child_of_tooling_adding_only_freeze(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "ok"
            freeze, tooling, head = frozen_repo(repo)
            self.assertEqual(fc.git_problems(freeze, head, fc.git_runner(repo)), [])
            self.assertEqual(fc.check_commit(repo, head, CAND), [])

            extra = Path(d) / "extra"
            frozen_repo(extra, mutate=lambda r, f: (r / "scripts/run_v100q_q.py").write_text("changed\n"))
            head = git(extra, "rev-parse", "HEAD").strip()
            problems = fc.check_commit(extra, head, CAND)
            self.assertTrue(any("differs from tooling.commit" in p for p in problems), problems)
            self.assertTrue(any("frozen files differ" in p for p in problems), problems)

            grand = Path(d) / "grand"
            freeze, tooling, head = frozen_repo(grand)
            (grand / "note.txt").write_text("x")
            git(grand, "add", ".")
            git(grand, "commit", "-qm", "later")
            later = git(grand, "rev-parse", "HEAD").strip()
            problems = fc.git_problems(freeze, later, fc.git_runner(grand))
            self.assertTrue(any("parents" in p for p in problems), problems)

    def setup_camp(self, d, core_sha=None, mutate=None):
        camp = base.camp_dir(Path(d))
        (camp / "logs").mkdir(parents=True)
        (camp / "logs" / "core-rule.json").write_text(json.dumps({"outcome": "identical"}))
        digest = core_sha or sha((camp / "logs" / "core-rule.json").read_bytes())
        frozen_repo(camp / "src/cand/knotrel-benchmarks", mutate=mutate, core_sha=digest)
        return camp

    def preflight(self, camp):
        r = runner.Part1Runner(camp, CAND)
        r.check_binaries = mock.Mock(side_effect=runner.Stop("NOT STARTED", "REACHED BINARIES"))
        with self.assertRaises(runner.Stop) as stop:
            r.preflight()
        return stop.exception.cause

    def test_runner_preflight_applies_every_guard(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self.preflight(self.setup_camp(d)), "REACHED BINARIES")
        cases = {
            "reference": (None, lambda r, f: f["reference"].update(commit="3" * 40), "reference"),
            "path set": (None, lambda r, f: f["file_sha256_paths"].pop(), "file_sha256"),
            "core rule hash": ("0" * 64, None, "core_rule.comparison"),
            "extra change": (None, lambda r, f: (r / "scripts/cli_paths.py").write_text("x\n"), "frozen files differ"),
        }
        for name, (core, mutate, needle) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                self.assertIn(needle, self.preflight(self.setup_camp(d, core, mutate)))

    def test_runner_preflight_refuses_a_freeze_not_child_of_tooling(self):
        with tempfile.TemporaryDirectory() as d:
            camp = self.setup_camp(d)
            repo = camp / "src/cand/knotrel-benchmarks"
            git(repo, "commit", "-q", "--allow-empty", "-m", "later")
            self.assertIn("parents", self.preflight(camp))


# -- N6 -------------------------------------------------------------------------------------------
class PrepareHelpersTest(unittest.TestCase):
    def test_local_helpers_must_equal_the_record(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            _, _, head = frozen_repo(repo)
            helpers = list(fc.PREPARE_HELPERS)
            self.assertEqual(fc.check_commit(repo, head, CAND, repo, helpers), [])
            (repo / helpers[1]).write_text("tampered\n")
            problems = fc.check_commit(repo, head, CAND, repo, helpers)
            self.assertEqual(len(problems), 1)
            self.assertIn(helpers[1], problems[0])
            self.assertTrue(fc.local_problems({}, repo, ["../../etc/passwd"]))  # only the named helpers
            proc = subprocess.run([sys.executable, str(ROOT / "scripts/freeze_check_v100q.py"), "record", "--repo",
                                   str(repo), "--freeze", head, "--cand", CAND, "--local-root", str(repo),
                                   *sum((["--local", h] for h in helpers), [])], capture_output=True, text=True,
                                  env={**os.environ, "LIFECYCLE_QUALIFICATION_ROOTS": d})
            self.assertEqual(proc.returncode, 1)
            self.assertIn("differs from the freeze record", proc.stderr)

    def test_prepare_checks_helpers_from_the_freeze_commit_before_running_them(self):
        check = PREPARE.index('python3 "$FC/freeze_check_v100q.py" record')
        self.assertLess(PREPARE.index('git -C "$BREPO" show "$FREEZE:scripts/$X"'), check)
        self.assertIn("for X in freeze_check_v100q.py cli_paths.py", PREPARE)
        for helper in ("prepare_campaign.sh", "series_budget.sh", "attempt_budget.sh", "check_restored.sh",
                       "launch_command.sh"):
            self.assertIn(f'--local "$DIR/{helper}"', PREPARE)
        self.assertLess(check, PREPARE.index('sh "$HERE/attempt_budget.sh"'))
        self.assertLess(check, PREPARE.index('sh "$HERE/check_restored.sh"'))
        self.assertEqual(set(fc.PREPARE_HELPERS), {f"{fc.V100}/{h}" for h in (
            "prepare_campaign.sh", "series_budget.sh", "attempt_budget.sh", "check_restored.sh", "launch_command.sh")})
        self.assertIn('freeze_check_v100q.py" core-rule', PREPARE)


# -- B3 -------------------------------------------------------------------------------------------
def attempt(root: Path, name: str, line: str, records=None, log=None, step=None, chain=()):
    d = root / name
    (d / "logs").mkdir(parents=True)
    (d / "logs" / "CONFORMANCE.txt").write_text(line + "\n")
    if records is not None:
        with open(d / "logs" / "failures.jsonl", "w") as handle:
            for r in records:
                handle.write(json.dumps(r) + "\n")
    if log is not None:
        (d / "logs" / f"{step}.log").write_text(log)
    with open(d / "logs" / "chain-steps.txt", "w") as handle:
        for s, what in chain:
            handle.write(f"{s} 2026-12-01T00:00:00Z {what}\n")
    return d


class Part1FailureTest(unittest.TestCase):
    def test_classification_fails_closed(self):
        self.assertEqual(p1.classify_child("OSError: [Errno 28] No space left on device")["classification"],
                         "infrastructure")
        self.assertEqual(p1.classify_child("refused: not on AC power")["classification"], "infrastructure")
        for text in ("thread 'main' panicked at src/lib.rs:10", "No space left on device; core-lifecycle exited 101",
                     "Traceback (most recent call last): KeyError 'x'", "",
                     "Note: No thermal warning level has been recorded", "record has errors: 3"):
            with self.subTest(text):
                self.assertEqual(p1.classify_child(text)["classification"], "product")

    def test_statuses(self):
        with tempfile.TemporaryDirectory() as d:
            camp = attempt(Path(d), "c-attempt1", "x")
            for status, cause, cls in (("BUDGET EXHAUSTED", "deadline", "conformance"),
                                       ("FAILED", "runner error: ValueError()", "conformance"),
                                       ("FAILED", "children without exactly one valid unit record", "conformance"),
                                       ("FAILED", "binary changed: x (end)", "conformance")):
                with self.subTest(cause):
                    self.assertEqual([r["classification"] for r in p1.failures(camp, status, cause)], [cls])
            self.assertEqual(p1.failures(camp, "CONFORMING", "ok"), [])

    def test_product_failure_outcome_fail_and_not_run(self):
        cell = "R-core-import-sparse-10k-20-10"
        with tempfile.TemporaryDirectory() as d:
            chain = [(s, w) for s in ("A-block1", "A-block2", "BC") for w in ("start", "end")] + [("R", "start (block R#0)")]
            camp = attempt(Path(d), "c-attempt1", "x", log=f"running {cell}\nthread 'main' panicked\n", step="R",
                           chain=chain)
            out = p1.record(camp, "FAILED", "R exited 101 (logs/R.log)")
            records = [json.loads(x) for x in (camp / "logs/failures.jsonl").read_text().splitlines()]
            written = json.loads((camp / "logs/part1-outcome.json").read_text())
        self.assertEqual(written, out)
        self.assertEqual(records[0]["classification"], "product")
        self.assertEqual(records[0]["failed_cell"], cell)
        states = {s["step"]: s["state"] for s in out["steps"]}
        self.assertEqual(states, {"A-block1": "completed", "A-block2": "completed", "BC": "completed", "R": "failed",
                                  "Rmem": "not run", "Mreg": "not run"})
        r_cells = {c["id"]: c["verdict"] for c in out["cells"]["R"]}
        self.assertEqual(r_cells.pop(cell), "FAIL")
        self.assertTrue(r_cells and set(r_cells.values()) == {"not run"})
        self.assertTrue(all(c["verdict"] == "not run" and c["reason"] for c in out["cells"]["Rmem"] + out["cells"]["M_reg"]))
        self.assertNotIn("A", out["cells"])
        self.assertFalse(out["attempt2_allowed"])

    def test_runner_writes_the_failure_record(self):
        seen = {}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(base.q3runner.Runner, "write_records",
                                                                   lambda self_: seen.setdefault("base", True)):
            camp = base.camp_dir(Path(d))
            r = runner.Part1Runner(camp, CAND)
            r.status, r.cause = "BLOCKED", "sustained host load"
            r.write_records()
            records = (camp / "logs/failures.jsonl").read_text()
        self.assertTrue(seen["base"])
        self.assertIn('"conformance"', records)

    def budget(self, root, dirs, n=2):
        return subprocess.run(["sh", str(V100 / "attempt_budget.sh"), "attempt", str(n), "2", *map(str, dirs),
                               str(root / "x-attempt[1-9]")], capture_output=True, text=True)

    def test_attempt_budget(self):
        product = [{"kind": "child", "step": "R", "classification": "product", "why": ["panic"]}]
        infra = [{"kind": "child", "step": "R", "classification": "infrastructure", "evidence": ["disk"]}]
        cases = {"product": ("FAILED: R exited 101 (logs/R.log)", product, 1),
                 "no record": ("FAILED: R exited 101 (logs/R.log)", None, 1),
                 "unknown": ("FAILED: R exited 1 (logs/R.log)", [{"classification": "?"}], 1),
                 "infrastructure": ("FAILED: R exited 1 (logs/R.log)", infra, 0),
                 "runner error": ("FAILED: runner error: x", [{"kind": "runner", "classification": "conformance"}], 0),
                 "budget": ("BUDGET EXHAUSTED: x", None, 0),
                 "conforming": ("CONFORMING: x", None, 1)}
        for name, (line, records, code) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                a1 = attempt(Path(d), "x-attempt1", line, records)
                proc = self.budget(Path(d), [a1])
                self.assertEqual(proc.returncode, code, proc.stderr)
                if name == "product":
                    self.assertIn("never rerun", proc.stderr)
        with tempfile.TemporaryDirectory() as d:  # series_budget.sh still applies first
            self.assertEqual(self.budget(Path(d), [], n=2).returncode, 1)
            self.assertEqual(self.budget(Path(d), [], n=1).returncode, 0)

    def test_series_budget_untouched_and_prepare_uses_the_wrapper(self):
        self.assertEqual((V100 / "series_budget.sh").read_bytes(),
                         (ROOT / "results/v0.9.0-qualification/series_budget.sh").read_bytes())
        self.assertIn('sh "$HERE/attempt_budget.sh" attempt "$ATTEMPT" "$CAP" "$CAMP"-attempt[1-9]', PREPARE)
        self.assertNotIn('sh "$HERE/series_budget.sh"', PREPARE)

    def test_protocol_states_the_part1_outcome(self):
        self.assertIn("the failed cell is **FAIL**", PROTOCOL)
        self.assertIn("**not run**, each with", PROTOCOL)


# -- B4 -------------------------------------------------------------------------------------------
class QAttemptTwoTest(unittest.TestCase):
    def part3(self, root: Path, run: dict, failures=()):
        d = root / "part3"
        d.mkdir(parents=True)
        (d / "run.json").write_text(json.dumps(run))
        with open(d / "failures.jsonl", "w") as handle:
            for f in failures:
                handle.write(json.dumps(f) + "\n")
        return d

    def test_every_branch(self):
        product = {"step": "round1-candidate", "failed_cell": "L1 G100k C=16", "classification": "not_infrastructure"}
        infra = {"step": "round1-candidate", "failed_cell": "L1 G100k C=16", "classification": "infrastructure"}
        cases = {
            "complete": ({"status": "COMPLETE"}, [infra], False),
            "complete with product": ({"status": "COMPLETE"}, [product], False),
            "cap": ({"status": "NONCONFORMING", "cap_reached": True}, [product], True),
            "infrastructure exhausted": ({"status": "NONCONFORMING", "cap_reached": False,
                                          "infrastructure_exhausted": ["round1-candidate:L1 G100k C=16"]}, [infra, infra], True),
            "nonconforming without cause": ({"status": "NONCONFORMING"}, [], False),
            "runner error": ({"status": "FAILED", "cause": "runner error"}, [infra], True),
            "runner error after product": ({"status": "FAILED", "cause": "runner error"}, [product], False),
            "other": ({"status": "INCOMPLETE"}, [], False),
        }
        for name, (run, failures, allowed) in cases.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as d:
                self.assertEqual(q.attempt2_gate(self.part3(Path(d), run, failures))[0], allowed)
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(q.attempt2_gate(Path(d))[0])  # no run.json

    def test_marker_and_final_attempt_only(self):
        with tempfile.TemporaryDirectory() as d:
            part3 = self.part3(Path(d), {"status": "NONCONFORMING", "cap_reached": True})
            roots = mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d})
            roots.start()
            self.addCleanup(roots.stop)
            with mock.patch("sys.stdout"):
                self.assertEqual(q.main(["--attempt2-gate", str(part3), "--write-marker", "other"]), 2)
                self.assertEqual(q.main(["--attempt2-gate", str(part3), "--write-marker", "part3-attempt2"]), 0)
            marker = json.loads((part3 / "superseded_by.json").read_text())
            self.assertEqual(marker["superseded_by"], "part3-attempt2")
            with mock.patch("sys.stderr"):
                self.assertEqual(q.main(["--attempt2-gate", str(part3)]), 1)  # once only
            with self.assertRaisesRegex(SystemExit, "superseded"):
                ev.evaluate(part3)

    def test_evaluator_carries_product_failures_of_the_superseded_attempt(self):
        qt = base.QTest()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            qt.run_q(root, base.FakeTool(fail={("round2-candidate", "L1 G100k C=16"): "panicked: knotrel-server crashed"}))
            (root / "part3" / "superseded_by.json").write_text(json.dumps({"superseded_by": "part3-attempt2"}))
            camp = qt.camp(root)
            r = q.QRunner(camp, root / "part3-attempt2", clock=base.Clock(), launch=base.FakeTool(), state=base.good_state)
            with mock.patch.dict(os.environ, {"KNOTREL_PG_ADMIN_URL": "postgres://x"}), mock.patch("sys.stdout"):
                r.run()
            out = ev.evaluate(root / "part3-attempt2")
            (root / "part3" / "superseded_by.json").unlink()
            with self.assertRaisesRegex(SystemExit, "superseded_by.json"):
                ev.evaluate(root / "part3-attempt2")
        self.assertEqual(out["final_attempt"], "part3-attempt2")
        self.assertEqual(out["criteria"]["Q1"]["status"], "FAIL")
        self.assertTrue(any("carried from superseded part3" in x for x in out["criteria"]["Q1"]["failed_observations"]))
        self.assertEqual(out["criteria"]["Q4"]["status"], "PASS")

    def test_run_part3_refuses_attempt2_after_complete(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "camp"
            (camp / "src/cand").mkdir(parents=True)
            os.symlink(ROOT, camp / "src/cand/knotrel-benchmarks")
            (camp / "logs").mkdir()
            (camp / "logs/CONFORMANCE.txt").write_text("CONFORMING: ok\n")
            self.part3(camp, {"status": "COMPLETE"}, [{"failed_cell": "x", "classification": "infrastructure"}])
            proc = subprocess.run(["sh", str(V100 / "run_part3.sh"), str(camp), "2"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 3)
        self.assertIn("COMPLETE", proc.stderr)
        self.assertNotIn("superseded_by", "".join(os.listdir(camp / "part3")) if (camp / "part3").exists() else "")

    def test_marker_written_only_after_postgres_is_ready(self):
        self.assertLess(PART3.index("SELECT 1"), PART3.index("--write-marker part3-attempt2"))
        self.assertLess(PART3.index("--write-marker part3-attempt2"), PART3.index('run_v100q_q.py" "$CAMP" "$OUT"'))


# -- N1 -------------------------------------------------------------------------------------------
class PostgresStartTest(unittest.TestCase):
    def test_start_is_checked_and_trapped(self):
        trap = PART3.index("stop-test-postgres.sh")
        start = PART3.index('PGOUT=$(bash "$F/scripts/start-test-postgres.sh" 18')
        self.assertLess(trap, start)
        line = PART3[start:PART3.index("\n", start)]
        self.assertTrue(line.endswith("|| PGRC=$?"), line)  # exit status kept, not masked by a pipe
        self.assertNotIn("| tail", line)
        self.assertIn("postgres://*", PART3)
        for check in ("pg_isready", "SELECT 1"):
            self.assertLess(PART3.index(check), PART3.index('run_v100q_q.py" "$CAMP" "$OUT"'))
        self.assertIn("classification infrastructure", PART3)
        self.assertIn("exit 4", PART3)
        self.assertNotIn('echo "$URL"', PART3)
        self.assertNotIn("$PGOUT\" >", PART3)


# -- N4, N5, S1 -----------------------------------------------------------------------------------
class QRunnerFixesTest(unittest.TestCase):
    def test_rerun_allowance_is_per_observation(self):
        disk = "Error: No space left on device (os error 28)"
        tool = base.FakeTool(fail={("round1-candidate", "L1 G100k C=64"): disk,
                                   ("round2-candidate", "L1 G100k C=64"): disk})
        with tempfile.TemporaryDirectory() as d:
            r, _ = base.QTest().run_q(Path(d), tool)
            failures = [json.loads(x) for x in (Path(d) / "part3/failures.jsonl").read_text().splitlines()]
        self.assertEqual([f["rerun"] for f in failures], [True, True])
        self.assertEqual(set(r.reruns), {"round1-candidate:L1 G100k C=64", "round2-candidate:L1 G100k C=64"})
        self.assertEqual(r.status, "COMPLETE")

    def test_unavailable_pmset_is_no_power_evidence(self):
        ok = base.good_state(None)
        unavailable = dict(ok, power="unavailable: [Errno 2] No such file or directory: 'pmset'",
                           therm="unavailable: [Errno 2]")
        self.assertEqual(q.classify_failure("anything", unavailable, unavailable)["classification"], "not_infrastructure")
        self.assertEqual(q.classify_failure("anything", ok, dict(ok, power=""))["classification"], "not_infrastructure")
        battery = dict(ok, power="Now drawing from 'Battery Power'\n -InternalBattery-0 80%")
        self.assertEqual(q.classify_failure("anything", ok, battery)["classification"], "infrastructure")

    def test_pg_process_patterns_removed(self):
        self.assertIn("LOAD_PG_PROCESS_PATTERNS", q.REMOVED_ENV)
        r = q.QRunner(Path("/c"), Path("/o"))
        with mock.patch.dict(os.environ, {"KNOTREL_PG_ADMIN_URL": "postgres://x", "LOAD_PG_PROCESS_PATTERNS": "x"}):
            self.assertNotIn("LOAD_PG_PROCESS_PATTERNS", r.env(Path("/s"), ["L1 G100k C=16"], Path("/d")))


# -- S2 -------------------------------------------------------------------------------------------
class QVerdictTest(unittest.TestCase):
    def test_zero_reference_median_gives_no_verdict(self):
        values = {("reference", "L1 G100k C=16"): {"rps": 0.0}}
        with tempfile.TemporaryDirectory() as d:
            base.QTest().run_q(Path(d), base.FakeTool(values=values))
            out = ev.evaluate(Path(d) / "part3")
        q5 = out["criteria"]["Q5"]
        self.assertIsNone(q5["status"])
        self.assertIn("median is 0", q5["no_verdict_reason"])
        self.assertIsNone(out["q_pass"])

    def test_nonconforming_keeps_a_known_product_fail(self):
        clock = base.Clock()
        clock.deadline_hint = 1000.0 + 1800.0
        tool = base.FakeTool(clock=clock, per_step=400.0,
                             fail={("round1-candidate", "L2 G100k C=64"): "thread 'main' panicked: feeder not ready"})
        with tempfile.TemporaryDirectory() as d:
            r, _ = base.QTest().run_q(Path(d), tool, clock=clock)
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual(r.status, "NONCONFORMING")
        self.assertEqual(out["criteria"]["Q4"]["status"], "FAIL")
        self.assertFalse(out["q_pass"])

    def test_failed_reference_observation_gives_q5_no_verdict(self):
        tool = base.FakeTool(fail={("round2-reference", "L1 G100k C=16"): "thread 'main' panicked: knotrel-server"})
        with tempfile.TemporaryDirectory() as d:
            base.QTest().run_q(Path(d), tool)
            out = ev.evaluate(Path(d) / "part3")
        self.assertEqual(out["q_status"], "COMPLETE")
        self.assertIsNone(out["criteria"]["Q5"]["status"])
        self.assertIn("reference observation failed", out["criteria"]["Q5"]["no_verdict_reason"])
        self.assertEqual(out["criteria"]["Q1"]["status"], "PASS")
        self.assertIn("no verdict, not FAIL", PROTOCOL)


# -- S3 -------------------------------------------------------------------------------------------
class PrepareDirectoryTest(unittest.TestCase):
    def test_checks_before_the_campaign_directory_and_failure_marker(self):
        mkdir = PREPARE.index('mkdir -p "$CAMP/logs"')
        for check in ('freeze_check_v100q.py" record', 'attempt_budget.sh" attempt',
                      'check_restored.sh" || exit 3', "CAND_VERSION="):
            self.assertLess(PREPARE.index(check), mkdir, check)
        self.assertIn("PREPARE-FAILED.txt", PREPARE)
        self.assertLess(mkdir, PREPARE.index("trap 'RC=$?"))
        self.assertIn("PREPARE-FAILED.txt", PROTOCOL)


# -- B5, S4 ---------------------------------------------------------------------------------------
class DecisionRuleTest(unittest.TestCase):
    def test_matrix_rule_is_split(self):
        rule = " ".join(MATRIX["v1_0_0"]["decision_rule"])
        self.assertIn("REGRESSION or FAIL blocks v1.0.0-rc.1", rule)
        self.assertIn("a disposition does not lift it", rule)
        self.assertIn("INCONCLUSIVE, INCONCLUSIVE_DISCLOSED and UNRESOLVED", rule)
        self.assertIn("INVALID, NONCONFORMING and not run follow plan section 5.5", rule)
        self.assertIn("Q3, if not PASS, needs a disposition and a documented operational envelope", rule)
        self.assertIn("E6 stays explicitly unqualified and needs its own, separate disposition", rule)
        self.assertIn("never converted", rule)
        self.assertNotIn("non-PASS results (REGRESSION, FAIL", rule)

    def test_protocol_rule_and_a_regression(self):
        section = PROTOCOL[PROTOCOL.index("## 7. Decision rule"):PROTOCOL.index("## 8.")]
        for needle in ("**blocks**", "a disposition\n  does not lift it", "INCONCLUSIVE_DISCLOSED", "**separate**",
                       "operational\n  envelope", "**never converted**", "INVALID, NONCONFORMING and not run"):
            self.assertIn(needle, section)
        self.assertIn("an INCONCLUSIVE\n  primary with median > t is REGRESSION", PROTOCOL)


# -- S5 -------------------------------------------------------------------------------------------
LOAD_RS = """const CELLS: &[Cell] = &[
""" + "".join(f'    Cell {{\n        scenario: "{c.split()[0]}",\n        graph: "{c.split()[1]}",\n        clients: {c.split("=")[1]},\n    }},\n'
              for c in q.CANDIDATE_CELLS) + "];\n"


class QCellsTest(unittest.TestCase):
    def test_cells_against_the_tool(self):
        self.assertEqual(q.tool_cell_keys(LOAD_RS), list(q.CANDIDATE_CELLS))
        self.assertEqual(q.cell_problems(LOAD_RS), [])
        self.assertTrue(q.cell_problems(LOAD_RS.replace('graph: "G10k"', 'graph: "G20k"')))
        swapped = LOAD_RS.replace("clients: 16", "clients: X").replace("clients: 64", "clients: 16").replace("clients: X", "clients: 64")
        self.assertTrue(any("order" in p for p in q.cell_problems(swapped)))
        self.assertTrue(q.cell_problems("fn main() {}"))
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "load.rs"
            path.write_text(LOAD_RS)
            with mock.patch("sys.stdout"), mock.patch.dict(os.environ, {"LIFECYCLE_QUALIFICATION_ROOTS": d}):
                self.assertEqual(q.main(["--check-cells", str(path)]), 0)

    def test_launch_env_check_runs_it(self):
        env = (V100 / "launch_env_check.sh").read_text()
        self.assertIn("run Q-cells python3 scripts/run_v100q_q.py --check-cells", env)
        self.assertIn("integrations/postgres-feeder/examples/load.rs", env)


if __name__ == "__main__":
    unittest.main()
