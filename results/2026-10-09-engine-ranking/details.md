# Per-cell detailed results — 2026-10-09

All values are medians across three independent processes. p95/p99 columns are medians of each process percentile, not pooled percentiles. Δ Compact = `100*(runtime/Compact - 1)`; Δ petgraph = `100*(runtime/petgraph - 1)`. Above best = `100*(runtime/best - 1)`. Runtimes and setups are in milliseconds, operations in microseconds, and RSS in MiB. Missing values are shown as —.

## cogentco / topology-zoo-outages-v1 / N=197 / q=import / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `42529c7c67c5077b`.

Operations: cut 99, link 99, query 1800 (732 true / 1068 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.081 [1.070, 1.106] | +0.0% | +52.0% | +217.7% | 0.053 | 11.6 | 0.125 / 0.250 | 0.167 / 0.167 | 1.708 / 2.208 |
| Workspace (opt-in) | 0.734 [0.731, 0.803] | -32.1% | +3.3% | +115.8% | 0.052 | 11.7 | 0.125 / 0.250 | 0.167 / 0.167 | 1.333 / 1.792 |
| ETT (experimental) | 0.340 [0.340, 0.341] | -68.5% | -52.1% | +0.0% | 0.177 | 11.8 | 2.416 / 3.334 | 1.167 / 1.333 | 0.084 / 0.125 |
| HDT (experimental) | 0.479 [0.471, 0.480] | -55.7% | -32.6% | +40.9% | 0.155 | 11.7 | 10.042 / 19.916 | 0.917 / 1.083 | 0.125 / 0.125 |
| petgraph (external) | 0.711 [0.710, 0.711] | -34.2% | +0.0% | +109.0% | 0.030 | 11.7 | 0.125 / 0.166 | 0.084 / 0.084 | 1.042 / 1.333 |

## cogentco / topology-zoo-outages-v1 / N=197 / q=import / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `42529c7c67c5077b`.

Operations: cut 99, link 99, query 1800 (732 true / 1068 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.904 [0.895, 0.915] | +0.0% | +39.5% | +191.9% | 0.035 | 11.6 | 0.084 / 0.125 | 0.125 / 0.125 | 1.333 / 1.667 |
| Workspace (opt-in) | 0.587 [0.586, 0.620] | -35.1% | -9.4% | +89.5% | 0.035 | 11.7 | 0.084 / 0.166 | 0.125 / 0.167 | 1.000 / 1.375 |
| ETT (experimental) | 0.310 [0.301, 0.349] | -65.7% | -52.2% | +0.0% | 0.149 | 11.6 | 2.458 / 3.166 | 1.125 / 1.250 | 0.084 / 0.125 |
| HDT (experimental) | 0.413 [0.412, 0.417] | -54.4% | -36.3% | +33.2% | 0.117 | 11.7 | 8.666 / 17.084 | 0.792 / 1.834 | 0.084 / 0.125 |
| petgraph (external) | 0.648 [0.646, 0.684] | -28.3% | +0.0% | +109.3% | 0.016 | 11.7 | 0.084 / 0.125 | 0.084 / 0.084 | 0.959 / 1.166 |

## dense / dense-bridge-churn-v1 / N=128 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `32193df9152bed0e`.

Operations: cut 450, link 450, query 100 (79 true / 21 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.176 [0.176, 0.177] | +0.0% | -80.3% | +13.7% | 0.279 | 11.7 | 0.042 / 0.042 | 0.042 / 0.042 | 2.667 / 3.542 |
| Workspace (opt-in) | 0.155 [0.154, 0.157] | -12.1% | -82.7% | +0.0% | 0.278 | 11.7 | 0.042 / 0.042 | 0.042 / 0.042 | 2.375 / 2.500 |
| ETT (experimental) | 14.010 [13.926, 14.097] | +7841.2% | +1466.2% | +8931.2% | 0.833 | 11.7 | 30.625 / 35.000 | 0.459 / 0.500 | 0.125 / 0.125 |
| HDT (experimental) | 0.788 [0.785, 0.806] | +346.5% | -11.9% | +407.8% | 0.803 | 11.8 | 0.500 / 0.584 | 0.333 / 0.375 | 0.125 / 0.167 |
| petgraph (external) | 0.894 [0.888, 0.899] | +407.0% | +0.0% | +476.6% | 0.394 | 11.7 | 0.042 / 0.042 | 0.125 / 0.125 | 17.917 / 20.583 |

## dense / dense-bridge-churn-v1 / N=128 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `32193df9152bed0e`.

Operations: cut 450, link 450, query 100 (79 true / 21 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.173 [0.170, 0.175] | +0.0% | -80.8% | +12.3% | 0.280 | 11.7 | 0.042 / 0.042 | 0.042 / 0.042 | 2.584 / 2.667 |
| Workspace (opt-in) | 0.154 [0.152, 0.176] | -11.0% | -82.9% | +0.0% | 0.282 | 11.6 | 0.042 / 0.042 | 0.042 / 0.042 | 2.334 / 2.500 |
| ETT (experimental) | 13.953 [13.866, 14.325] | +7955.6% | +1445.4% | +8948.1% | 0.818 | 11.7 | 30.625 / 30.750 | 0.459 / 0.500 | 0.125 / 0.125 |
| HDT (experimental) | 0.801 [0.797, 0.804] | +362.5% | -11.3% | +419.5% | 0.788 | 11.8 | 0.541 / 0.542 | 0.334 / 0.375 | 0.125 / 0.125 |
| petgraph (external) | 0.903 [0.887, 1.091] | +421.3% | +0.0% | +485.5% | 0.376 | 11.7 | 0.042 / 0.042 | 0.125 / 0.166 | 18.209 / 20.708 |

## dense / dense-bridge-churn-v1 / N=128 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `5c6a1202fe78f155`.

Operations: cut 250, link 250, query 500 (379 true / 121 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.721 [0.720, 0.921] | +0.0% | -84.2% | +13.9% | 0.279 | 11.7 | 0.042 / 0.042 | 0.042 / 0.042 | 2.583 / 2.625 |
| Workspace (opt-in) | 0.633 [0.632, 0.636] | -12.2% | -86.2% | +0.0% | 0.286 | 11.6 | 0.042 / 0.042 | 0.042 / 0.083 | 2.334 / 2.375 |
| ETT (experimental) | 7.876 [7.849, 8.244] | +992.1% | +72.1% | +1143.9% | 0.847 | 11.7 | 31.041 / 37.125 | 0.500 / 0.541 | 0.125 / 0.125 |
| HDT (experimental) | 0.673 [0.658, 0.714] | -6.6% | -85.3% | +6.4% | 0.817 | 11.7 | 0.583 / 0.667 | 0.334 / 0.375 | 0.125 / 0.125 |
| petgraph (external) | 4.577 [4.554, 4.581] | +534.6% | +0.0% | +622.8% | 0.396 | 11.7 | 0.042 / 0.042 | 0.167 / 0.167 | 19.584 / 20.500 |

## dense / dense-bridge-churn-v1 / N=128 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `5c6a1202fe78f155`.

Operations: cut 250, link 250, query 500 (379 true / 121 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.728 [0.721, 0.732] | +0.0% | -84.1% | +15.5% | 0.279 | 11.7 | 0.042 / 0.083 | 0.042 / 0.084 | 2.584 / 2.667 |
| Workspace (opt-in) | 0.630 [0.624, 0.634] | -13.4% | -86.2% | +0.0% | 0.278 | 11.7 | 0.042 / 0.042 | 0.042 / 0.083 | 2.334 / 2.375 |
| ETT (experimental) | 7.902 [7.845, 17.252] | +985.4% | +72.6% | +1153.5% | 0.831 | 11.7 | 31.250 / 32.750 | 0.500 / 0.542 | 0.084 / 0.125 |
| HDT (experimental) | 0.674 [0.666, 0.677] | -7.5% | -85.3% | +6.8% | 0.784 | 11.7 | 0.542 / 0.542 | 0.334 / 0.334 | 0.084 / 0.125 |
| petgraph (external) | 4.577 [4.575, 4.625] | +528.7% | +0.0% | +626.1% | 0.374 | 11.7 | 0.042 / 0.042 | 0.167 / 0.167 | 19.625 / 20.625 |

## dense / dense-bridge-churn-v1 / N=128 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `10e7f17d851f5dd3`.

Operations: cut 50, link 50, query 900 (687 true / 213 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.203 [1.199, 1.210] | +0.0% | -86.6% | +127.1% | 0.278 | 11.6 | 0.042 / 0.292 | 0.042 / 0.084 | 2.542 / 2.625 |
| Workspace (opt-in) | 1.091 [1.071, 1.196] | -9.3% | -87.8% | +105.9% | 0.290 | 11.6 | 0.042 / 0.333 | 0.083 / 0.125 | 2.417 / 2.459 |
| ETT (experimental) | 1.647 [1.632, 1.665] | +36.9% | -81.6% | +210.8% | 0.832 | 11.7 | 31.584 / 44.625 | 0.500 / 0.750 | 0.084 / 0.125 |
| HDT (experimental) | 0.530 [0.526, 0.534] | -56.0% | -94.1% | +0.0% | 0.809 | 11.8 | 0.584 / 410.208 | 0.334 / 0.875 | 0.084 / 0.125 |
| petgraph (external) | 8.964 [8.102, 11.716] | +645.0% | +0.0% | +1591.7% | 0.409 | 12.2 | 0.292 / 0.625 | 0.209 / 0.708 | 20.458 / 31.875 |

## dense / dense-bridge-churn-v1 / N=128 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `10e7f17d851f5dd3`.

Operations: cut 50, link 50, query 900 (687 true / 213 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.243 [1.199, 1.267] | +0.0% | -84.7% | +134.3% | 0.279 | 11.7 | 0.042 / 0.083 | 0.084 / 0.125 | 2.667 / 2.708 |
| Workspace (opt-in) | 1.044 [1.028, 1.083] | -16.0% | -87.2% | +96.8% | 0.280 | 11.7 | 0.042 / 0.042 | 0.042 / 0.084 | 2.334 / 2.375 |
| ETT (experimental) | 1.616 [1.599, 1.631] | +30.0% | -80.2% | +204.6% | 0.821 | 11.7 | 30.250 / 33.333 | 0.500 / 0.583 | 0.084 / 0.125 |
| HDT (experimental) | 0.530 [0.529, 0.535] | -57.3% | -93.5% | +0.0% | 0.781 | 11.7 | 0.583 / 417.666 | 0.334 / 0.542 | 0.084 / 0.084 |
| petgraph (external) | 8.147 [8.141, 8.191] | +555.6% | +0.0% | +1436.0% | 0.377 | 11.7 | 0.042 / 0.042 | 0.167 / 0.208 | 18.958 / 20.459 |

## dense / dense-bridge-churn-v1 / N=512 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Compact (default)**. Fingerprint: `9e6ef6a952b08411`.

Operations: cut 450, link 450, query 100 (77 true / 23 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.952 [1.951, 2.131] | +0.0% | -89.6% | +0.0% | 4.708 | 11.7 | 0.083 / 0.084 | 0.084 / 0.084 | 37.334 / 38.834 |
| Workspace (opt-in) | 1.954 [1.948, 1.956] | +0.1% | -89.6% | +0.1% | 4.633 | 11.8 | 0.083 / 0.084 | 0.084 / 0.084 | 37.542 / 37.917 |
| ETT (experimental) | 304.134 [298.195, 306.910] | +15477.3% | +1515.2% | +15477.3% | 14.445 | 12.1 | 698.041 / 969.291 | 0.875 / 1.583 | 1.000 / 1.375 |
| HDT (experimental) | 8.514 [8.438, 8.572] | +336.1% | -54.8% | +336.1% | 14.348 | 13.7 | 0.667 / 0.708 | 0.417 / 0.458 | 0.167 / 0.209 |
| petgraph (external) | 18.829 [18.285, 19.316] | +864.4% | +0.0% | +864.4% | 20.474 | 11.7 | 0.042 / 0.084 | 0.541 / 0.666 | 395.916 / 426.500 |

## dense / dense-bridge-churn-v1 / N=512 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Compact (default)**. Fingerprint: `9e6ef6a952b08411`.

Operations: cut 450, link 450, query 100 (77 true / 23 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.968 [1.944, 1.968] | +0.0% | -88.6% | +0.0% | 4.682 | 11.7 | 0.083 / 0.084 | 0.084 / 0.125 | 38.083 / 40.000 |
| Workspace (opt-in) | 1.994 [1.963, 2.235] | +1.3% | -88.5% | +1.3% | 4.710 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 40.458 / 42.625 |
| ETT (experimental) | 305.336 [304.087, 307.208] | +15416.3% | +1662.2% | +15416.3% | 13.942 | 12.2 | 700.041 / 860.833 | 0.875 / 1.917 | 0.916 / 1.125 |
| HDT (experimental) | 8.007 [8.001, 12.091] | +306.9% | -53.8% | +306.9% | 13.679 | 13.8 | 0.667 / 0.750 | 0.417 / 0.500 | 0.167 / 0.167 |
| petgraph (external) | 17.327 [17.206, 20.066] | +780.5% | +0.0% | +780.5% | 20.344 | 11.7 | 0.042 / 0.042 | 0.500 / 0.583 | 360.542 / 390.333 |

## dense / dense-bridge-churn-v1 / N=512 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `395736583f2619ca`.

Operations: cut 250, link 250, query 500 (369 true / 131 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 9.636 [9.619, 10.042] | +0.0% | -91.3% | +15.5% | 4.663 | 11.7 | 0.084 / 0.167 | 0.125 / 0.125 | 37.250 / 39.417 |
| Workspace (opt-in) | 9.658 [9.651, 12.041] | +0.2% | -91.3% | +15.8% | 4.628 | 11.7 | 0.084 / 0.125 | 0.125 / 0.125 | 37.625 / 41.000 |
| ETT (experimental) | 165.616 [165.484, 170.280] | +1618.6% | +49.4% | +1885.6% | 14.502 | 12.1 | 684.708 / 725.375 | 0.791 / 1.250 | 0.292 / 0.583 |
| HDT (experimental) | 8.341 [8.219, 9.348] | -13.4% | -92.5% | +0.0% | 14.330 | 13.7 | 0.667 / 0.750 | 0.417 / 0.500 | 0.125 / 0.167 |
| petgraph (external) | 110.872 [95.054, 123.224] | +1050.5% | +0.0% | +1229.2% | 20.542 | 11.7 | 0.208 / 0.834 | 0.667 / 1.542 | 439.834 / 613.333 |

## dense / dense-bridge-churn-v1 / N=512 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `395736583f2619ca`.

Operations: cut 250, link 250, query 500 (369 true / 131 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 9.613 [9.612, 9.630] | +0.0% | -90.2% | +20.2% | 4.622 | 11.7 | 0.084 / 0.084 | 0.125 / 0.125 | 37.208 / 37.500 |
| Workspace (opt-in) | 9.619 [9.522, 9.629] | +0.1% | -90.2% | +20.3% | 4.690 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 37.459 / 37.667 |
| ETT (experimental) | 172.534 [166.720, 201.301] | +1694.8% | +75.2% | +2057.9% | 13.808 | 12.2 | 715.625 / 856.041 | 1.000 / 2.584 | 0.500 / 0.667 |
| HDT (experimental) | 7.996 [7.892, 8.461] | -16.8% | -91.9% | +0.0% | 13.793 | 13.9 | 0.667 / 0.833 | 0.417 / 0.459 | 0.125 / 0.167 |
| petgraph (external) | 98.506 [95.584, 103.414] | +924.7% | +0.0% | +1132.0% | 20.343 | 11.7 | 0.042 / 0.042 | 0.542 / 0.584 | 402.959 / 459.584 |

## dense / dense-bridge-churn-v1 / N=512 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `a9d909ec7676fff9`.

Operations: cut 50, link 50, query 900 (667 true / 233 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 17.260 [17.203, 27.419] | +0.0% | -90.7% | +110.2% | 4.750 | 11.6 | 0.125 / 0.333 | 0.167 / 0.209 | 37.292 / 40.208 |
| Workspace (opt-in) | 17.255 [17.234, 18.465] | -0.0% | -90.7% | +110.1% | 4.627 | 11.8 | 0.125 / 0.292 | 0.125 / 0.208 | 37.500 / 39.875 |
| ETT (experimental) | 33.271 [32.242, 33.528] | +92.8% | -82.0% | +305.1% | 14.414 | 12.1 | 670.500 / 772.000 | 0.709 / 1.208 | 0.125 / 0.167 |
| HDT (experimental) | 8.213 [8.083, 10.289] | -52.4% | -95.6% | +0.0% | 14.191 | 13.7 | 0.750 / 8067.875 | 0.417 / 1.250 | 0.125 / 0.166 |
| petgraph (external) | 185.091 [168.624, 191.896] | +972.4% | +0.0% | +2153.6% | 20.375 | 11.7 | 0.375 / 3.041 | 0.916 / 1.209 | 422.458 / 495.583 |

## dense / dense-bridge-churn-v1 / N=512 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `a9d909ec7676fff9`.

Operations: cut 50, link 50, query 900 (667 true / 233 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 17.243 [17.185, 18.064] | +0.0% | -89.9% | +123.9% | 4.635 | 11.7 | 0.125 / 0.292 | 0.167 / 0.375 | 37.625 / 40.208 |
| Workspace (opt-in) | 16.996 [16.974, 17.202] | -1.4% | -90.0% | +120.7% | 4.631 | 11.7 | 0.125 / 0.125 | 0.125 / 0.166 | 37.000 / 40.208 |
| ETT (experimental) | 33.359 [32.122, 34.440] | +93.5% | -80.4% | +333.1% | 13.991 | 12.2 | 671.541 / 731.917 | 0.709 / 0.958 | 0.125 / 0.167 |
| HDT (experimental) | 7.701 [7.669, 8.210] | -55.3% | -95.5% | +0.0% | 13.713 | 13.8 | 0.750 / 7557.917 | 0.500 / 1.042 | 0.125 / 0.125 |
| petgraph (external) | 170.243 [167.798, 174.756] | +887.3% | +0.0% | +2110.5% | 20.278 | 11.7 | 0.042 / 0.333 | 0.542 / 0.625 | 386.750 / 431.583 |

## dense / redundant-bridge-churn-v1 / N=128 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `dd724154676b1772`.

Operations: cut 450, link 450, query 100 (89 true / 11 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.182 [0.182, 0.184] | +0.0% | -82.6% | +12.7% | 0.277 | 11.7 | 0.042 / 0.042 | 0.042 / 0.083 | 2.666 / 3.375 |
| Workspace (opt-in) | 0.162 [0.161, 0.164] | -11.3% | -84.6% | +0.0% | 0.277 | 11.8 | 0.042 / 0.042 | 0.042 / 0.084 | 2.375 / 2.500 |
| ETT (experimental) | 9.478 [9.133, 9.848] | +5100.7% | +805.8% | +5762.9% | 0.835 | 11.7 | 33.625 / 44.584 | 0.625 / 0.792 | 0.167 / 0.250 |
| HDT (experimental) | 0.777 [0.766, 0.780] | +326.5% | -25.7% | +380.8% | 0.802 | 11.8 | 1.042 / 1.084 | 0.541 / 0.542 | 0.125 / 0.167 |
| petgraph (external) | 1.046 [1.044, 1.061] | +474.2% | +0.0% | +547.3% | 0.395 | 11.7 | 0.042 / 0.042 | 0.125 / 0.167 | 19.208 / 20.125 |

## dense / redundant-bridge-churn-v1 / N=128 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `dd724154676b1772`.

Operations: cut 450, link 450, query 100 (89 true / 11 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.178 [0.177, 0.178] | +0.0% | -83.6% | +11.1% | 0.278 | 11.7 | 0.042 / 0.042 | 0.042 / 0.084 | 2.584 / 2.667 |
| Workspace (opt-in) | 0.160 [0.159, 0.166] | -10.0% | -85.3% | +0.0% | 0.281 | 11.7 | 0.042 / 0.042 | 0.042 / 0.084 | 2.375 / 2.417 |
| ETT (experimental) | 9.361 [9.023, 9.808] | +5170.3% | +762.3% | +5756.9% | 0.800 | 11.7 | 32.541 / 47.167 | 0.667 / 0.709 | 0.166 / 0.167 |
| HDT (experimental) | 0.778 [0.771, 1.673] | +338.0% | -28.3% | +386.8% | 0.789 | 11.7 | 1.041 / 1.042 | 0.541 / 0.542 | 0.084 / 0.125 |
| petgraph (external) | 1.086 [1.041, 1.094] | +511.2% | +0.0% | +579.2% | 0.374 | 11.7 | 0.042 / 0.042 | 0.125 / 0.166 | 19.584 / 20.875 |

## dense / redundant-bridge-churn-v1 / N=128 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `9e272d8635152beb`.

Operations: cut 251, link 249, query 500 (431 true / 69 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.720 [0.720, 0.735] | +0.0% | -85.5% | +14.3% | 0.279 | 11.7 | 0.042 / 0.042 | 0.042 / 0.084 | 2.583 / 2.667 |
| Workspace (opt-in) | 0.630 [0.629, 0.632] | -12.5% | -87.3% | +0.0% | 0.276 | 11.7 | 0.042 / 0.042 | 0.083 / 0.084 | 2.334 / 2.416 |
| ETT (experimental) | 5.382 [5.363, 5.391] | +647.1% | +8.6% | +753.9% | 0.846 | 11.7 | 32.250 / 35.625 | 0.667 / 0.709 | 0.125 / 0.125 |
| HDT (experimental) | 0.662 [0.662, 0.663] | -8.1% | -86.6% | +5.1% | 0.803 | 11.8 | 1.042 / 1.208 | 0.500 / 0.542 | 0.084 / 0.125 |
| petgraph (external) | 4.958 [4.916, 4.966] | +588.2% | +0.0% | +686.7% | 0.397 | 11.7 | 0.042 / 0.042 | 0.166 / 0.167 | 19.500 / 20.459 |

## dense / redundant-bridge-churn-v1 / N=128 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `9e272d8635152beb`.

Operations: cut 251, link 249, query 500 (431 true / 69 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.722 [0.719, 0.727] | +0.0% | -85.5% | +15.8% | 0.280 | 11.7 | 0.042 / 0.083 | 0.083 / 0.084 | 2.583 / 2.625 |
| Workspace (opt-in) | 0.624 [0.623, 0.639] | -13.7% | -87.5% | +0.0% | 0.282 | 11.7 | 0.042 / 0.042 | 0.083 / 0.084 | 2.334 / 2.375 |
| ETT (experimental) | 5.271 [5.258, 5.389] | +629.7% | +6.1% | +745.3% | 0.815 | 11.8 | 31.667 / 33.750 | 0.667 / 0.667 | 0.084 / 0.125 |
| HDT (experimental) | 0.663 [0.661, 0.666] | -8.2% | -86.7% | +6.4% | 0.790 | 11.8 | 1.000 / 1.084 | 0.500 / 0.542 | 0.084 / 0.084 |
| petgraph (external) | 4.968 [4.945, 5.069] | +587.9% | +0.0% | +696.9% | 0.377 | 11.7 | 0.042 / 0.042 | 0.166 / 0.167 | 19.541 / 20.583 |

## dense / redundant-bridge-churn-v1 / N=128 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `8a9d2267e1e32d39`.

Operations: cut 51, link 49, query 900 (791 true / 109 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.204 [1.203, 1.206] | +0.0% | -86.5% | +127.7% | 0.275 | 11.7 | 0.083 / 0.208 | 0.084 / 0.125 | 2.542 / 2.625 |
| Workspace (opt-in) | 1.051 [1.050, 1.116] | -12.7% | -88.2% | +98.7% | 0.281 | 11.7 | 0.083 / 0.292 | 0.083 / 0.125 | 2.375 / 2.417 |
| ETT (experimental) | 1.101 [1.087, 1.135] | -8.5% | -87.7% | +108.3% | 0.837 | 11.7 | 34.708 / 44.792 | 0.708 / 0.833 | 0.084 / 0.125 |
| HDT (experimental) | 0.529 [0.527, 0.529] | -56.1% | -94.1% | +0.0% | 0.808 | 11.8 | 1.625 / 406.792 | 0.625 / 0.959 | 0.084 / 0.125 |
| petgraph (external) | 8.930 [8.924, 9.288] | +641.9% | +0.0% | +1589.1% | 0.405 | 11.7 | 0.083 / 0.125 | 0.167 / 0.167 | 19.459 / 20.375 |

## dense / redundant-bridge-churn-v1 / N=128 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `8a9d2267e1e32d39`.

Operations: cut 51, link 49, query 900 (791 true / 109 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.221 [1.206, 1.224] | +0.0% | -86.4% | +129.1% | 0.278 | 11.6 | 0.042 / 0.084 | 0.084 / 0.125 | 2.583 / 2.667 |
| Workspace (opt-in) | 1.093 [1.031, 1.279] | -10.5% | -87.8% | +105.1% | 0.280 | 11.7 | 0.042 / 0.208 | 0.083 / 0.084 | 2.417 / 2.709 |
| ETT (experimental) | 1.066 [1.055, 1.084] | -12.7% | -88.1% | +100.0% | 0.814 | 11.7 | 31.334 / 31.583 | 0.666 / 0.708 | 0.084 / 0.125 |
| HDT (experimental) | 0.533 [0.531, 0.537] | -56.4% | -94.0% | +0.0% | 0.786 | 11.7 | 1.125 / 419.792 | 0.542 / 0.584 | 0.084 / 0.084 |
| petgraph (external) | 8.953 [8.938, 8.978] | +633.3% | +0.0% | +1580.1% | 0.377 | 11.7 | 0.042 / 0.042 | 0.167 / 0.167 | 19.459 / 20.417 |

## dense / redundant-bridge-churn-v1 / N=512 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Compact (default)**. Fingerprint: `c47db0e54795605a`.

Operations: cut 450, link 450, query 100 (85 true / 15 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.960 [1.953, 1.964] | +0.0% | -90.2% | +0.0% | 4.696 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 37.417 / 38.625 |
| Workspace (opt-in) | 1.976 [1.960, 2.090] | +0.9% | -90.1% | +0.9% | 4.706 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 38.125 / 39.875 |
| ETT (experimental) | 191.562 [191.258, 238.384] | +9676.1% | +861.2% | +9676.1% | 14.494 | 12.1 | 677.750 / 694.500 | 0.958 / 1.125 | 0.709 / 1.083 |
| HDT (experimental) | 8.580 [8.463, 8.633] | +337.9% | -56.9% | +337.9% | 14.321 | 13.7 | 1.334 / 1.417 | 0.666 / 0.667 | 0.167 / 0.209 |
| petgraph (external) | 19.930 [19.127, 29.671] | +917.1% | +0.0% | +917.1% | 20.786 | 11.6 | 0.042 / 0.084 | 0.542 / 0.625 | 399.000 / 430.917 |

## dense / redundant-bridge-churn-v1 / N=512 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `c47db0e54795605a`.

Operations: cut 450, link 450, query 100 (85 true / 15 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.967 [1.962, 2.051] | +0.0% | -90.0% | +1.6% | 4.639 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 37.583 / 40.375 |
| Workspace (opt-in) | 1.937 [1.928, 1.939] | -1.5% | -90.1% | +0.0% | 4.637 | 11.7 | 0.084 / 0.084 | 0.084 / 0.125 | 37.125 / 39.709 |
| ETT (experimental) | 191.407 [190.606, 192.067] | +9629.3% | +873.6% | +9781.4% | 13.803 | 12.2 | 676.792 / 684.833 | 0.958 / 0.959 | 0.167 / 0.208 |
| HDT (experimental) | 8.120 [8.053, 8.713] | +312.7% | -58.7% | +319.2% | 13.678 | 13.8 | 1.375 / 1.458 | 0.666 / 0.709 | 0.167 / 0.250 |
| petgraph (external) | 19.660 [19.131, 20.954] | +899.3% | +0.0% | +915.0% | 20.338 | 11.7 | 0.042 / 0.042 | 0.542 / 0.583 | 400.959 / 430.250 |

## dense / redundant-bridge-churn-v1 / N=512 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `d707059d04b0de28`.

Operations: cut 251, link 249, query 500 (434 true / 66 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 9.659 [9.622, 10.628] | +0.0% | -90.3% | +14.1% | 4.793 | 11.7 | 0.084 / 0.167 | 0.125 / 0.166 | 37.375 / 41.792 |
| Workspace (opt-in) | 9.698 [9.655, 17.397] | +0.4% | -90.3% | +14.6% | 4.689 | 11.6 | 0.084 / 0.125 | 0.084 / 0.166 | 37.708 / 40.916 |
| ETT (experimental) | 109.668 [109.353, 111.399] | +1035.4% | +9.8% | +1195.9% | 14.394 | 12.1 | 676.167 / 707.042 | 0.958 / 1.125 | 0.167 / 0.209 |
| HDT (experimental) | 8.463 [8.296, 8.710] | -12.4% | -91.5% | +0.0% | 14.321 | 13.7 | 1.334 / 1.542 | 0.666 / 0.708 | 0.125 / 0.209 |
| petgraph (external) | 99.873 [99.302, 106.896] | +934.0% | +0.0% | +1080.1% | 20.349 | 11.7 | 0.042 / 0.125 | 0.542 / 0.625 | 406.375 / 432.083 |

## dense / redundant-bridge-churn-v1 / N=512 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `d707059d04b0de28`.

Operations: cut 251, link 249, query 500 (434 true / 66 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 9.635 [9.621, 10.694] | +0.0% | -90.3% | +22.0% | 4.602 | 11.7 | 0.084 / 0.125 | 0.125 / 0.125 | 37.375 / 37.583 |
| Workspace (opt-in) | 10.415 [10.031, 10.645] | +8.1% | -89.5% | +31.9% | 4.829 | 11.6 | 0.125 / 0.500 | 0.167 / 0.375 | 40.875 / 72.250 |
| ETT (experimental) | 110.334 [109.366, 110.698] | +1045.1% | +10.8% | +1297.5% | 14.031 | 12.2 | 681.792 / 690.958 | 0.958 / 1.000 | 0.167 / 0.208 |
| HDT (experimental) | 7.895 [7.830, 8.000] | -18.1% | -92.1% | +0.0% | 13.635 | 13.8 | 1.375 / 1.584 | 0.666 / 0.708 | 0.125 / 0.125 |
| petgraph (external) | 99.546 [99.309, 108.743] | +933.1% | +0.0% | +1160.9% | 20.286 | 11.8 | 0.042 / 0.084 | 0.542 / 0.584 | 409.208 / 429.708 |

## dense / redundant-bridge-churn-v1 / N=512 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `5d614f64ff1f8734`.

Operations: cut 51, link 49, query 900 (799 true / 101 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 17.045 [16.999, 17.181] | +0.0% | -91.0% | +107.6% | 4.697 | 11.7 | 0.167 / 0.292 | 0.166 / 0.209 | 37.292 / 39.125 |
| Workspace (opt-in) | 17.142 [17.089, 17.414] | +0.6% | -90.9% | +108.8% | 4.763 | 11.6 | 0.167 / 0.208 | 0.166 / 0.250 | 37.750 / 40.500 |
| ETT (experimental) | 21.477 [20.930, 21.751] | +26.0% | -88.6% | +161.6% | 14.583 | 12.1 | 705.000 / 780.875 | 1.000 / 1.208 | 0.167 / 0.167 |
| HDT (experimental) | 8.209 [8.114, 8.216] | -51.8% | -95.6% | +0.0% | 14.244 | 13.7 | 1.917 / 8057.833 | 0.708 / 1.000 | 0.125 / 0.125 |
| petgraph (external) | 188.494 [175.107, 190.755] | +1005.9% | +0.0% | +2196.1% | 20.776 | 11.7 | 0.125 / 0.375 | 0.625 / 0.792 | 430.333 / 475.125 |

## dense / redundant-bridge-churn-v1 / N=512 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `5d614f64ff1f8734`.

Operations: cut 51, link 49, query 900 (799 true / 101 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 17.026 [17.016, 17.386] | +0.0% | -90.6% | +120.0% | 4.631 | 11.7 | 0.125 / 0.125 | 0.167 / 0.167 | 37.333 / 38.208 |
| Workspace (opt-in) | 16.999 [16.817, 17.020] | -0.2% | -90.6% | +119.6% | 4.623 | 11.7 | 0.125 / 0.125 | 0.167 / 0.167 | 37.542 / 37.792 |
| ETT (experimental) | 21.126 [21.022, 21.127] | +24.1% | -88.3% | +172.9% | 13.934 | 12.2 | 685.875 / 727.291 | 0.958 / 1.125 | 0.125 / 0.167 |
| HDT (experimental) | 7.740 [7.716, 8.247] | -54.5% | -95.7% | +0.0% | 14.004 | 13.8 | 1.875 / 7592.625 | 0.708 / 0.917 | 0.125 / 0.125 |
| petgraph (external) | 180.622 [175.548, 262.532] | +960.9% | +0.0% | +2233.5% | 20.379 | 11.7 | 0.459 / 0.584 | 0.792 / 0.916 | 421.375 / 485.375 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `320eed6cfa5efb0f`.

Operations: cut 484, link 416, query 100 (6 true / 94 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.178 [0.178, 0.182] | +0.0% | +61.8% | +61.8% | 0.179 | 11.7 | 0.125 / 0.125 | 0.167 / 0.208 | 1.750 / 2.709 |
| Workspace (opt-in) | 0.148 [0.148, 0.155] | -16.8% | +34.7% | +34.7% | 0.179 | 11.7 | 0.125 / 0.125 | 0.167 / 0.208 | 0.792 / 1.166 |
| ETT (experimental) | 0.942 [0.932, 0.985] | +429.3% | +756.7% | +756.7% | 0.958 | 11.7 | 2.125 / 3.208 | 1.291 / 1.375 | 0.167 / 0.208 |
| HDT (experimental) | 2.926 [2.912, 2.929] | +1544.4% | +2561.3% | +2561.3% | 0.714 | 11.8 | 13.083 / 77.750 | 1.000 / 1.125 | 0.208 / 0.250 |
| petgraph (external) | 0.110 [0.110, 0.111] | -38.2% | +0.0% | +0.0% | 0.079 | 11.8 | 0.084 / 0.125 | 0.084 / 0.084 | 0.666 / 1.042 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `320eed6cfa5efb0f`.

Operations: cut 484, link 416, query 100 (6 true / 94 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.136 [0.136, 0.141] | +0.0% | +50.8% | +50.8% | 0.170 | 11.7 | 0.084 / 0.084 | 0.125 / 0.166 | 0.959 / 1.458 |
| Workspace (opt-in) | 0.113 [0.112, 0.113] | -17.0% | +25.1% | +25.1% | 0.170 | 11.7 | 0.084 / 0.084 | 0.125 / 0.125 | 0.625 / 0.875 |
| ETT (experimental) | 0.839 [0.837, 0.840] | +517.1% | +830.3% | +830.3% | 0.884 | 11.8 | 1.875 / 2.375 | 1.125 / 1.250 | 0.167 / 0.167 |
| HDT (experimental) | 2.734 [2.730, 2.744] | +1910.4% | +2931.0% | +2931.0% | 0.660 | 11.7 | 11.250 / 74.958 | 0.875 / 1.000 | 0.167 / 0.209 |
| petgraph (external) | 0.090 [0.090, 0.090] | -33.7% | +0.0% | +0.0% | 0.063 | 11.7 | 0.084 / 0.084 | 0.083 / 0.084 | 0.625 / 0.958 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `9415351e77d1989e`.

Operations: cut 281, link 219, query 500 (46 true / 454 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.427 [0.423, 0.437] | +0.0% | +68.2% | +68.2% | 0.181 | 11.7 | 0.125 / 0.166 | 0.167 / 0.208 | 1.416 / 3.375 |
| Workspace (opt-in) | 0.292 [0.290, 0.296] | -31.7% | +14.8% | +14.8% | 0.187 | 11.7 | 0.125 / 0.167 | 0.167 / 0.208 | 1.000 / 1.458 |
| ETT (experimental) | 0.638 [0.636, 0.643] | +49.4% | +151.2% | +151.2% | 0.935 | 11.7 | 2.291 / 3.166 | 1.334 / 1.459 | 0.167 / 0.167 |
| HDT (experimental) | 2.294 [2.289, 2.294] | +437.2% | +803.3% | +803.3% | 0.719 | 11.7 | 23.750 / 93.042 | 1.042 / 1.125 | 0.167 / 0.209 |
| petgraph (external) | 0.254 [0.254, 0.274] | -40.5% | +0.0% | +0.0% | 0.078 | 11.6 | 0.084 / 0.125 | 0.084 / 0.084 | 0.834 / 1.667 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `9415351e77d1989e`.

Operations: cut 281, link 219, query 500 (46 true / 454 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.356 [0.354, 0.361] | +0.0% | +52.0% | +52.0% | 0.172 | 11.7 | 0.084 / 0.084 | 0.125 / 0.167 | 1.208 / 1.584 |
| Workspace (opt-in) | 0.238 [0.238, 0.242] | -33.0% | +1.8% | +1.8% | 0.169 | 11.7 | 0.084 / 0.125 | 0.125 / 0.167 | 0.833 / 1.208 |
| ETT (experimental) | 0.575 [0.574, 0.578] | +61.4% | +145.3% | +145.3% | 0.894 | 11.8 | 2.083 / 3.000 | 1.208 / 1.292 | 0.166 / 0.167 |
| HDT (experimental) | 2.159 [2.139, 5.165] | +506.4% | +821.5% | +821.5% | 0.682 | 11.7 | 23.166 / 88.292 | 0.958 / 1.042 | 0.167 / 0.208 |
| petgraph (external) | 0.234 [0.230, 0.237] | -34.2% | +0.0% | +0.0% | 0.064 | 11.6 | 0.084 / 0.084 | 0.083 / 0.084 | 0.792 / 1.667 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `0ad790a6f3499ba1`.

Operations: cut 76, link 24, query 900 (110 true / 790 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.712 [0.702, 0.716] | +0.0% | +32.9% | +166.5% | 0.180 | 11.7 | 0.125 / 0.209 | 0.208 / 0.250 | 1.542 / 2.459 |
| Workspace (opt-in) | 0.458 [0.455, 0.459] | -35.7% | -14.5% | +71.5% | 0.180 | 11.8 | 0.125 / 0.292 | 0.167 / 0.167 | 1.125 / 1.667 |
| ETT (experimental) | 0.267 [0.266, 0.271] | -62.5% | -50.1% | +0.0% | 0.931 | 11.7 | 2.917 / 4.750 | 1.375 / 1.500 | 0.166 / 0.167 |
| HDT (experimental) | 1.554 [1.540, 1.571] | +118.3% | +190.1% | +481.8% | 0.719 | 11.7 | 57.833 / 259.750 | 1.083 / 1.083 | 0.167 / 0.208 |
| petgraph (external) | 0.536 [0.525, 0.674] | -24.8% | +0.0% | +100.5% | 0.083 | 11.7 | 0.125 / 0.209 | 0.084 / 0.084 | 1.458 / 2.583 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `0ad790a6f3499ba1`.

Operations: cut 76, link 24, query 900 (110 true / 790 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.615 [0.607, 0.629] | +0.0% | -4.6% | +164.6% | 0.168 | 11.7 | 0.125 / 0.125 | 0.166 / 0.166 | 1.333 / 2.000 |
| Workspace (opt-in) | 0.398 [0.398, 0.410] | -35.3% | -38.3% | +71.2% | 0.168 | 11.7 | 0.125 / 0.167 | 0.167 / 0.167 | 0.959 / 1.541 |
| ETT (experimental) | 0.233 [0.232, 0.234] | -62.2% | -63.9% | +0.0% | 0.893 | 11.7 | 2.375 / 3.458 | 1.250 / 1.291 | 0.125 / 0.167 |
| HDT (experimental) | 1.446 [1.446, 1.470] | +135.0% | +124.2% | +521.7% | 0.665 | 11.7 | 54.875 / 241.833 | 1.000 / 1.042 | 0.167 / 0.167 |
| petgraph (external) | 0.645 [0.510, 0.737] | +4.8% | +0.0% | +177.3% | 0.063 | 11.7 | 0.084 / 0.125 | 0.084 / 0.084 | 1.875 / 3.375 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `33274370397b138c`.

Operations: cut 677, link 223, query 100 (1 true / 99 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.295 [0.294, 0.296] | +0.0% | +43.7% | +43.7% | 1.786 | 11.8 | 0.125 / 0.167 | 0.209 / 0.250 | 4.208 / 8.708 |
| Workspace (opt-in) | 0.243 [0.228, 0.248] | -17.8% | +18.1% | +18.1% | 1.754 | 11.7 | 0.125 / 0.167 | 0.250 / 0.250 | 2.500 / 4.833 |
| ETT (experimental) | 1.412 [1.405, 1.418] | +378.3% | +587.2% | +587.2% | 13.297 | 11.6 | 3.041 / 5.750 | 1.542 / 1.667 | 0.333 / 0.458 |
| HDT (experimental) | 25.780 [25.693, 25.830] | +8635.2% | +12450.0% | +12450.0% | 8.925 | 23.9 | 114.625 / 493.166 | 1.333 / 1.500 | 0.584 / 0.667 |
| petgraph (external) | 0.205 [0.204, 0.215] | -30.4% | +0.0% | +0.0% | 0.668 | 11.7 | 0.125 / 0.166 | 0.125 / 0.125 | 2.666 / 6.458 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `33274370397b138c`.

Operations: cut 677, link 223, query 100 (1 true / 99 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.262 [0.256, 0.289] | +0.0% | +27.7% | +27.7% | 1.754 | 11.7 | 0.125 / 0.167 | 0.209 / 0.250 | 2.792 / 5.375 |
| Workspace (opt-in) | 0.221 [0.219, 0.224] | -15.8% | +7.5% | +7.5% | 1.741 | 11.7 | 0.125 / 0.166 | 0.209 / 0.250 | 2.166 / 4.041 |
| ETT (experimental) | 1.451 [1.371, 1.638] | +453.9% | +607.3% | +607.3% | 12.832 | 11.7 | 3.000 / 6.708 | 1.542 / 1.709 | 0.333 / 0.375 |
| HDT (experimental) | 26.279 [25.262, 26.428] | +9931.9% | +12711.4% | +12711.4% | 8.594 | 26.6 | 114.333 / 478.917 | 1.625 / 1.792 | 0.958 / 1.084 |
| petgraph (external) | 0.205 [0.200, 0.206] | -21.7% | +0.0% | +0.0% | 0.638 | 11.7 | 0.125 / 0.125 | 0.125 / 0.125 | 2.750 / 6.417 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `812d06e6d029beeb`.

Operations: cut 426, link 74, query 500 (21 true / 479 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.971 [0.971, 1.038] | +0.0% | +9.9% | +33.0% | 1.787 | 11.7 | 0.166 / 0.167 | 0.250 / 0.250 | 3.541 / 15.750 |
| Workspace (opt-in) | 0.730 [0.729, 0.743] | -24.8% | -17.3% | +0.0% | 1.762 | 11.8 | 0.166 / 0.208 | 0.250 / 0.250 | 2.833 / 15.500 |
| ETT (experimental) | 1.038 [1.036, 1.079] | +6.9% | +17.6% | +42.1% | 12.637 | 11.7 | 3.584 / 7.125 | 1.542 / 1.625 | 0.292 / 0.417 |
| HDT (experimental) | 24.361 [24.006, 55.993] | +2409.2% | +2658.7% | +3236.0% | 8.961 | 23.9 | 178.709 / 806.541 | 1.667 / 1.917 | 0.583 / 0.750 |
| petgraph (external) | 0.883 [0.881, 0.898] | -9.0% | +0.0% | +20.9% | 0.670 | 11.8 | 0.125 / 0.167 | 0.125 / 0.125 | 3.916 / 15.375 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `812d06e6d029beeb`.

Operations: cut 426, link 74, query 500 (21 true / 479 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.879 [0.824, 1.152] | +0.0% | -0.8% | +32.2% | 1.742 | 11.7 | 0.125 / 0.125 | 0.209 / 0.250 | 3.083 / 9.459 |
| Workspace (opt-in) | 0.665 [0.662, 0.693] | -24.4% | -25.0% | +0.0% | 1.736 | 11.8 | 0.125 / 0.167 | 0.209 / 0.250 | 2.542 / 12.041 |
| ETT (experimental) | 0.964 [0.955, 0.983] | +9.7% | +8.8% | +45.1% | 12.365 | 11.6 | 3.292 / 7.000 | 1.500 / 1.541 | 0.250 / 0.292 |
| HDT (experimental) | 23.360 [23.288, 23.487] | +2558.4% | +2535.9% | +3415.1% | 8.505 | 25.9 | 173.792 / 791.000 | 1.375 / 1.500 | 0.458 / 0.542 |
| petgraph (external) | 0.886 [0.877, 1.075] | +0.9% | +0.0% | +33.4% | 0.641 | 11.7 | 0.125 / 0.166 | 0.125 / 0.167 | 3.875 / 15.625 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 2.973 [2.956, 3.020] | +0.0% | -25.0% | +447.8% | 1.769 | 11.8 | 0.167 / 0.333 | 0.250 / 0.250 | 8.500 / 12.500 |
| Workspace (opt-in) | 2.431 [2.429, 2.501] | -18.2% | -38.7% | +347.9% | 1.799 | 11.7 | 0.167 / 0.375 | 0.250 / 0.250 | 7.708 / 11.458 |
| ETT (experimental) | 0.543 [0.540, 0.551] | -81.7% | -86.3% | +0.0% | 12.666 | 11.7 | 7.125 / 21.084 | 1.542 / 1.542 | 0.334 / 0.417 |
| HDT (experimental) | 17.408 [15.650, 20.757] | +485.5% | +339.2% | +3107.1% | 9.037 | 18.9 | 675.333 / 2628.750 | 2.708 / 2.708 | 1.083 / 1.542 |
| petgraph (external) | 3.963 [3.915, 4.984] | +33.3% | +0.0% | +630.1% | 0.667 | 11.7 | 0.125 / 0.250 | 0.125 / 0.125 | 13.083 / 19.416 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 2.893 [2.787, 2.900] | +0.0% | -41.8% | +493.4% | 1.741 | 11.7 | 0.167 / 0.209 | 0.209 / 0.209 | 8.375 / 12.083 |
| Workspace (opt-in) | 2.381 [2.372, 2.580] | -17.7% | -52.1% | +388.5% | 1.743 | 11.7 | 0.167 / 0.167 | 0.250 / 0.250 | 7.625 / 12.250 |
| ETT (experimental) | 0.487 [0.471, 0.604] | -83.1% | -90.2% | +0.0% | 12.465 | 11.7 | 6.334 / 17.584 | 1.500 / 1.500 | 0.292 / 0.334 |
| HDT (experimental) | 16.881 [16.068, 23.133] | +483.5% | +239.9% | +3363.0% | 8.794 | 20.6 | 847.084 / 2553.792 | 4.792 / 4.792 | 0.958 / 2.000 |
| petgraph (external) | 4.967 [3.952, 4.986] | +71.7% | +0.0% | +918.9% | 0.620 | 11.7 | 0.125 / 0.166 | 0.125 / 0.125 | 15.500 / 23.000 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `89e71664442094ae`.

Operations: cut 865, link 35, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.933 [0.928, 1.210] | +0.0% | -9.4% | +14.2% | 19.505 | 16.8 | 0.375 / 0.500 | 0.292 / 0.292 | 18.292 / 51.125 |
| Workspace (opt-in) | 0.817 [0.777, 0.843] | -12.4% | -20.7% | +0.0% | 19.846 | 16.7 | 0.417 / 0.542 | 0.292 / 0.292 | 15.250 / 49.083 |
| ETT (experimental) | 4.888 [4.658, 4.917] | +424.2% | +375.0% | +498.6% | 214.183 | 49.4 | 11.542 / 44.792 | 2.250 / 2.459 | 1.417 / 1.708 |
| HDT (experimental) | 288.695 [287.543, 303.652] | +30857.9% | +27951.3% | +35255.8% | 133.493 | 234.9 | 1005.250 / 4318.375 | 4.583 / 4.959 | 2.791 / 4.792 |
| petgraph (external) | 1.029 [0.990, 1.262] | +10.4% | +0.0% | +26.0% | 7.636 | 14.1 | 0.292 / 0.375 | 0.209 / 0.209 | 22.375 / 73.792 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `89e71664442094ae`.

Operations: cut 865, link 35, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.834 [0.832, 0.844] | +0.0% | -16.7% | +9.4% | 18.778 | 16.8 | 0.250 / 0.292 | 0.292 / 0.292 | 16.833 / 47.875 |
| Workspace (opt-in) | 0.762 [0.723, 1.028] | -8.6% | -23.9% | +0.0% | 18.959 | 16.7 | 0.333 / 0.458 | 0.292 / 0.292 | 14.958 / 47.625 |
| ETT (experimental) | 4.906 [4.847, 4.985] | +488.3% | +389.9% | +543.5% | 215.946 | 67.8 | 11.917 / 43.000 | 2.292 / 2.541 | 1.292 / 1.583 |
| HDT (experimental) | 292.090 [287.416, 308.020] | +34929.8% | +29068.9% | +38213.2% | 154.334 | 235.0 | 1103.250 / 4247.042 | 5.000 / 5.583 | 6.500 / 10.375 |
| petgraph (external) | 1.001 [0.995, 1.004] | +20.1% | +0.0% | +31.3% | 7.079 | 14.1 | 0.167 / 0.250 | 0.167 / 0.167 | 23.708 / 77.083 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `1bc5729376b7dc79`.

Operations: cut 490, link 10, query 500 (20 true / 480 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.181 [5.177, 5.452] | +0.0% | -31.9% | +8.2% | 19.447 | 16.8 | 0.375 / 0.500 | 0.375 / 0.375 | 33.750 / 91.292 |
| Workspace (opt-in) | 4.789 [4.557, 5.978] | -7.6% | -37.1% | +0.0% | 20.007 | 16.7 | 0.500 / 0.708 | 0.542 / 0.542 | 33.834 / 101.000 |
| ETT (experimental) | 4.846 [4.828, 5.306] | -6.5% | -36.3% | +1.2% | 219.039 | 49.3 | 25.125 / 132.125 | 2.500 / 2.500 | 1.292 / 1.917 |
| HDT (experimental) | 318.876 [304.541, 330.757] | +6054.6% | +4091.7% | +6559.1% | 134.073 | 231.1 | 2486.500 / 11088.666 | 8.583 / 8.583 | 4.708 / 7.834 |
| petgraph (external) | 7.607 [7.395, 10.072] | +46.8% | +0.0% | +58.9% | 8.217 | 14.1 | 0.417 / 0.583 | 0.208 / 0.208 | 59.084 / 155.083 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `1bc5729376b7dc79`.

Operations: cut 490, link 10, query 500 (20 true / 480 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.059 [5.029, 5.293] | +0.0% | -30.8% | +14.6% | 18.861 | 16.9 | 0.333 / 0.500 | 0.292 / 0.292 | 33.291 / 89.958 |
| Workspace (opt-in) | 4.413 [4.379, 4.449] | -12.8% | -39.6% | +0.0% | 18.776 | 16.8 | 0.209 / 0.250 | 0.292 / 0.292 | 32.125 / 93.875 |
| ETT (experimental) | 5.699 [4.717, 5.909] | +12.6% | -22.0% | +29.1% | 218.762 | 67.8 | 30.750 / 152.917 | 2.667 / 2.667 | 1.791 / 2.375 |
| HDT (experimental) | 296.152 [292.617, 351.472] | +5754.0% | +3952.4% | +6611.0% | 134.016 | 240.5 | 2257.500 / 10527.708 | 5.500 / 5.500 | 3.084 / 4.000 |
| petgraph (external) | 7.308 [7.300, 7.488] | +44.5% | +0.0% | +65.6% | 7.054 | 14.1 | 0.208 / 0.250 | 0.209 / 0.209 | 53.459 / 157.375 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `912b25a39d1308b7`.

Operations: cut 100, link 0, query 900 (121 true / 779 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 24.420 [24.415, 25.705] | +0.0% | -38.5% | +474.1% | 19.479 | 16.8 | 0.583 / 0.708 | — / — | 60.167 / 173.542 |
| Workspace (opt-in) | 24.109 [23.992, 24.222] | -1.3% | -39.3% | +466.8% | 19.504 | 16.6 | 0.541 / 0.584 | — / — | 60.791 / 182.167 |
| ETT (experimental) | 4.253 [3.436, 9.614] | -82.6% | -89.3% | +0.0% | 217.104 | 49.3 | 71.125 / 410.041 | — / — | 2.458 / 3.542 |
| HDT (experimental) | 209.898 [200.698, 211.769] | +759.5% | +428.3% | +4834.9% | 171.824 | 170.1 | 9035.417 / 20683.958 | — / — | 3.333 / 5.292 |
| petgraph (external) | 39.729 [39.432, 39.819] | +62.7% | +0.0% | +834.1% | 7.744 | 14.1 | 0.458 / 0.708 | — / — | 101.792 / 292.750 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `912b25a39d1308b7`.

Operations: cut 100, link 0, query 900 (121 true / 779 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 24.177 [24.149, 27.396] | +0.0% | -39.0% | +713.7% | 18.793 | 16.8 | 0.500 / 0.584 | — / — | 59.625 / 171.834 |
| Workspace (opt-in) | 24.588 [23.837, 30.891] | +1.7% | -37.9% | +727.6% | 20.957 | 16.8 | 0.542 / 0.625 | — / — | 63.292 / 183.500 |
| ETT (experimental) | 2.971 [2.914, 3.061] | -87.7% | -92.5% | +0.0% | 217.801 | 67.7 | 61.541 / 364.958 | — / — | 1.209 / 1.458 |
| HDT (experimental) | 199.606 [192.825, 203.784] | +725.6% | +403.8% | +6618.3% | 133.049 | 183.1 | 8837.084 / 18951.583 | — / — | 3.666 / 5.666 |
| petgraph (external) | 39.616 [39.508, 56.452] | +63.9% | +0.0% | +1233.4% | 7.092 | 14.1 | 0.333 / 0.708 | — / — | 102.500 / 289.958 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `14a90b222d96b94d`.

Operations: cut 896, link 4, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.504 [5.452, 5.526] | +0.0% | -25.1% | +11.1% | 218.594 | 133.6 | 0.833 / 0.958 | 0.542 / 0.542 | 148.792 / 260.959 |
| Workspace (opt-in) | 4.954 [4.914, 4.971] | -10.0% | -32.6% | +0.0% | 211.630 | 137.0 | 0.791 / 0.917 | 0.417 / 0.417 | 133.792 / 363.334 |
| ETT (experimental) | 51.761 [51.481, 51.957] | +840.4% | +604.7% | +944.8% | 3303.909 | 395.4 | 166.667 / 822.334 | 5.042 / 5.042 | 3.166 / 3.583 |
| HDT (experimental) | 4800.475 [4776.657, 4897.819] | +87111.3% | +65255.2% | +96800.2% | 1950.554 | 1622.1 | 14475.292 / 64721.625 | 26.791 / 26.791 | 64.042 / 99.125 |
| petgraph (external) | 7.345 [7.211, 8.181] | +33.4% | +0.0% | +48.3% | 87.874 | 109.6 | 0.667 / 0.792 | 0.333 / 0.333 | 221.709 / 406.792 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `14a90b222d96b94d`.

Operations: cut 896, link 4, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.254 [5.185, 5.303] | +0.0% | -48.3% | +10.0% | 207.750 | 156.2 | 0.792 / 0.917 | 0.375 / 0.375 | 139.541 / 248.000 |
| Workspace (opt-in) | 4.778 [4.748, 5.170] | -9.1% | -53.0% | +0.0% | 209.202 | 159.9 | 0.791 / 0.916 | 0.459 / 0.459 | 133.958 / 310.000 |
| ETT (experimental) | 54.417 [50.421, 173.713] | +935.8% | +435.9% | +1039.0% | 3262.662 | 572.4 | 176.708 / 886.917 | 5.250 / 5.250 | 3.458 / 3.709 |
| HDT (experimental) | 4663.543 [4407.389, 4720.331] | +88668.1% | +45827.0% | +97513.8% | 1899.942 | 1812.8 | 13145.042 / 58310.000 | 17.500 / 17.500 | 41.125 / 93.750 |
| petgraph (external) | 10.154 [10.054, 10.329] | +93.3% | +0.0% | +112.5% | 80.493 | 125.6 | 3.875 / 6.334 | 0.750 / 0.750 | 326.041 / 602.500 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `e4985759f0c1baed`.

Operations: cut 499, link 1, query 500 (18 true / 482 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 43.519 [43.025, 52.507] | +0.0% | -36.3% | +2.6% | 216.496 | 138.1 | 1.042 / 1.167 | 0.792 / 0.792 | 320.041 / 577.917 |
| Workspace (opt-in) | 42.424 [41.866, 43.654] | -2.5% | -37.9% | +0.0% | 217.222 | 140.9 | 0.958 / 1.125 | 0.583 / 0.583 | 340.125 / 672.500 |
| ETT (experimental) | 55.060 [54.394, 59.404] | +26.5% | -19.4% | +29.8% | 3289.840 | 395.4 | 346.125 / 2558.334 | 7.000 / 7.000 | 3.334 / 5.083 |
| HDT (experimental) | 4862.337 [4724.688, 4879.395] | +11072.9% | +7018.9% | +11361.3% | 1992.918 | 1565.6 | 26756.167 / 167666.125 | 8.916 / 8.916 | 54.542 / 196.417 |
| petgraph (external) | 68.302 [67.309, 71.012] | +56.9% | +0.0% | +61.0% | 83.370 | 109.6 | 0.833 / 1.041 | 0.541 / 0.541 | 564.917 / 923.667 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `e4985759f0c1baed`.

Operations: cut 499, link 1, query 500 (18 true / 482 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 43.043 [42.756, 47.315] | +0.0% | -41.2% | +4.1% | 207.538 | 161.0 | 0.958 / 1.250 | 0.792 / 0.792 | 319.208 / 525.875 |
| Workspace (opt-in) | 41.331 [41.244, 105.348] | -4.0% | -43.5% | +0.0% | 209.594 | 163.8 | 0.958 / 1.125 | 0.666 / 0.666 | 342.042 / 552.834 |
| ETT (experimental) | 56.822 [54.455, 64.413] | +32.0% | -22.3% | +37.5% | 3143.839 | 603.9 | 351.209 / 2416.083 | 6.292 / 6.292 | 3.333 / 4.250 |
| HDT (experimental) | 4247.300 [4228.089, 4267.305] | +9767.5% | +5704.4% | +10176.3% | 1996.397 | 1810.8 | 23771.292 / 164251.417 | 8.417 / 8.417 | 17.667 / 48.625 |
| petgraph (external) | 73.174 [69.805, 75.649] | +70.0% | +0.0% | +77.0% | 80.502 | 125.7 | 4.792 / 6.708 | 0.375 / 0.375 | 581.292 / 920.875 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `2e8e9275071c8a32`.

Operations: cut 100, link 0, query 900 (125 true / 775 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 241.072 [239.321, 247.433] | +0.0% | -42.4% | +564.5% | 217.069 | 138.0 | 1.250 / 1.916 | — / — | 847.000 / 1083.083 |
| Workspace (opt-in) | 244.491 [244.141, 248.047] | +1.4% | -41.6% | +573.9% | 210.831 | 140.8 | 1.042 / 1.209 | — / — | 860.208 / 1096.041 |
| ETT (experimental) | 36.280 [35.317, 38.803] | -85.0% | -91.3% | +0.0% | 3140.537 | 395.4 | 1387.583 / 3508.166 | — / — | 2.792 / 3.500 |
| HDT (experimental) | 3443.326 [3368.865, 3486.570] | +1328.3% | +722.8% | +9391.0% | 2074.732 | 1307.6 | 118464.667 / 414747.042 | — / — | 16.541 / 31.250 |
| petgraph (external) | 418.498 [415.205, 423.563] | +73.6% | +0.0% | +1053.5% | 82.336 | 109.6 | 1.291 / 2.041 | — / — | 1466.458 / 1873.000 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `2e8e9275071c8a32`.

Operations: cut 100, link 0, query 900 (125 true / 775 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 239.377 [239.131, 240.323] | +0.0% | -43.8% | +537.3% | 208.133 | 163.3 | 1.125 / 1.375 | — / — | 844.083 / 1097.750 |
| Workspace (opt-in) | 252.416 [245.104, 431.798] | +5.4% | -40.8% | +572.0% | 216.589 | 163.8 | 1.541 / 2.083 | — / — | 891.167 / 1164.916 |
| ETT (experimental) | 37.562 [36.346, 38.816] | -84.3% | -91.2% | +0.0% | 3199.950 | 604.6 | 1297.000 / 3690.500 | — / — | 3.209 / 4.875 |
| HDT (experimental) | 3643.521 [3304.543, 4871.411] | +1422.1% | +755.0% | +9600.0% | 1958.435 | 1305.7 | 112342.833 / 406776.250 | — / — | 28.000 / 137.958 |
| petgraph (external) | 426.152 [415.811, 438.027] | +78.0% | +0.0% | +1034.5% | 82.703 | 125.6 | 7.209 / 9.667 | — / — | 1490.625 / 1931.167 |

## sparse / sustained-churn-path-v1 / N=1024 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `be2f4110f26fdb62`.

Operations: cut 667, link 233, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.142 [0.134, 0.142] | +0.0% | +54.5% | +54.5% | 0.178 | 11.7 | 0.125 / 0.125 | 0.167 / 0.209 | 1.333 / 1.542 |
| Workspace (opt-in) | 0.119 [0.119, 0.123] | -15.8% | +30.0% | +30.0% | 0.170 | 11.7 | 0.084 / 0.125 | 0.167 / 0.209 | 0.375 / 0.833 |
| ETT (experimental) | 0.508 [0.472, 0.517] | +258.8% | +454.4% | +454.4% | 0.905 | 11.7 | 0.792 / 0.959 | 0.875 / 1.000 | 0.167 / 0.209 |
| HDT (experimental) | 0.522 [0.512, 0.588] | +268.3% | +469.0% | +469.0% | 0.729 | 11.7 | 0.875 / 1.083 | 0.709 / 0.833 | 0.167 / 0.209 |
| petgraph (external) | 0.092 [0.091, 0.092] | -35.3% | +0.0% | +0.0% | 0.072 | 11.7 | 0.084 / 0.125 | 0.084 / 0.084 | 0.334 / 0.708 |

## sparse / sustained-churn-path-v1 / N=1024 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `be2f4110f26fdb62`.

Operations: cut 667, link 233, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.107 [0.106, 0.108] | +0.0% | +45.7% | +45.7% | 0.159 | 11.7 | 0.084 / 0.084 | 0.125 / 0.167 | 0.541 / 0.750 |
| Workspace (opt-in) | 0.107 [0.097, 0.163] | -0.5% | +45.0% | +45.0% | 0.176 | 11.7 | 0.084 / 0.125 | 0.125 / 0.167 | 0.458 / 0.750 |
| ETT (experimental) | 0.465 [0.461, 0.467] | +332.9% | +530.8% | +530.8% | 0.877 | 11.7 | 0.750 / 0.916 | 0.750 / 0.875 | 0.167 / 0.167 |
| HDT (experimental) | 0.449 [0.448, 1.215] | +318.1% | +509.2% | +509.2% | 0.652 | 11.7 | 0.750 / 1.000 | 0.584 / 0.708 | 0.167 / 0.208 |
| petgraph (external) | 0.074 [0.073, 0.074] | -31.4% | +0.0% | +0.0% | 0.058 | 11.8 | 0.084 / 0.084 | 0.084 / 0.084 | 0.292 / 0.458 |

## sparse / sustained-churn-path-v1 / N=1024 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `fff476c9490b49fe`.

Operations: cut 418, link 82, query 500 (12 true / 488 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.217 [0.214, 0.217] | +0.0% | +70.5% | +70.5% | 0.171 | 11.7 | 0.084 / 0.125 | 0.209 / 0.250 | 0.625 / 2.416 |
| Workspace (opt-in) | 0.147 [0.146, 0.151] | -32.0% | +15.9% | +15.9% | 0.176 | 11.7 | 0.084 / 0.125 | 0.208 / 0.209 | 0.334 / 0.667 |
| ETT (experimental) | 0.370 [0.369, 0.375] | +70.8% | +191.3% | +191.3% | 0.904 | 11.7 | 0.875 / 1.083 | 0.959 / 1.167 | 0.166 / 0.167 |
| HDT (experimental) | 0.368 [0.367, 0.379] | +69.5% | +189.0% | +189.0% | 0.690 | 11.8 | 0.875 / 1.208 | 0.792 / 0.958 | 0.167 / 0.167 |
| petgraph (external) | 0.127 [0.126, 0.127] | -41.3% | +0.0% | +0.0% | 0.070 | 11.7 | 0.084 / 0.125 | 0.084 / 0.125 | 0.375 / 0.584 |

## sparse / sustained-churn-path-v1 / N=1024 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `fff476c9490b49fe`.

Operations: cut 418, link 82, query 500 (12 true / 488 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.187 [0.187, 0.189] | +0.0% | +55.3% | +55.3% | 0.156 | 11.7 | 0.084 / 0.084 | 0.125 / 0.167 | 0.542 / 0.958 |
| Workspace (opt-in) | 0.129 [0.129, 0.130] | -30.7% | +7.6% | +7.6% | 0.157 | 11.7 | 0.084 / 0.084 | 0.125 / 0.167 | 0.334 / 0.625 |
| ETT (experimental) | 0.336 [0.328, 0.337] | +80.0% | +179.6% | +179.6% | 0.875 | 11.7 | 0.833 / 1.000 | 0.833 / 0.917 | 0.125 / 0.167 |
| HDT (experimental) | 0.330 [0.329, 0.363] | +76.4% | +174.0% | +174.0% | 0.644 | 11.7 | 0.792 / 1.041 | 0.666 / 0.791 | 0.125 / 0.167 |
| petgraph (external) | 0.120 [0.120, 0.184] | -35.6% | +0.0% | +0.0% | 0.070 | 11.7 | 0.084 / 0.084 | 0.084 / 0.084 | 0.375 / 0.708 |

## sparse / sustained-churn-path-v1 / N=1024 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `168ee7a337647010`.

Operations: cut 94, link 6, query 900 (56 true / 844 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.502 [0.496, 0.523] | +0.0% | +64.8% | +154.8% | 0.173 | 11.7 | 0.125 / 0.250 | 0.250 / 0.250 | 1.125 / 3.042 |
| Workspace (opt-in) | 0.318 [0.318, 0.320] | -36.6% | +4.5% | +61.6% | 0.171 | 11.7 | 0.125 / 0.209 | 0.250 / 0.250 | 0.792 / 1.791 |
| ETT (experimental) | 0.197 [0.197, 0.198] | -60.8% | -35.3% | +0.0% | 0.903 | 11.8 | 1.083 / 3.042 | 1.250 / 1.250 | 0.166 / 0.167 |
| HDT (experimental) | 0.203 [0.202, 0.203] | -59.6% | -33.4% | +3.0% | 0.702 | 11.7 | 1.167 / 2.458 | 1.084 / 1.084 | 0.166 / 0.167 |
| petgraph (external) | 0.305 [0.304, 0.305] | -39.3% | +0.0% | +54.6% | 0.070 | 11.7 | 0.084 / 0.208 | 0.125 / 0.125 | 0.917 / 1.750 |

## sparse / sustained-churn-path-v1 / N=1024 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `168ee7a337647010`.

Operations: cut 94, link 6, query 900 (56 true / 844 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.481 [0.472, 0.507] | +0.0% | +45.6% | +178.1% | 0.154 | 11.7 | 0.084 / 0.084 | 0.167 / 0.167 | 1.083 / 2.250 |
| Workspace (opt-in) | 0.305 [0.305, 0.321] | -36.4% | -7.4% | +76.8% | 0.155 | 11.8 | 0.084 / 0.125 | 0.167 / 0.167 | 0.750 / 1.792 |
| ETT (experimental) | 0.173 [0.172, 0.192] | -64.0% | -47.6% | +0.0% | 0.879 | 11.6 | 1.000 / 1.209 | 1.125 / 1.125 | 0.125 / 0.167 |
| HDT (experimental) | 0.177 [0.177, 0.203] | -63.1% | -46.2% | +2.7% | 0.645 | 11.7 | 1.000 / 1.250 | 0.917 / 0.917 | 0.125 / 0.167 |
| petgraph (external) | 0.330 [0.291, 0.363] | -31.3% | +0.0% | +91.0% | 0.057 | 11.7 | 0.084 / 0.125 | 0.083 / 0.083 | 1.083 / 2.208 |

## sparse / sustained-churn-path-v1 / N=10000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `dd6f131aa10291a2`.

Operations: cut 862, link 38, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.213 [0.212, 0.217] | +0.0% | +43.9% | +43.9% | 1.663 | 11.7 | 0.125 / 0.166 | 0.250 / 0.250 | 2.959 / 7.125 |
| Workspace (opt-in) | 0.173 [0.172, 0.175] | -18.9% | +16.7% | +16.7% | 1.672 | 11.7 | 0.125 / 0.167 | 0.250 / 0.250 | 1.167 / 3.959 |
| ETT (experimental) | 0.795 [0.767, 2.308] | +273.0% | +436.6% | +436.6% | 12.357 | 11.7 | 1.208 / 1.500 | 1.291 / 1.333 | 0.375 / 0.584 |
| HDT (experimental) | 0.832 [0.801, 0.901] | +290.1% | +461.2% | +461.2% | 8.693 | 11.7 | 1.334 / 2.000 | 1.084 / 1.125 | 0.625 / 0.875 |
| petgraph (external) | 0.148 [0.148, 0.149] | -30.5% | +0.0% | +0.0% | 0.629 | 11.8 | 0.125 / 0.125 | 0.125 / 0.125 | 1.291 / 3.125 |

## sparse / sustained-churn-path-v1 / N=10000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `dd6f131aa10291a2`.

Operations: cut 862, link 38, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.199 [0.196, 0.217] | +0.0% | +42.3% | +42.3% | 1.693 | 11.8 | 0.125 / 0.167 | 0.250 / 0.250 | 1.625 / 5.083 |
| Workspace (opt-in) | 0.164 [0.163, 0.166] | -17.7% | +17.1% | +17.1% | 1.647 | 11.7 | 0.125 / 0.125 | 0.250 / 0.250 | 1.125 / 3.917 |
| ETT (experimental) | 0.747 [0.732, 1.001] | +276.1% | +435.2% | +435.2% | 12.278 | 11.7 | 1.125 / 1.417 | 1.292 / 1.334 | 0.292 / 0.417 |
| HDT (experimental) | 0.766 [0.747, 0.778] | +285.4% | +448.5% | +448.5% | 8.278 | 11.8 | 1.125 / 1.375 | 0.917 / 1.000 | 0.333 / 0.375 |
| petgraph (external) | 0.140 [0.139, 0.141] | -29.7% | +0.0% | +0.0% | 0.586 | 11.7 | 0.125 / 0.125 | 0.084 / 0.125 | 1.292 / 3.083 |

## sparse / sustained-churn-path-v1 / N=10000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `9fd708d7c0f33425`.

Operations: cut 488, link 12, query 500 (7 true / 493 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.704 [0.689, 0.716] | +0.0% | +52.0% | +52.0% | 1.678 | 11.7 | 0.125 / 0.167 | 0.250 / 0.250 | 3.333 / 9.292 |
| Workspace (opt-in) | 0.507 [0.506, 0.508] | -27.9% | +9.5% | +9.5% | 1.696 | 11.8 | 0.125 / 0.167 | 0.250 / 0.250 | 2.625 / 8.250 |
| ETT (experimental) | 0.590 [0.582, 0.613] | -16.2% | +27.4% | +27.4% | 12.316 | 11.7 | 1.333 / 1.750 | 1.209 / 1.209 | 0.458 / 0.583 |
| HDT (experimental) | 0.657 [0.644, 0.903] | -6.6% | +42.0% | +42.0% | 8.959 | 11.7 | 1.583 / 2.625 | 1.500 / 1.500 | 0.625 / 1.084 |
| petgraph (external) | 0.463 [0.461, 0.561] | -34.2% | +0.0% | +0.0% | 0.628 | 11.7 | 0.125 / 0.125 | 0.125 / 0.125 | 2.583 / 6.375 |

## sparse / sustained-churn-path-v1 / N=10000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **Workspace (opt-in)**. Fingerprint: `9fd708d7c0f33425`.

Operations: cut 488, link 12, query 500 (7 true / 493 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.676 [0.662, 0.684] | +0.0% | +19.8% | +36.8% | 1.643 | 11.7 | 0.125 / 0.125 | 0.209 / 0.209 | 3.250 / 9.083 |
| Workspace (opt-in) | 0.494 [0.492, 0.821] | -26.9% | -12.4% | +0.0% | 1.631 | 11.7 | 0.125 / 0.166 | 0.209 / 0.209 | 2.625 / 8.250 |
| ETT (experimental) | 0.517 [0.513, 0.519] | -23.6% | -8.5% | +4.5% | 12.134 | 11.8 | 1.125 / 1.375 | 1.083 / 1.083 | 0.250 / 0.292 |
| HDT (experimental) | 0.597 [0.551, 0.924] | -11.7% | +5.7% | +20.8% | 8.403 | 11.7 | 1.292 / 1.625 | 0.959 / 0.959 | 0.375 / 0.500 |
| petgraph (external) | 0.565 [0.561, 1.159] | -16.5% | +0.0% | +14.2% | 0.583 | 11.7 | 0.125 / 0.125 | 0.125 / 0.125 | 3.584 / 7.000 |

## sparse / sustained-churn-path-v1 / N=10000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 2.649 [2.620, 5.334] | +0.0% | +25.0% | +589.5% | 1.671 | 11.8 | 0.167 / 0.208 | — / — | 8.916 / 16.125 |
| Workspace (opt-in) | 2.201 [2.158, 2.204] | -16.9% | +3.9% | +473.0% | 1.670 | 11.7 | 0.166 / 0.167 | — / — | 8.125 / 14.292 |
| ETT (experimental) | 0.474 [0.410, 0.498] | -82.1% | -77.6% | +23.3% | 12.484 | 11.7 | 2.125 / 3.250 | — / — | 0.709 / 1.167 |
| HDT (experimental) | 0.384 [0.382, 0.386] | -85.5% | -81.9% | +0.0% | 8.665 | 11.7 | 1.916 / 3.083 | — / — | 0.625 / 0.834 |
| petgraph (external) | 2.120 [2.113, 2.133] | -20.0% | +0.0% | +451.7% | 0.628 | 11.7 | 0.166 / 0.167 | — / — | 7.750 / 11.834 |

## sparse / sustained-churn-path-v1 / N=10000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 2.604 [2.601, 2.733] | +0.0% | +23.7% | +776.2% | 1.640 | 11.7 | 0.125 / 0.167 | — / — | 8.917 / 15.000 |
| Workspace (opt-in) | 2.224 [2.220, 2.307] | -14.6% | +5.7% | +648.5% | 1.647 | 11.7 | 0.166 / 0.167 | — / — | 8.250 / 14.875 |
| ETT (experimental) | 0.297 [0.289, 0.329] | -88.6% | -85.9% | +0.0% | 12.166 | 11.8 | 1.333 / 1.667 | — / — | 0.250 / 0.334 |
| HDT (experimental) | 0.308 [0.300, 0.325] | -88.2% | -85.4% | +3.7% | 8.269 | 11.8 | 1.500 / 1.667 | — / — | 0.292 / 0.375 |
| petgraph (external) | 2.105 [2.101, 2.733] | -19.1% | +0.0% | +608.4% | 0.580 | 11.8 | 0.125 / 0.125 | — / — | 7.584 / 12.000 |

## sparse / sustained-churn-path-v1 / N=100000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `c6d51f6b6cd4fb61`.

Operations: cut 894, link 6, query 100 (0 true / 100 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.792 [0.768, 0.814] | +0.0% | +40.5% | +40.5% | 18.473 | 16.7 | 0.417 / 0.583 | 0.416 / 0.416 | 16.667 / 36.875 |
| Workspace (opt-in) | 0.649 [0.638, 0.693] | -18.1% | +15.1% | +15.1% | 18.654 | 16.6 | 0.416 / 0.500 | 0.375 / 0.375 | 15.042 / 34.125 |
| ETT (experimental) | 3.406 [2.564, 3.412] | +330.0% | +504.0% | +504.0% | 224.820 | 47.8 | 9.375 / 14.417 | 2.416 / 2.416 | 6.125 / 8.291 |
| HDT (experimental) | 2.701 [2.297, 3.038] | +241.0% | +379.0% | +379.0% | 127.970 | 69.4 | 5.333 / 20.416 | 1.667 / 1.667 | 2.792 / 5.041 |
| petgraph (external) | 0.564 [0.562, 0.575] | -28.8% | +0.0% | +0.0% | 7.196 | 13.8 | 0.334 / 0.458 | 0.166 / 0.166 | 12.208 / 25.625 |

## sparse / sustained-churn-path-v1 / N=100000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `c6d51f6b6cd4fb61`.

Operations: cut 894, link 6, query 100 (0 true / 100 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.696 [0.693, 0.720] | +0.0% | +29.5% | +29.5% | 17.714 | 16.8 | 0.291 / 0.334 | 0.375 / 0.375 | 13.500 / 36.292 |
| Workspace (opt-in) | 0.593 [0.582, 0.675] | -14.8% | +10.4% | +10.4% | 17.911 | 16.7 | 0.292 / 0.375 | 0.416 / 0.416 | 14.709 / 33.541 |
| ETT (experimental) | 2.123 [2.103, 2.243] | +204.9% | +294.9% | +294.9% | 213.837 | 66.2 | 4.667 / 9.667 | 1.875 / 1.875 | 3.000 / 4.583 |
| HDT (experimental) | 2.682 [2.374, 6.719] | +285.2% | +398.9% | +398.9% | 132.220 | 87.9 | 6.958 / 21.083 | 1.583 / 1.583 | 3.375 / 4.875 |
| petgraph (external) | 0.538 [0.534, 0.648] | -22.8% | +0.0% | +0.0% | 6.609 | 13.9 | 0.250 / 0.292 | 0.167 / 0.167 | 12.584 / 26.542 |

## sparse / sustained-churn-path-v1 / N=100000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `1779b65c977fb4b8`.

Operations: cut 498, link 2, query 500 (13 true / 487 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 4.591 [4.545, 5.634] | +0.0% | +24.5% | +119.4% | 18.671 | 16.7 | 0.375 / 0.542 | 0.417 / 0.417 | 34.417 / 83.334 |
| Workspace (opt-in) | 4.255 [3.959, 4.702] | -7.3% | +15.3% | +103.3% | 19.020 | 16.6 | 0.667 / 1.125 | 0.375 / 0.375 | 30.834 / 84.000 |
| ETT (experimental) | 2.093 [1.611, 2.106] | -54.4% | -43.3% | +0.0% | 211.483 | 47.8 | 4.750 / 8.000 | 1.792 / 1.792 | 3.417 / 6.333 |
| HDT (experimental) | 3.576 [2.098, 3.824] | -22.1% | -3.1% | +70.9% | 132.775 | 69.4 | 14.000 / 28.875 | 2.000 / 2.000 | 6.000 / 8.875 |
| petgraph (external) | 3.689 [3.632, 3.713] | -19.7% | +0.0% | +76.3% | 7.224 | 13.8 | 0.334 / 0.417 | 0.167 / 0.167 | 25.666 / 70.750 |

## sparse / sustained-churn-path-v1 / N=100000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `1779b65c977fb4b8`.

Operations: cut 498, link 2, query 500 (13 true / 487 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 4.673 [4.530, 10.307] | +0.0% | +26.0% | +97.5% | 18.061 | 16.8 | 0.375 / 1.125 | 0.417 / 0.417 | 32.833 / 91.417 |
| Workspace (opt-in) | 3.892 [3.861, 4.360] | -16.7% | +5.0% | +64.5% | 17.776 | 16.7 | 0.291 / 0.334 | 0.375 / 0.375 | 29.458 / 81.709 |
| ETT (experimental) | 2.366 [1.944, 3.312] | -49.4% | -36.2% | +0.0% | 221.714 | 66.2 | 6.833 / 11.500 | 1.916 / 1.916 | 5.042 / 9.041 |
| HDT (experimental) | 2.465 [2.156, 2.939] | -47.3% | -33.5% | +4.2% | 127.316 | 87.9 | 9.417 / 24.875 | 1.792 / 1.792 | 3.750 / 6.500 |
| petgraph (external) | 3.707 [3.551, 4.127] | -20.7% | +0.0% | +56.7% | 6.613 | 13.9 | 0.250 / 0.292 | 0.166 / 0.166 | 24.500 / 75.958 |

## sparse / sustained-churn-path-v1 / N=100000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `4f8ccd68acfa61f8`.

Operations: cut 100, link 0, query 900 (64 true / 836 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 23.467 [23.400, 23.789] | +0.0% | +7.8% | +1567.7% | 18.420 | 16.7 | 0.459 / 0.625 | — / — | 85.833 / 176.209 |
| Workspace (opt-in) | 22.571 [22.109, 23.327] | -3.8% | +3.7% | +1503.9% | 18.346 | 16.6 | 0.541 / 0.625 | — / — | 86.667 / 181.958 |
| ETT (experimental) | 1.407 [1.394, 1.598] | -94.0% | -93.5% | +0.0% | 205.636 | 47.8 | 6.708 / 10.333 | — / — | 3.375 / 5.541 |
| HDT (experimental) | 1.802 [1.571, 1.845] | -92.3% | -91.7% | +28.0% | 127.497 | 69.5 | 17.834 / 38.042 | — / — | 3.875 / 7.125 |
| petgraph (external) | 21.767 [19.391, 33.561] | -7.2% | +0.0% | +1446.8% | 7.370 | 13.8 | 1.375 / 1.666 | — / — | 85.500 / 153.750 |

## sparse / sustained-churn-path-v1 / N=100000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `4f8ccd68acfa61f8`.

Operations: cut 100, link 0, query 900 (64 true / 836 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 23.415 [23.365, 24.330] | +0.0% | +10.9% | +1458.5% | 17.816 | 16.7 | 0.292 / 0.375 | — / — | 86.542 / 179.167 |
| Workspace (opt-in) | 22.462 [22.259, 22.770] | -4.1% | +6.4% | +1395.0% | 17.886 | 16.6 | 0.375 / 0.625 | — / — | 87.792 / 182.542 |
| ETT (experimental) | 1.710 [1.646, 1.973] | -92.7% | -91.9% | +13.8% | 204.781 | 66.2 | 7.458 / 10.917 | — / — | 4.500 / 7.583 |
| HDT (experimental) | 1.502 [1.425, 2.386] | -93.6% | -92.9% | +0.0% | 126.021 | 87.9 | 17.125 / 29.708 | — / — | 2.500 / 5.167 |
| petgraph (external) | 21.110 [20.288, 42.936] | -9.8% | +0.0% | +1305.0% | 7.219 | 13.8 | 0.542 / 0.625 | — / — | 71.041 / 149.542 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=10 / fresh

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `e39886814af69da5`.

Operations: cut 900, link 0, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.589 [5.022, 5.761] | +0.0% | +42.0% | +42.0% | 202.495 | 132.3 | 1.500 / 1.833 | — / — | 174.542 / 349.625 |
| Workspace (opt-in) | 5.657 [4.907, 5.674] | +1.2% | +43.7% | +43.7% | 203.025 | 136.0 | 1.958 / 2.875 | — / — | 179.833 / 436.000 |
| ETT (experimental) | 9.982 [6.563, 31.017] | +78.6% | +153.5% | +153.5% | 3173.328 | 381.3 | 21.833 / 33.791 | — / — | 12.708 / 15.500 |
| HDT (experimental) | 27.982 [10.431, 29.695] | +400.7% | +610.7% | +610.7% | 1910.402 | 493.2 | 98.083 / 186.416 | — / — | 36.125 / 66.917 |
| petgraph (external) | 3.937 [3.819, 4.911] | -29.6% | +0.0% | +0.0% | 75.580 | 90.7 | 1.333 / 1.541 | — / — | 129.542 / 229.500 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=10 / warmed

Complete: True (3/3 valid trials per engine). Winner: **petgraph (external)**. Fingerprint: `e39886814af69da5`.

Operations: cut 900, link 0, query 100 (2 true / 98 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 4.882 [4.813, 5.328] | +0.0% | +27.9% | +27.9% | 198.070 | 161.2 | 1.250 / 1.667 | — / — | 137.875 / 229.208 |
| Workspace (opt-in) | 5.003 [4.882, 5.786] | +2.5% | +31.1% | +31.1% | 199.161 | 145.0 | 1.708 / 1.959 | — / — | 164.084 / 332.250 |
| ETT (experimental) | 8.069 [7.009, 8.765] | +65.3% | +111.4% | +111.4% | 3178.840 | 493.8 | 17.125 / 26.000 | — / — | 10.083 / 12.167 |
| HDT (experimental) | 5.451 [4.960, 7.940] | +11.6% | +42.8% | +42.8% | 1834.136 | 588.2 | 12.292 / 18.000 | — / — | 6.833 / 9.042 |
| petgraph (external) | 3.816 [3.473, 9.141] | -21.8% | +0.0% | +0.0% | 73.558 | 121.3 | 1.292 / 1.541 | — / — | 118.500 / 241.875 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=50 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `01a19f08e1152f91`.

Operations: cut 500, link 0, query 500 (15 true / 485 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 43.218 [42.995, 43.307] | +0.0% | +19.8% | +424.3% | 202.877 | 148.6 | 1.000 / 1.375 | — / — | 232.417 / 804.042 |
| Workspace (opt-in) | 40.069 [39.548, 41.700] | -7.3% | +11.1% | +386.1% | 206.089 | 143.0 | 1.000 / 1.291 | — / — | 237.791 / 815.875 |
| ETT (experimental) | 8.243 [5.660, 13.510] | -80.9% | -77.2% | +0.0% | 3149.529 | 381.4 | 19.583 / 25.333 | — / — | 13.459 / 16.500 |
| HDT (experimental) | 44.000 [13.766, 46.204] | +1.8% | +22.0% | +433.8% | 2052.818 | 460.0 | 128.750 / 367.208 | — / — | 39.000 / 149.041 |
| petgraph (external) | 36.076 [35.154, 36.282] | -16.5% | +0.0% | +337.7% | 73.248 | 90.7 | 1.291 / 2.000 | — / — | 197.125 / 902.417 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=50 / warmed

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `01a19f08e1152f91`.

Operations: cut 500, link 0, query 500 (15 true / 485 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 42.505 [41.906, 44.686] | +0.0% | +13.7% | +574.1% | 201.655 | 171.6 | 1.917 / 3.208 | — / — | 236.584 / 821.625 |
| Workspace (opt-in) | 40.140 [39.638, 40.328] | -5.6% | +7.4% | +536.6% | 197.473 | 152.0 | 0.875 / 1.125 | — / — | 232.917 / 828.584 |
| ETT (experimental) | 6.306 [6.285, 7.011] | -85.2% | -83.1% | +0.0% | 3193.039 | 546.3 | 14.583 / 20.542 | — / — | 9.375 / 13.083 |
| HDT (experimental) | 6.367 [5.686, 6.951] | -85.0% | -83.0% | +1.0% | 1797.834 | 587.4 | 14.709 / 20.458 | — / — | 9.583 / 12.208 |
| petgraph (external) | 37.374 [35.202, 39.113] | -12.1% | +0.0% | +492.7% | 73.326 | 121.3 | 0.667 / 0.792 | — / — | 204.917 / 957.000 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=90 / fresh

Complete: True (3/3 valid trials per engine). Winner: **ETT (experimental)**. Fingerprint: `5097cf16db2527e7`.

Operations: cut 100, link 0, query 900 (51 true / 849 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 217.459 [210.840, 232.536] | +0.0% | +22.1% | +3578.0% | 210.688 | 182.6 | 1.250 / 1.667 | — / — | 802.666 / 1954.041 |
| Workspace (opt-in) | 212.574 [207.831, 221.767] | -2.2% | +19.4% | +3495.4% | 202.470 | 143.0 | 1.250 / 2.291 | — / — | 821.708 / 1720.625 |
| ETT (experimental) | 5.912 [5.056, 23.038] | -97.3% | -96.7% | +0.0% | 3189.194 | 381.3 | 22.042 / 34.792 | — / — | 11.375 / 16.375 |
| HDT (experimental) | 8.806 [3.611, 13.761] | -96.0% | -95.1% | +48.9% | 1928.109 | 587.7 | 29.083 / 42.458 | — / — | 15.375 / 19.750 |
| petgraph (external) | 178.041 [177.827, 231.888] | -18.1% | +0.0% | +2911.3% | 74.890 | 90.7 | 0.958 / 1.583 | — / — | 661.291 / 1555.958 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=90 / warmed

Complete: True (3/3 valid trials per engine). Winner: **HDT (experimental)**. Fingerprint: `5097cf16db2527e7`.

Operations: cut 100, link 0, query 900 (51 true / 849 false).

| Engine | Runtime ms [min, max] | Δ Compact | Δ petgraph | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 215.435 [212.296, 251.888] | +0.0% | +16.1% | +3250.3% | 203.047 | 207.5 | 1.750 / 2.333 | — / — | 806.917 / 2023.666 |
| Workspace (opt-in) | 209.830 [207.072, 210.243] | -2.6% | +13.1% | +3163.2% | 197.420 | 152.0 | 1.000 / 1.167 | — / — | 824.792 / 1717.583 |
| ETT (experimental) | 8.126 [5.551, 22.864] | -96.2% | -95.6% | +26.4% | 3184.644 | 464.4 | 38.375 / 52.500 | — / — | 16.625 / 22.167 |
| HDT (experimental) | 6.430 [4.576, 6.917] | -97.0% | -96.5% | +0.0% | 1820.106 | 575.8 | 18.709 / 20.958 | — / — | 11.833 / 14.875 |
| petgraph (external) | 185.592 [182.196, 188.861] | -13.9% | +0.0% | +2786.2% | 74.873 | 121.3 | 1.833 / 3.416 | — / — | 668.625 / 1648.292 |

