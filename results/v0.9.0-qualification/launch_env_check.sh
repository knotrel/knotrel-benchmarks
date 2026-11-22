#!/bin/sh
# Checks, in the launch environment, that the runner will find every program it runs and that
# every collector accepts its arguments (dry runs measure nothing and write no output), before
# an attempt can be used up. Derived from results/v0.7.0-qualification-3/launch_env_check.sh:
# the same checks, with this directory's bindings, plus the Part 2 collectors.
#
# Usage: launch_env_check.sh CAMP OUT
set -u
[ $# -eq 2 ] || { echo "usage: launch_env_check.sh CAMP OUT" >&2; exit 2; }
CAMP=${1%/}
OUT=$2
B=$CAMP/src/cand/knotrel-benchmarks
R=$B/results/v0.9.0-qualification
T=$CAMP/targets
A=$CAMP/A
: > "$OUT"
say() { echo "$1" >> "$OUT"; }
bad() { say "LAUNCH-ENV FAILED: $1"; echo "LAUNCH-ENV FAILED: $1"; exit 1; }
WANT_PATH=$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin
[ "$PATH" = "$WANT_PATH" ] || bad "PATH is $PATH, expected $WANT_PATH"
cd "$B" || bad "no tooling clone in $CAMP"
[ -f "$R/FREEZE.json" ] || bad "no $R/FREEZE.json (the R/Rmem/M collectors would refuse to run)"
[ "$(ls "$CAMP/bin" | tr '\n' ' ')" = "python3 rustc " ] || bad "CAMP/bin must hold exactly python3 and rustc: $(ls "$CAMP/bin" | tr '\n' ' ')"
for TOOL in $(grep -v '^#' "$R/launch_tools.txt"); do
  P=$(command -v "$TOOL") || bad "$TOOL not found on the launch PATH"
  say "tool $TOOL $P"
done
V=$(rustc +1.100.0 -Vv 2>&1) || bad "rustc +1.100.0 -Vv failed: $V"
say "rustc $(echo "$V" | head -1)"
unset KNOTREL_GATE_DIR KNOTREL_INTERFERENCE_DIR
export LIFECYCLE_QUALIFICATION_ROOTS=/Users/rt/workspace/knotrel/evidence
D=${OUT%.txt}-dryrun
run() {  # name command...
  NAME=$1; shift
  if "$@" >> "$OUT" 2>&1; then say "dry-run $NAME ok"; else bad "dry run $NAME failed (see $OUT)"; fi
}
WM=results/v0.9.0-qualification/window-multipliers-q3.json
run A python3 scripts/run_v090q_collect.py a --manifest "$A/plan/manifest.json" --schedule "$A/plan/schedule.json" --dry-run
run BC python3 scripts/run_v090q_collect.py bc --out "$D-BC" --profile final --core "$T/cand-probes/release/core-lifecycle" --core-count "$T/cand-probes-count/release/core-lifecycle" --http "$T/cand-probes/release/http-lifecycle" --order-seed 50720 --knotrel "$CAMP/src/cand/knotrel" --lifecycle-engines compact-bfs --equivalent-references --window-multipliers $WM --dry-run
run T5 python3 scripts/run_v070q3_t5.py --out "$D-T5" --base "$T/t5base-probes/release/core-lifecycle" --cand "$T/cand-probes/release/core-lifecycle" --order-seed 50730 --dry-run
run R python3 scripts/run_v090q_collect.py r --out "$D-R" --ref "$T/ref-probes/release/release-cells" --cand "$T/cand-probes/release/release-cells" --dry-run
run Rmem python3 scripts/run_v090q_collect.py rmem --out "$D-Rmem" --ref "$T/ref-probes-peak/release/memory-peak" --cand "$T/cand-probes-peak/release/memory-peak" --dry-run
run Mdesc python3 scripts/run_v090q_collect.py mdesc --out "$D-Mdesc" --probe "$T/contention/release/contention-probe" --server "$T/cand-server/release/knotrel-server" --dry-run
run Mreg python3 scripts/run_v090q_collect.py mreg --out "$D-Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/ref-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server" --dry-run
run P2-BC python3 scripts/run_v090q_collect.py bc --out "$D-P2BC" --profile final --core "$T/v080-probes/release/core-lifecycle" --core-count "$T/v080-probes-count/release/core-lifecycle" --http "$T/v080-probes/release/http-lifecycle" --order-seed 50720 --knotrel "$CAMP/src/v080/knotrel" --lifecycle-engines compact-bfs --equivalent-references --only B4 --window-multipliers $WM --dry-run
run P2-Mreg python3 scripts/run_v090q_collect.py mreg --out "$D-P2Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/v080-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server" --dry-run
run runner python3 scripts/run_v090q_autonomous.py "$CAMP" "$(git -C "$CAMP/src/cand/knotrel" rev-parse HEAD)" --dry-run
for X in BC T5 R Rmem Mdesc Mreg P2BC P2Mreg; do [ ! -e "$D-$X" ] || bad "dry run $X wrote $D-$X"; done
[ -x "$T/feeder/release/knotrel-pg-feeder" ] && [ -x "$T/feeder/release/examples/load" ] || bad "Part 3 feeder or load tool not built"
say "LAUNCH-ENV OK"
echo "LAUNCH-ENV OK"
