# Knotrel v0.7.0 vs v0.6.0 — release performance comparison (re-qualification)

This is the per-release comparison the knotrel release procedure requires. It
comes from the frozen v0.7.0 re-qualification
([protocol](PROTOCOL.md), [matrix](MATRIX.json), freeze records
[FREEZE.json](FREEZE.json), [FREEZE-A1.json](FREEZE-A1.json),
[FREEZE-A2.json](FREEZE-A2.json), [FREEZE-A3.json](FREEZE-A3.json)
revision 2). It supersedes the statistical results of the first v0.7.0
campaign ([`../v0.7.0-qualification/COMPARISON-v0.6.0-v0.7.0.md`](../v0.7.0-qualification/COMPARISON-v0.6.0-v0.7.0.md)),
whose collection was non-conforming.

The v0.7.0 release notes are the authoritative product statement. Maintainer
decisions on the results below are recorded there, not here. No maintainer
waiver or acceptance from v0.6.0 or earlier applies, and none from the first
v0.7.0 campaign: every result was measured again and is reported as measured.

**Stato: qualificazione non conforme, decisione pendente.**
- The campaign is **experimentally CONFORMING** (§2).
- The qualification does **not** pass unconditionally: §9 lists the results
  that are not PASS. None is waived, accepted or dispositioned here. Each
  awaits the maintainer's decision.
- Independent review: pending (`analysis/INDEPENDENT-REVIEW.md` will record
  it).

This report keeps two things separate, per cell:
- **Statistical result:** what the frozen analyzers computed from the raw
  data. Every analysis reproduces byte for byte from the raw data with the
  frozen tooling (§1).
- **Experimental conformance:** whether the data were collected under the
  frozen protocol (§2).

## Summary

**Experimental conformance: CONFORMING** (attempt a3-3, the first conforming
attempt of series a3, final by rule).
- Gate: zero violations, zero HID resets, every one of 925 measured children
  gated before and after it; gated = collected for every experiment.
- Per cell: 201 of 201 cells CONFORMING
  ([`conformance/CELL-CONFORMANCE.md`](conformance/CELL-CONFORMANCE.md)).
- Interference (disclosure only, §10.3): 11 of 201 cells "read with caution",
  all of them only through the 0.01 s resolution of `ps` CPU times on
  children shorter than 0.04 s. Background CPU was zero in every one of 3,905
  monitor samples ([`conformance/INTERFERENCE.md`](conformance/INTERFERENCE.md)).

**Statistical results**

| Experiment | Result |
|---|---|
| A, lifecycle off vs v0.6.0 (9 cells) | 9 PASS |
| R, lifecycle on vs v0.6.0 (11 cells) | 11 PASS, 3 of them IMPROVED (HTTP import −17% to −20%) |
| Rmem (10 cells) | 10 PASS; allocator byte counts identical between the arms |
| M_reg, contention vs v0.6.0 (6 cells) | 6 PASS; read95 batch 8 client p99 +6.41% [+0.21, +10.09] |
| B/C timing (61 cells) | 58 PASS, **1 REGRESSION, 2 INCONCLUSIVE** |
| B5 memory (2) / C1, C2 | PASS / PASS |
| C3 heap growth (15) | 12 PASS, **3 FAIL** |
| C4 RSS (15, disclosure) | 9 PASS, **6 EXCEEDS_BUDGET** |
| M_desc (descriptive, 162 rows) | 161 VALID, **1 INVALID**; M5 rule (i) in 17 of 32 |

## 1. Identities

| | Reference (published v0.6.0) | Candidate (v0.7.0) |
|---|---|---|
| knotrel commit | `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538` (signed tag `v0.6.0`) | `e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc` |
| `knotrel-server` sha256 | `feb0f70341772477a27751be601da62f76cf701866cdaea96c5b49894c25f90b` | `ea895dfe36eb2bb1ef39b2b4968aa23a24232cec14347f4efc2bb2aae4c74e30` |
| A core harness (`df635a1e`, derived lockfile) sha256 | `75f211da0baddfc20628c21d15d06740b19363355ab00db7aead5a6e8a3a4390` | `170750f0d3054da4b4783dcbd4627485ca9d628f61f086c4c628dfb3c9555b74` |
| `release-cells` sha256 | `581c5af4e60b2d99c6be63395eae0c4deb836361338a22f7886519d453723cd1` | `e4fc059b0c1fa396792f5fc49f988f868955b41253bcf512f25f16905e3f3e4d` |
| `memory-peak` sha256 | `19217e5da07913c3ccef056e0486ecf02f73baaa9d088eeca14e9a97c55fd701` | `5767dfcbbe1c5b39229f438c3d158a1e5b993aeee2f55377763f2e68277a8e97` |

