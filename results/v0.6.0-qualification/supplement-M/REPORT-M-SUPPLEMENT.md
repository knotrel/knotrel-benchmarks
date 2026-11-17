# v0.6.0 supplementary contention run (M supplement): report

**SUPPLEMENTARY, WITH A PROTOCOL NON-CONFORMITY (§7).** An automated
process ran `git fetch` during measured children, against the protocol's
"Nothing else runs during measurement". The run is kept as evidence with
limitations, and acceptance of its results is **not** recommended. The
minimal rerun of the two M_reg cells has since run, conforming to its
declared rules; both cells PASS
([`rerun-Mreg/REPORT-MREG-RERUN.md`](rerun-Mreg/REPORT-MREG-RERUN.md)).

This run does not replace, re-classify or extend any result
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

## 2. Validity, classified

"Valid" in this report refers only to the first two levels below. It never
means protocol conformance, which is level 3 and is **not met** (§7).

| Level | Status | Basis |
|---|---|---|
| 1. Functional correctness of the probe | **Shown, with limits** | Zero transport errors, per-item errors and no-op mutations; zero background failures. The no-op detector has a positive control. The `item_errors` detector rests on code reading. Feeder per-event results are not inspected (§3). |
| 2. Validity of the analyzer inputs | **Met** | All 60 M_desc records and 48 analyzed M_reg observations satisfy the declared validity rule (protocol §5). All children exited 0. Every start record has probe revision 2. Server and probe hashes are verified, and outputs match `logs/outputs-sha256.txt`. |
| 3. Conformance of the run to the protocol | **Not met for M_desc, undetermined for M_reg** | §7 |

At level 2, the declared rule requires:
- no transport or batch-shape errors;
- no per-item error results and no no-op mutations;
- every background activity completed work with zero failures.

The run had no `node_limit_exceeded`, no failed import and no stopped feeder.
The only refusals were 503 admission refusals at 64 clients, which the rule
allows. Query-client refusals per 64-client configuration (all in
`analysis/Mdesc-supplement-analysis.json`, field `statuses`):
- about 288,000–303,000 with no background or with feeder events;
- about 479,000–496,000 with import (6 s window);
- 282,000–307,000 for `mixed50`.

The probe counts every refused attempt: refused query clients resend
immediately (closed loop).

## 3. M_reg supplement against v0.5.0 (12 analyzed pairs, fresh server per observation)

| Cell (100k, 16 clients) | Throughput v0.5.0 → v0.6.0 | Change [interval] | Client p99 v0.5.0 → v0.6.0 | Change [interval] | Supplementary outcome |
|---|---|---|---|---|---|
| standalone, lifecycle off, `mixed50`, batch 64, effective toggles | 50.33 → 50.00 req/s | **−0.33%** [−1.32, +1.34] | 351.1 → 359.9 ms | **+1.98%** [−1.62, +5.36] | PASS (analyzer) |
| source-managed, lifecycle on, `read100`, batch 8, feeder catch-up | 200.83 → 199.33 req/s | **−1.00%** [−4.04, +1.16] | 92.0 → 94.8 ms | **+3.86%** [−1.63, +9.41] | PASS (analyzer) |

**How the numbers are computed** (frozen `summarize_metric`, unchanged):
- **Per pair.** Pair *i* (one v0.5.0 and one v0.6.0 observation, each on a
  fresh server, order balanced) gives one value per arm:
  - throughput: completed requests in the 3 s window divided by 3;
  - latency: client p99 of that observation.
- **Changes in the table.** They are always v0.6.0 against v0.5.0:
  - *d_i = ln(v0.6.0_i / v0.5.0_i)*;
  - the change shown is *exp(median d_i) − 1*;
  - the interval is *[exp(d₍₃₎) − 1, exp(d₍₁₀₎) − 1]*, order statistics of
    the 12 sorted *d_i*.
