#!/bin/sh
# Prepares the frozen v0.7.0 qualification 3 campaign (no measurement).
# Identical to results/v0.7.0-requalification/prepare_campaign.sh (amendment 3, revision 2) except:
# the campaign directory name (v0.7.0-qualification-3-<cand7>-q3-attemptN), the freeze record
# (FREEZE-Q3.json) and series q3 only, the A session seeds (230720-230722), the A plan checkpoint
# name, the qualification-3 launch environment check, and the informational __TEXT,__text
# comparison against the builds of re-qualification attempt a3-3.
#
# Usage: prepare_campaign.sh CAND_SHA FREEZE_SHA [ATTEMPT [SERIES]]
#   CAND_SHA   knotrel candidate commit (full SHA)
#   FREEZE_SHA knotrel-benchmarks commit containing MATRIX.json, PROTOCOL.md and the freeze record
#   ATTEMPT    attempt number (default 1); attempt N >= 2 uses the suffix -attemptN
#   SERIES     q3 (required); the suffix is -q3-attemptN for every N, including 1
# It writes CAMP/LAUNCH-COMMAND.txt: the command the maintainer runs in Terminal.app with Claude
# quit.
#
# Creates /Users/rt/workspace/knotrel/evidence/v0.7.0-qualification-3-<cand7>-q3-attemptN/ (refuses to
# reuse it) with git clones at the recorded commits, derived lockfiles (recorded as diffs),
# every binary of the campaign built with --locked --offline into its own target directory,
# release-binary smoke tests, identities.json for experiment A and its plan, and
# binaries-sha256.txt. Logs go to logs/.
set -eu
CAND=$1
FREEZE=$2
ATTEMPT=${3:-1}
SERIES=${4:-}
REF=5db9ec4738a7f90bf06a83ea12f35c0dab9ab538      # knotrel v0.6.0 (published, signed tag)
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675  # core harness used by A since v0.4.0
KREPO=/Users/rt/workspace/knotrel/knotrel
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
C8=$(echo "$CAND" | cut -c1-7)
CAMP=/Users/rt/workspace/knotrel/evidence/v0.7.0-qualification-3-$C8
LAUNCH=1
# Qualification 3 (PROTOCOL.md sections 7 and 9): FREEZE-Q3, series q3, cap from the frozen matrix,
# no soak, no unrestored quiesce anywhere.
git -C "$BREPO" cat-file -e "$FREEZE:results/v0.7.0-qualification-3/FREEZE-Q3.json" 2>/dev/null \
  || { echo "FREEZE $FREEZE has no results/v0.7.0-qualification-3/FREEZE-Q3.json" >&2; exit 3; }
[ "$SERIES" = q3 ] || { echo "qualification 3: pass ATTEMPT and series q3" >&2; exit 3; }
CAP=$(git -C "$BREPO" show "$FREEZE:results/v0.7.0-qualification-3/MATRIX.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['conformance']['qualification_3']['attempts_cap'])")
case "$ATTEMPT" in [1-9]) ;; *) echo "attempt must be 1-9" >&2; exit 3;; esac
sh "$(dirname "$0")/series_budget.sh" attempt "$ATTEMPT" "$CAP" "$CAMP-$SERIES"-attempt[1-9] || exit 3
sh "$(dirname "$0")/check_restored.sh" || exit 3
CAMP=$CAMP-$SERIES-attempt$ATTEMPT
SOURCE_MANIFEST=/Users/rt/workspace/knotrel/evidence/p0-coverage-increment-1-plan-20261030/manifest.json
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
mkdir -p "$CAMP/logs" "$CAMP/src/ref" "$CAMP/src/cand" "$CAMP/targets" "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
clone "$KREPO" "$CAMP/src/ref/knotrel" "$REF"
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$BREPO" "$CAMP/src/ref/knotrel-benchmarks" "$FREEZE"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$FREEZE"
# Reference probes link knotrel 0.6.0: restore the probe lockfile of knotrel-benchmarks tag
# v0.6.0 (bddef0f3), which resolves knotrel 0.6.0 without sonic-rs.
git -C "$CAMP/src/ref/knotrel-benchmarks" show bddef0f301f582495cb22e47cfd67def88fa9967:tools/lifecycle-probes/Cargo.lock > "$CAMP/src/ref/knotrel-benchmarks/tools/lifecycle-probes/Cargo.lock"
git -C "$CAMP/src/ref/knotrel-benchmarks" diff > "$L/ref-probes-lock-derivation.diff"
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
for X in B C; do
  ( cd "$CAMP/A/build-inputs/$X/knotrel-benchmarks" && CARGO_TARGET_DIR=$T/A-$X-harness cargo +1.100.0 build --release --locked --offline -p knotrel-benchmarks --bin knotrel-benchmarks ) > "$L/build-A-$X-harness.log" 2>&1
