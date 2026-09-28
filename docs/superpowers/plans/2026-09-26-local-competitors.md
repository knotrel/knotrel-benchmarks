# Local competitor comparison

The user approved identifying direct alternatives before optimizing Knotrel.
Implement directly in the existing dirty checkout; preserve all previous changes.
No commits or pushes. GraphScope work remains deferred.

## Design

Compare four synchronous in-process implementations with the same versioned
trace: existing Knotrel BFS, an experimental compact-index BFS, petgraph DFS,
and outils HDT. Use a single binary and fixed vertex universe for the comparison;
report that pre-registration is narrower than Knotrel's growing-node API. All
adapters accept full u64 IDs and retain simple undirected/idempotent semantics.
Charge ID translation, edge-handle lookup and query workspace reset to operations.
Do not adopt a third-party engine into knotrel-core in this experimental step.

Keep default benchmark CLI compatible. Add --engine, and --engine all for the
same-process comparison, rotating engine order across process trials in the
collection script. Preserve original traces; optional extra immediate query
repeats are reported separately and identified as workload augmentation.
Retain raw first-query versus repeated-query and true/false distributions.
Include setup costs and per-run process memory only if measured with clear scope.
Do not call fresh processes hardware-cache cold or remove valid maintained state.

## Tasks

- [x] Record primary-source scope, releases, licenses and maintenance evidence.
- [x] Add locked benchmark-only dependencies and test adapters against independent
      transitive closure, including repeated queries, redundant updates, cycles,
      bridges, isolated/full-width IDs and invalid/unknown endpoints.
- [x] Add common runner and cache-aware comparisons while preserving default output.
- [x] Run release matrix with multiple process trials and rotated engine order.
- [x] Document results, semantic gaps and a concrete next optimization decision;
      run required checks and independent review.
