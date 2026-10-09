# Per-scenario traversal comparison

Compact is the runtime baseline. Negative delta means lower runtime. Times are
medians across process trials (one trial for extreme exploration); brackets show
observed runtime min/max, not confidence intervals. RSS is whole-process peak.
All sizes, regimes and unfavorable results are retained. A dash means no operation
of that kind occurred; no synthetic zero percentile is invented.

## sparse: sustained-churn-blocks-v1, N=1024, queries=10, fresh

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 6/94.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.179 [0.178, 0.181] | +0.00% | 0.175 | 7.58 | 484 / 0.125 / 0.125 | 416 / 0.167 / 0.208 | 1.917 / 3.000 |
| Knotrel Workspace | 3 | 0.151 [0.150, 0.160] | -15.50% | 0.177 | 7.56 | 484 / 0.125 / 0.125 | 416 / 0.167 / 0.208 | 0.834 / 1.125 |
| External petgraph DFS | 3 | 0.111 [0.111, 0.115] | -38.00% | 0.075 | 7.58 | 484 / 0.084 / 0.125 | 416 / 0.084 / 0.084 | 0.709 / 1.083 |

## sparse: sustained-churn-blocks-v1, N=1024, queries=10, warmed

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 6/94.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.134 [0.130, 0.134] | +0.00% | 0.167 | 7.62 | 484 / 0.084 / 0.084 | 416 / 0.125 / 0.125 | 0.958 / 1.333 |
| Knotrel Workspace | 3 | 0.110 [0.108, 0.110] | -18.15% | 0.167 | 7.59 | 484 / 0.084 / 0.084 | 416 / 0.125 / 0.125 | 0.625 / 0.875 |
| External petgraph DFS | 3 | 0.089 [0.088, 0.095] | -33.59% | 0.060 | 7.58 | 484 / 0.083 / 0.084 | 416 / 0.083 / 0.084 | 0.625 / 1.000 |

## sparse: sustained-churn-blocks-v1, N=1024, queries=50, fresh

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 46/454.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.433 [0.401, 0.439] | +0.00% | 0.174 | 7.59 | 281 / 0.125 / 0.167 | 219 / 0.167 / 0.208 | 1.417 / 2.833 |
| Knotrel Workspace | 3 | 0.290 [0.287, 0.297] | -32.94% | 0.175 | 7.58 | 281 / 0.125 / 0.166 | 219 / 0.167 / 0.208 | 0.959 / 1.708 |
| External petgraph DFS | 3 | 0.251 [0.238, 0.255] | -41.92% | 0.080 | 7.58 | 281 / 0.084 / 0.125 | 219 / 0.084 / 0.084 | 0.833 / 1.625 |

## sparse: sustained-churn-blocks-v1, N=1024, queries=50, warmed

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 46/454.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.352 [0.349, 0.352] | +0.00% | 0.167 | 7.58 | 281 / 0.084 / 0.125 | 219 / 0.125 / 0.166 | 1.208 / 1.584 |
| Knotrel Workspace | 3 | 0.234 [0.220, 0.235] | -33.32% | 0.168 | 7.58 | 281 / 0.084 / 0.084 | 219 / 0.125 / 0.125 | 0.792 / 1.166 |
| External petgraph DFS | 3 | 0.230 [0.213, 0.288] | -34.63% | 0.061 | 7.58 | 281 / 0.084 / 0.084 | 219 / 0.083 / 0.084 | 0.792 / 1.625 |

## sparse: sustained-churn-blocks-v1, N=1024, queries=90, fresh

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 110/790.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.693 [0.688, 0.703] | +0.00% | 0.176 | 7.62 | 76 / 0.125 / 0.250 | 24 / 0.167 / 0.167 | 1.542 / 2.334 |
| Knotrel Workspace | 3 | 0.474 [0.468, 0.480] | -31.65% | 0.179 | 7.62 | 76 / 0.125 / 0.208 | 24 / 0.167 / 0.208 | 1.125 / 1.708 |
| External petgraph DFS | 3 | 0.527 [0.491, 0.545] | -24.01% | 0.075 | 7.58 | 76 / 0.125 / 0.166 | 24 / 0.084 / 0.084 | 1.458 / 2.500 |

## sparse: sustained-churn-blocks-v1, N=1024, queries=90, warmed

Initial edges: 1087; max degree: 3; density: 0.0020753146383186705; true/false queries: 110/790.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.576 [0.559, 0.624] | +0.00% | 0.153 | 7.59 | 76 / 0.084 / 0.125 | 24 / 0.125 / 0.125 | 1.250 / 1.833 |
| Knotrel Workspace | 3 | 0.390 [0.381, 0.393] | -32.25% | 0.166 | 7.62 | 76 / 0.084 / 0.125 | 24 / 0.166 / 0.167 | 0.917 / 1.458 |
| External petgraph DFS | 3 | 0.507 [0.506, 0.526] | -11.86% | 0.060 | 7.62 | 76 / 0.084 / 0.084 | 24 / 0.084 / 0.084 | 1.417 / 2.541 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=10, fresh

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 1/99.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.291 [0.291, 0.293] | +0.00% | 1.766 | 7.58 | 677 / 0.125 / 0.167 | 223 / 0.250 / 0.250 | 4.291 / 6.084 |
| Knotrel Workspace | 3 | 0.235 [0.231, 0.275] | -19.39% | 1.681 | 7.59 | 677 / 0.125 / 0.167 | 223 / 0.209 / 0.250 | 2.500 / 4.792 |
| External petgraph DFS | 3 | 0.203 [0.202, 0.209] | -30.48% | 0.678 | 7.62 | 677 / 0.125 / 0.125 | 223 / 0.125 / 0.125 | 2.667 / 6.500 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=10, warmed

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 1/99.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.261 [0.250, 0.272] | +0.00% | 1.742 | 7.58 | 677 / 0.125 / 0.125 | 223 / 0.209 / 0.250 | 2.834 / 5.333 |
| Knotrel Workspace | 3 | 0.220 [0.200, 0.252] | -15.65% | 1.742 | 7.59 | 677 / 0.125 / 0.166 | 223 / 0.209 / 0.250 | 2.083 / 3.958 |
| External petgraph DFS | 3 | 0.204 [0.197, 0.214] | -21.72% | 0.632 | 7.59 | 677 / 0.125 / 0.125 | 223 / 0.125 / 0.125 | 2.666 / 8.375 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=50, fresh

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 21/479.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.972 [0.925, 1.027] | +0.00% | 1.762 | 7.58 | 426 / 0.166 / 0.208 | 74 / 0.250 / 0.250 | 3.916 / 14.750 |
| Knotrel Workspace | 3 | 0.722 [0.700, 0.729] | -25.70% | 1.689 | 7.59 | 426 / 0.166 / 0.167 | 74 / 0.250 / 0.250 | 2.667 / 14.459 |
| External petgraph DFS | 3 | 0.921 [0.851, 1.234] | -5.26% | 0.687 | 7.59 | 426 / 0.125 / 0.167 | 74 / 0.166 / 0.167 | 4.125 / 17.458 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=50, warmed

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 21/479.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.875 [0.873, 0.914] | +0.00% | 1.739 | 7.59 | 426 / 0.125 / 0.167 | 74 / 0.250 / 0.250 | 3.083 / 9.584 |
| Knotrel Workspace | 3 | 0.679 [0.666, 0.679] | -22.34% | 1.736 | 7.58 | 426 / 0.125 / 0.167 | 74 / 0.250 / 0.250 | 2.584 / 12.334 |
| External petgraph DFS | 3 | 0.872 [0.871, 0.969] | -0.29% | 0.621 | 7.59 | 426 / 0.125 / 0.125 | 74 / 0.125 / 0.125 | 3.875 / 14.875 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=90, fresh

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 99/801.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 2.958 [2.953, 3.029] | +0.00% | 1.756 | 7.58 | 94 / 0.167 / 0.292 | 6 / 0.250 / 0.250 | 8.416 / 12.500 |
| Knotrel Workspace | 3 | 2.463 [2.448, 2.475] | -16.76% | 1.766 | 7.62 | 94 / 0.167 / 0.292 | 6 / 0.250 / 0.250 | 7.708 / 11.292 |
| External petgraph DFS | 3 | 3.999 [3.959, 4.064] | +35.19% | 0.664 | 7.59 | 94 / 0.167 / 0.334 | 6 / 0.167 / 0.167 | 12.875 / 19.000 |

