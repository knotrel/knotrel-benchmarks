# v0.7.0 re-qualification — amendment 1 proposal (declared, not approved, not frozen, not started)

**Status:** a proposal for the maintainer. Nothing in it is implemented,
frozen or run.

- **What it amends:** [`PROTOCOL.md`](PROTOCOL.md), frozen in
  [`FREEZE.json`](FREEZE.json) at tooling `9616984f`.
- **Why now:** the frozen protocol is exhausted. All 3 attempts were
  NONCONFORMING (§1), and it allows no fourth.
- **Data from the exhausted attempts** (§1.2) stays without a verdict and is
  not reused.
- **Scope:** the amendment changes only host preparation, a pre-launch
  precondition, an unmeasured soak and attempt accounting. It does not touch
  statistics, thresholds, the matrix's experiments or seeds, the analyzers,
  the conformance rule, the process classes or the granularity. Nothing in it
  depends on any measured value.
- **Review:** an independent review of a first draft has been incorporated
  (§7).

## 1. The three attempts (facts, unchanged)

All three ran the frozen tooling and matrix against candidate `e75ff6a`. The
seeds were A 130720–2, extension 130730–2, B/C 50720, R 60720 and M_reg 60721.

### 1.1 Causes

| # | Directory (`evidence/…`) | First violation | Gate stop | Cause (monitor record) |
|---|---|---|---|---|
| 1 | `v0.7.0-requalification-e75ff6a` | 2026-11-17 22:39:48.6Z, quiet period | 22:40:42Z (end of quiet period) | HID idle fell from 413 s to 0.035 s: one input event, no process violation |
| 2 | `…-attempt2` | 2026-11-18 07:41:32.8Z, A-extension | 07:41:44.8Z | `/Applications/WhatsApp.app/…/ServiceExtension.appex` (ppid 1), started by the system while WhatsApp was not running |
| 3 | `…-attempt3` | 2026-11-18 09:01:02.4Z, A-main | 09:04:32Z | `~/Library/Application Support/Google/GoogleUpdater/…/GoogleUpdater` (ppid 1). Attribution to the user LaunchAgent `com.google.GoogleUpdater.wake` (`StartInterval` 3600) is **inferred** from ppid 1, the path and its arguments |

- **Records:** in every attempt the monitor was alive throughout, the gate
  stopped at the next check, and `logs/CONFORMANCE.txt`, the Git state and the
  checksums were written.
- **Cause removal between attempts:**
  - before attempt 2, the external input devices were declared off;
  - before attempt 3, WhatsApp.app was renamed in place and renamed back
    after the attempt (maintainer-approved).
- **Disclosed under the short-lived-process limit (§3.6):** in attempt 2, a
  `top` record at 07:26:07Z (quiet period) shows a process `(disclaimer)`,
  unresolved and classified forbidden. It had already exited by the next
  sample, so it was not a violation. This is correct under the frozen rules.

### 1.2 Measurement outputs that exist (no verdict, not reused)

The frozen chain wrote raw A-main output before each stop:
- **Attempt 2:** all 108 A-main pairs, the in-chain decision analysis
  (`A/decision-analysis-main.json`) and the start of A-extension.
- **Attempt 3:** part of A-main.

[`EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256`](EXHAUSTED-ATTEMPTS-A-OUTPUTS.sha256)
records all 317 files by sha256.

- **Under the frozen §3.5** (fail fast, whole attempt) none of this has a
  verdict. It is not analysed, reused, pooled or used to choose cells.
- **What the controller saw.** It did not open these files. It read
  `logs/chain-steps.txt`, which names the two A cells that the in-chain
  decision chose for extension in attempt 2
  (`core_sparse_traversal_10k_compact-{bfs,workspace}_warmed`), and the final
  line of `logs/A-main-run.log` ("108 pairs verified").
- **What the reviewer saw.** It identified the decision file, but reported no
  values from it.
