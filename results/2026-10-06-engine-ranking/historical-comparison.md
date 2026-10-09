# Historical comparison on matched traces

62 / 62 original main cells matched by trace fingerprint, actual operation counts and true/false query counts. The twelve one-million-node cells are excluded. Original results remain unchanged.

These measurements come from different days and builds and have different trial counts. They show observed drift, not the causal effect of an optimization. Consult the dedicated paired experiments for before/after evidence. The four-engine column holds the competitor set fixed; the five-engine column also admits Workspace.

| Engine | Original wins / 62 | Current wins, same four engines | Current wins, with Workspace | Median per-cell runtime drift | Drift min–max |
|---|---:|---:|---:|---:|---:|
| compact-bfs | 17 | 13 | 4 | +3.2% | -16.2% to +10.0% |
| ett-scan | 15 | 15 | 15 | +2.6% | -19.6% to +17.5% |
| hdt | 13 | 17 | 15 | -6.2% | -45.7% to +13.5% |
| petgraph-dfs | 17 | 17 | 16 | +1.8% | -24.1% to +28.4% |
| compact-workspace | not measured | excluded | 12 | — | — |

Drift = `100*(current runtime / historical runtime - 1)`. The median summarizes drift across this selected matrix; it is not an aggregate throughput gain. Per-cell raw medians and percentages are in [historical-comparison.json](historical-comparison.json).
