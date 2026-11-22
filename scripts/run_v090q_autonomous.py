#!/usr/bin/env python3
"""Autonomous runner of the v0.9.0 qualification (results/v0.9.0-qualification/PROTOCOL.md).

The v0.7.0 qualification-3 runner (``run_v070q3_autonomous.py``, revision 3) unchanged in
behaviour: the same preflight, telemetry monitor, interference policy, limits, restart rule,
end checks and records. Only the bindings change:

- the freeze record and helper scripts are this directory's (``FREEZE.json`` revision 1,
  campaign "v0.9.0 qualification");
- collectors are bound to this directory's matrix (``run_v090q_collect.py``);
- the A extension checkpoint is ``v0.9.0-Qualification-A-Extension``;
- arm B of check T5 is the probes built against knotrel v0.7.0 (``targets/t5base-probes``).

Part 1 (deciding, candidate against v0.7.0) runs A main, A analysis, A extension (if
required), B/C, T5, R, Rmem, M_desc and M_reg, budget 105 minutes, in CAMP.

Part 2 (``--part 2``; descriptive, candidate against v0.8.0) runs, in CAMP/part2 with its own
gate, logs and records: the B4 cells with ``http-lifecycle`` built against v0.8.0, then M_reg
with the v0.8.0 server as reference; budget 20 minutes. It refuses to start unless Part 1 of
the same campaign directory is CONFORMING.

    run_v090q_autonomous.py CAMP CAND_SHA [--part 2] [--dry-run]
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import run_v070q3_autonomous as base  # noqa: E402

V090 = "results/v0.9.0-qualification"
FREEZE_REVISION = 1
CAMPAIGN = "v0.9.0 qualification"
Stop = base.Stop
MANIFEST = "/Users/rt/workspace/knotrel/evidence/p0-coverage-increment-1-plan-20261030/manifest.json"


class Part1Runner(base.Runner):
    outputs = base.OUTPUTS

    def preflight(self) -> None:
        """The frozen preflight, with this campaign's freeze record and revision."""
        name = self.campaign_name()
        if f"-{self.cand[:7]}-" not in name:
            raise Stop("NOT STARTED", f"candidate {self.cand} does not match {name}")
        for out in self.outputs:
            if (self.camp / out).exists():
                raise Stop("NOT STARTED", f"output already exists: {out}")
        freeze = json.loads((self.bench / V090 / "FREEZE.json").read_text())
        if freeze.get("revision") != FREEZE_REVISION or freeze.get("campaign") != CAMPAIGN:
            raise Stop("NOT STARTED", f"freeze {freeze.get('campaign')!r} revision {freeze.get('revision')}, "
                                      f"expected {CAMPAIGN!r} revision {FREEZE_REVISION}")
        if freeze.get("candidate", {}).get("commit") != self.cand:
            raise Stop("NOT STARTED", f"freeze candidate {freeze.get('candidate', {}).get('commit')} is not {self.cand}")
        bad = [p for p, h in freeze["file_sha256"].items() if base.sha256(self.bench / p) != h]
        if bad:
            raise Stop("NOT STARTED", f"frozen files differ: {bad[:5]}")
        self.check_binaries("preflight")
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        if "AC Power" not in (batt.splitlines() or [""])[0]:
            raise Stop("NOT STARTED", "not on AC power")
        if shutil.disk_usage(self.campaign_root()).free < self.limits["min_free_bytes"]:
            raise Stop("NOT STARTED", "less free disk space than required")
        restored = subprocess.run(["sh", str(self.bench / V090 / "check_restored.sh")], capture_output=True, text=True)
        if restored.returncode != 0:
            raise Stop("NOT STARTED", f"an earlier launcher quiesce is not restored: {restored.stdout[-300:]}")

    def campaign_root(self) -> Path:
        return self.camp

    def campaign_name(self) -> str:
        return self.campaign_root().name

    def check_binaries(self, when: str) -> None:
        root = self.campaign_root()
        for line in (root / "binaries-sha256.txt").read_text().splitlines():
            digest, path = line.split(None, 1)
            if base.sha256(root / path.strip()) != digest:
                raise Stop("NOT STARTED" if when == "preflight" else "FAILED", f"binary changed: {path} ({when})")

    def collect(self, experiment: str, *args: str) -> List[str]:
        return [self.python, "scripts/run_v090q_collect.py", experiment, *args]

    def write_records(self) -> None:
        """The frozen records, with this directory's helper scripts and this part's outputs.
        The frozen module reads both names at call time; they are restored afterwards, so
        importing this module never changes the q3 runner."""
        saved = base.Q3, base.OUTPUTS
        base.Q3, base.OUTPUTS = V090, self.outputs
        try:
            super().write_records()
        finally:
            base.Q3, base.OUTPUTS = saved

    def sequence(self) -> None:
        """The frozen q3 sequence; only the bindings listed in the module docstring differ."""
        a, t = self.camp / "A", self.targets
        self.run_step("A-main", self.collect("a", "--manifest", str(a / "plan/manifest.json"), "--schedule",
                                             str(a / "plan/schedule.json"), "--execute", str(a / "raw-main")),
                      "A-main", [a / "raw-main"])
        self.analysis("A-analysis", ["scripts/analyze_bc_qualification.py", "--main", str(a / "raw-main"),
                                     "--rules", "v0.4.0", "--output", str(a / "decision-analysis-main.json")])
        cells = json.loads((a / "decision-analysis-main.json").read_text())["extension_cells_required"]
        if cells:
            self.analysis("A-extension-plan", ["scripts/prepare_bc_qualification.py", str(a / "extension/plan"),
                                               "--identities", str(a / "identities.json"), "--source-manifest",
                                               MANIFEST, "--phase", "extension", "--cells", *cells,
                                               "--checkpoint", "v0.9.0-Qualification-A-Extension",
                                               "--session-seeds", "130730", "130731", "130732"])
            self.run_step("A-extension", self.collect("a", "--manifest", str(a / "extension/plan/manifest.json"),
                                                      "--schedule", str(a / "extension/plan/schedule.json"),
                                                      "--execute", str(a / "extension/raw-extension")),
                          "A-extension", [a / "extension/raw-extension"])
            self.analysis("A-analysis-final", ["scripts/analyze_bc_qualification.py", "--main", str(a / "raw-main"),
                                               "--extension", str(a / "extension/raw-extension"), "--rules", "v0.4.0",
                                               "--output", str(a / "final-decision-analysis.json")])
        else:
            self.stamp("A-extension", "none required")
            shutil.copy(a / "decision-analysis-main.json", a / "final-decision-analysis.json")
        self.run_step("BC", self.collect(
            "bc", "--out", str(self.camp / "BC"), "--profile", "final", "--core", str(t / "cand-probes/release/core-lifecycle"),
            "--core-count", str(t / "cand-probes-count/release/core-lifecycle"), "--http",
            str(t / "cand-probes/release/http-lifecycle"), "--order-seed", "50720", "--knotrel",
            str(self.camp / "src/cand/knotrel"), "--lifecycle-engines", "compact-bfs", "--equivalent-references",
            "--window-multipliers", f"{V090}/window-multipliers-q3.json"), "BC")
        self.run_step("T5", [self.python, "scripts/run_v070q3_t5.py", "--out", str(self.camp / "T5"), "--base",
                             str(t / "t5base-probes/release/core-lifecycle"), "--cand",
                             str(t / "cand-probes/release/core-lifecycle"), "--order-seed", "50730"], "T5")
        self.run_step("R", self.collect("r", "--out", str(self.camp / "R"), "--ref", str(t / "ref-probes/release/release-cells"),
                                        "--cand", str(t / "cand-probes/release/release-cells")), "R")
        self.run_step("Rmem", self.collect("rmem", "--out", str(self.camp / "Rmem"), "--ref",
                                           str(t / "ref-probes-peak/release/memory-peak"), "--cand",
                                           str(t / "cand-probes-peak/release/memory-peak")), "Rmem")
        self.run_step("Mdesc", self.collect("mdesc", "--out", str(self.camp / "Mdesc"), "--probe",
                                            str(t / "contention/release/contention-probe"), "--server",
                                            str(t / "cand-server/release/knotrel-server")), "Mdesc")
        self.run_step("Mreg", self.collect("mreg", "--out", str(self.camp / "Mreg"), "--probe",
                                           str(t / "contention/release/contention-probe"), "--ref",
                                           str(t / "ref-server/release/knotrel-server"), "--cand",
                                           str(t / "cand-server/release/knotrel-server")), "Mreg")


