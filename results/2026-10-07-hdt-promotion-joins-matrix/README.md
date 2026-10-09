# HDT promotion-only joins: extended reference comparison

## Decision

7 cells meet the predeclared regression-investigation screen. Keep the patch isolated; investigate those cells before integration.

The exact [pilot candidate](../2026-10-07-hdt-promotion-joins/README.md) and frozen binaries are reused. Production core remains unchanged. This follow-up is separate from the pilot; samples are not pooled.

## Practical findings and next diagnostic

All 12 block cells improve, from -7.03% to -13.11%, with 46/48 faster pairs.
The median block-cell change is -9.76%. This extends the promotion benefit beyond
the pilot's 90% query load to the 10% and 50% query loads.

The seven investigation flags are six path cells and dense bridge512,q10,warmed
(+5.13%, four slower pairs). Flagged path median changes range from +5.12% to
+28.54%. The same path1M,q50,warmed case that improved in the pilot now worsens
18.62%; keep both observations, do not choose the favorable one.

The algorithmic benefit during promotions remains supported by the pilot's
structural evidence, but absence of a broad regression is not established.
A useful next diagnostic is a bounded A/A control using the same binary plus
inspection of generated code for the ordinary link path. Compare flagged cases
with balanced reruns only after recording that protocol. Unchanged structural
counts on the previously probed path do not rule out compilation/layout effects
or measurement variation, and neither cause has been demonstrated here. Do not
change the candidate or discard outliers merely to obtain a passing screen.

## Coverage and method

304 planned sequential processes; 38 cells; four paired trials per cell, balanced 2/2 execution order. This covers the full optimization reference matrix used for earlier candidates: sparse 100k/1M, dense512 and Cogentco197. It is **not** the complete 74-cell multi-engine competitor ranking or a new competitor benchmark. See [protocol](protocol.md).

Percent change is `100*(after median/before median-1)`; negative is better. Family summaries are unweighted medians of cell changes, not aggregate runtime or throughput. Setup is separate. Runtime includes harness checking and timing overhead. Warmed uses an untimed replay on a separate graph; there is no answer cache or hardware-cache flush. RSS is whole-process peak resident memory.

## Family overview

| Family | Complete cells | Faster medians | Median cell change | Range |
|---|---:|---:|---:|---:|
| sparse | 24 | 17 | -7.10% | -16.30% to +28.54% |
| dense | 12 | 4 | +0.57% | -1.45% to +5.13% |
| cogentco | 2 | 1 | -1.88% | -4.68% to +0.92% |

