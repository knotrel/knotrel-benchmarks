# Compact production core comparison — 2026-09-27

The production `Graph` is measured as `compact-bfs`; the preserved original
`ReferenceGraph` remains `reference-bfs`. Petgraph 0.8.3 DFS is the primary
external baseline. This is an embedded comparison, not an HTTP benchmark.

## Protocol

Apple M3 / macOS aarch64, Rust 1.98.1, release thin LTO, one codegen unit.
Four families, sizes 128/1024/4096, 100 rounds, seed 42. Two warmup regimes and
three independent process trials yield 72 sequential process invocations.
Each process runs all three engines in rotated order with three fresh-graph
measured repetitions per engine: 648 backend repetitions. All answers are
validated. Fresh means no deliberate replay warmup, not flushed CPU/OS caches;
warmed means one discarded replay. Hardware caches, frequency, thermal state
and background activity are uncontrolled. Validation/documentation processes
may overlap the beginning of the repeat-augmented collection.

This collection uses **0 extra immediate query repeats**. Extra calls are
reported separately; they affect cache state even when excluded from base totals.
The base trace is 50% queries; with one extra repeat the executed stream is 2/3
queries. Setup is reported separately. Total operation intervals exclude setup,
extra repeats, harness checks and destruction. Workload wall time is not service
throughput. Query p50 values below are medians of nine per-repetition summaries,
not pooled percentiles or nine independent process trials.

## Warmed results at 4096 vertices

| Workload | Backend | Query p50 µs | Base-operation total ms (min–max) |
| --- | --- | ---: | ---: |
| chain-split-rejoin-v1 | knotrel-core/compact-bfs-v1 | 17.875 | 2.911 (2.348–3.530) |
| chain-split-rejoin-v1 | knotrel-core/reference-bfs | 278.334 | 41.704 (39.360–47.468) |
| chain-split-rejoin-v1 | petgraph-0.8.3/dfs | 12.458 | 2.101 (1.952–2.273) |
| components-join-split-v1 | knotrel-core/compact-bfs-v1 | 11.083 | 2.284 (2.125–2.429) |
| components-join-split-v1 | knotrel-core/reference-bfs | 128.084 | 37.658 (36.965–41.507) |
| components-join-split-v1 | petgraph-0.8.3/dfs | 8.791 | 2.111 (1.967–2.198) |
| cycle-alternatives-v1 | knotrel-core/compact-bfs-v1 | 11.125 | 3.504 (3.212–3.656) |
| cycle-alternatives-v1 | knotrel-core/reference-bfs | 177.125 | 70.905 (66.020–150.164) |
| cycle-alternatives-v1 | petgraph-0.8.3/dfs | 7.416 | 2.267 (2.172–2.875) |
| hub-alternatives-v1 | knotrel-core/compact-bfs-v1 | 7.416 | 4.731 (4.495–4.775) |
| hub-alternatives-v1 | knotrel-core/reference-bfs | 210.209 | 139.852 (135.758–157.281) |
| hub-alternatives-v1 | petgraph-0.8.3/dfs | 21.083 | 13.151 (12.997–13.944) |

## Interpretation and limits

The compact core substantially reduces time against the ordered reference on
these traces. Petgraph remains faster on chain, cycle and component workloads;
the compact core wins the hub workload. This is not an HDT implementation or a
market-superiority claim. DFS/BFS exploration order and scratch reuse differ:
petgraph reuses workspace; production Graph allocates local scratch inside every
query timer to preserve its shared-reference API. All ID translation is timed.
Sorted-vector updates can cost O(degree) and regress on other update-heavy traces.

These sparse synthetic traces restore topology each round. They do not measure
sustained churn, large dense graphs, growing-node latency or RSS. Growth is
covered by correctness tests, not these timing traces. No universal crossover,
production SLO or memory improvement is established. All sizes and both regimes,
setup, original true/false queries and distributions remain in raw reports and
summary.csv. Do not compare timings directly to older runs as controlled speedups.

## Reproduction and verification

```sh
python3 scripts/run_baseline.py results/NEW_DIRECTORY --nodes 128 1024 4096 --rounds 100 --process-trials 3 --repetitions 3 --cache-regimes both --engines reference-bfs,compact-bfs,petgraph-dfs --query-repeats 0
python3 scripts/summarize_comparison.py results/NEW_DIRECTORY
```

The manifest records both dirty checkouts, commands, source/executable hashes,
collector and source snapshots. All 26 source hashes and
151 artifact hashes were checked after collection.
README and summary.csv were created later and are outside that checksum set.
Both workspaces pass formatting, Clippy and Rustdoc with warnings denied, and
locked tests. Core/server: 15 tests and one doctest; benchmarks: 12 Rust tests;
Python protocol/helper suite: eight tests. Independent review found no blocking
correctness issue; its documentation corrections were applied. No commit/push.

See the [repeat-augmented companion](../2026-09-27-compact-core/README.md)
for separately timed immediate repeated queries.
