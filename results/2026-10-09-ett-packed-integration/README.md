# ETT packed-token integration — 2026-10-09

The measured candidate is now integrated into core forest.rs. The source is
byte-identical to the [pilot candidate](../2026-10-09-ett-packed-tokens/README.md),
including layout, boundary, clearing and overflow tests. Public APIs, algorithm,
configuration, default engine and experimental status remain unchanged.

The [full matrix](../2026-10-09-ett-packed-tokens-matrix/README.md) preserves the
before/after evidence and setup tradeoff. No new performance measurements are
claimed by this integration. Historical results remain unchanged.

Both workspace verification suites passed; see [verification.json](verification.json)
and saved logs. The exact candidate had independent code review in the pilot,
and the full-matrix protocol had independent review. The additional final matrix
numerical review did not complete because the reviewer reached its usage limit;
the implementer recomputed all runtime medians and ran the saved audit instead.

No other isolated candidate was combined. No staging, commit or push performed.
