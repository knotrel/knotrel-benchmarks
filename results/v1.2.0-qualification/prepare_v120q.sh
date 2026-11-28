#!/bin/sh
# Prepares a v1.2.0 release-qualification session (knotrel#182; knotrel
# docs/releases/v1.2.0-qualification-plan.md, sections 2, 4, 8, 9 and 10). It builds
# everything, writes the tool map and checks the delegated collectors with their dry runs.
# It never measures.
#
# Usage: prepare_v120q.sh CAND_SHA TOOLING_SHA --pre-freeze [2|3]
#        prepare_v120q.sh CAND_SHA FREEZE_SHA ATTEMPT        (ATTEMPT: 1, 2 or 3; plan sections 9, 13, 14)
#
# Attempt 3 (plan section 14; "--pre-freeze 3"): freeze record and matrix under
# results/v1.2.0-qualification/attempt3/; the K harness and cf5-core builds again (K1, K2, K4),
# query-shape-probe against each arm (K3, M1: cand-qsp, base-qsp), built from build-inputs/<arm>
# with lockfiles derived for the arm (scripts/derive_arm_lock.py: knotrel-core version and
# nohash-hasher, which v1.1.0 locks and the candidate does not), the variant-k4 wrapper and its
# smoke, V1 seeds 182310-182312 and 182320-182322, the Q runner check, the disk check.
#
# Attempt 2 (plan section 13; "--pre-freeze 2" for its pre-freeze check): the freeze record
# and matrix are results/v1.2.0-qualification/attempt2/{FREEZE.json,v120q-matrix.json}; no K1
# or K2 builds (no base-harness, no cand-harness); V1 seeds 182210-182212 and 182220-182222;
# the server variant CAMP/variant-k4 (a wrapper execing the candidate server with
# KNOTREL_MAX_CONCURRENT_QUERIES=4, other targets linked) for cell Q-K4, with a smoke check
# that the limiter is active only there; the Q runner check (check_v120q_q_runner.py); both Q
# cells map exit 6 to TOOL_ERROR. Before cloning, at least MIN_FREE_GB (default 8) must be free
# on the evidence volume, and the free space before and after is recorded in logs/disk.txt.
#
# Attempt mode verifies the freeze first: FREEZE_SHA's only change from its parent adds
# results/v1.2.0-qualification/FREEZE.json, which names CAND_SHA (candidate), the parent
# (tooling) and the SHA-256 of results/v1.2.0-qualification/v120q-matrix.json at FREEZE_SHA.
# run_cf5.py checks the candidate checkout and the matrix against the same record.
#
# Builds, one target directory each, toolchain 1.100.0, --release --locked --offline:
#   ref-server        knotrel-server at v1.1.0 (V2 contention_base, Q reference, V1 label B)
#   cand-server       knotrel-server + measure_e2e at the candidate (V1 label C, V2, Q)
#   A-B-harness       the v1.0.0 A harness (knotrel-benchmarks df635a1e) against v1.1.0
#   A-C-harness       the same harness source against the candidate (lockfiles derived:
#                     only the knotrel-core version line may change)
#   base-harness      harness and cf5-core at the tooling commit against v1.1.0 (K1, K2 ref)
#   cand-harness      harness and cf5-core at the tooling commit against the candidate
#   cand-probes       core-lifecycle, http-lifecycle (B4)
#   cand-probes-count core-lifecycle with count-alloc (required by the B4 collector)
#   contention        contention-probe (V2; links no knotrel crate)
#   feeder            knotrel-pg-feeder + the load tool at the candidate (Q)
# Then: release-binary smoke of both servers; A identities and the two V1 plans (seeds of
# plan section 4.1); dry runs of V1 (both blocks), B4 and Q; the Q container check;
# tools.json; binary checksums.
#
# Declared before any measurement (plan sections 4.1 and 4.2), never derived from results:
#   V1 session seeds 182110 182111 182112 (block 1), 182120 182121 182122 (block 2);
#   B4 order seed 182400; Q cap 2700 s.
# Environment overrides: KNOTREL_REPO, BENCH_REPO, EVIDENCE_ROOT, SOURCE_MANIFEST.
set -eu
CAND=$1
TOOLING=$2
MODE=${3:-}
SCOPE=1
case "$MODE" in 2) SCOPE=2 ;; 3) SCOPE=3 ;; --pre-freeze) case "${4:-}" in 2|3) SCOPE=$4 ;; esac ;; esac
MIN_FREE_GB=${MIN_FREE_GB:-8}
REF=57c35e8d4b17bfce2d9941419ef251a2a2a1d69c          # knotrel v1.1.0 (published tag b0a19fd5, commit)
HARNESS=df635a1e872fd9e2d556b166ac23f342ee45d675      # core harness used by A since v0.4.0
SOURCE_MANIFEST_SHA256=95dfdabd165863c832473cd756441c0b825a846a64be45367b52901e2f6c8d42
KREPO=${KNOTREL_REPO:-/Users/rt/workspace/knotrel/knotrel}
BREPO=${BENCH_REPO:-/Users/rt/workspace/knotrel/knotrel-benchmarks}
EVIDENCE=${EVIDENCE_ROOT:-/Users/rt/workspace/knotrel/evidence}
SOURCE_MANIFEST=${SOURCE_MANIFEST:-$EVIDENCE/p0-coverage-increment-1-plan-20261030/manifest.json}
Q=results/v1.2.0-qualification
QA=$Q
[ "$SCOPE" = 1 ] || QA=$Q/attempt$SCOPE
for X in "$CAND" "$TOOLING"; do
  echo "$X" | grep -Eq '^[0-9a-f]{40}$' || { echo "commits must be 40-character SHAs" >&2; exit 3; }
