# v1.2.0 release qualification: summary

Reference: v1.1.0. Plan: knotrel docs/releases/v1.2.0-qualification-plan.md, section 13 (attempt 2).

## Deciding items by outcome

| Outcome | Count | Items |
|---|---|---|
| DELEGATED_DONE | 4 | `B4`, `Q`, `Q-K4`, `V1` |
| INCONCLUSIVE | 1 | `B4-http-metrics-ops-compact-bfs-sparse-10000` |
| INCONCLUSIVE_DISCLOSED | 1 | `http_lifecycle_compact_bfs_small` |
| PASS | 44 | — |
| UNRESOLVED | 2 | `http_standalone_batch_b1_compact_bfs`, `http_standalone_batch_b256_compact_bfs` |

## Q3 (feeder catch-up under query load)

Mode: KNOTREL_MAX_CONCURRENT_QUERIES=4.

**PASS**. C=16 share 55.5% against 50% (pass); C=64 share 54.9% against 25% (pass).

Next step: #87 can close with the #180 ledger row (plan section 6.3).

Default mode (reported, not deciding): **FAIL**, C=16 21.9%, C=64 11.6%.

## Reported, cost and descriptive items (not deciding)

| Item | Role | Outcome |
|---|---|---|
| `core_sparse_traversal_10k_compact-bfs_warmed` | descriptive | PASS |
| `core_sparse_traversal_10k_compact-workspace_warmed` | descriptive | PASS |
| `core_sustained_churn_10k_compact-bfs_warmed` | descriptive | PASS |
| `core_sustained_churn_10k_compact-workspace_warmed` | descriptive | PASS |
| `Q/Q3` | reported | FAIL |
| `Q-K4/Q5` | cost | FAIL |

## `ops-atomic` (hub 10k, deciding)

`B4-http-ops-atomic-compact-bfs-hub-10000`: **PASS**, interval [-3.9074127056579977, -2.9394322262125017] %.
