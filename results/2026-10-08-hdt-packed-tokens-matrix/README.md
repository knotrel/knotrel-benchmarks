# HDT 64-byte tokens: extended reference matrix

## Decision

1 cells meet the predeclared runtime regression screen. Retain the candidate separately and investigate them before integration. Memory improvements must not hide runtime regressions.

Exact same [candidate and binary pair as the pilot](../2026-10-08-hdt-packed-tokens/README.md): four optional token indices encoded with NonZeroUsize, 96→64 bytes per token on this 64-bit target. No join/reroot optimization, page preparation or other candidate is combined. Production core remains unchanged.

## Practical findings

Runtime medians improve in 33 of 38 cells. All 12 block cells improve by
6.57%–10.48%, with 47/48 faster pairs. Their median cell change is -8.14%.
All six 100k path cells also improve, each with four faster pairs. Dense controls
improve in 11/12 cells; both Cogentco medians improve.

RSS medians decrease in all 24 large sparse cells, by 6.51%–22.31% (median cell
change -14.19%). Dense RSS is effectively flat (median +0.085%, range -0.51% to
+0.46%); Cogentco is unchanged. Setup is not universally improved: median cell
changes are +1.98% sparse, +1.16% dense and -3.18% Cogentco.

One cell meets the regression screen: path1M,q50,fresh rises from 9.096 ms to
19.999 ms (+119.85%), with three slower pairs. The four paired changes are
+23.07%, -58.91%, +746.82% and +195.77%; before samples span 6.80–21.40 ms and
after samples 8.79–57.56 ms. This variability does not justify discarding the
regression. Its cause is unresolved.

Other median slowdowns also remain visible: path1M,q90,warmed +28.61% (two slower
pairs), path1M,q90,fresh +6.28% (one slower pair), path1M,q10,fresh +2.65%, and a
dense redundant-bridge control +1.46%. The engineering screen flags only one cell;
that is not a claim that only one cell slowed down.

Memory evidence is consistently favorable at scale, but general integration
remains premature. The next bounded diagnostic should compare resource counters
for baseline and packed tokens on the flagged path1M,q50,fresh trace, separating
setup from replay and retaining the same representation change. Previous memory
findings used another trace and cannot establish this case's cause. Do not combine
with promotion-join changes or discard adverse measurements.

## Method

304 planned processes; 38 cells; four adjacent pairs/cell with 2/2 balanced order and seed 42 shuffle. All processes run sequentially. The matrix covers sparse path/blocks at 100k/1M with 10/50/90% queries, dense 512 controls and Cogentco 197, each fresh/warmed. It is the full optimization matrix, not all 74 cells or all engines of the competitor ranking. [Protocol](protocol.md).

Changes are `100*(after median/before median-1)`. Negative runtime means improvement. Family summaries are unweighted medians of cell changes, not aggregate throughput. Setup is separate; workload wall includes checking, sampling and timer overhead. Warmed uses an untimed replay on a separate graph; no answer cache/hardware cache flush. Peak RSS is the whole process including trace, allocator retention and harness, not graph-only or token-only memory.

## Family overview

| Family | Cells | Faster medians | Median runtime change | Median RSS change | Median setup change |
|---|---:|---:|---:|---:|---:|
| sparse | 24 | 20 | -8.69% | -14.19% | +1.98% |
| dense | 12 | 11 | -3.22% | +0.09% | +1.16% |
| cogentco | 2 | 2 | -5.45% | +0.00% | -3.18% |

