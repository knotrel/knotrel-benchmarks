# HDT scheduling and memory phase diagnosis

Four baseline-only diagnostic processes, eight path1M,q90 replays each; one small smoke process precedes them. Same algorithm and reference trace, fresh graph each replay. Markers pause the child at phase boundaries while the observer reads macOS task counters. [Protocol](protocol.md).

## Findings and decision

In these 32 perturbed replays, elapsed variation tracks task CPU consumption
closely (descriptive Pearson r=0.99994). Observer wall minus CPU time has a median
of about 19 microseconds and maximum about 156 microseconds, while replay CPU
ranges from 4.20 to 12.70 milliseconds. This provides little support for long
CPU descheduling waits as the dominant variation in this particular run. Boundary
handshakes are included, so these gaps are not pure scheduler-wait measurements.

Replay faults range from 0 to 4,657 and copy-on-write faults from 0 to 954. Their
pooled descriptive correlations with original replay wall time are 0.645 and
0.716. All measured setup and replay pagein deltas are zero. Thus faults are not
evidence of disk paging here. Soft-fault handling and memory behavior are a more
promising next hypothesis than long descheduling waits, but allocation, mapping,
compression and cache mechanisms are not distinguished by these counters.

Do not infer a production fix from this correlation. A controlled next experiment
could resolve writable-page faults before the replay in an isolated copy, retaining
the exact trace, then observe whether replay faults and CPU variation decrease.
Such page preparation also changes cache state and must be labeled as a diagnostic
condition, with its cost reported separately; it is not a free optimization. No
such treatment, system-setting change or candidate integration was performed here.

## Measurement scope

These are **perturbed diagnostics**, not comparable performance results. Task CPU time uses Mach ticks on this host: conversion uses mach_timebase_info and was calibrated against getrusage. Native structure size and offsets match the installed SDK. The initial unit-calibration failure is preserved and occurred before child measurements.

Observer wall and CPU intervals include boundary communication; original workload timers exclude those marker handshakes. Context switches include handshake-induced switching and are not split into voluntary/involuntary. Faults do not necessarily mean disk I/O; pageins are shown separately. Resident bytes are boundary samples, not peak usage or graph payload. Sample-buffer allocation between setup_end and replay_start, and teardown after empty_after, are outside both measured phases; RSS changes across those gaps cannot be assigned to replay work. Empty brackets estimate observable handshake activity but are not subtracted.

## Phase summaries

| Phase | Intervals | Observer wall median ms | CPU median ms | Faults min/median/max | Pageins min/median/max | Context switches min/median/max | RSS median MiB |
|---|---:|---:|---:|---|---|---|---:|
| setup | 32 | 1823.816 | 1821.130 | 22446/31532.0/50185 | 0/0.0/0 | 88/122.5/1510 | 699.9 |
| replay | 32 | 6.284 | 6.265 | 0/194.0/4657 | 0/0.0/0 | 1/1.0/25 | 744.2 |
| empty_before | 32 | 0.036 | 0.005 | 0/0.0/0 | 0/0.0/0 | 1/1.0/1 | 700.4 |
| empty_after | 32 | 0.022 | 0.004 | 0/0.0/0 | 0/0.0/0 | 1/1.0/2 | 744.2 |

## Replay observations

