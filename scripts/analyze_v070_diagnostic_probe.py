#!/usr/bin/env python3
"""Paired summary of a v0.7.0 contention diagnostic (descriptive only).

For each cell and metric: arm medians, the paired change
``exp(median ln(cand/ref)) - 1`` and the order-statistic range r(2)-r(n-1)
of the paired changes (n = 8: about a 93% distribution-free interval for the
median). Throughput-like metrics are inverted so that a positive change is
always worse. Every analyzed observation must have exit 0, no transport
error and only 200/503 statuses; otherwise the cell is INVALID.

    analyze_v070_diagnostic_probe.py DIR [--markdown]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

NAME = re.compile(r"^\d{5}-(?P<cell>.+)-(?P<phase>warmup|analyzed)-(?P<index>\d{2})-(?P<arm>ref|cand)$")

# (label, extractor, higher_is_better)
METRICS = [
    ("req/s", lambda r: r["requests_per_s"], True),
    ("p50 ms", lambda r: r["latency_ns"]["p50"] / 1e6, False),
    ("p99 ms", lambda r: r["latency_ns"]["p99"] / 1e6, False),
    ("lock wait / latency", lambda r: lock_share(r), False),
    ("feeder events", lambda r: (r.get("background") or {}).get("completed")
     if (r.get("background") or {}).get("kind") == "events" else None, True),
    ("feeder batch p50 ms", lambda r: (r["background"]["p50_ns"] / 1e6)
     if (r.get("background") or {}).get("kind") == "events" else None, False),
    ("imports", lambda r: (r.get("background") or {}).get("completed")
     if (r.get("background") or {}).get("kind") == "import" else None, True),
]


def lock_share(record: Dict[str, Any]) -> Optional[float]:
    phases = record.get("server_phases", {})
    for kind in ("batch", "operation"):
        wait = phases.get(f'knotrel_graph_lock_wait_seconds{{kind="{kind}"}}')
        if wait and wait.get("count"):
            return wait["mean_s"] / (record["latency_ns"]["mean"] / 1e9)
    return None


def config_record(path: Path) -> Dict[str, Any]:
    for line in reversed(path.read_text().splitlines()):
        if line.startswith("{"):
            value = json.loads(line)
            if value.get("kind") == "config":
                return value
    raise ValueError(f"{path}: no config record")


def summarize(values: List[float]) -> Dict[str, Any]:
    ordered = sorted(values)
    n = len(ordered)
    low, high = (ordered[1], ordered[-2]) if n >= 4 else (ordered[0], ordered[-1])
    to_pct = lambda x: (math.exp(x) - 1) * 100  # noqa: E731
    return {"n": n, "change_pct": to_pct(statistics.median(ordered)), "low_pct": to_pct(low),
            "high_pct": to_pct(high)}


def analyze(directory: Path) -> Dict[str, Any]:
    log = json.loads((directory / "run-log.json").read_text())
    pairs: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
    invalid: Dict[str, List[str]] = {}
    for child in log["children"]:
        parsed = NAME.match(child["name"])
        if not parsed or parsed["phase"] != "analyzed":
            continue
        record = config_record(directory / "raw" / f"{child['name']}.stdout")
        bad = [s for s in record.get("statuses", {}) if s not in ("200", "503")]
        if child["exit"] != 0 or record.get("errors") or bad:
            invalid.setdefault(parsed["cell"], []).append(child["name"])
        pairs.setdefault(parsed["cell"], {}).setdefault(parsed["index"], {})[parsed["arm"]] = record
    result: Dict[str, Any] = {}
    for cell, by_index in pairs.items():
        complete = [p for p in by_index.values() if "ref" in p and "cand" in p]
        rows = {}
        for label, extract, higher in METRICS:
            refs = [extract(p["ref"]) for p in complete]
            cands = [extract(p["cand"]) for p in complete]
            if any(v is None or v <= 0 for v in refs + cands):
                continue
            logs = [math.log(r / c) if higher else math.log(c / r) for r, c in zip(refs, cands)]
            rows[label] = {"ref_median": statistics.median(refs), "cand_median": statistics.median(cands),
                           **summarize(logs)}
        result[cell] = {"valid": cell not in invalid, "invalid_children": invalid.get(cell, []),
                        "pairs": len(complete), "metrics": rows}
    return result


def markdown(result: Dict[str, Any]) -> str:
    lines = ["| Cell | Metric | v0.6.0 | candidate | change (positive = worse) [r(2)-r(n-1)] |",
             "|---|---|---|---|---|"]
    for cell in sorted(result):
        entry = result[cell]
        tag = "" if entry["valid"] else " **INVALID**"
        for label, row in entry["metrics"].items():
            lines.append(f"| {cell}{tag} | {label} | {row['ref_median']:.4g} | {row['cand_median']:.4g} | "
                         f"{row['change_pct']:+.1f}% [{row['low_pct']:+.1f}, {row['high_pct']:+.1f}] |")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    result = analyze(args.directory)
    print(markdown(result) if args.markdown else json.dumps(result, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
