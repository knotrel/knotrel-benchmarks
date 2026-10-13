# Knotrel benchmarks

Reproducible workloads for measuring exact dynamic graph connectivity.

## Current Benchmark Results

The active repository tree maintains benchmark evidence for the latest version of Knotrel. Detailed historical runs are preserved in Git history (see [results/README.md](results/README.md)).

- **[Current five-engine ranking](results/ranking/README.md)**: 74-cell evaluation across `Compact BFS`, `Compact Workspace`, `ETT`, `HDT`, and external `petgraph` following migration to `FxHashMap` and 64-byte token packing. Knotrel engines combined win **72 / 74 cells (97.3%)** against petgraph; Compact Workspace leads with 31 / 74 wins (41.9%).
- **[ETT scan-root hardware profile on Apple M4](results/hardware-profile/README.md)**: 72 fixed paired recordings validating signpost intervals, Apple M4 CPU performance counters, ~45% dense workload speedup, and path variance under hardware profiling.
- **[Bulk graph initialization](results/initialization/README.md)**: Phase 0 calibration and replication records for bulk graph construction (`try_from_edges`) and stage-based timing accounting.
- **[Continuous performance evaluation](results/perf_evaluation_latest.json)**: Latest automated regression evaluation metrics.

---

## Architecture & Engines

The harness compares Knotrel's own connectivity backends with external libraries:
- `compact-bfs`: **Knotrel's default backend** (`Graph`).
- `compact-workspace`: Knotrel's opt-in caller-owned workspace backend (`BfsWorkspace`), avoiding allocation on repeated traversals.
- `ett-scan`: **Knotrel's experimental backend** maintaining dynamic spanning forests via Euler Tour Trees with 64-byte packed tokens.
- `hdt`: **Knotrel's experimental backend** implementing Holm-de Lichtenberg-Thorup multilevel dynamic graph connectivity.
- `petgraph-dfs`: External baseline wrapped by benchmark adapter.

Measured calls are embedded kernel operations, not HTTP service requests.

Workloads include deterministic synthetic families and imported topology traces. The harness validates every result and supports trace export, warmup, and separate reports for repeated fresh-graph runs.

See [domain source selection](docs/research/2026-10-03-domain-scenarios.md), [scenarios and contracts](docs/scenarios/README.md), and [Topology Zoo adapter](docs/scenarios/topology-zoo.md) for domain-specific workloads.

## Local layout

Keep both repositories in the same parent directory, named `knotrel` and `knotrel-benchmarks`. The workspace uses `../knotrel/crates/knotrel-core` as a path dependency, so edits in your local core are measured immediately.

Both workspaces pin Rust **1.98.1**, edition **2024** and resolver **3**. Third-party dependencies are locked in Cargo.lock. The path dependency is intentionally not revision-pinned: record the exact core revision and diff with every result.

## Run

```sh
cargo run --release --locked -- --nodes 10000 --rounds 1000 --seed 42
```

Select a workload and save a reusable trace:

```sh
cargo run --release --locked -- --workload cycle-alternatives-v1 --nodes 4096 --rounds 200 --seed 42 --warmup 1 --repetitions 3 --trace-out cycle.trace.json
```

`--help` lists all families and flags. Defaults preserve the original chain sequence, with one warmup and one measured replay. Each repetition starts with a fresh graph. Trace output refuses to overwrite files. JSON report schema 2 stores latency summaries under `repetitions[i].measurements`, with separate cut/link/connected summaries; it also records topology and trace fingerprint.

See [methodology](docs/methodology.md) for topology, ratios, timing boundaries, trace interchange and limitations.

Reproduce a complete matrix:

```sh
python3 scripts/run_baseline.py results/NEW_RUN_DIRECTORY
```

## Development

```sh
cargo fmt --all -- --check
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo test --workspace --locked
RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked
```

All public items require English Rustdoc. Complex private code documents invariants and costs. See [methodology](docs/methodology.md) before comparing engines. CI checks out the sibling core repository; its Rust foundation must exist in the selected core revision first.

## Comparing backends

```sh
cargo run --release --locked -- --engine all --nodes 4096 --rounds 100 --query-repeats 1 --repetitions 3
```

Multiple engines produce schema 3 containing one schema-2 report per backend. Setup, original true/false queries and immediate repeated queries are reported separately. Repeats augment the workload; no hardware-cache flushing is implied.

For the full recorded protocol with independent process trials and rotated order:

```sh
python3 scripts/run_baseline.py results/NEW_COMPARISON --nodes 128 1024 4096 --rounds 100 --process-trials 4 --repetitions 3 --cache-regimes both --engines all --query-repeats 1
python3 scripts/summarize_comparison.py results/NEW_COMPARISON
```

`--engine compact-bfs` measures the default production `Graph`. The `all` selector includes all active backends. See [current engine ranking](results/ranking/README.md) for latest numbers.

## Dynamic forest and scale workloads

`--engine ett-scan` selects the experimental maintained forest. For sustained churn and process memory measurements:

```sh
python3 scripts/run_scale.py results/NEW_SCALE_RUN --nodes 10000 100000 --query-percent 10 50 90 99 --rounds 20 --trials 2
python3 scripts/summarize_scale.py results/NEW_SCALE_RUN
```

One round is 100 operations for sustained families. RSS covers the whole process, including the harness.

## Experimental Knotrel HDT

`--engine hdt` selects `knotrel-core/hdt-sparse-levels-v3`, with separate `hdt_stats` promotion/search counters. HDT maintains multiple forests and uses more memory; its update bound is amortized. Dense stress families `dense-bridge-churn-v1` and `redundant-bridge-churn-v1` keep two cliques fixed and toggle one or two bridges.

```sh
python3 scripts/run_scale.py results/NEW_HDT_RUN --nodes 128 512 \
  --workloads dense-bridge-churn-v1 redundant-bridge-churn-v1 \
  --query-percent 50 99 --rounds 20 --trials 2 \
  --engines compact-bfs petgraph-dfs ett-scan hdt
python3 scripts/summarize_scale.py results/NEW_HDT_RUN
```

### HDT storage diagnostics

```sh
cargo run --release --locked --bin hdt-profile -- --engine hdt --nodes 512 --rounds 10 --workload dense-bridge-churn-v1 --query-percent 50
```

The JSON contains structural storage snapshots after registration, initial edges and replay, registration/loading stage durations, cumulative work counters and operation latency groups.
