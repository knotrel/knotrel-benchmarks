#!/usr/bin/env python3
"""CF5 runner (knotrel ``docs/releases/v1.1.0-cf5-qualification-plan.md``, sections 2, 5, 8-10).

    run_cf5.py --matrix M --tools T --out DIR [--session 2 --resume-from DIR1]
    run_cf5.py --matrix M --tools T --out DIR --preparatory [--pairs N] [--warmup N]
               [--blocks B,..] [--cells-per-block K] [--cap-hours H] [--order-seed S]

Output in DIR:

- ``record.json``, written **before** the first observation: matrix SHA-256, tool map,
  SHA-256 of every executable it names, checkout SHAs and lockfile hashes (tool map keys
  ``_checkouts`` and ``_lockfiles``), host description, the derived order seed, session;
- ``schedule.json``: the frozen order (smoke, then tiers and blocks in priority order, pairs
  interleaved within each block);
- ``raw.jsonl``: every observation with the full selected output object, SHA-256 of
  stdout, stderr tail, wall time; a failed observation is recorded too;
- ``smoke.jsonl``: the tier-1 correctness smoke (one ``--verify`` observation per distinct
  arm; deterministic arms twice, compared);
- ``status.json``: per cell COMPLETE, INCOMPLETE (pairs done), NOT_RUN, FAILED, or for
  delegated cells DELEGATED_DONE / DELEGATED_FAILED / NOT_RUN; the campaign state
  (complete, incomplete, failed) and host snapshots per block. Always written, also after a
  crash or an interruption.

Rules:

- **Order seed:** derived from the matrix SHA-256 and the candidate checkout SHA, so it
  cannot be chosen; ``--order-seed`` exists only with ``--preparatory``.
- **Pairs:** 2 warmup and 24 measured pairs per paired cell, a fresh process per
  observation, exactly half the measured pairs CF first; pairs are interleaved **within a
  block**, and blocks run in the matrix's priority order, so a cap cuts the last blocks.
- **Cap:** no step starts after the cap (smoke and delegated collectors included); the pair
  in progress completes.
- **Correctness gate:** a non-zero exit, unparsable output or a failed check (cell-level
  ``check``, arm-level ``checks``, trace identity) stops the campaign. A timeout or a
  missing binary is an infrastructure failure: the observation is retried once, then the
  campaign stops.
- **Second session:** only after a session 1 that is not failed, within 14 days, with the
  same matrix and binaries; exactly the INCOMPLETE and NOT_RUN cells, from scratch, in
  session 1's schedule order restricted to them; complete cells are never repeated.
- **Preparatory mode:** marked in every file; the analyzer refuses it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

PAIRS = 24
WARMUP = 2
OBSERVATION_TIMEOUT_S = 3_600
SECOND_SESSION_DAYS = 14


class GateFailure(Exception):
    """A correctness-gate failure: the campaign stops. ``args[0]`` is the cell id."""


class InfrastructureFailure(Exception):
    """A timeout or a missing executable: retried once."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


def dig(value: Any, path: str) -> Any:
    for part in path.split("."):
        value = value[int(part)] if isinstance(value, list) else value[part]
    return value


def json_objects(stdout: str) -> List[Dict[str, Any]]:
    objects = []
    for text in stdout.splitlines():
        text = text.strip()
        if text.startswith("{"):
            objects.append(json.loads(text))
    return objects


def select_line(stdout: str, line: str) -> Dict[str, Any]:
    """The JSON object an arm's ``line`` selector names: ``whole``, ``last``, ``kind=X``, or
    ``derive=churn_memory`` (the v1.0.0 Rmem churn metrics, derived from all lines)."""
    if line == "whole":
        return json.loads(stdout)
    objects = json_objects(stdout)
    if line == "last":
        if not objects:
            raise ValueError("no JSON line")
        return objects[-1]
    if line == "derive=churn_memory":
        # The v1.0.0 Rmem derivation (analyze_v060_qualification.churn_memory), with its
        # check that every checkpoint's logical counts equal the model's.
        import analyze_v060_qualification as v060
        try:
            return v060.churn_memory(objects)
        except v060.AnalysisError as error:
            raise ValueError(str(error)) from error
    if line.startswith("kind="):
        kind = line.split("=", 1)[1]
        for obj in objects:
            if obj.get("kind") == kind:
                return obj
        raise ValueError(f"no JSON line of kind {kind}")
    raise ValueError(f"unknown line selector {line}")


