# Decision: keep the rank-zero shortcut experimental

Do not integrate this candidate into the production checkout yet. Preserve the
patch and both frozen binaries as an experiment; the current HDT implementation,
engine configuration and default stay unchanged.

The initial 228-process matrix shows a small mixed result: sparse cell changes
have median -0.81% (15/24 faster); dense changes have median +0.78% (5/12 faster).
These summaries are not an aggregate speedup. The separate adaptive confirmation
adds 64 processes and finds a repeatable narrow benefit on warmed 1M cyclic blocks
with 90% queries: -3.73% median runtime, faster in 8/8 pairs. The initial path
regressions do not reproduce at their original magnitudes. All 292 timed processes
succeeded. See the [confirmation](../2026-10-06-hdt-reroot-confirmation/README.md).

The [structural comparison](structural-comparison.json) explains why eligibility
is misleading: although half of promotion reroot calls have rank zero, eliminating
them removes only 1.42% of pull calls and 1.49% of join calls inside tree promotions
at 1M nodes / 90% queries; split entries fall 8.94%. Most eligible calls are already
small. Two runs per variant per trace return identical counts; the same promotions
by source level and the same HDT aggregate counters are preserved. These are
function-entry counts, not CPU-time shares or predicted speedups.

The next useful experiment should target nontrivial reroot/concatenation work
inside higher-level tree links, which still accounts for almost all remaining
forest work. In particular, measure the duplicated root/rank parent traversals
and the split used by concatenation before choosing one change. A fused traversal
or a different join construction should be tested separately, with the same
before/after policy; do not bundle it with this shortcut. No faster asymptotic
complexity or automatic engine selection is justified by these measurements.

All prior results are preserved. The candidate remains a small isolated
algorithm patch with tests, not a committed feature. Source-isolation metadata
records the omitted toolchain pin files and verifies the effective compiler;
order-audit records the globally alternating order and per-cell imbalance.
