#!/usr/bin/env python3
"""Per-child conformance gate for the v0.7.0 re-qualification.

Every collector of the re-qualification calls ``Gate.before`` immediately
before a measured child and ``Gate.after`` immediately after it
(``run_v070r_collect.py``). The gate relies on the allow-list monitor
(``conformance_monitor.py``), which must already be running.

``before(label)`` passes only if:
- a stop has not been recorded already (``gate-stop.json``);
- the monitor process is alive, its status is younger than ``MAX_HEARTBEAT_AGE_S``,
  and its totals of violations, HID resets and HID read failures are zero;
- a fresh classification of the process table finds nothing forbidden;
- the HID idle time shows no input since the previous gate check;
- AC power, and no recorded thermal or performance warning.

``after(label, start, end)``:
- reads the monitor log written since the previous check;
- requires heartbeats covering [start, end] with no gap above
  ``MAX_HEARTBEAT_GAP_S`` (including from ``start`` to the first heartbeat
  and from the last heartbeat to ``end``);
- requires no forbidden process and no HID reset in that window, and zero
  monitor totals.

It records, for the child, the CPU seconds consumed by every non-campaign
class (``system``, ``baseline``, ``forbidden``) from cumulative ``ps`` CPU
time. This is disclosure, not a threshold.

**Outcome (declared protocol §4):** any failed check makes the whole attempt
NONCONFORMING.
- A failure found by ``before`` raises ``GateStop`` before the child starts.
- A failure found by ``after`` is recorded in ``gate-stop.json`` without
  interrupting the collector, so the completed observation is still saved.
  The next ``before`` raises ``GateStop``, and the chain checks
  ``gate-stop.json`` after every step.

Nothing is excluded or re-classified after the fact.
``GateStop`` derives from ``SystemExit``, so collectors that catch
``Exception`` cannot swallow it.

Environment (set by the chain): ``KNOTREL_GATE_DIR`` (directory holding
``policy.json``, ``monitor-status.json``, ``activity-monitor.jsonl``; the gate
writes ``gate-log.jsonl`` and ``gate-stop.json`` there).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import conformance_monitor as cm  # noqa: E402

MAX_HEARTBEAT_AGE_S = 1.0
MAX_HEARTBEAT_GAP_S = 1.0
HID_TOLERANCE_S = cm.HID_TOLERANCE_S


class GateStop(SystemExit):
    """Raised to stop the collector; the attempt is NONCONFORMING."""


def host_power_ok() -> Optional[str]:
    batt = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, env=cm.C_ENV).stdout
    first = batt.splitlines()[0] if batt.strip() else ""
    if "AC Power" not in first:
        return f"not on AC power: {batt.strip()[:200]}"
    therm = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True, env=cm.C_ENV).stdout
    for needle in ("No thermal warning level has been recorded", "No performance warning level has been recorded"):
        if needle not in therm:
            return f"thermal or performance warning: {therm.strip()[:300]}"
    return None


class Gate:
    """Gate state for one collector process."""

    def __init__(self, directory: Path,
                 snapshot: Callable[[], List[cm.Proc]] = cm.snapshot,
                 hid: Callable[[], Tuple[Optional[float], float]] = cm.hid_read,
                 foreground: Callable[[], Dict[int, str]] = cm.foreground_pids,
                 power: Callable[[], Optional[str]] = host_power_ok,
                 alive: Callable[[int], bool] = cm.pid_alive,
                 clock: Callable[[], float] = time.time):
        self.dir = directory
        self.policy = cm.Policy.load(directory / "policy.json")
        self.status_path = directory / "monitor-status.json"
        self.log_path = directory / "activity-monitor.jsonl"
        self.stop_path = directory / "gate-stop.json"
        self.gate_log = directory / "gate-log.jsonl"
        self.snapshot, self.hid, self.power, self.alive, self.clock = snapshot, hid, power, alive, clock
        self.foreground = foreground
        self.offset = 0
        self.last_hid: Optional[tuple] = None
        self.cpu_before: Dict[int, tuple] = {}
        self.counter = 0

    # -- helpers ---------------------------------------------------------------
    def _record(self, row: Dict[str, object]) -> None:
        with open(self.gate_log, "a") as handle:
            handle.write(json.dumps(row) + "\n")

    def _stop(self, label: str, phase: str, reasons: List[str]) -> None:
        record = {"utc": cm.utc(self.clock()), "label": label, "phase": phase, "reasons": reasons,
                  "pid": os.getpid()}
        if not self.stop_path.exists():
            cm.write_atomic(self.stop_path, record)
        self._record({"kind": "stop", **record})

    def _status(self) -> Dict[str, object]:
        return json.loads(self.status_path.read_text())

    def _check_status(self, reasons: List[str]) -> None:
        try:
            status = self._status()
        except (OSError, ValueError) as error:
            reasons.append(f"monitor status unreadable: {error}")
            return
        if not self.alive(int(status["pid"])):
            reasons.append(f"monitor process {status['pid']} not alive")
        age = self.clock() - float(status["t"])
        if age > MAX_HEARTBEAT_AGE_S:
            reasons.append(f"monitor heartbeat {age:.2f} s old")
        for key in ("violations_total", "hid_resets_total", "hid_failures", "foreground_failures"):
            if status.get(key):
                reasons.append(f"monitor {key} = {status[key]} (last violation: {status.get('last_violation')})")

    def _cpu(self, procs: List[cm.Proc]) -> Dict[int, tuple]:
        classes = dict((p.pid, c) for p, c in cm.classify(procs, self.policy))
        return {p.pid: (classes[p.pid], p.cputime_s, p.path or p.comm) for p in procs if classes[p.pid] != "campaign"}

    # -- gate ------------------------------------------------------------------
    def before(self, label: str) -> None:
        self.counter += 1
        reasons: List[str] = []
        if self.stop_path.exists():
            reasons.append(f"stop already recorded: {self.stop_path.read_text()[:300]}")
        self._check_status(reasons)
        procs = self.snapshot()
        try:
            fg = self.foreground()
        except cm.ForegroundUnavailable as error:
            fg = {}
            reasons.append(f"foreground apps unavailable: {error}")
        found = cm.forbidden(procs, self.policy, self.alive, fg)
        if found:
            reasons.append(f"forbidden processes: {found[:5]}")
        idle, mono = self.hid()
        if idle is None:
            reasons.append("HID idle time unreadable")
        elif self.last_hid is not None and cm.hid_reset(self.last_hid[0], self.last_hid[1], idle, mono, HID_TOLERANCE_S):
            reasons.append(f"user input since the previous check (HID idle {idle:.2f} s)")
        if idle is not None:
            self.last_hid = (idle, mono)
        power = self.power()
        if power:
            reasons.append(power)
        if reasons:
            self._stop(label, "before", reasons)
            raise GateStop(f"conformance gate before {label}: {'; '.join(reasons)[:800]}")
        self.cpu_before = self._cpu(procs)

    def wait_for_heartbeat(self, end: float, poll_s: float = 0.02) -> None:
        """Wait (at most ``MAX_HEARTBEAT_GAP_S``) for the first monitor heartbeat after ``end``."""
        deadline = time.time() + MAX_HEARTBEAT_GAP_S
        while time.time() < deadline:
            try:
                if float(self._status()["t"]) >= end:
                    return
            except (OSError, ValueError, KeyError):
                pass
            time.sleep(poll_s)

    def _read_log(self) -> List[Dict[str, object]]:
        rows = []
        with open(self.log_path) as handle:
            handle.seek(self.offset)
            data = handle.read()
        complete = data[: data.rfind("\n") + 1]
        self.offset += len(complete.encode())
        for line in complete.splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows

    def after(self, label: str, start: float, end: float) -> bool:
        """Check the child's interval; record a stop (no raise) if it fails."""
        reasons: List[str] = []
        try:
            rows = self._read_log()
        except (OSError, ValueError) as error:
            rows = []
            reasons.append(f"monitor log unreadable: {error}")
        beats = sorted(float(r["t"]) for r in rows if r.get("k") == "s")
        inside = [t for t in beats if start - MAX_HEARTBEAT_GAP_S <= t <= end + MAX_HEARTBEAT_GAP_S]
        if not any(t <= start + MAX_HEARTBEAT_GAP_S for t in inside):
            reasons.append("no heartbeat at the child's start")
        if not any(t >= end for t in inside):
            reasons.append("no heartbeat after the child ended")
        points = [start] + [t for t in inside if start < t < end] + [end]
        gaps = [b - a for a, b in zip(points, points[1:])]
        if max(gaps) > MAX_HEARTBEAT_GAP_S:
            reasons.append(f"monitor heartbeat gap {max(gaps):.2f} s inside the child")
        violations = [r for r in rows if r.get("k") == "s" and r.get("v")
                      and start - MAX_HEARTBEAT_GAP_S <= float(r["t"]) <= end + MAX_HEARTBEAT_GAP_S]
        if violations:
            reasons.append(f"forbidden processes during the child: {violations[0]['v'][:5]}")
        resets = [r for r in rows if r.get("k") == "h" and r.get("reset")]
        if resets:
            reasons.append(f"user input during or before the child at t={resets[0]['t']}")
        self._check_status(reasons)
        cpu: Optional[Dict[str, float]] = None
        if self.cpu_before:  # only after a before(): the quiet-period check has no baseline
            cpu = {}
            for pid, (cls, seconds, _) in self._cpu(self.snapshot()).items():
                prior = self.cpu_before.get(pid)
                if prior is None:
                    used = seconds  # started during the child
                elif prior[0] == cls:
                    used = seconds - prior[1]
                else:
                    used = 0.0  # PID reused with another class: not attributable
                cpu[cls] = round(cpu.get(cls, 0.0) + max(0.0, used), 3)
            self.cpu_before = {}
        self._record({"kind": "child", "label": label, "start": round(start, 3), "end": round(end, 3),
                      "heartbeats": len([t for t in inside if start <= t <= end]),
                      "max_gap_s": round(max(gaps), 3),
                      "cpu_seconds_by_class": cpu, "conforming": not reasons, "reasons": reasons})
        if reasons:
            self._stop(label, "after", reasons)
            return False
        return True


    def full_log_check(self, start: float, end: float) -> List[str]:
        """Whole-attempt checks at chain end: monitor alive and fresh, zero totals, no gap anywhere."""
        reasons: List[str] = []
        self._check_status(reasons)
        text = self.log_path.read_text()
        rows = [json.loads(line) for line in text[: text.rfind("\n") + 1].splitlines() if line.strip()]
        beats = sorted(float(r["t"]) for r in rows if r.get("k") == "s" and start <= float(r["t"]) <= end)
        points = [start] + beats + [end]
        gaps = [b - a for a, b in zip(points, points[1:])]
        if max(gaps) > MAX_HEARTBEAT_GAP_S:
            reasons.append(f"monitor heartbeat gap {max(gaps):.2f} s between {start} and {end}")
        if any(r.get("k") == "s" and r.get("v") for r in rows):
            reasons.append("forbidden processes recorded in the monitor log")
        if any(r.get("k") == "h" and r.get("reset") for r in rows):
            reasons.append("user input recorded in the monitor log")
        if any(r.get("k") == "h" and r.get("idle") is None for r in rows):
            reasons.append("HID read failure recorded in the monitor log")
        return reasons


