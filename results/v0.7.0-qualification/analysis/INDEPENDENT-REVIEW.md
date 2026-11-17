# Independent review: COMPARISON-v0.6.0-v0.7.0.md

Report reviewed: `knotrel-benchmarks/results/v0.7.0-qualification/COMPARISON-v0.6.0-v0.7.0.md` (26,818 bytes, 2026-11-17 21:29).

Method: I recomputed every table value from the analysis JSONs and re-ran every analysis from the raw evidence into a scratch directory. I recomputed the host statistics from `logs/activity-monitor.jsonl` and the run logs, and checked the code claims with read-only `git diff`/`git show` in the knotrel worktree. I compared the cross-release M_desc rows against the v0.6.0 revision-1 and revision-2 analyses. Nothing was written to the evidence or results directories, and no cargo command was run.

Scratch outputs are in `/private/tmp/claude-501/-Users-rt-workspace-knotrel/a1cddd20-25d9-47d8-bd37-1419d4f1e1b4/scratchpad/review/` (`rerun/`, `mon.py`, `mon2.py`, `rwin.py`, `bcwin.py`, `mregwin.py`, `awin*.py`, `md.py`, `md6.py`, `bc.py`, `host.py`).

**Overall:** every verdict and every number in the result tables is correct, and all analyses reproduce byte for byte. The problems are in disclosure and wording:
- the host-activity disclosure is selective, and the report does not assess conformance (blocking);
- some summary wording overclaims;
- several factual claims are wrong: the startup tolerance and timer resolution, the mutation-test size, the "revision-1 defects did not apply" statement, and some load figures;
- disclosure sections the v0.6.0 precedent had are missing.

---

## Blocking

### B1. The host-activity disclosure covers only Chrome, and conformance to the chain's operator rule is not assessed

**Location:** §1 "Activity gate" and its Chrome table; §3, last bullets; §5 `ops` bullet; §8 item 11 ("The gate ran as declared …").

**Evidence:** `logs/activity-monitor.jsonl`, recomputed with `mon2.py`, `rwin.py` and `mregwin.py`. The frozen `run_final_chain.sh`, line 4, says: "The operator runs nothing else until it completes."

1. **Interactive activity during M_reg, 20:17:14–20:17:30Z.** In the same samples:
   - `GeminiAppLauncher` at 32–40%;
   - `Finder` at 86–98%;
   - two `com.apple.appkit.xpc.openAndSavePanelService` processes at 87–99% each;
   - `codesign` at up to 182%.

   That is roughly 3–4 cores of user-driven activity, typical of a file dialog. It falls in the M_reg cell `standalone-off-read95-b1-c4-10k`, where 34 of the 107 analyzed-observation samples had more than 30% from non-probe processes (cand 18, ref 16). The report never mentions it.
2. **WindowServer during the R toggle-churn cell.** The cell is INCONCLUSIVE and ran 19:56:42–19:56:52Z. WindowServer reached 37.6, 49.3, 52.7 and 32.9% at 19:56:42–46. The disturbed pairs coincide with it: analyzed pairs 02–05 were 106–163 ms in *both* arms, against about 80–90 ms in pairs 06–13 (`R/raw/*toggle*.stdout`). Pair 03 was 163.1 / 147.3 ms and pair 04 was 93.8 / 150.8 ms.

   The report says "No Chrome sample above 30% fell in the R window" and "The cause is not established". That is literally true but omits concurrent activity coinciding with the outlier pairs of the very cell it discusses.
3. **Other undisclosed processes:**
   - WindowServer: median 35% across A main (421 samples above 30%) and 28% across B/C (178 samples above 30%); up to 38.6% during the `ops` sparse 100k run;
   - Docker Desktop renderer: up to 80% during M_desc;
   - Claude desktop renderer: up to 77%;
   - two `claude-code` CLI processes (pids 32478 and 99641) were alive throughout.

   FREEZE.json `known_concurrent_activity` says another agent session "must be idle during the campaign". The report does not say whether it was.
4. **Precedent.** The v0.6.0 precedent (`supplement-M/REPORT-M-SUPPLEMENT.md` §2 and §7; comparison §9) classified concurrent automated activity as "Protocol conformance: not met" and did not propose that run's results for acceptance. The v0.7.0 report instead frames all of this as a Chrome-only disclosure: "the gate ran as declared". The gate's pattern was met, but the operator rule was not evaluated.

**Suggested correction:**
- Add a conformance subsection, as in the precedent. Quote the operator rule from `run_final_chain.sh` and list every non-gated process above 30%, with times and the affected experiment and cell. At minimum include:
  - the 20:17:14–30Z burst during M_reg `read95-b1-c4-10k`;
  - WindowServer during R toggle churn, pairs 02–05;
  - Docker Desktop during M_desc;
  - the second Claude Code process.
