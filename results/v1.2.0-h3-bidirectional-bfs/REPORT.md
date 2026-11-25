# v1.2.0 H3 impact estimate: bidirectional BFS for `compact-bfs` queries

**Kind: impact estimate** under the
[per-release measurement policy](../../docs/methodology.md#per-release-measurement-policy).
It decides adoption of one change and does **not** qualify v1.2.0; if adopted,
the core query path enters the scope of the v1.2.0 release qualification
([knotrel#182](https://github.com/knotrel/knotrel/issues/182)). Issue:
[knotrel#181](https://github.com/knotrel/knotrel/issues/181); change:
[knotrel#196](https://github.com/knotrel/knotrel/pull/196).

**Protocol:** [`docs/design/bidirectional-bfs-impact-estimate.md`](https://github.com/knotrel/knotrel/blob/1daee1b/docs/design/bidirectional-bfs-impact-estimate.md)
at knotrel `1daee1b`, committed (2026-11-25 23:12 UTC) before the first
observation (23:14 UTC, `host-before.txt`). Criteria were fixed by Claude under
the maintainer's delegation for the v1.2.0 plan.

## Outcome

**ADOPT** under the protocol's decision rule: correctness holds, all six
deciding core cells are FASTER, and both benefit conditions hold. One
deviation in the wording of the correctness condition is disclosed below; it
does not change the outcome.

## Provenance

| Item | Value |
| --- | --- |
| Base | knotrel `cd57816` (`origin/main`) |
| Candidate | knotrel `1daee1b` (base + the change only) |
| Harness | knotrel-benchmarks `8a47e5ca`, `tools/lifecycle-probes` built offline against each arm (lockfile regenerated for the build, so records say `probes_dirty: true`) |
| Builds | `cargo build --release --locked` (server), `--release --offline` (probe); hashes in [`binaries.sha256`](binaries.sha256) |
| Host | Apple M3, 8 CPUs, 16 GB, AC power; PostgreSQL 18.7 container; loopback |
| Window | 2026-11-25 23:14:45 – 23:34:55 UTC; swap-ins and swap-outs 0 before and after (cumulative counters) |
| Background | macOS indexing and media analysis were active at the start (`host-before.txt`); recorded, not removed |
| Evidence | [`A/`](A/), [`B/`](B/), [`run.log`](run.log) (every run exit 0), checksums in [`MANIFEST.sha256`](MANIFEST.sha256) |

## A. Core query cost (deciding)

`core-lifecycle pairs --exp ops --mix query`, `compact-bfs`, window 4,000,
seed 5,000,001, 2 pairs + 1 warm-up per process, 6 paired blocks with
alternating arm order. Statistic: median lifecycle-arm window time per process.
Interval: [min, max] of the 6 paired ratios (96.9 % distribution-free interval
for the median ratio).

| Topology | Nodes | Base, median (ms) | Candidate, median (ms) | Ratio (median) | Interval | Verdict |
| --- | --- | --- | --- | --- | --- | --- |
| sparse | 10,000 | 215.04 | 5.53 | 0.026 | [0.025, 0.027] | FASTER |
| sparse | 100,000 | 2,340.04 | 18.99 | 0.008 | [0.008, 0.008] | FASTER |
| ring | 10,000 | 122.17 | 28.19 | 0.231 | [0.228, 0.236] | FASTER |
| ring | 100,000 | 1,359.38 | 99.65 | 0.073 | [0.072, 0.074] | FASTER |
| hub | 10,000 | 118.01 | 5.02 | 0.043 | [0.042, 0.043] | FASTER |
| hub | 100,000 | 1,468.67 | 15.90 | 0.011 | [0.011, 0.011] | FASTER |

Every run's untimed verify record matched, and the answer digests and end-state
digests are **identical between base and candidate** in every cell and block.

These ratios cover the probe's query-heavy lifecycle trace on these generated
topologies only. They are not a general speedup claim; queries whose endpoints
lie in different large components were not isolated, and the protocol's known
risk (negative queries from a small into a large component) is not measured
separately here.

## B. Feeder under query load (benefit; descriptive otherwise)

Load tool at the base commit, `LOAD_ENGINE=compact-bfs`, default window and
backlog, 3 observations per arm per cell, arms alternating per repetition.
No Q verdict is issued here; Q1–Q5 thresholds are unchanged and the v1.2.0 Q3
verdict belongs to #182.

| Cell | Arm | Catch-up rate (events/s), 3 obs | Median share of `C`=0 | Time to `ready` (s) | Query batch execution (ms) | Feeder lock wait (ms) | Query requests/s | Query p99 (ms) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| L2 G100k `C`=0 | base | 183,380 / 146,581 / 178,159 | — | 0.52 / 0.65 / 0.53 | — | 0 | — | — |
| L2 G100k `C`=0 | candidate | 176,995 / 179,883 / 177,960 | — | 0.53 / 0.53 / 0.53 | — | 0 | — | — |
| L2 G100k `C`=16 | base | 23,747 / 26,762 / 28,191 | 15.0 % | 3.98 / 3.54 / 3.36 | 6.71–7.17 | 7.01–7.52 | 1,250–1,332 | 64.5–80.5 |
| L2 G100k `C`=16 | candidate | 104,256 / 77,799 / 73,839 | 43.7 % | 0.91 / 1.22 / 1.28 | 0.05–0.06 | 0.08–0.18 | 33,333–37,193 | 2.5–3.1 |
| L2 G100k `C`=64 | base | 16,377 / 20,444 / 17,178 | 9.6 % | 5.78 / 4.63 / 5.51 | 12.59–13.12 | 10.95–13.85 | 1,230–1,246 | 108.1–131.3 |
| L2 G100k `C`=64 | candidate | 66,404 / 73,283 / 68,255 | 38.4 % | 1.42 / 1.29 / 1.39 | 0.05–0.06 | 0.11–0.41 | 35,268–39,364 | 5.2–6.6 |

| L1 G100k `C`=16 | Query requests/s | Query p99 (ms) | Marker lag p50 (ms) | Marker lag p99 (ms) | Query errors | Q2 rule |
| --- | --- | --- | --- | --- | --- | --- |
| base | 1,211 / 1,108 / 1,095 | 64.0 / 87.2 / 84.2 | 35.5 / 38.6 / 38.2 | 125.1 / 128.5 / 119.6 | 0 | pass ×3 |
| candidate | 42,019 / 41,381 / 43,936 | 1.6 / 1.6 / 1.5 | 30.7 / 27.2 / 27.3 | 58.1 / 57.6 / 57.5 | 0 | pass ×3 |

Shares use each arm's own `C`=0 median (base 178,159, candidate 177,960
events/s). The query clients are closed-loop, so the candidate's clients sent
about 30 times as many requests while the backlog drained; the catch-up shares
are therefore measured under a much higher offered query load than the base's.

## Decision rule, item by item

1. **Correctness: holds.** Workspace tests (including the new all-pairs
   differential test), Clippy, Rustdoc, the core MSRV job and the rest of CI
   pass on #196 (37 checks). Every probe verify record matches, and answers are
   identical across arms. The load tool reported no query error in any
   observation and the Q2 rule passed in every L1 observation.
   **Deviation (wording):** the protocol named "Q2-style final-state agreement";
   the load tool's Q2 is the freshness and retained-WAL rule and the tool has no
   separate final-state comparison. The correctness evidence actually used is
   the list above.
2. **No regression in A: holds.** No cell SLOWER, none INCONCLUSIVE.
3. **Benefit: holds, both ways.** All three 100,000-node cells are FASTER (two
   required). In B, the candidate's median L2 G100k `C`=16 share is 43.7 %
   against 15.0 % (2.9 times; 1.2 required), with lower query batch execution.

## Limits

- One host, one session, background system activity at the start.
- Part B is descriptive beyond the benefit check; the shares are not a Q3
  verdict. Descriptively, the candidate's `C`=16 share (43.7 %) is still below
  Q3's 50 % threshold and its `C`=64 share (38.4 %) is above the 25 % one;
  only #182 decides.
- The disconnected-pair risk stated in the protocol remains unmeasured as a
  separate cell.
