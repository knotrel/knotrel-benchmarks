# v1.2.0 qualification attempt 3: budget (knotrel#182)

Recorded before any frozen collection, as the plan requires (knotrel
`docs/releases/v1.2.0-qualification-plan.md` §14.11, with amendment 1 of §14).

**Cap: 9.0 host hours for the single session** (`rules.cap_hours` in `v120q-matrix.json`).
There is no second session. A cell left incomplete at the cap is `INCOMPLETE`; a cell never
started is `NOT_RUN`.

## Preparatory trial of the new blocks

- **Date:** 2026-11-28.
- **Campaign:** `v1.2.0-qualification-prefreeze-a3-24c2602-0d59c64`.
- **Command:** `run_cf5.py --preparatory --pairs 2 --warmup 0 --no-smoke --blocks K3,M1,M2,K4`.
- **Host:** no swap activity.

Its results decide nothing. Projections to 26 pairs scale the trial's observation wall time
by 13.

| Block | Trial (2 pairs) | Projected (26 pairs) | §14.11 estimate / worst case |
|---|---|---|---|
| K3 | 0.4 min | 5 min | 20 / 25 min |
| M1 | 3.4 min | 44 min | 41 / 45 min |
| M2 | 2.3 min | 30 min | 43 / 50 min |
| K4 | 0.2 min (slowest observation 0.7 s, timeout 300 s) | 3 min | 10 / 20 min |

The carried blocks keep their measured times from attempts 1 and 2. The worst case of §14.11
is 405 min; with a 30 % margin that is 527 min. **The cap is therefore 9.0 h.**

## Superseded freeze 5a02d25 (no observation)

- **What happened:** the first freeze (`FREEZE-superseded-5a02d25.json`, knotrel-benchmarks#75) did not start. `prepare_v120q.sh` stopped before any build, because `derive_arm_lock.py`, confined to its default roots after the SonarCloud fix, refused the campaign's lock path.
- **Effect:** no observation was collected and no session ran. The preparation logs are kept in `evidence/v1.2.0-qualification-attempt3-prepare-refused-5a02d25`.
- **Fix:** the preparation now exports the campaign as an allowed root. A new freeze follows, with the candidate, matrix and cap unchanged.
