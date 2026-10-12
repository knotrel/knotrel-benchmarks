#!/usr/bin/env python3
"""Build isolated, source-verified ETT scan-root profiling binaries."""

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
    """Return a SHA-256 digest for one regular file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(
    args: list[str],
    cwd: Path,
    log: Path,
    *,
    env: dict[str, str] | None = None,
) -> None:
    """Run one checked build or verification command and preserve its output."""
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


def git_state(root: Path) -> dict[str, Any]:
    """Collect immutable revision and dirty-state provenance."""
    return {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            text=True,
        ).strip(),
        "status": subprocess.check_output(
            ["git", "status", "--porcelain"],
            cwd=root,
            text=True,
        ),
    }


def source_hashes() -> dict[str, str]:
    """Hash exactly the source files recorded by the original pilot."""
    original = json.loads((PILOT / "builds.json").read_text())["original_source_sha256"]
    current: dict[str, str] = {}
    for name in original:
        checkout, relative = name.split("/", 1)
        root = CORE if checkout == "core" else BENCHMARKS
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"saved source path is absent: {path}")
        current[name] = sha256(path)
    mismatches = {
        name: {"expected": original[name], "actual": current[name]}
        for name in original
        if current[name] != original[name]
    }
    if mismatches:
        raise RuntimeError(
            "current sources differ from the recorded pilot:\n"
            + json.dumps(mismatches, indent=2, sort_keys=True)
        )
    return current


def copy_workspace(workspace: Path) -> tuple[Path, Path]:
    """Copy both workspaces without Git metadata or build products."""
    copies: dict[str, Path] = {}
    for source in (CORE, BENCHMARKS):
        destination = workspace / source.name
        shutil.copytree(
            source,
            destination,
            ignore=shutil.ignore_patterns(".git", "target", "__pycache__"),
        )
        copies[source.name] = destination
    return copies["knotrel"], copies["knotrel-benchmarks"]


def snapshots() -> dict[str, dict[str, str]]:
    """Load the preserved before/after source snapshots."""
    return {
        variant: {
            source: (PILOT / f"{variant}-{source}.rs.txt").read_text()
            for source in ("forest", "dynamic")
        }
        for variant in ("before", "after")
    }


def candidate_patch(sources: dict[str, dict[str, str]]) -> str:
    """Generate the candidate-only patch from the transferred snapshots."""
    return "".join(
        "".join(
            difflib.unified_diff(
                sources["before"][source].splitlines(keepends=True),
                sources["after"][source].splitlines(keepends=True),
                fromfile=f"a/crates/knotrel-core/src/{source}.rs",
                tofile=f"b/crates/knotrel-core/src/{source}.rs",
            )
        )
        for source in ("forest", "dynamic")
    )


def main() -> None:
    """Produce two verified release binaries in a private isolated workspace."""
    if (RESULTS / "builds.json").exists():
        raise RuntimeError("refusing to overwrite recorded build provenance")
    recorded_hashes = source_hashes()
    sources = snapshots()
    patch = candidate_patch(sources)
    expected_patch = (PILOT / "candidate.patch").read_text()
    if patch != expected_patch:
        raise RuntimeError("snapshot-derived patch differs from saved candidate.patch")

    workspace = Path(tempfile.mkdtemp(prefix="knotrel-ett-hardware-m4-", dir="/private/tmp"))
    isolated_core, isolated_benchmarks = copy_workspace(workspace)
    core_source = isolated_core / "crates/knotrel-core/src"
    metadata: dict[str, Any] = {
        "schema_version": 1,
        "created_utc": dt.datetime.now(dt.UTC).isoformat(),
        "workspace": str(workspace),
        "current_source_sha256": recorded_hashes,
        "pilot_builds_sha256": sha256(PILOT / "builds.json"),
        "candidate_patch_sha256": hashlib.sha256(patch.encode()).hexdigest(),
        "checkouts": {
            "core": git_state(CORE),
            "benchmarks": git_state(BENCHMARKS),
        },
        "compiler": subprocess.check_output(["rustc", "-vV"], cwd=BENCHMARKS, text=True),
        "variants": {},
    }

    for variant, variant_sources in sources.items():
        for source, contents in variant_sources.items():
            (core_source / f"{source}.rs").write_text(contents)
        run(
            ["cargo", "fmt", "--all", "--", "--check"],
            isolated_benchmarks,
            RESULTS / f"{variant}-fmt.txt",
        )
        run(
            ["cargo", "clippy", "--locked", "--workspace", "--all-targets", "--", "-D", "warnings"],
            isolated_benchmarks,
            RESULTS / f"{variant}-clippy.txt",
        )
        run(
            ["cargo", "test", "--locked", "--workspace"],
            isolated_benchmarks,
            RESULTS / f"{variant}-test.txt",
        )
        run(
            ["cargo", "doc", "--locked", "--workspace", "--no-deps"],
            isolated_benchmarks,
            RESULTS / f"{variant}-doc.txt",
            env=dict(os.environ, RUSTDOCFLAGS="-D warnings"),
        )
        run(
            ["cargo", "build", "--locked", "--release", "--bin", "knotrel-benchmarks"],
            isolated_benchmarks,
            RESULTS / f"{variant}-build.txt",
        )
        binary = workspace / variant
        shutil.copy2(isolated_benchmarks / "target/release/knotrel-benchmarks", binary)
        metadata["variants"][variant] = {
            "binary": str(binary),
            "binary_sha256": sha256(binary),
            "forest_sha256": hashlib.sha256(
                variant_sources["forest"].encode()
            ).hexdigest(),
            "dynamic_sha256": hashlib.sha256(
                variant_sources["dynamic"].encode()
            ).hexdigest(),
        }

    (RESULTS / "candidate.patch").write_text(patch)
    (RESULTS / "builds.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