## sparse: sustained-churn-blocks-v1, N=10000, queries=90, warmed

Initial edges: 10624; max degree: 3; density: 0.0002125012501250125; true/false queries: 99/801.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 2.853 [2.843, 2.914] | +0.00% | 1.741 | 7.59 | 94 / 0.125 / 0.167 | 6 / 0.209 / 0.209 | 8.333 / 12.167 |
| Knotrel Workspace | 3 | 2.367 [2.359, 2.377] | -17.05% | 1.735 | 7.58 | 94 / 0.125 / 0.167 | 6 / 0.209 / 0.209 | 7.625 / 11.209 |
| External petgraph DFS | 3 | 3.940 [3.924, 4.058] | +38.07% | 0.622 | 7.58 | 94 / 0.125 / 0.167 | 6 / 0.125 / 0.125 | 13.125 / 18.500 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=10, fresh

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.976 [0.969, 0.988] | +0.00% | 19.719 | 16.80 | 865 / 0.417 / 0.542 | 35 / 0.291 / 0.292 | 17.875 / 50.542 |
| Knotrel Workspace | 3 | 0.884 [0.824, 1.224] | -9.38% | 20.028 | 16.70 | 865 / 0.459 / 0.625 | 35 / 0.333 / 0.333 | 15.708 / 48.375 |
| External petgraph DFS | 3 | 1.034 [0.946, 1.096] | +6.01% | 7.874 | 14.19 | 865 / 0.250 / 0.375 | 35 / 0.167 / 0.209 | 22.250 / 73.250 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=10, warmed

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.971 [0.777, 1.149] | +0.00% | 18.984 | 16.88 | 865 / 0.500 / 0.666 | 35 / 0.292 / 0.333 | 17.250 / 45.542 |
| Knotrel Workspace | 3 | 0.765 [0.713, 0.813] | -21.19% | 18.908 | 16.70 | 865 / 0.292 / 0.417 | 35 / 0.292 / 0.292 | 14.875 / 46.875 |
| External petgraph DFS | 3 | 0.991 [0.988, 1.163] | +2.04% | 6.961 | 14.20 | 865 / 0.167 / 0.209 | 35 / 0.167 / 0.167 | 23.000 / 76.542 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=50, fresh

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 20/480.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 5.265 [5.161, 9.706] | +0.00% | 19.660 | 16.83 | 490 / 0.417 / 0.542 | 10 / 0.500 / 0.500 | 37.208 / 93.000 |
| Knotrel Workspace | 3 | 4.552 [4.308, 4.638] | -13.54% | 19.349 | 16.67 | 490 / 0.375 / 0.500 | 10 / 0.292 / 0.292 | 32.583 / 93.834 |
| External petgraph DFS | 3 | 7.143 [7.134, 7.250] | +35.68% | 7.353 | 14.17 | 490 / 0.292 / 0.375 | 10 / 0.167 / 0.167 | 52.209 / 142.917 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=50, warmed

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 20/480.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 5.064 [5.045, 5.069] | +0.00% | 18.862 | 16.80 | 490 / 0.292 / 0.542 | 10 / 0.291 / 0.291 | 33.292 / 90.625 |
| Knotrel Workspace | 3 | 4.461 [4.442, 4.707] | -11.89% | 19.105 | 16.78 | 490 / 0.292 / 0.500 | 10 / 0.292 / 0.292 | 33.292 / 94.000 |
| External petgraph DFS | 3 | 7.504 [7.211, 7.649] | +48.19% | 7.006 | 14.17 | 490 / 0.250 / 0.834 | 10 / 0.250 / 0.250 | 52.500 / 157.333 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=90, fresh

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 121/779.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 25.422 [24.301, 25.582] | +0.00% | 19.885 | 16.89 | 100 / 0.625 / 1.125 | — | 63.125 / 172.417 |
| Knotrel Workspace | 3 | 23.856 [23.649, 24.026] | -6.16% | 19.354 | 16.64 | 100 / 0.625 / 1.000 | — | 62.375 / 182.375 |
| External petgraph DFS | 3 | 39.849 [38.851, 40.452] | +56.75% | 7.626 | 14.14 | 100 / 0.583 / 0.625 | — | 103.834 / 289.667 |

## sparse: sustained-churn-blocks-v1, N=100000, queries=90, warmed

