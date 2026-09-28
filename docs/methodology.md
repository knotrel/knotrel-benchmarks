# Benchmark methodology

## Deterministic trace contract

The preserved ordered `ReferenceGraph` remains the reference backend. `chain-split-rejoin-v1` preserves
its original initial edges and operation sequence for a given nodes/rounds/seed.
`generate(kind, config)` returns initial edges and an ordered operation vector,
independent of the measured backend. Initialize **all** vertices `0..nodes`
before loading the undirected edges. Every link and cut in these traces must
return `changed = true`; queries carry topology-derived expected booleans.

`--trace-out NEW_PATH` writes compact JSON (trace schema 1) before warmup. It
refuses to overwrite existing files. The envelope contains workload, config,
initial edges and operations (`op`, `source`, `target`, and query `expected`).
Integers are JSON numbers: consumers must parse u64 losslessly, especially seed;
this is a benchmark interchange format, not the string-ID HTTP protocol.
Future adapters can read these files or use the Rust generator; the current CLI
only generates traces, and does not import arbitrary external trace files.

The report contains FNV-1a-64 of the exact compact export bytes (including config
and expected answers), starting at 0xcbf29ce484222325 and multiplying by
0x100000001b3 modulo 2^64 after XOR with each byte. This is a stable diagnostic
fingerprint, **not** a collision-resistant proof. The baseline manifest also
records SHA-256 checksums of saved files. Trace identities do not depend on
warmup, repetition count or timings. Selection uses the original wrapping LCG;
modulo selection is biased and is not a statistical sampling guarantee.

## Workload families

Let n = vertices, r = rounds and d = the selected leaf's original degree.
The four historical base traces are sparse, undirected, simple and have 50% queries. Every round
restores the initial graph. Density at any point is 2m/(n(n-1)); reports include
initial density, edge count and maximum degree. Operation counts in each
repetition make the actual update/query ratio observable.

| Versioned name | Initial topology and edge range | Operations per round | What it exercises |
| --- | --- | --- | --- |
| `chain-split-rejoin-v1` | Path; m ranges n-2 to n-1; max degree 2 (1 at n=2) | 1 cut, 1 link, 2 queries | Cut a seeded bridge; query endpoints false then true. Only bridges. |
| `cycle-alternatives-v1` | Ring; m ranges n-2 to n; max degree 2 | 2 cuts, 2 links, 4 queries | Remove both edges at a seeded vertex. First cut has an alternative path; second isolates it. Queries to the opposite vertex: true, false, true, true. |
| `components-join-split-v1` | Two paths of floor(n/2) and ceil(n/2); m ranges n-2 to n-1; initial max degree 2 | 1 link, 1 cut, 2 queries | Seeded cross-component bridge joins then splits the paths. Query 0 to n-1: true then false. |
| `hub-alternatives-v1` | Star plus a path through leaves; initial m=2n-3; minimum m=2n-3-d; initial max degree n-1 | d cuts, d links, 2d queries; d=2 at leaf-path endpoints, otherwise 3 | Cut spoke first, then remaining incident edges to isolate a seeded leaf; restore in reverse. Query hub to leaf after each mutation. One false query per round traverses the large source component. |

Chain needs n>=2, others n>=6; all require r>=1. Only chain accepts n=2.
The hub is deliberately degree-skewed, **not** a fitted power-law distribution.
Cycle and hub exercise alternate paths but do not guarantee which deleted edge
is a maintained tree edge in a future backend; each backend should instrument
replacement searches separately. These families do not establish performance
on dense graphs, long-lived randomized churn, different query/update ratios,
real datasets, concurrent traffic or worst-case adversarial sequences.

## Correctness

Expected answers are constructed from topology, never read from the timed
backend. All updates change state and every query is checked outside its timer.
Integration tests replay all four families for n=6,7,12 with seeds 0,42,u64::MAX,
checking each mutation and query against a separate adjacency matrix and
Floyd-Warshall transitive closure. This O(n^3)-time, O(n^2)-space oracle is test-only;
it independently validates the generator, while the runtime checks the engine.
Determinism, changed seeds, invalid/overflowing sizes, stable export, overwrite
protection and CLI sampling counts have separate tests.

## Timing, warmup and repetitions

Defaults: one complete warmup replay and one measured repetition. Use
`--warmup 0` for no warmup; `--repetitions N` requires N>=1. Each replay builds a
fresh graph from the same trace. Warmups execute the same checks and timers and
discard their summaries. They warm process/allocator caches; they do not promise
steady-state CPU frequency or warm state inside the next graph instance.

Trace generation, export, initial graph construction and timing-buffer
allocation are excluded from operation and workload wall intervals. Each
operation interval includes the synchronous backend call, a compiler barrier and
clock overhead. Validation and sample insertion happen afterward. Wall time
also includes dispatch, checking and sample storage, but excludes final sorting
and graph destruction. It is not end-to-end service throughput. Each repetition
records `setup_ns` separately for vertex registration, backend construction and
initial edge loading; it is excluded from operation and workload wall intervals.

