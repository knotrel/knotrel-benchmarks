# Knotrel v0.7.0 re-qualification protocol

**Status:** sections 1–7 were frozen in `FREEZE.json` (2026-11-17) and are
exhausted (3 NONCONFORMING attempts). Amendment 1 (§8) was frozen in
`FREEZE-A1.json`. Its series a1 is closed with zero attempts after soak a1-1
ended SOAK NONCONFORMING. Amendment 2 (§9) was frozen in
`FREEZE-A2.json` (revision 3). Its series a2 is closed with zero attempts after
soak a2-2 ended SOAK NONCONFORMING. **Amendment 3 (§10) is a DRAFT until
`FREEZE-A3.json` exists in this directory.**
- The machine-readable definition is [`MATRIX.json`](MATRIX.json); this file
  explains it.
- It implements [`RERUN-PROPOSAL.md`](RERUN-PROPOSAL.md), approved by the
  maintainer on 2026-11-17 ("Approve, build tooling"). Differences from the
  proposal are listed in §6.
- The tooling was reviewed independently before freezing
  ([`TOOLING-REVIEW.md`](TOOLING-REVIEW.md)); §7 records how each finding was
  handled.
- Nothing here was chosen after seeing a result of this collection.
- **Relation to the first campaign.** The first v0.7.0 campaign
  (`../v0.7.0-qualification/`) is NONCONFORMING as a whole. Its data and
  verdicts stay unchanged. Nothing from it is reused, pooled or used to
  choose cells.

## 1. References and identities

| Role | Identity |
|---|---|
| Product reference | knotrel **v0.6.0, published** (signed tag `v0.6.0` = `5db9ec4738a7f90bf06a83ea12f35c0dab9ab538`) |
| Benchmarks reference | knotrel-benchmarks tag `v0.6.0` = `bddef0f3…` (reference probe lockfile) |
| Candidate | knotrel `e75ff6a26ec245aefcadfff254e0ac2dd6efc4fc`, recorded in `FREEZE.json` |
| Tooling | knotrel-benchmarks `feature/v0.7.0-qualification` at the commit recorded in `FREEZE.json` |
| Toolchain and host | rustc 1.100.0, release, `--locked --offline`; Apple M3, macOS 26.5.2 |

## 2. Experiments, statistics and analysis

- **Unchanged from the first campaign:** A, B/C, R, Rmem, M_desc and M_reg,
  with the same cells, workloads, pair counts, warmups, windows, tolerances,
  validity rule and analyzers. A unit test deep-diffs both matrices against
  an explicit list of allowed changes, and diffs the two prepare scripts.
- **New seeds, declared before any result:**
  - A sessions 130720–130722, extension 130730–130732;
  - B/C order 50720, R order 60720, M_reg order 60721.
