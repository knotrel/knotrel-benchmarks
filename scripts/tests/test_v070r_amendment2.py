"""Tests for amendment 2 of the v0.7.0 re-qualification (controller kind "terminal").

Process tables are synthetic; no test starts Terminal, quits Claude or touches launchd.
"""

import importlib.util
import itertools
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import conformance_monitor as cm  # noqa: E402

REPO = SCRIPTS.parent
RQ = REPO / "results/v0.7.0-requalification"
FREEZE_A1 = "8b931e1f7b930142334f02149c7e36411ee2174a"

TERM = cm.TERMINAL_EXE
CLAUDE_APP = "/Applications/Claude.app/Contents/MacOS/Claude"
CLAUDE_CLI = "/Users/rt/Library/Application Support/Claude/claude-code/2.1.325/x/claude.app/Contents/MacOS/claude"


def P(pid, ppid, path, comm=None, stat="S"):
    return cm.Proc(pid, ppid, 0.0, comm or (path or "?"), path, 0.0, stat)


def terminal_tree(extra=()):
    """launchd -> Terminal -> login -> -zsh -> caffeinate -> sh (chain) -> python3 (campaign)."""
    return [P(1, 0, "/sbin/launchd"), P(100, 1, TERM), P(101, 100, "/usr/bin/login", "login"),
            P(102, 101, "/bin/zsh", "-zsh"), P(103, 102, "/usr/bin/caffeinate"), P(104, 103, "/bin/sh"),
            P(105, 104, "/usr/bin/python3"), P(200, 1, "/usr/libexec/logd"),
            P(201, 1, "/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder")] + list(extra)


class TerminalPolicy(unittest.TestCase):
    def test_valid(self):
        pol = cm.build_policy_terminal(terminal_tree(), 104, ["/x/helper"])
        self.assertEqual((pol.controller_pid, pol.controller_children, pol.controller_kind), (100, {101, 102, 103}, "terminal"))
        self.assertEqual(pol.baseline_paths, {"/x/helper"})

    def refused(self, procs, chain=104, needle=""):
        with self.assertRaises(cm.PolicyError) as ctx:
            cm.build_policy_terminal(procs, chain, [])
        self.assertIn(needle, str(ctx.exception))

    def test_claude_running_refused(self):
        self.refused(terminal_tree([P(300, 1, CLAUDE_APP)]), needle="Claude")
        self.refused(terminal_tree([P(300, 1, "/Applications/Claude.app/Contents/Frameworks/Claude Helper.app/Contents/MacOS/Claude Helper")]), needle="Claude")
        self.refused(terminal_tree([P(300, 1, CLAUDE_CLI)]), needle="Claude")
        self.refused(terminal_tree([P(300, 1, "/opt/homebrew/bin/claude")]), needle="Claude")
        self.refused(terminal_tree([P(300, 1, None, "claude")]), needle="Claude")

    def test_zombie_claude_ignored(self):
        cm.build_policy_terminal(terminal_tree([P(300, 1, None, "claude", "Z")]), 104, [])

    def test_second_tab_refused(self):
        self.refused(terminal_tree([P(110, 100, "/usr/bin/login", "login"), P(111, 110, "/bin/zsh", "-zsh")]),
                     needle="other live descendants")

    def test_command_beside_chain_refused(self):
        self.refused(terminal_tree([P(112, 102, "/usr/bin/tee")]), needle="other live descendants")

    def test_second_terminal_refused(self):
        self.refused(terminal_tree([P(120, 1, TERM)]), needle="more than one Terminal")

    def test_not_under_terminal_refused(self):
        procs = [P(1, 0, "/sbin/launchd"), P(50, 1, "/Applications/iTerm.app/Contents/MacOS/iTerm2"),
                 P(51, 50, "/bin/zsh"), P(104, 51, "/bin/sh")]
        self.refused(procs, needle="not Terminal.app")

    def test_terminal_not_under_launchd_refused(self):
        procs = terminal_tree()
        procs[1] = P(100, 77, TERM)
        procs.append(P(77, 1, "/usr/bin/script"))
        self.refused(procs, needle="not Terminal.app")

    def test_non_apple_ancestor_refused(self):
        procs = terminal_tree()
        procs[3] = P(102, 101, "/opt/homebrew/bin/zsh", "-zsh")
        self.refused(procs, needle="Apple location")

    def test_chain_without_ancestors_refused(self):
        self.refused([P(1, 0, "/sbin/launchd"), P(104, 1, "/bin/sh")], needle="")


