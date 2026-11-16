# Experiment A on candidate dcd8ccc (amendment 4)

Main 2026-11-16T11:49:20Z-12:02:46Z (108 pairs), extension 12:02:46Z-12:16:06Z
(48 pairs, 4 cells), both exit 0; analyses exit 0 (`--rules v0.4.0`). Run as part
of `run4-chain-dcd8ccc.sh` under `caffeinate`; the agent ran no other command
during the chain. Pre-launch: AC power, no build, every frozen hash verified.

| Cell | Outcome | Primary (pairs) | Note |
|---|---|---|---|
| core sparse traversal compact-bfs | PASS | −7.23% [−33.47, +2.83] (12) | |
| core sparse traversal compact-workspace | PASS | −1.94% [−9.87, +6.00] (12) | |
| core sustained churn compact-bfs | PASS | −1.02% [−3.67, +0.64] (12) | |
| core sustained churn compact-workspace | PASS | +0.19% [−1.38, +2.28] (12) | |
| HTTP lifecycle startup | INCONCLUSIVE_DISCLOSED | +5.14% [−17.35, +22.13] (24) | |
| HTTP batch 1 | **UNRESOLVED** | +0.04% [−5.57, +5.32] PASS (24) | request p99 INCONCLUSIVE +6.04% [−27.84, +50.04] |
| HTTP batch 8 | PASS | −0.42% [−5.05, +8.17] (24) | |
| HTTP batch 64 | **UNRESOLVED** | −2.11% [−4.01, +1.96] PASS (24) | sampled max RSS INCONCLUSIVE +0.11% [−3.50, +25.14] (t = 20%) |
| HTTP batch 256 | PASS | −1.72% [−3.13, +6.84] (12) | |

Summary for `dcd8ccc`: 6 PASS, 1 INCONCLUSIVE_DISCLOSED, 2 UNRESOLVED, no
REGRESSION. The records for `6494253` (4/2/3) and `a1d9577` (5/1/3) are
unchanged and separate; no result is selected across candidates.
