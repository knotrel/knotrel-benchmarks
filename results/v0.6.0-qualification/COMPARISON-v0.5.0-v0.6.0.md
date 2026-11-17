# Knotrel v0.6.0 vs v0.5.0 — release performance comparison

This is the per-release comparison the knotrel release procedure requires. It
is assembled from the frozen v0.6.0 final qualification
([protocol](PROTOCOL.md), [matrix](MATRIX.json), [freeze record](FREEZE.json)).
The v0.6.0 release notes are the authoritative product statement; maintainer
decisions on the failures below are recorded there, not here. No maintainer
waiver from an earlier release applies.

**Outcome:** v0.6.0 is **not demonstrated to be faster in general**. The
qualification did **not pass unconditionally**. Results by area:

- **Imports:** HTTP import memory falls sharply, and core imports and fresh-ID
  churn are confirmed faster. One release-to-release timing REGRESSION remains
  (HTTP import with many inactive entries).
- **Repeated failures:** the lifecycle-cost REGRESSION for that import and the
  three heap-growth FAILs recur from v0.5.0.
- **Lifecycle off** (against v0.5.0): no REGRESSION, 2 UNRESOLVED and 2
  INCONCLUSIVE_DISCLOSED cells.
- **Contention:** no regression against v0.5.0 on the cells that measured what
  they declared. The single graph lock dominates read-heavy latency at
  saturation. Part of the contention matrix was invalidated by a tooling
  defect (§7).

## 1. Identities

| | Reference (published v0.5.0) | Candidate (v0.6.0) |
|---|---|---|
| knotrel commit | `51e3b4da2de802a4ebf352b1e8a8311657e48d38` (signed tag `v0.5.0`; crates.io 0.5.0; GitHub Release) | `48bc82fabbd36b2cd34bf3790b2d625de3503195` (branch `feature/v0.6.0-lifecycle-efficiency`) |
| `knotrel-server` (local release build) sha256 | `e3d12df8e669224c20890fe8720dfb7b372a352c5ff5aa01bb9d6e8de6c1b236` | `d4adec2e8813c8316a813a8b33969c193245723e5964b3ded20b4d543021667d` |
| A core harness (knotrel-benchmarks `df635a1e`, derived lockfile) sha256 | `03f0391f6c20eb98182b874f5975462f23d4d9ff8ca497d22a4a010edd598b42` | `c55b258a67e62a62f26276bba67c0562d4a2315ceae8d06c32dcf97b8ab1e534` |
| `release-cells` sha256 | `e276edd943ea8b6cbd7ebffea3729012701ae622e9cbc1674ee76cb3606e969d` | `8cb44029b12c783ac7cfd47b73f2ed758335796b630523645dbbae4576701e3f` |
| `memory-peak` sha256 | `06c94029a70b95f08e8ea823acaf60fb34c0cdd93da036faa9c633eea40c5658` | `3a8391e1564d67c535a2ad4a8c367b88c25928ac386ae50f2a3ca904b5bce378` |

- **Shared binaries:**
  - `measure_e2e` (A HTTP driver, from the candidate source): `3bc27430584b0eafb2845dcd313457d853f5d5f4f65a617998bd46a22d6bb55b`.
  - `contention-probe`: `a3f3c3ff6065d0bd1aaf80605619b60c955492fbec6a56dad310d7ebf1077a69`.
  - Candidate lifecycle probes: `core-lifecycle` `7f220b28…`, count-alloc `core-lifecycle` `ef7d8eb4…`, `http-lifecycle` `0f9703bc…`.
  - Full list: [`analysis/binaries-sha256.txt`](analysis/binaries-sha256.txt).
