# Long-history pruning comparison

See the [main report](../2026-09-27-forest-pruned/README.md) for methods,
counter definitions, interpretation and limitations.

Two process trials per configuration; medians below are summaries, not pooled samples.

## Warmed results

| Family | Query % | v1 operations ms | v2 operations ms | v1 cut p99 µs | v2 cut p99 µs |
| --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | 63.187 | 61.404 | 2.729 | 2.438 |
| blocks | 99 | 18.815 | 18.063 | 9.500 | 5.917 |
| path | 50 | 30.743 | 30.680 | 1.167 | 0.979 |
| path | 99 | 17.259 | 16.504 | 4.604 | 1.646 |

| Family | Query % | Engine | Base ops ms | Setup ms | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 39.725 | 1.759 | 13.6 |
| blocks | 50 | ett-scan | 61.404 | 12.159 | 18.0 |
| blocks | 50 | ett-scan-v1 | 63.187 | 10.666 | 18.3 |
| blocks | 50 | petgraph-dfs | 25.474 | 0.620 | 12.9 |
| blocks | 99 | compact-bfs | 110.623 | 1.693 | 15.4 |
| blocks | 99 | ett-scan | 18.063 | 12.354 | 18.9 |
| blocks | 99 | ett-scan-v1 | 18.815 | 10.981 | 19.2 |
| blocks | 99 | petgraph-dfs | 98.403 | 0.619 | 14.7 |
| path | 50 | compact-bfs | 23.512 | 1.649 | 13.6 |
| path | 50 | ett-scan | 30.680 | 11.952 | 17.0 |
| path | 50 | ett-scan-v1 | 30.743 | 10.479 | 17.3 |
| path | 50 | petgraph-dfs | 10.250 | 0.564 | 12.9 |
| path | 99 | compact-bfs | 87.478 | 1.591 | 15.3 |
| path | 99 | ett-scan | 16.504 | 11.757 | 18.6 |
| path | 99 | ett-scan-v1 | 17.259 | 10.505 | 19.0 |
| path | 99 | petgraph-dfs | 56.878 | 0.573 | 14.6 |

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 10000 --query-percent 50 99 --rounds 1000 --trials 2 --regimes warmed --engines compact-bfs petgraph-dfs ett-scan-v1 ett-scan
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

All raw trials and [verification](verification.md) are retained.