class Part2Runner(Part1Runner):
    outputs = ("BC", "Mreg", "gate")

    def __init__(self, camp: Path, cand: str, limits: Optional[Dict[str, float]] = None, **kwargs: Any):
        if limits is None:
            limits = {**base.LIMITS, "budget_s": 20 * 60.0}
        super().__init__(camp, cand, limits, **kwargs)
        self.root = camp
        self.camp = camp / "part2"
        self.gate_dir = self.camp / "gate"
        self.logs = self.camp / "logs"

    def campaign_root(self) -> Path:
        return self.root

    def preflight(self) -> None:
        status = self.root / "logs" / "CONFORMANCE.txt"
        if not status.exists() or not status.read_text().startswith("CONFORMING"):
            raise Stop("NOT STARTED", "Part 1 of this campaign directory is not CONFORMING")
        super().preflight()

    def sequence(self) -> None:
        t = self.targets
        self.run_step("BC", self.collect(
            "bc", "--out", str(self.camp / "BC"), "--profile", "final", "--core", str(t / "v080-probes/release/core-lifecycle"),
            "--core-count", str(t / "v080-probes-count/release/core-lifecycle"), "--http",
            str(t / "v080-probes/release/http-lifecycle"), "--order-seed", "50720", "--knotrel",
            str(self.root / "src/v080/knotrel"), "--lifecycle-engines", "compact-bfs", "--equivalent-references",
            "--only", "B4", "--window-multipliers", f"{V090}/window-multipliers-q3.json"), "BC")
        self.run_step("Mreg", self.collect("mreg", "--out", str(self.camp / "Mreg"), "--probe",
                                           str(t / "contention/release/contention-probe"), "--ref",
                                           str(t / "v080-server/release/knotrel-server"), "--cand",
                                           str(t / "cand-server/release/knotrel-server")), "Mreg")

    def run(self) -> int:
        self.camp.mkdir(exist_ok=True)
        return super().run()



def main(argv: List[str]) -> int:
    args = argv[1:]
    dry = "--dry-run" in args
    if dry:
        args.remove("--dry-run")
    part = 1
    if "--part" in args:
        i = args.index("--part")
        part = int(args[i + 1]) if i + 1 < len(args) and args[i + 1] in ("1", "2") else 0
        del args[i:i + 2]
    if len(args) != 2 or part not in (1, 2):
        print(__doc__, file=sys.stderr)
        return 2
    camp, cand = Path(args[0]).resolve(), args[1]
    runner = (Part1Runner if part == 1 else Part2Runner)(camp, cand)
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
