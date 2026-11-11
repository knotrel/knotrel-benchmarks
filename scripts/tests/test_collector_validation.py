"""Synthetic qualification regressions; no external evidence or real benchmarks."""

import copy
import json
from pathlib import Path
import sys
import os
import time
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_p0_aa as p0
from test_p0_aa import _make_valid_batch_report, _make_valid_lifecycle_report


def core_report():
    cell = dict(engine="compact-bfs", workload="chain-split-rejoin-v1", nodes=16,
                rounds=2, seed=42, warmup=1, repetitions=3)
    def latency(count):
        return dict(count=count, total_ns=count, min_ns=0, p50_ns=1,
                    p95_ns=1, p99_ns=1, max_ns=2)
    repetition = dict(setup_ns=0, workload_wall_ns=10,
                      measurements={key: latency(count) for key, count in
                                    p0.expected_operation_counts(cell).items()},
                      query_true=latency(2), query_false=latency(2), repeated_queries=None)
    report = dict(schema_version=2, engine=p0.CORE_ENGINE_NAME_MAP[cell["engine"]],
                  workload=cell["workload"], config={key: cell[key] for key in ("nodes", "rounds", "seed")},
                  warmup=1, query_repeats=0, trace_fingerprint_fnv1a64="0123456789abcdef",
                  repetitions=[copy.deepcopy(repetition) for _ in range(3)])
    return cell, report


def http_report(kind):
    cell = dict(engine="compact-bfs", batch_size=64, nodes=1000, seed=42, runs=3)
    factory = _make_valid_batch_report if kind == "batch" else _make_valid_lifecycle_report
    report = factory(cell)
    report["runs"] = [copy.deepcopy(report["runs"][0]) for _ in range(3)]
    for index, run in enumerate(report["runs"]):
        run["run_index"] = index + 1
    parser = p0.parse_http_batch_json if kind == "batch" else p0.parse_http_lifecycle_json
    return cell, report, parser


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("field,value", [
    (("workload_wall_ns",), -1), (("setup_ns",), "invalid"),
    (("measurements", "cut", "count"), -1),
    (("measurements", "link", "count"), True),
    (("measurements", "connected", "p99_ns"), float("inf")),
    (("query_true", "count"), 999),
])
def test_core_rejects_corruption_in_every_entry(index, field, value):
    cell, report = core_report()
    target = report["repetitions"][index]
    for name in field[:-1]:
        target = target[name]
    target[field[-1]] = value
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("field", ["setup_ns", "measurements", "query_true", "repeated_queries"])
def test_core_requires_fields_in_every_entry(index, field):
    cell, report = core_report()
    del report["repetitions"][index][field]
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


@pytest.mark.parametrize("kind", ["lifecycle", "batch"])
@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("mutation", ["negative", "missing", "verification", "seed", "invalid"])
def test_http_rejects_corruption_in_every_entry(kind, index, mutation):
    cell, report, parser = http_report(kind)
    run = report["runs"][index]
    if mutation == "negative":
        run["setup" if kind == "batch" else "snapshot_import"]["duration_ns"] = -1
    elif mutation == "missing":
        del run["memory"]
    elif mutation == "verification":
        if kind == "batch":
            run["verification"]["all_items_matched"] = False
        else:
            run["query"]["verified_queries"] = 0
    elif mutation == "seed":
        run["seed"] = 99
    else:
        run["setup" if kind == "batch" else "snapshot_import"]["duration_ms"] = "invalid"
    with pytest.raises(p0.QualificationBlockerError):
        parser(report, cell)


@pytest.mark.parametrize("kind", ["core", "lifecycle", "batch"])
@pytest.mark.parametrize("count", [0, 2, 4])
def test_exact_entry_inventory(kind, count):
    if kind == "core":
        cell, report = core_report()
        report["repetitions"] = [copy.deepcopy(report["repetitions"][0]) for _ in range(count)]
        parser = lambda: p0.parse_core_output(json.dumps(report), "", cell)
    else:
        cell, report, parse = http_report(kind)
        report["runs"] = [copy.deepcopy(report["runs"][0]) for _ in range(count)]
        parser = lambda: parse(report, cell)
    with pytest.raises(p0.QualificationBlockerError):
        parser()