- **Tooling:** knotrel-benchmarks `54dcfc514582f495dd0c0eb51d8604fcd0fc2114`; freeze commit `763584627ffeebe195ad0cfc2f9af0a9b4f25a2e`, which adds only `FREEZE.json`. Reference probes are built from the same tooling with the v0.5.0 probe lockfile (diff recorded); their build records name knotrel `51e3b4d` clean and, as expected from that lockfile derivation, `probes_dirty: true`. Candidate builds name `48bc82f` clean.
- **Host and toolchain:** Apple M3, macOS 26.5.2; rustc 1.100.0, release profile, `--locked --offline`. All 506 collector children ran on AC power with no recorded thermal or performance warning. The 1-minute load average was 9.41 at launch (decaying after the campaign builds; no build process was running). A main session 0 ran at a 1-minute load of 5.31–5.98 (5-minute about 9.6), with no visible effect on its paired ratios relative to the other sessions. R and M children started at 1.80–6.46. No load limit exists in the rules; this is disclosure, not a validity condition.
- **Campaign:** 2026-11-16T22:50:26Z → 23:49:59Z (A main 13.4 min, A extension 13.3 min, B/C 7.2 min, R 1.1 min, Rmem 0.1 min, M_desc 11.5 min, M_reg 12.8 min), estimated at 83 min, cap 240 min.
- **Raw evidence:** `evidence/v0.6.0-qualification-48bc82f/` (outside this repository).
  - **Post-campaign change to the evidence tree:** a `git fetch` ran in the A source clones (`A/sources/{B,C}/knotrel`, `A/sources/knotrel-benchmarks`) at about 00:04Z on 2026-11-17, during the post-campaign review. It most likely came from the reviewing agent; this is not established. Three `.git/FETCH_HEAD` files now fail `outputs-sha256.txt` and git objects were added. HEADs and all measured outputs are unchanged.
  - Output checksums: [`analysis/outputs-sha256.txt`](analysis/outputs-sha256.txt).
  - Input checksums: [`analysis/inputs-sha256.txt`](analysis/inputs-sha256.txt).
  - One setup deviation before measurement: [`analysis/SETUP-DEVIATION.md`](analysis/SETUP-DEVIATION.md).
- **Release commit:** documentation-only commits after `48bc82f` must leave the executed code unchanged. This is verified by comparing `__TEXT,__text` of release builds and recorded in the release notes.

**How to read:** *paired change* is `exp(median ln(C/B)) − 1`; positive means
v0.6.0 is slower or larger, except for throughput, where the ratio is inverted
so that positive is still worse. The *interval* is the paired order-statistic
interval (n = 12: r(3)–r(10); n = 24: r(7)–r(18)), not a significance test.
**PASS** is a regression decision, not proof of a speedup. **IMPROVED** is
stated only when the whole interval is below zero.

## 2. Lifecycle off: existing behavior against v0.5.0 (experiment A, v0.4.0 rules)

| Cell | Outcome | Primary (B → C, median) | Paired change [interval] (pairs) | Supporting metrics |
|---|---|---|---|---|
| core sparse traversal, `compact-bfs` | PASS | 4.660 → 4.609 ms | −0.95% [−3.78, +2.92] (24) | p99 PASS, RSS PASS |
| core sparse traversal, `compact-workspace` | INCONCLUSIVE_DISCLOSED | 5.108 → 5.652 ms | +6.20% [−1.72, +19.43] (24) | `connected` p99 +2.32% [+0.54, +12.64] PASS; RSS PASS |
| core sustained churn, `compact-bfs` | PASS | 0.6705 → 0.6708 ms | −0.34% [−1.17, +0.09] (12) | PASS |
| core sustained churn, `compact-workspace` | PASS | 0.4837 → 0.4809 ms | −0.27% [−4.75, +1.71] (12) | PASS |
| HTTP startup to ready | INCONCLUSIVE_DISCLOSED | 4.37 → 4.57 ms | +7.18% [−18.30, +24.15] (24) | query p99 PASS; RSS −4.50% [−5.11, −3.33] PASS |
| HTTP batch 1 | **UNRESOLVED** | window 169.1 → 167.0 ms | +0.30% [−5.15, +4.15] PASS (24) | **request p99 120.4 → 131.2 µs, −2.29% [−26.62, +52.03] INCONCLUSIVE** (t = 25%); RSS PASS |
| HTTP batch 8 | PASS | 30.94 → 29.01 ms | +0.40% [−9.43, +2.05] (12) | PASS |
| HTTP batch 64 | PASS | 5.658 → 5.640 ms | −0.73% [−7.81, +6.96] (12) | PASS |
| HTTP batch 256 | **UNRESOLVED** | 2.636 → 2.653 ms | −0.93% [−2.75, +0.60] PASS (24) | p99 PASS; **sampled max RSS 6.82 → 6.96 MB, +1.15% [+0.23, +22.16] INCONCLUSIVE** (t = 20%) |

