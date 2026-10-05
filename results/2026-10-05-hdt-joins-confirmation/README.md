# Adaptive regression confirmation

Four new paired trials for each of the six initial scenario cells whose runtime
regression exceeded 15%: 48 additional processes. Selection is adaptive, not an
independent random sample of all workloads. Original results remain intact;
these trials are reported separately, never pooled with them. Same executables,
traces, cache regimes and measurement protocol as the
[main report](../2026-10-05-hdt-joins/README.md).

| Workload | Nodes | Query % | Regime | Initial runtime delta | Confirmation runtime delta |
|---|---:|---:|---|---:|---:|
| redundant-bridge-churn-v1 | 512 | 90 | fresh | +289.20% | -0.74% |
| sustained-churn-path-v1 | 1024 | 50 | fresh | +161.15% | -1.32% |
| sustained-churn-path-v1 | 1024 | 90 | warmed | +19.09% | +0.82% |
| sustained-churn-path-v1 | 10000 | 50 | warmed | +49.32% | -14.93% |
| sustained-churn-path-v1 | 100000 | 50 | fresh | +50.42% | -18.85% |
| sustained-churn-path-v1 | 100000 | 50 | warmed | +25.34% | +11.62% |

The two >100% initial regressions did not reproduce. This does not erase the
original observations. The 100k path / 50% query / warmed cell still regresses
by 11.62%; the fresh version changes direction. Workload sensitivity and process
variation remain relevant. No blanket speedup or significance claim is made.
`comparison.json` includes per-process ranges and operation tails. `collect.py`
preserves the >15% selection rule and four-trial construction; `compare_confirmation.py`
regenerates the comparison. Whole-process RSS is not engine-only allocation.
