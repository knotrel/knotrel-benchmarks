# ETT scan-root reuse: marker-scoped manual-counter report

## Scope and method

This report analyzes the completed 72-process Apple M4 campaign: 36 adjacent
before/after pairs, with 12 pairs per workload. The primary metric is the
`measurement-replay` `os_signpost` duration. Percentage change is
`100 * (after / before - 1)`, so negative values are faster.

The 95% confidence intervals below are fixed-seed (`1012`), two-sided
percentile bootstrap intervals from 100,000 resamples of the paired percentage
changes. They quantify sampling uncertainty for this 12-pair experiment; they
do not establish a mechanism or predict another host. All 72 traces exited
successfully, all marker intervals validated, and sleep was inhibited during
collection.

## Performance

| Workload | Before median | After median | Median paired change (95% CI) | Mean paired change (95% CI) | Faster / slower |
| --- | ---: | ---: | ---: | ---: | ---: |
| path fresh | 7.40 ms | 7.39 ms | -0.60% (-12.77% to 2.55%) | -2.70% (-8.38% to 3.76%) | 7 / 5 |
| path warmed | 5.43 ms | 5.59 ms | 4.43% (-7.84% to 10.54%) | 1.95% (-3.83% to 7.62%) | 5 / 7 |
| dense warmed | 32.67 ms | 18.22 ms | -44.67% (-45.45% to -42.50%) | -47.55% (-56.41% to -42.00%) | 12 / 0 |

The exact two-sided sign-test p-values are 0.774 for each path workload and
0.000488 for dense warmed. Dense warmed is therefore a stable positive-control
benefit in this experiment. Neither path workload has an interval excluding no
change; fresh is variable and warmed trends slower but remains inconclusive.

### Variability and individual regressions

| Workload | Paired-change IQR | Paired-change range | Individual regressions |
| --- | ---: | ---: | --- |
| path fresh | -12.18% to 1.92% | -15.78% to 23.66% | trials 0: +4.34%, 2: +3.82%, 6: +1.29%, 10: +23.66%, 11: +0.70% |
| path warmed | -7.38% to 10.26% | -14.44% to 18.45% | trials 0: +3.78%, 1: +18.45%, 2: +5.08%, 3: +11.12%, 4: +9.97%, 5: +12.90%, 9: +6.15% |
| dense warmed | -45.39% to -42.57% | -92.34% to -35.06% | none |

The unusually large dense improvement in one pair remains preserved in the
range and mean; the median and its narrow bootstrap interval show that the
direction does not depend on that pair.

## Hardware-counter evidence

The independent mapping probe established that `counters-profile` positions
0–7 map to the configured events and positions 8–15 are an exact duplicate.
All 192,154 nonzero arrays in this campaign passed that duplication check. The
analysis uses only the first eight values.

Counter samples are sparse and uneven: the median count was 32.5 samples
before and 17.5 after for dense warmed. Two dense-after recordings have zero
marker-overlap samples (`b01-g04-dense-warmed-t03-after` and
`b03-g05-dense-warmed-t05-after`), leaving 10 complete counter pairs for that
workload. They remain in the performance analysis. Both path workloads have
24/24 records with counters, but only median 5–7 samples per record.

Consequently, the following are **descriptive changes in per-record
per-sample medians**, not totals of work and not reliable derived metrics:

| Dense-warmed event | Complete pairs | Median descriptive change (95% bootstrap CI) |
| --- | ---: | ---: |
| `FIXED_CYCLES` | 10 | 0.16% (-33.25% to 3.90%) |
| `INST_ALL` | 10 | 0.46% (-33.09% to 5.90%) |
| `BRANCH_MISPRED_NONSPEC` | 10 | -72.71% (-81.99% to -71.09%) |
| `ARM_L1D_CACHE_RD` | 10 | 7.02% (-28.74% to 12.84%) |
| `ARM_L1D_CACHE_LMISS_RD` | 10 | 84.12% (17.13% to 95.65%) |
| `ARM_STALL_BACKEND` | 10 | 22.23% (-19.49% to 27.29%) |

The lower sampled branch-misprediction values are compatible with a
branch-related explanation for dense warmed, but do not establish one: they
are not total branch counts, sample counts differ substantially, and other
events do not present a coherent reduction. In particular, the descriptive
increase in long-latency L1D read misses does not identify page faults or TLB
misses; this template has no TLB event. No IPC, miss rate, cycles per operation,
or total-work estimate is defensible from these per-sample medians.

## Assessment

The scan-root reuse candidate is supported as a **workload-specific dense
warmed optimization** on this Apple M4 experiment. It is not supported as a
general optimization: fresh-path behavior remains variable, and warmed-path
behavior remains inconclusive with several individual regressions. Hardware
evidence supplies a plausible but unproven branch-related hypothesis for the
dense result; it does not establish causality. The candidate should remain
isolated from production until a decision explicitly accepts that narrow scope
or further evidence resolves the path behavior.

The complete machine-readable paired results, bootstrap summaries, counter
coverage, and descriptive event comparisons are in [analysis.json](analysis.json).
