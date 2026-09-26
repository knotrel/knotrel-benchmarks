# Benchmark methodology

## Implemented baseline

`chain-split-rejoin-v1` starts with an undirected path. A wrapping 64-bit LCG
selects which edge to cut in each round. Deleting a path edge disconnects the two
ends; restoring it reconnects them. These expected results come from topology,
independently of the measured engine. The generator is deterministic for a
configuration; modulo edge selection has a small bias and is not advertised as
unbiased sampling.

Graph construction, trace generation and latency-buffer allocation occur before
measurement. Each timed interval includes the engine call, a compiler barrier
and clock overhead. Correctness checks and sample insertion occur afterward.
Latency samples are sorted after the run, using nearest-rank percentiles
`ceil(p*n/100)`. A singleton's percentiles equal its only sample. No timer-overhead
subtraction or automatic warmup is performed. Very short updates may be dominated
by clock overhead. Wall time additionally includes checking and harness overhead.

The harness stores O(rounds) operations and timing samples. This affects memory
and cache behavior. It does not measure engine-only RSS. The first workload is
single-threaded, has 50% queries, alternates split/rejoin updates and uses only
bridge deletions. It cannot establish scaling, general workload performance,
concurrent service throughput or network latency.

## Reproducible runs

Record both Git revisions and any diffs, Cargo.lock files, Rust compiler,
optimization flags, target CPU settings, OS/kernel, CPU model, core count, RAM,
dataset checksum, full arguments and repetition count. Run from the source
checkout; the report's Git fields describe checkout state at run time and do not
attest to a separately copied binary. Null Git fields mean metadata was unavailable.
Do not modify either checkout between building and running.

Use a quiet machine and repeated process runs. Preserve each JSON report. Report
variability across repetitions rather than selecting the fastest. Keep local core
results separate from HTTP results, where serialization, scheduling and transport
are part of the measured service cost. Record memory independently and account for
the harness, allocator, preload and external processes.

## Future comparison adapters

Before comparing with GraphScope or a specialized dynamic-connectivity engine:

1. Load identical graphs and replay an identical update/query trace.
2. Match undirected graph semantics, duplicate handling and node lifetime.
3. Ensure every query sees the same preceding updates. Measure waiting for an
   incremental engine to catch up; do not compare stale answers with exact ones.
4. Validate query answers against an independent oracle before interpreting times.
5. Distinguish boolean connectivity queries from materializing full component labels.
6. Include ingestion, deletion maintenance, compaction and required synchronization.
7. Record software versions, worker counts, thread counts, hardware and costs.

GraphScope's incremental capabilities must be exercised by an actual adapter;
do not assume full recomputation on every update. Add cyclic, high-degree,
disconnected, skewed and adversarial workloads before making broad conclusions.
