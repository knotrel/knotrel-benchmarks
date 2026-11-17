#!/usr/bin/env python3
"""Post-campaign conformance cross-check of the v0.7.0 qualification.

Joins every measured interval of the frozen v0.7.0 campaign (A observations;
B/C cells; R, Rmem and M_reg children; M_desc server processes) with the
continuous host-activity monitor (``logs/activity-monitor.jsonl``). It reads
only; it changes no data, verdict or analysis.

Process classes (descriptive, declared in results/v0.7.0-requalification/RERUN-PROPOSAL.md):
- ``user_app``: interactive applications and their helpers (browser, chat,
  container desktop, terminal, desktop assistant apps, file dialogs, disk-image
  mounts). Finder, the always-running macOS shell, is classed as system; its
  file dialogs (open/save panel services) are user activity. The frozen
  operator rule ("The operator runs nothing else until it
  completes", ``run_final_chain.sh``) excludes them.
- ``agent``: Claude Code CLI processes. ``FREEZE.json`` requires the other
  agent session to be idle; idleness cannot be established from CPU samples.
- ``system``: everything else outside the campaign (WindowServer, launchd,
  macOS daemons). Reported as an association only.

Per measured interval [start - 1 s, end + 1 s]:
- NONCONFORMING: a ``user_app`` process appears in a monitor sample.
- INDETERMINATE: none appears, but the monitor records only the five busiest
  processes, so absence below the top five cannot be shown while user
  applications are alive during the campaign.
- CONFORMING: user applications provably absent. The monitor cannot show
  this here, so no interval qualifies.

    analyze_v070_conformance.py CAMPAIGN_DIR --json OUT.json --markdown OUT.md
"""

from __future__ import annotations

import argparse
import bisect
import datetime as dt
import glob
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

USER_APP = re.compile(
    r"Google Chrome|WhatsApp|Docker|Terminal\.app|Gemini|Claude\.app/|openAndSavePanel|"
    r"diskimages-helper|hdiejectd")
AGENT = re.compile(r"claude-code/")
CAMPAIGN = re.compile(r"knotrel|release-cells|memory-peak|core-lifecycle|http-lifecycle|contention-probe|"
                      r"measure_e2e|host_activity_monitor|run_p0_aa|run_v0|run_lifecycle|caffeinate")


def ts(text: str) -> float:
    return dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()


def short(args: str) -> str:
    app = re.search(r"/([^/]+?)\.app/", args)
    return (app.group(1) if app else args.split("/")[-1].split(" ")[0])[:32]


class Monitor:
    def __init__(self, path: Path):
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
        self.start = ts(next(r for r in rows if r["kind"] == "start")["utc"])
        self.stop = ts(next(r for r in rows if r["kind"] == "stop")["utc"])
        self.matches = [r for r in rows if r["kind"] == "match"]
        self.tops = sorted(((ts(r["utc"]), r["processes"]) for r in rows if r["kind"] == "top"), key=lambda x: x[0])
        self.times = [t for t, _ in self.tops]

    def window(self, start: float, end: float) -> List[Tuple[float, List[Dict[str, Any]]]]:
        lo = bisect.bisect_left(self.times, start - 1.0)
        hi = bisect.bisect_right(self.times, end + 1.0)
        return self.tops[lo:hi]


def classify(samples) -> Dict[str, Any]:
    user, agent, system = defaultdict(float), defaultdict(float), defaultdict(float)
    for _, procs in samples:
        per = defaultdict(float)
        for p in procs:
            if CAMPAIGN.search(p["args"]):
                continue
            per[(short(p["args"]), "user" if USER_APP.search(p["args"]) else
                 "agent" if AGENT.search(p["args"]) else "system")] += p["pcpu"]
        for (name, cls), cpu in per.items():
            target = user if cls == "user" else agent if cls == "agent" else system
            target[name] = max(target[name], cpu)
    status = "NONCONFORMING" if user else "INDETERMINATE"
    return {"status": status, "user": dict(user), "agent": dict(agent),
            "system_over_30": {k: v for k, v in system.items() if v > 30}}


