# Proposal: admission of `GET /v1/stats` (no product change made)

The maintainer asked for this on 2026-11-19: "Per ora non modificare
l'admission control di stats/health: prepara una proposta separata che
consideri il rischio di aggravare la saturazione." It is a proposal for a
decision. Nothing here has been implemented in the product.

## Facts (candidate e75ff6a, `docs/http-api.md`)

- **Health endpoints already bypass admission.** `GET /health` and `GET /ready`
  take neither the graph lock nor an admission permit (`docs/http-api.md`,
  "Lifecycle, health and shutdown"). `/metrics` takes neither either, and it
  exports node and edge gauges without the graph lock (the metrics registry
  has its own internal synchronization). "Exempt health/ready" is therefore
  already the behaviour, and needs no decision.
- **`GET /v1/stats` is admitted like a query.** It takes one of the
  `KNOTREL_MAX_PENDING_JOBS` (default 32) admission permits and the shared
  graph lock (`service.rs` `stats()` → `run_read`). Over capacity it gets 503
  `busy`.
- **The `ETag` that a replacement import needs** (`If-Match`) is returned by
  every query response, batch response, stats snapshot and import
  publication. A 412 response states the current token only in its message
  text (D5: `does not match current state '"1.18304.e1-18304"'`), not in an
  `ETag` header.
- **Measured under saturation** (D5: 64 query clients, 32 permits): 43–44 of
  50 sampled `/v1/stats` requests got 503 (about 87%).
  - D5b, final runs: with bounded retries and backoff, the refresh succeeded
    in all three forced runs, after 1, 2 and **11 of 12** attempts (19 ms,
    62 ms, 1.2 s). The last came within one attempt of exhaustion.
  - `docs/http-api.md` tells a feeder to re-read the token via `/v1/stats`
    for recovery. It does **not** prescribe retrying `busy`, nor any backoff.
    Probe revision 3 adds bounded retry on its own.
  - In these runs (n = 3, refresh timing within the window not recorded),
    such a client recovered, but with little margin.
- **The a3-3 INVALID row came from the probe,** which did not retry. It did
  not come from an impossibility in the server (D5, D5b).

## Options

| Option | Change | Extra load under saturation | Risk | Evidence a decision would need |
|---|---|---|---|---|
| **A. Status quo plus client guidance** | a docs change: retry guidance for `busy` on stats (none exists today); probe revision 3 already behaves this way | retries only, bounded by the client's backoff | under this saturation a refresh came within one attempt of exhaustion (D5b), so clients may exhaust their retries; for the probe, a starved refresh is visible, not silent (`import_starved`) | none beyond D5b; optionally a soak with 64+ clients and stats polling |
| **B. Separate small permit pool for stats** (for example 1–2 permits) | admission code and config | at most k extra shared-lock holders | while a mutation waits for the lock, new readers wait behind it, so stats cannot starve writers. Stats readers do add shared-lock hold time, and with k unbounded clients the pool itself saturates. | M_desc with stats polling at 16/64 clients, against the status quo: query latency p99, feeder lag, stats refusal rate |
| **C. Lock-free state token** (for example the token on `/ready`, or a small `/v1/state-tag` served from an atomically published word, as readiness is) | new published state and endpoint | no graph lock, no permit | the token must be published atomically with every state change (generation, version, position); consistency must be proven against the import precondition | contract tests (token always equals the precondition's view); a race test under concurrent events |
| **D. `ETag` header on 412 responses** | the import error path adds the current token as an `ETag` header | none: the information is computed under the lock the import already holds | an API addition; clients must not retry blindly in a loop (one retry per 412, as the probe does) | contract test; docs update |

Saturation risk, in order: D and C add no graph work, A adds bounded client
retries, and B adds bounded server work, but could worsen saturation if
sized or used carelessly.

## Recommendation (for the maintainer to decide)

- **Keep A** for v0.7.0, with a docs change that adds retry guidance for
  `busy`. Probe revision 3 already retries with backoff and records
  starvation instead of hiding it. Its margin under 64 clients is thin (11
  of 12 attempts in one run), so the retry bound is itself a decision for the
  maintainer.
- **Consider D** as the smallest product change that removes the need for a
  stats round-trip after a 412. It adds no load under saturation.
- **Do not pursue B** without the measurement listed above.
- **C** is larger and has a consistency burden. Only consider it if
  monitoring needs a token served without the graph lock for reasons other
  than imports.

None of these options changes the a3-3 results, the INVALID row, or any
threshold.
