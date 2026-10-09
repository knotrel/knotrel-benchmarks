# HDT token-arena preparation diagnostic

One isolated binary, baseline algorithm, exact path1M,q90 trace. Modes none/read/write run in a balanced three-block order, three processes each, eight fresh-graph replays/process. Each mode also passes a small smoke run. [Protocol](protocol.md).

## Decision and findings

Do not integrate this preparation pass: it moves cost rather than removing it.
Read preparation reduces median replay time 49.28%, but preparation+replay costs
122.98% more. Write preparation reduces replay time 58.46%, with 228.06% higher
combined cost. Setup is separate and would add further cost to all conditions.

For write mode, the median of process-mean replay faults falls from 2,318.75 to
0.125, and COW faults from 367.75 to zero. The preparation phase itself incurs
faults (median process mean 5,724.875). All preparation/replay pagein deltas are
zero. This intervention supports a material effect of the token arena's memory
state on this diagnostic workload. The read-only improvement also shows that
writable-page preparation is not the only relevant effect. We cannot apportion
the timing difference between fault handling, cache warming, compression or
other memory mechanisms from these measurements alone.

There are only three full-size process observations per mode. Replay variation
remains: individual write-mode replays range from roughly 2.3 to 5.7 ms. Do not
claim the benchmark is now stable, universal causal attribution, or a production
speedup. Historical promotion-only results remain separate and unresolved.

A more useful optimization hypothesis is reducing the token footprint rather
than adding an O(tokens) warm-up before each trace. The compiled arena stride is
96 bytes/token here; a denser representation could touch fewer pages. Such a
representation change requires its own invariants, correctness tests and paired
measurements. It is proposed, not implemented in this experiment.

## Scope and verification of treatment

Only initialized forest tokens are touched. For this trace the setup creates 2,999,998 tokens. Each read visits the candidate byte; each write stores its identical black-boxed value. Unused capacity, adjacency trees, maps, graph metadata and sample buffers are not prepared. This is not complete graph/process prefaulting.

The [saved assembly](touch-assembly.txt) contains a token load at stride 0x60 in the read loop and a token store at the same stride in the write loop. Read mode still writes its black_box temporary on the stack. The state-preservation test compares all Debug-visible forest fields and checks AVL/aggregate invariants after preparation and token recycling; all replay oracle/counters match the reference.

## Process-level comparison

Medians below are over three process means, not over 24 independent replays. Preparation+replay is computed per replay before averaging, and excludes setup. All modes share the same diagnostic binary.

| Mode | Preparation ms | Replay ms | Replay change | Preparation + replay ms | Combined change | Replay faults | Replay COW faults | Preparation faults |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| none | 0.000 | 7.409 | +0.00% | 7.409 | +0.00% | 2318.8 | 367.8 | 0.0 |
| read | 13.357 | 3.758 | -49.28% | 16.520 | +122.98% | 405.1 | 135.8 | 3404.6 |
| write | 21.228 | 3.077 | -58.46% | 24.305 | +228.06% | 0.1 | 0.0 | 5724.9 |

## Every full-size process

| Process | Preparation mean ms | Replay mean ms | Replay min–max ms | Combined mean ms | Replay faults mean | Replay COW mean |
|---|---:|---:|---:|---:|---:|---:|
| block0-none | 0.000 | 7.520 | 6.337–8.745 | 7.520 | 2318.8 | 367.9 |
| block0-read | 13.357 | 2.770 | 2.444–3.129 | 16.127 | 13.6 | 13.0 |
| block0-write | 21.228 | 3.077 | 2.389–4.457 | 24.305 | 0.1 | 0.0 |
| block1-read | 24.255 | 3.768 | 2.809–5.021 | 28.022 | 405.1 | 135.8 |
| block1-write | 26.562 | 3.215 | 2.468–5.690 | 29.776 | 24.9 | 0.0 |
| block1-none | 0.000 | 7.409 | 5.089–9.752 | 7.409 | 2318.9 | 367.8 |
| block2-write | 20.533 | 2.819 | 2.308–3.679 | 23.352 | 0.1 | 0.0 |
| block2-none | 0.000 | 7.143 | 5.432–11.498 | 7.143 | 70.9 | 6.6 |
| block2-read | 12.762 | 3.758 | 2.531–5.010 | 16.520 | 485.8 | 371.0 |

## Limits

This is a perturbed resource experiment, not production performance. Touching pages also changes cache state and consumes memory bandwidth. Read versus write helps interpretation but is not perfect causal isolation. Task counters include boundary IPC; original setup/preparation/replay timers exclude it. Empty brackets remain in the raw observations. Page faults are not synonymous with disk I/O; pageins are retained separately. CPU time is converted from Mach ticks using the calibrated system timebase. RSS is sampled at boundaries, not peak graph memory. Sample allocation and graph teardown remain outside these phases.

No historical measurements are pooled, outliers removed, or latency percentiles combined. [analysis.json](analysis.json) retains individual phases, process observations, range and CPU/resource counters. [Diagnostic patch](diagnostic.patch) and complete source snapshots remain separate from production. No commit or staging action was performed.

## Validation

[Verification](verification.json) records formatting, all-target Clippy, benchmark
library tests/doctests and Rustdoc, plus core Clippy, complete core tests/doctests
and Rustdoc. The initial new-entry-point test failure is recorded separately;
it indicates the diagnostic method was absent, not a baseline algorithm defect.
Three smoke processes and nine full-size processes succeeded (6 small and 72
full-size replays). Every full replay matches the frozen fingerprint, expected
answers, operation counts and HDT counters. Source/binary hashes and phase order
are checked in [audit](audit.json).

Independent review was requested but the reviewer hit its usage limit before
completing this experiment. No independent-review approval is claimed; automated
checks and primary-agent inspection were completed.
