# Packed-index integration — 2026-10-09

The experimental HDT core now uses the packed optional indices evaluated in the
[original pilot](../2026-10-08-hdt-packed-tokens/README.md). The integrated source
matches that candidate after rustfmt; no other isolated optimization is included.
Public APIs, default engine and experimental status are unchanged.

Integration is justified by memory savings, with latency uncertainty retained.
The [full matrix](../2026-10-08-hdt-packed-tokens-matrix/README.md) and
[separate diagnostic/confirmation](../2026-10-09-hdt-packed-resources/README.md)
remain historical observations against frozen sources. Their regression flags
are not rewritten. This integration adds no new performance measurements.

Independent read-only code review found no material issues in index conversions,
overflow rejection, token reuse, tests or documented performance limitations.
The reviewer did not execute tests. Verification logs in this directory record
the integration checks run by the implementer.
