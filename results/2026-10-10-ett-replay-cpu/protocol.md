# Replay-local CPU diagnostic (predeclared)

Hypothesis: the path variance is mostly off-CPU delay. Measure wall and current
thread CPU around the same replay loop, excluding setup and graph destruction.
Also record process CPU, which includes any other process threads. Clock reads
slightly widen CPU intervals; small negative wall-minus-CPU values are retained.
This instrumented experiment is not a replacement for uninstrumented performance
results and does not permit a product speed claim. No per-operation extra clocks.

Use isolated copies of the exact before/after pilot sources. Add rustix 1.1.4
from local cache only to the diagnostic harness for safe CPU clock access.
No production code or lockfile changes. No replay-local resource counter API is
available in that dependency; retain whole-process resources but do not ascribe
them to replay. Exact implementation and lockfile snapshots accompany results.

Same 3 cells and fixed budget: path1M q50 fresh/warmed, dense512 q90 warmed,
12 pairs each, 6 AB/6 BA, shuffled seed1010, 72 sequential runs. Original warmup,
rounds and seed. No trace changes, rerun-until-pass or discarded outliers.
Use process-scoped caffeinate -is and capture power events. Any observed sleep
invalidates campaign acceptance. No integration follows this diagnosis.

Compare individual wall/CPU changes and distributions. Predominantly equal CPU
and wall growth contradicts an off-CPU-only explanation, but cannot distinguish
cache stalls, CPU frequency, page behavior and generated-code effects.
