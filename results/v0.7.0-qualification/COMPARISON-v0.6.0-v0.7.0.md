# Knotrel v0.7.0 vs v0.6.0 — release performance comparison

This is the per-release comparison the knotrel release procedure requires. It
comes from the frozen v0.7.0 final qualification
([protocol](PROTOCOL.md), [matrix](MATRIX.json), [freeze record](FREEZE.json)).
The v0.7.0 release notes are the authoritative product statement. Maintainer
decisions on the results below are recorded there, not here. No maintainer
waiver or acceptance from v0.6.0 or earlier applies: every v0.6.0 non-PASS
result was measured again and is reported as measured.

**Status: qualification NOT CONFORMING; maintainer decision pending.**
- The report was independently reviewed
  ([`analysis/INDEPENDENT-REVIEW.md`](analysis/INDEPENDENT-REVIEW.md)), and
  every analysis reproduces byte for byte from the raw data.
- No maintainer decision has been recorded. Nothing here accepts or waives any
  result.

This report keeps two things separate:
- **Statistical result:** what the frozen analyzers computed from the raw
  data. It is unchanged and recorded below.
- **Experimental conformance:** whether the data were collected under the
  frozen protocol.

**Experimental conformance: NONCONFORMING (whole campaign)** (§1, Protocol
conformance).
- **The rule:** the frozen operator rule, "The operator runs nothing else until
  it completes", covers the whole chain. The frozen protocol gives it no
  finer granularity.
- **What happened:**
  - user applications ran throughout the campaign;
  - an interactive burst occurred during M_reg: a disk-image mount, an app
    launch and file dialogs.
- **Cross-check over every measured unit**
  ([`conformance/CONFORMANCE-CROSSCHECK.md`](conformance/CONFORMANCE-CROSSCHECK.md)):
  960 non-conforming, 13 indeterminate, 0 conforming.
- **Consequence:** no verdict or speedup statement of this campaign can be
  proposed for acceptance. One conforming re-collection of the whole campaign
  is proposed in
  [`../v0.7.0-requalification/RERUN-PROPOSAL.md`](../v0.7.0-requalification/RERUN-PROPOSAL.md).
  It is not started.

**Statistical results of this campaign** (recorded, not usable for
acceptance). The qualification would not have passed unconditionally even
under conforming conditions.
- **Contention (M_reg):** all 6 cells PASS statistically, 4 of them with
  intervals entirely below zero.
  - The like-for-like comparison is M_reg: the same revision-2 probe binary
    for both arms, in the same session (§6).
  - read95 batch 8 client p99 +5.38% [+0.16, +11.16].
- **Imports (R, Rmem):**
  - HTTP import −17% to −21%, intervals entirely below zero;
  - allocator byte counts identical.
- **Lifecycle off (A):** 7 PASS, 1 INCONCLUSIVE_DISCLOSED (startup),
  1 UNRESOLVED (batch-1 request p99); no REGRESSION.
- **R:** INCONCLUSIVE for core import hub 10k and toggle churn.
- **B/C:**
  - `import-high` REGRESSION;
  - `metrics-ops` and `ops` sparse 100k INCONCLUSIVE;
  - C3 heap-growth FAIL ×3;
  - C4 RSS EXCEEDS_BUDGET 6/15.
- **M5 rule (i), descriptive:** 16 of 32.

## 1. Identities

| | Reference (published v0.6.0) | Candidate (v0.7.0) |
|---|---|---|
| knotrel commit | `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538` (signed tag `v0.6.0`; crates.io 0.6.0) | `e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc` (branch `feature/v0.7.0-measured-concurrency`) |
| `knotrel-server` (local release build) sha256 | `697ebca0cbfb2afc44175af32a1519c45368c2067550a00f560c472d6597b1e7` | `98aa7d0b54f51297769e53a755804a10f4b8ab1df2ee835f9b673cd052750b48` |
| A core harness (knotrel-benchmarks `df635a1e`, derived lockfile) sha256 | `d9cae8c8c1d3374e1cde703e84c8f02befeb16fb5b1fd9308109753c5915b3df` | `ce85991f56690adadb14b428eace9420e37520234cfd4f02ab8fc6e44cbd0c76` |
| `release-cells` sha256 | `26391ed537b983554ab7c609643dc1319b175364541e878efd9d779002162bf9` | `3310428ea9ae256445d182e36e01295f04e4dafceba1e0e336ae22449fb415fc` |
| `memory-peak` sha256 | `27caf53fe5b4c7f134c6bd070f8ddef006cb4845605e66108d8f9caeedd403c2` | `27e4b8bc5777850ac4e52741a9557c86e62b26d9b5f10569a9d18b6bb448df4b` |

