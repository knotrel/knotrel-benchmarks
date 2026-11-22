# knotrel v0.9.0: final performance campaign (roadmap 0.9.6), protocol

**Status: frozen when `FREEZE.json` (revision 1) is written.** This protocol
implements the plan approved by the maintainer on 2026-11-22 ("Approved, run
it"): knotrel `docs/releases/v0.9.0-qualification-plan.md` (knotrel
`23b5f27`). Where this file and the plan differ, the plan rules. A failed
cell is reported as failed and is not reinterpreted.

## 1. Builds

| Role | knotrel | Probes (knotrel-benchmarks) |
|---|---|---|
| Candidate | `e827b2a7bb1930b70e75ed7ccff2ac0201db9e40` (main after the 0.9.0 version bump) | the freeze commit (probe lockfile: knotrel 0.9.0) |
| Deciding reference | v0.7.0 = `9f933a783b043f9f44fd5de014c3c8a93c7922c3` | `7116c32e` (probe lockfile: knotrel 0.7.0) |
| Descriptive reference (Part 2) | v0.8.0 = `e3fc7361caf2f29dcf6870e8018b96414ebd927b` | `e843aae2` (probe lockfile: knotrel 0.8.0) |

- The three probe trees have **the same source**. Their only difference is
  the two knotrel version lines of `tools/lifecycle-probes/Cargo.lock`. The
  prepare script checks this, and so does the T5 analysis.
- Each reference's probes are built from a **clean clone** at its commit. In
  q3, the reference probe lockfile was derived inside a dirty clone. Here no
  derivation is needed, so every probe build records itself as not dirty.
- Everything is built with Rust 1.100.0, `--release --locked --offline`,
  each binary in its own target directory, as in q3.
- **Release commit rule.** The release commit's `crates/`, `Cargo.toml` and
  `Cargo.lock` must equal the candidate's. Otherwise the campaign is
  repeated.

## 2. Part 1: deciding, candidate against v0.7.0

**The method.** The v0.7.0 qualification-3 campaign
(`results/v0.7.0-qualification-3`, `FREEZE.json` revision 3), re-run
unchanged:
- experiments A, B/C (140 cells, capability-equivalent references), T5, R,
  Rmem, M_desc and M_reg;
- the same cells, pair counts, estimators, seeds, workloads, order seeds and
  window multipliers;
- the same revision-3 interference policy, limits and restart rule;
- **every threshold**: A primary 10 %, query tail 25 %, RSS 20 %, the B and C
  tolerances, B5 3×, C1–C4, T5 25 %, R, Rmem and M_reg tolerances, the
  metrics budget 6 %;
- `MATRIX.json` here is q3's, with only `references`, the T5 arm
  descriptions, the attempt series and cap, the campaign directory and the
  budget changed. A `v0_9_0` section is added for Parts 2 and 3.

**What changes, and why:**

| Item | q3 | v0.9.0 |
|---|---|---|
| Reference of A, R, Rmem, M_reg | v0.6.0 | v0.7.0 |
| Candidate | `fa5f3a9` | `e827b2a` |
| T5 arm B | probes against `e75ff6a` (isolated T1) | probes against v0.7.0. The question becomes: "does the candidate lengthen compaction pauses compared with v0.7.0?" Same workload, same equality checks. |
| B/C | candidate only | unchanged: B/C compares arms within the candidate build and runs no reference binary |
| Bindings | `run_v070q3_*`, q3 matrix | `run_v090q_collect.py`, `analyze_v090q.py`, `report_v090q_bc.py` and `analyze_v090q_t5.py`: thin wrappers that bind the frozen q3 code to this matrix. The T5 wrapper accepts a separate, clean probe revision for arm B and checks that the probe source is identical. |
| Runner | `run_v070q3_autonomous.py` | `run_v090q_autonomous.py`: a subclass with the same behaviour. It checks this freeze record (revision 1, campaign "v0.9.0 qualification", candidate commit) and uses the A extension checkpoint `v0.9.0-Qualification-A-Extension`. |
| Campaign directory | `v0.7.0-qualification-3-<c7>-q3-attemptN` | `v0.9.0-qualification-<c7>-attemptN` |
| Attempts | cap 3 (4 after revision 3) | **one**, cap 2. A second attempt is allowed only if the first does not conform (gate, budget or recovery exhausted), never because of a result. A second non-conforming attempt ends the campaign for a maintainer decision. |
| Budget | 105 min | 105 min (q3-3 took 87.2) |

**Unchanged consequence.** The two `hub` 10k lifecycle requirements (B4 ops
and B4 events) have no equivalent reference. They stay unqualified by
construction (q3 §4.1, decision 8): they get no verdict, and their
disposition is the maintainer's.

## 3. Part 2: descriptive, candidate against v0.8.0

Part 2 covers what changed after v0.8.0: the reserved feeder admission lanes
(0.9.3). Its budget is 20 minutes, and it runs only after Part 1 ends
CONFORMING. It has its own gate, logs and records in `CAMP/part2`, under the
same interference policy.

