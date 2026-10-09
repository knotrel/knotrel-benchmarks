#!/usr/bin/env python3
"""Run the unified 74-cell 5-engine ranking campaign for 2026-10-09.

Evaluates Compact, Workspace, ETT (with packed tokens), HDT (with packed tokens),
and petgraph across 74 main cells with 3 process trials per engine (1,110 runs).
Whole-process peak resident memory is measured using platform time tools.
All runs are executed sequentially in a deterministic, balanced order.
"""
import hashlib
import itertools
import json
import os
from pathlib import Path
import platform
import random
import re
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT.parent / "knotrel"
sys.path.insert(0, str(ROOT / "scripts"))
from run_baseline import command, hashes, source_patch


def peak_rss(stderr, system):
    """Normalize the platform time tool's peak process RSS to bytes."""
    if system == "darwin":
        match = re.search(r"^\s*(\d+)\s+maximum resident set size\s*$", stderr, re.M)
        return int(match[1]) if match else None
    match = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", stderr)
    return int(match[1]) * 1024 if match else None


def run_measurement(invocation, timeout):
    """Bound both time wrapper and benchmark lifetime; preserve partial output."""
    with subprocess.Popen(
        invocation,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            return subprocess.CompletedProcess(
                invocation, process.returncode, stdout, stderr
            ), False
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            stdout, stderr = process.communicate()
            return subprocess.CompletedProcess(invocation, 124, stdout, stderr), True


def ensure_cogentco_trace():
    """Verify pinned Cogentco trace input; recover from provenance if needed."""
    expected_hash = "d56e9371c2e290d7b115c43df65fd0a31949639821cbcf3f96617e15a1b82760"
    rec_meta = ROOT / "results/2026-10-09-ett-packed-tokens/recovered-trace.json"
    trace_path = None
    if rec_meta.exists():
        data = json.loads(rec_meta.read_text())
        candidate = Path(data.get("path", ""))
        if candidate.exists() and hashlib.sha256(candidate.read_bytes()).hexdigest() == expected_hash:
            trace_path = candidate

    if trace_path is None:
        recover_script = ROOT / "results/2026-10-09-ett-packed-tokens/recover_trace.py"
        subprocess.run(["python3", str(recover_script)], cwd=ROOT, check=True)
        data = json.loads(rec_meta.read_text())
        trace_path = Path(data["path"])

    actual_hash = hashlib.sha256(trace_path.read_bytes()).hexdigest()
    if actual_hash != expected_hash:
        raise RuntimeError(f"Cogentco trace hash mismatch: expected {expected_hash}, got {actual_hash}")
    return trace_path, actual_hash


def main():
    destination = Path(__file__).resolve().parent
    timeout = 120
    engines = ["compact-bfs", "compact-workspace", "ett-scan", "hdt", "petgraph-dfs"]

    print("Verifying inputs and recording environment...", flush=True)
    trace_path, trace_sha256 = ensure_cogentco_trace()
    before_hashes = hashes()

    meta = {
        "platform": platform.platform(),
        "compiler": command(["rustc", "-vV"]),
        "source_sha256": before_hashes,
        "patch_scope": "Tracked changes against HEAD, excluding results/; untracked Rust files saved separately.",
        "memory_scope": "Peak entire child process, including trace, export, warmups, samples and engine. Not engine-only RSS.",
        "environment": {
            k: os.environ.get(k)
            for k in [
                "RUSTFLAGS",
                "CARGO_ENCODED_RUSTFLAGS",
                "CARGO_BUILD_TARGET",
                "CARGO_TARGET_DIR",
                "CARGO_PROFILE_RELEASE_OPT_LEVEL",
                "CARGO_PROFILE_RELEASE_LTO",
                "CARGO_PROFILE_RELEASE_CODEGEN_UNITS",
            ]
        },
        "cogentco_trace": {
            "path": str(trace_path),
            "sha256": trace_sha256,
        },
        "cases": [],
    }

    for name, root in [("benchmarks", ROOT), ("core", CORE)]:
        meta[name] = {
            "revision": command(["git", "rev-parse", "HEAD"], root),
            "status": command(["git", "status", "--porcelain"], root),
        }
        (destination / f"{name}.patch").write_text(source_patch(root) + "\n")
        for relative in command(
            ["git", "ls-files", "--others", "--exclude-standard"], root
        ).splitlines():
            f = root / relative
            if relative.startswith("crates/") and f.suffix == ".rs":
                saved = destination / "untracked" / name / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(f.read_bytes())

    for script in ["run_scale.py", "run_baseline.py"]:
        (destination / script).write_bytes((ROOT / "scripts" / script).read_bytes())

    print("Building release executable...", flush=True)
    build_args = [
        "cargo",
        "build",
        "--release",
        "--locked",
        "--message-format=json-render-diagnostics",
    ]
    meta["build_command"] = build_args
    build = subprocess.run(
        build_args, cwd=ROOT, check=True, text=True, stdout=subprocess.PIPE
    )
    artifacts = [json.loads(line) for line in build.stdout.splitlines()]
    binary = next(
        Path(a["executable"])
        for a in artifacts
        if a.get("reason") == "compiler-artifact"
        and a.get("target", {}).get("name") == "knotrel-benchmarks"
        and a.get("executable")
    )
    meta["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()

    cases = []

    # 1. Sparse cases (48 cells * 15 = 720 cases)
    sparse_nodes = [1024, 10000, 100000, 1000000]
    sparse_queries = [10, 50, 90]
    sparse_workloads = ["sustained-churn-path-v1", "sustained-churn-blocks-v1"]
    for n, q, workload, trial, regime, engine in itertools.product(
        sparse_nodes, sparse_queries, sparse_workloads, range(3), ["fresh", "warmed"], engines
    ):
        name = f"sparse-{workload}-n{n}-q{q}-{regime}-p{trial}-{engine}"
        cmd = [
            str(binary),
            "--nodes",
            str(n),
            "--rounds",
            "10",
            "--workload",
            workload,
            "--query-percent",
            str(q),
            "--engine",
            engine,
            "--warmup",
            str(int(regime == "warmed")),
            "--repetitions",
            "1",
            "--seed",
            "42",
            "--query-repeats",
            "0",
        ]
        cases.append({
            "name": name,
            "family": "sparse",
            "nodes": n,
            "query_percent": q,
            "workload": workload,
            "trial": trial,
            "regime": regime,
            "engine": engine,
            "args": cmd,
        })

    # 2. Dense cases (24 cells * 15 = 360 cases)
    dense_nodes = [128, 512]
    dense_queries = [10, 50, 90]
    dense_workloads = ["dense-bridge-churn-v1", "redundant-bridge-churn-v1"]
    for n, q, workload, trial, regime, engine in itertools.product(
        dense_nodes, dense_queries, dense_workloads, range(3), ["fresh", "warmed"], engines
    ):
        name = f"dense-{workload}-n{n}-q{q}-{regime}-p{trial}-{engine}"
        cmd = [
            str(binary),
            "--nodes",
            str(n),
            "--rounds",
            "10",
            "--workload",
            workload,
            "--query-percent",
            str(q),
            "--engine",
            engine,
            "--warmup",
            str(int(regime == "warmed")),
            "--repetitions",
            "1",
            "--seed",
            "42",
            "--query-repeats",
            "0",
        ]
        cases.append({
            "name": name,
            "family": "dense",
            "nodes": n,
            "query_percent": q,
            "workload": workload,
            "trial": trial,
            "regime": regime,
            "engine": engine,
            "args": cmd,
        })

    # 3. Cogentco cases (2 cells * 15 = 30 cases)
    for trial, regime, engine in itertools.product(
        range(3), ["fresh", "warmed"], engines
    ):
        name = f"cogentco-topology-zoo-outages-v1-n197-import-{regime}-p{trial}-{engine}"
        cmd = [
            str(binary),
            "--trace-in",
            str(trace_path),
            "--engine",
            engine,
            "--warmup",
            str(int(regime == "warmed")),
            "--repetitions",
            "1",
        ]
        cases.append({
            "name": name,
            "family": "cogentco",
            "nodes": 197,
            "query_percent": None,
            "workload": "topology-zoo-outages-v1",
            "trial": trial,
            "regime": regime,
            "engine": engine,
            "args": cmd,
        })

    if len(cases) != 1110:
        raise RuntimeError(f"Expected 1110 cases, got {len(cases)}")

    print(f"Prepared {len(cases)} cases across 74 cells. Shuffling deterministically...", flush=True)
    random.Random(42).shuffle(cases)

    time_tool = ["/usr/bin/time", "-l" if sys.platform == "darwin" else "-v"]

    for i, c in enumerate(cases):
        name = c["name"]
        timed = [*time_tool, *c["args"]]
        print(f"[{i+1}/{len(cases)}] {name}", flush=True)
        result, timed_out = run_measurement(timed, timeout)
        (destination / (name + ".stderr.txt")).write_text(result.stderr)
        rss = peak_rss(result.stderr, sys.platform)
        case_info = {
            "name": name,
            "family": c["family"],
            "nodes": c["nodes"],
            "query_percent": c["query_percent"],
            "workload": c["workload"],
            "trial": c["trial"],
            "regime": c["regime"],
            "engine": c["engine"],
            "command": timed,
            "timed_out": timed_out,
            "exit_code": result.returncode,
            "peak_process_rss_bytes": rss,
        }
        meta["cases"].append(case_info)
        (destination / "manifest.partial.json").write_text(
            json.dumps(meta, indent=2) + "\n"
        )
        if result.returncode != 0:
            (destination / (name + ".partial-stdout.txt")).write_text(result.stdout)
            continue

        json.loads(result.stdout)
        if rss is None:
            raise RuntimeError(f"Missing process RSS for {name}")
        (destination / (name + ".json")).write_text(result.stdout)

    if before_hashes != hashes():
        raise RuntimeError("Source files changed during measurement!")

    (destination / "manifest.partial.json").unlink()
    meta["artifact_sha256"] = {
        str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (destination / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print("Collection completed successfully!", flush=True)


if __name__ == "__main__":
    main()