@pytest.mark.parametrize("kind", ["core", "lifecycle", "batch"])
def test_identity_and_configuration_mismatch(kind):
    if kind == "core":
        cell, report = core_report()
        report["config"]["seed"] = 99
        with pytest.raises(p0.QualificationBlockerError):
            p0.parse_core_output(json.dumps(report), "", cell)
    else:
        cell, report, parser = http_report(kind)
        report["configuration"]["effective_engine"] = "other"
        with pytest.raises(p0.QualificationBlockerError):
            parser(report, cell)


@pytest.mark.parametrize("kind", ["core", "lifecycle", "batch"])
def test_zero_latency_samples_and_first_entry_selection(kind):
    if kind == "core":
        cell, report = core_report()
        for repetition in report["repetitions"]:
            for latency in [*repetition["measurements"].values(), repetition["query_true"], repetition["query_false"]]:
                for key in latency:
                    if key != "count":
                        latency[key] = 0
        report["repetitions"][1]["workload_wall_ns"] = 20
        parsed = p0.parse_core_output(json.dumps(report), "", cell)
        assert parsed["workload_wall_ns"] == 10
    else:
        cell, report, parser = http_report(kind)
        for run in report["runs"]:
            latency = run["request_latency" if kind == "batch" else "query"]
            for unit in ("latency_ns", "latency_us"):
                for key in latency[unit]:
                    latency[unit][key] = 0
        key = "measurement_window" if kind == "batch" else "registration_through_barrier"
        report["runs"][1][key]["duration_ms"] = 999
        parsed = parser(report, cell)
        selected = "window_duration_ms" if kind == "batch" else "time_to_ready_ms"
        assert parsed["exported_metrics"][selected] == report["runs"][0][key]["duration_ms"]


@pytest.mark.parametrize("kind", ["core", "lifecycle", "batch"])
def test_duplicate_json_keys_are_rejected(kind, tmp_path):
    if kind == "core":
        cell, report = core_report()
        text = json.dumps(report).replace('"setup_ns": 0', '"setup_ns": 0, "setup_ns": 1', 1)
        parse = lambda: p0.parse_core_output(text, "", cell)
    else:
        cell, report, _ = http_report(kind)
        text = json.dumps(report).replace('"seed": 42', '"seed": 42, "seed": 42', 1)
        filename = tmp_path / "report.json"
        filename.write_text(text)
        parse = lambda: p0.parse_http_json_report(filename, cell)
    with pytest.raises(p0.QualificationBlockerError):
        parse()


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_capture_overflow_is_bounded_and_reaped(stream, tmp_path):
    code = f"import os,sys,time; print('started', flush=True); os.write({1 if stream == 'stdout' else 2}, b'x'*1000000); time.sleep(20)"
    started = time.monotonic()
    observation = p0.observe_child([sys.executable, "-c", code], str(tmp_path),
                                   dict(os.environ), 2, is_core=False, output_limit_bytes=256)
    assert observation["output_limit_exceeded"] is True
    assert observation["direct_child_reaped"] is True
    assert observation["failure_reason"]
    assert observation["stdout_bytes_captured"] + observation["stderr_bytes_captured"] <= 256
    assert time.monotonic() - started < 4


def test_timeout_preserves_partial_streams_and_reaps(tmp_path):
    code = "import sys,time; print('partial out',flush=True); print('partial err',file=sys.stderr,flush=True); time.sleep(20)"
    observation = p0.observe_child([sys.executable, "-c", code], str(tmp_path),
                                   dict(os.environ), 0.2, is_core=False)
    assert observation["timed_out"]
    assert observation["direct_child_reaped"]
    assert "partial out" in observation["stdout"]
    assert "partial err" in observation["raw_stderr"]


