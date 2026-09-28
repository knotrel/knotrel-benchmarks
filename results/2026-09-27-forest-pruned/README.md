# Candidate-subtree pruning: controlled v1/v2 comparison

2026-09-27. The experimental ForestGraph now maintains candidate-presence
aggregates and enumerates candidates lazily. The default compact Graph and HTTP
service are unchanged. This remains an exact Euler-tour scan prototype, not HDT.

## Compared implementations

- `ett-scan-v1`: frozen original prototype, identity `knotrel-core/ett-scan-v1`,
  eager smaller-side vertex enumeration. Original token layout and timed methods
  preserved in benchmark-only code; imports and test-only accessors differ.
- `ett-scan`: current core, identity `knotrel-core/ett-pruned-v2`. Local candidate
  flags and subtree OR aggregates skip empty regions. Enumeration stops at the
  first crossing candidate. Ancestor maintenance is inside update/setup timings.
- Compact BFS and petgraph 0.8.3 remain practical controls in all but the repeat
  sensitivity suite. No external product-performance claim follows.

Each suite uses a single release executable containing both forest versions.
The first collection preceded a Rustdoc-only counter clarification; later builds
include it. There is no algorithm change between collections, and each manifest
records its actual source and binary. Hardware: Apple M3, macOS aarch64, Rust
1.98.1, thin LTO, one codegen unit. No added core dependency or unsafe code.

## Protocol

208 isolated, sequential process executions across four suites. Every process has
one measured replay, plus zero (`fresh`) or one (`warmed`) discarded replay.
Fresh is not hardware-cache cold. Cases are deterministically shuffled; no CPU
pinning/frequency/thermal/background controls. All results are checked against
independent topology-derived answers and all requested trials are retained.

| Suite | Nodes | Base operations | Query % | Regimes | Trials/config | Processes |
| --- | ---: | ---: | --- | --- | ---: | ---: |
| This matrix | 100,000 | 2,000 | 10/50/90/99 | fresh/warmed | 2 | 128 |
| [Million](../2026-09-27-pruned-million/README.md) | 1,000,000 | 2,000 | 50/99 | warmed | 1 | 16 |
| [Long](../2026-09-27-pruned-long/README.md) | 10,000 | 100,000 | 50/99 | warmed | 2 | 32 |
| [Repeats](../2026-09-27-pruned-repeats/README.md) | 100,000 | 2,000 + extra queries | 50/99 | fresh/warmed | 2 | 32 |

Both sustained path and connected-cycle-block families are used. Their topology
is not restored between rounds, but they are constrained sparse models, not dense
or adversarial graphs. Fixed operation counts imply different update counts and
fragmentation at different query percentages. At 99% in the short suites there
are only 20 updates, so cut p99 is effectively a small-sample maximum.

Base operation totals exclude setup, repeats, checking and teardown. Setup includes
registration-validation overhead, node registration and initial edges. Peak RSS
is the whole process, including trace export, allocator retention, warmup, harness
and engine; do not interpret it as engine-only heap. Extra repeats are separately
timed and still affect cache state. Other suites have no immediate repeats.

## Main result at 100,000 nodes

Warmed medians of two process summaries. Percentiles are not pooled and two
trials do not establish confidence intervals. Every trial, setup, latency maximum,
true/false query distribution and fresh result is retained in raw JSON/summary.csv.

| Family | Query % | v1 operations ms | v2 operations ms | v1 cut p99 µs | v2 cut p99 µs |
| --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 10 | 11.939 | 9.259 | 56.916 | 35.604 |
| blocks | 50 | 10.478 | 8.548 | 102.021 | 81.208 |
| blocks | 90 | 6.169 | 5.179 | 429.771 | 389.875 |
| blocks | 99 | 3.560 | 3.839 | 311.812 | 311.938 |
| path | 10 | 7.819 | 4.140 | 27.083 | 7.750 |
| path | 50 | 6.102 | 3.582 | 45.125 | 7.521 |
| path | 90 | 4.440 | 2.418 | 156.855 | 6.833 |
| path | 99 | 3.439 | 2.502 | 369.688 | 16.583 |

Path scans now yield zero vertices, versus 150,262–345,995 eager vertices in v1
on these traces. This reduces median base-operation totals by roughly 27–47%.
Block traces benefit less because internal non-tree candidates still need testing.
The 99%-query block case regresses from 3.560 ms to 3.839 ms; do not select only
winning cases or infer statistical significance from two trials.

## Scale and longevity

At one million nodes (one warmed trial), the 99%-query path's cut p99 drops from
6,542 µs to 27 µs. Its base operations fall from 27.640 ms to 10.890 ms. Blocks
still have expensive replacement searches: cut p99 is 9,846 µs versus 23,996 µs.
These are observations, not production tail-latency guarantees.

