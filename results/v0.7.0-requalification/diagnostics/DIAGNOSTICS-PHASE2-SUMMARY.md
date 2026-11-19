# v0.7.0 re-qualification: diagnostics phase 2 summary

These are the diagnostics the maintainer ordered on 2026-11-19 (path C, all
items), run against the plan declared before measuring in
[`DIAGNOSTICS-PLAN-2.md`](DIAGNOSTICS-PLAN-2.md). Departures from the plan
are listed in each README.

Rules that hold throughout:
- **a3-3 and its verdicts are preserved:** REGRESSION, FAIL ×3,
  INCONCLUSIVE ×2, INVALID. No exception, threshold change or release.
- **Product patches are diagnostic builds only.**
- **The qualification remains non-conforming**, and the decision is pending
  ("qualificazione non conforme, decisione pendente"). Non-conforming refers
  to the outcome (non-PASS results). The run itself, a3-3, was CONFORMING to
  the conformance protocol.

All measurements ran on the developer laptop, not gated.

## 1. Causes: demonstrated or indicated

| Item (a3-3 result) | Cause, and the strength of the evidence | Evidence |
|---|---|---|
| **1. B4 `import-high` REGRESSION** | **Measured breakdown.** L − E splits into: parse +776 µs (about 1.05 GB/s in L and F, 0.87 GB/s in E; roughly proportional to body bytes between L and F), catalog/sort/finish +725 µs (holding the registered topology), and effective engine +208 µs. L − F (+305 µs) is mostly parse (+226 µs). Construction costs about the same in L and F (1,071 against 1,012 µs) for different work. | [D1b](D1b-prepare/README.md) (30 rounds) |
| **2. C3 heap FAIL ×3** | **Demonstrated.** The catalog hash table grows from 131,072 to 262,144 buckets at cycle 5. Fresh-ID churn leaves tombstones until it grows. Reserving that size at construction is the only change, and C3 then passes in all three topologies, with peak and steady state identical to the byte. | [D2b](D2b-presize/README.md) (deterministic counts; reproduces D2 byte for byte) |
| **3. B4 `ops` 100k INCONCLUSIVE** | **Indicated.** Both arms make the same number of engine link/cut calls (1,860 / 10,470); engine shifts differ (28,700 against 36,971). The difference is mostly the lifecycle catalog bookkeeping, roughly 85% of the core difference, estimated from profile sample shares: scans, neighbor probes, incident shifts, binary searches. The core replay does not reproduce D3's server ratio (2.54 against 1.74); about 300 µs per window is unexplained. The frozen reference's planner does comparable work outside the window (694 µs over the same trace, from a separate run and binary). About 2,886 of the 9,464 lifecycle operations are no-ops. | [D3b](D3b-ops-window/README.md) (core replay, counters, 6+6 profile windows) |
| **4. B4 `metrics-ops` INCONCLUSIVE** | **Not resolved.** Lock timing is about 1% of the overhead (D4). `track_http`'s recording work is about 0.15% of the window by microbenchmark. Removing the whole layer gave −1.08 points, which is unresolved and confounded by a different build. The layer is neither shown nor excluded; the rest is unattributed. | [D4b](D4b-middleware/README.md) (200 pairs per variant, declared) |
| **6. M_desc INVALID (6/6 HTTP 412)** | Already classified by D5: a probe error, met by correct server precondition enforcement. Verified now: with bounded refresh and one retry after a 412, the same stale-token situation completes every attempted import (6, 5, 5). In one run the refresh used 11 of its 12 attempts. | [D5b](D5b-probe-refresh/README.md) |

## 2. Interventions verified by a measured variant

| Intervention | Verified effect | Measured cost | Status |
|---|---|---|---|
| **Catalog pre-size at construction (2n)** | C3 PASS in all 3 topologies (growth −0.017 / +0.030 / −0.005) | B5 2.9999992× against ≤ 3.0: passes by **8 bytes**; +5.12 MiB at construction; import +3.5% (pair range −4.3% to +7.5%) | diagnostic build only. The margin is not robust: it depends on n and fixed per-node sizes. |
| Full pre-size (catalog + engine) | C3 PASS | B5 3.40× FAIL | rejected by the rules |
| Engine-only pre-size (ids/hdr/eng) | not sufficient: ring stays FAIL | import net heap +2.1 to +4.4 MiB (at construction, hdr-1.25 is below frozen) | — |
| **Probe revision 3** (bounded refresh, 412 retry, starvation flag) | stale token recovers in all 3 forced runs (6/6, 5/5, 5/5); 10 Rust and 15 Python tests | refresh 19 ms, 62 ms and 1.2 s under 64 clients; the last used 11 of 12 attempts | in the tooling, amendment 4 (§11), reviewed; the retry bound is a maintainer decision |
| Metrics: V1 (no `track_http`), V2 (cached handles, same series) | no resolved reduction (−1.08 / −0.72 points, intervals overlap; different builds from V0; V2 supplementary) | — | not shown effective |

