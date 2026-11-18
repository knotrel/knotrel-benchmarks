"""Tests for amendment 1 of the v0.7.0 re-qualification (scripts/launcher_audit.py, chain).

launchd, pluginkit and crontab are injected through a fake runner; app bundles are temporary
directories. No test touches the real launchd state or /Applications.
"""

import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))

import launcher_audit as la  # noqa: E402

REPO = SCRIPTS.parent
RQ = REPO / "results/v0.7.0-requalification"
FROZEN = "cda112c0b5c994a540c2293fe11f5d6aa4cfbc0e"


# Real-format samples (macOS 26, 2026-11-18), trimmed.
LAUNCHCTL_JOB_REAL = """gui/501/com.google.GoogleUpdater.wake = {
\tactive count = 0
\tpath = /Users/rt/Library/LaunchAgents/com.google.GoogleUpdater.wake.plist
\ttype = LaunchAgent
\tstate = not running

\tprogram = /Users/rt/Library/Application Support/Google/GoogleUpdater/Current/GoogleUpdater.app/Contents/MacOS/GoogleUpdater
\targuments = {
\t\t/Users/rt/Library/Application Support/Google/GoogleUpdater/Current/GoogleUpdater.app/Contents/MacOS/GoogleUpdater
\t\t--wake-all
\t}

\tdomain = gui/501 [100024]
\trun interval = 3600 seconds
}
"""
LAUNCHCTL_SUBMITTED_REAL = """gui/501/com.docker.helper = {
\tactive count = 0
\tpath = (submitted by smd.412)
\ttype = Submitted
\tstate = not running

\tprogram identifier = com.docker.helper (mode: 1)
\tproperties = supports transactions | resolve program | has LWCR
}
"""
LAUNCHCTL_DOMAIN_REAL = """gui/501 = {
\ttype = gui
\thandle = 501
\tservices = {
\t\t   16433   (pe) \tcom.apple.syncdefaultsd
\t\t       0      0 \tcom.google.GoogleUpdater.wake
\t\t       0     78 \tcom.microsoft.EdgeUpdater.wake
\t}

\tunmanaged processes = {
\t\tx
\t}
}
"""
PLUGINKIT_REAL = ("     com.apple.StoreKit.SKAskPermissionExtension(1.0)\t3F077662-0DB4-54A0-A191-C5961C055B3D\t2026-07-21 00:10:58 +0000\t"
                  "/System/Library/Frameworks/StoreKit.framework/Versions/A/PlugIns/SKAskPermissionExtension.appex\n"
                  " (1 plug-ins)\n")


def service_text(path, program):
    return f"x = {{\n\tpath = {path}\n\ttype = LaunchAgent\n\n\tprogram = {program}\n}}\n"


class FakeLaunchd:
    """gui/<uid> state: label -> (plist, program). Records every command."""

    def __init__(self, jobs, fail_bootout=(), fail_bootstrap=()):
        self.jobs = dict(jobs)
        self.plists = {plist: (label, prog) for label, (plist, prog) in jobs.items()}
        self.fail_bootout, self.fail_bootstrap = set(fail_bootout), set(fail_bootstrap)
        self.calls = []

    def __call__(self, cmd):
        self.calls.append(list(cmd))
        if cmd[:2] == ["launchctl", "print"]:
            target = cmd[2]
            if "/" in target and target.count("/") >= 2:
                label = target.split("/", 2)[2]
                if label in self.jobs:
                    return 0, service_text(*self.jobs[label])
                return 113, ""
            body = "".join(f"\t\t0\t0\t{label}\n" for label in self.jobs)
            return 0, f"{target} = {{\n\tservices = {{\n{body}\t}}\n}}\n"
        if cmd[:2] == ["launchctl", "bootout"]:
            label = cmd[2].split("/", 2)[2]
            if label not in self.fail_bootout:
                self.jobs.pop(label, None)
            return 0, ""
        if cmd[:2] == ["launchctl", "bootstrap"]:
            plist = cmd[3]
            if plist in self.plists and self.plists[plist][0] not in self.fail_bootstrap:
                label, prog = self.plists[plist]
                self.jobs[label] = (plist, prog)
                return 0, ""
            return 5, ""
        if cmd[0] == "pluginkit":
            return 0, PLUGINKIT_REAL
        if cmd[0] == "crontab":
            return 1, "crontab: no crontab for u\n"
        raise AssertionError(cmd)