- State conformance as **not met** for the operator rule (or "undetermined", with reasons), and say whether the FREEZE condition on the other agent session was met.
- Replace "The cells reported non-PASS in R and B/C had no such sample" with a statement covering all processes. For R toggle churn: "WindowServer at 33–53% coincided with analyzed pairs 02–05, which are inflated in both arms."

---

## Should-fix

### S1. "All of them run query-only batches" is false

**Location:** §1 Contention bullet ("4 cells are IMPROVED; all of them run query-only batches"). Related wording: §1 M5 bullet ("no longer holds for query-only batches"), §7 heading "Query-only scaling (… read95 batch 1)", and §7 "because such batches usually contain a mutation".

**Evidence:**
- `tools/contention-probe/src/main.rs` lines 287–296 draw a 5% mutation per operation for `read95`.
- Of the four IMPROVED cells, `read95` batch 8 has about 34% of batches with a mutation (1 − 0.95⁸, as §6 itself says). `read95` batch 1 at 10k has 5% mutation requests. Only the two `read100` cells are query-only.
- For batch 8, 34% is not "usually".

**Suggested correction:**
- §1: "4 cells are IMPROVED: the two `read100` cells are query-only; in the two `read95` cells most requests are query-only (66% of batch-8 batches, 95% of batch-1 requests)."
- §7: rename the heading to "Mostly-query scaling (read95, batch 1)".
- §7: write "batch-64 batches almost always contain a mutation (96%); batch-8 batches do in about 34% of cases and wait behind those that do."

### S2. HTTP startup: wrong tolerance and wrong resolution claim

**Location:**
- §2 startup row ("4 → 4 ms");
- §2 "Startup-to-ready is recorded at millisecond resolution (4 ms in both arms)";
- §8 item 8: "Startup time undetermined within ±25%" and "Millisecond resolution (4 ms both arms)".

**Evidence:**
- `A-final-decision-analysis.json`, cell `http_lifecycle_compact_bfs_small`: `primary_tolerance_pct` = 10, not 25.
- B_median = 4.1189 ms and C_median = 4.0366 ms. Raw pair values have microsecond resolution (for example 3.27275 vs 4.348792 ms).
- The v0.6.0 precedent printed 4.37 → 4.57 ms.
- The INCONCLUSIVE comes from the upper bound, +10.47%, exceeding 10%.

**Suggested correction:**
- Print "4.119 → 4.037 ms".
- Delete the millisecond-resolution sentence, or replace it with "the paired interval is wide (−22.02, +10.47)".
- §8 item 8: "upper bound +10.47% against the 10% primary tolerance".

### S3. Mutation-test size misstated

**Location:** §9 ("a 77-case corpus and 50,000 seeded mutations").

**Evidence:** `git show e75ff6a:crates/knotrel-server/src/api.rs`:
- line 2023 is `for i in 0..20_000`, in `import_fast_parser_matches_serde_json_under_mutation`;
- there is no other sonic-rs mutation test;
- the 77-case corpus count is correct (37 + 1 + 12 + 5 + 1 + 14 + 2 + 2 + 1 + 2).

Both tests compare `sonic_rs` and `serde_json` on acceptance and decoded value. Error-path classification is unchanged: bodies both parsers reject still go to the `simd_json` fallback.

**Suggested correction:** write "20,000 seeded mutations". Describe the tests as accept/decode parity with `serde_json`, and say the error-path classification is the unchanged `simd_json` fallback.

### S4. M_desc cross-release comparison: the "revision-1 defects did not apply" claim is false, and other provenance is incomplete

**Location:** §7 intro ("revision 1 for standalone `read95` with no background work, where the revision-1 defects did not apply"); §7 scaling table, batch-64 table and open-loop bullet; §1 M5 "In v0.6.0 it held in 32 of 32".

