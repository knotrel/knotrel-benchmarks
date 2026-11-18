#!/bin/sh
# Amendment 2: read-only check run from Terminal.app just before run_final_chain.sh, by the same
# LAUNCH-COMMAND.txt, with the same ancestry (/usr/bin/caffeinate -dimsu /bin/sh ...).
# It changes nothing on the host and nothing in the campaign directory except
# logs/precheck-*.{json,txt}. If it fails, the chain is not launched, so the campaign directory
# stays usable (a refusal inside the chain would use up the directory: PROTOCOL.md section 9.5).
#
# Usage: precheck_terminal.sh CAMP
# Checks: the campaign was never launched (no gate/ directory, no CONFORMANCE.txt); AC power;
# MATRIX conformance.controller_kind is terminal; the controller policy (Terminal lineage, one
# window and tab, no Claude process); ~/.claude/projects readable; no unrestored quiesce.
set -u
[ $# -eq 1 ] || { echo "usage: precheck_terminal.sh CAMP" >&2; exit 2; }
CAMP=${1%/}
B=$CAMP/src/cand/knotrel-benchmarks
L=$CAMP/logs
MATRIX=$B/results/v0.7.0-requalification/MATRIX.json
cd "$B" || { echo "PRECHECK REFUSED: no tooling clone in $CAMP"; exit 1; }
fail() { echo "PRECHECK REFUSED: $1"; echo "Nothing was started. Fix it, then run the same command again."; exit 1; }
[ ! -e "$CAMP/gate" ] && [ ! -e "$L/CONFORMANCE.txt" ] || fail "$CAMP was already launched (the prepare script makes a new directory)"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) fail "not on AC power";; esac
KIND=$(python3 -c "import json;print(json.load(open('$MATRIX'))['conformance']['controller_kind'])" 2>/dev/null)
[ "$KIND" = terminal ] || fail "MATRIX conformance.controller_kind is not terminal"
python3 scripts/conformance_monitor.py policy --chain $$ --controller-kind terminal --matrix "$MATRIX" --out "$L/precheck-policy.json" 2> "$L/precheck-policy-error.txt" \
  || fail "$(cat "$L/precheck-policy-error.txt")"
S=$(python3 scripts/conformance_monitor.py tree-state "$HOME/.claude/projects" 2>/dev/null) && [ -n "$S" ] || fail "~/.claude/projects unreadable"
sh "$B/results/v0.7.0-requalification/check_restored.sh" 2> "$L/precheck-restored.txt" || fail "unrestored quiesce: $(cat "$L/precheck-restored.txt")"
echo "PRECHECK OK: launching the chain now. Leave the Mac; do not reopen Claude until this window prints the result."
