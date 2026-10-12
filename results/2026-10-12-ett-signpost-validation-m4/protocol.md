# ETT scan-root signpost validation on Apple M4

## Purpose and isolation

This campaign validates replay interval markers before any replay-scoped
hardware-counter interpretation. It is separate from the preceding
whole-process-only `2026-10-12-ett-hardware-profile-m4` feasibility campaign.

`apple-log` 0.7.0 is the only added dependency, and only in a copied diagnostic
benchmark workspace under `/private/tmp`. It is a crates.io package with
MIT OR Apache-2.0 licensing, declared MSRV 1.82, and a safe public
`OSSignposter` API. Its opt-in `raw-ffi` feature is not enabled. No production
manifest, lockfile, source file, or ETT candidate source is changed.

The diagnostic adds no `unsafe` Rust. It creates one `OSSignposter` before
replaying engines and emits:

- a `warmup-replay` interval around each unreported fresh-graph warmup;
- a `measurement-replay` interval after graph construction and all sample
  buffer allocations, and before replay summaries and graph destruction.

The operation loop, timers, oracle, workload, graph rebuild policy, and
candidate snapshots remain unchanged.

## Fixed marker-validation budget

Exactly two CPU Counters recordings are made:

| Order | Variant | Workload | Nodes | Queries | Warmup |
|---:|---|---|---:|---:|---:|
| 1 | before | `sustained-churn-path-v1` | 1,000,000 | 50% | 1 |
| 2 | after | `sustained-churn-path-v1` | 1,000,000 | 50% | 1 |

Both use seed 42, ten rounds, one measured replay, no repeated queries, and
the `ett-scan` engine. The order is fixed before the first recording. These
two recordings validate marker visibility and ordering only; they are not a
performance comparison and do not establish a before/after effect.

`collect.py` saves the complete command, hashes, stdout, stderr, trace table
of contents, and the exported `OSSignpostIntervals` table. It runs each
recording under a temporary `caffeinate -is` assertion. Any trace is rejected
for later replay-scoped analysis unless it has exactly one `warmup-replay` and
one `measurement-replay` interval for its target process, ordered without
overlap. A profiler failure, absent marker, malformed marker, or sleep/wake
event is retained and ends this validation; no retry is permitted.

## Decision

Only a successful marker validation permits a separate, newly predeclared
hardware collection. That later campaign must still report unavailable
counters and distinguish marker-scoped thread/process metrics from system-wide
metrics. A successful marker is not an ETT optimization acceptance result.
