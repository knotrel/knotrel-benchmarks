# Independent tooling review: v0.7.0 re-qualification (pre-freeze)

Scope: the uncommitted files of `feature/v0.7.0-qualification` listed in the brief
(RERUN-PROPOSAL.md, PROTOCOL.md, MATRIX.json, prepare_campaign.sh, run_final_chain.sh,
scripts/conformance_monitor.py, scripts/conformance_gate.py, scripts/run_v070r_collect.py,
scripts/tests/test_v070r_conformance.py), read against the frozen collectors
run_p0_aa.py, run_lifecycle_qualification.py and run_v060_qualification.py (via
run_v070_qualification.py in the first campaign).

Paths below are relative to `/Users/rt/workspace/knotrel/v0.7.0/knotrel-benchmarks`.
Abbreviations: `mon` = scripts/conformance_monitor.py, `gate` = scripts/conformance_gate.py,
`coll` = scripts/run_v070r_collect.py, `chain` = results/v0.7.0-requalification/run_final_chain.sh.

Experiments run (all read-only, scratchpad only): unit tests (17/17 pass), `sh -n` on both
scripts (pass), a matrix deep-diff, `inventory` with a scratch policy, a 25 s monitor run,
a zombie-classification probe, a `caffeinate -u` vs `HIDIdleTime` probe, timing of
`snapshot()` / `ioreg` / `pmset`, and a `git-snapshot` of the workspace.

---

## Blocking

### B1. Every controller descendant that exists at launch is baseline for the whole run, ahead of the deny-list and path rules

- **Where.** chain:64 `children = cm.descendants(procs, controller) - chain_tree - {controller}`.
  mon:217-219 returns `baseline` for any PID in `controller_children` *before* the
  deny-list (mon:225-227) and before the path rules (mon:228-232). The chain computes
  `ancestors` (chain:57-61) and never uses it.
- **Failure scenario (non-conforming run passes).** Before launch, the controlling session
  (or a subagent of it) still has a background job running: a `run_in_background` cargo
  build, a leftover `prepare_campaign.sh`, a `Monitor` until-loop, `htop`, `tail -f`, a
  `python3` server and so on. At policy time all of them become `controller_children`. They
  are classified `baseline` for the whole run, whatever their executable (deny-listed `cargo`,
  `rustc`, `git` and `python3` included). The prelaunch `check` (chain:70) passes, the monitor
  never flags them, and the run is stamped CONFORMING. Their CPU shows up only as "baseline"
  in the disclosure.
- **Contradicts the declarations.** PROTOCOL §3.2 row 4 says "its descendants present when
  the policy is written (the shells between it and the chain)". The proposal §2.1 baseline
  is "(1) the controlling CLI and its parent Claude desktop app; (2) caffeinate". PROTOCOL §6
  does not declare the broadening. (MATRIX `conformance.classes.baseline` does describe the
  broad version, so matrix and protocol disagree.)
- **Fix.** Use the `ancestors` set the chain already computes. Policy baseline =
  `controller` ∪ (`ancestors` ∩ `descendants(controller)`): the tool shell and `caffeinate`.
  If any other controller descendant exists at launch, refuse to start (exit 4 with the list),
  or classify those processes under the normal rules. Also move the deny-list check above the
  controller-children baseline, so that a deny-listed executable is never baseline. Add a
  unit test: a pre-existing `cargo` child of the controller must be forbidden, or must make
  the launch refuse.

### B2. CONTROLLER_PID is not validated

- **Where.** chain:51-55 checks only that the PID exists.
- **Failure scenario.** The operator passes the Claude desktop app's PID, or `1`, or the PID
  of the wrong Claude Code session.
  - With `1`: every process on the host at policy time becomes `controller_children`, so
    `baseline` (B1). That includes Chrome, Terminal and other sessions. Prelaunch `check`
    passes and the run can be CONFORMING with every user app running. Every new process is
    then "a tool call", so it is forbidden. The outcome depends on what starts later.
  - With the Claude.app PID: other Claude Code sessions alive at launch, and their current
    tool processes, become baseline.
- **Fix.** Require `controller in ancestors` (the chain must descend from it). Require its
  executable to match the Claude Code CLI layout
  (`…/claude-code/<ver>/…/claude.app/Contents/MacOS/claude`). Refuse otherwise. Test it.

(B2 is operator-input dependent. It is blocking because the fix is two lines, and the failure
silently voids the allow-list.)

---

## Should-fix

### S1. Apps classified `system` despite PROTOCOL §3.2 row 8 ("apps … forbidden")

- **Where.** mon:79-90 (`/System/Library/`, `/System/Cryptexes/`,
  `/System/Volumes/Preboot/Cryptexes/`), mon:228.
