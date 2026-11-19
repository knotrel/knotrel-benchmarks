# v0.7.0 re-qualification: diagnostics summary

These are the diagnostics the maintainer ordered on 2026-11-19, against the
plan declared in [`DIAGNOSTICS-PLAN.md`](DIAGNOSTICS-PLAN.md). Departures
from that plan are listed in each diagnostic's README. The main ones:
- D1's F arm does not hold the same structures as L;
- D2's pre-sizing differs from the plan's wording;
- D3's code-site profile was not done as planned;
- D4 gives pair ranges instead of intervals, and (d) was built without a
  guiding profile;
- D5 added a "forced" variant.
- **No verdict changes.** Attempt a3-3's results stand as measured:
  REGRESSION, FAIL ×3, INCONCLUSIVE ×2, INVALID. No threshold changes and no
  exception is accepted.
- **The release stays pending.** No result is dispositioned here.

All runs were on the developer laptop, not gated. Each diagnostic was one run
of the declared size, except that D4 ran (b) twice and D5 added three forced
runs. Ranges are pair min–max, not confidence intervals.

## Findings

| Item | Diagnostic | Finding | Open questions for the maintainer |
|---|---|---|---|
| 1. B4 `import-high` REGRESSION | [D1](D1-import-high/README.md) | (1) **A plain server given the full registered volume** (19,991 edges, against the reference's 2,139 effective) costs 4.42× the reference. That is 82–93% of the lifecycle import's excess, depending on the method, so volume is the main driver. (2) **The lifecycle import costs +13.7%** (pair range 7.8–21.5%) over that plain import. The two servers build different structures (the lifecycle engine holds only the effective edges), so this is not a clean flag cost. | Is holding the full registered topology part of the product contract? Should the lifecycle import path (wire format, catalog and flag handling) be investigated further? |
| 2. C3 heap growth FAIL ×3 | [D2](D2-c3-heap/README.md) | (1) **The peak is in the first compaction interval.** Over 300 cycles (15 compactions), no heap above that peak: steady-state maximum about 31.1 MiB sparse/hub, 28.9 MiB ring; slope ≤ 0.21% per 150 cycles. (2) **Declared strict-maximum criterion:** sparse is bounded; ring and hub exceed it by about 9 KB (0.03%), and ring's per-interval maxima drift about 0.3%. Behaviour beyond 300 cycles is not established. (3) **Pre-sizing at construction** (catalog, ID map, adjacency headers at 2n) makes C3 pass and lowers the peak by 1.29–1.42 MiB, but B5 rises to 3.40×, above its 3× budget. Pre-sizing at compaction only does not help C3. | Which of: accept the C3 trade-off, partial pre-sizing, or a longer-window rule for a future release? |
| 3. B4 `ops` sparse 100k INCONCLUSIVE | [D3](D3-ops-100k/README.md) | (1) **The apply phase** (lifecycle operations in `knotrel-core`) is +74% and exceeds the whole window difference. Other phases are lower for the lifecycle arm; admission, lock and dispatch add nothing measurable. The arms apply different operation sets (9,464 against 13,057). (2) The planned per-arm code-site profile was not achieved: too few window samples. | Is optimization of the core lifecycle paths wanted? If so, a window-only profile comes first |
| 4. B4 `metrics-ops` INCONCLUSIVE | [D4](D4-metrics-ops/README.md) | (1) **Lock timing** is about 1% of the metrics overhead. (2) **Per-batch counting** gives no measurable gain. (3) **Outside the handler** (router, parse, middleware, probe loop): 15–40% of the overhead; the metrics share there is not isolated. (4) **No variant that keeps the same observability** beats run-to-run noise, so whether 6% can be met without reducing observability is not established. The medians (4.2–5.2%) come from an instrumented build on an ungated host and do not bear on the a3-3 verdict. | A declared separate re-measurement with more pairs or a quieter host? Look at the request middleware? |
| 6. M_desc INVALID row (6/6 HTTP 412) | [D5](D5-412/README.md) | **Expected precondition enforcement by the server, caused by a probe error; no product defect found in this diagnostic.** (1) The unmodified probe did not reproduce the failure in 9 runs. A forced copy that keeps the stale token, as the a3-3 record indicates, reproduced it: every 412 answered a token different from the live ETag. (2) With a fresh token, imports succeed at 64 clients (54/54). (3) Under saturation `/v1/stats` was refused in about 87% of sampled requests. That is not the odds for the refresh at the start of a configuration. | Change the probe's refresh logic for future collections (tooling)? Should `/v1/stats` bypass admission (product question)? |

Items 5 (C4, a disclosure category), 7 (M_reg p99 +6.41%), 8 (A
`compact-workspace` near its tolerance), 9 (interference marking) and 10
(cross-check deviation) had no diagnostic ordered. They await the
maintainer's decision.
