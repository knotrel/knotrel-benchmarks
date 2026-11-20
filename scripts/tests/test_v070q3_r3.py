"""Tests of qualification 3 revision 3 (PROTOCOL section 14): the timestamp fix, the proportional
interference gate, unit recovery in the collectors and the autonomous runner. Fixtures and
simulations only: nothing here measures performance."""

import json
import os
import random
import signal
import subprocess
import sys
import tempfile
import time
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import conformance_gate as cg  # noqa: E402
import conformance_monitor as cm  # noqa: E402
import interference_gate as ig  # noqa: E402

MATRIX = json.loads((ROOT / "results" / "v0.7.0-qualification-3" / "MATRIX.json").read_text())


# -- 1. Timestamp defect ---------------------------------------------------------------------
def old_sample_line(t, seq, found):
    """The monitor's heartbeat line before revision 3 (attempt q3-2)."""
    return json.dumps({"k": "s", "t": round(t, 3), "seq": seq, "v": found}) + "\n"


class TimestampDefect(unittest.TestCase):
    def gate(self, tmp, lines, status_t, pid_alive=True):
        d = Path(tmp)
        (d / "activity-monitor.jsonl").write_text("".join(lines))
        (d / "monitor-status.json").write_text(json.dumps({"pid": 4242, "t": status_t}))
        g = cg.Gate.__new__(cg.Gate)
        g.dir, g.log_path, g.status_path = d, d / "activity-monitor.jsonl", d / "monitor-status.json"
        g.stop_path, g.gate_log = d / "gate-stop.json", d / "gate-log.jsonl"
        g.offset, g.cpu_before, g.counter = 0, {}, 0
        g.alive = lambda pid: pid_alive
        g.clock = lambda: status_t + 0.1
        return g

    def beats(self, writer, times):
        return [writer(t, i, []) for i, t in enumerate(times)]

    # The q3-2 incident: child end 1795164979.3412; next heartbeat 0.14 ms later.
    START, END = 1795164979.105, 1795164979.3412
    TIMES = [1795164978.921, 1795164979.131, 1795164979.341341]

    def test_old_rounding_reproduces_the_false_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = self.gate(tmp, self.beats(old_sample_line, self.TIMES), self.TIMES[-1])
            self.assertFalse(g.after("r:incident", self.START, self.END))
            self.assertIn("no heartbeat after the child ended", (Path(tmp) / "gate-stop.json").read_text())

    def test_exact_timestamps_fix_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            g = self.gate(tmp, self.beats(cm.sample_line, self.TIMES), self.TIMES[-1])
            self.assertTrue(g.after("r:incident", self.START, self.END))

    def test_sample_line_is_exact(self):
        for t in self.TIMES + [time.time()]:
            self.assertEqual(json.loads(cm.sample_line(t, 1, []))["t"], t)

    def test_before_equal_after_end(self):
        with tempfile.TemporaryDirectory() as tmp:  # coincident with the end: covered
            g = self.gate(tmp, self.beats(cm.sample_line, [self.START - 0.1, self.END]), self.END)
            self.assertTrue(g.after("x", self.START, self.END))
        with tempfile.TemporaryDirectory() as tmp:  # only before the end: missing
            g = self.gate(tmp, self.beats(cm.sample_line, [self.START - 0.1, self.END - 1e-6]), self.END - 1e-6)
            self.assertFalse(g.after("x", self.START, self.END))
        with tempfile.TemporaryDirectory() as tmp:  # after the end: covered
            g = self.gate(tmp, self.beats(cm.sample_line, [self.START - 0.1, self.END + 1e-6]), self.END + 1e-6)
            self.assertTrue(g.after("x", self.START, self.END))

    def test_still_detects_missing_gaps_dead_monitor_and_partial_log(self):
        with tempfile.TemporaryDirectory() as tmp:  # gap > 1 s inside the child
            g = self.gate(tmp, self.beats(cm.sample_line, [self.START - 0.1, self.START + 1.5, self.END + 2]),
                          self.END + 2)
            self.assertFalse(g.after("x", self.START, self.END + 1.9))
        with tempfile.TemporaryDirectory() as tmp:  # monitor process gone
            g = self.gate(tmp, self.beats(cm.sample_line, [self.START - 0.1, self.END + 0.1]), self.END + 0.1,
                          pid_alive=False)
            self.assertFalse(g.after("x", self.START, self.END))
        with tempfile.TemporaryDirectory() as tmp:  # the only beat after the end is an incomplete line
            lines = self.beats(cm.sample_line, [self.START - 0.1])
            lines.append(cm.sample_line(self.END + 0.1, 9, []).rstrip("\n")[:-3])
            g = self.gate(tmp, lines, self.END + 0.1)
            self.assertFalse(g.after("x", self.START, self.END))

    def test_new_gate_coverage_uses_exact_values(self):
        self.assertEqual(ig.coverage_reasons(self.TIMES, self.START, self.END, 2.5), [])
        rounded = [round(t, 3) for t in self.TIMES]
        self.assertIn("no telemetry after the unit ended", ig.coverage_reasons(rounded, self.START, self.END, 2.5))