- **Candidate content:** 0.7.4a, the shared read lock for query-only requests.
  0.7.4b, `sonic-rs` import parsing with fallback to the v0.6.0 parsers. The
  `knotrel-core` source is byte-identical to v0.6.0
  (`git diff 5db9ec4 e75ff6a -- crates/knotrel-core` is empty).
- **Shared binaries:**
  - `measure_e2e` (A HTTP driver, from the candidate source): `aa51bf67d4a38fcf613325762dbaca62098614322489465afab89f5771b5bcb4`.
  - `contention-probe` revision 2: `e7d0b4b6757b5941eef156eed9f3073d3581879dff9ab78c2aadee8a8058a34d`, identical to the v0.6.0 M supplement build.
  - Candidate lifecycle probes: `core-lifecycle` `6e3ce90e…`, count-alloc `core-lifecycle` `9da41fcf…`, `http-lifecycle` `ac658cbe…`.
  - Full list: [`analysis/binaries-sha256.txt`](analysis/binaries-sha256.txt).
- **Tooling:**
  - knotrel-benchmarks `82123ae31b202a3f3ce8d0c52ee5a234ad5b0c18`; freeze commit `4c03cf7ba9c764cf27473d41ef3449b71b81bd60`, which adds only `FREEZE.json`.
  - Reference probes are built from the same tooling with the v0.6.0 probe lockfile (knotrel-benchmarks tag `v0.6.0`, `bddef0f3`); the lockfile derivations are recorded as diffs.
- **Host and toolchain:**
  - Apple M3, macOS 26.5.2; rustc 1.100.0, release profile, `--locked --offline`.
  - All 661 collected children, plus every A session check, ran on AC power with no recorded thermal or performance warning. No child exited non-zero.
  - 1-minute load average:
    - 1.51 at launch;
    - the six A session pre-checks: 1.28–2.36;
    - B/C 1.34–2.68, R 2.53–3.10, Rmem 2.49–2.53.
  - M_desc children started at 2.49–24.0, M_reg children at 2.26–22.93.
    - M_desc's high values follow its own 64-client configurations.
    - M_reg's maximum came in its source-managed import cell (M_reg median 6.1).
  - No load limit exists in the rules; this is disclosure, not a validity condition.
- **Campaign:** 2026-11-17T19:22:21Z → 20:22:30Z, 60.2 min against an 86 min estimate and a 240 min cap. A main 13.4 min, A extension 13.3, B/C 7.3, R 1.5, Rmem 0.1, M_desc 11.6, M_reg 13.0.
- **Activity gate (protocol §3.4):**
  - `host_activity_monitor.py --check` ran before the chain and before every R, Rmem and M child, and never stopped the chain. Per-child results are not logged; "passed" is inferred from the absence of a stop record.
  - A and B/C children are not gated (see the wording block below).
  - A continuous monitor ran from 19:22:21Z to 20:22:27Z. It checked the full process table 14,620 times against the gate pattern (`git`, `cargo`, `rustc`, Antigravity, Visual Studio Code) with no match. It also recorded the five busiest processes about once a second (3,246 samples): `logs/activity-monitor.jsonl` in the evidence.

**Protocol conformance: not met.**

The frozen `run_final_chain.sh` says: "The operator runs nothing else until it
completes." The monitor's top-five samples show non-campaign processes above
30% of a core in every experiment except Rmem. Figures are `ps` %cpu, a
decaying average, summed per application per sample. The monitor sees only
the five busiest processes, so lighter activity is not recorded.

| Experiment | Non-campaign processes above 30% (samples, highest) |
|---|---|
| A main (766 samples) | WindowServer 421, 56%; Google Chrome 39, 219%; system daemons (duetexpertd, PerfPowerServices, runningboardd) up to 116% in ≤ 5 samples each; Claude desktop 2, 69% |
| A extension (758) | Google Chrome 5, 67%; system daemons ≤ 6 samples each, up to 120%; Claude desktop 2, 74% |
| B/C (373) | WindowServer 178, 41%; Google Chrome 3, 83%; system daemons ≤ 5 samples each, up to 103% |
| R (75) | WindowServer 16, 53% |
| Rmem (5) | none |
| M_desc (598) | WindowServer 46, 76%; Google Chrome 39, 197%; mobileassetd 15, 144%; Docker Desktop 2, 80%; other system daemons ≤ 10 samples each |
| M_reg (670) | Google Chrome 29, 166%; WindowServer 18, 66%; **20:17:13–29Z: disk-image mount (`diskimages-helper` 62–69%), Gemini app launch (up to 182%), Finder and two open/save-panel services at 86–98% each** |

Associations with host activity. Overlap in time only; no cause is
established:

- **M_reg, `standalone-off-read95-b1-c4-10k`, pairs 06–08**
  (20:17:12–33Z) overlap the interactive burst. In the other pairs,
  throughput was about 31,000 / 15,200 req/s (candidate / reference). In
  these three pairs, it was lower in both arms:

  | Pair | Candidate | Reference |
  |---|---|---|
  | 06 | 27,056 | 15,076 |
  | 07 | 19,461 | 9,312 |
  | 08 | 23,574 | 15,202 |

  Every pair stays in the analysis. The cell's statistical result is computed
  over all 12 pairs, as frozen.
- **R toggle churn, 19:56:42–52Z.** Analyzed pairs 02–05 overlap WindowServer
  at 33–53%:
  - those pairs took 94–163 ms in both arms;
  - pairs 06–13 took about 80–90 ms.
- **A:** no A observation lies within 5 s of a Chrome sample above 30%.
  User applications appear in the top-five samples of 302 of 312 A
  observations (cross-check table). WindowServer at 30–56% was present
  throughout A main.
- **B/C `ops` sparse 100k:** no Chrome sample above 30%; WindowServer up to
  38.6% during its 9.8-second run.
- **Per-cell table:** every cell, with its interval, the activity observed,
  the monitor coverage and its classification, is in
  [`conformance/CONFORMANCE-CROSSCHECK.md`](conformance/CONFORMANCE-CROSSCHECK.md).

Other session: `FREEZE.json` requires the other agent session to be idle. Two
Claude Code processes were alive throughout (this session and one other). Each
appeared in the top-five list in about 150 samples, with median 2–3% and
maximum 12–23%. Whether the other session was idle is not established.

Granularity: the operator rule's stated scope is the whole chain, and the
frozen invalidation rules attach no finer consequence to it. The campaign is
therefore non-conforming as a whole. Excluding single observations or pairs
would be a retroactive and more permissive rule; it would also contradict
"no outlier exclusion". Precedent: the v0.6.0 M supplement proposed none of
its non-conforming results for acceptance (REPORT-M-SUPPLEMENT §7.3).

- **Setup deviation, before any measurement:** `prepare_campaign.sh` stopped at the A plan step for the same reason as in v0.6.0 (a missing sibling `evidence/` directory). The same manual fix was applied: a symlink, then the remaining steps were run unchanged. Record: [`analysis/SETUP-DEVIATION.md`](analysis/SETUP-DEVIATION.md). The fix is still not committed to the script.
- **Tooling clone not clean:** the continuous monitor writes `activity-monitor.jsonl` into the campaign's tooling clone, as `run_final_chain.sh` declares. B/C provenance therefore records the benchmarks checkout as having one untracked file, `?? activity-monitor.jsonl`.
- **Raw evidence:** `evidence/v0.7.0-qualification-e75ff6a/` (outside this repository).
  - All 14,780 entries in [`analysis/outputs-sha256.txt`](analysis/outputs-sha256.txt) verified after the campaign; the independent review verified them again.
  - Analysis outputs: [`analysis/analysis-sha256.txt`](analysis/analysis-sha256.txt). The R, Rmem, M_desc and M_reg analyzers also wrote an `analysis.json` next to their raw data after the checksum file was made; those files are identical to the copies here.
  - The lockfile derivations (`logs/*lock-derivation.diff`) are covered by [`analysis/inputs-sha256.txt`](analysis/inputs-sha256.txt).
- **Release commit:** documentation-only commits after `e75ff6a` must leave the executed code unchanged. This is checked by comparing `__TEXT,__text` of release builds and is recorded in the release notes.

**Wording in the frozen protocol (unchanged, noted here):**
- `MATRIX.json` requires the activity gate "before every child". The A and
  B/C collectors have no activity check; only R, Rmem and M children are
  gated. `PROTOCOL.md` §3.4 lists only R, Rmem and M.
- `MATRIX.json` asks for power and thermal checks "before every cell". The A
  collector checks once per session, and M_desc once per server process
  (38 checks for 162 configurations). B/C, R, Rmem and M_reg check before
  every child.
- `MATRIX.json` `rules.R` says "order seed 60500". `experiments.R.order_seed`
  is 60700, which the collector used and the protocol states.
- The protocol and matrix say 36 M_desc server processes. The run had 38: the
  36 closed-loop servers plus 2 open-loop servers, as in v0.6.0.

