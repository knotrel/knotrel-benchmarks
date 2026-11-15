# Re-check of the Marginal Hot-Path Regression

Hand-written narrative. Numbers come from the generated [REPORT.md](REPORT.md)
and [analysis/summary.json](analysis/summary.json), regenerated from [run/](run/)
by [analyze.py](analyze.py).

## Why

The [hot-path audit campaign](../hot-path-audit-20261114/README.md) reported
one confirmed regression by its rule: dynamic `compact-bfs` sustained-churn
`connected_total_ns`, +2.14% [+0.64%, +4.18%] against an A/A bound of ±2.06%
(n = 12), on a query path the change set does not modify. Roadmap Feature
0.4.1 requires re-measuring that cell before deciding which optimizations
v0.4.0 includes.

## Pre-specified design (fixed before running, in the collector's docstring)

- **Binaries:** exactly the `knotrel-benchmarks` binaries of the audit
  campaign (`base`, `cand`, byte-identical `aa`), verified against the sha256
  values recorded in its `run/builds/binaries.json` before any observation.
  No rebuild, so the re-check measures the same machine code.
- **Command:** the audit collector's own `command_for("dynamic", …)` for
  `compact-bfs` / `sustained-churn-blocks-v1` / 10,000 nodes / 200 rounds.
- **Schedule:** 24 counterbalanced rounds (every arm order four times), one
  session, 60 s quiet, 5 s between rounds, host checks enforced. No extension.
- **Verdict rule:** the audit's (`analyze.py` of the audit campaign is
  imported, not copied): confirmed only if the 95% bootstrap interval excludes
  zero and the median exceeds the A/A bound. Primary metric
  `connected_total_ns`; `workload_wall_ns`, `link_total_ns` and
  `cut_total_ns` are secondary.

## Result

| Metric | Role | Paired change [95% CI] | A/A bound | Verdict |
| --- | --- | ---: | ---: | --- |
| `connected_total_ns` | primary | +0.83% [+0.10%, +1.78%] | ±2.14% | inconclusive |
| `workload_wall_ns` | secondary | +0.16% [−0.46%, +1.33%] | ±1.63% | inconclusive |
| `link_total_ns` | secondary | −11.36% [−22.34%, −6.16%] | ±8.01% | confirmed improvement |
| `cut_total_ns` | secondary | −6.78% [−18.34%, −1.13%] | ±10.91% | inconclusive |

Trace fingerprints are identical across all 72 runs.

**Interpretation.** The regression **does not reproduce**: with twice the
rounds, the median is +0.83%, less than half of the A/A bound, and whole-workload
time is unchanged within noise. The interval still lies slightly above zero,
so a small slowdown below the noise floor of this host cannot be excluded;
it is not a confirmed regression under the audit's rule. The original verdict
is best explained as one of the expected chance verdicts among the audit's 42
tests (its margin over the bound was 0.08 percentage points). The secondary
`link_total_ns` improvement points the same way as the audit's inconclusive
−9.62% for this cell; no mechanism was attributed, and as a secondary metric
it is reported, not claimed.

## Identity

| Item | Value |
| --- | --- |
| Source campaign | `results/hot-path-audit-20261114` (its `manifest.json` sha256 is recorded in [run/provenance.json](run/provenance.json)) |
| `base` and `aa` binary | `8fa8ed4a52059705823760f5e7498719a0cafcbd4bd169e3df205c913b00ce20` |
| `cand` binary | `6c2a00804e2dc0b6f124069ceb8559640d4862c7a65a9127d1982359b1b7f849` |
| Host | Apple M3, macOS 26.5.2, AC power |
| Collected | 2026-11-15, 10:03–10:06 UTC, 72 observations |

## Reproduction

The binaries live in the ignored `target-hot-path-audit/` directory created by
the audit collector; rebuild them by rerunning that collector if they are gone.

```sh
python3 scripts/run_hot_path_recheck.py <new-output-directory>
python3 results/hot-path-recheck-20261115/analyze.py --check
```