class TerminalClassify(unittest.TestCase):
    def classes(self, extra=(), fg=None):
        procs = terminal_tree(extra)
        pol = cm.build_policy_terminal(terminal_tree(), 104, ["/x/helper"])
        return {p.pid: c for p, c in cm.classify(procs, pol, fg or {})}

    def test_lineage_is_baseline_before_deny_list(self):
        c = self.classes()
        self.assertEqual([c[i] for i in (100, 101, 102, 103)], ["baseline"] * 4)
        self.assertEqual((c[104], c[105]), ("campaign", "campaign"))
        self.assertEqual(c[200], "system")

    def test_new_terminal_descendant_forbidden(self):
        c = self.classes([P(110, 100, "/usr/bin/login", "login"), P(111, 102, "/bin/ls")])
        self.assertEqual((c[110], c[111]), ("forbidden", "forbidden"))

    def test_claude_forbidden_everywhere(self):
        c = self.classes([P(300, 1, CLAUDE_APP), P(301, 300, CLAUDE_CLI), P(302, 1, "/usr/bin/claude"),
                          P(303, 301, "/Library/Developer/CommandLineTools/usr/bin/git")])
        self.assertEqual([c[i] for i in (300, 301, 302, 303)], ["forbidden"] * 4)

    def test_foreground(self):
        fg = {100: TERM, 201: "/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder", 300: CLAUDE_APP,
              301: "/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app/Contents/MacOS/Safari"}
        c = self.classes([P(300, 1, CLAUDE_APP), P(301, 1, fg[301])], fg)
        self.assertEqual((c[100], c[201], c[300], c[301]), ("baseline", "system", "forbidden", "forbidden"))

    def test_deny_list_and_baseline_unchanged(self):
        c = self.classes([P(400, 1, "/usr/bin/git"), P(401, 1, "/x/helper"), P(402, 1, "/Applications/Other.app/x")])
        self.assertEqual((c[400], c[401], c[402]), ("forbidden", "baseline", "forbidden"))


def _frozen_monitor():
    src = subprocess.run(["git", "-C", str(REPO), "show", f"{FREEZE_A1}:scripts/conformance_monitor.py"],
                         capture_output=True, text=True, check=True).stdout
    tmp = tempfile.NamedTemporaryFile("w", suffix="_frozen_monitor.py", delete=False)
    tmp.write(src)
    tmp.close()
    spec = importlib.util.spec_from_file_location("frozen_monitor", tmp.name)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["frozen_monitor"] = mod
    spec.loader.exec_module(mod)
    os.unlink(tmp.name)
    return mod


class ClaudeCliModeUnchanged(unittest.TestCase):
    """The amendment-1 (claude-cli) classification is identical to the frozen monitor's."""

    def test_classification_parity(self):
        old = _frozen_monitor()
        paths = [None, "/sbin/launchd", "/usr/bin/login", "/bin/zsh", "/usr/bin/git", "/usr/libexec/x", CLAUDE_APP,
                 CLAUDE_CLI, TERM, "/x/helper", "/Applications/Other.app/x", "/usr/bin/caffeinate",
                 "/System/Applications/Mail.app/Contents/PlugIns/a.appex/x"]
        tree = [(1, 0), (10, 1), (11, 10), (12, 11), (13, 12), (14, 13), (15, 10), (16, 1), (17, 16), (18, 14)]
        cases = 0
        for combo in itertools.product(range(len(paths)), repeat=3):
            new_procs, old_procs = [], []
            for i, (pid, ppid) in enumerate(tree):
                path = paths[combo[i % 3]] if pid not in (1, 10, 13) else {1: "/sbin/launchd", 10: CLAUDE_CLI, 13: "/bin/sh"}[pid]
                stat = "Z" if pid == 17 and combo[0] == 0 else "S"
                new_procs.append(P(pid, ppid, path, os.path.basename(path or "claude"), stat))
                old_procs.append(old.Proc(pid, ppid, 0.0, os.path.basename(path or "claude"), path, 0.0, stat))
            fg = {16: paths[combo[1]] or "", 11: paths[combo[2]] or ""}
            new_pol = cm.Policy(13, 10, {11, 12}, {"/x/helper"})
            old_pol = old.Policy(13, 10, {11, 12}, {"/x/helper"})
            self.assertEqual([c for _, c in cm.classify(new_procs, new_pol, fg)],
                             [c for _, c in old.classify(old_procs, old_pol, fg)], combo)
            cases += 1
        self.assertGreater(cases, 1000)

    def test_build_policy_parity(self):
        old = _frozen_monitor()
        procs = [P(1, 0, "/sbin/launchd"), P(10, 1, CLAUDE_CLI), P(11, 10, "/bin/zsh"), P(12, 11, "/usr/bin/caffeinate"), P(13, 12, "/bin/sh")]
        oprocs = [old.Proc(p.pid, p.ppid, 0.0, p.comm, p.path, 0.0, p.stat) for p in procs]
        self.assertEqual(cm.build_policy(procs, 13, 10, []).to_json() | {"controller_kind": None},
                         old.build_policy(oprocs, 13, 10, []).to_json() | {"controller_kind": None})

    def test_old_policy_file_loads_as_claude_cli(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.json"
            f.write_text(json.dumps({"chain_pid": 5, "controller_pid": 4, "controller_children": [3], "baseline_paths": []}))
            self.assertEqual(cm.Policy.load(f).controller_kind, "claude-cli")
            f.write_text(json.dumps({"chain_pid": 5, "controller_kind": "other"}))
            with self.assertRaises(ValueError):
                cm.Policy.load(f)

    def test_policy_round_trip_terminal(self):
        pol = cm.build_policy_terminal(terminal_tree(), 104, [])
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.json"
            f.write_text(json.dumps(pol.to_json()))
            self.assertEqual(cm.Policy.load(f), pol)


class TreeStateAndCli(unittest.TestCase):
    def test_tree_state_detects_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a").mkdir()
            (root / "a/s.jsonl").write_text("x")
            before = cm.tree_state(root)
            self.assertEqual(before, cm.tree_state(root))
            (root / "a/sub.jsonl").write_text("y")
            self.assertNotEqual(before, cm.tree_state(root))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "conformance_monitor.py"), *args], capture_output=True, text=True)

    def test_policy_argument_rules(self):
        with tempfile.TemporaryDirectory() as d:
            m = Path(d) / "m.json"
            m.write_text(json.dumps({"conformance": {"host_baseline": []}}))
            out = str(Path(d) / "p.json")
            r = self.run_cli("policy", "--chain", "1", "--controller", "2", "--controller-kind", "terminal", "--matrix", str(m), "--out", out)
            self.assertEqual(r.returncode, 1)
            self.assertIn("not used with --controller-kind terminal", r.stderr)
            r = self.run_cli("policy", "--chain", "1", "--matrix", str(m), "--out", out)
            self.assertEqual(r.returncode, 1)
            self.assertIn("--controller is required", r.stderr)
            # This test process does not descend from Terminal.app (or Claude is running): refused.
            r = self.run_cli("policy", "--chain", str(os.getpid()), "--controller-kind", "terminal", "--matrix", str(m), "--out", out)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(Path(out).exists())