# -- 2. Proportional gate --------------------------------------------------------------------
def sample(t, ext=0.1, **kw):
    row = {"k": "s", "t": t, "ext_cpu": ext, "pressure": 1, "sleep_s": 0.0, "top": [["Claude Helper", 0.05]],
           "span_s": 1.0}
    row.update(kw)
    return row


class Host:
    """Simulated monitor: writes one sample per simulated second from ``profile(t)``."""

    def __init__(self, directory, profile, start=1000.0, slow=lambda t: {"ac": True, "therm": "ok"}):
        self.dir, self.profile, self.now, self.slow = Path(directory), profile, start, slow
        self.log = self.dir / "telemetry.jsonl"
        self.seq = 0
        self.silent = False
        self.next = start + 1.0
        for _ in range(40):
            self.tick(1.0)

    def tick(self, seconds):
        end = self.now + seconds
        while self.next <= end + 1e-9:
            t = self.next
            self.next += 1.0
            if self.silent:
                continue
            row = sample(t, **self.profile(t))
            if self.seq % 5 == 0:
                row.update(self.slow(t))
            self.seq += 1
            with open(self.log, "a") as h:
                h.write(json.dumps(row) + "\n")
            (self.dir / "monitor-status.json").write_text(json.dumps({"pid": 1, "t": t, "seq": self.seq}))
        self.now = end

    def gate(self, **rules):
        return ig.Gate(self.dir, clock=lambda: self.now, sleep=self.tick, rules={**ig.RULES, **rules},
                       alive=lambda pid: True)