- **M_desc:** 38 server processes (36 closed-loop + 2 open-loop).
- **Analysis bindings:**
  - A: `analyze_bc_qualification.py --rules v0.4.0`;
  - B/C: `analyze_lifecycle_qualification.py`;
  - R, Rmem, M_desc, M_reg: `analyze_v070r_qualification.py` (the first
    campaign's analyzers bound to this matrix).
- **Contention claims:** release-to-release contention statements come only
  from M_reg (the same revision-2 probe binary for both arms). M_desc
  describes the candidate only.

## 3. Conformance

### 3.1 The rule

Nothing outside the allow-list runs, and no user input occurs, from the start
of the quiet period to the end of the chain. The controlling session makes no
tool call in that window.

### 3.2 Process classes

`scripts/conformance_monitor.py` classifies every process; the first matching
rule applies:

| # | Rule | Class |
|---|---|---|
| 1 | the chain process and its descendants (PID ancestry) | campaign |
| 2 | a descendant of the controlling CLI that is not one of the chain's ancestors recorded in the policy (a tool call), whatever its executable, zombies included | forbidden |
| 3 | any other zombie process | the class of its parent |
| 4 | PID 0 | system |
| 5 | an executable on the deny-list, wherever it lives (for an unresolvable process, its `comm`): `diskimages-helper`, `hdiejectd`, `hdiutil`, the open/save panel service, `ScreenSaverEngine`, `screencapture`, `installer`, `softwareupdate`, `git`, `git-*`, `xcodebuild`, `xcrun`, `osascript`, `open`, `ssh`, `scp`, `curl`, `python3`, `cargo`, `rustc`, `rustup`, `sshd`, `sshd-session`, `screensharingd`, `ScreensharingAgent`, `ARDAgent`, `login`, `atrun` | forbidden |
| 6 | a registered foreground app (`lsappinfo`) other than Finder and the Claude desktop app, wherever it lives (for example Safari in its cryptex, DiskImageMounter, Installer, Archive Utility, Keychain Access) | forbidden |
| 7 | the controlling CLI and the chain's ancestors below it (shell, `caffeinate`); the Claude desktop app (`/Applications/Claude.app/`) | baseline |
| 8 | a live process whose executable cannot be resolved | forbidden |
| 9 | an executable in an Apple-controlled location (`/System/Library/`, `/System/Cryptexes/`, `/System/iOSSupport/System/Library/`, `/System/Volumes/Preboot/Cryptexes/`, `/usr/libexec/`, `/usr/sbin/`, `/sbin/`, `/usr/bin/`, `/bin/`, `/Library/Apple/`), or a system app extension (`/System/Applications/*.app/Contents/PlugIns/*.appex/`) | system |
| 10 | an executable in `conformance.host_baseline`: the resident privileged helpers `com.docker.vmnetd`, `com.nordvpn.macos.helper` and `simdiskimaged` | baseline |
| 11 | everything else: apps, other Claude Code sessions, Homebrew and user binaries | forbidden |

**The policy** (`conformance_monitor.py policy`) is written after the grace
period. It refuses the launch if:
- the given controller PID is not a Claude Code CLI executable;
- or it is not an ancestor of the chain;
- or it has any other live descendant (for example a background job the
  session started earlier).

### 3.3 Detection

- **Process table** with executable paths (`proc_pidpath`): every 0.2 s.
- **Foreground apps** (`lsappinfo list`): every second. If `lsappinfo` fails
  or lists nothing, that counts as a monitor failure, which the gate treats
  like a violation.
- **User input.** The HID idle time is read every second by the monitor and
  at every gate check, timestamped with the monotonic clock at the read. A
  reading below the previous one plus the elapsed time, minus 1.0 s, means
  keyboard, mouse or trackpad input. That is any input more than 1 s after
  the previous one; the last input is at least the grace period earlier.
- **Git state.** A read-only snapshot of every clone under
  `/Users/rt/workspace/knotrel` (`FETCH_HEAD` mtime, remote-tracking reflog
  sizes) is taken before the quiet period and at chain end, while the monitor
  still runs.
- **Controller session.** After the grace period, the launch is refused
  (NOT STARTED, no attempt consumed) unless:
  - the given transcript is under `~/.claude/projects/`, was modified in the
    last 10 min and contains this campaign's `run_final_chain.sh` launch;
  - the size and mtime of the transcript and of every file in its session
    directory (subagent transcripts, tool results) are unchanged for 30 s;
  - the HID idle time is at least 60 s.

  The same session state is compared after every step and at chain end. Any
  change means the session or a subagent acted, including tool calls that
  start no process.
- **CPU accounting.** For every child, the CPU seconds of the system,
  baseline and forbidden classes are recorded. This is disclosure only, with
  no threshold.

### 3.4 Liveness, the per-child gate and the end checks

`scripts/conformance_gate.py`, through `scripts/run_v070r_collect.py`, wraps
every measured child; the measuring code of every collector is imported
unchanged:
- A observations (`run_p0_aa.observe_child`);
- B/C cells: exactly the three declared probe binaries. Any other
  absolute-path program stops the collector;
- R, Rmem, M_desc and M_reg children (`Recorder.run`).

**Before each child:**
- no stop recorded;
- the monitor PID alive, its heartbeat at most 1.0 s old;
- zero monitor totals of violations, HID resets and HID read failures;
- a fresh classification, foreground apps included, with nothing forbidden;
- no HID input since the previous check;
- AC power, and no thermal or performance warning.

**After each child:**
- heartbeats covering the child with no gap above 1.0 s, one at its start
  and one after its end;
- no forbidden sample and no HID reset;
- zero monitor totals.

**Monitor lifetime:** the monitor exits on its own if the chain process
disappears. The chain stops the monitor on every exit path.

**At chain end**, with the monitor still running:
- the whole monitor log from the quiet-period start: no heartbeat gap above
  1.0 s, no violation, no reset, no HID failure, with the monitor alive and
  fresh;
- every child each collector recorded has exactly one conforming gate
  record;
- the Git state is unchanged;
- the controller transcript is unchanged.

### 3.5 Outcome (granularity declared now)

- **Fail fast.** Any failed check makes the whole attempt NONCONFORMING, with
  no verdict for any experiment of the attempt, completed ones included.
  - A failure before a child stops at once.
  - A failure after a child is recorded in `gate/gate-stop.json`, so the
    completed observation is saved, and stops at the next check. The chain
    also checks after every step.
- **Records on every exit.** Every exit path writes `logs/CONFORMANCE.txt`
  (CONFORMING, NONCONFORMING, FAILED or NOT STARTED), the final Git state
  and output checksums.
- **Nothing excluded:** no observation, pair or cell is excluded or
  re-classified.
- **Restart:**
  - only after the cause is removed;
  - into a new directory (`prepare_campaign.sh CAND FREEZE N` →
    `…-attemptN`), with the same frozen matrix and seeds;
  - every stopped attempt is kept and reported;
  - at most 3 attempts; then the maintainer decides.
- **Not an infrastructure failure:** a conformance failure does not use the
  one-rerun allowance for infrastructure failures.

### 3.6 Limits (disclosed)

- **Short-lived processes.** A process that starts and exits between two
  0.2-second samples can be missed. The CPU accounting, the Git snapshot and
  the transcript check cover such processes only in part.
- **Tool calls that start no process** are covered only by the transcript
  check. This includes file reads and writes, MCP tools on running servers,
  and desktop-app tools such as the browser pane.
- **Allowed system processes** are not limited in CPU; their CPU is
  reported.
- **Root-writable system directories.** A few firmlinked data directories
  under `/System/Library` and `/usr/libexec` are root-writable, but are
  treated as system.
- **PIDs are not paired with start times.** The baseline PIDs are the
  chain's own ancestors, alive throughout.
- **launchd and cron jobs.** A launchd or cron job running only system
  binaries, without a foreground app or input, is classified as system.
  Remote Login and Screen Sharing must therefore be off (§4). Their daemons
  are also deny-listed.
- **Grace period.** The 120-second grace period before the policy is not
  monitored. Its end is checked: session stable for 30 s, and no input for
  60 s.
- **System dialogs.** Rare system dialogs that register as foreground apps
  (for example Problem Reporter) stop the attempt. This is conservative.
- **Signals.** A SIGTERM sent to the chain alone takes effect only when the
  current collector ends, up to about 27 min during A. The attempt is still
  NONCONFORMING.
- **Monitor priority.** The monitor runs at normal priority. A heartbeat gap
  above 1.0 s stops the attempt, which is conservative; under synthetic load
  (12 busy processes on 8 cores) the largest gap was 0.22 s.
- **Final seconds.** The final checksums are computed after the monitor
  stops.

## 4. Host preparation (operator)

1. **Builds first.** `prepare_campaign.sh` (builds, smoke tests, A plan and dry
   run, informational `__TEXT,__text` comparison with the first campaign)
   finishes before anything below.
2. **Quit every application** (browser, chat, Docker Desktop, Terminal,
   editors, assistant apps, Calendar, System Settings), so that no file
   dialog is left over.
   - Stop every other Claude Code session: no process left.
   - The controlling session has no background job running.
   - Stop the GnuPG agents (`gpgconf --kill all`).
3. **Sharing and power:**
   - Remote Login, Screen Sharing and Remote Management off;
   - AC power;
   - no mounted disk image (other than system ones);
   - no pending install;
   - screen saver set to *Never* (a safeguard alongside `caffeinate -d`).
4. **Allow-list check.** The chain's prelaunch `check` must find nothing
   forbidden; `inventory` lists every non-campaign process.
   - A resident background process not covered by §3.2 needs a matrix
     amendment and a new freeze before measuring. It is never allowed
     silently.
5. **Hands off.** The controlling session starts the chain and ends its turn.
   It makes no further tool call until the chain has finished. The operator
   leaves the Mac within the 120-second grace period and does not touch it
   until the chain ends.

## 5. Sequence, duration and budget

1. `prepare_campaign.sh <CAND> <FREEZE>`: about 20 min.
2. Host preparation (§4).
3. `caffeinate -dimsu sh run_final_chain.sh <CAMP> <CAND> <CONTROLLER_PID> <TRANSCRIPT>`
   (TRANSCRIPT is the controlling session's `~/.claude/projects/…/<id>.jsonl`):
   - a 120-second grace period;
   - transcript validation, a 30-second session-stability check and the
     HID-idle check;
   - the policy, the allow-list check, the inventory and the Git and session
     snapshots;
   - the monitor;
   - a 300-second quiet period, checked like a child;
   - the experiments, gated per child;
   - the end checks;
   - `logs/CONFORMANCE.txt`.
4. Analysis with the bound analyzers and the conformance cross-check. A
   comparison report states the statistical result and the conformance of
   every cell separately. Then an independent review.

**Estimate:** about 74 min for the chain:
- A 27, B/C 8, R 2, Rmem 1, M_desc 12, M_reg 13;
- gate overhead about 3;
- grace period and stability check 3, quiet period 5.

If every A cell needed the extension, about +15 min. Cap 240 min. Operator
away for about 75–95 min.

## 6. Differences from the proposal (declared before freezing)

- **Spotlight removed from the deny-list.** Its UI process is resident.
- **Additions to the deny-list:** `python3`, `cargo`, `rustc`, `rustup`; the
  remote-access daemons (`sshd`, `sshd-session`, `screensharingd`,
  `ScreensharingAgent`, `ARDAgent`); `login` and `atrun`.
  - The campaign's own processes are classified by ancestry first.
  - `python3` only affects the `/usr/bin/python3` shim; other Pythons are
    forbidden by rule 11 anyway.
- **Foreground-app rule (row 6):** forbids apps in system locations, which
  path rules alone cannot catch.
- **Narrower controller baseline:**
  - only the controller and the chain's own ancestors below it are allowed;
  - any other live descendant refuses the launch, and any later one is a
    forbidden tool call;
  - the controller is validated as a Claude Code CLI that is an ancestor of
    the chain.
- **Controller session check:** the transcript and the session directory,
  subagents included, are validated, must be stable before the policy, and
  are compared after every step. This covers tool calls that start no
  process.
- **Grace period:** 120 s between launch and the policy, then a 30-second
  stability check and a minimum of 60 s without input.
- **HID:**
  - read once per second (the proposal said with every process-table
    sample);
  - timestamped at the read with the monotonic clock;
  - tolerance 1.0 s instead of 0.25 s, to avoid false resets under load. It
    still detects any input more than 1 s after the previous input.
- **End checks:**
  - whole-attempt monitor continuity;
  - verification that every recorded child was gated.
- **Host baseline:** exact resident helper executables, from the inventory
  of 2026-11-17.
- **Signatures by location.** Apple signatures are not checked with
  `codesign` per executable. The listed locations are written by Apple
  updates only, except the root-writable firmlinked data directories (§3.6).
- **`__TEXT,__text` comparison** with the first campaign's builds: in
  `prepare_campaign.sh`, information only.
- **Budget:** 74 min, including the grace period and the stability check.

## 7. Independent tooling review

Every blocking and should-fix finding of [`TOOLING-REVIEW.md`](TOOLING-REVIEW.md)
was fixed before freezing, as follows.

| Finding | Fix |
|---|---|
| B1 broad controller baseline | §3.2 rows 3 and 7, the policy refusal |
| B2 controller not validated | the policy validation |
| S1 apps in system locations | row 6 |
| S2 HID false resets | §3.3 |
| S3 no grace period | §5 |
| S4 tool calls without a process | the transcript check; disclosed in §3.6 |
| S5 zombies | row 2 |
| S6 monitor continuity between children | the end checks |
| S7 no trap | the `finish` trap; the monitor exits when the chain is gone |
| S8 gating not verified | the end checks; exact B/C binaries |
| S9 remote and launchd activity | deny-list, §4 item 3, §3.6 |
| S10 undeclared differences | §6, plus the analysis binding (§2) |

**Verification pass** (same reviewer, after the fixes):
- B1, B2, S1–S3 and S5–S10 confirmed fixed. S4 was only partly fixed; the
  three remaining issues are now fixed:
  - **N1** subagents invisible: the session-directory state;
  - **N2** no stability check before launch and comparison only at the end:
    the 30-second stability check and the comparison after every step;
  - **N3** transcript not tied to the launch: the transcript validation.
- **New minor findings:**
  - **Fixed:**
    - N4: minimum 60 s without input at policy time;
    - N5: `lsappinfo` failure counted, path reset between apps;
    - N6: a zombie tool call is forbidden;
    - N7: torn last line ignored by the end check;
    - N8 (B/C part): undeclared program recorded as a gate stop.
  - **Disclosed in §3.6:**
    - N5: system dialogs stop the attempt;
    - N8: SIGTERM latency.

Minor findings of the first pass:
- **Fixed:**
  - M1 (monotonic HID);
  - M2 (deny-listed `comm` of a dead process);
  - M4 (quiet-period CPU);
  - M5 (C locale);
  - M6 (records on every exit);
  - M7 (extension-cell parse);
  - M10 (rule order);
  - M11 (budget keys restored);
  - M12 (Git snapshot before the monitor stops).
- **Disclosed:**
  - M3 (PIDs without start times);
  - M8 (root-writable firmlinked directories);
  - M9 (`python3` scope).

## 8. Amendment 1 (approved 2026-11-18, "Approve, build tooling")

[`AMENDMENT-1-PROPOSAL.md`](AMENDMENT-1-PROPOSAL.md) explains the reasons. The
frozen series ended with 3 NONCONFORMING attempts:
1. user input;
2. the WhatsApp notification extension, started by the system;
3. GoogleUpdater, started by launchd.

None of them produced a verdict.

The amendment changes only host preparation, one pre-launch precondition, an
unmeasured soak and attempt accounting. Sections 1–7 apply unchanged otherwise.
That includes the rule, the classes, the deny-list, HID, liveness, granularity,
the experiments, seeds, statistics, thresholds and analyzers.

### 8.1 What runs, in order

1. **Preparation.**
   - **Soak:** `prepare_soak.sh FREEZE_A1 N a1` creates
     `evidence/v0.7.0-requalification-a1-soakN`. It clones the frozen tooling
     only: no build and no candidate. It refuses before creating anything
     when:
     - `FREEZE-A1.json` is not in FREEZE_A1;
     - N is not 1–9 or exceeds `max_soaks`;
     - any quiesce is unrestored (`check_restored.sh`).
   - **Attempt:** `prepare_campaign.sh CAND FREEZE_A1 N a1` creates
     `…-<cand8>-a1-attemptN`. When FREEZE_A1 is an amendment-1 freeze, it
     refuses before creating anything when:
     - the series is not `a1`;
     - N exceeds `attempts_cap`;
     - no soak has ended `SOAK CONFORMING`;
     - any quiesce is unrestored.
2. **Host preparation (§4)**, with one added item (A4): external keyboards,
   mice and trackpads are off or unplugged, and nothing rests on the built-in
   keyboard or trackpad.
3. **Launch.** `caffeinate -dimsu sh run_final_chain.sh CAMP CAND CONTROLLER_PID TRANSCRIPT [--soak]`.
   For a soak, CAND is `-`.
   0. **Argument check, before anything runs (exit 2):**
      - `--soak` needs CAND `-` and a `*-soakN` directory;
      - an attempt needs a full SHA and a directory that is not a soak
        directory;
      - any other argument is refused.
   1. **AC power check.**
   2. **Quiesce (A1):** `launcher_audit.py quiesce`.
      - It refuses (NOT STARTED) while any `evidence/*/logs/quiesce-restore.json`
        has no successful restore result.
      - It writes `logs/quiesce-inventory.json` first, from the same collector
        as the audit.
      - It boots out `conformance.quiesce.launchd` from `gui/<uid>`.
      - It renames each bundle in `conformance.quiesce.park_apps` to
        `<name>.parked-qualification`.
      - The manifest is written before each action and updated after it,
        durably (fsync). It holds each action's intent and its quoted manual
        inverse. Each action is verified.
      - After parking, it confirms with `pluginkit` that no extension still
        resolves inside a parked bundle.
   3. **Audit (A2)**, before the grace period: `launcher_audit.py audit`. A
      failure is NOT STARTED.
   4. **Grace period.** Then, as in §5: transcript validation, stability check
      and HID idle check.
   5. **Audit (A2) again**, just before the policy. A failure is NOT STARTED.
   6. **As in §5:** policy, allow-list check, inventory, Git and session
      snapshots, monitor and quiet period.
   7. **Experiments.** For an attempt, the experiments exactly as in §5. For a
      soak (A3), a single gated campaign child (`/bin/sleep`,
      `conformance.soak.duration_s` = 4800 s). The end checks then require
      exactly one gated `soak` child and no measurement output. The result
      prefix is `SOAK`.
4. **`finish`, on every exit path.** Further INT, TERM and HUP signals are
   ignored from here on.
   1. Stop the monitor.
   2. Write the Git state, `CONFORMANCE.txt`, the monitor log copy and the
      checksums.
   3. **Then** run `launcher_audit.py restore`:
      - bootstrap every job that was booted out;
      - rename each parked bundle back;
      - never overwrite an occupied path;
      - write `logs/quiesce-restore-result.json`;
      - add a `RESTORE` line to `chain-steps.txt` and print `RESTORE OK` or
        `RESTORE FAILED`.
      - Only actions whose intent was recorded are undone.
   4. A failed restore exits 21. RESULT and `CONFORMANCE.txt` are not
      changed. The failure is reported to the maintainer and never retried
      silently.

### 8.2 The audit (A2)

**Apple criterion.** A job counts as *Apple* only when both its plist and its
program are in Apple locations:
- **Locations:** `SYSTEM_PREFIXES` plus `/System/Applications/` (sealed
  system volume). This wider set applies to this criterion only; process
  classification is unchanged.
- **Labels are ignored.**
- **A job without a plist,** such as one shown as `(submitted by …)`, or a
  failed `launchctl print`, counts as third-party.

**A failure is any of:**
1. A loaded job in `gui/<uid>` or `user/<uid>` that is third-party, not in
   `allow_jobs`, and matches no `allow_jobs_prefix`, and either:
   - has `RunAtLoad`, `KeepAlive`, `StartInterval`, `StartCalendarInterval`,
     `WatchPaths`, `QueueDirectories`, `StartOnMount` or `LaunchEvents`; or
   - has triggers that cannot be read (fail closed).
2. A third-party app extension (`pluginkit -m -A -v`) whose bundle path
   exists and is not in `allow_extensions` (empty).
3. A non-empty user crontab.

**Recorded but not gating:** third-party jobs in the `system` domain. Root
would be needed to act on them. The resident ones are in `host_baseline`, and
anything they spawn is still forbidden.

**`allow_jobs` and `allow_jobs_prefix`.** An entry is verified against
the job, not trusted from its label. A matching job must:
- run a program under the entry's `program_prefix` (`null` means the job has
  no program line);
- declare only the triggers the entry lists;
- have readable triggers, unless the entry sets `unreadable_ok`.

Otherwise the audit fails. Entries, each with its reason in MATRIX
`conformance.quiesce`:
- `com.docker.helper` (SMAppService, no plist);
- three ShipIt updaters, which run on demand from apps that are quit;
- `com.jetbrains.toolbox` (triggers limited to `RunAtLoad`);
- four CoreSimulator XPC services;
- the Claude desktop app's job, by prefix.

**Triggers come from the plist on disk at audit time.** A plist edited after
it was loaded is read as edited. This is disclosed.

**Operational note.** The audit fails closed, so the following stop a launch
as NOT STARTED, consistent with §4 item 2 (quit every application):
- an open application other than the Claude desktop app. Its runningboard job
  (`application.<bundle-id>…`, "submitted") is third-party and unknown, and
  this applies to Apple applications too;
- a job that exits between the domain listing and its own print.

### 8.3 Attempt accounting (A5)

- **New series:** `a1`, with a cap of 3 attempts.
- **The first CONFORMING attempt is final,** whatever its statistical result.
- **No further series** without a new maintainer decision, recorded before
  any result of this series.
- **Soaks:** at most 2, and they are required before attempt 1.
  - A soak consumes no attempt and produces no data.
  - After a failed soak, the only changes allowed are those in
    `conformance.soak.allowed_changes_after_a_soak`. They never widen a
    class, the baseline or the deny-list, and each needs a new freeze and
    approval.
- **Reporting:** the report lists every attempt of both series, every soak,
  and the outputs of the exhausted attempts
  ([`EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256`](EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256)).
  Those outputs have no verdict and are not reused.

### 8.4 Differences from the proposal (declared before freezing)

The tooling review (§8.6) found differences in the first tooling commit. They
are now implemented as proposed:
- the inventory before quiesce;
- the `pluginkit` check after parking;
- `prepare` refusing after an unrestored manifest;
- allow-list entries checked for triggers.

What remains different is listed below.

1. **Tool layout.**
   - A2, quiesce and restore are one script, `scripts/launcher_audit.py`. The
     proposal had a `conformance_monitor.py` subcommand and two shell scripts.
   - `conformance_monitor.py` is unchanged.
2. **Audit timing.** The audit also runs before the grace period, so a failure
   shows up at once. It still runs again just before the policy.
3. **`/System/Applications/` added** to the launcher criterion's Apple
   locations. Two Apple jobs live there: `com.apple.systemsettingsagent`
   (`LaunchEvents`) and `com.apple.systemprofiler` (`RunAtLoad`). Without it
   they would fail the audit.
4. **Four CoreSimulator XPC services added to `allow_jobs`.** The first live
   audit, read-only and before any approval-dependent action, found them in
   `user/501`. They are on-demand XPC services of Xcode under
   `/Library/Developer`; `simdiskimaged` is already `host_baseline`.
5. **A process already running from a parked bundle is not ended** by
   quiesce. Parking stops new launches only. A leftover process, such as
   WhatsApp's extension started earlier, makes the allow-list check fail
   (NOT STARTED). The operator then ends it with the maintainer's approval.
6. **Root-owned plist round trip.** The bootout and bootstrap round trip of
   each Q job was run once for real on 2026-11-18, including the root-owned
   `/Library/LaunchAgents/com.microsoft.update.agent` from `gui/501`. It is
   recorded in `evidence/v0.7.0-requalification-a1-roundtrip/logs/`:
   - after quiesce the audit passed;
   - restore succeeded for all 4 actions, and the audit then failed exactly
     on the Q jobs and the two WhatsApp extensions;
   - restoring the MAU agent started Microsoft Update Assistant, as
     disclosed.
   - That round trip ran the first tooling commit. The final quiesce and
     restore code differs (intent-based restore, inventory, `pluginkit`
     check). The bootout and bootstrap calls themselves are unchanged.
7. **Allow-list format.** The allow-list is a set of verified entries, each
   with a program prefix, permitted triggers and a reason, instead of a list
   of labels. This is stricter.
8. **Prepare enforcement.** `prepare_campaign.sh` also enforces the series
   name, the attempt cap and a prior `SOAK CONFORMING`.

### 8.5 Manual recovery

Use this if `RESTORE FAILED` was printed, or if the chain was killed with no
trap (SIGKILL or power loss). The next quiesce and both prepare scripts
refuse while this is unresolved.
1. **Read the manifest.** Open `CAMP/logs/quiesce-restore.json`. Its
   `manual_restore` array lists, quoted for `sh`, the inverse of every action
   that was started:
   - `launchctl bootstrap gui/501 '<plist>'` for each job booted out;
   - `mv -n '<app>.parked-qualification' '<app>'` for each parked bundle.
     `-n` never overwrites. If the original path is occupied, for example
     after a reinstall, the maintainer decides which copy to keep.
2. **Run them.** Then check:
   - `launchctl print gui/501/<label>` succeeds for each job;
   - each bundle is back at its path.
3. **Record the restore.** Run
   `python3 scripts/launcher_audit.py restore --camp CAMP` from the campaign's
   tooling clone. It finds everything in place and writes
   `quiesce-restore-result.json` with `ok: true`, which clears the block.
4. **If the manifest is unreadable** (empty after a power loss), use
   `logs/quiesce-inventory.json` and MATRIX `conformance.quiesce`:
   - bootstrap each Q job from the plist path the inventory records;
   - rename each parked bundle back.

   Then write a correct manifest and run step 3. This case is reported to the
   maintainer.

### 8.6 Tooling review (amendment 1)

An independent reviewer read the first tooling commit against the approved
proposal and the frozen protocol, with read-only access and a live read-only
audit.
- **Checked and found correct:**
  - the restore ordering;
  - crash safety and idempotence;
  - the soak prerequisites;
  - the classification of `caffeinate` and `launchctl`;
  - the frozen material unchanged except as declared;
  - no rule, threshold, seed, analyzer or granularity change.

| Finding | Disposition |
|---|---|
| B1 no manual recovery in §8 | §8.5 |
| B2 undeclared differences (inventory, post-park check, prepare refusal, allow-list triggers) | implemented (§8.1, §8.2); remaining differences in §8.4 |
| S1 restore could fail when nothing was changed | restore keyed on recorded intent; tested |
| S2 allow-list trusted labels and skipped triggers | verified entries (program prefix, permitted triggers, `unreadable_ok`); tested including spoofing |
| S3 second signal skipped the restore | `finish` ignores INT/TERM/HUP |
| S4 failed restore invisible | `RESTORE` line in `chain-steps.txt`, exit 21 |
| S5 soak flag not tied to the directory | argument check before anything runs (exit 2); tested |
| S6 `prepare_soak.sh` gaps | FREEZE-A1 required, N validated, unrestored check; tested |
| S7 fail-open parsing | the `pluginkit` footer count must match; `crontab` accepts only "no crontab for"; tested |
| Minor: crash window, quoting, fsync | intent and manual command recorded before each action; `shlex.quote`, `mv -n`; fsync of file and directory |
| Minor: triggers read from disk; application jobs | disclosed (§8.2) |
| Minor: `required_before_first_attempt` not enforced; old-series naming | enforced in `prepare_campaign.sh` (§8.1) |
| Test gaps | real-format `launchctl` and `pluginkit` fixtures, prefix rule, pre-existing parked path, corrupt result or manifest, argument checks added |

**Verification pass** (same reviewer, read-only, live audit):
- **All findings above confirmed fixed:** B1, B2 and S1–S7.
  - All 10 allow-list entries match the live host.
  - The `pluginkit` footer matches the parsed count (435).
  - Nine bad argument sets are refused before anything runs.
- **New minor findings, all fixed:**
  - A prior `SOAK CONFORMING` now counts only if its tooling clone is at the
    same FREEZE commit.
  - `prepare_soak.sh` accepts only the series `a1`.
  - The chain refuses a CAND that does not match the campaign directory, and
    strips a trailing `/` from CAMP.
  - `run()` documents that callers parse output only on exit code 0.
  - `finish` is now executed by tests (`FinishExecuted`): the real chain runs
    against a stub tooling clone. The tests show that:
    - the restore runs after the Git state, `CONFORMANCE.txt` and the
      checksums are written;
    - a failed restore exits 21;
    - a TERM and a HUP during the restore do not skip it.
- **Disclosed:**
  - `prepare_campaign.sh` runs `check_restored.sh` from the directory it is
    invoked from (the worktree at the freeze commit), not from a clone.
  - The manual command `restore --camp <CAMP>` must be run from the tooling
    clone (§8.5).

## 9. Amendment 2 (option A approved 2026-11-18, "Option A")

**Why.** Soak a1-1 (`evidence/v0.7.0-requalification-a1-soak1`) ended
`SOAK NONCONFORMING` (exit 13).
- At 11:11:01Z the controlling Claude Code CLI (pid 32478) spawned
  `/Library/Developer/CommandLineTools/usr/bin/git` while idle. Git is
  deny-listed, and rule 2 forbids any new descendant of the controller.
- There was no human input and no controller tool call.
- The quiesce, the audit and the restore all worked.
- The options are in [`AMENDMENT-2-OPTIONS.md`](AMENDMENT-2-OPTIONS.md). The
  maintainer chose option A.

**Maintainer decisions (2026-11-18).**
- Option A: "Option A".
- Options §3, items 3–5, decided after the first tooling review:
  - soak budget: "No reset" (§9.7);
  - series: "a2, cap 3", with series a1 closed (§9.7);
  - review path: "Verification pass" (§9.9).

**What changes.** Only the controller and how the chain is launched.
- The maintainer launches the chain from Terminal.app with Claude quit
  completely. MATRIX `conformance.controller_kind` is `terminal`, and the
  details are in `conformance.amendment_2`. The keys it supersedes are listed
  in `amendment_2.superseded_keys`.
- Unchanged:
  - the rule, the deny-list, HID, liveness and granularity;
  - experiments, seeds, statistics, thresholds and analyzers;
  - the quiesce, the audit and the soak of §8, except one allow-list entry
    (§9.5).

### 9.1 Controller check

`conformance_monitor.py policy --controller-kind terminal` refuses the launch
unless:
- **Terminal is the top.** Terminal.app
  (`/System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal`) is
  the chain's topmost ancestor, with launchd as its parent.
- **Exact lineage.** The ancestors in between are exactly `/usr/bin/login`
  and `/bin/zsh` (`TERMINAL_LINEAGE`). Anything else is refused, for example
  `sudo`, `osascript`, `open`, `script`, another shell, or `caffeinate` as a
  parent.
- **A `caffeinate` child.** The chain has a live `/usr/bin/caffeinate` child
  (§9.11).
- **One window, one tab.** Terminal has no other live descendant.
- **One Terminal.** There is no other Terminal process.
- **No Claude process.** None of these runs:
  - the desktop app;
  - the Claude Code CLI, inside the app or as a native install under
    `~/.local/share/claude/versions/`;
  - a process named `claude`;
  - a process whose command line names claude-code, such as a node-based CLI.

The check runs three times:
1. in `precheck_terminal.sh`, before the chain (§9.6). A refusal starts
   nothing;
2. at chain start, before the quiesce (`logs/policy-prequiesce.json`). A
   refusal is NOT STARTED;
3. for the policy, after the grace period. A refusal is NOT STARTED.

### 9.2 Classes (controller kind `terminal`)

Changes to §3.2:
- **Rule 2** applies to Terminal's descendants. A new window or tab, or any
  process started beside the chain, is forbidden.
- **Ancestors are baseline.** Terminal and the chain's ancestors below it are
  `baseline` right after rule 2, before the deny-list, because `login` is
  deny-listed. This holds only while each PID still runs the executable the
  policy recorded for it (`controller_paths`) and is still an ancestor of the
  chain in that sample. A reused PID falls through to the other rules, so for
  example `git` is forbidden.
- **Foreground apps.** The allowed foreground apps are Finder and
  Terminal.app.
- **Claude is forbidden.** The Claude desktop app is no longer baseline. Any
  Claude executable is `forbidden`, wherever it lives. A Claude CLI that is
  not recognized by name is forbidden by rule 11.
- **Scope.** This changes the controller's baseline class, which
  `soak.allowed_changes_after_a_soak` does not cover. The maintainer approved
  it as option A.
  - Net effect: Claude leaves the baseline.
  - Terminal, `login` and `zsh` enter it only as the chain's own ancestors.
    `caffeinate` is the chain's child, so it is campaign class.

### 9.3 Claude state (replaces the transcript check)

The size and mtime of every file under `~/.claude/projects` are taken twice:
- after the grace period, then again `session_stable_s` later. If unreadable
  or different, the launch is NOT STARTED;
- at every gate check and at chain end, compared with that state. If
  unreadable or different, the attempt is NONCONFORMING (exit 16).

The check fails closed: an unreadable tree never compares equal. With Claude
quit, nothing writes there. Other Claude files (`history.jsonl`, `sessions/`,
and so on) are not compared, but any Claude process is forbidden.

### 9.4 Environment

The chain inherits the environment of the Terminal login shell instead of
the Claude Code CLI's. This is a declared difference. The launch command:
- sets `PATH` to `CAMP/bin`, then `/usr/bin:/bin:/usr/sbin:/sbin`.
  `CAMP/bin` holds one entry, a `python3` symlink that the prepare script
  makes to the python3 it used. No other tool comes ahead of `/usr/bin`;
- uses absolute `/usr/bin/caffeinate` and `/bin/sh`;
- gives stdin from `/dev/null`.

Through the symlink, `sys.executable` is `CAMP/bin/python3`. `sys.prefix`
and the executable the monitor sees stay the framework's. No v070r collector
records the interpreter path.

`prelaunch-host.txt` records:
- python3's path and version;
- `PATH`;
- the names of the environment variables;
- the values of the `PYTHON*`, `DYLD_*`, `RUST*`, `CARGO*`, `LANG` and `LC_*`
  variables. Names containing `TOKEN`, `SECRET`, `PASSWORD` or `KEY` are
  redacted.

### 9.5 Allow-list

In `quiesce.allow_jobs_prefix`:
- **Removed:** `application.com.anthropic.claudefordesktop.`, the Claude app,
  which is now quit.
- **Added:** `application.com.apple.Terminal.`, Terminal's runningboard job,
  with program prefix `/System/Applications/Utilities/Terminal.app/`. It has
  no triggers, and undeterminable triggers are allowed.
- With Terminal open, the live audit (2026-11-18) failed on this job only,
  besides the jobs the quiesce handles.

### 9.6 Sequence for the maintainer

1. **Preparation.** The controller (Claude) runs `prepare_soak.sh` or
   `prepare_campaign.sh`. It writes `CAMP/LAUNCH-COMMAND.txt`
   (`launch_command.sh`), and the controller shows it to the maintainer.
2. **Host.** §4 and §8 apply: AC power, every application quit, external
   input devices off.
3. **Quit Claude.** Quit the Claude desktop app completely (Cmd-Q). If a
   Claude helper outlives it (for example `chrome_crashpad_handler`), the
   precheck lists it and refuses. End it, or restart the Mac, before running
   the command again.
4. **Open one Terminal window and paste the command.**
   - It first runs `precheck_terminal.sh`, which is read-only.
     - It refuses if the directory was already launched, if the Mac is not on
       AC power, or if the controller check (§9.1) fails.
     - It also refuses if a forbidden process runs now. This is the read-only
       `check`, with its own policy.
     - It also refuses if `~/.claude/projects` is unreadable or a quiesce is
       unrestored.
     - On refusal it prints why and starts nothing. Fix the cause and paste
       the same command again.
   - On success it starts the chain. Its output is appended to
     `CAMP/chain-launch.log`, which is never overwritten.
5. **Leave the Mac** for the whole run. Do not reopen Claude, open a window
   or tab, or type. Typing is caught as HID input, and its text never reaches
   the chain, whose stdin is `/dev/null`.
6. **After the result.** When the window prints the log's last lines, reopen
   Claude and tell the controller. It reads the logs and reports.

A `RESTORE FAILED` line means §8.5 applies.

### 9.7 Accounting

- **Decided:** the series ("a2, cap 3") and the soak budget ("No reset").
- **Series a1.** Closed with zero attempts, recorded and reported.
- **Series a2.**
  - Cap: 3 (`amendment_2.attempts_cap`).
  - The first CONFORMING attempt is final.
  - No further series without a prior maintainer decision.
- **Soaks.** `soak.max_soaks` (2) counts every soak of every amendment.
  - Soak a1-1 used one, so the only possible a2 soak is
    `v0.7.0-requalification-a2-soak2`.
  - A SOAK CONFORMING soak from the amendment-2 freeze is required before
    attempt 1. `prepare_campaign.sh` enforces this.
- **Budget (`series_budget.sh`, both prepare scripts).** Every directory
  counts, whatever its result. This is the amendment-1 rule: soak N at most
  `max_soaks`, attempt N at most `attempts_cap`. The following are stricter
  than amendment 1:
  - numbers are never reused or skipped;
  - a directory without `logs/CONFORMANCE.txt` blocks the next one (never
    launched, or killed without its trap);
  - no attempt is prepared after a CONFORMING one.
- **A refusal inside the chain uses up its directory.** That is why
  `precheck_terminal.sh` runs first.
  - With no soak reset, a NOT STARTED a2-soak2 exhausts the soak budget, and
    the maintainer decides.
  - Refusals the precheck cannot prevent: HID input in the last 60 s before
    the policy, the launcher audit after the quiesce, `~/.claude/projects`
    still changing, or a process that starts between the precheck and the
    prelaunch check.
- **Directories.** Attempts go in `…-e75ff6a-a2-attemptN`. The prepare
  scripts refuse series a1 and amendment-1 freezes.

### 9.8 Limits and other differences (disclosed)

- **Short-lived Claude processes.** A Claude process that starts and exits
  between two 0.2 s samples, and writes nothing under `~/.claude/projects`, is
  not detected.
- **claude-cli mode is unchanged in classification.** A parity test checks
  it against the amendment-1 monitor over more than 2,000 synthetic process
  tables. Its outputs differ in three ways:
  - `policy.json` and the monitor's start record gain `controller_kind` and
    `controller_paths`;
  - a policy call without `--controller` exits 1 instead of 2;
  - policies written before this amendment load as `claude-cli`.
- **Live check not done.** The Terminal lineage was observed live
  (Terminal → `login` → `-zsh`). A full policy check from a real Terminal
  window could not be run while Claude is open, because the policy refuses
  then. `precheck_terminal.sh` is that check at launch time, and it starts
  nothing on refusal.

### 9.9 Tooling review (amendment 2)

**Decided (options §3, item 5):** "Verification pass". The same reviewer
checks the fixes before the freeze.

An independent reviewer read the first draft (`3795f144`) with read-only
access.

| Finding | Disposition |
|---|---|
| B1 options §3.3–3.5 recorded as approved | marked pending, then decided by the maintainer and recorded with the wording |
| B2 NOT STARTED accounting more permissive than amendment 1 | withdrawn: every directory counts (the amendment-1 rule), with stricter numbering checks; `precheck_terminal.sh` added so that refusable launches start nothing |
| S1 any Apple-location ancestor accepted, placed before the deny-list | exact lineage (`login`, `zsh`, `caffeinate` in revision 2, corrected to `login`, `zsh` plus a required `caffeinate` child in §9.11); tested with `sudo`, `osascript`, `open`, `script`, `bash` |
| S2 PID reuse more permissive | the policy records each ancestor's path; baseline only while PID and path match; tested |
| S3 tree-state fails open | fails closed (`TREE-STATE-FAILED`); NOT STARTED before the monitor, NONCONFORMING after |
| S4 native-install and node-based CLI not detected | `~/.local/share/claude/versions/` pattern and command-line scan; tested |
| S5 launch environment undeclared | §9.4: `PATH` pinned, absolute paths, environment recorded |
| S6 log overwritten, tty stdin | the log is appended, stdin is `/dev/null`, typing text corrected |
| S7 superseded keys unstated | `amendment_2.superseded_keys`; the allow-list change named in `changes`; the module docstring updated |
| M1 grace message lost in the log | written to `/dev/tty` |
| M2 refusal burns a directory | stated (§9.7); prevented by `precheck_terminal.sh` |
| M3 message for a killed chain | corrected |
| M4 CLI-level differences | declared (§9.8) |
| M5 exit status through `caffeinate` | verified: `caffeinate` returns the child's status |
| M6 other Claude files not compared | declared (§9.3) |

**Verification pass (`3795f144..39e4cba1`).** All earlier findings are
fixed, declared or reduced to a small residue, and nothing blocks the
freeze. The follow-up fixes:

| Finding | Disposition |
|---|---|
| N1 a refusal inside the chain spends the last soak | the precheck runs the read-only process check; the budget consequence is stated (§9.7) |
| N2 a lingering Claude helper | stated (§9.6 step 3); the precheck refuses, which is correct |
| N3 zsh `NO_CLOBBER` | not set on this host; with it set, the chain does not start, which is safe |
| N4 PATH could bring other tools | `PATH` starts with `CAMP/bin`, which holds only a `python3` symlink (see M-b) |
| N5 precheck refusal tests | precheck policy and process-check refusals tested, files written pinned, one-liner parsed with `zsh -n` |
| S2 residue: a reused PID that is no longer an ancestor | the lineage baseline also requires the PID to be an ancestor of the chain in that sample; in terminal mode, rule 2 exempts a recorded PID only under the same condition (found by the new test: a reused PID had fallen through to `system`) |
| S3 cosmetic: wrong message when only S2 fails | a failure in either reading is reported as "unreadable" |
| S5 residue: other variables inherited | the values of `PYTHON*`, `DYLD_*`, `RUST*`, `CARGO*`, `LANG` and `LC_*` are recorded |
| S7 residue: the "no attempt consumed" phrase | `superseded_keys.grace_period` says it is now stricter |

**Re-verification (`39e4cba1..2dc157ab`).** No blockers and no should-fix
findings. Two minor findings, both fixed:

| Finding | Disposition |
|---|---|
| M-a possible secrets in `prelaunch-host.txt` | values whose names contain TOKEN, SECRET, PASSWORD or KEY are redacted |
| M-b the python3-directory check used a fixed tool list | `PATH` starts with `CAMP/bin`, which holds only a `python3` symlink. The python.org directory on this host holds about 50 other tools, so an allow-list was not workable |

### 9.10 Audit race (freeze revision 2)

**Decision (2026-11-18):** "Fix and refreeze".

**Why.** Spotlight starts and ends `com.apple.mdworker.shared.<id>` instances
in the gui and user domains all the time.
- An instance that exits between the domain listing and its own
  `launchctl print` could not be read.
- The audit then failed closed, and the launch was NOT STARTED.
- §8.2 already disclosed this as a NOT STARTED cause. With one soak left and
  every directory counted, it would exhaust the soaks.
- It was seen in a live audit on 2026-11-18, while Spotlight was indexing.

**Change (`launcher_audit.py inventory`).** When printing a job in a gated
domain fails, the audit lists the domain again:
- **Label gone:** a job no longer loaded can't fire. It is recorded in
  `exited_during_inventory` and not audited.
- **Label still there:** the job is printed once more. A second failure is
  still third-party with unknown triggers, so the audit fails closed.

A non-Apple label that exits is also reported as a warning on stderr. The
warning is only informational and never fails the audit.

Nothing else in the audit changes. The tests cover the exited, retried,
second-failure and failed re-list cases. A failed re-list raises, so the
audit fails closed.

**Review of the delta (`e57106bc..7a0f4e36`).** No blockers and no
should-fix findings. The three minor findings are addressed: the non-Apple
warning, the re-list test and the `sys.executable` disclosure (§9.4).

**Freeze.** `FREEZE-A2.json` revision 2 supersedes freeze `e57106bc`.
- The soak directory prepared from `e57106bc` was never launched and holds no
  data. It is kept, renamed
  `v0.7.0-requalification-a2-soak2.unlaunched-e57106bc`, and is outside the
  soak budget.
- `a2-soak2` is prepared again from revision 2. The soak budget is unchanged:
  one soak left.

### 9.11 Lineage correction (freeze revision 3)

**Decision (2026-11-18):** "Fix and refreeze".

**What happened.** The first launch of a2-soak2 was refused by the precheck,
so nothing started and no soak was used. The precheck reported the lineage
`login`, `zsh`, without `caffeinate`.

**Cause.** Revision 2 required `/usr/bin/caffeinate` as an ancestor of the
chain. That was assumed, not observed: the earlier live check of the Terminal
tree had stopped at `-zsh`, and the reviews checked the code against the
assumption. On this host, `caffeinate UTILITY` behaves differently:
- it execs the utility in its own PID;
- it forks a `caffeinate` child that holds the assertions on the utility's
  behalf (`pmset -g assertions`: "caffeinate asserting on behalf of
  '/bin/sh'").

**Change.**
- **Lineage.** `TERMINAL_LINEAGE` is `/usr/bin/login`, `/bin/zsh`. The
  baseline loses `caffeinate`.
- **Required child.** The policy requires a live `/usr/bin/caffeinate` child
  of the chain, checked in the precheck and in the chain's policy. This is a
  new requirement, so it is stricter. The child is a chain descendant, so it
  is campaign class.
- **Tests** use the real tree. A live test (`CaffeinateLive`) checks how
  `caffeinate` behaves on this host. A live check from a `caffeinate`-wrapped
  shell found the child as expected.

**Freeze.** `FREEZE-A2.json` revision 3 supersedes revision 2 (`58ed921a`).
- The directory prepared from revision 2 was not launched: the precheck
  refused, it holds only `logs/precheck-policy-error.txt`, and no data. It is
  kept, renamed `v0.7.0-requalification-a2-soak2.unlaunched-58ed921a`, and is
  outside the soak budget.
- `a2-soak2` is prepared again. The soak budget is unchanged: one soak left.
- Earlier statements in this section that the lineage including `caffeinate`
  had been observed were wrong and are corrected above.

## 10. Amendment 3 (background processes allowed)

**Maintainer decision (2026-11-18).**
- The maintainer asked: "Non possiamo solo accettare che altri processi
  possano essere running? E' un laptop non un server dedicato".
- The maintainer then delegated the choices: "Scegli tu quello che ci aiuta
  a portare risultati sensati ma anche a non restare bloccati per giorni".
- The choices below were made by the controller under that delegation and
  are recorded in MATRIX `conformance.amendment_3`.

**Why.** No run so far was conforming:
| Run | Cause | Monitor violations |
|---|---|---|
| attempt 1 | user input during the quiet period (HID reset) | — |
| attempt 2 | WhatsApp's notification extension | 57 |
| attempt 3 | GoogleUpdater | 74 |
| soak a1-1 | `git`, spawned by the Claude Code CLI | 1 |
| soak a2-2 | Safari's `CacheDeleteExtension`, caught at startup with no resolvable path (rule 8) | 1 |

- Amendments 1 and 2 removed the persistent causes: host preparation, the
  quiesce, and the Terminal controller with Claude quit.
- The last two failures were single samples of harmless processes.
- On a laptop, macOS starts background processes on its own, and over hours
  of 0.2 s samples one is always caught. A rule that forbids every unknown
  process is not workable there.

### 10.1 Classes

`conformance.background_allowed` is true, so the policy sets
`background_allowed` (terminal kind only):
- **Rules 8 and 11 give `background`.** A live process whose executable can't
  be resolved, or that falls in no other class, is allowed. Its CPU time is
  recorded under `background`.
- **Rules 1–7 are unchanged.** These stay forbidden, including when the path
  is unresolved or `ps` shows the process as `(name)`:
  - any new descendant of Terminal;
  - deny-listed executables (`git`, `cargo`, `rustc`, `ssh`, installers and
    so on). Parentheses are stripped, and a name cut to 16 characters
    matches by prefix;
  - outside the campaign, the interpreters `Python` (the python.org
    framework executable) and `node`;
  - foreground apps other than Finder and Terminal;
  - any Claude executable: its path, a name starting with `claude`, or a
    command line naming claude-code. The monitor scans command lines once a
    second, which replaces §9.2's reliance on rule 11 for a CLI not
    recognized by name.
- **Still checked:**
  - HID input;
  - the Git state;
  - `~/.claude/projects`;
  - monitor liveness and the per-child gate;
  - the controller check, the precheck and the caffeinate child.

### 10.2 Launcher audit and quiesce

- **The audit is recorded, not a precondition** (`conformance.launcher_audit`
  is `record`). Findings go to `logs/launcher-audit*.{json,txt}` and to a
  `chain-steps.txt` line, and the launch continues.
- **The quiesce and restore of the updaters and WhatsApp are unchanged.** They
  reduce background noise. A failed quiesce, or an unrestored earlier quiesce,
  still stops the launch.

### 10.3 Interference: disclosure only

- **Recording.**
  - Each gate child record has `cpu_seconds_by_class`, which now includes
    `background`. It is the difference of `ps` CPU totals before and after
    the child, so a process that starts and exits within the child is not
    counted. This under-count is disclosed.
  - The monitor's per-second `top` record adds `background_pcpu_sum`, the
    sum of `ps` %CPU of the background processes in that sample. It does see
    short-lived processes that are alive at a sample.
- **Reporting.** This is specified now and implemented in the comparison
  report before the analysis. It is not part of the frozen tooling. For each
  cell, the report shows:
  - background and baseline CPU as a share of one core over the child's
    duration;
  - the mean `background_pcpu_sum` over the child.

  It marks cells above 25% of one core on either measure "read with
  caution".
- **No invalidation.** The paired, interleaved design carries background
  noise into both versions. A threshold that invalidated would bring back the
  blocking this amendment removes.

### 10.4 Accounting

- **Series a2.** Closed with zero attempts, recorded and reported.
- **Series a3.**
  - Cap: 3 (`amendment_3.attempts_cap`).
  - No soak.
  - The first CONFORMING attempt is final.
  - Every directory counts (`series_budget.sh`).
- **Prepare scripts.** `prepare_campaign.sh` takes series a3 under a
  `FREEZE-A3.json` freeze, and refuses series a2 and amendment-2 freezes.
  `prepare_soak.sh` refuses an amendment-3 freeze.
- **No retroactivity.** Every earlier attempt and soak stays as recorded and
  is reported.

### 10.5 Launch

The same as §9.6: the prepare script writes `CAMP/LAUNCH-COMMAND.txt`, and the
maintainer runs it from the only Terminal window with Claude quit.

### 10.6 Review (amendment 3)

An independent reviewer read the draft (`c35c1929`). It found no blockers.

| Finding | Disposition |
|---|---|
| S1 a deny-listed or Claude process with an unresolved path or a `(name)` comm became background | parentheses stripped, prefix match for cut names, `claude*` names forbidden; tested |
| S2 a Claude CLI not recognized by name became background | command-line scan in the monitor, once a second; tested |
| S3 interference reporting described as existing; under-count | reporting specified as to-be-implemented in the comparison report; under-count disclosed; `background_pcpu_sum` added to the monitor log |
| S4 cause table incomplete | all five runs listed with their causes and violation counts |
| M1 interpreters became background | `Python` and `node` forbidden outside the campaign (stricter) |
| M2 `background_allowed` output undeclared | declared in `amendment_3.cli_differences` |
| M3 series a2 refused for the wrong reason | explicit refusal: series a2 is closed |

**Re-verification (`c35c1929..dfbee540`).** All seven findings are fixed,
with no blockers and no should-fix findings. Three minor points are
disclosed and not changed:
- **A false positive is possible, but no worse than before.** An unresolved
  `com.apple.appkit.xpc.VersionsUIHelper`, cut to `(com.apple.appkit)`,
  matches a deny name by prefix and is forbidden. It runs only when someone
  opens the Versions UI, and before amendment 3 it was forbidden in that
  state anyway.
- **The command-line scan fails open.** If `ps -Ao pid=,args=` fails, no
  Claude PID is found. The scan is supplementary: Claude by path or name is
  still forbidden, and the precheck refuses while any Claude process runs.
- **The report marking gets its own review.** The marking code for the 25%
  limit is written after the freeze. It is reviewed independently before the
  analysis, against the limit fixed here.


### 10.7 Launch environment (freeze revision 2)

**Cause.** Attempt a3-2 (`v0.7.0-requalification-e75ff6a-a3-attempt2`)
ended `FAILED: BC (no verdict; conformance not established)`, chain exit 7.
- Grace, quiet period, A main and A extension completed. The gate recorded
  zero violations and zero HID resets.
- B/C stopped at its first line: `run_lifecycle_qualification.py` records
  `rustc +1.100.0 -Vv` in its provenance, by bare name. The launch PATH of
  §9.4 (`CAMP/bin` with `python3` only, then the system directories) has no
  `rustc`, so Python raised `FileNotFoundError`.
- The defect came in with §9.4 (amendment 2). It was never exercised: soaks
  stop before B/C, and the prepare script ran its dry runs with its own PATH.

**Change.** No rule, threshold, collector or gate changes.
- `CAMP/bin` holds exactly two links: `python3` and `rustc` (to the rustup
  proxy that the prepare script used; it selects `+1.100.0`, as before).
- `launch_tools.txt` lists every program the chain's Python code runs by bare
  name. A test requires the list to cover every such call in the chain's
  scripts.
- `launch_env_check.sh CAMP OUT` checks, with the launch PATH:
  - that PATH is exactly the launch PATH;
  - that every listed program resolves, and `rustc +1.100.0 -Vv` succeeds;
  - the dry run of every collector (A, B/C, R, Rmem, M_desc, M_reg) with the
    chain's arguments. `KNOTREL_GATE_DIR` is unset, so no gated child can run.
- `prepare_campaign.sh` runs the check under `env -i` with the launch PATH
  (`logs/launch-env-check.txt`). A failure stops the prepare, so no launch
  command is written.
- `precheck_terminal.sh` runs it again in the real launch environment
  (`logs/precheck-launch-env.txt`). A failure is a refusal: nothing starts and
  the directory stays usable (§9.7).
- The dry runs run `git` (rev-parse, status, diff) and `rustc -Vv` before the
  chain starts. They write no output and change no Git ref. They may refresh
  the Git index of the campaign clones and the Python bytecode cache of the
  tooling clone; both happen before the chain's Git snapshot.
- **Limits (disclosed).**
  - `launch_tools.txt` covers the chain's own Python code: literal argument
    lists, including the collectors' local helpers. It does not cover
    imported helpers, which run only `git` today, the shell chain's tools
    (all in `/usr/bin` or `/bin`), or bare-name calls inside measured Rust
    binaries. For example, the core harness records `git` output and stores
    null if it fails, so nothing crashes. The precheck's dry runs exercise
    the imported helpers that run in a dry run.
  - The A extension (`prepare_bc_qualification.py`,
    `analyze_bc_qualification.py`) has no dry run: its plan exists only at
    run time. Neither script starts a subprocess.
  - `env -i` in the prepare script sets `LANG=C.UTF-8`, the value recorded
    in the launch environment of a3-2 (`prelaunch-host.txt`).

**Accounting.** Unchanged. Attempt a3-2 counts (every directory counts,
§10.4), so 2 of 3 attempts in series a3 are used. Not counting a3-2, or
raising the cap, would be an explicit maintainer decision; none was taken.
A3-2's A outputs are not used: the attempt has no verdict.

**Review (`162348c4..e0ae6559`).** An independent reviewer found no blockers
and no should-fix findings. Five minor points:

| Finding | Disposition |
|---|---|
| M1 the side-effect claims were too strong (index refresh, bytecode cache) | wording corrected here and in `launch_env_check.sh` |
| M2 the test compared only the B/C arguments with the chain | it now compares A, B/C, R, Rmem, M_desc and M_reg |
| M3 the scanner does not cover imported helpers, shell tools or Rust binaries | disclosed above (Limits) |
| M4 the dry-run `--out` paths were not `precheck-*` in the precheck | named after the report file (`logs/precheck-launch-env-dryrun-*`, never created) |
| M5 `LANG=C.UTF-8` under `env -i` | kept: the value recorded in a3-2's launch environment; disclosed above |
