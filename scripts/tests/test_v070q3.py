"""Tests for the v0.7.0 qualification 3 tooling (results/v0.7.0-qualification-3).

They pin what qualification 3 changes relative to the re-qualification (amendment 3
revision 2) and that nothing else drifts: the chain, the launch-environment check and the
precheck agree on paths and arguments; the B/C cells and window multipliers include exactly
the capability-equivalent cells; the matrix differs from the re-qualification's only where
the protocol says; the collectors and analyzers bind the qualification-3 matrix.
"""

import json
import re
import shlex
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_lifecycle_qualification as lifecycle  # noqa: E402

Q3 = ROOT / "results" / "v0.7.0-qualification-3"
RQ = ROOT / "results" / "v0.7.0-requalification"
MATRIX = json.loads((Q3 / "MATRIX.json").read_text())
RQ_MATRIX = json.loads((RQ / "MATRIX.json").read_text())
CHAIN = (Q3 / "run_final_chain.sh").read_text()
ENV = (Q3 / "launch_env_check.sh").read_text()
PREPARE = (Q3 / "prepare_campaign.sh").read_text()
PRECHECK = (Q3 / "precheck_terminal.sh").read_text()
LAUNCH = (Q3 / "launch_command.sh").read_text()
MULTIPLIERS = json.loads((Q3 / "window-multipliers-q3.json").read_text())


def collector_args(text: str, experiment: str) -> list:
    """Collector arguments for EXPERIMENT: after `run_v070q3_collect.py EXPERIMENT`, or after
    the chain's `step NAME CODE EXPERIMENT`, up to a redirection; --dry-run dropped."""
    for line in text.splitlines():
        if f"run_v070q3_collect.py {experiment} " in line:
            words = shlex.split(line[line.index("run_v070q3_collect.py"):].split(">")[0])
            return [w for w in words[2:] if w != "--dry-run"]
        words = line.split()
        if len(words) > 3 and words[0] == "step" and words[3] == experiment:
            return [w for w in shlex.split(line)[4:] if w != "--dry-run"]
    raise AssertionError(f"no collector call for {experiment}")


class Paths(unittest.TestCase):
    def test_every_script_uses_qualification_3_paths(self):
        for name, text in (("chain", CHAIN), ("env", ENV), ("precheck", PRECHECK), ("launch", LAUNCH)):
            self.assertNotIn("results/v0.7.0-requalification/", text.replace("results/v0.7.0-requalification/prepare_campaign.sh", ""), name)
            self.assertNotIn("run_v070r_collect.py", text, name)
        self.assertIn("MATRIX=$B/results/v0.7.0-qualification-3/MATRIX.json", CHAIN)
        self.assertIn("MATRIX=$B/results/v0.7.0-qualification-3/MATRIX.json", PRECHECK)
        self.assertIn("R=$CAMP/src/cand/knotrel-benchmarks/results/v0.7.0-qualification-3", LAUNCH)

    def test_prepare_requires_freeze_q3_and_series_q3(self):
        self.assertIn("results/v0.7.0-qualification-3/FREEZE-Q3.json", PREPARE)
        self.assertIn('[ "$SERIES" = q3 ]', PREPARE)
        self.assertIn("['conformance']['qualification_3']['attempts_cap']", PREPARE)
        self.assertIn("CAMP=/Users/rt/workspace/knotrel/evidence/v0.7.0-qualification-3-$C8", PREPARE)
        self.assertIn("--session-seeds 130720 130721 130722", PREPARE)
        self.assertIn("results/v0.7.0-qualification-3/launch_env_check.sh", PREPARE)
        self.assertNotIn("FREEZE-A3.json", PREPARE)

    def test_chain_extension_seeds(self):
        self.assertIn("--session-seeds 130730 130731 130732", CHAIN)
        # Addendum 1, A5: a3-3's seeds are kept; the whole A experiment matches the re-qualification.
        self.assertEqual(MATRIX["experiments"]["A"], RQ_MATRIX["experiments"]["A"])


