# v1.2.0 release qualification, attempt 2: report (knotrel#182)

**Outcome: no deciding item is REGRESSION or FAIL. Four deciding items have no verdict either
way, and each needs a maintainer disposition (plan §6.1, §6.2). The release decision stays with
#182.**

- **Q3 is PASS with `KNOTREL_MAX_CONCURRENT_QUERIES=4`.** At C=16 the feeder keeps **55.5 %** of
  its no-load rate (threshold 50 %), and at C=64 it keeps **54.9 %** (threshold 25 %).
- **In the default mode, Q3 is FAIL** (21.9 % and 11.6 %). It is reported and does not decide
  (plan §13.3).
- Q1, Q2, Q4 and Q5 pass in the default mode. Q1–Q4 pass with K=4.
- K=4 has a cost, Q5 of `Q-K4`, published and not deciding: query throughput is 85.1 % and
  88.0 % of v1.1.0's, below the 90 % rule, while query p99 drops to about 29 % of v1.1.0's.
- The deciding items without a verdict:
  - B4: one INCONCLUSIVE;
  - V1: one INCONCLUSIVE_DISCLOSED and two UNRESOLVED.
- No tag and no publication follow from this report.

## Run

| | |
|---|---|
| Candidate | knotrel 977e54d: v1.1.0's executed core plus the experimental B2 limiter (#207), off by default |
| Reference | v1.1.0 (57c35e8) |
| Freeze | knotrel-benchmarks 99f820c9 (`FREEZE.json`), tooling e66bd81f, matrix SHA-256 `8631c453…8dd`; the session used this matrix (`host-session1/matrix.txt`) |
| Plan | knotrel `docs/releases/v1.2.0-qualification-plan.md`, §13 (#208) |
| Budget | 3.5 h cap (§13.6) |
| Attempt | 2 (the last one the plan provides), single session, 2026-11-27 21:36–23:26 UTC (1 h 50 min), `campaign: complete`, all steps ran |
| Host conformance | Swapins and Swapouts delta 0 (`analysis/swap-activity.json`); Docker stopped outside Q; AC power |
| Collector states | V1, Q, Q-K4 and B4 `DELEGATED_DONE`, each with a single attempt, exit 0. No `TOOL_ERROR`, no `INCOMPLETE`. Both Q evaluations were written by the session itself |

Analyses are in `analysis/`:
- `cf5-analysis.json`: V2;
- `v1-analysis.json`;
- `q-evaluation.json`: default mode;
- `q-k4-evaluation.json`: K=4;
- `b4-analysis.json` and `b4-analysis.md`;
- `summary.json` and `summary.md`;
- `status.json`, `record.json`, `swap-activity.json`.

Raw evidence stays on the host under
`evidence/v1.2.0-qualification-attempt2-977e54d-99f820c/`.

Pre-collection checks (§13.5) passed:
- Q runner layout and the tool-error/criterion separation: `logs/Q-runner-check.json`, 10/10;
- K=4 variant smoke: `logs/smoke-k4.txt`;
- free disk: 17.8 GB before the builds, 15.9 GB after preparation, threshold 8 GB.

## Q: feeder under query load

### Q3, catch-up (deciding with K=4)

Rule: on L2 G100k, the feeder's rate at C=16 must be ≥ 50 % of its C=0 rate, and at C=64 ≥ 25 %.

| Mode | C=0 (rows/s) | C=16 | Share | C=64 | Share | Q3 |
|---|---|---|---|---|---|---|
| **K=4** (`Q-K4`, deciding) | 176 932 | 98 112 | **55.5 %** | 97 204 | **54.9 %** | **PASS** |
| Default (`Q`, reported) | 154 044 | 33 706 | 21.9 % | 17 913 | 11.6 % | FAIL |

Per §13.4, #87 can close with the #180 ledger row. The release notes say that Q3 passes with
the experimental `KNOTREL_MAX_CONCURRENT_QUERIES=4` on the qualification host (8 CPUs). They
also say that the default mode's Q3 is FAIL as measured.

### Q1, Q2, Q4, Q5

| Criterion | Default (`Q`) | K=4 (`Q-K4`) |
|---|---|---|
| Q1: marker p99 / max, L1 G100k C=16 (≤ 1000 / 3000 ms) | PASS, 141.4 / 179.3 ms | PASS, 67.1 / 70.7 ms |
| Q2: lag and WAL bounded | PASS | PASS |
| Q4: time to ready, L2 G100k C=64 (≤ 60 s) | PASS, 5.28 s | PASS, 0.97 s |
| Q5: steady query cost against v1.1.0 | **PASS** (deciding) | **FAIL** (cost, not deciding) |

### Q5, steady-feeding query cost

The baseline is the **v1.1.0 server measured in the same session**, on the same cells.

Rule: the candidate's median query throughput is ≥ 90 % of the reference's, and its median
query p99 is ≤ 125 % of the reference's. The evaluator's rule text still says "v0.9.0", from
the v1.0.0 runner. The reference it measures is the campaign's `ref-server`, which is v1.1.0.

| Cell | Mode | Throughput v1.1.0 → candidate (req/s) | Ratio | p99 v1.1.0 → candidate (ms) | Ratio | Q5 |
|---|---|---|---|---|---|---|
| L1 G100k C=16 | default | 1189 → 1274 | 1.072 | 74.1 → 76.7 | 1.035 | pass |
| L1 G100k C=64 | default | 1115 → 1130 | 1.013 | 152.9 → 157.8 | 1.031 | pass |
| L1 G100k C=16 | K=4 | 1211 → 1030 | **0.851** | 76.4 → 22.4 | 0.294 | fail (throughput) |
| L1 G100k C=64 | K=4 | 1116 → 982 | **0.880** | 159.9 → 46.8 | 0.292 | fail (throughput) |

The ratios measured here differ from the ones in knotrel `docs/http-api.md` ("Bounded query
concurrency"), which came from the impact estimate:

| | Throughput ratio, C=16 / C=64 | p99 |
|---|---|---|
| Impact estimate (`docs/http-api.md`) | 0.879 / 0.890 | 76.5→22.1 ms, 157.9→46.2 ms |
| This qualification | 0.851 / 0.880 | 76.4→22.4 ms, 159.9→46.8 ms |

Updating the page with the qualification figures is a docs change for the maintainer to decide.

## Deciding items, by outcome (plan §6.4, nothing pooled)

### REGRESSION or FAIL

None.

### INCONCLUSIVE, B4 (needs a disposition, §6.2)

Interval: candidate against v1.1.0, as a % change of time; positive means slower.

| Item | Median change | Interval | Tolerance |
|---|---|---|---|
| `B4-http-metrics-ops-compact-bfs-sparse-10000` | +4.05 % | [+1.58, +7.08] % | 6 % |

- In attempt 1 (candidate 9faf168, whose server code equals v1.1.0's for this path), the same
  cell was PASS, with a median of +3.46 % and an interval of [+1.63, +5.77] %.
- This candidate's `/metrics` path is the one changed by #207 (`metrics.rs`). With the limiter
  unset, the limiter series are absent (`logs/smoke-k4.txt`: plain `limiter_series=0`).
- Whether the upper bound's move past 6 % comes from that change or from dispersion is not
  established.

### INCONCLUSIVE_DISCLOSED and UNRESOLVED, V1 HTTP cells (frozen v1.0.0 A rules; each needs a disposition)

| Item | Class | Median change | Interval |
|---|---|---|---|
| `http_lifecycle_compact_bfs_small` | INCONCLUSIVE_DISCLOSED | −0.75 % | [−20.2, +23.6] % |
| `http_standalone_batch_b1_compact_bfs` | UNRESOLVED | +3.38 % | [−3.9, +8.4] % |
| `http_standalone_batch_b256_compact_bfs` | UNRESOLVED | +0.07 % | [−1.8, +0.8] % |

Attempt 1, on a candidate with a different core change, gave these three cells the same classes.

### PASS (44)

- **V2:** all 12 metrics of the 6 M_reg cells.

  | Cell | p99 latency | Throughput |
  |---|---|---|
  | source-managed off read100 b8 c16 100k import | [−2.4, +1.9] % | [−2.0, +2.3] % |
  | source-managed on read100 b8 c16 100k events | [−8.2, +8.7] % | [−0.8, +2.4] % |
  | standalone off mixed50 b64 c16 100k | [−2.3, +0.7] % | [−1.3, +0.6] % |
  | standalone off read95 b1 c4 10k | [−0.6, +0.7] % | [−0.1, +0.6] % |
  | standalone off read95 b8 c16 100k | [−1.6, +4.4] % | [−1.2, +1.2] % |
  | standalone on lifecycle50 b8 c16 100k | [−1.9, +1.6] % | [−0.5, +1.2] % |

- **V1 HTTP:** `http_standalone_batch_b8_compact_bfs` and `_b64_`.
- **B4:** 22 of 23 deciding cells, including **`ops-atomic` hub 10k: PASS**, interval
  [−3.91, −2.94] %. The atomic gate checks and negative controls hold.
- **Q:** Q1, Q2, Q4 and Q5 in the default mode, and Q1, Q2, Q3 and Q4 with K=4.

## Not deciding

- **V1 core cells (descriptive, §13.3):** all four PASS.

  | Cell | Interval |
  |---|---|
  | `core_sparse_traversal_10k_compact-bfs_warmed` | [−1.5, +2.8] % |
  | `core_sparse_traversal_10k_compact-workspace_warmed` | [−8.7, +5.9] % |
  | `core_sustained_churn_10k_compact-bfs_warmed` | [−0.8, +0.6] % |
  | `core_sustained_churn_10k_compact-workspace_warmed` | [+0.03, +1.0] % |

  Attempt 1's core regressions do not recur. That fits the scope: the executed core code
  equals v1.1.0's.
- **Reported:** `Q/Q3`, default mode, is FAIL (above).
- **Cost:** `Q-K4/Q5` is FAIL (above).
- **B4 descriptive, not passing,** with the same classes as in attempt 1:
  - `import-high` sparse 10 000: REGRESSION, [+379.9, +412.4] %; attempt 1 [+385.8, +441.0] %;
  - `ops` sparse 100 000: INCONCLUSIVE, [+18.2, +25.4] %; attempt 1 [+17.0, +26.3] %.
- **B4 unqualified, hub 10k:**
  - `ops` [+10.8, +11.5] %;
  - `events` [+4.5, +5.9] %;
  - both `-equivalent-` cells faster.

  Hub 10k `events` stays **not qualified** (§7).

## Dispositions (§13.7)

| Item | Disposition |
|---|---|
| K1 and K2 | no cells: the executed core code equals v1.1.0's |
| V1 core cells | descriptive (above) |
| Unchanged paths (`compact-bfs` sustained resources, `ett`, `hdt`, `cluster-forest`, `compact-workspace`, mutations) | as §7: no cells. The `connected` scratch is v1.1.0's: one V-bit bitset and one queue per call |
| Hub 10k `events` (B4) | not qualified, as §7 |
| B2 opt-in mode beyond Q | **not qualified**. Only `Q-K4` measures it; V1, V2 and B4 ran in the default mode |

## Open for the maintainer (#182)

1. Disposition of the four deciding items without a verdict: B4 `metrics-ops` sparse 10k, V1
   `http_lifecycle_compact_bfs_small`, and V1 `b1` and `b256`. The options are to accept them
   with disclosure, or to run a targeted follow-up on the same candidate (§6.1). Rerunning
   inside this campaign is not allowed.
2. The release decision for v1.2.0.
3. Whether `docs/http-api.md` should carry this qualification's Q5 ratios in place of the
   estimate's.

## Notes on the analysis

- **B4 provenance.** B4 was checked with `--expect-probes-rev` set to the freeze commit
  99f820c9, the checkout the probes were built from. Its only difference from the tooling
  commit e66bd81f is `FREEZE.json`. A first run with the tooling commit was refused as
  `INVALID RUN`, as designed.
- **Summary rows.** `summary.json` lists V1, Q, Q-K4 and B4 under `DELEGATED_DONE`. Those rows
  are block markers, not outcomes, and the counts above leave them out.
