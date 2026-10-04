# Topology Zoo adapter integration smoke — 2026-10-03

Purpose: validate acquisition, normalization, imported replay and all scheduled
answers on a small real topology. **Not a performance ranking or scale study.**
The preserved [raw report](replay.json) contains timer samples for auditability;
these are too few and the graph is too small for comparative conclusions.

## Which implementations are Knotrel?

This run compares **three Knotrel implementations and one external baseline**.
It measures embedded kernel calls, not the Knotrel HTTP server or a deployed service.

| CLI selector | Ownership and role | Exact report identity |
| --- | --- | --- |
| `compact-bfs` | **Knotrel**, current default core backend | `knotrel-core/compact-bfs-v1` |
| `ett-scan` | **Knotrel**, experimental Euler-tour backend | `knotrel-core/ett-pruned-v2` |
| `hdt` | **Knotrel**, experimental HDT backend | `knotrel-core/hdt-sparse-levels-v3` |
| `petgraph-dfs` | **External**, petgraph 0.8.3 DFS through our benchmark adapter | `petgraph-0.8.3/dfs` |

ETT and HDT are algorithm families, not separate competing products in this run.
The offline union-find/BFS oracles validate answers; they are not timed competitors.
Abilene was chosen to inspect importer behavior cheaply, not because 11 vertices
represent a demanding application. Keep this as a regression test, not as evidence
that Knotrel scales or outperforms another implementation.

## Interpretation boundaries

Passing every query means no discrepancy on this trace, not universal correctness
or proof that stale answers cannot occur. Near-zero timer samples do not mean
zero-cost operations, and these samples cannot establish a twofold speedup.
Cache residency and timer resolution were not independently characterized here.
The adapter preserves IDs, isolates and link multiplicity; it does not import
arbitrary GraphML attributes into the connectivity engine. No claim about a
specific mutation complexity follows from these timings.

Input: Abilene GraphML at the immutable Topology Zoo revision and SHA-256 recorded
in [manifest.json](manifest.json). Source/license links, attribution and complete
reproduction commands are in the [adapter guide](../../docs/scenarios/topology-zoo.md).
The topology is archival; the outage sequence is our synthetic experiment.
No raw third-party dataset or full trace is committed. Recreate the trace with
the guide and compare its SHA-256 with the manifest before replay.

| Check | Observed |
| --- | --- |
| Registered vertices / initial simple edges | 11 / 14 |
| Initial components / projected bridges | 1 / 0 |
| Source failure and repair batches | 20 |
| Effective cuts / links | 10 / 10 |
| Scheduled queries / true / false | 180 / 103 / 77 |
| Engines | compact-bfs, ett-scan, hdt, petgraph-dfs |
| Warmups / measured fresh-graph replays per engine | 1 / 3 |
| Immediate additional repeats per query | 2 (360 per measured replay) |
| Correctness | All scheduled and repeated queries passed on every replay |

The source-link union-find oracle and independent Rust BFS validation run outside
kernel timing. The Rust validator checks all 180 imported answers once before
warmup. Fresh graphs do not imply cold allocator, filesystem or hardware caches;
those are uncontrolled. Engine order was fixed for this integration check.
A comparative experiment must rotate order and separately analyze fixed-only
and varied-pair traces, repeats, tails and larger topologies. No RSS measurement
or end-to-end preprocessing timing was performed here.

The report records runtime checkout revisions/dirty state. The manifest also
records source-file hashes (including the new uncommitted implementation), input
and output checksums, compiler information via the raw report, and host details.
Source hashes are audit aids, not a binary attestation. Cargo.lock was unchanged.

Validation accompanying the implementation: 31 Rust tests, 4 Python tests,
formatting, Clippy and Rustdoc with warnings denied. Fixtures include parallel
links, a cycle, a bridge, an isolate, all-pairs checks, malformed imports and
byte-exact re-export under changed sampling options.
