# HDT promotion-only join association

## Decision

The pilot gate passed. This qualifies the candidate for a full reference-matrix comparison; it does not justify production integration yet. Qualifying block cells: 4/4 (required 3). Control regressions meeting the screen: 0.

The candidate is saved separately; production core code is unchanged. No earlier
candidate patches are combined. No commit or staging action is implied.

## Change

[Patch](candidate.patch): ordinary `Forest::link` retains left association through
`link_ordered::<false>`. Only tree-edge promotion in `HdtGraph::promote` calls
`link_promoted`, which uses right association at destination level `i+1 > 0`.
Both preserve the exact sequence `left, ab, right, ba`, AVL balance, parent links
and aggregates, with O(log V) worst-case link cost. Replacement links use the
ordinary route. No public configuration or API changes.

This targets the promotion benefit in the [previous global-association experiment](../2026-10-07-hdt-join-order/README.md)
while preserving ordinary level-zero construction. Compile-time selection avoids
a runtime configuration check, but code layout can still affect measured timing.

## Paired pilot

[Protocol](protocol.md): 72 sequential processes, nine cells, four pairs per cell,
2/2 before-first/after-first order, seed 42 shuffle. Includes the original eight
pilot cells plus warmed path at one million vertices, predeclared before timing.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Change | Faster pairs |
|---|---:|---:|---|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | — | fresh | 0.480 | 0.480 | -0.01% | 2/4 |
| topology-zoo-outages-v1 | 197 | — | warmed | 0.433 | 0.419 | -3.26% | 4/4 |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.146 | 8.369 | +2.74% | 1/4 |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 211.708 | 193.268 | -8.71% | 4/4 |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 217.825 | 193.747 | -11.05% | 4/4 |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3439.209 | 2907.410 | -15.46% | 4/4 |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3226.760 | 2839.835 | -11.99% | 4/4 |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 6.845 | 6.347 | -7.28% | 3/4 |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.884 | 4.132 | -29.78% | 3/4 |

Negative change means less runtime. Percentage is `100*(after median/before
median-1)`, not median paired percentage. Runtime is workload wall time, excluding
setup and including harness checking/timer overhead. Warmed performs an untimed
replay on a separate graph; no answer cache or hardware-cache flush. Whole-process
RSS, setup and operation latency tails are retained in [comparison.json](comparison.json).
This small pilot is an engineering screen, not statistical significance. Do not
pool these samples with earlier experiments or infer competitor performance.

All 72 processes succeeded. Their replays are checked against reference fingerprints and expected
answers, with identical operation and HDT counters. Failures are retained by the
analyzer; inspect its `failed` list. See [gate](gate.json) for the unchanged screen.

## Structural evidence

Separate instrumented executions, two identical repeats per variant/trace:

- 100,000 vertices: promotion pull entries -21.73%, join entries -20.95%, split entries -1.46%.
- 1,000,000 vertices: promotion pull entries -22.34%, join entries -21.77%, split entries -1.25%.

Path1M,q50 replay counters identical before/after: **yes**. See
[path counters](path-structural-comparison.json). The observed -29.78% warmed path timing must not be presented as an algorithmic work reduction: the path does not use promotion links, and its counted work is unchanged. Timing variation or code-layout effects remain possible, not established causes. This checks the expected absence
of extra structural work on the non-promoting control, not equality of runtime.
Promotion counts, endpoint materialization and link-side sizes match in the block
probes. Function-entry counts include recursion and are not CPU-time shares.
See [block counters](structural-comparison.json) and sibling probe directories.

## Correctness and preservation

The explicit cyclic-order/aggregate tests exercise ordinary and promoted links,
reversed relinks and recycled tokens. The initial red log records the missing new
entry point, not a correctness defect in the baseline. The reconstructed candidate passes workspace formatting, Clippy with warnings denied, workspace tests/doctests and Rustdoc with warnings denied.
Saved before/after sources include both `hdt_forest.rs` and `hdt.rs`; builds record
source/compiler/binary hashes. Reconstruct with [verify.py](verify.py), then inspect
[verification](reconstruction-verification.json) and [audit](audit.json).
All historical results and patches remain separate.
