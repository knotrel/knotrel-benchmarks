# Bidirectional BFS per-layer fix: impact estimate result

**Kind:** impact estimate under the per-release measurement policy (knotrel#186). It decides
adoption of one change. It does not qualify v1.2.0: candidate 9faf168 stays not qualified,
and attempt 1 of knotrel#182 stays valid.

| | |
|---|---|
| **Protocol** | knotrel `docs/design/bidirectional-bfs-layer-fix-impact-estimate.md` at eedcf34, committed 2026-11-27 16:03 +01:00, before the first observation (16:08) |
| **Change** | knotrel#203 |
| **Arms** | `prev` 9faf168 (the #196 search); `fix` eedcf34; `v110` 57c35e8 |
| **Tooling** | knotrel-benchmarks 72473c30, built per arm with `cargo +1.100.0 build --release --offline` (`build.sh`, `logs/build-summary.txt`) |
| **`--locked`** | all builds except the `fix` harness and probes. Their lockfiles drop `fixedbitset` from the `knotrel-core` entry, one line each (`logs/*.lock-derivation.diff`) |
| **Host** | Apple M3, AC power, `caffeinate`, Docker stopped |
| **Window** | 15:08:29–15:12:42 UTC; swap-ins and swap-outs 0 before and after (`host-*.txt`) |
| **Evidence** | `raw/A.jsonl`, `raw/B/`, `run.log` (every run exit 0), `binaries.sha256`, `analysis.json` (from `analyze_estimate.py`) |

## Outcome: REJECT. `main` keeps the #196 search; knotrel#203 is closed as "no change".

| Rule | Result |
|---|---|
| 1. Correctness | **holds** for the runs: 576 harness runs and 72 probe runs exit 0, trace fingerprints match across arms, every probe verify record matches. knotrel#203 CI: 39 checks pass, 1 skipped (workspace tests with the new differential test, Clippy, Rustdoc, core MSRV) |
| 2. Path-like benefit (≥ 6 of 8 FASTER, none SLOWER) | **fails**: 5 FASTER, 3 NEUTRAL |
| 3. No loss in the gain regime (no SLOWER) | **fails**: hub-alternatives 10k and 100k and sustained-churn-blocks 10k and 100k are SLOWER |
| 4. Feeder guard (C) | **not run** |

Block C (feeder, needs Docker) was not run. Rules 2 and 3 had already fixed the outcome,
and no C result could change it. This is a disclosed deviation from the protocol's list of
cells; no threshold was changed.

## A. K1 workloads: 12 paired blocks, [r(3), r(10)] intervals, 96.1 %

Times: median `workload_wall_ns` in ms. Verdict thresholds as in the protocol: FASTER if
r(10) < 0.90, SLOWER if r(3) > 1.10.

| Set | Workload | N | v1.1.0 | prev | fix | fix/prev | Verdict | fix/v1.1.0 (descriptive) |
|---|---|---|---|---|---|---|---|---|
| path-like | chain-split-rejoin | 10k | 4.19 | 9.73 | 6.64 | 0.68 [0.66, 0.69] | FASTER | 1.60 [1.47, 1.71] |
| path-like | chain-split-rejoin | 100k | 38.73 | 103.37 | 65.56 | 0.63 [0.62, 0.66] | FASTER | 1.66 [1.34, 1.77] |
| path-like | cycle-alternatives | 10k | 7.51 | 11.95 | 8.99 | 0.75 [0.74, 0.78] | FASTER | 1.20 [1.17, 1.21] |
| path-like | cycle-alternatives | 100k | 62.17 | 115.50 | 75.12 | 0.65 [0.64, 0.67] | FASTER | 1.20 [1.20, 1.21] |
| path-like | components-join-split | 10k | 5.05 | 6.62 | 6.96 | 1.05 [1.01, 1.08] | NEUTRAL | 1.39 [1.32, 1.45] |
| path-like | components-join-split | 100k | 42.30 | 63.95 | 64.84 | 1.00 [0.99, 1.02] | NEUTRAL | 1.51 [1.49, 1.58] |
| path-like | sustained-churn-path | 10k | 0.73 | 1.04 | 1.07 | 1.02 [1.01, 1.03] | NEUTRAL | 1.45 [1.44, 1.46] |
| path-like | sustained-churn-path | 100k | 4.79 | 7.37 | 6.23 | 0.83 [0.82, 0.86] | FASTER | 1.30 [1.29, 1.32] |
| low-diameter | hub-alternatives | 10k | 20.75 | 0.23 | 9.79 | 42.0 [41.5, 48.3] | **SLOWER** | 0.47 |
| low-diameter | hub-alternatives | 100k | 208.65 | 1.59 | 87.66 | 55.0 [54.7, 55.1] | **SLOWER** | 0.42 |
| low-diameter | dense-bridge-churn | 512 | 104.23 | 62.24 | 52.01 | 0.84 [0.83, 0.84] | FASTER | 0.50 |
| low-diameter | dense-bridge-churn | 2048 | 1586.3 | 944.8 | 754.9 | 0.80 [0.80, 0.80] | FASTER | 0.48 |
| low-diameter | redundant-bridge-churn | 512 | 104.09 | 35.04 | 29.77 | 0.85 [0.85, 0.85] | FASTER | 0.29 |
| low-diameter | redundant-bridge-churn | 2048 | 1583.2 | 436.6 | 351.2 | 0.80 [0.80, 0.81] | FASTER | 0.22 |
| blocks | sustained-churn-blocks | 10k | 1.28 | 1.49 | 1.77 | 1.20 [1.18, 1.21] | **SLOWER** | 1.38 [1.36, 1.42] |
| blocks | sustained-churn-blocks | 100k | 7.59 | 7.83 | 8.81 | 1.13 [1.12, 1.14] | **SLOWER** | 1.16 [1.15, 1.18] |

## B. #181 A cells: 6 paired blocks, [min, max], 96.9 %

| Topology | N | prev (ms) | fix (ms) | fix/prev | Verdict |
|---|---|---|---|---|---|
| sparse | 10k | 5.30 | 5.15 | 0.98 [0.97, 1.06] | NEUTRAL |
| sparse | 100k | 18.00 | 17.70 | 0.98 [0.95, 1.02] | NEUTRAL |
| ring | 10k | 28.02 | 29.10 | 1.04 [1.04, 1.04] | NEUTRAL |
| ring | 100k | 98.17 | 103.99 | 1.06 [1.03, 1.10] | NEUTRAL |
| hub | 10k | 4.93 | 4.18 | 0.85 [0.85, 0.85] | FASTER |
| hub | 100k | 15.45 | 9.95 | 0.64 [0.64, 0.65] | FASTER |

## What the result teaches (descriptive, from the per-query totals in `raw/A.jsonl`)

1. **The leaner bookkeeping works where it was aimed.**
   - On chains and cycles, where work is identical, the single mark array and the cursor
     queues cut time by 25–37 % against `prev`.
   - Dense and redundant bridges improved by 15–20 %, and #181 hub by 15–36 %.
2. **The degree read was load-bearing; replacing it was the mistake.**
   - hub-alternatives connected queries (0, v) pair a hub of degree N−1 with a vertex of
     degree 3. `prev` expands the low-degree side first and meets the hub at once (0.18 ms
     for 500 queries at 100k).
   - The fix balances by frontier vertex count, so it ties at 1:1 and expands the hub:
     86 ms.
3. **Alternating on ties doubled disconnected work on paths.**
   - On two separated half-chains, `prev`'s `<=` tie-break keeps expanding the source side
     until it is exhausted. The fix alternates and walks both halves.
   - Disconnected-query time on components-join-split 100k: `prev` 34.2 ms, `fix` 44.0 ms,
     v1.1.0 17.9 ms. Blocks show the same effect.
   - Connected queries improved instead: 29.6 ms to 20.5 ms against v1.1.0's 24.4 ms.
4. **Even where the fix helps, path-like cells stay 1.2–1.7× v1.1.0.**
   - This is beyond the frozen K1 time margin of 0.10.
   - A layer-synchronous bidirectional search with one-vertex layers keeps a cost that the
     v1.1.0 single-queue scan does not have. Leaner bookkeeping alone does not close the
     #182 regressions.

## Consequences for the next candidate

- **`main` keeps the #196 search.** The 10 deciding #182 regressions stay open.
- The diagnosis recommendation of a circumscribed fix is **not borne out as implemented**.
  A next attempt would need, at least:
  - degree-based balancing, kept as in `prev`;
  - the `prev` tie-break;
  - the leaner mark array and queues;
  - and, to approach v1.1.0 on paths, a way to avoid per-layer switching while one side's
    frontier stays narrow.
- That last part is an adaptive element. These data now support one, which the
  diagnosis's work counts alone did not show.
- Any such design needs its own protocol and estimate. None is started here.