done
[ "$(git -C "$KREPO" rev-parse v1.1.0^{commit})" = "$REF" ] \
  || { echo "knotrel tag v1.1.0 is not $REF" >&2; exit 3; }
case "$MODE" in
  --pre-freeze) LABEL=prefreeze
       [ "$SCOPE" = 1 ] || LABEL=prefreeze-a$SCOPE ;;
  1|2|3) LABEL=attempt$MODE
       F=$QA/FREEZE.json
       git -C "$BREPO" cat-file -e "$TOOLING:$F" 2>/dev/null \
         || { echo "$TOOLING has no $F" >&2; exit 3; }
       CHANGED=$(git -C "$BREPO" diff --name-status "$TOOLING^" "$TOOLING")
       [ "$CHANGED" = "$(printf 'A\t%s' "$F")" ] \
         || { echo "the freeze commit must only add $F; it changes: $CHANGED" >&2; exit 3; }
       git -C "$BREPO" show "$TOOLING:$F" | python3 -c "
import hashlib, json, subprocess, sys
cand, freeze, parent, repo, q = sys.argv[1:]
record = json.load(sys.stdin)
matrix = subprocess.run(['git', '-C', repo, 'show', freeze + ':' + q + '/v120q-matrix.json'],
                        capture_output=True, check=True).stdout
problems = []
if record.get('candidate') != cand:
    problems.append('freeze candidate %s is not %s' % (record.get('candidate'), cand))
if record.get('tooling') != parent:
    problems.append('freeze tooling %s is not the parent %s' % (record.get('tooling'), parent))
if record.get('matrix_sha256') != hashlib.sha256(matrix).hexdigest():
    problems.append('freeze matrix_sha256 is not the matrix at the freeze commit')
if not record.get('cap_hours'):
    problems.append('freeze record has no cap_hours (plan section 8)')
for p in problems: print(p, file=sys.stderr)
sys.exit(1 if problems else 0)
" "$CAND" "$TOOLING" "$(git -C "$BREPO" rev-parse "$TOOLING^")" "$BREPO" "$QA" || exit 3 ;;
  *) echo "third argument: --pre-freeze, 1, 2 or 3" >&2; exit 3 ;;
esac
# The tooling's lockfiles must name the candidate's knotrel version (--locked builds).
CAND_VERSION=$(git -C "$KREPO" show "$CAND:Cargo.toml" | grep -m1 '^version' | cut -d'"' -f2)
REF_VERSION=$(git -C "$KREPO" show "$REF:Cargo.toml" | grep -m1 '^version' | cut -d'"' -f2)
LOCKS="Cargo.lock tools/lifecycle-probes/Cargo.lock"
[ "$SCOPE" = 3 ] && LOCKS="$LOCKS tools/query-shape-probe/Cargo.lock"
for LOCK in $LOCKS; do
  git -C "$BREPO" show "$TOOLING:$LOCK" | python3 -c "
