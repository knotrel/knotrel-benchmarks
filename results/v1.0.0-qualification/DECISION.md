# v1.0.0 qualification: final decision record

Two separate statements, which should not be confused:

1. **Campaign execution: VALID.** Attempt 1 is CONFORMING in Part 1, and
   block Q is COMPLETE under its protocol and cap. The data are fit to
   classify.
2. **Release qualification: ACCEPTED WITH EXCEPTIONS** (accettata con
   eccezioni), for v1.0.0.
   - This is **not** "all gates PASS", and **not** a complete qualification.
   - No deciding result is REGRESSION or FAIL, so nothing blocks the rc
     under plan section 8.
   - Four deciding results are inconclusive (one UNRESOLVED, three
     INCONCLUSIVE). The maintainer accepts them with the dispositions of
     section 4, recorded next to the verdicts, not in place of them.
   - Q3 of the feeder protocol is FAIL. The maintainer accepts it as a known
     limit with the documented operational envelope of section 4.
   - Two requirements (E6) are not qualified. The maintainer accepts them,
     separately, as unqualified requirements for 1.0, with no performance
     claim.
   - Every original classification, interval and threshold stands as
     measured. Nothing was converted into PASS, nothing was measured again,
     and no v0.9.0 acceptance was inherited.

This file is the single decision record for v1.0.0. `PROTOCOL.md`,
`MATRIX.json` and `FREEZE.json` (revision 1, freeze commit `115a9524`) are
unchanged. The analyses are in `analysis/attempt1/` (commands in
`ANALYSIS-COMMANDS.txt`, checksums in `analysis-sha256.txt`).

## 1. What was measured

| | |
|---|---|
| Candidate | knotrel `0c49b2a689ef548f53581c487edecd2ecc63b2df` (1.0.0-rc.1) |
| Deciding reference | published knotrel v0.9.0, tag `v0.9.0` = `223f04c10b0af663b54e269e0970ee10ac1dc6b2` (A, R, Rmem, M_reg, T5 arm B, Q5) |
| Tooling and probes | knotrel-benchmarks freeze commit `115a9524438ae5cc9d06cb7d2142dd184e2e45b9` (revision 1, tooling `f11c97c`); reference probes at `53c50e96` (knotrel 0.9.0), same probe source |
| Plan | knotrel `docs/releases/v1.0.0-qualification-plan.md` at `0c1da1a`, approved 2026-11-23: perimeter A, B4, C, R, Rmem, M_reg, Q (block D excluded); core rule different, so B1–B3, B5 and T5 added; A at fixed n = 24; thresholds unchanged |
| Host | Apple M3 (4P+4E), 16 GB, macOS 26.5.2, rustc 1.100.0, AC power. Server, PostgreSQL 18.7 (`18.7-alpine@sha256:ff64c9e3…`) and load generator on the same machine |
| Attempt 1 | 2026-11-23: Part 1 18:31–19:49Z; block Q 20:33–21:01Z |
| Raw evidence | private bundle `v1.0.0-qualification-0c49b2a-attempt1`; checksums of every output file in `analysis/attempt1/campaign-outputs-sha256.txt` (1951 files) and of the 17 binaries in `analysis/attempt1/binaries-sha256.txt` |

## 2. Campaign execution

- **Part 1: CONFORMING.** Every unit valid under the revision-3 policy;
  counts and binaries verified at the end.
  - 891 units, 1 invalidated, 1 readiness wait (5.0 s).
  - 77.6 min of a 105-min budget.
  - The invalidated unit was in block A2. External CPU reached 1.75 cores
    over 10 s (Claude app 1.06 + 0.77, `fseventsd` 0.63): the controller
    session was still open after the launch. The policy invalidated the
    block and restarted it once (its one allowed restart); the restarted
    block completed with every unit valid. No result was read before the
    restart.
- **Block Q: COMPLETE.** All seven candidate cells and the two Q5 reference
  cells, three observations each, in three rounds with alternating order; no
  failed or repeated observation; 27.5 min of a 30-min cap.
