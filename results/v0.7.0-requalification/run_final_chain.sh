#!/bin/sh
# Runs the frozen v0.7.0 re-qualification in one chain: grace period, policy, quiet period,
# then A (main, extension if required), B/C, R, Rmem, M_desc, M_reg. Every measured child is
# gated (scripts/conformance_gate.py) by the allow-list monitor (scripts/conformance_monitor.py).
#
# Amendment 2 (PROTOCOL.md section 9): the maintainer runs CAMP/LAUNCH-COMMAND.txt (written by
# the prepare script: precheck_terminal.sh, then this chain) in the only window of Terminal.app,
# with Claude (desktop app and Claude Code CLI) quit completely:
#   /usr/bin/caffeinate -dimsu /bin/sh run_final_chain.sh CAMP CAND_SHA [--soak] < /dev/null
# (caffeinate execs the chain in its own PID and asserts from a caffeinate child: PROTOCOL.md 9.11)
#   CAMP            campaign directory made by prepare_campaign.sh (prepare_soak.sh for --soak)
#   CAND_SHA        knotrel candidate commit ("-" with --soak)
#   --soak          amendment 1, A3: run everything except the experiments; one gated campaign
#                   child sleeps conformance.soak.duration_s. No binary is built or run; no data.
# The controller is Terminal.app (scripts/conformance_monitor.py, controller kind "terminal"): the
# policy refuses the launch while any Claude process runs, while Terminal has another window or
# tab, or if the chain does not descend from Terminal.app. ~/.claude/projects must not change
# during the attempt (it replaces the transcript check of the Claude Code controller).
#
# Amendment 1 (PROTOCOL.md section 8): before the grace period, third-party autonomous
# launchers are quiesced (scripts/launcher_audit.py quiesce, A1) and audited (A2, again just
# before the policy); a failed quiesce or audit is NOT STARTED. On every exit path, after the
# monitor has stopped and every record is written, the quiesce is restored and verified
# (logs/quiesce-restore-result.json).
#
# Conformance rule (MATRIX.json "conformance"): nothing outside the allow-list runs and no
# user input occurs from the start of the quiet period to the end of the chain. Any failed
# check stops the chain; the attempt is then NONCONFORMING (chain-steps.txt and
# logs/CONFORMANCE.txt). Every exit path writes logs/CONFORMANCE.txt, the final Git state and
# output checksums.
set -u
# Arguments: the soak flag must match the directory and the candidate (refused before anything runs).
case $# in 2|3) ;; *) echo "usage: run_final_chain.sh CAMP CAND_SHA [--soak]  (amendment 2: from Terminal.app, Claude quit)" >&2; exit 2;; esac
CAMP=${1%/}
CAND=$2
SOAK=""
if [ $# -eq 3 ]; then
  [ "$3" = "--soak" ] || { echo "unknown argument: $3" >&2; exit 2; }
  SOAK=1
fi
case "$(basename "$CAMP")" in *-soak[1-9]) ISSOAKDIR=1;; *) ISSOAKDIR="";; esac
if [ -n "$SOAK" ]; then
  { [ "$CAND" = "-" ] && [ -n "$ISSOAKDIR" ]; } || { echo "--soak needs CAND '-' and a *-soakN directory" >&2; exit 2; }
else
  { [ -z "$ISSOAKDIR" ] && echo "$CAND" | grep -Eq '^[0-9a-f]{40}$'; } || { echo "an attempt needs a full candidate SHA and a non-soak directory" >&2; exit 2; }
  case "$(basename "$CAMP")" in *-"$(echo "$CAND" | cut -c1-7)"|*-"$(echo "$CAND" | cut -c1-7)"-*) ;; *) echo "CAND $CAND does not match the campaign directory" >&2; exit 2;; esac