class ProportionalGate(unittest.TestCase):
    def test_rules_match_matrix(self):
        frozen = MATRIX["conformance"]["qualification_3"]["revision_3"]
        self.assertEqual(frozen["rules"], ig.RULES)

    def test_idle_apps_and_user_input_do_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {"ext": 0.15, "hid_idle": t % 7})  # input every few seconds
            g = host.gate()
            self.assertEqual(g.ready("u"), 0.0)
            result = g.run_unit("pair", lambda: [g.child("A:x", lambda: host.tick(5)), g.child("A:y", lambda: host.tick(5))])
            self.assertEqual(len(result), 2)
            rows = [json.loads(l) for l in (Path(tmp) / "units.jsonl").read_text().splitlines()]
            self.assertTrue(rows[-1]["valid"])

    def test_sustained_load_waits_then_resumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            busy_until = 1100.0
            host = Host(tmp, lambda t: {"ext": 3.0 if t <= busy_until else 0.1})
            g = host.gate()
            waited = g.ready("u")
            self.assertGreater(host.now, busy_until + ig.RULES["ready_window_s"] * 0.6)
            self.assertGreater(waited, 50)
            wait = [json.loads(l) for l in (Path(tmp) / "units.jsonl").read_text().splitlines()][-1]
            self.assertEqual(wait["kind"], "wait")
            self.assertIn("external CPU", wait["reasons"][0])

    def test_short_spike_below_window_threshold_is_tolerated(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {"ext": 4.0 if 1045 <= t < 1047 else 0.1})
            g = host.gate()
            g.run_unit("u", lambda: g.child("BC:x", lambda: host.tick(10)))
            self.assertTrue(json.loads((Path(tmp) / "units.jsonl").read_text().splitlines()[-1])["valid"])

    def test_load_during_unit_repeats_the_whole_pair(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {"ext": 2.5 if 1046 <= t < 1060 else 0.1})
            g = host.gate()
            ran, preserved = [], []

            def pair():
                for arm in ("ref", "cand"):
                    g.child(f"r:cell-00-{arm}", lambda: host.tick(5))
                    ran.append(arm)

            g.run_unit("r:cell-00", pair, lambda attempt, reasons: preserved.append((attempt, reasons)))
            self.assertEqual(ran, ["ref", "cand", "ref", "cand"])  # both arms again, never one alone
            self.assertEqual(len(preserved), 1)
            self.assertIn("external CPU", preserved[0][1][0])
            units = [json.loads(l) for l in (Path(tmp) / "units.jsonl").read_text().splitlines() if '"unit"' in l]
            self.assertEqual([u["valid"] for u in units if u["kind"] == "unit"], [False, True])

    def test_memory_power_thermal_sleep_invalidate(self):
        for profile, slow, word in (
                (lambda t: {"pressure": 2 if t > 1042 else 1}, None, "memory"),
                (lambda t: {"sleep_s": 30.0 if 1043 <= t < 1044 else 0.0}, None, "sleep"),
                (lambda t: {}, lambda t: {"ac": t < 1042, "therm": "ok"}, "AC"),
                (lambda t: {}, lambda t: {"ac": True, "therm": "ok" if t < 1042 else "CPU_Speed_Limit = 80"}, "thermal")):
            with tempfile.TemporaryDirectory() as tmp:
                host = Host(tmp, profile, slow=slow or (lambda t: {"ac": True, "therm": "ok"}))
                g = host.gate(retries=0, wait_limit_s=5)
                with self.assertRaises((ig.RecoveryExhausted, ig.Blocked), msg=word):
                    g.run_unit("u", lambda: g.child("BC:x", lambda: host.tick(8)))
                text = (Path(tmp) / "units.jsonl").read_text()
                self.assertIn(word, text)

    def test_monitor_missing_silent_or_with_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:  # never started
            now = [5000.0]
            g = ig.Gate(Path(tmp), clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s),
                        alive=lambda pid: True)
            with self.assertRaises(ig.MonitorLost):
                g.ready("u")
        with tempfile.TemporaryDirectory() as tmp:  # stops sampling
            host = Host(tmp, lambda t: {})
            host.silent = True
            host.tick(10)
            with self.assertRaises(ig.MonitorLost):
                host.gate().ready("u")
        with tempfile.TemporaryDirectory() as tmp:  # monitor process gone
            host = Host(tmp, lambda t: {})
            g = ig.Gate(Path(tmp), clock=lambda: host.now, sleep=host.tick, alive=lambda pid: False)
            with self.assertRaises(ig.MonitorLost):
                g.ready("u")
        samples = [sample(t) for t in (1.0, 2.0, 6.0, 7.0)]  # a 4 s gap inside the unit
        self.assertTrue(any("gap" in r for r in ig.judge(samples, 1.5, 6.5)))

    def test_budget_and_wait_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {"ext": 3.0})
            with self.assertRaises(ig.Blocked) as caught:
                host.gate(wait_limit_s=60).ready("u")
            self.assertIn("blocked by sustained host load", caught.exception.reason)
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {})
            (Path(tmp) / "limits.json").write_text(json.dumps({"deadline": host.now - 1}))
            with self.assertRaises(ig.BudgetExhausted):
                host.gate().ready("u")
        with tempfile.TemporaryDirectory() as tmp:  # retries exhausted
            busy = [False]
            host = Host(tmp, lambda t: {"ext": 2.0 if busy[0] else 0.1})
            g = host.gate(retries=1)
            calls = []

            def loaded():
                busy[0] = True
                host.tick(20)
                busy[0] = False

            def unit():
                calls.append(1)
                g.child("T5:x", loaded)
            with self.assertRaises(ig.RecoveryExhausted):
                g.run_unit("T5:x", unit)
            self.assertEqual(len(calls), 2)

    def test_block_child_raises_block_invalid(self):
        with tempfile.TemporaryDirectory() as tmp:
            host = Host(tmp, lambda t: {"ext": 2.5 if t > 1043 else 0.1})
            with self.assertRaises(ig.BlockInvalid):
                host.gate().block_child("A:x", lambda: host.tick(10))

    def test_valid_children_counts_final_block_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = [{"kind": "unit", "block": "A-main#0", "valid": True, "children": ["A:1", "A:2"]},
                    {"kind": "unit", "block": "A-main#0", "valid": False, "children": ["A:3"]},
                    {"kind": "unit", "block": "A-main#1", "valid": True, "children": ["A:1"]},
                    {"kind": "unit", "block": "BC#0", "valid": False, "children": ["BC:c"]},
                    {"kind": "unit", "block": "BC#0", "valid": True, "children": ["BC:c"]},
                    {"kind": "wait", "block": "BC#0", "seconds": 3}]
            (Path(tmp) / "units.jsonl").write_text("\n".join(json.dumps(r) for r in rows))
            self.assertEqual(ig.valid_children(Path(tmp)), {"A": 1, "BC": 1})