Initial edges: 106249; max degree: 3; density: 2.1250012500125e-05; true/false queries: 121/779.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 26.971 [24.433, 51.968] | +0.00% | 19.525 | 17.09 | 100 / 0.584 / 0.792 | — | 81.041 / 179.209 |
| Knotrel Workspace | 3 | 24.018 [23.570, 35.864] | -10.95% | 21.579 | 16.78 | 100 / 0.542 / 0.750 | — | 62.042 / 182.625 |
| External petgraph DFS | 3 | 39.108 [39.056, 39.734] | +45.00% | 6.983 | 14.17 | 100 / 0.583 / 0.667 | — | 99.083 / 290.917 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=10, fresh

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 5.796 [5.431, 5.903] | +0.00% | 215.384 | 133.61 | 896 / 1.042 / 1.333 | 4 / 0.625 / 0.625 | 145.125 / 275.500 |
| Knotrel Workspace | 3 | 5.401 [5.009, 5.510] | -6.82% | 217.716 | 136.95 | 896 / 0.959 / 1.209 | 4 / 0.625 / 0.625 | 138.083 / 371.500 |
| External petgraph DFS | 3 | 7.253 [7.055, 7.271] | +25.12% | 81.985 | 109.61 | 896 / 0.708 / 0.833 | 4 / 0.333 / 0.333 | 218.792 / 382.250 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=10, warmed

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 5.297 [5.233, 5.623] | +0.00% | 207.943 | 156.09 | 896 / 0.792 / 0.959 | 4 / 0.583 / 0.583 | 139.958 / 252.667 |
| Knotrel Workspace | 3 | 4.896 [4.786, 4.993] | -7.57% | 211.112 | 159.89 | 896 / 0.792 / 0.917 | 4 / 0.500 / 0.500 | 136.291 / 310.834 |
| External petgraph DFS | 3 | 10.401 [10.374, 15.285] | +96.35% | 80.813 | 125.59 | 896 / 3.959 / 7.333 | 4 / 1.584 / 1.584 | 321.750 / 585.042 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=50, fresh

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 18/482.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 46.055 [44.360, 46.667] | +0.00% | 221.753 | 137.94 | 499 / 1.209 / 1.625 | 1 / 1.250 / 1.250 | 341.333 / 586.500 |
| Knotrel Workspace | 3 | 41.404 [41.183, 42.911] | -10.10% | 216.661 | 140.88 | 499 / 1.042 / 1.250 | 1 / 0.750 / 0.750 | 328.792 / 587.167 |
| External petgraph DFS | 3 | 65.824 [65.713, 68.004] | +42.93% | 82.542 | 109.62 | 499 / 0.875 / 1.166 | 1 / 0.666 / 0.666 | 546.666 / 895.709 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=50, warmed

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 18/482.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 42.827 [42.798, 43.379] | +0.00% | 205.617 | 161.00 | 499 / 0.917 / 1.125 | 1 / 0.875 / 0.875 | 333.375 / 511.209 |
| Knotrel Workspace | 3 | 43.469 [41.516, 48.771] | +1.50% | 209.337 | 163.77 | 499 / 1.042 / 1.417 | 1 / 1.083 / 1.083 | 343.875 / 602.334 |
| External petgraph DFS | 3 | 69.541 [69.349, 69.940] | +62.38% | 80.856 | 125.70 | 499 / 5.500 / 8.042 | 1 / 0.625 / 0.625 | 552.875 / 915.041 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=90, fresh

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 125/775.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 243.762 [240.710, 246.971] | +0.00% | 218.054 | 138.00 | 100 / 1.333 / 1.500 | — | 861.458 / 1130.708 |
| Knotrel Workspace | 3 | 245.570 [241.767, 246.318] | +0.74% | 214.293 | 140.81 | 100 / 1.250 / 1.458 | — | 854.084 / 1102.000 |
| External petgraph DFS | 3 | 404.614 [403.025, 405.843] | +65.99% | 85.290 | 109.61 | 100 / 1.209 / 1.459 | — | 1440.292 / 1828.292 |

## sparse: sustained-churn-blocks-v1, N=1000000, queries=90, warmed

Initial edges: 1062499; max degree: 3; density: 2.125000125000125e-06; true/false queries: 125/775.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 242.076 [238.054, 253.839] | +0.00% | 205.896 | 163.00 | 100 / 1.333 / 1.458 | — | 856.667 / 1044.291 |
| Knotrel Workspace | 3 | 244.324 [241.924, 244.820] | +0.93% | 209.329 | 163.77 | 100 / 1.250 / 1.666 | — | 855.542 / 1091.334 |
| External petgraph DFS | 3 | 426.956 [406.563, 716.364] | +76.37% | 81.633 | 125.69 | 100 / 7.708 / 8.750 | — | 1473.041 / 1926.125 |

## sparse: sustained-churn-path-v1, N=1024, queries=10, fresh

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.136 [0.134, 0.138] | +0.00% | 0.169 | 7.58 | 667 / 0.084 / 0.125 | 233 / 0.167 / 0.209 | 1.333 / 1.750 |
| Knotrel Workspace | 3 | 0.118 [0.112, 0.119] | -13.11% | 0.166 | 7.58 | 667 / 0.084 / 0.125 | 233 / 0.167 / 0.208 | 0.375 / 0.708 |
| External petgraph DFS | 3 | 0.091 [0.089, 0.095] | -33.10% | 0.065 | 7.58 | 667 / 0.084 / 0.125 | 233 / 0.084 / 0.084 | 0.333 / 0.709 |

## sparse: sustained-churn-path-v1, N=1024, queries=10, warmed

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.107 [0.105, 0.113] | +0.00% | 0.163 | 7.59 | 667 / 0.084 / 0.125 | 233 / 0.125 / 0.166 | 0.583 / 0.833 |
| Knotrel Workspace | 3 | 0.096 [0.095, 0.097] | -10.93% | 0.157 | 7.58 | 667 / 0.084 / 0.084 | 233 / 0.125 / 0.166 | 0.333 / 0.666 |
| External petgraph DFS | 3 | 0.073 [0.067, 0.073] | -32.44% | 0.055 | 7.59 | 667 / 0.083 / 0.084 | 233 / 0.083 / 0.084 | 0.292 / 0.417 |

## sparse: sustained-churn-path-v1, N=1024, queries=50, fresh

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 12/488.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.216 [0.212, 0.298] | +0.00% | 0.173 | 7.58 | 418 / 0.084 / 0.167 | 82 / 0.208 / 0.209 | 0.625 / 2.458 |
| Knotrel Workspace | 3 | 0.149 [0.149, 0.154] | -30.78% | 0.166 | 7.59 | 418 / 0.084 / 0.125 | 82 / 0.208 / 0.250 | 0.375 / 0.667 |
| External petgraph DFS | 3 | 0.126 [0.126, 0.127] | -41.74% | 0.065 | 7.58 | 418 / 0.084 / 0.084 | 82 / 0.084 / 0.125 | 0.375 / 0.584 |

## sparse: sustained-churn-path-v1, N=1024, queries=50, warmed

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 12/488.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.186 [0.174, 0.187] | +0.00% | 0.154 | 7.58 | 418 / 0.084 / 0.084 | 82 / 0.125 / 0.167 | 0.583 / 0.958 |
| Knotrel Workspace | 3 | 0.125 [0.125, 0.155] | -32.83% | 0.154 | 7.59 | 418 / 0.084 / 0.084 | 82 / 0.125 / 0.167 | 0.334 / 0.667 |
| External petgraph DFS | 3 | 0.108 [0.108, 0.109] | -41.69% | 0.056 | 7.67 | 418 / 0.084 / 0.084 | 82 / 0.084 / 0.084 | 0.333 / 0.625 |

## sparse: sustained-churn-path-v1, N=1024, queries=90, fresh

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 56/844.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.492 [0.491, 0.495] | +0.00% | 0.166 | 7.58 | 94 / 0.125 / 0.291 | 6 / 0.209 / 0.209 | 1.125 / 3.000 |
| Knotrel Workspace | 3 | 0.327 [0.327, 0.337] | -33.54% | 0.166 | 7.61 | 94 / 0.125 / 0.209 | 6 / 0.250 / 0.250 | 0.792 / 1.917 |
| External petgraph DFS | 3 | 0.303 [0.302, 0.303] | -38.55% | 0.066 | 7.62 | 94 / 0.084 / 0.209 | 6 / 0.084 / 0.084 | 0.917 / 1.708 |

## sparse: sustained-churn-path-v1, N=1024, queries=90, warmed

