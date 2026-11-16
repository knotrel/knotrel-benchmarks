# D5 — compact-bfs memory peaks on candidate dcd8ccc (frozen in amendment 4)

Diagnostic only, no verdict. Runner `run_d5.py`: D4a's `compact-bfs` churn
runs (fresh, same, toggle; sparse, 100,000 nodes, 30 cycles, 5%, seed 5000001)
and D4d's `compact-bfs` 100,000-node imports (core and HTTP create at 20/10 and
60/30 flags; HTTP replace at 20/10), 8 runs, one process at a time, cap 5
minutes, AC power, binary hashes checked before starting. Metric definitions as
in `D4-PLAN.md`. Output: `D5/`.
