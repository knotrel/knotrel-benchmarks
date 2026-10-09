# HDT repeated-replay measurement study

## Decision

A/A did not meet the predeclared all-cell ±5% screen. A/B was not started. Aggregating separate replay intervals has not demonstrated sufficiently stable behavior under this screen. Do not integrate or alter the candidate based on this run.

## What this establishes

24 successful processes contain 272 measured replays. The A/A median changes are
+0.91%, +13.62% and +3.31% for cells 0, 1 and 2 respectively. Cell 1 fails the
absolute-change validation rule even though only two of its four paired changes
are positive; this is the declared A/A rule, not the earlier A/B regression rule.

The million-node path accumulated roughly 106/121 ms of measured work per process
(medians left/right), yet the difference remained above the screen. Its first
replay is particularly variable (+107% ratio-of-medians in this small sample).
Repeating an unchanged short trace therefore did not solve the measurement issue.
No cause such as scheduling, cache misses or memory pressure is established.
Whole-process RSS on that path is around 1.06/1.08 GB (median left/right): having
one live graph does not imply that allocator-retained pages disappear each replay.

Do not increase repetition counts again merely to chase a passing result. A
useful next direction is environmental profiling or measurement on an otherwise
idle dedicated host, with CPU scheduling and memory behavior recorded. Keep the
measured reduction in promotion work as separate algorithmic evidence, and avoid
claiming universal timing improvement until controls are credible.

## Method

Use existing repetitions in the exact frozen binaries: 16 replays/process for path100k,q50 (one initial warmup) and path1M,q90 (zero initial warmups), 2 for blocks1M,q90 (one initial warmup). Each replay rebuilds its own graph and excludes setup from workload time; only one graph is live. No Rust code, trace or rounds changes.

This aggregates **separate timed intervals**, not one continuous long interval. Process and allocator caches can carry across rebuilt graphs, so the regime differs from the original single-replay fresh/warmed tests. Every replay retains the same trace fingerprint, oracle answers, operation counts and HDT counters. Workload wall time still includes checking/timing/harness overhead. Setup, individual replays and whole-process RSS are preserved.

Four balanced pairs per cell/stage; process mean is sum of workload times divided by replay count. The process remains the observation unit. Do not treat internal replays as independent trials or pool latency percentiles. [Protocol](protocol.md).

| Stage | Cell | Left mean-replay median ms | Right mean-replay median ms | Change | First-replay change | Sum replay median left/right ms | Slower pairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| AA | 0 | 2.366 | 2.388 | +0.91% | +1.16% | 37.86/38.21 | 3/4 |
| AA | 1 | 6.639 | 7.543 | +13.62% | +107.01% | 106.22/120.68 | 2/4 |
| AA | 2 | 3324.371 | 3434.446 | +3.31% | +3.94% | 6648.74/6868.89 | 4/4 |

Cells: 0=path100k,q50; 1=path1M,q90; 2=blocks1M,q90. Percent change is ratio of medians of process means; it is not median paired change. First-replay change is separate diagnostic information, not an alternative primary statistic. Full ranges and each paired delta are in the stage assessment JSON.

## Limits and preservation

This small study cannot identify a hardware cause, establish a universal noise bound or prove a candidate regression absent. Historical comparisons and the promotion-only patch remain unchanged. The preflight collector initially encountered a missing `config` field on an unrelated imported topology; it was fixed before measurements and [the error log](preflight-failure.txt) was preserved. No failed measurement was discarded.

[Audit](audit.json) records validated hashes, counts and Python syntax. The unchanged binaries passed workspace checks in the earlier candidate study; no new Rust test claim is needed here. No commits or staging changes were made.