def argv_for(arm: Dict[str, Any], tools: Dict[str, Any], scratch: Path,
             extra: Optional[List[str]] = None) -> List[str]:
    if arm["tool"] not in tools:
        raise InfrastructureFailure(f"tool {arm['tool']} is not in the tool map")
    args = list(arm["args"])
    if "--configs-json" in args:
        i = args.index("--configs-json")
        path = scratch / f"configs-{hashlib.sha1(args[i + 1].encode()).hexdigest()[:12]}.jsonl"
        path.write_text(args[i + 1] + "\n")
        args[i:i + 2] = ["--configs", str(path)]
    return list(tools[arm["tool"]]) + args + list(extra or [])


def run_arm(cell: Dict[str, Any], arm_name: str, tools: Dict[str, Any], scratch: Path,
            extra: Optional[List[str]] = None) -> Dict[str, Any]:
    """Runs one arm once and applies every check. Returns the observation record; raises
    GateFailure or InfrastructureFailure."""
    arm = cell["arms"][arm_name]
    argv = argv_for(arm, tools, scratch, extra)
    start = time.monotonic()
    try:
        done = subprocess.run(argv, capture_output=True, text=True,
                              timeout=OBSERVATION_TIMEOUT_S)
    except subprocess.TimeoutExpired as error:
        raise InfrastructureFailure(f"{cell['id']} {arm_name}: timeout") from error
    except OSError as error:
        raise InfrastructureFailure(f"{cell['id']} {arm_name}: {error}") from error
    record: Dict[str, Any] = {"arm": arm_name, "argv": argv, "exit": done.returncode,
                              "wall_s": time.monotonic() - start,
                              "stdout_sha256": sha256_bytes(done.stdout.encode()),
                              "stderr_tail": done.stderr[-2000:]}
    try:
        if done.returncode != 0:
            raise GateFailure(f"{cell['id']} {arm_name}: exit {done.returncode}")
        obj = select_line(done.stdout, arm.get("line", "whole"))
        record["object"] = obj
        record["metrics"] = {m["name"]: dig(obj, m["path"]) for m in cell["metrics"]}
        check = cell.get("check", {})
        if "path" in check and dig(obj, check["path"]) != check["equals"]:
            raise GateFailure(f"{cell['id']} {arm_name}: check {check['path']} = "
                              f"{dig(obj, check['path'])!r}, expected {check['equals']!r}")
        for item in arm.get("checks", []):
            target = select_line(done.stdout, item.get("line", arm.get("line", "whole")))
            if dig(target, item["path"]) != item["equals"]:
                raise GateFailure(f"{cell['id']} {arm_name}: {item['path']} = "
                                  f"{dig(target, item['path'])!r}, expected {item['equals']!r}")
    except GateFailure as failure:
        record["failure"] = str(failure)
        failure.record = record  # type: ignore[attr-defined]
        raise
    except (ValueError, KeyError, IndexError, TypeError) as error:
        record["failure"] = f"unparsable output: {error}"
        failure = GateFailure(f"{cell['id']} {arm_name}: unparsable output: {error}")
        failure.record = record  # type: ignore[attr-defined]
        raise failure from error
    return record


def run_arm_retrying(cell, arm_name, tools, scratch, extra=None) -> Dict[str, Any]:
    try:
        return run_arm(cell, arm_name, tools, scratch, extra)
    except InfrastructureFailure as first:
        try:
            record = run_arm(cell, arm_name, tools, scratch, extra)
        except InfrastructureFailure as second:
            raise GateFailure(f"{cell['id']} {arm_name}: infrastructure failure twice: "
                              f"{first}; {second}") from second
        record["retried_after"] = str(first)
        return record


