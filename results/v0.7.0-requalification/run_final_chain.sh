#!/bin/sh
# Runs the frozen v0.7.0 re-qualification in one chain: grace period, policy, quiet period,
# then A (main, extension if required), B/C, R, Rmem, M_desc, M_reg. Every measured child is
# gated (scripts/conformance_gate.py) by the allow-list monitor (scripts/conformance_monitor.py).
#
# Run under: caffeinate -dimsu sh run_final_chain.sh CAMP CAND_SHA CONTROLLER_PID TRANSCRIPT
#   CAMP            campaign directory made by prepare_campaign.sh
#   CAND_SHA        knotrel candidate commit
#   CONTROLLER_PID  PID of the controlling Claude Code CLI (an ancestor of this chain)
#   TRANSCRIPT      that session's transcript file (~/.claude/projects/.../<id>.jsonl); it and
#                   every file of the session directory (subagents) must not change during the attempt
#
# Conformance rule (MATRIX.json "conformance"): nothing outside the allow-list runs and no
# user input occurs from the start of the quiet period to the end of the chain. Any failed
# check stops the chain; the attempt is then NONCONFORMING (chain-steps.txt and
# logs/CONFORMANCE.txt). Every exit path writes logs/CONFORMANCE.txt, the final Git state and
# output checksums.
set -u
CAMP=$1
CAND=$2
CONTROLLER=$3
TRANSCRIPT=$4
B=$CAMP/src/cand/knotrel-benchmarks
T=$CAMP/targets
L=$CAMP/logs
A=$CAMP/A
G=$CAMP/gate
MATRIX=$B/results/v0.7.0-requalification/MATRIX.json
export LIFECYCLE_QUALIFICATION_ROOTS=/Users/rt/workspace/knotrel/evidence
export KNOTREL_GATE_DIR=$G
cd "$B" || exit 2
for f in "$A/raw-main" "$CAMP/BC" "$CAMP/R" "$CAMP/Rmem" "$CAMP/Mdesc" "$CAMP/Mreg" "$G"; do
  if [ -e "$f" ]; then echo "refusing to relaunch: $f exists" >&2; exit 3; fi
done
mkdir -p "$G"
stamp() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >> "$L/chain-steps.txt"; }
conf() { python3 -c "import json;print(json.load(open('$MATRIX'))['conformance']['$1'])"; }
session_state() { python3 scripts/conformance_monitor.py session-state "$TRANSCRIPT"; }

MON=""
RESULT="NONCONFORMING: chain ended before its last step"
finish() {  # runs on every exit: stop the monitor, record conformance, Git state and checksums
  trap - EXIT INT TERM HUP
  if [ -n "$MON" ]; then kill "$MON" 2>/dev/null; wait "$MON" 2>/dev/null; MON=""; fi
  [ -e "$L/git-after.json" ] || python3 scripts/conformance_monitor.py git-snapshot /Users/rt/workspace/knotrel > "$L/git-after.json" 2>/dev/null
  { echo "$RESULT"; cat "$G/gate-stop.json" 2>/dev/null; } > "$L/CONFORMANCE.txt"
  [ -e "$G/activity-monitor.jsonl" ] && cp "$G/activity-monitor.jsonl" "$L/activity-monitor.jsonl"
  ( cd "$CAMP" && find A BC R Rmem Mdesc Mreg gate -type f -print0 2>/dev/null | xargs -0 shasum -a 256 > logs/outputs-sha256.txt )
}
trap finish EXIT
trap 'RESULT="NONCONFORMING: chain interrupted by a signal"; exit 20' INT TERM HUP
nonconforming() { RESULT="NONCONFORMING: $1"; stamp NONCONFORMING "$1"; exit "$2"; }
failed() { RESULT="FAILED: $1 (no verdict; conformance not established)"; stamp "$1" FAILED; exit "$2"; }
SESSION_BEFORE=""
gate_check() {
  if [ -e "$G/gate-stop.json" ]; then nonconforming "gate stop after $1" 13; fi
  if [ -n "$SESSION_BEFORE" ] && [ "$(session_state)" != "$SESSION_BEFORE" ]; then
    session_state > "$L/session-after.json"
    nonconforming "controller session or subagent transcript changed (after $1)" 16
  fi
}

# --- Prelaunch: host state, grace period, policy, allow-list check, Git state ---
{ date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -2; pmset -g therm; uptime; } > "$L/prelaunch-host.txt"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) RESULT="NOT STARTED: not on AC power"; exit 4;; esac
GRACE=$(conf grace_period_s)
STABLE=$(conf session_stable_s)
MIN_IDLE=$(conf min_hid_idle_at_policy_s)
stamp GRACE "start ${GRACE}s (operator leaves the Mac; the controller ends its turn)"
sleep "$GRACE"
# The launch command reaches the transcript only after the tool call returns: validate after the grace.
if ! python3 scripts/conformance_monitor.py validate-transcript "$TRANSCRIPT" "$CAMP" 2> "$L/transcript-error.txt"; then
  RESULT="NOT STARTED: transcript not validated ($(cat "$L/transcript-error.txt"))"; exit 4
fi
S1=$(session_state); sleep "$STABLE"; S2=$(session_state)
[ "$S1" = "$S2" ] || { RESULT="NOT STARTED: controller session still active after the grace period"; exit 4; }
IDLE=$(python3 scripts/conformance_monitor.py hid-idle) || { RESULT="NOT STARTED: HID idle time unreadable"; exit 4; }
python3 -c "import sys; sys.exit(0 if float('$IDLE') >= float('$MIN_IDLE') else 1)" || { RESULT="NOT STARTED: user input ${IDLE}s ago (minimum ${MIN_IDLE}s)"; exit 4; }
if ! python3 scripts/conformance_monitor.py policy --chain $$ --controller "$CONTROLLER" --matrix "$MATRIX" --out "$G/policy.json" 2> "$L/policy-error.txt"; then
  RESULT="NOT STARTED: policy refused ($(cat "$L/policy-error.txt"))"; exit 4
fi
cp "$G/policy.json" "$L/policy.json"
python3 scripts/conformance_monitor.py inventory --policy "$G/policy.json" > "$L/prelaunch-inventory.txt"
if ! python3 scripts/conformance_monitor.py check --policy "$G/policy.json" > "$L/prelaunch-check.txt"; then
  RESULT="NOT STARTED: forbidden processes present (logs/prelaunch-check.txt)"; exit 4
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
RESULT="CONFORMING: every gate check passed; monitor alive with no gap, zero totals; every child gated; Git state and controller transcript unchanged"
stamp CHAIN complete