import re, sys
want = set(sys.argv[1:])
found = re.findall(r'name = \"knotrel-core\"\nversion = \"([^\"]+)\"', sys.stdin.read())
if len(found) != 1 or found[0] not in want:
    sys.exit('lockfile knotrel-core %s, expected one of %s' % (found, sorted(want)))
" "$CAND_VERSION" "$REF_VERSION" || { echo "in $LOCK" >&2; exit 3; }
done
[ "$CAND_VERSION" = "$REF_VERSION" ] \
  || { echo "candidate $CAND_VERSION and v1.1.0 $REF_VERSION differ: the K harness lockfile serves both arms only at one version" >&2; exit 3; }
[ "$(shasum -a 256 "$SOURCE_MANIFEST" | cut -d' ' -f1)" = "$SOURCE_MANIFEST_SHA256" ] \
  || { echo "A source manifest $SOURCE_MANIFEST missing or not the recorded one" >&2; exit 3; }
C7=$(echo "$CAND" | cut -c1-7)
T7=$(echo "$TOOLING" | cut -c1-7)
CAMP=$EVIDENCE/v1.2.0-qualification-$LABEL-$C7-$T7
if [ -e "$CAMP" ]; then echo "refusing to reuse $CAMP" >&2; exit 3; fi
FREE_KB=$(df -Pk "$EVIDENCE" | awk 'NR==2 {print $4}')
[ "$FREE_KB" -ge $((MIN_FREE_GB * 1024 * 1024)) ] \
  || { echo "only $((FREE_KB / 1024 / 1024)) GB free on the evidence volume; at least $MIN_FREE_GB GB required" >&2; exit 3; }
mkdir -p "$CAMP/logs" "$CAMP/src/cand" "$CAMP/src/base" "$CAMP/targets" "$CAMP/delegated" \
  "$CAMP/A/sources/B" "$CAMP/A/sources/C" "$CAMP/A/build-inputs/B" "$CAMP/A/build-inputs/C"
L=$CAMP/logs
trap 'RC=$?; [ "$RC" -eq 0 ] || echo "prepare failed (exit $RC) at $(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$L/PREPARE-FAILED.txt"' EXIT
echo "$LABEL" > "$L/prepare-mode.txt"
echo "before: $(df -Pk "$EVIDENCE" | awk 'NR==2 {print $4}') KB free (minimum ${MIN_FREE_GB} GB)" > "$L/disk.txt"
clone() { git clone --quiet "$1" "$2" && git -C "$2" checkout --quiet --detach "$3" && test "$(git -C "$2" rev-parse HEAD)" = "$3"; }

# --- Checkouts ---
# src/cand: the candidate and the tooling (analyzers, collectors, probes). src/base: v1.1.0
# and the same tooling, so the K harness builds against v1.1.0 through ../knotrel.
clone "$KREPO" "$CAMP/src/cand/knotrel" "$CAND"
clone "$BREPO" "$CAMP/src/cand/knotrel-benchmarks" "$TOOLING"
clone "$KREPO" "$CAMP/src/base/knotrel" "$REF"
clone "$BREPO" "$CAMP/src/base/knotrel-benchmarks" "$TOOLING"
clone "$KREPO" "$CAMP/A/sources/B/knotrel" "$REF"
clone "$KREPO" "$CAMP/A/sources/C/knotrel" "$CAND"
clone "$BREPO" "$CAMP/A/sources/knotrel-benchmarks" "$HARNESS"
for X in B C; do
  V=$(grep -m1 '^version' "$CAMP/A/sources/$X/knotrel/Cargo.toml" | cut -d'"' -f2)
  I=$CAMP/A/build-inputs/$X/knotrel-benchmarks
  mkdir -p "$I"
  cp -R "$CAMP/A/sources/knotrel-benchmarks/Cargo.toml" "$CAMP/A/sources/knotrel-benchmarks/crates" "$CAMP/A/sources/knotrel-benchmarks/rust-toolchain.toml" "$I/"
  # The knotrel-core version line and, since knotrel#210, nohash-hasher follow the arm
  # (derive_arm_lock.py at the tooling commit; a no-op for nohash-hasher in attempts 1 and 2).
  python3 "$CAMP/src/cand/knotrel-benchmarks/scripts/derive_arm_lock.py" "$CAMP/A/sources/knotrel-benchmarks/Cargo.lock" "$I/Cargo.lock" "$CAMP/A/sources/$X/knotrel"
  [ "$(grep -A1 'name = "knotrel-core"' "$I/Cargo.lock" | sed -n 's/^version = "\(.*\)"/\1/p')" = "$V" ] \
    || { echo "A-$X harness lock: knotrel-core version is not $V" >&2; exit 3; }
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
if [ "$SCOPE" = 1 ]; then
  ( cd "$B" && CARGO_TARGET_DIR=$T/cand-harness $CB -p knotrel-benchmarks --bin knotrel-benchmarks --bin cf5-core ) > "$L/build-cand-harness.log" 2>&1
  ( cd "$CAMP/src/base/knotrel-benchmarks" && CARGO_TARGET_DIR=$T/base-harness $CB -p knotrel-benchmarks --bin knotrel-benchmarks --bin cf5-core ) > "$L/build-base-harness.log" 2>&1
