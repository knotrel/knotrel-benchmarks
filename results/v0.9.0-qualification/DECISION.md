# v0.9.0 qualification: final decision record

Two separate statements, which should not be confused:

1. **Campaign execution: VALID.** Attempt 2 is CONFORMING under the frozen
   protocol in Part 1 (deciding) and in Part 2 (descriptive). Part 3 ran to
   completion under its protocol. The data are fit to classify.
2. **Release: ACCEPTED WITH EXCEPTIONS** (accettata con eccezioni), for
   v0.9.0 only.
   - This is **not** "all gates PASS", and **not** a complete qualification.
   - Five deciding results are not PASS. The maintainer accepts them as
     exceptions limited to v0.9.0.
   - Two requirements are not qualified by comparison. The maintainer
     accepts that for this release.
   - Q3 of the feeder protocol stays FAIL, as already declared.
   - Every original classification, interval and threshold stands as
     measured, including UNRESOLVED. Nothing was converted into PASS, and
     nothing was measured again.
   - No exception below is a precedent for any other release.

This file is the single decision record for v0.9.0. It supersedes nothing:
`PROTOCOL.md`, `MATRIX.json` and `FREEZE.json` (revision 1) are unchanged.
The analyses are in `analysis/attempt2/` (commands in
`analysis/attempt2/ANALYSIS-COMMANDS.txt`, checksums in
`analysis/attempt2/analysis-sha256.txt`). Attempt 1 is kept in
`analysis/attempt1/`.

## 1. What was measured

| | |
|---|---|
| Candidate | knotrel `e827b2a7bb1930b70e75ed7ccff2ac0201db9e40` (main after the 0.9.0 version bump) |
| Deciding reference (Part 1) | published knotrel v0.7.0, tag `v0.7.0` = `9f933a783b043f9f44fd5de014c3c8a93c7922c3` |
| Descriptive reference (Part 2) | published knotrel v0.8.0, tag `v0.8.0` = `e3fc7361caf2f29dcf6870e8018b96414ebd927b` |
| Tooling and probes | knotrel-benchmarks `08cc3d99a4792ffe04584d76a8f5b3d4ab33f955` (freeze revision 1); reference probes at `7116c32e` (knotrel 0.7.0) and `e843aae2` (knotrel 0.8.0), same probe source |
| Method | the v0.7.0 qualification-3 method (`results/v0.7.0-qualification-3`, freeze revision 3), unchanged: cells, pairs, estimators, seeds, window multipliers, interference policy and every threshold |
| Host | Apple M3 (4P+4E), 16 GB, macOS 26.5.2, rustc 1.100.0, AC power |
| Attempt 2 | 2026-11-22: Part 1 09:39–11:05Z, Part 2 11:05–11:24Z, Part 3 11:24–11:43Z |
| Raw evidence | private bundles `v0.9.0-qualification-e827b2a-attempt1` and `-attempt2`; checksums of every output file in `analysis/attempt*/campaign-outputs-sha256.txt` (attempt 2: 1855 files, Part 2: 419 files; attempt 1: 1731 files) and of the 20 binaries in `analysis/attempt2/binaries-sha256.txt` |

## 2. Campaign execution

- **Attempt 2, Part 1: CONFORMING.** Every unit was valid under the
  revision-3 policy; counts and binaries were verified at the end.
  - 732 units, 0 invalidated, 0 readiness waits, 0 block restarts.
  - 85.5 min of a 105-min budget.
- **Attempt 2, Part 2: CONFORMING.** 121 units, 0 invalidated, 1 readiness
  wait (22.1 s); 18.3 min of 20.
- **Attempt 2, Part 3:** all seven cells, three observations each, no
  repeated observation; PostgreSQL `18.7-alpine@sha256:ff64c9e3…`.
- **Attempt 1: not conforming, kept, not used.** BUDGET EXHAUSTED at the
  first M_reg unit (105.1 min). Every step before M_reg ended normally. The
  time went to 13 readiness waits (1525.3 s in all, longest 388.3 s),
  caused by interactive use of the host (126 user inputs recorded; the
  busiest external processes were WindowServer, the Codex app, Chrome and
  the Claude app). Two units were invalidated by `duetexpertd` and redone.
  Under the protocol (§2, attempts), a non-conforming first attempt allows
  one second attempt; it was not chosen by any result, since attempt 1 was
  never analyzed. Attempt 2 ran on an idle host.
- **Integrity.** `shasum -c` of every output list and of the binaries: no
  mismatch, for both attempts.
