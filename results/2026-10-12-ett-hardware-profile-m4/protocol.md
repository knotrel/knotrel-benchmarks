# Apple M4 ETT scan-root hardware-profile protocol

## Scope and decision boundary

This is a diagnostic campaign for the ETT scan-root reuse candidate preserved
in `results/2026-10-10-ett-scan-root`. It is not an acceptance benchmark and
does not change the production core. Its purpose is to establish what Xcode
27 Instruments can collect on this Apple M4 host and whether those data can be
scoped to the measured replay.

The current checkout must match the source hashes preserved by the pilot except
for result documentation. `build.py` checks that condition, constructs isolated
copies under `/private/tmp`, installs the saved before/after `forest.rs` and
`dynamic.rs` snapshots, and proves that their generated patch is identical to
the saved candidate patch. It records all source, binary, compiler, revision,
and dirty-state provenance in this directory.

No source in either production checkout is modified. The diagnostic binaries
are not timing-acceptance binaries and are never pooled with the historical
campaigns.

## Instrumentation limitation established before collection

The installed Xcode 27 `CPU Counters` template contains `Points of Interest`
and uses a 10 ms process bucket. A profiler-recognized replay marker would
need an `os_signpost` call inside the isolated Rust binary. The macOS SDK
exposes that API as C only; no cached safe Rust wrapper or supported marker
utility is available. Calling it directly would introduce `unsafe`, which is
prohibited for this investigation.

Accordingly, this campaign deliberately records complete processes and saves
their trace tables only to test profiler availability and sampling resolution.
It **must not** attribute cache, cycle, instruction, fault, scheduler, core,
frequency, energy, or any other counter to the replay. The runner's internal
`workload_wall_ns` remains the only verified replay boundary, but it cannot
select a subinterval in the trace. A missing sample is reported as insufficient
resolution, not as zero cost.

This limitation is an outcome of the protocol, not permission to increase the
number of rounds or replay the same graph repeatedly.

## Fixed collection budget

Six CPU Counters traces are collected exactly once, with one fresh process per
trace and the original deterministic operation parameters:

| Order | Variant | Workload | Nodes | Queries | Warmup |
|---:|---|---|---:|---:|---:|
| 1 | before | `sustained-churn-path-v1` | 1,000,000 | 50% | 0 |
| 2 | after | `sustained-churn-path-v1` | 1,000,000 | 50% | 0 |
| 3 | after | `sustained-churn-path-v1` | 1,000,000 | 50% | 1 |
| 4 | before | `sustained-churn-path-v1` | 1,000,000 | 50% | 1 |
| 5 | before | `dense-bridge-churn-v1` | 512 | 90% | 1 |
| 6 | after | `dense-bridge-churn-v1` | 512 | 90% | 1 |

Every command uses seed 42, ten rounds, one measured replay, zero repeated
queries, and `ett-scan`. The order alternates the variant within each case,
and the path case reverses direction between fresh and warmed. No extra trace
is collected to seek a preferred outcome. Failed commands, failed recording,
empty tables, and adverse observations are retained.

`collect.py` captures the Xcode path, template listing, recording options,
process command, binary SHA-256, xctrace exit status, target stdout/stderr,
trace table of contents, and `pmset` state. It runs under a temporary
`caffeinate -is` assertion and preserves the power-log interval. Any observed
suspension invalidates the collection for acceptance; the raw traces remain.

## Analysis limits

The analysis reports:

- the six commands, complete-process traces, and their exported table names;
- whether the trace has enough samples to identify useful work;
- benchmark-reported replay wall time separately from trace observations;
- CPU/thread time only when independently reported by a separately verified
  diagnostic binary, not inferred from a whole-process trace;
- the absence of verified replay-scoped cache, fault, scheduler, core,
  frequency, or energy metrics when markers are absent.

No absolute time is compared with the Apple M3 historical campaign. The dense
case is a positive control only if a later, non-instrumented paired campaign
uses matching source and workload semantics. A favorable median, trace, or
whole-process counter is not evidence for integration.
