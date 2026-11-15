#!/usr/bin/env python3
"""Collector for the knotrel M6.5 metrics-overhead qualification.

Measures the cost of enabling the opt-in Prometheus metrics
(`KNOTREL_METRICS_ENABLED`) on the in-process `knotrel-server` router, using
one release build of `tools/hot-path-probes` `router-probe` (mimalloc, like
the server) against the knotrel working tree:

- arm `off`: the binary without `--metrics`;
- arm `on`: the same binary with `--metrics`;
- arm `aa`: a byte-identical copy of the binary under another path, without
  `--metrics` (A/A noise reference).

Budget, approved by the owner on 2026-11-15 before any measurement (knotrel
`docs/observability-contract.md`, section 6): per scenario, the paired median
slowdown of `on` versus `off` must be at most 3% and the upper bound of its
95% bootstrap interval at most 6%. Verdicts:

- PASS: median <= 3% and interval upper bound <= 6%;
- REGRESSION: interval lower bound > 3% and median above the A/A bound
  (a confirmed slowdown beyond the budget; blocks Acceptance M6);
- INCONCLUSIVE: anything else (disclosed).

Stopping rule: PRIMARY_ROUNDS counterbalanced rounds; if any scenario is not
PASS, exactly one extension of EXTENSION_ROUNDS rounds runs, and the final
verdicts use all rounds. No further rounds are ever added.

Identity: knotrel HEAD must be BASELINE_COMMIT; the measured tree is
identified by the sha256 of the code diff (`git diff HEAD` excluding `docs/`
and `*.md`) together with every untracked code file, checked before the build,
after the build and after the last observation.

Usage: python3 scripts/run_metrics_overhead.py <campaign-directory>
Writes <campaign-directory>/run/ and refuses to overwrite it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from run_hot_path_audit import (  # noqa: E402
    CampaignError,
    arm_orders,
    child_env,
    host_metadata,
    repository_state,
    sha256_bytes,
    sha256_file,
)
from run_p0_aa import host_state, observe_child, validate_host_state  # noqa: E402

SCHEMA = "knotrel-metrics-overhead-v1"
TOOLCHAIN = "1.100.0"
BASELINE_COMMIT = "e1e11818a762baf07575719456a2158959b2e2c8"
ARMS = ("off", "on", "aa")
PRIMARY_ROUNDS = 24
EXTENSION_ROUNDS = 12
SESSIONS = 2
QUIET_SECONDS = 60.0
SESSION_COOLDOWN_SECONDS = 120.0
ROUND_COOLDOWN_SECONDS = 5.0
PROBE_ITERATIONS = 2000
CHILD_TIMEOUT_SECONDS = 180.0
STREAM_LIMIT_BYTES = 4 * 1024 * 1024
BUDGET_MEDIAN_PCT = 3.0
BUDGET_UPPER_PCT = 6.0
BOOTSTRAP_SEED = 20261115
BOOTSTRAP_RESAMPLES = 10_000
CODE_PATHSPEC = ["--", ".", ":(exclude)docs", ":(exclude)*.md"]


# ---------------------------------------------------------------------------
# Pure functions (unit-tested; reused by the campaign's analyze.py)
# ---------------------------------------------------------------------------


def schedule(rounds: int, first_round: int = 0, arms: Sequence[str] = ARMS) -> List[Dict[str, Any]]:
    """Counterbalanced entries: round r uses permutation (first_round + r) mod 6."""
    orders = arm_orders(arms)
    entries = []
    for offset in range(rounds):
        round_index = first_round + offset
        for position, arm in enumerate(orders[round_index % len(orders)]):
            entries.append({"round": round_index, "arm": arm, "position": position})
    return entries


def parse_probe(stdout: str) -> Dict[str, float]:
    """Nanoseconds per request for each scenario of one timing process."""
    values = {}
    for line in stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            record = json.loads(line)
            values[record["scenario"]] = int(record["elapsed_ns"]) / record["requests"]
    return values


def bootstrap_median_ci(values: Sequence[float], seed: int = BOOTSTRAP_SEED,
                        resamples: int = BOOTSTRAP_RESAMPLES) -> Tuple[float, float]:
    """95% percentile-bootstrap interval of the median (deterministic)."""
    import random

    rng = random.Random(seed)
    data = list(values)
    medians = sorted(statistics.median(rng.choices(data, k=len(data))) for _ in range(resamples))
    return medians[int(0.025 * resamples)], medians[int(0.975 * resamples) - 1]


def paired_changes(by_round: Dict[int, Dict[str, float]], arm: str, ref: str = "off") -> List[float]:
    """Per-round percent change of `arm` against `ref` (positive = slower)."""
    return [100.0 * (values[arm] / values[ref] - 1.0)
            for _, values in sorted(by_round.items()) if arm in values and ref in values]


def budget_verdict(median: float, ci: Tuple[float, float], aa_bound: float) -> str:
    """PASS / REGRESSION / INCONCLUSIVE under the approved budget."""
    if median <= BUDGET_MEDIAN_PCT and ci[1] <= BUDGET_UPPER_PCT:
        return "PASS"
    if ci[0] > BUDGET_MEDIAN_PCT and median > aa_bound:
        return "REGRESSION"
    return "INCONCLUSIVE"


def evaluate(by_round: Dict[int, Dict[str, float]]) -> Dict[str, Any]:
    """Paired statistics and verdict for one scenario."""
    aa = paired_changes(by_round, "aa")
    on = paired_changes(by_round, "on")
    aa_ci = bootstrap_median_ci(aa)
    aa_bound = max(abs(aa_ci[0]), abs(aa_ci[1]))
    on_ci = bootstrap_median_ci(on)
    on_median = statistics.median(on)
    return {
        "n": len(on),
        "aa": {"changes_pct": aa, "median_pct": statistics.median(aa), "ci95_pct": list(aa_ci),
               "noise_bound_pct": aa_bound},
        "on": {"changes_pct": on, "median_pct": on_median, "ci95_pct": list(on_ci),
               "verdict": budget_verdict(on_median, on_ci, aa_bound)},
    }


def by_scenario(observations: Sequence[Dict[str, Any]], root: Path) -> Dict[str, Dict[int, Dict[str, float]]]:
    """Scenario -> round -> arm -> ns/request, from timed observations."""
    table: Dict[str, Dict[int, Dict[str, float]]] = {}
    for record in observations:
        if record["section"] != "timed":
            continue
        stdout = (root / record["stdout_path"]).read_text()
        for scenario, value in parse_probe(stdout).items():
            table.setdefault(scenario, {}).setdefault(record["round"], {})[record["arm"]] = value
    return table


def code_identity(repo: Path) -> Dict[str, Any]:
    """sha256 of the code diff plus every untracked code file (docs and *.md excluded)."""
    diff = subprocess.run(["git", "-C", str(repo), "diff", "HEAD", "--binary", *CODE_PATHSPEC],
                          capture_output=True, check=True).stdout
    untracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard", "-z", *CODE_PATHSPEC],
        capture_output=True, check=True).stdout.decode().split("\0")
    files = sorted(path for path in untracked if path)
    digest = hashlib.sha256(diff)
    listed = {}
    for path in files:
        file_hash = sha256_file(repo / path)
        listed[path] = file_hash
        digest.update(f"\0{path}\0{file_hash}".encode())
    return {"code_diff_sha256": sha256_bytes(diff), "untracked_code_files": listed,
            "identity_sha256": digest.hexdigest()}


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------


class Campaign:
    """One collector invocation."""

    def __init__(self, args: argparse.Namespace) -> None:
        self.bench = SCRIPTS_DIR.parent
        self.knotrel = Path(args.knotrel).resolve()
        self.out = Path(args.campaign).resolve() / "run"
        self.work = self.bench / "target-metrics-overhead"
        self.quiet = args.quiet_seconds
        self.session_cooldown = args.session_cooldown_seconds
        self.round_cooldown = args.round_cooldown_seconds
        self.enforce_host = not args.no_host_checks
        self.primary_rounds = args.primary_rounds
        self.extension_rounds = args.extension_rounds
        self.identity: Dict[str, Any] = {}
        self.binary: Dict[str, Path] = {}
        self.sequence = 0
        self.records: List[Dict[str, Any]] = []

    def log(self, message: str) -> None:
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {message}"
        print(line, flush=True)
        with (self.out / "collector.log").open("a") as handle:
            handle.write(line + "\n")

    def write_json(self, relative: str, value: Any) -> None:
        path = self.out / relative
        if path.exists():
            raise CampaignError(f"refusing to overwrite {path}")
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")

    def check_host(self, label: str) -> None:
        state = host_state()
        state["label"] = label
        with (self.out / "host-checks.jsonl").open("a") as handle:
            handle.write(json.dumps(state, sort_keys=True) + "\n")
        if self.enforce_host:
            valid, error = validate_host_state(state, enforce_ac=sys.platform == "darwin")
            if not valid:
                raise CampaignError(f"host check failed at {label}: {error}")

    def check_identity(self, label: str) -> None:
        current = code_identity(self.knotrel)
        if current["identity_sha256"] != self.identity["identity_sha256"]:
            raise CampaignError(f"knotrel code changed during the campaign ({label})")
        self.log(f"identity unchanged at {label}: {current['identity_sha256']}")

    def provenance(self) -> None:
        knotrel = repository_state(self.knotrel)
        if knotrel["head"] != BASELINE_COMMIT:
            raise CampaignError(f"knotrel HEAD {knotrel['head']} is not {BASELINE_COMMIT}")
        self.identity = code_identity(self.knotrel)
        patch = subprocess.run(["git", "-C", str(self.knotrel), "diff", "HEAD", "--binary", *CODE_PATHSPEC],
                               capture_output=True, check=True).stdout
        (self.out / "tree").mkdir()
        (self.out / "tree" / "code.patch").write_bytes(patch)
        for path in self.identity["untracked_code_files"]:
            target = self.out / "tree" / "untracked" / path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.knotrel / path, target)
        self.write_json("provenance.json", {
            "schema": f"{SCHEMA}-provenance",
            "knotrel": knotrel,
            "knotrel_benchmarks": repository_state(self.bench),
            "measured_tree": {"base_commit": BASELINE_COMMIT, **self.identity,
                              "reconstruction": "git archive BASE + git apply tree/code.patch + copy tree/untracked/"},
            "budget": {"median_pct_max": BUDGET_MEDIAN_PCT, "ci95_upper_pct_max": BUDGET_UPPER_PCT,
                       "approved": "2026-11-15, before measurement"},
        })
        self.log(f"provenance ok: identity {self.identity['identity_sha256']}")

    def build(self) -> None:
        target = self.work / "target"
        log = self.out / "build.log"
        argv = ["cargo", f"+{TOOLCHAIN}", "build", "--release", "--locked", "--bin", "router-probe"]
        with log.open("wb") as handle:
            result = subprocess.run(argv, cwd=self.bench / "tools" / "hot-path-probes",
                                    env={**child_env(), "CARGO_TARGET_DIR": str(target)},
                                    stdout=handle, stderr=subprocess.STDOUT, timeout=1800)
        if result.returncode != 0:
            raise CampaignError(f"build failed; see {log}")
        built = target / "release" / "router-probe"
        for arm in ("off", "aa"):
            destination = self.work / arm / "router-probe"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(built, destination)
            destination.chmod(0o755)
            self.binary[arm] = destination
        self.binary["on"] = self.binary["off"]
        hashes = {arm: sha256_file(path) for arm, path in self.binary.items()}
        if len(set(hashes.values())) != 1:
            raise CampaignError(f"A/A copy differs: {hashes}")
        self.write_json("binaries.json", {"router-probe": {arm: str(path) for arm, path in self.binary.items()},
                                          "sha256": hashes["off"]})
        self.check_identity("after-build")

    def argv(self, arm: str, mode: str = "timing") -> List[str]:
        argv = [str(self.binary[arm]), "--mode", mode]
        if mode == "timing":
            argv += ["--iterations", str(PROBE_ITERATIONS)]
        return argv + (["--metrics"] if arm == "on" else [])

    def observe(self, section: str, label: Dict[str, Any], argv: List[str]) -> Dict[str, Any]:
        env = child_env()
        observation = observe_child(argv, cwd=str(self.work), env=env, timeout_seconds=CHILD_TIMEOUT_SECONDS,
                                    is_core=True, output_limit_bytes=STREAM_LIMIT_BYTES)
        stem = f"raw/{section}/{self.sequence:05d}"
        stdout_path, stderr_path = self.out / f"{stem}.stdout", self.out / f"{stem}.stderr"
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(observation["stdout"] or "")
        stderr_path.write_text(observation["raw_stderr"] or "")
        record = {"sequence": self.sequence, "section": section, **label, "argv": argv, "env": env,
                  "launch_unix_ns": observation["launch_unix_ns"],
                  "wall_duration_ns": observation["wall_duration_ns"],
                  "exit_code": observation["exit_code"], "timed_out": observation["timed_out"],
                  "failure_reason": observation["failure_reason"],
                  "peak_rss_bytes": observation["peak_rss_bytes"],
                  "stdout_path": str(stdout_path.relative_to(self.out)),
                  "stderr_path": str(stderr_path.relative_to(self.out)),
                  "stdout_sha256": sha256_file(stdout_path), "stderr_sha256": sha256_file(stderr_path)}
        self.sequence += 1
        with (self.out / "observations.jsonl").open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
        self.records.append(record)
        if record["exit_code"] != 0:
            raise CampaignError(f"child failed ({section} {label}): {record['failure_reason']}")
        return record

    def verify(self) -> None:
        for arm in ("off", "on"):
            self.observe("verify", {"arm": arm}, self.argv(arm, "verify"))
        self.log("verify pass complete")

    def timed(self, entries: List[Dict[str, Any]], phase: str) -> None:
        per_session = max(1, len({e["round"] for e in entries}) // SESSIONS)
        first = entries[0]["round"]
        current_round = None
        for entry in entries:
            if entry["round"] != current_round:
                offset = entry["round"] - first
                if offset == 0:
                    self.log(f"{phase}: quiet {self.quiet}s")
                    time.sleep(self.quiet)
                elif offset % per_session == 0:
                    self.log(f"{phase}: session cooldown {self.session_cooldown}s")
                    time.sleep(self.session_cooldown)
                else:
                    time.sleep(self.round_cooldown)
                current_round = entry["round"]
                self.check_host(f"{phase}-round-{current_round}")
                self.log(f"{phase}: round {current_round + 1}")
            self.observe("timed", {"phase": phase, **entry}, self.argv(entry["arm"]))

    def decide_extension(self) -> Dict[str, str]:
        table = by_scenario(self.records, self.out)
        return {scenario: evaluate(rounds)["on"]["verdict"] for scenario, rounds in sorted(table.items())}

    def execute(self) -> None:
        if self.out.exists():
            raise CampaignError(f"{self.out} already exists; the collector never overwrites results")
        self.out.mkdir(parents=True)
        started = time.time()
        self.log(f"collector start: {SCHEMA}")
        self.write_json("environment.json", {
            "schema": f"{SCHEMA}-environment", "host": host_metadata(TOOLCHAIN),
            "collector": {"argv": sys.argv, "python": sys.version,
                          "script_sha256": sha256_file(Path(__file__))},
            "allocator": "mimalloc (router-probe default build, like knotrel-server)",
            "logging": "no tracing subscriber installed in the probe: log statements are disabled in every arm",
        })
        self.provenance()
        self.build()
        self.verify()
        primary = schedule(self.primary_rounds)
        self.timed(primary, "primary")
        verdicts = self.decide_extension()
        self.log(f"primary verdicts: {verdicts}")
        extension: List[Dict[str, Any]] = []
        if any(v != "PASS" for v in verdicts.values()):
            extension = schedule(self.extension_rounds, first_round=self.primary_rounds)
            self.timed(extension, "extension")
            self.log(f"final verdicts: {self.decide_extension()}")
        self.write_json("schedule.json", {"schema": f"{SCHEMA}-schedule", "arms": list(ARMS),
                                          "primary": primary, "extension": extension,
                                          "primary_verdicts": verdicts,
                                          "quiet_seconds": self.quiet,
                                          "session_cooldown_seconds": self.session_cooldown,
                                          "round_cooldown_seconds": self.round_cooldown})
        self.check_host("after-timed")
        self.check_identity("end")
        self.write_json("DONE", {"observations": self.sequence,
                                 "duration_seconds": round(time.time() - started, 1)})
        self.log(f"collector complete: {self.sequence} observations")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("campaign", help="campaign directory; run/ is created inside it")
    parser.add_argument("--knotrel", default=str(SCRIPTS_DIR.parent.parent / "knotrel"))
    parser.add_argument("--primary-rounds", type=int, default=PRIMARY_ROUNDS)
    parser.add_argument("--extension-rounds", type=int, default=EXTENSION_ROUNDS)
    parser.add_argument("--quiet-seconds", type=float, default=QUIET_SECONDS)
    parser.add_argument("--session-cooldown-seconds", type=float, default=SESSION_COOLDOWN_SECONDS)
    parser.add_argument("--round-cooldown-seconds", type=float, default=ROUND_COOLDOWN_SECONDS)
    parser.add_argument("--no-host-checks", action="store_true",
                        help="record host checks without enforcing them (never for official runs)")
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    campaign = Campaign(parse_args(argv))
    try:
        campaign.execute()
    except (CampaignError, subprocess.SubprocessError, OSError) as error:
        if campaign.out.exists():
            (campaign.out / "STOPPED").write_text(f"{type(error).__name__}: {error}\n")
            campaign.log(f"STOPPED: {error}")
        else:
            print(f"STOPPED: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