- **Candidate content:** unchanged from the first campaign. 0.7.4a, the
  shared read lock for query-only requests; 0.7.4b, `sonic-rs` import parsing
  with fallback to the v0.6.0 parsers. `knotrel-core` is byte-identical to
  v0.6.0.
- **Shared binaries:** `measure_e2e` `e21d2c41…`; `contention-probe`
  revision 2 `e7d0b4b6757b5941eef156eed9f3073d3581879dff9ab78c2aadee8a8058a34d`
  (identical to the first campaign and the v0.6.0 M supplement build);
  candidate lifecycle probes `core-lifecycle` `c21e2081…`, count-alloc
  `core-lifecycle` `caf59ffd…`, `http-lifecycle` `1912237b…`. Full list:
  [`analysis/binaries-sha256.txt`](analysis/binaries-sha256.txt).
- **Executed code vs the first campaign** (`__TEXT,__text`, information only,
  [`analysis/text-section-compare.txt`](analysis/text-section-compare.txt)):
  both servers and the contention probe are identical; both `release-cells`
  differ, as they do between every two builds in separate directories.
- **Tooling:** knotrel-benchmarks `087526ad36aa0f94513f41c3318287556c8f0dd2`,
  freeze commit `f73c2bd524e7dd6323ed5ee49017fb9e6840be6c` (FREEZE-A3
  revision 2, which adds only `FREEZE-A3.json`). Reference probes use the
  v0.6.0 probe lockfile (tag `v0.6.0`, `bddef0f3`); derivations recorded as
  diffs in the evidence.
- **Host and toolchain:** Apple M3, macOS 26.5.2; rustc 1.100.0, release
  profile, `--locked --offline`. Every child ran on AC power with no
  recorded thermal or performance warning; no child exited non-zero.
- **1-minute load average** (disclosure; no load limit exists in the rules):
  2.52 at launch; B/C 1.45–2.91; R 2.00–2.49; Rmem 2.49–2.64; M_desc
  2.64–20.11 and M_reg 2.18–16.06, from their own 16- and 64-client
  configurations.
- **Campaign:** evidence `v0.7.0-requalification-e75ff6a-a3-attempt3`,
  2026-11-18 20:11:42Z (grace) → 21:22:16Z, 70.6 min against the 240 min cap:
  quiet period 5.0, A main 14.2, A extension 13.3 (cells
  `http_standalone_batch_b64` and `b8`), B/C 7.7, R 2.4, Rmem 0.2, M_desc
  11.7, M_reg 13.6 ([`analysis/chain-steps.txt`](analysis/chain-steps.txt)).
- **Reproduction:** every analysis was run twice from the raw data with the
  frozen clone at `f73c2bd5`; the outputs are byte-identical. Checksums:
  [`analysis/analysis-sha256.txt`](analysis/analysis-sha256.txt) (archived
  outputs), [`analysis/inputs-sha256.txt`](analysis/inputs-sha256.txt) (plans,
  run logs, gate records), [`analysis/outputs-sha256.txt`](analysis/outputs-sha256.txt)
  (every raw output, written by the chain).

## 2. Experimental conformance

**Rule** (MATRIX `conformance`, amendments 1–3, PROTOCOL.md §§7–10): from the
start of the quiet period to the end of the chain, nothing outside the
allow-list runs and no user input occurs; every measured child is gated by
the allow-list monitor before and after it. Under amendment 3, processes the
monitor cannot attribute to the campaign, the system or the controller are
classed `background` and recorded, not forbidden; deny-listed programs,
Claude processes, interpreters, new Terminal descendants and foreground apps
other than Finder and Terminal stay forbidden.

