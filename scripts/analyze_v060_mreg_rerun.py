#!/usr/bin/env python3
"""Analysis of the declared v0.6.0 M_reg rerun.

Verdicts come from the M supplement's analysis (frozen ``analyze_mreg`` plus
the validity rule) unchanged. Conformance (rerun matrix ``rules.conformance``)
is applied on top:

- a child whose interval ``[start, start + duration + 1 s]`` overlaps a
  ``match`` sample of the host-activity monitor is non-conforming; a cell with a
  non-conforming analyzed observation becomes NONCONFORMING (no verdict);
- a quiet-period log with any ``match`` sample, or a Git-state comparison with
  any change, makes every cell NONCONFORMING.

    analyze_v060_mreg_rerun.py DIR --monitor FILE --quiet FILE --git-diff FILE
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_v060_m_supplement import analyze_supplement_mreg  # noqa: E402
from analyze_v060_qualification import NAME, AnalysisError  # noqa: E402
from cli_paths import confined, confined_directory  # noqa: E402

MATRIX = (Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "supplement-M"
          / "rerun-Mreg" / "MATRIX-MREG-RERUN.json")


def parse_utc(text: str) -> float:
    text = text.rstrip("Z")
    fmt = "%Y-%m-%dT%H:%M:%S.%f" if "." in text else "%Y-%m-%dT%H:%M:%S"
    return datetime.datetime.strptime(text, fmt).replace(tzinfo=datetime.timezone.utc).timestamp()


def match_times(path: Path) -> List[float]:
    times = []
    for line in path.read_text().splitlines():
        if line.strip():
            record = json.loads(line)
            if record.get("kind") == "match":
                times.append(parse_utc(record["utc"]))
    return times


def child_intervals(directory: Path) -> List[Tuple[str, float, float]]:
    log = json.loads((directory / "run-log.json").read_text())
    out = []
    for child in log["children"]:
        start = parse_utc(child["host"]["utc"])
        out.append((child["name"], start, start + float(child["seconds"]) + 1.0))
    return out


def analyze(directory: Path, monitor: Path, quiet: Path, git_diff: Path, matrix: Dict[str, Any]) -> Dict[str, Any]:
    verdicts = analyze_supplement_mreg(directory, matrix)
    matches = match_times(monitor)
    nonconforming: Dict[str, List[str]] = {}
    for name, start, end in child_intervals(directory):
        hits = [t for t in matches if start <= t <= end]
        parsed = NAME.match(name)
        if hits and parsed and parsed["phase"] == "analyzed":
            nonconforming.setdefault(parsed["cell"], []).append(f"{name}: {len(hits)} matching samples")
    quiet_matches = len(match_times(quiet))
    git_changes = json.loads(git_diff.read_text()).get("changed", [])
    run_level = []
    if quiet_matches:
        run_level.append(f"quiet period: {quiet_matches} matching samples")
    if git_changes:
        run_level.append(f"git state changed during the run: {git_changes[:10]}")
    for cell_id in list(verdicts):
        reasons = run_level + nonconforming.get(cell_id, [])
        if reasons:
            verdicts[cell_id] = {"verdict": "NONCONFORMING", "analyzer_result": verdicts[cell_id],
                                 "reasons": reasons}
    return {"cells": verdicts, "monitor_match_samples": len(matches), "quiet_match_samples": quiet_matches,
            "git_changes": git_changes}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--monitor", required=True, type=Path)
    parser.add_argument("--quiet", required=True, type=Path)
    parser.add_argument("--git-diff", required=True, type=Path)
    args = parser.parse_args()
    args.directory = confined_directory(args.directory, "DIR")
    args.monitor = confined(args.monitor, "--monitor")
    args.quiet = confined(args.quiet, "--quiet")
    args.git_diff = confined(args.git_diff, "--git-diff")
    matrix = json.loads(MATRIX.read_text())
    try:
        result = analyze(args.directory, args.monitor, args.quiet, args.git_diff, matrix)
    except (AnalysisError, KeyError, StopIteration, ValueError) as error:
        print(f"analysis rejected: {error!r}", file=sys.stderr)
        return 2
    result = {"label": matrix["label"], "result": result}
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
