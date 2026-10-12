# ETT replay-local CPU diagnosis

**Off-CPU delay alone does not explain the path variability.** Across all 36
matched pairs, current-thread CPU and wall-time changes have the same direction.
The dense benefit remains about 45% in both metrics; the path remains variable.
This narrows the investigation but does not resolve the original regression.

[Protocol](protocol.md), [all paired measurements](comparison.json),
[CPU summary](cpu-summary.json), [environment](environment.json).

## Method and verification

Two isolated instrumented binaries from the original pilot's before/after core
snapshots; production checkouts and lockfiles are unchanged. The only diagnostic
dependency is locally cached rustix 1.1.4, using safe thread/process CPU clock APIs.
Saved harness source and lockfile, build script, binary hashes and commands are
included. Formatting, all-target Clippy, workspace tests and Rustdoc checks passed
for the isolated benchmark workspace ([verification](verification.json)).

Clocks bracket the entire operation loop after graph setup and sample allocation,
before summaries and graph destruction. The original per-operation timing and
oracle remain unchanged. CPU intervals are slightly wider than wall intervals
because clock reads are sequential; negative sub-microsecond differences are
retained. Process CPU includes other threads if present. CPU time includes time
spent on-core waiting for memory; it is not a count of useful instructions.

72 sequential processes, twelve pairs per cell, six AB/six BA, original traces,
rounds and warmup. Temporary sleep prevention was active. No sleep events were
observed during the two-minute collection. All runs succeeded; trace fingerprints,
answer/operation counts, forest stats, artifact hashes and ordering checks passed.
These are diagnostic timings, not a replacement for the uninstrumented campaigns.

## Results

| Case | Wall median change | Thread CPU median change | Faster wall pairs |
|---|---:|---:|---:|
| Dense512 q90 warmed | −44.94% | −44.91% | 12/12 |
| Path1M q50 fresh | −1.31% | −1.37% | 6/12 |
| Path1M q50 warmed | −3.50% | −2.73% | 7/12 |

Percentages compare per-variant medians. Individual paired CPU changes remain
wide: fresh approximately −24% to +43%; warmed approximately −32% to +35%.
No samples were removed, and these small path median decreases do not establish
non-regression or a reproducible speedup.

Wall-minus-thread-CPU differences, expressed as a fraction of each run's wall time:

| Case / variant | Median gap | Maximum gap |
|---|---:|---:|
| Fresh before | 0.022% | 1.56% |
| Fresh after | 0.060% | 0.89% |
| Warmed before | 0.121% | 21.17% |
| Warmed after | −0.005% | 8.18% |

Most path runs have very little off-CPU gap. Some warmed outliers do contain
significant off-CPU delay, so scheduling is a contributor. However CPU variability
persists after separating that gap, and every pair retains its direction.
Percentage changes of the near-zero signed `wall_minus_thread_ns` metric in the
raw generic comparison are not meaningful; use absolute gaps or fractions above.

## What this establishes and what remains unknown

The earlier exact structural replay showed identical root calls and parent steps
on the path, with zero candidate scans. This diagnosis finds variability in CPU
time despite that unchanged abstract work. Possible causes include memory locality,
page behavior, CPU frequency/core placement or generated-code layout. This
experiment does not distinguish them. It does not prove an algorithmic regression,
prove standby caused the original +36.77%, or justify dismissing adverse pairs.

Replay-local resource deltas were not added: the available safe clock dependency
does not expose that resource API. Whole-process resource counts remain saved but
cannot be attributed to the few milliseconds of measured replay.

Keep the root-reuse patch isolated. Before another acceptance matrix, the useful
next diagnostic is memory-locality/CPU profiling of path replays, with a fixed
budget and explicit resource scope. Avoid further unchanged timing reruns or an
algorithm patch based solely on fluctuating medians. Any platform profiler should
be run separately from the uninstrumented benchmark and preserve cache/warmup
semantics. No core integration or competitor ranking update is made here.

Reproduce: `python3 build.py`, then in a new result directory use the saved
collection under `caffeinate -is`; analyze with `python3 analyze.py` and
`python3 summarize.py`. Collection refuses to overwrite an existing manifest.
The original pilot and both follow-ups remain intact.