done
P=tools/lifecycle-probes
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle --bin http-lifecycle --bin release-cells ) > "$L/build-cand-probes.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes-count cargo +1.100.0 build --release --locked --offline --features count-alloc --bin core-lifecycle ) > "$L/build-cand-probes-count.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/cand-probes-peak cargo +1.100.0 build --release --locked --offline --features peak-alloc --bin memory-peak ) > "$L/build-cand-probes-peak.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/ref-probes cargo +1.100.0 build --release --locked --offline --bin release-cells ) > "$L/build-ref-probes.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/ref-probes-peak cargo +1.100.0 build --release --locked --offline --features peak-alloc --bin memory-peak ) > "$L/build-ref-probes-peak.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/tools/contention-probe" && CARGO_TARGET_DIR=$T/contention cargo +1.100.0 build --release --locked --offline ) > "$L/build-contention.log" 2>&1

# --- Release-binary smoke tests (deployment check of both servers) ---
for X in ref cand; do
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
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --checkpoint v0.7.0-Qualification3-A-Main --session-seeds 230720 230721 230722 ) > "$L/A-plan.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x \( -path '*/release/*' \) ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )
# --- Executed-code identity with the builds of re-qualification attempt a3-3 (information only) ---
FIRST=/Users/rt/workspace/knotrel/evidence/v0.7.0-requalification-e75ff6a-a3-attempt3/targets
for X in cand-server/release/knotrel-server ref-server/release/knotrel-server cand-probes/release/release-cells ref-probes/release/release-cells contention/release/contention-probe; do
  if [ -f "$FIRST/$X" ]; then
    NEW=$(otool -s __TEXT __text "$T/$X" | tail -n +3 | shasum -a 256 | cut -d' ' -f1)
    OLD=$(otool -s __TEXT __text "$FIRST/$X" | tail -n +3 | shasum -a 256 | cut -d' ' -f1)
    echo "$X new=$NEW first=$OLD $( [ "$NEW" = "$OLD" ] && echo identical || echo different )"
  fi
done > "$L/text-section-compare.txt"
if [ -n "$LAUNCH" ]; then
  mkdir -p "$CAMP/bin" && ln -s "$(command -v python3)" "$CAMP/bin/python3"
  # Re-qualification amendment 3, revision 2 (PROTOCOL.md 10.7 there): rustc on the launch PATH.
  ln -s "$(command -v rustc)" "$CAMP/bin/rustc"
  # Every tool and every collector dry run, in a clean environment with the launch PATH.
  env -i HOME="$HOME" USER="${USER:-}" LOGNAME="${LOGNAME:-}" TMPDIR="${TMPDIR:-/tmp}" LANG=C.UTF-8 \
    PATH="$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/sh "$B/results/v0.7.0-qualification-3/launch_env_check.sh" "$CAMP" "$L/launch-env-check.txt"
  sh "$(dirname "$0")/launch_command.sh" "$CAMP" "$CAND" > "$CAMP/LAUNCH-COMMAND.txt"
fi
echo "PREPARED $CAMP"
