# ETT cut structural diagnosis

Identical instrumentation in the baseline and direct-join candidate. Each of
three traces replayed twice per variant in fresh processes: 12 successful runs.
Repeated outputs match exactly. Production source hashes remain unchanged.
Oracle answers and historical trace fingerprints match. No elapsed times are measured.

| Workload | Phase | Counter | Before | After | Change |
|---|---|---|---:|---:|---:|
| dense-bridge-churn-v1 | detach | root_calls | 50 | 50 | +0.00% |
| dense-bridge-churn-v1 | detach | rank_calls | 100 | 100 | +0.00% |
| dense-bridge-churn-v1 | detach | split_entries | 2800 | 2900 | +3.57% |
| dense-bridge-churn-v1 | detach | join_entries | 3400 | 3600 | +5.88% |
| dense-bridge-churn-v1 | detach | pulls | 3400 | 3600 | +5.88% |
| dense-bridge-churn-v1 | search | root_calls | 6477100 | 6477100 | +0.00% |
| dense-bridge-churn-v1 | search | root_steps | 49861000 | 58243100 | +16.81% |
| dense-bridge-churn-v1 | search | candidate_tokens | 25550 | 38150 | +49.32% |
| redundant-bridge-churn-v1 | detach | root_calls | 42 | 42 | +0.00% |
| redundant-bridge-churn-v1 | detach | rank_calls | 84 | 84 | +0.00% |
| redundant-bridge-churn-v1 | detach | split_entries | 2315 | 2338 | +0.99% |
| redundant-bridge-churn-v1 | detach | join_entries | 2871 | 2882 | +0.38% |
| redundant-bridge-churn-v1 | detach | pulls | 2931 | 2882 | -1.67% |
| redundant-bridge-churn-v1 | detach | rotations | 30 | 0 | -100.00% |
| redundant-bridge-churn-v1 | search | root_calls | 4015860 | 4015860 | +0.00% |
| redundant-bridge-churn-v1 | search | root_steps | 30908718 | 36105612 | +16.81% |
| redundant-bridge-churn-v1 | search | candidate_tokens | 15940 | 23752 | +49.01% |
| redundant-bridge-churn-v1 | repair | root_calls | 36 | 36 | +0.00% |
| redundant-bridge-churn-v1 | repair | root_steps | 310 | 324 | +4.52% |
| redundant-bridge-churn-v1 | repair | rank_calls | 36 | 36 | +0.00% |
| redundant-bridge-churn-v1 | repair | rank_steps | 310 | 324 | +4.52% |
| redundant-bridge-churn-v1 | repair | split_entries | 1160 | 604 | -47.93% |
| redundant-bridge-churn-v1 | repair | join_entries | 1689 | 1059 | -37.30% |
| redundant-bridge-churn-v1 | repair | pulls | 1717 | 1115 | -35.06% |
| redundant-bridge-churn-v1 | repair | rotations | 14 | 28 | +100.00% |
| redundant-bridge-churn-v1 | repair | mark_visits | 66 | 66 | +0.00% |
| sustained-churn-path-v1 | detach | root_calls | 418 | 418 | +0.00% |
| sustained-churn-path-v1 | detach | root_steps | 1354 | 1363 | +0.66% |
| sustained-churn-path-v1 | detach | rank_calls | 836 | 836 | +0.00% |
| sustained-churn-path-v1 | detach | rank_steps | 2459 | 2472 | +0.53% |
| sustained-churn-path-v1 | detach | split_entries | 11654 | 11672 | +0.15% |
| sustained-churn-path-v1 | detach | join_entries | 12194 | 12200 | +0.05% |
| sustained-churn-path-v1 | detach | pulls | 13742 | 13740 | -0.01% |
| sustained-churn-path-v1 | detach | rotations | 774 | 770 | -0.52% |
| sustained-churn-path-v1 | search | root_calls | 836 | 836 | +0.00% |
| sustained-churn-path-v1 | search | root_steps | 2028 | 2031 | +0.15% |

Counts above sum tree-cut operations only. Split/join counts include recursive
and base-case calls; root/rank steps count parent edges actually followed.
Candidate tokens count iterator stack pops, including non-yielded structural tokens.
Other includes endpoint and candidate-mark work outside the three named phases.
Counter increments perturb execution but not token layout. Count changes do not
quantify time shares or establish cache/scheduling causality. Original uninstrumented
[timing observations](../2026-10-10-ett-direct-joins/README.md) remain separate.

[Full analysis](analysis.json) retains all operation groups; raw files retain
per-operation counters. [Protocol](protocol.md), [builds](builds.json),
[verification](verification.json). No production changes, staging or commits.

## Finding and next candidate

In the primary dense trace, both variants examine 3,238,500 candidate edges
and 12,750 vertices across 50 tree cuts, with zero replacements. Search root
calls remain 6,477,100, but parent steps rise from 49,861,000 to 58,243,100
(+16.81%). Candidate iterator token visits rise from 25,550 to 38,150 (+49.32%).
Detach joins/pulls increase only from 3,400 to 3,600. These counts identify
additional search traversal work; they are not comparable units of CPU time.

The redundant-bridge control has the same direction: search parent steps
30,908,718 → 36,105,612 (+16.81%), despite identical ordinary scan counters.
The path control has no candidate edges, with almost unchanged structural work.
This supports an additional root-traversal explanation for the observed dense
regression, without assigning an exact fraction of elapsed time to that mechanism.

A targeted next candidate is to retain the smaller component's root for the
lifetime of the replacement scan, and compare only each candidate target's root
against it. Every enumerated source belongs to that component; the forest is
immutable during enumeration. This can remove repeated source-root traversal
without caching connectivity answers across mutations, changing scan order or
adding O(V) scratch storage. Verify iterator/borrow invariants and benchmark it
separately against the current production ETT, not the rejected direct-join
candidate. No such optimization is integrated by this diagnostic study.

## Verification and review

Both variants passed core tests and release builds. The candidate diagnostic
workspace passed formatting, all-target Clippy, tests/doctests and Rustdoc in
both repositories; this is not a claim of full workspace checks on both variants.
Independent read-only review confirmed that removing forest counter increments
recovers the original snapshots byte-for-byte and that dynamic.rs adds only
phase scopes. All 12 processes, repeats, fingerprints and answers were checked.

`mark_visits` means mark-propagation token visits, including the starting token
and the final unchanged token; it is not strictly a count of ancestors. Earlier
protocol/source shorthand should be interpreted using this precise definition.