**Attempt a3-3: CONFORMING** ([`conformance/CONFORMANCE.txt`](conformance/CONFORMANCE.txt)).
- Precheck in the launch environment passed, including every collector dry
  run ([`conformance/precheck-launch-env.txt`](conformance/precheck-launch-env.txt)).
- Quiesce and launcher audit: audit passed with no findings (recorded mode)
  ([`conformance/launcher-audit.json`](conformance/launcher-audit.json));
  restore OK after the chain, verified again by hand
  ([`conformance/quiesce-restore-result.json`](conformance/quiesce-restore-result.json)).
- Monitor alive throughout with no gap; violations 0; HID resets 0 (HID idle
  4,261 s at the end); foreground failures 0.
- Quiet period conforming; 925 gated children, all conforming, gated =
  collected for A 264, B/C 127, R 308, Rmem 20, M_desc 38, M_reg 168
  ([`conformance/end-checks.txt`](conformance/end-checks.txt)).
- Git state of the workspace and `~/.claude/projects` unchanged.

**Per cell:** 201 of 201 CONFORMING: A 9, B/C 127 (one gated child per
run-log cell), R 11, Rmem 10, M_desc 38 server processes, M_reg 6
([`conformance/CELL-CONFORMANCE.md`](conformance/CELL-CONFORMANCE.md)).

**Interference marking** (PROTOCOL.md §10.3, disclosure only, no
invalidation; [`conformance/INTERFERENCE.md`](conformance/INTERFERENCE.md)).
- Code written after the freeze as §10.3 specifies
  (`scripts/report_v070r_interference.py`) and reviewed independently before
  the analysis. The review found two blockers (R and M_reg cells split in
  two; a floating-point artefact marking children at exactly 25%); both were
  fixed and re-verified.
- Background CPU: zero in all 3,905 monitor samples; no child has background
  CPU above 2.2% of one core. 552 children are shorter than the sampling
  interval and have no sample.
- 11 cells are marked "read with caution": A `core_sustained_churn_10k`
  `compact-bfs` (8 of 24 children) and `compact-workspace` (10 of 24); eight
  B/C cells (B5 memory hub 100k and seven C cells at 1k); Rmem
  `import-core-60-30` (2 of 2). In every marked child the measure over the
  limit is **baseline** CPU (the Terminal lineage), exactly one or two 0.01 s
  `ps` ticks inside a child of 0.032–0.040 s. The marking follows §10.3
  unchanged; this resolution effect is disclosed, not corrected.

**Cross-check (deviation, disclosed).** PROTOCOL.md §5 step 4 and
RERUN-PROPOSAL.md name "the conformance cross-check", the first campaign's
`scripts/analyze_v070_conformance.py`. It cannot be run on this campaign: it
reads the first campaign's monitor format (top-five records by `kind`/`utc`),
and it classes Terminal.app as a user application, while amendment 2 makes
Terminal.app the controller. Per-cell conformance is taken instead from the
gate's own per-child decisions (`scripts/report_v070r_cell_conformance.py`),
which check the full process table against the allow-list before and after
every child, a stronger basis than top-five samples. The maintainer approved
writing the report on this basis (2026-11-19).

**Every directory of the re-qualification** (all counted, all reported; none
selected by its result):