**How to read:**
- *Paired change* is `exp(median ln(C/B)) − 1`. Positive means v0.7.0 is slower or larger, except for throughput: there the ratio is inverted, so positive still means worse.
- In the M_reg JSON, the `B`/`C` columns of a higher-is-better metric therefore hold candidate/reference. The tables below print reference → candidate.
- The *interval* is the paired order-statistic interval (n = 12: r(3)–r(10); n = 24: r(7)–r(18)). It is not a significance test.
- **PASS** is a regression decision, not proof of a speedup. **IMPROVED** is stated only when the whole interval is below zero.
- **Every outcome in §2–§7 is a statistical result only.** The experimental conformance of every one is NONCONFORMING (campaign, §1). No outcome here supports acceptance or a performance claim.

## 2. Lifecycle off: existing behavior against v0.6.0 (experiment A, v0.4.0 rules)

| Cell | Outcome | Primary (B → C, median) | Paired change [interval] (pairs) | Supporting metrics |
|---|---|---|---|---|
| core sparse traversal, `compact-bfs` | PASS | 4.577 → 4.578 ms | +2.96% [−4.52, +6.96] (12) | `connected` p99 PASS, RSS PASS |
| core sparse traversal, `compact-workspace` | PASS | 5.715 → 5.688 ms | −3.82% [−8.90, +6.59] (24) | PASS |
| core sustained churn, `compact-bfs` | PASS | 0.6748 → 0.6861 ms | +0.54% [−4.24, +7.65] (12) | PASS |
| core sustained churn, `compact-workspace` | PASS | 0.4705 → 0.4716 ms | +0.43% [−5.64, +3.32] (12) | PASS |
| HTTP startup to ready | INCONCLUSIVE_DISCLOSED | 4.119 → 4.037 ms | −3.84% [−22.02, +10.47] (24) | query p99 −1.38% [−16.50, +5.40] PASS; RSS +2.25% [−0.22, +3.46] PASS |
| HTTP batch 1 | **UNRESOLVED** | window 167.5 → 165.1 ms | −0.27% [−6.48, +6.25] PASS (24) | **request p99 105.0 → 103.5 µs, −0.36% [−36.33, +49.04] INCONCLUSIVE** (t = 25%); RSS +2.10% [+1.28, +4.12] PASS |
| HTTP batch 8 | PASS | 29.35 → 30.50 ms | −1.72% [−8.75, +5.53] (24) | p99 −0.17% [−5.21, +10.68] PASS; RSS +2.65% [+0.44, +5.92] PASS |
| HTTP batch 64 | PASS | 6.057 → 5.927 ms | −0.64% [−9.81, +6.44] (12) | PASS |
| HTTP batch 256 | PASS | 2.712 → 2.786 ms | +3.13% [−2.55, +8.53] (12) | p99 +4.68% [−3.37, +21.16] PASS; RSS +1.71% [−17.77, +2.28] PASS |

**Summary:** 7 PASS, 1 INCONCLUSIVE_DISCLOSED, 1 UNRESOLVED, no REGRESSION.
Four cells took the single 12-pair extension (`compact-workspace` traversal,
startup, batch 1, batch 8).

Compared with v0.6.0 against v0.5.0 (5 / 2 / 2):
- batch-1 p99 is UNRESOLVED for the third release in a row;
- startup is INCONCLUSIVE_DISCLOSED again;
- `compact-workspace` traversal and batch-256 RSS now pass.

Startup is INCONCLUSIVE because the upper bound of its wide interval,
+10.47%, exceeds the 10% primary tolerance. The median is −3.84%.

**Not covered by A:** the experimental `ett`/`hdt` engines, the feeder and
import paths (except through startup), and metrics-enabled operation. A runs
one client, so it does not exercise the shared read lock under contention;
that is M's job.

## 3. Lifecycle on: release-to-release cells (experiment R, tolerance 10%)

| Cell | Outcome | v0.6.0 → v0.7.0 (median) | Paired change [interval] |
|---|---|---|---|
| core import, sparse 100k, 20% inactive / 10% disabled | PASS | 13.533 → 13.617 ms | +0.63% [−1.13, +2.00] |
| core import, sparse 100k, 60/30 | PASS | 11.501 → 11.538 ms | +0.22% [−0.71, +2.38] |
| core import, sparse 10k, 20/10 | PASS (IMPROVED) | 0.997 → 0.976 ms | −1.84% [−3.78, −0.41] |
| core import, hub 10k, 20/10 | **INCONCLUSIVE** | 0.771 → 0.810 ms | +2.31% [−1.29, +10.86] |
| HTTP import, sparse 100k, 20/10 | **PASS (IMPROVED)** | 28.392 → 23.291 ms | −17.46% [−18.84, −16.63] |
| HTTP import, sparse 100k, 60/30 | **PASS (IMPROVED)** | 28.542 → 23.461 ms | −17.77% [−19.53, −15.48] |
| HTTP import, sparse 10k, 20/10 | **PASS (IMPROVED)** | 2.557 → 2.051 ms | −20.62% [−21.03, −19.63] |
| fresh-ID churn, sparse 100k (30 cycles × 5%) | PASS | 220.19 → 231.35 ms | +0.29% [−3.61, +6.95] |
| fresh-ID churn, hub 100k | PASS | 208.39 → 207.63 ms | −0.74% [−1.58, +0.46] |
| same-ID churn, sparse 100k | PASS | 103.02 → 101.38 ms | −1.24% [−9.64, +4.86] |
| toggle churn, sparse 100k | **INCONCLUSIVE** | 87.78 → 92.01 ms | +9.73% [−3.55, +13.69] |