- **Evidence.** `/Applications/Safari.app` is a symlink to
  `../System/Cryptexes/App/System/Applications/Safari.app`. Running cryptex processes resolve
  to `/System/Volumes/Preboot/Cryptexes/App/...` and are classified `system` (scratch
  inventory: SafariLaunchAgent, PasswordBreachAgent…). Safari, and its WebKit content
  processes under `/System/Library/Frameworks/`, are therefore `system`. The same holds for
  the user-launchable apps in `/System/Library/CoreServices/` and
  `/System/Library/CoreServices/Applications/`: DiskImageMounter (the Finder double-click
  path of a disk-image mount), Installer, Archive Utility, Screen Sharing, Keychain Access,
  Ticket Viewer, Directory Utility and others.
- **Failure scenario.** An app launch with no HID input stays undetected. Examples: a
  Shortcuts or Calendar automation, a launchd job, or `open` run through a system process.
  An interactive launch is still caught by HID.
- **Fix.** Either deny-list the main executables of user-facing system apps (Safari,
  DiskImageMounter, Installer, Archive Utility, Screen Sharing, Keychain Access…), or, more
  robustly, forbid any new *foreground* application. Snapshot `lsappinfo list`
  (type="Foreground") at policy time and forbid any change. At minimum, correct row 8 and
  disclose the gap in §3.6.

### S2. HID reset rule is timed with the sample start, not the HID read: false resets under load

- **Where.** mon:308 `t = time.time()` (sample start). `ps` + classification then run
  (mon:309-310), then `ioreg` is spawned (mon:317). `hid_reset(last_idle, last_hid_t, idle, t)`
  (mon:322) uses `t`, not the read time. The tolerance is 0.25 s (mon:273). The gate likewise
  takes `now` before spawning `ioreg` (gate:146-147).
- **Failure scenario (conforming run fails).** Under the M_desc/M_reg load the monitor runs at
  normal priority. If `ps` + classification + `ioreg` spawn in one sample is ≥ 0.25 s slower
  than in the previous HID sample, the observed idle is "too small" by that amount and a reset
  is reported. The attempt is NONCONFORMING and consumes one of the 3 attempts. Measured idle
  latency is about 18 ms (`snapshot`) + 12 ms (`ioreg`). The margin is therefore only about
  8x the idle cost.
- **Fix.** Timestamp immediately after the HID read, using `time.monotonic()` for the delta
  (see M1). Better still, read `HIDIdleTime` in-process through IOKit (no process spawn).
  Raise the tolerance to about 1-2 s. Detection does not need it tight: during the campaign
  `previous_idle` is hundreds of seconds, and any input drops idle to less than the elapsed
  time.

### S3. No grace between launch and the policy / quiet-period start

- **Where.** chain:45-82. Policy, `check`, inventory, git snapshot and monitor start all
  happen within about 2-3 s of the controller's tool call.
- **Failure scenario (conforming run fails, or policy captures noise).** The operator's last
  click (for example approving the Bash permission prompt) or a trackpad touch while leaving
  falls inside the quiet period: a reset, NONCONFORMING. The controller's own turn-end
  activity also happens after the policy is written: plugin or Stop hooks, desktop-app diff
  refresh, MCP reconnects. Any process it spawns is a "new controller descendant", so
  forbidden. (No user hooks are configured in `~/.claude/settings.json`. Plugin hooks were not
  checked.)
- **Fix.** Add a declared pre-policy delay, for example `sleep 120` before chain:45, so the
  controller's turn ends and the operator leaves before the baseline is taken. Then do one
  full dry run of chain:45-94 (quiet period only) with the controller idle, to confirm zero
  violations.

### S4. Tool calls handled inside the CLI or the desktop app are not detected (undisclosed)

- **Where.** mon:212-214 detects only *new processes* under the controller. PROTOCOL §3.2
  row 2, §4.5 and §3.6.
- **Failure scenario (non-conforming run passes).** These tool calls spawn no process:
  - CLI in-process: Read/Write/Edit, WebFetch/WebSearch, Agent orchestration;
  - MCP tools served by an already-running server;
  - desktop-app tools, which run in Claude.app helpers (baseline by path, mon:221-222): the
    Browser pane, computer use, `ccd_*`.

  Browser-pane page loads run in `Claude Helper (Renderer)`, which is baseline. "The
  controlling session makes no tool call" is therefore enforced only for Bash-like tools.
- **Fix.** Disclose this in §3.6. Add a cheap objective check: record size and mtime of the
  controller session's transcript JSONL (`~/.claude/projects/<proj>/<session>.jsonl`) at policy
  time, and require them unchanged at chain end, before the completion notification.
  Optionally put a CPU ceiling on the `baseline` class.