| Directory | Freeze | Result | Cause |
|---|---|---|---|
| `v0.7.0-requalification-e75ff6a` (attempt 1) | FREEZE | NONCONFORMING: quiet period | user input (HID reset) |
| `…-e75ff6a-attempt2` | FREEZE | NONCONFORMING: gate stop after A-extension | WhatsApp notification extension (57 violations) |
| `…-e75ff6a-attempt3` | FREEZE | NONCONFORMING: gate stop after A-main | GoogleUpdater (74 violations) |
| `…-a1-roundtrip` | (tooling test) | not a measurement | root-owned plist round trip of the quiesce (PROTOCOL §8) |
| `…-a1-soak1` | FREEZE-A1 | SOAK NONCONFORMING | `git` spawned by the Claude Code CLI (1 violation); series a1 closed with zero attempts |
| `…-a2-soak2.unlaunched-e57106bc` | FREEZE-A2 r1 | never launched | superseded by the audit-race fix (§9.10) |
| `…-a2-soak2.unlaunched-58ed921a` | FREEZE-A2 r2 | precheck refused, nothing started | lineage correction (§9.11) |
| `…-a2-soak2` | FREEZE-A2 r3 | SOAK NONCONFORMING | Safari `CacheDeleteExtension` with no resolvable path (1 violation); series a2 closed with zero attempts |
| `…-e75ff6a-a3-attempt1` | FREEZE-A3 r1 | NONCONFORMING: quiet period | HID input during the quiet period; zero process violations |
| `…-e75ff6a-a3-attempt2` | FREEZE-A3 r1 | FAILED: B/C (no verdict) | `rustc` missing from the launch PATH (§10.7); gate clean through A |
| `…-e75ff6a-a3-attempt3` | FREEZE-A3 r2 | **CONFORMING** | this report |

The A outputs of the exhausted attempts 2 and 3 are checksummed in
[`EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256`](EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256). The A outputs of a3-2 are not used:
the attempt has no verdict.

## 3. Lifecycle off: existing behavior against v0.6.0 (experiment A, v0.4.0 rules)

| Cell | Outcome | Primary (B → C, median) | Paired change [interval] (pairs) | Supporting metrics | First campaign (non-conforming) |
|---|---|---|---|---|---|
| core sparse traversal, `compact-bfs` | PASS | 4.473 → 4.466 ms | −0.27% [−1.83, +2.76] (12) | `connected` p99 +1.81% PASS; RSS PASS | PASS +2.96% |
| core sparse traversal, `compact-workspace` | PASS | 5.687 → 5.770 ms | +0.39% [−8.22, +9.97] (12) | `connected` p99 +7.53% [−8.98, +12.91] PASS; RSS PASS | PASS −3.82% |
| core sustained churn, `compact-bfs` | PASS ¹ | 0.6685 → 0.6692 ms | +0.68% [−0.17, +1.44] (12) | `connected` p99 +1.24% [−1.63, +19.60] PASS; RSS PASS | PASS +0.54% |
| core sustained churn, `compact-workspace` | PASS ¹ | 0.4698 → 0.4728 ms | +0.40% [−0.28, +1.06] (12) | PASS | PASS +0.43% |
| HTTP startup to ready | PASS | 3.992 → 3.877 ms | −3.10% [−5.88, +0.57] (12) | query p99 −0.92% PASS; RSS +2.25% [+1.04, +3.20] PASS | INCONCLUSIVE_DISCLOSED |
| HTTP batch 1 | PASS | window 174.3 → 175.5 ms | +1.75% [−0.64, +3.36] (12) | request p99 +0.81% [−10.14, +9.34] PASS; RSS +1.70% PASS | UNRESOLVED |
| HTTP batch 8 | PASS | 33.73 → 33.82 ms | +2.80% [−2.11, +5.56] (24) | p99 −0.20% PASS; RSS +1.53% [+0.87, +2.19] PASS | PASS |
| HTTP batch 64 | PASS | 6.702 → 6.797 ms | +2.30% [−3.45, +7.39] (24) | p99 +0.22% PASS; RSS −13.98% [−16.86, +2.53] PASS | PASS |
| HTTP batch 256 | PASS | 2.886 → 2.887 ms | +0.91% [−1.33, +4.09] (12) | p99 −0.76% PASS; RSS −12.66% [−19.31, +8.60] PASS | PASS |

¹ Interference marking "read with caution" (§2), baseline CPU at `ps`
resolution only.

**Summary:** 9 PASS, no REGRESSION, no INCONCLUSIVE. Two cells took the
12-pair extension (batch 8, batch 64). `link_p99_ns` and `cut_p99_ns` are
report-only (in the analysis file). HTTP startup (INCONCLUSIVE_DISCLOSED in
v0.6.0 and the first campaign) and batch-1 request p99 (UNRESOLVED in v0.5.0,
v0.6.0 and the first campaign) PASS here, with narrower intervals.

