#!/usr/bin/env python3
"""Pre-specified re-measurement of one hot-path audit cell.

The hot-path audit campaign (`results/hot-path-audit-20261114/`) reported one
marginal confirmed regression: dynamic `compact-bfs` sustained-churn
`connected_total_ns`, +2.14% against an A/A bound of ±2.06%, on a query path
the change set does not modify. Roadmap Feature 0.4.1 requires re-measuring
that cell before the inclusion decision.

Fixed before running (2026-11-15):

- binaries: the exact `knotrel-benchmarks` binaries of that campaign
  (`base`, `cand`, and the byte-identical `aa` copy), verified against the
  sha256 values in its `run/builds/binaries.json`;
- command: the campaign's own `command_for("dynamic", cell)` for
  `compact-bfs` / `sustained-churn-blocks-v1` / 10,000 nodes / 200 rounds;
- schedule: ROUNDS counterbalanced rounds (every order of the three arms
  equally often), one session, 60 s quiet, 5 s between rounds;
- primary metric: `connected_total_ns`; the verdict rule is the campaign's
  (confirmed only if the 95% bootstrap interval excludes zero and the median
  exceeds the A/A bound); `workload_wall_ns`, `link_total_ns` and
  `cut_total_ns` are reported as secondary metrics. No extension.

Usage: python3 scripts/run_hot_path_recheck.py <output-directory>
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_hot_path_audit import (  # noqa: E402
    CampaignError,
    child_env,
    command_for,
    host_metadata,
    repository_state,
    sha256_file,
)
from run_metrics_overhead import schedule  # noqa: E402
from run_p0_aa import host_state, observe_child, validate_host_state  # noqa: E402

SCHEMA = "knotrel-hot-path-recheck-v1"
ARMS = ("base", "cand", "aa")
ROUNDS = 24
CELL = {"kind": "dynamic", "engine": "compact-bfs", "workload": "sustained-churn-blocks-v1",
        "nodes": 10_000, "rounds": 200}
CELL_ID = "dynamic/compact-bfs/sustained-churn-blocks-v1/10000x200"
SOURCE_CAMPAIGN = SCRIPTS_DIR.parent / "results" / "hot-path-audit-20261114"


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("out")
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--quiet-seconds", type=float, default=60.0)
    parser.add_argument("--round-cooldown-seconds", type=float, default=5.0)
    parser.add_argument("--no-host-checks", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve() / "run"
    if out.exists():
        print(f"STOPPED: {out} exists", file=sys.stderr)
        return 1
    out.mkdir(parents=True)

    def log(message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message}"
        print(line, flush=True)
        with (out / "collector.log").open("a") as handle:
            handle.write(line + "\n")

    def check_host(label: str) -> None:
        state = host_state()
        state["label"] = label
        with (out / "host-checks.jsonl").open("a") as handle:
            handle.write(json.dumps(state, sort_keys=True) + "\n")
        if not args.no_host_checks:
            valid, error = validate_host_state(state, enforce_ac=sys.platform == "darwin")
            if not valid:
                raise CampaignError(f"host check failed at {label}: {error}")

    try:
        log(f"collector start: {SCHEMA}")
        recorded = json.loads((SOURCE_CAMPAIGN / "run" / "builds" / "binaries.json").read_text())
        binaries: Dict[str, Dict[str, str]] = {}
        for arm in ARMS:
            path = Path(recorded["paths"][arm]["knotrel-benchmarks"])
            expected = recorded["sha256"][arm]["knotrel-benchmarks"]
            actual = sha256_file(path)
            if actual != expected:
                raise CampaignError(f"{arm} binary {path} sha256 {actual} != recorded {expected}")
            binaries[arm] = {"knotrel-benchmarks": str(path)}
        (out / "provenance.json").write_text(json.dumps({
            "schema": f"{SCHEMA}-provenance",
            "source_campaign": "results/hot-path-audit-20261114",
            "source_manifest_sha256": sha256_file(SOURCE_CAMPAIGN / "manifest.json"),
            "binaries": {arm: {"path": binaries[arm]["knotrel-benchmarks"],
                               "sha256": recorded["sha256"][arm]["knotrel-benchmarks"]} for arm in ARMS},
            "cell": CELL, "cell_id": CELL_ID,
            "knotrel_benchmarks": repository_state(SCRIPTS_DIR.parent),
        }, indent=2, sort_keys=True) + "\n")
        (out / "environment.json").write_text(json.dumps({
            "schema": f"{SCHEMA}-environment", "host": host_metadata("1.100.0"),
            "collector": {"argv": sys.argv, "python": sys.version,
                          "script_sha256": sha256_file(Path(__file__))},
        }, indent=2, sort_keys=True) + "\n")
        entries = schedule(args.rounds, arms=ARMS)
        (out / "schedule.json").write_text(json.dumps({"schema": f"{SCHEMA}-schedule", "entries": entries},
                                                      indent=2, sort_keys=True) + "\n")
        log(f"binaries verified; quiet {args.quiet_seconds}s")
        time.sleep(args.quiet_seconds)
        work = SCRIPTS_DIR.parent / "target-hot-path-audit"
        current = None
        for sequence, entry in enumerate(entries):
            if entry["round"] != current:
                if current is not None:
                    time.sleep(args.round_cooldown_seconds)
                current = entry["round"]
                check_host(f"round-{current}")
                log(f"round {current + 1}/{args.rounds}")
            argv = command_for("dynamic", CELL, binaries[entry["arm"]])
            env = child_env()
            observation = observe_child(argv, cwd=str(work), env=env, timeout_seconds=180.0,
                                        is_core=True, output_limit_bytes=4 * 1024 * 1024)
            stdout_path = out / "raw" / f"{sequence:05d}.stdout"
            stderr_path = out / "raw" / f"{sequence:05d}.stderr"
            stdout_path.parent.mkdir(exist_ok=True)
            stdout_path.write_text(observation["stdout"] or "")
            stderr_path.write_text(observation["raw_stderr"] or "")
            record: Dict[str, Any] = {
                "sequence": sequence, "section": "timed", "kind": "dynamic", "cell": CELL_ID, **entry,
                "argv": argv, "env": env, "exit_code": observation["exit_code"],
                "wall_duration_ns": observation["wall_duration_ns"],
                "failure_reason": observation["failure_reason"],
                "stdout_path": str(stdout_path.relative_to(out)),
                "stderr_path": str(stderr_path.relative_to(out)),
                "stdout_sha256": sha256_file(stdout_path), "stderr_sha256": sha256_file(stderr_path)}
            with (out / "observations.jsonl").open("a") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
            if record["exit_code"] != 0:
                raise CampaignError(f"child failed: {record['failure_reason']}")
        check_host("after")
        (out / "DONE").write_text(json.dumps({"observations": len(entries)}) + "\n")
        log(f"collector complete: {len(entries)} observations")
        return 0
    except (CampaignError, OSError) as error:
        (out / "STOPPED").write_text(f"{type(error).__name__}: {error}\n")
        log(f"STOPPED: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