- **Integrity.** `shasum -a 256 -c` of the output list (1951 files) and of the
  binaries (17): no mismatch.
- **Core rule.** The attempt's recomputation agrees with the pre-freeze file
  (`core-rule-agreement.json`): outcome different, same per-pair flags.
- **Analysis.** Frozen analyzers and the v1.0.0 wrappers only, each run once
  after both parts ended (`ANALYSIS-COMMANDS.txt`).
- **Launch note.** The first launch from an interactive terminal stopped
  before the runner started: `os.setsid()` refused because the shell made the
  process a process-group leader. Nothing ran and no attempt was consumed;
  the same command, wrapped in a subshell, started the runner. The launcher
  text should use the subshell form (follow-up, no effect on results).
- **Tooling note.** `part1-outcome.json` labels the completed steps of this
  CONFORMING attempt with the reason "no verdict: the attempt did not
  conform". The label is wrong (a follow-up fix in
  `part1_failures_v100q.py`); its `status` is CONFORMING, and no analysis
  reads the label.

## 3. Results

| Experiment | Outcome |
|---|---|
| A (24 pairs per cell, 9 cells) | 8 PASS, **1 UNRESOLVED** (§4 X1) |
| B1–B3 timing (core rule) | 37/37 PASS |
| B4 timing, deciding | 21 PASS, **1 INCONCLUSIVE** (§4 X2) |
| B4 timing, descriptive | 11 PASS, 1 REGRESSION (`import-high`), 1 INCONCLUSIVE (`ops` sparse 100k): disclosures, §5 |
| B4 not equivalent (hub 10k ops, events) | measured, no verdict (§4 E6) |
| B5 memory (core rule) | 2/2 PASS |
| C1 / C2 / C3 | 30/30 / 60/60 / 15/15 PASS |
| C4 RSS | 9 PASS, **6 EXCEEDS_BUDGET** (disclosure, §5) |
| T5 compaction pauses (core rule; arm B = v0.9.0) | 6/6 PASS |
| R | 8 PASS, 1 PASS (IMPROVED), **2 INCONCLUSIVE** (§4 X3, X4) |
| Rmem | 10 cells, 20/20 metrics PASS |
| M_reg | 6/6 PASS |
| Q1, Q2, Q4, Q5 (deciding) | PASS |
| Q3 (classified as measured) | **FAIL** (§4 Q3) |

**T5** (median of the candidate against v0.9.0, with its interval; tolerance
25%):

| Topology | P_max, v0.9.0 → candidate | P_90, v0.9.0 → candidate |
|---|---|---|
| sparse | 15.70 → 15.32 ms, −2.5% [−8.6, +0.8] PASS | 14.31 → 14.25 ms, −0.2% [−1.7, +0.8] PASS |
| ring | 12.67 → 12.59 ms, −1.4% [−3.5, +5.6] PASS | 12.26 → 12.29 ms, +0.3% [−1.2, +1.4] PASS |
| hub | 14.76 → 14.80 ms, −0.0% [−5.3, +2.0] PASS | 14.29 → 14.11 ms, −0.5% [−2.1, +0.6] PASS |

**M_reg** (v0.9.0 → candidate, medians; tolerances 10% throughput, 25% p99):

| Cell | Throughput | p99 |
|---|---|---|
| standalone read95, b1, 4 clients, 10k | 32,809 → 32,846 req/s | 0.26 → 0.26 ms |
| standalone read95, b8, 16 clients, 100k | 349 → 350 req/s | 88.3 → 88.2 ms |
| standalone mixed50, b64, 16 clients, 100k | 51 → 51 req/s | 347.5 → 347.1 ms |
| standalone lifecycle50, b8, 16 clients, 100k | 399 → 399 req/s | 54.0 → 54.4 ms |
| source-managed read100 during import, 100k | 1,016 → 1,006 req/s | 77.5 → 77.7 ms |
| source-managed read100 during events, 100k | 911 → 910 req/s | 53.3 → 51.1 ms |

