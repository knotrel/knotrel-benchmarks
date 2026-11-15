#!/usr/bin/env python3
"""Baseline-versus-candidate collector for the Knotrel hot-path audit.

Compares the pre-optimization baseline (knotrel commit e1e1181, a clean
`git archive`) with the verified candidate (that commit plus the code-only
working-tree patch archived by this collector). Results are written to a new
`run/` directory inside the campaign directory
(`results/hot-path-audit-20261114/`); `analyze.py` there regenerates every
table from the raw files.

Stages, in order:

1. Provenance. Refuses to run unless knotrel HEAD is the baseline commit and
   the code-only working-tree diff hash equals the verified candidate hash.
   Records revision, branch, staged/unstaged state and diff hashes for both
   repositories, and archives the candidate patch.
2. Materialization. Baseline = `git archive BASELINE`; candidate = the same
   archive plus the archived patch, checked file by file against the live
   working tree. Builds never read the live checkout or its index.
3. Builds with the pinned toolchain (`--locked`, release profile, the
   repository's allocator): knotrel server and `measure_e2e`, the benchmark
   runners, and `tools/hot-path-probes` in timing (mimalloc) and counting
   (`count-alloc`, system allocator) variants. The A/A arm is a byte-identical
   copy of the baseline binaries under another path.
4. Verification of this repository (fmt, Clippy with warnings denied for all
   targets and features, tests and doctests, Rustdoc, collector unit tests).
5. Untimed correctness: initialization oracles (`--validate`), router
   verification digests, and deterministic allocation counts.
6. Timed sessions on a schedule archived before the first observation:
   facade-limited bulk initialization, dynamic link/cut/connectivity
   workloads and router timing, each round running every arm once per cell
   in a counterbalanced order, then the job-tracking microbenchmark and a
   separate end-to-end HTTP section.

Every child's argv, environment, working directory, timestamps, exit status,
stdout and stderr are retained. The collector stops, without reruns, on a
child failure, a host-state violation (AC power, thermal, competing builds)
or a provenance mismatch.

Usage (from the knotrel-benchmarks root, sibling `knotrel` checkout):

    python3 scripts/run_hot_path_audit.py results/hot-path-audit-20261114
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import platform
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_p0_aa import host_state, observe_child, validate_host_state  # noqa: E402

SCHEMA = "knotrel-hot-path-audit-v1"
TOOLCHAIN = "1.100.0"
BASELINE_COMMIT = "e1e11818a762baf07575719456a2158959b2e2c8"
# sha256 of `git diff HEAD -- . ':(exclude)docs'` for the verified candidate
# (see provenance/reconstruct_verified_tree.sh for the link to the verified
# final tree).
CANDIDATE_CODE_DIFF_SHA256 = "8b579f7d8a8db52d499263870b486d0bbaec1775135c4bb50f8e9005a55cc9d7"
SCHEDULE_SEED = 20261115
ARMS = ("base", "cand", "aa")
ROUNDS = 12
SESSIONS = 2
E2E_ROUNDS = 6
QUIET_SECONDS = 60.0
SESSION_COOLDOWN_SECONDS = 120.0
ROUND_COOLDOWN_SECONDS = 5.0
CHILD_TIMEOUT_SECONDS = 180.0
BUILD_TIMEOUT_SECONDS = 1800.0
STREAM_LIMIT_BYTES = 4 * 1024 * 1024
COUNT_REPEATS = 3
MICRO_REPEATS = 3
PROBE_ITERATIONS = 2000
# Explicit child environment; nothing else is inherited.
CHILD_ENV_KEYS = ("PATH", "HOME")

INIT_CELLS = [
    {"engine": engine, "workload": workload, "nodes": nodes}
    for engine in ("compact-bfs", "ett-scan", "hdt")
    for workload, nodes in (("chain-split-rejoin-v1", 200_000), ("sustained-churn-blocks-v1", 100_000))
]
DYNAMIC_CELLS = [
    {"engine": engine, "workload": workload, "nodes": 10_000, "rounds": 200}
    for engine in ("compact-bfs", "ett-scan", "hdt")
    for workload in ("chain-split-rejoin-v1", "sustained-churn-blocks-v1")
]
PROBE_CELLS = [{"metrics": metrics} for metrics in (False, True)]


class CampaignError(RuntimeError):
    """A stop condition: the campaign ends without reruns."""


# ---------------------------------------------------------------------------
# Pure helpers (unit tested)
# ---------------------------------------------------------------------------


def sha256_bytes(data: bytes) -> str:
    """Hex sha256 of `data`."""
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    """Hex sha256 of a file, streamed."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 16):
            digest.update(chunk)
    return digest.hexdigest()