- **Analysis.** Frozen analyzers and the thin v0.9.0 wrappers only
  (`ANALYSIS-COMMANDS.txt`). As in q3, the first B/C invocation failed with
  no output because the path-confinement variable was not set; it was rerun
  with the variable set, and no data was read in between.
- **Post-decision hardening (no effect on results).** For the repository's
  security gate, `analyze_v090q_t5.py` now accepts only hexadecimal commit
  ids and a confined `--benchmarks` path, and `evaluate_v090q_part3.py`
  confines its two paths (`run_part3.sh` sets the confinement root). Rerun on
  the attempt-2 evidence, both produce output byte-identical to the archived
  `T5-analysis.json` and `part3/evaluation.json`. The campaign ran with, and
  reproduces with, the frozen tooling at `08cc3d99`.

## 3. Part 1 results (deciding, candidate against v0.7.0)

| Experiment | Outcome |
|---|---|
| A (session, extension; 24 pairs) | 7 PASS, **1 INCONCLUSIVE_DISCLOSED**, **1 UNRESOLVED** (§4 E1, E2) |
| B1–B4 timing, deciding | 58 PASS, **1 INCONCLUSIVE** (§4 E3) |
| B4 timing, descriptive | 12 PASS, 1 REGRESSION (`import-high`, §5.2) |
| B4 not-equivalent (hub 10k ops, events) | 2 PASS, descriptive, no verdict (§4 E6) |
| B5 memory | 2/2 PASS |
| C1 / C2 / C3 | 30/30 / 60/60 / 15/15 PASS |
| C4 RSS | 9 PASS, **6 EXCEEDS_BUDGET** (disclosure category, §5.1) |
| T5 compaction pauses (arm B = v0.7.0) | 6/6 PASS |
| R | 9 PASS, **2 INCONCLUSIVE** (§4 E4, E5) |
| Rmem | 10/10 PASS |
| M_reg | 6/6 PASS (1 improved) |
| M_desc | 162/162 configurations valid (descriptive) |

**T5** (100k nodes, 600 cycles, 5% fresh churn, 12 pairs; tolerance 25%;
median of the candidate against v0.7.0, with its interval):

| Topology | P_max, v0.7.0 → candidate | P_90, v0.7.0 → candidate |
|---|---|---|
| sparse | 15.58 → 15.59 ms, +2.4% [−1.9, +11.0] PASS | 14.38 → 14.38 ms, +0.5% [−2.4, +1.5] PASS |
| ring | 12.81 → 12.78 ms, −0.2% [−2.7, +2.4] PASS | 12.42 → 12.34 ms, −1.1% [−3.2, +2.1] PASS |
| hub | 15.23 → 14.97 ms, −1.2% [−3.9, +2.9] PASS | 14.35 → 14.28 ms, −0.6% [−2.7, +1.1] PASS |

**M_reg** (v0.7.0 → candidate, request throughput and p99; tolerances 10%
and 25%):

| Cell | Throughput | p99 |
|---|---|---|
| standalone read95, b1, 4 clients, 10k | 30,966 → 31,019 req/s | 0.27 → 0.27 ms |
| standalone read95, b8, 16 clients, 100k | 349 → 350 req/s | 94.7 → 95.3 ms |
| standalone mixed50, b64, 16 clients, 100k | 51 → 51 req/s | 346 → 346 ms |
| standalone lifecycle50, b8, 16 clients, 100k | 397 → 395 req/s | 55.0 → 55.6 ms |
| source-managed read100 during import, 100k | 966 → 979 req/s | 82.9 → 82.3 ms |
| source-managed read100 during events, 100k | 868 → 878 req/s, +1.2% [+0.5, +1.8] PASS (IMPROVED) | 58.2 → 53.0 ms |

## 4. Maintainer decisions (2026-11-22)

> "Accetto i cinque risultati non-PASS come eccezioni limitate alla v0.9.0.
> Mantieni le classificazioni originali, compreso UNRESOLVED, gli intervalli
> e le soglie. Non convertirli in PASS e non ripetere le misure per ottenere
> un esito favorevole."

The five results below keep their classification. None was measured again.

### E1. A `core_sparse_traversal_10k_compact-bfs_warmed`: INCONCLUSIVE_DISCLOSED, accepted

Primary metric `workload_wall_ns`: 4.85 → 5.02 ms, median +5.1%, interval
[−2.6%, +13.8%], tolerance 10%. The median is inside the tolerance; the
interval crosses it. Supporting metrics pass (`connected_p99_ns` +1.2%,
peak RSS +1.2%); `link_p99_ns` and `cut_p99_ns` are report-only (timer
resolution). Both arms show occasional pairs near 7 ms against a typical
4.8 ms. No cause is claimed. In v0.7.0 this cell was PASS.