- **Reading the signs.**
  - A negative throughput change means **v0.6.0 completed fewer requests**:
    −0.33% and −1.00% are small decreases, not speedups.
  - A positive p99 change means v0.6.0's tail is longer.
- **How the analyzer decides.** The verdict is computed on the orientation in
  which positive means worse:
  - throughput uses *ln(v0.5.0/v0.6.0)*, which `analysis.json` stores as
    +0.33% [−1.33, +1.32] and +1.01% [−1.15, +4.21];
  - p99 uses *ln(v0.6.0/v0.5.0)*.
  - PASS requires the upper bound to be at most ln(1.10) for throughput and
    ln(1.25) for p99. Both cells meet it, and neither interval excludes zero.
  - In `analysis.json`, for throughput, `B_median` holds v0.6.0 and
    `C_median` holds v0.5.0.
- **Why the medians shown can disagree with the change.** The values in the
  "v0.5.0 → v0.6.0" columns are separate medians of each arm. The change is
  the median of the paired ratios, which is a different statistic.
  - mixed50 throughput: ratio of arm medians −0.66%, paired −0.33%;
  - events throughput: −0.75% against −1.00%;
  - p99: +2.50% against +1.98%, and +3.08% against +3.86%.
- **Throughput resolution.** It is quantized: a window completes an integer
  number of requests, so at about 50 req/s one request is 0.67%.

Notes:
- In every observation of the second cell, the feeder's event batches were
  accepted (HTTP 200) with zero failures: 3,328–3,648 events per observation
  on the candidate and 3,520–3,712 on v0.5.0. The probe does not inspect
  per-event results (`applied`, `unchanged`, `duplicate`). The feeder uses
  fresh IDs and an advancing delivery sequence, so non-applied events are
  unlikely, but they were not checked.
- Frozen outcomes stay unchanged:
  - the `mixed50` cell: **PASS †**, which measured rejected links;
  - the events cell: **invalid for its purpose**.

## 4. M_desc supplement (candidate, descriptive, one observation per configuration; conformance in §7)

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
| 100k, on | 16 | 204.7 | 91.4 ms | 3,648 | 0 | 78.7 / 91.1 ms |
| 100k, on | 64 | 162.7 | 244.3 ms | 448 | 303 | 0.1 / 190.2 ms |
| 10k, off / on | 64 | 1,855 / 1,839 | 22.2 / 32.8 ms | 15,552 / 15,488 | 313 / 306 | 0.1 / 18.8 and 17.4 ms |

