# HDT rank-zero reroot experiment — 2026-10-06

An isolated candidate returns the existing tour when `reroot` computes rank zero, avoiding an unnecessary split/concat. The in-order sequence is already correct, so keeping its AVL structure preserves connectivity, sizes and incidence aggregates. [candidate.patch](candidate.patch) is the only algorithm change between the two builds.

The [structural probe](../2026-10-06-hdt-reroot-probe/results.json) finds 212,366 rank-zero calls among 424,544 promotion reroots at 100k vertices, and 2,279,820 among 4,559,450 at 1M (both block traces, 90% queries). Roughly half the calls qualify, but this does not imply halving runtime: trivial tours already cost little.

## Paired results

38 / 38 cells complete; 0 / 228 processes failed. Each cell uses three sequential pairs. Before/after order alternates globally after a seeded shuffle; per-cell order balance is not enforced. Six initial cells have the same variant first in all three pairs. See [order-audit.json](order-audit.json), including the separate confirmation order counts. Negative runtime change means improvement. Runtime excludes setup; per-operation timing includes timer granularity. Fresh/warmed are separate cells, without hardware-cache flushing.

| Family | Cells | Faster cells | Median of cell changes | Range of cell changes |
|---|---:|---:|---:|---:|
| sparse | 24 | 15 | -0.81% | -14.88% to +11.81% |
| dense | 12 | 5 | +0.78% | -1.47% to +3.21% |
| cogentco | 2 | 1 | -1.35% | -3.02% to +0.32% |

A median of percentage changes describes this selected matrix, not an aggregate throughput gain. Three pairs are a screening experiment, not a confidence interval. Setup, tails and RSS remain separate in [comparison.json](comparison.json). Whole-process RSS includes the trace and harness, not only engine storage.

## Every scenario

