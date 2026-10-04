# Connectivity campaign protocol — 2026-10-04

Goal: identify where Knotrel's maintained connectivity backends improve queries
and where update or memory costs outweigh that benefit. No universal winner is
assumed. This measures embedded kernels, not the HTTP service.

| Selector | Ownership / role |
| --- | --- |
| compact-bfs | Knotrel default |
| ett-scan | Knotrel experimental ETT |
| hdt | Knotrel experimental HDT |
| petgraph-dfs | External petgraph 0.8.3 DFS baseline |

## Prespecified matrix

- Sparse persistent churn: path and cyclic blocks; 1,024, 10,000 and 100,000
  vertices; 10%, 50%, 90% queries; 10 rounds (1,000 base operations); two
  independent processes per cell per regime; zero or one complete warmup.
- Dense controls: two-clique bridge and redundant-bridge churn; 128 and 512
  vertices; same mixes, rounds, trials and regimes.
- Cache sensitivity supplement: sparse 10,000-vertex, 90%-query cells, two
  immediate extra queries per scheduled query; compare separately with the
  zero-repeat matrix. Repeats are not pooled into base-query distributions.
- Real topology: pin a larger Topology Zoo input, preserve physical-link
  multiplicity, run seeded progressive outages and repairs. Rotate four engines
  through all four order positions; record fresh/warmed processes separately.

Synthetic cases use the existing collector's seeded global shuffled execution
order; this is randomized order, not a perfectly balanced Latin square. All
backends in a cell receive the same trace. Seed 42 is fixed, so independent
process trials do not imply independent graph samples. Query/mutation operation
mixes are generated schedules; real-topology query schedules are ours too.

## Evidence and interpretation

Keep per-process samples, p50/p95/p99, counts, setup time and peak whole-process
RSS, commands, source/binary/trace hashes, source patches and failures. RSS includes
harness, traces, temporary export buffers, validation and warmups; it is not
engine-only memory. Operation timing includes timer/barrier costs; wall time also
includes dispatch, assertions and sampling. Do not call inverse p50 throughput.

Summarize each cell's trial range and median separately by regime. Two trials
are exploratory evidence, not confidence intervals. Report query, mutation and
memory tradeoffs together; include results unfavorable to Knotrel. Do not infer
fraud detection, routing feasibility, commercial superiority or asymptotic bounds
from these runs. Raw trace exports remain ignored local files.
