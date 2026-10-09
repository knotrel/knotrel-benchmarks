# HDT structural diagnosis: 100k path, 50% queries

## Finding

The earlier elapsed-time regression has **no corresponding increase in the
measured aggregate structural work during cuts or queries** on this exact trace.
Before and after perform identical counts for all seven measured counters in
498 cuts and 500 connectivity queries. Only two replay operations are links;
these perform less structural work after the direct-join optimization.

This narrows the diagnosis: additional aggregate root/rank traversal, split,
join or pull work does not explain the previously observed slowdown on this
trace. It does not prove identical per-operation behavior, memory access order,
cache misses or execution time. No hardware counters were collected. Do not
attribute remaining timing variation to a specific OS/cache/thermal cause.

## Method

`probe.py` copies core sources into a new temporary directory and reconstructs
the before variant by reversing only the direct-join edit. All original core
source hashes are checked against both frozen benchmark snapshots before any
instrumentation. Production files and APIs are untouched.

Diagnostic atomic counters record pull/join/split function entries (including
recursive and empty-base-case calls), root/rank calls and parent steps in their
loops. Counters are reset and collected around every operation and aggregated
by phase. The isolated core and replay harness are compiled with optimized
`rustc`, edition 2024, without debug assertions. These builds are diagnostic,
not the Cargo benchmark binaries; no timings are recorded or compared.

The harness reads the original exported 100k path trace: 10 rounds, seed 42,
50% queries. Registration and initial links are separated from measured-replay
operations. Every mutation and query result is asserted against the trace.
Each variant is executed twice; output counters must match exactly across runs.
Fresh/warmed timing regimes are not repeated: this is structural work, not a
cache experiment. Trace SHA-256, original source snapshots, commands and compiler
are in `results.json`. `harness.rs.txt` and the instrumented forest snapshots
preserve exactly what the probe executed; `probe.py` contains all injection code.

## Counts

| Phase | Operations | Counter | Before | After | Delta |
|---|---:|---|---:|---:|---:|
| initial_links | 99999 | pull | 13,626,504 | 7,175,680 | -47.34% |
| initial_links | 99999 | join | 13,151,572 | 6,825,742 | -48.10% |
| initial_links | 99999 | split | 7,338,317 | 2,268,946 | -69.08% |
| initial_links | 99999 | root_calls | 399,996 | 399,996 | +0.00% |
| initial_links | 99999 | rank_calls | 199,998 | 199,998 | +0.00% |
| initial_links | 99999 | root_parent_steps | 2,837,918 | 3,087,912 | +8.81% |
| initial_links | 99999 | rank_parent_steps | 1,418,959 | 1,543,956 | +8.81% |
| cut | 498 | pull | 32,880 | 32,880 | +0.00% |
| cut | 498 | join | 31,622 | 31,622 | +0.00% |
| cut | 498 | split | 27,400 | 27,400 | +0.00% |
| cut | 498 | root_calls | 1,992 | 1,992 | +0.00% |
| cut | 498 | rank_calls | 996 | 996 | +0.00% |
| cut | 498 | root_parent_steps | 15,254 | 15,254 | +0.00% |
| cut | 498 | rank_parent_steps | 8,955 | 8,955 | +0.00% |
| link | 2 | pull | 151 | 102 | -32.45% |
| link | 2 | join | 149 | 100 | -32.89% |
| link | 2 | split | 110 | 61 | -44.55% |
| link | 2 | root_calls | 8 | 8 | +0.00% |
| link | 2 | rank_calls | 4 | 4 | +0.00% |
| link | 2 | root_parent_steps | 20 | 20 | +0.00% |
| link | 2 | rank_parent_steps | 10 | 10 | +0.00% |
| connected | 500 | root_calls | 1,000 | 1,000 | +0.00% |
| connected | 500 | root_parent_steps | 10,611 | 10,611 | +0.00% |

Registration makes no calls to these counted methods. Initial construction saves
millions of split/join/pull calls, despite slightly longer aggregate root/rank
walks. This is consistent with the previously measured setup improvement, but
the diagnostic alone does not assign time savings to individual methods.

The workload's label “50% queries” must not be mistaken for balanced link/cut
traffic: its remaining 500 operations are **498 cuts and 2 links**. Consequently,
this replay offers little direct opportunity to benefit from faster link beyond
initial construction. The cyclic-block workloads exercise promotion links much
more heavily, explaining why they are a more relevant target for this change;
that last explanation is a mechanism-based inference, not a new measurement here.

## Decision and limits

Keep direct joins in experimental HDT. Do not introduce a path-specific fallback
or roll back based on the earlier 11.62% observation: the
[48-process timing investigation](../2026-10-05-hdt-path-investigation/README.md)
did not reproduce a stable slowdown, and this probe finds no aggregate structural
penalty during cuts/queries. Preserve all unfavorable measurements.

The regression investigation can close as **not reproduced consistently; no
measured structural cause**, not “proved impossible” or “definitively cache noise”.
Future timing work should use longer measurement windows or controlled repeated
replays while preserving the original short reference trace, with hardware
profiling only if a repeatable gap remains. Do not silently substitute a longer
trace into existing before/after tables.

## Reproduction and validation

Run `probe.py` from any directory in a fresh copy of this result directory;
it refuses to overwrite `results.json`. The original exported trace must remain
available at the referenced campaign path. Then run `summarize.py`. Four isolated
replays completed with exact result checks and deterministic counters. No new
production code was introduced, so the unchanged workspace suites were not rerun.
