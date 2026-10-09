# ETT 64-byte tokens: extended reference matrix

## Decision

No cell meets the predeclared runtime regression screen. This supports the candidate on this optimization matrix, not universal improvement. Review remaining workload coverage before integration.

Exact same [candidate and binary pair as the pilot](../2026-10-09-ett-packed-tokens/README.md): four optional token indices encoded with NonZeroUsize, 96→64 bytes per token on this 64-bit target. No join/reroot optimization, page preparation or other candidate is combined. Production ETT remains unchanged.

## Method

304 planned processes; 38 cells; four adjacent pairs/cell with 2/2 balanced order and seed 42 shuffle. All processes run sequentially. The matrix covers sparse path/blocks at 100k/1M with 10/50/90% queries, dense 512 controls and Cogentco 197, each fresh/warmed. It is the full optimization matrix, not all 74 cells or all engines of the competitor ranking. [Protocol](protocol.md).

Changes are `100*(after median/before median-1)`. Negative runtime means improvement. Family summaries are unweighted medians of cell changes, not aggregate throughput. Setup is separate; workload wall includes checking, sampling and timer overhead. Warmed uses an untimed replay on a separate graph; no answer cache/hardware cache flush. Peak RSS is the whole process including trace, allocator retention and harness, not graph-only or token-only memory.

## Family overview

| Family | Cells | Faster medians | Median runtime change | Median RSS change | Median setup change |
|---|---:|---:|---:|---:|---:|
| sparse | 24 | 24 | -18.69% | -18.25% | +4.56% |
| dense | 12 | 12 | -12.53% | +0.03% | -2.54% |
| cogentco | 2 | 2 | -8.60% | +0.00% | -6.61% |

## Every measured cell

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | RSS before MiB | RSS after MiB | RSS change | Setup change | Flag |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| topology-zoo-outages-v1 | 197 | — | fresh | 0.362 | 0.340 | -6.15% | 4/4 | 3.6 | 3.6 | +0.00% | -1.99% | — |
| topology-zoo-outages-v1 | 197 | — | warmed | 0.341 | 0.303 | -11.04% | 4/4 | 3.6 | 3.6 | +0.00% | -11.23% | — |
| dense-bridge-churn-v1 | 512 | 10 | fresh | 344.668 | 299.970 | -12.97% | 4/4 | 12.0 | 12.0 | -0.26% | -2.23% | — |
| dense-bridge-churn-v1 | 512 | 10 | warmed | 344.548 | 300.915 | -12.66% | 4/4 | 12.1 | 12.1 | +0.19% | -2.94% | — |
| dense-bridge-churn-v1 | 512 | 50 | fresh | 192.588 | 168.689 | -12.41% | 4/4 | 12.1 | 12.0 | -0.32% | -3.54% | — |
| dense-bridge-churn-v1 | 512 | 50 | warmed | 192.909 | 167.719 | -13.06% | 4/4 | 12.1 | 12.2 | +0.26% | -2.61% | — |
| dense-bridge-churn-v1 | 512 | 90 | fresh | 38.447 | 33.816 | -12.04% | 4/4 | 12.1 | 12.1 | -0.06% | -0.62% | — |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 38.505 | 33.905 | -11.95% | 4/4 | 12.1 | 12.1 | +0.32% | -1.78% | — |
| redundant-bridge-churn-v1 | 512 | 10 | fresh | 219.810 | 192.353 | -12.49% | 4/4 | 12.0 | 12.0 | -0.26% | -2.46% | — |
| redundant-bridge-churn-v1 | 512 | 10 | warmed | 220.369 | 192.671 | -12.57% | 4/4 | 12.1 | 12.1 | +0.13% | -2.86% | — |
| redundant-bridge-churn-v1 | 512 | 50 | fresh | 125.632 | 110.017 | -12.43% | 4/4 | 12.1 | 12.0 | -0.26% | -2.63% | — |
| redundant-bridge-churn-v1 | 512 | 50 | warmed | 126.448 | 110.358 | -12.72% | 4/4 | 12.1 | 12.2 | +0.32% | -2.24% | — |
| redundant-bridge-churn-v1 | 512 | 90 | fresh | 24.858 | 21.900 | -11.90% | 4/4 | 12.1 | 12.1 | -0.19% | -1.36% | — |
| redundant-bridge-churn-v1 | 512 | 90 | warmed | 24.318 | 20.979 | -13.73% | 4/4 | 12.1 | 12.1 | +0.32% | -4.14% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | fresh | 6.586 | 5.374 | -18.40% | 3/4 | 58.5 | 49.3 | -15.74% | +6.89% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | warmed | 6.325 | 5.190 | -17.94% | 4/4 | 83.7 | 67.7 | -19.14% | +5.35% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | fresh | 6.227 | 4.891 | -21.45% | 4/4 | 58.5 | 49.3 | -15.71% | +6.85% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | warmed | 6.228 | 5.132 | -17.60% | 4/4 | 83.7 | 67.7 | -19.11% | +4.66% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 3.800 | 3.199 | -15.83% | 3/4 | 58.4 | 49.2 | -15.71% | +6.30% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 3.680 | 3.373 | -8.33% | 3/4 | 83.6 | 67.6 | -19.15% | +6.27% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | fresh | 68.648 | 50.783 | -26.02% | 4/4 | 486.1 | 395.3 | -18.67% | +2.02% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | warmed | 66.422 | 51.988 | -21.73% | 4/4 | 689.5 | 586.8 | -14.89% | -0.25% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | fresh | 68.552 | 53.302 | -22.25% | 4/4 | 486.0 | 395.3 | -18.66% | +2.59% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | warmed | 68.762 | 55.707 | -18.99% | 4/4 | 700.4 | 542.9 | -22.49% | +1.29% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 48.185 | 38.415 | -20.28% | 4/4 | 480.8 | 395.3 | -17.79% | +0.84% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 47.007 | 37.429 | -20.38% | 4/4 | 691.9 | 543.4 | -21.45% | +1.19% | — |
| sustained-churn-path-v1 | 100000 | 10 | fresh | 2.826 | 2.542 | -10.06% | 3/4 | 57.0 | 47.8 | -16.13% | +7.68% | — |
| sustained-churn-path-v1 | 100000 | 10 | warmed | 2.446 | 2.214 | -9.48% | 4/4 | 82.2 | 66.1 | -19.48% | +7.94% | — |
| sustained-churn-path-v1 | 100000 | 50 | fresh | 2.578 | 2.332 | -9.57% | 3/4 | 57.0 | 47.8 | -16.16% | +7.56% | — |
| sustained-churn-path-v1 | 100000 | 50 | warmed | 2.356 | 1.861 | -21.01% | 4/4 | 82.2 | 66.2 | -19.47% | +4.46% | — |
| sustained-churn-path-v1 | 100000 | 90 | fresh | 2.006 | 1.838 | -8.36% | 3/4 | 56.9 | 47.7 | -16.13% | +4.88% | — |
| sustained-churn-path-v1 | 100000 | 90 | warmed | 1.923 | 1.666 | -13.37% | 3/4 | 82.1 | 66.1 | -19.48% | +8.73% | — |
| sustained-churn-path-v1 | 1000000 | 10 | fresh | 8.678 | 7.996 | -7.86% | 4/4 | 470.5 | 381.2 | -18.97% | +4.66% | — |
| sustained-churn-path-v1 | 1000000 | 10 | warmed | 17.610 | 7.855 | -55.39% | 3/4 | 602.8 | 520.3 | -13.69% | +1.63% | — |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 18.530 | 8.361 | -54.88% | 4/4 | 423.1 | 366.0 | -13.52% | +2.08% | — |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 8.919 | 6.452 | -27.66% | 4/4 | 628.4 | 516.4 | -17.84% | +2.65% | — |
| sustained-churn-path-v1 | 1000000 | 90 | fresh | 8.478 | 6.098 | -28.08% | 2/4 | 459.5 | 381.2 | -17.03% | +2.72% | — |
| sustained-churn-path-v1 | 1000000 | 90 | warmed | 6.987 | 6.163 | -11.79% | 3/4 | 716.0 | 577.5 | -19.34% | +4.12% | — |