**Not covered by A:** the experimental `ett`/`hdt` engines, the feeder and
import paths (except through startup), metrics-enabled operation. A runs one
client, so it does not exercise the shared read lock under contention.

## 4. Lifecycle on: release-to-release cells (experiment R, tolerance 10%)

| Cell | Outcome | v0.6.0 → v0.7.0 (median) | Paired change [interval] | First campaign |
|---|---|---|---|---|
| core import, sparse 100k, 20% inactive / 10% disabled | PASS | 14.02 → 13.93 ms | −0.29% [−3.47, +8.23] | PASS |
| core import, sparse 100k, 60/30 | PASS | 11.75 → 11.72 ms | +0.41% [−2.49, +3.87] | PASS |
| core import, sparse 10k, 20/10 | PASS | 1.005 → 1.017 ms | +1.00% [−4.39, +6.10] | PASS (IMPROVED) |
| core import, hub 10k, 20/10 | PASS | 0.797 → 0.822 ms | +3.96% [−2.70, +7.13] | INCONCLUSIVE |
| HTTP import, sparse 100k, 20/10 | **PASS (IMPROVED)** | 28.40 → 23.59 ms | −16.88% [−18.56, −15.22] | PASS (IMPROVED) |
| HTTP import, sparse 100k, 60/30 | **PASS (IMPROVED)** | 28.57 → 23.65 ms | −17.20% [−19.48, −16.50] | PASS (IMPROVED) |
| HTTP import, sparse 10k, 20/10 | **PASS (IMPROVED)** | 2.487 → 2.009 ms | −19.53% [−22.29, −18.32] | PASS (IMPROVED) |
| fresh-ID churn, sparse 100k (30 cycles × 5%) | PASS | 206.4 → 204.2 ms | −1.56% [−3.28, +0.55] | PASS |
| fresh-ID churn, hub 100k | PASS | 214.6 → 218.3 ms | +1.54% [−0.29, +3.89] | PASS |
| same-ID churn, sparse 100k | PASS | 114.9 → 112.2 ms | −1.41% [−3.75, +0.37] | PASS |
| toggle churn, sparse 100k | PASS | 83.70 → 84.29 ms | +0.21% [−4.73, +4.00] | INCONCLUSIVE |

The two cells INCONCLUSIVE in the first campaign (core import hub 10k,
toggle churn) PASS here. Both run `knotrel-core` code only, which is
byte-identical between the arms. Core import sparse 10k is no longer
IMPROVED: its interval now includes zero.

## 5. Lifecycle on: memory (Rmem; allocator byte counts, deterministic, tolerance 20%)

Every Rmem metric is byte-for-byte identical between the arms: change 0.0%,
PASS in all 10 cells.

| Run (100k nodes, MiB) | v0.6.0 = v0.7.0 | Outcome |
|---|---|---|
| HTTP create import 20/10: peak live heap / transient over final | 32.6 / 9.5 | PASS |
| HTTP create import 60/30: peak / transient | 31.2 / 9.5 | PASS |
| HTTP replace import 20/10: peak / transient | 50.4 / 27.4 | PASS |
| core import 20/10: peak / live after | 25.8 / 24.2 | PASS |
| core import 60/30: peak / live after ¹ | 24.4 / 22.9 | PASS |
| fresh churn sparse / ring / hub: net max live | 33.5 / 30.2 / 33.2 | PASS |
| fresh churn sparse / ring / hub: compaction peak | 40.7 / 36.9 / 40.3 | PASS |
| same-ID churn sparse: net max / peak | 23.3 / 27.0 | PASS |
| toggle churn sparse: net max / peak | 23.0 / 23.0 | PASS |

¹ Interference marking (§2), baseline CPU at `ps` resolution only; the
metric is a deterministic byte count.

The HTTP import counts are 1–6 bytes below the first campaign's, in both arms
alike; the core import and churn counts are identical to it.
These are live requested-heap counts, not RSS.

## 6. Lifecycle cost on the candidate (B/C, v0.5.0 protocol unchanged)

