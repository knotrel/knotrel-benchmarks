# ETT scan-root marker-scoped CPU Counters on Apple M4 — 2026-10-12

This is the replay-scoped successor to the whole-process feasibility campaign
and the successful safe signpost validation. The [protocol](protocol.md)
predeclares 72 trace recordings: twelve balanced adjacent before/after pairs
for each priority workload.

[plan.py](plan.py) creates the immutable seeded order. [collect.py](collect.py)
records one of six fixed batches and exports marker, counter, metric, and
thread-activity data. [analyze.py](analyze.py) accepts only samples overlapping
the `measurement-replay` marker for replay-scoped reporting.

## Collection validity

All 72 predeclared recordings completed successfully. All target processes
emitted the expected marker sequence: one `measurement-replay` interval for
fresh runs, and non-overlapping `warmup-replay` then `measurement-replay`
intervals for warmed runs. Temporary `caffeinate -is` was visible during every
recording. The six saved power-log intervals contain no `Sleep`, `Wake`, or
`DarkWake` event.

The first batch's collector metadata labels its two fresh pairs invalid because
the original parser required a warmup marker unconditionally. The saved XML
shows the correct fresh sequence; [analyze.py](analyze.py) classifies it from
the raw exported marker rows without rerunning any trace.

## Paired replay wall time

Negative values improve the candidate. Variant medians and paired medians are
reported separately because the path distribution is variable.

| Case | Before median | After median | Variant-median change | Paired median change | Faster pairs | Paired range |
|---|---:|---:|---:|---:|---:|---:|
| Path 1M, 50%, fresh | 7.186 ms | 7.295 ms | +1.53% | +8.80% | 4/12 | −11.89% to +28.88% |
| Path 1M, 50%, warmed | 5.660 ms | 5.543 ms | −2.06% | +0.07% | 6/12 | −67.13% to +94.59% |
| Dense bridge 512, 90%, warmed | 32.005 ms | 17.760 ms | −44.51% | −44.53% | 12/12 | −48.40% to −42.92% |

The dense positive control reproduces its expected benefit, with a tight
all-favorable distribution. The path distribution is strongly variable on this
host. Fresh has an unfavorable paired median, while warmed has a near-zero
paired median but extreme favorable and unfavorable observations. This
reproduces **variability**, not a stable path speedup or a stable path
regression.

## Marker-scoped counters and scheduling observations

`CounterMetricByThread` rows overlap every marked measurement interval:

| Case | Before rows per replay, median (range) | After rows per replay, median (range) |
|---|---:|---:|
| Path fresh | 15.5 (8–21) | 16.0 (9–37) |
| Path warmed | 12.0 (6–25) | 13.5 (3–32) |
| Dense warmed | 63.0 (40–89) | 34.0 (23–44) |

The dense row-count reduction is compatible with its shorter replay, but is
not a cache-miss, instruction, cycle, or stall attribution. CPU Counters
exported raw `uint64-array` values without an event-definition table that
unambiguously maps each element to a hardware event. Those raw arrays are
retained externally and are deliberately not converted into named metrics.

Counter rows observed both P and E cores in every path variant. The median
number of observed core-label transitions within a replay was 6.0 before and
5.5 after for fresh path, and 4.0 for both warmed variants. Core sampling
therefore does not distinguish the candidate as a source of the path
variability. It also does not prove thread migration: CPU Counters samples
intervals rather than a complete scheduler history.

No marker-scoped page-fault, allocator, frequency, thermal/energy, named
instruction, named cycle, cache-miss, TLB-miss, or memory-stall metric was
exported with a verified definition. Existing replay-local CPU-time diagnosis
remains separate evidence; this campaign neither overrides it nor infers
causation from wall time.

## Decision and artifacts

The ETT scan-root candidate remains isolated. The marker-scoped collection
strengthens the dense benefit and confirms path variability, but it does not
identify a causal hardware mechanism or satisfy an integration gate.

[analysis.json](analysis.json) retains all 36 pairs, marker intervals,
counter-row distributions, core labels, process hashes, and failure flags.
The safe-wrapper build provenance and full verification are in
[the marker-validation result](../2026-10-12-ett-signpost-validation-m4/README.md).

The 72 raw `.trace` bundles and bulky exported counter/activity tables are
outside Git at:

`/Users/robertotrunfio/.copilot/session-state/38a24407-0788-43b6-9112-59903987563b/files/ett-hardware-profile-m4-signposted-raw`

Each batch records their hashes and exact location. Set the artifact root in
the analysis environment only when independently reprocessing the raw exports.
