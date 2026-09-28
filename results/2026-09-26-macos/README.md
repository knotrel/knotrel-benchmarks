# Local BFS baseline — 2026-09-26

Measured on Apple M3, 8 CPU cores, 16 GiB RAM; macOS 26.5.2 (25F84),
aarch64, Rust 1.98.1 (48a229cea 2026-09-01). Release profile: thin LTO,
one codegen unit, default optimization level, no recorded RUSTFLAGS override.
The manifest records the exact compiler, build command and environment fields.
Hardware sysctl queries were denied in the sandbox; a separately authorized
read returned `Apple M3`, `8`, `17179869184`. The manifest retains the original
permission errors rather than silently inventing successful automatic discovery.

Each row uses 200 rounds, seed 42, one discarded full warmup replay and three
measured fresh-graph replays in one process. Workload/size processes ran
sequentially. Power mode, CPU affinity, background load and thermal conditions
were not controlled. This is an exploratory developer-machine baseline.

## Observations

All measured operations passed the topology-derived runtime checks. Query time
accounted for 98.29%–99.95% of the sum of timed operation durations across these
runs; graph setup is excluded. At 4096 vertices, the median of per-run query p50s
ranged from 115.000 µs (components) to 277.208 µs (chain). The query p95 range for
the chain at that size was 303.625–365.375 µs, showing visible run variability.

These observations motivate maintaining connectivity state between queries.
They do **not** show which alternative algorithm wins: none is implemented or
measured here. Update medians near tens of nanoseconds are strongly affected by
clock granularity and timer overhead; they are not precise isolated update costs.

## Results

Values are microseconds. Cut/link/query p50 columns are the **median of the three
per-repetition p50s**, not a pooled percentile. Query p95 shows min–max across the
three repetition p95s. Raw JSON preserves every repetition, counts, totals and
all percentiles including p99/max. Do not compare workload totals as though
rounds contained equal numbers of operations.

| Workload | Vertices | Cut p50 | Link p50 | Query p50 | Query p95 range |
| --- | ---: | ---: | ---: | ---: | ---: |
| chain-split-rejoin-v1 | 128 | 0.042 | 0.042 | 4.667 | 4.791–4.792 |
| cycle-alternatives-v1 | 128 | 0.042 | 0.042 | 2.250 | 7.166–7.625 |
| components-join-split-v1 | 128 | 0.042 | 0.042 | 1.709 | 5.792–6.542 |
| hub-alternatives-v1 | 128 | 0.042 | 0.042 | 3.750 | 5.500–5.584 |
| chain-split-rejoin-v1 | 1024 | 0.042 | 0.083 | 39.917 | 40.792–43.208 |
| cycle-alternatives-v1 | 1024 | 0.083 | 0.083 | 30.042 | 86.625–86.959 |
| components-join-split-v1 | 1024 | 0.083 | 0.083 | 21.167 | 80.042–80.958 |
| hub-alternatives-v1 | 1024 | 0.083 | 0.083 | 38.208 | 60.334–63.708 |
| chain-split-rejoin-v1 | 4096 | 0.125 | 0.084 | 277.208 | 303.625–365.375 |
| cycle-alternatives-v1 | 4096 | 0.125 | 0.084 | 166.125 | 346.917–350.917 |
| components-join-split-v1 | 4096 | 0.125 | 0.125 | 115.000 | 349.333–353.917 |
| hub-alternatives-v1 | 4096 | 0.125 | 0.125 | 207.375 | 400.625–419.834 |

## Reproduction and provenance

From the benchmark checkout:

```sh
python3 scripts/run_baseline.py results/NEW_RUN_DIRECTORY
```

See [methodology](../../docs/methodology.md) for the trace and timing contract.
`manifest.json` stores exact arguments, SHA-256 checksums, hardware discovery,
both revisions/dirty states and build-input hashes. `*.json` are raw reports;
`*.trace.json` are the matching reusable traces. `benchmarks.patch` preserves
tracked modifications at measurement time; `untracked/benchmarks/crates/...`
contains the new Rust trace generator omitted by Git diff. Apply that patch to
benchmark revision [`9a20223`](https://github.com/knotrel/knotrel-benchmarks/tree/9a20223c54e3f0383b0300a1cdd4b7d40cc6bb3e) and copy the
untracked generator at its relative path to recover the measured Rust sources.
Use core revision [`87ca572`](https://github.com/knotrel/knotrel/tree/87ca572223b6657836db14aa34338c7855d56859) in the sibling [`knotrel`](https://github.com/knotrel/knotrel) clone.
The core patch is empty. Later documentation edits do not change measured code.

The manifest hashes artifacts present at run completion; this explanatory README
and later verification log are not part of that checksum set. Runtime Git metadata
is not binary attestation. These local runs include uncommitted benchmark changes,
preserved through diffs and hashes, as requested. There are no GraphScope, HTTP,
RSS, end-to-end loading-cost, optimized-engine or commercial-cost measurements.