Not release-to-release comparisons: each cell compares the candidate with a
semantically equivalent reference built from the same source and run in the
same process. Full table: [`analysis/BC-analysis.md`](analysis/BC-analysis.md).

| | First campaign (non-conforming) | Re-qualification |
|---|---|---|
| B1–B4 timing (61 cells) | 58 PASS, 1 REGRESSION, 2 INCONCLUSIVE | **58 PASS, 1 REGRESSION, 2 INCONCLUSIVE** (same cells) |
| B5 memory (budget 3×) | 2.45×, 2.44× PASS | 2.45×, 2.44× PASS ¹ (hub) |
| C1 engine slots / C2 counts | all PASS | all PASS (at most 95,000 retired slots at 100k) |
| C3 heap growth | 12 PASS, 3 FAIL | 12 PASS, **3 FAIL** (same cells, identical values) |
| C4 RSS (disclosure) | 9 PASS, 6 EXCEEDS_BUDGET | 9 PASS, **6 EXCEEDS_BUDGET** (same cells) |

¹ Eight B/C cells carry the interference marking (§2): B5 hub 100k and seven
C cells at 1k, baseline CPU at `ps` resolution only.

Cells that are not PASS, or close to their tolerance:

| Cell | Reference → candidate | Change [interval] | Tolerance | Outcome | First campaign |
|---|---|---|---|---|---|
| `import-high` sparse 10k (60/30) | 1.666 → 8.668 ms | +413.26% [+375.24, +446.79] | 100% | **REGRESSION** | REGRESSION +402.09% |
| `metrics-ops` sparse 10k | 2.743 → 2.900 ms | +5.65% [+2.93, +8.58] | 6% | **INCONCLUSIVE** | INCONCLUSIVE +5.13% |
| `ops` sparse 100k | 3.796 → 4.613 ms | +23.76% [+18.05, +26.72] | 25% | **INCONCLUSIVE** | INCONCLUSIVE +20.71% |
| `ops` sparse 10k | 2.446 → 2.894 ms | +18.78% [+16.30, +21.71] | 25% | PASS | PASS +21.68% |
| `import` sparse 100k | 12.77 → 24.06 ms | +88.14% [+85.12, +89.90] | 100% | PASS | PASS +88.11% |

- **`ops` sparse 100k:** both arms run in process on the candidate server
  (lifecycle on vs off), both with mutation-only batches that take the graph
  lock exclusively. The median is 3 points above the first campaign's; the
  upper bound, +26.72%, exceeds the 25% tolerance while the lower bound,
  +18.05%, is above zero.
- **`import` and `import-high`:** both arms parse with the candidate's
  parser; the reference imports only the effective graph.

C3 fresh-ID churn at 100k (rule: late/early ≤ 1.25 and 30-cycle growth ≤ 0.10
of the early mean); values identical to the first campaign and to v0.6.0:

| Topology | Net heap first → max → last (MiB) | Late/early | 30-cycle growth | C3 |
|---|---|---|---|---|
| sparse | 23.0 → 33.5 → 31.1 | 0.927 | +0.103 | **FAIL** |
| ring | 19.4 → 30.2 → 28.4 | 0.950 | +0.172 | **FAIL** |
| hub | 22.5 → 33.2 → 30.8 | 0.927 | +0.119 | **FAIL** |

C4 EXCEEDS_BUDGET (RSS, allocator retention, disclosure by rule): lifecycle
sparse fresh 1k, 10k, 100k; ring fresh 100k; hub fresh 100k; hub same 100k.

## 7. Contention (M_reg against v0.6.0; tolerances: throughput 10%, p99 25%)

Probe revision 2, fresh server per observation, 2 warmup + 12 pairs. Every
analyzed observation is VALID under the declared rule.

