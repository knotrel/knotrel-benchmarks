# Immediate-repeat sensitivity — 2026-09-27

See the [main report](../2026-09-27-forest-scale/README.md) for interpretation,
backend semantics, timing boundaries and process-RSS scope.

Two trials per configuration; table values are medians of process summaries.
One extra immediate query per original query; repeats are separate from base totals, but alter subsequent cache state. Executed query fractions are 2/3 and 198/199 for base percentages 50 and 99.

## Warmed results

| Family | Query % | Backend | Base ops ms | Setup ms | Query p50 µs | Cut p99 µs | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 6.935 | 19.562 | 3.688 | 0.542 | 17.9 |
| blocks | 50 | ett-scan | 11.792 | 157.607 | 1.000 | 97.980 | 80.3 |
| blocks | 50 | petgraph-dfs | 8.367 | 6.874 | 3.271 | 0.458 | 14.1 |
| blocks | 99 | compact-bfs | 128.579 | 19.009 | 49.458 | 1.167 | 16.8 |
| blocks | 99 | ett-scan | 3.744 | 150.919 | 0.770 | 338.917 | 80.0 |
| blocks | 99 | petgraph-dfs | 213.255 | 7.930 | 80.709 | 0.917 | 14.1 |
| path | 50 | compact-bfs | 6.033 | 17.839 | 3.021 | 0.520 | 16.7 |
| path | 50 | ett-scan | 6.476 | 145.443 | 0.916 | 43.750 | 78.9 |
| path | 50 | petgraph-dfs | 4.595 | 6.514 | 1.938 | 0.625 | 13.8 |
| path | 99 | compact-bfs | 119.236 | 17.621 | 46.062 | 1.041 | 16.7 |
| path | 99 | ett-scan | 4.387 | 147.513 | 0.958 | 570.313 | 78.5 |
| path | 99 | petgraph-dfs | 103.853 | 6.629 | 39.458 | 0.834 | 13.8 |

All process rows, including fresh results where measured, are in summary.csv.
No intervals are pooled. Base totals exclude setup and extra repeats.

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 100000 --query-percent 50 99 --rounds 20 --trials 2 --regimes fresh warmed --query-repeats 1
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

See [verification](verification.md).
