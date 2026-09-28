# Million-node pruning comparison

See the [main report](../2026-09-27-forest-pruned/README.md) for methods,
counter definitions, interpretation and limitations.

One process trial per configuration; no variability estimate.

## Warmed results

| Family | Query % | v1 operations ms | v2 operations ms | v1 cut p99 µs | v2 cut p99 µs |
| --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | 144.511 | 77.947 | 1916.292 | 873.833 |
| blocks | 99 | 66.126 | 29.744 | 23996.125 | 9845.500 |
| path | 50 | 48.112 | 11.398 | 549.875 | 19.083 |
| path | 99 | 27.640 | 10.890 | 6542.417 | 27.000 |

| Family | Query % | Engine | Base ops ms | Setup ms | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 54.223 | 207.619 | 160.9 |
| blocks | 50 | ett-scan | 77.947 | 3027.278 | 785.8 |
| blocks | 50 | ett-scan-v1 | 144.511 | 2488.442 | 770.4 |
| blocks | 50 | petgraph-dfs | 79.821 | 78.539 | 125.5 |
| blocks | 99 | compact-bfs | 987.780 | 208.627 | 162.8 |
| blocks | 99 | ett-scan | 29.744 | 3148.826 | 783.7 |
| blocks | 99 | ett-scan-v1 | 66.126 | 2383.854 | 769.8 |
| blocks | 99 | petgraph-dfs | 1690.898 | 80.111 | 125.6 |
| path | 50 | compact-bfs | 50.651 | 196.429 | 171.5 |
| path | 50 | ett-scan | 11.398 | 3029.859 | 804.3 |
| path | 50 | ett-scan-v1 | 48.112 | 2306.664 | 757.3 |
| path | 50 | petgraph-dfs | 41.436 | 72.833 | 121.2 |
| path | 99 | compact-bfs | 1285.011 | 197.473 | 506.4 |
| path | 99 | ett-scan | 10.890 | 3021.971 | 804.3 |
| path | 99 | ett-scan-v1 | 27.640 | 2298.501 | 758.0 |
| path | 99 | petgraph-dfs | 1136.692 | 71.667 | 121.2 |

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 1000000 --query-percent 50 99 --rounds 20 --trials 1 --regimes warmed --engines compact-bfs petgraph-dfs ett-scan-v1 ett-scan
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

All raw trials and [verification](verification.md) are retained.
