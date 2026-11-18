"""Tests for the v0.7.0 re-qualification conformance tooling.

Covers:
- scripts/conformance_monitor.py: classification rules, policy validation,
  the HID reset rule, CPU-time parsing, the Git snapshot and a short real
  monitor run;
- scripts/conformance_gate.py: before/after checks, the deferred stop, log
  offsets across children, CPU accounting, waiting for heartbeats, the
  end-of-chain checks and gating verification;
- scripts/run_v070r_collect.py: which calls are gated, for A, B/C and R/M;
- results/v0.7.0-requalification: the matrix and prepare script differ from
  the first campaign's only in the declared items.

Process tables, the clock, HID readings, foreground apps and power state are
injected. No real process is part of a test's expected classification.
"""

import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import conformance_gate as cg  # noqa: E402
import conformance_monitor as cm  # noqa: E402
import run_v070r_collect as rc  # noqa: E402

REPO = SCRIPTS.parent
CHAIN = 1000
CONTROLLER = 500
CLI = "/Users/u/Library/Application Support/Claude/claude-code/2.1/abc/claude.app/Contents/MacOS/claude"


def proc(pid, ppid, path, cpu=0.0, cputime=0.0, comm=None, stat="S"):
    return cm.Proc(pid, ppid, cpu, comm or (path or "x"), path, cputime, stat)


def table(extra=()):
    rows = [
        proc(1, 0, "/sbin/launchd"),
        proc(400, 1, "/Applications/Claude.app/Contents/MacOS/Claude"),
        proc(CONTROLLER, 400, CLI),
        proc(600, CONTROLLER, "/bin/zsh"),
        proc(650, 600, "/usr/bin/caffeinate"),
        proc(CHAIN, 650, "/bin/sh"),
        proc(1001, CHAIN, "/Library/Frameworks/Python.framework/Versions/3.12/Resources/Python.app/Contents/MacOS/Python"),
        proc(1002, 1001, "/usr/bin/git"),  # a collector's provenance call: campaign by ancestry
        proc(300, 1, "/System/Library/CoreServices/WindowServer"),
        proc(301, 1, "/System/Applications/Weather.app/Contents/PlugIns/WeatherWidget.appex/Contents/MacOS/WeatherWidget"),
        proc(302, 1, "/Library/PrivilegedHelperTools/com.docker.vmnetd"),
        proc(303, 1, "/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder"),
    ]
    return rows + list(extra)


def policy():
    return cm.build_policy(table(), CHAIN, CONTROLLER, ["/Library/PrivilegedHelperTools/com.docker.vmnetd"])


FOREGROUND = {303: "/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder",
              400: "/Applications/Claude.app/Contents/MacOS/Claude"}


