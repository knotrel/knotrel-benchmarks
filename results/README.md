# Knotrel Benchmark Results

This directory contains recorded benchmark and performance evaluation reports. Each report measures the Knotrel revision recorded in it, not necessarily the latest release; see the [repository README](../README.md#evidence-by-release-and-purpose) for versions and hosts. Historical experiment runs, pilots, and campaign traces are preserved in the Git commit history, keeping the active working tree lean and focused while maintaining full reproducibility and provenance.

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

### 4. Hot-Path Audit, v0.3.0 Candidate (`hot-path-audit-20261114/`)
- **Detailed Report**: [hot-path-audit-20261114/README.md](hot-path-audit-20261114/README.md) (generated tables: [REPORT.md](hot-path-audit-20261114/REPORT.md))
- **Scope**: Knotrel `e1e1181` (baseline) versus the hot-path audit change set (candidate code diff sha256 `8b579f7d…cc9d7`), with a same-binary A/A arm, 12 counterbalanced rounds, Rust 1.100.0, Apple M3. Core initialization and dynamic workloads, the in-process `knotrel-server` router probe, allocation counts and a separate end-to-end HTTP section.
- **Key Results**:
  - Results identical across arms; allocations per request fall 16.7% (single query) to 75.0% (100,000-node import).
  - 13 confirmed timing improvements (router import about −21%, feeder −14% to −19%, batches −6% to −9%; core initialization −4% to −7%), 1 marginal regression on a code path the patch does not change, 28 inconclusive.

### 5. M6.5 Metrics Overhead, v0.4.0 Candidate (`metrics-overhead-20261115/`)
- **Detailed Report**: [metrics-overhead-20261115/README.md](metrics-overhead-20261115/README.md) (generated tables: [REPORT.md](metrics-overhead-20261115/REPORT.md))
- **Scope**: Opt-in Prometheus metrics on versus off on one release build of the in-process router probe (v0.4.0 candidate tree, identity `6ec5f564…ae65c3c`), byte-identical A/A copy, 24 counterbalanced rounds, budget approved before measurement (median ≤ 3%, 95% CI upper ≤ 6%).
- **Key Results**: 6/6 scenarios PASS; largest cost +1.28% [+0.60%, +1.59%] (batch of 1,024 queries).

### 6. Hot-Path Regression Re-check (`hot-path-recheck-20261115/`)
- **Detailed Report**: [hot-path-recheck-20261115/README.md](hot-path-recheck-20261115/README.md)
- **Scope**: Pre-specified re-measurement of the hot-path audit's one marginal regression with the campaign's exact binaries, 24 counterbalanced rounds.
- **Key Results**: `compact-bfs` dynamic `connected_total_ns` +0.83% [+0.10%, +1.78%] against an A/A bound of ±2.14%: inconclusive; the regression does not reproduce.

### 7. Latest Performance Evaluation Summary (`perf_evaluation_latest.json`)
- Continuous performance metrics and regression gate output.

## Historical Evidence in Git

Prior milestone results, exploratory pilots, and campaign traces are archived in the Git repository history. To inspect historical data from earlier versions:

```sh
git log --stat -- results/
```
