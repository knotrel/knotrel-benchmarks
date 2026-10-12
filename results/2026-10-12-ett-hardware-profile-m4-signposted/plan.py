#!/usr/bin/env python3
"""Create the fixed balanced 72-process marker-scoped profiling plan."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path


RESULTS = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    """Return a SHA-256 digest for one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    """Create the plan once and refuse to alter an existing collection."""
    plan_path = RESULTS / "plan.json"
    if plan_path.exists() or list(RESULTS.glob("batch-*.json")):
        raise RuntimeError("profiling plan or collection batch already exists")
    cases = (
        {
            "name": "path-fresh",
            "workload": "sustained-churn-path-v1",
            "nodes": 1_000_000,
            "query_percent": 50,
            "warmup": 0,
        },
        {
            "name": "path-warmed",
            "workload": "sustained-churn-path-v1",
            "nodes": 1_000_000,
            "query_percent": 50,
            "warmup": 1,
        },
        {
            "name": "dense-warmed",
            "workload": "dense-bridge-churn-v1",
            "nodes": 512,
            "query_percent": 90,
            "warmup": 1,
        },
    )
    groups = []
    for case in cases:
        for trial in range(12):
            groups.append(
                {
                    "case": case,
                    "trial": trial,
                    "order": ["before", "after"]
                    if trial % 2 == 0
                    else ["after", "before"],
                }
            )
    random.Random(1012).shuffle(groups)
    plan = {
        "schema_version": 1,
        "seed": 1012,
        "groups": groups,
        "batches": [groups[index : index + 6] for index in range(0, len(groups), 6)],
        "protocol_sha256": sha256(RESULTS / "protocol.md"),
    }
    plan_path.write_text(json.dumps(plan, indent=2) + "\n")


if __name__ == "__main__":
    main()
