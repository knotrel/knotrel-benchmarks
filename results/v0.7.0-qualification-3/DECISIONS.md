# v0.7.0 qualification: final decision record

**Overall status: ACCEPTED WITH EXCEPTIONS** (accettato con eccezioni), for
v0.7.0 only.
- This is **not** "all gates PASS", and **not** a complete qualification.
- Three deciding results are INCONCLUSIVE and accepted by the maintainer.
- Two requirements are not qualified by comparison and are accepted by a
  maintainer exception.
- Every original verdict, criterion and threshold stands as measured.
- No exception below is a precedent for any other release.

This file is the single decision record for v0.7.0. It supersedes nothing:
the protocol (`PROTOCOL.md`), the freezes (`FREEZE.json`, `FREEZE-r2.json`)
and the earlier attempts stay unchanged. The analyses are in
`analysis/q3-3/` (checksums in `analysis/q3-3/analysis-sha256.txt`).

## 1. What was measured

| | |
|---|---|
| Candidate | knotrel `fa5f3a9eac24873dd2d8d3e0a2c21764cfff9373` |
| Reference | published knotrel v0.6.0, signed tag `v0.6.0` = `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538` |
| T5 arm B | knotrel `e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc` (the candidate without the catalog tombstone handling) |
| Tooling and probes | knotrel-benchmarks `0be5471654ed9d3629f8c85d8b86705b0cf351e1` (freeze revision 3) |
| Attempt | q3-3, 2026-11-20 09:41–11:09Z, Apple M3 (4P+4E), 16 GB, macOS 26.5.2, rustc 1.100.0 |
| Raw evidence | private bundle `v0.7.0-qualification-3-fa5f3a9-q3-attempt3`; 1891 output files, checksums in `analysis/q3-3/campaign-outputs-sha256.txt`; 14 binaries in `analysis/q3-3/binaries-sha256.txt` |

## 2. Conformance

- **q3-3: CONFORMING** under the revision-3 protocol (§14). Every unit was
  valid; counts and binaries were verified at the end.
  - 756 units, 0 invalidated, 0 repeated, 0 block restarts.
  - 6 readiness waits, 71.7 s in all (longest 18.2 s). Each wait was the
    30-s external CPU mean at 0.60–0.63 cores against 0.6.
  - 87.2 min of a 105-min budget.
- **Earlier attempts, unchanged and not conforming:**
  - q3-1: user input under the revision-2 rule;
  - q3-2: gate stop after R, caused by the heartbeat timestamp defect fixed
    in revision 3 (§14.1).
  
  Neither result is used, and no retroactive conformance is claimed.
- **Analysis.** The analyses ran with the frozen analyzers
  (`analysis/q3-3/ANALYSIS-COMMANDS.txt`). The first B/C invocation failed
  with no output, because the path-confinement variable was not set. It was
  rerun with the variable set; no data was read in between.

## 3. Results

| Experiment | Outcome |
|---|---|
| A (session, extension) | 9/9 PASS |
| B1–B4 timing, deciding | 58 PASS, **1 INCONCLUSIVE** (accepted, §4 D1) |
| B4 timing, descriptive | 11 PASS, 1 REGRESSION (`import-high`, §5.2), 1 INCONCLUSIVE (`ops` sparse 100k) |
| B4 not-equivalent (hub 10k ops, events) | 2 PASS, descriptive, no verdict (§4 D3) |
| B5 memory | 2/2 PASS |
| C1 / C2 | 30/30 PASS / 60/60 PASS |
| **C3 heap growth** | **15/15 PASS** |
| C4 RSS | 9 PASS, **6 EXCEEDS_BUDGET** (disclosure category, §5.1) |
| **T5 compaction pauses** | **6/6 PASS** |
| R | 9 PASS, **2 INCONCLUSIVE** (accepted, §4 D2) |
| Rmem | 10/10 PASS |
| M_reg | 6/6 PASS (4 improved) |
| M_desc | 162/162 configurations valid (descriptive) |

**C3.** All 15 cells pass (late/early ≤ 1.25 and 30-cycle growth ≤ 0.10).
The three cells that failed in the re-qualification (fresh-ID churn,
100k nodes) now pass:

| Cell | Late/early | 30-cycle growth |
|---|---|---|
| sparse fresh 100k | 0.914 | −0.021 |
| ring fresh 100k | 0.940 | +0.037 |
| hub fresh 100k | 0.914 | −0.006 |

**T5** (100k nodes, 600 cycles, 5% fresh churn, 12 pairs; tolerance 25%;
median of C against B, with its interval):

