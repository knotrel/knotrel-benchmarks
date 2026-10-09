# ETT packed optional indices — pilot

Four private optional indices use checked index + 1 encoding. Tokens occupy
64 instead of 96 bytes on this 64-bit target. No algorithm/API change. Candidate
is isolated; production ETT remains unchanged. [Protocol](protocol.md).

## Before / after

Negative changes mean improvement. Runtime excludes setup; peak RSS covers the
whole process. Four paired processes per variant/cell; fresh and warmed are
separate. No answer cache or hardware cache flush.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | Peak RSS change | Setup change |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | imported | fresh | 0.339 | 0.321 | -5.54% | 3/4 | +0.00% | -2.70% |
| topology-zoo-outages-v1 | 197 | imported | warmed | 0.292 | 0.286 | -1.94% | 3/4 | +0.00% | -0.20% |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 37.226 | 32.471 | -12.77% | 4/4 | +0.32% | -1.57% |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 3.776 | 3.381 | -10.46% | 3/4 | -15.69% | +6.53% |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 3.842 | 3.189 | -16.99% | 4/4 | -19.17% | +4.41% |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 50.808 | 36.170 | -28.81% | 3/4 | -18.62% | +0.42% |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 46.302 | 36.693 | -20.75% | 3/4 | -19.46% | +4.98% |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 11.800 | 8.156 | -30.88% | 3/4 | -16.10% | +3.73% |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 7.439 | 6.621 | -10.99% | 3/4 | -20.15% | +0.33% |

## Decision screen

Completed comparison: 72 successful processes. Runtime regression flags: 0.
The original attempt also contains 16 failed Cogentco processes because its
historical temporary trace file was absent. Those failures remain in
[manifest.json](manifest.json) and [initial-comparison.json](initial-comparison.json).
Only the missing-input cases were completed after recovering the pinned source
and verifying byte-identical trace SHA-256. The synthetic cases were not rerun.
[completed-manifest.json](completed-manifest.json) selects the successful cases;
88 process attempts in total. Cogentco completion ran later, separately from the
synthetic cases, preserving its original within-cell balanced order.
A flag means median runtime >5% slower with at least 3/4 adverse pairs; it is
a screening rule, not a significance test. See [comparison.json](comparison.json)
for all pairs, ranges and cut/link/query p50/p95/p99. No reciprocal-latency
throughput estimates or universal speedup claims are made.

## Verification and provenance

[Saved patch](candidate.patch), [build metadata](builds.json),
[verification](verification.json), [audit](audit.json). Both binaries were built
from identical isolated sibling copies except for ETT forest.rs. Source hashes
and exact traces are checked; the harness validates answers against its oracle.
Process order is balanced within every cell. Historical rankings are not pooled
with these measurements. A favorable pilot only justifies a broader matrix.

## Disposition and reproduction

All nine cell medians improve, but individual adverse pairs remain. This pilot
supports a broader paired ETT matrix; it does not establish universal speedup
or justify automatic integration. Production ETT remains unchanged.

Run `analyze_completed.py` and `audit_completed.py` to reproduce completed
statistics and checks. The original `analyze.py` reconstructs the initial
incomplete comparison instead. Preserve separate completion provenance.
