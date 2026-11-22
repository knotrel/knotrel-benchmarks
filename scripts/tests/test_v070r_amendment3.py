"""Tests for amendment 3 of the v0.7.0 re-qualification (background processes allowed)."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical  # noqa: E402

historical.ensure()  # earlier campaigns are read from their release tags

import conformance_monitor as cm  # noqa: E402
from test_v070r_amendment2 import P, terminal_tree, CLAUDE_APP, CLAUDE_CLI, TERM  # noqa: E402

REPO = SCRIPTS.parent
RQ = REPO / "results/v0.7.0-requalification"
FREEZE_A2 = "564ced8da54929435209bbfb4bedae7a511f7268"


def policy(background=True):
    pol = cm.build_policy_terminal(terminal_tree(), 104, ["/x/helper"])
    pol.background_allowed = background
    return pol


def classes(extra=(), fg=None, background=True, claude_pids=frozenset()):
    return {p.pid: c for p, c in cm.classify(terminal_tree(extra), policy(background), fg or {}, set(claude_pids))}


class BackgroundClass(unittest.TestCase):
    def test_unresolved_and_unknown_are_background(self):
        c = classes([P(500, 1, None, "(CacheDeleteExten)"), P(501, 1, "/Applications/WhatsApp.app/x"),
                     P(502, 1, "/Users/rt/Library/Application Support/Google/GoogleUpdater/x")])
        self.assertEqual((c[500], c[501], c[502]), ("background", "background", "background"))
        off = classes([P(500, 1, None, "(CacheDeleteExten)"), P(501, 1, "/Applications/WhatsApp.app/x")], background=False)
        self.assertEqual((off[500], off[501]), ("forbidden", "forbidden"))

    def test_real_interference_stays_forbidden(self):
        fg = {600: "/Applications/Safari.app/Contents/MacOS/Safari"}
        c = classes([P(600, 1, fg[600]), P(601, 1, "/opt/homebrew/bin/git"), P(602, 1, None, "cargo"),
                     P(603, 1, CLAUDE_APP), P(604, 1, CLAUDE_CLI), P(605, 100, "/usr/bin/login", "login"),
                     P(606, 102, "/bin/ls"), P(607, 1, "/usr/bin/ssh")], fg)
        for pid in (600, 601, 602, 603, 604, 605, 606, 607):
            self.assertEqual(c[pid], "forbidden", pid)

    def test_unresolved_or_parenthesised_names_stay_forbidden(self):
        c = classes([P(800, 1, None, "(git)"), P(801, 1, None, "(claude)"), P(802, 1, None, "Claude Helper"),
                     P(803, 1, None, "(diskimages-help)"), P(804, 1, None, "(cargo)"), P(805, 1, None, "(ssh)"),
                     P(806, 1, None, "(CacheDeleteExten)")])
        self.assertEqual([c[i] for i in (800, 801, 802, 803, 804, 805)], ["forbidden"] * 6)
        self.assertEqual(c[806], "background")

    def test_interpreters_and_cmdline_claude_forbidden(self):
        py = "/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python"
        node = "/Users/rt/.nvm/versions/node/v20.19.3/bin/node"
        c = classes([P(900, 1, py), P(901, 1, node), P(902, 1, "/opt/x/runner")], claude_pids={902})
        self.assertEqual((c[900], c[901], c[902]), ("forbidden", "forbidden", "forbidden"))
        # campaign interpreters are unaffected
        c = classes([P(903, 104, py)])
        self.assertEqual(c[903], "campaign")

    def test_claude_pids_cache(self):
        orig = cm.claude_cmdlines
        calls = []
        cm.claude_cmdlines = lambda: calls.append(1) or [(42, "node claude-code")]
        cm._CLAUDE_PIDS["t"] = 0.0
        try:
            self.assertEqual(cm.claude_pids_cached(), {42})
            self.assertEqual(cm.claude_pids_cached(), {42})
            self.assertEqual(len(calls), 1)
        finally:
            cm.claude_cmdlines = orig
            cm._CLAUDE_PIDS["t"] = 0.0

    def test_system_baseline_campaign_unchanged(self):
        c = classes([P(700, 1, "/usr/libexec/x"), P(701, 1, "/x/helper")])
        self.assertEqual((c[700], c[701], c[100], c[103], c[104]), ("system", "baseline", "baseline", "campaign", "campaign"))

    def test_forbidden_list_excludes_background(self):
        procs = terminal_tree([P(500, 1, None, "(CacheDeleteExten)"), P(601, 1, "/usr/bin/git")])
        found = cm.forbidden(procs, policy(), lambda pid: True, {})
        self.assertEqual([r["pid"] for r in found], [601])

    def test_policy_load_rules(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "p.json"
            f.write_text(json.dumps(policy().to_json()))
            self.assertTrue(cm.Policy.load(f).background_allowed)
            f.write_text(json.dumps({"chain_pid": 5, "controller_pid": 4, "background_allowed": True}))
            with self.assertRaises(ValueError):
                cm.Policy.load(f)  # claude-cli kind cannot allow background

    def test_policy_cli_reads_matrix(self):
        src = (SCRIPTS / "conformance_monitor.py").read_text()
        self.assertIn('policy.background_allowed = bool(json.loads(args.matrix.read_text())["conformance"].get("background_allowed", False))', src)


class ChainAndPrepare(unittest.TestCase):
    chain = (RQ / "run_final_chain.sh").read_text()

    def test_audit_record_mode(self):
        self.assertIn("get('launcher_audit','gate')", self.chain)
        self.assertEqual(self.chain.count('|| audit_failed "logs/launcher-audit'), 2)
        self.assertNotIn('--out "$L/launcher-audit.json" 2> "$L/launcher-audit.txt" || notstarted', self.chain)
        self.assertIn('launcher_audit.py quiesce --matrix "$MATRIX" --camp "$CAMP" > "$L/quiesce.log" 2>&1 || notstarted', self.chain)

    def test_prepare_campaign_a3(self):
        prep = (RQ / "prepare_campaign.sh").read_text()
        a3 = prep.index("FREEZE-A3.json")
        self.assertLess(a3, prep.index("FREEZE-A2.json"))
        block = prep[a3:prep.index("elif", a3)]
        self.assertIn('[ "$SERIES" = a3 ]', block)
        self.assertIn("['amendment_3']['attempts_cap']", block)
        self.assertIn("series_budget.sh", block)
        self.assertIn("check_restored.sh", block)
        self.assertNotIn("SOAK", block)

    def test_prepare_soak_refuses_a3(self):
        soak = (RQ / "prepare_soak.sh").read_text()
        self.assertLess(soak.index("FREEZE-A3.json"), soak.index("mkdir"))
        self.assertIn("amendment 3 has no soaks", soak)


CHAIN_PY = ("conformance_monitor.py", "conformance_gate.py", "launcher_audit.py", "run_v070r_collect.py",
            "run_p0_aa.py", "run_lifecycle_qualification.py", "run_v060_qualification.py",
            "analyze_bc_qualification.py", "prepare_bc_qualification.py")
CALLS = {"run", "runner", "check_output", "check_call", "call", "Popen", "command", "optional_command"}


def bare_name_calls():
    """Programs run by bare name in the chain's Python code: {name: [file:line]}."""
    import ast
    found = {}
    for name in CHAIN_PY:
        tree = ast.parse((SCRIPTS / name).read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            func = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
            first = node.args[0]
            if func in CALLS and isinstance(first, (ast.List, ast.Tuple)) and first.elts \
                    and isinstance(first.elts[0], ast.Constant) and isinstance(first.elts[0].value, str) \
                    and "/" not in first.elts[0].value:
                found.setdefault(first.elts[0].value, []).append(f"{name}:{node.lineno}")
    return found


class LaunchEnvironment(unittest.TestCase):
    """Amendment 3, revision 2 (PROTOCOL.md 10.7): a3-2 failed at B/C on a missing rustc."""
    tools = {l.strip() for l in (RQ / "launch_tools.txt").read_text().splitlines() if l.strip() and not l.startswith("#")}
    check = RQ / "launch_env_check.sh"

    def test_launch_tools_cover_every_bare_name_call(self):
        calls = bare_name_calls()
        self.assertIn("rustc", calls)  # the a3-2 cause (run_lifecycle_qualification provenance)
        self.assertIn("git", calls)
        self.assertEqual(set(calls), self.tools, calls)

    def test_system_tools_resolve_without_camp_bin(self):
        for tool in self.tools - {"rustc"}:
            r = subprocess.run(["/bin/sh", "-c", f"command -v {tool}"], capture_output=True, text=True,
                               env={"PATH": "/usr/bin:/bin:/usr/sbin:/sbin"})
            self.assertEqual(r.returncode, 0, tool)

    def test_prepare_links_rustc_and_runs_the_check_before_the_launch_command(self):
        prep = (RQ / "prepare_campaign.sh").read_text()
        link, check, launch = (prep.index('ln -s "$(command -v rustc)" "$CAMP/bin/rustc"'),
                               prep.index("launch_env_check.sh"), prep.index("launch_command.sh\""))
        self.assertLess(link, check)
        self.assertLess(check, launch)
        self.assertIn('env -i HOME="$HOME"', prep)
        self.assertIn('PATH="$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/sh', prep)

    def test_precheck_runs_the_check_before_ok(self):
        pre = (RQ / "precheck_terminal.sh").read_text()
        self.assertLess(pre.index("launch_env_check.sh"), pre.index('echo "PRECHECK OK'))
        self.assertIn('"$L/precheck-launch-env.txt"', pre)

    def test_check_runs_every_collector_dry_run_with_the_chain_arguments(self):
        text = self.check.read_text()
        chain = (RQ / "run_final_chain.sh").read_text()
        for step in ("a", "bc", "r", "rmem", "mdesc", "mreg"):
            self.assertIn(f"scripts/run_v070r_collect.py {step} ", text, step)
        self.assertEqual(text.count("--dry-run"), 6)
        # Every collector: the same arguments as the chain, apart from --out (and A's --execute).
        a_chain = chain[chain.index("run_v070r_collect.py a --manifest \"$A/plan"):].split("\n")[0]
        self.assertIn(a_chain[a_chain.index("--manifest"):a_chain.index(" --execute")], text)
        bc_chain = chain[chain.index("run_v070r_collect.py bc"):].split("\n")[0]
        self.assertIn(bc_chain[bc_chain.index("--profile"):bc_chain.index(" >")], text)
        for name in ("R", "Rmem", "Mdesc", "Mreg"):
            line = chain[chain.index(f"step {name} "):].split("\n")[0]
            args = line[line.index(f'--out "$CAMP/{name}" ') + len(f'--out "$CAMP/{name}" '):]
            self.assertIn(f'--out "$D-{name}" {args} --dry-run', text, name)
        self.assertIn('D=${OUT%.txt}-dryrun', text)
        self.assertIn("unset KNOTREL_GATE_DIR", text)
        self.assertIn("rustc +1.100.0 -Vv", text)

    def _run(self, path, bin_entries):
        with tempfile.TemporaryDirectory() as d:
            camp = Path(d)
            (camp / "bin").mkdir()
            for e in bin_entries:
                (camp / "bin" / e).symlink_to("/usr/bin/true")
            (camp / "src/cand/knotrel-benchmarks").mkdir(parents=True)
            out = camp / "report.txt"
            r = subprocess.run(["/bin/sh", str(self.check), str(camp), str(out)], capture_output=True, text=True,
                               env={"PATH": path.replace("CAMP", str(camp)), "HOME": os.environ["HOME"]})
            return r, out.read_text() if out.exists() else ""

    def test_check_refuses_another_path(self):
        r, report = self._run("CAMP/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin", ["python3", "rustc"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("LAUNCH-ENV FAILED: PATH is", report)

    def test_check_refuses_camp_bin_without_rustc(self):
        r, report = self._run("CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin", ["python3"])
        self.assertEqual(r.returncode, 1)
        self.assertIn("CAMP/bin must hold exactly python3 and rustc", report)


class MatrixAmendment3(unittest.TestCase):
    def test_only_declared_keys_change_from_amendment_2(self):
        frozen = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{FREEZE_A2}:results/v0.7.0-requalification/MATRIX.json"],
                                           capture_output=True, text=True, check=True).stdout)
        new = json.loads((RQ / "MATRIX.json").read_text())
        self.assertEqual({k for k in set(frozen) | set(new) if frozen.get(k) != new.get(k)}, {"status", "conformance"})
        fc, nc = frozen["conformance"], new["conformance"]
        self.assertEqual({k for k in set(fc) | set(nc) if fc.get(k) != nc.get(k)},
                         {"outcome", "background_allowed", "launcher_audit", "amendment_3"})
        self.assertTrue(nc["outcome"].startswith(fc["outcome"]))
        self.assertEqual(fc["deny_basenames"], nc["deny_basenames"])

    def test_record(self):
        c = json.loads((RQ / "MATRIX.json").read_text())["conformance"]
        a = c["amendment_3"]
        self.assertIs(c["background_allowed"], True)
        self.assertEqual(c["launcher_audit"], "record")
        self.assertEqual((a["attempt_series"], a["attempts_cap"], a["first_conforming_attempt_is_final"]), ("a3", 3, True))
        for key in ("decision", "cause", "changes", "interference", "closed_series", "soak", "retroactivity", "review"):
            self.assertTrue(a.get(key), key)


if __name__ == "__main__":
    unittest.main()
