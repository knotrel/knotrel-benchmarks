#!/bin/sh
# Prepares a CF5 session (knotrel docs/releases/v1.1.0-cf5-qualification-plan.md, sections 2,
# 4, 8 and 10). It builds everything, writes the tool map and checks the delegated collectors
# with their dry runs. It never measures.
#
# Usage: prepare_cf5.sh CAND_SHA TOOLING_SHA --pre-freeze
#        prepare_cf5.sh CAND_SHA FREEZE_SHA SESSION        (SESSION: 1 or 2)
#
# Builds, one target directory each, with toolchain 1.100.0, --release --locked --offline
# (same flags as v1.0.0's prepare_campaign.sh):
#   ref-server         knotrel-server at v1.0.0 (V2, V3: contention_v100; V1: label B)
#   cand-server        knotrel-server + measure_e2e at the candidate (S1, V1-V3, S3)
#   A-B-harness        the v1.0.0 A harness (knotrel-benchmarks df635a1e) against v1.0.0
#   A-C-harness        the same harness source against the candidate; the lockfiles are derived,
#                      and only the knotrel-core version line changes, as in v1.0.0
#   cand-harness       harness and cf5-core at the tooling commit (K1-K3, K2x, V3)
#   cand-probes        core-lifecycle, http-lifecycle, release-cells (L1, L2, L3)
#   cand-probes-count  core-lifecycle with count-alloc (L2)
#   cand-probes-peak   memory-peak with peak-alloc (K4, L4)
#   contention         contention-probe (S1, V2, V3)
#   feeder             knotrel-pg-feeder + the load tool at the candidate (S3)
# Then: release-binary smoke of both servers; A identities and the two V1 plans (seeds
# declared below); dry runs of V1 (both blocks), L2 and S3; tools.json; binary checksums.
#
# Declared before any CF5 measurement, never derived from results:
#   V1 session seeds 141240 141241 141242 (block 1), 141250 141251 141252 (block 2);
#   L2 order seed 51240.
# Environment overrides: KNOTREL_REPO, BENCH_REPO, EVIDENCE_ROOT, SOURCE_MANIFEST (defaults as in
# results/v1.0.0-qualification/prepare_campaign.sh).
set -eu
CAND=$1
TOOLING=$2
MODE=${3:-}
REF=d38df5f9fb935e95de6f7195d8bb1d5d9a458be9          # knotrel v1.0.0 (published tag)
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675      # core harness used by A since v0.4.0
SOURCE_MANIFEST_SHA256=95dfdabd165863c832473cd756441c0b825a846a64be45367b52901e2f6c8d42
KREPO=${KNOTREL_REPO:-/Users/rt/workspace/knotrel/knotrel}
BREPO=${BENCH_REPO:-/Users/rt/workspace/knotrel/knotrel-benchmarks}
EVIDENCE=${EVIDENCE_ROOT:-/Users/rt/workspace/knotrel/evidence}
SOURCE_MANIFEST=${SOURCE_MANIFEST:-$EVIDENCE/p0-coverage-increment-1-plan-20261030/manifest.json}
for X in "$CAND" "$TOOLING"; do
  echo "$X" | grep -Eq '^[0-9a-f]{40}$' || { echo "commits must be 40-character SHAs" >&2; exit 3; }
done
case "$MODE" in
  --pre-freeze) LABEL=prefreeze ;;
  1|2) LABEL=session$MODE
       git -C "$BREPO" cat-file -e "$TOOLING:results/v1.1.0-cf5/FREEZE.json" 2>/dev/null \
         || { echo "$TOOLING has no results/v1.1.0-cf5/FREEZE.json" >&2; exit 3; } ;;
  *) echo "third argument: --pre-freeze, 1 or 2" >&2; exit 3 ;;
esac
[ "$(shasum -a 256 "$SOURCE_MANIFEST" | cut -d' ' -f1)" = "$SOURCE_MANIFEST_SHA256" ] \
  || { echo "A source manifest $SOURCE_MANIFEST missing or not the recorded one" >&2; exit 3; }