- **The two INCONCLUSIVE cells** run in the `release-cells` probe on
  `knotrel-core` code paths only. `knotrel-core` is byte-identical between
  the arms. The two `release-cells` binaries are not identical, because they
  also link `knotrel-server` (with `sonic-rs` in the candidate). Their
  lockfiles differ only in the `sonic-rs` dependency tree and the knotrel
  versions. `knotrel-core`'s own dependencies are identical. That leaves code
  layout or link-time optimization, or noise, as possible causes.
  - **Toggle churn:** the paired median is 0.27 points below tolerance; the
    ratio of arm medians is +4.8%.
  - **Core import hub 10k:** paired median +2.31%, ratio of arm medians
    +5.13%; upper bound +10.86%.
  - **Toggle churn host activity:** WindowServer at 33–53% coincided with
    analyzed pairs 02–05, which are inflated in both arms (§1).
  - The cause is not established. Neither cell's `knotrel-core` code changed.

## 4. Lifecycle on: memory (Rmem; allocator byte counts, deterministic, tolerance 20%)

Every Rmem metric is byte-for-byte identical to v0.6.0: change 0.0%, PASS.

| Run (100k nodes, MiB) | v0.6.0 | v0.7.0 | Outcome |
|---|---|---|---|
| HTTP create import 20/10: peak live heap / transient over final | 32.6 / 9.5 | 32.6 / 9.5 | PASS |
| HTTP create import 60/30: peak / transient | 31.2 / 9.5 | 31.2 / 9.5 | PASS |
| HTTP replace import 20/10: peak / transient | 50.4 / 27.4 | 50.4 / 27.4 | PASS |
| core import 20/10: peak / live after | 25.8 / 24.2 | 25.8 / 24.2 | PASS |
| core import 60/30: peak / live after | 24.4 / 22.9 | 24.4 / 22.9 | PASS |
| fresh churn sparse / ring / hub: net max live | 33.5 / 30.2 / 33.2 | same | PASS |
| fresh churn sparse / ring / hub: compaction peak | 40.7 / 36.9 / 40.3 | same | PASS |
| same-ID churn sparse: net max / peak | 23.3 / 27.0 | same | PASS |
| toggle churn sparse: net max / peak | 23.0 / 23.0 | same | PASS |

`sonic-rs` parses the request body in place. The v0.6.0 HTTP import memory
reduction is kept. These are live requested-heap counts, not RSS.

## 5. Lifecycle cost on the candidate (B/C, v0.5.0 protocol unchanged)

These are not release-to-release comparisons. Each cell compares the candidate
with a semantically equivalent reference, built from the same source and run
in the same process. Full table: [`analysis/BC-analysis.md`](analysis/BC-analysis.md).

| | v0.6.0 | v0.7.0 |
|---|---|---|
| B1–B4 timing (61 cells) | 59 PASS, 1 REGRESSION, 1 INCONCLUSIVE | **58 PASS, 1 REGRESSION, 2 INCONCLUSIVE** |
| B5 memory (budget 3×) | 2.45×, 2.44× PASS | 2.45×, 2.44× PASS |
| C1 engine slots / C2 counts | all PASS | all PASS (at most 95,000 retired slots at 100k) |
| C3 heap growth | 12 PASS, **3 FAIL** | 12 PASS, **3 FAIL** (same cells, identical values) |
| C4 RSS (disclosure) | 7 PASS, 8 EXCEEDS_BUDGET | 9 PASS, 6 EXCEEDS_BUDGET (`sparse-same-1000` and `sparse-toggle-1000` now pass) |

Cells that are not PASS, or that sit close to their tolerance:

| Cell | v0.6.0 | v0.7.0 (reference → candidate) |
|---|---|---|
| `import-high` sparse 10k (60/30) | REGRESSION +419.89% [+401.74, +441.61] | **REGRESSION** 1.640 → 8.408 ms, +402.09% [+392.31, +446.45] (t = 100%) |
| `metrics-ops` sparse 10k | INCONCLUSIVE +5.57% [+1.83, +9.42] | **INCONCLUSIVE** 2.798 → 2.942 ms, +5.13% [+3.67, +7.57] (t = 6%) |
| `ops` sparse 100k | PASS +19.45% [+10.46, +23.21] | **INCONCLUSIVE** 3.843 → 4.769 ms, +20.71% [+13.27, +29.34] (t = 25%) |
| `ops` sparse 10k | PASS +19.58% [+17.92, +21.03] | PASS +21.68% [+19.16, +23.36] |
| `import` sparse 100k | PASS +84.54% | PASS 12.35 → 23.29 ms, +88.11% [+83.36, +91.28] (t = 100%) |

- **`ops` sparse 100k:** both arms run in process on the candidate server:
  the candidate arm with lifecycle on, the reference arm with lifecycle off.
  - Both send mutation-only batches, so both take the graph lock exclusively.
  - The median is within 1.3 points of v0.6.0's; the interval is wider.
  - During its 9.8-second run: no Chrome sample above 30%, WindowServer up to
    38.6% (§1).
- **`import` and `import-high`:** both arms parse with the candidate's
  parser. Absolute import times are lower than in v0.6.0 in both arms
  (`import` sparse 100k: 15.57 → 12.35 ms reference, 28.66 → 23.29 ms
  candidate).

C3 fresh-ID churn at 100k: net heap first → max → last (MiB), late/early
ratio, and 30-cycle slope as a share of the early mean. The rule is ≤ 1.25 and
≤ 0.10. All values are identical to v0.6.0:

| Topology | v0.7.0 |
|---|---|
| sparse | 23.0 → 33.5 → 31.1, 0.927, **+0.103 FAIL** |
| ring | 19.4 → 30.2 → 28.4, 0.950, **+0.172 FAIL** |
| hub | 22.5 → 33.2 → 30.8, 0.927, **+0.119 FAIL** |

## 6. Contention (M_reg against v0.6.0; tolerances: throughput 10%, p99 25%)

Probe revision 2, fresh server per observation, 2 warmup + 12 pairs. Every
analyzed observation is VALID under the declared rule.

| Cell (100k nodes unless noted, 16 closed-loop clients) | Throughput v0.6.0 → v0.7.0 | Change [interval] | Client p99 | Change [interval] | Outcome |
|---|---|---|---|---|---|
| standalone, lifecycle off, read95, batch 8 | 208.5 → 349.2 req/s | **−40.26% [−41.01, −39.14]** (IMPROVED) | 91.9 → 96.9 ms | +5.38% [+0.16, +11.16] | PASS |
| standalone, off, mixed50, batch 64 | 49.8 → 49.7 req/s | +1.01% [−1.99, +2.03] | 352.3 → 353.7 ms | +0.09% [−5.11, +4.63] | PASS |
| standalone, off, read95, batch 1, 4 clients, 10k | 15,187 → 30,681 req/s | **−50.63% [−51.29, −46.75]** (IMPROVED) | 0.53 → 0.28 ms | **−47.43% [−48.51, −40.39]** (IMPROVED) | PASS |
| standalone, lifecycle on, lifecycle50, batch 8 | 391.0 → 390.7 req/s | +0.17% [−1.26, +1.20] | 55.75 → 55.92 ms | +2.13% [−2.93, +5.48] | PASS |
| source-managed, off, read100, batch 8, replace import every second | 200.1 → 955.5 req/s | **−79.37% [−79.78, −77.08]** (IMPROVED) | 93.9 → 91.4 ms | −3.82% [−32.14, +3.68] | PASS |
| source-managed, on, read100, batch 8, feeder catch-up | 204.2 → 899.8 req/s | **−77.43% [−77.62, −77.05]** (IMPROVED) | 92.8 → 54.6 ms | **−40.47% [−47.72, −38.37]** (IMPROVED) | PASS |

Throughput changes are inverted: negative means v0.7.0 is faster.

- **read95 batch 8.** About 34% of 8-operation read95 batches contain a
  mutation (1 − 0.95⁸) and still take the lock exclusively. Throughput rises
  67%. Client p99 is +5.38% [+0.16, +11.16]: a confirmed small increase,
  within the 25% tolerance. It mixes mutation-bearing and query-only batches,
  the setting of the observation in §7.
- **read95 batch 1, 10k.** Pairs 06–08 overlap the interactive host activity
  (§1). They stay in the analysis.
- **mixed50 and lifecycle50.** These batches almost always contain a mutation
  and are unchanged.

## 7. Contention profile of the candidate (M_desc, descriptive)