1. **B4 cells.**
   - Run: `run_lifecycle_qualification.py --profile final --only B4
     --equivalent-references`, with the same order seed and window
     multipliers, using `http-lifecycle` built against v0.8.0. The
     `--core-count` binary is the v0.8.0 count-alloc build; no core cell runs
     under `--only B4`, but the interference collector requires distinct
     binaries for core and core-count cells.
   - The collector has no per-cell filter, so all 37 B4 cells run (about
     4.4 minutes in q3-3). With M_reg (about 13.8 minutes) that leaves a
     small margin in the 20-minute budget. If Part 2 ends without
     conforming, it is reported as such and Part 3 still runs.
   - The six `B4-http-events-*` cells are compared with the same cells of
     Part 1 by `compare_v090q_part2.py`. It uses the frozen per-cell checks
     and estimator, plus the ratio of the two versions' lifecycle-arm
     medians.
   - That ratio compares two unpaired runs of the same session, so it is
     descriptive only.
   - The other B4 cells are recorded but are not Part 2 results.
2. **M_reg.**
   - Run: the frozen M_reg cells, with reference = knotrel-server v0.8.0 and
     candidate = the Part 1 candidate server.
   - Analyzed by `analyze_v090q.py mreg`. The classification it computes is
     reported as a description, without a verdict.

Part 2 states the change from v0.8.0. It is never a pass.

## 4. Part 3: feeder under load on the candidate

**Protocol and timing.**
- The approved protocol, knotrel `docs/integrations/feeder-under-load.md`:
  all seven cells, 3 observations, criteria Q1–Q5 unchanged.
- The load tool runs with no `LOAD_*` override.
- `run_part3.sh` runs it after Part 2 has ended. It requires Part 1 to be
  CONFORMING, not Part 2: Part 2 is descriptive, and its status is reported
  as it is.

**Builds and PostgreSQL.**
- Server: the candidate server of Part 1.
- Feeder and load tool: built at the candidate commit (`targets/feeder`).
- PostgreSQL 18.7: the pinned image of `scripts/start-test-postgres.sh`.

**Criteria.**
- Q1–Q4 come from the tool's own evaluation.
- Q5 is computed by `evaluate_v090q_part3.py` against the protocol's v0.8.0
  baseline summary (SHA-256 `bc6e8c09…`), as for change A. It uses L1 G100k
  with 16 and 64 clients: median throughput ≥ 90 %, median client p99
  ≤ 125 %.
- **Deciding:** Q1, Q2, Q4 and Q5.
- **Q3** is the declared limitation of v0.9.0 (maintainer decision
  2026-11-21). It is reported again as measured. Its thresholds do not
  change, and CPU contention is not presented as a demonstrated cause.

**Budget and repetition.** 30 minutes. One repeated observation per cell is
allowed only for a recorded host problem, as the protocol states.

## 5. Sequence

1. Tooling committed. Tests (`scripts/tests/test_v090q.py` and the existing
   suite) pass. Then `FREEZE.json`.
2. Run `prepare_campaign.sh CAND FREEZE 1`. It:
   - clones and builds everything;
   - runs the smoke tests and records the checksums;
   - runs the launch environment check, with dry runs of every collector of
     Parts 1 and 2 and the runner's preflight;
   - writes `LAUNCH-COMMAND.txt`.
3. Part 1, then Part 2, then Part 3, in one session. Nothing else heavy runs
   on the host: no builds, no other benchmark.
4. Analysis with the commands of §6, then the decision record (`DECISION.md`)
   in this directory. The knotrel release notes and
   `docs/performance-by-version.md` report the outcome, with its limits.

## 6. Analysis commands

- **A:** `analyze_bc_qualification.py`, rules v0.4.0 (the runner writes
  `A/final-decision-analysis.json`).
- **B/C:** `analyze_lifecycle_qualification.py BC
  --expect-knotrel-rev e827b2a… --expect-probes-rev <freeze>
  --expect-multipliers-sha256 <window-multipliers-q3.json>
  --expect-lifecycle-engines compact-bfs --expect-equivalent-references`.
- **T5:** `analyze_v090q_t5.py T5 --expect-base-rev 9f933a7…
  --expect-cand-rev e827b2a… --expect-base-probes-rev 7116c32e…
  --expect-probes-rev <freeze> --benchmarks <tooling clone>`.
- **Report:** `report_v090q_bc.py BC-analysis.json T5-analysis.json`.
- **R and Rmem:** `analyze_v090q.py r|rmem DIR --ref-rev 9f933a7…
  --cand-rev e827b2a…`.
- **M_desc and M_reg:** `analyze_v090q.py mdesc|mreg DIR`.
- **Part 2:** `compare_v090q_part2.py BC part2/BC …` and
  `analyze_v090q.py mreg part2/Mreg`.
- **Part 3:** `part3/evaluation.json`.

## 7. Decision rule (the plan's, unchanged)

- **Part 1** classifies every cell. v0.9.0 is **qualified** only if every
  deciding cell is PASS. Disclosure categories are reported as such.
- Any other result is reported as it is, for a maintainer decision.
- No exception from v0.7.0 or earlier carries over. The v0.7.0 exceptions are
  measured again and classified anew.
- **Part 2** is descriptive.
- **Part 3:** Q1, Q2, Q4 and Q5 must pass. Q3 stays FAIL as declared.
- No performance claim goes beyond what the classification supports. No rule
  changes after collection, and no rerun is chosen by its result.
