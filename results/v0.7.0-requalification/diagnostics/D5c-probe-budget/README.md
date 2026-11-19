# D5c: probe revision 4 (time budget), live verification (item 5, phase 3)

This diagnostic follows DIAGNOSTICS-PLAN-3.md, "Probe revision 4". It is not
part of the qualification. The a3-3 M_desc row stays INVALID.

**Revision 4** (`tools/contention-probe`, commit 7e8b507c):
- **Budget:** 1 s per ETag refresh, from its first request. That is one
  period of the background import cadence: a refresh that cannot finish
  within one period has stalled the activity.
- **Retries:** backoff of 10–160 ms, at most 10 attempts (950 ms of
  cumulative backoff before the tenth).
- **Bounds:** each read timeout and reconnect is bounded by the remaining
  budget.
- **Exhaustion:** recorded with its reason (`deadline` or `attempts`).
  Exhaustion and incomplete imports set `import_starved`.
- **Rust tests:** 13, including:
  - slow refusals exhaust the deadline before the attempt cap;
  - a silent server is bounded by the budget;
  - the budget and the cap are consistent.

**Live runs.** The setup is D5's: the a3-3 candidate server, source-managed,
lifecycle on, 100k nodes, seed 7, configurations `c16-events` → `c64-none` →
`c64-import`.
- **fixed:** 3 runs of the revision-4 build.
- **forced:** 3 runs of a copy that skips the initial refresh, so the token
  is stale as in a3-3 (`forced-copy.diff`).
- They ran in the quiet phase-3 chain; every run exited 0.

| Run | Attempted / completed | 412 / retries | Stats attempts (503 refused) | Refresh | Exhausted | Import p50 / max | Starved |
|---|---|---|---|---|---|---|---|
| fixed 1 | 6 / 6 | 0 / 0 | 1 (0) | 4.0 ms | 0 | 660 / 962 ms | no |
| fixed 2 | 6 / 6 | 0 / 0 | 1 (0) | 0.4 ms | 0 | 546 / 732 ms | no |
| fixed 3 | 6 / 6 | 0 / 0 | 1 (0) | 0.3 ms | 0 | 850 / 892 ms | no |
| forced 1 | 6 / 6 | 1 / 1 | 2 (1) | 28.3 ms | 0 | 603 / 1,493 ms | no |
| forced 2 | 6 / 6 | 1 / 1 | 2 (1) | 29.5 ms | 0 | 666 / 1,088 ms | no |
| forced 3 | 6 / 6 | 1 / 1 | 1 (0) | 22.0 ms | 0 | 675 / 1,692 ms | no |

(`summary.txt`, from `summarize.py`.)

## What this shows

- **Recovery.** Every forced run recovered within 1–2 stats attempts (22–30
  ms), well inside the 1 s budget. Every attempted import completed.
- **The budget was not stressed in these runs.** D5b's earlier forced run 3
  needed 11 attempts and 1.2 s. Under revision 4 such a refresh would count
  as starved, and its configuration would be invalid.
  - That is the declared, workload-derived rule, chosen before these runs.
  - Whether it recurs in qualification 3 is a property of the host and of
    load timing. It is a residual risk for the M_desc import rows, not
    something to tune now.
