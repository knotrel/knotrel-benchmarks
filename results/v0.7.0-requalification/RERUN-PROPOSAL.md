# v0.7.0 conforming re-qualification — proposal (declared, not frozen, not started)

**Status:**
- This is a proposal for the maintainer.
- Nothing here is frozen, built or measured.
- It needs approval before its `MATRIX.json`, `PROTOCOL.md` and `FREEZE.json`
  are written and frozen. No measurement starts before the freeze.
- It does not change, re-classify or replace any data or verdict of the first
  campaign (`../v0.7.0-qualification/`, evidence
  `evidence/v0.7.0-qualification-e75ff6a/`). That campaign stays recorded
  unchanged, as a non-conforming collection.

## 1. Why the whole campaign is repeated

### 1.1 The frozen rule and its granularity

The rules of the first campaign that concern concurrent activity, quoted from
the frozen files (tooling `82123ae3`, freeze `4c03cf7b`):

| Source | Rule | Stated consequence |
|---|---|---|
| `run_final_chain.sh`, line 4 | "The operator runs nothing else until it completes." | **None stated.** The rule's scope is the whole chain ("until it completes") |
| `MATRIX.json` `host_conditions.activity` | No Antigravity IDE, Visual Studio Code or `git` process (`host_activity_monitor.py --check`) "before every child"; the continuous monitor samples the whole campaign | Only the gate's own: a match stops the run. Nothing is stated for what the monitor records |
| `FREEZE.json` `known_concurrent_activity` | The other agent session "must be idle during the campaign" | None stated |
| `MATRIX.json` `host_conditions.power` / `.thermal` | AC power / no thermal warning, before every cell | Battery: "invalidates the run"; thermal warning: "invalidates the cell" |
| `MATRIX.json` `invalidation`, `PROTOCOL.md` §4 (v0.6.0 §4) | Code change, tooling change, failed child; "no rerun until favorable, no selected seeds or layouts, no outlier exclusion" | Per experiment; invalid runs kept |

- **Granularity.** The violated rule is the operator rule. The frozen protocol
  attaches no observation-, pair-, cell- or session-level consequence to it,
  and its scope is the chain as a whole.
- **No finer rule after the fact.** Inventing one now would be a retroactive
  rule. Per-observation exclusion, for example, would be both retroactive and
  more permissive. It would also contradict "no outlier exclusion".
- **The only granularity consistent with the frozen text is the campaign.**
  The first campaign is **non-conforming as a whole**. None of its results can
  be proposed for acceptance.
- **Precedent.** The v0.6.0 M supplement (REPORT-M-SUPPLEMENT §7) kept its
  non-conforming results as evidence with limitations and proposed none of
  them for acceptance.
  - Its rerun covered only the results that could have been proposed for
    acceptance. Here that is every experiment, because every experiment
    produces verdicts or speedup statements.

### 1.2 What the monitor shows for every cell

[`../v0.7.0-qualification/conformance/CONFORMANCE-CROSSCHECK.md`](../v0.7.0-qualification/conformance/CONFORMANCE-CROSSCHECK.md)
crosses every measured interval with `logs/activity-monitor.jsonl`. It covers
every cell, including PASS cells and the cells used for speedup statements.
The script is `scripts/analyze_v070_conformance.py` (read-only).

**Coverage of the monitor:**
- The monitor was alive from 19:22:21Z to 20:22:27Z, covering every measured
  interval; the largest gap between samples was 1.33 s.
- The gate pattern matched 0 times.
- **Limit:** it recorded only the five busiest processes per second, so
  activity outside the top five is invisible.

**User applications were present throughout:**

| Application | First seen | Last seen |
|---|---|---|
| Google Chrome | 19:22:36Z | 20:22:26Z |
| WhatsApp | 19:22:22Z | 20:20:20Z |
| Docker Desktop | 19:23:19Z | 20:22:23Z |
| Terminal | 19:22:25Z | 20:22:22Z |
| Claude desktop | 19:22:21Z | 20:20:20Z |
| a second Claude Code CLI process | 19:22:21Z | 20:21:33Z |

Also, between 20:17:13Z and 20:17:29Z: a disk-image mount, the Gemini app
launch and two open/save dialogs.

**Classification of each measured unit** (observation, B/C cell or M_desc
server process; rules in §2.1 of this file and in the script):