What this shows:
- **With 16 clients, the feeder queues behind queries for the single graph
  lock.** At 100k, query batches hold the lock about 5 ms each (about 196
  serialized batches/s). A 64-event feeder batch waits behind the queued
  query batches, about one round of 16 (feeder batch p50 about 80 ms, close to
  one client's latency). Catch-up therefore falls to about 900 events/s from
  about 7,000 (lifecycle off) or 9,800 (lifecycle on) with 4 clients. The
  server gives feeder work no priority over queued queries.
- **The 64-client feeder numbers are an artifact of the probe and are not
  server characteristics.**
  - Queries hold all 32 admission permits, and the feeder is refused with
    `503 import_in_progress` (documented admission behavior).
  - Refused query clients resend immediately, with no backoff (about 300,000
    refused attempts per configuration). The feeder sleeps 10 ms after each
    refusal: 303–313 refusals, about 3 s of a 4 s run.
  - The low catch-up (about 120 events/s at 100k) therefore mostly measures
    the feeder losing a permit race against hot-spinning clients.
  - What it shows is that admission has no reservation for feeder requests.
    It says nothing about catch-up under any realistic client retry policy.
- These properties are relevant to v0.7.0 and to the supported-envelope work
  (v1.0 readiness criterion 4). They are not defects of v0.6.0's contract.

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

- **Caveats for any comparison with the frozen rows:**
  - Each row is a single observation.
  - The supplement's `mixed50` servers start fresh. The frozen ones had
    first run 12 `read95` configurations on the same process.
  - The frozen rows measured rejected links and no-op cuts.
- **With 1 to 16 clients and batch 1 or 8,** throughput and p99 are within
  about 6% of the frozen rows (lifecycle on, b8-c16: −4.2% req/s, p99 +6%).
- **Larger differences:**
  - lifecycle on, b8-c64: 291.0 against 334.7 req/s (−13%), p99 202.1
    against 168.3 ms (+20%);
  - lifecycle on, b1-c64: −7.6% req/s;
  - lifecycle off, b1-c64: p99 −10%;
  - lifecycle on, b64-c16: p99 418.7 against 362.3 ms (+16%).
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
  measure as declared now have supplementary measurements with valid
  analyzer inputs (levels 1–2 of §2). The run does **not** conform to its
  protocol (§7):
  - Both M_reg cells come out PASS from the analyzer, but they are not
    proposed for acceptance.
  - Feeder catch-up and import overlap are covered descriptively at both
    sizes and all client counts. The 10k source-managed servers
    (`S-source-{off,on}-10k`) ran while a fetch was recorded, and all rows
    are single observations.
- **Frozen results.** The frozen verdicts and the frozen coverage-defect
  record are not changed.
- **New descriptive findings** for v0.7.0 and the envelope work:
  - The feeder has no priority over queued queries: at 100k, catch-up slows
    by 8–11× from 4 to 16 clients. Admission reserves nothing for feeder
    requests; the 64-client catch-up numbers are a probe artifact (§4.1).
  - At 10k with 16 clients and lifecycle off, one high query p99 coincided
    with import overlap (single observation).
- **M5 rule (i)** was not re-evaluated, as declared; its configurations were
  not affected by the defects. Note that `analysis.json` contains an
  `m5_rule_i` block that the reused analyzer computes automatically over the
  supplement's rows. It is not part of this supplement's results.

## 6. Disclosures and limitations

- **Automated git activity.** The facts, timeline and impact are in §7.
  An earlier version of this section attributed the fetches to Visual Studio
  Code. That attribution was unproven and is withdrawn.
- **Probe limitations (none triggered in this run):**
  - The validity counters cover only the measure window.
  - A client transport error drops the batch body instead of resending it.
    Errors were 0 everywhere.
  - A non-200 analyzed M_reg observation would abort the reused frozen
    analyzer instead of marking only its cell INVALID.
  - **Positive control of `noop_mutations`.** Outputs from an earlier probe
    iteration, kept after the run in
    `evidence/v0.6.0-diagnostics/m-supplement-functional-check/positive-control-earlier-iteration/`,
    show the no-op detector firing on the revision-1 defects:
    - 9–10 no-ops at b64-c16;
    - 465–468 at b1-c64.
  - **No positive control of `item_errors`.** None is preserved. The
    detector's correctness rests on code reading of the documented
    `{"result":"error","code":…}` shape.

## 7. Protocol conformance (concurrent activity)

### 7.1 The rules

- **Machine-checked rule** (`MATRIX-M-SUPPLEMENT.json` `host_conditions`,
  copied from the frozen matrix):
  - No `cargo`/`rustc` process and no other campaign.
  - The collector checks it before each experiment with
    `pgrep cargo|rustc`; power and thermal state are checked before every
    child.
  - It was met.
- **Operator rule** (`PROTOCOL-M-SUPPLEMENT.md` §4, host prerequisites):
  - "Nothing else runs during measurement."
  - It is not machine-checked.
  - The invalidation rules (code change, tooling change, failed child,
    invalid runs) attach no stated consequence to it.
  - It is the rule at issue.

### 7.2 What the evidence shows

**Integrity of sources, binaries and results: intact.**
- Every evidence clone has a detached HEAD at its recorded commit and no
  tracked changes.
- Server binaries verify against the frozen campaign's checksums, and the
  probe's hash matches its build.
- All outputs verify against `logs/outputs-sha256.txt`.
- The automated fetches changed only `.git` metadata: remote refs,
  `FETCH_HEAD`, new objects and reflogs.

**Measurement conditions: not met for M_desc, undetermined for M_reg.** The
evidence comes from the remote-tracking reflogs (`core.logAllRefUpdates`) of
the clones, scanned without following symlinks.
- **Ref-updating fetches inside measured M_desc children:**
  - 06:25:54Z, `src/cand/knotrel-benchmarks`;
  - 06:25:55Z, `src/ref/knotrel-benchmarks`;
  - 06:26:06Z, `A/sources/knotrel-benchmarks`.
  - Each moved `origin/feature/v0.6.0-qualification` 04cb25d7 → 8faf37bb,
    picking up the freeze commit made at 06:23:21Z.
  - They fall inside children `00003-S-source-off-10k` and
    `00004-S-source-on-10k`.
  - A `git fetch` process therefore ran and wrote objects while the run was
    measuring. **The operator rule was violated during M_desc.**
- **M_reg (06:28:11–06:32:14Z):**
  - No ref-updating fetch is recorded.
  - No commit existed between 06:23:21Z and 06:33:37Z, so any fetch in that
    window would have updated no ref. It would have left only `FETCH_HEAD`,
    which every later fetch overwrites.
  - Fetches are observed every 2–3 minutes, by ref updates and by current
    `FETCH_HEAD` times (for example 07:35:39 and 07:38:39 +0100). That
    cadence makes fetches during M_reg likely, but neither their presence
    nor their absence can be shown. **Conformance for M_reg is
    undetermined.**
- **Frozen campaign (22:50–23:50Z on 2026-11-16):**
  - No commit was made during it, so the same method cannot detect fetches
    there either.
  - The fetching process (see below) had been running since 2026-11-14
    21:31Z.
  - Conformance of the frozen campaign to the user's instruction "no
    concurrent activity during measurement" is therefore also undetermined.
  - Its machine-checked rule, no concurrent build or campaign, was met.
  - Nothing in sections 1–8 of the comparison changes. This is an evidence
    limitation for the maintainer.
- **Load average.** The recorded 1-minute load average ranged from 2.08 to
  6.95 across children. It includes the probe's own client threads and
  servers, so it cannot isolate other activity.

**Attribution, shown live after the run and not for the past.**
- A passive 250-second poll of the process table, 2026-11-17 06:53–06:57Z,
  recorded `git fetch` processes whose parent is PID 5603,
  `Antigravity IDE Helper (Plugin)`, started 2026-11-14 22:31 local time.
- They ran in repositories all over `/Users/rt/workspace/knotrel`, including
  `evidence/` clones, and included HTTPS fetches from `github.com` for the
  main clones.
- Record: `evidence/v0.6.0-diagnostics/m-supplement-host-activity/`.
- That this same process caused the 06:25–06:26Z fetches is a strong
  inference: same cadence, same repositories, and it was the only fetching
  process observed. It is not proven.

**Possible performance impact: not quantified, and not assumed to be zero.**
A fetch is a short burst of process creation, CPU, disk writes and, for
remote clones, network I/O, on the same machine as the probe and server. Its
effect on the affected observations was not measured, and modifying only Git
metadata says nothing about the CPU and I/O it consumed.

### 7.3 Recommendation (single)

Conformance is violated for M_desc and undetermined for M_reg, so:
- **Keep this supplement as evidence with limitations.** Do not propose its
  two M_reg PASS results for acceptance.
- **Rerun only the two M_reg cells**, with the same statistical protocol
  (2 warmup and 12 analyzed pairs, same tolerances and analyzer), the same
  frozen probe revision 2 binary and the same server binaries.
  - The rerun's preparation is in [`rerun-Mreg/`](rerun-Mreg/), including how
    automated activity is removed and how its absence is verified.
  - The 60 descriptive configurations are not repeated.
  - The rerun is **not started**.
- **Scope of the supplementary results.** The supplementary PASS results,
  from this run or from the rerun, never replace frozen verdicts
  automatically, and they close no other non-PASS item.

