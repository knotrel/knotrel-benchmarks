#!/bin/sh
# Prepares a soak (amendment 1, A3): no build, no candidate, no measurement. Only the frozen
# knotrel-benchmarks tooling is cloned, so run_final_chain.sh --soak can run from it.
#
# Usage: prepare_soak.sh FREEZE_SHA N SERIES
#   FREEZE_SHA knotrel-benchmarks commit containing the amendment-2 freeze record (FREEZE-A2.json)
#   N          soak number, counted across amendments: the number of existing soak directories
#              plus one, at most conformance.soak.max_soaks (series_budget.sh)
#   SERIES     attempt series of the amendment (a2; series a1 is closed)
# Writes CAMP/LAUNCH-COMMAND.txt: the command the maintainer runs in Terminal.app with Claude quit.
#
# Creates /Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-SERIES-soakN/ (refuses to reuse it).
set -eu
FREEZE=$1
N=$2
SERIES=$3
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
case "$N" in [1-9]) ;; *) echo "soak number must be 1-9" >&2; exit 3;; esac
case "$SERIES" in a2) ;; a1) echo "series a1 is closed (amendment 2)" >&2; exit 3;; *) echo "series must be a2 (amendment 2)" >&2; exit 3;; esac
CAMP=/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-$SERIES-soak$N
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
if git -C "$BREPO" cat-file -e "$FREEZE:results/v0.7.0-requalification/FREEZE-A3.json" 2>/dev/null; then echo "amendment 3 has no soaks" >&2; exit 3; fi
git -C "$BREPO" cat-file -e "$FREEZE:results/v0.7.0-requalification/FREEZE-A2.json" || { echo "FREEZE-A2.json is not in $FREEZE: the amendment is not frozen" >&2; exit 3; }

sh "$(dirname "$0")/check_restored.sh" || exit 3
MAX=$(git -C "$BREPO" show "$FREEZE:results/v0.7.0-requalification/MATRIX.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['conformance']['soak']['max_soaks'])")
# The soak budget counts every soak of every amendment (MATRIX conformance.amendment_2.soak_budget).
sh "$(dirname "$0")/series_budget.sh" soak "$N" "$MAX" /Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-a*-soak[1-9] || exit 3
mkdir -p "$CAMP/logs" "$CAMP/src/cand"
git clone --quiet "$BREPO" "$CAMP/src/cand/knotrel-benchmarks"
git -C "$CAMP/src/cand/knotrel-benchmarks" checkout --quiet --detach "$FREEZE"
test "$(git -C "$CAMP/src/cand/knotrel-benchmarks" rev-parse HEAD)" = "$FREEZE"
mkdir -p "$CAMP/bin" && ln -s "$(command -v python3)" "$CAMP/bin/python3"
sh "$(dirname "$0")/launch_command.sh" "$CAMP" - --soak > "$CAMP/LAUNCH-COMMAND.txt"
echo "PREPARED $CAMP"
