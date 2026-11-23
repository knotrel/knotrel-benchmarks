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
#   the first Q ended NONCONFORMING (cap) or with an infrastructure failure recorded in its
#   failures.jsonl (plan section 9: one rerun of Q as a whole, never because of a result).
# Writes, in the Q directory: the steps of run_v100q_q.py (one directory per round and side),
# host-before.txt and host-after.txt, run.json, run.txt (times, candidate commit, binaries,
# PostgreSQL image), then evaluation.json. The PostgreSQL container is started before and
# removed after; its URL (with a random password) is passed in the environment and never written.
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
     python3 - "$CAMP/part3" <<'PY' || { echo "Q attempt 2 is allowed only after a NONCONFORMING Q or an infrastructure failure" >&2; exit 3; }
import json, os, sys
d = sys.argv[1]
run = json.load(open(os.path.join(d, "run.json")))
path = os.path.join(d, "failures.jsonl")
infra = os.path.exists(path) and any(json.loads(l).get("classification") == "infrastructure"
                                     for l in open(path) if l.strip())
sys.exit(0 if run["status"] == "NONCONFORMING" or infra else 1)
PY
     ;;
  *) echo "QATTEMPT must be 1 or 2" >&2; exit 3 ;;
esac
head -1 "$CAMP/logs/CONFORMANCE.txt" | grep -q '^CONFORMING' || { echo "Part 1 is not CONFORMING" >&2; exit 3; }
[ ! -e "$OUT" ] || { echo "refusing to reuse $OUT" >&2; exit 3; }
pmset -g batt | head -1 | grep -q "AC Power" || { echo "not on AC power" >&2; exit 3; }
for X in cand-server/release/knotrel-server ref-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do
  grep -q "$(shasum -a 256 "$T/$X" | cut -d' ' -f1)  targets/$X\$" "$CAMP/binaries-sha256.txt" || { echo "binary changed: $X" >&2; exit 3; }
done
URL=$(bash "$F/scripts/start-test-postgres.sh" 18 | tail -1)
trap 'bash "$F/scripts/stop-test-postgres.sh" 18 > /dev/null 2>&1 || true' EXIT INT TERM
RC=0
KNOTREL_PG_ADMIN_URL="$URL" python3 "$B/scripts/run_v100q_q.py" "$CAMP" "$OUT" || RC=$?
{
  echo "candidate $(git -C "$K" rev-parse HEAD)"
  echo "run_v100q_q exit $RC"
  grep -o 'postgres:18[^"]*' "$F/scripts/start-test-postgres.sh" | head -1
} > "$OUT/run.txt"
LIFECYCLE_QUALIFICATION_ROOTS="$CAMP" python3 "$B/scripts/evaluate_v100q_q.py" "$OUT" \
  --baseline-v080 "$K/docs/integrations/feeder-under-load/baseline-v0.8.0-summary.json" > "$OUT/evaluation.json"
cat "$OUT/evaluation.json"