**Summary:** 5 PASS, 2 INCONCLUSIVE_DISCLOSED, 2 UNRESOLVED, no
REGRESSION. Five cells took the single 12-pair extension. v0.5.0 vs v0.4.0
was 6 / 1 / 2. Batch-1 p99 is UNRESOLVED again; batch-256 RSS is newly
UNRESOLVED; batch-64 RSS, UNRESOLVED in v0.5.0, now passes.

**Not covered by A:** the experimental `ett`/`hdt` engines, feeder and import
paths (except through startup), and metrics-enabled operation.

## 3. Lifecycle on: release-to-release cells (experiment R, tolerance 10%)

| Cell | Outcome | v0.5.0 → v0.6.0 (median) | Paired change [interval] |
|---|---|---|---|
| core import, sparse 100k, 20% inactive / 10% disabled | **PASS (IMPROVED)** | 15.595 → 13.532 ms | −13.62% [−14.91, −11.95] |
| core import, sparse 100k, 60/30 | PASS | 11.446 → 11.388 ms | −0.26% [−3.85, +1.90] |
| core import, sparse 10k, 20/10 | **PASS (IMPROVED)** | 1.144 → 1.025 ms | −11.72% [−15.41, −8.19] |
| core import, hub 10k, 20/10 | **PASS (IMPROVED)** | 0.846 → 0.813 ms | −5.63% [−10.64, −4.10] |
| HTTP import, sparse 100k, 20/10 | PASS | 28.264 → 28.360 ms | +0.74% [−0.29, +1.72] |
| HTTP import, sparse 100k, 60/30 | **REGRESSION** | 25.133 → 28.476 ms | **+13.44% [+12.55, +14.02]** |
| HTTP import, sparse 10k, 20/10 | PASS | 2.293 → 2.466 ms | +7.71% [+6.05, +8.72] |
| fresh-ID churn, sparse 100k (30 cycles × 5%) | **PASS (IMPROVED)** | 199.26 → 188.22 ms | −5.75% [−7.34, −3.24] |
| fresh-ID churn, hub 100k | **PASS (IMPROVED)** | 212.17 → 201.13 ms | −5.68% [−6.71, −3.34] |
| same-ID churn, sparse 100k | PASS | 97.76 → 94.44 ms | −3.41% [−6.63, +1.58] |
| toggle churn, sparse 100k | PASS | 77.65 → 77.74 ms | +0.57% [−4.33, +3.11] |

Slowest single operation in fresh-ID churn (one compaction per run in both
releases), medians over the 12 analyzed pairs: sparse 29.63 → 17.50 ms, hub
28.75 → 16.42 ms.

## 4. Lifecycle on: memory (Rmem; allocator byte counts, deterministic, tolerance 20%)

