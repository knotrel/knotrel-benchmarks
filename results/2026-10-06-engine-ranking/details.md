# Per-cell results

All values are medians across three processes, except the one-trial extreme supplement. p95/p99 columns are medians of each process percentile, not percentiles of pooled samples. Δ Compact = `100*(runtime/Compact-1)`; negative means faster. Above best = `100*(runtime/best-1)`. Runtime/setup are milliseconds, operation tails are microseconds and RSS is MiB. Missing operations are shown as —.

## sparse / sustained-churn-blocks-v1 / N=1024 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `320eed6cfa5efb0f`.

Operations: cut 484, link 416, query 100 (6 true / 94 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.179 [0.178, 0.196] | +0.0% | +59.8% | 0.182 | 7.6 | 0.125 / 0.125 | 0.167 / 0.208 | 1.708 / 2.875 |
| ETT (experimental) | 1.015 [1.003, 1.080] | +467.2% | +806.2% | 1.005 | 7.6 | 2.291 / 3.250 | 1.375 / 1.541 | 0.208 / 0.209 |
| HDT (experimental) | 3.197 [3.148, 3.337] | +1685.9% | +2753.2% | 0.768 | 7.6 | 15.875 / 84.167 | 1.084 / 1.292 | 0.250 / 0.333 |
| petgraph (external) | 0.112 [0.111, 0.115] | -37.4% | +0.0% | 0.082 | 7.6 | 0.084 / 0.125 | 0.084 / 0.084 | 0.709 / 1.125 |
| Workspace (opt-in) | 0.149 [0.148, 0.151] | -16.8% | +32.9% | 0.179 | 7.6 | 0.125 / 0.125 | 0.167 / 0.208 | 0.791 / 1.166 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `320eed6cfa5efb0f`.

Operations: cut 484, link 416, query 100 (6 true / 94 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 3.101 [2.933, 3.132] | +2237.0% | +3357.2% | 0.704 | 7.6 | 13.834 / 81.000 | 1.083 / 1.209 | 0.209 / 0.250 |
| petgraph (external) | 0.090 [0.089, 0.091] | -32.4% | +0.0% | 0.061 | 7.6 | 0.083 / 0.084 | 0.083 / 0.084 | 0.584 / 0.958 |
| Workspace (opt-in) | 0.111 [0.111, 0.111] | -16.4% | +23.6% | 0.167 | 7.6 | 0.084 / 0.084 | 0.125 / 0.125 | 0.625 / 0.875 |
| Compact (default) | 0.133 [0.132, 0.135] | +0.0% | +47.9% | 0.166 | 7.6 | 0.084 / 0.084 | 0.125 / 0.125 | 0.917 / 1.375 |
| ETT (experimental) | 0.930 [0.908, 0.991] | +600.5% | +936.3% | 0.957 | 7.7 | 2.167 / 3.333 | 1.250 / 1.375 | 0.208 / 0.250 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=50 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `9415351e77d1989e`.

Operations: cut 281, link 219, query 500 (46 true / 454 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.417 [0.416, 0.426] | +0.0% | +59.3% | 0.175 | 7.6 | 0.125 / 0.125 | 0.167 / 0.208 | 1.375 / 2.583 |
| Workspace (opt-in) | 0.291 [0.270, 0.293] | -30.3% | +11.1% | 0.175 | 7.6 | 0.125 / 0.125 | 0.167 / 0.167 | 1.000 / 1.458 |
| ETT (experimental) | 0.699 [0.688, 0.715] | +67.5% | +166.9% | 0.996 | 7.6 | 2.583 / 3.459 | 1.500 / 1.625 | 0.167 / 0.209 |
| HDT (experimental) | 2.505 [2.504, 2.523] | +500.8% | +857.1% | 0.772 | 7.6 | 25.666 / 101.125 | 1.167 / 1.250 | 0.209 / 0.250 |
| petgraph (external) | 0.262 [0.252, 0.268] | -37.2% | +0.0% | 0.080 | 7.6 | 0.084 / 0.125 | 0.084 / 0.125 | 0.875 / 1.666 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=50 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `9415351e77d1989e`.

Operations: cut 281, link 219, query 500 (46 true / 454 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.349 [0.341, 0.358] | +0.0% | +50.6% | 0.166 | 7.6 | 0.084 / 0.084 | 0.125 / 0.167 | 1.167 / 1.542 |
| Workspace (opt-in) | 0.237 [0.237, 0.242] | -31.9% | +2.5% | 0.167 | 7.6 | 0.084 / 0.084 | 0.125 / 0.166 | 0.792 / 1.208 |
| HDT (experimental) | 2.314 [2.300, 2.324] | +563.7% | +899.7% | 0.705 | 7.6 | 23.375 / 97.750 | 1.000 / 1.167 | 0.167 / 0.209 |
| petgraph (external) | 0.232 [0.230, 0.235] | -33.6% | +0.0% | 0.061 | 7.7 | 0.083 / 0.084 | 0.083 / 0.084 | 0.792 / 1.625 |
| ETT (experimental) | 0.622 [0.616, 0.689] | +78.5% | +168.8% | 0.962 | 7.7 | 2.291 / 3.542 | 1.333 / 1.459 | 0.167 / 0.167 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `0ad790a6f3499ba1`.

Operations: cut 76, link 24, query 900 (110 true / 790 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.525 [0.490, 0.530] | -24.5% | +84.8% | 0.075 | 7.6 | 0.125 / 0.167 | 0.084 / 0.125 | 1.458 / 2.459 |
| Compact (default) | 0.696 [0.691, 0.700] | +0.0% | +144.8% | 0.176 | 7.6 | 0.125 / 0.250 | 0.167 / 0.208 | 1.541 / 2.500 |
| ETT (experimental) | 0.284 [0.283, 0.299] | -59.2% | +0.0% | 1.003 | 7.6 | 3.417 / 5.541 | 1.500 / 1.666 | 0.167 / 0.167 |
| Workspace (opt-in) | 0.464 [0.459, 0.468] | -33.2% | +63.4% | 0.175 | 7.6 | 0.125 / 0.333 | 0.167 / 0.208 | 1.084 / 1.625 |
| HDT (experimental) | 1.691 [1.663, 1.732] | +143.1% | +495.1% | 0.764 | 7.6 | 67.958 / 285.584 | 1.167 / 1.250 | 0.208 / 0.209 |

## sparse / sustained-churn-blocks-v1 / N=1024 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `0ad790a6f3499ba1`.

Operations: cut 76, link 24, query 900 (110 true / 790 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 0.247 [0.237, 0.262] | -59.2% | +0.0% | 0.959 | 7.6 | 2.750 / 4.209 | 1.333 / 1.416 | 0.125 / 0.167 |
| HDT (experimental) | 1.548 [1.544, 1.564] | +155.7% | +527.2% | 0.705 | 7.6 | 59.458 / 267.417 | 1.083 / 1.125 | 0.167 / 0.208 |
| Workspace (opt-in) | 0.395 [0.390, 0.404] | -34.8% | +59.9% | 0.165 | 7.6 | 0.084 / 0.125 | 0.167 / 0.167 | 0.958 / 1.500 |
| Compact (default) | 0.605 [0.602, 0.611] | +0.0% | +145.3% | 0.164 | 7.6 | 0.084 / 0.125 | 0.125 / 0.167 | 1.333 / 1.917 |
| petgraph (external) | 0.507 [0.505, 0.508] | -16.3% | +105.4% | 0.059 | 7.6 | 0.084 / 0.084 | 0.083 / 0.084 | 1.417 / 2.459 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `33274370397b138c`.

Operations: cut 677, link 223, query 100 (1 true / 99 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 1.608 [1.604, 1.658] | +436.5% | +642.8% | 12.740 | 9.1 | 3.541 / 7.375 | 1.667 / 1.792 | 0.375 / 0.417 |
| Workspace (opt-in) | 0.247 [0.242, 0.248] | -17.6% | +14.1% | 1.763 | 7.6 | 0.125 / 0.167 | 0.250 / 0.250 | 2.542 / 4.875 |
| HDT (experimental) | 29.467 [29.371, 31.232] | +9734.8% | +13516.0% | 9.323 | 27.9 | 129.208 / 562.209 | 2.542 / 3.667 | 1.166 / 2.417 |
| Compact (default) | 0.300 [0.296, 0.308] | +0.0% | +38.4% | 1.766 | 7.7 | 0.125 / 0.167 | 0.250 / 0.250 | 4.417 / 8.167 |
| petgraph (external) | 0.216 [0.208, 0.223] | -27.8% | +0.0% | 0.673 | 7.6 | 0.125 / 0.167 | 0.125 / 0.167 | 2.709 / 6.500 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `33274370397b138c`.

Operations: cut 677, link 223, query 100 (1 true / 99 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.257 [0.256, 0.261] | +0.0% | +31.7% | 1.753 | 7.6 | 0.125 / 0.125 | 0.209 / 0.250 | 2.792 / 5.375 |
| ETT (experimental) | 1.563 [1.542, 15.071] | +507.7% | +700.4% | 12.396 | 9.1 | 3.375 / 6.958 | 1.709 / 1.792 | 0.333 / 0.500 |
| HDT (experimental) | 28.899 [28.634, 30.471] | +11135.7% | +14698.0% | 9.006 | 28.8 | 123.625 / 528.125 | 2.292 / 2.750 | 1.125 / 1.583 |
| Workspace (opt-in) | 0.229 [0.219, 0.266] | -11.0% | +17.2% | 1.765 | 7.6 | 0.125 / 0.208 | 0.209 / 0.250 | 2.417 / 4.125 |
| petgraph (external) | 0.195 [0.195, 0.197] | -24.1% | +0.0% | 0.629 | 7.6 | 0.125 / 0.125 | 0.125 / 0.125 | 2.667 / 6.333 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=50 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `812d06e6d029beeb`.

Operations: cut 426, link 74, query 500 (21 true / 479 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.914 [0.881, 0.923] | -10.5% | +23.0% | 0.660 | 7.6 | 0.125 / 0.167 | 0.125 / 0.167 | 3.917 / 15.584 |
| Compact (default) | 1.021 [0.980, 1.039] | +0.0% | +37.5% | 1.791 | 7.6 | 0.167 / 0.209 | 0.250 / 0.250 | 3.666 / 16.875 |
| ETT (experimental) | 1.171 [1.170, 1.173] | +14.7% | +57.6% | 12.687 | 9.0 | 4.167 / 9.667 | 1.667 / 1.750 | 0.333 / 0.417 |
| HDT (experimental) | 27.321 [27.078, 29.087] | +2575.0% | +3577.5% | 9.179 | 28.7 | 195.167 / 885.250 | 2.375 / 3.458 | 1.125 / 1.834 |
| Workspace (opt-in) | 0.743 [0.737, 0.751] | -27.3% | +0.0% | 1.778 | 7.6 | 0.167 / 0.167 | 0.250 / 0.250 | 2.958 / 15.375 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `812d06e6d029beeb`.

Operations: cut 426, link 74, query 500 (21 true / 479 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 1.098 [1.057, 1.142] | +20.0% | +56.9% | 12.275 | 9.1 | 3.917 / 9.917 | 1.583 / 1.667 | 0.333 / 0.417 |
| Compact (default) | 0.914 [0.878, 0.925] | +0.0% | +30.7% | 1.752 | 7.6 | 0.125 / 0.125 | 0.209 / 0.250 | 3.167 / 9.791 |
| Workspace (opt-in) | 0.700 [0.672, 0.708] | -23.5% | +0.0% | 1.726 | 7.6 | 0.125 / 0.167 | 0.250 / 0.250 | 2.583 / 12.500 |
| petgraph (external) | 1.142 [0.882, 1.163] | +24.8% | +63.1% | 0.638 | 7.6 | 0.125 / 0.167 | 0.125 / 0.125 | 5.625 / 20.500 |
| HDT (experimental) | 26.559 [25.989, 29.577] | +2804.2% | +3695.0% | 8.743 | 29.7 | 197.333 / 855.708 | 2.000 / 3.334 | 1.000 / 2.166 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 3.943 [3.908, 4.076] | +32.5% | +469.0% | 0.656 | 7.6 | 0.166 / 0.208 | 0.167 / 0.167 | 12.958 / 18.375 |
| HDT (experimental) | 17.283 [17.226, 17.479] | +480.6% | +2394.1% | 9.240 | 23.3 | 690.708 / 2664.125 | 1.917 / 1.917 | 0.708 / 0.958 |
| Compact (default) | 2.977 [2.959, 3.148] | +0.0% | +329.6% | 1.763 | 7.6 | 0.167 / 0.333 | 0.250 / 0.250 | 8.500 / 13.500 |
| Workspace (opt-in) | 2.459 [2.425, 2.465] | -17.4% | +254.9% | 1.758 | 7.6 | 0.167 / 0.292 | 0.250 / 0.250 | 7.667 / 11.250 |
| ETT (experimental) | 0.693 [0.587, 0.773] | -76.7% | +0.0% | 12.820 | 9.0 | 9.792 / 32.417 | 1.792 / 1.792 | 0.500 / 0.709 |

## sparse / sustained-churn-blocks-v1 / N=10000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 0.575 [0.542, 0.599] | -80.2% | +0.0% | 12.295 | 9.1 | 8.542 / 25.458 | 1.667 / 1.667 | 0.333 / 0.375 |
| Compact (default) | 2.908 [2.874, 2.920] | +0.0% | +405.8% | 1.733 | 7.6 | 0.166 / 0.167 | 0.250 / 0.250 | 8.333 / 12.125 |
| petgraph (external) | 4.077 [3.939, 5.034] | +40.2% | +609.1% | 0.628 | 7.6 | 0.125 / 0.209 | 0.125 / 0.125 | 13.042 / 19.833 |
| HDT (experimental) | 17.058 [16.546, 17.473] | +486.7% | +2867.1% | 8.849 | 24.0 | 663.750 / 2714.167 | 2.542 / 2.542 | 0.875 / 1.125 |
| Workspace (opt-in) | 2.362 [2.337, 2.408] | -18.8% | +310.9% | 1.729 | 7.6 | 0.167 / 0.167 | 0.209 / 0.209 | 7.583 / 11.209 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=10 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `89e71664442094ae`.

Operations: cut 865, link 35, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 6.211 [6.136, 6.341] | +552.3% | +645.6% | 204.165 | 58.5 | 16.375 / 58.500 | 2.833 / 2.875 | 1.417 / 1.791 |
| HDT (experimental) | 325.562 [314.943, 333.693] | +34094.7% | +38987.0% | 133.040 | 293.4 | 1184.792 / 4776.292 | 6.333 / 7.209 | 3.708 / 4.750 |
| Workspace (opt-in) | 0.833 [0.816, 0.918] | -12.5% | +0.0% | 20.028 | 16.7 | 0.417 / 0.542 | 0.292 / 0.292 | 15.333 / 47.333 |
| Compact (default) | 0.952 [0.939, 0.983] | +0.0% | +14.3% | 19.510 | 16.8 | 0.375 / 0.500 | 0.292 / 0.333 | 18.125 / 49.042 |
| petgraph (external) | 1.036 [1.032, 1.170] | +8.8% | +24.3% | 7.752 | 14.1 | 0.292 / 0.375 | 0.208 / 0.250 | 22.458 / 74.375 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=10 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `89e71664442094ae`.

Operations: cut 865, link 35, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.741 [0.713, 0.805] | -13.7% | +0.0% | 18.953 | 16.7 | 0.250 / 0.333 | 0.292 / 0.292 | 15.459 / 46.417 |
| petgraph (external) | 1.001 [0.978, 1.008] | +16.6% | +35.1% | 7.215 | 14.1 | 0.167 / 0.250 | 0.167 / 0.167 | 22.791 / 75.750 |
| ETT (experimental) | 6.268 [5.977, 7.552] | +630.2% | +746.0% | 205.888 | 83.7 | 15.583 / 58.792 | 2.792 / 2.875 | 1.458 / 1.625 |
| Compact (default) | 0.859 [0.850, 0.937] | +0.0% | +15.9% | 18.819 | 16.8 | 0.250 / 0.333 | 0.292 / 0.292 | 16.541 / 47.625 |
| HDT (experimental) | 314.135 [312.933, 314.740] | +36491.1% | +42295.8% | 129.881 | 302.3 | 1171.334 / 4626.583 | 5.583 / 6.500 | 3.584 / 4.834 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=50 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `1bc5729376b7dc79`.

Operations: cut 490, link 10, query 500 (20 true / 480 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 5.239 [4.883, 5.293] | +0.0% | +16.1% | 19.483 | 16.8 | 0.375 / 0.459 | 0.333 / 0.333 | 35.708 / 93.166 |
| petgraph (external) | 7.438 [7.384, 7.905] | +42.0% | +64.8% | 7.646 | 14.1 | 0.416 / 0.500 | 0.209 / 0.209 | 53.584 / 151.833 |
| Workspace (opt-in) | 4.512 [4.486, 4.605] | -13.9% | +0.0% | 19.403 | 16.6 | 0.375 / 0.500 | 0.292 / 0.292 | 32.583 / 94.041 |
| HDT (experimental) | 336.350 [333.739, 399.738] | +6320.7% | +7354.6% | 132.913 | 276.5 | 2597.500 / 11344.125 | 7.792 / 7.792 | 3.666 / 4.750 |
| ETT (experimental) | 6.577 [6.213, 7.328] | +25.6% | +45.8% | 205.747 | 58.5 | 36.250 / 182.917 | 3.125 / 3.125 | 1.375 / 1.958 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `1bc5729376b7dc79`.

Operations: cut 490, link 10, query 500 (20 true / 480 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 6.251 [5.944, 6.293] | +22.6% | +36.0% | 202.591 | 83.7 | 33.125 / 161.959 | 3.125 / 3.125 | 1.333 / 1.583 |
| HDT (experimental) | 322.979 [320.667, 326.228] | +6236.7% | +6929.2% | 130.125 | 278.5 | 2498.042 / 11311.584 | 6.958 / 6.958 | 4.042 / 5.541 |
| Workspace (opt-in) | 4.595 [4.493, 4.671] | -9.9% | +0.0% | 18.988 | 16.7 | 0.375 / 0.583 | 0.375 / 0.375 | 37.625 / 94.459 |
| Compact (default) | 5.097 [4.977, 5.123] | +0.0% | +10.9% | 18.998 | 16.8 | 0.292 / 0.334 | 0.334 / 0.334 | 33.125 / 91.000 |
| petgraph (external) | 7.408 [7.359, 8.663] | +45.3% | +61.2% | 7.089 | 14.1 | 0.333 / 0.459 | 0.167 / 0.167 | 55.291 / 149.084 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `912b25a39d1308b7`.

Operations: cut 100, link 0, query 900 (121 true / 779 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 4.194 [3.791, 4.206] | -83.0% | +0.0% | 204.278 | 58.4 | 93.375 / 460.500 | — / — | 1.542 / 1.917 |
| petgraph (external) | 39.008 [38.936, 39.640] | +58.2% | +830.0% | 7.663 | 14.1 | 0.583 / 0.666 | — / — | 101.583 / 289.666 |
| HDT (experimental) | 214.466 [212.925, 216.647] | +769.5% | +5013.1% | 132.492 | 205.3 | 9523.708 / 20471.083 | — / — | 2.916 / 3.709 |
| Compact (default) | 24.665 [24.516, 27.509] | +0.0% | +488.0% | 19.457 | 16.8 | 0.584 / 1.000 | — / — | 60.541 / 175.792 |
| Workspace (opt-in) | 23.976 [23.860, 24.046] | -2.8% | +471.6% | 19.578 | 16.6 | 0.542 / 0.708 | — / — | 61.000 / 181.833 |

## sparse / sustained-churn-blocks-v1 / N=100000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `912b25a39d1308b7`.

Operations: cut 100, link 0, query 900 (121 true / 779 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 216.863 [214.877, 240.296] | +786.8% | +5775.6% | 131.183 | 206.8 | 9532.083 / 20680.250 | — / — | 4.042 / 6.250 |
| Compact (default) | 24.456 [24.398, 24.527] | +0.0% | +562.6% | 18.963 | 16.8 | 0.542 / 0.667 | — / — | 60.166 / 173.000 |
| ETT (experimental) | 3.691 [3.673, 4.007] | -84.9% | +0.0% | 202.502 | 83.7 | 81.375 / 415.791 | — / — | 1.458 / 1.708 |
| Workspace (opt-in) | 23.716 [23.704, 23.782] | -3.0% | +542.6% | 18.992 | 16.7 | 0.375 / 0.584 | — / — | 62.834 / 181.125 |
| petgraph (external) | 39.159 [38.997, 39.399] | +60.1% | +961.0% | 7.085 | 14.1 | 0.458 / 0.583 | — / — | 99.583 / 291.917 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=10 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `14a90b222d96b94d`.

Operations: cut 896, link 4, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 5.177 [4.829, 7.844] | -6.6% | +0.0% | 215.667 | 136.9 | 1.000 / 1.708 | 0.625 / 0.625 | 149.292 / 352.209 |
| petgraph (external) | 7.232 [7.029, 7.354] | +30.5% | +39.7% | 81.495 | 109.5 | 0.750 / 0.875 | 0.375 / 0.375 | 212.791 / 388.958 |
| ETT (experimental) | 64.855 [64.533, 73.142] | +1070.4% | +1152.8% | 3127.544 | 486.1 | 228.375 / 1006.625 | 5.792 / 5.792 | 4.834 / 5.500 |
| HDT (experimental) | 5200.543 [5193.644, 5223.467] | +93747.9% | +100354.0% | 2041.172 | 1959.7 | 16339.667 / 76685.375 | 131.417 / 131.417 | 60.375 / 155.583 |
| Compact (default) | 5.541 [5.454, 6.041] | +0.0% | +7.0% | 216.908 | 133.6 | 0.916 / 1.208 | 0.459 / 0.459 | 146.833 / 273.375 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=10 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `14a90b222d96b94d`.

Operations: cut 896, link 4, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 67.710 [65.192, 70.759] | +1182.9% | +1312.7% | 3086.575 | 702.2 | 234.917 / 1054.375 | 5.459 / 5.459 | 4.042 / 4.459 |
| HDT (experimental) | 4784.707 [4680.737, 5065.246] | +90558.1% | +99730.4% | 1978.456 | 2136.1 | 14188.542 / 61112.041 | 128.208 / 128.208 | 35.625 / 89.042 |
| petgraph (external) | 10.317 [10.245, 10.444] | +95.5% | +115.2% | 81.316 | 125.5 | 4.041 / 7.125 | 1.000 / 1.000 | 319.917 / 613.875 |
| Workspace (opt-in) | 4.793 [4.742, 4.825] | -9.2% | +0.0% | 209.773 | 159.8 | 0.875 / 0.958 | 0.375 / 0.375 | 132.542 / 312.042 |
| Compact (default) | 5.278 [5.245, 5.359] | +0.0% | +10.1% | 209.541 | 156.2 | 0.792 / 0.958 | 0.417 / 0.417 | 139.833 / 251.667 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=50 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `e4985759f0c1baed`.

Operations: cut 499, link 1, query 500 (18 true / 482 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 68.728 [68.169, 73.802] | +58.7% | +62.4% | 3189.697 | 486.1 | 443.125 / 2559.667 | 7.000 / 7.000 | 3.583 / 5.166 |
| petgraph (external) | 67.030 [65.866, 68.149] | +54.8% | +58.4% | 82.354 | 109.6 | 0.875 / 1.083 | 0.542 / 0.542 | 549.959 / 1007.875 |
| HDT (experimental) | 5305.634 [4688.174, 5457.177] | +12154.3% | +12440.8% | 2086.580 | 1454.3 | 28925.000 / 184227.958 | 41.375 / 41.375 | 153.417 / 342.083 |
| Compact (default) | 43.296 [42.905, 43.548] | +0.0% | +2.3% | 216.905 | 138.0 | 1.000 / 1.209 | 0.875 / 0.875 | 319.083 / 515.708 |
| Workspace (opt-in) | 42.307 [41.699, 43.091] | -2.3% | +0.0% | 223.697 | 140.8 | 1.083 / 1.375 | 0.959 / 0.959 | 344.583 / 570.417 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `e4985759f0c1baed`.

Operations: cut 499, link 1, query 500 (18 true / 482 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 69.551 [64.034, 75.565] | +61.2% | +67.2% | 3126.455 | 734.1 | 448.833 / 2547.750 | 7.833 / 7.833 | 3.625 / 4.375 |
| petgraph (external) | 68.883 [68.698, 69.206] | +59.7% | +65.6% | 81.213 | 125.6 | 4.666 / 7.125 | 0.542 / 0.542 | 545.291 / 936.416 |
| HDT (experimental) | 4531.607 [4374.522, 4821.736] | +10405.7% | +10796.8% | 1932.033 | 2062.3 | 24922.125 / 175008.125 | 13.041 / 13.041 | 84.041 / 253.958 |
| Compact (default) | 43.135 [43.133, 43.481] | +0.0% | +3.7% | 211.027 | 161.0 | 1.041 / 1.209 | 0.958 / 0.958 | 326.833 / 554.667 |
| Workspace (opt-in) | 41.587 [41.344, 45.189] | -3.6% | +0.0% | 210.042 | 163.8 | 1.042 / 1.334 | 0.958 / 0.958 | 341.458 / 558.750 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `2e8e9275071c8a32`.

Operations: cut 100, link 0, query 900 (125 true / 775 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 245.492 [245.304, 252.547] | -5.1% | +410.2% | 214.418 | 140.8 | 1.417 / 1.542 | — / — | 866.042 / 1123.292 |
| petgraph (external) | 398.462 [396.516, 399.038] | +54.1% | +728.1% | 82.706 | 109.6 | 1.666 / 2.250 | — / — | 1421.083 / 1773.000 |
| HDT (experimental) | 3549.135 [3260.519, 3855.633] | +1272.5% | +7275.7% | 1992.448 | 1650.4 | 118303.042 / 382623.542 | — / — | 14.083 / 20.167 |
| Compact (default) | 258.588 [247.006, 338.052] | +0.0% | +437.4% | 218.166 | 139.6 | 1.750 / 2.334 | — / — | 871.042 / 1152.750 |
| ETT (experimental) | 48.119 [46.791, 51.417] | -81.4% | +0.0% | 3344.457 | 486.0 | 1829.041 / 4263.500 | — / — | 3.458 / 4.875 |

## sparse / sustained-churn-blocks-v1 / N=1000000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `2e8e9275071c8a32`.

Operations: cut 100, link 0, query 900 (125 true / 775 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 399.899 [399.454, 400.552] | +65.5% | +742.5% | 81.191 | 125.6 | 7.458 / 8.625 | — / — | 1414.625 / 1809.584 |
| Compact (default) | 241.660 [240.933, 252.376] | +0.0% | +409.1% | 210.815 | 161.0 | 1.333 / 1.500 | — / — | 849.833 / 1106.500 |
| Workspace (opt-in) | 244.649 [244.590, 250.780] | +1.2% | +415.4% | 212.030 | 163.8 | 1.334 / 1.541 | — / — | 858.083 / 1098.541 |
| HDT (experimental) | 3408.847 [3304.503, 3529.083] | +1310.6% | +7081.6% | 1991.523 | 1597.5 | 115148.416 / 423677.625 | — / — | 27.125 / 60.667 |
| ETT (experimental) | 47.466 [46.594, 56.173] | -80.4% | +0.0% | 3141.980 | 708.2 | 1956.958 / 4354.375 | — / — | 3.209 / 4.000 |

## sparse / sustained-churn-path-v1 / N=1024 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `be2f4110f26fdb62`.

Operations: cut 667, link 233, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 0.538 [0.531, 0.591] | +291.7% | +485.8% | 0.746 | 7.6 | 0.917 / 1.292 | 0.750 / 0.833 | 0.208 / 0.250 |
| petgraph (external) | 0.092 [0.091, 0.092] | -33.1% | +0.0% | 0.064 | 7.6 | 0.084 / 0.125 | 0.084 / 0.084 | 0.333 / 0.708 |
| ETT (experimental) | 0.538 [0.538, 0.539] | +291.3% | +485.2% | 0.983 | 7.6 | 0.875 / 1.084 | 0.917 / 1.042 | 0.208 / 0.250 |
| Compact (default) | 0.137 [0.133, 0.141] | +0.0% | +49.5% | 0.166 | 7.6 | 0.125 / 0.125 | 0.167 / 0.209 | 1.208 / 1.458 |
| Workspace (opt-in) | 0.117 [0.117, 0.117] | -14.9% | +27.3% | 0.166 | 7.6 | 0.084 / 0.125 | 0.167 / 0.208 | 0.334 / 0.750 |

## sparse / sustained-churn-path-v1 / N=1024 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `be2f4110f26fdb62`.

Operations: cut 667, link 233, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.106 [0.104, 0.106] | +0.0% | +43.6% | 0.157 | 7.6 | 0.084 / 0.084 | 0.125 / 0.166 | 0.541 / 0.750 |
| Workspace (opt-in) | 0.096 [0.095, 0.096] | -9.4% | +30.1% | 0.157 | 7.6 | 0.084 / 0.084 | 0.125 / 0.125 | 0.375 / 0.625 |
| HDT (experimental) | 0.480 [0.474, 0.485] | +354.5% | +552.6% | 0.691 | 7.6 | 0.833 / 1.042 | 0.625 / 0.709 | 0.167 / 0.167 |
| ETT (experimental) | 0.486 [0.481, 0.522] | +360.7% | +561.5% | 0.933 | 7.6 | 0.833 / 1.000 | 0.792 / 0.916 | 0.167 / 0.208 |
| petgraph (external) | 0.074 [0.073, 0.075] | -30.3% | +0.0% | 0.056 | 7.7 | 0.084 / 0.084 | 0.084 / 0.084 | 0.291 / 0.417 |

## sparse / sustained-churn-path-v1 / N=1024 / q=50 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `fff476c9490b49fe`.

Operations: cut 418, link 82, query 500 (12 true / 488 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.133 [0.126, 2.012] | -37.5% | +0.0% | 0.064 | 7.6 | 0.084 / 0.125 | 0.084 / 0.125 | 0.375 / 0.667 |
| HDT (experimental) | 0.399 [0.397, 0.400] | +87.2% | +199.6% | 0.744 | 7.6 | 1.000 / 1.458 | 0.792 / 1.042 | 0.167 / 0.208 |
| ETT (experimental) | 0.394 [0.387, 0.395] | +84.7% | +195.6% | 0.976 | 7.7 | 0.958 / 1.250 | 1.000 / 1.292 | 0.167 / 0.208 |
| Workspace (opt-in) | 0.146 [0.146, 0.147] | -31.5% | +9.7% | 0.167 | 7.6 | 0.084 / 0.125 | 0.208 / 0.250 | 0.334 / 0.625 |
| Compact (default) | 0.213 [0.213, 0.223] | +0.0% | +60.1% | 0.166 | 7.6 | 0.084 / 0.125 | 0.208 / 0.250 | 0.625 / 2.250 |

## sparse / sustained-churn-path-v1 / N=1024 / q=50 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `fff476c9490b49fe`.

Operations: cut 418, link 82, query 500 (12 true / 488 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 0.346 [0.346, 0.352] | +85.3% | +211.9% | 0.695 | 7.6 | 0.875 / 1.125 | 0.667 / 0.833 | 0.166 / 0.208 |
| Workspace (opt-in) | 0.127 [0.126, 0.128] | -32.1% | +14.3% | 0.155 | 7.6 | 0.084 / 0.084 | 0.125 / 0.167 | 0.333 / 0.625 |
| ETT (experimental) | 0.345 [0.344, 0.352] | +84.7% | +210.9% | 0.934 | 7.7 | 0.834 / 1.125 | 0.916 / 1.042 | 0.125 / 0.208 |
| Compact (default) | 0.187 [0.185, 0.222] | +0.0% | +68.3% | 0.157 | 7.6 | 0.084 / 0.084 | 0.125 / 0.167 | 0.542 / 1.000 |
| petgraph (external) | 0.111 [0.111, 0.111] | -40.6% | +0.0% | 0.056 | 7.7 | 0.084 / 0.084 | 0.084 / 0.084 | 0.333 / 0.625 |

## sparse / sustained-churn-path-v1 / N=1024 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `168ee7a337647010`.

Operations: cut 94, link 6, query 900 (56 true / 844 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.306 [0.284, 0.307] | -41.6% | +47.3% | 0.062 | 7.6 | 0.125 / 0.208 | 0.125 / 0.125 | 0.917 / 1.708 |
| HDT (experimental) | 0.212 [0.211, 0.221] | -59.6% | +1.8% | 0.750 | 7.6 | 1.292 / 2.541 | 1.125 / 1.125 | 0.167 / 0.208 |
| ETT (experimental) | 0.208 [0.207, 0.213] | -60.3% | +0.0% | 0.985 | 7.6 | 1.208 / 1.958 | 1.333 / 1.333 | 0.167 / 0.167 |
| Compact (default) | 0.524 [0.496, 0.527] | +0.0% | +152.1% | 0.165 | 7.6 | 0.125 / 0.292 | 0.250 / 0.250 | 1.125 / 3.041 |
| Workspace (opt-in) | 0.319 [0.319, 0.319] | -39.1% | +53.5% | 0.165 | 7.6 | 0.125 / 0.250 | 0.250 / 0.250 | 0.791 / 1.792 |

## sparse / sustained-churn-path-v1 / N=1024 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `168ee7a337647010`.

Operations: cut 94, link 6, query 900 (56 true / 844 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 0.187 [0.185, 0.187] | -60.3% | +2.9% | 0.691 | 7.6 | 1.083 / 1.333 | 1.000 / 1.000 | 0.125 / 0.167 |
| petgraph (external) | 0.361 [0.292, 0.362] | -23.2% | +99.1% | 0.054 | 7.6 | 0.083 / 0.084 | 0.042 / 0.042 | 1.208 / 2.250 |
| ETT (experimental) | 0.181 [0.176, 0.184] | -61.5% | +0.0% | 0.932 | 7.6 | 1.000 / 1.292 | 1.166 / 1.166 | 0.125 / 0.167 |
| Workspace (opt-in) | 0.306 [0.306, 0.310] | -34.9% | +68.8% | 0.154 | 7.6 | 0.084 / 0.125 | 0.167 / 0.167 | 0.750 / 1.833 |
| Compact (default) | 0.470 [0.464, 0.471] | +0.0% | +159.4% | 0.152 | 7.7 | 0.084 / 0.125 | 0.167 / 0.167 | 1.042 / 2.167 |

## sparse / sustained-churn-path-v1 / N=10000 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `dd6f131aa10291a2`.

Operations: cut 862, link 38, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.210 [0.210, 0.225] | +0.0% | +42.2% | 1.661 | 7.7 | 0.125 / 0.166 | 0.250 / 0.250 | 2.916 / 7.000 |
| ETT (experimental) | 0.924 [0.880, 0.925] | +340.2% | +526.2% | 12.319 | 8.8 | 1.625 / 2.375 | 1.375 / 1.500 | 0.667 / 0.875 |
| HDT (experimental) | 0.941 [0.910, 1.308] | +348.4% | +537.8% | 8.836 | 11.0 | 1.667 / 2.500 | 1.125 / 1.166 | 0.792 / 0.958 |
| Workspace (opt-in) | 0.170 [0.169, 0.171] | -18.8% | +15.5% | 1.666 | 7.6 | 0.125 / 0.125 | 0.250 / 0.250 | 1.125 / 3.958 |
| petgraph (external) | 0.147 [0.147, 0.149] | -29.7% | +0.0% | 0.620 | 7.7 | 0.125 / 0.125 | 0.125 / 0.125 | 1.333 / 3.125 |

## sparse / sustained-churn-path-v1 / N=10000 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `dd6f131aa10291a2`.

Operations: cut 862, link 38, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 0.797 [0.756, 2.378] | +315.0% | +458.6% | 12.043 | 8.9 | 1.209 / 1.583 | 1.250 / 1.250 | 0.375 / 0.541 |
| Compact (default) | 0.192 [0.188, 0.194] | +0.0% | +34.6% | 1.631 | 7.6 | 0.125 / 0.125 | 0.209 / 0.250 | 1.542 / 4.708 |
| petgraph (external) | 0.143 [0.142, 0.143] | -25.7% | +0.0% | 0.585 | 7.6 | 0.125 / 0.125 | 0.125 / 0.125 | 1.375 / 3.042 |
| HDT (experimental) | 0.824 [0.777, 0.894] | +328.6% | +476.9% | 8.349 | 11.1 | 1.208 / 1.458 | 1.000 / 1.000 | 0.334 / 0.416 |
| Workspace (opt-in) | 0.165 [0.162, 0.167] | -14.2% | +15.5% | 1.636 | 7.6 | 0.125 / 0.125 | 0.250 / 0.250 | 1.167 / 3.958 |

## sparse / sustained-churn-path-v1 / N=10000 / q=50 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `9fd708d7c0f33425`.

Operations: cut 488, link 12, query 500 (7 true / 493 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.508 [0.505, 0.508] | -27.6% | +9.3% | 1.675 | 7.7 | 0.125 / 0.167 | 0.250 / 0.250 | 2.584 / 8.167 |
| ETT (experimental) | 0.736 [0.723, 0.811] | +4.9% | +58.4% | 12.435 | 8.8 | 1.958 / 2.584 | 1.333 / 1.333 | 0.833 / 1.375 |
| petgraph (external) | 0.464 [0.463, 0.465] | -33.7% | +0.0% | 0.639 | 7.6 | 0.125 / 0.125 | 0.125 / 0.125 | 2.583 / 5.667 |
| HDT (experimental) | 0.753 [0.700, 0.774] | +7.4% | +62.1% | 8.919 | 11.0 | 1.834 / 2.708 | 1.084 / 1.084 | 0.833 / 1.250 |
| Compact (default) | 0.701 [0.691, 0.703] | +0.0% | +50.9% | 1.676 | 7.6 | 0.125 / 0.167 | 0.250 / 0.250 | 3.292 / 9.250 |

## sparse / sustained-churn-path-v1 / N=10000 / q=50 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `9fd708d7c0f33425`.

Operations: cut 488, link 12, query 500 (7 true / 493 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 0.629 [0.554, 0.801] | -8.3% | +36.2% | 11.987 | 8.8 | 1.458 / 1.917 | 1.208 / 1.208 | 0.500 / 0.750 |
| Workspace (opt-in) | 0.499 [0.498, 0.502] | -27.4% | +7.9% | 1.663 | 7.7 | 0.125 / 0.125 | 0.250 / 0.250 | 2.625 / 8.250 |
| HDT (experimental) | 0.608 [0.604, 0.833] | -11.4% | +31.6% | 8.363 | 11.1 | 1.333 / 1.708 | 1.042 / 1.042 | 0.375 / 0.500 |
| Compact (default) | 0.687 [0.670, 0.732] | +0.0% | +48.6% | 1.632 | 7.7 | 0.125 / 0.125 | 0.250 / 0.250 | 3.250 / 9.250 |
| petgraph (external) | 0.462 [0.461, 0.467] | -32.7% | +0.0% | 0.585 | 7.6 | 0.125 / 0.125 | 0.125 / 0.125 | 2.541 / 6.291 |

## sparse / sustained-churn-path-v1 / N=10000 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 2.217 [2.203, 2.262] | -17.0% | +354.0% | 1.660 | 7.6 | 0.166 / 0.167 | — / — | 8.291 / 14.667 |
| Compact (default) | 2.672 [2.667, 2.790] | +0.0% | +447.3% | 1.684 | 7.6 | 0.167 / 0.209 | — / — | 9.125 / 16.333 |
| HDT (experimental) | 0.488 [0.488, 0.755] | -81.7% | +0.0% | 8.824 | 11.0 | 2.292 / 3.291 | — / — | 0.833 / 1.291 |
| ETT (experimental) | 0.515 [0.477, 0.655] | -80.7% | +5.5% | 12.415 | 8.8 | 2.583 / 4.125 | — / — | 0.834 / 1.458 |
| petgraph (external) | 2.131 [2.096, 2.198] | -20.3% | +336.5% | 0.619 | 7.6 | 0.125 / 0.167 | — / — | 7.750 / 11.708 |

## sparse / sustained-churn-path-v1 / N=10000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 0.337 [0.333, 0.339] | -87.0% | +0.0% | 11.917 | 8.8 | 1.500 / 1.625 | — / — | 0.375 / 0.458 |
| petgraph (external) | 2.152 [2.122, 2.733] | -17.0% | +538.8% | 0.591 | 7.6 | 0.125 / 0.167 | — / — | 8.125 / 12.167 |
| HDT (experimental) | 0.362 [0.340, 0.620] | -86.0% | +7.5% | 8.351 | 11.1 | 1.500 / 1.959 | — / — | 0.375 / 0.500 |
| Workspace (opt-in) | 2.230 [2.226, 2.237] | -14.0% | +562.0% | 1.648 | 7.6 | 0.125 / 0.208 | — / — | 8.375 / 14.833 |
| Compact (default) | 2.594 [2.589, 2.599] | +0.0% | +670.0% | 1.642 | 7.6 | 0.125 / 0.166 | — / — | 8.792 / 15.083 |

## sparse / sustained-churn-path-v1 / N=100000 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `c6d51f6b6cd4fb61`.

Operations: cut 894, link 6, query 100 (0 true / 100 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.730 [0.637, 0.773] | -13.5% | +31.4% | 18.461 | 16.6 | 0.459 / 0.667 | 0.375 / 0.375 | 15.250 / 34.291 |
| petgraph (external) | 0.555 [0.538, 0.588] | -34.2% | +0.0% | 7.065 | 13.8 | 0.334 / 0.417 | 0.166 / 0.166 | 11.542 / 26.333 |
| Compact (default) | 0.844 [0.810, 0.856] | +0.0% | +51.9% | 18.556 | 16.7 | 0.459 / 0.625 | 0.375 / 0.375 | 17.041 / 40.708 |
| ETT (experimental) | 2.381 [2.147, 3.080] | +182.2% | +328.8% | 196.757 | 57.0 | 3.833 / 5.208 | 2.459 / 2.459 | 2.458 / 3.167 |
| HDT (experimental) | 3.894 [3.799, 4.094] | +361.5% | +601.1% | 127.605 | 80.8 | 11.583 / 27.042 | 2.500 / 2.500 | 5.667 / 7.583 |

## sparse / sustained-churn-path-v1 / N=100000 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `c6d51f6b6cd4fb61`.

Operations: cut 894, link 6, query 100 (0 true / 100 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.632 [0.601, 0.641] | -18.6% | +6.3% | 18.118 | 16.6 | 0.334 / 0.417 | 0.416 / 0.416 | 14.833 / 34.875 |
| petgraph (external) | 0.595 [0.547, 0.598] | -23.4% | +0.0% | 6.651 | 13.8 | 0.375 / 0.500 | 0.125 / 0.125 | 12.167 / 27.292 |
| HDT (experimental) | 3.075 [2.886, 3.403] | +296.0% | +416.8% | 127.608 | 107.4 | 7.041 / 23.125 | 2.208 / 2.208 | 3.750 / 5.625 |
| Compact (default) | 0.777 [0.772, 0.841] | +0.0% | +30.5% | 17.946 | 16.8 | 0.416 / 0.500 | 0.334 / 0.334 | 16.708 / 36.875 |
| ETT (experimental) | 2.521 [2.378, 2.785] | +224.6% | +323.7% | 201.374 | 82.2 | 5.250 / 9.917 | 2.584 / 2.584 | 3.292 / 4.833 |

## sparse / sustained-churn-path-v1 / N=100000 / q=50 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `1779b65c977fb4b8`.

Operations: cut 498, link 2, query 500 (13 true / 487 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 2.622 [2.158, 2.793] | -43.0% | +0.0% | 206.358 | 57.0 | 7.167 / 13.209 | 2.500 / 2.500 | 5.166 / 8.959 |
| Compact (default) | 4.601 [4.570, 4.681] | +0.0% | +75.5% | 18.544 | 16.7 | 0.375 / 0.541 | 0.417 / 0.417 | 33.458 / 82.625 |
| petgraph (external) | 3.707 [3.635, 3.908] | -19.4% | +41.4% | 7.099 | 13.8 | 0.334 / 0.583 | 0.167 / 0.167 | 25.042 / 73.167 |
| HDT (experimental) | 3.261 [3.018, 3.670] | -29.1% | +24.3% | 127.335 | 80.9 | 13.167 / 28.834 | 2.167 / 2.167 | 4.375 / 8.208 |
| Workspace (opt-in) | 4.097 [4.015, 4.106] | -11.0% | +56.2% | 18.530 | 16.5 | 0.416 / 0.625 | 0.375 / 0.375 | 30.042 / 83.667 |

## sparse / sustained-churn-path-v1 / N=100000 / q=50 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `1779b65c977fb4b8`.

Operations: cut 498, link 2, query 500 (13 true / 487 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 4.553 [4.488, 4.763] | +0.0% | +103.9% | 17.886 | 16.7 | 0.292 / 0.417 | 0.417 / 0.417 | 31.417 / 81.333 |
| petgraph (external) | 3.673 [3.594, 3.726] | -19.3% | +64.5% | 6.613 | 13.8 | 0.291 / 0.375 | 0.167 / 0.167 | 25.292 / 74.250 |
| Workspace (opt-in) | 3.984 [3.930, 4.050] | -12.5% | +78.4% | 17.932 | 16.6 | 0.334 / 0.500 | 0.417 / 0.417 | 29.458 / 82.959 |
| ETT (experimental) | 2.233 [2.172, 2.661] | -51.0% | +0.0% | 198.495 | 82.2 | 6.291 / 11.458 | 2.250 / 2.250 | 4.042 / 7.250 |
| HDT (experimental) | 2.591 [2.483, 3.092] | -43.1% | +16.0% | 127.332 | 107.5 | 9.666 / 25.500 | 2.208 / 2.208 | 3.000 / 6.000 |

## sparse / sustained-churn-path-v1 / N=100000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `4f8ccd68acfa61f8`.

Operations: cut 100, link 0, query 900 (64 true / 836 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 23.679 [23.400, 23.912] | +0.0% | +1114.5% | 18.541 | 16.7 | 0.459 / 0.625 | — / — | 86.167 / 179.125 |
| ETT (experimental) | 1.950 [1.862, 2.068] | -91.8% | +0.0% | 199.843 | 56.9 | 8.250 / 10.875 | — / — | 4.792 / 7.500 |
| Workspace (opt-in) | 22.822 [22.557, 22.849] | -3.6% | +1070.5% | 18.491 | 16.6 | 0.542 / 0.917 | — / — | 88.167 / 182.250 |
| HDT (experimental) | 2.548 [2.239, 2.720] | -89.2% | +30.7% | 128.644 | 80.8 | 22.291 / 32.917 | — / — | 5.458 / 8.875 |
| petgraph (external) | 19.883 [19.714, 20.167] | -16.0% | +919.8% | 7.085 | 13.8 | 0.458 / 0.541 | — / — | 69.208 / 150.750 |

## sparse / sustained-churn-path-v1 / N=100000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `4f8ccd68acfa61f8`.

Operations: cut 100, link 0, query 900 (64 true / 836 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 2.193 [1.690, 2.867] | -90.9% | +31.9% | 127.321 | 107.5 | 19.416 / 35.583 | — / — | 4.375 / 7.292 |
| petgraph (external) | 19.589 [19.497, 19.907] | -18.3% | +1078.3% | 6.673 | 13.8 | 0.333 / 0.500 | — / — | 68.792 / 146.375 |
| Workspace (opt-in) | 22.572 [22.377, 22.708] | -5.9% | +1257.7% | 17.854 | 16.6 | 0.458 / 0.667 | — / — | 88.167 / 183.250 |
| ETT (experimental) | 1.663 [1.658, 2.605] | -93.1% | +0.0% | 199.471 | 82.2 | 5.625 / 9.583 | — / — | 3.583 / 6.208 |
| Compact (default) | 23.984 [23.523, 24.451] | +0.0% | +1342.6% | 17.990 | 16.7 | 0.500 / 0.625 | — / — | 88.458 / 178.083 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=10 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `e39886814af69da5`.

Operations: cut 900, link 0, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 4.002 [3.794, 4.008] | -19.0% | +0.0% | 74.672 | 90.7 | 1.208 / 1.500 | — / — | 132.250 / 211.292 |
| HDT (experimental) | 7.944 [5.107, 8.602] | +60.8% | +98.5% | 1911.510 | 685.6 | 17.208 / 27.292 | — / — | 9.125 / 10.166 |
| ETT (experimental) | 7.087 [3.870, 9.285] | +43.4% | +77.1% | 3076.881 | 470.5 | 15.500 / 20.250 | — / — | 8.084 / 9.625 |
| Compact (default) | 4.942 [4.855, 5.325] | +0.0% | +23.5% | 204.292 | 132.2 | 1.250 / 1.625 | — / — | 142.458 / 250.084 |
| Workspace (opt-in) | 4.383 [4.336, 4.655] | -11.3% | +9.5% | 201.712 | 136.0 | 1.000 / 1.375 | — / — | 133.000 / 341.000 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=10 / warmed

Complete: True. Winner: petgraph-dfs. Fingerprint: `e39886814af69da5`.

Operations: cut 900, link 0, query 100 (2 true / 98 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 7.920 [6.756, 22.236] | +66.7% | +106.1% | 3085.122 | 790.1 | 15.666 / 21.167 | — / — | 9.833 / 11.542 |
| HDT (experimental) | 6.539 [3.992, 8.836] | +37.7% | +70.2% | 1871.986 | 685.6 | 13.792 / 19.416 | — / — | 8.083 / 10.666 |
| petgraph (external) | 3.842 [3.567, 4.699] | -19.1% | +0.0% | 74.014 | 121.3 | 1.083 / 1.375 | — / — | 141.333 / 248.917 |
| Workspace (opt-in) | 4.638 [4.600, 4.772] | -2.4% | +20.7% | 203.315 | 145.0 | 1.042 / 1.250 | — / — | 131.667 / 333.250 |
| Compact (default) | 4.750 [4.668, 4.970] | +0.0% | +23.6% | 201.003 | 161.2 | 1.250 / 1.709 | — / — | 135.834 / 226.792 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=50 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `01a19f08e1152f91`.

Operations: cut 500, link 0, query 500 (15 true / 485 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 41.065 [40.133, 42.657] | -2.3% | +472.1% | 206.466 | 143.0 | 1.083 / 1.333 | — / — | 246.958 / 840.792 |
| ETT (experimental) | 7.178 [5.490, 8.223] | -82.9% | +0.0% | 3096.784 | 470.6 | 17.875 / 23.792 | — / — | 10.834 / 14.042 |
| petgraph (external) | 35.751 [35.000, 37.543] | -14.9% | +398.1% | 75.061 | 90.7 | 0.875 / 1.583 | — / — | 199.541 / 908.416 |
| Compact (default) | 42.025 [41.350, 42.472] | +0.0% | +485.5% | 203.487 | 148.6 | 0.958 / 1.250 | — / — | 236.166 / 773.166 |
| HDT (experimental) | 7.843 [7.105, 11.591] | -81.3% | +9.3% | 1920.374 | 684.7 | 20.292 / 35.833 | — / — | 9.958 / 14.708 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=50 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `01a19f08e1152f91`.

Operations: cut 500, link 0, query 500 (15 true / 485 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 7.256 [6.065, 7.653] | -82.8% | +5.0% | 1860.565 | 684.6 | 16.667 / 22.042 | — / — | 10.125 / 13.333 |
| Workspace (opt-in) | 40.633 [39.759, 42.202] | -3.5% | +488.0% | 200.140 | 152.0 | 1.000 / 1.292 | — / — | 237.541 / 831.750 |
| petgraph (external) | 35.841 [35.352, 37.755] | -14.9% | +418.7% | 73.880 | 121.3 | 0.833 / 1.125 | — / — | 201.167 / 921.709 |
| ETT (experimental) | 6.910 [6.008, 11.254] | -83.6% | +0.0% | 3079.370 | 786.7 | 16.417 / 23.125 | — / — | 10.750 / 13.708 |
| Compact (default) | 42.097 [41.625, 42.175] | +0.0% | +509.2% | 201.675 | 171.6 | 1.042 / 1.333 | — / — | 233.458 / 807.125 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `5097cf16db2527e7`.

Operations: cut 100, link 0, query 900 (51 true / 849 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 209.858 [205.659, 221.913] | +0.0% | +3194.3% | 203.891 | 182.0 | 1.292 / 2.042 | — / — | 797.917 / 1917.500 |
| Workspace (opt-in) | 210.642 [210.632, 217.016] | +0.4% | +3206.6% | 202.255 | 143.0 | 1.250 / 1.541 | — / — | 832.625 / 1731.625 |
| HDT (experimental) | 7.488 [6.368, 24.884] | -96.4% | +17.5% | 2057.938 | 684.9 | 23.833 / 39.583 | — / — | 11.625 / 14.250 |
| petgraph (external) | 179.283 [177.900, 182.853] | -14.6% | +2714.3% | 74.924 | 90.7 | 1.083 / 1.250 | — / — | 677.500 / 1502.458 |
| ETT (experimental) | 6.370 [4.532, 6.709] | -97.0% | +0.0% | 3140.990 | 470.5 | 18.375 / 24.458 | — / — | 11.916 / 15.500 |

## sparse / sustained-churn-path-v1 / N=1000000 / q=90 / warmed

Complete: True. Winner: hdt. Fingerprint: `5097cf16db2527e7`.

Operations: cut 100, link 0, query 900 (51 true / 849 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 211.704 [205.246, 242.161] | +1.9% | +4827.9% | 199.766 | 152.0 | 1.416 / 1.958 | — / — | 830.125 / 1717.792 |
| HDT (experimental) | 4.296 [3.015, 5.200] | -97.9% | +0.0% | 1871.582 | 685.0 | 13.292 / 19.875 | — / — | 7.584 / 10.417 |
| ETT (experimental) | 5.660 [5.053, 6.143] | -97.3% | +31.7% | 3036.784 | 790.3 | 17.542 / 22.250 | — / — | 10.917 / 14.667 |
| Compact (default) | 207.840 [207.246, 215.146] | +0.0% | +4738.0% | 201.358 | 205.9 | 1.167 / 1.750 | — / — | 791.083 / 1969.209 |
| petgraph (external) | 178.505 [177.433, 178.817] | -14.1% | +4055.2% | 74.027 | 121.2 | 0.875 / 1.291 | — / — | 659.208 / 1674.917 |

## dense / dense-bridge-churn-v1 / N=128 / q=10 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `32193df9152bed0e`.

Operations: cut 450, link 450, query 100 (79 true / 21 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.173 [0.172, 0.174] | +0.0% | +7.1% | 0.281 | 7.6 | 0.042 / 0.042 | 0.042 / 0.042 | 2.584 / 2.875 |
| Workspace (opt-in) | 0.162 [0.160, 0.181] | -6.6% | +0.0% | 0.281 | 7.6 | 0.042 / 0.042 | 0.042 / 0.042 | 2.542 / 2.916 |
| petgraph (external) | 0.902 [0.889, 0.904] | +419.9% | +456.7% | 0.403 | 7.6 | 0.042 / 0.042 | 0.125 / 0.167 | 18.167 / 20.583 |
| ETT (experimental) | 15.019 [15.018, 15.071] | +8560.6% | +9173.4% | 0.859 | 7.7 | 35.292 / 37.500 | 0.500 / 0.584 | 0.125 / 0.167 |
| HDT (experimental) | 0.838 [0.833, 0.846] | +383.1% | +417.2% | 0.827 | 7.6 | 0.584 / 0.625 | 0.334 / 0.375 | 0.125 / 0.167 |

## dense / dense-bridge-churn-v1 / N=128 / q=10 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `32193df9152bed0e`.

Operations: cut 450, link 450, query 100 (79 true / 21 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.158 [0.153, 0.170] | -14.3% | +0.0% | 0.277 | 7.6 | 0.042 / 0.042 | 0.042 / 0.042 | 2.417 / 2.625 |
| Compact (default) | 0.184 [0.172, 0.211] | +0.0% | +16.7% | 0.276 | 7.6 | 0.042 / 0.042 | 0.042 / 0.083 | 3.000 / 3.125 |
| petgraph (external) | 0.906 [0.888, 0.906] | +392.8% | +474.9% | 0.371 | 7.6 | 0.042 / 0.042 | 0.125 / 0.167 | 18.375 / 21.000 |
| ETT (experimental) | 15.059 [15.017, 15.159] | +8093.8% | +9459.0% | 0.806 | 7.6 | 34.709 / 38.208 | 0.500 / 0.625 | 0.125 / 0.125 |
| HDT (experimental) | 0.837 [0.835, 0.848] | +355.2% | +431.1% | 0.789 | 7.6 | 0.542 / 0.584 | 0.334 / 0.334 | 0.125 / 0.125 |

## dense / dense-bridge-churn-v1 / N=128 / q=50 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `5c6a1202fe78f155`.

Operations: cut 250, link 250, query 500 (379 true / 121 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 4.588 [4.582, 4.697] | +532.0% | +579.1% | 0.410 | 7.6 | 0.042 / 0.042 | 0.167 / 0.167 | 19.792 / 20.958 |
| ETT (experimental) | 8.532 [8.509, 8.562] | +1075.3% | +1162.9% | 0.844 | 7.6 | 36.958 / 46.083 | 0.583 / 0.833 | 0.125 / 0.167 |
| Compact (default) | 0.726 [0.716, 0.741] | +0.0% | +7.5% | 0.287 | 7.6 | 0.042 / 0.042 | 0.042 / 0.042 | 2.583 / 2.875 |
| Workspace (opt-in) | 0.676 [0.669, 0.677] | -6.9% | +0.0% | 0.275 | 7.6 | 0.042 / 0.042 | 0.042 / 0.084 | 2.500 / 2.542 |
| HDT (experimental) | 0.700 [0.697, 0.700] | -3.5% | +3.7% | 0.837 | 7.6 | 0.583 / 0.625 | 0.334 / 0.375 | 0.125 / 0.125 |

## dense / dense-bridge-churn-v1 / N=128 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `5c6a1202fe78f155`.

Operations: cut 250, link 250, query 500 (379 true / 121 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 4.646 [4.645, 4.715] | +549.2% | +605.7% | 0.383 | 7.6 | 0.042 / 0.042 | 0.167 / 0.167 | 20.000 / 21.125 |
| Workspace (opt-in) | 0.658 [0.629, 0.676] | -8.0% | +0.0% | 0.279 | 7.7 | 0.042 / 0.042 | 0.042 / 0.083 | 2.500 / 2.500 |
| ETT (experimental) | 8.418 [8.402, 8.463] | +1076.4% | +1178.7% | 0.807 | 7.6 | 34.000 / 37.084 | 0.541 / 0.667 | 0.125 / 0.125 |
| Compact (default) | 0.716 [0.713, 0.717] | +0.0% | +8.7% | 0.274 | 7.7 | 0.042 / 0.042 | 0.042 / 0.042 | 2.542 / 2.584 |
| HDT (experimental) | 0.700 [0.694, 0.702] | -2.2% | +6.3% | 0.796 | 7.6 | 0.542 / 0.625 | 0.334 / 0.334 | 0.084 / 0.125 |

## dense / dense-bridge-churn-v1 / N=128 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `10e7f17d851f5dd3`.

Operations: cut 50, link 50, query 900 (687 true / 213 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.199 [1.195, 1.284] | +0.0% | +116.9% | 0.284 | 7.6 | 0.083 / 0.291 | 0.042 / 0.125 | 2.542 / 2.625 |
| petgraph (external) | 8.172 [8.110, 8.360] | +581.8% | +1378.6% | 0.392 | 7.6 | 0.042 / 0.167 | 0.167 / 0.208 | 18.875 / 20.625 |
| ETT (experimental) | 1.766 [1.763, 1.771] | +47.4% | +219.6% | 0.863 | 7.6 | 34.083 / 49.000 | 0.542 / 0.834 | 0.125 / 0.125 |
| HDT (experimental) | 0.553 [0.551, 0.569] | -53.9% | +0.0% | 0.823 | 7.6 | 0.625 / 429.791 | 0.334 / 0.958 | 0.084 / 0.125 |
| Workspace (opt-in) | 1.111 [1.110, 1.113] | -7.3% | +101.0% | 0.275 | 7.6 | 0.042 / 0.291 | 0.084 / 0.125 | 2.500 / 2.500 |

## dense / dense-bridge-churn-v1 / N=128 / q=90 / warmed

Complete: True. Winner: hdt. Fingerprint: `10e7f17d851f5dd3`.

Operations: cut 50, link 50, query 900 (687 true / 213 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 1.732 [1.725, 1.745] | +43.5% | +211.0% | 0.820 | 7.7 | 33.084 / 34.708 | 0.542 / 0.583 | 0.084 / 0.125 |
| petgraph (external) | 8.150 [8.141, 8.352] | +575.2% | +1363.5% | 0.385 | 7.6 | 0.042 / 0.084 | 0.167 / 0.208 | 18.958 / 20.375 |
| Workspace (opt-in) | 1.035 [1.031, 1.037] | -14.3% | +85.8% | 0.280 | 7.6 | 0.042 / 0.042 | 0.083 / 0.084 | 2.333 / 2.334 |
| Compact (default) | 1.207 [1.187, 1.233] | +0.0% | +116.8% | 0.275 | 7.7 | 0.042 / 0.042 | 0.084 / 0.125 | 2.542 / 2.666 |
| HDT (experimental) | 0.557 [0.547, 0.565] | -53.9% | +0.0% | 0.794 | 7.7 | 0.625 / 437.292 | 0.334 / 0.583 | 0.084 / 0.084 |

## dense / dense-bridge-churn-v1 / N=512 / q=10 / fresh

Complete: True. Winner: compact-bfs. Fingerprint: `9e6ef6a952b08411`.

Operations: cut 450, link 450, query 100 (77 true / 23 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 1.949 [1.948, 1.954] | +0.0% | +0.0% | 4.752 | 7.6 | 0.083 / 0.084 | 0.084 / 0.084 | 37.333 / 38.875 |
| HDT (experimental) | 9.308 [8.945, 9.764] | +377.7% | +377.7% | 14.269 | 13.6 | 0.709 / 0.750 | 0.459 / 0.459 | 0.500 / 0.791 |
| ETT (experimental) | 343.590 [341.649, 345.001] | +17532.8% | +17532.8% | 15.073 | 12.1 | 785.541 / 817.167 | 0.959 / 1.750 | 1.000 / 1.500 |
| Workspace (opt-in) | 2.154 [2.091, 2.180] | +10.6% | +10.6% | 4.855 | 7.6 | 0.084 / 0.084 | 0.084 / 0.125 | 43.875 / 45.833 |
| petgraph (external) | 18.747 [17.399, 18.969] | +862.1% | +862.1% | 20.459 | 7.6 | 0.042 / 0.042 | 0.542 / 0.583 | 390.000 / 443.000 |

## dense / dense-bridge-churn-v1 / N=512 / q=10 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `9e6ef6a952b08411`.

Operations: cut 450, link 450, query 100 (77 true / 23 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 8.894 [8.808, 9.084] | +355.4% | +360.6% | 13.660 | 13.7 | 0.709 / 0.709 | 0.417 / 0.458 | 0.291 / 0.375 |
| ETT (experimental) | 342.882 [342.358, 343.376] | +17455.2% | +17656.7% | 14.373 | 12.1 | 782.958 / 807.000 | 0.958 / 1.375 | 1.041 / 1.625 |
| petgraph (external) | 18.894 [17.412, 19.020] | +867.4% | +878.5% | 20.471 | 7.6 | 0.042 / 0.042 | 0.541 / 0.625 | 393.917 / 427.875 |
| Workspace (opt-in) | 1.931 [1.927, 2.083] | -1.1% | +0.0% | 4.715 | 7.6 | 0.083 / 0.084 | 0.084 / 0.084 | 37.125 / 38.625 |
| Compact (default) | 1.953 [1.951, 1.959] | +0.0% | +1.1% | 4.719 | 7.6 | 0.084 / 0.084 | 0.084 / 0.125 | 37.375 / 40.166 |

## dense / dense-bridge-churn-v1 / N=512 / q=50 / fresh

Complete: True. Winner: hdt. Fingerprint: `395736583f2619ca`.

Operations: cut 250, link 250, query 500 (369 true / 131 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 8.874 [8.711, 9.201] | -8.3% | +0.0% | 14.225 | 13.6 | 0.709 / 0.958 | 0.417 / 0.625 | 0.167 / 0.292 |
| ETT (experimental) | 191.417 [190.691, 192.389] | +1878.5% | +2057.1% | 14.898 | 12.1 | 791.834 / 892.709 | 1.041 / 2.417 | 0.625 / 1.125 |
| Compact (default) | 9.675 [9.621, 9.684] | +0.0% | +9.0% | 4.803 | 7.6 | 0.084 / 0.125 | 0.125 / 0.167 | 37.875 / 40.375 |
| petgraph (external) | 98.827 [97.320, 99.674] | +921.5% | +1013.7% | 20.479 | 7.7 | 0.042 / 0.167 | 0.583 / 0.708 | 389.792 / 443.625 |
| Workspace (opt-in) | 10.300 [10.300, 10.621] | +6.5% | +16.1% | 4.789 | 7.6 | 0.084 / 0.125 | 0.125 / 0.125 | 40.250 / 40.542 |

## dense / dense-bridge-churn-v1 / N=512 / q=50 / warmed

Complete: True. Winner: hdt. Fingerprint: `395736583f2619ca`.

Operations: cut 250, link 250, query 500 (369 true / 131 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 8.865 [8.597, 8.924] | -8.2% | +0.0% | 13.580 | 13.8 | 0.709 / 0.792 | 0.417 / 0.459 | 0.209 / 0.417 |
| ETT (experimental) | 191.144 [190.590, 191.290] | +1879.3% | +2056.3% | 14.376 | 12.1 | 788.041 / 816.708 | 0.917 / 1.666 | 0.542 / 1.042 |
| petgraph (external) | 101.285 [99.626, 102.021] | +948.8% | +1042.6% | 20.375 | 7.6 | 0.042 / 0.084 | 0.542 / 0.625 | 399.291 / 452.458 |
| Workspace (opt-in) | 9.609 [9.500, 9.851] | -0.5% | +8.4% | 4.705 | 7.6 | 0.084 / 0.125 | 0.125 / 0.125 | 37.750 / 41.125 |
| Compact (default) | 9.657 [9.610, 9.751] | +0.0% | +8.9% | 4.694 | 7.6 | 0.084 / 0.084 | 0.125 / 0.125 | 37.750 / 39.833 |

## dense / dense-bridge-churn-v1 / N=512 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `a9d909ec7676fff9`.

Operations: cut 50, link 50, query 900 (667 true / 233 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 8.811 [8.662, 9.707] | -49.8% | +0.0% | 14.311 | 13.6 | 0.917 / 8635.417 | 0.542 / 1.458 | 0.167 / 0.292 |
| ETT (experimental) | 38.435 [38.141, 38.547] | +118.9% | +336.2% | 15.024 | 12.1 | 799.917 / 873.958 | 1.250 / 2.459 | 0.209 / 0.333 |
| Compact (default) | 17.555 [17.239, 17.663] | +0.0% | +99.2% | 4.966 | 7.7 | 0.209 / 0.375 | 0.208 / 0.583 | 39.083 / 42.958 |
| Workspace (opt-in) | 18.523 [18.457, 19.878] | +5.5% | +110.2% | 4.813 | 7.6 | 0.208 / 0.334 | 0.208 / 0.500 | 40.542 / 44.000 |
| petgraph (external) | 177.965 [173.792, 179.748] | +913.8% | +1919.8% | 20.467 | 7.6 | 0.292 / 0.917 | 0.834 / 0.959 | 401.125 / 460.834 |

## dense / dense-bridge-churn-v1 / N=512 / q=90 / warmed

Complete: True. Winner: hdt. Fingerprint: `a9d909ec7676fff9`.

Operations: cut 50, link 50, query 900 (667 true / 233 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 8.517 [8.385, 8.624] | -51.0% | +0.0% | 13.654 | 13.8 | 0.792 / 8347.375 | 0.459 / 1.750 | 0.166 / 0.167 |
| petgraph (external) | 174.487 [173.691, 179.880] | +904.7% | +1948.7% | 20.328 | 7.6 | 0.167 / 0.334 | 0.584 / 0.834 | 395.250 / 447.667 |
| ETT (experimental) | 38.311 [38.266, 38.434] | +120.6% | +349.8% | 14.374 | 12.2 | 799.541 / 859.375 | 1.041 / 2.292 | 0.167 / 0.208 |
| Workspace (opt-in) | 18.687 [18.669, 18.688] | +7.6% | +119.4% | 4.876 | 7.6 | 0.167 / 0.208 | 0.209 / 0.333 | 41.416 / 45.292 |
| Compact (default) | 17.366 [17.184, 17.421] | +0.0% | +103.9% | 4.681 | 7.6 | 0.125 / 0.125 | 0.166 / 0.208 | 37.959 / 41.750 |

## dense / redundant-bridge-churn-v1 / N=128 / q=10 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `dd724154676b1772`.

Operations: cut 450, link 450, query 100 (89 true / 11 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 0.831 [0.818, 0.832] | +355.7% | +376.0% | 0.815 | 7.6 | 1.166 / 1.250 | 0.583 / 0.625 | 0.125 / 0.167 |
| petgraph (external) | 1.077 [1.075, 1.090] | +490.1% | +516.4% | 0.403 | 7.6 | 0.042 / 0.042 | 0.125 / 0.167 | 19.792 / 20.833 |
| Workspace (opt-in) | 0.175 [0.167, 0.176] | -4.3% | +0.0% | 0.278 | 7.6 | 0.042 / 0.042 | 0.042 / 0.083 | 2.792 / 2.875 |
| Compact (default) | 0.182 [0.180, 0.183] | +0.0% | +4.5% | 0.273 | 7.6 | 0.042 / 0.042 | 0.042 / 0.084 | 2.667 / 3.042 |
| ETT (experimental) | 9.833 [9.746, 10.078] | +5289.1% | +5529.5% | 0.892 | 7.6 | 34.292 / 40.791 | 0.708 / 0.792 | 0.166 / 0.333 |

## dense / redundant-bridge-churn-v1 / N=128 / q=10 / warmed

Complete: True. Winner: compact-bfs. Fingerprint: `dd724154676b1772`.

Operations: cut 450, link 450, query 100 (89 true / 11 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 0.179 [0.177, 0.179] | +0.7% | +0.7% | 0.273 | 7.6 | 0.042 / 0.042 | 0.042 / 0.084 | 2.791 / 2.875 |
| HDT (experimental) | 0.828 [0.826, 0.828] | +366.4% | +366.4% | 0.812 | 7.6 | 1.125 / 1.167 | 0.583 / 0.584 | 0.125 / 0.125 |
| ETT (experimental) | 9.833 [9.719, 9.879] | +5437.3% | +5437.3% | 0.815 | 7.7 | 34.000 / 37.125 | 0.708 / 0.750 | 0.125 / 0.167 |
| petgraph (external) | 1.064 [1.052, 1.068] | +499.2% | +499.2% | 0.375 | 7.6 | 0.042 / 0.042 | 0.125 / 0.167 | 19.750 / 20.625 |
| Compact (default) | 0.178 [0.177, 0.186] | +0.0% | +0.0% | 0.272 | 7.6 | 0.042 / 0.042 | 0.042 / 0.083 | 2.584 / 2.708 |

## dense / redundant-bridge-churn-v1 / N=128 / q=50 / fresh

Complete: True. Winner: hdt. Fingerprint: `9e272d8635152beb`.

Operations: cut 251, link 249, query 500 (431 true / 69 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 0.721 [0.717, 0.741] | +0.0% | +2.3% | 0.278 | 7.6 | 0.042 / 0.083 | 0.042 / 0.084 | 2.583 / 2.708 |
| HDT (experimental) | 0.704 [0.693, 0.734] | -2.3% | +0.0% | 0.831 | 7.7 | 1.167 / 1.292 | 0.583 / 0.584 | 0.084 / 0.125 |
| Workspace (opt-in) | 0.737 [0.664, 0.739] | +2.3% | +4.6% | 0.275 | 7.7 | 0.042 / 0.083 | 0.083 / 0.084 | 2.792 / 2.834 |
| petgraph (external) | 5.211 [5.006, 5.247] | +622.9% | +639.8% | 0.393 | 7.6 | 0.042 / 0.042 | 0.167 / 0.208 | 20.375 / 21.875 |
| ETT (experimental) | 5.687 [5.639, 5.721] | +689.0% | +707.4% | 0.851 | 7.6 | 34.042 / 38.667 | 0.708 / 0.750 | 0.125 / 0.125 |

## dense / redundant-bridge-churn-v1 / N=128 / q=50 / warmed

Complete: True. Winner: hdt. Fingerprint: `9e272d8635152beb`.

Operations: cut 251, link 249, query 500 (431 true / 69 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 4.981 [4.965, 5.027] | +592.2% | +611.5% | 0.384 | 7.6 | 0.042 / 0.042 | 0.167 / 0.167 | 19.500 / 20.750 |
| Workspace (opt-in) | 0.734 [0.722, 0.736] | +2.0% | +4.9% | 0.272 | 7.6 | 0.042 / 0.042 | 0.083 / 0.084 | 2.792 / 2.833 |
| Compact (default) | 0.720 [0.718, 0.749] | +0.0% | +2.8% | 0.272 | 7.6 | 0.042 / 0.042 | 0.083 / 0.084 | 2.584 / 2.666 |
| HDT (experimental) | 0.700 [0.692, 0.703] | -2.7% | +0.0% | 0.790 | 7.6 | 1.125 / 1.250 | 0.583 / 0.584 | 0.084 / 0.125 |
| ETT (experimental) | 5.627 [5.612, 5.688] | +682.0% | +703.8% | 0.818 | 7.6 | 33.958 / 38.666 | 0.708 / 0.709 | 0.125 / 0.125 |

## dense / redundant-bridge-churn-v1 / N=128 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `8a9d2267e1e32d39`.

Operations: cut 51, link 49, query 900 (791 true / 109 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 1.218 [1.103, 1.280] | +0.8% | +120.5% | 0.288 | 7.6 | 0.084 / 0.292 | 0.084 / 0.125 | 2.792 / 2.834 |
| petgraph (external) | 9.074 [8.993, 9.152] | +651.4% | +1542.5% | 0.392 | 7.6 | 0.083 / 0.167 | 0.208 / 0.292 | 19.791 / 20.792 |
| Compact (default) | 1.208 [1.199, 1.213] | +0.0% | +118.6% | 0.273 | 7.6 | 0.083 / 0.292 | 0.084 / 0.125 | 2.583 / 2.625 |
| ETT (experimental) | 1.207 [1.185, 1.249] | -0.0% | +118.5% | 0.852 | 7.6 | 38.958 / 48.250 | 0.792 / 0.875 | 0.125 / 0.125 |
| HDT (experimental) | 0.552 [0.551, 0.596] | -54.3% | +0.0% | 0.820 | 7.6 | 1.792 / 425.209 | 0.625 / 0.875 | 0.084 / 0.125 |

## dense / redundant-bridge-churn-v1 / N=128 / q=90 / warmed

Complete: True. Winner: hdt. Fingerprint: `8a9d2267e1e32d39`.

Operations: cut 51, link 49, query 900 (791 true / 109 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 1.164 [1.161, 1.274] | -5.5% | +95.6% | 0.854 | 7.6 | 35.000 / 38.292 | 0.750 / 0.792 | 0.084 / 0.125 |
| Workspace (opt-in) | 1.229 [1.035, 1.250] | -0.2% | +106.5% | 0.275 | 7.6 | 0.042 / 0.042 | 0.084 / 0.084 | 2.792 / 2.875 |
| Compact (default) | 1.232 [1.196, 1.243] | +0.0% | +107.0% | 0.275 | 7.6 | 0.083 / 0.208 | 0.084 / 0.292 | 2.583 / 3.042 |
| HDT (experimental) | 0.595 [0.538, 0.596] | -51.7% | +0.0% | 0.812 | 7.6 | 1.417 / 462.917 | 0.667 / 0.709 | 0.084 / 0.125 |
| petgraph (external) | 9.132 [8.936, 9.239] | +641.1% | +1434.3% | 0.382 | 7.7 | 0.042 / 0.125 | 0.167 / 0.250 | 19.958 / 20.917 |

## dense / redundant-bridge-churn-v1 / N=512 / q=10 / fresh

Complete: True. Winner: compact-bfs. Fingerprint: `c47db0e54795605a`.

Operations: cut 450, link 450, query 100 (85 true / 15 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 218.904 [218.357, 220.001] | +10972.8% | +10972.8% | 14.982 | 12.1 | 780.833 / 835.125 | 1.125 / 1.667 | 0.792 / 1.083 |
| Compact (default) | 1.977 [1.966, 1.985] | +0.0% | +0.0% | 4.888 | 7.6 | 0.084 / 0.125 | 0.084 / 0.125 | 37.875 / 40.167 |
| HDT (experimental) | 9.095 [8.975, 9.163] | +360.0% | +360.0% | 14.350 | 13.6 | 1.541 / 1.625 | 0.709 / 0.792 | 0.375 / 0.458 |
| Workspace (opt-in) | 2.093 [2.088, 2.095] | +5.9% | +5.9% | 4.802 | 7.6 | 0.084 / 0.084 | 0.084 / 0.125 | 40.375 / 40.917 |
| petgraph (external) | 20.345 [19.234, 20.857] | +929.1% | +929.1% | 20.608 | 7.6 | 0.042 / 0.084 | 0.542 / 0.625 | 420.084 / 455.042 |

## dense / redundant-bridge-churn-v1 / N=512 / q=10 / warmed

Complete: True. Winner: compact-bfs. Fingerprint: `c47db0e54795605a`.

Operations: cut 450, link 450, query 100 (85 true / 15 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 9.039 [8.725, 9.148] | +355.9% | +355.9% | 13.722 | 13.7 | 1.541 / 1.625 | 0.709 / 0.750 | 0.292 / 0.417 |
| ETT (experimental) | 221.373 [219.316, 451.120] | +11065.2% | +11065.2% | 14.477 | 12.1 | 803.458 / 867.083 | 1.208 / 1.959 | 0.958 / 1.459 |
| Compact (default) | 1.983 [1.949, 1.988] | +0.0% | +0.0% | 4.622 | 7.6 | 0.084 / 0.084 | 0.084 / 0.125 | 38.125 / 40.625 |
| Workspace (opt-in) | 2.102 [1.933, 2.128] | +6.0% | +6.0% | 4.678 | 7.6 | 0.084 / 0.125 | 0.084 / 0.125 | 40.458 / 43.167 |
| petgraph (external) | 19.806 [19.528, 20.638] | +898.9% | +898.9% | 20.381 | 7.6 | 0.042 / 0.042 | 0.542 / 0.583 | 402.417 / 453.750 |

## dense / redundant-bridge-churn-v1 / N=512 / q=50 / fresh

Complete: True. Winner: hdt. Fingerprint: `d707059d04b0de28`.

Operations: cut 251, link 249, query 500 (434 true / 66 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ETT (experimental) | 126.203 [125.863, 126.866] | +1193.6% | +1312.2% | 14.869 | 12.1 | 786.042 / 833.667 | 1.209 / 2.250 | 0.542 / 0.833 |
| petgraph (external) | 103.858 [102.761, 104.916] | +964.6% | +1062.1% | 20.560 | 7.6 | 0.083 / 0.250 | 0.583 / 0.667 | 430.375 / 460.167 |
| Compact (default) | 9.756 [9.698, 9.764] | +0.0% | +9.2% | 4.872 | 7.6 | 0.125 / 0.208 | 0.125 / 0.208 | 37.916 / 41.042 |
| Workspace (opt-in) | 10.434 [10.391, 10.457] | +7.0% | +16.8% | 4.832 | 7.6 | 0.125 / 0.208 | 0.125 / 0.208 | 41.583 / 45.125 |
| HDT (experimental) | 8.937 [8.936, 19.807] | -8.4% | +0.0% | 14.194 | 13.6 | 1.542 / 1.708 | 0.750 / 0.750 | 0.250 / 0.458 |

## dense / redundant-bridge-churn-v1 / N=512 / q=50 / warmed

Complete: True. Winner: hdt. Fingerprint: `d707059d04b0de28`.

Operations: cut 251, link 249, query 500 (434 true / 66 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 105.931 [103.072, 106.796] | +994.1% | +1089.5% | 20.399 | 7.7 | 0.042 / 0.167 | 0.584 / 0.667 | 439.709 / 475.792 |
| Workspace (opt-in) | 10.346 [9.537, 10.548] | +6.9% | +16.2% | 4.667 | 7.6 | 0.084 / 0.125 | 0.125 / 0.125 | 40.416 / 42.292 |
| Compact (default) | 9.682 [9.635, 9.701] | +0.0% | +8.7% | 4.703 | 7.6 | 0.084 / 0.125 | 0.125 / 0.125 | 37.459 / 40.083 |
| HDT (experimental) | 8.905 [8.698, 9.088] | -8.0% | +0.0% | 13.619 | 13.8 | 1.500 / 2.250 | 0.709 / 0.750 | 0.209 / 0.375 |
| ETT (experimental) | 125.686 [125.451, 126.432] | +1198.1% | +1311.3% | 14.349 | 12.2 | 782.792 / 813.584 | 1.125 / 1.375 | 0.459 / 0.709 |

## dense / redundant-bridge-churn-v1 / N=512 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `5d614f64ff1f8734`.

Operations: cut 51, link 49, query 900 (799 true / 101 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 183.395 [182.234, 184.516] | +968.6% | +1970.9% | 20.534 | 7.6 | 0.250 / 0.500 | 0.625 / 0.875 | 423.709 / 465.375 |
| Workspace (opt-in) | 18.339 [18.329, 18.347] | +6.9% | +107.1% | 4.873 | 7.6 | 0.208 / 0.333 | 0.208 / 0.292 | 40.459 / 43.208 |
| HDT (experimental) | 8.856 [8.778, 8.862] | -48.4% | +0.0% | 14.182 | 13.7 | 2.291 / 8660.833 | 0.834 / 1.416 | 0.167 / 0.417 |
| ETT (experimental) | 24.122 [24.122, 24.269] | +40.6% | +172.4% | 14.888 | 12.1 | 801.250 / 872.166 | 1.292 / 1.458 | 0.167 / 0.209 |
| Compact (default) | 17.162 [17.111, 17.191] | +0.0% | +93.8% | 4.776 | 7.6 | 0.208 / 0.375 | 0.208 / 0.458 | 38.000 / 41.125 |

## dense / redundant-bridge-churn-v1 / N=512 / q=90 / warmed

Complete: True. Winner: hdt. Fingerprint: `5d614f64ff1f8734`.

Operations: cut 51, link 49, query 900 (799 true / 101 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 184.300 [180.829, 185.649] | +977.5% | +2018.5% | 20.289 | 7.6 | 0.208 / 0.833 | 0.625 / 0.708 | 422.333 / 466.292 |
| ETT (experimental) | 24.063 [23.865, 26.937] | +40.7% | +176.6% | 14.470 | 12.2 | 820.375 / 861.583 | 1.208 / 2.083 | 0.167 / 0.250 |
| Compact (default) | 17.104 [17.063, 17.251] | +0.0% | +96.6% | 4.652 | 7.6 | 0.167 / 0.292 | 0.209 / 0.375 | 37.375 / 41.166 |
| HDT (experimental) | 8.700 [8.603, 8.800] | -49.1% | +0.0% | 13.573 | 13.7 | 2.167 / 8518.500 | 0.750 / 1.500 | 0.208 / 0.458 |
| Workspace (opt-in) | 18.336 [16.973, 18.697] | +7.2% | +110.8% | 4.767 | 7.7 | 0.167 / 0.292 | 0.208 / 0.334 | 40.375 / 44.042 |

## cogentco / topology-zoo-outages-v1 / N=197 / q=None / fresh

Complete: True. Winner: ett-scan. Fingerprint: `42529c7c67c5077b`.

Operations: cut 99, link 99, query 1800 (732 true / 1068 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.715 [0.711, 0.759] | -34.2% | +82.0% | 0.026 | 7.6 | 0.125 / 0.125 | 0.084 / 0.084 | 1.042 / 1.375 |
| Compact (default) | 1.088 [1.079, 1.097] | +0.0% | +176.7% | 0.051 | 7.6 | 0.125 / 0.209 | 0.125 / 0.167 | 1.708 / 2.167 |
| ETT (experimental) | 0.393 [0.357, 0.402] | -63.9% | +0.0% | 0.192 | 7.6 | 2.958 / 3.875 | 1.334 / 1.458 | 0.125 / 0.167 |
| Workspace (opt-in) | 0.727 [0.727, 0.731] | -33.1% | +85.0% | 0.048 | 7.6 | 0.125 / 0.292 | 0.167 / 0.167 | 1.292 / 1.750 |
| HDT (experimental) | 0.495 [0.492, 0.504] | -54.5% | +25.8% | 0.159 | 7.7 | 10.541 / 22.583 | 0.958 / 1.125 | 0.125 / 0.125 |

## cogentco / topology-zoo-outages-v1 / N=197 / q=None / warmed

Complete: True. Winner: ett-scan. Fingerprint: `42529c7c67c5077b`.

Operations: cut 99, link 99, query 1800 (732 true / 1068 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 0.648 [0.645, 0.698] | -32.2% | +106.8% | 0.017 | 7.6 | 0.084 / 0.084 | 0.084 / 0.084 | 0.959 / 1.125 |
| Workspace (opt-in) | 0.584 [0.581, 0.603] | -39.0% | +86.2% | 0.038 | 7.6 | 0.084 / 0.125 | 0.125 / 0.167 | 1.000 / 1.334 |
| Compact (default) | 0.957 [0.948, 1.007] | +0.0% | +205.1% | 0.037 | 7.7 | 0.084 / 0.125 | 0.125 / 0.125 | 1.417 / 1.875 |
| ETT (experimental) | 0.314 [0.313, 0.316] | -67.2% | +0.0% | 0.144 | 7.6 | 2.375 / 2.875 | 1.167 / 1.292 | 0.084 / 0.125 |
| HDT (experimental) | 0.433 [0.433, 0.513] | -54.7% | +38.2% | 0.122 | 7.6 | 8.959 / 19.833 | 0.875 / 1.042 | 0.125 / 0.125 |

## repeats / sustained-churn-blocks-v1 / N=10000 / q=90 / fresh

Complete: True. Winner: ett-scan. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false), additional repeats 1800.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 11.600 [11.559, 11.605] | +37.7% | +1352.5% | 0.679 | 7.6 | 0.167 / 0.208 | 0.125 / 0.125 | 12.791 / 19.166 |
| HDT (experimental) | 17.813 [17.645, 17.924] | +111.4% | +2130.6% | 9.298 | 23.3 | 730.417 / 2748.958 | 2.375 / 2.375 | 0.750 / 1.291 |
| Workspace (opt-in) | 6.913 [6.896, 7.116] | -18.0% | +765.6% | 1.802 | 7.6 | 0.250 / 0.542 | 0.250 / 0.250 | 7.708 / 11.500 |
| Compact (default) | 8.426 [8.397, 8.479] | +0.0% | +955.1% | 1.779 | 7.7 | 0.209 / 0.291 | 0.250 / 0.250 | 8.375 / 12.584 |
| ETT (experimental) | 0.799 [0.779, 0.835] | -90.5% | +0.0% | 12.806 | 9.0 | 8.500 / 28.208 | 1.750 / 1.750 | 0.333 / 0.417 |

## repeats / sustained-churn-blocks-v1 / N=10000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `ac238bba1870db53`.

Operations: cut 94, link 6, query 900 (99 true / 801 false), additional repeats 1800.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 17.851 [17.401, 17.861] | +114.1% | +2380.1% | 8.903 | 24.0 | 665.292 / 2783.916 | 5.417 / 5.417 | 1.125 / 1.708 |
| Compact (default) | 8.336 [8.308, 8.574] | +0.0% | +1058.1% | 1.722 | 7.7 | 0.167 / 0.334 | 0.209 / 0.209 | 8.334 / 12.375 |
| Workspace (opt-in) | 6.865 [6.814, 7.045] | -17.6% | +853.8% | 1.737 | 7.6 | 0.209 / 0.291 | 0.375 / 0.375 | 7.541 / 11.500 |
| petgraph (external) | 14.445 [12.805, 14.634] | +73.3% | +1906.9% | 0.618 | 7.7 | 0.167 / 0.375 | 0.167 / 0.167 | 15.667 / 23.542 |
| ETT (experimental) | 0.720 [0.697, 0.799] | -91.4% | +0.0% | 12.173 | 9.1 | 8.333 / 24.083 | 1.583 / 1.583 | 0.292 / 0.375 |

## repeats / sustained-churn-path-v1 / N=10000 / q=90 / fresh

Complete: True. Winner: hdt. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false), additional repeats 1800.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| HDT (experimental) | 0.702 [0.658, 0.729] | -90.9% | +0.0% | 8.962 | 11.0 | 2.583 / 3.667 | — / — | 0.833 / 1.333 |
| Workspace (opt-in) | 6.433 [6.384, 6.466] | -16.8% | +816.0% | 1.677 | 7.6 | 0.167 / 0.209 | — / — | 8.375 / 14.833 |
| Compact (default) | 7.735 [7.701, 7.758] | +0.0% | +1001.3% | 1.698 | 7.6 | 0.208 / 0.250 | — / — | 9.083 / 15.708 |
| petgraph (external) | 6.172 [6.142, 6.175] | -20.2% | +778.9% | 0.630 | 7.6 | 0.167 / 0.208 | — / — | 7.958 / 11.833 |
| ETT (experimental) | 0.719 [0.643, 0.729] | -90.7% | +2.4% | 12.403 | 8.8 | 2.333 / 3.167 | — / — | 0.791 / 1.250 |

## repeats / sustained-churn-path-v1 / N=10000 / q=90 / warmed

Complete: True. Winner: ett-scan. Fingerprint: `af00ae89d7fcadb1`.

Operations: cut 100, link 0, query 900 (56 true / 844 false), additional repeats 1800.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 6.405 [6.340, 6.440] | -16.8% | +1144.2% | 1.638 | 7.6 | 0.166 / 0.209 | — / — | 8.375 / 14.500 |
| petgraph (external) | 6.557 [6.176, 71.298] | -14.8% | +1173.9% | 0.587 | 7.6 | 0.208 / 0.333 | — / — | 8.250 / 14.541 |
| Compact (default) | 7.696 [7.624, 7.822] | +0.0% | +1395.0% | 1.641 | 7.7 | 0.166 / 0.209 | — / — | 8.959 / 15.208 |
| HDT (experimental) | 0.556 [0.492, 0.568] | -92.8% | +7.9% | 8.452 | 11.1 | 1.667 / 2.042 | — / — | 0.375 / 0.459 |
| ETT (experimental) | 0.515 [0.491, 0.640] | -93.3% | +0.0% | 12.030 | 8.8 | 1.583 / 1.916 | — / — | 0.333 / 0.417 |

## extreme / sustained-churn-blocks-v1 / N=10000000 / q=50 / fresh

Complete: True. Winner: compact-workspace. Fingerprint: `8fe7485009a30ef9`.

Operations: cut 500, link 0, query 500 (15 true / 485 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Workspace (opt-in) | 414.583 [414.583, 414.583] | -33.1% | +0.0% | 2995.932 | 1345.5 | 2.000 / 2.416 | — / — | 3147.417 / 8275.458 |
| petgraph (external) | 714.689 [714.689, 714.689] | +15.3% | +72.4% | 895.979 | 932.6 | 4.209 / 6.083 | — / — | 4946.042 / 15538.167 |
| Compact (default) | 619.909 [619.909, 619.909] | +0.0% | +49.5% | 2462.778 | 1429.2 | 2.417 / 4.875 | — / — | 4177.042 / 11458.083 |

## extreme / sustained-churn-blocks-v1 / N=10000000 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `8fe7485009a30ef9`.

Operations: cut 500, link 0, query 500 (15 true / 485 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Compact (default) | 561.255 [561.255, 561.255] | +0.0% | +11.6% | 2421.656 | 1674.5 | 5.750 / 7.083 | — / — | 4169.458 / 10279.541 |
| petgraph (external) | 684.523 [684.523, 684.523] | +22.0% | +36.1% | 947.458 | 1257.5 | 1.708 / 5.708 | — / — | 5057.958 / 14579.500 |
| Workspace (opt-in) | 503.139 [503.139, 503.139] | -10.4% | +0.0% | 2744.441 | 1576.9 | 3.500 / 5.667 | — / — | 3561.000 / 15709.458 |

## extreme / sustained-churn-path-v1 / N=10000000 / q=50 / fresh

Complete: True. Winner: petgraph-dfs. Fingerprint: `34b5694104c66807`.

Operations: cut 500, link 0, query 500 (8 true / 492 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 363.951 [363.951, 363.951] | -34.8% | +0.0% | 820.784 | 886.2 | 1.416 / 2.000 | — / — | 3173.833 / 7846.334 |
| Compact (default) | 558.413 [558.413, 558.413] | +0.0% | +53.4% | 2272.838 | 1266.9 | 13.292 / 21.125 | — / — | 4088.791 / 14293.125 |
| Workspace (opt-in) | 441.012 [441.012, 441.012] | -21.0% | +21.2% | 2234.316 | 1366.7 | 4.667 / 7.667 | — / — | 3517.542 / 10295.500 |

## extreme / sustained-churn-path-v1 / N=10000000 / q=50 / warmed

Complete: True. Winner: compact-workspace. Fingerprint: `34b5694104c66807`.

Operations: cut 500, link 0, query 500 (8 true / 492 false), additional repeats 0.

| Engine | Runtime ms [min, max] | Δ Compact | Above best | Setup ms | RSS MiB | Cut p95/p99 µs | Link p95/p99 µs | Query p95/p99 µs |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| petgraph (external) | 429.577 [429.577, 429.577] | -26.3% | +0.1% | 825.378 | 1259.2 | 5.459 / 8.333 | — / — | 3144.542 / 8655.541 |
| Compact (default) | 582.683 [582.683, 582.683] | +0.0% | +35.7% | 2373.419 | 1694.0 | 12.209 / 37.750 | — / — | 3894.291 / 12886.250 |
| Workspace (opt-in) | 429.361 [429.361, 429.361] | -26.3% | +0.0% | 2371.521 | 1513.0 | 2.625 / 14.166 | — / — | 3530.584 / 10714.375 |

