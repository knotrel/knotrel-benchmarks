#!/bin/sh
# Prepares and runs the declared v0.6.0 M supplement (PROTOCOL-M-SUPPLEMENT.md).
# Usage: caffeinate -dimsu sh run_m_supplement.sh FREEZE_SHA
#   FREEZE_SHA  knotrel-benchmarks commit that contains FREEZE-M-SUPPLEMENT.json
# Creates /Users/rt/workspace/knotrel/evidence/v0.6.0-m-supplement-48bc82f/ (refuses to
# reuse it), clones knotrel-benchmarks at FREEZE_SHA, builds the probe with
# --locked --offline, verifies the frozen campaign's server binaries against its
# binaries-sha256.txt, then runs M_desc and M_reg supplements and their analyses.
set -eu
FREEZE=$1
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
CAMPAIGN=/Users/rt/workspace/knotrel/evidence/v0.6.0-qualification-48bc82f
OUT=/Users/rt/workspace/knotrel/evidence/v0.6.0-m-supplement-48bc82f
if [ -e "$OUT" ]; then echo "refusing to reuse $OUT" >&2; exit 3; fi
mkdir -p "$OUT/logs" "$OUT/targets"
L=$OUT/logs
stamp() { echo "$1 $(date -u +%Y-%m-%dT%H:%M:%SZ) $2" >> "$L/steps.txt"; }
git clone --quiet "$BREPO" "$OUT/knotrel-benchmarks"
git -C "$OUT/knotrel-benchmarks" checkout --quiet --detach "$FREEZE"
test "$(git -C "$OUT/knotrel-benchmarks" rev-parse HEAD)" = "$FREEZE"
B=$OUT/knotrel-benchmarks
test -f "$B/results/v0.6.0-qualification/supplement-M/FREEZE-M-SUPPLEMENT.json"

# Servers: the frozen campaign's builds, verified in place.
REF_SERVER=$CAMPAIGN/targets/ref-server/release/knotrel-server
CAND_SERVER=$CAMPAIGN/targets/cand-server/release/knotrel-server
( cd "$CAMPAIGN" && grep -E ' targets/(ref|cand)-server/release/knotrel-server$' binaries-sha256.txt > "$L/servers-expected-sha256.txt" && shasum -a 256 -c "$L/servers-expected-sha256.txt" ) > "$L/servers-verify.txt" 2>&1
test "$(grep -c ': OK$' "$L/servers-verify.txt")" = 2

stamp build start
( cd "$B/tools/contention-probe" && CARGO_TARGET_DIR=$OUT/targets/contention cargo +1.100.0 build --release --locked --offline ) > "$L/build-contention.log" 2>&1
stamp build end
PROBE=$OUT/targets/contention/release/contention-probe
shasum -a 256 "$PROBE" "$REF_SERVER" "$CAND_SERVER" > "$OUT/binaries-sha256.txt"

{ date -u +%Y-%m-%dT%H:%M:%SZ; pmset -g batt | head -2; pmset -g therm; uptime; pgrep -lf 'cargo|rustc' || echo no-builds; } > "$L/prelaunch-host.txt"
case "$(pmset -g batt | head -1)" in *"AC Power"*) ;; *) echo "not on AC power" >&2; exit 4;; esac
if pgrep -l 'cargo|rustc' >/dev/null; then echo "build processes running" >&2; exit 4; fi

cd "$B"
stamp Mdesc start
python3 scripts/run_v060_m_supplement.py mdesc --out "$OUT/Mdesc" --probe "$PROBE" --server "$CAND_SERVER" > "$L/Mdesc.log" 2>&1 || { stamp Mdesc FAILED; exit 10; }
stamp Mdesc end
stamp Mreg start
python3 scripts/run_v060_m_supplement.py mreg --out "$OUT/Mreg" --probe "$PROBE" --ref "$REF_SERVER" --cand "$CAND_SERVER" > "$L/Mreg.log" 2>&1 || { stamp Mreg FAILED; exit 11; }
stamp Mreg end
python3 scripts/analyze_v060_m_supplement.py mdesc "$OUT/Mdesc" > "$L/Mdesc-analysis.log" 2>&1 || { stamp Mdesc-analysis FAILED; exit 12; }
python3 scripts/analyze_v060_m_supplement.py mreg "$OUT/Mreg" > "$L/Mreg-analysis.log" 2>&1 || { stamp Mreg-analysis FAILED; exit 13; }
( cd "$OUT" && find Mdesc Mreg -type f -print0 | xargs -0 shasum -a 256 > logs/outputs-sha256.txt )
stamp RUN complete
