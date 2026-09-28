# HDT levels: measured benefit and limits

Local Apple M3 / macOS, Rust 1.98.1 release build. Experimental
`knotrel-core/hdt-levels-v2` skips candidate-free replacement levels. Compact BFS
remains the default. These results do **not** support replacing ETT universally.

## Decision

- HDT helps when repeated deletions would rescan stable internal edges. In the
  512-node one-bridge dense case with 50% queries, the 2,000 timed operations take
  8.40 ms for HDT versus 393.68 ms for ETT and 19.87 ms for compact BFS. Setup is
  separate and reduces this advantage for short-lived graphs.
- A first large promotion is expensive. The same HDT case has cut p99 about
  0.67 µs but a maximum cut around 7.66 ms. Do not use the small p99 to hide the
  initial repair. With only 10 cuts at 99% queries, p99 is the maximum.
- Candidate-free pruning fixes the pure-path promotion problem, but per-level
  memory remains high. At 100,000 vertices, the warmed 50%-query path case takes
  4.86 ms for HDT versus 4.32 ms for ETT, with whole-process peaks around 390 MiB
  versus 82 MiB. Sparse cycle blocks remain much worse for HDT (463 ms versus
  7.96 ms). These sparse cells have one process trial per regime.
- Keep engine choice explicit. The next optimization target is per-level memory
  and tree-promotion cost in candidate-bearing sparse components; there is no
  evidence for making HDT the default or claiming a general product advantage.

## Protocol and provenance

All four backends within each collection use the same binary and ordered trace.
The primary adopted-library comparison is petgraph 0.8.3 DFS; ETT and compact BFS
are internal controls. No GraphScope, Differential Dataflow or Memgraph adapter
was measured here. HDT v1 and v2 are separate builds; their before/after numbers
are observations, not a same-binary isolated speedup experiment.

| Collection | Processes | Nodes | Base operations | Query share | Trials per cell | Regimes | Extra repeats |
| --- | ---: | --- | ---: | --- | ---: | --- | ---: |
| [v2 dense](summary.csv) | 64 | 512 | 2,000 | 50%, 99% | 2 | fresh, warmed | 0 |
| [v2 sparse](../2026-09-28-hdt-v2-sparse/summary.csv) | 64 | 10,000; 100,000 | 2,000 | 50%, 99% | 1 | fresh, warmed | 0 |
| [v2 longer dense](../2026-09-28-hdt-v2-long/summary.csv) | 16 | 512 | 10,000 | 50%, 99% | 1 | warmed | 0 |
| [v2 repeat control](../2026-09-28-hdt-v2-repeats/summary.csv) | 32 | 512 | 2,000 | 50%, 99% | 1 | fresh, warmed | 1 |
| [initial v1 dense](../2026-09-28-hdt-dense/summary.csv) | 128 | 128; 512 | 2,000 | 50%, 99% | 2 | fresh, warmed | 0 |
| [initial v1 sparse](../2026-09-28-hdt-sparse/summary.csv) | 64 | 10,000; 100,000 | 2,000 | 50%, 99% | 1 | fresh, warmed | 0 |
| [initial v1 repeats](../2026-09-28-hdt-repeats/summary.csv) | 32 | 512 | 2,000 | 50%, 99% | 1 | fresh, warmed | 1 |

400 separate backend processes total; 176 use final v2. Each process has one
measured replay. Warmed processes first replay on a separate fresh graph; this
warms code/allocator/hardware state, not the measured graph's HDT edge levels.
Fresh means no deliberate replay warmup, not cache flushing. Process order is
shuffled deterministically; seed 42 fixes all traces. Immediate repeated queries
are separately timed and excluded from base-operation totals. There is no answer
cache in either maintained engine. Timings include per-call timer overhead.

Tables use medians across the available process trials, never pooled latency
samples. A displayed cut p99/max is the median of per-process p99/max values.
Operation totals sum observed call times, not inverse p50 throughput. Setup is
engine creation plus initial loading; setup plus calls is still not end-to-end
HTTP or trace-generation time. Whole-process peak RSS includes trace generation,
export, warmup, allocator retention and samples; it is **not engine heap**.

Manifests retain source hashes, dirty state, patches, untracked Rust sources,
compiler, binary hash, commands and raw trace/report hashes. See [audit](audit.json).
The initial dense collector included 1.90 GB of already-staged historical
results in its source patch. After that collection completed, only its
`benchmarks.patch` was narrowed to exclude `results/`; original and replacement
hashes/byte counts are recorded in manifest `postprocessing`. Timings, traces,
measured Rust source and original collector copies were preserved. Later
collections apply this exclusion directly. A regression test covers staged
results so future snapshots do not recursively copy old measurements.