def test_launch_failure_does_not_fabricate_streams(tmp_path):
    observation = p0.observe_child([str(tmp_path / "missing")], str(tmp_path), {}, 1, is_core=False)
    assert observation["status"] == "launch_failed"
    assert observation["failure_reason"]
    assert observation["stdout"] is None and observation["raw_stderr"] is None
    assert observation["wrapper_pid"] is None


def candidate_args(tmp_path, fake=False):
    import run_candidate_a_comparison as candidate
    binary = tmp_path / "synthetic-input"
    binary.write_text("not an executable")
    args = ["collector", "--destination", str(tmp_path / "out"), "--baseline-bin", str(binary),
            "--candidate-bin", str(binary), "--execute", "--skip-quiet"]
    if fake:
        args.append("--fake-runner")
    digests = ["03dbb4167e6516d0d7e10b691fefe6f5e9d9ed48cf43843307c59d53200d2d27",
               "1c19413d023b3e7278c9cb3b8df7adf4019b50daf9a2b5678fa93791e1b40d4c"]
    return candidate, args, digests


@pytest.mark.parametrize("failure", ["nonzero", "timeout", "malformed", "schema", "overflow", "launch"])
def test_candidate_persists_failed_observation(tmp_path, failure):
    candidate, args, digests = candidate_args(tmp_path)
    observation = dict(exit_code=1 if failure == "nonzero" else 0,
                       timed_out=failure == "timeout", stdout="raw marker", raw_stderr="error marker",
                       peak_rss_bytes=None, output_limit_exceeded=failure == "overflow",
                       failure_reason=failure if failure in ("overflow", "launch") else None)
    if failure == "schema":
        observation["stdout"] = '{"schema_version":999}'
    if failure == "launch":
        observation.update(stdout=None, raw_stderr=None, exit_code=None, status="launch_failed")
    with patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests), \
         patch.object(candidate, "host_state", return_value={}), \
         patch.object(candidate, "validate_host_state", return_value=(True, None)), \
         patch.object(candidate, "observe_child", return_value=observation) as child:
        with pytest.raises((ValueError, RuntimeError)):
            candidate.main()
        assert child.call_count == 1
    records = list((tmp_path / "out").glob("observation_*.json"))
    assert len(records) == 1
    record = json.loads(records[0].read_text())
    assert record["obs"]["stdout"] == observation["stdout"]
    assert record["obs"]["raw_stderr"] == observation["raw_stderr"]
    assert record["status"] != "parsed_valid" and record["failure_reason"]


def test_complete_candidate_fake_mode_is_self_validating(tmp_path):
    candidate, args, digests = candidate_args(tmp_path, fake=True)
    with patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests), \
         patch.object(candidate, "observe_child") as child:
        candidate.main()
        child.assert_not_called()
    destination = tmp_path / "out"
    assert len(list(destination.glob("report_pair_*.json"))) == 72
    assert len(list(destination.glob("pair_*.json"))) == 36
    assert len(list(destination.glob("observation_*.json"))) == 72
    for filename in destination.glob("observation_*.json"):
        record = json.loads(filename.read_text())
        cell = next(cell for cell in candidate.CELL_DEFINITIONS if cell["cell_id"] == record["cell_id"])
        candidate.parse_core_report(record["obs"]["stdout"], cell)
    assert json.loads((destination / "run_metadata.json").read_text())["status"] == "completed"


def test_campaign_budget_stops_before_child_and_retains_failure(tmp_path):
    candidate, args, digests = candidate_args(tmp_path)
    with patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests), \
         patch.object(candidate, "host_state", return_value={}), \
         patch.object(candidate, "validate_host_state", return_value=(True, None)), \
         patch.object(candidate, "DISK_CEILING_BYTES", 16384), \
         patch.object(candidate, "observe_child") as child:
        with pytest.raises(RuntimeError, match="budget|ceiling"):
            candidate.main()
        child.assert_not_called()
    metadata = json.loads((tmp_path / "out/run_metadata.json").read_text())
    assert metadata["status"] == "failed" and metadata["failure_error"]


