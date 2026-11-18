#!/bin/sh
# Prepares an amendment-1 soak (A3): no build, no candidate, no measurement. Only the frozen
# knotrel-benchmarks tooling is cloned, so run_final_chain.sh --soak can run from it.
#
# Usage: prepare_soak.sh FREEZE_SHA N SERIES
#   FREEZE_SHA knotrel-benchmarks commit containing the amendment's freeze record
#   N          soak number (at most conformance.soak.max_soaks)
#   SERIES     attempt series of the amendment (a1)
#
# Creates /Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-SERIES-soakN/ (refuses to reuse it).
set -eu
FREEZE=$1
N=$2
SERIES=$3
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
case "$N" in [1-9]) ;; *) echo "soak number must be 1-9" >&2; exit 3;; esac
case "$SERIES" in a[1-9]) ;; *) echo "series must be aN" >&2; exit 3;; esac
CAMP=/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-$SERIES-soak$N
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
git -C "$BREPO" cat-file -e "$FREEZE:results/v0.7.0-requalification/FREEZE-A1.json" || { echo "FREEZE-A1.json is not in $FREEZE: the amendment is not frozen" >&2; exit 3; }
sh "$(dirname "$0")/check_restored.sh" || exit 3
MAX=$(git -C "$BREPO" show "$FREEZE:results/v0.7.0-requalification/MATRIX.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['conformance']['soak']['max_soaks'])")
if [ "$N" -gt "$MAX" ]; then echo "soak $N exceeds max_soaks $MAX: the maintainer decides" >&2; exit 3; fi
mkdir -p "$CAMP/logs" "$CAMP/src/cand"
git clone --quiet "$BREPO" "$CAMP/src/cand/knotrel-benchmarks"
git -C "$CAMP/src/cand/knotrel-benchmarks" checkout --quiet --detach "$FREEZE"
test "$(git -C "$CAMP/src/cand/knotrel-benchmarks" rev-parse HEAD)" = "$FREEZE"
echo "PREPARED $CAMP"
