#!/bin/sh
# Amendment 2: prints the one-line command the maintainer pastes into the only Terminal.app window
# (zsh) with Claude quit. Used by prepare_soak.sh and prepare_campaign.sh (CAMP/LAUNCH-COMMAND.txt).
#
# Usage: launch_command.sh CAMP CAND [--soak]
# The command: pins PATH to CAMP/bin (python3 and rustc, linked by the prepare script) plus the
# system directories;
# runs precheck_terminal.sh (read-only) and only if it passes the chain, both as
# /usr/bin/caffeinate -dimsu /bin/sh ... (the lineage the policy requires) with stdin from
# /dev/null; appends to CAMP/chain-launch.log (never overwrites); prints the log's tail at the end.
set -eu
CAMP=${1%/}
CAND=$2
EXTRA=${3:-}
case "$CAMP" in *[!A-Za-z0-9_./-]*) echo "unsupported character in $CAMP" >&2; exit 3;; esac
# PATH starts with CAMP/bin, which the prepare script fills with two links (PROTOCOL.md 10.7): python3 to
# the python3 it used, rustc to its rustup proxy. No other tool comes ahead of /usr/bin.
PYDIR=$CAMP/bin
R=$CAMP/src/cand/knotrel-benchmarks/results/v0.7.0-requalification
LOG=$CAMP/chain-launch.log
echo "export PATH=$PYDIR:/usr/bin:/bin:/usr/sbin:/sbin; cd /; if /usr/bin/caffeinate -dimsu /bin/sh $R/precheck_terminal.sh $CAMP < /dev/null; then /usr/bin/caffeinate -dimsu /bin/sh $R/run_final_chain.sh $CAMP $CAND $EXTRA < /dev/null >> $LOG 2>&1; echo \"chain exit=\$?\" >> $LOG; tail -4 $LOG; fi"
