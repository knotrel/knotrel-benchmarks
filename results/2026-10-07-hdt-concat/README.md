# HDT dedicated concat extraction — 2026-10-07

**Decision: keep this candidate experimental; do not expand or integrate it.** The predeclared pilot gate is not met: only one of four block cells has at least 3% lower median runtime with at least three of four faster pairs. Three qualifying block cells were required. No control crosses the specified regression gate.

`concat` originally extracted its pivot using a general split at the last token rank. [candidate.patch](candidate.patch) replaces that operation with a right-spine extraction and AVL deletion rebalancing. It preserves sequence order, parent pointers and aggregates, but may change tree shape. It does not include the earlier rank-zero or fused-lookup candidates.

## Pilot runtime

64 timed processes completed successfully, across eight cells with four sequential pairs each. Each cell has two before-first and two after-first pairs. This pilot covers only the cases below; it is not a new full ranking. The gate was recorded in [protocol.md](protocol.md) before measurement. Negative percentages mean lower workload wall runtime, excluding setup; four pairs are not a statistical confidence interval.

| Workload | Vertices | Query mix | Regime | Before ms | After ms | Runtime change | Faster pairs / 4 |
|---|---:|---:|---|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.513 | 0.509 | -0.84% | 2 |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.453 | 0.451 | -0.25% | 3 |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.414 | 8.489 | +0.90% | 2 |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 216.137 | 215.211 | -0.43% | 3 |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 217.841 | 214.826 | -1.38% | 3 |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3490.649 | 3497.183 | +0.19% | 1 |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3401.467 | 3288.765 | -3.31% | 3 |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 5.654 | 5.491 | -2.88% | 3 |

The warmed 1M-block / 90%-query cell improves 3.31%, faster in three of four pairs. The fresh counterpart is 0.19% slower. The 100k block changes are -0.43% fresh and -1.38% warmed. These small/mixed results do not support a general performance claim. Setup, operation tails, paired runtime changes and process RSS remain in [comparison.json](comparison.json). RSS is for the whole process, not only the graph structure. Warmup does not flush hardware caches.

## Structural evidence

Two repetitions per variant on each preserved 100k/1M block trace with 90% queries (eight instrumented replays total) return identical counts. Promotion counts by level and endpoint materialization match between variants. The probes run separately from timing.

| Vertices | Promotion pull change | Promotion join change | Promotion split change | Added pop_last entries |
|---|---:|---:|---:|---:|
| 100000 | -1.32% | -3.77% | -15.87% | 265,666 |
| 1000000 | -1.07% | -2.99% | -13.41% | 2,850,058 |

At one million vertices, eliminating general split work removes about 13.41% of split entries and 2.99% of join entries, but only 1.07% of aggregate-recomputation (`pull`) entries, while adding 2,850,058 dedicated extraction entries. Recursive function counts are not instruction costs or CPU-time shares; unlike calls must not be added into a synthetic speedup. This is consistent with replacing some traversal machinery while leaving most tree maintenance in place, rather than removing the expensive promotion workload.

## Correctness and preservation

An independent test exercises extraction on tours of 1–95 vertex tokens, every split position, repeated concatenation/extraction, candidate marks and parent/AVL invariants. Full existing core tests/doctests cover real tree-edge handles, cuts, cycles and replacements. The new direct test fails to compile against the before source because the helper does not exist; this is an availability check, not a discovered correctness failure in the original code. The candidate passes. Reconstruction from saved source also passes format, Clippy, core tests/doctests and Rustdoc checks.

Every successful timing replay validates its oracle. Analysis verifies artifact hashes, trace fingerprints, actual mutation/query and answer counts, and paired HDT counters. The [gate result](gate.json) records the unchanged screening thresholds. Before/after sources, patch, test source, commands and raw outputs are saved here; structural probes are in sibling before-probe/after-probe directories. Source snapshots match the frozen ranking except for this forest patch. No production source, default configuration, staged file or historical measurement was changed by this experiment.

The [candidate inventory](../../docs/experiments/2026-10-06-hdt-candidates.md) preserves all three alternatives and their SHA-256 hashes. They are not committed or combined. Reproduce in a fresh destination using build.py, test.py, collect.py, analyze.py and gate.py; then run the separate structural probes, structural-comparison.py, verify.py and report.py. Raw final collections refuse overwrite.

## Next hypothesis

Inspect how the two joins in `link` are associated. The current code builds `left + ab + right` and then appends `ba` to the merged tree. Forming `right + ba` first and joining that with `left` around `ab` preserves the same sequence. It may avoid appending to the larger merged tree when the right tour is small. Measure tour sizes and structural work before testing this separate candidate; no benefit from that reassociation is claimed here.