### S5. Zombies of non-campaign processes are reported as forbidden

- **Where.** mon:112-130 (`proc_pidpath` fails on a zombie; comm is `<defunct>`, not absolute)
  and mon:223-224 + mon:248 (`pid_alive` is True for a zombie).
- **Evidence (probe).** An unreaped child gave
  `Proc(comm='<defunct>', path=None)` → `forbidden: unresolved:<defunct>`.
- **Failure scenario (conforming run fails).** Any system daemon, Claude.app helper or host
  baseline helper that leaves a child unreaped for ≥ 1 sample stops the attempt. (No zombies
  were seen in a 10 s sample, so the risk is low but nonzero over 75 min.)
- **Fix.** Read `stat=` from `ps`. Classify a `Z` process by its parent's class, or ignore it
  and log it.

### S6. Monitor continuity is checked only inside gated windows; the chain end does not check liveness

- **Where.** Heartbeat gaps are checked only in `gate.after` (gate:193-202), per child and for
  the quiet period. The chain-end check (chain:135-141) reads totals from
  `monitor-status.json` and checks neither its age nor whether the monitor PID is alive.
- **Failure scenario.** A monitor stall or crash between children goes unnoticed: during A's
  inter-session cooldowns and pre-session quiet periods, the analysis and plan steps
  (chain:101-109), or after the last M_reg child. Short-lived forbidden processes in that time
  are missed. If the monitor died after the last `after()`, the end check passes on a stale
  status file.
- **Fix.** At chain end, scan `activity-monitor.jsonl` from QSTART to now: require no `s` gap
  above 1.0 s, require the last heartbeat within 1 s, and require the monitor PID alive before
  `kill`. Add a unit test.

### S7. No `trap`: the monitor can outlive the chain

- **Where.** chain has no `trap`. The monitor loops `while running` (mon:307) and never checks
  its parent.
- **Failure scenario.** If the chain `sh` is killed (TaskStop, SIGKILL, HUP from the session),
  the monitor is reparented to launchd. It keeps sampling at 5 Hz and appending to the log
  indefinitely. CONFORMANCE.txt, git-after and checksums are not written.
- **Fix.** Add `trap 'nonconforming "chain interrupted" 16' INT TERM HUP` and a cleanup on
  EXIT that kills `$MON`. In the monitor, exit when `policy.chain_pid` is no longer alive.

### S8. "Every measured child is gated" is assumed, not verified

- **Where.** coll:59-64 gates B/C children by the heuristic "argv[0] starts with /". coll:38-49
  and coll:74-84 monkey-patch `run_p0_aa.observe_child` and `Recorder.run`. The chain stamps
  CONFORMING (chain:151) without checking that gate records exist.
- **Failure scenario.** A future or frozen-code detail bypasses the patch: a call bound before
  patching, a relative program path, or a renamed function. Children then run ungated, and the
  attempt is still CONFORMING. Totals still cover forbidden processes, but the declared
  per-child liveness, HID and power checks are silently absent.
- **Fix.** At chain end, compare the per-step count of `gate-log.jsonl` `child` records with the
  collectors' own child counts: A observations in the `pair_*.json` files, B/C `run-log.jsonl`
  lines, R/Rmem/M `run-log.json` children. Gate on argv[0] ∈ {the three B/C binaries} instead
  of "absolute path".

### S9. Remote or launchd-run activity through system binaries is invisible

- **Where.** mon:228 classifies by executable path only, without ancestry.
- **Failure scenario (non-conforming run passes).** Each of the following is entirely `system`
  and makes no HID input:
  - an SSH login: `/usr/libexec/sshd-session` → `/bin/zsh` → `/usr/bin/*`;
  - a user launchd agent or cron job running `/bin/sh` with `/usr/bin/rsync`, `zip`, `top`
    and so on;
  - Screen Sharing (`screensharingd`; it is unclear whether its injected events reset
    `HIDIdleTime`).
- **Fix.** Add `sshd-session`, `sshd`, `screensharingd`, `ScreensharingAgent`, `ARDAgent`,
  `login`, `cron` (when it has children) and `atrun` to the deny-list. Alternatively, forbid
  any shell (`/bin/{sh,bash,zsh,dash,ksh,tcsh,csh}`) outside campaign and baseline whose parent
  is not a system daemon. At minimum disclose this in §3.6, and require Remote Login and Screen
  Sharing to be off in §4.

### S10. PROTOCOL §6 omits differences from the proposal

