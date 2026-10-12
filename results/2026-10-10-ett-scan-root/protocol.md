# ETT scan-root reuse pilot

Current GenericForest sources are the baseline. Keep the component root already
selected by smaller_candidates in its immutable iterator. During replacement
search compare only each target root; sources are necessarily members. Preserve
iteration order, candidate selection, APIs and all mutations. No answer cache,
no O(V) scratch, no direct-join candidate. Production remains unchanged.

Nine original pilot cells: path1M q50 fresh/warmed; blocks100k/1M q90
fresh/warmed; dense bridge512 q90 warmed; Cogentco fresh/warmed. Six trials
per engine (current ETT, candidate ETT, petgraph), all six engine-order
permutations once per cell, seed42 group shuffle. 162 sequential processes,
one replay each, original warmup, verified Cogentco SHA. No hardware flush.

Preserve every failure, pair, percentile and setup/RSS tradeoff. Runtime flag:
>5% median increase and at least4/6 slower pairs, not a significance test.
A favorable pilot supports a broader matrix; no automatic integration.
Validate membership/reuse behavior and existing differential tests. Separately
count root calls and parent steps on the diagnostic dense trace, excluding
setup, without recording or comparing instrumented times.
