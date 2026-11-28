# Performance prototypes: reusable query scratch and snapshot reads (2026-11-28)

Recorded before any measurement. Diagnostic, short runs. Separate from the
v1.2.0 qualification (knotrel#182); nothing here is a qualification verdict.

**Baseline:** knotrel `main` at 7202dbe (contains #209 bidirectional search and
#210 FxHash ID maps). Each prototype lives on its own branch cut from 7202dbe
and is measured only against 7202dbe, so a result belongs to one change.

**Host:** the maintainer's M3 (8 CPUs), AC power, Docker stopped, same session.

## Prototype 1: reusable BFS scratch (`feature/query-scratch-reuse`)

Change: `Graph::connected` keeps its two queues and two mark bitsets in
thread-local scratch instead of allocating and zeroing them per call. Marks are
cleared from the queues after each query (O(visited), with a full clear when
cheaper). Retained capacity is capped per thread; scratch above the cap is
released after the query. Variants measured: capped (proposed) and uncapped.

Loads (core, public API, counting allocator; 1, 4, 8 and 16 threads sharing one
graph; 100,000 vertices):

| Id | Graph | Queries |
|---|---|---|
| S1 | random, 2N edges | random pairs (short, connected) |
| S2 | random, 2N edges, plus a separate 64-vertex component | small component to giant (short, disconnected) |
| L1 | chain | ends (long, connected) |
| L2 | cycle | opposite vertices (long, connected) |
| L3 | chain split in the middle | ends (long, disconnected) |
| P | chain of 1,000,000, then random 100k | one large query per thread, then 10,000 short ones: live heap after each phase |

Plus one server check: `contention-probe` standalone read95, batch 8, 16
clients, 100k random graph: requests/s, p99, server RSS.

Measures: per-query latency p50 and p99, allocations and bytes allocated per
query, live heap retained per thread after P.

Success (adopt if all hold):
1. S1 and S2 p50 improve by at least 10 % at 1 and at 16 threads.
2. L1, L2 and L3 are not more than 5 % worse (median over 3 alternating
   processes and two code layouts, default and `-align-loops=64`).
3. Steady-state allocations per query are 0.
4. Capped variant: retained scratch after P at most 256 KiB per thread.

Budget: implementation 1.5 h; host measurement 20 min.

## Prototype 2: snapshot reads (`feature/snapshot-reads`)

Change: the server keeps two copies of the graph state (left-right). Read-only
jobs take a shared guard on the current copy with `try_read` and never park on
a writer; writers serialize on a writer mutex, apply a job to the inactive copy,
publish it by swapping the current index, then bring the other copy up to date.
A read job (all queries of one batch) holds one copy for its whole duration.

Consistency checks (tests on the branch, must pass 100 %):
- every query of one read batch sees one version;
- a concurrent reader observes a write batch entirely before or entirely after
  it (writers alternate two-edge batches; readers query both edges in one
  batch and must never see one edge without the other).

Loads (`contention-probe`, 100k random graph, 16 clients, 20 s measure):

| Id | Mode | Mix |
|---|---|---|
| R | standalone | read95, batch 8 |
| F | source-managed, lifecycle | read100, batch 8, background feeder events |
| W | standalone | mixed50, batch 64 (write-heavy, expected cost) |

Measures: query requests/s and p99; write latency (server lock wait plus
execution of write jobs); feeder events/s; server RSS idle after load, peak
during F, and while a reader holds an old copy.

Success (adopt if all hold):
1. R: query p99 at least 30 % lower and throughput at least 20 % higher.
2. F: feeder events/s not more than 10 % lower, query p99 lower.
3. Write latency at most 2x the baseline.
4. Memory at most 2.2x the baseline graph state.
5. Consistency checks pass.

Budget: implementation 3.5 h; host measurement 30 min.

## Report

One table per prototype (benefit, cost, favoured loads, penalized loads,
recommendation). The merge decision is left to the maintainer.
