# ETT scan-root reuse: focused correctness review

## Verdict

No correctness defect was found in the candidate patch. The replacement-search
substitution is semantically sound under a concrete forest-component invariant,
and the relevant isolated-candidate tests passed. The patch is therefore
**correctness-safe to integrate** at the reviewed revision.

This is not a recommendation to enable it as a general production optimization:
the separate performance evidence remains workload-specific and path behavior
is unresolved.

## Invariant and equivalence

Immediately after `self.forest.cut(arcs)`, let `R` be the Euler-tour root of
the smaller of the two components selected by `smaller_candidates(a, b)`.
During the lifetime of `Candidates`:

1. `Candidates::root` is `R`, selected from the post-cut roots using their
   `vertices` counts (with the existing deterministic tie choice).
2. Every `v` yielded by `Candidates::next()` belongs to `R`'s component. The
   traversal begins at `R` and descends only its token-tree children; pruning
   can omit vertices but cannot yield a vertex from another component.
3. The immutable `&Forest` held by `Candidates` prevents `cut`, `link`, root
   rotation, or candidate-flag mutation until the scan is no longer used.
   Consequently, `R` remains the root of every yielded `v`.

For every candidate incidence `(v, w)` examined by the loop:

```text
forest.connected(v, w)
  <=> root(vertex_token(v)) == root(vertex_token(w))
  <=> R == root(vertex_token(w))
  <=> candidates.contains_vertex(w)
```

Thus `!candidates.contains_vertex(w)` finds exactly the same crossing
replacement edge as `!forest.connected(v, w)`.

## Lifecycle cases reviewed

| Case | Review result |
| --- | --- |
| Component selection | Roots are recomputed after the tree cut, then the smaller root is captured. Equal sizes retain the existing `a`-side tie selection; either side is complete for replacement search because every non-tree edge is stored at both endpoints. |
| Empty candidate set | `has_candidates` leaves the stack empty. No `v` is yielded and both old/new searches find no replacement. |
| Pruned scan | `has_candidates` skips empty subtrees only. A yielded `v` is still in the captured component; unmarked `w` membership does not depend on its candidate flag. |
| Crossing replacement | The first `w` outside `R` is exactly the first old `!connected(v, w)` result. The loop exits before mutating the forest. |
| No replacement | Every examined `w` belongs to `R`; iterator exhaustion proves the same absence of crossing non-tree edges as the old loop. |
| Mutation after discovery | Candidate-edge removal, candidate-flag repair, and `forest.link(v, w)` occur only after the iterator has no further use. Rust's borrow checker enforces that the immutable forest borrow cannot overlap the mutable link. |
| Early exit | A replacement can break with unvisited iterator stack entries. The borrow still ends before the subsequent mutation; no cached root is used after it. |
| Iterator exhaustion and later mutations | `contains_vertex` remains valid after exhaustion while the immutable borrow lives. A new scan after `cut` or `link` computes a new root; the candidate unit test covers this sequence. |

## Test evidence

The tested source hashes matched the profiled after binary:

| File | SHA-256 |
| --- | --- |
| `forest.rs` | `74d68ac0d189d8878eb9d5e88c68744e4e25f148cd03b2e484266912c0abaac6` |
| `dynamic.rs` | `86669dcaab49850aff82e38f4f576c1943fa28bea6315c0aa5f5f87b5ecfc91d` |

In `/private/tmp/knotrel-ett-signpost-m4-cfdokimi`, with Cargo locked:

| Test scope | Result |
| --- | ---: |
| Core unit tests, including `scan_root_tests` and internal structural invariant differential test | 14 passed |
| Core `connectivity.rs`, including independent transitive closure and `ReferenceGraph` differential histories | 7 passed |
| Core `forest.rs`, including replacement discovery, early exit, candidate pruning, random matrix/reference history, and post-replacement cleanup | 6 passed |
| Benchmark dense workload oracle | 2 passed |
| Benchmark engine semantics/cache-invalidation tests | 3 passed |
| Benchmark sustained workload independent matrix oracle | 5 passed |

The pre-existing isolated-candidate verification had also passed workspace
formatting, Clippy with warnings denied, workspace tests, and Rustdoc.

## Coverage gaps and remaining risks

No test directly asserts the equivalence above for **every** yielded `v` and
every possible `w` in a single scan; existing tests establish it through
membership cases plus end-to-end differential histories. A future test could
make that algebraic property explicit across equal-size and unequal-size
components, a crossing edge, and an internal non-tree edge. This is a test
coverage improvement, not evidence of a defect.

The internal 3,000-step invariant test and external randomized/matrix
differential tests are deterministic, bounded histories. They do not constitute
a formal proof over arbitrary graph histories. The API is crate-private, so
external callers cannot retain `Candidates` and misuse its captured root.

The material remaining risk is performance-policy, not correctness: the
candidate is strongly beneficial for dense replacement scans but its path
outcomes are variable. Keep the integration decision gated on the intended
workload scope; see [implementation-assessment.md](implementation-assessment.md)
and [report.md](report.md).
