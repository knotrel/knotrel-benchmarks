# Controlled BFS versus LIFO search — 2026-10-05

## Contract and scope

These are **benchmark-only Knotrel controls**, not production engine options.
`traversal-bfs` and `traversal-dfs` share a snapshot of Compact's sorted adjacency,
BTreeMap ID translation, mutation implementation, u32 epoch marks and reusable
Vec scratch. Both mark on insertion and stop when an inspected neighbor equals
the target. DFS pops the last pending vertex; BFS advances a queue cursor.
This isolates FIFO/LIFO traversal and its inherent buffer-lifetime differences.
It does not reproduce petgraph's mark-on-pop DFS or its bitset/edge layout.

`compact-workspace` is a production-core anchor; `petgraph-dfs` is the external
context. The controls are not assumed binary-identical to the production BFS.
Every report labels the implementation. No default, server configuration or
production core API changed.

## Timed matrix

904 successful processes on one shared benchmark executable: 576 sparse, 288
dense, 16 extreme, 24 Cogentco. Sizes, seeds, workloads and operation traces
match the preserved traversal-scale study. Sparse: 1,024/10k/100k/1M, path/blocks,
10/50/90% queries; dense: 128/512 with one/two bridges; both fresh and warmed,
three independent processes per engine/cell. 10M uses only 50% queries and one
trial per engine/cell, so it remains exploratory. Cogentco uses the preserved
real topology with synthetic failures and three trials per regime.

Runtime is replay wall time, excluding graph setup; setup, whole-process peak
RSS and per-operation tails are retained in `comparison.json`. Fresh/warmed do
not mean hardware caches were flushed. Expected mutation/query results and exact
fingerprints are checked. New measurements never overwrite historical results.
Synthetic collection order is seeded shuffle, not perfect position balancing.

All deltas below are `100*(DFS/BFS-control - 1)`, so negative is less runtime.
Small sample counts and process variation limit close rankings. No confidence
interval or universal speedup is claimed. We do not pool per-operation percentiles.

| Family | Cells | DFS lower-runtime cells | Runtime delta range | Median cell delta |
|---|---:|---:|---:|---:|
| sparse | 48 | 13 | -17.27% to +78.60% | +8.37% |
| dense | 24 | 19 | -9.59% to +4.90% | -3.06% |
| extreme | 4 | 0 | +6.56% to +95.38% | +55.16% |
| cogentco | 2 | 2 | -38.77% to -38.12% | -38.45% |

Equal-weight summaries are descriptive, not production workload weights. Extreme
is excluded from any general recommendation. Inspect ranges before reading a
small median difference as a stable effect.

## Warmed 50% query scenarios and real topology

Workspace and petgraph percentages also use the **BFS control** denominator.

| Family / topology | N | BFS ms | DFS delta | Core Workspace delta | petgraph delta |
|---|---:|---:|---:|---:|---:|
| sparse / sustained-churn-blocks-v1 | 1024 | 0.257 | -12.62% | -9.17% | -10.03% |
| sparse / sustained-churn-blocks-v1 | 10000 | 0.760 | +21.40% | -16.13% | +14.70% |
| sparse / sustained-churn-blocks-v1 | 100000 | 5.355 | +56.47% | -19.59% | +35.27% |
| sparse / sustained-churn-blocks-v1 | 1000000 | 48.826 | +78.60% | -18.90% | +49.22% |
| sparse / sustained-churn-path-v1 | 1024 | 0.130 | -5.15% | -0.68% | -15.44% |
| sparse / sustained-churn-path-v1 | 10000 | 0.491 | +19.51% | +6.21% | -6.86% |
| sparse / sustained-churn-path-v1 | 100000 | 4.192 | +8.72% | -6.45% | -9.34% |
| sparse / sustained-churn-path-v1 | 1000000 | 41.871 | +5.73% | +0.44% | -13.96% |
| dense / dense-bridge-churn-v1 | 128 | 0.682 | -4.58% | -2.94% | +571.54% |
| dense / dense-bridge-churn-v1 | 512 | 9.668 | +4.90% | -1.75% | +886.58% |
| dense / redundant-bridge-churn-v1 | 128 | 0.679 | -7.26% | -8.59% | +629.03% |
| dense / redundant-bridge-churn-v1 | 512 | 10.308 | -1.72% | -0.45% | +920.32% |
| extreme / sustained-churn-blocks-v1 | 10000000 | 474.655 | +89.88% | -12.31% | +36.53% |
| extreme / sustained-churn-path-v1 | 10000000 | 420.263 | +6.56% | +12.40% | -8.90% |
| cogentco / topology-zoo-outages-v1 | 197 | 0.671 | -38.12% | -8.69% | -3.27% |

