#!/usr/bin/env python3
"""Autonomous runner of Part 1 of the v1.0.0 qualification (results/v1.0.0-qualification/PROTOCOL.md).

The v0.9.0 Part 1 runner (``run_v090q_autonomous.Part1Runner``, itself the v0.7.0
qualification-3 runner, revision 3) unchanged in behaviour: the same preflight, telemetry
monitor, interference policy, limits (budget 105 minutes), restart rule, end checks and
records. What differs is the binding and the reduced chain of the approved plan (knotrel
``docs/releases/v1.0.0-qualification-plan.md`` sections 4, 5.3 and 13 item 3):

- the freeze record is this directory's ``FREEZE.json`` (revision 1, campaign
  "v1.0.0 qualification"); the preflight also requires its reference commit, its candidate
  commit (a parameter of the campaign, never hard-coded) and its core-rule outcome;
- collectors are bound to this directory's matrix (``run_v100q_collect.py``);
- **A runs in two fixed blocks with no interim analysis** (plan section 5.3, option a):
  block 1 from ``A/plan`` into ``A/raw-main``, then block 2 from ``A/plan-block2`` into
  ``A/extension/raw-extension`` (the frozen paths ``conformance_gate.collector_counts``
  reads). Both plans are prepared by ``prepare_campaign.sh`` before the launch, so no step
  of the chain reads A data. The A analysis (``analyze_v100q_a.py``) runs once, after the
  chain, like every other analysis;
- B/C runs ``--only B4,C`` (the full B/C collector and T5 only if the freeze record says
  the core rule triggered, plan section 4.3);
- R, Rmem and M_reg as in v0.9.0, against v0.9.0; no T5 (unless the core rule triggered),
  no M_desc, no Part 2.

Q (feeder under load) is not run by this runner: ``run_part3.sh`` runs it after Part 1 ends
CONFORMING, under its own cap.

    run_v100q_autonomous.py CAMP CAND_SHA [--dry-run]
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import run_v070q3_autonomous as base  # noqa: E402
import run_v090q_autonomous as v090  # noqa: E402

V100 = "results/v1.0.0-qualification"
FREEZE_REVISION = 1
CAMPAIGN = "v1.0.0 qualification"
REFERENCE = "223f04c10b0af663b54e269e0970ee10ac1dc6b2"  # knotrel v0.9.0 (plan section 2)
CORE_RULE_OUTCOMES = ("identical", "different")
Stop = base.Stop
SHA = re.compile(r"[0-9a-f]{40}")
OUTPUTS = ("A/raw-main", "A/extension", "BC", "T5", "R", "Rmem", "Mreg", "gate")


class Part1Runner(v090.Part1Runner):
    """Part 1 of the v1.0.0 qualification: A (two fixed blocks), B4+C, R, Rmem, M_reg."""

    outputs = OUTPUTS

    def freeze(self) -> dict:
        return json.loads((self.bench / V100 / "FREEZE.json").read_text())

    def core_rule_triggered(self) -> bool:
        """True if the freeze record says the core's executed code changed (plan section 4.3)."""
        outcome = self.freeze().get("core_rule", {}).get("outcome")
        if outcome not in CORE_RULE_OUTCOMES:
            raise Stop("NOT STARTED", f"freeze core_rule.outcome is {outcome!r}, expected one of {CORE_RULE_OUTCOMES}")
        return outcome == "different"

    def preflight(self) -> None:
        """The frozen preflight (``run_v090q_autonomous.Part1Runner.preflight``) with this
        campaign's freeze record, plus the v1.0 freeze fields: a 40-character candidate equal to
        the freeze record's, a 40-character reference commit and a core-rule outcome."""
        name = self.campaign_name()
        if f"-{self.cand[:7]}-" not in name:
            raise Stop("NOT STARTED", f"candidate {self.cand} does not match {name}")
        if not SHA.fullmatch(self.cand):
            raise Stop("NOT STARTED", f"candidate {self.cand!r} is not a 40-character commit")
        for out in self.outputs:
            if (self.camp / out).exists():
                raise Stop("NOT STARTED", f"output already exists: {out}")
        path = self.bench / V100 / "FREEZE.json"
        if not path.exists():
            raise Stop("NOT STARTED", f"no {V100}/FREEZE.json: the campaign is not frozen")
        freeze = json.loads(path.read_text())
        if freeze.get("revision") != FREEZE_REVISION or freeze.get("campaign") != CAMPAIGN:
            raise Stop("NOT STARTED", f"freeze {freeze.get('campaign')!r} revision {freeze.get('revision')}, "
                                      f"expected {CAMPAIGN!r} revision {FREEZE_REVISION}")
        if not freeze.get("frozen_utc") or "NOT FROZEN" in str(freeze.get("status", "")):
            raise Stop("NOT STARTED", "the freeze record is a draft (no frozen_utc, or status NOT FROZEN)")
        if freeze.get("candidate", {}).get("commit") != self.cand:
            raise Stop("NOT STARTED", f"freeze candidate {freeze.get('candidate', {}).get('commit')} is not {self.cand}")
        reference = freeze.get("reference", {}).get("commit")
        if not SHA.fullmatch(reference or ""):
            raise Stop("NOT STARTED", f"freeze reference commit {reference!r} is not a 40-character commit")
        self.core_rule_triggered()
        bad = [p for p, h in freeze["file_sha256"].items() if base.sha256(self.bench / p) != h]
        if bad:
            raise Stop("NOT STARTED", f"frozen files differ: {bad[:5]}")
        self.check_binaries("preflight")
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        if "AC Power" not in (batt.splitlines() or [""])[0]:
            raise Stop("NOT STARTED", "not on AC power")
        if shutil.disk_usage(self.campaign_root()).free < self.limits["min_free_bytes"]:
            raise Stop("NOT STARTED", "less free disk space than required")
        restored = subprocess.run(["sh", str(self.bench / V100 / "check_restored.sh")], capture_output=True, text=True)
        if restored.returncode != 0:
            raise Stop("NOT STARTED", f"an earlier launcher quiesce is not restored: {restored.stdout[-300:]}")

    def collect(self, experiment: str, *args: str) -> List[str]:
        return [self.python, "scripts/run_v100q_collect.py", experiment, *args]

    def write_records(self) -> None:
        """The frozen records with this directory's helper scripts and outputs (restored afterwards)."""
        saved = base.Q3, base.OUTPUTS
        base.Q3, base.OUTPUTS = V100, self.outputs
        try:
            base.Runner.write_records(self)
        finally:
            base.Q3, base.OUTPUTS = saved

    def bc_args(self) -> List[str]:
        t = self.targets
        args = ["bc", "--out", str(self.camp / "BC"), "--profile", "final", "--core",
                str(t / "cand-probes/release/core-lifecycle"), "--core-count",
                str(t / "cand-probes-count/release/core-lifecycle"), "--http",
                str(t / "cand-probes/release/http-lifecycle"), "--order-seed", "50720", "--knotrel",
                str(self.camp / "src/cand/knotrel"), "--lifecycle-engines", "compact-bfs",
                "--equivalent-references", "--window-multipliers", f"{V100}/window-multipliers-q3.json"]
        if not self.core_rule_triggered():
            args[-2:-2] = ["--only", "B4,C"]
        return args

    def sequence(self) -> None:
        """A block 1, A block 2 (no analysis in between), B4+C, [T5], R, Rmem, M_reg."""
        a, t = self.camp / "A", self.targets
        self.run_step("A-block1", self.collect("a", "--manifest", str(a / "plan/manifest.json"), "--schedule",
                                               str(a / "plan/schedule.json"), "--execute", str(a / "raw-main")),
                      "A-block1", [a / "raw-main"])
        self.run_step("A-block2", self.collect("a", "--manifest", str(a / "plan-block2/manifest.json"), "--schedule",
                                               str(a / "plan-block2/schedule.json"), "--execute",
                                               str(a / "extension/raw-extension")),
                      "A-block2", [a / "extension/raw-extension"])
        self.run_step("BC", self.collect(*self.bc_args()), "BC")
        if self.core_rule_triggered():
            self.run_step("T5", [self.python, "scripts/run_v070q3_t5.py", "--out", str(self.camp / "T5"), "--base",
                                 str(t / "t5base-probes/release/core-lifecycle"), "--cand",
                                 str(t / "cand-probes/release/core-lifecycle"), "--order-seed", "50730"], "T5")
        self.run_step("R", self.collect("r", "--out", str(self.camp / "R"), "--ref", str(t / "ref-probes/release/release-cells"),
                                        "--cand", str(t / "cand-probes/release/release-cells")), "R")
        self.run_step("Rmem", self.collect("rmem", "--out", str(self.camp / "Rmem"), "--ref",
                                           str(t / "ref-probes-peak/release/memory-peak"), "--cand",
                                           str(t / "cand-probes-peak/release/memory-peak")), "Rmem")
        self.run_step("Mreg", self.collect("mreg", "--out", str(self.camp / "Mreg"), "--probe",
                                           str(t / "contention/release/contention-probe"), "--ref",
                                           str(t / "ref-server/release/knotrel-server"), "--cand",
                                           str(t / "cand-server/release/knotrel-server")), "Mreg")


def main(argv: List[str]) -> int:
    args = argv[1:]
    dry = "--dry-run" in args
    if dry:
        args.remove("--dry-run")
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    camp, cand = Path(args[0]).resolve(), args[1]
    runner = Part1Runner(camp, cand)
    if dry:
        runner.logs.mkdir(parents=True, exist_ok=True)
        try:
            runner.preflight()
        except Stop as stop:
            print(f"DRY-RUN {stop.status}: {stop.cause}")
            return 1
        print("DRY-RUN PREFLIGHT OK")
        return 0
    return runner.run()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