- **Effect on this amendment:** none. No list, criterion or number here
  depends on these outputs. The extension rule stays the frozen rule and is
  re-run from scratch in every attempt.

## 2. Diagnosis

The rule and the monitor did their job. What failed is host preparation
(§4). It required quitting applications, but did not cover software that the
**system starts on its own** while the owning application is not running.
Two mechanisms caused this:
1. scheduled third-party launchd jobs;
2. app extensions launched by external events, such as a push notification.

**Host drift between attempts.** Microsoft AutoUpdate (MAU) was installed on
2026-11-18 at 01:32:39Z, between attempts 1 and 2, according to the
`InstallHistory.plist` entry "Microsoft AutoUpdate", process `installer`.
- The install added `/Library/LaunchAgents/com.microsoft.update.agent.plist`
  and `/Library/LaunchDaemons/com.microsoft.autoupdate.helper.plist`.
- No Microsoft application is in `/Applications`. A `com.microsoft.teams2`
  package receipt (May 2026) and a launchd override entry
  `com.microsoft.teams2.agent` exist. The process that triggered the install
  could not be determined without root.
- **Consequence:** an inventory taken in advance can go stale, so the
  precondition (A2) runs at every launch.

### 2.1 Inventory of this Mac (2026-11-18, read-only)

| Job / item | Domain, location | Trigger | Loaded | Expected during an 80-min run |
|---|---|---|---|---|
| `com.google.GoogleUpdater.wake` | gui/501, `~/Library/LaunchAgents` | `StartInterval` 3600 | yes | launch expected (inferred cause of attempt 3) |
| `com.microsoft.EdgeUpdater.wake` | gui/501, `~/Library/LaunchAgents` | `StartInterval` 3600 | yes (last exit 78) | launch expected; not observed in attempts 2–3 |
| `com.microsoft.update.agent` (MAU) | gui/501, `/Library/LaunchAgents` (root-owned plist) | `RunAtLoad`, `StartInterval` 3600, Mach service | yes | launch expected; not observed in attempts 2–3 |
| `com.jetbrains.toolbox` | gui/501, `~/Library/LaunchAgents` | `RunAtLoad` only | yes, not running | none (fires at load only) |
| `com.google.keystone.agent`, `.xpcservice` | `~/Library/LaunchAgents` | empty plists | no | none |
| `com.docker.helper` | gui/501, registered by SMAppService (no plist) | not readable from a plist | yes, not running | unknown; on demand from Docker Desktop, which is quit |
| `com.docker.socket` | system, `/Library/LaunchDaemons` | `RunAtLoad`, no `KeepAlive` | not running | none |
| `com.docker.vmnetd`, `com.nordvpn.macos.helper` | system, `/Library/LaunchDaemons` | resident | running | already `host_baseline` |
| `com.microsoft.autoupdate.helper` | system, `/Library/LaunchDaemons` | Mach services | not running | only when MAU calls it |
| `com.vix.cron` (cron) | system | Apple-signed | loaded | runs root and user crontabs. User crontab: to be checked at launch (A2). Root crontabs are not readable without root |
| `com.google.antigravity*.ShipIt`, `com.microsoft.VSCode.ShipIt` | gui/501 | on demand from their apps | not running | none with the apps quit |
| WhatsApp `ServiceExtension.appex`, `Intents.appex` | pluginkit, `/Applications/WhatsApp.app` | push notification; Siri intents | registered | launch observed (cause of attempt 2) |

**Other mechanisms:**
- `pluginkit -m -A` lists 435 plug-ins. All are Apple's except the two
  WhatsApp ones.
- Third-party LaunchDaemons and Login Items shipped inside applications
  (Muse Hub, Gemini, NordVPN, PDFgear, Docker) exist but are not loaded.
- Background Task Management (`sfltool dumpbtm`) cannot be read without
  authentication. That is a disclosed limit.

## 3. Proposed amendments

### A1. Quiesce third-party autonomous launchers (host preparation, reversible)