| Run (100k nodes, MiB) | v0.5.0 | v0.6.0 | Change | Outcome |
|---|---|---|---|---|
| HTTP create import 20/10 (body 8.3 MiB): peak live heap | 111.2 | 32.6 | −70.7% | PASS |
| … transient over final graph | 87.0 | 9.5 | −89.0% | PASS |
| HTTP create import 60/30 (body 9.9 MiB): peak | 128.6 | 31.2 | −75.7% | PASS |
| … transient over final | 106.2 | 9.5 | −91.0% | PASS |
| HTTP replace import 20/10 (old graph live): peak | 130.3 | 50.4 | −61.3% | PASS |
| … transient over final | 106.0 | 27.4 | −74.2% | PASS |
| core import 20/10: peak / live after | 28.2 / 25.5 | 25.8 / 24.2 | −8.7% / −4.8% | PASS |
| core import 60/30: peak / live after | 24.8 / 23.6 | 24.4 / 22.9 | −1.7% / −2.9% | PASS |
| fresh churn sparse: net max / compaction peak | 37.3 / 49.2 | 33.5 / 40.7 | −10.1% / −17.2% | PASS |
| fresh churn ring | 33.1 / 43.6 | 30.2 / 36.9 | −9.0% / −15.5% | PASS |
| fresh churn hub | 36.9 / 48.7 | 33.2 / 40.3 | −9.9% / −17.3% | PASS |
| same-ID churn sparse | 24.1 / 27.0 | 23.3 / 27.0 | −3.1% / 0.0% | PASS |
| toggle churn sparse | 23.0 / 23.0 | 23.0 / 23.0 | 0.0% | PASS |

These numbers are live requested heap. They are not RSS, which includes
allocator retention and has no bound from Knotrel.

## 5. Lifecycle cost on the candidate (B/C, v0.5.0 protocol unchanged)

These are not release-to-release comparisons. Each cell compares the
candidate with a semantically equivalent reference built from the same
source in the same process. Verdicts are compared with v0.5.0 run 4
(`dcd8ccc`); reference arms differ between runs because of host variance.

| | v0.5.0 run 4 | v0.6.0 |
|---|---|---|
| B1–B4 timing (61 cells) | 56 PASS, 2 REGRESSION, 3 INCONCLUSIVE | **59 PASS, 1 REGRESSION, 1 INCONCLUSIVE** |
| B5 memory (budget 3×) | 2.45×, 2.44× PASS | 2.45×, 2.44× PASS |
| C1 engine slots / C2 counts | all PASS | all PASS (max retired slots 95,000 at 100k) |
| C3 heap growth | 12 PASS, **3 FAIL** | 12 PASS, **3 FAIL** (same cells) |
| C4 RSS (disclosure) | 7 PASS, 8 EXCEEDS_BUDGET | 7 PASS, 8 EXCEEDS_BUDGET (`sparse-toggle-1000` newly exceeds, `sparse-same-100000` newly passes) |

Cells that changed verdict or are not PASS:

| Cell | v0.5.0 | v0.6.0 (reference → candidate) |
|---|---|---|
| `import` sparse 100k | REGRESSION +109.9% [+101.9, +115.9] | **PASS** 15.57 → 28.66 ms, +84.54% [+82.58, +86.40] (t = 100%) |
| `import` sparse 10k | INCONCLUSIVE +100.8% [+96.1, +107.0] | **PASS** 2.97 → 5.36 ms, +80.88% [+76.23, +85.76] |
| `import` hub 10k | PASS | PASS +69.94% [+66.02, +74.64] |
| `import-high` sparse 10k (60/30) | REGRESSION +444.8% [+427.3, +464.6] | **REGRESSION** 2.05 → 10.56 ms, +419.89% [+401.74, +441.61] |
| `metrics-ops` | INCONCLUSIVE +6.5% [+5.3, +8.3] | **INCONCLUSIVE** 2.77 → 2.91 ms, +5.57% [+1.83, +9.42] (t = 6%) |
| `metrics-legacy` `ett` | INCONCLUSIVE +4.0% [+1.0, +6.4] | PASS +1.92% [−0.10, +4.13] |

