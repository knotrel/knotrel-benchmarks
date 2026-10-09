# Traversal competitors across graph sizes — 2026-10-05

## Scope and result

**678 successful processes**, one release executable and identical source hashes:
Knotrel Compact BFS, Knotrel caller-owned Compact Workspace v2, and the external
petgraph 0.8.3 DFS adapter. This is a current shared comparison of three traversal
implementations, not a current ranking of ETT/HDT or graph database products.
All graphs use exact undirected connectivity and immediate visibility of updates.

There is no universal winner. On sparse graphs petgraph wins many path cases;
Knotrel often does better on cyclic blocks as size grows. Reusing BFS scratch
helps many cases but does not guarantee a win at one million vertices. Dense
controls favor Knotrel over this petgraph DFS adapter. Cogentco favors Workspace.

## Matrix and limits

| Family | Vertex sizes | Query ratios | Trials per engine/regime | Processes |
|---|---|---|---:|---:|
| Sparse path and cyclic blocks | 1,024; 10k; 100k; 1M | 10%, 50%, 90% | 3 | 432 |
| Two-clique dense controls, one/two bridges | 128; 512 | 10%, 50%, 90% | 3 | 216 |
| Extreme sparse exploration, path/blocks | 10M | 50% only | **1** | 12 |
| Real Cogentco topology with synthetic outages | 197 | imported trace | 3 | 18 |

Every row includes fresh (no deliberate warmup) and warmed (one replay on another
fresh graph). Hardware caches are not flushed and no query answers are cached.
Synthetic cases retain seed 42, ten rounds and 1,000 operations. Independent
oracle answers and mutation outcomes are checked by the runner. Fingerprints and
true/false counts match across every engine/trial in each cell. Real-topology
outages are controlled experiments, not recorded operator incidents.

The 10M results are **exploratory single observations**, not a reliable ranking.
All completed within a 120-second per-process timeout. Peak whole-process RSS
was about 208 MiB in the <=1M sparse matrix and 1,799 MiB at 10M; this includes
trace construction/serialization, setup, warmups and harness, not engine-only
memory. No memory ceiling was enforced. These are successful test points, not
maximum supported graph sizes. Dense graphs are not extrapolated to 1M/10M:
edge counts grow quadratically.

## Sparse ranking by size

Each size has 12 scenario/regime cells. Counts give equal weight to path/blocks,
query mixes and cache regimes. They are not workload prevalence, statistical
significance or a product score. Close timings can change order across runs.

| Vertices | Compact first places | Workspace first places | petgraph first places |
|---:|---:|---:|---:|
| 1,024 | 0/12 | 3/12 | 9/12 |
| 10,000 | 0/12 | 5/12 | 7/12 |
| 100,000 | 0/12 | 6/12 | 6/12 |
| 1,000,000 | 3/12 | 3/12 | 6/12 |

## Representative scale comparison: 50% queries, warmed

Compact is the explicit baseline: delta = `100*(engine runtime / Compact runtime - 1)`.
Negative is less time. These are median replay wall times, **excluding setup**;
setup/RSS/query/cut/link p95/p99 and observed ranges appear in the detailed table.
The two 10M rows have one trial and are labeled exploratory.

| Topology | Vertices | Compact ms | Workspace delta | petgraph delta |
|---|---:|---:|---:|---:|
| blocks | 1,024 | 0.352 | -33.3% | -34.6% |
| blocks | 10,000 | 0.875 | -22.3% | -0.3% |
| blocks | 100,000 | 5.064 | -11.9% | +48.2% |
| blocks | 1,000,000 | 42.827 | +1.5% | +62.4% |
| path | 1,024 | 0.186 | -32.8% | -41.7% |
| path | 10,000 | 0.667 | -29.0% | -32.0% |
| path | 100,000 | 4.531 | -15.5% | -19.0% |
| path | 1,000,000 | 41.509 | +1.4% | -14.7% |
| blocks (exploratory) | 10,000,000 | 519.820 | -23.2% | +24.7% |
| path (exploratory) | 10,000,000 | 488.079 | -15.3% | -24.5% |

On warmed Cogentco, Workspace takes 39.3% less replay time than Compact and
petgraph 30.1% less. That is one real topology, not evidence across industries.

## Why petgraph can match or beat default Compact

The source audit is for the actual pinned adapter, not a generic library claim:

