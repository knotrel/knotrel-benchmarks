#!/bin/sh
# Runs one v1.2.0 release-qualification session (knotrel#182; knotrel
# docs/releases/v1.2.0-qualification-plan.md, sections 5, 8 and 9) and records the host
# conformance data around it.
#
# Usage: run_session.sh CAMP [OUT_NAME [RUN_CF5_ARGS...]]
#   OUT_NAME      output directory under CAMP (default: session1; must not exist)
#   RUN_CF5_ARGS  passed to run_cf5.py (the preparatory duration trial: --preparatory
#                 --pairs 2 --warmup 0 --no-smoke); none for the frozen session
#
# The matrix is the one next to the tool map's freeze record (_freeze): attempt 1's
# results/v1.2.0-qualification/v120q-matrix.json, attempt 2's attempt2/v120q-matrix.json.
#
# Before and after the session: vm_stat (cumulative Swapins and Swapouts, plan section 5),
# sysctl vm.swapusage, pmset power and thermal state, uptime, into OUT/host-before.txt and
# OUT/host-after.txt; then OUT/swap-activity.json with the counter deltas. Non-zero deltas
# make the session NONCONFORMING (plan section 9); this script records them and exits 5,
# and the analysis must not publish classes from that session. The session runs under
# caffeinate -ims. Exit status: run_cf5.py's, or 5 for swap activity.
set -eu
CAMP=${1:?usage: run_session.sh CAMP [OUT_NAME [RUN_CF5_ARGS...]]}
CAMP=${CAMP%/}
NAME=${2:-session1}
[ $# -ge 2 ] && shift 2 || shift 1
B=$CAMP/src/cand/knotrel-benchmarks
OUT=$CAMP/$NAME
if [ -e "$OUT" ]; then echo "refusing to reuse $OUT" >&2; exit 3; fi
HOSTDIR=$CAMP/host-$NAME
mkdir -p "$HOSTDIR"
snapshot() {
  { date -u +%Y-%m-%dT%H:%M:%SZ; vm_stat; sysctl vm.swapusage; pmset -g batt; pmset -g therm; uptime; } > "$1" 2>&1
}
snapshot "$HOSTDIR/host-before.txt"
RC=0
MATRIX=$(python3 -c "import json, os, sys; print(os.path.join(os.path.dirname(json.load(open(sys.argv[1]))['_freeze']), 'v120q-matrix.json'))" "$CAMP/tools.json")
[ -f "$MATRIX" ] || { echo "no matrix $MATRIX" >&2; exit 3; }
echo "matrix: $MATRIX" > "$HOSTDIR/matrix.txt"
( cd "$B" && LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" caffeinate -ims python3 scripts/run_cf5.py \
    --matrix "$MATRIX" --tools "$CAMP/tools.json" \
    --out "$OUT" "$@" ) || RC=$?
snapshot "$HOSTDIR/host-after.txt"
SWAP=0
python3 - "$HOSTDIR" "$RC" <<'PY' || SWAP=$?
import json, re, sys
d, rc = sys.argv[1], int(sys.argv[2])
def counters(name):
    text = open(f"{d}/{name}").read()
    return {k: int(re.search(rf"^{k}:\s+(\d+)\.", text, re.M).group(1)) for k in ("Swapins", "Swapouts")}
before, after = counters("host-before.txt"), counters("host-after.txt")
delta = {k: after[k] - before[k] for k in before}
record = {"before": before, "after": after, "delta": delta, "run_cf5_exit": rc,
          "swap_activity": any(delta.values())}
json.dump(record, open(f"{d}/swap-activity.json", "w"), indent=1)
print(json.dumps(record))
sys.exit(5 if record["swap_activity"] else 0)
PY
[ "$RC" -ne 0 ] && exit "$RC"
exit "$SWAP"
