#!/bin/sh
# Prints the commands that launch the v1.0.0 qualification (PROTOCOL.md section 5): Part 1, the
# autonomous runner, detached in its own session with the launch PATH (CAMP/bin, then the system
# directories), stdin from /dev/null, appending to CAMP/runner.log; then block Q, to run only
# after Part 1 ended CONFORMING (run_part3.sh checks it). Derived from
# results/v0.9.0-qualification/launch_command.sh (no Part 2, no block D).
#
# Usage: launch_command.sh CAMP CAND
set -eu
CAMP=${1%/}
CAND=$2
case "$CAMP" in *[!A-Za-z0-9_./-]*) echo "unsupported character in $CAMP" >&2; exit 3;; esac
echo "$CAND" | grep -Eq '^[0-9a-f]{40}$' || { echo "CAND must be a 40-character commit" >&2; exit 3; }
echo "# Part 1"
echo "export PATH=$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin; cd $CAMP/src/cand/knotrel-benchmarks && nohup python3 -c 'import os,sys; os.setsid(); os.execv(sys.executable, [sys.executable] + sys.argv[1:])' scripts/run_v100q_autonomous.py $CAMP $CAND < /dev/null >> $CAMP/runner.log 2>&1 &"
echo "# Block Q, after Part 1 ended CONFORMING (head -1 $CAMP/logs/CONFORMANCE.txt)"
echo "sh $CAMP/src/cand/knotrel-benchmarks/results/v1.0.0-qualification/run_part3.sh $CAMP"