def cell_id(kind: str, cell: Dict[str, Any]) -> str:
    """Stable identifier for one measured cell."""
    if kind == "init":
        return f"init/{cell['engine']}/{cell['workload']}/{cell['nodes']}"
    if kind == "dynamic":
        return f"dynamic/{cell['engine']}/{cell['workload']}/{cell['nodes']}x{cell['rounds']}"
    if kind == "probe":
        return f"probe/timing/metrics-{'on' if cell['metrics'] else 'off'}"
    raise ValueError(kind)


def all_cells() -> List[Dict[str, Any]]:
    """Every timed cell of the main sessions, with its kind and identifier."""
    cells = []
    for kind, group in (("init", INIT_CELLS), ("dynamic", DYNAMIC_CELLS), ("probe", PROBE_CELLS)):
        for cell in group:
            cells.append({"kind": kind, "id": cell_id(kind, cell), **cell})
    return cells


def arm_orders(arms: Sequence[str] = ARMS) -> List[List[str]]:
    """All permutations of the arms, in lexicographic order."""
    return [list(order) for order in itertools.permutations(arms)]


def build_schedule(
    cells: List[Dict[str, Any]],
    rounds: int = ROUNDS,
    sessions: int = SESSIONS,
    seed: int = SCHEDULE_SEED,
    arms: Sequence[str] = ARMS,
) -> Dict[str, Any]:
    """Counterbalanced, interleaved schedule.

    Every round contains each cell once; inside a cell block every arm runs
    once. Across rounds each cell cycles through all arm permutations from a
    seeded starting offset, so with rounds a multiple of len(permutations)
    every order appears equally often and every arm occupies every position
    equally often. Cell order inside a round is shuffled with a seeded RNG.
    Rounds are split evenly into sessions.
    """
    if rounds % sessions:
        raise ValueError("rounds must divide evenly into sessions")
    orders = arm_orders(arms)
    rng = random.Random(seed)
    offsets = {cell["id"]: rng.randrange(len(orders)) for cell in cells}
    entries = []
    sequence = 0
    per_session = rounds // sessions
    for round_index in range(rounds):
        round_cells = list(cells)
        rng.shuffle(round_cells)
        for cell in round_cells:
            order = orders[(offsets[cell["id"]] + round_index) % len(orders)]
            for position, arm in enumerate(order):
                entries.append({
                    "sequence": sequence,
                    "session": round_index // per_session,
                    "round": round_index,
                    "cell": cell["id"],
                    "arm": arm,
                    "position": position,
                    "order": "".join(a[0] for a in order),
                })
                sequence += 1
    return {
        "schema": f"{SCHEMA}-schedule",
        "seed": seed,
        "rounds": rounds,
        "sessions": sessions,
        "arms": list(arms),
        "cells": cells,
        "entries": entries,
    }


def e2e_schedule(rounds: int = E2E_ROUNDS, arms: Sequence[str] = ARMS) -> List[Dict[str, Any]]:
    """End-to-end rounds cycle through arm permutations (separate section)."""
    orders = arm_orders(arms)
    entries = []
    for round_index in range(rounds):
        for position, arm in enumerate(orders[round_index % len(orders)]):
            entries.append({"round": round_index, "arm": arm, "position": position})
    return entries


def command_for(kind: str, cell: Dict[str, Any], binaries: Dict[str, str]) -> List[str]:
    """argv for one timed observation; `binaries` maps tool -> path."""
    if kind == "init":
        return [
            binaries["initialization-profile"], "--engine", cell["engine"],
            "--workload", cell["workload"], "--nodes", str(cell["nodes"]),
            "--rounds", "1", "--seed", "42", "--surface", "facade-limited",
            "--init-mode", "bulk", "--timing", "whole", "--warmup", "1", "--repetitions", "5",
        ]
    if kind == "dynamic":
        return [
            binaries["knotrel-benchmarks"], "--engine", cell["engine"],
            "--workload", cell["workload"], "--nodes", str(cell["nodes"]),
            "--rounds", str(cell["rounds"]), "--seed", "42", "--warmup", "1", "--repetitions", "5",
        ]
    if kind == "probe":
        argv = [binaries["router-probe-timing"], "--mode", "timing", "--iterations", str(PROBE_ITERATIONS)]
        return argv + (["--metrics"] if cell["metrics"] else [])
    raise ValueError(kind)