| Topology | P_max, B → C | P_90, B → C |
|---|---|---|
| sparse | 17.32 → 15.61 ms, −10.6% [−16.7, −6.7] PASS | 15.66 → 14.38 ms, −8.8% [−10.0, −6.9] PASS |
| ring | 14.09 → 12.90 ms, −7.5% [−12.0, −6.5] PASS | 13.23 → 12.41 ms, −6.1% [−7.9, −5.4] PASS |
| hub | 16.53 → 14.90 ms, −8.5% [−13.7, −7.8] PASS | 15.55 → 14.27 ms, −8.1% [−9.4, −7.7] PASS |

**M_reg** (reference v0.6.0 → candidate, request throughput and p99):

| Cell | Throughput | p99 |
|---|---|---|
| standalone read95, b1, 4 clients, 10k | 15,289 → 32,232 req/s (×2.11) | 0.53 → 0.26 ms |
| standalone read95, b8, 16 clients, 100k | 213 → 350 req/s (×1.65) | 91.1 → 90.7 ms |
| standalone mixed50, b64, 16 clients, 100k | 51 → 51 req/s | 346 → 353 ms |
| standalone lifecycle50, b8, 16 clients, 100k | 399 → 399 req/s | 54.7 → 54.1 ms |
| source-managed read100 during import, 100k | 204 → 1,053 req/s (×5.17) | 92.2 → 77.0 ms |
| source-managed read100 during events, 100k | 206 → 938 req/s (×4.54) | 91.3 → 50.5 ms |

## 4. Maintainer decisions (2026-11-20)

### D1. B4 `metrics-ops`, sparse 10k: accepted INCONCLUSIVE

`B4-http-metrics-ops-compact-bfs-sparse-10000`: 2.71 → 2.83 ms, median
+6.5%, interval [+1.7%, +7.4%], budget 6%.
- **Stays INCONCLUSIVE**, accepted for v0.7.0 only; it does not become
  PASS.
- Not repeated.

### D2. R `core-import` sparse and hub 10k: accepted INCONCLUSIVE

| Cell | v0.6.0 → candidate | Median | Interval | Tolerance |
|---|---|---|---|---|
| `R-core-import-sparse-10k-20-10` | 970 → 947 µs | −1.7% | [−17.6%, +14.2%] | 10% |
| `R-core-import-hub-10k-20-10` | 788 → 802 µs | +3.1% | [−17.9%, +24.7%] | 10% |

- The uncertainty is accepted; both **stay INCONCLUSIVE**, for v0.7.0 only.
- Not repeated.

> "questi tre risultati restano INCONCLUSIVE, con accettazione esplicita
> del maintainer per v0.7.0 soltanto. Non diventano PASS e non costituiscono
> precedenti per altre release."

### D3. B4 `ops` and `events`, hub 10k: exception for two unqualified requirements

**Why they are uncovered.** No candidate measurement is missing: q3-3 holds
valid candidate observations for both. The missing piece is a v0.6.0
reference that offers the candidate's atomicity (PROTOCOL §4.3).
- The hub 10k trace deactivates two hub nodes. Each command expands to
  1,425 and 1,565 plain operations.
- A plain request carries at most 1,024 operations
  (`MAX_BATCH_OPERATIONS`, not configurable).
- **ops:** no atomic plain route exists.
- **events:** the only atomic route is a full replacement import per
  affected chunk. That is a different reference design, excluded by
  decision 8.
- Neither a fix to the analysis nor a targeted collection can produce a
  comparison under the protocol.

**Decision.**

> "Autorizzo l'eccezione per B4 ops/events hub 10k, limitata a v0.7.0. I
> requisiti restano non qualificati per confronto e non diventano PASS.
> Questa decisione modifica esplicitamente il precedente divieto di
> eccezioni per queste due voci."

**Indicative evidence, not a verdict.** Each comparison has limits:

| Requirement | Comparison | v0.6.0 → candidate | Median [interval] |
|---|---|---|---|
| ops | frozen cell (`B4-http-ops-…-hub-10000`) | 2.83 → 2.96 ms | +4.0% [+1.8, +7.3] |
| ops | not-equivalent cell (`…-equivalent-…`) | 3.41 → 3.13 ms | −6.8% [−11.4, −3.6] |
| events | frozen cell | 4.97 → 5.20 ms | +5.0% [+4.3, +6.3] |
| events | not-equivalent cell | 5.56 → 5.21 ms | −6.4% [−7.1, −5.2] |

