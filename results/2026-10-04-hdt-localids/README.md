# HDT promotion endpoint reuse — before/after

This experiment changes **Knotrel's experimental HDT backend**, not an external
product. Incidence insertion returns the local endpoint indices it already
resolved; tree promotion passes them directly to the upper-level Euler-tour
forest. This avoids two successful local-map lookups per tree promotion.
HDT invariants, public APIs, default backend and configuration are unchanged.
The 100k-node cyclic-block / 90% query trace performs 212,272 tree promotions,
so this removes 424,544 redundant endpoint lookups, not the promotions themselves.

## Measurement contract

272 successful processes replay all 136 HDT reference cases from the preserved
[connectivity campaign](../2026-10-04-connectivity-campaign/README.md): sparse,
dense, repeated queries and real Cogentco topology. Each case uses frozen before
and after release executables, adjacent and with alternating execution order;
case order is shuffled with seed 42. There are 66 scenario cells, with two trials
per synthetic cell and four per Cogentco cell. Every trace fingerprint and every
HDT work counter equals its original reference. Other engines were not rerun;
this is a comparison against the previous Knotrel HDT implementation.

`manifest.json` preserves both revisions, source and binary SHA-256, commands,
compiler/platform and artifact hashes; `core-after.patch` preserves the change.
Both binaries retain the algorithm identity `knotrel-core/hdt-sparse-levels-v3`.
Use the manifest variant/build snapshot, not the reports' checkout-at-run-time
metadata, to identify compiled source: both binaries ran against the modified
checkout. Both builds used `cargo build --release --locked --bin knotrel-benchmarks`.
Build-time environment overrides (RUSTFLAGS, profile/target configuration) were
**not captured**; identical effective build settings cannot be independently
verified from these snapshots. This is a reproducibility limitation.

Fresh means no harness warmup; warmed means one untimed replay on a separate
fresh graph. Neither flushes hardware caches. Repeated queries remain separately
reported; no answer cache was added. RSS is peak **whole-process** memory,
including setup, validation and traces, not engine heap size.

## Results

All percentages are `100 × (after / before − 1)`; negative means lower cost.
The baseline is the concurrently collected **before** executable, not the old
campaign's timing. Values summarize per-process medians; operation percentiles
are never pooled. Full metrics, sample ranges and historical timing drift are
in [comparison.json](comparison.json), regenerated with `python3 .../compare.py`.

| Family | Cells with lower runtime / total | Runtime delta range | Median cell delta |
|---|---:|---:|---:|
| sparse | 25/36 | -16.00% to +11.89% | -1.59% |
| dense | 7/24 | -4.43% to +5.65% | +1.40% |
| repeats | 3/4 | -24.40% to +4.32% | -7.64% |
| cogentco | 2/2 | -3.92% to -2.19% | -3.06% |

These cell summaries are descriptive, not confidence intervals or a weighted
production score. Dense workloads improve in only 7/24 cells. The path control
has zero promotions yet its 100k warmed runtime varies from −16.00% to +9.49%
across query mixes: changes there cannot demonstrate a promotion-path speedup.
Runtime variation and possible build/code-layout effects limit causal claims.

The targeted cyclic-block 100k warmed cases improve by 11.15%, 3.98% and 3.30%
for 10%, 50% and 90% queries respectively. Their cut p95 falls by 4.54%, 6.42%
and 5.52%. Cogentco improves by 2.19% fresh and 3.92% warmed. These are measured
outcomes of this campaign, not a universal performance guarantee.

Keep the small redundant-work removal in the experimental backend, but do not
promote HDT to the default on this evidence. It does not fix the high promotion
count or establish a winner over the other engines. A next optimization should
target the measured forest update/promotion work, with the same preserved
reference matrix and new paired measurements. Confirm small runtime effects
with additional independent trials before making product performance claims.

## All scenario cells

Runtime is median replay wall time; cut p95 is the median of per-process p95s.
RSS deltas do not establish heap-allocation savings.

