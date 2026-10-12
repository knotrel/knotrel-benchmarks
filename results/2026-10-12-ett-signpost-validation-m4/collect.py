#!/usr/bin/env python3
"""Collect and validate the two fixed replay-signpost trace attempts."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as element_tree
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
XCODE = Path("/Applications/Xcode.app/Contents/Developer")


def sha256(path: Path) -> str:
    """Return a SHA-256 digest for one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_output(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run one command and retain both output streams."""
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    return {
        "args": args,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def signpost_rows(path: Path, variant: str) -> list[dict[str, int | str]]:
    """Read target-process interval rows from an exported Instruments table."""
    tree = element_tree.parse(path)
    by_id = {
        field.attrib["id"]: field
        for field in tree.iter()
        if "id" in field.attrib
    }

    def value(field: element_tree.Element[str]) -> element_tree.Element[str]:
        """Resolve Instruments' XML reference nodes to their source field."""
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
            }
        )
    return rows


def valid_intervals(rows: list[dict[str, int | str]]) -> bool:
    """Require one ordered non-overlapping warmup and measurement interval."""
    expected = ["warmup-replay", "measurement-replay"]
    if [row["name"] for row in rows] != expected:
        return False
    warmup, measurement = rows
    return int(warmup["start_ns"]) + int(warmup["duration_ns"]) <= int(
        measurement["start_ns"]
    )


def main() -> None:
    """Run the fixed marker-validation budget once without overwriting results."""
    if (RESULTS / "manifest.json").exists():
        raise RuntimeError("refusing to overwrite existing marker validation")
    builds = json.loads((RESULTS / "builds.json").read_text())
    env = dict(os.environ, DEVELOPER_DIR=str(XCODE))
    xctrace = ["xcrun", "xctrace"]
    if command_output(xctrace + ["list", "templates"], env)["exit_code"] != 0:
        raise RuntimeError("xctrace templates are unavailable")
    plan = [("01-before", "before"), ("02-after", "after")]
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "started_utc": dt.datetime.now(dt.UTC).isoformat(),
        "protocol_sha256": sha256(RESULTS / "protocol.md"),
        "builds_sha256": sha256(RESULTS / "builds.json"),
        "records": [],
    }
    for name, variant in plan:
        binary = Path(builds["variants"][variant]["binary"])
        if sha256(binary) != builds["variants"][variant]["binary_sha256"]:
            raise RuntimeError(f"binary hash mismatch: {variant}")
        trace = RESULTS / f"{name}.trace"
        stdout = RESULTS / f"{name}.stdout.txt"
        replay = [
            str(binary),
            "--nodes",
            "1000000",
            "--rounds",
            "10",
            "--workload",
            "sustained-churn-path-v1",
            "--query-percent",
            "50",
            "--engine",
            "ett-scan",
            "--warmup",
            "1",
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
            "CPU Counters",
            "--output",
            str(trace),
            "--target-stdout",
            str(stdout),
            "--launch",
            "--",
        ] + replay
        before_assertions = command_output(["pmset", "-g", "assertions"], env)
        with subprocess.Popen(["caffeinate", "-is"], env=env) as inhibitor:
            during_assertions = command_output(["pmset", "-g", "assertions"], env)
            result = command_output(command, env)
            inhibitor.terminate()
            inhibitor.wait(timeout=30)
        toc = command_output(xctrace + ["export", str(trace), "--toc"], env)
        signposts = command_output(
            xctrace + ["export", str(trace), "--xpath", '//*[@schema="OSSignpostIntervals"]'],
            env,
        )
        (RESULTS / f"{name}.toc.xml").write_text(toc["stdout"])
        signpost_path = RESULTS / f"{name}.OSSignpostIntervals.xml"
        signpost_path.write_text(signposts["stdout"])
        rows = signpost_rows(signpost_path, variant) if signposts["exit_code"] == 0 else []
        metadata["records"].append(
            {
                "name": name,
                "variant": variant,
                "binary_sha256": sha256(binary),
                "replay_command": replay,
                "before_assertions": before_assertions,
                "during_assertions": during_assertions,
                "xctrace": result,
                "trace_toc": toc,
                "signpost_export": signposts,
                "signpost_rows": rows,
                "signpost_intervals_valid": valid_intervals(rows),
            }
        )
        (RESULTS / "manifest.partial.json").write_text(
            json.dumps(metadata, indent=2) + "\n"
        )
    metadata["completed_utc"] = dt.datetime.now(dt.UTC).isoformat()
    metadata["power_log"] = command_output(["pmset", "-g", "log"], env)
    metadata["all_intervals_valid"] = all(
        record["signpost_intervals_valid"] for record in metadata["records"]
    )
    metadata["artifact_sha256"] = {
        path.name: sha256(path)
        for path in RESULTS.iterdir()
        if path.is_file() and path.name not in {"manifest.json", "manifest.partial.json"}
    }
    (RESULTS / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (RESULTS / "manifest.partial.json").unlink()
    if not metadata["all_intervals_valid"]:
        raise RuntimeError("marker validation failed; no retry permitted")


if __name__ == "__main__":
    main()