def same_trace(cell: Dict[str, Any], cf: Dict[str, Any], ref: Dict[str, Any]) -> None:
    field = cell.get("check", {}).get("same_trace")
    if not field:
        return
    a, b = cf["object"].get(field), ref["object"].get(field)
    if a is None or b is None or a != b:
        raise GateFailure(f"{cell['id']}: arms ran different inputs ({field}: {a!r}, {b!r})")


def block_order(matrix: Dict[str, Any]) -> List[str]:
    return [b for tier in matrix["rules"]["block_order"] for b in tier]


def schedule(cells: List[Dict[str, Any]], seed: int, pairs: int, warmup: int,
             order: List[str]) -> List[Dict[str, Any]]:
    """Smoke first, then blocks in priority order; per block, deterministic cells, then
    rounds over its paired cells; per cell, exactly half CF-first among measured pairs."""
    rng = random.Random(seed)
    steps: List[Dict[str, Any]] = [{"kind": "smoke", "block": "smoke", "tier": 1}]
    rank = {block: i for i, block in enumerate(order)}
    blocks = sorted({c["block"] for c in cells}, key=lambda b: rank.get(b, len(rank)))
    for block in blocks:
        block_cells = [c for c in cells if c["block"] == block]
        tier = block_cells[0]["tier"]
        for cell in block_cells:
            if cell["kind"] in ("delegated", "deterministic"):
                steps.append({"cell": cell["id"], "block": block, "tier": tier,
                              "kind": cell["kind"]})
        paired = [c["id"] for c in block_cells if c["kind"] == "paired"]
        flags: Dict[str, List[bool]] = {}
        for cell_id in paired:
            measured = [True] * (pairs // 2) + [False] * (pairs - pairs // 2)
            rng.shuffle(measured)
            flags[cell_id] = [i % 2 == 0 for i in range(warmup)] + measured
        for index in range(warmup + pairs):
            round_cells = list(paired)
            rng.shuffle(round_cells)
            for cell_id in round_cells:
                steps.append({"cell": cell_id, "block": block, "tier": tier, "kind": "pair",
                              "pair": index, "warmup": index < warmup,
                              "cf_first": flags[cell_id][index]})
    return steps


def command_output(argv: List[str]) -> Optional[str]:
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None


def host_description() -> Dict[str, Any]:
    darwin = platform.system() == "Darwin"
    return {"platform": platform.platform(), "machine": platform.machine(),
            "kernel": command_output(["uname", "-a"]), "python": sys.version.split()[0],
            "cpu": command_output(["sysctl", "-n", "machdep.cpu.brand_string"]) if darwin
            else command_output(["sh", "-c", "grep -m1 'model name' /proc/cpuinfo"]),
            "cores": os.cpu_count(),
            "memory_bytes": command_output(["sysctl", "-n", "hw.memsize"]) if darwin
            else command_output(["sh", "-c", "grep MemTotal /proc/meminfo"]),
            "frequency_policy": command_output(["pmset", "-g"]) if darwin
            else command_output(["sh", "-c", "cat /sys/devices/system/cpu/cpu0/cpufreq/"
                                             "scaling_governor"])}


def host_snapshot(label: str) -> Dict[str, Any]:
    darwin = platform.system() == "Darwin"
    return {"label": label, "time": time.time(),
            "loadavg": os.getloadavg() if hasattr(os, "getloadavg") else None,
            "swap": command_output(["sysctl", "-n", "vm.swapusage"]) if darwin
            else command_output(["sh", "-c", "grep -E 'SwapTotal|SwapFree' /proc/meminfo"]),
            "thermal": command_output(["pmset", "-g", "therm"]) if darwin
            else command_output(["sh", "-c", "cat /sys/class/thermal/thermal_zone0/temp"])}


def provenance(tools: Dict[str, Any]) -> Dict[str, Any]:
    executables = {}
    for key, value in tools.items():
        if key.startswith("_") or not isinstance(value, list):
            continue
        for item in value:
            if isinstance(item, str) and os.path.isfile(item) and os.access(item, os.X_OK):
                executables[item] = sha256_file(Path(item))
    checkouts = {name: {"path": path,
                        "sha": command_output(["git", "-C", path, "rev-parse", "HEAD"]),
                        "dirty": bool(command_output(["git", "-C", path, "status",
                                                      "--porcelain"]))}
                 for name, path in tools.get("_checkouts", {}).items()}
    lockfiles = {path: sha256_file(Path(path)) for path in tools.get("_lockfiles", [])}
    # Delegated collectors: every argv element that names a file (absolute, or relative to
    # the collector's cwd) is hashed, so a session 2 with another collector script is refused.
    delegated = {}
    for cell_id, spec in sorted(tools.get("_delegated", {}).items()):
        files = {}
        for item in spec.get("argv", []):
            path = Path(item) if os.path.isabs(item) else Path(spec.get("cwd") or ".") / item
            if path.is_file():
                files[item] = sha256_file(path)
        delegated[cell_id] = files
    return {"executables": executables, "checkouts": checkouts, "lockfiles": lockfiles,
            "delegated": delegated}


def missing_delegated_env(steps: List[Dict[str, Any]], tools: Dict[str, Any]) -> List[str]:
    """Environment variables a scheduled delegated collector needs (``requires_env``) and
    that are unset: the session does not start (checked before ``record.json``)."""
    missing = []
    for step in steps:
        if step.get("kind") != "delegated":
            continue
        spec = tools.get("_delegated", {}).get(step["cell"], {})
        missing += [f"{step['cell']}: {name}" for name in spec.get("requires_env", [])
                    if not os.environ.get(name)]
    return missing


def derived_seed(matrix_sha: str, candidate_sha: Optional[str]) -> int:
    return int(sha256_bytes(f"{matrix_sha}:{candidate_sha}".encode())[:15], 16)


def smoke(cells: List[Dict[str, Any]], tools: Dict[str, Any], scratch: Path, log) -> None:
    """Tier-1 correctness smoke: every distinct arm once (``--verify true`` for cf5-core);
    deterministic arms twice, with their metrics compared (a difference is recorded)."""
    seen = set()
    for cell in cells:
        if cell["kind"] not in ("paired", "deterministic"):
            continue
        for arm_name in ("cf", "ref"):
            arm = cell["arms"][arm_name]
            key = json.dumps([arm["tool"], arm["args"]])
            if key in seen:
                continue
            seen.add(key)
            extra = ["--verify", "true"] if arm["tool"] == "cf5_core" else None
            first = run_arm_retrying(cell, arm_name, tools, scratch, extra)
            entry = {"cell": cell["id"], "arm": arm_name, "metrics": first["metrics"],
                     "wall_s": first["wall_s"]}
            if cell["kind"] == "deterministic":
                second = run_arm_retrying(cell, arm_name, tools, scratch)
                entry["repeat_metrics"] = second["metrics"]
                entry["deterministic"] = second["metrics"] == first["metrics"]
            log.write(json.dumps(entry) + "\n")
            log.flush()


def run_delegated(cell: Dict[str, Any], tools: Dict[str, Any], out: Path) -> Dict[str, Any]:
    spec = tools.get("_delegated", {}).get(cell["id"])
    if not spec:
        return {"state": "NOT_RUN", "reason": "no collector command in the tool map"}
    log = out / f"delegated-{cell['id']}.log"
    start = time.monotonic()
    with log.open("w") as handle:
        done = subprocess.run(spec["argv"], cwd=spec.get("cwd"), stdout=handle,
                              stderr=subprocess.STDOUT,
                              env={**os.environ, **spec.get("env", {})})
    return {"state": "DELEGATED_DONE" if done.returncode == 0 else "DELEGATED_FAILED",
            "exit": done.returncode, "wall_s": time.monotonic() - start, "log": str(log)}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--tools", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--session", type=int, choices=(1, 2), default=1)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--preparatory", action="store_true")
    parser.add_argument("--order-seed", type=int)
    parser.add_argument("--cap-hours", type=float)
    parser.add_argument("--blocks")
    parser.add_argument("--pairs", type=int)
    parser.add_argument("--warmup", type=int)
    parser.add_argument("--cells-per-block", type=int)
    parser.add_argument("--no-smoke", action="store_true")
    args = parser.parse_args(argv)
    restricted = [args.order_seed is not None, args.cap_hours is not None, bool(args.blocks),
                  args.pairs is not None, args.warmup is not None, bool(args.cells_per_block),
                  args.no_smoke]
    if any(restricted) and not args.preparatory:
        parser.error("--order-seed, --cap-hours, --blocks, --pairs, --warmup, "
                     "--cells-per-block and --no-smoke need --preparatory")

    matrix_text = args.matrix.read_bytes()
    matrix = json.loads(matrix_text)
    matrix_sha = sha256_bytes(matrix_text)
    tools = json.loads(args.tools.read_text())
    prov = provenance(tools)
    candidate_sha = prov["checkouts"].get("candidate", {}).get("sha")
    pairs = args.pairs if args.pairs is not None else PAIRS
    warmup = args.warmup if args.warmup is not None else WARMUP
    seed = args.order_seed if args.order_seed is not None else derived_seed(matrix_sha,
                                                                            candidate_sha)
    cap_hours = args.cap_hours if args.cap_hours is not None else (
        matrix["rules"]["cap_hours"] if args.session == 1
        else matrix["rules"]["second_session_cap_hours"])

    cells = matrix["cells"]
    if args.blocks:
        wanted = set(args.blocks.split(","))
        cells = [c for c in cells if c["block"] in wanted]
    if args.cells_per_block:
        kept, seen = [], {}
        for cell in cells:
            seen[cell["block"]] = seen.get(cell["block"], 0) + 1
            if seen[cell["block"]] <= args.cells_per_block:
                kept.append(cell)
        cells = kept
    order = block_order(matrix)
    first_steps = None
    if args.session == 2:
        if args.preparatory or not args.resume_from:
            parser.error("--session 2 needs --resume-from and no --preparatory")
        status1 = json.loads((args.resume_from / "status.json").read_text())
        record1 = json.loads((args.resume_from / "record.json").read_text())
        if status1.get("preparatory") or record1.get("preparatory"):
            parser.error("cannot resume from a preparatory run")
        if status1["campaign"] == "failed":
            parser.error("session 1 failed the correctness gate: no second session")
        if record1["matrix_sha256"] != matrix_sha:
            parser.error("the matrix differs from session 1's")
        if record1["provenance"]["executables"] != prov["executables"] or \
                record1["provenance"]["checkouts"] != prov["checkouts"] or \
                record1["provenance"].get("delegated") != prov["delegated"]:
            parser.error("binaries or checkouts differ from session 1's")
        if time.time() - record1["start"]["time"] > SECOND_SESSION_DAYS * 86_400:
            parser.error("more than 14 days after session 1")
        seed = record1["order_seed"]
        todo = {cid for cid, s in status1["cells"].items() if s["state"] in ("INCOMPLETE",
                                                                            "NOT_RUN")}
        cells = [c for c in cells if c["id"] in todo]
        first_steps = json.loads((args.resume_from / "schedule.json").read_text())
    elif args.resume_from:
        parser.error("--resume-from is for --session 2")

    if first_steps is not None:
        ids = {c["id"] for c in cells}
        steps = [s for s in first_steps if s.get("kind") == "smoke" or s.get("cell") in ids]
    else:
        steps = schedule(cells, seed, pairs, warmup, order)
    if args.no_smoke:
        steps = [s for s in steps if s["kind"] != "smoke"]
    missing_env = missing_delegated_env(steps, tools)
    if missing_env:
        parser.error("NOT STARTED: unset environment for delegated collectors: "
                     + ", ".join(missing_env))
    args.out.mkdir(parents=True, exist_ok=False)
    scratch = Path(tempfile.mkdtemp(prefix="cf5-"))
    record = {"schema": "cf5-record-2", "preparatory": args.preparatory,
              "session": args.session, "order_seed": seed,
              "order_seed_derived": args.order_seed is None and args.session == 1,
              "matrix_sha256": matrix_sha, "tools": tools, "provenance": prov,
              "pairs": pairs, "warmup_pairs": warmup, "cap_hours": cap_hours,
              "cells": [c["id"] for c in cells], "host": host_description(),
              "resume_from": str(args.resume_from) if args.resume_from else None,
              "start": host_snapshot("start")}
    (args.out / "record.json").write_text(json.dumps(record, indent=1) + "\n")
    (args.out / "schedule.json").write_text(json.dumps(steps) + "\n")

    by_id = {c["id"]: c for c in cells}
    state: Dict[str, Dict[str, Any]] = {c["id"]: {"state": "NOT_RUN", "pairs": 0}
                                        for c in cells}
    deadline = time.monotonic() + cap_hours * 3600
    campaign = "complete"
    snapshots: List[Dict[str, Any]] = []
    current_block = None
    raw = (args.out / "raw.jsonl").open("w")
    smoke_log = (args.out / "smoke.jsonl").open("w")
    try:
        for step in steps:
            if step["block"] != current_block:
                if current_block is not None:
                    snapshots.append(host_snapshot(f"after {current_block}"))
                snapshots.append(host_snapshot(f"before {step['block']}"))
                current_block = step["block"]
            if time.monotonic() > deadline:
                campaign = "incomplete"
                break
            if step["kind"] == "smoke":
                smoke(cells, tools, scratch, smoke_log)
                continue
            cell = by_id[step["cell"]]
            if step["kind"] == "delegated":
                state[cell["id"]] = run_delegated(cell, tools, args.out)
                continue
            if step["kind"] == "deterministic":
                for arm_name in ("cf", "ref"):
                    obs = run_arm_retrying(cell, arm_name, tools, scratch)
                    raw.write(json.dumps({"cell": cell["id"], **obs}) + "\n")
                state[cell["id"]] = {"state": "COMPLETE", "pairs": 1}
                raw.flush()
                continue
            order_arms = ("cf", "ref") if step["cf_first"] else ("ref", "cf")
            observed = {a: run_arm_retrying(cell, a, tools, scratch) for a in order_arms}
            same_trace(cell, observed["cf"], observed["ref"])
            raw.write(json.dumps({"cell": cell["id"], "pair": step["pair"],
                                  "warmup": step["warmup"], "cf_first": step["cf_first"],
                                  "cf": observed["cf"], "ref": observed["ref"]}) + "\n")
            raw.flush()
            current = state[cell["id"]]
            if not step["warmup"]:
                done = current["pairs"] + 1
                state[cell["id"]] = {"state": "COMPLETE" if done == pairs else "INCOMPLETE",
                                     "pairs": done}
            elif current["state"] == "NOT_RUN":
                state[cell["id"]] = {"state": "INCOMPLETE", "pairs": 0}
    except GateFailure as failure:
        campaign = "failed"
        cell_id = str(failure.args[0]).split(" ")[0].rstrip(":")
        state[cell_id] = {"state": "FAILED", "reason": str(failure)}
        failed = getattr(failure, "record", None)
        raw.write(json.dumps({"cell": cell_id, "failed_observation": failed,
                              "reason": str(failure)}) + "\n")
        snapshots.append(host_snapshot(f"failure {cell_id}"))
    except KeyboardInterrupt:
        campaign = "incomplete"
        snapshots.append(host_snapshot("interrupted"))
    finally:
        raw.close()
        smoke_log.close()
        snapshots.append(host_snapshot("end"))
        if campaign == "complete" and any(s["state"] in ("INCOMPLETE", "NOT_RUN")
                                          for s in state.values()):
            campaign = "incomplete"
        status = {"schema": "cf5-status-2", "preparatory": args.preparatory,
                  "session": args.session, "campaign": campaign, "cells": state,
                  "snapshots": snapshots}
        (args.out / "status.json").write_text(json.dumps(status, indent=1) + "\n")
        shutil.rmtree(scratch, ignore_errors=True)
    print(json.dumps({"campaign": campaign, "preparatory": args.preparatory,
                      "out": str(args.out)}))
    return 0 if campaign != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
