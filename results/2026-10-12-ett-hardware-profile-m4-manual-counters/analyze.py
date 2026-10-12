#!/usr/bin/env python3
"""Analyze the completed marker-scoped manual-counter campaign."""

from __future__ import annotations

import json
import math
import random
import statistics
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
RAW = Path(
    "/Users/robertotrunfio/.copilot/session-state/"
    "38a24407-0788-43b6-9112-59903987563b/files/"
    "ett-hardware-profile-m4-manual-counters-raw"
)
EVENTS = (
    "FIXED_CYCLES",
    "CORE_ACTIVE_CYCLE",
    "BRANCH_MISPRED_NONSPEC",
    "L1I_CACHE_MISS_DEMAND",
    "INST_ALL",
    "ARM_L1D_CACHE_RD",
    "ARM_L1D_CACHE_LMISS_RD",
    "ARM_STALL_BACKEND",
)
CASES = ("path-fresh", "path-warmed", "dense-warmed")
BOOTSTRAP_DRAWS = 100_000
BOOTSTRAP_SEED = 1012


def percentile(values: list[float], fraction: float) -> float:
    """Return the linearly interpolated percentile of a nonempty sample."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def summary(values: list[float], rng: random.Random) -> dict[str, float | int | list[float]]:
    """Return distribution and fixed-seed bootstrap summaries for paired values."""
    if not values:
        raise ValueError("cannot summarize an empty sample")
    medians = []
    means = []
    for _ in range(BOOTSTRAP_DRAWS):
        draw = [values[rng.randrange(len(values))] for _ in values]
        medians.append(statistics.median(draw))
        means.append(statistics.fmean(draw))
    return {
        "n": len(values),
        "median": statistics.median(values),
        "mean": statistics.fmean(values),
        "iqr": [percentile(values, 0.25), percentile(values, 0.75)],
        "range": [min(values), max(values)],
        "median_bootstrap_95_ci": [percentile(medians, 0.025), percentile(medians, 0.975)],
        "mean_bootstrap_95_ci": [percentile(means, 0.025), percentile(means, 0.975)],
    }


def sign_test_two_sided(faster: int, slower: int) -> float:
    """Return exact two-sided sign-test p-value after excluding ties."""
    total = faster + slower
    if not total:
        return 1.0
    probability = sum(math.comb(total, count) for count in range(0, min(faster, slower) + 1))
    return min(1.0, 2 * probability / 2**total)


def samples(record: dict[str, Any]) -> list[list[int]]:
    """Return valid target-process samples inside measurement-replay."""
    tree = ET.parse(RAW / f"{record['name']}.counters-profile.xml")
    by_id = {field.attrib["id"]: field for field in tree.iter() if "id" in field.attrib}

    def resolve(field: ET.Element[str]) -> ET.Element[str]:
        while "ref" in field.attrib:
            field = by_id[field.attrib["ref"]]
        return field

    marker = next(row for row in record["signpost_rows"] if row["name"] == "measurement-replay")
    start = int(marker["start_ns"])
    end = start + int(marker["duration_ns"])
    selected = []
    for row in tree.iter("row"):
        fields = {field.tag: resolve(field) for field in row}
        if not {"sample-time", "process", "pmc-events"} <= fields.keys():
            continue
        if not fields["process"].attrib.get("fmt", "").startswith(record["variant"] + " "):
            continue
        timestamp = int(fields["sample-time"].text or "0")
        values = [int(value) for value in (fields["pmc-events"].text or "").split()]
        if start <= timestamp <= end and len(values) == 16 and values[:8] == values[8:]:
            selected.append(values[:8])
    return selected


def measurement_duration(record: dict[str, Any]) -> int:
    """Return the primary marker-scoped duration for one record."""
    return int(next(
        row["duration_ns"] for row in record["signpost_rows"]
        if row["name"] == "measurement-replay"
    ))


def main() -> None:
    """Write complete JSON data and a concise engineering report."""
    raw_records: list[dict[str, Any]] = []
    for batch in range(1, 7):
        data = json.loads((RESULTS / f"batch-{batch:02d}.json").read_text())
        if not data["all_markers_valid"]:
            raise RuntimeError(f"batch {batch} has invalid signposts")
        raw_records.extend(data["records"])
    if len(raw_records) != 72:
        raise RuntimeError(f"expected 72 records, found {len(raw_records)}")

    records = []
    for record in raw_records:
        selected = samples(record)
        medians = dict(zip(EVENTS, map(statistics.median, zip(*selected)))) if selected else None
        records.append({
            "name": record["name"],
            "case": record["case"]["name"],
            "trial": int(record["trial"]),
            "variant": record["variant"],
            "marker_duration_ns": measurement_duration(record),
            "counter_sample_count": len(selected),
            "counter_sample_median": medians,
        })

    grouped: dict[tuple[str, int], dict[str, dict[str, Any]]] = defaultdict(dict)
    for record in records:
        grouped[(record["case"], record["trial"])][record["variant"]] = record

    rng = random.Random(BOOTSTRAP_SEED)
    cases = []
    for case in CASES:
        pairs = []
        for trial in range(12):
            variants = grouped[(case, trial)]
            if set(variants) != {"before", "after"}:
                raise RuntimeError(f"incomplete pair: {case} trial {trial}")
            before, after = variants["before"], variants["after"]
            duration_change = 100 * (after["marker_duration_ns"] / before["marker_duration_ns"] - 1)
            pairs.append({
                "trial": trial,
                "before_duration_ns": before["marker_duration_ns"],
                "after_duration_ns": after["marker_duration_ns"],
                "duration_change_percent": duration_change,
                "before_counter_sample_count": before["counter_sample_count"],
                "after_counter_sample_count": after["counter_sample_count"],
            })
        changes = [pair["duration_change_percent"] for pair in pairs]
        faster = sum(change < 0 for change in changes)
        slower = sum(change > 0 for change in changes)
        regressions = [pair for pair in pairs if pair["duration_change_percent"] > 0]
        cases.append({
            "case": case,
            "pairs": pairs,
            "before_duration_median_ns": statistics.median(pair["before_duration_ns"] for pair in pairs),
            "after_duration_median_ns": statistics.median(pair["after_duration_ns"] for pair in pairs),
            "change_of_duration_medians_percent": 100 * (
                statistics.median(pair["after_duration_ns"] for pair in pairs)
                / statistics.median(pair["before_duration_ns"] for pair in pairs) - 1
            ),
            "paired_duration_change_percent": summary(changes, rng),
            "faster_pairs": faster,
            "slower_pairs": slower,
            "exact_two_sided_sign_test_p": sign_test_two_sided(faster, slower),
            "regressions": regressions,
        })

    hardware = []
    for case in CASES:
        case_records = [record for record in records if record["case"] == case]
        missing = [record["name"] for record in case_records if record["counter_sample_median"] is None]
        event_summaries = []
        for event in EVENTS:
            changes = []
            for trial in range(12):
                before = grouped[(case, trial)]["before"]
                after = grouped[(case, trial)]["after"]
                if before["counter_sample_median"] is None or after["counter_sample_median"] is None:
                    continue
                before_value = before["counter_sample_median"][event]
                after_value = after["counter_sample_median"][event]
                if before_value > 0:
                    changes.append(100 * (after_value / before_value - 1))
            event_summaries.append({
                "event": event,
                "complete_pairs": len(changes),
                "paired_per_record_median_sample_change_percent": summary(changes, rng),
            })
        hardware.append({
            "case": case,
            "records_with_counter_samples": sum(record["counter_sample_median"] is not None for record in case_records),
            "missing_counter_records": missing,
            "before_sample_count_distribution": summary(
                [record["counter_sample_count"] for record in case_records if record["variant"] == "before"], rng
            ),
            "after_sample_count_distribution": summary(
                [record["counter_sample_count"] for record in case_records if record["variant"] == "after"], rng
            ),
            "events": event_summaries,
        })

    analysis = {
        "schema_version": 2,
        "primary_metric": "measurement-replay signpost duration",
        "percent_change": "100 * (after / before - 1); negative is faster",
        "bootstrap": {
            "draws": BOOTSTRAP_DRAWS,
            "seed": BOOTSTRAP_SEED,
            "interval": "two-sided percentile 95% confidence interval",
        },
        "events": EVENTS,
        "records": records,
        "performance": cases,
        "hardware_descriptive_only": hardware,
    }
    (RESULTS / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")


if __name__ == "__main__":
    main()