Initial edges: 1023; max degree: 2; density: 0.001953125; true/false queries: 56/844.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.465 [0.442, 0.473] | +0.00% | 0.150 | 7.61 | 94 / 0.084 / 0.125 | 6 / 0.125 / 0.125 | 1.083 / 2.250 |
| Knotrel Workspace | 3 | 0.305 [0.294, 0.313] | -34.55% | 0.152 | 7.59 | 94 / 0.084 / 0.084 | 6 / 0.125 / 0.125 | 0.791 / 1.792 |
| External petgraph DFS | 3 | 0.364 [0.361, 0.368] | -21.77% | 0.053 | 7.58 | 94 / 0.084 / 0.084 | 6 / 0.083 / 0.083 | 1.208 / 2.291 |

## sparse: sustained-churn-path-v1, N=10000, queries=10, fresh

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.210 [0.207, 0.260] | +0.00% | 1.676 | 7.59 | 862 / 0.125 / 0.166 | 38 / 0.250 / 0.292 | 2.584 / 6.375 |
| Knotrel Workspace | 3 | 0.170 [0.160, 0.174] | -18.88% | 1.690 | 7.58 | 862 / 0.125 / 0.125 | 38 / 0.250 / 0.250 | 1.167 / 3.917 |
| External petgraph DFS | 3 | 0.147 [0.146, 0.150] | -30.04% | 0.621 | 7.59 | 862 / 0.125 / 0.125 | 38 / 0.125 / 0.125 | 1.334 / 3.083 |

## sparse: sustained-churn-path-v1, N=10000, queries=10, warmed

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.195 [0.191, 0.203] | +0.00% | 1.655 | 7.58 | 862 / 0.125 / 0.125 | 38 / 0.209 / 0.250 | 1.667 / 4.708 |
| Knotrel Workspace | 3 | 0.165 [0.159, 0.166] | -15.35% | 1.667 | 7.58 | 862 / 0.125 / 0.125 | 38 / 0.209 / 0.250 | 1.125 / 3.916 |
| External petgraph DFS | 3 | 0.149 [0.147, 0.174] | -23.86% | 0.584 | 7.59 | 862 / 0.125 / 0.125 | 38 / 0.125 / 0.125 | 1.750 / 3.334 |

## sparse: sustained-churn-path-v1, N=10000, queries=50, fresh

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 7/493.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.697 [0.644, 0.784] | +0.00% | 1.654 | 7.59 | 488 / 0.125 / 0.167 | 12 / 0.291 / 0.291 | 3.292 / 8.667 |
| Knotrel Workspace | 3 | 0.506 [0.485, 0.516] | -27.41% | 1.667 | 7.62 | 488 / 0.125 / 0.167 | 12 / 0.250 / 0.250 | 2.584 / 8.208 |
| External petgraph DFS | 3 | 0.464 [0.444, 0.472] | -33.47% | 0.629 | 7.56 | 488 / 0.125 / 0.125 | 12 / 0.125 / 0.125 | 2.500 / 5.959 |

## sparse: sustained-churn-path-v1, N=10000, queries=50, warmed

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 7/493.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.667 [0.632, 0.682] | +0.00% | 1.639 | 7.58 | 488 / 0.125 / 0.166 | 12 / 0.250 / 0.250 | 3.166 / 9.500 |
| Knotrel Workspace | 3 | 0.473 [0.473, 0.504] | -29.00% | 1.532 | 7.61 | 488 / 0.125 / 0.125 | 12 / 0.209 / 0.209 | 2.500 / 7.875 |
| External petgraph DFS | 3 | 0.454 [0.447, 0.455] | -31.97% | 0.579 | 7.59 | 488 / 0.125 / 0.125 | 12 / 0.084 / 0.084 | 2.542 / 5.875 |

## sparse: sustained-churn-path-v1, N=10000, queries=90, fresh

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 56/844.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 2.632 [2.454, 2.641] | +0.00% | 1.680 | 7.59 | 100 / 0.166 / 0.208 | — | 8.958 / 15.958 |
| Knotrel Workspace | 3 | 2.221 [2.212, 2.499] | -15.63% | 1.733 | 7.59 | 100 / 0.209 / 0.291 | — | 8.292 / 14.750 |
| External petgraph DFS | 3 | 2.140 [2.101, 2.223] | -18.71% | 0.622 | 7.59 | 100 / 0.166 / 0.209 | — | 7.667 / 11.792 |

## sparse: sustained-churn-path-v1, N=10000, queries=90, warmed

Initial edges: 9999; max degree: 2; density: 0.0002; true/false queries: 56/844.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 2.672 [2.593, 2.703] | +0.00% | 1.651 | 7.58 | 100 / 0.167 / 0.250 | — | 9.625 / 15.583 |
| Knotrel Workspace | 3 | 2.230 [2.202, 2.259] | -16.56% | 1.677 | 7.62 | 100 / 0.125 / 0.167 | — | 8.417 / 14.792 |
| External petgraph DFS | 3 | 2.559 [2.103, 2.730] | -4.25% | 0.595 | 7.62 | 100 / 0.125 / 0.125 | — | 8.875 / 14.708 |

## sparse: sustained-churn-path-v1, N=100000, queries=10, fresh

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 0/100.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.959 [0.817, 1.123] | +0.00% | 18.679 | 16.75 | 894 / 1.167 / 2.250 | 6 / 0.375 / 0.375 | 18.667 / 40.250 |
| Knotrel Workspace | 3 | 0.666 [0.656, 0.736] | -30.53% | 18.547 | 16.58 | 894 / 0.417 / 0.542 | 6 / 0.375 / 0.375 | 15.125 / 34.666 |
| External petgraph DFS | 3 | 0.571 [0.555, 0.589] | -40.50% | 7.193 | 13.88 | 894 / 0.333 / 0.458 | 6 / 0.125 / 0.125 | 11.375 / 27.250 |

## sparse: sustained-churn-path-v1, N=100000, queries=10, warmed

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 0/100.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.716 [0.698, 0.745] | +0.00% | 17.987 | 16.80 | 894 / 0.333 / 0.375 | 6 / 0.375 / 0.375 | 13.833 / 35.667 |
| Knotrel Workspace | 3 | 0.626 [0.600, 0.737] | -12.54% | 17.869 | 16.62 | 894 / 0.375 / 0.792 | 6 / 0.375 / 0.375 | 14.584 / 32.416 |
| External petgraph DFS | 3 | 0.518 [0.511, 0.538] | -27.69% | 6.514 | 13.91 | 894 / 0.250 / 0.292 | 6 / 0.125 / 0.125 | 12.042 / 24.250 |

## sparse: sustained-churn-path-v1, N=100000, queries=50, fresh

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 13/487.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 4.666 [4.604, 4.848] | +0.00% | 19.118 | 16.67 | 498 / 0.458 / 0.958 | 2 / 0.416 / 0.416 | 32.417 / 82.791 |
| Knotrel Workspace | 3 | 4.285 [3.965, 4.286] | -8.18% | 17.901 | 16.62 | 498 / 0.584 / 1.125 | 2 / 0.500 / 0.500 | 29.834 / 83.000 |
| External petgraph DFS | 3 | 3.702 [3.691, 3.766] | -20.67% | 7.228 | 13.88 | 498 / 0.375 / 1.083 | 2 / 0.208 / 0.208 | 25.625 / 70.500 |