These are not listed in §6:
- the broadened baseline: all pre-existing controller descendants, every
  `/Applications/Claude.app/` process, and baseline taking precedence over the deny-list (see
  B1);
- HID sampled once per second (proposal §2.1: "sampled with the process table");
- the proposal §3.3 step 3 `__TEXT,__text` comparison with the first campaign's builds, which
  is absent from prepare_campaign.sh and the chain;
- the analysis binding: `scripts/analyze_v070_qualification.py:24` is bound to the *first*
  campaign's MATRIX, and no requalification binding exists. Results are identical today,
  because the experiments differ only in seeds and no analyzer reads seeds. The protocol still
  says "frozen analyzers", so the binding to be used should be frozen and named.

**Fix.** List these in §6, or implement them.

---

## Minor

- **M1. Wall clock everywhere.** mon:308, gate:88/146/164 use `time.time()`. An NTP step
  forward makes a false HID reset or a heartbeat "gap". A step back can mask input. Use
  `time.monotonic()` for the HID deltas inside one process.
- **M2. Dead processes with a known deny-listed comm are dropped.** mon:248-249 drops any
  `path is None` process that has died, even when `comm` is a bare deny-listed name: a process
  launched as `git` shows comm `git` (verified with `sleep`). Classify by
  `basename(comm)` when the path is unavailable. The drop also applies to controller-tree tool
  calls (mon:212-214), although for those the zsh comm is usually absolute.
- **M3. PIDs, not (PID, start time).** mon:177, chain:64. Over about 75 min the monitor alone
  spawns about 6.5 processes/s (`ps` at 5 Hz, `ioreg` at 1 Hz), and the PID space has already
  wrapped on this host (live PIDs 14k-99k). A dead `controller_children` PID reused by a new
  process makes that process baseline. With the B1 fix the set is only long-lived ancestors,
  so this becomes theoretical. Still, store `(pid, lstart)`.
- **M4. Quiet-period CPU disclosure is wrong.** The chain:87-91 Gate never calls `before()`,
  so `cpu_before` is empty and gate:216 adds *lifetime* CPU of every process (WindowServer
  hours) into the quiet-period record.
- **M5. Locale.** mon:160-167 parses `ps` `pcpu`/`time` as floats with `.`. Under a
  decimal-comma `LC_NUMERIC` the monitor crashes on its first sample. That fails safe, but it
  is a wasted attempt. Pass `env={**os.environ, "LC_ALL": "C"}` to `ps` and `ioreg`. (It works
  in the current environment.)
- **M6. Failure exits leave no conformance record.** chain:99/101/105/107/109/118/126 exit
  after `kill $MON` with no `wait`, no CONFORMANCE.txt, no git-after and no checksums. A failed
  attempt's conformance then cannot be established afterwards.
- **M7. Inherited: a crash in the CELLS parse means "no extension".** chain:102. A failing
  `python3 -c` gives an empty `CELLS`, which is treated as "none required" (as in the first
  campaign). Check `$?`.
- **M8. "System" locations are not all Apple-update-only.** The firmlinked data-volume
  directories `/System/Library/{Caches,Assets,AssetsV2,PreinstalledAssets*,Speech}` and
  `/usr/libexec/cups` (`/usr/share/firmlinks`) are root-writable. The PROTOCOL §6 claim "can
  only be written by Apple updates" is slightly overstated. This needs root, so disclose it
  rather than fix it.
- **M9. Deny entry `python3` is ineffective for framework or Homebrew Python.**
  `proc_pidpath` gives `…/Python.app/Contents/MacOS/Python`, basename `Python` (seen in the
  scratch snapshot). Rule 8 forbids those pythons anyway, so only the `/usr/bin/python3` shim
  is affected. Harmless, but the protocol text implies more.
- **M10. Rule order in the module docstring** (mon:9-29: PID 0 as rule 2) differs from the
  code and from PROTOCOL §3.2 (controller rule first). It is cosmetic.
- **M11. MATRIX budget.** `budget.candidates_in_qualification` and
  `budget.optimization_candidates` were removed. No script reads them, and budget is declared,
  but they are information about the candidate rather than budget. Consider keeping them.
- **M12. Monitor end.** chain:142 stops the monitor before git-after and checksums. Activity
  in those last seconds is unmonitored; "to the end of the chain" is slightly overstated.

---

## Test adequacy (scripts/tests/test_v070r_conformance.py)

Untested paths that matter:
- `run_monitor` itself: log and status writing, the HID integration with the
  timestamp-vs-read latency (S2), the status atomic write, SIGTERM stop.
- `Gate.wait_for_heartbeat`, and `_read_log` partial-line and offset handling across several
  `after()` calls in one process (child 2 after child 1). The first-`after()`-from-offset-0
  behaviour is also untested.
