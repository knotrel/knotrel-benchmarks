# Packed tokens: resource diagnosis on the flagged path

Exact original flagged trace: one million nodes, 50% query, ten rounds, seed42, no warmup, one replay/process. Eight adjacent pairs with 4/4 order balance; two smoke processes. Same phase markers in both variants. [Protocol](protocol.md).

## Findings and disposition

The original slowdown does not reproduce in this diagnostic: packed tokens have
21.88% lower median replay time, faster in 6/8 pairs. Median replay task CPU moves
from 10.350 to 8.087 ms, faults from 229.5 to 199, COW faults from 108 to 93, and
post-replay resident memory from 684.6 to 587.4 MiB. Replay pageins are zero in both
variants. CPU closely tracks wall time; the data do not support long descheduling
waits as the dominant cost in this observed run. Reduced fault counts do not by
themselves establish the timing cause; representation/code/cache effects remain.

## Separate uninstrumented confirmation

After seeing the diagnostic result, one bounded adaptive confirmation was declared
and run using the exact original pilot/matrix binaries, with no markers. Same
q50, fresh trace, eight balanced pairs, 16 processes. Samples are not pooled with the
diagnostic or historical matrix. [Confirmation protocol](confirmation/protocol.md)
and [raw comparison](confirmation/comparison.json).

The before/after medians are 10.438/8.714 ms (-16.51%), with 6/8 faster pairs.
Whole-process peak RSS medians decrease 12.47%. Before samples span 8.896–23.055 ms;
after samples span 6.899–26.306 ms. The two slower pairs are +6.02% and +160.77%.
Keep both adverse observations: this is not proof of uniformly lower latency or
improved tails. Unlike diagnostic RSS, this RSS is measured over the full process.

Taken with the full matrix's consistent sparse-memory saving and block-runtime
benefit, this supports considering integration of the 64-byte representation as
a memory optimization, with timing limitations explicitly documented. It does not
automatically erase the original regression flag or prove its cause. No further
repeat-until-pass cycle is proposed. The next step is an integration review of
this isolated candidate, without combining promotion-join optimizations. No
production change is made by this report.

## Paired timings

Median original workload timer change: **-21.88%**; packed variant faster in **6/8** pairs. This is a diagnostic result, not a replacement for the original +119.85% matrix regression.

| Variant | Replay ms median (min–max) | Replay CPU ms | Observer replay ms | Setup ms | Replay faults | Replay COW | Replay pageins | Replay switches | RSS after replay MiB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| before | 10.344 (6.363–12.575) | 10.350 | 10.373 | 1859.389 | 229.5 | 108.0 | 0.0 | 1.5 | 684.6 |
| after | 8.081 (6.141–9.953) | 8.087 | 8.106 | 1796.817 | 199.0 | 93.0 | 0.0 | 1.0 | 587.4 |

## Every pair

| Pair | Before ms | After ms | Change | Before/after faults | Before/after COW |
|---:|---:|---:|---:|---|---|
| 0 | 10.864 | 8.931 | -17.79% | 230/198 | 108/93 |
| 1 | 11.275 | 6.141 | -45.54% | 228/199 | 108/93 |
| 2 | 6.363 | 6.974 | +9.61% | 228/199 | 108/93 |
| 3 | 12.575 | 9.445 | -24.89% | 230/203 | 108/93 |
| 4 | 8.376 | 9.953 | +18.82% | 229/199 | 108/93 |
| 5 | 9.345 | 6.204 | -33.61% | 230/199 | 108/93 |
| 6 | 10.566 | 8.743 | -17.25% | 229/199 | 108/93 |
| 7 | 10.123 | 7.419 | -26.71% | 231/199 | 108/93 |

## Limits

Markers pause each child to read counters and can change its subsequent scheduling/cache state. Diagnostic code layout also differs from the uninstrumented matrix. CPU time is Mach ticks converted with calibrated timebase; task counters and observer wall include handshake activity, while original setup/replay timers exclude it. Empty brackets are retained and not subtracted. Context switches include handshake switching. Faults are not disk I/O; pageins are separate. Boundary RSS is not peak process RSS, graph payload or allocator allocation count. Sample buffers and teardown are outside the named phases.

Results cannot establish universal absence of a regression or a causal mechanism. Preserve adverse pairs, the original flagged case and historical results. [analysis.json](analysis.json) retains every phase and range. No page preparation, priority, affinity or system setting was changed. Production sources and candidate patches remain untouched.

## Verification

Source/variant hashes, phase sequence, reference counters, trace fingerprints and balanced order are checked in [audit](audit.json). [Diagnostic checks](verification.json) cover formatting, all-target Clippy, library tests/doctests and Rustdoc; graph correctness tests for the exact packed source passed in the original pilot. Ordinary CLI tests assume no marker handshake and are not used for this diagnostic runner.