## sparse: sustained-churn-path-v1, N=100000, queries=50, warmed

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 13/487.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 4.531 [4.414, 4.546] | +0.00% | 17.011 | 16.77 | 498 / 0.333 / 0.417 | 2 / 0.375 / 0.375 | 31.500 / 79.625 |
| Knotrel Workspace | 3 | 3.829 [3.661, 3.908] | -15.51% | 16.911 | 16.69 | 498 / 0.333 / 0.458 | 2 / 0.292 / 0.292 | 29.667 / 83.000 |
| External petgraph DFS | 3 | 3.671 [3.628, 3.765] | -18.99% | 6.936 | 13.94 | 498 / 0.334 / 0.625 | 2 / 0.167 / 0.167 | 24.917 / 74.583 |

## sparse: sustained-churn-path-v1, N=100000, queries=90, fresh

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 64/836.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 23.193 [23.117, 23.667] | +0.00% | 18.560 | 16.61 | 100 / 0.500 / 0.625 | — | 82.666 / 178.625 |
| Knotrel Workspace | 3 | 23.816 [21.808, 24.138] | +2.69% | 20.167 | 16.53 | 100 / 0.791 / 3.167 | — | 91.709 / 195.959 |
| External petgraph DFS | 3 | 19.650 [19.642, 20.924] | -15.28% | 7.171 | 13.84 | 100 / 0.458 / 0.667 | — | 67.750 / 144.625 |

## sparse: sustained-churn-path-v1, N=100000, queries=90, warmed

Initial edges: 99999; max degree: 2; density: 2e-05; true/false queries: 64/836.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 23.138 [22.589, 23.550] | +0.00% | 17.987 | 16.67 | 100 / 0.542 / 0.667 | — | 81.917 / 178.959 |
| Knotrel Workspace | 3 | 22.213 [22.117, 22.284] | -3.99% | 17.740 | 16.61 | 100 / 0.417 / 0.542 | — | 86.833 / 181.083 |
| External petgraph DFS | 3 | 19.466 [19.403, 19.869] | -15.87% | 6.620 | 13.88 | 100 / 0.500 / 0.583 | — | 66.208 / 143.584 |

## sparse: sustained-churn-path-v1, N=1000000, queries=10, fresh

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 5.634 [5.291, 5.696] | +0.00% | 207.773 | 132.23 | 900 / 1.667 / 2.000 | — | 181.083 / 285.458 |
| Knotrel Workspace | 3 | 6.008 [4.747, 6.017] | +6.63% | 204.296 | 135.97 | 900 / 2.625 / 4.334 | — | 167.041 / 448.084 |
| External petgraph DFS | 3 | 4.990 [3.818, 5.457] | -11.43% | 76.088 | 90.77 | 900 / 1.500 / 2.500 | — | 155.084 / 345.125 |

## sparse: sustained-churn-path-v1, N=1000000, queries=10, warmed

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 2/98.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 4.640 [4.630, 4.886] | +0.00% | 195.488 | 161.20 | 900 / 1.000 / 1.333 | — | 135.167 / 229.709 |
| Knotrel Workspace | 3 | 4.772 [4.706, 4.919] | +2.85% | 189.403 | 144.92 | 900 / 1.458 / 1.750 | — | 132.625 / 313.292 |
| External petgraph DFS | 3 | 3.801 [3.653, 3.824] | -18.07% | 72.369 | 121.33 | 900 / 1.125 / 1.375 | — | 130.041 / 257.041 |

## sparse: sustained-churn-path-v1, N=1000000, queries=50, fresh

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 15/485.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 46.318 [45.757, 68.149] | +0.00% | 226.944 | 149.78 | 500 / 1.291 / 1.750 | — | 252.416 / 919.250 |
| Knotrel Workspace | 3 | 41.184 [40.365, 43.209] | -11.09% | 202.957 | 143.02 | 500 / 1.333 / 2.083 | — | 236.583 / 837.125 |
| External petgraph DFS | 3 | 36.365 [35.704, 36.753] | -21.49% | 75.495 | 90.78 | 500 / 0.916 / 1.791 | — | 197.208 / 905.500 |

## sparse: sustained-churn-path-v1, N=1000000, queries=50, warmed

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 15/485.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 41.509 [40.662, 41.676] | +0.00% | 197.291 | 171.56 | 500 / 0.917 / 1.208 | — | 227.041 / 781.666 |
| Knotrel Workspace | 3 | 42.075 [40.258, 42.168] | +1.36% | 197.540 | 151.98 | 500 / 1.167 / 1.833 | — | 243.916 / 844.542 |
| External petgraph DFS | 3 | 35.425 [35.350, 42.435] | -14.66% | 73.173 | 121.34 | 500 / 0.709 / 0.958 | — | 203.166 / 927.084 |

## sparse: sustained-churn-path-v1, N=1000000, queries=90, fresh

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 51/849.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 209.425 [208.870, 220.718] | +0.00% | 203.517 | 182.06 | 100 / 2.042 / 2.708 | — | 785.167 / 2079.958 |
| Knotrel Workspace | 3 | 208.766 [206.444, 213.475] | -0.31% | 202.163 | 142.97 | 100 / 1.208 / 1.875 | — | 817.292 / 1728.375 |
| External petgraph DFS | 3 | 178.564 [176.633, 178.686] | -14.74% | 74.824 | 90.75 | 100 / 1.417 / 2.500 | — | 661.416 / 1509.542 |

## sparse: sustained-churn-path-v1, N=1000000, queries=90, warmed

Initial edges: 999999; max degree: 2; density: 2e-06; true/false queries: 51/849.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 206.993 [205.892, 238.883] | +0.00% | 201.447 | 205.44 | 100 / 1.250 / 1.417 | — | 796.792 / 1913.042 |
| Knotrel Workspace | 3 | 209.535 [205.440, 210.689] | +1.23% | 200.027 | 151.94 | 100 / 1.125 / 1.417 | — | 811.833 / 1725.541 |
| External petgraph DFS | 3 | 178.285 [176.134, 180.455] | -13.87% | 73.231 | 121.33 | 100 / 0.917 / 1.375 | — | 667.083 / 1553.125 |

## dense: dense-bridge-churn-v1, N=128, queries=10, fresh

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 79/21.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.174 [0.174, 0.175] | +0.00% | 0.273 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.042 | 2.666 / 2.917 |
| Knotrel Workspace | 3 | 0.170 [0.150, 0.171] | -2.32% | 0.270 | 7.62 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.042 | 2.709 / 2.750 |
| External petgraph DFS | 3 | 0.890 [0.888, 0.941] | +411.13% | 0.394 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.125 / 0.167 | 17.916 / 20.709 |

## dense: dense-bridge-churn-v1, N=128, queries=10, warmed

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 79/21.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.170 [0.170, 0.171] | +0.00% | 0.269 | 7.62 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.042 | 2.583 / 2.625 |
| Knotrel Workspace | 3 | 0.157 [0.153, 0.161] | -7.38% | 0.271 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.042 | 2.542 / 2.625 |
| External petgraph DFS | 3 | 0.915 [0.889, 0.939] | +438.86% | 0.379 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.125 / 0.167 | 18.208 / 20.250 |

