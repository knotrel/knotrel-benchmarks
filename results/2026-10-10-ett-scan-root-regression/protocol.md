# Scan-root regression confirmation (predeclared)

Question: does the warmed million-vertex path slowdown repeat with the exact
frozen binaries, or is its direction unstable across fresh processes?
No source changes, recompilation, cache flush or core integration.

Use path1M q50 fresh and warmed plus dense bridge512 q90 warmed as a positive
control. Twelve matched before/after pairs per cell (72 sequential processes),
six AB and six BA, groups shuffled with seed 1010. Keep original commands,
seeds, rounds, warmup and one measured replay. No petgraph rerun: the question
is candidate overhead, not a new competitor ranking. Stop at this fixed budget;
retain every failure/outlier. Flag >5% median increase and >=8/12 adverse pairs;
this is a screening rule, not a statistical significance test.

Record full time -l output and UTC order. Resource counts cover the whole
process (including graph construction, warmup and destruction); they cannot
establish a replay-local scheduling or memory cause. Inspect operation totals,
tails and pairs, not just one median. Preserve the original flagged pilot.

Before timing, replay the same million-vertex path in the already frozen
counter binaries twice each. Compare per-operation answers, root calls/steps,
and forest counters. This counter runner has no warmup and no elapsed timers:
it checks graph work, not the warmed cache state. No concurrent heavy work.
