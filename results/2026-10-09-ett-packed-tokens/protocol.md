# ETT packed indices: bounded pilot

Change only the private ETT forest's four optional indices to checked nonzero
encoding. Keep current HDT, all algorithms, public contracts and dependencies
unchanged. Preserve the production checkout and both source snapshots/patch.

Before collection: test the 64-byte layout expectation against the original
96-byte token, then run candidate correctness tests and build both release
binaries from isolated sibling copies. Record compiler, source and binary hashes.

Nine fixed cells from the October 6 ranking: blocks at 100k/1M vertices, 90%
queries, fresh/warmed (four); path at 1M, 50%, fresh/warmed (two); dense bridge
churn at 512, 90%, warmed (one); Cogentco fresh/warmed (two). Four adjacent pairs
per cell, two before-first and two after-first, shuffled with seed 42. 72 sequential
processes, one measured replay each. Keep original commands and trace identities.
No answer cache or hardware cache flush. Warmup is an unreported fresh-graph replay.

Measure complete workload wall time, setup, operation distributions and peak
process RSS separately. Verify oracle-answer counts and fingerprints across all
successful runs. Preserve failures and every adverse pair. RSS includes harness
and setup, not solely the graph. No causal cache-locality claim is inferred.

Decision screen: all runs correct; report all median changes. Flag runtime
regressions above 5% with at least 3/4 slower pairs. A favorable pilot may justify
a larger matrix, not automatic integration. Do not repeat until passing or pool
these observations with historical engine rankings. No promised runtime gain.