## dense: dense-bridge-churn-v1, N=128, queries=50, fresh

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 379/121.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.721 [0.675, 0.773] | +0.00% | 0.273 | 7.61 | 250 / 0.042 / 0.083 | 250 / 0.042 / 0.042 | 2.584 / 2.667 |
| Knotrel Workspace | 3 | 0.669 [0.664, 0.714] | -7.18% | 0.282 | 7.58 | 250 / 0.042 / 0.125 | 250 / 0.042 / 0.083 | 2.500 / 2.542 |
| External petgraph DFS | 3 | 4.601 [4.561, 4.692] | +537.89% | 0.394 | 7.58 | 250 / 0.042 / 0.042 | 250 / 0.167 / 0.208 | 19.750 / 20.625 |

## dense: dense-bridge-churn-v1, N=128, queries=50, warmed

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 379/121.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.718 [0.716, 0.722] | +0.00% | 0.270 | 7.62 | 250 / 0.042 / 0.042 | 250 / 0.042 / 0.083 | 2.583 / 2.625 |
| Knotrel Workspace | 3 | 0.657 [0.656, 0.677] | -8.45% | 0.271 | 7.59 | 250 / 0.042 / 0.042 | 250 / 0.042 / 0.083 | 2.500 / 2.500 |
| External petgraph DFS | 3 | 4.633 [4.569, 4.636] | +545.21% | 0.377 | 7.58 | 250 / 0.042 / 0.042 | 250 / 0.167 / 0.209 | 19.459 / 21.125 |

## dense: dense-bridge-churn-v1, N=128, queries=90, fresh

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 687/213.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.202 [1.199, 1.217] | +0.00% | 0.270 | 7.59 | 50 / 0.083 / 0.291 | 50 / 0.042 / 0.084 | 2.542 / 2.750 |
| Knotrel Workspace | 3 | 1.118 [1.109, 1.120] | -6.97% | 0.271 | 7.58 | 50 / 0.042 / 0.250 | 50 / 0.083 / 0.167 | 2.500 / 2.541 |
| External petgraph DFS | 3 | 8.272 [8.260, 8.326] | +588.14% | 0.394 | 7.59 | 50 / 0.042 / 0.084 | 50 / 0.167 / 0.167 | 19.167 / 20.958 |

## dense: dense-bridge-churn-v1, N=128, queries=90, warmed

Initial edges: 4033; max degree: 64; density: 0.4961860236220472; true/false queries: 687/213.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.199 [1.197, 1.216] | +0.00% | 0.272 | 7.62 | 50 / 0.042 / 0.083 | 50 / 0.084 / 0.084 | 2.584 / 2.625 |
| Knotrel Workspace | 3 | 1.037 [1.037, 1.042] | -13.51% | 0.271 | 7.59 | 50 / 0.042 / 0.083 | 50 / 0.083 / 0.084 | 2.333 / 2.375 |
| External petgraph DFS | 3 | 8.349 [8.127, 8.369] | +596.16% | 0.380 | 7.59 | 50 / 0.042 / 0.042 | 50 / 0.167 / 0.208 | 19.167 / 21.167 |

## dense: dense-bridge-churn-v1, N=512, queries=10, fresh

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 77/23.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.952 [1.944, 2.009] | +0.00% | 4.775 | 7.58 | 450 / 0.083 / 0.084 | 450 / 0.084 / 0.084 | 37.333 / 38.333 |
| Knotrel Workspace | 3 | 2.084 [2.076, 2.121] | +6.77% | 4.693 | 7.59 | 450 / 0.083 / 0.084 | 450 / 0.084 / 0.084 | 40.291 / 40.500 |
| External petgraph DFS | 3 | 17.295 [16.940, 18.205] | +785.95% | 19.853 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.500 / 0.542 | 360.042 / 396.459 |

## dense: dense-bridge-churn-v1, N=512, queries=10, warmed

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 77/23.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.945 [1.944, 1.977] | +0.00% | 4.562 | 7.59 | 450 / 0.084 / 0.084 | 450 / 0.084 / 0.125 | 37.250 / 37.459 |
| Knotrel Workspace | 3 | 1.944 [1.927, 2.023] | -0.04% | 4.628 | 7.59 | 450 / 0.083 / 0.084 | 450 / 0.084 / 0.125 | 37.542 / 37.833 |
| External petgraph DFS | 3 | 17.166 [16.662, 18.027] | +782.57% | 19.360 | 7.59 | 450 / 0.042 / 0.042 | 450 / 0.500 / 0.542 | 362.208 / 384.084 |

## dense: dense-bridge-churn-v1, N=512, queries=50, fresh

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 369/131.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 9.588 [9.498, 9.690] | +0.00% | 4.811 | 7.58 | 250 / 0.084 / 0.166 | 250 / 0.125 / 0.208 | 37.917 / 43.083 |
| Knotrel Workspace | 3 | 10.293 [10.279, 10.338] | +7.36% | 4.683 | 7.58 | 250 / 0.084 / 0.125 | 250 / 0.084 / 0.125 | 40.167 / 40.541 |
| External petgraph DFS | 3 | 94.638 [93.972, 96.904] | +887.09% | 19.514 | 7.58 | 250 / 0.042 / 0.250 | 250 / 0.542 / 0.625 | 381.375 / 428.833 |

## dense: dense-bridge-churn-v1, N=512, queries=50, warmed

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 369/131.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 9.675 [9.674, 9.719] | +0.00% | 4.629 | 7.61 | 250 / 0.084 / 0.125 | 250 / 0.125 / 0.125 | 37.833 / 42.542 |
| Knotrel Workspace | 3 | 10.070 [9.794, 10.356] | +4.09% | 4.585 | 7.62 | 250 / 0.084 / 0.125 | 250 / 0.125 / 0.125 | 41.291 / 44.291 |
| External petgraph DFS | 3 | 95.078 [93.200, 96.216] | +882.76% | 19.084 | 7.62 | 250 / 0.042 / 0.083 | 250 / 0.542 / 0.625 | 384.417 / 425.917 |

## dense: dense-bridge-churn-v1, N=512, queries=90, fresh

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 667/233.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 17.227 [17.213, 17.403] | +0.00% | 4.709 | 7.61 | 50 / 0.125 / 0.250 | 50 / 0.167 / 0.167 | 37.209 / 40.750 |
| Knotrel Workspace | 3 | 18.507 [18.370, 18.561] | +7.43% | 4.827 | 7.59 | 50 / 0.209 / 0.333 | 50 / 0.208 / 0.500 | 41.125 / 44.208 |
| External petgraph DFS | 3 | 171.448 [169.679, 177.591] | +895.21% | 19.249 | 7.62 | 50 / 0.125 / 0.667 | 50 / 0.792 / 0.959 | 389.375 / 446.334 |

## dense: dense-bridge-churn-v1, N=512, queries=90, warmed

Initial edges: 65281; max degree: 256; density: 0.49902917074363995; true/false queries: 667/233.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 17.047 [16.884, 17.216] | +0.00% | 4.667 | 7.58 | 50 / 0.125 / 0.208 | 50 / 0.167 / 0.209 | 37.167 / 41.209 |
| Knotrel Workspace | 3 | 17.924 [17.433, 18.327] | +5.14% | 4.605 | 7.58 | 50 / 0.125 / 0.125 | 50 / 0.125 / 0.167 | 40.125 / 43.542 |
| External petgraph DFS | 3 | 167.665 [167.470, 168.356] | +883.52% | 18.896 | 7.58 | 50 / 0.083 / 0.334 | 50 / 0.542 / 0.625 | 383.542 / 436.500 |

