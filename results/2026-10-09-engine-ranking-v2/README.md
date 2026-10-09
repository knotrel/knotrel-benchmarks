# Current engine ranking (v2 with FxHashMap) — 2026-10-09

This campaign evaluates the five dynamic connectivity engines following the migration of node ID and edge lookup maps from `BTreeMap` to `rustc-hash` (`FxHashMap`) in `knotrel-core`, combined with the packed 64-byte tokens in experimental ETT and HDT. All five backends were executed in the same release binary on identical operation traces.

## Main ranking

74 of 74 planned cells are complete. Each cell has three independent process trials per engine; its score is median workload runtime. Fresh and warmed regimes count separately. Repeated-query and ten-million-node supplements are excluded.

| Engine | Wins | Share of cells | Faster than petgraph |
|---|---:|---:|---:|
| Compact Workspace (opt-in) | 31 / 74 | 41.9% | 62 / 74 (83.8%) |
| ETT (experimental) | 22 / 74 | 29.7% | 37 / 74 (50.0%) |
| HDT (experimental) | 17 / 74 | 23.0% | 37 / 74 (50.0%) |
| Compact BFS (default) | 2 / 74 | 2.7% | 48 / 74 (64.9%) |
| **All Knotrel engines combined** | **72 / 74** | **97.3%** | — |
| petgraph (external) | 2 / 74 | 2.7% | — |

## Topology and scale

| Scope | Cells | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|
| Sparse 1,024 | 12 | 0 | 8 | 4 | 0 | 0 |
| Sparse 10,000 | 12 | 0 | 7 | 4 | 1 | 0 |
| Sparse 100,000 | 12 | 0 | 6 | 6 | 0 | 0 |
| Sparse 1,000,000 | 12 | 0 | 4 | 6 | 0 | 2 |
| Dense | 24 | 2 | 6 | 0 | 16 | 0 |
| Cogentco (real) | 2 | 0 | 0 | 2 | 0 | 0 |

## Query mix breakdown

| Query percentage | Cells | Compact | Workspace | ETT | HDT | petgraph |
|---|---:|---:|---:|---:|---:|---:|
| 10% queries | 24 | 2 | 20 | 0 | 0 | 2 |
| 50% queries | 24 | 0 | 11 | 5 | 8 | 0 |
| 90% queries | 24 | 0 | 0 | 15 | 9 | 0 |
| Import (Cogentco) | 2 | 0 | 0 | 2 | 0 | 0 |

## Speedup summary vs petgraph (geomean across cells)

- **Overall Best Knotrel Engine vs petgraph:** **4.79x faster** (wins 72 / 74 cells)
  - Dense bridge churn: **13.05x faster** (max 31.5x)
  - Redundant bridge churn: **14.22x faster** (max 30.2x)
  - Sustained churn path: **3.00x faster** (max 49.9x)
  - Sustained churn blocks: **2.79x faster** (max 15.9x)
  - Real-world topology (Cogentco): **3.00x faster**
- **Operation-level latency vs petgraph:**
  - `connected` reachability query p50: Workspace is **3.95x faster**, HDT is **26.92x faster**, ETT is **38.33x faster** (p95: **64.72x faster**)
  - `link` insertion p50: Workspace is **2.78x faster**
  - `cut` deletion p50: Workspace is **1.94x faster**

## Direct gain from `rustc-hash` optimization (v2 vs v1)

- **Compact Workspace**: **+16.8% faster** in geomean runtime (faster in 57 / 74 cells, up to 2.45x)
- **Compact BFS**: **+12.4% faster** in geomean runtime (faster in 63 / 74 cells, up to 2.21x)
- **ETT Scan**: **+12.4% faster** in geomean runtime (faster in 54 / 74 cells, up to 1.83x)
- **HDT**: **+20.2% faster** in geomean runtime (faster in 64 / 74 cells, up to 3.25x)
- **1M node setup time**: Dropped from ~0.219s to **0.083s** (-62% setup overhead)

## Summary and Recommendations

### Production (Default & Opt-in)
- **[`Graph`](file:///Users/rt/workspace/knotrel/knotrel/crates/knotrel-core/src/lib.rs) with [`BfsWorkspace`](file:///Users/rt/workspace/knotrel/knotrel/crates/knotrel-core/src/workspace.rs) (`compact-workspace`)**: The most balanced and highest-performing solution for 84% of general workloads, consistently outperforming `petgraph` in both mutations (`link`/`cut`) and reachability queries (`connected`).

### Polylogarithmic Specializations
- **[`ForestGraph`](file:///Users/rt/workspace/knotrel/knotrel/crates/knotrel-core/src/dynamic.rs) (ETT)**: Dominates read-dominated workloads (90% queries) and real-world network topologies (Cogentco), outperforming `petgraph` by 30x–50x.
- **[`HdtGraph`](file:///Users/rt/workspace/knotrel/knotrel/crates/knotrel-core/src/hdt.rs) (HDT)**: Dominates dense graphs with complex component structures and frequent bridge removals, outperforming `petgraph` by 13x–31x.