- CPU accounting values. The test only asserts that the key `"system"` exists (test:188).
  Nothing tests new processes, class changes, exited processes, or the quiet-period case (M4).
- Policy construction (chain:47-68): it is inline in sh and untested. Missing tests: a
  pre-existing controller child (B1) and a wrong controller PID (B2).
- Zombie / `<defunct>` (S5); dead process with a deny-listed comm (M2); PID reuse (M3).
- A and R/M wrappers: only B/C gating is tested (test:259-270). No test checks that `_a`
  and `_recorder` actually gate, or that `GateStop` propagates through
  `run_p0_aa.execute_pilot` (handlers at run_p0_aa.py:3181-3186 re-raise) and
  `Recorder.run`.
- Chain behaviour: exit paths, monitor kill, quiet-period failure, Git diff stop. A
  stub-collector harness run with a fake `KNOTREL_GATE_DIR` would cover most of this.
- Matrix test (test:274-290) is one-directional:
  - it iterates only the first matrix's experiment keys, so a key *added* to a new experiment
    (for example `M_desc.server_processes`) or a removed or added experiment goes unnoticed;
  - it compares only selected `rules` keys, so the `rules.R` and `no_waiver_inheritance` edits
    and any new rules key go unchecked;
  - it does not check top-level sections (`budget`, `host_conditions`, `invalidation`,
    `references`, `schema`);
  - prepare_campaign.sh is not diffed against the first campaign's script.

  Replace it with a full deep diff against an explicit allow-list of changed paths.

---

## Verified correct

- **Matrix deep-diff.** The only differences from results/v0.7.0-qualification/MATRIX.json
  are the declared ones:
  - A session seeds 130720-2 and extension seeds 130730-2;
  - order seeds B/C 50720, R 60720, M_reg 60721;
  - `host_conditions` (4 strings) and the new `conformance` section;
  - `budget`: estimates, `attempts_cap`, `basis`, and two removed info keys (M11);
  - `invalidation.conformance`; `references.first_campaign` and `references.proposal`;
  - `schema`;
  - wording: `rules.R` ("order seed 60500" → `experiments.R.order_seed`),
    `no_waiver_inheritance` (appended sentence), and `experiments.M_desc.server_processes`
    (38 servers).

  Cells, pairs, warmups, windows, tolerances and the validity rule are unchanged.
- **Seeds actually used.** A main 130720-2 (prepare:107); A extension 130730-2 (chain:105);
  B/C `--order-seed 50720` (chain:117); R/M_reg `spec["order_seed"]` from the requalification
  matrix (run_v060_qualification.py:163,228 with coll:76).
- **prepare_campaign.sh diff.** Exactly as declared: header comment; ATTEMPT argument and
  `-attemptN` suffix; directory name; A main seeds and checkpoint; and an explicit
  `--source-manifest` (proposal §3.2 row "prepare_campaign.sh"). The manifest path has sha256
  `95dfdabd…`, identical to the first campaign's `pilot_design.source_manifest.sha256`. The
  chain's extension step also passes `--source-manifest` (chain:105).
- **R/Rmem/M collector.** It is the same code path as the first campaign: run_v070_qualification.py
  was itself a wrapper around run_v060_qualification.py. The MATRIX and FREEZE binding move to
  requalification (coll:76; run_v060_qualification.py:243-245 requires
  requalification/FREEZE.json).
- **GateStop cannot be swallowed.**
  - `before()` raises outside `run()` (gate:244-248), so `observe_child`'s own
    `except (KeyboardInterrupt, SystemExit)` (run_p0_aa.py:2334) never sees it.
  - `execute_pilot` re-raises SystemExit (run_p0_aa.py:3181-3186).
  - B/C and Recorder have no broad handlers.
  - The stop file is written before raising (gate:158), and the chain checks the file
    regardless of exit status (chain:42, 99, 107, 118, 126).
- **Every measured child of A, B/C, R, Rmem, M_desc and M_reg passes through the patched
  call.** This includes warmup pairs (run_v060_qualification.py:146-150) and the 2 open-loop
  M_desc servers (:212).
  - M_desc/M_reg servers are children of the probe, so campaign by ancestry, and are reaped
    (tools/contention-probe/src/main.rs:1053-1054).
  - A HTTP servers are reaped by `measure_e2e` (knotrel e75ff6a
    `crates/knotrel-server/examples/measure_e2e.rs`:383-384, 430-431, 524-525) and killpg'd by
    `observe_child`.
