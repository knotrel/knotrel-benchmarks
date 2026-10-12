# ETT scan-root awake-host confirmation

Exact frozen binaries from the [original pilot](../2026-10-10-ett-scan-root/README.md).
This campaign preserves the [sleep-affected confirmation](../2026-10-10-ett-scan-root-regression/README.md).
Twelve matched pairs per cell, six AB and six BA, 72 sequential processes.
No rebuild, source change, cache flush or petgraph rerun. [Protocol](protocol.md).

Collection: 2026-10-10T16:32:46.068499+00:00 to 2026-10-10T16:34:51.578760+00:00.
No sleep observed: **True**. Successful complete campaign: **True**.
Process-scoped `caffeinate -is` assertions were captured at both boundaries.
The inhibitor ends with collection. [Environment](environment.json) and [power events](power-events.txt).
No observed sleep does not guarantee CPU isolation or identical cache state.

| Case | Before ms | After ms | Runtime change | Faster pairs | Setup change | RSS change | Flag |
|---|---:|---:|---:|---:|---:|---:|---|
| dense-bridge-churn-v1-n512-q90-warmed-p0-ett-scan | 37.125 | 20.551 | -44.64% | 12/12 | -1.78% | -0.38% | False |
| sustained-churn-path-v1-n1000000-q50-fresh-p0-ett-scan | 6.134 | 6.777 | +10.48% | 6/12 | +1.10% | +1.83% | False |
| sustained-churn-path-v1-n1000000-q50-warmed-p0-ett-scan | 9.295 | 8.885 | -4.40% | 5/12 | -0.28% | -3.31% | False |

A screening flag requires >5% median runtime increase and at least 8/12 adverse pairs.
This is not a significance test. All failures, outliers and paired values are retained in
[comparison.json](comparison.json), with operation totals/tails and whole-process resources.
Whole-process resource counts include construction, warmup and destruction; they cannot
attribute a replay-local slowdown to scheduling, page faults or compiler layout.

## Structural and provenance checks

Both repeated structural path runs and complete before/after outputs match exactly.
No candidate edges are scanned on the path. Root counters match the prior diagnosis.
Analysis checks trace fingerprints, reference answer/operation counts, unchanged forest
stats, raw artifact hashes and balanced engine order. The collector verifies frozen binary
hashes before every run. Production code was not modified; the previous full candidate
workspace checks remain historical evidence and were not rerun for this measurement-only task.

Reproduce: `python3 analyze.py` then `python3 report.py`. No automatic core integration.
