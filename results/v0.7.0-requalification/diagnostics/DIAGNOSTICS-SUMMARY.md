# v0.7.0 re-qualification: diagnostics summary

These are the diagnostics the maintainer ordered on 2026-11-19, run as
declared in [`DIAGNOSTICS-PLAN.md`](DIAGNOSTICS-PLAN.md). Every departure
from the plan is stated in the diagnostic's README.
- **No verdict changes.** Attempt a3-3's results stand as measured:
  REGRESSION, FAIL ×3, INCONCLUSIVE ×2, INVALID. No threshold changes and no
  exception is accepted.
- **The release stays pending.** No result is dispositioned here.

All runs were on the developer laptop, not gated. Each diagnostic was one run
of the declared size.

## Findings

| Item | Diagnostic | Finding | Open questions for the maintainer |
|---|---|---|---|
| 1. B4 `import-high` REGRESSION | [D1](D1-import-high/README.md) | (1) **About 86% of the overhead is volume**: the full registered topology (19,991 edges) against the reference's effective graph (2,139 edges). A plain server given the same volume costs 4.42× the reference. (2) **At equal volume, flags and lifecycle cost +13.7%** (7.8–21.5%): 32% more body bytes and a longer `prepare` phase. | Is holding the full topology part of the product contract (then the volume cost follows from it)? Should the +13.7% be investigated further (wire format, flag handling)? |
| 2. C3 heap growth FAIL ×3 | [D2](D2-c3-heap/README.md) | (1) **The peak is in the first compaction interval.** Over 300 cycles, 15 compactions, the heap stays in a band below that peak: steady-state maximum about 31.1 MiB sparse/hub, 28.9 MiB ring; slope ≤ 0.21% per 150 cycles. (2) **Declared strict-maximum criterion:** sparse is bounded; ring and hub exceed it by about 9 KB (0.03%). (3) **Pre-sizing at construction** makes C3 pass and lowers the peak by about 1.4 MiB, but B5 rises to 3.40×, above its 3× budget. Pre-sizing at compaction only does not help C3. | Accept the C3 trade-off, pursue partial pre-sizing, or define a longer-window rule for a future release? |
| 3. B4 `ops` sparse 100k INCONCLUSIVE | [D3](D3-ops-100k/README.md) | (1) **All of the overhead is in applying lifecycle operations** in `knotrel-core` (+74% applying time). Admission, lock and dispatch add nothing; parse and serialize are cheaper on the lifecycle side. (2) **Against an application doing the same bookkeeping** (B1 core), the operations cost +1.5%. B4's reference plans untimed. (3) No ranked code-site profile: too few samples. | Optimize core lifecycle paths (a core change), or accept? A window-only profile if optimization is wanted |
| 4. B4 `metrics-ops` INCONCLUSIVE | [D4](D4-metrics-ops/README.md) | (1) **The median overhead is 4.2–5.2% in every run** (below 6%); a3-3's median was 5.65%. The non-PASS is interval width. (2) **Lock timing is about 1%.** (3) **Per-batch counting gives no measurable gain.** (4) About 30–40% of the overhead sits in request-level HTTP metrics. No variant that keeps the same observability beats the noise. | A declared re-measurement with more pairs or a quieter host to narrow the interval (separate evidence)? Look at the request middleware? |
| 6. M_desc INVALID row (6/6 HTTP 412) | [D5](D5-412/README.md) | **Expected precondition enforcement by the server, caused by a probe error. No product defect found.** (1) The probe's single `/v1/stats` refresh lost to admission at 64 clients (stats got 503 in about 87% of attempts under that load); it then kept a token made stale by the earlier events configuration. (2) Every 412 answered a token different from the live ETag. (3) With a fresh token, imports succeed at 64 clients (54/54). | Fix the probe's refresh (tooling) for future collections? Should `/v1/stats` bypass admission (product question)? |

Items 5 (C4, a disclosure category), 7 (M_reg p99 +6.41%), 8 (A
`compact-workspace` near its tolerance), 9 (interference marking) and 10
(cross-check deviation) had no diagnostic ordered. They await the
maintainer's decision.
