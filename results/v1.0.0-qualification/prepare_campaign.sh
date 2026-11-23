#!/bin/sh
# Prepares the v1.0.0 qualification campaign (no measurement); PROTOCOL.md section 5.
# Derived from results/v0.9.0-qualification/prepare_campaign.sh. The builds, flags, toolchain,
# A identities, smoke tests and checksums are the same; what differs:
#   - reference: knotrel v0.9.0 (was v0.7.0); its probes (release-cells, memory-peak, and the
#     core-lifecycle builds used by the core rule and, if it triggers, by T5 arm B) are built from
#     a clean knotrel-benchmarks clone at BASE_PROBES, whose probe lockfile resolves knotrel 0.9.0
#     and whose probe source equals the tooling commit's (only the two knotrel version lines of
#     tools/lifecycle-probes/Cargo.lock differ);
#   - the candidate is a parameter (CAND_SHA), never hard-coded; the freeze record must name it;
#   - A: both blocks are planned here (block 1: A/plan, session seeds; block 2: A/plan-block2,
#     the plan generator's extension phase with all nine cells, extension seeds), and both are
#     dry-run; nothing in the chain reads A data (plan section 5.3);
#   - the core rule (plan section 4.3) is computed from these builds (logs/core-rule.json); its
#     outcome and per-pair identical booleans must equal those of the pre-freeze file named by
#     FREEZE.json core_rule.comparison (whose SHA-256 is checked); digests may differ, since the
#     builds embed the campaign directory's path (logs/core-rule-agreement.json records both);
#   - attempt mode checks the freeze record with the freeze commit's freeze_check_v100q.py and
#     verifies the helpers it runs from its own directory against the record (N6); the attempt
#     budget is attempt_budget.sh (series_budget.sh plus the plan section 5.5 failure rule);
#   - the probe lockfile must name the candidate's Cargo.toml version (checked before the
#     campaign directory is created);
#   - the probe compatibility check (plan section 13 item 6, functional only) runs on these
#     builds (logs/probe-compat/);
#   - no v0.8.0 builds (no Part 2, no block D); Q uses the reference server targets/ref-server for
#     its Q5 arm and the feeder and load tool built at the candidate (targets/feeder);
#   - campaign directory EVIDENCE/v1.0.0-qualification-<cand7>-attemptN, attempts cap from the
#     matrix (2).
#
# Usage: prepare_campaign.sh CAND_SHA FREEZE_SHA ATTEMPT
#        prepare_campaign.sh CAND_SHA TOOLING_SHA --pre-freeze
# --pre-freeze is the verification before the freeze (PROTOCOL.md section 5, step 1): it does
# everything above in EVIDENCE/v1.0.0-prefreeze-<cand7>-<tooling7> without a freeze record or an
# attempt number, and its launch environment check expects the runner to refuse (not frozen).
# Its core-rule and probe-compatibility outputs are inputs of the freeze record.
# Environment overrides (defaults in brackets): KNOTREL_REPO [/Users/rt/workspace/knotrel/knotrel],
# BENCH_REPO [/Users/rt/workspace/knotrel/knotrel-benchmarks], EVIDENCE_ROOT
# [/Users/rt/workspace/knotrel/evidence], SOURCE_MANIFEST [EVIDENCE_ROOT/p0-coverage-increment-1-
# plan-20261030/manifest.json; its SHA-256 is checked].
set -eu
CAND=$1
FREEZE=$2
ATTEMPT=${3:-1}
REF=223f04c10b0af663b54e269e0970ee10ac1dc6b2          # knotrel v0.9.0 (published tag); plan section 2
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675      # core harness used by A since v0.4.0
BASE_PROBES=53c50e962983886bd7442012aa4c2f561cb5a3fa  # knotrel-benchmarks: probe lockfile for knotrel 0.9.0
SOURCE_MANIFEST_SHA256=95dfdabd165863c832473cd756441c0b825a846a64be45367b52901e2f6c8d42
KREPO=${KNOTREL_REPO:-/Users/rt/workspace/knotrel/knotrel}
BREPO=${BENCH_REPO:-/Users/rt/workspace/knotrel/knotrel-benchmarks}
EVIDENCE=${EVIDENCE_ROOT:-/Users/rt/workspace/knotrel/evidence}
SOURCE_MANIFEST=${SOURCE_MANIFEST:-$EVIDENCE/p0-coverage-increment-1-plan-20261030/manifest.json}
DIR=results/v1.0.0-qualification
HERE=$(cd "$(dirname "$0")" && pwd)
echo "$CAND" | grep -Eq '^[0-9a-f]{40}$' || { echo "CAND_SHA must be a 40-character commit" >&2; exit 3; }
C7=$(echo "$CAND" | cut -c1-7)
[ "$(shasum -a 256 "$SOURCE_MANIFEST" | cut -d' ' -f1)" = "$SOURCE_MANIFEST_SHA256" ] \
  || { echo "A source manifest $SOURCE_MANIFEST missing or not the recorded one" >&2; exit 3; }
