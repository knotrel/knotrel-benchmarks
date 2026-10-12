# Decision: targeted benefit confirmed, path regression still unresolved

[Full measurements and environmental checks](README.md).

The awake-host campaign completed 72 successful processes with no sleep/wake
transitions observed between collection boundaries. Both power assertion snapshots
show the temporary inhibitor; after the command completed, no caffeinate assertion
remained. Frozen binary and source provenance checks passed. There were no source
changes or core integration.

The dense positive control consistently improves: runtime −44.64%, 12/12 faster
pairs, cut total −44.74%, cut p95 −44.27%. This agrees with both earlier campaigns
and the structural reduction of source-root lookups.

The path does **not** establish non-regression:

| Path case | Ratio of runtime medians | Median paired change | Faster pairs |
|---|---:|---:|---:|
| Fresh | +10.48% | +2.93% | 6/12 |
| Warmed | −4.40% | +16.61% | 5/12 |

These estimators answer different questions. Their disagreement and the broad
ranges prevent treating the warmed median decrease as an improvement. Warmed
before runs span 4.30–18.51 ms; after runs span 5.51–26.17 ms. Fresh includes an
adverse pair of +232.34%. All samples are retained. Neither cell meets the
predeclared screening flag's joint size-and-consistency criterion; absence of a
flag is not proof of non-regression.

Whole-process RSS medians change +1.83% fresh / −3.31% warmed. Fresh setup rises
1.10%, warmed setup falls 0.28%. The warmed path's setup alone is about 1.56 s,
versus approximately 9 ms for measured operations. Whole-process scheduling and
memory counters are dominated by activity outside the measured replay and do not
identify its cause. The structural replay still has identical per-operation root
calls, parent steps, answers and forest counters.

Conclusion: sleep explains the previous campaign's long process-time gaps, but
removing sleep does not remove path variability. It is not justified to attribute
the original +36.77% to standby, to dismiss it as noise, or to claim a path speedup.
Keep the patch isolated and preserve the original regression.

## Next diagnostic step

Add separate replay-local instrumentation around the complete operation loop:
wall time and current-thread CPU time, plus process resource deltas where
available. Save those as diagnostic results, separate from uninstrumented timing.
Keep fresh/warmed graph reconstruction semantics and inspect individual runs.
This distinguishes off-CPU delay from time spent executing before investigating
allocator/page behavior or code layout. Process deltas are not necessarily
thread-local; document that boundary. Do not change the core algorithm or increase
rounds without a separate protocol: longer traces change the mutated graph fraction.
