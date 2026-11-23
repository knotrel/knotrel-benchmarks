#!/bin/sh
# Block Q of the v1.0.0 qualification (PROTOCOL.md section 4): the approved feeder-under-load
# protocol (knotrel docs/integrations/feeder-under-load.md) on the candidate, all seven cells,
# 3 observations, plus the Q5 reference arm (v0.9.0 server, L1 G100k C=16 and C=64, 3
# observations each) in the same session, in three alternating rounds, under a 30-minute cap
# (scripts/run_v100q_q.py), then evaluated (scripts/evaluate_v100q_q.py). Runs only after
# Part 1 ended CONFORMING. Derived from results/v0.9.0-qualification/run_part3.sh.
#
# Usage: run_part3.sh CAMP [QATTEMPT]
#   QATTEMPT 1 (default) writes CAMP/part3; 2 writes CAMP/part3-attempt2 and is allowed only if
#   the first Q did not end COMPLETE and its cause is the cap or an infrastructure failure whose
#   one rerun was used up (both NONCONFORMING), or a runner or tooling error (FAILED) with no
#   product failure (run_v100q_q.py --attempt2-gate; plan section 9: one rerun of Q as a whole,
#   never because of a result). A COMPLETE Q is final. Attempt 2 writes superseded_by.json into
#   CAMP/part3; the evaluator then accepts only CAMP/part3-attempt2.
# Writes, in the Q directory: the steps of run_v100q_q.py (one directory per round and side),
# host-before.txt and host-after.txt, run.json, run.txt (times, candidate commit, binaries,
# PostgreSQL image), then evaluation.json. The PostgreSQL container is started before and
# removed after (the trap is set first); its start output and exit status are checked (a
# postgres:// URL) and the server answers SELECT 1 before step 1. A start failure is an
# infrastructure failure, recorded in CAMP/logs/<Q directory>-postgres-start-failed-N.txt; it
# allows one more start of the same Q attempt. The URL (with a random password) is passed in the
# environment and never written.
set -eu
CAMP=${1%/}
QATTEMPT=${2:-1}
K=$CAMP/src/cand/knotrel
B=$CAMP/src/cand/knotrel-benchmarks
F=$K/integrations/postgres-feeder
T=$CAMP/targets
case "$QATTEMPT" in
  1) OUT=$CAMP/part3 ;;
  2) OUT=$CAMP/part3-attempt2
     [ -f "$CAMP/part3/run.json" ] || { echo "no first Q to repeat" >&2; exit 3; }
     python3 "$B/scripts/run_v100q_q.py" --attempt2-gate "$CAMP/part3" \
       || { echo "Q attempt 2 is not allowed (see the reason above)" >&2; exit 3; }
     ;;
  *) echo "QATTEMPT must be 1 or 2" >&2; exit 3 ;;
esac
head -1 "$CAMP/logs/CONFORMANCE.txt" | grep -q '^CONFORMING' || { echo "Part 1 is not CONFORMING" >&2; exit 3; }
[ ! -e "$OUT" ] || { echo "refusing to reuse $OUT" >&2; exit 3; }
pmset -g batt | head -1 | grep -q "AC Power" || { echo "not on AC power" >&2; exit 3; }
for X in cand-server/release/knotrel-server ref-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do
  grep -q "$(shasum -a 256 "$T/$X" | cut -d' ' -f1)  targets/$X\$" "$CAMP/binaries-sha256.txt" || { echo "binary changed: $X" >&2; exit 3; }
done
QNAME=$(basename "$OUT")
FAILED_STARTS=$(ls "$CAMP/logs/$QNAME"-postgres-start-failed-*.txt 2>/dev/null | wc -l | tr -d ' ')
[ "$FAILED_STARTS" -lt 2 ] || { echo "PostgreSQL failed to start twice for $QNAME: the infrastructure rerun is used up; the maintainer decides" >&2; exit 3; }
for D in /usr/local/bin /opt/homebrew/bin /Applications/Docker.app/Contents/Resources/bin "$HOME/.docker/bin"; do
  case ":$PATH:" in *":$D:"*) ;; *) [ -d "$D" ] && PATH="$PATH:$D" ;; esac
done
PGNAME=knotrel-pg-test-18
trap 'bash "$F/scripts/stop-test-postgres.sh" 18 > /dev/null 2>&1 || true' EXIT
trap 'exit 130' INT TERM
PGERR=$CAMP/logs/$QNAME-postgres-start.stderr
PGRC=0
PGOUT=$(bash "$F/scripts/start-test-postgres.sh" 18 2> "$PGERR") || PGRC=$?
URL=$(printf '%s\n' "$PGOUT" | tail -1)
PGWHY=""
if [ "$PGRC" -ne 0 ]; then PGWHY="start-test-postgres.sh exited $PGRC"
else
  case "$URL" in postgres://*) ;; *) PGWHY="start-test-postgres.sh printed no postgres:// URL" ;; esac
fi
if [ -z "$PGWHY" ]; then
  docker exec "$PGNAME" pg_isready -U postgres -h 127.0.0.1 > /dev/null 2>&1 || PGWHY="pg_isready failed in $PGNAME"
fi
if [ -z "$PGWHY" ]; then
  [ "$(docker exec "$PGNAME" psql -U postgres -h 127.0.0.1 -qAt -c 'SELECT 1' 2>/dev/null)" = 1 ] || PGWHY="SELECT 1 failed in $PGNAME"
fi
if [ -n "$PGWHY" ]; then
  N=$((FAILED_STARTS + 1))
  {
    echo "classification infrastructure (plan section 5.5: loss of the local PostgreSQL container)"
    echo "utc $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "cause $PGWHY"
    echo "stderr tail:"
    tail -20 "$PGERR" 2>/dev/null || true
    echo "docker:"
    docker ps -a --format '{{.Names}} {{.Image}} {{.Status}}' 2>&1 | head -20 || true
  } > "$CAMP/logs/$QNAME-postgres-start-failed-$N.txt"
  echo "infrastructure failure: PostgreSQL not available ($PGWHY); recorded in logs/$QNAME-postgres-start-failed-$N.txt" >&2
  exit 4
fi
if [ "$QATTEMPT" = 2 ]; then
  python3 "$B/scripts/run_v100q_q.py" --attempt2-gate "$CAMP/part3" --write-marker part3-attempt2 > /dev/null \
    || { echo "Q attempt 2 is not allowed" >&2; exit 3; }
fi
RC=0
LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" KNOTREL_PG_ADMIN_URL="$URL" python3 "$B/scripts/run_v100q_q.py" "$CAMP" "$OUT" || RC=$?
{
  echo "candidate $(git -C "$K" rev-parse HEAD)"
  echo "run_v100q_q exit $RC"
  grep -o 'postgres:18[^"]*' "$F/scripts/start-test-postgres.sh" | head -1
} > "$OUT/run.txt"
LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" python3 "$B/scripts/evaluate_v100q_q.py" "$OUT" \
  --baseline-v080 "$K/docs/integrations/feeder-under-load/baseline-v0.8.0-summary.json" > "$OUT/evaluation.json"
cat "$OUT/evaluation.json"
