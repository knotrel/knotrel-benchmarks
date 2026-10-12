# ETT direct joins: isolated competitor-aware pilot

Replace only three concatenations in ETT forest link with two AVL joins using
new directed tokens as pivots. Preserve sequence, exact connectivity and APIs.
Use current sources, including the user's latest libraries; old ranking timings
are not the baseline. Keep production source unchanged and save the patch.

Nine cells: path 1M q50 fresh/warmed; blocks 100k/1M q90 fresh/warmed;
dense bridge 512 q90 warmed; Cogentco fresh/warmed. Six independent trials per
cell per engine: current ETT, candidate ETT, petgraph. All six permutations of
three engines used once per cell; groups shuffled seed42; sequential execution.
162 processes, same traces, one replay per process, original warmup settings.
Petgraph uses the frozen baseline binary, with identical adapter semantics.
Verify recovered Cogentco SHA before starting. No answer caching/hardware flush.

Run existing invariant/differential tests on both core variants and full
candidate workspace checks. Record all sources/binaries/compiler/checkouts.
Compare per-cell median workload wall time, setup, whole-process peak RSS,
operation p50/p95/p99 and all paired changes. Do not pool percentiles or infer
throughput by reciprocal median. A runtime regression screen is >5% median
increase with at least 4/6 slower pairs; all other adverse observations remain.
Preserve failures and exclude incomplete cells. A favorable pilot supports a
larger matrix, not automatic integration or universal competitor superiority.
