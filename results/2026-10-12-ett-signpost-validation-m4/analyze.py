#!/usr/bin/env python3
"""Validate saved signpost exports after collection without rerunning traces."""

from __future__ import annotations

import hashlib
import json
import os
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
TRACE_ROOT = Path(os.environ.get("KNOTREL_TRACE_ARTIFACT_DIR", RESULTS))


def bundle_sha256(bundle: Path) -> str:
    """Hash a trace bundle by relative file name and per-file digest."""
    digest = hashlib.sha256()
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(bundle).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def signpost_rows(path: Path, variant: str) -> list[dict[str, int | str]]:
    """Resolve and return target-process Instruments signpost intervals."""
    tree = element_tree.parse(path)
    by_id = {
        field.attrib["id"]: field
        for field in tree.iter()
        if "id" in field.attrib
    }

    def value(field: element_tree.Element[str]) -> element_tree.Element[str]:
        while "ref" in field.attrib:
            field = by_id[field.attrib["ref"]]
        return field

    rows = []
    for row in tree.iter("row"):
        fields = {field.tag: value(field) for field in row}
        process = fields.get("process")
        if process is None or not process.attrib.get("fmt", "").startswith(f"{variant} "):
            continue
        rows.append(
            {
                "name": fields["signpost-name"].text or "",
                "start_ns": int(fields["start-time"].text or "0"),
                "duration_ns": int(fields["duration"].text or "0"),
                "process": process.attrib["fmt"],
                "thread": fields["thread"].attrib["fmt"],
            }
        )
    return rows


def valid(rows: list[dict[str, int | str]]) -> bool:
    """Require the protocol's two ordered, non-overlapping replay intervals."""
    expected = ["warmup-replay", "measurement-replay"]
    if [row["name"] for row in rows] != expected:
        return False
    warmup, measurement = rows
    return int(warmup["start_ns"]) + int(warmup["duration_ns"]) <= int(
        measurement["start_ns"]
    )


def main() -> None:
    """Write a validation result from the two immutable exported trace tables."""
    manifest = json.loads((RESULTS / "manifest.json").read_text())
    records: list[dict[str, Any]] = []
    for record in manifest["records"]:
        rows = signpost_rows(
            RESULTS / f"{record['name']}.OSSignpostIntervals.xml",
            record["variant"],
        )
        benchmark = json.loads((RESULTS / f"{record['name']}.stdout.txt").read_text())
        records.append(
            {
                "name": record["name"],
                "variant": record["variant"],
                "xctrace_exit_code": record["xctrace"]["exit_code"],
                "caffeinate_present": "caffeinate"
                in record["during_assertions"]["stdout"],
                "intervals": rows,
                "intervals_valid": valid(rows),
                "measurement_workload_wall_ns": benchmark["repetitions"][0][
                    "workload_wall_ns"
                ],
                "trace_bundle_sha256": bundle_sha256(
                    TRACE_ROOT / f"{record['name']}.trace"
                ),
            }
        )
    analysis = {
        "schema_version": 1,
        "collection_parser_status": (
            "The initial collector wrote the traces successfully but reported a false "
            "failure because it did not resolve Instruments XML references and used "
            "`name` instead of `signpost-name`. No trace was retried."
        ),
        "all_intervals_valid": all(record["intervals_valid"] for record in records),
        "trace_artifact_root": str(TRACE_ROOT),
        "records": records,
    }
    (RESULTS / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")


if __name__ == "__main__":
    main()