if [ "$ATTEMPT" = "--pre-freeze" ]; then
  MODE=prefreeze
  CAMP=$EVIDENCE/v1.0.0-prefreeze-$C7-$(echo "$FREEZE" | cut -c1-7)
else
  MODE=attempt
  git -C "$BREPO" cat-file -e "$FREEZE:$DIR/FREEZE.json" 2>/dev/null \
    || { echo "FREEZE $FREEZE has no $DIR/FREEZE.json" >&2; exit 3; }
  # The freeze guards (scripts/freeze_check_v100q.py), run from the freeze commit itself: the
  # record (candidate, reference, core-rule outcome, the pre-freeze core-rule.json and its
  # SHA-256 under EVIDENCE_ROOT or KNOTREL_PREFREEZE_CORE_RULE, a hash list equal to
  # its hashed files and covering the required files), every file's hash in the freeze tree,
  # the freeze commit as the only child of tooling.commit adding only FREEZE.json, and the
  # helpers this script runs from its own directory (finding N6) equal to the record.
  FC=$(mktemp -d)
  for X in freeze_check_v100q.py cli_paths.py; do
    git -C "$BREPO" show "$FREEZE:scripts/$X" > "$FC/$X" 2>/dev/null \
      || { echo "FREEZE $FREEZE has no scripts/$X" >&2; rm -rf "$FC"; exit 3; }
  done
  FCRC=0
  LIFECYCLE_QUALIFICATION_ROOTS="$BREPO:$(cd "$HERE/../.." && pwd):$EVIDENCE" python3 "$FC/freeze_check_v100q.py" record \
    --repo "$BREPO" --freeze "$FREEZE" --cand "$CAND" --evidence-root "$EVIDENCE" --local-root "$HERE/../.." --local "$DIR/prepare_campaign.sh" \
    --local "$DIR/series_budget.sh" --local "$DIR/attempt_budget.sh" --local "$DIR/check_restored.sh" \
    --local "$DIR/launch_command.sh" || FCRC=$?
  rm -rf "$FC"
  [ "$FCRC" -eq 0 ] || exit 3
  CAP=$(git -C "$BREPO" show "$FREEZE:$DIR/MATRIX.json" | python3 -c "import json,sys;print(json.load(sys.stdin)['conformance']['qualification_3']['attempts_cap'])")
  case "$ATTEMPT" in [1-9]) ;; *) echo "attempt must be 1-9" >&2; exit 3;; esac
  CAMP=$EVIDENCE/v1.0.0-qualification-$C7
  # series_budget.sh unchanged, then the v1.0 rule: no second attempt after a product failure.
  sh "$HERE/attempt_budget.sh" attempt "$ATTEMPT" "$CAP" "$CAMP"-attempt[1-9] || exit 3
  sh "$HERE/check_restored.sh" || exit 3
  CAMP=$CAMP-attempt$ATTEMPT
