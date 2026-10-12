# ETT cut structural diagnosis

Compare the exact original/direct-join forest snapshots from the preceding
pilot, adding identical diagnostic hooks to both. Production sources unchanged.
No diagnostic timings are interpreted or compared to normal benchmark timings.
Thread-local counters avoid changing Token/Forest layouts; instrumentation still
perturbs execution and is intended only to measure structural work.

Per operation, count root calls and parent steps, rank calls/parent steps,
split/join entries (including recursion/base cases), pulls, rotations,
candidate iterator tokens and mark-propagation ancestor visits. Attribute work
to outer/other, tree detach, replacement search and replacement repair using
nested phase guards. Retain ordinary ForestStats and operation answers.
Setup is excluded by clearing counters before each operation.

Primary: dense bridge churn, 512 nodes, q90, rounds10, seed42. Controls:
redundant bridge churn512/q90 and path1024/q50. Replay each variant twice in
fresh processes and require exact structural repeatability. Total12processes.
Counters, not CPU time shares: an increased count supports added structural
work, not quantified timing causality. Original pilot regressions remain intact.
