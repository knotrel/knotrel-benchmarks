# ETT packed tokens: full paired matrix

Use the exact frozen before/after binaries from the ETT packed-token pilot.
38 fixed cells: sparse path/blocks at 100k and 1M, query ratios 10/50/90,
fresh/warmed (24); two dense workloads at 512, three ratios, fresh/warmed (12);
Cogentco fresh/warmed (2). Four adjacent pairs per cell, order balanced 2/2,
seed42 shuffle, 304 sequential processes, one measured replay per process.

Validate the recovered Cogentco trace SHA before collection. All source and
binary hashes must match the pilot. No answer cache or hardware flush. Preserve
all failures and adverse pairs, excluding incomplete cells from conclusions.
Compare workload runtime, setup, operation tails and whole-process RSS separately.
Flag median runtime >5% slower with at least 3/4 adverse pairs. This screen is not
a significance test. Do not pool with pilot or competitor campaigns; no automatic
integration or repeat-until-pass. Production ETT remains unchanged.
