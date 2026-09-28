# Competitive landscape and benchmark priorities

Observed 2026-09-26. Separate **customer alternatives** from **algorithmic
controls**. A library can be a useful performance reference without being a
successful product, and a successful database can serve a different contract.

## Selection

| Priority and role | Candidate | Evidence of adoption / maintenance | Decision |
| --- | --- | --- | --- |
| Primary embedded incumbent | petgraph 0.8.3 | GitHub API: 4,020 stars, 467 forks, pushed 2026-09-20. crates.io reports 111,774,854 recent downloads. | Measure now: common Rust graph representation and path query. This represents an application implementing connectivity itself. |
| Next incremental reference | Differential Dataflow 0.25.1 | 3,013 stars, 211 forks, pushed 2026-09-23; 83,331 recent crate downloads. Materialize documents its use of Timely and Differential Dataflow. | Prioritize a later exact incremental-components adapter with timestamp/frontier synchronization and memory accounting. Not measured here. |
| Relevant product alternative | Memgraph | Vendor-published Volue customer story concerns changing power-grid topology and connected traces; named customer/engineers and deployed workflow. | Investigate for a topology-management use case. First establish equivalent boolean undirected answers; then compare service lifecycle costs. No performance claim yet. |
| Secondary algorithmic control | outils 0.3.0 | 10 stars, 1 fork, last push and published release in October 2020; 54 recent crate downloads. | Measure HDT as a research control. Do not call it an established commercial competitor or adopt it into the core on these results alone. |
| Additional research control | tomtseng/dynamic-connectivity-hdt | 25 stars, no forks, last push 2023-09-14; repository declares MIT. | A C++ implementation to inspect if needed to separate HDT's algorithm from outils' implementation constants. Not measured. |
| Deferred broad platform | GraphScope | Multiple engines/stores, rather than one directly substitutable kernel. Ingress documentation and standalone deployment must be distinguished. | Previous user-directed investigation paused. Prepared Python probe has not been run against a live engine. |

Numbers come from the [saved API snapshot](2026-09-26-adoption-snapshot.json),
not estimates. GitHub stars measure attention, not revenue, support quality,
correctness or production users. Crate downloads include CI and transitive
fetches, not unique adopters; `recent_downloads` is the provider's rolling field.
The last-push timestamp is activity evidence, not a count of substantive commits.
No market-share, customer-count or commercial-success ranking is established.
A small repository can still beat a large project on a narrowly defined algorithm.

## Primary evidence and licensing

- [petgraph repository](https://github.com/petgraph/petgraph) and
  [crate metadata](https://crates.io/api/v1/crates/petgraph): 0.8.3 declares
  `MIT OR Apache-2.0`. This benchmark calls `has_path_connecting` with reusable
  DFS state. It must not be described as BFS or a maintained connectivity index.
- [outils repository](https://github.com/ouaffm/outils),
  [crate metadata](https://crates.io/api/v1/crates/outils) and
  [DynamicGraph documentation](https://docs.rs/outils/0.3.0/outils/graph/dynconn/hdt/struct.DynamicGraph.html):
  0.3.0 declares `MIT/Apache-2.0`; fixed vertex universe and HDT level structure.
  Inspection of the downloaded 0.3.0 source confirms AA-tree Euler forests,
  replacement searches, edge handles, and false reflexive queries. Source search
  found no unsafe blocks in this release; this is not a security or quality audit.
- [Differential Dataflow repository](https://github.com/TimelyDataflow/differential-dataflow)
  declares MIT. [Materialize's architecture account](https://materialize.com/blog/materialize-under-the-hood/)
  provides named product-use evidence, not evidence that any specific DD graph
  program meets Knotrel's desired latency. Component labeling need not enumerate
  all reachable vertex pairs; do not assert unavoidable O(n²) memory.
- [Memgraph's Volue story](https://memgraph.com/customer-stories/how-volue-optimized-power-grid-management-with-memgraph)
  is a vendor case study, not an independent benchmark. It reports topology
  changes, connected traces and operational tooling. It supports investigating
  demand in this domain, not claiming that Knotrel replaces the full workflow.
- [C++ HDT repository](https://github.com/tomtseng/dynamic-connectivity-hdt):
  research implementation with a different integration/toolchain cost.

Only outils and petgraph are new runtime dependencies, confined to the benchmark
workspace and pinned exactly in Cargo.lock. Existing locked versions were
preserved. Knotrel core/server dependencies and licenses are unchanged. No
third-party source is copied into the production core.

## Product hypothesis to validate

Start with **an application maintaining an undirected operational topology**:
edge insertions/removals from an authoritative event stream, followed by exact
pair-connectivity queries. The immediate alternative is an embedded graph library
and a traversal, not necessarily a graph database. If a team already uses a graph
database for storage, attributes and exploration, Knotrel could be a specialized
index alongside it; replacing that database adds scope and migration costs.

This hypothesis still needs a real user/workload: graph size and degree spectrum,
update/query ratio, burst behavior, latency budget, memory budget, and whether
embedded or network access is preferred. No customer interviews were conducted.
For network infrastructure, detecting faults and obtaining accurate topology are
upstream responsibilities. In electrical models, topological connection does not
establish power flow or safe operation. General ReBAC requires relation/policy
semantics beyond undirected connectivity.

## Optimization decision

See the [local comparison](../../results/2026-09-26-competitors/README.md).
Do not optimize merely to beat the original ordered-adjacency BFS. The practical
baseline is petgraph plus traversal and the compact BFS control. Outils isolates
the query/update tradeoff of one HDT implementation; it does not establish the
best achievable HDT performance or justify claiming a market lead.

Next engineering milestone: retain the reference, develop a production-capable
compact representation with the full growing-u64-node contract, and assess a
maintained connectivity index against that stronger baseline. Before choosing
HDT for production, extend to sustained churn, larger graphs, varying query/update
ratios, adversarial replacement searches and measured memory. Add DD when its
adapter can account for convergence after every visible update. A product-level
Memgraph comparison follows a validated customer contract rather than a desired
headline speedup. GraphScope is not the immediate optimization target.

## Subsequent milestones

The compact core is now implemented and the opt-in Euler-tour scan prototype is
measured in the [2026-09-27 scale study](../../results/2026-09-27-forest-scale/README.md).
Petgraph remains the practical external baseline. The forest wins operation-only
query-heavy cases but loses other mixes, costs more to load and needs more memory.
These findings reinforce the distinction between a useful algorithm and an
established product advantage.
