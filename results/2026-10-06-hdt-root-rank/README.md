# HDT single-pass root/rank experiment — 2026-10-06

`reroot` previously walked parent links once to find the tour root and again to compute the token rank. The candidate returns both from one read-only walk. It preserves split/concat and the exact tour sequence, and does not include the earlier rank-zero shortcut. [candidate.patch](candidate.patch) and the full before/after forest files are retained in this checkout.

38 / 38 cells complete; 0 / 304 timed processes failed. Each cell has four sequential before/after pairs, two in each execution order. Pairs were shuffled with seed42. Fresh and warmed runs remain separate; hardware caches were not flushed. The warmed run replays a fresh graph after one untimed warmup.

## Runtime results

| Family | Complete cells | Faster cells | Median cell change | Cell change range |
|---|---:|---:|---:|---:|
| sparse | 24 | 19 | -1.24% | -12.68% to +13.53% |
| dense | 12 | 3 | +0.26% | -1.84% to +6.00% |
| cogentco | 2 | 1 | +1.00% | -1.07% to +3.06% |

Negative change means lower runtime: `100*(after/before-1)`. These are per-cell median workload wall times, excluding setup but including harness checking and sampling. The median of cell changes is descriptive, not an aggregate throughput gain. Four pairs do not establish a statistical confidence interval.

| Workload | Vertices | Query mix | Regime | Before ms | After ms | Change | Faster pairs / 4 | Setup change | RSS change |
|---|---:|---:|---|---:|---:|---:|---:|---:|---:|
| topology-zoo-outages-v1 | 197 | None | fresh | 0.500 | 0.495 | -1.07% | 3 | -0.52% | +0.00% |
| topology-zoo-outages-v1 | 197 | None | warmed | 0.434 | 0.447 | +3.06% | 1 | +2.02% | +0.00% |
| dense-bridge-churn-v1 | 512 | 10 | fresh | 8.856 | 8.999 | +1.62% | 1 | +1.19% | +0.29% |
| dense-bridge-churn-v1 | 512 | 10 | warmed | 8.721 | 8.722 | +0.01% | 2 | -1.43% | +0.23% |
| dense-bridge-churn-v1 | 512 | 50 | fresh | 8.652 | 8.783 | +1.51% | 1 | +1.37% | -0.06% |
| dense-bridge-churn-v1 | 512 | 50 | warmed | 8.375 | 8.329 | -0.55% | 3 | +0.75% | +0.28% |
| dense-bridge-churn-v1 | 512 | 90 | fresh | 8.632 | 8.638 | +0.07% | 1 | -0.49% | +0.23% |
| dense-bridge-churn-v1 | 512 | 90 | warmed | 8.442 | 8.287 | -1.84% | 2 | +1.62% | -0.11% |
| redundant-bridge-churn-v1 | 512 | 10 | fresh | 8.780 | 8.803 | +0.26% | 3 | +0.29% | +0.23% |
| redundant-bridge-churn-v1 | 512 | 10 | warmed | 8.507 | 9.017 | +6.00% | 1 | +1.92% | +0.11% |
| redundant-bridge-churn-v1 | 512 | 50 | fresh | 8.716 | 8.739 | +0.26% | 3 | -0.16% | -0.17% |
| redundant-bridge-churn-v1 | 512 | 50 | warmed | 8.280 | 8.476 | +2.36% | 0 | +0.59% | +0.28% |
| redundant-bridge-churn-v1 | 512 | 90 | fresh | 8.484 | 8.563 | +0.94% | 2 | +0.79% | +0.06% |
| redundant-bridge-churn-v1 | 512 | 90 | warmed | 8.190 | 8.134 | -0.68% | 4 | +0.37% | +0.00% |
| sustained-churn-blocks-v1 | 100000 | 10 | fresh | 318.432 | 314.579 | -1.21% | 3 | -2.82% | -0.51% |
| sustained-churn-blocks-v1 | 100000 | 10 | warmed | 307.709 | 309.590 | +0.61% | 1 | -3.83% | +0.12% |
| sustained-churn-blocks-v1 | 100000 | 50 | fresh | 330.761 | 326.069 | -1.42% | 3 | -1.99% | -0.28% |
| sustained-churn-blocks-v1 | 100000 | 50 | warmed | 321.826 | 319.580 | -0.70% | 4 | -5.40% | -0.00% |
| sustained-churn-blocks-v1 | 100000 | 90 | fresh | 212.129 | 209.853 | -1.07% | 4 | -2.83% | +0.74% |
| sustained-churn-blocks-v1 | 100000 | 90 | warmed | 217.877 | 211.196 | -3.07% | 4 | -4.54% | -0.75% |
| sustained-churn-blocks-v1 | 1000000 | 10 | fresh | 4997.673 | 4794.958 | -4.06% | 2 | -2.78% | -3.71% |
| sustained-churn-blocks-v1 | 1000000 | 10 | warmed | 4683.869 | 4624.100 | -1.28% | 2 | -3.00% | +4.72% |
| sustained-churn-blocks-v1 | 1000000 | 50 | fresh | 4627.286 | 4623.320 | -0.09% | 3 | -1.43% | +4.24% |
| sustained-churn-blocks-v1 | 1000000 | 50 | warmed | 4549.706 | 4501.515 | -1.06% | 3 | -2.76% | +8.37% |
| sustained-churn-blocks-v1 | 1000000 | 90 | fresh | 3372.549 | 3305.567 | -1.99% | 3 | -3.70% | -4.93% |
| sustained-churn-blocks-v1 | 1000000 | 90 | warmed | 3366.203 | 3249.826 | -3.46% | 3 | -3.62% | -3.20% |
| sustained-churn-path-v1 | 100000 | 10 | fresh | 2.866 | 3.122 | +8.93% | 0 | -2.43% | +0.01% |
| sustained-churn-path-v1 | 100000 | 10 | warmed | 2.855 | 2.832 | -0.81% | 3 | -4.62% | -0.01% |
| sustained-churn-path-v1 | 100000 | 50 | fresh | 2.816 | 2.656 | -5.69% | 3 | -1.90% | -0.04% |
| sustained-churn-path-v1 | 100000 | 50 | warmed | 2.658 | 2.666 | +0.27% | 2 | -2.98% | +0.00% |
| sustained-churn-path-v1 | 100000 | 90 | fresh | 2.150 | 2.103 | -2.21% | 4 | -2.39% | -0.01% |
| sustained-churn-path-v1 | 100000 | 90 | warmed | 2.131 | 2.113 | -0.83% | 3 | -3.17% | +0.00% |
| sustained-churn-path-v1 | 1000000 | 10 | fresh | 7.080 | 6.183 | -12.68% | 4 | -1.96% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 10 | warmed | 6.797 | 6.984 | +2.74% | 2 | -6.91% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 50 | fresh | 6.741 | 7.654 | +13.53% | 2 | -2.89% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 50 | warmed | 5.162 | 4.937 | -4.36% | 1 | +0.03% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 90 | fresh | 4.010 | 3.671 | -8.45% | 3 | -1.98% | -0.00% |
| sustained-churn-path-v1 | 1000000 | 90 | warmed | 4.737 | 4.596 | -2.99% | 2 | -2.60% | +0.00% |

