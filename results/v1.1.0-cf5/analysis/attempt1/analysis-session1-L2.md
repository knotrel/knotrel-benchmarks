| Cell | Scale | Reference median | Candidate median | Median change | Interval | Tolerance | Status |
|---|---|---|---|---|---|---|---|

| Memory cell | Plain net heap | Lifecycle net heap | Reference net heap | Lifecycle/plain | Status |
|---|---|---|---|---|---|

| Sustained cell | Metric | First | Last | Max | Late/early | Projected 30-cycle growth | Max retired slots | C1 | C2 | C3/C4 |
|---|---|---|---|---|---|---|---|---|---|---|
| C-heap-lifecycle-cluster-forest-hub-fresh-100000 | net_heap_bytes | 50.9 MiB | 62.9 MiB | 82.1 MiB | 0.939 | +0.016 | 95000 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-hub-same-100000 | net_heap_bytes | 50.9 MiB | 55.3 MiB | 55.7 MiB | 0.997 | +0.077 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-hub-toggle-100000 | net_heap_bytes | 50.9 MiB | 52.2 MiB | 52.2 MiB | 1.004 | +0.015 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-ring-fresh-100000 | net_heap_bytes | 44.2 MiB | 57.7 MiB | 73.9 MiB | 0.994 | +0.052 | 95000 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-ring-same-100000 | net_heap_bytes | 44.2 MiB | 47.2 MiB | 47.2 MiB | 1.008 | +0.040 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-ring-toggle-100000 | net_heap_bytes | 44.2 MiB | 44.9 MiB | 44.9 MiB | 1.003 | +0.010 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-fresh-1000 | net_heap_bytes | 0.5 MiB | 0.7 MiB | 0.8 MiB | 0.978 | +0.008 | 1000 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-fresh-10000 | net_heap_bytes | 5.8 MiB | 6.5 MiB | 7.8 MiB | 0.943 | -0.057 | 9500 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-fresh-100000 | net_heap_bytes | 51.1 MiB | 63.3 MiB | 82.7 MiB | 0.939 | +0.005 | 95000 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-same-1000 | net_heap_bytes | 0.5 MiB | 0.6 MiB | 0.6 MiB | 1.133 | +0.202 | 0 | PASS | PASS | FAIL |
| C-heap-lifecycle-cluster-forest-sparse-same-10000 | net_heap_bytes | 5.8 MiB | 6.0 MiB | 6.0 MiB | 0.998 | +0.002 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-same-100000 | net_heap_bytes | 51.1 MiB | 55.8 MiB | 55.9 MiB | 0.999 | +0.068 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-toggle-1000 | net_heap_bytes | 0.5 MiB | 0.6 MiB | 0.6 MiB | 1.146 | +0.146 | 0 | PASS | PASS | FAIL |
| C-heap-lifecycle-cluster-forest-sparse-toggle-10000 | net_heap_bytes | 5.8 MiB | 6.0 MiB | 6.0 MiB | 1.007 | +0.014 | 0 | PASS | PASS | PASS |
| C-heap-lifecycle-cluster-forest-sparse-toggle-100000 | net_heap_bytes | 51.1 MiB | 52.9 MiB | 52.9 MiB | 1.009 | +0.017 | 0 | PASS | PASS | PASS |
| C-heap-reference-cluster-forest-hub-fresh-100000 | net_heap_bytes | 56.0 MiB | 103.7 MiB | 103.7 MiB | 1.324 | +0.692 | - | - | PASS | - |
| C-heap-reference-cluster-forest-hub-same-100000 | net_heap_bytes | 56.0 MiB | 59.9 MiB | 60.8 MiB | 0.987 | +0.056 | - | - | PASS | - |
| C-heap-reference-cluster-forest-hub-toggle-100000 | net_heap_bytes | 56.0 MiB | 59.6 MiB | 59.6 MiB | 1.017 | +0.047 | - | - | PASS | - |
| C-heap-reference-cluster-forest-ring-fresh-100000 | net_heap_bytes | 46.4 MiB | 94.1 MiB | 94.1 MiB | 1.407 | +0.803 | - | - | PASS | - |
| C-heap-reference-cluster-forest-ring-same-100000 | net_heap_bytes | 46.4 MiB | 50.3 MiB | 50.3 MiB | 1.015 | +0.055 | - | - | PASS | - |
| C-heap-reference-cluster-forest-ring-toggle-100000 | net_heap_bytes | 46.4 MiB | 47.3 MiB | 47.3 MiB | 1.005 | +0.014 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-fresh-1000 | net_heap_bytes | 0.6 MiB | 1.0 MiB | 1.0 MiB | 1.264 | +0.409 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-fresh-10000 | net_heap_bytes | 6.2 MiB | 10.2 MiB | 10.2 MiB | 1.394 | +0.584 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-fresh-100000 | net_heap_bytes | 55.1 MiB | 104.0 MiB | 104.0 MiB | 1.340 | +0.708 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-same-1000 | net_heap_bytes | 0.6 MiB | 0.7 MiB | 0.7 MiB | 1.126 | +0.194 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-same-10000 | net_heap_bytes | 6.2 MiB | 6.4 MiB | 6.4 MiB | 1.001 | +0.007 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-same-100000 | net_heap_bytes | 55.1 MiB | 60.1 MiB | 60.1 MiB | 1.001 | +0.068 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-toggle-1000 | net_heap_bytes | 0.6 MiB | 0.7 MiB | 0.7 MiB | 1.145 | +0.226 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-toggle-10000 | net_heap_bytes | 6.2 MiB | 6.6 MiB | 6.6 MiB | 1.016 | +0.037 | - | - | PASS | - |
| C-heap-reference-cluster-forest-sparse-toggle-100000 | net_heap_bytes | 55.1 MiB | 58.8 MiB | 58.8 MiB | 1.019 | +0.043 | - | - | PASS | - |
| C-rss-lifecycle-cluster-forest-hub-fresh-100000 | net_rss_bytes | 25.9 MiB | 98.2 MiB | 98.2 MiB | 2.479 | +2.554 | 95000 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-hub-same-100000 | net_rss_bytes | 13.0 MiB | 24.0 MiB | 24.0 MiB | 1.061 | +0.675 | 0 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-hub-toggle-100000 | net_rss_bytes | 37.9 MiB | 40.0 MiB | 40.0 MiB | 1.009 | +0.034 | 0 | PASS | PASS | PASS |
| C-rss-lifecycle-cluster-forest-ring-fresh-100000 | net_rss_bytes | 27.8 MiB | 106.0 MiB | 106.0 MiB | 3.016 | +2.934 | 95000 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-ring-same-100000 | net_rss_bytes | 30.2 MiB | 30.2 MiB | 30.2 MiB | 1.000 | +0.001 | 0 | PASS | PASS | PASS |
| C-rss-lifecycle-cluster-forest-ring-toggle-100000 | net_rss_bytes | 37.5 MiB | 39.1 MiB | 39.1 MiB | 1.009 | +0.027 | 0 | PASS | PASS | PASS |
| C-rss-lifecycle-cluster-forest-sparse-fresh-1000 | net_rss_bytes | 0.6 MiB | 1.3 MiB | 1.3 MiB | 1.688 | +1.160 | 1000 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-fresh-10000 | net_rss_bytes | 3.2 MiB | 9.1 MiB | 9.1 MiB | 2.270 | +2.099 | 9500 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-fresh-100000 | net_rss_bytes | 17.9 MiB | 99.6 MiB | 99.6 MiB | 2.657 | +3.074 | 95000 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-same-1000 | net_rss_bytes | 0.6 MiB | 0.7 MiB | 0.7 MiB | 1.150 | +0.315 | 0 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-same-10000 | net_rss_bytes | 3.6 MiB | 3.8 MiB | 3.8 MiB | 1.012 | +0.030 | 0 | PASS | PASS | PASS |
| C-rss-lifecycle-cluster-forest-sparse-same-100000 | net_rss_bytes | 23.5 MiB | 33.0 MiB | 33.0 MiB | 1.021 | +0.320 | 0 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-toggle-1000 | net_rss_bytes | 0.6 MiB | 0.7 MiB | 0.7 MiB | 1.154 | +0.175 | 0 | PASS | PASS | EXCEEDS_BUDGET |
| C-rss-lifecycle-cluster-forest-sparse-toggle-10000 | net_rss_bytes | 3.4 MiB | 3.7 MiB | 3.7 MiB | 1.040 | +0.068 | 0 | PASS | PASS | PASS |
| C-rss-lifecycle-cluster-forest-sparse-toggle-100000 | net_rss_bytes | 40.8 MiB | 43.2 MiB | 43.2 MiB | 1.021 | +0.037 | 0 | PASS | PASS | PASS |
| C-rss-reference-cluster-forest-hub-fresh-100000 | net_rss_bytes | 37.6 MiB | 84.5 MiB | 84.5 MiB | 1.447 | +0.830 | - | - | PASS | - |
| C-rss-reference-cluster-forest-hub-same-100000 | net_rss_bytes | 26.9 MiB | 35.2 MiB | 35.2 MiB | 1.002 | +0.216 | - | - | PASS | - |
| C-rss-reference-cluster-forest-hub-toggle-100000 | net_rss_bytes | 44.8 MiB | 52.0 MiB | 52.0 MiB | 1.048 | +0.124 | - | - | PASS | - |
| C-rss-reference-cluster-forest-ring-fresh-100000 | net_rss_bytes | 30.2 MiB | 84.7 MiB | 84.7 MiB | 1.511 | +1.217 | - | - | PASS | - |
| C-rss-reference-cluster-forest-ring-same-100000 | net_rss_bytes | 31.9 MiB | 38.5 MiB | 38.5 MiB | 1.046 | +0.139 | - | - | PASS | - |
| C-rss-reference-cluster-forest-ring-toggle-100000 | net_rss_bytes | 43.8 MiB | 45.9 MiB | 45.9 MiB | 1.013 | +0.033 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-fresh-1000 | net_rss_bytes | 0.7 MiB | 1.1 MiB | 1.1 MiB | 1.309 | +0.485 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-fresh-10000 | net_rss_bytes | 3.9 MiB | 7.8 MiB | 7.8 MiB | 1.505 | +0.830 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-fresh-100000 | net_rss_bytes | 28.2 MiB | 71.3 MiB | 71.3 MiB | 1.286 | +0.905 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-same-1000 | net_rss_bytes | 0.7 MiB | 0.8 MiB | 0.8 MiB | 1.156 | +0.257 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-same-10000 | net_rss_bytes | 3.9 MiB | 4.4 MiB | 4.4 MiB | 1.033 | +0.073 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-same-100000 | net_rss_bytes | 31.0 MiB | 33.7 MiB | 33.7 MiB | 1.009 | +0.036 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-toggle-1000 | net_rss_bytes | 0.7 MiB | 0.8 MiB | 0.8 MiB | 1.152 | +0.277 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-toggle-10000 | net_rss_bytes | 3.7 MiB | 4.4 MiB | 4.4 MiB | 1.061 | +0.125 | - | - | PASS | - |
| C-rss-reference-cluster-forest-sparse-toggle-100000 | net_rss_bytes | 50.8 MiB | 57.1 MiB | 57.1 MiB | 1.041 | +0.091 | - | - | PASS | - |
