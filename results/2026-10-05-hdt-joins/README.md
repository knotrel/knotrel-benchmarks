# HDT direct joins — paired before/after

Knotrel's experimental HDT forest now links two tours with two direct AVL joins,
using the newly allocated directed edge tokens as pivots. Previously it used
three concatenations, each splitting a tour to obtain a pivot. Both constructions
preserve the sequence `left, ab, right, ba`, stable handles, incidence flags,
vertex counts and logarithmic worst-case link complexity. AVL shape can differ,
which may change marked-vertex traversal and replacement selection. This is
Knotrel versus its previous implementation, not a comparison with an external
product. Default engine and public configuration remain unchanged.

## Protocol

All 136 HDT reference cases from the preserved October 4 sparse, dense, repeated
query and Cogentco campaigns were run on both frozen executables: 272 processes,
66 scenario cells, two trials per synthetic cell and four per Cogentco cell.
Order is shuffled with seed 42; adjacent before/after order alternates. Each
process validates expected query and mutation results; every trace fingerprint
matches its historical reference. Work counters are recorded, not required to
match, because forest shape may affect edge selection.

Before includes the previously accepted local-ID reuse. Both variants retain
engine identity `knotrel-core/hdt-sparse-levels-v3`; identify them through manifest
variant and binary hashes. Manifest snapshots capture source hashes, revisions,
build commands and Rust/Cargo environment variables. `core-after.patch` preserves
the change. Runtime checkout metadata is not the source identity of the frozen
before executable. No answer cache is introduced. Fresh means no deliberate
warmup, warmed means one untimed replay on another fresh graph; hardware caches
are not flushed. Whole-process peak RSS includes setup, validation and traces.

## Results

Delta is `100 * (after / before - 1)`: negative is lower cost. Baseline timings
come from this paired collection, not the historical campaign. Full operation
p50/p95/p99, totals, setup, RSS, sample ranges and historical drift are retained
in `comparison.json`. Percentiles are medians of per-process percentiles, not
pooled samples. Small trial counts do not establish statistical significance.

HDT work counters differ in **0/136 paired cases**.

| Family | Lower runtime / cells | Runtime delta range | Median cell delta |
|---|---:|---:|---:|
| sparse | 26/36 | -45.54% to +161.15% | -14.42% |
| dense | 22/24 | -35.14% to +289.20% | -4.20% |
| repeats | 3/4 | -27.70% to +0.82% | -17.01% |
| cogentco | 2/2 | -12.25% to -9.65% | -10.95% |

Cell counts are descriptive, not a production-weighted score.