All 162 rows (156 closed-loop configurations and 6 open-loop) across 38 fresh
server processes (36 closed-loop, 2 open-loop) are VALID under the declared
probe rule. Their collection is non-conforming (§1). Full table:
[`analysis/Mdesc-summary.md`](analysis/Mdesc-summary.md). Each figure is one
measured window (3 s; 5 s for import configurations) of the candidate only.

**No comparison with v0.6.0 is made here.** M_desc runs only the candidate,
and the available v0.6.0 profiles are not comparable baselines:
- **The frozen v0.6.0 campaign** ran contention probe revision 1. Its
  toggles hit the node limit at 100k, and carry-over and an off-by-one made
  some cuts no-ops at both sizes.
- **The v0.6.0 M supplement** ran revision 2, but its protocol conformance was
  not met.

Release-to-release contention statements rest only on M_reg (§6). An earlier
draft of this section compared single windows with those profiles; those
comparisons are withdrawn.

- **M5 rule (i), re-evaluated:** it holds in **16 of 32** saturated read-heavy
  configurations.
  - **Holds:** all 16 standalone `read95` configurations with batch 8 or 64.
    Lock wait is 0.87–0.97 of client latency. Batch-64 batches almost always
    contain a mutation (96%); batch-8 batches do in about 34% of cases.
  - **Does not hold:** the 8 `read95` batch-1 configurations (lock share
    0.20–0.49) and the 8 query-only source-managed `read100` configurations
    (0.00).
- **Candidate profile, 100k, lifecycle off, read95 batch 1:** 5,393 req/s at
  16 clients (p99 15.6 ms) and 4,552 req/s at 64 (p99 32.7 ms). At 10k:
  49,005 req/s with 16 clients.
- **Source-managed `read100` batch 8, 100k, lifecycle on, 16 clients:**
  1,018 req/s.
  - With feeder events: 840 req/s; 17,024 events completed in the window;
    query lock share 0.48. Queries wait behind the queued feeder batch, which
    is the writer-priority design.
  - With 64 clients: the feeder was refused with 503 115 times in the window,
    so the catch-up count there reflects admission competition.
- **Imports overlapping queries, 100k:** every background replacement import
  completed. Import p50 was 149–163 ms with 16 clients, and 428 / 761 ms with
  64 clients (lifecycle off / on).
- **read95 batch 64:** p99 reached 1,087–1,123 ms at 100k with 16 clients,
  and 239–246 ms at 10k with 64 clients. These are single windows with no
  baseline. The closest paired evidence is M_reg read95 batch 8: p99 +5.38%
  [+0.16, +11.16].
- **Open loop** (offered at 0.5 / 0.9 / 1.1 × the candidate's own measured
  saturation: 169 / 305 / 373 req/s, lifecycle off): client p99 44 / 102 /
  675 ms; lifecycle on: 16 / 103 / 959 ms.
  - The probe's open-loop "achieved" rate equals the offered rate by
    construction (limitation disclosed in v0.6.0 §7).

## 8. Non-PASS results: impact, evidence and options

Statistical results of a non-conforming campaign (§1). No option below has
been applied. No result can be accepted from this campaign; the options apply
to the conforming re-collection
([`../v0.7.0-requalification/RERUN-PROPOSAL.md`](../v0.7.0-requalification/RERUN-PROPOSAL.md)),
which measures every item again. No decision from an earlier release
applies.