- **Frozen collectors' helpers are `campaign` by ancestry.** These are `pmset`, `sysctl`, `ps`,
  `pgrep`, `/usr/bin/time`, `git rev-parse` / `git status`, and `rustc -Vv`. A unit test covers
  `git` (test:45,64).
- **caffeinate.** Under `caffeinate -dimsu sh run_final_chain.sh`, caffeinate is the chain's
  parent and a pre-existing controller descendant, so it is baseline. It is not deny-listed, and
  `/usr/bin/caffeinate` would be `system` anyway.
- **`caffeinate -u` does not reset `HIDIdleTime`.** Probe: 64.15 → 64.68 → 65.72 → 68.27 s
  across a 3 s `-u` assertion. No spurious HID resets come from the chain's own wrapper.
- **Status-file write is atomic** (mon:283-286, same-directory `os.replace`). The log row is
  written and line-flushed *before* the status update (mon:315 then mon:334). So when
  `wait_for_heartbeat` sees `t >= end`, the matching `s` row is already readable.
- **Partial lines.** `_read_log` keeps only complete lines and advances a byte offset
  (gate:178-179). JSON is ASCII (`ensure_ascii`), so byte and char offsets agree.
- **Very short children (< 0.2 s)** do not fail spuriously. The gap list is
  `[start, end]` (gate:199). The "beat at start" condition is met by the post-end heartbeat
  that `wait_for_heartbeat` waits for (≤ about 0.25 s at idle). Heartbeats consumed by the
  previous `after()` are not needed.
- **Reading from offset 0 in each new collector process** only adds old rows. Violations are
  windowed (gate:203-204). Resets are not windowed, but any earlier reset already made the
  totals non-zero. There is no spurious effect. The cost is one parse of a log of about 5 MB.
- **The Git-state comparison is sound against the collectors' own git use.** Only `rev-parse`,
  `status --porcelain`, `diff`, `ls-files` and `diff --name-only` run, and none touches
  `FETCH_HEAD` or remote reflogs. There is no global `core.fsmonitor` or `maintenance` config.
  A `git-snapshot` of the workspace takes about 2.3 s and covers 48 clones, including the
  main `knotrel` and `knotrel-benchmarks` (worktrees share their main `.git`). Its scope is
  fetch activity only, as disclosed in §3.3.
- **sh portability.** `sh -n` passes for both scripts. The chain uses only POSIX constructs:
  `$(...)`, `[ ]`, functions, `case`, `wait`, and BSD-compatible `find -print0 | xargs -0`,
  `cmp -s` and `date -u +fmt`.
- **Quiet period.** It is checked as a child over [QSTART, end] with gap, violation and reset
  rules (chain:83-93). Failure goes to `nonconforming`, which kills the monitor.
- **Cost of the monitor primitives on this host:** `snapshot()` about 18 ms, `ioreg` about
  12 ms, two `pmset` calls about 13 ms.
- **Controller idle behaviour.** A 25 s monitor run with this session's CLI as controller
  showed no new controller descendants. The first campaign's git-matching monitor also saw no
  `git` during 60 min with the controller idle. Neither the CLI nor the desktop app appears to
  spawn `git` while idle. Turn-end behaviour is untested (S3).
- **Classification of the current host matches the intent for:** Chrome (including the
  code-sign-clone path under `/private/var/folders`), Docker Desktop, Gemini, Sublime,
  WhatsApp appex, Calendar, System Settings, Terminal, open/save panel services, GnuPG agents,
  htop, and the other Claude Code session's CLI. All were `forbidden`, with 0 unresolved.

---

# Verification pass (after the coordinator's fixes)

Re-read in full: the rewritten `conformance_monitor.py` (517 lines),
`conformance_gate.py` (318), `run_v070r_collect.py` (115),
`analyze_v070r_qualification.py` (28), `run_final_chain.sh` (156), the prepare diff,
PROTOCOL §3-§7, and the MATRIX deep-diff.

Experiments (read-only, scratchpad only):
- **Tests and syntax.** 29/29 unit tests pass; `sh -n` passes.
- **`policy` on the real host.** The controller PID tried is the Claude Code CLI that is the
  parent of my tool shell.
  - Controller = that CLI (32478): accepted. `controller_children` was empty because there the
    chain is the tool shell itself.
  - Refused: the Claude.app PID ("not a Claude Code CLI"), PID 1, the other session's CLI and
    the chain itself ("not an ancestor").
- **lsappinfo parsing.** `foreground_pids()` on the real host found 8 Foreground apps; only
  Finder and Claude.app were allowed.
  - Chrome resolves through its code-sign-clone path and is forbidden.
  - The `pid = N !signalled type=...` variant is matched by the regex.
  - `lsappinfo list` takes about 21 ms.
