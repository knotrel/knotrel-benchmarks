# ETT scan-root reuse: paired pilot with petgraph

Only replacement search changes: reuse the immutable smaller-component root.
Production sources remain unchanged. The candidate and baseline reflect the
current libraries; historical timing campaigns are not reused as measurements.

Six trials per engine/cell, all six engine-order permutations, sequential runs.
All figures below are per-cell medians. Negative percentages mean less time.
RSS is whole-process peak; setup and operation tails remain separate in
[comparison.json](comparison.json). [Protocol](protocol.md).

| Workload | Nodes | Query % | Regime | Before ms | After ms | Petgraph ms | Change vs before | Change vs petgraph | Faster pairs | RSS change | Setup change | Flag |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.219 | 0.214 | 0.776 | -2.33% | -72.48% | 4/6 | +0.00% | +8.45% | False |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.192 | 0.192 | 0.678 | +0.17% | -71.69% | 2/6 | +0.00% | -0.26% | False |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 37.261 | 20.621 | 175.420 | -44.66% | -88.25% | 6/6 | +0.05% | +0.57% | False |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 3.666 | 2.703 | 39.681 | -26.28% | -93.19% | 6/6 | +0.01% | -1.71% | False |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 2.878 | 2.774 | 39.555 | -3.61% | -92.99% | 3/6 | +0.02% | +0.49% | False |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 40.477 | 35.772 | 409.669 | -11.62% | -91.27% | 5/6 | -0.00% | -0.23% | False |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 38.525 | 35.796 | 409.981 | -7.08% | -91.27% | 5/6 | -3.98% | +0.24% | False |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 7.025 | 6.738 | 36.033 | -4.09% | -81.30% | 5/6 | -2.55% | +3.10% | False |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 7.923 | 10.837 | 37.438 | +36.77% | -71.05% | 2/6 | -7.25% | -0.46% | True |

Failed processes: 0. Screening flags: 1.

A flag is >5% runtime increase with at least 4/6 adverse pairs, not a significance test.
No outliers removed or repeated-until-pass. No hardware-cache flush or answer cache.
Fresh/warmed refer to deliberate full-graph replay warmup. Fixed operation counts
change the mutated fraction at different sizes. Cogentco is one real topology
with synthetic outages; no general market superiority or tail guarantee follows.

Tests, source/binary provenance and the saved patch accompany this report.
Existing forest differential/invariant tests ran on both variants. The full
candidate workspace checks are in [verification.json](verification.json).

## Interpretation and decision

Keep this candidate isolated. It delivers a repeatable benefit on the targeted
replacement scan, but the pilot does not pass the regression screen.
The saved [patch](candidate.patch) and complete before/after sources preserve the
experiment independently of temporary build directories. The baseline includes
core revision `86fb85a` and its shared `GenericForest` refactor; these measurements
must not be substituted for the earlier standalone-forest direct-join campaign.

- Dense bridge churn: runtime **−44.66%**, 6/6 faster pairs; cut total **−44.74%**
  and cut p95 **−44.22%**. Link p95 nevertheless rises **5.04%**.
- Blocks at 100k vertices: **−26.28% fresh** (6/6), **−3.61% warmed** (3/6).
  At one million: **−11.62% fresh**, **−7.08% warmed** (both 5/6).
- Cogentco: **−2.33% fresh**, **+0.17% warmed**, not a robust general improvement.
- One-million-vertex path, warmed: **+36.77%**, four adverse pairs out of six.
  Cut total rises **36.66%**, connected total **37.22%**, and cut p95 **39.06%**.
  Pair changes are −31.47%, −9.63%, +17.92%, +33.42%, +73.76%, +139.82%.
  This case scans zero candidate edges and vertices, so eliminated source-root
  walks cannot directly explain its timing. The cause remains unresolved;
  allocator state, scheduling and compiler layout are hypotheses, not findings.
  The fresh path also retains one **+189.78%** adverse pair despite its better
  median. No samples were dropped.

The candidate beats petgraph's median runtime in all nine selected cells
(71.05–93.19% less runtime). The baseline already wins these cells, so this is
neither evidence of universal superiority nor a reason to accept a regression.
RSS changes range from −7.25% to +0.05%; setup changes range from −1.71% to +8.45%.
Whole-process peak RSS does not establish a reduction in the data structure's
memory footprint: the code adds one iterator field and removes no stored graph data.

## Structural proof, separate from timing

The [counter summary](diagnostic/summary.json) comes from separately instrumented
binaries, two identical repeats per variant on dense bridge churn (512 vertices,
90% queries, ten rounds). Counts cover whole cut operations, not just search:

| Counter | Before | After |
|---|---:|---:|
| Root calls | 6,477,150 | 3,238,650 |
| Parent steps | 58,243,100 | 29,122,000 |
| Candidate incidences | 3,238,500 | 3,238,500 |
| Scanned vertices | 12,750 | 12,750 |
| Tree cuts / replacements | 50 / 0 | 50 / 0 |

Exactly one root lookup per candidate incidence disappears; root calls and parent
steps fall approximately 50%. All operation answers and forest counters match.
Reproduce the counter audit with `python3 diagnostic/analyze.py` from this folder.
These counts support the mechanism, not a percentage attribution of elapsed time.
Timed binaries contain no diagnostic counters.

## Next gate

Before a larger matrix or integration, run a separately named, predeclared
confirmation of the warmed/fresh million-vertex path together with dense churn
as a positive control, preserving this pilot. Diagnose cut and connected costs,
process resources and variance using separate instrumented runs. Do not rerun
until a preferred result appears; a favorable follow-up does not erase this flag.

Full checks for both candidate workspaces passed: formatting, all-target Clippy,
workspace tests and Rustdoc warnings. [Audit](audit.json), [review](review.md).
