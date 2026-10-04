# HDT follow-up diagnostics — 2026-10-04

Eight instrumented runs cover path/cyclic blocks at 100k nodes, q10/q90,
1,000 operations, current sparse HDT and the historical frozen HDT v2 control.
These diagnostic timings are not normal before/after performance measurements.
The current-HDT traces and all work counters exactly match the corresponding
original 2026-10-04 campaign cells. Manifests preserve source and binary identity.

On cyclic blocks with 90% queries, current HDT performs 100 cuts: 91 tree cuts
with promotions, six tree cuts without promotions, three non-tree cuts. Promoting
cuts account for 373,073,081 of 373,503,996 recorded cut nanoseconds (99.88%).
They promote 212,272 tree edges and 12,317 non-tree edges. This isolates the
expensive class of operations, not the exclusive cost of the promote function.

A [separate CPU sample](../2026-10-04-hdt-cpu-profile/README.md) points to Euler-tour
maintenance and sparse-level lookup/materialization. No HDT algorithm change has
been made yet, and the frozen v2 control is not a proposed replacement.

Next bounded experiment: eliminate redundant sparse-level ID translation when
promotion both inserts incidence and links an upper-level tree edge. Profile
`Level::ensure`, incidence maintenance and tour link costs before/after. Preserve
HDT size/nesting invariants, rerun unchanged sparse/dense/Cogentco/repeat controls,
and retain the unmodified v3 as an explicit before control. Larger storage/layout
changes require separate measurements rather than combining unisolated changes.