Report schema 2 replaces schema 1's single `measurements`/`workload_wall_ns` with
an ordered `repetitions` array. Each repetition retains separate cut/link/query
min, p50, p95, p99, max, count and total nanoseconds. Percentiles use nearest rank
ceil(p*n/100); samples are sorted after timing. Report all repetitions and their
variability; do not pool per-run percentiles or select the fastest run. No timer
overhead subtraction is applied. Very short updates can be timer dominated.

The harness retains O(n+r) trace storage and O(r) sample storage per replay;
report storage is O(repetitions). Export temporarily adds an O(n+r) JSON buffer.
There is no RSS measurement, memory budget estimator or engine-only allocation
accounting. Very large inputs can exhaust memory despite checked trace allocation.

## Reproducing the recorded local baseline

```sh
python3 scripts/run_baseline.py results/NEW_RUN_DIRECTORY
```

The standard-library-only script builds release with `--locked`, then runs all
four families sequentially at n=128,1024,4096, r=200, seed=42, one warmup and three
measured repetitions. One process handles each workload/size pair. It preserves
raw JSON, exported traces, source hashes, both revisions and dirty states,
tracked diffs, untracked Rust files, compiler, OS, CPU, RAM, build environment,
commands and executable checksum. It rejects changed source inputs during runs.
Use a new output directory. The script takes the executable path from Cargo build output, including custom
target directories, and requires the sibling checkout layout.

These in-process repetitions are not independent process trials. Run the script
again on a quiet machine to study process-level and scheduling variability.
The source manifest covers workspace Rust/build files, manifests, lockfiles,
toolchain and workspace Cargo configuration. It does not attest to every global
Cargo configuration, compiler environment override or external tool. Record
those separately if customized. Runtime Git state alone never attests to compiled
code. See [local results](../results/2026-09-26-macos/README.md).

## Future comparison adapters

Before comparing with GraphScope or another dynamic-connectivity engine:

1. Load identical graphs and replay the exact same exported update/query trace.
2. Match undirected semantics, duplicate handling and vertex lifetime.
3. Require every answer to see all preceding updates, including synchronization
   or waiting for incremental maintenance. Stale answers are not exact parity.
4. Validate answers independently before interpreting performance.
5. Distinguish a boolean connectivity query from materializing all component labels.
6. Report loading, update, state maintenance, compaction, synchronization and query
   costs separately, plus total lifecycle cost and memory.
7. Record software versions, workers, threads, hardware and monetary costs.

No validated live HTTP or GraphScope comparison is available. A deferred
GraphScope probe exists but has not been executed against a live engine. GraphScope's incremental
capabilities must be verified in an actual comparable experiment; do not assume
full recomputation. Beating this BFS alone establishes no commercial advantage.

## Embedded comparisons and cache protocol

`--engine` selects `reference-bfs` (default), `compact-bfs`, `dense-bfs`, `petgraph-dfs`,
`outils-hdt`, `all`, or an ordered comma-separated list. Multiple backends return
schema 3 with a `comparisons` array of schema-2 reports sharing one trace.
The `dense-bfs` and petgraph adapters reuse scratch storage but reset traversal
state each query. Outils maintains a connectivity index. The production compact core uses local per-call scratch and supports growing
vertices. All experimental indexed adapters
pre-register a fixed vertex universe; this does not test growing-node API parity.
ID translation and edge-handle bookkeeping are inside operation intervals.

`--query-repeats N` adds N immediate checked calls after each original query.
Their distributions appear separately in `repeated_queries`; original true/false
queries also have separate summaries. Repeats affect later cache state, so base
operation totals from these runs are not a separate unaugmented experiment.
With N repeats the executed query fraction is (N+1)/(N+2), versus 50% in the base
trace. Sample storage becomes O(r*(N+1)).

The collector supports `--process-trials`, `--cache-regimes fresh|warmed|both`,
`--engines`, and `--query-repeats`, as well as sizes/rounds/repetitions. Fresh means
zero deliberate replay warmups; warmed means one. Neither flushes hardware or
OS caches. Cases are shuffled deterministically and backend order rotates across
process trials. Four trials balance the positions of four backends, not every
cache interaction. Reports preserve all repetitions and process identities.
See the [comparison results](../results/2026-09-26-competitors/README.md) and
[adoption-based candidate selection](research/2026-09-26-competitive-landscape.md).

## Sustained scale experiments

`sustained-churn-path-v1` toggles seeded path edges; an ordered set of absent
boundaries answers queries independently. `sustained-churn-blocks-v1` connects
16-vertex cycles with bridges, toggles bridges and removes/restores one internal
cycle edge per selected block. Blocks stay internally connected. The oracle uses
missing bridge boundaries, not a measured engine. State persists across rounds.
Each round is 100 operations and `--query-percent 1..99` gives the exact query
count per round; the remainder are changed updates. A short trace may have no
links, in which case its latency field is null, not zero. Fixed operation counts
mean different numbers of updates and different fragmentation at different ratios.

