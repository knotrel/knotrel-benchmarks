#!/usr/bin/env python3
"""Create derivative templates and record the fixed manual-counter mapping probe."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import plistlib
import subprocess
from pathlib import Path


RESULTS = Path(__file__).resolve().parent
VALIDATION = RESULTS.parent / "2026-10-12-ett-signpost-validation-m4"
ORIGINAL = Path("/Users/robertotrunfio/Downloads/MyTemplate.tracetemplate")
RAW = Path(
    "/Users/robertotrunfio/.copilot/session-state/"
    "38a24407-0788-43b6-9112-59903987563b/files/ett-manual-counter-mapping-m4"
)
EXPECTED_SHA256 = "99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74"
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


def sha256(path: Path) -> str:
    """Return the SHA-256 of one file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def decode_event(encoded: str) -> str:
    """Extract the mnemonic from one NSKeyedArchiver event payload."""
    decoded = plistlib.loads(base64.b64decode(encoded))
    text = repr(decoded)
    for event in EVENTS:
        if event in text:
            return event
    raise RuntimeError("event payload does not contain a known mnemonic")


def write_options(options: dict[str, object], payloads: list[str], path: Path) -> None:
    """Persist one supported recording-options derivative."""
    copied = json.loads(json.dumps(options))
    counters = copied.get("CPU Counters")
    if not isinstance(counters, dict):
        raise RuntimeError("recording options do not contain CPU Counters")
    counters["allEventsAndFormulas"] = payloads
    path.write_text(json.dumps(copied, indent=2) + "\n")


def run(args: list[str], env: dict[str, str]) -> dict[str, object]:
    """Run a command and retain its reproducibility record."""
    completed = subprocess.run(args, env=env, capture_output=True, text=True, check=False)
    return {
        "args": args,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> None:
    """Create templates and collect the predeclared mapping recordings."""
    if (RESULTS / "manifest.json").exists():
        raise RuntimeError("refusing to overwrite mapping results")
    if sha256(ORIGINAL) != EXPECTED_SHA256:
        raise RuntimeError("original template hash changed")
    env = dict(os.environ, DEVELOPER_DIR="/Applications/Xcode.app/Contents/Developer")
    xctrace = ["xcrun", "xctrace"]
    shown = run(xctrace + ["record", "--template", str(ORIGINAL), "--show-recording-options"], env)
    if shown["exit_code"] != 0:
        raise RuntimeError("original template is not usable by xctrace")
    options = json.loads(str(shown["stdout"]))
    counters = options.get("CPU Counters")
    if not isinstance(counters, dict):
        raise RuntimeError("original template has no CPU Counters options")
    payloads = counters.get("allEventsAndFormulas")
    if not isinstance(payloads, list) or not all(isinstance(item, str) for item in payloads):
        raise RuntimeError("original template has no manual event payloads")
    ordered_events = [decode_event(payload) for payload in payloads]
    if ordered_events != list(EVENTS):
        raise RuntimeError(f"unexpected original event order: {ordered_events}")

    templates = RAW / "recording-options"
    traces = RAW / "traces"
    templates.mkdir(parents=True, exist_ok=True)
    traces.mkdir(parents=True, exist_ok=True)
    variants = [(event, [payloads[index]]) for index, event in enumerate(EVENTS)]
    variants.append(("full-reversed", list(reversed(payloads))))

    builds = json.loads((VALIDATION / "builds.json").read_text())
    binary = Path(builds["variants"]["before"]["binary"])
    if sha256(binary) != builds["variants"]["before"]["binary_sha256"]:
        raise RuntimeError("validated before binary hash changed")
    workload = [
        str(binary), "--nodes", "1000000", "--rounds", "10",
        "--workload", "sustained-churn-path-v1", "--query-percent", "50",
        "--engine", "ett-scan", "--warmup", "1", "--repetitions", "1",
        "--seed", "42", "--query-repeats", "0",
    ]
    records = []
    for name, selected in variants:
        recording_options = templates / f"{name}.json"
        trace = traces / f"{name}.trace"
        write_options(options, selected, recording_options)
        derived = run(
            xctrace + ["record", "--template", str(ORIGINAL),
                       "--recording-options", str(recording_options),
                       "--show-recording-options"],
            env,
        )
        if derived["exit_code"] != 0:
            raise RuntimeError(f"derived recording options rejected: {name}")
        with subprocess.Popen(["caffeinate", "-is"], env=env) as inhibitor:
            recording = run(
                xctrace + ["record", "--template", str(ORIGINAL),
                            "--recording-options", str(recording_options), "--output", str(trace),
                            "--launch", "--"] + workload,
                env,
            )
            inhibitor.terminate()
            inhibitor.wait(timeout=30)
        if recording["exit_code"] != 0:
            raise RuntimeError(f"recording failed: {name}")
        export = run(
            xctrace + ["export", str(trace), "--xpath",
                       '/trace-toc/run/data/table[@schema="counters-profile"]'],
            env,
        )
        if export["exit_code"] != 0:
            raise RuntimeError(f"counter export failed: {name}")
        (RESULTS / f"{name}.counters-profile.xml").write_text(str(export["stdout"]))
        records.append({
            "name": name, "events": [decode_event(payload) for payload in selected],
            "recording_options": str(recording_options),
            "recording_options_sha256": sha256(recording_options),
            "trace": str(trace), "recording": recording, "export": export,
        })
    (RESULTS / "manifest.json").write_text(json.dumps({
        "original_template": str(ORIGINAL), "original_template_sha256": EXPECTED_SHA256,
        "original_event_order": ordered_events, "binary": str(binary),
        "binary_sha256": builds["variants"]["before"]["binary_sha256"],
        "workload": workload, "records": records,
    }, indent=2) + "\n")


if __name__ == "__main__":
    main()
