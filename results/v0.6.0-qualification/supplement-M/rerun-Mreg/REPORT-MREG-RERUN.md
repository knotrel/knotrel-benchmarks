# v0.6.0 M_reg rerun: report

**SUPPLEMENTARY.** This rerun does not replace, re-classify or extend any
frozen v0.6.0 verdict and closes no other non-PASS item. Using its verdicts as
coverage evidence for comparison §8 item 9 is the maintainer's decision.

Protocol: [`PROTOCOL-MREG-RERUN.md`](PROTOCOL-MREG-RERUN.md) (§7 records both
attempts).
Authorization: maintainer, 2026-11-17: "IDEs closed, go", then "Stopped,
restart" after the ShipIt loop was removed.

## 1. Attempts

| Attempt | Freeze | Outcome |
|---|---|---|
| 1 | `50be4d61` | Stopped by the quiet-period gate. The VS Code updater `ShipIt` was relaunched by launchd every 40–90 s (5 samples). **No measurement.** Record: `evidence/v0.6.0-mreg-rerun-48bc82f/` |
| 2 | `ea26dd12` | Completed. Record: `evidence/v0.6.0-mreg-rerun-48bc82f-attempt2/` |

Between the two attempts, freeze `ea26dd12` changed only two things: the run
script's optional attempt number (new output directory) and the protocol's
attempt record. Matrix and scripts are byte-identical (checked in
`FREEZE-MREG-RERUN.json`).

Before attempt 2:
- The operator removed the launchd job (`launchctl remove
  com.microsoft.VSCode.ShipIt`).
- `launchctl list` no longer shows it.
- A 100 s pre-check with the monitor recorded no matching process.

## 2. Identities and conditions (attempt 2)

| Item | Value |
|---|---|
| Servers | cand `d4adec2e…` (48bc82f), ref `e3d12df8…` (v0.5.0), the frozen campaign's builds, verified before the run (`logs/binaries-verify.json`) |
| Probe | revision 2, `e7d0b4b6…`, the M supplement's build, verified and not rebuilt |
| Quiet period | 08:12:16–08:17:16Z: 1,170 samples at 0.2 s, **0 matching processes** |
| Measurement | 08:17:17–08:21:22Z, 56 children, all exit 0, AC power on all, no thermal or performance warning |
| Run monitor | 1,054 samples, **0 matching processes**, no gap above 1.3 s in the per-second top log |
| Git state | **0 changes** across 41 clones under `/Users/rt/workspace/knotrel`, compared before the quiet period and after the run |
| Output checksums | All entries of `logs/outputs-sha256.txt` verify except `logs/steps.txt`, because the run script appends its final `RUN complete` line after hashing (a script-ordering defect). With that last line removed, `steps.txt` matches its recorded hash (`b6e384c7…`). |

## 3. Classification

| Level | Status |
|---|---|
| 1. Functional correctness of the probe | Shown, with the M supplement's limits: every analyzed observation has 0 errors, 0 per-item errors and 0 no-ops, and feeder catch-up has 0 failures |
| 2. Validity of the analyzer inputs | **Met**: 48 analyzed observations, all status 200 only, arm order 6/6 in each cell |
| 3. Conformance to the declared, verifiable conformance rules (protocol §4–§5) | **Met**: prelaunch gate, quiet period, per-child gates, run monitor and Git-state comparison are all clean |

**Residual activity, disclosed** (not covered by the activity pattern; impact
not quantified):
- **Ordinary desktop processes were running**, as in every earlier campaign.
  From the per-second top log, macOS `ps` %CPU, which is a decaying average:
  - WindowServer, about 36% throughout;
  - Google Chrome: 8 samples above 20% between 08:18:23 and 08:20:46, peak
    226%;
  - single samples of Spotlight metadata (80%), Safari SafeBrowsing (68%) and
    the Claude app renderer (138% at 08:19:55);
  - WhatsApp and Docker's backend at low levels.
- **The operator ran one `launchctl list | grep` command during the run.**
  Its exact time was not recorded.
- The protocol excluded builds, tests, editors, agents and Git activity, and
  those are verified absent. It did not require quitting browsers or other
  desktop applications.
- The randomized, balanced pair order spreads such activity over both arms,
  but this does not prove it had no effect.

## 4. Results (12 analyzed pairs per cell; v0.6.0 against v0.5.0)

Paired change: *exp(median ln(v0.6.0ᵢ / v0.5.0ᵢ)) − 1*, with interval
[r(3), r(10)]. Arm medians are given for orientation; the paired change is
a different statistic (see the M supplement report §3). The verdict uses the
frozen analyzer:
- throughput on ln(v0.5.0/v0.6.0), tolerance 10%;
- p99 on ln(v0.6.0/v0.5.0), tolerance 25%.

| Cell (100k, 16 clients) | Throughput, arm medians v0.5.0 → v0.6.0 | Throughput change [interval] | p99, arm medians v0.5.0 → v0.6.0 | p99 change [interval] | Verdict |
|---|---|---|---|---|---|
| standalone, lifecycle off, `mixed50`, batch 64 | 50.67 → 50.33 req/s | −0.33% [−0.66, +0.00] | 352.6 → 347.7 ms | −0.43% [−2.42, +0.90] | **PASS** |
| source-managed, lifecycle on, `read100`, batch 8, feeder catch-up | 206.0 → 201.5 req/s | **−1.63% [−3.79, −0.82]** | 89.8 → 92.7 ms | **+3.98% [+0.75, +6.20]** | **PASS** |

How to read them:
- **Feeder catch-up cell.** The whole intervals are on the "worse" side.
  v0.6.0 completes about 1.6% fewer query requests and has an about 4%
  longer client p99 than v0.5.0 in this cell.
  - These are **confirmed small degradations, within tolerance** (upper
    bounds +3.94% on the analyzer's throughput ratio against 10%, and
    +6.20% on p99 against 25%).
  - They are not improvements.
  - Feeder catch-up was accepted with 0 failures in every observation:
    3,520–3,648 events per observation on v0.6.0 and 3,648–3,840 on v0.5.0.
- **`mixed50` cell.** No difference is shown. The throughput interval ends
  at 0.00%: requests per window are integers, so one request is 0.66% at
  about 50 req/s.
- **Consistency with the M supplement's non-conforming run** (same cells):
  - feeder catch-up: throughput −1.00% [−4.04, +1.16], p99 +3.86%;
  - `mixed50`: −0.33% and +1.98%.
  - The directions agree; the rerun is the conforming measurement.

## 5. Recommendation

Conformance with the declared, verifiable rules is demonstrated, and the
residual desktop activity is disclosed above. **Proposed:** that the
maintainer accept these two supplementary M_reg verdicts (PASS, PASS) as the
coverage evidence for comparison §8 item 9 (contention coverage), together
with the disclosed residual activity and the confirmed small degradation
within tolerance in the feeder catch-up cell.

The proposal is limited to those two cells:
- The frozen verdicts stay as they are: `mixed50` PASS †, and the events
  cell invalid for its purpose.
- The M supplement stays evidence with limitations. That includes its 60
  descriptive configurations, whose run did not conform.
- No other non-PASS item is affected.
