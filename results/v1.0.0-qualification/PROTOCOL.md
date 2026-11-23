# knotrel v1.0.0: qualification campaign (roadmap R1), protocol

**Status: DRAFT, NOT FROZEN.** Frozen only when `FREEZE.json` (revision 1)
is written; until then this directory holds `FREEZE.template.json`, which is
not a freeze record and which no collector or runner accepts. **Nothing has
been measured.** The candidate commit is chosen at the freeze.

This protocol implements knotrel `docs/releases/v1.0.0-qualification-plan.md`
(knotrel `origin/main` `d847283`), with the maintainer's decisions of
2026-11-23:

- the perimeter of plan §4.1: A, B4 (all 37 cells), C, R, Rmem, M_reg and Q
  (7 cells plus the Q5 v0.9.0 reference arm in the same session);
- **block D excluded**;
- A at a **fixed n = 24 pairs per cell, no interim look** (plan §5.3, option a);
- thresholds unchanged from the v0.9.0 matrix;
- budget: Part 1 ≤ 105 min and Q ≤ 30 min, two separate caps;
- one attempt, cap 2, the second only for non-conformance;
- the infrastructure and product failure rules of plan §5.5;
- reference v0.9.0 `223f04c10b0af663b54e269e0970ee10ac1dc6b2`.

Where this file and the plan differ, the plan rules. A failed cell is reported
as failed and is not reinterpreted.

## 1. Builds

| Role | knotrel | Probes (knotrel-benchmarks) |
|---|---|---|
| Candidate | **chosen at the freeze**: the commit on `main` after the R3 changes and the version bump, recorded in `FREEZE.json` `candidate.commit`; every script takes it as `CAND_SHA` | the freeze commit (probe lockfile: knotrel 1.0.0) |
| Reference | v0.9.0 = `223f04c10b0af663b54e269e0970ee10ac1dc6b2` (a newer 0.9.x replaces it only if published before the freeze, plan §2) | `53c50e96` (probe lockfile: knotrel 0.9.0) |

- The two probe trees have **the same source**. Their only difference is the
  two knotrel version lines of `tools/lifecycle-probes/Cargo.lock`. The
  prepare script checks this. The probes compile unchanged against knotrel
  1.0 (`#[non_exhaustive]` types included): verified before the freeze
  (§5, step 1).
- Each reference build comes from a **clean clone** at its commit; every
  probe build records itself as not dirty.
- Everything is built with Rust 1.100.0, `--release --locked --offline`, each
  binary in its own target directory, as in v0.9.0.
- No descriptive second reference (plan §2). No v0.8.0 build.
- **Release commit rule.** The rc and 1.0 commits must equal the measured
  candidate in `crates/`, `Cargo.toml`, `Cargo.lock` and
  `rust-toolchain.toml`, apart from the version fields (workspace version,
  `knotrel-core` dependency version, matching `Cargo.lock` lines), and the
  `knotrel-server` release build must have an identical `__TEXT,__text`.
  Otherwise the affected experiments are repeated.

## 2. Part 1: deciding, candidate against v0.9.0

**The method.** The v0.9.0 campaign (`results/v0.9.0-qualification`,
`FREEZE.json` revision 1; itself the v0.7.0 qualification-3 method), re-run
unchanged on a reduced perimeter: the same cells, pair counts, estimators,
seeds, workloads, order seeds and window multipliers; the same revision-3
interference policy, limits and restart rule; **every threshold**.
`MATRIX.json` here is v0.9.0's, changing only what the plan changes (tests
pin the difference): `references`, `rules.A` and `experiments.A` (fixed
n = 24), the B/C collector restricted to `--only B4,C`, `experiments.M_desc`
removed, T5 kept only for the core rule, the budget, the attempt series
`v100q` and its cap, the campaign directory, and a `v1_0_0` section (Q, core
rule, failure definitions, decision rule, publication). The `v0_9_0` section
is removed.

**What changes, and why:**

