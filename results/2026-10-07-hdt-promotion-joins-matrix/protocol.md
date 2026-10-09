# Promotion-only joins: full optimization reference matrix

Separate follow-up to the successful nine-cell pilot. Reuse its exact frozen
before/after binaries; do not combine samples or change the candidate.

38 cells: sparse path/blocks at 100k and 1M vertices, query fractions 10/50/90,
fresh/warmed (24); dense controls at 512 vertices (12); Cogentco (2).
This is the full 38-cell optimization matrix used in earlier candidate studies,
not all sizes/engines in the broader 74-cell competitor ranking. Four pairs/cell,
balanced 2/2 execution order, seed42 shuffle, 304 sequential processes, 120s timeout.
No heavy diagnostics alongside timed measurements. Preserve failures and raw data.

Report runtime relative to before median, pair direction, setup, whole-process RSS
and operation latency tails. No pooled competitor ranking or throughput inference.
Warm-up is an untimed replay on a separate graph, not an answer cache. Hardware
caches are not flushed. Check trace fingerprint, oracle results, operation counts
and HDT counters. Keep historical baselines and pilot separate.

Flag any cell with >5% runtime regression and at least 3/4 slower pairs for
investigation before integration. Report all other regressions too, even below
this engineering screen. This screen is not statistical significance. A broad
benefit does not permit ignoring an individual regression. No automatic commit
or production integration is part of this measurement step.
