# knotrel#151: compact internal node indices (B64), comparison result

**Decision: REJECT** (frozen analyzer, decision rule D1–D6 of knotrel
`docs/design/compact-node-index.md` section 6.7, approved 2026-11-26).
B64 is not adopted; knotrel#199 is closed unmerged. Two independent items
fail: **D4** (13 primary metrics SLOWER) and **D5** (inspection criterion C4
fails on the candidate). The memory benefit the design aimed for is real
(G1 and G2 pass), but the approved criteria require no time regression and
no inspection-cost failure, and both are violated. No class below was
changed, and nothing was measured again.

## What was compared

| | |
|---|---|
| Base (CUR) | knotrel `2d7fa9d386096ee534508a7d546381cdd06437f3` (`main`) |
| Candidate (B64) | knotrel `0f46322399745c1882adc9d605183340055d750b` (knotrel#199, draft) |
| Harness | knotrel-benchmarks `c2e7d2de2655b7e1e7586e5b9274c335c8640fef`, probes built `--locked`, no overlay, toolchain 1.100.0 |
| Matrix | [`matrix.json`](matrix.json), SHA-256 `31d52ec7…69a9`; 141 cells; windows from the pilot; cap 9 h (approved by the maintainer after the pilot, before the freeze) |
| Freeze | [`FREEZE.json`](FREEZE.json), order seed `658879285057047842` (derived, not chosen) |
| Host | Apple M3, 8 CPUs, 16 GB, AC power; swap 0 at every snapshot; no thermal or performance warning recorded |
| Session | 2026-11-26 18:11 – 2026-11-27 00:55 UTC (6 h 44 min); `end_cause`: all steps ran; 140 cells COMPLETE, Q DELEGATED_DONE |

The pilot (preparatory, never used for decisions) is kept outside this
repository; its ratios were not inspected before the freeze.

## Decision items

| Item | Result | Basis |
|---|---|---|
| D1 correctness | pass | no failed session or cell; smoke and every gate (`same_trace`) passed |
| D2 benefit (G1 and G2) | pass | G1: CB-L `M1` `sparse-1e6` q = 0.825 and `star-1e6` q = 0.825, both SMALLER. G2: 11.7–26.2 bytes saved per registered edge on every M1 cell with V ≥ 10⁵, both engines (threshold 8) |
| D3 no memory metric LARGER | pass | no M1–M5 metric LARGER |
| **D4 no time metric SLOWER (strict)** | **fail** | 13 metrics SLOWER, listed below |
| **D5 Q (C1–C4 on the candidate)** | **fail** | C4 fails: RSS on − off = 77.6 bytes per node, limit 40 (base 8.7) |
| D6 dispositions | pass | maintainer dispositions recorded on 2026-11-27 for all 12 INCONCLUSIVE / TIMER_LIMITED items (see below); the decision stays REJECT |

### D4: the 13 SLOWER metrics

Ratio B / CUR, 24 pairs, interval [r(7), r(18)]; the time margin is 10 %.

| Cell | Operation | Ratio | Interval |
|---|---|---|---|
| R1-cb-sparse-1e6 | `cut` of random edges | 1.567 | [1.556, 1.580] |
| R3-cb-sparse-1e6 | `set_edge_enabled(false)` | 1.470 | [1.459, 1.489] |
| I3-cf-his-1e6 | `set_edge_enabled(true)` on hub spokes | 1.435 | [1.423, 1.448] |
| I3-cb-sparse-1e6 | `set_edge_enabled(true)` | 1.319 | [1.277, 1.361] |
| R4-cb-star-1e4 | hub node removal cycle | 1.316 | [1.302, 1.326] |
| R4-cb-star-1e5 | hub node removal cycle | 1.315 | [1.307, 1.330] |
| I3-cf-his-1e5 | `set_edge_enabled(true)` on hub spokes | 1.315 | [1.304, 1.323] |
| R5-cb-sparse-1e6 | `remove_node` | 1.240 | [1.230, 1.254] |
| I1-cb-sparse-1e6 | incremental build | 1.213 | [1.203, 1.217] |
| I3-cf-his-1e4 | `set_edge_enabled(true)` on hub spokes | 1.208 | [1.202, 1.232] |
| C2-cb-sparse-1e6 | mass-removal churn, total | 1.160 | [1.157, 1.166] |
| I1-cf-sparse-1e6 | incremental build | 1.132 | [1.123, 1.150] |
| I3-cb-his-1e4 | `set_edge_enabled(true)` on hub spokes | 1.105 | [1.104, 1.108] |

Every interval lies wholly above the margin, so none is a borderline class.
The slowdowns concentrate on edge-level mutations of large sparse graphs and
on enabling hub spokes. A plausible reading, not measured: every endpoint
lookup now goes through the `NodeId → slot` hash map, where the base reached
the record directly.

### D5: inspection criterion C4

Delegated collector [`campaign/delegated/Q-attempt1/`](campaign/delegated/Q-attempt1/) (`inspection_q_151.py`, full form, 500 000
nodes, 1 500 000 edges, hub degree 20 000; criteria of knotrel
`docs/console-inspection-costs.md`):

| Arm | C1 | C2 | C3 | C4 | RSS off | RSS on | on − off per node |
|---|---|---|---|---|---|---|---|
| base | pass | pass | pass | pass | 223.9 MB | 228.3 MB | 8.7 B |
| candidate | pass | pass | pass | **fail** | 178.4 MB | 217.3 MB | **77.6 B** (limit 40) |

The candidate server is smaller in absolute terms in both modes. C4 is
defined on the difference, though, and enabling inspection costs about 39 MB
more than in the base. The criterion is reported as failed, as the
inspection document requires.

## What improved (recorded, not offsetting)

- **Memory:** CB-L bulk import live memory q = 0.80–0.88 on every M1 graph
  (all SMALLER); CF-L 0.91–0.95 (SIMILAR). M2–M5: no LARGER; 15 of 46 memory
  metrics SMALLER.
- **Hub paging and hub-spoke work:** P1 full hub traversal FASTER on all 8
  cells (up to 11× at `his-1e6` ordered, ratio 0.091); P2 single pages FASTER
  on 14 of 16 metrics; I2 spoke insertion and R2 spoke cut FASTER (ratios
  0.55–0.75); R4 at `star-1e6` FASTER for both engines.
- **HTTP (P3, P4, C3):** all EQUIVALENT.

Under the approved strict rule, these gains do not offset D4 or D5.

## Items without a class decision (D6)

**Maintainer disposition (2026-11-27), for each of the 12 items:** the
original class and interval are kept, and the item is closed without further
measurement, because D4 and D5 already determine the REJECT of B64. The
dispositions are in [`DISPOSITIONS.json`](DISPOSITIONS.json). Re-running the
frozen analyzer with them gives
[`analysis-with-dispositions.json`](analysis-with-dispositions.json): D6
pass, decision REJECT. Every cell class equals `analysis.json`.


INCONCLUSIVE: `I1-cb-sparse-1e5`, `I2-cf-his-1e4`, `R3-cb-his-1e4`,
`P2-cb-his-1e4-ordered/p99_page_ns`, `C1-cb-sparse-1e5-same/slowest_op_ns`,
`C1-cb-sparse-1e5-toggle/slowest_op_ns`. TIMER_LIMITED (EQUIVALENT without the
limit): the six C1 `observation_ns` metrics.

## Files

| File | Content |
|---|---|
| [`FREEZE.json`](FREEZE.json), [`matrix.json`](matrix.json) | the freeze record and the frozen matrix |
| [`analysis.json`](analysis.json) | frozen analyzer output (`analyze_151.py`, no dispositions) |
| [`DISPOSITIONS.json`](DISPOSITIONS.json), [`analysis-with-dispositions.json`](analysis-with-dispositions.json) | the maintainer's D6 dispositions and the analyzer output with them |
| [`CELLS.md`](CELLS.md) | every classified metric, generated from `analysis.json` |
| [`campaign/`](campaign/) | `record.json`, `schedule.json`, `status.json`, `smoke.jsonl`, `raw.jsonl.zst` (every observation; zstd of the original `raw.jsonl`), `delegated/` (Q collector output and log, both arms) |
| [`binaries-sha256.txt`](binaries-sha256.txt), [`evidence-sha256.txt`](evidence-sha256.txt) | executable hashes; hashes of the original evidence files |
| `host-before.txt`, `host-after.txt` | host state around the session |

Reproduce the analysis:

```bash
zstd -d campaign/raw.jsonl.zst
python3 ../../scripts/analyze_151.py --matrix matrix.json --run campaign --out analysis-check.json
```

This was checked before publication: the output's cells and decision equal
[`analysis.json`](analysis.json).
