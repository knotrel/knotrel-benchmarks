#!/bin/sh
# Prepares the frozen v0.6.0 final-qualification campaign (no measurement).
#
# Usage: prepare_campaign.sh CAND_SHA FREEZE_SHA
#   CAND_SHA   knotrel candidate commit (full SHA)
#   FREEZE_SHA knotrel-benchmarks commit containing MATRIX.json, PROTOCOL.md and FREEZE.json
#
# Creates /Users/rt/workspace/knotrel/evidence/v0.6.0-qualification-<cand8>/ (refuses to
# reuse it) with git clones at the recorded commits, derived lockfiles (recorded as diffs),
# every binary of the campaign built with --locked --offline into its own target directory,
# release-binary smoke tests, identities.json for experiment A and its plan, and
# binaries-sha256.txt. Logs go to logs/.
set -eu
CAND=$1
FREEZE=$2
REF=51e3b4da2de802a4ebf352b1e8a8311657e48d38      # knotrel v0.5.0 (published)
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675  # core harness used by A since v0.4.0
KREPO=/Users/rt/workspace/knotrel/knotrel
BREPO=/Users/rt/workspace/knotrel/knotrel-benchmarks
C8=$(echo "$CAND" | cut -c1-7)
CAMP=/Users/rt/workspace/knotrel/evidence/v0.6.0-qualification-$C8
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
mkdir -p "$CAMP/logs" "$CAMP/src/ref" "$CAMP/src/cand" "$CAMP/targets" "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
clone "$KREPO" "$CAMP/src/ref/knotrel" "$REF"
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$BREPO" "$CAMP/src/ref/knotrel-benchmarks" "$FREEZE"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$FREEZE"
# Reference probes link knotrel 0.5.0: restore the v0.5.0 probe lockfile (identical to the
# tooling lockfile before the 0.6.0 version bump, commit c9ab3614).
git -C "$CAMP/src/ref/knotrel-benchmarks" show 7ce6abb726ef3112604df2ceaff7b4a7ef21c328:tools/lifecycle-probes/Cargo.lock > "$CAMP/src/ref/knotrel-benchmarks/tools/lifecycle-probes/Cargo.lock"
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
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --checkpoint v0.6.0-Qualification-A-Main --session-seeds 130600 130601 130602 ) > "$L/A-plan.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x \( -path '*/release/*' \) ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )
echo "PREPARED $CAMP"