class ChainAndDryRunsAgree(unittest.TestCase):
    def test_collector_arguments_match(self):
        for experiment in ("bc", "r", "rmem", "mdesc", "mreg"):
            chain, env = collector_args(CHAIN, experiment), collector_args(ENV, experiment)
            # --out differs (the dry run's path is never created); everything else is identical.
            strip = lambda a: [x for i, x in enumerate(a) if not (x == "--out" or (i and a[i - 1] == "--out"))]
            self.assertEqual(strip(chain), strip(env), experiment)

    def test_bc_uses_equivalent_cells_and_q3_multipliers(self):
        args = collector_args(CHAIN, "bc")
        self.assertIn("--equivalent-references", args)
        self.assertEqual(args[args.index("--window-multipliers") + 1], "results/v0.7.0-qualification-3/window-multipliers-q3.json")
        self.assertEqual(args[args.index("--order-seed") + 1], "50720")


class Cells(unittest.TestCase):
    def test_equivalent_cells_and_their_multipliers(self):
        frozen = lifecycle.matrix("final", "compact-bfs")
        q3 = lifecycle.matrix("final", "compact-bfs", True)
        added = [c for c in q3 if c["id"] not in {f["id"] for f in frozen}]
        self.assertEqual(len(added), 13)
        deciding = MATRIX["experiments"]["B_C"]["equivalent_references"]["deciding"]
        descriptive = MATRIX["experiments"]["B_C"]["equivalent_references"]["descriptive"]
        self.assertEqual(sorted(c["id"] for c in added), sorted(deciding))
        self.assertEqual(sorted(d.replace("-equivalent", "") for d in deciding), sorted(descriptive))
        by_id = {c["id"]: c for c in q3}
        for cell in added:
            twin = by_id[cell["id"].replace("-equivalent", "")]
            self.assertEqual(cell["tolerance"], twin["tolerance"])
            self.assertEqual(MULTIPLIERS[cell["id"]], MULTIPLIERS[twin["id"]])
            scenario = cell["args"][cell["args"].index("--scenario") + 1]
            self.assertEqual(scenario, twin["args"][twin["args"].index("--scenario") + 1] + "-equivalent")
            strip = lambda a: [x for i, x in enumerate(a) if not (x == "--scenario" or (i and a[i - 1] == "--scenario"))]
            self.assertEqual(strip(cell["args"]), strip(twin["args"]))
        lifecycle.apply_multipliers(q3, MULTIPLIERS)  # complete, no unknown key

    def test_default_matrix_unchanged(self):
        self.assertEqual(len(lifecycle.matrix("final", "compact-bfs")), 127)
        self.assertFalse(any("equivalent" in c["id"] for c in lifecycle.matrix("final", "compact-bfs")))


class MatrixDelta(unittest.TestCase):
    def test_only_declared_differences(self):
        changed = {k for k in set(MATRIX) | set(RQ_MATRIX) if MATRIX.get(k) != RQ_MATRIX.get(k)}
        self.assertEqual(changed, {"schema", "status", "references", "experiments", "analysis", "conformance"})
        self.assertEqual(MATRIX["rules"], RQ_MATRIX["rules"])
        conf = {k: v for k, v in MATRIX["conformance"].items() if k != "qualification_3"}
        self.assertEqual(conf, RQ_MATRIX["conformance"])
        self.assertEqual(MATRIX["conformance"]["qualification_3"]["attempt_series"], "q3")
        self.assertEqual(MATRIX["conformance"]["qualification_3"]["attempts_cap"], 3)
        for name in ("R", "Rmem", "M_desc", "M_reg"):
            a, b = dict(MATRIX["experiments"][name]), dict(RQ_MATRIX["experiments"][name])
            a.pop("question"), b.pop("question")
            self.assertEqual(a, b, name)

    def test_thresholds_unchanged(self):
        frozen = {c["id"]: c.get("tolerance") for c in lifecycle.matrix("final", "compact-bfs")}
        q3 = {c["id"]: c.get("tolerance") for c in lifecycle.matrix("final", "compact-bfs", True)}
        for cell_id, tolerance in frozen.items():
            self.assertEqual(q3[cell_id], tolerance)


class Bindings(unittest.TestCase):
    def test_collector_and_analyzer_bind_q3_matrix(self):
        collect = (ROOT / "scripts" / "run_v070q3_collect.py").read_text()
        self.assertIn('"v0.7.0-qualification-3" / "MATRIX.json"', collect)
        analyze = (ROOT / "scripts" / "analyze_v070q3.py").read_text()
        self.assertIn('"v0.7.0-qualification-3" / "MATRIX.json"', analyze)
        self.assertIn("a4.installed()", analyze)


if __name__ == "__main__":
    unittest.main()