# S3 needs the candidate's load tool to honour LOAD_ENGINE (knotrel#152).
git -C "$KREPO" show "$CAND:integrations/postgres-feeder/examples/load.rs" | grep -q 'LOAD_ENGINE' \
  || { echo "the candidate's load tool has no LOAD_ENGINE" >&2; exit 3; }
C7=$(echo "$CAND" | cut -c1-7)
T7=$(echo "$TOOLING" | cut -c1-7)
CAMP=$EVIDENCE/v1.1.0-cf5-$LABEL-$C7-$T7
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
mkdir -p "$CAMP/logs" "$CAMP/src/cand" "$CAMP/targets" "$CAMP/delegated" \
  "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
trap 'RC=$?; [ "$RC" -eq 0 ] || echo "prepare failed (exit $RC) at $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$L/PREPARE-FAILED.txt"' EXIT
echo "$LABEL" > "$L/prepare-mode.txt"
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$TOOLING"
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

# --- Builds ---
T=$CAMP/targets
B=$CAMP/src/cand/knotrel-benchmarks
P=$B/tools/lifecycle-probes
CB="cargo +1.100.0 build --release --locked --offline"
( cd "$CAMP/A/sources/B/knotrel" && CARGO_TARGET_DIR=$T/ref-server $CB -p knotrel-server --bin knotrel-server ) > "$L/build-ref-server.log" 2>&1
( cd "$CAMP/A/sources/C/knotrel" && CARGO_TARGET_DIR=$T/cand-server $CB -p knotrel-server --bin knotrel-server --example measure_e2e ) > "$L/build-cand-server.log" 2>&1
for X in B C; do
  ( cd "$CAMP/A/build-inputs/$X/knotrel-benchmarks" && CARGO_TARGET_DIR=$T/A-$X-harness $CB -p knotrel-benchmarks --bin knotrel-benchmarks ) > "$L/build-A-$X-harness.log" 2>&1
done
( cd "$B" && CARGO_TARGET_DIR=$T/cand-harness $CB -p knotrel-benchmarks --bin knotrel-benchmarks --bin cf5-core ) > "$L/build-cand-harness.log" 2>&1
( cd "$P" && CARGO_TARGET_DIR=$T/cand-probes $CB --bin core-lifecycle --bin http-lifecycle --bin release-cells ) > "$L/build-cand-probes.log" 2>&1
( cd "$P" && CARGO_TARGET_DIR=$T/cand-probes-count $CB --features count-alloc --bin core-lifecycle ) > "$L/build-cand-probes-count.log" 2>&1
( cd "$P" && CARGO_TARGET_DIR=$T/cand-probes-peak $CB --features peak-alloc --bin memory-peak ) > "$L/build-cand-probes-peak.log" 2>&1
( cd "$B/tools/contention-probe" && CARGO_TARGET_DIR=$T/contention $CB ) > "$L/build-contention.log" 2>&1
( cd "$CAMP/src/cand/knotrel/integrations/postgres-feeder" && CARGO_TARGET_DIR=$T/feeder $CB --bin knotrel-pg-feeder --example load ) > "$L/build-feeder.log" 2>&1

# --- Release-binary smoke tests (deployment check of the servers, not measurements) ---
for X in ref cand; do
  bash "$CAMP/src/cand/knotrel/scripts/smoke-test-release-binary.sh" "$T/$X-server/release/knotrel-server" > "$L/smoke-$X-server.log" 2>&1
done

# --- V1: A identities and both plans (B = v1.0.0, C = candidate), then their dry runs ---
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
CELLS=$(cd "$B" && python3 -c "import sys; sys.path.insert(0, 'scripts'); import run_p0_aa; print(' '.join(run_p0_aa.QUALIFICATION_CELL_IDS))")
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --checkpoint v1.1.0-CF5-V1-Block1 --session-seeds 141240 141241 141242 ) > "$L/A-plan.log" 2>&1
# shellcheck disable=SC2086 # nine cell ids, one word each
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan-block2" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --phase extension --cells $CELLS --checkpoint v1.1.0-CF5-V1-Block2 --session-seeds 141250 141251 141252 ) > "$L/A-plan-block2.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan-block2/manifest.json" --schedule "$CAMP/A/plan-block2/schedule.json" --dry-run ) > "$L/A-block2-dry-run.log" 2>&1