# -- 3. Collector adapters -------------------------------------------------------------------
class FakeGate:
    """Scripted gate: the attempts listed in ``invalid`` (unit, attempt) are invalid."""

    def __init__(self, invalid=()):
        self.invalid, self.units, self._in = set(invalid), [], False

    @property
    def in_unit(self):
        return self._in

    def child(self, label, run):
        return run()

    def run_unit(self, unit, run, preserve=lambda a, r: None):
        for attempt in range(3):
            self._in = True
            try:
                result = run()
            finally:
                self._in = False
            bad = (unit, attempt) in self.invalid
            self.units.append((unit, attempt, not bad))
            if not bad:
                return result
            preserve(attempt, ["external CPU 2.0 cores"])
        raise ig.RecoveryExhausted(unit)


class Adapters(unittest.TestCase):
    def setUp(self):
        self.saved = ig._GATE

    def tearDown(self):
        ig._GATE = self.saved

    def test_paired_order_identical_to_frozen(self):
        import run_v060_qualification as frozen
        import interference_collect as ic
        cells = [{"id": f"c{i}"} for i in range(4)]
        expected = []
        frozen.paired_experiment(None, cells, {}, 2, 12, 7, lambda c, a, l: expected.append(l))
        got = []
        ig._GATE = FakeGate()
        saved = (frozen.Recorder.run, frozen.paired_experiment, frozen.cmd_rmem, frozen.main)
        try:
            frozen.main = lambda: 0
            ic._recorder("r", [])
            rec = types.SimpleNamespace(log={"children": []})
            frozen.paired_experiment(rec, cells, {}, 2, 12, 7, lambda c, a, l: got.append(l))
        finally:
            frozen.Recorder.run, frozen.paired_experiment, frozen.cmd_rmem, frozen.main = saved
        self.assertEqual(got, expected)

    def test_recorder_invalid_pair_moves_both_children(self):
        import run_v060_qualification as frozen
        import interference_collect as ic
        with tempfile.TemporaryDirectory() as tmp:
            rec = frozen.Recorder(Path(tmp) / "R", {"experiment": "r"}, enforce_host=False)
            ig._GATE = FakeGate(invalid={("r:c0-analyzed-00", 0)})
            saved = (frozen.Recorder.run, frozen.paired_experiment, frozen.cmd_rmem, frozen.main)
            try:
                frozen.main = lambda: 0
                ic._recorder("r", [])
                frozen.paired_experiment(rec, [{"id": "c0"}], {}, 0, 2, 3,
                                         lambda c, arm, label: rec.run(label, ["/bin/echo", arm]))
            finally:
                frozen.Recorder.run, frozen.paired_experiment, frozen.cmd_rmem, frozen.main = saved
            names = [c["name"] for c in rec.log["children"]]
            self.assertEqual(len(names), 4)  # two valid pairs
            moved = [c["name"] for c in rec.log["invalidated"][0]["children"]]
            self.assertEqual(len(moved), 2)  # the whole invalid pair, both arms
            self.assertTrue(all((Path(tmp) / "R/raw/invalidated" / f"{n}.stdout").exists() for n in moved))
            self.assertFalse(set(moved) & set(names))

    def test_bc_cell_repeated_and_preserved(self):
        import interference_collect as ic
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe"
            probe.write_text("#!/bin/sh\necho run $$\n")
            probe.chmod(0o755)
            ic._BC_IDS[("--x", "1")] = "B1-cell"
            ig._GATE = FakeGate(invalid={("BC:B1-cell", 0)})
            sub = ic._UnitSubprocess([str(probe)], Path(tmp) / "BC")
            result = sub.run([str(probe), "--x", "1"], capture_output=True, text=True)
            self.assertTrue(result.stdout.startswith("run "))
            kept = Path(tmp) / "BC/invalidated/B1-cell.attempt0.stdout"
            self.assertTrue(kept.exists() and kept.read_text() != result.stdout)
            with self.assertRaises(SystemExit):
                sub.run(["/bin/sh", "-c", "true"])  # undeclared absolute program

    def test_t5_pair_repeated_whole(self):
        import run_v070q3_t5 as t5
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / "probe"
            binary.write_text("#!/bin/sh\necho '{\"kind\":\"build\"}'; echo $$\n")
            binary.chmod(0o755)
            runs = t5.plan(50730)[:4]
            ig._GATE = FakeGate(invalid={(f"T5:{runs[0]['topology']}-{runs[0]['pair']}", 0)})
            out = Path(tmp) / "T5"
            self.assertEqual(t5.collect_units(out, {"B": binary, "C": binary}, runs, {"x": 1}), 0)
            log = [json.loads(l) for l in (out / "run-log.jsonl").read_text().splitlines()]
            self.assertEqual([r["id"] for r in log], [r["id"] for r in runs])
            kept = sorted(p.name for p in (out / "raw/invalidated").iterdir())
            self.assertEqual(kept, sorted(f"{r['id']}.attempt0.{s}" for r in runs[:2] for s in ("jsonl", "stderr")))
            self.assertEqual(len((out / "invalidated.jsonl").read_text().splitlines()), 1)


