#!/usr/bin/env python3
"""Host telemetry monitor of the proportional interference policy (qualification 3, revision 3).

Samples the host once per second while the campaign root process lives, and writes one JSON
line per sample to ``telemetry.jsonl`` and the same sample's identity to ``monitor-status.json``
(atomic replace). Both carry the **same** ``t`` value: ``time.time()`` written exactly (JSON
round-trips a float), never rounded. The gate compares unit boundaries taken from the same
clock with these values (PROTOCOL section 14.1).

Per sample:
- ``ext_cpu``: CPU cores used by processes **outside** the campaign since the previous sample,
  from cumulative CPU time (``ps -A -o pid=,ppid=,time=,comm=``). The campaign is the root
  process and all its descendants: runner, collectors, benchmarks, servers and this monitor.
  A process that appears between two samples counts with all its CPU time; one that starts
  and exits between two samples is not seen (declared limit);
- ``camp_cpu``: the same for the campaign (context);
- ``top``: the three busiest external processes (context);
- ``pressure``: ``kern.memorystatus_vm_pressure_level`` (1 normal, 2 warning, 4 critical);
- ``sleep_s``: growth of (wall clock - monotonic clock) since the previous sample. The
  monotonic clock stops while the Mac sleeps, so a sleep shows as a jump;
- ``load1``: one-minute load average (context).
- ``ac`` (on AC power) and ``therm`` (``ok`` or the pmset warning text), read after ``t``.
Every fifth sample adds ``swapouts`` and ``pageouts`` (cumulative, context) and ``hid_idle``
(seconds since the last user input, context only). Every external command has a 10-s timeout.

    interference_monitor.py monitor --root PID --dir DIR [--interval 1.0]
    interference_monitor.py sample            # one sample pair to stdout (diagnostics)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

C_ENV = {"PATH": "/usr/bin:/bin:/usr/sbin:/sbin", "LANG": "C", "LC_ALL": "C"}
SLOW_EVERY = 5


def parse_cpu_time(text: str) -> float:
    """``ps`` cumulative CPU time: ``[[dd-]hh:]mm:ss[.cc]`` to seconds."""
    days = 0
    if "-" in text:
        day, text = text.split("-", 1)
        days = int(day)
    parts = [float(p) for p in text.split(":")]
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + part
    return days * 86400 + seconds


Table = Dict[int, Tuple[int, float, str]]


def cpu_table() -> Table:
    """pid -> (ppid, cumulative CPU seconds, command name)."""
    out = subprocess.run(["ps", "-A", "-o", "pid=,ppid=,time=,comm="], capture_output=True, text=True,
                         env=C_ENV, check=True, timeout=10).stdout
    table: Table = {}
    for line in out.splitlines():
        fields = line.split(None, 3)
        if len(fields) < 3:
            continue
        try:
            table[int(fields[0])] = (int(fields[1]), parse_cpu_time(fields[2]),
                                     os.path.basename(fields[3]) if len(fields) > 3 else "")
        except ValueError:
            continue
    return table


def descendants(root: int, table: Table) -> Set[int]:
    children: Dict[int, List[int]] = {}
    for pid, (ppid, _, _) in table.items():
        children.setdefault(ppid, []).append(pid)
    found, stack = {root}, [root]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in found:
                found.add(child)
                stack.append(child)
    return found


def cpu_delta(previous: Table, current: Table, campaign: Set[int]) -> Tuple[float, float, List[Tuple[str, float]]]:
    """CPU seconds since ``previous``: (external, campaign, busiest external [(name, seconds)])."""
    external = camp = 0.0
    per: List[Tuple[str, float]] = []
    for pid, (_, seconds, name) in current.items():
        before = previous.get(pid)
        used = seconds - before[1] if before is not None and before[1] <= seconds else seconds
        if used <= 0:
            continue
        if pid in campaign:
            camp += used
        else:
            external += used
            per.append((name, used))
    per.sort(key=lambda x: -x[1])
    return external, camp, per[:3]


def pressure_level() -> Optional[int]:
    out = subprocess.run(["sysctl", "-n", "kern.memorystatus_vm_pressure_level"], capture_output=True,
                         text=True, env=C_ENV, timeout=10)
    try:
        return int(out.stdout.strip())
    except ValueError:
        return None


def power_on_ac() -> Optional[bool]:
    out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, env=C_ENV, timeout=10).stdout
    first = out.splitlines()[0] if out.strip() else ""
    return None if not first else "AC Power" in first


def thermal_state() -> str:
    """``ok``, or the pmset lines that report a recorded warning or a speed limit below 100."""
    out = subprocess.run(["pmset", "-g", "therm"], capture_output=True, text=True, env=C_ENV, timeout=10)
    if out.returncode != 0:
        return f"unreadable: {out.stderr.strip()[:200]}"
    bad = []
    for line in out.stdout.splitlines():
        text = line.strip()
        limit = re.search(r"CPU_Speed_Limit\s*=\s*(\d+)", text)
        if limit and int(limit.group(1)) != 100:
            bad.append(text)
        elif ("warning level" in text or "CPU power status" in text) and not text.startswith("Note: No "):
            bad.append(text)
    return "ok" if not bad else "; ".join(bad)[:300]


def vm_counters() -> Dict[str, Optional[int]]:
    out = subprocess.run(["vm_stat"], capture_output=True, text=True, env=C_ENV, timeout=10).stdout
    found: Dict[str, Optional[int]] = {"swapouts": None, "pageouts": None}
    for line in out.splitlines():
        for key, label in (("swapouts", "Swapouts"), ("pageouts", "Pageouts")):
            if line.startswith(label + ":"):
                found[key] = int(line.split(":")[1].strip().rstrip("."))
    return found


def hid_idle() -> Optional[float]:
    out = subprocess.run(["ioreg", "-c", "IOHIDSystem", "-d", "4", "-r"], capture_output=True, text=True,
                         env=C_ENV, timeout=10).stdout
    match = re.search(r'"HIDIdleTime" = (\d+)', out)
    return int(match.group(1)) / 1e9 if match else None


def write_atomic(path: Path, value: Dict[str, object]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value))
    os.replace(tmp, path)


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


class Sampler:
    """One telemetry sample per call; the first call only primes the CPU table."""

    def __init__(self, root: int, clock=time.time, mono=time.monotonic, table=cpu_table,
                 pressure=pressure_level, power=power_on_ac, therm=thermal_state, vm=vm_counters,
                 idle=hid_idle):
        self.root, self.clock, self.mono = root, clock, mono
        self.table, self.pressure, self.power, self.therm, self.vm, self.idle = table, pressure, power, therm, vm, idle
        self.previous: Optional[Table] = None
        self.prev_t = self.prev_offset = 0.0
        self.seq = 0

    def sample(self) -> Optional[Dict[str, object]]:
        t, mono = self.clock(), self.mono()
        table = self.table()
        offset = t - mono
        if self.previous is None:
            self.previous, self.prev_t, self.prev_offset = table, t, offset
            return None
        span = max(t - self.prev_t, 1e-6)
        ext, camp, top = cpu_delta(self.previous, table, descendants(self.root, table))
        self.seq += 1
        row: Dict[str, object] = {
            "k": "s", "t": t, "mono": mono, "seq": self.seq, "span_s": span,
            "ext_cpu": ext / span, "camp_cpu": camp / span,
            "top": [[name, round(sec / span, 3)] for name, sec in top],
            "pressure": self.pressure(), "sleep_s": max(0.0, offset - self.prev_offset),
            "load1": os.getloadavg()[0], "ac": self.power(), "therm": self.therm()}
        if self.seq % SLOW_EVERY == 1:
            row.update({**self.vm(), "hid_idle": self.idle()})
        self.previous, self.prev_t, self.prev_offset = table, t, offset
        return row


def monitor(root: int, directory: Path, interval: float) -> int:
    directory.mkdir(parents=True, exist_ok=True)
    log, status = directory / "telemetry.jsonl", directory / "monitor-status.json"
    running = True

    def stop(*_: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    sampler = Sampler(root)
    reason = "signal"
    with open(log, "a", buffering=1) as handle:
        handle.write(json.dumps({"k": "start", "t": time.time(), "pid": os.getpid(), "root": root,
                                 "interval_s": interval}) + "\n")
        while running:
            began = time.monotonic()
            if not alive(root):
                reason = "root_gone"
                break
            try:
                row = sampler.sample()
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                handle.write(json.dumps({"k": "error", "t": time.time(), "error": str(error)[:300]}) + "\n")
                row = None
            if row is not None:
                handle.write(json.dumps(row) + "\n")
                write_atomic(status, {"pid": os.getpid(), "t": row["t"], "seq": row["seq"]})
            time.sleep(max(0.0, interval - (time.monotonic() - began)))
        handle.write(json.dumps({"k": "stop", "t": time.time(), "reason": reason, "samples": sampler.seq}) + "\n")
    return 0


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("monitor")
    m.add_argument("--root", type=int, required=True)
    m.add_argument("--dir", type=Path, required=True)
    m.add_argument("--interval", type=float, default=1.0)
    sub.add_parser("sample")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.command == "monitor":
        return monitor(args.root, args.dir, args.interval)
    sampler = Sampler(os.getpid())
    sampler.sample()
    time.sleep(1.0)
    print(json.dumps(sampler.sample()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