**Not verified by any variant** (hypotheses only):
- **Import:** arena/CSR incident allocation (198 µs), cheaper sort/dedup
  (242 µs), indices assigned in the catalog pass (about 208 µs). Their total
  is an upper bound of about 490 µs (absolute and relative-to-E costs
  mixed), which even if fully saved leaves L/E
  far above the 2× tolerance (≈ 4.9 against E).
- **Ops:** another incident layout, and a reused `affected` buffer.
- **Ops, unexplained residual:** about 300 µs per window between D3's
  apply phase and the core replay, unprofiled.

## 3. Quantitative trade-offs

- **Import (B4 `import-high`).** Parse is set by the wire format; catalog
  volume by the contract that keeps registered entries.
  - Within the current contract and format, no plausible implementation
    change reaches the 100% tolerance (bound above).
  - Reaching it needs a contract or format decision: a more compact flag
    encoding, or importing only the effective graph. Otherwise it needs a
    rule decision, for example a capability-equivalent reference; that would
    apply to a future qualification only.
- **C3 against B5.** The catalog pre-size buys C3 for +5.12 MiB per 100k
  nodes. It takes B5 from 2.45× to 3.000× (8 B of margin).
  - Alternatives are a product change that avoids tombstone-driven growth
    (unmeasured), or a rule change: a longer window, or measuring after the
    first compaction. Both are decisions for a future release.
  - **Long run (1,500 cycles):**
    - the peak always falls in the first interval;
    - after that the heap stays in a band; interval maxima have an SD of
      12–22 KB;
    - ring trends +12.5 KiB per 1,000 cycles (+0.04%);
    - sparse is bounded by the halves rule; ring and hub fail it by about
      7 KB; all three fail the drift criterion by 8–15 KB.
- **Ops 100k.** At core level, lifecycle against plain plus planner is about
  +10%. Against the frozen reference, which plans untimed, it is +154% at
  core level (+20–24% end to end).
  - The gap is mostly the bookkeeping itself. Moving under 25% within the frozen
    rule needs cheaper catalog maintenance (unmeasured), or a rule decision
    to time the reference's planning.
- **Metrics-ops.**
  - The released overhead measured +7.02% [+5.95, +7.74] in this diagnostic,
    with a lower bound of 5.95%. The host is ungated, n = 200, and it does
    not bear on a3-3.
  - No variant that keeps the same observability was shown to reduce it.
  - Meeting 6% without reducing observability is still not established.
    The unattributed part (job-phase timing and operation counters in the
    handler) is the next isolation target.
- **M_desc.** The tooling fix is verified. The stats admission options are
  in [`STATS-ADMISSION-PROPOSAL.md`](STATS-ADMISSION-PROPOSAL.md). The
  recommendation is to keep the status quo with retry guidance in the docs,
  and to consider a 412 `ETag` header; nothing has been implemented.

## 4. Proposed qualification path (for the maintainer's decision)

**Decisions needed before any new campaign.** None is taken here.
1. **Item 1 (import):** the contract question. Is the full registered
   topology plus flags in the body required? If yes, the B4 reference or its
   tolerance must change, by a forward-only rule decision. If no, a format
   change is the product route.
2. **Item 2 (C3):** adopt the catalog pre-size (8-byte B5 margin), seek a
   product fix for tombstone growth, or change the rule (window or
   post-compaction measurement) for a future release.
3. **Item 3 (ops 100k):** keep the untimed-planner reference, or time it.
   Alternatively, invest in catalog maintenance (unmeasured).
4. **Item 4 (metrics-ops):** one more isolation (handler job clock and
   operation counters) before any product change.
5. **Item 6:** approve amendment 4 for future collections (probe
   revision 3), decide whether to raise its retry bound (one run used 11 of
   12 attempts), and choose a stats admission option.
6. **Items 5 and 7–10 of the comparison report's §9** (a3-3 numbering, not
   the plan's item numbers) remain pending.

**Then, a new campaign.**
- Product changes, if any, go into a new candidate commit.
- Then a new matrix and freeze, with tooling from amendment 4 and any
  forward-only rule changes decided above, declared before measuring.
- Then a series with its own cap, on the same terminal-controller and
  interference rules as a3, unless changed.
- a3-3 stays the qualification of e75ff6a, with its verdicts. A new
  campaign qualifies a new candidate, or e75ff6a under new declared rules.
  It never re-labels a3-3.

**What can be done without decisions.** Only the D4 follow-up isolation, with
a same-binary control.

**Review.** An independent review of the phase-2 commits found no blockers.
Its should-fix and minor findings are addressed in the READMEs, this
summary, the proposal and amendment 4. The D5b live runs were repeated with
the final probe source.
