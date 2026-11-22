#!/bin/sh
# Prepares the frozen v0.9.0 qualification campaign (no measurement); PROTOCOL.md section 5.
# Derived from results/v0.7.0-qualification-3/prepare_campaign.sh. The builds, flags, toolchain,
# A identities and plan, smoke tests and checksums are the same; what differs:
#   - reference: knotrel v0.7.0 (was v0.6.0); its probes (release-cells, memory-peak and the T5
#     arm-B core-lifecycle) are built from a clean knotrel-benchmarks clone at BASE_PROBES, whose
#     probe lockfile resolves knotrel 0.7.0 and whose probe source equals the freeze commit's
#     (no lockfile derivation, so the T5 base build is not dirty);
#   - T5 arm B is that v0.7.0 build (targets/t5base-probes), replacing the e75ff6a build;
#   - Part 2 (descriptive): knotrel v0.8.0 server (targets/v080-server) and http-lifecycle and
#     core-lifecycle built against v0.8.0 from a clean clone at V080_PROBES (targets/v080-probes);
#   - Part 3: the feeder and its load tool at the candidate (targets/feeder);
#   - campaign directory evidence/v0.9.0-qualification-<cand7>-attemptN, attempts cap from the
#     matrix (2); no __TEXT comparison with an earlier campaign (different commits).
#
# Usage: prepare_campaign.sh CAND_SHA FREEZE_SHA ATTEMPT
set -eu
CAND=$1
FREEZE=$2
ATTEMPT=${3:-1}
REF=9f933a783b043f9f44fd5de014c3c8a93c7922c3          # knotrel v0.7.0 (published tag)
V080=e3fc7361caf2f29dcf6870e8018b96414ebd927b         # knotrel v0.8.0 (published tag)
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675      # core harness used by A since v0.4.0
BASE_PROBES=7116c32e7c3351a995048713032745117fc7df7b  # knotrel-benchmarks: probe lockfile for knotrel 0.7.0
V080_PROBES=e843aae2fd6d74a03b834dfe84f9367d7bc897a3  # knotrel-benchmarks: probe lockfile for knotrel 0.8.0
KREPO=/Users/rt/workspace/knotrel/knotrel
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
DIR=results/v0.9.0-qualification
C7=$(echo "$CAND" | cut -c1-7)
CAMP=/Users/rt/workspace/knotrel/evidence/v0.9.0-qualification-$C7
git -C "$BREPO" cat-file -e "$FREEZE:$DIR/FREEZE.json" 2>/dev/null \
  || { echo "FREEZE $FREEZE has no $DIR/FREEZE.json" >&2; exit 3; }
CAP=$(git -C "$BREPO" show "$FREEZE:$DIR/MATRIX.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['conformance']['qualification_3']['attempts_cap'])")
case "$ATTEMPT" in [1-9]) ;; *) echo "attempt must be 1-9" >&2; exit 3;; esac
sh "$(dirname "$0")/series_budget.sh" attempt "$ATTEMPT" "$CAP" "$CAMP"-attempt[1-9] || exit 3
sh "$(dirname "$0")/check_restored.sh" || exit 3
CAMP=$CAMP-attempt$ATTEMPT
SOURCE_MANIFEST=/Users/rt/workspace/knotrel/evidence/p0-coverage-increment-1-plan-20261030/manifest.json
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
mkdir -p "$CAMP/logs" "$CAMP/src/ref" "$CAMP/src/cand" "$CAMP/src/v080" "$CAMP/targets" "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
clone "$KREPO" "$CAMP/src/ref/knotrel" "$REF"
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$KREPO" "$CAMP/src/v080/knotrel" "$V080"
clone "$BREPO" "$CAMP/src/ref/knotrel-benchmarks" "$BASE_PROBES"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$FREEZE"
clone "$BREPO" "$CAMP/src/v080/knotrel-benchmarks" "$V080_PROBES"
# The three probe trees must be the same source; only the two knotrel version lines of the
# lockfile may differ (recorded, and checked again by analyze_v090q_t5.py).
for X in ref v080; do
  git -C "$CAMP/src/cand/knotrel-benchmarks" diff "$(git -C "$CAMP/src/$X/knotrel-benchmarks" rev-parse HEAD)" "$FREEZE" -- tools/lifecycle-probes > "$L/probes-$X-vs-freeze.diff"
  test "$(grep -c '^[+-]version = "0\.' "$L/probes-$X-vs-freeze.diff")" -eq 4
  test "$(grep '^[+-]' "$L/probes-$X-vs-freeze.diff" | grep -vc '^[+-][+-]')" -eq 4