| Family / workload | Nodes | Query % | Regime | Before ms | After ms | Runtime delta | Cut p95 delta | RSS delta |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| cogentco / topology-zoo-outages-v1 | 197 | None | fresh | 0.540 | 0.488 | -9.65% | -18.05% | +0.54% |
| cogentco / topology-zoo-outages-v1 | 197 | None | warmed | 0.493 | 0.433 | -12.25% | -24.60% | +0.00% |
| dense / dense-bridge-churn-v1 | 128 | 10 | fresh | 1.300 | 0.843 | -35.14% | -33.31% | -0.43% |
| dense / dense-bridge-churn-v1 | 128 | 10 | warmed | 0.907 | 0.901 | -0.70% | +7.76% | +0.32% |
| dense / dense-bridge-churn-v1 | 128 | 50 | fresh | 0.810 | 0.650 | -19.74% | -10.71% | +0.00% |
| dense / dense-bridge-churn-v1 | 128 | 50 | warmed | 0.807 | 0.717 | -11.12% | +11.11% | -0.11% |
| dense / dense-bridge-churn-v1 | 128 | 90 | fresh | 0.658 | 0.559 | -15.13% | -6.23% | -0.32% |
| dense / dense-bridge-churn-v1 | 128 | 90 | warmed | 0.583 | 0.538 | -7.85% | +22.97% | -0.32% |
| dense / dense-bridge-churn-v1 | 512 | 10 | fresh | 9.089 | 8.745 | -3.79% | +9.45% | +1.03% |
| dense / dense-bridge-churn-v1 | 512 | 10 | warmed | 9.399 | 9.149 | -2.66% | +18.67% | -0.06% |
| dense / dense-bridge-churn-v1 | 512 | 50 | fresh | 9.271 | 8.958 | -3.37% | +3.20% | -0.17% |
| dense / dense-bridge-churn-v1 | 512 | 50 | warmed | 8.807 | 8.655 | -1.73% | +6.22% | +0.17% |
| dense / dense-bridge-churn-v1 | 512 | 90 | fresh | 8.797 | 8.489 | -3.50% | +20.03% | +0.00% |
| dense / dense-bridge-churn-v1 | 512 | 90 | warmed | 8.799 | 8.427 | -4.23% | +8.33% | +0.00% |
| dense / redundant-bridge-churn-v1 | 128 | 10 | fresh | 0.928 | 0.800 | -13.75% | -15.60% | +0.11% |
| dense / redundant-bridge-churn-v1 | 128 | 10 | warmed | 0.928 | 0.864 | -6.89% | -12.49% | -0.32% |
| dense / redundant-bridge-churn-v1 | 128 | 50 | fresh | 0.762 | 0.653 | -14.27% | -14.79% | -0.11% |
| dense / redundant-bridge-churn-v1 | 128 | 50 | warmed | 0.794 | 0.688 | -13.30% | -17.21% | +0.21% |
| dense / redundant-bridge-churn-v1 | 128 | 90 | fresh | 0.609 | 0.581 | -4.62% | -10.29% | +0.11% |
| dense / redundant-bridge-churn-v1 | 128 | 90 | warmed | 0.555 | 0.542 | -2.38% | -6.22% | +0.21% |
| dense / redundant-bridge-churn-v1 | 512 | 10 | fresh | 9.031 | 9.037 | +0.07% | -13.43% | -0.06% |
| dense / redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.821 | 8.351 | -5.32% | -12.69% | +0.28% |
| dense / redundant-bridge-churn-v1 | 512 | 50 | fresh | 8.900 | 8.612 | -3.24% | -10.12% | +0.23% |
| dense / redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.343 | 7.995 | -4.18% | -6.60% | -0.11% |
| dense / redundant-bridge-churn-v1 | 512 | 90 | fresh | 9.390 | 36.546 | +289.20% | -3.83% | -0.90% |
| dense / redundant-bridge-churn-v1 | 512 | 90 | warmed | 8.583 | 8.513 | -0.81% | +0.02% | +0.23% |
| repeats / sustained-churn-blocks-v1 | 10000 | 90 | fresh | 24.322 | 17.586 | -27.70% | -29.26% | +0.67% |
| repeats / sustained-churn-blocks-v1 | 10000 | 90 | warmed | 23.181 | 17.271 | -25.49% | -26.77% | -0.06% |
| repeats / sustained-churn-path-v1 | 10000 | 90 | fresh | 0.837 | 0.844 | +0.82% | -10.37% | -0.57% |
| repeats / sustained-churn-path-v1 | 10000 | 90 | warmed | 0.558 | 0.510 | -8.53% | -31.18% | +0.28% |
| sparse / sustained-churn-blocks-v1 | 1024 | 10 | fresh | 8.986 | 4.893 | -45.54% | -52.79% | +0.21% |
| sparse / sustained-churn-blocks-v1 | 1024 | 10 | warmed | 3.554 | 3.073 | -13.54% | -9.62% | +0.11% |
| sparse / sustained-churn-blocks-v1 | 1024 | 50 | fresh | 3.037 | 2.561 | -15.69% | -19.25% | +0.54% |
| sparse / sustained-churn-blocks-v1 | 1024 | 50 | warmed | 2.772 | 2.381 | -14.10% | -20.57% | -0.21% |
| sparse / sustained-churn-blocks-v1 | 1024 | 90 | fresh | 2.078 | 1.592 | -23.39% | -24.97% | +0.11% |
| sparse / sustained-churn-blocks-v1 | 1024 | 90 | warmed | 1.986 | 1.474 | -25.80% | -29.00% | -0.11% |
| sparse / sustained-churn-blocks-v1 | 10000 | 10 | fresh | 38.984 | 30.144 | -22.67% | -24.69% | +0.06% |
| sparse / sustained-churn-blocks-v1 | 10000 | 10 | warmed | 35.892 | 27.533 | -23.29% | -23.88% | +0.66% |
| sparse / sustained-churn-blocks-v1 | 10000 | 50 | fresh | 36.477 | 28.360 | -22.25% | -26.33% | +0.27% |
| sparse / sustained-churn-blocks-v1 | 10000 | 50 | warmed | 36.002 | 28.220 | -21.61% | -24.54% | -1.93% |
| sparse / sustained-churn-blocks-v1 | 10000 | 90 | fresh | 25.455 | 18.605 | -26.91% | -28.78% | +0.24% |
| sparse / sustained-churn-blocks-v1 | 10000 | 90 | warmed | 23.211 | 17.116 | -26.26% | -26.77% | +0.62% |
| sparse / sustained-churn-blocks-v1 | 100000 | 10 | fresh | 456.796 | 350.083 | -23.36% | -24.45% | +0.38% |
| sparse / sustained-churn-blocks-v1 | 100000 | 10 | warmed | 455.957 | 337.348 | -26.01% | -29.77% | +0.21% |
| sparse / sustained-churn-blocks-v1 | 100000 | 50 | fresh | 468.264 | 348.980 | -25.47% | -28.35% | +0.35% |
| sparse / sustained-churn-blocks-v1 | 100000 | 50 | warmed | 528.408 | 339.270 | -35.79% | -34.35% | +0.04% |
| sparse / sustained-churn-blocks-v1 | 100000 | 90 | fresh | 308.792 | 224.415 | -27.32% | -28.89% | +0.11% |
| sparse / sustained-churn-blocks-v1 | 100000 | 90 | warmed | 334.458 | 285.133 | -14.75% | -17.82% | -1.02% |
| sparse / sustained-churn-path-v1 | 1024 | 10 | fresh | 0.558 | 0.513 | -8.00% | +0.00% | -0.32% |
| sparse / sustained-churn-path-v1 | 1024 | 10 | warmed | 0.489 | 0.477 | -2.55% | +5.24% | -0.21% |
| sparse / sustained-churn-path-v1 | 1024 | 50 | fresh | 0.408 | 1.065 | +161.15% | +93.65% | +0.43% |
| sparse / sustained-churn-path-v1 | 1024 | 50 | warmed | 0.360 | 0.356 | -1.19% | +0.06% | -0.43% |
| sparse / sustained-churn-path-v1 | 1024 | 90 | fresh | 0.246 | 0.209 | -14.78% | -12.86% | +0.11% |
| sparse / sustained-churn-path-v1 | 1024 | 90 | warmed | 0.195 | 0.232 | +19.09% | +17.56% | -0.21% |
| sparse / sustained-churn-path-v1 | 10000 | 10 | fresh | 1.153 | 1.183 | +2.59% | -3.00% | -0.07% |
| sparse / sustained-churn-path-v1 | 10000 | 10 | warmed | 1.143 | 0.887 | -22.42% | -22.58% | -0.42% |
| sparse / sustained-churn-path-v1 | 10000 | 50 | fresh | 0.758 | 0.782 | +3.14% | -0.03% | +0.07% |
| sparse / sustained-churn-path-v1 | 10000 | 50 | warmed | 0.827 | 1.235 | +49.32% | +43.85% | -0.14% |
| sparse / sustained-churn-path-v1 | 10000 | 90 | fresh | 0.534 | 0.582 | +9.14% | +24.82% | +0.00% |
| sparse / sustained-churn-path-v1 | 10000 | 90 | warmed | 0.376 | 0.359 | -4.57% | -10.44% | +0.00% |
| sparse / sustained-churn-path-v1 | 100000 | 10 | fresh | 3.154 | 3.417 | +8.36% | +4.03% | -0.02% |
| sparse / sustained-churn-path-v1 | 100000 | 10 | warmed | 3.518 | 3.727 | +5.96% | +10.45% | -0.01% |
| sparse / sustained-churn-path-v1 | 100000 | 50 | fresh | 4.076 | 6.132 | +50.42% | +53.73% | +0.47% |
| sparse / sustained-churn-path-v1 | 100000 | 50 | warmed | 3.454 | 4.329 | +25.34% | +18.69% | +0.01% |
| sparse / sustained-churn-path-v1 | 100000 | 90 | fresh | 2.945 | 2.768 | -6.02% | -2.70% | -0.01% |
| sparse / sustained-churn-path-v1 | 100000 | 90 | warmed | 2.621 | 2.456 | -6.29% | -1.43% | +0.01% |

