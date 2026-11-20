# D4c: metrics clock and counters on the same binary (item 4, phase 3)

This diagnostic follows DIAGNOSTICS-PLAN-3.md, D4c. It is not part of the
qualification. The a3-3 result stands: B4 `metrics-ops` INCONCLUSIVE +5.65%.
The 6% budget is unchanged.

**Setup.**
- **One diagnostic binary** (`d4c-variants.diff` on e75ff6a), with the
  variant selected by `KNOTREL_D4C`:
  - `ctl`: the released path, the same-binary control;
  - `nocount`: no per-operation counters;
  - `noclock`: no job clock (queue, lock-wait and execution histograms);
  - `nogauge`: no graph-count gauges;
  - `notrack`: no `track_http` layer;
  - `noall`: none of the four.
- **Workload:** the frozen `metrics-ops` scenario, metrics on against off in
  the same process.
- **Size:** 200 pairs per variant, in two runs of 100 plus 4 warmup.
- **Order:** ctl, nocount, noclock, nogauge, notrack, noall, then reversed.
  Fixed n, run in the quiet phase-3 timing chain.
- **Estimator:** median ln(on/off), with the distribution-free 95% interval
  [r(86), r(115)].
- **Outputs:** `raw/run01-ctl.jsonl` … `raw/run12-ctl.jsonl`. `summary.txt`
  comes from `analyze.py`.

## Results (`summary.txt`)

| Variant | Median overhead [95%] | Run medians (first block, second block) | ctl − variant (declared rule) |
|---|---|---|---|
| ctl | **+5.41%** [+4.54, +5.82] | +5.73%, +4.64% | — |
| nocount | +1.68% [+1.12, +2.33] | **+5.81%, −1.21%** | +3.73 points, claimed |
| noclock | +0.97% [+0.21, +1.35] | +1.50%, −0.43% | +4.44 points, claimed |
| nogauge | +0.80% [+0.13, +1.58] | +1.67%, +0.23% | +4.61 points, claimed |
| notrack | +3.76% [+3.26, +4.84] | +3.78%, +3.55% | +1.64 points, not claimed |
| noall | +2.99% [+2.15, +3.32] | +3.08%, +2.26% | +2.42 points, claimed |

## Reading: the decomposition is not internally consistent

By the declared rule, the nocount, noclock, nogauge and noall shares are
"claimed": their intervals do not overlap ctl's. The data contradict the
model behind that rule:
- **noall is above three of its parts.** noall (+2.99%) removes everything
  that nocount (+1.68%), noclock (+0.97%) and nogauge (+0.80%) each remove,
  and more. Its overhead cannot be higher than theirs if the components
  added up.
- **The run-to-run spread of one variant is as large as the effects.**
  nocount's two runs differ by about 7 points (+5.81% against −1.21%). Each
  variant's pooled interval of 200 pairs mixes two runs whose medians
  differ, so the interval understates the variability between runs.
- **The likely, but not shown, explanation is run-level effects** (process
  start, memory layout, host state) rather than the instrumentation. The
  paired within-run design would not remove them. The data show the
  inconsistency, not its cause.

**Conclusion (no verdict).**
- The 6% budget question is still **not resolved**.
- On the same-binary control, the released overhead measured +5.41% [+4.54,
  +5.82] on this host. That is not a qualification result.

**Maintainer decision (2026-11-20, plan addendum 4):** "accetto l'omissione
del follow-up come deviazione della sola diagnostica. Non considero risolto
l'overhead e non concedo deroghe al 6%: deciderà la misura q3 prevista dal
protocollo." The departure below is accepted for this diagnostic only; the
overhead stays unresolved and B4 `metrics-ops` in qualification 3 decides at
6%.

**Departure from the plan (accepted as a diagnostic-only departure).** The
declared follow-up (a same-observability variant for each claimed component,
candidate inclusion only without overlap) was **not run**. That decision was
taken after seeing the data.
- **Why:** the claimed shares are contradicted by the data's own internal
  consistency. A follow-up measured with the same protocol would carry the
  same run-level effects. It could pass the non-overlap rule spuriously and
  put a metrics change into the candidate on noise.
- **This is reported, not resolved.** The candidate contains no metrics
  change, and the B4 `metrics-ops` cell will be measured in qualification 3
  on the released metrics code, against its unchanged 6% tolerance.
- **What would settle it** is a design with more runs and fewer pairs per run
  (for example 20 runs × 10 pairs per variant, analyzed with the run as the
  unit), declared before collection. That is for the maintainer to decide.
