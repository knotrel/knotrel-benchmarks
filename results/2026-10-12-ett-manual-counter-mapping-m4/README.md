# ETT manual-counter mapping probe on Apple M4 — 2026-10-12

This experiment establishes whether the manual CPU Counters template can be
interpreted from its XML export. It never modifies the original user-provided
template. Instead, it creates `xctrace --recording-options` JSON derivatives
outside the worktree:

1. one derivative per configured event;
2. one derivative containing all eight events in reverse order.

Every recording reuses the validated signpost-enabled `before` warmed-path
binary. A trustworthy mapping requires that each single-event export has one
counter value, and that the reverse configuration reverses the full
configuration's value positions. A mere match between template order and an
anonymous array is explicitly insufficient.