fi
if [ "$SCOPE" = 3 ]; then
  # Attempt 3: v1.1.0 still locks nohash-hasher and the candidate does not (knotrel#210), so
  # each arm builds the tooling from build-inputs/<arm>: the tooling sources with lockfiles
  # derived for that arm (derive_arm_lock.py) and knotrel linked next to them.
  for X in cand base; do
    I=$CAMP/build-inputs/$X/knotrel-benchmarks
    mkdir -p "$I/tools"
    cp -R "$CAMP/src/$X/knotrel-benchmarks/Cargo.toml" "$CAMP/src/$X/knotrel-benchmarks/crates" "$CAMP/src/$X/knotrel-benchmarks/rust-toolchain.toml" "$I/"
    cp -R "$CAMP/src/$X/knotrel-benchmarks/tools/query-shape-probe" "$CAMP/src/$X/knotrel-benchmarks/tools/lifecycle-probes" "$I/tools/"
    ln -s "../../src/$X/knotrel" "$CAMP/build-inputs/$X/knotrel"
    for LOCK in Cargo.lock tools/query-shape-probe/Cargo.lock tools/lifecycle-probes/Cargo.lock; do
      python3 "$B/scripts/derive_arm_lock.py" "$CAMP/src/$X/knotrel-benchmarks/$LOCK" "$I/$LOCK" "$CAMP/src/$X/knotrel"
      diff "$CAMP/src/$X/knotrel-benchmarks/$LOCK" "$I/$LOCK" >> "$L/$X-lock-derivation.diff" || true
    done
    ( cd "$I" && CARGO_TARGET_DIR=$T/$X-harness $CB -p knotrel-benchmarks --bin knotrel-benchmarks --bin cf5-core ) > "$L/build-$X-harness.log" 2>&1
    ( cd "$I/tools/query-shape-probe" && CARGO_TARGET_DIR=$T/$X-qsp $CB ) > "$L/build-$X-qsp.log" 2>&1
  done
fi
# Attempt 3: the B4 probes build from build-inputs/cand (lockfile derived for the candidate).
[ "$SCOPE" = 3 ] && P=$CAMP/build-inputs/cand/knotrel-benchmarks/tools/lifecycle-probes
( cd "$P" && CARGO_TARGET_DIR=$T/cand-probes $CB --bin core-lifecycle --bin http-lifecycle ) > "$L/build-cand-probes.log" 2>&1
( cd "$P" && CARGO_TARGET_DIR=$T/cand-probes-count $CB --features count-alloc --bin core-lifecycle ) > "$L/build-cand-probes-count.log" 2>&1
( cd "$B/tools/contention-probe" && CARGO_TARGET_DIR=$T/contention $CB ) > "$L/build-contention.log" 2>&1
( cd "$CAMP/src/cand/knotrel/integrations/postgres-feeder" && CARGO_TARGET_DIR=$T/feeder $CB --bin knotrel-pg-feeder --example load ) > "$L/build-feeder.log" 2>&1

# --- Release-binary smoke tests (deployment check of the servers, not measurements) ---
for X in ref cand; do
  bash "$CAMP/src/cand/knotrel/scripts/smoke-test-release-binary.sh" "$T/$X-server/release/knotrel-server" > "$L/smoke-$X-server.log" 2>&1
done

