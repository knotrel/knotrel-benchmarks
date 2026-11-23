#!/usr/bin/env python3
"""Autonomous runner of Part 1 of the v1.0.0 qualification (results/v1.0.0-qualification/PROTOCOL.md).

The v0.9.0 Part 1 runner (``run_v090q_autonomous.Part1Runner``, itself the v0.7.0
qualification-3 runner, revision 3) unchanged in behaviour: the same preflight, telemetry
monitor, interference policy, limits (budget 105 minutes), restart rule, end checks and
records. What differs is the binding and the reduced chain of the approved plan (knotrel
``docs/releases/v1.0.0-qualification-plan.md`` sections 4, 5.3 and 13 item 3):

- the freeze record is this directory's ``FREEZE.json`` (revision 1, campaign
  "v1.0.0 qualification"); the preflight applies every check of ``freeze_check_v100q.py``
  (candidate, reference ``REFERENCE``, core-rule outcome and provenance, the complete
  hash list, the freeze commit as the only child of the tooling commit);
- at its end it records the cause of a non-CONFORMING end (``part1_failures_v100q.py``:
  product, infrastructure or conformance, in ``logs/failures.jsonl``, and the Part 1 outcome
  in ``logs/part1-outcome.json``); a product failure never allows a second attempt;
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
import freeze_check_v100q as fc  # noqa: E402
import part1_failures_v100q as p1  # noqa: E402

V100 = "results/v1.0.0-qualification"
FREEZE_REVISION = fc.FREEZE_REVISION
CAMPAIGN = fc.CAMPAIGN
REFERENCE = fc.REFERENCE  # knotrel v0.9.0 (plan section 2); the preflight requires it
CORE_RULE_OUTCOMES = fc.CORE_RULE_OUTCOMES
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

    def git(self, *args: str) -> str:
        """Git in the campaign's tooling clone (a clone of the freeze commit, with its history)."""
        return subprocess.run(["git", "-C", str(self.bench), *args], capture_output=True, text=True,
                              check=True).stdout

    def frozen_digest(self, path: str):
        """SHA-256 of a file of the tooling clone, or None if it cannot be read."""
        return fc.sha256_file(self.bench / path)

    def preflight(self) -> None:
        """The frozen preflight (``run_v090q_autonomous.Part1Runner.preflight``) with this
        campaign's freeze record and the v1.0 freeze guards of ``freeze_check_v100q.py``: the
        record's identity, candidate and reference (``REFERENCE``), core-rule outcome; its hash
        list equal to its hashed files and covering ``REQUIRED_FROZEN_PATHS``; every file's hash;
        the pre-freeze ``core-rule.json`` (``core_rule.comparison``, under EVIDENCE_ROOT, the
        campaign directory's parent) with its SHA-256, and this directory's
        ``logs/core-rule.json`` agreeing with it (outcome, per-pair booleans); and the
        freeze commit (the clone's HEAD) as the only child of ``tooling.commit``, adding only
        FREEZE.json."""
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
        problems = fc.record_problems(freeze, self.cand, REFERENCE)
        if not problems:
            problems = fc.file_problems(freeze, self.frozen_digest)
        if not problems:
            problems = fc.core_rule_problems(freeze, self.campaign_root().parent,
                                             self.campaign_root() / "logs" / "core-rule.json")
        if not problems:
            try:
                head = self.git("rev-parse", "HEAD").strip()
            except (OSError, subprocess.CalledProcessError) as error:
                raise Stop("NOT STARTED", f"the tooling clone is not a Git checkout: {error}")
            problems = fc.git_problems(freeze, head, self.git)
        if problems:
            raise Stop("NOT STARTED", "; ".join(problems))
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
        """The frozen records with this directory's helper scripts and outputs (restored
        afterwards), preceded by the failure record of plan section 5.5
        (``part1_failures_v100q.record``: ``logs/failures.jsonl`` classifies every cause of a
        non-CONFORMING end as product, infrastructure or conformance, and
        ``logs/part1-outcome.json`` lists FAIL and not-run cells). Each is attempted even if
        the other fails."""
        error = None
        try:
            p1.record(self.camp, self.status, self.cause)
        except Exception as exc:  # noqa: BLE001 - the frozen records must still be written
            error = exc
        saved = base.Q3, base.OUTPUTS
        base.Q3, base.OUTPUTS = V100, self.outputs
        try:
            base.Runner.write_records(self)
        finally:
            base.Q3, base.OUTPUTS = saved
        if error is not None:
            raise error

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
