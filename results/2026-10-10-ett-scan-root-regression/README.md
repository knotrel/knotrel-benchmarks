# ETT scan-root regression diagnosis

**Do not integrate yet.** The original +36.77% warmed path regression did not
repeat, but macOS slept during this confirmation campaign. The measured sign
reversal cannot close the regression or establish a path speedup.

[Original pilot](../2026-10-10-ett-scan-root/README.md),
[predeclared protocol](protocol.md), [all results](comparison.json),
[commands, order and hashes](manifest.json).

## Fixed-budget confirmation

Exact original binaries, no rebuilding or source changes. Twelve pairs per cell,
six AB and six BA, randomized group order, 72 sequential successful processes.
All samples are retained, including resource anomalies. No petgraph rerun.

| Case | Before median ms | After median ms | Runtime change | Faster pairs |
|---|---:|---:|---:|---:|
| Dense bridge512 q90 warmed | 34.641 | 19.056 | −44.99% | 12/12 |
| Path1M q50 fresh | 4.904 | 5.023 | +2.43% | 4/12 |
| Path1M q50 warmed | 6.846 | 6.095 | −10.97% | 11/12 |

No new screening flag under the predeclared >5%, >=8/12 adverse-pair rule.
This is not an acceptance decision. Fresh path has adverse pairs of +69.59%
and +106.02%; every pair is available in the comparison file. In the dense
control, all pairs improve between 44.14% and 46.30%, cut total improves 45.07%
and cut p95 improves 45.04%. This agrees with the original targeted benefit.

## What the graph actually does

The separately instrumented path replay was repeated twice per variant. Its
complete per-operation JSON is identical before/after, including answers, root
calls/steps and forest counters. Cuts perform 1,500 root calls and 16,200 parent
steps; queries perform 1,000 root calls and 14,039 parent steps. No candidate
edges or vertices are scanned. This verifies no extra root traversal work on
this path; it does not prove identical generated machine code or memory access.
The counter runner has no warmup and is not used for elapsed-time conclusions.

Inspection of `main.rs::replay` confirms that warmup performs a full replay on a
fresh graph and the measured replay constructs another graph. Graph state does
not carry over; allocator and process cache state can. On the warmed path the
measured replay is only about 6–7 ms within roughly 3 seconds of process work.
Whole-process resource counts cannot isolate that small interval.

## Environmental finding and limits

Three successful runs report long wall time with little CPU time:

| Run | UTC start | Process real seconds | User / system seconds |
|---|---|---:|---:|
| g04-t02-before (warmed path) | 14:32:49 | 928.98 | 2.88 / 0.12 |
| g17-t04-before (fresh path) | 14:49:03 | 927.51 | 1.49 / 0.06 |
| g32-t02-after (fresh path) | 15:05:16 | 926.66 | 1.51 / 0.07 |

[Filtered macOS power events](power-events.txt) confirm maintenance sleep and
DarkWake intervals overlapping these runs. Events use local time UTC+02:00.
The subprocess timeout did not flag them; timeout completion therefore does not
certify uninterrupted wall time on this host. The benchmark's replay timer
remained in milliseconds. Do not subtract sleep duration from replay timings or
selectively discard these runs to obtain a favorable result.

This proves environmental disruption in **this confirmation**, not the cause of
the earlier pilot's warmed-path regression. Changes in whole-process context
switches, RSS and cycles do not establish replay-local causality. Whole-process
retired instruction medians differ by only +0.024% fresh and −0.0067% warmed;
these counts are dominated by graph setup and destruction.

## Decision and next experiment

Keep the candidate and original regression intact. Before a wider matrix,
repeat a separately named fixed-budget confirmation while the machine is fully
awake, with a process-scoped idle-sleep inhibitor and captured power events.
An idle-sleep inhibitor alone must not be treated as protection against lid-close
or forced sleep: verify that no sleep overlaps the actual campaign and mark the
whole campaign environmentally invalid if it does. Preserve invalid runs.

Only if the path remains adverse under those conditions should the next step
instrument replay-local CPU/resource counters or inspect compiler layout. Do not
change the graph algorithm to explain a slowdown that is not yet reproducible.

## Validation

Analysis verifies frozen artifact hashes, 72 runs, balanced order, reference trace
fingerprints, expected query counts, operation counts and unchanged forest stats.
Structural repeats and complete before/after outputs match exactly. The original
source/binary audit still passes. Production core remains unchanged; existing
full candidate workspace verification is retained from the pilot. No Rust code
changed in this investigation, so those checks were not repeated.

Reproduce with `python3 analyze.py` in this directory. `collect.py` refuses to
overwrite an existing manifest. The script documents the historical collection;
use a new directory and the awake-host controls above for further experiments.
