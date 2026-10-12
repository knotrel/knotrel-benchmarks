#!/usr/bin/env python3
"""Build isolated scan-root variants with safe replay signposts."""

from __future__ import annotations

import datetime as dt
import difflib
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


RESULTS = Path(__file__).resolve().parent
BENCHMARKS = RESULTS.parents[1]
CORE = BENCHMARKS.parent / "knotrel"
PILOT = BENCHMARKS / "results" / "2026-10-10-ett-scan-root"


def sha256(path: Path) -> str:
    """Return the SHA-256 digest of one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args: list[str], cwd: Path, log: Path, env: dict[str, str] | None = None) -> None:
    """Run one checked diagnostic build command while retaining its log."""
    with log.open("w") as output:
        subprocess.run(
            args,
            cwd=cwd,
            env=env,
            check=True,
            stdout=output,
            stderr=subprocess.STDOUT,
            text=True,
        )


def git_state(root: Path) -> dict[str, str]:
    """Record immutable revision and current dirty state."""
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip(),
        "status": subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=root, text=True
        ),
    }


def source_hashes() -> dict[str, str]:
    """Verify all pilot-recorded current sources before copying them."""
    recorded = json.loads((PILOT / "builds.json").read_text())["original_source_sha256"]
    actual: dict[str, str] = {}
    for name, expected in recorded.items():
        checkout, relative = name.split("/", 1)
        path = (CORE if checkout == "core" else BENCHMARKS) / relative
        value = sha256(path)
        if value != expected:
            raise RuntimeError(f"pilot source hash mismatch: {name}")
        actual[name] = value
    return actual


def snapshots() -> dict[str, dict[str, str]]:
    """Load the before/after candidate snapshots preserved by the pilot."""
    return {
        variant: {
            source: (PILOT / f"{variant}-{source}.rs.txt").read_text()
            for source in ("forest", "dynamic")
        }
        for variant in ("before", "after")
    }


def patch(before: str, after: str, path: str) -> str:
    """Produce one reproducible unified diff."""
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def instrument(main: str, cargo: str) -> tuple[str, str]:
    """Add safe signpost boundaries to the benchmark copy only."""
    cargo = cargo.replace("[dependencies]", '[dependencies]\napple-log = "=0.7.0"', 1)
    main = main.replace(
        "use knotrel_benchmarks::engines::{Engine, EngineKind};",
        "use apple_log::{OSSignposter, CATEGORY_POINTS_OF_INTEREST};\n"
        "use knotrel_benchmarks::engines::{Engine, EngineKind};",
        1,
    )
    main = main.replace(
        "    let mut reports = Vec::new();",
        '    let signposter = OSSignposter::new(\n'
        '        "io.github.knotrel.benchmarks",\n'
        "        CATEGORY_POINTS_OF_INTEREST,\n"
        "    )?;\n"
        "    let mut reports = Vec::new();",
        1,
    )
    main = main.replace(
        "            replay(nodes, &workload, engine, options.query_repeats)?;",
        "            replay(\n"
        "                nodes,\n"
        "                &workload,\n"
        "                engine,\n"
        "                options.query_repeats,\n"
        "                &signposter,\n"
        '                c"warmup-replay",\n'
        "            )?;",
        1,
    )
    main = main.replace(
        "            repetitions.push(replay(nodes, &workload, engine, options.query_repeats)?);",
        "            repetitions.push(replay(\n"
        "                nodes,\n"
        "                &workload,\n"
        "                engine,\n"
        "                options.query_repeats,\n"
        "                &signposter,\n"
        '                c"measurement-replay",\n'
        "            )?);",
        1,
    )
    main = main.replace(
        "    query_repeats: usize,\n) -> Result<Run, Box<dyn Error>> {",
        "    query_repeats: usize,\n"
        "    signposter: &OSSignposter,\n"
        "    phase: &'static std::ffi::CStr,\n"
        ") -> Result<Run, Box<dyn Error>> {",
        1,
    )
    main = main.replace(
        "    let wall_start = Instant::now();\n"
        "    for &operation in &workload.operations {",
        "    let interval = signposter.begin_interval(phase, signposter.make_signpost_id(), \"\");\n"
        "    let replay_result = (|| -> Result<u128, Box<dyn Error>> {\n"
        "        let wall_start = Instant::now();\n"
        "        for &operation in &workload.operations {",
        1,
    )
    main = main.replace(
        "    let workload_wall_ns = wall_start.elapsed().as_nanos();\n"
        "    let forest_stats = graph.forest_stats().map(|stats| {",
        "        let workload_wall_ns = wall_start.elapsed().as_nanos();\n"
        "        Ok(workload_wall_ns)\n"
        "    })();\n"
        "    signposter.end_interval(interval, \"\");\n"
        "    let workload_wall_ns = replay_result?;\n"
        "    let forest_stats = graph.forest_stats().map(|stats| {",
        1,
    )
    return main, cargo


def main() -> None:
    """Create and verify safe-signpost diagnostic binaries."""
    if (RESULTS / "builds.json").exists():
        raise RuntimeError("refusing to overwrite existing signpost build metadata")
    current_hashes = source_hashes()
    source_variants = snapshots()
    workspace = Path(tempfile.mkdtemp(prefix="knotrel-ett-signpost-m4-", dir="/private/tmp"))
    isolated_core = workspace / "knotrel"
    isolated_benchmarks = workspace / "knotrel-benchmarks"
    shutil.copytree(CORE, isolated_core, ignore=shutil.ignore_patterns(".git", "target", "__pycache__"))
    shutil.copytree(
        BENCHMARKS,
        isolated_benchmarks,
        ignore=shutil.ignore_patterns(".git", "target", "__pycache__"),
    )
    main_path = isolated_benchmarks / "crates/knotrel-benchmarks/src/main.rs"
    cargo_path = isolated_benchmarks / "crates/knotrel-benchmarks/Cargo.toml"
    original_main = main_path.read_text()
    original_cargo = cargo_path.read_text()
    instrumented_main, instrumented_cargo = instrument(original_main, original_cargo)
    if "unsafe" in instrumented_main:
        raise RuntimeError("diagnostic benchmark source unexpectedly contains unsafe")
    main_path.write_text(instrumented_main)
    cargo_path.write_text(instrumented_cargo)
    run(["cargo", "fmt", "--all"], isolated_benchmarks, RESULTS / "format.txt")
    run(["cargo", "generate-lockfile"], isolated_benchmarks, RESULTS / "lockfile.txt")
    diagnostic_patch = patch(
        original_cargo,
        cargo_path.read_text(),
        "crates/knotrel-benchmarks/Cargo.toml",
    ) + patch(
        original_main,
        main_path.read_text(),
        "crates/knotrel-benchmarks/src/main.rs",
    )
    (RESULTS / "diagnostic.patch").write_text(diagnostic_patch)

    metadata: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "workspace": str(workspace),
        "source_sha256": current_hashes,
        "checkouts": {"core": git_state(CORE), "benchmarks": git_state(BENCHMARKS)},
        "compiler": subprocess.check_output(["rustc", "-vV"], cwd=BENCHMARKS, text=True),
        "apple_log": {
            "version": "0.7.0",
            "features": [],
            "raw_ffi_enabled": False,
            "cargo_manifest_sha256": sha256(
                Path.home()
                / ".cargo/registry/src/index.crates.io-1949cf8c6b5b557f/apple-log-0.7.0/Cargo.toml"
            ),
        },
        "variants": {},
    }
    core_source = isolated_core / "crates/knotrel-core/src"
    commands = [
        ["cargo", "fmt", "--all", "--", "--check"],
        ["cargo", "clippy", "--locked", "--workspace", "--all-targets", "--", "-D", "warnings"],
        ["cargo", "test", "--locked", "--workspace"],
        ["cargo", "doc", "--locked", "--workspace", "--no-deps"],
        ["cargo", "build", "--locked", "--release", "--bin", "knotrel-benchmarks"],
    ]
    for variant, sources in source_variants.items():
        for source, contents in sources.items():
            (core_source / f"{source}.rs").write_text(contents)
        for index, command in enumerate(commands):
            environment = dict(os.environ, RUSTDOCFLAGS="-D warnings") if command[1] == "doc" else None
            run(command, isolated_benchmarks, RESULTS / f"{variant}-{index}.txt", environment)
        binary = workspace / variant
        shutil.copy2(isolated_benchmarks / "target/release/knotrel-benchmarks", binary)
        metadata["variants"][variant] = {
            "binary": str(binary),
            "binary_sha256": sha256(binary),
            "forest_sha256": hashlib.sha256(sources["forest"].encode()).hexdigest(),
            "dynamic_sha256": hashlib.sha256(sources["dynamic"].encode()).hexdigest(),
        }
    metadata["diagnostic_source_sha256"] = {
        "Cargo.toml": sha256(cargo_path),
        "Cargo.lock": sha256(isolated_benchmarks / "Cargo.lock"),
        "main.rs": sha256(main_path),
    }
    (RESULTS / "builds.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (RESULTS / "verification.json").write_text(
        json.dumps({"all_passed": True, "commands": commands}, indent=2) + "\n"
    )


if __name__ == "__main__":
    main()
