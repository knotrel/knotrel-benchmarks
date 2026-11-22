"""Tests for the declared v0.6.0 M_reg rerun (matrix, monitor pattern, conformance, Git snapshot)."""

import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import historical  # noqa: E402

historical.ensure()  # earlier campaigns are read from their release tags

import analyze_v060_mreg_rerun as rr  # noqa: E402
import analyze_v060_m_supplement as sup  # noqa: E402
import git_state_snapshot as gs  # noqa: E402
import host_activity_monitor as mon  # noqa: E402
from test_v060_m_supplement import SupplementAnalysis  # noqa: E402

RERUN = json.loads(rr.MATRIX.read_text())
SUPP = json.loads(sup.MATRIX.read_text())


class RerunMatrix(unittest.TestCase):
    def test_cells_and_statistics_match_the_supplement(self):
        a, b = RERUN["M_reg_supplement"], SUPP["M_reg_supplement"]
        self.assertEqual(a["cells"], b["cells"])
        for key in ("warmup_pairs", "pairs", "seed"):
            self.assertEqual(a[key], b[key])
        self.assertNotEqual(a["order_seed"], b["order_seed"])
        for key in ("interval", "tolerances", "classification", "M_reg", "validity"):
            self.assertEqual(RERUN["rules"][key], SUPP["rules"][key])

    def test_binaries_are_the_measured_ones(self):
        self.assertEqual(RERUN["binaries"]["probe"]["sha256"],
                         "e7d0b4b6757b5941eef156eed9f3073d3581879dff9ab78c2aadee8a8058a34d")
        self.assertEqual(RERUN["binaries"]["cand"]["sha256"][:8], "d4adec2e")
        self.assertEqual(RERUN["binaries"]["ref"]["sha256"][:8], "e3d12df8")


class MonitorPattern(unittest.TestCase):
    def test_matches_automated_activity(self):
        for args in ("/Library/Developer/CommandLineTools/usr/bin/git fetch",
                     "git-upload-pack /x", "/usr/libexec/git-core/git-remote-https origin u",
                     "cargo build", "/x/rustc --edition 2024",
                     "/Applications/Antigravity IDE.app/Contents/MacOS/Electron",
                     "/Applications/Visual Studio Code.app/Contents/MacOS/Code"):
            self.assertTrue(mon.PATTERN.search(args), args)

    def test_ignores_measured_and_baseline_processes(self):
        for args in ("/e/targets/cand-server/release/knotrel-server", "/e/contention-probe --nodes 1",
                     "/Applications/Claude.app/Contents/Frameworks/Claude Helper (Renderer).app/x",
                     "python3 scripts/run_v060_mreg_rerun.py --out x", "/usr/sbin/digit"):
            self.assertFalse(mon.PATTERN.search(args), args)


class Conformance(unittest.TestCase):
    def write(self, root, match_at=None, quiet_match=False, git_changed=False):
        SupplementAnalysis().write_mreg(root)
        log_path = Path(root) / "run-log.json"
        log = json.loads(log_path.read_text())
        for index, child in enumerate(log["children"]):
            child["host"] = {"utc": f"2026-11-17T08:{index // 60:02d}:{index % 60:02d}Z"}
            child["seconds"] = 0.5
        log_path.write_text(json.dumps(log))
        monitor = Path(root) / "monitor.jsonl"
        lines = [{"kind": "start", "utc": "2026-11-17T07:59:00.0Z"}]
        if match_at:
            lines.append({"kind": "match", "utc": match_at, "processes": [{"args": "git fetch"}]})
        monitor.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
        quiet = Path(root) / "quiet.jsonl"
        quiet.write_text(json.dumps({"kind": "match", "utc": "2026-11-17T07:55:00.0Z"}) + "\n" if quiet_match else "")
        diff = Path(root) / "diff.json"
        diff.write_text(json.dumps({"changed": ["clone:FETCH_HEAD_mtime"] if git_changed else []}))
        return monitor, quiet, diff, log["children"]

    def test_clean_run_keeps_analyzer_verdicts(self):
        with tempfile.TemporaryDirectory() as tmp:
            monitor, quiet, diff, _ = self.write(tmp)
            result = rr.analyze(Path(tmp), monitor, quiet, diff, RERUN)
            self.assertEqual({c["verdict"] for c in result["cells"].values()}, {"PASS"})

    def test_match_inside_an_analyzed_child_voids_only_its_cell(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, _, _, children = self.write(tmp)
            target = next(c for c in children if "-analyzed-" in c["name"])
            monitor, quiet, diff, _ = self.write(tempfile.mkdtemp(dir=tmp), match_at=target["host"]["utc"][:-1] + ".3Z")
            directory = monitor.parent
            result = rr.analyze(directory, monitor, quiet, diff, RERUN)
            verdicts = {k: v["verdict"] for k, v in result["cells"].items()}
            cell = rr.NAME.match(target["name"])["cell"]
            self.assertEqual(verdicts[cell], "NONCONFORMING")
            self.assertEqual(sorted(verdicts.values()), ["NONCONFORMING", "PASS"])

    def test_quiet_period_or_git_change_voids_every_cell(self):
        for kwargs in ({"quiet_match": True}, {"git_changed": True}):
            with tempfile.TemporaryDirectory() as tmp:
                monitor, quiet, diff, _ = self.write(tmp, **kwargs)
                result = rr.analyze(Path(tmp), monitor, quiet, diff, RERUN)
                self.assertEqual({c["verdict"] for c in result["cells"].values()}, {"NONCONFORMING"})


class GitSnapshot(unittest.TestCase):
    def test_detects_fetch_head_and_reflog_changes_without_following_links(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp) / "a"
            logs = clone / ".git" / "logs" / "refs" / "remotes" / "origin"
            logs.mkdir(parents=True)
            (logs / "main").write_text("x\n")
            (Path(tmp) / "link").symlink_to(clone)
            before = gs.snapshot(tmp)
            self.assertEqual(list(before), [str(clone)])
            (logs / "main").write_text("x\ny\n")
            (clone / ".git" / "FETCH_HEAD").write_text("z")
            after = gs.snapshot(tmp)
            self.assertNotEqual(before, after)


if __name__ == "__main__":
    unittest.main()
