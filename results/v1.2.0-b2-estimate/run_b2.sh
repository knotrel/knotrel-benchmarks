#!/bin/sh
# Runs the B2 estimate's measured blocks in the approved order (design section 7):
# off Q run, stop check, on Q run. The 2 h cap is enforced between blocks; each Q run has its own
# 2,700 s collection cap. Docker and PostgreSQL exist only inside each run_q.sh call.
#   run_b2.sh E
set -eu
E=${1%/}
START=$(date +%s)
CAP=7200
note() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $*" | tee -a "$E/run.log"; }
host() { { date -u +%FT%TZ; vm_stat | grep -E 'Swap(ins|outs)'; pmset -g batt | head -1; uptime; } > "$E/host-$1.txt"; }
host before
for MODE in off on; do
  if [ $(( $(date +%s) - START )) -ge $CAP ]; then note "INCOMPLETE: cap reached before $MODE"; exit 0; fi
  B=$E/$MODE/src/cand/knotrel-benchmarks
  RC=0
  caffeinate -ims sh "$B/results/v1.2.0-qualification/run_q.sh" "$E/$MODE" "$E/$MODE/run" > "$E/$MODE/run_q.log" 2>&1 || RC=$?
  note "$MODE run_q.sh exit $RC"
  host "after-$MODE"
  if [ "$MODE" = off ]; then
    if ( cd "$B" && python3 results/v1.2.0-b2-estimate/analyze_b2.py --stop-check "$E" ) >> "$E/run.log" 2>&1; then
      note "stop check: off mode passes its deciding criteria; on run follows"
    else
      note "stop check: off mode fails a deciding criterion (or has no evaluation); on run SKIPPED by protocol"
      exit 0
    fi
  fi
done
note "elapsed $(( $(date +%s) - START )) s"