fi
P=""; [ -n "$SOAK" ] && P="SOAK "
B=$CAMP/src/cand/knotrel-benchmarks
T=$CAMP/targets
L=$CAMP/logs
A=$CAMP/A
G=$CAMP/gate
MATRIX=$B/results/v0.7.0-requalification/MATRIX.json
export LIFECYCLE_QUALIFICATION_ROOTS=/Users/rt/workspace/knotrel/evidence
export KNOTREL_GATE_DIR=$G
cd "$B" || exit 2
for f in "$A/raw-main" "$CAMP/BC" "$CAMP/R" "$CAMP/Rmem" "$CAMP/Mdesc" "$CAMP/Mreg" "$G" "$L/quiesce-restore.json"; do
  if [ -e "$f" ]; then echo "refusing to relaunch: $f exists" >&2; exit 3; fi
done
mkdir -p "$G"
stamp() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >> "$L/chain-steps.txt"; }
conf() { python3 -c "import json;print(json.load(open('$MATRIX'))['conformance']['$1'])"; }
CLAUDE_STATE_DIR=$HOME/.claude/projects
# Fails closed: an unreadable tree gives TREE-STATE-FAILED, never an empty (always equal) state.
session_state() { _S=$(python3 scripts/conformance_monitor.py tree-state "$CLAUDE_STATE_DIR" 2>/dev/null) && [ -n "$_S" ] && echo "$_S" || echo "TREE-STATE-FAILED"; }
tty_note() { { echo "$1"; } > /dev/tty 2>/dev/null || true; }
policy() { python3 scripts/conformance_monitor.py policy --chain $$ --controller-kind terminal --matrix "$MATRIX" --out "$1"; }

MON=""
RESULT="${P}NONCONFORMING: chain ended before its last step"
finish() {  # runs on every exit: stop the monitor, record conformance, Git state and checksums,
            # then (strictly after all records) restore the quiesced launchers and apps
  trap - EXIT
  trap '' INT TERM HUP  # a second signal must not skip the records or the restore
  if [ -n "$MON" ]; then kill "$MON" 2>/dev/null; wait "$MON" 2>/dev/null; MON=""; fi
  [ -e "$L/git-after.json" ] || python3 scripts/conformance_monitor.py git-snapshot /Users/rt/workspace/knotrel > "$L/git-after.json" 2>/dev/null
  { echo "$RESULT"; cat "$G/gate-stop.json" 2>/dev/null; } > "$L/CONFORMANCE.txt"
  [ -e "$G/activity-monitor.jsonl" ] && cp "$G/activity-monitor.jsonl" "$L/activity-monitor.jsonl"
  ( cd "$CAMP" && find A BC R Rmem Mdesc Mreg gate -type f -print0 2>/dev/null | xargs -0 shasum -a 256 > logs/outputs-sha256.txt )
  RESTORE_FAILED=""
  if [ -e "$L/quiesce-restore.json" ]; then
    if python3 scripts/launcher_audit.py restore --camp "$CAMP" > "$L/quiesce-restore.log" 2>&1; then
      stamp RESTORE "ok (logs/quiesce-restore-result.json)"
      echo "RESTORE OK (logs/quiesce-restore-result.json)"
    else
      RESTORE_FAILED=1
      stamp RESTORE "FAILED (logs/quiesce-restore-result.json; manual procedure in PROTOCOL.md section 8.5)"
      echo "RESTORE FAILED: see logs/quiesce-restore-result.json and PROTOCOL.md section 8.5"
    fi
  fi
  echo "$RESULT"
  if [ -n "$RESTORE_FAILED" ]; then exit 21; fi
}
trap finish EXIT
trap 'RESULT="${P}NONCONFORMING: chain interrupted by a signal"; exit 20' INT TERM HUP
nonconforming() { RESULT="${P}NONCONFORMING: $1"; stamp NONCONFORMING "$1"; exit "$2"; }
failed() { RESULT="${P}FAILED: $1 (no verdict; conformance not established)"; stamp "$1" FAILED; exit "$2"; }
notstarted() { RESULT="${P}NOT STARTED: $1"; stamp NOT-STARTED "$1"; exit 4; }
SESSION_BEFORE=""
gate_check() {
  if [ -e "$G/gate-stop.json" ]; then nonconforming "gate stop after $1" 13; fi
  if [ "$(session_state)" != "$SESSION_BEFORE" ]; then  # SESSION_BEFORE is a validated state when the monitor runs
    session_state > "$L/session-after.json"
    nonconforming "Claude session files changed under ~/.claude/projects (after $1)" 16
  fi
}