| # | Result | Impact | Evidence | Options |
|---|---|---|---|---|
| 1 | B4 `import-high` **REGRESSION** +402.09% [+392.31, +446.45] (t = 100%) | Full-topology import with 60/30 flags costs about 5× an effective-graph-only reference | Recurs from v0.5.0 (+444.8%) and v0.6.0 (+419.9%). Parsing the non-effective entries the contract requires already exceeds the reference. Both arms are faster in absolute terms than in v0.6.0 | (a) accept with disclosure as inherent to the full-topology contract; (b) define a different reference or tolerance for future releases (a product decision, made before measuring) |
| 2 | C3 heap growth **FAIL** ×3 (fresh-ID churn, 100k) | Heap grows over 30 cycles before compaction | Identical values to v0.6.0 (`knotrel-core` unchanged): one-time catalog table doubling plus the retired-slot sawtooth. Slopes +0.103 / +0.172 / +0.119 | (a) accept with disclosure; (b) pre-size the catalog and re-measure (B5 cost); (c) a longer-window resource rule for future releases (a product decision, made before measuring) |
| 3 | B4 `ops` sparse 100k **INCONCLUSIVE** +20.71% [+13.27, +29.34] (t = 25%) | Lifecycle-on batch overhead at 100k might exceed 25%; median about +21% | Newly INCONCLUSIVE; v0.6.0 PASS +19.45% [+10.46, +23.21]. Same-binary comparison; both arms send mutation-only batches and take the lock exclusively. No Chrome sample; WindowServer up to 38.6% during the run | (a) accept with disclosure; (b) a declared re-measurement of this cell |
| 4 | B4 `metrics-ops` **INCONCLUSIVE** +5.13% [+3.67, +7.57] (t = 6%) | Metrics overhead on lifecycle batches may exceed the 6% budget | Recurs from v0.5.0 and v0.6.0. Metrics recording logic is unchanged; `metrics.rs` changed only to time `RwLock` acquisition | (a) accept with disclosure; (b) a targeted overhead diagnostic |
| 5 | R toggle churn **INCONCLUSIVE** +9.73% [−3.55, +13.69] | Toggle churn might be up to 13.7% slower; ratio of arm medians +4.8% (87.8 → 92.0 ms) | `knotrel-core` and its dependencies identical; the probe binaries differ (they also link `knotrel-server` and `sonic-rs`). WindowServer at 33–53% coincided with pairs 02–05, inflated in both arms | (a) accept as undetermined, with disclosure; (b) a declared re-measurement of the two R cells; (c) an identity check of the core code in both `release-cells` binaries first |
| 6 | R core import hub 10k **INCONCLUSIVE** +2.31% [−1.29, +10.86] | Upper bound 0.86 points over tolerance; median +2.3% (0.771 → 0.810 ms) | Code and binaries as 5 | As 5 |
| 7 | A batch 1 **UNRESOLVED** (request p99 interval [−36.33, +49.04]) | Tail latency of single-operation requests is undetermined; the window PASSes | Same outcome in v0.5.0 and v0.6.0; very wide interval. A uses one client, so the shared lock is uncontended; the median p99 is 105.0 → 103.5 µs | (a) accept as undetermined; (b) a longer-window p99 diagnostic, then a declared re-measurement |
| 8 | A HTTP startup **INCONCLUSIVE_DISCLOSED** −3.84% [−22.02, +10.47] | Upper bound +10.47% against the 10% primary tolerance; median slightly faster (4.119 → 4.037 ms) | Wide interval; startup passes through import (now `sonic-rs`); INCONCLUSIVE_DISCLOSED in v0.6.0 too | (a) disclose under the existing policy |
| 9 | C4 RSS EXCEEDS_BUDGET 6/15 | Disclosure only (allocator retention) | Two fewer than v0.6.0 | Disclose |
| 10 | M_reg read95 batch 8 client p99 +5.38% [+0.16, +11.16] (PASS, interval entirely above zero) | A confirmed small tail-latency increase for mixes of mutation-bearing and query-only batches, within the 25% tolerance | A plausible mechanism, not shown: a writer now waits for in-flight shared readers. Earlier single-window M_desc comparisons with v0.6.0 are withdrawn (incompatible baselines, §7) | (a) disclose; (b) a declared paired read95 batch 64 cell in a future collection (a scope change, separate decision) |
| 11 | **Experimental conformance: NONCONFORMING (campaign)**: user applications throughout; an interactive burst during M_reg; plus the setup symlink deviation and the frozen-wording discrepancies (§1) | No result of this campaign can be proposed for acceptance, PASS cells and speedup statements included | Frozen operator rule with chain-wide scope and no finer granularity; cross-check of every unit: 960 non-conforming, 13 indeterminate, 0 conforming | Single proposal: a conforming re-collection of the **whole** campaign under a frozen allow-list monitor, as in [`RERUN-PROPOSAL.md`](../v0.7.0-requalification/RERUN-PROPOSAL.md) (not started) |

## 9. Coverage and claims

- Results apply to the measured host (Apple M3, ARM64), toolchain,
  configurations and workloads. No general speedup is claimed.
- `sonic-rs` performance on x86-64 is not measured.
- Parser parity rests on unit tests in the knotrel repository, run on the
  developer host:
  - a 77-case corpus and 20,000 seeded mutations;
  - they check that `sonic-rs` and `serde_json` accept the same bodies and
    decode them to the same values;
  - error classification is unchanged by construction: bodies `sonic-rs`
    rejects go to the v0.6.0 `serde_json`/`simd-json` path.
- CI on Linux, macOS and Windows has not yet run on the candidate branch
  (release gate).
- Fresh-ID churn slowest single operation (one compaction per run), medians
  over 12 pairs: sparse 18.62 → 18.96 ms, hub 16.82 → 16.71 ms.
- The shared read lock helps only requests whose operations are all queries.
  A batch with any mutation keeps the whole graph exclusively (§6, §7).
- The diagnostics (`diagnostics/DIAGNOSTICS-v0.7.0.md`) chose the candidates.
  They change no verdict here.
