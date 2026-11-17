#!/bin/sh
# Runs the frozen v0.7.0 final qualification in one chain: A (main, extension if
# required), B/C, R, Rmem, M_desc, M_reg. Run under: caffeinate -dimsu sh run_final_chain.sh CAMP CAND_SHA
# The operator runs nothing else until it completes. Every step's exit status is logged;
# the chain stops at the first failing collector.
set -u
CAMP=$1
CAND=$2
REF=5db9ec4738a7f90bf06a83ea12f35c0dab9ab538
B=$CAMP/src/cand/knotrel-benchmarks
T=$CAMP/targets
L=$CAMP/logs
A=$CAMP/A
export LIFECYCLE_QUALIFICATION_ROOTS=/Users/rt/workspace/knotrel/evidence
cd "$B" || exit 2
for f in "$A/raw-main" "$CAMP/BC" "$CAMP/R" "$CAMP/Rmem" "$CAMP/Mdesc" "$CAMP/Mreg"; do
  if [ -e "$f" ]; then echo "refusing to relaunch: $f exists" >&2; exit 3; fi
done
stamp() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >> "$L/chain-steps.txt"; }
{ date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -2; pmset -g therm; uptime; pgrep -lf 'cargo|rustc' || echo no-builds; } > "$L/prelaunch-host.txt"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) echo "not on AC power" >&2; exit 4;; esac
if pgrep -l 'cargo|rustc' >/dev/null; then echo "build processes running" >&2; exit 4; fi
if ! python3 scripts/host_activity_monitor.py --check > "$L/prelaunch-activity.txt"; then echo "host activity (IDE/git) present" >&2; exit 4; fi
# Continuous activity sampling for the whole chain (output inside the tooling clone, copied to logs at the end).
python3 scripts/host_activity_monitor.py --out activity-monitor.jsonl &
MON=$!

stamp A-main start
python3 scripts/run_p0_aa.py --manifest "$A/plan/manifest.json" --schedule "$A/plan/schedule.json" --execute "$A/raw-main" > "$L/A-main-run.log" 2>&1 || { stamp A-main FAILED; exit 5; }
stamp A-main end
python3 scripts/analyze_bc_qualification.py --main "$A/raw-main" --rules v0.4.0 --output "$A/decision-analysis-main.json" > "$L/A-analysis-main.log" 2>&1 || { stamp A-analysis FAILED; exit 5; }
CELLS=$(python3 -c "import json;print(' '.join(json.load(open('$A/decision-analysis-main.json'))['extension_cells_required']))")
if [ -n "$CELLS" ]; then
  stamp A-extension "start cells: $CELLS"
  python3 scripts/prepare_bc_qualification.py "$A/extension/plan" --identities "$A/identities.json" --phase extension --cells $CELLS --checkpoint v0.7.0-Qualification-A-Extension --session-seeds 130710 130711 130712 > "$L/A-extension-plan.log" 2>&1 || { stamp A-extension-plan FAILED; exit 6; }
  python3 scripts/run_p0_aa.py --manifest "$A/extension/plan/manifest.json" --schedule "$A/extension/plan/schedule.json" --execute "$A/extension/raw-extension" > "$L/A-extension-run.log" 2>&1 || { stamp A-extension FAILED; exit 6; }
  stamp A-extension end
  python3 scripts/analyze_bc_qualification.py --main "$A/raw-main" --extension "$A/extension/raw-extension" --rules v0.4.0 --output "$A/final-decision-analysis.json" > "$L/A-analysis-final.log" 2>&1 || { stamp A-analysis-final FAILED; exit 6; }
else
  stamp A-extension "none required"
  cp "$A/decision-analysis-main.json" "$A/final-decision-analysis.json"
fi

stamp BC start
python3 scripts/run_lifecycle_qualification.py --out "$CAMP/BC" --profile final --core "$T/cand-probes/release/core-lifecycle" --core-count "$T/cand-probes-count/release/core-lifecycle" --http "$T/cand-probes/release/http-lifecycle" --order-seed 50700 --knotrel "$CAMP/src/cand/knotrel" --lifecycle-engines compact-bfs --window-multipliers results/lifecycle-qualification-v0.5.0/window-multipliers-dcd8ccc.json > "$L/BC.log" 2>&1 || { stamp BC FAILED; exit 7; }
stamp BC end

stamp R start
python3 scripts/run_v070_qualification.py r --out "$CAMP/R" --ref "$T/ref-probes/release/release-cells" --cand "$T/cand-probes/release/release-cells" > "$L/R.log" 2>&1 || { stamp R FAILED; exit 8; }
stamp R end
stamp Rmem start
python3 scripts/run_v070_qualification.py rmem --out "$CAMP/Rmem" --ref "$T/ref-probes-peak/release/memory-peak" --cand "$T/cand-probes-peak/release/memory-peak" > "$L/Rmem.log" 2>&1 || { stamp Rmem FAILED; exit 9; }
stamp Rmem end
stamp Mdesc start
python3 scripts/run_v070_qualification.py mdesc --out "$CAMP/Mdesc" --probe "$T/contention/release/contention-probe" --server "$T/cand-server/release/knotrel-server" > "$L/Mdesc.log" 2>&1 || { stamp Mdesc FAILED; exit 10; }
stamp Mdesc end
stamp Mreg start
python3 scripts/run_v070_qualification.py mreg --out "$CAMP/Mreg" --probe "$T/contention/release/contention-probe" --ref "$T/ref-server/release/knotrel-server" --cand "$T/cand-server/release/knotrel-server" > "$L/Mreg.log" 2>&1 || { stamp Mreg FAILED; exit 11; }
stamp Mreg end
kill $MON; wait $MON 2>/dev/null; cp activity-monitor.jsonl "$L/activity-monitor.jsonl"
( cd "$CAMP" && find A BC R Rmem Mdesc Mreg -type f -print0 2>/dev/null | xargs -0 shasum -a 256 > logs/outputs-sha256.txt )
stamp CHAIN complete
