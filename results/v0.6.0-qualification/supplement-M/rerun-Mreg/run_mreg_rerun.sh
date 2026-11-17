#!/bin/sh
# Runs the declared v0.6.0 M_reg rerun (PROTOCOL-MREG-RERUN.md). Do not start
# without maintainer approval.
# Usage: caffeinate -dimsu sh run_mreg_rerun.sh FREEZE_SHA
#   FREEZE_SHA  knotrel-benchmarks commit that contains FREEZE-MREG-RERUN.json
# Creates /Users/rt/workspace/knotrel/evidence/v0.6.0-mreg-rerun-48bc82f/ (refuses to reuse it).
# Never writes to historical evidence: binaries are read in place, Git state is only read.
set -eu
FREEZE=$1
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
WORKSPACE=/Users/rt/workspace/knotrel
OUT=$WORKSPACE/evidence/v0.6.0-mreg-rerun-48bc82f
if [ -e "$OUT" ]; then echo "refusing to reuse $OUT" >&2; exit 3; fi
mkdir -p "$OUT/logs"
L=$OUT/logs
stamp() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >> "$L/steps.txt"; }

# Scripts at the freeze commit (the only Git operation of the run; before any check).
git clone --quiet "$BREPO" "$OUT/knotrel-benchmarks"
git -C "$OUT/knotrel-benchmarks" checkout --quiet --detach "$FREEZE"
test "$(git -C "$OUT/knotrel-benchmarks" rev-parse HEAD)" = "$FREEZE"
B=$OUT/knotrel-benchmarks
test -f "$B/results/v0.6.0-qualification/supplement-M/rerun-Mreg/FREEZE-MREG-RERUN.json"
cd "$B"
python3 scripts/run_v060_mreg_rerun.py --out "$OUT/unused" --dry-run > "$L/binaries-verify.json"

# Host prerequisites.
{ date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -2; pmset -g therm; uptime; } > "$L/prelaunch-host.txt"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) echo "not on AC power" >&2; exit 4;; esac
if ! python3 scripts/host_activity_monitor.py --check > "$L/prelaunch-activity.txt"; then
  echo "automated activity present (see $L/prelaunch-activity.txt)" >&2; exit 4
fi

# Quiet period: 300 s of monitoring with no matching process, else stop before measuring.
python3 scripts/git_state_snapshot.py snapshot "$WORKSPACE" "$L/git-state-before.json"
stamp quiet start
python3 scripts/host_activity_monitor.py --out "$L/quiet-monitor.jsonl" & QPID=$!
sleep 300
kill "$QPID"; wait "$QPID" || true
stamp quiet end
if grep -q '"kind": "match"' "$L/quiet-monitor.jsonl"; then
  echo "activity during the quiet period; not measuring" >&2; stamp quiet FAILED; exit 5
fi

# Measurement with continuous monitoring.
python3 scripts/host_activity_monitor.py --out "$L/run-monitor.jsonl" & MPID=$!
stamp Mreg start
STATUS=0
python3 scripts/run_v060_mreg_rerun.py --out "$OUT/Mreg" > "$L/Mreg.log" 2>&1 || STATUS=$?
stamp Mreg "end status $STATUS"
kill "$MPID"; wait "$MPID" || true
python3 scripts/git_state_snapshot.py snapshot "$WORKSPACE" "$L/git-state-after.json"
python3 scripts/git_state_snapshot.py compare "$L/git-state-before.json" "$L/git-state-after.json" "$L/git-state-diff.json" > "$L/git-state-compare.txt"
if [ "$STATUS" -ne 0 ]; then exit 10; fi
python3 scripts/analyze_v060_mreg_rerun.py "$OUT/Mreg" --monitor "$L/run-monitor.jsonl" --quiet "$L/quiet-monitor.jsonl" --git-diff "$L/git-state-diff.json" > "$L/Mreg-analysis.log" 2>&1 || { stamp analysis FAILED; exit 11; }
( cd "$OUT" && find Mreg logs -type f ! -name outputs-sha256.txt -print0 | xargs -0 shasum -a 256 > logs/outputs-sha256.txt )
stamp RUN complete
