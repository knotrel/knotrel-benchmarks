#!/bin/sh
# Prints the commands that launch the v0.9.0 qualification's autonomous runner (PROTOCOL.md
# section 5): Part 1, then Part 2 after Part 1 ends CONFORMING. Each runs detached in its own
# session with the launch PATH (CAMP/bin, then the system directories), stdin from /dev/null,
# appending to CAMP/runner.log. Derived from results/v0.7.0-qualification-3/launch_command.sh
# (revision 3 path only; no Terminal controller, no soak).
#
# Usage: launch_command.sh CAMP CAND
set -eu
CAMP=${1%/}
CAND=$2
case "$CAMP" in *[!A-Za-z0-9_./-]*) echo "unsupported character in $CAMP" >&2; exit 3;; esac
for PART in 1 2; do
  echo "# Part $PART"
  echo "export PATH=$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin; cd $CAMP/src/cand/knotrel-benchmarks && nohup python3 -c 'import os,sys; os.setsid(); os.execv(sys.executable, [sys.executable] + sys.argv[1:])' scripts/run_v090q_autonomous.py $CAMP $CAND --part $PART < /dev/null >> $CAMP/runner.log 2>&1 &"
done