# -- 4. Runner -------------------------------------------------------------------------------
class RunnerEndPath(unittest.TestCase):
    def make(self, tmp):
        import run_v070q3_autonomous as ra
        camp = Path(tmp) / "v0.7.0-qualification-3-fa5f3a9-q3-attempt9"
        (camp / "src/cand/knotrel-benchmarks/results/v0.7.0-qualification-3").mkdir(parents=True)
        (camp / "src/cand/knotrel-benchmarks/results/v0.7.0-qualification-3/check_restored.sh").write_text("exit 0\n")
        runner = ra.Runner(camp, "fa5f3a9" + "0" * 33)
        return ra, camp, runner

    def test_failure_mid_sequence_cleans_up_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            ra, camp, runner = self.make(tmp)
            runner.preflight = lambda: None

            def start_monitor():
                runner.gate_dir.mkdir()
                runner.monitor = subprocess.Popen(["/bin/sleep", "60"])
                runner.caffeinate = subprocess.Popen(["/bin/sleep", "60"])

            def sequence():
                runner.child = subprocess.Popen(["/bin/sleep", "60"])
                raise ra.Stop("BLOCKED", "blocked by sustained host load before BC:x")

            runner.start_monitor, runner.sequence = start_monitor, sequence
            self.assertEqual(runner.run(), 1)
            for proc in (runner.monitor, runner.caffeinate):
                self.assertIsNotNone(proc.poll())
            self.assertIn("BLOCKED: blocked by sustained host load", (camp / "logs/CONFORMANCE.txt").read_text())
            summary = json.loads((camp / "SUMMARY.json").read_text())
            self.assertEqual(summary["status"], "BLOCKED")
            self.assertTrue((camp / "SUMMARY.txt").exists())
            self.assertIn("RESTORE", (camp / "logs/chain-steps.txt").read_text())

    def test_signal_interrupts_and_cleans_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            ra, camp, runner = self.make(tmp)
            runner.preflight = lambda: None

            def start_monitor():
                runner.gate_dir.mkdir()
                runner.monitor = subprocess.Popen(["/bin/sleep", "60"])

            def sequence():
                runner.child = subprocess.Popen(["/bin/sleep", "60"])
                os.kill(os.getpid(), signal.SIGTERM)
                runner.child.wait()

            runner.start_monitor, runner.sequence = start_monitor, sequence
            previous = signal.getsignal(signal.SIGTERM)
            try:
                self.assertEqual(runner.run(), 1)
            finally:
                signal.signal(signal.SIGTERM, previous)
            self.assertIsNotNone(runner.monitor.poll())
            self.assertTrue((camp / "logs/CONFORMANCE.txt").read_text().startswith("INTERRUPTED"))

    def test_preflight_refusal_writes_no_conformance(self):
        with tempfile.TemporaryDirectory() as tmp:
            ra, camp, runner = self.make(tmp)
            (camp / "BC").mkdir()
            self.assertEqual(runner.run(), 1)
            self.assertFalse((camp / "logs/CONFORMANCE.txt").exists())  # no attempt used
            self.assertIn("NOT STARTED", (camp / "logs/PREFLIGHT-REFUSED.txt").read_text())

    def test_block_restart_then_exhausted(self):
        with tempfile.TemporaryDirectory() as tmp:
            ra, camp, runner = self.make(tmp)
            runner.logs.mkdir()
            runner.gate_dir.mkdir()
            out = camp / "A" / "raw-main"
            script = f"import os,sys; os.makedirs({str(out)!r}, exist_ok=True); sys.exit(75)"
            with self.assertRaises(ra.Stop) as caught:
                runner.run_step("A-main", [sys.executable, "-c", script], "A-main", [out])
            self.assertEqual(caught.exception.status, "RECOVERY EXHAUSTED")
            self.assertTrue((camp / "invalidated" / "raw-main.1").exists())
            self.assertEqual([s["block"] for s in runner.steps], ["A-main#0", "A-main#1"])

    def test_gate_exit_codes_map_to_statuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            ra, camp, runner = self.make(tmp)
            runner.logs.mkdir()
            runner.gate_dir.mkdir()
            for code, status in ra.EXIT_STATUS.items():
                with self.assertRaises(ra.Stop) as caught:
                    runner.run_step("BC", [sys.executable, "-c", f"raise SystemExit({code})"], "BC")
                self.assertEqual(caught.exception.status, status)


