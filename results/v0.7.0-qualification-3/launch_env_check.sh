#!/bin/sh
# Qualification 3 (re-qualification amendment 3, revision 2, PROTOCOL.md section 10.7 there): checks, in the launch environment, that the
# chain will find every program it runs, before any attempt can be used up by a missing tool.
# Attempt a3-2 failed at B/C because `rustc` (provenance only) was not on the pinned PATH.
#
# Usage: launch_env_check.sh CAMP OUT
#   CAMP  campaign directory (prepared, not launched)
#   OUT   report file (prepare: logs/launch-env-check.txt; precheck: logs/precheck-launch-env.txt)
# Run with the launch PATH (CAMP/bin, then /usr/bin:/bin:/usr/sbin:/sbin): prepare_campaign.sh runs
# it under env -i with that PATH; precheck_terminal.sh runs it in the real launch environment.
# Checks:
#   1. PATH is exactly the launch PATH;
#   2. every program in launch_tools.txt resolves by name, CAMP/bin holds exactly python3 and rustc,
#      and `rustc +1.100.0 -Vv` succeeds (the B/C provenance call);
#   3. the dry run of every collector of the chain, with the chain's own arguments (A main, B/C,
#      T5, R, Rmem, M_desc, M_reg). A dry run measures nothing, writes no output and changes no Git ref,
#      and runs no gated child (KNOTREL_GATE_DIR stays unset, so a gated call would refuse). It may
#      refresh the Git index of the campaign clones (git status) and the Python bytecode cache of
#      the tooling clone; both happen before the chain's Git snapshot.
# Exit 1 on the first failure, with the reason on stdout and in OUT.
set -u
[ $# -eq 2 ] || { echo "usage: launch_env_check.sh CAMP OUT" >&2; exit 2; }
CAMP=${1%/}
OUT=$2
B=$CAMP/src/cand/knotrel-benchmarks
R=$B/results/v0.7.0-qualification-3
T=$CAMP/targets
A=$CAMP/A
: > "$OUT"
say() { echo "$1" >> "$OUT"; }
bad() { say "LAUNCH-ENV FAILED: $1"; echo "LAUNCH-ENV FAILED: $1"; exit 1; }
WANT_PATH=$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin
[ "$PATH" = "$WANT_PATH" ] || bad "PATH is $PATH, expected $WANT_PATH"
cd "$B" || bad "no tooling clone in $CAMP"
# Qualification 3: the R/Rmem/M collectors refuse to measure unless FREEZE.json sits next to the
# bound matrix (run_v060_qualification.py); a dry run skips that check, so check it here.
[ -f "$R/FREEZE.json" ] || bad "no $R/FREEZE.json (the R/Rmem/M collectors would refuse to run)"
[ "$(ls "$CAMP/bin" | tr '\n' ' ')" = "python3 rustc " ] || bad "CAMP/bin must hold exactly python3 and rustc: $(ls "$CAMP/bin" | tr '\n' ' ')"
for TOOL in $(grep -v '^#' "$R/launch_tools.txt"); do
  P=$(command -v "$TOOL") || bad "$TOOL not found on the launch PATH"
  say "tool $TOOL $P"
done
V=$(rustc +1.100.0 -Vv 2>&1) || bad "rustc +1.100.0 -Vv failed: $V"
say "rustc $(echo "$V" | head -1)"
unset KNOTREL_GATE_DIR
export LIFECYCLE_QUALIFICATION_ROOTS=/Users/rt/workspace/knotrel/evidence
D=${OUT%.txt}-dryrun  # never created (the dry runs return before writing --out); named after OUT, so
                      # the precheck's paths stay logs/precheck-*
run() {  # name command...
  NAME=$1; shift
  if "$@" >> "$OUT" 2>&1; then say "dry-run $NAME ok"; else bad "dry run $NAME failed (see $OUT)"; fi
}
run A python3 scripts/run_v070q3_collect.py a --manifest "$A/plan/manifest.json" --schedule "$A/plan/schedule.json" --dry-run
run BC python3 scripts/run_v070q3_collect.py bc --out "$D-BC" --profile final --core "$T/cand-probes/release/core-lifecycle" --core-count "$T/cand-probes-count/release/core-lifecycle" --http "$T/cand-probes/release/http-lifecycle" --order-seed 50720 --knotrel "$CAMP/src/cand/knotrel" --lifecycle-engines compact-bfs --equivalent-references --window-multipliers results/v0.7.0-qualification-3/window-multipliers-q3.json --dry-run
run T5 python3 scripts/run_v070q3_t5.py --out "$D-T5" --base "$T/t1base-probes/release/core-lifecycle" --cand "$T/cand-probes/release/core-lifecycle" --order-seed 50730 --dry-run
run R python3 scripts/run_v070q3_collect.py r --out "$D-R" --ref "$T/ref-probes/release/release-cells" --cand "$T/cand-probes/release/release-cells" --dry-run
run Rmem python3 scripts/run_v070q3_collect.py rmem --out "$D-Rmem" --ref "$T/ref-probes-peak/release/memory-peak" --cand "$T/cand-probes-peak/release/memory-peak" --dry-run
run Mdesc python3 scripts/run_v070q3_collect.py mdesc --out "$D-Mdesc" --probe "$T/contention/release/contention-probe" --server "$T/cand-server/release/knotrel-server" --dry-run
run Mreg python3 scripts/run_v070q3_collect.py mreg --out "$D-Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/ref-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server" --dry-run
# Revision 3: the autonomous runner's own preflight (FREEZE revision, hashes, binaries, AC, disk,
# no unrestored quiesce); it measures nothing and starts no monitor.
run runner python3 scripts/run_v070q3_autonomous.py "$CAMP" "$(basename "$CAMP" | sed -E 's/.*-([0-9a-f]{7})-q3-.*/\1/')"0000000000000000000000000000000000 --dry-run
for X in BC T5 R Rmem Mdesc Mreg; do [ ! -e "$D-$X" ] || bad "dry run $X wrote $D-$X"; done
say "LAUNCH-ENV OK"
echo "LAUNCH-ENV OK"
