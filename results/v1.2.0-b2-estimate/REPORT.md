# B2 bounded concurrent query execution: impact estimate result (knotrel#87)

**Kind.** Impact estimate under the per-release measurement policy (knotrel#186). It decides
adoption only. The v1.2.0 release verdict, Q3 included, belongs to knotrel#182, on a
defined candidate.

| | |
|---|---|
| **Design** | knotrel `docs/design/b2-bounded-query-concurrency.md`, approved by the maintainer and recorded before implementation and measurement (f204d03, merged in knotrel#206; SHA-256 `83144805…a691f9`) |
| **Approved choices** | Q5 option **B** (deciding in the default mode; with K = 4 computed and published as the operational cost); a single opt-in value **K = 4**; a 2 h budget |
| **Candidate** | knotrel#207 at 2fd8293 (CI: 37 pass, 1 skipped) |
| **Reference** | v1.1.0 57c35e8: the in-session Q5 reference server of each run |
| **Freeze** | `FREEZE.json` (653b9d69), tooling ee80cfe4 |
| **Procedure** | the frozen block-Q procedure (`run_v100q_q.py`: 3 rounds, seven cells, 2,700 s cap; `evaluate_v100q_q.py` as fixed in #60), once per mode |
| **Mode `off`** | the B2 build, setting unset |
| **Mode `on`** | the same binary, started through a wrapper with `KNOTREL_MAX_CONCURRENT_QUERIES=4`. The load tool clears the server environment, so the setting has to travel with the executable. Its activation was checked through the limiter metrics before the run; it is absent in `off` |
| **Host** | Apple M3, 8 CPUs, AC power, `caffeinate`, PostgreSQL 18.7 container only inside each run. Swap-ins and swap-outs 0 before and after both runs (`host-*.txt`) |
| **Window** | off 18:33–19:01 UTC, on 19:01–19:29 UTC: 56 min of the 2 h cap. Both runs `COMPLETE` |

## Outcome: **ADOPT** under the approved rule

| Mode | Q1 | Q2 | Q3 | Q4 | Q5 against v1.1.0 |
|---|---|---|---|---|---|
| `off` (default) | PASS | PASS | FAIL (reported) | PASS | **PASS** (deciding) |
| `on` (K = 4) | PASS | PASS | **PASS**: C=16 56.3 % (≥ 50 %), C=64 55.0 % (≥ 25 %) | PASS | FAIL on throughput, PASS on p99: the published operational cost, not deciding (option B) |

- The default mode does not regress.
- The opt-in mode passes Q3 under the unchanged thresholds: the first Q3 PASS for
  `compact-bfs`.

## Side by side (medians of 3 observations; client p99 is end to end, including the wait for the limiter permit and admission)

### Feeder catch-up (L2 G100k, backlog of 100,000 changes)

| | `off` | `on` (K = 4) | on / off |
|---|---|---|---|
| Events/s, no query load (C=0) | 179,889 | 176,842 | 0.98 |
| Events/s, C=16 | 29,125 | **99,475** | **3.42×** |
| Share kept, C=16 | 16.2 % | **56.3 %** | +40.1 points |
| Events/s, C=64 | 15,966 | **97,258** | **6.09×** |
| Share kept, C=64 | 8.9 % | **55.0 %** | +46.1 points |
| Host CPU busy during C=16 / C=64 | 93.5 % / 95.9 % | 57.6 % / 58.2 % | — |
| Feeder 503 refusals | 0 | 0 | — |

**Summary quantities (design section 5).**
- **Feeder recovery against `off` at C=16:** +247 %, i.e. 3.47× the share.
- **Distance from the Q3 threshold at C=16:** **+6.3 points** (56.3 % against 50 %). At
  C=64 the share is 55.0 % against 25 %.
- The historical reference of the restored query path, 15 % (#181 base), is consistent
  with the `off` value, 16.2 %.

### Queries during catch-up (L2 G100k)

| | `off` | `on` (K = 4) | on / off |
|---|---|---|---|
| Throughput C=16 (req/s) | 1,418.8 | 783.1 | 0.55 |
| Client p99 C=16 | 57.5 ms | 60.8 ms | 1.06 |
| Throughput C=64 (req/s) | 1,442.7 | 789.2 | 0.55 |
| Client p99 C=64 | 97.2 ms | 96.8 ms | 1.00 |
| Query 503 refusals C=16 / C=64 | 0 / 18,997 | 0 / 1,586 | — |
| Query errors | 0 | 0 | — |

### Queries at steady feeding (L1 G100k, the Q5 cells)

| | v1.1.0 (`off` run) | `off` | v1.1.0 (`on` run) | `on` (K = 4) | on / v1.1.0 |
|---|---|---|---|---|---|
| Throughput C=16 (req/s) | 1,199.4 | 1,292.2 | 1,203.2 | 1,058.1 | **0.879** |
| Client p99 C=16 | 77.4 ms | 74.3 ms | 76.5 ms | **22.1 ms** | **0.29** |
| Throughput C=64 (req/s) | 1,126.1 | 1,138.7 | 1,116.7 | 993.8 | **0.890** |
| Client p99 C=64 | 163.3 ms | 156.0 ms | 157.9 ms | **46.2 ms** | **0.29** |
| Query 503 refusals C=64 | 160,418 | 164,221 | 160,833 | 111,539 | — |

**Q5 with K = 4: the operational cost.**
- Throughput is 87.9 % (C=16) and 88.9 % (C=64) of v1.1.0. That is just below the 90 %
  threshold, so the throughput part fails.
- Client p99 falls to 29 % of v1.1.0 (≤ 125 %), so the p99 part passes.
- Fewer clients are refused at C=64.

**The cost is much smaller than the design's model predicted.**
- The model expected −30 to −35 % throughput in L1 and −55 % in L2.
- Measured: L1 −11 to −12 %; L2 −45 %, where the feeder is draining its backlog. The model
  assumed about 7 ms per batch.

## Reading

- **The feeder really drains more events.** Under 16 and 64 query clients it applies 3.4×
  and 6.1× as many events per second.
  - The C=64 share (55.0 %) nearly equals the C=16 share (56.3 %): with the bound, the
    feeder's progress no longer depends on the number of query clients.
  - Host CPU during catch-up falls from about 94 % to about 58 %. The limiter frees CPU
    rather than shifting it.
- **Queries pay in throughput, not in latency.**
  - In L2 (catch-up), query throughput is 45 % lower, with p99 unchanged.
  - In L1 (steady feeding), throughput is 11–12 % lower, while p99 is 3.4× lower: less
    time-slicing among concurrent batches.
  - Admission refusals at C=64 fall, because queued queries wait at the limiter instead of
    piling up behind the lock.
- **Limits.** One host (8 CPUs), loopback, one value K = 4, three observations per cell.
  K is a per-host choice, and other values were not measured.

## Adoption proposal (for the maintainer)

**Adopt B2 as an experimental opt-in** (knotrel#207): `KNOTREL_MAX_CONCURRENT_QUERIES`,
unset by default.
- The default behavior is unchanged, and Q5 passes against v1.1.0.
- With K = 4 on this host, Q3 passes with a margin of 6 points.

**Recommended for:**
- **source-managed deployments where the feeder must keep up or catch up under
  sustained query load:**
  - recovery after a feeder or database outage;
  - bulk change bursts;
  - backlogs after an import or replacement;
  - any setup where freshness under load matters more than peak query throughput;
- **query-heavy deployments that value tail latency.** In steady feeding, p99 fell 3.4×
  for an 11–12 % throughput cost;
- a starting value of **about half the CPUs** (K = 4 on 8 CPUs, as measured). Other
  values are unmeasured and should be checked on the target host.

**Not recommended for:**
- standalone deployments without a feeder, where there is only the throughput cost;
- deployments that need maximum query throughput;
- workloads with fewer concurrent query clients than K, where there is no effect.

**Release consequence.**
- If adopted, B2 becomes the v1.2.0 product change.
- Attempt 2 of #182 would be scoped from the diff (server query admission path; Q in both
  modes) and scheduled on that defined candidate.
- This estimate is not that qualification.

## Deviations (disclosed)

1. **The run directory was named `run`.** The orchestrator `run_b2.sh` named the run
   directory `run`, but the fixed evaluator accepts `Q` only under `Q-attempt<k>` (#60).
   - The `off` evaluation therefore failed, explicitly (`off/Q-evaluation.error.txt`), with
     no empty file.
   - The stop check then read "no evaluation" as a failure and skipped `on`. The protocol
     allows a skip only for a failed deciding criterion.
   - **Remedy:**
     - the `off` data were evaluated on an unmodified copy in the accepted layout
       (`off/eval/Q-attempt1/Q` on the host; the collection is unchanged);
     - the `on` run was then started by hand with `run_q.sh` and a run directory named
       `Q-attempt1`;
     - `run_b2.sh` and `analyze_b2.py` were fixed after the run.
   - Measurement, cells, thresholds and criteria are unchanged.
2. **Run-to-run noise in L1.** In the `off` run, L1 query throughput is 7.7 % (C=16) above
   the in-session v1.1.0 reference, although the code is the same. This is reported as
   noise; Q5 `off` PASS does not depend on it.

## Files

| Path | Contents |
|---|---|
| `analysis.json` | the full analysis (`analyze_b2.py`) |
| `off/Q-evaluation.json`, `on/Q-evaluation.json` | the frozen evaluator's verdicts |
| `off/raw/`, `on/raw/` | per-round `results.jsonl` and `summary.json`, `run.json`, `steps.jsonl` |
| `off/Q-evaluation.error.txt` | the deviation-1 failure |
| `run.log`, `host-*.txt`, `*/binaries-sha256.txt`, `b2-server.sha256` | the run record, host state and binary hashes |

Full raw evidence stays on the host under `evidence/v1.2.0-b2-2fd8293/`.
