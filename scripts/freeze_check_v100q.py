#!/usr/bin/env python3
"""Freeze-record checks of the v1.0.0 qualification (results/v1.0.0-qualification/PROTOCOL.md §5).

One implementation, used by the Part 1 runner's preflight (``run_v100q_autonomous.py``) and by
``prepare_campaign.sh``. It depends only on the standard library and ``cli_paths.py``, so prepare
runs the copies held by the freeze commit (extracted with ``git show`` into a temporary
directory) instead of a working tree that may differ from them. Command-line paths are confined
(``cli_paths``). A freeze record is accepted only if:

- it is the v1.0.0 record, revision 1, frozen (``frozen_utc`` set, no "NOT FROZEN" status);
- its candidate is the campaign's 40-character commit and its reference commit is
  ``REFERENCE`` (knotrel v0.9.0, plan section 2);
- its core-rule outcome is ``identical`` or ``different`` and ``core_rule.comparison`` holds a
  64-hex ``sha256`` (checked against ``logs/core-rule.json`` of the campaign directory once
  prepare has written it);
- ``set(file_sha256) == set(file_sha256_paths)`` and that list contains every path of
  ``REQUIRED_FROZEN_PATHS``, so no executed file can be dropped from the hash check;
- every listed file has its recorded SHA-256 (on disk for the runner; in the freeze commit's
  tree for prepare, which also checks its own helpers on disk);
- the freeze commit has exactly one parent, ``tooling.commit``, and differs from it only in
  ``results/v1.0.0-qualification/FREEZE.json`` (the freeze commit adds only the record).

    freeze_check_v100q.py record --repo BREPO --freeze FREEZE_SHA --cand CAND_SHA
                                 [--local-root DIR --local PATH ...]
    freeze_check_v100q.py core-rule CAMP   # CAMP/logs/core-rule.json against the clone's FREEZE.json

Exit 0 if every check passes; otherwise 1, one problem per line on stderr.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence

V100 = "results/v1.0.0-qualification"
FREEZE_PATH = f"{V100}/FREEZE.json"
FREEZE_REVISION = 1
CAMPAIGN = "v1.0.0 qualification"
REFERENCE = "223f04c10b0af663b54e269e0970ee10ac1dc6b2"  # knotrel v0.9.0 (plan section 2)
CORE_RULE_OUTCOMES = ("identical", "different")
SHA = re.compile(r"[0-9a-f]{40}")
SHA256 = re.compile(r"[0-9a-f]{64}")

#: Files whose hash every freeze record must carry: the v1.0 bindings and helpers, every frozen
#: module they import, and the probe sources. ``file_sha256_paths`` may list more, never fewer.
REQUIRED_FROZEN_PATHS = (
    f"{V100}/MATRIX.json",
    f"{V100}/PROTOCOL.md",
    f"{V100}/attempt_budget.sh",
    f"{V100}/check_restored.sh",
    f"{V100}/launch_command.sh",
    f"{V100}/launch_env_check.sh",
    f"{V100}/launch_tools.txt",
    f"{V100}/prepare_campaign.sh",
    f"{V100}/run_part3.sh",
    f"{V100}/series_budget.sh",
    f"{V100}/window-multipliers-q3.json",
    "scripts/analyze_bc_qualification.py",
    "scripts/analyze_lifecycle_qualification.py",
    "scripts/analyze_v060_m_supplement.py",
    "scripts/analyze_v060_qualification.py",
    "scripts/analyze_v070_qualification.py",
    "scripts/analyze_v070q3_t5.py",
    "scripts/analyze_v070r_a4.py",
    "scripts/analyze_v070r_qualification.py",
    "scripts/analyze_v090q_t5.py",
    "scripts/analyze_v100q.py",
    "scripts/analyze_v100q_a.py",
    "scripts/analyze_v100q_bc.py",
    "scripts/analyze_v100q_t5.py",
    "scripts/build_site.py",
    "scripts/cli_paths.py",
    "scripts/conformance_gate.py",
    "scripts/conformance_monitor.py",
    "scripts/core_rule_v100q.py",
    "scripts/evaluate_v100q_q.py",
    "scripts/export_v100q_site.py",
    "scripts/freeze_check_v100q.py",
    "scripts/interference_collect.py",
    "scripts/interference_gate.py",
    "scripts/interference_monitor.py",
    "scripts/launcher_audit.py",
    "scripts/part1_failures_v100q.py",
    "scripts/prepare_bc_qualification.py",
    "scripts/probe_compat_v100q.py",
    "scripts/report_v070q3_bc.py",
    "scripts/report_v100q_bc.py",
    "scripts/run_baseline.py",
    "scripts/run_lifecycle_qualification.py",
    "scripts/run_p0_aa.py",
    "scripts/run_scale.py",
    "scripts/run_v060_qualification.py",
    "scripts/run_v070q3_autonomous.py",
    "scripts/run_v070q3_t5.py",
    "scripts/run_v070r_collect.py",
    "scripts/run_v090q_autonomous.py",
    "scripts/run_v100q_autonomous.py",
    "scripts/run_v100q_collect.py",
    "scripts/run_v100q_q.py",
    "scripts/tests/test_v100q.py",
    "scripts/tests/test_v100q_review.py",
    "tools/contention-probe/Cargo.lock",
    "tools/contention-probe/Cargo.toml",
    "tools/contention-probe/src/main.rs",
    "tools/lifecycle-probes/Cargo.lock",
    "tools/lifecycle-probes/Cargo.toml",
    "tools/lifecycle-probes/build.rs",
    "tools/lifecycle-probes/src/bin/core-lifecycle.rs",
    "tools/lifecycle-probes/src/bin/http-lifecycle.rs",
    "tools/lifecycle-probes/src/bin/memory-peak.rs",
    "tools/lifecycle-probes/src/bin/release-cells.rs",
    "tools/lifecycle-probes/src/churn.rs",
    "tools/lifecycle-probes/src/lib.rs",
)

#: Helpers prepare_campaign.sh runs from its own directory before the frozen clone exists
#: (finding N6): each must equal the freeze record's hash.
PREPARE_HELPERS = (
    f"{V100}/prepare_campaign.sh",
    f"{V100}/series_budget.sh",
    f"{V100}/attempt_budget.sh",
    f"{V100}/check_restored.sh",
    f"{V100}/launch_command.sh",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> Optional[str]:
    """SHA-256 of ``path``, or None if it cannot be read."""
    try:
        return sha256_bytes(Path(path).read_bytes())
    except OSError:
        return None


def record_problems(freeze: Dict[str, Any], cand: str, reference: str = REFERENCE) -> List[str]:
    """Identity, state and completeness of the record itself (no file or Git access)."""
    problems = []
    if freeze.get("campaign") != CAMPAIGN or freeze.get("revision") != FREEZE_REVISION:
        problems.append(f"freeze {freeze.get('campaign')!r} revision {freeze.get('revision')}, "
                        f"expected {CAMPAIGN!r} revision {FREEZE_REVISION}")
    if not freeze.get("frozen_utc") or "NOT FROZEN" in str(freeze.get("status", "")):
        problems.append("the freeze record is a draft (no frozen_utc, or status NOT FROZEN)")
    if not SHA.fullmatch(cand or ""):
        problems.append(f"candidate {cand!r} is not a 40-character commit")
    candidate = (freeze.get("candidate") or {}).get("commit")
    if candidate != cand:
        problems.append(f"freeze candidate {candidate} is not {cand}")
    ref = (freeze.get("reference") or {}).get("commit")
    if ref != reference:
        problems.append(f"freeze reference commit {ref!r} is not {reference} (a newer 0.9.x needs REFERENCE, "
                        "prepare_campaign.sh REF and this check updated before the freeze)")
    core = freeze.get("core_rule") or {}
    if core.get("outcome") not in CORE_RULE_OUTCOMES:
        problems.append(f"freeze core_rule.outcome is {core.get('outcome')!r}, expected one of {CORE_RULE_OUTCOMES}")
    comparison = core.get("comparison")
    if not isinstance(comparison, dict) or not SHA256.fullmatch(str(comparison.get("sha256", ""))):
        problems.append("freeze core_rule.comparison has no 64-hex sha256 of core-rule.json")
    tooling = (freeze.get("tooling") or {}).get("commit")
    if not SHA.fullmatch(str(tooling or "")):
        problems.append(f"freeze tooling.commit {tooling!r} is not a 40-character commit")
    problems += path_set_problems(freeze)
    return problems


def path_set_problems(freeze: Dict[str, Any], required: Iterable[str] = REQUIRED_FROZEN_PATHS) -> List[str]:
    """``file_sha256`` covers exactly ``file_sha256_paths``, which covers ``required``."""
    paths, hashes = freeze.get("file_sha256_paths"), freeze.get("file_sha256")
    if not isinstance(paths, list) or not isinstance(hashes, dict):
        return ["freeze file_sha256_paths is not a list or file_sha256 is not a mapping"]
    problems = []
    listed, hashed = set(paths), set(hashes)
    if len(listed) != len(paths):
        problems.append("freeze file_sha256_paths lists a path twice")
    if listed != hashed:
        problems.append(f"freeze file_sha256 keys differ from file_sha256_paths: missing hashes "
                        f"{sorted(listed - hashed)[:5]}, unlisted hashes {sorted(hashed - listed)[:5]}")
    missing = sorted(set(required) - listed)
    if missing:
        problems.append(f"freeze file_sha256_paths lacks required files: {missing[:5]}")
    bad = [p for p, h in hashes.items() if not SHA256.fullmatch(str(h))]
    if bad:
        problems.append(f"freeze file_sha256 values are not SHA-256 digests: {bad[:5]}")
    return problems


def file_problems(freeze: Dict[str, Any], digest: Callable[[str], Optional[str]]) -> List[str]:
    """Every hashed file must have its recorded digest (``digest(path)`` gives the actual one)."""
    hashes = freeze.get("file_sha256")
    if not isinstance(hashes, dict):
        return ["freeze file_sha256 is not a mapping"]
    bad = [p for p, h in sorted(hashes.items()) if digest(p) != h]
    return [f"frozen files differ: {bad[:5]}"] if bad else []


def local_problems(freeze: Dict[str, Any], root: Path, paths: Sequence[str]) -> List[str]:
    """Files run from outside the frozen clone (prepare's helpers) must equal the record."""
    hashes = freeze.get("file_sha256") or {}
    base = Path(root).resolve()
    problems = []
    for path in paths:
        target = (base / path).resolve()
        if path not in PREPARE_HELPERS or not target.is_relative_to(base):
            problems.append(f"{path} is not one of the prepare helpers {PREPARE_HELPERS}")
        elif path not in hashes:
            problems.append(f"{path} is not in the freeze record's file_sha256")
        elif sha256_file(target) != hashes[path]:
            problems.append(f"{Path(root) / path} differs from the freeze record (run prepare from the freeze commit)")
    return problems


def git_problems(freeze: Dict[str, Any], freeze_commit: str, git: Callable[..., str]) -> List[str]:
    """The freeze commit is the only child of ``tooling.commit`` and adds only FREEZE.json."""
    tooling = str((freeze.get("tooling") or {}).get("commit") or "")
    if not SHA.fullmatch(tooling):
        return [f"freeze tooling.commit {tooling!r} is not a 40-character commit"]
    problems = []
    try:
        parents = git("rev-parse", f"{freeze_commit}^@").split()
        changed = [x for x in git("diff", "--name-only", tooling, freeze_commit).splitlines() if x.strip()]
    except (OSError, subprocess.CalledProcessError) as error:
        return [f"git check of the freeze commit failed: {error}"]
    if parents != [tooling]:
        problems.append(f"freeze commit {freeze_commit} has parents {parents}, expected exactly tooling.commit {tooling}")
    if changed != [FREEZE_PATH]:
        problems.append(f"freeze commit differs from tooling.commit in {changed[:5]}, expected only {FREEZE_PATH}")
    return problems


def core_rule_problems(freeze: Dict[str, Any], core_rule_json: Path) -> List[str]:
    """``core_rule.comparison.sha256`` must be the SHA-256 of the campaign's ``logs/core-rule.json``,
    and that file's outcome the record's."""
    core = freeze.get("core_rule") or {}
    recorded = (core.get("comparison") or {}).get("sha256") if isinstance(core.get("comparison"), dict) else None
    actual = sha256_file(core_rule_json)
    if actual is None:
        return [f"no {core_rule_json}: prepare_campaign.sh writes it"]
    problems = []
    if actual != recorded:
        problems.append(f"{core_rule_json} SHA-256 {actual} is not the freeze record's core_rule.comparison {recorded}")
    try:
        outcome = json.loads(Path(core_rule_json).read_text()).get("outcome")
    except ValueError:
        outcome = None
    if outcome != core.get("outcome"):
        problems.append(f"{core_rule_json} outcome {outcome!r} differs from the freeze record's {core.get('outcome')!r}")
    return problems


def git_runner(repo: Path) -> Callable[..., str]:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout
    return git


def git_blob_digest(repo: Path, commit: str) -> Callable[[str], Optional[str]]:
    def digest(path: str) -> Optional[str]:
        proc = subprocess.run(["git", "-C", str(repo), "show", f"{commit}:{path}"], capture_output=True)
        return sha256_bytes(proc.stdout) if proc.returncode == 0 else None
    return digest


def check_commit(repo: Path, freeze_commit: str, cand: str, local_root: Optional[Path] = None,
                 local: Sequence[str] = ()) -> List[str]:
    """Every check of a freeze commit in ``repo`` (prepare_campaign.sh, before any clone)."""
    git = git_runner(repo)
    try:
        freeze = json.loads(git("show", f"{freeze_commit}:{FREEZE_PATH}"))
    except (subprocess.CalledProcessError, ValueError) as error:
        return [f"FREEZE {freeze_commit} has no readable {FREEZE_PATH}: {error}"]
    problems = record_problems(freeze, cand)
    problems += file_problems(freeze, git_blob_digest(repo, freeze_commit))
    problems += git_problems(freeze, freeze_commit, git)
    if local_root is not None:
        problems += local_problems(freeze, local_root, local)
    return problems


def main(argv: Optional[Sequence[str]] = None) -> int:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from cli_paths import confined_directory
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record")
    rec.add_argument("--repo", type=Path, required=True)
    rec.add_argument("--freeze", required=True)
    rec.add_argument("--cand", required=True)
    rec.add_argument("--local-root", type=Path)
    rec.add_argument("--local", action="append", default=[])
    core = sub.add_parser("core-rule")
    core.add_argument("camp", type=Path)
    args = parser.parse_args(argv)
    if args.command == "record":
        if args.local and args.local_root is None:
            parser.error("--local needs --local-root")
        if not SHA.fullmatch(args.freeze):
            parser.error("--freeze must be a 40-character commit")
        repo = confined_directory(args.repo, "--repo")
        local_root = confined_directory(args.local_root, "--local-root") if args.local_root else None
        problems = check_commit(repo, args.freeze, args.cand, local_root, args.local)
    else:
        camp = confined_directory(args.camp, "CAMP")
        freeze = json.loads((camp / "src/cand/knotrel-benchmarks" / FREEZE_PATH).read_text())
        problems = core_rule_problems(freeze, camp / "logs" / "core-rule.json")
    for p in problems:
        print(p, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
