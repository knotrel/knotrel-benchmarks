# Bulk graph initialization: architecture, performance, and design

## Implementation update (2026-10-13)

Phase 0 is **closed** following the failed
[identical-path A/A validation](../../results/2026-10-12-initialization-aa/README.md).
Its outcome is accepted; no further calibration or relaxed statistical criteria
are planned. Existing evidence is preserved.

The first correctness-only increment implements the Section 4 signature on
[`ConnectivityGraph`](../../../knotrel/crates/knotrel-core/src/configuration.rs):
`try_from_edges(engine, limits, nodes, edges)`. It executes the reference
`with_limits` / ordered `add_node` / ordered `link` sequence literally.
The invariant after each accepted input item is the same backend state as the
incremental prefix; errors drop the unpublished local graph. No separate
construction representation or weakened backend invariant is introduced.

This deliberately narrows the original Phase 1 plan below: normalization,
reservation and new indexed-insertion helpers are deferred. No backend changes,
new dependencies, direct forest construction, HTTP integration or harness
timing changes are included. Slices are borrowed, input is not collected or
reordered, and auxiliary space beyond graph construction is O(1). Time and
allocations remain those of incremental construction. Cardinality ceilings
remain distinct from memory limits; allocation failure is not recoverable
through `GraphError`. Streaming and raw-backend constructors remain out of scope.

[Differential tests](../../../knotrel/crates/knotrel-core/tests/bulk.rs) cover all
three engines, ordered/reversed construction of every simple graph through five
vertices, sparse/dense/cyclic/disconnected inputs, duplicates, implicit vertices,
full-range IDs, exact/zero limits and first-error precedence. Dynamic continuations
compare operation results, counts and all-pairs connectivity with incremental
construction and, for topology histories, the independent ordered reference graph.

Acceptance for this increment is correctness, maintainability and the complete
workspace quality gates, **not a performance threshold**. No performance
improvement is claimed. The remaining text records the original design and
its now-deferred optimization/measurement proposals, not authorization to resume
measurement.