# --- Prelaunch: host state, grace period, policy, allow-list check, Git state ---
{ date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -2; pmset -g therm; uptime
  echo "python3: $(command -v python3) $(python3 -V 2>&1)"; echo "PATH=$PATH"; echo "environment names: $(env | cut -d= -f1 | sort | tr '\n' ' ')"; env | /usr/bin/grep -E '^(PYTHON|DYLD_|RUST|CARGO|LANG=|LC_)' | sed -E 's/^([^=]*(TOKEN|SECRET|PASSWORD|KEY)[^=]*)=.*/\1=<redacted>/' | sort; } > "$L/prelaunch-host.txt"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) RESULT="${P}NOT STARTED: not on AC power"; exit 4;; esac
# Amendment 2: the controller is Terminal.app; check it (and that Claude is quit) before anything changes on the host.
[ "$(conf controller_kind)" = terminal ] || { RESULT="${P}NOT STARTED: MATRIX conformance.controller_kind is not terminal"; exit 4; }
policy "$L/policy-prequiesce.json" 2> "$L/policy-error.txt" || { RESULT="${P}NOT STARTED: controller check refused ($(cat "$L/policy-error.txt"))"; exit 4; }
# Amendment 1, A1/A2: quiesce (refuses while any earlier manifest is unrestored), then audit.
python3 scripts/launcher_audit.py quiesce --matrix "$MATRIX" --camp "$CAMP" > "$L/quiesce.log" 2>&1 || notstarted "launcher quiesce failed (logs/quiesce.log)"
python3 scripts/launcher_audit.py audit --matrix "$MATRIX" --out "$L/launcher-audit-pregrace.json" 2> "$L/launcher-audit-pregrace.txt" || notstarted "launcher audit failed before the grace period (logs/launcher-audit-pregrace.txt)"
GRACE=$(conf grace_period_s)
STABLE=$(conf session_stable_s)
MIN_IDLE=$(conf min_hid_idle_at_policy_s)
stamp GRACE "start ${GRACE}s (operator leaves the Mac; Claude is quit)"
tty_note "Grace period ${GRACE}s: leave the Mac now. Do not reopen Claude until this window prints the result."
sleep "$GRACE"
S1=$(session_state); sleep "$STABLE"; S2=$(session_state)
[ "$S1" != TREE-STATE-FAILED ] && [ "$S2" != TREE-STATE-FAILED ] || { RESULT="${P}NOT STARTED: ~/.claude/projects unreadable"; exit 4; }
[ "$S1" = "$S2" ] || { RESULT="${P}NOT STARTED: Claude session files still changing after the grace period"; exit 4; }
IDLE=$(python3 scripts/conformance_monitor.py hid-idle) || { RESULT="${P}NOT STARTED: HID idle time unreadable"; exit 4; }
python3 -c "import sys; sys.exit(0 if float('$IDLE') >= float('$MIN_IDLE') else 1)" || { RESULT="${P}NOT STARTED: user input ${IDLE}s ago (minimum ${MIN_IDLE}s)"; exit 4; }
python3 scripts/launcher_audit.py audit --matrix "$MATRIX" --out "$L/launcher-audit.json" 2> "$L/launcher-audit.txt" || notstarted "launcher audit failed (logs/launcher-audit.txt)"
if ! policy "$G/policy.json" 2> "$L/policy-error.txt"; then
  RESULT="${P}NOT STARTED: policy refused ($(cat "$L/policy-error.txt"))"; exit 4
fi
cp "$G/policy.json" "$L/policy.json"
python3 scripts/conformance_monitor.py inventory --policy "$G/policy.json" > "$L/prelaunch-inventory.txt"
if ! python3 scripts/conformance_monitor.py check --policy "$G/policy.json" > "$L/prelaunch-check.txt"; then
  RESULT="${P}NOT STARTED: forbidden processes present (logs/prelaunch-check.txt)"; exit 4
fi
python3 scripts/conformance_monitor.py git-snapshot /Users/rt/workspace/knotrel > "$L/git-before.json"
SESSION_BEFORE=$S2
echo "$SESSION_BEFORE" > "$L/session-before.json"

