# HDT v3: sparse levels reduce memory, with a measured repair-time cost

2026-09-28, Apple M3/macOS, Rust 1.98.1 release build. HDT remains experimental;
compact BFS remains the default. This milestone optimizes representation, not
the number of promotions. Do not present it as a general speed improvement.

## Scope and provenance

284 normal isolated processes plus 8 separate instrumented diagnostic processes.
The normal matrix uses one binary containing frozen HDT v2, sparse HDT v3,
unchanged ETT, compact BFS and petgraph DFS. Petgraph remains the adopted external
library baseline. No new claim about product adoption or GraphScope is made.

| Collection | Scope | Processes |
|---|---|---|
| [Sparse](manifest.json) | 10k/100k vertices, path/cycle blocks, 50/99% queries, 2,000 base operations, 2 trials, fresh/warmed, five engines | 160 |
| [Dense](../2026-09-28-hdt-v3-dense/manifest.json) | 512 vertices, one/two bridges between cliques, 50/99%, 2,000 operations, 2 trials, fresh/warmed, five engines | 80 |
| [Long](../2026-09-28-hdt-v3-long/manifest.json) | 10k cycle-block vertices, 50/99%, 10,000 operations, 2 warmed trials, five engines | 20 |
| [Repeated](../2026-09-28-hdt-v3-repeats/manifest.json) | 10k path/cycle blocks, 50/99%, 2,000 base operations plus one extra call per query, 1 trial, fresh/warmed, HDT v2/v3 and ETT | 24 |
| [Diagnostics](../2026-09-28-hdt-v3-profile/manifest.json) | 100k path/cycle blocks, 50/99%, 2,000 operations, HDT v2/v3, one process each | 8 |

Seed 42; case order shuffled deterministically. Fresh means no deliberate replay
warmup, not a CPU/OS cache flush. Warmed uses one untimed replay on a separate
engine instance. No affinity, thermal control or confidence intervals. Two
trials only provide a local indication of variability. Repeated calls have their
own timing fields and never contribute to base-operation totals. There is no
answer cache in either HDT implementation.

All snapshots and correctness checks run outside operation timers. Diagnostic
counter reads/snapshot allocations perturb caches; diagnostic timings are not
combined with normal measurements. Peak process RSS includes harness, traces,
JSON, warmup and allocator retention; it is not engine heap usage.

The manifests retain source hashes, tracked patches excluding old results,
untracked Rust sources, compiler/build information, binary hashes and artifact
hashes. The diagnostic manifest references and hashes the sparse manifest;
keep these directories together. [Audit](audit.json) checks artifact hashes,
source agreement, trace fingerprints and HDT counters across versions, cache
regimes and diagnostic replays. Raw trials remain in each summary CSV.

## What changed

F_0 retains dense direct indices. Higher levels now materialize vertices only
when promoted edges touch them, using stable local indices and ordered maps.
Absent vertices are implicit isolated singletons. Growing the graph does not
allocate a copy of every vertex at every level. Queries, exact immediate
visibility, external IDs and startup engine selectors keep the same contract.
Upper records and vector capacity are retained after cuts; no compaction was
added. Worst-case logical memory remains O(E + V log V).

## Structural storage, separate from RSS

Vector bytes are requested owned vector capacities, including per-edge arc
buffers and sparse reverse maps. Ordered bytes are live key/value payload only;
B-tree spare slots/node metadata and allocator overhead are unknown and excluded.
The returned snapshot itself is excluded. These columns cannot be labeled total
heap usage. All values below are MiB (2^20 bytes), 100k vertices.

| Graph | Stage | v2 vectors | v2 ordered payload | v2 vertex records | v3 vectors | v3 ordered payload | v3 vertex records |
|---|---|---|---|---|---|---|---|
| path | after_node_registration | 342.004 | 1.526 | 1800000 | 19.001 | 1.526 | 100000 |
| path | after_initial_edges | 379.530 | 7.629 | 1800000 | 56.527 | 7.629 | 100000 |
| path | after_replay | 379.530 | 7.569 | 1800000 | 56.527 | 7.569 | 100000 |
| blocks | after_replay | 519.497 | 7.955 | 1800000 | 252.713 | 13.583 | 468821 |

Before any edge exists, v2 already reserves 342 MiB of vector capacity for
1.8 million vertex records across 18 levels. V3 has 100,000 records in one level
and 19 MiB. After the cyclic q50 replay, sparse maps increase the ordered payload
but eliminate most untouched upper-level records. The accounting therefore
explains a real representation saving without subtracting unrelated process RSS.

## Normal timings and process memory

The tables use the arithmetic mean of two warmed trials. Time is the sum of
individually timed base calls in ms, excluding setup, oracle checks and repeated
queries. Setup and process RSS are separate. Each raw trial remains available;
means of p99 values below are not pooled percentiles.

100k vertices, 2,000 operations:

| Graph | Query % | Engine | Calls ms | Setup ms | Peak process MiB |
|---|---|---|---|---|---|
| path | 50 | hdt-v2 | 5.006 | 259.792 | 390.141 |
| path | 50 | hdt | 4.853 | 201.012 | 107.781 |
| path | 50 | ett-scan | 4.549 | 202.548 | 82.203 |
| path | 50 | compact-bfs | 6.116 | 18.778 | 16.836 |
| path | 50 | petgraph-dfs | 5.010 | 6.985 | 13.852 |
| path | 99 | hdt-v2 | 2.843 | 262.925 | 390.391 |
| path | 99 | hdt | 3.323 | 211.833 | 107.789 |
| path | 99 | ett-scan | 3.114 | 201.467 | 82.195 |
| path | 99 | compact-bfs | 123.844 | 18.278 | 17.273 |
| path | 99 | petgraph-dfs | 103.503 | 6.775 | 13.828 |
| blocks | 50 | hdt-v2 | 448.397 | 266.656 | 547.211 |
| blocks | 50 | hdt | 633.770 | 207.041 | 293.961 |
| blocks | 50 | ett-scan | 8.537 | 205.149 | 83.734 |
| blocks | 50 | compact-bfs | 7.636 | 19.428 | 16.797 |
| blocks | 50 | petgraph-dfs | 8.785 | 7.287 | 14.117 |
| blocks | 99 | hdt-v2 | 180.345 | 262.418 | 419.641 |
| blocks | 99 | hdt | 202.186 | 206.581 | 154.367 |
| blocks | 99 | ett-scan | 3.569 | 211.125 | 83.656 |
| blocks | 99 | compact-bfs | 145.609 | 18.978 | 16.805 |
| blocks | 99 | petgraph-dfs | 211.160 | 7.337 | 14.102 |

At q50 the path RSS decreases from 390.141 to 107.781 MiB (about 72%); cycle-block
RSS decreases from 547.211 to 293.961 MiB (about 46%). Cycle-block call time
increases from 448.397 to 633.770 ms (about 41%). Identical counters show the
saving does not come from doing fewer repairs. Upper-level map lookups/allocation
are a plausible added cost, not a CPU-profile attribution of every nanosecond.

512 vertices, dense controls (2,000 operations):

| Graph | Query % | v2 ms | v3 ms | ETT ms | Compact ms | Petgraph ms |
|---|---|---|---|---|---|---|
| one bridge | 50 | 8.270 | 8.833 | 376.705 | 17.895 | 182.961 |
| one bridge | 99 | 7.257 | 8.227 | 7.721 | 36.534 | 363.462 |
| two bridges | 50 | 8.047 | 8.889 | 229.776 | 18.296 | 202.403 |
| two bridges | 99 | 7.310 | 8.619 | 5.639 | 36.595 | 394.095 |

V3 retains a large advantage over ETT scans in these mutation-heavy dense cases,
but v2 is faster than v3 in all four warmed dense cells. With 99% queries,
ETT is faster than v3 here. The fixed clique topology rewards promotion reuse;
this is not evidence about arbitrary dense production graphs.

Long cycle-block histories (10k vertices, 10,000 operations):

| Query % | v2 ms | v3 ms | ETT ms | Compact ms | Petgraph ms |
|---|---|---|---|---|---|
| 50 | 40.733 | 52.868 | 6.791 | 4.645 | 3.161 |
| 99 | 19.624 | 24.291 | 2.356 | 29.960 | 38.049 |

The longer cyclic control preserves the regression; extra history alone does
not remove promotion cost. This trace progressively splits/rejoins selected
bridges; it is not unbounded arbitrary graph growth or a real-world workload.

## Expensive cuts

100k vertices, normal warmed runs. Mean of per-trial p99 and the largest observed
cut across those two trials (not a latency guarantee):

| Graph | Query % | Engine | Cuts/trial | Mean p99 µs | Largest cut ms |
|---|---|---|---|---|---|
| path | 50 | hdt-v2 | 995 | 20.979 | 0.052 |
| path | 50 | hdt | 995 | 21.980 | 0.055 |
| path | 99 | hdt-v2 | 20 | 45.646 | 0.053 |
| path | 99 | hdt | 20 | 43.645 | 0.046 |
| blocks | 50 | hdt-v2 | 959 | 7895.333 | 75.231 |
| blocks | 50 | hdt | 959 | 10925.959 | 74.512 |
| blocks | 99 | hdt-v2 | 20 | 30078.396 | 30.200 |
| blocks | 99 | hdt | 20 | 32130.917 | 32.139 |

The q99 traces have only 20 cuts; their p99 is the sample maximum. Do not read
these cells as a stable tail estimate. Instrumented cyclic q50 replay records
873 promoting tree cuts, 55 non-promoting tree cuts and 31 non-tree cuts, plus
368,203 tree and 21,721 non-tree promotions. More than 99% of its measured cut
time is in the promoting group, for both versions. This localizes the remaining
problem to promotion-bearing repairs; it does not separate AVL, map and allocator
CPU cost. The pure-path control performs no promotions.

## Decision and next experiment

Keep compact BFS as the default and `hdt` explicitly experimental. Retain v3 as
the lower-memory HDT representation, with its cyclic latency regression visible
in this report. Users prioritizing latency on sparse graphs should compare ETT
and compact against their own traces; on the measured path/cycle blocks ETT is
a much stronger HDT latency control. Petgraph remains the external baseline.

Next target the global/local mapping and promotion path with function-level
profiling before another optimization. A compact indexed mapping could reduce
lookup overhead, but must preserve growth bounds, arbitrary IDs and sparse
memory behavior. Compare it against both frozen v2 and v3, including worst cuts.
Do not change the default or add runtime engine switching on these results.

Core/server and benchmark formatting, Clippy, full tests/doctests and Rustdoc
passed. Independent reviews checked sparse-level invariants and instrumentation.
No commits, pushes, dependency additions or index changes were performed.