## Structural diagnostics

The separate `traversal-profile` binary instantiates `COUNT=true`; timed adapters
use `COUNT=false`, removing counter increments at compile time. Diagnostic results
contain **no timing measurements**. Counters measure expanded vertices (not
necessarily all discovered vertices), inspected adjacency entries, peak pending
frontier and peak Vec length. BFS retains expanded queue entries until query end;
DFS pops them. Vector length is not allocated capacity, heap bytes or process RSS.
No answer cache is used, and diagnostic state is reset for every query.

Diagnostics replay each synthetic scenario twice, require byte-identical output,
and match the timing fingerprint. Both searches assert each independent expected
answer against the same graph state. Cogentco has timings but no structural probe
in this version. Aggregate work is not sufficient to attribute cache behavior or
all execution-time changes to a single cause. Detailed per-query counts remain
available for true/false separation.

| Topology | N | Query % | DFS/BFS expanded delta | DFS/BFS examined arcs delta | BFS / DFS peak buffer length |
|---|---:|---:|---:|---:|---:|
| sustained-churn-blocks-v1 | 1024 | 10 | -0.55% | -0.55% | 400 / 40 |
| sustained-churn-blocks-v1 | 1024 | 50 | -0.05% | -0.14% | 608 / 46 |
| sustained-churn-blocks-v1 | 1024 | 90 | +1.21% | +1.24% | 608 / 76 |
| sustained-churn-blocks-v1 | 10000 | 10 | +0.12% | +0.10% | 3296 / 166 |
| sustained-churn-blocks-v1 | 10000 | 50 | -1.61% | -1.47% | 6704 / 586 |
| sustained-churn-blocks-v1 | 10000 | 90 | -2.64% | -2.42% | 6704 / 586 |
| sustained-churn-blocks-v1 | 100000 | 10 | -0.31% | -0.30% | 35728 / 988 |
| sustained-churn-blocks-v1 | 100000 | 50 | +1.35% | +1.61% | 71960 / 7482 |
| sustained-churn-blocks-v1 | 100000 | 90 | +0.07% | +0.44% | 91952 / 10846 |
| sustained-churn-blocks-v1 | 1000000 | 10 | +2.85% | +2.96% | 139824 / 18402 |
| sustained-churn-blocks-v1 | 1000000 | 50 | +0.69% | +0.73% | 507200 / 44838 |
| sustained-churn-blocks-v1 | 1000000 | 90 | -0.57% | -0.32% | 507200 / 60788 |
| sustained-churn-path-v1 | 1024 | 10 | +3.61% | +3.95% | 99 / 2 |
| sustained-churn-path-v1 | 1024 | 50 | +0.04% | +0.05% | 596 / 2 |
| sustained-churn-path-v1 | 1024 | 90 | -0.37% | -0.38% | 596 / 2 |
| sustained-churn-path-v1 | 10000 | 10 | +10.63% | +10.74% | 1785 / 2 |
| sustained-churn-path-v1 | 10000 | 50 | +0.57% | +0.57% | 4460 / 2 |
| sustained-churn-path-v1 | 10000 | 90 | -0.34% | -0.34% | 6074 / 2 |
| sustained-churn-path-v1 | 100000 | 10 | +0.00% | +0.00% | 15819 / 2 |
| sustained-churn-path-v1 | 100000 | 50 | -1.13% | -1.13% | 49891 / 2 |
| sustained-churn-path-v1 | 100000 | 90 | +0.63% | +0.63% | 66044 / 2 |
| sustained-churn-path-v1 | 1000000 | 10 | -1.16% | -1.16% | 75444 / 2 |
| sustained-churn-path-v1 | 1000000 | 50 | +1.33% | +1.33% | 915983 / 2 |
| sustained-churn-path-v1 | 1000000 | 90 | -0.96% | -0.96% | 915983 / 2 |
| dense-bridge-churn-v1 | 128 | 10 | +2.14% | +2.17% | 126 / 63 |
| dense-bridge-churn-v1 | 128 | 50 | +0.38% | +0.38% | 127 / 63 |
| dense-bridge-churn-v1 | 128 | 90 | +0.44% | +0.45% | 127 / 111 |
| dense-bridge-churn-v1 | 512 | 10 | +0.00% | +0.00% | 508 / 255 |
| dense-bridge-churn-v1 | 512 | 50 | -0.39% | -0.39% | 508 / 444 |
| dense-bridge-churn-v1 | 512 | 90 | +0.22% | +0.22% | 511 / 256 |
| redundant-bridge-churn-v1 | 128 | 10 | +1.34% | +1.36% | 127 / 63 |
| redundant-bridge-churn-v1 | 128 | 50 | +0.78% | +0.79% | 127 / 65 |
| redundant-bridge-churn-v1 | 128 | 90 | -1.92% | -1.95% | 127 / 120 |
| redundant-bridge-churn-v1 | 512 | 10 | -0.18% | -0.18% | 511 / 255 |
| redundant-bridge-churn-v1 | 512 | 50 | -0.57% | -0.57% | 509 / 444 |
| redundant-bridge-churn-v1 | 512 | 90 | +0.88% | +0.88% | 511 / 359 |
| sustained-churn-blocks-v1 | 10000000 | 50 | -1.34% | -1.15% | 8543936 / 737830 |
| sustained-churn-path-v1 | 10000000 | 50 | -1.28% | -1.28% | 6001418 / 2 |

