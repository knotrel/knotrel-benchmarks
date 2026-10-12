#!/usr/bin/env python3
"""Summarize whole-process Instruments data without claiming replay scope."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import xml.etree.ElementTree as element_tree
from collections import Counter
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
TRACE_ROOT = Path(os.environ.get("KNOTREL_TRACE_ARTIFACT_DIR", RESULTS))
SCHEMAS = (
    "OSSignpostIntervals",
    "CounterMetricByThread",
    "MetricTableForThread",
    "ThreadActivity",
)


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha256(bundle: Path) -> str:
    """Hash a trace bundle by relative filename and per-file digest."""
    digest = hashlib.sha256()
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(bundle).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def row_count(path: Path) -> int:
    """Count exported trace rows without interpreting their values."""
    return sum(1 for element in element_tree.parse(path).iter() if element.tag == "row")


def artifact_path(name: str, suffix: str) -> Path:
    """Find an exported trace artifact in external storage or the result directory."""
    external = TRACE_ROOT / f"{name}.{suffix}"
    return external if external.exists() else RESULTS / f"{name}.{suffix}"


def target_counter_rows(path: Path, variant: str) -> dict[str, Any]:
    """Describe directly identified target-process counter intervals.

    These intervals include setup and, when applicable, warmup. They are kept
    only to show the available trace scope and must not be treated as replay
    counters.
    """
    rows = 0
    duration_ns = 0
    cores: Counter[str] = Counter()
    for row in element_tree.parse(path).iter("row"):
        fields = {child.tag: child for child in row}
        process = fields.get("process")
        if process is None or not process.attrib.get("fmt", "").startswith(f"{variant} "):
            continue
        rows += 1
        duration_ns += int(fields["duration"].text or "0")
        cores[fields["core"].attrib["fmt"]] += 1
    return {
        "rows": rows,
        "sum_interval_ns": duration_ns,
        "core_sample_counts": dict(sorted(cores.items())),
        "replay_scoped": False,
    }


def sleep_events(manifest: dict[str, Any]) -> list[str]:
    """Find actual Sleep/Wake records inside the collection interval."""
    start = dt.datetime.fromisoformat(manifest["started_utc"]).astimezone()
    end = dt.datetime.fromisoformat(manifest["completed_utc"]).astimezone()
    events = []
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} [+-]\d{4}\s+(Sleep|Wake|DarkWake)\b")
    for line in manifest["pmset_after"]["stdout"].splitlines():
        if not pattern.match(line):
            continue
        try:
            timestamp = dt.datetime.strptime(line[:25], "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            continue
        if start <= timestamp <= end:
            events.append(line)
    return events


def main() -> None:
    """Write a scope-preserving analysis of the six fixed trace attempts."""
    manifest = json.loads((RESULTS / "manifest.json").read_text())
    records = []
    artifacts: dict[str, dict[str, str]] = {}
    for record in manifest["records"]:
        name = record["name"]
        benchmark = json.loads((RESULTS / f"{name}.stdout.txt").read_text())
        replay = benchmark["repetitions"][0]
        table_rows = {
            schema: row_count(artifact_path(name, f"{schema}.xml"))
            for schema in SCHEMAS
        }
        counter = target_counter_rows(
            artifact_path(name, "CounterMetricByThread.xml"),
            record["variant"],
        )
        bundle = artifact_path(name, "trace")
        artifact_paths = [bundle] + [
            artifact_path(name, f"{schema}.xml")
            for schema in SCHEMAS
            if schema != "OSSignpostIntervals"
        ]
        artifacts[name] = {
            str(path.name): bundle_sha256(path) if path.is_dir() else sha256(path)
            for path in artifact_paths
        }
        records.append(
            {
                "name": name,
                "variant": record["variant"],
                "workload": record["workload"],
                "warmup": record["warmup"],
                "trace_recording_exit_code": record["xctrace"]["exit_code"],
                "trace_tables": table_rows,
                "target_counter_intervals": counter,
                "replay": {
                    "workload_wall_ns": replay["workload_wall_ns"],
                    "setup_ns": replay["setup_ns"],
                    "trace_fingerprint_fnv1a64": benchmark["trace_fingerprint_fnv1a64"],
                },
            }
        )
    analysis = {
        "schema_version": 1,
        "analysis_scope": (
            "Complete process only; no profiler-recognized replay marker was recorded. "
            "No trace-derived metric is replay-scoped."
        ),
        "trace_artifact_root": str(TRACE_ROOT),
        "signpost_intervals_present": False,
        "power": {
            "caffeinate_present_during_each_record": all(
                "caffeinate" in record["during_assertions"]["stdout"]
                for record in manifest["records"]
            ),
            "sleep_or_wake_events_during_collection": sleep_events(manifest),
        },
        "records": records,
        "raw_artifact_sha256": artifacts,
    }
    (RESULTS / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")


if __name__ == "__main__":
    main()