| Workload | Vertices | Query mix | Regime | Before ms | After ms | Runtime change | Faster pairs / 3 | Setup change | RSS change |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.494 | 0.496 | +0.32% | 2 | -2.32% | +0.00% |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.441 | 0.428 | -3.02% | 3 | -2.53% | +0.00% |
| dense-bridge-churn-v1 | 512 | 10 | fresh | 8.694 | 8.656 | -0.43% | 1 | +3.07% | -0.57% |
| dense-bridge-churn-v1 | 512 | 10 | warmed | 8.305 | 8.440 | +1.62% | 0 | +2.30% | -0.34% |
| dense-bridge-churn-v1 | 512 | 50 | fresh | 8.547 | 8.473 | -0.86% | 2 | +3.39% | -0.11% |
| dense-bridge-churn-v1 | 512 | 50 | warmed | 8.076 | 8.230 | +1.90% | 0 | +2.11% | -0.34% |
| dense-bridge-churn-v1 | 512 | 90 | fresh | 8.082 | 8.028 | -0.67% | 1 | +3.98% | -0.34% |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 7.961 | 8.045 | +1.05% | 1 | +2.53% | -0.34% |
| redundant-bridge-churn-v1 | 512 | 10 | fresh | 8.888 | 8.757 | -1.47% | 2 | +2.52% | -0.46% |
| redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.345 | 8.448 | +1.23% | 1 | +2.98% | -0.34% |
| redundant-bridge-churn-v1 | 512 | 50 | fresh | 8.679 | 8.598 | -0.94% | 2 | +3.93% | -0.23% |
| redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.209 | 8.251 | +0.52% | 1 | +1.73% | -0.23% |
| redundant-bridge-churn-v1 | 512 | 90 | fresh | 8.354 | 8.457 | +1.23% | 1 | +2.62% | -0.57% |
| redundant-bridge-churn-v1 | 512 | 90 | warmed | 7.902 | 8.156 | +3.21% | 0 | +2.92% | -0.11% |
| sustained-churn-blocks-v1 | 100000 | 10 | fresh | 314.898 | 312.860 | -0.65% | 2 | -2.34% | -0.01% |
| sustained-churn-blocks-v1 | 100000 | 10 | warmed | 309.329 | 307.046 | -0.74% | 3 | -1.71% | +0.59% |
| sustained-churn-blocks-v1 | 100000 | 50 | fresh | 328.991 | 330.194 | +0.37% | 2 | -0.35% | +0.01% |
| sustained-churn-blocks-v1 | 100000 | 50 | warmed | 320.002 | 317.009 | -0.94% | 3 | -0.63% | +0.03% |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 210.889 | 208.758 | -1.01% | 3 | -1.13% | -0.01% |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 214.704 | 213.016 | -0.79% | 3 | -3.57% | -0.09% |
| sustained-churn-blocks-v1 | 1000000 | 10 | fresh | 4792.223 | 4752.147 | -0.84% | 1 | -0.43% | +3.05% |
| sustained-churn-blocks-v1 | 1000000 | 10 | warmed | 4692.191 | 4842.786 | +3.21% | 0 | -0.47% | -1.00% |
| sustained-churn-blocks-v1 | 1000000 | 50 | fresh | 4739.954 | 4615.023 | -2.64% | 2 | -0.59% | -13.44% |
| sustained-churn-blocks-v1 | 1000000 | 50 | warmed | 4479.467 | 4500.196 | +0.46% | 2 | -0.84% | -4.15% |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3361.540 | 3405.087 | +1.30% | 2 | +0.82% | +5.29% |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3296.001 | 3126.508 | -5.14% | 3 | -1.40% | -5.04% |
| sustained-churn-path-v1 | 100000 | 10 | fresh | 3.022 | 2.917 | -3.46% | 2 | -1.74% | -0.02% |
| sustained-churn-path-v1 | 100000 | 10 | warmed | 2.938 | 2.829 | -3.70% | 2 | -1.31% | +0.01% |
| sustained-churn-path-v1 | 100000 | 50 | fresh | 2.513 | 2.720 | +8.24% | 0 | +0.01% | +0.00% |
| sustained-churn-path-v1 | 100000 | 50 | warmed | 2.469 | 2.553 | +3.43% | 1 | +1.31% | +0.00% |
| sustained-churn-path-v1 | 100000 | 90 | fresh | 1.950 | 1.719 | -11.85% | 3 | -2.50% | +0.00% |
| sustained-churn-path-v1 | 100000 | 90 | warmed | 1.919 | 1.778 | -7.31% | 3 | +2.14% | +0.04% |
| sustained-churn-path-v1 | 1000000 | 10 | fresh | 4.894 | 4.847 | -0.96% | 1 | -0.77% | +0.00% |
| sustained-churn-path-v1 | 1000000 | 10 | warmed | 5.879 | 5.004 | -14.88% | 2 | -0.32% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 6.489 | 7.256 | +11.81% | 2 | -2.33% | +0.02% |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.351 | 5.297 | -1.00% | 1 | -2.30% | +0.00% |
| sustained-churn-path-v1 | 1000000 | 90 | fresh | 5.378 | 5.637 | +4.81% | 1 | +1.24% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 90 | warmed | 3.499 | 3.715 | +6.17% | 1 | -1.24% | +0.00% |

## Audit and reproduction

Both optimized binaries were built in the same temporary workspace with the same Cargo configuration and compiler, changing only the HDT forest source. Neither contains the structural probe instrumentation. The temporary copies omit the toolchain pin files; the effective compiler was independently verified after building as the same Rust 1.98.1 (see source-isolation-audit.json). All Rust/Cargo files match the preserved snapshot except the candidate forest. Build commands, relevant build environment and binary hashes are in [builds.json](builds.json); complete original source hashes point to the preserved current-ranking snapshot. The candidate core passed its unit/integration tests and doctests before measurement; [candidate-tests.txt](candidate-tests.txt) retains the output.

Commands and all raw results are in [manifest.json](manifest.json). Every successful replay checks the workload oracle. Analysis verifies artifact hashes, trace fingerprints, actual mutation/query counts and answer counts, and equal HDT counters between paired variants. Collection preserves failures; incomplete cells are not ranked. Production sources were unchanged throughout collection.

Reproduce in a new destination by running build.py, collect.py, analyze.py, then report.py and order-audit.py. Build and final collection outputs refuse overwrite. The preserved [five-engine ranking](../2026-10-06-engine-ranking/README.md) and [promotion diagnosis](../2026-10-06-hdt-blocks-profile/README.md) remain reference results. See [decision.md](decision.md) for the decision after reviewing this experiment.
