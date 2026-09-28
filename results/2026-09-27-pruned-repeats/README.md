# Immediate-repeat pruning sensitivity

See the [main report](../2026-09-27-forest-pruned/README.md) for methods,
counter definitions, interpretation and limitations.

Two process trials per configuration; medians below are summaries, not pooled samples.
Every query is immediately repeated once. Repeats are separately timed; base totals still reflect the altered cache state.

## Warmed results

| Family | Query % | v1 operations ms | v2 operations ms | v1 cut p99 µs | v2 cut p99 µs |
| --- | ---: | ---: | ---: | ---: | ---: |
| blocks | 50 | 9.972 | 8.338 | 88.709 | 68.688 |
| blocks | 99 | 4.384 | 3.379 | 438.688 | 296.354 |
| path | 50 | 6.641 | 4.032 | 46.438 | 9.396 |
| path | 99 | 3.408 | 3.125 | 417.541 | 21.709 |

| Family | Query % | Engine | Base ops ms | Setup ms | Peak process RSS MiB |
| --- | ---: | --- | ---: | ---: | ---: |
| blocks | 50 | ett-scan | 8.338 | 202.388 | 83.7 |
| blocks | 50 | ett-scan-v1 | 9.972 | 150.675 | 80.6 |
| blocks | 99 | ett-scan | 3.379 | 203.411 | 83.6 |
| blocks | 99 | ett-scan-v1 | 4.384 | 148.033 | 81.0 |
| path | 50 | ett-scan | 4.032 | 199.242 | 82.1 |
| path | 50 | ett-scan-v1 | 6.641 | 165.258 | 79.2 |
| path | 99 | ett-scan | 3.125 | 198.292 | 82.2 |
| path | 99 | ett-scan-v1 | 3.408 | 142.800 | 78.7 |

```sh
python3 scripts/run_scale.py results/NEW_DIRECTORY --nodes 100000 --query-percent 50 99 --rounds 20 --trials 2 --regimes fresh warmed --query-repeats 1 --engines ett-scan-v1 ett-scan
python3 scripts/summarize_scale.py results/NEW_DIRECTORY
```

All raw trials and [verification](verification.md) are retained.
