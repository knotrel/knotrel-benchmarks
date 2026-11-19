# Evaluation: `ETag` header on 412 responses of replacement imports

The maintainer ordered this separate evaluation on 2026-11-19 (plan 3,
item 5). It is a diagnostic build only. Nothing here goes into the candidate
without a maintainer decision.

## Change evaluated (`etag412.diff`, on candidate e75ff6a)

- `validate_replacement_precondition` runs under the import's write lock.
  When the `If-Match` token is well formed but does not match the live
  state, it now returns a new error variant that carries the current token.
- The HTTP layer returns the same 412 `precondition_failed` body, plus an
  `ETag` header with that token.
- Malformed `If-Match` values (weak tags, `*`, lists, bad syntax) still get
  412 with no `ETag`: they say nothing about the state.
- Server unit tests still pass: 119 library tests.

## Tests (`harness/`, `raw/etag-eval.json`)

The tests run in process through the real router, on a source-managed
lifecycle server.

| Scenario | Trials | Result |
|---|---|---|
| **Consistency.** After k event batches (k = 1..50), a replacement with the stale token gets 412. Its `ETag` header is compared with `GET /v1/stats` right after, then used for a retry. | 50 | 50/50: 412; header token equals the stats token; retry 201 |
| **Staleness after release.** As above, but one more event batch is applied between the 412 and the retry. | 50 | 50/50: the retry with the 412 token gets 412 again, with a newer token; a retry with that token succeeds (201) |

## Assessment

- **Consistency: holds.** The token is formatted from the same state, under
  the same lock, as the comparison that failed. It is exactly the token
  `/v1/stats` would have returned at that moment.
- **Concurrency: no worse than `/v1/stats`.** The token can be stale as soon
  as the lock is released, like any token read through `/v1/stats`. A client
  still needs the 412-and-retry path, and a bounded one, as in probe revision
  3/4.
- **What it saves:** the `GET /v1/stats` round trip after a 412. Under
  saturation that request competes for the 32 admission permits (D5: about
  87% refused under 64 clients). The 412 already went through import
  admission, so the token comes with no extra admitted request.
- **Semantics: the main risk.**
  - `If-Match` protects a replacement against changes the feeder has not
    seen.
  - Handing back the current token makes a blind retry trivial: send again
    with whatever the server returned, without re-evaluating.
  - In source-managed mode, the changes that advance the token are the
    feeder's own events and imports. Feeder sessions are fenced by
    `feeder_epoch` and a lease. The token protects against the feeder's own
    stale view, or against a fenced-out predecessor's late writes, rather
    than against a second concurrent writer.
  - A feeder that retries blindly would replace the graph regardless of
    events it applied in between. A feeder that re-reads `/v1/stats` and
    retries without re-evaluating does exactly the same today. The header
    changes the cost of a blind retry, not its possibility.
- **Contract impact:**
  - an additive response header on an error status;
  - `docs/http-api.md` would need to say that the token is advisory, that it
    may be stale on arrival, and that a feeder should re-derive its
    replacement from its own source position before retrying;
  - existing clients are unaffected.

## Recommendation (for the maintainer to decide)

- **Technically sound and cheap.** Adopting it is a product/API decision.
- **If adopted:**
  - document it as advisory;
  - keep the bounded refresh in clients as the fallback;
  - add contract tests (the token on mismatch; none on malformed tags);
  - qualify it in a later candidate.
- **It is not needed for the qualification:** probe revision 4 does not
  depend on it.
- **It is not included in the v0.7.0 candidate prepared now,** which follows
  the decision "Nessun cambio di API ora" (no API change for now).
