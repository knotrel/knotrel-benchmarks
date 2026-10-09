# HDT cyclic-blocks diagnosis — 2026-10-06

Diagnostic replay time is concentrated in cuts that perform promotions; nearly all counted forest join work occurs inside tree-promotion bodies. This is a diagnosis, not an optimization result: production sources and the default engine are unchanged. The [current ranking](../2026-10-06-engine-ranking/README.md) remains the normal timing baseline.

## Observations

At one million vertices and 90% queries, the block trace has 100 cuts (97 tree cuts), 900 queries and no links. It causes 2,279,725 tree promotions and 134,846 non-tree promotions, yet only 47 replacements. The path control has 100 tree cuts and zero promotions or replacement candidates. The same distinction appears at 100,000 vertices.

| Vertices | Queries | Topology | Tree cuts | Cuts with promotions | Tree promotions | Non-tree promotions | Candidates | Replacements |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 100,000 | 10% | sustained-churn-path-v1 | 894 | 0 | 0 | 0 | 0 | 0 |
| 100,000 | 10% | sustained-churn-blocks-v1 | 829 | 778 | 321,004 | 18,837 | 19,233 | 396 |
| 100,000 | 50% | sustained-churn-path-v1 | 498 | 0 | 0 | 0 | 0 | 0 |
| 100,000 | 50% | sustained-churn-blocks-v1 | 477 | 450 | 328,503 | 19,534 | 19,768 | 234 |
| 100,000 | 90% | sustained-churn-path-v1 | 100 | 0 | 0 | 0 | 0 | 0 |
| 100,000 | 90% | sustained-churn-blocks-v1 | 97 | 91 | 212,272 | 12,317 | 12,364 | 47 |
| 1,000,000 | 10% | sustained-churn-path-v1 | 900 | 0 | 0 | 0 | 0 | 0 |
| 1,000,000 | 10% | sustained-churn-blocks-v1 | 868 | 812 | 3,464,793 | 206,168 | 206,588 | 420 |
| 1,000,000 | 50% | sustained-churn-path-v1 | 500 | 0 | 0 | 0 | 0 | 0 |
| 1,000,000 | 50% | sustained-churn-blocks-v1 | 480 | 455 | 3,296,813 | 197,072 | 197,303 | 231 |
| 1,000,000 | 90% | sustained-churn-path-v1 | 100 | 0 | 0 | 0 | 0 | 0 |
| 1,000,000 | 90% | sustained-churn-blocks-v1 | 97 | 95 | 2,279,725 | 134,846 | 134,893 | 47 |

## Isolated structural attribution

Four traces (path/blocks × 100k/1M, 90% queries) were replayed twice against a temporary copy of the current core, with counters inserted into promotion bodies and forest functions. Both runs return identical counters. All results are oracle-checked; aggregate HDT counters match the existing profiler. Function calls include recursive and base-case calls. These counts are not CPU-time percentages.

| Block vertices | Promotion-body pull calls | Promotion-body join calls | Promotion-body split calls | Share of all replay join calls | Newly materialized vertex records |
|---|---:|---:|---:|---:|---:|
| 100,000 | 12,011,875 | 11,271,179 | 4,013,990 | 99.742% | 212,335 |
| 1,000,000 | 160,524,732 | 152,549,086 | 50,998,602 | 99.976% | 2,279,793 |

A vertex record here belongs to one forest level. A single graph vertex can have multiple such records. Materialization counts are not allocator-call counts, and this probe does not measure allocation latency or hardware cache misses.

| Source level → next level | Tree promotions, 100k blocks | Tree promotions, 1M blocks |
|---|---:|---:|
| 0 → 1 | 98,276 | 935,470 |
| 1 → 2 | 71,970 | 705,525 |
| 2 → 3 | 34,330 | 451,748 |
| 3 → 4 | 7,540 | 179,910 |
| 4 → 5 | 156 | 7,072 |

## Storage and diagnostic timing

At 1M vertices / 90% queries on blocks, requested owned vector capacity rises from 477,374,128 bytes after setup to 1,829,305,616 bytes after replay; materialized levels rise from one to six. Live ordered-container payload rises from 83,999,936 to 120,470,224 bytes. These snapshots exclude allocator and B-tree overhead and are not total heap or RSS. They describe retained storage, not allocation rate.

The existing profiler places the full duration of a cut in the “with promotions” category if it performs any promotion. Across the block diagnostics, that category accounts for 98.97%–99.83% of summed instrumented operation intervals. This includes other repair work inside those cuts; it is not a timing of the promotion body alone. Diagnostic sampling/storage snapshots perturb caches, so these timings are never compared numerically with the normal ranking.

## Interpretation and next optimization experiment

In the implementation, `replace` promotes the smaller side’s exact-level tree edges before scanning its non-tree candidates. Every tree promotion creates a tour copy in the next forest through `forest.link`; it can also materialize endpoint records. A few cuts can therefore trigger millions of promotions early in the edge lifetimes. This is consistent with an amortized update bound: the benchmark includes setup separately and measures a short, 1,000-operation replay, not steady-state amortized cost over an indefinite history.

The evidence makes repeated construction of higher-level forests the first optimization target. Before changing promotion order or skipping work (which could violate HDT invariants), profile the link/reroot path within tree promotion, then test a single reduction in redundant structural work or endpoint materialization. Preserve graph semantics and compare an uninstrumented candidate with the frozen current build using interleaved trials. Keep the path, dense and Cogentco cases as regression controls. A bulk promotion/build approach is a separate algorithmic design requiring an invariant proof; these counters alone do not justify adopting it.

No improvement percentage is claimed here. Candidate-edge scanning is not ruled out as a cost, but candidate count alone does not explain the measured volume of forest maintenance. Cache misses and allocator overhead remain unmeasured.

## Reproduction and audit

`collect.py` runs the existing `hdt-profile` binary twice on each of 12 preserved traces: 100k/1M vertices, 10/50/90% queries, path/blocks, ten rounds, seed 42. All 24 processes succeed. Source hashes match the current ranking. Fingerprints and mutation/query counts match its normal runs; counters and storage snapshots are identical across the repeated diagnostics. Fresh/warmed timing regimes are not duplicated because this is a structural diagnosis, not a cache-performance comparison.

The [isolated probe](../2026-10-06-hdt-blocks-structure/probe.py) preserves its injected sources, harness, compiler commands and [results](../2026-10-06-hdt-blocks-structure/results.json). It exports and verifies the exact traces before replay. Setup counters are reset before the measured operation sequence. Instrumented binaries are never used for timing claims.

Run `collect.py`, then the sibling structural `probe.py`, then `analyze.py`; collectors reject existing final outputs. [analysis.json](analysis.json) retains all snapshots and diagnostic ranges; raw JSON and manifests remain adjacent. No historical result was overwritten.