if __name__ == "__main__":
    unittest.main()


class RunnerArguments(unittest.TestCase):
    """The runner runs each collector with the arguments of the frozen chain (and of the
    launch-environment dry runs), in the frozen order."""

    def test_same_collector_arguments_and_order_as_the_chain(self):
        import shlex
        import run_v070q3_autonomous as ra
        q3 = ROOT / "results" / "v0.7.0-qualification-3"
        chain = (q3 / "run_final_chain.sh").read_text()
        with tempfile.TemporaryDirectory() as tmp:
            camp = Path(tmp) / "c"
            (camp / "A").mkdir(parents=True)
            (camp / "A/decision-analysis-main.json").write_text(json.dumps({"extension_cells_required": []}))
            runner = ra.Runner(camp, "f" * 40)
            calls = []
            runner.run_step = lambda name, argv, block, dirs=(): calls.append((name, argv))
            runner.analysis = lambda name, argv: calls.append((name, argv))
            runner.logs = camp
            runner.sequence()
        names = [c[0] for c in calls]
        self.assertEqual(names, ["A-main", "A-analysis", "BC", "T5", "R", "Rmem", "Mdesc", "Mreg"])

        def norm(words):
            out = []
            for w in words:
                w = w.replace(str(camp / "targets"), "$T").replace(str(camp / "A"), "$A").replace(str(camp), "$CAMP")
                out.append(w)
            return out

        for name, experiment in (("BC", "bc"), ("R", "r"), ("Rmem", "rmem"), ("Mdesc", "mdesc"), ("Mreg", "mreg")):
            argv = norm(dict(calls)[name])
            got = argv[argv.index(experiment) + 1:]
            line = next(l for l in chain.splitlines()
                        if f"run_v070q3_collect.py {experiment} " in l or (l.startswith("step ") and f" {experiment} " in l))
            words = shlex.split(line.split(">")[0])
            want = words[words.index(experiment) + 1:] if "run_v070q3_collect.py" in line else words[4:]
            self.assertEqual(got, [w.replace('"', "") for w in want], name)
        t5 = norm(dict(calls)["T5"])
        line = next(l for l in chain.splitlines() if "run_v070q3_t5.py" in l)
        want = shlex.split(line.split(">")[0])
        self.assertEqual(t5[t5.index("--out"):], want[want.index("--out"):])
        a = norm(dict(calls)["A-main"])
        self.assertEqual(a[a.index("a") + 1:], ["--manifest", "$A/plan/manifest.json", "--schedule",
                                               "$A/plan/schedule.json", "--execute", "$A/raw-main"])

    def test_launch_command_runs_the_runner(self):
        out = subprocess.run(["sh", str(ROOT / "results/v0.7.0-qualification-3/launch_command.sh"),
                              "/x/evidence/v0.7.0-qualification-3-fa5f3a9-q3-attempt3", "f" * 40],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn("scripts/run_v070q3_autonomous.py /x/evidence/v0.7.0-qualification-3-fa5f3a9-q3-attempt3 " + "f" * 40, out)
        self.assertNotIn("run_final_chain.sh", out)
        self.assertNotIn("precheck_terminal.sh", out)
