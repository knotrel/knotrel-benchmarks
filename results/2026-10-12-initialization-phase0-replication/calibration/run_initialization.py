#!/usr/bin/env python3
"""Collect a bounded Phase-0 initialization baseline; no optimization arms.

Run calibration first, then baseline and limits into distinct new directories.
Every observation uses one fresh process, zero warmups, and one repetition.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
import time
import subprocess

from run_baseline import ROOT, CORE, command, hashes, source_patch, optional_command
from run_scale import peak_rss, run_measurement

ENGINES = ["compact-bfs", "ett-scan", "hdt"]
TOPOLOGIES = [
    ("chain-split-rejoin-v1", 100_000),
    ("cycle-alternatives-v1", 100_000),
    ("components-join-split-v1", 100_000),
    ("dense-bridge-churn-v1", 512),
]
SETUP_PHASES = [
    "node_vector_ns", "adapter_validation_ns", "vertex_registration_ns",
    "constructor_other_ns", "initial_edges_ns", "setup_other_ns",
]


def cases(stage):
    """Six process trials per cell; paired controls have balanced AB/BA order."""
    topologies = (TOPOLOGIES[-1:] if stage == "calibration" else
                  TOPOLOGIES[:1] if stage == "limits" else TOPOLOGIES)
    groups = []
    for workload, nodes in topologies:
        for engine in ENGINES:
            for trial in range(6):
                if stage == "calibration":
                    arms = [("adapter", "whole"), ("adapter", "phases")]
                elif stage == "limits":
                    arms = [("facade", "phases"), ("facade-limited", "phases")]
                else:
                    arms = [("adapter", "phases")]
                if trial % 2:
                    arms.reverse()
                groups.append([
                    dict(workload=workload, nodes=nodes, engine=engine, trial=trial,
                         surface=surface, timing=timing)
                    for surface, timing in arms
                ])
    random.Random(42).shuffle(groups)
    return [case for group in groups for case in group]


def quantile(values, probability):
    """Linear-interpolated sample quantile, also used for descriptive quartiles."""
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def distribution(values):
    """No pooling of inner operation percentiles or fastest-run selection."""
    return dict(n=len(values), median=statistics.median(values), min=min(values),
                q1=quantile(values, .25), q3=quantile(values, .75), max=max(values))


def paired_interval(values):
    """Seeded paired bootstrap of the median; exploratory with six pairs."""
    rng = random.Random(42)
    boot = [statistics.median(rng.choices(values, k=len(values))) for _ in range(5000)]
    return [quantile(boot, .025), quantile(boot, .975)]


def validate_report(report, case):
    """Reject wrong boundaries, identities, empty phases, or non-build-only runs."""
    if (report["schema_version"] != 1 or report["measurement"] != "initialization-only"
            or report["debug_assertions"] or report["warmup"] != 0
            or report["validated_dynamic_continuation"]
            or report["surface"] != case["surface"] or report["timing"] != case["timing"]
            or report["workload"] != case["workload"]
            or report["config"] != {"nodes": case["nodes"], "rounds": 1, "seed": 42}
            or len(report["repetitions"]) != 1):
        raise ValueError("unexpected initialization report contract")
    expected_engines = {
        "compact-bfs": "knotrel-core/compact-bfs-v1",
        "ett-scan": "knotrel-core/ett-pruned-v2",
        "hdt": "knotrel-core/hdt-sparse-levels-v3",
    }
    if report["engine"] != expected_engines[case["engine"]]:
        raise ValueError("wrong engine identity")
    run = report["repetitions"][0]
    if not 0 < run["setup_ns"] <= run["total_initialization_ns"]:
        raise ValueError("invalid enclosing timing")
    if case["timing"] == "phases":
        p = run["phases"]
        if sum(p[k] or 0 for k in SETUP_PHASES) != run["setup_ns"]:
            raise ValueError("setup phase accounting mismatch")
        if (p["input_generation_ns"] + p["trace_encoding_fingerprint_ns"]
                + run["setup_ns"] != run["total_initialization_ns"]):
            raise ValueError("total phase accounting mismatch")
        if (p["adapter_validation_ns"] is None) != (case["surface"] != "adapter"):
            raise ValueError("wrong validation phase applicability")
        if any(v is not None and v < 0 for v in p.values()):
            raise ValueError("negative phase")
        if not p["vertex_registration_ns"] or not p["initial_edges_ns"]:
            raise ValueError("unresolved principal phase")
    elif "phases" in run:
        raise ValueError("whole-timer control unexpectedly has phase timing")
    return run


def analyze(records, stage):
    """Keep cell distributions and individual paired deltas, not pooled engines."""
    cells = {}
    for record in records:
        key = (record["workload"], record["engine"], record["surface"], record["timing"])
        cells.setdefault(key, []).append(record)
    rows = []
    for key, group in sorted(cells.items()):
        runs = [r["run"] for r in group]
        row = dict(zip(["workload", "engine", "surface", "timing"], key))
        row["nodes"] = group[0]["nodes"]
        row["initial_edges"] = runs[0]["initial_edges"]
        row["metrics"] = {k: distribution([r[k] for r in runs])
                          for k in ["setup_ns", "total_initialization_ns"]}
        row["metrics"]["peak_process_rss_bytes"] = distribution(
            [r["peak_process_rss_bytes"] for r in group])
        if "phases" in runs[0]:
            row["phases"] = {
                k: None if runs[0]["phases"][k] is None else
                distribution([r["phases"][k] for r in runs])
                for k in runs[0]["phases"]
            }
            row["setup_shares_percent"] = {
                k: None if runs[0]["phases"][k] is None else
                distribution([100 * r["phases"][k] / r["setup_ns"] for r in runs])
                for k in SETUP_PHASES
            }
        rows.append(row)
    pairs = []
    if stage != "baseline":
        for engine in ENGINES:
            deltas = []
            for trial in range(6):
                group = [r for r in records if r["engine"] == engine and r["trial"] == trial]
                baseline = next(r for r in group if
                                (r["timing"] == "whole" if stage == "calibration"
                                 else r["surface"] == "facade"))
                treatment = next(r for r in group if r is not baseline)
                deltas.append(100 * (treatment["run"]["setup_ns"] /
                                    baseline["run"]["setup_ns"] - 1))
            pairs.append(dict(engine=engine, changes_percent=deltas,
                              median_percent=statistics.median(deltas),
                              bootstrap_95_percent=paired_interval(deltas)))
    max_residual = max((100 * r["run"]["phases"]["setup_other_ns"] /
                        r["run"]["setup_ns"] for r in records if "phases" in r["run"]),
                       default=0)
    result = dict(stage=stage, rows=rows, pairs=pairs,
                  max_setup_residual_percent=max_residual)
    if stage == "calibration":
        result["calibration_pass"] = max_residual < 1 and all(
            abs(p["median_percent"]) <= 5
            and p["bootstrap_95_percent"][0] >= -10
            and p["bootstrap_95_percent"][1] <= 10 for p in pairs)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--stage", choices=["calibration", "baseline", "limits"], required=True)
    parser.add_argument("--calibration", type=Path,
                        help="Successful calibration directory, required after calibration stage")
    args = parser.parse_args()
    if sys.platform not in ["darwin", "linux"]:
        parser.error("RSS collection requires macOS or Linux")
    if args.stage != "calibration":
        if args.calibration is None:
            parser.error("--calibration is required")
        calibration = json.loads((args.calibration / "analysis.json").read_text())
        if not calibration.get("calibration_pass"):
            parser.error("instrumentation calibration did not pass; stop")
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    before = hashes()
    build_args = ["cargo", "build", "--release", "--locked", "--bin",
                  "initialization-profile", "--message-format=json-render-diagnostics"]
    build = subprocess.run(build_args, cwd=ROOT, text=True, capture_output=True)
    (destination / "build.stdout.jsonl").write_text(build.stdout)
    (destination / "build.stderr.txt").write_text(build.stderr)
    build.check_returncode()
    artifacts = [json.loads(line) for line in build.stdout.splitlines()]
    binaries = [a["executable"] for a in artifacts if a.get("reason") == "compiler-artifact"
                and a.get("target", {}).get("name") == "initialization-profile"
                and a.get("executable")]
    if len(binaries) != 1:
        raise RuntimeError("Cargo did not report exactly one executable")
    binary = Path(binaries[0])
    binary_hash = hashlib.sha256(binary.read_bytes()).hexdigest()
    if args.stage != "calibration":
        previous = json.loads((args.calibration / "manifest.json").read_text())
        if previous["binary_sha256"] != binary_hash or previous["source_sha256"] != before:
            raise RuntimeError("sources/binary differ from calibration; stop")
    meta = dict(stage=args.stage, platform=platform.platform(),
                compiler=command(["rustc", "-vV"]), source_sha256=before,
                binary_sha256=binary_hash, build_command=build_args,
                memory_scope="Fresh build-only whole process, including input/JSON and reporting; not engine heap.",
                warmup=0, repetitions=1, trials=6, order_seed=42,
                planned_cases=cases(args.stage), cases=[],
                environment={k: os.environ.get(k) for k in [
                    "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_TARGET",
                    "CARGO_TARGET_DIR", "CARGO_PROFILE_RELEASE_OPT_LEVEL",
                    "CARGO_PROFILE_RELEASE_LTO", "CARGO_PROFILE_RELEASE_CODEGEN_UNITS"]})
    if sys.platform == "darwin":
        meta["hardware"] = {k: optional_command(["sysctl", "-n", k])
                            for k in ["machdep.cpu.brand_string", "hw.ncpu", "hw.memsize"]}
    for name, root in [("benchmarks", ROOT), ("core", CORE)]:
        meta[name] = dict(revision=command(["git", "rev-parse", "HEAD"], root),
                          status=command(["git", "status", "--porcelain"], root))
        (destination / f"{name}.patch").write_text(source_patch(root) + "\n")
        for relative in command(["git", "ls-files", "--others", "--exclude-standard"], root).splitlines():
            path = root / relative
            if relative.startswith("crates/") and path.suffix == ".rs":
                saved = destination / "untracked" / name / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                saved.write_bytes(path.read_bytes())
    scripts = ["run_initialization.py", "run_baseline.py", "run_scale.py"]
    for script in scripts:
        (destination / script).write_bytes((ROOT / "scripts" / script).read_bytes())
    meta["load_average_before"] = os.getloadavg()
    # No compilation, oracle replay or source inspection overlaps collection.
    time.sleep(3)
    fingerprints = {}
    for i, case in enumerate(meta["planned_cases"]):
        name = f'{i:03}-{case["engine"]}-{case["trial"]}-{case["surface"]}-{case["timing"]}'
        invocation = ["/usr/bin/time", "-l" if sys.platform == "darwin" else "-v",
                      str(binary), "--engine", case["engine"], "--workload", case["workload"],
                      "--nodes", str(case["nodes"]), "--rounds", "1", "--seed", "42",
                      "--surface", case["surface"], "--timing", case["timing"],
                      "--warmup", "0", "--repetitions", "1"]
        result, timed_out = run_measurement(invocation, 30)
        (destination / f"{name}.json").write_text(result.stdout)
        (destination / f"{name}.stderr.txt").write_text(result.stderr)
        record = case | dict(name=name, command=invocation, exit_code=result.returncode,
                             timed_out=timed_out, peak_process_rss_bytes=peak_rss(result.stderr, sys.platform))
        meta["cases"].append(record)
        (destination / "manifest.partial.json").write_text(json.dumps(meta, indent=2) + "\n")
        result.check_returncode()
        if record["peak_process_rss_bytes"] is None:
            raise RuntimeError("platform time tool did not report peak RSS")
        run = validate_report(json.loads(result.stdout), case)
        identity = run["trace_fingerprint_fnv1a64"], run["initial_edges"]
        topology = case["workload"], case["nodes"]
        if topology in fingerprints and fingerprints[topology] != identity:
            raise RuntimeError("initial graph/trace identity changed between arms")
        fingerprints[topology] = identity
        record["run"] = run
    meta["load_average_after"] = os.getloadavg()
    if hashes() != before or hashlib.sha256(binary.read_bytes()).hexdigest() != binary_hash:
        raise RuntimeError("sources/binary changed during collection")
    for script in scripts:
        if (destination / script).read_bytes() != (ROOT / "scripts" / script).read_bytes():
            raise RuntimeError("collector changed during collection")
    analysis = analyze(meta["cases"], args.stage)
    (destination / "analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    (destination / "manifest.partial.json").unlink()
    meta["artifact_sha256"] = {
        str(p.relative_to(destination)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(destination.rglob("*")) if p.is_file()
    }
    (destination / "manifest.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(dict(stage=args.stage, processes=len(meta["cases"]),
                          max_setup_residual_percent=analysis["max_setup_residual_percent"],
                          pairs=analysis["pairs"],
                          calibration_pass=analysis.get("calibration_pass")), indent=2))
    if args.stage == "calibration" and not analysis["calibration_pass"]:
        raise SystemExit("Calibration inconclusive or excessive perturbation; stop before baseline.")


if __name__ == "__main__":
    main()
