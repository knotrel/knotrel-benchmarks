# Packed HDT tokens: bounded pilot

Replace only the four optional token indices (left/right/parent/vertex) with
index+1 encoded as Option<NonZeroUsize>. Preserve raw usize handles at algorithm
boundaries and all node IDs, AVL operations, ordering and HDT behavior. No unsafe,
new dependencies, page preparation, or combination with prior candidates.
On the current 64-bit target, test Token size 96 -> 64 bytes (-33.33%); encoded
indices round-trip None/zero/max-1 and reject usize::MAX. Valid Vec element indices
cannot equal usize::MAX. Storage accounting must follow actual Token size.

Run complete core tests, formatting, Clippy and documentation checks. Freeze both
release binaries. Same nine-cell pilot as promotion-only joins, four paired
trials/cell, balanced2/2, shuffle42,72sequentialprocesses. Keep traces/oracle/HDT
counters identical; preserve raw results, setup and whole-process RSS. No page
warming intervention. Original fresh/warmed regimes; short-run variability remains
known and must qualify runtime claims. No statistical significance claim.

Retain the existing pilot runtime screen: >=3 of4 block cells improve median>=3%
and >=3/4 faster pairs; no control >5% slower with>=3slowerpairs. Also report every
RSS/setup/latency regression. Deterministic token-byte saving is distinct from
allocator/whole-process RSS. Passing does not authorize automatic integration;
full reference matrix remains separate. No staging or commits.
