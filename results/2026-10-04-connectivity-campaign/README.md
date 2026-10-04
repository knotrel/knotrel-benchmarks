# Knotrel versus petgraph: measured tradeoffs — 2026-10-04

**544 isolated process runs completed with no failures.** This is an exploratory
embedded-kernel campaign, not an HTTP/service benchmark or a product leaderboard.
The [prespecified protocol](../../docs/experiments/2026-10-04-connectivity-campaign.md)
records the matrix and its limits. Existing engine/generator code was not changed.

For per-scenario percentage gaps, winner frequencies and signed deltas against
the default, see [runtime percentages](runtime-percentages.md) and
[optimization candidates](optimization-notes.md). Those use replay wall time;
the tables below retain the original summed operation intervals.

## Ownership and conclusions

- **Knotrel default:** `compact-bfs` (compact adjacency, traversal per query).
- **Knotrel experimental:** `ett-scan` (ETT) and `hdt` (sparse HDT v3).
- **External baseline:** `petgraph-dfs`, petgraph 0.8.3 through our adapter.
  ETT/HDT here are Knotrel implementations, not independent products.

The evidence supports keeping the default unchanged for now. ETT improves
query-heavy sparse workloads at substantial memory cost. HDT performs better
than ETT on these dense bridge controls, but its expensive cuts on cyclic blocks
make it a poor general default. Petgraph remains competitive on update-heavy
sparse workloads; those unfavorable results are retained below.

## Coverage and how to read the numbers

| Collection | Completed processes | Scope |
| --- | ---: | --- |
| [Sparse](../2026-10-04-sparse-campaign/manifest.json) | 288 | 1,024 / 10,000 / 100,000 vertices; paths and cyclic blocks; 10/50/90% queries |
| [Dense](../2026-10-04-dense-campaign/manifest.json) | 192 | 128 / 512 vertices; two-clique bridge and redundant bridge |
| [Repeated queries](../2026-10-04-repeats-campaign/manifest.json) | 32 | 10,000 vertices, 90% queries; two immediate extra queries |
| [Cogentco](../2026-10-04-cogentco-campaign/manifest.json) | 32 | Real 197-vertex, 243-edge topology; synthetic outages |

Synthetic cells have two process trials per engine and cache regime, 1,000 base
operations per process. Cogentco has four trials per regime. “Fresh” means zero
explicit warmups; “warmed” means one full warmup. Both use fresh graphs and
uncontrolled CPU/OS caches. Synthetic process order is globally shuffled with a
fixed seed; real-topology engine order rotates through all four positions.
No competing benchmark processes were intentionally run concurrently.
[Host metadata](environment.json) records CPU, memory and platform; CPU affinity,
power state and thermals were not controlled or instrumented.

Tables show **warmed** cells. Each number is the median across process trials;
query ranges show the minimum and maximum per-process p50. These are not pooled
percentiles or confidence intervals. [summary.json](summary.json) contains both
regimes and trial ranges for p50/p95/p99, update/query counts, setup, totals and
RSS. Rebuild it with `python3 results/2026-10-04-connectivity-campaign/summarize.py`.

“Base operation sum” adds recorded cut/link/connected intervals, excluding setup,
validation, sample handling and extra repeated queries. It is not service latency
or measured throughput. RSS is peak **whole-process** memory, including traces,
export buffers, warmup and harness; it is not engine heap size. Small sub-µs
samples are sensitive to timer resolution/overhead.

## Sparse query-heavy workload: 100,000 vertices, 90% queries

### Cyclic blocks

| Implementation | Query p50, µs (trial range) | Cut p50, µs | Base operation sum, ms | Peak process RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Knotrel default / compact BFS | 17.417 (17.292–17.542) | 0.188 | 23.858 | 16.8 |
| Knotrel experimental / ETT | 1.021 (0.958–1.084) | 10.375 | 3.831 | 83.6 |
| Knotrel experimental / HDT | 2.250 (2.000–2.500) | 1191.646 | 328.640 | 206.8 |
| External / petgraph 0.8.3 DFS | 28.396 (28.292–28.500) | 0.208 | 39.978 | 14.1 |

This trace has 100 cuts and 900 queries, with no links at this size/seed. ETT's
base-operation sum is about 6.2× lower than Knotrel compact BFS and 10.4× lower
than petgraph in these warmed trials, while its whole-process RSS is about 5×
compact BFS's. HDT's cuts erase its query advantage: the summed intervals are
about 13.8× compact BFS's. These ratios describe this trace, not all applications.

One HDT trial records 212,272 tree promotions and 12,317 non-tree promotions.
That is a useful profiling target, not proof of which function consumes time.
The raw cut tails and both trials are preserved; query p50 alone hides this cost.

### Path

| Implementation | Query p50, µs (trial range) | Cut p50, µs | Base operation sum, ms | Peak process RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Knotrel default / compact BFS | 13.541 (13.500–13.583) | 0.291 | 23.233 | 16.7 |
| Knotrel experimental / ETT | 1.229 (1.000–1.458) | 3.250 | 1.886 | 82.2 |
| Knotrel experimental / HDT | 1.104 (1.083–1.125) | 3.688 | 2.170 | 107.4 |
| External / petgraph 0.8.3 DFS | 11.083 (11.000–11.166) | 0.208 | 19.580 | 13.8 |

The same engines behave differently when replacement structure changes. HDT is
close to ETT here, unlike the cyclic-block case. Kernel choice must account for
mutation topology and memory, not just vertex count or query complexity.

## Update-heavy counterexample: 100,000-vertex path, 10% queries

