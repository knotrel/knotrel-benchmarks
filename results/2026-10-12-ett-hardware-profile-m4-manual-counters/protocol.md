# ETT scan-root marker-scoped manual counters protocol on Apple M4

This campaign reuses the immutable 72-process seed-1012 plan from the prior
marker-scoped campaign. It uses the same hash-verified isolated before/after
binaries, replay arguments, signpost validation, sleep inhibition, six batches,
and external raw-artifact policy.

The only profiling change is the read-only manual CPU Counters template,
SHA-256 `99b0cb00c8c35bdd66fb6456021ea11c21c0c3e36c89b0b4e5975ea5622ecd74`.
The independent mapping probe establishes positions 0–7 as the configured
event sequence; positions 8–15 are an exact duplicate and are validation data,
not additional counters. A record is analyzable only when its marker intervals
are valid, `counters-profile` exports successfully, and every used nonzero
counter array has two identical eight-value groups.

All reported counter aggregates must be restricted to target-process samples
overlapping `measurement-replay`. `ARM_L1D_CACHE_LMISS_RD` is not a page-fault
or TLB counter; no TLB claim is allowed.
