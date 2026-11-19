# D5b: probe 503/412 handling, verification (item 5, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D5b, and verifies amendment 4
(PROTOCOL §11). It is not part of the qualification. The a3-3 M_desc row
`read100-b8-c64-import` stays **INVALID** as measured.

**What changed.** The change is in the tooling itself, not a diagnostic copy:
`tools/contention-probe`, revision 3. Details are in PROTOCOL §11:
- bounded ETag refresh: up to 12 attempts, backoff 10–160 ms, at most 1.27 s
  of backoff. Each attempt is bounded only by the connection's 60 s read
  timeout;
- a refresh ended by a status other than 503, or by a 200 without an `ETag`,
  is a distinct failure (`refresh-failed-status`);
- one retry after a 412;
- `background.imports` accounting and `import_starved`.

The validity rule for future collections is in `scripts/analyze_v070r_a4.py`.

## Verification

1. **Rust unit tests** (`cargo test` in `tools/contention-probe`, 10 tests,
   all pass) against a scripted stub server:
   - the backoff sequence;
   - 503, 503, 200: 3 attempts, the token read;
   - persistent 503: 12 attempts, no token, `import_starved` true;
   - 412, then stats 503 and 200, then 201 on the retry: the stats requests
     and the retry's `If-Match` are recorded;
   - 412 after a refresh: a recorded failure, starved;
   - 412 with an exhausted refresh: not retried, `refresh-exhausted`
     recorded, starved;
   - fewer imports completed than attempted: starved;
   - a 500 on stats: one attempt, `refresh-failed-status`, starved;
   - a 200 without an `ETag`: `refresh-failed-status`;
   - a connection closed without a reply: reconnect, then the token on the
     second attempt.
2. **Python tests:** `scripts/tests/test_v070r_amendment4.py` (15 tests).
   - They cover the source contract and the validity rule, including
     fail-closed for revision-2 records and starvation derived from the
     counters even when the flag says false.
   - One test runs `analyze_supplement_mdesc` end to end with the rule
     installed, and checks that importing the module changes nothing.
3. **Live runs** on the a3-3 candidate server. The setup is D5's
   (source-managed, lifecycle on, 100k nodes, seed 7), with configurations
   `c16-events` → `c64-none` → `c64-import`:
   - `fixed`: revision 3, as built from the tooling;
   - `forced`: a copy that skips the initial refresh (`forced-copy.diff`),
     so the token stays stale after the events configuration, as in a3-3.

   Binaries are listed in `raw/binaries-sha256.txt`. Runs are listed in
   `raw/runs.txt`; every run exited 0.

| Run | Imports attempted / completed | 412 | Retries | Failures after refresh | Stats attempts (503 refused) | Refresh latency | Import latency p50 / max | Starved |
|---|---|---|---|---|---|---|---|---|
| fixed 1 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 0.5 ms | 498 / 642 ms | no |
| fixed 2 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 55.4 ms | 675 / 841 ms | no |
| fixed 3 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 16.0 ms | 706 / 782 ms | no |
| forced 1 | 6 / 6 | 1 | 1 | 0 | 1 (0) | 19.4 ms | 646 / 1,515 ms | no |
| forced 2 | 5 / 5 | 1 | 1 | 0 | 2 (1) | 62.2 ms | 756 / 1,537 ms | no |
| forced 3 | 5 / 5 | 1 | 1 | 0 | **11 (10)** | **1,205.5 ms** | 731 / 2,501 ms | no |

(`summary.txt`, from `summarize.py`.)

## What this shows

- **Recovery.** With the token stale, as in a3-3, the first import gets
  412. The probe refreshes and the retry succeeds; every attempted import
  completes (6, 5, 5). The same situation in a3-3 produced 0 of 6.
- **The refresh bound is close to the edge under this saturation.** In
  forced run 3 the refresh needed 11 of its 12 attempts (10 refused with
  503, 1.2 s). One more refusal would have exhausted it and made the
  configuration starved, and invalid under the amendment 4 rule.
  - This matches D5's sampling: about 87% of stats requests refused under
    64 query clients, measured after the clients had saturated admission.
  - Whether to raise the bound before any campaign is a decision for the
    maintainer. The bound was not changed after seeing this run.
- **No starvation is hidden.**
  - The refresh time and the slower first import are in the record.
  - A refresh that fails, or a window whose imports do not all complete, is
    flagged `import_starved`, and the amendment 4 rule recomputes this from
    the counters.
- **The failing-refresh path is shown at unit level, not live.**
- **Fewer imports per window** in forced runs 2 and 3 (5 against 6) come
  from the refresh time spent inside the window. Each attempted import
  completed.

## Events and limits

- **Superseded runs**, all exit 0 and all kept:
  - `raw/superseded/`: six runs whose `start` record still read
    `probe_revision: 2`;
  - `raw/superseded-pre-review/`: six runs of the probe before the review
    fixes (failure kinds, `stats_other`, `refresh_failed_status`). Same
    outcome: 6/6 everywhere; forced runs needed 1–2 stats attempts.
  - Both sets were repeated with the final source, as tabled above.
- **The race did not recur.** As in D5, the fixed probe's initial refresh
  got 200 at its first attempt in every run.
- **When the refresh ran is not recorded.** A refresh at the start of a
  configuration meets less saturation than one after the clients ramp up,
  so refusal rates differ between runs.
- **The forced copy is a synthetic reproduction:** it removes the initial
  refresh.
- **One host, not gated:** three runs per variant.
