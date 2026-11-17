#!/usr/bin/env python3
"""Analysis of the declared v0.6.0 supplementary contention run (M supplement).

Writes ``analysis.json`` into the collector directory. M_desc rows come from the
frozen ``analyze_mdesc`` unchanged, plus a validity flag per configuration
(supplement matrix ``rules.validity``). M_reg verdicts come from the frozen
``analyze_mreg`` unchanged, applied to the supplement's two cells, after the
validity check of every analyzed observation (a cell with an invalid
observation is INVALID, with no verdict).

    analyze_v060_m_supplement.py mdesc|mreg DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analyze_v060_qualification import (  # noqa: E402
    NAME, AnalysisError, analyze_mdesc, analyze_mreg, load_children,
)

MATRIX = (Path(__file__).resolve().parent.parent / "results" / "v0.6.0-qualification" / "supplement-M"
          / "MATRIX-M-SUPPLEMENT.json")


def validity(record: Dict[str, Any]) -> List[str]:
    """Reasons why a probe configuration record is invalid (empty when valid)."""
    reasons = []
    if record.get("errors"):
        reasons.append(f"errors={record['errors']}")
    if record.get("item_errors"):
        reasons.append(f"item_errors={record['item_errors']}")
    if record.get("noop_mutations"):
        reasons.append(f"noop_mutations={record['noop_mutations']}")
    for key in ("item_errors", "noop_mutations"):
        if key not in record:
            reasons.append(f"missing {key} (probe revision 1?)")
    background = record.get("background")
    if background:
        if background.get("failures"):
            reasons.append(f"background failures={background['failures']} {background.get('failure_kinds')}")
        if not background.get("completed"):
            reasons.append("background completed=0")
    return reasons


def analyze_supplement_mdesc(directory: Path) -> Dict[str, Any]:
    result = analyze_mdesc(directory, {})
    flags = []
    for child in load_children(directory):
        for record in child["records"]:
            if record.get("kind") == "config":
                flags.append(validity(record))
    if len(flags) != len(result["rows"]):
        raise AnalysisError("row count mismatch")
    for row, reasons in zip(result["rows"], flags):
        row["valid"] = not reasons
        row["invalid_reasons"] = reasons
    result["invalid_configs"] = [f"{r['server']}/{r['config']}" for r in result["rows"] if not r["valid"]]
    return result


def analyze_supplement_mreg(directory: Path, matrix: Dict[str, Any]) -> Dict[str, Any]:
    spec = matrix["M_reg_supplement"]
    invalid: Dict[str, List[str]] = {}
    for child in load_children(directory):
        match = NAME.match(child["name"])
        if not match or match["phase"] != "analyzed":
            continue
        record = next(r for r in child["records"] if r.get("kind") == "config")
        reasons = validity(record)
        if reasons:
            invalid.setdefault(match["cell"], []).append(f"{child['name']}: {'; '.join(reasons)}")
    valid_cells = [c for c in spec["cells"] if c["id"] not in invalid]
    out: Dict[str, Any] = {}
    if valid_cells:
        out.update(analyze_mreg(directory, {"experiments": {"M_reg": {**spec, "cells": valid_cells}}}))
    for cell_id, reasons in invalid.items():
        out[cell_id] = {"verdict": "INVALID", "invalid_observations": reasons}
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("experiment", choices=["mdesc", "mreg"])
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    matrix = json.loads(MATRIX.read_text())
    try:
        if args.experiment == "mdesc":
            result = analyze_supplement_mdesc(args.directory)
        else:
            result = analyze_supplement_mreg(args.directory, matrix)
    except (AnalysisError, KeyError, StopIteration, ValueError) as error:
        print(f"analysis rejected: {error!r}", file=sys.stderr)
        return 2
    result = {"label": matrix["label"], "result": result}
    (args.directory / "analysis.json").write_text(json.dumps(result, indent=1))
    print(json.dumps(result, indent=1)[:4000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
