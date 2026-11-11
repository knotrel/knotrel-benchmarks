#!/usr/bin/env python3
"""Tests for the Candidate A vs Baseline comparison runner."""

import json
import copy
from pathlib import Path
import sys
import pytest

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_candidate_a_comparison import (
    CELL_DEFINITIONS,
    build_command_args,
    generate_schedule,
    parse_core_report,
)


def test_schedule_generation_balance_and_reproducibility():
    schedule1 = generate_schedule(CELL_DEFINITIONS, sessions_count=3)
    schedule2 = generate_schedule(CELL_DEFINITIONS, sessions_count=3)

    assert schedule1 == schedule2
    assert schedule1["total_pairs"] == 36
    assert schedule1["total_invocations"] == 72
    assert len(schedule1["sessions"]) == 3

    b_first_count = 0
    c_first_count = 0
    cell_counts = {}

    for s in schedule1["sessions"]:
        assert len(s["pairs"]) == 12
        for p in s["pairs"]:
            if p["order"] == "B_first":
                b_first_count += 1
            elif p["order"] == "C_first":
                c_first_count += 1
            cell_counts[p["cell_id"]] = cell_counts.get(p["cell_id"], 0) + 1

    assert b_first_count == 18
    assert c_first_count == 18
    assert len(cell_counts) == 6
    for cell_id, cnt in cell_counts.items():
        assert cnt == 6  # 6 pairs per cell across 3 sessions


def test_build_command_args_mapping():
    cell_blocks = CELL_DEFINITIONS[0]
    args = build_command_args("/path/to/bin", cell_blocks, repetitions=3, warmup=1)
    assert args == [
        "/path/to/bin",
        "--workload", "sustained-churn-blocks-v1",
        "--nodes", "10000",
        "--rounds", "200",
        "--seed", "42",
        "--warmup", "1",
        "--repetitions", "3",
        "--engine", "compact-bfs",
        "--query-percent", "10",
    ]

    cell_chain = CELL_DEFINITIONS[1]
    args_chain = build_command_args("/path/to/bin", cell_chain, repetitions=3, warmup=1)
    assert "--query-percent" not in args_chain
    assert args_chain[args_chain.index("--workload") + 1] == "chain-split-rejoin-v1"


def valid_core_report():
    cell = CELL_DEFINITIONS[0]
    def latency(count, duration):
        return {"count": count, "total_ns": count * duration,
                "min_ns": duration, "p50_ns": duration, "p95_ns": duration,
                "p99_ns": duration, "max_ns": duration}
    return {
        "schema_version": 2,
        "engine": "knotrel-core/compact-bfs-v1",
        "workload": "sustained-churn-blocks-v1",
        "config": {"nodes": 10000, "rounds": 200, "seed": 42},
        "warmup": 1,
        "query_repeats": 0,
        "query_percent": 10,
        "trace_fingerprint_fnv1a64": cell["expected_fingerprint"],
        "repetitions": [
            {
                "workload_wall_ns": 1500000,
                "setup_ns": 200000,
                "measurements": {
                    "cut": latency(9308, 40),
                    "link": latency(8692, 40),
                    "connected": latency(2000, 400),
                },
                "query_true": latency(1000, 400),
                "query_false": latency(1000, 400),
                "repeated_queries": None,
            }
            for _ in range(3)
        ],
    }


def test_parse_core_report_validation():
    cell = CELL_DEFINITIONS[0]
    valid_report = valid_core_report()
    parsed = parse_core_report(json.dumps(valid_report), cell)
    assert parsed["status"] == "parsed_valid"
    assert parsed["workload_wall_ns_median"] == 1500000
    assert parsed["link_p50_ns_median"] == 40

    # Fingerprint mismatch rejection
    invalid_fp = dict(valid_report)
    invalid_fp["trace_fingerprint_fnv1a64"] = "0000000000000000"
    with pytest.raises(ValueError, match="Trace fingerprint mismatch"):
        parse_core_report(json.dumps(invalid_fp), cell)

    # Missing counts rejection
    invalid_counts = copy.deepcopy(valid_report)
    invalid_counts["repetitions"][0]["measurements"]["link"]["count"] = 8690
    with pytest.raises(ValueError, match="count mismatch"):
        parse_core_report(json.dumps(invalid_counts), cell)


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("path,value", [
    (("measurements", "link", "count"), 8690),
    (("measurements", "cut", "count"), True),
    (("workload_wall_ns",), 0),
    (("workload_wall_ns",), float("inf")),
    (("setup_ns",), -1),
    (("setup_ns",), "200000"),
    (("measurements", "connected", "p95_ns"), None),
    (("measurements", "link", "p50_ns"), float("nan")),
    (("measurements", "link", "max_ns"), 0),
    (("measurements", "link", "total_ns"), -1),
    (("query_true", "count"), 999),
    (("query_false", "total_ns"), 399999),
    (("repeated_queries",), {}),
])
def test_rejects_invalid_data_in_every_repetition(index, path, value):
    report = valid_core_report()
    target = report["repetitions"][index]
    for name in path[:-1]:
        target = target[name]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        parse_core_report(json.dumps(report), CELL_DEFINITIONS[0])


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("field", ["total_ns", "min_ns", "p50_ns", "p95_ns", "p99_ns", "max_ns"])
def test_rejects_missing_latency_fields_in_later_repetitions(index, field):
    report = valid_core_report()
    del report["repetitions"][index]["measurements"]["link"][field]
    with pytest.raises(ValueError):
        parse_core_report(json.dumps(report), CELL_DEFINITIONS[0])


@pytest.mark.parametrize("field,value", [
    ("schema_version", 3), ("schema_version", True),
    ("engine", "other"), ("workload", "other"), ("config", {}),
    ("config", {"nodes": True, "rounds": 200, "seed": 42}),
    ("query_percent", 90), ("warmup", 0), ("query_repeats", 1),
    ("repetitions", {}),
])
def test_rejects_report_identity_and_protocol_mismatch(field, value):
    report = valid_core_report()
    report[field] = value
    with pytest.raises(ValueError):
        parse_core_report(json.dumps(report), CELL_DEFINITIONS[0])


def test_rejects_duplicate_json_keys():
    text = json.dumps(valid_core_report()).replace('"setup_ns": 200000',
                                                  '"setup_ns": 200000, "setup_ns": 1', 1)
    with pytest.raises(ValueError, match="Duplicate JSON field"):
        parse_core_report(text, CELL_DEFINITIONS[0])


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("field", ["query_true", "query_false", "repeated_queries", "setup_ns"])
def test_rejects_missing_schema_fields_in_later_repetitions(index, field):
    report = valid_core_report()
    del report["repetitions"][index][field]
    with pytest.raises(ValueError):
        parse_core_report(json.dumps(report), CELL_DEFINITIONS[0])
