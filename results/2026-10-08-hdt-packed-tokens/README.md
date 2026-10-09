# HDT packed token indices

## Decision

The pilot runtime screen passes: 3/4 qualifying block cells and 0 control flags. Keep the candidate isolated pending broader validation; no production integration or commit follows this pilot.

## Practical findings

All 72 processes succeeded with identical trace identities, oracle answers,
operation counts and paired HDT counters. The four block runtime changes are
-8.27%, -9.18%, -7.94% and -1.21%; the first three qualify under the pilot screen.
The 1M warmed path is essentially tied (-0.07%) with only one faster pair out of
four; do not describe that as a robust speedup. No control meets the regression
screen. Short-run variability remains relevant.

Whole-process peak RSS medians fall 10.65%–17.16% on the large sparse cells;
the 1M path falls about 14.2%. Small Cogentco RSS is unchanged. Setup is not
uniformly faster: the 100k block cells increase about 3.7%–3.8%, retained below.
The exact 33.33% token-size reduction should not be substituted for these total
process measurements.

This is a promising memory candidate, not ready for general integration on the
pilot alone. Next run the full 38-cell optimization reference matrix, preserving
this candidate separately from promotion-join reassociation. Combining them now
would obscure the individual tradeoffs.

## Representation and correctness

The four optional indices in each HDT token now use a private `Index(Option<NonZeroUsize>)`, encoding index+1 and reserving zero for absence. External forest handles, graph node IDs and algorithm signatures retain usize/u64 semantics. Each read decodes and each write encodes; AVL operations and sequence order are unchanged. No earlier join/reroot candidate or page preparation is combined.

On the measured 64-bit target the token shrinks from **96 to 64 bytes (-33.33%)**. This is exact layout evidence, not a claim that total memory or RSS falls one third. The storage counter continues using actual `size_of::<Token>()`. Three million initialized tokens save roughly 96 MB of payload, before capacity rounding and other graph storage.

Checked encoding rejects usize::MAX; every valid stored index identifies a Vec element and cannot have that value. Tests cover None, index zero, max-1, clearing and rejected overflow, as well as the 64-byte budget and capacity accounting. The layout test failed at 96 bytes on baseline and passes at 64 after. Complete core tests/doctests pass, including rotations, splits, marked vertices, sparse level translation, growth, deletion and token reuse.

## Paired pilot

Same nine cells as the promotion-only pilot, four balanced pairs/cell, 72 sequential processes, frozen before/after binaries. No warming intervention; the original zero/one warmup regimes remain. See [protocol](protocol.md). Historical investigations demonstrated variability on short path replays, so runtime observations are provisional. The layout saving itself is deterministic.

| Workload | Nodes | Query % | Regime | Before ms | After ms | Runtime change | Faster pairs | RSS before MiB | RSS after MiB | RSS change | Setup change |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | — | fresh | 0.518 | 0.476 | -8.05% | 3/4 | 3.6 | 3.6 | +0.00% | -9.62% |
| topology-zoo-outages-v1 | 197 | — | warmed | 0.444 | 0.423 | -4.73% | 4/4 | 3.6 | 3.6 | +0.00% | -3.48% |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.327 | 8.092 | -2.82% | 4/4 | 13.8 | 13.8 | -0.11% | +0.24% |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 216.347 | 198.447 | -8.27% | 4/4 | 205.3 | 170.0 | -17.16% | +3.69% |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 216.368 | 196.498 | -9.18% | 4/4 | 206.8 | 183.1 | -11.50% | +3.81% |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3499.678 | 3221.737 | -7.94% | 4/4 | 1542.9 | 1345.0 | -12.83% | -4.00% |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3306.611 | 3266.538 | -1.21% | 3/4 | 1621.4 | 1448.7 | -10.65% | +0.89% |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 7.390 | 6.872 | -7.01% | 3/4 | 684.6 | 587.4 | -14.21% | -1.04% |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 6.024 | 6.020 | -0.07% | 1/4 | 684.5 | 587.4 | -14.20% | -0.32% |

Percent change is `100*(after median/before median-1)`. Negative runtime change is faster. Whole-process peak RSS includes trace, allocator retention, warmup and harness, not only graph payload. Setup is separate from workload wall time; wall time includes checks and timer/sample overhead. Warmed replays a separate graph; there is no answer cache or hardware cache flush.

All planned cells and failures are retained in [comparison.json](comparison.json), with before/after ranges, pair directions and operation p50/p95/p99. No pooling across runs or comparison to unmeasured competitors. The [gate](gate.json) is an engineering screen, not statistical significance.

## Artifacts and verification

[Candidate patch](candidate.patch), complete before/after forest sources, compiler/source/binary hashes and original measurements are saved independently of temporary workspaces. [Reconstruction verification](reconstruction-verification.json) checks formatting, workspace Clippy, workspace tests/doctests and Rustdoc. [Audit](audit.json) checks measurement integrity and balanced order. Production source hashes remain those of the frozen ranking; user staging is untouched.