| Process | Replay | Original wall ms | Observed CPU ms | Observer wall ms | Faults | Pageins | Context switches |
|---|---:|---:|---:|---:|---:|---:|---:|
| pair0-left | 0 | 7.745 | 7.750 | 7.770 | 194 | 0 | 1 |
| pair0-left | 1 | 5.073 | 5.077 | 5.096 | 1 | 0 | 1 |
| pair0-left | 2 | 5.405 | 5.408 | 5.423 | 194 | 0 | 1 |
| pair0-left | 3 | 7.247 | 7.251 | 7.272 | 197 | 0 | 1 |
| pair0-left | 4 | 7.318 | 7.322 | 7.338 | 194 | 0 | 1 |
| pair0-left | 5 | 7.913 | 7.802 | 7.958 | 194 | 0 | 25 |
| pair0-left | 6 | 7.623 | 7.628 | 7.645 | 194 | 0 | 1 |
| pair0-left | 7 | 8.027 | 8.032 | 8.050 | 4656 | 0 | 1 |
| pair0-right | 0 | 4.195 | 4.201 | 4.227 | 194 | 0 | 2 |
| pair0-right | 1 | 4.625 | 4.629 | 4.653 | 0 | 0 | 2 |
| pair0-right | 2 | 5.123 | 5.127 | 5.146 | 194 | 0 | 1 |
| pair0-right | 3 | 5.660 | 5.664 | 5.681 | 194 | 0 | 1 |
| pair0-right | 4 | 6.142 | 6.147 | 6.164 | 4014 | 0 | 1 |
| pair0-right | 5 | 4.453 | 4.457 | 4.470 | 0 | 0 | 1 |
| pair0-right | 6 | 5.596 | 5.600 | 5.614 | 0 | 0 | 1 |
| pair0-right | 7 | 6.102 | 6.106 | 6.119 | 1 | 0 | 1 |
| pair1-right | 0 | 6.378 | 6.383 | 6.404 | 194 | 0 | 1 |
| pair1-right | 1 | 4.901 | 4.905 | 4.920 | 0 | 0 | 1 |
| pair1-right | 2 | 5.274 | 5.279 | 5.292 | 194 | 0 | 1 |
| pair1-right | 3 | 6.792 | 6.797 | 6.814 | 194 | 0 | 1 |
| pair1-right | 4 | 8.389 | 8.394 | 8.431 | 4656 | 0 | 2 |
| pair1-right | 5 | 7.962 | 7.965 | 7.994 | 4656 | 0 | 2 |
| pair1-right | 6 | 9.532 | 9.539 | 9.562 | 4656 | 0 | 1 |
| pair1-right | 7 | 5.835 | 5.840 | 5.856 | 3999 | 0 | 1 |
| pair1-left | 0 | 4.717 | 4.722 | 4.742 | 194 | 0 | 1 |
| pair1-left | 1 | 4.730 | 4.732 | 4.755 | 0 | 0 | 2 |
| pair1-left | 2 | 4.806 | 4.811 | 4.825 | 194 | 0 | 1 |
| pair1-left | 3 | 8.660 | 8.667 | 8.700 | 194 | 0 | 1 |
| pair1-left | 4 | 8.026 | 8.031 | 8.049 | 4656 | 0 | 1 |
| pair1-left | 5 | 8.952 | 8.953 | 8.979 | 4656 | 0 | 3 |
| pair1-left | 6 | 8.150 | 8.159 | 8.199 | 4656 | 0 | 2 |
| pair1-left | 7 | 12.709 | 12.699 | 12.792 | 4657 | 0 | 7 |

Descriptive Pearson correlations against original workload wall time: `{"cpu_ns": 0.9999419699183305, "faults": 0.6448380186899855, "pageins": null, "cow_faults": 0.7155944067656951, "csw": 0.26948764930093294}`. These nested observations are not independent; correlations are not causal tests or confidence estimates. Raw boundaries, CPU ticks and snapshot latency remain in [analysis.json](analysis.json) and each observations file.

The diagnostic adds no unsafe Rust or dependency and does not change production sources. [Patch](diagnostic.patch), source snapshots, compiler/binary hashes and the [calibration](calibration.json) are retained. Instruments was unavailable in the installed Command Line Tools environment. No CPU affinity, priority, cache, swap or system configuration was changed.

## Verification

[Verification](verification.json) covers formatting, all-target Clippy, library tests, doctests and Rustdoc. The diagnostic handshake is exercised by the small smoke trace and all 32 full-size replays; ordinary CLI tests assume a different, non-handshake protocol and were not used to validate this isolated runner.
