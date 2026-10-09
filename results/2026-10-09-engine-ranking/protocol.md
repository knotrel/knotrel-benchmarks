# Five-engine ranking protocol — 2026-10-09

## Objective

Re-evaluate and update the comparative ranking of the five connectivity engines
following the integration of packed 64-byte tokens in both experimental ETT
(`knotrel-core/src/forest.rs`) and experimental HDT (`knotrel-core/src/hdt_forest.rs`).

The five evaluated backends are:
- `compact-bfs`: Knotrel's default adjacency-list BFS engine.
- `compact-workspace`: Knotrel's caller-owned query workspace using BFS.
- `ett-scan`: Knotrel's experimental Euler Tour Forest engine with packed tokens.
- `hdt`: Knotrel's experimental Holm-de Lichtenberg-Thorup engine with packed tokens.
- `petgraph-dfs`: External comparison using `petgraph` 0.8.3 with fixed-vertex DFS.

## Scope and Matrix

The benchmark matrix reconstructs exactly the 74 main cells of the historical
2026-10-06 ranking, with equal weight across all completed cells. Repeated-query
and ten-million-node supplements are explicitly excluded from the ranking:

1. **Sparse synthetic graphs (48 cells)**:
   - Node sizes: 1,024, 10,000, 100,000, 1,000,000.
   - Workloads: `sustained-churn-path-v1` and `sustained-churn-blocks-v1`.
   - Query percentages: 10%, 50%, 90%.
   - Regimes: fresh (warmup = 0) and warmed (warmup = 1).
   - Parameters: 10 rounds (1,000 operations), seed 42, query_repeats = 0, repetitions = 1.

2. **Dense synthetic graphs (24 cells)**:
   - Node sizes: 128, 512 (clique bridges).
   - Workloads: `dense-bridge-churn-v1` and `redundant-bridge-churn-v1`.
   - Query percentages: 10%, 50%, 90%.
   - Regimes: fresh (warmup = 0) and warmed (warmup = 1).
   - Parameters: 10 rounds (1,000 operations), seed 42, query_repeats = 0, repetitions = 1.

3. **Real network topology (2 cells)**:
   - Workload: `topology-zoo-outages-v1` on Cogentco topology (197 vertices, 243 edges).
   - Verified trace SHA-256: `d56e9371c2e290d7b115c43df65fd0a31949639821cbcf3f96617e15a1b82760`.
   - Regimes: fresh (warmup = 0) and warmed (warmup = 1).
   - Parameters: repetitions = 1.

Total: 74 cells × 5 engines × 3 independent process trials = 1,110 runs.

## Execution Rules and Environment

1. **Single Release Binary**:
   A single release binary is built (`cargo build --release --locked`) before collection.
   All compiler information (`rustc -vV`), environment variables, Git revisions,
   dirty statuses, and SHA-256 hashes of all source files in both `knotrel` and
   `knotrel-benchmarks` are recorded in `manifest.json`.

2. **Sequential, Non-Concurrent Execution**:
   All 1,110 process trials run strictly sequentially in a single process queue.
   No concurrent benchmarks, background builds, or CPU-intensive tasks may run.

3. **Balanced, Reproducible Order**:
   All 1,110 cases are generated deterministically and shuffled using
   `random.Random(42).shuffle(...)` to eliminate systematic order bias and environmental drift.

4. **Resource Measurement**:
   Each measurement is wrapped by `/usr/bin/time -l` on macOS to record maximum resident
   set size (peak whole-process RSS in bytes). RSS includes trace decoding, JSON serialization,
   warmup iterations, harness allocations, and engine memory. It is not engine-only heap.

5. **Timeout and Error Handling**:
   Process timeout is set to 120 seconds. Any timeouts, nonzero exit codes, or partial
   outputs are preserved and disclosed in `manifest.json`, `audit.json`, and `comparison.json`.
   No selective reruns or cherry-picked trials are permitted.

6. **Correctness Verification**:
   Across all five engines within every cell:
   - `trace_fingerprint_fnv1a64` must be identical.
   - Total operation counts (`cut`, `link`, `query`) must match exactly.
   - Query answer counts (`query_true`, `query_false`) must match exactly.
   - Incomplete cells are excluded from winning counts.

## Interpretative Limits

- **Implementations**: ETT and HDT are Knotrel experimental implementations with exact
  connectivity semantics. `petgraph` is the external Rust comparison library.
  GraphScope, Memgraph, and Differential Dataflow are not measured.
- **Whole-process RSS**: Peak RSS measures the whole benchmark process including the test
  harness, trace buffers, and warmup phases. It does not measure isolated graph heap memory.
- **No Throughput Inversion**: Throughput cannot be inferred by inverting median operation
  latency.
- **Cache Regimes**: Warmed/fresh regimes denote replay warmup without cache clearing;
  hardware CPU/L3 caches are not flushed. None of the backends cache connectivity query results.
- **Percentiles**: Percentiles (p50, p95, p99) are per-process values and must not be aggregated
  as if drawn from a single pooled distribution.
- **Domain Scope**: Cogentco is an imported telecommunications topology with synthetic
  failure sequences; it does not represent fraud detection, graph OLAP, or power-grid simulation.
- **Ranking Context**: Win shares describe this specific 74-cell workload selection, not a
  universal dominance guarantee.
- **Historical Comparison**: Comparison against the 2026-10-06 ranking represents observed drift
  across distinct campaigns, not an interleaved causal before/after attribution.
