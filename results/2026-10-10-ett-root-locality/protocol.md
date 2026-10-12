# Root locality diagnostic

Xcode Instruments is unavailable (xcrun cannot find xctrace; selected developer
path is CommandLineTools). Do not substitute statistical stack sampling of graph
setup for a 5–10 ms replay profile.

Instrument only parent-field reads in GenericForest::root in isolated copies.
Record logical token index and byte coordinate relative to the arena's first
page, retaining its actual page alignment. Host sysctl reports 16,384-byte pages
and 128-byte cache lines. These are virtual-address coverage measurements, not
cache misses, physical page placement, residency, TLB misses or CPU placement.
No production changes and no unsafe dereferences. Start after setup, stop before
summaries. Recorder allocations perturb state; all instrumented timings ignored.

Eight fixed runs: before/after × fresh/warmed × two repeats, path1M q50,
10 rounds seed42. Preserve oracle checks and complete ordered traces. Compare
ordered logical indices exactly, unique tokens, unique lines/pages, transitions
and arena alignment. Root access coverage is not coverage of all graph accesses.
No integration or performance acceptance follows this structural experiment.
