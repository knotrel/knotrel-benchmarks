# Promotion-only right-associated joins — bounded experiment

Apply right association only in HdtGraph::promote for tree edges, at destination
level i+1 (always above zero). Keep ordinary Forest::link and level-zero construction
on the existing association. Preserve exact cyclic order, AVL/parent/aggregate
invariants, oracle answers and HDT counters. Do not combine previous candidates.
No public configuration or API change; isolated candidate only.

Use the previous eight pilot cells plus warmed path1M,q50, since that control
showed a possible regression. Four pairs per cell, balanced 2/2 order, shuffle42,
72 sequential processes; same frozen reference traces. Preserve setup, RSS and
operation latency tails. Warm-up replays a separate graph; no answer cache or
hardware cache flush. No heavy work concurrent with timings.

Gate before measurement: at least 3 of 4 block cells improve median workload wall
runtime >=3%, each with >=3/4 faster pairs; no control worsens >5% with >=3 slower
pairs; all cases complete successfully. This is an engineering screen, not
statistical significance. If passed, a full matrix is the next validation step,
not automatic production integration. Report failures and keep history intact.

Explicit order/aggregate test exercises the new promoted-link entry point,
including reversed relinks and token reuse. Record missing-method red separately
from behavioral correctness: the baseline is correct. Run full workspace checks.