**Evidence:**
- **Node limit at 100k.** In revision 1 (`git show 7979c491:tools/contention-probe/src/main.rs`, lines 611–619), `read95` toggles use the same client-owned extra edges as `mixed50`, with `base = n + 1_000_000*(client+1)`. No `KNOTREL_MAX_NODES` override was set. So at 100k every `read95` link failed with `node_limit_exceeded` and its cuts were no-ops, the same defect v0.6.0 §7 recorded for `mixed50`.
- **Off-by-one and carry-over.** These revision-1 defects apply at both sizes. The 12 `read95` configurations share a server and reuse the same IDs (fixed by the `+ 256 * ordinal` change in revision 2).
- **Affected rows.** All v0.6.0 rows the report uses for standalone `read95` come from revision 1: batch 1, batch 64, and the open-loop rows, which are also `read95`. The `read100` source-managed rows are unaffected.
- **Revision-2 rows from the non-conforming run.** The 10k source-managed v0.6.0 figure ("about 1,960") comes from `S-source-{off,on}-10k`. Those are the children during which the git fetches were recorded (REPORT-M-SUPPLEMENT §7.2).
- **Frozen v0.6.0 campaign.** Its own conformance is "undetermined" in the precedent (§9).
- **Calibration available.** The v0.7.0 M_reg reference arm runs the v0.6.0 server under revision 2 and gives 208.5 req/s and p99 91.9 ms for `read95` b8 c16 100k. Revision 1 gave 205.3 req/s and p99 90.6 ms. The workload effect at that configuration therefore looks small, because the extra edges are isolated pairs and their link/cut is cheap. The claim itself is still incorrect.

Rows used, all checked against the source files:

| Figure | v0.6.0 source | Revision |
|---|---|---|
| read95 b1 16/64 clients (1,561, p99 17.2, lock 0.93; 1,344, p99 50.7, lock 0.96) | v0.6.0 `analysis/Mdesc-analysis.json` | 1 |
| 15,120 at 10k | same | 1 |
| read95 b64 p99 635 / 636 / 145 / 147 / 2,071 / 3,946 ms; 26 req/s | same | 1 |
| Open loop 103 / 185 / 226 req/s, p99 24 / 26 / 514 ms | same | 1 |
| source-managed read100 b8 100k on, 16 clients: 204 | `supplement-M/analysis/Mdesc-supplement-analysis.json` | 2 |
| about 1,960 at 10k | same (fetch-affected children) | 2 |
| Catch-up 39,360 / 3,648 / 448; off 3,520; query p99 91.4 ms | same | 2 |

**Suggested correction:**
- Replace the claim with: "revision 1 for standalone `read95`. Its 5% toggles were rejected at 100k (node limit) and partly no-ops at both sizes (carry-over, off-by-one), so the v0.6.0 rows ran a slightly cheaper mutation mix."
- Cite the M_reg reference-arm calibration.
- Note that the 10k revision-2 rows come from the fetch-affected children.
- Apply the same caveat to the batch-64 observation and the open-loop rows.

### S5. The closest paired evidence for the batch-64 tail observation is omitted, and §1 omits a confirmed p99 increase

**Location:** §7 batch-64 observation ("The paired M_reg cell closest to them (mixed50 batch 64) is p99 +0.09%"); §8 item 10; §1 Contention bullet.

**Evidence:** `Mreg-analysis.json`, `Mreg-standalone-off-read95-b8-c16-100k-none`, `latency_ns.p99`: +5.38% [+0.16, +11.16]. The whole interval is above zero.
- This cell mixes mutation-bearing batches with query-only batches, which is the setting of the mechanism §8 item 10 proposes.
- `mixed50` b64 almost never has query-only batches, so it is not the closest analog.
- The v0.6.0 precedent flagged comparable within-tolerance but consistent degradations explicitly: §6 called the 10k batch-1 cell "slightly but consistently slower", and the rerun recorded "a confirmed small degradation within tolerance".

**Suggested correction:**
- Cite `read95` b8 p99 +5.38% [+0.16, +11.16] as the closest paired evidence in §7 and §8 item 10.
- Add to §1: "read95 batch 8 client p99 rose +5.4% (interval entirely above zero, within the 25% tolerance)."

### S6. The 64-client catch-up "13×" uses a figure the precedent declared a probe artifact

**Location:** §7 feeder table, 64-client row (448 → 5,952, "13×").

**Evidence:**
- REPORT-M-SUPPLEMENT §4.1: "The 64-client feeder numbers are an artifact of the probe … say nothing about catch-up under any realistic client retry policy."
- v0.7.0 `Mdesc-analysis.json`, `M-source-on-100k` `read100-b8-c64-events`: the feeder was still refused 115 times (`refused_503`), and queries got 99,929 refusals.

**Suggested correction:** drop the ratio or mark the row "admission-race artifact, see v0.6.0 REPORT-M-SUPPLEMENT §4.1".

### S7. Frozen-protocol wording discrepancies are not disclosed (v0.6.0 §1 precedent)

**Location:** §1. The v0.6.0 report had a "Wording in the frozen protocol" block; v0.7.0 has none.