# --- Delegated collectors (run by run_cf5.py at their place in the order) ---
cat > "$CAMP/delegated/V1.sh" <<EOF
#!/bin/sh
# V1: the v1.0.0 A procedure, n = 24 fixed (two blocks of 12 pairs, no interim analysis).
set -eu
cd "$B"
python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --execute "$CAMP/A/raw-main"
python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan-block2/manifest.json" --schedule "$CAMP/A/plan-block2/schedule.json" --execute "$CAMP/A/extension/raw-extension"
EOF
L2_ARGS="--profile final --core $T/cand-probes/release/core-lifecycle --core-count $T/cand-probes-count/release/core-lifecycle --http $T/cand-probes/release/http-lifecycle --order-seed 51240 --knotrel $CAMP/src/cand/knotrel --only C --lifecycle-engines cluster-forest"
# shellcheck disable=SC2086 # L2_ARGS holds paths without spaces
( cd "$B" && python3 scripts/run_lifecycle_qualification.py --out "$CAMP/L2-dry" $L2_ARGS --dry-run ) > "$L/L2-dry-run.log" 2>&1
( cd "$B" && python3 scripts/run_cf5_s3.py run "$CAMP" "$CAMP/S3" --dry-run ) > "$L/S3-dry-run.log" 2>&1

# --- Tool map ---
python3 - "$CAMP" "$L2_ARGS" <<'PY'
import json, shlex, sys
camp, l2 = sys.argv[1], sys.argv[2]
t = f"{camp}/targets"
b = f"{camp}/src/cand/knotrel-benchmarks"
tools = {
    "harness": [f"{t}/cand-harness/release/knotrel-benchmarks"],
    "cf5_core": [f"{t}/cand-harness/release/cf5-core"],
    "memory_peak": [f"{t}/cand-probes-peak/release/memory-peak"],
    "release_cells": [f"{t}/cand-probes/release/release-cells"],
    "http_lifecycle": [f"{t}/cand-probes/release/http-lifecycle"],
    "contention": [f"{t}/contention/release/contention-probe", "--server-bin", f"{t}/cand-server/release/knotrel-server"],
    "contention_v100": [f"{t}/contention/release/contention-probe", "--server-bin", f"{t}/ref-server/release/knotrel-server"],
    "harness_a_candidate": [f"{t}/A-C-harness/release/knotrel-benchmarks"],
    "harness_a_v100": [f"{t}/A-B-harness/release/knotrel-benchmarks"],
    "_delegated": {
        "V1": {"argv": ["/bin/sh", f"{camp}/delegated/V1.sh"], "cwd": b},
        "L2": {"argv": ["python3", "scripts/run_lifecycle_qualification.py", "--out", f"{camp}/L2"] + shlex.split(l2), "cwd": b},
        "S3": {"argv": ["python3", "scripts/run_cf5_s3.py", "run", camp, f"{camp}/S3"], "cwd": b,
               "requires_env": ["KNOTREL_PG_ADMIN_URL"]},
    },
    "_checkouts": {"candidate": f"{camp}/src/cand/knotrel", "benchmarks": b,
                   "v100": f"{camp}/A/sources/B/knotrel", "harness_a": f"{camp}/A/sources/knotrel-benchmarks"},
    "_lockfiles": [f"{camp}/src/cand/knotrel/Cargo.lock", f"{b}/Cargo.lock", f"{b}/tools/lifecycle-probes/Cargo.lock",
                   f"{b}/tools/contention-probe/Cargo.lock", f"{camp}/A/sources/B/knotrel/Cargo.lock",
                   f"{camp}/A/build-inputs/B/knotrel-benchmarks/Cargo.lock",
                   f"{camp}/A/build-inputs/C/knotrel-benchmarks/Cargo.lock"],
}
json.dump(tools, open(f"{camp}/tools.json", "w"), indent=1)
PY

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x -path '*/release/*' ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )
echo "PREPARED ($LABEL) $CAMP"