C3 fresh-ID churn at 100k, net heap first → max → last (MiB), late/early
ratio and 30-cycle slope as a share of the early mean (rule: ≤ 1.25 and
≤ 0.10):

| Topology | v0.6.0 | v0.5.0 |
|---|---|---|
| sparse | 23.0 → 33.5 → 31.1, 0.927, **+0.103 FAIL** | 23.0 → 37.3 → 34.5, 0.969, +0.117 FAIL |
| ring | 19.4 → 30.2 → 28.4, 0.950, **+0.172 FAIL** | +0.208 FAIL |
| hub | 22.5 → 33.2 → 30.8, 0.927, **+0.119 FAIL** | +0.136 FAIL |

The check counts allocated heap over 30 cycles. The remaining rise includes
the one-time catalog hash-table doubling described in the lifecycle contract
(*Hash-table capacity under churn*). The verdicts stand as measured.

## 6. Contention (M_reg against v0.5.0; tolerances: throughput 10%, p99 25%)

| Cell (100k nodes unless noted, 16 closed-loop clients) | Throughput v0.5.0 → v0.6.0 | Change [interval] | Client p99 | Change [interval] | Outcome |
|---|---|---|---|---|---|
| standalone, lifecycle off, read95, batch 8 | 209.2 → 208.3 req/s | +0.16% [−0.64, +5.04] | 91.6 → 92.3 ms | +2.60% [−3.90, +22.05] | PASS |
| standalone, off, mixed50, batch 64 † | 50.33 → 50.33 req/s | 0.00% [−0.66, +2.01] | 353.8 → 352.7 ms | +1.19% [−2.55, +4.83] | PASS † |
| standalone, off, read95, batch 1, 4 clients, 10k | 15,363 → 15,246 req/s | +0.66% [+0.34, +1.20] | 0.524 → 0.533 ms | +1.64% [+0.62, +3.25] | PASS |
| standalone, lifecycle on, lifecycle50, batch 8 | 391.0 → 388.2 req/s | +0.47% [−0.95, +1.87] | 56.4 → 56.5 ms | +2.22% [−4.78, +3.85] | PASS |
| source-managed, off, read100, batch 8, replace import every second | 200.1 → 199.6 req/s | +0.55% [−0.40, +1.79] | 95.0 → 94.9 ms | −0.70% [−22.70, +6.00] | PASS |
| source-managed, on, read100, batch 8, feeder catch-up ‡ | 202.3 → 203.7 req/s | −1.55% [−2.47, +1.32] | 93.2 → 91.8 ms | −1.60% [−9.84, +2.58] | **invalid for its purpose ‡** |

Throughput "change" is positive when v0.6.0 is slower. The 10k batch-1 cell
is slightly but consistently slower in both metrics (throughput +0.66%
[+0.34, +1.20], p99 +1.64% [+0.62, +3.25]), within tolerance. (An earlier
version of this table printed the throughput medians in reversed order; the
percentages and verdicts were correct.)

## 7. Contention profile of the candidate (M_desc, descriptive) and coverage defect

Full table: [`analysis/Mdesc-summary.md`](analysis/Mdesc-summary.md).

- **Lock-bound reads.** The predeclared M5 rule (i) holds in 32 of 32 saturated
  read-heavy configurations: mean graph-lock wait is 0.85–1.01 of mean client
  latency at 16 or 64 clients. Throughput does not grow with clients:
  - 100k, lifecycle off, read95 batch 1: 1,482 / 1,561 / 1,344 req/s at
    1 / 16 / 64 clients, p99 1.90 / 17.2 / 50.7 ms;
  - mean execution under the lock 0.59–0.74 ms, about one BFS per
    `connected`.
  - Maintainer decision B keeps the mutex for v0.6.0; v0.7.0 addresses this
    bottleneck.