## Dense: 512 nodes, 2,000 operations

Each graph consists of two fixed cliques, with one or two toggled cross bridges.
Initial edges number 65,281 or 65,282. Same-clique membership or an active bridge
provides an independent oracle; small cases also pass matrix closure tests.
Internal edges never churn: this deliberately favors amortizing promoted stable
edges. It is not a random dense graph or a representative production distribution.

Warmed, median of two processes; timed operations in milliseconds:

| Topology | Queries | Compact BFS | petgraph DFS | ETT | HDT v2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| one bridge | 50% | 19.867 | 188.797 | 393.683 | 8.401 |
| one bridge | 99% | 42.841 | 390.238 | 8.964 | 8.752 |
| two bridges | 50% | 19.488 | 285.008 | 249.552 | 9.017 |
| two bridges | 99% | 37.204 | 387.772 | 5.958 | 8.840 |

Setup, cut tails and memory (same warmed cells):

| Topology | Queries | Engine | Setup ms | Setup + timed calls ms | Cut p99 µs | Cut max ms | Process peak MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| one bridge | 50% | compact-bfs | 5.632 | 25.499 | 0.230 | 0.001 | 7.94 |
| one bridge | 50% | petgraph-dfs | 19.324 | 208.121 | 0.062 | 0.000 | 8.01 |
| one bridge | 50% | ett-scan | 14.852 | 408.535 | 1255.000 | 6.027 | 12.19 |
| one bridge | 50% | hdt | 14.222 | 22.623 | 0.667 | 7.663 | 14.59 |
| one bridge | 99% | compact-bfs | 5.295 | 48.135 | 0.459 | 0.000 | 7.99 |
| one bridge | 99% | petgraph-dfs | 19.202 | 409.439 | 0.792 | 0.001 | 7.91 |
| one bridge | 99% | ett-scan | 15.249 | 24.214 | 1136.708 | 1.137 | 12.25 |
| one bridge | 99% | hdt | 15.819 | 24.570 | 8525.041 | 8.525 | 14.64 |
| two bridges | 50% | compact-bfs | 4.924 | 24.412 | 0.230 | 0.001 | 7.94 |
| two bridges | 50% | petgraph-dfs | 20.759 | 305.767 | 1.083 | 0.002 | 8.02 |
| two bridges | 50% | ett-scan | 15.538 | 265.091 | 1436.521 | 1.786 | 12.20 |
| two bridges | 50% | hdt | 16.268 | 25.285 | 1.729 | 8.303 | 15.11 |
| two bridges | 99% | compact-bfs | 4.658 | 41.862 | 0.250 | 0.000 | 7.91 |
| two bridges | 99% | petgraph-dfs | 19.117 | 406.890 | 1.000 | 0.001 | 7.91 |
| two bridges | 99% | ett-scan | 14.963 | 20.921 | 1085.458 | 1.085 | 12.21 |
| two bridges | 99% | hdt | 16.139 | 24.979 | 8536.875 | 8.537 | 14.84 |

For one bridge / 50% queries, 500 cuts produce 32,385,000 ETT non-tree incidence
checks versus 32,385 HDT checks and non-tree promotions, plus 255 tree promotions.
These count actual algorithm events, not equal-cost CPU instructions. HDT pays
most promotion work on the first repair. Base traces and counters agree across
fresh/warmed regimes; scheduling and cache state still affect timing.

## Longer dense traces

10,000 base operations, one warmed process per cell, milliseconds:

| Topology | Queries | Compact BFS | petgraph DFS | ETT | HDT v2 |
| --- | ---: | ---: | ---: | ---: | ---: |
| one bridge | 50% | 93.432 | 958.659 | 1955.630 | 11.181 |
| one bridge | 99% | 185.110 | 1916.458 | 40.253 | 8.259 |
| two bridges | 50% | 93.205 | 1007.481 | 1163.743 | 11.654 |
| two bridges | 99% | 244.701 | 2042.288 | 22.724 | 8.065 |

This extension makes the first promotion cost a smaller part of total work.
It still repeats changes only to the same one/two bridges; it does not validate
arbitrary sustained dense churn. Single-process values are observations, not
confidence intervals or stable service throughput.

## Sparse controls: 100,000 nodes

2,000 base operations, one warmed process per cell. Path edges and block bridges
change continuously; cycle blocks also cut/rejoin internal cycle edges.