**Evidence:**
- **Activity gate.** `MATRIX.json` `host_conditions.activity` requires the gate "before every child". Only R, Rmem and M children are gated: `run_p0_aa.py` (A) and `run_lifecycle_qualification.py` (B/C) contain no activity check. The report's sentence is accurate, but the matrix discrepancy is not stated.
- **Power and thermal.** `host_conditions` power/thermal say "before every cell". A checks per session; M_desc checks per server process (38 checks for 162 configurations).
- **Order seed.** `MATRIX.json` `rules.R` says "order seed 60500", but `experiments.R.order_seed` = 60700. The collector uses 60700 (`run_v060_qualification.py:163`).
- **Server count.** The protocol and matrix say 36 server processes for M_desc. The run had 38 (36 plus 2 open-loop servers, `Mdesc/run-log.json`). The report's "across 36 fresh server processes" for all 162 rows is therefore wrong.

**Suggested correction:** add a "Wording in the frozen protocol (unchanged, noted here)" block listing these four items, and write "38 server processes (36 + 2 open-loop)".

---

## Minor

**M1. Load-average figures (§1).**
- "A sessions started at 1.51 and 1.64": those are the collectors' initial host states. The six session pre-checks were 1.70, 2.36, 1.52, 1.66, 1.69 and 1.28 (`A/*/run_metadata.json` `session_host_states`).
- "R/Rmem at 2.26–3.10": R was 2.53–3.10 and Rmem 2.49–2.53 (2.26 is the M_reg minimum).
- "The high values are the load left by the preceding 64-client configuration": true for M_desc. M_reg has no 64-client configurations, and its maximum (22.93) occurred in its own 16-client `source-managed` import cell (median 6.1).

**M2. Activity-monitor description (§1).**
- The gate pattern was checked on the full process table 14,620 times (`stop` record), with zero `match` records. The 3,246 records are the per-second top-5 lists.
- The Chrome table counts the *sum* over Chrome processes per sample, and `ps` %cpu on macOS is a decaying average. Say so.
- The impact on A can be quantified rather than left open. No A observation (312 observations, 41.7 s of measurement in a 25.7-min span) lies within 5 s of a Chrome sample above 30% (`awin.py`, `awin2.py`). The A rows of the table count samples between observations.
- The per-child gate result is not logged; "passed" is inferred from the absence of a `stopped` record.

**M3.** §7 says "Each figure below is one 3-second window". Import configurations use a 5-second window (`Mdesc/*.configs.jsonl`, `measure_ms` 5000).

**M4.** §5 says "The lifecycle-on path takes the graph lock exclusively in both arms". The reference arm is lifecycle-off; both arms send mutation-only batches (`http-lifecycle.rs` scenario `ops`), so both are exclusive. Reword accordingly.

**M5.** §3 says "The upper bound exceeds 10% only through the interval's upper end". That is a tautology; give the ratio of arm medians (+5.13%) instead.

**M6. Lockfiles.** §3 and §8 item 5 say the binaries were "built from different lockfiles". `logs/ref-probes-lock-derivation.diff` only removes the sonic-rs dependency tree and changes the knotrel versions. `knotrel-core`'s dependencies (rustc-hash, nohash-hasher, fixedbitset, tinyvec) are identical. Say so: it narrows the likely cause to codegen/LTO or noise.

**M7.** §8 item 4 says "no code change on the metrics path". `metrics.rs` changed (46 lines) to generalize lock timing to `RwLock`. The metrics *recording* logic is unchanged.

**M8. Checksum coverage.**
- `R/`, `Rmem/`, `Mdesc/` and `Mreg/analysis.json` were written into the evidence tree after `outputs-sha256.txt` (21:24 vs 21:22) and are not listed. They match the results copies.
- v0.6.0 had `inputs-sha256.txt` covering the lock-derivation diffs; v0.7.0 has no equivalent.

**M9.** The import-overlap bullet omits that the import p50 at 100k, 64 clients, lifecycle on rose from 448 to 761 ms (single windows; v0.6.0 revision 2 vs v0.7.0). It fell at 16 clients (208–214 → 149–163 ms).

**M10.** §8 item 11, "Every A cell passed except the two repeats; every M_reg cell passed": passing is weak evidence of no disturbance. Prefer the overlap analysis in M2.

**M11.** v0.6.0 §3 reported the fresh-ID churn slowest operation; v0.7.0 omits it. The values are in `R-analysis.json`: sparse 18.62 → 18.96 ms, hub 16.82 → 16.71 ms. Optional.

---

## Verified correct

**Reproducibility.** Every re-run analysis is byte-identical to the published file:
- R, Rmem, M_desc and M_reg via `analyze_v070_qualification.py`;
- A via `analyze_bc_qualification.py --rules v0.4.0` (main + extension);
- B/C via `analyze_lifecycle_qualification.py`, with probes rev `4c03cf7b` and multipliers sha `130c35bb…`.

