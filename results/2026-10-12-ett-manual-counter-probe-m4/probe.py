#!/usr/bin/env python3
"""Record the fixed manual-counter export probe without changing production."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


RESULTS = Path(__file__).resolve().parent
VALIDATION = RESULTS.parent / "2026-10-12-ett-signpost-validation-m4"
TEMPLATE = Path("$HOME/Downloads/MyTemplate.tracetemplate")
RAW = Path(
    "$SESSION_STATE/"
    "files/ett-manual-counter-probe-m4"
)
EXPECTED_TEMPLATE_SHA256 = "99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74"


def sha256(path: Path) -> str:
    """Return one file's SHA-256 digest."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def output(args: list[str], env: dict[str, str]) -> dict[str, object]:
    """Run one command and retain its text output."""
    run = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    return {"args": args, "exit_code": run.returncode, "stdout": run.stdout, "stderr": run.stderr}


def main() -> None:
    """Run exactly the protocol's before and after warmed-path recordings."""
    if (RESULTS / "manifest.json").exists():
        raise RuntimeError("refusing to overwrite probe results")
    if sha256(TEMPLATE) != EXPECTED_TEMPLATE_SHA256:
        raise RuntimeError("manual template hash changed")
    validation = json.loads((VALIDATION / "builds.json").read_text())
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    xctrace = ["xcrun", "xctrace"]
    options = output(xctrace + ["record", "--template", str(TEMPLATE), "--show-recording-options"], env)
    if options["exit_code"] != 0:
        raise RuntimeError("manual template is not usable by xctrace")
    RAW.mkdir(parents=True, exist_ok=True)
    records = []
    for variant in ("before", "after"):
        binary = Path(validation["variants"][variant]["binary"])
        if sha256(binary) != validation["variants"][variant]["binary_sha256"]:
            raise RuntimeError(f"binary hash mismatch: {variant}")
        name = f"path-warmed-{variant}"
        trace = RAW / f"{name}.trace"
        stdout = RESULTS / f"{name}.stdout.txt"
        command = [
            str(binary), "--nodes", "1000000", "--rounds", "10",
            "--workload", "sustained-churn-path-v1", "--query-percent", "50",
            "--engine", "ett-scan", "--warmup", "1", "--repetitions", "1",
            "--seed", "42", "--query-repeats", "0",
        ]
        with subprocess.Popen(["caffeinate", "-is"], env=env) as inhibitor:
            recorded = output(
                xctrace + ["record", "--template", str(TEMPLATE), "--output", str(trace),
                            "--target-stdout", str(stdout), "--launch", "--"] + command,
                env,
            )
            inhibitor.terminate()
            inhibitor.wait(timeout=30)
        toc = output(xctrace + ["export", str(trace), "--toc"], env)
        (RESULTS / f"{name}.toc.xml").write_text(str(toc["stdout"]))
        records.append({"variant": variant, "command": command, "xctrace": recorded, "toc": toc})
    (RESULTS / "manifest.json").write_text(json.dumps({
        "template": str(TEMPLATE), "template_sha256": EXPECTED_TEMPLATE_SHA256,
        "recording_options": options, "raw_root": str(RAW), "records": records,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