- **Frozen cells.** The v0.6.0 side plans outside the timed window and is
  not atomic: it provides a different service. How its cost relates to an
  atomic reference is unknown.
- **Not-equivalent cells.** The v0.6.0 side plans inside the window, but it
  splits two lifecycle chunks into two requests each (39 requests against
  37 for ops, 76 against 74 for events), so it is still not atomic. The
  direction and size of the bias this introduces are not measured.
- **No measured atomic reference exists** for either requirement.
- The 25% tolerance of these families is quoted for orientation only; no
  status is derived from it.

## 5. Disclosures (unchanged categories)

### 5.1 C4 RSS: EXCEEDS_BUDGET ×6

C4 is a disclosure category by rule (allocator retention in RSS), not a
FAIL. These are the same cells as in the re-qualification. Net RSS first →
last and 30-cycle projected growth:

| Cell | Net RSS first → last | 30-cycle growth |
|---|---|---|
| sparse fresh 1k | 0.16 → 0.23 MiB | +0.65 |
| sparse fresh 10k | 1.38 → 2.31 MiB | +0.77 |
| sparse fresh 100k | 6.50 → 7.41 MiB | +0.13 |
| ring fresh 100k | 8.44 → 21.61 MiB | +1.06 |
| hub fresh 100k | 1.41 → 5.44 MiB | +2.42 |
| hub same 100k | 5.23 → 6.88 MiB | +0.29 |

The heap rule for the same workloads (C3) passes in every cell.

### 5.2 B4 `import-high`: descriptive REGRESSION, +408%

`B4-http-import-high-compact-bfs-sparse-10000` (10k nodes, 60% inactive and
30% disabled): 1.52 → 7.66 ms per import call, +408% [+384%, +432%] against
a 100% tolerance. It is descriptive by protocol (§4.1), and it stays a
REGRESSION as measured.
- **Baseline.** v0.6.0's frozen reference imports only the effective graph
  and copies a lean flag store. It does not validate the registered
  topology, cannot answer per-entry state, and cannot plan later lifecycle
  operations.
- **Contract compared.** The candidate keeps and validates the complete
  registered topology with flags, and publishes atomically with validation.
- **Capability-equivalent comparison** (deciding):
  `B4-http-import-high-equivalent-…`, 5.08 → 7.95 ms, +57.8%
  [+54.3%, +63.1%] against 100%: PASS.
- **History.** The descriptive overhead recurs from earlier releases:
  v0.5.0 +444.8%, v0.6.0 +419.9%, first v0.7.0 campaign +402.1%,
  re-qualification +413.3%.
- **Operational impact.** It is a per-import cost: about 6 ms more per
  10k-node import dominated by inactive entries, on the measured host. It
  is not on the query path. R measures flagged HTTP imports with 20%/10%
  and 60%/30% flags (10k and 100k nodes) 16–20% faster than v0.6.0.
- **Not a gate.** It is not turned retroactively into a new gate.

### 5.3 Other descriptive non-PASS results

`B4-http-ops-compact-bfs-sparse-100000` (frozen counterpart, descriptive):
3.78 → 4.59 ms, +19.9% [+17.3%, +25.7%] against 25%, INCONCLUSIVE. Its
deciding equivalent cell passes.

## 6. Applicability to the release commit

- The release branch `release/v0.7.0` is the candidate's commits rebased
  onto `origin/main` (`c75682d`).
- After that rebase, `main`'s dependency bump of `fixedbitset` (0.5.7 →
  0.5.9, a `knotrel-core` dependency) is reverted in `Cargo.lock`. The
  release builds the measured version.
- On the branch head `acc4582`, `crates/`, `Cargo.toml`, `Cargo.lock` and
  `rust-toolchain.toml` are identical to `fa5f3a9`:
  `git diff fa5f3a9 acc4582 -- crates Cargo.toml Cargo.lock rust-toolchain.toml`
  is empty.
- The other differences are documentation, CI workflow and test files from
  `main`, plus the release documentation.
- **Repeat the check on the final commit.** Merging into `main` can give
  the commit a new SHA, so the same `git diff` must be repeated against the
  final SHA on `main` before tagging.
- The `fixedbitset` bump is re-applied after the release.

## 7. Not claimed

- v0.7.0 is not claimed to be faster in general than v0.6.0.
- The two hub 10k requirements are not qualified.
- The accepted INCONCLUSIVE results are not PASS.
- Host-specific: Apple M3, macOS. No other platform was measured.
