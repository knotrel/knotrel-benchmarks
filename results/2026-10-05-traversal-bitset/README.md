# BFS epoch marks versus packed bitset — 2026-10-05

## Controlled change

This is a **benchmark-only** experiment. `traversal-bfs` uses reusable u32 epoch
marks; `traversal-bitset` uses reusable u64 words, one bit per vertex, cleared for
each non-reflexive query. Both use the same sorted adjacency, BTreeMap ID lookup,
mutation code, FIFO queue, marking on insertion and early target detection.
Queue and graph representation are unchanged. No connectivity answers are cached.
No production core API, default backend or server configuration was changed.

This custom bitset is not copied from petgraph and is not a claim to reproduce
its implementation. petgraph remains a DFS/bitset/edge-arena context baseline;
production `compact-workspace` is an anchor beside both experimental controls.
Controls are not assumed performance-identical to the production Workspace.

## Measurement contract

One release binary, 904 timed processes: 576 sparse, 288 dense, 16 extreme and
24 Cogentco. Sparse sizes are 1,024, 10k, 100k, 1M; paths and cyclic blocks;
10/50/90% queries; fresh/warmed; three process trials per engine/cell. Dense uses
128/512 vertices and one/two inter-clique bridges. Cogentco reuses the real
197-vertex topology with synthetic outages. 10M is one trial per cell, 50% queries
only, and is **exploratory**. All synthetic traces retain ten rounds and seed 42.

Runtime means median replay wall time including dispatch/checks/sampling but
excluding setup. Bitset reset is inside each timed non-reflexive query. Epoch
initial growth is also inside the first such query; rollover is tested but not
reached in this short campaign. Warmup recreates the graph and scratch before
measurement; it does not preallocate the measured workspace or flush hardware
caches. Cases execute sequentially in seeded shuffle order, not strict position
balance. Per-process operation percentiles are summarized, never pooled.

The before/after denominator is **epoch BFS in this same build**, not historical
timings. The prior DFS campaign is preserved; `baseline-drift.json` gives its
unchanged-trace epoch timing drift separately. Do not multiply historical speedups
to manufacture a current ranking. All metrics and unfavorable cases are retained.

## Runtime outcome

Delta = `100*(bitset/epoch - 1)`; negative means lower replay time. Cell summaries
are descriptive and equally weighted, not a production mix or confidence interval.

| Family | Cells | Bitset lower-runtime cells | Delta range | Median cell delta |
|---|---:|---:|---:|---:|
| sparse | 48 | 8 | -18.64% to +20.76% | +3.19% |
| dense | 24 | 11 | -3.77% to +3.85% | +0.61% |
| extreme | 4 | 2 | -11.76% to +24.62% | +3.21% |
| cogentco | 2 | 0 | +1.81% to +4.47% | +3.14% |

## Warmed 50% query examples

All three percentage columns use the experimental epoch BFS denominator.

| Family / topology | N | Epoch ms | Bitset delta | Production Workspace delta | petgraph delta |
|---|---:|---:|---:|---:|---:|
| sparse / sustained-churn-blocks-v1 | 1024 | 0.254 | +6.16% | -6.08% | -8.44% |
| sparse / sustained-churn-blocks-v1 | 10000 | 0.746 | +12.47% | -10.56% | +24.97% |
| sparse / sustained-churn-blocks-v1 | 100000 | 5.244 | +13.06% | -13.40% | +39.78% |
| sparse / sustained-churn-blocks-v1 | 1000000 | 49.807 | +4.87% | -16.71% | +44.42% |
| sparse / sustained-churn-path-v1 | 1024 | 0.130 | +3.34% | -1.60% | -15.43% |
| sparse / sustained-churn-path-v1 | 10000 | 0.492 | +4.35% | +4.99% | +15.98% |
| sparse / sustained-churn-path-v1 | 100000 | 3.970 | +3.11% | +5.24% | -8.78% |
| sparse / sustained-churn-path-v1 | 1000000 | 42.476 | -1.44% | -3.07% | -12.88% |
| dense / dense-bridge-churn-v1 | 128 | 0.655 | +0.85% | -4.23% | +614.21% |
| dense / dense-bridge-churn-v1 | 512 | 9.559 | +3.50% | -0.03% | +922.63% |
| dense / redundant-bridge-churn-v1 | 128 | 0.665 | -1.35% | +8.80% | +659.21% |
| dense / redundant-bridge-churn-v1 | 512 | 9.750 | +1.74% | +4.48% | +1013.25% |
| extreme / sustained-churn-blocks-v1 | 10000000 | 483.623 | +7.96% | -10.64% | +35.66% |
| extreme / sustained-churn-path-v1 | 10000000 | 425.938 | -1.54% | +3.50% | -7.98% |
| cogentco / topology-zoo-outages-v1 | 197 | 0.688 | +1.81% | -15.54% | -6.03% |

