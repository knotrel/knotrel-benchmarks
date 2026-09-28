# Local competitor comparison — 2026-09-26

This experiment compares synchronous embedded algorithms, not network services.
The primary external engineering baseline is petgraph 0.8.3. Outils 0.3.0 is an
old, low-adoption HDT implementation used only as an algorithmic control; beating
it would not establish a market advantage. See [candidate selection and adoption](../../docs/research/2026-09-26-competitive-landscape.md).

## Environment and protocol

Apple M3 / macOS aarch64, Rust 1.98.1; release thin LTO, one codegen unit.
The hardware was identified in the prior local baseline (8 cores, 16 GiB).
Sandboxed automatic hardware queries may be unavailable in the saved manifest.
CPU affinity, frequency, thermal state and background workload were uncontrolled.

Four families × three sizes (128, 1024, 4096) × two warmup regimes × four process
trials = **96 sequential process invocations**. Each process executes all four
backends, rotating their order by trial, on the same generated trace (100 rounds,
seed 42), with three measured fresh-graph repetitions per backend. There are
**1,152 measured backend repetitions**. Report every trial; do not treat the three
within-process repetitions as independent process trials.

`fresh` means zero deliberate replay warmups for that backend. It does not mean
flushed CPU, allocator, OS or page caches; other backends may already have run in
the process. `warmed` means one complete unreported replay for each backend,
followed by fresh graph construction. Every original query is immediately repeated
once and validated again. Repeat timings are separate from original query timings;
this augments the workload and can affect subsequent operations' cache state.
The base trace has 50% queries; with the extra repeats, the executed stream has
2/3 queries. Engine order rotation balances positions, not all cache interactions.

## Results at 4096 vertices, warmed regime

Values below are medians of **12 per-repetition summaries** (four processes ×
three repetitions). Operation p50s are in microseconds. Base operation totals are
milliseconds, followed by min–max across those 12 summaries. Totals exclude extra
query repeats, setup and harness overhead, but come from repeat-augmented runs;
they are not timings from a separate unaugmented execution. Do not sum medians or
invert a p50 to claim throughput.

| Workload | Backend | Cut p50 µs | Link p50 µs | Query p50 µs | Base operation total ms (range) |
| --- | --- | ---: | ---: | ---: | ---: |
| chain-split-rejoin-v1 | knotrel-benchmarks/dense-bfs-v1 | 0.083 | 0.083 | 14.958 | 2.279 (2.261–2.442) |
| chain-split-rejoin-v1 | knotrel-core/reference-bfs | 0.125 | 0.084 | 351.667 | 53.075 (51.437–53.812) |
| chain-split-rejoin-v1 | outils-0.3.0/hdt | 60.145 | 2.834 | 0.084 | 12.812 (12.572–12.997) |
| chain-split-rejoin-v1 | petgraph-0.8.3/dfs | 0.084 | 0.042 | 12.604 | 2.102 (2.044–2.205) |
| components-join-split-v1 | knotrel-benchmarks/dense-bfs-v1 | 0.083 | 0.083 | 10.541 | 2.171 (2.102–2.205) |
| components-join-split-v1 | knotrel-core/reference-bfs | 0.125 | 0.125 | 173.208 | 46.891 (46.212–49.405) |
| components-join-split-v1 | outils-0.3.0/hdt | 23.416 | 6.854 | 0.083 | 5.312 (5.082–5.457) |
| components-join-split-v1 | petgraph-0.8.3/dfs | 0.084 | 0.084 | 9.417 | 2.047 (2.026–49.442) |
| cycle-alternatives-v1 | knotrel-benchmarks/dense-bfs-v1 | 0.083 | 0.083 | 11.041 | 3.479 (3.393–3.571) |
| cycle-alternatives-v1 | knotrel-core/reference-bfs | 0.125 | 0.125 | 200.145 | 77.778 (76.872–79.971) |
| cycle-alternatives-v1 | outils-0.3.0/hdt | 19.125 | 0.333 | 0.125 | 15.881 (15.375–17.248) |
| cycle-alternatives-v1 | petgraph-0.8.3/dfs | 0.042 | 0.042 | 7.354 | 2.272 (2.205–2.392) |
| hub-alternatives-v1 | knotrel-benchmarks/dense-bfs-v1 | 0.083 | 0.042 | 6.875 | 4.534 (4.462–4.611) |
| hub-alternatives-v1 | knotrel-core/reference-bfs | 0.125 | 0.125 | 260.292 | 169.250 (164.576–189.015) |
| hub-alternatives-v1 | outils-0.3.0/hdt | 5.416 | 0.209 | 0.042 | 1.766 (1.724–2.015) |
| hub-alternatives-v1 | petgraph-0.8.3/dfs | 0.084 | 0.042 | 21.209 | 13.299 (13.090–13.669) |

