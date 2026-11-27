# v1.2.0 release qualification: report (knotrel#182)

**Outcome: the candidate does not qualify.**

- 10 deciding cells are REGRESSION against v1.1.0, and each blocks the release (plan §6.1).
- Q3 is **FAIL**: at C=16 the feeder keeps **48.5 %** of its no-load rate, below the 50 % threshold.
- The next step for Q3 is the **B2 decision of #87** (plan §6.3).
- No tag and no publication follow from this report.

## Run

| | |
|---|---|
| Candidate | knotrel 9faf168 (`Graph::connected` bidirectional BFS, #196); knotrel main after it changes only docs |
| Reference | v1.1.0 (57c35e8) |
| Freeze | knotrel-benchmarks 4cf9b103 (`FREEZE.json`), tooling 4fbee419, matrix SHA-256 in the freeze |
| Plan | knotrel `docs/releases/v1.2.0-qualification-plan.md` (knotrel#201) |
| Budget | 5.0 h cap (`BUDGET.md`), recorded before collection |
| Attempt | 1, single session, 2026-11-27 09:52–13:13 (3 h 21 min), `campaign: complete`, all steps ran |
| Host conformance | Swapins and Swapouts delta 0 (`attempt1/swap-activity.json`); Docker stopped |

Analyses: `attempt1/` (`cf5-analysis.json` for V2, K1 and K2, `v1-analysis.json`,
`Q-evaluation.json`, `b4-analysis.json`, `summary.json`). Raw evidence is kept on the host
under `evidence/v1.2.0-qualification-attempt1-9faf168-4cf9b10/`.

## Q3: feeder catch-up under query load

| | Rate (rows/s) | Share of C=0 | Threshold | |
|---|---|---|---|---|
| C=0 | 173 131 | — | — | |
| C=16 | 84 034 | **48.5 %** | ≥ 50 % | **fail** |
| C=64 | 58 026 | 33.5 % | ≥ 25 % | pass |

**Q3 FAIL**, thresholds unchanged. Q1, Q2, Q4 and Q5 are PASS. Q5 is measured against the
v1.1.0 server.

**Next step:** the #87 B2 decision. B2 means bounded concurrent query execution, designed
and then measured as an impact estimate against Q1–Q5, with the thresholds unchanged.
#87 stays open.

## Deciding items, by outcome (plan §6.4, nothing pooled)

### REGRESSION (10, each blocks the release)

Intervals: candidate against v1.1.0, as a % change of time, so positive means slower.
Tolerances are those of the frozen rules.

| Block | Item | Interval |
|---|---|---|
| K1 | chain-split-rejoin 10 000 | [+131.9, +170.7] % |
| K1 | chain-split-rejoin 100 000 | [+189.5, +213.4] % |
| K1 | components-join-split 10 000 | [+44.5, +53.3] % |
| K1 | components-join-split 100 000 | [+68.9, +77.7] % |
| K1 | cycle-alternatives 10 000 | [+59.2, +64.8] % |
| K1 | cycle-alternatives 100 000 | [+88.2, +93.5] % |
| K1 | sustained-churn-path 100 000 | [+51.7, +54.7] % |
| V1 | core_sparse_traversal_10k compact-bfs (warmed) | [+91.7, +120.8] % |
| V1 | core_sparse_traversal_10k compact-workspace (warmed) | [+7.4, +17.8] % |
| V1 | core_sustained_churn_10k compact-bfs (warmed) | [+43.2, +48.1] % |

The `compact-workspace` regression is not explained by the scope analysis. Plan §3 records
`connected_with_workspace` as unchanged. Its workload may still reach `Graph::connected`;
this is not verified.

### TIMER_LIMITED (2: handled as INCONCLUSIVE; each needs a disposition)

| Item | Interval |
|---|---|
| K1 sustained-churn-blocks 10 000 | [+16.2, +18.4] % |
| K1 sustained-churn-path 10 000 | [+40.7, +44.2] % |

### INCONCLUSIVE and unresolved, V1 (frozen v1.0.0 A rules; each needs a disposition)

| Item | Class | Interval |
|---|---|---|
| http_lifecycle_compact_bfs_small | INCONCLUSIVE_DISCLOSED | [−18.3, +18.6] % |
| http_standalone_batch_b1_compact_bfs | UNRESOLVED | [−6.4, +7.5] % |
| http_standalone_batch_b256_compact_bfs | UNRESOLVED | [−1.6, +2.3] % |

### PASS

- V2: all 12 metrics of the 6 M_reg cells (p99 latency and throughput).
- K2: all 12 metrics (d4 and d16, 10⁴ to 10⁶ nodes, query and update).
- K1: 7 metrics.
- V1: 3 cells.
- B4: all 23 deciding cells, including **`ops-atomic` hub 10k: PASS**, interval
  [−4.5, −3.2] %. The atomic gate checks and negative controls hold.
- Q1, Q2, Q4, Q5.

## Not deciding

- **B4 unqualified (no verdict):** the plain and `-equivalent-` `ops` and `events` hub 10k
  cells. Measured: `ops` hub [+10.8, +12.0] %, `events` hub [+4.1, +6.7] %, both
  `-equivalent-` cells faster. Hub 10k `events` stays **not qualified**, as decided by the
  maintainer.
- **B4 descriptive, not passing:**
  - `import-high` sparse 10 000: REGRESSION, [+385.8, +441.0] %;
  - `ops` sparse 100 000: INCONCLUSIVE, [+17.0, +26.3] %.

## Reading

The candidate's only executed change is the bidirectional BFS in `Graph::connected`. Every
cell that reaches it through traversal-heavy workloads got slower, by up to about three
times on chains. The cells limited by HTTP and batching (V2, B4 deciding, K2 staged
compact-bfs) did not regress.

A cause is not established. One candidate is the per-call work: the old search allocated
one V-bit visited set, the new one allocates two plus two frontier vectors. Another is the
layer-by-layer expansion on sparse graphs. Diagnosing it is outside this campaign.

Q3 did not reach the 50 % threshold at C=16. That matches the earlier descriptive impact
estimate (43.7 %).

## Notes on the analysis

- **Q directory name.** `run_q.sh` writes Q into `delegated/Q-attempt1/Q`, but
  `evaluate_v100q_q.py` accepts only a directory named `part3` or `part3-attempt2`. So the
  session's own evaluation step wrote an empty `Q-evaluation.json`.
  - The evaluation was rerun after the session on an unmodified copy named
    `analysis/part3`. Collection was not affected.
  - The tooling should be fixed before any later attempt.
- **Summary rows.** `summary.json` lists the delegated blocks V1, Q and B4 with the CF5
  state `DELEGATED_DONE`. These rows are block markers, not outcomes; this report
  leaves them out.
- **B4 provenance.** B4 was checked with `--expect-probes-rev` set to the freeze commit
  4cf9b103, which is the checkout the probes were built from: tooling plus `FREEZE.json`
  only.
