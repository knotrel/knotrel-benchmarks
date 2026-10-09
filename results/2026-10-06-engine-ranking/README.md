# Current engine ranking — 2026-10-06

This campaign compares five engines in the same executable on identical operation traces. It includes the optimized HDT implementation and the caller-owned Compact workspace. No production algorithm was changed for this campaign.

## Main ranking

74 of 74 planned cells are complete. Each cell has three independent process trials per engine; its score is median workload runtime. Fresh and warmed regimes count separately. Repeated-query and ten-million-node supplements do not enter this ranking. Each cell has equal weight; these percentages describe this workload selection, not market share or a universal performance score.

| Engine | Wins | Share of cells | Faster than petgraph |
|---|---:|---:|---:|
| Compact (default) | 4 / 74 | 5.4% | 39 / 74 |
| Workspace (opt-in) | 16 / 74 | 21.6% | 44 / 74 |
| ETT (experimental) | 20 / 74 | 27.0% | 33 / 74 |
| HDT (experimental) | 16 / 74 | 21.6% | 38 / 74 |
| petgraph (external) | 18 / 74 | 24.3% | — |

54 / 74 winners have all three runtimes below every competitor's three runtimes. This range check is descriptive, not a significance test.

## Topology and scale

| Scope | Cells | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|
| Sparse 1,024 | 12 | 0 | 0 | 4 | 0 | 8 |
| Sparse 10,000 | 12 | 0 | 2 | 3 | 1 | 6 |
| Sparse 100,000 | 12 | 0 | 4 | 6 | 0 | 2 |
| Sparse 1,000,000 | 12 | 0 | 4 | 5 | 1 | 2 |
| dense | 24 | 4 | 6 | 0 | 14 | 0 |
| cogentco | 2 | 0 | 0 | 2 | 0 | 0 |

## Representative warmed cells

Runtime is the complete measured workload in milliseconds; parentheses show the percentage above the fastest engine in that cell. These are not individual query latencies.

| Workload | Nodes | Query mix | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|---:|
| sustained-churn-blocks-v1 | 100,000 | 10 | 0.859 (+15.9%) | 0.741 (+0.0%) | 6.268 (+746.0%) | 314.135 (+42295.8%) | 1.001 (+35.1%) |
| sustained-churn-blocks-v1 | 100,000 | 90 | 24.456 (+562.6%) | 23.716 (+542.6%) | 3.691 (+0.0%) | 216.863 (+5775.6%) | 39.159 (+961.0%) |
| sustained-churn-blocks-v1 | 1,000,000 | 10 | 5.278 (+10.1%) | 4.793 (+0.0%) | 67.710 (+1312.7%) | 4784.707 (+99730.4%) | 10.317 (+115.2%) |
| sustained-churn-blocks-v1 | 1,000,000 | 90 | 241.660 (+409.1%) | 244.649 (+415.4%) | 47.466 (+0.0%) | 3408.847 (+7081.6%) | 399.899 (+742.5%) |
| sustained-churn-path-v1 | 100,000 | 10 | 0.777 (+30.5%) | 0.632 (+6.3%) | 2.521 (+323.7%) | 3.075 (+416.8%) | 0.595 (+0.0%) |
| sustained-churn-path-v1 | 100,000 | 90 | 23.984 (+1342.6%) | 22.572 (+1257.7%) | 1.663 (+0.0%) | 2.193 (+31.9%) | 19.589 (+1078.3%) |
| sustained-churn-path-v1 | 1,000,000 | 10 | 4.750 (+23.6%) | 4.638 (+20.7%) | 7.920 (+106.1%) | 6.539 (+70.2%) | 3.842 (+0.0%) |
| sustained-churn-path-v1 | 1,000,000 | 90 | 207.840 (+4738.0%) | 211.704 (+4827.9%) | 5.660 (+31.7%) | 4.296 (+0.0%) | 178.505 (+4055.2%) |
| dense-bridge-churn-v1 | 512 | 90 | 17.366 (+103.9%) | 18.687 (+119.4%) | 38.311 (+349.8%) | 8.517 (+0.0%) | 174.487 (+1948.7%) |
| redundant-bridge-churn-v1 | 512 | 90 | 17.104 (+96.6%) | 18.336 (+110.8%) | 24.063 (+176.6%) | 8.700 (+0.0%) | 184.300 (+2018.5%) |
| topology-zoo-outages-v1 | 197 | import | 0.957 (+205.1%) | 0.584 (+86.2%) | 0.314 (+0.0%) | 0.433 (+38.2%) | 0.648 (+106.8%) |

## Decision and next experiment

Keep the current default and explicit engine choices. ETT leads the count of wins, but Workspace beats petgraph in more cells; winner count and head-to-head coverage answer different questions. No engine dominates this matrix. The broad labels sparse/dense and vertex count alone are insufficient for an automatic selector: query mix and mutation structure also change the winner.

