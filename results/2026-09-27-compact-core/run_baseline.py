#!/usr/bin/env python3
"""Build and record a sequential local release matrix using only the standard library.

Run from any directory: python3 scripts/run_baseline.py NEW_OUTPUT_DIRECTORY.
The output must not exist. Source hashes cover both workspaces' build inputs;
patches and untracked Rust files preserve this milestone without a commit.
"""
import argparse
import random
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT.parent / "knotrel"
ENGINES = ["reference-bfs", "compact-bfs", "dense-bfs", "petgraph-dfs", "outils-hdt"]
KINDS = ["chain-split-rejoin-v1", "cycle-alternatives-v1",
         "components-join-split-v1", "hub-alternatives-v1"]


def command(args, cwd=ROOT):
    return subprocess.check_output(args, cwd=cwd, text=True).strip()


def optional_command(args):
    result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True)
    return {"value": result.stdout.strip() if result.returncode == 0 else None,
            "error": result.stderr.strip() if result.returncode else None}


def hashes():
    result = {}
    for name, root in [("benchmarks", ROOT), ("core", CORE)]:
        paths = [root / "Cargo.toml", root / "Cargo.lock", root / "rust-toolchain.toml"]
        paths += sorted((root / "crates").rglob("*.rs"))
        paths += sorted((root / "crates").rglob("Cargo.toml"))
        paths += sorted((root / ".cargo").glob("config*"))
        for path in paths:
            result[f"{name}/{path.relative_to(root)}"] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result


def run_cases(nodes, kinds, trials, regimes, order_seed):
    """Balance fresh processes across regimes, then randomize execution order.

    Fresh means no deliberate replay warmup, not flushed CPU or OS caches.
    Every case is a separate process; repetitions inside it stay separate.
    """
    if trials < 1 or regimes not in ("fresh", "warmed", "both"):
        raise ValueError("positive trials and a known cache regime are required")
    warmups = [0, 1] if regimes == "both" else [int(regimes == "warmed")]
    cases = []
    for n in nodes:
        for kind in kinds:
            for trial in range(trials):
                for warmup in warmups:
                    regime = "warmed" if warmup else "fresh"
                    name = f"{kind}-n{n}-{regime}-p{trial}"
                    cases.append(dict(nodes=n, kind=kind, trial=trial, warmup=warmup,
                                      regime=regime, name=name))
    random.Random(order_seed).shuffle(cases)
    return cases


def engine_order(selection, trial):
    """Rotate order across process trials to balance first/last positions."""
    engines = ENGINES[:] if selection == "all" else selection.split(',')
    if not engines or len(set(engines)) != len(engines) or any(e not in ENGINES for e in engines):
        raise ValueError("unknown or duplicate engine")
    offset = trial % len(engines)
    return engines[offset:] + engines[:offset]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--nodes", type=int, nargs="+", default=[128, 1024, 4096])
    parser.add_argument("--rounds", type=int, default=200)
    parser.add_argument("--process-trials", type=int, default=1)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--cache-regimes", choices=["fresh", "warmed", "both"], default="warmed")
    parser.add_argument("--engines", default="reference-bfs")
    parser.add_argument("--query-repeats", type=int, default=0)
    parser.add_argument("--order-seed", type=int, default=42)
    args = parser.parse_args()
    if min(args.nodes) < 6 or min(args.rounds, args.process_trials, args.repetitions) < 1:
        parser.error("nodes must be >=6 and all counts positive")
    engine_order(args.engines, 0)
    if args.query_repeats < 0:
        parser.error("query repeats must be nonnegative")
    cases = run_cases(args.nodes, KINDS, args.process_trials, args.cache_regimes, args.order_seed)
    for case in cases:
        case["engine_order"] = engine_order(args.engines, case["trial"])
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    before = hashes()
    collector_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    metadata = {
        "platform": platform.platform(), "machine": platform.machine(),
        "compiler": command(["rustc", "-vV"]),
        "build_command": ["cargo", "build", "--release", "--locked", "--message-format=json-render-diagnostics"],
        "environment": {key: os.environ.get(key) for key in
                        ["RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_TARGET", "CARGO_TARGET_DIR", "CARGO_PROFILE_RELEASE_OPT_LEVEL", "CARGO_PROFILE_RELEASE_LTO", "CARGO_PROFILE_RELEASE_CODEGEN_UNITS"]},
        "source_sha256": before,
        "collector_sha256": collector_hash,
        "query_repeats": args.query_repeats,
        "method": "One sequential process per case; fresh graphs per replay; CPU/OS caches uncontrolled.",
        "cache_protocol": {"cases_in_execution_order": cases, "order_seed": args.order_seed,
                           "process_trials": args.process_trials, "repetitions": args.repetitions,
                           "system_caches_flushed": False},
        "commands": [],
    }
    if sys.platform == "darwin":
        metadata["hardware"] = {key: optional_command(["sysctl", "-n", key]) for key in
                                ["machdep.cpu.brand_string", "hw.ncpu", "hw.memsize"]}
        metadata["os_version"] = command(["sw_vers"])
    for name, root in [("benchmarks", ROOT), ("core", CORE)]:
        metadata[name] = {"revision": command(["git", "rev-parse", "HEAD"], root),
                          "status": command(["git", "status", "--porcelain"], root)}
        (destination / f"{name}.patch").write_text(command(["git", "diff", "--binary", "HEAD"], root) + "\n")
        for relative in command(["git", "ls-files", "--others", "--exclude-standard"], root).splitlines():
            path = root / relative
            if relative.startswith("crates/") and path.suffix == ".rs":
                saved = destination / "untracked" / name / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(path.read_bytes())
    build = subprocess.run(metadata["build_command"], cwd=ROOT, check=True,
                           text=True, stdout=subprocess.PIPE)
    artifacts = [json.loads(line) for line in build.stdout.splitlines()]
    executables = [item["executable"] for item in artifacts
                   if item.get("reason") == "compiler-artifact"
                   and item.get("target", {}).get("name") == "knotrel-benchmarks"
                   and item.get("executable")]
    if len(executables) != 1:
        raise RuntimeError("Cargo did not report exactly one benchmark executable")
    binary = Path(executables[0])
    metadata["binary_sha256"] = hashlib.sha256(binary.read_bytes()).hexdigest()
    for case in cases:
        name = case["name"]
        trace = destination / f"{name}.trace.json"
        command_args = [str(binary), "--workload", case["kind"], "--nodes", str(case["nodes"]),
                        "--rounds", str(args.rounds), "--seed", "42", "--warmup", str(case["warmup"]),
                        "--repetitions", str(args.repetitions), "--trace-out", str(trace),
                        "--engine", ",".join(case["engine_order"]), "--query-repeats", str(args.query_repeats)]
        metadata["commands"].append(command_args)
        print(f"Measuring {name}", flush=True)
        output = command(command_args)
        json.loads(output)
        (destination / f"{name}.json").write_text(output + "\n")
    if hashes() != before or hashlib.sha256(Path(__file__).read_bytes()).hexdigest() != collector_hash:
        raise RuntimeError("Build inputs changed during measurement; discard these results")
    (destination / "run_baseline.py").write_bytes(Path(__file__).read_bytes())
    metadata["artifact_sha256"] = {str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sorted(destination.rglob("*")) if p.is_file()}
    (destination / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
