# Million-node extension — 2026-09-27

See the [main report](../2026-09-27-forest-scale/README.md) for interpretation,
backend semantics, timing boundaries and process-RSS scope.

One trial per configuration: no estimate of between-process variability.

## Warmed results

| Family | Query % | Backend | Base ops ms | Setup ms | Query p50 µs | Cut p99 µs | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | compact-bfs | 53.611 | 209.657 | 25.041 | 1.292 | 160.9 |
| blocks | 50 | ett-scan | 127.985 | 2356.525 | 2.500 | 1771.042 | 701.2 |
| blocks | 50 | petgraph-dfs | 81.909 | 81.150 | 28.375 | 6.208 | 125.6 |
| blocks | 99 | compact-bfs | 992.576 | 219.096 | 453.833 | 1.833 | 163.5 |
| blocks | 99 | ett-scan | 68.259 | 2500.280 | 2.209 | 25016.875 | 572.1 |
| blocks | 99 | petgraph-dfs | 1702.887 | 80.606 | 803.500 | 10.209 | 125.5 |
| path | 50 | compact-bfs | 60.777 | 205.097 | 27.583 | 2.083 | 172.6 |
| path | 50 | ett-scan | 52.343 | 2323.574 | 2.500 | 617.584 | 639.8 |
| path | 50 | petgraph-dfs | 41.780 | 75.091 | 14.041 | 0.917 | 121.2 |
| path | 99 | compact-bfs | 1421.812 | 203.093 | 418.625 | 2.333 | 506.2 |
| path | 99 | ett-scan | 30.692 | 2299.257 | 2.792 | 6903.291 | 687.4 |
| path | 99 | petgraph-dfs | 1316.909 | 73.947 | 369.334 | 37.375 | 121.2 |

All process rows, including fresh results where measured, are in summary.csv.
No intervals are pooled. Base totals exclude setup and extra repeats.

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 1000000 --query-percent 10 50 90 99 --rounds 20 --trials 1 --regimes fresh warmed
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

See [verification](verification.md).