def intervals(camp: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for phase, pattern in (("A-main", "A/raw-main/pair_*.json"),
                           ("A-extension", "A/extension/raw-extension/pair_*.json")):
        for f in sorted(glob.glob(str(camp / pattern))):
            pair = json.loads(Path(f).read_text())
            cell = re.sub(r"^pair_\d+_", "", Path(f).stem)
            for obs in pair["observations"]:
                out.append({"experiment": phase, "cell": cell, "kind": "observation",
                            "start": obs["launch_unix_ns"] / 1e9, "end": obs["completion_unix_ns"] / 1e9})
    for line in (camp / "BC/run-log.jsonl").read_text().splitlines():
        rec = json.loads(line)
        start = ts(rec["host_before"]["utc"])
        out.append({"experiment": "BC", "cell": rec["id"], "kind": "cell (all pairs)",
                    "start": start, "end": start + rec["seconds"] + 1.0})
    for exp in ("R", "Rmem", "Mreg", "Mdesc"):
        log = json.loads((camp / exp / "run-log.json").read_text())
        for child in log["children"]:
            start = ts(child["host"]["utc"])
            name = re.sub(r"^\d+-", "", child["name"])
            m = re.match(r"^(?P<cell>.+?)-(?P<phase>warmup|analyzed)-\d{2}-(?P<arm>ref|cand)$", name)
            cell = m["cell"] if m else re.sub(r"-(ref|cand)$", "", name)
            kind = (m["phase"] + " observation") if m else ("server process (all configurations)" if exp == "Mdesc" else "observation")
            # host utc has 1 s resolution: widen by 1 s.
            out.append({"experiment": exp, "cell": cell, "kind": kind, "start": start, "end": start + child["seconds"] + 1.0})
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("campaign", type=Path)
    ap.add_argument("--json", type=Path, required=True)
    ap.add_argument("--markdown", type=Path, required=True)
    args = ap.parse_args()
    mon = Monitor(args.campaign / "logs/activity-monitor.jsonl")
    items = intervals(args.campaign)
    cells: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for it in items:
        samples = mon.window(it["start"], it["end"])
        c = classify(samples)
        it.update(c, samples=len(samples), covered=mon.start <= it["start"] and it["end"] <= mon.stop + 1.0)
        key = (it["experiment"], it["cell"])
        row = cells.setdefault(key, {"experiment": it["experiment"], "cell": it["cell"], "kind": it["kind"],
                                     "start": it["start"], "end": it["end"], "intervals": 0, "samples": 0,
                                     "uncovered": 0, "NONCONFORMING": 0, "INDETERMINATE": 0, "CONFORMING": 0,
                                     "user": defaultdict(float), "agent": defaultdict(float),
                                     "system_over_30": defaultdict(float)})
        if row["kind"] != it["kind"]:
            row["kind"] = "observations (warmup + analyzed)"
        row["start"], row["end"] = min(row["start"], it["start"]), max(row["end"], it["end"])
        row["intervals"] += 1
        row["samples"] += it["samples"]
        row["uncovered"] += 0 if it["covered"] else 1
        row[it["status"]] += 1
        for cls in ("user", "agent", "system_over_30"):
            for k, v in it[cls].items():
                row[cls][k] = max(row[cls][k], v)
    result = {"monitor": {"start": mon.start, "stop": mon.stop, "top_samples": len(mon.tops),
                          "max_gap_s": max(b - a for a, b in zip(mon.times, mon.times[1:])),
                          "pattern_matches": len(mon.matches)},
              "cells": [{**r, "user": dict(r["user"]), "agent": dict(r["agent"]),
                         "system_over_30": dict(r["system_over_30"])} for r in cells.values()],
              "intervals": items}
    args.json.write_text(json.dumps(result, indent=1))

    def fmt(t: float) -> str:
        return dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%H:%M:%S")

    def names(d: Dict[str, float]) -> str:
        return ", ".join(f"{k} {v:.0f}%" for k, v in sorted(d.items(), key=lambda x: -x[1])[:4]) or "—"

    lines = [
        "# v0.7.0 qualification: conformance cross-check (all cells)", "",
        "Generated by `scripts/analyze_v070_conformance.py` from the frozen campaign's raw run logs and "
        "`logs/activity-monitor.jsonl`. It changes no data or verdict. Classes and rules: see the script "
        "docstring and `results/v0.7.0-requalification/RERUN-PROPOSAL.md` §1.2 and §2.1.", "",
        f"Monitor alive {fmt(mon.start)}–{fmt(mon.stop)}Z, {len(mon.tops)} top-5 samples, largest gap "
        f"{result['monitor']['max_gap_s']:.2f} s, {result['monitor']['pattern_matches']} gate-pattern matches. "
        "Coverage limit: only the five busiest processes per second, so activity below the top five is not "
        "visible; R/Rmem/M child start times have 1 s resolution (intervals widened by 1 s).", "",
        "Protocol treatment (all rows): the violated rule is the chain-wide operator rule; the frozen protocol "
        "gives it no observation-, pair- or session-level consequence, so non-conformance attaches to the "
        "**campaign**. Data and verdicts stay unchanged; no result of this campaign is proposed for "
        "acceptance; every experiment is repeated in a new declared collection.", "",
        "| Experiment | Cell / session | Measured interval (UTC) | Unit | Units | Monitor samples | "
        "User-application activity observed (max % CPU) | Agent processes (max %) | System > 30% "
        "(association only) | Non-conforming / indeterminate / conforming units |",
        "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(cells.values(), key=lambda r: r["start"]):
        lines.append(
            f"| {r['experiment']} | `{r['cell']}` | {fmt(r['start'])}–{fmt(r['end'])} | {r['kind']} | {r['intervals']} | "
            f"{r['samples']}{' (not covered: ' + str(r['uncovered']) + ')' if r['uncovered'] else ''} | {names(r['user'])} | "
            f"{names(r['agent'])} | {names(r['system_over_30'])} | {r['NONCONFORMING']} / {r['INDETERMINATE']} / {r['CONFORMING']} |")
    totals = defaultdict(lambda: defaultdict(int))
    for it in items:
        totals[it["experiment"]][it["status"]] += 1
    lines += ["", "## Totals per experiment (units)", "",
              "| Experiment | Non-conforming | Indeterminate | Conforming |", "|---|---|---|---|"]
    for exp, t in totals.items():
        lines.append(f"| {exp} | {t['NONCONFORMING']} | {t['INDETERMINATE']} | {t['CONFORMING']} |")
    args.markdown.write_text("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
