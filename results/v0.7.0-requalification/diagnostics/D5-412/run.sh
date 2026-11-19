#!/bin/sh
# D5 reproduction (DIAGNOSTICS-PLAN.md): 3 runs, each runs the frozen, instrumented and corrected
# probe in turn against the a3-3 candidate server (source-managed, lifecycle on, 100k, seed 7).
set -u
OUT=$1
SERVER=/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-e75ff6a-a3-attempt3/targets/cand-server/release/knotrel-server
for RUN in 1 2 3; do
  for V in frozen instrumented corrected; do
    case $V in
      frozen) P=/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-e75ff6a-a3-attempt3/targets/contention/release/contention-probe;;
      *) P=/private/tmp/claude-501/-Users-rt-workspace-knotrel/a1cddd20-25d9-47d8-bd37-1419d4f1e1b4/scratchpad/d5target/$V/release/contention-probe-d5-$V;;
    esac
    echo "run $RUN $V $(date -u +%H:%M:%SZ)" >> $OUT/runs.txt
    "$P" --server-bin "$SERVER" --mode source-managed --lifecycle true --nodes 100000 --seed 7 --configs /Users/rt/workspace/knotrel/v0.7.0/knotrel-benchmarks/results/v0.7.0-requalification/diagnostics/D5-412/configs.jsonl > $OUT/run$RUN-$V.stdout 2> $OUT/run$RUN-$V.stderr
    echo "  exit $?" >> $OUT/runs.txt
  done
done