def test_test_inputs_and_execution_defaults_are_portable():
    import run_batch_warmup_investigation as batch
    import test_p0_aa as tests
    assert "/Users/" not in str(p0.DEFAULT_MANIFEST_PATH)
    assert batch.WORKSPACE_DIR == Path(batch.__file__).resolve().parents[2]
    assert "/Users/" not in Path(tests.__file__).read_text()
    assert "evidence" not in tests.EVIDENCE_ROOT.parts
    fixture = Path(__file__).parent / "fixtures/standalone_batch_smoke_b1.json"
    assert "/Users/" not in fixture.read_text()


@pytest.mark.parametrize("kind", ["lifecycle", "batch"])
@pytest.mark.parametrize("index", [0, 1, 2])
@pytest.mark.parametrize("field", ["run_index", "seed", "timing", "container"])
def test_http_requires_identity_and_well_formed_run(kind, index, field):
    cell, report, parser = http_report(kind)
    run = report["runs"][index]
    if field in ("run_index", "seed"):
        del run[field]
    elif field == "timing":
        if kind == "lifecycle":
            del run["barrier"]
        else:
            del run["setup"]["duration_ns"]
    else:
        run["request_latency" if kind == "batch" else "query"] = []
    with pytest.raises(p0.QualificationBlockerError):
        parser(report, cell)


def test_capture_preserves_invalid_utf8_bytes(tmp_path):
    observation = p0.observe_child([sys.executable, "-c", "import os;os.write(1,b'\\xff')"],
                                   str(tmp_path), dict(os.environ), 1, is_core=False)
    assert observation["stdout_bytes_base64"] == "/w=="


@pytest.mark.parametrize("kind", ["core", "lifecycle", "batch"])
@pytest.mark.parametrize("text", ["{malformed", "[]", "null", "true"])
def test_malformed_json_is_qualification_failure(kind, text, tmp_path):
    if kind == "core":
        cell, _ = core_report()
        parser = lambda: p0.parse_core_output(text, "", cell)
    else:
        cell, _, _ = http_report(kind)
        filename = tmp_path / "malformed.json"
        filename.write_text(text)
        parser = lambda: p0.parse_http_json_report(filename, cell)
    with pytest.raises(p0.QualificationBlockerError):
        parser()


def test_shared_campaign_budget_reserves_failure_space(tmp_path):
    (tmp_path / "existing").write_bytes(b"x" * 1024)
    with pytest.raises(p0.QualificationBlockerError, match="budget"):
        p0.campaign_capture_limit(tmp_path, ceiling=2048, reserve=1024)


def test_overflow_kills_descendant_group(tmp_path):
    import subprocess
    code = ("import os,sys,time\n"
            "if os.fork()==0:\n time.sleep(20);sys.exit(0)\n"
            "os.write(1,b'x'*1000000)\ntime.sleep(20)\n")
    observation = p0.observe_child([sys.executable, "-c", code], str(tmp_path),
                                   dict(os.environ), 2, is_core=False, output_limit_bytes=128)
    assert observation["output_limit_exceeded"] and observation["direct_child_reaped"]
    processes = subprocess.check_output(["ps", "-Ao", "pgid=,stat="], text=True)
    for line in processes.splitlines():
        group, state = line.split()
        if int(group) == observation["wrapper_pid"]:
            assert state.startswith("Z"), "Capture left a running descendant"


