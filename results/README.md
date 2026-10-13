# Knotrel Benchmark Results

This directory contains benchmark and performance evaluation records for the latest version of Knotrel. Historical experiment runs, pilots, and campaign traces are preserved in the Git commit history, keeping the active working tree lean and focused while maintaining full reproducibility and provenance.

## Canonical Benchmark Suites

### 1. Dynamic Connectivity Engine Ranking (`ranking/`)
- **Detailed Report**: [ranking/README.md](ranking/README.md)
- **Scope**: Comprehensive 74-cell 5-engine evaluation (`Compact BFS`, `Compact Workspace`, `ETT`, `HDT`, `petgraph`) following the migration to `FxHashMap` in `knotrel-core` and 64-byte token packing in ETT/HDT.
- **Key Results**:
  - **Compact Workspace** leads with 31/74 wins (41.9%) and beats `petgraph` in 62/74 cells (83.8%).
  - **Experimental ETT** wins 22/74 cells (29.7%) and **HDT** wins 17/74 cells (23.0%), with 15–19% memory reductions at scale.
  - **All Knotrel engines combined** win **72 of 74 evaluated cells (97.3%)** over `petgraph`.

### 2. Apple M4 Hardware Profile (`hardware-profile/`)
- **Detailed Report**: [hardware-profile/README.md](hardware-profile/README.md)
- **Scope**: Replay-scoped CPU counters and signposted execution profiles on Apple M4 silicon under Xcode Instruments.
- **Key Results**:
  - 72 fixed paired recordings validating marker sequences, CPU counters, dense workload acceleration (~45%), and path variance.

### 3. Bulk Graph Initialization & Construction (`initialization/`)
- **Detailed Report**: [initialization/README.md](initialization/README.md)
- **Scope**: Phase 0 instrumentation, timing bounds, calibration, and replication data for bulk graph construction (`try_from_edges`).

### 4. Latest Performance Evaluation Summary (`perf_evaluation_latest.json`)
- Continuous performance metrics and regression gate output.

## Historical Evidence in Git

Prior milestone results, exploratory pilots, and campaign traces are archived in the Git repository history. To inspect historical data from earlier versions:

```sh
git log --stat -- results/
```
