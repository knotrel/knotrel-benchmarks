# Optimization reference and before/after policy

The 2026-10-04 connectivity campaign is the persistent regression reference.
Never overwrite its raw measurements, manifests, snapshots or hashes. New studies
use new directories, include negative results, and reference the original cells.

First experiment: caller-owned compact BFS workspace. Keep `compact-bfs` unchanged
and measure `compact-workspace` in the same release build with identical traces.
Run the complete sparse, dense, repeated-query and Cogentco matrix for both.
Compare replay runtime, query and mutation p50/p95/p99, setup and peak process RSS.
Validate trace fingerprint identity against the historical campaign. Separate
same-build treatment deltas from shifts versus historical machine timings.

API scope: optional Graph method, independent caller-owned workspace. No change
to default engine, server behavior or shared `&self` semantics. No answer cache.
Both variants reuse queue and visited allocation. Preserved v1 clears touched
nodes; v2 uses u32 generation marks (four bytes per registered node), with a
full retained-array clear on generation rollover. Keep both experiment records.

Acceptance is evidence-based: query-heavy benefit must be assessed together with
regressions, memory and short-lived graph startup cost. Two trials and one seed
remain exploratory; any proposed default change requires broader confirmation.

Next stages: profile HDT replacement/promotions against the same traces, then ETT
candidate-search/storage. Every implementation proposal repeats this protocol;
keep diagnostic timings separate from normal benchmark timings. An unsuccessful
optimization is a recorded outcome, not grounds for changing the test matrix.