**Q5** (candidate against v0.9.0 in the same session, medians of three
observations): L1 G100k C=16 query throughput 1,209 → 1,297 req/s (ratio
1.072, ≥ 0.90), p99 79.0 → 80.0 ms (ratio 1.012, ≤ 1.25); C=64 throughput
1,133 → 1,150 req/s (1.014), p99 162.9 → 160.4 ms (0.984). **Q1** (C=16):
marker p99 165 ms ≤ 1000, max 183 ms ≤ 3000. **Q2**: every L1 observation
within its lag and retained-WAL limits. **Q4**: time to ready at C=64 5.7 s
≤ 60 s.

## 4. Maintainer decisions (2026-11-23)

> "Approvo le disposizioni per la qualificazione della v1.0.0, mantenendo
> tutti i verdetti originali [...] Accetto separatamente E6 come requisito
> non qualificato per la 1.0, senza dichiarazioni di prestazione. Confermo
> le altre disclosure."

Each result keeps its classification. The disposition is recorded next to
it.

### X1. A `http_standalone_batch_b256_compact_bfs`: UNRESOLVED, accepted with a disclosure

- Primary metric `window_duration_ns`: v0.9.0 3.350 ms → candidate 3.291 ms;
  interval [−4.2%, +5.1%], within the ±10% tolerance.
- Supporting `request_latency_p99_ns`: [−6.6%, +4.3%], PASS.
- Supporting `sampled_max_rss_bytes`: INCONCLUSIVE, [−7.1%, +22.4%] against
  the 20% tolerance; this makes the cell UNRESOLVED under the v0.4.0 rules.
