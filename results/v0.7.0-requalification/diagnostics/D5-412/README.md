# D5 — M_desc `read100-b8-c64-import`: 6/6 replacement imports HTTP 412

Diagnostic ordered on 2026-11-19 (DIAGNOSTICS-PLAN.md, D5). It is not part
of the qualification, and the a3-3 row stays INVALID as measured.

## Classification

**Expected precondition enforcement by the server, caused by a probe
error. No product defect was found in this diagnostic.**

This classification rests partly on a synthetic reproduction. The
unmodified probe never reproduced the 412 (0 of 9 runs). The forced copy
builds in the hypothesised mechanism: it keeps the stored token. The
criteria were then met on that reproduction and on the 54 fresh-token
imports. That the a3-3 failure followed this path is inferred from its
record (`stats-503` then 412s), not observed directly.

## Mechanism

1. Before `c64-import`, the configuration `read100-b8-c16-events` applies
   tens of thousands of feeder events. They advance the state version, so the
   probe's stored ETag is stale.
2. At the start of an import configuration, the probe makes one
   `GET /v1/stats` call to refresh the ETag.
   - Under 64 query clients, `/v1/stats` is refused with 503 `busy` most of
     the time. It shares the bounded admission (32 permits) with the queries.
     This is documented: `service.rs` `stats()`, `docs/http-api.md`.
   - In a3-3 this one request got 503 (`stats-503`).
3. The probe neither retries that request nor refreshes the ETag after a
   412, so it sent the stale token for the whole window.
4. The server rejected every replacement import with 412
   `precondition_failed`, as the documented `If-Match` contract requires.

## Evidence

All runs are in `raw/`, with binaries in `raw/binaries-sha256.txt`. The setup
used the a3-3 candidate server: source-managed, lifecycle on, 100k nodes,
seed 7, configurations `c16-events`, `c64-none`, `c64-import`. Runs are listed
in `raw/runs.txt`; every run exited 0, and none was discarded.

| Variant | Runs | Initial `/v1/stats` | Imports in `c64-import` | 412 |
|---|---|---|---|---|
| frozen probe (a3-3 binary) | 3 | 200 at the first attempt | 6/6 completed each | 0 |
| instrumented copy | 3 | 200 at the first attempt; stored token `"1.0.p0"`, live `"1.15488…"` to `"1.17728…"` | 6/6 each | 0 |
| corrected copy (retry `/v1/stats` on 503; refresh after a 412) | 3 | 200 at the first attempt | 6/6 each | 0 |
| forced copy (added, see below) | 3 | 50 samples under load: **43–44 of 50 got 503**; refresh skipped, as in a3-3 | **0 completed** (4, 5, 5 attempted) | **14 of 14** |

- **Every 412 in the forced runs** answered `If-Match: "1.0.p0"`. The live
  ETag read right after it (stats retried until 200) was different every
  time (`"1.16512.e1-16512"`, `"1.18304.e1-18304"`,
  `"1.62912.e1-62912"`).
- **The server's message** reads, for example:
  `If-Match '"1.0.p0"' does not match current state '"1.18304.e1-18304"'`.
  No 412 answered a token equal to the live ETag.
- **Fresh tokens succeed at 64 clients.** With a fresh token, replacement
  imports completed in 54 of 54 attempts across the 9 non-forced runs. The
  `/v1/stats` ETag is accepted by the import precondition.

**Product-defect criteria (plan): none met.**
- No 412 answered a matching token.
- The ETag from `/v1/stats` and the import precondition agree.
- Imports complete at 64 clients once the token is fresh.

## Departures from the plan (declared here)

- **The race did not recur.** In the 9 planned runs, the first `/v1/stats`
  request got 200. That request is made as the configuration starts, before
  the 64 clients saturate admission. In a3-3 it lost the race. The
  corrected copy's retry path was therefore not exercised by a 503.
- **Added a fourth variant, "forced".** It does what the a3-3 probe did after
  its 503: it keeps the stored token. Before that, it samples 50 stats
  requests under load to measure how often the refresh is refused. Its imports
  are fewer per window (4–5) because the sampling takes about 1 s of the
  5 s window.
- **The stale token differs from a3-3's.** a3-3 ran the full configuration
  list, so its stored token came from `c16-import`'s last import. The reduced
  list here leaves the setup token `"1.0.p0"`. Both are stale after the
  events configuration.
- **The ~87% refusal rate** was sampled after the clients had saturated
  admission. The refresh at the start of a configuration usually got 200
  here, so 87% is not the probability that a3-3's single refresh would
  fail.

## Observations (no verdict)

- **Probe refresh logic.** A feeder that follows `docs/http-api.md` retries
  503 `busy` and re-reads the ETag before a replacement import. The probe
  does neither. Whether to change it for future collections is a tooling
  decision for the maintainer. The frozen probe is not changed by this
  diagnostic.
- **Operational note.** Under saturation, `/v1/stats` is refused most of the
  time (about 87% here), because it uses the same admission as graph work.
  This is documented behavior. Whether stats should bypass admission is a
  product question for the maintainer, not a defect.