| Implementation | Query p50, µs (trial range) | Cut p50, µs | Base operation sum, ms | Peak process RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Knotrel default / compact BFS | 3.354 (3.291–3.417) | 0.208 | 0.773 | 16.7 |
| Knotrel experimental / ETT | 1.250 (1.083–1.416) | 2.229 | 2.556 | 82.2 |
| Knotrel experimental / HDT | 1.646 (1.333–1.959) | 2.500 | 3.595 | 107.4 |
| External / petgraph 0.8.3 DFS | 2.375 (2.250–2.500) | 0.145 | 0.570 | 13.9 |

Petgraph has the lowest base-operation sum here. Both maintained Knotrel backends
pay more for updates than they save on the 100 queries. This is why we do not
replace the default or claim blanket superiority from the query-heavy rows.

## Dense control: 512 vertices, one bridge, 90% queries

| Implementation | Query p50, µs (trial range) | Cut p50, µs | Base operation sum, ms | Peak process RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Knotrel default / compact BFS | 34.145 (34.083–34.208) | 0.083 | 16.089 | 6.3 |
| Knotrel experimental / ETT | 0.125 (0.125–0.125) | 708.146 | 36.103 | 12.2 |
| Knotrel experimental / HDT | 0.083 (0.083–0.083) | 0.584 | 8.110 | 13.8 |
| External / petgraph 0.8.3 DFS | 199.250 (192.708–205.792) | 0.042 | 162.433 | 6.3 |

There are 65,281 initial edges, 50 cuts, 50 links and 900 queries. The dense graph
has fewer vertices but many more edges than a similarly sized sparse topology.
ETT's replacement scans are expensive; HDT improves the aggregate on this control.
Its low cut p50 must still be read with total and tail costs. The redundant-bridge
variant and update-heavy mixes are included in summary.json, not omitted.

## Real topology: Cogentco

| Implementation | Query p50, µs (trial range) | Cut p50, µs | Base operation sum, ms | Peak process RSS, MiB |
| --- | ---: | ---: | ---: | ---: |
| Knotrel default / compact BFS | 0.334 (0.292–0.375) | 0.042 | 0.929 | 6.3 |
| Knotrel experimental / ETT | 0.062 (0.042–0.083) | 0.834 | 0.275 | 6.3 |
| Knotrel experimental / HDT | 0.083 (0.083–0.083) | 1.375 | 0.439 | 6.4 |
| External / petgraph 0.8.3 DFS | 0.208 (0.208–0.209) | 0.042 | 0.624 | 6.3 |

The source is [Cogentco GraphML at pinned revision](https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/51118849b99534f01010d885d66321433a7eef9e/graphml/Cogentco.graphml),
SHA-256 `fca525c7484c1044feb09add79fec0861d4b234622e5d07b7d202470ad0a09ca`.
It starts connected with 32 projected bridges. One hundred seeded physical-link
failures followed by reverse repairs produce 200 batches and 1,800 scheduled
queries (732 true, 1,068 false). All pass independent validation and backend replay.

Data attribution: Knight, Nguyen, Falkner, Bowden and Roughan, *The Internet
Topology Zoo*, IEEE JSAC 2011, DOI 10.1109/JSAC.2011.111002; archive CC-BY-4.0,
[license at the pinned revision](https://raw.githubusercontent.com/mroughan/InternetTopologyZoo/51118849b99534f01010d885d66321433a7eef9e/LICENSE).
Outages and query schedule are ours, not operator observations. This is a larger
real case than Abilene, but 197 nodes do not establish industrial-scale behavior.

## Cache sensitivity and limitations

The supplement keeps base queries and immediate repeats separate. For example,
ETT on warmed 10,000-vertex cyclic blocks has a base-query median p50 of 0.208 µs
and immediate-repeat p50 of 0.083 µs. This is compatible with locality effects,
but does not isolate CPU cache behavior or prove an application answer cache.
Fresh/warmed and repeat/no-repeat process cells remain separate in summary.json.

Important limits: one graph seed; only two synthetic process trials; fixed short
operation counts across sizes; no steady-state guarantee. At 100,000 vertices,
the 90%-query sparse traces contain only cuts, whereas smaller versions include
some relinks. Therefore their timing curves are not a controlled empirical proof
of asymptotic complexity. Graph fragmentation and reachable component size matter.
No directed reachability, graph properties, authorization, fraud classification,
network IO, concurrent clients, persistence or multi-tenant admission is measured.
No production or market-superiority claims follow.

## Reproduction and next decision

The four collection manifests preserve exact commands, trace fingerprints,
source and binary hashes, checkout state, patches, failures and RSS stderr.
Large synthetic trace exports remain ignored local files. Cogentco's original
input and imported trace remain outside Git: use the adapter guide with the
source above, `--failures 100 --seed 42 --queries 8`, acquisition date 2026-10-04,
and the manifest's exact provenance text. The collection retains `collect.py`
for rotating isolated imported replays. Historical paths may need relocation.

[Audit](audit.json) records checksum verification of every original manifest
artifact, identical per-cell traces across backends and matching build inputs
across collections. A fresh clone lacks ignored traces; it can rebuild aggregates
from raw measurement JSON but cannot repeat the full local artifact audit until
traces are regenerated. See [publication policy](../README.md).

Next optimization target: profile HDT cut/promotion costs on cyclic blocks,
retain the dense controls to avoid losing HDT's strengths, and check changes on
all four engines' unchanged traces. Expand to multiple seeds, longer balanced
update histories and more real topologies before choosing a new default.
