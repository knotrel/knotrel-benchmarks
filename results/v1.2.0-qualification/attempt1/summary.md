# v1.2.0 release qualification: summary

Reference: v1.1.0. Plan: knotrel docs/releases/v1.2.0-qualification-plan.md.

## Deciding items by outcome

| Outcome | Count | Items |
|---|---|---|
| DELEGATED_DONE | 3 | `B4`, `Q`, `V1` |
| FAIL | 1 | `Q3` |
| INCONCLUSIVE_DISCLOSED | 1 | `http_lifecycle_compact_bfs_small` |
| PASS | 61 | — |
| REGRESSION | 10 | `K1-chain-split-rejoin-v1-10000/workload_wall_ns`, `K1-chain-split-rejoin-v1-100000/workload_wall_ns`, `K1-components-join-split-v1-10000/workload_wall_ns`, `K1-components-join-split-v1-100000/workload_wall_ns`, `K1-cycle-alternatives-v1-10000/workload_wall_ns`, `K1-cycle-alternatives-v1-100000/workload_wall_ns`, `K1-sustained-churn-path-v1-100000/workload_wall_ns`, `core_sparse_traversal_10k_compact-bfs_warmed`, `core_sparse_traversal_10k_compact-workspace_warmed`, `core_sustained_churn_10k_compact-bfs_warmed` |
| TIMER_LIMITED | 2 | `K1-sustained-churn-blocks-v1-10000/workload_wall_ns`, `K1-sustained-churn-path-v1-10000/workload_wall_ns` |
| UNRESOLVED | 2 | `http_standalone_batch_b1_compact_bfs`, `http_standalone_batch_b256_compact_bfs` |

## Q3 (feeder catch-up under query load)

**FAIL**. C=16 share 48.5% against 50% (fail); C=64 share 33.5% against 25% (pass).

Next step: #87 step B2: bounded concurrent query execution, designed and measured as an impact estimate against Q1-Q5 with unchanged thresholds (plan section 6.3).

## `ops-atomic` (hub 10k, deciding)

`B4-http-ops-atomic-compact-bfs-hub-10000`: **PASS**, interval [-4.485907997375516, -3.2314488407811037] %.
