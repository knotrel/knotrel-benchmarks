# v0.6.0 M_reg rerun: protocol (declared, not frozen, not started)

**Status:**
- Prepared after the M supplement's protocol non-conformity
  (`../REPORT-M-SUPPLEMENT.md` §7).
- It needs maintainer approval before it is frozen (`FREEZE-MREG-RERUN.json`)
  and run.
- **Supplementary.** It does not replace, re-classify or extend any frozen
  v0.6.0 result. Its verdicts never close another non-PASS item.

## 1. Why, and why only these two cells

- **Non-conformity.** The M supplement ran while an automated process
  executed `git fetch`.
  - Proven inside measured M_desc children.
  - Undetermined for M_reg.
  - This breaks the protocol rule "Nothing else runs during measurement".
- **Scope.**
  - The only results of the supplement that could be proposed for acceptance
    are its two M_reg comparisons, so only those are rerun.
  - The 60 descriptive M_desc configurations are not repeated. They stay as
    evidence with limitations.

## 2. What stays identical

- **Cells.** `Mreg-standalone-off-mixed50-b64-c16-100k-none` and
  `Mreg-source-managed-on-read100-b8-c16-100k-events`, copied from
  `MATRIX-M-SUPPLEMENT.json` (a test checks it).
- **Statistics:**
  - 2 warmup pairs and 12 analyzed pairs;
  - a fresh server per observation and balanced arm order;
  - paired log ratios with the order-statistic interval r(3), r(10);
  - tolerances: throughput 10% (ratio v0.5.0/v0.6.0), client p99 25%;
  - the frozen `analyze_mreg` and the supplement's validity rule, unchanged.
- **Binaries**, read in place and checked against the sha256 in
  `MATRIX-MREG-RERUN.json` before any child:
  - the frozen campaign's servers: cand `d4adec2e…`, ref `e3d12df8…`;
  - the M supplement's probe revision 2 build, `e7d0b4b6…`, which is not
    rebuilt, so no `cargo` runs.

The only change is a new pair-order seed, 60602, declared now. Reusing 60601
would replay the same order; the seed is declared before any result.

## 3. Removing automated activity (operator, before freezing)

Observed source: `Antigravity IDE Helper (Plugin)` runs periodic `git fetch`
in every repository under `/Users/rt/workspace/knotrel`
(`evidence/v0.6.0-diagnostics/m-supplement-host-activity/`). Visual Studio
Code is also running; no fetch by it was observed.

1. **Quit Antigravity IDE and Visual Studio Code.**
   - The alternative is to disable their Git auto-fetch and remove
     `evidence/` and the repositories from their workspaces.
   - Quitting is the verifiable option, because the gate checks it by process
     name.
   - This is the operator's action: no tool changes IDE settings.
2. **Start no other build, test, editor or agent work on the host until the
   run ends.**
   - The Claude desktop app stays open and idle, as accepted host baseline,
     and is disclosed.
   - Its process names do not match the activity pattern. Any `git` process
     it would start does match, and would be caught.
3. **Historical evidence is not modified.**
   - The run only reads historical evidence: binaries and Git state.
   - It writes only its own new directory,
     `evidence/v0.6.0-mreg-rerun-48bc82f/`, and refuses to reuse it.

## 4. Verifying absence

All checks are automated in `run_mreg_rerun.sh`. Their logs are kept in the
rerun's `logs/`.

- **Prelaunch gate.** `host_activity_monitor.py --check` must find no
  process matching `git`, `git-*`, `cargo`, `rustc`, `Antigravity`,
  `Visual Studio Code` or `Code Helper`; otherwise the run stops. AC power
  is required, as before.
- **Quiet period.** 300 s of monitoring before measuring. The monitor samples
  the process table every 0.2 s and logs the five busiest non-measured
  processes every second. Any matching sample stops the run before
  measurement.
- **Per child.** The activity gate runs before every child; a match stops
  the run, and the stop is recorded.
- **During measurement.** Continuous monitoring. A child whose interval
  [start, start + duration + 1 s] overlaps a matching sample is
  non-conforming.
- **Git state.** A read-only snapshot of every clone under the workspace is
  taken before the quiet period and after the run: `FETCH_HEAD` mtime and
  remote-tracking reflog lengths. Any change makes the run non-conforming.
- **Limit.** A process that lives less than 0.2 s between samples can be
  missed. The Git-state comparison covers fetches that miss the monitor.

## 5. Outcome rules (declared)

- **Per cell:**
  - **NONCONFORMING (no verdict):** a non-conforming analyzed observation, or
    any run-level conformance failure (quiet period, Git state);
  - **INVALID:** an invalid analyzed observation (the supplement's validity
    rule);
  - otherwise, the frozen classification: PASS, INCONCLUSIVE or REGRESSION.
- **Reporting.** The outcome is reported whatever it is.
- **No further rerun.** These cells are not rerun again for v0.6.0 without a
  new maintainer decision.
- **Stops.** A stop at a gate, before or during measurement, is reported. It
  can be restarted only after the cause is removed, into a new directory,
  and the stop record is kept.
- **Use of results.** If the cells are conforming and valid, their
  supplementary verdicts may be proposed to the maintainer for acceptance as
  the coverage evidence for comparison §8 item 9. Nothing else changes.

## 6. Budget

About 10 minutes (5 quiet and 5 measuring); cap 20.