| Item | v0.9.0 | v1.0.0 |
|---|---|---|
| Reference of A, R, Rmem, M_reg (and Q5) | v0.7.0 (Q5: frozen v0.8.0 summary) | v0.9.0; Q5 against v0.9.0 in the same session |
| Candidate | `e827b2a` | chosen at the freeze (parameter) |
| A | 12 pairs, interim analysis, extension of the INCONCLUSIVE cells | **24 pairs for every cell**, two blocks of 12, **no interim analysis** (plan §5.3) |
| B/C | 140 cells | `--only B4,C`: 37 B4 cells (22 deciding, 13 descriptive, 2 not equivalent) and 60 C cells (15 configurations) |
| T5, B1–B3, B5 | measured | only if the core rule triggers (§3) |
| M_desc | measured, descriptive | not run |
| Part 2 (v0.8.0) | descriptive | none; block D excluded |
| Bindings | `run_v090q_*` | `run_v100q_collect.py`, `analyze_v100q.py` (`r`, `rmem`, `mreg`), `analyze_v100q_a.py`, `analyze_v100q_bc.py`, `report_v100q_bc.py`, `run_v100q_q.py`, `evaluate_v100q_q.py`: thin wrappers binding the frozen code to this matrix |
| Runner | `run_v090q_autonomous.py` | `run_v100q_autonomous.py`: the same behaviour with the reduced chain; it checks this freeze record (revision 1, campaign "v1.0.0 qualification", candidate and reference commits, core-rule outcome) |
| Campaign directory | `v0.9.0-qualification-<c7>-attemptN` | `v1.0.0-qualification-<c7>-attemptN` |
| Attempts | one, cap 2 | one, cap 2 (series `v100q`) |
| Budget | 105 / 20 / 30 min | Part 1 105 min, Q 30 min, separate caps |

**A: fixed n = 24 (plan §5.3, option a).**
- Block 1: `A/plan` (plan generator phase `main`, checkpoint
  `v1.0.0-Qualification-A-Block1`, session seeds 130720–130722), raw pairs in
  `A/raw-main`.
- Block 2: `A/plan-block2` (the generator's `extension` phase with **all
  nine cells**, checkpoint `v1.0.0-Qualification-A-Block2`, extension seeds
  130730–130732), raw pairs in `A/extension/raw-extension`, the frozen path
  that the conformance end check counts.
- Both plans are made by `prepare_campaign.sh` before the launch, and both
  are dry-run. The runner's v0.9.0 steps `A-analysis` and `A-extension-plan`
  are removed: no step of the chain reads A data.
- `analyze_v100q_a.py` runs once, after the chain. It reuses the frozen
  v0.4.0 functions of `analyze_bc_qualification.py` (input checks, balanced
  design per block, consistency over both blocks, `evaluate_cell` final
  decision on 24 pairs) without its interim decision. The 24 log ratios of a
  cell form one sample; the block is recorded per pair, not a stratum.
  Interval `[r(7), r(18)]`, coverage 1 − 2·P(Bin(24, ½) ≤ 6) = **97.73 %**.
  Classes: PASS, REGRESSION, INCONCLUSIVE_DISCLOSED, UNRESOLVED.
- The order-statistic intervals are not 95 % intervals: 97.73 % at n = 24,
  96.14 % at n = 12 (B4, R, M_reg).

**B4 and C.** `run_lifecycle_qualification.py --profile final
--lifecycle-engines compact-bfs --equivalent-references --only B4,C`, order
seed 50720 and the frozen window multipliers. The collector has no per-cell
filter, so all 37 B4 cells and all 60 C cells run, and every cell is
classified and published. The frozen analyzer refuses any `--only` run, so
`analyze_v100q_bc.py --expect-only B4,C` installs a completeness check for
exactly the B4 and C cells of the frozen matrix; every rule and every
per-cell check is the frozen analyzer's.

**Unchanged consequence (E6).** The two `hub` 10k lifecycle requirements (B4
`ops` and `events`) have no equivalent reference. They run unchanged inside
B4, get no verdict, and stay explicitly unqualified. The v0.9.0 acceptance
does not carry over; **E6 requires a disposition for 1.0**.

## 3. Core rule (plan §4.3)

Decided **at the freeze, from builds, never from measurements**.
`core_rule_v100q.py` compares `__TEXT,__text` (`otool -s __TEXT __text`) of
the release builds of `core-lifecycle` (B/C `core`), its `count-alloc` build
(B/C `core-count`) and the A core harness, built against the candidate and
against the reference.

- **Identical:** the perimeter is as above (`--only B4,C`); A core cells, R,
  Rmem and C still run.
- **Different:** B1–B3, B5 and T5 join the perimeter with their frozen cells
  and thresholds: the runner runs the full B/C collector and T5
  (`run_v070q3_t5.py`, arm B `targets/t5base-probes`), within the Part 1 cap.