**Third-party criterion, shared by A1 and A2.** A job or extension counts as
third-party unless both of these are in an Apple-controlled location of the
frozen §3.2 (rule 9):
- its plist path, when it has one;
- its program path.

Labels are never used, because a user job can call itself `com.apple.*`.

**Before the grace period,** a new script `host_quiesce.sh` runs as the user,
without root:
1. **Refuse to start** if a previous `quiesce-restore.json` anywhere under
   `evidence/` has no matching successful restore result.
2. **Write the inventory** `logs/quiesce-inventory.json` covering:
   - all loaded jobs in `gui/501`, `user/501` and `system` (read with
     `launchctl print`, no root);
   - their plist and program paths and their triggers;
   - the user crontab;
   - the third-party app extensions.
3. **Boot out** `launchctl bootout gui/501/<label>` for exactly the jobs in
   the frozen list **Q** (MATRIX `conformance.quiesce.launchd`):
   `com.google.GoogleUpdater.wake`, `com.microsoft.EdgeUpdater.wake` and
   `com.microsoft.update.agent`.
   - `com.jetbrains.toolbox` is **not** in Q: it has no autonomous trigger
     during a run, and its bootstrap at restore would start the app.
   - Bootout neither edits nor deletes any plist. It lasts until the job is
     bootstrapped again or the next login.
   - Each bootout is verified with `launchctl print`.
4. **Park the bundles** in the frozen list **P**
   (`conformance.quiesce.park_apps`): `/Applications/WhatsApp.app`.
   - Each is renamed in place to `<name>.parked-qualification`.
     `/Applications` is admin-group writable, so no password is needed.
   - `pluginkit` is then checked to confirm the extension no longer resolves
     to an existing path.
5. **Write the restore manifest** `logs/quiesce-restore.json`: every action
   and its inverse.

**Restore, strictly after the chain's records.** `host_restore.sh` runs only
after all of the following:
- the monitor has stopped;
- `logs/CONFORMANCE.txt`, the final Git state and the output checksums are
  written.

It runs on every exit path of the chain (from the trap, after `finish`). It
then:
1. bootstraps the Q jobs: `launchctl bootstrap gui/501 <plist>`;
2. renames the bundles back;
3. verifies both with `launchctl print` and a path check;
4. writes `logs/quiesce-restore-result.json`.

**Disclosed side effect:** bootstrapping `com.microsoft.update.agent` starts
Microsoft Update Assistant at once (`RunAtLoad`), after the attempt is over.

**Restore failure modes:**

| Case | Handling |
|---|---|
| A job is already loaded | Recorded as restored |
| The bundle path is now occupied (for example by a reinstall) | No overwrite; the parked bundle is left in place and reported |
| SIGKILL or power loss (no trap) | The next quiesce or prepare refuses to start (step 1) |

- A manual recovery procedure, giving the exact bootstrap and rename
  commands, is written into `logs/quiesce-restore.json` and `PROTOCOL.md` §8.
- A failed restore is reported to the maintainer and never retried silently.
- **Before freezing,** one real bootout and bootstrap round trip of each Q
  job is tested. This includes the root-owned `/Library/LaunchAgents` job from
  `gui/501`. The test is recorded in the tooling review.

**Not done:** no root-domain daemon is touched, no plist is edited or
removed, nothing is uninstalled.

**Permission.** These steps change user-level, non-persistent launchd state
and rename one application. They need the maintainer's explicit approval as
part of this amendment.

### A2. Pre-launch launcher audit (new NOT STARTED check, before the policy)

**What it checks.** A new subcommand,
`conformance_monitor.py launcher-audit --matrix M`, stops the chain as **NOT
STARTED** when, at launch:
1. any job loaded in `gui/501` or `user/501` is third-party (A1 criterion),
   is not in `allow_jobs`, and either:
   - has a timer, load, keep-alive, watch-path or launch-event trigger;
   - or its triggers cannot be determined, because it has no plist, an
     unreadable plist or an unparsable `launchctl print` (fail closed);
