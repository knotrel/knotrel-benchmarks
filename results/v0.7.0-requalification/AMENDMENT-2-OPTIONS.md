# v0.7.0 requalification: options after soak a1-1 (draft, no decision)

Status: options for the maintainer. Nothing is changed or frozen yet. The
amendment-1 freeze (`8b931e1f`) stays in force until the maintainer decides.

## 1. Facts

- **Soak:** `evidence/v0.7.0-requalification-a1-soak1`.
  - It ran from 10:24:45Z to 11:44:45Z (4800 s).
  - Result: `SOAK NONCONFORMING: gate stop after soak`, exit 13.
- **Violation:** exactly one, in one monitor sample
  (`logs/activity-monitor.jsonl` line 20593, 11:11:01.46Z).
  - Process: `/Library/Developer/CommandLineTools/usr/bin/git`, pid 14112,
    1.5 % CPU.
  - Parent: ppid 32478, the controller Claude Code CLI itself.
  - The previous sample, 125 s earlier, was clean.
- **No human input.** HID idle never reset. It reached 4681 s at the end of
  the soak.
- **No controller action.** The controller made no tool calls between the
  launch and the completion notification.
- **Cause of the spawn is not known.**
  - The monitor records the path only, not the arguments.
  - The controller's working directory (`/Users/rt/workspace/knotrel`) is not
    a Git repository.
  - The CLI spawns Git for its own purposes, and when it does so is not under
    our control.
- **Never seen before.** No earlier qualification or requalification monitor
  log has any child of a controller or any `git` process. Earlier runs were
  shorter in their gated windows, and attempts 2 and 3 stopped early.
- **Quiesce and audit worked.** The quiesced jobs and the parked bundle
  produced no activity.
- **Restore OK.** The 3 jobs are loaded and `WhatsApp.app` is back. This was
  verified live after the chain ended.
- **Budget:**
  - soaks: 1 of `max_soaks` 2 used;
  - attempts in series a1: none run.

**Conclusion.** The host preparation of amendment 1 held. The remaining
source of activity is the controller process, which the protocol allows to
exist during the run.

## 2. Options

### Option A: launch from Terminal with Claude quit (recommended)

The controller prepares everything and ends its session. The maintainer then:
1. quits the Claude desktop app completely;
2. pastes one printed command into Terminal.app;
3. leaves the Mac.

The controller reads the results only after the chain has ended.

- **Tooling changes:**
  - `run_final_chain.sh` gets a controller mode `terminal`. The ancestry
    validation becomes `sh ← zsh (login) ← Terminal.app`, all at Apple
    paths, in place of the Claude Code CLI with its transcript.
  - A new, stricter check: no Claude process (`Claude.app`, `claude` CLI)
    exists at launch. The monitor then classifies any Claude process as
    forbidden.
  - The transcript check is replaced by that check, not dropped silently.
  - `allow_jobs_prefix` changes:
    - remove `application.com.anthropic.claudefordesktop.`;
    - add `application.com.apple.Terminal.` with program prefix
      `/System/Applications/Utilities/Terminal.app/`.
- **Pro:**
  - It removes the source, rather than tolerating it.
  - It also removes Claude.app's own background activity.
  - No rule becomes more permissive.
- **Con:**
  - The tooling change is the largest of the options: ancestry validation,
    policy, tests and review.
  - It needs a manual action by the maintainer at each launch.
  - Terminal.app becomes part of the baseline.

### Option B: keep the controller, suppress its Git activity

Configure the controller session so that the CLI should not run Git: no Git
directory reachable from it, environment and settings adjusted.

- **Pro:** small tooling change.
- **Con:**
  - The trigger is unknown, so success cannot be shown before a run. It would
    rest on one soak only.
  - The last soak could be spent on a guess.
- **Not recommended.**

### Option C: detach the chain, then exit the controller

The controller starts the chain detached from itself. The chain is then
reparented to `launchd`. After that, the controller's CLI process and the
desktop app exit.

- **Pro:** no manual typing.
- **Con:**
  - On macOS, the detached chain is hard to keep alive across the app
    quitting, because the app's process group is killed.
  - The usual workaround is a one-shot LaunchAgent. That is itself a
    third-party launchd job, which the audit would have to allow.
  - Complexity and risk are higher than with A, for a similar result.

### Option D: allow `git` children of the controller

- **Rejected by this draft.** It makes the forbidden-process rule more
  permissive. The arguments cannot be verified, since the monitor sees only
  the path.
- Listed only for completeness, because the maintainer rules exclude more
  permissive changes.

## 3. Decisions requested from the maintainer

1. **Disposition of soak a1-1.** It stays SOAK NONCONFORMING. It is reported
   in full in the comparison report.
2. **Option:** A (recommended), B, C, or none, which would stop the
   requalification.
3. **Soak budget under a new freeze.** Proposed: no reset.
   - The cap of 2 soaks counts across amendments, so 1 soak remains.
   - A soak is still required from the new freeze before attempt 1.
4. **Attempt series.** Proposed:
   - series `a2` under the new freeze, cap 3, first CONFORMING attempt final;
   - series `a1` closed with zero attempts, recorded as such.
5. **Review.** Proposed: the same review path as amendment 1. An independent
   tooling review and a verification pass, then a freeze, before the soak.

No threshold, seed, analyzer, granularity or gate rule changes in any option.
