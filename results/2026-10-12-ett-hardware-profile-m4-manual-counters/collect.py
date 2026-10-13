#!/usr/bin/env python3
"""Collect one fixed batch of marker-scoped CPU Counters traces."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
VALIDATION = RESULTS.parent / "2026-10-12-ett-signpost-validation-m4"
XCODE = Path("/Applications/Xcode.app/Contents/Developer")
TRACE_ROOT = Path(
    "$SESSION_STATE/"
    "files/"
    "ett-hardware-profile-m4-manual-counters-raw"
)
TEMPLATE = Path("$HOME/Downloads/MyTemplate.tracetemplate")
TEMPLATE_SHA256 = "99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74"


def sha256(path: Path) -> str:
    """Return a SHA-256 digest for one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def bundle_sha256(bundle: Path) -> str:
    """Hash a trace bundle by relative path and content digest."""
    digest = hashlib.sha256()
    for path in sorted(bundle.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(bundle).as_posix().encode() + b"\0")
            digest.update(hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def command_output(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run one short command and retain its output."""
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    return {
        "args": args,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def export(args: list[str], output: Path, env: dict[str, str]) -> dict[str, Any]:
    """Export one trace table to a file without buffering it in memory."""
    with output.open("w") as file:
        result = subprocess.run(
            args,
            env=env,
            stdout=file,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    return {"args": args, "exit_code": result.returncode, "stderr": result.stderr}


def signpost_rows(path: Path, variant: str) -> list[dict[str, int | str]]:
    """Resolve target-process signpost intervals from Instruments XML."""
    tree = element_tree.parse(path)
    by_id = {field.attrib["id"]: field for field in tree.iter() if "id" in field.attrib}

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


def valid_intervals(rows: list[dict[str, int | str]], warmup: int) -> bool:
    """Require the replay intervals that the selected fresh/warmed regime uses."""
    expected = ["warmup-replay", "measurement-replay"] if warmup else ["measurement-replay"]
    if [row["name"] for row in rows] != expected:
        return False
    if not warmup:
        return True
    warmup, measurement = rows
    return int(warmup["start_ns"]) + int(warmup["duration_ns"]) <= int(
        measurement["start_ns"]
    )


def main() -> None:
    """Collect one immutable six-group batch selected by a one-based argument."""
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        raise SystemExit("usage: collect.py BATCH_NUMBER")
    batch_number = int(sys.argv[1])
    plan = json.loads((RESULTS / "plan.json").read_text())
    if not 1 <= batch_number <= len(plan["batches"]):
        raise SystemExit("batch number is outside the fixed plan")
    batch_path = RESULTS / f"batch-{batch_number:02d}.json"
    if batch_path.exists():
        raise RuntimeError("refusing to overwrite a collected batch")
    validation = json.loads((VALIDATION / "analysis.json").read_text())
    if not validation["all_intervals_valid"]:
        raise RuntimeError("safe marker validation did not pass")
    builds = json.loads((VALIDATION / "builds.json").read_text())
    env = dict(os.environ, DEVELOPER_DIR=str(XCODE))
    xctrace = ["xcrun", "xctrace"]
    if sha256(TEMPLATE) != TEMPLATE_SHA256:
        raise RuntimeError("manual CPU Counters template hash changed")
    template_listing = command_output(xctrace + ["list", "templates"], env)
    options = command_output(
        xctrace + ["record", "--template", str(TEMPLATE), "--show-recording-options"],
        env,
    )
    if template_listing["exit_code"] != 0 or options["exit_code"] != 0:
        raise RuntimeError("CPU Counters template is unavailable")
    TRACE_ROOT.mkdir(parents=True, exist_ok=True)
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "batch": batch_number,
        "started_utc": dt.datetime.now(dt.UTC).isoformat(),
        "protocol_sha256": sha256(RESULTS / "protocol.md"),
        "plan_sha256": sha256(RESULTS / "plan.json"),
        "validation_analysis_sha256": sha256(VALIDATION / "analysis.json"),
        "validation_builds_sha256": sha256(VALIDATION / "builds.json"),
        "trace_artifact_root": str(TRACE_ROOT),
        "template": str(TEMPLATE),
        "template_sha256": TEMPLATE_SHA256,
        "xctrace_templates": template_listing,
        "cpu_counters_options": options,
        "records": [],
    }
    for group_index, group in enumerate(plan["batches"][batch_number - 1]):
        case = group["case"]
        for variant in group["order"]:
            binary = Path(builds["variants"][variant]["binary"])
            binary_hash = sha256(binary)
            if binary_hash != builds["variants"][variant]["binary_sha256"]:
                raise RuntimeError(f"binary hash mismatch: {variant}")
            name = f"b{batch_number:02d}-g{group_index:02d}-{case['name']}-t{group['trial']:02d}-{variant}"
            trace = TRACE_ROOT / f"{name}.trace"
            stdout = RESULTS / f"{name}.stdout.txt"
            replay = [
                str(binary),
                "--nodes",
                str(case["nodes"]),
                "--rounds",
                "10",
                "--workload",
                case["workload"],
                "--query-percent",
                str(case["query_percent"]),
                "--engine",
                "ett-scan",
                "--warmup",
                str(case["warmup"]),
                "--repetitions",
                "1",
                "--seed",
                "42",
                "--query-repeats",
                "0",
            ]
            command = xctrace + [
                "record",
                "--template",
                str(TEMPLATE),
                "--output",
                str(trace),
                "--target-stdout",
                str(stdout),
                "--launch",
                "--",
            ] + replay
            started = dt.datetime.now(dt.UTC).isoformat()
            before_assertions = command_output(["pmset", "-g", "assertions"], env)
            with subprocess.Popen(["caffeinate", "-is"], env=env) as inhibitor:
                during_assertions = command_output(["pmset", "-g", "assertions"], env)
                recorded = command_output(command, env)
                inhibitor.terminate()
                inhibitor.wait(timeout=30)
            toc = export(xctrace + ["export", str(trace), "--toc"], RESULTS / f"{name}.toc.xml", env)
            signposts = export(
                xctrace + ["export", str(trace), "--xpath", '//*[@schema="OSSignpostIntervals"]'],
                RESULTS / f"{name}.OSSignpostIntervals.xml",
                env,
            )
            counter_path = TRACE_ROOT / f"{name}.counters-profile.xml"
            counters = export(
                xctrace + ["export", str(trace), "--xpath", '//*[@schema="counters-profile"]'],
                counter_path,
                env,
            )
            metrics_path = TRACE_ROOT / f"{name}.MetricTableForThread.xml"
            metrics = export(
                xctrace + ["export", str(trace), "--xpath", '//*[@schema="MetricTableForThread"]'],
                metrics_path,
                env,
            )
            activity_path = TRACE_ROOT / f"{name}.ThreadActivity.xml"
            activity = export(
                xctrace + ["export", str(trace), "--xpath", '//*[@schema="ThreadActivity"]'],
                activity_path,
                env,
            )
            rows = (
                signpost_rows(RESULTS / f"{name}.OSSignpostIntervals.xml", variant)
                if signposts["exit_code"] == 0
                else []
            )
            metadata["records"].append(
                {
                    "name": name,
                    "group_index": group_index,
                    "case": case,
                    "trial": group["trial"],
                    "variant": variant,
                    "started_utc": started,
                    "binary_sha256": binary_hash,
                    "replay_command": replay,
                    "before_assertions": before_assertions,
                    "during_assertions": during_assertions,
                    "xctrace": recorded,
                    "exports": {
                        "toc": toc,
                        "signposts": signposts,
                        "counters": counters,
                        "metrics": metrics,
                        "activity": activity,
                    },
                    "signpost_rows": rows,
                    "signpost_intervals_valid": valid_intervals(rows, case["warmup"]),
                    "trace_bundle_sha256": bundle_sha256(trace) if trace.exists() else None,
                    "counter_sha256": sha256(counter_path) if counter_path.exists() else None,
                    "metrics_sha256": sha256(metrics_path) if metrics_path.exists() else None,
                    "activity_sha256": sha256(activity_path) if activity_path.exists() else None,
                }
            )
            (RESULTS / f"batch-{batch_number:02d}.partial.json").write_text(
                json.dumps(metadata, indent=2) + "\n"
            )
    metadata["completed_utc"] = dt.datetime.now(dt.UTC).isoformat()
    metadata["power_log"] = command_output(["pmset", "-g", "log"], env)
    metadata["all_markers_valid"] = all(
        record["signpost_intervals_valid"] for record in metadata["records"]
    )
    batch_path.write_text(json.dumps(metadata, indent=2) + "\n")
    (RESULTS / f"batch-{batch_number:02d}.partial.json").unlink()


if __name__ == "__main__":
    main()