def _run_failed_capture(tmp_path, caller, observation):
    import run_batch_warmup_investigation as batch
    candidate, args, digests = candidate_args(tmp_path)
    if caller == "candidate":
        contexts = [patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests),
                    patch.object(candidate, "host_state", return_value={}),
                    patch.object(candidate, "validate_host_state", return_value=(True, None))]
        module = candidate
        invoke = candidate.main
    elif caller == "batch":
        contexts = [patch.object(batch, "host_state", return_value={})]
        module = batch
        invoke = lambda: batch.execute_investigation(tmp_path / "out", cwd=tmp_path,
            enforce_host=False, check_provenance=False, pre_quiet_seconds=0, inter_cooldown_seconds=0)
    else:
        cell, _ = core_report()
        cell.update(cell_id="synthetic", type="core", argv=["synthetic"], cwd=str(tmp_path), env={})
        seeds = list(p0.SESSION_SEEDS)
        manifest = dict(schema="knotrel-p0-pilot-manifest-v1", pilot_design=dict(cells=[cell],
            total_cells=1, total_pairs=6, total_measured_launches=12, sessions_count=3, session_seeds=seeds))
        pairs = [dict(pair_id=index, session=index // 2, cell_id="synthetic", labels=["A", "Aprime"]
            if index % 2 == 0 else ["Aprime", "A"], argv=cell["argv"], cwd=cell["cwd"], env={}) for index in range(6)]
        schedule = dict(schema="knotrel-p0-pilot-schedule-v1", total_cells=1, total_pairs=6,
            total_measured_runs=12, pairs=pairs,
            sessions=[dict(session_id=index, seed=seed, pair_count=2) for index, seed in enumerate(seeds)])
        p0.save_json(tmp_path / "manifest.json", manifest)
        p0.save_json(tmp_path / "schedule.json", schedule)
        contexts = [patch.object(p0, "host_state", return_value={})]
        module = p0
        invoke = lambda: p0.execute_pilot(tmp_path / "manifest.json", tmp_path / "schedule.json",
            tmp_path / "out", enforce_host=False, check_provenance=False,
            session_pre_quiet_seconds=0, inter_session_cooldown_seconds=0)
    from contextlib import ExitStack
    with ExitStack() as stack:
        for context in contexts:
            stack.enter_context(context)
        child = stack.enter_context(patch.object(module, "observe_child", return_value=observation))
        with pytest.raises((RuntimeError, p0.ProcessExecutionError), match="[Cc]apture"):
            invoke()
        assert child.call_count == 1
    destination = tmp_path / "out"
    records = list(destination.glob("observation_*.json")) if caller == "candidate" else list(destination.glob("pair_*.json"))
    assert len(records) == 1
    saved = json.loads(records[0].read_text())
    entry = saved if caller == "candidate" else saved["observations"][0]
    streams = entry["obs"] if caller == "candidate" else entry
    assert streams["stdout"] == observation["stdout"]
    assert streams["raw_stderr"] == observation["raw_stderr"]
    assert entry["status"] != "parsed_valid"
    metadata = json.loads((destination / "run_metadata.json").read_text())
    assert metadata["status"] != "completed"
    assert metadata.get("failure_error") or metadata.get("failure_record") or metadata.get("error")


@pytest.mark.parametrize("caller", ["p0", "batch", "candidate"])
@pytest.mark.parametrize("status,reason", [("failed", None), ("captured", "Capture failure: synthetic read error")])
def test_unsuccessful_capture_never_becomes_valid(tmp_path, caller, status, reason):
    _, report = core_report()
    observation = dict(status=status, failure_reason=reason, exit_code=0, timed_out=False,
        output_limit_exceeded=False, stdout=json.dumps(report), raw_stderr="preserved stderr",
        full_cmd=["synthetic"], wrapper_pid=123, launch_monotonic_ns=1, completion_monotonic_ns=2,
        launch_unix_ns=1, completion_unix_ns=2, wall_duration_ns=1, peak_rss_bytes=None,
        wrapper_diagnostics=None, direct_child_reaped=True)
    _run_failed_capture(tmp_path, caller, observation)