## dense: redundant-bridge-churn-v1, N=128, queries=10, fresh

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 89/11.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.182 [0.182, 0.197] | +0.00% | 0.274 | 7.58 | 450 / 0.042 / 0.083 | 450 / 0.042 / 0.084 | 2.667 / 3.042 |
| Knotrel Workspace | 3 | 0.168 [0.155, 0.168] | -7.70% | 0.274 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.084 | 2.541 / 2.583 |
| External petgraph DFS | 3 | 1.063 [1.063, 1.067] | +484.74% | 0.394 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.125 / 0.167 | 19.709 / 21.000 |

## dense: redundant-bridge-churn-v1, N=128, queries=10, warmed

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 89/11.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.177 [0.176, 0.177] | +0.00% | 0.270 | 7.59 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.084 | 2.584 / 2.625 |
| Knotrel Workspace | 3 | 0.166 [0.165, 0.169] | -6.29% | 0.270 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.042 / 0.083 | 2.500 / 2.583 |
| External petgraph DFS | 3 | 1.047 [1.044, 1.056] | +491.43% | 0.375 | 7.66 | 450 / 0.042 / 0.042 | 450 / 0.125 / 0.167 | 19.208 / 20.000 |

## dense: redundant-bridge-churn-v1, N=128, queries=50, fresh

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 431/69.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.719 [0.716, 0.721] | +0.00% | 0.272 | 7.59 | 251 / 0.042 / 0.083 | 249 / 0.042 / 0.084 | 2.583 / 2.667 |
| Knotrel Workspace | 3 | 0.671 [0.665, 0.680] | -6.67% | 0.271 | 7.59 | 251 / 0.042 / 0.042 | 249 / 0.083 / 0.084 | 2.500 / 2.667 |
| External petgraph DFS | 3 | 4.944 [4.935, 5.193] | +587.20% | 0.395 | 7.59 | 251 / 0.042 / 0.042 | 249 / 0.167 / 0.208 | 19.417 / 20.500 |

## dense: redundant-bridge-churn-v1, N=128, queries=50, warmed

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 431/69.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.721 [0.715, 0.724] | +0.00% | 0.275 | 7.62 | 251 / 0.042 / 0.042 | 249 / 0.083 / 0.084 | 2.583 / 2.667 |
| Knotrel Workspace | 3 | 0.621 [0.618, 0.660] | -13.87% | 0.286 | 7.62 | 251 / 0.042 / 0.042 | 249 / 0.083 / 0.084 | 2.334 / 2.375 |
| External petgraph DFS | 3 | 4.949 [4.941, 5.125] | +586.36% | 0.379 | 7.62 | 251 / 0.042 / 0.042 | 249 / 0.167 / 0.208 | 19.541 / 20.542 |

## dense: redundant-bridge-churn-v1, N=128, queries=90, fresh

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 791/109.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.216 [1.205, 1.224] | +0.00% | 0.275 | 7.58 | 51 / 0.084 / 0.291 | 49 / 0.084 / 0.125 | 2.584 / 2.916 |
| Knotrel Workspace | 3 | 1.133 [1.065, 1.156] | -6.84% | 0.272 | 7.59 | 51 / 0.084 / 0.250 | 49 / 0.084 / 0.125 | 2.667 / 2.708 |
| External petgraph DFS | 3 | 8.913 [8.814, 9.147] | +632.86% | 0.393 | 7.58 | 51 / 0.042 / 0.083 | 49 / 0.167 / 0.167 | 19.375 / 20.458 |

## dense: redundant-bridge-churn-v1, N=128, queries=90, warmed

Initial edges: 4034; max degree: 64; density: 0.49630905511811024; true/false queries: 791/109.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.203 [1.127, 1.204] | +0.00% | 0.270 | 7.59 | 51 / 0.042 / 0.083 | 49 / 0.084 / 0.125 | 2.583 / 2.584 |
| Knotrel Workspace | 3 | 1.101 [1.030, 1.101] | -8.52% | 0.271 | 7.59 | 51 / 0.042 / 0.083 | 49 / 0.083 / 0.084 | 2.500 / 2.500 |
| External petgraph DFS | 3 | 8.969 [8.956, 9.028] | +645.33% | 0.382 | 7.58 | 51 / 0.042 / 0.208 | 49 / 0.167 / 0.209 | 19.459 / 20.541 |

## dense: redundant-bridge-churn-v1, N=512, queries=10, fresh

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 85/15.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.960 [1.953, 2.019] | +0.00% | 4.675 | 7.58 | 450 / 0.084 / 0.084 | 450 / 0.084 / 0.125 | 37.375 / 37.833 |
| Knotrel Workspace | 3 | 2.090 [2.086, 2.126] | +6.64% | 4.674 | 7.59 | 450 / 0.084 / 0.084 | 450 / 0.084 / 0.125 | 40.292 / 40.666 |
| External petgraph DFS | 3 | 20.218 [19.439, 20.709] | +931.52% | 19.355 | 7.59 | 450 / 0.042 / 0.042 | 450 / 0.542 / 0.542 | 422.667 / 459.167 |

## dense: redundant-bridge-churn-v1, N=512, queries=10, warmed

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 85/15.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.952 [1.846, 1.959] | +0.00% | 4.601 | 7.58 | 450 / 0.084 / 0.084 | 450 / 0.084 / 0.125 | 37.292 / 39.167 |
| Knotrel Workspace | 3 | 2.002 [1.939, 2.085] | +2.58% | 4.609 | 7.59 | 450 / 0.084 / 0.084 | 450 / 0.084 / 0.125 | 38.917 / 40.458 |
| External petgraph DFS | 3 | 18.548 [18.420, 18.967] | +850.24% | 19.357 | 7.58 | 450 / 0.042 / 0.042 | 450 / 0.500 / 0.542 | 385.125 / 413.916 |

## dense: redundant-bridge-churn-v1, N=512, queries=50, fresh

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 434/66.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 9.645 [9.477, 9.669] | +0.00% | 4.702 | 7.59 | 251 / 0.084 / 0.167 | 249 / 0.125 / 0.208 | 37.375 / 40.250 |
| Knotrel Workspace | 3 | 10.342 [10.328, 10.347] | +7.22% | 4.716 | 7.59 | 251 / 0.084 / 0.125 | 249 / 0.125 / 0.125 | 41.250 / 41.875 |
| External petgraph DFS | 3 | 99.674 [97.842, 101.395] | +933.39% | 19.177 | 7.62 | 251 / 0.042 / 0.167 | 249 / 0.583 / 0.625 | 413.584 / 454.250 |

