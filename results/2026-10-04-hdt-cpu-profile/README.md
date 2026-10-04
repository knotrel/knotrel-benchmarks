# HDT CPU stack sample — diagnostic only

macOS `sample` observed our HDT process for five seconds at a requested 1 ms
interval. The workload is cyclic blocks, 100k vertices, 90% queries, **1,000 rounds
and ten replays**: intentionally longer than the reference so it can be sampled.
It includes registration, initial edges, replay and teardown; timings in
`diagnostic-run.json` must not enter the normal comparison tables.

The main thread has 4,181 samples. The nonrecursive top-of-stack summary reports:

| Symbol | Samples | Share of main-thread samples |
| --- | ---: | ---: |
| HDT Forest::pull | 869 | 20.8% |
| HDT Forest::split | 481 | 11.5% |
| HDT Forest::join | 477 | 11.4% |
| HDT Level::ensure | 388 | 9.3% |

These support investigating tree-maintenance and sparse-ID bookkeeping. They do
not show that allocations dominate, and they are not exclusive cut-only shares.
Recursive inclusive counts in the full call graph must not be summed as time.
Sampling and optimizer inlining affect attribution; no allocation profiler ran.

`manifest.json`, `collect.py`, `sample.txt` and `artifact-checksums.json` preserve
commands, source/binary hashes and output. Both sampled benchmark and sampler
exited successfully. No other process was intentionally sampled.
