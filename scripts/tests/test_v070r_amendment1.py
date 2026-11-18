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
            return 0, ""
        if cmd[0] == "crontab":
            return 1, ""
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
        self.assertEqual(len(la.audit_jobs([job], [], [])), 1)

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

    def test_fail_closed_and_allow_lists(self):
        reasons = la.audit_jobs(self.jobs(), [], ["application.com.anthropic.claudefordesktop."])
        self.assertEqual(len(reasons), 2)
        self.assertTrue(any("timer" in r for r in reasons) and any("unknown" in r and "undeterminable" in r for r in reasons))
        self.assertEqual(la.audit_jobs(self.jobs(), ["timer", "unknown"], ["application.com.anthropic.claudefordesktop."]), [])

    def test_extensions(self):
        out = ("     com.apple.x(1.0)\tA\t2026\t/System/Library/X.appex\n"
               "+    net.whatsapp.WhatsApp.ServiceExtension(26)\tB\t2026\t/Applications/WhatsApp.app/Contents/PlugIns/S.appex\n"
               " (435 plug-ins)\n")
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
        self.assertEqual(len(manifest["manual_restore"]), 3)
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

    def test_relaunch_refused_after_quiesce(self):
        self.assertIn('"$L/quiesce-restore.json"; do', self.text)

    def test_prepare_series_and_soak(self):
        prep = (RQ / "prepare_campaign.sh").read_text()
        self.assertIn('CAMP=$CAMP-$SERIES-attempt$ATTEMPT', prep)
        soak = (RQ / "prepare_soak.sh").read_text()
        self.assertNotIn("cargo", soak)
        self.assertNotIn("rm -rf", soak)
        self.assertLess(soak.index("max_soaks"), soak.index("mkdir"))


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
        for label in q["allow_jobs"]:
            self.assertTrue(label in q["allow_jobs_reasons"] or any(
                k.endswith("*") and label.startswith(k[:-1]) for k in q["allow_jobs_reasons"]), label)
        soak = json.loads((RQ / "MATRIX.json").read_text())["conformance"]["soak"]
        self.assertEqual((soak["duration_s"], soak["max_soaks"]), (4800, 2))


if __name__ == "__main__":
    unittest.main()