## Correctness and structural evidence

The isolated candidate passed complete core tests/doctests and an additional lookup test that enumerates the tour in order independently, checking every live vertex/arc token after singleton registration, links, cuts, relinks and mark updates. The before source fails that new test to compile because the fused helper does not exist; the after source passes. This is an API-availability red check, not an observed correctness failure in the original implementation. See candidate-test.rs.txt and test-results.json.

Structural probes on preserved 100k/1M block traces with 90% queries run separately from timing, twice per variant per trace. [structural-comparison.json](structural-comparison.json) checks that promotion counts by level, forest restructuring calls and endpoint materialization are unchanged, while comparing parent steps. These counters cannot be interpreted as runtime shares.

## Reproduction and preservation

Run build.py, test.py and collect.py in a fresh result destination, then analyze.py and report.py. Probe scripts are in the sibling before-probe and after-probe directories; run them after timings, then structural-comparison.py. Collectors refuse to overwrite completed results. Both temporary builds copy toolchain pins and use identical Rust/Cargo inputs except the candidate forest. Source-isolation-audit.json checks these inputs and the compiler. Manifests retain commands, hashes, raw outputs, failures and whole-process RSS, which is not engine-only heap.

Analysis verifies fingerprints, answer counts, mutation counts and paired HDT counters. Operation percentiles, setup, RSS and paired directions are preserved in [comparison.json](comparison.json); percentile summaries are not pooled samples. No failed process is silently omitted from the report.

The [candidate inventory](../../docs/experiments/2026-10-06-hdt-candidates.md) preserves the previous rank-zero patch separately with its SHA-256. The [current five-engine ranking](../2026-10-06-engine-ranking/README.md) remains the historical timing reference; no inter-day performance claim is inferred from it. See [decision.md](decision.md) for the integration decision and remaining limitations.
