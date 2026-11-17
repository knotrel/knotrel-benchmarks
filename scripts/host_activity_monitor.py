#!/usr/bin/env python3
"""Host-activity monitor for benchmark runs (v0.6.0 M_reg rerun).

Samples the process table every ``--interval`` seconds (default 0.2) and
appends one JSON line per sample that contains a process matching the
activity pattern (Git, Cargo, rustc, Antigravity IDE, Visual Studio Code),
plus one ``top`` line per second with the five busiest processes other than
the measured server and probe. Runs until SIGTERM/SIGINT. Read-only: it
never touches the processes or repositories it observes.

    host_activity_monitor.py --out FILE [--interval 0.2]
    host_activity_monitor.py --check     # exit 1 if a matching process exists now
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import signal
import subprocess
import sys
import time
from typing import Dict, List

PATTERN = re.compile(r"(^|/)(git|git-[a-z-]+|cargo|rustc)( |$)|Antigravity|Visual Studio Code|Code Helper")
MEASURED = re.compile(r"knotrel-server|contention-probe")


def utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def processes() -> List[Dict[str, object]]:
    out = subprocess.run(["ps", "-Ao", "pid=,ppid=,pcpu=,args="], capture_output=True, text=True).stdout
    rows = []
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) == 4:
            rows.append({"pid": int(parts[0]), "ppid": int(parts[1]), "pcpu": float(parts[2]), "args": parts[3]})
    return rows


def matching(rows: List[Dict[str, object]]) -> List[Dict[str, object]]:
    me = os.getpid()
    return [r for r in rows if r["pid"] != me and PATTERN.search(str(r["args"]))]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out")
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.check:
        found = matching(processes())
        for row in found:
            print(json.dumps(row))
        return 1 if found else 0
    if not args.out:
        parser.error("--out is required unless --check")
    running = True

    def stop(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    last_top = 0.0
    samples = 0
    with open(args.out, "a", buffering=1) as handle:
        handle.write(json.dumps({"kind": "start", "utc": utc(), "interval_s": args.interval,
                                 "pattern": PATTERN.pattern}) + "\n")
        while running:
            rows = processes()
            samples += 1
            found = matching(rows)
            if found:
                handle.write(json.dumps({"kind": "match", "utc": utc(), "processes": found}) + "\n")
            now = time.monotonic()
            if now - last_top >= 1.0:
                last_top = now
                busy = sorted((r for r in rows if not MEASURED.search(str(r["args"]))),
                              key=lambda r: -float(r["pcpu"]))[:5]
                handle.write(json.dumps({"kind": "top", "utc": utc(),
                                         "processes": [{**r, "args": str(r["args"])[:160]} for r in busy]}) + "\n")
            time.sleep(args.interval)
        handle.write(json.dumps({"kind": "stop", "utc": utc(), "samples": samples}) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
