# Promotion-only HDT: A/A regression diagnosis

## Findings

All 168 processes succeeded. Two same-binary groups cross the earlier regression
screen: baseline A/A on path100k,q90,fresh (+6.11%, 3/4 slower) and candidate A/A
on path100k,q50,warmed (+10.32%, 4/4 slower). Same-binary median changes span
-39.82% to +10.32%. Thus this short-run measurement regime can produce apparent
regressions without an algorithm change.

Contemporaneous A/B crosses the screen in two cells: path100k,q50,warmed (+6.94%)
and path1M,q90,fresh (+14.43%), both 3/4 slower. The other five prior flags do not
reproduce under that screen in this follow-up. This weakens a stable, universal
regression interpretation but does not prove that the candidate has no cost.
Historical flags and raw measurements remain intact.

Compiled-code inspection finds no additional wrapper call on the ordinary
Forest::link return path. Its first 128 disassembled instructions and entry
address are unchanged. Promotion code grows 516 bytes and later symbols move;
that is evidence of a layout change, not evidence that layout caused the timing
changes. The current diagnosis is **measurement variability is demonstrated;
a persistent candidate cost and its cause remain unresolved**.

Keep the patch isolated. The next useful experiment is a controlled harness
with enough replay work per sample to reduce sensitivity to short intervals,
using prebuilt independent graph states to preserve the mutation sequence and
keeping setup separate. First validate that harness with A/A; then repeat A/B on
the two remaining flagged cases and a block case. Preserve the current harness
and trace identities as references. Do not repeatedly rerun the same short test
until its sign becomes favorable. This harness change is proposed, not implemented.

## Measurements

Adaptive follow-up on all seven previously flagged cells. Same frozen binaries and traces; four balanced pairs per cell and mode, interleaved in seed42 order. [Protocol](protocol.md). Historical flags remain unchanged; these are not independent randomly selected workloads.

A/A compares the exact same executable path and SHA-256 on both sides. Negative means right-side median is lower. A/B compares baseline (left) with candidate (right). Percentage is ratio of medians, not median pair change. No outliers removed, no A/A subtraction and no pooling with earlier measurements.

| Cell | Workload | Nodes | Query % | Regime | Original A/B change |
|---:|---|---:|---:|---|---:|
| 0 | dense-bridge-churn-v1 | 512 | 10 | warmed | +5.13% |
| 1 | sustained-churn-path-v1 | 100000 | 10 | warmed | +5.12% |
| 2 | sustained-churn-path-v1 | 100000 | 50 | warmed | +14.93% |
| 3 | sustained-churn-path-v1 | 100000 | 90 | fresh | +28.54% |
| 4 | sustained-churn-path-v1 | 1000000 | 10 | fresh | +22.42% |
| 5 | sustained-churn-path-v1 | 1000000 | 50 | warmed | +18.62% |
| 6 | sustained-churn-path-v1 | 1000000 | 90 | fresh | +17.78% |

| Cell | Mode | Left ms | Right ms | Change | Slower pairs | >5% and ≥3 slower |
|---:|---|---:|---:|---:|---:|---|
| 0 | AA_after | 9.116 | 9.305 | +2.07% | 3/4 | no |
| 0 | AA_before | 8.769 | 8.757 | -0.13% | 2/4 | no |
| 0 | AB | 9.132 | 8.963 | -1.86% | 1/4 | no |
| 1 | AA_after | 3.440 | 3.685 | +7.11% | 2/4 | no |
| 1 | AA_before | 3.641 | 3.627 | -0.38% | 1/4 | no |
| 1 | AB | 3.801 | 3.637 | -4.33% | 1/4 | no |
| 2 | AA_after | 2.998 | 3.307 | +10.32% | 4/4 | yes |
| 2 | AA_before | 3.267 | 2.866 | -12.27% | 0/4 | no |
| 2 | AB | 3.154 | 3.373 | +6.94% | 3/4 | yes |
| 3 | AA_after | 2.523 | 2.210 | -12.40% | 1/4 | no |
| 3 | AA_before | 2.583 | 2.740 | +6.11% | 3/4 | yes |
| 3 | AB | 2.595 | 2.182 | -15.93% | 0/4 | no |
| 4 | AA_after | 11.734 | 8.887 | -24.27% | 1/4 | no |
| 4 | AA_before | 11.355 | 11.912 | +4.90% | 3/4 | no |
| 4 | AB | 17.033 | 10.279 | -39.65% | 1/4 | no |
| 5 | AA_after | 6.640 | 7.162 | +7.87% | 2/4 | no |
| 5 | AA_before | 8.852 | 8.428 | -4.80% | 1/4 | no |
| 5 | AB | 6.940 | 6.628 | -4.50% | 2/4 | no |
| 6 | AA_after | 8.145 | 7.600 | -6.69% | 2/4 | no |
| 6 | AA_before | 13.887 | 8.357 | -39.82% | 1/4 | no |
| 6 | AB | 6.846 | 7.833 | +14.43% | 3/4 | yes |

Four pairs are limited evidence, not an equivalence test. An A/A flag demonstrates that the engineering screen can fire without an algorithm change. It does not prove every A/B regression is noise; lack of an A/A flag does not establish negligible noise. No automatic integration follows.

Raw operation totals and latency percentiles remain in each process JSON; [comparison.json](comparison.json) includes runtime/setup/RSS ranges and pair changes. Warmed uses a separate untimed graph replay; no hardware-cache flush or answer cache. Workload time excludes setup but includes harness work. RSS is whole-process.

See [compiled-code inspection](assembly.md) and [audit](audit.json). Production sources and historical results are preserved.