| Detail | Compact | Workspace | petgraph adapter |
|---|---|---|---|
| Search | BFS | Same BFS ordering | DFS |
| Visit storage | New byte marks and queue each query | Reused u32 generations and queue | Reused DFS stack and FixedBitSet |
| Reset | Allocate/zero marks for all registered vertices | Advance generation; full reset only on rollover | Clear bitset for each search |
| Adjacency | Per-vertex vectors of usize neighbors | Same graph | Contiguous node/edge arenas with linked incidence indices |
| ID translation | BTreeMap | BTreeMap | Adapter BTreeMap |
| Target detection | While inspecting a neighbor | Same | DFS yields a vertex after examining its neighbors |
| Answer caching | None | None | None |

All three perform a new traversal rather than maintaining component labels.
Default Compact's per-query scratch allocation is a concrete disadvantage that
Workspace addresses. petgraph's packed bitset has smaller marking storage than
Workspace's four-byte epochs, but clearing and traversal work differ. DFS/BFS
ordering, early exits, adjacency layout and mark-on-pop versus mark-on-enqueue
can alter actual work. These are mechanisms identified in source, not measured
allocation/cache-miss attribution; this campaign did not count visited vertices.

For mutations, Compact locates edges with binary search in sorted adjacency
vectors and inserts/removes with shifts. petgraph finds edges by scanning
incidence lists, then uses edge swap removal and
repairs incidence links. The adapter does **not** use StableGraph and does not
benefit from petgraph's customary u32 default index: it explicitly selects usize.
The petgraph adapter pre-registers a fixed vertex universe; it does not implement
Knotrel's growing-node public contract. Timed ID lookups and duplicate checks are
included for both. This is a fair fixed-trace connectivity comparison, not full
API equivalence or network/server throughput.

Evidence locations: `crates/knotrel-benchmarks/src/engines.rs` (adapter), sibling
core `src/lib.rs` and `src/workspace.rs`; pinned petgraph source
`src/algo/mod.rs::has_path_connecting`, `src/visit/traversal.rs::Dfs`, and
`src/graph_impl/mod.rs::{Visitable,remove_edge}`. The Cargo lock and source hashes
are recorded; no dependency or product code was changed.

## Graph size is more than vertex count

Synthetic sparse graphs start as one connected component. Path has N−1 edges,
maximum degree 2 and mean degree near 2. Cyclic blocks add one closing edge per
up-to-16-vertex block: roughly 1.0625N edges, maximum degree 3, mean degree near
2.125. Dense controls start with two cliques and one/two bridges; for N=512 this
means 65,281/65,282 edges. Initial edge count, density, degree, true/false answer
counts and actual cut/link counts are retained per scenario in the JSON/table.

The number of operations remains fixed as N grows. As a result the fraction of
edges changed, component-size distribution and link/cut balance change; the
curves are not a controlled proof of asymptotic complexity. In particular many
large scenarios contain predominantly deletions, despite a nominal 50% mutation
ratio. Initial component sizes above do not describe the whole replay history.
Cogentco has 197 vertices and 243 simple edges; this is the same imported trace
and source provenance used in the historical campaign.

## Interpretation and next optimization

Keep the optional Workspace API rather than replacing the default from these
results. A more discriminating next experiment is an allocation/visited-edge
probe plus BFS versus DFS on the **same adjacency representation and scratch
policy**. This would isolate search order from memory layout; directly copying
petgraph's DFS would conflate them. No such optimization is claimed here.

ETT/HDT, Differential Dataflow, GraphScope and Memgraph have no placement in this
three-engine campaign. The historical four-engine ranking remains preserved.
Project adoption and stars are not performance evidence and are not re-ranked
here. This report compares implementations, not commercial product maturity.

## Reproduction and detailed evidence

[All scenario metrics](details.md) and [machine-readable comparison](comparison.json)
retain every outcome, including cases where Workspace or petgraph lose. Runtime
is replay wall time including dispatch, checks and sampling, not throughput.
Per-operation percentiles are medians of per-process percentiles, never pooled.

`collect.py` is a bounded variant of `scripts/run_scale.py`: no trace export
(the runner still fingerprints its generated trace), recorded failures rather
than discarding them, timeout 120s, and fresh output directories. Exact arguments,
source/binary hashes, revisions/dirty state, compiler and build-environment
settings are in each collection's manifest. Synthetic collectors shuffle all
cases with seed 42; they do not enforce strict Latin-square position balance.
`collect_real.py` reuses the exact same executable for Cogentco.
`analyze.py` audits file hashes, shared binary/source identity and cell fingerprints;
`report.py` regenerates this report. All 678 processes succeeded with zero oracle
failures. Existing source was not changed; no new correctness behavior needed a
Rust test rerun. Historical collections, staged changes and Git index are intact.