2. any third-party app extension resolves to an existing bundle path and is
   not in `allow_extensions`;
3. the user crontab is non-empty.

A NOT STARTED stop consumes no attempt, as with the other pre-launch checks.

**Allow-lists:**
- `allow_jobs`: on-demand jobs with no autonomous trigger. These are
  `com.docker.helper`, `com.google.antigravity-ide.ShipIt`,
  `com.google.antigravity.ShipIt` and `com.microsoft.VSCode.ShipIt`, plus a
  declared prefix rule `application.com.anthropic.claudefordesktop.`, because
  the label of the Claude desktop app's job changes.
  - `com.docker.helper` is allow-listed by name because SMAppService
    registered it and it has no plist.
- `com.jetbrains.toolbox` is allow-listed with the reason "`RunAtLoad`
  only".
- `allow_extensions`: empty.

**System domain.** Loaded third-party jobs in `system` are recorded but not
gating. Booting them out would need root. The resident ones are already in
`host_baseline`; any other process they spawn is still forbidden.

**Output:** the result is written to `logs/launcher-audit.json`.

**Not a classification change.** A2 is a precondition only. Process classes,
the deny-list and the rule order are unchanged, and anything spawned anyway is
still forbidden.

### A3. Sentinel soak before the first amended attempt (no measurement)

- **What runs.** Once, before amended attempt 1, the chain runs in soak mode
  with the same quiesce, A2 audit, grace period, policy, monitor and gate.
  - In place of the experiments there is a single campaign child that only
    sleeps for 80 minutes. It builds and runs no candidate, reference or probe
    binary.
  - 80 minutes covers more than one full cycle of every hourly timer in §2.1.
- **Records.** It writes `logs/CONFORMANCE.txt` with the prefix `SOAK`. It
  never produces data and consumes no attempt.
- **On a violation:** remove the cause, then repeat the soak. At most 2
  soaks; then the maintainer decides.
- **What a soak may change.** A change driven by a soak may only:
  - add entries to Q or P;
  - add steps to host preparation;
  - add entries to `allow_jobs` for on-demand jobs (never one with an
    autonomous trigger).

  It must **never** widen a process classification, `host_baseline` or the
  deny-list. Every such change needs a matrix amendment, a new freeze and the
  maintainer's approval.
- **Reporting.** Every soak and its outcome is reported.
- **Limit.** A soak shows only that nothing happened during its own window.
  It cannot exclude rare push-triggered events.
- **Cost and choice.** About 85 minutes of unattended host time. The soak is
  recommended, and the maintainer may drop it (§5).

### A4. Input devices (operator, host preparation)

§4 gains an explicit item:
- external keyboards, mice and trackpads are powered off or unplugged before
  the grace period;
- nothing rests on the built-in keyboard or trackpad.

The HID rule is unchanged.

### A5. Attempt accounting (fixed before any soak or attempt)

- **New series.** The amended protocol starts a new attempt series,
  `…-a1-attemptN` (`prepare_campaign.sh CAND FREEZE_A1 N`).
- **Cap.** The cap is chosen by the maintainer (§5), proposed at 3. It is
  written into `FREEZE-A1.json` before the first soak.
- **The first CONFORMING attempt is final**, whatever its statistical
  outcome. No further attempt is run to replace it.
- **No further series** after this one without a new maintainer decision.
  That decision must be recorded before any result of the new series is
  seen.
- **Seeds stay as declared.** They were fixed before any attempt ran.
  Keeping them means no seed choice can follow from any output.
- **Reporting.** The comparison report's conformance section lists:
  - all attempts of both series, with their causes;
  - the existence of the §1.2 outputs and their checksums;
  - every soak.

## 4. What stays unchanged

- **Conformance:**
  - the conformance rule (§3.1);
  - the process classes and their order;
  - the deny-list;
  - the HID tolerance, the heartbeat limits, and the grace and quiet periods;
  - whole-attempt fail-fast granularity (§3.5).