| Experiment | Non-conforming | Indeterminate | Conforming |
|---|---|---|---|
| A main | 208 | 8 | 0 |
| A extension | 94 | 2 | 0 |
| B/C | 127 | 0 | 0 |
| R | 306 | 2 | 0 |
| Rmem | 20 | 0 | 0 |
| M_desc | 37 | 1 | 0 |
| M_reg | 168 | 0 | 0 |

- **Indeterminate** means no user application appeared among the top five.
  Absence below the top five cannot be shown while those applications were
  alive.
- **Associations, not causation.** The cross-check also records system
  processes above 30%, such as WindowServer. These are associations only.
  - In one M_reg cell (read95 batch 1, 10k), the pairs whose intervals overlap
    the 20:17Z interactive burst have lower throughput in both arms.
  - In R toggle churn, the pairs that overlap WindowServer at 33–53% are
    slower in both arms.
  - Neither association establishes a cause.

### 1.3 Selection

- **Every experiment of the campaign is repeated:** A main with its extension
  rule, B/C, R, Rmem, M_desc and M_reg.
- **Selection is by conformance, not by result.** It does not follow
  closeness to a threshold or a favorable outcome. In particular, it is not
  reduced to the INCONCLUSIVE cells (R, B/C `ops`).
- **No pair of the first campaign is removed** from its analysis, and no new
  verdict is computed from it.

### 1.4 Non-PASS results from earlier releases

- No v0.6.0 or earlier maintainer decision applies to v0.7.0.
- Recurring non-PASS results are measured again and reported as measured:
  - B4 `import-high`;
  - C3 heap growth;
  - B4 `metrics-ops`;
  - A batch-1 p99 and startup;
  - C4 RSS.

## 2. Conformance rules of the new collection (declared before freezing)

### 2.1 What is forbidden, and how it is detected

**Principle:** an allow-list. Anything not allowed is forbidden. Adding names
to a block pattern, as the first campaign did, is not enough.

| Class | Definition (how it is recognised) | Rule |
|---|---|---|
| **Campaign** | Descendants of the chain's process, by PID ancestry, recorded at every sample (not by name) | Allowed |
| **macOS system** | Executable under `/System/`, `/usr/libexec/`, `/usr/sbin/`, `/sbin/`, `/usr/bin/` or `/Library/Apple/`, Apple-signed (`codesign` identifier `com.apple.*`, checked once per new executable) | Allowed; CPU time accounted and reported (§2.3); never invalidates, apart from the deny-list below |
| **System executables that indicate user action** | `diskimages-helper`, `hdiejectd`, `hdiutil`, `com.apple.appkit.xpc.openAndSavePanelService`, `ScreenSaverEngine`, `screencapture`, `installer`, `softwareupdate` (active install), `Spotlight` UI | **Forbidden** |
| **Declared baseline** | (1) the controlling Claude Code CLI process (its PID, recorded at launch) and its parent Claude desktop app; (2) `caffeinate` | Allowed; required idle: no tool call between quiet-period start and chain end; CPU time reported |
| **Everything else** | Any other user process, including browsers, chat, container desktops, terminals, IDEs, editors, other Claude Code sessions, assistant apps, `git`, `cargo`, `rustc`, Python other than the campaign's | **Forbidden** |

- **User input:** the HID idle time (`ioreg -c IOHIDSystem` `HIDIdleTime`),
  sampled with the process table, must increase monotonically from the start
  of the quiet period to the end of the chain. Any reset is keyboard, mouse
  or trackpad input, which is forbidden.
- **Git state:** a read-only snapshot of every clone under the workspace
  (`FETCH_HEAD` mtime, remote-tracking reflog lengths) is taken before the
  quiet period and after the chain. Any change is forbidden activity.
- **Disclosed limits:**
  - a process that starts and exits between two 0.2-second samples can be
    missed by the process check;
  - the CPU-time accounting (§2.3) and the Git snapshot cover such processes
    only in part.

### 2.2 Liveness of the monitor

- **Heartbeat.** The monitor samples the full process table every 0.2 s and
  writes a heartbeat with every sample.
- **Before every child** (every A observation, B/C cell, R, Rmem and M child),
  the collector's gate requires:
  - the monitor PID alive;
  - the last heartbeat younger than 1 s;
  - no forbidden process now;
  - no HID input since the previous check.

  Otherwise it stops the chain before the child starts.
- **After every child,** the gate checks the child's interval:
  - no heartbeat gap above 1 s;
  - no forbidden sample;
  - no HID reset.

  Otherwise it stops the chain.
