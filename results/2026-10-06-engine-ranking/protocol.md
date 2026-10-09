# Current five-engine ranking protocol — 2026-10-06

Freeze one shared release binary and source snapshot for Compact, Workspace,
ETT, current HDT and external petgraph. No production edits during collection.
Preserve all previous collections and report historical drift separately.

Main matrix: sparse path/blocks at 1,024, 10k, 100k and 1M vertices;
10/50/90% queries; dense one/two-bridge cliques at 128/512; Cogentco import.
Three trials per engine, fresh/warmed, ten synthetic rounds and seed 42.
Main ranking has 74 equal-weight cells. Repeat supplement: 10k sparse,
90% queries, two immediate repeats per query, three trials, reported separately.

Exploratory 10M: path/blocks, 50% queries, fresh/warmed, one trial for Compact,
Workspace and petgraph only. ETT/HDT not attempted at 10M in this session:
resource exposure on the shared 16GiB host is not justified before inspecting
1M data. This is an explicit scope limit, not a measured failure or capacity
ceiling. No full five-engine ranking may be reported for these four cells.

All runs sequential, seeded case shuffle, timeout 120s/process. Record failures
and partial output, not just successes. Rank complete main cells only; disclose
any incomplete cells and timeout counts. No memory cap is enforced. RSS is whole
process including trace/setup/warmup, not engine heap. No CPU-cache flushing.
Runtime excludes setup and includes replay dispatch/checking/sampling. Record
setup, operation p50/p95/p99 and RSS separately; do not aggregate them into one
score. Exactly compare fingerprints, operation counts and query outcomes.
