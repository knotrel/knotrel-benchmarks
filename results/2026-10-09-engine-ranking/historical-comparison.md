# Historical comparison: 2026-10-06 vs 2026-10-09 on matched cells

All 74 main cells matched exactly by trace fingerprint, actual operation counts, and true/false query outcomes. Ten-million-node and repeated-query supplements are excluded.

These measurements reflect distinct sequential campaigns on the same host with unchanged release compiler settings. Drift is descriptive, not an isolated causal proof.

## Overall summary across 74 main cells

| Engine | 2026-10-06 Wins | 2026-10-09 Wins | Net Change | Median Runtime Drift | Runtime Drift Range | Median RSS Change (100k+1M) |
|---|---:|---:|---:|---:|---:|---:|
| Compact (default) | 4 / 74 | 3 / 74 | -1 | -0.4% | -10.3% to +13.1% | +0.0% |
| Workspace (opt-in) | 16 / 74 | 20 / 74 | +4 | -0.8% | -15.1% to +29.1% | +0.0% |
| ETT (experimental) | 20 / 74 | 19 / 74 | -1 | -8.8% | -27.8% to +43.6% | -18.8% |
| HDT (experimental) | 16 / 74 | 15 / 74 | -1 | -6.7% | -31.5% to +461.0% | -16.2% |
| petgraph (external) | 18 / 74 | 17 / 74 | -1 | -0.3% | -22.4% to +27.3% | +0.1% |

## Winner shifts

Out of 74 cells, 7 cells changed winner between campaigns:

| Family | Workload | Nodes | Query % | Regime | 2026-10-06 Winner | 2026-10-09 Winner |
|---|---|---:|---:|---|---|---|
| dense | dense-bridge-churn-v1 | 512 | 10 | warmed | Workspace (opt-in) | Compact (default) |
| dense | redundant-bridge-churn-v1 | 128 | 10 | warmed | Compact (default) | Workspace (opt-in) |
| dense | redundant-bridge-churn-v1 | 128 | 50 | fresh | HDT (experimental) | Workspace (opt-in) |
| dense | redundant-bridge-churn-v1 | 128 | 50 | warmed | HDT (experimental) | Workspace (opt-in) |
| dense | redundant-bridge-churn-v1 | 512 | 10 | warmed | Compact (default) | Workspace (opt-in) |
| sparse | sustained-churn-path-v1 | 10,000 | 50 | warmed | petgraph (external) | Workspace (opt-in) |
| sparse | sustained-churn-path-v1 | 100,000 | 90 | warmed | ETT (experimental) | HDT (experimental) |

## Memory and Setup at Scale (100k and 1M nodes)

At 100k and 1M nodes, where engine allocations dominate process RSS:
- **ETT**: Process RSS decreased by median -17.6% at 100k and -18.8% at 1M (peak RSS dropped from 790.5 MiB to 607.9 MiB at 1M). Setup time increased by +3.1% to +6.2%.
- **HDT**: Process RSS decreased by median -16.8% at 100k and -15.5% at 1M (peak RSS dropped from 2201.1 MiB to 1910.4 MiB at 1M). Setup time was within -2.4% to +1.2%.
- **Controls** (`compact-bfs`, `compact-workspace`, `petgraph-dfs`): Process RSS remained essentially flat (median change < 0.2%).

Full per-cell data is preserved in [historical-comparison.json](historical-comparison.json).