fi
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
# The probe lockfile of the tooling commit must name the candidate's knotrel version (the
# workspace version of its Cargo.toml) for knotrel-core and knotrel-server, and in attempt mode
# the freeze record's candidate.version must be that version too. Checked from Git, before the
# campaign directory exists (finding S3: a refused prepare leaves no directory behind).
CAND_VERSION=$(git -C "$KREPO" show "$CAND:Cargo.toml" | grep -m1 '^version' | cut -d'"' -f2)
git -C "$BREPO" show "$FREEZE:tools/lifecycle-probes/Cargo.lock" | python3 -c "
import json, re, subprocess, sys
want, mode, repo, freeze = sys.argv[1:]
lock = sys.stdin.read()
problems = []
for name in ('knotrel-core', 'knotrel-server'):
    found = re.findall(r'name = \"%s\"\nversion = \"([^\"]+)\"' % name, lock)
    if found != [want]:
        problems.append('probe lockfile %s versions %s, expected the candidate version %s' % (name, found, want))
if mode == 'attempt':
    record = json.loads(subprocess.run(['git', '-C', repo, 'show', freeze + ':results/v1.0.0-qualification/FREEZE.json'],
                                       capture_output=True, text=True, check=True).stdout)
    if record.get('candidate', {}).get('version') != want:
        problems.append('freeze candidate.version %s is not the candidate Cargo.toml version %s' % (record.get('candidate', {}).get('version'), want))
for p in problems: print(p, file=sys.stderr)
sys.exit(1 if problems else 0)
" "$CAND_VERSION" "$MODE" "$BREPO" "$FREEZE" || exit 3
mkdir -p "$CAMP/logs" "$CAMP/src/ref" "$CAMP/src/cand" "$CAMP/targets" "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
# From here a failure leaves a directory that was never launched: record where it stopped
# (PROTOCOL.md section 5, step 3, for the recovery).
trap 'RC=$?; [ "$RC" -eq 0 ] || echo "prepare failed (exit $RC) at $(date -u +%Y-%m-%dT%H:%M:%SZ); never launched" > "$L/PREPARE-FAILED.txt"' EXIT
echo "$MODE" > "$L/prepare-mode.txt"
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
clone "$KREPO" "$CAMP/src/ref/knotrel" "$REF"
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$BREPO" "$CAMP/src/ref/knotrel-benchmarks" "$BASE_PROBES"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$FREEZE"
# The two probe trees must be the same source; only the two knotrel version lines of the lockfile
# may differ (0.9.0 in the reference tree, the candidate's version in the tooling tree, checked above).
git -C "$CAMP/src/cand/knotrel-benchmarks" diff "$BASE_PROBES" "$FREEZE" -- tools/lifecycle-probes > "$L/probes-ref-vs-tooling.diff"
test "$(grep -c '^[+-]version = "' "$L/probes-ref-vs-tooling.diff")" -eq 4
test "$(grep '^[+-]' "$L/probes-ref-vs-tooling.diff" | grep -vc '^[+-][+-]')" -eq 4
# Experiment A: same layout as v0.9.0 (sources/{B,C}/knotrel, harness at $HARNESS).
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
# Reference core probes: the core rule compares them with the candidate's; T5 arm B if it triggers.
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/t5base-probes cargo +1.100.0 build --release --locked --offline --bin core-lifecycle ) > "$L/build-t5base-probes.log" 2>&1
( cd "$CAMP/src/ref/knotrel-benchmarks/$P" && CARGO_TARGET_DIR=$T/ref-probes-count cargo +1.100.0 build --release --locked --offline --features count-alloc --bin core-lifecycle ) > "$L/build-ref-probes-count.log" 2>&1
( cd "$CAMP/src/cand/knotrel-benchmarks/tools/contention-probe" && CARGO_TARGET_DIR=$T/contention cargo +1.100.0 build --release --locked --offline ) > "$L/build-contention.log" 2>&1
( cd "$CAMP/src/cand/knotrel/integrations/postgres-feeder" && CARGO_TARGET_DIR=$T/feeder cargo +1.100.0 build --release --locked --offline --bin knotrel-pg-feeder --example load ) > "$L/build-feeder.log" 2>&1

