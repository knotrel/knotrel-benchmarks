# v0.6.0 supplementary contention run (M supplement): report

**SUPPLEMENTARY.** This run does not replace, re-classify or extend any result
of the frozen v0.6.0 campaign, and it grants no waiver. The frozen verdicts in
`COMPARISON-v0.5.0-v0.6.0.md` stand as they are. Whether these results count
for v0.6.0 is the maintainer's decision.

Protocol: [`PROTOCOL-M-SUPPLEMENT.md`](PROTOCOL-M-SUPPLEMENT.md). Matrix:
[`MATRIX-M-SUPPLEMENT.json`](MATRIX-M-SUPPLEMENT.json).
Authorization: maintainer, 2026-11-17, "Rerun M dichiarato".

## 1. Identities and conditions

| Item | Value |
|---|---|
| Tooling commit (probe revision 2, collector, analysis, matrix, protocol) | `8e190f725d170ba60ebcbc050468dc2bd7d2fb1a` |
| Freeze commit (adds `FREEZE-M-SUPPLEMENT.json` only) | `8faf37bb6587dd57ab93aa4e7209c41df95a61c0` |
| Candidate server (48bc82f, the frozen campaign's own build) | sha256 `d4adec2e…021667d`, verified `OK` against the campaign's `binaries-sha256.txt` |
| Reference server (v0.5.0, 51e3b4d, the frozen campaign's own build) | sha256 `e3d12df8…6c1b236`, verified `OK` |
| Probe (built at the freeze commit, `--locked --offline`, rustc 1.100.0) | sha256 `e7d0b4b6…058a34d` |
| Run | 2026-11-17 06:23:40–06:32:14 UTC (M_desc 4.5 min, M_reg 4.0 min; budget 14, cap 30) |
| Host | Apple M3, macOS 26.5.2, AC power on all 62 children, no thermal or performance warning, no build process |
| Evidence | `evidence/v0.6.0-m-supplement-48bc82f/` (raw outputs, logs, `logs/outputs-sha256.txt`) |

**Pre-measurement checks:**
- Clippy with `-D warnings` and a release build of the probe.
- The Python suite: 256 tests OK, 2 skipped.
- A functional check on both servers with 0 invalid configurations:
  `evidence/v0.6.0-diagnostics/m-supplement-functional-check/`.

No child failed, nothing was rerun, and no extension was used.

**Disclosed wording discrepancy:** `PROTOCOL-M-SUPPLEMENT.md` §3 and the
matrix's `covers` text say "all 6 configurations" per source-managed server.
The frozen matrix actually has 9 per server: no background, import and events
at 4, 16 and 64 clients. The supplement matrix copies all 9, as its
repeated-for-order rule requires, and the run executed exactly the matrix:
4 × 9 + 2 × 12 = 60 configurations. Only the prose miscounted; the frozen
files are left unchanged.

## 2. Validity

All 60 M_desc configuration records and all 48 analyzed M_reg observations
are **valid** under the declared rule:
- no transport or batch-shape errors;
- no per-item error results and no no-op mutations;
- every background activity completed work with zero failures.

The run had no `node_limit_exceeded`, no failed import and no stopped feeder.
The only refusals were 503 admission refusals at 64 clients, which the rule
allows and which are reported below.

## 3. M_reg supplement against v0.5.0 (12 analyzed pairs, fresh server per observation)

| Cell (100k, 16 clients) | Throughput v0.5.0 → v0.6.0 | Change [interval] | Client p99 v0.5.0 → v0.6.0 | Change [interval] | Supplementary outcome |
|---|---|---|---|---|---|
| standalone, lifecycle off, `mixed50`, batch 64, effective toggles | 50.33 → 50.00 req/s | +0.33% [−1.32, +1.33] | 351.1 → 359.9 ms | +1.98% [−1.62, +5.36] | **PASS** |
| source-managed, lifecycle on, `read100`, batch 8, feeder catch-up | 200.83 → 199.33 req/s | +1.01% [−1.15, +4.21] | 92.0 → 94.8 ms | +3.86% [−1.63, +9.41] | **PASS** |

Notes:
- Throughput "change" is positive when v0.6.0 is slower; the ratio is B/C, as
  in the frozen analysis. Medians are per arm, intervals are paired.
- Feeder catch-up was effective in every observation of the second cell:
  3,328–3,648 events per observation on the candidate and 3,520–3,712 on
  v0.5.0, with zero failures.
- Frozen outcomes stay unchanged:
  - the `mixed50` cell: **PASS †**, which measured rejected links;
  - the events cell: **invalid for its purpose**.

## 4. M_desc supplement (candidate, descriptive, one observation per configuration)

Background `completed` counts work over the whole background run (warmup plus
measure window, about 4 s, or 6 s with import). An import runs once per second
when it can.

### 4.1 Feeder catch-up overlapping queries (previously not measured at 100k)

| Server | Clients | Query req/s | Query p99 | Events completed | 503 refusals of the feeder | Feeder batch p50 / max |
|---|---|---|---|---|---|---|
| 100k, off | 4 | 197.7 | 27.4 ms | 28,224 | 0 | 0.1 / 28.7 ms |
| 100k, off | 16 | 196.0 | 92.8 ms | 3,520 | 0 | 82.0 / 94.3 ms |
| 100k, off | 64 | 152.0 | 407.0 ms | 512 | 308 | 0.1 / 152.9 ms |
| 100k, on | 4 | 204.7 | 26.3 ms | 39,360 | 0 | 0.1 / 27.1 ms |
| 100k, on | 16 | 204.7 | 91.4 ms | 3,648 | 0 | 78.7 / 91.4 ms |
| 100k, on | 64 | 162.7 | 244.3 ms | 448 | 303 | 0.1 / 190.2 ms |
| 10k, off / on | 64 | 1,855 / 1,839 | 22.2 / 32.8 ms | 15,552 / 15,488 | 313 / 306 | 0.1 / 18.8 and 17.4 ms |

What this shows:
- **The feeder queues behind queries for the single graph lock.** At 100k
  with 16 clients, a 64-event batch takes about one query batch's lock time
  (p50 about 80 ms), so catch-up falls to about 900 events/s from about 7,000
  (lifecycle off) or 9,800 (lifecycle on) with 4 clients.
- **At 64 clients most feeder attempts are refused.** Queries hold all 32
  admission permits, and the feeder is refused with
  `503 import_in_progress` (documented admission behavior). Accepted batches
  still progress, but catch-up drops to about 120 events/s at 100k.
- **There is no feeder priority over queries.** This is a measured property
  relevant to v0.7.0 and to the supported-envelope work (v1.0 readiness
  criterion 4). It is not a defect of v0.6.0's contract.

### 4.2 Import overlap at 10k with 16 and 64 clients (previously every import failed)

| Server | Clients | Query req/s | Query p99 | Imports completed / failures | Import p50 / max |
|---|---|---|---|---|---|
| 10k, off | 16 | 1,771 | 29.4 ms | 6 / 0 | 20.9 / 21.7 ms |
| 10k, on | 16 | 1,960 | 10.1 ms | 6 / 0 | 20.0 / 21.1 ms |
| 10k, off | 64 | 1,821 | 33.1 ms | 6 / 0 | 42.0 / 88.7 ms |
| 10k, on | 64 | 1,855 | 34.1 ms | 6 / 0 | 39.3 / 45.6 ms |

Each is a single observation. Query p99 with 16 clients and lifecycle off,
29.4 ms, is three times the no-background configuration (9.5 ms) and the
lifecycle-on run (10.1 ms). One observation cannot say whether that is a
systematic import-overlap tail or noise.

### 4.3 `mixed50` at 100k with effective toggles (previously rejected links and no-op cuts)

Full rows are in `analysis/Mdesc-supplement-analysis.json`.

- With batch 1 and 8, throughput and p99 are within a few percent of the
  frozen rows that measured rejected links. With 1 to 16 clients, effective
  toggles cost no visible time beside the BFS queries.
- At batch 64 with 64 clients, the tail is heavier than in the frozen run:
  - lifecycle off: p99 971.8 ms against 893.5 ms;
  - lifecycle on: p99 1,693 ms against 890.9 ms, and 32.7 against
    37.7 req/s.
  - Fairness falls to Jain 0.82–0.85, with 282,000–284,000 refusals.
  - This is a single observation in an overloaded configuration.
- Lock wait stays 0.92–0.99 of client latency at 16 and 64 clients, as in the
  frozen run.

## 5. What changes for the v0.6.0 decision

- **Coverage defect 9 of comparison §8.** The cells the frozen run did not
  measure as declared now have valid supplementary measurements:
  - both M_reg cells PASS against v0.5.0;
  - feeder catch-up and import overlap are covered at both sizes and all
    client counts.
- **Frozen results.** The frozen verdicts and the frozen coverage-defect
  record are not changed.
- **New descriptive findings** for v0.7.0 and the envelope work:
  - The feeder has no priority over queries: catch-up slows by 8–11× from 4 to
    16 clients at 100k, and at 64 clients it is mostly refused by
    admission.
  - At 10k with 16 clients and lifecycle off, one high query p99 coincided
    with import overlap (single observation).
- **M5 rule (i)** was not re-evaluated, as declared; its configurations were
  not affected by the defects. Note that `analysis.json` contains an
  `m5_rule_i` block that the reused analyzer computes automatically over the
  supplement's rows. It is not part of this supplement's results.