- **Batch size (M3.6).** Larger batches amortize HTTP overhead but not lock
  time. Operations per second at 100k, read95, one client: 1,482 (batch 1),
  1,592 (8), 1,685 (64). Per-request latency grows proportionally
  (p50 0.54 / 4.8 / 37.6 ms). At 16 clients, a 64-operation batch waits
  about 0.6 s at p50.
- **Saturation.** With 64 clients (above the 32 pending-job limit), excess
  requests get 503 `busy`, 163,000–306,000 per 3-second window from 64
  tight-looping clients (237,000–306,000 at 100k). At 100k, achieved
  throughput falls 10–51% below the 16-client level (for example read95 batch
  64, lifecycle on: 1,728 → 853 operations/s), and fairness drops at batch 64
  (Jain 0.60–0.89). At 10k the change ranges from +44% to −12%, with Jain
  0.98–0.99.
- **Imports overlapping queries.** At 100k, a replacement import every second
  completed in every configuration. Its p50 HTTP duration rose with
  query load (85 ms with 4 clients, 206 ms with 16, 425 ms with 64): it waits
  for the graph lock behind queries. Query throughput changed by −0.7% to
  −3.5%. **At 10k with 16 and 64 clients, every background import failed**
  (completed 0, failures 5, in both lifecycle off and on; see the second
  coverage defect below).
- **Open loop.** Load was offered at 0.5 / 0.9 / 1.1 × the measured
  closed-loop saturation (100k, read95, batch 8, 16 clients; lifecycle off).
  - Client p50 was 14.1 / 15.2 / 377 ms and p99 24.1 / 26.0 / 514 ms
    (lifecycle on: p50 14.6 / 15.9 / 250 ms).
  - Beyond saturation, latency grows without bound for the duration of the
    overload; there is no shedding below the pending-job limit.
  - **Limitation:** the probe's open-loop "achieved" rate counts every request
    scheduled inside the window, including those completed after it, so it
    equals the offered rate by construction (103 / 185 / 226 req/s). It is not
    a throughput measure; saturation shows only in latency.
