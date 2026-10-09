# Algorithm and external-baseline ranking

This ranks the **last complete shared four-engine campaign**, not current code.
The source is `runtime-percentages.json`: 62 non-repeat scenario/cache-regime
cells, median replay wall time, setup excluded. Each cell has equal weight;
synthetic cells have two process trials, Cogentco four. Winners are observations,
not statistically established production rankings. Repeated-query cells are
reported separately. Memory, setup and tail latency are not included in this
single runtime ranking.

| Rank by first-place count | Implementation | Owner | First places |
|---|---|---|---:|
| 1 (tie) | Compact BFS | Knotrel default | 17/62 (27.4%) |
| 1 (tie) | petgraph DFS adapter | External library | 17/62 (27.4%) |
| 3 | ETT with replacement-edge scan | Knotrel experimental | 15/62 (24.2%) |
| 4 | HDT with sparse levels | Knotrel experimental | 13/62 (21.0%) |

These are implementations and adapters, not a ranking of abstract algorithms.
Counting whichever Knotrel backend wins as a single product result would assume
an oracle selector that the product does not have. Do not combine their wins.

## Where each implementation leads

| Family | Compact | ETT | HDT | External petgraph |
|---|---:|---:|---:|---:|
| Sparse: 36 cells | 5 | 13 | 1 | 17 |
| Dense: 24 cells | 12 | 0 | 12 | 0 |
| Cogentco: 2 regimes of one topology | 0 | 2 | 0 | 0 |
| Repeated-query supplement: 4 cells | 0 | 2 | 2 | 0 |

ETT is particularly competitive in sparse, query-heavy cases and Cogentco;
HDT is competitive in dense query-heavy cases, but the historical cyclic-block
promotion cost is severe. Compact and petgraph remain important controls for
mutation-heavy workloads. A 50% mutation ratio is not necessarily equal numbers
of links and cuts: the 100k path / 50% query trace has 498 cuts and only 2 links.

## Direct head-to-head with petgraph

For each of the same 62 cells, compare one fixed Knotrel backend with the
petgraph adapter, irrespective of whether a third engine is faster:

| Knotrel backend | Lower median runtime than petgraph | Higher median runtime |
|---|---:|---:|
| Compact | 33/62 (53.2%) | 29/62 |
| ETT | 26/62 (41.9%) | 36/62 |
| HDT | 32/62 (51.6%) | 30/62 |

This does not establish superiority over petgraph as a whole; it measures this
adapter, workload matrix and connectivity contract. It says nothing about market
adoption, network APIs or production reliability.

## Current-code caveat

The complete campaign predates caller-owned compact workspace v2, HDT local-ID
reuse and direct joins. Their later paired before/after collections provide
valid within-experiment comparisons, but cannot be spliced into this ranking:
other engines were not rerun contemporaneously in those collections. In
particular, multiplying historical runtimes by later speedup percentages would
hide baseline drift and measurement variability.

- Workspace v2 is optional and improves sparse/Cogentco cases against compact,
  with mixed dense results; it has no placement in this four-engine campaign.
- HDT direct joins improve cyclic-block/Cogentco timings in their paired study;
  the path follow-up shows the previously observed regression is not stable.
- Neither result establishes a new current-code winner over ETT or petgraph.

A current ranking requires one new common-build campaign including compact,
compact-workspace, ETT, current HDT and petgraph with preserved traces, balanced
execution order and sufficient independent trials. Report runtime, setup,
cut/query p95/p99 and RSS separately; retain fresh/warmed and repeat splits.

## Competitor coverage

Only **petgraph** participates as an external baseline in this shared campaign.
Earlier outils measurements are research controls, not evidence of product
adoption or a comparable market leader. Differential Dataflow, GraphScope and
Memgraph have no results in this campaign and receive no performance rank.
Comparing them requires an adapter and identical exact undirected connectivity
and mutation-visibility semantics; network/server costs must be separated from
embedded kernel cost. Repository stars, if reported later, need a dated source
and must not be treated as performance or production-readiness evidence.