- **Collectors covered:** the gate wraps the A collector (`run_p0_aa.py`) and
  the B/C collector (`run_lifecycle_qualification.py`), which the first
  campaign did not gate. This is a declared tooling change.

### 2.3 CPU accounting (reported, not a validity threshold)

- For every child, the gate records the cumulative CPU time (`ps -o time`)
  of every non-campaign process at the start and at the end.
- It reports, per child, the CPU seconds consumed by:
  - the macOS system class;
  - the declared baseline.
- This catches short bursts between samples.
- No threshold on system CPU is declared. System CPU is disclosed and never
  invalidates. Any threshold would have to be declared by the maintainer
  before the freeze.

### 2.4 Granularity and outcome (declared)

- **Fail fast at campaign level.** Any forbidden activity, any monitor
  liveness failure, any HID input, or a Git-state change stops the chain. The
  whole attempt is **NONCONFORMING**, with no verdict for any experiment of
  that attempt, including those already completed.
  - This matches the scope of the operator rule. It avoids choosing
    individual pairs or experiments after the fact.
- **Restart.**
  - Only after the cause is removed;
  - into a new directory (`…-attemptN`), with a new attempt record;
  - with the same frozen matrix and seeds (no re-seeding after seeing data);
  - every stopped attempt is kept and reported.
- **Attempt cap.** At most 3 attempts. After the third, the maintainer
  decides.
- **Otherwise:** the frozen statistical rules apply unchanged:
  - v0.4.0 rules for A, with one 12-pair extension per INCONCLUSIVE gated
    metric;
  - the v0.5.0 protocol for B/C;
  - primary 10% for R, and 20% for Rmem;
  - M_reg: throughput 10%, p99 25%, with the probe-revision-2 validity rule.
- **Infrastructure failure:** one rerun of an experiment for an
  infrastructure failure unrelated to the measured code, with its cause
  recorded (unchanged rule).

### 2.5 Host preparation (operator, before the quiet period)

1. Quit every application in the forbidden class: browser, chat, Docker
   Desktop, Terminal, IDEs, assistant apps. Stop every other Claude Code
   session; stopped means no process left, idle is not enough.
2. Leave only the Claude desktop app with the controlling session. That
   session makes no tool call until the chain ends.
3. AC power. No disk images mounted. No pending software update or install.
4. Builds and checks (§3.3) finish first. Then the operator leaves the Mac
   untouched: no keyboard or mouse input from the start of the quiet period
   to the end.

## 3. Matrix, criteria, duration and budget

### 3.1 Identities (unchanged)

| | Identity |
|---|---|
| Candidate | knotrel `e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc` (or a later commit with identical executed code, checked by `__TEXT,__text`) |
| Reference | published v0.6.0, `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538` |
| Benchmarks reference | `bddef0f3` (v0.6.0 probe lockfile) |
| Contention probe | revision 2, the same source as the first campaign |
| Toolchain and host | rustc 1.100.0, `--locked --offline`; Apple M3, macOS 26.5.2 |

### 3.2 Matrix: the first campaign's matrix, unchanged except for

| Item | First campaign | Re-qualification |
|---|---|---|
| Cells, workloads, pairs, warmups, windows, tolerances, analyzers | as frozen | **identical** |
| A seeds | 130700–130702, ext 130710–130712 | **130720–130722, ext 130730–130732** |
| B/C order seed | 50700 | **50720** |
| R order seed | 60700 | **60720** |
| M_reg order seed | 60701 | **60721** |
| M_desc seed | 7 | 7 (the configurations, not the order) |
| Activity gate | named pattern; R, Rmem, M only | allow-list, HID input, liveness, Git state; **every child of every experiment** (§2) |
| Power and thermal | per session (A), per server (M_desc) | before every child, all experiments |
| Matrix wording | `rules.R` "order seed 60500"; "36 servers" | corrected: one order seed per experiment; 38 M_desc servers (36 + 2 open loop) |
| `prepare_campaign.sh` | symlink defect | fix committed before freezing (the source-manifest path) |
| Conformance cross-check | after the campaign | the same script runs as part of the analysis; its output is part of the report |

**Seeds** are declared now, before any result. They differ from the first
campaign's so that the pair order does not simply replay.

### 3.3 Sequence

1. **Tooling (no measurement):**
   - monitor v2 and gate wrappers, with unit tests;
   - matrix, protocol and prepare-script fix;
   - an independent review of the tooling.