class Chain(unittest.TestCase):
    text = (RQ / "run_final_chain.sh").read_text()

    def test_controller_check_before_quiesce(self):
        t = self.text
        pre = t.index('policy "$L/policy-prequiesce.json"')
        kind = t.index('[ "$(conf controller_kind)" = terminal ]')
        self.assertLess(t.index("pmset -g batt | head -1"), kind)
        self.assertLess(kind, pre)
        self.assertLess(pre, t.index("python3 scripts/launcher_audit.py quiesce"))

    def test_no_claude_controller_left(self):
        for gone in ("TRANSCRIPT", "CONTROLLER", "validate-transcript", "session-state", "--controller \""):
            self.assertNotIn(gone, self.text)
        self.assertIn("--controller-kind terminal", self.text)
        self.assertIn('tree-state "$CLAUDE_STATE_DIR"', self.text)
        self.assertIn("CLAUDE_STATE_DIR=$HOME/.claude/projects", self.text)

    def test_session_state_compared_at_gates(self):
        gate = self.text[self.text.index("gate_check() {"):self.text.index("# --- Prelaunch")]
        self.assertIn('"$(session_state)" != "$SESSION_BEFORE"', gate)
        self.assertIn("~/.claude/projects (after $1)\" 16", gate)

    def test_policy_after_grace_and_audit(self):
        t = self.text
        self.assertLess(t.index('sleep "$GRACE"'), t.index('policy "$G/policy.json"'))
        self.assertLess(t.index('--out "$L/launcher-audit.json"'), t.index('policy "$G/policy.json"'))


