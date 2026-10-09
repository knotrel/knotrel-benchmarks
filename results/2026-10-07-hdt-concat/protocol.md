# Dedicated concat pivot extraction — pilot

Replace concat's generic split-at-last-rank with a right-spine extraction and
AVL deletion rebalancing. Preserve sequence, parents and aggregates. Tree shape
may change. Do not combine previous patches. Direct invariant tests and existing
core tests/doctests must pass before timing.

Eight cells: 100k/1M blocks,q90,fresh/warmed; 1M path,q50,fresh;
dense bridge512,q90,warmed; Cogentco fresh/warmed. Four sequential pairs/cell,
balanced 2/2 order, shuffle42. 64 processes. Same preserved traces. Retain all
failures and check answers, fingerprints, mutation counts and HDT counters.
Runtime is workload wall time; setup, tails and whole-process RSS are separate.

Predeclared screening gate: expand to all 38 prior cells only if at least 3 of 4
block cells improve median runtime >=3%, each with >=3 of 4 faster pairs, and
no control regresses >5% with at least 3 slower pairs. Otherwise retain the pilot as
experimental. This is an engineering screen, not statistical significance.
Never pool selected follow-up results with the initial pilot.

Structural probes run separately from timings. Report pop_last call counts
alongside replaced split/join work; do not add unlike function counts to infer
speedup. Earlier baselines and candidate patches remain unchanged.