# --- Attempts 2 and 3: the K = 4 server variant for cell Q-K4 (plan sections 13, 14.8) ---
if [ "$SCOPE" != 1 ]; then
  V=$CAMP/variant-k4
  mkdir -p "$V/targets/cand-server/release" "$V/targets/ref-server/release" "$V/targets/feeder/release/examples"
  REAL=$T/cand-server/release/knotrel-server
  printf '#!/bin/sh\n# v1.2.0 attempt %s, cell Q-K4: the candidate server with KNOTREL_MAX_CONCURRENT_QUERIES=4.\nKNOTREL_MAX_CONCURRENT_QUERIES=4 exec %s "$@"\n' "$SCOPE" "$REAL" > "$V/targets/cand-server/release/knotrel-server"
  chmod +x "$V/targets/cand-server/release/knotrel-server"
  ln -s "$T/ref-server/release/knotrel-server" "$V/targets/ref-server/release/knotrel-server"
  ln -s "$T/feeder/release/knotrel-pg-feeder" "$V/targets/feeder/release/knotrel-pg-feeder"
  ln -s "$T/feeder/release/examples/load" "$V/targets/feeder/release/examples/load"
  ( cd "$V" && for X in cand-server/release/knotrel-server ref-server/release/knotrel-server feeder/release/knotrel-pg-feeder feeder/release/examples/load; do shasum -a 256 "targets/$X"; done ) > "$V/binaries-sha256.txt"
  # Smoke, not a measurement: the limiter series exist through the wrapper and not without it
  # (the series are registered only when the setting is configured), and K = 0 is refused.
  for SIDE in plain variant; do
    BIN=$REAL; PORT=18710
    [ "$SIDE" = variant ] && BIN=$V/targets/cand-server/release/knotrel-server && PORT=18711
    env -i KNOTREL_ADDR=127.0.0.1:$PORT KNOTREL_METRICS_ENABLED=true "$BIN" > "$L/smoke-k4-$SIDE.log" 2>&1 &
    PID=$!
    UP=0
    for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$PORT/health" > /dev/null 2>&1 && UP=1 && break; sleep 0.2; done
    METRICS=$(curl -fsS "http://127.0.0.1:$PORT/metrics" 2>/dev/null || true)
    kill "$PID" 2>/dev/null || true
    wait "$PID" 2>/dev/null || true
    [ "$UP" = 1 ] || { echo "smoke: $SIDE server did not start" >&2; exit 4; }
    HAS=0
    printf '%s\n' "$METRICS" | grep -q '^knotrel_query_limiter_waiting' && HAS=1
    echo "$SIDE limiter_series=$HAS" >> "$L/smoke-k4.txt"
    if [ "$SIDE" = variant ] && [ "$HAS" != 1 ]; then echo "smoke: limiter not active in variant-k4" >&2; exit 4; fi
    if [ "$SIDE" = plain ] && [ "$HAS" != 0 ]; then echo "smoke: limiter active without the setting" >&2; exit 4; fi
  done
  if env -i KNOTREL_ADDR=127.0.0.1:18712 KNOTREL_MAX_CONCURRENT_QUERIES=0 "$REAL" > "$L/smoke-k4-reject.log" 2>&1; then
    echo "smoke: KNOTREL_MAX_CONCURRENT_QUERIES=0 was not refused" >&2; exit 4
  fi
  grep -q KNOTREL_MAX_CONCURRENT_QUERIES "$L/smoke-k4-reject.log" || { echo "smoke: K = 0 refusal not reported" >&2; exit 4; }
  echo "K=0 refused" >> "$L/smoke-k4.txt"
fi

# --- V1: A identities and both plans (B = v1.1.0, C = candidate), then their dry runs ---
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
# Paths are confined (cli_paths): the campaign directory and the A source manifest's directory.
LIFECYCLE_QUALIFICATION_ROOTS="$CAMP:$(dirname "$SOURCE_MANIFEST")"
export LIFECYCLE_QUALIFICATION_ROOTS
if [ "$SCOPE" = 3 ]; then
  CK=v1.2.0-RQ3-V1; S1="182310 182311 182312"; S2="182320 182321 182322"
elif [ "$SCOPE" = 2 ]; then
  CK=v1.2.0-RQ2-V1; S1="182210 182211 182212"; S2="182220 182221 182222"
else
  CK=v1.2.0-RQ-V1; S1="182110 182111 182112"; S2="182120 182121 182122"
