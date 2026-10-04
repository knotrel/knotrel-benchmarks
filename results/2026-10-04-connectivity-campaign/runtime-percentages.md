# Runtime percentages by scenario — 2026-10-04

Runtime is `workload_wall_ns`, including dispatch, clock calls, assertions and
sample recording, but excluding setup, parsing and offline validation. This
differs from the sum of operation intervals in the main report.

The lowest median runtime in each scenario is the local baseline (0%).
`+100%` means twice its runtime; `+900%` means ten times its runtime.
The JSON also gives signed deltas against Knotrel compact, the default:
negative means less runtime. A 90% time reduction is not a 90% speedup.

Each scenario has equal weight, including separate fresh/warmed regimes.
Win counts reflect this chosen matrix, not production workload prevalence.
Repeated-query scenarios are reported separately and excluded from overall.
Observed trial-range separation is descriptive, not statistical significance.

| Family | Scenarios | Knotrel compact wins | Knotrel ETT wins | Knotrel HDT wins | External petgraph wins |
| --- | ---: | ---: | ---: | ---: | ---: |
| overall | 62 | 17 (27.4%) | 15 (24.2%) | 13 (21.0%) | 17 (27.4%) |
| sparse | 36 | 5 (13.9%) | 13 (36.1%) | 1 (2.8%) | 17 (47.2%) |
| dense | 24 | 12 (50.0%) | 0 (0.0%) | 12 (50.0%) | 0 (0.0%) |
| cogentco | 2 | 0 (0.0%) | 2 (100.0%) | 0 (0.0%) | 0 (0.0%) |
| repeats | 4 | 0 (0.0%) | 2 (50.0%) | 2 (50.0%) | 0 (0.0%) |

Overall, 56 of 62 winners have runtime trial ranges below all other engines' ranges; no confidence interval is inferred.

Each table row: workload / nodes / query percentage / cache regime. Entries
are percentage **more runtime than the row winner**. `overlap` means the
winner's observed range overlaps at least one competitor; rankings may be fragile.

## sparse