2. **Maintainer approval**, then the freeze commit.
3. **Preparation in a new evidence directory**
   (`evidence/v0.7.0-requalification-<sha>/`):
   - release builds, smoke tests, A plan and dry run;
   - binary checksums, plus a `__TEXT,__text` comparison with the first
     campaign's builds, for information.
4. **Host preparation** (§2.5), then a 300-second quiet period with every §2
   check. It stops on any violation before measuring.
5. **The chain:** A main, A extension if required, B/C, R, Rmem, M_desc,
   M_reg, gated per child.
6. **Analysis:**
   - the frozen analyzers;
   - the conformance cross-check;
   - a comparison report with **statistical result and conformance stated
     separately for every cell**;
   - an independent review;
   - every non-PASS result surfaced to the maintainer.

### 3.4 Duration and cost

| Part | Estimate |
|---|---|
| Tooling (monitor v2, gate wrappers, tests, matrix/protocol, prepare fix) | about 3–4 h of agent work, plus an independent tooling review |
| Preparation: builds, smoke tests, A plan, dry run (operator may be present) | about 20 min |
| Quiet period (operator away) | 5 min |
| Chain: as measured in the first campaign (60.2 min, extension in 4 cells) plus per-child gate overhead (about 970 checks × ~0.3 s ≈ 5 min) | **about 65–70 min**; if every A cell needed the extension, about 85 min |
| **Operator away from the Mac** | **about 75–95 min** in one block |
| Cap | 4 h for the chain (unchanged); the maintainer is asked first if a revised estimate exceeds it |
| Analysis, report, independent review | about 2–3 h of agent work |

The first campaign's estimate was 86 min, and it ran in 60.2. The new estimate
is based on the measured durations.

## 4. Comparability of probes and baselines

| Result | Arms | Probe or binary | Comparable? |
|---|---|---|---|
| **M_reg** (first campaign and re-qualification) | v0.6.0 and v0.7.0 servers, same session, fresh server per observation | contention probe revision 2, one binary for both arms (first campaign `e7d0b4b6…`) | **Yes**, like for like. The only source for contention improvement claims |
| **M_desc** | candidate only | revision 2 | Descriptive of the candidate only |
| v0.6.0 M_desc rows used in the first report's §7 for standalone `read95`, batch 64 and open loop | v0.6.0 frozen campaign | **revision 1** (`a3f3c3ff…`). Its toggles hit the node limit at 100k, and carry-over and an off-by-one made some cuts no-ops at both sizes | **No.** Not used to support any improvement |
| v0.6.0 M_desc rows for source-managed configurations (catch-up, imports) | v0.6.0 M supplement | revision 2, but from a run with **conformance not met** (`git fetch` in measured children) | **No.** Not used to support any improvement |
| R, Rmem | v0.6.0 and v0.7.0, same session | `release-cells`/`memory-peak` from the same tooling source; lockfiles differ only in the knotrel versions and the `sonic-rs` tree | Yes |
| A | v0.6.0 and v0.7.0, same session | the same `df635a1e` harness and the shared `measure_e2e` | Yes |
| B/C | candidate vs its own equivalent reference | the candidate probes | Within the candidate only; not release to release |
| R against v0.5.0 (the 25.133 ms figure) | different campaigns | — | **No.** Removed from the report's support |
| Diagnostics (`DIAGNOSTICS-v0.7.0.md`) | both arms, revision 2 | — | Diagnostic only; activity monitor not running; no claim |

**Consequences:**
- Release-to-release contention improvements may be claimed only from M_reg,
  and only from a conforming collection.
- Any feeder catch-up or import-overlap statement against v0.6.0 needs a
  paired M_reg cell. M_reg has one feeder catch-up cell and one import cell.
- Single-window M_desc figures compared with v0.6.0 are not evidence.
- **Not included in this proposal:** an M_desc reference arm, which would
  give a revision-2 v0.6.0 profile. It would be a scope expansion and needs
  its own maintainer decision.

## 5. What this proposal does not do

- **No change to the first campaign's data or verdicts.** It stays
  `NONCONFORMING (campaign)` with its statistical results recorded.
- **No threshold change.** The tolerances stay as frozen. No system-CPU
  validity threshold is introduced (§2.3).
- **No waiver or acceptance** of any non-PASS result.
- **No measurement, push, tag or publication.**
