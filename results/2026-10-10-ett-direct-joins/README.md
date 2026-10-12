# ETT direct joins: paired pilot with petgraph

Only ETT forest link changes: two direct joins replace three concatenations.
Production sources remain unchanged. The candidate and baseline reflect the
current libraries; historical timing campaigns are not reused as measurements.

Six trials per engine/cell, all six engine-order permutations, sequential runs.
All figures below are per-cell medians. Negative percentages mean less time.
RSS is whole-process peak; setup and operation tails remain separate in
[comparison.json](comparison.json). [Protocol](protocol.md).

| Workload | Nodes | Query % | Regime | Before ms | After ms | Petgraph ms | Change vs before | Change vs petgraph | Faster pairs | RSS change | Setup change | Flag |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.243 | 0.226 | 0.728 | -6.92% | -68.89% | 6/6 | +0.00% | -20.08% | False |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.224 | 0.202 | 0.662 | -9.46% | -69.41% | 6/6 | +0.00% | -32.18% | False |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 33.951 | 37.891 | 178.162 | +11.60% | -78.73% | 0/6 | -0.28% | -8.66% | True |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 3.291 | 3.237 | 41.406 | -1.64% | -92.18% | 3/6 | -0.01% | -42.08% | False |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 3.021 | 2.867 | 41.365 | -5.10% | -93.07% | 3/6 | +0.01% | -45.57% | False |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 40.712 | 42.941 | 413.893 | +5.47% | -89.62% | 1/6 | +1.90% | -44.63% | True |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 40.193 | 40.368 | 444.460 | +0.44% | -90.92% | 2/6 | +19.45% | -46.48% | False |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 7.273 | 7.831 | 36.342 | +7.67% | -78.45% | 2/6 | +5.37% | -46.35% | True |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 6.623 | 7.290 | 36.763 | +10.08% | -80.17% | 3/6 | +6.93% | -46.58% | False |

Failed processes: 0. Screening flags: 3.

A flag is >5% runtime increase with at least 4/6 adverse pairs, not a significance test.
No outliers removed or repeated-until-pass. No hardware-cache flush or answer cache.
Fresh/warmed refer to deliberate full-graph replay warmup. Fixed operation counts
change the mutated fraction at different sizes. Cogentco is one real topology
with synthetic outages; no general market superiority or tail guarantee follows.

Tests, source/binary provenance and the saved patch accompany this report.
Existing forest differential/invariant tests ran on both variants. The full
candidate workspace checks are in [verification.json](verification.json).

## Decision

Do not integrate this candidate as a general replay optimization. Three cells
meet the declared regression screen: dense warmed +11.60% (0/6 faster pairs),
1M blocks fresh +5.47% (1/6), and 1M path fresh +7.67% (2/6). The unflagged
1M path warmed median also increases 10.08% (3/6 faster); retain this adverse
observation despite the screen not triggering. Warmed 1M blocks peak RSS also
increases 19.45%; the runtime-only screen must not hide this memory cost.

Cogentco improves 6.92–9.46% (6/6 pairs in each regime). Setup on 1M fresh
blocks/path decreases 44.63%/46.35%, but replay regresses. This may motivate a
separate bulk-construction investigation, not a hidden runtime fallback.

Both original and candidate ETT beat petgraph on all nine selected cell medians.
The candidate's margin against petgraph therefore does not establish that this
patch improves Knotrel: its relevant before/after comparison is mixed. This
small query-heavy selection does not replace the broader competitor ranking.

In the dense case the before/after forest counters are identical: 3,238,500
candidate edges, 12,750 scanned vertices and 50 tree cuts. Median cut total time
increases 11.74%, while link and query totals decrease 38.53% and 34.33%.
This localizes the observed cost to cut processing without proving a mechanism.
AVL shape, traversal work below these counters and memory effects remain
possible explanations. Do not assert cache or scheduling causality from timers.

The next useful experiment is a focused cut-path structural profile of this
dense case, separating replacement-edge scanning from AVL root/rank/split work.
Preserve the current production engine; do not add an automatic engine selector
or claim a universal competitor speedup based on this pilot.
