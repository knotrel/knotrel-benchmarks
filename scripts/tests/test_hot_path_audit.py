"""Unit tests for the hot-path audit collector's pure helpers."""

from __future__ import annotations

import collections
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_hot_path_audit as audit  # noqa: E402


class ScheduleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.cells = audit.all_cells()
        self.schedule = audit.build_schedule(self.cells)

    def test_cells_are_unique_and_cover_required_matrix(self) -> None:
        ids = [cell["id"] for cell in self.cells]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sum(cell["kind"] == "init" for cell in self.cells), 6)
        self.assertEqual(sum(cell["kind"] == "dynamic" for cell in self.cells), 6)
        self.assertEqual(sum(cell["kind"] == "probe" for cell in self.cells), 2)
        self.assertIn("init/hdt/chain-split-rejoin-v1/200000", ids)
        self.assertIn("init/compact-bfs/sustained-churn-blocks-v1/100000", ids)

    def test_every_round_runs_every_arm_once_per_cell(self) -> None:
        per_round = collections.Counter(
            (entry["round"], entry["cell"], entry["arm"]) for entry in self.schedule["entries"])
        self.assertEqual(set(per_round.values()), {1})
        self.assertEqual(len(per_round), audit.ROUNDS * len(self.cells) * len(audit.ARMS))

    def test_arm_blocks_are_contiguous(self) -> None:
        entries = self.schedule["entries"]
        for start in range(0, len(entries), len(audit.ARMS)):
            block = entries[start:start + len(audit.ARMS)]
            self.assertEqual(len({(e["round"], e["cell"]) for e in block}), 1)
            self.assertEqual(sorted(e["arm"] for e in block), sorted(audit.ARMS))

    def test_positions_and_orders_are_counterbalanced(self) -> None:
        orders = len(audit.arm_orders())
        self.assertEqual(audit.ROUNDS % orders, 0)
        for cell in self.cells:
            entries = [e for e in self.schedule["entries"] if e["cell"] == cell["id"]]
            positions = collections.Counter((e["arm"], e["position"]) for e in entries)
            self.assertEqual(set(positions.values()), {audit.ROUNDS // len(audit.ARMS)})
            seen_orders = collections.Counter(e["order"] for e in entries if e["position"] == 0)
            self.assertEqual(set(seen_orders.values()), {audit.ROUNDS // orders})

    def test_schedule_is_deterministic_and_seed_sensitive(self) -> None:
        again = audit.build_schedule(self.cells)
        self.assertEqual(self.schedule, again)
        other = audit.build_schedule(self.cells, seed=audit.SCHEDULE_SEED + 1)
        self.assertNotEqual(self.schedule["entries"], other["entries"])

    def test_sessions_split_rounds_evenly(self) -> None:
        sessions = collections.Counter(e["session"] for e in self.schedule["entries"])
        self.assertEqual(len(sessions), audit.SESSIONS)
        self.assertEqual(len(set(sessions.values())), 1)
        with self.assertRaises(ValueError):
            audit.build_schedule(self.cells, rounds=5, sessions=2)

    def test_e2e_schedule_cycles_arm_orders(self) -> None:
        entries = audit.e2e_schedule()
        self.assertEqual(len(entries), audit.E2E_ROUNDS * len(audit.ARMS))
        firsts = [e["arm"] for e in entries if e["position"] == 0]
        self.assertEqual(collections.Counter(firsts), {"base": 2, "cand": 2, "aa": 2})


class CommandTests(unittest.TestCase):
    binaries = {
        "initialization-profile": "/b/init",
        "knotrel-benchmarks": "/b/run",
        "router-probe-timing": "/b/probe",
    }

    def test_init_command_is_facade_limited_bulk_whole(self) -> None:
        cell = {"engine": "hdt", "workload": "chain-split-rejoin-v1", "nodes": 200000}
        argv = audit.command_for("init", cell, self.binaries)
        self.assertEqual(argv[0], "/b/init")
        for flag, value in (("--surface", "facade-limited"), ("--init-mode", "bulk"),
                            ("--timing", "whole"), ("--seed", "42"), ("--nodes", "200000")):
            self.assertEqual(argv[argv.index(flag) + 1], value)
        self.assertEqual(argv[-4:], ["--warmup", "1", "--repetitions", "5"])

    def test_dynamic_and_probe_commands(self) -> None:
        cell = {"engine": "ett-scan", "workload": "sustained-churn-blocks-v1", "nodes": 10000, "rounds": 200}
        argv = audit.command_for("dynamic", cell, self.binaries)
        self.assertEqual(argv[:3], ["/b/run", "--engine", "ett-scan"])
        self.assertIn("--seed", argv)
        probe = audit.command_for("probe", {"metrics": True}, self.binaries)
        self.assertEqual(probe[:3], ["/b/probe", "--mode", "timing"])
        self.assertEqual(probe[-1], "--metrics")
        self.assertNotIn("--metrics", audit.command_for("probe", {"metrics": False}, self.binaries))

    def test_child_environment_is_minimal_and_explicit(self) -> None:
        env = audit.child_env()
        self.assertTrue(set(env) <= {"PATH", "HOME", "LANG", "LC_ALL"})
        self.assertEqual(env["LC_ALL"], "C")

    def test_code_only_pathspec_excludes_docs(self) -> None:
        self.assertEqual(audit.code_only_pathspec(), ["--", ".", ":(exclude)docs"])


if __name__ == "__main__":
    unittest.main()
