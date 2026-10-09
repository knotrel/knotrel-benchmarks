# Packed tokens: full optimization reference matrix

Use exact frozen before/after binaries from the 64-byte token pilot. No source,
trace, algorithm, warm-up, or page-preparation changes. Separate from pilot;
do not pool samples. 38 optimization reference cells: 24 sparse path/blocks at
100k/1M with query fractions10/50/90 and fresh/warmed; 12dense512; 2Cogentco197.
This is not the entire 74-cell competitor ranking.

Four balanced pairs per cell,2/2 order,shuffle42,304sequential processes,120s timeout.
Retain failures and every result. Report per-cell runtime/setup/whole-process RSS,
latency summaries and paired direction. No heavy workloads alongside timing.
Check frozen source/binary hashes, trace fingerprints, oracle/count/HDT identity.

Flag >5% runtime regression with>=3/4 slower pairs for investigation before
integration; report all smaller regressions too. This engineering screen is not
significance and prior A/A instability remains relevant. Exact token size reduction
96->64 is distinct from total process RSS. Passing does not automatically integrate,
stage or commit the candidate. Keep every previous experiment intact.
