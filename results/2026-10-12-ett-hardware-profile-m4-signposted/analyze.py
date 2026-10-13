#!/usr/bin/env python3
"""Analyze fixed marker-scoped ETT CPU Counters records."""

from __future__ import annotations

import datetime as dt
import json
import statistics
import xml.etree.ElementTree as element_tree
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
TRACE_ROOT = Path(
    "$SESSION_STATE/"
    "files/"
    "ett-hardware-profile-m4-signposted-raw"
)


def resolved_rows(path: Path, variant: str) -> list[dict[str, element_tree.Element[str]]]:
    """Resolve Instruments XML references for rows owned by the target process."""
    tree = element_tree.parse(path)
    by_id = {field.attrib["id"]: field for field in tree.iter() if "id" in field.attrib}

    def value(field: element_tree.Element[str]) -> element_tree.Element[str]:
        while "ref" in field.attrib:
            field = by_id[field.attrib["ref"]]
        return field

    result = []
    for row in tree.iter("row"):
        fields = {field.tag: value(field) for field in row}
        process = fields.get("process")
        if process is not None and process.attrib.get("fmt", "").startswith(f"{variant} "):
            result.append(fields)
    return result


def signposts(path: Path, variant: str, warmup: int) -> dict[str, Any]:
    """Extract and validate the fresh/warmed signpost sequence."""
    rows = resolved_rows(path, variant)
    intervals = [
        {
            "name": fields["signpost-name"].text or "",
            "start_ns": int(fields["start-time"].text or "0"),
            "duration_ns": int(fields["duration"].text or "0"),
        }
        for fields in rows
    ]
    expected = ["warmup-replay", "measurement-replay"] if warmup else ["measurement-replay"]
    valid = [row["name"] for row in intervals] == expected
    if warmup and valid:
        warmup_interval, measurement = intervals
        valid = (
            warmup_interval["start_ns"] + warmup_interval["duration_ns"]
            <= measurement["start_ns"]
        )
    measurement = next(
        (row for row in intervals if row["name"] == "measurement-replay"),
        None,
    )
    return {"valid": valid, "intervals": intervals, "measurement": measurement}


def overlaps(
    start_ns: int,
    duration_ns: int,
    interval: dict[str, int],
) -> bool:
    """Return whether two half-open monotonic time intervals overlap."""
    return start_ns < interval["start_ns"] + interval["duration_ns"] and interval["start_ns"] < start_ns + duration_ns


def counter_summary(path: Path, variant: str, measurement: dict[str, int] | None) -> dict[str, Any]:
    """Summarize only counter rows that overlap the marked measurement replay."""
    if measurement is None:
        return {"replay_scoped": False, "rows": 0, "duration_ns": 0, "core_samples": {}}
    selected = []
    for fields in resolved_rows(path, variant):
        if "start-time" not in fields or "duration" not in fields or "core" not in fields:
            continue
        start_ns = int(fields["start-time"].text or "0")
        duration_ns = int(fields["duration"].text or "0")
        if overlaps(start_ns, duration_ns, measurement):
            selected.append((start_ns, duration_ns, fields["core"].attrib.get("fmt", "unknown")))
    selected.sort()
    cores = Counter(core for _, _, core in selected)
    migrations = sum(
        previous[2] != current[2] for previous, current in zip(selected, selected[1:])
    )
    return {
        "replay_scoped": True,
        "rows": len(selected),
        "duration_ns": sum(duration for _, duration, _ in selected),
        "core_samples": dict(sorted(cores.items())),
        "observed_core_transitions": migrations,
    }


def median(values: list[float]) -> float:
    """Return one median while retaining all source values elsewhere."""
    return float(statistics.median(values))


