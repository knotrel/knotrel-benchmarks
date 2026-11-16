# D4 — memory bounds diagnostic on the exact candidate (frozen before execution)

Authorized by the owner (minimum verification of the evidence audit). Diagnostic
only: no historical C3 verdict changes, and no plateau found here turns a FAIL
into a PASS.

## Identity

- Candidate: knotrel `a1d95778f8c876c49efd09dcddcdf6fbdd8259fe` (clean, detached
  for the build; `754ddbc` adds only test and documentation changes).
- D4a/c/d tool: `tools/lifecycle-probes/target-peak/release/memory-peak`, probes
  `00bd886e` clean, sha256 `451702f2deccc8270aefd804acfe57184d6e4cc31a1473127d2d8635f94d3a6a`,
  build record names knotrel `a1d9577` clean. Allocator `cap 0.1.2` (`stats`):
  live requested heap and its running maximum; reallocations at their
  resulting size; allocator-internal copies and metadata excluded; the
  maximum cannot be reset (a peak is exact only when the mark rises in the
  interval, otherwise it is bounded by the earlier mark).
- D4b tool: the amendment-2 count-alloc binary
  `tools/lifecycle-probes/target-count/release/core-lifecycle`, sha256
  `53497c21efe4d0ea225e703a78623a2896ea8c7222342619ca3ff1d6410f4565`
  (knotrel `a1d9577`, probes `444806d3`, both clean).

## Runs (fixed; no extension)

- **D4a churn peaks** (`memory-peak churn`, lifecycle arm, 30 cycles, 5%,
  seed 5000001, checkpoint after construction and every cycle): engines
  `compact-bfs`, `ett`, `hdt` × `fresh`, `same`, `toggle`, topology `sparse`,
  100,000 nodes (9 runs). Recorded per checkpoint: live heap, peak mark and
  whether it rose in the cycle, RSS, logical and expected counts, engine and
  retired slots, catalog and incident capacities, compaction in the cycle.
  Validity: logical counts equal the expected counts and equal run 3's
  `C-heap-lifecycle-*` checkpoints at every cycle.
- **D4b plateau check** (`core-lifecycle resources --cycles 120`): the 17 D2
  cells with D2's argv and D2's frozen rule (PLATEAU / BOUNDED_SAWTOOTH /
  GROWING), now on the exact candidate with clean tooling.
- **D4c HDT levels** (`memory-peak hdt-levels`, 120 cycles, sample every 10):
  `sparse` and `ring`, 100,000 nodes, `same` and `toggle` (4 runs). The
  effective-graph changes of the D4a schedule applied to `HdtGraph`; per-level
  record slots, tree edges, incidences and capacities; the run fails if the
  engine edge count diverges from the model.
- **D4d import peaks**: `memory-peak import-core` and `import-http --mode
  create`: `compact-bfs` sparse 100,000 with 20/10 and 60/30 flags, `ett` and
  `hdt` sparse 10,000 with 20/10; `import-http --mode replace`: `compact-bfs`
  sparse 100,000 20/10 (10 runs). Each run is its own process.

## Host and budget

AC power; one process at a time; no other agent command during the collection
(one chained command; the only monitoring is its completion). At most 100,000
nodes and 120 cycles. Measured-time cap for D4: 15 minutes; the chain stops
when the cap is reached and the remaining runs are reported as not run.

## Reporting

Separate: (1) bounds that follow from code invariants; (2) observed maxima;
(3) retained capacities; (4) unbounded or unguaranteed quantities (RSS,
allocator retention). Output: `evidence/v0.5.0-remediation/D4/`.
