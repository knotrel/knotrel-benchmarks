"""Repository-owned synthetic inputs for collector tests, never measurements."""

import copy
import hashlib
import json
from pathlib import Path


def write_inputs(root: Path):
    """Materialize synthetic plans/reports and real hashed placeholder files."""
    def save(filename, value):
        filename.parent.mkdir(parents=True, exist_ok=True)
        filename.write_text(json.dumps(value, indent=2) + "\n")

    def digest(filename):
        return hashlib.sha256(filename.read_bytes()).hexdigest()

    core = root / "checkouts/knotrel"
    bench = root / "checkouts/knotrel-benchmarks"
    for repo in (core, bench):
        repo.mkdir(parents=True)
        (repo / "Cargo.lock").write_text("synthetic lockfile\n")
    binaries = {}
    for name in ("knotrel_benchmarks", "measure_e2e", "knotrel_server"):
        filename = root / "bin" / (name if name == "measure_e2e" else name.replace("_", "-"))
        filename.parent.mkdir(exist_ok=True)
        filename.write_text("#!/bin/sh\nexit 99\n")
        filename.chmod(0o755)
        binaries[name] = {"path": str(filename), "sha256": digest(filename)}
    provenance = dict(binaries=binaries, knotrel_baseline_checkout=str(core),
                      knotrel_benchmarks_checkout=str(bench), knotrel_baseline_commit="1" * 40,
                      knotrel_benchmarks_commit="2" * 40,
                      lockfiles=dict(knotrel_lock_sha256=digest(core / "Cargo.lock"),
                                     benchmarks_lock_derived_sha256=digest(bench / "Cargo.lock")))
    seeds = [120047, 120048, 120049]
    cells = []
    for workload_id, workload in [("sparse_traversal", "chain-split-rejoin-v1"),
                                   ("dense_alternatives", "dense-bridge-churn-v1"),
                                   ("sustained_churn", "sustained-churn-path-v1")]:
        for engine in ("compact-bfs", "compact-workspace", "ett-scan", "hdt", "petgraph-dfs"):
            for regime in ("fresh", "warm"):
                cells.append(dict(cell_id=f"core_{workload_id}_{engine}_{regime}", type="core",
                                  workload=workload, workload_id=workload_id, nodes=128, rounds=10,
                                  seed=42, engine=engine, warmup=0, repetitions=1,
                                  cwd=str(root), argv=[binaries["knotrel_benchmarks"]["path"]], env={}))
    http = dict(cell_id="http_lifecycle_compact_bfs_small", type="http", engine="compact-bfs",
                workload="source-managed-lifecycle", tier="small", nodes=1000, edges=2000,
                events=500, queries=1000, seed=42, runs=1, cwd=str(root),
                argv=[binaries["measure_e2e"]["path"]], env={})

    for proposed in (False, True):
        selected = copy.deepcopy(cells[:15] if proposed else cells)
        selected.append(copy.deepcopy(http))
        if proposed:
            selected[-1]["report_schema"] = "measure_e2e.v1"
            selected.append(dict(http, cell_id="http_batch", scenario="standalone-batch",
                                 workload="standalone-batch", batch_size=64, report_schema="measure_e2e.batch.v1"))
        count = len(selected)
        manifest = dict(schema="knotrel-p0-pilot-manifest-v1", checkpoint="synthetic" if proposed else "P0-AA-Pilot-Plan",
                        provenance=provenance, pilot_design=dict(cells=selected, total_cells=count,
                            total_pairs=count * 6, total_measured_launches=count * 12,
                            sessions_count=3, session_seeds=seeds,
                            additional_child_launches=dict(total_child_servers=120 if proposed else 24),
                            total_process_launches=count * 12 + (120 if proposed else 24)))
        pairs = []
        for session in range(3):
            for cell in selected:
                for labels in (["A", "Aprime"], ["Aprime", "A"]):
                    pairs.append(dict(pair_id=len(pairs), session=session, cell_id=cell["cell_id"],
                                      labels=labels, argv=cell["argv"], cwd=cell["cwd"], env=cell["env"]))
        schedule = dict(schema="knotrel-p0-pilot-schedule-v1", total_cells=count,
                        total_pairs=count * 6, total_measured_runs=count * 12, pairs=pairs,
                        sessions=[dict(session_id=index, seed=seed, pair_count=count * 2) for index, seed in enumerate(seeds)])
        bundle = root / ("proposed-plan" if proposed else "pilot-plan")
        save(bundle / "manifest.json", manifest)
        save(bundle / "schedule.json", schedule)

    def latency(count):
        return dict(count=count, total_ns=count, min_ns=0, p50_ns=1, p95_ns=1, p99_ns=1, max_ns=2)
    repetition = dict(setup_ns=46916, workload_wall_ns=25875,
                      measurements=dict(cut=latency(10), link=latency(10), connected=latency(20)),
                      query_true=latency(10), query_false=latency(10), repeated_queries=None)
    report = dict(schema_version=2, workload="chain-split-rejoin-v1", engine="knotrel-core/compact-bfs-v1",
                  config=dict(nodes=128, rounds=10, seed=42), warmup=0, repetitions=[repetition],
                  trace_fingerprint_fnv1a64="ea72ce261a96e862")
    save(root / "core/core_smoke_report.json", report)
    http_dir = root / "http"
    http_dir.mkdir()
    markdown = ("| Run # | Import (ms) | Catch-up (ms) | Time-to-Ready (ms) | Query QPS | Latency p50 (\u00b5s) | Latency p95 (\u00b5s) | Oracle Agreement | Final Sampled RSS (MiB) | Sampled Max RSS (MiB)* | Restart Recovery (ms) |\n"
                "| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\n"
                "| **#1** | `2.97` | `2.77` | `6.37` | `9458.8` | `87.1` | `168.1` | `1000/1000 (100.00%)` | `7.55` | `7.55` | `34.98` |\n")
    (http_dir / "measurement_small_release.md").write_text(markdown)
    (http_dir / "stdout.log").write_text(markdown)


def synthetic_git_command(args, cwd=None):
    """Simulate declared fixture Git identities while real file hashes are checked."""
    if args == ["git", "rev-parse", "HEAD"]:
        return ("2" if "benchmarks" in str(cwd) else "1") * 40
    if args == ["git", "diff", "--cached", "--name-only"]:
        return "Cargo.lock"
    return ""