For false queries the diagnostic checks equal expanded-vertex and examined-arc
counts, since both searches must exhaust the reachable component. True queries
can terminate in different places; DFS does not promise a shortest path.


## Decision

Do not replace production BFS with this DFS. It is slower in 35/48 sparse cells,
while its small dense differences are mixed and the Cogentco gains are specific
to one topology. Against actual core Workspace, the warmed Cogentco improvement
is 32.24%; against the BFS control it is 38.12%. These denominators must not be
interchanged. Keep both controls for investigation, not as server options.

On warmed cyclic blocks at 1M vertices and 50% queries, DFS takes 78.60% more
runtime than the BFS control. Diagnostics show only 0.69% more expanded vertices
and 0.73% more inspected arcs. Therefore extra traversal count alone does not
account for the magnitude of this timing gap. Access order, stack/queue behavior
and compiled-code effects remain plausible but unmeasured contributors; there
are no hardware cache-miss or allocation-count measurements here.

The BFS control itself differs measurably from production Workspace (for example,
19% on that cell), so this is a controlled experimental comparison, not a claim
that replacing a production method yields the reported percentage. Both anchors
are retained in every cell. petgraph's advantage cannot be credited to DFS alone:
it combines different mark timing, bitset storage and adjacency representation.
A next controlled experiment can hold BFS fixed and vary epoch marks versus a
packed bitset; that optimization is not implemented or claimed by this report.

## Reproduction and validation

`collect.py` and `collect_real.py` preserve commands, binary/source hashes,
compiler, environment, dirty source patches and new Rust files. `analyze.py`
checks cardinalities, artifact hashes, source/binary equality, fingerprints and
answer counts before ranking. `collect_diagnostics.py` records the separately
built profiler identity and source hashes. Diagnostics may have a later source
snapshot than the timed executable because the legacy-workload fingerprint fix, its test and CLI help text
were finalized after the timed collection; traversal kernels are unchanged.

Tests cover independent matrix-oracle histories for every engine, early exits,
cut/relink, unknown/full-width IDs, epoch rollover and known structural counts.
The CLI comparison checks all registered engines. Formatting, all-target Clippy
with warnings denied, workspace tests/doctests and Rustdoc with warnings denied
passed before delivery, including a regression test for legacy/sustained profiler trace identity. Instrumented values are never mixed into runtime
ranking. The previous source audit's claim that Compact used swap removal has
been corrected: Compact uses binary search and shifts in sorted neighbor vectors.
