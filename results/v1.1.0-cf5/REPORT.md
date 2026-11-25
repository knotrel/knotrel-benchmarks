# v1.1.0 CF5: performance qualification of `cluster-forest` — report, attempt 1

**Status: FINAL for attempt 1, published with one accepted limitation (D1).**
The maintainer's decisions of 2026-11-25, taken after the session, are recorded in
section 7. Nothing in this file changes a class, an interval or a threshold. Every class
is the one the analyzers computed.

> **Limitation (D1): host swap activity not verifiable; results accepted by the
> maintainer with this limitation.** Swap occupancy was 738.25 MB at the start and at all
> 30 snapshots, and 722.25 MB at the end. The 192 zero values of `swaps` concern only the
> V1 processes observed. This applies to every class below, PASS included.

Three statements, which should not be confused:

1. **Session execution: COMPLETE.** Session 1 ran every scheduled step within the
   15-hour cap. It had no interruption, no rerun, no infrastructure failure and no
   correctness failure. No second session is needed or possible (plan section 8.1).
2. **Conformance: accepted with an explicit exception (D1).** The maintainer reads "no
   swap" as no swap activity during the measurement. The attempt's data record only swap
   occupancy, which was stable. No system-wide swap-in or swap-out counter covers the
   window, so swap activity is **not verifiable**. The maintainer accepted the use and
   publication of the attempt's results with an exception limited to that check. The
   attempt is closed without a rerun. Future campaigns record the cumulative counters
   before and after the window (section 7, D1).
3. **Coverage: all 226 comparisons have an outcome.**
   - 211 come from the frozen analyzers.
   - The 15 L2 comparisons come from the revised L2 analyzer (D2, section 6, L2). It
     produced a verdict where the frozen one refused the run.
   - L2 has 2 C3 FAIL and 9 C4 EXCEEDS_BUDGET (section 6, L2). The two C3 FAILs are
     accepted as a documented limitation of the `cluster-forest` lifecycle on the sparse
     1 000-node graph; memory stability for those two workloads stays open (D5).

The plan is knotrel `docs/releases/v1.1.0-cf5-qualification-plan.md`, revision 5, as
amended on 2026-11-24 (PostgreSQL for S3).

## 1. What was measured

