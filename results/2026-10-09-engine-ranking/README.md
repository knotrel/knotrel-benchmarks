# Current engine ranking — 2026-10-09

This campaign evaluates the five dynamic connectivity engines following the integration of packed 64-byte tokens in both experimental ETT and HDT. All five backends were executed in the same release binary on identical operation traces. No production algorithms or default configurations were altered.

## Main ranking

74 of 74 planned cells are complete. Each cell has three independent process trials per engine; its score is median workload runtime. Fresh and warmed regimes count separately. Repeated-query and ten-million-node supplements are excluded. Each cell has equal weight; these percentages describe this workload matrix, not universal superiority.

| Engine | Wins | Share of cells | Faster than petgraph |
|---|---:|---:|---:|
| Compact (default) | 3 / 74 | 4.1% | 40 / 74 |
| Workspace (opt-in) | 20 / 74 | 27.0% | 45 / 74 |
| ETT (experimental) | 19 / 74 | 25.7% | 35 / 74 |
| HDT (experimental) | 15 / 74 | 20.3% | 37 / 74 |
| petgraph (external) | 17 / 74 | 23.0% | — |

51 / 74 winners have all three runtimes strictly below every competitor's three runtimes. This range check is descriptive, not a significance test.

## Topology and scale

| Scope | Cells | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|
| Sparse 1,024 | 12 | 0 | 0 | 4 | 0 | 8 |
| Sparse 10,000 | 12 | 0 | 3 | 3 | 1 | 5 |
| Sparse 100,000 | 12 | 0 | 4 | 5 | 1 | 2 |
| Sparse 1,000,000 | 12 | 0 | 4 | 5 | 1 | 2 |
| dense | 24 | 3 | 9 | 0 | 12 | 0 |
| cogentco | 2 | 0 | 0 | 2 | 0 | 0 |

## Query mix breakdown

| Query percentage | Cells | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|
| 10% queries | 24 | 3 | 9 | 0 | 0 | 12 |
| 50% queries | 24 | 0 | 11 | 4 | 4 | 5 |
| 90% queries | 24 | 0 | 0 | 13 | 11 | 0 |
| Import (Cogentco) | 2 | 0 | 0 | 2 | 0 | 0 |

## Representative warmed cells

Runtime is the complete measured workload in milliseconds; parentheses show the percentage above the fastest engine in that cell. These are not individual query latencies.

| Workload | Nodes | Query mix | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | import | 0.904 (+191.9%) | 0.587 (+89.5%) | 0.310 (+0.0%) | 0.413 (+33.2%) | 0.648 (+109.3%) |
| dense-bridge-churn-v1 | 512 | 90 | 17.243 (+123.9%) | 16.996 (+120.7%) | 33.359 (+333.1%) | 7.701 (+0.0%) | 170.243 (+2110.5%) |
| redundant-bridge-churn-v1 | 512 | 90 | 17.026 (+120.0%) | 16.999 (+119.6%) | 21.126 (+172.9%) | 7.740 (+0.0%) | 180.622 (+2233.5%) |
| sustained-churn-blocks-v1 | 100,000 | 10 | 0.834 (+9.4%) | 0.762 (+0.0%) | 4.906 (+543.5%) | 292.090 (+38213.2%) | 1.001 (+31.3%) |
| sustained-churn-blocks-v1 | 100,000 | 90 | 24.177 (+713.7%) | 24.588 (+727.6%) | 2.971 (+0.0%) | 199.606 (+6618.3%) | 39.616 (+1233.4%) |
| sustained-churn-blocks-v1 | 1,000,000 | 10 | 5.254 (+10.0%) | 4.778 (+0.0%) | 54.417 (+1039.0%) | 4663.543 (+97513.8%) | 10.154 (+112.5%) |
| sustained-churn-blocks-v1 | 1,000,000 | 90 | 239.377 (+537.3%) | 252.416 (+572.0%) | 37.562 (+0.0%) | 3643.521 (+9600.0%) | 426.152 (+1034.5%) |
| sustained-churn-path-v1 | 100,000 | 10 | 0.696 (+29.5%) | 0.593 (+10.4%) | 2.123 (+294.9%) | 2.682 (+398.9%) | 0.538 (+0.0%) |
| sustained-churn-path-v1 | 100,000 | 90 | 23.415 (+1458.5%) | 22.462 (+1395.0%) | 1.710 (+13.8%) | 1.502 (+0.0%) | 21.110 (+1305.0%) |
| sustained-churn-path-v1 | 1,000,000 | 10 | 4.882 (+27.9%) | 5.003 (+31.1%) | 8.069 (+111.4%) | 5.451 (+42.8%) | 3.816 (+0.0%) |
| sustained-churn-path-v1 | 1,000,000 | 90 | 215.435 (+3250.3%) | 209.830 (+3163.2%) | 8.126 (+26.4%) | 6.430 (+0.0%) | 185.592 (+2786.2%) |