def write_plist(directory, name, data):
    path = Path(directory) / name
    with open(path, "wb") as fh:
        plistlib.dump(data, fh)
    return str(path)


class Criterion(unittest.TestCase):
    def job(self, path, program, triggers=None):
        runner = lambda cmd: (0, service_text(path, program))
        return la.describe_job("gui/501", "x", runner, lambda p: triggers)

    def test_apple_needs_plist_and_program_in_apple_locations(self):
        self.assertTrue(self.job("/System/Library/LaunchAgents/a.plist", "/usr/libexec/a")["apple"])
        self.assertTrue(self.job("/System/Library/LaunchAgents/a.plist", "/System/Applications/X.app/Contents/MacOS/x")["apple"])

    def test_label_spoofing_is_third_party(self):
        runner = lambda cmd: (0, service_text("/Users/u/Library/LaunchAgents/com.apple.evil.plist", "/bin/sh"))
        job = la.describe_job("gui/501", "com.apple.evil", runner, lambda p: ["StartInterval"])
        self.assertFalse(job["apple"])
        self.assertEqual(len(la.audit_jobs([job], {}, {})), 1)

    def test_apple_program_with_third_party_plist(self):
        self.assertFalse(self.job("/Library/LaunchAgents/x.plist", "/usr/bin/python3")["apple"])

    def test_submitted_job_is_third_party_and_unknown(self):
        job = self.job("(submitted by smd.412)", "/Applications/D.app/x")
        self.assertFalse(job["apple"])
        self.assertIsNone(job["plist"])
        self.assertIsNone(job["triggers"])

    def test_unreadable_print_is_third_party(self):
        job = la.describe_job("gui/501", "x", lambda cmd: (113, ""), lambda p: [])
        self.assertFalse(job["apple"])


