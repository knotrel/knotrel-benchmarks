# Empty-rotation HDT experiment

Question: does avoiding split/concat when reroot rank is zero improve the
preserved cyclic-block workloads without material regressions in controls?
The isolated structural probe establishes frequency; it does not time savings.
Only the rank-zero early return differs between release variants. No other
algorithm, incidence order, configuration or default changes.

Use paired sequential process trials, alternating before/after order per pair,
seeded shuffle (42), three pairs per cell. Select the current ranking's sparse
100k/1M path/blocks × 10/50/90% queries × fresh/warmed (24 cells), dense 512
one/two bridges × 10/50/90% × fresh/warmed (12 cells), and Cogentco (2 cells).
Total: 38 cells, 114 pairs, 228 processes. Preserve raw results, hashes and
failures. Compare fingerprints, actual operation/query outcomes and HDT counters.
Do not change sources while collecting or mix instrumented probe timings in.

Primary metric: median replay wall runtime per cell; report signed percentage
change and paired direction counts, separately from setup/tails/process RSS.
No aggregate speedup or default switch. A small or mixed result is insufficient
to promote the candidate: keep it isolated and document it. Confirm clear
regressions before claiming causality. Existing baselines remain untouched.