## dense: redundant-bridge-churn-v1, N=512, queries=50, warmed

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 434/66.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 9.657 [9.617, 9.673] | +0.00% | 4.631 | 7.56 | 251 / 0.084 / 0.125 | 249 / 0.125 / 0.125 | 37.375 / 38.583 |
| Knotrel Workspace | 3 | 9.587 [9.486, 10.383] | -0.72% | 4.732 | 7.58 | 251 / 0.125 / 0.125 | 249 / 0.125 / 0.167 | 37.333 / 41.750 |
| External petgraph DFS | 3 | 97.360 [96.208, 101.672] | +908.20% | 18.856 | 7.62 | 251 / 0.042 / 0.084 | 249 / 0.542 / 0.625 | 401.000 / 430.459 |

## dense: redundant-bridge-churn-v1, N=512, queries=90, fresh

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 799/101.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 16.931 [16.878, 17.098] | +0.00% | 4.749 | 7.58 | 51 / 0.209 / 0.292 | 49 / 0.208 / 0.250 | 37.375 / 41.083 |
| Knotrel Workspace | 3 | 18.222 [18.210, 18.268] | +7.63% | 4.690 | 7.58 | 51 / 0.208 / 0.375 | 49 / 0.209 / 0.375 | 41.000 / 44.083 |
| External petgraph DFS | 3 | 172.961 [172.095, 174.496] | +921.58% | 19.285 | 7.59 | 51 / 0.125 / 0.208 | 49 / 0.583 / 0.958 | 401.584 / 429.584 |

## dense: redundant-bridge-churn-v1, N=512, queries=90, warmed

Initial edges: 65282; max degree: 256; density: 0.4990368150684932; true/false queries: 799/101.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 16.802 [16.635, 17.067] | +0.00% | 4.650 | 7.59 | 51 / 0.125 / 0.167 | 49 / 0.125 / 0.167 | 37.333 / 40.875 |
| Knotrel Workspace | 3 | 17.463 [16.962, 17.663] | +3.93% | 4.665 | 7.61 | 51 / 0.125 / 0.333 | 49 / 0.208 / 0.250 | 40.125 / 41.917 |
| External petgraph DFS | 3 | 174.941 [173.588, 175.501] | +941.17% | 18.933 | 7.58 | 51 / 0.084 / 0.500 | 49 / 0.583 / 0.667 | 407.292 / 441.792 |

## extreme: sustained-churn-blocks-v1, N=10000000, queries=50, fresh

Initial edges: 10624999; max degree: 3; density: 2.1250000125000011e-07; true/false queries: 15/485.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 1 | 533.862 [533.862, 533.862] | +0.00% | 2242.851 | 1697.81 | 500 / 10.959 / 19.334 | — | 4407.250 / 12649.041 |
| Knotrel Workspace | 1 | 415.580 [415.580, 415.580] | -22.16% | 2689.201 | 1394.16 | 500 / 1.875 / 2.167 | — | 2929.000 / 8245.708 |
| External petgraph DFS | 1 | 652.489 [652.489, 652.489] | +22.22% | 962.291 | 902.23 | 500 / 3.541 / 4.709 | — | 4424.959 / 13123.167 |

## extreme: sustained-churn-blocks-v1, N=10000000, queries=50, warmed

Initial edges: 10624999; max degree: 3; density: 2.1250000125000011e-07; true/false queries: 15/485.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 1 | 519.820 [519.820, 519.820] | +0.00% | 2273.739 | 1799.30 | 500 / 2.042 / 2.417 | — | 4306.583 / 10417.875 |
| Knotrel Workspace | 1 | 399.316 [399.316, 399.316] | -23.18% | 2400.367 | 1724.98 | 500 / 1.792 / 2.083 | — | 2893.208 / 8178.667 |
| External petgraph DFS | 1 | 648.399 [648.399, 648.399] | +24.74% | 867.649 | 1265.83 | 500 / 1.542 / 5.875 | — | 4420.417 / 13381.333 |

## extreme: sustained-churn-path-v1, N=10000000, queries=50, fresh

Initial edges: 9999999; max degree: 2; density: 2e-07; true/false queries: 8/492.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 1 | 585.446 [585.446, 585.446] | +0.00% | 2179.879 | 1260.58 | 500 / 14.208 / 124.875 | — | 4033.125 / 13195.833 |
| Knotrel Workspace | 1 | 591.763 [591.763, 591.763] | +1.08% | 2200.812 | 1223.50 | 500 / 22.958 / 302.916 | — | 3645.333 / 14108.542 |
| External petgraph DFS | 1 | 425.577 [425.577, 425.577] | -27.31% | 885.449 | 744.19 | 500 / 10.625 / 14.625 | — | 3099.542 / 9458.959 |

## extreme: sustained-churn-path-v1, N=10000000, queries=50, warmed

Initial edges: 9999999; max degree: 2; density: 2e-07; true/false queries: 8/492.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 1 | 488.079 [488.079, 488.079] | +0.00% | 2260.928 | 1671.72 | 500 / 3.083 / 5.833 | — | 4030.917 / 11494.792 |
| Knotrel Workspace | 1 | 413.173 [413.173, 413.173] | -15.35% | 2191.361 | 1567.22 | 500 / 1.667 / 2.125 | — | 3382.834 / 10464.625 |
| External petgraph DFS | 1 | 368.334 [368.334, 368.334] | -24.53% | 785.789 | 1142.30 | 500 / 7.584 / 10.916 | — | 3162.291 / 7881.583 |

## cogentco: topology-zoo-outages-v1, N=197, queries=None, fresh

Initial edges: 243; max degree: 9; density: 0.012586760592561898; true/false queries: 732/1068.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 1.028 [1.003, 1.134] | +0.00% | 0.051 | 7.58 | 99 / 0.125 / 0.250 | 99 / 0.125 / 0.167 | 1.584 / 2.041 |
| Knotrel Workspace | 3 | 0.701 [0.686, 0.726] | -31.82% | 0.055 | 7.58 | 99 / 0.125 / 0.167 | 99 / 0.167 / 0.208 | 1.250 / 1.708 |
| External petgraph DFS | 3 | 0.704 [0.665, 0.738] | -31.50% | 0.029 | 7.58 | 99 / 0.125 / 0.208 | 99 / 0.084 / 0.084 | 1.042 / 1.333 |

## cogentco: topology-zoo-outages-v1, N=197, queries=None, warmed

Initial edges: 243; max degree: 9; density: 0.012586760592561898; true/false queries: 732/1068.

| Engine | Trials | Replay ms [min,max] | Delta | Setup ms | RSS MiB | Cut count / p95 µs / p99 µs | Link count / p95 µs / p99 µs | Query p95 / p99 µs |
|---|---:|---|---:|---:|---:|---|---|---|
| Knotrel Compact | 3 | 0.903 [0.893, 0.910] | +0.00% | 0.032 | 7.56 | 99 / 0.084 / 0.084 | 99 / 0.125 / 0.125 | 1.334 / 1.750 |
| Knotrel Workspace | 3 | 0.548 [0.543, 0.585] | -39.30% | 0.034 | 7.56 | 99 / 0.084 / 0.125 | 99 / 0.125 / 0.125 | 0.917 / 1.292 |
| External petgraph DFS | 3 | 0.631 [0.604, 0.642] | -30.13% | 0.014 | 7.58 | 99 / 0.084 / 0.084 | 99 / 0.083 / 0.084 | 0.917 / 1.125 |