- **Experiments:**
  - identities and experiments;
  - seeds;
  - statistics, tolerances and thresholds;
  - the analyzers, probe revision and probe validity rule.
- **No inherited waivers.**
- **Controller discipline:** no tool call after launch until the chain ends.
- **Publication:** no push, tag or publication.

## 5. Maintainer decisions requested

1. **Approve A1** with Q and P as proposed. This includes permission to boot
   out and restore those jobs, and to rename WhatsApp.app and back, in every
   amended attempt and soak.
2. **Approve A2** with the proposed `allow_jobs` list and an empty
   `allow_extensions` list.
3. **Keep or drop A3**, the 80-minute soak. Recommended: keep.
4. **Attempt cap** for the new series. Proposed: 3.

## 6. Implementation, review, freeze and cost

1. **Tooling,** about 1.5 h of agent time and no measurement:
   - new files `host_quiesce.sh`, `host_restore.sh`;
   - a new `launcher-audit` subcommand;
   - a `--soak` mode in `run_final_chain.sh`, with the restore placed after
     `finish`;
   - MATRIX keys `conformance.quiesce.{launchd, park_apps, allow_jobs,
     allow_jobs_prefix, allow_extensions}`, `attempt_series: "a1"`, the soak
     settings and the attempts cap;
   - tests: third-party criterion including label spoofing, fail closed on
     unknown triggers, quiesce and restore idempotent, refusal after an
     unrestored manifest, restore ordering after the records, restore on
     every exit path, soak gating and soak that builds no binary;
   - `PROTOCOL.md` §8 listing this amendment, its differences and the manual
     recovery procedure.
2. **Bootout and bootstrap round trip** of each Q job (A1), recorded.
3. **Independent review** of the tooling diff before freezing. Findings and
   their dispositions are recorded in `TOOLING-REVIEW.md` §A1.
4. **Freeze:** `FREEZE-A1.json`, containing the tooling commit, the sha256 of
   every file, the attempt cap and the maintainer approvals, quoted.
5. **Host time:**
   - about 20 minutes of preparation per attempt;
   - one soak of about 85 minutes;
   - a chain of about 74 minutes per attempt (cap 240).

   The first amended attempt takes about 3 hours end to end; each further
   attempt about 1.6 hours.
6. **After a CONFORMING attempt:**
   - analysis with the bound analyzers;
   - the conformance cross-check;
   - a comparison report with the statistical result and the conformance of
     each cell kept separate;
   - an independent review;
   - every non-PASS surfaced to the maintainer.

## 7. Review of the first draft (dispositions)

| Finding | Disposition |
|---|---|
| B1 "no measurement exists" was false | Fixed: §1.2 lists the outputs, with checksums and what was seen; the seed justification changed |
| B2 restore could self-violate (`RunAtLoad`) | Fixed: restore runs strictly after the monitor stops and the records are written; side effect disclosed; Toolbox removed from Q |
| S1 label-based exclusion spoofable | Fixed: path-based criterion shared by A1 and A2 |
| S2 SMAppService job without plist | Fixed: fail closed unless allow-listed by name |
| S3 domains beyond `gui/501`; cron; BTM | Fixed: `user/501` gated, `system` recorded, user crontab gated; root crontabs and BTM disclosed as limits |
| S4 MAU installed between attempts | Disclosed in §2; A2 runs at every launch |
| S5 restore failure modes | Fixed: refusal on an unrestored manifest, verification, manual procedure |
| S6 soak could widen allow-lists | Fixed: soak changes restricted, never widening classifications or the baseline |
| S7 appearance of result-shopping | Fixed: first CONFORMING attempt final, cap frozen before the soak, no further series without a prior decision, full reporting; soak builds no binary |
| S8 "stopped" column | Fixed: separate first-violation and stop columns |
| M1–M5 | Fixed: one explicit Q list, separate job and extension allow-lists with a prefix rule, counts and "expected" wording, "inferred" attribution, the `(disclaimer)` sample disclosed |