The harness integration is the optional `--init-mode bulk` of `initialization-profile`
(facade surfaces, whole timing only); see the
[methodology](../methodology.md#optional-bulk-initialization-mode).

Validation completed for this increment:

- Core/server workspace: **74 tests/doctests passed**, including the four new
  bulk tests (6,600 small-graph construction pairs and 2,160 limit/input cases,
  in addition to topology histories and explicit error-order cases).
- Benchmark workspace: **38 correctness tests passed**; these include existing
  CLI smoke checks, not calibration campaigns.
- Both workspaces passed `cargo fmt --all -- --check`,
  `cargo clippy --workspace --all-targets --locked -- -D warnings`,
  `cargo test --workspace --locked`, and
  `RUSTDOCFLAGS='-D warnings' cargo doc --workspace --no-deps --locked`.
- All 82 + 82 + 375 manifest-listed artifacts from the two calibrations and
  A/A stage were hash-verified unchanged. No performance collection was run.

**Original proposal status:** No implementation or new measurements at writing.
**Date:** 2026-10-12.
**Decision:** Start with an order-preserving constructor using bounded
reservation and shared incremental insertion primitives. Measure construction
phases before investing in direct Euler-tour construction.

## 1. Scope and evidence

Review baseline:

- Core: `61a3556435f10ec9d5fe768682f1195ebd22ac71`.
- Benchmarks: `1567a4e2adee8f3e35eae9923107505868b3f01d`.
- Both worktrees were clean at the start of this review.
- Rust 1.98.1, edition 2024; existing dependencies and algorithms only.

The integrated ETT scan-root optimization is part of the baseline, not a new
variable. This proposal neither reopens that investigation nor changes its
evidence. Initialization means creating a new graph, not adding a batch to an
existing live graph, restoring promoted HDT state, or changing engines in place.
No HTTP endpoint, persistence format, dependency, production code, or benchmark
result is changed by this document.

**Evidence labels:** source facts are verified against the implementation;
measurements are observations from saved runs; predicted savings are hypotheses
until a controlled construction comparison measures them.

### Source map

Paths into `knotrel` assume the documented sibling-checkout layout. Line anchors
refer to the review revisions; they are not a promise about future line numbers.

| Area | Source |
| --- | --- |
| Public graph/error contract; compact adjacency | [core lib.rs](../../../knotrel/crates/knotrel-core/src/lib.rs#L44), especially `Graph::add_node` / `link` at lines 122/141 |
| Engine dispatch and cardinality checks | [configuration.rs](../../../knotrel/crates/knotrel-core/src/configuration.rs#L96), especially `add_node` / `link` at lines 130/155 |
| ETT node registration and edge classification | [dynamic.rs](../../../knotrel/crates/knotrel-core/src/dynamic.rs#L62) |
| Shared AVL arena, allocation, and metadata | [index.rs](../../../knotrel/crates/knotrel-core/src/index.rs#L132) |
| Root/rank/reroot/link and candidate maintenance | [index.rs](../../../knotrel/crates/knotrel-core/src/index.rs#L327) |
| HDT base/sparse levels and incidences | [hdt.rs](../../../knotrel/crates/knotrel-core/src/hdt.rs#L44), public initialization at lines 184/205 |
| HDT exact-level mark semantics | [hdt_forest.rs](../../../knotrel/crates/knotrel-core/src/hdt_forest.rs#L30) |
| Reusable BFS scratch, not another graph representation | [workspace.rs](../../../knotrel/crates/knotrel-core/src/workspace.rs#L5) |
| Harness setup timer and loading loop | [main.rs](../../crates/knotrel-benchmarks/src/main.rs#L233) |
| Adapter creation and node validation | [engines.rs](../../crates/knotrel-benchmarks/src/engines.rs#L166) |
| Strict benchmark import, distinct from the core API | [imported.rs](../../crates/knotrel-benchmarks/src/imported.rs#L35) |

### What the existing timing evidence actually measures

The [2026-10-09 ranking](../../results/2026-10-09-engine-ranking/README.md),
[comparison data](../../results/2026-10-09-engine-ranking/comparison.json), and
[manifest](../../results/2026-10-09-engine-ranking/manifest.json) contain
initialization measurements, not measurements of a bulk implementation.
Selected **warmed, 90%-query cells**, three process trials per engine:

| Initial topology | V | E | Compact setup median | ETT setup median [min, max] | HDT setup median [min, max] |
| --- | ---: | ---: | ---: | ---: | ---: |
| Path | 1,000,000 | 999,999 | 203.047 ms | 3,184.644 [3,167.591, 3,292.580] ms | 1,820.106 [1,761.037, 1,919.468] ms |
| Cyclic blocks | 1,000,000 | 1,062,499 | 208.133 ms | 3,199.950 [3,169.036, 3,209.436] ms | 1,958.435 [1,925.420, 3,074.556] ms |
| Two cliques with one bridge | 512 | 65,281 | 4.635 ms | 13.991 [13.511, 14.398] ms | 13.713 [13.496, 13.739] ms |

These numbers are copied from the corresponding `rows[].engines[engine].metrics.setup_ns`
fields, not from ratios of maxima or prose summaries. Query percentage labels
identify cells; queries occur **after** setup. These observations establish that
setup warrants investigation, not which function dominates it.

Important qualifications:

1. `setup_ns` starts **before** allocating `(0..node_count).collect::<Vec<u64>>()`,
   constructing the adapter, and inserting initial edges. Trace generation,
   file parsing/import validation, operation sample buffers, replay, and graph
   destruction are outside that interval.
2. `Engine::new` unconditionally constructs a `BTreeMap` from the node slice to
   validate uniqueness. Knotrel's raw backend branches then build their own ID
   maps and discard the temporary map. This is additional allocation/work in
   measured setup; its duration has not been separated. Do not label a harness
   cleanup as a core bulk-loading speedup.
3. The adapter calls raw `Graph`, `ForestGraph`, and `HdtGraph`, not the
   limit-enforcing `ConnectivityGraph` wrapper. Existing timings do not quantify
   initialization with configured cardinality limits.
4. Those runs used core `0c3a02338d43dcb699337b1bd60d72fcd3f3aa7e`, benchmark
   `046c42e19c5198c6b51ca40cba445b4a5fbbcae9`, Rust 1.98.1, and reported
   macOS 26.5.2 arm64. Current `main.rs` and `engines.rs` SHA-256 values match
   the saved manifest, so the timing-boundary observations apply to that
   campaign. Historical absolute times are not a new interleaved baseline.
5. Peak RSS from `/usr/bin/time -l` includes warmup, trace storage, setup,
   dynamic replay, and serialization. It cannot establish peak construction
   memory or the number/cost of allocations. The
   [ranking protocol](../../results/2026-10-09-engine-ranking/protocol.md)
   explicitly states this limitation.

No saved evidence here separately measures ID hashing, vector growth, sorted
insertion shifts, AVL balancing, or incidence-set maintenance. Claims that any
one of them dominates setup would exceed the evidence.

## 2. Existing initialization architecture

### 2.1 Public APIs and transport boundary

All raw backends expose `new`, `add_node`, `link`, `cut`, and `connected`.
`ConnectivityGraph::with_limits` owns one selected backend and enforces
immutable `GraphLimits`. Links create missing endpoints; cuts retain vertices.
The wrapper adds dispatch and validation, not a bulk construction path.

The server currently starts an empty configured graph in
[server main.rs](../../../knotrel/crates/knotrel-server/src/main.rs).
Embedding can provide a graph to the router. HTTP
[service batches](../../../knotrel/crates/knotrel-server/src/service.rs#L120)
hold one graph lock, but an operation error does **not** roll back preceding
operations. An atomic constructor must not silently change this batch contract.

The existing benchmark import is stricter than core `link`: it requires a
normalized node universe and canonical, unique initial edges. That input
restriction is useful for fixtures, but must not become an accidental
restriction on the proposed general Rust constructor.

### 2.2 BFS / compact graph

**Verified storage and work**

- `IntMap<NodeId, usize>` maps arbitrary `u64` IDs to append-only indices.
- `Vec<Vec<usize>>` stores sorted, unique, symmetric adjacency; a scalar counts
  undirected edges. There is no initial spanning forest to construct.
- `add_node` uses a hash-map entry lookup, appends an empty adjacency vector,
  and inserts the ID when absent. Outer vector/map growth may allocate/copy.
- `link` checks self-loops, calls `add_node` twice even for pre-registered
  endpoints, and then looks up both IDs again. It binary-searches adjacency
  for duplicate detection and insertion positions, inserts at both endpoints,
  and increments the count once.
- Binary search is logarithmic in degree; inserting in the middle moves a
  suffix of the vector. Capacity reservation can remove growth, **not shifts**.
- No connectivity search is performed to insert an edge.
- `BfsWorkspace` affects later queries only. Its empty initial state does not
  require preallocating visited arrays during graph construction.

**Potentially avoidable:** repeated endpoint lookups; outer/inner vector and
map growth; repeated sorted insertion for an unordered high-degree input.
**Inherent:** reading IDs/edges, duplicate handling, storing both incidences,
and ensuring sorted adjacency for the existing dynamic implementation.

Input order matters: the generated path and lexicographically emitted clique
edges often append to already sorted lists. Their timings are not evidence for
the worst-case shifting cost; a shuffled-edge case is required.

### 2.3 ETT / `ForestGraph`

**Verified storage and work**

- An ID `IntMap`, a vector of `BTreeSet<usize>` non-tree neighbor sets, an
  `FxHashMap<(usize, usize), Option<(usize, usize)>>` edge map, and
  `GenericForest<bool>`.
- Each registered vertex receives one permanent token. Each spanning-tree
  edge receives two directed tokens; the edge map stores their handles.
  Non-tree edges have `None` handles and incidences at both endpoints.
- Tokens and vertex-token indices use vectors; edge tokens released by later
  cuts go on a free list. Pure initialization has no released slots.
- `link` repeats endpoint registration/lookups, canonicalizes the edge key,
  checks duplication, then compares the two forest roots.
- If disconnected, `GenericForest::link` reroots both tours and joins them.
  Rerooting uses root and rank walks, AVL splits/concatenation, balancing, and
  metadata repair. Its extra `debug_assert!(!connected(...))` is not release
  workload cost.
- If already connected, two ordered non-tree-set insertions occur, followed
  by candidate-flag refreshes. `update_candidate_flag` immediately returns if
  the flag is unchanged; during insertion-only construction each vertex's
  boolean can change from false to true at most once. Do not charge a full
  ancestor traversal for every refresh call.

A finished insertion-only forest with V vertices and C components contains
`V + 2(V-C) = 3V-2C` live tokens, independent of the number of non-tree edges.
Reserving two tokens **per graph edge** would be a serious dense-graph mistake.
The packed token is 64 bytes on the tested 64-bit layout; one million connected
vertices imply 2,999,998 live tokens, approximately 183.1 MiB of token payload
alone, excluding capacities, ID/edge maps, and incidences.

**Potentially avoidable:** repeated ID resolution, reallocations, using AVL
connectivity to classify every edge during a static insertion-only build, and
maintaining the tour incrementally when its complete final tree is known.
**Still required:** a spanning forest for every component, valid arc handles and
AVL metadata, and representation of all non-tree edges. Fewer allocations do
not by themselves remove logarithmic tree maintenance.

### 2.4 HDT / `HdtGraph`

**Verified storage and work**

- Global ID and edge hash maps; each edge has an exact level and a
  `TinyVec<[Arcs; 4]>` of handles. Initially a tree edge uses one inline handle
  pair; a non-tree edge uses an empty vector, not a separate heap allocation.
- The first vertex materializes dense level zero. `Level::ensure` creates a
  permanent forest token plus empty exact-level tree/non-tree `BTreeSet`s.
- Higher levels are sparse: missing vertices are implicit singletons, and
  their local/global maps materialize on promotion. Initial insertion creates
  **only F_0**, not V vertices in every possible level.
- `add_node` checks ID presence, ensures the base-level record, then inserts
  the ID. `link` calls it twice, looks up IDs, checks duplicate keys, compares
  F_0 roots, links tours if necessary, and inserts exact-level incidences.
- All inserted edges start at level zero. Both tree and non-tree edges have
  symmetric incidence sets here, unlike ETT's non-tree-only sets.
- `incidence` ensures/translates endpoints and refreshes the two mark bits.
  During initial insertion each bit changes at most once per vertex; repeated
  refreshes can return immediately through the shared candidate-flag helper.
- Promotions and higher-level repair occur on dynamic tree deletion, not
  initial insertion. The full HDT update bound is not a bill for building
  every level during setup.

Initial logical storage is O(V+E), with one materialized forest when V > 0.
The general O(E + V log V) storage bound concerns subsequent histories, not
mandatory eager initialization. Sparse-level construction must remain lazy.

### 2.5 Limits, dependencies, and common repeated work

The wrapper enforces self-loop rejection before mutations; new-node limits
precede edge limits; duplicates succeed even at capacity. With a node ceiling,
it uses `connected(x, x)` as a presence check. BFS returns early after ID
lookups; raw ETT/HDT delegate to `GenericForest::connected`, which in source
walks two roots even for identical local indices. Thus the wrapper's prose
about never traversing for checks is too strong for those backends. A private
ID-membership check could avoid that work; no timing contribution is measured.

Existing [core dependencies](../../../knotrel/crates/knotrel-core/Cargo.toml)
already provide fast integer hashing, bitsets, and inline vectors. Standard
`BTreeSet` has no capacity-reservation API. No dependency replacement is needed.
The server's `mimalloc` global allocator is declared in its executable; it does
not automatically apply to the benchmark executable or embedded core.

## 3. Cost model and alternatives

Let:

- N = explicit node occurrences; M = input edge occurrences, including duplicates.
- V = distinct registered IDs, including edge-only endpoints and isolates.
- E = distinct accepted undirected edges; C = final component count.
- T = V-C spanning edges; R = E-T non-tree edges.
- `L = log2(V+1)`.
- `B_nt` / `B_all` = ordered-set insertion cost over non-tree / all incidences.
  Both are bounded by O(E L), but reflect actual endpoint degrees.

Bounds assume ordinary expected/amortized hash-table behavior, not adversarial
collision resistance. Zero/one-vertex cases use V+1 inside logarithms.
All strategies must at least read O(N+M) input; duplicate-heavy input cannot be
treated as E work. Retained data needs O(V+E) space initially.

### A. Reserved incremental construction and shared indexed insertion

Keep edge order, classification, tour linking, and incidence updates unchanged.
Extract a private registration helper returning the local index and a private
local-endpoint insertion primitive from each backend's existing `link`. Public
`link` delegates to the same primitive: no second implementation of mutations.
Private presence checks handle limits without a connectivity query.

Reserve known/validated counts for ID/edge maps, outer adjacency containers,
vertex-token indices, and the base token arena. Reserve no eager HDT upper
levels and no O(E) free list. Do not promise to reserve B-tree nodes.

| Backend | Time after this optimization | Memory / risk |
| --- | --- | --- |
| BFS | Same bound: O(N + M L + sum(deg(v)^2)) in the unfavorable sorted-insertion order; fewer hash probes/reallocations | Little extra scratch; reservation may retain slack. Low risk if insertion order is unchanged. |
| ETT | O(N + M + E L + T L + B_nt + V L), still O(N + M + (V+E)L) as an upper bound | O(V+E) retained, bounded reservation slack. Low-to-moderate helper/limit-ordering risk. |
| HDT | Similar, with B_all instead of B_nt, all on level zero | O(V+E) initial storage, no upper-level expansion. Must preserve exact-level marks/handles. |

These are upper bounds, not measured cost shares. In particular vector growth
is already amortized, and candidate refresh often returns immediately.
For low-degree paths reservation does not remove T logarithmic tour links.

### B. Dedicated bulk path sharing internal primitives

Use the complete finite input to normalize IDs/deduplicate edges in first-seen
order, count degrees, and pass local endpoints to existing backend primitives.
Do not build one universal backend representation.

- **BFS:** fill two degree-sized adjacency arrays by append, then sort/dedup
  as needed, instead of maintaining sorted order after each insertion.
  With normalized unique edges, time is
  O(N+M + sum(deg(v) log(deg(v)+1))). This improves the unfavorable
  repeated-shift bound; on already append-friendly input it can do more work.
- **ETT:** an ephemeral union-find can classify edges in input order, then
  use the existing AVL `link` only for spanning edges. By induction its
  partition equals forest connectivity after every processed prefix, so the
  first accepted spanning-edge set matches incremental construction.
  Time becomes O(N+M + E alpha(V) + T L + B_nt + V L).
  A path still has T = E; its tour-linking logarithmic factor remains.
- **HDT:** the same classifier is valid for insertion-only level-zero
  construction. Keep `Level::incidence`, inline arc handles and marks.
  Replace B_nt by B_all in that bound. Do not assign higher initial levels.

Defer expensive candidate-aggregate repair only if a separate proof and test
shows that a final bottom-up pass produces identical flags before publication;
this is not part of the first step. Union-find is temporary build scratch and
must never become a stale dynamic connectivity cache.

Normalized edge storage/deduplication can add O(E) scratch; ID mapping, degrees,
and union-find add O(V). Reuse the final ID map where feasible instead of
maintaining two copies. A one-pass order-preserving variant can use the final
edge map for duplicate checks, but cannot know every exact capacity upfront.
Medium complexity/risk: validation ordering, duplicates, temporary ownership,
and preservation of forest selection all need tests.

### C. Direct construction of the initial forest

First establish registered IDs, unique edges, components and a spanning forest.
For compatibility, prefer input-order union-find to choosing an unrelated DFS
spanning forest. Then, for each component:

1. Generate a valid Euler-tour sequence with one permanent vertex token and
   two directed tokens per spanning edge. Record both handles for every tree
   edge, preserving the traversal nesting required by `cut`.
2. Populate edge maps and final incidence sets, deriving each permanent
   token's candidate/mark bits without repeated ancestor updates.
3. Build a balanced implicit AVL tree over that sequence by midpoint
   construction, setting parent/child indices, height, token count, vertex
   count, and aggregate OR bottom-up. Leave the free list empty.
4. Validate the complete representation before returning it.

Tour generation and balanced materialization take O(V+T) time; use an explicit
DFS stack for graph traversal so a million-node path does not recurse a million
frames. Only balanced-tree construction may recurse O(log V) deep.

**Meaningful algorithmic advantage:** the T incremental O(log V) AVL links
become O(V+T) forest materialization. With input-order union-find:

- ETT: O(N+M + E alpha(V) + V + B_nt).
- HDT: O(N+M + E alpha(V) + V + B_all).
- BFS has no spanning forest; its applicable direct construction is B's
  append-and-sort adjacency build, not an Euler-tour builder.

A DFS over complete adjacency could classify in O(V+E), but may choose a
different spanning forest and needs the full adjacency scratch. It is not the
compatibility-first recommendation. Keeping `BTreeSet` means neither direct
ETT nor HDT is unconditionally linear in all graph edges. Sparse trees are a
more promising asymptotic target than dense graphs whose ordered incidences
can still dominate the upper bound.

Scratch can reach O(V+E): normalized edges/sets plus O(V) traversal, sequence
and ID/union-find buffers coexist with final storage. Account for their peak
lifetime, not just retained capacity. HDT should construct F_0 only; upper
forests remain implicit singletons. All initial edges at level zero satisfy
the HDT component-size hierarchy, with
`U = next_power_of_two(max(V, 1))`.

**High risk:** a balanced token tree is not sufficient unless the sequence is
a correct Euler tour with valid arc pairs. Bugs can remain invisible to initial
connectivity and appear only on later cuts, token reuse, or HDT promotions.
Even the same spanning-edge set can have a different AVL shape/tour order,
changing replacement discovery order, diagnostic counts and later latency.
This is a later construction specialization, not a replacement dynamic
algorithm and not the first implementation.

## 4. Proposed minimal Rust contract

One fallible owned constructor on the existing engine facade; illustrative
signature, not implemented:

```rust
impl ConnectivityGraph {
    pub fn try_from_edges(
        engine: EngineConfig,
        limits: GraphLimits,
        nodes: &[NodeId],
        edges: &[(NodeId, NodeId)],
    ) -> Result<Self, GraphError>;
}
```

Borrowed slices provide finite, replayable input and require no iterator
collection policy, lifetime on the result, builder object, backend trait, or
public local-index API. Callers pass `GraphLimits::default()` for no ceilings.
Streaming ingestion and raw-type convenience constructors are deferred, not
silently emulated by collecting an unbounded stream.

### Reference semantics

The definition of success and semantic error precedence is this ordered
sequence, executed on an unpublished local graph:

```rust
let mut graph = ConnectivityGraph::with_limits(engine, limits);
for &node in nodes {
    graph.add_node(node)?;
}
for &(a, b) in edges {
    graph.link(a, b)?;
}
Ok(graph)
```

| Concern | Required behavior |
| --- | --- |
| Duplicate vertices | No-op; preserve the first occurrence's registration index. Count distinct IDs toward the node limit. |
| Duplicate/reversed edges | No-op; one undirected edge, no duplicate incidences or replacement arcs. Do not reject a duplicate merely because the edge limit is reached. |
| Edge-only endpoints | Auto-register them as current `link` does, source before target, after that edge's validation. The node slice supplies isolates as well as pre-registration; it is not a closed universe. |
| Self-loops | Return `GraphError::SelfLoop` for the first reached offending edge. No endpoint creation for that edge. Do not pre-scan later self-loops ahead of earlier limit errors. |
| Disconnected/empty input | Valid. Preserve explicit isolates. Empty inputs return an empty graph; all existing reflexivity and unknown-node query rules apply afterward. |
| Limits | Enforce `GraphLimits` on distinct accepted nodes/edges. Process nodes first; per edge use self-loop, node-limit, then edge-limit precedence. Enforce before changing that edge's state. `Some(0)` remains meaningful. |
| Atomicity | Return a fully usable owned graph or `Err`; no partially built graph is returned and no existing graph is changed. Do not offer in-place rollback or change HTTP batch semantics. |
| Errors | Propagate the same first `GraphError` as the reference loop. Do not skip invalid records or invent partial success. No per-item `changed` vector is promised by a constructor. |
| Determinism | Preserve explicit node order, implicit endpoint first-seen order, and first-seen unique-edge order. Never let hash-map iteration choose the spanning forest or error. |
| Subsequent operations | Existing `link`, `cut`, `connected`, growth and limits must behave identically, including return booleans, error precedence, isolates retained after cuts, and current read-only query semantics. |

Example error-order tests include a node list exceeding its limit before any
edge, and an edge-limit failure before a later self-loop. Counting the final
union of nodes/edges before deciding an error is not generally equivalent.

### Capacity, allocation failure, and resource guarantees

`Result<_, GraphError>` covers graph validation, **not a recoverable-OOM
guarantee**. Existing graph collections use infallible allocations; B-tree
insertions in particular have no fallible reservation counterpart here.
The initial constructor should retain that policy and explicitly document
possible allocation failure/abort and capacity-overflow panic. Do not claim
that using `try_reserve` on some vectors makes the whole constructor fallible
for memory exhaustion. If recoverable OOM is required, stop and design that
contract separately rather than silently mapping it to a graph error.

Reservation must use checked arithmetic for token counts, degree totals and
byte estimates. No wrapping, truncation, unchecked index narrowing, or reserving
`2*M` tokens. Existing `Index` encoding and actual vector representability
bounds still apply. Any unrepresentable capacity must fail explicitly, not
return a partially initialized graph.

Cardinality limits are not RAM budgets: input slices, hash-table slack, B-tree
overhead and temporary buffers also consume memory. Do not reserve directly
from `max_nodes`, `max_edges`, or raw duplicate-heavy input lengths.

For the first implementation, a practical bounded policy is:

- Normalize the explicit node list in first-seen order, checking its node
  ceiling as it is read; reuse that mapping as the final backend ID map.
  Materialize graph records only after their count `V0` is known.
- Reserve outer vertex structures for V0. The temporary mapping may itself
  grow normally; this does not promise zero ID-map reallocations.
- Use an initial edge capacity hint `min(M, V0, max_edges if set)`, not M.
  For ETT/HDT, the requested initial token reservation is bounded by
  `V0 + 2 * min(edge_hint, V0.saturating_sub(1))`.
  This covers a pre-registered spanning tree while bounding initial slack
  by O(V0), even with repeated copies of one edge. Actual collection capacity
  and allocator rounding must still be measured.
- Empty node input is valid: use normal growth for edge-created vertices.
  Unknown future endpoints must never be rejected to make reservation easier.
- BFS inner degree reservation is deferred until accepted degrees are known;
  it is not guessed uniformly. HDT upper levels and free lists remain lazy.

This node-staging phase temporarily owns an ID map without materialized vertex
records; no query/link can access the backend until one record per index has
been created. Avoid a publicly usable half-constructed graph. Keeping the
mapping in a local build variable and moving it into the completed backend is
preferable to weakening invariants of ordinary mutation methods.

### Equivalence boundary

Required equivalence is graph membership, undirected edges, connectivity,
operation results/errors, limits, and safe continuation under arbitrary
subsequent operations. A/B should additionally preserve initial spanning-edge
selection; the initial insertion-only ETT/HDT work counters are zero.

Exact allocation counts, capacities, addresses, hash-table arrangement,
`Debug` formatting and operation latency are not guaranteed equal. The public
raw ETT/HDT diagnostic APIs make a further distinction important: a direct
builder's different tour shape or replacement order may change future
`ForestStats` / `HdtStats` and storage snapshots while connectivity remains
correct. Do not promise bit-identical diagnostic histories for C. For A, use
matching structural histories as an additional regression gate.

Initial graph construction is not snapshot restoration: HDT levels/promotions,
historical statistics, reserved capacities and service revision numbers cannot
be reconstructed just from a node/edge list. This API promises none of those.

## 5. Correctness invariants and validation

### Representation invariants

1. **All backends:** one stable local index per ID, exactly one matching vertex
   record, unique undirected edges, symmetric adjacency/incidences, correct
   node/edge counts; no unvalidated endpoint index is used.
2. **BFS:** every neighbor list is sorted, duplicate-free and in range; total
   adjacency length equals 2E. The ordinary binary-search `link`/`cut` remains
   valid after publication.
3. **ETT:** each connected component has one spanning tree; every tree edge
   has two valid tour tokens and every non-tree edge is in both endpoint sets.
   Permanent tokens map to the correct vertices. Parent pointers, AVL
   balance, heights, sizes, vertex counts and candidate ORs are consistent.
   Free/occupied token sets are disjoint and exhaustive.
4. **HDT:** all initial edges have level zero; tree edges have one valid F_0
   handle pair and non-tree edges none. Exact-level incidence sets and mark
   bits agree. F_0 spans graph components; higher levels have no materialized
   vertices/edges initially. Subsequent F_i size, nesting, sparse-ID and
   promotion invariants remain those of the existing implementation.
5. **Build lifecycle:** no partial object escapes; no persistent union-find or
   construction-only cache can bypass a later cut.

Reuse [AVL validation](../../../knotrel/crates/knotrel-core/src/index.rs#L401),
[ETT classification checks](../../../knotrel/crates/knotrel-core/src/dynamic.rs#L186)
and [HDT level validation](../../../knotrel/crates/knotrel-core/src/hdt.rs#L448)
in test-only paths. They must run after build and after mutations, not inside
performance timers.

### Differential tests

For each EngineConfig, construct one graph with the reference ordered loop and
one through bulk. Compare with an independent adjacency-matrix transitive
closure for small graphs and `ReferenceGraph` histories. Test:

- Empty graph, singleton, isolated vertices, multiple components, two equal
  components and an empty explicit node list with edge-only endpoints.
- Repeated vertices, repeated/reversed edges, unsorted IDs/edges, `0`,
  `u64::MAX`, sparse high-bit IDs, self-loops, and unknown query endpoints.
- Every small simple graph up to five vertices in selected insertion orders;
  deterministic larger random sequences, including duplicate-heavy inputs.
- Limits None/zero/exactly full/one short; error ordering across the node/edge
  boundary and between edges; duplicates at capacity; implicit endpoints that
  must not survive a rejected edge in the sequential oracle.
- Capacity arithmetic helpers at representability boundaries without attempting
  enormous allocations. Empty inputs must not underflow V-1.

After initialization, feed both graphs identical histories: new vertices,
duplicate links, missing cuts, all-edge deletion, bridge split/rejoin, non-tree
deletion, cycle replacement, repeated promotion/cut and token reuse. Compare
each operation's result, counts and all-pairs reachability on small cases.
Exercise HDT growth across powers of two and sparse upper levels after
promotions. Reuse BFS workspaces across the old/new graphs in raw BFS tests
without sharing mutable scratch across concurrent queries.

Existing starting points:

- [core connectivity tests](../../../knotrel/crates/knotrel-core/tests/connectivity.rs),
  [forest tests](../../../knotrel/crates/knotrel-core/tests/forest.rs),
  [HDT tests](../../../knotrel/crates/knotrel-core/tests/hdt.rs),
  [limits tests](../../../knotrel/crates/knotrel-core/tests/limits.rs).
- [engine differential tests](../../crates/knotrel-benchmarks/tests/engines.rs),
  [dense oracle tests](../../crates/knotrel-benchmarks/tests/dense_workloads.rs),
  [workload tests](../../crates/knotrel-benchmarks/tests/workload.rs),
  and [import tests](../../crates/knotrel-benchmarks/tests/import.rs).

Tests of invalid bulk input compare the error with the sequential oracle;
the oracle's partial prefix is intentionally not returned by bulk. Successful
construction must subsequently pass the full existing core test/doctest,
Clippy, formatting and warning-denied Rustdoc gates.

## 6. Focused measurement design

**Future protocol only:** do not run this matrix as part of this design review.
Reuse existing workload generation, deterministic IDs/seeds, source/binary
hash capture and external RSS collection from
[run_baseline.py](../../scripts/run_baseline.py). Follow the
[before/after policy](2026-10-04-before-after-policy.md).

### Timing and accounting boundaries

Retain the existing `setup_ns` field and meaning in old reports. A new versioned
initialization report should expose:

| Metric | Boundary / limitation |
| --- | --- |
| Input preparation | File decode, trace generation, node-list creation and adapter validation, separately from core construction. |
| Vertex registration | Mapping/duplicate/limit checks, normalization and materializing vertex records; include any work shifted to the prepass. |
| Initial edge insertion | The complete edge phase, including validation, deduplication, endpoint registration and structural work where interleaved. |
| Forest classification/materialization | Separate in B/C where real phase boundaries exist. In A it is nested inside edge insertion: use a separately instrumented build and structural counts, not invented independent wall intervals. BFS reports not-applicable, not a fictitious zero-cost spanning-forest phase. |
| Total core initialization | Entry to the public constructor until a ready graph returns, including normalization, reservations, and disposal of temporary build buffers. For incremental baseline use exactly the reference loop. |
| Ready-graph memory / peak | Report allocated-capacity accounting separately from a fresh build-only child process's peak RSS. Keep the ready graph alive until measurement completes. |
| Dynamic continuation | Identical query/update replay after both constructions, with setup excluded; include the first queries/cuts as well as a longer continuation. |

Do not sum a nested forest time with its enclosing edge time. Main elapsed-time
comparisons use uninstrumented release builds; counts/timers inside AVL/hash
operations belong to separate diagnostic runs and are not performance results.
If instrumentation cannot measure a subphase reliably, report it unavailable.

Build-only child processes avoid contamination by later HDT promotions, but
their RSS still includes input, runtime, and allocator overhead. For warmed
processes, peak RSS also includes the discarded warmup graph. Report fresh
construction peaks separately; do not subtract unrelated high-water marks to
claim exact engine heap. `HdtGraph::storage_stats` is useful after construction
but explicitly omits allocator/hash-table overhead.

Avoid an accidental facade/raw-backend comparison: compare bulk
`ConnectivityGraph` with incremental `ConnectivityGraph` under the same
EngineConfig and limits. Preserve existing raw-engine adapters. A focused
initialization mode can reuse the Workload operations with the facade for both
arms; it does not need a new public backend trait or changed historical
EngineKind identities. Keep raw-type structural tests separate if the facade
does not expose diagnostic counters.

### Topologies, scale, and order

| Family | Planned scales | Purpose |
| --- | --- | --- |
| Path / sparse tree | 1,024; 10,000; 100,000; 1M only after memory preflight | V-only registration versus T near V; no non-tree sets. |
| Cyclic blocks / cycle | Same sparse scales | Separate spanning links from non-tree incidence creation. |
| Two cliques with one/two bridges | 128; 512; larger only with explicit budget | E much greater than V; ordered-set and duplicate-classification pressure. |
| Disconnected forest/cyclic components with isolates | 1,024; 100,000, plus small correctness fixtures | Correct C, T, empty components and capacity slack. |
| High-degree hub | 1,024; 10,000 | BFS insertion shifts; contrast naturally sorted and fixed-seed shuffled edges. |
| Existing Cogentco import | Existing 197-vertex artifact | Small imported control; not a general real-world performance claim. |

Existing `components-join-split-v1`, sustained path/blocks, hub, dense bridge
generators and the pinned import cover much of this. Add only benchmark-owned
disconnected/isolate fixtures and deterministic edge permutations where needed.
Do not alter a versioned workload's existing sequence. Capture the ordered
initial edge list as well as the dynamic suffix in the trace hash.

Duplicate and edge-only-endpoint cases are additional correctness/resource
controls. They must not be omitted merely because the historical harness
assumes pre-registered unique vertices.

### Statistical and acceptance discipline

- Start with four selected cells for **one backend**, not the full Cartesian
  matrix: e.g. 100k path, 100k blocks, 512 clique bridge, and a disconnected
  control for ETT. Six fixed adjacent pairs (three AB/three BA) per cell are
  a screening budget, not proof of a small gain.
- Separate fresh process/no warmup from one complete discarded warmup build;
  never carry the same graph into a measured build. Warmup does not guarantee
  cache or frequency state. Construction-only warmup and the historical full
  replay warmup are different protocols and must be labelled.
- Use one release binary with explicit baseline/treatment selection for
  constructor-only changes, balanced process order, fixed inputs, no concurrent
  workloads, and recorded compiler/flags/allocator/hardware. When shared
  incremental `link` changes, also compare frozen-before and candidate binaries
  to detect dynamic API regressions hidden by a same-binary control.
- For total setup and each valid phase, retain per-pair
  `100*(bulk/incremental - 1)`, medians, ranges/IQR and all adverse pairs.
  If a screen merits confirmation, predeclare 12 pairs on the selected cells
  and paired bootstrap intervals. No pooling of internal repetitions or
  operation percentiles as independent samples.
- **Proposed engineering gate, not a speed prediction:** at least 5% median
  total-core-setup reduction on the preselected target and a paired 95% CI
  below zero in confirmation; no confirmed greater-than-5% dynamic slowdown
  or greater-than-10% fresh build-only peak-RSS increase in controls.
  A wide interval is inconclusive, not proof of no regression. Investigate
  smaller consistent regressions too; do not hide them behind the threshold.
- All semantic/invariant tests must pass. A failure, timeout, excessive memory
  or unfavorable sample is retained without replacement. Expansion to 1M or
  another backend is gated, not automatic.

This proposal does not estimate a wall-time percentage. The mechanically
expected savings for A are fewer endpoint-map probes and fewer vector growth
events; the fraction of total initialization they represent is still unknown.

## 7. Recommended implementation sequence

### Phase 0: establish the attributable baseline

Add focused initialization reporting using the existing harness conventions;
do not introduce new profiler traces. Split node/adapter preparation from
vertex/edge work and compare default versus configured-limit construction.
Use a small fixed source-level diagnostic to count root/rank steps, structural
links, candidate-refresh changes versus no-ops, and collection growth events.
No timing claim may be based on that instrumented executable.

**Exit:** reproducible phase boundaries and input equivalence. If the temporary
adapter map explains most of the opportunity, treat adapter cleanup as a
separate harness change and leave production algorithms alone.

### Phase 1: order-preserving construction (recommended first code change)

Implement the minimal facade constructor and private node/index insertion
helpers. Use first-seen explicit-node normalization with bounded reservations
as specified above, then replay edges in order through the same primitive
used by incremental `link`. Keep implicit endpoint growth, duplicate tests,
AVL linking, incidence updates, and all dynamic algorithms unchanged.

First evaluate the constructor on ETT's sparse controls; correctness must work
for all three facade variants. Avoid bundling BFS adjacency sorting,
union-find, deferred aggregate repair, HTTP loading, or direct tree building.
Do not expose a supposedly fast unchecked public API.

**Exit:** exact ordered-loop error/result equivalence, invariant tests and
dynamic continuations pass; measurements meet the predeclared gate. For
pre-registered edges, the source-level aim is to replace registration-plus-ID
relookup with one local-index resolution per endpoint. Compiler effects and
time savings must be measured, not asserted from the helper count.

If this fails to improve total setup, do not add more knobs to make it look
successful. Retain or reject the convenience API on its own merits, record
the negative performance result, and choose Phase 2 only from measured costs.

### Phase 2: one backend-specific improvement at a time

- BFS append/sort construction only if unordered adjacency shifts or inner
  growth are significant; verify sorted-input controls do not regress.
- ETT/HDT input-order union-find classification only if repeated classification
  root walks matter; retain existing forest and incidence primitives.
- If sparse ETT time is mostly T tour links, skip speculative library swaps
  and separately evaluate whether Phase 3's larger correctness cost is worth it.

**Exit:** each change independently meets correctness, memory, setup and dynamic
continuation gates. Do not ascribe one backend's result to the others.

### Phase 3: direct tour construction, only with a demonstrated need

Prototype a tested linear tour/AVL materializer for the already chosen
spanning forest, first ETT and only then HDT's F_0. Require arc/tour and
post-cut/promotion invariants, not just matching initial connected answers.
No eager higher levels or changes to online algorithms.

**Exit:** material reduction in total construction justifies temporary memory
and maintenance complexity; post-build dynamic behavior is measured and any
diagnostic-history differences are explicitly accepted.

## 8. Alternatives not selected and open decisions

Not selected now:

- **A new high-performance library:** none removes the semantic need to
  register IDs, classify edges and maintain tours. Existing safe collections
  suffice for the first experiment.
- **DSU as the persistent backend:** it cannot support arbitrary deletions;
  at most it is ephemeral build scratch.
- **Bulk sorting of all edges by default:** it can alter spanning-edge
  selection and first-error order. BFS neighbor sorting after acceptance is
  different from reordering public input operations.
- **A universal eager graph representation / CSR replacement:** adds staging
  cost or changes mutation characteristics across backends. Keep final dynamic
  representations unchanged.
- **In-place transactional batches, parallel loading, live engine switching:**
  introduce rollback, synchronization or publication questions beyond atomic
  owned construction.
- **Direct ETT/HDT materialization first:** mathematically promising for sparse
  forests, but current data does not isolate its cost enough to justify its
  much larger invariant surface.

Measurements/decisions needed before coding:

1. Is the first consumer the embedded facade, startup import, or raw Graph plus
   BfsWorkspace? This proposal targets the facade; a raw convenience API should
   be added only for a concrete caller, not by default.
2. What fraction of representative loading uses pre-registered nodes versus
   edge-only discovery? The bounded reservation plan intentionally provides
   less benefit in the latter case.
3. How much setup is adapter validation, mapping, vector growth, AVL linking,
   classification, or incidence maintenance? Existing aggregate setup cannot
   answer this.
4. Does the consumer require recoverable allocation failure or a hard memory
   budget? Neither is offered by current GraphError/GraphLimits. Do not imply
   either with a fallible constructor.
5. Would a later direct builder's different diagnostic history be acceptable?
   Connectivity equivalence alone does not promise identical scan counts or
   HDT promotion history.

**Final recommendation:** implement A first, behind the proposed owned
constructor, with attributable setup measurements and a fixed acceptance gate.
It is the smallest design that can reduce known repeated work without changing
the graph algorithm, edge order or dynamic semantics. Expect fewer lookup and
growth operations, **not a promised wall-time speedup or new asymptotic bound**.
The recommendation is invalidated as a performance priority if measurements
show those costs are minor, normalization/slack outweighs the savings, or
subsequent updates regress. In that case use the evidence to choose a specific
B/C construction change, rather than accumulating speculative optimizations.
