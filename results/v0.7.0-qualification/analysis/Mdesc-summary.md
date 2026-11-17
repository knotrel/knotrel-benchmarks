# M_desc summary (v0.7.0 candidate `e75ff6a`, descriptive)

One 3-second window per configuration, contention probe revision 2. Generated from `Mdesc-analysis.json`; every row VALID under the declared rule.

| Server | Config | Background | Open rate | req/s | ops/s | p50 ms | p99 ms | 503 | Jain | Lock wait / latency | Background completed / failures | RSS MiB |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M-standalone-off-10k | read95-b1-c1 | none |  | 10630.7 | 10630.7 | 0.083 | 0.210 | 0 | 1.000 | 0.00 |  | 10.7 |
| M-standalone-off-10k | read95-b1-c4 | none |  | 32031.0 | 32031.0 | 0.114 | 0.269 | 0 | 1.000 | 0.06 |  | 13.2 |
| M-standalone-off-10k | read95-b1-c16 | none |  | 49005.3 | 49005.3 | 0.294 | 0.888 | 0 | 1.000 | 0.20 |  | 32.2 |
| M-standalone-off-10k | read95-b1-c64 | none |  | 46088.0 | 46088.0 | 1.080 | 3.401 | 52230 | 1.000 | 0.26 |  | 55.7 |
| M-standalone-off-10k | read95-b8-c1 | none |  | 1847.7 | 14781.3 | 0.535 | 0.872 | 0 | 1.000 | 0.00 |  | 56.4 |
| M-standalone-off-10k | read95-b8-c4 | none |  | 3340.3 | 26722.7 | 1.165 | 2.396 | 0 | 1.000 | 0.54 |  | 56.6 |
| M-standalone-off-10k | read95-b8-c16 | none |  | 3441.7 | 27533.3 | 4.555 | 8.953 | 0 | 1.000 | 0.87 |  | 57.5 |
| M-standalone-off-10k | read95-b8-c64 | none |  | 3287.0 | 26296.0 | 9.893 | 21.858 | 267910 | 0.998 | 0.90 |  | 60.3 |
| M-standalone-off-10k | read95-b64-c1 | none |  | 272.0 | 17408.0 | 3.626 | 4.659 | 0 | 1.000 | 0.00 |  | 60.7 |
| M-standalone-off-10k | read95-b64-c4 | none |  | 277.7 | 17770.7 | 14.391 | 16.779 | 0 | 1.000 | 0.74 |  | 60.8 |
| M-standalone-off-10k | read95-b64-c16 | none |  | 273.7 | 17514.7 | 57.978 | 65.974 | 0 | 1.000 | 0.94 |  | 62.2 |
| M-standalone-off-10k | read95-b64-c64 | none |  | 260.3 | 16661.3 | 121.878 | 238.706 | 276512 | 0.979 | 0.97 |  | 63.9 |
| M-standalone-off-10k-mixed50 | mixed50-b1-c1 | none |  | 14808.7 | 14808.7 | 0.040 | 0.203 | 0 | 1.000 | 0.00 |  | 10.3 |
| M-standalone-off-10k-mixed50 | mixed50-b1-c4 | none |  | 32751.0 | 32751.0 | 0.111 | 0.293 | 0 | 1.000 | 0.32 |  | 13.0 |
| M-standalone-off-10k-mixed50 | mixed50-b1-c16 | none |  | 35767.0 | 35767.0 | 0.432 | 1.181 | 0 | 1.000 | 0.76 |  | 22.4 |
| M-standalone-off-10k-mixed50 | mixed50-b1-c64 | none |  | 31336.0 | 31336.0 | 1.288 | 4.610 | 185742 | 1.000 | 0.68 |  | 41.5 |
| M-standalone-off-10k-mixed50 | mixed50-b8-c1 | none |  | 3052.3 | 24418.7 | 0.314 | 0.663 | 0 | 1.000 | 0.00 |  | 43.2 |
| M-standalone-off-10k-mixed50 | mixed50-b8-c4 | none |  | 3731.0 | 29848.0 | 1.058 | 1.772 | 0 | 1.000 | 0.67 |  | 43.4 |
| M-standalone-off-10k-mixed50 | mixed50-b8-c16 | none |  | 3719.3 | 29754.7 | 4.272 | 6.294 | 0 | 1.000 | 0.92 |  | 44.2 |
| M-standalone-off-10k-mixed50 | mixed50-b8-c64 | none |  | 3555.7 | 28445.3 | 9.195 | 17.753 | 292314 | 0.998 | 0.93 |  | 46.3 |
| M-standalone-off-10k-mixed50 | mixed50-b64-c1 | none |  | 499.0 | 31936.0 | 1.976 | 2.855 | 0 | 1.000 | 0.00 |  | 46.5 |
| M-standalone-off-10k-mixed50 | mixed50-b64-c4 | none |  | 516.7 | 33066.7 | 7.705 | 9.468 | 0 | 1.000 | 0.74 |  | 46.6 |
| M-standalone-off-10k-mixed50 | mixed50-b64-c16 | none |  | 511.3 | 32725.3 | 31.166 | 35.184 | 0 | 1.000 | 0.93 |  | 48.3 |
| M-standalone-off-10k-mixed50 | mixed50-b64-c64 | none |  | 481.3 | 30805.3 | 65.661 | 127.385 | 273969 | 0.988 | 0.96 |  | 49.6 |
| M-source-off-10k | read100-b8-c4-none | none |  | 6983.3 | 55866.7 | 0.564 | 0.931 | 0 | 1.000 | 0.00 |  | 15.4 |
| M-source-off-10k | read100-b8-c4-import | import |  | 6837.8 | 54702.4 | 0.575 | 0.948 | 0 | 1.000 | 0.00 | 6 / 0 | 28.9 |
| M-source-off-10k | read100-b8-c4-events | events |  | 5637.0 | 45096.0 | 0.691 | 1.238 | 0 | 1.000 | 0.19 | 385728 / 0 | 32.6 |
| M-source-off-10k | read100-b8-c16-none | none |  | 11362.7 | 90901.3 | 0.977 | 4.429 | 0 | 0.992 | 0.00 |  | 77.6 |
| M-source-off-10k | read100-b8-c16-import | import |  | 11528.0 | 92224.0 | 1.006 | 4.054 | 0 | 0.993 | 0.00 | 6 / 0 | 96.0 |
| M-source-off-10k | read100-b8-c16-events | events |  | 9788.3 | 78306.7 | 1.636 | 3.322 | 0 | 1.000 | 0.34 | 169024 / 0 | 100.7 |
| M-source-off-10k | read100-b8-c64-none | none |  | 10166.7 | 81333.3 | 4.240 | 21.592 | 59694 | 0.999 | 0.00 |  | 135.9 |
| M-source-off-10k | read100-b8-c64-import | import |  | 9317.2 | 74537.6 | 4.482 | 25.850 | 81024 | 0.999 | 0.00 | 6 / 0 | 162.7 |
| M-source-off-10k | read100-b8-c64-events | events |  | 9281.3 | 74250.7 | 4.338 | 16.302 | 59241 | 0.999 | 0.16 | 23232 / 0 | 170.9 |
| M-standalone-off-100k | read95-b1-c1 | none |  | 1396.3 | 1396.3 | 0.550 | 2.049 | 0 | 1.000 | 0.00 |  | 30.5 |
| M-standalone-off-100k | read95-b1-c4 | none |  | 4776.0 | 4776.0 | 0.700 | 2.567 | 0 | 1.000 | 0.11 |  | 41.4 |
| M-standalone-off-100k | read95-b1-c16 | none |  | 5393.0 | 5393.0 | 2.316 | 15.578 | 0 | 0.999 | 0.43 |  | 261.7 |
| M-standalone-off-100k | read95-b1-c64 | none |  | 4552.0 | 4552.0 | 8.184 | 32.671 | 113568 | 0.999 | 0.46 |  | 274.3 |
| M-standalone-off-100k | read95-b8-c1 | none |  | 203.0 | 1624.0 | 4.687 | 11.149 | 0 | 1.000 | 0.00 |  | 275.8 |
| M-standalone-off-100k | read95-b8-c4 | none |  | 328.0 | 2624.0 | 11.948 | 25.809 | 0 | 1.000 | 0.59 |  | 278.1 |
| M-standalone-off-100k | read95-b8-c16 | none |  | 338.7 | 2709.3 | 45.672 | 109.225 | 0 | 1.000 | 0.88 |  | 281.2 |
| M-standalone-off-100k | read95-b8-c64 | none |  | 295.7 | 2365.3 | 105.086 | 234.060 | 259309 | 0.987 | 0.93 |  | 281.6 |
| M-standalone-off-100k | read95-b64-c1 | none |  | 26.7 | 1706.7 | 37.499 | 44.617 | 0 | 1.000 | 0.00 |  | 281.9 |
| M-standalone-off-100k | read95-b64-c4 | none |  | 26.7 | 1706.7 | 148.669 | 302.784 | 0 | 0.999 | 0.78 |  | 282.2 |
| M-standalone-off-100k | read95-b64-c16 | none |  | 26.3 | 1685.3 | 603.722 | 1122.831 | 0 | 0.993 | 0.95 |  | 285.3 |
| M-standalone-off-100k | read95-b64-c64 | none |  | 16.7 | 1066.7 | 1872.820 | 1961.923 | 267217 | 0.698 | 0.95 |  | 286.1 |
| M-standalone-off-100k-mixed50 | mixed50-b1-c1 | none |  | 2530.3 | 2530.3 | 0.096 | 1.906 | 0 | 1.000 | 0.00 |  | 31.6 |
| M-standalone-off-100k-mixed50 | mixed50-b1-c4 | none |  | 4321.3 | 4321.3 | 0.822 | 2.871 | 0 | 1.000 | 0.55 |  | 41.5 |
| M-standalone-off-100k-mixed50 | mixed50-b1-c16 | none |  | 4388.7 | 4388.7 | 3.471 | 8.871 | 0 | 1.000 | 0.87 |  | 81.7 |
| M-standalone-off-100k-mixed50 | mixed50-b1-c64 | none |  | 2622.3 | 2622.3 | 10.490 | 58.563 | 250574 | 0.996 | 0.92 |  | 133.2 |
| M-standalone-off-100k-mixed50 | mixed50-b8-c1 | none |  | 317.7 | 2541.3 | 2.914 | 9.172 | 0 | 1.000 | 0.00 |  | 133.5 |
| M-standalone-off-100k-mixed50 | mixed50-b8-c4 | none |  | 364.0 | 2912.0 | 10.768 | 19.225 | 0 | 1.000 | 0.74 |  | 134.5 |
| M-standalone-off-100k-mixed50 | mixed50-b8-c16 | none |  | 370.0 | 2960.0 | 42.071 | 76.831 | 0 | 1.000 | 0.94 |  | 135.7 |
| M-standalone-off-100k-mixed50 | mixed50-b8-c64 | none |  | 277.0 | 2216.0 | 108.409 | 229.952 | 288375 | 0.975 | 0.96 |  | 139.8 |
| M-standalone-off-100k-mixed50 | mixed50-b64-c1 | none |  | 49.3 | 3157.3 | 20.081 | 31.556 | 0 | 1.000 | 0.00 |  | 141.3 |
| M-standalone-off-100k-mixed50 | mixed50-b64-c4 | none |  | 49.0 | 3136.0 | 82.198 | 100.101 | 0 | 1.000 | 0.75 |  | 141.3 |
| M-standalone-off-100k-mixed50 | mixed50-b64-c16 | none |  | 45.7 | 2922.7 | 336.523 | 439.766 | 0 | 0.997 | 0.93 |  | 141.7 |
| M-standalone-off-100k-mixed50 | mixed50-b64-c64 | none |  | 35.3 | 2261.3 | 853.905 | 1085.558 | 255897 | 0.905 | 0.95 |  | 154.8 |
| M-source-off-100k | read100-b8-c4-none | none |  | 701.7 | 5613.3 | 5.607 | 9.732 | 0 | 1.000 | 0.00 |  | 57.7 |
| M-source-off-100k | read100-b8-c4-import | import |  | 671.0 | 5368.0 | 5.785 | 10.612 | 0 | 1.000 | 0.00 | 6 / 0 | 146.8 |
| M-source-off-100k | read100-b8-c4-events | events |  | 518.7 | 4149.3 | 7.353 | 15.389 | 0 | 1.000 | 0.26 | 48000 / 0 | 153.1 |
| M-source-off-100k | read100-b8-c16-none | none |  | 809.3 | 6474.7 | 11.131 | 83.620 | 0 | 0.997 | 0.00 |  | 246.7 |
| M-source-off-100k | read100-b8-c16-import | import |  | 944.2 | 7553.6 | 9.537 | 90.372 | 0 | 0.994 | 0.01 | 6 / 0 | 472.8 |
| M-source-off-100k | read100-b8-c16-events | events |  | 821.3 | 6570.7 | 18.832 | 46.312 | 0 | 0.999 | 0.48 | 42688 / 0 | 475.7 |
| M-source-off-100k | read100-b8-c64-none | none |  | 672.0 | 5376.0 | 39.821 | 200.599 | 145322 | 0.987 | 0.00 |  | 493.1 |
| M-source-off-100k | read100-b8-c64-import | import |  | 693.2 | 5545.6 | 40.114 | 200.470 | 196210 | 0.992 | 0.03 | 6 / 0 | 583.8 |
| M-source-off-100k | read100-b8-c64-events | events |  | 738.0 | 5904.0 | 52.893 | 131.708 | 90542 | 0.994 | 0.22 | 2688 / 0 | 585.4 |
| M-standalone-on-10k | read95-b1-c1 | none |  | 10539.0 | 10539.0 | 0.084 | 0.211 | 0 | 1.000 | 0.00 |  | 11.7 |
| M-standalone-on-10k | read95-b1-c4 | none |  | 30727.0 | 30727.0 | 0.119 | 0.278 | 0 | 1.000 | 0.05 |  | 14.2 |
| M-standalone-on-10k | read95-b1-c16 | none |  | 46219.7 | 46219.7 | 0.309 | 0.993 | 0 | 1.000 | 0.21 |  | 39.4 |
| M-standalone-on-10k | read95-b1-c64 | none |  | 44211.0 | 44211.0 | 1.151 | 3.453 | 44799 | 1.000 | 0.25 |  | 60.7 |
| M-standalone-on-10k | read95-b8-c1 | none |  | 1835.0 | 14680.0 | 0.538 | 0.877 | 0 | 1.000 | 0.00 |  | 62.2 |
| M-standalone-on-10k | read95-b8-c4 | none |  | 3282.7 | 26261.3 | 1.179 | 2.419 | 0 | 1.000 | 0.54 |  | 62.5 |
| M-standalone-on-10k | read95-b8-c16 | none |  | 3424.3 | 27394.7 | 4.624 | 9.225 | 0 | 1.000 | 0.87 |  | 63.4 |
| M-standalone-on-10k | read95-b8-c64 | none |  | 3133.3 | 25066.7 | 10.420 | 21.932 | 256230 | 0.998 | 0.90 |  | 69.0 |
| M-standalone-on-10k | read95-b64-c1 | none |  | 270.3 | 17301.3 | 3.648 | 4.674 | 0 | 1.000 | 0.00 |  | 69.3 |
| M-standalone-on-10k | read95-b64-c4 | none |  | 274.7 | 17578.7 | 14.518 | 16.762 | 0 | 1.000 | 0.74 |  | 69.4 |
| M-standalone-on-10k | read95-b64-c16 | none |  | 273.0 | 17472.0 | 58.116 | 65.096 | 0 | 1.000 | 0.94 |  | 70.6 |
| M-standalone-on-10k | read95-b64-c64 | none |  | 251.3 | 16085.3 | 125.530 | 245.855 | 267424 | 0.979 | 0.96 |  | 72.1 |
| M-standalone-on-10k-mixed50 | mixed50-b1-c1 | none |  | 14766.0 | 14766.0 | 0.040 | 0.204 | 0 | 1.000 | 0.00 |  | 11.9 |
| M-standalone-on-10k-mixed50 | mixed50-b1-c4 | none |  | 32713.3 | 32713.3 | 0.111 | 0.295 | 0 | 1.000 | 0.32 |  | 14.8 |
| M-standalone-on-10k-mixed50 | mixed50-b1-c16 | none |  | 35466.0 | 35466.0 | 0.435 | 1.199 | 0 | 1.000 | 0.76 |  | 25.0 |
| M-standalone-on-10k-mixed50 | mixed50-b1-c64 | none |  | 29715.3 | 29715.3 | 1.359 | 4.607 | 182623 | 1.000 | 0.69 |  | 40.6 |
| M-standalone-on-10k-mixed50 | mixed50-b8-c1 | none |  | 3063.3 | 24506.7 | 0.312 | 0.665 | 0 | 1.000 | 0.00 |  | 41.3 |
| M-standalone-on-10k-mixed50 | mixed50-b8-c4 | none |  | 3752.0 | 30016.0 | 1.052 | 1.732 | 0 | 1.000 | 0.67 |  | 41.8 |
| M-standalone-on-10k-mixed50 | mixed50-b8-c16 | none |  | 3762.3 | 30098.7 | 4.230 | 5.973 | 0 | 1.000 | 0.92 |  | 42.4 |
| M-standalone-on-10k-mixed50 | mixed50-b8-c64 | none |  | 3448.0 | 27584.0 | 9.436 | 18.146 | 293307 | 0.998 | 0.94 |  | 49.4 |
| M-standalone-on-10k-mixed50 | mixed50-b64-c1 | none |  | 494.7 | 31658.7 | 1.998 | 2.889 | 0 | 1.000 | 0.00 |  | 50.0 |
| M-standalone-on-10k-mixed50 | mixed50-b64-c4 | none |  | 506.0 | 32384.0 | 7.798 | 10.009 | 0 | 1.000 | 0.74 |  | 50.1 |
| M-standalone-on-10k-mixed50 | mixed50-b64-c16 | none |  | 500.7 | 32042.7 | 30.910 | 114.720 | 0 | 1.000 | 0.93 |  | 51.2 |
| M-standalone-on-10k-mixed50 | mixed50-b64-c64 | none |  | 460.7 | 29482.7 | 68.434 | 86.594 | 271199 | 0.991 | 0.97 |  | 53.2 |
| M-standalone-on-10k-lifecycle50-b1-c1 | lifecycle50-b1-c1 | none |  | 14517.0 | 14517.0 | 0.041 | 0.207 | 0 | 1.000 | 0.00 |  | 11.7 |
| M-standalone-on-10k-lifecycle50-b1-c4 | lifecycle50-b1-c4 | none |  | 29875.3 | 29875.3 | 0.120 | 0.349 | 0 | 1.000 | 0.30 |  | 15.5 |
| M-standalone-on-10k-lifecycle50-b1-c16 | lifecycle50-b1-c16 | none |  | 36430.0 | 36430.0 | 0.422 | 1.167 | 0 | 1.000 | 0.73 |  | 27.0 |
| M-standalone-on-10k-lifecycle50-b1-c64 | lifecycle50-b1-c64 | none |  | 41220.0 | 41220.0 | 1.067 | 3.352 | 128131 | 1.000 | 0.53 |  | 40.5 |
| M-standalone-on-10k-lifecycle50-b8-c1 | lifecycle50-b8-c1 | none |  | 3131.7 | 25053.3 | 0.306 | 0.655 | 0 | 1.000 | 0.00 |  | 11.9 |
| M-standalone-on-10k-lifecycle50-b8-c4 | lifecycle50-b8-c4 | none |  | 3933.7 | 31469.3 | 1.008 | 1.674 | 0 | 1.000 | 0.68 |  | 13.8 |
| M-standalone-on-10k-lifecycle50-b8-c16 | lifecycle50-b8-c16 | none |  | 4247.0 | 33976.0 | 3.755 | 5.789 | 0 | 1.000 | 0.92 |  | 24.1 |
| M-standalone-on-10k-lifecycle50-b8-c64 | lifecycle50-b8-c64 | none |  | 5627.3 | 45018.7 | 5.864 | 15.868 | 269221 | 0.999 | 0.91 |  | 36.1 |
| M-standalone-on-10k-lifecycle50-b64-c1 | lifecycle50-b64-c1 | none |  | 499.3 | 31957.3 | 1.982 | 2.848 | 0 | 1.000 | 0.00 |  | 12.1 |
| M-standalone-on-10k-lifecycle50-b64-c4 | lifecycle50-b64-c4 | none |  | 526.0 | 33664.0 | 7.581 | 9.529 | 0 | 1.000 | 0.73 |  | 13.4 |
| M-standalone-on-10k-lifecycle50-b64-c16 | lifecycle50-b64-c16 | none |  | 576.0 | 36864.0 | 27.862 | 33.354 | 0 | 1.000 | 0.93 |  | 22.9 |
| M-standalone-on-10k-lifecycle50-b64-c64 | lifecycle50-b64-c64 | none |  | 857.3 | 54869.3 | 37.388 | 65.704 | 261092 | 0.994 | 0.96 |  | 37.3 |
| M-source-on-10k | read100-b8-c4-none | none |  | 6793.3 | 54346.7 | 0.580 | 0.957 | 0 | 1.000 | 0.00 |  | 15.0 |
| M-source-on-10k | read100-b8-c4-import | import |  | 6678.4 | 53427.2 | 0.590 | 0.967 | 0 | 1.000 | 0.00 | 6 / 0 | 40.1 |
| M-source-on-10k | read100-b8-c4-events | events |  | 5550.3 | 44402.7 | 0.702 | 1.237 | 0 | 1.000 | 0.19 | 382336 / 0 | 43.2 |
| M-source-on-10k | read100-b8-c16-none | none |  | 11415.3 | 91322.7 | 0.985 | 4.297 | 0 | 0.991 | 0.00 |  | 86.0 |
| M-source-on-10k | read100-b8-c16-import | import |  | 11336.8 | 90694.4 | 1.014 | 4.123 | 0 | 0.994 | 0.01 | 6 / 0 | 111.0 |
| M-source-on-10k | read100-b8-c16-events | events |  | 9523.0 | 76184.0 | 1.619 | 4.034 | 0 | 1.000 | 0.36 | 165632 / 0 | 116.5 |
| M-source-on-10k | read100-b8-c64-none | none |  | 10241.3 | 81930.7 | 4.339 | 22.979 | 50444 | 0.998 | 0.00 |  | 149.5 |
| M-source-on-10k | read100-b8-c64-import | import |  | 10413.2 | 83305.6 | 4.163 | 19.375 | 69384 | 0.999 | 0.00 | 6 / 0 | 190.6 |
| M-source-on-10k | read100-b8-c64-events | events |  | 9699.3 | 77594.7 | 4.045 | 16.561 | 62248 | 0.999 | 0.16 | 62976 / 0 | 200.0 |
| M-standalone-on-100k | read95-b1-c1 | none |  | 1445.0 | 1445.0 | 0.546 | 1.965 | 0 | 1.000 | 0.00 |  | 45.2 |
| M-standalone-on-100k | read95-b1-c4 | none |  | 4682.7 | 4682.7 | 0.717 | 2.531 | 0 | 1.000 | 0.12 |  | 54.4 |
| M-standalone-on-100k | read95-b1-c16 | none |  | 5721.7 | 5721.7 | 2.303 | 12.734 | 0 | 0.999 | 0.43 |  | 225.0 |
| M-standalone-on-100k | read95-b1-c64 | none |  | 4562.3 | 4562.3 | 8.468 | 25.727 | 126638 | 0.999 | 0.49 |  | 234.0 |
| M-standalone-on-100k | read95-b8-c1 | none |  | 207.7 | 1661.3 | 4.713 | 8.211 | 0 | 1.000 | 0.00 |  | 234.5 |
| M-standalone-on-100k | read95-b8-c4 | none |  | 331.0 | 2648.0 | 11.566 | 28.526 | 0 | 1.000 | 0.58 |  | 238.5 |
| M-standalone-on-100k | read95-b8-c16 | none |  | 351.3 | 2810.7 | 44.402 | 98.386 | 0 | 0.999 | 0.87 |  | 242.3 |
| M-standalone-on-100k | read95-b8-c64 | none |  | 247.0 | 1976.0 | 125.677 | 287.148 | 270036 | 0.981 | 0.93 |  | 243.0 |
| M-standalone-on-100k | read95-b64-c1 | none |  | 26.3 | 1685.3 | 37.916 | 58.989 | 0 | 1.000 | 0.00 |  | 243.2 |
| M-standalone-on-100k | read95-b64-c4 | none |  | 26.7 | 1706.7 | 147.778 | 301.922 | 0 | 0.999 | 0.75 |  | 243.2 |
| M-standalone-on-100k | read95-b64-c16 | none |  | 26.7 | 1706.7 | 595.123 | 1086.536 | 0 | 0.990 | 0.94 |  | 246.0 |
| M-standalone-on-100k | read95-b64-c64 | none |  | 15.7 | 1002.7 | 1856.246 | 2010.758 | 278300 | 0.606 | 0.97 |  | 246.0 |
| M-standalone-on-100k-mixed50 | mixed50-b1-c1 | none |  | 2518.3 | 2518.3 | 0.095 | 1.894 | 0 | 1.000 | 0.00 |  | 45.0 |
| M-standalone-on-100k-mixed50 | mixed50-b1-c4 | none |  | 4259.7 | 4259.7 | 0.841 | 2.839 | 0 | 1.000 | 0.55 |  | 55.2 |
| M-standalone-on-100k-mixed50 | mixed50-b1-c16 | none |  | 4354.0 | 4354.0 | 3.542 | 8.087 | 0 | 1.000 | 0.87 |  | 96.0 |
| M-standalone-on-100k-mixed50 | mixed50-b1-c64 | none |  | 3210.0 | 3210.0 | 9.409 | 43.612 | 275051 | 0.997 | 0.92 |  | 141.5 |
| M-standalone-on-100k-mixed50 | mixed50-b8-c1 | none |  | 383.0 | 3064.0 | 2.483 | 6.004 | 0 | 1.000 | 0.00 |  | 142.8 |
| M-standalone-on-100k-mixed50 | mixed50-b8-c4 | none |  | 387.3 | 3098.7 | 10.248 | 16.919 | 0 | 1.000 | 0.74 |  | 142.9 |
| M-standalone-on-100k-mixed50 | mixed50-b8-c16 | none |  | 391.3 | 3130.7 | 40.287 | 58.964 | 0 | 1.000 | 0.93 |  | 145.3 |
| M-standalone-on-100k-mixed50 | mixed50-b8-c64 | none |  | 318.0 | 2544.0 | 98.096 | 191.331 | 288355 | 0.979 | 0.96 |  | 159.6 |
| M-standalone-on-100k-mixed50 | mixed50-b64-c1 | none |  | 50.3 | 3221.3 | 19.714 | 29.147 | 0 | 1.000 | 0.00 |  | 162.8 |
| M-standalone-on-100k-mixed50 | mixed50-b64-c4 | none |  | 50.0 | 3200.0 | 80.232 | 98.985 | 0 | 1.000 | 0.75 |  | 163.0 |
| M-standalone-on-100k-mixed50 | mixed50-b64-c16 | none |  | 49.7 | 3178.7 | 323.987 | 350.109 | 0 | 0.998 | 0.94 |  | 163.5 |
| M-standalone-on-100k-mixed50 | mixed50-b64-c64 | none |  | 36.7 | 2346.7 | 868.103 | 923.377 | 245064 | 0.852 | 0.98 |  | 171.5 |
| M-standalone-on-100k-lifecycle50-b1-c1 | lifecycle50-b1-c1 | none |  | 2550.0 | 2550.0 | 0.092 | 1.896 | 0 | 1.000 | 0.00 |  | 45.3 |
| M-standalone-on-100k-lifecycle50-b1-c4 | lifecycle50-b1-c4 | none |  | 4377.3 | 4377.3 | 0.816 | 2.796 | 0 | 1.000 | 0.55 |  | 54.1 |
| M-standalone-on-100k-lifecycle50-b1-c16 | lifecycle50-b1-c16 | none |  | 4376.7 | 4376.7 | 3.544 | 7.691 | 0 | 1.000 | 0.88 |  | 88.0 |
| M-standalone-on-100k-lifecycle50-b1-c64 | lifecycle50-b1-c64 | none |  | 3513.3 | 3513.3 | 8.532 | 40.225 | 274472 | 0.998 | 0.92 |  | 146.3 |
| M-standalone-on-100k-lifecycle50-b8-c1 | lifecycle50-b8-c1 | none |  | 386.3 | 3090.7 | 2.478 | 6.193 | 0 | 1.000 | 0.00 |  | 43.6 |
| M-standalone-on-100k-lifecycle50-b8-c4 | lifecycle50-b8-c4 | none |  | 389.7 | 3117.3 | 10.168 | 17.624 | 0 | 1.000 | 0.74 |  | 48.2 |
| M-standalone-on-100k-lifecycle50-b8-c16 | lifecycle50-b8-c16 | none |  | 391.0 | 3128.0 | 40.733 | 57.710 | 0 | 1.000 | 0.93 |  | 77.3 |
| M-standalone-on-100k-lifecycle50-b8-c64 | lifecycle50-b8-c64 | none |  | 353.3 | 2826.7 | 88.370 | 185.386 | 300112 | 0.985 | 0.97 |  | 118.3 |
| M-standalone-on-100k-lifecycle50-b64-c1 | lifecycle50-b64-c1 | none |  | 50.7 | 3242.7 | 19.442 | 29.153 | 0 | 1.000 | 0.00 |  | 44.5 |
| M-standalone-on-100k-lifecycle50-b64-c4 | lifecycle50-b64-c4 | none |  | 49.7 | 3178.7 | 79.775 | 98.808 | 0 | 1.000 | 0.75 |  | 50.7 |
| M-standalone-on-100k-lifecycle50-b64-c16 | lifecycle50-b64-c16 | none |  | 49.7 | 3178.7 | 321.372 | 358.885 | 0 | 0.998 | 0.93 |  | 79.1 |
| M-standalone-on-100k-lifecycle50-b64-c64 | lifecycle50-b64-c64 | none |  | 37.3 | 2389.3 | 830.378 | 958.284 | 277154 | 0.867 | 0.97 |  | 116.7 |
| M-source-on-100k | read100-b8-c4-none | none |  | 710.7 | 5685.3 | 5.568 | 9.670 | 0 | 1.000 | 0.00 |  | 66.6 |
| M-source-on-100k | read100-b8-c4-import | import |  | 688.0 | 5504.0 | 5.728 | 10.105 | 0 | 1.000 | 0.00 | 6 / 0 | 164.2 |
| M-source-on-100k | read100-b8-c4-events | events |  | 534.3 | 4274.7 | 7.192 | 14.631 | 0 | 1.000 | 0.28 | 65792 / 0 | 168.3 |
| M-source-on-100k | read100-b8-c16-none | none |  | 1017.7 | 8141.3 | 8.744 | 99.191 | 0 | 0.986 | 0.00 |  | 301.1 |
| M-source-on-100k | read100-b8-c16-import | import |  | 984.6 | 7876.8 | 9.287 | 93.428 | 0 | 0.993 | 0.02 | 6 / 0 | 440.3 |
| M-source-on-100k | read100-b8-c16-events | events |  | 840.0 | 6720.0 | 17.866 | 54.247 | 0 | 0.999 | 0.48 | 17024 / 0 | 445.1 |
| M-source-on-100k | read100-b8-c64-none | none |  | 567.3 | 4538.7 | 37.002 | 278.958 | 103547 | 0.983 | 0.00 |  | 446.8 |
| M-source-on-100k | read100-b8-c64-import | import |  | 623.6 | 4988.8 | 42.019 | 242.058 | 175011 | 0.993 | 0.04 | 6 / 0 | 552.2 |
| M-source-on-100k | read100-b8-c64-events | events |  | 702.7 | 5621.3 | 48.813 | 187.202 | 99929 | 0.990 | 0.20 | 5952 / 0 | 554.1 |
| M-open-off-100k | open-read95-b8-c16-f0.5 | none | 169.3 | 169.3 | 1354.7 | 9.803 | 44.249 | 0 | 1.000 | 0.08 |  | 54.9 |
| M-open-off-100k | open-read95-b8-c16-f0.9 | none | 304.8 | 305.0 | 2440.0 | 19.815 | 101.619 | 0 | 1.000 | 0.60 |  | 74.0 |
| M-open-off-100k | open-read95-b8-c16-f1.1 | none | 372.5 | 372.7 | 2981.3 | 280.610 | 675.094 | 0 | 1.000 | 0.13 |  | 81.5 |
| M-open-on-100k | open-read95-b8-c16-f0.5 | none | 175.7 | 175.7 | 1405.3 | 9.991 | 15.937 | 0 | 1.000 | 0.03 |  | 49.6 |
| M-open-on-100k | open-read95-b8-c16-f0.9 | none | 316.2 | 316.0 | 2528.0 | 31.652 | 103.461 | 0 | 1.000 | 0.67 |  | 84.3 |
| M-open-on-100k | open-read95-b8-c16-f1.1 | none | 386.5 | 386.3 | 3090.7 | 489.634 | 958.943 | 0 | 1.000 | 0.09 |  | 92.5 |
