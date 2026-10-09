# Right-associated tour joins — pilot

Keep the exact sequence left, ab, right, ba. Replace (left + ab + right) + ba
with left + ab + (right + ba), using the same AVL join routine. Do not combine
prior candidates. AVL shape may change; connectivity, tour order, candidate
incidences and all aggregates must remain correct. Explicit cyclic-order tests
run on both variants; full core tests/doctests run on the candidate.

Use the same eight-cell pilot as concat: blocks100k/1M,q90,fresh/warmed;
path1M,q50,fresh; dense bridge512,q90,warmed; Cogentco fresh/warmed. Four paired
trials/cell, balanced 2/2 order, seed42 shuffle, 64 processes. Preserve errors,
trace identities, oracle answers, HDT counters, setup, tails and process RSS.

Predeclared gate: expand to the full 38-cell matrix only if at least 3 of 4 block
cells improve median workload wall runtime >=3%, each with >=3 of 4 faster pairs,
and no control regresses >5% with at least 3 slower pairs. Otherwise keep experimental.
The gate is an engineering screen, not significance. Full follow-up is separate,
never pooled with the pilot. All historical results and patches remain intact.

Structural counters run outside timed measurement. Count link-side tour sizes
and forest work by promotion scope; do not interpret calls as CPU-time shares.