def test_actual_read_failure_after_valid_stdout_stops_campaign(tmp_path):
    _, report = core_report()
    real_popen, real_read = p0.subprocess.Popen, p0.os.read
    state = {}
    def launch(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        state["process"] = process
        return process
    def read(descriptor, count):
        data = real_read(descriptor, count)
        process = state.get("process")
        if process is not None and descriptor == process.stdout.fileno():
            if data:
                state["stdout_seen"] = True
            elif state.get("stdout_seen"):
                process.wait(timeout=1)
                raise OSError("synthetic capture failure after valid JSON")
        return data
    with patch.object(p0.subprocess, "Popen", side_effect=launch), patch.object(p0.os, "read", side_effect=read):
        observation = p0.observe_child([sys.executable, "-c", "print(" + repr(json.dumps(report)) + ")"],
            str(tmp_path), dict(os.environ), 2, is_core=False)
    assert observation["status"] == "failed" and observation["exit_code"] == 0
    assert observation["direct_child_reaped"]
    p0.parse_core_output(observation["stdout"], "", core_report()[0])
    _run_failed_capture(tmp_path, "p0", observation)


@pytest.mark.parametrize("metadata", ["environment", "arguments"])
@pytest.mark.parametrize("text", ["x" * 40000, '"\\\u00e9' * 10000])
def test_candidate_reserves_serialized_metadata_before_launch(tmp_path, metadata, text):
    candidate, args, digests = candidate_args(tmp_path)
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch.object(sys, "argv", args))
        stack.enter_context(patch.object(candidate, "digest_file", side_effect=digests))
        stack.enter_context(patch.object(candidate, "host_state", return_value={}))
        stack.enter_context(patch.object(candidate, "validate_host_state", return_value=(True, None)))
        stack.enter_context(patch.object(candidate, "DISK_CEILING_BYTES", 92763))
        if metadata == "environment":
            stack.enter_context(patch.dict(os.environ, {"PATH": text}))
        else:
            stack.enter_context(patch.object(candidate, "build_command_args", return_value=["synthetic", text]))
        child = stack.enter_context(patch.object(candidate, "observe_child", return_value=dict(
            exit_code=1, timed_out=False, stdout="bounded out", raw_stderr="bounded err", peak_rss_bytes=None)))
        with pytest.raises(RuntimeError, match="budget|ceiling"):
            candidate.main()
        child.assert_not_called()
    record = json.loads((tmp_path / "out/run_metadata.json").read_text())
    assert record["status"] == "failed" and record["failure_error"]
    assert sum(filename.stat().st_size for filename in (tmp_path / "out").iterdir()) <= 92763


@pytest.mark.parametrize("failed", [False, True])
@pytest.mark.parametrize("ceiling", [150000, 250000])
def test_candidate_near_ceiling_preserves_every_admitted_capture(tmp_path, failed, ceiling):
    candidate, args, digests = candidate_args(tmp_path)
    from test_candidate_a_comparison import valid_core_report
    report = valid_core_report()
    binary = Path(args[args.index("--baseline-bin") + 1])
    stderr = 'quoted " and slash \\ and unicode \u00e9\n'
    binary.write_text("#!" + sys.executable + "\nimport sys\nprint(" + repr(json.dumps(report)) + ")\n"
        + "sys.stderr.write(" + repr(stderr) + ")\nsys.exit(" + str(int(failed)) + ")\n")
    binary.chmod(0o755)
    schedule = candidate.generate_schedule([candidate.CELL_DEFINITIONS[0]], sessions_count=1)
    observer = candidate.observe_child
    captures = []
    def observe(*positional, **keywords):
        result = observer(*positional, **keywords)
        captures.append(result)
        return result
    with patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests), \
         patch.object(candidate, "host_state", return_value={}), \
         patch.object(candidate, "validate_host_state", return_value=(True, None)), \
         patch.object(candidate, "generate_schedule", return_value=schedule), \
         patch.object(candidate, "DISK_CEILING_BYTES", ceiling), \
         patch.object(candidate, "observe_child", side_effect=observe):
        try:
            candidate.main()
        except RuntimeError:
            pass
    assert captures
    destination = tmp_path / "out"
    records = sorted(destination.glob("observation_*.json"))
    assert len(records) == len(captures)
    for filename, capture in zip(records, captures):
        stored = json.loads(filename.read_text())["obs"]
        assert stored["stdout"] == capture["stdout"]
        assert stored["raw_stderr"] == capture["raw_stderr"]
        assert capture["direct_child_reaped"]
    metadata = json.loads((destination / "run_metadata.json").read_text())
    if failed:
        assert len(captures) == 1 and metadata["status"] == "failed"
    else:
        assert any(capture["exit_code"] == 0 and not capture.get("failure_reason") for capture in captures)
    assert sum(filename.stat().st_size for filename in destination.iterdir()) <= ceiling


