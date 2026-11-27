# knotrel#151 campaign: every classified metric

Generated from `analysis.json` (no class changed). Ratio is B / CUR (median of the paired log ratios, exponentiated; throughput metrics are CUR / B); memory metrics show q = B / CUR.

| Cell | Group | Metric | Class | Ratio or q | Interval |
|---|---|---|---|---|---|
| C1-cb-hub-1e5-fresh | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 0.924 | [0.921, 0.926] |
| C1-cb-hub-1e5-fresh | C1 | slowest_op_ns | EQUIVALENT | 0.933 | [0.929, 0.936] |
| C1-cb-hub-1e5-same | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 0.922 | [0.920, 0.927] |
| C1-cb-hub-1e5-same | C1 | slowest_op_ns | EQUIVALENT | 0.793 | [0.787, 0.797] |
| C1-cb-hub-1e5-toggle | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 1.026 | [1.024, 1.027] |
| C1-cb-hub-1e5-toggle | C1 | slowest_op_ns | EQUIVALENT | 0.996 | [0.983, 1.005] |
| C1-cb-sparse-1e5-fresh | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 0.906 | [0.904, 0.908] |
| C1-cb-sparse-1e5-fresh | C1 | slowest_op_ns | EQUIVALENT | 0.917 | [0.912, 0.919] |
| C1-cb-sparse-1e5-same | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 0.905 | [0.901, 0.908] |
| C1-cb-sparse-1e5-same | C1 | slowest_op_ns | INCONCLUSIVE | 0.754 | [0.581, 1.353] |
| C1-cb-sparse-1e5-toggle | C1 | observation_ns | TIMER_LIMITED (without limit: EQUIVALENT) | 0.996 | [0.992, 0.998] |
| C1-cb-sparse-1e5-toggle | C1 | slowest_op_ns | INCONCLUSIVE | 0.960 | [0.715, 1.686] |
| C1-cf-hub-1e5-fresh | C1 | observation_ns | EQUIVALENT | 1.056 | [1.053, 1.058] |
| C1-cf-hub-1e5-fresh | C1 | slowest_op_ns | EQUIVALENT | 0.992 | [0.987, 0.996] |
| C1-cf-hub-1e5-same | C1 | observation_ns | EQUIVALENT | 1.053 | [1.052, 1.057] |
| C1-cf-hub-1e5-same | C1 | slowest_op_ns | EQUIVALENT | 1.017 | [1.012, 1.025] |
| C1-cf-hub-1e5-toggle | C1 | observation_ns | EQUIVALENT | 1.035 | [1.033, 1.036] |
| C1-cf-hub-1e5-toggle | C1 | slowest_op_ns | EQUIVALENT | 1.010 | [1.007, 1.015] |
| C1-cf-sparse-1e5-fresh | C1 | observation_ns | EQUIVALENT | 1.054 | [1.050, 1.056] |
| C1-cf-sparse-1e5-fresh | C1 | slowest_op_ns | EQUIVALENT | 1.003 | [1.002, 1.007] |
| C1-cf-sparse-1e5-same | C1 | observation_ns | EQUIVALENT | 1.059 | [1.055, 1.063] |
| C1-cf-sparse-1e5-same | C1 | slowest_op_ns | EQUIVALENT | 1.006 | [1.000, 1.018] |
| C1-cf-sparse-1e5-toggle | C1 | observation_ns | EQUIVALENT | 1.027 | [1.023, 1.032] |
| C1-cf-sparse-1e5-toggle | C1 | slowest_op_ns | EQUIVALENT | 1.042 | [1.038, 1.046] |
| C2-cb-sparse-1e6 | C2 | observation_ns | SLOWER | 1.160 | [1.157, 1.166] |
| C2-cb-sparse-1e6 | C2 | slowest_op_ns | EQUIVALENT | 0.785 | [0.782, 0.788] |
| C2-cf-sparse-1e6 | C2 | observation_ns | EQUIVALENT | 1.014 | [1.011, 1.024] |
| C2-cf-sparse-1e6 | C2 | slowest_op_ns | EQUIVALENT | 1.042 | [1.032, 1.045] |
| C3-cb-hub-1e4 | C3 | requests_per_s | EQUIVALENT | 1.009 | [1.006, 1.010] |
| C3-cb-sparse-1e4 | C3 | requests_per_s | EQUIVALENT | 1.034 | [1.024, 1.042] |
| C3-cf-hub-1e4 | C3 | requests_per_s | EQUIVALENT | 1.002 | [1.000, 1.004] |
| C3-cf-sparse-1e4 | C3 | requests_per_s | EQUIVALENT | 1.006 | [1.005, 1.007] |
| I1-cb-sparse-1e5 | I1 | observation_ns | INCONCLUSIVE | 0.901 | [0.898, 0.903] |
| I1-cb-sparse-1e6 | I1 | observation_ns | SLOWER | 1.213 | [1.203, 1.217] |
| I1-cf-sparse-1e5 | I1 | observation_ns | EQUIVALENT | 1.031 | [1.027, 1.035] |
| I1-cf-sparse-1e6 | I1 | observation_ns | SLOWER | 1.132 | [1.123, 1.150] |
| I2-cb-his-1e4 | I2 | observation_ns | FASTER | 0.701 | [0.699, 0.703] |
| I2-cb-his-1e5 | I2 | observation_ns | FASTER | 0.746 | [0.744, 0.750] |
| I2-cb-his-1e6 | I2 | observation_ns | FASTER | 0.696 | [0.695, 0.697] |
| I2-cf-his-1e4 | I2 | observation_ns | INCONCLUSIVE | 0.919 | [0.896, 0.926] |
| I2-cf-his-1e5 | I2 | observation_ns | FASTER | 0.641 | [0.640, 0.644] |
| I2-cf-his-1e6 | I2 | observation_ns | FASTER | 0.547 | [0.546, 0.548] |
| I3-cb-his-1e4 | I3 | observation_ns | SLOWER | 1.105 | [1.104, 1.108] |
| I3-cb-his-1e5 | I3 | observation_ns | EQUIVALENT | 1.017 | [1.014, 1.018] |
| I3-cb-his-1e6 | I3 | observation_ns | EQUIVALENT | 1.004 | [1.001, 1.006] |
| I3-cb-sparse-1e6 | I3 | observation_ns | SLOWER | 1.319 | [1.277, 1.361] |
| I3-cf-his-1e4 | I3 | observation_ns | SLOWER | 1.208 | [1.202, 1.232] |
| I3-cf-his-1e5 | I3 | observation_ns | SLOWER | 1.315 | [1.304, 1.323] |
| I3-cf-his-1e6 | I3 | observation_ns | SLOWER | 1.435 | [1.423, 1.448] |
| I3-cf-sparse-1e6 | I3 | observation_ns | EQUIVALENT | 1.074 | [1.060, 1.084] |
| M1-cb-his-1e4 | M1 | high_water | SMALLER | q 0.806 |  |
| M1-cb-his-1e4 | M1 | live_after | SMALLER | q 0.824 |  |
| M1-cb-his-1e5 | M1 | high_water | SMALLER | q 0.804 |  |
| M1-cb-his-1e5 | M1 | live_after | SMALLER | q 0.822 |  |
| M1-cb-his-1e6 | M1 | high_water | SMALLER | q 0.784 |  |
| M1-cb-his-1e6 | M1 | live_after | SMALLER | q 0.799 |  |
| M1-cb-ring-1e6 | M1 | high_water | SMALLER | q 0.837 |  |
| M1-cb-ring-1e6 | M1 | live_after | SMALLER | q 0.863 |  |
| M1-cb-sparse-1e4 | M1 | high_water | SMALLER | q 0.852 |  |
| M1-cb-sparse-1e4 | M1 | live_after | SMALLER | q 0.854 |  |
| M1-cb-sparse-1e5 | M1 | high_water | SMALLER | q 0.863 |  |
| M1-cb-sparse-1e5 | M1 | live_after | SMALLER | q 0.880 |  |
| M1-cb-sparse-1e6 | M1 | high_water | SMALLER | q 0.806 |  |
| M1-cb-sparse-1e6 | M1 | live_after | SMALLER | q 0.825 |  |
| M1-cb-star-1e4 | M1 | high_water | SMALLER | q 0.852 |  |
| M1-cb-star-1e4 | M1 | live_after | SMALLER | q 0.854 |  |
| M1-cb-star-1e5 | M1 | high_water | SMALLER | q 0.863 |  |
| M1-cb-star-1e5 | M1 | live_after | SMALLER | q 0.880 |  |
| M1-cb-star-1e6 | M1 | high_water | SMALLER | q 0.806 |  |
| M1-cb-star-1e6 | M1 | live_after | SMALLER | q 0.825 |  |
| M1-cf-his-1e4 | M1 | high_water | SIMILAR | q 0.930 |  |
| M1-cf-his-1e4 | M1 | live_after | SIMILAR | q 0.921 |  |
| M1-cf-his-1e5 | M1 | high_water | SIMILAR | q 0.934 |  |
| M1-cf-his-1e5 | M1 | live_after | SIMILAR | q 0.925 |  |
| M1-cf-his-1e6 | M1 | high_water | SIMILAR | q 0.917 |  |
| M1-cf-his-1e6 | M1 | live_after | SIMILAR | q 0.907 |  |
| M1-cf-ring-1e6 | M1 | high_water | SIMILAR | q 0.945 |  |
| M1-cf-ring-1e6 | M1 | live_after | SIMILAR | q 0.942 |  |
| M1-cf-sparse-1e4 | M1 | high_water | SIMILAR | q 0.959 |  |
| M1-cf-sparse-1e4 | M1 | live_after | SIMILAR | q 0.947 |  |
| M1-cf-sparse-1e5 | M1 | high_water | SIMILAR | q 0.963 |  |
| M1-cf-sparse-1e5 | M1 | live_after | SIMILAR | q 0.954 |  |
| M1-cf-sparse-1e6 | M1 | high_water | SIMILAR | q 0.931 |  |
| M1-cf-sparse-1e6 | M1 | live_after | SIMILAR | q 0.921 |  |
| M1-cf-star-1e4 | M1 | high_water | SIMILAR | q 0.960 |  |
| M1-cf-star-1e4 | M1 | live_after | SIMILAR | q 0.947 |  |
| M1-cf-star-1e5 | M1 | high_water | SIMILAR | q 0.963 |  |
| M1-cf-star-1e5 | M1 | live_after | SIMILAR | q 0.954 |  |
| M1-cf-star-1e6 | M1 | high_water | SIMILAR | q 0.931 |  |
| M1-cf-star-1e6 | M1 | live_after | SIMILAR | q 0.922 |  |
| M1iso-cb-iso-1e6 | M1-iso (report-only) | high_water | SMALLER | q 0.889 |  |
| M1iso-cb-iso-1e6 | M1-iso (report-only) | live_after | SIMILAR | q 0.929 |  |
| M1iso-cf-iso-1e6 | M1-iso (report-only) | high_water | SIMILAR | q 0.954 |  |
| M1iso-cf-iso-1e6 | M1-iso (report-only) | live_after | SIMILAR | q 0.945 |  |
| M2-cb-his-1e6 | M2 | high_water | SMALLER | q 0.883 |  |
| M2-cb-his-1e6 | M2 | live_after | SMALLER | q 0.883 |  |
| M2-cb-sparse-1e6 | M2 | high_water | SIMILAR | q 0.923 |  |
| M2-cb-sparse-1e6 | M2 | live_after | SIMILAR | q 0.923 |  |
| M2-cf-his-1e6 | M2 | high_water | SIMILAR | q 0.948 |  |
| M2-cf-his-1e6 | M2 | live_after | SIMILAR | q 0.948 |  |
| M2-cf-sparse-1e6 | M2 | high_water | SIMILAR | q 0.972 |  |
| M2-cf-sparse-1e6 | M2 | live_after | SIMILAR | q 0.967 |  |
| M3-cb-his-1e6 | M3 | high_water | SMALLER | q 0.826 |  |
| M3-cb-his-1e6 | M3 | live_after_swap | SMALLER | q 0.799 |  |
| M3-cb-sparse-1e6 | M3 | high_water | SMALLER | q 0.837 |  |
| M3-cb-sparse-1e6 | M3 | live_after_swap | SMALLER | q 0.825 |  |
| M3-cf-his-1e6 | M3 | high_water | SIMILAR | q 0.919 |  |
| M3-cf-his-1e6 | M3 | live_after_swap | SIMILAR | q 0.907 |  |
| M3-cf-sparse-1e6 | M3 | high_water | SIMILAR | q 0.930 |  |
| M3-cf-sparse-1e6 | M3 | live_after_swap | SIMILAR | q 0.921 |  |
| M4-cb-hub-1e5-fresh | M4 | high_water | SIMILAR | q 0.976 |  |
| M4-cb-hub-1e5-fresh | M4 | live_at_end | SMALLER | q 0.896 |  |
| M4-cb-hub-1e5-same | M4 | high_water | SIMILAR | q 1.000 |  |
| M4-cb-hub-1e5-same | M4 | live_at_end | SMALLER | q 0.881 |  |
| M4-cb-hub-1e5-toggle | M4 | high_water | SIMILAR | q 0.948 |  |
| M4-cb-hub-1e5-toggle | M4 | live_at_end | SMALLER | q 0.880 |  |
| M4-cb-sparse-1e5-fresh | M4 | high_water | SIMILAR | q 0.963 |  |
| M4-cb-sparse-1e5-fresh | M4 | live_at_end | SMALLER | q 0.893 |  |
| M4-cb-sparse-1e5-same | M4 | high_water | SIMILAR | q 1.000 |  |
| M4-cb-sparse-1e5-same | M4 | live_at_end | SMALLER | q 0.878 |  |
| M4-cb-sparse-1e5-toggle | M4 | high_water | SIMILAR | q 0.907 |  |
| M4-cb-sparse-1e5-toggle | M4 | live_at_end | SMALLER | q 0.875 |  |
| M4-cf-hub-1e5-fresh | M4 | high_water | SIMILAR | q 0.980 |  |
| M4-cf-hub-1e5-fresh | M4 | live_at_end | SIMILAR | q 0.958 |  |
| M4-cf-hub-1e5-same | M4 | high_water | SIMILAR | q 0.952 |  |
| M4-cf-hub-1e5-same | M4 | live_at_end | SIMILAR | q 0.952 |  |
| M4-cf-hub-1e5-toggle | M4 | high_water | SIMILAR | q 0.949 |  |
| M4-cf-hub-1e5-toggle | M4 | live_at_end | SIMILAR | q 0.948 |  |
| M4-cf-sparse-1e5-fresh | M4 | high_water | SIMILAR | q 0.979 |  |
| M4-cf-sparse-1e5-fresh | M4 | live_at_end | SIMILAR | q 0.956 |  |
| M4-cf-sparse-1e5-same | M4 | high_water | SIMILAR | q 0.950 |  |
| M4-cf-sparse-1e5-same | M4 | live_at_end | SIMILAR | q 0.950 |  |
| M4-cf-sparse-1e5-toggle | M4 | high_water | SIMILAR | q 0.946 |  |
| M4-cf-sparse-1e5-toggle | M4 | live_at_end | SIMILAR | q 0.946 |  |
| M5-cb-sparse-1e6 | M5 | high_water | SMALLER | q 0.813 |  |
| M5-cb-sparse-1e6 | M5 | live_after_removal | SMALLER | q 0.843 |  |
| M5-cb-sparse-1e6 | M5 | live_at_end | SMALLER | q 0.885 |  |
| M5-cf-sparse-1e6 | M5 | high_water | SIMILAR | q 0.962 |  |
| M5-cf-sparse-1e6 | M5 | live_after_removal | SIMILAR | q 0.915 |  |
| M5-cf-sparse-1e6 | M5 | live_at_end | SIMILAR | q 0.937 |  |
| M6-cb-his-1e4 | M6 (report-only) | rss_after_build | SMALLER | q 0.867 |  |
| M6-cb-his-1e5 | M6 (report-only) | rss_after_build | SMALLER | q 0.865 |  |
| M6-cb-his-1e6 | M6 (report-only) | rss_after_build | SMALLER | q 0.841 |  |
| M6-cb-ring-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.916 |  |
| M6-cb-sparse-1e6 | M6 (report-only) | rss_after_build | SMALLER | q 0.798 |  |
| M6-cb-star-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.932 |  |
| M6-cf-his-1e4 | M6 (report-only) | rss_after_build | SIMILAR | q 0.934 |  |
| M6-cf-his-1e5 | M6 (report-only) | rss_after_build | SIMILAR | q 0.933 |  |
| M6-cf-his-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.923 |  |
| M6-cf-ring-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.969 |  |
| M6-cf-sparse-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.922 |  |
| M6-cf-star-1e6 | M6 (report-only) | rss_after_build | SIMILAR | q 0.924 |  |
| P1-cb-his-1e4-ordered | P1 | observation_ns | FASTER | 0.328 | [0.325, 0.329] |
| P1-cb-his-1e4-scrambled | P1 | observation_ns | FASTER | 0.349 | [0.348, 0.350] |
| P1-cb-his-1e5-ordered | P1 | observation_ns | FASTER | 0.684 | [0.661, 0.699] |
| P1-cb-his-1e5-scrambled | P1 | observation_ns | FASTER | 0.397 | [0.389, 0.403] |
| P1-cb-his-1e6-ordered | P1 | observation_ns | FASTER | 0.091 | [0.090, 0.091] |
| P1-cb-his-1e6-scrambled | P1 | observation_ns | FASTER | 0.562 | [0.555, 0.570] |
| P1-cf-his-1e6-ordered | P1 | observation_ns | FASTER | 0.090 | [0.088, 0.090] |
| P1-cf-his-1e6-scrambled | P1 | observation_ns | FASTER | 0.516 | [0.512, 0.520] |
| P2-cb-his-1e4-ordered | P2 | median_page_ns | FASTER | 0.386 | [0.386, 0.400] |
| P2-cb-his-1e4-ordered | P2 | p99_page_ns | INCONCLUSIVE | 1.505 | [1.118, 1.604] |
| P2-cb-his-1e4-scrambled | P2 | median_page_ns | FASTER | 0.422 | [0.417, 0.423] |
| P2-cb-his-1e4-scrambled | P2 | p99_page_ns | FASTER | 0.429 | [0.413, 0.443] |
| P2-cb-his-1e5-ordered | P2 | median_page_ns | FASTER | 0.494 | [0.483, 0.497] |
| P2-cb-his-1e5-ordered | P2 | p99_page_ns | EQUIVALENT | 1.088 | [1.065, 1.119] |
| P2-cb-his-1e5-scrambled | P2 | median_page_ns | FASTER | 0.446 | [0.429, 0.463] |
| P2-cb-his-1e5-scrambled | P2 | p99_page_ns | FASTER | 0.517 | [0.510, 0.527] |
| P2-cb-his-1e6-ordered | P2 | median_page_ns | FASTER | 0.194 | [0.193, 0.197] |
| P2-cb-his-1e6-ordered | P2 | p99_page_ns | FASTER | 0.145 | [0.142, 0.149] |
| P2-cb-his-1e6-scrambled | P2 | median_page_ns | FASTER | 0.625 | [0.619, 0.644] |
| P2-cb-his-1e6-scrambled | P2 | p99_page_ns | FASTER | 0.452 | [0.448, 0.458] |
| P2-cf-his-1e6-ordered | P2 | median_page_ns | FASTER | 0.191 | [0.189, 0.193] |
| P2-cf-his-1e6-ordered | P2 | p99_page_ns | FASTER | 0.143 | [0.140, 0.144] |
| P2-cf-his-1e6-scrambled | P2 | median_page_ns | FASTER | 0.599 | [0.590, 0.605] |
| P2-cf-his-1e6-scrambled | P2 | p99_page_ns | FASTER | 0.454 | [0.447, 0.465] |
| P3-cb-his-1e4 | P3 | median_ns | EQUIVALENT | 0.979 | [0.968, 0.984] |
| P3-cb-his-1e4 | P3 | p99_ns | EQUIVALENT | 0.969 | [0.958, 0.976] |
| P3-cb-his-1e5 | P3 | median_ns | EQUIVALENT | 0.974 | [0.968, 0.978] |
| P3-cb-his-1e5 | P3 | p99_ns | EQUIVALENT | 0.954 | [0.948, 0.968] |
| P3-cb-his-1e6 | P3 | median_ns | EQUIVALENT | 0.976 | [0.967, 0.983] |
| P3-cb-his-1e6 | P3 | p99_ns | EQUIVALENT | 0.947 | [0.941, 0.952] |
| P3-cf-his-1e6 | P3 | median_ns | EQUIVALENT | 0.970 | [0.963, 0.986] |
| P3-cf-his-1e6 | P3 | p99_ns | EQUIVALENT | 0.919 | [0.901, 0.940] |
| P4-cb-his-1e6 | P4 | page_p99_ns | EQUIVALENT | 0.987 | [0.976, 1.004] |
| P4-cb-his-1e6 | P4 | traversal_ns | EQUIVALENT | 1.015 | [1.012, 1.017] |
| P4-cf-his-1e6 | P4 | page_p99_ns | EQUIVALENT | 0.996 | [0.986, 1.003] |
| P4-cf-his-1e6 | P4 | traversal_ns | EQUIVALENT | 1.011 | [1.008, 1.013] |
| R1-cb-sparse-1e5 | R1 | observation_ns | EQUIVALENT | 1.068 | [1.055, 1.083] |
| R1-cb-sparse-1e6 | R1 | observation_ns | SLOWER | 1.567 | [1.556, 1.580] |
| R1-cf-sparse-1e5 | R1 | observation_ns | EQUIVALENT | 1.030 | [1.025, 1.036] |
| R1-cf-sparse-1e6 | R1 | observation_ns | EQUIVALENT | 1.006 | [1.004, 1.008] |
| R2-cb-his-1e4 | R2 | observation_ns | FASTER | 0.721 | [0.717, 0.725] |
| R2-cb-his-1e5 | R2 | observation_ns | FASTER | 0.735 | [0.734, 0.738] |
| R2-cb-his-1e6 | R2 | observation_ns | FASTER | 0.702 | [0.700, 0.704] |
| R2-cf-his-1e4 | R2 | observation_ns | EQUIVALENT | 1.001 | [0.989, 1.010] |
| R2-cf-his-1e5 | R2 | observation_ns | EQUIVALENT | 0.958 | [0.948, 0.962] |
| R2-cf-his-1e6 | R2 | observation_ns | FASTER | 0.582 | [0.579, 0.584] |
| R3-cb-his-1e4 | R3 | observation_ns | INCONCLUSIVE | 1.100 | [1.093, 1.106] |
| R3-cb-his-1e5 | R3 | observation_ns | EQUIVALENT | 1.025 | [1.024, 1.027] |
| R3-cb-his-1e6 | R3 | observation_ns | EQUIVALENT | 1.015 | [1.013, 1.018] |
| R3-cb-sparse-1e6 | R3 | observation_ns | SLOWER | 1.470 | [1.459, 1.489] |
| R3-cf-his-1e4 | R3 | observation_ns | EQUIVALENT | 1.002 | [0.998, 1.006] |
| R3-cf-his-1e5 | R3 | observation_ns | EQUIVALENT | 1.022 | [1.010, 1.030] |
| R3-cf-his-1e6 | R3 | observation_ns | EQUIVALENT | 1.087 | [1.080, 1.095] |
| R3-cf-sparse-1e6 | R3 | observation_ns | EQUIVALENT | 1.005 | [1.003, 1.008] |
| R4-cb-star-1e4 | R4 | per_cycle_ns | SLOWER | 1.316 | [1.302, 1.326] |
| R4-cb-star-1e5 | R4 | per_cycle_ns | SLOWER | 1.315 | [1.307, 1.330] |
| R4-cb-star-1e6 | R4 | per_cycle_ns | FASTER | 0.654 | [0.646, 0.657] |
| R4-cf-star-1e4 | R4 | per_cycle_ns | EQUIVALENT | 1.072 | [1.069, 1.080] |
| R4-cf-star-1e5 | R4 | per_cycle_ns | EQUIVALENT | 1.068 | [1.064, 1.075] |
| R4-cf-star-1e6 | R4 | per_cycle_ns | FASTER | 0.747 | [0.735, 0.756] |
| R5-cb-sparse-1e6 | R5 | observation_ns | SLOWER | 1.240 | [1.230, 1.254] |
| R5-cf-sparse-1e6 | R5 | observation_ns | EQUIVALENT | 0.991 | [0.989, 0.995] |
