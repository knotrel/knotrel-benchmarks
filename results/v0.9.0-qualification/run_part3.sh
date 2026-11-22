#!/bin/sh
# Part 3 of the v0.9.0 qualification (PROTOCOL.md section 4): the approved feeder-under-load
# protocol (knotrel docs/integrations/feeder-under-load.md) on the candidate, all cells,
# 3 observations, no smoke overrides (LOAD_* unset). Runs after Part 2 has ended; requires Part 1 CONFORMING.
#
# Usage: run_part3.sh CAMP
# Writes CAMP/part3/: results.jsonl and summary.json (the load tool), host-before.txt and
# host-after.txt (power, thermal, top processes), run.txt (times, binaries, PostgreSQL image),
# then evaluation.json (evaluate_v090q_part3.py: Q1-Q4 from the tool, Q5 against the v0.8.0
# baseline of the approved protocol). The PostgreSQL container is started before and removed
# after; its URL (with a random password) is passed in the environment and never written.
set -eu
CAMP=${1%/}
OUT=$CAMP/part3
K=$CAMP/src/cand/knotrel
F=$K/integrations/postgres-feeder
T=$CAMP/targets
# Part 3 depends on Part 1 (a conforming deciding campaign on this candidate), not on Part 2,
# which is descriptive; it runs after Part 2 has ended, whatever Part 2's status.
head -1 "$CAMP/logs/CONFORMANCE.txt" | grep -q '^CONFORMING' || { echo "Part 1 is not CONFORMING" >&2; exit 3; }
[ -f "$CAMP/part2/logs/CONFORMANCE.txt" ] || { echo "Part 2 has not ended" >&2; exit 3; }
[ ! -e "$OUT" ] || { echo "refusing to reuse $OUT" >&2; exit 3; }
pmset -g batt | head -1 | grep -q "AC Power" || { echo "not on AC power" >&2; exit 3; }
grep -q "$(shasum -a 256 "$T/cand-server/release/knotrel-server" | cut -d' ' -f1)" "$CAMP/binaries-sha256.txt" || { echo "candidate server changed" >&2; exit 3; }
mkdir -p "$OUT"
host() { { date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -1; pmset -g therm; ps -Ao pcpu,comm -r | head -12; } > "$1" 2>&1; }
host "$OUT/host-before.txt"
URL=$(bash "$F/scripts/start-test-postgres.sh" 18 | tail -1)
trap 'bash "$F/scripts/stop-test-postgres.sh" 18 > /dev/null 2>&1 || true' EXIT INT TERM
{
  echo "start $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo "candidate $(git -C "$K" rev-parse HEAD)"
  shasum -a 256 "$T/cand-server/release/knotrel-server" "$T/feeder/release/knotrel-pg-feeder" "$T/feeder/release/examples/load"
  grep -o 'postgres:18[^"]*' "$F/scripts/start-test-postgres.sh" | head -1
} > "$OUT/run.txt"
env -u LOAD_REPS -u LOAD_WINDOW_SECS -u LOAD_BACKLOG -u LOAD_CELLS \
  KNOTREL_BIN="$T/cand-server/release/knotrel-server" FEEDER_BIN="$T/feeder/release/knotrel-pg-feeder" \
  KNOTREL_PG_ADMIN_URL="$URL" LOAD_OUT="$OUT" \
  /usr/bin/caffeinate -dimsu "$T/feeder/release/examples/load" > "$OUT/load.stdout" 2> "$OUT/load.stderr"
echo "end $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$OUT/run.txt"
host "$OUT/host-after.txt"
python3 "$CAMP/src/cand/knotrel-benchmarks/scripts/evaluate_v090q_part3.py" "$OUT/summary.json" \
  "$K/docs/integrations/feeder-under-load/baseline-v0.8.0-summary.json" > "$OUT/evaluation.json"
cat "$OUT/evaluation.json"