done
# Experiment A: same layout as v0.5.0 (sources/{B,C}/knotrel, harness at $HARNESS).
clone "$KREPO" "$CAMP/A/sources/B/knotrel" "$REF"
clone "$KREPO" "$CAMP/A/sources/C/knotrel" "$CAND"
clone "$BREPO" "$CAMP/A/sources/knotrel-benchmarks" "$HARNESS"
for X in B C; do
  V=$(grep -m1 '^version' "$CAMP/A/sources/$X/knotrel/Cargo.toml" | cut -d'"' -f2)
  I=$CAMP/A/build-inputs/$X/knotrel-benchmarks
  mkdir -p "$I"
  cp -R "$CAMP/A/sources/knotrel-benchmarks/Cargo.toml" "$CAMP/A/sources/knotrel-benchmarks/crates" "$CAMP/A/sources/knotrel-benchmarks/rust-toolchain.toml" "$I/"
  python3 - "$CAMP/A/sources/knotrel-benchmarks/Cargo.lock" "$I/Cargo.lock" "$V" <<'PY'
import re, sys
src, dst, version = sys.argv[1:]
text = open(src).read()
new, count = re.subn(r'(name = "knotrel-core"\nversion = ")[^"]+(")', r'\g<1>' + version + r'\2', text)
assert count == 1, count
open(dst, "w").write(new)
PY
  diff "$CAMP/A/sources/knotrel-benchmarks/Cargo.lock" "$I/Cargo.lock" > "$L/A-$X-harness-lock-derivation.diff" || true
  ln -s "../../sources/$X/knotrel" "$CAMP/A/build-inputs/$X/knotrel"
done

# --- Builds (each into its own target directory) ---
T=$CAMP/targets
( cd "$CAMP/A/sources/B/knotrel" && CARGO_TARGET_DIR=$T/ref-server cargo +1.100.0 build --release --locked --offline -p knotrel-server --bin knotrel-server ) > "$L/build-ref-server.log" 2>&1
( cd "$CAMP/A/sources/C/knotrel" && CARGO_TARGET_DIR=$T/cand-server cargo +1.100.0 build --release --locked --offline -p knotrel-server --bin knotrel-server --example measure_e2e ) > "$L/build-cand-server.log" 2>&1
( cd "$CAMP/src/v080/knotrel" && CARGO_TARGET_DIR=$T/v080-server cargo +1.100.0 build --release --locked --offline -p knotrel-server --bin knotrel-server ) > "$L/build-v080-server.log" 2>&1
for X in B C; do
  ( cd "$CAMP/A/build-inputs/$X/knotrel-benchmarks" && CARGO_TARGET_DIR=$T/A-$X-harness cargo +1.100.0 build --release --locked --offline -p knotrel-benchmarks --bin knotrel-benchmarks ) > "$L/build-A-$X-harness.log" 2>&1
