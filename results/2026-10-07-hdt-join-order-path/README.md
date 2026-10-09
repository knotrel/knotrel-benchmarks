# Adaptive path confirmation

This follow-up was selected after the initial pilot's noisy +32.29% path result.
It is separate evidence, not a preplanned replication or an automatic gate override.
See [protocol](protocol.md), [comparison](comparison.json) and the
[parent experiment](../2026-10-07-hdt-join-order/README.md).

32 sequential processes, eight pairs per regime, balanced 4/4 order. Same frozen
binaries and path trace; one million vertices, 500 cuts, 500 queries, no links.
All processes succeeded and fingerprints, oracle answers and HDT counters match.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs |
|---|---:|---:|---|---:|---:|---:|---:|
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 8.944 | 8.000 | -10.55% | 4/8 |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.993 | 6.430 | +7.29% | 3/8 |

Fresh: before 6.850–10.821 ms, after 7.239–11.898 ms; 4/8 faster pairs.
Warmed: before 5.522–7.815 ms, after 5.895–23.352 ms; 3/8 faster pairs.
Do not pool these observations with the initial pilot or claim a stable 32%
regression. The warmed result leaves a possible regression unresolved.

[Structural counters](structural-comparison.json), from separate instrumented
replays repeated twice per variant, show modestly increased forest work despite
identical oracle results and HDT counters. They exclude setup and do not measure
time shares. The workload contains no tree promotions. The original gate remains
failed; the candidate is preserved but not integrated.
