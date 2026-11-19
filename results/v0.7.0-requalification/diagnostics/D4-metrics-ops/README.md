# D4 — B4 `metrics-ops` sparse 10k INCONCLUSIVE: metrics recording vs lock timing

Diagnostic ordered on 2026-11-19 (DIAGNOSTICS-PLAN.md, D4). It is not part
of the qualification. The a3-3 result, INCONCLUSIVE +5.65% [+2.93, +8.58]
against a 6% tolerance, stands. This measurement is separate from it.

**Setup.** A diagnostic build of the candidate (`variants.diff`, on top of
the D3 phase counters) selects a variant with `KNOTREL_D4_VARIANT`. Each run
is the frozen `--scenario metrics-ops --nodes 10000 --requests 40`, seed
5000001: two lifecycle servers, metrics on vs off, 24 pairs after 2 warmup,
alternating arms, one run per variant. Outputs are in `raw/`, summarized
with `../D3-ops-100k/phases.py`.

## Variants and results (metrics on vs metrics off, same build)

| Variant | Exports the same metrics as released? | Median window overhead (pair min–max, not a confidence interval) | Lock-wait phase difference | Apply phase difference | Outside-handler difference |
|---|---|---|---|---|---|
| (b) released (first run, `metrics-ops-instrumented.jsonl`) | yes | +5.2% (−9.9 to +11.0) | +1.5 µs | +110.3 µs | +23.2 µs |
| (b) released (`metrics-ops-released.jsonl`) | yes | +4.2% (−5.6 to +20.5) | +1.2 µs | +54.9 µs | +41.6 µs |
| (c) no `RwLock` acquisition timing | **no**: the lock-wait histograms are not observed | +5.1% (−2.3 to +9.2) | +0.0 µs | +46.1 µs | +41.9 µs |
| (d) per-batch aggregated operation counts, one flush per batch | yes, the same counters and totals (by construction; not scraped here) | +4.4% (−7.2 to +9.4) | +1.4 µs | +56.5 µs | +49.6 µs |

(Window totals are 2.7–3.0 ms; the overhead is 100–150 µs per window.)

## Reading

- **Lock-acquisition timing** costs about 1–1.5 µs per 37-request window,
  about 1% of the metrics overhead. Removing it (c) does not move the
  overhead beyond run-to-run noise.
- **Per-operation counting.** Aggregating the counts per batch (d) does not
  measurably change the apply-phase difference: 56 µs against 55 µs in (b).
  The two runs of (b) itself differ by a factor of 2 in that phase (55 and
  110 µs).
- **Outside the handler.** 15–40% of the overhead lies there (+23 to
  +50 µs). That phase includes the router, body parse, the request-level
  middleware and the probe loop. Nothing here isolates the metrics share
  within it.
- **Run-to-run noise** on this laptop (pair ranges about ±10%) is larger than
  any difference between variants.

## Answer to the maintainer's question (no verdict)

- **Can the 6% budget be met without reducing observability?** Not
  established. No variant that exports the same metrics showed a reduction
  beyond run-to-run noise. Removing lock timing reduces observability, and
  its share is about 1% of the metrics overhead, not 1 point of the window.
  In this run (c) measured +5.1% against (b)'s +4.2%.
- These medians come from an instrumented build (the D3 counters in every
  variant) on an ungated laptop. They are not evidence about the qualified
  result, and they do not bear on its verdict.

**Departures from the plan.**
- The plan asked for an interval per variant. The table gives pair min–max
  instead.
- Variant (d) was built without a profile pointing to it, although the plan
  made it conditional on one.
- That (d) exports the same metrics follows from the code (same counters,
  same totals). It was not checked by scraping.
- (b) was run twice.
