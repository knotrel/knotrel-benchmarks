# Performance prototypes: report (2026-11-28)

Plan: [`PLAN.md`](PLAN.md), committed before any measurement (58a70fc7, 09:37 +01:00).

- **Baseline:** knotrel `main` at 7202dbe (#209 and #210).
- **Prototype branches**, each cut from 7202dbe and compared only with it:
  - `feature/query-scratch-reuse` (661c454);
  - `feature/snapshot-reads` (732642c).
- **Host:** M3 with 8 CPUs, AC power. Host time for measurement: 20 s (core) plus about 3 min (server) for prototype 1, and 280 s for prototype 2.
- **Scope:** diagnostic runs, separate from the v1.2.0 qualification (knotrel#182). The merge decision stays with the maintainer.

Raw outputs are in [`raw/`](raw).

## Summary

| | Benefit | Cost | Favoured loads | Penalized loads | Recommendation |
|---|---|---|---|---|---|
| **1. Reusable query scratch** | Short queries: p50 0.25–0.78×, p99 0.51–0.88×, 0 allocations per query (from 9–18). Server: read95 +13 % req/s, mixed50 +20 % req/s with p99 −18 % | Up to 256 KiB of scratch per thread (measured 56 KiB after short queries); RSS +4 MiB at read95. Long queries above the cap still allocate | Many short queries: random and low-diameter graphs, small-to-giant disconnected queries, write-heavy batches that are bound by execution time | None measured beyond the ±5 % band (cycle L2: 0.97–1.05×) | **Adopt.** It met all four criteria. Keep the cap: without it a thread kept 8.3 MiB after one large query, 132 MiB over 16 threads |
| **2. Snapshot reads (two copies)** | Pure-read latency: read95 p50 601 → 131 µs. Feeder tail: event request max 104 → 32 ms; events/s +4 % | Every write is applied twice, and the writer waits for readers still on the old copy. Throughput −26 % (read95) and −54 % (mixed50); query p99 2.5× (read95) and 1.7× (feeder); event job execution 56 → 254 µs. State memory 2×: RSS after load +14–20 MiB, peak +10–30 MiB | Loads that are nearly all reads, with rare writes, where read latency matters more than throughput | Any load with frequent writes, which includes every measured load. With closed-loop clients, slower writes cut total throughput | **Do not adopt in this form.** It failed criteria 1, 2 (query p99) and 3. The consistency checks pass |

## Prototype 1: reusable query scratch

**Change.** `Graph::connected` keeps its two queues and two mark bitsets in thread-local scratch. After each query it clears the marks it set, at O(visited) cost, or in one pass when that is cheaper. It releases capacity above 64 KiB per buffer, so a thread keeps at most 256 KiB. A dirty flag makes the next query start from empty scratch if a search unwinds. New tests:
- alternating graphs of very different sizes on one thread (stale marks);
- eight threads querying a shared graph, checked against the reference.

**Core loads.** 100,000 vertices, public API, per-thread allocation counters. Each figure is the median of 3 alternating processes × 2 code layouts (default and `-align-loops=64`), given as default/aligned where they differ.

| Load | Threads | p50 base → p1 (µs) | p50 ratio | p99 ratio | Allocations per query |
|---|---|---|---|---|---|
| S1 random, short | 1 | 5.4 → 4.2 | 0.78 / 0.78 | 0.87 / 0.88 | 18.4 → 0 |
| | 16 | 7.6 → 5.5 | 0.73 / 0.71 | 0.83 / 0.81 | 18.4 → 0 |
| S2 small → giant, disconnected | 1 | 0.9 → 0.4 | 0.45 / 0.48 | 0.71 / 0.68 | 9.4 → 0 |
| | 16 | 1.5 → 0.5 | 0.33 / 0.27 | 0.58 / 0.51 | 9.4 → 0 |
| L1 chain, ends | 1 | 343 → 294 | 0.98 / 0.76 | 0.96 / 0.68 | 27 → 16 |
| | 16 | 444 → 347 | 0.85 / 0.72 | 0.95 / 0.87 | 27 → 16 |
| L2 cycle, opposite | 1 | 283 → 290 | 1.05 / 1.00 | 1.05 / 1.02 | 27 → 16 |
| | 16 | 330 → 331 | 1.00 / 1.00 | 0.99 / 1.07 | 27 → 16 |
| L3 split chain, disconnected | 1 | 191 → 141 | 0.83 / 0.67 | 0.76 / 0.73 | 26 → 15 |
| | 16 | 207 → 171 | 0.88 / 0.78 | 0.95 / 0.19 | 26 → 15 |

Threads 4 and 8 are in `raw/p1`. Long queries go past the 64 KiB queue cap, so the queue is reallocated, by design.

**Memory retained after "large query → many small queries"** (live heap per thread, counting allocator): one search across a chain of 1,000,000 vertices, then 10,000 short queries on the 100k random graph.

| Variant | After the large query | After 10,000 short queries | 16 threads, total |
|---|---|---|---|
| baseline | 0 | 0 | 0 |
| capped (prototype) | 2 KiB | 56 KiB | 0.9 MiB |
| uncapped | 8.2 MiB | 8.3 MiB | 132 MiB |

**Server** (`contention-probe`, 100k random graph, 16 clients, 15 s; median of 3 alternating runs):

| Load | req/s | p50 | p99 | RSS |
|---|---|---|---|---|
| read95 b8 | 26,485 → 30,001 (+13 %) | 593 → 516 µs | 1,464 → 1,425 µs | 35.3 → 39.2 MiB |
| mixed50 b64 | 4,643 → 5,570 (+20 %) | 3,429 → 2,848 µs | 3,959 → 3,264 µs | 34.0 → 34.1 MiB |

**Criteria.**
1. S1 and S2 p50 ≥ 10 % better at 1 and 16 threads: **met**.
2. L1–L3 at most 5 % worse: **met**. Worst case is L2 at 1 thread, 1.05 default and 1.00 aligned.
3. Zero allocations per query in steady state: **met** for queries within the cap.
4. At most 256 KiB retained per thread: **met** (56 KiB).

**Process note.** The first server comparison was void. Both binaries were built in one shared target directory, cargo judged the baseline build fresh from file timestamps, and both runs used the prototype. It was detected because the two binaries were identical, and repeated with the baseline built in its own target directory. The core measurements used separate target directories from the start.

## Prototype 2: snapshot reads

**Change** (`crates/knotrel-server/src/versions.rs`). The service keeps two copies of `GraphState`:
- **Readers** take the current copy with `try_read`, never parking on a writer, and hold it for the whole read job.
- **Writers** serialize on a mutex. Each one runs on the inactive copy, publishes it by swapping the current index (before unlocking, see below), then updates the other copy:
  - batches and feeder events: replay of the job;
  - sessions, heartbeats, gaps and barriers: copy of the metadata;
  - imports: full clone.
- Core and server state types derive `Clone`.

**Consistency checks** (all pass, 20 of 20 repeated release runs):
- container test: writers alternate two-field jobs, some replayed and some cloned. Readers never see one field without the other, and a reader's version never goes backwards;
- service test: a writer alternates the batches `[link 1-2, link 3-4]` and `[cut 1-2, cut 3-4]`, and six concurrent readers query both pairs in one batch. The answers are always equal, match the state version, and the version is monotonic;
- held old version: other readers proceed and the new version is published, while the writer waits for that reader before updating the old copy and returning.

The first run of the container test found a real ordering bug. The writer unlocked the new copy before swapping the index, so a reader with a stale index could read the new version and then, on its next read, the old one. Publishing before unlocking fixed it.

Four existing tests assert that readers wait behind a writer: stats behind a locked job, admission bound, and two panic-ordering tests. They are marked ignored with that reason. Jobs after a panic are still refused.

**Server** (`contention-probe`, 100k random graph, 16 clients, 20 s; mean of 2 alternating runs):

| Load | Metric | Baseline | Snapshot reads |
|---|---|---|---|
| R standalone read95 b8 | requests/s | 25,959 | 19,300 (−26 %) |
| | p50 / p99 | 601 / 1,508 µs | 131 / 3,733 µs |
| | batch lock wait / execution (reads and writes) | 484 / 63 µs | 678 / 97 µs |
| | RSS after load / peak | 23.9 / 36.3 MiB | 37.8 / 47.1 MiB |
| F source-managed read100 b8 + feeder events | query requests/s | 39,606 | 38,441 (−3 %) |
| | query p50 / p99 | 355 / 1,094 µs | 329 / 1,865 µs |
| | feeder events/s | 104,019 | 108,469 (+4 %) |
| | event job lock wait / execution | 113 / 56 µs | 0 / 254 µs |
| | event request p50 / max | 548 µs / 104.3 ms | 586 µs / 31.9 ms |
| | RSS after load / peak | 38.1 / 72.9 MiB | 58.3 / 102.7 MiB |
| W standalone mixed50 b64 | requests/s | 4,617 | 2,107 (−54 %) |
| | p50 / p99 | 3,448 / 4,029 µs | 7,455 / 9,577 µs |
| | write batch lock wait / execution | 3,173 / 215 µs | 6,997 / 472 µs |

- **Write latency.** In W almost every batch writes, so batch lock wait plus execution is the write latency, and it rises 2.2×. In F, the event job's execution includes the replay and the wait for readers on the old copy. In R, the server histograms do not separate read batches from write batches.
- **Memory while a reader holds an old version.** This design never creates a third copy, so the peak stays at two copies of the state (+14–20 MiB after load here). A long reader on the old copy delays the writer's return instead (container test above).

**Criteria.**
1. R p99 −30 % and throughput +20 %: **failed** (p99 +148 %, throughput −26 %).
2. F events/s at most 10 % lower: **met** (+4 %). F query p99 lower: **failed** (+70 %).
3. Write latency at most 2×: **failed** (2.2× in W).
4. Memory at most 2.2× the graph state: **met**. The state doubles, and RSS grows 1.4–1.6×.
5. Consistency: **met**.

**Reading.** Readers stop waiting, but every write pays for two applications and for the drain of the old copy, all inside the write critical section. With closed-loop clients and any real share of writes, write serialization sets throughput, so the overall effect is negative. Two directions remain if snapshot reads are wanted later:
- apply the old copy's update at the start of the next write instead of at the end of this one. That shortens the critical path only when writes are spaced out;
- structurally shared (persistent) graph storage, so a version costs O(changes). That is a much larger change.
