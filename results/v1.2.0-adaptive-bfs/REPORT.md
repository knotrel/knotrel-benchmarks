# Adaptive bidirectional BFS: impact estimate result

**Kind.** Impact estimate under the per-release measurement policy (knotrel#186), for a
single candidate. The v1.2.0 release verdict stays with knotrel#182: 9faf168 stays not
qualified, and attempt 1 stays valid.

| | |
|---|---|
| **Protocol** | knotrel `docs/design/adaptive-bfs-impact-estimate.md`, approved by the maintainer with R10 deciding; commit 841ceda, SHA-256 `40838c51…f9955`. Committed 16:50 +01:00, before implementation and measurement |
| **Candidate** | knotrel#204 at f9de542 |
| **Arms** | `v110` 57c35e8; `bfs196` 9faf168; `cand` f9de542 |
| **Tooling** | knotrel-benchmarks e0a7b3bc (`prepare_adaptive.sh`, `run_adaptive.py`, `analyze_adaptive.py`, `diagnostic_d.py`) |
| **Freeze** | `FREEZE.json`: 95299224, 17:18 +01:00 |
| **Builds** | all 12 `cargo +1.100.0 build --release --offline --locked` (`run1/build-summary.txt`) |
| **Window** | 17:22–18:00 +01:00, 38.5 min of the 60-minute cap; swap-ins and swap-outs 0 before and after (`run1/host-*.txt`); Docker stopped |
| **Evidence** | `run1/raw/K.jsonl`, `run1/raw/L/`, `run1/analysis-core.json`, `run1/run.log`, `run1/V-block*.log`, `run1/D/`. The V1 pair records (`raw/V`, with local paths) are kept on the host under `evidence/v1.2.0-adaptive-bfs-f9de542/run1/raw/V` |

**Freeze 1 was voided before any observation.** At block 0, the frozen V1 provenance check
of `run_p0_aa.py` refused the candidate's derived A-harness lockfile. That candidate,
b1ab7d5, had moved `fixedbitset` to the dev-dependencies of `knotrel-core`
(`freeze1-void/`).
- The candidate was revised to keep `FixedBitSet` as the storage of the same two-bit
  marks: one allocation, read and written by whole blocks.
- The rule, thresholds, cells, criteria and tooling are unchanged.
- It was re-frozen before any measurement.

**Analyzer validation before the freeze.** `analyze_adaptive.py --validate-attempt1`
reproduced exactly the published attempt-1 classes of all 16 K1 cells and of the 4 V1 core
cells.

## Outcome: REJECT, decided by the core blocks. The feeder (F) was skipped by protocol.

| Criterion | Result |
|---|---|
| C1 Correctness | **holds**. knotrel#204 CI: 37 pass, 1 skipped, including the random-history and protocol-case differential tests in both endpoint orders. 1,248 K1 runs and 108 #181 probe runs exit 0, with matching fingerprints and verify records. Both V1 blocks exit 0 |
| C2 Recovery against v1.1.0 (R1–R10) | **fails**: R1–R9 are `REGRESSION`; R10 is `INCONCLUSIVE_DISCLOSED`. Among the other K1 cells, sustained-churn-path 10k and both sustained-churn-blocks cells are `REGRESSION` |
| C3 Gains kept against #196 (G1–G12, ρ ≥ 0.80) | **fails**: G7 (#181 ring 10k) ρ = 0.56 and G8 (ring 100k) ρ = 0.73. The blocks guards are `REGRESSION` against v1.1.0 |
| C4 Feeder | **not run**: C2 and C3 already make REJECT certain (protocol section 5) |

Feeder recovery kept against #196, and the distance from the Q3 50 % threshold at 16
clients: **not measured**, because F was skipped by protocol. The last measured values stay
those of #182 attempt 1, where #196 was at 48.5 % (−1.5 points).

## Comparison 1: recovery against v1.1.0 (frozen #182 rules; verdicts under their native names)

K1: medians of `workload_wall_ns` over 24 pairs, ratio interval [r(7), r(18)] (97.73 %),
class from `analyze_cf5.classify_paired`, time margin 0.10. V1: `evaluate_cell` (v0.4.0
rules, final, n = 24), primary interval in %.

| # | Cell | v1.1.0 | cand | cand / v1.1.0 | Native class |
|---|---|---|---|---|---|
| R1 | K1 chain-split-rejoin 10k | 4.39 ms | 6.38 ms | 1.49 [1.42, 1.61] | `REGRESSION` |
| R2 | K1 chain-split-rejoin 100k | 40.45 ms | 71.47 ms | 1.58 [1.42, 1.84] | `REGRESSION` |
| R3 | K1 cycle-alternatives 10k | 7.40 ms | 10.24 ms | 1.40 [1.36, 1.44] | `REGRESSION` |
| R4 | K1 cycle-alternatives 100k | 65.08 ms | 98.36 ms | 1.52 [1.46, 1.61] | `REGRESSION` |
| R5 | K1 components-join-split 10k | 4.94 ms | 6.04 ms | 1.21 [1.20, 1.25] | `REGRESSION` |
| R6 | K1 components-join-split 100k | 44.28 ms | 52.14 ms | 1.19 [1.15, 1.25] | `REGRESSION` |
| R7 | K1 sustained-churn-path 100k | 4.77 ms | 7.29 ms | 1.52 [1.47, 1.57] | `REGRESSION` |
| R8 | V1 sparse traversal compact-bfs | 4.49 ms | 5.89 ms | primary [+25.8, +38.1] % | `REGRESSION` |
| R9 | V1 sustained churn compact-bfs | 0.67 ms | 1.11 ms | primary [+64.5, +68.5] % | `REGRESSION` |
| R10 | V1 sparse traversal **compact-workspace** | 5.53 ms | 5.77 ms | primary [+0.8, +11.5] %, median +5.4 % | `INCONCLUSIVE_DISCLOSED` |

**Other K1 cells against v1.1.0.**
- `PASS`: hub-alternatives 10k and 100k (0.011, 0.008); dense-bridge 512 and 2048 (0.53,
  0.49); redundant-bridge 512 and 2048 (0.30, 0.23).
- `REGRESSION`:
  - sustained-churn-path 10k, 1.47 [1.43, 1.50], which was `TIMER_LIMITED` in attempt 1;
  - sustained-churn-blocks 10k, 2.13 [2.12, 2.15];
  - sustained-churn-blocks 100k, 2.45 [2.44, 2.47].

V1 sustained churn compact-workspace: `PASS` (−0.3 %).

**R10 diagnostic (block D).** `connected_with_workspace` is the same 236 instructions in
both V1 builds, apart from three page-offset immediates of constant (panic-location)
addresses. It starts 68 bytes later in the candidate build: 0x…e84 → 0x…ec8, mod 64 from 4
to 8. These are the same addresses as in #182 attempt 1, where the cell was `REGRESSION`
[+7, +18] %; here it is `INCONCLUSIVE_DISCLOSED` [+0.8, +11.5] %. The code and its placement
are the same in both runs, yet the class differs. This is documented as a diagnostic
element; the adoption rule applies unchanged.

## Comparison 2: gains kept against #196

ρ = ln(t_v110 / t_cand) / ln(t_v110 / t_bfs196), from medians.

| # | Cell | Load protected | v1.1.0 | #196 | cand | cand / #196 | ρ |
|---|---|---|---|---|---|---|---|
| G1 | K1 hub-alternatives 10k | hub-endpoint queries | 20.67 | 0.233 | 0.224 | 0.96 [0.96, 0.97] | 1.01 |
| G2 | K1 hub-alternatives 100k | same | 207.9 | 1.594 | 1.566 | 0.98 [0.98, 0.99] | 1.00 |
| G3 | #181 hub 10k | random pairs, interior hubs | 116.7 | 4.94 | 5.06 | — | 0.99 |
| G4 | #181 hub 100k | same | 1,455 | 15.41 | 14.57 | — | 1.01 |
| G5 | #181 sparse 10k | giant and small components | 207.5 | 5.30 | 6.28 | — | 0.95 |
| G6 | #181 sparse 100k | same | 2,233 | 17.99 | 22.86 | — | 0.95 |
| G7 | #181 ring 10k | small world, degree ≤ 3 | 121.6 | 28.00 | 53.30 | — | **0.56** |
| G8 | #181 ring 100k | same | 1,341 | 97.78 | 197.1 | — | **0.73** |
| G9 | K1 dense-bridge 512 | dense frontiers | 104.0 | 61.96 | 55.04 | 0.89 | 1.23 |
| G10 | K1 dense-bridge 2048 | same | 1,576 | 939.4 | 778.9 | 0.83 | 1.36 |
| G11 | K1 redundant-bridge 512 | redundancy | 104.0 | 34.93 | 31.45 | 0.90 | 1.10 |
| G12 | K1 redundant-bridge 2048 | same | 1,575 | 433.9 | 361.7 | 0.83 | 1.14 |

- Times are medians in ms; for #181 cells, the per-process window time.
- Every G cell is faster than v1.1.0. The interval bounds per cell are in
  `analysis-core.json`.
- **The hub-endpoint load (G1, G2) is fully protected:** the start rule fixed the #203
  failure.
- The interior-hub and dense loads are kept or improved.
- **The ring load is not kept:** with degrees ≤ 3, frontier costs rarely differ by more
  than 2×, so the search often stays one-sided where #196 would balance.

## Block D: what the work counts explain (untimed, not deciding; `run1/D/work.json`)

**Path-like cells: exactly v1.1.0's work, still 1.2–1.6× its time.**
- On chain-split-rejoin, cycle-alternatives and sustained-churn-path, the candidate
  examines **exactly** v1.1.0's adjacency entries (W = 1.000), with **0 switches**. It
  behaves as a one-sided search, as section 1.3 predicted. On components-join-split
  connected queries it examines fewer (W = 0.63).
- Yet it is 1.2–1.6× v1.1.0's time. The remaining gap is a per-entry constant of the inner
  loop, not search work: the two-bit mark decode, the degree read and `pending` update per
  marked vertex, and the side bookkeeping, against v1.1.0's single bitset test and
  `neighbor == b`.
- **The rule did what it was designed to do, but no bidirectional bookkeeping measured so
  far is cheap enough to stay within 10 % of the one-sided v1.1.0 loop on these cells.**

**Hub-leaf.** In both endpoint orders: 1,100 entries for 500 connected queries, and 0 for
disconnected (isolated leaf). v1.1.0, hub first: 9.2 M and 103 M entries.

**Sustained-churn-blocks.** W = 0.95–0.99, with 1.8–2.9 switches per query, yet 2.1–2.5×
v1.1.0's time. The slowdown is not search work, and these data do not isolate it. Fixed
per-query costs are one candidate explanation (a mark array of 2V bits, two queues per
query, about 4,000 entries per query); this is not established.

## Consequence: this line of BFS experiments is closed (protocol section 6)

None of the three bidirectional implementations measured (#196, #203, this candidate)
clears the #182 path-like regressions against v1.1.0 within the frozen margins.

The maintainer's choice, as the protocol prescribes:

1. **Restore the v1.1.0 BFS** in `Graph::connected`. This clears R1–R9 by construction, and
   R10 is unaffected code. It gives up the #181 gains: the K1 hub and bridge gains, the
   #181 cells, and the feeder C=16 share, which returns to about 15 % (#181 base), far from
   Q3's 50 %.
2. **Reduce the v1.2.0 scope.** Either:
   - keep #196 and accept the path-like regressions explicitly, named in the release notes
     (the #182 plan §6.1 route); or
   - narrow v1.2.0 to changes that do not touch `Graph::connected`.

B2 on #87 stays open in both cases.