## Every measured cell

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | Setup change | RSS change | Flag |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| topology-zoo-outages-v1 | 197 | — | fresh | 0.528 | 0.503 | -4.68% | 3/4 | -1.37% | +0.00% | — |
| topology-zoo-outages-v1 | 197 | — | warmed | 0.442 | 0.446 | +0.92% | 2/4 | +2.93% | +0.00% | — |
| dense-bridge-churn-v1 | 512 | 10 | fresh | 8.874 | 8.950 | +0.85% | 2/4 | -1.44% | -0.06% | — |
| dense-bridge-churn-v1 | 512 | 10 | warmed | 8.569 | 9.009 | +5.13% | 0/4 | -0.36% | -0.17% | investigate |
| dense-bridge-churn-v1 | 512 | 50 | fresh | 8.748 | 8.773 | +0.29% | 1/4 | -0.01% | -0.46% | — |
| dense-bridge-churn-v1 | 512 | 50 | warmed | 8.534 | 8.619 | +0.99% | 2/4 | -1.01% | -0.17% | — |
| dense-bridge-churn-v1 | 512 | 90 | fresh | 8.625 | 8.617 | -0.10% | 2/4 | -0.24% | -0.29% | — |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.402 | 8.563 | +1.92% | 1/4 | -0.19% | +0.11% | — |
| redundant-bridge-churn-v1 | 512 | 10 | fresh | 8.823 | 9.012 | +2.14% | 1/4 | -0.01% | +0.00% | — |
| redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.860 | 8.732 | -1.45% | 4/4 | +1.14% | +0.17% | — |
| redundant-bridge-churn-v1 | 512 | 50 | fresh | 8.670 | 8.681 | +0.13% | 2/4 | -0.78% | -0.06% | — |
| redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.618 | 8.570 | -0.56% | 3/4 | +0.17% | +0.06% | — |
| redundant-bridge-churn-v1 | 512 | 90 | fresh | 8.588 | 8.529 | -0.69% | 2/4 | +3.18% | -0.17% | — |
| redundant-bridge-churn-v1 | 512 | 90 | warmed | 8.270 | 8.407 | +1.66% | 1/4 | +0.14% | +0.17% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | fresh | 327.125 | 297.754 | -8.98% | 4/4 | +0.69% | +0.61% | — |
| sustained-churn-blocks-v1 | 100000 | 10 | warmed | 311.621 | 286.018 | -8.22% | 4/4 | +0.81% | +0.77% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | fresh | 334.089 | 310.590 | -7.03% | 4/4 | +3.33% | +1.10% | — |
| sustained-churn-blocks-v1 | 100000 | 50 | warmed | 324.877 | 295.466 | -9.05% | 4/4 | +0.23% | +1.02% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 213.916 | 193.823 | -9.39% | 4/4 | +0.20% | +1.03% | — |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 215.755 | 193.580 | -10.28% | 3/4 | -1.19% | +1.20% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | fresh | 4942.516 | 4313.919 | -12.72% | 4/4 | +1.08% | +1.52% | — |
| sustained-churn-blocks-v1 | 1000000 | 10 | warmed | 4630.509 | 4298.209 | -7.18% | 4/4 | -0.87% | -4.05% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | fresh | 4669.329 | 4191.319 | -10.24% | 3/4 | +0.26% | -10.14% | — |
| sustained-churn-blocks-v1 | 1000000 | 50 | warmed | 4552.123 | 4091.378 | -10.12% | 4/4 | +0.84% | -2.71% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3477.108 | 3037.662 | -12.64% | 4/4 | +0.12% | +4.82% | — |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3330.022 | 2893.381 | -13.11% | 4/4 | +1.89% | +4.81% | — |
| sustained-churn-path-v1 | 100000 | 10 | fresh | 3.358 | 3.242 | -3.45% | 2/4 | -0.14% | +0.00% | — |
| sustained-churn-path-v1 | 100000 | 10 | warmed | 3.008 | 3.162 | +5.12% | 1/4 | +0.37% | +0.00% | investigate |
| sustained-churn-path-v1 | 100000 | 50 | fresh | 2.915 | 2.782 | -4.56% | 3/4 | +0.37% | -0.02% | — |
| sustained-churn-path-v1 | 100000 | 50 | warmed | 2.910 | 3.344 | +14.93% | 1/4 | +1.09% | +0.01% | investigate |
| sustained-churn-path-v1 | 100000 | 90 | fresh | 2.104 | 2.705 | +28.54% | 1/4 | +2.19% | -0.02% | investigate |
| sustained-churn-path-v1 | 100000 | 90 | warmed | 2.136 | 2.003 | -6.21% | 3/4 | +0.80% | +0.00% | — |
| sustained-churn-path-v1 | 1000000 | 10 | fresh | 7.496 | 9.177 | +22.42% | 1/4 | +2.43% | +0.00% | investigate |
| sustained-churn-path-v1 | 1000000 | 10 | warmed | 7.508 | 7.372 | -1.81% | 2/4 | +1.01% | +0.00% | — |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 7.413 | 7.950 | +7.23% | 2/4 | +4.27% | +0.00% | — |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.233 | 6.208 | +18.62% | 1/4 | +1.62% | +0.00% | investigate |
| sustained-churn-path-v1 | 1000000 | 90 | fresh | 4.345 | 5.117 | +17.78% | 1/4 | -0.19% | -0.00% | investigate |
| sustained-churn-path-v1 | 1000000 | 90 | warmed | 5.173 | 4.330 | -16.30% | 1/4 | -1.19% | +0.00% | — |

## Interpretation and limits

All observed slowdowns are retained above. The >5% plus at least three slower pairs rule is an engineering screen, not a confidence interval or statistical significance test. Four pairs are limited evidence; do not attribute noisy differences to a particular hardware cause without measurement.

The pilot structural probes establish less forest work during promotions, and identical counted work on the path1M,q50 control. Timing changes on non-promoting paths must not be advertised as an algorithmic work reduction. This candidate does not change asymptotic HDT bounds or establish superiority over another engine.

[comparison.json](comparison.json) retains before/after medians, ranges, paired deltas and operation totals/p50/p95/p99. Percentiles are not pooled across runs. The fixed operation count as node count grows also changes the mutated fraction. Cogentco is a real topology with synthetic outages, not a fraud-detection workload.

## Validation and artifacts

Completed cells: 38/38; failed processes: 0. Successful runs match reference trace fingerprints and oracle answers; the analyzer checks operation identities and paired HDT counters. [Audit](audit.json) verifies frozen source/binary/artifact hashes and per-cell order. The same candidate already passed full workspace formatting, Clippy, tests/doctests and Rustdoc in the [pilot verification](../2026-10-07-hdt-promotion-joins/reconstruction-verification.json). No new production code was changed for this run.

See [assessment.json](assessment.json) for the machine-readable screen and the [preserved patch inventory](../../docs/experiments/2026-10-06-hdt-candidates.md). No commits or staging changes were made.