- **‡ Coverage defect (tooling).** The probe's feeder catch-up and `mixed50`
  link toggles register new node IDs above the graph's size. The server's
  default `KNOTREL_MAX_NODES` is 100,000, so at 100k nodes:
  - every feeder `link` event fails with `node_limit_exceeded`, and the
    background feeder stops after its first request;
  - `mixed50` links are rejected per item, and its cuts are no-ops.
  - Consequences:
    - Feeder catch-up overlapping queries was **not measured at 100k**
      (6 M_desc configurations and M_reg's last cell). That cell is reported
      but is not a valid catch-up comparison.
    - **† `mixed50` at 100k** measured rejected links and no-op cuts instead
      of effective toggles, in both arms; M_reg's comparison is still
      like-for-like.
    - At 10k, catch-up was measured with 4 and 16 clients; with 64 clients the
      feeder stopped after one batch. The cause was not logged; it is
      probably admission refusal (503) while queries hold all pending-job
      slots, which is unverified.
  - The defect was found after the campaign and reproduced with a scratch copy
    of the probe that prints the server's reply. The record is in
    `evidence/v0.6.0-diagnostics/post-campaign-probe-defect/`: feeder events
    at 100k return 422 `node_limit_exceeded`, and a probe-style toggle at 100k
    returns a per-item `node_limit_exceeded` link and a no-op cut. The frozen
    results are kept unchanged. A fix would change frozen tooling and needs a
    new, separately declared run.
- **Second coverage defect (tooling).** At 10k nodes with 16 and 64 clients,
  the background replacement imports all failed (4 M_desc configurations).
  The probable cause, not reproduced, is that the probe reuses an etag the
  preceding feeder-events configuration made stale. The reply is not logged.
  Import overlap at 10k is therefore covered only with 4 clients.

## 8. Non-PASS results: impact, evidence and options

No option below has been applied. Accepting any failure is a maintainer
decision for v0.6.0 only.

| # | Result | Impact | Evidence | Options |
|---|---|---|---|---|
| 1 | R HTTP import 100k 60/30 **REGRESSION** +13.44% [+12.55, +14.02] (+3.3 ms) | Flagged imports dominated by inactive/disabled entries take about 13% longer than in v0.5.0; the 20/10 import is unchanged (+0.74%) and 10k is +7.7% | C2 replaced simd-json with serde_json for import bodies. serde_json is slower on flagged object entries; peak memory falls 76% for the same import (Rmem) | (a) accept for v0.6.0 with disclosure, trading time for memory; (b) optimize flagged-entry deserialization (hand-written visitor) and re-qualify R/B4 import cells; (c) revert C2 and lose the memory reduction |
| 2 | B4 `import-high` **REGRESSION** +419.89% (t = 100%) | Against a reference that imports only the effective graph, the full-topology import with 60/30 flags costs about 5× | Repeats v0.5.0 (+444.8%). Parsing the non-effective entries the contract requires already exceeds the reference | (a) accept with disclosure as inherent to the full-topology contract; (b) define a different reference or tolerance for future releases (product decision, before measuring); (c) reduce parse cost as in 1(b) |
| 3 | C3 heap growth **FAIL** ×3 (fresh-ID churn, 100k) | Heap grows over 30 cycles before compaction; peaks are lower than v0.5.0 | Bounded one-time catalog table doubling plus the retired-slot sawtooth until compaction at `V` retired slots (lifecycle contract); slopes +0.103 / +0.172 / +0.119 | (a) accept with disclosure; (b) pre-size the catalog against doubling (about +5 MiB per 100k nodes, with a B5 cost) and re-measure; (c) a longer-window resource rule for future releases (product decision, before measuring) |
| 4 | A batch 1 **UNRESOLVED** (request p99 interval [−26.62, +52.03]) | Tail latency of single-operation batches is undetermined; the window PASSes | No code change on the standalone batch path; same outcome as v0.5.0; very wide interval | (a) accept as undetermined; (b) a longer-window p99 diagnostic, then a declared re-measurement |
| 5 | A batch 256 **UNRESOLVED** (sampled max RSS upper bound +22.16% against 20%) | RSS might exceed tolerance; the median is +1.15% | No code change on the batch path; sampled RSS is noisy | Same as 4 |
| 6 | A `compact-workspace` traversal, startup **INCONCLUSIVE_DISCLOSED** | Traversal: paired median +6.20%, upper bound +19.43%, ratio of arm medians +10.6% (5.108 → 5.652 ms). Startup: +7.18%, upper bound +24.15% | Startup passes through import (C2). The traversal path has no code change, apart from new crate-private functions in the same crate | (a) disclose under the existing policy; (b) a declared re-measurement if the traversal size matters for the decision |
| 7 | B4 `metrics-ops` **INCONCLUSIVE** +5.57% [+1.83, +9.42] (t = 6%) | Metrics overhead on lifecycle batches may exceed the 6% budget | Repeats v0.5.0; no code change on the metrics path | (a) accept with disclosure; (b) a targeted overhead diagnostic |
| 8 | C4 RSS EXCEEDS_BUDGET 8/15 | Disclosure only (allocator retention) | Same count as v0.5.0 | Disclose |
| 9 | Contention coverage defects (§7): feeder catch-up not measured at 100k (6 M_desc configurations and the M_reg events cell); `mixed50` at 100k ran rejected links and no-op cuts; import overlap at 10k not measured with 16 or 64 clients (4 configurations) | The catch-up overlap requirement is not covered at 100k, and the import overlap requirement only partly at 10k | Tooling defects. Node-limit cause reproduced (`evidence/v0.6.0-diagnostics/post-campaign-probe-defect/`); the import cause is probable, not reproduced | (a) declare and run a separate, labelled run of the affected M cells with fixed tooling, with no change to frozen results; (b) leave as coverage gaps for v0.7.0's contention work |
