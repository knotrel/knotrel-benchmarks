#!/usr/bin/env python3
"""Autonomous runner of v0.7.0 qualification 3, revision 3 (PROTOCOL section 14).

One invocation runs the whole collection; nobody needs to quit applications or stop using the
Mac. Interference is judged by telemetry (``interference_monitor.py``) under the rules of
``interference_gate.py``, not by the presence of processes or user input.

    run_v070q3_autonomous.py CAMP CAND_SHA [--dry-run]

1. **Preflight** (nothing is measured; a failure is NOT STARTED): the campaign directory
   matches the candidate; no output exists yet; every file of the freeze record matches its
   hash in the campaign's tooling clone; every binary matches ``binaries-sha256.txt``; AC power;
   free disk space; no unrestored launcher quiesce from an earlier attempt.
2. **Monitor:** ``caffeinate -dimsu -w <runner>`` holds the power assertions while the runner
   lives; the telemetry monitor starts as the runner's child and must deliver
   ``monitor_check_samples`` samples, including a power/thermal sample, within
   ``monitor_start_s``.
3. **Steps,** in the frozen order: A main, A analysis, A extension (if required), B/C, T5, R,
   Rmem, M_desc, M_reg. Each collector runs with ``KNOTREL_INTERFERENCE_DIR`` and waits on its
   own for acceptable conditions before each unit. An A block whose child is invalid exits 75;
   its output moves to ``invalidated/`` and the block restarts, at most
   ``a_block_restarts`` times.
4. **Limits:** the campaign deadline (``budget_s`` after the start), the wait limit per unit
   and the retries per unit are enforced by the gate and end the campaign with their own
   status. Everything is preserved.
5. **End:** every collector child must have exactly one valid unit record (final blocks
   only); binaries must still match. Then ``logs/CONFORMANCE.txt``, ``SUMMARY.json`` and
   ``SUMMARY.txt`` are written, the monitor and caffeinate stopped, output checksums written.
   This policy quiesces nothing, so nothing needs restoring; the runner re-checks that no
   earlier quiesce is left unrestored. Signals (TERM, INT, HUP) end the current child and run
   the same end path (status INTERRUPTED).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import interference_gate as ig  # noqa: E402

LIMITS = {
    "budget_s": 105 * 60.0,
    "a_block_restarts": 1,
    "monitor_start_s": 20.0,
    "monitor_check_samples": 6,
    "min_free_bytes": 3 * 1024 ** 3,
}
Q3 = "results/v0.7.0-qualification-3"
OUTPUTS = ("A/raw-main", "A/extension", "BC", "T5", "R", "Rmem", "Mdesc", "Mreg", "gate")
EXIT_STATUS = {ig.EXIT_BLOCKED: "BLOCKED", ig.EXIT_BUDGET: "BUDGET EXHAUSTED", ig.EXIT_MONITOR: "MONITOR LOST",
               ig.EXIT_RECOVERY: "RECOVERY EXHAUSTED"}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


class Stop(Exception):
    def __init__(self, status: str, cause: str):
        super().__init__(f"{status}: {cause}")
        self.status, self.cause = status, cause


class Runner:
    def __init__(self, camp: Path, cand: str, limits: Optional[Dict[str, float]] = None,
                 clock=time.time, python: str = sys.executable):
        self.camp, self.cand = camp, cand
        self.limits = dict(LIMITS if limits is None else limits)
        self.clock, self.python = clock, python
        self.bench = camp / "src" / "cand" / "knotrel-benchmarks"
        self.targets = camp / "targets"
        self.gate_dir = camp / "gate"
        self.logs = camp / "logs"
        self.steps: List[Dict[str, Any]] = []
        self.monitor: Optional[subprocess.Popen] = None
        self.caffeinate: Optional[subprocess.Popen] = None
        self.child: Optional[subprocess.Popen] = None
        self.started = clock()
        self.status, self.cause = "INCOMPLETE", "runner ended before its last step"

    # -- logging ---------------------------------------------------------------
    def stamp(self, step: str, what: str) -> None:
        with open(self.logs / "chain-steps.txt", "a") as handle:
            handle.write(f"{step} {utc()} {what}\n")

    # -- preflight -------------------------------------------------------------
    def preflight(self) -> None:
        name = self.camp.name
        if f"-{self.cand[:7]}-" not in name:
            raise Stop("NOT STARTED", f"candidate {self.cand} does not match {name}")
        for out in OUTPUTS:
            if (self.camp / out).exists():
                raise Stop("NOT STARTED", f"output already exists: {out}")
        freeze = json.loads((self.bench / Q3 / "FREEZE.json").read_text())
        if freeze.get("revision") != 3:
            raise Stop("NOT STARTED", f"freeze revision {freeze.get('revision')}, expected 3")
        bad = [p for p, h in freeze["file_sha256"].items() if sha256(self.bench / p) != h]
        if bad:
            raise Stop("NOT STARTED", f"frozen files differ: {bad[:5]}")
        self.check_binaries("preflight")
        batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True).stdout
        if "AC Power" not in (batt.splitlines() or [""])[0]:
            raise Stop("NOT STARTED", "not on AC power")
        if shutil.disk_usage(self.camp).free < self.limits["min_free_bytes"]:
            raise Stop("NOT STARTED", "less free disk space than required")
        restored = subprocess.run(["sh", str(self.bench / Q3 / "check_restored.sh")], capture_output=True, text=True)
        if restored.returncode != 0:
            raise Stop("NOT STARTED", f"an earlier launcher quiesce is not restored: {restored.stdout[-300:]}")

    def check_binaries(self, when: str) -> None:
        for line in (self.camp / "binaries-sha256.txt").read_text().splitlines():
            digest, path = line.split(None, 1)
            if sha256(self.camp / path.strip()) != digest:
                raise Stop("NOT STARTED" if when == "preflight" else "FAILED", f"binary changed: {path} ({when})")

    # -- monitor ---------------------------------------------------------------
    def start_monitor(self) -> None:
        self.gate_dir.mkdir()
        (self.gate_dir / "limits.json").write_text(json.dumps({
            "deadline": self.started + self.limits["budget_s"], "limits": self.limits, "rules": ig.RULES}))
        self.caffeinate = subprocess.Popen(["/usr/bin/caffeinate", "-dimsu", "-w", str(os.getpid())])
        self.monitor = subprocess.Popen(
            [self.python, str(SCRIPTS / "interference_monitor.py"), "monitor", "--root", str(os.getpid()),
             "--dir", str(self.gate_dir)], stdout=subprocess.DEVNULL, stderr=open(self.logs / "monitor.stderr", "w"))
        gate = ig.Gate(self.gate_dir)
        deadline = time.time() + self.limits["monitor_start_s"]
        while time.time() < deadline:
            samples = gate.samples()
            if (len(samples) >= self.limits["monitor_check_samples"] and any("ac" in s for s in samples)
                    and not ig.coverage_reasons([s["t"] for s in samples], samples[0]["t"], samples[-1]["t"],
                                                ig.RULES["gap_s"])):
                self.stamp("MONITOR", f"running, {len(samples)} samples")
                return
            if self.monitor.poll() is not None:
                break
            time.sleep(0.5)
        raise Stop("NOT STARTED", "telemetry monitor did not deliver samples")

    # -- steps -----------------------------------------------------------------
    def run_step(self, name: str, argv: List[str], block: str, restartable_dirs: List[Path] = ()) -> None:
        restarts = 0
        while True:
            env = {**os.environ, "KNOTREL_INTERFERENCE_DIR": str(self.gate_dir),
                   "KNOTREL_BLOCK": f"{block}#{restarts}",
                   "LIFECYCLE_QUALIFICATION_ROOTS": os.environ.get("LIFECYCLE_QUALIFICATION_ROOTS",
                                                                   str(self.camp.parent))}
            env.pop("KNOTREL_GATE_DIR", None)
            self.stamp(name, f"start (block {block}#{restarts})")
            began = self.clock()
            with open(self.logs / f"{name}.log", "a") as log:
                self.child = subprocess.Popen(argv, cwd=self.bench, env=env, stdout=log, stderr=subprocess.STDOUT)
                code = self.child.wait()
                self.child = None
            self.steps.append({"step": name, "block": f"{block}#{restarts}", "exit": code,
                               "seconds": round(self.clock() - began, 1)})
            if code == 0:
                self.stamp(name, "end")
                return
            if code == ig.EXIT_BLOCK_INVALID and restarts < self.limits["a_block_restarts"]:
                restarts += 1
                for directory in restartable_dirs:
                    if directory.exists():
                        target = self.camp / "invalidated" / f"{directory.name}.{restarts}"
                        target.parent.mkdir(exist_ok=True)
                        shutil.move(str(directory), str(target))
                self.stamp(name, f"block invalid, restart {restarts}")
                continue
            if code == ig.EXIT_BLOCK_INVALID:
                raise Stop("RECOVERY EXHAUSTED", f"{name}: block invalid after {restarts} restart(s)")
            if code in EXIT_STATUS:
                raise Stop(EXIT_STATUS[code], f"{name}: {self.last_gate_reason()}")
            raise Stop("FAILED", f"{name} exited {code} (logs/{name}.log)")

    def last_gate_reason(self) -> str:
        units = self.gate_dir / "units.jsonl"
        if units.exists():
            rows = [json.loads(line) for line in units.read_text().splitlines() if line.strip()]
            if rows:
                last = rows[-1]
                return f"{last.get('label') or last.get('unit')}: {'; '.join(last.get('reasons', []))}"
        return "see the step log"

    def collect(self, experiment: str, *args: str) -> List[str]:
        return [self.python, "scripts/run_v070q3_collect.py", experiment, *args]

    def sequence(self) -> None:
        a, t = self.camp / "A", self.targets
        manifest = "/Users/rt/workspace/knotrel/evidence/p0-coverage-increment-1-plan-20261030/manifest.json"
        self.run_step("A-main", self.collect("a", "--manifest", str(a / "plan/manifest.json"), "--schedule",
                                             str(a / "plan/schedule.json"), "--execute", str(a / "raw-main")),
                      "A-main", [a / "raw-main"])
        self.analysis("A-analysis", ["scripts/analyze_bc_qualification.py", "--main", str(a / "raw-main"),
                                     "--rules", "v0.4.0", "--output", str(a / "decision-analysis-main.json")])
        cells = json.loads((a / "decision-analysis-main.json").read_text())["extension_cells_required"]
        if cells:
            self.analysis("A-extension-plan", ["scripts/prepare_bc_qualification.py", str(a / "extension/plan"),
                                               "--identities", str(a / "identities.json"), "--source-manifest",
                                               manifest, "--phase", "extension", "--cells", *cells,
                                               "--checkpoint", "v0.7.0-Qualification3-A-Extension",
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
            "--window-multipliers", f"{Q3}/window-multipliers-q3.json"), "BC")
        self.run_step("T5", [self.python, "scripts/run_v070q3_t5.py", "--out", str(self.camp / "T5"), "--base",
                             str(t / "t1base-probes/release/core-lifecycle"), "--cand",
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

    def analysis(self, name: str, argv: List[str]) -> None:
        self.stamp(name, "start")
        with open(self.logs / f"{name}.log", "a") as log:
            code = subprocess.run([self.python, *argv], cwd=self.bench, stdout=log, stderr=subprocess.STDOUT).returncode
        if code != 0:
            raise Stop("FAILED", f"{name} exited {code} (logs/{name}.log)")
        self.stamp(name, "end")

    # -- end -------------------------------------------------------------------
    def end_checks(self) -> None:
        import conformance_gate as cg
        collected, valid = cg.collector_counts(self.camp), ig.valid_children(self.gate_dir)
        mismatch = {k: (collected[k], valid.get(k, 0)) for k in collected if collected[k] != valid.get(k, 0)}
        if mismatch:
            raise Stop("FAILED", f"children without exactly one valid unit record (collected, valid): {mismatch}")
        self.check_binaries("end")

    def summary(self) -> Dict[str, Any]:
        rows = []
        units = self.gate_dir / "units.jsonl"
        if units.exists():
            rows = [json.loads(line) for line in units.read_text().splitlines() if line.strip()]
        samples = ig.Gate(self.gate_dir).samples() if (self.gate_dir / "telemetry.jsonl").exists() else []
        invalid = [r for r in rows if r.get("kind") == "unit" and not r["valid"]]
        waits = [r for r in rows if r.get("kind") == "wait"]
        ext = sorted(s["ext_cpu"] for s in samples)
        idle = [s["hid_idle"] for s in samples if s.get("hid_idle") is not None]
        inputs = sum(1 for a, b in zip(idle, idle[1:]) if b < a)
        top: Dict[str, float] = {}
        for s in samples:
            for name, cores in s.get("top", []):
                top[name] = top.get(name, 0.0) + cores * s.get("span_s", 1.0)
        return {
            "status": self.status, "cause": self.cause, "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.started)),
            "ended_utc": utc(), "duration_min": round((self.clock() - self.started) / 60, 1),
            "limits": self.limits, "rules": ig.RULES, "steps": self.steps,
            "units": sum(1 for r in rows if r.get("kind") == "unit"),
            "invalidated_units": [{k: r[k] for k in ("block", "unit", "attempt", "reasons")} for r in invalid],
            "waits": {"count": len(waits), "total_s": round(sum(w["seconds"] for w in waits), 1),
                      "longest_s": round(max((w["seconds"] for w in waits), default=0.0), 1),
                      "reasons": [w["reasons"][:2] for w in sorted(waits, key=lambda w: -w["seconds"])[:5]]},
            "telemetry": {"samples": len(samples),
                          "ext_cpu_cores": ({"p50": ext[len(ext) // 2], "p99": ext[int(0.99 * (len(ext) - 1))],
                                             "max": ext[-1]} if ext else None),
                          "context_user_inputs": inputs,
                          "context_top_external_cpu_s": dict(sorted(top.items(), key=lambda kv: -kv[1])[:8])},
        }

    def finish(self) -> None:
        for proc in (self.child,):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    proc.kill()
        if self.monitor is not None and self.monitor.poll() is None:
            self.monitor.terminate()
            try:
                self.monitor.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.monitor.kill()
        if self.caffeinate is not None and self.caffeinate.poll() is None:
            self.caffeinate.terminate()
        summary = self.summary()
        (self.camp / "SUMMARY.json").write_text(json.dumps(summary, indent=1))
        lines = [f"{summary['status']}: {summary['cause']}",
                 f"duration {summary['duration_min']} min (budget {self.limits['budget_s'] / 60:.0f} min)",
                 f"units {summary['units']}, invalidated {len(summary['invalidated_units'])}, waits "
                 f"{summary['waits']['count']} ({summary['waits']['total_s']} s, longest {summary['waits']['longest_s']} s)"]
        lines += [f"  invalidated {u['unit']} attempt {u['attempt']}: {'; '.join(u['reasons'])}" for u in summary["invalidated_units"]]
        lines += [f"  step {s['step']} {s['block']} exit {s['exit']} {s['seconds']} s" for s in self.steps]
        (self.camp / "SUMMARY.txt").write_text("\n".join(lines) + "\n")
        (self.logs / "CONFORMANCE.txt").write_text(f"{self.status}: {self.cause}\n")
        restored = subprocess.run(["sh", str(self.bench / Q3 / "check_restored.sh")], capture_output=True, text=True)
        self.stamp("RESTORE", "nothing quiesced by this policy; earlier quiesce state "
                   + ("restored" if restored.returncode == 0 else "NOT restored (see check_restored.sh)"))
        found = []
        for out in OUTPUTS + ("invalidated",):
            base = self.camp / out
            if base.exists():
                found += [p for p in sorted(base.rglob("*")) if p.is_file()]
        with open(self.logs / "outputs-sha256.txt", "w") as handle:
            for p in found:
                handle.write(f"{sha256(p)}  {p.relative_to(self.camp)}\n")
        print("\n".join(lines[:3]))

    def run(self) -> int:
        def interrupted(signum: int, _frame: Any) -> None:
            raise Stop("INTERRUPTED", f"signal {signum}")

        for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
            signal.signal(sig, interrupted)
        self.logs.mkdir(exist_ok=True)
        try:
            self.preflight()
            self.stamp("PREFLIGHT", "ok")
            self.start_monitor()
            self.sequence()
            self.end_checks()
            self.status, self.cause = "CONFORMING", "every unit valid under the revision-3 policy; counts and binaries verified"
        except Stop as stop:
            self.status, self.cause = stop.status, stop.cause
            self.stamp(stop.status, stop.cause)
        except Exception as error:  # noqa: BLE001 - any failure still runs the end path
            self.status, self.cause = "FAILED", f"runner error: {error!r}"
            self.stamp("FAILED", self.cause)
        finally:
            for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                signal.signal(sig, signal.SIG_IGN)
            if self.status != "NOT STARTED" or (self.gate_dir.exists()):
                self.finish()
            else:
                (self.logs / "PREFLIGHT-REFUSED.txt").write_text(f"{self.status}: {self.cause}\n")
                print(f"{self.status}: {self.cause}")
        return 0 if self.status == "CONFORMING" else 1


def main() -> int:
    if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != "--dry-run"):
        print(__doc__, file=sys.stderr)
        return 2
    camp, cand = Path(sys.argv[1]).resolve(), sys.argv[2]
    runner = Runner(camp, cand)
    if len(sys.argv) == 4:
        runner.logs.mkdir(exist_ok=True)
        try:
            runner.preflight()
        except Stop as stop:
            print(f"DRY-RUN {stop.status}: {stop.cause}")
            return 1
        print("DRY-RUN PREFLIGHT OK")
        return 0
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
