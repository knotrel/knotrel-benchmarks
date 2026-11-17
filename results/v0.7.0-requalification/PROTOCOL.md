# Knotrel v0.7.0 re-qualification protocol

**Status: DRAFT until `FREEZE.json` exists in this directory.**
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