## Every measured cell

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | RSS before MiB | RSS after MiB | RSS change | Setup change | Flag |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| topology-zoo-outages-v1 | 197 | — | fresh | 0.510 | 0.471 | -7.68% | 4/4 | 3.6 | 3.6 | +0.00% | -0.89% | — |
| topology-zoo-outages-v1 | 197 | — | warmed | 0.439 | 0.425 | -3.22% | 3/4 | 3.6 | 3.6 | +0.00% | -5.46% | — |
| dense-bridge-churn-v1 | 512 | 10 | fresh | 8.990 | 8.924 | -0.73% | 2/4 | 13.7 | 13.7 | +0.29% | +0.41% | — |
| dense-bridge-churn-v1 | 512 | 10 | warmed | 8.746 | 8.427 | -3.64% | 3/4 | 13.8 | 13.7 | -0.06% | +3.70% | — |
| dense-bridge-churn-v1 | 512 | 50 | fresh | 8.696 | 8.691 | -0.06% | 1/4 | 13.7 | 13.7 | +0.17% | +1.50% | — |
| dense-bridge-churn-v1 | 512 | 50 | warmed | 8.833 | 8.559 | -3.11% | 4/4 | 13.8 | 13.8 | -0.23% | +0.95% | — |
| dense-bridge-churn-v1 | 512 | 90 | fresh | 8.628 | 8.487 | -1.63% | 2/4 | 13.7 | 13.7 | +0.46% | -1.16% | — |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.565 | 7.965 | -7.02% | 4/4 | 13.8 | 13.8 | +0.06% | -0.13% | — |
| redundant-bridge-churn-v1 | 512 | 10 | fresh | 9.068 | 8.699 | -4.07% | 3/4 | 13.6 | 13.7 | +0.29% | +1.37% | — |
| redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.737 | 8.573 | -1.88% | 3/4 | 13.8 | 13.7 | -0.51% | +0.18% | — |
| redundant-bridge-churn-v1 | 512 | 50 | fresh | 8.824 | 8.449 | -4.26% | 4/4 | 13.7 | 13.7 | +0.11% | +1.49% | — |
| redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.365 | 8.487 | +1.46% | 2/4 | 13.8 | 13.8 | -0.23% | +2.64% | — |
| redundant-bridge-churn-v1 | 512 | 90 | fresh | 8.730 | 8.340 | -4.46% | 4/4 | 13.7 | 13.7 | +0.23% | -0.63% | — |
| redundant-bridge-churn-v1 | 512 | 90 | warmed | 8.236 | 7.962 | -3.33% | 3/4 | 13.8 | 13.8 | -0.11% | +1.99% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | fresh | 324.562 | 295.610 | -8.92% | 4/4 | 293.4 | 234.8 | -19.96% | +4.64% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | warmed | 309.684 | 289.342 | -6.57% | 4/4 | 302.3 | 234.8 | -22.31% | +9.44% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | fresh | 337.699 | 310.209 | -8.14% | 4/4 | 276.5 | 231.0 | -16.45% | +2.60% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | warmed | 332.689 | 305.628 | -8.13% | 4/4 | 277.7 | 241.2 | -13.15% | +4.41% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 221.459 | 203.603 | -8.06% | 4/4 | 204.5 | 170.0 | -16.87% | +4.54% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 219.826 | 200.842 | -8.64% | 4/4 | 206.8 | 183.0 | -11.51% | +3.81% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | fresh | 4922.414 | 4448.139 | -9.64% | 4/4 | 1970.4 | 1822.5 | -7.50% | -0.26% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | warmed | 4872.330 | 4549.806 | -6.62% | 4/4 | 2163.4 | 1923.6 | -11.08% | -9.70% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | fresh | 4895.615 | 4382.360 | -10.48% | 4/4 | 1715.6 | 1532.7 | -10.66% | -1.96% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | warmed | 4552.449 | 4238.202 | -6.90% | 4/4 | 2076.7 | 1911.1 | -7.97% | -0.42% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3496.112 | 3190.291 | -8.75% | 3/4 | 1578.9 | 1421.0 | -10.00% | -1.15% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3407.283 | 3182.779 | -6.59% | 4/4 | 1593.6 | 1489.9 | -6.51% | -0.25% | — |
| sustained-churn-path-v1 | 100000 | 10 | fresh | 3.195 | 2.597 | -18.71% | 4/4 | 80.8 | 69.4 | -14.11% | +6.80% | — |
| sustained-churn-path-v1 | 100000 | 10 | warmed | 3.073 | 2.501 | -18.61% | 4/4 | 107.4 | 87.8 | -18.21% | +1.08% | — |
| sustained-churn-path-v1 | 100000 | 50 | fresh | 3.143 | 2.498 | -20.54% | 4/4 | 80.8 | 69.3 | -14.18% | +3.81% | — |
| sustained-churn-path-v1 | 100000 | 50 | warmed | 2.662 | 2.214 | -16.83% | 4/4 | 107.5 | 87.8 | -18.30% | +8.21% | — |
| sustained-churn-path-v1 | 100000 | 90 | fresh | 2.265 | 1.760 | -22.27% | 4/4 | 80.8 | 69.4 | -14.09% | +3.72% | — |
| sustained-churn-path-v1 | 100000 | 90 | warmed | 2.230 | 1.678 | -24.75% | 4/4 | 107.5 | 87.9 | -18.25% | +4.93% | — |
| sustained-churn-path-v1 | 1000000 | 10 | fresh | 8.124 | 8.339 | +2.65% | 1/4 | 685.6 | 588.1 | -14.22% | -2.25% | — |
| sustained-churn-path-v1 | 1000000 | 10 | warmed | 8.482 | 7.127 | -15.98% | 3/4 | 685.6 | 588.1 | -14.22% | -0.99% | — |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 9.096 | 19.999 | +119.85% | 1/4 | 634.0 | 553.6 | -12.68% | +3.36% | investigate |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 6.406 | 5.585 | -12.81% | 3/4 | 684.6 | 587.3 | -14.21% | +0.98% | — |
| sustained-churn-path-v1 | 1000000 | 90 | fresh | 4.944 | 5.255 | +6.28% | 3/4 | 685.0 | 587.7 | -14.20% | -0.91% | — |
| sustained-churn-path-v1 | 1000000 | 90 | warmed | 5.707 | 7.340 | +28.61% | 2/4 | 684.9 | 587.6 | -14.20% | +1.36% | — |

## Limits and preservation

The deterministic token payload saving is 33.33%; it must not replace measured total RSS. Prior A/A studies showed short-path timing variability, and this study does not eliminate it. Four pairs per cell do not establish statistical significance or equivalence. Preserve flags even where memory improves. No data are pooled with pilot/history; no outliers removed. Operation totals, p50, p95, p99, ranges and each paired delta remain in [comparison.json](comparison.json); percentiles are not pooled.

Fixed operation count changes the mutated fraction as graphs grow. Cogentco is a real topology with synthetic outages, not a fraud-detection benchmark. No competitor superiority can be inferred from this two-binary study.

## Validation

Complete cells: 38/38; failed processes: 0. Trace fingerprints, oracle answers, operation counts and paired HDT counters are checked. [Audit](audit.json) checks frozen sources, exact pilot binary hashes, measured artifacts and balanced order. The candidate already passed full workspace formatting, Clippy, tests/doctests and Rustdoc in [pilot verification](../2026-10-08-hdt-packed-tokens/reconstruction-verification.json). No new Rust changes were made for this collection.

[Assessment](assessment.json) retains all flags. [Patch inventory](../../docs/experiments/2026-10-06-hdt-candidates.md) preserves this candidate independently of temporary builds. No staging, commit or push was performed.

Analysis and report finalized on 2026-10-09; the result directory retains the study start date. Individual run timestamps are preserved.