def main() -> None:
    """Write distributions, pairs, marker validity, and scoped sample counts."""
    plan = json.loads((RESULTS / "plan.json").read_text())
    batches = [json.loads((RESULTS / f"batch-{index:02d}.json").read_text()) for index in range(1, 7)]
    records = []
    sleep_events = []
    for batch in batches:
        start = dt.datetime.fromisoformat(batch["started_utc"]).astimezone()
        end = dt.datetime.fromisoformat(batch["completed_utc"]).astimezone()
        for line in batch["power_log"]["stdout"].splitlines():
            if not line.startswith("2026-10-12 "):
                continue
            try:
                timestamp = dt.datetime.strptime(line[:25], "%Y-%m-%d %H:%M:%S %z")
            except ValueError:
                continue
            if start <= timestamp <= end and any(
                label in line.split()[3:4] for label in ("Sleep", "Wake", "DarkWake")
            ):
                sleep_events.append(line)
        for record in batch["records"]:
            marker = signposts(
                RESULTS / f"{record['name']}.OSSignpostIntervals.xml",
                record["variant"],
                record["case"]["warmup"],
            )
            benchmark = json.loads((RESULTS / f"{record['name']}.stdout.txt").read_text())
            counter = counter_summary(
                TRACE_ROOT / f"{record['name']}.CounterMetricByThread.xml",
                record["variant"],
                marker["measurement"],
            )
            records.append(
                {
                    "name": record["name"],
                    "case": record["case"]["name"],
                    "trial": record["trial"],
                    "variant": record["variant"],
                    "xctrace_exit_code": record["xctrace"]["exit_code"],
                    "caffeinate_present": "caffeinate"
                    in record["during_assertions"]["stdout"],
                    "markers": marker,
                    "workload_wall_ns": benchmark["repetitions"][0]["workload_wall_ns"],
                    "counter": counter,
                    "trace_bundle_sha256": record["trace_bundle_sha256"],
                    "counter_sha256": record["counter_sha256"],
                }
            )
    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        grouped[(record["case"], record["trial"])][record["variant"]] = record
    case_rows = []
    for case in ("path-fresh", "path-warmed", "dense-warmed"):
        pairs = []
        for trial in range(12):
            variants = grouped[(case, trial)]
            before, after = variants["before"], variants["after"]
            pairs.append(
                {
                    "trial": trial,
                    "before_wall_ns": before["workload_wall_ns"],
                    "after_wall_ns": after["workload_wall_ns"],
                    "wall_change_percent": 100
                    * (after["workload_wall_ns"] / before["workload_wall_ns"] - 1),
                    "before_measurement_marker_ns": before["markers"]["measurement"]["duration_ns"],
                    "after_measurement_marker_ns": after["markers"]["measurement"]["duration_ns"],
                    "before_counter_rows": before["counter"]["rows"],
                    "after_counter_rows": after["counter"]["rows"],
                    "before_core_samples": before["counter"]["core_samples"],
                    "after_core_samples": after["counter"]["core_samples"],
                }
            )
        case_rows.append(
            {
                "case": case,
                "pairs": pairs,
                "before_wall_median_ns": median([pair["before_wall_ns"] for pair in pairs]),
                "after_wall_median_ns": median([pair["after_wall_ns"] for pair in pairs]),
                "median_paired_wall_change_percent": median(
                    [pair["wall_change_percent"] for pair in pairs]
                ),
                "faster_pairs": sum(pair["wall_change_percent"] < 0 for pair in pairs),
                "marker_valid_records": sum(
                    record["markers"]["valid"] and record["xctrace_exit_code"] == 0
                    for record in records
                    if record["case"] == case
                ),
                "counter_rows_per_record": {
                    variant: [
                        record["counter"]["rows"]
                        for record in records
                        if record["case"] == case and record["variant"] == variant
                    ]
                    for variant in ("before", "after")
                },
            }
        )
    analysis = {
        "schema_version": 1,
        "plan_sha256": plan["protocol_sha256"],
        "trace_artifact_root": str(TRACE_ROOT),
        "records": records,
        "cases": case_rows,
        "all_xctrace_success": all(record["xctrace_exit_code"] == 0 for record in records),
        "all_markers_valid": all(record["markers"]["valid"] for record in records),
        "all_caffeinate_present": all(record["caffeinate_present"] for record in records),
        "sleep_or_wake_events": sleep_events,
        "scope_note": (
            "Counter summaries contain only target-process CounterMetricByThread "
            "rows overlapping measurement-replay. Raw arrays are retained; no "
            "metric name or causal interpretation is inferred without an exported "
            "counter definition."
        ),
    }
    (RESULTS / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")


if __name__ == "__main__":
    main()
