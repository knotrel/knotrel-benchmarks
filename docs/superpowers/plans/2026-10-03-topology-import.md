# Topology import implementation plan

**Goal:** Replay independently validated imported traces and convert one pinned
Topology Zoo GraphML artifact into a deterministic outage experiment.

**Architecture:** Python standard-library GraphML preprocessing; strict versioned
JSON import in the existing Rust runner. Reuse existing engine timing and report
fields; keep generated trace bytes and report schema unchanged. Imported reports
use schema 4 with import metadata instead of generated rounds/config.

**Spec:** [Domain adapter contracts](../../scenarios/README.md).

**Constraints:** Rust 1.98.1; no new dependencies; no core edits; no commits.
Retain existing user documentation edits. Execute inline in the authorized checkout.

## Tasks

- [x] Add CLI tests for import replay, incorrect oracles, invalid mutations,
  invalid endpoints/batches/provenance and incompatible generation flags.
- [x] Add strict import schema and independent untimed BFS validation; expose
  `--trace-in`, preserve imported bytes on optional export, report validation time.
- [x] Add Python fixture tests for parallel links, isolates, directed/nested graphs,
  missing endpoints, checksum mismatch, deterministic queries and no overwrite.
- [x] Implement `scripts/import_topology_zoo.py` with SHA-256 input pin, explicit
  provenance, sorted ID map, seeded LCG/Fisher-Yates outages and reverse repairs.
  Queries comprise a fixed probe and seeded distinct pairs; expected answers
  derive from active source links rather than projected mutation counters.
- [x] Pin and acquire one small real GraphML artifact outside Git; verify license,
  exercise import/replay across compact, ETT, HDT and petgraph, retain provenance.
- [x] Update runnable documentation and run Python tests, Rust tests, fmt, Clippy,
  Rustdoc and diff checks. Review changes and report limits without extrapolation.

## Review focus

- Parallel physical links must not disconnect a still-live pair.
- Queries with false expected answers must be rejected before timed replay.
- Unsupported GraphML semantics must fail rather than silently lose connectivity.
- Isolates and nonnumeric IDs must survive normalization.
- Cache/repetition options must not alter imported bytes or provenance.