done
P=tools/lifecycle-probes
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle --bin http-lifecycle --bin release-cells ) > "$L/build-cand-probes.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/t5base-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle ) > "$L/build-t5base-probes.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes-count cargo +1.100.0 build --release --locked --offline --features count-alloc --bin core-lifecycle ) > "$L/build-cand-probes-count.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes-peak cargo +1.100.0 build --release --locked --offline --features peak-alloc --bin memory-peak ) > "$L/build-cand-probes-peak.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/ref-probes cargo +1.100.0 build --release --locked --offline --bin release-cells ) > "$L/build-ref-probes.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/ref-probes-peak cargo +1.100.0 build --release --locked --offline --features peak-alloc --bin memory-peak ) > "$L/build-ref-probes-peak.log" 2>&1
( cd "$CAMP/src/v080/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/v080-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle --bin http-lifecycle ) > "$L/build-v080-probes.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/tools/contention-probe" && CARGO_TARGET_DIR=$T/contention cargo +1.100.0 build --release --locked --offline ) > "$L/build-contention.log" 2>&1
( cd "$CAMP/src/cand/knotrel/integrations/postgres-feeder" && CARGO_TARGET_DIR=$T/feeder cargo +1.100.0 build --release --locked --offline --bin knotrel-pg-feeder --example load ) > "$L/build-feeder.log" 2>&1

# --- Release-binary smoke tests (deployment check of the servers) ---
for X in ref cand v080; do
  bash "$CAMP/src/cand/knotrel/scripts/smoke-test-release-binary.sh" "$T/$X-server/release/knotrel-server" > "$L/smoke-$X-server.log" 2>&1
done

# --- Identities and plan for experiment A ---
python3 - "$CAMP" "$REF" "$CAND" "$HARNESS" <<'PY'
import hashlib, json, sys
camp, ref, cand, harness = sys.argv[1:]
h = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
ids = {"comparison_identities": {}, "shared_binaries": {}}
for label, commit, server in (("B", ref, "ref-server"), ("C", cand, "cand-server")):
    k = f"{camp}/A/sources/{label}/knotrel"
    hb = f"{camp}/targets/A-{label}-harness/release/knotrel-benchmarks"
    sb = f"{camp}/targets/{server}/release/knotrel-server"
    lock = f"{camp}/A/build-inputs/{label}/knotrel-benchmarks/Cargo.lock"
    ids["comparison_identities"][label] = {
        "binaries": {"knotrel_benchmarks": {"path": hb, "sha256": h(hb), "source_commit": harness},
                     "knotrel_server": {"path": sb, "sha256": h(sb), "source_commit": commit}},
        "checkouts": {"benchmarks_source": {"commit": harness, "path": f"{camp}/A/sources/knotrel-benchmarks"},
                      "knotrel_source": {"commit": commit, "path": k}},
        "lockfiles": {"benchmarks_lock_derived": {"path": lock, "sha256": h(lock)},
                      "knotrel_lock": {"path": f"{k}/Cargo.lock", "sha256": h(f"{k}/Cargo.lock")}}}
m = f"{camp}/targets/cand-server/release/examples/measure_e2e"
ids["shared_binaries"]["measure_e2e"] = {"path": m, "sha256": h(m), "source_checkout": f"{camp}/A/sources/C/knotrel"}
json.dump(ids, open(f"{camp}/A/identities.json", "w"), indent=1)
PY
B=$CAMP/src/cand/knotrel-benchmarks
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --checkpoint v0.9.0-Qualification-A-Main --session-seeds 130720 130721 130722 ) > "$L/A-plan.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x \( -path '*/release/*' \) ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )
mkdir -p "$CAMP/bin" && ln -s "$(command -v python3)" "$CAMP/bin/python3"
ln -s "$(command -v rustc)" "$CAMP/bin/rustc"
env -i HOME="$HOME" USER="${USER:-}" LOGNAME="${LOGNAME:-}" TMPDIR="${TMPDIR:-/tmp}" LANG=C.UTF-8 \
  PATH="$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/sh "$B/$DIR/launch_env_check.sh" "$CAMP" "$L/launch-env-check.txt"
sh "$(dirname "$0")/launch_command.sh" "$CAMP" "$CAND" > "$CAMP/LAUNCH-COMMAND.txt"
echo "PREPARED $CAMP"