# --- Monitor and quiet period ---
python3 scripts/conformance_monitor.py monitor --policy "$G/policy.json" --out "$G/activity-monitor.jsonl" --status "$G/monitor-status.json" &
MON=$!
QUIET=$(conf quiet_period_s)
QSTART=$(python3 -c "import time;print(time.time())")
stamp QUIET "start ${QUIET}s"
sleep "$QUIET"
python3 - "$G" "$QSTART" <<'PY' || nonconforming "quiet period" 12
import pathlib, sys, time
sys.path.insert(0, "scripts")
import conformance_gate as cg
g = cg.Gate(pathlib.Path(sys.argv[1]))
start, end = float(sys.argv[2]), time.time()
g.wait_for_heartbeat(end)
if not g.after("quiet-period", start, end):
    raise SystemExit(1)
PY
gate_check quiet-period
stamp QUIET end

if [ -n "$SOAK" ]; then
  # --- Amendment 1, A3: soak. One gated campaign child that only sleeps; no binary, no data. ---
  DUR=$(python3 -c "import json;print(json.load(open('$MATRIX'))['conformance']['soak']['duration_s'])")
  stamp SOAK "start ${DUR}s"
  python3 - "$DUR" <<'PY' > "$L/soak.log" 2>&1
import subprocess, sys
sys.path.insert(0, "scripts")
import conformance_gate as cg
cg.gated("soak:sleep", lambda: subprocess.run(["/bin/sleep", sys.argv[1]], check=True))
PY
  RC=$?; gate_check soak; [ $RC -eq 0 ] || failed soak 5
  stamp SOAK end
  python3 scripts/conformance_monitor.py git-snapshot /Users/rt/workspace/knotrel > "$L/git-after.json"
  python3 - "$CAMP" "$G" "$QSTART" <<'PY' > "$L/end-checks.txt" 2>&1 || nonconforming "end-of-soak checks (logs/end-checks.txt)" 14
import pathlib, sys, time
sys.path.insert(0, "scripts")
import conformance_gate as cg
camp, gate_dir, start = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), float(sys.argv[3])
g = cg.Gate(gate_dir)
reasons = g.full_log_check(start, time.time())
gated, collected = cg.gated_counts(gate_dir), cg.collector_counts(camp)
if gated != {"soak": 1}:
    reasons.append(f"soak: expected exactly one gated soak child, got {gated}")
if any(collected.values()):
    reasons.append(f"soak: measurement outputs present {collected}")
print({"gated": gated, "collected": collected, "reasons": reasons})
if reasons:
    raise SystemExit(1)
PY
  if ! cmp -s "$L/git-before.json" "$L/git-after.json"; then
    diff "$L/git-before.json" "$L/git-after.json" > "$L/git-state.diff"
    nonconforming "Git state changed during the soak (logs/git-state.diff)" 15
  fi
  session_state > "$L/session-after.json"
  gate_check soak-end
  RESULT="SOAK CONFORMING: every gate check passed; monitor alive with no gap, zero totals; one gated sleep child; Git state and Claude session files unchanged (no data)"
  stamp CHAIN "soak complete"
  exit 0
fi

# --- A ---
stamp A-main start
python3 scripts/run_v070r_collect.py a --manifest "$A/plan/manifest.json" --schedule "$A/plan/schedule.json" --execute "$A/raw-main" > "$L/A-main-run.log" 2>&1
RC=$?; gate_check A-main; [ $RC -eq 0 ] || failed A-main 5
stamp A-main end
python3 scripts/analyze_bc_qualification.py --main "$A/raw-main" --rules v0.4.0 --output "$A/decision-analysis-main.json" > "$L/A-analysis-main.log" 2>&1 || failed A-analysis 5
CELLS=$(python3 -c "import json;print(' '.join(json.load(open('$A/decision-analysis-main.json'))['extension_cells_required']))") || failed A-extension-cells 5
if [ -n "$CELLS" ]; then
  stamp A-extension "start cells: $CELLS"
  python3 scripts/prepare_bc_qualification.py "$A/extension/plan" --identities "$A/identities.json" --source-manifest /Users/rt/workspace/knotrel/evidence/p0-coverage-increment-1-plan-20261030/manifest.json --phase extension --cells $CELLS --checkpoint v0.7.0-Requalification-A-Extension --session-seeds 130730 130731 130732 > "$L/A-extension-plan.log" 2>&1 || failed A-extension-plan 6
  python3 scripts/run_v070r_collect.py a --manifest "$A/extension/plan/manifest.json" --schedule "$A/extension/plan/schedule.json" --execute "$A/extension/raw-extension" > "$L/A-extension-run.log" 2>&1
  RC=$?; gate_check A-extension; [ $RC -eq 0 ] || failed A-extension 6
  stamp A-extension end
  python3 scripts/analyze_bc_qualification.py --main "$A/raw-main" --extension "$A/extension/raw-extension" --rules v0.4.0 --output "$A/final-decision-analysis.json" > "$L/A-analysis-final.log" 2>&1 || failed A-analysis-final 6