### E2. A `http_standalone_batch_b256_compact_bfs`: UNRESOLVED, accepted

The primary metric passes: `window_duration_ns` 3.28 → 3.28 ms, −1.1%
[−6.6%, +4.5%] against 10%. The p99 request latency passes (+0.1%). The
supporting `sampled_max_rss_bytes` is INCONCLUSIVE: +1.2% [−2.3%, +23.0%]
against 20%. Under rules v0.4.0 an INCONCLUSIVE supporting metric makes the
cell UNRESOLVED; it stays UNRESOLVED. In v0.7.0 this cell was PASS.

### E3. B4 `metrics-ops`, sparse 10k: INCONCLUSIVE, accepted

`B4-http-metrics-ops-compact-bfs-sparse-10000`: 2.76 → 2.89 ms, median
+5.3%, interval [+0.9%, +7.8%], metrics budget 6%. Same cell and same
status as v0.7.0 (D1 there: +6.5% [+1.7, +7.4]).

### E4–E5. R `core-import` sparse and hub 10k: INCONCLUSIVE, accepted

| Cell | v0.7.0 → candidate | Median | Interval | Tolerance |
|---|---|---|---|---|
| `R-core-import-sparse-10k-20-10` | 974 → 963 µs | −2.4% | [−13.7%, +17.2%] | 10% |
| `R-core-import-hub-10k-20-10` | 822 → 814 µs | −3.3% | [−17.3%, +20.7%] | 10% |

Same cells and same status as v0.7.0 (D2 there).

### E6. B4 `ops` and `events`, hub 10k: not qualified by comparison, accepted for v0.9.0

> "Accetto inoltre, per questa release, la mancata qualificazione
> comparativa delle due celle hub ops/events, con motivazione e limiti
> espliciti."

**Why they are not qualified.** Unchanged from v0.7.0 (q3 §4.1, decision
8; v0.7.0 DECISIONS D3). The candidate has valid observations for both. The
missing piece is a reference that offers the candidate's atomicity:
- the hub 10k trace deactivates two hub nodes, each expanding to 1,425 and
  1,565 plain operations, while a plain request carries at most 1,024
  (`MAX_BATCH_OPERATIONS`, not configurable);
- **ops:** no atomic plain route exists;
- **events:** the only atomic route is a full replacement import per
  affected chunk, a different reference design not adopted.

**Limits.** The two requirements stay **not qualified**; they do not become
PASS. The acceptance applies to v0.9.0 only. The roadmap assigns them to
v1.2.0 (H2).

**Indicative evidence, not a verdict:**

| Requirement | Comparison | v0.7.0 → candidate | Median [interval] |
|---|---|---|---|
| ops | frozen cell (`B4-http-ops-…-hub-10000`) | 2.89 → 3.18 ms | +10.8% [+4.0, +11.4] |
| ops | not-equivalent cell (`…-equivalent-…`) | 3.40 → 3.28 ms | −3.5% [−3.8, −2.7] |
| events | frozen cell | 4.95 → 5.22 ms | +5.0% [+3.8, +6.2] |
| events | not-equivalent cell | 5.54 → 5.22 ms | −5.9% [−7.0, −5.0] |

- **Frozen cells:** the reference plans outside the timed window and is not
  atomic, so it provides a different service.
- **Not-equivalent cells:** the reference plans inside the window but
  splits two chunks into two requests each, so it is still not atomic; the
  bias this introduces is not measured.
- No measured atomic reference exists. The 25% tolerance is quoted for
  orientation only; no status is derived from it.

### E7. Feeder Q3: FAIL, accepted limitation

> "Q3 resta FAIL come limite già accettato"

See §7. Unchanged since the maintainer decision of 2026-11-21.

## 5. Disclosures (kept visible)

### 5.1 C4 RSS: EXCEEDS_BUDGET ×6

C4 is a disclosure category by rule (allocator retention in RSS), not a
FAIL. Same six cells as in v0.7.0. Net RSS first → last, and 30-cycle
projected growth:

| Cell | Net RSS first → last | 30-cycle growth |
|---|---|---|
| sparse fresh 1k | 0.17 → 0.25 MiB | +0.60 |
| sparse fresh 10k | 1.39 → 2.33 MiB | +0.76 |
| sparse fresh 100k | 6.52 → 7.42 MiB | +0.13 |
| ring fresh 100k | 8.45 → 21.62 MiB | +1.06 |
| hub fresh 100k | 1.42 → 5.45 MiB | +2.41 |
| hub same 100k | 5.25 → 6.89 MiB | +0.29 |