- Disposition: accepted. The batch success path is unchanged since v0.9.0
  (#126 changes body-read failures only). No claim is made about the RSS of
  this cell; the release notes say so.

### X2. B4 `metrics-ops`, compact-bfs sparse 10k (E3): INCONCLUSIVE, accepted with documentation

- In the measured configuration, enabling metrics increased batch-operation
  time by **5.4%** (median of 12 paired log ratios; ratio of medians +4.6%).
  The interval, **[+1.5%, +6.6%]** (96.14% order-statistic interval, not a
  95% interval), crosses the 6% budget. Outcome **INCONCLUSIVE**.
- Disposition: accepted. Metrics are off by default. The documentation
  states the measurement with the same wording, not as a guaranteed bound.

### X3–X4. R `core-import` sparse and hub 10k: INCONCLUSIVE, accepted with a disclosure

| Cell | v0.9.0 → candidate (median) | Median change | Interval | Tolerance |
|---|---|---|---|---|
| `R-core-import-sparse-10k-20-10` | 0.968 → 0.963 ms | −1.9% | [−19.0%, +18.4%] | ±10% |
| `R-core-import-hub-10k-20-10` | — | −0.7% | [−12.7%, +13.4%] | ±10% |

- The medians are neutral; the intervals are wide for observations of about
  1 ms with 12 pairs. The 100k counterparts are PASS, one PASS (IMPROVED)
  (`R-core-import-sparse-100k-60-30`, −1.4% [−2.5%, −0.1%]).
- Disposition: accepted. No equivalence claim at 10k; the release notes say
  so.

### Q3. Feeder catch-up under query load: FAIL, accepted as a known limit with an envelope

- Rule: L2 G100k, catch-up rate at C=16 ≥ 50% and at C=64 ≥ 25% of the rate
  at C=0. Measured (medians of three observations; the ratios are ratios of
  these medians): C=0 **178,095** events/s; C=16 **31,455** events/s
  (**17.7%**); C=64 **16,675** events/s (**9.4%**). FAIL.
- Comparison: consistent with what was observed in v0.9.0 (17.98% and
  10.15%, v0.9.0 decision record E7). The two campaigns are separate
  sessions; no paired comparison of Q3 between versions was made, so no claim
  of absence of regression is made.
- **Operational envelope** (documented in the feeder documentation and the
  release notes):
  - Measured on one Apple M3 with the server, PostgreSQL 18.7 and the load
    generator on the same machine, graph G100k, 0, 16 and 64 concurrent query
    clients.
  - Catch-up rates as above. A backlog of 94,604 events reached `ready` in
    0.53 s (C=0), 3.0 s (C=16) and 5.7 s (C=64), medians.
  - `backlog / rate` is an estimate of catch-up time under the measured
    conditions, not a guarantee on the time to reach `ready`.
  - 0 feeder refusals were observed at the load levels tested.
  - Not qualified: larger graphs, more than 64 concurrent clients, other
    hardware or a separate database host.
- Disposition: accepted as a known limit for 1.0. Q3 does not block the rc
  under plan section 8; it required this disposition and envelope. R2 (the
  two-Mac diagnosis) is separate and does not change Q3.

### E6. B4 `ops` and `events`, compact-bfs hub 10k: unqualified requirements, accepted separately

- No equivalent reference exists for these two requirements; they ran inside
  B4, get no verdict, and are not qualified.
- Disposition: accepted separately as unqualified requirements for 1.0, with
  **no performance claim**. An equivalent reference design is a 1.x activity
  (knotrel backlog). The v0.9.0 acceptance (E6 there) was not inherited.

## 5. Disclosures (kept visible, not converted, no disposition)

- **C4 RSS: EXCEEDS_BUDGET ×6**: `C-rss-lifecycle-compact-bfs` sparse fresh
  1k, 10k and 100k; ring fresh 100k; hub fresh 100k; hub same 100k.
- **B4 `import-high`, compact-bfs sparse 10k: descriptive REGRESSION**,
  +402% (median; interval [+393%, +419%], tolerance 100%), within the
  candidate build (lifecycle against its reference arm). v0.9.0: +400%.
- **B4 `ops`, compact-bfs sparse 100k: descriptive INCONCLUSIVE**, +19.9%
  (interval [+17.4%, +25.1%], tolerance 25%), within the candidate build.
  v0.9.0: PASS at +20.7%.

The maintainer confirmed these disclosures. They are named in the release
notes with their numbers.

## 6. Applicability to the release commits

The rc and 1.0 commits must equal the candidate `0c49b2a` in `crates/`,
`Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml` apart from the version
fields, with an identical `__TEXT,__text` of the `knotrel-server` release
build (FREEZE.json, `candidate.note`). On 2026-11-23 knotrel `main` equals
the candidate in those paths.

**Addendum, 2026-11-24: transfer to 1.0.0 under a waiver.** The maintainer
decided to release 1.0.0 directly, without publishing a release candidate.
Changing only the version from `1.0.0-rc.1` to `1.0.0` changes
`__TEXT,__text` of the `knotrel-server` release build (45,427 of 596,048
instructions; a control build of `main` at version `1.0.0-rc.1` is identical
to the candidate). The maintainer waived the identity requirement for this
step only, after verifying that the delta is limited to the four version
lines in `crates/`, `Cargo.toml`, `Cargo.lock` and `rust-toolchain.toml`, with
the same resolved dependencies and build configuration (knotrel
`docs/releases/v1.0.0-text-identity-waiver.md`). This decision applies to
1.0.0 unchanged, with every verdict, disposition, exception and limitation
above. The campaign was not repeated; binary identity with the measured build
and a new measurement of 1.0.0 are not claimed.

## 7. Not claimed

- No complete qualification, and no "all gates PASS".
- No RSS claim for A `http_standalone_batch_b256`; no 10k equivalence for R
  `core-import`; no bound on the metrics cost beyond the measurement in X2.
- No performance claim for the two E6 requirements.
- No catch-up guarantee outside the Q3 envelope, and no claim that Q3 did not
  regress.
- No result on hardware other than the measurement host.
- This decision authorizes no tag and no publication; the 1.0.0 publication
  was authorized separately by the maintainer on 2026-11-24.