- **20 s run of the new monitor.** 96 samples, maximum gap 0.211 s, 20 HID reads, 0 resets,
  with foreground apps flagged.
- **`chain_gone` exit.** With `chain_pid` set to a 3 s `sleep`, the monitor stopped after 3 s
  with reason `chain_gone`.
- **Trap behaviour under /bin/sh (bash 3.2 in sh mode)**, tested with a replica of the chain's
  trap structure:
  - `nonconforming` inside `… <<PY || nonconforming` runs `finish` with the right RESULT and
    exit code;
  - the normal end runs `finish` with exit code 0;
  - SIGTERM runs `finish` with RESULT "signal" and exit code 20;
  - the background job is killed in all three cases.
- **Controller transcript behaviour.** The coordinator's main transcript JSONL was unchanged for
  more than 5 min while this subagent was working (mtime 22:59:53, size 8629284).
  - In another session, a 70-min idle gap had no transcript writes at all.
  - Stop hooks in this setup are in-process `callback`s. They start no process, but they append
    a `stop_hook_summary` at turn end.

## Verdicts on the earlier findings

| Item | Fixed? | Fix correct? |
|---|---|---|
| B1 | yes | yes. `build_policy` (mon:259-282) allows only the chain's ancestors below the controller. Any other live non-zombie descendant refuses the launch. The deny-list (mon:305) and foreground rule (mon:307) now precede the baseline (mon:309). |
| B2 | yes | yes. The controller must be in `lineage[1:]` and match `CONTROLLER_CLI` (mon:269-275). Verified on the host. |
| S1 | yes | yes. Rule 6 (mon:307) with `foreground_pids` (mon:190-203) parses real output correctly. Residual: see N5. |
| S2 | yes | yes. `hid_read` timestamps the read with a monotonic midpoint (mon:366-370); tolerance 1.0 s; the gate uses the same tuple (gate:148-154). |
| S3 | yes | mostly. 120 s grace before the policy (chain:59-61). Turn completion is not verified: see N2. |
| S4 | partly | The transcript check exists (chain:37, 71, 152-154). Three new defects: N1 (subagents invisible), N2 (end-only and no stability check), N3 (transcript not bound to the controller). |
| S5 | yes | yes, apart from minor N6 (ordering against rule 3). |
| S6 | yes | yes. `full_log_check` (gate:235-255) checks the whole log from QSTART, monitor liveness and freshness, totals and HID failures, run while the monitor is still running (chain:134). See minor N7. |
| S7 | yes | yes. The `finish` EXIT trap and the signal trap (chain:41-50) were verified under /bin/sh. The monitor exits on `chain_gone` (mon:407-409), verified. See minor N8. |
| S8 | yes | yes. B/C gates exactly the realpaths of `--core`, `--core-count` and `--http` (coll:58-71). `verify_gating` compares conforming gate records per prefix with the collectors' own counts (gate:258-291). The label prefixes `A`, `BC`, `r`, `rmem`, `mdesc` and `mreg` match on both sides. |
| S9 | yes | yes, as a deny-list addition plus disclosure (§3.6, §4.3). `com.apple.atrun` is not loaded on this host, so `atrun` will not fire spuriously. |
| S10 | yes | yes. §6 lists the differences. `analyze_v070r_qualification.py` binds both `first.MATRIX` and `first.frozen.MATRIX`. The `__TEXT,__text` comparison in prepare cannot abort under `set -e`: each pipeline ends in `cut`. |
| M1 | yes | yes |
| M2 | yes | yes. Rule 5 uses the `comm` basename when the path is unavailable (mon:305), and `forbidden()` keeps dead deny-listed `comm`s (mon:341). |
| M3 | disclosed | acceptable: the baseline PIDs are now only long-lived ancestors. |
| M4 | yes | yes (gate:212-224) |
| M5 | yes | yes (`C_ENV` for `ps`, `ioreg`, `lsappinfo` and `pmset`) |
| M6 | yes | yes. Every exit after chain:49 writes CONFORMANCE.txt, git-after and checksums. (Exits at chain:30-33 happen before the trap, before anything has started.) |
| M7 | yes | yes (chain:100) |
| M8, M9 | disclosed | acceptable |
| M10 | yes | yes |
| M11 | yes | yes (budget keys restored) |
| M12 | yes | yes (chain:133 runs before the monitor stops) |

## New or remaining defects

### N1 (should-fix). The transcript check misses subagents

- **Where.** chain:37 stats only `$TRANSCRIPT`.
- **Evidence.** Subagent activity is written to `<session>/subagents/agent-*.jsonl`. The main
  JSONL did not change during this whole subagent run.