## Reproduction

From the benchmark repository, `build.py before` and `build.py after` freeze the
respective checked-out sources into `/private/tmp/knotrel-hdt-joins`; execute
before building/modifying the next variant. `collect.py` requires those snapshots
and the Cogentco trace at its documented temporary path. Use a new result
directory for every collection; existing manifests are never overwritten.
Run `compare.py`, then `report.py` to regenerate this table and audit. Raw trace
exports and binaries are local/ignored; reconstruct the source with recorded
revisions and patch. The original source trace import provenance remains in the
reference Cogentco campaign. Keep the
[before/after policy](../../docs/experiments/2026-10-04-before-after-policy.md).

## Acceptance and validation

The [48-process adaptive confirmation](../2026-10-05-hdt-joins-confirmation/README.md)
repeats all six cells with initial runtime regression above 15%, four new paired
trials each. The +161% and +289% outliers do not reproduce, but warmed 100k path /
50% queries remains **11.62% slower**. Original and confirmation measurements are
kept separate. Total experimental processes: **320**.

Retain the direct-join change in the experimental HDT backend: warmed 100k cyclic
blocks improve by 26.01%, 35.79% and 14.75% for 10%, 50%, 90% queries in the full
campaign; Cogentco improves by 9.65–12.25%. This is not a universal improvement,
and the confirmed path regression remains a follow-up target. Default engine
selection is unchanged. The work counters happen to match in every paired run,
so measured differences here are not explained by fewer promotions/candidates.

Formatting, all-target Clippy with warnings denied, full workspace tests and
doctests, and Rustdoc with warnings denied passed in both repositories; four
Python adapter tests passed. Existing forest tests validate rotations, repeated
cut/relink, reversed endpoints, recycled tokens, sizes and both candidate marks.
Independent read-only review found no correctness issue. This is a refactoring
with unchanged semantics; the existing invariant suite was run before and after.
