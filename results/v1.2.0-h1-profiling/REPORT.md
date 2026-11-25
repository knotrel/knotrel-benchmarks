# v1.2.0 H1 profiling: feeder under query load, hub 10k lifecycle, #151 structures

**Kind: profiling (diagnostic).** Under the
[per-release measurement policy](../../docs/methodology.md#per-release-measurement-policy)
this is neither a release qualification nor an impact estimate. Nothing here is
qualification data, no verdict is computed, and no threshold is evaluated. The
numbers rank bottlenecks and select candidates for
[knotrel#181](https://github.com/knotrel/knotrel/issues/181) (H3) and inform
[knotrel#180](https://github.com/knotrel/knotrel/issues/180) (H2) and
[knotrel#87](https://github.com/knotrel/knotrel/issues/87). Issue:
[knotrel#179](https://github.com/knotrel/knotrel/issues/179).

## Provenance

| Item | Value |
| --- | --- |
| Date | 2026-11-25/26 |
| Knotrel | `57c35e8` (v1.1.0 release commit), clean code tree |
| Harness | knotrel-benchmarks `8a47e5ca`; `tools/lifecycle-probes/Cargo.lock` was regenerated offline for the build (2-line version bump to the 1.1.0 path crates) and restored afterwards, so probe records say `probes_dirty: true` |
| Builds | release profile with `CARGO_PROFILE_RELEASE_DEBUG=line-tables-only`, `STRIP=none` (symbols for `sample`); **not** the release build configuration |
| Host | Apple M3, 8 CPUs, 16 GB, macOS 26 (Darwin 25.5); PostgreSQL 18.7 container (`scripts/start-test-postgres.sh 18`); loopback |
| Host state | **Not controlled.** Spotlight indexing (`mds`, `mdworker`) was active during the Q3 runs, and `/usr/bin/sample` itself ran during each catch-up. Per-process CPU of these is in the `process_cpu.top_other` records. |
| Profiler | macOS `/usr/bin/sample`, 1 ms interval, all threads (on-CPU and blocked stacks) |
| Raw evidence | `~/workspace/knotrel/evidence/v1.2.0-h1-profiling-57c35e8/` on the maintainer host (full `sample` call trees, load logs, feeder logs); checksums in [`raw-MANIFEST.sha256`](raw-MANIFEST.sha256). This directory keeps the result records, the summary table and the top-of-stack excerpts. |

## 1. Feeder catch-up under query load (Q3 scenario)

**Setup.** The load tool of `integrations/postgres-feeder` (`examples/load.rs`)
in arm S (single host, per-process CPU accounting), scenario L2 G100k, backlog
100,000 changes, `C` = 0, 16, 64, two observations per cell, for `compact-bfs`
and `cluster-forest`. A watcher started `sample` on the server and on the feeder
for 2 s at the start of each catch-up (second feeder start of an observation).
Records: [`q3/`](q3/); table: [`q3/summary-table.txt`](q3/summary-table.txt).

| Engine | `C` | Catch-up rate (events/s), obs 1 / 2 | Share of `C`=0 (same rep) | Query batch execution (ms) | Feeder job lock wait (ms) | Feeder job execution (ms) | Knotrel cores |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compact-bfs | 0 | 147,047 / 170,491 | — | — | 0 | 1.46 / 1.41 | 0.25 / 0.28 |
| compact-bfs | 16 | 50,148 / 36,996 | 34 % / 22 % | 8.82 / 7.44 | 9.25 / 7.78 | 1.02 / 1.00 | 4.18 / 5.63 |
| compact-bfs | 64 | 36,871 / 42,009 | 25 % / 25 % | 12.50 / 12.17 | 12.33 / 11.67 | 1.09 / 1.26 | 4.45 / 4.26 |
| cluster-forest | 0 | 75,278 / 69,018 | — | — | 0 | 9.64 / 10.79 | 0.70 / 0.69 |
| cluster-forest | 16 | 65,486 / 63,076 | 87 % / 91 % | 0.01 / 0.02 | 0.03 / 0.08 | 10.88 / 10.99 | 1.39 / 1.25 |
| cluster-forest | 64 | 55,705 / 56,330 | 74 % / 82 % | 0.02 / 0.02 | 0.13 / 0.11 | 12.22 / 12.59 | 1.25 / 1.29 |

The shares are descriptive. They are higher than the qualification values for
compact-bfs (17.7 % and 9.4 % in v1.0.0) and come from a different build
configuration on an uncontrolled host, with two observations; they must not be
read as a Q3 result.

**Where the server's CPU goes (compact-bfs, `C`=16).** In the server sample of
observation 1 (`stack-tops/compact-bfs-srv6472.server.txt`), 10,725 of the
11,965 samples that were not blocked in the kernel (`__psynch_cvwait`,
`kevent`, `__psynch_mutexwait`, `__recvfrom`) had
`knotrel_core::Graph::connected` on top of the stack, about 90 %; across the
four compact-bfs samples with query clients (`C`=16 and 64) the share is
84–96 %. Feeder event
application (`LifecycleGraph::set_node_active`, `set_edge_enabled`,
`Graph::add_node`) appears with single-digit sample counts. With
`cluster-forest`, `connected` falls to 178 samples and the top on-CPU frames
are the forest's update paths (`list_remove`, `cut`, `hang_rank_trees`).

**Where a feeder job's time goes (compact-bfs).** About 93 jobs of about
1,000 events per catch-up:

| `C` | Time per job (catch-up / jobs) | In server phases (queue + lock + execution) | Outside server phases |
| --- | --- | --- | --- |
| 0 | 5.9–6.9 ms | about 2.4 ms | about 4–5 ms |
| 16 | 20–27 ms | about 10–11 ms (lock wait 7.8–9.3) | about 10–16 ms |

The feeder process is mostly blocked waiting for responses: its sample
(`stack-tops/compact-bfs-srv6472.feeder.txt`) is dominated by `__psynch_cvwait`
and `kevent`, with serialization and allocation frames in the tens of samples.
The feeder and PostgreSQL together used about 0.4–0.5 cores during catch-up
under load, while Knotrel used 4.2–5.6 of 8.

## 2. Hub 10k lifecycle `ops` and `events` (B4, E6)

**Setup.** `tools/lifecycle-probes` `http-lifecycle`, compact-bfs, hub, 10,000
nodes, 40 requests, 6 pairs plus 1 warm-up, seed 5,000,001, scenarios `ops`,
`events`, `ops-equivalent`, `events-equivalent`; `sample` attached to the whole
process for up to 30 s. Records: [`hub10k/`](hub10k/).

| Scenario | Candidate window, median (ms) | Reference window, median (ms) | Pairs |
| --- | --- | --- | --- |
| `ops` | 3.54 | 3.10 | 7 |
| `events` | 5.41 | 5.14 | 7 |
| `ops-equivalent` | 3.45 | 3.69 | 7 |
| `events-equivalent` | 5.55 | 6.42 | 7 |

**Profiling not warranted beyond this.** Each timed window lasts 3–7 ms, so a
1 ms sampler collects a handful of window samples per pair; the process
profile is dominated by untimed arm construction and JSON handling
(`stack-tops/*`). The open question for these two requirements is the
equivalence of the reference (atomicity of split chunks), not a performance
bottleneck; it is handled by the reference design proposed in
[knotrel#194](https://github.com/knotrel/knotrel/pull/194).

## 3. Structures targeted by #151 (heap accounting)

**Setup.** `core-lifecycle resources` built with `count-alloc`, 100,000 nodes,
no churn, seed 5,000,001 (the B5 configuration). Net live heap after
construction, from the allocator counter (deterministic, no interval needed).
Records: [`mem151/`](mem151/).

| Engine | Arm | Topology | Edges | Net heap (bytes) | Bytes per edge | Incidence entries / capacity | Catalog capacity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| compact-bfs | plain | sparse | 199,994 | 9,830,888 | 49.2 | — | — |
| compact-bfs | lifecycle | sparse | 199,994 | 24,118,704 | 120.6 | 399,988 / 557,116 | 114,688 |
| compact-bfs | plain | hub | 199,004 | 9,639,112 | 48.4 | — | — |
| compact-bfs | lifecycle | hub | 199,004 | 23,543,376 | 118.3 | 398,008 / 533,144 | 114,688 |
| cluster-forest | plain | sparse | 199,994 | 39,296,072 | 196.5 | — | — |
| cluster-forest | lifecycle | sparse | 199,994 | 53,583,888 | 267.9 | 399,988 / 557,116 | 114,688 |
| cluster-forest | plain | hub | 199,004 | 39,443,768 | 198.2 | — | — |
| cluster-forest | lifecycle | hub | 199,004 | 53,348,032 | 268.1 | 398,008 / 533,144 | 114,688 |

The lifecycle layer adds about 14.1–14.5 MB at this size for both engines,
about 60 % of the compact-bfs lifecycle total. Incidence capacity is about 1.4
times the entries (557,116 for 399,988). These are inputs to the #151 memory
formulas, not a prediction of B's saving.

## Ranked bottlenecks

| Rank | Bottleneck | Evidence | Affects | Candidate action |
| --- | --- | --- | --- | --- |
| 1 | **compact-bfs query execution**: `Graph::connected` is a one-directional BFS that allocates an O(V) bitset per call and, on G100k's giant component, explores a large part of it before meeting the target | 84–96 % of on-CPU server samples with query clients; query batch execution 7.4–8.8 ms (`C`=16) and 12.2–12.5 ms (`C`=64) for 8 queries; Knotrel at 4.2–5.6 cores | Q3, query latency, CPU left for feeder and PostgreSQL | H3 candidate: **bidirectional BFS** (smaller-frontier expansion) with reusable scratch, same answers and worst-case bound; impact estimate before adoption |
| 2 | **Feeder write-lock wait behind in-flight query batches** (task-fair lock: a writer waits for the readers already holding it) | 7.8–9.3 ms per job at `C`=16, about the length of one query batch; 0.03–0.13 ms with cluster-forest | Q3 | Shrinks with rank 1. B1 cannot preempt readers already running; B2 (bounded concurrent query execution) limits both concurrent readers and their CPU. Decided in #87's impact estimate |
| 3 | **Time outside the server's graph phases grows under load** (HTTP, feeder, PostgreSQL decoding on a saturated host) | about 4–5 ms per job at `C`=0, about 10–16 ms at `C`=16; feeder mostly blocked waiting; feeder plus PostgreSQL at about 0.4–0.5 cores | Q3 | Indirect: follows CPU taken by queries (rank 1). No feeder-side change indicated by this profile |
| 4 | **cluster-forest update cost** | feeder job execution 9.6–12.6 ms against 1.0–1.5 ms for compact-bfs; no-query catch-up 69–75k events/s against 147–170k | catch-up without queries on cluster-forest | Out of v1.2.0 scope (CF7 #178 is deferred); recorded for the engine guide |
| 5 | **Lifecycle layer memory** (incidences, catalog) | about 14 MB per 200k edges, 60 % of the compact-bfs lifecycle heap; incidence capacity about 1.4 × entries | RSS on large graphs | #151 option B (design under review) |

Not profiled, with the reason:
- Core engines other than the paths above (`ett`, `hdt`, cluster-forest
  queries): CF5 characterizes them on this host and the core code is unchanged
  since that campaign; no v1.2.0 change is being considered there.
- Imports, sparse and ring lifecycle churn: no v1.2.0 change is being
  considered on these paths.
- Hub 10k timed windows: see section 2.

## Limits

- One host, uncontrolled background load, symbolized non-release builds, two
  observations per Q3 cell. Profiles rank costs within a run; they do not
  measure the size of any improvement.
- The bidirectional-BFS gain is a hypothesis to be measured by an impact
  estimate with criteria fixed beforehand, not a result of this profile.