class Classification(unittest.TestCase):
    def classes(self, rows, fg=None):
        return {p.pid: c for p, c in cm.classify(rows, policy(), fg if fg is not None else FOREGROUND)}

    def test_policy_contents(self):
        p = policy()
        self.assertEqual(p.controller_children, {600, 650})

    def test_allowed_classes(self):
        c = self.classes(table())
        self.assertEqual(c[CHAIN], "campaign")
        self.assertEqual(c[1002], "campaign", "git run by the chain is campaign, not forbidden")
        for pid in (CONTROLLER, 600, 650, 400, 302):
            self.assertEqual(c[pid], "baseline", pid)
        for pid in (300, 301, 303):
            self.assertEqual(c[pid], "system", pid)
        self.assertEqual(cm.forbidden(table(), policy(), foreground=FOREGROUND), [])

    def test_forbidden_examples(self):
        extra = [
            proc(2001, 1, "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            proc(2002, 1, "/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal"),
            proc(2003, 1, "/usr/bin/git"),
            proc(2004, 1, "/System/Library/PrivateFrameworks/DiskImages2.framework/XPCServices/diskimages-helper"),
            proc(2005, 1, "/System/Library/Frameworks/AppKit.framework/Versions/C/XPCServices/com.apple.appkit.xpc.openAndSavePanelService.xpc/Contents/MacOS/com.apple.appkit.xpc.openAndSavePanelService"),
            proc(2006, 400, CLI),  # another Claude Code session
            proc(2007, CONTROLLER, "/bin/zsh"),  # new descendant of the controller: a tool call
            proc(2008, 1, "/opt/homebrew/bin/htop"),
            proc(2009, 1, "/Library/Developer/CommandLineTools/usr/bin/git-remote-https"),
            proc(2010, 1, "/usr/libexec/sshd-session"),
            proc(2011, 1, "/System/Volumes/Preboot/Cryptexes/App/System/Applications/Safari.app/Contents/MacOS/Safari"),
            proc(2012, 1, "/System/Library/CoreServices/DiskImageMounter.app/Contents/MacOS/DiskImageMounter"),
            proc(2013, 2007, "/usr/bin/top"),  # grandchild of a tool call
        ]
        fg = {**FOREGROUND, 2011: "Safari", 2012: "DiskImageMounter"}
        c = self.classes(table(extra), fg)
        for pid in range(2001, 2014):
            self.assertEqual(c[pid], "forbidden", pid)

    def test_unresolved_and_dead(self):
        rows = table([proc(3001, 1, None, comm="ghost"), proc(3002, 1, None, comm="git")])
        alive = [r["pid"] for r in cm.forbidden(rows, policy(), alive=lambda pid: True)]
        dead = [r["pid"] for r in cm.forbidden(rows, policy(), alive=lambda pid: False)]
        self.assertEqual(alive, [3001, 3002])
        self.assertEqual(dead, [3002], "a dead process with a deny-listed comm is still reported")

    def test_zombie_takes_parent_class(self):
        rows = table([proc(4001, 1001, None, comm="<defunct>", stat="Z"),
                      proc(4002, 300, None, comm="<defunct>", stat="Z"),
                      proc(4003, 1, None, comm="<defunct>", stat="Z")])
        c = self.classes(rows)
        self.assertEqual((c[4001], c[4002], c[4003]), ("campaign", "system", "system"))

    def test_tool_call_zombie_is_forbidden(self):
        c = self.classes(table([proc(4004, CONTROLLER, None, comm="<defunct>", stat="Z")]))
        self.assertEqual(c[4004], "forbidden")

    def test_kernel_is_system(self):
        self.assertEqual(self.classes(table([proc(0, 0, None, comm="kernel_task")]))[0], "system")


class Foreground(unittest.TestCase):
    SAMPLE = """ 1) "loginwindow" ASN:0x0-0x3003:
    executable path="/System/Library/CoreServices/loginwindow.app/Contents/MacOS/loginwindow"
    pid = 487 type="UIElement" flavor=3
 2) "Finder" ASN:0x0-0x1:
    executable path="/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder"
    pid = 760 type="Foreground" flavor=3
 3) "NoPath" ASN:0x0-0x2:
    pid = 900 type="Foreground" flavor=3
"""

    def run_with(self, stdout, code=0):
        saved = cm.subprocess.run
        cm.subprocess.run = lambda *a, **k: subprocess.CompletedProcess(a, code, stdout, "")
        try:
            return cm.foreground_pids()
        finally:
            cm.subprocess.run = saved

    def test_parse_and_path_reset(self):
        self.assertEqual(self.run_with(self.SAMPLE),
                         {760: "/System/Library/CoreServices/Finder.app/Contents/MacOS/Finder", 900: ""})

    def test_failure_raises(self):
        with self.assertRaises(cm.ForegroundUnavailable):
            self.run_with("", 1)
        with self.assertRaises(cm.ForegroundUnavailable):
            self.run_with("nothing")


class Session(unittest.TestCase):
    def test_session_state_includes_subagents(self):
        with tempfile.TemporaryDirectory() as tmp:
            t = Path(tmp) / "abc.jsonl"
            t.write_text("x\n")
            (Path(tmp) / "abc" / "subagents").mkdir(parents=True)
            sub = Path(tmp) / "abc" / "subagents" / "agent-1.jsonl"
            sub.write_text("a\n")
            before = cm.session_state(t)
            self.assertEqual(len(before), 2)
            sub.write_text("a\nb\n")
            self.assertNotEqual(before, cm.session_state(t))

    def test_validate_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            outside = Path(tmp) / "s.jsonl"
            outside.write_text("run_final_chain.sh /camp\n")
            self.assertTrue(cm.validate_transcript(outside, "/camp", time.time()))
        projects = Path.home() / ".claude" / "projects"
        if projects.is_dir():
            with tempfile.TemporaryDirectory(dir=projects) as tmp:
                good = Path(tmp) / "s.jsonl"
                good.write_text("caffeinate -dimsu sh run_final_chain.sh /camp/x e75 32478\n")
                self.assertEqual(cm.validate_transcript(good, "/camp/x", time.time()), [])
                self.assertTrue(cm.validate_transcript(good, "/camp/y", time.time()))
                self.assertTrue(cm.validate_transcript(good, "/camp/x", time.time() + 3600))


class PolicyValidation(unittest.TestCase):
    def test_refusals(self):
        with self.assertRaisesRegex(cm.PolicyError, "not running"):
            cm.build_policy(table(), CHAIN, 777, [])
        with self.assertRaisesRegex(cm.PolicyError, "not an ancestor"):
            cm.build_policy(table([proc(5000, 400, CLI)]), CHAIN, 5000, [])
        with self.assertRaisesRegex(cm.PolicyError, "not a Claude Code CLI"):
            cm.build_policy(table(), CHAIN, 400, [])  # the desktop app
        with self.assertRaisesRegex(cm.PolicyError, "not a Claude Code CLI"):
            cm.build_policy(table(), CHAIN, 600, [])  # the shell
        with self.assertRaisesRegex(cm.PolicyError, "other live descendants"):
            cm.build_policy(table([proc(5001, CONTROLLER, "/bin/zsh"),
                                   proc(5002, 5001, "/Users/u/.cargo/bin/cargo")]), CHAIN, CONTROLLER, [])

    def test_zombie_child_does_not_refuse(self):
        cm.build_policy(table([proc(5003, CONTROLLER, None, comm="<defunct>", stat="Z")]), CHAIN, CONTROLLER, [])


class Helpers(unittest.TestCase):
    def test_hid_reset(self):
        self.assertFalse(cm.hid_reset(10.0, 100.0, 11.0, 101.0))
        self.assertFalse(cm.hid_reset(10.0, 100.0, 10.2, 101.0), "0.8 s read latency is within tolerance")
        self.assertTrue(cm.hid_reset(10.0, 100.0, 0.4, 101.0), "input between readings")
        self.assertTrue(cm.hid_reset(200.0, 100.0, 5.0, 109.0), "input long before the second reading")

    def test_parse_cputime(self):
        self.assertAlmostEqual(cm.parse_cputime("0:01.50"), 1.5)
        self.assertAlmostEqual(cm.parse_cputime("252:19.14"), 252 * 60 + 19.14)
        self.assertAlmostEqual(cm.parse_cputime("1-02:03:04.00"), 86400 + 7384)

    def test_git_snapshot_detects_fetch_and_skips_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "r"
            (repo / ".git" / "logs" / "refs" / "remotes" / "origin").mkdir(parents=True)
            log = repo / ".git" / "logs" / "refs" / "remotes" / "origin" / "main"
            log.write_text("a\n")
            (Path(tmp) / "targets" / "x" / ".git").mkdir(parents=True)
            before = cm.git_snapshot(Path(tmp))
            self.assertEqual(list(before), [str(repo / ".git")])
            log.write_text("a\nb\n")
            self.assertNotEqual(before, cm.git_snapshot(Path(tmp)))

    def test_real_monitor_short_run(self):
        """The monitor writes heartbeats, HID records and status, and stops when the chain is gone."""
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            chain = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(3)"])
            (d / "policy.json").write_text(json.dumps(cm.Policy(chain.pid).to_json()))
            mon = subprocess.Popen([sys.executable, str(SCRIPTS / "conformance_monitor.py"), "monitor",
                                    "--policy", str(d / "policy.json"), "--out", str(d / "log.jsonl"),
                                    "--status", str(d / "status.json"), "--interval", "0.2"])
            chain.wait()
            self.assertEqual(mon.wait(timeout=10), 0)
            rows = [json.loads(line) for line in (d / "log.jsonl").read_text().splitlines()]
            beats = [r["t"] for r in rows if r.get("k") == "s"]
            self.assertGreaterEqual(len(beats), 8)
            self.assertLess(max(b - a for a, b in zip(beats, beats[1:])), 1.0)
            self.assertTrue(any(r.get("k") == "h" for r in rows))
            self.assertEqual(rows[-1]["reason"], "chain_gone")
            self.assertEqual(json.loads((d / "status.json").read_text())["seq"], len(beats))


class FakeHost:
    """Injected snapshot, HID, foreground, power, liveness and clock for the gate."""

    def __init__(self, directory: Path):
        self.dir = directory
        self.now = 1000.0
        self.mono = 50.0
        self.idle = 500.0
        self.rows = table()
        self.fg = dict(FOREGROUND)
        self.power_error = None
        self.monitor_alive = True
        (directory / "policy.json").write_text(json.dumps(policy().to_json()))
        self.status()
        (directory / "activity-monitor.jsonl").write_text("")

    def status(self, **extra):
        data = {"pid": 4242, "t": self.now, "seq": 1, "violations_total": 0, "hid_resets_total": 0,
                "hid_failures": 0, "hid_idle": self.idle}
        data.update(extra)
        (self.dir / "monitor-status.json").write_text(json.dumps(data))

    def beats(self, start, end, step=0.2, violation_at=None, reset_at=None):
        with open(self.dir / "activity-monitor.jsonl", "a") as handle:
            t = start
            while t <= end + 1e-9:
                v = [{"pid": 9, "path": "/Applications/X.app/Contents/MacOS/X"}] \
                    if violation_at is not None and abs(t - violation_at) < 0.11 else []
                handle.write(json.dumps({"k": "s", "t": round(t, 3), "seq": 0, "v": v}) + "\n")
                t += step
            if reset_at is not None:
                handle.write(json.dumps({"k": "h", "t": reset_at, "idle": 0.1, "reset": True}) + "\n")

    def advance(self, seconds, cpu=0.0):
        self.now += seconds
        self.mono += seconds
        self.idle += seconds
        for p in self.rows:
            if p.pid == 300:
                p.cputime_s += cpu
        self.status()

    def gate(self):
        return cg.Gate(self.dir, snapshot=lambda: copy.deepcopy(self.rows), hid=lambda: (self.idle, self.mono),
                       foreground=lambda: self.fg, power=lambda: self.power_error,
                       alive=lambda pid: self.monitor_alive, clock=lambda: self.now)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.host = FakeHost(self.dir)

    def tearDown(self):
        self.tmp.cleanup()

    def stopped(self):
        return (self.dir / "gate-stop.json").exists()

    def run_child(self, g, seconds=2.0, cpu=0.0, **beats):
        g.before("x:child")
        start = self.host.now
        self.host.beats(start - 0.1, start + seconds + 0.1, **beats)
        self.host.advance(seconds, cpu)
        return g.after("x:child", start, start + seconds)

    def records(self):
        return [json.loads(line) for line in (self.dir / "gate-log.jsonl").read_text().splitlines()]

    def test_conforming_children_and_offsets(self):
        g = self.host.gate()
        self.assertTrue(self.run_child(g, cpu=0.5))
        self.assertTrue(self.run_child(g, cpu=1.25))
        self.assertTrue(self.run_child(g, seconds=0.05))  # shorter than one sample interval
        self.assertFalse(self.stopped())
        cpu = [r["cpu_seconds_by_class"] for r in self.records()]
        self.assertEqual(cpu[0]["system"], 0.5)
        self.assertEqual(cpu[1]["system"], 1.25)
        self.assertGreater(g.offset, 0)

    def test_before_failures(self):
        cases = {
            "forbidden": lambda h: h.rows.append(proc(5000, 1, "/Applications/WhatsApp.app/Contents/MacOS/WhatsApp")),
            "foreground": lambda h: (h.rows.append(proc(5001, 1, "/System/Library/CoreServices/Installer.app/Contents/MacOS/Installer")),
                                     h.fg.__setitem__(5001, "Installer")),
            "stale": lambda h: h.status(t=h.now - 2.0),
            "dead": lambda h: setattr(h, "monitor_alive", False),
            "totals": lambda h: h.status(violations_total=1),
            "power": lambda h: setattr(h, "power_error", "not on AC power"),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                self.tearDown()
                self.setUp()
                mutate(self.host)
                with self.assertRaises(cg.GateStop):
                    self.host.gate().before("x")
                self.assertTrue(self.stopped())

    def test_hid_input_between_checks(self):
        g = self.host.gate()
        g.before("a")
        self.host.advance(3.0)
        self.host.idle = 0.5  # input happened
        with self.assertRaises(cg.GateStop):
            g.before("b")

    def test_after_failure_is_deferred(self):
        g = self.host.gate()
        g.before("x:child")
        start = self.host.now
        self.host.beats(start - 0.1, start + 0.6)
        self.host.beats(start + 2.0, start + 3.1)  # 1.4 s gap inside the child
        self.host.advance(3.0)
        self.assertFalse(g.after("x:child", start, start + 3.0))  # recorded, not raised
        self.assertTrue(self.stopped())
        with self.assertRaises(cg.GateStop):
            g.before("x:next")

    def test_violation_and_reset_in_window(self):
        for kwargs in ({"reset_at": 1001.0}, {"violation_at": 1001.0}):
            with self.subTest(kwargs):
                self.tearDown()
                self.setUp()
                self.assertFalse(self.run_child(self.host.gate(), **kwargs))
                self.assertTrue(self.stopped())

    def test_no_heartbeat_after_end(self):
        g = self.host.gate()
        g.before("x:child")
        start = self.host.now
        self.host.beats(start - 0.1, start + 1.5)
        self.host.advance(2.0)
        self.assertFalse(g.after("x:child", start, start + 2.0))

    def test_quiet_period_without_before_has_no_cpu(self):
        g = self.host.gate()
        start = self.host.now
        self.host.beats(start - 0.1, start + 5.1)
        self.host.advance(5.0)
        self.assertTrue(g.after("quiet-period", start, start + 5.0))
        self.assertIsNone(self.records()[-1]["cpu_seconds_by_class"])

    def test_foreground_unavailable_stops(self):
        g = self.host.gate()

        def fail():
            raise cm.ForegroundUnavailable("lsappinfo exit 1")
        g.foreground = fail
        with self.assertRaises(cg.GateStop):
            g.before("x")

    def test_full_log_check_ignores_torn_line(self):
        g = self.host.gate()
        start = self.host.now
        self.host.beats(start, start + 2.0)
        with open(self.dir / "activity-monitor.jsonl", "a") as handle:
            handle.write('{"k": "s", "t": 10')
        self.host.advance(2.0)
        self.assertEqual(g.full_log_check(start, start + 2.0), [])

    def test_wait_for_heartbeat(self):
        g = cg.Gate(self.dir)
        self.host.status(t=time.time() + 0.1)
        t0 = time.time()
        g.wait_for_heartbeat(time.time())
        self.assertLess(time.time() - t0, 0.2)
        self.host.status(t=time.time() - 10)
        t0 = time.time()
        g.wait_for_heartbeat(time.time())
        self.assertGreaterEqual(time.time() - t0, cg.MAX_HEARTBEAT_GAP_S - 0.05)

    def test_full_log_check(self):
        g = self.host.gate()
        start = self.host.now
        self.host.beats(start, start + 3.0)
        self.host.beats(start + 4.5, start + 6.0)
        self.host.advance(6.0)
        reasons = g.full_log_check(start, start + 6.0)
        self.assertTrue(any("gap" in r for r in reasons))

    def test_verify_gating(self):
        camp = self.dir / "camp"
        (camp / "R").mkdir(parents=True)
        (camp / "R" / "run-log.json").write_text(json.dumps({"children": [{}, {}]}))
        g = self.host.gate()
        self.run_child(g)
        rows = self.records()
        rows[-1]["label"] = "r:one"
        (self.dir / "gate-log.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n")
        self.assertEqual(cg.verify_gating(camp, self.dir), ["r: 2 children recorded by the collector, 1 gated"])

    def test_gated_requires_environment(self):
        saved = os.environ.pop("KNOTREL_GATE_DIR", None)
        cg._GATE = None
        try:
            with self.assertRaises(cg.GateStop):
                cg.gated("x", lambda: None)
        finally:
            if saved is not None:
                os.environ["KNOTREL_GATE_DIR"] = saved


class Wrappers(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.original = rc.conformance_gate.gated
        rc.conformance_gate.gated = lambda label, run: (self.calls.append(label), run())[1]

    def tearDown(self):
        rc.conformance_gate.gated = self.original

    def test_bc_gates_only_declared_binaries(self):
        shim = rc._GatedSubprocess(["/usr/bin/true"])
        shim.run(["true"], capture_output=True)
        shim.run(["/usr/bin/true"], capture_output=True)
        self.assertIs(shim.SubprocessError, subprocess.SubprocessError)
        self.assertEqual(self.calls, ["BC:/usr/bin/true"])
        stops = []
        saved_gate = rc.conformance_gate.gate
        rc.conformance_gate.gate = lambda: type("G", (), {"_stop": lambda self, *a: stops.append(a)})()
        try:
            with self.assertRaises(cg.GateStop):
                shim.run(["/usr/bin/false"])
        finally:
            rc.conformance_gate.gate = saved_gate
        self.assertEqual(len(stops), 1, "the undeclared-program stop is recorded")
        self.assertEqual(rc._measured_binaries(["--core", "/a", "--core-count", "/b", "--http", "/c"]), ["/a", "/b", "/c"])

    def test_a_and_recorder_wrappers_gate(self):
        import run_p0_aa
        import run_v060_qualification
        saved_observe, saved_main = run_p0_aa.observe_child, run_p0_aa.main
        saved_run, saved_rmain = run_v060_qualification.Recorder.run, run_v060_qualification.main
        try:
            run_p0_aa.observe_child = lambda *a, **k: "observed"
            run_p0_aa.main = lambda: run_p0_aa.observe_child(argv=["/bin/probe", "x"], cwd="/", env={}, timeout_seconds=1)
            self.assertEqual(rc._a([]), "observed")
            run_v060_qualification.Recorder.run = lambda self, label, argv: "ran"
            run_v060_qualification.main = lambda: run_v060_qualification.Recorder.run(None, "R-cell", ["/bin/x"])
            self.assertEqual(rc._recorder("r", []), "ran")
            self.assertEqual(run_v060_qualification.MATRIX, rc.MATRIX)
        finally:
            run_p0_aa.observe_child, run_p0_aa.main = saved_observe, saved_main
            run_v060_qualification.Recorder.run, run_v060_qualification.main = saved_run, saved_rmain
        self.assertEqual(self.calls, ["A:/bin/probe x", "r:R-cell"])


def _flatten(value, prefix=""):
    if isinstance(value, dict):
        out = {}
        for key, item in value.items():
            out.update(_flatten(item, f"{prefix}/{key}"))
        return out
    return {prefix: value}


ALLOWED_MATRIX_CHANGES = (
    "/schema", "/references/first_campaign", "/references/proposal", "/rules/R", "/rules/no_waiver_inheritance",
    "/experiments/A/session_seeds", "/experiments/A/extension_seeds", "/experiments/B_C/order_seed",
    "/experiments/R/order_seed", "/experiments/M_reg/order_seed", "/experiments/M_desc/server_processes",
    "/host_conditions/", "/conformance/", "/invalidation/conformance", "/budget/final_estimate_minutes/",
    "/budget/basis", "/budget/attempts_cap", "/analysis",
    "/status",  # amendment 1 (checked against the frozen matrix in test_v070r_amendment1.py)
)


class Matrix(unittest.TestCase):
    def test_deep_diff_only_declared(self):
        first = _flatten(json.loads((REPO / "results/v0.7.0-qualification/MATRIX.json").read_text()))
        new = _flatten(json.loads((REPO / "results/v0.7.0-requalification/MATRIX.json").read_text()))
        changed = {k for k in set(first) | set(new) if first.get(k, "<absent>") != new.get(k, "<absent>")}
        undeclared = sorted(k for k in changed if not k.startswith(ALLOWED_MATRIX_CHANGES))
        self.assertEqual(undeclared, [])
        self.assertIn("order seed experiments.R.order_seed", new["/rules/R"])
        self.assertEqual(new["/experiments/A/session_seeds"], [130720, 130721, 130722])
        self.assertEqual(new["/experiments/A/extension_seeds"], [130730, 130731, 130732])
        self.assertEqual([new[f"/experiments/{e}/order_seed"] for e in ("B_C", "R", "M_reg")], [50720, 60720, 60721])

    def test_matrix_matches_code(self):
        conf = json.loads((REPO / "results/v0.7.0-requalification/MATRIX.json").read_text())["conformance"]
        self.assertEqual(set(conf["deny_basenames"]) - {"git-*"}, cm.DENY_BASENAMES)
        self.assertEqual(cm.DENY_BASENAME_PREFIXES, ("git-",))
        self.assertEqual(conf["hid_tolerance_s"], cm.HID_TOLERANCE_S)
        self.assertEqual(cg.HID_TOLERANCE_S, cm.HID_TOLERANCE_S)

    def test_prepare_script_declared_diff(self):
        old = (REPO / "results/v0.7.0-qualification/prepare_campaign.sh").read_text().splitlines()
        new = (REPO / "results/v0.7.0-requalification/prepare_campaign.sh").read_text().splitlines()
        removed = [line for line in old if line not in new]
        self.assertTrue(all(("130700" in line or "Prepares the frozen" in line or "Usage:" in line
                             or "v0.7.0-qualification-$C8" in line or "Creates /Users" in line
                             or "FREEZE_SHA knotrel-benchmarks commit" in line) for line in removed), removed)
        added = "\n".join(line for line in new if line not in old)
        for needle in ("--source-manifest", "130720 130721 130722", "attempt", "otool -s __TEXT __text"):
            self.assertIn(needle, added)
        self.assertNotIn("cargo", "\n".join(l for l in new if l not in old and not l.startswith("#")).replace("cargo +1.100.0", ""))

    def test_chain_script(self):
        chain = REPO / "results/v0.7.0-requalification/run_final_chain.sh"
        self.assertEqual(subprocess.run(["sh", "-n", str(chain)]).returncode, 0)
        text = chain.read_text()
        for needle in ("130730 130731 130732", "--order-seed 50720", "trap finish EXIT", "conformance_monitor.py policy",
                       "verify_gating", "full_log_check", "session_state", "validate-transcript", "hid-idle"):
            self.assertIn(needle, text)
        self.assertNotIn("scripts/run_p0_aa.py --manifest", text, "A must run through the gate")
        self.assertNotIn("scripts/run_v070_qualification.py", text, "R/M must run through the gate")


if __name__ == "__main__":
    unittest.main()
