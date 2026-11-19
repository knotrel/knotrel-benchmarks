# D4b: middleware isolation and a declared re-measurement (item 4, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D4b. It is not part of the
qualification. The a3-3 result stands: B4 `metrics-ops` INCONCLUSIVE +5.65%
[+2.93, +8.58] against a 6% tolerance. This measurement is separate from
it, does not re-run or replace it, and does not bear on its verdict.

## Setup

**Workload.** The frozen `metrics-ops` scenario: sparse 10k, 40 requests,
seed 5000001. Metrics on and off run in the same process, as frozen.

**Variants.**
- **V0:** the a3-3 candidate's frozen probe binary, unmodified.
- **V1:** a diagnostic build (`d4b-variants.diff`) with the `track_http`
  layer omitted (`KNOTREL_D4B_NO_TRACK`).
  - The handler, operation and lifecycle metrics are unchanged.
  - The timeout-marking and shutdown-gate telemetry, which metrics also
    enable, are unchanged.
- **V2:** the same build with `KNOTREL_D4B_CACHED`. `track_http` records
  through handles resolved once per label set, filled on first use, instead
  of `Family::get_or_create` on every request.
  - `micro/src/bin/export-check.rs` checks that it exports the same series
    as the released path: 295 unique series-shape lines (including `#` HELP
    and TYPE lines), identical label sets, identical request counters (`raw/export-check.txt`). Family maps do not keep
    order, so the comparison ignores series order.
- **(a) Micro-measure** (`micro/`): `track_http`'s per-request work outside
  `next.run`, 15 × 1,000,000 calls.

**Numerosity and stop criterion**, declared before collection:
- 200 analyzed pairs per variant, in two runs of 100 plus 4 warmup.
- Run order: V0, V1, V1, V0, then V2, V2.
- Fixed sample size: no interim analysis, no early stop, no extension.

**Estimator.** The frozen method: per-pair ln(on/off), median, and a
distribution-free 95% order-statistic interval [r(86), r(115)].

**Host.** The developer laptop, not gated.

**Departures and events (`raw/runs.txt`).**
1. **First invocations aborted before collection.** The first four
   invocations stopped before collecting any pair. The shell passed the
   argument string as one word, and the probe printed `Error: missing
   value`. Their outputs are in `raw/aborted/`.
   - This was an invocation error (shell quoting), not the probe error the
     declared rule covers. Repeating them is reasonable, and it is disclosed
     here.
   - Each run's single repeat is now used. All repeats completed with 100
     pairs.
2. **V2's trigger reading was chosen after seeing V0 and V1.**
   - The declared trigger reads "V0 − V1 indicates a middleware share of at
     least 1.0 percentage point". The plan also says a difference is claimed
     only if the intervals do not overlap.
   - The trigger was read on the point estimate (+1.08 points), which is the
     looser reading. Under the stricter reading (non-overlapping intervals)
     V2 would not have been triggered. Neither would it by (a), at 0.15%.
   - **V2 is therefore supplementary.** It bears on no conclusion beyond its
     own non-resolved result.
3. **V2's runs are appended, not interleaved ABBA,** as declared.
4. **Two binaries for V1 and V2, and a different build from V0.**
   - V0 is the frozen a3-3 binary.
   - V1 ran on a scratch build. Its stamp `4f41f82 base` (dirty) is a scratch
     snapshot whose tree equals e75ff6a's, plus `d4b-variants.diff` without
     the V2 hunks. That intermediate source is not archived separately.
   - V2 is a later rebuild with the full diff. Both hashes are in
     `raw/binary-sha256.txt`.
   - **V0 against V1/V2 therefore differs in build** (codegen and layout) as
     well as in the layer. There is no same-binary control (V1's binary with
     the variable unset). Differences of about 1 point cannot be attributed
     to the layer alone.
5. **File naming.** The plan named `d4b-no-middleware.diff`. V1's switch and
   V2's cache are both in `d4b-variants.diff`.

## Results (`summary.txt`, `raw/micro.jsonl`)

| | Median overhead (metrics on/off) | 95% interval | Median window on / off | Per-run medians |
|---|---|---|---|---|
| V0 frozen binary | **+7.02%** | [+5.95, +7.74] | 2,974.0 / 2,787.2 µs | +7.39%, +6.31% |
| V1 without `track_http` | +5.94% | [+4.75, +6.65] | 2,959.7 / 2,817.7 µs | +5.36%, +6.45% |
| V2 cached handles (same metrics) | +6.30% | [+5.70, +7.14] | 2,985.5 / 2,793.7 µs | +5.91%, +6.71% |

- **V0 − V1:** +1.08 points; the intervals overlap, so no difference is
  claimed (declared rule).
- **V0 − V2:** +0.72 points; the intervals overlap, so no difference is
  claimed.
- **(a) `track_http` recording work:** 112.5 ns per request (110.8–124.7),
  or 4.2 µs per 37-request window, about **0.15%** of the 2.8 ms window.

## What this indicates (no verdict)

1. **The middleware layer is neither shown nor excluded as a contributor.**
   - The recording work is estimated at about 0.15% of the window, from a
     hot-cache microbenchmark: a fresh family, one label set, clock reads
     back to back, no async frame.
   - Removing the whole layer (V1) gave −1.08 points. That is 15% of V0's
     overhead, the low end of D4's 15–40% outside-handler share. It is not
     resolved at n = 200.
   - Run-to-run spread within a variant (V0 +7.39 / +6.31; V1 +5.36 / +6.45)
     is as large as the effect, and V0 and V1 differ in build (departure 4).
2. **The cheaper path with the same observability (V2) shows no resolved
   gain** (−0.72 points, not resolved). Under the declared rule, no variant
   that keeps the same metrics is shown to reduce the overhead.
3. **The 6% budget without reduced observability** is still **not
   established**.
   - On this ungated laptop, at n = 200, V0's interval is [+5.95, +7.74]:
     lower bound 5.95%, almost entirely above the 6% tolerance.
   - That host and sample size differ from a3-3's. The figure describes this
     diagnostic only. It is not a re-run, and the a3-3 INCONCLUSIVE stands.
4. **Where the rest is.** D4 placed most of the metrics overhead in the
   apply phase (operation metrics and job-phase timing in the handler). The
   outside-handler part (15–40%) is not attributed. The recording work alone
   is small by microbenchmark, and the layer as a whole is unresolved. A next
   isolation would be the per-batch job clock and the operation counters in
   the handler, with a same-binary control. D4's variant (d) did not reduce them;
   nothing further was measured here.

## Limits

- One host, not gated, and 200 pairs per variant.
- The micro-measure excludes the middleware's async frame and the request
  extension lookup.
- The order-statistic intervals of separate variants are compared only for
  overlap. That comparison is conservative.
