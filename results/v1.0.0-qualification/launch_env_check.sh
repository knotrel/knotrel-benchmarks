#!/bin/sh
# Checks, in the launch environment, that the runner will find every program it runs and that
# every collector accepts its arguments (dry runs measure nothing and write no output), before
# an attempt can be used up. Derived from results/v0.9.0-qualification/launch_env_check.sh: the
# same checks with this directory's bindings and the v1.0 chain (A block 1 and block 2, B4+C or
# the full B/C if the core rule triggered, R, Rmem, M_reg; no M_desc, no Part 2), plus block Q's
# binaries and the Q runner's arguments.
#
# Usage: launch_env_check.sh CAMP OUT
# LAUNCH_ENV_MODE=prefreeze (set by prepare_campaign.sh --pre-freeze): there is no freeze record
# yet, so the runner's preflight must refuse with "not frozen" and that refusal is the expected
# result; every other check is the same.
set -u
[ $# -eq 2 ] || { echo "usage: launch_env_check.sh CAMP OUT" >&2; exit 2; }
CAMP=${1%/}
OUT=$2
MODE=${LAUNCH_ENV_MODE:-attempt}
B=$CAMP/src/cand/knotrel-benchmarks
R=$B/results/v1.0.0-qualification
T=$CAMP/targets
A=$CAMP/A
: > "$OUT"
say() { echo "$1" >> "$OUT"; }
bad() { say "LAUNCH-ENV FAILED: $1"; echo "LAUNCH-ENV FAILED: $1"; exit 1; }
WANT_PATH=$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin
[ "$PATH" = "$WANT_PATH" ] || bad "PATH is $PATH, expected $WANT_PATH"
cd "$B" || bad "no tooling clone in $CAMP"
case "$MODE" in
  attempt) [ -f "$R/FREEZE.json" ] || bad "no $R/FREEZE.json (the R/Rmem/M collectors would refuse to run)" ;;
  prefreeze) [ ! -f "$R/FREEZE.json" ] || bad "pre-freeze check, but $R/FREEZE.json exists" ;;
  *) bad "unknown LAUNCH_ENV_MODE $MODE" ;;
esac
say "mode $MODE"
[ "$(ls "$CAMP/bin" | tr '\n' ' ')" = "python3 rustc " ] || bad "CAMP/bin must hold exactly python3 and rustc: $(ls "$CAMP/bin" | tr '\n' ' ')"
for TOOL in $(grep -v '^#' "$R/launch_tools.txt"); do
  P=$(command -v "$TOOL") || bad "$TOOL not found on the launch PATH"
  say "tool $TOOL $P"
done
V=$(rustc +1.100.0 -Vv 2>&1) || bad "rustc +1.100.0 -Vv failed: $V"
say "rustc $(echo "$V" | head -1)"
unset KNOTREL_GATE_DIR KNOTREL_INTERFERENCE_DIR
export LIFECYCLE_QUALIFICATION_ROOTS="$(dirname "$CAMP")"
D=${OUT%.txt}-dryrun
run() {  # name command...
  NAME=$1; shift
  if "$@" >> "$OUT" 2>&1; then say "dry-run $NAME ok"; else bad "dry run $NAME failed (see $OUT)"; fi
}
WM=results/v1.0.0-qualification/window-multipliers-q3.json
CORE_RULE=identical
if [ "$MODE" = attempt ]; then
  CORE_RULE=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['core_rule']['outcome'])" "$R/FREEZE.json") || bad "no core_rule.outcome in the freeze record"
fi
ONLY="--only B4,C"
[ "$CORE_RULE" = different ] && ONLY=""
say "core rule $CORE_RULE (B/C ${ONLY:-full})"
run A-block1 python3 scripts/run_v100q_collect.py a --manifest "$A/plan/manifest.json" --schedule "$A/plan/schedule.json" --dry-run
run A-block2 python3 scripts/run_v100q_collect.py a --manifest "$A/plan-block2/manifest.json" --schedule "$A/plan-block2/schedule.json" --dry-run
# shellcheck disable=SC2086 # ONLY is empty or two words
run BC python3 scripts/run_v100q_collect.py bc --out "$D-BC" --profile final --core "$T/cand-probes/release/core-lifecycle" --core-count "$T/cand-probes-count/release/core-lifecycle" --http "$T/cand-probes/release/http-lifecycle" --order-seed 50720 --knotrel "$CAMP/src/cand/knotrel" --lifecycle-engines compact-bfs --equivalent-references $ONLY --window-multipliers $WM --dry-run
if [ "$CORE_RULE" = different ]; then
  run T5 python3 scripts/run_v070q3_t5.py --out "$D-T5" --base "$T/t5base-probes/release/core-lifecycle" --cand "$T/cand-probes/release/core-lifecycle" --order-seed 50730 --dry-run
fi
run R python3 scripts/run_v100q_collect.py r --out "$D-R" --ref "$T/ref-probes/release/release-cells" --cand "$T/cand-probes/release/release-cells" --dry-run
run Rmem python3 scripts/run_v100q_collect.py rmem --out "$D-Rmem" --ref "$T/ref-probes-peak/release/memory-peak" --cand "$T/cand-probes-peak/release/memory-peak" --dry-run
run Mreg python3 scripts/run_v100q_collect.py mreg --out "$D-Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/ref-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server" --dry-run
RUNNER=$(python3 scripts/run_v100q_autonomous.py "$CAMP" "$(git -C "$CAMP/src/cand/knotrel" rev-parse HEAD)" --dry-run 2>&1)
RC=$?
say "$RUNNER"
if [ "$MODE" = attempt ]; then
  [ $RC -eq 0 ] || bad "runner preflight failed: $RUNNER"
  say "dry-run runner ok"
else
  case "$RUNNER" in
    *"DRY-RUN NOT STARTED: no results/v1.0.0-qualification/FREEZE.json: the campaign is not frozen"*) say "dry-run runner refused as expected before the freeze" ;;
    *) bad "pre-freeze runner preflight did not refuse as expected: $RUNNER" ;;
  esac
fi
for X in BC T5 R Rmem Mreg; do [ ! -e "$D-$X" ] || bad "dry run $X wrote $D-$X"; done
for X in cand-server/release/knotrel-server ref-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do
  [ -x "$T/$X" ] || bad "block Q binary $X not built"
done
python3 scripts/run_v100q_q.py --help > /dev/null 2>&1 || bad "Q runner does not start"
python3 scripts/evaluate_v100q_q.py --help > /dev/null 2>&1 || bad "Q evaluator does not start"
say "LAUNCH-ENV OK"
echo "LAUNCH-ENV OK"
