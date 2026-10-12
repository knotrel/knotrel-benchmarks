#!/usr/bin/env python3
"""Record the fixed six-trace whole-process Instruments feasibility campaign."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
XCODE = Path("/Applications/Xcode.app/Contents/Developer")


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_output(args: list[str], env: dict[str, str]) -> dict[str, Any]:
    """Run a command without suppressing either output stream."""
    result = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    return {
        "args": args,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


def main() -> None:
    """Collect the predeclared traces without overwriting prior results."""
    if (RESULTS / "manifest.json").exists():
        raise RuntimeError("refusing to overwrite an existing collection manifest")
    builds = json.loads((RESULTS / "builds.json").read_text())
    env = dict(os.environ, DEVELOPER_DIR=str(XCODE))
    xctrace = ["xcrun", "xctrace"]
    template_listing = command_output(xctrace + ["list", "templates"], env)
    options = command_output(
        xctrace + ["record", "--template", "CPU Counters", "--show-recording-options"],
        env,
    )
    if template_listing["exit_code"] != 0 or options["exit_code"] != 0:
        raise RuntimeError("CPU Counters template is not available")

    plan = [
        ("01-path-fresh-before", "before", "sustained-churn-path-v1", 1_000_000, 50, 0),
        ("02-path-fresh-after", "after", "sustained-churn-path-v1", 1_000_000, 50, 0),
        ("03-path-warmed-after", "after", "sustained-churn-path-v1", 1_000_000, 50, 1),
        ("04-path-warmed-before", "before", "sustained-churn-path-v1", 1_000_000, 50, 1),
        ("05-dense-warmed-before", "before", "dense-bridge-churn-v1", 512, 90, 1),
        ("06-dense-warmed-after", "after", "dense-bridge-churn-v1", 512, 90, 1),
    ]
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "started_utc": dt.datetime.now(dt.UTC).isoformat(),
        "protocol_sha256": sha256(RESULTS / "protocol.md"),
        "builds_sha256": sha256(RESULTS / "builds.json"),
        "xctrace_templates": template_listing,
        "cpu_counters_recording_options": options,
        "records": [],
    }
    (RESULTS / "pmset-before.txt").write_text(
        subprocess.check_output(["pmset", "-g", "log"], text=True)
    )

    for name, variant, workload, nodes, query_percent, warmup in plan:
        binary = Path(builds["variants"][variant]["binary"])
        binary_hash = sha256(binary)
        if binary_hash != builds["variants"][variant]["binary_sha256"]:
            raise RuntimeError(f"binary hash mismatch for {name}")
        trace = RESULTS / f"{name}.trace"
        stdout = RESULTS / f"{name}.stdout.txt"
        replay = [
            str(binary),
            "--nodes",
            str(nodes),
            "--rounds",
            "10",
            "--workload",
            workload,
            "--query-percent",
            str(query_percent),
            "--engine",
            "ett-scan",
            "--warmup",
            str(warmup),
            "--repetitions",
            "1",
            "--seed",
            "42",
            "--query-repeats",
            "0",
        ]
        assertions = command_output(["pmset", "-g", "assertions"], env)
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
        started = dt.datetime.now(dt.UTC).isoformat()
        with subprocess.Popen(["caffeinate", "-is"], env=env) as inhibitor:
            during = command_output(["pmset", "-g", "assertions"], env)
            result = command_output(command, env)
            inhibitor.terminate()
            inhibitor.wait(timeout=30)
        toc = (
            command_output(xctrace + ["export", str(trace), "--toc"], env)
            if trace.exists()
            else None
        )
        if toc is not None:
            (RESULTS / f"{name}.toc.xml").write_text(toc["stdout"])
        metadata["records"].append(
            {
                "name": name,
                "variant": variant,
                "workload": workload,
                "nodes": nodes,
                "query_percent": query_percent,
                "warmup": warmup,
                "started_utc": started,
                "binary": str(binary),
                "binary_sha256": binary_hash,
                "replay_command": replay,
                "before_assertions": assertions,
                "during_assertions": during,
                "xctrace": result,
                "trace_present": trace.exists(),
                "trace_toc": toc,
            }
        )
        (RESULTS / "manifest.partial.json").write_text(
            json.dumps(metadata, indent=2) + "\n"
        )

    metadata["completed_utc"] = dt.datetime.now(dt.UTC).isoformat()
    metadata["pmset_after"] = command_output(["pmset", "-g", "log"], env)
    metadata["artifact_sha256"] = {
        path.name: sha256(path)
        for path in RESULTS.iterdir()
        if path.is_file() and path.name not in {"manifest.json", "manifest.partial.json"}
    }
    (RESULTS / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (RESULTS / "manifest.partial.json").unlink()


if __name__ == "__main__":
    main()
