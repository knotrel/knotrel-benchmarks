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

### 4. Current Release Qualification, v0.9.0 (`v0.9.0-qualification/`)
- **Decision Record**: [v0.9.0-qualification/DECISION.md](v0.9.0-qualification/DECISION.md) (protocol: [PROTOCOL.md](v0.9.0-qualification/PROTOCOL.md); frozen matrix: [MATRIX.json](v0.9.0-qualification/MATRIX.json))
- **Scope**: Knotrel `e827b2a` against the published v0.7.0 (deciding reference) and v0.8.0 (descriptive reference), re-running the v0.7.0 qualification-3 method unchanged except where the protocol says.
- **Key Results**: campaign execution VALID (attempt 2 CONFORMING); release ACCEPTED WITH EXCEPTIONS, for v0.9.0 only. Five deciding results are not PASS; the decision record lists them.

### 5. Next Release Qualification, v1.0.0 (`v1.0.0-qualification/`)
- **Protocol (draft, not frozen)**: [v1.0.0-qualification/PROTOCOL.md](v1.0.0-qualification/PROTOCOL.md) (matrix: [MATRIX.json](v1.0.0-qualification/MATRIX.json); freeze template: [FREEZE.template.json](v1.0.0-qualification/FREEZE.template.json))
- **Scope**: the candidate (chosen at the freeze) against the published v0.9.0 on the reduced perimeter approved by the maintainer (A at a fixed n = 24, B4, C, R, Rmem, M_reg, Q with a same-session Q5 v0.9.0 arm; block D excluded).
- **Key Results**: none. Tooling only; nothing is frozen and nothing has been measured.

### 6. Latest Performance Evaluation Summary (`perf_evaluation_latest.json`)
- Continuous performance metrics and regression gate output.

## Earlier Release Evidence at Tags

Only the current release's qualification stays in the working tree. When a release is tagged, its
evidence is committed with it, and the evidence of earlier releases leaves `main`; each campaign
stays, unchanged, in the tree of the tag that closed it:

| Campaign | Tag |
| --- | --- |
| [Hot-path audit, v0.3.0 candidate](https://github.com/knotrel/knotrel-benchmarks/tree/v0.4.0/results/hot-path-audit-20261114) | `v0.4.0` |
| [Hot-path regression re-check](https://github.com/knotrel/knotrel-benchmarks/tree/v0.4.0/results/hot-path-recheck-20261115) | `v0.4.0` |
| [Metrics overhead (M6.5), v0.4.0 candidate](https://github.com/knotrel/knotrel-benchmarks/tree/v0.4.0/results/metrics-overhead-20261115) and release-candidate reruns ([r1](https://github.com/knotrel/knotrel-benchmarks/tree/v0.4.0/results/metrics-overhead-rc-62c2cea), [r2](https://github.com/knotrel/knotrel-benchmarks/tree/v0.4.0/results/metrics-overhead-rc-62c2cea-r2)) | `v0.4.0` |
| [v0.5.0 lifecycle qualification](https://github.com/knotrel/knotrel-benchmarks/tree/v0.5.0/results/lifecycle-qualification-v0.5.0) | `v0.5.0` |
| [v0.6.0 qualification](https://github.com/knotrel/knotrel-benchmarks/tree/v0.6.0/results/v0.6.0-qualification) | `v0.6.0` |
| [v0.7.0 qualification](https://github.com/knotrel/knotrel-benchmarks/tree/v0.7.0/results/v0.7.0-qualification), [re-qualification](https://github.com/knotrel/knotrel-benchmarks/tree/v0.7.0/results/v0.7.0-requalification) and [qualification 3](https://github.com/knotrel/knotrel-benchmarks/tree/v0.7.0/results/v0.7.0-qualification-3) | `v0.7.0` |

Locally, `git show <tag>:results/<campaign>/<file>` or `git archive <tag> results/<campaign>` retrieves
them. Frozen tooling that still binds these paths is tested against the tag copies
(`scripts/tests/historical.py`). Earlier experiment runs and pilots remain in the commit history:

```sh
git log --stat -- results/
```