Prioritize a structural profile of HDT on the preserved blocks-with-cycles traces. On the warmed one-million-node, 90% query cell, HDT takes about 3.41 seconds versus ETT 47.47 milliseconds (about 71.8 times the runtime), while HDT wins the one-million-node path at the same query ratio. This contrast makes replacement search and level promotions concrete profiling targets; it does not yet prove which internal step dominates.

Run counters outside the timed campaign, distinguish tree/non-tree cuts, replacement candidates, promotions by level, forest updates and allocation pressure. Start at 100,000 nodes, reproduce the pattern at one million, then test one targeted change with interleaved before/after trials on exactly these traces. Retain path, dense and Cogentco controls so a blocks improvement cannot conceal regressions elsewhere. No default switch or speculative optimization is part of this ranking.

## Memory and setup at one million vertices

Maximum observed process RSS and maximum available cell-median setup time across the one-million-node sparse cases, including successful observations from incomplete cells. RSS includes the harness, trace, setup and warmup; it is not engine heap usage. Maxima can come from different cells.

| Engine | Peak process RSS (MiB) | Largest median setup (s) | Successful trials |
|---|---:|---:|---:|
| Compact (default) | 207.9 | 0.218 | 36 |
| Workspace (opt-in) | 163.8 | 0.224 | 36 |
| ETT (experimental) | 790.5 | 3.344 | 36 |
| HDT (experimental) | 2201.1 | 2.087 | 36 |
| petgraph (external) | 125.7 | 0.083 | 36 |

## Supplements

- **repeats:** 4 complete cells; winners: ETT (experimental) 3, HDT (experimental) 1.
- **extreme:** 4 complete cells; winners: Workspace (opt-in) 3, petgraph (external) 1.

Repeated queries use two additional copies of each query in the 10,000-node, 90% query workload. Fresh/warmed runs do not flush hardware caches. None of these engines caches connectivity answers. At ten million nodes only Compact, Workspace and petgraph were attempted, with one trial per cell: exploratory evidence only. ETT and HDT were not attempted at that size on this shared 16 GiB host; this is a scope restriction, not an observed timeout or capacity failure.

## Meaning and limits

- Compact is the production default. Workspace is an opt-in, caller-owned query workspace; this result does not make it a server configuration or an automatic selector.
- ETT and HDT are Knotrel experimental implementations with exact connectivity semantics, not external competitors. Experimental denotes integration/maturity status, not approximate answers.
- petgraph 0.8.3 is the external Rust-library adapter with a fixed vertex universe, ID translation, reused DFS space and immediate mutation visibility. This is not a network-service comparison. GraphScope, Memgraph and Differential Dataflow were not measured.
- Synthetic sparse traces cover paths and blocks with cycles; dense traces cover bridge churn and redundant bridges. Ten rounds contain 1,000 operations. Holding this count fixed while scaling vertices changes the fraction of the graph mutated; it is not an asymptotic proof.
- Cogentco is one real network topology (197 vertices, 243 simple edges), with synthetic outages. It is not a fraud detector, an electrical simulation or a validation of domain semantics.
- Runtime is workload wall time including harness dispatch, assertions and timer sampling, excluding graph setup. Per-operation samples exclude correctness checks. Setup, operation tails and process RSS are separate in [details.md](details.md). Percentages never use reciprocal median latency as measured throughput.
- Trial order was shuffled deterministically, executions were sequential, and the same release binary and source hashes were required across all collections. No hardware-cache flush, CPU isolation or statistical confidence interval is claimed.
- 0 failed processes (0 timeouts) are retained in [comparison.json](comparison.json); [audit.json](audit.json) reports all 1,182 attempted processes. Incomplete cells are excluded explicitly from winner counts.

## Reproduction and references

Read [protocol.md](protocol.md), run the recorded collector commands, then `python3 results/2026-10-06-engine-ranking/analyze.py` then `python3 results/2026-10-06-engine-ranking/history.py` and `python3 results/2026-10-06-engine-ranking/report.py`. Collection directories ending in `-sparse`, `-dense`, `-cogentco`, `-repeats` and `-extreme` preserve manifests, commands, raw outputs, RSS logs, source/build metadata and artifact hashes. Analysis verifies every recorded artifact hash and matches trace fingerprints and actual operation/answer counts across engines.

The [matched historical comparison](historical-comparison.md) holds the original traces and competitor set fixed when reporting changes in ordering. The [original four-engine ranking](../2026-10-04-connectivity-campaign/ranking.md), [workspace comparison](../2026-10-04-workspace-v2-comparison/README.md), [HDT join comparison](../2026-10-05-hdt-joins/README.md), [traversal-order experiment](../2026-10-05-traversal-order/README.md) and [bitset experiment](../2026-10-05-traversal-bitset/README.md) remain separate historical references. This campaign is a current ranking, not an interleaved before/after experiment; changes relative to those days cannot be attributed solely to an optimization.
