#!/usr/bin/env python3
"""Run only the approved fixed Stage-A identical-path initialization validation.

No builds, warmups, retries, adjustable sample counts, or Stage-B implementation.
Both sides have byte-identical argv and environment; labels stay in the parent.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import signal
import statistics
import subprocess
import sys
import time

from run_baseline import ROOT, CORE, command, hashes, source_patch
from run_initialization import ENGINES, distribution, validate_report
from run_scale import peak_rss

METHOD = ROOT / "docs/experiments/2026-10-12-initialization-methodology-review.md"
APPROVED_METHOD_SHA256 = "446490ed560dbfa04e8c92920734ec70572fddde0b1aea5521d5849f9220dff6"
REFERENCE = ROOT / "results/2026-10-12-initialization-phase0/calibration"
REPLICATION = ROOT / "results/2026-10-12-initialization-phase0-replication/calibration"
SEEDS = (120047, 120048, 120049)
QUIET_SECONDS = 60
SESSION_GAP_SECONDS = 300
TIMEOUT_SECONDS = 30
METRICS = ("setup_ns", "total_initialization_ns")
PRECISION = math.log(1.02)
VARIABILITY = math.log(1.03)
TAIL = math.log(1.10)
SCRIPTS = ("run_initialization_aa.py", "run_initialization.py",
           "run_baseline.py", "run_scale.py", "tests/test_initialization_aa.py")
BUILD_PROCESSES = {"cargo", "rustc", "clang", "clang++", "cc1", "make",
                   "ninja", "xcodebuild", "swiftc", "pytest"}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def save_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def child_arguments(binary, engine):
    """Labels and session/trial identifiers must never enter child argv."""
    return ["/usr/bin/time", "-l", str(binary), "--engine", engine,
            "--workload", "dense-bridge-churn-v1", "--nodes", "512",
            "--rounds", "1", "--seed", "42", "--surface", "adapter",
            "--timing", "whole", "--warmup", "0", "--repetitions", "1"]


def schedule(binary):
    """24 pairs/backend; 3 sessions; cyclic engine order and seeded 4/4 labels."""
    plan = []
    for session, seed in enumerate(SEEDS):
        rng = random.Random(seed)
        labels = {}
        for engine in ENGINES:
            labels[engine] = [("A", "Aprime")] * 4 + [("Aprime", "A")] * 4
            rng.shuffle(labels[engine])
        for round_number in range(8):
            offset = (session + round_number) % 3
            for engine in ENGINES[offset:] + ENGINES[:offset]:
                pair = len(plan)
                plan.append(dict(session=session, round=round_number, engine=engine,
                                 pair=pair, labels=list(labels[engine][round_number]),
                                 children=[child_arguments(binary, engine),
                                           child_arguments(binary, engine)]))
    validate_schedule(plan, binary)
    return plan


def validate_schedule(plan, binary):
    """Reject ordering or identity drift before any child is launched."""
    if len(plan) != 72:
        raise ValueError("Stage A requires 72 pairs")
    for session in range(3):
        group = [p for p in plan if p["session"] == session]
        if len(group) != 24 or group[0]["engine"] != ENGINES[session]:
            raise ValueError("wrong session size/start rotation")
        for engine in ENGINES:
            subset = [p for p in group if p["engine"] == engine]
            if len(subset) != 8 or sum(p["labels"] == ["A", "Aprime"] for p in subset) != 4:
                raise ValueError("labels must balance four/four per backend/session")
        for r in range(8):
            offset = (session + r) % 3
            expected = ENGINES[offset:] + ENGINES[:offset]
            round_pairs = group[r * 3:r * 3 + 3]
            if ([p["engine"] for p in round_pairs] != expected
                    or any(p["round"] != r for p in round_pairs)):
                raise ValueError("engine order does not match approved rotation")
    for i, pair in enumerate(plan):
        if pair["pair"] != i or sorted(pair["labels"]) != ["A", "Aprime"]:
            raise ValueError("invalid pair identity")
        expected = child_arguments(binary, pair["engine"])
        if pair["children"] != [expected, expected]:
            raise ValueError("child arguments differ or select a different code path")


def host_state():
    """Read host indicators without changing power policy, QoS, or services."""
    processes = []
    for line in command(["ps", "-Ao", "pid=,pcpu=,comm="]).splitlines():
        pid, cpu, executable = line.strip().split(None, 2)
        processes.append(dict(pid=int(pid), cpu_percent=float(cpu),
                              name=Path(executable).name))
    thermal = subprocess.run(["pmset", "-g", "therm"], text=True, capture_output=True)
    return dict(
        monotonic_ns=time.monotonic_ns(), unix_ns=time.time_ns(),
        power=command(["pmset", "-g", "batt"]),
        power_configuration=command(["pmset", "-g", "custom"]),
        sleep_wake=command(["sysctl", "kern.sleeptime", "kern.waketime"]),
        collector_nice=os.getpriority(os.PRIO_PROCESS, 0),
        load_average=os.getloadavg(),
        top_processes=sorted(processes, key=lambda p: p["cpu_percent"], reverse=True)[:10],
        known_workloads=[p for p in processes if p["name"] in BUILD_PROCESSES
                         or p["name"] == "initialization-profile"],
        thermal=dict(exit_code=thermal.returncode, stdout=thermal.stdout,
                     stderr=thermal.stderr),
    )


def validate_host(current, baseline=None):
    if "Now drawing from 'AC Power'" not in current["power"]:
        raise ValueError("preflight/host failure: AC power is required")
    if current["known_workloads"]:
        raise ValueError(f"known concurrent build/test/workload: {current['known_workloads']}")
    if baseline is not None:
        for key in ("power_configuration", "sleep_wake", "collector_nice"):
            if current[key] != baseline[key]:
                raise ValueError(f"host condition changed: {key}")


def binary_stat(binary):
    s = binary.stat()
    return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]


def preflight(binary):
    """No executable is run: validate provenance against both archived attempts."""
    if digest(METHOD) != APPROVED_METHOD_SHA256:
        raise ValueError("approved methodology identity changed; stop")
    reference = json.loads((REFERENCE / "manifest.json").read_text())
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise ValueError("recorded executable is missing or not executable")
    for folder in (REFERENCE, REPLICATION):
        manifest = json.loads((folder / "manifest.json").read_text())
        if digest(binary) != manifest["binary_sha256"]:
            raise ValueError("binary identity differs from the reviewed executable")
        if hashes() != manifest["source_sha256"]:
            raise ValueError("Rust source/build provenance differs from reviewed executable")
        for relative, expected in manifest["artifact_sha256"].items():
            if digest(folder / relative) != expected:
                raise ValueError(f"previous evidence changed: {folder / relative}")
    for script in ("run_initialization.py", "run_baseline.py", "run_scale.py"):
        if (ROOT / "scripts" / script).read_bytes() != (REFERENCE / script).read_bytes():
            raise ValueError(f"reviewed helper changed: {script}")
    state = host_state()
    validate_host(state)
    return dict(binary_sha256=digest(binary), binary_stat=binary_stat(binary),
                source_sha256=reference["source_sha256"], host=state,
                methodology_sha256=digest(METHOD),
                script_sha256={s: digest(ROOT / "scripts" / s) for s in SCRIPTS},
                expected_trace=reference["cases"][0]["run"]["trace_fingerprint_fnv1a64"])


def validate_provenance(binary, baseline):
    if binary_stat(binary) != baseline["binary_stat"] or digest(binary) != baseline["binary_sha256"]:
        raise ValueError("binary changed during Stage A")
    if hashes() != baseline["source_sha256"] or digest(METHOD) != baseline["methodology_sha256"]:
        raise ValueError("source or approved methodology changed during Stage A")
    if any(digest(ROOT / "scripts" / s) != sha for s, sha in baseline["script_sha256"].items()):
        raise ValueError("collector/helper changed during Stage A")


def wait_quiet(seconds, baseline, destination, name):
    """Fixed elapsed wait; host-event detection never resets or extends its target."""
    start = time.monotonic_ns()
    deadline = time.monotonic() + seconds
    checks = []
    try:
        while True:
            state = host_state()
            checks.append(state)
            validate_host(state, baseline)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            time.sleep(min(10, remaining))
    finally:
        save_json(destination / f"{name}.json",
                  dict(required_seconds=seconds, start_monotonic_ns=start,
                       end_monotonic_ns=time.monotonic_ns(), checks=checks))


def observe(arguments, environment):
    """Capture one whole child process; retain PID and raw wrapper diagnostics."""
    launch = time.monotonic_ns()
    with subprocess.Popen(arguments, cwd=ROOT, env=environment, stdin=subprocess.DEVNULL,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                          start_new_session=True) as process:
        timed_out = False
        try:
            stdout, stderr = process.communicate(timeout=TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            stdout, stderr = process.communicate()
        completed = time.monotonic_ns()
        return dict(wrapper_pid=process.pid, launch_monotonic_ns=launch,
                    completion_monotonic_ns=completed, exit_code=process.returncode,
                    timed_out=timed_out, stdout=stdout, stderr=stderr)


def process_metadata(stderr):
    """Keep raw stderr authoritative; unavailable fields stay explicitly null."""
    fields = {}
    for label in ("page reclaims", "page faults", "swaps",
                  "voluntary context switches", "involuntary context switches",
                  "instructions retired", "cycles elapsed", "peak memory footprint"):
        match = re.search(r"^\s*(\d+)\s+" + re.escape(label) + r"\s*$", stderr, re.M)
        fields[label.replace(" ", "_")] = int(match[1]) if match else None
    match = re.search(r"([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys", stderr)
    fields["printed_process_seconds"] = (
        dict(zip(("real", "user", "sys"), map(float, match.groups()))) if match else None)
    return fields


def collect_pair(pair, binary, baseline, environment, destination):
    """No disk writes, host probes or statistical analysis between successful children."""
    validate_provenance(binary, baseline)
    before = host_state()
    validate_host(before, baseline["host"])
    observations = []
    try:
        for position, (label, arguments) in enumerate(zip(pair["labels"], pair["children"])):
            if binary_stat(binary) != baseline["binary_stat"]:
                raise ValueError("binary identity changed before child launch")
            result = observe(arguments, environment)
            result.update(session=pair["session"], round=pair["round"], pair=pair["pair"],
                          engine=pair["engine"], label=label, pair_position=position,
                          observation=2 * pair["pair"] + position, arguments=arguments,
                          arguments_sha256=json_digest(arguments),
                          environment_sha256=json_digest(environment), cwd=str(ROOT))
            observations.append(result)
            if result["timed_out"] or result["exit_code"] != 0:
                raise RuntimeError(f"child failed: pair {pair['pair']}, position {position}")
        for result in observations:
            case = dict(surface="adapter", timing="whole", workload="dense-bridge-churn-v1",
                        nodes=512, engine=pair["engine"])
            run = validate_report(json.loads(result["stdout"]), case)
            if (run["initial_edges"] != 65281
                    or run["trace_fingerprint_fnv1a64"] != baseline["expected_trace"]):
                raise ValueError("initial graph/trace identity differs from reviewed input")
            result["run"] = run
            result["peak_process_rss_bytes"] = peak_rss(result["stderr"], "darwin")
            if result["peak_process_rss_bytes"] is None:
                raise ValueError("missing whole-process peak RSS")
            result["process_metadata"] = process_metadata(result["stderr"])
        validate_provenance(binary, baseline)
        after = host_state()
        validate_host(after, baseline["host"])
        return observations
    finally:
        for result in observations:
            stem = f'{result["observation"]:03}-{result["engine"]}-{result["label"]}'
            (destination / f"{stem}.json").write_text(result["stdout"])
            (destination / f"{stem}.stderr.txt").write_text(result["stderr"])
        save_json(destination / f'pair-{pair["pair"]:02}.json',
                  dict(plan=pair, host_before=before,
                       host_after=locals().get("after"),
                       observations=[{k: v for k, v in r.items() if k not in ("stdout", "stderr")}
                                     for r in observations]))


def percent(value):
    return 100 * math.expm1(value)


def gate_metric(rows, metric):
    """Apply every approved criterion once, without omitting any observation."""
    if len(rows) != 48:
        raise ValueError("24 complete pairs per backend are required for inference")
    pairs = []
    for pair_id in sorted({r["pair"] for r in rows}):
        group = sorted((r for r in rows if r["pair"] == pair_id),
                       key=lambda r: r["pair_position"])
        if len(group) != 2 or {r["label"] for r in group} != {"A", "Aprime"}:
            raise ValueError("incomplete or malformed A/A pair")
        values = {r["label"]: r["run"][metric] for r in group}
        if any(v <= 0 for v in values.values()):
            raise ValueError("invalid timing value")
        pairs.append(dict(pair=pair_id, session=group[0]["session"],
                          labeled_log_ratio=math.log(values["Aprime"] / values["A"]),
                          chronological_log_ratio=math.log(
                              group[1]["run"][metric] / group[0]["run"][metric])))
    differences = [p["labeled_log_ratio"] for p in pairs]
    ordered = sorted(differences)
    interval = [ordered[6], ordered[17]]
    median_abs = statistics.median(abs(d) for d in differences)
    tail_count = sum(abs(d) > TAIL for d in differences)
    checks = dict(precision=interval[0] >= -PRECISION and interval[1] <= PRECISION,
                  variability=median_abs <= VARIABILITY, tails=tail_count <= 2)
    sessions = []
    for session in range(3):
        subset = [p for p in pairs if p["session"] == session]
        observations = sorted((r for r in rows if r["session"] == session),
                              key=lambda r: r["observation"])
        if len(subset) != 8 or len(observations) != 16:
            raise ValueError("session is not eight complete pairs")
        labeled = statistics.median(p["labeled_log_ratio"] for p in subset)
        chronological = statistics.median(p["chronological_log_ratio"] for p in subset)
        startup = observations[0]["run"][metric] / statistics.median(
            r["run"][metric] for r in observations[1:])
        session_checks = dict(labeled_median=abs(labeled) <= VARIABILITY,
                              chronological_median=abs(chronological) <= VARIABILITY,
                              startup=1 / 1.10 <= startup <= 1.10)
        sessions.append(dict(session=session, labeled_median_log=labeled,
                             chronological_median_log=chronological,
                             first_observation=observations[0]["observation"],
                             startup_ratio=startup, checks=session_checks,
                             passed=all(session_checks.values())))
    return dict(metric=metric, pairs=pairs, observation_distribution=distribution(
                    [r["run"][metric] for r in rows]),
                log_ratio_distribution=distribution(differences),
                chronological_log_ratio_distribution=distribution(
                    [p["chronological_log_ratio"] for p in pairs]),
                median_change_percent=percent(statistics.median(differences)),
                median_interval_ranks_7_18_log=interval,
                median_interval_percent=[percent(v) for v in interval],
                median_absolute_log_ratio=median_abs, tail_count=tail_count,
                checks=checks, sessions=sessions,
                passed=all(checks.values()) and all(s["passed"] for s in sessions))


def analyze(observations):
    if len(observations) != 144 or sorted(r["observation"] for r in observations) != list(range(144)):
        raise ValueError("only a complete 144-observation stage can be analyzed")
    rows = []
    for engine in ENGINES:
        selected = [r for r in observations if r["engine"] == engine]
        metrics = {metric: gate_metric(selected, metric) for metric in METRICS}
        rows.append(dict(engine=engine, metrics=metrics,
                         peak_process_rss_bytes=distribution(
                             [r["peak_process_rss_bytes"] for r in selected]),
                         passed=all(m["passed"] for m in metrics.values())))
    return dict(stage="A-only", pairs_per_backend=24, observations=144,
                median_interval_coverage=1 - 2 * sum(math.comb(24, j) for j in range(7)) / 2**24,
                rows=rows, passed=all(r["passed"] for r in rows),
                stage_b_authorized=False)


def order_plot(observations):
    """Dependency-free SVG retaining every observation and each session boundary."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1260">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="sans-serif" font-size="12" fill="black">',
             '<text x="40" y="22">Identical whole path: A blue, A-prime orange; global observation order</text>']
    for panel, (engine, metric) in enumerate((e, m) for e in ENGINES for m in METRICS):
        subset = sorted((r for r in observations if r["engine"] == engine),
                        key=lambda r: r["observation"])
        top = 55 + panel * 195
        maximum = max(r["run"][metric] for r in subset) * 1.05
        points = [(65 + r["observation"] * 6, top + 140 * (1 - r["run"][metric] / maximum), r)
                  for r in subset]
        parts.append(f'<text x="40" y="{top-8}">{engine}: {metric}; top={maximum/1e6:.3f} ms, bottom=0</text>')
        for boundary in (0, 48, 96, 144):
            x = 65 + boundary * 6
            parts.append(f'<path d="M{x},{top} v140" stroke="#cccccc"/>')
            parts.append(f'<text x="{x}" y="{top+155}">{boundary}</text>')
        coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y, _ in points)
        parts.append(f'<polyline points="{coordinates}" fill="none" stroke="#aaaaaa"/>')
        for x, y, row in points:
            color = "#2670c0" if row["label"] == "A" else "#df7700"
            parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="{color}"/>')
    return "\n".join(parts + ["</g></svg>\n"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--prevent-idle-sleep", action="store_true",
                        help="User-approved temporary caffeinate -i assertion; no power/QoS changes")
    args = parser.parse_args()
    if sys.platform != "darwin":
        parser.error("this approved host protocol requires macOS")
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    manifest = dict(stage="A-only", stage_b_authorized=False, status="preflight",
                    started_unix_ns=time.time_ns(), observations=[],
                    python=sys.version, platform=platform.platform(),
                    exclusive_host=False, prevention_authorized=args.prevent_idle_sleep)
    assertion = None
    try:
        if args.prevent_idle_sleep:
            assertion = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                                         stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            time.sleep(0.1)
            if assertion.poll() is not None:
                raise RuntimeError(f"idle-sleep assertion failed: {assertion.stderr.read()}")
            manifest["idle_sleep_assertion_pid"] = assertion.pid
        binary = Path(json.loads((REFERENCE / "manifest.json").read_text())["cases"][0]["command"][2])
        manifest["binary"] = str(binary)
        manifest["host_preflight"] = host_state()
        validate_host(manifest["host_preflight"])
        baseline = preflight(binary)
        validate_host(baseline["host"], manifest["host_preflight"])
        manifest["preflight"] = baseline
        plan = schedule(binary)
        environment = dict(os.environ)
        manifest["environment_sha256"] = json_digest(environment)
        manifest["recorded_environment"] = {k: environment.get(k) for k in (
            "RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_TARGET", "CARGO_TARGET_DIR",
            "DYLD_INSERT_LIBRARIES", "MallocNanoZone", "MallocStackLogging", "LC_ALL", "LANG",
            "PYTHONDONTWRITEBYTECODE")}
        manifest["quiet_seconds"] = QUIET_SECONDS
        manifest["session_gap_seconds"] = SESSION_GAP_SECONDS
        manifest["quiet_interpretation"] = (
            "60 seconds before session 0; each subsequent fixed 300-second quiet gap "
            "also includes the required final 60 quiet seconds before its session.")
        manifest["qos_policy"] = (
            "Unchanged inherited priority/QoS; no affinity, P/E-core residency or actual QoS-class telemetry.")
        manifest["hardware"] = command(["sysctl", "machdep.cpu.brand_string", "hw.ncpu",
                                        "hw.memsize", "hw.perflevel0.name",
                                        "hw.perflevel0.physicalcpu", "hw.perflevel1.name",
                                        "hw.perflevel1.physicalcpu"])
        for name, root in (("benchmarks", ROOT), ("core", CORE)):
            manifest[name] = dict(revision=command(["git", "rev-parse", "HEAD"], root),
                                  status=command(["git", "status", "--porcelain"], root))
            (destination / f"{name}.patch").write_text(source_patch(root) + "\n")
        for script in SCRIPTS:
            saved = destination / "collector" / script
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes((ROOT / "scripts" / script).read_bytes())
        (destination / "approved-methodology.md").write_bytes(METHOD.read_bytes())
        save_json(destination / "preflight.json", baseline)
        save_json(destination / "schedule.json", plan)
        manifest["schedule_sha256"] = digest(destination / "schedule.json")
        save_json(destination / "manifest.partial.json", manifest)
        for session in range(3):
            if session:
                wait_quiet(SESSION_GAP_SECONDS, baseline["host"], destination,
                           f"session-{session}-gap")
            else:
                wait_quiet(QUIET_SECONDS, baseline["host"], destination,
                           f"session-{session}-quiet")
            validate_provenance(binary, baseline)
            if digest(destination / "schedule.json") != manifest["schedule_sha256"]:
                raise ValueError("archived schedule changed")
            if assertion is not None and assertion.poll() is not None:
                raise RuntimeError("idle-sleep assertion unexpectedly ended")
            for pair in (p for p in plan if p["session"] == session):
                if assertion is not None and assertion.poll() is not None:
                    raise RuntimeError("idle-sleep assertion unexpectedly ended")
                records = collect_pair(pair, binary, baseline, environment, destination)
                manifest["observations"].extend(
                    {k: v for k, v in r.items() if k not in ("stdout", "stderr")} for r in records)
                manifest["status"] = "collecting"
                save_json(destination / "manifest.partial.json", manifest)
        analysis = analyze(manifest["observations"])
        save_json(destination / "analysis.json", analysis)
        (destination / "order.svg").write_text(order_plot(manifest["observations"]))
        manifest["status"] = "passed" if analysis["passed"] else "failed-statistical-gates"
        print(json.dumps(dict(status=manifest["status"], observations=144,
                              rows=[dict(engine=r["engine"], passed=r["passed"],
                                         metrics={k: dict(passed=v["passed"], checks=v["checks"],
                                                          median_change_percent=v["median_change_percent"],
                                                          median_interval_percent=v["median_interval_percent"])
                                                  for k, v in r["metrics"].items()})
                                    for r in analysis["rows"]]), indent=2), flush=True)
    except BaseException as error:
        manifest["status"] = "stopped"
        manifest["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        if assertion is not None:
            if assertion.poll() is None:
                assertion.terminate()
            assertion.communicate()
        manifest["finished_unix_ns"] = time.time_ns()
        manifest["artifact_sha256"] = {
            str(p.relative_to(destination)): digest(p) for p in sorted(destination.rglob("*"))
            if p.is_file() and p.name not in ("manifest.json", "manifest.partial.json")}
        save_json(destination / "manifest.json", manifest)
        partial = destination / "manifest.partial.json"
        if partial.exists():
            partial.unlink()
    if manifest["status"] != "passed":
        raise SystemExit("Stage A failed its fixed gates. Stop; Stage B is not authorized.")


if __name__ == "__main__":
    main()