## Memory and setup at one million vertices

Maximum observed process RSS and maximum available cell-median setup time across the one-million-node sparse cases. RSS includes the harness, trace, setup, and warmup; it is not engine-only heap. Maxima can come from different cells.

| Engine | Peak process RSS (MiB) | Largest median setup (s) | Successful trials |
|---|---:|---:|---:|
| Compact (default) | 207.8 | 0.219 | 36 |
| Workspace (opt-in) | 165.4 | 0.217 | 36 |
| ETT (experimental) | 607.9 | 3.304 | 36 |
| HDT (experimental) | 1910.4 | 2.075 | 36 |
| petgraph (external) | 125.7 | 0.088 | 36 |

## Comparison with 2026-10-06 ranking

Across the identical 74 matched cells (see [historical-comparison.md](historical-comparison.md)):
- **ETT (experimental)**: Won 19/74 cells (vs 20/74). Experienced a median runtime speedup of **-8.81%** across all cells and **-17.64%** at 100k nodes. Memory decreased substantially: peak RSS at 1M nodes dropped from 790.5 MiB to **607.9 MiB** (-23.1%), with median -18.8% process RSS reduction across 1M sparse cells.
- **HDT (experimental)**: Won 15/74 cells (vs 16/74). Experienced a median runtime speedup of **-6.65%** across all cells and **-8.13%** at 100k nodes. Memory decreased substantially: peak RSS at 1M nodes dropped from 2201.1 MiB to **1910.4 MiB** (-13.2%), with median -16.8% process RSS reduction at 100k nodes.
- **Workspace (opt-in)**: Won 20/74 cells (vs 16/74). Outperformed petgraph in **45 / 74 cells** (60.8%), taking top spot in total wins in this campaign.
- **Compact (default)**: Won 3/74 cells (vs 4/74). Outperformed petgraph in **40 / 74 cells** (54.1%).
- **petgraph (external)**: Won 17/74 cells (vs 18/74). Retains leadership in small/medium sparse graphs with low query percentages due to ultra-lightweight initial setup.

## Decision and next recommended bottleneck

1. **Retain Current Roles**: Keep `compact-bfs` as production default and `compact-workspace` as the opt-in concurrent/query workspace. Retain `ett-scan` and `hdt` as experimental.
2. **Target HDT Cyclic Block Scalability**: While packed tokens successfully reduced HDT memory by ~15–17%, HDT remains dramatically slower than ETT on sparse graphs with cycles (`sustained-churn-blocks-v1`). On the warmed 1,000,000-node 90%-query cell, HDT takes ~3.3 seconds vs ETT ~41 milliseconds (~80× slower). The next priority must be structural profiling of replacement edge search and tree promotions in cyclic components.
3. **Target ETT Setup Overhead**: ETT is highly competitive on query-dominated sparse and Cogentco workloads, but its setup time at 1M nodes (3.357s) is ~13× higher than Compact (0.259s) and ~17× higher than petgraph (0.197s). Reducing vertex and initial-edge allocation overhead in ETT setup is the primary opportunity to broaden its competitive range.

## Meaning and limits

- **Knotrel vs External**: `compact-bfs`, `compact-workspace`, `ett-scan`, and `hdt` are Knotrel implementations. `petgraph` 0.8.3 is the external library comparison. GraphScope, Memgraph, and Differential Dataflow are not measured.
- **Memory Interpretation**: Peak RSS is the entire process resident memory (including trace loading, harness, and warmup), not engine-only heap.
- **No Throughput Inversion**: Throughput cannot be computed as the reciprocal of median operation latency.
- **Cache Regimes**: Warmed/fresh denotes workload repetition; CPU/L3 hardware caches are not cleared, and no engine caches query answers.
- **Percentiles**: Latency percentiles (p50/p95/p99) are per-process values and must not be pooled across executions.
- **Topology Scope**: Cogentco is a real network topology with synthetic failures, not a fraud or power-grid simulation.
- **Win Rates**: Win percentages reflect this 74-cell selection and do not imply universal dominance.

## Reproduction and references

To reproduce: inspect [protocol.md](protocol.md), run `python3 results/2026-10-09-engine-ranking/collect.py`, followed by `python3 results/2026-10-09-engine-ranking/analyze.py`, `python3 results/2026-10-09-engine-ranking/history.py`, and `python3 results/2026-10-09-engine-ranking/report.py`. All manifests, raw outputs, stderr logs, and artifact hashes are preserved in this directory.
