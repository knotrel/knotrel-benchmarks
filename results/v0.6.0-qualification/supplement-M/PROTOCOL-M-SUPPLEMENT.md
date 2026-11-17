# v0.6.0 supplementary contention run (M supplement): protocol

**Status:** declared before measurement and frozen by
`FREEZE-M-SUPPLEMENT.json`. **Supplementary:** this run does not replace,
re-classify or extend any result of the frozen v0.6.0 campaign
(`evidence/v0.6.0-qualification-48bc82f`), and grants no waiver.

Authorization: maintainer, 2026-11-17, "Rerun M dichiarato", which selects
option 9(a) of `COMPARISON-v0.5.0-v0.6.0.md` §8: a separate, labelled run of
the affected M cells with fixed tooling.

## 1. Why

After the frozen campaign, three tooling defects were found in
`contention-probe` (revision 1). They are recorded in comparison §7 and
reproduced in `evidence/v0.6.0-diagnostics/post-campaign-probe-defect/`.

1. At 100k nodes, feeder catch-up and `mixed50` link toggles registered new
   node IDs beyond the server's default `KNOTREL_MAX_NODES` (100,000). Every
   feeder link failed with `node_limit_exceeded`, so the feeder stopped after
   its first request. `mixed50` links were rejected per item and its cuts did
   nothing.
2. At 10k with 16 and 64 clients, every background replacement import failed.
   The import reused an `ETag` that the preceding events configuration had
   made stale.
3. At 10k with 64 clients the feeder stopped after one batch. Feeder events are
   refused with `503 import_in_progress` while queries hold every admission
   permit, which is documented admission behavior (http-api, rejection
   metrics), and revision 1 treated that refusal as fatal.

Building revision 2 and running the functional checks (§4) exposed two more
defects in revision 1:

4. **Off-by-one at the first pass boundary.** The last owned item of the first
   pass was cut before it was linked, so each client produced one no-op
   mutation.
5. **Carry-over between configurations.** Later configurations on the same
   server reused the same extra-edge IDs, and toggles skipped after a 503
   desynchronized the link/cut phases. As a result, some mutations were
   no-ops.

## 2. What changes (probe revision 2 only)

- **Node limit.** The server is started with
  `KNOTREL_MAX_NODES = nodes + 100000`. It is otherwise configured as in the
  frozen run: cleared environment, `compact-bfs`, metrics on, default
  admission limit of 32 pending jobs.
- **Import ETag.** A background import reads the current `ETag` from
  `GET /v1/stats` when its configuration starts.
- **Feeder refusals.**
  - A feeder request refused with 503 is retried unchanged after 10 ms and
    counted (`refused_503`).
  - Any other failure stops the background activity.
  - Every failure is recorded with its status and error code.
- **Batch results.** Per-item error results and no-op mutations
  (`changed: false`) are counted.
- **Toggle correctness.**
  - The toggle phase is read before the pass boundary flips it.
  - Each configuration toggles fresh extra-edge IDs.
  - A client resends a refused batch body unchanged.

Not changed:
- the servers: the frozen campaign's release builds, read in place and
  verified against its `binaries-sha256.txt`;
- workloads, mixes, batch sizes, client counts, windows and seeds;
- the M_reg pair schedule rules and tolerances;
- the M_desc and M_reg analysis code (reused unchanged).

## 3. What runs

From `MATRIX-M-SUPPLEMENT.json`, copied from the frozen matrix (a test checks
that every configuration and cell is identical):

- **M_desc supplement, on the candidate only (descriptive), 60 configurations
  on 6 server processes:**
  - `mixed50` at 100k, lifecycle off and on: 12 configurations each.
  - Source-managed at 10k and 100k, lifecycle off and on: all 6
    configurations each, in the frozen order. Import and events alternate on
    one server, so every configuration has the same predecessor as in the
    frozen run.
- **M_reg supplement, candidate against v0.5.0:**
  - Cells: `Mreg-standalone-off-mixed50-b64-c16-100k-none` and
    `Mreg-source-managed-on-read100-b8-c16-100k-events`.
  - Schedule: 2 warmup pairs plus 12 analyzed pairs, a fresh server per
    observation, arm order balanced, order seed 60601.
  - Tolerances: throughput 10% (ratio B/C), client p99 25%.

M5 rule (i) is not re-evaluated. Its configurations (read-heavy, no
background) were not affected by the defects.

## 4. Before measuring

- **Functional checks (done before the freeze):**
  - Probe: `cargo clippy -D warnings` and a release build.
  - The Python suite.
  - Short smoke runs (0.2 s warmup, 0.6–1.5 s windows), on both servers, of
    every covered mix and background in both lifecycle modes at 10k and 100k.
    Each one must yield zero invalid configurations.
  - The smoke runs are tooling validation only. Their numbers are not results
    and are not reported as such.
- **Host prerequisites:**
  - AC power before every child.
  - No thermal or performance warning.
  - No `cargo` or `rustc` process.
  - `caffeinate -dimsu`.
  - Nothing else runs during measurement.

## 5. Validity and interpretation (declared)

- **Validity.** A configuration record is **valid** only if all of these hold:
  - `errors == 0`;
  - `item_errors` is empty;
  - `noop_mutations == 0`;
  - with background activity: `background.failures == 0` and
    `background.completed > 0`.
- **503 refusals.** Refusals are allowed and reported.
- **Invalid records.** An invalid record is reported as invalid. It is never
  rerun or dropped.
- **M_reg.**
  - Every analyzed observation must also have only status 200 (frozen
    analyzer).
  - A cell with an invalid analyzed observation is **INVALID** and gets no
    verdict.
- **Interpretation.**
  - Supplementary verdicts are reported **beside** the frozen ones, never
    instead of them.
  - Whether they count for v0.6.0 is the maintainer's decision.
- **No extension and no rerun.** The only exception is one rerun of a child
  after a documented infrastructure failure unrelated to the measured code.
- **Invalidation.** The frozen campaign's rules apply.
  - Any change to the probe, collector or analysis after the freeze
    invalidates the affected experiment.
  - A change to executed knotrel code is impossible here, because the server
    binaries are fixed.

## 6. Budget

Estimated 14 minutes (M_desc supplement about 5, M_reg supplement about 9);
cap 30 minutes. Exceeding the cap stops the run.

## 7. Outputs

- **Evidence directory:** `evidence/v0.6.0-m-supplement-48bc82f/`, which is
  new; the scripts refuse to reuse it.
- **Contents:**
  - a clone of knotrel-benchmarks at the freeze commit;
  - the probe built there with `--locked --offline`;
  - logs and checksums;
  - `Mdesc/` and `Mreg/` collector outputs with `analysis.json`.
- **Report:** `results/v0.6.0-qualification/supplement-M/REPORT-M-SUPPLEMENT.md`.
