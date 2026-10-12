# Manual-counter export analysis

Both fixed warmed-path recordings exited successfully and contain the expected
`OSSignpostIntervals` rows. The CPU Counters export has timestamped
`counters-profile` rows with process, thread, core, thread state, and
`pmc-events`.

The result is not sufficient to name the values. The `counters-profile` schema
labels the field only as `Counter Value Array`; no row, column, or auxiliary
CPU Counters export names an element as `FIXED_CYCLES`,
`CORE_ACTIVE_CYCLES`, `BRANCH_MISPRED_NON_SPEC`, `IFU_CACHE_MISS_DEMAND`,
`INST_ALL`, `L1D_CACHE_RD`, `L1D_CACHE_LMISS_RD`, or `IFU_STALL_BACKEND`.
It contains sixteen values with the first eight repeated. Other counter
exports can contain eight values but likewise have no per-position label.

The template's `allEventsAndFormulas` preserves the requested event order, but
that configuration order is not an export-side proof of position-to-event
mapping or of the duplicated group semantics. Consequently, these values must
not be reported as cycles, instructions, branch mispredictions, cache
statistics, or backend stalls, and no large manual-counter campaign was
started.

The next valid route is a separately predeclared mapping probe using derivative
one-event templates, or a documented Instruments export whose schema includes
both the PMC value and its event name. Neither changes the user-provided
template nor the production repositories.
