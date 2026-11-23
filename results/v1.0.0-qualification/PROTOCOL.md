# knotrel v1.0.0: qualification campaign (roadmap R1), protocol

**Status: DRAFT, NOT FROZEN.** Frozen only when `FREEZE.json` (revision 1)
is written; until then this directory holds `FREEZE.template.json`, which is
not a freeze record and which no collector or runner accepts. **Nothing has
been measured.** The candidate commit is chosen at the freeze.

This protocol implements knotrel `docs/releases/v1.0.0-qualification-plan.md`
(knotrel `origin/main` at the freeze, which records candidate `0c49b2a`,
1.0.0-rc.1; the plan commit is recorded in `FREEZE.json` `plan`), with the
maintainer's decisions of 2026-11-23:

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
| Candidate | **chosen at the freeze**: the commit on `main` after the R3 changes and the version bump, recorded in `FREEZE.json` `candidate.commit`; every script takes it as `CAND_SHA` | the freeze commit (probe lockfile: knotrel 1.0.0-rc.1, the candidate's `Cargo.toml` version) |
| Reference | v0.9.0 = `223f04c10b0af663b54e269e0970ee10ac1dc6b2` (a newer 0.9.x replaces it only if published before the freeze, plan §2) | `53c50e96` (probe lockfile: knotrel 0.9.0) |

- The two probe trees have **the same source**. Their only difference is the
  two knotrel version lines of `tools/lifecycle-probes/Cargo.lock`. The
  prepare script checks this, and, before it creates the campaign directory,
  that both lines (`knotrel-core`, `knotrel-server`) equal the candidate's
  `Cargo.toml` version and `FREEZE.json` `candidate.version`; a test pins the
  lockfile against the freeze record. The probes compile unchanged against knotrel
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
  Classes: PASS, REGRESSION, INCONCLUSIVE_DISCLOSED, UNRESOLVED. As in
  `MATRIX rules.A`: INCONCLUSIVE_DISCLOSED only for an INCONCLUSIVE primary
  with median ≤ t and every supporting metric PASS; **an INCONCLUSIVE
  primary with median > t is REGRESSION**; any other non-PASS gated metric
  is UNRESOLVED.
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

`FREEZE.json` records the outcome and **provenance**: `core_rule.comparison`
names the pre-freeze `logs/core-rule.json` (`file`, relative to
EVIDENCE_ROOT) and its `sha256`. Prepare and the runner verify that file's
SHA-256 and outcome; if it is missing they refuse, unless
`KNOTREL_PREFREEZE_CORE_RULE` names it (inside EVIDENCE_ROOT).

At each attempt, `prepare_campaign.sh` recomputes the rule on the attempt's
clean builds and requires **agreement**, not equality: the same `outcome` and
the same per-pair `identical` booleans as the pre-freeze file. The digests
themselves are not compared across directories. The builds embed the campaign
directory's absolute path in panic locations, so `__cstring`, and with it the
`__text` digests, change with the path's length; the comparison within one
directory (candidate against reference) is what decides. Prepare records the
attempt's own `core-rule.json` and its SHA-256 in
`logs/core-rule-agreement.json`, and the runner's preflight checks the
agreement again. A different outcome or different per-pair booleans stop
prepare before the launch, for a maintainer decision (never a result).

**Known limit (path length within a directory).** The candidate probes link
`src/cand/knotrel` and the reference probes `src/ref/knotrel`, so the
embedded paths differ in length between the two arms of the probe pairs (the
A harness uses the equal-length `B` and `C`). Path length alone can therefore
make a probe pair "different". The error is in the safe direction: it adds
B1–B3, B5 and T5 to the perimeter, within the Part 1 cap; it can never hide a
change. For this campaign the pre-freeze analysis found real code-generation
differences regardless, in the release `core-lifecycle`:
`LifecycleGraph::connected` (384 → 444 bytes) and `GenericForest::balance`
(684 → 624 bytes) (knotrel `docs/releases/v1.0.0-qualification-plan.md` §4.3,
knotrel#140). `core_rule_v100q.py` and the build layout are unchanged.

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
  their three observations get no verdict, and none counts as PASS; a
  criterion with a failed candidate observation stays **FAIL**.
- **Second attempt of Q** (`run_part3.sh CAMP 2`, once, as a whole), only if
  the first did not end COMPLETE and its cause is the cap or an
  infrastructure failure whose one rerun was used up (both NONCONFORMING), or
  a runner or tooling error (FAILED) with no product failure. A COMPLETE Q is
  final, whatever `failures.jsonl` holds; no rerun is chosen by a result.
  Attempt 2 writes `superseded_by.json` into `part3`; the evaluator accepts
  only the final attempt, and carries the candidate's product failures of the
  superseded attempt (they are never rerun): the failures in its
  `failures.jsonl` and its completed observations that lack a value a
  criterion needs (a feeder not ready within 300 s writes `secs_to_ready`
  null and exits 0, so it never reaches `failures.jsonl`). The gate's reason
  and the marker state this. A FAILED first attempt with such an observation
  is a product failure and allows no second attempt. The publication reads only the
  final attempt's `evaluation.json`.
- **PostgreSQL.** `run_part3.sh` sets its cleanup trap first, checks the
  start script's exit status and its `postgres://` URL, and runs `pg_isready`
  and `SELECT 1` in the container before step 1. A start failure is an
  infrastructure failure, recorded in `logs/<Q directory>-postgres-start-failed-N.txt`;
  it allows one more start of the same Q attempt.
- **Failures (plan §5.5).** A failed tool invocation is recorded with its
  evidence (exit status, time, stderr tail, power, thermal state, free disk,
  Docker containers). It is an infrastructure failure only for closed-list
  evidence with no product indication; ambiguous evidence is not (fail
  closed); an unavailable `pmset` reading is no evidence, and power evidence
  is a positive "Battery Power" reading. An infrastructure failure allows one
  rerun of that observation (per round, side and cell); if the rerun fails
  too, the observation is lost and Q is NONCONFORMING. A product failure
  counts as measured, and the criteria using it **FAIL**.
- **Criteria (`evaluate_v100q_q.py`).** Q1–Q4 are computed by a line-by-line
  port of the tool's `evaluate` on the three rounds; every step's own
  `summary.json` is recomputed with the port and must match, so the port is
  checked on the campaign's own data. Q5: for each of `C` = 16 and 64, the
  candidate's median query throughput ≥ 90 % and its median client p99
  ≤ 125 % of the v0.9.0 medians of this session. A failed v0.9.0 reference
  observation gives Q5 **no verdict, not FAIL** (it is not a candidate
  result), with the reason; so does a v0.9.0 median of 0 (no ratio). Neither
  is ever PASS. Q5 against the frozen v0.8.0 baseline (SHA-256 `bc6e8c09…`)
  is reported, not deciding.
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
3. Run `prepare_campaign.sh CAND FREEZE 1`. Before it creates the campaign
   directory it checks the freeze record with the freeze commit's own
   `freeze_check_v100q.py` (identity, candidate, reference, core-rule outcome
   and hash, `file_sha256` keys equal to `file_sha256_paths`, which covers the
   list held in that script, every file's hash, the freeze commit as the only
   child of `tooling.commit` adding only `FREEZE.json`), the SHA-256 of the
   helpers it runs from its own directory, the attempt budget
   (`attempt_budget.sh`) and the probe lockfile version. Then it clones and builds everything,
   runs the smoke tests, records the checksums, recomputes the core rule
   (must equal the freeze record's), reruns the probe compatibility check,
   runs the launch environment check (every collector's dry run, the
   runner's preflight and the Q cells against the load tool's cell keys) and
   writes `LAUNCH-COMMAND.txt`. **If prepare fails after creating the
   directory** (a build, smoke test, core rule or probe check), it writes
   `logs/PREPARE-FAILED.txt`; that directory was never launched (no
   `CONFORMANCE.txt`, no `runner.log`) and the attempt budget refuses to
   continue past it. Recovery is the maintainer's recorded decision: rename it
   to `…-attemptN.prepare-failed-<utc>` (kept as evidence, outside the attempt
   pattern) and rerun prepare with the same N.
   **Attempt 2** is prepared only if attempt 1 is not CONFORMING
   (`series_budget.sh`) and, if it ended FAILED, every cause in its
   `logs/failures.jsonl` is infrastructure or conformance
   (`attempt_budget.sh`; plan §5.5).
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
- **Part 1 outcome after a failure:** `logs/part1-outcome.json` and
  `logs/failures.jsonl` (written by the runner;
  `part1_failures_v100q.py summary CAMP` prints them again).
- **Q:** `part3/evaluation.json` (written by `run_part3.sh`), or
  `part3-attempt2/evaluation.json` if Q was rerun (only the final attempt).

## 7. Decision rule (plan §5.5, §7–8)

- The campaign is **valid** when one Part 1 attempt is CONFORMING and Q
  completes under its protocol and cap.
- v1.0.0 is **qualified** only if the campaign is valid and every deciding
  cell and criterion is PASS. Any other result is reported as it is, for a
  maintainer decision. A disposition is recorded next to the verdict, never
  in place of it.
- **REGRESSION or FAIL** of a deciding cell or criterion **blocks**
  `v1.0.0-rc.1`: it is fixed and re-measured (plan §8 rule 5); a disposition
  does not lift it.
- **Inconclusive** results (INCONCLUSIVE, INCONCLUSIVE_DISCLOSED,
  UNRESOLVED) need an **explicit, recorded maintainer disposition**: accepted
  for v1.0 with the classification kept and disclosed, assigned to v1.2.0 H2
  with a criterion, or fixed and re-measured. NOT_EQUIVALENT needs a
  disposition too (plan §7).
- **INVALID, NONCONFORMING and not run** follow §5.5 of the plan and the
  attempt rules (§5 step 3, §4): a deciding cell without a valid verdict
  cannot be disposed as PASS; NONCONFORMING twice (Part 1 or Q) means no rc
  until the maintainer decides.
- **Part 1 product failure.** A collector child that fails on a product
  failure ends the attempt FAILED: the failed cell is **FAIL**; the other
  cells of that experiment and every later step are **not run**, each with
  the reason (`logs/part1-outcome.json`). No second attempt follows. An
  infrastructure failure of a child (closed-list evidence, no product
  indication; ambiguous counts as product) allows one rerun, which in Part 1
  is attempt 2; a conformance failure allows attempt 2 under the attempts
  rule.
- **Q3**, if not PASS, needs a disposition **and** a documented operational
  envelope (plan §8 rule 2); the absence of either blocks the rc.
- **E6** (the two not-equivalent hub 10k B4 cells) stays unqualified and
  needs its own, **separate** disposition for 1.0; it never becomes PASS.
- **Disclosures** (C4 EXCEEDS_BUDGET, the descriptive B4 frozen
  counterparts including `import-high`) and TIMER_LIMITED cells are listed
  and published, **never converted**, and do not block.
- No v0.9.0 or earlier acceptance or exception is inherited. No rule changes
  after collection, and no rerun is chosen by its result.

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
export instead of being mapped. **Final Q attempt only:** the exporter derives
the final Q attempt from the campaign directory's own records (`part3`, or
`part3-attempt2` when `part3/superseded_by.json` names it and it carries no
marker itself) and refuses a `--q` that is not that attempt's
`evaluation.json`, an ambiguous layout (an attempt 2 without the marker, a
marker naming a missing or different directory, an unknown `part3*`
directory), a campaign directory of another candidate, and an evaluation whose
`final_attempt` or `superseded_attempts` disagree. Every Q row records
`q_attempt`.