| Topology | Queries | Engine | Timed ops ms | Setup ms | Cut p99 µs | Cut max ms | Process peak MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| path | 50% | compact-bfs | 5.963 | 18.190 | 0.458 | 0.001 | 16.72 |
| path | 50% | petgraph-dfs | 4.401 | 6.380 | 0.292 | 0.001 | 13.80 |
| path | 50% | ett-scan | 4.319 | 203.534 | 9.041 | 0.013 | 82.22 |
| path | 50% | hdt | 4.860 | 258.189 | 21.958 | 0.081 | 390.19 |
| path | 99% | compact-bfs | 119.428 | 18.147 | 0.958 | 0.001 | 16.73 |
| path | 99% | petgraph-dfs | 132.403 | 6.606 | 1.750 | 0.002 | 13.86 |
| path | 99% | ett-scan | 2.566 | 198.248 | 18.709 | 0.019 | 82.17 |
| path | 99% | hdt | 3.195 | 265.074 | 39.292 | 0.039 | 390.12 |
| cycle blocks | 50% | compact-bfs | 6.674 | 19.278 | 0.375 | 0.001 | 16.83 |
| cycle blocks | 50% | petgraph-dfs | 8.291 | 7.138 | 0.292 | 0.001 | 14.08 |
| cycle blocks | 50% | ett-scan | 7.962 | 202.333 | 66.917 | 0.565 | 83.72 |
| cycle blocks | 50% | hdt | 462.959 | 260.308 | 9664.375 | 71.437 | 548.84 |
| cycle blocks | 99% | compact-bfs | 126.652 | 19.229 | 0.833 | 0.001 | 16.84 |
| cycle blocks | 99% | petgraph-dfs | 211.984 | 7.300 | 0.875 | 0.001 | 14.12 |
| cycle blocks | 99% | ett-scan | 3.648 | 206.201 | 290.875 | 0.291 | 83.64 |
| cycle blocks | 99% | hdt | 181.343 | 262.207 | 29923.791 | 29.924 | 419.47 |

Initial v1 path / 50% measured 343.203 ms and 510.25 MiB versus v2's 4.860 ms and
about 390 MiB (separate builds/runs). The causal counter change is stronger evidence
than the timing ratio: v2 pure-path repairs perform zero tree promotions and zero
candidate checks. The correctness regression first observed 511 unnecessary
promotions in a 1,025-node path under v1 and then passed with zero in v2.

Candidate-bearing cycle blocks still force large promotions. At 100,000 vertices,
HDT's 50%-query block case is about 58 times slower than ETT in timed calls and
uses a much larger process footprint. No million-node HDT collection was attempted
in this milestone; the measured footprint already warrants caution about scale.

## Repeated-query and cache control

512 nodes, one bridge, 50% base queries. Each original query is immediately
repeated once; timings below keep the two populations separate. One process per
cell, p50 values in nanoseconds (timer resolution/overhead limits interpretation):

| Regime | Engine | Original query p50 ns | Repeated query p50 ns | Base ops ms | Extra query total ms |
| --- | --- | ---: | ---: | ---: | ---: |
| fresh | compact-bfs | 36541 | 36542 | 19.769 | 19.891 |
| fresh | petgraph-dfs | 229916 | 229792 | 188.560 | 187.852 |
| fresh | ett-scan | 125 | 83 | 374.233 | 0.082 |
| fresh | hdt | 84 | 83 | 9.472 | 0.080 |
| warmed | compact-bfs | 34167 | 34167 | 18.750 | 18.606 |
| warmed | petgraph-dfs | 231083 | 230917 | 193.025 | 192.148 |
| warmed | ett-scan | 125 | 83 | 375.891 | 0.075 |
| warmed | hdt | 84 | 83 | 8.768 | 0.079 |

All original and repeated answers pass the oracle. Query repeats are an altered
workload and may warm caches for later work; they are not a way to subtract an
assumed cache contribution. Fresh/warmed and 99%-query controls are retained in
the CSVs rather than combined into one headline. There is no controlled cache
flush, CPU pinning, thermal control or claim that this local sample generalizes.

## Verification and next work

Core/server: 41 tests and 2 doctests; benchmark: 19 Rust tests; collectors/probes:
11 Python tests. Formatting, Clippy and Rustdoc with warnings denied pass in
both workspaces. Algorithm/growth and adapter/oracle reviews were independent.
Existing original workloads and backend identities remain unchanged; only the
new HDT identity advances from v1 to v2. No dependencies or default engine changed.

Before considering a production default, reduce the per-level vertex/adjacency
footprint and evaluate promotion cost on candidate-bearing sparse graphs. Add
less structured churn and representative application traces. Keep setup and
worst observed cuts visible, and do not equate HDT's amortized bound with an SLO.