class Prepare(unittest.TestCase):
    def test_series_a1_closed(self):
        soak = subprocess.run(["sh", str(RQ / "prepare_soak.sh"), "deadbeef", "2", "a1"], capture_output=True, text=True)
        self.assertEqual(soak.returncode, 3)
        self.assertIn("closed", soak.stderr)
        prep = (RQ / "prepare_campaign.sh").read_text()
        a2 = prep.index("FREEZE-A2.json")
        a1 = prep.index("series a1 is closed")
        self.assertLess(a2, a1)
        self.assertIn("v0.7.0-requalification-a2-soak[1-9]", prep)
        self.assertIn("['amendment_2']['attempts_cap']", prep)

    def test_soak_budget_counted_across_amendments(self):
        soak = (RQ / "prepare_soak.sh").read_text()
        call = soak.index('series_budget.sh" soak "$N" "$MAX" /Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-a*-soak[1-9]')
        self.assertLess(call, soak.index("mkdir"))
        prep = (RQ / "prepare_campaign.sh").read_text()
        self.assertLess(prep.index('series_budget.sh" attempt "$ATTEMPT" "$CAP" "$CAMP-$SERIES"-attempt[1-9]'),
                        prep.index('mkdir -p "$CAMP/logs"'))

    def budget(self, kind, n, cap, results):
        with tempfile.TemporaryDirectory() as d:
            dirs = []
            for i, first in enumerate(results, 1):
                x = Path(d) / f"x-{i}"
                (x / "logs").mkdir(parents=True)
                if first is not None:
                    (x / "logs/CONFORMANCE.txt").write_text(first + "\nmore\n")
                dirs.append(str(x))
            return subprocess.run(["sh", str(RQ / "series_budget.sh"), kind, str(n), str(cap), *dirs, str(Path(d) / "x-[1-9]")],
                                  capture_output=True, text=True).returncode

    def test_series_budget(self):
        self.assertEqual(self.budget("soak", 2, 2, ["SOAK NONCONFORMING: x"]), 0)
        self.assertEqual(self.budget("soak", 3, 2, ["SOAK NONCONFORMING: x", "SOAK NONCONFORMING: y"]), 1)
        self.assertEqual(self.budget("soak", 3, 2, ["SOAK NONCONFORMING: x", "SOAK NOT STARTED: y"]), 0)
        self.assertEqual(self.budget("soak", 2, 2, []), 1)          # numbers are never skipped
        self.assertEqual(self.budget("soak", 1, 2, ["SOAK NONCONFORMING"]), 1)  # nor reused
        self.assertEqual(self.budget("soak", 2, 2, [None]), 1)      # prepared, never launched
        self.assertEqual(self.budget("attempt", 1, 3, []), 0)
        self.assertEqual(self.budget("attempt", 3, 3, ["NONCONFORMING: a", "NOT STARTED: b"]), 0)
        self.assertEqual(self.budget("attempt", 4, 3, ["NONCONFORMING: a", "NONCONFORMING: b", "FAILED: c"]), 1)
        self.assertEqual(self.budget("attempt", 2, 3, ["CONFORMING: every gate check passed"]), 1)

    def test_launch_command_written(self):
        for name, needle in (("prepare_soak.sh", "run_final_chain.sh $CAMP - --soak"),
                             ("prepare_campaign.sh", "run_final_chain.sh $CAMP $CAND >")):
            text = (RQ / name).read_text()
            self.assertIn(needle, text, name)
            self.assertIn("LAUNCH-COMMAND.txt", text, name)
            self.assertIn("caffeinate -dimsu sh", text, name)
            self.assertNotIn("| tee", text, name)


class MatrixAmendment2(unittest.TestCase):
    def test_only_declared_keys_change_from_amendment_1(self):
        frozen = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{FREEZE_A1}:results/v0.7.0-requalification/MATRIX.json"],
                                           capture_output=True, text=True, check=True).stdout)
        new = json.loads((RQ / "MATRIX.json").read_text())
        self.assertEqual(set(frozen) ^ set(new), set())
        self.assertEqual({k for k in new if new[k] != frozen[k]}, {"status", "conformance"})
        fc, nc = frozen["conformance"], new["conformance"]
        self.assertEqual({k for k in set(fc) | set(nc) if fc.get(k) != nc.get(k)},
                         {"outcome", "quiesce", "controller_kind", "amendment_2"})
        self.assertTrue(nc["outcome"].startswith(fc["outcome"]))
        fq, nq = fc["quiesce"], nc["quiesce"]
        self.assertEqual({k for k in set(fq) | set(nq) if fq.get(k) != nq.get(k)}, {"allow_jobs_prefix"})
        self.assertEqual(set(nq["allow_jobs_prefix"]), {"application.com.apple.Terminal."})
        self.assertEqual(nq["allow_jobs_prefix"]["application.com.apple.Terminal."]["program_prefix"], cm.TERMINAL_APP)
        self.assertEqual(nq["allow_jobs_prefix"]["application.com.apple.Terminal."]["triggers"], [])

    def test_amendment_2_record(self):
        c = json.loads((RQ / "MATRIX.json").read_text())["conformance"]
        a = c["amendment_2"]
        self.assertEqual(c["controller_kind"], "terminal")
        self.assertEqual((a["attempt_series"], a["attempts_cap"], a["first_conforming_attempt_is_final"]), ("a2", 3, True))
        self.assertEqual(c["soak"]["max_soaks"], 2)
        for key in ("controller", "classes", "claude_state", "soak_budget", "scope_note", "limits", "closed_series"):
            self.assertTrue(a.get(key), key)


if __name__ == "__main__":
    unittest.main()