fi
# shellcheck disable=SC2086 # three seeds, one word each
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --checkpoint $CK-Block1 --session-seeds $S1 ) > "$L/A-plan.log" 2>&1
# shellcheck disable=SC2086 # nine cell ids, one word each
( cd "$B" && python3 scripts/prepare_bc_qualification.py "$CAMP/A/plan-block2" --identities "$CAMP/A/identities.json" --source-manifest "$SOURCE_MANIFEST" --phase extension --cells $CELLS --checkpoint $CK-Block2 --session-seeds $S2 ) > "$L/A-plan-block2.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --dry-run ) > "$L/A-dry-run.log" 2>&1
( cd "$B" && python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan-block2/manifest.json" --schedule "$CAMP/A/plan-block2/schedule.json" --dry-run ) > "$L/A-block2-dry-run.log" 2>&1

# --- Delegated collectors (run by run_cf5.py at their place in the order) ---
cat > "$CAMP/delegated/V1.sh" <<EOF
#!/bin/sh
# V1: the v1.0.0 A procedure, n = 24 fixed (two blocks of 12 pairs, no interim analysis).
# \$1: the fresh output directory run_cf5.py gives this attempt ({run}).
set -eu
cd "$B"
LIFECYCLE_QUALIFICATION_ROOTS="$CAMP"
export LIFECYCLE_QUALIFICATION_ROOTS
python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan/manifest.json" --schedule "$CAMP/A/plan/schedule.json" --execute "\$1/raw-main"
python3 scripts/run_p0_aa.py --manifest "$CAMP/A/plan-block2/manifest.json" --schedule "$CAMP/A/plan-block2/schedule.json" --execute "\$1/extension/raw-extension"
EOF
B4_ARGS="--profile final --core $T/cand-probes/release/core-lifecycle --core-count $T/cand-probes-count/release/core-lifecycle --http $T/cand-probes/release/http-lifecycle --order-seed 182400 --knotrel $CAMP/src/cand/knotrel --only B4 --lifecycle-engines compact-bfs --equivalent-references --atomic-references --window-multipliers $B/$Q/window-multipliers.json"
# shellcheck disable=SC2086 # B4_ARGS holds paths without spaces
( cd "$B" && python3 scripts/run_lifecycle_qualification.py --out "$CAMP/B4-dry" $B4_ARGS --dry-run ) > "$L/B4-dry-run.log" 2>&1
( cd "$B" && python3 scripts/run_v100q_q.py --check-cells "$CAMP/src/cand/knotrel/integrations/postgres-feeder/examples/load.rs" ) > "$L/Q-cells-check.log" 2>&1
# Q prerequisites: Docker Desktop, the pinned PostgreSQL image (pulled by digest if absent) and
# one container cycle (start, SELECT 1, removal); Docker Desktop is left as it was.
sh "$B/$Q/run_q.sh" "$CAMP" --prepare > "$L/Q-prepare.out" 2>&1

# --- Tool map ---
python3 - "$CAMP" "$B4_ARGS" "$Q" "$SCOPE" "$QA" <<'PY'
import json, shlex, sys
camp, b4, q, scope, qa = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
t = f"{camp}/targets"
b = f"{camp}/src/cand/knotrel-benchmarks"
tools = {
    "harness_cand": [f"{t}/cand-harness/release/knotrel-benchmarks"],
    "harness_base": [f"{t}/base-harness/release/knotrel-benchmarks"],
    "cf5_core_cand": [f"{t}/cand-harness/release/cf5-core"],
    "cf5_core_base": [f"{t}/base-harness/release/cf5-core"],
    "contention_cand": [f"{t}/contention/release/contention-probe", "--server-bin", f"{t}/cand-server/release/knotrel-server"],
    "contention_base": [f"{t}/contention/release/contention-probe", "--server-bin", f"{t}/ref-server/release/knotrel-server"],
    "_delegated": {
        # {run}: a fresh directory per attempt, under run_cf5.py's --out.
        "V1": {"argv": ["/bin/sh", f"{camp}/delegated/V1.sh", "{run}"], "cwd": b,
               "env": {"LIFECYCLE_QUALIFICATION_ROOTS": camp}},
        # run_q.sh: Docker Desktop and PostgreSQL exist only while Q runs; the URL is generated
        # at Q time and never written. Exit 1: Q NONCONFORMING by its own 45-minute cap;
        # 4: Docker or PostgreSQL unavailable (rerun once).
        "Q": {"argv": ["/bin/sh", f"{b}/{q}/run_q.sh", camp, "{run}"], "cwd": b,
              "incomplete_exit": [1]},
        "B4": {"argv": ["python3", "scripts/run_lifecycle_qualification.py", "--out", "{run}/B4"] + shlex.split(b4),
               "cwd": b, "env": {"LIFECYCLE_QUALIFICATION_ROOTS": camp}},
    },
    "_freeze": f"{b}/{qa}/FREEZE.json",
    "_checkouts": {"candidate": f"{camp}/src/cand/knotrel", "benchmarks": b,
                   "v110": f"{camp}/src/base/knotrel", "benchmarks_base": f"{camp}/src/base/knotrel-benchmarks",
                   "v110_A": f"{camp}/A/sources/B/knotrel", "harness_a": f"{camp}/A/sources/knotrel-benchmarks"},
    "_lockfiles": [f"{camp}/src/cand/knotrel/Cargo.lock", f"{camp}/src/base/knotrel/Cargo.lock", f"{b}/Cargo.lock",
                   f"{b}/tools/lifecycle-probes/Cargo.lock", f"{b}/tools/contention-probe/Cargo.lock",
                   f"{camp}/A/build-inputs/B/knotrel-benchmarks/Cargo.lock",
                   f"{camp}/A/build-inputs/C/knotrel-benchmarks/Cargo.lock"],
}
if scope == "3":
    # Attempt 3 (plan section 14): query-shape-probe against each arm (K3, M1).
    tools["qsp_cand"] = [f"{t}/cand-qsp/release/query-shape-probe"]
    tools["qsp_base"] = [f"{t}/base-qsp/release/query-shape-probe"]
    tools["_lockfiles"].append(f"{b}/tools/query-shape-probe/Cargo.lock")
    for arm in ("cand", "base"):
        for lock in ("Cargo.lock", "tools/query-shape-probe/Cargo.lock",
                     "tools/lifecycle-probes/Cargo.lock"):
            tools["_lockfiles"].append(f"{camp}/build-inputs/{arm}/knotrel-benchmarks/{lock}")
if scope == "2":
    # Attempt 2 (plan section 13): no K1 or K2 tools.
    for key in ("harness_cand", "harness_base", "cf5_core_cand", "cf5_core_base"):
        del tools[key]
if scope in ("2", "3"):
    # Both Q cells map exit 6 (the evaluation failed after the measurement) to TOOL_ERROR,
    # never rerun and never a verdict.
    q_spec = tools["_delegated"]["Q"]
    q_spec["tool_error_exit"] = [6]
    tools["_delegated"]["Q-K4"] = dict(q_spec, argv=q_spec["argv"] + ["variant-k4"])
json.dump(tools, open(f"{camp}/tools.json", "w"), indent=1)
PY
if [ "$SCOPE" != 1 ]; then
  # The runner gives Q and Q-K4 the directories the evaluator accepts, and a tool error is
  # distinguished from a failed criterion (plan section 13, pre-collection checks).
  ( cd "$B" && LIFECYCLE_QUALIFICATION_ROOTS="$CAMP:$EVIDENCE" python3 scripts/check_v120q_q_runner.py "$CAMP" --out "$L/Q-runner-check.json" \
      --fail-sample "$EVIDENCE/v1.2.0-qualification-attempt1-9faf168-4cf9b10/session1/delegated/Q-attempt1/Q" ) > "$L/Q-runner-check.log" 2>&1 \
    || { echo "Q runner check failed: $L/Q-runner-check.json" >&2; exit 4; }
fi

# --- Binary checksums ---
( cd "$CAMP" && find targets -type f -perm -u+x -path '*/release/*' ! -path '*/deps/*' ! -path '*/build/*' ! -name '*.d' -print0 | xargs -0 shasum -a 256 > binaries-sha256.txt )
( cd "$B" && python3 -c "import sys; sys.path.insert(0, 'scripts'); from cli_paths import confined; confined('$CAMP/tools.json', 'tools'); confined('$CAMP/session1', 'out')" ) \
  || { echo "campaign paths refused by cli_paths" >&2; exit 4; }
echo "after: $(df -Pk "$EVIDENCE" | awk 'NR==2 {print $4}') KB free; campaign $(du -sk "$CAMP" | cut -f1) KB" >> "$L/disk.txt"
echo "PREPARED ($LABEL) $CAMP"
echo "session: sh $B/$Q/run_session.sh $CAMP"
