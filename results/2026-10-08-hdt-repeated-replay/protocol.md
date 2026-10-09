# Repeated replay measurement validation

Use the existing --repetitions option in the exact frozen before/after binaries.
No Rust changes. Each repetition creates a fresh graph, replays the identical
trace with its independent expected answers and excludes setup from workload time.
At most one graph is live; no pool of million-node states. Do not increase rounds:
that would change sustained traces. This is an aggregate of separate timed
intervals, not one continuous long interval or isolated kernel measurement.

Three cells: path100k,q50 with one initial warmup; path1M,q90 with zero initial
warmups; blocks1M,q90 with one initial warmup. Path cells use 16 repetitions/process,
blocks use 2. Cache state may persist between repetitions, so call this a repeated
process regime, not the original fresh/warmed regime. No hardware cache flush.

First A/A: baseline executable against itself, 4 process pairs/cell, balanced2/2,
seed42shuffle,24 sequential processes,300s timeout each. Validation screen:
all runs complete and absolute ratio-of-median change of the process mean replay
time <=5% in every cell. Four pairs is limited evidence, not equivalence. If this
screen fails, stop before A/B and report the failure; do not tune repetitions or
remove outliers to force a pass in this study.

Only if A/A passes, run A/B with the same schedule and counts. Retain both stages
separately. Flag >5% candidate slowdown with >=3/4 slower pairs; no automatic core
integration. The independent samples are processes, not internal repetitions.
Preserve first replay and all individual runtime/setup/counters/latency summaries;
report process sum, process mean and first-replay separately. Do not pool latency
percentiles or historical data. Record workload timer/harness overhead and whole
process RSS. This tests aggregation reliability, not a new algorithm.
