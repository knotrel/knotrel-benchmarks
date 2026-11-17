#!/usr/bin/env python3
"""Summary of a v0.7.0 in-process diagnostic (R paired cells, Rmem cells).

R: arm medians of ``observation_ns`` and the paired change
``exp(median ln(cand/ref)) - 1`` with the range r(2)-r(n-1). Rmem: the
deterministic byte counts of each arm and their ratio. Descriptive only.

    analyze_v070_diagnostic_cells.py DIR [--markdown]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_v070_diagnostic_probe import summarize  # noqa: E402

R_NAME = re.compile(r"^\d{5}-(?P<cell>R-.+)-(?P<phase>warmup|analyzed)-(?P<index>\d{2})-(?P<arm>ref|cand)$")
M_NAME = re.compile(r"^\d{5}-(?P<cell>Rmem-.+)-(?P<arm>ref|cand)$")
MEM_KEYS = ("peak_after", "transient_over_final")


def last_record(path: Path) -> Dict[str, Any]:
    for line in reversed(path.read_text().splitlines()):
        if line.startswith("{") and json.loads(line).get("kind") != "build":
            return json.loads(line)
    raise ValueError(f"{path}: no result record")


def analyze(directory: Path) -> Dict[str, Any]:
    log = json.loads((directory / "run-log.json").read_text())
    r: Dict[str, Dict[str, Dict[str, float]]] = {}
    mem: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for child in log["children"]:
        stdout = directory / "raw" / f"{child['name']}.stdout"
        parsed = R_NAME.match(child["name"])
        if parsed:
            if parsed["phase"] == "analyzed":
                value = last_record(stdout)["observation_ns"]
                r.setdefault(parsed["cell"], {}).setdefault(parsed["index"], {})[parsed["arm"]] = value
            continue
        parsed = M_NAME.match(child["name"])
        if parsed:
            mem.setdefault(parsed["cell"], {})[parsed["arm"]] = last_record(stdout)
    out: Dict[str, Any] = {"R": {}, "Rmem": {}}
    for cell, by_index in r.items():
        pairs = [p for p in by_index.values() if "ref" in p and "cand" in p]
        refs = [p["ref"] / 1e6 for p in pairs]
        cands = [p["cand"] / 1e6 for p in pairs]
        out["R"][cell] = {"ref_ms": statistics.median(refs), "cand_ms": statistics.median(cands),
                          **summarize([math.log(c / b) for b, c in zip(refs, cands)])}
    for cell, arms in mem.items():
        row = {}
        for key in MEM_KEYS:
            if key in arms.get("ref", {}) and key in arms.get("cand", {}):
                ref, cand = arms["ref"][key], arms["cand"][key]
                row[key] = {"ref_mib": ref / 2**20, "cand_mib": cand / 2**20, "change_pct": (cand / ref - 1) * 100}
        out["Rmem"][cell] = row
    return out


def markdown(result: Dict[str, Any]) -> str:
    lines = ["| R cell | v0.6.0 ms | candidate ms | change [r(2)-r(n-1)] |", "|---|---|---|---|"]
    for cell, row in sorted(result["R"].items()):
        lines.append(f"| {cell} | {row['ref_ms']:.3f} | {row['cand_ms']:.3f} | "
                     f"{row['change_pct']:+.2f}% [{row['low_pct']:+.2f}, {row['high_pct']:+.2f}] |")
    lines += ["", "| Rmem cell | metric | v0.6.0 MiB | candidate MiB | change |", "|---|---|---|---|---|"]
    for cell, rows in sorted(result["Rmem"].items()):
        for key, row in rows.items():
            lines.append(f"| {cell} | {key} | {row['ref_mib']:.1f} | {row['cand_mib']:.1f} | {row['change_pct']:+.1f}% |")
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