else
  stamp A-extension "none required"
  cp "$A/decision-analysis-main.json" "$A/final-decision-analysis.json"
fi

# --- B/C ---
stamp BC start
python3 scripts/run_v070r_collect.py bc --out "$CAMP/BC" --profile final --core "$T/cand-probes/release/core-lifecycle" --core-count "$T/cand-probes-count/release/core-lifecycle" --http "$T/cand-probes/release/http-lifecycle" --order-seed 50720 --knotrel "$CAMP/src/cand/knotrel" --lifecycle-engines compact-bfs --window-multipliers results/lifecycle-qualification-v0.5.0/window-multipliers-dcd8ccc.json > "$L/BC.log" 2>&1
RC=$?; gate_check BC; [ $RC -eq 0 ] || failed BC 7
stamp BC end

# --- R, Rmem, M_desc, M_reg ---
step() {  # step-name exit-code collector-args...
  NAME=$1; CODE=$2; shift 2
  stamp "$NAME" start
  python3 scripts/run_v070r_collect.py "$@" > "$L/$NAME.log" 2>&1
  RC=$?; gate_check "$NAME"; [ $RC -eq 0 ] || failed "$NAME" "$CODE"
  stamp "$NAME" end
}
step R 8 r --out "$CAMP/R" --ref "$T/ref-probes/release/release-cells" --cand "$T/cand-probes/release/release-cells"
step Rmem 9 rmem --out "$CAMP/Rmem" --ref "$T/ref-probes-peak/release/memory-peak" --cand "$T/cand-probes-peak/release/memory-peak"
step Mdesc 10 mdesc --out "$CAMP/Mdesc" --probe "$T/contention/release/contention-probe" --server "$T/cand-server/release/knotrel-server"
step Mreg 11 mreg --out "$CAMP/Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/ref-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server"

# --- End checks, with the monitor still running ---
python3 scripts/conformance_monitor.py git-snapshot /Users/rt/workspace/knotrel > "$L/git-after.json"
python3 - "$CAMP" "$G" "$QSTART" <<'PY' > "$L/end-checks.txt" 2>&1 || nonconforming "end-of-chain checks (logs/end-checks.txt)" 14
import pathlib, sys, time
sys.path.insert(0, "scripts")
import conformance_gate as cg
camp, gate_dir, start = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2]), float(sys.argv[3])
g = cg.Gate(gate_dir)
reasons = g.full_log_check(start, time.time())
reasons += cg.verify_gating(camp, gate_dir)
print({"gated": cg.gated_counts(gate_dir), "collected": cg.collector_counts(camp), "reasons": reasons})
if reasons:
    raise SystemExit(1)
PY
# The collectors read the campaign clones (git rev-parse/status), which changes no FETCH_HEAD or
# remote-tracking reflog; any difference anywhere is forbidden activity.
if ! cmp -s "$L/git-before.json" "$L/git-after.json"; then
  diff "$L/git-before.json" "$L/git-after.json" > "$L/git-state.diff"
  nonconforming "Git state changed during the attempt (logs/git-state.diff)" 15
fi
session_state > "$L/session-after.json"
gate_check chain-end
RESULT="CONFORMING: every gate check passed; monitor alive with no gap, zero totals; every child gated; Git state and Claude session files unchanged"
stamp CHAIN complete