The heap rule for the same workloads (C3) passes in every cell.

### 5.2 B4 `import-high`: descriptive REGRESSION, +400%

`B4-http-import-high-compact-bfs-sparse-10000`: 1.55 → 7.65 ms per import
call, +399.7% [+388.9%, +425.7%] against 100%. Descriptive by protocol; it
stays a REGRESSION as measured. The reference imports only the effective
graph; the candidate keeps and validates the complete registered topology.
The capability-equivalent cell (deciding) passes: 5.10 → 8.06 ms, +55.4%
[+54.7%, +62.5%] against 100%. The overhead recurs from every release since
v0.5.0 (v0.7.0: +408%).

## 6. Part 2 (descriptive, candidate against v0.8.0)

No verdict. It describes the change after v0.8.0 (the reserved feeder
admission lanes of 0.9.3).

**B4 feeder events**, lifecycle-arm medians, two unpaired runs of the same
session:

| Cell | v0.8.0 | Candidate | Ratio |
|---|---|---|---|
| events sparse 10k | 4.71 ms | 4.69 ms | 0.995 |
| events hub 10k | 5.22 ms | 5.22 ms | 1.001 |
| events sparse 100k | 6.89 ms | 6.46 ms | 0.937 |
| events equivalent sparse 10k | 4.73 ms | 4.74 ms | 1.002 |
| events equivalent hub 10k | 5.21 ms | 5.22 ms | 1.002 |
| events equivalent sparse 100k | 6.92 ms | 6.83 ms | 0.988 |

**M_reg against v0.8.0:** in all six cells both throughput and p99 are
within the M_reg tolerances (candidate against v0.8.0: throughput −1.3%
to +0.5%, p99 −5.2% to +1.3%; paired medians).

**Conclusion, scoped.** On this host, for these six feeder-event cells and
these six M_reg scenarios, the event-cell ratios are between 0.94 and
1.00 and no M_reg comparison crosses the frozen tolerances. This
says nothing about other workloads, scales or hosts, and the cross-version
event ratios are unpaired.

## 7. Part 3 (feeder under load, candidate)

Protocol `docs/integrations/feeder-under-load.md` (knotrel), seven cells,
three observations each, no `LOAD_*` override.

| Criterion | Rule | Measured | Outcome |
|---|---|---|---|
| Q1 | L1 G100k C=16: p99 ≤ 1000 ms, max ≤ 3000 ms | p99 147.6 ms, max 247.2 ms | PASS |
| Q2 | no growing lag, bounded WAL | 12/12 observations | PASS |
| Q3 | L2 G100k: C=16 ≥ 50 %, C=64 ≥ 25 % of C=0 | 18.0 %, 10.1 % (29,094 and 16,426 of 161,854 changes/s) | **FAIL** (accepted limitation) |
| Q4 | L2 G100k C=64: ready ≤ 60 s | 5.8 s | PASS |
| Q5 | L1 G100k C=16/64 against v0.8.0: throughput ≥ 90 %, p99 ≤ 125 % | throughput 1.02 / 0.94, p99 0.98 / 0.86 | PASS |

- **Deciding (Q1, Q2, Q4, Q5): PASS.**
- **Q3** stays FAIL; thresholds unchanged. Earlier v0.9.0 measurement:
  14.7 % and 8.9 %. No cause is claimed; host CPU contention remains an
  untested hypothesis. Follow-up: knotrel/knotrel#87 (roadmap R2, H2).

## 8. Applicability to the release commit

- The protocol requires the release commit's `crates/`, `Cargo.toml` and
  `Cargo.lock` to equal the candidate's.
- **Checked on 2026-11-22:** knotrel `main` at `cd803e8`:
  `git diff e827b2a cd803e8 -- crates Cargo.toml Cargo.lock rust-toolchain.toml`
  is empty. The commits after the candidate are documentation only.
- The final commit chosen for the tag must be checked the same way before
  tagging. Any difference in those paths requires the campaign again.

## 9. Not claimed

- v0.9.0 is not claimed to be faster in general than v0.7.0 or v0.8.0.
- The five accepted results are not PASS; E2 stays UNRESOLVED.
- The two hub 10k requirements are not qualified.
- Q3 is not met, and no cause for it is claimed.
- Host-specific: Apple M3, macOS. No other platform was measured.
