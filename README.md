# Knotrel benchmarks

Reproducible workloads, measurement tools and recorded evidence for
[Knotrel](https://github.com/knotrel/knotrel), an in-memory engine for exact
connectivity in undirected graphs whose edges are inserted and deleted.

This repository answers three different questions, and its reports are kept
separate accordingly:

1. **Release regression qualification:** did a release candidate regress
   against the previous release on a fixed, pre-approved set of cells?
2. **Engine and competitor comparison:** how do Knotrel's engines compare with
   each other and with an external library on identical traces?
3. **Algorithm experiments and diagnostics:** did a specific code change or
   instrumentation behave as intended?

A result from one category does not answer another. Competitor rankings are
not release qualifications, and an algorithm experiment does not establish a
release-wide speedup.

## What is measured

- **Engines:** Knotrel `compact-bfs` (the default `Graph`), `compact-workspace`
  (opt-in caller-owned `BfsWorkspace`), experimental `ett-scan` (Euler-tour
  forest) and experimental `hdt` (Holm–de Lichtenberg–Thorup), compared with
  the external `petgraph-dfs` adapter. [Methodology](docs/methodology.md#embedded-comparisons-and-cache-protocol)
  lists further historical adapters.
- **Workloads:** deterministic synthetic families (chain, cycle, component and hub
  families; sustained churn on paths and blocks; dense and redundant bridge
  churn) and
  an imported Topology Zoo trace (Cogentco outages). See
  [scenarios](docs/scenarios/README.md), the
  [Topology Zoo adapter](docs/scenarios/topology-zoo.md) and
  [domain source selection](docs/research/2026-10-03-domain-scenarios.md).
- **Release qualification** additionally drives the `knotrel-server` HTTP
  service for batch and source-managed lifecycle cells.

### Important limitations

- Engine comparisons time **embedded library calls**, not HTTP requests or
  end-to-end service throughput.
- Each report covers its own host, scales and operation mixes. Results do not
  transfer automatically to other hardware, topologies or sizes.
- Warmups warm process and allocator caches; no hardware or OS cache flushing
  is performed. RSS covers the whole process, including the harness.
- Per-run percentiles are never pooled, and the fastest run is never selected.
  Very short operations can be timer-dominated.
- Every recorded report below was measured on macOS; each entry states the
  host details its report actually records.

See the [methodology](docs/methodology.md) for timing boundaries, correctness
checks, trace interchange and further limitations.

## Evidence by release and purpose

### Latest published release: v0.2.0

No v0.2.0-specific performance report is published in this repository. The
v0.2.0 sources (`7e9becd`) serve only as the **baseline** of the v0.3.0
qualification below.

### Current candidate: v0.3.0 regression qualification

The v0.3.0 candidate is **not yet published**. Its release qualification
compared Knotrel `6a1267f` (candidate) with v0.2.0 sources `7e9becd` rebuilt
with Rust 1.100.0 (baseline), using one shared harness (`df635a1e`), HTTP
driver and collector (`580c7e44`: baseline/candidate mode of
[`run_p0_aa.py`](scripts/run_p0_aa.py), prepared by
[`prepare_bc_qualification.py`](scripts/prepare_bc_qualification.py); see
[collector validation](docs/collector-validation.md) for reader rules). It ran on a macOS 26.5.2
arm64 host, in nine cells covering `compact-bfs` and `compact-workspace`
core workloads, standalone HTTP batches and source-managed HTTP readiness.

Outcome: **7 PASS and 2 INCONCLUSIVE**, accepted with disclosure under the
release policy. HTTP batch B8 (median paired change −1.42%, interval −15.63%
to +12.09%) and HTTP lifecycle readiness (+8.02%, −11.46% to +21.97%) did not
pass and do not exclude regressions. PASS is a decision under a pre-approved
tolerance, not a significance test. No speedup is claimed.

The per-cell table belongs to the v0.3.0 release documentation
(`docs/releases/v0.3.0-release-notes.md` and `docs/performance-v0.3.0.md` in
Knotrel). It becomes public when that candidate documentation is published.
Until then, Knotrel's public `main` still shows the earlier planning status. The
raw qualification reports are **not published** in either repository; this
summary is the only current public record. `ett` and `hdt` were not
re-qualified.

### Historical engine and competitor comparison

- **[Five-engine ranking, 2026-10-09](results/ranking/README.md):** 74 cells,
  three process trials per engine, Knotrel engines versus `petgraph-dfs`.
  Recorded checkouts: core `d1cfb15` (before the v0.1.0 preview) and benchmarks
  `bf7ddb0`, plus the captured [lockfile patch](results/ranking/benchmarks.patch).
  The report records macOS but not the CPU model or Rust toolchain. Wins are
  split across all five engines (Compact Workspace 31, ETT 22, HDT 17, Compact
  BFS 2, petgraph 2), so **no engine wins universally** in this matrix. It does
  not measure v0.1.0, v0.2.0 or the v0.3.0 candidate.

### Historical algorithm experiments and diagnostics

- **[ETT scan-root hardware profile, 2026-10-12](results/hardware-profile/README.md):**
  72 paired before/after recordings of one ETT candidate on Apple M4 under
  Instruments CPU Counters, following its [protocol](results/hardware-profile/protocol.md).
  A dense positive control improved; path workloads reproduced variability, not
  a stable speedup or regression. The committed report does not record its own
  source revision or Rust toolchain: it reuses isolated builds whose provenance
  was kept outside Git. Its whole-process predecessor, kept in history at
  [`1567a4e2`](https://github.com/knotrel/knotrel-benchmarks/blob/1567a4e2adee8f3e35eae9923107505868b3f01d/results/2026-10-12-ett-hardware-profile-m4/builds.json),
  recorded core `86fb85a8` plus the candidate patch, benchmarks `a3504d6d`, and
  Rust 1.98.1 on `aarch64-apple-darwin`. The report keeps the ETT candidate isolated.
- **[Bulk initialization Phase 0](results/initialization/README.md):**
  instrumentation and calibration for `try_from_edges`; core `61a3556`, Rust
  1.98.1, Apple M4 with macOS 27.0.1. It **stopped after calibration**, so no
  initialization baseline is established.
- **[Automated evaluation snapshot](results/perf_evaluation_latest.json):**
  per-engine results for 13 workloads, committed 2026-10-13. The file records
  no source revision, host or toolchain; treat it as historical and do not use
  it as a release measurement.
- Experiment designs and policies: [before/after policy](docs/experiments/2026-10-04-before-after-policy.md),
  [connectivity campaign](docs/experiments/2026-10-04-connectivity-campaign.md),
  [HDT candidates](docs/experiments/2026-10-06-hdt-candidates.md),
  [bulk loading design](docs/experiments/2026-10-12-bulk-graph-loading-design.md)
  and [initialization methodology review](docs/experiments/2026-10-12-initialization-methodology-review.md).

Older runs, pilots and campaign traces remain in Git history; see
[results/README.md](results/README.md).

## Local layout

Keep both repositories in the same parent directory, named `knotrel` and `knotrel-benchmarks`. The workspace uses `../knotrel/crates/knotrel-core` as a path dependency, so edits in your local core are measured immediately.

Both workspaces pin Rust **1.100.0**, edition **2024** and resolver **3**. The sibling `knotrel-core` retains Rust **1.98.1** as its MSRV. Third-party dependencies are locked in Cargo.lock. The path dependency is intentionally not revision-pinned: record the exact core revision and diff with every result.

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

`--engine compact-bfs` measures the default production `Graph`. The `all` selector includes all active backends. See the [historical engine ranking](results/ranking/README.md) for recorded numbers.

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