| Scenario | Winner | Best runtime ms | Compact Δ% | ETT Δ% | HDT Δ% | Petgraph Δ% | Range check |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| sustained-churn-blocks-v1 / 1024 / 10 / fresh | External petgraph | 0.105 | +71.8% | +857.4% | +3602.4% | +0.0% | separated |
| sustained-churn-blocks-v1 / 1024 / 10 / warmed | External petgraph | 0.097 | +33.7% | +849.7% | +3585.0% | +0.0% | separated |
| sustained-churn-blocks-v1 / 1024 / 50 / fresh | External petgraph | 0.245 | +70.5% | +181.8% | +1145.4% | +0.0% | separated |
| sustained-churn-blocks-v1 / 1024 / 50 / warmed | External petgraph | 0.282 | +20.9% | +124.5% | +943.6% | +0.0% | separated |
| sustained-churn-blocks-v1 / 1024 / 90 / fresh | Knotrel ETT | 0.277 | +153.0% | +0.0% | +683.0% | +85.9% | separated |
| sustained-churn-blocks-v1 / 1024 / 90 / warmed | Knotrel ETT | 0.249 | +145.6% | +0.0% | +709.4% | +100.6% | separated |
| sustained-churn-blocks-v1 / 10000 / 10 / fresh | External petgraph | 0.235 | +20.9% | +552.4% | +16475.4% | +0.0% | separated |
| sustained-churn-blocks-v1 / 10000 / 10 / warmed | External petgraph | 0.225 | +10.5% | +649.5% | +16814.3% | +0.0% | separated |
| sustained-churn-blocks-v1 / 10000 / 50 / fresh | External petgraph | 0.914 | +7.0% | +28.5% | +4063.0% | +0.0% | overlap |
| sustained-churn-blocks-v1 / 10000 / 50 / warmed | Knotrel compact | 0.859 | +0.0% | +28.1% | +4073.7% | +3.5% | separated |
| sustained-churn-blocks-v1 / 10000 / 90 / fresh | Knotrel ETT | 0.619 | +354.5% | +0.0% | +3862.8% | +612.3% | separated |
| sustained-churn-blocks-v1 / 10000 / 90 / warmed | Knotrel ETT | 0.570 | +408.1% | +0.0% | +4126.5% | +690.4% | separated |
| sustained-churn-blocks-v1 / 100000 / 10 / fresh | Knotrel compact | 0.963 | +0.0% | +554.5% | +46775.8% | +3.4% | overlap |
| sustained-churn-blocks-v1 / 100000 / 10 / warmed | Knotrel compact | 0.926 | +0.0% | +550.7% | +48071.1% | +7.2% | overlap |
| sustained-churn-blocks-v1 / 100000 / 50 / fresh | Knotrel compact | 5.172 | +0.0% | +20.6% | +8931.2% | +42.2% | separated |
| sustained-churn-blocks-v1 / 100000 / 50 / warmed | Knotrel compact | 5.169 | +0.0% | +24.1% | +8877.8% | +54.4% | separated |
| sustained-churn-blocks-v1 / 100000 / 90 / fresh | Knotrel ETT | 3.568 | +588.1% | +0.0% | +8712.8% | +1004.1% | separated |
| sustained-churn-blocks-v1 / 100000 / 90 / warmed | Knotrel ETT | 3.852 | +520.1% | +0.0% | +8432.8% | +938.5% | separated |
| sustained-churn-path-v1 / 1024 / 10 / fresh | External petgraph | 0.093 | +43.1% | +459.2% | +501.2% | +0.0% | separated |
| sustained-churn-path-v1 / 1024 / 10 / warmed | External petgraph | 0.077 | +35.0% | +531.7% | +541.0% | +0.0% | separated |
| sustained-churn-path-v1 / 1024 / 50 / fresh | External petgraph | 0.131 | +58.6% | +198.8% | +211.7% | +0.0% | separated |
| sustained-churn-path-v1 / 1024 / 50 / warmed | External petgraph | 0.110 | +65.5% | +218.1% | +220.5% | +0.0% | separated |
| sustained-churn-path-v1 / 1024 / 90 / fresh | Knotrel ETT | 0.205 | +137.2% | +0.0% | +5.3% | +97.0% | separated |
| sustained-churn-path-v1 / 1024 / 90 / warmed | Knotrel ETT | 0.182 | +152.4% | +0.0% | +4.2% | +79.1% | separated |
| sustained-churn-path-v1 / 10000 / 10 / fresh | External petgraph | 0.165 | +24.1% | +457.2% | +539.2% | +0.0% | separated |
| sustained-churn-path-v1 / 10000 / 10 / warmed | External petgraph | 0.143 | +24.4% | +447.0% | +533.9% | +0.0% | separated |
| sustained-churn-path-v1 / 10000 / 50 / fresh | External petgraph | 0.499 | +67.4% | +57.1% | +51.3% | +0.0% | separated |
| sustained-churn-path-v1 / 10000 / 50 / warmed | External petgraph | 0.513 | +28.9% | +11.0% | +62.5% | +0.0% | overlap |
| sustained-churn-path-v1 / 10000 / 90 / fresh | Knotrel HDT | 0.468 | +464.6% | +2.3% | +0.0% | +414.9% | overlap |
| sustained-churn-path-v1 / 10000 / 90 / warmed | Knotrel ETT | 0.364 | +608.3% | +0.0% | +83.2% | +556.3% | separated |
| sustained-churn-path-v1 / 100000 / 10 / fresh | External petgraph | 0.620 | +29.4% | +378.0% | +453.9% | +0.0% | separated |
| sustained-churn-path-v1 / 100000 / 10 / warmed | External petgraph | 0.591 | +34.7% | +335.7% | +511.6% | +0.0% | separated |
| sustained-churn-path-v1 / 100000 / 50 / fresh | Knotrel ETT | 2.774 | +63.5% | +0.0% | +16.1% | +23.1% | separated |
| sustained-churn-path-v1 / 100000 / 50 / warmed | Knotrel ETT | 2.194 | +105.7% | +0.0% | +42.9% | +64.5% | separated |
| sustained-churn-path-v1 / 100000 / 90 / fresh | Knotrel ETT | 2.127 | +1000.6% | +0.0% | +43.5% | +823.8% | separated |
| sustained-churn-path-v1 / 100000 / 90 / warmed | Knotrel ETT | 1.906 | +1119.8% | +0.0% | +14.9% | +928.3% | overlap |

## dense

