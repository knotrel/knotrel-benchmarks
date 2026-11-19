# D5b: probe 503/412 handling, verification (item 5, phase 2)

This diagnostic follows DIAGNOSTICS-PLAN-2.md, D5b, and verifies amendment 4
(PROTOCOL §11). It is not part of the qualification. The a3-3 M_desc row
`read100-b8-c64-import` stays **INVALID** as measured.

**What changed.** The change is in the tooling itself, not a diagnostic copy:
`tools/contention-probe`, revision 3. Details are in PROTOCOL §11:
- bounded ETag refresh: up to 12 attempts, backoff 10–160 ms, at most 1.27 s
  of waiting;
- one retry after a 412;
- `background.imports` accounting and `import_starved`.

The validity rule for future collections is in `scripts/analyze_v070r_a4.py`.

## Verification

1. **Rust unit tests** (`cargo test` in `tools/contention-probe`, 7 tests,
   all pass) against a scripted stub server:
   - the backoff sequence;
   - 503, 503, 200: 3 attempts, the token read;
   - persistent 503: 12 attempts, no token, `import_starved` true;
   - 412, then stats 503 and 200, then 201 on the retry: the stats requests
     and the retry's `If-Match` are recorded;
   - 412 after a refresh: a recorded failure, starved;
   - 412 with an exhausted refresh: not retried, `refresh-exhausted`
     recorded, starved;
   - fewer imports completed than attempted: starved.
2. **Python tests:** `scripts/tests/test_v070r_amendment4.py` (13 tests). They
   cover the source contract and the validity rule, including fail-closed for
   revision-2 records.
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
| fixed 1 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 0.4 ms | 705 / 795 ms | no |
| fixed 2 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 0.5 ms | 616 / 807 ms | no |
| fixed 3 | 6 / 6 | 0 | 0 | 0 | 1 (0) | 0.4 ms | 618 / 710 ms | no |
| forced 1 | 6 / 6 | 1 | 1 | 0 | 2 (1) | 31.6 ms | 556 / 1,119 ms | no |
| forced 2 | 6 / 6 | 1 | 1 | 0 | 1 (0) | 15.8 ms | 609 / 1,377 ms | no |
| forced 3 | 6 / 6 | 1 | 1 | 0 | 2 (1) | 42.4 ms | 579 / 1,368 ms | no |

(`summary.txt`, from `summarize.py`.)

## What this shows

- **Recovery.** With the token stale, as in a3-3, the first import gets 412.
  The probe refreshes in 1–2 stats attempts, under 64 query clients and with
  one 503 refusal in two runs. The retry succeeds, and all 6 imports
  complete. The same situation in a3-3 produced 0 of 6.
- **No starvation is hidden.**
  - The refresh time (16–42 ms) and the slower first import (max 1.1–1.4 s,
    against 0.7–0.8 s) are visible in the record.
  - A configuration whose refresh cannot succeed, or whose imports do not
    all complete, is flagged `import_starved` and is invalid under the
    amendment 4 rule.
- **That flagging path is shown at unit level, not live.** Under the
  candidate server and these configurations, no refresh came near
  exhaustion.

## Events and limits

- **Superseded runs.** The first six live runs (all exit 0) used a binary
  whose `start` record still read `probe_revision: 2`; the code was
  otherwise identical. They are kept in `raw/superseded/` and were repeated
  with the revision-3 label.
- **The race did not recur.** As in D5, the fixed probe's initial refresh
  got 200 at its first attempt in every run. The race a3-3 lost did not
  recur here.
- **The forced copy is a synthetic reproduction:** it removes the initial
  refresh.
- **One host, not gated:** three runs per variant.