## Memory mechanism, not a process-memory promise

Logical mark payload is `4*N` bytes for epochs and `8*ceil(N/64)` bytes for bitsets:
approximately 32x smaller. This excludes Vec headers/capacity slack, allocator
metadata, BFS queue, graph, trace and harness. At 10M nodes this is 40,000,000
versus 1,250,000 bytes. The queue remains identical and may dominate scratch.
Process RSS in the detailed results includes all setup, traces and warmups;
it must not be interpreted as engine heap or marker allocation size.

Bitset clears every retained word on each non-reflexive query, even when only a
small component is reachable. Epoch marks usually avoid this reset but touch
larger entries during the visit. This is the expected tradeoff, not an attribution
of measured time to CPU caches: no hardware cache-miss or allocation profiler ran.

## Structural diagnostics

The separate `traversal-profile` uses COUNT=true; timed adapters use COUNT=false.
For each of 38 synthetic scenarios, two diagnostic runs must produce identical
output and match the timed fingerprint. Every query asserts exact expected
answers and **equal BFS/bitset expanded vertices, inspected arcs, peak pending
frontier and peak buffer length**. Diagnostic output contains no timing results.
Cogentco is timed but not structurally instrumented here. Peak vector length is
not allocated capacity. The retained DFS diagnostics are context only.

Validated 19,000 query comparisons across 38 scenarios, each replayed twice (76 diagnostic executions).


## Decision

Keep generation marks as the production Workspace strategy. In this campaign
bitset is slower in 40/48 sparse cells (median cell delta +3.19%), dense differences
are small and mixed (median +0.61%), and Cogentco is +1.81% warmed / +4.47% fresh
against the epoch control. Limited process trials do not establish significance
for close differences. This evidence does not justify a default or production
API change; it does not prove packed bitsets are universally inferior either.

Keep the bitset adapter as a reproducible memory/time tradeoff reference. At 10M,
mark payload falls from 40MB to 1.25MB, but observed whole-process RSS does not
consistently fall: in the single warmed path observation it increases from about
1,512 to 1,582 MiB. This is why mark-size arithmetic must not be presented as
measured process-memory savings. Extreme results are exploratory, not replicated.

Since per-query structural work is identical, the elapsed differences arise
outside a change in the chosen BFS traversal: marker/reset implementation and
associated compiled-code/access effects are candidates. This experiment cannot
assign individual CPU cycles to clearing, bit operations or cache behavior.
Neither switching to DFS nor replacing epochs with this bitset reproduces a
universal petgraph advantage. The next investigation should profile the remaining
adjacency/access costs before introducing another production strategy.

## Reproduction and checks

`collect.py` and `collect_real.py` retain exact arguments, revisions/dirty state,
source and binary hashes, compiler and build settings. New output directories
are mandatory; 120-second process timeout and whole-process RSS are recorded.
`analyze.py` verifies artifact hashes, cardinalities, source/binary identity,
fingerprints and answer counts. `collect_diagnostics.py` records separate profiler
identity. `report.py` verifies per-query work equality and regenerates these tables.

Formatting, all-target Clippy with warnings denied, workspace tests/doctests and
Rustdoc with warnings denied passed. Tests include bit boundaries at 63/64,
growth beyond one word, early target exit, subsequent cuts, scratch reuse on a
smaller graph, full-width IDs and independent matrix-oracle histories for all
13 adapters. Diagnostic fingerprint compatibility covers legacy and sustained
traces. Read-only review found no correctness blocker. Core production source,
Cargo.lock, existing results and staged user changes were preserved.

[Detailed timings, tails and RSS](details.md) and [raw comparison](comparison.json)
show every scenario and its observed process range. Close rankings can reverse
with timing noise; the 10M observations must not be treated as replicated wins.