| Cell (100k nodes unless noted, 16 closed-loop clients) | Throughput v0.6.0 → v0.7.0 | Change [interval] | Client p99 v0.6.0 → v0.7.0 | Change [interval] | Outcome |
|---|---|---|---|---|---|
| standalone, lifecycle off, read95, batch 8 | 208.5 → 348.0 req/s | −40.00% [−40.21, −39.44] (IMPROVED) | 91.2 → 97.3 ms | **+6.41% [+0.21, +10.09]** | PASS |
| standalone, off, mixed50, batch 64 | 49.5 → 49.7 req/s | +0.00% [−1.34, +1.35] | 361.7 → 356.8 ms | −0.30% [−2.56, +2.18] | PASS |
| standalone, off, read95, batch 1, 4 clients, 10k | 15,350 → 31,140 req/s | −50.69% [−50.99, −50.27] (IMPROVED) | 0.527 → 0.278 ms | −47.56% [−47.77, −46.68] (IMPROVED) | PASS |
| standalone, lifecycle on, lifecycle50, batch 8 | 384.8 → 386.0 req/s | −0.17% [−0.95, +0.87] | 57.15 → 56.43 ms | −1.43% [−4.57, +2.30] | PASS |
| source-managed, off, read100, batch 8, replace import every second | 198.9 → 943.0 req/s | −78.94% [−79.16, −78.65] (IMPROVED) | 94.1 → 85.3 ms | −9.94% [−10.73, −7.40] (IMPROVED) | PASS |
| source-managed, on, read100, batch 8, feeder catch-up | 204.7 → 844.7 req/s | −75.77% [−76.38, −75.40] (IMPROVED) | 90.6 → 59.6 ms | −34.15% [−43.17, −31.13] (IMPROVED) | PASS |

Throughput changes are inverted by the frozen analyzer (for
higher-is-better metrics it compares candidate against reference): negative
means v0.7.0 is faster.

- **read95 batch 8.** About 34% of 8-operation read95 batches contain a
  mutation and still take the lock exclusively. Throughput rises 67%. Client
  p99 is +6.41% [+0.21, +10.09]: a confirmed small increase (the interval is
  entirely above zero), within the 25% tolerance. The first campaign showed
  the same, +5.38% [+0.16, +11.16].
- **mixed50 and lifecycle50** batches almost always contain a mutation and
  are unchanged.

## 8. Contention profile of the candidate (M_desc, descriptive)