The scripts are unchanged since the freeze.

**Checksums.**
- All 14,780 entries of `outputs-sha256.txt` verify OK, and the file is identical to `logs/outputs-sha256.txt`.
- `analysis-sha256.txt` verifies.
- All 13 binaries verify, and every sha in the §1 table and the bullets matches.
- MATRIX, PROTOCOL and FREEZE hashes match FREEZE.json and the run-log metadata.
- The `chain-steps`, `prelaunch-host` and `SETUP-DEVIATION` copies are identical to the evidence versions.

**Identities.**
- `v0.6.0` tag → `5db9ec4`; benchmarks `v0.6.0` → `bddef0f3`.
- The freeze commit adds only FREEZE.json.
- The source clones are at `e75ff6a` and `5db9ec4`.

**§2 (A).** All nine rows match the JSON: medians, paired changes, intervals, pair counts, supporting metrics and statuses. The rest also checks out:
- 7 / 1 / 1 split;
- the four extension cells;
- the INCONCLUSIVE_DISCLOSED and UNRESOLVED logic under the v0.4.0 rules;
- the v0.6.0 comparison: 5 / 2 / 2, batch-1 p99 UNRESOLVED a third time, startup INCONCLUSIVE_DISCLOSED again, `compact-workspace` and batch-256 now pass.

**§3 (R).** All 11 rows match, including the IMPROVED flags (interval upper bound below zero), the "0.27 points", the +4.8% ratio, the "0.86 points" and the 17–21% range. The arms are balanced 6/6 per cell.

**§4 (Rmem).** All 10 cells are byte-identical between arms (change 0.0%), and the MiB figures are correct.

**§5 (B/C).** Every figure checks out:
- 58 / 1 / 2 against v0.6.0's 59 / 1 / 1;
- B5 2.45× and 2.44×;
- C1 and C2 all PASS, maximum 95,000 retired slots;
- C3: 3 FAIL with values identical to v0.6.0;
- C4: 9 / 6, with `sparse-same-1000` and `sparse-toggle-1000` now passing;
- all five detail rows and the v0.6.0 comparisons;
- `ops` sparse 100k: 9.753 s run, no Chrome sample above 30% (maximum 4%).

**§6 (M_reg).** All six cells match, with reference → candidate printed correctly for both throughput (JSON B = candidate) and p99 (JSON B = reference). Also verified:
- every verdict;
- all analyzed observations valid, only status 200;
- arms balanced 6/6;
- "throughput rises 67%" (349.2 / 208.5) and 1 − 0.95⁸ ≈ 34%.

**§7 (M_desc), descriptive numbers.**
- 162 rows, 0 invalid;
- M5: 16 of 32, with lock shares 0.87–0.97, 0.20–0.49 and 0.00;
- v0.7.0 throughputs, p99s, catch-up counts and lock share 0.48;
- import throughput ranges 944–985 and 809–1,018;
- batch-64 p99 table;
- open-loop rates and p99s;
- every v0.6.0 figure matches its source row (table in S4).

**§8 completeness.** Every non-PASS result appears in §8, and none is misclassified: A ×2, R ×2, B4 ×3, C3 ×3, C4 ×6, M_reg none, Rmem none, no TIMER_LIMITED cells.

**Code claims.**
- `git diff 5db9ec4 e75ff6a -- crates/knotrel-core` is empty, and core's dependency versions are unchanged.
- A batch with any mutation runs the exclusive path: `execute` → `run`; only `as_query`-all batches and stats use `run_read`.
- Both B/C arms are in-process on the candidate `knotrel-server`.
- `release-cells` and `memory-peak` link `knotrel-server` and use the real router.
- The 77-case corpus count is correct.

**Host.**
- 661 collected children (BC 127, R 308, Rmem 20, M_desc 38, M_reg 168), all on AC power, no thermal or performance warning, every exit 0.
- All 312 A observations exited 0 with status `parsed_valid`.
- B/C load 1.34–2.68; M children 2.26–24.0; launch load 1.51.
- Campaign 19:22:21–20:22:30Z (60.2 min), with correct per-experiment durations.
- Chrome table: 39/766, 11, 219%; 5/758, 0, 67%; 3/373, 0, 83%; R/Rmem 0, max 25%; 39/598, 2, 197%; 29/670, 6, 166%. All match when Chrome processes are summed per sample.
- Zero gate-pattern matches.
- Tooling clone untracked `activity-monitor.jsonl` (B/C provenance).