## Limits and preservation

The deterministic token payload saving is 33.33%; it must not replace measured total RSS. Prior A/A studies showed short-path timing variability, and this study does not eliminate it. Four pairs per cell do not establish statistical significance or equivalence. Preserve flags even where memory improves. No data are pooled with pilot/history; no outliers removed. Operation totals, p50, p95, p99, ranges and each paired delta remain in [comparison.json](comparison.json); percentiles are not pooled.

Fixed operation count changes the mutated fraction as graphs grow. Cogentco is a real topology with synthetic outages, not a fraud-detection benchmark. No competitor superiority can be inferred from this two-binary study.

## Validation

Complete cells: 38/38; failed processes: 0. Trace fingerprints, oracle answers, operation counts and paired ETT counters are checked. [Audit](audit.json) checks frozen sources, exact pilot binary hashes, measured artifacts and balanced order. The candidate already passed full workspace formatting, Clippy, tests/doctests and Rustdoc in [pilot verification](../2026-10-09-ett-packed-tokens/verification.json). No new Rust changes were made for this collection.

[Assessment](assessment.json) retains all flags. [Patch inventory](../../docs/experiments/2026-10-06-hdt-candidates.md) preserves this candidate independently of temporary builds. No staging, commit or push was performed.

## Integration recommendation

This matrix supports reviewing the isolated packed ETT representation for
integration: all 38 runtime medians improve and all 24 sparse peak-RSS medians
fall. Retain the sparse setup tradeoff (median cell change +4.56%, maximum
+8.73%) and individual adverse pairs. Large gains on short path replays remain
sensitive to timing variability; four pairs do not establish tail guarantees.
Keep the experimental engine status and default unchanged. No integration is
performed by this measurement campaign.
