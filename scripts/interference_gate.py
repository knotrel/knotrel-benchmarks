#!/usr/bin/env python3
"""Proportional interference gate (qualification 3, revision 3; PROTOCOL section 14).

Collectors run each **unit** (the smallest group of children whose results must be judged
together) through :meth:`Gate.run_unit`:

1. **Before the unit** :meth:`Gate.ready` waits until the host is acceptable (rule ``ready``
   below). It never waits inside a unit: no timed child is suspended or resumed.
2. The unit's children run; each child's start and end are taken with ``time.time()``, the
   clock of the telemetry samples.
3. **After the unit** :meth:`Gate.assess` waits for a telemetry sample at least
   ``after_s`` after the end (same clock, exact values) and judges the unit's interval
   (rule ``invalid``).
4. A valid unit is kept. An invalid unit is recorded with its reasons; the collector preserves
   its outputs as invalidated, and the **whole unit** is repeated, at most ``retries`` times.
   Then :class:`RecoveryExhausted` stops the campaign (the result stays inconclusive).

Validity depends only on telemetry and these rules, never on a measured value.

Rules (``RULES``; the same values are frozen in MATRIX ``conformance.qualification_3.revision_3``):
- **ready:** the latest sample is at most ``status_age_s`` old; at least ``ready_window_s`` of
  samples with no gap above ``gap_s``; over that window: mean external CPU <=
  ``ready_cpu`` cores, the trailing ``invalid_window_s`` mean <= ``invalid_cpu``, memory
  pressure level <= ``pressure_max`` in every sample, no sleep, and in the latest slow sample
  AC power and no thermal warning.
- **invalid:** in the interval [start - gap_s, end + after_s]: a gap between samples above
  ``gap_s`` (or none at the ends), any sample whose trailing ``invalid_window_s`` mean
  external CPU exceeds ``invalid_cpu``, memory pressure above ``pressure_max``, a sleep
  (``sleep_s`` > ``sleep_jump_s``), or a slow sample showing battery power or a thermal
  warning.
- **limits:** a wait longer than ``wait_limit_s`` raises :class:`Blocked` ("blocked by
  sustained host load"); passing the campaign deadline raises :class:`BudgetExhausted`;
  a monitor whose status is older than ``status_age_s`` for ``monitor_lost_s`` raises
  :class:`MonitorLost`. Each is a ``SystemExit`` with its own code, so the runner can state
  the cause.

Records go to ``DIR/units.jsonl``: one line per unit attempt and per wait.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

RULES: Dict[str, float] = {
    "sample_s": 1.0,
    "gap_s": 2.5,
    "status_age_s": 3.0,
    "monitor_lost_s": 30.0,
    "after_s": 1.0,
    "after_wait_s": 10.0,
    "invalid_window_s": 10.0,
    "invalid_cpu": 1.5,
    "ready_window_s": 30.0,
    "ready_cpu": 0.6,
    "pressure_max": 1,
    "sleep_jump_s": 2.0,
    "wait_limit_s": 600.0,
    "retries": 2,
}

EXIT_BLOCKED, EXIT_BUDGET, EXIT_MONITOR, EXIT_RECOVERY, EXIT_BLOCK_INVALID = 77, 76, 78, 79, 75


class Blocked(SystemExit):
    def __init__(self, reason: str):
        super().__init__(EXIT_BLOCKED)
        self.reason = reason


class BudgetExhausted(SystemExit):
    def __init__(self, reason: str):
        super().__init__(EXIT_BUDGET)
        self.reason = reason


class MonitorLost(SystemExit):
    def __init__(self, reason: str):
        super().__init__(EXIT_MONITOR)
        self.reason = reason


class RecoveryExhausted(SystemExit):
    def __init__(self, reason: str):
        super().__init__(EXIT_RECOVERY)
        self.reason = reason


class BlockInvalid(SystemExit):
    """A child of a block-level unit (experiment A) is invalid: the runner restarts the block."""

    def __init__(self, reason: str):
        super().__init__(EXIT_BLOCK_INVALID)
        self.reason = reason


def trailing_mean(samples: Sequence[Dict[str, Any]], index: int, window: float) -> float:
    """Mean ``ext_cpu`` of the samples in (t - window, t] for sample ``index``."""
    t = samples[index]["t"]
    values = [s["ext_cpu"] for s in samples[: index + 1] if s["t"] > t - window]
    return sum(values) / len(values)


def coverage_reasons(beats: Sequence[float], start: float, end: float, gap: float) -> List[str]:
    """Heartbeat coverage of [start, end]: a beat at or before start + gap, one at or after
    ``end`` (exact comparison, same clock), and no gap above ``gap`` in between."""
    reasons = []
    inside = sorted(t for t in beats if start - gap <= t)
    if not any(t <= start + gap for t in inside):
        reasons.append("no telemetry at the unit's start")
    if not any(t >= end for t in inside):
        reasons.append("no telemetry after the unit ended")
    points = [start] + [t for t in inside if start < t < end] + [end]
    worst = max(b - a for a, b in zip(points, points[1:]))
    if worst > gap:
        reasons.append(f"telemetry gap {worst:.2f} s inside the unit")
    return reasons


def slow_sample_reasons(sample: Dict[str, Any]) -> List[str]:
    reasons = []
    if "ac" in sample and sample["ac"] is not True:
        reasons.append("not on AC power" if sample["ac"] is False else "AC power unreadable")
    if "therm" in sample and sample["therm"] != "ok":
        reasons.append(f"thermal: {sample['therm']}")
    return reasons


def judge(samples: Sequence[Dict[str, Any]], start: float, end: float,
          rules: Dict[str, float] = RULES) -> List[str]:
    """Reasons that make the unit [start, end] invalid (empty: valid)."""
    reasons = coverage_reasons([s["t"] for s in samples], start, end, rules["gap_s"])
    lo, hi = start - rules["gap_s"], end + rules["after_s"]
    for i, s in enumerate(samples):
        if not lo <= s["t"] <= hi:
            continue
        mean = trailing_mean(samples, i, rules["invalid_window_s"])
        if mean > rules["invalid_cpu"]:
            top = ", ".join(f"{n} {c:.2f}" for n, c in s.get("top", []))
            reasons.append(f"external CPU {mean:.2f} cores over {rules['invalid_window_s']:.0f} s > "
                           f"{rules['invalid_cpu']} (busiest: {top})")
        if s.get("pressure") is None or s["pressure"] > rules["pressure_max"]:
            reasons.append(f"memory pressure level {s.get('pressure')}")
        if s.get("sleep_s", 0) > rules["sleep_jump_s"]:
            reasons.append(f"system sleep of {s['sleep_s']:.1f} s")
        reasons += slow_sample_reasons(s)
    seen, unique = set(), []
    for r in reasons:  # keep the first occurrence of each kind, in order
        key = r.split(" ")[0] + r.split(" ")[1] if " " in r else r
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def ready_reasons(samples: Sequence[Dict[str, Any]], now: float, rules: Dict[str, float] = RULES) -> List[str]:
    """Reasons to keep waiting before a unit (empty: start now)."""
    if not samples or now - samples[-1]["t"] > rules["status_age_s"]:
        return ["telemetry not current"]
    window = [s for s in samples if s["t"] > now - rules["ready_window_s"]]
    beats = [s["t"] for s in window]
    if not beats or beats[0] > now - rules["ready_window_s"] + rules["gap_s"]:
        return [f"less than {rules['ready_window_s']:.0f} s of telemetry"]
    reasons = []
    gaps = [b - a for a, b in zip(beats, beats[1:])]
    if gaps and max(gaps) > rules["gap_s"]:
        reasons.append(f"telemetry gap {max(gaps):.1f} s in the last {rules['ready_window_s']:.0f} s")
    mean = sum(s["ext_cpu"] for s in window) / len(window)
    if mean > rules["ready_cpu"]:
        top = ", ".join(f"{n} {c:.2f}" for n, c in window[-1].get("top", []))
        reasons.append(f"external CPU {mean:.2f} cores over {rules['ready_window_s']:.0f} s > {rules['ready_cpu']} "
                       f"(busiest now: {top})")
    recent = trailing_mean(samples, len(samples) - 1, rules["invalid_window_s"])
    if recent > rules["invalid_cpu"]:
        reasons.append(f"external CPU {recent:.2f} cores over {rules['invalid_window_s']:.0f} s > {rules['invalid_cpu']}")
    if any(s.get("pressure") is None or s["pressure"] > rules["pressure_max"] for s in window):
        reasons.append("memory pressure above normal")
    if any(s.get("sleep_s", 0) > rules["sleep_jump_s"] for s in window):
        reasons.append("system sleep in the window")
    slow = [s for s in samples if "ac" in s]
    if not slow:
        reasons.append("no power/thermal sample yet")
    else:
        reasons += slow_sample_reasons(slow[-1])
    return reasons


class Gate:
    """Gate of one collector process, reading the monitor's files in ``directory``."""

    def __init__(self, directory: Path, clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep, rules: Optional[Dict[str, float]] = None,
                 alive: Optional[Callable[[int], bool]] = None):
        self.dir = Path(directory)
        self.clock, self.sleep = clock, sleep
        self.rules = dict(RULES if rules is None else rules)
        self.alive = alive or _alive
        self.log_path = self.dir / "telemetry.jsonl"
        self.status_path = self.dir / "monitor-status.json"
        self.units_path = self.dir / "units.jsonl"
        self.block = os.environ.get("KNOTREL_BLOCK", "")
        self._samples: List[Dict[str, Any]] = []
        self._offset = 0
        self._children: Optional[List[Tuple[str, float, float]]] = None
        limits = self.dir / "limits.json"
        self.deadline = json.loads(limits.read_text())["deadline"] if limits.exists() else float("inf")

    # -- telemetry -------------------------------------------------------------
    def samples(self) -> List[Dict[str, Any]]:
        if self.log_path.exists():
            with open(self.log_path, "rb") as handle:
                handle.seek(self._offset)
                data = handle.read()
            complete = data[: data.rfind(b"\n") + 1]
            self._offset += len(complete)
            for line in complete.decode().splitlines():
                if line.strip():
                    row = json.loads(line)
                    if row.get("k") == "s":
                        self._samples.append(row)
        return self._samples

    def _check_monitor(self, since: float) -> None:
        """Raise MonitorLost when the monitor is dead or silent for ``monitor_lost_s``."""
        try:
            status = json.loads(self.status_path.read_text())
            pid, t = int(status["pid"]), float(status["t"])
        except (OSError, ValueError, KeyError):
            pid, t = 0, 0.0
        now = self.clock()
        if (pid and not self.alive(pid)) or (now - t > self.rules["status_age_s"]
                                             and now - since > self.rules["monitor_lost_s"]):
            raise MonitorLost(f"telemetry monitor {'gone' if pid and not self.alive(pid) else 'silent'} "
                              f"(last sample {now - t:.1f} s ago)")

    def record(self, row: Dict[str, Any]) -> None:
        row = {"block": self.block, **row}
        with open(self.units_path, "a") as handle:
            handle.write(json.dumps(row) + "\n")

    # -- rules -----------------------------------------------------------------
    def ready(self, label: str) -> float:
        """Wait until the host is acceptable; returns the seconds waited."""
        began = self.clock()
        last_reasons: List[str] = []
        while True:
            now = self.clock()
            if now > self.deadline:
                raise BudgetExhausted(f"campaign duration budget exhausted before {label}")
            self._check_monitor(began)
            reasons = ready_reasons(self.samples(), now, self.rules)
            if not reasons:
                waited = now - began
                if waited >= self.rules["sample_s"] * 2:
                    self.record({"kind": "wait", "label": label, "start": began, "end": now,
                                 "seconds": waited, "reasons": last_reasons})
                return waited
            last_reasons = reasons
            if now - began > self.rules["wait_limit_s"]:
                self.record({"kind": "wait", "label": label, "start": began, "end": now,
                             "seconds": now - began, "reasons": reasons, "blocked": True})
                raise Blocked(f"blocked by sustained host load before {label}: {'; '.join(reasons)}")
            self.sleep(self.rules["sample_s"])

    def assess(self, start: float, end: float) -> List[str]:
        """Wait for telemetry past ``end + after_s`` and judge [start, end]."""
        target = end + self.rules["after_s"]
        waited_from = self.clock()
        while not self.samples() or self.samples()[-1]["t"] < target:
            if self.clock() - waited_from > self.rules["after_wait_s"]:
                self._check_monitor(waited_from - self.rules["monitor_lost_s"])
                return judge(self.samples(), start, end, self.rules) + ["telemetry did not reach the unit's end"]
            self.sleep(0.05)
        return judge(self.samples(), start, end, self.rules)

    # -- units -----------------------------------------------------------------
    def child(self, label: str, run: Callable[[], Any]) -> Any:
        """Run one child, recording its interval on the current unit."""
        start = self.clock()
        try:
            return run()
        finally:
            if self._children is not None:
                self._children.append((label, start, self.clock()))

    @property
    def in_unit(self) -> bool:
        return self._children is not None

    def run_unit(self, unit: str, run: Callable[[], Any],
                 preserve: Callable[[int, List[str]], None] = lambda attempt, reasons: None) -> Any:
        """Run ``run`` (all children of the unit) until one attempt is valid."""
        for attempt in range(int(self.rules["retries"]) + 1):
            waited = self.ready(unit)
            self._children = []
            try:
                result = run()
                children = self._children
            finally:
                self._children = None
            if not children:
                raise RuntimeError(f"unit {unit} ran no child")
            start, end = children[0][1], children[-1][2]
            reasons = self.assess(start, end)
            self.record({"kind": "unit", "unit": unit, "attempt": attempt, "start": start, "end": end,
                         "waited_s": waited, "children": [c[0] for c in children], "valid": not reasons,
                         "reasons": reasons})
            if not reasons:
                return result
            preserve(attempt, reasons)
        raise RecoveryExhausted(f"unit {unit} invalid after {int(self.rules['retries']) + 1} attempts: "
                                f"{'; '.join(reasons)}")

    def block_child(self, label: str, run: Callable[[], Any]) -> Any:
        """Experiment A: wait before each child; an invalid child invalidates the whole block."""
        waited = self.ready(label)
        start = self.clock()
        result = run()
        end = self.clock()
        reasons = self.assess(start, end)
        self.record({"kind": "unit", "unit": label, "attempt": 0, "start": start, "end": end, "waited_s": waited,
                     "children": [label], "valid": not reasons, "reasons": reasons, "block_child": True})
        if reasons:
            raise BlockInvalid(f"{label}: {'; '.join(reasons)}")
        return result


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


_GATE: Optional[Gate] = None


def gate() -> Gate:
    global _GATE
    if _GATE is None:
        directory = os.environ.get("KNOTREL_INTERFERENCE_DIR")
        if not directory:
            raise SystemExit("KNOTREL_INTERFERENCE_DIR is not set: the interference gate is mandatory")
        _GATE = Gate(Path(directory))
    return _GATE


def valid_children(directory: Path) -> Dict[str, int]:
    """Valid children per experiment prefix (text before ':'), counting only each step's final block."""
    rows = [json.loads(line) for line in (Path(directory) / "units.jsonl").read_text().splitlines() if line.strip()] \
        if (Path(directory) / "units.jsonl").exists() else []
    final_block: Dict[str, str] = {}
    for r in rows:
        if r.get("kind") == "unit" and r.get("block"):
            final_block[r["block"].split("#")[0]] = r["block"]
    counts: Dict[str, int] = {}
    for r in rows:
        if r.get("kind") != "unit" or not r["valid"]:
            continue
        if r.get("block") and final_block.get(r["block"].split("#")[0]) != r["block"]:
            continue
        for label in r["children"]:
            prefix = label.split(":", 1)[0]
            counts[prefix] = counts.get(prefix, 0) + 1
    return counts
