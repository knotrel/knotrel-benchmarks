# ETT scan-root reuse: implementation assessment

## Confirmed implementation facts

The candidate changes only the replacement-search membership test after a tree
cut. `Candidates` already finds and selects the smaller-component root. The
candidate stores that existing root in the iterator and adds
`contains_vertex(vertex)`, which tests:

```text
root(vertex) == captured_smaller_component_root
```

The replacement loop changes from `forest.connected(v, w)` to
`!candidates.contains_vertex(w)`. Every scanned `v` is already in the captured
component, so the candidate removes precisely the redundant `root(v)` walk and
retains the necessary `root(w)` walk. The immutable iterator borrow prevents
forest mutation while the captured root is used; mutation for a replacement
occurs after the iterator is no longer used.

The candidate does **not** change candidate pruning, scan order, non-tree
adjacency (`BTreeSet`), Euler-tour tree mutation, replacement choice, or
allocation strategy. It adds one `usize` to the stack-resident iterator. No
heap allocation is introduced by the change.

For `c` tested non-tree incidences, the relevant membership work changes from
approximately `2c * O(log V)` root walks to `c * O(log V)`, plus the one root
that was already found to select the smaller component. The asymptotic bound is
unchanged; this is a substantial constant-factor reduction only where `c` is
large.

## Correlation with workload evidence

| Evidence | Confirmed observation | What it supports |
| --- | --- | --- |
| Dense structural audit, 512 vertices, 90% queries, 10 rounds | Candidate incidences and scanned vertices are unchanged at 3,238,500 and 12,750. Root calls fall 6,477,150 → 3,238,650; parent steps fall 58,243,100 → 29,122,000. | Exactly one source-root walk is removed per candidate incidence; logical work and answers are preserved. |
| Same dense audit | `cut` total falls 37.105 ms → 21.243 ms; links and queries are small relative to cuts. | The saved AVL parent traversals coincide with the affected operation and explain why a large dense gain is mechanically plausible. It does not allocate a percentage of elapsed time to that change. |
| Current 12-pair dense-warmed campaign | Marker-duration median paired change is -44.67% (95% bootstrap CI -45.45% to -42.50%); 12/12 pairs are faster. | The dense benefit is reproducible under marker-scoped measurement. |
| Path structural results | `candidate_edges = 0` and `scanned_vertices = 0` for the one-million-node path. | The inner membership test is never executed; root reuse cannot directly speed this workload. |
| Current path campaigns | Fresh: -0.60% median paired change, CI -12.77% to 2.55%; warmed: +4.43%, CI -7.84% to 10.54%. | Neither path result establishes a candidate effect. Warmed has seven regressions. |
| Earlier blocks pilot | Nonzero scan workloads improved, for example 100k fresh blocks -26.28% (6/6 faster). | Supportive, but historical and not a causal proof for this campaign. |

`dense-bridge-churn-v1` consists of two fixed 256-vertex cliques joined by one
toggled bridge. A bridge cut has no cross-clique replacement, so it exhausts
the marked smaller clique's many internal non-tree incidences. This makes `c`
large and makes the eliminated source-root walk dominant. In contrast,
`sustained-churn-path-v1` has no non-tree edges: candidate flags are absent,
the iterator is empty, and the optimized membership test is not reached.

## Memory access and branching

The direct, source-level memory effect is fewer dependent loads through AVL
parent links for every candidate incidence. This is plausibly valuable in the
dense scan because the old source root is recomputed millions of times. The
candidate does not change `BTreeSet` iteration or candidate-token traversal,
so it does not remove the non-tree adjacency reads themselves.

The logical crossing-edge branch has the same condition and outcome as before;
only the work needed to evaluate source-component membership changes. The
manual-counter campaign found lower **per-sample median**
`BRANCH_MISPRED_NONSPEC` values for complete dense pairs, but its samples are
sparse, uneven, and not totals. That is compatible with less branch-heavy root
traversal, not evidence that branch misprediction caused the time reduction.
The campaign cannot establish cache-miss, allocator, TLB, frequency, or energy
mechanisms. In particular, `ARM_L1D_CACHE_LMISS_RD` is not a page-fault or TLB
measure.

On the path, the extra iterator word and the `for`-to-`while let` rewrite may
alter code layout, register allocation, or branch layout even though the
membership operation is unused. That is a plausible source of small behavior
changes, but no collected evidence identifies it as the cause of the path
variability. There is no source-level allocation regression: the same
stack-backed `TinyVec` is used and no new heap object is created.

## Trade-offs and recommendation

The candidate has a narrow and favorable trade-off:

- **Benefit:** removes one logarithmic AVL-root traversal per examined
  non-tree incidence, with a strong dense-scan benefit.
- **Cost:** one `usize` in a short-lived iterator plus a more specialized
  iterator API whose root-validity contract depends on its immutable borrow.
- **No demonstrated cost:** no change to persistent forest/graph storage, scan
  order, replacement semantics, or allocator behavior.
- **Unresolved cost:** path outcomes are variable, and the implementation
  change may perturb code generation even when no candidate edge is scanned.

Retain the implementation **as-is as an isolated candidate**: its mechanism is
minimal, its correctness boundary is enforced by Rust borrowing, and the
structural audit matches the dense performance result. Do not refine it
speculatively: caching more roots, changing candidate storage, or modifying
scan order would combine a proven constant-factor improvement with unmeasured
algorithmic changes. A production decision should require an explicit
acceptance of the workload-specific scope or a further predeclared experiment
that resolves the path variance; the current evidence does not support a
general-purpose integration claim.

The timing and hardware boundary conditions are detailed in
[report.md](report.md); the original candidate source delta is preserved in
[`../2026-10-10-ett-scan-root/candidate.patch`](../2026-10-10-ett-scan-root/candidate.patch).