`FREEZE.json` records the outcome and the comparison file's SHA-256. The
runner refuses to start without it; `prepare_campaign.sh` recomputes the
comparison on the campaign's clean builds and stops if it differs.

## 4. Block Q: feeder under load

- **Protocol:** knotrel `docs/integrations/feeder-under-load.md`, all seven
  cells, 3 observations each, criteria Q1–Q5 with unchanged thresholds.
- **Builds:** the candidate server of Part 1; feeder and load tool built at
  the candidate commit (`targets/feeder`); PostgreSQL 18.7, the pinned image
  of `scripts/start-test-postgres.sh`.
- **Q5 reference arm:** L1 G100k `C` = 16 and 64 on the v0.9.0 server
  (`targets/ref-server`), 3 observations each, in the same session, with the
  same feeder, tool and PostgreSQL.
- **Order: three rounds** (`run_v100q_q.py`). Each round runs one repetition
  of the candidate's seven cells and one of the two reference cells; the side
  that goes first alternates (candidate first in rounds 1 and 3). The tool
  selects cells with `LOAD_CELLS` and `LOAD_REPS=1`; `LOAD_WINDOW_SECS`,
  `LOAD_BACKLOG` and every R2 variable are removed from the environment.
- **Cap: 30 minutes.** A step that would start after the deadline does not
  start; a running step is stopped at the deadline. Block Q is then
  NONCONFORMING: completed observations are kept; criteria whose cells lack
  their three observations get no verdict, and none counts as PASS. Q can be
  rerun once, as a whole (`run_part3.sh CAMP 2`), only after this
  non-conformance or an infrastructure failure, never because of a result.
- **Failures (plan §5.5).** A failed tool invocation is recorded with its
  evidence (exit status, time, stderr tail, power, thermal state, free disk,
  Docker containers). It is an infrastructure failure only for closed-list
  evidence with no product indication; ambiguous evidence is not (fail
  closed). An infrastructure failure allows one rerun of that observation; a
  product failure counts as measured, and the criteria using it **FAIL**.
- **Criteria (`evaluate_v100q_q.py`).** Q1–Q4 are computed by a line-by-line
  port of the tool's `evaluate` on the three rounds; every step's own
  `summary.json` is recomputed with the port and must match, so the port is
  checked on the campaign's own data. Q5: for each of `C` = 16 and 64, the
  candidate's median query throughput ≥ 90 % and its median client p99
  ≤ 125 % of the v0.9.0 medians of this session. Q5 against the frozen
  v0.8.0 baseline (SHA-256 `bc6e8c09…`) is reported, not deciding.
- **Deciding:** Q1, Q2, Q4 and Q5. **Q3** is classified as measured; the
  v0.9.0 acceptance does not carry over; if not PASS it needs a disposition
  and a documented operational envelope (plan §8).
- Q has no chain gate, as in v0.9.0. It runs only after Part 1 ended
  CONFORMING (`run_part3.sh` checks it).

## 5. Sequence

1. **Before the freeze (verification, no measurement).** Tooling committed;
   `python3 -m pytest -q scripts/tests` passes (the existing suite and
   `scripts/tests/test_v100q.py`). Then
   `prepare_campaign.sh CAND TOOLING --pre-freeze` on the intended candidate:
   clean clones, every build, the release-binary smoke tests, both A plans and
   their dry runs, the core-rule comparison, the probe compatibility check
   (`probe_compat_v100q.py`, functional only: every probe of the perimeter
   once with reduced repetitions at its frozen graph size against the
   candidate, and the R, Rmem and M_reg probes against v0.9.0 too; an empty
   `outstanding_jobs` series on the candidate must not fail the probe), and
   the launch environment check (every collector's dry run; the
   runner must refuse because nothing is frozen).
2. **Freeze.** Write `FREEZE.json` (revision 1) from `FREEZE.template.json`:
   the candidate and reference commits, the core-rule outcome and comparison
   hash, the probe compatibility result, the delta record of plan §3.5, the
   test results, the review, and the SHA-256 of every file listed in the
   template. Commit it alone (the freeze commit).