def code_only_pathspec() -> List[str]:
    """Pathspec selecting the candidate's code (documentation excluded)."""
    return ["--", ".", ":(exclude)docs"]


# ---------------------------------------------------------------------------
# Process and repository helpers
# ---------------------------------------------------------------------------


def run(argv: List[str], cwd: Path, check: bool = True, timeout: float = 600.0,
        env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
    """Run a helper command, capturing bytes."""
    result = subprocess.run(argv, cwd=cwd, capture_output=True, timeout=timeout, env=env)
    if check and result.returncode != 0:
        raise CampaignError(f"{argv} failed ({result.returncode}): {result.stderr.decode(errors='replace')[-2000:]}")
    return result


def git(repo: Path, *args: str) -> bytes:
    """stdout of a git command in `repo`."""
    return run(["git", "-C", str(repo), *args], cwd=repo).stdout


def repository_state(repo: Path) -> Dict[str, Any]:
    """Revision, branch, staged/unstaged status and diff hashes."""
    state = {
        "path": str(repo),
        "head": git(repo, "rev-parse", "HEAD").decode().strip(),
        "branch": git(repo, "branch", "--show-current").decode().strip(),
        "status_porcelain": git(repo, "status", "--porcelain=v1", "--untracked-files=all").decode(),
        "diff_unstaged_sha256": sha256_bytes(git(repo, "diff")),
        "diff_staged_sha256": sha256_bytes(git(repo, "diff", "--cached")),
        "diff_head_sha256": sha256_bytes(git(repo, "diff", "HEAD")),
    }
    state["diff_head_code_only_sha256"] = sha256_bytes(git(repo, "diff", "HEAD", *code_only_pathspec()))
    state["staged_equals_worktree"] = state["diff_unstaged_sha256"] == sha256_bytes(b"")
    return state


def child_env() -> Dict[str, str]:
    """Minimal explicit environment for measured children."""
    env = {key: os.environ[key] for key in CHILD_ENV_KEYS if key in os.environ}
    env["LANG"] = "C"
    env["LC_ALL"] = "C"
    return env


def host_metadata(toolchain: str) -> Dict[str, Any]:
    """Host, OS, CPU, memory, power and compiler metadata."""

    def capture(argv: List[str]) -> Dict[str, Any]:
        try:
            result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
            return {"argv": argv, "exit_code": result.returncode,
                    "stdout": result.stdout, "stderr": result.stderr}
        except Exception as error:  # Recorded, never silently treated as healthy.
            return {"argv": argv, "exit_code": None, "stdout": "", "stderr": str(error)}

    commands = [
        ["uname", "-a"],
        ["rustup", "--version"],
        ["rustup", "toolchain", "list"],
        ["rustc", f"+{toolchain}", "-Vv"],
        ["cargo", f"+{toolchain}", "-Vv"],
        ["python3", "--version"],
        ["git", "--version"],
    ]
    if sys.platform == "darwin":
        commands += [
            ["sw_vers"],
            ["sysctl", "hw.model", "machdep.cpu.brand_string", "hw.ncpu", "hw.physicalcpu",
             "hw.perflevel0.physicalcpu", "hw.perflevel1.physicalcpu", "hw.memsize"],
            ["pmset", "-g"],
            ["pmset", "-g", "batt"],
            ["pmset", "-g", "therm"],
        ]
    else:
        commands += [["nproc"], ["cat", "/proc/meminfo"], ["lscpu"]]
    return {
        "python_platform": platform.platform(),
        "machine": platform.machine(),
        "commands": [capture(argv) for argv in commands],
    }


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------


class Campaign:
    """State and stages of one collector invocation."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.bench = SCRIPTS_DIR.parent
        self.knotrel = Path(args.knotrel).resolve()
        self.campaign = Path(args.campaign).resolve()
        self.out = self.campaign / "run"
        self.work = self.bench / "target-hot-path-audit"
        self.toolchain = args.toolchain
        self.rounds = args.rounds
        self.sessions = args.sessions
        self.e2e_rounds = args.e2e_rounds
        self.quiet = args.quiet_seconds
        self.session_cooldown = args.session_cooldown_seconds
        self.round_cooldown = args.round_cooldown_seconds
        self.enforce_host = not args.no_host_checks
        self.skip_repo_checks = args.skip_repo_checks
        self.ignore_rust_version = args.ignore_rust_version
        self.binaries: Dict[str, Dict[str, str]] = {}
        self.observations = None
        self.sequence = 0

    # -- logging ------------------------------------------------------------

    def log(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message}"
        print(line, flush=True)
        with (self.out / "collector.log").open("a") as handle:
            handle.write(line + "\n")

    def write_json(self, relative: str, value: Any) -> Path:
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise CampaignError(f"refusing to overwrite {path}")
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        return path

    def check_host(self, label: str) -> Dict[str, Any]:
        state = host_state()
        state["label"] = label
        with (self.out / "host-checks.jsonl").open("a") as handle:
            handle.write(json.dumps(state, sort_keys=True) + "\n")
        if self.enforce_host:
            valid, error = validate_host_state(state, enforce_ac=sys.platform == "darwin")
            if not valid:
                raise CampaignError(f"host check failed at {label}: {error}")
        return state

    # -- stage 1: provenance ---------------------------------------------------

    def provenance(self) -> None:
        knotrel = repository_state(self.knotrel)
        bench = repository_state(self.bench)
        if knotrel["head"] != BASELINE_COMMIT:
            raise CampaignError(f"knotrel HEAD {knotrel['head']} is not the baseline {BASELINE_COMMIT}")
        if knotrel["diff_head_code_only_sha256"] != CANDIDATE_CODE_DIFF_SHA256:
            raise CampaignError(
                "knotrel code-only working-tree diff does not match the verified candidate: "
                f"{knotrel['diff_head_code_only_sha256']} != {CANDIDATE_CODE_DIFF_SHA256}")
        code_patch = git(self.knotrel, "diff", "HEAD", "--binary", *code_only_pathspec())
        full_patch = git(self.knotrel, "diff", "HEAD", "--binary")
        (self.out / "candidate").mkdir(parents=True)
        (self.out / "candidate" / "candidate-code.patch").write_bytes(code_patch)
        (self.out / "candidate" / "candidate-full.patch").write_bytes(full_patch)
        self.write_json("provenance.json", {
            "schema": f"{SCHEMA}-provenance",
            "baseline": {
                "repository": "knotrel",
                "commit": BASELINE_COMMIT,
                "materialization": f"git archive {BASELINE_COMMIT}",
            },
            "candidate": {
                "repository": "knotrel",
                "base_commit": BASELINE_COMMIT,
                "materialization": "git archive BASELINE + git apply candidate/candidate-code.patch",
                "code_patch_sha256": sha256_bytes(code_patch),
                "full_patch_sha256": sha256_bytes(full_patch),
                "expected_code_diff_sha256": CANDIDATE_CODE_DIFF_SHA256,
                "note": "Documentation is excluded from the built candidate; its edits do not affect binaries.",
            },
            "knotrel": knotrel,
            "knotrel_benchmarks": bench,
            "harness_files_sha256": self.harness_hashes(),
            "toolchain": self.toolchain,
        })
        self.log(f"provenance ok: code diff {knotrel['diff_head_code_only_sha256']}")

    def harness_hashes(self) -> Dict[str, str]:
        """sha256 of every harness source file used by this campaign."""
        files = [self.bench / "scripts" / "run_hot_path_audit.py", self.bench / "scripts" / "run_p0_aa.py",
                 self.campaign / "analyze.py"]
        probes = self.bench / "tools" / "hot-path-probes"
        files += [path for path in sorted(probes.rglob("*"))
                  if path.is_file() and "target" not in path.relative_to(probes).parts]
        return {str(path.relative_to(self.bench)): sha256_file(path) for path in files}

    # -- stage 2: materialization ---------------------------------------------

    def materialize(self) -> Dict[str, Path]:
        if self.work.exists():
            shutil.rmtree(self.work)
        trees = {}
        for arm in ("base", "cand"):
            tree = self.work / "trees" / arm
            tree.mkdir(parents=True)
            archive = git(self.knotrel, "archive", "--format=tar", BASELINE_COMMIT)
            subprocess.run(["tar", "-x", "-C", str(tree)], input=archive, check=True)
            trees[arm] = tree
        patch = self.out / "candidate" / "candidate-code.patch"
        # A private empty repository: inside the knotrel-benchmarks checkout a
        # plain `git apply` would resolve paths against this repository and
        # silently skip every file.
        apply_git = self.work / "apply.git"
        run(["git", "init", "-q", "--bare", str(apply_git)], cwd=self.work)
        run(["git", f"--git-dir={apply_git}", f"--work-tree={trees['cand']}", "apply",
             "--whitespace=nowarn", str(patch)], cwd=trees["cand"])
        # The reconstructed candidate must equal the live working tree.
        changed = git(self.knotrel, "diff", "HEAD", "--name-only", *code_only_pathspec()).decode().split()
        untracked = git(self.knotrel, "ls-files", "--others", "--exclude-standard").decode().split()
        identity = {}
        for relative in sorted(set(changed + [p for p in untracked if not p.startswith("docs/")])):
            live = self.knotrel / relative
            rebuilt = trees["cand"] / relative
            live_hash = sha256_file(live) if live.exists() else None
            rebuilt_hash = sha256_file(rebuilt) if rebuilt.exists() else None
            if live_hash != rebuilt_hash:
                raise CampaignError(f"candidate reconstruction differs from working tree: {relative}")
            identity[relative] = live_hash
        self.write_json("candidate/reconstruction.json", {
            "files_sha256": identity,
            "untracked_in_knotrel": untracked,
        })
        self.log(f"materialized trees; {len(identity)} candidate files match the working tree")
        return trees

    # -- stage 3: builds --------------------------------------------------------

    def cargo(self, label: str, cwd: Path, target: Path, args: List[str]) -> Dict[str, Any]:
        argv = ["cargo", f"+{self.toolchain}", *args]
        if self.ignore_rust_version:
            argv.append("--ignore-rust-version")
        env = dict(os.environ, CARGO_TARGET_DIR=str(target))
        log = self.out / "builds" / f"{label}.log"
        log.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=BUILD_TIMEOUT_SECONDS)
        log.write_bytes(result.stdout + result.stderr)
        record = {"label": label, "argv": argv, "cwd": str(cwd), "CARGO_TARGET_DIR": str(target),
                  "exit_code": result.returncode, "seconds": round(time.monotonic() - start, 3),
                  "log": str(log.relative_to(self.out))}
        with (self.out / "builds" / "builds.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        if result.returncode != 0:
            raise CampaignError(f"build {label} failed; see {log}")
        return record

    def build(self, trees: Dict[str, Path]) -> None:
        locks = self.out / "locks"
        locks.mkdir(parents=True)
        for arm, tree in trees.items():
            knotrel_target = self.work / f"target-knotrel-{arm}"
            self.cargo(f"knotrel-{arm}", tree, knotrel_target,
                       ["build", "--release", "--locked", "--bin", "knotrel-server", "--example", "measure_e2e"])
            bench = self.work / f"bench-{arm}"
            bench.mkdir()
            for name in ("Cargo.toml", "Cargo.lock", "rust-toolchain.toml"):
                shutil.copy2(self.bench / name, bench / name)
            shutil.copytree(self.bench / "crates", bench / "crates")
            manifest = (bench / "Cargo.toml").read_text()
            original = 'path = "../knotrel/crates/knotrel-core"'
            if original not in manifest:
                raise CampaignError("unexpected knotrel-core path in the benchmark manifest")
            (bench / "Cargo.toml").write_text(manifest.replace(original, f'path = "{tree}/crates/knotrel-core"'))
            bench_target = self.work / f"target-bench-{arm}"
            self.cargo(f"bench-{arm}", bench, bench_target,
                       ["build", "--release", "--locked", "--bin", "knotrel-benchmarks", "--bin", "initialization-profile"])
            probes = self.work / f"probes-{arm}"
            shutil.copytree(self.bench / "tools" / "hot-path-probes", probes)
            manifest = (probes / "Cargo.toml").read_text()
            original = 'path = "../../../knotrel/crates/knotrel-server"'
            if original not in manifest:
                raise CampaignError("unexpected knotrel-server path in the probe manifest")
            (probes / "Cargo.toml").write_text(manifest.replace(original, f'path = "{tree}/crates/knotrel-server"'))
            timing_target = self.work / f"target-probes-{arm}-timing"
            count_target = self.work / f"target-probes-{arm}-count"
            self.cargo(f"probes-{arm}-timing", probes, timing_target, ["build", "--release", "--locked"])
            self.cargo(f"probes-{arm}-count", probes, count_target,
                       ["build", "--release", "--locked", "--features", "count-alloc"])
            for name, path in (("knotrel", tree / "Cargo.lock"), ("bench", bench / "Cargo.lock"),
                               ("probes", probes / "Cargo.lock")):
                shutil.copy2(path, locks / f"{name}-{arm}.Cargo.lock")
            self.binaries[arm] = {
                "knotrel-server": str(knotrel_target / "release" / "knotrel-server"),
                "measure_e2e": str(knotrel_target / "release" / "examples" / "measure_e2e"),
                "knotrel-benchmarks": str(bench_target / "release" / "knotrel-benchmarks"),
                "initialization-profile": str(bench_target / "release" / "initialization-profile"),
                "router-probe-timing": str(timing_target / "release" / "router-probe"),
                "router-probe-count": str(count_target / "release" / "router-probe"),
                "job-tracking": str(timing_target / "release" / "job-tracking"),
            }
        aa = self.work / "aa"
        aa.mkdir()
        self.binaries["aa"] = {}
        for tool, path in self.binaries["base"].items():
            copy = aa / tool
            shutil.copy2(path, copy)
            self.binaries["aa"][tool] = str(copy)
        hashes = {arm: {tool: sha256_file(Path(path)) for tool, path in tools.items()}
                  for arm, tools in self.binaries.items()}
        for tool, digest in hashes["base"].items():
            if hashes["aa"][tool] != digest:
                raise CampaignError(f"A/A copy of {tool} is not byte-identical")
        self.write_json("builds/binaries.json", {"paths": self.binaries, "sha256": hashes})
        self.log("builds complete")

    # -- stage 4: repository verification -------------------------------------

    def verify_repository(self) -> None:
        if self.skip_repo_checks:
            self.log("repository verification skipped (--skip-repo-checks)")
            return
        target = self.work / "target-verify"
        probes_target = self.work / "target-verify-probes"
        checks = [
            ("bench-fmt", self.bench, ["cargo", f"+{self.toolchain}", "fmt", "--all", "--", "--check"], target),
            ("bench-clippy", self.bench, ["cargo", f"+{self.toolchain}", "clippy", "--workspace", "--all-targets",
                                          "--all-features", "--locked", "--", "-D", "warnings"], target),
            ("bench-test", self.bench, ["cargo", f"+{self.toolchain}", "test", "--workspace", "--all-features",
                                        "--locked"], target),
            ("bench-doc", self.bench, ["cargo", f"+{self.toolchain}", "doc", "--workspace", "--no-deps",
                                       "--locked"], target),
            ("probes-fmt", self.bench / "tools" / "hot-path-probes",
             ["cargo", f"+{self.toolchain}", "fmt", "--", "--check"], probes_target),
            ("probes-clippy", self.bench / "tools" / "hot-path-probes",
             ["cargo", f"+{self.toolchain}", "clippy", "--all-targets", "--all-features", "--locked", "--", "-D",
              "warnings"], probes_target),
            ("probes-test", self.bench / "tools" / "hot-path-probes",
             ["cargo", f"+{self.toolchain}", "test", "--all-features", "--locked"], probes_target),
            ("probes-doc", self.bench / "tools" / "hot-path-probes",
             ["cargo", f"+{self.toolchain}", "doc", "--no-deps", "--locked"], probes_target),
            ("collector-tests", self.bench,
             [sys.executable, "-m", "unittest", "discover", "-s", "scripts/tests", "-p", "test_hot_path_audit.py"],
             None),
            ("analysis-tests", self.bench,
             [sys.executable, "-m", "unittest", "discover", "-s", str(self.campaign / "tests"), "-p", "test_*.py"],
             None),
        ]
        results = []
        for label, cwd, argv, target_dir in checks:
            env = dict(os.environ, RUSTDOCFLAGS="-D warnings")
            if target_dir is not None:
                env["CARGO_TARGET_DIR"] = str(target_dir)
            log = self.out / "verification" / f"{label}.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, timeout=BUILD_TIMEOUT_SECONDS)
            log.write_bytes(result.stdout + result.stderr)
            results.append({"label": label, "argv": argv, "cwd": str(cwd), "exit_code": result.returncode,
                            "env": {"RUSTDOCFLAGS": "-D warnings",
                                    "CARGO_TARGET_DIR": str(target_dir) if target_dir else None},
                            "log": str(log.relative_to(self.out))})
            self.log(f"verification {label}: exit {result.returncode}")
        self.write_json("verification/summary.json", results)
        failed = [r["label"] for r in results if r["exit_code"] != 0]
        if failed:
            raise CampaignError(f"repository verification failed: {failed}")

    # -- observations -------------------------------------------------------------

    def observe(self, section: str, label: Dict[str, Any], argv: List[str],
                timeout: float = CHILD_TIMEOUT_SECONDS, wrap_time: bool = True) -> Dict[str, Any]:
        """Runs one child, archives its streams and appends a record."""
        env = child_env()
        observation = observe_child(argv, cwd=str(self.work), env=env, timeout_seconds=timeout,
                                    is_core=wrap_time, output_limit_bytes=STREAM_LIMIT_BYTES)
        sequence = self.sequence
        self.sequence += 1
        stem = f"raw/{section}/{sequence:05d}"
        stdout_path = self.out / f"{stem}.stdout"
        stderr_path = self.out / f"{stem}.stderr"
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(observation["stdout"] or "")
        stderr_path.write_text(observation["raw_stderr"] or "")
        record = {
            "sequence": sequence,
            "section": section,
            **label,
            "argv": argv,
            "full_cmd": observation["full_cmd"],
            "cwd": observation["cwd"],
            "env": env,
            "launch_unix_ns": observation["launch_unix_ns"],
            "wall_duration_ns": observation["wall_duration_ns"],
            "exit_code": observation["exit_code"],
            "timed_out": observation["timed_out"],
            "status": observation["status"],
            "failure_reason": observation["failure_reason"],
            "peak_rss_bytes": observation["peak_rss_bytes"],
            "stdout_path": str(stdout_path.relative_to(self.out)),
            "stderr_path": str(stderr_path.relative_to(self.out)),
            "stdout_sha256": sha256_file(stdout_path),
            "stderr_sha256": sha256_file(stderr_path),
        }
        with (self.out / "observations.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        if record["exit_code"] != 0:
            raise CampaignError(f"child failed ({section} {label}): {record['failure_reason']}")
        return record

    # -- stage 5: correctness -----------------------------------------------------

    def correctness(self) -> None:
        for cell in INIT_CELLS:
            for arm in ("base", "cand"):
                argv = command_for("init", cell, self.binaries[arm])
                argv = argv[:-4] + ["--warmup", "0", "--repetitions", "1", "--validate"]
                self.observe("correctness", {"kind": "init-validate", "cell": cell_id("init", cell), "arm": arm}, argv)
        for metrics in (False, True):
            for repeat in range(2):
                for arm in ("base", "cand"):
                    argv = [self.binaries[arm]["router-probe-timing"], "--mode", "verify"]
                    argv += ["--metrics"] if metrics else []
                    self.observe("correctness", {"kind": "router-verify", "metrics": metrics,
                                                 "repeat": repeat, "arm": arm}, argv)
        for repeat in range(COUNT_REPEATS):
            for metrics in (False, True):
                for arm in (("base", "cand") if repeat % 2 == 0 else ("cand", "base")):
                    argv = [self.binaries[arm]["router-probe-count"], "--mode", "count",
                            "--iterations", str(PROBE_ITERATIONS)]
                    argv += ["--metrics"] if metrics else []
                    self.observe("allocation", {"kind": "router-count", "metrics": metrics,
                                                "repeat": repeat, "arm": arm}, argv)
        self.log("correctness and allocation passes complete")

    # -- stage 6: timed sessions ----------------------------------------------------

    def sessions_run(self) -> None:
        cells = {cell["id"]: cell for cell in all_cells()}
        schedule = build_schedule(list(cells.values()), rounds=self.rounds, sessions=self.sessions)
        e2e = e2e_schedule(self.e2e_rounds)
        self.write_json("schedule.json", {**schedule, "e2e": e2e, "quiet_seconds": self.quiet,
                                          "session_cooldown_seconds": self.session_cooldown,
                                          "round_cooldown_seconds": self.round_cooldown})
        current_session = None
        current_round = None
        for entry in schedule["entries"]:
            if entry["session"] != current_session:
                if current_session is not None:
                    self.log(f"session cooldown {self.session_cooldown}s")
                    time.sleep(self.session_cooldown)
                else:
                    self.log(f"pre-session quiet {self.quiet}s")
                    time.sleep(self.quiet)
                current_session = entry["session"]
            if entry["round"] != current_round:
                if current_round is not None:
                    time.sleep(self.round_cooldown)
                current_round = entry["round"]
                self.check_host(f"round-{current_round}")
                self.log(f"round {current_round + 1}/{self.rounds}")
            cell = cells[entry["cell"]]
            argv = command_for(cell["kind"], cell, self.binaries[entry["arm"]])
            self.observe("timed", {"kind": cell["kind"], "cell": cell["id"], "arm": entry["arm"],
                                   "session": entry["session"], "round": entry["round"],
                                   "position": entry["position"], "order": entry["order"],
                                   "schedule_sequence": entry["sequence"]}, argv)
        self.check_host("after-sessions")
        for repeat in range(MICRO_REPEATS):
            self.observe("micro", {"kind": "job-tracking", "repeat": repeat},
                         [self.binaries["cand"]["job-tracking"], "--samples", "9"], wrap_time=False)
        self.log("end-to-end HTTP section (separate; connection setup may dominate)")
        for entry in e2e:
            tools = self.binaries[entry["arm"]]
            argv = [tools["measure_e2e"], "--scenario", "lifecycle", "--dataset", "large", "--runs", "1",
                    "--spawn-server", "--server-bin", tools["knotrel-server"]]
            self.observe("e2e", {"kind": "e2e-lifecycle-large", **entry}, argv, timeout=600.0, wrap_time=False)
        self.check_host("after-e2e")

    # -- driver ---------------------------------------------------------------------

    def execute(self) -> None:
        if self.out.exists():
            raise CampaignError(f"{self.out} already exists; the collector never overwrites results")
        self.out.mkdir(parents=True)
        started = time.time()
        self.log(f"collector start: {SCHEMA}")
        self.write_json("environment.json", {
            "schema": f"{SCHEMA}-environment",
            "host": host_metadata(self.toolchain),
            "child_env_keys": list(CHILD_ENV_KEYS) + ["LANG", "LC_ALL"],
            "collector": {"argv": sys.argv, "python": sys.version, "script_sha256": sha256_file(Path(__file__))},
            "allocators": {
                "router-probe timing / job-tracking / knotrel-server": "mimalloc (repository allocator)",
                "router-probe count": "system allocator wrapped by stats_alloc (counts only; timings not reported)",
                "knotrel-benchmarks / initialization-profile": "system allocator (benchmark harness default)",
            },
        })
        self.check_host("start")
        self.provenance()
        trees = self.materialize()
        self.build(trees)
        self.verify_repository()
        self.correctness()
        self.sessions_run()
        (self.out / "DONE").write_text(json.dumps({
            "completed_unix": time.time(), "duration_seconds": round(time.time() - started, 1),
            "observations": self.sequence}) + "\n")
        self.log(f"collector complete: {self.sequence} observations")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("campaign", help="campaign directory (results/hot-path-audit-20261114)")
    parser.add_argument("--knotrel", default=str(SCRIPTS_DIR.parent.parent / "knotrel"))
    parser.add_argument("--toolchain", default=TOOLCHAIN)
    parser.add_argument("--rounds", type=int, default=ROUNDS)
    parser.add_argument("--sessions", type=int, default=SESSIONS)
    parser.add_argument("--e2e-rounds", type=int, default=E2E_ROUNDS)
    parser.add_argument("--quiet-seconds", type=float, default=QUIET_SECONDS)
    parser.add_argument("--session-cooldown-seconds", type=float, default=SESSION_COOLDOWN_SECONDS)
    parser.add_argument("--round-cooldown-seconds", type=float, default=ROUND_COOLDOWN_SECONDS)
    parser.add_argument("--no-host-checks", action="store_true",
                        help="record host state without enforcing it (dry runs only; recorded in the log)")
    parser.add_argument("--skip-repo-checks", action="store_true",
                        help="skip repository verification (dry runs only; recorded in the log)")
    parser.add_argument("--ignore-rust-version", action="store_true",
                        help="pass --ignore-rust-version to builds (dry runs on older toolchains only)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    campaign = Campaign(args)
    try:
        campaign.execute()
    except CampaignError as error:
        if campaign.out.exists():
            campaign.log(f"STOPPED: {error}")
            (campaign.out / "STOPPED").write_text(str(error) + "\n")
        else:
            print(f"STOPPED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
