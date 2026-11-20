# Proposal: targeted check of compaction latency tails with T1 (decision 3)

**Status: APPROVED on 2026-11-20 (PROTOCOL §1, decision 7), with the 25%
tolerance as a new criterion for pause tails.** The binding specification is
PROTOCOL §5.1; where this proposal differs (for example the run time, about
9 s), §5.1 rules. This file is kept as the proposal the maintainer decided
on.

## Why a check is needed

PROTOCOL §5.1: q3 does not measure or constrain the tails.
- **What D2c showed.** In D2c's T1 timing runs, engine-compaction tails were
  higher: ring p99 31.1 against 17.3 ms, ring maximum 37.9 against 22.0, hub
  maximum 72.3 against 27.3. Medians were lower. Each figure comes from **one
  run per policy** on an ungated laptop.
- **D2c's count build is not evidence.** It also recorded event durations,
  declared unusable because they ran next to other jobs (plan addendum 1, A1).
  For context only, they show large maxima **without** T1 too: ring 67.5 ms
  and hub 84.0 ms frozen.
- **What that implies.** Single maxima vary from run to run. A check must
  treat the run as the unit and compare paired runs (the lesson of D4c).

## Proposed check: T5, compaction pauses

**Question.** Does T1 lengthen the longest pauses of lifecycle mutations
under fresh-ID churn at 100k nodes? A pause is the time of one lifecycle
call, which includes any compaction or catalog rebuild it triggers.

**Arms.**
- **B:** knotrel `e75ff6a`, the a3-3 candidate, without T1.
- **C:** knotrel `fa5f3a9`, the q3 candidate, with T1.
- T1 is the only executed-code difference between them (PROTOCOL §2.1), so
  the comparison isolates it.
- Both are release builds of the same `core-lifecycle` source (timing build,
  no allocator counter).

**Workload.** The frozen C workload: fresh-ID churn of 5% per cycle,
100,000 nodes, seed 5000001, on `sparse`, `ring` and `hub`.
- **600 cycles per run:** 30 compaction intervals, and with T1 about 97
  catalog rebuilds.

**Measurement.**
- A new `core-lifecycle pauses` mode times every lifecycle call with
  `Instant`, identically in both arms.
- After each cycle, outside the timing, it reads `retired_vertices` to find
  the compaction intervals, as D2c did.
- **Per run:**
  - **P_max:** the longest single call;
  - **P_90:** the 90th percentile of the 30 per-interval maxima (the 27th of
    30), that is, the typical bad compaction pause;
  - the absolute values, for the report.

**Design.**
- 12 analyzed pairs after 2 warmup pairs per topology.
- A fresh process per run.
- Arm order balanced 6/6 by a seeded shuffle.
- These are the R and M_reg rules.

**Estimator and criterion.** The frozen paired estimator: per pair
ln(C/B), interval [r(3), r(10)] for n = 12.
- **PASS** if the upper bound is ≤ ln(1.25);
- **REGRESSION** if the lower bound is > ln(1.25);
- **INCONCLUSIVE** otherwise.
- **Six deciding results:** P_max and P_90 on each of the three topologies.
- **Any non-PASS** goes to the maintainer, as every other deciding non-PASS
  does; there is no waiver.

**Why these choices.**
- **The 25% tolerance is not new.** It is the frozen `query_tail` tolerance
  that q3 already applies to tail latency: A query tail, and M_reg client
  p99. A pause tail is the same kind of metric.
- **e75ff6a as B.** It answers the question asked, T1's effect on the tails.
  The v0.6.0 reference would mix in every other change since v0.6.0.
- **Two metrics.** P_max is the maintainer's "massimo". P_90 of the
  interval maxima is the closest robust analogue of the p99 that can be
  estimated with 30 compactions per run. Using both avoids judging only
  the single most extreme value.
- **600 cycles, replicated.** These are 360 compaction intervals per arm
  and topology, more than one 6,000-cycle run gives. They are spread over 12
  processes, so run-level effects show up in the paired spread instead of in
  one number.

**Cost.**
- About 84 runs of 10–15 s, about 20 minutes, in the chain after B/C.
- One extra build: the probes against `e75ff6a`, already a qualified source.

**Implementation, if accepted.**
- The `pauses` mode in `core-lifecycle`.
- The e75ff6a probe build in `prepare_campaign.sh`.
- The cell list in the chain.
- An analyzer and T5 rows in the decision report.
- Tests, an independent delta review, then the revision-2 freeze.

## Alternatives

1. **No check.** The tails stay an unconstrained, disclosed uncertainty of
   T1. Q3 would then qualify T1 only on memory and median window times.
2. **An absolute ceiling** (for example a maximum pause in ms). It is not
   proposed: no product document states a pause objective, so any figure
   would be chosen now, without a basis.
3. **v0.6.0 as B,** in addition to or instead of e75ff6a. It would answer a
   different question: the release against the reference, rather than T1.
