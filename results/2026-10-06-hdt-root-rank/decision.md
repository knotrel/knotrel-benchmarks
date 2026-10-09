# Decision — completed 2026-10-07

Keep the single-pass lookup as a preserved experimental patch. Production core
and engine defaults remain unchanged. Do not combine it with the rank-zero
candidate without a separate paired experiment.

All 304 timed processes succeeded, covering 38 cells with four pairs each,
balanced two before-first and two after-first per cell. Sparse results improve
in 19/24 cells, with a median cell change of -1.24%; dense results improve in
3/12 cells, with median +0.26%; Cogentco improves in one of two regimes.
The warmed 1M-block/90%-query target has -3.46% median runtime, faster in 3/4
pairs. The matrix remains mixed and the improvements are small. Observed
individual regressions (up to +13.53%) are retained; four pairs do not establish
that these are stable regressions, and no causal explanation is asserted.

The mechanism is verified. On the 1M-block/90%-query trace, parent steps inside
tree promotions fall from 68,940,822 to 34,470,411, exactly 50%. At 100k they fall
from 4,949,814 to 2,474,907. Both independent repeated runs match. Promotions by
level, materialized endpoint records and forest pull/join/split counts remain
identical. The 1M case still performs 152,549,086 join entries, 160,524,732 pull
entries and 50,998,602 split entries inside tree promotions. Function-entry
counts include recursion and base cases; they are not timing shares.

This establishes that duplicate parent walks exist and can be removed, but
removing them does not substantially change the workload cost in this campaign.
The next investigation should examine the split/concat/join work used to build
promoted forests, with a clearly isolated change and the same controls. A bulk
promotion or forest-build algorithm would require a separate design and proof
that level nesting, tour order and candidate incidence invariants are preserved.
No such algorithm is implemented or benchmarked here.

The candidate patch, full before/after source files, independent lookup test,
compiler/build metadata and raw results are saved in this repository checkout.
The earlier rank-zero patch is preserved separately. Neither patch has been
staged or committed by this task; see the [inventory](../../docs/experiments/2026-10-06-hdt-candidates.md).