@pytest.mark.parametrize("field,expected,reported", [
    ("query_repeats", 0, 7), ("query_repeats", 1, None),
    ("query_repeats", 0, True), ("query_repeats", 0, "0"),
    ("query_repeats", 0, -1), ("query_repeats", 0, 0.0),
    ("query_percent", 50, 99), ("query_percent", 50, True),
    ("query_percent", 50, "50"), ("query_percent", 50, 50.0),
    ("query_percent", 90, None),
])
def test_core_query_controls_match_requested_configuration(field, expected, reported):
    cell, report = core_report()
    cell[field] = expected
    if reported is None:
        report.pop(field, None)
    else:
        report[field] = reported
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


@pytest.mark.parametrize("schema", [2, 3, 4])
def test_core_query_control_legacy_and_native_defaults(schema):
    cell, report = core_report()
    cell.update(query_repeats=0, query_percent=50)
    report["schema_version"] = schema
    report.pop("query_repeats")
    report.pop("query_percent", None)
    parsed = p0.parse_core_output(json.dumps(report), "", cell)
    assert parsed["workload_wall_ns"] == report["repetitions"][0]["workload_wall_ns"]


def test_core_query_controls_use_requested_argv():
    cell, report = core_report()
    cell["argv"] = ["synthetic", "--query-repeats", "1"]
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


def test_sustained_query_percent_default_and_missing_nondefault():
    cell, report = core_report()
    cell["workload"] = report["workload"] = "dense-bridge-churn-v1"
    for repetition in report["repetitions"]:
        for operation, count in p0.expected_operation_counts(cell).items():
            repetition["measurements"][operation].update(count=count, total_ns=count)
        for name in ("query_true", "query_false"):
            repetition[name].update(count=50, total_ns=50)
    p0.parse_core_output(json.dumps(report), "", cell)
    cell["query_percent"] = 90
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


def test_observation_write_failure_enters_failure_handler(tmp_path):
    candidate, args, digests = candidate_args(tmp_path)
    observation = dict(exit_code=0, timed_out=False, stdout="bounded out", raw_stderr="bounded err", peak_rss_bytes=None)
    original = Path.write_bytes
    failed = []
    def write(filename, data):
        if filename.name.startswith("observation_") and not failed:
            failed.append(filename)
            raise OSError("synthetic observation write failure")
        return original(filename, data)
    with patch.object(sys, "argv", args), patch.object(candidate, "digest_file", side_effect=digests), \
         patch.object(candidate, "host_state", return_value={}), \
         patch.object(candidate, "validate_host_state", return_value=(True, None)), \
         patch.object(candidate, "observe_child", return_value=observation) as child, \
         patch.object(Path, "write_bytes", write):
        with pytest.raises(OSError, match="synthetic observation write failure"):
            candidate.main()
        assert child.call_count == 1
    saved = json.loads(failed[0].read_text())
    assert saved["status"] == "failed" and saved["failure_reason"]
    assert saved["obs"]["stdout"] == observation["stdout"]
    assert saved["obs"]["raw_stderr"] == observation["raw_stderr"]
    assert json.loads((tmp_path / "out/run_metadata.json").read_text())["status"] == "failed"


@pytest.mark.parametrize("invalid", [True, "1", 1.0])
def test_requested_control_type_cannot_be_hidden_by_argv(invalid):
    cell, report = core_report()
    cell.update(query_repeats=invalid, argv=["synthetic", "--query-repeats", "1"])
    report["query_repeats"] = 1
    with pytest.raises(p0.QualificationBlockerError):
        p0.parse_core_output(json.dumps(report), "", cell)


def test_valid_nondefault_query_repeats_preserve_first_metric():
    cell, report = core_report()
    cell.update(query_repeats=1, argv=["synthetic", "--query-repeats", "1"])
    report["query_repeats"] = 1
    for repetition in report["repetitions"]:
        repetition["repeated_queries"] = copy.deepcopy(repetition["measurements"]["connected"])
    assert p0.parse_core_output(json.dumps(report), "", cell)["workload_wall_ns"] == 10