## Interpretation

The reference's ordered-map BFS is a weak performance baseline: compact BFS and
petgraph DFS are substantially faster on these traces. This is a measured
representation/traversal improvement, not dynamic connectivity maintenance.
Petgraph uses DFS, with a different exploration order from BFS; topology and query
placement matter, particularly in the hub workload.

Outils makes queries much cheaper but pays for updates. At 4096 vertices it has a
higher median base-operation total than both traversal controls on chain, cycle
and joining-components traces, and a lower total on the hub trace. Its median
setup time is roughly 10–12 ms at that size. Fast query latency alone therefore
does not select the fastest engine for this workload mix. Nanosecond-scale query
values are timer/dispatch sensitive; do not infer hardware-independent nanosecond
promises or asymptotic scaling from them.

Both warmup regimes and every size are in `summary.csv`; raw JSON retains each
repetition, true/false query distributions, repeated-query latencies, setup cost,
counts and timing totals. No universal winner, crossover size or production SLO
is established. These graphs are sparse, restore topology each round and are at
most 4096 vertices. No RSS or allocator-memory measurement was made, so the
memory tradeoff remains open.

## Semantics and boundaries

All backends operate synchronously, pre-register vertices, retain isolated nodes,
reject self-loops and make duplicate links/absent cuts idempotent. The indexed
adapters use BTreeMap<u64, usize> so full-width IDs are supported with lookup cost
inside timings. Outils requires an edge-handle map, which is also timed; reflexive
connectivity is normalized to true for existing nodes. Its universe is fixed.
The adapters are not evidence that outils supports Knotrel's growing-node API.
Reference core behavior remains unchanged.

The dense BFS uses adjacency vectors, linear edge scans, swap-removal and reusable
visited/queue storage. Petgraph reuses DFS space. Both reset traversal state for
queries and cache no answers. Outils legitimately maintains connectivity state;
we do not disable it to manufacture a cache-free comparison. All query answers
are topology-derived; randomized histories, full u64 IDs, cycles, duplicate
updates and repeated queries are also tested against a matrix closure oracle.

Setup times include backend construction, registered IDs and initial edges.
Timed updates include required bookkeeping and replacement search; timed queries
include ID translation and scratch resets. Query timing buffers and correctness
checks are outside operation intervals. Workload wall time includes extra query
repeats and checking; setup and graph destruction are outside it.

## Reproduction

```sh
python3 scripts/run_baseline.py results/NEW_DIRECTORY --nodes 128 1024 4096 --rounds 100 --process-trials 4 --repetitions 3 --cache-regimes both --engines reference-bfs,dense-bfs,petgraph-dfs,outils-hdt --query-repeats 1
python3 scripts/summarize_comparison.py results/NEW_DIRECTORY
```

`manifest.json` records actual order, commands, compiler, environment, both Git
states, current build-input hashes, collector hash and executable hash. The saved
`run_baseline.py`, tracked patches and `untracked/...` Rust files preserve the
measurement implementation without requiring commits. Apply patches to the
recorded revisions and restore untracked Rust files to reconstruct source;
Cargo.lock pins external dependencies with registry checksums. Existing locked
package versions were preserved while new dependencies were added.

Checksums cover artifacts present at completion; this README and the later
summary/research/verification files are not in that original checksum set.
The original 2026-09-26-macos baseline is preserved, but these timings are not a
controlled before/after run against it. GraphScope, Memgraph and Differential
Dataflow were not executed, and no comparative claim about them is supported.
