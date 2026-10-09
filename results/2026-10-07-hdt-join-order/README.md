# HDT right-associated tour joins

## Decision

Keep the candidate isolated. The predeclared pilot gate **failed** because of the
path control, despite all four block cells qualifying. Do not expand to the full
38-cell matrix or integrate this variant on this evidence. The adaptive path
follow-up does not override the gate and is not pooled with the pilot.

## Change and correctness

The saved [patch](candidate.patch) changes only the association of two AVL joins
in `Forest::link`: `(left + ab + right) + ba` becomes `left + ab + (right + ba)`.
The exact cyclic sequence is preserved, but tree shape can change. The operation
remains logarithmic. None of the earlier candidate patches is combined here.
Explicit cyclic-order/aggregate tests pass on both variants, including repeated
cut/relink and recycled tokens; the candidate also passes core tests/doctests.
Full sources, compiler metadata, binary hashes and tests are preserved alongside
this report. Production core code is unchanged; this patch is saved, not committed.

## Initial pilot

64 sequential processes, eight cells, four pairs per cell, balanced 2/2 execution
order. See [protocol](protocol.md), [comparison](comparison.json), and
[gate](gate.json). Negative change means less median workload wall runtime;
percentage is `100 * (after median / before median - 1)`, not the median of
pairwise percentages. Pair counts are shown separately.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs |
|---|---:|---:|---|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.503 | 0.508 | +0.95% | 2/4 |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.477 | 0.435 | -8.89% | 4/4 |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.396 | 8.366 | -0.36% | 1/4 |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 215.020 | 192.014 | -10.70% | 3/4 |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 216.984 | 194.818 | -10.22% | 4/4 |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3536.996 | 2964.414 | -16.19% | 4/4 |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3421.624 | 3015.082 | -11.88% | 4/4 |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 7.320 | 9.683 | +32.29% | 1/4 |

All processes succeeded; trace fingerprints, operation counts, expected answers
and HDT counters match. Setup is separate. Runtime includes harness work and
operation timing; it is not a pure kernel throughput estimate. `fresh` uses no
warm-up; `warmed` uses an untimed replay on a separate graph before measurement.
There is no answer cache or hardware-cache flush. RSS measures the whole process,
not isolated engine allocations. Setup, RSS and latency tails remain in the JSON.

## Why blocks improve

In separate instrumented replays (two identical repeats per trace/variant),
tree-promotion `pull` entries decrease 21.73% at 100k nodes and 22.34% at 1M;
`join` entries decrease 20.95% and 21.77%. Almost every promoted link has a
singleton right tour: 2,279,696 of 2,279,725 at 1M. The new association joins that
small side first. Link-side sizes, promotions and vertex materialization counts
match. This is evidence of reduced structural work, not a measured CPU-time share.
See [structural comparison](structural-comparison.json) and the sibling before/
after probe directories for instrumentation and reproducible inputs.

## Path regression investigation

The initial +32.29% path result had broad ranges (before 3.89–21.69 ms, after
5.49–34.87 ms). A separate adaptive study ran 32 more processes: eight balanced
pairs for each fresh/warmed regime using the same frozen binaries and trace.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs |
|---|---:|---:|---|---:|---:|---:|---:|
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 8.944 | 8.000 | -10.55% | 4/8 |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.993 | 6.430 | +7.29% | 3/8 |

The fresh slowdown does not reproduce consistently; the warmed result still
shows a possible cost. These observations do not establish statistical
significance or identify scheduling/cache effects. The path has no promotions.
Separate deterministic counters show slightly more work after setup:
`pull` +3.37%, `join` +1.14%, `split` +0.81% outside replacement; root parent steps
+0.32% there and +1.67% inside replacement. A changed level-zero tree shape is
therefore a plausible contributor, not proof of the entire timing difference.
See the [separate follow-up](../2026-10-07-hdt-join-order-path/README.md).

## Next bounded experiment

Try right association only for higher-level tree-promotion links, retaining the
current association for level-zero construction/links. This targets the measured
promotion benefit while preserving the control tree shape. It is a hypothesis,
not implemented here. Require the same correctness checks and predeclared pilot
before considering a full matrix. Keep this candidate and all historical results.

## Verification

[Reconstruction verification](reconstruction-verification.json) records exact
saved-source reconstruction and formatting, Clippy with warnings denied, core
tests/doctests and Rustdoc with warnings denied. The [full workspace checks](workspace-verification.json) also pass; the server startup test required a rerun outside the socket-restricting sandbox. The initial permission failure is retained. [Audit](audit.json) checks source
and artifact hashes and per-cell order. No commit, push or staging was performed.