# --- Release-binary smoke tests (deployment check of the servers, not measurements) ---
for X in ref cand; do
  bash "$CAMP/src/cand/knotrel/scripts/smoke-test-release-binary.sh" "$T/$X-server/release/knotrel-server" > "$L/smoke-$X-server.log" 2>&1
done

# --- Identities and both plans of experiment A ---
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
CELLS=$(cd "$B" && python3 -c "import sys; sys.path.insert(0, 'scripts'); import run_p0_aa; print(' '.join(run_p0_aa.QUALIFICATION_CELL_IDS))")
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --checkpoint v1.0.0-Qualification-A-Block1 --session-seeds 130720 130721 130722 ) > "$L/A-plan.log" 2>&1
# shellcheck disable=SC2086 # nine cell ids, one word each
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan-block2" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --phase extension --cells $CELLS --checkpoint v1.0.0-Qualification-A-Block2 --session-seeds 130730 130731 130732 ) > "$L/A-plan-block2.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan-block2/manifest.json" --schedule "$CAMP/A/plan-block2/schedule.json" --dry-run ) > "$L/A-block2-dry-run.log" 2>&1

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x \( -path '*/release/*' \) ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )

# --- Core rule (plan section 4.3) and probe compatibility (plan section 13 item 6) ---
LIFECYCLE_QUALIFICATION_ROOTS="$EVIDENCE" python3 "$B/scripts/core_rule_v100q.py" "$CAMP" "$L/core-rule.json" > "$L/core-rule.log" 2>&1
OUTCOME=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['outcome'])" "$L/core-rule.json")
echo "core rule: $OUTCOME"
if [ "$MODE" = attempt ]; then
  # Same outcome and per-pair identical booleans as the pre-freeze file (digests may differ);
  # writes logs/core-rule-agreement.json with this attempt's core-rule.json SHA-256.
  LIFECYCLE_QUALIFICATION_ROOTS="$EVIDENCE" python3 "$B/scripts/freeze_check_v100q.py" core-rule "$CAMP" \
    --evidence-root "$EVIDENCE" --write \
    || { echo "core rule differs from the freeze record's" >&2; exit 3; }
fi
( cd "$B" && LIFECYCLE_QUALIFICATION_ROOTS="$EVIDENCE" python3 scripts/probe_compat_v100q.py "$CAMP" "$L/probe-compat" ) > "$L/probe-compat.log" 2>&1 \
  || { echo "probe compatibility check failed (see $L/probe-compat.log)" >&2; exit 3; }

# --- Launch environment: every program and every collector dry run, launch PATH, clean env ---
mkdir -p "$CAMP/bin" && ln -s "$(command -v python3)" "$CAMP/bin/python3"
ln -s "$(command -v rustc)" "$CAMP/bin/rustc"
env -i HOME="$HOME" USER="${USER:-}" LOGNAME="${LOGNAME:-}" TMPDIR="${TMPDIR:-/tmp}" LANG=C.UTF-8 \
  ${KNOTREL_PREFREEZE_CORE_RULE:+KNOTREL_PREFREEZE_CORE_RULE="$KNOTREL_PREFREEZE_CORE_RULE"} \
  LAUNCH_ENV_MODE="$MODE" PATH="$CAMP/bin:/usr/bin:/bin:/usr/sbin:/sbin" /bin/sh "$B/$DIR/launch_env_check.sh" "$CAMP" "$L/launch-env-check.txt"
sh "$HERE/launch_command.sh" "$CAMP" "$CAND" > "$CAMP/LAUNCH-COMMAND.txt"
echo "PREPARED ($MODE) $CAMP"