162 rows (156 closed-loop configurations, 6 open-loop) across 38 fresh server
processes. 161 are VALID under the declared probe rule; **one is INVALID**.
Each figure is one measured window of the candidate only; no comparison with
v0.6.0 is made here (the available v0.6.0 profiles are not comparable
baselines, as stated in the first campaign's §7). Full data:
[`analysis/Mdesc-analysis.json`](analysis/Mdesc-analysis.json).

- **INVALID: `M-source-on-100k`, `read100-b8-c64-import`** (source-managed,
  lifecycle on, 64 clients, replacement import every second). All 6
  background imports in the window failed with `412 precondition_failed`,
  one stats request returned 503, and no import completed (invalid reasons:
  "background failures=6", "background completed=0"). The queries in the same
  window ran (788.6 req/s). In the first campaign the same configuration
  completed 6 of 6 imports (p50 761 ms). In this campaign the 4- and
  16-client import configurations of the same server completed 5 of 5
  (p50 67 / 273 ms). The cause is not established.
- **M5 rule (i):** holds in **17 of 32** saturated read-heavy configurations
  (first campaign: 16 of 32). Configuration list in the analysis file.

## 9. Results that are not PASS: impact, evidence and options

Statistical results of a CONFORMING campaign. No option below has been
applied; none is recommended over another here; every item awaits the
maintainer's decision. No decision from an earlier release or from the first
v0.7.0 campaign applies.

| # | Result | Impact | Evidence | Options |
|---|---|---|---|---|
| 1 | B4 `import-high` **REGRESSION** +413.26% [+375.24, +446.79] (t = 100%) | Full-topology import with 60/30 flags costs about 5× an effective-graph-only reference | Recurs from v0.5.0 (+444.8%), v0.6.0 (+419.9%) and the first campaign (+402.1%). The reference parses only the effective graph | (a) accept with disclosure as inherent to the full-topology contract; (b) define a different reference or tolerance for future releases (a product decision, made before measuring) |
| 2 | C3 heap growth **FAIL** ×3 (fresh-ID churn, 100k) | Heap grows over 30 cycles before compaction | Identical values to v0.6.0 and the first campaign (`knotrel-core` unchanged); growth +0.103 / +0.172 / +0.119 against 0.10 | (a) accept with disclosure; (b) pre-size the catalog and re-measure (B5 cost); (c) a longer-window resource rule for future releases (product decision, made before measuring) |
| 3 | B4 `ops` sparse 100k **INCONCLUSIVE** +23.76% [+18.05, +26.72] (t = 25%) | Lifecycle-on batch overhead at 100k may exceed 25%; median about +24% | INCONCLUSIVE in the first campaign too (+20.71%); v0.6.0 PASS +19.45%. Same binary, both arms exclusive-lock mutation batches | (a) accept with disclosure; (b) a declared re-measurement of this cell; (c) a targeted overhead diagnostic |
| 4 | B4 `metrics-ops` sparse 10k **INCONCLUSIVE** +5.65% [+2.93, +8.58] (t = 6%) | Metrics overhead on lifecycle batches may exceed the 6% budget | Recurs from v0.5.0, v0.6.0 and the first campaign. Recording logic unchanged; `metrics.rs` only times `RwLock` acquisition | (a) accept with disclosure; (b) a targeted overhead diagnostic |
| 5 | C4 RSS **EXCEEDS_BUDGET** 6/15 | Disclosure category by rule (allocator retention), not FAIL | Same cells as the first campaign | Disclose |
| 6 | M_desc **INVALID** row `M-source-on-100k/read100-b8-c64-import`: 6 of 6 background imports `412 precondition_failed`, none completed | Under 64 query clients with lifecycle on, replacement imports in this window were all refused by the precondition check; whether this is a product behavior (for example a version precondition that cannot win against continuous catch-up) or a probe effect is not known | Descriptive experiment, no verdict. New: the first campaign completed 6/6 in the same configuration; 4- and 16-client configurations completed 5/5 here | (a) disclose as an unexplained invalid descriptive row; (b) a diagnostic of import preconditions under feeder catch-up and 64 clients before release; (c) a declared re-measurement of the configuration |
| 7 | M_reg read95 batch 8 client p99 **+6.41% [+0.21, +10.09]** (PASS, interval entirely above zero) | A confirmed small tail-latency increase for mixes of mutation-bearing and query-only batches, within the 25% tolerance | Same direction as the first campaign (+5.38%). Plausible mechanism, not shown: a writer now waits for in-flight shared readers | (a) disclose; (b) a declared paired read95 batch 64 cell in a future collection (scope change, separate decision) |
| 8 | Interference marking: 11 cells "read with caution" | None on the measurements: background CPU zero; baseline only at `ps` resolution | §2; [`conformance/INTERFERENCE.md`](conformance/INTERFERENCE.md) | Disclose (§10.3: no invalidation) |
| 9 | Cross-check deviation (§2) | The named first-campaign script was not run; per-cell conformance comes from the gate | Format and class incompatibility with the re-qualification monitor and amendment 2 | Disclose (maintainer approved the report on this basis) |

## 10. Differences from the frozen plan (declared)

- **Amendments 1–3** (PROTOCOL.md §§8–10) changed the host preparation, the
  controller (Terminal.app, Claude quit) and the class of unattributed
  processes (`background`, recorded). No threshold, seed, statistic,
  analyzer, granularity or experiment changed. FREEZE-A3 revision 2 added
  only the launch-environment check (§10.7).
- **Interference marking** was written after the freeze, as §10.3 required,
  and reviewed before the analysis.
- **Cross-check** replaced as described in §2.

## 11. Coverage and claims

- Results apply to the measured host (Apple M3, ARM64), toolchain,
  configurations and workloads. No general speedup is claimed.
- `sonic-rs` performance on x86-64 is not measured.
- Parser parity rests on the knotrel repository's unit tests (77-case corpus,
  20,000 seeded mutations; bodies `sonic-rs` rejects take the v0.6.0 path).
- The shared read lock helps only requests whose operations are all queries;
  a batch with any mutation takes the graph exclusively (§7).
- CI on Linux, macOS and Windows for the candidate branch is a release gate
  outside this report.
- `cargo deny` license findings and x86-64 performance are open follow-ups,
  not covered here.
