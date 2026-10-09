# Adaptive confirmation of rank-zero reroot

64 additional processes, four selected cells, eight pairs each; no failures. Selection followed the initial results and is documented in [protocol.md](protocol.md). These trials remain separate from the original matrix. Negative runtime change means improvement. Order alternates globally, not per cell.

| Scenario | Initial change, 3 pairs | Confirmation change, 8 pairs | Faster pairs | Before-first / after-first |
|---|---:|---:|---:|---:|
| sustained-churn-blocks-v1 / 1000000 / 10 / warmed | +3.21% | -2.35% | 5 / 8 | 2 / 6 |
| sustained-churn-blocks-v1 / 1000000 / 90 / warmed | -5.14% | -3.73% | 8 / 8 | 4 / 4 |
| sustained-churn-path-v1 / 100000 / 50 / fresh | +8.24% | -4.86% | 7 / 8 | 3 / 5 |
| sustained-churn-path-v1 / 1000000 / 50 / fresh | +11.81% | +0.27% | 5 / 8 | 7 / 1 |

The initial path regressions are not reproduced at the same magnitude. The targeted 1M-block, 90%-query warmed cell improves in all eight pairs, with a 3.73% lower median runtime. This is a narrow result; selection was adaptive and the four cells do not establish a universal improvement. Refer to [comparison.json](comparison.json) for paired runtime changes, tails, setup and process RSS. All correctness checks, fingerprints and paired HDT counters match.
