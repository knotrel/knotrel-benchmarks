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
        self.refused(procs, needle="must be exactly")

    def test_lineage_must_be_exact(self):
        base = terminal_tree()
        for idx, path in ((3, "/usr/bin/osascript"), (3, "/usr/bin/sudo"), (4, "/usr/bin/open"), (4, "/usr/bin/script"),
                          (3, "/bin/bash"), (2, "/usr/bin/sudo")):
            procs = list(base)
            procs[idx] = P(procs[idx].pid, procs[idx].ppid, path)
            self.refused(procs, needle="must be exactly")
        # deny-listed or sudo ancestor inserted between caffeinate and the chain
        procs = list(base)
        procs[5] = P(104, 106, "/bin/sh")
        procs.append(P(106, 103, "/usr/bin/sudo"))
        self.refused(procs, needle="must be exactly")
        # without caffeinate
        procs = [p for p in base if p.pid != 103]
        procs[[p.pid for p in procs].index(104)] = P(104, 102, "/bin/sh")
        self.refused(procs, needle="must be exactly")

    def test_claude_cli_installs_detected(self):
        self.refused(terminal_tree([P(300, 1, "/Users/rt/.local/share/claude/versions/2.0.65", "2.0.65")]), needle="Claude")
        procs = terminal_tree([P(301, 1, "/opt/homebrew/Cellar/node/22/bin/node", "node")])
        with self.assertRaises(cm.PolicyError):
            cm.build_policy_terminal(procs, 104, [], [(301, "node /opt/homebrew/lib/node_modules/@anthropic-ai/claude-code/cli.js")])
        cm.build_policy_terminal(terminal_tree(), 104, [], [(999, "node claude-code (exited)")])  # not in the table

    def test_policy_records_paths(self):
        pol = cm.build_policy_terminal(terminal_tree(), 104, [])
        self.assertEqual(pol.controller_paths, {100: TERM, 101: "/usr/bin/login", 102: "/bin/zsh", 103: "/usr/bin/caffeinate"})

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

    def test_reused_lineage_pid_not_baseline(self):
        procs = terminal_tree()
        pol = cm.build_policy_terminal(procs, 104, [])
        later = [p for p in procs if p.pid not in (103,)] + [P(103, 1, "/usr/bin/git"), P(101, 1, CLAUDE_APP)]
        later = [p for p in later if not (p.pid == 101 and p.path == "/usr/bin/login")]
        c = {p.pid: cls for p, cls in cm.classify(later, pol, {101: CLAUDE_APP})}
        self.assertEqual((c[103], c[101]), ("forbidden", "forbidden"))

    def test_reused_lineage_pid_not_ancestor(self):
        procs = terminal_tree()
        pol = cm.build_policy_terminal(procs, 104, [])
        # caffeinate (103) died: the chain is reparented to launchd; PID 103 is reused by a new
        # /usr/bin/caffeinate in a new Terminal tab, with the same recorded path.
        later = [p for p in procs if p.pid not in (103, 104, 105)] + [P(104, 1, "/bin/sh"), P(105, 104, "/usr/bin/python3"),
                                                                      P(110, 100, "/usr/bin/login", "login"), P(103, 110, "/usr/bin/caffeinate")]
        c = {p.pid: cls for p, cls in cm.classify(later, pol, {})}
        self.assertEqual(c[103], "forbidden")
        self.assertEqual(c[110], "forbidden")

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
        drop = {"controller_kind": None, "controller_paths": None}
        self.assertEqual(cm.build_policy(procs, 13, 10, []).to_json() | drop, old.build_policy(oprocs, 13, 10, []).to_json() | drop)

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

    def test_tree_state_fails_closed(self):
        t = self.text
        self.assertIn('&& [ -n "$_S" ] && echo "$_S" || echo "TREE-STATE-FAILED"', t)
        self.assertIn('[ "$S1" != TREE-STATE-FAILED ] && [ "$S2" != TREE-STATE-FAILED ] ||', t)
        gate = t[t.index("gate_check() {"):t.index("# --- Prelaunch")]
        self.assertNotIn('[ -n "$SESSION_BEFORE" ]', gate)

    def test_environment_recorded(self):
        self.assertIn('echo "python3: $(command -v python3)', self.text)
        self.assertIn("environment names:", self.text)

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
        self.assertEqual(self.budget("soak", 3, 2, ["SOAK NONCONFORMING: x", "SOAK NOT STARTED: y"]), 1)  # every directory counts
        self.assertEqual(self.budget("soak", 2, 2, []), 1)          # numbers are never skipped
        self.assertEqual(self.budget("soak", 1, 2, ["SOAK NONCONFORMING"]), 1)  # nor reused
        self.assertEqual(self.budget("soak", 2, 2, [None]), 1)      # no CONFORMANCE.txt
        self.assertEqual(self.budget("attempt", 1, 3, []), 0)
        self.assertEqual(self.budget("attempt", 3, 3, ["NONCONFORMING: a", "NOT STARTED: b"]), 0)
        self.assertEqual(self.budget("attempt", 4, 3, ["NONCONFORMING: a", "NOT STARTED: b", "FAILED: c"]), 1)
        self.assertEqual(self.budget("attempt", 2, 3, ["CONFORMING: every gate check passed"]), 1)

    def test_launch_command_used(self):
        for name in ("prepare_soak.sh", "prepare_campaign.sh"):
            text = (RQ / name).read_text()
            self.assertIn('launch_command.sh" "$CAMP"', text, name)
            self.assertIn("LAUNCH-COMMAND.txt", text, name)

    def test_launch_command_shape(self):
        camp = "/e/v0.7.0-requalification-a2-soak2"
        out = subprocess.run(["sh", str(RQ / "launch_command.sh"), camp, "-", "--soak"], capture_output=True, text=True, check=True).stdout
        r = camp + "/src/cand/knotrel-benchmarks/results/v0.7.0-requalification"
        self.assertTrue(out.startswith("export PATH="), out)
        self.assertIn(":/usr/bin:/bin:/usr/sbin:/sbin; cd /; ", out)
        pre = out.index(f"if /usr/bin/caffeinate -dimsu /bin/sh {r}/precheck_terminal.sh {camp} < /dev/null; then ")
        chain = out.index(f"/usr/bin/caffeinate -dimsu /bin/sh {r}/run_final_chain.sh {camp} - --soak < /dev/null >> {camp}/chain-launch.log 2>&1;")
        self.assertLess(pre, chain)
        self.assertIn('echo "chain exit=$?" >> ' + camp + "/chain-launch.log", out)
        self.assertTrue(out.rstrip().endswith("; fi"))
        self.assertNotIn("| ", out)
        self.assertNotIn("> " + camp + "/chain-launch.log", out.replace(">> " + camp + "/chain-launch.log", ""))
        bad = subprocess.run(["sh", str(RQ / "launch_command.sh"), "/e/x y", "-"], capture_output=True, text=True)
        self.assertNotEqual(bad.returncode, 0)

    def test_precheck_refuses_launched_campaign_and_starts_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "v0.7.0-requalification-a2-soak2"
            (camp / "src/cand/knotrel-benchmarks").mkdir(parents=True)
            (camp / "logs").mkdir()
            (camp / "gate").mkdir()
            r = subprocess.run(["sh", str(RQ / "precheck_terminal.sh"), str(camp)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("PRECHECK REFUSED", r.stdout)
            self.assertIn("already launched", r.stdout)
            self.assertEqual(sorted(p.name for p in (camp / "logs").iterdir()), [])
        r = subprocess.run(["sh", str(RQ / "precheck_terminal.sh"), "/nonexistent/x"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)

    def test_launch_command_parses_in_zsh(self):
        for args in (["/e/v0.7.0-requalification-a2-soak2", "-", "--soak"], ["/e/v0.7.0-requalification-e75ff6a-a2-attempt1", "e" * 40]):
            out = subprocess.run(["sh", str(RQ / "launch_command.sh"), *args], capture_output=True, text=True, check=True).stdout
            self.assertEqual(subprocess.run(["/bin/zsh", "-n", "-c", out]).returncode, 0, out)

    def test_launch_command_path_is_campaign_bin(self):
        camp = "/e/v0.7.0-requalification-a2-soak2"
        out = subprocess.run(["sh", str(RQ / "launch_command.sh"), camp, "-", "--soak"], capture_output=True, text=True, check=True).stdout
        self.assertTrue(out.startswith(f"export PATH={camp}/bin:/usr/bin:/bin:/usr/sbin:/sbin; "), out)
        for name in ("prepare_soak.sh", "prepare_campaign.sh"):
            text = (RQ / name).read_text()
            link = text.index('ln -s "$(command -v python3)" "$CAMP/bin/python3"')
            self.assertLess(link, text.index('launch_command.sh" "$CAMP"'), name)

    def test_precheck_runs_policy_read_only(self):
        t = (RQ / "precheck_terminal.sh").read_text()
        self.assertIn("policy --chain $$ --controller-kind terminal", t)
        for forbidden in ("launcher_audit", "mkdir", "rm ", "run_final_chain", "bootout", "mv "):
            self.assertNotIn(forbidden, t.split("set -u", 1)[1])


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


STUB_AUDIT = r"""
import os, sys
open(os.environ["STUB_ORDER"], "a").write(sys.argv[1] + "\n")
sys.exit(0 if sys.argv[1] == "restore" else 1)
"""
STUB_MONITOR = r"""
import os, sys
open(os.environ["STUB_ORDER"], "a").write(sys.argv[1] + "\n")
if sys.argv[1] == "policy" and os.environ.get("STUB_POLICY") == "fail":
    print("policy refused: Claude processes are running", file=sys.stderr)
    sys.exit(1)
print("{}")
"""


def _ac_power():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    return "AC Power" in out.splitlines()[0] if out else False


@unittest.skipUnless(_ac_power(), "the chain checks AC power before the controller check")
class PrequiesceRefusalExecuted(unittest.TestCase):
    """The real chain against a stub tooling clone: a refused controller check stops it before the quiesce."""

    def test_refused_before_quiesce(self):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d) / "v0.7.0-requalification-a2-soak2"
            b = camp / "src/cand/knotrel-benchmarks"
            (b / "scripts").mkdir(parents=True)
            (b / "results/v0.7.0-requalification").mkdir(parents=True)
            (camp / "logs").mkdir()
            (b / "scripts/launcher_audit.py").write_text(STUB_AUDIT)
            (b / "scripts/conformance_monitor.py").write_text(STUB_MONITOR)
            (b / "results/v0.7.0-requalification/MATRIX.json").write_text('{"conformance": {"controller_kind": "terminal"}}')
            order = Path(d) / "order.txt"
            env = {**os.environ, "STUB_ORDER": str(order), "STUB_POLICY": "fail"}
            r = subprocess.run(["sh", str(RQ / "run_final_chain.sh"), str(camp), "-", "--soak"], env=env, capture_output=True, text=True, timeout=60)
            self.assertEqual(r.returncode, 4, r.stdout + r.stderr)
            calls = order.read_text().splitlines()
            self.assertEqual(calls[0], "policy")
            self.assertNotIn("quiesce", calls)
            self.assertNotIn("restore", calls)
            self.assertTrue((camp / "logs/CONFORMANCE.txt").read_text().startswith("SOAK NOT STARTED: controller check refused"))
            self.assertFalse((camp / "logs/quiesce-restore.json").exists())


@unittest.skipUnless(_ac_power(), "the precheck checks AC power first")
class PrecheckRefusalsExecuted(unittest.TestCase):
    """precheck_terminal.sh against a stub tooling clone: refusals start nothing and write only logs/precheck-*."""

    def run_precheck(self, policy="ok", check="ok"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        camp = Path(tmp.name) / "v0.7.0-requalification-a2-soak2"
        b = camp / "src/cand/knotrel-benchmarks"
        (b / "scripts").mkdir(parents=True)
        (b / "results/v0.7.0-requalification").mkdir(parents=True)
        (camp / "logs").mkdir()
        (b / "scripts/conformance_monitor.py").write_text(STUB_PRECHECK_MONITOR)
        (b / "results/v0.7.0-requalification/MATRIX.json").write_text('{"conformance": {"controller_kind": "terminal"}}')
        (b / "results/v0.7.0-requalification/check_restored.sh").write_text("exit 0\n")
        order = Path(tmp.name) / "order.txt"
        env = {**os.environ, "STUB_ORDER": str(order), "STUB_POLICY": policy, "STUB_CHECK": check}
        r = subprocess.run(["sh", str(RQ / "precheck_terminal.sh"), str(camp)], env=env, capture_output=True, text=True, timeout=60)
        written = sorted(p.name for p in (camp / "logs").iterdir())
        others = sorted(str(p.relative_to(camp)) for p in camp.rglob("*") if p.is_file() and "logs" not in p.parts and "src" not in p.parts)
        return r, order.read_text().splitlines() if order.exists() else [], written, others

    def test_policy_refusal(self):
        r, calls, written, others = self.run_precheck(policy="fail")
        self.assertEqual(r.returncode, 1)
        self.assertIn("PRECHECK REFUSED: policy refused", r.stdout)
        self.assertEqual(calls, ["policy"])
        self.assertTrue(set(written) <= {"precheck-policy.json", "precheck-policy-error.txt"}, written)
        self.assertEqual(others, [])

    def test_check_refusal(self):
        r, calls, written, others = self.run_precheck(check="fail")
        self.assertEqual(r.returncode, 1)
        self.assertIn("forbidden processes running", r.stdout)
        self.assertEqual(calls, ["policy", "check"])
        self.assertTrue(all(w.startswith("precheck-") for w in written), written)
        self.assertEqual(others, [])

    def test_ok(self):
        r, calls, written, others = self.run_precheck()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("PRECHECK OK", r.stdout)
        self.assertEqual(calls, ["policy", "check", "tree-state"])
        self.assertTrue(all(w.startswith("precheck-") for w in written), written)
        self.assertEqual(others, [])


STUB_PRECHECK_MONITOR = r"""
import os, sys
open(os.environ["STUB_ORDER"], "a").write(sys.argv[1] + "\n")
args = dict(zip(sys.argv[2::2], sys.argv[3::2]))
if sys.argv[1] == "policy":
    if os.environ["STUB_POLICY"] == "fail":
        print("policy refused: Claude processes are running", file=sys.stderr)
        sys.exit(1)
    open(args["--out"], "w").write("{}")
elif sys.argv[1] == "check" and os.environ["STUB_CHECK"] == "fail":
    print('{"pid": 7, "path": "/Applications/Docker.app/x"}')
    sys.exit(1)
else:
    print("{}")
"""


if __name__ == "__main__":
    unittest.main()