class Triggers(unittest.TestCase):
    def test_plist_triggers(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(la.plist_triggers(write_plist(d, "a", {"StartInterval": 3600})), ["StartInterval"])
            self.assertEqual(la.plist_triggers(write_plist(d, "b", {"RunAtLoad": False, "KeepAlive": False})), [])
            self.assertEqual(la.plist_triggers(write_plist(d, "c", {"MachServices": {"x": True}})), [])
            self.assertEqual(sorted(la.plist_triggers(write_plist(d, "d", {"RunAtLoad": True, "KeepAlive": {"SuccessfulExit": False}}))),
                             ["KeepAlive", "RunAtLoad"])
            self.assertEqual(la.plist_triggers(write_plist(d, "e", {"LaunchEvents": {}, "WatchPaths": ["/x"]})),
                             ["WatchPaths", "LaunchEvents"])
            empty = Path(d) / "empty"
            empty.write_bytes(b"")
            self.assertIsNone(la.plist_triggers(str(empty)))
            self.assertIsNone(la.plist_triggers(str(Path(d) / "missing")))


class Audit(unittest.TestCase):
    def jobs(self):
        third = {"apple": False, "domain": "gui/501", "path": "/Users/u/Library/LaunchAgents/x.plist"}
        return [
            {**third, "label": "timer", "triggers": ["StartInterval"]},
            {**third, "label": "ondemand", "triggers": []},
            {**third, "label": "unknown", "triggers": None, "path": "(submitted by smd)"},
            {**third, "label": "application.com.anthropic.claudefordesktop.1.2", "triggers": None},
            {"apple": True, "domain": "gui/501", "label": "com.apple.a", "path": "/System/Library/x", "triggers": ["RunAtLoad"]},
        ]

    CLAUDE = {"application.com.anthropic.claudefordesktop.": {"program_prefix": "/Applications/Claude.app/", "unreadable_ok": True}}

    def jobs_with_programs(self):
        jobs = self.jobs()
        for j in jobs:
            j.setdefault("program", "/Applications/Claude.app/Contents/MacOS/Claude" if j["label"].startswith("application.") else "/x/" + j["label"])
        return jobs

    def test_fail_closed_and_allow_lists(self):
        reasons = la.audit_jobs(self.jobs_with_programs(), {}, self.CLAUDE)
        self.assertEqual(len(reasons), 2)
        self.assertTrue(any("timer" in r for r in reasons) and any("unknown" in r and "undeterminable" in r for r in reasons))
        allow = {"timer": {"program_prefix": "/x/", "triggers": ["StartInterval"]},
                 "unknown": {"program_prefix": "/x/", "unreadable_ok": True}}
        self.assertEqual(la.audit_jobs(self.jobs_with_programs(), allow, self.CLAUDE), [])

    def test_allow_entries_are_verified_not_trusted(self):
        jobs = self.jobs_with_programs()
        # a timer the entry does not permit
        r = la.audit_jobs(jobs, {"timer": {"program_prefix": "/x/", "triggers": ["RunAtLoad"]}}, self.CLAUDE)
        self.assertTrue(any("timer" in x and "not permitted" in x for x in r))
        # wrong program for an allow-listed label (spoofed label)
        r = la.audit_jobs(jobs, {"timer": {"program_prefix": "/Applications/Good.app/", "triggers": ["StartInterval"]}}, self.CLAUDE)
        self.assertTrue(any("timer" in x and "outside" in x for x in r))
        # unreadable triggers without unreadable_ok
        r = la.audit_jobs(jobs, {"unknown": {"program_prefix": "/x/"}}, self.CLAUDE)
        self.assertTrue(any("unknown" in x and "undeterminable" in x for x in r))
        # prefix rule checks the program too
        spoof = [{"apple": False, "domain": "gui/501", "label": "application.com.anthropic.claudefordesktop.9",
                  "path": "(submitted by x)", "program": "/tmp/evil", "triggers": None}]
        self.assertEqual(len(la.audit_jobs(spoof, {}, self.CLAUDE)), 1)
        # entry expecting no program line
        nop = [{"apple": False, "domain": "gui/501", "label": "d", "path": "(submitted by smd)", "program": "/x/d", "triggers": None}]
        self.assertEqual(len(la.audit_jobs(nop, {"d": {"program_prefix": None, "unreadable_ok": True}}, {})), 1)

    def test_real_launchctl_formats(self):
        self.assertEqual(la.parse_service(LAUNCHCTL_JOB_REAL)["path"], "/Users/rt/Library/LaunchAgents/com.google.GoogleUpdater.wake.plist")
        self.assertTrue(la.parse_service(LAUNCHCTL_JOB_REAL)["program"].endswith("/MacOS/GoogleUpdater"))
        sub = la.parse_service(LAUNCHCTL_SUBMITTED_REAL)
        self.assertEqual(sub, {"path": "(submitted by smd.412)", "program": None})
        labels = la.domain_labels("gui/501", lambda cmd: (0, LAUNCHCTL_DOMAIN_REAL))
        self.assertEqual(labels, ["com.apple.syncdefaultsd", "com.google.GoogleUpdater.wake", "com.microsoft.EdgeUpdater.wake"])

    def test_extensions_fail_closed(self):
        self.assertEqual(len(la.extensions(lambda cmd: (0, PLUGINKIT_REAL))), 1)
        for bad in ("", " (0 plug-ins)\n", PLUGINKIT_REAL.replace("(1 plug-ins)", "(2 plug-ins)"),
                    "garbage line\n (1 plug-ins)\n"):
            with self.assertRaises(RuntimeError):
                la.extensions(lambda cmd: (0, bad))

    def test_crontab_fail_closed(self):
        self.assertEqual(la.user_crontab(lambda cmd: (1, "crontab: no crontab for rt\n")), "")
        with self.assertRaises(RuntimeError):
            la.user_crontab(lambda cmd: (1, "crontab: permission denied\n"))

    def test_extensions(self):
        out = ("     com.apple.x(1.0)\tA\t2026\t/System/Library/X.appex\n"
               "+    net.whatsapp.WhatsApp.ServiceExtension(26)\tB\t2026\t/Applications/WhatsApp.app/Contents/PlugIns/S.appex\n"
               " (2 plug-ins)\n")
        rows = la.extensions(lambda cmd: (0, out))
        self.assertEqual([r["id"] for r in rows], ["com.apple.x", "net.whatsapp.WhatsApp.ServiceExtension"])
        self.assertEqual(len(la.audit_extensions(rows, [], lambda p: True)), 1)
        self.assertEqual(la.audit_extensions(rows, [], lambda p: False), [], "a parked bundle no longer resolves")
        self.assertEqual(la.audit_extensions(rows, ["net.whatsapp.WhatsApp.ServiceExtension"], lambda p: True), [])

    def test_crontab(self):
        base = {"jobs": [], "extensions": []}
        self.assertEqual(la.audit({**base, "user_crontab": "# only a comment\n\n"}, {}), [])
        self.assertEqual(la.audit({**base, "user_crontab": "*/5 * * * * /bin/x\n"}, {}), ["user crontab is not empty"])

    def test_inventory_with_fake_runner(self):
        fake = FakeLaunchd({"com.g.wake": ("/Users/u/Library/LaunchAgents/g.plist", "/Users/u/G.app/g")})
        inv = la.inventory(fake, uid=501)
        self.assertEqual({j["label"] for j in inv["jobs"]}, {"com.g.wake"})
        self.assertEqual(inv["user_crontab"], "")


class QuiesceRestore(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.root = base / "evidence"
        self.camp = self.root / "camp"
        (self.camp / "logs").mkdir(parents=True)
        self.app = base / "Applications" / "W.app"
        (self.app / "Contents").mkdir(parents=True)
        self.conf = {"launchd": ["g.wake", "e.wake", "absent"], "park_apps": [str(self.app), str(base / "Applications/None.app")]}
        self.fake = FakeLaunchd({"g.wake": ("/p/g.plist", "/x/g"), "e.wake": ("/p/e.plist", "/x/e"), "keep": ("/p/k.plist", "/x/k")})

    def tearDown(self):
        self.tmp.cleanup()

    def quiesce(self, fake=None):
        return la.quiesce(self.camp, self.conf, fake or self.fake, uid=501, root=self.root)

    def test_round_trip(self):
        ok, manifest = self.quiesce()
        self.assertTrue(ok, manifest)
        self.assertEqual(set(self.fake.jobs), {"keep"})
        self.assertFalse(self.app.exists())
        self.assertTrue(Path(str(self.app) + la.PARK_SUFFIX).exists())
        self.assertEqual(la.pending(self.root), [str(self.camp / "logs" / la.MANIFEST)])
        self.assertEqual(len(manifest["manual_restore"]), 4)  # 2 bootstraps, 1 mv, the restore command
        self.assertTrue((self.camp / "logs" / "quiesce-inventory.json").exists())
        ok, result = la.restore(self.camp, self.fake)
        self.assertTrue(ok, result)
        self.assertEqual(set(self.fake.jobs), {"keep", "g.wake", "e.wake"})
        self.assertTrue(self.app.exists())
        self.assertEqual(la.pending(self.root), [])
        ok, again = la.restore(self.camp, self.fake)  # idempotent
        self.assertTrue(ok)
        self.assertEqual({a["result"] for a in again["actions"]}, {"already loaded", "already in place"})

    def test_refuses_while_unrestored(self):
        self.quiesce()
        other = self.root / "camp2"
        (other / "logs").mkdir(parents=True)
        ok, info = la.quiesce(other, self.conf, self.fake, uid=501, root=self.root)
        self.assertFalse(ok)
        self.assertIn("refused", info)
        self.assertFalse((other / "logs" / la.MANIFEST).exists())

    def test_bootout_failure_is_reported(self):
        fake = FakeLaunchd({"g.wake": ("/p/g.plist", "/x/g")}, fail_bootout={"g.wake"})
        ok, manifest = self.quiesce(fake)
        self.assertFalse(ok)
        self.assertIn("g.wake: still loaded after bootout", manifest["errors"])

    def test_submitted_job_not_booted_out(self):
        fake = FakeLaunchd({"g.wake": ("(submitted by smd)", "/x/g")})
        ok, manifest = self.quiesce(fake)
        self.assertFalse(ok)
        self.assertIn("g.wake", fake.jobs)
        self.assertFalse(any(c[:2] == ["launchctl", "bootout"] for c in fake.calls))

    def test_bootstrap_failure(self):
        self.quiesce()
        self.fake.fail_bootstrap = {"g.wake"}
        ok, result = la.restore(self.camp, self.fake)
        self.assertFalse(ok)
        self.assertIn("FAILED", {a["result"] for a in result["actions"]})
        self.assertEqual(len(la.pending(self.root)), 1)

    def test_occupied_path_is_not_overwritten(self):
        self.quiesce()
        (self.app / "Contents").mkdir(parents=True)  # e.g. reinstalled
        ok, result = la.restore(self.camp, self.fake)
        self.assertFalse(ok)
        self.assertTrue(Path(str(self.app) + la.PARK_SUFFIX).exists())
        self.assertTrue(any("occupied" in str(a["result"]) for a in result["actions"]))

    def test_manifest_written_before_action(self):
        seen = {}

        def crashing(cmd):
            if cmd[:2] == ["launchctl", "bootout"]:
                seen["manifest"] = json.loads((self.camp / "logs" / la.MANIFEST).read_text())
                raise KeyboardInterrupt  # as if killed mid-way
            return self.fake(cmd)

        with self.assertRaises(KeyboardInterrupt):
            self.quiesce(crashing)
        self.assertEqual(seen["manifest"]["jobs"][0]["intent"], "bootout")
        self.assertEqual(la.pending(self.root), [str(self.camp / "logs" / la.MANIFEST)])

    def test_parked_path_preexisting_is_left_alone(self):
        Path(str(self.app) + la.PARK_SUFFIX).mkdir()
        ok, manifest = self.quiesce()
        self.assertFalse(ok)
        self.assertTrue(self.app.exists())
        ok, result = la.restore(self.camp, self.fake)  # nothing was renamed: nothing to undo
        self.assertTrue(ok, result)
        self.assertTrue(self.app.exists() and Path(str(self.app) + la.PARK_SUFFIX).exists())
        self.assertEqual(la.pending(self.root), [])

    def test_corrupt_result_or_manifest_keeps_pending(self):
        self.quiesce()
        (self.camp / "logs" / la.RESULT).write_text("{not json")
        self.assertEqual(len(la.pending(self.root)), 1)
        (self.camp / "logs" / la.MANIFEST).write_text("")
        ok, result = la.restore(self.camp, self.fake)
        self.assertFalse(ok)
        self.assertIn("manual procedure", result["error"])
        self.assertEqual(len(la.pending(self.root)), 1)

    def test_extension_still_resolving_after_park_fails(self):
        out = (f"     x.ext(1)\tA\t2026\t{self.app}/Contents/PlugIns/S.appex\n (1 plug-ins)\n")
        def runner(cmd):
            return (0, out) if cmd[0] == "pluginkit" else self.fake(cmd)
        ok, manifest = la.quiesce(self.camp, self.conf, runner, uid=501, root=self.root,
                                  take_inventory=lambda: {}, exists=lambda p: True)
        self.assertFalse(ok)
        self.assertTrue(manifest["extensions_after_park"])

    def test_manual_commands_are_quoted(self):
        m = {"jobs": [{"intent": "bootout", "domain": "gui/501", "plist": "/a b/it's.plist"}],
             "apps": [{"intent": "rename", "path": "/A/W.app", "parked_path": "/A/W.app.parked-qualification"}]}
        cmds = la.manual_commands(m)
        self.assertIn("launchctl bootstrap gui/501 '/a b/it'\"'\"'s.plist'", cmds)
        self.assertTrue(cmds[1].startswith("mv -n "))

    def test_no_manifest_restore_is_ok(self):
        empty = self.root / "empty"
        (empty / "logs").mkdir(parents=True)
        self.assertTrue(la.restore(empty, self.fake)[0])


class Chain(unittest.TestCase):
    text = (RQ / "run_final_chain.sh").read_text()

    def test_syntax(self):
        for name in ("run_final_chain.sh", "prepare_campaign.sh", "prepare_soak.sh"):
            self.assertEqual(subprocess.run(["sh", "-n", str(RQ / name)]).returncode, 0, name)

    def test_order(self):
        t = self.text
        quiesce = t.index("python3 scripts/launcher_audit.py quiesce")
        self.assertLess(quiesce, t.index('stamp GRACE'))
        self.assertLess(t.index("launcher_audit.py audit --matrix \"$MATRIX\" --out \"$L/launcher-audit.json\""),
                        t.index("conformance_monitor.py policy --chain"))
        self.assertLess(t.index("pmset -g batt | head -1"), quiesce)

    def test_restore_strictly_after_records(self):
        finish = self.text[self.text.index("finish() {"):self.text.index("trap finish EXIT")]
        restore = finish.index("launcher_audit.py restore")
        for record in ('kill "$MON"', "git-after.json", "CONFORMANCE.txt", "outputs-sha256.txt"):
            self.assertLess(finish.index(record), restore, record)

    def test_soak_branch_measures_nothing(self):
        start = self.text.index('if [ -n "$SOAK" ]; then\n  # --- Amendment 1, A3')
        end = self.text.index("exit 0\nfi", start)
        soak = self.text[start:end]
        self.assertLess(end, self.text.index("# --- A ---"))
        for forbidden in ("run_v070r_collect", "targets/", "cargo", "$T/"):
            self.assertNotIn(forbidden, soak)
        self.assertIn('cg.gated("soak:sleep"', soak)
        self.assertIn('gated != {"soak": 1}', soak)
        self.assertIn("SOAK CONFORMING", soak)

    def test_argument_validation_before_any_action(self):
        chain = str(RQ / "run_final_chain.sh")
        sha = "e" * 40
        for args in (["/e/x-soak1", sha, "1", "t"], ["/e/x-a1-attempt1", "-", "1", "t", "--soak"],
                     ["/e/x-soak1", "-", "1", "t", "--soak", "extra"], ["/e/x-a1-attempt1", sha, "1", "t", "--soakx"],
                     ["/e/x-a1-attempt1", "abc", "1", "t"], ["/e/x"],
                     ["/e/v-1111111-a1-attempt1", "2" * 40, "1", "t"]):
            proc = subprocess.run(["sh", chain] + args, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2, args)
        head = self.text[:self.text.index("B=$CAMP/src")]
        self.assertNotIn("launcher_audit", head.split("set -u", 1)[1].split("CAMP=$1")[0])

    def test_finish_ignores_second_signal_and_reports_restore(self):
        finish = self.text[self.text.index("finish() {"):self.text.index("trap finish EXIT")]
        self.assertIn("trap '' INT TERM HUP", finish)
        self.assertIn("stamp RESTORE", finish)
        self.assertIn("exit 21", finish)

    def test_relaunch_refused_after_quiesce(self):
        self.assertIn('"$L/quiesce-restore.json"; do', self.text)

    def test_prepare_series_and_soak(self):
        prep = (RQ / "prepare_campaign.sh").read_text()
        self.assertIn('CAMP=$CAMP-$SERIES-attempt$ATTEMPT', prep)
        for needle in ("FREEZE-A1.json", "attempts_cap", "SOAK CONFORMING", "check_restored.sh"):
            self.assertIn(needle, prep)
        self.assertLess(prep.index("check_restored.sh"), prep.index('mkdir -p "$CAMP/logs"'))
        soak = (RQ / "prepare_soak.sh").read_text()
        self.assertNotIn("cargo", soak)
        self.assertNotIn("rm -rf", soak)
        for needle in ("max_soaks", "FREEZE-A1.json", "check_restored.sh", "[1-9]) ;;"):
            self.assertLess(soak.index(needle), soak.index("mkdir"), needle)

    def test_prepare_soak_refuses_bad_number(self):
        for n, series in (("0", "a1"), ("1a", "a1"), ("10", "a1"), ("1", "a2")):
            proc = subprocess.run(["sh", str(RQ / "prepare_soak.sh"), "deadbeef", n, series], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 3, (n, series))


class MatrixAmendment(unittest.TestCase):
    def test_only_declared_keys_change_from_frozen(self):
        frozen = json.loads(subprocess.run(["git", "-C", str(REPO), "show", f"{FROZEN}:results/v0.7.0-requalification/MATRIX.json"],
                                           capture_output=True, text=True, check=True).stdout)
        new = json.loads((RQ / "MATRIX.json").read_text())
        self.assertEqual(set(frozen) ^ set(new), set())
        changed_top = {k for k in new if new[k] != frozen[k]}
        self.assertEqual(changed_top, {"status", "conformance"})
        fc, nc = frozen["conformance"], new["conformance"]
        changed = {k for k in set(fc) | set(nc) if fc.get(k) != nc.get(k)}
        self.assertEqual(changed, {"outcome", "amendment_1", "quiesce", "soak", "input_devices"})
        self.assertTrue(nc["outcome"].startswith(fc["outcome"]))

    def test_quiesce_lists(self):
        q = json.loads((RQ / "MATRIX.json").read_text())["conformance"]["quiesce"]
        self.assertEqual(q["launchd"], ["com.google.GoogleUpdater.wake", "com.microsoft.EdgeUpdater.wake", "com.microsoft.update.agent"])
        self.assertEqual(q["park_apps"], ["/Applications/WhatsApp.app"])
        self.assertEqual(q["allow_extensions"], [])
        self.assertFalse(set(q["launchd"]) & set(q["allow_jobs"]))
        for label, entry in list(q["allow_jobs"].items()) + list(q["allow_jobs_prefix"].items()):
            self.assertTrue(entry.get("reason"), label)
            self.assertIn("program_prefix", entry, label)
            self.assertLessEqual(set(entry.get("triggers", [])), {"RunAtLoad"}, label)
        soak = json.loads((RQ / "MATRIX.json").read_text())["conformance"]["soak"]
        self.assertEqual((soak["duration_s"], soak["max_soaks"]), (4800, 2))


STUB_AUDIT = r"""
import json, os, sys, time
order = os.environ["STUB_ORDER"]
def note(x):
    open(order, "a").write(x + "\n")
cmd = sys.argv[1]
args = dict(zip(sys.argv[2::2], sys.argv[3::2]))
if cmd == "quiesce":
    camp = args["--camp"]
    json.dump({"jobs": []}, open(os.path.join(camp, "logs", "quiesce-restore.json"), "w"))
    note("quiesce")
    sys.exit(0)
if cmd == "audit":
    note("audit")
    sys.exit(1)
if cmd == "restore":
    camp = args["--camp"]
    logs = os.path.join(camp, "logs")
    note("restore-start conformance=%s checksums=%s" % (os.path.exists(os.path.join(logs, "CONFORMANCE.txt")),
                                                       os.path.exists(os.path.join(logs, "outputs-sha256.txt"))))
    mode = os.environ.get("STUB_RESTORE", "ok")
    if mode == "slow":
        open(os.environ["STUB_READY"], "w").write("x")
        time.sleep(2)
    note("restore-end")
    sys.exit(1 if mode == "fail" else 0)
sys.exit(3)
"""
STUB_MONITOR = r"""
import os, sys
open(os.environ["STUB_ORDER"], "a").write(sys.argv[1] + "\n")
print("{}")
"""


def _ac_power():
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
    return "AC Power" in out.splitlines()[0] if out else False


@unittest.skipUnless(_ac_power(), "the chain checks AC power before the quiesce")
class FinishExecuted(unittest.TestCase):
    """Runs the real chain against a stub tooling clone; the audit stub fails, so the chain
    ends NOT STARTED through finish. Nothing real is quiesced or restored."""

    def run_chain(self, mode, signal_during_restore=False):
        import signal, time
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        camp = Path(tmp.name) / "v0.7.0-requalification-a1-soak1"
        b = camp / "src/cand/knotrel-benchmarks"
        (b / "scripts").mkdir(parents=True)
        (b / "results/v0.7.0-requalification").mkdir(parents=True)
        (camp / "logs").mkdir()
        (b / "scripts/launcher_audit.py").write_text(STUB_AUDIT)
        (b / "scripts/conformance_monitor.py").write_text(STUB_MONITOR)
        (b / "results/v0.7.0-requalification/MATRIX.json").write_text("{}")
        order = Path(tmp.name) / "order.txt"
        ready = Path(tmp.name) / "ready"
        env = {**os.environ, "STUB_ORDER": str(order), "STUB_RESTORE": mode, "STUB_READY": str(ready)}
        proc = subprocess.Popen(["sh", str(RQ / "run_final_chain.sh"), str(camp), "-", "1", "t", "--soak"],
                                env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if signal_during_restore:
            deadline = time.time() + 20
            while not ready.exists() and time.time() < deadline:
                time.sleep(0.05)
            proc.send_signal(signal.SIGTERM)
            proc.send_signal(signal.SIGHUP)
        out, _ = proc.communicate(timeout=60)
        return proc.returncode, out, order.read_text().splitlines(), camp

    def test_restore_after_records_on_not_started(self):
        rc, out, order, camp = self.run_chain("ok")
        self.assertEqual(rc, 4, out)
        self.assertEqual(order[:2], ["quiesce", "audit"])
        self.assertIn("git-snapshot", order)
        self.assertLess(order.index("git-snapshot"), order.index("restore-start conformance=True checksums=True"))
        self.assertTrue((camp / "logs/CONFORMANCE.txt").read_text().startswith("SOAK NOT STARTED: launcher audit failed"))
        self.assertIn("RESTORE OK", out)
        self.assertRegex((camp / "logs/chain-steps.txt").read_text(), r"RESTORE \S+ ok")

    def test_failed_restore_exits_21(self):
        rc, out, order, camp = self.run_chain("fail")
        self.assertEqual(rc, 21, out)
        self.assertIn("RESTORE FAILED", out)
        self.assertTrue((camp / "logs/CONFORMANCE.txt").read_text().startswith("SOAK NOT STARTED"))

    def test_signals_during_finish_do_not_skip_restore(self):
        rc, out, order, camp = self.run_chain("slow", signal_during_restore=True)
        self.assertIn("restore-end", order)
        self.assertEqual(rc, 4, out)
        self.assertIn("RESTORE OK", out)


if __name__ == "__main__":
    unittest.main()