def gated_counts(directory: Path) -> Dict[str, int]:
    """Conforming child records in ``gate-log.jsonl`` per label prefix (``A``, ``BC``, ``r``…)."""
    counts: Dict[str, int] = {}
    path = directory / "gate-log.jsonl"
    if path.exists():
        for line in path.read_text().splitlines():
            row = json.loads(line)
            if row.get("kind") == "child" and row.get("conforming") and row.get("label") != "quiet-period":
                prefix = str(row["label"]).split(":", 1)[0]
                counts[prefix] = counts.get(prefix, 0) + 1
    return counts


def collector_counts(camp: Path) -> Dict[str, int]:
    """Children each collector recorded itself (independent of the gate)."""
    counts: Dict[str, int] = {}
    observations = 0
    for pattern in ("A/raw-main/pair_*.json", "A/extension/raw-extension/pair_*.json"):
        for pair in camp.glob(pattern):
            observations += len(json.loads(pair.read_text()).get("observations", []))
    counts["A"] = observations
    bc = camp / "BC" / "run-log.jsonl"
    counts["BC"] = len(bc.read_text().splitlines()) if bc.exists() else 0
    for prefix, name in (("r", "R"), ("rmem", "Rmem"), ("mdesc", "Mdesc"), ("mreg", "Mreg")):
        log = camp / name / "run-log.json"
        counts[prefix] = len(json.loads(log.read_text())["children"]) if log.exists() else 0
    return counts


def verify_gating(camp: Path, directory: Path) -> List[str]:
    """Every child a collector recorded has exactly one conforming gate record."""
    gated_n, collected = gated_counts(directory), collector_counts(camp)
    return [f"{prefix}: {collected[prefix]} children recorded by the collector, {gated_n.get(prefix, 0)} gated"
            for prefix in collected if collected[prefix] != gated_n.get(prefix, 0)]


_GATE: Optional[Gate] = None


def gate() -> Gate:
    """The process-wide gate, created from ``KNOTREL_GATE_DIR``."""
    global _GATE
    if _GATE is None:
        directory = os.environ.get("KNOTREL_GATE_DIR")
        if not directory:
            raise GateStop("KNOTREL_GATE_DIR is not set: the conformance gate is mandatory")
        _GATE = Gate(Path(directory))
    return _GATE


def gated(label: str, run: Callable[[], object]) -> object:
    """Run one measured child between ``before`` and ``after``."""
    g = gate()
    g.before(label)
    start = time.time()
    try:
        return run()
    finally:
        end = time.time()
        g.wait_for_heartbeat(end)
        g.after(label, start, end)