- **Failure scenario (non-conforming run passes).** A background subagent of the controller is
  alive at policy time. It is in a model call or in-process tool use, so it has no process and
  `build_policy` does not refuse. It then does Read/Write/Edit/WebFetch for the whole attempt.
  None of this reaches the main transcript, and the run is CONFORMING.
- **Fix.** Make `transcript_state` cover the session directory recursively: `$TRANSCRIPT` plus
  `${TRANSCRIPT%.jsonl}/`, taking the largest mtime and the total size or a file-list digest.
  Refuse the launch if any subagent file changed during the grace period.

### N2 (should-fix). The transcript is checked only at chain end, and its stability at launch is never verified

- **Where.** `TRANSCRIPT_BEFORE` is taken once (chain:71) and compared once (chain:154).
- **Failure scenario (attempt wasted).** The controller's turn does not end within 120 s, for
  example a long final message, or a stop-hook or title write that arrives late. The transcript
  then changes after `TRANSCRIPT_BEFORE`. This is found only after about 75 min, and one of the
  3 attempts is consumed.
- **Contradicts the protocol.** It also breaks fail-fast (§3.5): a mid-run tool call by the
  controller is caught only at the end.
- **Fix.**
  - Before the policy, require the transcript state to be unchanged across at least 30 s, for
    example by sampling at grace − 30 s and at grace end. Otherwise refuse (NOT STARTED).
  - Compare the transcript state in `gate_check` after every step, and optionally in `before()`.

### N3 (should-fix). The transcript is not bound to the controller

- **Where.** chain:21 and chain:58 only test `-f "$TRANSCRIPT"`.
- **Failure scenario (non-conforming run passes).** A wrong or stale file is passed: another
  session's transcript, an old one, or any static file. The check is then vacuous.
- **Fix.** Require all of these:
  - the path lies under `~/.claude/projects/`;
  - its mtime is within a few minutes of chain start, since the launching tool call itself
    writes it;
  - its tail contains the `run_final_chain.sh` launch command with this `$CAMP`.

  Record the session id in the logs.

### N4 (minor). HID during the grace period is not enforced

PROTOCOL §3.3 says "the last input is at least the grace period earlier", but nothing enforces
it. Make `policy` record `hid_idle_seconds()`, and refuse if it is below, say, 60 s. That would
also catch an operator still at the Mac.

### N5 (minor). Foreground-rule robustness

- `foreground_pids` (mon:190-203) returns `{}` silently if `lsappinfo` fails, which disables
  rule 6 with no record. Count it like `hid_failures`.
- `path` is not reset per record. A record with `executable path=[ NULL ]` inherits the
  previous app's path; that only matters when `proc_pidpath` also fails.
- System-launched foreground apps (Problem Reporter after a crash, Captive Network Assistant)
  would stop the attempt. They are rare, and failing conservatively is acceptable, but
  disclose it.

### N6 (minor). A zombie of a new controller tool call is classified as baseline

- **Where.** Rule 2 (zombie takes its parent's class, mon:294-298) runs before rule 3
  (mon:299-301). A just-exited, unreaped tool-call child of the CLI therefore gets the
  controller's class, baseline.
- **Fix.** Evaluate rule 3 before rule 2. The process is still a new controller descendant.

### N7 (minor). `full_log_check` can crash on a partial last line

- **Where.** gate:240-243 parses every line that looks like `{…}`.
- **Failure scenario.** A torn final line ending in `}` raises `ValueError`. The end check exits
  1 and the chain reports NONCONFORMING (code 14) spuriously. This is unlikely with line-buffered
  writes of about 1 KB.
- **Fix.** Parse only up to the last `\n`, as `_read_log` does, or catch `ValueError` on the
  final line.

### N8 (minor). Signal handling

- **Deferred trap.** Under /bin/sh a SIGTERM sent only to the chain is deferred until the
  current foreground collector finishes; verified, the trap ran after `sleep` completed. During
  A that can mean up to about 27 min of measurement continuing. The monitor is still alive, so
  the gates pass meanwhile. The outcome is still NONCONFORMING, so there is no false pass.
  Option: run collectors in the background with `wait`, so the trap fires at once, and kill
  the process group in `finish`.
- **Unrecorded GateStop.** The undeclared-program `GateStop` (coll:69-70) is raised without
  writing `gate-stop.json`. The chain records FAILED, not NONCONFORMING. That is acceptable, but
  route it through `Gate._stop` for a uniform record.

## Remaining blocking / should-fix

- **Blocking:** none.
- **Should-fix:** N1, N2 and N3, all in the controller-transcript check. The rest of the earlier
  findings are fixed correctly.