| Scenario | Winner | Best runtime ms | Compact Δ% | ETT Δ% | HDT Δ% | Petgraph Δ% | Range check |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| dense-bridge-churn-v1 / 128 / 10 / fresh | Knotrel compact | 0.170 | +0.0% | +8548.6% | +423.4% | +400.5% | separated |
| dense-bridge-churn-v1 / 128 / 10 / warmed | Knotrel compact | 0.167 | +0.0% | +8235.0% | +445.1% | +406.2% | separated |
| dense-bridge-churn-v1 / 128 / 50 / fresh | Knotrel compact | 0.696 | +0.0% | +1061.9% | +3.5% | +545.0% | separated |
| dense-bridge-churn-v1 / 128 / 50 / warmed | Knotrel compact | 0.672 | +0.0% | +1097.9% | +5.3% | +536.2% | separated |
| dense-bridge-churn-v1 / 128 / 90 / fresh | Knotrel HDT | 0.586 | +90.9% | +182.6% | +0.0% | +1207.5% | separated |
| dense-bridge-churn-v1 / 128 / 90 / warmed | Knotrel HDT | 0.556 | +101.4% | +201.2% | +0.0% | +1312.5% | separated |
| dense-bridge-churn-v1 / 512 / 10 / fresh | Knotrel compact | 1.887 | +0.0% | +17102.3% | +379.2% | +849.8% | separated |
| dense-bridge-churn-v1 / 512 / 10 / warmed | Knotrel compact | 1.851 | +0.0% | +17191.3% | +364.9% | +808.5% | separated |
| dense-bridge-churn-v1 / 512 / 50 / fresh | Knotrel HDT | 8.336 | +7.7% | +2117.9% | +0.0% | +982.1% | separated |
| dense-bridge-churn-v1 / 512 / 50 / warmed | Knotrel HDT | 8.386 | +7.2% | +2063.1% | +0.0% | +998.2% | separated |
| dense-bridge-churn-v1 / 512 / 90 / fresh | Knotrel HDT | 8.703 | +94.4% | +315.8% | +0.0% | +1763.9% | separated |
| dense-bridge-churn-v1 / 512 / 90 / warmed | Knotrel HDT | 8.131 | +98.1% | +344.3% | +0.0% | +1898.2% | separated |
| redundant-bridge-churn-v1 / 128 / 10 / fresh | Knotrel compact | 0.177 | +0.0% | +5322.9% | +412.9% | +464.0% | separated |
| redundant-bridge-churn-v1 / 128 / 10 / warmed | Knotrel compact | 0.172 | +0.0% | +5537.2% | +401.6% | +474.3% | separated |
| redundant-bridge-churn-v1 / 128 / 50 / fresh | Knotrel compact | 0.735 | +0.0% | +635.2% | +5.5% | +540.0% | separated |
| redundant-bridge-churn-v1 / 128 / 50 / warmed | Knotrel compact | 0.669 | +0.0% | +693.9% | +11.4% | +592.9% | separated |
| redundant-bridge-churn-v1 / 128 / 90 / fresh | Knotrel HDT | 0.590 | +97.2% | +90.3% | +0.0% | +1360.2% | separated |
| redundant-bridge-churn-v1 / 128 / 90 / warmed | Knotrel HDT | 0.621 | +81.1% | +80.9% | +0.0% | +1244.1% | separated |
| redundant-bridge-churn-v1 / 512 / 10 / fresh | Knotrel compact | 1.828 | +0.0% | +11148.8% | +370.6% | +950.5% | separated |
| redundant-bridge-churn-v1 / 512 / 10 / warmed | Knotrel compact | 1.870 | +0.0% | +11013.4% | +391.9% | +940.1% | separated |
| redundant-bridge-churn-v1 / 512 / 50 / fresh | Knotrel HDT | 8.732 | +4.6% | +1285.8% | +0.0% | +1118.9% | separated |
| redundant-bridge-churn-v1 / 512 / 50 / warmed | Knotrel HDT | 8.382 | +8.1% | +1317.1% | +0.0% | +1064.4% | separated |
| redundant-bridge-churn-v1 / 512 / 90 / fresh | Knotrel HDT | 8.354 | +95.8% | +171.6% | +0.0% | +1954.7% | separated |
| redundant-bridge-churn-v1 / 512 / 90 / warmed | Knotrel HDT | 8.318 | +93.7% | +177.9% | +0.0% | +1941.4% | separated |

## cogentco

| Scenario | Winner | Best runtime ms | Compact Δ% | ETT Δ% | HDT Δ% | Petgraph Δ% | Range check |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| topology-zoo-outages-v1 / 197 / domain schedule / fresh | Knotrel ETT | 0.361 | +204.4% | +0.0% | +51.4% | +98.4% | separated |
| topology-zoo-outages-v1 / 197 / domain schedule / warmed | Knotrel ETT | 0.317 | +207.0% | +0.0% | +52.1% | +110.6% | separated |

## repeats

| Scenario | Winner | Best runtime ms | Compact Δ% | ETT Δ% | HDT Δ% | Petgraph Δ% | Range check |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| sustained-churn-blocks-v1 / 10000 / 90 / fresh | Knotrel ETT | 0.839 | +900.9% | +0.0% | +2834.1% | +1285.4% | separated |
| sustained-churn-blocks-v1 / 10000 / 90 / warmed | Knotrel ETT | 0.743 | +1007.3% | +0.0% | +3140.7% | +1689.0% | separated |
| sustained-churn-path-v1 / 10000 / 90 / fresh | Knotrel HDT | 0.686 | +990.1% | +2.8% | +0.0% | +925.5% | overlap |
| sustained-churn-path-v1 / 10000 / 90 / warmed | Knotrel HDT | 0.494 | +1408.4% | +4.2% | +0.0% | +1135.4% | separated |

Raw medians, trial ranges and signed deltas against Knotrel compact are in
[runtime-percentages.json](runtime-percentages.json). Rebuild both with
`python3 results/2026-10-04-connectivity-campaign/percentages.py`.

See the [main report](README.md) for memory, operation tails, provenance and
limitations. Runtime winners are not necessarily memory or startup winners.
No historical measurement, source hash or original aggregate was changed.