| Family / workload | Nodes | Query % | Regime | Before ms | After ms | Runtime Δ | Cut p95 Δ | RSS Δ |
|---|---:|---:|---|---:|---:|---:|---:|---:|
| cogentco / topology-zoo-outages-v1 | 197 | import | fresh | 0.539 | 0.527 | -2.19% | -7.89% | +0.00% |
| cogentco / topology-zoo-outages-v1 | 197 | import | warmed | 0.491 | 0.472 | -3.92% | -5.97% | +0.00% |
| dense / dense-bridge-churn-v1 | 128 | 10 | fresh | 0.966 | 0.947 | -1.88% | +4.03% | +0.33% |
| dense / dense-bridge-churn-v1 | 128 | 10 | warmed | 0.938 | 0.952 | +1.51% | +4.03% | -0.33% |
| dense / dense-bridge-churn-v1 | 128 | 50 | fresh | 0.775 | 0.794 | +2.52% | -7.30% | -0.11% |
| dense / dense-bridge-churn-v1 | 128 | 50 | warmed | 0.802 | 0.766 | -4.43% | -3.73% | -0.11% |
| dense / dense-bridge-churn-v1 | 128 | 90 | fresh | 0.597 | 0.615 | +3.04% | +0.08% | -0.43% |
| dense / dense-bridge-churn-v1 | 128 | 90 | warmed | 0.598 | 0.602 | +0.66% | +0.09% | -0.22% |
| dense / dense-bridge-churn-v1 | 512 | 10 | fresh | 9.122 | 9.211 | +0.98% | +3.25% | -0.40% |
| dense / dense-bridge-churn-v1 | 512 | 10 | warmed | 8.959 | 9.465 | +5.65% | +9.37% | -0.06% |
| dense / dense-bridge-churn-v1 | 512 | 50 | fresh | 8.962 | 9.162 | +2.23% | -0.07% | -0.23% |
| dense / dense-bridge-churn-v1 | 512 | 50 | warmed | 8.747 | 9.160 | +4.72% | -2.98% | +0.11% |
| dense / dense-bridge-churn-v1 | 512 | 90 | fresh | 8.684 | 9.015 | +3.81% | -32.64% | -0.17% |
| dense / dense-bridge-churn-v1 | 512 | 90 | warmed | 8.734 | 8.669 | -0.75% | -2.72% | -0.51% |
| dense / redundant-bridge-churn-v1 | 128 | 10 | fresh | 0.922 | 0.940 | +1.88% | +0.04% | -0.44% |
| dense / redundant-bridge-churn-v1 | 128 | 10 | warmed | 0.931 | 0.919 | -1.28% | -1.54% | +0.44% |
| dense / redundant-bridge-churn-v1 | 128 | 50 | fresh | 0.770 | 0.780 | +1.29% | +0.00% | +0.33% |
| dense / redundant-bridge-churn-v1 | 128 | 50 | warmed | 0.772 | 0.800 | +3.67% | +4.80% | +0.11% |
| dense / redundant-bridge-churn-v1 | 128 | 90 | fresh | 0.608 | 0.606 | -0.33% | -2.98% | +0.00% |
| dense / redundant-bridge-churn-v1 | 128 | 90 | warmed | 0.603 | 0.617 | +2.30% | +21.39% | +0.44% |
| dense / redundant-bridge-churn-v1 | 512 | 10 | fresh | 9.289 | 9.393 | +1.13% | +1.27% | -0.57% |
| dense / redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.964 | 8.772 | -2.15% | +1.18% | -0.23% |
| dense / redundant-bridge-churn-v1 | 512 | 50 | fresh | 9.188 | 9.082 | -1.16% | +1.24% | -0.28% |
| dense / redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.683 | 8.901 | +2.52% | +3.69% | -0.34% |
| dense / redundant-bridge-churn-v1 | 512 | 90 | fresh | 8.840 | 8.950 | +1.25% | +0.00% | -0.28% |
| dense / redundant-bridge-churn-v1 | 512 | 90 | warmed | 8.451 | 8.752 | +3.57% | -2.56% | -0.17% |
| repeats / sustained-churn-blocks-v1 | 10000 | 90 | fresh | 25.048 | 23.736 | -5.24% | -3.98% | -0.23% |
| repeats / sustained-churn-blocks-v1 | 10000 | 90 | warmed | 25.637 | 23.060 | -10.05% | -9.49% | -2.07% |
| repeats / sustained-churn-path-v1 | 10000 | 90 | fresh | 0.731 | 0.762 | +4.32% | +11.05% | +0.64% |
| repeats / sustained-churn-path-v1 | 10000 | 90 | warmed | 0.757 | 0.572 | -24.40% | -41.48% | +0.35% |
| sparse / sustained-churn-blocks-v1 | 1024 | 10 | fresh | 3.936 | 3.757 | -4.55% | +14.34% | +0.33% |
| sparse / sustained-churn-blocks-v1 | 1024 | 10 | warmed | 3.657 | 3.674 | +0.47% | -2.04% | +0.00% |
| sparse / sustained-churn-blocks-v1 | 1024 | 50 | fresh | 3.128 | 3.166 | +1.20% | -4.68% | +0.00% |
| sparse / sustained-churn-blocks-v1 | 1024 | 50 | warmed | 3.029 | 2.844 | -6.11% | -6.85% | +0.22% |
| sparse / sustained-churn-blocks-v1 | 1024 | 90 | fresh | 2.166 | 2.100 | -3.05% | -1.88% | -0.65% |
| sparse / sustained-churn-blocks-v1 | 1024 | 90 | warmed | 2.030 | 2.021 | -0.43% | -3.07% | +0.11% |
| sparse / sustained-churn-blocks-v1 | 10000 | 10 | fresh | 39.027 | 37.518 | -3.87% | -4.70% | -0.61% |
| sparse / sustained-churn-blocks-v1 | 10000 | 10 | warmed | 38.504 | 36.332 | -5.64% | -4.23% | -0.30% |
| sparse / sustained-churn-blocks-v1 | 10000 | 50 | fresh | 38.653 | 38.407 | -0.64% | -0.26% | -0.11% |
| sparse / sustained-churn-blocks-v1 | 10000 | 50 | warmed | 37.215 | 34.435 | -7.47% | -5.27% | -0.26% |
| sparse / sustained-churn-blocks-v1 | 10000 | 90 | fresh | 24.863 | 23.565 | -5.22% | -4.48% | -0.80% |
| sparse / sustained-churn-blocks-v1 | 10000 | 90 | warmed | 24.136 | 23.144 | -4.11% | -9.42% | -0.32% |
| sparse / sustained-churn-blocks-v1 | 100000 | 10 | fresh | 461.206 | 467.863 | +1.44% | +5.32% | -0.62% |
| sparse / sustained-churn-blocks-v1 | 100000 | 10 | warmed | 502.770 | 446.698 | -11.15% | -4.54% | -1.23% |
| sparse / sustained-churn-blocks-v1 | 100000 | 50 | fresh | 483.756 | 483.870 | +0.02% | +5.56% | -0.58% |
| sparse / sustained-churn-blocks-v1 | 100000 | 50 | warmed | 493.094 | 473.446 | -3.98% | -6.42% | -0.55% |
| sparse / sustained-churn-blocks-v1 | 100000 | 90 | fresh | 316.003 | 304.032 | -3.79% | -3.74% | -0.67% |
| sparse / sustained-churn-blocks-v1 | 100000 | 90 | warmed | 317.625 | 307.141 | -3.30% | -5.52% | -0.85% |
| sparse / sustained-churn-path-v1 | 1024 | 10 | fresh | 0.568 | 0.558 | -1.63% | -6.52% | +0.22% |
| sparse / sustained-churn-path-v1 | 1024 | 10 | warmed | 0.519 | 0.505 | -2.76% | -2.52% | -0.44% |
| sparse / sustained-churn-path-v1 | 1024 | 50 | fresh | 0.410 | 0.404 | -1.61% | -2.06% | -0.11% |
| sparse / sustained-churn-path-v1 | 1024 | 50 | warmed | 0.362 | 0.360 | -0.36% | +0.00% | +0.33% |
| sparse / sustained-churn-path-v1 | 1024 | 90 | fresh | 0.224 | 0.222 | -0.91% | +0.00% | +0.00% |
| sparse / sustained-churn-path-v1 | 1024 | 90 | warmed | 0.186 | 0.184 | -1.51% | +3.91% | +0.00% |
| sparse / sustained-churn-path-v1 | 10000 | 10 | fresh | 1.081 | 0.971 | -10.22% | -15.79% | -0.14% |
| sparse / sustained-churn-path-v1 | 10000 | 10 | warmed | 0.856 | 0.861 | +0.62% | -3.20% | +0.07% |
| sparse / sustained-churn-path-v1 | 10000 | 50 | fresh | 0.742 | 0.744 | +0.26% | -2.19% | -0.14% |
| sparse / sustained-churn-path-v1 | 10000 | 50 | warmed | 0.581 | 0.650 | +11.89% | +14.75% | +0.00% |
| sparse / sustained-churn-path-v1 | 10000 | 90 | fresh | 0.612 | 0.560 | -8.48% | -24.85% | +0.21% |
| sparse / sustained-churn-path-v1 | 10000 | 90 | warmed | 0.361 | 0.364 | +0.83% | +13.24% | +0.14% |
| sparse / sustained-churn-path-v1 | 100000 | 10 | fresh | 4.049 | 4.041 | -0.18% | -3.72% | +0.04% |
| sparse / sustained-churn-path-v1 | 100000 | 10 | warmed | 4.158 | 3.493 | -16.00% | -20.55% | -0.04% |
| sparse / sustained-churn-path-v1 | 100000 | 50 | fresh | 3.316 | 3.618 | +9.10% | +3.09% | +0.00% |
| sparse / sustained-churn-path-v1 | 100000 | 50 | warmed | 3.129 | 3.080 | -1.57% | +1.64% | -0.02% |
| sparse / sustained-churn-path-v1 | 100000 | 90 | fresh | 2.342 | 2.603 | +11.14% | +6.20% | +0.03% |
| sparse / sustained-churn-path-v1 | 100000 | 90 | warmed | 2.180 | 2.387 | +9.49% | +6.40% | +0.01% |

## Validation and reproduction

Formatting, Clippy for all targets with warnings denied, workspace tests/doctests,
and Rustdoc with warnings denied passed in both repositories. Four Python import
adapter tests also passed. The new core regression test exercises sparse global
indices whose local forest handles differ, including link, cut and mark removal.
A read-only review found no correctness issue; the uncaptured build environment
limitation above was identified during review.

`collect.py` documents the collection procedure and refuses to overwrite an
existing manifest. To repeat, use a new output directory, reconstruct the before
revision and after patch from the manifest, build/copy both executables and
write their snapshots at the collector's explicit temporary paths. Regenerate
Cogentco using the original campaign provenance. Capture build environment
settings in any future collection. The temporary paths are inputs, not portable
binary artifacts; binaries and large raw trace exports are not committed.
`audit.json` verifies recorded file hashes, exact fingerprints/counters and source
hashes. The original four campaign manifests and their artifacts were checked
without rewriting them. See the permanent
[before/after policy](../../docs/experiments/2026-10-04-before-after-policy.md).