`ett-scan` measures the opt-in deterministic AVL Euler-tour forest with an
exhaustive smaller-side replacement scan. It is not HDT. Reports include
`forest_stats` only for this backend: tree cuts, enumerated vertices, examined
non-tree incidences and replacements. Counters reset after setup and include
measured mutation work. Queries allocate no scratch; maintained connectivity is
valid state, not a cache to disable. The compact default remains unchanged.

`run_scale.py` runs one engine per fresh process, deterministically shuffling
cases. `fresh`/`warmed` remain replay policies, not CPU-cache states. The platform
time tool records whole-process peak RSS including generation, trace JSON export,
harness buffers, engine and any warmup. This cannot be called engine heap usage.
The collector normalizes macOS bytes / Linux KiB, saves stderr and commands, and
kills the entire measurement process group on timeout. Failed cases remain in
partial metadata and are not silently dropped. `summarize_scale.py` preserves one
row per process, including null operation categories and replacement counters.

## Candidate-pruned forest version

`ett-scan` now reports `knotrel-core/ett-pruned-v2`. A frozen benchmark-only copy
of the previous implementation is selectable as `ett-scan-v1`, preserving its
`knotrel-core/ett-scan-v1` identity and original token representation. Both run in
the same executable with the same adapter registration and timing boundaries.
Historical reports continue to identify v1, not the current ForestGraph.

For v1, `scanned_vertices` counts all vertices eagerly enumerated before checking
edges. For v2 it counts candidate-bearing vertices yielded before success or
exhaustion. It does not count AVL tokens traversed or ancestor repairs, so counter
ratios are not runtime speedups. The other replacement counters keep their
semantics. Pruning preserves the relative enumeration order of candidate vertices.
The `all` selector now contains seven backends; explicit lists preserve old suites.


## Dense bridge churn workloads

`dense-bridge-churn-v1` and `redundant-bridge-churn-v1` split n>=4 vertices
into fixed cliques of floor(n/2) and ceil(n/2) vertices. Internal edges load
before cross-clique edges. The first family starts with one bridge `(0, n/2)`;
the second starts with that bridge and `(1, n/2+1)`. Every update toggles one
bridge, selected by the seeded generator, and changes graph state. The redundant
family tracks its two bridges independently. State persists across rounds,
including when an odd update count leaves a bridge absent at a round boundary.

Each round contains exactly 100 operations with `--query-percent 1..99` queries
(default 50), using the sustained families' operation scheduling. Queries select
seeded random vertex pairs. Their topology oracle answers true exactly when the
vertices share a clique or at least one bridge remains. Small odd/even fixtures
with several seeds and ratios are validated by independent transitive closure.
The sparse and historical versioned traces retain their generation contracts.

With a=floor(n/2) and b=ceil(n/2), initial edge count is
`a*(a-1)/2 + b*(b-1)/2 + bridges`. These are explicitly synthetic **dense** stress
cases: generation and retained trace storage take O(n² + operations), with
checked edge/operation arithmetic and fallible vector reservations. Export and
backend setup also retain or process quadratic edge data. Large sparse-workload
node counts are unsuitable defaults here. The single-bridge family targets
repeated failed replacement searches; the second also exercises redundant
cross-clique connectivity. This is workload intent, not a performance result or
a guarantee about a backend's selected forest. The cases do not model production
distributions, and generation/setup are outside timed operation intervals.


### Knotrel HDT diagnostics

`hdt` records `knotrel-core/hdt-sparse-levels-v3`, a growing-node HDT implementation with
separate exact-level tree/non-tree aggregates. Each report's optional `hdt_stats`
contains tree_cuts, candidate_edges, replacements, tree_promotions,
non_tree_promotions and levels_visited. Setup counters are reset before replay.
The scale CSV prefixes these with `hdt_`; ETT fields stay unchanged, and absent
backend-specific counters remain empty. Optional diagnostics extend schema 2
without changing the trace format or old workload fingerprints. Interpret each
counter by its algorithm; equal values are not required between ETT and HDT.

Sparse HDT v3 materializes only touched upper-level vertices. Frozen `hdt-v2`
preserves the prior algorithm/layout under `knotrel-core/hdt-levels-v2`.
`hdt-profile` is a separate instrumented diagnostic binary; it reports structural
storage after registration, load and replay and groups cuts by promotion-counter
deltas. It must not contribute to normal timing tables. Vector capacities and
live ordered payload exclude B-tree/allocator overhead and are not RSS. See the
[v3 report](../results/2026-09-28-hdt-v3-sparse/README.md) for the measured tradeoff.