| | |
|---|---|
| Candidate | knotrel `02cba6825f9ad9ef769f4006428ccad5509076e9` (PR #152 on `main`), clean checkout |
| Baseline (V blocks) | knotrel v1.0.0, built from source with the same toolchain and flags |
| Tooling | knotrel-benchmarks freeze commit `f4d41f19869c0a63baa0ce32d91ab02c1dd1522f` (`FREEZE.json`: tooling `ff6889e7`, matrix sha256 `cc3473e4…2380`), clean checkout |
| Host | Apple M3 (8 cores), 16 GB, macOS 26.5.2 (Darwin 25.5.0), toolchain 1.100.0, AC power throughout, `caffeinate -ims`. Server, PostgreSQL (S3 only) and load generator on the same machine |
| Session 1 | 2026-11-24 19:57:19Z to 2026-11-25 08:17:54Z: **12 h 20 min** of a 15 h cap (estimate in plan section 11: 12.6 h) |
| Order seed | `795524442842124889`, derived from the matrix hash and the candidate SHA (`order_seed_derived: true`) |
| Schedule | 4 374 steps: 1 smoke, 4 342 measured pairs (2 warmup pairs and 24 measured pairs per paired cell), 28 deterministic, 3 delegated |
| Raw evidence | private bundle `v1.1.0-cf5-attempt1-02cba68-f4d41f1`. Checksums of every session output in `analysis/attempt1/campaign-outputs-sha256.txt` (671 files) and of the 15 binaries in `analysis/attempt1/binaries-sha256.txt` |

## 2. Session execution

- **Every step ran.** `status.json` reports `campaign: complete`, `end_cause: all steps ran`.
  - 195 of 195 paired and deterministic cells are COMPLETE. Every timed cell has 24 pairs.
  - The 3 delegated blocks are DELEGATED_DONE at their first attempt.
  - No observation exited non-zero. No rerun was used.
- **Correctness gate.** The tier-1 smoke ran every distinct arm (274 records) before any
  measured pair, with the answers checked. Every measured observation passed its gate.
  A failure would have stopped the campaign as a FAIL.
- **Integrity.** These were checked after the session:
  - the 10 executables hashed in the record still match;
  - `shasum -a 256 -c binaries-sha256.txt`: 15 of 15 OK;
  - the candidate and benchmarks checkouts are clean at the recorded SHAs.
- **S3 PostgreSQL lifecycle** (plan section 8 amendment), from `s3-lifecycle.log`:
  - Docker Desktop started at 04:56:48Z;
  - pinned `postgres:18.7-alpine@sha256:ff64c9e3…` ready at 04:56:54Z;
  - S3 exited 0 at 05:35:43Z;
  - container removed, then Docker Desktop quit with its virtual machine gone at 05:35:53Z.
  - Every other block ran with no Docker or PostgreSQL. The admin URL was passed only in S3's
    environment and appears in no file.
- **Block times** (from the host snapshots):

  | Tier | Block | Start (Z) | Duration |
  |---|---|---|---|
  | 1 | smoke | 19:57 | 45 min |
  | 1 | V1 | 20:42 | 27 min |
  | 1 | V2 | 21:09 | 25 min |
  | 2 | K1 | 21:34 | 44 min |
  | 2 | K2 | 22:18 | 5 h 29 min |
  | 2 | S1 | 03:47 | 57 min |
  | 2 | L1 | 04:44 | 12 min |
  | 2 | S3 | 04:56 | 39 min (own cap 90 min) |
  | 3 | K3 | 05:35 | 36 min |
  | 3 | K4 | 06:11 | 8 min |
  | 3 | L3 | 06:19 | 6 min |
  | 3 | L4 | 06:25 | 1 min |
  | 3 | L2 | 06:26 | 2 min |
  | 3 | V3 | 06:27 | 24 min |
  | 3 | K2x | 06:51 | 1 h 26 min |

- **Host conditions** (recorded before and after every block, `session1-status.json`):
  - AC power throughout. No thermal or performance warning was recorded at any snapshot.
  - **Swap occupancy** (`sysctl vm.swapusage`, the only system-wide swap value
    recorded): 738.25 MB used of 2 048 MB at the start, identical at all 30 snapshots
    through the end of K2x, and 722.25 MB at the end.
  - **Swap activity: not recorded** for the whole window, and so not verifiable (section
    7, D1: accepted as a limitation). The data were
    searched for cumulative counters:
    - the runner's snapshots record occupancy only;
    - the L2 run log records power, load and thermal state only;
    - the only counter, `swaps` in V1's `/usr/bin/time -l` output (192 values, all 0),
      is per child process (`ru_nswap`). It covers only the V1 observations, not the
      host.
  - The system's cumulative `Swapins` and `Swapouts` (`vm_stat`) exist, but no reading
    was taken at the start of the session, so no delta can be computed afterwards.
  - **Load average** (1 min):
    - about 2 between blocks, with the Claude desktop app open;
    - 8–15 right after the multithreaded and server blocks (smoke, V2, S1, S3, V3), which
      the blocks themselves produce;
    - back to about 2 by the next block.
  - As in v1.0.0, load is recorded as context. The runner enforces no idle threshold.

## 3. Regression checks against v1.0.0 (V1, V2): plan section 7.1

### 3.1 V1: frozen v1.0.0 experiment A protocol

**Protocol note (approved with revision 5).** V1 follows the frozen v1.0.0 experiment A
protocol (`analyze_v100q_a.py`, rule set v0.4.0, fixed n = 24, `link_p99_ns` and
`cut_p99_ns` of the four core cells REPORT_ONLY). Its PASS is a PASS **under that protocol**.
It does not apply the section 6.1 TIMER_LIMITED rule, and it is **not a general guarantee on
measurement error**.

| Cell | Outcome | Primary metric, interval (tolerance) | Non-PASS element |
|---|---|---|---|
| core sparse traversal 10k, compact-bfs | PASS | `workload_wall_ns` [−4.9 %, +2.3 %] (10 %) | — |
| core sparse traversal 10k, compact-workspace | PASS | `workload_wall_ns` [−6.4 %, +9.9 %] (10 %) | — |
| core sustained churn 10k, compact-bfs | PASS | `workload_wall_ns` [−1.0 %, +0.6 %] (10 %) | — |
| core sustained churn 10k, compact-workspace | PASS | `workload_wall_ns` [−0.7 %, +0.6 %] (10 %) | — |
| HTTP batch b8 | PASS | `window_duration_ns` [−7.1 %, +7.1 %] (10 %) | — |
| HTTP batch b256 | PASS | `window_duration_ns` [−2.8 %, +4.9 %] (10 %) | — |
| **HTTP batch b1** | **UNRESOLVED** | `window_duration_ns` PASS [−6.2 %, +9.0 %] (10 %) | `request_latency_p99_ns` INCONCLUSIVE [−41.9 %, +73.8 %] (25 %) |
| **HTTP batch b64** | **UNRESOLVED** | `window_duration_ns` PASS [−4.2 %, +3.4 %] (10 %) | `sampled_max_rss_bytes` INCONCLUSIVE [0.0 %, +22.1 %] (20 %) |
| **HTTP lifecycle small** | **INCONCLUSIVE_DISCLOSED** | `time_to_ready_ms` INCONCLUSIVE [−18.3 %, +25.9 %] (10 %) | the primary metric |

The full per-metric output is in `analysis/attempt1/analysis-session1-V1.json`.

Every V1 and V2 class, PASS included, carries the D1 limitation: host swap activity not
verifiable.

**No V1 result is REGRESSION or FAIL.** Three are inconclusive (2 UNRESOLVED,
1 INCONCLUSIVE_DISCLOSED). Under section 7.1 an inconclusive result is no evidence either
way: it is neither a regression nor a pass. The maintainer's disposition is in section 7, D3.

### 3.2 V2: `analyze_cf5.py`, with the section 6.1 rule

| Cells | Outcome |
|---|---|
| 6 M_reg cells, `compact-bfs` (throughput 10 %, p99 25 %) | 12 of 12 metrics PASS |
| `chain-split-rejoin-v1` 100 000, `hdt` | PASS [−3.2 %, −0.2 %] |
| `sustained-churn-path-v1` 100 000, `hdt` | PASS [−3.1 %, +4.0 %] |
| **`chain-split-rejoin-v1` 100 000, `ett` (scan)** | **TIMER_LIMITED**: interval [−2.2 %, +1.8 %], δ = 0.098. The class without the limit (PASS) is published and not counted |
| **`sustained-churn-path-v1` 100 000, `ett` (scan)** | **TIMER_LIMITED**: interval [−3.5 %, +2.6 %], δ = 0.097. The class without the limit (PASS) is published and not counted |

**No V2 result is REGRESSION.** There are 14 PASS and 2 TIMER_LIMITED. Under section 7.1 a
V2 TIMER_LIMITED is handled as INCONCLUSIVE: it needs a maintainer disposition and is
never a pass or a regression (section 7, D3). The two `ett` cells have medians of about
0.35 ms and 1.8 ms. These are wall times that include per-operation timing (section 5).

## 4. `cluster-forest` against the existing engines

Classes as computed, published with the D1 limitation (host swap activity not
verifiable; results accepted by the maintainer with this limitation). Every cell, metric, median, interval and δ is in
[`analysis/attempt1/CELLS.md`](analysis/attempt1/CELLS.md). Core (K, L) and end-to-end
(S) results are reported separately, as plan section 4.3 requires.

### 4.1 Class counts per block (all metrics)

| Block | vs compact-bfs | vs ETT | vs HDT |
|---|---|---|---|
| K1 (48) | 8 FASTER, 8 SLOWER | 4 FASTER, 11 SLOWER, **1 TIMER_LIMITED** | 6 FASTER, 8 SLOWER, **2 TIMER_LIMITED** |
| K2 (18 × 2) | 6 FASTER, 6 SLOWER | 1 FASTER, 9 SLOWER, 2 EQUIVALENT | 5 FASTER, 3 SLOWER, 3 EQUIVALENT, 1 INCONCLUSIVE |
| K2x (9 × 2) | 6 SLOWER | 3 FASTER, 3 SLOWER | 4 FASTER, 1 EQUIVALENT, 1 INCONCLUSIVE |
| K3 (36) | 12 SLOWER | 12 FASTER | 12 FASTER |
| K4 (18 × 4) | 24 LARGER | 19 SMALLER, 5 SIMILAR | 24 SMALLER |
| L1 (11) | 3 FASTER, 8 SLOWER | — | — |
| L3 (11) | 10 SLOWER, 1 INCONCLUSIVE | — | — |
| L4 (10 × 2) | 19 LARGER, 1 SIMILAR | — | — |
| S1 (14 × 2) | 12 FASTER | 6 EQUIVALENT, 2 SLOWER | 6 EQUIVALENT, 2 SLOWER |
| V3 (10 × 1–2) | vs v1.0.0 compact-bfs: 12 FASTER, 2 SLOWER | vs v1.0.0 compact-workspace: 2 SLOWER | |

K3 counts include its veto rows (the K3 metrics counted again as vetoes of the K2
families). They are the same 36 measurements.

### 4.2 Family statements (plan section 12), as computed by the analyzer

| Family | vs compact-bfs | vs ETT | vs HDT |
|---|---|---|---|
| `chain-split-rejoin-v1` | prefer reference | prefer reference | prefer reference |
| `cycle-alternatives-v1` | prefer reference | prefer reference | prefer reference |
| `components-join-split-v1` | **prefer cluster-forest** | prefer reference | prefer reference |
| `hub-alternatives-v1` | **prefer cluster-forest** | insufficient evidence (TIMER_LIMITED) | insufficient evidence (TIMER_LIMITED) |
| `sustained-churn-path-v1` | prefer reference | prefer reference | prefer reference |
| `sustained-churn-blocks-v1` | prefer reference | prefer reference | **prefer cluster-forest** |
| `dense-bridge-churn-v1` | **prefer cluster-forest** | **prefer cluster-forest** | **prefer cluster-forest** |
| `redundant-bridge-churn-v1` | **prefer cluster-forest** | **prefer cluster-forest** | **prefer cluster-forest** |
| K2 d4 (with K3, K4 vetoes) | mixed results | mixed results | mixed results |
| K2 d16 (with K3, K4 vetoes) | mixed results | mixed results | mixed results |
| K2x | prefer reference | mixed results | insufficient evidence (1 INCONCLUSIVE) |
| K3 families | prefer reference | **prefer cluster-forest** | **prefer cluster-forest** |
| L (L1, L3; L4 veto) | mixed results | — | — |
| S1 lifecycle off | **prefer cluster-forest** | isolated differences (`mixed50-b64-c16`) | isolated differences (`mixed50-b64-c16`) |
| S1 lifecycle on | **prefer cluster-forest** | — | — |

**Perimeter (plan section 12).** Every statement is limited to:
- the workload family, sizes and densities of the matrix;
- the host of section 1;
- candidate `02cba68`;
- the server configurations used.

Nothing here extrapolates to other sizes, graph shapes, hardware, concurrency levels or
releases.

The magnitudes are reported as measured. Some differences are one or two orders of
magnitude:
- K1 chain and cycle against ETT;
- K2x delete against compact-bfs;
- the S1 and L1 query cells against compact-bfs.

CF5 performs no causal analysis of them.

### 4.3 What the classes show, in brief

- **Against compact-bfs (the default):**
  - CF is much faster where compact-bfs answers queries by search:
    - K2 queries;
    - S1, all 6 cells: throughput about 2.4–250× higher and p99 lower;
    - L1 query cells;
    - the components, hub, dense-bridge and redundant-bridge K1 families.
  - CF is slower on updates and construction:
    - K2 updates;
    - K2x, K3;
    - most L1 and L3 cells;
    - K1 chain, cycle and the sustained families.
  - CF uses more memory: K4, and 19 of 20 L4 metrics LARGER.
- **Against ETT and HDT:**
  - CF is faster on construction (K3, all 24 cells) and on the dense and redundant-bridge
    families.
  - CF uses less memory than HDT (K4, all SMALLER) and, mostly, than ETT.
  - CF is slower than ETT on K2 updates and on every sparse K1 family.
  - Against HDT, K2 is mixed: CF updates are FASTER at d4 10⁵ and d16 10⁵–10⁶ and
    EQUIVALENT at d4 10⁴, d4 10⁶ and d16 10⁴. CF queries are FASTER at 10⁵,
    SLOWER at 10⁶ and at d16 10⁴, and INCONCLUSIVE at d4 10⁴.
  - S1 is EQUIVALENT except `mixed50-b64-c16`, where CF is about 30 % slower than both.
- **Against v1.0.0 (V3, descriptive):**
  - CF on the candidate is FASTER than v1.0.0's compact-bfs on all 6 M_reg cells
    (12 metrics);
  - it is SLOWER than v1.0.0's compact-bfs and compact-workspace on the 2 A core
    workloads (4 cells).

## 5. Measurement limit and per-operation timing (report requirements of revision 5)

- **E is a calibration estimate, not a mathematical upper bound.** It comes from one host
  and one day. Only the tick term (41.667 ns) is guaranteed. A class that stands was not
  changed by the calibrated limit. It is not immune to every measurement error.
- **What δ excludes** (plan section 6.1, recorded per metric in `not_in_limit`):
  - preemption, interrupts, frequency changes, and client scheduling or wake-up delays.
    These act on both arms and enter the pair dispersion; they are not bounded by E;
  - errors beyond the calibrated maxima of the clock read and harness gap;
  - the difference between per-pair values and medians;
  - host drift between blocks.
- **Per-operation timing, unquantified.** The `workload_wall_ns` of K1, V2 and V3 and the
  L3 churn cells time each operation separately. This also removes overlap between
  consecutive operations, an effect that depends on the operation and is not quantified.
  It concerns, in particular:
  - the 3 K1 `hub-alternatives` TIMER_LIMITED cells (δ 0.14–0.25), whose class without the
    limit would be SLOWER;
  - the 2 V2 `ett` TIMER_LIMITED cells;
  - every K1, V3 and L3 churn class that stands.
- **TIMER_LIMITED, 5 metrics in all.** None was turned into a PASS or EQUIVALENT, and none
  is counted:

  | Metric | Interval | δ | Without limit |
  |---|---|---|---|
  | K1 hub-alternatives 10 000 vs ETT | [+31.7 %, +33.8 %] | 0.245 | SLOWER |
  | K1 hub-alternatives 10 000 vs HDT | [+22.7 %, +24.1 %] | 0.234 | SLOWER |
  | K1 hub-alternatives 100 000 vs HDT | [+14.9 %, +20.3 %] | 0.143 | SLOWER |
  | V2 chain-split-rejoin 100 000 ett | [−2.2 %, +1.8 %] | 0.098 | PASS |
  | V2 sustained-churn-path 100 000 ett | [−3.5 %, +2.6 %] | 0.097 | PASS |

  The preparatory diagnostic of plan section 6.1 had named the K1 `hub-alternatives` cells
  against ETT and HDT as at risk.
- **Multiplicity (plan section 6).** With about 230 intervals, about five are expected to
  miss their median by chance. No family-wise correction is applied, and no cell was rerun
  because of its result.

## 6. Protocols of their own

### S3 (feeder protocol) and V1

- **S3: feeder protocol.**
  - Rules: absolute Q1–Q4, plus Q5-style ratios of medians over 3 observations per side.
  - No interval and no TIMER_LIMITED; the section 6.1 rule does not apply.
  - Status COMPLETE: every planned observation ran within S3's own 90-minute cap, with no
    rerun.

  | Comparison | Rule | Result |
  |---|---|---|
  | Q1 | L1 G100k C=16: p99 ≤ 1 000 ms, max ≤ 3 000 ms | **PASS** (p99 57.0 ms, max 57.3 ms) |
  | Q2 | every L1 observation: last10 ≤ 2 × first10 + 50 ms; retained WAL ≤ 16 MiB | **PASS** (12 of 12) |
  | Q3 | L2 G100k: C=16 ≥ 50 % and C=64 ≥ 25 % of C=0 | **PASS** (93.5 %, 77.8 %) |
  | Q4 | L2 G100k C=64: time to ready ≤ 60 s | **PASS** (1.47 s) |
  | Q5-style, L1 G100k C=16 | CF median query rps ≥ 90 %, p99 ≤ 125 % of compact-bfs | **PASS** |
  | Q5-style, L1 G100k C=64 | same | **PASS** |
  | Q5-style, L1 G10k C=16 | same | **PASS** |

  Same session, `compact-bfs` side, descriptive only (not a CF5 comparison): Q3 is FAIL
  (16.6 %, 9.1 %), the known v0.9.0 limitation (knotrel#87). Q1, Q2 and Q4 are PASS.
  Plan section 4.3 allows CF to be presented as relevant to that limitation only under the
  Q rules. That is a statement for the maintainer, not made here.
- **V1:** see section 3.1.

### L2: C rules (sustained resources), no time metric

- **Collection:** 60 of 60 executions exit 0, covering 15 configurations × heap and RSS ×
  lifecycle and reference arms (`--profile final --only C --lifecycle-engines
  cluster-forest`, order seed 51240).
- **Analyzer versions (D2):**
  - **Frozen** (knotrel-benchmarks `f4d41f19`, `analyze_lifecycle_qualification.py`
    sha256 `bbd12a59…ae5c`): refuses the run with "INVALID RUN: not a complete final run"
    (exit 3). The exact output is kept in `analysis/attempt1/L2-frozen-analyzer-refusal.txt`.
    The frozen file is unchanged in the campaign checkout and at `f4d41f19`.
  - **Revised:** the frozen file plus the `--expect-only C` revision, sha256
    `09c547efce0f8537a5919191157b88c446f4a8854c9973cfbb7a0380760dcbae`, committed with
    this report as `scripts/analyze_lifecycle_qualification.py`. **It produced
    the L2 verdicts below.** It was run once, after its tests passed.
    - It accepts only the C profile, and only as the complete 60-cell C matrix of the
      `cluster-forest` scope.
    - It requires no window multipliers, declared explicitly
      (`--expect-multipliers-sha256 none`), and the recorded cell count must match.
    - It now refuses a duplicate cell in the plan or the run log. The frozen file
      indexed both by id and silently kept the last record.
    - The C1–C4 rules are unchanged.
    - Regression tests: 9 new tests in `scripts/tests/test_lifecycle_qualification.py`.
      They cover the complete matrix accepted, the frozen refusal without the flag, and
      refusal of a missing cell, a duplicate in the plan or run log, a timed cell, declared
      multipliers, a wrong filter or count, and a profile other than C. On the frozen analyzer 7
      of the 9 fail. The two that pass are the frozen-refusal test and the
      other-profile test, which the frozen argument parser also refuses. Full suite:
      961 passed, 3 skipped.
- **Verdicts** (`analysis/attempt1/analysis-session1-L2.json`, `.md`):

  | Rule | Scope | Result |
  |---|---|---|
  | C1 `engine_vertices ≤ 2 × nodes + 1024` | 30 lifecycle runs | **30 PASS** |
  | C2 logical counts exact | 60 runs | **60 PASS** |
  | C3 heap growth (late/early ≤ 1.25, projected 30-cycle growth ≤ 10 %) | 15 lifecycle heap runs | **13 PASS, 2 FAIL** |
  | C4 RSS growth, same rules (disclosure) | 15 lifecycle RSS runs | 6 PASS, **9 EXCEEDS_BUDGET** |

- **C3 FAIL** (a rule outcome that needs a disposition, as in v1.0.0 §6; disposition in
  section 7, D5: accepted as a documented limitation, class kept as FAIL). Each run is
  published separately. The percentages are **projections of the slope rule** to 30
  cycles, not measured growth:

  | Run | late/early | Projected 30-cycle growth | Net heap first → last |
  |---|---|---|---|
  | `C-heap-lifecycle-cluster-forest-sparse-same-1000` (reuse same) | 1.133 | **+20.2 %** (projection) | 558 512 → 650 736 B |
  | `C-heap-lifecycle-cluster-forest-sparse-toggle-1000` (toggle) | 1.146 | **+14.6 %** (projection) | 558 512 → 656 824 B |

  - Both fail the slope rule only.
  - The reference arm of the same configurations, which the rules do not judge, shows
    +19.4 % and +22.6 %.
  - At 10 000 and 100 000 nodes the same configurations pass C3, with projected growth of
    7 % or less.
- **C4 EXCEEDS_BUDGET:** RSS on sparse fresh, same and toggle at 1 000; sparse fresh at
  10 000; sparse fresh and same, ring fresh, hub fresh and same at 100 000. This is a
  disclosure category (allocator retention), not a FAIL. All nine stay visible with their
  numbers in `analysis/attempt1/analysis-session1-L2.md`.

## 7. Maintainer decisions (2026-11-25, after the session) and open points

### D1 — conformance: swap (closed with an explicit exception)

- **Decision.** "No swap" in plan section 9 means **no swap activity during the
  measurement**. The decision was taken after the session.
  - It cites plan section 9 (conformance: "the host is idle …; no swap", stated "as
    v1.0.0 §5.4").
  - It cites v1.0.0 §5.4, which that item refers to. There swap and load average are
    recorded as context only. The interference indicators are external CPU, memory
    pressure, sleep, AC power, thermal warnings and telemetry coverage.
- **Rule applied with the decision.**
  - If cumulative swap-in and swap-out counters cover the whole window with zero delta,
    the requirement is met (the 738 MB of initial occupancy is reported).
  - If only occupancy exists, the result is "stable occupancy, activity not verifiable"
    and D1 stays open.
  - If the counters show activity, their deltas are reported and the rule is applied.
  - In the last two cases publication of the classes is suspended, and the maintainer is
    informed before any further measurement.
- **Result: stable occupancy, activity not verifiable.** Only occupancy covers the window
  (section 2): 738.25 MB at the start, unchanged at every block boundary, 722.25 MB at the
  end. No cumulative counter covers it.
  The 192 zero values of `swaps` in V1's `/usr/bin/time -l` output concern only the V1
  processes observed, not the host.
- **Exception (maintainer, 2026-11-25).** The maintainer accepts the use and publication
  of attempt 1's results with an explicit exception **limited to the verification of host
  swap activity**. Every other conformance item is unaffected.
  - Wording carried in the summary, next to the CF6 conclusions and with every class, PASS
    included: **"host swap activity not verifiable; results accepted by the maintainer
    with this limitation"**.
  - The exception does not turn the check into a pass: swap activity during the window
    remains unknown.
  - The attempt is **closed without a rerun**.
- **Protocol change for future campaigns.** Record the system's cumulative swap counters
  (`vm_stat` `Swapins` and `Swapouts` on macOS, or the equivalent) immediately before the
  first and after the last measured observation, so that a delta covers the whole
  measurement window. Recorded in `docs/methodology.md`, "Host swap activity". The CF5
  runner and freeze of this attempt are not changed.

### D2 — L2 analysis (decided, applied)

- **Decision.** A targeted revision of the analyzer for the `--only C` profile that the
  freeze prescribes.
- **Done** (section 6, L2):
  - the revision accepts the complete C matrix and refuses missing or duplicate cells;
  - the frozen version and its original refusal are kept;
  - after the tests, the revision was applied once to the existing data.
- **The L2 verdicts come from the revised analyzer**, sha256 `09c547ef…cbae`, the file
  `scripts/analyze_lifecycle_qualification.py` included in the same change as this report.

### D3 — inconclusive regression checks (decided: left open for CF6)

- **Decision.** For CF6 these five cells stay **open on performance**.
  - Their original classes are kept.
  - No further measurement is requested.
  - None is a regression or a pass.
- **Consequence for the families (plan section 12):** none of the five belongs to a
  family. V1 and V2 compare the candidate's existing engines with v1.0.0, so they enter
  no CF6 family statement. Each leaves the corresponding regression question (plan
  question 4) open for that engine and configuration.

| # | Cell | Original class | Metric | Interval (tolerance) |
|---|---|---|---|---|
| 1 | V1 HTTP standalone batch b1, `compact-bfs` | **UNRESOLVED** | `request_latency_p99_ns` (supporting) INCONCLUSIVE; primary `window_duration_ns` PASS [−6.2 %, +9.0 %] | [−41.9 %, +73.8 %] (25 %) |
| 2 | V1 HTTP standalone batch b64, `compact-bfs` | **UNRESOLVED** | `sampled_max_rss_bytes` (supporting) INCONCLUSIVE; primary `window_duration_ns` PASS [−4.2 %, +3.4 %] | [0.0 %, +22.1 %] (20 %) |
| 3 | V1 HTTP lifecycle small, `compact-bfs` | **INCONCLUSIVE_DISCLOSED** | `time_to_ready_ms` (primary) | [−18.3 %, +25.9 %] (10 %) |
| 4 | V2 `chain-split-rejoin-v1` 100 000, `ett` (scan) | **TIMER_LIMITED** | `workload_wall_ns`, δ = 0.098 (class without limit: PASS, not counted) | [−2.2 %, +1.8 %] (10 %) |
| 5 | V2 `sustained-churn-path-v1` 100 000, `ett` (scan) | **TIMER_LIMITED** | `workload_wall_ns`, δ = 0.097 (class without limit: PASS, not counted) | [−3.5 %, +2.6 %] (10 %) |

What each cell leaves open:
1. Tail latency at batch size 1 of the HTTP server with `compact-bfs`, against v1.0.0.
2. Peak RSS at batch size 64 of the HTTP server with `compact-bfs`, against v1.0.0.
3. Time to ready of the small HTTP lifecycle configuration with `compact-bfs`, against
   v1.0.0.
4. and 5. The `ett` engine (scan variant) on two core workloads, against v1.0.0, at the
   instrument's resolution.

The V1 rows follow the v1.0.0 protocol, without the section 6.1 rule. The V2 rows follow
the section 6.1 rule, under which TIMER_LIMITED is handled as INCONCLUSIVE.

These are separate from the **non-conclusive cells inside CF6 families**, which D3 does
not cover and which the family statements already count:
- 3 K1 `hub-alternatives` TIMER_LIMITED cells: the family vs ETT and vs HDT is
  *insufficient evidence*;
- K2x 2^20 vs HDT `delete_ns` INCONCLUSIVE: K2x vs HDT is *insufficient evidence*;
- K2 d4 10⁴ vs HDT `query_ns` INCONCLUSIVE: the family is *mixed results* either way;
- L3 `http-import-sparse-100k-60-30` INCONCLUSIVE: L is *mixed results* either way.

### D4 — CF6 (decided): conclusions per family within CF5's coverage

- **Decision.** `compact-bfs` stays the default engine. `cluster-forest` stays opt-in and
  experimental. This is the plan's default outcome (section 12); promotion is not
  eligible in v1.1.0, and a change of default is out of scope.
- **Perimeter.** Every conclusion below holds only within:
  - the CF5 matrix (the families, sizes and densities of plan section 4);
  - the host of section 1 (Apple M3, 16 GB, macOS 26.5.2);
  - candidate `02cba68`;
  - the server configurations used.

  None extrapolates beyond that.
- **Limitation (D1): host swap activity not verifiable; results accepted by the maintainer
  with this limitation.** It applies to every conclusion below.
- **Selection guidance, from the family statements of section 4.2:**
  - **Prefer `cluster-forest` over every reference:** dense two-clique churn
    (`dense-bridge-churn-v1`, `redundant-bridge-churn-v1`, 512 and 2 048 nodes).
  - **Prefer `cluster-forest` over `compact-bfs`:**
    - `components-join-split-v1` and `hub-alternatives-v1` (10⁴, 10⁵);
    - the server's M_reg mixes, lifecycle off (4 cells) and on (2 cells).
  - **Prefer `cluster-forest` over ETT and HDT:**
    - construction from the K1 family graphs (K3 families, 10⁵);
    - over HDT only, `sustained-churn-blocks-v1`.
  - **Prefer the reference:**
    - `chain-split-rejoin-v1`, `cycle-alternatives-v1` and `sustained-churn-path-v1`
      against all three references;
    - `components-join-split-v1` and `sustained-churn-blocks-v1` against ETT
      (and `components-join-split-v1` against HDT);
    - K2x and K3 families against `compact-bfs`.
  - **Mixed results, no preference:**
    - the staged K2 protocol, d4 and d16, against every reference. Updates, queries,
      construction and memory point in different directions; for example, against
      `compact-bfs`, queries are much faster but updates, construction and memory are
      worse;
    - K2x against ETT;
    - the lifecycle family L against `compact-bfs`.
  - **Insufficient evidence:**
    - `hub-alternatives-v1` against ETT and HDT (TIMER_LIMITED);
    - K2x against HDT (one INCONCLUSIVE).
  - **Isolated differences:** S1 lifecycle off against ETT and HDT. Equivalent except
    `mixed50-b64-c16`, where CF is SLOWER (about 30 %).
- **Outside the family statements, reported with their own rules:**
  - S3, all seven comparisons PASS. Under the Q rules CF meets Q3, which the
    `compact-bfs` side of the same session fails, but only in this configuration and
    session.
  - L2: two C3 FAILs accepted as a documented limitation (D5) and nine C4
    EXCEEDS_BUDGET disclosures.
  - The V3 descriptive comparison with the released v1.0.0 default.
  - The D3 regression checks, left open.

### D5 — L2 C3 FAIL (decided: documented limitation)

- Two `cluster-forest` lifecycle heap runs at 1 000 nodes on the sparse graph fail C3 on
  the slope rule (section 6, L2). Under v1.0.0 §6, which the plan applies to L2, a C3 FAIL
  is non-PASS and needs a disposition.
- **Decision.** The maintainer accepts both as a **documented limitation of the
  `cluster-forest` lifecycle on the sparse 1 000-node graph**. The class stays **FAIL**;
  acceptance does not make it a PASS. Each is published separately:
  - **reuse same** (`C-heap-lifecycle-cluster-forest-sparse-same-1000`): projected
    30-cycle heap growth **+20.2 %**;
  - **toggle** (`C-heap-lifecycle-cluster-forest-sparse-toggle-1000`): projected 30-cycle
    heap growth **+14.6 %**.

  Both percentages are projections of the slope rule, not measured growth.
- **Memory stability for these two workloads stays open.**
- The nine C4 EXCEEDS_BUDGET runs stay visible (section 6, L2), as disclosures.
- It does not enter the CF6 family statements: L2 has none. It is not a correctness
  failure, so the campaign is not FAIL.

### Closure

- D3 and D4 are confirmed. `compact-bfs` stays the default; `cluster-forest` stays opt-in
  and experimental.
- Every original class is preserved. Merge, tag and release publication are separate
  decisions.

## 8. Files

| File | Content |
|---|---|
| `analysis/attempt1/analysis-session1.json` | `analyze_cf5.py` output: every paired and deterministic cell, family statements, report notes |
| `analysis/attempt1/analysis-session1-V1.json` | `analyze_v100q_a.py` output for V1 |
| `analysis/attempt1/analysis-session1-L2.json`, `analysis-session1-L2.md` | revised L2 analyzer output (D2) |
| `analysis/attempt1/L2-frozen-analyzer-refusal.txt` | the frozen L2 analyzer's refusal, verbatim |
| `analysis/attempt1/S3-evaluation.json` | S3 evaluation by its collector |
| `analysis/attempt1/CELLS.md` | every cell and metric, rendered by `render_cells.py` (presentation only) |
| `analysis/attempt1/session1-record.json`, `session1-status.json` | the runner's record and final status, including host snapshots |
| `analysis/attempt1/ANALYSIS-COMMANDS.txt` | the exact analysis commands, each run once |
| `analysis/attempt1/analysis-sha256.txt`, `campaign-outputs-sha256.txt`, `binaries-sha256.txt` | checksums |
