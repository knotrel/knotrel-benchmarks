# v0.7.0 re-qualification: diagnostics ordered by the maintainer (declared before measuring)

Ordered on 2026-11-19 ([`../REPORTING-DECISIONS.md`](../REPORTING-DECISIONS.md)).
The release stays pending until the maintainer decides.

## Rules for every diagnostic

- **Separate from the qualification.** A diagnostic never replaces, re-runs or
  supersedes a result of attempt a3-3. The verdicts stand as measured:
  - REGRESSION (B4 `import-high`);
  - FAIL ×3 (C3);
  - INCONCLUSIVE (B4 `ops` sparse 100k, B4 `metrics-ops`);
  - INVALID (M_desc `read100-b8-c64-import`).
- **No threshold changes** and no exception is accepted.
- **Diagnostic code is separate.** The frozen tooling and probes are not
  modified. Diagnostic harnesses and instrumented builds live under this
  directory or in scratch worktrees. Product patches used to evaluate
  mitigations are diagnostic builds only, never merged by this work.
- **Host.** The developer laptop, with normal background activity and no
  conformance gate, disclosed as such. Comparisons are paired and
  alternating where two variants are compared. Repetition counts are fixed
  below, before measuring.
- **Every run is reported**, including failed or discarded runs, with the
  reason.
- **Outputs.** `Dn-*/` subdirectories, one per diagnostic: raw logs, the
  harness source, a short README.

## D1 — B4 `import-high` REGRESSION (item 1)

**Question:** how the +413% splits into costs, and how the candidate compares
with a reference of equivalent capability.

**Cost breakdown.** Candidate arm, sparse 10k, 60% inactive / 30% disabled,
the frozen trace and seed:
1. body bytes, full vs effective-only;
2. the server's own import phase durations
   (`knotrel_import_duration_seconds{phase}`: receive, prepare, and publish if
   exposed);
3. in-process parse-only time of the full body vs the effective body;
4. the remaining build and publication time.

**Capability-equivalent comparison.** Three arms, paired and alternating,
fresh server per import:
- (L) the lifecycle import of the full topology with flags (the B4
  candidate);
- (F) a plain import of the full registered graph with every entry active:
  the same parse and storage volume, without flags;
- (E) the B4 reference: a plain import of the effective graph plus the
  application-side lean store.

Reported:
- F − E: the volume cost of keeping non-effective entries;
- L − F: the flag and lifecycle cost.

12 pairs per comparison, 2 warmup.

**Result statement:** which part, if any, is not required by the
full-topology contract. No verdict changes.

## D2 — C3 heap growth FAIL ×3 (item 2)

**Question:** is growth bounded over repeated compaction cycles, and what
does mitigation cost?

**Repeated cycles.** The frozen `core-lifecycle resources` (count-alloc
build), fresh-ID churn, 5% per cycle, 100k nodes, sparse, ring and hub. The
run is 300 cycles (10× the qualification's 30), one run per topology.

Recorded per cycle:
- net live heap;
- peak;
- engine vertices, retired slots and catalog capacities;
- compactions.

**Bounded** means the maximum net heap over cycles 151–300 is at most the
maximum over cycles 31–150, and the 150-cycle least-squares slope of cycles
151–300 is within ±1% of the early mean.

Also reported:
- the steady state: the mean, minimum and maximum over the last 100 cycles;
- the overall peak.

**Mitigation cost.** A diagnostic build of the candidate whose catalog and
incident tables are pre-sized to the expected capacity: the registered nodes
plus retired-slot headroom, sized from the 300-cycle run. Measured on that
build:
- the C3 rule values over 30 cycles;
- the 300-cycle behavior;
- the B5 memory ratio (plain / lifecycle / reference at 100k);
- the startup peak.

One run each, deterministic byte counts.

## D3 — B4 `ops` sparse 100k INCONCLUSIVE (item 3)

**Question:** where the lifecycle batch overhead at 100k goes, and which costs
are actionable.

The frozen `http-lifecycle --scenario ops`, sparse 100k: both arms in one
process.

1. **Sampling profile** (macOS `sample` at 1 ms) over windows of each arm,
   alternating arms. Six windows per arm, symbolized against the
   release-with-debug-info build of the same commit.
2. **Phase timing** of an instrumented diagnostic build: parse,
   lifecycle-plan, lock wait, engine operations, response.

Reported: the top differences in self time between the arms, each
attributed to a code site and classed as inherent to lifecycle semantics or
candidate for optimization. No new verdict.

## D4 — B4 `metrics-ops` sparse 10k INCONCLUSIVE (item 4)

**Question:** how much of the overhead is metrics recording and how much is
lock-acquisition timing, and can the 6% budget be met without reducing
observability?

Diagnostic builds of the candidate, all on the frozen `metrics-ops` requests
(sparse 10k):
- (a) metrics off;
- (b) metrics on, as released;
- (c) metrics on with `RwLock` acquisition timing removed;
- (d) metrics on with the same observable counters, recorded through a
  cheaper path, if the profile shows one (for example thread-local
  aggregation or one clock read per batch).

24 pairs per comparison against (a), 2 warmup.

Reported: each variant's overhead, its interval, and whether every metric of
(b) is still exported. Whether the 6% budget "can be met without reducing
observability" is answered only by a variant that exports the same metrics.

## D5 — M_desc `read100-b8-c64-import`: 6/6 replacement imports HTTP 412 (item 6)

**Question:** is this expected precondition enforcement, a probe error or a
product defect?

**Facts already in the evidence (a3-3, `Mdesc/raw/00036-M-source-on-100k.stdout`):**
- The configurations run in a fixed order. `read100-b8-c16-events`
  (65,152 events applied) and `read100-b8-c64-none` run just before
  `read100-b8-c64-import`.
- The probe refreshes its stored ETag with one `GET /v1/stats` at the start
  of an import configuration (`tools/contention-probe/src/main.rs`,
  background `import`). In this configuration that request returned 503
  (`stats-503`), while 64 query clients saturated the server's 32 admission
  permits.
- `GET /v1/stats` uses the same bounded admission as writes. This is
  documented: `service.rs` `stats()`, `docs/http-api.md` 503 `busy`.
- After a 412, the probe does not refresh the ETag. It keeps sending the
  same token.

**Hypothesis:** the probe sent an ETag made stale by the earlier events
configuration, and the server rejected it correctly.

**Reproduction.** The candidate server, source-managed, lifecycle on, 100k
nodes, the frozen seed, with the configurations `read100-b8-c16-events`,
`read100-b8-c64-none` and `read100-b8-c64-import` in that order. 3 runs each:
1. the frozen probe, unchanged;
2. an instrumented copy of the probe. It logs every `If-Match` it sends,
   the status of each stats request, and a fresh ETag read after each 412
   (retrying the stats request until it gets 200). It changes nothing else;
3. a corrected copy that retries the stats request on 503 (bounded backoff)
   and re-reads the ETag after a 412, as `docs/http-api.md` describes for a
   compliant feeder.

**Classification:**
- **Expected precondition enforcement:** every 412 answers an `If-Match`
  that differs from the live ETag read just after it (an older state
  version). The server is correct.
- **Probe error:** the stale token comes from the probe's refresh logic (a
  503 not retried, no refresh after a 412), and the corrected copy completes
  its imports at 64 clients.
- **Product defect:** a 412 answers an `If-Match` equal to the live ETag; or
  the stats ETag disagrees with the import's precondition token; or the
  corrected copy still cannot complete any import at 64 clients, for example
  because the precondition can never be met while other requests keep
  advancing the state, in a read-only workload where nothing should advance
  it.