The tradeoff is material: forest setup at one million nodes rises from roughly
2.3–2.5 seconds to 3.0–3.15 seconds. Peak process RSS in the paired runs rises
from roughly 757–770 MiB to 784–804 MiB. The entire process is measured; differences
cannot be assigned solely to token storage. Faster operations do not imply a
faster short-lived full lifecycle.

On the 100,000-operation histories, differences shrink to roughly 0–5%:
fragmentation makes many components small, reducing the cost of v1 enumeration.
Petgraph remains faster than both forest variants at the 50% mix on these long
traces. These findings support keeping the forest opt-in and retaining practical
traversal baselines. Complete controls and costs follow.

| Family | Query % | Engine | Base ops ms | Setup ms | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: |
| blocks | 10 | compact-bfs | 1.250 | 18.698 | 16.7 |
| blocks | 10 | ett-scan | 9.259 | 220.572 | 83.7 |
| blocks | 10 | ett-scan-v1 | 11.939 | 151.086 | 80.5 |
| blocks | 10 | petgraph-dfs | 1.266 | 6.779 | 14.1 |
| blocks | 50 | compact-bfs | 7.092 | 18.857 | 16.8 |
| blocks | 50 | ett-scan | 8.548 | 202.690 | 83.6 |
| blocks | 50 | ett-scan-v1 | 10.478 | 152.919 | 83.8 |
| blocks | 50 | petgraph-dfs | 8.428 | 6.761 | 14.0 |
| blocks | 90 | compact-bfs | 32.425 | 19.336 | 16.8 |
| blocks | 90 | ett-scan | 5.179 | 201.558 | 83.7 |
| blocks | 90 | ett-scan-v1 | 6.169 | 149.814 | 80.3 |
| blocks | 90 | petgraph-dfs | 47.970 | 6.982 | 14.1 |
| blocks | 99 | compact-bfs | 126.738 | 18.878 | 17.0 |
| blocks | 99 | ett-scan | 3.839 | 205.369 | 83.5 |
| blocks | 99 | ett-scan-v1 | 3.560 | 150.024 | 80.1 |
| blocks | 99 | petgraph-dfs | 208.045 | 7.044 | 14.1 |
| path | 10 | compact-bfs | 1.081 | 17.667 | 16.7 |
| path | 10 | ett-scan | 4.140 | 196.814 | 82.2 |
| path | 10 | ett-scan-v1 | 7.819 | 144.373 | 79.1 |
| path | 10 | petgraph-dfs | 0.896 | 6.470 | 13.8 |
| path | 50 | compact-bfs | 5.929 | 17.520 | 16.7 |
| path | 50 | ett-scan | 3.582 | 198.145 | 82.1 |
| path | 50 | ett-scan-v1 | 6.102 | 144.568 | 79.0 |
| path | 50 | petgraph-dfs | 4.478 | 6.625 | 13.8 |
| path | 90 | compact-bfs | 30.194 | 18.173 | 16.7 |
| path | 90 | ett-scan | 2.418 | 196.252 | 82.1 |
| path | 90 | ett-scan-v1 | 4.440 | 149.787 | 78.9 |
| path | 90 | petgraph-dfs | 24.984 | 6.508 | 13.8 |
| path | 99 | compact-bfs | 119.020 | 17.821 | 16.8 |
| path | 99 | ett-scan | 2.502 | 197.731 | 82.1 |
| path | 99 | ett-scan-v1 | 3.439 | 145.937 | 78.6 |
| path | 99 | petgraph-dfs | 103.230 | 6.518 | 13.8 |

## Counters and verification

`scanned_vertices` is versioned: v1 counts every eagerly enumerated vertex;
v2 counts only candidate-bearing vertices actually yielded. Neither counts AVL
tokens visited or ancestor repairs; their ratio is not a CPU speedup. `tree_cuts`,
`candidate_edges` and `replacements` have unchanged semantics. All 60 paired v1/v2
configurations have identical values for those three counters, consistent with
preserving the candidate order and selected forest edges. Matrix-oracle tests
provide independent correctness evidence beyond that equivalence.

Three targeted tests failed on v1 and pass on v2: empty-candidate bridge cuts,
early replacement on a large cycle and clearing flags after the last non-tree
edge disappears. Random-history tests validate aggregates and edge classification
after every mutation. See [verification](verification.md) for full checks and hash
audits. No commits or pushes were made.

## Reproduction and next step

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 100000 --query-percent 10 50 90 99 --rounds 20 --trials 2 --regimes fresh warmed --engines compact-bfs petgraph-dfs ett-scan-v1 ett-scan
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

The remaining bottleneck on cyclic graphs is checking many internal non-tree
edges, not enumerating candidate-free vertices. Before HDT levels, quantify this
on dense/redundant graphs and stable-edge-count churn; separately investigate
setup and metadata layout to recover the observed regressions. Cluster Forest
remains an alternative to research for space efficiency, not a measured backend.