3. Run `prepare_campaign.sh CAND FREEZE 1`. It clones and builds everything,
   runs the smoke tests, records the checksums, recomputes the core rule
   (must equal the freeze record's), reruns the probe compatibility check,
   runs the launch environment check (every collector's dry run and the
   runner's preflight) and writes `LAUNCH-COMMAND.txt`.
4. One session: Part 1, then block Q (`run_part3.sh`) if Part 1 ended
   CONFORMING. Nothing else heavy runs on the host: no builds, no other
   benchmark.
5. Analysis with the commands of §6, then the decision record
   (`DECISION.md`), the maintainer's dispositions and publication (§8).

## 6. Analysis commands

- **A:** `analyze_v100q_a.py --block1 A/raw-main --block2
  A/extension/raw-extension --output analysis/A-final-decision-analysis.json`.
- **B4 and C:** `analyze_v100q_bc.py BC --expect-only B4,C
  --expect-knotrel-rev <cand> --expect-probes-rev <freeze>
  --expect-multipliers-sha256 <window-multipliers-q3.json>
  --expect-lifecycle-engines compact-bfs --expect-equivalent-references
  --json analysis/BC-analysis.json --markdown analysis/BC-analysis.md`
  (`--expect-only full` if the core rule triggered).
- **T5 (core rule only):** `analyze_v100q_t5.py T5 --expect-base-rev
  223f04c… --expect-cand-rev <cand> --expect-base-probes-rev 53c50e96…
  --expect-probes-rev <freeze> --benchmarks <tooling clone> --json
  analysis/T5-analysis.json` (`analyze_v090q_t5.py`, whose probe-source check
  accepted only 0.x version lines, with the 0.9.0 to 1.0.0 lockfile lines
  allowed).
- **Report:** `report_v100q_bc.py analysis/BC-analysis.json --core-rule
  identical` (`different` adds `T5-analysis.json`).
- **R and Rmem:** `analyze_v100q.py r|rmem DIR --ref-rev 223f04c…
  --cand-rev <cand>`.
- **M_reg:** `analyze_v100q.py mreg Mreg`.
- **Q:** `part3/evaluation.json` (written by `run_part3.sh`).

## 7. Decision rule (plan §7–8, unchanged)

- The campaign is **valid** when one Part 1 attempt is CONFORMING and Q
  completes under its protocol and cap.
- v1.0.0 is **qualified** only if the campaign is valid and every deciding
  cell and criterion is PASS. Any other result is reported as it is, for a
  maintainer decision.
- Non-PASS results (REGRESSION, FAIL, INCONCLUSIVE, INCONCLUSIVE_DISCLOSED,
  UNRESOLVED, NOT_EQUIVALENT, INVALID, not run) need a recorded maintainer
  disposition before `v1.0.0-rc.1`. A disposition is recorded next to the
  verdict, never in place of it.
- Disclosure categories (C4 EXCEEDS_BUDGET, the descriptive B4 frozen
  counterparts including `import-high`) and TIMER_LIMITED cells are listed,
  never converted, and do not block.
- No v0.9.0 or earlier exception carries over. No rule changes after
  collection, and no rerun is chosen by its result.

## 8. Publication (plan §11)

`export_v100q_site.py` turns the analyzer outputs into the `1.0.0` entry of
`docs/data/releases.json`, only after `DECISION.md` exists. It writes to a
separate file and never edits `docs/`; copying the result is a separate,
reviewed change. `delta_ci95` holds the order-statistic interval in percent,
and `ci_method` names it with its coverage (it is not a 95 % interval). Rmem
and Q rows have no interval, with the plan's reasons. B4 and C rows state that
their reference is an arm of the candidate build. As in the plan, only E6 and
Q5 against v0.8.0 go to the campaign report only; every other classified cell
and criterion is a site row, and no deciding verdict is dropped. The rows use
site schema 2 (`docs/SITE.md`): the verdict exactly as measured (PASS,
PASS (IMPROVED), FAIL, REGRESSION, INCONCLUSIVE, INCONCLUSIVE_DISCLOSED,
UNRESOLVED, TIMER_LIMITED, EXCEEDS_BUDGET, INVALID, NOT_EQUIVALENT, NOT_RUN,
or none), a category (decisive, descriptive, disclosure) and an execution
status (completed, not_run, nonconforming, failed), never converted or merged.
C1, C2 and Q2 are threshold-kind rows with their verdict and no ratio or
interval, as is an Rmem metric whose reference is zero; an M_reg cell that is
INVALID without metrics is a `failed` row with its reason. Not-run cells carry
their reason and no values. A truly unknown measured class still stops the
export instead of being mapped.
