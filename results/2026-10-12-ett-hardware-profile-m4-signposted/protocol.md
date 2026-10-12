# ETT scan-root marker-scoped CPU Counters protocol on Apple M4

## Preconditions and scope

This campaign follows the successful safe-marker validation in
`2026-10-12-ett-signpost-validation-m4`. It reuses only the isolated,
hash-verified before/after binaries from that result. The binaries add
`apple-log` 0.7.0 solely in their copied benchmark workspace and emit
`warmup-replay` and `measurement-replay` signpost intervals. Production
sources, lockfiles, and the scan-root candidate remain unchanged.

`CPU Counters` is the only Instruments template used. Every exported metric is
classified by scope. A metric may be reported as replay-scoped only if its time
interval overlaps the target process's `measurement-replay` signpost interval.
Whole-process and system data remain separate. Missing or zero replay-overlap
samples are insufficient resolution, never zero work.

## Fixed budget and order

The committed [plan.json](plan.json) is generated once by [plan.py](plan.py)
using seed 1012 before collection. It contains 36 adjacent before/after groups:

| Case | Groups | Variant order |
|---|---:|---|
| path, 1,000,000 vertices, 50% queries, fresh | 12 | 6 AB, 6 BA |
| path, 1,000,000 vertices, 50% queries, warmed | 12 | 6 AB, 6 BA |
| dense bridge churn, 512 vertices, 90% queries, warmed | 12 | 6 AB, 6 BA |

Every process uses seed 42, ten rounds, `ett-scan`, one measured replay, and
zero repeated queries. Each warmup rebuilds a graph and never passes graph
state to the measured replay. The 36 groups are shuffled as units and split
into six consecutive batches of six groups (12 processes). The plan cannot be
regenerated or edited after any batch exists.

Each process retains stdout, xctrace diagnostics, marker export, counter,
metric, and thread-activity exports. The raw `.trace` bundles and bulky exports
are stored outside Git in the session artifact location recorded by each batch;
their hashes remain in the result directory. No failed or adverse result is
repeated.

## Measures and limits

The campaign captures only the availability of:

- marker-scoped counter samples, their raw counter arrays, and associated
  thread/core labels;
- marker-scoped thread-activity rows when exported;
- marker interval duration and internal replay wall time;
- process-wide trace tables, kept explicitly separate;
- temporary sleep inhibition and power-log events.

It does not claim page faults, allocator events, instructions, cycles, cache or
TLB misses, frequency, energy, or a named bottleneck unless the exported table
gives the metric, scope, and marker overlap unambiguously. The CPU Counters
template's configured mode, template listing, and recording options are saved
with every batch.

## Decision

The analysis must report all 36 pairs per case, distributions rather than a
single median, marker validation failures, profiler failures, adverse pairs,
and missing data. A path result may be described as reproduced only if its
paired distribution is variable on this host; a dense direction may be called a
positive-control observation only if its full paired distribution is favorable.
No median, counter difference, or profiler trace integrates the candidate.
