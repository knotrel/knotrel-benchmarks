# Long sustained histories — 2026-09-27

See the [main report](../2026-09-27-forest-scale/README.md) for interpretation,
backend semantics, timing boundaries and process-RSS scope.

Two trials per configuration; table values are medians of process summaries.

## Warmed results

| Family | Query % | Backend | Base ops ms | Setup ms | Query p50 µs | Cut p99 µs | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 40.181 | 1.743 | 0.625 | 0.125 | 13.5 |
| blocks | 50 | ett-scan | 65.225 | 11.103 | 0.188 | 2.833 | 18.1 |
| blocks | 50 | petgraph-dfs | 26.297 | 0.631 | 0.375 | 0.125 | 12.9 |
| blocks | 99 | compact-bfs | 113.414 | 1.719 | 0.916 | 0.208 | 15.3 |
| blocks | 99 | ett-scan | 19.258 | 10.883 | 0.167 | 8.979 | 19.0 |
| blocks | 99 | petgraph-dfs | 100.388 | 0.644 | 0.625 | 0.167 | 14.7 |
| path | 50 | compact-bfs | 24.026 | 1.613 | 0.333 | 0.125 | 13.5 |
| path | 50 | ett-scan | 34.467 | 10.896 | 0.125 | 1.292 | 17.2 |
| path | 50 | petgraph-dfs | 11.607 | 0.604 | 0.125 | 0.125 | 12.9 |
| path | 99 | compact-bfs | 98.702 | 1.651 | 0.605 | 0.521 | 15.3 |
| path | 99 | ett-scan | 17.767 | 10.619 | 0.167 | 5.396 | 18.8 |
| path | 99 | petgraph-dfs | 57.985 | 0.606 | 0.292 | 0.145 | 14.6 |

All process rows, including fresh results where measured, are in summary.csv.
No intervals are pooled. Base totals exclude setup and extra repeats.

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 10000 --query-percent 50 99 --rounds 1000 --trials 2 --regimes warmed
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

See [verification](verification.md).
